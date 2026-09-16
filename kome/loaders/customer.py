# kome/loaders/customer.py
from datetime import date, timedelta
import pandas as pd
import psycopg

TRACKED = [
    "customer_name", "branch_name", "rank_code", "category_code", "order_app_code",
    "salesperson_code", "price_level_code", "closing_day_code", "billing_customer_code",
    "postcode", "prefecture", "city", "address", "phone", "invoice_reg_no", "spot_flag",
]


def _norm(v):
    """Chuẩn hoá một giá trị TRACKED để so sánh/lưu trữ ổn định qua các lần nạp.

    Excel để trống -> pandas đọc thành NaN (float), không phải "". Nếu không
    chuẩn hoá, NaN != NaN nên mỗi lần nạp lại cùng file sẽ tưởng nhầm là "đổi",
    vi phạm ràng buộc #2 (nạp lại cùng file phải ra cùng kết quả).
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return v


def load(conn: psycopg.Connection, df: pd.DataFrame,
         snapshot_date: date, batch_id: int) -> dict:
    """SCD2. Chỉ tạo phiên bản mới khi một trong TRACKED thay đổi.

    Bản xuất một phần chỉ chứa vài khách KHÔNG được hiểu là các khách
    khác đã biến mất — hàm này chỉ upsert, không bao giờ đóng dòng của
    khách vắng mặt trong file.
    """
    current = {
        r[0]: tuple(_norm(v) for v in r[1:]) for r in conn.execute(
            f"SELECT customer_code, {', '.join(TRACKED)} FROM core.dim_customer WHERE is_current"
        ).fetchall()
    }
    inserted = closed = unchanged = 0
    with conn.cursor() as cur:
        for row in df.itertuples(index=False):
            code = row.customer_code
            new = tuple(_norm(getattr(row, c)) for c in TRACKED)
            old = current.get(code)
            if old is not None and old == new:
                unchanged += 1
                continue
            if old is not None:
                cur.execute(
                    """UPDATE core.dim_customer SET valid_to = %s, is_current = false
                       WHERE customer_code = %s AND is_current""",
                    (snapshot_date - timedelta(days=1), code),
                )
                closed += 1
            cur.execute(
                f"""INSERT INTO core.dim_customer
                      (customer_code, valid_from, is_current, {', '.join(TRACKED)}, batch_id)
                    VALUES (%s, %s, true, {', '.join(['%s'] * len(TRACKED))}, %s)""",
                (code, snapshot_date, *new, batch_id),
            )
            inserted += 1
    conn.commit()
    return {"inserted": inserted, "closed": closed, "unchanged": unchanged}
