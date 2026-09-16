CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS meta;

COMMENT ON SCHEMA core IS 'Dữ liệu OBC đã chuẩn hoá. CHỈ ĐỌC với mọi ứng dụng.';
COMMENT ON SCHEMA mart IS 'Bảng tổng hợp cho báo cáo. Định nghĩa chỉ số nằm ở đây.';
COMMENT ON SCHEMA app IS 'Dữ liệu do ứng dụng sinh ra. Đọc-ghi.';
COMMENT ON SCHEMA meta IS 'Nhật ký nạp, trạng thái migration.';
