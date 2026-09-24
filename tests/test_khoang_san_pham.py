"""Khoảng xem — đợt C: màn Sản phẩm (danh mục · hồ sơ mã)."""
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from kome import ban_khoang as BK
from kome import khoang_xem as KX
from kome.web.app import create_app
from tests.test_ban_do import _ho_so_khach, _mua


def _gieo(conn, batch):
    _ho_so_khach(conn, batch, "KA01", "Quan Tokyo")
    _ho_so_khach(conn, batch, "KA02", "Quan Osaka", prefecture="大阪府")
    _mua(conn, batch, "KA01", date(2026, 6, 8), tien=66_000, tax=6_000, hang="XT07")
    _mua(conn, batch, "KA01", date(2026, 7, 2), tien=110_000, tax=10_000, hang="XT07")
    _mua(conn, batch, "KA02", date(2026, 7, 3), tien=55_000, tax=5_000, hang="XT07")
    _mua(conn, batch, "KA02", date(2026, 6, 5), tien=33_000, tax=3_000, hang="XT09")
    _mua(conn, batch, "KA01", date(2026, 7, 9), tien=22_000, tax=2_000, hang="XT08")


@pytest.fixture
def c(test_db_url):
    return TestClient(create_app(db_url=test_db_url))


def test_danh_muc_khoang_cong_lai_BANG_tong(conn, batch):
    _gieo(conn, batch)
    kx = KX.giai_conn(conn, KX.doc_tham_so())             # 1/7 → 9/7, so 1/6 → 9/6
    d = BK.danh_muc_khoang(conn, kx)
    tong = conn.execute("SELECT dt FROM mart.tong_khoang(%s, %s)", (kx.tu, kx.den)).fetchone()[0]
    assert sum(v[0] or 0 for v in d["dong"].values()) == tong
    assert d["dong"]["XT07"][:1] == [150_000] and d["dong"]["XT07"][3] == 2 and d["dong"]["XT07"][4] == 60_000
    assert d["dong"]["XT09"][0] is None and d["dong"]["XT09"][4] == 30_000, \
        "mã chỉ bán ở dải so sánh vẫn phải có dòng (FULL JOIN)"


def test_api_danh_muc_khoang_khong_bi_route_ma_nuot(conn, batch, c):
    _gieo(conn, batch)
    r = c.get("/api/san-pham/khoang?thang=2026-06")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["khoang"]["nhan"] == "Tháng 6/2026" and d["dong"]["XT09"][0] == 30_000
    assert c.get("/api/san-pham/khoang?thang=2026-13").status_code == 400


def test_ho_so_ma_theo_khoang(conn, batch, c):
    _gieo(conn, batch)
    d = c.get("/api/san-pham/XT07/khoang").json()
    assert d["tong"]["dt"] == 150_000 and d["tong"]["so_khach"] == 2
    assert sum(k["doanh_thu"] for k in d["khach"]) == d["tong"]["dt"]
    assert [k["ma"] for k in d["khach"]] == ["KA01", "KA02"]
    assert d["dt_ss"] == 60_000 and abs(d["tang"] - (150_000 / 60_000 - 1)) < 1e-9
    assert c.get("/api/san-pham/KHONG_CO/khoang").json()["tong"]["dt"] == 0


@pytest.mark.parametrize("url", ["/api/san-pham/khoang", "/api/san-pham/XT07/khoang"])
def test_ngan_sach_luot_hoi(conn, batch, c, monkeypatch, url):
    _gieo(conn, batch)
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    assert c.get(url).status_code == 200
    assert dem["n"] <= 2, f"{url}: {dem['n']} lượt hỏi"
