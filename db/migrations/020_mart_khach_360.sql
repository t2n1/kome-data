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
--
-- "Ngày dự kiến mua lại" (lan_cuoi + nhip_ngay) chỉ được TÍNH MỘT LẦN ở lớp
-- con `x`, rồi tái dùng cho cả `du_kien_lan_toi` lẫn `tre_ngay` ở lớp ngoài.
-- Viết biểu thức đó ba lần (đã từng làm) là ba chỗ phải sửa giống hệt nhau
-- mỗi khi đổi công thức — sửa một chỗ quên hai chỗ là đúng loại lỗi cả file
-- này cảnh báo. Dùng `nhip_ngay * interval '1 day'` thay vì nối chuỗi
-- `(nhip_ngay || ' days')::interval`: nối chuỗi phụ thuộc cách Postgres IN
-- một numeric ra text (locale, ký số thập phân), còn nhân với interval thì
-- không.
CREATE OR REPLACE VIEW mart.khach_mat_hang AS
SELECT customer_code, product_code, ten_hang, doanh_thu_thuan, lai_gop,
       so_luong, so_lan, lan_dau, lan_cuoi, nhip_ngay, du_kien_lan_toi,
       -- Chỉ tính khi ĐÃ quá hạn. Số âm ở cột "trễ" sẽ bị đọc thành "sớm",
       -- mà đó không phải điều cột này nói. du_kien_lan_toi NULL thì so sánh
       -- ra NULL luôn, không cần lặp lại điều kiện so_khoang >= 2 ở đây.
       CASE WHEN hom_nay > du_kien_lan_toi THEN hom_nay - du_kien_lan_toi END AS tre_ngay
FROM (
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
                THEN (max(f.sales_date) + n.nhip_ngay * interval '1 day')::date
           END AS du_kien_lan_toi,
           m.hom_nay AS hom_nay
    FROM core.fact_sales_line f
    LEFT JOIN core.dim_product s ON s.product_code = f.product_code
    LEFT JOIN mart.nhip_mat_hang n
           ON n.customer_code = f.customer_code AND n.product_code = f.product_code
    CROSS JOIN mart.moc_thoi_gian m
    GROUP BY f.customer_code, f.product_code, s.product_name,
             n.so_khoang, n.nhip_ngay, m.hom_nay
) x;


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
-- đã phá sản thì im lặng là đúng, không phải bất thường (migration 016). Cả
-- ba nhánh dưới đây loại khách đó qua `trang_thai <> 'ngung_giao_dich'` —
-- KHÔNG qua `dau_hieu_obc IS NULL`. Hai cột đó của 016 nói hai điều khác
-- nhau: `dau_hieu_obc` là NGUYÊN VĂN cụm ※…※ đầu tiên (cắt ở 20 ký tự, có
-- thể là một ghi chú vô hại không liên quan gì tới đóng cửa), còn `da_ngung`
-- (mà `trang_thai='ngung_giao_dich'` dựa vào) là kết quả so khớp từ khoá
-- đóng cửa thật, không giới hạn độ dài. Lấy nhầm cột thì lệch hai chiều: một
-- ghi chú ※…※ bất kỳ loại oan khách còn sống khỏi mọi nhóm việc, còn một dấu
-- đóng cửa dài hơn 20 ký tự lại cho khách đã phá sản quay về danh sách gọi.
CREATE VIEW mart.khach_nhom_viec AS
-- im lặng quá 2 lần nhịp mua riêng của chính khách đó. Lọc thẳng bằng
-- trang_thai — nhóm việc "im" và trang /can-xu-ly phải trả lời CÙNG một câu
-- hỏi, nên dùng CHUNG một điều kiện chứ không viết lại bằng ty_le_im_lang:
-- ty_le_im_lang không tự loại khách 'chua_du_lich_su' (dưới 3 lần mua, xem
-- comment ở khach_mat_hang phía trên) như trang_thai đã làm.
SELECT customer_code, 'im' AS nhom
FROM mart.khach_360
WHERE trang_thai IN ('canh_bao', 'da_roi_bo')

UNION ALL
-- hạng S/A mà 30 ngày gần nhất tụt dưới 80% trung bình ba kỳ 30 ngày trước đó.
-- CỬA SỔ TRƯỢT chứ không phải tháng lịch: so "tháng này" với "tháng trước" là
-- so một tháng dở dang với một tháng đủ, nên vào ngày mùng 3 thì khách nào
-- cũng trông như đang tụt.
SELECT k.customer_code, 'tut'
FROM mart.khach_360 k
JOIN mart.hang_doanh_thu h ON h.customer_code = k.customer_code
CROSS JOIN mart.moc_thoi_gian m
WHERE h.hang IN ('S', 'A') AND k.trang_thai <> 'ngung_giao_dich'
  AND (SELECT coalesce(sum(doanh_thu_thuan), 0) FROM mart.lan_mua l
       WHERE l.customer_code = k.customer_code
         AND l.sales_date > m.hom_nay - 30)
      < 0.8 * (SELECT coalesce(sum(doanh_thu_thuan), 0) / 3.0 FROM mart.lan_mua l
               WHERE l.customer_code = k.customer_code
                 AND l.sales_date > m.hom_nay - 120
                 AND l.sales_date <= m.hom_nay - 30)

UNION ALL
-- khách mới (đơn đầu trong 90 ngày) mà đã im quá 1,2 lần nhịp
--
-- CỐ Ý lọc bằng ty_le_im_lang >= 1,2 chứ KHÔNG qua trang_thai như nhánh
-- 'im' ở trên. "Khách mới" theo định nghĩa có rất ít lần mua — thường đúng
-- 2 — nên trang_thai của họ gần như luôn là 'chua_du_lich_su'. Lọc qua
-- trang_thai thì nhóm này gần như luôn rỗng, mất đúng lý do nó tồn tại.
-- Còn nhóm 'im' nói "khách này đang rời đi" — một khẳng định mạnh mà hai
-- điểm dữ liệu không đủ để đưa ra, nên nó CẦN cổng trang_thai chặn lại. Hai
-- nhóm chịu được mức chắc chắn khác nhau, nên cố ý dùng hai ngưỡng khác
-- nhau — không phải một chỗ sót lại quên đồng bộ với nhánh 'im'.
SELECT customer_code, 'moi'
FROM mart.khach_360 k
CROSS JOIN mart.moc_thoi_gian m
WHERE k.lan_dau > m.hom_nay - 90
  AND k.ty_le_im_lang >= 1.2
  AND k.trang_thai <> 'ngung_giao_dich';


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
