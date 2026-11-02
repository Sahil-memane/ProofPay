"""
Recovery Timing and Scheduling Rules.

Calculates the next allowed send time considering:
  1. 48-hour minimum gap between non-urgent customer contacts
  2. Quiet hours (21:00 - 08:00 / 9 PM - 8 AM in customer local timezone via zoneinfo)
  3. Payday alignment (configured days of the month, e.g. 1st and 15th)
  4. Daylight saving transitions (DST edge cases)
"""
from __future__ import annotations

import zoneinfo
from datetime import datetime, timedelta, timezone
from typing import Sequence


PAYDAY_DAYS_DEFAULT: tuple[int, ...] = (1, 15)
QUIET_START_HOUR = 21   # 9 PM customer time
QUIET_END_HOUR = 8      # 8 AM customer time
MIN_GAP_HOURS = 48.0


def is_in_quiet_hours(dt: datetime, tz_name: str) -> bool:
    """Return True if datetime falls within quiet hours (21:00 to 08:00) in customer timezone."""
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")

    local_dt = dt.astimezone(tz)
    hour = local_dt.hour
    return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR


def align_to_payday(dt: datetime, payday_days: Sequence[int] = PAYDAY_DAYS_DEFAULT) -> datetime:
    """Advance datetime to the next payday date if not already on one."""
    current = dt
    # Advance up to 32 days to find the next payday day
    for _ in range(32):
        if current.day in payday_days:
            return current
        current += timedelta(days=1)
    return current


def get_next_allowed_send_time(
    customer_tz: str,
    last_contact_at: datetime | None,
    now: datetime,
    is_payday_aligned: bool = False,
    min_gap_hours: float = MIN_GAP_HOURS,
    payday_days: Sequence[int] = PAYDAY_DAYS_DEFAULT,
) -> datetime:
    """
    Calculate the next allowed contact time adhering to:
      - 48-hour gap from last contact
      - Customer quiet hours (9 PM to 8 AM local time)
      - Optional payday alignment
    """
    try:
        tz = zoneinfo.ZoneInfo(customer_tz)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")

    utc_now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    utc_now = utc_now.astimezone(timezone.utc)

    # 1. 48-Hour Gap Enforcement
    earliest = utc_now
    if last_contact_at:
        last_utc = last_contact_at if last_contact_at.tzinfo else last_contact_at.replace(tzinfo=timezone.utc)
        min_next = last_utc.astimezone(timezone.utc) + timedelta(hours=min_gap_hours)
        if min_next > earliest:
            earliest = min_next

    # Convert to customer local timezone
    local_dt = earliest.astimezone(tz)

    # 2. Payday Alignment
    if is_payday_aligned:
        local_dt = align_to_payday(local_dt, payday_days)

    # 3. Quiet Hours Window Adjustment
    # If currently in quiet hours (>= 21:00 or < 08:00), push to 09:00 AM customer time
    if local_dt.hour >= QUIET_START_HOUR:
        # After 9 PM: push to tomorrow morning at 09:00 AM
        next_day = local_dt.date() + timedelta(days=1)
        local_dt = datetime(next_day.year, next_day.month, next_day.day, 9, 0, 0, tzinfo=tz)
    elif local_dt.hour < QUIET_END_HOUR:
        # Before 8 AM: push to today at 09:00 AM
        curr_day = local_dt.date()
        local_dt = datetime(curr_day.year, curr_day.month, curr_day.day, 9, 0, 0, tzinfo=tz)

    # Convert back to UTC
    return local_dt.astimezone(timezone.utc)

