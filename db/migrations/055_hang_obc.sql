-- 055 — Hạng khách lấy từ OBC (得意先ランク), và khách Z / ZZ / ZZZ không vào danh sách gọi.
--
-- Chủ DN chốt 2026-09-28 (đặc tả docs/superpowers/specs/2026-09-28-hang-obc-design.md):
--   * Hạng trên web = 得意先ランク trong file 得意先全情報, KHÔNG tự tính. Hạng tự tính theo
--     doanh thu 12 tháng (cume_dist, 020) bị bỏ — hai hạng cùng tên là hai con số nói hai điều,
--     và người ta đối chiếu với OBC (khách 000000000179: OBC ZZZ, web từng ghi B).
--   * Khách mang hạng OBC Z (長期不在) / ZZ (連絡先不明) / ZZZ (電話禁止又は不要) không vào bất kỳ
--     danh sách gọi nào — cùng cổng với khách ※廃業※ (016), nhưng KHÔNG đổi trang_thai của họ
--     thành 'ngung_giao_dich': 583/604 khách ZZZ vẫn đang mua (đo thật 2026-09-28).
--
-- Hạng là bản HIỆN HÀNH của core.dim_customer (is_current), không quay về theo mốc — OBC không
-- cho biết hạng ngày cũ; cùng nếp tên khách / người phụ trách (bất biến 040).


-- Nhãn ngắn của 得意先ランク. ĐỊNH NGHĨA DUY NHẤT — mọi chỗ hiện / lọc / xét hạng đọc hàm này.
-- Theo MÃ (rank_code), không theo chữ của rank_name (tên có khoảng trắng toàn góc, dễ đổi). Mã
-- lạ (OBC thêm hạng mới) -> nguyên văn rank_name: hiện đúng điều OBC ghi, không đoán.
CREATE FUNCTION mart.hang_obc(p_rank_code text, p_rank_name text)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_rank_code
             WHEN '0001' THEN 'S'
             WHEN '0002' THEN 'A'
             WHEN '0003' THEN 'B'
             WHEN '0004' THEN 'C'
             WHEN '0005' THEN 'D'
             WHEN '0006' THEN 'Z'
             WHEN '0007' THEN 'ZZ'
             WHEN '0008' THEN 'ZZZ'
             WHEN '0011' THEN 'キャンペーン不要'
             WHEN '0999' THEN '対象外'
             ELSE nullif(btrim(coalesce(p_rank_name, '')), '')
           END
$$;

COMMENT ON FUNCTION mart.hang_obc(text, text) IS
  'Nhãn ngắn của 得意先ランク (OBC). Định nghĩa DUY NHẤT của "hạng khách" từ 055 — không phải
   hạng theo doanh thu (đã bỏ). kome.khach_hang.THU_TU_HANG là bản chép bắt buộc của các nhãn.';

-- Hạng nào nghĩa là "đừng gọi". Viết trên NHÃN của hang_obc để ánh xạ mã chỉ ở một chỗ.
CREATE FUNCTION mart.la_hang_khong_goi(p_hang text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
    SELECT coalesce(p_hang IN ('Z', 'ZZ', 'ZZZ'), false)
$$;


-- dau_hieu_khach (016): thêm ba cột ở CUỐI. `khong_goi` là cổng DUY NHẤT của mọi danh sách gọi:
-- ※廃業※ … (da_ngung) HOẶC hạng OBC Z/ZZ/ZZZ. `da_ngung` giữ nguyên nghĩa (đóng cửa thật) —
-- nó vẫn quyết định trang_thai 'ngung_giao_dich'.
CREATE OR REPLACE VIEW mart.dau_hieu_khach AS
SELECT customer_code,
       customer_name,
       (regexp_match(customer_name, '※([^※]{1,20})※'))[1] AS dau_hieu_obc,
       (customer_name ~ '※[^※]*(廃業|清算|精算|取引停止|取引禁止|取引永久|使用禁止)[^※]*※')
           AS da_ngung,
       mart.hang_obc(rank_code, rank_name)                   AS hang_obc,
       nullif(rank_name, '')                                 AS hang_obc_ten,
       coalesce(customer_name ~ '※[^※]*(廃業|清算|精算|取引停止|取引禁止|取引永久|使用禁止)[^※]*※', false)
       OR mart.la_hang_khong_goi(mart.hang_obc(rank_code, rank_name)) AS khong_goi
FROM core.dim_customer
WHERE is_current;

COMMENT ON COLUMN mart.dau_hieu_khach.khong_goi IS
  'Cổng DUY NHẤT của mọi danh sách gọi (055): da_ngung (※廃業※…) HOẶC hạng OBC Z/ZZ/ZZZ.
   Không đổi trang_thai của khách — chỉ loại khỏi danh sách gọi.';


-- khach_360 (016): thêm ba cột ở CUỐI, đọc từ dau_hieu_khach đã JOIN sẵn (không thêm JOIN).
CREATE OR REPLACE VIEW mart.khach_360 AS
SELECT
    k.customer_code,
    coalesce(nullif(d.customer_name, ''), '(chưa có tên)') AS ten,
    d.branch_name, d.phone, d.postcode, d.prefecture, d.city, d.address,
    d.salesperson_code, d.rank_code, d.category_code, d.closing_day_code,
    d.price_level_code, d.spot_flag,

    k.lan_dau, k.lan_cuoi, k.so_lan_mua, k.so_phieu,
    k.doanh_thu_thuan, k.lai_gop,
    k.lai_gop::numeric / nullif(k.doanh_thu_thuan, 0)          AS ty_suat,
    k.doanh_thu_thuan / k.so_lan_mua                            AS gia_tri_tb_moi_lan,
    (m.hom_nay - k.lan_cuoi)                                    AS so_ngay_im_lang,
    n.nhip_ngay,
    n.so_khoang,
    CASE WHEN n.nhip_ngay > 0
         THEN (m.hom_nay - k.lan_cuoi)::numeric / n.nhip_ngay END AS ty_le_im_lang,

    CASE
      WHEN coalesce(h.da_ngung, false) THEN 'ngung_giao_dich'
      WHEN n.nhip_ngay IS NULL OR n.so_khoang < 2 THEN 'chua_du_lich_su'
      WHEN (m.hom_nay - k.lan_cuoi)::numeric / n.nhip_ngay >= 4 THEN 'da_roi_bo'
      WHEN (m.hom_nay - k.lan_cuoi)::numeric / n.nhip_ngay >= 2 THEN 'canh_bao'
      ELSE 'binh_thuong'
    END AS trang_thai,

    h.dau_hieu_obc,
    coalesce(h.da_ngung, false) AS da_ngung,
    h.hang_obc,
    h.hang_obc_ten,
    coalesce(h.khong_goi, false) AS khong_goi
FROM (
    SELECT customer_code,
           min(sales_date) AS lan_dau, max(sales_date) AS lan_cuoi,
           count(DISTINCT sales_date) AS so_lan_mua,
           count(*) AS so_phieu,
           sum(doanh_thu_thuan) AS doanh_thu_thuan,
           sum(lai_gop) AS lai_gop
    FROM mart.lan_mua GROUP BY customer_code
) k
LEFT JOIN core.dim_customer d
       ON d.customer_code = k.customer_code AND d.is_current
LEFT JOIN mart.nhip_mua n ON n.customer_code = k.customer_code
LEFT JOIN mart.dau_hieu_khach h ON h.customer_code = k.customer_code
CROSS JOIN mart.moc_thoi_gian m;


-- Doanh thu 12 tháng của từng khách — phần CÒN DÙNG của hang_doanh_thu (020), đúng công thức cũ.
-- Bản đồ tỉnh (khach_theo_tinh.doanh_thu_12t) đọc nó.
CREATE VIEW mart.doanh_thu_12t AS
SELECT k.customer_code,
       coalesce(sum(l.doanh_thu_thuan), 0) AS dt_12t
FROM mart.khach_360 k
CROSS JOIN mart.moc_thoi_gian m
LEFT JOIN mart.lan_mua l
       ON l.customer_code = k.customer_code
      AND l.sales_date > m.hom_nay - 365
GROUP BY k.customer_code;

COMMENT ON VIEW mart.doanh_thu_12t IS
  'Doanh thu thuần 12 tháng (sales_date > hom_nay - 365) của từng khách — nơi DUY NHẤT định
   nghĩa "doanh thu 12 tháng" của khách (trước 055 là mart.hang_doanh_thu.dt_12t).';


-- Nhóm việc (020): 'tut' xét hạng S/A của OBC; cả ba nhánh qua cổng khong_goi.
-- Nhánh 'im' = trang_thai IN ('canh_bao','da_roi_bo') AND NOT khong_goi — kome/khach_hang.py
-- (danh_ba, can_xu_ly, dem_va_can_xu_ly) và mart.uu_tien_lien_he viết ĐÚNG vị từ đó (có test canh).
CREATE OR REPLACE VIEW mart.khach_nhom_viec AS
SELECT customer_code, 'im' AS nhom
FROM mart.khach_360
WHERE trang_thai IN ('canh_bao', 'da_roi_bo') AND NOT khong_goi

UNION ALL
SELECT k.customer_code, 'tut'
FROM mart.khach_360 k
CROSS JOIN mart.moc_thoi_gian m
WHERE k.hang_obc IN ('S', 'A') AND NOT k.khong_goi
  AND (SELECT coalesce(sum(doanh_thu_thuan), 0) FROM mart.lan_mua l
       WHERE l.customer_code = k.customer_code
         AND l.sales_date > m.hom_nay - 30)
      < 0.8 * (SELECT coalesce(sum(doanh_thu_thuan), 0) / 3.0 FROM mart.lan_mua l
               WHERE l.customer_code = k.customer_code
                 AND l.sales_date > m.hom_nay - 120
                 AND l.sales_date <= m.hom_nay - 30)

UNION ALL
SELECT customer_code, 'moi'
FROM mart.khach_360 k
CROSS JOIN mart.moc_thoi_gian m
WHERE k.lan_dau > m.hom_nay - 90
  AND k.ty_le_im_lang >= 1.2
  AND NOT k.khong_goi;


-- Bản đồ (025): doanh thu 12 tháng đọc mart.doanh_thu_12t; cột và công thức giữ nguyên.
CREATE OR REPLACE VIEW mart.khach_theo_tinh AS
SELECT k.prefecture,
       k.salesperson_code,
       count(*)                       AS so_khach,
       coalesce(sum(h.dt_12t), 0)::bigint AS doanh_thu_12t,
       count(*) FILTER (
           WHERE EXISTS (SELECT 1 FROM mart.khach_nhom_viec v
                          WHERE v.customer_code = k.customer_code
                            AND v.nhom = 'im')) AS can_goi
FROM mart.khach_360 k
LEFT JOIN mart.doanh_thu_12t h ON h.customer_code = k.customer_code
GROUP BY 1, 2;

COMMENT ON COLUMN mart.khach_theo_tinh.doanh_thu_12t IS
  'ĐỌC mart.doanh_thu_12t.dt_12t (055; trước là hang_doanh_thu) — không tự tính lại, không dùng
   khach_360.doanh_thu_thuan (đó là TOÀN BỘ LỊCH SỬ).';
COMMENT ON COLUMN mart.khach_theo_tinh.can_goi IS
  'Đếm qua EXISTS vào mart.khach_nhom_viec (nhom=''im''), không LEFT JOIN — một khách có thể
   thuộc nhiều nhóm việc cùng lúc. Khách khong_goi (※廃業※, hạng OBC Z/ZZ/ZZZ) đã bị
   khach_nhom_viec tự loại, dù vẫn được đếm ở so_khach.';

-- Hạng tự tính theo doanh thu: bỏ. Không CASCADE — còn ai phụ thuộc thì migration nổ ngay ở đây.
DROP VIEW mart.hang_doanh_thu;


-- Cần liên hệ (030): cùng cổng khong_goi.
CREATE OR REPLACE VIEW mart.uu_tien_lien_he AS
SELECT customer_code, ten, prefecture, phone, salesperson_code,
       doanh_thu_thuan, lan_cuoi, so_ngay_im_lang, nhip_ngay, ty_le_im_lang,
       trang_thai,
       CASE trang_thai
         WHEN 'da_roi_bo'   THEN 'lau_khong_mua'
         WHEN 'canh_bao'    THEN 'qua_han'
         ELSE                    'sap_den_han'
       END AS ly_do,
       CASE trang_thai
         WHEN 'da_roi_bo'   THEN 1
         WHEN 'canh_bao'    THEN 2
         ELSE                    3
       END AS thu_tu
FROM mart.khach_360
WHERE NOT khong_goi
  AND (trang_thai IN ('da_roi_bo', 'canh_bao')
       OR (trang_thai = 'binh_thuong' AND ty_le_im_lang >= 1));


-- Nhìn theo tháng (037): nhãn 'khong_goi' đọc cổng khong_goi thay cho da_ngung. Còn lại nguyên văn.
CREATE OR REPLACE VIEW mart.khach_thang_nay AS
WITH m AS MATERIALIZED (
    SELECT hom_nay,
           date_trunc('month', hom_nay)::date                        AS dau,
           (date_trunc('month', hom_nay) - interval '1 month')::date AS dau_1,
           (date_trunc('month', hom_nay) - interval '3 month')::date AS dau_3,
           extract(day FROM hom_nay)::int                            AS d,
           hom_nay = (date_trunc('month', hom_nay) + interval '1 month - 1 day')::date AS cuoi
    FROM mart.moc_thoi_gian
    WHERE hom_nay IS NOT NULL
), c AS (
    SELECT l.customer_code,
           sum(l.doanh_thu_thuan) FILTER (WHERE l.sales_date >= m.dau)          AS dt0,
           sum(l.doanh_thu_thuan) FILTER (WHERE l.sales_date >= m.dau_1
                                            AND l.sales_date <  m.dau)          AS dt1,
           sum(l.doanh_thu_thuan) FILTER (WHERE l.sales_date <  m.dau)          AS dt3,
           coalesce(bool_or(l.doanh_thu_thuan > 0 AND l.sales_date >= m.dau), false) AS co0,
           coalesce(bool_or(l.doanh_thu_thuan > 0 AND l.sales_date >= m.dau_1
                            AND l.sales_date < m.dau
                            AND (m.cuoi OR extract(day FROM l.sales_date) <= m.d)), false) AS co1_den_ngay,
           sum(l.doanh_thu_thuan) FILTER (WHERE l.sales_date >= m.dau_1 AND l.sales_date < m.dau
                            AND (m.cuoi OR extract(day FROM l.sales_date) <= m.d))       AS dt1_den_ngay,
           count(DISTINCT date_trunc('month', l.sales_date))
               FILTER (WHERE l.doanh_thu_thuan > 0 AND l.sales_date < m.dau)    AS so_thang,
           count(DISTINCT date_trunc('month', l.sales_date))
               FILTER (WHERE l.doanh_thu_thuan > 0 AND l.sales_date < m.dau
                         AND (m.cuoi OR extract(day FROM l.sales_date) <= m.d)) AS so_thang_den_ngay
    FROM m
    JOIN mart.lan_mua l ON l.sales_date >= m.dau_3 AND l.sales_date <= m.hom_nay
    GROUP BY l.customer_code
)
SELECT c.customer_code,
       coalesce(nullif(d.customer_name, ''), c.customer_code) AS ten,
       d.salesperson_code,
       to_char(m.dau, 'YYYY-MM')        AS thang,
       m.hom_nay                        AS ngay_moc,
       coalesce(c.dt0, 0)               AS dt_thang_nay,
       coalesce(c.dt1, 0)               AS dt_thang_truoc,
       round(coalesce(c.dt3, 0) / 3.0)::bigint AS dt_tb_3_thang,
       c.so_thang::int                  AS so_thang_mua_3,
       c.so_thang_den_ngay::int         AS so_thang_den_ngay,
       c.co1_den_ngay                   AS thang_truoc_den_ngay,
       CASE
         WHEN coalesce(h.khong_goi, false)               THEN 'khong_goi'
         WHEN c.co0                                      THEN 'da_mua'
         WHEN c.so_thang >= 2 AND c.so_thang_den_ngay >= 2 THEN 'tre'
         WHEN c.so_thang >= 2                            THEN 'chua_toi_ngay'
         ELSE                                                 'khac'
       END AS nhan,
       coalesce(c.dt1_den_ngay, 0)      AS dt_thang_truoc_den_ngay
FROM c
CROSS JOIN m
LEFT JOIN core.dim_customer d ON d.customer_code = c.customer_code AND d.is_current
LEFT JOIN mart.dau_hieu_khach h ON h.customer_code = c.customer_code;


-- Cặp (khách, mã) (054): nhãn 'khong_goi' đọc cổng khong_goi thay cho da_ngung. Chữ ký giữ
-- nguyên nên CREATE OR REPLACE được; thân còn lại NGUYÊN VĂN 054.
CREATE OR REPLACE FUNCTION mart.khach_mat_hang_cua(p_mas text[])
RETURNS TABLE (customer_code text, product_code text, ten_hang text, doanh_thu_thuan numeric,
               lai_gop numeric, so_luong numeric, so_lan bigint, lan_dau date, lan_cuoi date,
               nhip_ngay double precision, du_kien_lan_toi date, tre_ngay integer,
               trang_thai_cap text)
LANGUAGE sql STABLE AS $$
    SELECT y.customer_code, y.product_code, y.ten_hang, y.doanh_thu_thuan,
           y.lai_gop, y.so_luong, y.so_lan, y.lan_dau, y.lan_cuoi, y.nhip_ngay,
           y.du_kien_lan_toi, y.tre_ngay,
           CASE
             WHEN coalesce(dh.khong_goi, false) THEN 'khong_goi'
             WHEN y.tre_ngay >= y.nhip_ngay THEN 'ngung'
             ELSE 'mua'
           END                                                AS trang_thai_cap
    FROM (
        SELECT x.customer_code, x.product_code, x.ten_hang, x.doanh_thu_thuan,
               x.lai_gop, x.so_luong, x.so_lan, x.lan_dau, x.lan_cuoi,
               x.nhip_ngay, x.du_kien_lan_toi,
               CASE WHEN x.hom_nay > x.du_kien_lan_toi
                    THEN x.hom_nay - x.du_kien_lan_toi END      AS tre_ngay
        FROM (
            SELECT f.customer_code, f.product_code,
                   coalesce(nullif(s.product_name, ''), f.product_code) AS ten_hang,
                   sum(f.amount - f.tax_amount) AS doanh_thu_thuan,
                   sum(f.gross_profit)          AS lai_gop,
                   sum(f.qty)                   AS so_luong,
                   count(DISTINCT f.sales_date) AS so_lan,
                   min(f.sales_date)            AS lan_dau,
                   max(f.sales_date)            AS lan_cuoi,
                   CASE WHEN n.so_khoang >= 2 THEN n.nhip_ngay END AS nhip_ngay,
                   CASE WHEN n.so_khoang >= 2
                        THEN (max(f.sales_date) + n.nhip_ngay * interval '1 day')::date
                   END AS du_kien_lan_toi,
                   m.hom_nay AS hom_nay
            FROM mart.ban_den_moc f
            LEFT JOIN core.dim_product s ON s.product_code = f.product_code
            LEFT JOIN mart.nhip_mat_hang_cua(p_mas) n
                   ON n.customer_code = f.customer_code
                  AND n.product_code = f.product_code
            CROSS JOIN mart.moc_thoi_gian m
            WHERE (p_mas IS NULL OR f.product_code = ANY(p_mas))
              AND NOT mart.khong_phai_hang(f.product_code, s.kind_code, s.food_category_name)
              AND NOT EXISTS (SELECT 1 FROM mart.ma_ngung_ban_an a WHERE a.product_code = f.product_code)
            GROUP BY f.customer_code, f.product_code, s.product_name,
                     n.so_khoang, n.nhip_ngay, m.hom_nay
        ) x
    ) y
    LEFT JOIN mart.dau_hieu_khach dh ON dh.customer_code = y.customer_code
$$;

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
