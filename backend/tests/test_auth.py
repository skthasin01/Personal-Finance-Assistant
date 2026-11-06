from tests.conftest import register

API = "/api/v1"
CSRF = {"X-Requested-With": "XMLHttpRequest"}


def test_register_login_me_refresh_logout(client):
    headers = register(client)
    me = client.get(f"{API}/auth/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "alice@example.com"
    assert body["currency_code"] == "BDT"
    assert "password_hash" not in body

    # default categories + Cash account seeded
    assert len(client.get(f"{API}/categories", headers=headers).json()) >= 10
    assert client.get(f"{API}/accounts", headers=headers).json()[0]["name"] == "Cash"

    r = client.post(f"{API}/auth/login", json={"email": "ALICE@example.com", "password": "secret123"})
    assert r.status_code == 200
    assert "refresh_token" in r.cookies or client.cookies.get("refresh_token")

    old_cookie = client.cookies.get("refresh_token")
    r = client.post(f"{API}/auth/refresh", headers=CSRF)
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]
    new_cookie = client.cookies.get("refresh_token")
    assert new_cookie and new_cookie != old_cookie

    # reusing the rotated (old) token is rejected and revokes the family
    client.cookies.set("refresh_token", old_cookie, path="/api/v1/auth")
    assert client.post(f"{API}/auth/refresh", headers=CSRF).status_code == 401
    client.cookies.set("refresh_token", new_cookie, path="/api/v1/auth")
    assert client.post(f"{API}/auth/refresh", headers=CSRF).status_code == 401


def test_refresh_requires_csrf_header(client):
    register(client)
    assert client.post(f"{API}/auth/refresh").status_code == 403


def test_logout_revokes_refresh(client):
    register(client)
    assert client.post(f"{API}/auth/logout", headers=CSRF).status_code == 200
    assert client.post(f"{API}/auth/refresh", headers=CSRF).status_code == 401


def test_duplicate_email_and_generic_login_error(client):
    register(client)
    r = client.post(f"{API}/auth/register", json={"full_name": "A", "email": "alice@example.com", "password": "x"})
    assert r.status_code == 422  # validation (short name/password) first
    r = client.post(f"{API}/auth/register",
                    json={"full_name": "Alice B", "email": "alice@example.com", "password": "another123"})
    assert r.status_code == 409

    wrong_pw = client.post(f"{API}/auth/login", json={"email": "alice@example.com", "password": "nope12345"})
    no_user = client.post(f"{API}/auth/login", json={"email": "ghost@example.com", "password": "nope12345"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json()["error"]["message"] == no_user.json()["error"]["message"]


def test_weak_password_rejected(client):
    r = client.post(f"{API}/auth/register", json={"full_name": "Bob", "email": "b@example.com", "password": "abcdefgh"})
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "password"


def test_protected_routes_need_token(client):
    assert client.get(f"{API}/accounts").status_code == 401
    assert client.get(f"{API}/accounts", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_profile_update_and_delete(client, auth):
    r = client.patch(f"{API}/users/me", headers=auth, json={"timezone": "Asia/Dhaka", "currency_code": "usd",
                                                            "ai_consent": True})
    assert r.status_code == 200
    assert r.json()["currency_code"] == "USD" and r.json()["ai_consent"] is True
    assert client.patch(f"{API}/users/me", headers=auth, json={"timezone": "Mars/Base"}).status_code == 422

    assert client.request("DELETE", f"{API}/users/me", headers=auth, json={"password": "wrong"}).status_code == 401
    assert client.request("DELETE", f"{API}/users/me", headers=auth, json={"password": "secret123"}).status_code == 200
    assert client.get(f"{API}/auth/me", headers=auth).status_code == 401
