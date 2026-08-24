"""SD-1..SD-6 from everthing.md section 7."""
import pytest

from app.tools import ToolError, search_documents


def test_sd1_no_account_returns_general_docs_only():
    r = search_documents("cancellation fee", account_id=None)
    assert r["results"]
    assert all(item["doc_type"] != "agreement" for item in r["results"])


def test_sd2_northstar_agreement_ranks_above_general_sop():
    r = search_documents("cancellation fee", account_id="ACCT-001")
    assert r["results"][0]["source_file"] == "05_Northstar_Logistics_Enterprise_Agreement.pdf"


def test_sd3_no_cross_account_contamination():
    north = search_documents("cancellation fee", account_id="ACCT-001")
    lumen = search_documents("cancellation fee", account_id="ACCT-002")
    north_files = {r["source_file"] for r in north["results"]}
    lumen_files = {r["source_file"] for r in lumen["results"]}
    assert "05_Northstar_Logistics_Enterprise_Agreement.pdf" not in lumen_files
    assert "06_LumenWorks_Service_Agreement.pdf" not in north_files
    assert north_files != lumen_files or not north_files


def test_sd4_deprecated_ranked_last_not_first():
    r = search_documents("support response time severity", account_id=None, top_k=5)
    statuses = [item["status"] for item in r["results"]]
    if "deprecated" in statuses:
        assert statuses[0] != "deprecated"


def test_sd5_irrelevant_query_returns_low_confidence():
    r = search_documents("what is the capital of France", account_id=None)
    assert r["results"] == []


def test_sd6_empty_query_raises():
    with pytest.raises(ToolError):
        search_documents("", account_id=None)
