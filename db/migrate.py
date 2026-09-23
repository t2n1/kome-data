from pathlib import Path
import psycopg

_TRACKER = """
CREATE SCHEMA IF NOT EXISTS meta;
CREATE TABLE IF NOT EXISTS meta.schema_migration (
    filename    text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now()
);
"""


def apply_all(conn: psycopg.Connection, migrations_dir: Path) -> list[str]:
    """Chạy các file .sql chưa chạy, theo thứ tự tên. Trả về tên file vừa chạy."""
    conn.execute(_TRACKER)
    conn.commit()
    done = {r[0] for r in conn.execute("SELECT filename FROM meta.schema_migration")}
    applied = []
    for path in sorted(migrations_dir.glob("*.sql")):
        if path.name in done:
            continue
        conn.execute(path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO meta.schema_migration (filename) VALUES (%s)", (path.name,)
        )
        conn.commit()
        applied.append(path.name)
    return applied


if __name__ == "__main__":
    # Đọc .env như mọi script khác (kome/env.py): thiếu dòng này thì lệnh
    # trong sổ tay nổ KeyError DATABASE_URL trên máy không nạp sẵn biến môi trường.
    from kome.env import nap_env
    nap_env()
    from kome.db import connect
    with connect() as c:
        for name in apply_all(c, Path(__file__).parent / "migrations"):
            print(f"đã chạy {name}")
