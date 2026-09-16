-- Lớp `mart`: ĐỊNH NGHĨA CHỈ SỐ, một nơi duy nhất.
--
-- Vì sao bắt buộc phải ở đây chứ không rải trong Python hay trong mẫu HTML:
-- "doanh thu" là một câu hỏi có nhiều câu trả lời đúng về mặt kỹ thuật (có
-- thuế / không thuế / trừ trả lại / theo ngày bán hay ngày lập hoá đơn). Khi
-- hai chỗ trong hệ thống trả lời khác nhau, người đọc không biết tin bên nào
-- — và mất niềm tin vào con số thì cả hệ thống này vô dụng.
--
-- BA LUẬT KHÔNG ĐƯỢC PHÁ:
--
-- 1. Doanh thu thuần = sum(amount - tax_amount). KHÔNG lấy thẳng `amount`:
--    `amount` đã gồm thuế tiêu dùng, cộng cả thuế vào doanh thu làm tỷ suất
--    lãi gộp tụt xuống một cách vô cớ.
--
-- 2. KHÔNG lọc bỏ 赤伝 (phiếu đỏ — hàng trả lại, số ÂM). Hàng trả lại là
--    doanh thu âm thật. Lọc đi là báo cáo đẹp hơn thực tế, và đúng vào lúc
--    có nhiều hàng trả lại thì báo cáo nói dối nhiều nhất.
--
-- 3. Kỳ kế toán lấy từ core.dim_date (company_fy, company_fy_no) — 1/8 →
--    31/7, KHÔNG phải năm tài chính Nhật chuẩn. Đừng tính lại bằng tay.

CREATE SCHEMA IF NOT EXISTS mart;


-- Nền chung: mỗi dòng bán kèm sẵn nhãn thời gian của kỳ công ty.
CREATE VIEW mart.dong_ban AS
SELECT f.*,
       d.company_fy,
       d.company_fy_no,
       d.company_fy_label,
       d.company_fy_month,
       to_char(f.sales_date, 'YYYY-MM')        AS thang,
       f.amount - f.tax_amount                  AS doanh_thu_thuan
FROM core.fact_sales_line f
JOIN core.dim_date d ON d.date_key = f.sales_date;

COMMENT ON VIEW mart.dong_ban IS
  'Nền của mọi báo cáo. doanh_thu_thuan = amount - tax_amount (ĐÃ trừ thuế).';


CREATE VIEW mart.ban_theo_thang AS
SELECT thang,
       min(company_fy)        AS company_fy,
       min(company_fy_no)     AS company_fy_no,
       min(company_fy_month)  AS thang_trong_ky,
       sum(doanh_thu_thuan)   AS doanh_thu_thuan,
       sum(gross_profit)      AS lai_gop,
       sum(doanh_thu_thuan) - sum(gross_profit) AS gia_von,
       -- nullif: tháng không có doanh thu thì tỷ suất là NULL để màn hình nói
       -- "chưa có số". Hiện 0% sẽ bị đọc thành "bán mà không lãi đồng nào".
       sum(gross_profit)::numeric / nullif(sum(doanh_thu_thuan), 0) AS ty_suat,
       count(DISTINCT slip_no)      AS so_phieu,
       count(DISTINCT customer_code) AS so_khach,
       count(*)                      AS so_dong
FROM mart.dong_ban
GROUP BY thang;


-- So với CÙNG KỲ NĂM TRƯỚC. Cột `co_cung_ky` là phần quan trọng nhất ở đây:
-- dữ liệu bán bắt đầu 2025-03-03 và trước mốc đó KHÔNG TỒN TẠI (đặc tả §2.2.1
-- — công ty không còn lưu). Với những tháng không có tháng đối chiếu, màn hình
-- PHẢI nói rõ "không có dữ liệu cùng kỳ", chứ để trống hay hiện 0% thì người
-- đọc sẽ tưởng doanh thu sụt 100%.
CREATE VIEW mart.ban_theo_thang_so_sanh AS
SELECT t.*,
       tr.doanh_thu_thuan AS dt_cung_ky,
       tr.ty_suat         AS ty_suat_cung_ky,
       (tr.thang IS NOT NULL) AS co_cung_ky,
       CASE WHEN tr.doanh_thu_thuan > 0
            THEN t.doanh_thu_thuan::numeric / tr.doanh_thu_thuan - 1 END AS tang_truong
FROM mart.ban_theo_thang t
LEFT JOIN mart.ban_theo_thang tr
       ON tr.thang = to_char(to_date(t.thang, 'YYYY-MM') - interval '1 year', 'YYYY-MM');


CREATE VIEW mart.tong_theo_ky AS
SELECT company_fy,
       min(company_fy_no)    AS company_fy_no,
       min(company_fy_label) AS nhan,
       min(sales_date)       AS ngay_dau,
       max(sales_date)       AS ngay_cuoi,
       count(DISTINCT to_char(sales_date, 'YYYY-MM')) AS so_thang_co_du_lieu,
       sum(doanh_thu_thuan)  AS doanh_thu_thuan,
       sum(gross_profit)     AS lai_gop,
       sum(gross_profit)::numeric / nullif(sum(doanh_thu_thuan), 0) AS ty_suat,
       count(DISTINCT customer_code) AS so_khach,
       count(DISTINCT slip_no)       AS so_phieu
FROM mart.dong_ban
GROUP BY company_fy;

COMMENT ON VIEW mart.tong_theo_ky IS
  'so_thang_co_du_lieu < 12 nghĩa là kỳ KHÔNG đầy đủ — đừng đem tổng kỳ đó so
   với kỳ khác. Kỳ 6 chỉ có 5 tháng vì dữ liệu bắt đầu 2025-03-03.';


CREATE VIEW mart.ban_theo_khach AS
SELECT b.company_fy,
       b.customer_code,
       coalesce(nullif(k.customer_name, ''), '(chưa có tên)') AS ten_khach,
       k.prefecture,
       k.category_code,
       b.salesperson_code,
       sum(b.doanh_thu_thuan) AS doanh_thu_thuan,
       sum(b.gross_profit)    AS lai_gop,
       sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0) AS ty_suat,
       count(DISTINCT b.slip_no) AS so_phieu,
       max(b.sales_date)         AS mua_gan_nhat
FROM mart.dong_ban b
-- is_current: SCD2 giữ nhiều phiên bản mỗi khách; lấy bản hiện hành để tên
-- hiển thị là tên mới nhất. LEFT JOIN vì có mã khách trong phiếu bán chưa
-- kịp xuất sang file 得意先全情報 — mất doanh thu của họ còn tệ hơn mất tên.
LEFT JOIN core.dim_customer k
       ON k.customer_code = b.customer_code AND k.is_current
GROUP BY b.company_fy, b.customer_code, k.customer_name, k.prefecture,
         k.category_code, b.salesperson_code;


CREATE VIEW mart.ban_theo_san_pham AS
SELECT b.company_fy,
       b.product_code,
       coalesce(nullif(s.product_name, ''), b.product_code) AS ten_hang,
       s.food_category_name,
       sum(b.doanh_thu_thuan) AS doanh_thu_thuan,
       sum(b.gross_profit)    AS lai_gop,
       sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0) AS ty_suat,
       sum(b.qty)             AS so_luong,
       count(DISTINCT b.customer_code) AS so_khach_mua
FROM mart.dong_ban b
LEFT JOIN core.dim_product s ON s.product_code = b.product_code
GROUP BY b.company_fy, b.product_code, s.product_name, s.food_category_name;


CREATE VIEW mart.ban_theo_nhan_vien AS
SELECT company_fy,
       salesperson_code,
       sum(doanh_thu_thuan) AS doanh_thu_thuan,
       sum(gross_profit)    AS lai_gop,
       sum(gross_profit)::numeric / nullif(sum(doanh_thu_thuan), 0) AS ty_suat,
       count(DISTINCT customer_code) AS so_khach,
       count(DISTINCT slip_no)       AS so_phieu
FROM mart.dong_ban
GROUP BY company_fy, salesperson_code;


-- Quyền: mart là lớp CHỈ ĐỌC với mọi người. Không ai ghi vào đây — nội dung
-- của nó suy ra từ core, và một bảng mart sửa được bằng tay là một con số
-- không đối chiếu được với sổ cái OBC.
GRANT USAGE ON SCHEMA mart TO kome_app, kome_report, kome_ingest;
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
