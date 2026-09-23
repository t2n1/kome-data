"""Chuẩn bị file sổ cái OBC (元帳) sau khi reader đã đọc và ép kiểu (đợt 6).

Sổ cái không phải một bảng phẳng như các file khác: phía trên header có 5 dòng
thông tin, và giữa các dòng chi tiết có dòng TỔNG PHỤ (伝票計 / ［ n月計］ /
【合計】). Hàm ở đây:
  1. đọc kỳ của file từ dòng 集計期間 — không có kỳ thì không biết ảnh chụp này
     "tính đến ngày nào";
  2. kiểm dòng 集計軸項目 đúng loại sổ khai trong files.yml (`so_cai_truc`) —
     `請求先元帳` và `得意先元帳` dùng CHUNG tên sheet `得意先元帳`;
  3. đối chiếu từng bên: mang sang + 【合計】(債権額 + 債権調整額 − 入金額 −
     入金調整額) = 残高 của dòng cuối → số bên lệch vào `df.attrs["so_cai_lech"]`
     (cổng 5, cảnh báo);
  4. bỏ dòng tổng phụ, gắn `line_kind`, `row_seq`, `period_from`, `period_to`.
Dòng có 行タイトル lạ (không phải trống / 繰越残高 / tổng phụ đã biết) là mẫu xuất
khác → ColumnMismatch (cổng 2), không đoán.
"""
from datetime import date
from pathlib import Path
import re

import pandas as pd

from kome.config import FileSpec

MANG_SANG = "繰越残高"
_TONG_PHU = re.compile(r"^(伝票計|【合計】|［\s*\d{1,2}月計］)$")
_KY = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*～\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日")


def doc_thong_tin(path: Path, spec: FileSpec) -> dict[str, str]:
    """Các dòng phía trên header: cột A là nhãn, cột B là giá trị."""
    raw = pd.read_excel(path, sheet_name=spec.sheet, header=None,
                        nrows=spec.header_row - 1, engine="calamine", dtype=str)
    out = {}
    for _, r in raw.iterrows():
        k = str(r.iloc[0]).strip() if pd.notna(r.iloc[0]) else ""
        v = str(r.iloc[1]).strip() if len(r) > 1 and pd.notna(r.iloc[1]) else ""
        if k:
            out[k] = v
    return out


def doc_ky(chuoi: str) -> tuple[date, date] | None:
    m = _KY.search(chuoi or "")
    if not m:
        return None
    y1, m1, d1, y2, m2, d2 = (int(x) for x in m.groups())
    return date(y1, m1, d1), date(y2, m2, d2)


def chuan_bi(path: Path, spec: FileSpec, df: pd.DataFrame) -> pd.DataFrame:
    from kome.reader import ColumnMismatch

    tt = doc_thong_tin(path, spec)
    truc = tt.get("集計軸項目", "")
    if truc != spec.so_cai_truc:
        raise ColumnMismatch(
            f"{spec.display_name}: dòng 集計軸項目 là '{truc or '(trống)'}', phải là "
            f"'{spec.so_cai_truc}' — có thể là sổ khác loại (得意先元帳 / 請求先元帳 cùng tên sheet)")
    ky = doc_ky(tt.get("集計期間", ""))
    if ky is None:
        raise ColumnMismatch(f"{spec.display_name}: không đọc được kỳ ở dòng 集計期間")

    tieu_de = df["row_title"].fillna("").astype(str).str.strip()
    la_tong = tieu_de.str.match(_TONG_PHU)
    la = (tieu_de == "") | (tieu_de == MANG_SANG) | la_tong
    if not la.all():
        la_la = sorted(set(tieu_de[~la]))[:5]
        raise ColumnMismatch(f"{spec.display_name}: có dòng 行タイトル lạ {la_la} — mẫu xuất khác")

    # Cổng 5: đối chiếu với 【合計】 từng bên nhận hoá đơn.
    ma = df["billing_customer_code"]
    mang = df[tieu_de == MANG_SANG].groupby(ma)["balance"].sum()
    tong = df[tieu_de == "【合計】"].groupby(ma)[
        ["receivable_amount", "receivable_adj", "payment_amount", "payment_adj"]].sum()
    chi_tiet = df[(tieu_de == "") | (tieu_de == MANG_SANG)]
    cuoi = chi_tiet.groupby(chi_tiet["billing_customer_code"])["balance"].last()
    lech = 0
    for m, so_du in cuoi.items():
        t = tong.loc[m] if m in tong.index else None
        bien = 0 if t is None else int(t.receivable_amount + t.receivable_adj
                                       - t.payment_amount - t.payment_adj)
        if int(mang.get(m, 0)) + bien != int(so_du):
            lech += 1

    out = chi_tiet.copy()
    td = tieu_de[out.index]
    # Dòng chi tiết: phiếu THU khi chỉ có cột thu (入金額 / 入金調整額) mang giá trị;
    # còn lại là phiếu bán — kể cả phiếu 債権額 = 0 (đo thật: có phiếu bán ¥1 mà
    # 債権額 = 0, ô không trống).
    thu = ((out["payment_amount"] != 0) | (out["payment_adj"] != 0)) \
        & (out["receivable_amount"] == 0) & (out["receivable_adj"] == 0) & (out["sales_amount"] == 0)
    out["line_kind"] = "phieu_ban"
    out.loc[thu, "line_kind"] = "phieu_thu"
    out.loc[td == MANG_SANG, "line_kind"] = "mang_sang"
    out["period_from"], out["period_to"] = ky
    out = out.drop(columns=["row_title"]).reset_index(drop=True)
    out["row_seq"] = range(1, len(out) + 1)
    out.attrs["so_cai_lech"] = lech
    out.attrs["so_ben"] = int(cuoi.size)
    return out
