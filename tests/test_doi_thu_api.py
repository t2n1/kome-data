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
                                        ("/api/san-pham/NT01/doi-thu", 2), ("/api/doi-thu/goi-y-nhac", 2),
                                        ("/api/khach-hang/K0001/doi-thu", 2)])
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


# ---------------------------------------------------------------- đợt 1b

def test_nhom_quy_cach_ngan_sach_va_hinh_dang(conn, batch, test_db_url, monkeypatch):
    _nen(conn, batch)
    c = _web(test_db_url)
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    r = c.get("/api/doi-thu/nhom-quy-cach")
    assert r.status_code == 200, r.text
    assert dem["n"] <= 2 and set(r.json()) == {"nhom", "quy_cach"}
    assert any(q["ma"] == "NT01" for q in r.json()["quy_cach"])


@pytest.mark.parametrize("url", ["/api/doi-thu/nhom/them-ma", "/api/doi-thu/nhom/bo-ma"])
def test_hai_post_moi_chi_nhan_json(conn, batch, test_db_url, url):
    _nen(conn, batch)
    assert _web(test_db_url).post(url, data={"product_code": "NT01"}).status_code == 415


def test_them_ma_va_bo_ma_qua_api_va_loi_400(conn, batch, test_db_url):
    _nen(conn, batch)
    c = _web(test_db_url)
    n = c.post("/api/doi-thu/nhom", json={"ten": "Basa", "ma_kome": []}).json()["id"]
    r = c.post("/api/doi-thu/nhom/them-ma", json={"nhom_id": n, "ma_kome": ["NT0l"]})
    assert r.status_code == 400 and "NT0l" in r.json()["loi"]
    assert c.post("/api/doi-thu/nhom/them-ma", json={"nhom_id": n, "ma_kome": "NT01"}).status_code == 400
    assert c.post("/api/doi-thu/nhom/them-ma", json={"nhom_id": n}).status_code == 400
    assert c.post("/api/doi-thu/nhom/them-ma", json={"nhom_id": n, "ma_kome": ["NT01"]}).json()["ok"]
    g = next(x for x in c.get("/api/doi-thu/nhom-quy-cach").json()["nhom"] if x["id"] == n)
    assert [m["ma"] for m in g["ma"]] == ["NT01"]
    r = c.post("/api/doi-thu/nhom/bo-ma", json={"product_code": "KHONGCO"})
    assert r.status_code == 400 and r.json()["loi"]
    assert c.post("/api/doi-thu/nhom/bo-ma", json={"product_code": "NT01"}).json()["ok"]
    g = next(x for x in c.get("/api/doi-thu/nhom-quy-cach").json()["nhom"] if x["id"] == n)
    assert g["ma"] == []


def test_nhom_ma_kome_la_chuoi_thi_400(conn, batch, test_db_url):
    _nen(conn, batch)
    r = _web(test_db_url).post("/api/doi-thu/nhom", json={"ten": "X", "ma_kome": "NT01"})
    assert r.status_code == 400 and r.json()["loi"]


# ---- Đợt 2 (063): tin hiện trường `@` qua API ----------------------------------------------------------

CAU = "Khách nói @THAK bán @Basa rẻ hơn mình"


def _the(loai, khoa, nhan):
    return {"loai": loai, "khoa": khoa, "vi_tri_dau": CAU.index(nhan), "do_dai": len(nhan)}


def _than(**them):
    return {"kieu": "goi", "ket_qua": "tot", "noi_dung": CAU,
            "nhac": [_the("doi_thu", "THAK", "@THAK"), _the("nhom", "ma:NT01", "@Basa")], **them}


def _nen_khach(conn, batch):
    from tests.test_khach_hang import _ho_so_khach
    _hang(conn, batch)
    _ho_so_khach(conn, batch, "K0001", "Quán một")


def test_post_tiep_xuc_kem_the_va_gia_tra_id_va_canh_bao(conn, batch, test_db_url):
    _nen_khach(conn, batch)
    c = _web(test_db_url)
    r = c.post("/api/khach-hang/K0001/tiep-xuc", json=_than(gia=[
        {"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 1200, "don_vi_gia": "kg"}]))
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True and isinstance(j["id"], int) and j["canh_bao"] == []
    assert conn.execute("SELECT count(*) FROM app.tiep_xuc_nhac").fetchone()[0] == 2
    assert conn.execute("SELECT gia_goc, loai_nguon FROM app.gia_doi_thu_tay").fetchone() == (1200, "khach_ke")


def test_post_tiep_xuc_cu_khong_nhac_khong_gia_van_chay_va_tra_canh_bao_rong(conn, batch, test_db_url):
    _nen_khach(conn, batch)
    r = _web(test_db_url).post("/api/khach-hang/K0001/tiep-xuc",
                               json={"kieu": "goi", "ket_qua": "tot", "noi_dung": "gọi thường"})
    assert r.status_code == 200 and r.json()["ok"] is True and r.json()["canh_bao"] == []
    assert conn.execute("SELECT count(*) FROM app.tiep_xuc_nhac").fetchone()[0] == 0


def test_post_the_lech_vi_tri_tra_400_va_khong_de_lai_dong_tiep_xuc(conn, batch, test_db_url):
    """[CRITICAL] Lỗi ở thẻ -> không có dòng tiếp xúc nào (cùng một giao dịch)."""
    _nen_khach(conn, batch)
    b = _than()
    b["nhac"][1]["vi_tri_dau"] += 1
    r = _web(test_db_url).post("/api/khach-hang/K0001/tiep-xuc", json=b)
    assert r.status_code == 400 and "@" in r.json()["loi"]
    assert conn.execute("SELECT count(*) FROM app.nhat_ky_tiep_xuc").fetchone()[0] == 0


def test_post_gia_khong_co_the_tuong_ung_tra_400(conn, batch, test_db_url):
    _nen_khach(conn, batch)
    b = _than(gia=[{"ma_doi_thu": "ICHIBA", "nhom_khoa": "ma:NT01", "gia_goc": 900, "don_vi_gia": "kg"}])
    r = _web(test_db_url).post("/api/khach-hang/K0001/tiep-xuc", json=b)
    assert r.status_code == 400
    assert conn.execute("SELECT count(*) FROM app.nhat_ky_tiep_xuc").fetchone()[0] == 0


@pytest.mark.parametrize("them", [{"nhac": "THAK"}, {"nhac": [1]}, {"gia": {"a": 1}}, {"gia": ["x"]}])
def test_post_nhac_gia_sai_kieu_tra_400_khong_500(conn, batch, test_db_url, them):
    _nen_khach(conn, batch)
    r = _web(test_db_url).post("/api/khach-hang/K0001/tiep-xuc", json=_than(**them))
    assert r.status_code == 400
    assert conn.execute("SELECT count(*) FROM app.nhat_ky_tiep_xuc").fetchone()[0] == 0


def test_post_canh_bao_khi_gia_lech_xa(conn, batch, test_db_url):
    _nen(conn, batch)                    # A B C = 540 560 580, D = 1400 (cùng nhóm ma:NT01)
    from tests.test_khach_hang import _ho_so_khach
    _ho_so_khach(conn, batch, "K0001", "Quán một")
    r = _web(test_db_url).post("/api/khach-hang/K0001/tiep-xuc", json=_than(gia=[
        {"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 2500, "don_vi_gia": "kg"}]))
    assert r.status_code == 200 and len(r.json()["canh_bao"]) == 1 and "kiểm lại đơn vị" in r.json()["canh_bao"][0]


def test_goi_y_nhac_va_khach_doi_thu_qua_api(conn, batch, test_db_url, monkeypatch):
    monkeypatch.setenv("KOME_ANH_CHUP", "1")            # ảnh chụp BẬT: ghi tiếp xúc phải làm nó cũ đi
    _nen_khach(conn, batch)
    c = _web(test_db_url)
    g = c.get("/api/doi-thu/goi-y-nhac").json()
    assert {x["ma"] for x in g["doi_thu"]} >= {"THAK", "ICHIBA"}
    assert any(x["khoa"] == "ma:NT01" and x["loai"] == "ma" for x in g["hang"])
    assert c.get("/api/khach-hang/K0001/doi-thu").json() == {"tin": [], "ly_do_ngung": []}
    assert c.post("/api/khach-hang/K0001/tiep-xuc", json=_than()).status_code == 200
    t = c.get("/api/khach-hang/K0001/doi-thu").json()["tin"]
    assert len(t) == 1 and t[0]["doi_thu"][0]["ma"] == "THAK" and t[0]["noi_dung"] == CAU


def test_ho_so_ben_va_tong_quan_co_khoi_moi_qua_api(conn, batch, test_db_url):
    _nen_khach(conn, batch)
    c = _web(test_db_url)
    assert c.post("/api/khach-hang/K0001/tiep-xuc", json=_than()).status_code == 200
    kh = c.get("/api/doi-thu/ben/THAK").json()["khach_dang_mua"]
    assert [x["ma_khach"] for x in kh] == ["K0001"]
    assert c.get("/api/doi-thu/tong-quan").json()["hien_truong"]["tong"] == 1


def test_post_thu_muc_ghi_va_phien_ban_doi(conn, batch, test_db_url):
    _nen(conn, batch)
    c = _web(test_db_url)
    r = c.post("/api/doi-thu/thu-muc", json={"thang": "2026-07", "lien_ket": "https://drive.google.com/t7"})
    assert r.status_code == 200 and r.json()["ok"] is True
    dong = c.get("/api/doi-thu/duyet").json()["dong"]
    assert all(d["lien_ket_thu_muc"] == "https://drive.google.com/t7" for d in dong if d["nguon"] == "nap")


@pytest.mark.parametrize("than", [{"thang": "2026-07", "lien_ket": "javascript:x"}, {"thang": "2026-7", "lien_ket": "https://a"},
                                  {"lien_ket": "https://a"}, {"thang": "2026-07"}])
def test_post_thu_muc_sai_tra_400(conn, batch, test_db_url, than):
    c = _web(test_db_url)
    r = c.post("/api/doi-thu/thu-muc", json=than)
    assert r.status_code == 400 and "loi" in r.json()


def test_post_thu_muc_chi_nhan_json(test_db_url):
    c = _web(test_db_url)
    assert c.post("/api/doi-thu/thu-muc", data="thang=2026-07").status_code == 415


def test_nhat_ky_thao_tac_co_dong_dan_link_thu_muc(conn, batch):
    from kome import doi_thu as DT, nhat_ky as NK
    DT.dat_thu_muc(conn, "2026-07", "https://drive.google.com/t7", None)
    conn.commit()
    assert any(d.loai == "doi_thu" and "thư mục" in d.noi_dung.lower() for d in NK.dong_thoi_gian(conn))
