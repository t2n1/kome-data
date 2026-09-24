"""Giai đoạn 2 — API màn Khách hàng (danh sách · hồ sơ 360° · bản đồ) và ảnh
chụp danh bạ. Đặc tả: docs/superpowers/specs/2026-09-23-giai-doan-2-khach-hang-design.md."""
from datetime import date, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from kome import ho_so_khach as HSK
from kome import khach_hang as KH
from kome.web import anh_chup
from kome.web.app import create_app
from tests.test_khach_hang import HOM_NAY, _ho_so_khach, _mua, _mua_deu, _neo


@pytest.fixture
def c(test_db_url):
    return TestClient(create_app(db_url=test_db_url))


def _nen(conn, batch):
    for ma, ten, sale in (("K1", "Quán Một", "0104"), ("K2", "Quán Hai", "0102"), ("K3", "Quán Ba", "0104")):
        _ho_so_khach(conn, batch, ma, ten, salesperson_code=sale)
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=40 if ma == "K3" else 1)
    _neo(conn, batch)


def _dem_luot_hoi(monkeypatch):
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    return dem


@pytest.mark.parametrize("url, tran", [
    ("/api/khach-hang/ds", 3), ("/api/khach-hang/ds?nhom=im&hang=S,A&nhan_thang=tre&sap=tb3", 3),
    ("/api/khach-hang/K1", 8), ("/api/khach-hang/K1/dong?tu=2026-07-01&den=2026-07-31", 1),
    ("/api/ban-do?chi_so=doanh_thu", 2),
])
def test_ngan_sach_luot_hoi_tung_endpoint(conn, batch, c, monkeypatch, url, tran):
    """[IMPORTANT] Nút thắt là SỐ LƯỢT HỎI (47 ms mạng mỗi lượt tới Tokyo).
    Ảnh chụp tắt trong test (conftest), nên đây là số lượt khi tính mới."""
    _nen(conn, batch)
    dem = _dem_luot_hoi(monkeypatch)
    r = c.get(url)
    assert r.status_code == 200, r.text
    assert dem["n"] <= tran, f"{url} chạy {dem['n']} lượt hỏi, trần {tran}"


def test_ho_so_goi_it_hon_tran_8(conn, batch, monkeypatch):
    """Giai đoạn 2 gộp "đã ngừng mua" vào câu mặt hàng: ho_so() còn 7 — chỗ
    trống là cố ý (CLAUDE.md)."""
    _nen(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    KH.ho_so(conn, "K1")
    assert dem["n"] <= 7


@pytest.mark.parametrize("url", ["/api/khach-hang/ds", "/api/khach-hang/K1", "/api/khach-hang/K1/dong?tu=2026-07-01&den=2026-07-02",
                                 "/api/ban-do"])
def test_chua_dang_nhap_thi_401_json(test_db_url, monkeypatch, url):
    monkeypatch.setenv("KOME_SESSION_SECRET", "bi-mat-thu-" + "x" * 32)
    r = TestClient(create_app(db_url=test_db_url)).get(url, follow_redirects=False)
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/json")


def test_ba_route_tra_vo_react(conn, c):
    for duong in ("/khach-hang", "/ban-do", "/khach-hang/BAT-KY"):
        r = c.get(duong, cookies={"kome_giao_dien": "toi"})
        assert r.status_code == 200 and 'id="goc"' in r.text and 'data-theme="toi"' in r.text, duong


def test_nhom_im_cua_danh_ba_DUNG_BANG_view_nhom_viec(conn, batch):
    """[CRITICAL] danh_ba() đọc nhánh 'im' từ `trang_thai IN TRANG_THAI_CAN_XU_LY`
    thay vì hỏi view (bớt một lần dựng khach_360) — chỉ đúng chừng nào nhánh
    đó của mart.khach_nhom_viec VẪN là đúng điều kiện ấy. Đổi view mà quên
    đây là "khách đang rời đi" có hai định nghĩa."""
    _nen(conn, batch)
    db = KH.danh_ba(conn)
    tu_db = {k["ma"] for k in db["khach"] if "im" in k["nhom"]}
    tu_view = {r[0] for r in conn.execute(
        "SELECT customer_code FROM mart.khach_nhom_viec WHERE nhom = 'im'").fetchall()}
    assert tu_db == tu_view and "K3" in tu_db
    assert KH.trang_danh_sach(db, nhom="im").so_can_xu_ly == len(tu_view)


def test_loc_thang_DUNG_BANG_nhan_cua_view(conn, batch):
    """Bộ lọc `thang` của danh sách ĐỌC nhãn mart.khach_thang_nay, so bằng."""
    _nen(conn, batch)
    for nhan in KH.NHAN_THANG:
        view = {r[0] for r in conn.execute(
            "SELECT customer_code FROM mart.khach_thang_nay WHERE nhan = %s", (nhan,)).fetchall()}
        assert {k.ma for k in KH.danh_sach(conn, thang=nhan, co=200).khach} == view, nhan


def test_hang_nhieu_gia_tri_va_chua_ai_phu_trach(conn, batch):
    _nen(conn, batch)
    _ho_so_khach(conn, batch, "K9", "Quán không ai", salesperson_code=None)
    _mua(conn, batch, "K9", HOM_NAY)
    db = KH.danh_ba(conn)
    hai = KH.trang_danh_sach(db, hang="S,A,B,C,D")
    assert hai.tong == len([k for k in db["khach"] if k["hang"]])
    t = KH.trang_danh_sach(db, sale=KH.PT_TRONG)
    assert "K9" in {k.ma for k in t.khach}
    assert KH.tong_quan(db).chua_pt == sum(1 for k in db["khach"] if not k["co_pt"])


def test_o_kpi_la_tong_CUA_CA_NHOM_khong_chi_trang_nay(conn, batch):
    _nen(conn, batch)
    db = KH.danh_ba(conn)
    t = KH.trang_danh_sach(db, co=50)
    assert t.tong_doanh_thu == sum(k["doanh_thu"] for k in db["khach"])
    assert t.tong_dt_thang_nay == sum(k["thang_nay"] or 0 for k in db["khach"])


def test_anh_chup_danh_ba_KHONG_cu_di_khi_ghi_tiep_xuc(conn, batch, monkeypatch):
    """Danh bạ không đọc bảng `app` nào -> phiên bản chỉ theo dữ liệu nạp: ghi
    một cuộc gọi không bắt tính lại ~6 s danh bạ. Hồ sơ thì CÓ đọc nhật ký ->
    phiên bản đầy đủ, ghi xong là hồ sơ tính lại."""
    monkeypatch.setenv("KOME_ANH_CHUP", "1")
    _nen(conn, batch)
    pb_nap = lambda: conn.execute(f"SELECT {anh_chup._PHIEN_BAN_NAP}").fetchone()[0]
    pb_du = lambda: conn.execute(f"SELECT {anh_chup._PHIEN_BAN}").fetchone()[0]
    truoc = (pb_nap(), pb_du())
    conn.execute("INSERT INTO app.nhat_ky_tiep_xuc (customer_code, kieu, ket_qua, noi_dung) VALUES ('K1','goi','tot','x')")
    conn.commit()
    assert pb_nap() == truoc[0] and pb_du() != truoc[1]
    _, pb1 = anh_chup.lay_du_lieu(conn, anh_chup.KHOA_DANH_BA, KH.danh_ba, chi_nap=True)
    goc = KH.danh_ba
    monkeypatch.setattr(KH, "danh_ba", lambda c: pytest.fail("trúng ảnh chụp mà vẫn tính lại"))
    _, pb2 = anh_chup.lay_du_lieu(conn, anh_chup.KHOA_DANH_BA, KH.danh_ba, chi_nap=True)
    assert pb1 == pb2
    monkeypatch.setattr(KH, "danh_ba", goc)


def test_ty_trong_va_bien_theo_nganh_la_TY_SO_CUA_CAC_TONG():
    mh = [{"nganh": "A", "doanh_thu": 1000, "lai_gop": 500}, {"nganh": "A", "doanh_thu": 9000, "lai_gop": 900},
          {"nganh": "B", "doanh_thu": 10000, "lai_gop": 1000}, {"nganh": "C", "doanh_thu": -300, "lai_gop": -30}]
    g = HSK.theo_nganh(mh)
    a = next(x for x in g["nganh"] if x["nganh"] == "A")
    assert a["bien"] == pytest.approx(1400 / 10000)       # không phải (0,5 + 0,1) / 2
    assert a["ty_trong"] == pytest.approx(0.5)
    # Ngành doanh thu âm không vẽ được — phải NÓI RA số tiền bị bỏ (bất biến cây ô).
    assert g["so_nganh_khong_ve"] == 1 and g["khong_ve"] == -300


def test_tuan_26_va_cua_so_30_ngay_tinh_tu_MOC_du_lieu():
    moc = date(2026, 7, 12)
    ngay = [{"ngay": moc, "doanh_thu": 100}, {"ngay": moc - timedelta(days=6), "doanh_thu": 50},
            {"ngay": moc - timedelta(days=7), "doanh_thu": 10}, {"ngay": moc - timedelta(days=40), "doanh_thu": 7}]
    t = HSK.tuan_26(ngay, moc)
    assert len(t) == 26 and t[-1]["doanh_thu"] == 150 and t[-2]["doanh_thu"] == 10
    assert HSK.cua_so(ngay, moc, 30, 0) == 160 and HSK.cua_so(ngay, moc, 60, 30) == 7


def test_ho_so_api_du_cac_khoi(conn, batch, c):
    _nen(conn, batch)
    h = c.get("/api/khach-hang/K1").json()
    assert h["khach"]["ma"] == "K1" and h["hom_nay"] == HOM_NAY.isoformat()
    assert len(h["tuan"]) == 26 and h["thang"] and h["mat_hang"]
    assert h["ho_so"]["ten_phu_trach"] == "TRAN THI LAN THANH"
    assert h["thang_nay"]["nhan"] in KH.NHAN_THANG
    d = c.get("/api/khach-hang/K1/dong?tu=2026-07-01&den=2026-07-31").json()
    assert d["dong"] and all("2026-07-01" <= x["ngay"] <= "2026-07-31" for x in d["dong"])
    assert c.get("/api/khach-hang/K1/dong?tu=2026-01-01&den=2026-07-31").status_code == 400
