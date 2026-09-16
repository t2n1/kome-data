# tests/test_load_sales.py
from datetime import date
import pandas as pd
from kome.loaders import sales
from kome.reader import dedup_on_keys


def _line(slip="079934", seq=1, amount=29167, profit=9907, qty=6, batch_id=1):
    return {
        "slip_no": slip, "line_seq": seq, "sales_date": date(2026, 5, 1),
        "slip_type": "債権計上", "customer_code": "000000009292",
        "billing_customer_code": "000000009292", "salesperson_code": "0004",
        "product_code": "XT07", "pack_code": "02", "case_qty": 1, "qty": qty, "unit_price": 5250,
        "unit_cost": 3210, "amount": amount, "tax_amount": 2333, "cost": 19260,
        "gross_profit": profit, "gross_margin": 0.3397, "paid_amount": 0,
        "batch_id": batch_id,
    }


def test_nap_va_cong_dung(conn, batch):
    b = batch(1)
    df = pd.DataFrame([_line(seq=1, batch_id=b), _line(seq=2, amount=37778, profit=14498, batch_id=b)])
    assert sales.load(conn, df, date(2026, 5, 1), b) == 2
    r = conn.execute("SELECT sum(amount), sum(gross_profit) FROM core.fact_sales_line").fetchone()
    assert r[0] == 66_945 and r[1] == 24_405


def test_phieu_do_so_am_duoc_giu_nguyen(conn, batch):
    b = batch(1)
    df = pd.DataFrame([
        _line(seq=1, batch_id=b),
        _line(seq=2, amount=-29167, profit=-9907, qty=-6, batch_id=b),
    ])
    sales.load(conn, df, date(2026, 5, 1), b)
    total = conn.execute("SELECT sum(amount) FROM core.fact_sales_line").fetchone()[0]
    assert total == 0          # bán rồi trả lại = 0, KHÔNG lọc bỏ dòng âm
    n = conn.execute("SELECT count(*) FROM core.fact_sales_line").fetchone()[0]
    assert n == 2


def test_nap_ba_lan_van_the(conn, batch):
    for i in range(3):
        b = batch(i + 1)
        df = pd.DataFrame([_line(batch_id=b)])
        sales.load(conn, df, date(2026, 5, 1), b)
    r = conn.execute("SELECT count(*), sum(amount) FROM core.fact_sales_line").fetchone()
    assert r[0] == 1 and r[1] == 29_167


def test_doi_soat_thang_ghi_de_phieu_da_sua(conn, batch):
    b1 = batch(1)
    sales.load(conn, pd.DataFrame([_line(amount=29167, batch_id=b1)]), date(2026, 5, 1), b1)
    b2 = batch(2)
    sales.load(conn, pd.DataFrame([_line(amount=25000, batch_id=b2)]), date(2026, 5, 1), b2)
    r = conn.execute("SELECT sum(amount), count(*) FROM core.fact_sales_line").fetchone()
    assert r[0] == 25_000 and r[1] == 1


def test_khu_trung_dong_xuat_hai_lan():
    """売上伝票データ xuất mỗi dòng nghiệp vụ HAI LẦN: một lần dưới 出荷内訳,
    một lần dưới 明細按分 — cùng 伝票No. + 明細行番号, cùng 金額/粗利益.

    Không khử trùng thì cộng thẳng ra gấp đôi doanh thu thực. Giữ dòng đầu
    tiên của mỗi khoá (slip_no, line_seq) là đủ (đã kiểm chứng trên dữ liệu
    thật: 4 cách lọc khác nhau đều cho cùng tổng 粗利益)."""
    df = pd.DataFrame([
        {"slip_no": "079934", "line_seq": 1, "amount": 31500, "gross_profit": 9907},   # 出荷内訳
        {"slip_no": "079934", "line_seq": 1, "amount": 31500, "gross_profit": 9907},   # 明細按分 (bản sao)
        {"slip_no": "079934", "line_seq": 2, "amount": 5000, "gross_profit": 1000},
        {"slip_no": "079934", "line_seq": 2, "amount": 5000, "gross_profit": 1000},
        {"slip_no": "079935", "line_seq": 1, "amount": 1200, "gross_profit": 300},
    ])
    result = dedup_on_keys(df, ["slip_no", "line_seq"])
    assert len(result) == 3
    assert result["amount"].sum() == 37_700
    assert result["gross_profit"].sum() == 11_207
