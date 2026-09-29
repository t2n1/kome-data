-- 066 — KOME: kg của MỘT đơn vị theo 荷姿 của OBC + bảng giá KOME (đặc tả giao diện mới §5.3, §6.3).
-- Đo 2026-09-29: 15 nhóm có giá KOME > 3× trung vị (xốt Barona ¥78,403/kg vs ¥845). Các mã đó KHÔNG có 荷姿 nào ở
-- 商品データ (pack1_code = '') và bán bằng '00' — một '00' là CẢ sản phẩm như tên ghi (80g × 20 × 4 = 6,4 kg), còn 060
-- coi '00' = một gói 80g. Có 荷姿１ thì '02' = pack1_base_qty × '00' (Ngũ vị hương 3g: 400 × 3g = 1,2 kg; 060 tách
-- tên "3g x 100 pack x 4 boxes" ra 0,3 kg). pack1_code NULL (chưa nạp lại 商品データ bản có cột) → giữ luật 060.
-- Tên dạng ba thừa số "a g x b x c" → kg_moi_thung = a × b × c (người sửa ở app.quy_cach_kome vẫn thắng).
-- CREATE OR REPLACE: cột cũ giữ nguyên thứ tự, kg_00 / kg_02 thêm ở CUỐI.

CREATE OR REPLACE VIEW mart.quy_cach_kome AS
WITH t AS (
    SELECT p.product_code, nullif(p.pack1_code, '') AS pack1, p.pack1_code = '' AS khong_hanh, p.pack1_base_qty,
           regexp_match(p.product_name, '(\d+(?:[.,]\d+)?)\s*(kg|gr|g)\s*[x×*]\s*(\d+)', 'i') AS m1,
           regexp_match(p.product_name, '(\d+(?:[.,]\d+)?)\s*kg\s*/\s*case', 'i')             AS m2,
           regexp_match(p.product_name, '(\d+(?:[.,]\d+)?)\s*(kg|gr|g)\s*[x×*]\s*(\d+)\s*[[:alpha:]]*\s*[x×*]\s*(\d+)', 'i') AS m3
    FROM core.dim_product p
),
q AS (
    SELECT t.*, o.product_code IS NOT NULL AS da_sua,
           coalesce(o.kg_moi_goi, CASE WHEN t.m1 IS NOT NULL THEN replace(t.m1[1], ',', '.')::numeric
                                       / CASE WHEN lower(t.m1[2]) = 'kg' THEN 1 ELSE 1000 END END) AS kg_moi_goi,
           coalesce(o.goi_moi_thung, t.m1[3]::numeric)                                            AS goi_moi_thung,
           coalesce(o.kg_moi_thung, replace(t.m2[1], ',', '.')::numeric,
                    CASE WHEN t.m3 IS NOT NULL THEN replace(t.m3[1], ',', '.')::numeric
                         / CASE WHEN lower(t.m3[2]) = 'kg' THEN 1 ELSE 1000 END
                         * t.m3[3]::numeric * t.m3[4]::numeric END)                                AS kg_moi_thung,
           o.kg_moi_thung IS NOT NULL                                                              AS thung_nguoi_sua
    FROM t LEFT JOIN app.quy_cach_kome o USING (product_code)
)
SELECT q.product_code, q.kg_moi_goi, q.goi_moi_thung, q.kg_moi_thung, q.da_sua,
       CASE WHEN q.khong_hanh THEN coalesce(q.kg_moi_thung, q.kg_moi_goi * q.goi_moi_thung)
            ELSE q.kg_moi_goi END                                                                 AS kg_00,
       CASE WHEN NOT q.thung_nguoi_sua AND q.pack1 = '02' AND q.pack1_base_qty > 0 AND q.kg_moi_goi IS NOT NULL
            THEN q.kg_moi_goi * q.pack1_base_qty
            ELSE coalesce(q.kg_moi_thung, q.kg_moi_goi * q.goi_moi_thung) END                     AS kg_02
FROM q;

CREATE OR REPLACE VIEW mart.gia_kome_kg AS
SELECT f.product_code,
       sum(f.amount - f.tax_amount)                                AS doanh_thu,
       sum(f.qty * k.kg)                                           AS kg_ban,
       sum(f.amount - f.tax_amount) / nullif(sum(f.qty * k.kg), 0) AS yen_kg
FROM mart.ban_den_moc f
CROSS JOIN mart.moc_thoi_gian m
JOIN mart.quy_cach_kome q ON q.product_code = f.product_code
CROSS JOIN LATERAL (SELECT CASE f.pack_code WHEN '02' THEN q.kg_02 WHEN '00' THEN q.kg_00 END AS kg) k
WHERE f.sales_date > m.hom_nay - 90 AND k.kg IS NOT NULL
GROUP BY f.product_code;

-- 売価No.10 = giá KHUYẾN MÃI của KOME (chủ DN 2026-09-29). ĐỊNH NGHĨA MỘT LẦN; kome/san_pham_360.py::NHAN_BAC chép nhãn.
CREATE FUNCTION mart.la_gia_km_kome(p_level text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$ SELECT p_level = '10' $$;

-- Bảng giá KOME quy về ¥/kg chưa thuế, bản mới nhất ≤ mốc (040) mỗi (mã, bậc, quy cách). Luật hai cột: chưa thuế nếu > 0
-- và KHÔNG mâu thuẫn (gồm thuế > 0 mà nhỏ hơn chưa thuế); không thì gồm thuế ÷ 1,08. Mỗi (mã, bậc) một dòng: ưu tiên
-- quy cách '02' khi biết kg, không thì '00'.
CREATE VIEW mart.gia_kome_bang AS
WITH m AS (
    SELECT DISTINCT ON (product_code, pack_code, price_level) product_code, pack_code, price_level, price_ex_tax, price_in_tax
    FROM core.fact_price_list
    WHERE valid_from <= coalesce(mart.moc_lui(), 'infinity'::date) AND (price_ex_tax > 0 OR price_in_tax > 0)
    ORDER BY product_code, pack_code, price_level, valid_from DESC
),
g AS (
    SELECT m.product_code, m.price_level, m.pack_code,
           CASE WHEN m.price_ex_tax > 0 AND NOT (m.price_in_tax > 0 AND m.price_in_tax < m.price_ex_tax)
                THEN m.price_ex_tax::numeric ELSE m.price_in_tax / 1.08 END                  AS gia_chua_thue,
           (m.price_ex_tax > 0 AND m.price_in_tax > 0 AND m.price_in_tax < m.price_ex_tax)    AS hai_cot_lech,
           CASE m.pack_code WHEN '02' THEN q.kg_02 WHEN '00' THEN q.kg_00 END                 AS kg
    FROM m JOIN mart.quy_cach_kome q USING (product_code)
)
SELECT DISTINCT ON (product_code, price_level) product_code, price_level, pack_code, gia_chua_thue,
       gia_chua_thue / kg AS yen_kg, hai_cot_lech
FROM g WHERE kg > 0
ORDER BY product_code, price_level, (pack_code = '02') DESC;

CREATE FUNCTION mart.gia_kome_chuan(p_ma text) RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT yen_kg FROM mart.gia_kome_bang WHERE product_code = p_ma AND price_level = 'std'
$$;

GRANT SELECT ON mart.quy_cach_kome, mart.gia_kome_kg, mart.gia_kome_bang TO kome_app, kome_report, kome_ingest;
GRANT EXECUTE ON FUNCTION mart.la_gia_km_kome(text), mart.gia_kome_chuan(text) TO kome_app, kome_report, kome_ingest;
