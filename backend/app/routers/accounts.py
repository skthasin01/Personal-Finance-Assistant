import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountOut, AccountUpdate
from app.schemas.common import Message
from app.services import account_service
from app.services.common import get_owned

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(user: CurrentUser, db: DbSession, include_inactive: bool = True):
    return account_service.list_accounts(db, user, include_inactive)


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(data: AccountCreate, user: CurrentUser, db: DbSession):
    acc = account_service.create_account(db, user, data)
    return account_service.account_out(db, user, [acc])[0]


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: uuid.UUID, user: CurrentUser, db: DbSession):
    acc = get_owned(db, Account, account_id, user.id, "Account")
    return account_service.account_out(db, user, [acc])[0]


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(account_id: uuid.UUID, data: AccountUpdate, user: CurrentUser, db: DbSession):
    acc = account_service.update_account(db, user, account_id, data)
    return account_service.account_out(db, user, [acc])[0]


@router.delete("/{account_id}", response_model=Message)
def delete_account(account_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return Message(message=account_service.delete_account(db, user, account_id))
