-- 057 — Sản phẩm 360: 26 tuần + khách mới/quay lại có THAM SỐ ngày cuối cửa sổ
-- (đặc tả 2026-09-28-ky-so-sanh-toan-web-design.md, đợt 3).
--
-- Kỳ so của khoảng xem cần CÙNG công thức trên một cửa sổ lùi (26 tuần kết thúc ở
-- tuần chứa `p_den`; 12 tháng kết thúc ở tháng chứa `p_den`). Không chép công thức
-- lần hai: thân định nghĩa chuyển vào hai hàm `…_den(p_ma, p_den)`, và hai hàm cũ
-- (051/052) nay chỉ gọi chúng với mốc (`mart.moc_thoi_gian.hom_nay`) — cùng nếp 054.
-- Chữ ký `RETURNS TABLE` của hai hàm cũ không đổi (CREATE OR REPLACE được).
--
-- "Mới" vẫn = tháng của lần ĐẦU khách mua mã này tính trên MỌI dữ liệu ≤ mốc (không
-- ≤ p_den): cửa sổ lùi chỉ dời các tháng được ĐẾM, không đổi định nghĩa "lần đầu".

CREATE OR REPLACE FUNCTION mart.sp_theo_tuan_den(p_ma text, p_den date)
RETURNS TABLE (tuan date, so_luong numeric, doanh_thu numeric)
LANGUAGE sql STABLE AS $$
    -- 26 tuần ISO (thứ Hai) kết thúc ở tuần chứa p_den; tuần không bán = 0.
    WITH m AS (SELECT date_trunc('week', p_den)::date AS t),
    g AS (SELECT (m.t - 7 * i) AS tuan FROM m, generate_series(0, 25) AS i),
    b AS (
        SELECT date_trunc('week', f.sales_date)::date AS tuan,
               sum(f.qty)::numeric AS sl, sum(f.amount - f.tax_amount)::numeric AS dt
          FROM mart.ban_den_moc f CROSS JOIN m
         WHERE f.product_code = p_ma AND f.sales_date >= m.t - 7 * 25 AND f.sales_date < m.t + 7
         GROUP BY 1
    )
    SELECT g.tuan, coalesce(b.sl, 0), coalesce(b.dt, 0)
      FROM g LEFT JOIN b USING (tuan)
     ORDER BY g.tuan
$$;

CREATE OR REPLACE FUNCTION mart.sp_theo_tuan(p_ma text)
RETURNS TABLE (tuan date, so_luong numeric, doanh_thu numeric)
LANGUAGE sql STABLE AS $$
    SELECT * FROM mart.sp_theo_tuan_den(p_ma, (SELECT hom_nay FROM mart.moc_thoi_gian))
$$;

CREATE OR REPLACE FUNCTION mart.sp_khach_moi_thang_den(p_ma text, p_den date)
RETURNS TABLE (thang text, khach_moi bigint, khach_quay_lai bigint)
LANGUAGE sql STABLE AS $$
    -- "Tháng có mua" = (khách, tháng) có DT thuần > 0 (nếp 036). "Mới" = tháng đó là tháng
    -- của lần ĐẦU khách mua mã này (tính trên mọi dữ liệu ≤ mốc). 12 tháng kết thúc ở
    -- tháng chứa p_den, tháng trống = 0.
    WITH ct AS (
        SELECT f.customer_code, to_char(f.sales_date, 'YYYY-MM') AS thang
          FROM mart.ban_den_moc f
         WHERE f.product_code = p_ma
         GROUP BY 1, 2
        HAVING sum(f.amount - f.tax_amount) > 0
    ),
    dau AS (SELECT customer_code, min(thang) AS thang_dau FROM ct GROUP BY 1),
    g AS (
        SELECT to_char(x, 'YYYY-MM') AS thang
          FROM generate_series(date_trunc('month', p_den) - interval '11 months',
                               date_trunc('month', p_den), interval '1 month') AS x
    )
    SELECT g.thang,
           count(ct.customer_code) FILTER (WHERE dau.thang_dau = g.thang),
           count(ct.customer_code) FILTER (WHERE dau.thang_dau < g.thang)
      FROM g
      LEFT JOIN ct ON ct.thang = g.thang
      LEFT JOIN dau ON dau.customer_code = ct.customer_code
     GROUP BY g.thang
     ORDER BY g.thang
$$;

CREATE OR REPLACE FUNCTION mart.sp_khach_moi_thang(p_ma text)
RETURNS TABLE (thang text, khach_moi bigint, khach_quay_lai bigint)
LANGUAGE sql STABLE AS $$
    SELECT * FROM mart.sp_khach_moi_thang_den(p_ma, (SELECT hom_nay FROM mart.moc_thoi_gian))
$$;
