# Đặt lịch hẹn (Google Calendar)

| | |
|---|---|
| Tên | `dat-lich-google-calendar` (plugin và toolset cùng tên) |
| Nhóm | Lịch hẹn |
| Cần trước | đã **Kết nối Google** trên trang quản lý VPS (token Google dùng chung với add-on Google Sheets & Drive), với quyền Google Calendar |
| Thư viện Python | không, chỉ thư viện chuẩn |

Bốn tool cho Hermes của **chủ máy**:

| Tool | Làm gì |
|---|---|
| `lich_xem` | lịch hẹn từ ngày đến ngày (≤ 31 ngày) |
| `lich_gio_trong` | khoảng giờ trống trong ngày, trong giờ làm việc, đủ dài cho một cuộc hẹn |
| `lich_dat_hen` | đặt lịch; trùng lịch khác thì trả `trung_lich`, chỉ đặt chồng khi `cho_phep_trung` |
| `lich_huy_hen` | huỷ theo `event_id` |

## Ai dùng được

Chủ máy dùng qua:
- bảng điều khiển Hermes;
- ứng dụng Hermes trên máy tính;
- dòng lệnh;
- lịch chạy tự động.

Tool **không** tới widget web, Zalo OA, Fanpage, cũng không tới bot Telegram/WhatsApp/Slack/Discord, kể cả bot của chủ máy. Khách lạ không đặt hay huỷ lịch được bằng cách chat.

## Biến môi trường (tuỳ chọn)

| Biến | Mặc định |
|---|---|
| `LICH_HEN_CALENDAR_ID` | `primary` |
| `LICH_HEN_TIMEZONE` | `Asia/Ho_Chi_Minh` |
| `LICH_HEN_GIO_LAM` | `08:00-18:00` |
| `GOOGLE_TOKEN_PATH` | `/opt/data/google_token.json` |

## Quyền Google

Tool cần scope `https://www.googleapis.com/auth/calendar.events`. Token thiếu scope này thì tool trả câu hướng dẫn **Kết nối lại Google**, không gọi Google.

## Cách chạy

- Token hết hạn ⇒ làm mới một lần bằng `refresh_token`. Chỉ gửi tới `https://oauth2.googleapis.com/` (token trỏ chỗ khác thì từ chối), rồi ghi lại tệp token (atomic).
- Lỗi nào cũng trả một câu tiếng Việt; không bao giờ lộ token hay traceback.
