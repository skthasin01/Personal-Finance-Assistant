# Backend (FastAPI)

Setup, configuration, and run/test commands are in the [project README](../README.md). The design and
business rules are in [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

```bash
.venv/Scripts/alembic upgrade head                     # apply migrations
.venv/Scripts/python -m uvicorn app.main:app --reload  # run on :8000
.venv/Scripts/python -m pytest -q                      # tests
```

Layout: `app/routers` (HTTP) → `app/schemas` (validation) → `app/services` (business rules, ownership) →
`app/models` (SQLAlchemy). New migrations: `alembic revision --autogenerate -m "message"`.
