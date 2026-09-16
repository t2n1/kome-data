CREATE TABLE core.dim_warehouse (
    warehouse_code text PRIMARY KEY,
    warehouse_name text NOT NULL,
    first_seen     date NOT NULL DEFAULT current_date
);

CREATE TABLE core.fact_inventory_daily (
    snapshot_date   date          NOT NULL REFERENCES core.dim_date(date_key),
    product_code    text          NOT NULL,
    warehouse_code  text          NOT NULL REFERENCES core.dim_warehouse(warehouse_code),
    pack_code       text          NOT NULL DEFAULT '',
    product_name    text,
    name_ja         text,
    unit            text,
    best_before     text,                      -- giữ nguyên dạng '2028年06月09日'
    shipped_qty     numeric(14,4) NOT NULL DEFAULT 0,   -- xuất TRONG NGÀY
    stock_qty       numeric(14,4) NOT NULL DEFAULT 0,   -- CÓ phần thập phân
    stock_unit_cost bigint        NOT NULL DEFAULT 0,
    stock_value     bigint        NOT NULL DEFAULT 0,
    batch_id        bigint        NOT NULL REFERENCES meta.ingest_batch(batch_id),
    PRIMARY KEY (snapshot_date, product_code, warehouse_code)
);
CREATE INDEX ON core.fact_inventory_daily (product_code, snapshot_date DESC);
CREATE INDEX ON core.fact_inventory_daily (batch_id);

COMMENT ON TABLE core.fact_inventory_daily IS
  'Độ hạt: 商品コード + 倉庫コード + ngày. Đã kiểm chứng 177 khoá/177 dòng, 0 trùng.';
COMMENT ON COLUMN core.fact_inventory_daily.stock_qty IS
  'NUMERIC vì có phần thập phân thật (83.75 ケース). KHÔNG ép số nguyên.';
