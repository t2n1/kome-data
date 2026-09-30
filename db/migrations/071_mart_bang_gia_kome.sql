-- 071 — Bảng giá KOME từng (mã, quy cách, bậc) + lần nạp trước (trang /bang-gia, chủ DN duyệt 2026-09-30).
-- ĐỊNH NGHĨA MỘT LẦN của "lần nạp mới nhất ≤ mốc" và luật hai cột thuế — trước đây chép ở 066 (mart.gia_kome_bang) VÀ ở
-- kome/san_pham_360.py::_bac_gia. Nay cả hai đọc view này (gia_kome_bang thay thân bằng CREATE OR REPLACE, cột y hệt).
--
-- "Trạng thái" của (mã, quy cách) tại một valid_from = các dòng có batch_id LỚN NHẤT ở valid_from đó: file sửa CÙNG ngày
-- được kome/loaders/price.py upsert (bậc còn lại đổi batch_id), bậc bị bỏ giữ batch_id cũ và phải biến mất. price.py bỏ
-- bậc 0/0 nên bậc hết hạn (vd 売価No.10) chỉ biến mất nhờ luật này.
-- Hiện hành = trạng thái ở valid_from lớn nhất ≤ mốc (040); lần trước = trạng thái ở valid_from lớn nhất NHỎ HƠN đó.
-- Dòng `hien_hanh = false` = bậc có ở lần trước mà lần này KHÔNG có (bị bỏ) — gia_chua_thue NULL.
-- Luật hai cột: chưa thuế nếu > 0 và KHÔNG mâu thuẫn (gồm thuế > 0 mà nhỏ hơn chưa thuế); không thì gồm thuế ÷ 1,08.
-- `doi` = đã đổi so với lần trước (giá khác, bậc mới, hoặc bậc bị bỏ) — chỉ khi (mã, quy cách) CÓ lần trước.
-- `duoi_gia_von` = giá chưa thuế < 単位原価 (unit_cost > 0).

CREATE VIEW mart.bang_gia_kome AS
WITH f AS (
    SELECT f.*, max(f.batch_id) OVER (PARTITION BY f.product_code, f.pack_code, f.valid_from) AS b_max
    FROM core.fact_price_list f
    WHERE f.valid_from <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date))
),
s AS (
    SELECT f.product_code, f.pack_code, f.price_level, f.valid_from, f.price_ex_tax, f.price_in_tax, f.unit_cost,
           CASE WHEN f.price_ex_tax > 0 AND NOT (f.price_in_tax > 0 AND f.price_in_tax < f.price_ex_tax)
                THEN f.price_ex_tax::numeric ELSE f.price_in_tax / 1.08 END                  AS gia_chua_thue,
           (f.price_ex_tax > 0 AND f.price_in_tax > 0 AND f.price_in_tax < f.price_ex_tax)    AS hai_cot_lech
    FROM f
    WHERE f.batch_id = f.b_max AND (f.price_ex_tax > 0 OR f.price_in_tax > 0)
),
d AS (
    SELECT x.product_code, x.pack_code, x.valid_from,
           row_number() OVER (PARTITION BY x.product_code, x.pack_code ORDER BY x.valid_from DESC) AS thu
    FROM (SELECT DISTINCT product_code, pack_code, valid_from FROM f WHERE batch_id = b_max) x
),
k AS (
    SELECT n.product_code, n.pack_code, n.valid_from AS tu_ngay, t.valid_from AS tu_ngay_truoc
    FROM d n LEFT JOIN d t ON t.product_code = n.product_code AND t.pack_code = n.pack_code AND t.thu = 2
    WHERE n.thu = 1
),
nay AS (SELECT s.* FROM s JOIN k ON k.product_code = s.product_code AND k.pack_code = s.pack_code AND s.valid_from = k.tu_ngay),
truoc AS (SELECT s.* FROM s JOIN k ON k.product_code = s.product_code AND k.pack_code = s.pack_code AND s.valid_from = k.tu_ngay_truoc),
lv AS (SELECT product_code, pack_code, price_level FROM nay UNION SELECT product_code, pack_code, price_level FROM truoc)
SELECT k.product_code, k.pack_code, lv.price_level,
       n.product_code IS NOT NULL                                              AS hien_hanh,
       k.tu_ngay, k.tu_ngay_truoc,
       n.price_ex_tax, n.price_in_tax, n.gia_chua_thue, coalesce(n.hai_cot_lech, false) AS hai_cot_lech,
       nullif(n.unit_cost, 0)                                                   AS gia_von,
       t.gia_chua_thue                                                          AS gia_truoc,
       (k.tu_ngay_truoc IS NOT NULL AND n.gia_chua_thue IS DISTINCT FROM t.gia_chua_thue) AS doi,
       coalesce(n.unit_cost > 0 AND n.gia_chua_thue < n.unit_cost, false)      AS duoi_gia_von
FROM k
JOIN lv ON lv.product_code = k.product_code AND lv.pack_code = k.pack_code
LEFT JOIN nay n ON n.product_code = lv.product_code AND n.pack_code = lv.pack_code AND n.price_level = lv.price_level
LEFT JOIN truoc t ON t.product_code = lv.product_code AND t.pack_code = lv.pack_code AND t.price_level = lv.price_level;

-- Thân mới, cột y hệt 066 (CREATE OR REPLACE giữ mọi view phụ thuộc: gia_doi_thu_hien_hanh, so_sanh_nhom…).
CREATE OR REPLACE VIEW mart.gia_kome_bang AS
WITH g AS (
    SELECT b.product_code, b.price_level, b.pack_code, b.gia_chua_thue, b.hai_cot_lech,
           CASE b.pack_code WHEN '02' THEN q.kg_02 WHEN '00' THEN q.kg_00 END AS kg
    FROM mart.bang_gia_kome b JOIN mart.quy_cach_kome q USING (product_code)
    WHERE b.hien_hanh
)
SELECT DISTINCT ON (product_code, price_level) product_code, price_level, pack_code, gia_chua_thue,
       gia_chua_thue / kg AS yen_kg, hai_cot_lech
FROM g WHERE kg > 0
ORDER BY product_code, price_level, (pack_code = '02') DESC;

GRANT SELECT ON mart.bang_gia_kome TO kome_app, kome_report, kome_ingest;
