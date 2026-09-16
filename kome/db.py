import os
import psycopg


def connect(url: str | None = None) -> psycopg.Connection:
    """Mở kết nối Postgres. Mật khẩu chỉ đến từ biến môi trường."""
    return psycopg.connect(url or os.environ["DATABASE_URL"])
