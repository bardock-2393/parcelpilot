import asyncio
import sqlite3
from contextlib import contextmanager

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    plan TEXT NOT NULL,
    status TEXT NOT NULL,
    csm TEXT,
    contract_file TEXT,
    premium_support INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    carrier TEXT,
    status TEXT,
    booked_at TEXT,
    pickup_window_start TEXT,
    pickup_window_end TEXT,
    pickup_actual_at TEXT,
    shipment_fee_inr REAL,
    carrier_fault INTEGER,
    customer_fault INTEGER,
    cancellation_requested_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    created_at TEXT,
    status TEXT,
    subject TEXT,
    description TEXT,
    channel TEXT,
    assigned_to TEXT,
    last_customer_message_at TEXT,
    historical_resolution TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    account_id TEXT,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS escalation_drafts (
    token TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    account_id TEXT,
    payload_json TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS escalations (
    escalation_id TEXT PRIMARY KEY,
    account_id TEXT,
    session_id TEXT,
    ticket_id TEXT,
    action_type TEXT,
    reason TEXT,
    summary TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    account_id TEXT,
    step_type TEXT NOT NULL,
    tool_name TEXT,
    input_json TEXT,
    output_json TEXT,
    decision TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS flagged_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT UNIQUE NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    summary TEXT NOT NULL,
    affected_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def session_scope():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


async def run_db(fn, *args, **kwargs):
    """Run a blocking sqlite operation off the event loop."""
    return await asyncio.to_thread(fn, *args, **kwargs)
