from fastapi import HTTPException

from app.db import session_scope
from app.identity import Identity


def resolve_identity(session_id: str) -> Identity:
    with session_scope() as conn:
        row = conn.execute(
            "SELECT session_id, account_id, role FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(401, "Unknown session_id. Call /api/auth/session first.")
    return Identity(session_id=row["session_id"], role=row["role"], account_id=row["account_id"])
