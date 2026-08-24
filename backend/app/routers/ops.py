from fastapi import APIRouter, HTTPException

from app.dependencies import resolve_identity
from app.detection import list_flagged_issues, run_detection
from app.trace import get_trace

router = APIRouter(prefix="/api/ops", tags=["ops"])


def _require_internal(session_id: str):
    identity = resolve_identity(session_id)
    if not identity.is_internal:
        raise HTTPException(403, "Internal role required.")
    return identity


@router.get("/flagged-issues")
def flagged_issues(session_id: str):
    _require_internal(session_id)
    return list_flagged_issues()


@router.post("/run-detection")
def trigger_detection(session_id: str):
    _require_internal(session_id)
    return run_detection()


@router.get("/trace")
def trace(session_id: str, target_session_id: str):
    _require_internal(session_id)
    return get_trace(target_session_id)
