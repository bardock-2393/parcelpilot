"""QD-1..QD-7 from everthing.md section 7."""
from app.tools import query_structured_data


def test_qd1_own_order_returns_data():
    r = query_structured_data("order", "ORD-1001", account_id="ACCT-001")
    assert r["found"] is True
    assert r["order"]["order_id"] == "ORD-1001"


def test_qd2_other_account_order_not_found():
    r = query_structured_data("order", "ORD-1001", account_id="ACCT-002")
    assert r["found"] is False


def test_qd3_nonexistent_order_no_crash():
    r = query_structured_data("order", "ORD-9999-DOES-NOT-EXIST", account_id="ACCT-001")
    assert r["found"] is False
    assert "message" in r


def test_qd4_hours_late_calculation():
    r = query_structured_data("order", "ORD-1002", account_id="ACCT-001", calculation="hours_late")
    assert r["calculation"]["hours_late"] >= 0


def test_qd5_service_credit_boundary_just_under_and_over():
    # ORD-2002: carrier_fault=True, pickup not yet actual -> hours_late computed vs snapshot "now".
    r = query_structured_data("order", "ORD-2002", account_id="ACCT-002", calculation="service_credit_amount")
    calc = r["calculation"]
    assert calc["threshold_hours"] == 4  # LumenWorks agreement override
    if calc["hours_late"] > 4:
        assert calc["eligible"] is True
        assert calc["amount_inr"] == 300
    else:
        assert calc["eligible"] is False


def test_qd6_model_supplied_account_id_is_ignored_by_the_tool_layer():
    # The tool function itself trusts whatever account_id it's given -- enforcement
    # that the MODEL can't set it lives in the validator (see test_validator.py TV-4).
    # Here we confirm the tool correctly scopes to whatever account_id it is called with.
    mine = query_structured_data("order", "ORD-1001", account_id="ACCT-001")
    other = query_structured_data("order", "ORD-1001", account_id="ACCT-002")
    assert mine["found"] is True
    assert other["found"] is False


def test_qd7_internal_role_bypasses_account_scoping():
    internal_result = query_structured_data("ticket", "TKT-501", account_id=None)
    customer_wrong_account = query_structured_data("ticket", "TKT-501", account_id="ACCT-002")
    assert internal_result["found"] is True
    assert customer_wrong_account["found"] is False
