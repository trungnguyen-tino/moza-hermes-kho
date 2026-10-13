"""The Moza portal's ZNS endpoints, with the standard library only.

The machine never holds a Zalo OA token: the portal does (it refreshes them; a refresh token works
once), so every ZNS call goes through it, authenticated by this assistant's portal token
(``PORTAL_INGEST_TOKEN``, set on the machine by Moza): ``GET …/templates`` lists the allowed templates,
``POST …/messages`` ``{phone: "84…", template_id, template_data, tracking_id}`` sends one.

Errors are ``ZnsError`` with a sentence the model can relay (the portal's own Vietnamese message when it
gives one); the token never appears in one.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit

TIMEOUT = 15
NOT_AVAILABLE = ("Portal chưa mở Thông báo ZNS cho trợ lý này (cần Zalo OA đã kết nối, mẫu tin ZNS đã được Zalo duyệt "
                 "và chủ trợ lý cho phép dùng). Chủ trợ lý liên hệ Moza để bật.")


class ZnsError(Exception):
    """A failure whose message may be shown to the model as is."""


def _portal() -> tuple[str, str]:
    url = urlsplit((os.getenv("PORTAL_INGEST_URL") or "").strip())
    token = (os.getenv("PORTAL_INGEST_TOKEN") or "").strip()
    if url.scheme != "https" or not url.netloc or not token:
        raise ZnsError("Trợ lý chưa được nối với portal Moza (thiếu PORTAL_INGEST_URL/PORTAL_INGEST_TOKEN).")
    return f"https://{url.netloc}/api/v1/internal/zalo-oa/zns", token


def _message(error: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(error.read(8192) or b"{}")
    except (OSError, ValueError):
        body = {}
    text = body.get("message") or body.get("error") if isinstance(body, dict) else None
    if error.code == 404:
        return NOT_AVAILABLE
    if error.code in (401, 403):
        return str(text or "Portal từ chối yêu cầu ZNS của trợ lý này.")[:300]
    if error.code == 429:
        return str(text or "Đã hết hạn mức gửi ZNS trong ngày.")[:300]
    if error.code == 422:
        return str(text or "Portal không nhận mẫu tin hoặc tham số này.")[:300]
    return "Portal chưa gửi được ZNS, thử lại sau ít phút."


def call(method: str, path: str, body: dict | None = None) -> dict:
    base, token = _portal()
    payload = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base + path, data=payload, method=method, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json",
        **({"Content-Type": "application/json"} if payload is not None else {})})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 — https portal from the env
            answer = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        raise ZnsError(_message(error)) from None
    except (urllib.error.URLError, OSError, ValueError):
        raise ZnsError("Không gọi được portal Moza, thử lại sau ít phút.") from None
    data = answer.get("data") if isinstance(answer, dict) else None
    if not isinstance(data, dict):
        raise ZnsError("Portal trả lời không đúng dạng.")
    return data
