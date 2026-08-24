import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from app.agent import clear_history, get_history, run_turn
from app.config import AVAILABLE_MODELS, GEMINI_MODEL
from app.dependencies import resolve_identity
from app.tools import cancel_escalation, confirm_escalation

log = logging.getLogger("parcelpilot.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    model: str | None = None

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("message must not be empty")
        return v

    @field_validator("model")
    @classmethod
    def known_model(cls, v: str | None) -> str | None:
        if v and v not in AVAILABLE_MODELS:
            raise ValueError(f"model must be one of {AVAILABLE_MODELS}")
        return v


class ConfirmRequest(BaseModel):
    session_id: str
    token: str
    action: str  # "confirm" | "cancel"


@router.get("/history")
def history(session_id: str):
    resolve_identity(session_id)  # 401 if unknown
    return get_history(session_id)


@router.get("/models")
def models():
    return {"default": GEMINI_MODEL, "options": AVAILABLE_MODELS}


@router.delete("/history")
def delete_history(session_id: str):
    resolve_identity(session_id)  # 401 if unknown
    clear_history(session_id)
    return {"status": "cleared"}


@router.post("")
async def chat(req: ChatRequest):
    identity = resolve_identity(req.session_id)
    try:
        return await run_turn(identity, req.message, model=req.model)
    except Exception:
        log.exception("Agent turn failed for session %s", req.session_id)
        raise HTTPException(502, "The assistant is temporarily unavailable. Please try again.")


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    identity = resolve_identity(req.session_id)

    async def event_source():
        try:
            result = await run_turn(identity, req.message, model=req.model)
        except Exception:
            log.exception("Agent turn failed for session %s", req.session_id)
            yield f"event: error\ndata: {json.dumps({'message': 'The assistant is temporarily unavailable. Please try again.'})}\n\n"
            return

        for word in result["text"].split(" "):
            yield f"event: token\ndata: {json.dumps({'text': word + ' '})}\n\n"

        done_payload = {"tool_calls": result["tool_calls"], "escalation_draft": result["escalation_draft"]}
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@router.post("/confirm-action")
def confirm_action(req: ConfirmRequest):
    identity = resolve_identity(req.session_id)
    if req.action == "confirm":
        return confirm_escalation(req.token, identity)
    if req.action == "cancel":
        return cancel_escalation(req.token, identity)
    raise HTTPException(400, "action must be 'confirm' or 'cancel'")
