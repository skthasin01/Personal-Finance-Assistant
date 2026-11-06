"""Add clearly-labelled DEMO data to an existing user, for local testing only.

Usage (from backend/):
    python -m scripts.seed_demo you@example.com

Every demo record starts with "[Demo]" so it is never mistaken for real data.
Refuses to run in production. (The login page's "Try the demo" button uses the
same seed data via app/services/demo_service.py.)
"""
import sys

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.config import get_settings
from app.database.connection import SessionLocal
from app.models.user import User
from app.services.demo_service import seed_demo_data


def main(email: str) -> None:
    if get_settings().is_production:
        sys.exit("Refusing to seed demo data in production.")
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email.strip().lower())).first()
        if user is None:
            sys.exit(f"No user with email {email}. Register first.")
        seed_demo_data(db, user)
    print("Demo data added (all records are prefixed with [Demo]).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m scripts.seed_demo <email>")
    main(sys.argv[1])
