# kome/loaders/so_cai.py
"""Ghi sổ công nợ 請求先元帳 vào core.fact_ar_ledger (đợt 6, migration 038).

Mỗi lô là MỘT ẢNH CHỤP của một kỳ — không xoá, không đè lô cũ. Mart đọc lô có
kỳ kết thúc muộn nhất (`mart.so_cong_no_moi_nhat`); hoàn tác xoá theo batch_id
như mọi bảng `core`, lô trước tự quay lại. Dữ liệu đã được kome/so_cai.py chuẩn
bị (bỏ dòng tổng phụ, gắn line_kind / row_seq / kỳ) trước khi tới đây.
"""
from datetime import date

import pandas as pd
import psycopg

COT = ["row_seq", "billing_customer_code", "billing_customer_name", "closing_day_code",
       "closing_day_name", "line_kind", "entry_date", "slip_no", "bank_name",
       "receivable_amount", "receivable_adj", "sales_amount", "tax_amount",
       "payment_amount", "payment_adj", "balance", "memo", "period_from", "period_to"]


def _o(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and v == ""):
        return None
    return v.item() if hasattr(v, "item") else v


def load(conn: psycopg.Connection, df: pd.DataFrame, data_date: date, batch_id: int) -> int:
    rows = [(batch_id, *(_o(getattr(r, c)) for c in COT)) for r in df.itertuples(index=False)]
    with conn.cursor() as cur:
        cur.executemany(
            f"""INSERT INTO core.fact_ar_ledger (batch_id, {", ".join(COT)})
                VALUES ({", ".join(["%s"] * (len(COT) + 1))})""",
            rows)
    conn.commit()
    return len(rows)
