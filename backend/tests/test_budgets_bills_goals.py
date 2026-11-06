from datetime import date, timedelta

from tests.conftest import cash_account, category_id

API = "/api/v1"
TODAY = date.today()
D = TODAY.replace(day=1).isoformat()


def _expense(client, h, cat, amount):
    r = client.post(f"{API}/transactions", headers=h, json={
        "transaction_type": "expense", "account_id": cash_account(client, h), "category_id": category_id(client, h, cat),
        "amount": amount, "transaction_date": D})
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- budgets
def test_budget_usage_matches_transactions(client, auth):
    food = category_id(client, auth, "Food & Dining")
    r = client.post(f"{API}/budgets", headers=auth, json={"category_id": food, "limit_amount": "5000",
                                                          "month": TODAY.month, "year": TODAY.year})
    assert r.status_code == 201
    overall = client.post(f"{API}/budgets", headers=auth, json={"limit_amount": "20000", "month": TODAY.month,
                                                                "year": TODAY.year}).json()
    _expense(client, auth, "Food & Dining", "4200")
    _expense(client, auth, "Transport", "800")

    budgets = {b["category_name"] or "overall": b for b in
               client.get(f"{API}/budgets?month={TODAY.month}&year={TODAY.year}", headers=auth).json()}
    assert budgets["Food & Dining"]["spent_amount"] == "4200.00"
    assert budgets["Food & Dining"]["utilization_percent"] == "84.0"
    assert budgets["Food & Dining"]["status"] == "warning"
    # overall budget is independent: all net expenses, not a sum of category limits
    assert budgets["overall"]["spent_amount"] == "5000.00"
    assert budgets["overall"]["id"] == overall["id"]
    _expense(client, auth, "Food & Dining", "900")
    b = client.get(f"{API}/budgets/{budgets['Food & Dining']['id']}", headers=auth).json()
    assert b["status"] == "exceeded" and b["remaining_amount"] == "-100.00"


def test_duplicate_budgets_rejected(client, auth):
    food = category_id(client, auth, "Food & Dining")
    body = {"category_id": food, "limit_amount": "100", "month": 1, "year": 2027}
    assert client.post(f"{API}/budgets", headers=auth, json=body).status_code == 201
    assert client.post(f"{API}/budgets", headers=auth, json=body).status_code == 409
    overall = {"limit_amount": "100", "month": 1, "year": 2027}
    assert client.post(f"{API}/budgets", headers=auth, json=overall).status_code == 201
    assert client.post(f"{API}/budgets", headers=auth, json=overall).status_code == 409
    assert client.post(f"{API}/budgets", headers=auth, json={**overall, "limit_amount": "0"}).status_code == 422
    salary = category_id(client, auth, "Salary")
    assert client.post(f"{API}/budgets", headers=auth, json={**body, "category_id": salary, "month": 2}).status_code == 422


# ---------------------------------------------------------------- bills
def _bill(client, h, **kw):
    body = {"title": "DESCO Electricity", "bill_type": "electricity", "amount": "1500", "due_date": TODAY.isoformat()}
    body.update(kw)
    r = client.post(f"{API}/bills", headers=h, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_bill_paid_once_no_duplicate_expense(client, auth):
    bill = _bill(client, auth, recurrence_rule="monthly")
    cash = cash_account(client, auth)
    r = client.post(f"{API}/bills/{bill['id']}/pay", headers=auth, json={"account_id": cash})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bill"]["status"] == "paid"
    assert body["transaction"]["transaction_type"] == "expense"
    assert body["transaction"]["is_bill_payment"] is True
    assert body["next_bill"]["status"] == "pending"

    again = client.post(f"{API}/bills/{bill['id']}/pay", headers=auth, json={"account_id": cash})
    assert again.status_code == 409
    expenses = client.get(f"{API}/transactions?type=expense", headers=auth).json()
    assert expenses["total"] == 1
    assert client.get(f"{API}/analytics/summary", headers=auth).json()["current"]["expense"] == "1500.00"

    # deleting the payment puts the bill back to pending
    client.delete(f"{API}/transactions/{body['transaction']['id']}", headers=auth)
    assert client.get(f"{API}/bills/{bill['id']}", headers=auth).json()["status"] == "pending"


def test_bill_overdue_and_comparison(client, auth):
    _bill(client, auth, amount="1000", due_date=(TODAY - timedelta(days=40)).isoformat())
    current = _bill(client, auth, amount="1250", due_date=(TODAY - timedelta(days=2)).isoformat())
    assert current["display_status"] == "overdue"
    assert current["comparison"]["change_percent"] == "25.0"
    first_ever = _bill(client, auth, bill_type="water", title="WASA", amount="300")
    assert first_ever["comparison"]["previous_amount"] is None
    overdue = client.get(f"{API}/bills?status=overdue", headers=auth).json()
    assert overdue["total"] == 2


# ---------------------------------------------------------------- savings
def test_goal_progress_from_contribution_ledger(client, auth):
    bank = client.post(f"{API}/accounts", headers=auth,
                       json={"name": "Bank", "account_type": "bank", "opening_balance": "10000"}).json()["id"]
    savings = client.post(f"{API}/accounts", headers=auth,
                          json={"name": "Savings", "account_type": "savings"}).json()["id"]
    target_date = (TODAY + timedelta(days=200)).isoformat()
    goal = client.post(f"{API}/savings-goals", headers=auth,
                       json={"title": "Emergency fund", "target_amount": "6000", "target_date": target_date}).json()
    assert goal["saved_amount"] == "0.00" and goal["progress_percent"] == "0.0"

    c1 = client.post(f"{API}/savings-goals/{goal['id']}/contributions", headers=auth, json={
        "amount": "2000", "contribution_date": TODAY.isoformat(), "from_account_id": bank, "to_account_id": savings})
    assert c1.status_code == 201, c1.text
    client.post(f"{API}/savings-goals/{goal['id']}/contributions", headers=auth,
                json={"amount": "1000", "contribution_date": TODAY.isoformat()})
    detail = client.get(f"{API}/savings-goals/{goal['id']}", headers=auth).json()
    assert detail["saved_amount"] == "3000.00"
    assert detail["progress_percent"] == "50.0"
    assert sum(float(c["amount"]) for c in detail["contributions"]) == 3000
    assert detail["projection"]["required_monthly"] is not None

    # contribution transfer is not an expense
    s = client.get(f"{API}/analytics/summary", headers=auth).json()["current"]
    assert s["expense"] == "0.00"
    bal = {a["name"]: a["current_balance"] for a in client.get(f"{API}/accounts", headers=auth).json()}
    assert bal["Bank"] == "8000.00" and bal["Savings"] == "2000.00"

    # over-contribution: display capped at 100, real total preserved, goal completed
    client.post(f"{API}/savings-goals/{goal['id']}/contributions", headers=auth,
                json={"amount": "4000", "contribution_date": TODAY.isoformat()})
    g = client.get(f"{API}/savings-goals/{goal['id']}", headers=auth).json()
    assert g["progress_percent"] == "100.0" and g["saved_amount"] == "7000.00" and g["status"] == "completed"

    # the linked transfer cannot be deleted directly; deleting the contribution removes it
    tx_id = c1.json()["related_transaction_id"]
    assert client.delete(f"{API}/transactions/{tx_id}", headers=auth).status_code == 409
    assert client.delete(f"{API}/savings-goals/{goal['id']}/contributions/{c1.json()['id']}", headers=auth).status_code == 200
    bal = {a["name"]: a["current_balance"] for a in client.get(f"{API}/accounts", headers=auth).json()}
    assert bal["Bank"] == "10000.00"


# ---------------------------------------------------------------- empty/zero states
def test_empty_reports_are_safe(client, auth):
    s = client.get(f"{API}/analytics/summary", headers=auth).json()
    assert s["has_data"] is False and s["current"]["savings_rate"] is None
    assert s["income_change_percent"] is None
    assert client.get(f"{API}/analytics/trends", headers=auth).status_code == 200
    assert client.get(f"{API}/analytics/categories", headers=auth).json()["categories"] == []
    assert client.get(f"{API}/analytics/cash-flow", headers=auth).status_code == 200
    csv = client.get(f"{API}/analytics/export.csv", headers=auth)
    assert csv.status_code == 200 and "Net cash flow" in csv.text
    assert client.get(f"{API}/insights", headers=auth).status_code == 200
    assert client.get(f"{API}/notifications", headers=auth).json()["total"] == 0
    bad = client.get(f"{API}/analytics/summary?start_date=2026-05-01&end_date=2026-04-01", headers=auth)
    assert bad.status_code == 422


def test_notifications_not_duplicated(client, auth):
    _bill(client, auth, due_date=(TODAY + timedelta(days=1)).isoformat())
    first = client.get(f"{API}/notifications", headers=auth).json()
    second = client.get(f"{API}/notifications", headers=auth).json()
    assert first["total"] == second["total"] == 1
    nid = first["items"][0]["id"]
    assert client.patch(f"{API}/notifications/{nid}", headers=auth, json={"is_read": True}).json()["is_read"] is True
    assert client.get(f"{API}/notifications", headers=auth).json()["unread_count"] == 0


def test_csv_export_neutralizes_formulas(client, auth):
    client.post(f"{API}/transactions", headers=auth, json={
        "transaction_type": "expense", "account_id": cash_account(client, auth),
        "category_id": category_id(client, auth, "Shopping"), "amount": "5", "transaction_date": D,
        "description": "=HYPERLINK(\"http://evil\")"})
    text = client.get(f"{API}/analytics/export.csv", headers=auth).text
    assert "'=HYPERLINK" in text
