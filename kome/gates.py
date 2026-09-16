from dataclasses import dataclass
from pathlib import Path
import re
import pandas as pd
from kome.config import FileSpec

@dataclass(frozen=True)
class Blocker:
    gate: int
    message: str

@dataclass(frozen=True)
class Warning_:
    gate: int
    message: str

def check(
    path: Path, spec: FileSpec, df: pd.DataFrame, previous: dict | None
) -> tuple[list[Blocker], list[Warning_]]:
    """5 cổng. Cổng 1-3 chặn, cổng 4-5 cảnh báo. Không bao giờ sửa dữ liệu."""
    blockers: list[Blocker] = []
    warnings: list[Warning_] = []

    # Cổng 1 — nhận diện file qua tên
    if not re.match(spec.filename_pattern, path.name):
        blockers.append(Blocker(1, f"Tên file không đúng mẫu {spec.display_name}: {path.name}"))

    # Cổng 2 — khớp cột: reader đã ném ColumnMismatch trước khi tới đây

    # Cổng 3 — hợp lý nghiệp vụ
    if len(df) < spec.min_rows:
        blockers.append(Blocker(3, f"Chỉ có {len(df)} dòng, tối thiểu {spec.min_rows} — nghi file xuất một phần"))
    dup = df.duplicated(subset=spec.keys).sum()
    if dup:
        blockers.append(Blocker(3, f"{dup} dòng trùng khoá {spec.keys}"))
    for col in spec.code_columns:
        if (df[col] == "").all():
            blockers.append(Blocker(3, f"Cột mã {col} rỗng toàn bộ"))

    # Cổng 4 — so với lần nạp trước
    total_col = spec.money_columns[-1] if spec.money_columns else None
    total = int(df[total_col].sum()) if total_col else 0
    if previous:
        prev_rows = previous.get("row_count") or 0
        prev_total = previous.get("total") or 0
        if prev_rows and len(df) < prev_rows * 0.5:
            warnings.append(Warning_(4, f"Số dòng rơi từ {prev_rows} xuống {len(df)}"))
        if prev_total and (total > prev_total * 3 or total < prev_total * 0.34):
            warnings.append(Warning_(4, f"Tổng tiền lệch mạnh: {prev_total:,} → {total:,}"))

    # Cổng 5 — đối chiếu tích
    pc = spec.product_check
    if pc:
        a, b = pc["factors"]
        expected = (df[a] * df[b]).round()
        bad = int((expected - df[pc["result"]]).abs().gt(1).sum())
        if bad:
            warnings.append(Warning_(5, f"{bad} dòng có {a} × {b} ≠ {pc['result']}"))

    return blockers, warnings
