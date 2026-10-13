"""Đặt lịch hẹn: four tools on the owner's Google Calendar, for the owner's Hermes (dashboard, Hermes
Desktop, CLI, cron). They never reach Telegram/WhatsApp/Slack/Discord bots; Moza keeps them off the web widget, Zalo
OA and Facebook pages: a stranger never books or cancels by chatting.

  lich_xem        events between two dates
  lich_gio_trong  free slots of a day within working hours
  lich_dat_hen    book an appointment (refuses a clash unless told otherwise)
  lich_huy_hen    cancel an appointment by its event id

Hermes calls ``handler(args, **context)`` and takes a string back (JSON for structured results).
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import google_calendar as gcal
from . import schemas

TOOLSET = "dat-lich-google-calendar"
_EMOJI = "📅"
_DEFAULT_ZONE = "Asia/Ho_Chi_Minh"
_MAX_DAYS = 31
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")


def _zone() -> ZoneInfo:
    try:
        return ZoneInfo((os.getenv("LICH_HEN_TIMEZONE") or _DEFAULT_ZONE).strip())
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(_DEFAULT_ZONE)


def _clock(value: str, field: str) -> time:
    try:
        return datetime.strptime(str(value).strip(), "%H:%M").time()
    except ValueError:
        raise ValueError(f"{field} phải có dạng HH:MM, ví dụ 09:30.") from None


def _day(value: object, field: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError(f"{field} phải có dạng YYYY-MM-DD, ví dụ 2026-10-20.") from None


def _working_hours() -> tuple[time, time]:
    raw = (os.getenv("LICH_HEN_GIO_LAM") or "08:00-18:00").strip()
    try:
        start, end = (_clock(part, "LICH_HEN_GIO_LAM") for part in raw.split("-", 1))
    except ValueError:
        start, end = time(8), time(18)
    return (start, end) if start < end else (time(8), time(18))


def _minutes(value: object, default: int) -> int:
    try:
        minutes = int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        raise ValueError("thoi_luong_phut phải là số phút.") from None
    if not 5 <= minutes <= 480:
        raise ValueError("thoi_luong_phut phải từ 5 đến 480.")
    return minutes


def _when(entry: object, zone: ZoneInfo) -> tuple[datetime, bool]:
    """An event's start or end in the appointments' zone, and whether it is an all-day date."""
    entry = entry if isinstance(entry, dict) else {}
    if entry.get("dateTime"):
        return datetime.fromisoformat(str(entry["dateTime"]).replace("Z", "+00:00")).astimezone(zone), False
    return datetime.combine(date.fromisoformat(str(entry.get("date"))), time(0), zone), True


def _busy(events: list[dict], zone: ZoneInfo) -> list[dict]:
    out = []
    for event in events:
        if event.get("status") == "cancelled" or event.get("transparency") == "transparent":
            continue
        try:
            start, all_day = _when(event.get("start"), zone)
            end, _ = _when(event.get("end"), zone)
        except (ValueError, TypeError):
            continue
        out.append({"event_id": event.get("id"), "tieu_de": str(event.get("summary") or "(không tiêu đề)")[:120],
                    "start": start, "end": end, "ca_ngay": all_day,
                    "mo_ta": str(event.get("description") or "")[:200]})
    return out


def _events(start: datetime, end: datetime) -> list[dict]:
    answer = gcal.call("GET", gcal.events_path(), query={
        "timeMin": start.isoformat(), "timeMax": end.isoformat(), "singleEvents": "true", "orderBy": "startTime",
        "maxResults": "100"}) or {}
    items = answer.get("items")
    return _busy(items if isinstance(items, list) else [], _zone())


def _text(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d %H:%M")


def _shown(entry: dict) -> dict:
    return {"event_id": entry["event_id"], "tieu_de": entry["tieu_de"], "bat_dau": _text(entry["start"]),
            "ket_thuc": _text(entry["end"]), "ca_ngay": entry["ca_ngay"], "mo_ta": entry["mo_ta"]}


def _result(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def lich_xem(args: dict) -> str:
    first = _day(args.get("tu_ngay"), "tu_ngay")
    last = _day(args.get("den_ngay"), "den_ngay") if args.get("den_ngay") else first
    if last < first or (last - first).days >= _MAX_DAYS:
        raise ValueError(f"den_ngay phải từ tu_ngay tới tối đa {_MAX_DAYS} ngày sau.")
    zone = _zone()
    events = _events(datetime.combine(first, time(0), zone), datetime.combine(last + timedelta(days=1), time(0), zone))
    return _result({"tu_ngay": first.isoformat(), "den_ngay": last.isoformat(), "so_lich": len(events),
                    "lich": [_shown(entry) for entry in events[:50]]})


def lich_gio_trong(args: dict) -> str:
    day = _day(args.get("ngay"), "ngay")
    minutes = _minutes(args.get("thoi_luong_phut"), 30)
    open_at, close_at = _working_hours()
    if args.get("tu_gio"):
        open_at = _clock(args["tu_gio"], "tu_gio")
    if args.get("den_gio"):
        close_at = _clock(args["den_gio"], "den_gio")
    zone = _zone()
    start, end = datetime.combine(day, open_at, zone), datetime.combine(day, close_at, zone)
    now = datetime.now(zone)
    if start < now:
        # Today: nothing before the next five minutes.
        start = max(start, (now + timedelta(minutes=5 - now.minute % 5)).replace(second=0, microsecond=0))
    slots, cursor = [], start
    for entry in sorted(_events(datetime.combine(day, time(0), zone), datetime.combine(day + timedelta(days=1), time(0), zone)),
                        key=lambda item: item["start"]):
        if entry["start"] - cursor >= timedelta(minutes=minutes) and cursor < end:
            slots.append((cursor, min(entry["start"], end)))
        cursor = max(cursor, entry["end"])
    if end - cursor >= timedelta(minutes=minutes):
        slots.append((cursor, end))
    slots = [(a, b) for a, b in slots if b - a >= timedelta(minutes=minutes)]
    return _result({"ngay": day.isoformat(), "thoi_luong_phut": minutes,
                    "gio_trong": [f"{a:%H:%M}-{b:%H:%M}" for a, b in slots]})


def lich_dat_hen(args: dict) -> str:
    title = str(args.get("tieu_de") or "").strip()
    if not title:
        raise ValueError("Thiếu tieu_de của lịch hẹn.")
    email = str(args.get("email_khach") or "").strip()
    if email and not _EMAIL.match(email):
        raise ValueError("email_khach không hợp lệ.")
    zone = _zone()
    start = datetime.combine(_day(args.get("ngay"), "ngay"), _clock(args.get("gio", ""), "gio"), zone)
    end = start + timedelta(minutes=_minutes(args.get("thoi_luong_phut"), 30))
    clashes = [entry for entry in _events(start - timedelta(hours=12), end + timedelta(hours=12))
               if entry["start"] < end and entry["end"] > start]
    if clashes and args.get("cho_phep_trung") is not True:
        return _result({"trang_thai": "trung_lich", "trung_voi": [_shown(entry) for entry in clashes[:10]],
                        "goi_y": "Hỏi chủ trợ lý chọn giờ khác (lich_gio_trong) hoặc xác nhận đặt chồng (cho_phep_trung)."})
    lines = [f"Khách: {str(args.get('ten_khach') or '').strip()}" if args.get("ten_khach") else "",
             f"Điện thoại: {str(args.get('so_dien_thoai') or '').strip()}" if args.get("so_dien_thoai") else "",
             str(args.get("ghi_chu") or "").strip(), "Đặt bởi trợ lý Hermes."]
    invite = bool(email) and args.get("gui_loi_moi") is True
    body = {"summary": title[:200], "description": "\n".join(line for line in lines if line)[:2000],
            "start": {"dateTime": start.isoformat(), "timeZone": zone.key},
            "end": {"dateTime": end.isoformat(), "timeZone": zone.key},
            **({"attendees": [{"email": email}]} if email else {})}
    event = gcal.call("POST", gcal.events_path(), query={"sendUpdates": "all" if invite else "none"}, body=body) or {}
    return _result({"trang_thai": "da_dat", "event_id": event.get("id"), "bat_dau": _text(start), "ket_thuc": _text(end),
                    "link": event.get("htmlLink"), "da_gui_loi_moi": invite})


def lich_huy_hen(args: dict) -> str:
    event_id = str(args.get("event_id") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,1024}", event_id):
        raise ValueError("Thiếu event_id hợp lệ (lấy từ lich_xem).")
    notify = args.get("gui_thong_bao") is True
    gcal.call("DELETE", gcal.events_path(event_id), query={"sendUpdates": "all" if notify else "none"})
    return _result({"trang_thai": "da_huy", "event_id": event_id, "da_gui_thong_bao": notify})


def _handler(work):
    """Hermes' contract: ``handler(args, **context)`` → str. Bad input and Calendar failures come back as
    one Vietnamese sentence the model can relay; nothing else escapes."""

    def call(args=None, **_context) -> str:
        try:
            return work(args if isinstance(args, dict) else {})
        except (ValueError, gcal.CalendarError) as problem:
            return str(problem)

    call.__name__ = work.__name__
    return call


def register(ctx) -> None:
    """Plugin entry point: the four calendar tools, in their own toolset (named literally, so a review and
    the machine's install check can read them)."""
    ctx.register_tool(name="lich_xem", toolset=TOOLSET, schema=schemas.XEM, handler=_handler(lich_xem),
                      description="Xem lịch hẹn trên Google Calendar.", emoji=_EMOJI)
    ctx.register_tool(name="lich_gio_trong", toolset=TOOLSET, schema=schemas.GIO_TRONG, handler=_handler(lich_gio_trong),
                      description="Tìm giờ trống trong ngày.", emoji=_EMOJI)
    ctx.register_tool(name="lich_dat_hen", toolset=TOOLSET, schema=schemas.DAT_HEN, handler=_handler(lich_dat_hen),
                      description="Đặt lịch hẹn vào Google Calendar.", emoji=_EMOJI)
    ctx.register_tool(name="lich_huy_hen", toolset=TOOLSET, schema=schemas.HUY_HEN, handler=_handler(lich_huy_hen),
                      description="Huỷ lịch hẹn.", emoji=_EMOJI)
