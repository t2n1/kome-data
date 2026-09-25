from pathlib import Path
import pytest
from kome.config import load_specs
from kome.reader import read, ColumnMismatch
from kome.gates import check

SPECS = load_specs(Path("config/files.yml"))
OK = Path("tests/fixtures/zaiko_ok.xlsx")

def test_file_tot_khong_bi_chan():
    df = read(OK, SPECS["zaiko"])
    blockers, _ = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, previous=None)
    assert blockers == []

def test_cong_1_chan_sai_ten_file():
    df = read(OK, SPECS["zaiko"])
    blockers, _ = check(Path("bao_cao_linh_tinh.xlsx"), SPECS["zaiko"], df, None)
    assert any(b.gate == 1 for b in blockers)

def test_cong_2_chan_thieu_cot():
    with pytest.raises(ColumnMismatch):
        read(Path("tests/fixtures/zaiko_thieu_cot.xlsx"), SPECS["zaiko"])

def test_cong_3_chan_file_cat_cut():
    df = read(Path("tests/fixtures/zaiko_cat_cut.xlsx"), SPECS["zaiko"])
    blockers, _ = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert any(b.gate == 3 for b in blockers)

def test_cong_3_chan_khoa_trung():
    import pandas as pd
    df = read(OK, SPECS["zaiko"])
    doubled = pd.concat([df, df.iloc[[0]]], ignore_index=True)   # pandas 3: KHÔNG dùng _append
    blockers, _ = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], doubled, None)
    assert any(b.gate == 3 and "trùng" in b.message for b in blockers)

def test_cong_4_canh_bao_khi_tut_manh():
    df = read(OK, SPECS["zaiko"])
    prev = {"row_count": 400, "total": 300_000_000}
    _, warnings = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, prev)
    assert any(w.gate == 4 for w in warnings)

def test_cong_5_canh_bao_khi_tich_khong_khop():
    df = read(OK, SPECS["zaiko"])
    df.loc[0, "stock_value"] = 1
    _, warnings = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert any(w.gate == 5 for w in warnings)

def test_cong_3_chan_kho_rong_trong_key():
    """Một dòng có khoá rỗng phải bị chặn — lác đác không phải toàn bộ."""
    df = read(OK, SPECS["zaiko"])
    df.loc[0, "warehouse_code"] = ""  # rỗng ở một dòng
    blockers, _ = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert any(b.gate == 3 and "khoá" in b.message for b in blockers)

def test_cong_3_chan_fixture_zaiko_ma_rong_vi_kho_rong():
    """zaiko_ma_rong.xlsx có warehouse_code rỗng (nó là khoá) → phải chặn."""
    df = read(Path("tests/fixtures/zaiko_ma_rong.xlsx"), SPECS["zaiko"])
    blockers, _ = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert any(b.gate == 3 and "khoá" in b.message for b in blockers)

def test_cong_5_canh_bao_khi_khu_trung_gap_gia_tri_khac_nhau():
    """reader.dedup_on_keys() gắn số nhóm bất thường (cùng khoá nhưng khác
    tiền/số lượng) vào df.attrs["dedup_conflicts"] -- gates.check() phải
    biến nó thành cảnh báo cổng 5. KHÔNG chặn, vì chưa biết dòng nào trong
    nhóm là đúng."""
    df = read(OK, SPECS["zaiko"])
    df.attrs["dedup_conflicts"] = 1
    _, warnings = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert any(w.gate == 5 and "khử trùng" in w.message for w in warnings)

def test_cong_5_khong_canh_bao_khi_khu_trung_khong_co_xung_dot():
    df = read(OK, SPECS["zaiko"])
    assert df.attrs.get("dedup_conflicts", 0) == 0
    _, warnings = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert not any(w.gate == 5 and "khử trùng" in w.message for w in warnings)

def test_cong_3_khong_chan_ma_khong_key_roi_vai_dong():
    """Cột mã KHÔNG phải khoá rỗng vài dòng → KHÔNG bị chặn."""
    df = read(OK, SPECS["zaiko"])
    df.loc[0:2, "pack_code"] = ""  # pack_code không phải khoá, rỗng ở vài dòng
    blockers, _ = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert not any(b.gate == 3 and "pack_code" in b.message for b in blockers)

def test_cong_4_nguong_doc_tu_spec():
    """Ngưỡng cổng 4 đọc từ spec — nới rộng ngưỡng thì không cảnh báo."""
    from kome.config import FileSpec
    import pandas as pd

    df = read(OK, SPECS["zaiko"])
    prev = {"row_count": 400, "total": 300_000_000}

    # Với ngưỡng mặc định (0.5), dữ liệu này cảnh báo
    _, warnings_default = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, prev)
    assert any(w.gate == 4 for w in warnings_default)

    # Tạo spec với ngưỡng nới rộng hơn
    loose_spec = FileSpec(
        **{k: getattr(SPECS["zaiko"], k) for k in SPECS["zaiko"].__dataclass_fields__}
    )
    # Sử dụng dataclass replace để tạo bản copy với ngưỡng mới
    import dataclasses
    loose_spec = dataclasses.replace(
        loose_spec,
        warn_row_drop_ratio=0.1,  # nới rộng: chỉ cảnh báo khi rơi dưới 10%
    )

    # Với ngưỡng nới rộng, dữ liệu này KHÔNG cảnh báo
    _, warnings_loose = check(Path("在庫一覽_20260916.xlsx"), loose_spec, df, prev)
    assert not any(w.gate == 4 for w in warnings_loose)


# ---- Sheet sai tên (2026-09-25: 得意先全情報_20260925.xlsx xuất ra sheet 得意先情報
# thay vì 得意先データ作成 — trước đây nổ ValueError thành trang "hệ thống gặp lỗi").

def _doi_ten_sheet(tmp_path, ten: str, them_sheet: bool = False) -> Path:
    import openpyxl
    wb = openpyxl.load_workbook(OK)
    wb.active.title = ten
    if them_sheet:
        wb.create_sheet("Sheet2")
    p = tmp_path / "在庫一覧_20260916.xlsx"
    wb.save(p)
    return p


def test_sheet_sai_ten_ma_chi_mot_sheet_van_doc_va_canh_bao(tmp_path):
    """Cột mới là hợp đồng: một sheet duy nhất, đủ cột → đọc, kèm cảnh báo vàng."""
    p = _doi_ten_sheet(tmp_path, "在庫情報")
    df = read(p, SPECS["zaiko"])
    assert len(df) == len(read(OK, SPECS["zaiko"]))
    blockers, warnings = check(p, SPECS["zaiko"], df, None)
    assert blockers == []
    w = [x for x in warnings if x.gate == 2]
    assert w and "在庫情報" in w[0].message and SPECS["zaiko"].sheet in w[0].message


def test_sheet_sai_ten_va_nhieu_sheet_bi_cong_2_chan(tmp_path):
    """Nhiều sheet mà không sheet nào đúng tên: không đoán — cổng 2 chặn, nêu tên các sheet."""
    p = _doi_ten_sheet(tmp_path, "在庫情報", them_sheet=True)
    with pytest.raises(ColumnMismatch) as e:
        read(p, SPECS["zaiko"])
    assert "在庫情報" in str(e.value) and "Sheet2" in str(e.value)


def test_sheet_dung_ten_khong_canh_bao():
    df = read(OK, SPECS["zaiko"])
    _, warnings = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert not [w for w in warnings if w.gate == 2]
