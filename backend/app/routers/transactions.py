import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.common import Message, Page
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate, TransferCreate, TransferOut
from app.services import transaction_service as svc

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=Page[TransactionOut])
def list_transactions(
    user: CurrentUser, db: DbSession,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    sort: Literal["date_desc", "date_asc", "amount_desc", "amount_asc"] = "date_desc",
    search: str | None = Query(None, max_length=100),
    start_date: date | None = None, end_date: date | None = None,
    account_id: uuid.UUID | None = None, category_id: uuid.UUID | None = None,
    type: Literal["income", "expense", "transfer", "refund"] | None = None,
):
    return svc.list_transactions(db, user, page=page, page_size=page_size, sort=sort, search=search,
                                 start_date=start_date, end_date=end_date, account_id=account_id,
                                 category_id=category_id, transaction_type=type)


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(data: TransactionCreate, user: CurrentUser, db: DbSession):
    tx = svc.create_transaction(db, user, data)
    return svc.to_out(db, [tx])[0]


@router.post("/transfers", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def create_transfer(data: TransferCreate, user: CurrentUser, db: DbSession):
    out_leg, in_leg = svc.create_transfer(db, user, data)
    outs = svc.to_out(db, [out_leg, in_leg])
    return TransferOut(transfer_group_id=out_leg.transfer_group_id, outgoing=outs[0], incoming=outs[1])


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return svc.get_transaction(db, user, transaction_id)


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(transaction_id: uuid.UUID, data: TransactionUpdate, user: CurrentUser, db: DbSession):
    tx = svc.update_transaction(db, user, transaction_id, data)
    return svc.to_out(db, [tx])[0]


@router.delete("/{transaction_id}", response_model=Message)
def delete_transaction(transaction_id: uuid.UUID, user: CurrentUser, db: DbSession):
    svc.delete_transaction(db, user, transaction_id)
    return Message(message="Transaction deleted")
