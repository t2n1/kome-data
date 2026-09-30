-- Migration lấy khoá AccessExclusive trên app.nguoi_dung và ~20 view của mart; không có hạn chờ thì nó có thể xếp hàng sau một
-- truy vấn đọc dài và kéo cả trang web đứng theo. LOCAL = chỉ trong giao dịch này, không bao giờ lan qua Supavisor.
SET LOCAL lock_timeout = '10s';

-- 072 — Bảng dữ liệu sửa trực tiếp (Kho dữ liệu › Bảng dữ liệu). Đặc tả 2026-09-30-bang-du-lieu-sua-design.md.
-- core VẪN chỉ đọc với web: bản sửa ở sổ CHỈ THÊM app.sua_du_lieu; mọi chỉ số đọc GIÁ TRỊ HIỆU LỰC qua mart.dim_customer,
-- mart.dim_product, mart.bang_gia_kome, mart.ton_hien_tai. Luật (chủ DN chốt 2026-09-30): OBC vẫn ghi đúng giá trị lúc sửa
-- → bản sửa thắng; OBC ghi khác (người ta đã sửa trong OBC) → OBC thắng. Viết MỘT lần: mart.ap_sua / mart.lech_obc.

-- Ngày OBC dạng 'YYYY年M月D日' mà là NGÀY CÓ THẬT. Regex của mart.ton_hien_tai cho '2027年02月30日' / '2027年13月10日' lọt
-- qua rồi to_date nổ — dùng ở CHECK của app.sua_du_lieu bên dưới.
CREATE FUNCTION mart.la_ngay_obc(t text) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE
AS $$
DECLARE m text[];
BEGIN
    m := regexp_match(t, '^([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日$');
    IF m IS NULL THEN RETURN false; END IF;
    PERFORM make_date(m[1]::int, m[2]::int, m[3]::int);
    RETURN true;
EXCEPTION WHEN others THEN
    RETURN false;
END
$$;
GRANT EXECUTE ON FUNCTION mart.la_ngay_obc(text) TO kome_app, kome_report, kome_ingest;

CREATE TABLE app.sua_du_lieu (
    id            bigserial PRIMARY KEY,
    bang          text NOT NULL CHECK (bang IN ('khach', 'san_pham', 'gia', 'ton')),
    khoa          text NOT NULL CHECK (khoa <> ''),
    cot           text NOT NULL,
    gia_tri       text,
    gia_tri_obc   text,
    gia_tri_truoc text,
    bo            boolean NOT NULL DEFAULT false,
    nguoi_dung_id bigint REFERENCES app.nguoi_dung,
    luc           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT sua_du_lieu_cot_check CHECK (
        (bang = 'khach' AND cot IN ('customer_name', 'branch_name', 'rank_code', 'salesperson_code', 'closing_day_code',
                                    'postcode', 'prefecture', 'city', 'address', 'building', 'phone', 'transfer_account'))
     OR (bang = 'san_pham' AND cot IN ('product_name', 'name_ja', 'kind_code', 'food_category_code', 'rank_code',
                                       'compete_code', 'barcode', 'unit', 'case_qty', 'shelf_code', 'introduced_on',
                                       'pack1_code', 'pack1_base_qty'))
     OR (bang = 'gia' AND cot = 'gia_chua_thue')
     OR (bang = 'ton' AND cot IN ('stock_qty', 'best_before'))),
    -- Giá trị phải ép được sang kiểu cột đích của view hiệu lực (::numeric(14,4), ::numeric, to_date). kome_app INSERT thẳng
    -- được và sổ chỉ thêm, nên chặn ở CSDL chứ không chỉ ở Python: một dòng hỏng là mọi view phía trên nổ vĩnh viễn.
    -- Không nhận số âm, 'NaN', 'Infinity', số mũ; giá phải > 0; hạn phải là ngày có thật.
    CONSTRAINT sua_du_lieu_gia_tri_check CHECK (bo OR CASE
        WHEN cot IN ('stock_qty', 'case_qty', 'pack1_base_qty')
            THEN gia_tri IS NOT NULL AND gia_tri ~ '^[0-9]{1,10}(\.[0-9]{1,4})?$'
        WHEN cot = 'gia_chua_thue'
            THEN gia_tri IS NOT NULL AND gia_tri ~ '^[0-9]{1,12}(\.[0-9]{1,20})?$' AND gia_tri !~ '^0+(\.0+)?$'
        WHEN cot = 'best_before'
            THEN gia_tri IS NULL OR gia_tri = '' OR btrim(gia_tri, ' 　') = '賞味期限なし' OR mart.la_ngay_obc(gia_tri)
        ELSE true END)
);
-- Supabase SQL Editor tự bật RLS (không policy) trên bảng mới — xem lý do ở 061; chạy qua db/migrate.py thì vô hại.
ALTER TABLE app.sua_du_lieu DISABLE ROW LEVEL SECURITY;
CREATE INDEX sua_du_lieu_o ON app.sua_du_lieu (bang, khoa, cot, id DESC);
GRANT SELECT, INSERT ON app.sua_du_lieu TO kome_app;
GRANT USAGE ON SEQUENCE app.sua_du_lieu_id_seq TO kome_app;
REVOKE UPDATE, DELETE ON app.sua_du_lieu FROM kome_app;
GRANT SELECT ON app.sua_du_lieu TO kome_report, kome_ingest;

-- Dòng MỚI NHẤT của từng ô; bo = true nghĩa là không còn bản sửa (về OBC).
CREATE VIEW mart.sua_moi_nhat AS
SELECT DISTINCT ON (bang, khoa, cot) id, bang, khoa, cot, gia_tri, gia_tri_obc, bo, nguoi_dung_id, luc
FROM app.sua_du_lieu
ORDER BY bang, khoa, cot, id DESC;

CREATE VIEW mart.sua_theo_khoa AS
SELECT bang, khoa, jsonb_object_agg(cot, jsonb_build_array(gia_tri, gia_tri_obc)) AS j
FROM mart.sua_moi_nhat WHERE NOT bo
GROUP BY bang, khoa;

-- LUẬT HIỆU LỰC — ĐỊNH NGHĨA DUY NHẤT. obc = giá trị OBC hiện tại (::text của cột nguồn), j = mart.sua_theo_khoa.j.
CREATE FUNCTION mart.ap_sua(obc text, j jsonb, cot text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT CASE WHEN j ? cot AND (j -> cot ->> 1) IS NOT DISTINCT FROM obc THEN j -> cot ->> 0 ELSE obc END $$;

CREATE FUNCTION mart.lech_obc(obc text, j jsonb, cot text) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT coalesce(j ? cot AND (j -> cot ->> 1) IS NOT DISTINCT FROM obc, false) $$;

-- Danh mục khách hiệu lực: CÙNG cột / kiểu / thứ tự với core.dim_customer, mọi phiên bản SCD2; bản sửa chỉ áp lên
-- dòng is_current (không view nào đọc bản cũ). Cột cặp mã–tên: tên lấy theo MÃ hiệu lực khi mã bị sửa.
CREATE VIEW mart.dim_customer AS
WITH x AS (
    SELECT c.*, s.j
    FROM core.dim_customer c
    LEFT JOIN mart.sua_theo_khoa s ON c.is_current AND s.bang = 'khach' AND s.khoa = c.customer_code
)
SELECT x.customer_sk, x.customer_code, x.valid_from, x.valid_to, x.is_current,
       mart.ap_sua(x.customer_name, x.j, 'customer_name')       AS customer_name,
       mart.ap_sua(x.branch_name, x.j, 'branch_name')           AS branch_name,
       mart.ap_sua(x.rank_code, x.j, 'rank_code')               AS rank_code,
       x.category_code, x.order_app_code,
       mart.ap_sua(x.salesperson_code, x.j, 'salesperson_code') AS salesperson_code,
       x.price_level_code,
       mart.ap_sua(x.closing_day_code, x.j, 'closing_day_code') AS closing_day_code,
       x.billing_customer_code,
       mart.ap_sua(x.postcode, x.j, 'postcode')                 AS postcode,
       mart.ap_sua(x.prefecture, x.j, 'prefecture')             AS prefecture,
       mart.ap_sua(x.city, x.j, 'city')                         AS city,
       mart.ap_sua(x.address, x.j, 'address')                   AS address,
       mart.ap_sua(x.phone, x.j, 'phone')                       AS phone,
       x.invoice_reg_no, x.spot_flag, x.batch_id,
       mart.ap_sua(x.building, x.j, 'building')                 AS building,
       CASE WHEN mart.lech_obc(x.rank_code, x.j, 'rank_code')
            THEN (SELECT t.rank_name FROM core.dim_customer t
                  WHERE t.is_current AND t.rank_code = mart.ap_sua(x.rank_code, x.j, 'rank_code')
                    AND coalesce(t.rank_name, '') <> '' ORDER BY t.rank_name LIMIT 1)
            ELSE x.rank_name END                                  AS rank_name,
       CASE WHEN mart.lech_obc(x.salesperson_code, x.j, 'salesperson_code')
            THEN (SELECT t.ten FROM core.dim_salesperson t
                  WHERE t.salesperson_code = mart.ap_sua(x.salesperson_code, x.j, 'salesperson_code'))
            ELSE x.salesperson_name END                           AS salesperson_name,
       CASE WHEN mart.lech_obc(x.closing_day_code, x.j, 'closing_day_code')
            THEN (SELECT t.closing_day_name FROM core.dim_customer t
                  WHERE t.is_current AND t.closing_day_code = mart.ap_sua(x.closing_day_code, x.j, 'closing_day_code')
                    AND coalesce(t.closing_day_name, '') <> '' ORDER BY t.closing_day_name LIMIT 1)
            ELSE x.closing_day_name END                           AS closing_day_name,
       mart.ap_sua(x.transfer_account, x.j, 'transfer_account') AS transfer_account
FROM x;

CREATE VIEW mart.dim_product AS
WITH x AS (
    SELECT p.*, s.j
    FROM core.dim_product p
    LEFT JOIN mart.sua_theo_khoa s ON s.bang = 'san_pham' AND s.khoa = p.product_code
)
SELECT x.product_code,
       mart.ap_sua(x.product_name, x.j, 'product_name')             AS product_name,
       mart.ap_sua(x.name_ja, x.j, 'name_ja')                       AS name_ja,
       mart.ap_sua(x.kind_code, x.j, 'kind_code')                   AS kind_code,
       CASE WHEN mart.lech_obc(x.kind_code, x.j, 'kind_code')
            THEN (SELECT t.kind_name FROM core.dim_product t
                  WHERE t.kind_code = mart.ap_sua(x.kind_code, x.j, 'kind_code')
                    AND coalesce(t.kind_name, '') <> '' ORDER BY t.kind_name LIMIT 1)
            ELSE x.kind_name END                                      AS kind_name,
       mart.ap_sua(x.food_category_code, x.j, 'food_category_code') AS food_category_code,
       CASE WHEN mart.lech_obc(x.food_category_code, x.j, 'food_category_code')
            THEN (SELECT t.food_category_name FROM core.dim_product t
                  WHERE t.food_category_code = mart.ap_sua(x.food_category_code, x.j, 'food_category_code')
                    AND coalesce(t.food_category_name, '') <> '' ORDER BY t.food_category_name LIMIT 1)
            ELSE x.food_category_name END                             AS food_category_name,
       mart.ap_sua(x.rank_code, x.j, 'rank_code')                   AS rank_code,
       CASE WHEN mart.lech_obc(x.rank_code, x.j, 'rank_code')
            THEN (SELECT t.rank_name FROM core.dim_product t
                  WHERE t.rank_code = mart.ap_sua(x.rank_code, x.j, 'rank_code')
                    AND coalesce(t.rank_name, '') <> '' ORDER BY t.rank_name LIMIT 1)
            ELSE x.rank_name END                                      AS rank_name,
       mart.ap_sua(x.compete_code, x.j, 'compete_code')             AS compete_code,
       mart.ap_sua(x.barcode, x.j, 'barcode')                       AS barcode,
       mart.ap_sua(x.unit, x.j, 'unit')                             AS unit,
       mart.ap_sua(x.case_qty::text, x.j, 'case_qty')::numeric(14,4) AS case_qty,
       mart.ap_sua(x.shelf_code, x.j, 'shelf_code')                 AS shelf_code,
       mart.ap_sua(x.introduced_on, x.j, 'introduced_on')           AS introduced_on,
       x.batch_id,
       mart.ap_sua(x.pack1_code, x.j, 'pack1_code')                 AS pack1_code,
       mart.ap_sua(x.pack1_base_qty::text, x.j, 'pack1_base_qty')::numeric(14,4) AS pack1_base_qty
FROM x;

GRANT SELECT ON mart.sua_moi_nhat, mart.sua_theo_khoa, mart.dim_customer, mart.dim_product
    TO kome_app, kome_report, kome_ingest;
GRANT EXECUTE ON FUNCTION mart.ap_sua(text, jsonb, text), mart.lech_obc(text, jsonb, text)
    TO kome_app, kome_report, kome_ingest;

-- ---------------------------------------------------------------------------------------------------------------------
-- Phần 2 — mọi view / hàm của mart đang đọc danh mục OBC THÔ chuyển sang view hiệu lực. Đọc định nghĩa SỐNG trong danh mục
-- Postgres (không chép thân từ file cũ), đổi chuỗi, tạo lại. Cột ra y hệt (mart.dim_* cùng kiểu với core.dim_*) nên
-- CREATE OR REPLACE không phải DROP view phụ thuộc. Tên view hiệu lực TRÙNG tên bảng có chủ ý: pg_get_viewdef in
-- "dim_customer.cot" khi bảng không bí danh — đổi schema thì tên đó vẫn trỏ đúng.
-- Test canh: tests/test_bang_du_lieu_mart.py::test_KHONG_view_ham_mart_nao_con_doc_danh_muc_OBC_tho.
DO $do$
DECLARE r record; d text; sp text := current_setting('search_path');
BEGIN
    PERFORM set_config('search_path', 'pg_catalog', true);   -- mọi tên in ra đều có schema
    FOR r IN SELECT c.oid, c.relname FROM pg_class c
             WHERE c.relnamespace = 'mart'::regnamespace AND c.relkind = 'v'
               AND c.relname NOT IN ('dim_customer', 'dim_product')
               AND pg_get_viewdef(c.oid) ~ '\mcore\.dim_(customer|product)\M'
    LOOP
        d := regexp_replace(pg_get_viewdef(r.oid), '\mcore\.dim_(customer|product)\M', 'mart.dim_\1', 'g');
        d := regexp_replace(d, ';\s*$', '');
        EXECUTE format('CREATE OR REPLACE VIEW mart.%I AS %s', r.relname, d);
    END LOOP;
    FOR r IN SELECT p.oid FROM pg_proc p
             WHERE p.pronamespace = 'mart'::regnamespace AND p.prosrc ~ '\mcore\.dim_(customer|product)\M'
    LOOP
        EXECUTE regexp_replace(pg_get_functiondef(r.oid), '\mcore\.dim_(customer|product)\M', 'mart.dim_\1', 'g');
    END LOOP;
    PERFORM set_config('search_path', sp, true);             -- trả lại cho phần còn lại của giao dịch migration
END
$do$;

-- Giá hiệu lực (đặc tả §3): khoa sổ = mã|quy cách|bậc; chỉ áp lên dòng hiện hành; hai_cot_lech giữ theo OBC.
-- CTE f … lv chép NGUYÊN VĂN 071; chỉ câu SELECT cuối đổi. 14 cột đầu y hệt 071, gia_obc / da_sua thêm ở CUỐI.
CREATE OR REPLACE VIEW mart.bang_gia_kome AS
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
lv AS (SELECT product_code, pack_code, price_level FROM nay UNION SELECT product_code, pack_code, price_level FROM truoc),
hl AS (
    SELECT k.product_code, k.pack_code, lv.price_level, n.product_code IS NOT NULL AS hien_hanh,
           k.tu_ngay, k.tu_ngay_truoc, n.price_ex_tax, n.price_in_tax, n.hai_cot_lech, n.unit_cost,
           n.gia_chua_thue AS gia_obc, t.gia_chua_thue AS gia_truoc,
           CASE WHEN n.product_code IS NOT NULL
                THEN mart.ap_sua(n.gia_chua_thue::text, sk.j, 'gia_chua_thue')::numeric END AS gia_hl,
           n.product_code IS NOT NULL AND mart.lech_obc(n.gia_chua_thue::text, sk.j, 'gia_chua_thue') AS da_sua
    FROM k
    JOIN lv ON lv.product_code = k.product_code AND lv.pack_code = k.pack_code
    LEFT JOIN nay n ON n.product_code = lv.product_code AND n.pack_code = lv.pack_code AND n.price_level = lv.price_level
    LEFT JOIN truoc t ON t.product_code = lv.product_code AND t.pack_code = lv.pack_code AND t.price_level = lv.price_level
    LEFT JOIN mart.sua_theo_khoa sk
           ON sk.bang = 'gia' AND sk.khoa = k.product_code || '|' || k.pack_code || '|' || lv.price_level
)
SELECT product_code, pack_code, price_level, hien_hanh, tu_ngay, tu_ngay_truoc, price_ex_tax, price_in_tax,
       gia_hl AS gia_chua_thue, coalesce(hai_cot_lech, false) AS hai_cot_lech, nullif(unit_cost, 0) AS gia_von,
       gia_truoc,
       (tu_ngay_truoc IS NOT NULL AND gia_hl IS DISTINCT FROM gia_truoc) AS doi,
       coalesce(unit_cost > 0 AND gia_hl < unit_cost, false) AS duoi_gia_von,
       gia_obc, da_sua
FROM hl;

-- Tồn / hạn hiệu lực (đặc tả §3): khoa sổ = mã|kho, áp lên ảnh chụp ≤ mốc đang chọn (điều kiện ngày chụp y hệt 040).
-- gia_tri = stock_value của OBC, hoặc round(số lượng hiệu lực × stock_unit_cost) khi số lượng bị sửa. loai_han /
-- han_con_lai trên hạn hiệu lực. 8 cột đầu y hệt 040; bốn cột *_obc / sua_* thêm ở CUỐI.
CREATE OR REPLACE VIEW mart.ton_hien_tai AS
WITH i AS (
    SELECT i.*, sk.j
    FROM core.fact_inventory_daily i
    LEFT JOIN mart.sua_theo_khoa sk ON sk.bang = 'ton' AND sk.khoa = i.product_code || '|' || i.warehouse_code
    -- Ảnh chụp mới nhất KHÔNG SAU mốc đang xem (040). Chưa có ảnh chụp nào tới lúc đó ⇒ không dòng nào.
    WHERE i.snapshot_date = (SELECT max(snapshot_date) FROM core.fact_inventory_daily
                              WHERE snapshot_date <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date)))
),
h AS (
    SELECT i.*,
           mart.ap_sua(i.stock_qty::text, i.j, 'stock_qty')::numeric(14,4) AS sl,
           mart.ap_sua(i.best_before, i.j, 'best_before')                    AS bb,
           mart.lech_obc(i.stock_qty::text, i.j, 'stock_qty')                AS sua_sl,
           mart.lech_obc(i.best_before, i.j, 'best_before')                  AS sua_bb
    FROM i
)
SELECT h.product_code, h.warehouse_code, w.warehouse_name AS ten_kho,
       h.sl AS so_luong,
       CASE WHEN h.sua_sl THEN round(h.sl * h.stock_unit_cost)::bigint ELSE h.stock_value END AS gia_tri,
       h.bb AS best_before,
       CASE WHEN h.bb ~ '^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$' THEN 'ngay'
            -- btrim với danh sách ký tự tường minh (dấu cách thường VÀ dấu cách toàn giác U+3000) — xem 040.
            WHEN btrim(h.bb, ' 　') = '賞味期限なし'            THEN 'khong_han'
            WHEN coalesce(h.bb, '') = ''                     THEN 'trong'
            ELSE 'khong_ro' END AS loai_han,
       CASE WHEN h.bb ~ '^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$'
            THEN to_date(h.bb, 'YYYY"年"MM"月"DD"日"') - m.hom_nay
       END AS han_con_lai,
       h.stock_qty AS so_luong_obc, h.best_before AS best_before_obc, h.sua_sl AS sua_so_luong, h.sua_bb AS sua_han
FROM h
JOIN core.dim_warehouse w ON w.warehouse_code = h.warehouse_code
CROSS JOIN mart.moc_thoi_gian m;

-- Cờ quyền thứ tư (đặc tả §4). Sổ đổi quyền nhận thêm cờ đó. Đặt Ở CUỐI FILE có chủ ý: ALTER TABLE app.nguoi_dung giữ khoá
-- AccessExclusive trên bảng đăng nhập tới hết giao dịch — để nó sau mọi việc khác thì khoá đó giữ ngắn nhất có thể.
ALTER TABLE app.nguoi_dung ADD COLUMN duoc_sua_du_lieu boolean NOT NULL DEFAULT false;
ALTER TABLE app.nhat_ky_quyen DROP CONSTRAINT nhat_ky_quyen_co_check;
ALTER TABLE app.nhat_ky_quyen ADD CONSTRAINT nhat_ky_quyen_co_check
    CHECK (co IN ('duoc_vao_kho_du_lieu', 'duoc_sua_ngan_sach', 'duoc_quan_tri', 'duoc_sua_du_lieu'));
