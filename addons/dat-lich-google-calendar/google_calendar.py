"""Google Calendar over its REST API with the standard library only (no third-party package, so the
add-on has no dependency to lock).

Credentials: the OAuth token the Moza portal pushes for the Google Workspace add-on
(``GOOGLE_TOKEN_PATH``, default ``/opt/data/google_token.json``). The access token is refreshed on a
401 (``refresh_token`` grant, only ever sent to Google's token endpoint) and written back atomically,
like the Google Workspace add-on does. Every error is a ``CalendarError`` whose text is safe to show
the model: never a token, a secret or a traceback.
"""

from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.googleapis.com/calendar/v3"
TOKEN_URI = "https://oauth2.googleapis.com/token"
DEFAULT_TOKEN_PATH = "/opt/data/google_token.json"
CALENDAR_SCOPES = ("https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/calendar")
TIMEOUT = 20

NOT_CONNECTED = ("Chưa kết nối Google. Chủ trợ lý vào portal → VPS → Hermes → tab Kênh → Kết nối Google "
                 "trước khi đặt lịch.")
NO_CALENDAR_SCOPE = ("Google chưa cấp quyền Lịch cho trợ lý. Chủ trợ lý cần Kết nối lại Google (tab Kênh) "
                     "sau khi Moza mở quyền Google Calendar.")
RECONNECT = "Không làm mới được quyền Google — chủ trợ lý hãy Kết nối lại Google trong tab Kênh."


class CalendarError(Exception):
    """A failure whose message may be shown to the model as is."""


def token_path() -> Path:
    return Path(os.getenv("GOOGLE_TOKEN_PATH") or DEFAULT_TOKEN_PATH)


def calendar_id() -> str:
    return (os.getenv("LICH_HEN_CALENDAR_ID") or "primary").strip() or "primary"


def _load() -> dict:
    try:
        data = json.loads(token_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CalendarError(NOT_CONNECTED) from None
    except (OSError, ValueError):
        raise CalendarError("Token Google hỏng hoặc không đọc được — chủ trợ lý hãy Kết nối lại Google.") from None
    if not isinstance(data, dict) or not (data.get("token") or data.get("refresh_token")):
        raise CalendarError(NOT_CONNECTED)
    scopes = data.get("scopes")
    if isinstance(scopes, list) and scopes and not any(scope in CALENDAR_SCOPES for scope in scopes):
        raise CalendarError(NO_CALENDAR_SCOPE)
    return data


def _persist(data: dict) -> None:
    """Best effort: a failed write only costs another refresh next time."""
    path = token_path()
    try:
        fd, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    except OSError:
        pass


def _refresh(data: dict) -> dict:
    if not all(isinstance(data.get(key), str) and data.get(key) for key in ("refresh_token", "client_id", "client_secret")):
        raise CalendarError(RECONNECT)
    token_uri = data.get("token_uri") or TOKEN_URI
    # The refresh token and client secret only ever go to Google's own token endpoint.
    if not str(token_uri).startswith("https://oauth2.googleapis.com/"):
        raise CalendarError(RECONNECT)
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": data["refresh_token"],
                                   "client_id": data["client_id"], "client_secret": data["client_secret"]}).encode()
    request = urllib.request.Request(token_uri, data=body, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 — fixed https endpoint
            answer = json.loads(response.read() or b"{}")
    except (urllib.error.URLError, OSError, ValueError):
        raise CalendarError(RECONNECT) from None
    access = answer.get("access_token") if isinstance(answer, dict) else None
    if not isinstance(access, str) or not access:
        raise CalendarError(RECONNECT)
    data = {**data, "token": access}
    _persist(data)
    return data


def _friendly(error: urllib.error.HTTPError) -> str:
    try:
        detail = error.read(4096).decode("utf-8", "replace")
    except OSError:
        detail = ""
    if error.code == 403 and ("insufficient" in detail.lower() or "scope" in detail.lower()):
        return NO_CALENDAR_SCOPE
    if error.code in (401, 403):
        return "Google từ chối quyền truy cập Lịch — chủ trợ lý hãy Kết nối lại Google trong tab Kênh."
    if error.code in (404, 410):
        return "Không tìm thấy lịch hoặc lịch hẹn (mã sai hoặc đã bị xoá)."
    return "Google Calendar chưa trả lời được, thử lại sau ít phút."


def call(method: str, path: str, *, query: dict | None = None, body: dict | None = None) -> dict | None:
    """One Calendar API call (``path`` under /calendar/v3), refreshed once on a 401."""
    data = _load()
    url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
    payload = json.dumps(body).encode() if body is not None else None
    for attempt in (0, 1):
        request = urllib.request.Request(url, data=payload, method=method, headers={
            "Authorization": f"Bearer {data.get('token') or ''}", "Accept": "application/json",
            **({"Content-Type": "application/json"} if payload is not None else {})})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 — fixed https endpoint
                raw = response.read()
            return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            if error.code == 401 and attempt == 0:
                data = _refresh(data)
                continue
            raise CalendarError(_friendly(error)) from None
        except (urllib.error.URLError, OSError, ValueError):
            raise CalendarError("Không gọi được Google Calendar, thử lại sau ít phút.") from None
    raise CalendarError(RECONNECT)


def events_path(event_id: str | None = None) -> str:
    base = "/calendars/" + urllib.parse.quote(calendar_id(), safe="") + "/events"
    return base if event_id is None else base + "/" + urllib.parse.quote(event_id, safe="")
