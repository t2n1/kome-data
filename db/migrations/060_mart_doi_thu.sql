-- 060 — Chỉ số Thị trường & đối thủ (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4.4).
-- Mọi quy đổi / ghép / nhóm / bất thường viết ĐÚNG MỘT LẦN ở đây. kome/doi_thu.py chỉ hỏi.

-- Quy cách KOME: tách từ product_name "(500g x 20 packs)" / "(10kg/case)"; app.quy_cach_kome (người sửa) thắng.
CREATE VIEW mart.quy_cach_kome AS
WITH t AS (
    SELECT p.product_code,
           regexp_match(p.product_name, '\(\s*(\d+(?:[.,]\d+)?)\s*(kg|gr|g)\s*[x×]\s*(\d+)', 'i') AS m1,
           regexp_match(p.product_name, '(\d+(?:[.,]\d+)?)\s*kg\s*/\s*case', 'i')             AS m2
    FROM core.dim_product p
)
SELECT t.product_code,
       coalesce(o.kg_moi_goi, CASE WHEN t.m1 IS NOT NULL THEN replace(t.m1[1], ',', '.')::numeric
                                   / CASE WHEN lower(t.m1[2]) = 'kg' THEN 1 ELSE 1000 END END) AS kg_moi_goi,
       coalesce(o.goi_moi_thung, t.m1[3]::numeric)                                             AS goi_moi_thung,
       coalesce(o.kg_moi_thung, replace(t.m2[1], ',', '.')::numeric)                           AS kg_moi_thung,
       (o.product_code IS NOT NULL)                                                            AS da_sua
FROM t LEFT JOIN app.quy_cach_kome o USING (product_code);

-- Đơn giá thực 90 ngày của KOME quy về ¥/kg: TỶ SỐ CÁC TỔNG, đọc mart.ban_den_moc (quay về mốc, bỏ mã
-- nội bộ). pack_code '02' = thùng. Dòng mà quy cách không cho ra kg thì không vào tử lẫn mẫu (không đoán).
CREATE VIEW mart.gia_kome_kg AS
SELECT f.product_code,
       sum(f.amount - f.tax_amount)                                AS doanh_thu,
       sum(f.qty * k.kg)                                           AS kg_ban,
       sum(f.amount - f.tax_amount) / nullif(sum(f.qty * k.kg), 0) AS yen_kg
FROM mart.ban_den_moc f
CROSS JOIN mart.moc_thoi_gian m
JOIN mart.quy_cach_kome q ON q.product_code = f.product_code
CROSS JOIN LATERAL (SELECT CASE WHEN f.pack_code = '02' THEN coalesce(q.kg_moi_thung, q.kg_moi_goi * q.goi_moi_thung)
                                ELSE q.kg_moi_goi END AS kg) k
WHERE f.sales_date > m.hom_nay - 90 AND k.kg IS NOT NULL
GROUP BY f.product_code;

-- Bất thường: MỘT định nghĩa.
CREATE FUNCTION mart.la_gia_bat_thuong(gia numeric, trung_vi numeric, so_ben bigint) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
    SELECT coalesce(so_ben >= 3 AND trung_vi > 0 AND gia IS NOT NULL AND (gia > 2 * trung_vi OR gia < 0.5 * trung_vi), false)
$$;

CREATE VIEW mart.gia_doi_thu_quan_sat AS
WITH dc AS (
    SELECT DISTINCT ON (fact_id, truong) fact_id, truong, gia_tri_moi
    FROM app.dinh_chinh_gia ORDER BY fact_id, truong, id DESC
),
p AS (
    SELECT fact_id,
           max(gia_tri_moi) FILTER (WHERE truong = 'ten_goc')           AS ten_goc,
           max(gia_tri_moi) FILTER (WHERE truong = 'quy_cach_goc')      AS quy_cach_goc,
           max(gia_tri_moi) FILTER (WHERE truong = 'gia_goc')           AS gia_goc,
           max(gia_tri_moi) FILTER (WHERE truong = 'don_vi_gia')        AS don_vi_gia,
           max(gia_tri_moi) FILTER (WHERE truong = 'kg_moi_don_vi_gia') AS kg,
           max(gia_tri_moi) FILTER (WHERE truong = 'thue')              AS thue,
           max(gia_tri_moi) FILTER (WHERE truong = 'gom_ship')          AS gom_ship,
           max(gia_tri_moi) FILTER (WHERE truong = 'kenh_gia')          AS kenh_gia,
           max(gia_tri_moi) FILTER (WHERE truong = 'muc_gia')           AS muc_gia,
           max(gia_tri_moi) FILTER (WHERE truong = 'trang_thai')        AS trang_thai,
           bool_or(truong = 'xac_nhan')                                 AS xac_nhan,
           bool_or(truong <> 'xac_nhan')                                AS da_sua
    FROM dc GROUP BY fact_id
),
nap AS (
    SELECT 'nap'::text AS nguon, f.id, f.batch_id, f.ma_doi_thu, f.ma_hang_dt, f.ngay_nguon, f.hinh_thuc_nguon,
           f.nguon_file, f.vi_tri,
           coalesce(p.ten_goc, f.ten_goc) AS ten_goc, coalesce(p.quy_cach_goc, f.quy_cach_goc) AS quy_cach_goc,
           coalesce(nullif(p.gia_goc, '')::numeric, f.gia_goc) AS gia_goc,
           coalesce(p.don_vi_gia, f.don_vi_gia) AS don_vi_gia,
           coalesce(nullif(p.kg, '')::numeric, f.kg_moi_don_vi_gia) AS kg_moi_don_vi_gia,
           coalesce(p.thue, f.thue) AS thue, coalesce(p.gom_ship, f.gom_ship) AS gom_ship,
           coalesce(p.kenh_gia, f.kenh_gia) AS kenh_gia, coalesce(p.muc_gia, f.muc_gia) AS muc_gia,
           f.gia_bac, f.gia_truoc_km, coalesce(p.trang_thai, f.trang_thai) AS trang_thai, f.khuyen_mai,
           'bang_gia'::text AS loai_nguon, f.ghi_chu, f.ma_kome_de_xuat, f.nhan_de_xuat,
           CASE WHEN p.da_sua THEN 'da_sua' WHEN p.xac_nhan THEN 'da_xac_nhan'
                WHEN f.do_chac = 'can_xem' THEN 'can_xem' ELSE 'ai_doc' END AS trang_thai_duyet
    FROM core.fact_gia_doi_thu f LEFT JOIN p ON p.fact_id = f.id
),
tay AS (
    SELECT 'tay'::text, t.id, NULL::bigint, t.ma_doi_thu, t.ma_hang_dt, (t.luc AT TIME ZONE 'Asia/Tokyo')::date,
           'tay'::text, NULL::text, NULL::text, t.ten_goc, t.quy_cach_goc, t.gia_goc, t.don_vi_gia,
           t.kg_moi_don_vi_gia, t.thue, t.gom_ship, t.kenh_gia, t.muc_gia, NULL::text, NULL::numeric,
           t.trang_thai, NULL::text, t.loai_nguon, t.ghi_chu_nguon,
           NULL::text, NULL::text, 'nhap_tay'::text
    FROM app.gia_doi_thu_tay t
),
tat AS (SELECT * FROM nap UNION ALL SELECT * FROM tay),
ghep AS (
    SELECT a.*, g.ma_doi_thu IS NOT NULL AS co_ghep,
           CASE WHEN g.ma_doi_thu IS NULL THEN a.ma_kome_de_xuat
                WHEN g.nhan = 'khong' THEN NULL ELSE g.product_code END AS ma_kome,
           CASE WHEN g.ma_doi_thu IS NULL THEN a.nhan_de_xuat
                WHEN g.nhan = 'khong' THEN NULL ELSE g.nhan END         AS nhan,
           g.nhom_id AS nhom_ghep
    FROM tat a LEFT JOIN app.ghep_hang g USING (ma_doi_thu, ma_hang_dt)
    WHERE mart.moc_lui() IS NULL OR a.ngay_nguon <= mart.moc_lui()
)
SELECT x.nguon, x.id, x.batch_id, x.ma_doi_thu, d.ten AS ten_doi_thu, x.ma_hang_dt, x.ngay_nguon,
       x.hinh_thuc_nguon, x.nguon_file, x.vi_tri, x.ten_goc, x.quy_cach_goc, x.gia_goc, x.don_vi_gia,
       x.kg_moi_don_vi_gia, x.thue, x.gom_ship, x.kenh_gia, x.muc_gia, x.gia_bac, x.gia_truoc_km, x.trang_thai,
       x.khuyen_mai, x.loai_nguon, ln.thu_tu AS thu_tu_nguon, x.ghi_chu, x.ma_kome, x.nhan,
       CASE WHEN x.nhom_ghep IS NOT NULL THEN 'n:' || x.nhom_ghep
            WHEN nm.nhom_id IS NOT NULL THEN 'n:' || nm.nhom_id
            WHEN x.ma_kome IS NOT NULL THEN 'ma:' || x.ma_kome END                    AS nhom_khoa,
       coalesce(ng.ten, nn.ten, kp.product_name)                                      AS ten_nhom,
       x.trang_thai_duyet,
       x.gia_goc / coalesce(nullif(x.kg_moi_don_vi_gia, 0), 1)
                 / CASE WHEN x.thue = 'co' THEN 1.08 ELSE 1 END                        AS yen_chuan,
       CASE WHEN x.kg_moi_don_vi_gia > 0 THEN 'kg' ELSE 'don_vi:' || coalesce(x.don_vi_gia, '?') END AS don_vi_so,
       concat_ws(' · ', CASE x.thue WHEN 'co' THEN 'có thuế (đã quy về chưa thuế)' WHEN 'chua' THEN 'chưa thuế'
                                  ELSE 'thuế không rõ' END,
                        CASE x.gom_ship WHEN 'co' THEN 'gồm ship' WHEN 'khong' THEN 'chưa ship' ELSE 'ship không rõ' END,
                        x.kenh_gia, x.muc_gia)                                         AS nen_gia,
       row_number() OVER (PARTITION BY x.ma_doi_thu, x.ma_hang_dt, coalesce(x.kenh_gia, ''), coalesce(x.muc_gia, ''),
                                       (x.loai_nguon = 'khach_ke')
                          ORDER BY x.ngay_nguon DESC, ln.thu_tu, (x.nguon = 'tay') DESC, x.batch_id DESC NULLS FIRST, x.id DESC) = 1
                                                                                       AS hien_hanh,
       (SELECT hom_nay FROM mart.moc_thoi_gian) - x.ngay_nguon                         AS tuoi_ngay
FROM ghep x
LEFT JOIN app.doi_thu d ON d.ma = x.ma_doi_thu
LEFT JOIN app.loai_nguon ln ON ln.ma = x.loai_nguon
LEFT JOIN app.nhom_so_sanh_ma nm ON nm.product_code = x.ma_kome AND x.nhom_ghep IS NULL
LEFT JOIN app.nhom_so_sanh ng ON ng.id = x.nhom_ghep
LEFT JOIN app.nhom_so_sanh nn ON nn.id = nm.nhom_id
LEFT JOIN core.dim_product kp ON kp.product_code = x.ma_kome;

CREATE VIEW mart.gia_doi_thu_hien_hanh AS
WITH q AS MATERIALIZED (SELECT * FROM mart.gia_doi_thu_quan_sat WHERE hien_hanh),
tv AS (
    SELECT nhom_khoa, don_vi_so,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY yen_chuan) AS trung_vi,
           count(DISTINCT ma_doi_thu)                             AS so_ben
    FROM q
    WHERE nhom_khoa IS NOT NULL AND yen_chuan IS NOT NULL AND trang_thai <> 'het' AND loai_nguon <> 'khach_ke'
    GROUP BY 1, 2
)
SELECT q.*, tv.trung_vi AS trung_vi_nhom, tv.so_ben AS so_ben_nhom,
       q.trang_thai_duyet NOT IN ('da_xac_nhan', 'da_sua')
         AND mart.la_gia_bat_thuong(q.yen_chuan, tv.trung_vi::numeric, tv.so_ben) AS bat_thuong
FROM q LEFT JOIN tv USING (nhom_khoa, don_vi_so);

CREATE VIEW mart.so_sanh_nhom AS
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
           sum(g.doanh_thu) / nullif(sum(g.kg_ban), 0) AS gia_kome
    FROM thanh_vien tv LEFT JOIN mart.gia_kome_kg g USING (product_code)
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
            THEN avg((h.yen_chuan < k.gia_kome)::int) END                               AS ty_le_re_hon_kome
FROM h LEFT JOIN kome k USING (nhom_khoa)
GROUP BY h.nhom_khoa, h.don_vi_so, k.ma_kome, k.gia_kome;

GRANT SELECT ON mart.quy_cach_kome, mart.gia_kome_kg, mart.gia_doi_thu_quan_sat, mart.gia_doi_thu_hien_hanh,
                mart.so_sanh_nhom TO kome_app, kome_report, kome_ingest;
GRANT EXECUTE ON FUNCTION mart.la_gia_bat_thuong(numeric, numeric, bigint) TO kome_app, kome_report, kome_ingest;
