-- 067 — Quan sát đối thủ: quy cách gói + giá bậc có cấu trúc (đặc tả giao diện mới §5.1, §5.2); So sánh mang giá KOME
-- chuẩn (§5.3). Giá tại N thùng = bậc RẺ NHẤT có `tu` (quy ra thùng) ≤ N, không bậc nào áp → giá lẻ. 'kg' → thùng bằng
-- kg_thung_dt; 'goi' → thùng bằng so_goi_thung; thiếu quy cách → bậc đó KHÔNG áp (không đoán). Pallet CHỈ khi bảng ghi
-- rõ (bậc don_vi_sl 'pallet' hoặc dòng muc_gia 'pallet') — không "1 pallet = 40 thùng". Thống kê nhóm (trung vị, bất
-- thường, thấp / cao nhất) vẫn trên GIÁ LẺ (yen_chuan) — "Khách mua" chỉ đổi cái được vẽ.
-- quan_sat: CREATE OR REPLACE (cột cũ giữ thứ tự, cột mới ở CUỐI) — hien_hanh dùng q.* nên phải DROP + tạo lại cùng
-- so_sanh_nhom (không view nào khác phụ thuộc hai view đó — kiểm bằng pg_depend trước khi chạy).

CREATE FUNCTION mart.gia_bac_kg(p_bac jsonb, p_sl numeric, p_pallet boolean, p_kg_thung numeric, p_so_goi integer,
                                p_kl_goi numeric, p_thue text) RETURNS numeric LANGUAGE sql IMMUTABLE AS $$
    SELECT min(b.gia_kg)
    FROM (
        SELECT CASE e->>'don_vi_gia' WHEN 'kg'    THEN (e->>'gia')::numeric
                                     WHEN 'thung' THEN (e->>'gia')::numeric / nullif(p_kg_thung, 0)
                                     WHEN 'goi'   THEN (e->>'gia')::numeric / nullif(p_kl_goi / 1000, 0) END
               / CASE WHEN p_thue = 'co' THEN 1.08 ELSE 1 END                                        AS gia_kg,
               CASE e->>'don_vi_sl' WHEN 'thung' THEN (e->>'tu')::numeric
                                    WHEN 'kg'    THEN (e->>'tu')::numeric / nullif(p_kg_thung, 0)
                                    WHEN 'goi'   THEN (e->>'tu')::numeric / nullif(p_so_goi, 0) END  AS tu_thung,
               e->>'don_vi_sl' = 'pallet'                                                            AS la_pallet
        FROM jsonb_array_elements(coalesce(p_bac, '[]'::jsonb)) e
    ) b
    WHERE CASE WHEN p_pallet THEN b.la_pallet OR b.tu_thung IS NOT NULL
               ELSE NOT b.la_pallet AND b.tu_thung <= p_sl END
$$;

-- Thân = 063 (chép nguyên), đổi: đính chính so_goi_thung / kl_goi_g / bac / khuyen_mai / gia_truoc_km áp lên bản nạp
-- ('' = đã xoá khuyến mãi / giá trước KM, '[]' = đã xoá bậc); giá tay mang khuyen_mai / gia_truoc_km / quy cách / bậc;
-- SELECT cuối thành CTE r; thêm ở CUỐI kg_thung_dt, giá gói / thùng, giá tại 1 / 5 / 10 thùng và pallet.
CREATE OR REPLACE VIEW mart.gia_doi_thu_quan_sat AS
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
           max(gia_tri_moi) FILTER (WHERE truong = 'so_goi_thung')      AS so_goi_thung,
           max(gia_tri_moi) FILTER (WHERE truong = 'kl_goi_g')          AS kl_goi_g,
           max(gia_tri_moi) FILTER (WHERE truong = 'bac')               AS bac,
           max(gia_tri_moi) FILTER (WHERE truong = 'khuyen_mai')        AS khuyen_mai,
           max(gia_tri_moi) FILTER (WHERE truong = 'gia_truoc_km')      AS gia_truoc_km,
           bool_or(truong = 'xac_nhan')                                 AS xac_nhan,
           bool_or(truong <> 'xac_nhan')                                AS da_sua
    FROM dc GROUP BY fact_id
),
nap AS (
    SELECT 'nap'::text AS nguon, f.id, f.batch_id, f.ma_doi_thu, f.ma_hang_dt, f.ngay_nguon, f.hinh_thuc_nguon,
           f.nguon_file, f.vi_tri,
           coalesce(p.ten_goc, f.ten_goc) AS ten_goc, coalesce(p.quy_cach_goc, f.quy_cach_goc) AS quy_cach_goc,
           coalesce(CASE WHEN p.gia_goc ~ '^\s*\d+(\.\d+)?\s*$' THEN p.gia_goc::numeric END, f.gia_goc) AS gia_goc,
           coalesce(p.don_vi_gia, f.don_vi_gia) AS don_vi_gia,
           coalesce(CASE WHEN p.kg ~ '^\s*\d+(\.\d+)?\s*$' THEN p.kg::numeric END, f.kg_moi_don_vi_gia) AS kg_moi_don_vi_gia,
           coalesce(p.thue, f.thue) AS thue, coalesce(p.gom_ship, f.gom_ship) AS gom_ship,
           coalesce(p.kenh_gia, f.kenh_gia) AS kenh_gia, coalesce(p.muc_gia, f.muc_gia) AS muc_gia,
           f.gia_bac,
           CASE WHEN p.gia_truoc_km IS NULL THEN f.gia_truoc_km
                WHEN p.gia_truoc_km ~ '^\s*\d+(\.\d+)?\s*$' THEN p.gia_truoc_km::numeric END AS gia_truoc_km,
           coalesce(p.trang_thai, f.trang_thai) AS trang_thai,
           CASE WHEN p.khuyen_mai IS NULL THEN f.khuyen_mai ELSE nullif(p.khuyen_mai, '') END AS khuyen_mai,
           'bang_gia'::text AS loai_nguon, f.ghi_chu, f.ma_kome_de_xuat, f.nhan_de_xuat,
           CASE WHEN p.da_sua THEN 'da_sua' WHEN p.xac_nhan THEN 'da_xac_nhan'
                WHEN f.do_chac = 'can_xem' THEN 'can_xem' ELSE 'ai_doc' END AS trang_thai_duyet,
           NULL::text AS nhom_ke,
           coalesce(CASE WHEN p.so_goi_thung ~ '^\s*\d+\s*$' THEN p.so_goi_thung::int END, f.so_goi_thung) AS so_goi_thung,
           coalesce(CASE WHEN p.kl_goi_g ~ '^\s*\d+(\.\d+)?\s*$' THEN p.kl_goi_g::numeric END, f.kl_goi_g) AS kl_goi_g,
           CASE WHEN p.bac IS NULL THEN f.bac ELSE p.bac::jsonb END AS bac
    FROM core.fact_gia_doi_thu f LEFT JOIN p ON p.fact_id = f.id
),
tay AS (
    -- Giá khách kể: khoá chuỗi (ma_hang_dt) dựng LÚC ĐỌC từ nhóm HIỆN HÀNH — 'ke:<khách>:<nhom_cua_khoa(khoá đã ghi)>'
    -- — để "tin mới nhất của (khách, bên, nhóm) là hiện trạng" đúng cả khi cùng hàng được gắn lúc 'ma:<mã>', lúc
    -- 'n:<nhóm>' (hay mã được thêm vào nhóm sau). Cột lưu app.gia_doi_thu_tay.ma_hang_dt giữ nguyên (sổ chỉ thêm).
    SELECT 'tay'::text, t.id, NULL::bigint, t.ma_doi_thu,
           CASE WHEN t.loai_nguon = 'khach_ke' AND t.nhom_khoa IS NOT NULL AND t.customer_code IS NOT NULL
                THEN 'ke:' || t.customer_code || ':' || mart.nhom_cua_khoa(t.nhom_khoa)
                ELSE t.ma_hang_dt END,
           (t.luc AT TIME ZONE 'Asia/Tokyo')::date,
           'tay'::text, NULL::text, NULL::text, t.ten_goc, t.quy_cach_goc, t.gia_goc, t.don_vi_gia,
           t.kg_moi_don_vi_gia, t.thue, t.gom_ship, t.kenh_gia, t.muc_gia, NULL::text, t.gia_truoc_km,
           t.trang_thai, t.khuyen_mai, t.loai_nguon, t.ghi_chu_nguon,
           NULL::text, NULL::text, 'nhap_tay'::text, mart.nhom_cua_khoa(t.nhom_khoa),
           t.so_goi_thung, t.kl_goi_g, t.bac
    FROM app.gia_doi_thu_tay t
),
tat AS (SELECT * FROM nap UNION ALL SELECT * FROM tay),
ghep AS (
    SELECT a.*, g.ma_doi_thu IS NOT NULL AS co_ghep,
           CASE WHEN g.ma_doi_thu IS NULL THEN a.ma_kome_de_xuat
                WHEN g.nhan = 'khong' THEN NULL ELSE g.product_code END AS ma_kome,
           CASE WHEN g.ma_doi_thu IS NULL THEN a.nhan_de_xuat
                WHEN g.nhan = 'khong' THEN NULL ELSE g.nhan END         AS nhan,
           CASE WHEN g.nhan = 'khong' THEN NULL ELSE g.nhom_id END AS nhom_ghep
    FROM tat a LEFT JOIN app.ghep_hang g USING (ma_doi_thu, ma_hang_dt)
    WHERE a.ngay_nguon <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date))
),
r AS (
SELECT x.nguon, x.id, x.batch_id, x.ma_doi_thu, d.ten AS ten_doi_thu, x.ma_hang_dt, x.ngay_nguon,
       x.hinh_thuc_nguon, x.nguon_file, x.vi_tri, x.ten_goc, x.quy_cach_goc, x.gia_goc, x.don_vi_gia,
       x.kg_moi_don_vi_gia, x.thue, x.gom_ship, x.kenh_gia, x.muc_gia, x.gia_bac, x.gia_truoc_km, x.trang_thai,
       x.khuyen_mai, x.loai_nguon, ln.thu_tu AS thu_tu_nguon, x.ghi_chu, x.ma_kome, x.nhan,
       coalesce(x.nhom_ke,
                CASE WHEN x.nhom_ghep IS NOT NULL THEN 'n:' || x.nhom_ghep
                     WHEN nm.nhom_id IS NOT NULL THEN 'n:' || nm.nhom_id
                     WHEN x.ma_kome IS NOT NULL THEN 'ma:' || x.ma_kome END)          AS nhom_khoa,
       CASE WHEN x.nhom_ke IS NOT NULL THEN coalesce(nk.ten, kk.product_name)
            ELSE coalesce(ng.ten, nn.ten, kp.product_name) END                        AS ten_nhom,
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
       (SELECT hom_nay FROM mart.moc_thoi_gian) - x.ngay_nguon                         AS tuoi_ngay,
       x.so_goi_thung, x.kl_goi_g, x.bac
FROM ghep x
LEFT JOIN app.doi_thu d ON d.ma = x.ma_doi_thu
LEFT JOIN app.loai_nguon ln ON ln.ma = x.loai_nguon
LEFT JOIN app.nhom_so_sanh_ma nm ON nm.product_code = x.ma_kome AND x.nhom_ghep IS NULL
LEFT JOIN app.nhom_so_sanh ng ON ng.id = x.nhom_ghep
LEFT JOIN app.nhom_so_sanh nn ON nn.id = nm.nhom_id
LEFT JOIN core.dim_product kp ON kp.product_code = x.ma_kome
LEFT JOIN app.nhom_so_sanh nk ON nk.id = CASE WHEN x.nhom_ke ~ '^n:[0-9]+$' THEN substr(x.nhom_ke, 3)::bigint END
LEFT JOIN core.dim_product kk ON kk.product_code = CASE WHEN x.nhom_ke LIKE 'ma:%' THEN substr(x.nhom_ke, 4) END
),
k AS (
    SELECT r.*,
           CASE WHEN r.don_vi_gia IN ('thung', 'cs', 'case', 'ctn') AND r.kg_moi_don_vi_gia > 0 THEN r.kg_moi_don_vi_gia
                WHEN r.so_goi_thung > 0 AND r.kl_goi_g > 0 THEN r.so_goi_thung * r.kl_goi_g / 1000 END AS kg_thung_dt
    FROM r
)
SELECT k.*,
       CASE WHEN k.don_vi_so = 'kg' AND k.kl_goi_g > 0 THEN k.yen_chuan * k.kl_goi_g / 1000 END      AS gia_goi,
       CASE WHEN k.don_vi_so = 'kg' AND k.kg_thung_dt > 0 THEN k.yen_chuan * k.kg_thung_dt END       AS gia_thung,
       CASE WHEN k.don_vi_so = 'kg'
            THEN least(k.yen_chuan, mart.gia_bac_kg(k.bac, 1, false, k.kg_thung_dt, k.so_goi_thung, k.kl_goi_g, k.thue))
            ELSE k.yen_chuan END                                                                     AS gia_1,
       CASE WHEN k.don_vi_so = 'kg'
            THEN least(k.yen_chuan, mart.gia_bac_kg(k.bac, 5, false, k.kg_thung_dt, k.so_goi_thung, k.kl_goi_g, k.thue))
            ELSE k.yen_chuan END                                                                     AS gia_5,
       CASE WHEN k.don_vi_so = 'kg'
            THEN least(k.yen_chuan, mart.gia_bac_kg(k.bac, 10, false, k.kg_thung_dt, k.so_goi_thung, k.kl_goi_g, k.thue))
            ELSE k.yen_chuan END                                                                     AS gia_10,
       CASE WHEN k.don_vi_so <> 'kg' THEN NULL
            WHEN k.muc_gia = 'pallet' THEN k.yen_chuan
            WHEN EXISTS (SELECT 1 FROM jsonb_array_elements(coalesce(k.bac, '[]'::jsonb)) e WHERE e->>'don_vi_sl' = 'pallet')
            THEN least(k.yen_chuan, mart.gia_bac_kg(k.bac, NULL, true, k.kg_thung_dt, k.so_goi_thung, k.kl_goi_g, k.thue))
       END                                                                                           AS gia_pallet
FROM k;

DROP VIEW mart.so_sanh_nhom;
DROP VIEW mart.gia_doi_thu_hien_hanh;

-- Thân = 060.
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

-- Thân = 062, thêm giá KOME chuẩn / bảng / khuyến mãi (066). "Vị trí" (ty_le_re_hon_kome) so với 標準価格, không có thì
-- thực bán 90 ngày. Nhóm nhiều mã: chuẩn = trung bình có trọng số kg đã bán 90 ngày (tỷ số các tổng), không mã nào
-- bán thì trung bình thường; bảng / khuyến mãi lấy của mã bán nhiều kg nhất trong nhóm.
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
tv_gia AS (
    SELECT tv.nhom_khoa, tv.product_code, g.doanh_thu, g.kg_ban, mart.gia_kome_chuan(tv.product_code) AS chuan
    FROM thanh_vien tv LEFT JOIN mart.gia_kome_kg g USING (product_code)
),
chinh AS (      -- mã "chính" của nhóm: bán nhiều kg nhất (không ai bán → mã nhỏ nhất)
    SELECT DISTINCT ON (nhom_khoa) nhom_khoa, product_code FROM tv_gia
    ORDER BY nhom_khoa, kg_ban DESC NULLS LAST, product_code
),
kome AS (
    SELECT t.nhom_khoa, array_agg(t.product_code ORDER BY t.product_code) AS ma_kome,
           sum(t.doanh_thu) / nullif(sum(t.kg_ban), 0) AS gia_kome,
           coalesce(sum(t.chuan * t.kg_ban) FILTER (WHERE t.chuan IS NOT NULL)
                      / nullif(sum(t.kg_ban) FILTER (WHERE t.chuan IS NOT NULL), 0),
                    avg(t.chuan)) AS gia_kome_chuan,
           mode() WITHIN GROUP (ORDER BY mart.ten_nganh(p.food_category_name, p.product_code, p.kind_code)) AS nganh
    FROM tv_gia t LEFT JOIN core.dim_product p USING (product_code)
    GROUP BY t.nhom_khoa
),
bang AS (
    SELECT c.nhom_khoa,
           jsonb_object_agg(b.price_level, round(b.yen_kg, 1))
             FILTER (WHERE b.price_level <> 'std' AND NOT mart.la_gia_km_kome(b.price_level))             AS gia_kome_bang,
           min(b.yen_kg) FILTER (WHERE mart.la_gia_km_kome(b.price_level))                                   AS km
    FROM chinh c JOIN mart.gia_kome_bang b USING (product_code)
    GROUP BY c.nhom_khoa
)
SELECT h.nhom_khoa, max(h.ten_nhom) AS ten_nhom, h.don_vi_so, k.ma_kome,
       CASE WHEN h.don_vi_so = 'kg' THEN k.gia_kome END                                 AS gia_kome,
       count(DISTINCT h.ma_doi_thu)                                                     AS so_ben,
       count(*)                                                                         AS so_quan_sat,
       min(h.yen_chuan)                                                                 AS thap_nhat,
       (array_agg(h.ma_doi_thu ORDER BY h.yen_chuan))[1]                                AS ben_thap_nhat,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY h.yen_chuan)                         AS trung_vi,
       max(h.yen_chuan)                                                                 AS cao_nhat,
       CASE WHEN h.don_vi_so = 'kg' AND coalesce(k.gia_kome_chuan, k.gia_kome) IS NOT NULL
            THEN avg((h.yen_chuan < coalesce(k.gia_kome_chuan, k.gia_kome))::int) END   AS ty_le_re_hon_kome,
       k.nganh,
       CASE WHEN h.don_vi_so = 'kg' THEN k.gia_kome_chuan END                           AS gia_kome_chuan,
       CASE WHEN h.don_vi_so = 'kg' THEN b.gia_kome_bang END                            AS gia_kome_bang,
       CASE WHEN h.don_vi_so = 'kg' AND b.km < coalesce(k.gia_kome_chuan, 'infinity') THEN b.km END AS gia_kome_km
FROM h LEFT JOIN kome k USING (nhom_khoa) LEFT JOIN bang b USING (nhom_khoa)
GROUP BY h.nhom_khoa, h.don_vi_so, k.ma_kome, k.gia_kome, k.nganh, k.gia_kome_chuan, b.gia_kome_bang, b.km;

GRANT SELECT ON mart.gia_doi_thu_quan_sat, mart.gia_doi_thu_hien_hanh, mart.so_sanh_nhom TO kome_app, kome_report, kome_ingest;
GRANT EXECUTE ON FUNCTION mart.gia_bac_kg(jsonb, numeric, boolean, numeric, integer, numeric, text) TO kome_app, kome_report, kome_ingest;
