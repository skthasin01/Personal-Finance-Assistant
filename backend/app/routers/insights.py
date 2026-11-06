import uuid

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.notification import InsightOut, InsightUpdate
from app.services import insight_service as svc

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=list[InsightOut])
def list_insights(user: CurrentUser, db: DbSession, include_dismissed: bool = False):
    return svc.list_insights(db, user, include_dismissed)


@router.patch("/{insight_id}", response_model=InsightOut)
def update_insight(insight_id: uuid.UUID, data: InsightUpdate, user: CurrentUser, db: DbSession):
    return svc.set_dismissed(db, user, insight_id, data.is_dismissed)
