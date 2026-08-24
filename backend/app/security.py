"""Signed, single-use confirmation tokens for state-changing actions (stdlib hmac,
no extra dependency: a token is a random id whose authenticity is proven by an
HMAC signature over id+session+expiry; validity/single-use is enforced by the
escalation_drafts DB row, not by the signature alone)."""
import hashlib
import hmac
import secrets
import time

from app.config import TOKEN_SECRET


def _sign(raw: str) -> str:
    return hmac.new(TOKEN_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()


def issue_token(draft_id: str, session_id: str) -> str:
    raw = f"{draft_id}:{session_id}:{int(time.time())}"
    return f"{raw}:{_sign(raw)}"


def verify_token(token: str, session_id: str) -> str | None:
    """Returns the draft_id if the signature is valid and matches the session, else None."""
    parts = token.split(":")
    if len(parts) != 4:
        return None
    draft_id, token_session, ts, sig = parts
    raw = f"{draft_id}:{token_session}:{ts}"
    if not hmac.compare_digest(_sign(raw), sig):
        return None
    if token_session != session_id:
        return None
    return draft_id


def new_draft_id() -> str:
    return secrets.token_urlsafe(16)
