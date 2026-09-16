-- Kỳ kế toán THẬT của 株式会社KOME: 1 tháng 8 → 31 tháng 7 năm sau.
--
-- Migration 004 đã tạo cột `fiscal_year` theo năm tài chính Nhật CHUẨN (1/4 → 31/3).
-- Đó là mặc định của Nhật, NHƯNG KHÔNG PHẢI kỳ của công ty này. Không sửa được 004
-- (luật bất biến: migration đã chạy thì không đụng), nên thêm cột mới ở đây và
-- ghi chú cảnh báo lên cột cũ để không ai dùng nhầm.
--
-- Vì sao quan trọng: tháng 7 là THÁNG CHỐT KỲ. Dùng lịch 4月始まり thì tháng 7 rơi vào
-- giữa kỳ, và khuôn mẫu "tỷ suất tụt dần về cuối kỳ" không lộ ra. Đã kiểm chứng trên
-- dữ liệu thật: tháng 7 là tháng tỷ suất thấp nhất ở CẢ HAI kỳ (30,3% và 26,5%).

ALTER TABLE core.dim_date
    ADD COLUMN company_fy         integer,   -- năm KẾT THÚC kỳ: 2026 = kỳ 1/8/2025 → 31/7/2026
    ADD COLUMN company_fy_label   text,      -- 'Kỳ 2026-07'
    ADD COLUMN company_fy_month   integer,   -- tháng thứ mấy trong kỳ: 8月=1 … 7月=12
    ADD COLUMN company_fy_quarter integer,   -- quý trong kỳ: 8-10月=1, 11-1月=2, 2-4月=3, 5-7月=4
    ADD COLUMN is_fy_end_month    boolean;   -- tháng 7 = tháng chốt kỳ

UPDATE core.dim_date SET
    company_fy         = CASE WHEN month >= 8 THEN year + 1 ELSE year END,
    company_fy_label   = 'Kỳ ' || (CASE WHEN month >= 8 THEN year + 1 ELSE year END)::text || '-07',
    company_fy_month   = ((month + 4) % 12) + 1,
    company_fy_quarter = (((month + 4) % 12) / 3) + 1,
    is_fy_end_month    = (month = 7);

ALTER TABLE core.dim_date
    ALTER COLUMN company_fy         SET NOT NULL,
    ALTER COLUMN company_fy_label   SET NOT NULL,
    ALTER COLUMN company_fy_month   SET NOT NULL,
    ALTER COLUMN company_fy_quarter SET NOT NULL,
    ALTER COLUMN is_fy_end_month    SET NOT NULL;

CREATE INDEX ON core.dim_date (company_fy, company_fy_month);

COMMENT ON COLUMN core.dim_date.fiscal_year IS
  'KHÔNG PHẢI kỳ của công ty này. Đây là năm tài chính Nhật chuẩn (1/4 → 31/3), giữ lại
   để đối chiếu với tài liệu bên ngoài. Báo cáo nội bộ phải dùng company_fy.';
COMMENT ON COLUMN core.dim_date.company_fy IS
  'Kỳ kế toán của 株式会社KOME: 1/8 → 31/7. Đánh số theo năm KẾT THÚC kỳ,
   ví dụ company_fy = 2026 nghĩa là kỳ 2025-08-01 → 2026-07-31.';
COMMENT ON COLUMN core.dim_date.company_fy_month IS
  'Tháng thứ mấy trong kỳ: tháng 8 = 1, tháng 9 = 2, …, tháng 7 = 12 (tháng chốt kỳ).
   Dùng cột này khi so sánh cùng kỳ giữa các năm, đừng dùng số tháng dương lịch.';
