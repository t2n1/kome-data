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
            with z.open(f"{table}.csv", "w") as out, \
                 conn.cursor().copy(f"COPY {table} TO STDOUT WITH CSV HEADER") as cp:
                for chunk in cp:
                    out.write(bytes(chunk))
            # Đếm bằng SELECT count(*), KHÔNG đếm ký tự xuống dòng trong CSV:
            # một ô chữ chứa ký tự xuống dòng (商品名, 支店名 — Excel cho phép)
            # làm số đếm lớn hơn thực tế, khiến verify() mỗi quý báo ok:False
            # GIẢ. Cảnh báo sai cũng nguy hiểm như không cảnh báo: người ta
            # học cách bỏ qua nó.
            manifest["tables"][table] = conn.execute(
                f"SELECT count(*) FROM {table}"
            ).fetchone()[0]
        manifest["migrations"] = [
            r[0] for r in conn.execute(
                "SELECT filename FROM meta.schema_migration ORDER BY filename"
            ).fetchall()
        ]
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    return path


def backup_status(out_dir: Path, max_age_hours: float = 36) -> dict:
    """Trạng thái sao lưu mới nhất trong out_dir — dùng cho dải cảnh báo trên
    trang /health.

    'Mới nhất' xét theo thời điểm sửa đổi file (mtime), không theo ngày mã
    hoá trong tên file `kome_YYYYMMDD.zip` — file có thể được chép lại/ghi đè
    mà không đổi tên. Trả về {"stale": bool, "last": datetime | None}.
    """
    out_dir = Path(out_dir)
    files = (
        sorted(out_dir.glob("kome_*.zip"), key=lambda p: p.stat().st_mtime)
        if out_dir.exists() else []
    )
    if not files:
        return {"stale": True, "last": None}
    last = datetime.fromtimestamp(files[-1].stat().st_mtime, tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    return {"stale": age_hours > max_age_hours, "last": last}


def prune(out_dir: Path, keep_daily: int = 30, keep_monthly: int = 12) -> list[Path]:
    """Giữ N bản gần nhất theo ngày + bản CUỐI mỗi tháng (ngày lớn nhất trong
    tháng, khớp với chốt sổ) trong M tháng. Xoá phần còn lại."""
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


# --- Chạy trực tiếp: python -m ops.backup -------------------------------------
# Tự đọc .env nên chạy được ở PowerShell, Git Bash, và cả Windows Task Scheduler
# (nơi môi trường trống rỗng — xem kome/env.py).
if __name__ == "__main__":
    import os, sys
    from kome.env import nap_env

    nap_env()
    thu_muc = Path(os.environ.get("BACKUP_DIR", "./backups"))
    url = os.environ["DATABASE_URL_TEST" if "--test" in sys.argv else "DATABASE_URL"]
    f = dump(url, thu_muc)
    giu = prune(thu_muc)
    print(f"Đã sao lưu: {f}")
    print(f"Giữ lại {len(giu)} bản trong {thu_muc}")
