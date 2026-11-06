from datetime import date
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.analytics import CashFlowOut, CategoriesOut, SummaryOut, TrendsOut
from app.services import analytics_service as svc

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=SummaryOut)
def summary(user: CurrentUser, db: DbSession, start_date: date | None = None, end_date: date | None = None):
    """Totals for the period (default: current month in the user's timezone) and the previous period."""
    return svc.summary(db, user, start_date, end_date)


@router.get("/trends", response_model=TrendsOut)
def trends(user: CurrentUser, db: DbSession, start_date: date | None = None, end_date: date | None = None,
           granularity: Literal["day", "week", "month"] = "month", months: int = Query(6, ge=1, le=24)):
    return svc.trends(db, user, start_date, end_date, granularity, months)


@router.get("/categories", response_model=CategoriesOut)
def categories(user: CurrentUser, db: DbSession, start_date: date | None = None, end_date: date | None = None,
               type: Literal["income", "expense"] = "expense"):
    return svc.categories(db, user, start_date, end_date, type)


@router.get("/cash-flow", response_model=CashFlowOut)
def cash_flow(user: CurrentUser, db: DbSession, start_date: date | None = None, end_date: date | None = None):
    return svc.cash_flow(db, user, start_date, end_date)


@router.get("/export.csv")
def export_csv(user: CurrentUser, db: DbSession, start_date: date | None = None, end_date: date | None = None):
    start, end = svc.resolve_period(user, start_date, end_date)
    content = svc.export_csv(db, user, start, end)
    filename = f"finance-report-{start.isoformat()}-to-{end.isoformat()}.csv"
    return Response(content="﻿" + content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
