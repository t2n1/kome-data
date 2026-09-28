"""Mùa vụ sản phẩm (/mua-vu, migration 058) — đặc tả 2026-09-29-mua-vu-san-pham-design.md."""
from datetime import date, timedelta

import pytest

from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY

KHACH = "202607010001"


def _hang(conn, batch):
    b = batch(778_101)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, kind_code, kind_name, food_category_name, batch_id)
           VALUES ('XT07', 'Bánh phở', '0', '有形', '食材（常温）＿VNM', %s),
                  ('MKT18', 'Poster', '0', '有形', '雑貨_VNM', %s),
                  ('FEE1', '代引手数料', '1', '無形', '', %s),
                  ('FEE2', 'Phí lạ trong POSM', '1', '無形', '雑貨_VNM', %s)""",
        (b, b, b, b))
    conn.commit()
    _ho_so_khach(conn, batch, KHACH, "Quán A")


def _dong(conn):
    return {(r[0], r[1]): r[2:] for r in conn.execute(
        "SELECT ma, ngay, doanh_thu_thuan, lai_gop, so_luong FROM mart.mua_vu_ngay")}


def test_phi_va_posm_gop_ve_ma_gia_phi_xet_truoc(conn, batch):
    _hang(conn, batch)
    d = HOM_NAY - timedelta(days=2)
    for hang in ("XT07", "MKT18", "FEE1", "FEE2"):
        _mua(conn, batch, KHACH, d, hang=hang)
    _neo(conn, batch)
    dong = _dong(conn)
    assert ("XT07", d) in dong
    assert ("MKT18", d) not in dong and ("FEE1", d) not in dong and ("FEE2", d) not in dong
    assert dong[("__phi", d)][0] == 2 * 100_000       # FEE1 + FEE2 (phí xét trước POSM)
    assert dong[("__tang", d)][0] == 100_000          # MKT18


def test_tong_moi_ngay_KHONG_mat_tien_so_voi_ban_den_moc(conn, batch):
    _hang(conn, batch)
    for i, hang in enumerate(("XT07", "MKT18", "FEE1", "KHONG_CO_MASTER")):
        _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=i), hang=hang)
    _neo(conn, batch)
    a = dict(conn.execute("SELECT ngay, sum(doanh_thu_thuan) FROM mart.mua_vu_ngay GROUP BY 1"))
    b = dict(conn.execute("SELECT sales_date, sum(amount - tax_amount) FROM mart.ban_den_moc GROUP BY 1"))
    assert a == b


def test_cong_theo_thang_BANG_san_pham_theo_thang(conn, batch):
    _hang(conn, batch)
    for i in range(6):
        _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=9 * i), hang="XT07")
    _neo(conn, batch)
    a = {r[0]: r[1:] for r in conn.execute(
        """SELECT to_char(ngay, 'YYYY-MM'), sum(doanh_thu_thuan), sum(lai_gop), sum(so_luong)
           FROM mart.mua_vu_ngay WHERE ma = 'XT07' GROUP BY 1""")}
    b = {r[0]: r[1:] for r in conn.execute(
        """SELECT thang, doanh_thu_thuan, lai_gop, so_luong
           FROM mart.san_pham_theo_thang WHERE product_code = 'XT07'""")}
    assert a == b and a


def test_phieu_do_giu_so_am_va_ma_noi_bo_bi_bo(conn, batch):
    _hang(conn, batch)
    d = HOM_NAY - timedelta(days=1)
    _mua(conn, batch, KHACH, d, tien=-55_000, tax=-5_000, gp=-15_000, hang="XT07")
    _mua(conn, batch, "009000000001", d - timedelta(days=1), hang="XT07")   # nhân viên (044)
    _neo(conn, batch)
    dong = _dong(conn)
    assert dong[("XT07", d)][0] == -50_000
    assert ("XT07", d - timedelta(days=1)) not in dong


def test_moc_lui_cat_dung(conn, batch):
    _hang(conn, batch)
    _mua(conn, batch, KHACH, date(2026, 7, 1), hang="XT07")
    _neo(conn, batch)
    with conn.transaction():
        conn.execute("SELECT set_config('kome.moc', '2026-07-10', true)")
        ngay = {r[0] for r in conn.execute("SELECT ngay FROM mart.mua_vu_ngay")}
    assert max(ngay) <= date(2026, 7, 10)
