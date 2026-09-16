import os
import pytest
import psycopg


@pytest.fixture
def test_db_url() -> str:
    """CHỈ CSDL thử nghiệm. Fixture conn sẽ XOÁ SẠCH schema — không bao giờ trỏ vào CSDL thật."""
    url = os.environ["DATABASE_URL_TEST"]
    assert url != os.environ.get("DATABASE_URL"), \
        "DATABASE_URL_TEST trùng DATABASE_URL — test sẽ xoá sạch CSDL thật"
    return url


@pytest.fixture
def conn(test_db_url):
    with psycopg.connect(test_db_url) as c:
        c.execute("DROP SCHEMA IF EXISTS core, mart, app, meta CASCADE")
        c.commit()
        yield c


@pytest.fixture
def batch(conn):
    """Tạo sẵn một dòng meta.ingest_batch và trả về batch_id.

    Mọi bảng fact/dim đều có batch_id REFERENCES meta.ingest_batch(batch_id),
    nên test nào ghi dữ liệu cũng phải có lô thật — truyền số 1 tuỳ tiện sẽ
    vi phạm khoá ngoại.
    """
    from pathlib import Path
    from db.migrate import apply_all
    apply_all(conn, Path("db/migrations"))

    def _make(n: int = 1) -> int:
        row = conn.execute(
            """INSERT INTO meta.ingest_batch
                 (spec_name, source_file, digest, archived_to, row_count)
               VALUES ('test', 'test.xlsx', %s, '/tmp/test.xlsx', 0)
               RETURNING batch_id""",
            (f"digest-{n}",),
        ).fetchone()
        conn.commit()
        return row[0]

    return _make
