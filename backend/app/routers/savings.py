import uuid
from typing import Literal

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.common import Message
from app.schemas.savings_goal import ContributionCreate, ContributionOut, GoalCreate, GoalDetailOut, GoalOut, GoalUpdate
from app.services import savings_service as svc

router = APIRouter(prefix="/savings-goals", tags=["savings goals"])


@router.get("", response_model=list[GoalOut])
def list_goals(user: CurrentUser, db: DbSession, status: Literal["active", "completed", "cancelled"] | None = None):
    return svc.list_goals(db, user, status)


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(data: GoalCreate, user: CurrentUser, db: DbSession):
    return svc.to_out(db, user, [svc.create_goal(db, user, data)])[0]


@router.get("/{goal_id}", response_model=GoalDetailOut)
def get_goal(goal_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return svc.get_goal_detail(db, user, goal_id)


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: uuid.UUID, data: GoalUpdate, user: CurrentUser, db: DbSession):
    return svc.to_out(db, user, [svc.update_goal(db, user, goal_id, data)])[0]


@router.delete("/{goal_id}", response_model=Message)
def delete_goal(goal_id: uuid.UUID, user: CurrentUser, db: DbSession):
    svc.delete_goal(db, user, goal_id)
    return Message(message="Savings goal deleted")


@router.post("/{goal_id}/contributions", response_model=ContributionOut, status_code=status.HTTP_201_CREATED)
def add_contribution(goal_id: uuid.UUID, data: ContributionCreate, user: CurrentUser, db: DbSession):
    return svc.add_contribution(db, user, goal_id, data)


@router.delete("/{goal_id}/contributions/{contribution_id}", response_model=Message)
def delete_contribution(goal_id: uuid.UUID, contribution_id: uuid.UUID, user: CurrentUser, db: DbSession):
    svc.delete_contribution(db, user, goal_id, contribution_id)
    return Message(message="Contribution deleted")
