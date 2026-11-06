"""Date helpers. Period boundaries use the user's configured timezone.

Transaction dates are calendar dates (DATE) as the user sees them, so "today"
must be computed in the user's timezone, not the server's.
"""
import calendar
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def is_valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def today_for(tz_name: str) -> date:
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        tz = timezone.utc
    return datetime.now(tz).date()


def month_bounds(year: int, month: int) -> tuple[date, date]:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def previous_period(start: date, end: date) -> tuple[date, date]:
    """Period of equal length immediately before [start, end]. Whole calendar
    months map to the previous whole calendar month(s)."""
    if start.day == 1 and end == month_bounds(end.year, end.month)[1]:
        months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        prev_start = add_months(start, -months)
        prev_end = start - timedelta(days=1)
        return prev_start, prev_end
    length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    return prev_end - timedelta(days=length - 1), prev_end


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())
