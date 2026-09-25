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


# Tiêu đề THẬT của bản xuất hằng ngày 売上明細表 (đo 2026-09-25): 20 cột, có hai
# cặp trùng tên (売上日付, 売上区分).
MEISAI_20_COT = [
    "売上日付", "売上区分", "伝票No.", "売上日付", "売上区分コード", "売上区分",
    "得意先コード", "得意先名", "担当者コード", "担当者名", "荷姿区分コード",
    "荷姿区分名", "商品名", "商品コード", "日本語", "単価", "税抜純売上高",
    "粗利益", "粗利益率", "純売上数量",
]


def _dong_meisai(slip, ma, pack, don_gia, net, lai, sl):
    return ["2026-09-25", "売上", slip, "2026-09-25", " 0", "売上",
            "000000000106", "QUAN CO AN", "0104", "TRAN THI LAN THANH", pack,
            "ケース（大：段ボール）", "Bot gao", ma, "米粉", don_gia, net, lai,
            0.1, sl]


def test_meisai_doc_duoc_mau_xuat_HANG_NGAY_20_cot(tmp_path):
    """Bản xuất hằng ngày chỉ có 20 cột (không 税込純売上高 / 消費税額 / 入数 /
    単位原価 / 売上原価 / 伝票区分 / 部門コード / 消費税率). Trước bản sửa 046 cổng
    2 chặn cả file vì 8 cột đó. amount của meisai = 税抜純売上高."""
    import pandas as pd
    rows = [
        _dong_meisai("095805", "TK04", "02", 7680, 14222, 1502, 2),
        _dong_meisai("095805", "DK17", "02", 7164, 6633, 2529, 1),
        _dong_meisai("095806", "000000000001", "00", 300, -300, -300, 1),  # 赤伝: ÂM
    ]
    p = tmp_path / "売上明細表_20260925.xlsx"
    pd.DataFrame(rows, columns=MEISAI_20_COT).to_excel(p, sheet_name="売上明細表", index=False)

    doc = read(p, SPECS["meisai"])

    assert list(doc["line_seq"]) == [1, 2, 1]
    assert doc["slip_no"].tolist() == ["095805", "095805", "095806"]
    assert doc["customer_code"].tolist() == ["000000000106"] * 3   # giữ số 0 đầu
    assert doc["amount"].tolist() == [14222, 6633, -300]          # 税抜, ÂM giữ nguyên
    assert doc["qty"].tolist() == [2.0, 1.0, 1.0]
    assert "tax_amount" not in doc.columns


def test_meisai_ban_117_cot_cu_van_doc_duoc_va_lay_ban_DAU_cua_cot_trung_ten(tmp_path):
    """Bản xuất cũ (2026-08-03) có 117 cột mà 20 cột ĐẦU giống hệt bản hằng ngày,
    và lặp lại 荷姿区分コード ở phần sau (bản tra danh mục — RỖNG ở dòng phụ phí/
    coupon). pandas thêm ".1" cho bản trùng thứ hai, nên khai tên không hậu tố
    là lấy bản đầu, luôn có giá trị. amount vẫn là 税抜 dù file có 税込."""
    import pandas as pd
    cot = MEISAI_20_COT + ["消費税額", "伝票区分", "荷姿区分コード", "入数", "単位原価",
                          "税込純売上高", "売上原価", "消費税率"]
    rows = [
        _dong_meisai("090001", "XT07", "02", 5250, 29167, 9907, 6)
        + [2333, "債権計上", "02", 1, 3210, 31500, 19260, 0.08],
        _dong_meisai("090001", "000000000001", "00", 300, 278, 278, 1)
        + [22, "債権計上", "", 1, 0, 300, 0, 0.08],
    ]
    p = tmp_path / "売上明細表_20260803.xlsx"
    pd.DataFrame(rows, columns=cot).to_excel(p, sheet_name="売上明細表", index=False)

    doc = read(p, SPECS["meisai"])

    assert list(doc["line_seq"]) == [1, 2]
    assert doc["pack_code"].tolist() == ["02", "00"]   # bản LUÔN có giá trị
    assert doc["amount"].tolist() == [29167, 278]      # 税抜, KHÔNG phải 税込
