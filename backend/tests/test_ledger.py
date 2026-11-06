"""Acceptance checks for the ledger rules in the brief (section 7 and 14)."""
from datetime import date

from tests.conftest import cash_account, category_id

API = "/api/v1"
D = date.today().replace(day=1).isoformat()  # inside the current month


def _account(client, h, name, opening="0"):
    r = client.post(f"{API}/accounts", headers=h, json={"name": name, "account_type": "bank", "opening_balance": opening})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _tx(client, h, **kw):
    r = client.post(f"{API}/transactions", headers=h, json={"transaction_date": D, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def _summary(client, h):
    return client.get(f"{API}/analytics/summary", headers=h).json()["current"]


def _balances(client, h):
    return {a["name"]: a["current_balance"] for a in client.get(f"{API}/accounts", headers=h).json()}


def test_income_expense_balance_and_totals(client, auth):
    bank = _account(client, auth, "City Bank", "1000.00")
    _tx(client, auth, transaction_type="income", account_id=bank, category_id=category_id(client, auth, "Salary"),
        amount="50000.00")
    _tx(client, auth, transaction_type="expense", account_id=bank, category_id=category_id(client, auth, "Groceries"),
        amount="12500.50")
    s = _summary(client, auth)
    assert s["income"] == "50000.00"
    assert s["expense"] == "12500.50"
    assert s["net_cash_flow"] == "37499.50"
    assert s["savings_rate"] == "75.0"
    assert _balances(client, auth)["City Bank"] == "38499.50"


def test_transfer_moves_balance_but_not_totals(client, auth):
    bank = _account(client, auth, "Bank", "5000.00")
    cash = cash_account(client, auth)
    before = _summary(client, auth)
    r = client.post(f"{API}/transactions/transfers", headers=auth,
                    json={"from_account_id": bank, "to_account_id": cash, "amount": "1200.00", "transaction_date": D})
    assert r.status_code == 201, r.text
    after = _summary(client, auth)
    assert before["income"] == after["income"] == "0.00"
    assert before["expense"] == after["expense"] == "0.00"
    assert after["savings_rate"] is None
    b = _balances(client, auth)
    assert b["Bank"] == "3800.00" and b["Cash"] == "1200.00"

    # deleting one leg deletes the whole transfer
    client.delete(f"{API}/transactions/{r.json()['outgoing']['id']}", headers=auth)
    b = _balances(client, auth)
    assert b["Bank"] == "5000.00" and b["Cash"] == "0.00"


def test_transfer_same_account_rejected(client, auth):
    cash = cash_account(client, auth)
    r = client.post(f"{API}/transactions/transfers", headers=auth,
                    json={"from_account_id": cash, "to_account_id": cash, "amount": "10", "transaction_date": D})
    assert r.status_code == 422


def test_refund_reduces_expense_not_income(client, auth):
    cash = cash_account(client, auth)
    shop = category_id(client, auth, "Shopping")
    exp = _tx(client, auth, transaction_type="expense", account_id=cash, category_id=shop, amount="3000.00")
    _tx(client, auth, transaction_type="income", account_id=cash, category_id=category_id(client, auth, "Salary"),
        amount="10000.00")
    refund = _tx(client, auth, transaction_type="refund", account_id=cash, amount="1000.00",
                 related_transaction_id=exp["id"])
    assert refund["category_id"] == shop
    s = _summary(client, auth)
    assert s["income"] == "10000.00"
    assert s["gross_expense"] == "3000.00"
    assert s["refunds"] == "1000.00"
    assert s["expense"] == "2000.00"
    assert _balances(client, auth)["Cash"] == "8000.00"

    # cannot refund more than remains
    r = client.post(f"{API}/transactions", headers=auth, json={
        "transaction_type": "refund", "account_id": cash, "amount": "2000.01", "transaction_date": D,
        "related_transaction_id": exp["id"]})
    assert r.status_code == 422
    # expense with refunds cannot be deleted
    assert client.delete(f"{API}/transactions/{exp['id']}", headers=auth).status_code == 409
    # category breakdown nets the refund
    cats = client.get(f"{API}/analytics/categories", headers=auth).json()["categories"]
    assert next(c for c in cats if c["name"] == "Shopping")["amount"] == "2000.00"


def test_validation_category_type_and_amount(client, auth):
    cash = cash_account(client, auth)
    r = client.post(f"{API}/transactions", headers=auth, json={
        "transaction_type": "income", "account_id": cash, "category_id": category_id(client, auth, "Groceries"),
        "amount": "10", "transaction_date": D})
    assert r.status_code == 422
    for bad in ("0", "-5", "1.234"):
        r = client.post(f"{API}/transactions", headers=auth, json={
            "transaction_type": "expense", "account_id": cash, "category_id": category_id(client, auth, "Groceries"),
            "amount": bad, "transaction_date": D})
        assert r.status_code == 422, bad


def test_list_filters_search_pagination(client, auth):
    cash = cash_account(client, auth)
    food = category_id(client, auth, "Food & Dining")
    for i in range(25):
        _tx(client, auth, transaction_type="expense", account_id=cash, category_id=food, amount=str(10 + i),
            description=f"lunch {i}" if i % 2 else f"dinner {i}")
    page = client.get(f"{API}/transactions?page=2&page_size=10&sort=amount_desc", headers=auth).json()
    assert page["total"] == 25 and page["pages"] == 3 and len(page["items"]) == 10
    assert page["items"][0]["amount"] == "24.00"
    found = client.get(f"{API}/transactions?search=lunch", headers=auth).json()
    assert found["total"] == 12
    assert client.get(f"{API}/transactions?page_size=500", headers=auth).status_code == 422


def test_account_delete_soft_when_used(client, auth):
    bank = _account(client, auth, "Old Bank")
    _tx(client, auth, transaction_type="expense", account_id=bank, category_id=category_id(client, auth, "Travel"),
        amount="5")
    r = client.delete(f"{API}/accounts/{bank}", headers=auth)
    assert "deactivated" in r.json()["message"]
    acc = client.get(f"{API}/accounts/{bank}", headers=auth).json()
    assert acc["is_active"] is False
    empty = _account(client, auth, "Unused")
    assert client.delete(f"{API}/accounts/{empty}", headers=auth).json()["message"] == "Account deleted."


def test_weekly_trend_buckets_stay_inside_period(client, auth):
    r = client.get(f"{API}/analytics/trends?granularity=week&start_date=2026-11-01&end_date=2026-11-30", headers=auth)
    assert r.status_code == 200
    starts = [p["start_date"] for p in r.json()["points"]]
    assert starts[0] == "2026-11-01" and all(s >= "2026-11-01" for s in starts)
