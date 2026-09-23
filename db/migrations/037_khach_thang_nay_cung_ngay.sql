-- 037 — Thêm `dt_thang_truoc_den_ngay` vào CUỐI mart.khach_thang_nay (036) cho
-- danh sách khách React (giai đoạn 2): so doanh thu tháng này với tháng trước
-- CÙNG DẢI NGÀY. CREATE OR REPLACE chỉ cho thêm cột vào cuối — mọi cột và
-- nhãn của 036 giữ nguyên thứ tự và nghĩa. Chú thích định nghĩa: xem 036.
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
       -- Tháng trước, từ mùng 1 tới cùng ngày, đã có phiếu chưa — để so số
       -- khách đã mua với CÙNG DẢI NGÀY tháng trước (nếp 029 §3.7).
       c.co1_den_ngay                   AS thang_truoc_den_ngay,
       CASE
         WHEN coalesce(h.da_ngung, false)                THEN 'khong_goi'
         WHEN c.co0                                      THEN 'da_mua'
         WHEN c.so_thang >= 2 AND c.so_thang_den_ngay >= 2 THEN 'tre'
         WHEN c.so_thang >= 2                            THEN 'chua_toi_ngay'
         ELSE                                                 'khac'
       END AS nhan,
       -- 037: doanh thu tháng trước từ mùng 1 tới CÙNG NGÀY (cùng vị từ với
       -- thang_truoc_den_ngay ngay trên). Cột "so tháng trước" của danh sách
       -- khách so với con số này, KHÔNG với trọn tháng trước: giữa tháng mà so
       -- với cả tháng thì ai cũng "sụt 60%" (nếp 029 §3.7).
       coalesce(c.dt1_den_ngay, 0)      AS dt_thang_truoc_den_ngay
FROM c
CROSS JOIN m
LEFT JOIN core.dim_customer d ON d.customer_code = c.customer_code AND d.is_current
LEFT JOIN mart.dau_hieu_khach h ON h.customer_code = c.customer_code;

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
