# tests/test_reader.py
from pathlib import Path
from kome.config import load_specs
from kome.reader import read

SPECS = load_specs(Path("config/files.yml"))

def test_reads_inventory_fixture():
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    assert len(df) == 177
    assert df["stock_value"].sum() == 137_839_071

def test_codes_keep_leading_zeros():
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    assert set(df["warehouse_code"]) == {"0001", "1002"}
    assert df["warehouse_code"].dtype == object   # không bao giờ là số

def test_quantity_keeps_decimals():
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    assert (df["stock_qty"] % 1 != 0).sum() == 20   # 20 dòng có phần lẻ

def test_money_is_integer():
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    assert df["stock_value"].dtype.kind in "iu"

def test_ma_rong_thanh_chuoi_rong_khong_phai_nan():
    df = read(Path("tests/fixtures/zaiko_ma_rong.xlsx"), SPECS["zaiko"])
    assert (df["warehouse_code"] == "").sum() >= 2
    assert df["warehouse_code"].isna().sum() == 0   # phải là chuỗi rỗng, không phải NaN


def test_dedup_on_keys_mac_dinh_tat_cho_cac_spec_khac():
    """dedup_on_keys là tính năng riêng cho 売上伝票データ (Task 10, xuất mỗi
    dòng hai lần). Các spec khác KHÔNG khai báo nó trong files.yml nên phải
    nhận giá trị mặc định False -- không được vô tình bật cho spec khác."""
    assert SPECS["zaiko"].dedup_on_keys is False
    assert SPECS["tokuisaki"].dedup_on_keys is False


def test_synthesize_line_seq_mac_dinh_tat_cho_cac_spec_khac():
    """synthesize_line_seq là tính năng riêng cho 売上明細表 (không có
    明細行番号 trong file gốc). Các spec khác phải nhận mặc định False."""
    assert SPECS["zaiko"].synthesize_line_seq is False
    assert SPECS["uriage"].synthesize_line_seq is False


def test_khong_bat_dedup_thi_cong_3_van_chan_khoa_trung():
    """Quy hồi quy: với spec không bật dedup_on_keys, khoá trùng vẫn phải
    bị cổng 3 chặn như trước Task 10 -- dedup không được vô tình che giấu
    lỗi trùng khoá thật của các file khác."""
    import pandas as pd
    from kome.gates import check

    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    doubled = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    blockers, _ = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], doubled, None)
    assert any(b.gate == 3 and "trùng" in b.message for b in blockers)


def test_o_trong_cot_chu_thanh_none_khong_phai_chuoi_nan():
    """[IMPORTANT] pd.read_excel(dtype=str) trả ô trống thành NaN. Trước đây
    chỉ code_columns được chuẩn hoá, nên các cột chữ khác đi thẳng vào Postgres
    dưới dạng chuỗi 'NaN': cột trông có dữ liệu, `IS NULL` trả về False, và
    báo cáo rủi ro hạn sử dụng lọc `WHERE best_before IS NOT NULL` đếm cả dòng
    trống. Trên chính file mốc 在庫一覧_20260916: name_ja và best_before mỗi
    cột có 1 ô trống."""
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    for col in df.columns:
        if df[col].dtype == object:
            xau = [v for v in df[col] if isinstance(v, str) and v.strip().lower() == "nan"]
            assert xau == [], f"cột {col} chứa chuỗi 'NaN': {xau[:3]}"
    # và ô trống thật sự là None, không phải NaN
    assert df["name_ja"].isna().sum() >= 1
    assert all(v is None for v in df["name_ja"] if not isinstance(v, str))


def test_o_trong_vao_csdl_la_null_that(conn, batch):
    """Đi hết đường: đọc -> nạp -> `IS NULL` trong Postgres phải trả về True."""
    from datetime import date
    from kome.loaders import inventory

    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    inventory.load(conn, df, date(2026, 9, 16), batch(1))

    n_nan = conn.execute(
        """SELECT count(*) FROM core.fact_inventory_daily
           WHERE name_ja = 'NaN' OR best_before = 'NaN'"""
    ).fetchone()[0]
    assert n_nan == 0

    n_null = conn.execute(
        """SELECT count(*) FROM core.fact_inventory_daily
           WHERE name_ja IS NULL OR best_before IS NULL"""
    ).fetchone()[0]
    assert n_null >= 1          # ô trống thật -> NULL thật


def test_meisai_tu_sinh_line_seq_va_lay_dung_cot_trung_ten(tmp_path):
    """売上明細表 không có 明細行番号, và có 2 cột CÙNG TÊN 荷姿区分コード (một
    bản luôn có giá trị, một bản tra theo danh mục sản phẩm nên rỗng ở dòng
    phụ phí/coupon không phải sản phẩm thật -- đã kiểm chứng trên dữ liệu
    thật 2026-08-03: 0 lệch giữa 2 bản khi cả hai đều có dữ liệu).

    pandas tự thêm hậu tố ".1" cho cột trùng thứ hai khi đọc -- khai tên
    KHÔNG hậu tố trong config/files.yml là lấy đúng bản luôn có giá trị.
    """
    import pandas as pd
    cols = ["伝票No.", "得意先コード", "商品コード", "荷姿区分コード", "荷姿区分名",
            "売上日付", "伝票区分", "担当者コード", "部門コード",
            "入数", "純売上数量", "単価", "単位原価",
            "税込純売上高", "消費税額", "売上原価", "粗利益", "粗利益率", "消費税率",
            "荷姿区分コード", "荷姿区分名"]     # 2 cột cuối là bản trùng tên, để trống
    rows = [
        # 2 dòng cùng 伝票No. 090001 -> phải được sinh line_seq 1, 2
        ["090001", "000000009292", "XT07", "02", "ケース（大：段ボール）",
         "2026-08-03", "債権計上", "0004", "0020", 1, 6, 5250, 3210,
         31500, 2333, 19260, 9907, 0.3145, 0.08, "02", "ケース（大：段ボール）"],
        ["090001", "000000009292", "XT08", "00", "バ　ラ（小：単品）",
         "2026-08-03", "債権計上", "0004", "0020", 1, 2, 1000, 600,
         2000, 148, 1200, 652, 0.326, 0.08, "00", "バ　ラ（小：単品）"],
        # dòng phụ phí COD: mã không phải sản phẩm thật -> bản tra danh mục rỗng
        ["090001", "000000009292", "000000000001", "00", "荷姿区分なし",
         "2026-08-03", "債権計上", "0004", "0020", 1, 1, 300, 0,
         300, 22, 0, 273, 1.0, 0.08, "", ""],
    ]
    df_out = pd.DataFrame(rows, columns=cols)
    p = tmp_path / "売上明細表_20260803.xlsx"
    df_out.to_excel(p, sheet_name="売上明細表", index=False)

    doc = read(p, SPECS["meisai"])

    assert list(doc["line_seq"]) == [1, 2, 3]
    assert doc["pack_code"].tolist() == ["02", "00", "00"]   # bản LUÔN có giá trị
    assert doc["amount"].sum() == 33_800
