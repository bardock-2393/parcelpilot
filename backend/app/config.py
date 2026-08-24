import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR.parent / "data"))
DB_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "parcelpilot.db"))
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", BASE_DIR / "chroma_db"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "uploads"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

# Reference "now" for all time-based logic, per the assessment workbook's README snapshot.
# ponytail: hardcoded from the data pack's README sheet; re-read it if the data pack changes.
SNAPSHOT_TIME = os.environ.get("SNAPSHOT_TIME", "2026-08-16T11:00:00+05:30")

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

TOKEN_SECRET = os.environ.get("TOKEN_SECRET", "dev-insecure-secret-change-me")
MAX_TOOL_CALLS_PER_TURN = int(os.environ.get("MAX_TOOL_CALLS_PER_TURN", "8"))
ESCALATION_RATE_LIMIT = int(os.environ.get("ESCALATION_RATE_LIMIT", "5"))
ESCALATION_RATE_WINDOW_SECONDS = int(os.environ.get("ESCALATION_RATE_WINDOW_SECONDS", "60"))
CONFIRMATION_TOKEN_TTL_SECONDS = int(os.environ.get("CONFIRMATION_TOKEN_TTL_SECONDS", "900"))
