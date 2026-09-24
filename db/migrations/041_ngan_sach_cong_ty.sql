-- 041: ngân sách CÔNG TY theo tháng — doanh thu + lãi gộp; chỉ tiêu từng người thêm lãi gộp.
--
-- Chủ DN 2026-09-24: "đặt ngân sách theo từng tháng, có doanh thu và lợi nhuận" — chọn
-- công ty + từng người, lợi nhuận = lãi gộp 粗利益. Đặc tả:
-- docs/superpowers/specs/2026-09-24-ngan-sach-cong-ty-design.md.
--
-- LUẬT: ngân sách công ty là số NHẬP THẲNG, KHÔNG phải tổng từng người. Chưa đặt = "chưa
-- đặt" — không rơi về tổng từng người (hai định nghĩa cùng tên là hai con số nói hai điều).
--
-- PHẢI chạy bằng vai trò `postgres` (ALTER DEFAULT PRIVILEGES của 009 không có FOR ROLE).

-- ---------------------------------------------------------------------------
-- Bảng
-- ---------------------------------------------------------------------------

CREATE TABLE app.ngan_sach_cong_ty (
    -- date mùng 1 + khoá ngoại dim_date: cùng lý lẽ app.ngan_sach.thang (026).
    thang      date NOT NULL PRIMARY KEY REFERENCES core.dim_date (date_key)
                    CHECK (extract(day FROM thang) = 1),
    -- NULL = chưa đặt; 0 = đặt bằng không. Tiền luôn là số nguyên yên.
    doanh_thu  bigint NULL CHECK (doanh_thu >= 0),
    lai_gop    bigint NULL CHECK (lai_gop >= 0),
    sua_luc    timestamptz NOT NULL DEFAULT now(),
    sua_boi    bigint NULL REFERENCES app.nguoi_dung,
    -- Dòng không có ô nào là dòng thừa — xoá thì xoá cả dòng.
    CHECK (doanh_thu IS NOT NULL OR lai_gop IS NOT NULL)
);

COMMENT ON TABLE app.ngan_sach_cong_ty IS
  'Ngân sách của CẢ CÔNG TY theo tháng, nhập thẳng — không phải tổng của app.ngan_sach.
   NULL = chưa đặt, 0 = đặt bằng không.';

-- Từng người: thêm lãi gộp; doanh thu thôi bắt buộc (đặt lãi gộp mà chưa đặt doanh thu
-- là hợp lệ). muc_tieu giữ tên cũ = chỉ tiêu DOANH THU.
ALTER TABLE app.ngan_sach ALTER COLUMN muc_tieu DROP NOT NULL;
ALTER TABLE app.ngan_sach ADD COLUMN lai_gop bigint NULL CHECK (lai_gop >= 0);
ALTER TABLE app.ngan_sach ADD CONSTRAINT ngan_sach_co_it_nhat_mot_o
    CHECK (muc_tieu IS NOT NULL OR lai_gop IS NOT NULL);

-- MỘT sổ cho cả hai bảng: salesperson_code NULL = công ty; chi_so nói ô nào. Giữ một sổ
-- là để kome/web/anh_chup.py::_PHIEN_BAN (đọc max(id) của sổ này) và /nhat-ky không cần
-- nhánh thứ hai.
ALTER TABLE app.ngan_sach_nhat_ky ALTER COLUMN salesperson_code DROP NOT NULL;
ALTER TABLE app.ngan_sach_nhat_ky ADD COLUMN chi_so text NOT NULL DEFAULT 'doanh_thu'
    CHECK (chi_so IN ('doanh_thu', 'lai_gop'));

-- ---------------------------------------------------------------------------
-- mart
-- ---------------------------------------------------------------------------

-- Từng người: thêm cột lãi gộp ở CUỐI (CREATE OR REPLACE chỉ cho nối cột).
CREATE OR REPLACE VIEW mart.ngan_sach_thang AS
SELECT to_char(n.thang, 'YYYY-MM') AS thang,
       d.company_fy,
       n.salesperson_code,
       n.muc_tieu,
       n.lai_gop                   AS muc_tieu_lg
FROM app.ngan_sach n
JOIN core.dim_date d ON d.date_key = n.thang;

-- Công ty: chỗ DUY NHẤT đổi khoá date -> 'YYYY-MM' của bảng công ty.
CREATE VIEW mart.ngan_sach_cong_ty_thang AS
SELECT to_char(n.thang, 'YYYY-MM') AS thang,
       d.company_fy,
       n.doanh_thu,
       n.lai_gop
FROM app.ngan_sach_cong_ty n
JOIN core.dim_date d ON d.date_key = n.thang;

-- Tiến độ công ty. FULL JOIN (bất biến của tien_do_ngan_sach): tháng có bán mà chưa đặt
-- và tháng đã đặt mà chưa bán đều có dòng. Mốc đến hôm nay = ngân sách × ngày làm việc
-- đã qua ÷ ngày làm việc của tháng — đúng công thức muc_tieu_den_hom_nay của từng người.
CREATE VIEW mart.tien_do_cong_ty AS
SELECT coalesce(b.thang, n.thang)                          AS thang,
       coalesce(b.company_fy, n.company_fy)                AS company_fy,
       n.doanh_thu                                         AS muc_tieu,
       n.lai_gop                                           AS muc_tieu_lg,
       coalesce(b.doanh_thu_thuan, 0)::bigint              AS thuc_te,
       coalesce(b.lai_gop, 0)::bigint                      AS thuc_te_lg,
       k.ngay_kd,
       k.ngay_kd_da_qua,
       (n.doanh_thu * k.ngay_kd_da_qua::numeric / nullif(k.ngay_kd, 0))::bigint
                                                           AS muc_tieu_den_hom_nay,
       (n.lai_gop * k.ngay_kd_da_qua::numeric / nullif(k.ngay_kd, 0))::bigint
                                                           AS muc_tieu_lg_den_hom_nay,
       coalesce(b.doanh_thu_thuan, 0)::numeric / nullif(n.doanh_thu, 0) AS tien_do,
       coalesce(b.lai_gop, 0)::numeric / nullif(n.lai_gop, 0)           AS tien_do_lg
FROM mart.ban_theo_thang b
FULL JOIN mart.ngan_sach_cong_ty_thang n ON n.thang = b.thang
LEFT JOIN mart.ngay_kinh_doanh k ON k.thang = coalesce(b.thang, n.thang);

COMMENT ON VIEW mart.tien_do_cong_ty IS
  'Tiến độ ngân sách CÔNG TY (app.ngan_sach_cong_ty, nhập thẳng — không cộng từ từng
   người). FULL JOIN: đổi thành LEFT JOIN theo bất kỳ chiều nào là mất dòng.';

-- Từng người: thêm bốn cột lãi gộp ở CUỐI, phần trước giữ NGUYÊN VĂN 028.
CREATE OR REPLACE VIEW mart.tien_do_ngan_sach AS
WITH bt AS MATERIALIZED (
    SELECT * FROM mart.ban_theo_nhan_vien_thang
),
ct AS (
    SELECT DISTINCT thang FROM bt
)
SELECT coalesce(bt.thang, n.thang)                        AS thang,
       coalesce(bt.company_fy, n.company_fy)              AS company_fy,
       coalesce(bt.salesperson_code, n.salesperson_code)  AS salesperson_code,
       n.muc_tieu,
       coalesce(bt.doanh_thu_thuan, 0)::bigint            AS thuc_te,
       k.ngay_kd,
       k.ngay_kd_da_qua,
       (n.muc_tieu * k.ngay_kd_da_qua::numeric / nullif(k.ngay_kd, 0))::bigint
                                                         AS muc_tieu_den_hom_nay,
       coalesce(bt.doanh_thu_thuan, 0)::numeric / nullif(n.muc_tieu, 0) AS tien_do,
       CASE WHEN ct.thang IS NOT NULL
            THEN coalesce(tr.doanh_thu_thuan, 0)::bigint END      AS cung_ky,
       (ct.thang IS NOT NULL)                                     AS co_cung_ky,
       CASE WHEN tr.doanh_thu_thuan > 0
            THEN coalesce(bt.doanh_thu_thuan, 0)::numeric
                 / tr.doanh_thu_thuan - 1 END                     AS tang_truong,
       n.muc_tieu_lg,
       coalesce(bt.lai_gop, 0)::bigint                            AS thuc_te_lg,
       (n.muc_tieu_lg * k.ngay_kd_da_qua::numeric / nullif(k.ngay_kd, 0))::bigint
                                                                  AS muc_tieu_lg_den_hom_nay,
       coalesce(bt.lai_gop, 0)::numeric / nullif(n.muc_tieu_lg, 0) AS tien_do_lg
FROM bt
FULL JOIN mart.ngan_sach_thang     n  ON n.thang = bt.thang
                                     AND n.salesperson_code = bt.salesperson_code
LEFT JOIN mart.ngay_kinh_doanh     k  ON k.thang = coalesce(bt.thang, n.thang)
LEFT JOIN bt                       tr ON tr.salesperson_code
                                          = coalesce(bt.salesperson_code, n.salesperson_code)
                                     AND tr.thang = to_char(
                                           to_date(coalesce(bt.thang, n.thang), 'YYYY-MM')
                                           - interval '1 year', 'YYYY-MM')
LEFT JOIN ct                          ON ct.thang = to_char(
                                           to_date(coalesce(bt.thang, n.thang), 'YYYY-MM')
                                           - interval '1 year', 'YYYY-MM');

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
