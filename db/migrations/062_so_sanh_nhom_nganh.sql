-- 062 — Thêm cột `nganh` vào mart.so_sanh_nhom (đặc tả 2026-09-29-thi-truong-doi-thu-design.md, đợt 1b).
-- Ngành của một nhóm = ngành PHỔ BIẾN NHẤT trong các mã KOME của nhóm (nhóm ngầm định = ngành của chính mã đó),
-- qua mart.ten_nganh 3 tham số (một chỗ viết nhãn ngành). Thân view GIỐNG HỆT 060; CREATE OR REPLACE VIEW chỉ cho
-- thêm cột ở CUỐI nên `nganh` đứng cuối. 059–061 đã chạy trên CSDL thật — không sửa, thay đổi đi qua file này.

CREATE OR REPLACE VIEW mart.so_sanh_nhom AS
WITH h AS MATERIALIZED (
    SELECT * FROM mart.gia_doi_thu_hien_hanh
    WHERE nhom_khoa IS NOT NULL AND yen_chuan IS NOT NULL AND trang_thai <> 'het'
      AND loai_nguon <> 'khach_ke' AND NOT bat_thuong
),
thanh_vien AS (      -- mã KOME của từng nhóm: nhóm ngầm định = đúng mã đó; nhóm có tên = nhom_so_sanh_ma
    SELECT DISTINCT nhom_khoa, substr(nhom_khoa, 4) AS product_code FROM h WHERE nhom_khoa LIKE 'ma:%'
    UNION
    SELECT 'n:' || nhom_id, product_code FROM app.nhom_so_sanh_ma
),
kome AS (
    SELECT tv.nhom_khoa, array_agg(tv.product_code ORDER BY tv.product_code) AS ma_kome,
           sum(g.doanh_thu) / nullif(sum(g.kg_ban), 0) AS gia_kome,
           mode() WITHIN GROUP (ORDER BY mart.ten_nganh(p.food_category_name, p.product_code, p.kind_code)) AS nganh
    FROM thanh_vien tv LEFT JOIN mart.gia_kome_kg g USING (product_code)
                       LEFT JOIN core.dim_product p USING (product_code)
    GROUP BY tv.nhom_khoa
)
SELECT h.nhom_khoa, max(h.ten_nhom) AS ten_nhom, h.don_vi_so, k.ma_kome,
       CASE WHEN h.don_vi_so = 'kg' THEN k.gia_kome END                                 AS gia_kome,
       count(DISTINCT h.ma_doi_thu)                                                     AS so_ben,
       count(*)                                                                         AS so_quan_sat,
       min(h.yen_chuan)                                                                 AS thap_nhat,
       (array_agg(h.ma_doi_thu ORDER BY h.yen_chuan))[1]                                AS ben_thap_nhat,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY h.yen_chuan)                         AS trung_vi,
       max(h.yen_chuan)                                                                 AS cao_nhat,
       CASE WHEN h.don_vi_so = 'kg' AND k.gia_kome IS NOT NULL
            THEN avg((h.yen_chuan < k.gia_kome)::int) END                               AS ty_le_re_hon_kome,
       k.nganh
FROM h LEFT JOIN kome k USING (nhom_khoa)
GROUP BY h.nhom_khoa, h.don_vi_so, k.ma_kome, k.gia_kome, k.nganh;

GRANT SELECT ON mart.so_sanh_nhom TO kome_app, kome_report, kome_ingest;
