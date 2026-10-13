"""Thông báo ZNS: the two tools as Hermes calls them, against a fake portal. The machine never holds a
Zalo OA token; it only speaks to the portal with this assistant's portal token, over https."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from conftest import load_addon

zns = load_addon("thong-bao-zns")
tools, portal = zns.tools, zns.portal_zns
BASE = "https://api.mozaai.vn/api/v1/internal/zalo-oa/zns"


class Portal:
    def __init__(self):
        self.requests: list[dict] = []
        self.status, self.body = 200, {"data": {}}

    def __call__(self, request, timeout=None):
        self.requests.append({"method": request.get_method(), "url": request.full_url, "headers": dict(request.header_items()),
                              "body": json.loads(request.data) if request.data else None})
        raw = json.dumps(self.body).encode()
        if self.status >= 400:
            raise urllib.error.HTTPError(request.full_url, self.status, "error", {}, io.BytesIO(raw))
        return io.BytesIO(raw)


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("PORTAL_INGEST_URL", "https://api.mozaai.vn/api/v1/internal/ingest")
    monkeypatch.setenv("PORTAL_INGEST_TOKEN", "portal-token-secret")
    server = Portal()
    monkeypatch.setattr(portal.urllib.request, "urlopen", server)
    return server


def _handlers() -> dict:
    found = {}

    class Ctx:
        def register_tool(self, **kwargs):
            found[kwargs["name"]] = kwargs

    tools.register(Ctx())
    return found


def _call(name: str, args: dict | None) -> str:
    return _handlers()[name]["handler"](args, session_id="s")


def test_two_tools_in_their_own_toolset():
    found = _handlers()
    assert sorted(found) == ["zns_gui", "zns_mau_tin"]
    assert {entry["toolset"] for entry in found.values()} == {"thong-bao-zns"}
    assert all(entry["schema"]["name"] == name and "function" not in entry["schema"] for name, entry in found.items())


def test_templates_come_from_the_portal_with_the_assistant_token(fake):
    fake.body = {"data": {"templates": [{"template_id": "231456", "name": "Xác nhận đơn", "params": [{"name": "customer_name"}],
                                         "price_vnd": 300}]}}
    out = json.loads(_call("zns_mau_tin", {}))
    assert out["mau_tin"][0]["template_id"] == "231456"
    assert fake.requests == [{"method": "GET", "url": BASE + "/templates", "body": None,
                              "headers": {"Authorization": "Bearer portal-token-secret", "Accept": "application/json"}}]


@pytest.mark.parametrize(("raw", "normalized"), [("0901234567", "84901234567"), ("+84 90 123 4567", "84901234567"),
                                                 ("84901234567", "84901234567"), ("090.123.4567", "84901234567")])
def test_a_send_goes_through_the_portal_with_a_zalo_phone_number(fake, raw, normalized):
    fake.status, fake.body = 202, {"data": {"status": "queued", "message_id": "m1"}}
    out = json.loads(_call("zns_gui", {"so_dien_thoai": raw, "template_id": "231456", "tham_so": {"customer_name": "Lan", "amount": 350000},
                                       "ma_theo_doi": "don-42"}))
    assert out == {"trang_thai": "queued", "message_id": "m1", "ma_theo_doi": "don-42"}
    assert fake.requests[0]["url"] == BASE + "/messages"
    assert fake.requests[0]["body"] == {"phone": normalized, "template_id": "231456",
                                        "template_data": {"customer_name": "Lan", "amount": "350000"}, "tracking_id": "don-42"}


def test_a_tracking_id_is_made_when_none_is_given(fake):
    fake.body = {"data": {"status": "sent", "message_id": "m2"}}
    tracking = json.loads(_call("zns_gui", {"so_dien_thoai": "0901234567", "template_id": "1", "tham_so": {}}))["ma_theo_doi"]
    assert len(tracking) == 32 and fake.requests[0]["body"]["tracking_id"] == tracking


@pytest.mark.parametrize(("args", "message"), [
    ({"so_dien_thoai": "12345", "template_id": "1", "tham_so": {}}, "so_dien_thoai phải là số di động Việt Nam, ví dụ 0901234567."),
    ({"so_dien_thoai": "0901234567", "template_id": "abc", "tham_so": {}}, "Thiếu template_id hợp lệ (lấy từ zns_mau_tin)."),
    ({"so_dien_thoai": "0901234567", "template_id": "1", "tham_so": ["x"]},
     "tham_so phải là bảng tên tham số → giá trị chữ hoặc số (tối đa 30)."),
    ({"so_dien_thoai": "0901234567", "template_id": "1", "tham_so": {}, "ma_theo_doi": "có dấu"},
     "ma_theo_doi chỉ gồm chữ, số, - và _ (tối đa 48 ký tự)."),
])
def test_bad_input_never_reaches_the_portal(fake, args, message):
    assert _call("zns_gui", args) == message
    assert fake.requests == []


@pytest.mark.parametrize(("status", "body", "message"), [
    (404, {}, portal.NOT_AVAILABLE),
    (429, {"message": "Đã gửi đủ 200 tin ZNS hôm nay."}, "Đã gửi đủ 200 tin ZNS hôm nay."),
    (422, {"message": "Mẫu tin 231456 thiếu tham số order_code."}, "Mẫu tin 231456 thiếu tham số order_code."),
    (500, {"message": "stack trace"}, "Portal chưa gửi được ZNS, thử lại sau ít phút."),
])
def test_portal_refusals_come_back_as_one_sentence(fake, status, body, message):
    fake.status, fake.body = status, body
    assert _call("zns_gui", {"so_dien_thoai": "0901234567", "template_id": "1", "tham_so": {}}) == message


def test_without_an_https_portal_nothing_is_sent(fake, monkeypatch):
    monkeypatch.setenv("PORTAL_INGEST_URL", "http://api.mozaai.vn/api/v1/internal/ingest")
    assert "PORTAL_INGEST_URL" in _call("zns_mau_tin", {})
    monkeypatch.delenv("PORTAL_INGEST_TOKEN")
    monkeypatch.setenv("PORTAL_INGEST_URL", "https://api.mozaai.vn/x")
    assert "PORTAL_INGEST_TOKEN" in _call("zns_mau_tin", None)
    assert fake.requests == []
