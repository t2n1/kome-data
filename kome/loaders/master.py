# kome/loaders/master.py
from datetime import date
from typing import Callable
import pandas as pd
import psycopg

def make_loader(table: str, keys: list[str], columns: list[str]) -> Callable:
    """Sinh loader upsert cho một bảng master. Không giữ lịch sử."""
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in columns if c not in keys)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}, batch_id) "
        f"VALUES ({', '.join(['%s'] * (len(columns) + 1))}) "
        f"ON CONFLICT ({', '.join(keys)}) DO UPDATE SET {updates}, batch_id=EXCLUDED.batch_id"
    )

    def load(conn: psycopg.Connection, df: pd.DataFrame,
             data_date: date, batch_id: int) -> int:
        rows = [tuple(getattr(r, c) for c in columns) + (batch_id,)
                for r in df.itertuples(index=False)]
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()
        return len(rows)

    return load
