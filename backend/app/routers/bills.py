import uuid
from datetime import date

from fastapi import APIRouter, Query, status
from pydantic import BaseModel

from app.core.dependencies import CurrentUser, DbSession
from app.models.bill import Bill
from app.schemas.bill import BillCreate, BillOut, BillPay, BillUpdate
from app.schemas.common import Message, Page
from app.schemas.transaction import TransactionOut
from app.services import bill_service as svc
from app.services import transaction_service
from app.services.common import get_owned

router = APIRouter(prefix="/bills", tags=["bills"])


class BillPayOut(BaseModel):
    bill: BillOut
    transaction: TransactionOut
    next_bill: BillOut | None


@router.get("", response_model=Page[BillOut])
def list_bills(user: CurrentUser, db: DbSession, status: str | None = None,
               page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
               start_date: date | None = None, end_date: date | None = None):
    return svc.list_bills(db, user, status=status, page=page, page_size=page_size,
                          start_date=start_date, end_date=end_date)


@router.post("", response_model=BillOut, status_code=status.HTTP_201_CREATED)
def create_bill(data: BillCreate, user: CurrentUser, db: DbSession):
    return svc.to_out(db, user, svc.create_bill(db, user, data), with_comparison=True)


@router.get("/{bill_id}", response_model=BillOut)
def get_bill(bill_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return svc.to_out(db, user, get_owned(db, Bill, bill_id, user.id, "Bill"), with_comparison=True)


@router.patch("/{bill_id}", response_model=BillOut)
def update_bill(bill_id: uuid.UUID, data: BillUpdate, user: CurrentUser, db: DbSession):
    return svc.to_out(db, user, svc.update_bill(db, user, bill_id, data), with_comparison=True)


@router.delete("/{bill_id}", response_model=Message)
def delete_bill(bill_id: uuid.UUID, user: CurrentUser, db: DbSession):
    svc.delete_bill(db, user, bill_id)
    return Message(message="Bill deleted")


@router.post("/{bill_id}/pay", response_model=BillPayOut)
def pay_bill(bill_id: uuid.UUID, data: BillPay, user: CurrentUser, db: DbSession):
    bill, next_bill = svc.pay_bill(db, user, bill_id, data)
    tx = transaction_service.get_transaction(db, user, bill.payment_transaction_id)
    return BillPayOut(bill=svc.to_out(db, user, bill), transaction=tx,
                      next_bill=svc.to_out(db, user, next_bill) if next_bill else None)
