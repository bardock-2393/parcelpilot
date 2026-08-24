import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.db import init_db, session_scope
from app.ingest import ingest
from app.routers import auth, chat, ops
from app.seed import seed

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ParcelPilot AI Support Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # locked to the actual deployed frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(ops.router)


@app.on_event("startup")
def startup() -> None:
    init_db()
    with session_scope() as conn:
        count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    if count == 0:
        logging.info("No accounts found -- seeding structured data from the data pack.")
        seed()
    try:
        from app.ingest import get_collection

        if get_collection().count() == 0:
            logging.info("Vector store empty -- running document ingestion.")
            ingest()
    except Exception:
        logging.exception("Document ingestion skipped/failed at startup (run `python -m app.ingest` manually).")


@app.get("/api/health")
def health():
    return {"status": "ok"}
