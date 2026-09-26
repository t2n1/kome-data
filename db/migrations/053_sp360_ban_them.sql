-- 053 — Sản phẩm 360, nhóm "Bán thêm" (đặc tả §4). Đọc mart.ban_den_moc / mart.khach_mat_hang.
--
-- mart.ban_den_moc được tham chiếu HAI LẦN trong sp_mua_kem (CTE p và CTE k) mà KHÔNG bọc
-- MATERIALIZED: nó là một view MỎNG, chỉ lọc theo mốc trên một bảng ĐÃ CÓ CHỈ MỤC
-- (core.fact_sales_line) — Postgres NỐI TRỰC TIẾP (inline) view đó vào từng câu tham chiếu rồi
-- dùng chỉ mục riêng cho vị từ của lần tham chiếu đó (product_code = p_ma ở CTE p,
-- slip_no IN (...) ở CTE k). Bọc AS MATERIALIZED ở đây sẽ ép Postgres SAO CHÉP TOÀN BỘ kết quả
-- lọc-theo-mốc của cả bảng bán hàng vào bộ nhớ trước khi lọc tiếp — đắt hơn, không rẻ hơn. Bất
-- biến CTE-trùng (ghi ở CLAUDE.md) áp cho VIEW NẶNG bị tính lại nhiều lần (vd. san_pham_360); nó
-- không áp cho một view mỏng như ban_den_moc.
--
-- sp_khach_nen_chao.lan_cuoi: đây là lần mua GẦN NHẤT của khách với BẤT KỲ mã nào CÙNG NGÀNH với
-- p_ma (max(h.lan_cuoi) qua mọi mã trong CTE cung), KHÔNG PHẢI lần mua p_ma — khách trong danh
-- sách này chưa từng mua p_ma (lọc ở WHERE NOT EXISTS cuối câu), nên "lần mua p_ma gần nhất" vô
-- nghĩa với chính họ.

CREATE OR REPLACE FUNCTION mart.sp_mua_kem(p_ma text)
RETURNS TABLE (product_code text, ten_hang text, so_phieu bigint, ty_le numeric, tong_phieu bigint)
LANGUAGE sql STABLE AS $$
    -- Trong các phiếu (slip_no) 12 tháng có dòng MUA (qty > 0) mã này: mỗi mã khác có dòng mua
    -- trên bao nhiêu phiếu đó. Bỏ phí / POSM (khong_phai_hang, 048/049) và mã ※終売※ hết tồn (050).
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    p AS MATERIALIZED (
        SELECT DISTINCT f.slip_no
          FROM mart.ban_den_moc f CROSS JOIN m
         WHERE f.product_code = p_ma AND f.qty > 0 AND f.sales_date > m.hom_nay - 365
    ),
    t AS (SELECT count(*) AS n FROM p),
    k AS (
        SELECT f.product_code, count(DISTINCT f.slip_no) AS so_phieu
          FROM mart.ban_den_moc f JOIN p ON p.slip_no = f.slip_no
         WHERE f.product_code <> p_ma AND f.qty > 0
         GROUP BY f.product_code
    )
    SELECT k.product_code, coalesce(nullif(d.product_name, ''), k.product_code),
           k.so_phieu, k.so_phieu::numeric / nullif(t.n, 0), t.n
      FROM k CROSS JOIN t
      LEFT JOIN core.dim_product d ON d.product_code = k.product_code
     WHERE NOT mart.khong_phai_hang(k.product_code, d.kind_code, d.food_category_name)
       AND NOT EXISTS (SELECT 1 FROM mart.ma_ngung_ban_an a WHERE a.product_code = k.product_code)
     ORDER BY k.so_phieu DESC, k.product_code
     LIMIT 15
$$;

CREATE OR REPLACE FUNCTION mart.sp_khach_nen_chao(p_ma text)
RETURNS TABLE (customer_code text, ten text, nganh text, doanh_thu_nganh numeric,
               so_ma_nganh bigint, lan_cuoi date)
LANGUAGE sql STABLE AS $$
    -- Khách đang mua đều (trang_thai_cap = 'mua', so BẰNG — 024) ≥ 1 mã CÙNG NGÀNH, chưa từng có
    -- dòng với mã này (≤ mốc). ※廃業※ mang 'khong_goi' nên tự rơi ra. Mã ※終売※ (kể cả còn tồn),
    -- ngành chưa phân loại / phí / POSM -> rỗng. Xếp theo DT thuần ngành đó 12 tháng.
    -- LATERAL `= mã` cho khach_mat_hang: `= ANY`/JOIN không đẩy vị từ qua nhip_mat_hang (đo thật ở
    -- /lien-he: 2 s -> 0,1 s).
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    sp AS (
        SELECT mart.ten_nganh(d.food_category_name, d.product_code, d.kind_code) AS nganh,
               mart.la_ngung_ban(d.rank_code, d.product_name) AS ngung
          FROM core.dim_product d WHERE d.product_code = p_ma
    ),
    cung AS (
        SELECT d.product_code
          FROM core.dim_product d CROSS JOIN sp
         WHERE d.product_code <> p_ma
           AND mart.ten_nganh(d.food_category_name, d.product_code, d.kind_code) = sp.nganh
           AND NOT sp.ngung
           AND sp.nganh NOT IN ('(chưa phân loại)', 'Phí & điều chỉnh', 'Hàng tặng (POSM)')
    ),
    k AS (
        SELECT h.customer_code, count(*) AS so_ma, max(h.lan_cuoi) AS lan_cuoi
          FROM cung
          CROSS JOIN LATERAL (
              SELECT x.customer_code, x.lan_cuoi FROM mart.khach_mat_hang x
               WHERE x.product_code = cung.product_code AND x.trang_thai_cap = 'mua') h
         GROUP BY h.customer_code
    ),
    dt AS (
        SELECT f.customer_code, sum(f.amount - f.tax_amount)::numeric AS dt
          FROM mart.ban_den_moc f CROSS JOIN m
          JOIN cung ON cung.product_code = f.product_code
         WHERE f.sales_date > m.hom_nay - 365
           AND f.customer_code IN (SELECT customer_code FROM k)
         GROUP BY f.customer_code
    )
    SELECT k.customer_code, coalesce(nullif(c.customer_name, ''), k.customer_code),
           sp.nganh, coalesce(dt.dt, 0), k.so_ma, k.lan_cuoi
      FROM k CROSS JOIN sp
      LEFT JOIN dt ON dt.customer_code = k.customer_code
      LEFT JOIN core.dim_customer c ON c.customer_code = k.customer_code AND c.is_current
     WHERE NOT EXISTS (SELECT 1 FROM mart.ban_den_moc f
                        WHERE f.customer_code = k.customer_code AND f.product_code = p_ma)
     ORDER BY coalesce(dt.dt, 0) DESC, k.customer_code
$$;
