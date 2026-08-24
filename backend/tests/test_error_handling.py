"""EH-1..EH-4 from everthing.md section 7."""
import pytest
from fastapi.testclient import TestClient
from google.genai import errors as genai_errors

from app.agent import _execute_tool
from app.gemini_client import call_with_retry
from app.main import app


@pytest.mark.asyncio
async def test_eh1_retries_on_429_then_succeeds():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise genai_errors.APIError(429, {"error": {"message": "rate limited"}})
        return "ok"

    result = await call_with_retry(flaky, base_delay=0.01)
    assert result == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_eh1_gives_up_after_max_attempts_with_clean_exception():
    def always_fails():
        raise genai_errors.APIError(429, {"error": {"message": "rate limited"}})

    with pytest.raises(genai_errors.APIError):
        await call_with_retry(always_fails, max_attempts=2, base_delay=0.01)


@pytest.mark.asyncio
async def test_eh2_retries_on_timeout():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise TimeoutError("timed out")
        return "ok"

    result = await call_with_retry(flaky, base_delay=0.01)
    assert result == "ok"


def test_eh3_tool_error_caught_not_raised(northstar):
    # Empty query would raise ToolError inside search_documents -- _execute_tool must
    # catch it and hand back an error dict, not let it propagate and crash the loop.
    result = _execute_tool("search_documents", {"query": "", "account_id": None}, northstar)
    assert "error" in result


def test_eh4_empty_message_rejected_without_calling_agent():
    client = TestClient(app)
    client.post("/api/auth/session", json={"identity": "ACCT-001"})
    resp = client.post("/api/chat", json={"session_id": "session-ACCT-001", "message": "   "})
    assert resp.status_code == 422
