# kome/reader.py
from pathlib import Path
import pandas as pd
from kome.config import FileSpec

class ColumnMismatch(Exception):
    """Cột trong file không khớp khai báo — cổng 2 dùng lỗi này."""


def dedup_on_keys(
    df: pd.DataFrame, keys: list[str], compare_columns: list[str] | None = None
) -> pd.DataFrame:
    """Giữ dòng đầu tiên của mỗi khoá `keys`, bỏ các bản sao còn lại.

    Dùng cho các bản xuất OBC lặp lại CÙNG một dòng nghiệp vụ nhiều lần
    dưới các mục con khác nhau (vd. 売上伝票データ: 出荷内訳 và 明細按分 — cùng
    伝票No.+明細行番号, cùng 金額/粗利益). Không khử trùng thì cộng thẳng sẽ ra
    gấp đôi số thật.

    CHỈ so khoá — không tự biết bản sao có cùng giá trị hay không. Nếu
    `compare_columns` được truyền (thường là money_columns + qty_columns),
    hàm đếm số NHÓM trùng khoá mà các cột đó KHÔNG đồng nhất trong nhóm
    (nghi có hai dòng khác nhau bị gộp nhầm, không phải bản xuất lặp vô
    hại) và ghi số đó vào `df.attrs["dedup_conflicts"]` để gates.check()
    biến thành cảnh báo cổng 5 — hàm này không tự chặn, vì chưa biết dòng
    nào trong nhóm là đúng.
    """
    conflicts = 0
    cols = [c for c in (compare_columns or []) if c in df.columns]
    if cols:
        nunique = df.groupby(keys, sort=False)[cols].nunique(dropna=False)
        conflicts = int((nunique.max(axis=1) > 1).sum())
    result = df.drop_duplicates(subset=keys, keep="first").reset_index(drop=True)
    result.attrs["dedup_conflicts"] = conflicts
    return result


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

    # Ô TRỐNG -> None cho MỌI cột chữ, một lần, ngay tại đây.
    # pd.read_excel(dtype=str) trả ô trống thành NaN (float). Trước đây chỉ
    # code_columns được chuẩn hoá, nên các cột chữ khác đi thẳng vào Postgres
    # dưới dạng chuỗi 'NaN' — cột trông có dữ liệu, `IS NULL` trả về False, và
    # báo cáo lọc `WHERE best_before IS NOT NULL` đếm cả những dòng trống.
    # (Task 9 từng vá riêng cho dim_customer bằng customer._norm(); làm ở đây
    # thì inventory/master/price cũng được hưởng, không phải vá từng loader.)
    # Lưu ý pandas 3: dtype=str trả về dtype "str" (không phải "object"), nên
    # KHÔNG kiểm tra `dtype == object` — sẽ trượt hết và lỗi quay lại im lặng.
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s):
            continue
        df[col] = s.astype(object).where(s.notna(), None)

    if spec.dedup_on_keys:
        df = dedup_on_keys(df, spec.keys, spec.money_columns + spec.qty_columns)

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
