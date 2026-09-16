import hashlib
import shutil
from datetime import date
from pathlib import Path
import psycopg


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def already_loaded(conn: psycopg.Connection, digest: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM meta.ingest_batch WHERE digest = %s AND undone_at IS NULL",
        (digest,),
    ).fetchone()
    return row is not None


def store(conn, path: Path, spec_name: str, digest: str,
          row_count: int, total: int, archive_dir: Path) -> int:
    """Lưu file gốc rồi ghi nhật ký. Lưu file TRƯỚC khi ghi CSDL."""
    folder = Path(archive_dir) / spec_name / date.today().strftime("%Y/%m")
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{path.stem}__{digest[:12]}{path.suffix}"
    shutil.copy2(path, dest)

    row = conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count, total_amount)
           VALUES (%s,%s,%s,%s,%s,%s) RETURNING batch_id""",
        (spec_name, path.name, digest, str(dest), row_count, total),
    ).fetchone()
    conn.commit()
    return row[0]


def previous_stats(conn, spec_name: str) -> dict | None:
    row = conn.execute(
        """SELECT row_count, total_amount FROM meta.ingest_batch
           WHERE spec_name = %s AND undone_at IS NULL
           ORDER BY loaded_at DESC LIMIT 1""",
        (spec_name,),
    ).fetchone()
    return {"row_count": row[0], "total": row[1]} if row else None


def undo(conn, batch_id: int) -> None:
    """Đánh dấu lô đã huỷ. Loader xoá dữ liệu theo batch_id trước khi gọi hàm này."""
    conn.execute(
        "UPDATE meta.ingest_batch SET undone_at = now() WHERE batch_id = %s", (batch_id,)
    )
    conn.commit()
