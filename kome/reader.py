# kome/reader.py
from pathlib import Path
import pandas as pd
from kome.config import FileSpec

class ColumnMismatch(Exception):
    """Cột trong file không khớp khai báo — cổng 2 dùng lỗi này."""

def read(path: Path, spec: FileSpec) -> pd.DataFrame:
    """Đọc file Excel theo khai báo. Mọi mã giữ nguyên dạng chuỗi."""
    df = pd.read_excel(
        path,
        sheet_name=spec.sheet,
        header=spec.header_row - 1,
        engine="calamine",
        dtype=str,              # đọc TẤT CẢ dạng chuỗi trước, ép kiểu sau
    )
    df.columns = [str(c).strip() for c in df.columns]

    missing = [ja for ja in spec.columns if ja not in df.columns]
    if missing:
        raise ColumnMismatch(
            f"{spec.display_name}: thiếu {len(missing)} cột: {missing[:10]}"
        )

    df = df[list(spec.columns)].rename(columns=spec.columns)
    df = df.dropna(how="all")

    for col in spec.money_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).round().astype("int64")
    for col in spec.qty_columns + spec.rate_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype("float64")
    for col in spec.code_columns:
        df[col] = df[col].fillna("").astype("object").str.strip()

    return df.reset_index(drop=True)
