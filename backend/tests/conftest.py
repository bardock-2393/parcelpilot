import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.db import init_db
from app.identity import Identity
from app.ingest import get_collection, ingest
from app.seed import seed


@pytest.fixture(scope="session", autouse=True)
def _setup_data():
    init_db()
    seed()
    if get_collection().count() == 0:
        ingest()


@pytest.fixture
def northstar():
    return Identity(session_id="test-session-northstar", role="customer", account_id="ACCT-001")


@pytest.fixture
def lumenworks():
    return Identity(session_id="test-session-lumenworks", role="customer", account_id="ACCT-002")


@pytest.fixture
def internal():
    return Identity(session_id="test-session-internal", role="internal", account_id=None)
