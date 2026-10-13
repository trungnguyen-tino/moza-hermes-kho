"""Đặt lịch hẹn (Google Calendar): the four tools as Hermes calls them (``handler(args)`` → str), against
a fake Google (urllib.request.urlopen), with the token the portal pushes in a temporary file."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
from datetime import date, timedelta

import pytest

from conftest import load_addon

cal = load_addon("dat-lich-google-calendar")
tools, gcal = cal.tools, cal.google_calendar
FUTURE = (date.today() + timedelta(days=7)).isoformat()
SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/calendar.events"]


class Google:
    """Answers queued per (method, path prefix); records every request."""

    def __init__(self):
        self.requests: list[dict] = []
        self.answers: list[tuple[str, str, int, dict | None]] = []

    def answer(self, method: str, prefix: str, status: int = 200, body: dict | None = None) -> None:
        self.answers.append((method, prefix, status, body))

    def __call__(self, request, timeout=None):
        url = urllib.parse.urlsplit(request.full_url)
        entry = {"method": request.get_method(), "url": request.full_url, "path": url.path,
                 "query": dict(urllib.parse.parse_qsl(url.query)), "headers": dict(request.header_items()),
                 "body": request.data}
        self.requests.append(entry)
        for index, (method, prefix, status, body) in enumerate(self.answers):
            if method == entry["method"] and request.full_url.startswith(prefix):
                del self.answers[index]
                raw = json.dumps(body).encode() if body is not None else b""
                if status >= 400:
                    raise urllib.error.HTTPError(request.full_url, status, "error", {}, io.BytesIO(raw))
                return io.BytesIO(raw)
        raise AssertionError(f"unexpected request {entry['method']} {request.full_url}")


@pytest.fixture
def google(monkeypatch, tmp_path):
    token = tmp_path / "google_token.json"
    token.write_text(json.dumps({"token": "access-1", "refresh_token": "refresh-secret", "client_id": "cid",
                                 "client_secret": "client-secret", "token_uri": "https://oauth2.googleapis.com/token",
                                 "scopes": SCOPES}), encoding="utf-8")
    monkeypatch.setenv("GOOGLE_TOKEN_PATH", str(token))
    monkeypatch.delenv("LICH_HEN_CALENDAR_ID", raising=False)
    monkeypatch.setenv("LICH_HEN_TIMEZONE", "Asia/Ho_Chi_Minh")
    monkeypatch.setenv("LICH_HEN_GIO_LAM", "08:00-18:00")
    fake = Google()
    monkeypatch.setattr(gcal.urllib.request, "urlopen", fake)
    fake.token = token
    return fake


def _handlers() -> dict:
    found = {}

    class Ctx:
        def register_tool(self, **kwargs):
            found[kwargs["name"]] = kwargs

    tools.register(Ctx())
    return found


def _call(name: str, args: dict | None) -> str:
    return _handlers()[name]["handler"](args, task_id="t", session_id="s")


def _event(event_id: str, day: str, start: str, end: str) -> dict:
    return {"id": event_id, "summary": f"Hẹn {event_id}", "start": {"dateTime": f"{day}T{start}:00+07:00"},
            "end": {"dateTime": f"{day}T{end}:00+07:00"}}


EVENTS = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def test_four_tools_in_their_own_toolset_with_bare_schemas():
    found = _handlers()
    assert sorted(found) == ["lich_dat_hen", "lich_gio_trong", "lich_huy_hen", "lich_xem"]
    for name, entry in found.items():
        assert entry["toolset"] == "dat-lich-google-calendar"
        assert entry["schema"]["name"] == name and entry["schema"]["parameters"]["type"] == "object"
        assert "function" not in entry["schema"]


def test_not_connected_or_no_calendar_scope_says_what_to_do(google):
    google.token.unlink()
    assert _call("lich_xem", {"tu_ngay": FUTURE}) == gcal.NOT_CONNECTED
    google.token.write_text(json.dumps({"token": "a", "scopes": ["https://www.googleapis.com/auth/drive.file"]}), encoding="utf-8")
    assert _call("lich_xem", {"tu_ngay": FUTURE}) == gcal.NO_CALENDAR_SCOPE
    assert google.requests == []


def test_xem_lists_events_in_the_appointments_time_zone(google):
    google.answer("GET", EVENTS, body={"items": [{"id": "e1", "summary": "Cắt tóc", "start": {"dateTime": f"{FUTURE}T02:00:00Z"},
                                                  "end": {"dateTime": f"{FUTURE}T03:00:00Z"}},
                                                 {"id": "e2", "summary": "Nghỉ", "start": {"date": FUTURE}, "end": {"date": FUTURE}}]})
    out = json.loads(_call("lich_xem", {"tu_ngay": FUTURE}))
    query = google.requests[0]["query"]
    assert (query["timeMin"], query["singleEvents"], query["orderBy"]) == (f"{FUTURE}T00:00:00+07:00", "true", "startTime")
    assert google.requests[0]["headers"]["Authorization"] == "Bearer access-1"
    assert out["lich"][0] == {"event_id": "e1", "tieu_de": "Cắt tóc", "bat_dau": f"{FUTURE} 09:00", "ket_thuc": f"{FUTURE} 10:00",
                              "ca_ngay": False, "mo_ta": ""}
    assert out["lich"][1]["ca_ngay"] is True


def test_gio_trong_finds_the_gaps_long_enough(google):
    google.answer("GET", EVENTS, body={"items": [_event("a", FUTURE, "09:00", "10:00"), _event("b", FUTURE, "13:00", "14:30"),
                                                 _event("c", FUTURE, "17:30", "18:00")]})
    out = json.loads(_call("lich_gio_trong", {"ngay": FUTURE, "thoi_luong_phut": 60}))
    assert out["gio_trong"] == ["08:00-09:00", "10:00-13:00", "14:30-17:30"]


def test_dat_hen_refuses_a_clash_unless_told(google):
    google.answer("GET", EVENTS, body={"items": [_event("a", FUTURE, "09:00", "10:00")]})
    out = json.loads(_call("lich_dat_hen", {"ngay": FUTURE, "gio": "09:30", "tieu_de": "Gội đầu - chị Lan"}))
    assert out["trang_thai"] == "trung_lich" and out["trung_voi"][0]["event_id"] == "a"
    assert [r["method"] for r in google.requests] == ["GET"]


def test_dat_hen_books_with_the_customer_in_the_description(google):
    google.answer("GET", EVENTS, body={"items": []})
    google.answer("POST", EVENTS, body={"id": "new1", "htmlLink": "https://calendar.google.com/event?eid=x"})
    out = json.loads(_call("lich_dat_hen", {"ngay": FUTURE, "gio": "15:00", "thoi_luong_phut": 45, "tieu_de": "Gội đầu",
                                            "ten_khach": "Chị Lan", "so_dien_thoai": "0901234567"}))
    post = google.requests[-1]
    body = json.loads(post["body"])
    assert post["query"] == {"sendUpdates": "none"}
    assert body["start"] == {"dateTime": f"{FUTURE}T15:00:00+07:00", "timeZone": "Asia/Ho_Chi_Minh"}
    assert body["end"]["dateTime"] == f"{FUTURE}T15:45:00+07:00"
    assert body["description"] == "Khách: Chị Lan\nĐiện thoại: 0901234567\nĐặt bởi trợ lý Hermes."
    assert "attendees" not in body
    assert out == {"trang_thai": "da_dat", "event_id": "new1", "bat_dau": f"{FUTURE} 15:00", "ket_thuc": f"{FUTURE} 15:45",
                   "link": "https://calendar.google.com/event?eid=x", "da_gui_loi_moi": False}


def test_an_invitation_goes_only_with_an_email_and_when_asked(google):
    google.answer("GET", EVENTS, body={"items": []})
    google.answer("POST", EVENTS, body={"id": "n2"})
    _call("lich_dat_hen", {"ngay": FUTURE, "gio": "10:00", "tieu_de": "Tư vấn", "email_khach": "lan@example.com", "gui_loi_moi": True})
    assert google.requests[-1]["query"] == {"sendUpdates": "all"}
    assert json.loads(google.requests[-1]["body"])["attendees"] == [{"email": "lan@example.com"}]
    assert _call("lich_dat_hen", {"ngay": FUTURE, "gio": "10:00", "tieu_de": "x", "email_khach": "khong-phai-email"}) \
        == "email_khach không hợp lệ."


def test_an_expired_token_is_refreshed_once_and_kept(google):
    google.answer("GET", EVENTS, status=401, body={"error": "expired"})
    google.answer("POST", "https://oauth2.googleapis.com/token", body={"access_token": "access-2", "expires_in": 3599})
    google.answer("GET", EVENTS, body={"items": []})
    out = _call("lich_xem", {"tu_ngay": FUTURE})
    assert json.loads(out)["so_lich"] == 0
    refresh = google.requests[1]
    assert dict(urllib.parse.parse_qsl(refresh["body"].decode())) == {"grant_type": "refresh_token", "refresh_token": "refresh-secret",
                                                                     "client_id": "cid", "client_secret": "client-secret"}
    assert google.requests[2]["headers"]["Authorization"] == "Bearer access-2"
    saved = json.loads(google.token.read_text(encoding="utf-8"))
    assert (saved["token"], saved["refresh_token"]) == ("access-2", "refresh-secret")
    assert "secret" not in out and "access-2" not in out


def test_secrets_never_leave_for_another_host(google):
    data = json.loads(google.token.read_text(encoding="utf-8"))
    google.token.write_text(json.dumps({**data, "token_uri": "https://evil.example/token"}), encoding="utf-8")
    google.answer("GET", EVENTS, status=401, body={})
    assert _call("lich_xem", {"tu_ngay": FUTURE}) == gcal.RECONNECT
    assert [r["url"] for r in google.requests] == [google.requests[0]["url"]]


def test_a_missing_scope_answer_says_so(google):
    google.answer("GET", EVENTS, status=403, body={"error": {"status": "PERMISSION_DENIED", "message": "Request had insufficient authentication scopes."}})
    assert _call("lich_xem", {"tu_ngay": FUTURE}) == gcal.NO_CALENDAR_SCOPE


def test_huy_hen_deletes_by_id_and_checks_it(google, monkeypatch):
    assert _call("lich_huy_hen", {"event_id": "../x"}) == "Thiếu event_id hợp lệ (lấy từ lich_xem)."
    monkeypatch.setenv("LICH_HEN_CALENDAR_ID", "salon@group.calendar.google.com")
    google.answer("DELETE", "https://www.googleapis.com/calendar/v3/calendars/salon%40group.calendar.google.com/events/abc123")
    assert json.loads(_call("lich_huy_hen", {"event_id": "abc123"}))["trang_thai"] == "da_huy"
    assert google.requests[-1]["query"] == {"sendUpdates": "none"}


@pytest.mark.parametrize(("tool", "args", "message"), [
    ("lich_xem", {"tu_ngay": "20/10/2026"}, "tu_ngay phải có dạng YYYY-MM-DD, ví dụ 2026-10-20."),
    ("lich_gio_trong", {"ngay": FUTURE, "thoi_luong_phut": 1000}, "thoi_luong_phut phải từ 5 đến 480."),
    ("lich_dat_hen", {"ngay": FUTURE, "gio": "9h", "tieu_de": "x"}, "gio phải có dạng HH:MM, ví dụ 09:30."),
    ("lich_dat_hen", None, "Thiếu tieu_de của lịch hẹn."),
])
def test_bad_input_comes_back_as_one_sentence(google, tool, args, message):
    assert _call(tool, args) == message
    assert google.requests == []
