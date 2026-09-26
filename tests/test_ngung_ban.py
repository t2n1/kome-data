"""050 — hàng ※終売※ (ngừng kinh doanh) không phân tích, không hiện ở bất kỳ đâu — TRỪ khi
còn tồn (chủ DN chốt 2026-09-26). Tiền của hàng đó đã bán VẪN trong mọi tổng và trong ngành
thật của nó (cùng phương án A của 048/049)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from kome import ban_khoang as BK
from kome import bao_cao as BC
from kome import khach_hang as KH
from kome import khoang_xem as KX
from kome import san_pham as SP
from kome.web.app import create_app
from tests.test_khach_hang import HOM_NAY, _ho_so_khach, _mua, _neo
from tests.test_san_pham import _ton_ngay

NGUNG = "BA11"       # ※終売※, hết tồn -> ẩn
NGUNG_TON = "VF03"   # ※終売※, còn tồn -> hiện, "bán nốt"
HANG = "XT07"
KHACH = "202607010001"
KHACH_B = "202607010002"


def _du_lieu(conn, batch):
    b = batch(777_201)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, kind_code, kind_name, food_category_name,
              rank_code, rank_name, batch_id)
           VALUES (%s, '※終売※Lau rieu cua (230g x 40 packs)', '0', '有形', '調味料_VNM',
                   '0999', '※終売※', %s),
                  (%s, '※終売※[ VIFON ] Banh Da Cua', '0', '有形', 'インスタント食品_VNM',
                   '0999', '※終売※', %s),
                  (%s, 'Bánh phở', '0', '有形', '調味料_VNM', '0002', 'Aランク', %s),
                  ('XT09', 'Nước mắm', '0', '有形', '調味料_VNM', '0002', 'Aランク', %s)""",
        (NGUNG, b, NGUNG_TON, b, HANG, b, b))
    conn.commit()
    _ho_so_khach(conn, batch, KHACH, "Quán A")
    for i in range(4):   # đủ nhịp để thành "mặt hàng mua đều" / "đã ngừng mua" nếu lọt vào
        _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=40 + 7 * i), hang=NGUNG)
        _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=41 + 7 * i), hang=NGUNG_TON)
    _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=2), hang=HANG)
    _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=3), hang=NGUNG)
    _neo(conn, batch)
    # Ảnh chụp tồn mới nhất (HOM_NAY): NGUNG không có dòng, NGUNG_TON còn ít hàng.
    _ton_ngay(conn, batch, NGUNG_TON, HOM_NAY, sl=1)
    _ton_ngay(conn, batch, HANG, HOM_NAY, sl=500)


@pytest.mark.parametrize("hang,ten,ngung", [
    ("0999", "Pho", True), (" 0999 ", None, True), ("", "※終売※Pho", True),
    (None, "abc ※終売※ Pho", True), ("0001", "Pho", False), (None, None, False),
])
def test_ngung_ban_dinh_nghia_MOT_LAN_mot_trong_hai_dau(conn, hang, ten, ngung):
    assert conn.execute("SELECT mart.la_ngung_ban(%s, %s)", (hang, ten)).fetchone()[0] is ngung


def test_het_ton_ra_khoi_danh_muc_con_ton_thi_hien_va_mang_co(conn, batch):
    _du_lieu(conn, batch)
    sp = {r[0]: r[1] for r in conn.execute("SELECT product_code, ngung_ban FROM mart.san_pham_360")}
    assert NGUNG not in sp
    assert sp[NGUNG_TON] is True and sp[HANG] is False
    dm = {m["ma"]: m for m in SP.danh_muc(conn)["ma"]}
    assert NGUNG not in dm and dm[NGUNG_TON]["ngung_ban"] is True


def test_con_ton_it_KHONG_BAO_GIO_la_sap_thieu(conn, batch):
    _du_lieu(conn, batch)
    tt, du = conn.execute("SELECT trang_thai, du_ban_ngay FROM mart.san_pham_360 WHERE product_code = %s",
                          (NGUNG_TON,)).fetchone()
    assert du is not None and du < 14, "dữ liệu không đủ ít tồn — test không kiểm được gì"
    assert tt != "sap_thieu"


def test_tien_VAN_trong_tong_va_trong_nganh_that(conn, batch):
    _du_lieu(conn, batch)
    thang = f"{HOM_NAY:%Y-%m}"
    dt_tong = conn.execute("SELECT doanh_thu_thuan FROM mart.ban_theo_thang WHERE thang = %s",
                           (thang,)).fetchone()[0]
    dt_ngung = conn.execute(
        "SELECT sum(amount - tax_amount) FROM core.fact_sales_line "
        "WHERE product_code = %s AND to_char(sales_date, 'YYYY-MM') = %s", (NGUNG, thang)).fetchone()[0]
    assert dt_ngung > 0
    nganh = dict(conn.execute(
        "SELECT nganh, doanh_thu_thuan FROM mart.ban_theo_nganh_thang WHERE thang = %s",
        (thang,)).fetchall())
    assert sum(nganh.values()) == dt_tong
    assert "調味料_VNM" in nganh


def test_het_ton_khong_phai_mat_hang_cua_khach_va_khong_goi_y(conn, batch):
    _du_lieu(conn, batch)
    cap = {r[0] for r in conn.execute(
        "SELECT product_code FROM mart.khach_mat_hang WHERE customer_code = %s", (KHACH,))}
    assert NGUNG not in cap and NGUNG_TON in cap
    h = KH.ho_so(conn, KHACH)
    assert NGUNG not in {m["ma"] for m in h.mat_hang}
    assert NGUNG not in {m["ma"] for m in h.da_ngung_mua}
    _ho_so_khach(conn, batch, KHACH_B, "Quán B")
    _mua(conn, batch, KHACH_B, HOM_NAY - timedelta(days=5), hang="XT09")
    g = KH.ho_so(conn, KHACH_B).goi_y
    assert g, "khối gợi ý rỗng — test không kiểm được gì"
    # gợi ý là chào mã MỚI — không chào mã đã ngừng kinh doanh, kể cả còn tồn
    assert not {NGUNG, NGUNG_TON} & {x["ma"] for x in g}


def test_moc_lui_ve_luc_con_ton_thi_ma_hien_lai(conn, batch):
    _du_lieu(conn, batch)
    lui = HOM_NAY - timedelta(days=10)
    _ton_ngay(conn, batch, NGUNG, HOM_NAY - timedelta(days=20), sl=50)
    conn.execute("SELECT set_config('kome.moc', %s, true)", (lui.isoformat(),))
    assert conn.execute("SELECT count(*) FROM mart.san_pham_360 WHERE product_code = %s",
                        (NGUNG,)).fetchone()[0] == 1
    conn.rollback()
    assert conn.execute("SELECT count(*) FROM mart.san_pham_360 WHERE product_code = %s",
                        (NGUNG,)).fetchone()[0] == 0


def test_bao_cao_gop_MOT_dong_moi_nganh_va_doi_soat_du(conn, batch):
    _du_lieu(conn, batch)
    kx = KX.giai_conn(conn, KX.doc_tham_so(thang=f"{HOM_NAY:%Y-%m}"))
    bc = BK.tinh_bao_cao(conn, kx)
    ma = {h["ma"] for h in bc.hang_theo_nganh}
    assert NGUNG not in ma and HANG in ma
    assert NGUNG not in {h["ma"] for h in bc.hang} and "" not in {h["ma"] for h in bc.hang}
    gop = [h for h in bc.hang_theo_nganh if h.get("la_ngung_ban_het_ton")]
    assert len(gop) == 1 and gop[0]["ma"] == "" and gop[0]["so_ma"] == 1
    assert gop[0]["nhom"] == "調味料_VNM" and gop[0]["doanh_thu"] > 0
    assert sum(h["doanh_thu"] for h in bc.hang_theo_nganh) == sum(n.doanh_thu for n in bc.nganh_ky)


def test_bao_cao_ky_cung_gop(conn, batch):
    _du_lieu(conn, batch)
    bc = BC.tinh_bao_cao(conn, None)
    assert NGUNG not in {h["ma"] for h in bc.hang_theo_nganh}
    assert [h["so_ma"] for h in bc.hang_theo_nganh if h.get("la_ngung_ban_het_ton")] == [1]


def test_mat_hang_theo_khoang_cua_khach_danh_dau_het_ton(conn, batch):
    _du_lieu(conn, batch)
    kx = KX.giai_conn(conn, KX.doc_tham_so(thang=f"{HOM_NAY:%Y-%m}"))
    co = {m["ma"]: m["la_ngung_ban_het_ton"] for m in BK.cua_khach(conn, kx, KHACH)["mat_hang"]}
    assert co[NGUNG] is True and co[HANG] is False
    assert co.get(NGUNG_TON, False) is False


def test_mo_thang_ho_so_ma_het_ton_noi_da_ngung_kinh_doanh(conn, batch, test_db_url):
    _du_lieu(conn, batch)
    assert SP.ho_so(conn, NGUNG) is None and SP.la_ma_ngung_ban_an(conn, NGUNG)
    c = TestClient(create_app(db_url=test_db_url))
    r = c.get(f"/api/san-pham/{NGUNG}")
    assert r.status_code == 404 and "終売" in r.json()["loi"]
    r = c.get("/api/san-pham/KHONG_CO")
    assert r.status_code == 404 and "終売" not in r.json()["loi"]
    assert c.get(f"/api/san-pham/{NGUNG_TON}").status_code == 200
