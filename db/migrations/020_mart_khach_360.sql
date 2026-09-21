-- 020: chỉ số của Customer 360 (đợt 4a).
--
-- KHÔNG có MATERIALIZED VIEW ở đây, và đó là chủ ý. Đo thật 2026-09-22:
-- `EXPLAIN ANALYZE` của mart.khach_mat_hang lọc một khách chạy 10 ms, nhưng
-- cùng truy vấn đó đo từ Python qua pooler Tokyo mất 260 ms, và một round-trip
-- rỗng đã 47 ms. Nút thắt là SỐ LƯỢT HỎI, không phải sức tính. Materialized
-- view giải quyết nhầm vấn đề, và đổi lại phải có bước làm mới gắn vào pipeline
-- nạp — mà lộ trình dành đợt 6 làm đợt DUY NHẤT động vào pipeline.


-- Khoảng cách giữa hai lần mua CÙNG MỘT MÃ của cùng một khách.
-- Song song với mart.khoang_cach_mua (015) nhưng chia nhỏ thêm theo mã hàng.
CREATE VIEW mart.khoang_cach_mat_hang AS
SELECT customer_code, product_code, sales_date,
       sales_date - lag(sales_date) OVER (PARTITION BY customer_code, product_code
                                          ORDER BY sales_date) AS so_ngay_cach
FROM (SELECT DISTINCT customer_code, product_code, sales_date
      FROM core.fact_sales_line) x;


-- Nhịp mua theo từng mã. TRUNG VỊ, y hệt mart.nhip_mua — một khái niệm chỉ có
-- một công thức. Đổi công thức ở một chỗ mà quên chỗ kia là hai con số cùng tên
-- nói hai điều khác nhau.
CREATE VIEW mart.nhip_mat_hang AS
SELECT customer_code, product_code,
       count(*)                                                 AS so_khoang,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY so_ngay_cach) AS nhip_ngay
FROM mart.khoang_cach_mat_hang
WHERE so_ngay_cach IS NOT NULL
GROUP BY customer_code, product_code;


-- Thêm ba cột vào cuối khach_mat_hang. CREATE OR REPLACE giữ nguyên thứ tự và
-- kiểu của 9 cột cũ (bắt buộc của Postgres) và chỉ nối thêm ở cuối.
CREATE OR REPLACE VIEW mart.khach_mat_hang AS
SELECT f.customer_code, f.product_code,
       coalesce(nullif(s.product_name, ''), f.product_code) AS ten_hang,
       sum(f.amount - f.tax_amount) AS doanh_thu_thuan,
       sum(f.gross_profit)          AS lai_gop,
       sum(f.qty)                   AS so_luong,
       count(DISTINCT f.sales_date) AS so_lan,
       min(f.sales_date)            AS lan_dau,
       max(f.sales_date)            AS lan_cuoi,
       -- Dưới 2 khoảng cách = dưới 3 lần mua: không đủ để nói về "nhịp".
       -- NULL chứ không phải một con số, để trang hiện `—`.
       CASE WHEN n.so_khoang >= 2 THEN n.nhip_ngay END AS nhip_ngay,
       CASE WHEN n.so_khoang >= 2
            THEN max(f.sales_date) + (n.nhip_ngay || ' days')::interval
       END::date AS du_kien_lan_toi,
       -- Chỉ tính khi ĐÃ quá hạn. Số âm ở cột "trễ" sẽ bị đọc thành "sớm",
       -- mà đó không phải điều cột này nói.
       CASE WHEN n.so_khoang >= 2
             AND m.hom_nay > max(f.sales_date) + (n.nhip_ngay || ' days')::interval
            THEN m.hom_nay - (max(f.sales_date) + (n.nhip_ngay || ' days')::interval)::date
       END AS tre_ngay
FROM core.fact_sales_line f
LEFT JOIN core.dim_product s ON s.product_code = f.product_code
LEFT JOIN mart.nhip_mat_hang n
       ON n.customer_code = f.customer_code AND n.product_code = f.product_code
CROSS JOIN mart.moc_thoi_gian m
GROUP BY f.customer_code, f.product_code, s.product_name,
         n.so_khoang, n.nhip_ngay, m.hom_nay;


-- Hạng theo DOANH THU 12 THÁNG — chỉ số của CHÚNG TA, không phải 得意先ランク
-- của OBC. Lý do: rank_code của OBC có 10 nhóm ('0008': 605 khách, '0005': 402…)
-- và KHÔNG file xuất nào ta nạp có tên của các mã đó, nên hiển thị "0008: 605
-- khách" không nói gì với người đọc. Năm bậc và tên chữ cái lấy từ gói thiết kế;
-- cách chia là của ta. Nhãn trên trang PHẢI đọc là "hạng theo doanh thu 12
-- tháng" — gọi tắt là "hạng" thì sẽ có người đối chiếu với OBC rồi thấy lệch.
CREATE VIEW mart.hang_doanh_thu AS
WITH dt AS (
    SELECT k.customer_code,
           coalesce(sum(l.doanh_thu_thuan), 0) AS dt_12t
    FROM mart.khach_360 k
    CROSS JOIN mart.moc_thoi_gian m
    LEFT JOIN mart.lan_mua l
           ON l.customer_code = k.customer_code
          AND l.sales_date > m.hom_nay - 365
    GROUP BY k.customer_code
), xh AS (
    SELECT customer_code, dt_12t,
           cume_dist() OVER (ORDER BY dt_12t DESC) AS vi_tri
    FROM dt
)
SELECT customer_code, dt_12t,
       CASE WHEN vi_tri <= 0.05 THEN 'S'
            WHEN vi_tri <= 0.20 THEN 'A'
            WHEN vi_tri <= 0.50 THEN 'B'
            WHEN vi_tri <= 0.80 THEN 'C'
            ELSE 'D' END AS hang
FROM xh;


-- Bốn nhóm việc của "Danh sách làm việc". Một khách có thể thuộc nhiều nhóm.
-- Nhóm "Toàn bộ danh bạ" KHÔNG có ở đây — nó là "không lọc", không phải một
-- nhóm; đưa vào đây là nhân đôi 1.710 dòng cho mỗi lần đọc view.
--
-- Khách OBC đã đánh dấu ※廃業※ / ※取引停止※ không vào nhóm nào: doanh nghiệp
-- đã phá sản thì im lặng là đúng, không phải bất thường (migration 016).
CREATE VIEW mart.khach_nhom_viec AS
-- im lặng quá 2 lần nhịp mua riêng của chính khách đó
SELECT customer_code, 'im' AS nhom
FROM mart.khach_360
WHERE ty_le_im_lang >= 2 AND dau_hieu_obc IS NULL

UNION ALL
-- hạng S/A mà 30 ngày gần nhất tụt dưới 80% trung bình ba kỳ 30 ngày trước đó.
-- CỬA SỔ TRƯỢT chứ không phải tháng lịch: so "tháng này" với "tháng trước" là
-- so một tháng dở dang với một tháng đủ, nên vào ngày mùng 3 thì khách nào
-- cũng trông như đang tụt.
SELECT k.customer_code, 'tut'
FROM mart.khach_360 k
JOIN mart.hang_doanh_thu h ON h.customer_code = k.customer_code
CROSS JOIN mart.moc_thoi_gian m
WHERE h.hang IN ('S', 'A') AND k.dau_hieu_obc IS NULL
  AND (SELECT coalesce(sum(doanh_thu_thuan), 0) FROM mart.lan_mua l
       WHERE l.customer_code = k.customer_code
         AND l.sales_date > m.hom_nay - 30)
      < 0.8 * (SELECT coalesce(sum(doanh_thu_thuan), 0) / 3.0 FROM mart.lan_mua l
               WHERE l.customer_code = k.customer_code
                 AND l.sales_date > m.hom_nay - 120
                 AND l.sales_date <= m.hom_nay - 30)

UNION ALL
-- khách mới (đơn đầu trong 90 ngày) mà đã im quá 1,2 lần nhịp
SELECT customer_code, 'moi'
FROM mart.khach_360 k
CROSS JOIN mart.moc_thoi_gian m
WHERE k.lan_dau > m.hom_nay - 90
  AND k.ty_le_im_lang >= 1.2
  AND k.dau_hieu_obc IS NULL;


-- Tải của từng nhân viên. LEFT JOIN từ dim_salesperson chứ không JOIN từ
-- khach_360: một người chưa có khách nào vẫn phải hiện với số 0, nếu không thì
-- bảng im lặng bỏ sót đúng người đang rảnh.
CREATE VIEW mart.tai_nhan_vien AS
SELECT s.salesperson_code, s.ten,
       count(k.customer_code)                  AS so_khach,
       coalesce(sum(k.doanh_thu_thuan), 0)     AS doanh_thu,
       count(*) FILTER (WHERE k.trang_thai IN ('canh_bao', 'da_roi_bo'))
                                               AS so_khach_canh_bao
FROM core.dim_salesperson s
LEFT JOIN mart.khach_360 k ON k.salesperson_code = s.salesperson_code
GROUP BY s.salesperson_code, s.ten;


GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
