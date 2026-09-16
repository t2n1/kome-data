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

    # Khoá rỗng ở BẤT KỲ dòng nào -> chặn (làm hỏng upsert)
    for col in spec.keys:
        n = int((df[col].astype(str).str.strip() == "").sum())
        if n:
            blockers.append(Blocker(3, f"{n} dòng có khoá {col} rỗng"))

    # Cột mã rỗng TOÀN BỘ -> chặn (nghi chọn sai mẫu xuất)
    for col in spec.code_columns:
        if len(df) and (df[col].astype(str).str.strip() == "").all():
            blockers.append(Blocker(3, f"Cột mã {col} rỗng toàn bộ"))

    # Ngày bắt buộc không đọc được (errors="coerce" ở reader đã nuốt lỗi
    # thành None/NaT) -> chặn TRƯỚC khi lô được lưu, không để lô mồ côi
    # trong meta.ingest_batch hay bung lỗi khoá ngoại giữa chừng.
    for col in spec.required_date_columns:
        if col in df.columns:
            n = int(df[col].isna().sum())
            if n:
                blockers.append(Blocker(3, f"{n} dòng có {col} không đọc được thành ngày"))

    # Cổng 4 — so với lần nạp trước.
    # Cột tiền đại diện đọc từ spec.total_column (khai tay trong files.yml),
    # KHÔNG suy ra từ money_columns[-1]: với 売上伝票データ cột cuối là 入金額１
    # (gần như luôn 0), nên total = 0 và điều kiện `prev_total and ...` bên
    # dưới sẽ TẮT IM LẶNG cả nhánh cảnh báo lệch tiền cho đúng file quan
    # trọng nhất. total_column = None nghĩa là file không có tiền đại diện
    # (file master, bảng giá) -> bỏ qua nhánh tiền CÓ CHỦ Ý.
    total_col = spec.total_column
    total = int(df[total_col].sum()) if total_col else 0
    if previous:
        prev_rows = previous.get("row_count") or 0
        prev_total = previous.get("total") or 0
        if prev_rows and len(df) < prev_rows * spec.warn_row_drop_ratio:
            warnings.append(Warning_(4, f"Số dòng rơi từ {prev_rows} xuống {len(df)}"))
        if total_col and prev_total and (
            total > prev_total * spec.warn_total_spike
            or total < prev_total * spec.warn_total_drop
        ):
            warnings.append(Warning_(4, f"Tổng tiền lệch mạnh: {prev_total:,} → {total:,}"))

    # Cổng 5 — khử trùng (dedup_on_keys) đã gộp các dòng trùng khoá mà GIÁ TRỊ
    # khác nhau (tiền/số lượng) -> cảnh báo, không tự biết dòng nào đúng nên
    # không chặn. df.attrs được reader.dedup_on_keys() gắn vào khi so sánh.
    dedup_conflicts = df.attrs.get("dedup_conflicts", 0)
    if dedup_conflicts:
        warnings.append(Warning_(
            5, f"{dedup_conflicts} nhóm trùng khoá {spec.keys} có giá trị khác nhau "
               f"khi khử trùng — đã giữ dòng đầu tiên, cần kiểm tra"))

    # Cổng 5 — đối chiếu tích
    pc = spec.product_check
    if pc:
        a, b = pc["factors"]
        expected = (df[a] * df[b]).round()
        bad = int((expected - df[pc["result"]]).abs().gt(1).sum())
        if bad:
            warnings.append(Warning_(5, f"{bad} dòng có {a} × {b} ≠ {pc['result']}"))

    return blockers, warnings
