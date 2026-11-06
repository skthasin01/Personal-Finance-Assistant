"""One-click demo workspaces."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.database.connection import SessionLocal
from app.models.user import User
from app.services import demo_service

API = "/api/v1"


def test_demo_disabled_by_default(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    assert client.get(f"{API}/auth/demo").json()["enabled"] is False
    assert client.post(f"{API}/auth/demo").status_code == 404


def test_demo_login_creates_private_seeded_workspace(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "demo_mode", True)
    assert client.get(f"{API}/auth/demo").json()["enabled"] is True

    r1 = client.post(f"{API}/auth/demo")
    assert r1.status_code == 201, r1.text
    assert r1.json()["user"]["is_demo"] is True
    assert client.cookies.get("refresh_token")  # signed in with a session cookie
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    h2 = {"Authorization": f"Bearer {client.post(f'{API}/auth/demo').json()['access_token']}"}

    # Seeded data is present and labelled, and figures are consistent
    accounts = client.get(f"{API}/accounts", headers=h1).json()
    assert any(a["name"] == "[Demo] City Bank" for a in accounts)
    s = client.get(f"{API}/analytics/summary", headers=h1).json()
    assert s["has_data"] is True and s["current"]["refunds"] == "1200.00"
    assert client.get(f"{API}/bills?status=overdue", headers=h1).json()["total"] == 1

    # Two demo visitors never see each other's records
    tx_id = client.get(f"{API}/transactions", headers=h1).json()["items"][0]["id"]
    assert client.get(f"{API}/transactions/{tx_id}", headers=h2).status_code == 404


def test_expired_demo_users_are_purged(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "demo_mode", True)
    client.post(f"{API}/auth/demo")
    with SessionLocal() as db:
        old = db.scalars(select(User).where(User.is_demo.is_(True))).first()
        old.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        db.commit()
        assert demo_service.purge_expired_demo_users(db) == 1
        assert db.scalars(select(User).where(User.is_demo.is_(True))).first() is None
