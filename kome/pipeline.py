# kome/pipeline.py
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re
from kome import archive, gates
from kome.config import load_specs, FileSpec
from kome.reader import read, ColumnMismatch
from kome.loaders import inventory, customer

SPECS = load_specs(Path("config/files.yml"))
LOADERS = {"zaiko": inventory.load, "tokuisaki": customer.load}

# Bảng nào cần dọn khi hoàn tác một lô, theo từng loại file.
# Thêm loader mới thì BẮT BUỘC thêm mục ở đây, nếu không hoàn tác sẽ sót bảng.
# Lưu ý dim_customer là SCD2 (luật #6): undo_batch() chỉ DELETE các dòng có
# batch_id = lô vừa nạp (tức các dòng MỚI được insert ở lô đó); nó không phục
# hồi lại is_current của các dòng đã bị đóng valid_to trong cùng lô đó.
UNDO_TABLES = {"zaiko": ["core.fact_inventory_daily"], "tokuisaki": ["core.dim_customer"]}

@dataclass
class IngestResult:
    ok: bool
    spec_name: str | None = None
    row_count: int = 0
    total: int = 0
    batch_id: int | None = None
    skipped: bool = False
    blockers: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

def identify(path: Path) -> tuple[FileSpec, date] | tuple[None, None]:
    """Cổng 1: nhận ra loại file và ngày dữ liệu từ tên file."""
    for spec in SPECS.values():
        m = re.match(spec.filename_pattern, path.name)
        if m:
            return spec, datetime.strptime(m.group("date"), "%Y%m%d").date()
    return None, None

def ingest(conn, path: Path, archive_dir: Path) -> IngestResult:
    spec, data_date = identify(path)
    if spec is None:
        return IngestResult(ok=False, blockers=[gates.Blocker(1, f"Không nhận ra loại file: {path.name}")])

    digest = archive.sha256_of(path)
    if archive.already_loaded(conn, digest):
        return IngestResult(ok=True, spec_name=spec.name, skipped=True)

    try:
        df = read(path, spec)
    except ColumnMismatch as e:
        return IngestResult(ok=False, spec_name=spec.name, blockers=[gates.Blocker(2, str(e))])

    blockers, warnings = gates.check(path, spec, df, archive.previous_stats(conn, spec.name))
    if blockers:
        return IngestResult(ok=False, spec_name=spec.name, blockers=blockers, warnings=warnings)

    total = int(df[spec.money_columns[-1]].sum()) if spec.money_columns else 0
    batch_id = archive.store(conn, path, spec.name, digest, len(df), total, archive_dir)
    LOADERS[spec.name](conn, df, data_date, batch_id)

    return IngestResult(ok=True, spec_name=spec.name, row_count=len(df),
                        total=total, batch_id=batch_id, warnings=warnings)

def undo_batch(conn, batch_id: int) -> int:
    """Xoá dữ liệu của một lô rồi đánh dấu lô đã huỷ. Trả về số dòng đã xoá.

    KHÔNG xoá dòng trong meta.ingest_batch — chỉ đặt undone_at (luật bất biến #6).
    """
    row = conn.execute(
        "SELECT spec_name FROM meta.ingest_batch WHERE batch_id = %s", (batch_id,)
    ).fetchone()
    if row is None:
        return 0
    deleted = 0
    for table in UNDO_TABLES.get(row[0], []):
        cur = conn.execute(f"DELETE FROM {table} WHERE batch_id = %s", (batch_id,))
        deleted += cur.rowcount
    archive.undo(conn, batch_id)
    return deleted
