"""A user can never read, update or delete another user's data (404, not 403)."""
from datetime import date

from tests.conftest import cash_account, category_id

API = "/api/v1"
D = date.today().isoformat()


def test_cross_user_access_denied(client, make_user):
    alice = make_user("alice@example.com", "Alice")
    bob = make_user("bob@example.com", "Bob")

    a_cash = cash_account(client, alice)
    a_food = category_id(client, alice, "Food & Dining")
    tx = client.post(f"{API}/transactions", headers=alice, json={
        "transaction_type": "expense", "account_id": a_cash, "category_id": a_food, "amount": "100",
        "transaction_date": D}).json()
    bill = client.post(f"{API}/bills", headers=alice, json={
        "title": "Rent", "bill_type": "rent", "amount": "15000", "due_date": D}).json()
    goal = client.post(f"{API}/savings-goals", headers=alice, json={"title": "Laptop", "target_amount": "80000"}).json()
    budget = client.post(f"{API}/budgets", headers=alice, json={
        "limit_amount": "1000", "month": date.today().month, "year": date.today().year}).json()
    conv = client.post(f"{API}/ai/conversations", headers=alice, json={}).json()

    private = [f"/accounts/{a_cash}", f"/transactions/{tx['id']}", f"/bills/{bill['id']}",
               f"/savings-goals/{goal['id']}", f"/budgets/{budget['id']}", f"/ai/conversations/{conv['id']}"]
    for path in private:
        assert client.get(API + path, headers=bob).status_code == 404, path
        assert client.delete(API + path, headers=bob).status_code == 404, path
    assert client.patch(f"{API}/transactions/{tx['id']}", headers=bob, json={"amount": "1"}).status_code == 404
    assert client.patch(f"{API}/categories/{a_food}", headers=bob, json={"name": "x"}).status_code == 404
    assert client.post(f"{API}/bills/{bill['id']}/pay", headers=bob,
                       json={"account_id": cash_account(client, bob)}).status_code == 404
    assert client.post(f"{API}/ai/conversations/{conv['id']}/messages", headers=bob,
                       json={"content": "hi"}).status_code == 404

    # Bob cannot use Alice's account or category in his own records
    r = client.post(f"{API}/transactions", headers=bob, json={
        "transaction_type": "expense", "account_id": a_cash, "category_id": a_food, "amount": "1",
        "transaction_date": D})
    assert r.status_code == 404
    r = client.post(f"{API}/transactions", headers=bob, json={
        "transaction_type": "refund", "account_id": cash_account(client, bob), "amount": "1", "transaction_date": D,
        "related_transaction_id": tx["id"]})
    assert r.status_code == 404
    r = client.post(f"{API}/transactions/transfers", headers=bob, json={
        "from_account_id": cash_account(client, bob), "to_account_id": a_cash, "amount": "1", "transaction_date": D})
    assert r.status_code == 404

    # lists contain only own data
    assert client.get(f"{API}/transactions", headers=bob).json()["total"] == 0
    assert client.get(f"{API}/bills", headers=bob).json()["total"] == 0
    assert client.get(f"{API}/savings-goals", headers=bob).json() == []
    assert client.get(f"{API}/ai/conversations", headers=bob).json() == []
    assert client.get(f"{API}/analytics/summary", headers=bob).json()["current"]["expense"] == "0.00"

    # Alice's data still intact
    assert client.get(f"{API}/transactions/{tx['id']}", headers=alice).status_code == 200
