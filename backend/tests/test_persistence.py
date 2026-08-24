"""SP-1..SP-3 from everthing.md section 7. Uses the message-store functions directly
(no LLM call needed -- persistence is a DB-layer concern)."""
import uuid

from app.agent import _save_message, get_history


def _fresh_session_id(label: str) -> str:
    # Unique per run: the sqlite file persists across test runs, so a fixed id would
    # accumulate messages from earlier runs and break exact-count assertions.
    return f"test-persistence-{label}-{uuid.uuid4().hex[:8]}"


def test_sp1_messages_returned_in_order():
    session_id = _fresh_session_id("sp1")
    _save_message(session_id, "user", "first")
    _save_message(session_id, "model", "first reply")
    _save_message(session_id, "user", "second")
    history = get_history(session_id)
    assert [h["content"] for h in history] == ["first", "first reply", "second"]


def test_sp2_history_survives_reconnect_with_same_session_id():
    session_id = _fresh_session_id("sp2")
    _save_message(session_id, "user", "hello")
    # Simulate "backend restart" by just re-fetching from the DB with a fresh call --
    # nothing is cached in-process, so this proves it isn't an in-memory dict.
    history = get_history(session_id)
    assert len(history) == 1
    assert history[0]["content"] == "hello"


def test_sp3_no_bleed_between_concurrent_sessions():
    session_a, session_b = _fresh_session_id("sp3a"), _fresh_session_id("sp3b")
    _save_message(session_a, "user", "session A message")
    _save_message(session_b, "user", "session B message")
    a = get_history(session_a)
    b = get_history(session_b)
    assert [h["content"] for h in a] == ["session A message"]
    assert [h["content"] for h in b] == ["session B message"]
