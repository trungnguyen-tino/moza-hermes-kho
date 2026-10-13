"""Thông báo ZNS: two tools for the owner's Hermes (dashboard, Hermes on the desktop, CLI, cron). They
never reach the web widget, Zalo OA, Facebook pages or any Telegram/WhatsApp/Slack/Discord bot, so a
stranger never makes the OA send (and pay for) a message.

  zns_mau_tin  the ZNS templates the owner allowed, with their parameters and price
  zns_gui      send one template to one phone number (only when the owner asks or confirms)

Every send goes through the portal (portal_zns.py), which checks the template, the parameters and the
daily cap. Hermes calls ``handler(args, **context)`` and takes a string back.
"""

from __future__ import annotations

import json
import re
import uuid

from . import portal_zns

TOOLSET = "thong-bao-zns"
_EMOJI = "📨"
_TEMPLATE_ID = re.compile(r"^[0-9]{1,20}$")
_TRACKING_ID = re.compile(r"^[A-Za-z0-9_-]{1,48}$")


def phone_84(value: object) -> str:
    """A Vietnamese mobile number as Zalo takes it (84…, digits only); ValueError otherwise."""
    digits = re.sub(r"[\s.()-]", "", str(value or ""))
    if digits.startswith("+"):
        digits = digits[1:]
    if digits.startswith("0"):
        digits = "84" + digits[1:]
    if not re.fullmatch(r"84[1-9][0-9]{8}", digits):
        raise ValueError("so_dien_thoai phải là số di động Việt Nam, ví dụ 0901234567.")
    return digits


def zns_mau_tin(args: dict) -> str:
    data = portal_zns.call("GET", "/templates")
    templates = data.get("templates") if isinstance(data.get("templates"), list) else []
    return json.dumps({"mau_tin": templates[:50]}, ensure_ascii=False)


def zns_gui(args: dict) -> str:
    template_id = str(args.get("template_id") or "").strip()
    if not _TEMPLATE_ID.match(template_id):
        raise ValueError("Thiếu template_id hợp lệ (lấy từ zns_mau_tin).")
    params = args.get("tham_so") if args.get("tham_so") is not None else {}
    if not isinstance(params, dict) or len(params) > 30 or not all(
            isinstance(key, str) and isinstance(value, (str, int, float)) for key, value in params.items()):
        raise ValueError("tham_so phải là bảng tên tham số → giá trị chữ hoặc số (tối đa 30).")
    tracking = str(args.get("ma_theo_doi") or "").strip() or uuid.uuid4().hex[:32]
    if not _TRACKING_ID.match(tracking):
        raise ValueError("ma_theo_doi chỉ gồm chữ, số, - và _ (tối đa 48 ký tự).")
    data = portal_zns.call("POST", "/messages", {
        "phone": phone_84(args.get("so_dien_thoai")), "template_id": template_id,
        "template_data": {key: str(value)[:400] for key, value in params.items()}, "tracking_id": tracking})
    return json.dumps({"trang_thai": data.get("status"), "message_id": data.get("message_id"), "ma_theo_doi": tracking},
                      ensure_ascii=False)


def _handler(work):
    """Hermes' contract: ``handler(args, **context)`` → str; bad input and portal refusals come back as one
    sentence the model can relay."""

    def call(args=None, **_context) -> str:
        try:
            return work(args if isinstance(args, dict) else {})
        except (ValueError, portal_zns.ZnsError) as problem:
            return str(problem)

    call.__name__ = work.__name__
    return call


_MAU_TIN = {"name": "zns_mau_tin", "parameters": {"type": "object", "properties": {}, "required": []},
            "description": "Liệt kê các mẫu tin ZNS (Zalo) chủ trợ lý cho phép dùng, kèm tham số và giá mỗi tin. "
                           "Gọi trước zns_gui để lấy đúng template_id và tên tham số."}
_GUI = {"name": "zns_gui", "description": (
    "Gửi một tin ZNS (thông báo qua Zalo theo mẫu đã duyệt) tới số điện thoại của khách: xác nhận đơn, nhắc lịch hẹn… "
    "Mỗi tin Zalo tính phí. Chỉ gửi khi chủ trợ lý yêu cầu hoặc đã xác nhận nội dung, không gửi quảng cáo."),
    "parameters": {"type": "object", "required": ["so_dien_thoai", "template_id", "tham_so"], "properties": {
        "so_dien_thoai": {"type": "string", "description": "Số di động Việt Nam của khách, ví dụ 0901234567."},
        "template_id": {"type": "string", "description": "Mã mẫu tin (từ zns_mau_tin)."},
        "tham_so": {"type": "object", "description": "Giá trị cho từng tham số của mẫu, ví dụ {\"customer_name\": \"Lan\"}."},
        "ma_theo_doi": {"type": "string", "description": "Mã để không gửi trùng khi thử lại (tuỳ chọn)."}}}}


def register(ctx) -> None:
    """Plugin entry point: the two ZNS tools, in their own toolset (named literally for the review)."""
    ctx.register_tool(name="zns_mau_tin", toolset=TOOLSET, schema=_MAU_TIN, handler=_handler(zns_mau_tin),
                      description="Liệt kê mẫu tin ZNS được phép.", emoji=_EMOJI)
    ctx.register_tool(name="zns_gui", toolset=TOOLSET, schema=_GUI, handler=_handler(zns_gui),
                      description="Gửi một tin ZNS theo mẫu.", emoji=_EMOJI)
