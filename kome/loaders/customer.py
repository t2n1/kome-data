# kome/loaders/customer.py
from datetime import date, timedelta
import pandas as pd
import psycopg

TRACKED = [
    "customer_name", "branch_name", "rank_code", "category_code", "order_app_code",
    "salesperson_code", "price_level_code", "closing_day_code", "billing_customer_code",
    "postcode", "prefecture", "city", "address", "phone", "invoice_reg_no", "spot_flag",
]

# Ô trống của Excel (NaN của pandas) đã được kome.reader.read() chuẩn hoá thành
# None cho MỌI cột chữ, nên loader này không cần chuẩn hoá lại — trước đây có
# hàm _norm() riêng, chỉ customer.py được hưởng còn inventory/master/price thì
# không (xem ghi chú trong kome/reader.py).

_SET_TRACKED = ", ".join(f"{c} = %s" for c in TRACKED)


def load(conn: psycopg.Connection, df: pd.DataFrame,
         snapshot_date: date, batch_id: int) -> dict:
    """SCD2. Chỉ tạo phiên bản mới khi một trong TRACKED thay đổi.

    Bản xuất một phần chỉ chứa vài khách KHÔNG được hiểu là các khách
    khác đã biến mất — hàm này chỉ upsert, không bao giờ đóng dòng của
    khách vắng mặt trong file.

    Sửa lại TRONG NGÀY (kế toán phát hiện sai, sửa trong OBC, xuất lại, kéo–thả
    lại cùng ngày) thì CẬP NHẬT TẠI CHỖ phiên bản đang mở, không đóng-rồi-mở-mới:
    đóng bằng `snapshot_date - 1 ngày` khi phiên bản cũ cũng bắt đầu đúng ngày đó
    sẽ sinh `valid_to < valid_from`, và mọi truy vấn lịch sử dạng
    `valid_from <= d AND (valid_to IS NULL OR valid_to >= d)` sẽ không bao giờ
    trả về dòng ấy — nó biến mất khỏi lịch sử vĩnh viễn.
    """
    current = {
        r[0]: (tuple(r[1:-1]), r[-1]) for r in conn.execute(
            f"SELECT customer_code, {', '.join(TRACKED)}, valid_from "
            f"FROM core.dim_customer WHERE is_current"
        ).fetchall()
    }
    inserted = closed = unchanged = updated = 0
    with conn.cursor() as cur:
        for row in df.itertuples(index=False):
            code = row.customer_code
            new = tuple(getattr(row, c) for c in TRACKED)
            old = current.get(code)
            if old is not None and old[0] == new:
                unchanged += 1
                continue
            if old is not None and old[1] == snapshot_date:
                # Cùng ngày: sửa tại chỗ phiên bản đang mở.
                cur.execute(
                    f"""UPDATE core.dim_customer SET {_SET_TRACKED}, batch_id = %s
                        WHERE customer_code = %s AND is_current""",
                    (*new, batch_id, code),
                )
                updated += 1
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
    return {"inserted": inserted, "closed": closed,
            "unchanged": unchanged, "updated": updated}
