-- Đợt 5b — các view phân tích cho /bao-cao và / (đặc tả
-- docs/superpowers/specs/2026-09-23-dot-5b-bao-cao-dashboard-design.md §3).
--
-- Ba luật của 014 vẫn giữ: doanh thu thuần = amount - tax_amount; KHÔNG lọc
-- 赤伝; kỳ lấy từ core.dim_date. Thêm hai luật đã học ở 5a:
--   * "cùng kỳ" NULL CHỈ khi tháng M-12 không có trong kho; có tháng mà không
--     bán thì là 0 (nếp cột cung_ky của 028).
--   * tăng trưởng chỉ tính khi mẫu số > 0 — mẫu số âm (赤伝) cho phần trăm
--     NGƯỢC DẤU.


-- 3.1 + 3.2 — Ngành hàng. Biểu thức "ngành" viết ĐÚNG MỘT LẦN, ở đây.
-- LEFT JOIN: 47.816 dòng bán có product_code = '' (dòng chú thích của phiếu,
-- đo 2026-09-23) và mọi mã chưa kịp vào danh mục vẫn giữ tiền của nó, rơi vào
-- '(chưa phân loại)'. JOIN thường thì tổng các ngành lệch tổng tháng.
CREATE VIEW mart.ban_theo_nganh_thang AS
SELECT b.thang,
       min(b.company_fy) AS company_fy,
       coalesce(nullif(p.food_category_name, ''), '(chưa phân loại)') AS nganh,
       sum(b.doanh_thu_thuan) AS doanh_thu_thuan,
       sum(b.gross_profit)    AS lai_gop
FROM mart.dong_ban b
LEFT JOIN core.dim_product p ON p.product_code = b.product_code
GROUP BY b.thang, coalesce(nullif(p.food_category_name, ''), '(chưa phân loại)');


-- 3.3 — Ngành × tháng so cùng kỳ. FULL JOIN: ngành bán năm ngoái mà năm nay
-- không bán phải CÓ dòng (doanh_thu_thuan = 0) — đó là ngành sụt mạnh nhất.
-- `ct` giữ lại chỉ những tháng CÓ trong kho: thiếu nó thì FULL JOIN đẻ ra
-- dòng cho 12 tháng tương lai từ dữ liệu năm trước.
CREATE VIEW mart.ban_theo_nganh_thang_so_sanh AS
WITH nt AS MATERIALIZED (
    SELECT * FROM mart.ban_theo_nganh_thang
), ct AS MATERIALIZED (
    SELECT thang, min(company_fy) AS company_fy FROM nt GROUP BY thang
), cap AS (
    SELECT coalesce(a.thang,
                    to_char(to_date(tr.thang, 'YYYY-MM') + interval '1 year', 'YYYY-MM')) AS thang,
           coalesce(a.nganh, tr.nganh) AS nganh,
           a.doanh_thu_thuan,
           a.lai_gop,
           tr.doanh_thu_thuan AS dt_tr
    FROM nt a
    FULL JOIN nt tr
           ON tr.nganh = a.nganh
          AND tr.thang = to_char(to_date(a.thang, 'YYYY-MM') - interval '1 year', 'YYYY-MM')
)
SELECT c.thang,
       t.company_fy,
       c.nganh,
       coalesce(c.doanh_thu_thuan, 0) AS doanh_thu_thuan,
       coalesce(c.lai_gop, 0)         AS lai_gop,
       CASE WHEN ck.thang IS NOT NULL THEN coalesce(c.dt_tr, 0) END AS dt_cung_ky,
       (ck.thang IS NOT NULL) AS co_cung_ky,
       CASE WHEN c.dt_tr > 0
            THEN coalesce(c.doanh_thu_thuan, 0)::numeric / c.dt_tr - 1 END AS tang_truong
FROM cap c
JOIN ct t ON t.thang = c.thang
LEFT JOIN ct ck
       ON ck.thang = to_char(to_date(c.thang, 'YYYY-MM') - interval '1 year', 'YYYY-MM');


-- 3.3b — Ngành × kỳ. dt_cung_ky là NULL ở tháng không có cùng kỳ, nên sum()
-- của nó tự chỉ cộng các tháng đối chiếu; dt_doi_chieu lọc CÙNG tập tháng đó,
-- để chênh lệch là cùng tháng trừ cùng tháng.
CREATE VIEW mart.nganh_ky_cung_ky AS
SELECT company_fy,
       nganh,
       sum(doanh_thu_thuan) AS doanh_thu_thuan,
       sum(lai_gop)         AS lai_gop,
       sum(doanh_thu_thuan) FILTER (WHERE co_cung_ky) AS dt_doi_chieu,
       sum(dt_cung_ky)      AS dt_cung_ky,
       sum(doanh_thu_thuan) FILTER (WHERE co_cung_ky) - sum(dt_cung_ky) AS chenh_lech,
       CASE WHEN sum(dt_cung_ky) > 0
            THEN (sum(doanh_thu_thuan) FILTER (WHERE co_cung_ky))::numeric
                 / sum(dt_cung_ky) - 1 END AS tang_truong
FROM mart.ban_theo_nganh_thang_so_sanh
GROUP BY company_fy, nganh;


-- 3.4 — Kỳ so cùng kỳ, CÙNG THÁNG với cùng tháng. Kỳ 6 chỉ có 5 tháng: so cả
-- kỳ 7 với cả kỳ 6 ra "+140%", đúng số học mà nói dối kinh doanh.
--
-- Tháng đối chiếu = tháng có dòng bán VÀ tháng M-12 cũng có dòng bán (cùng
-- định nghĩa "có trong kho" với co_cung_ky). Lọc mart.dong_ban theo DẢI
-- sales_date chứ không theo cột `thang` (to_char, không có chỉ mục): đo thật
-- 2026-09-23 là 332 ms so với 960 ms, cùng kết quả đến từng yên. `moc` trải
-- mỗi tháng đối chiếu thành hai dòng (tháng này, tháng M-12) để dong_ban chỉ
-- được đọc trong MỘT phép nối.
CREATE VIEW mart.ky_cung_ky AS
WITH doi AS MATERIALIZED (
    SELECT d.company_fy,
           d.date_key                           AS tu,
           (d.date_key - interval '1 year')::date AS tu_ck
    FROM core.dim_date d
    WHERE extract(day FROM d.date_key) = 1
      AND EXISTS (SELECT 1 FROM core.fact_sales_line f
                  WHERE f.sales_date >= d.date_key
                    AND f.sales_date <  d.date_key + interval '1 month')
      AND EXISTS (SELECT 1 FROM core.fact_sales_line f
                  WHERE f.sales_date >= d.date_key - interval '1 year'
                    AND f.sales_date <  d.date_key - interval '11 months')
), moc AS (
    SELECT company_fy, tu, true AS la_nay FROM doi
    UNION ALL
    SELECT company_fy, tu_ck, false FROM doi
), gop AS (
    SELECT m.company_fy, m.la_nay,
           count(DISTINCT m.tu)            AS so_thang,
           to_char(min(m.tu), 'YYYY-MM')   AS tu,
           to_char(max(m.tu), 'YYYY-MM')   AS den,
           sum(b.doanh_thu_thuan)          AS dt,
           sum(b.gross_profit)             AS lg,
           count(DISTINCT b.customer_code) AS so_khach
    FROM moc m
    JOIN mart.dong_ban b
      ON b.sales_date >= m.tu AND b.sales_date < m.tu + interval '1 month'
    GROUP BY m.company_fy, m.la_nay
)
SELECT k.company_fy,
       coalesce(n.so_thang, 0) AS so_thang_doi_chieu,
       n.tu  AS thang_dau_doi_chieu,
       n.den AS thang_cuoi_doi_chieu,
       n.dt, n.lg, n.so_khach,
       t.dt       AS dt_ck,
       t.lg       AS lg_ck,
       t.so_khach AS so_khach_ck
-- Danh sách kỳ lấy từ LỊCH trong dải min→max(sales_date) (hai lần tra chỉ
-- mục), không từ mart.ban_theo_thang — view đó gộp trọn bảng bán (~160 ms)
-- chỉ để trả về hai con số kỳ.
FROM (SELECT DISTINCT d.company_fy
      FROM core.dim_date d
      WHERE d.date_key BETWEEN (SELECT min(sales_date) FROM core.fact_sales_line)
                           AND (SELECT max(sales_date) FROM core.fact_sales_line)) k
LEFT JOIN gop n ON n.company_fy = k.company_fy AND n.la_nay
LEFT JOIN gop t ON t.company_fy = k.company_fy AND NOT t.la_nay;


-- 3.5 — Pareto. Gộp theo KHÁCH, không theo (khách, người phụ trách) như
-- mart.ban_theo_khach: khách đổi người phụ trách giữa kỳ sẽ chiếm hai cột.
-- ROWS + khoá phụ customer_code: thứ tự xác định, hai khách bằng tiền nhau
-- không đổi chỗ giữa hai lần mở trang, và luỹ kế không nhảy bậc ở chỗ hoà.
CREATE VIEW mart.tap_trung_khach AS
WITH k AS (
    SELECT company_fy, customer_code, sum(doanh_thu_thuan) AS dt
    FROM mart.dong_ban
    GROUP BY company_fy, customer_code
)
SELECT k.company_fy,
       k.customer_code,
       coalesce(nullif(c.customer_name, ''), '(chưa có tên)') AS ten_khach,
       k.dt AS doanh_thu_thuan,
       row_number() OVER w AS thu_hang,
       k.dt::numeric / nullif(sum(k.dt) OVER (PARTITION BY k.company_fy), 0) AS ty_trong,
       (sum(k.dt) OVER w)::numeric
           / nullif(sum(k.dt) OVER (PARTITION BY k.company_fy), 0) AS luy_ke
FROM k
LEFT JOIN core.dim_customer c
       ON c.customer_code = k.customer_code AND c.is_current
WINDOW w AS (PARTITION BY k.company_fy
             ORDER BY k.dt DESC, k.customer_code
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW);


-- 3.6 — Theo ngày, nối TỪ lịch: ngày không bán vẫn có dòng mang số 0, để
-- trục hoành của biểu đồ xu hướng không co lại. coalesce(…, 0) đúng ở đây:
-- trong dải dữ liệu, không có phiếu nghĩa là bán 0 đồng, không phải "không
-- biết".
CREATE VIEW mart.ban_theo_ngay AS
WITH b AS (
    SELECT sales_date,
           sum(doanh_thu_thuan)          AS dt,
           sum(gross_profit)             AS lg,
           count(DISTINCT slip_no)       AS so_phieu,
           count(DISTINCT customer_code) AS so_khach
    FROM mart.dong_ban
    GROUP BY sales_date
), dai AS (
    SELECT min(sales_date) AS tu, max(sales_date) AS den FROM core.fact_sales_line
)
SELECT d.date_key AS ngay,
       to_char(d.date_key, 'YYYY-MM') AS thang,
       coalesce(b.dt, 0)       AS doanh_thu_thuan,
       coalesce(b.lg, 0)       AS lai_gop,
       coalesce(b.so_phieu, 0) AS so_phieu,
       coalesce(b.so_khach, 0) AS so_khach
FROM dai
JOIN core.dim_date d ON d.date_key BETWEEN dai.tu AND dai.den
LEFT JOIN b ON b.sales_date = d.date_key;


-- 3.7 — Tháng của hom_nay, từ mùng 1 tới hom_nay, so với CÙNG DẢI NGÀY năm
-- trước (không phải trọn tháng năm trước: 12 ngày đầu tháng so với cả một
-- tháng thì giữa tháng nào cũng "sụt 60%"). `hom_nay - interval '1 year'`
-- của Postgres tự kẹp 29/2 về 28/2.
-- `dai.den` ở 3.6 và `hom_nay` ở đây cùng là max(sales_date) — cùng định
-- nghĩa với mart.moc_thoi_gian.
CREATE VIEW mart.thang_den_hom_nay AS
WITH r AS (
    SELECT hom_nay,
           date_trunc('month', hom_nay)::date                        AS tu,
           (date_trunc('month', hom_nay) - interval '1 year')::date  AS tu_ck,
           (hom_nay - interval '1 year')::date                       AS den_ck
    FROM mart.moc_thoi_gian
), g AS (
    SELECT sum(b.doanh_thu_thuan) FILTER (WHERE b.sales_date >= r.tu)            AS dt,
           sum(b.gross_profit)    FILTER (WHERE b.sales_date >= r.tu)            AS lg,
           count(DISTINCT b.customer_code) FILTER (WHERE b.sales_date >= r.tu)   AS so_khach,
           count(DISTINCT b.slip_no)       FILTER (WHERE b.sales_date >= r.tu)   AS so_phieu,
           sum(b.doanh_thu_thuan) FILTER (WHERE b.sales_date <= r.den_ck)        AS dt_ck,
           sum(b.gross_profit)    FILTER (WHERE b.sales_date <= r.den_ck)        AS lg_ck,
           count(DISTINCT b.customer_code) FILTER (WHERE b.sales_date <= r.den_ck) AS so_khach_ck
    FROM r
    JOIN mart.dong_ban b
      ON (b.sales_date BETWEEN r.tu AND r.hom_nay)
      OR (b.sales_date BETWEEN r.tu_ck AND r.den_ck)
)
SELECT to_char(r.hom_nay, 'YYYY-MM') AS thang,
       r.tu AS tu_ngay,
       r.hom_nay AS den_ngay,
       r.tu_ck AS tu_ngay_ck,
       r.den_ck AS den_ngay_ck,
       coalesce(g.dt, 0)       AS dt,
       coalesce(g.lg, 0)       AS lg,
       coalesce(g.so_khach, 0) AS so_khach,
       coalesce(g.so_phieu, 0) AS so_phieu,
       ck.co AS co_cung_ky,
       CASE WHEN ck.co THEN coalesce(g.dt_ck, 0) END       AS dt_ck,
       CASE WHEN ck.co THEN coalesce(g.lg_ck, 0) END       AS lg_ck,
       CASE WHEN ck.co THEN coalesce(g.so_khach_ck, 0) END AS so_khach_ck
FROM r
CROSS JOIN g
CROSS JOIN LATERAL (
    SELECT EXISTS (SELECT 1 FROM core.fact_sales_line f
                   WHERE f.sales_date >= r.tu_ck
                     AND f.sales_date < (r.tu_ck + interval '1 month')) AS co
) ck
WHERE r.hom_nay IS NOT NULL;


-- Bắt buộc: ALTER DEFAULT PRIVILEGES của 009 KHÔNG có kome_ingest, và quyền
-- của chủ view chỉ phủ bảng gốc, không phủ chính view (bất biến GRANT, 026).
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
