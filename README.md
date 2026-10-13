# moza-hermes-kho — add-on Hermes do Moza soạn

Add-on cho Hermes Agent trên VPS của mozaai.vn. Mỗi add-on là một thư mục trong `addons/`.

Máy khách cài add-on bằng cách clone **đúng commit đã duyệt** của repo công khai này. Add-on miễn phí, do Moza soạn hoặc duyệt. Plugin cộng đồng trên GitHub cũng đi đúng quy trình dưới đây.

| Add-on | Loại | Cần trước | Trạng thái |
|---|---|---|---|
| [`khach-don-google-sheet`](addons/khach-don-google-sheet) — Sổ khách & đơn trên Google Sheet | kỹ năng (dùng tool có sẵn của add-on Google Sheets & Drive) | add-on Google Sheets & Drive bật, đã Kết nối Google, đã chọn Sheet | sẵn sàng |
| [`dat-lich-google-calendar`](addons/dat-lich-google-calendar) — Đặt lịch hẹn | plugin, 4 tool, chỉ dùng thư viện chuẩn | Kết nối Google **có quyền Google Calendar** | chờ Moza mở quyền Google Calendar |
| [`thong-bao-zns`](addons/thong-bao-zns) — Thông báo ZNS | plugin, 2 tool gửi qua portal Moza | Zalo OA, mẫu tin ZNS đã duyệt | chờ Moza mở ZNS |

## Add-on dùng ở đâu

Tool của add-on chỉ phục vụ **chủ máy**, qua bảng điều khiển Hermes, ứng dụng Hermes trên máy tính, dòng lệnh và lịch chạy tự động.

Tool add-on **không** tới:
- kênh người lạ tới được: widget web, Zalo OA, Fanpage;
- bot Telegram/WhatsApp/Slack/Discord, kể cả bot của chủ máy (chưa hỗ trợ).

## Viết một add-on

- **Kỹ năng** (ưu tiên khi tool có sẵn đã đủ):
  - `addon.yaml`: `kind: skill`, `name`, `title`, `description`, `category` dạng `moza-…`, `biz_group`, `customer_visible`, `requires`;
  - `SKILL.md` là thân kỹ năng, không có frontmatter.
- **Plugin Hermes.** Máy chạy lại các luật này trước khi cài:
  - `plugin.yaml`, tên `^[a-z0-9][a-z0-9_-]{0,62}$`, không trùng plugin của Moza;
  - không có:
    - `capabilities` hay `python_runtime: external`;
    - `pyproject.toml`, `package.json` hay symlink;
  - **chỉ** gọi thẳng `ctx.register_tool(...)`; hook, middleware, lệnh, đoạn system prompt và mọi `register_*` khác bị từ chối. Tham chiếu tới plugin context qua đường gián tiếp cũng bị từ chối: gán `ctx.register_x` vào biến, `getattr`/`setattr` với tên tính toán, `vars()`, `__dict__`;
  - `name` và `toolset` của tool ghi bằng chữ hoặc hằng số module;
  - toolset phải là toolset riêng của add-on: không phải `todo`, `rag`, `hermes-*`, `mcp-*`, `moza-*`, không trùng toolset của Hermes hay plugin khác; không `override=True`;
  - handler theo hợp đồng của Hermes: `handler(args, **context)` trả **chuỗi** (JSON cho kết quả có cấu trúc); schema là `{name, description, parameters}` (Hermes tự bọc `{"type": "function"}`);
  - **chưa nhận thư viện Python**: khai `python_dependencies`/`pip_dependencies` hay có `requirements.lock` đều bị từ chối. Dùng thư viện chuẩn;
  - bí mật đọc từ biến môi trường hay tệp Moza đặt sẵn trên máy. Không in token, không trả traceback cho model.
- Test đặt ở `tests/`, không đặt trong thư mục add-on (mọi tệp trong đó được cài lên máy). Chạy `scripts/test.sh`.

## Quy trình duyệt (mỗi commit một lần)

1. Commit vào nhánh mặc định của repo. Moza chỉ nhận commit nằm trên nhánh mặc định, không nhận commit của fork hay pull request.
2. Moza nhập commit đó (repo, SHA 40 ký tự, thư mục `addons/<tên>`):
   - đọc `plugin.yaml` và các tệp khai thư viện ở đúng SHA;
   - vi phạm luật ⇒ **từ chối kèm lý do**.
3. Moza quét mã của đúng commit bằng bộ quét bảo mật của Hermes và các luật trên. Báo cáo quét gắn vào bản nháp; báo cáo phải khớp đúng commit.
4. Người duyệt đọc mã của commit và phần thay đổi so với bản đang phát hành, rồi **duyệt & xuất bản** hoặc **từ chối**.
5. Máy khách cài đúng commit đã duyệt:
   - installer của Hermes ghim SHA, không ghi đè;
   - luật chạy lại trên cây vừa clone;
   - một lần khởi động lại Hermes, rồi kiểm công cụ của các kênh công khai.
6. Sửa add-on = commit mới = duyệt lại từ bước 2. Máy đang chạy bản cũ giữ nguyên tới khi chủ máy bấm **Cập nhật**.
