from pathlib import Path
from db.migrate import apply_all


def test_apply_all_creates_schemas(fresh_conn):
    applied = apply_all(fresh_conn, Path("db/migrations"))
    assert "001_schemas.sql" in applied
    row = fresh_conn.execute(
        "SELECT count(*) FROM information_schema.schemata "
        "WHERE schema_name IN ('core','mart','app','meta')"
    ).fetchone()
    assert row[0] == 4


def test_apply_all_is_idempotent(fresh_conn):
    first = apply_all(fresh_conn, Path("db/migrations"))
    second = apply_all(fresh_conn, Path("db/migrations"))
    assert first != []
    assert second == []   # lần hai không chạy lại gì
