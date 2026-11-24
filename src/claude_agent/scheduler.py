"""Owner-approved meeting schedule (local; no calendar scopes required).

Only entries the owner created/enabled are ever joined. Times are Asia/Dhaka by default.
The PC must be on and the app running; missed windows are recorded, never surprise-joined later.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

RECURRENCES = ("none", "daily", "weekdays", "weekly")
EARLY = timedelta(minutes=2)
LATE = timedelta(minutes=10)


def _parse(start_iso: str, tz: ZoneInfo) -> datetime:
    dt = datetime.fromisoformat(start_iso)
    return dt if dt.tzinfo else dt.replace(tzinfo=tz)


def occurrence_near(start_iso: str, recurrence: str, now: datetime, tz: ZoneInfo) -> datetime | None:
    """Return the occurrence whose join window [t-2m, t+10m] contains now, if any."""
    first = _parse(start_iso, tz)
    if recurrence not in RECURRENCES:
        return None
    if recurrence == "none":
        cands = [first]
    else:
        local_now = now.astimezone(tz)
        base = first.astimezone(tz)
        cands = []
        for d in (-1, 0, 1):
            day = (local_now + timedelta(days=d)).date()
            t = datetime.combine(day, base.timetz())
            if t < first:
                continue
            if recurrence == "weekdays" and t.weekday() in (4, 5):   # Fri/Sat weekend in Bangladesh
                continue
            if recurrence == "weekly" and t.weekday() != base.weekday():
                continue
            cands.append(t)
    for t in cands:
        if t - EARLY <= now <= t + LATE:
            return t
    return None


def next_occurrence(start_iso: str, recurrence: str, now: datetime, tz: ZoneInfo) -> datetime | None:
    first = _parse(start_iso, tz)
    if recurrence == "none":
        return first if first + LATE >= now else None
    t = max(first, now.astimezone(tz).replace(hour=first.astimezone(tz).hour, minute=first.astimezone(tz).minute,
                                              second=0, microsecond=0))
    for _ in range(9):
        if t + LATE >= now and occurrence_near(start_iso, recurrence, t, tz):
            return t
        t += timedelta(days=1)
    return None


def due(schedules: list[dict], now: datetime, tz: ZoneInfo) -> list[tuple[dict, datetime]]:
    out = []
    for s in schedules:
        if not s.get("enabled"):
            continue
        occ = occurrence_near(s["start_iso"], s.get("recurrence", "none"), now, tz)
        if occ is None:
            continue
        last = s.get("last_run")
        if last and last >= (occ - EARLY).timestamp():
            continue   # already handled this occurrence
        out.append((s, occ))
    return out
