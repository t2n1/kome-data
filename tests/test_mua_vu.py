"""Mùa vụ sản phẩm (/mua-vu, migration 058) — đặc tả 2026-09-29-mua-vu-san-pham-design.md."""
from datetime import date, timedelta
from pathlib import Path

import pytest

from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY

KHACH = "202607010001"

_SRC = Path(__file__).resolve().parents[1] / "giao_dien" / "src"


def test_muc_thanh_ben_va_route_co_mat():
    """Trang chạy được mà không có trong thanh điều hướng thì không ai vào được."""
    muc = (_SRC / "khung" / "muc.ts").read_text(encoding="utf-8")
    assert 'url: "/mua-vu"' in muc and "muavu" in muc
    assert '"/mua-vu"' in (_SRC / "main.tsx").read_text(encoding="utf-8")


def test_man_khong_tu_viet_lai_chi_so_va_dung_giu_khoang():
    src = (_SRC / "mua_vu" / "ManMuaVu.tsx").read_text(encoding="utf-8")
    assert "giuKhoang(" in src                       # replaceState qua giuKhoang
    assert "toFixed(" not in src and "de-DE" not in src   # định dạng qua dinh_dang.ts
    assert "/api/mua-vu" in src


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


from kome import mua_vu as MV


def _web(test_db_url):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    return TestClient(create_app(db_url=test_db_url))


def test_du_lieu_dang_cot_giu_so_0_dau_va_so_thap_phan(conn, batch):
    _hang(conn, batch)
    b = batch(778_202)
    conn.execute("""INSERT INTO core.dim_product (product_code, product_name, kind_code,
                      kind_name, food_category_name, batch_id)
                    VALUES ('000123', 'Mã số 0 đầu', '0', '有形', '調味料_VNM', %s)""", (b,))
    conn.commit()
    _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=3), hang="000123")
    _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=1), hang="FEE1")
    _neo(conn, batch)
    d = MV.du_lieu(conn)
    ma = [m["ma"] for m in d["ma"]]
    assert "000123" in ma and "__phi" in ma
    assert d["phi"] == ma.index("__phi") and d["tang"] is None
    k = ma.index("000123")
    j = d["dong"]["i"].index(k)
    assert d["dong"]["d"][j] == (HOM_NAY - timedelta(days=3) - date.fromisoformat(d["ngay_dau"])).days
    assert isinstance(d["dong"]["sl"][j], float) and isinstance(d["dong"]["dt"][j], int)
    m = d["ma"][k]
    assert m["ten"] == "Mã số 0 đầu" and m["nganh"] == "調味料_VNM" and m["an"] is False
    assert set(d["nganh"]) == {x["nganh"] for x in d["ma"] if x["nganh"]}   # mã giả: nganh ""
    assert len(d["dong"]["i"]) == len(d["dong"]["dt"]) == len(d["dong"]["sl"])


def test_du_lieu_ma_khong_co_master_van_co_ten_va_nganh(conn, batch):
    _ho_so_khach(conn, batch, KHACH, "Quán A")
    _mua(conn, batch, KHACH, HOM_NAY, hang="LA01")
    d = MV.du_lieu(conn)
    m = next(x for x in d["ma"] if x["ma"] == "LA01")
    assert m["ten"] == "LA01" and m["nganh"] == "(chưa phân loại)"


def test_du_lieu_kho_rong(conn):
    d = MV.du_lieu(conn)
    assert d["ngay_dau"] is None and d["ma"] == [] and d["dong"]["i"] == []


def test_du_lieu_DUNG_MOT_luot_hoi(conn, batch, monkeypatch):
    _hang(conn, batch)
    _mua(conn, batch, KHACH, HOM_NAY, hang="XT07")
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    MV.du_lieu(conn)
    assert dem["n"] == 1


def test_trang_va_api_mo_duoc_va_ngan_sach_luot_hoi(conn, batch, test_db_url, monkeypatch):
    import psycopg
    _hang(conn, batch)
    _mua(conn, batch, KHACH, HOM_NAY, hang="XT07")
    c = _web(test_db_url)
    r = c.get("/mua-vu")
    assert r.status_code == 200 and 'id="goc"' in r.text
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    r = c.get("/api/mua-vu")
    assert r.status_code == 200, r.text
    assert r.json()["ma"][0]["ma"]
    assert dem["n"] <= 2, f"/api/mua-vu chạy {dem['n']} lượt hỏi, trần 2"


def test_api_chua_dang_nhap_thi_401_json(test_db_url, monkeypatch):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    monkeypatch.setenv("KOME_SESSION_SECRET", "bi-mat-thu-" + "x" * 32)
    r = TestClient(create_app(db_url=test_db_url)).get("/api/mua-vu", follow_redirects=False)
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/json")
