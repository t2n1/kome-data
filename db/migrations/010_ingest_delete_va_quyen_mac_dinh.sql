-- 010: vá ba lỗ hổng của 009_roles.sql, phát hiện ở đợt review cuối Giai đoạn 0.
--
-- LƯU Ý BẤT BIẾN: ALTER DEFAULT PRIVILEGES dưới đây KHÔNG có mệnh đề FOR ROLE,
-- nên nó chỉ áp cho bảng/sequence do CHÍNH vai trò đang chạy migration tạo ra.
-- Migration vì vậy PHẢI luôn chạy bằng vai trò `postgres`. Đổi vai trò chạy
-- migration thì quyền mặc định sẽ âm thầm không áp dụng cho bảng mới.

-- (1) Hoàn tác một lô là DELETE FROM core.… WHERE batch_id = %s
--     (kome/pipeline.py:undo_batch). 009 chỉ cấp SELECT/INSERT/UPDATE, nên
--     ngay khi runbook bảo đổi DATABASE_URL sang kome_ingest_user thì sự cố
--     ĐẦU BẢNG của runbook ("Nạp nhầm file" -> hoàn tác) và route /undo/{id}
--     đều chết với permission denied — đúng lúc người ta đang hoảng.
GRANT DELETE ON ALL TABLES IN SCHEMA core TO kome_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA core
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kome_ingest;

-- meta CỐ Ý không có DELETE: meta.ingest_batch là bảng lịch sử, hoàn tác chỉ
-- đặt undone_at, không bao giờ xoá dòng (luật bất biến #6). CSDL giữ luôn.
ALTER DEFAULT PRIVILEGES IN SCHEMA meta
    GRANT SELECT, INSERT, UPDATE ON TABLES TO kome_ingest;

-- (2) 009 có ALTER DEFAULT PRIVILEGES cho TABLES nhưng THIẾU cho SEQUENCES:
--     bảng mới có bigserial ở giai đoạn sau sẽ INSERT được nhưng lỗi
--     "permission denied for sequence".
ALTER DEFAULT PRIVILEGES IN SCHEMA core, meta
    GRANT USAGE, SELECT ON SEQUENCES TO kome_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA app
    GRANT USAGE, SELECT ON SEQUENCES TO kome_app;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA core, meta TO kome_ingest;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA app TO kome_app;

-- (3) SCD2: khoảng thời gian âm là dữ liệu chết (mọi truy vấn lịch sử
--     `valid_from <= d AND (valid_to IS NULL OR valid_to >= d)` sẽ không trả
--     về ngày nào). kome/loaders/customer.py đã sửa để cập nhật tại chỗ khi
--     xuất lại trong cùng ngày; CHECK này để CSDL cũng chặn.
ALTER TABLE core.dim_customer
    ADD CONSTRAINT dim_customer_khoang_hop_le
    CHECK (valid_to IS NULL OR valid_to >= valid_from);
