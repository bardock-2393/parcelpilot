"""Proactive issue detection: scheduled/on-demand job over the same tickets/orders
tables the chat agent reads. Writes findings to flagged_issues; safe to re-run
(dedupe_key is UNIQUE, so reruns with no new data create no duplicate rows)."""
import json
import time
from collections import defaultdict
from datetime import timedelta

from app.db import session_scope
from app.time_utils import parse_dt, snapshot_now

SPIKE_LOOKBACK_DAYS = 3
SPIKE_THRESHOLD = 3
NEAR_BREACH_WINDOW_HOURS = 2
MULTI_ACCOUNT_MIN_ACCOUNTS = 2

# Keyword tags mirroring the Product Operations Guide's known issues (04_*.pdf).
KNOWN_ISSUE_TAGS = {
    "KI-208": ["bulk upload", "csv"],
    "KI-211": ["swiftship", "still shows booked", "pickup"],
}

# ponytail: keyword heuristic, not a real classifier -- upgrade to an LLM/embedding
# tagger if the ticket corpus grows past what a few keyword lists can cover.
SEVERITY_P1_KEYWORDS = ["all ", "every user", "outage", "security", "exposure", "credential"]
SEVERITY_P2_KEYWORDS = ["bulk upload", "fails", "failing", "degraded"]

# First-response targets in hours: (account overrides sourced from the signed
# agreements; falls back to the CURRENT Support Policy v3 by plan).
ACCOUNT_SLA_HOURS = {
    "ACCT-001": {"P1": 0.25, "P2": 1, "P3": 8},  # Northstar Enterprise Agreement
    "ACCT-002": {"P1": 2, "P2": 4, "P3": 48},  # LumenWorks Service Agreement
}
PLAN_SLA_HOURS = {
    "Enterprise": {"P1": 0.5, "P2": 2, "P3": 24},
    "Growth": {"P1": 2, "P2": 4, "P3": 48},
    "Standard": {"P1": 4, "P2": 24, "P3": 48},
}


def tag_ticket(ticket: dict) -> str | None:
    text = f"{ticket['subject']} {ticket['description']}".lower()
    for tag, keywords in KNOWN_ISSUE_TAGS.items():
        if any(kw in text for kw in keywords):
            return tag
    return None


def classify_severity(ticket: dict) -> str:
    text = f"{ticket['subject']} {ticket['description']}".lower()
    if any(kw in text for kw in SEVERITY_P1_KEYWORDS):
        return "P1"
    if any(kw in text for kw in SEVERITY_P2_KEYWORDS):
        return "P2"
    return "P3"


def sla_deadline(ticket: dict, account: dict) -> "datetime | None":
    created = parse_dt(ticket["created_at"])
    if created is None:
        return None
    severity = classify_severity(ticket)
    hours = ACCOUNT_SLA_HOURS.get(account["account_id"], {}).get(severity)
    if hours is None:
        hours = PLAN_SLA_HOURS.get(account["plan"], PLAN_SLA_HOURS["Standard"])[severity]
    return created + timedelta(hours=hours)


def _insert_flag(conn, dedupe_key: str, issue_type: str, severity: str, summary: str, affected: dict) -> bool:
    cur = conn.execute(
        """INSERT OR IGNORE INTO flagged_issues
               (dedupe_key, issue_type, severity, summary, affected_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (dedupe_key, issue_type, severity, summary, json.dumps(affected), str(time.time())),
    )
    return cur.rowcount > 0


def run_detection() -> dict:
    now = snapshot_now()
    created = {"complaint_spike": 0, "sla_breach": 0, "sla_near_breach": 0, "multi_account_pattern": 0}

    with session_scope() as conn:
        tickets = [dict(r) for r in conn.execute("SELECT * FROM tickets").fetchall()]
        accounts = {r["account_id"]: dict(r) for r in conn.execute("SELECT * FROM accounts").fetchall()}

        by_tag: dict[str, list[dict]] = defaultdict(list)
        for t in tickets:
            created_at = parse_dt(t["created_at"])
            if created_at is None or (now - created_at) > timedelta(days=SPIKE_LOOKBACK_DAYS):
                continue
            tag = tag_ticket(t)
            if tag:
                by_tag[tag].append(t)

        for tag, group in by_tag.items():
            if len(group) >= SPIKE_THRESHOLD:
                key = f"spike:{tag}:{now.date().isoformat()}"
                if _insert_flag(
                    conn, key, "complaint_spike", "amber",
                    f"{len(group)} tickets in the last {SPIKE_LOOKBACK_DAYS} days match known issue {tag}.",
                    {"tag": tag, "ticket_ids": [t["ticket_id"] for t in group]},
                ):
                    created["complaint_spike"] += 1

            distinct_accounts = {t["account_id"] for t in group}
            if len(distinct_accounts) >= MULTI_ACCOUNT_MIN_ACCOUNTS:
                key = f"multi_account:{tag}:{now.date().isoformat()}"
                if _insert_flag(
                    conn, key, "multi_account_pattern", "gray",
                    f"{tag} reported across {len(distinct_accounts)} accounts: {', '.join(sorted(distinct_accounts))}.",
                    {"tag": tag, "accounts": sorted(distinct_accounts), "ticket_ids": [t["ticket_id"] for t in group]},
                ):
                    created["multi_account_pattern"] += 1

        for t in tickets:
            if t["status"] != "open":
                continue
            account = accounts.get(t["account_id"])
            if account is None:
                continue
            deadline = sla_deadline(t, account)
            if deadline is None:
                continue
            if deadline < now:
                key = f"sla_breach:{t['ticket_id']}"
                if _insert_flag(
                    conn, key, "sla_breach", "red",
                    f"Ticket {t['ticket_id']} breached its {classify_severity(t)} response target.",
                    {"ticket_id": t["ticket_id"], "account_id": t["account_id"], "deadline": deadline.isoformat()},
                ):
                    created["sla_breach"] += 1
            elif deadline < now + timedelta(hours=NEAR_BREACH_WINDOW_HOURS):
                key = f"sla_near_breach:{t['ticket_id']}"
                if _insert_flag(
                    conn, key, "sla_near_breach", "amber",
                    f"Ticket {t['ticket_id']} is approaching its {classify_severity(t)} response target.",
                    {"ticket_id": t["ticket_id"], "account_id": t["account_id"], "deadline": deadline.isoformat()},
                ):
                    created["sla_near_breach"] += 1

    return created


def list_flagged_issues() -> list[dict]:
    with session_scope() as conn:
        rows = conn.execute("SELECT * FROM flagged_issues ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["affected"] = json.loads(d.pop("affected_json"))
        out.append(d)
    return out
