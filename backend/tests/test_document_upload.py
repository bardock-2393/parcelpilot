"""Internal-only PDF upload -> ingest path (added on top of the assessment's own
requirements as a bonus, per the brief's 'feel free to add more data' note)."""
from app.config import DATA_DIR
from app.ingest import ingest_uploaded_file, list_documents


def test_upload_ingests_and_lists_the_document():
    path = DATA_DIR / "01_Support_Policy_v3_CURRENT.pdf"
    result = ingest_uploaded_file(path, "01_Support_Policy_v3_CURRENT.pdf", "support_policy", "current", None)
    assert result["chunks_ingested"] >= 1

    docs = list_documents()
    entry = next(d for d in docs if d["source_file"] == "01_Support_Policy_v3_CURRENT.pdf")
    assert entry["doc_type"] == "support_policy"
    assert entry["authority_rank"] == 1  # current, non-agreement


def test_upload_rerun_does_not_duplicate_chunks():
    path = DATA_DIR / "04_Product_Operations_Guide_and_Known_Issues.pdf"
    first = ingest_uploaded_file(path, "04_Product_Operations_Guide_and_Known_Issues.pdf", "product_guide", "current", None)
    second = ingest_uploaded_file(path, "04_Product_Operations_Guide_and_Known_Issues.pdf", "product_guide", "current", None)
    assert first["chunks_ingested"] == second["chunks_ingested"]
    docs = list_documents()
    entry = next(d for d in docs if d["source_file"] == "04_Product_Operations_Guide_and_Known_Issues.pdf")
    assert entry["chunk_count"] == first["chunks_ingested"]


def test_agreement_doc_type_forces_authority_rank_zero():
    path = DATA_DIR / "05_Northstar_Logistics_Enterprise_Agreement.pdf"
    ingest_uploaded_file(path, "05_Northstar_Logistics_Enterprise_Agreement.pdf", "agreement", "current", "ACCT-001")
    docs = list_documents()
    entry = next(d for d in docs if d["source_file"] == "05_Northstar_Logistics_Enterprise_Agreement.pdf")
    assert entry["authority_rank"] == 0
