-- 052 — Sản phẩm 360, nhóm "Thời gian" và "Giá & lãi" (đặc tả §4). Đọc mart.ban_den_moc.

CREATE OR REPLACE FUNCTION mart.sp_theo_tuan(p_ma text)
RETURNS TABLE (tuan date, so_luong numeric, doanh_thu numeric)
LANGUAGE sql STABLE AS $$
    -- 26 tuần ISO (thứ Hai) kết thúc ở tuần chứa mốc; tuần không bán = 0.
    WITH m AS (SELECT date_trunc('week', hom_nay)::date AS t FROM mart.moc_thoi_gian),
    g AS (SELECT (m.t - 7 * i) AS tuan FROM m, generate_series(0, 25) AS i),
    b AS (
        SELECT date_trunc('week', f.sales_date)::date AS tuan,
               sum(f.qty)::numeric AS sl, sum(f.amount - f.tax_amount)::numeric AS dt
          FROM mart.ban_den_moc f CROSS JOIN m
         WHERE f.product_code = p_ma AND f.sales_date >= m.t - 7 * 25
         GROUP BY 1
    )
    SELECT g.tuan, coalesce(b.sl, 0), coalesce(b.dt, 0)
      FROM g LEFT JOIN b USING (tuan)
     ORDER BY g.tuan
$$;

CREATE OR REPLACE FUNCTION mart.sp_co_don(p_ma text)
RETURNS TABLE (pack_code text, nhom text, thu_tu int, so_dong bigint, so_luong numeric)
LANGUAGE sql STABLE AS $$
    -- Phân bố SL mỗi dòng bán theo quy cách, 12 tháng. Dòng âm (赤伝) KHÔNG lọc: nhóm 'tra_lai'.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    d AS (
        SELECT f.pack_code, f.qty,
               CASE WHEN f.qty < 0 THEN 'tra_lai' WHEN f.qty = 0 THEN 'khong_sl'
                    WHEN f.qty <= 1 THEN '1' WHEN f.qty <= 2 THEN '2'
                    WHEN f.qty <= 5 THEN '3–5' WHEN f.qty <= 10 THEN '6–10' ELSE '>10' END AS nhom,
               CASE WHEN f.qty < 0 THEN 7 WHEN f.qty = 0 THEN 6
                    WHEN f.qty <= 1 THEN 1 WHEN f.qty <= 2 THEN 2
                    WHEN f.qty <= 5 THEN 3 WHEN f.qty <= 10 THEN 4 ELSE 5 END AS thu_tu
          FROM mart.ban_den_moc f CROSS JOIN m
         WHERE f.product_code = p_ma AND f.sales_date > m.hom_nay - 365
    )
    SELECT pack_code, nhom, thu_tu, count(*), sum(qty)::numeric
      FROM d GROUP BY pack_code, nhom, thu_tu
     ORDER BY pack_code, thu_tu
$$;

CREATE OR REPLACE FUNCTION mart.sp_don_gia_thang(p_ma text)
RETURNS TABLE (thang text, pack_code text, so_luong numeric, doanh_thu numeric, don_gia numeric)
LANGUAGE sql STABLE AS $$
    -- Đơn giá thực = Σ DT thuần / Σ qty theo (tháng, quy cách) — TỶ SỐ CÁC TỔNG, không
    -- trung bình unit_price. Σ qty ≤ 0 (tháng toàn trả lại) -> NULL. 12 tháng lịch tới mốc.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian)
    SELECT to_char(f.sales_date, 'YYYY-MM'), f.pack_code,
           sum(f.qty)::numeric, sum(f.amount - f.tax_amount)::numeric,
           CASE WHEN sum(f.qty) > 0 THEN sum(f.amount - f.tax_amount)::numeric / sum(f.qty) END
      FROM mart.ban_den_moc f CROSS JOIN m
     WHERE f.product_code = p_ma
       AND f.sales_date >= (date_trunc('month', m.hom_nay) - interval '11 months')::date
     GROUP BY 1, 2
     ORDER BY 1, 2
$$;

CREATE OR REPLACE FUNCTION mart.sp_khach_gia(p_ma text)
RETURNS TABLE (customer_code text, ten text, pack_code text, so_lan bigint, so_luong numeric,
               doanh_thu numeric, lai_gop numeric, don_gia numeric, bien numeric)
LANGUAGE sql STABLE AS $$
    -- Theo khách, 12 tháng. Chỉ khách DT thuần > 0 VÀ ≥ 2 ngày mua (tránh mẫu số tí hon do
    -- 赤伝 — bài học 021). Đơn giá tính trên quy cách phổ biến nhất của mã (nhiều dòng nhất),
    -- biên = Σ lãi gộp / Σ DT thuần. Cả hai là tỷ số các tổng.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    f AS MATERIALIZED (
        SELECT b.customer_code, b.sales_date, b.pack_code, b.qty,
               b.amount - b.tax_amount AS dt, b.gross_profit
          FROM mart.ban_den_moc b CROSS JOIN m
         WHERE b.product_code = p_ma AND b.sales_date > m.hom_nay - 365
    ),
    q AS (SELECT f.pack_code FROM f GROUP BY f.pack_code ORDER BY count(*) DESC, f.pack_code LIMIT 1),
    k AS (
        SELECT f.customer_code,
               count(DISTINCT f.sales_date) AS so_lan,
               sum(f.dt)::numeric AS dt, sum(f.gross_profit)::numeric AS lg,
               sum(f.qty) FILTER (WHERE f.pack_code = (SELECT pack_code FROM q))::numeric AS sl_q,
               sum(f.dt)  FILTER (WHERE f.pack_code = (SELECT pack_code FROM q))::numeric AS dt_q
          FROM f GROUP BY f.customer_code
    )
    SELECT k.customer_code, coalesce(nullif(c.customer_name, ''), k.customer_code),
           (SELECT pack_code FROM q), k.so_lan, k.sl_q, k.dt, k.lg,
           CASE WHEN k.sl_q > 0 THEN k.dt_q / k.sl_q END,
           k.lg / k.dt
      FROM k
      LEFT JOIN core.dim_customer c ON c.customer_code = k.customer_code AND c.is_current
     WHERE k.dt > 0 AND k.so_lan >= 2
     ORDER BY k.lg / k.dt, k.customer_code
$$;
