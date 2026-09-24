"""Khoảng xem — đợt B: màn Khách hàng (danh sách · hồ sơ · bản đồ).

Số trong khoảng của từng khách / tỉnh phải cộng lại ĐÚNG tổng của khoảng
(`mart.tong_khoang`), và nhãn "tính đến hôm nay" (hạng, trạng thái) không đổi
theo khoảng.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from kome import ban_do as BD
from kome import ban_khoang as BK
from kome import khach_hang as KH
from kome import khoang_xem as KX
from kome.web.app import create_app
from tests.test_ban_do import _ho_so_khach, _mua


def _gieo(conn, batch):
    _ho_so_khach(conn, batch, "KA01", "Quan Tokyo", prefecture="東京都", salesperson_code="0104")
    _ho_so_khach(conn, batch, "KA02", "Quan Osaka", prefecture="大阪府", salesperson_code="0102")
    _mua(conn, batch, "KA01", date(2026, 6, 8), tien=66_000, tax=6_000)
    _mua(conn, batch, "KA01", date(2026, 7, 2), tien=110_000, tax=10_000)
    _mua(conn, batch, "KA01", date(2026, 7, 9), tien=55_000, tax=5_000, hang="XT08")
    _mua(conn, batch, "KA02", date(2026, 6, 5), tien=33_000, tax=3_000)
    # Khách chưa có trong danh mục khách (không tỉnh) — tiền vẫn phải được đếm.
    _mua(conn, batch, "KA99", date(2026, 7, 5), tien=22_000, tax=2_000)


def _kx(conn, **ts):
    return KX.giai_conn(conn, KX.doc_tham_so(**ts))


def _tong(conn, tu, den):
    return conn.execute("SELECT dt, so_khach FROM mart.tong_khoang(%s, %s)", (tu, den)).fetchone()


@pytest.fixture
def c(test_db_url):
    return TestClient(create_app(db_url=test_db_url))


def test_danh_ba_khoang_cong_lai_BANG_tong_khoang(conn, batch):
    _gieo(conn, batch)
    kx = _kx(conn)                                       # tháng 7/2026, 1 → 9
    kk = BK.danh_ba_khoang(conn, kx)
    assert kk["so_sanh"].ma == "thang_truoc"
    assert sum(v[0] or 0 for v in kk["dong"].values()) == _tong(conn, kx.tu, kx.den)[0]
    assert kk["dong"]["KA02"][0] is None and kk["dong"]["KA02"][3] == 30_000, \
        "khách chỉ mua ở dải so sánh vẫn phải có dòng (FULL JOIN)"


def test_danh_sach_theo_khoang(conn, batch, c):
    _gieo(conn, batch)
    d = c.get("/api/khach-hang/ds?nv=__moi_nguoi&thang=2026-06").json()
    t = d["trang"]
    assert d["khoang"]["nhan"] == "Tháng 6/2026"
    assert t["tong_dt_khoang"] == _tong(conn, date(2026, 6, 1), date(2026, 6, 30))[0]
    assert t["khach"][0]["ma"] in ("KA01", "KA02") and t["sap"] == "dt_khoang"
    assert [k["dt_khoang"] for k in t["khach"]] == sorted((k["dt_khoang"] for k in t["khach"]), reverse=True)
    # Chip "có mua trong khoảng" = đúng số khách có phiếu trong khoảng.
    cm = c.get("/api/khach-hang/ds?nv=__moi_nguoi&thang=2026-06&co_mua=1").json()
    assert cm["trang"]["tong"] == cm["tq"]["co_mua"] == 2
    # Nhãn tính đến hôm nay không đổi theo khoảng.
    m7 = {k["ma"]: k for k in c.get("/api/khach-hang/ds?nv=__moi_nguoi").json()["trang"]["khach"]}
    m6 = {k["ma"]: k for k in t["khach"]}
    assert all(m6[m]["trang_thai"] == m7[m]["trang_thai"] and m6[m]["hang"] == m7[m]["hang"] for m in m6)


def test_danh_sach_khoang_sai_la_400(conn, batch, c):
    _gieo(conn, batch)
    assert c.get("/api/khach-hang/ds?thang=2026-13").status_code == 400
    assert c.get("/api/khach-hang/ds?thang=2020-01").status_code == 400


def test_ho_so_theo_khoang(conn, batch, c):
    _gieo(conn, batch)
    d = c.get("/api/khach-hang/KA01/khoang").json()
    assert d["tong"]["dt"] == 150_000 and d["tong"]["so_ngay"] == 2
    assert sum(m["doanh_thu"] for m in d["mat_hang"]) == d["tong"]["dt"]
    assert sum(n["doanh_thu"] for n in d["ngay"]) == d["tong"]["dt"]
    tt = next(s for s in d["so_sanh"] if s["ma"] == "thang_truoc")
    assert (tt["dt_ck"], tt["tu"], tt["den"]) == (60_000, "2026-06-01", "2026-06-09")
    assert c.get("/api/khach-hang/KHONG_CO/khoang").json()["tong"]["dt"] == 0


def test_ban_do_theo_khoang_cong_lai_BANG_tong(conn, batch):
    _gieo(conn, batch)
    kx = _kx(conn)
    t = BD.ban_do(conn, chi_so="dt_khoang", kx=kx)
    dt, so_khach = _tong(conn, kx.tu, kx.den)
    assert t.chi_so == "dt_khoang"
    assert t.tong["dt_khoang"] == dt and t.tong["khach_mua"] == so_khach
    tokyo = next(o for o in t.o if o.ten == "東京都")
    assert (tokyo.dt_khoang, tokyo.khach_mua, tokyo.gia_tri) == (150_000, 1, 150_000)
    assert sum(o.dt_khoang for o in t.o) == dt - 20_000, "khách không tỉnh không vào ô nào"
    # Không có khoảng: chỉ số theo khoảng không hợp lệ, rơi về "khach".
    assert BD.ban_do(conn, chi_so="dt_khoang").chi_so == "khach"


def test_ban_do_theo_khoang_van_2_truy_van(conn, batch, monkeypatch):
    _gieo(conn, batch)
    kx = _kx(conn)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    BD.ban_do(conn, sale="0104", chi_so="khach_mua", kx=kx)
    assert dem["n"] == 2


def test_ghep_khoang_khong_sua_danh_ba_goc(conn, batch):
    _gieo(conn, batch)
    db = KH.danh_ba(conn)
    kk = BK.danh_ba_khoang(conn, _kx(conn))
    from kome.web.api import thanh_json
    moi = KH.ghep_khoang(db, thanh_json(kk))
    assert "dt_khoang" not in db["khach"][0] and "dt_khoang" in moi["khach"][0]
