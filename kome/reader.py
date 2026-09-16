# kome/reader.py
from pathlib import Path
import pandas as pd
from kome.config import FileSpec

class ColumnMismatch(Exception):
    """Cột trong file không khớp khai báo — cổng 2 dùng lỗi này."""


def dedup_on_keys(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Giữ dòng đầu tiên của mỗi khoá `keys`, bỏ các bản sao còn lại.

    Dùng cho các bản xuất OBC lặp lại CÙNG một dòng nghiệp vụ nhiều lần
    dưới các mục con khác nhau (vd. 売上伝票データ: 出荷内訳 và 明細按分 — cùng
    伝票No.+明細行番号, cùng 金額/粗利益). Không khử trùng thì cộng thẳng sẽ ra
    gấp đôi số thật.
    """
    return df.drop_duplicates(subset=keys, keep="first").reset_index(drop=True)


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

    if spec.dedup_on_keys:
        df = dedup_on_keys(df, spec.keys)

    for col in spec.date_columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        df[col] = df[col].where(df[col].notna(), None)

    for col in spec.money_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).round().astype("int64")
    for col in spec.qty_columns + spec.rate_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype("float64")
    for col in spec.code_columns:
        df[col] = df[col].fillna("").astype("object").str.strip()

    return df.reset_index(drop=True)
