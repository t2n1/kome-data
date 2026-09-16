# kome/loaders/sales.py
from datetime import date
import pandas as pd
import psycopg

COLUMNS = [
    "slip_no", "line_seq", "sales_date", "billing_date", "slip_type",
    "customer_code", "billing_customer_code", "salesperson_code", "department_code",
    "shipto_code", "product_code", "pack_code", "case_qty", "qty", "unit_price",
    "unit_cost", "amount", "tax_amount", "cost", "gross_profit", "gross_margin",
    "tax_rate", "paid_amount", "payment_slip_no", "closing_day_code", "batch_id",
]
_UPDATE = ", ".join(f"{c}=EXCLUDED.{c}" for c in COLUMNS if c not in ("slip_no", "line_seq"))


def load(conn: psycopg.Connection, df: pd.DataFrame,
         data_date: date, batch_id: int) -> int:
    """Upsert theo 伝票No. + số dòng.

    Nhờ khoá này mà đối soát tháng hoạt động: nạp lại cả tháng thì phiếu
    đã sửa trong OBC được ghi đè, phiếu không đổi thì ghi lại y nguyên.

    LƯU Ý: 売上伝票データ xuất mỗi dòng nghiệp vụ HAI LẦN (出荷内訳 và 明細按分,
    cùng khoá slip_no+line_seq). Việc khử trùng phải xảy ra TRƯỚC khi tới đây
    (kome.reader.read() làm việc này qua cấu hình dedup_on_keys) — loader này
    chỉ upsert, không tự khử trùng, để dùng được cả cho dữ liệu test đã sạch.
    """
    df = df.copy()
    df["batch_id"] = batch_id
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = None
    rows = list(df[COLUMNS].itertuples(index=False, name=None))
    with conn.cursor() as cur:
        cur.executemany(
            f"""INSERT INTO core.fact_sales_line ({', '.join(COLUMNS)})
                VALUES ({', '.join(['%s'] * len(COLUMNS))})
                ON CONFLICT (slip_no, line_seq) DO UPDATE SET {_UPDATE}""",
            rows,
        )
    conn.commit()
    return len(rows)
