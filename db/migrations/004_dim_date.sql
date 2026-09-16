CREATE TABLE core.dim_date (
    date_key       date    PRIMARY KEY,
    year           integer NOT NULL,
    month          integer NOT NULL,
    day            integer NOT NULL,
    fiscal_year    integer NOT NULL,
    fiscal_quarter integer NOT NULL,
    iso_week       integer NOT NULL,
    day_of_week    integer NOT NULL,
    is_weekend     boolean NOT NULL
);

COMMENT ON COLUMN core.dim_date.fiscal_year IS
  'Năm tài chính Nhật: bắt đầu 1/4. Tháng 1-3 thuộc năm tài chính trước.';

INSERT INTO core.dim_date
SELECT d::date,
       EXTRACT(year  FROM d)::int,
       EXTRACT(month FROM d)::int,
       EXTRACT(day   FROM d)::int,
       CASE WHEN EXTRACT(month FROM d) >= 4
            THEN EXTRACT(year FROM d)::int
            ELSE EXTRACT(year FROM d)::int - 1 END,
       ((EXTRACT(month FROM d)::int + 8) % 12) / 3 + 1,
       EXTRACT(week FROM d)::int,
       EXTRACT(isodow FROM d)::int,
       EXTRACT(isodow FROM d)::int >= 6
FROM generate_series('2024-01-01'::date, '2035-12-31'::date, '1 day') AS d;
