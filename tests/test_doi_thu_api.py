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
                                        ("/api/doi-thu/ben/A", 2), ("/api/doi-thu/duyet?loc=bat_thuong", 2), ("/api/doi-thu/duyet?loc=da_xoa", 2),
                                        ("/api/san-pham/NT01/doi-thu", 2), ("/api/doi-thu/goi-y-nhac", 2),
                                        ("/api/khach-hang/K0001/doi-thu", 2),
                                        ("/api/doi-thu/mat-hang/nap/{fid}", 2),
                                        ("/api/doi-thu/lich-su?doi_tuong=gia:{fid},giao:KOME", 2),
                                        ("/api/doi-thu/giao-hang", 2)])
def test_ngan_sach_luot_hoi(conn, batch, test_db_url, monkeypatch, url, tran):
    url = url.format(fid=_nen(conn, batch)[0])
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
    from kome.web import anh_chup as AC
    pb = lambda: conn.execute(f"SELECT {AC._PHIEN_BAN}").fetchone()[0]
    conn.commit()
    truoc = pb()
    r = c.post("/api/doi-thu/thu-muc", json={"thang": "2026-07", "lien_ket": "https://drive.google.com/t7"})
    assert r.status_code == 200 and r.json()["ok"] is True
    conn.commit()
    assert pb() != truoc, "lưu link thư mục phải làm đổi phiên bản ảnh chụp"
    dong = c.get("/api/doi-thu/duyet").json()["dong"]
    assert dong
    assert all(d["lien_ket_thu_muc"] == "https://drive.google.com/t7" for d in dong if d["nguon"] == "nap")


@pytest.mark.parametrize("than", [{"thang": "2026-07", "lien_ket": "javascript:x"}, {"thang": "2026-7", "lien_ket": "https://a"},
                                  {"lien_ket": "https://a"}, {"thang": "2026-07"}])
def test_post_thu_muc_sai_tra_400(conn, batch, test_db_url, than):
    c = _web(test_db_url)
    r = c.post("/api/doi-thu/thu-muc", json=than)
    assert r.status_code == 400 and "loi" in r.json()


@pytest.mark.parametrize("url", ["/api/doi-thu/thu-muc", "/api/doi-thu/gia-moi"])
@pytest.mark.parametrize("than", [[], "x", 5])
def test_post_than_khong_phai_doi_tuong_tra_400(test_db_url, url, than):
    c = _web(test_db_url)
    r = c.post(url, json=than)
    assert r.status_code == 400 and "loi" in r.json()


def test_post_thu_muc_chi_nhan_json(test_db_url):
    c = _web(test_db_url)
    assert c.post("/api/doi-thu/thu-muc", data="thang=2026-07").status_code == 415


def test_nhat_ky_thao_tac_co_dong_dan_link_thu_muc(conn, batch):
    from kome import doi_thu as DT, nhat_ky as NK
    DT.dat_thu_muc(conn, "2026-07", "https://drive.google.com/t7", None)
    conn.commit()
    assert any(d.loai == "doi_thu" and "thư mục" in d.noi_dung.lower() for d in NK.dong_thoi_gian(conn))


# ---- Đợt 4b: đọc tươi cho pop-up sửa + tab Phí & giao hàng ---------------------------------------------

def test_mat_hang_200_kem_lich_su_va_404_json(conn, batch, test_db_url):
    from kome import doi_thu as DT
    fid = _nen(conn, batch)[0]
    DT.sua(conn, fid, {"gia_goc": "545"}, None)
    conn.commit()
    c = _web(test_db_url)
    r = c.get(f"/api/doi-thu/mat-hang/nap/{fid}")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["quan_sat"]["id"] == fid and [x["doi_tuong"] for x in j["lich_su"]] == [f"gia:{fid}"]
    r = c.get("/api/doi-thu/mat-hang/nap/999999")
    assert r.status_code == 404 and r.json() == {"loi": "Không có mặt hàng này."}
    assert c.get(f"/api/doi-thu/mat-hang/xyz/{fid}").status_code == 400


def test_lich_su_qua_5_khoa_400_va_hinh_dang(conn, batch, test_db_url):
    c = _web(test_db_url)
    assert c.get("/api/doi-thu/lich-su?doi_tuong=a,b,c,d,e,f").status_code == 400
    assert c.get("/api/doi-thu/lich-su").status_code == 400
    r = c.get("/api/doi-thu/lich-su?doi_tuong=giao:KOME")
    assert r.status_code == 200 and r.json() == {"lich_su": []}


def test_giao_hang_kome_dung_dau(conn, batch, test_db_url):
    r = _web(test_db_url).get("/api/doi-thu/giao-hang")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["dong"][0]["ma_doi_thu"] == "KOME" and "sua_cuoi" in j["dong"][0] and "so_don_ship" in j["bang_chung"]


# ---- Đợt 4b task 2: ghi từ pop-up (một giao dịch, 409 chống sửa đè) -------------------------------------

_POST_4B = ["/api/doi-thu/sua-mat-hang", "/api/doi-thu/giao-hang", "/api/doi-thu/dieu-kien", "/api/doi-thu/ben"]


def _max_nk(conn):
    return conn.execute("SELECT coalesce(max(id), 0) FROM app.doi_thu_nhat_ky").fetchone()[0]


@pytest.mark.parametrize("url", _POST_4B)
def test_4b2_post_chi_nhan_json_va_than_phai_la_doi_tuong(test_db_url, url):
    c = _web(test_db_url)
    assert c.post(url, data={"ma": "THAK"}).status_code == 415
    for than in ([], "x", 5):
        r = c.post(url, json=than)
        assert r.status_code == 400 and "loi" in r.json()


def test_4b2_sua_mat_hang_ok_tra_sua_cuoi(conn, batch, test_db_url):
    fid = _nen(conn, batch)[0]
    r = _web(test_db_url).post("/api/doi-thu/sua-mat-hang", json={
        "nguon": "nap", "id": fid, "da_xem": 0, "ghi_de": False, "nhan": "khong",
        "thay_doi": {"so_goi_thung": "20"}, "vi_sao_gia": None})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] and (j["nguon"], j["id"]) == ("nap", fid) and j["sua_cuoi"] == _max_nk(conn)


def test_4b2_sua_mat_hang_truong_gia_khong_vi_sao_400(conn, batch, test_db_url):
    fid = _nen(conn, batch)[0]
    r = _web(test_db_url).post("/api/doi-thu/sua-mat-hang",
                               json={"nguon": "nap", "id": fid, "da_xem": 0, "thay_doi": {"gia_goc": "500"}})
    assert r.status_code == 400 and "vì sao" in r.json()["loi"]


def test_4b2_mot_phan_hong_thi_khong_phan_nao_vao_qua_api(conn, batch, test_db_url):
    fid = _nen(conn, batch)[0]
    r = _web(test_db_url).post("/api/doi-thu/sua-mat-hang", json={
        "nguon": "nap", "id": fid, "da_xem": 0, "nhan": "khong", "thay_doi": {"so_goi_thung": "1.5"}})
    assert r.status_code == 400
    assert conn.execute("SELECT count(*) FROM app.ghep_hang").fetchone()[0] == 0 and _max_nk(conn) == 0


def test_4b2_xung_dot_409_kem_ai_luc_sau_va_khong_ghi(conn, batch, test_db_url):
    from kome import doi_thu as DT
    from tests.test_doi_thu import _nguoi
    fid = _nen(conn, batch)[0]
    DT.sua(conn, fid, {"muc_gia": "sỉ"}, _nguoi(conn))
    conn.commit()
    c = _web(test_db_url)
    b = {"nguon": "nap", "id": fid, "da_xem": 0, "nhan": "khong"}
    r = c.post("/api/doi-thu/sua-mat-hang", json=b)
    assert r.status_code == 409, r.text
    j = r.json()
    assert j["loi"] == "Có người vừa sửa mục này."
    assert j["xung_dot"]["ai"] == "lan" and j["xung_dot"]["sau"] == {"muc_gia": "sỉ"}
    assert j["xung_dot"]["luc"][:2] == "20" and "T" in j["xung_dot"]["luc"]
    assert conn.execute("SELECT count(*) FROM app.ghep_hang").fetchone()[0] == 0
    r = c.post("/api/doi-thu/sua-mat-hang", json=b | {"ghi_de": True})
    assert r.status_code == 200 and conn.execute("SELECT count(*) FROM app.ghep_hang").fetchone()[0] == 1


def test_4b2_giao_hang_va_dieu_kien_qua_api_409(conn, batch, test_db_url):
    c = _web(test_db_url)
    r = c.post("/api/doi-thu/giao-hang", json={"ma_doi_thu": "IMAI", "thay_doi": {"phi_ship": "600"}, "da_xem": 0})
    assert r.status_code == 200 and r.json()["sua_cuoi"] == _max_nk(conn)
    r = c.post("/api/doi-thu/giao-hang", json={"ma_doi_thu": "IMAI", "thay_doi": {"phi_ship": "610"}, "da_xem": 0})
    assert r.status_code == 409 and r.json()["xung_dot"]["sau"] == {"phi_ship": "600.00"}
    r = c.post("/api/doi-thu/giao-hang", json={"ma_doi_thu": "IMAI", "thay_doi": ["phi_ship"], "da_xem": 0})
    assert r.status_code == 400
    b = {"fact_id": None, "ma_doi_thu": "IMAI", "loai": "khac", "noi_dung": "Nghỉ Obon", "bo": False, "da_xem": 0}
    r = c.post("/api/doi-thu/dieu-kien", json=b)
    assert r.status_code == 200 and isinstance(r.json()["id"], int) and r.json()["sua_cuoi"] == _max_nk(conn)
    assert c.post("/api/doi-thu/dieu-kien", json=b | {"noi_dung": "khác"}).status_code == 200   # thêm mới: không kiểm
    assert c.post("/api/doi-thu/dieu-kien", json=b | {"bo": True}).status_code == 409
    assert c.post("/api/doi-thu/dieu-kien", json=b | {"bo": True, "ghi_de": True}).status_code == 200
    assert c.post("/api/doi-thu/dieu-kien", json=b | {"loai": "la", "ghi_de": True}).status_code == 400


@pytest.fixture
def imai_goc(conn):
    goc = conn.execute("SELECT ten, web, ghi_chu FROM app.doi_thu WHERE ma='IMAI'").fetchone()
    yield
    conn.rollback()
    conn.execute("UPDATE app.doi_thu SET ten=%s, web=%s, ghi_chu=%s WHERE ma='IMAI'", goc)
    conn.commit()


def test_4b2_ben_qua_api(conn, test_db_url, imai_goc):
    c = _web(test_db_url)
    r = c.post("/api/doi-thu/ben", json={"ma": "IMAI", "web": "http://imai.jp", "da_xem": 0})
    assert r.status_code == 400 and "https" in r.json()["loi"]
    r = c.post("/api/doi-thu/ben", json={"ma": "IMAI", "web": "https://imai.jp", "ghi_chu": "x", "da_xem": 0})
    assert r.status_code == 200 and r.json()["sua_cuoi"] == _max_nk(conn)
    assert c.post("/api/doi-thu/ben", json={"ma": "IMAI", "web": "", "da_xem": 0}).status_code == 409
    r = c.post("/api/doi-thu/ben", json={"ma": "IMAI", "web": "", "da_xem": _max_nk(conn)})
    assert r.status_code == 200
    assert conn.execute("SELECT web, ghi_chu FROM app.doi_thu WHERE ma='IMAI'").fetchone() == (None, "x")
    assert c.get("/api/doi-thu/ben/IMAI").json()["sua_cuoi_ben"] == _max_nk(conn)


def test_4b2_hong_SAU_buoc_nhan_van_khong_ghi_gi(conn, batch, test_db_url):
    """Dòng tay: đổi nhãn hợp lệ + gia_goc "" (không phải hết hàng) — lỗi "có giá" phải chặn TRƯỚC dat_ghep."""
    from kome import doi_thu as DT
    from tests.test_doi_thu import _ba_ben
    fid = _ba_ben(conn, batch)[0]
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi"}, None)
    DT.dat_ghep(conn, "THAK", "hTHAK", "NT01", None, "cung_hang", None)
    conn.commit()
    truoc = (_max_nk(conn), conn.execute("SELECT count(*) FROM app.gia_doi_thu_tay").fetchone()[0])
    r = _web(test_db_url).post("/api/doi-thu/sua-mat-hang", json={
        "nguon": "tay", "id": tid, "da_xem": _max_nk(conn), "nhan": "thay_the", "vi_sao_gia": "doc_sai",
        "thay_doi": {"gia_goc": ""}})
    assert r.status_code == 400 and "Nhập giá" in r.json()["loi"]
    assert conn.execute("SELECT nhan FROM app.ghep_hang").fetchone()[0] == "cung_hang"
    assert (_max_nk(conn), conn.execute("SELECT count(*) FROM app.gia_doi_thu_tay").fetchone()[0]) == truoc


def test_4b2_dong_bi_thay_van_doc_duoc_qua_mat_hang(conn, batch, test_db_url):
    from kome import doi_thu as DT
    from tests.test_doi_thu import _ba_ben
    fid = _ba_ben(conn, batch)[0]
    DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "vi_sao_gia": "da_doi", "loai_nguon": "to_roi",
                           "thay_doi": {"kenh_gia": "web"}}, None)
    conn.commit()
    r = _web(test_db_url).get(f"/api/doi-thu/mat-hang/nap/{fid}")
    assert r.status_code == 200 and r.json()["quan_sat"]["hien_hanh"] is False



def test_4b_ra_dong_bi_thay_409_kem_thay_boi_va_mat_hang_mang_thay_boi(conn, batch, test_db_url):
    """B14 qua API: sửa dòng đã bị thay → 409 cùng dạng, thêm `thay_boi` {nguon, id} (cả trong xung_dot); ghi_de
    không lách được; GET /mat-hang mang thay_boi để pop-up khoá Lưu ngay lúc mở."""
    from kome import doi_thu as DT
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 540)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi"}, None)
    conn.commit()
    c = _web(test_db_url)
    for ghi_de in (False, True):
        r = c.post("/api/doi-thu/sua-mat-hang", json={"nguon": "nap", "id": fid, "da_xem": _max_nk(conn), "ghi_de": ghi_de,
                                                        "thay_doi": {"so_goi_thung": "20"}})
        assert r.status_code == 409, r.text
        j = r.json()
        assert j["thay_boi"] == {"nguon": "tay", "id": tid} == j["xung_dot"]["thay_boi"]
        assert j["loi"] == "Dòng này đã có bản mới."
    assert conn.execute("SELECT count(*) FROM app.dinh_chinh_gia").fetchone()[0] == 0
    r = c.get(f"/api/doi-thu/mat-hang/nap/{fid}")
    assert r.status_code == 200 and r.json()["quan_sat"]["thay_boi"] == {"nguon": "tay", "id": tid}
    assert c.get(f"/api/doi-thu/mat-hang/tay/{tid}").json()["quan_sat"]["thay_boi"] is None


def test_4b_ra_so_sanh_mang_da_bo(conn, batch, test_db_url):
    fid = _nen(conn, batch)[0]
    c = _web(test_db_url)
    assert c.post("/api/doi-thu/sua-mat-hang", json={"nguon": "nap", "id": fid, "da_xem": 0, "nhan": "khong"}).status_code == 200
    j = c.get("/api/doi-thu/so-sanh").json()
    assert [(x["id"], x["nhom_khoa"], x["nhan_cu"]) for x in j["da_bo"]] == [(fid, "ma:NT01", "thay_the")]
    assert all(q["id"] != fid for n in j["nhom"] for q in n["quan_sat"])


# ---- 070: ẩn / khôi phục và gộp tay mặt hàng qua API ----------------------------------------------------

@pytest.mark.parametrize("url", ["/api/doi-thu/an", "/api/doi-thu/gop-mat-hang"])
def test_070_post_chi_nhan_json_va_than_phai_la_doi_tuong(test_db_url, url):
    c = _web(test_db_url)
    assert c.post(url, data={"ma": "THAK"}).status_code == 415
    for than in ([], "x", 5):
        r = c.post(url, json=than)
        assert r.status_code == 400 and "loi" in r.json()


def test_post_an_va_gop_mat_hang_chi_nhan_json_va_tra_409(conn, batch, test_db_url):
    _hang(conn, batch)
    fid_a = _qs(conn, batch, "THAK", 540, hang="hA")
    _qs(conn, batch, "THAK", 560, hang="hB")
    c = _web(test_db_url)
    # 1) ẩn: 200, có sua_cuoi = mốc nhật ký mới nhất
    r = c.post("/api/doi-thu/an", json={"nguon": "nap", "id": fid_a, "an": True, "da_xem": 0})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] and (j["nguon"], j["id"]) == ("nap", fid_a) and j["sua_cuoi"] == _max_nk(conn) > 0
    # 2) gửi lại với da_xem cũ: 409 kèm xung_dot, không ghi thêm
    n_truoc = _max_nk(conn)
    r = c.post("/api/doi-thu/an", json={"nguon": "nap", "id": fid_a, "an": False, "da_xem": 0})
    assert r.status_code == 409, r.text
    x = r.json()["xung_dot"]
    assert r.json()["loi"] == "Có người vừa sửa mục này." and x["sua_cuoi"] == j["sua_cuoi"] and "luc" in x
    assert _max_nk(conn) == n_truoc
    # ... ghi_de gửi lại được; dòng không có -> 400
    assert c.post("/api/doi-thu/an", json={"nguon": "nap", "id": fid_a, "an": False, "da_xem": 0,
                                           "ghi_de": True}).status_code == 200
    assert c.post("/api/doi-thu/an", json={"nguon": "nap", "id": 999999, "an": True, "da_xem": 0}).status_code == 400
    assert c.post("/api/doi-thu/an", json={"nguon": "nap", "id": fid_a, "an": "co", "da_xem": 0}).status_code == 400
    # 3) không phải JSON: 415 như các POST cùng nhóm
    assert c.post("/api/doi-thu/an", data="chữ thô").status_code == 415
    assert c.post("/api/doi-thu/an", content="không phải json",
                  headers={"content-type": "application/json"}).status_code == 400
    # 4) gộp hB vào hA: 200 kèm đích đã quy; gửi lại với da_xem cũ -> 409; đích không có -> 400
    r = c.post("/api/doi-thu/gop-mat-hang", json={"ma_doi_thu": "THAK", "ma_hang_dt": "hB",
                                                   "vao_ma_hang_dt": "hA", "da_xem": 0})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] and j["vao_ma_hang_dt"] == "hA" and j["sua_cuoi"] == _max_nk(conn)
    assert conn.execute("SELECT vao_ma_hang_dt FROM app.gop_mat_hang WHERE ma_hang_dt = 'hB'").fetchone()[0] == "hA"
    r = c.post("/api/doi-thu/gop-mat-hang", json={"ma_doi_thu": "THAK", "ma_hang_dt": "hB",
                                                   "vao_ma_hang_dt": None, "da_xem": 0})
    assert r.status_code == 409 and "xung_dot" in r.json()
    r = c.post("/api/doi-thu/gop-mat-hang", json={"ma_doi_thu": "THAK", "ma_hang_dt": "hB",
                                                   "vao_ma_hang_dt": "khong-co", "da_xem": j["sua_cuoi"]})
    assert r.status_code == 400
