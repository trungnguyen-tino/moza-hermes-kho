Dùng kỹ năng này khi chủ trợ lý muốn ghi một khách hoặc một đơn hàng vào sổ trên
Google Sheet, tra lại đơn đã ghi, hoặc tổng hợp đơn theo ngày. Chỉ làm theo yêu cầu
của chủ trợ lý; không tự ghi gì khi đang trả lời khách lạ.

Kỹ năng dùng các tool của add-on Google Workspace: `gdrive_list`, `gsheet_read`,
`gsheet_append`. Thiếu các tool này (add-on chưa bật) hoặc tool trả lời "Chưa kết nối
Google" thì dừng và nói với chủ: "Vào portal → VPS → Hermes → Add-on, bật Google
Sheets & Drive; rồi tab Kênh → Kết nối Google và chọn file Sheet làm sổ đơn."

## 1. Tìm sổ đơn

1. Nếu chủ đã nói ID hoặc đường dẫn Sheet trong cuộc trò chuyện, dùng ID đó (phần
   giữa `/d/` và `/edit` của đường dẫn).
2. Nếu chưa, gọi `gdrive_list` và chọn file có `mime_type`
   `application/vnd.google-apps.spreadsheet` mà tên có chữ "đơn", "khách" hoặc
   "order". Có nhiều file hợp thì hỏi chủ chọn một, đừng tự đoán.
3. Không thấy file nào: nhờ chủ tạo một Google Sheet trống tên "Sổ đơn" và chọn nó
   bằng nút "Chọn tài liệu từ Drive" trong tab Kênh của portal. Không tự tạo file
   khác thay thế.

Ghi nhớ ID sổ đơn trong cuộc trò chuyện này để các lần sau không hỏi lại.

## 2. Đảm bảo hàng tiêu đề

Đọc `gsheet_read` vùng `A1:I1` của trang đầu tiên.

- Trống: ghi hàng tiêu đề bằng `gsheet_append` với vùng `A1`:
  `Thời gian | Kênh | Tên khách | Số điện thoại | Sản phẩm / dịch vụ | Số lượng | Thành tiền | Ghi chú | Trạng thái`
- Đã có tiêu đề khác mẫu: dùng đúng thứ tự cột đang có, không ghi đè, không chèn cột.

## 3. Ghi một đơn

1. Lấy từ lời chủ (hoặc đoạn tin nhắn chủ dán vào): tên khách, số điện thoại, sản
   phẩm/dịch vụ, số lượng, thành tiền, kênh (Zalo, Fanpage, gọi điện, tại quầy…),
   ghi chú. Thiếu tên khách hoặc sản phẩm thì hỏi lại chủ trước khi ghi.
2. Chuẩn hoá:
   - Thời gian: giờ Việt Nam lúc ghi, dạng `YYYY-MM-DD HH:MM`, trừ khi chủ nói giờ khác.
   - Số điện thoại: chỉ chữ số, bắt đầu bằng `0` (đổi `+84`/`84` đầu số thành `0`).
   - Thành tiền: số nguyên đồng, không dấu chấm, không chữ "đ" (ví dụ `350000`).
   - Trạng thái: `Mới` nếu chủ không nói khác.
3. Nhắc lại cho chủ một dòng tóm tắt đơn và chỉ ghi khi chủ đồng ý (hoặc chủ đã nói
   rõ "ghi luôn").
4. Gọi `gsheet_append` một lần với một hàng theo đúng thứ tự cột, vùng `A1`.
5. Báo lại: "Đã ghi đơn của <tên> vào sổ." Không đọc lại số điện thoại đầy đủ trong
   câu trả lời; chỉ 4 số cuối.

Nhiều đơn cùng lúc: gom thành nhiều hàng trong MỘT lần `gsheet_append`.

## 4. Tra cứu và tổng hợp

- Tra theo tên, 4 số cuối điện thoại hoặc ngày: đọc `gsheet_read` vùng `A1:I1000`,
  lọc trong đầu, trả lời ngắn gọn (tối đa 10 đơn; nhiều hơn thì nói tổng số và hỏi
  chủ muốn lọc thêm theo gì).
- Tổng hợp trong ngày: đếm số đơn, cộng cột Thành tiền của các hàng có Thời gian bắt
  đầu bằng ngày đó, chia theo Trạng thái.
- Đổi trạng thái hay sửa một đơn cũ: tool chỉ thêm được hàng mới. Ghi một hàng mới
  với trạng thái mới và ghi chú "Cập nhật đơn lúc <thời gian cũ>", rồi nói với chủ
  rằng dòng cũ vẫn còn trong sổ.

## 5. Không làm

- Không ghi mật khẩu, số thẻ, mã OTP hay giấy tờ tuỳ thân vào sổ.
- Không xoá hay ghi đè dữ liệu cũ (tool không cho, và cũng không được nhờ cách khác).
- Không gửi nội dung sổ đơn cho người không phải chủ trợ lý.
