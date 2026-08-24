"""CE-1..CE-7 from everthing.md section 7."""
import time

import pytest

from app.db import session_scope
from app.security import issue_token
from app.tools import ToolError, cancel_escalation, confirm_escalation, create_escalation


def _count_escalations() -> int:
    with session_scope() as conn:
        return conn.execute("SELECT COUNT(*) FROM escalations").fetchone()[0]


def test_ce1_draft_only_no_write(northstar):
    before = _count_escalations()
    r = create_escalation("manager_approval", "no matching clause", "waive fee", northstar)
    assert r["status"] == "pending_confirmation"
    assert _count_escalations() == before


def test_ce2_confirm_writes_row(northstar):
    r = create_escalation("manager_approval", "reason", "summary", northstar)
    before = _count_escalations()
    result = confirm_escalation(r["confirmation_token"], northstar)
    assert result["status"] == "created"
    assert _count_escalations() == before + 1


def test_ce3_replayed_token_rejected(northstar):
    r = create_escalation("manager_approval", "reason", "summary", northstar)
    first = confirm_escalation(r["confirmation_token"], northstar)
    second = confirm_escalation(r["confirmation_token"], northstar)
    assert first["status"] == "created"
    assert second["status"] == "rejected"


def test_ce4_fabricated_token_rejected(northstar):
    fake = issue_token("not-a-real-draft-id", northstar.session_id)
    result = confirm_escalation(fake, northstar)
    assert result["status"] == "rejected"


def test_ce5_cancel_writes_nothing(northstar):
    r = create_escalation("manager_approval", "reason", "summary", northstar)
    before = _count_escalations()
    result = cancel_escalation(r["confirmation_token"], northstar)
    assert result["status"] == "cancelled"
    assert _count_escalations() == before
    # cancelled token can't later be confirmed
    assert confirm_escalation(r["confirmation_token"], northstar)["status"] == "rejected"


def test_ce6_missing_required_field_raises(northstar):
    with pytest.raises(ToolError):
        create_escalation("manager_approval", "", "summary", northstar)


def test_ce7_rate_limit_throttles_rapid_requests(northstar):
    accepted = 0
    rejected = 0
    for _ in range(12):
        try:
            create_escalation("manager_approval", "reason", "summary", northstar)
            accepted += 1
        except ToolError:
            rejected += 1
    assert rejected > 0
