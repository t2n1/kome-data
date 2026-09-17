from datetime import date
import os
from pathlib import Path

import pytest
import psycopg

from db.migrate import apply_all
from kome.db import connect as ket_noi
from kome.env import nap_env

# Đọc .env ngay khi pytest nạp conftest. Không có dòng này thì `pytest` chỉ
# chạy được sau khi người ta nhớ nạp biến môi trường bằng tay — và trên
# PowerShell thì cú pháp nạp đó còn khác Bash. Biến đã có sẵn vẫn được ưu
# tiên, nên chạy trong CI (không có .env) không đổi gì.
nap_env(bat_buoc=False)

MIGRATIONS = Path("db/migrations")
SCHEMAS = ("core", "mart", "app", "meta")

# Bảng KHÔNG được dọn giữa hai test:
#  - meta.schema_migration: xoá là mất dấu vết migration -> mỗi test lại chạy
#    lại cả bộ migration (đo được: 3,6 giây/lần, chủ yếu do 004_dim_date.sql
#    chèn ~4.380 dòng qua pooler Tokyo).
#  - core.dim_date: dữ liệu THAM CHIẾU do chính migration nạp, mọi bảng fact
#    đều có khoá ngoại tới nó. Xoá đi là mọi lần nạp đều vỡ khoá ngoại.
GIU_LAI = {"meta.schema_migration", "core.dim_date"}

# Nhớ danh sách bảng sau lần tra đầu tiên (xem fixture `conn`).
_TABLES: list[str] | None = None


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """CHỈ CSDL thử nghiệm. Các fixture dưới đây XOÁ SẠCH dữ liệu — không bao giờ trỏ vào CSDL thật."""
    url = os.environ["DATABASE_URL_TEST"]
    assert url != os.environ.get("DATABASE_URL"), \
        "DATABASE_URL_TEST trùng DATABASE_URL — test sẽ xoá sạch CSDL thật"
    return url


@pytest.fixture(scope="session")
def _session_conn(test_db_url):
    """Một kết nối duy nhất cho cả phiên test, schema đã dựng sẵn.

    Trước đây fixture `conn` mở kết nối mới + DROP SCHEMA + apply_all() trước
    MỖI test: ~55 test × 3,6 giây ≈ 3,3 phút chỉ để chuẩn bị (004_dim_date.sql
    chèn ~4.380 dòng qua pooler Tokyo mỗi lần). Giờ dựng một lần và giữ nguyên
    kết nối — mở kết nối qua pooler cũng mất ~0,5 giây/lần.

    Không dùng Docker hay bất cứ thứ gì phải cài đặt: ràng buộc của dự án là
    giảm tối đa số thứ có thể hỏng.

    Dùng `kome.db.connect()` chứ không gọi thẳng `psycopg.connect()`: hàm đó
    tự tắt câu lệnh chuẩn bị sẵn khi URL đi qua pooler giao dịch (cổng 6543,
    đúng cổng `DATABASE_URL_TEST` đang dùng). Bỏ qua nó từng làm lộ đúng lỗi
    `kome/db.py` viết ra để né: `prepared statement "_pg3_N" does not exist`,
    vì pooler có thể âm thầm đổi kết nối vật lý phía sau kết nối phiên dài
    này (đã bắt được lỗi này thật, không phải giả định).
    """
    with ket_noi(test_db_url) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {', '.join(SCHEMAS)} CASCADE")
        c.commit()
        apply_all(c, MIGRATIONS)
        yield c


def _bang_can_don(c: psycopg.Connection) -> list[str]:
    rows = c.execute(
        """SELECT table_schema || '.' || table_name
           FROM information_schema.tables
           WHERE table_schema = ANY(%s) AND table_type = 'BASE TABLE'
           ORDER BY 1""",
        (list(SCHEMAS),),
    ).fetchall()
    return [r[0] for r in rows if r[0] not in GIU_LAI]


@pytest.fixture
def conn(_session_conn):
    """Kết nối sạch DỮ LIỆU cho mỗi test — schema đã dựng sẵn ở phạm vi phiên.

    rollback() trước để một test hỏng giữa giao dịch không kéo theo test sau.
    Danh sách bảng tra một lần rồi nhớ lại: mỗi vòng hỏi-đáp qua pooler Tokyo
    mất ~60 ms, nhân với số test là đáng kể.
    """
    c = _session_conn
    c.rollback()
    global _TABLES
    if _TABLES is None:
        _TABLES = _bang_can_don(c)
    if _TABLES:
        c.execute(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE")
    c.commit()
    yield c


@pytest.fixture
def fresh_conn(test_db_url, _session_conn):
    """Schema dựng SẠCH TỪ ĐẦU — chỉ dành cho tests/test_migrate.py và
    tests/test_roles.py, hai file cần chứng kiến chính việc migration chạy.

    Dùng kết nối riêng để không làm hỏng trạng thái kết nối dùng chung. Dọn dẹp
    cuối fixture dựng lại schema đầy đủ cho các test sau trong cùng phiên
    (apply_all là no-op nếu test đã tự chạy nó).
    """
    _session_conn.rollback()
    with ket_noi(test_db_url) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {', '.join(SCHEMAS)} CASCADE")
        c.commit()
        yield c
        apply_all(c, MIGRATIONS)


@pytest.fixture
def batch(conn):
    """Tạo sẵn một dòng meta.ingest_batch và trả về batch_id.

    Mọi bảng fact/dim đều có batch_id REFERENCES meta.ingest_batch(batch_id),
    nên test nào ghi dữ liệu cũng phải có lô thật — truyền số 1 tuỳ tiện sẽ
    vi phạm khoá ngoại.
    """
    def _make(n: int = 1, ngay: date = date(2026, 1, 1)) -> int:
        row = conn.execute(
            """INSERT INTO meta.ingest_batch
                 (spec_name, source_file, digest, archived_to, row_count, data_date)
               VALUES ('test', 'test.xlsx', %s, '/tmp/test.xlsx', 0, %s)
               RETURNING batch_id""",
            (f"digest-{n}", ngay),
        ).fetchone()
        conn.commit()
        return row[0]

    return _make
