import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import session_scope

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Mock login: no real credentials -- picking an identity IS the auth step, to make
# access-scoping easy to demo live. Session ids are deterministic per identity so a
# page refresh (same identity) reconnects to the same persisted conversation.
VALID_ACCOUNTS = {"ACCT-001", "ACCT-002", "ACCT-003", "ACCT-004"}


class SessionRequest(BaseModel):
    identity: str  # an account_id, or "internal"


@router.get("/accounts")
def list_accounts():
    with session_scope() as conn:
        rows = conn.execute("SELECT account_id, account_name, plan FROM accounts").fetchall()
    return [dict(r) for r in rows]


@router.post("/session")
def create_session(req: SessionRequest):
    if req.identity == "internal":
        session_id, role, account_id = "session-internal-ops", "internal", None
    elif req.identity in VALID_ACCOUNTS:
        session_id, role, account_id = f"session-{req.identity}", "customer", req.identity
    else:
        raise HTTPException(400, f"Unknown identity {req.identity!r}")

    with session_scope() as conn:
        conn.execute(
            """INSERT INTO sessions (session_id, account_id, role, created_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(session_id) DO NOTHING""",
            (session_id, account_id, role, str(time.time())),
        )
    return {"session_id": session_id, "role": role, "account_id": account_id}
