"""Bảng giá KOME (/bang-gia, migration 071) — mã × quy cách × 売価No., kèm lần nạp trước."""
from datetime import date
from pathlib import Path

import pytest

from kome import bang_gia as BG

_SRC = Path(__file__).resolve().parents[1] / "giao_dien" / "src"
D1, D2 = date(2026, 8, 13), date(2026, 9, 8)


def _hang(conn, batch):
    b = batch(771_001)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, kind_code, kind_name, food_category_name, pack1_code, pack1_base_qty, batch_id)
           VALUES ('NT01', 'Ca Ba sa cat khuc (500g x 20 packs)', '0', '有形', '冷凍_VNM', '02', 20, %s),
                  ('XT07', 'Banh pho', '0', '有形', '食材（常温）＿VNM', NULL, NULL, %s),
                  ('ZZ01', 'Khong co gia', '0', '有形', '食材（常温）＿VNM', NULL, NULL, %s),
                  ('MKT18', 'Poster', '0', '有形', '雑貨_VNM', NULL, NULL, %s),
                  ('FEE1', '代引手数料', '1', '無形', '', NULL, NULL, %s)""", (b,) * 5)
    conn.commit()


def _lan_nap(conn, batch, ngay, dong, n):
    """MỘT lần nạp = MỘT lô cho mọi dòng (như kome/loaders/price.py). dong: (mã, quy cách, bậc, chưa thuế, gồm thuế, vốn)."""
    b = batch(n, ngay)
    for ma, qc, lv, ex, inc, von in dong:
        conn.execute("""INSERT INTO core.fact_price_list (product_code, pack_code, price_level, valid_from, price_ex_tax,
                          price_in_tax, unit_cost, batch_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (product_code, pack_code, price_level, valid_from) DO UPDATE
                        SET price_ex_tax = EXCLUDED.price_ex_tax, price_in_tax = EXCLUDED.price_in_tax,
                            unit_cost = EXCLUDED.unit_cost, batch_id = EXCLUDED.batch_id""",
                     (ma, qc, lv, ngay, ex, inc, von, b))
    conn.commit()
    return b


def _bang(conn, ma):
    return {(r[0], r[1]): r[2:] for r in conn.execute(
        """SELECT pack_code, price_level, hien_hanh, gia_chua_thue, gia_truoc, doi, tu_ngay, tu_ngay_truoc
           FROM mart.bang_gia_kome WHERE product_code = %s""", (ma,))}


def test_hien_hanh_va_lan_nap_truoc_doi_gia_bac_moi_bac_bi_bo(conn, batch):
    _hang(conn, batch)
    _lan_nap(conn, batch, D1, [("NT01", "02", "01", 5000, 5400, 4000), ("NT01", "02", "02", 4800, 5184, 4000),
                               ("NT01", "02", "10", 4500, 4860, 4000)], 771_101)
    _lan_nap(conn, batch, D2, [("NT01", "02", "01", 5200, 5616, 4000), ("NT01", "02", "02", 4800, 5184, 4000),
                               ("NT01", "02", "04", 4700, 5076, 4000), ("NT01", "00", "01", 300, 324, 200)], 771_102)
    b = _bang(conn, "NT01")
    assert b[("02", "01")][:4] == (True, 5200, 5000, True)            # đổi giá
    assert b[("02", "02")][:4] == (True, 4800, 4800, False)           # giữ nguyên
    assert b[("02", "04")][:4] == (True, 4700, None, True)            # bậc mới
    assert b[("02", "10")][:4] == (False, None, 4500, True)           # bậc bị bỏ
    assert b[("02", "01")][4:] == (D2, D1)
    assert b[("00", "01")][:4] == (True, 300, None, False)            # quy cách chưa có lần trước → không "đổi"
    assert b[("00", "01")][4:] == (D2, None)


def test_sua_file_cung_ngay_bac_bi_bo_bien_mat_khong_thanh_lan_truoc(conn, batch):
    """price.py upsert file sửa cùng ngày — bậc bị bỏ giữ batch_id cũ và phải biến mất (066), không phải "lần trước"."""
    _hang(conn, batch)
    _lan_nap(conn, batch, D2, [("NT01", "02", "01", 5000, 5400, 0), ("NT01", "02", "10", 4500, 4860, 0)], 771_201)
    _lan_nap(conn, batch, D2, [("NT01", "02", "01", 5100, 5508, 0)], 771_202)
    b = _bang(conn, "NT01")
    assert set(b) == {("02", "01")}
    assert b[("02", "01")][:4] == (True, 5100, None, False)


def test_luat_hai_cot_va_duoi_gia_von(conn, batch):
    _hang(conn, batch)
    _lan_nap(conn, batch, D2, [("NT01", "02", "std", 0, 4860, 4000),      # chỉ gồm thuế → ÷ 1,08 = 4500
                               ("NT01", "02", "01", 5900, 4860, 4000),    # gồm thuế < chưa thuế → mâu thuẫn → 4500
                               ("NT01", "02", "10", 3900, 4212, 4000)],   # dưới giá vốn
               771_301)
    r = {x[0]: x[1:] for x in conn.execute(
        """SELECT price_level, round(gia_chua_thue), hai_cot_lech, duoi_gia_von, gia_von FROM mart.bang_gia_kome
           WHERE product_code = 'NT01'""")}
    assert r["std"] == (4500, False, False, 4000)
    assert r["01"] == (4500, True, False, 4000)
    assert r["10"] == (3900, False, True, 4000)


def test_lui_moc_thi_lan_nap_cu_thanh_hien_hanh(conn, batch):
    from tests.test_khach_hang import _ho_so_khach, _mua
    _hang(conn, batch)
    _lan_nap(conn, batch, D1, [("NT01", "02", "01", 5000, 5400, 0)], 771_401)
    _lan_nap(conn, batch, D2, [("NT01", "02", "01", 5200, 5616, 0)], 771_402)
    _ho_so_khach(conn, batch, "202601010001", "Quan A")
    _mua(conn, batch, "202601010001", D2, hang="NT01")
    conn.execute("SELECT set_config('kome.moc', '2026-08-20', true)")
    b = _bang(conn, "NT01")
    assert b[("02", "01")] == (True, 5000, None, False, D1, None)


def test_gia_kome_bang_va_bac_gia_doc_CUNG_view(conn, batch):
    """071 là định nghĩa DUY NHẤT: gia_kome_bang (so với đối thủ) và tab Giá & lãi đọc view này, không tự chép luật."""
    from kome import san_pham_360 as SP360
    _hang(conn, batch)
    _lan_nap(conn, batch, D2, [("NT01", "02", "01", 5000, 5400, 0), ("NT01", "00", "01", 300, 324, 0)], 771_501)
    assert [(g["quy_cach"], g["gia"]) for g in SP360._bac_gia(conn, "NT01")] == [("バラ (lẻ)", 300), ("ケース (thùng)", 5000)]
    assert conn.execute("SELECT pack_code, gia_chua_thue FROM mart.gia_kome_bang WHERE product_code='NT01'").fetchall() \
        == [("02", 5000)]
    goc = Path(__file__).resolve().parents[1]
    assert "FROM core.fact_price_list" not in (goc / "kome" / "san_pham_360.py").read_text(encoding="utf-8")
    m = (goc / "db" / "migrations" / "071_mart_bang_gia_kome.sql").read_text(encoding="utf-8")
    than = m[m.index("CREATE OR REPLACE VIEW mart.gia_kome_bang"):]
    assert "mart.bang_gia_kome" in than and "fact_price_list" not in than


def test_du_lieu_mot_luot_hoi_danh_muc_va_co(conn, batch, monkeypatch):
    _hang(conn, batch)
    _lan_nap(conn, batch, D1, [("NT01", "02", "01", 5000, 5400, 4000)], 771_601)
    _lan_nap(conn, batch, D2, [("NT01", "02", "01", 5200, 5616, 4000), ("NT01", "02", "10", 3900, 4212, 4000),
                               ("XT07", "02", "01", 2000, 2160, 0), ("MKT18", "00", "01", 100, 108, 0)], 771_602)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    d = BG.du_lieu(conn)
    assert dem["n"] == 1
    ma = {m["ma"]: m for m in d["ma"]}
    assert set(ma) == {"NT01", "XT07", "ZZ01"}                        # bỏ POSM / phí (048–049)
    assert ma["ZZ01"]["dong"] == [] and not ma["ZZ01"]["thieu_kg"]
    assert not ma["NT01"]["thieu_kg"] and ma["XT07"]["thieu_kg"]      # XT07: không suy được kg → không so với đối thủ
    (dong,) = ma["NT01"]["dong"]
    assert dong["qc"] == "02" and dong["gia_von"] == 4000 and dong["tu"] == "2026-09-08" and dong["tu_truoc"] == "2026-08-13"
    assert dong["g"]["01"] == {"gia": 5200, "truoc": 5000, "lech": False, "doi": True, "duoi": False, "bo": False}
    assert dong["g"]["10"]["duoi"] and dong["g"]["10"]["doi"]
    assert d["bac"] == [{"ma": "01", "nhan": "No.1"}, {"ma": "10", "nhan": "No.10 · KM"}]
    assert d["moi_nhat"] == "2026-09-08"


def test_nhan_bac_tieu_chuan_dau_tien():
    assert sorted(["10", "std", "02", "09"], key=BG._thu_bac) == ["std", "02", "09", "10"]
    assert BG.nhan_bac("std") == "標準価格" and BG.nhan_bac("03") == "No.3"


def _web(test_db_url):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    return TestClient(create_app(db_url=test_db_url))


def test_trang_va_api_mo_duoc_va_ngan_sach_luot_hoi(conn, batch, test_db_url, monkeypatch):
    import psycopg
    _hang(conn, batch)
    _lan_nap(conn, batch, D2, [("NT01", "02", "01", 5200, 5616, 4000)], 771_701)
    c = _web(test_db_url)
    r = c.get("/bang-gia")
    assert r.status_code == 200 and 'id="goc"' in r.text
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    r = c.get("/api/bang-gia")
    assert r.status_code == 200, r.text
    assert any(m["ma"] == "NT01" for m in r.json()["ma"])
    assert dem["n"] <= 2, f"/api/bang-gia chạy {dem['n']} lượt hỏi, trần 2"


def test_api_chua_dang_nhap_thi_401_json(test_db_url, monkeypatch):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    monkeypatch.setenv("KOME_SESSION_SECRET", "bi-mat-thu-" + "x" * 32)
    r = TestClient(create_app(db_url=test_db_url)).get("/api/bang-gia", follow_redirects=False)
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/json")


def test_muc_thanh_ben_va_route_co_mat():
    muc = (_SRC / "khung" / "muc.ts").read_text(encoding="utf-8")
    assert 'url: "/bang-gia"' in muc
    assert '"/bang-gia"' in (_SRC / "main.tsx").read_text(encoding="utf-8")
    src = (_SRC / "bang_gia" / "ManBangGia.tsx").read_text(encoding="utf-8")
    assert "/api/bang-gia" in src and "toFixed(" not in src and "de-DE" not in src
