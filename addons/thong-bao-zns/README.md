# Thông báo ZNS (Zalo OA)

| | |
|---|---|
| Tên | `thong-bao-zns` (plugin và toolset cùng tên) |
| Nhóm | Thông báo |
| Cần trước | Zalo OA đã kết nối trên trang quản lý VPS, mẫu tin ZNS đã được Zalo duyệt, số dư ZNS của OA |
| Thư viện Python | không, chỉ thư viện chuẩn |
| Trạng thái | chờ Moza mở ZNS; chưa phát hành |

Hai tool cho Hermes của **chủ máy**:

| Tool | Làm gì |
|---|---|
| `zns_mau_tin` | các mẫu tin ZNS chủ máy cho phép, kèm tham số và giá mỗi tin |
| `zns_gui` | gửi một mẫu tới một số di động; số được đổi sang dạng `84…`; `ma_theo_doi` để không gửi trùng khi thử lại |

- Máy **không giữ token Zalo OA**. Mọi lần gửi đi qua portal Moza (chỉ qua https), bằng token của trợ lý mà Moza đặt sẵn trên máy. Portal kiểm mẫu tin, tham số và hạn mức trong ngày.
- Mỗi tin Zalo tính phí theo bảng giá ZNS của Zalo, trừ vào số dư của OA.
- Tool chỉ phục vụ chủ máy. Không tới widget web, Zalo OA, Fanpage, cũng không tới bot Telegram/WhatsApp/Slack/Discord, kể cả bot của chủ máy. Nhờ vậy khách lạ không khiến OA gửi tin.
