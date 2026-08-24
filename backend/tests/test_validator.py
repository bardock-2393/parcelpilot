"""TV-1..TV-4 from everthing.md section 7 (TV-5, the tool-call cap, is in test_agent_loop.py)."""
import pytest

from app.validator import ValidationFailure, validate_call


def test_tv1_well_formed_call_passes(northstar):
    args = validate_call("query_structured_data", {"entity": "order", "lookup_id": "ORD-1001"}, northstar)
    assert args["entity"] == "order"
    assert args["lookup_id"] == "ORD-1001"


def test_tv2_missing_required_param_rejected(northstar):
    with pytest.raises(ValidationFailure):
        validate_call("query_structured_data", {"entity": "order"}, northstar)  # missing lookup_id


def test_tv3_unexpected_param_rejected(northstar):
    with pytest.raises(ValidationFailure):
        validate_call(
            "query_structured_data",
            {"entity": "order", "lookup_id": "ORD-1001", "made_up_param": "x"},
            northstar,
        )


def test_tv4_account_id_forcibly_overwritten(northstar):
    args = validate_call(
        "query_structured_data",
        {"entity": "order", "lookup_id": "ORD-1001", "account_id": "ACCT-002"},
        northstar,
    )
    assert args["account_id"] == "ACCT-001"  # session's real account, not the model's ACCT-002


def test_internal_role_may_pass_account_id_through(internal):
    args = validate_call(
        "query_structured_data",
        {"entity": "order", "lookup_id": "ORD-1001", "account_id": "ACCT-002"},
        internal,
    )
    assert args["account_id"] == "ACCT-002"
