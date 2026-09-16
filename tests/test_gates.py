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
