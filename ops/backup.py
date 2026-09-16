"""Sao lưu CSDL bằng thuần Python — không dùng pg_dump/psql/pg_restore.

Máy chạy việc này không cài PostgreSQL client, và cài riêng chỉ để sao lưu là
thêm một thứ nữa phải bảo trì cho một công ty không có nhân sự IT.

Cấu trúc bảng đã nằm trong db/migrations/*.sql lưu git, nên bản sao lưu chỉ
cần DỮ LIỆU: mỗi bảng ghi ra CSV bằng `COPY ... TO STDOUT WITH CSV HEADER`
của psycopg 3, gom vào một file .zip kèm manifest.json (thời điểm, phiên bản
migration cuối, số dòng từng bảng).

Mật khẩu chỉ đến từ biến môi trường (DATABASE_URL/DATABASE_URL_TEST) và
KHÔNG BAO GIỜ được ghi vào file sao lưu hay manifest.json.
"""
import json
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg

SCHEMAS = ("core", "mart", "app", "meta")


def list_tables(conn: psycopg.Connection) -> list[str]:
    """Mọi bảng thật trong 4 schema, sắp theo tên để bản sao lưu ổn định."""
    rows = conn.execute(
        """SELECT table_schema || '.' || table_name
           FROM information_schema.tables
           WHERE table_schema = ANY(%s) AND table_type = 'BASE TABLE'
           ORDER BY 1""",
        (list(SCHEMAS),),
    ).fetchall()
    return [r[0] for r in rows]


def dump(database_url: str, out_dir: Path) -> Path:
    """Kết xuất DỮ LIỆU từng bảng ra CSV trong một file .zip.

    Không dùng pg_dump: cấu trúc bảng đã nằm trong db/migrations/*.sql lưu git,
    nên chỉ cần sao lưu dữ liệu. Khôi phục = apply_all() rồi COPY FROM.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"kome_{date.today():%Y%m%d}.zip"
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "tables": {}}
    with psycopg.connect(database_url) as conn, \
         zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for table in list_tables(conn):
            n = 0
            with z.open(f"{table}.csv", "w") as out, \
                 conn.cursor().copy(f"COPY {table} TO STDOUT WITH CSV HEADER") as cp:
                for chunk in cp:
                    out.write(bytes(chunk))
                    n += bytes(chunk).count(b"\n")
            manifest["tables"][table] = max(n - 1, 0)   # trừ dòng tiêu đề
        manifest["migrations"] = [
            r[0] for r in conn.execute(
                "SELECT filename FROM meta.schema_migration ORDER BY filename"
            ).fetchall()
        ]
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    return path


def prune(out_dir: Path, keep_daily: int = 30, keep_monthly: int = 12) -> list[Path]:
    """Giữ N bản gần nhất theo ngày + bản đầu mỗi tháng trong M tháng. Xoá phần còn lại."""
    files = sorted(Path(out_dir).glob("kome_*.zip"), reverse=True)
    keep = set(files[:keep_daily])
    seen_months: dict[str, Path] = {}
    for f in files:
        ym = f.stem[5:11]
        seen_months.setdefault(ym, f)
    for ym in sorted(seen_months, reverse=True)[:keep_monthly]:
        keep.add(seen_months[ym])
    for f in files:
        if f not in keep:
            f.unlink()
    return sorted(keep)
