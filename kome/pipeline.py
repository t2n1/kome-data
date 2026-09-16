# kome/pipeline.py
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re
from kome import archive, gates
from kome.config import load_specs, FileSpec
from kome.reader import read, ColumnMismatch
from kome.loaders import inventory, customer, sales

SPECS = load_specs(Path("config/files.yml"))
LOADERS = {"zaiko": inventory.load, "tokuisaki": customer.load, "uriage": sales.load}

# Bảng nào cần dọn khi hoàn tác một lô, theo từng loại file.
# Thêm loader mới thì BẮT BUỘC thêm mục ở đây, nếu không hoàn tác sẽ sót bảng.
UNDO_TABLES = {
    "zaiko": ["core.fact_inventory_daily"],
    "tokuisaki": ["core.dim_customer"],
    "uriage": ["core.fact_sales_line"],
}

# Bảng SCD2: hoàn tác phải mở lại phiên bản trước đó, không chỉ xoá phiên bản
# mới — nếu không, khách bị đóng valid_to ở lô đó sẽ mất hẳn is_current=true
# và biến mất khỏi mọi báo cáo. Dạng: spec_name -> (tên bảng, cột khoá nghiệp vụ).
# Bảng nào có mặt ở đây thì undo_batch() xử lý riêng, KHÔNG xoá lại theo
# UNDO_TABLES nữa (tránh xoá hai lần) — nhưng vẫn giữ trong UNDO_TABLES để
# test lưới an toàn set(LOADERS) == set(UNDO_TABLES) còn đúng.
UNDO_SCD2 = {"tokuisaki": ("core.dim_customer", "customer_code")}

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

    Bảng SCD2 (UNDO_SCD2) được xử lý riêng theo 3 bước: (1) lấy trước danh sách
    khoá nghiệp vụ bị đụng tới ở lô này, (2) xoá phiên bản mới do lô này tạo,
    (3) mở lại phiên bản còn lại mới nhất của từng khoá đó (is_current=true,
    valid_to=NULL) — nếu không, khách bị đóng ở lô này sẽ mất hẳn is_current
    và biến mất khỏi báo cáo mà không ai biết.
    """
    row = conn.execute(
        "SELECT spec_name FROM meta.ingest_batch WHERE batch_id = %s", (batch_id,)
    ).fetchone()
    if row is None:
        return 0
    spec_name = row[0]
    deleted = 0

    scd2 = UNDO_SCD2.get(spec_name)
    if scd2:
        table, key = scd2
        codes = [
            r[0] for r in conn.execute(
                f"SELECT DISTINCT {key} FROM {table} WHERE batch_id = %s", (batch_id,)
            ).fetchall()
        ]
        cur = conn.execute(f"DELETE FROM {table} WHERE batch_id = %s", (batch_id,))
        deleted += cur.rowcount
        if codes:
            conn.execute(
                f"""UPDATE {table} d SET is_current = true, valid_to = NULL
                    FROM (SELECT {key} AS k, max(valid_from) AS vf FROM {table}
                          WHERE {key} = ANY(%s) GROUP BY {key}) latest
                    WHERE d.{key} = latest.k AND d.valid_from = latest.vf""",
                (codes,),
            )

    for table in UNDO_TABLES.get(spec_name, []):
        if scd2 and table == scd2[0]:
            continue   # đã xử lý ở nhánh SCD2 phía trên
        cur = conn.execute(f"DELETE FROM {table} WHERE batch_id = %s", (batch_id,))
        deleted += cur.rowcount

    archive.undo(conn, batch_id)
    return deleted
