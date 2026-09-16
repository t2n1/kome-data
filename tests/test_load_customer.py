from datetime import date
import pandas as pd
from kome.loaders import customer

D1 = date(2026, 9, 16)
D2 = date(2026, 9, 17)
D3 = date(2026, 9, 18)


def _df(rank="0003"):
    return pd.DataFrame([{
        "customer_code": "000000009292", "customer_name": "株式会社ASIANEX",
        "branch_name": "あじさい支店", "rank_code": rank, "category_code": "0202",
        "order_app_code": "0001", "salesperson_code": "0105", "price_level_code": "10",
        "closing_day_code": "99", "billing_customer_code": "000000009292",
        "postcode": "3720855", "prefecture": "群馬県", "city": "伊勢崎市",
        "address": "長沼町 615-4", "phone": "0270-75-6396",
        "invoice_reg_no": "", "spot_flag": "0",
    }])


def test_lan_dau_tao_mot_phien_ban(conn, batch):
    r = customer.load(conn, _df(), D1, batch(1))
    assert r["inserted"] == 1
    n = conn.execute("SELECT count(*) FROM core.dim_customer WHERE is_current").fetchone()[0]
    assert n == 1


def test_khong_doi_gi_thi_khong_tao_phien_ban_moi(conn, batch):
    customer.load(conn, _df(), D1, batch(1))
    r = customer.load(conn, _df(), D2, batch(2))
    assert r["inserted"] == 0 and r["unchanged"] == 1
    n = conn.execute("SELECT count(*) FROM core.dim_customer").fetchone()[0]
    assert n == 1


def test_doi_hang_thi_tao_phien_ban_moi_va_dong_cai_cu(conn, batch):
    customer.load(conn, _df(rank="0003"), D1, batch(1))
    r = customer.load(conn, _df(rank="0001"), D2, batch(2))
    assert r["inserted"] == 1 and r["closed"] == 1
    rows = conn.execute(
        """SELECT rank_code, valid_from, valid_to, is_current FROM core.dim_customer
           WHERE customer_code = '000000009292' ORDER BY valid_from"""
    ).fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "0003" and str(rows[0][2]) == "2026-09-16" and rows[0][3] is False
    assert rows[1][0] == "0001" and rows[1][3] is True


def test_khong_bao_gio_xoa_dong(conn, batch):
    customer.load(conn, _df(rank="0003"), D1, batch(1))
    customer.load(conn, _df(rank="0001"), D2, batch(2))
    customer.load(conn, _df(rank="0002"), D3, batch(3))
    n = conn.execute("SELECT count(*) FROM core.dim_customer").fetchone()[0]
    assert n == 3   # luật bất biến #6


def test_ban_xuat_mot_phan_khong_dong_khach_vang_mat(conn, batch):
    """File chỉ chứa vài khách KHÔNG được hiểu là các khách khác đã biến mất."""
    two = pd.concat([_df(), _df()], ignore_index=True)
    two.loc[1, "customer_code"] = "000000000002"
    customer.load(conn, two, D1, batch(1))
    r = customer.load(conn, _df(), D2, batch(2))  # chỉ 1 khách trong lần nạp thứ hai
    assert r["inserted"] == 0 and r["unchanged"] == 1
    n_current = conn.execute(
        "SELECT count(*) FROM core.dim_customer WHERE is_current"
    ).fetchone()[0]
    assert n_current == 2  # khách vắng mặt vẫn còn is_current=true


def test_gia_tri_rong_on_dinh_qua_cac_lan_nap(conn, batch):
    """Cột để trống (NaN khi đọc Excel) không được coi là 'đổi' ở lần nạp sau."""
    row = _df()
    row.loc[0, "phone"] = float("nan")
    row.loc[0, "address"] = float("nan")
    r1 = customer.load(conn, row, D1, batch(1))
    assert r1["inserted"] == 1
    row2 = _df()
    row2.loc[0, "phone"] = float("nan")
    row2.loc[0, "address"] = float("nan")
    r2 = customer.load(conn, row2, D2, batch(2))
    assert r2["inserted"] == 0 and r2["unchanged"] == 1
