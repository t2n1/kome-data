-- 072 — Bảng dữ liệu sửa trực tiếp (Kho dữ liệu › Bảng dữ liệu). Đặc tả 2026-09-30-bang-du-lieu-sua-design.md.
-- core VẪN chỉ đọc với web: bản sửa ở sổ CHỈ THÊM app.sua_du_lieu; mọi chỉ số đọc GIÁ TRỊ HIỆU LỰC qua mart.dim_customer,
-- mart.dim_product, mart.bang_gia_kome, mart.ton_hien_tai. Luật (chủ DN chốt 2026-09-30): OBC vẫn ghi đúng giá trị lúc sửa
-- → bản sửa thắng; OBC ghi khác (người ta đã sửa trong OBC) → OBC thắng. Viết MỘT lần: mart.ap_sua / mart.lech_obc.

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
     OR (bang = 'ton' AND cot IN ('stock_qty', 'best_before')))
);
CREATE INDEX sua_du_lieu_o ON app.sua_du_lieu (bang, khoa, cot, id DESC);
GRANT SELECT, INSERT ON app.sua_du_lieu TO kome_app;
GRANT USAGE ON SEQUENCE app.sua_du_lieu_id_seq TO kome_app;
REVOKE UPDATE, DELETE ON app.sua_du_lieu FROM kome_app;
GRANT SELECT ON app.sua_du_lieu TO kome_report, kome_ingest;

-- Cờ quyền thứ tư (đặc tả §4). Sổ đổi quyền nhận thêm cờ đó.
ALTER TABLE app.nguoi_dung ADD COLUMN duoc_sua_du_lieu boolean NOT NULL DEFAULT false;
ALTER TABLE app.nhat_ky_quyen DROP CONSTRAINT nhat_ky_quyen_co_check;
ALTER TABLE app.nhat_ky_quyen ADD CONSTRAINT nhat_ky_quyen_co_check
    CHECK (co IN ('duoc_vao_kho_du_lieu', 'duoc_sua_ngan_sach', 'duoc_quan_tri', 'duoc_sua_du_lieu'));

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
