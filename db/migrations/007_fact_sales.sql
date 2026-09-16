CREATE TABLE core.fact_sales_line (
    slip_no               text          NOT NULL,
    line_seq              integer       NOT NULL,
    sales_date            date          NOT NULL REFERENCES core.dim_date(date_key),
    billing_date          date,
    slip_type             text,
    customer_code         text          NOT NULL,
    billing_customer_code text,
    salesperson_code      text,
    department_code       text,
    shipto_code           text,
    product_code          text          NOT NULL,
    pack_code             text          NOT NULL DEFAULT '',
    case_qty              numeric(14,4) NOT NULL DEFAULT 0,
    qty                   numeric(14,4) NOT NULL DEFAULT 0,
    unit_price            bigint        NOT NULL DEFAULT 0,
    unit_cost             bigint        NOT NULL DEFAULT 0,
    amount                bigint        NOT NULL DEFAULT 0,
    tax_amount            bigint        NOT NULL DEFAULT 0,
    cost                  bigint        NOT NULL DEFAULT 0,
    gross_profit          bigint        NOT NULL DEFAULT 0,
    gross_margin          numeric(6,4),
    tax_rate              numeric(6,4),
    paid_amount           bigint        NOT NULL DEFAULT 0,
    payment_slip_no       text,
    closing_day_code      text,
    batch_id              bigint        NOT NULL REFERENCES meta.ingest_batch(batch_id),
    PRIMARY KEY (slip_no, line_seq)
);
CREATE INDEX ON core.fact_sales_line (sales_date);
CREATE INDEX ON core.fact_sales_line (customer_code, sales_date DESC);
CREATE INDEX ON core.fact_sales_line (product_code, sales_date DESC);
CREATE INDEX ON core.fact_sales_line (batch_id);

COMMENT ON TABLE core.fact_sales_line IS
  'Độ hạt: 伝票No. + số thứ tự dòng. 赤伝 (hàng trả) giữ nguyên số ÂM, không lọc bỏ. '
  '売上伝票データ xuất mỗi dòng hai lần (出荷内訳 + 明細按分, cùng khoá) — loader khử '
  'trùng bằng dedup_on_keys trước khi ghi, giữ dòng đầu tiên của mỗi (slip_no, line_seq).';
