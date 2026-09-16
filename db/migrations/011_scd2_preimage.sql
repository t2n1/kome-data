-- 011: giữ "ảnh trước" của các dòng SCD2 bị ĐÈ TẠI CHỖ, để hoàn tác trả lại
-- đúng giá trị cũ thay vì xoá mất khách.
--
-- Bối cảnh: 010 + kome/loaders/customer.py sửa lỗi khoảng thời gian âm bằng
-- cách CẬP NHẬT TẠI CHỖ khi xuất lại trong cùng ngày (không đóng-rồi-mở-mới).
-- Nhưng dòng bị đè khi ấy mang luôn batch_id của lô mới, trong khi hoàn tác là
-- `DELETE FROM core.dim_customer WHERE batch_id = %s` (kome/pipeline.py):
-- dòng DUY NHẤT của khách bị xoá hẳn, bước "mở lại phiên bản trước đó" không
-- còn gì để mở -> khách biến mất khỏi CSDL. Chính là sự cố ĐẦU BẢNG của
-- docs/runbook.md: nạp 13:30 -> sửa trong OBC -> nạp lại cùng ngày -> Hoàn tác.
--
-- Cách chữa: trước khi đè, loader chép giá trị cũ (và batch_id cũ) của từng
-- dòng vào cột này của CHÍNH LÔ ĐANG NẠP. undo_batch() hoàn nguyên các dòng ấy
-- TRƯỚC khi xoá; hoàn nguyên xong batch_id quay về lô cũ nên câu DELETE không
-- còn đụng tới chúng.
--
-- Đặt ở meta.ingest_batch (không phải bảng phụ mới, cũng không phải cột trên
-- core.dim_customer): hoàn tác vốn làm theo từng LÔ, và mỗi lô giữ ảnh trước
-- của riêng nó nên sửa nhiều lần trong ngày thì lùi được từng bước một.
ALTER TABLE meta.ingest_batch ADD COLUMN scd2_preimage jsonb;

COMMENT ON COLUMN meta.ingest_batch.scd2_preimage IS
  'Giá trị TRƯỚC KHI ĐÈ của các dòng SCD2 lô này sửa tại chỗ (xuất lại trong '
  'cùng ngày). Dạng [{"code":…, "batch_id":…, "values":{cột: giá trị}}]. '
  'NULL = lô này không đè lên dòng nào. Chỉ undo_batch() đọc.';
