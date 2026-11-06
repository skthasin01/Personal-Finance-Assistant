import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.budget import BudgetCreate, BudgetOut, BudgetUpdate
from app.schemas.common import Message
from app.services import budget_service as svc

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetOut])
def list_budgets(user: CurrentUser, db: DbSession, month: int | None = Query(None, ge=1, le=12),
                 year: int | None = Query(None, ge=2000, le=2100)):
    return svc.list_budgets(db, user, month, year)


@router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(data: BudgetCreate, user: CurrentUser, db: DbSession):
    return svc.create_budget(db, user, data)


@router.get("/{budget_id}", response_model=BudgetOut)
def get_budget(budget_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return svc.get_budget(db, user, budget_id)


@router.patch("/{budget_id}", response_model=BudgetOut)
def update_budget(budget_id: uuid.UUID, data: BudgetUpdate, user: CurrentUser, db: DbSession):
    return svc.update_budget(db, user, budget_id, data)


@router.delete("/{budget_id}", response_model=Message)
def delete_budget(budget_id: uuid.UUID, user: CurrentUser, db: DbSession):
    svc.delete_budget(db, user, budget_id)
    return Message(message="Budget deleted")
