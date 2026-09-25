# kome/reader.py
from dataclasses import replace
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


def chon_sheet(path: Path, spec: FileSpec) -> tuple[str, str | None]:
    """Sheet sẽ đọc + câu cảnh báo (None nếu đúng tên khai báo).

    Tên sheet do mẫu xuất của OBC đặt, không phải dữ liệu: 2026-09-25 file
    得意先全情報 xuất ra sheet `得意先情報` thay vì `得意先データ作成` với đúng 16
    cột. CỘT mới là hợp đồng (cổng 2 vẫn soát đủ), nên: file chỉ có MỘT sheet
    thì đọc sheet đó và cảnh báo; nhiều sheet mà không sheet nào đúng tên thì
    KHÔNG đoán — chặn ở cổng 2, nêu tên các sheet có trong file."""
    from python_calamine import CalamineWorkbook
    co = CalamineWorkbook.from_path(str(path)).sheet_names
    if spec.sheet in co:
        return spec.sheet, None
    if len(co) == 1:
        return co[0], (f"Sheet tên '{co[0]}', không phải '{spec.sheet}' như mẫu — vẫn đọc vì "
                       "file chỉ có một sheet và đủ cột. Mẫu xuất trong OBC có bị đổi không?")
    raise ColumnMismatch(f"{spec.display_name}: không có sheet '{spec.sheet}' — file có "
                         f"{len(co)} sheet: {co}. Xuất lại đúng mẫu.")


def read(path: Path, spec: FileSpec) -> pd.DataFrame:
    """Đọc file Excel theo khai báo. Mọi mã giữ nguyên dạng chuỗi."""
    ten_sheet, canh_bao_sheet = chon_sheet(path, spec)
    if ten_sheet != spec.sheet:
        spec = replace(spec, sheet=ten_sheet)       # so_cai.chuan_bi đọc lại đúng sheet này
    df = pd.read_excel(
        path,
        sheet_name=ten_sheet,
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

    # 売上明細表 không có 明細行番号 trong file gốc -- sinh line_seq bằng số thứ
    # tự xuất hiện trong file, nhóm theo slip_no. PHẢI làm TRƯỚC dedup_on_keys
    # và trước cổng 3 (kiểm khoá trùng dùng spec.keys = [slip_no, line_seq]),
    # để line_seq tồn tại lúc cổng 3 kiểm tra.
    if spec.synthesize_line_seq:
        df["line_seq"] = df.groupby("slip_no").cumcount() + 1

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
    for col, rong in spec.code_width.items():
        df[col] = df[col].map(lambda v: v.zfill(rong) if v.isdigit() and len(v) < rong else v)

    # Sổ cái (元帳): kỳ, đối chiếu 【合計】, bỏ dòng tổng phụ — kome/so_cai.py.
    if spec.so_cai_truc:
        from kome import so_cai
        df = so_cai.chuan_bi(path, spec, df.reset_index(drop=True))
    else:
        df = df.reset_index(drop=True)
    # Gắn SAU cùng: các bước trên dựng DataFrame mới và không giữ attrs.
    df.attrs["canh_bao_sheet"] = canh_bao_sheet
    return df
