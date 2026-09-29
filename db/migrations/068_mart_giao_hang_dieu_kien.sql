-- 068 — Điều kiện giao hàng / điều kiện bán HIỆN HÀNH (đặc tả giao diện mới §5.4).
-- Giao hàng của một bên = lô nạp mới nhất của bên đó (meta.ingest_batch chưa hoàn tác, data_date rồi batch_id), mỗi
-- trường: đính chính của sale thắng NẾU ghi SAU lúc nạp lô đó (loaded_at) — "mới nhất thắng" giữa người đọc và người sửa;
-- bên chưa có lô nào mà sale đã điền → vẫn có dòng. '' = xoá về "không ghi" (NULL). KOME: app.giao_hang_kome
-- (`suy` = chưa ai xác nhận số suy từ phiếu bán). Điều kiện bán: lô mới nhất của bên, bỏ loại 'ghi_chu_doc', áp sửa / bỏ
-- mới nhất theo fact_id, cộng dòng sale thêm tay (fact_id NULL, không bị bỏ).

CREATE VIEW mart.giao_hang_hien_hanh AS
WITH lo AS (
    SELECT DISTINCT ON (f.ma_doi_thu) f.*, b.loaded_at
    FROM core.fact_giao_hang_doi_thu f JOIN meta.ingest_batch b USING (batch_id)
    WHERE b.undone_at IS NULL
    ORDER BY f.ma_doi_thu, b.data_date DESC, f.batch_id DESC, f.id DESC
),
dc AS (
    SELECT DISTINCT ON (ma_doi_thu, truong) ma_doi_thu, truong, gia_tri_moi, luc
    FROM app.dinh_chinh_giao_hang ORDER BY ma_doi_thu, truong, id DESC
),
ben AS (SELECT ma_doi_thu FROM lo UNION SELECT ma_doi_thu FROM dc),
v AS (
    SELECT b.ma_doi_thu, l.ngay_nguon, l.nguon_chu, l.loaded_at,
           l.bao_ship, l.phi_ship, l.phi_ship_theo, l.mien_ship_tu, l.mien_ship_kien, l.thung_moi_kien, l.phu_phi,
           l.phi_daibiki, l.daibiki_tu, l.daibiki_sau, l.ck_mien_daibiki, l.kien_toi_da_kg, l.ghep_kien, l.thue, l.cach_gui
    FROM ben b LEFT JOIN lo l USING (ma_doi_thu)
)
SELECT v.ma_doi_thu, d.ten,
       CASE WHEN x.bao_ship IS NULL THEN v.bao_ship ELSE nullif(x.bao_ship, '')::boolean END                      AS bao_ship,
       CASE WHEN x.phi_ship IS NULL THEN v.phi_ship ELSE nullif(x.phi_ship, '')::numeric END                      AS phi_ship,
       CASE WHEN x.phi_ship_theo IS NULL THEN v.phi_ship_theo ELSE nullif(x.phi_ship_theo, '') END                AS phi_ship_theo,
       CASE WHEN x.mien_ship_tu IS NULL THEN v.mien_ship_tu ELSE nullif(x.mien_ship_tu, '')::numeric END          AS mien_ship_tu,
       CASE WHEN x.mien_ship_kien IS NULL THEN v.mien_ship_kien ELSE nullif(x.mien_ship_kien, '')::int END        AS mien_ship_kien,
       CASE WHEN x.thung_moi_kien IS NULL THEN v.thung_moi_kien ELSE nullif(x.thung_moi_kien, '')::int END        AS thung_moi_kien,
       CASE WHEN x.phu_phi IS NULL THEN v.phu_phi ELSE nullif(x.phu_phi, '')::jsonb END                           AS phu_phi,
       CASE WHEN x.phi_daibiki IS NULL THEN v.phi_daibiki ELSE nullif(x.phi_daibiki, '')::numeric END             AS phi_daibiki,
       CASE WHEN x.daibiki_tu IS NULL THEN v.daibiki_tu ELSE nullif(x.daibiki_tu, '')::numeric END                AS daibiki_tu,
       CASE WHEN x.daibiki_sau IS NULL THEN v.daibiki_sau ELSE nullif(x.daibiki_sau, '')::numeric END             AS daibiki_sau,
       CASE WHEN x.ck_mien_daibiki IS NULL THEN v.ck_mien_daibiki ELSE nullif(x.ck_mien_daibiki, '')::boolean END AS ck_mien_daibiki,
       CASE WHEN x.kien_toi_da_kg IS NULL THEN v.kien_toi_da_kg ELSE nullif(x.kien_toi_da_kg, '')::numeric END    AS kien_toi_da_kg,
       CASE WHEN x.ghep_kien IS NULL THEN v.ghep_kien ELSE nullif(x.ghep_kien, '') END                            AS ghep_kien,
       CASE WHEN x.thue IS NULL THEN v.thue ELSE nullif(x.thue, '') END                                           AS thue,
       CASE WHEN x.cach_gui IS NULL THEN v.cach_gui ELSE nullif(x.cach_gui, '') END                               AS cach_gui,
       v.nguon_chu, v.ngay_nguon, false AS suy, false AS da_xac_nhan, 1 AS thu_tu
FROM v
LEFT JOIN app.doi_thu d ON d.ma = v.ma_doi_thu
CROSS JOIN LATERAL (
    SELECT max(gia_tri_moi) FILTER (WHERE truong = 'bao_ship')        AS bao_ship,
           max(gia_tri_moi) FILTER (WHERE truong = 'phi_ship')        AS phi_ship,
           max(gia_tri_moi) FILTER (WHERE truong = 'phi_ship_theo')   AS phi_ship_theo,
           max(gia_tri_moi) FILTER (WHERE truong = 'mien_ship_tu')    AS mien_ship_tu,
           max(gia_tri_moi) FILTER (WHERE truong = 'mien_ship_kien')  AS mien_ship_kien,
           max(gia_tri_moi) FILTER (WHERE truong = 'thung_moi_kien')  AS thung_moi_kien,
           max(gia_tri_moi) FILTER (WHERE truong = 'phu_phi')         AS phu_phi,
           max(gia_tri_moi) FILTER (WHERE truong = 'phi_daibiki')     AS phi_daibiki,
           max(gia_tri_moi) FILTER (WHERE truong = 'daibiki_tu')      AS daibiki_tu,
           max(gia_tri_moi) FILTER (WHERE truong = 'daibiki_sau')     AS daibiki_sau,
           max(gia_tri_moi) FILTER (WHERE truong = 'ck_mien_daibiki') AS ck_mien_daibiki,
           max(gia_tri_moi) FILTER (WHERE truong = 'kien_toi_da_kg')  AS kien_toi_da_kg,
           max(gia_tri_moi) FILTER (WHERE truong = 'ghep_kien')       AS ghep_kien,
           max(gia_tri_moi) FILTER (WHERE truong = 'thue')            AS thue,
           max(gia_tri_moi) FILTER (WHERE truong = 'cach_gui')        AS cach_gui
    FROM dc WHERE dc.ma_doi_thu = v.ma_doi_thu AND (v.loaded_at IS NULL OR dc.luc > v.loaded_at)
) x
UNION ALL
SELECT 'KOME', 'KOME', k.bao_ship, k.phi_ship, k.phi_ship_theo, k.mien_ship_tu, k.mien_ship_kien, k.thung_moi_kien,
       k.phu_phi, k.phi_daibiki, k.daibiki_tu, k.daibiki_sau, k.ck_mien_daibiki, k.kien_toi_da_kg, k.ghep_kien, k.thue,
       k.cach_gui, NULL, (k.sua_luc AT TIME ZONE 'Asia/Tokyo')::date, NOT k.da_xac_nhan, k.da_xac_nhan, 0
FROM app.giao_hang_kome k
ORDER BY thu_tu, ma_doi_thu;

-- Bằng chứng cho dòng KOME (đặc tả §5.4): đếm trên phiếu 180 ngày tới mốc. Mã phí nhận theo TÊN OBC (配送料… / 代引手数料…).
CREATE VIEW mart.giao_hang_kome_bang_chung AS
WITH don AS (
    SELECT f.slip_no,
           sum(f.amount) FILTER (WHERE NOT mart.la_phi_dieu_chinh(f.product_code, p.kind_code))  AS tien_hang,
           bool_or(p.product_name LIKE '配送料%')                                                  AS co_ship,
           bool_or(p.product_name LIKE '代引手数料330%')                                           AS dai_330,
           bool_or(p.product_name LIKE '代引手数料300%')                                           AS dai_300
    FROM mart.ban_den_moc f CROSS JOIN mart.moc_thoi_gian m
    LEFT JOIN core.dim_product p ON p.product_code = f.product_code
    WHERE f.sales_date > m.hom_nay - 180
    GROUP BY f.slip_no
)
SELECT count(*) FILTER (WHERE co_ship) AS so_don_ship, max(tien_hang) FILTER (WHERE co_ship) AS don_ship_lon_nhat,
       count(*) FILTER (WHERE dai_330) AS so_don_dai_330, count(*) FILTER (WHERE dai_300) AS so_don_dai_300
FROM don;

CREATE VIEW mart.dieu_kien_hien_hanh AS
WITH lo AS (
    SELECT DISTINCT ON (f.ma_doi_thu) f.ma_doi_thu, f.batch_id
    FROM core.fact_dieu_kien_doi_thu f JOIN meta.ingest_batch b USING (batch_id)
    WHERE b.undone_at IS NULL
    ORDER BY f.ma_doi_thu, b.data_date DESC, f.batch_id DESC
),
sua AS (
    SELECT DISTINCT ON (fact_id) fact_id, loai, noi_dung, bo FROM app.dinh_chinh_dieu_kien
    WHERE fact_id IS NOT NULL ORDER BY fact_id, id DESC
)
SELECT f.id, f.id AS fact_id, f.ma_doi_thu, coalesce(s.loai, f.loai) AS loai, coalesce(s.noi_dung, f.noi_dung) AS noi_dung,
       f.ngay_nguon, false AS them_tay
FROM core.fact_dieu_kien_doi_thu f JOIN lo USING (ma_doi_thu, batch_id)
LEFT JOIN sua s ON s.fact_id = f.id
WHERE f.loai <> 'ghi_chu_doc' AND NOT coalesce(s.bo, false)
UNION ALL
SELECT -t.id, NULL, t.ma_doi_thu, t.loai, t.noi_dung, (t.luc AT TIME ZONE 'Asia/Tokyo')::date, true
FROM app.dinh_chinh_dieu_kien t
WHERE t.fact_id IS NULL AND NOT t.bo
  AND NOT EXISTS (SELECT 1 FROM app.dinh_chinh_dieu_kien b
                  WHERE b.fact_id IS NULL AND b.bo AND b.id > t.id
                    AND (b.ma_doi_thu, b.loai, b.noi_dung) = (t.ma_doi_thu, t.loai, t.noi_dung));

GRANT SELECT ON mart.giao_hang_hien_hanh, mart.giao_hang_kome_bang_chung, mart.dieu_kien_hien_hanh
    TO kome_app, kome_report, kome_ingest;
