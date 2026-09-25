# kome/loaders/customer.py
from datetime import date, timedelta
import pandas as pd
import psycopg
from psycopg.types.json import Jsonb

# Cột theo dõi = đúng các cột của mẫu xuất 16 cột (files.yml, 2026-09-25). Sáu cột cũ
# (category_code, order_app_code, price_level_code, billing_customer_code,
# invoice_reg_no, spot_flag) vẫn nằm trong bảng cho lịch sử, nhưng không nằm ở đây:
# phiên bản mới ghi NULL cho chúng, và đổi giá trị cũ không sinh phiên bản mới.
TRACKED = [
    "customer_name", "branch_name", "rank_code", "rank_name",
    "salesperson_code", "salesperson_name", "closing_day_code", "closing_day_name",
    "postcode", "prefecture", "city", "address", "building", "phone", "transfer_account",
]
# Cột theo dõi của mẫu CŨ (trước 2026-09-25). Chỉ để hoàn tác một lô cũ: ảnh trước
# (`scd2_preimage`) của lô đó mang các khoá này — kome.pipeline gán lại đúng những
# khoá CÓ trong ảnh trước, không hơn.
TRACKED_CU = [
    "category_code", "order_app_code", "price_level_code", "billing_customer_code",
    "invoice_reg_no", "spot_flag",
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

    Đè tại chỗ thì GIÁ TRỊ CŨ MẤT, mà nút Hoàn tác tồn tại để đưa mọi thứ về
    như cũ. Nên trước khi đè, giá trị cũ (kèm batch_id cũ) được chép vào
    `meta.ingest_batch.scd2_preimage` của chính lô đang nạp; `undo_batch()`
    trong kome/pipeline.py hoàn nguyên từ đó. Không có bước này thì hoàn tác
    XOÁ HẲN khách: dòng bị đè mang batch_id của lô mới, mà hoàn tác là
    `DELETE ... WHERE batch_id = %s` và đó là dòng duy nhất của khách.
    """
    current = {
        r[0]: (tuple(r[1:-2]), r[-2], r[-1]) for r in conn.execute(
            f"SELECT customer_code, {', '.join(TRACKED)}, valid_from, batch_id "
            f"FROM core.dim_customer WHERE is_current"
        ).fetchall()
    }
    inserted = closed = unchanged = updated = 0
    preimage: list[dict] = []
    with conn.cursor() as cur:
        for row in df.itertuples(index=False):
            code = row.customer_code
            new = tuple(getattr(row, c) for c in TRACKED)
            old = current.get(code)
            if old is not None and old[0] == new:
                unchanged += 1
                continue
            if old is not None and old[1] == snapshot_date:
                # Cùng ngày: sửa tại chỗ phiên bản đang mở — nhớ giá trị cũ để
                # hoàn tác lùi lại được (giá trị lấy từ CSDL nên chỉ có chữ và
                # NULL, chắc chắn ghi được ra JSON).
                preimage.append({"code": code, "batch_id": old[2],
                                 "values": dict(zip(TRACKED, old[0]))})
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
    if preimage:
        # Cùng giao dịch với các UPDATE ở trên: lô hỏng giữa chừng thì cả dữ
        # liệu lẫn ảnh trước cùng bị rollback, không bao giờ lệch nhau.
        conn.execute(
            "UPDATE meta.ingest_batch SET scd2_preimage = %s WHERE batch_id = %s",
            (Jsonb(preimage), batch_id),
        )
    conn.commit()
    return {"inserted": inserted, "closed": closed,
            "unchanged": unchanged, "updated": updated}
