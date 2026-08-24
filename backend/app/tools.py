"""The 3 tools the agent can call. All account/role scoping is enforced here at the
function level -- never rely on the model's own restraint or the system prompt alone."""
import json
import time
from typing import Any

from app.config import CONFIRMATION_TOKEN_TTL_SECONDS, ESCALATION_RATE_LIMIT, ESCALATION_RATE_WINDOW_SECONDS
from app.db import session_scope
from app.identity import Identity
from app.ingest import embed_query, get_collection
from app.security import issue_token, new_draft_id, verify_token
from app.time_utils import parse_dt, snapshot_now

SIMILARITY_FLOOR = 0.55  # cosine similarity below this = "no confident match" (SD-5)

# Account-specific overrides sourced from the two signed agreements (05/06). Everything
# else falls back to the default SOP (03_Cancellation_and_Service_Credit_SOP_v4.pdf).
ACCOUNT_OVERRIDES: dict[str, dict[str, Any]] = {
    "ACCT-001": {  # Northstar Logistics Enterprise Agreement
        "cancellation_fee_waived_pre_pickup": True,
        "service_credit": None,  # SOP default applies; monthly INR 5,000 cap not modeled
    },
    "ACCT-002": {  # LumenWorks Service Agreement
        "cancellation_fee_waived_pre_pickup": False,
        "service_credit": {"threshold_hours": 4, "amount_inr": 300},
    },
}
DEFAULT_SERVICE_CREDIT = {"threshold_hours": 2, "cap_inr": 500, "cap_pct": 0.10}
DEFAULT_CANCELLATION_FEE_INR = 250
DEFAULT_CANCELLATION_GRACE_MINUTES = 30


class ToolError(Exception):
    """A validation-level error that should never reach the LLM as a stack trace."""


# --------------------------------------------------------------------------- #
# search_documents
# --------------------------------------------------------------------------- #
def search_documents(query: str, account_id: str | None, top_k: int = 5) -> dict:
    if not query or not query.strip():
        raise ToolError("query must not be empty")

    collection = get_collection()
    # No account context (customer callers always have one forced by the validator;
    # only an internal caller can reach here with account_id=None) -> only public docs.
    # Never surface a specific customer's signed agreement without that account's context.
    where = {"$or": [{"account_scope": ""}, {"account_scope": account_id or ""}]}

    candidate_n = max(top_k * 4, 15)
    query_embedding = embed_query(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(candidate_n, collection.count() or 1),
        where=where,
    )
    ids = results["ids"][0] if results["ids"] else []
    if not ids:
        return {"results": [], "note": "No matching documents found."}

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    ranked = []
    for doc, meta, dist in zip(docs, metas, dists):
        similarity = 1 - dist / 2  # chroma cosine distance is in [0, 2]
        ranked.append((meta["authority_rank"], -similarity, similarity, doc, meta))
    ranked.sort(key=lambda r: (r[0], r[1]))

    top = ranked[:top_k]
    if not top or top[0][2] < SIMILARITY_FLOOR:
        return {"results": [], "note": "No confident match in the document corpus."}

    return {
        "results": [
            {
                "text": doc,
                "source_file": meta["source_file"],
                "doc_type": meta["doc_type"],
                "status": meta["status"],
                "authority_rank": meta["authority_rank"],
                "page": meta["page"],
                "similarity": round(sim, 3),
            }
            for _, _, sim, doc, meta in top
        ]
    }


# --------------------------------------------------------------------------- #
# query_structured_data
# --------------------------------------------------------------------------- #
def _fetch_row(conn, table: str, id_col: str, lookup_id: str) -> dict | None:
    row = conn.execute(f"SELECT * FROM {table} WHERE {id_col} = ?", (lookup_id,)).fetchone()
    return dict(row) if row else None


def _hours_late(order: dict) -> float:
    window_end = parse_dt(order["pickup_window_end"])
    actual = parse_dt(order["pickup_actual_at"])
    reference = actual or snapshot_now()
    if window_end is None or reference is None:
        return 0.0
    delta = (reference - window_end).total_seconds() / 3600
    return round(max(delta, 0.0), 2)


def _service_credit(order: dict, account_id: str) -> dict:
    hours_late = _hours_late(order)
    if not order["carrier_fault"] or order["customer_fault"]:
        return {
            "eligible": False,
            "amount_inr": 0,
            "hours_late": hours_late,
            "reason": "Requires carrier fault with no customer fault.",
        }

    override = ACCOUNT_OVERRIDES.get(account_id, {}).get("service_credit")
    if override:
        threshold, amount = override["threshold_hours"], override["amount_inr"]
        source = "account agreement"
    else:
        threshold = DEFAULT_SERVICE_CREDIT["threshold_hours"]
        cap = DEFAULT_SERVICE_CREDIT["cap_inr"]
        amount = min(cap, round(order["shipment_fee_inr"] * DEFAULT_SERVICE_CREDIT["cap_pct"], 2))
        source = "default SOP"

    eligible = hours_late > threshold
    return {
        "eligible": eligible,
        "amount_inr": amount if eligible else 0,
        "hours_late": hours_late,
        "threshold_hours": threshold,
        "source": source,
        "requires_manager_approval": eligible and amount > 1000,
    }


def _cancellation_fee(order: dict, account_id: str) -> dict:
    status = order["status"]
    if status == "DELIVERED":
        return {"cancellable": False, "fee_inr": None, "reason": "Delivered orders cannot be cancelled."}
    if status == "PICKED_UP":
        return {
            "cancellable": False,
            "fee_inr": None,
            "reason": "Already picked up; use the return-to-origin workflow instead.",
        }

    waived = ACCOUNT_OVERRIDES.get(account_id, {}).get("cancellation_fee_waived_pre_pickup", False)
    if waived:
        return {"cancellable": True, "fee_inr": 0, "reason": "Waived by signed account agreement."}

    booked_at = parse_dt(order["booked_at"])
    requested_at = parse_dt(order.get("cancellation_requested_at")) or snapshot_now()
    if booked_at is None:
        return {"cancellable": True, "fee_inr": DEFAULT_CANCELLATION_FEE_INR, "reason": "Booking time unknown; default fee applied."}
    minutes_since_booking = (requested_at - booked_at).total_seconds() / 60
    if minutes_since_booking <= DEFAULT_CANCELLATION_GRACE_MINUTES:
        return {"cancellable": True, "fee_inr": 0, "reason": "Within the 30-minute no-fee grace window."}
    return {
        "cancellable": True,
        "fee_inr": DEFAULT_CANCELLATION_FEE_INR,
        "reason": "Past the 30-minute grace window; default SOP fee applies.",
    }


def query_structured_data(
    entity: str, lookup_id: str, account_id: str | None, calculation: str | None = None
) -> dict:
    table, id_col = ("orders", "order_id") if entity == "order" else ("tickets", "ticket_id")
    with session_scope() as conn:
        row = _fetch_row(conn, table, id_col, lookup_id)

    if row is None:
        return {"found": False, "message": f"No {entity} found with id {lookup_id}."}

    if account_id is not None and row["account_id"] != account_id:
        # Deliberately identical response to "not found" -- never confirm existence
        # of another account's data.
        return {"found": False, "message": f"No {entity} found with id {lookup_id}."}

    result: dict[str, Any] = {"found": True, entity: row}
    if calculation and entity == "order":
        owning_account = row["account_id"]
        if calculation == "hours_late":
            result["calculation"] = {"type": "hours_late", "hours_late": _hours_late(row)}
        elif calculation == "service_credit_amount":
            result["calculation"] = {"type": "service_credit_amount", **_service_credit(row, owning_account)}
        elif calculation == "cancellation_fee":
            result["calculation"] = {"type": "cancellation_fee", **_cancellation_fee(row, owning_account)}
    return result


# --------------------------------------------------------------------------- #
# create_escalation (draft-only; write happens only via /confirm-action)
# --------------------------------------------------------------------------- #
def check_rate_limit(conn, session_id: str) -> bool:
    cutoff = time.time() - ESCALATION_RATE_WINDOW_SECONDS
    row = conn.execute(
        "SELECT COUNT(*) FROM escalation_drafts WHERE session_id = ? AND created_at >= ?",
        (session_id, str(cutoff)),
    ).fetchone()
    return row[0] < ESCALATION_RATE_LIMIT


def create_escalation(
    action_type: str, reason: str, summary: str, identity: Identity, ticket_id: str | None = None
) -> dict:
    if not action_type or not reason or not summary:
        raise ToolError("action_type, reason, and summary are required")

    draft = {
        "action_type": action_type,
        "reason": reason,
        "summary": summary,
        "ticket_id": ticket_id,
        "account_id": identity.account_id,
    }
    draft_id = new_draft_id()
    with session_scope() as conn:
        if not check_rate_limit(conn, identity.session_id):
            raise ToolError("Rate limit exceeded for escalation creation on this session.")
        now = time.time()
        conn.execute(
            """INSERT INTO escalation_drafts (token, session_id, account_id, payload_json,
                   used, created_at, expires_at)
               VALUES (?, ?, ?, ?, 0, ?, ?)""",
            (draft_id, identity.session_id, identity.account_id, json.dumps(draft), str(now), str(now + CONFIRMATION_TOKEN_TTL_SECONDS)),
        )
    token = issue_token(draft_id, identity.session_id)
    return {"status": "pending_confirmation", "draft": draft, "confirmation_token": token}


def confirm_escalation(token: str, identity: Identity) -> dict:
    draft_id = verify_token(token, identity.session_id)
    if draft_id is None:
        return {"status": "rejected", "reason": "Invalid or forged confirmation token."}

    with session_scope() as conn:
        row = conn.execute(
            "SELECT * FROM escalation_drafts WHERE token = ?", (draft_id,)
        ).fetchone()
        if row is None:
            return {"status": "rejected", "reason": "Unknown confirmation draft."}
        if row["used"]:
            return {"status": "rejected", "reason": "This confirmation token has already been used."}
        if float(row["expires_at"]) < time.time():
            return {"status": "rejected", "reason": "This confirmation token has expired."}
        if row["session_id"] != identity.session_id:
            return {"status": "rejected", "reason": "Token does not belong to this session."}

        draft = json.loads(row["payload_json"])
        escalation_id = f"ESC-{draft_id[:8].upper()}"
        conn.execute(
            """INSERT INTO escalations (escalation_id, account_id, session_id, ticket_id,
                   action_type, reason, summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                escalation_id,
                draft["account_id"],
                identity.session_id,
                draft.get("ticket_id"),
                draft["action_type"],
                draft["reason"],
                draft["summary"],
                str(time.time()),
            ),
        )
        conn.execute("UPDATE escalation_drafts SET used = 1 WHERE token = ?", (draft_id,))
    return {"status": "created", "escalation_id": escalation_id}


def cancel_escalation(token: str, identity: Identity) -> dict:
    draft_id = verify_token(token, identity.session_id)
    if draft_id is None:
        return {"status": "rejected", "reason": "Invalid or forged confirmation token."}
    with session_scope() as conn:
        row = conn.execute("SELECT * FROM escalation_drafts WHERE token = ?", (draft_id,)).fetchone()
        if row is None or row["used"]:
            return {"status": "rejected", "reason": "Unknown or already-used draft."}
        conn.execute("UPDATE escalation_drafts SET used = 1 WHERE token = ?", (draft_id,))
    return {"status": "cancelled"}
