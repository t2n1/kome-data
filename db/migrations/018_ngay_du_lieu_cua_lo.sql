-- Ô cảnh báo "hôm nay chưa có dữ liệu" cần biết dữ liệu của lô MANG NGÀY NÀO,
-- chứ không phải lô được nạp lúc nào. Hai thứ đó khác nhau đúng vào lúc quan
-- trọng: hôm nay nạp bù file của tuần trước thì kho VẪN chưa có dữ liệu hôm
-- nay, dù meta.ingest_batch.loaded_at là hôm nay.
--
-- Vì sao không suy ngược từ dữ liệu đã nạp: core.dim_customer là SCD2 — ngày
-- nào khách không đổi gì thì nạp 得意先全情報 xong KHÔNG sinh dòng nào mang
-- ngày hôm nay, nên nguồn khách hàng sẽ luôn trông như thiếu dù nhân viên đã
-- làm đúng. Ngày vốn nằm sẵn trong tên file OBC, nên lưu thẳng vào lô.
ALTER TABLE meta.ingest_batch ADD COLUMN data_date date;

COMMENT ON COLUMN meta.ingest_batch.data_date IS
  'Ngày của DỮ LIỆU, tách từ tên file OBC (<tên>_YYYYMMDD.xlsx). Khác loaded_at.';

-- Lấp ngược cho các lô nạp trước migration này. Mọi tên file OBC đều theo mẫu
-- <tên>_YYYYMMDD.xlsx — đo trên CSDL thật ngày 2026-09-17: 23/23 lô khớp.
UPDATE meta.ingest_batch
   SET data_date = to_date(substring(source_file from '_(\d{8})\.xlsx$'), 'YYYYMMDD')
 WHERE data_date IS NULL;

-- NOT NULL đặt SAU khi lấp là CÓ CHỦ Ý: còn lô nào không tách được ngày thì
-- migration chết ngay tại dòng này, ồn ào và sửa được. Một NULL lọt qua sẽ làm
-- ô cảnh báo im lặng đúng vào lúc nó cần lên tiếng — kiểu hỏng tệ nhất cho một
-- thứ mà người dùng tin là "không đỏ nghĩa là ổn".
ALTER TABLE meta.ingest_batch ALTER COLUMN data_date SET NOT NULL;
