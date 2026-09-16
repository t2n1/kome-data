-- db/migrations/008_masters.sql
CREATE TABLE core.dim_supplier (
    supplier_code text PRIMARY KEY,
    supplier_name text,
    batch_id      bigint NOT NULL REFERENCES meta.ingest_batch(batch_id)
);

CREATE TABLE core.dim_product (
    product_code    text PRIMARY KEY,
    product_name    text,
    name_ja         text,
    kind_code       text,
    kind_name       text,
    food_category_code text,
    food_category_name text,
    rank_code       text,
    rank_name       text,
    compete_code    text,
    barcode         text,
    unit            text,
    case_qty        numeric(14,4) NOT NULL DEFAULT 0,
    shelf_code      text,
    introduced_on   text,
    batch_id        bigint NOT NULL REFERENCES meta.ingest_batch(batch_id)
);

CREATE TABLE core.dim_shipto (
    shipto_code   text PRIMARY KEY,
    shipto_name   text,
    customer_code text,            -- CÓ THỂ RỖNG: điểm giao không thuộc khách nào
    postcode      text,
    prefecture    text,
    city          text,
    address       text,
    phone         text,
    lead_time_code text,
    batch_id      bigint NOT NULL REFERENCES meta.ingest_batch(batch_id)
);
CREATE INDEX ON core.dim_shipto (customer_code);

CREATE TABLE core.fact_price_list (
    product_code text   NOT NULL,
    pack_code    text   NOT NULL,
    price_level  text   NOT NULL,      -- '01'..'10' ứng với 売価No.1..10
    valid_from   date   NOT NULL,
    price_ex_tax bigint NOT NULL DEFAULT 0,
    price_in_tax bigint NOT NULL DEFAULT 0,
    unit_cost    bigint NOT NULL DEFAULT 0,
    batch_id     bigint NOT NULL REFERENCES meta.ingest_batch(batch_id),
    PRIMARY KEY (product_code, pack_code, price_level, valid_from)
);

COMMENT ON TABLE core.fact_price_list IS
  'Giữ lịch sử giá. Ghép với dim_customer.price_level_code để ra giá đáng lẽ
   phải bán, so với fact_sales_line.unit_price để phát hiện bán dưới giá.
   Xem docs/data-linkage.md §3.4.';
COMMENT ON COLUMN core.dim_shipto.customer_code IS
  'Cho phép RỖNG — đã thấy 直送先 không gắn khách nào trong dữ liệu thật.';
