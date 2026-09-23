"""Giai đoạn 3 — API của ba màn chuyển sang React: Báo cáo (/api/bao-cao),
Dự báo (/api/du-bao), Cần liên hệ (/api/lien-he).

Ba lời hứa canh ở đây (cùng nếp tests/test_khach_hang_api.py của giai đoạn 2):
  * ngân sách LƯỢT HỎI của từng màn không nới ra khi chuyển sang API — nút
    thắt là số lượt hỏi (~47 ms mạng mỗi lượt tới pooler Tokyo), không phải
    sức tính. /bao-cao <= 11 (bất biến CLAUDE.md), /du-bao 3 (bất biến đợt
    8), /lien-he 3 (bất biến đợt 7). Ảnh chụp TẮT trong test (conftest), nên
    đây là số lượt khi tính mới;
  * chưa đăng nhập -> 401 JSON, không phải 303 (fetch() đi theo 303 là nhận
    HTML của trang đăng nhập rồi nổ ở JSON.parse);
  * ba route trả vỏ React có `data-theme` từ cookie ngay trong HTML đầu tiên
    (bất biến "không có khung hình sai màu").
"""
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from kome import du_bao as DB
from kome.web.app import create_app
from tests import test_bao_cao_phan_tich_web as BCW
from tests import test_lien_he as TLH


@pytest.fixture
def c(test_db_url):
    return TestClient(create_app(db_url=test_db_url))


def _dem_luot_hoi(monkeypatch):
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    return dem


def _hai_nam_ban(conn, batch):
    """24 tháng bán liên tục (2024-08 → 2026-07), doanh thu KHÁC nhau giữa các
    tháng — đủ để /du-bao có 12 tháng dự báo với ba kịch bản khác nhau, và để
    /bao-cao có cùng kỳ, ngành, Pareto, ngân sách."""
    BCW._nganh(conn, batch, "AA01", "Đồ khô")
    for i in range(24):
        th = (8 - 1 + i) % 12 + 1
        y = 2024 + (8 - 1 + i) // 12
        for ngay in (1, 15):
            BCW._ban(conn, batch, date(y, th, ngay), "AA01",
                     khach=f"00000000{9300 + i % 3}",
                     amount=110_000 + (i % 5) * 30_000, tax=10_000, gp=30_000,
                     n=i * 100 + ngay)
    conn.execute("INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
                 "VALUES ('0104', '2026-07-01', 6000000)")
    conn.commit()


@pytest.mark.parametrize("url, tran", [
    ("/api/bao-cao", 11), ("/api/bao-cao?ky=2026", 11), ("/api/bao-cao?ky=2025", 11),
    ("/api/du-bao", 3),
])
def test_ngan_sach_luot_hoi_bao_cao_du_bao(conn, batch, c, monkeypatch, url, tran):
    """[IMPORTANT] /bao-cao <= 11 và /du-bao = 3 lượt hỏi — ĐẾM Ở ENDPOINT,
    không chỉ ở hàm tính (tests/test_bao_cao_phan_tich.py và
    tests/test_du_bao.py đếm ở hàm): mọi câu mà route API thêm vào (hình
    học biểu đồ, chỉ số phụ…) cũng phải nằm trong trần."""
    _hai_nam_ban(conn, batch)
    dem = _dem_luot_hoi(monkeypatch)
    r = c.get(url)
    assert r.status_code == 200, r.text
    assert dem["n"] <= tran, f"{url} chạy {dem['n']} lượt hỏi, trần {tran}"


@pytest.mark.parametrize("url", ["/api/lien-he", "/api/lien-he?tat_ca=1",
                                 "/api/lien-he?ly_do=qua_han", "/api/lien-he?nv=0104"])
def test_ngan_sach_luot_hoi_lien_he(conn, batch, c, monkeypatch, url):
    """[IMPORTANT] /lien-he = 3 truy vấn (bất biến đợt 7) — danh sách ưu
    tiên, hoạt động gần đây, hẹn gọi lại."""
    TLH._nen(conn, batch)
    dem = _dem_luot_hoi(monkeypatch)
    r = c.get(url)
    assert r.status_code == 200, r.text
    assert dem["n"] <= 3, f"{url} chạy {dem['n']} lượt hỏi, trần 3"


@pytest.mark.parametrize("url", ["/api/bao-cao", "/api/bao-cao?ky=2026", "/api/du-bao",
                                 "/api/lien-he", "/api/lien-he?tat_ca=1"])
def test_chua_dang_nhap_thi_401_json(test_db_url, monkeypatch, url):
    monkeypatch.setenv("KOME_SESSION_SECRET", "bi-mat-thu-" + "x" * 32)
    r = TestClient(create_app(db_url=test_db_url)).get(url, follow_redirects=False)
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/json")


def test_ba_route_tra_vo_react_co_data_theme_tu_cookie(conn, c):
    for duong in ("/bao-cao", "/bao-cao?ky=2026", "/du-bao", "/du-bao?kb=cao",
                  "/lien-he", "/lien-he?tat_ca=1"):
        r = c.get(duong, cookies={"kome_giao_dien": "toi"})
        assert r.status_code == 200, duong
        assert 'id="goc"' in r.text and '<html lang="vi" data-theme="toi"' in r.text, duong
        assert "window.__KOME__=" in r.text, duong


def test_du_bao_tra_tong_CUA_CA_BA_kich_ban(conn, batch, c):
    """Đổi kịch bản ở trình duyệt KHÔNG hỏi lại máy chủ (`tong(kb)`/`theo(kb)`
    là phương thức, API tính sẵn cả ba). Tổng mỗi kịch bản phải bằng ĐÚNG
    tổng các tháng của chính kịch bản đó — ô "Tổng 12 tháng tới" và các cột
    biểu đồ là hai cách đọc cùng một con số — và khớp hàm gốc kome.du_bao."""
    _hai_nam_ban(conn, batch)
    d = c.get("/api/du-bao").json()
    assert set(d["kich_ban"]) == set(DB.KICH_BAN)
    assert set(d["tong"]) == set(d["theo"]) == set(DB.KICH_BAN)
    so_thang = len(d["db"]["nam"]["du_bao"])
    assert so_thang > 0, "dữ liệu phải đủ để có tháng dự báo — không thì test xanh vô nghĩa"
    for kb in DB.KICH_BAN:
        assert len(d["theo"][kb]) == so_thang, kb
        assert d["tong"][kb] == sum(d["theo"][kb]), kb
    m = DB.du_bao(conn).nam
    assert d["tong"] == {kb: m.tong(kb) for kb in DB.KICH_BAN}
    # Ba kịch bản phải thật sự khác nhau với dữ liệu này (thấp ≤ cơ sở ≤ cao).
    assert d["tong"]["thap"] <= d["tong"]["cs"] <= d["tong"]["cao"]
    assert d["tong"]["thap"] < d["tong"]["cao"]
    assert set(d["ve_nam"]) == set(DB.KICH_BAN)


def test_bao_cao_api_du_khoi_tren_kho_hai_nam(conn, batch, c):
    """Mọi khối của màn đều có dữ liệu để vẽ, và số của API BẰNG hàm gốc
    (API không định nghĩa chỉ số — bất biến giao diện React)."""
    from kome.bao_cao import tien_do_ngan_sach, tinh_bao_cao
    _hai_nam_ban(conn, batch)
    d = c.get("/api/bao-cao?ky=2026").json()
    for khoi in ("bd", "lk", "dg", "co", "nh", "pa"):
        assert d[khoi]["co"] is True, khoi
    bc = tinh_bao_cao(conn, 2026)
    assert d["bc"]["ky"]["doanh_thu"] == bc.ky.doanh_thu
    assert d["bc"]["ky"]["ty_suat"] == pytest.approx(bc.ky.ty_suat)
    assert d["td"]["thuc_te"] == tien_do_ngan_sach(conn, 2026).thuc_te
    assert set(d["so_nho"]) == {"dt", "lg", "ts", "kh"}
