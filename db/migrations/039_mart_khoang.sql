-- 039 — Chỉ số theo KHOẢNG NGÀY (đặc tả 2026-09-24-khoang-xem-thang-design.md §2).
--
-- Cả website mặc định xem theo tháng, có nút xem theo kỳ hoặc khoảng ngày tuỳ
-- chọn. Dải ngày do kome/khoang_xem.py giải; ĐỊNH NGHĨA chỉ số vẫn ở đây — mỗi
-- hàm là một "view nhận ngày": LANGUAGE sql STABLE, một câu SELECT, nên
-- Postgres gộp thẳng thân hàm vào câu gọi và dùng chỉ mục
-- fact_sales_line(sales_date) sẵn có (007).
--
-- Ba luật của 014 giữ nguyên vì mọi hàm đọc qua mart.dong_ban:
--   doanh thu thuần = amount − tax_amount · KHÔNG lọc 赤伝 · kỳ từ core.dim_date.
-- Tỷ suất luôn là TỶ SỐ CỦA CÁC TỔNG.
--
-- Đẳng thức có test canh (tests/test_mart_khoang.py): tổng một tháng trọn qua
-- tong_khoang = dòng mart.ban_theo_thang; tháng hiện tại = mart.thang_den_hom_nay;
-- Σ ngay_khoang = Σ nganh_khoang = tong_khoang.

-- Nhãn ngành: biểu thức này từng viết trong mart.ban_theo_nganh_thang (029).
-- Hàm mới cần cùng nhãn, nên biểu thức CHUYỂN vào một hàm và view kia gọi lại
-- nó — vẫn đúng MỘT chỗ viết (bất biến CLAUDE.md). `kome.bao_cao.NGANH_TRONG`
-- là bản chép bắt buộc ở tầng Python, có test so khớp.
CREATE FUNCTION mart.ten_nganh(food_category_name text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT coalesce(nullif(food_category_name, ''), '(chưa phân loại)') $$;

CREATE OR REPLACE VIEW mart.ban_theo_nganh_thang AS
SELECT b.thang,
       min(b.company_fy) AS company_fy,
       mart.ten_nganh(p.food_category_name) AS nganh,
       sum(b.doanh_thu_thuan) AS doanh_thu_thuan,
       sum(b.gross_profit)    AS lai_gop
FROM mart.dong_ban b
LEFT JOIN core.dim_product p ON p.product_code = b.product_code
GROUP BY b.thang, mart.ten_nganh(p.food_category_name);


-- Nền: dòng bán trong [tu, den] (cả hai đầu).
CREATE FUNCTION mart.dong_ban_khoang(tu date, den date) RETURNS SETOF mart.dong_ban
LANGUAGE sql STABLE
AS $$ SELECT * FROM mart.dong_ban WHERE sales_date BETWEEN tu AND den $$;


-- Tổng của khoảng — một dòng (tổng NULL khi không có dòng bán nào).
CREATE FUNCTION mart.tong_khoang(tu date, den date)
RETURNS TABLE (dt numeric, lg numeric, ty_suat numeric,
               so_phieu bigint, so_khach bigint, so_dong bigint)
LANGUAGE sql STABLE
AS $$
    SELECT sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric,
           sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0),
           count(DISTINCT b.slip_no), count(DISTINCT b.customer_code), count(*)
    FROM mart.dong_ban_khoang(tu, den) b
$$;


-- Theo ngày, nối TỪ LỊCH: ngày không bán vẫn có dòng mang số 0 (cùng lý lẽ
-- mart.ban_theo_ngay — trong dải dữ liệu, không có phiếu = bán 0 đồng).
CREATE FUNCTION mart.ngay_khoang(tu date, den date)
RETURNS TABLE (ngay date, dt numeric, lg numeric, so_phieu bigint, so_khach bigint)
LANGUAGE sql STABLE
AS $$
    SELECT d.date_key,
           coalesce(sum(b.doanh_thu_thuan), 0)::numeric, coalesce(sum(b.gross_profit), 0)::numeric,
           count(DISTINCT b.slip_no), count(DISTINCT b.customer_code)
    FROM core.dim_date d
    LEFT JOIN mart.dong_ban_khoang(tu, den) b ON b.sales_date = d.date_key
    WHERE d.date_key BETWEEN tu AND den
    GROUP BY d.date_key
    ORDER BY d.date_key
$$;


-- Theo tháng, các tháng CẮT theo [tu, den] (tháng đầu/cuối có thể không trọn —
-- `tu`/`den` của từng dòng nói rõ).
CREATE FUNCTION mart.thang_khoang(tu date, den date)
RETURNS TABLE (thang text, tu_ngay date, den_ngay date, dt numeric, lg numeric,
               so_phieu bigint, so_khach bigint)
LANGUAGE sql STABLE
AS $$
    SELECT to_char(d.date_key, 'YYYY-MM'), min(d.date_key), max(d.date_key),
           coalesce(sum(b.doanh_thu_thuan), 0)::numeric, coalesce(sum(b.gross_profit), 0)::numeric,
           count(DISTINCT b.slip_no), count(DISTINCT b.customer_code)
    FROM core.dim_date d
    LEFT JOIN mart.dong_ban_khoang(tu, den) b ON b.sales_date = d.date_key
    WHERE d.date_key BETWEEN tu AND den
    GROUP BY 1
    ORDER BY 1
$$;


-- Theo người phụ trách — cùng cột với mart.ban_theo_nhan_vien.
CREATE FUNCTION mart.sale_khoang(tu date, den date)
RETURNS TABLE (salesperson_code text, dt numeric, lg numeric, ty_suat numeric,
               so_khach bigint, so_phieu bigint)
LANGUAGE sql STABLE
AS $$
    SELECT b.salesperson_code, sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric,
           sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0),
           count(DISTINCT b.customer_code), count(DISTINCT b.slip_no)
    FROM mart.dong_ban_khoang(tu, den) b
    GROUP BY b.salesperson_code
$$;


-- Theo mã hàng — cùng cột với mart.ban_theo_san_pham (food_category_name THÔ,
-- như view đó; ghép ngành ở tầng gọi dùng bao_cao.NGANH_TRONG).
CREATE FUNCTION mart.mat_hang_khoang(tu date, den date)
RETURNS TABLE (product_code text, ten_hang text, food_category_name text,
               dt numeric, lg numeric, ty_suat numeric, so_luong numeric, so_khach bigint)
LANGUAGE sql STABLE
AS $$
    SELECT b.product_code, coalesce(nullif(s.product_name, ''), b.product_code),
           s.food_category_name,
           sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric,
           sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0),
           sum(b.qty)::numeric, count(DISTINCT b.customer_code)
    FROM mart.dong_ban_khoang(tu, den) b
    LEFT JOIN core.dim_product s ON s.product_code = b.product_code
    GROUP BY b.product_code, s.product_name, s.food_category_name
$$;


-- Theo khách — gộp theo KHÁCH (không theo khách × người phụ trách, cùng lý lẽ
-- mart.tap_trung_khach). so_ngay_mua = số ngày có phiếu.
CREATE FUNCTION mart.khach_khoang(tu date, den date)
RETURNS TABLE (customer_code text, dt numeric, lg numeric, ty_suat numeric,
               so_phieu bigint, so_ngay_mua bigint, lan_cuoi date)
LANGUAGE sql STABLE
AS $$
    SELECT b.customer_code, sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric,
           sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0),
           count(DISTINCT b.slip_no), count(DISTINCT b.sales_date), max(b.sales_date)
    FROM mart.dong_ban_khoang(tu, den) b
    GROUP BY b.customer_code
$$;


-- Theo ngành — LEFT JOIN sang dim_product: mã rỗng / chưa vào danh mục vẫn giữ
-- tiền của nó, rơi vào '(chưa phân loại)'.
CREATE FUNCTION mart.nganh_khoang(tu date, den date)
RETURNS TABLE (nganh text, dt numeric, lg numeric)
LANGUAGE sql STABLE
AS $$
    SELECT mart.ten_nganh(p.food_category_name),
           sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric
    FROM mart.dong_ban_khoang(tu, den) b
    LEFT JOIN core.dim_product p ON p.product_code = b.product_code
    GROUP BY 1
$$;


-- Ngành so sánh — cùng cột và cùng công thức với mart.nganh_ky_cung_ky:
--   dt/lg          : cả khoảng đang xem [tu, den]
--   dt_doi_chieu   : phần khoảng đem so [tu_dc, den_dc] (khác [tu, den] chỉ ở dạng Kỳ)
--   dt_cung_ky     : dải so sánh [tu_ss, den_ss]; NULL khi không có phép so
--   chenh_lech, tang_truong (gate > 0: 赤伝 có thể làm mẫu số âm)
-- FULL JOIN: ngành bán ở dải so sánh mà nay không bán vẫn CÓ dòng (dt = 0) —
-- ngành sụt mạnh nhất (bất biến FULL JOIN, CLAUDE.md). Truyền tu_ss = NULL khi
-- không có phép so: cột so sánh NULL, không đẻ ra dòng nào.
CREATE FUNCTION mart.nganh_so_sanh_khoang(tu date, den date, tu_dc date, den_dc date,
                                          tu_ss date, den_ss date)
RETURNS TABLE (nganh text, dt numeric, lg numeric, dt_doi_chieu numeric,
               dt_cung_ky numeric, chenh_lech numeric, tang_truong numeric)
LANGUAGE sql STABLE
AS $$
    WITH a AS (SELECT * FROM mart.nganh_khoang(tu, den)),
         c AS (SELECT * FROM mart.nganh_khoang(tu_dc, den_dc) WHERE tu_ss IS NOT NULL),
         s AS (SELECT * FROM mart.nganh_khoang(tu_ss, den_ss) WHERE tu_ss IS NOT NULL)
    SELECT coalesce(a.nganh, c.nganh, s.nganh),
           coalesce(a.dt, 0), coalesce(a.lg, 0),
           CASE WHEN tu_ss IS NOT NULL THEN coalesce(c.dt, 0) END,
           CASE WHEN tu_ss IS NOT NULL THEN coalesce(s.dt, 0) END,
           CASE WHEN tu_ss IS NOT NULL THEN coalesce(c.dt, 0) - coalesce(s.dt, 0) END,
           CASE WHEN s.dt > 0 THEN coalesce(c.dt, 0) / s.dt - 1 END
    FROM a
    FULL JOIN c ON c.nganh = a.nganh
    FULL JOIN s ON s.nganh = coalesce(a.nganh, c.nganh)
$$;


-- Pareto theo khách của khoảng — cùng cột với mart.tap_trung_khach (thứ tự xác
-- định: khoá phụ customer_code, ROWS).
CREATE FUNCTION mart.tap_trung_khoang(tu date, den date)
RETURNS TABLE (customer_code text, ten_khach text, dt numeric, thu_hang bigint,
               ty_trong numeric, luy_ke numeric)
LANGUAGE sql STABLE
AS $$
    WITH k AS (SELECT x.customer_code, x.dt FROM mart.khach_khoang(tu, den) x)
    SELECT k.customer_code,
           coalesce(nullif(c.customer_name, ''), '(chưa có tên)'),
           k.dt,
           row_number() OVER w,
           k.dt / nullif(sum(k.dt) OVER (), 0),
           (sum(k.dt) OVER w) / nullif(sum(k.dt) OVER (), 0)
    FROM k
    LEFT JOIN core.dim_customer c ON c.customer_code = k.customer_code AND c.is_current
    WINDOW w AS (ORDER BY k.dt DESC, k.customer_code
                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
$$;
