"""API /doi-thu — ngân sách lượt hỏi, POST chỉ JSON, sửa xong số đổi ngay (đặc tả §5, §9)."""
from pathlib import Path
import psycopg
import pytest

from tests.test_mart_doi_thu import _hang, _qs
from tests.test_mua_vu import _web

_SRC = Path(__file__).resolve().parents[1] / "giao_dien" / "src"


def _nen(conn, batch):
    _hang(conn, batch)
    return [_qs(conn, batch, b, g) for b, g in [("A", 540), ("B", 560), ("C", 580), ("D", 1400)]]


@pytest.mark.parametrize("url, tran", [("/api/doi-thu/tong-quan", 2), ("/api/doi-thu/so-sanh", 2),
                                        ("/api/doi-thu/ben/A", 2), ("/api/doi-thu/duyet?loc=bat_thuong", 2),
                                        ("/api/san-pham/NT01/doi-thu", 2)])
def test_ngan_sach_luot_hoi(conn, batch, test_db_url, monkeypatch, url, tran):
    _nen(conn, batch)
    c = _web(test_db_url)
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    r = c.get(url)
    assert r.status_code == 200, r.text
    assert dem["n"] <= tran, f"{url}: {dem['n']} lượt hỏi, trần {tran}"


def test_post_chi_nhan_json(conn, batch, test_db_url):
    fid = _nen(conn, batch)[3]
    c = _web(test_db_url)
    assert c.post("/api/doi-thu/xac-nhan", data={"fact_id": fid}).status_code == 415


def test_xac_nhan_xong_bat_thuong_mat_ngay(conn, batch, test_db_url, monkeypatch):
    monkeypatch.setenv("KOME_ANH_CHUP", "1")               # ảnh chụp BẬT: sửa phải làm nó cũ đi
    fid = _nen(conn, batch)[3]
    c = _web(test_db_url)
    assert len(c.get("/api/doi-thu/duyet?loc=bat_thuong").json()["dong"]) == 1
    assert c.post("/api/doi-thu/xac-nhan", json={"fact_id": fid}).json()["ok"]
    assert c.get("/api/doi-thu/duyet?loc=bat_thuong").json()["dong"] == []


def test_sua_sai_tra_400_kem_cau(conn, batch, test_db_url):
    fid = _nen(conn, batch)[0]
    r = _web(test_db_url).post("/api/doi-thu/sua", json={"fact_id": fid, "thay_doi": {"thue": "?"}})
    assert r.status_code == 400 and "thue" in r.json()["loi"]


def test_trang_mo_duoc(test_db_url):
    assert _web(test_db_url).get("/doi-thu").status_code == 200


def test_muc_thanh_ben_va_route():
    assert 'url: "/doi-thu"' in (_SRC / "khung" / "muc.ts").read_text(encoding="utf-8")
    assert '"/doi-thu"' in (_SRC / "main.tsx").read_text(encoding="utf-8")


def test_san_pham_doi_thu_khong_bi_route_khac_nuot(conn, batch, test_db_url):
    """R2: /api/san-pham/{ma}/doi-thu phải trả hình dạng mới {"nhom": …}, không rơi vào route khác."""
    _nen(conn, batch)
    r = _web(test_db_url).get("/api/san-pham/NT01/doi-thu")
    assert r.status_code == 200 and "nhom" in r.json()


def test_nhat_ky_thao_tac_thay_sua_doi_thu(conn, batch):
    from kome import doi_thu as DT, nhat_ky as NK
    fid = _nen(conn, batch)[0]
    DT.sua(conn, fid, {"gia_goc": "550"}, None)
    conn.commit()
    assert "doi_thu" in NK.LOAI
    assert any(d.loai == "doi_thu" for d in NK.dong_thoi_gian(conn))


def test_khoi_san_pham_tra_nhom_theo_kg(conn, batch, test_db_url):
    _nen(conn, batch)
    d = _web(test_db_url).get("/api/san-pham/NT01/doi-thu").json()
    assert d["nhom"]["nhom_khoa"] == "ma:NT01" and d["nhom"]["so_ben"] == 3
    assert (_SRC / "san_pham" / "ho_so" / "KhoiDoiThu.tsx").exists()
