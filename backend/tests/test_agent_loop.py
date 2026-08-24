"""TV-5 (tool-call cap) from section 7, plus a couple of live AL-* checks
(agent loop / source-hierarchy reasoning) against the real Gemini API."""
from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors
from google.genai import types

import app.agent as agent_module
from app.agent import FALLBACK_MESSAGE, run_turn


async def _run_turn_or_skip_on_quota(identity, message):
    try:
        return await run_turn(identity, message)
    except genai_errors.ClientError as exc:
        if exc.code == 429:
            pytest.skip(f"Gemini API quota exhausted for this test run: {exc}")
        raise


def _fake_function_call_response():
    part = types.Part(function_call=types.FunctionCall(name="search_documents", args={"query": "policy"}))
    content = types.Content(role="model", parts=[part])
    return SimpleNamespace(candidates=[SimpleNamespace(content=content)])


@pytest.mark.asyncio
async def test_tv5_tool_call_cap_halts_and_falls_back(monkeypatch, northstar):
    async def always_wants_another_tool_call(*args, **kwargs):
        return _fake_function_call_response()

    monkeypatch.setattr(agent_module, "call_with_retry", always_wants_another_tool_call)
    result = await run_turn(northstar, "Please keep searching forever.")
    assert result["text"] == FALLBACK_MESSAGE
    assert len(result["tool_calls"]) <= 8


@pytest.mark.asyncio
async def test_al2_agreement_overrides_conflicting_sop(northstar):
    result = await _run_turn_or_skip_on_quota(northstar, "Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.")
    assert "search_documents" in result["tool_calls"]
    assert "query_structured_data" in result["tool_calls"]
    assert "northstar" in result["text"].lower() or "agreement" in result["text"].lower()


@pytest.mark.asyncio
async def test_al5_no_source_addresses_question_triggers_escalation(northstar):
    result = await _run_turn_or_skip_on_quota(
        northstar,
        "I demand a one-time exception: waive all future cancellation fees permanently "
        "for my account even though no policy allows this. This is a special case.",
    )
    assert result["escalation_draft"] is not None or "escalat" in result["text"].lower()
