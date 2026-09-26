"""048 — phí & điều chỉnh (代引手数料, 配送料, 値引き/クーポン — OBC 無形 — và dòng
không mã hàng) KHÔNG phải sản phẩm, nhưng tiền của chúng VẪN nằm trong tổng doanh
thu (chủ DN chọn phương án A, 2026-09-26)."""
from datetime import timedelta

import pytest

from kome import ban_khoang as BK
from kome import bao_cao as BC
from kome import khach_hang as KH
from kome import khoang_xem as KX
from tests.test_khach_hang import HOM_NAY, _ho_so_khach, _mua, _neo

PHI = "000000000001"        # 代引手数料300
HANG = "XT07"


def _master(conn, batch):
    b = batch(777_001)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, kind_code, kind_name, food_category_name, batch_id)
           VALUES (%s, '代引手数料300（２万円以上）', '1', '無形', NULL, %s),
                  (%s, 'Bánh phở', '0', '有形', '食材（常温）＿VNM', %s),
                  ('XT09', 'Nước mắm', '0', '有形', '調味料_VNM', %s)""",
        (PHI, b, HANG, b, b))
    conn.commit()


def _du_lieu(conn, batch):
    _master(conn, batch)
    _ho_so_khach(conn, batch, "202607010001", "Quán A")
    for i in range(4):   # đủ nhịp để phí có thể thành "đã ngừng mua" nếu lọt vào
        _mua(conn, batch, "202607010001", HOM_NAY - timedelta(days=40 + 7 * i),
             tien=330, tax=30, gp=300, hang=PHI)
    _mua(conn, batch, "202607010001", HOM_NAY - timedelta(days=2), hang=HANG)
    _mua(conn, batch, "202607010001", HOM_NAY - timedelta(days=3), tien=330, tax=30,
         gp=300, hang=PHI)
    _neo(conn, batch)


@pytest.mark.parametrize("ma,kind,phi", [
    ("000000000001", "1", True), ("000000200010", "1", True),
    ("", None, True), (None, None, True),          # dòng làm tròn (端数) không mã
    ("XT07", "0", False), ("XT07", None, False),   # mã chưa có trong danh mục: không đoán
])
def test_phi_dieu_chinh_dinh_nghia_MOT_LAN_o_mart(conn, ma, kind, phi):
    assert conn.execute("SELECT mart.la_phi_dieu_chinh(%s, %s)", (ma, kind)).fetchone()[0] is phi


def test_nhan_nganh_phi_khop_hang_python(conn):
    assert conn.execute("SELECT mart.ten_nganh(NULL, %s, '1')", (PHI,)).fetchone()[0] == BC.NGANH_PHI
    assert conn.execute("SELECT mart.ten_nganh(NULL, 'X', '0')").fetchone()[0] == BC.NGANH_TRONG


def test_phi_ra_khoi_danh_muc_san_pham_nhung_VAN_trong_tong_doanh_thu(conn, batch):
    _du_lieu(conn, batch)
    ma_sp = {r[0] for r in conn.execute("SELECT product_code FROM mart.san_pham_360")}
    assert HANG in ma_sp and PHI not in ma_sp
    tong = conn.execute("SELECT doanh_thu_thuan FROM mart.ban_theo_thang WHERE thang = %s",
                        (f"{HOM_NAY:%Y-%m}",)).fetchone()[0]
    phi_thang = conn.execute(
        """SELECT coalesce(sum(doanh_thu_thuan), 0) FROM mart.dong_ban
            WHERE product_code = %s AND thang = %s""", (PHI, f"{HOM_NAY:%Y-%m}")).fetchone()[0]
    assert phi_thang > 0
    assert tong == 100_000 + 100_000 + phi_thang     # hàng + _neo + phí: phương án A
    nganh = dict(conn.execute(
        "SELECT nganh, doanh_thu_thuan FROM mart.ban_theo_nganh_thang WHERE thang = %s",
        (f"{HOM_NAY:%Y-%m}",)).fetchall())
    assert nganh[BC.NGANH_PHI] == phi_thang
    assert sum(nganh.values()) == tong


def test_phi_khong_phai_mat_hang_cua_khach(conn, batch):
    _du_lieu(conn, batch)
    assert conn.execute("SELECT count(*) FROM mart.khach_mat_hang WHERE product_code = %s",
                        (PHI,)).fetchone()[0] == 0
    h = KH.ho_so(conn, "202607010001")
    assert PHI not in {m["ma"] for m in h.mat_hang}
    assert PHI not in {g["ma"] for g in h.goi_y}


def test_goi_y_khong_de_xuat_phi_cho_khach_chua_tung_tra_phi(conn, batch):
    """配送料 có lãi gộp = doanh thu (ty_suat 100%) — lọt vào là đứng đầu gợi ý."""
    _du_lieu(conn, batch)
    _ho_so_khach(conn, batch, "202607010002", "Quán B")
    _mua(conn, batch, "202607010002", HOM_NAY - timedelta(days=5), hang="XT09")
    h = KH.ho_so(conn, "202607010002")
    assert h.goi_y, "khối gợi ý rỗng — test không kiểm được gì"
    assert PHI not in {g["ma"] for g in h.goi_y}
    assert "XT09" in {g["ma"] for g in KH.ho_so(conn, "202607010001").goi_y}


def test_bao_cao_tach_phi_thanh_khoi_rieng_va_doi_soat_du(conn, batch):
    _du_lieu(conn, batch)
    kx = KX.giai_conn(conn, KX.doc_tham_so(thang=f"{HOM_NAY:%Y-%m}"))
    bc = BK.tinh_bao_cao(conn, kx)
    assert PHI not in {h["ma"] for h in bc.hang_theo_nganh}
    assert PHI not in {h["ma"] for h in bc.hang}
    assert BC.NGANH_PHI not in {n.nganh for n in bc.nganh_ky}
    assert BC.NGANH_PHI not in {n.nganh for n in bc.nganh_thang}
    assert [d["ma"] for d in bc.phi.dong] == [PHI]
    tong = conn.execute("SELECT dt FROM mart.tong_khoang(%s, %s)", (kx.tu, kx.den)).fetchone()[0]
    assert sum(n.doanh_thu for n in bc.nganh_ky) + bc.phi.doanh_thu == tong
    assert sum(d["doanh_thu"] for d in bc.phi.dong) == bc.phi.doanh_thu   # từng mã = tổng nhóm


def test_bao_cao_ky_cung_tach_phi(conn, batch):
    _du_lieu(conn, batch)
    bc = BC.tinh_bao_cao(conn, None)
    assert PHI not in {h["ma"] for h in bc.hang_theo_nganh}
    assert BC.NGANH_PHI not in {n.nganh for n in bc.nganh_ky}
    assert bc.phi.doanh_thu > 0


def test_mat_hang_theo_khoang_cua_khach_danh_dau_phi(conn, batch):
    _du_lieu(conn, batch)
    kx = KX.giai_conn(conn, KX.doc_tham_so(thang=f"{HOM_NAY:%Y-%m}"))
    r = BK.cua_khach(conn, kx, "202607010001")
    co = {m["ma"]: m["la_phi"] for m in r["mat_hang"]}
    assert co == {HANG: False, PHI: True}
    # vẫn cộng đúng bằng tổng khoảng
    assert sum(m["doanh_thu"] for m in r["mat_hang"]) == r["tong"]["dt"]
