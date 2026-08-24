from datetime import datetime

from app.config import SNAPSHOT_TIME

_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in _FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized datetime format: {value!r}")


def snapshot_now() -> datetime:
    """Reference 'now' for all SLA/time-based logic: the data pack's stated snapshot
    time, not the wall clock -- the workbook's data is frozen at this instant."""
    dt = parse_dt(SNAPSHOT_TIME)
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt
