-- Vai trò KHÔNG có mật khẩu ở đây. Mật khẩu đặt riêng bằng CREATE USER ... LOGIN
-- PASSWORD tay trên SQL Editor của Supabase, không bao giờ nằm trong git (luật #5).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kome_ingest') THEN
        CREATE ROLE kome_ingest NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kome_app') THEN
        CREATE ROLE kome_app NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kome_report') THEN
        CREATE ROLE kome_report NOLOGIN;
    END IF;
END $$;

GRANT USAGE ON SCHEMA core, mart, meta TO kome_ingest, kome_app, kome_report;
GRANT USAGE ON SCHEMA app TO kome_app;

-- ingest: ghi được vào core và meta
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA core, meta TO kome_ingest;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA core, meta TO kome_ingest;

-- app: ĐỌC core (luật #1 — không bao giờ sửa dữ liệu OBC), đọc-ghi app
GRANT SELECT ON ALL TABLES IN SCHEMA core, mart TO kome_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO kome_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO kome_app;

-- report: chỉ đọc, mọi nơi
GRANT SELECT ON ALL TABLES IN SCHEMA core, mart, app TO kome_report;

-- Bảng tạo về sau cũng tự nhận quyền này
ALTER DEFAULT PRIVILEGES IN SCHEMA core, meta GRANT SELECT, INSERT, UPDATE ON TABLES TO kome_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA core, mart GRANT SELECT ON TABLES TO kome_app, kome_report;
ALTER DEFAULT PRIVILEGES IN SCHEMA app  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kome_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app  GRANT SELECT ON TABLES TO kome_report;
