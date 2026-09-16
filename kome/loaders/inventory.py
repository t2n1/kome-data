from datetime import date
import pandas as pd
import psycopg

def load(conn: psycopg.Connection, df: pd.DataFrame,
         snapshot_date: date, batch_id: int) -> int:
    """Ghi snapshot tồn kho. Nạp lại cùng ngày → ghi đè theo khoá."""
    warehouses = df[["warehouse_code", "warehouse_name"]].drop_duplicates()
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO core.dim_warehouse (warehouse_code, warehouse_name)
               VALUES (%s, %s)
               ON CONFLICT (warehouse_code) DO UPDATE SET warehouse_name = EXCLUDED.warehouse_name""",
            warehouses.itertuples(index=False, name=None),
        )
        rows = [
            (snapshot_date, r.product_code, r.warehouse_code, r.pack_code,
             r.product_name, r.name_ja, r.unit, r.best_before,
             r.shipped_qty, r.stock_qty, r.stock_unit_cost, r.stock_value, batch_id)
            for r in df.itertuples(index=False)
        ]
        cur.executemany(
            """INSERT INTO core.fact_inventory_daily
                 (snapshot_date, product_code, warehouse_code, pack_code,
                  product_name, name_ja, unit, best_before,
                  shipped_qty, stock_qty, stock_unit_cost, stock_value, batch_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (snapshot_date, product_code, warehouse_code) DO UPDATE SET
                 pack_code=EXCLUDED.pack_code, product_name=EXCLUDED.product_name,
                 name_ja=EXCLUDED.name_ja, unit=EXCLUDED.unit,
                 best_before=EXCLUDED.best_before, shipped_qty=EXCLUDED.shipped_qty,
                 stock_qty=EXCLUDED.stock_qty, stock_unit_cost=EXCLUDED.stock_unit_cost,
                 stock_value=EXCLUDED.stock_value, batch_id=EXCLUDED.batch_id""",
            rows,
        )
    conn.commit()
    return len(rows)
