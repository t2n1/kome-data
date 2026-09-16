CREATE TABLE core.dim_customer (
    customer_sk           bigserial PRIMARY KEY,
    customer_code         text NOT NULL,
    valid_from            date NOT NULL,
    valid_to              date,
    is_current            boolean NOT NULL DEFAULT true,
    customer_name         text,
    branch_name           text,
    rank_code             text,
    category_code         text,
    order_app_code        text,
    salesperson_code      text,
    price_level_code      text,
    closing_day_code      text,
    billing_customer_code text,
    postcode              text,
    prefecture            text,
    city                  text,
    address               text,
    phone                 text,
    invoice_reg_no        text,
    spot_flag             text,
    batch_id              bigint NOT NULL REFERENCES meta.ingest_batch(batch_id)
);
CREATE UNIQUE INDEX ON core.dim_customer (customer_code) WHERE is_current;
CREATE INDEX ON core.dim_customer (customer_code, valid_from);

COMMENT ON TABLE core.dim_customer IS
  'SCD2. KHÔNG BAO GIỜ XOÁ DÒNG — chỉ đóng valid_to và đặt is_current=false.';
