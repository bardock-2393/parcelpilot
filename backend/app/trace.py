import json
import re
import time

from app.db import session_scope

# ponytail: regex-based redaction covers emails/phone-like digit runs, the PII shapes
# present in this dataset; swap for a proper PII-detection library if the data grows.
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\b\d{10,}\b")


def redact(value):
    if isinstance(value, str):
        value = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
        value = _PHONE_RE.sub("[REDACTED_NUMBER]", value)
        return value
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def log_step(
    session_id: str,
    turn_id: str,
    account_id: str | None,
    step_type: str,
    tool_name: str | None = None,
    input_data=None,
    output_data=None,
    decision: str | None = None,
) -> None:
    with session_scope() as conn:
        conn.execute(
            """INSERT INTO agent_traces (session_id, turn_id, account_id, step_type,
                   tool_name, input_json, output_json, decision, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                turn_id,
                account_id,
                step_type,
                tool_name,
                json.dumps(redact(input_data)) if input_data is not None else None,
                json.dumps(redact(output_data)) if output_data is not None else None,
                decision,
                str(time.time()),
            ),
        )


def get_trace(session_id: str) -> list[dict]:
    with session_scope() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_traces WHERE session_id = ? ORDER BY id ASC", (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]
