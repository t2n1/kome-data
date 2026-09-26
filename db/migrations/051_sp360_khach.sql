-- 051 — Sản phẩm 360, nhóm "Ai mua & ở đâu" (đặc tả 2026-09-26-san-pham-360-trang-rieng-design.md §4).
-- Mọi hàm đọc mart.ban_den_moc (bỏ mã nội bộ 044, quay về theo mốc 040). Cửa sổ 12 tháng =
-- sales_date > hom_nay - 365 (cùng cửa sổ mart.hang_doanh_thu). DT thuần = amount - tax_amount.

CREATE OR REPLACE FUNCTION mart.sp_tap_trung_khach(p_ma text)
RETURNS TABLE (customer_code text, ten text, doanh_thu numeric, ty_trong numeric, luy_ke numeric)
LANGUAGE sql STABLE AS $$
    -- Gộp theo KHÁCH (không theo khách × người phụ trách) — nếp mart.tap_trung_khach.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    k AS (
        SELECT f.customer_code, sum(f.amount - f.tax_amount)::numeric AS dt
          FROM mart.ban_den_moc f CROSS JOIN m
         WHERE f.product_code = p_ma AND f.sales_date > m.hom_nay - 365
         GROUP BY f.customer_code
    ),
    t AS (SELECT sum(dt) AS tong FROM k)
    SELECT k.customer_code,
           coalesce(nullif(c.customer_name, ''), k.customer_code),
           k.dt,
           k.dt / nullif(t.tong, 0),
           sum(k.dt) OVER (ORDER BY k.dt DESC, k.customer_code) / nullif(t.tong, 0)
      FROM k CROSS JOIN t
      LEFT JOIN core.dim_customer c ON c.customer_code = k.customer_code AND c.is_current
     ORDER BY k.dt DESC, k.customer_code
$$;

CREATE OR REPLACE FUNCTION mart.sp_theo_tinh(p_ma text)
RETURNS TABLE (ma_jis text, ten text, ten_ngan text, vung text, hang_luoi int, cot_luoi int,
               doanh_thu numeric, so_khach bigint)
LANGUAGE sql STABLE AS $$
    -- LEFT JOIN TỪ dim_prefecture: đủ 47 ô kể cả tỉnh không ai mua (bất biến /ban-do).
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    k AS (
        SELECT c.prefecture, sum(f.amount - f.tax_amount)::numeric AS dt,
               count(DISTINCT f.customer_code) AS n
          FROM mart.ban_den_moc f CROSS JOIN m
          LEFT JOIN core.dim_customer c ON c.customer_code = f.customer_code AND c.is_current
         WHERE f.product_code = p_ma AND f.sales_date > m.hom_nay - 365
         GROUP BY c.prefecture
    )
    SELECT p.ma_jis, p.ten, p.ten_ngan, p.vung, p.hang_luoi, p.cot_luoi,
           coalesce(k.dt, 0), coalesce(k.n, 0)
      FROM core.dim_prefecture p
      LEFT JOIN k ON k.prefecture = p.ten
     ORDER BY p.ma_jis
$$;

CREATE OR REPLACE FUNCTION mart.sp_theo_nguoi(p_ma text)
RETURNS TABLE (salesperson_code text, ten text, doanh_thu numeric, lai_gop numeric, so_khach bigint)
LANGUAGE sql STABLE AS $$
    -- Xuất phát từ DÒNG BÁN, LEFT JOIN tên: mã ngoài dim_salesperson (vd '0000') vẫn có dòng.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian)
    SELECT coalesce(f.salesperson_code, ''), s.ten,
           sum(f.amount - f.tax_amount)::numeric, sum(f.gross_profit)::numeric,
           count(DISTINCT f.customer_code)
      FROM mart.ban_den_moc f CROSS JOIN m
      LEFT JOIN core.dim_salesperson s ON s.salesperson_code = f.salesperson_code
     WHERE f.product_code = p_ma AND f.sales_date > m.hom_nay - 365
     GROUP BY coalesce(f.salesperson_code, ''), s.ten
     ORDER BY 3 DESC, 1
$$;

CREATE OR REPLACE FUNCTION mart.sp_khach_moi_thang(p_ma text)
RETURNS TABLE (thang text, khach_moi bigint, khach_quay_lai bigint)
LANGUAGE sql STABLE AS $$
    -- "Tháng có mua" = (khách, tháng) có DT thuần > 0 (nếp 036). "Mới" = tháng đó là tháng
    -- của lần ĐẦU khách mua mã này (tính trên mọi dữ liệu ≤ mốc). 12 tháng, tháng trống = 0.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    ct AS (
        SELECT f.customer_code, to_char(f.sales_date, 'YYYY-MM') AS thang
          FROM mart.ban_den_moc f
         WHERE f.product_code = p_ma
         GROUP BY 1, 2
        HAVING sum(f.amount - f.tax_amount) > 0
    ),
    dau AS (SELECT customer_code, min(thang) AS thang_dau FROM ct GROUP BY 1),
    g AS (
        SELECT to_char(x, 'YYYY-MM') AS thang
          FROM m, generate_series(date_trunc('month', m.hom_nay) - interval '11 months',
                                  date_trunc('month', m.hom_nay), interval '1 month') AS x
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
