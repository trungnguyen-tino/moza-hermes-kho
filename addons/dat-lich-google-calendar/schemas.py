"""Tool schemas of the Đặt lịch hẹn add-on: the bare function objects Hermes' registry wraps itself."""

from __future__ import annotations


def schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required}}


_DAY = {"type": "string", "description": "Ngày dạng YYYY-MM-DD."}
_MINUTES = {"type": "integer", "description": "Thời lượng (phút), 5–480, mặc định 30."}

XEM = schema("lich_xem", "Xem các lịch hẹn trên Google Calendar của chủ trợ lý từ ngày đến ngày (tối đa 31 ngày).",
               {"tu_ngay": _DAY, "den_ngay": {**_DAY, "description": "Ngày cuối (mặc định = tu_ngay)."}}, ["tu_ngay"])
GIO_TRONG = schema(
    "lich_gio_trong", "Tìm các khoảng giờ còn trống trong một ngày, trong giờ làm việc, đủ dài cho một cuộc hẹn.",
    {"ngay": _DAY, "thoi_luong_phut": _MINUTES, "tu_gio": {"type": "string", "description": "HH:MM, mặc định giờ mở cửa."},
     "den_gio": {"type": "string", "description": "HH:MM, mặc định giờ đóng cửa."}}, ["ngay"])
DAT_HEN = schema(
    "lich_dat_hen",
    "Đặt một lịch hẹn vào Google Calendar của chủ trợ lý. Từ chối khi trùng lịch khác, trừ khi cho_phep_trung=true. "
    "Chỉ đặt khi chủ trợ lý yêu cầu hoặc đã xác nhận.",
    {"ngay": _DAY, "gio": {"type": "string", "description": "Giờ bắt đầu HH:MM."}, "thoi_luong_phut": _MINUTES,
     "tieu_de": {"type": "string", "description": "Tiêu đề, ví dụ 'Gội đầu - chị Lan'."},
     "ten_khach": {"type": "string"}, "so_dien_thoai": {"type": "string"},
     "email_khach": {"type": "string", "description": "Email của khách (tuỳ chọn)."},
     "gui_loi_moi": {"type": "boolean", "description": "Gửi lời mời qua email cho khách (cần email_khach)."},
     "ghi_chu": {"type": "string"},
     "cho_phep_trung": {"type": "boolean", "description": "Đặt dù trùng lịch khác (chỉ khi chủ trợ lý đồng ý)."}},
    ["ngay", "gio", "tieu_de"])
HUY_HEN = schema("lich_huy_hen", "Huỷ một lịch hẹn theo event_id (lấy từ lich_xem). Chỉ huỷ khi chủ trợ lý yêu cầu.",
                   {"event_id": {"type": "string"},
                    "gui_thong_bao": {"type": "boolean", "description": "Báo huỷ qua email cho khách mời."}}, ["event_id"])
