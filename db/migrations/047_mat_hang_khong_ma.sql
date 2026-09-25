-- 047 — dòng không có mã hàng không phải một "mặt hàng" của khách.
--
-- Đo thật 2026-09-25: OBC xuất dòng điều chỉnh làm tròn (端数, product_code
-- rỗng, amount ±1 yên, qty 0) ở cả 売上伝票データ (6.570 dòng từ 6/2026) lẫn
-- 売上明細表 (2.388 dòng tháng 9). mart.khach_mat_hang gộp chúng thành MỘT cặp
-- (khách, '') có đủ nhịp mua, ngày dự kiến, nhãn trang_thai_cap: 1.531 khách có
-- cặp đó, 381 khách bị tính thêm 1 "mã đã ngừng mua", và hồ sơ khách hiện một
-- dòng KHÔNG TÊN "quá hạn 25 ngày" trong "Lịch mua dự kiến từng mã".
--
-- Sửa ở ĐÚNG view đó (nhà của trạng thái cặp — 024): lọc product_code rỗng.
-- Tiền của các dòng này VẪN nằm trong mọi tổng (mart.dong_ban, khach_360,
-- ban_theo_*): đó là doanh thu thật, chỉ không phải một mặt hàng.
-- mart.khach_mat_hang_khoang (039) GIỮ dòng đó vì danh sách mặt hàng theo khoảng
-- của hồ sơ khách phải cộng đúng bằng tổng khoảng
-- (tests/test_khoang_khach.py) — chỉ đặt cho nó một cái tên đọc được thay cho
-- chuỗi rỗng.
--
-- Thân view chép nguyên từ 040_moc_lui.sql; CHỈ thêm một vị từ WHERE.

CREATE OR REPLACE VIEW mart.khach_mat_hang AS
SELECT y.customer_code, y.product_code, y.ten_hang, y.doanh_thu_thuan,
       y.lai_gop, y.so_luong, y.so_lan, y.lan_dau, y.lan_cuoi, y.nhip_ngay,
       y.du_kien_lan_toi, y.tre_ngay,
       CASE
         -- Khách bị OBC đánh dấu ※廃業※/※取引停止※ (016). Xét TRƯỚC hai nhánh
         -- kia: đã đóng cửa thì im lặng là đúng, không phải tín hiệu.
         WHEN coalesce(dh.da_ngung, false) THEN 'khong_goi'
         -- im lặng >= 2 x nhịp riêng của CHÍNH CẶP NÀY (tre_ngay = số ngày quá
         -- ngày dự kiến mua lại = lan_cuoi + nhip_ngay, nên tre >= nhip tương
         -- đương im lặng >= 2 nhịp — đúng ngưỡng 'canh_bao' mà mart.khach_360
         -- dùng cho quan hệ khách hàng).
         WHEN y.tre_ngay >= y.nhip_ngay THEN 'ngung'
         -- Còn lại. `tre_ngay` NULL (chưa đủ 3 lần mua, hoặc chưa tới ngày dự
         -- kiến) cho ra NULL ở nhánh trên nên rơi xuống đây — CỐ Ý: "chưa đủ
         -- dữ liệu" không phải "đã ngừng".
         ELSE 'mua'
       END                                                AS trang_thai_cap
FROM (
    SELECT x.customer_code, x.product_code, x.ten_hang, x.doanh_thu_thuan,
           x.lai_gop, x.so_luong, x.so_lan, x.lan_dau, x.lan_cuoi,
           x.nhip_ngay, x.du_kien_lan_toi,
           -- Chỉ tính khi ĐÃ quá hạn. Số âm ở cột "trễ" sẽ bị đọc thành
           -- "sớm", mà đó không phải điều cột này nói. du_kien_lan_toi NULL
           -- thì so sánh ra NULL luôn, không cần lặp lại điều kiện
           -- so_khoang >= 2 ở đây.
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
               -- Dưới 2 khoảng cách = dưới 3 lần mua: không đủ để nói về
               -- "nhịp". NULL chứ không phải một con số, để trang hiện `—`.
               CASE WHEN n.so_khoang >= 2 THEN n.nhip_ngay END AS nhip_ngay,
               CASE WHEN n.so_khoang >= 2
                    THEN (max(f.sales_date) + n.nhip_ngay * interval '1 day')::date
               END AS du_kien_lan_toi,
               m.hom_nay AS hom_nay
        FROM mart.ban_den_moc f
        LEFT JOIN core.dim_product s ON s.product_code = f.product_code
        LEFT JOIN mart.nhip_mat_hang n
               ON n.customer_code = f.customer_code
              AND n.product_code = f.product_code
        CROSS JOIN mart.moc_thoi_gian m
        -- 047: dòng KHÔNG có mã hàng (điều chỉnh làm tròn / 端数 của OBC, vài
        -- yên mỗi phiếu) không phải một mặt hàng khách "mua theo nhịp".
        WHERE coalesce(f.product_code, '') <> ''
        GROUP BY f.customer_code, f.product_code, s.product_name,
                 n.so_khoang, n.nhip_ngay, m.hom_nay
    ) x
) y
LEFT JOIN mart.dau_hieu_khach dh ON dh.customer_code = y.customer_code;

CREATE OR REPLACE FUNCTION mart.khach_mat_hang_khoang(tu date, den date)
RETURNS TABLE (customer_code text, product_code text, ten_hang text, dt numeric, lg numeric,
               so_luong numeric, so_ngay_mua bigint, lan_cuoi date)
LANGUAGE sql STABLE
AS $$
    SELECT b.customer_code, b.product_code,
           CASE WHEN coalesce(b.product_code, '') = '' THEN '(điều chỉnh làm tròn — không mã hàng)'
                ELSE coalesce(nullif(s.product_name, ''), b.product_code) END,
           sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric, sum(b.qty)::numeric,
           count(DISTINCT b.sales_date), max(b.sales_date)
    FROM mart.dong_ban_khoang(tu, den) b
    LEFT JOIN core.dim_product s ON s.product_code = b.product_code
    GROUP BY b.customer_code, b.product_code, s.product_name
$$;
