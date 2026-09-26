"""049 — hàng tặng POSM (ngành OBC 雑貨_VNM: poster, túi, ly… doanh thu ¥0) KHÔNG phải
sản phẩm, và là nhóm RIÊNG — không gộp vào "Phí & điều chỉnh" (chủ DN chốt 2026-09-26).
Giá vốn của chúng VẪN trong tổng lãi gộp (phương án A của 048)."""
from datetime import timedelta

import pytest

from kome import ban_khoang as BK
from kome import bao_cao as BC
from kome import khach_hang as KH
from kome import khoang_xem as KX
from tests.test_khach_hang import HOM_NAY, _ho_so_khach, _mua, _neo

POSM = "MKT18"          # Poster Ruou tao meo NQT -v2.0
HANG = "XT07"
KHACH = "202607010001"


def _du_lieu(conn, batch):
    b = batch(777_101)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, kind_code, kind_name, food_category_name, batch_id)
           VALUES (%s, 'Poster Ruou tao meo NQT -v2.0', '0', '有形', '雑貨_VNM', %s),
                  (%s, 'Bánh phở', '0', '有形', '食材（常温）＿VNM', %s),
                  ('XT09', 'Nước mắm', '0', '有形', '調味料_VNM', %s)""",
        (POSM, b, HANG, b, b))
    conn.commit()
    _ho_so_khach(conn, batch, KHACH, "Quán A")
    for i in range(4):   # đủ nhịp để POSM thành "đã ngừng mua" nếu lọt vào
        _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=40 + 7 * i),
             tien=0, tax=0, gp=-1_500, hang=POSM)
    _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=2), hang=HANG)
    _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=3), tien=0, tax=0, gp=-1_500, hang=POSM)
    _neo(conn, batch)


@pytest.mark.parametrize("nganh,tang", [
    ("雑貨_VNM", True), (" 雑貨_VNM ", True),
    ("調味料_VNM", False), ("", False), (None, False),
])
def test_hang_tang_dinh_nghia_MOT_LAN_theo_nganh(conn, nganh, tang):
    assert conn.execute("SELECT mart.la_hang_tang(%s)", (nganh,)).fetchone()[0] is tang


def test_nhan_nganh_hang_tang_khop_hang_python_va_phi_xet_truoc(conn):
    assert conn.execute("SELECT mart.ten_nganh('雑貨_VNM', 'MKT18', '0')").fetchone()[0] \
        == BC.NGANH_HANG_TANG
    # một mã 無形 lỡ nằm trong 雑貨_VNM vẫn là phí — không vừa phí vừa tặng
    assert conn.execute("SELECT mart.ten_nganh('雑貨_VNM', 'X', '1'), "
                        "mart.la_dong_hang_tang('X', '1', '雑貨_VNM')").fetchone() \
        == (BC.NGANH_PHI, False)
    assert BC.NGANH_HANG_TANG != BC.NGANH_PHI


def test_posm_ra_khoi_danh_muc_nhung_gia_von_VAN_trong_tong(conn, batch):
    _du_lieu(conn, batch)
    ma_sp = {r[0] for r in conn.execute("SELECT product_code FROM mart.san_pham_360")}
    assert HANG in ma_sp and POSM not in ma_sp
    thang = f"{HOM_NAY:%Y-%m}"
    lg_tong = conn.execute("SELECT lai_gop FROM mart.ban_theo_thang WHERE thang = %s",
                           (thang,)).fetchone()[0]
    nganh = dict(conn.execute(
        "SELECT nganh, lai_gop FROM mart.ban_theo_nganh_thang WHERE thang = %s",
        (thang,)).fetchall())
    assert nganh[BC.NGANH_HANG_TANG] < 0
    assert sum(nganh.values()) == lg_tong


def test_posm_khong_phai_mat_hang_cua_khach_va_khong_goi_y(conn, batch):
    _du_lieu(conn, batch)
    assert conn.execute("SELECT count(*) FROM mart.khach_mat_hang WHERE product_code = %s",
                        (POSM,)).fetchone()[0] == 0
    h = KH.ho_so(conn, KHACH)
    assert POSM not in {m["ma"] for m in h.mat_hang}
    _ho_so_khach(conn, batch, "202607010002", "Quán B")
    _mua(conn, batch, "202607010002", HOM_NAY - timedelta(days=5), hang="XT09")
    g = KH.ho_so(conn, "202607010002").goi_y
    assert g, "khối gợi ý rỗng — test không kiểm được gì"
    assert POSM not in {x["ma"] for x in g}


def test_bao_cao_tach_posm_thanh_khoi_RIENG_va_doi_soat_du(conn, batch):
    _du_lieu(conn, batch)
    kx = KX.giai_conn(conn, KX.doc_tham_so(thang=f"{HOM_NAY:%Y-%m}"))
    bc = BK.tinh_bao_cao(conn, kx)
    assert POSM not in {h["ma"] for h in bc.hang_theo_nganh}
    assert BC.NGANH_HANG_TANG not in {n.nganh for n in bc.nganh_ky}
    assert [d["ma"] for d in bc.hang_tang.dong] == [POSM]
    assert POSM not in {d["ma"] for d in bc.phi.dong}
    assert bc.hang_tang.dong[0]["so_luong"] > 0
    tong = conn.execute("SELECT lg FROM mart.tong_khoang(%s, %s)", (kx.tu, kx.den)).fetchone()[0]
    assert sum(n.lai_gop for n in bc.nganh_ky) + bc.phi.lai_gop + bc.hang_tang.lai_gop == tong
    assert sum(d["lai_gop"] for d in bc.hang_tang.dong) == bc.hang_tang.lai_gop


def test_bao_cao_ky_cung_tach_posm(conn, batch):
    _du_lieu(conn, batch)
    bc = BC.tinh_bao_cao(conn, None)
    assert POSM not in {h["ma"] for h in bc.hang_theo_nganh}
    assert BC.NGANH_HANG_TANG not in {n.nganh for n in bc.nganh_ky}
    assert bc.hang_tang.lai_gop < 0


def test_mat_hang_theo_khoang_cua_khach_danh_dau_posm(conn, batch):
    _du_lieu(conn, batch)
    kx = KX.giai_conn(conn, KX.doc_tham_so(thang=f"{HOM_NAY:%Y-%m}"))
    r = BK.cua_khach(conn, kx, KHACH)
    co = {m["ma"]: (m["la_phi"], m["la_hang_tang"]) for m in r["mat_hang"]}
    assert co == {HANG: (False, False), POSM: (False, True)}
