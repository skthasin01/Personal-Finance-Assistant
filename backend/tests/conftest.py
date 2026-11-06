"""Test setup.

By default tests run against a throwaway SQLite database so they work without a
PostgreSQL server. Set TEST_DATABASE_URL to run the same suite on PostgreSQL:
    TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/finance_test pytest
"""
import os
import tempfile
import warnings

_tmpdir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmpdir}/test.db")
os.environ["ENVIRONMENT"] = "test"
os.environ["LLM_PROVIDER"] = "local"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["AI_RATE_LIMIT_PER_MINUTE"] = "1000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app.database.base import Base  # noqa: E402
from app.database.connection import engine  # noqa: E402
from app.main import app  # noqa: E402
import app.models as _models  # noqa: E402,F401  (registers all tables)

warnings.filterwarnings("ignore", message=".*Dialect sqlite.*does \\*not\\* support Decimal.*")

if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


@pytest.fixture(autouse=True)
def fresh_db():
    sqlite = engine.dialect.name == "sqlite"
    with engine.connect() as conn:
        if sqlite:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(conn)
        conn.commit()
        if sqlite:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    from app.core.dependencies import ai_limiter, auth_limiter
    auth_limiter.reset()
    ai_limiter.reset()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def register(client: TestClient, email="alice@example.com", password="secret123", name="Alice") -> dict:
    r = client.post("/api/v1/auth/register", json={"full_name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register(client)


@pytest.fixture
def make_user(client):
    def _make(email, name="User"):
        # separate cookie jar per user is not needed: bearer headers identify the user
        return register(client, email=email, name=name)
    return _make


def category_id(client, headers, name):
    cats = client.get("/api/v1/categories", headers=headers).json()
    return next(c["id"] for c in cats if c["name"] == name)


def cash_account(client, headers):
    return next(a["id"] for a in client.get("/api/v1/accounts", headers=headers).json() if a["name"] == "Cash")
