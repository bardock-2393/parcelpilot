import shutil
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.config import UPLOAD_DIR
from app.dependencies import resolve_identity
from app.detection import list_flagged_issues, run_detection
from app.ingest import ingest_uploaded_file, list_documents
from app.trace import get_trace

router = APIRouter(prefix="/api/ops", tags=["ops"])

DOC_TYPES = {"support_policy", "sop", "product_guide", "agreement", "other"}
STATUSES = {"current", "deprecated"}


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


@router.get("/documents")
def documents(session_id: str):
    _require_internal(session_id)
    return list_documents()


@router.post("/documents")
async def upload_document(
    session_id: str,
    file: UploadFile,
    doc_type: str = Form(...),
    status: str = Form(...),
    account_scope: str = Form(""),
):
    _require_internal(session_id)
    if doc_type not in DOC_TYPES:
        raise HTTPException(400, f"doc_type must be one of {sorted(DOC_TYPES)}")
    if status not in STATUSES:
        raise HTTPException(400, f"status must be one of {sorted(STATUSES)}")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name  # strip any path components
    dest = UPLOAD_DIR / safe_name
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    result = ingest_uploaded_file(dest, safe_name, doc_type, status, account_scope or None)
    return result
