# Taka Wise — AI-Powered Personal Finance Assistant

A multi-user personal finance web app: accounts (cash, bank, bKash, Nagad…), income/expense/transfer/refund
records, monthly budgets, bills, savings goals, analytics with CSV export, notifications, and an AI assistant
that explains **your own verified figures**.

| Layer | Stack |
|---|---|
| Frontend | React 18 + Vite, Tailwind CSS v4, React Router, Axios, Recharts, Context API |
| Backend | Python FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL (`NUMERIC(14,2)` for money). SQLite works for local tests/dev |
| Auth | JWT access token (memory only) + rotating refresh token in an HttpOnly cookie, Argon2id passwords |
| AI | Provider abstraction: `local` (rule-based, nothing leaves the server) or `anthropic` (Claude) |

Design decisions, ledger rules, diagrams, and the security plan are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 1. Prerequisites

- Python 3.12+ (3.13 used in development)
- Node.js 20+
- PostgreSQL 14+ (you have PostgreSQL 18 installed as a Windows service)

## 2. Backend setup

```bash
cd backend
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # Windows (Git Bash / PowerShell)
# macOS/Linux: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

### Configure `.env`

A development `backend/.env` already exists. It currently points to **SQLite** (`dev.db`) because the
PostgreSQL password was not available while building. To use PostgreSQL (the agreed database):

1. Create the database (you will be asked for the `postgres` password):

   ```bash
   "C:/Program Files/PostgreSQL/18/bin/createdb.exe" -U postgres -h localhost finance_db
   ```

2. In `backend/.env`, replace the `DATABASE_URL` line with:

   ```
   DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/finance_db
   ```

3. Apply migrations:

   ```bash
   cd backend
   .venv/Scripts/alembic upgrade head
   ```

All settings are documented in [backend/.env.example](backend/.env.example). Never commit `.env`.

### Run the API

```bash
cd backend
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/api/v1/health
- Interactive API docs (development only): http://localhost:8000/docs

### "Try the demo account" button

With `DEMO_MODE=true` (already set in the development `.env`), the login page shows **Try the demo
account**. Each click creates a new private workspace with sample data labelled `[Demo]` and signs in. No
shared password exists anywhere; visitors never see each other's data, and demo workspaces are deleted after
`DEMO_TTL_HOURS` (default 24). Keep `DEMO_MODE=false` in production unless you want a public demo.

### Optional: demo data for your own account

Adds records prefixed with **[Demo]** to an existing user (refuses to run in production):

```bash
cd backend
.venv/Scripts/python -m scripts.seed_demo you@example.com
```

## 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to `http://127.0.0.1:8000`, so the browser
sees one origin and the HttpOnly refresh cookie works. See [frontend/.env.example](frontend/.env.example).

## 4. Tests

```bash
cd backend
.venv/Scripts/python -m pytest -q
```

```bash
cd frontend
npm test
```

Backend tests use a temporary SQLite database by default. To run the same suite on PostgreSQL, create an
empty `finance_test` database and set `TEST_DATABASE_URL=postgresql+psycopg://postgres:PASS@localhost:5432/finance_test`.

Current status: **37 backend tests** and **11 frontend tests** pass. They cover the acceptance criteria in the
brief (§14): auth and refresh rotation, cross-user isolation (404s), transfers excluded from totals,
pay-once bills, refunds reducing expenses, budget usage matching transactions, goal progress from the ledger,
zero/empty states, AI grounding and consent, and no secrets in responses.

## 5. Using the AI assistant

- Default `LLM_PROVIDER=local`: a deterministic assistant that explains backend-calculated figures. No data
  leaves your server and no consent prompt is needed.
- To use Claude, set in `backend/.env`:

  ```
  LLM_PROVIDER=anthropic
  ANTHROPIC_API_KEY=your-key
  ANTHROPIC_MODEL=claude-opus-5-5
  ```

  Users must then give explicit consent (prompted on the AI page; revocable in Settings) before any financial
  summary is sent. Only minimised aggregates are sent: never names, emails, passwords, tokens, or transaction
  descriptions. The model has no tools: it cannot move money or change records.

## 6. API quick reference

Base path `/api/v1`. Every private endpoint needs `Authorization: Bearer <access_token>`.

```bash
# Register (returns access token; sets HttpOnly refresh cookie)
curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" \
  -d '{"full_name":"Rahim Uddin","email":"rahim@example.com","password":"secret123"}'

# Record an expense (amounts are strings with up to 2 decimals)
curl -X POST http://localhost:8000/api/v1/transactions -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"transaction_type":"expense","account_id":"<uuid>","category_id":"<uuid>","amount":"450.00","transaction_date":"2026-11-06"}'

# Transfer between own accounts (not income/expense)
curl -X POST http://localhost:8000/api/v1/transactions/transfers -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"from_account_id":"<uuid>","to_account_id":"<uuid>","amount":"5000","transaction_date":"2026-11-06"}'

# Pay a bill once (creates exactly one linked expense)
curl -X POST http://localhost:8000/api/v1/bills/<bill_id>/pay -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"account_id":"<uuid>"}'

# Monthly summary (defaults to the current month in the user's timezone)
curl http://localhost:8000/api/v1/analytics/summary -H "Authorization: Bearer $TOKEN"
```

Full endpoint list: [docs/ARCHITECTURE.md#api](docs/ARCHITECTURE.md#api), or `/docs` while running.

Errors always look like `{"error": {"code": "...", "message": "...", "details": ...}}`. Records owned by
another user return **404**, so their existence is never revealed.

## 7. Manual test checklist

1. Register → you land on an empty dashboard with "no data" guidance.
2. Accounts: add a bank and a bKash account with opening balances.
3. Transactions: add income and expenses; add a transfer → balances move, dashboard income/expense don't.
4. Refund part of an expense → net expenses drop; income is unchanged.
5. Budgets: create an overall and a category budget; overspend → warning/exceeded badges and notifications.
6. Bills: add a monthly bill, mark it paid → one expense appears; paying again is refused; the next bill is created.
7. Savings: create a goal, add contributions (optionally as a transfer) → progress updates; expenses unchanged.
8. Analytics: switch periods, export CSV.
9. AI assistant: ask "Am I over budget anywhere?" → the answer quotes the same figures as the dashboard.
10. Open a second browser profile, register another user, confirm you can't see the first user's data.
11. Settings: change timezone/threshold, toggle AI consent, delete the account (password required).

## 8. Production notes

- Set `ENVIRONMENT=production`, a strong `JWT_SECRET_KEY` (32+ chars), `COOKIE_SECURE=true`, a real
  `CORS_ORIGINS`, and serve over HTTPS. The app refuses to start in production with a weak secret or
  insecure cookies. `/docs` is disabled in production.
- Run `alembic upgrade head` on deploy; never rely on `create_all`.
- Build the frontend with `npm run build` and serve `frontend/dist` from the same origin as the API (or a
  reverse proxy that maps `/api` to FastAPI) so the refresh cookie stays first-party.
- The rate limiter is in-memory (single process). Use Redis-backed limits if you run multiple workers.
- Back up PostgreSQL regularly (`pg_dump`). Deleting a user removes all of their data immediately.
