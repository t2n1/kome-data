# kome/loaders/price.py
#
# 取引単価データ có 20 cột giá NẰM NGANG (売価No.１(税抜)..売価No.10(税込)) trên mỗi
# dòng nguồn (khoá 商品コード + 荷姿区分コード). Bảng đích core.fact_price_list là
# DỌC — mỗi mức giá một dòng, khoá (product_code, pack_code, price_level, valid_from).
# reader.read() chỉ đổi tên cột theo config/files.yml (spec "tanka"), KHÔNG xoay
# trục — loader này tự xoay ngang -> dọc, nên không dùng make_loader() dùng chung
# được cho ba file master còn lại.
from datetime import date
import pandas as pd
import psycopg

PRICE_LEVELS = [f"{i:02d}" for i in range(1, 11)]  # '01'..'10' ứng với 売価No.1..10

def load(conn: psycopg.Connection, df: pd.DataFrame,
         valid_from: date, batch_id: int) -> int:
    """Xoay 10 mức giá của mỗi dòng nguồn thành tối đa 10 dòng đích.

    Bỏ qua mức giá trống (cả 税抜 và 税込 đều 0 sau khi reader ép kiểu tiền) —
    nhiều sản phẩm chỉ dùng vài mức trong 10 mức. Không giữ lịch sử theo
    khoá tự nhiên (product_code, pack_code) — lịch sử giá nằm ở valid_from
    (một dòng theo mỗi lần nạp), theo đúng thiết kế core.fact_price_list.
    """
    rows = []
    for r in df.itertuples(index=False):
        for level in PRICE_LEVELS:
            ex = getattr(r, f"price_ex_{level}")
            inc = getattr(r, f"price_in_{level}")
            if ex == 0 and inc == 0:
                continue
            rows.append((r.product_code, r.pack_code, level, valid_from,
                         ex, inc, r.unit_cost, batch_id))

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO core.fact_price_list
                 (product_code, pack_code, price_level, valid_from,
                  price_ex_tax, price_in_tax, unit_cost, batch_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (product_code, pack_code, price_level, valid_from) DO UPDATE SET
                 price_ex_tax=EXCLUDED.price_ex_tax, price_in_tax=EXCLUDED.price_in_tax,
                 unit_cost=EXCLUDED.unit_cost, batch_id=EXCLUDED.batch_id""",
            rows,
        )
    conn.commit()
    return len(rows)
