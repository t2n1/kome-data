-- 054 — mart.khach_mat_hang (và hai view nó đứng trên) lọc được theo MỘT DANH SÁCH mã hàng.
--
-- Vì sao: `mart.sp_khach_nen_chao` (053) cần nhãn trang_thai_cap của mọi cặp (khách, mã CÙNG
-- NGÀNH). Đọc view `khach_mat_hang` với `product_code = ANY(...)` hay JOIN thì Postgres KHÔNG đẩy
-- vị từ qua `nhip_mat_hang` xuống cửa sổ LAG của `khoang_cach_mat_hang` — nó dựng lại cửa sổ trên
-- TOÀN BỘ bảng bán. 053 né bằng LATERAL `= mã` từng mã, nên chi phí nhân theo cỡ ngành: đo thật
-- 2026-09-27, mã HAL04 (26 mã cùng ngành) mất 8,7 s.
--
-- Cách làm — MỘT định nghĩa, không chép công thức: thân ba view chuyển NGUYÊN VĂN vào ba hàm
-- `…_cua(p_mas text[])` (LANGUAGE sql STABLE — Postgres gộp thẳng vào câu gọi), thêm đúng một vị từ
-- `(p_mas IS NULL OR product_code = ANY(p_mas))` ở chỗ đọc `mart.ban_den_moc` trong cùng. Ba view
-- giữ tên và cột, chỉ còn `SELECT * FROM …_cua(NULL)`: với hằng NULL, vị từ gập thành `true` lúc lập
-- kế hoạch, nên mọi chỗ đang đọc view (khách 360, /lien-he, san_pham_360…) chạy ĐÚNG kế hoạch cũ.
-- Lọc theo mã không đổi được cửa sổ LAG của một cặp (khách, mã) — phân vùng cửa sổ chứa mã — nên
-- kết quả của hàm với danh sách = đúng các dòng đó của view (có test canh:
-- tests/test_mart_sp360.py::test_khach_mat_hang_cua_BANG_view_loc_theo_ma).

CREATE OR REPLACE FUNCTION mart.khoang_cach_mat_hang_cua(p_mas text[])
RETURNS TABLE (customer_code text, product_code text, sales_date date, so_ngay_cach integer)
LANGUAGE sql STABLE AS $$
    -- Thân của mart.khoang_cach_mat_hang (040), + vị từ danh sách mã.
    SELECT customer_code, product_code, sales_date,
           sales_date - lag(sales_date) OVER (PARTITION BY customer_code, product_code
                                              ORDER BY sales_date) AS so_ngay_cach
    FROM (SELECT DISTINCT b.customer_code, b.product_code, b.sales_date
          FROM mart.ban_den_moc b
          WHERE p_mas IS NULL OR b.product_code = ANY(p_mas)) x
$$;

CREATE OR REPLACE FUNCTION mart.nhip_mat_hang_cua(p_mas text[])
RETURNS TABLE (customer_code text, product_code text, so_khoang bigint, nhip_ngay double precision)
LANGUAGE sql STABLE AS $$
    -- Thân của mart.nhip_mat_hang (020) — CÙNG công thức trung vị với mart.nhip_mua.
    SELECT customer_code, product_code,
           count(*)                                                 AS so_khoang,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY so_ngay_cach) AS nhip_ngay
    FROM mart.khoang_cach_mat_hang_cua(p_mas)
    WHERE so_ngay_cach IS NOT NULL
    GROUP BY customer_code, product_code
$$;

CREATE OR REPLACE FUNCTION mart.khach_mat_hang_cua(p_mas text[])
RETURNS TABLE (customer_code text, product_code text, ten_hang text, doanh_thu_thuan numeric,
               lai_gop numeric, so_luong numeric, so_lan bigint, lan_dau date, lan_cuoi date,
               nhip_ngay double precision, du_kien_lan_toi date, tre_ngay integer,
               trang_thai_cap text)
LANGUAGE sql STABLE AS $$
    -- Thân của mart.khach_mat_hang (050) NGUYÊN VĂN, + vị từ danh sách mã ở chỗ đọc ban_den_moc,
    -- và nhip_mat_hang -> nhip_mat_hang_cua(p_mas). Chú thích từng nhánh: xem 024/047–050.
    SELECT y.customer_code, y.product_code, y.ten_hang, y.doanh_thu_thuan,
           y.lai_gop, y.so_luong, y.so_lan, y.lan_dau, y.lan_cuoi, y.nhip_ngay,
           y.du_kien_lan_toi, y.tre_ngay,
           CASE
             WHEN coalesce(dh.da_ngung, false) THEN 'khong_goi'
             WHEN y.tre_ngay >= y.nhip_ngay THEN 'ngung'
             ELSE 'mua'
           END                                                AS trang_thai_cap
    FROM (
        SELECT x.customer_code, x.product_code, x.ten_hang, x.doanh_thu_thuan,
               x.lai_gop, x.so_luong, x.so_lan, x.lan_dau, x.lan_cuoi,
               x.nhip_ngay, x.du_kien_lan_toi,
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
                   CASE WHEN n.so_khoang >= 2 THEN n.nhip_ngay END AS nhip_ngay,
                   CASE WHEN n.so_khoang >= 2
                        THEN (max(f.sales_date) + n.nhip_ngay * interval '1 day')::date
                   END AS du_kien_lan_toi,
                   m.hom_nay AS hom_nay
            FROM mart.ban_den_moc f
            LEFT JOIN core.dim_product s ON s.product_code = f.product_code
            LEFT JOIN mart.nhip_mat_hang_cua(p_mas) n
                   ON n.customer_code = f.customer_code
                  AND n.product_code = f.product_code
            CROSS JOIN mart.moc_thoi_gian m
            WHERE (p_mas IS NULL OR f.product_code = ANY(p_mas))
              AND NOT mart.khong_phai_hang(f.product_code, s.kind_code, s.food_category_name)
              AND NOT EXISTS (SELECT 1 FROM mart.ma_ngung_ban_an a WHERE a.product_code = f.product_code)
            GROUP BY f.customer_code, f.product_code, s.product_name,
                     n.so_khoang, n.nhip_ngay, m.hom_nay
        ) x
    ) y
    LEFT JOIN mart.dau_hieu_khach dh ON dh.customer_code = y.customer_code
$$;

-- Ba view: giữ tên, giữ cột, một nguồn duy nhất là hàm.
CREATE OR REPLACE VIEW mart.khoang_cach_mat_hang AS
SELECT * FROM mart.khoang_cach_mat_hang_cua(NULL);

CREATE OR REPLACE VIEW mart.nhip_mat_hang AS
SELECT * FROM mart.nhip_mat_hang_cua(NULL);

CREATE OR REPLACE VIEW mart.khach_mat_hang AS
SELECT * FROM mart.khach_mat_hang_cua(NULL);

-- sp_khach_nen_chao (053): thay 26 vòng LATERAL bằng MỘT lượt mart.khach_mat_hang_cua(danh sách).
-- PL/pgSQL + EXECUTE format(%L), KHÔNG phải SQL thuần — có chủ ý: danh sách mã cùng ngành phải là
-- HẰNG trong câu lệnh lúc Postgres lập kế hoạch, thì nó mới dùng chỉ mục (product_code, sales_date).
-- Thuần SQL (danh sách là một cột LATERAL) hay `EXECUTE … USING $1` (tham số) thì lúc lập kế hoạch
-- danh sách chưa biết, Postgres quét cả bảng bán theo ngày rồi lọc — đo thật HAL04: 1–2 s cả hai
-- cách; nhúng hằng: ~0,3 s (trước 054: 8,7 s). %L trích dẫn an toàn (quote_literal) — giá trị là
-- mã hàng lấy từ core.dim_product, không phải chuỗi người dùng gõ, nhưng vẫn không nối chuỗi trần.
CREATE OR REPLACE FUNCTION mart.sp_khach_nen_chao(p_ma text)
RETURNS TABLE (customer_code text, ten text, nganh text, doanh_thu_nganh numeric,
               so_ma_nganh bigint, lan_cuoi date)
LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_nganh text;
    v_bo    boolean;
    v_mas   text[];
BEGIN
    -- Định nghĩa không đổi so với 053: khách đang mua đều (trang_thai_cap = 'mua', so BẰNG — 024)
    -- ≥ 1 mã CÙNG NGÀNH, chưa từng có dòng với mã này (≤ mốc); ※廃業※ mang 'khong_goi' nên tự rơi
    -- ra. Mã đích ※終売※ (kể cả còn tồn) / không phải hàng (mart.khong_phai_hang — phí, POSM) /
    -- chưa phân loại ngành -> rỗng. `lan_cuoi` = lần mua cuối MÃ CÙNG NGÀNH (không phải mã này).
    -- Xếp theo DT thuần ngành đó 12 tháng.
    SELECT mart.ten_nganh(d.food_category_name, d.product_code, d.kind_code),
           mart.la_ngung_ban(d.rank_code, d.product_name)
           OR mart.khong_phai_hang(d.product_code, d.kind_code, d.food_category_name)
           OR nullif(d.food_category_name, '') IS NULL
      INTO v_nganh, v_bo
      FROM core.dim_product d WHERE d.product_code = p_ma;
    IF v_nganh IS NULL OR v_bo THEN
        RETURN;
    END IF;
    SELECT array_agg(d.product_code) INTO v_mas
      FROM core.dim_product d
     WHERE d.product_code <> p_ma
       AND mart.ten_nganh(d.food_category_name, d.product_code, d.kind_code) = v_nganh;
    IF v_mas IS NULL THEN
        RETURN;
    END IF;
    RETURN QUERY EXECUTE format($q$
        WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
        -- `k` được tham chiếu hai lần (câu cuối + lọc ở `dt`) -> AS MATERIALIZED tường minh.
        k AS MATERIALIZED (
            SELECT h.customer_code, count(*) AS so_ma, max(h.lan_cuoi) AS lan_cuoi
              FROM mart.khach_mat_hang_cua(%1$L::text[]) h
             WHERE h.trang_thai_cap = 'mua'
             GROUP BY h.customer_code
        ),
        dt AS (
            SELECT f.customer_code, sum(f.amount - f.tax_amount)::numeric AS dt
              FROM mart.ban_den_moc f CROSS JOIN m
             WHERE f.product_code = ANY(%1$L::text[])
               AND f.sales_date > m.hom_nay - 365
               AND f.customer_code IN (SELECT customer_code FROM k)
             GROUP BY f.customer_code
        )
        SELECT k.customer_code, coalesce(nullif(c.customer_name, ''), k.customer_code),
               %3$L::text, coalesce(dt.dt, 0), k.so_ma, k.lan_cuoi
          FROM k
          LEFT JOIN dt ON dt.customer_code = k.customer_code
          LEFT JOIN core.dim_customer c ON c.customer_code = k.customer_code AND c.is_current
         WHERE NOT EXISTS (SELECT 1 FROM mart.ban_den_moc f
                            WHERE f.customer_code = k.customer_code AND f.product_code = %2$L)
         ORDER BY coalesce(dt.dt, 0) DESC, k.customer_code
    $q$, v_mas, p_ma, v_nganh);
END
$$;
