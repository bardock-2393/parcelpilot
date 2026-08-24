"""Parse the policy/agreement PDFs, chunk by page, embed with Gemini, and
upsert into a persistent ChromaDB collection (idempotent by doc_id)."""
import chromadb
import pymupdf

from app.config import CHROMA_DIR, DATA_DIR, GEMINI_EMBEDDING_MODEL
from app.gemini_client import get_client

# doc_type, status, account_scope (None = visible to all accounts), authority_rank
# (lower = higher precedence: agreement > current policy/SOP/guide > deprecated).
DOC_META = {
    "01_Support_Policy_v3_CURRENT.pdf": ("support_policy", "current", None, 1),
    "02_Support_Policy_v2_DEPRECATED.pdf": ("support_policy", "deprecated", None, 3),
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf": ("sop", "current", None, 1),
    "04_Product_Operations_Guide_and_Known_Issues.pdf": ("product_guide", "current", None, 1),
    "05_Northstar_Logistics_Enterprise_Agreement.pdf": ("agreement", "current", "ACCT-001", 0),
    "06_LumenWorks_Service_Agreement.pdf": ("agreement", "current", "ACCT-002", 0),
}

EMBED_BATCH = 16


def _chunks_for_file(path, filename: str, doc_type: str, status: str, account_scope: str | None, authority_rank: int):
    doc = pymupdf.open(path)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if not text:
            continue
        doc_id = f"{filename}::p{page_num}"
        yield {
            "doc_id": doc_id,
            "text": text,
            "metadata": {
                "source_file": filename,
                "doc_type": doc_type,
                "status": status,
                "account_scope": account_scope or "",
                "authority_rank": authority_rank,
                "page": page_num,
            },
        }


def _chunks():
    for filename, (doc_type, status, account_scope, authority_rank) in DOC_META.items():
        yield from _chunks_for_file(DATA_DIR / filename, filename, doc_type, status, account_scope, authority_rank)


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    client = get_client()
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i : i + EMBED_BATCH]
        resp = client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=batch,
            config={"task_type": task_type},
        )
        out.extend([e.values for e in resp.embeddings])
    return out


def get_collection():
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return chroma_client.get_or_create_collection(name="documents")


def ingest() -> dict:
    collection = get_collection()
    chunks = list(_chunks())
    ids = [c["doc_id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    embeddings = _embed(texts, task_type="RETRIEVAL_DOCUMENT")
    # upsert (not add) keyed by doc_id -> re-running does not duplicate vectors.
    collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return {"chunks_ingested": len(ids), "collection_count": collection.count()}


def embed_query(query: str) -> list[float]:
    return _embed([query], task_type="RETRIEVAL_QUERY")[0]


def ingest_uploaded_file(
    path, filename: str, doc_type: str, status: str, account_scope: str | None
) -> dict:
    """Same idempotent upsert-by-doc_id path as the bulk ingest, for a single
    internally-uploaded PDF. authority_rank is derived rather than user-chosen,
    to keep the source hierarchy consistent with the seeded documents."""
    authority_rank = 0 if doc_type == "agreement" else (3 if status == "deprecated" else 1)
    chunks = list(_chunks_for_file(path, filename, doc_type, status, account_scope, authority_rank))
    if not chunks:
        return {"chunks_ingested": 0, "source_file": filename}
    collection = get_collection()
    ids = [c["doc_id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    embeddings = _embed(texts, task_type="RETRIEVAL_DOCUMENT")
    collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return {"chunks_ingested": len(ids), "source_file": filename}


def list_documents() -> list[dict]:
    """One row per source_file, aggregated from chunk metadata already in Chroma."""
    collection = get_collection()
    all_meta = collection.get(include=["metadatas"])["metadatas"] or []
    by_file: dict[str, dict] = {}
    for meta in all_meta:
        entry = by_file.setdefault(
            meta["source_file"],
            {
                "source_file": meta["source_file"],
                "doc_type": meta["doc_type"],
                "status": meta["status"],
                "account_scope": meta["account_scope"] or None,
                "authority_rank": meta["authority_rank"],
                "chunk_count": 0,
            },
        )
        entry["chunk_count"] += 1
    return sorted(by_file.values(), key=lambda d: (d["authority_rank"], d["source_file"]))


if __name__ == "__main__":
    print(ingest())
