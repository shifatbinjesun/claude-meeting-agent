from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from claude_agent import scheduler as s

TZ = ZoneInfo("Asia/Dhaka")


def at(h, m, day=24):
    return datetime(2026, 11, day, h, m, tzinfo=TZ)


def test_once_window():
    sch = [{"id": 1, "enabled": 1, "start_iso": "2026-11-24T15:00:00+06:00", "recurrence": "none", "last_run": None}]
    assert s.due(sch, at(14, 57), TZ) == []
    assert len(s.due(sch, at(14, 59), TZ)) == 1
    assert len(s.due(sch, at(15, 9), TZ)) == 1
    assert s.due(sch, at(15, 11), TZ) == []          # missed windows are never joined late


def test_disabled_and_already_run():
    base = {"id": 1, "start_iso": "2026-11-24T15:00:00+06:00", "recurrence": "none"}
    assert s.due([dict(base, enabled=0, last_run=None)], at(15, 0), TZ) == []
    ran = at(14, 59).timestamp()
    assert s.due([dict(base, enabled=1, last_run=ran)], at(15, 1), TZ) == []


def test_weekdays_skip_bangladesh_weekend():
    sch = [{"id": 2, "enabled": 1, "start_iso": "2026-11-22T10:00:00+06:00", "recurrence": "weekdays", "last_run": None}]
    assert len(s.due(sch, at(10, 0, 26), TZ)) == 1      # Thursday
    assert s.due(sch, at(10, 0, 27), TZ) == []          # Friday
    assert s.due(sch, at(10, 0, 28), TZ) == []          # Saturday
    assert len(s.due(sch, at(10, 0, 29), TZ)) == 1      # Sunday


def test_timezone_from_utc_now():
    sch = [{"id": 3, "enabled": 1, "start_iso": "2026-11-24T21:00:00", "recurrence": "daily", "last_run": None}]
    now_utc = datetime(2026, 11, 25, 15, 0, tzinfo=ZoneInfo("UTC"))   # 21:00 Dhaka
    assert len(s.due(sch, now_utc, TZ)) == 1


def test_next_occurrence():
    nxt = s.next_occurrence("2026-11-24T21:00:00+06:00", "daily", at(22, 0), TZ)
    assert nxt.date() == (at(22, 0) + timedelta(days=1)).date()
