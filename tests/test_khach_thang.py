"""Nhìn theo tháng (036): khách mua đều mà tháng này chưa mua.

Một định nghĩa (`mart.khach_thang_nay.nhan`), ba chỗ đọc (khối Tổng quan,
cột thứ tư của /lien-he, việc hôm nay) — các test dưới đây canh để ba chỗ đó
trả CÙNG một tập khách, và các ca biên của "đến cùng ngày" đúng như đặc tả.
"""
from datetime import date

from fastapi.testclient import TestClient

from kome import khach_thang as KT
from kome import lien_he as LH
from kome.tuoi_du_lieu import hom_nay_o_nhat
from kome.web.app import create_app
from tests.test_khach_hang import _ho_so_khach, _mua_nhieu

T = 110_000


def _nhan(conn) -> dict[str, str]:
    return dict(conn.execute(
        "SELECT customer_code, nhan FROM mart.khach_thang_nay").fetchall())


def _nen_giua_thang(conn, batch):
    """Mốc 12/7/2026 (neo Z). Mỗi khách một ca:
    A mua ngày 4–8 cả ba tháng trước            -> tre
    B mua ngày 25–27 cả ba tháng trước          -> chua_toi_ngay (thường mua cuối tháng)
    C đã có đơn 3/7                             -> da_mua
    D chỉ mua một lần 3/6                       -> khac
    E ※廃業※, mua như A                        -> khong_goi (xét TRƯỚC)
    F mua như A, tháng 7 chỉ có 赤伝 (số âm)    -> tre (hàng trả lại không phải đơn mua)
    G 2/3 tháng, chỉ 1 tháng có đơn trước ngày 12 -> chua_toi_ngay"""
    for ma, ten, sale in (("A", "An", "0104"), ("B", "Binh", "0104"), ("C", "Cuong", "0104"),
                          ("D", "Dung", "0104"), ("E", "※廃業※Em", "0104"),
                          ("F", "Phuc", "0102"), ("G", "Giang", "0104")):
        _ho_so_khach(conn, batch, ma, ten, salesperson_code=sale)
    d = date
    _mua_nhieu(conn, batch, [
        ("A", d(2026, 4, 5), T, "X"), ("A", d(2026, 5, 6), T, "X"), ("A", d(2026, 6, 8), T, "X"),
        ("B", d(2026, 4, 25), T, "X"), ("B", d(2026, 5, 26), T, "X"), ("B", d(2026, 6, 27), T, "X"),
        ("C", d(2026, 5, 5), T, "X"), ("C", d(2026, 6, 5), T, "X"), ("C", d(2026, 7, 3), T, "X"),
        ("D", d(2026, 6, 3), T, "X"),
        ("E", d(2026, 4, 5), T, "X"), ("E", d(2026, 5, 6), T, "X"), ("E", d(2026, 6, 8), T, "X"),
        ("F", d(2026, 5, 5), 3 * T, "X"), ("F", d(2026, 6, 5), 3 * T, "X"),
        ("F", d(2026, 7, 2), -T, "X"),
        ("G", d(2026, 5, 5), T, "X"), ("G", d(2026, 6, 20), T, "X"),
        ("Z", d(2026, 7, 12), T, "X"),
    ])


def test_nhan_giua_thang_dung_tung_ca(conn, batch):
    _nen_giua_thang(conn, batch)
    n = _nhan(conn)
    assert {k: n[k] for k in "ABCDEFG"} == {
        "A": "tre", "B": "chua_toi_ngay", "C": "da_mua", "D": "khac",
        "E": "khong_goi", "F": "tre", "G": "chua_toi_ngay"}


def test_phieu_do_van_tinh_vao_doanh_thu(conn, batch):
    """Luật 赤伝: không lọc bỏ — tháng chỉ có phiếu đỏ không phải tháng có mua,
    nhưng số tiền âm vẫn nằm trong doanh thu tháng."""
    _nen_giua_thang(conn, batch)
    dt = conn.execute("""SELECT dt_thang_nay, dt_tb_3_thang FROM mart.khach_thang_nay
                          WHERE customer_code = 'F'""").fetchone()
    assert dt[0] < 0
    assert dt[1] == round(2 * (3 * T - 3 * T // 11) / 3)


def test_moc_la_NGAY_CUOI_thang_ngan_thi_tinh_tron_thang_truoc(conn, batch):
    """[IMPORTANT] Mốc 30/6 là tháng đã hết: khách thường mua ngày 31 không
    phải "chưa tới ngày". Mốc 29/6 thì đúng là chưa tới."""
    _ho_so_khach(conn, batch, "H", "Hoa")
    _mua_nhieu(conn, batch, [("H", date(2026, 3, 31), T, "X"), ("H", date(2026, 5, 31), T, "X"),
                             ("Z", date(2026, 6, 30), T, "X")])
    assert _nhan(conn)["H"] == "tre"


def test_moc_29_6_khach_mua_ngay_31_la_chua_toi_ngay(conn, batch):
    _ho_so_khach(conn, batch, "H", "Hoa")
    _mua_nhieu(conn, batch, [("H", date(2026, 3, 31), T, "X"), ("H", date(2026, 5, 31), T, "X"),
                             ("Z", date(2026, 6, 29), T, "X")])
    assert _nhan(conn)["H"] == "chua_toi_ngay"


def test_moc_31_kep_thang_30_ngay(conn, batch):
    """Mốc 31/7: đơn ngày 30/6 là "đến cùng ngày" — tháng ngắn tự kẹp."""
    _ho_so_khach(conn, batch, "H", "Hoa")
    _mua_nhieu(conn, batch, [("H", date(2026, 4, 30), T, "X"), ("H", date(2026, 6, 30), T, "X"),
                             ("Z", date(2026, 7, 31), T, "X")])
    assert _nhan(conn)["H"] == "tre"


def test_khoi_tong_quan_dem_TOAN_CONG_TY_danh_sach_theo_sale(conn, batch):
    _nen_giua_thang(conn, batch)
    tat_ca = KT.chua_mua(conn)
    assert {k["ma"] for k in tat_ca["khach"]} == {"A", "F"}
    assert tat_ca["khach"][0]["ma"] == "F"          # TB/tháng lớn hơn đứng trước
    assert tat_ca["thang"] == "2026-07" and tat_ca["ngay_moc"] == "2026-07-12"
    rieng = KT.chua_mua(conn, sale="0104")
    assert {k["ma"] for k in rieng["khach"]} == {"A"}
    assert rieng["dem"] == tat_ca["dem"]
    assert tat_ca["dem"]["tre"] == 2 and tat_ca["dem"]["chua_toi_ngay"] == 2


def test_ba_cho_doc_tra_CUNG_MOT_tap_khach(conn, batch):
    """[CRITICAL] Khối Tổng quan, cột tháng của /lien-he và view phải cùng một
    tập — một định nghĩa, không phải ba bản chép."""
    _nen_giua_thang(conn, batch)
    view = {m for m, n in _nhan(conn).items() if n == "tre"}
    khoi = {k["ma"] for k in KT.chua_mua(conn)["khach"]}
    ds = LH.danh_sach(conn, hom_nay_o_nhat())
    cot = next(c for c in ds.cot if c.ly_do == LH.COT_THANG)
    # Cột tháng bỏ khách đã ở cột nhịp (A đang 'sắp đến hạn'): thẻ cột tháng
    # + khách 'tre' nằm ở cột khác = đúng tập của view, và `trung` đếm đúng.
    o_cot_khac = {t.ma for c in ds.cot if c.ly_do != LH.COT_THANG for t in c.the} & view
    assert view == khoi == {t.ma for t in cot.the} | o_cot_khac
    assert o_cot_khac == {"A"} and cot.trung == 1


def test_cot_thang_khong_lap_khach_da_o_cot_nhip(conn, batch):
    """Khách vừa 'quá hạn' theo nhịp vừa 'tre' theo tháng chỉ hiện một lần —
    ở cột nhịp — và cột tháng nói ra là đã bỏ bao nhiêu khách."""
    _ho_so_khach(conn, batch, "Q", "Qua")
    # Nhịp 10 ngày, lần cuối 21/6 -> im 40 ngày tới mốc 31/7 (4x nhịp: lâu không
    # mua), và 3/3 tháng trước có đơn, tháng 7 chưa -> cũng 'tre'.
    _mua_nhieu(conn, batch, [("Q", date(2026, 4, 20), T, "X"), ("Q", date(2026, 5, 22), T, "X"),
                             ("Q", date(2026, 6, 1), T, "X"), ("Q", date(2026, 6, 11), T, "X"),
                             ("Q", date(2026, 6, 21), T, "X"), ("Z", date(2026, 7, 31), T, "X")])
    assert _nhan(conn)["Q"] == "tre"
    ds = LH.danh_sach(conn, hom_nay_o_nhat())
    o = [c.ly_do for c in ds.cot for t in c.the if t.ma == "Q"]
    assert o and LH.COT_THANG not in o
    assert next(c for c in ds.cot if c.ly_do == LH.COT_THANG).trung == 1


def test_trang_lien_he_hien_cot_thang(conn, batch, test_db_url):
    _nen_giua_thang(conn, batch)
    r = TestClient(create_app(db_url=test_db_url)).get("/lien-he?tat_ca=1")
    assert r.status_code == 200
    assert "Mua đều, tháng này chưa" in r.text and "/tháng" in r.text
    assert "im None" not in r.text
