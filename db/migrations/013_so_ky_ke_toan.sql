-- Số kỳ kế toán theo cách công ty tự gọi: 第6期, 第7期, 第8期…
--
-- Chủ sở hữu xác nhận: Kỳ 8 = 2026-08-01 → 2027-07-31, Kỳ 7 là năm trước đó,
-- Kỳ 6 trước nữa. Suy ra quy luật: số kỳ = (năm KẾT THÚC kỳ) − 2019.
--   company_fy 2025 → Kỳ 6   (2024-08-01 → 2025-07-31)
--   company_fy 2026 → Kỳ 7   (2025-08-01 → 2026-07-31)
--   company_fy 2027 → Kỳ 8   (2026-08-01 → 2027-07-31)
--
-- Nghĩa là Kỳ 1 kết thúc 31/7/2020 — công ty bắt đầu kỳ đầu khoảng tháng 8/2019.
-- Nếu mốc này sai thì SỬA Ở ĐÂY bằng một migration mới, đừng sửa file này.
--
-- Vì sao cần: `company_fy` (năm kết thúc) là cách MÁY đánh số, còn nhân viên và
-- ban giám đốc gọi nhau bằng "kỳ 7", "kỳ 8". Báo cáo phải nói đúng ngôn ngữ của
-- người đọc, nếu không họ phải tự quy đổi mỗi lần nhìn.

ALTER TABLE core.dim_date
    ADD COLUMN company_fy_no integer;

UPDATE core.dim_date SET
    company_fy_no  = company_fy - 2019,
    -- Nhãn đổi sang dạng người dùng thật sự đọc: "Kỳ 7 (2025-08 → 2026-07)"
    company_fy_label = 'Kỳ ' || (company_fy - 2019)::text
                       || ' (' || (company_fy - 1)::text || '-08 → ' || company_fy::text || '-07)';

ALTER TABLE core.dim_date
    ALTER COLUMN company_fy_no SET NOT NULL,
    ADD CONSTRAINT dim_date_company_fy_no_duong CHECK (company_fy_no > 0);

CREATE INDEX ON core.dim_date (company_fy_no);

COMMENT ON COLUMN core.dim_date.company_fy_no IS
  'Số kỳ kế toán theo cách công ty tự gọi (第N期). Kỳ 8 = 2026-08-01 → 2027-07-31.
   Quy luật: company_fy_no = company_fy - 2019. DÙNG CỘT NÀY trong mọi thứ hiển thị
   cho người dùng; company_fy chỉ để tính toán và sắp xếp.';
