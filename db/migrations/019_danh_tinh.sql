-- 019: danh tính — ai đang đăng nhập, và ai phụ trách khách nào.
--
-- LƯU Ý BẤT BIẾN: ALTER DEFAULT PRIVILEGES của 009/010 KHÔNG có mệnh đề
-- FOR ROLE, nên file này (như mọi migration) PHẢI chạy bằng vai trò
-- `postgres`. Chạy bằng vai trò khác thì hai bảng dưới đây âm thầm không
-- nhận quyền mặc định, và lỗi chỉ lộ ra bằng một `permission denied` nhiều
-- tháng sau.

-- 担当者 của OBC. KHÁI NIỆM NÀY KHÔNG PHẢI "người dùng web": OBC có 5 người
-- phụ trách khách, còn web lên đơn có 7 tài khoản (gồm 2 arubaito chỉ nhập
-- đơn, không phụ trách khách nào). Hai bảng riêng, không bao giờ trộn —
-- xem CLAUDE.md, mục "Bẫy đã biết" số 5.
CREATE TABLE core.dim_salesperson (
    salesperson_code text PRIMARY KEY,
    ten              text NOT NULL
);

-- Số liệu lấy từ đặc tả nền §12.2 (đã ĐO từ dữ liệu thật), không suy đoán mới.
INSERT INTO core.dim_salesperson (salesperson_code, ten) VALUES
    ('0002', '西村 巧'),
    ('0004', 'TRINH CONG MINH'),
    ('0102', 'NGUYEN PHUONG DUNG'),
    ('0104', 'TRAN THI LAN THANH'),
    ('0105', 'HA HUY LONG');

CREATE TABLE app.nguoi_dung (
    id                   bigserial PRIMARY KEY,
    ten_dang_nhap        text UNIQUE NOT NULL,
    -- scrypt + salt RIÊNG từng người (kome/web/nguoi_dung.py). Salt riêng để
    -- hai người vô tình đặt trùng mật khẩu vẫn ra hai hash khác nhau.
    mat_khau_hash        bytea NOT NULL,
    mat_khau_salt        bytea NOT NULL,
    -- NULL = người này không phụ trách khách nào (chủ DN, kế toán, kho).
    -- Khi NULL thì trang khách hàng không lọc gì.
    salesperson_code     text NULL REFERENCES core.dim_salesperson,
    -- Cổng vào màn Kho dữ liệu: nạp file, hoàn tác lô. Mặc định FALSE —
    -- quyền phá huỷ phải được cấp TƯỜNG MINH, không phải thứ ai cũng có vì
    -- người tạo tài khoản quên đặt.
    duoc_vao_kho_du_lieu boolean NOT NULL DEFAULT false,
    tao_luc              timestamptz NOT NULL DEFAULT now()
);

-- kome_app đọc được nhật ký nạp. Vai trò này CỐ Ý không ghi được vào `core`,
-- nhưng việc nó không ĐỌC được `meta` là một khoảng trống chứ không phải chủ
-- ý: trang chủ `/` cần meta.ingest_batch cho ô "hôm nay đã có dữ liệu chưa".
-- Chỉ SELECT — không INSERT/UPDATE/DELETE.
-- (009 đã cấp USAGE trên schema meta cho kome_app; nhắc lại cho đọc được
--  trọn ý ở một chỗ, GRANT là thao tác idempotent.)
GRANT USAGE ON SCHEMA meta TO kome_app;
GRANT SELECT ON meta.ingest_batch TO kome_app;

-- kome_report (công cụ báo cáo/BI ngoài ứng dụng) tự nhận SELECT trên mọi
-- bảng schema `app` theo ALTER DEFAULT PRIVILEGES của 009 — kể cả bảng vừa
-- tạo ở trên. Một công cụ vẽ biểu đồ doanh thu không có việc gì phải đọc
-- hash và salt mật khẩu của nhân viên. Thu lại.
REVOKE SELECT ON app.nguoi_dung FROM kome_report;
