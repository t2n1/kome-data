-- 036 — Nhìn theo THÁNG: khách này tháng này đã mua chưa.
--
-- Công ty chạy doanh thu theo tháng, nên câu hỏi hằng ngày của người phụ
-- trách là "khách quen nào tháng này chưa có đơn". Đây là MỘT định nghĩa cho
-- mọi chỗ hỏi câu đó (khối Tổng quan, cột thứ tư của /lien-he, bộ lọc danh
-- sách khách): các màn ĐỌC cột `nhan` và SO BẰNG, không màn nào tự viết lại
-- vị từ (cùng nếp 022/024).
--
-- KHÁC nhóm 'im' của mart.khach_nhom_viec (im lặng >= 2x nhịp mua riêng):
-- một bên theo tháng lịch, một bên theo nhịp riêng của khách. Hai khái niệm,
-- hai tên — không gộp.
--
-- "Tháng này" = tháng của mart.moc_thoi_gian.hom_nay (ngày bán mới nhất trong
-- kho), KHÔNG phải current_date — cùng bất biến mốc thời gian.
--
-- "Tháng có mua" = có ít nhất một lần mua (phiếu) doanh thu thuần > 0. Một
-- tháng chỉ có 赤伝 (hàng trả lại, số âm) không phải một tháng khách đã mua.
-- Doanh thu thì cộng ĐỦ, kể cả phiếu đỏ (luật không lọc bỏ 赤伝).
--
-- Nhãn, xét theo đúng thứ tự:
--   khong_goi     — khách ※廃業※/※取引停止※ (016) — xét TRƯỚC, như 024
--   da_mua        — tháng này đã có phiếu
--   tre           — mua đều (>= 2 trong 3 tháng trước) VÀ trong >= 2 tháng
--                   trước, ĐẾN CÙNG NGÀY TRONG THÁNG đã có phiếu — giờ thì chưa.
--                   Đây là nhóm cần gọi.
--   chua_toi_ngay — mua đều nhưng thường mua muộn hơn trong tháng
--   khac          — không mua đều, tháng này chưa mua
-- "Cùng ngày": extract(day) <= ngày của mốc — tháng ngắn tự kẹp (mốc 31/7
-- thì tháng 6 tính trọn). Và khi mốc là NGÀY CUỐI tháng (30/6, 28/2) thì các
-- tháng trước tính TRỌN tháng: tháng đã hết, khách thường mua ngày 31 không
-- phải "chưa tới ngày" (cột `cuoi`).
-- NHÃN chứ không phải boolean — đừng dùng NOT (xem bất biến 024).
--
-- Chỉ có dòng cho khách có ít nhất một lần mua trong [mùng 1 của 3 tháng
-- trước, mốc]. Không có dòng = không mua gì 4 tháng qua (không thể 'tre').
CREATE VIEW mart.khach_thang_nay AS
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
       END AS nhan
FROM c
CROSS JOIN m
LEFT JOIN core.dim_customer d ON d.customer_code = c.customer_code AND d.is_current
LEFT JOIN mart.dau_hieu_khach h ON h.customer_code = c.customer_code;

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
