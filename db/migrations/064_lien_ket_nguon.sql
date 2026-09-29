-- 064 — Liên kết nguồn (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §11, Đợt 3).
-- Chủ DN chốt: KHÔNG lưu ảnh. File gốc nằm trên Google Drive dùng chung (Bang-gia-doi-thu/Tháng N/<bên>/);
-- web chỉ TRỎ tới: một link thư mục "Tháng N" mỗi tháng + link bằng chứng tuỳ chọn cho giá sale nhập.

CREATE TABLE app.thu_muc_nguon (
    thang     date PRIMARY KEY CHECK (extract(day FROM thang) = 1),
    lien_ket  text NOT NULL CHECK (lien_ket ~ '^https://[^[:space:]]+$' AND length(lien_ket) <= 2000),
    sua_luc   timestamptz NOT NULL DEFAULT now(),
    sua_boi   bigint REFERENCES app.nguoi_dung(id)
);
-- Sửa được (thay link sai) — KHÔNG chỉ-thêm; lịch sử nằm ở app.doi_thu_nhat_ky (loai 'thu_muc', cùng giao dịch).

ALTER TABLE app.gia_doi_thu_tay ADD COLUMN lien_ket_bang_chung text
    CHECK (lien_ket_bang_chung ~ '^https://[^[:space:]]+$' AND length(lien_ket_bang_chung) <= 2000);

ALTER TABLE app.doi_thu_nhat_ky DROP CONSTRAINT doi_thu_nhat_ky_loai_check;
ALTER TABLE app.doi_thu_nhat_ky ADD CONSTRAINT doi_thu_nhat_ky_loai_check
    CHECK (loai IN ('xac_nhan', 'sua', 'gia_moi', 'them', 'ghep', 'nhom', 'quy_cach', 'doi_thu', 'thu_muc'));

-- ĐÚNG MỘT chỗ định nghĩa nguồn của một quan sát (khoá (nguon, id) như mart.gia_doi_thu_quan_sat).
-- Tháng của dòng nạp = tháng của data_date của LÔ (gói tháng 8 dựng với --ngay 2026-08-31 → thư mục "Tháng 8"),
-- KHÔNG theo ngay_nguon (ngày trên từng file có thể là đầu tháng hay tháng trước).
CREATE VIEW mart.nguon_quan_sat AS
SELECT 'nap'::text AS nguon, f.id,
       date_trunc('month', b.data_date)::date AS thang_lo,
       tm.lien_ket                            AS lien_ket_thu_muc,
       d.web                                  AS web_ben,
       NULL::text                             AS lien_ket_bang_chung
FROM core.fact_gia_doi_thu f
JOIN meta.ingest_batch b ON b.batch_id = f.batch_id
LEFT JOIN app.thu_muc_nguon tm ON tm.thang = date_trunc('month', b.data_date)::date
LEFT JOIN app.doi_thu d ON d.ma = f.ma_doi_thu
UNION ALL
SELECT 'tay'::text, t.id, NULL::date, NULL::text, d.web, t.lien_ket_bang_chung
FROM app.gia_doi_thu_tay t
LEFT JOIN app.doi_thu d ON d.ma = t.ma_doi_thu;

GRANT SELECT ON mart.nguon_quan_sat TO kome_app, kome_report, kome_ingest;
GRANT SELECT ON app.thu_muc_nguon TO kome_report, kome_ingest;
