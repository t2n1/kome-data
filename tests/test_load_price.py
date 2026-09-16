# tests/test_load_price.py
#
# 取引単価データ có 20 cột giá NẰM NGANG trên mỗi dòng nguồn; kome/loaders/price.py
# tự xoay thành DỌC (một dòng/mức giá). Đây là phần logic dễ vỡ nhất của Task 11:
# ghép lệch một mức (vd. gán nhầm 売価No.３ vào price_level='01') sẽ làm sai giá
# toàn hệ thống — chuỗi liên kết giá này là nền của báo cáo "phát hiện bán dưới
# giá" ở giai đoạn sau (xem docs/data-linkage.md §3.4). Dùng DataFrame dựng tay,
# không cần file Excel.
from datetime import date
import pandas as pd
from kome.loaders.price import load

D1 = date(2026, 9, 16)

# Tên các cột "phẳng" mà reader.read() tạo ra sau khi đổi tên theo config/files.yml
# (spec "tanka") — xem PRICE_LEVELS trong kome/loaders/price.py: '01'..'10'.
_LEVELS = [f"{i:02d}" for i in range(1, 11)]


def _row(product_code="P1", pack_code="00", unit_cost=0, **prices) -> dict:
    """Dựng một dòng nguồn đã qua reader (phẳng, 20 cột giá mặc định = 0/trống).

    `prices` nhận các cặp price_ex_NN=<số>, price_in_NN=<số> muốn ghi đè.
    """
    row = {"product_code": product_code, "pack_code": pack_code, "unit_cost": unit_cost}
    for level in _LEVELS:
        row[f"price_ex_{level}"] = 0
        row[f"price_in_{level}"] = 0
    row.update(prices)
    return row


def _fetch(conn, product_code=None):
    sql = ("SELECT product_code, pack_code, price_level, price_ex_tax, price_in_tax, unit_cost "
           "FROM core.fact_price_list")
    params = ()
    if product_code:
        sql += " WHERE product_code = %s"
        params = (product_code,)
    sql += " ORDER BY product_code, pack_code, price_level"
    return conn.execute(sql, params).fetchall()


def test_ghep_dung_theo_muc_gia(conn, batch):
    """Chống ghép lệch mức: 売価No.１ phải ra price_level='01', 売価No.３ ra '03'.

    Nếu ai đó viết lại vòng lặp sinh tên cột/chỉ số bị lệch, price_level='01'
    sẽ vô tình nhận giá trị của một mức khác — test này bắt đúng lỗi đó.
    """
    df = pd.DataFrame([_row(
        unit_cost=35,
        price_ex_01=100, price_in_01=108,
        price_ex_03=300, price_in_03=324,
    )])
    n = load(conn, df, D1, batch(1))
    assert n == 2
    rows = _fetch(conn, "P1")
    assert rows == [
        ("P1", "00", "01", 100, 108, 35),
        ("P1", "00", "03", 300, 324, 35),
    ]


def test_bo_qua_muc_gia_trong(conn, batch):
    """Chỉ điền 2/10 mức -> chỉ sinh 2 dòng, không sinh 10 dòng với giá trị 0."""
    df = pd.DataFrame([_row(
        price_ex_02=200, price_in_02=216,
        price_ex_07=700, price_in_07=756,
    )])
    n = load(conn, df, D1, batch(1))
    assert n == 2
    rows = _fetch(conn, "P1")
    assert [r[2] for r in rows] == ["02", "07"]


def test_nap_lai_vo_hai(conn, batch):
    """Nạp cùng khoá + cùng valid_from hai lần -> số dòng không đổi, giá cập nhật tại chỗ."""
    df1 = pd.DataFrame([_row(unit_cost=35, price_ex_01=100, price_in_01=108)])
    load(conn, df1, D1, batch(1))

    df2 = pd.DataFrame([_row(unit_cost=40, price_ex_01=150, price_in_01=162)])
    n2 = load(conn, df2, D1, batch(2))  # cùng valid_from D1

    assert n2 == 1
    rows = _fetch(conn, "P1")
    assert rows == [("P1", "00", "01", 150, 162, 40)]


def test_khoa_gom_ca_pack_code(conn, batch):
    """Cùng product_code, khác pack_code (lẻ vs thùng) -> hai bộ dòng riêng, không đè nhau."""
    df = pd.DataFrame([
        _row(pack_code="00", unit_cost=35, price_ex_01=100, price_in_01=108),   # bán lẻ
        _row(pack_code="02", unit_cost=1050, price_ex_01=3000, price_in_01=3240),  # bán thùng
    ])
    n = load(conn, df, D1, batch(1))
    assert n == 2
    rows = _fetch(conn, "P1")
    assert rows == [
        ("P1", "00", "01", 100, 108, 35),
        ("P1", "02", "01", 3000, 3240, 1050),
    ]


def test_muc_10_chu_so_nua_rong_khong_lam_lech(conn, batch):
    """Mức 1-9 dùng chữ số toàn rộng ở tên cột nguồn (売価No.１), mức 10 dùng nửa
    rộng (売価No.10) — bẫy dễ vỡ nếu ai viết lại vòng lặp sinh tên cột theo mẫu
    chuỗi thay vì số nguyên. Ở đây kiểm tra sau khi reader đã đổi tên thành
    price_ex_10/price_in_10, loader vẫn xếp đúng vào price_level='10', không lẫn
    với '01' hay bị bỏ sót.
    """
    df = pd.DataFrame([_row(
        price_ex_09=900, price_in_09=972,
        price_ex_10=1000, price_in_10=1080,
    )])
    n = load(conn, df, D1, batch(1))
    assert n == 2
    rows = _fetch(conn, "P1")
    assert rows == [
        ("P1", "00", "09", 900, 972, 0),
        ("P1", "00", "10", 1000, 1080, 0),
    ]
