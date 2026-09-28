"""Bố cục trang Tổng quan theo từng tài khoản (migration 034, kome/web/bo_cuc.py).

Mỗi người tự kéo thả / đổi kích thước / ẩn hiện khối (theo Dashboard.dc.html),
lưu trên máy chủ chứ không trong localStorage. Các test ở đây canh ba điều:
máy chủ không tin bất cứ thứ gì trình duyệt gửi lên; trang vẽ SẴN đúng bố cục
đã lưu (không phải chờ JS); và không có người đăng nhập thì không có nút nào
hứa một việc máy chủ không làm được.
"""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kome.web import bo_cuc as BC
from kome.web.app import create_app

MK = "mat-khau-bo-cuc-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"
GOC = Path(__file__).resolve().parents[1]
MA = [k[0] for k in BC.KHOI]
# Thứ tự của bố cục mặc định ĐÃ xếp chỗ (theo y, x) — khác thứ tự danh mục từ lưới 12 cột.
MAC = [o.id for o in BC.mac_dinh()]


# ---- chuan_hoa: không tin trình duyệt ---------------------------------

@pytest.mark.parametrize("tho", [None, "", "không phải json", "{}", 42, [1, "x", None], {"id": "chi_so"}])
def test_rac_thi_ve_mac_dinh_khong_nem_loi(tho):
    assert BC.chuan_hoa(tho) == BC.mac_dinh()


def test_giu_thu_tu_va_noi_khoi_thieu_vao_cuoi():
    """Bố cục lưu từ trước khi code thêm một khối vẫn đọc được — khối mới
    nối vào ĐÁY, không vứt cả bố cục về mặc định như gói thiết kế. Bố cục cũ
    (không x/y, đơn vị 3 cột) đổi × DOI_CU và xếp theo thứ tự đã lưu."""
    ra = BC.chuan_hoa([{"id": "han_su_dung", "rong": 3, "cao": 1}, {"id": "kpi", "rong": 1, "cao": 4}])
    assert [o.id for o in ra[:2]] == ["han_su_dung", "kpi"]
    assert (ra[0].x, ra[0].y, ra[0].rong, ra[0].cao) == (0, 0, 12, 3)
    assert (ra[1].x, ra[1].y, ra[1].rong, ra[1].cao) == (0, 3, 4, 12)
    assert sorted(o.id for o in ra) == sorted(MA)
    assert all(not o.an for o in ra)
    assert all(o.y >= 3 for o in ra[2:])      # khối thiếu nằm dưới khối đã lưu


def test_bo_ma_la_va_ma_trung():
    ra = BC.chuan_hoa([{"id": "xoa_du_lieu"}, {"id": "kpi", "rong": 2},
                       {"id": "kpi", "rong": 3}, {"id": "__proto__"}])
    assert [o.id for o in ra].count("kpi") == 1
    assert ra[0].id == "kpi" and ra[0].rong == 8
    assert len(ra) == len(MA)


@pytest.mark.parametrize("rong,cao,mong", [
    (0, 0, (4, 3)), (-5, 99, (4, 12)), (7, 2, (12, 6)), (2.9, 3.2, (8, 9)),
    ("3", "2", None), (True, True, None), (None, None, None),
])
def test_kich_thuoc_bo_cuc_CU_kep_roi_doi_don_vi(rong, cao, mong):
    o = BC.chuan_hoa([{"id": "xu_huong", "rong": rong, "cao": cao}])[0]
    if mong is None:          # chuỗi, bool, thiếu -> mặc định của khối (8, 6)
        mong = (8, 6)
    assert (o.rong, o.cao) == mong


@pytest.mark.parametrize("vao,mong", [
    ({"x": 11, "y": 0, "rong": 99, "cao": 1}, (0, 0, 12, 2)),
    ({"x": 10, "y": -3, "rong": 4, "cao": 40}, (8, 0, 4, 16)),
    ({"x": 2.7, "y": 0, "rong": 1, "cao": 5}, (2, 0, 3, 5)),
    ({"x": 0, "y": 0, "rong": "4", "cao": None}, (0, 0, 8, 6)),
])
def test_bo_cuc_MOI_kep_toa_do_va_kich_thuoc(vao, mong):
    o = BC.chuan_hoa([{"id": "xu_huong", **vao}])[0]
    assert (o.x, o.y, o.rong, o.cao) == mong


def test_nen_giong_het_ban_typescript():
    """Cùng file ca với giao_dien/src/tong_quan/luoi_logic.test.ts — hai bản `nen`
    (máy chủ chuẩn hoá lúc đọc/ghi, trình duyệt lúc kéo) không được trôi khỏi nhau."""
    ca = json.loads((GOC / "tests/du_lieu/luoi_nen_ca.json").read_text(encoding="utf-8"))
    assert len(ca) >= 8
    for c in ca:
        ra = BC.nen([BC.O(x["id"], x["rong"], x["cao"], x["an"], x["x"], x["y"]) for x in c["vao"]])
        assert {o.id: [o.x, o.y] for o in ra} == c["ra"], c["ten"]


def _chong_nhau(ds):
    hien = [o for o in ds if not o.an]
    return [(a.id, b.id) for i, a in enumerate(hien) for b in hien[i + 1:]
            if BC._chong(a, b.x, b.y, b.rong, b.cao)]


@pytest.mark.parametrize("hat", range(40))
def test_khong_bao_gio_co_hai_khoi_chong_nhau(hat):
    """Bố cục rác bất kỳ (toạ độ trùng, tràn, lẫn khối ẩn) ra khỏi chuan_hoa là
    lưới sạch: không cặp khối hiện nào đè nhau, mọi khối nằm trong 12 cột."""
    import random
    r = random.Random(hat)
    tho = [{"id": m, "x": r.randint(-2, 14), "y": r.randint(-2, 30), "rong": r.randint(0, 14),
            "cao": r.randint(0, 18), "an": r.random() < .2} for m in r.sample(MA, r.randint(1, len(MA)))]
    ra = BC.chuan_hoa(tho)
    assert _chong_nhau(ra) == []
    assert all(0 <= o.x and o.x + o.rong <= 12 and o.y >= 0 for o in ra)
    assert sorted(o.id for o in ra) == sorted(MA)


def test_mac_dinh_da_xep_cho_va_khop_danh_muc():
    md = BC.mac_dinh()
    assert _chong_nhau(md) == [] and sorted(o.id for o in md) == sorted(MA)
    assert BC.danh_muc()["mac_dinh"] == [o.dict() for o in md]


def test_cach_xem_chi_nhan_ma_trong_danh_muc():
    ra = {o.id: o.xem for o in BC.chuan_hoa([
        {"id": "xu_huong", "x": 0, "y": 0, "rong": 8, "cao": 6, "xem": "luy_ke"},
        {"id": "theo_thang", "x": 0, "y": 6, "rong": 8, "cao": 6, "xem": "khong_co"},
        {"id": "kpi", "x": 0, "y": 12, "rong": 8, "cao": 3, "xem": "luy_ke"},
        {"id": "suc_khoe_khach", "x": 8, "y": 0, "rong": 4, "cao": 3, "xem": 1}])}
    assert ra == {**ra, "xu_huong": "luy_ke", "theo_thang": None, "kpi": None, "suc_khoe_khach": None}


def test_danh_muc_cach_xem_moi_khoi():
    du = {k[0] for k in BC._KHOI_DAY_DU}
    assert set(BC.CACH_XEM) <= du
    assert all(len(v) >= 2 and len({a for a, _ in v}) == len(v) for v in BC.CACH_XEM.values())
    for k in BC.danh_muc()["khoi"]:
        assert [x["id"] for x in k["cach_xem"]] == [a for a, _ in BC.CACH_XEM.get(k["id"], ())]


def test_an_chi_nhan_dung_true():
    ra = {o.id: o.an for o in BC.chuan_hoa([{"id": "kpi", "an": True}, {"id": "xu_huong", "an": "true"},
                                            {"id": "tuong_quan", "an": 1}])}
    assert ra["kpi"] is True and ra["xu_huong"] is False and ra["tuong_quan"] is False


def test_doc_duoc_chuoi_json():
    ra = BC.chuan_hoa(json.dumps([{"id": "suc_khoe_khach", "rong": 3, "cao": 1, "an": True}]))
    assert {o.id: o for o in ra}["suc_khoe_khach"] == BC.O("suc_khoe_khach", 12, 3, True)


def test_ma_khoi_cua_ban_jinja_van_doc_duoc():
    """Bố cục lưu bằng bản Jinja (034, mã chi_so/can_han…) không bị vứt khi đổi
    sang giao diện React — đổi sang mã mới, giữ nguyên thứ tự và kích thước."""
    ra = BC.chuan_hoa([{"id": "can_han", "rong": 1, "cao": 3}, {"id": "chi_so", "an": True}])
    assert (ra[0].id, ra[0].rong, ra[0].cao) == ("han_su_dung", 4, 9)
    assert {o.id: o.an for o in ra}["kpi"] is True


def test_danh_muc_bam_goi_thiet_ke():
    """21 khối của Dashboard.dc.html + khối tháng (036) + khách mới (044), 6 nhóm, 4 vai trò; mọi khối của vai trò
    đều có trong danh mục; mọi khối KHÔNG có hàm dữ liệu thì có câu "chưa có". Khối của tính
    năng công ty chưa dùng (kome/nguon_dung.py, BC.KHOI_CAN) rời danh mục nhưng vẫn có hàm."""
    from kome import khoi_tong_quan as KTQ, nguon_dung as ND
    dm = BC.danh_muc()
    ma = {k["id"] for k in dm["khoi"]}
    du = {k[0] for k in BC._KHOI_DAY_DU}
    an = {k for k, tn in BC.KHOI_CAN.items() if not ND.tinh_nang()[tn]}
    from kome import man_chua_co as MCC
    an |= set() if MCC.HIEN else set(MCC.KHOI)   # khối chưa làm tạm ẩn (2026-09-28)
    assert len(du) == 23 and ma == du - an and len(dm["nhom"]) == 6 and len(dm["vai_tro"]) == 4
    assert all(set(v["khoi"]) <= ma for v in dm["vai_tro"])
    assert du == set(KTQ.KHOI) | set(KTQ.CHUA_CO)
    assert not set(KTQ.KHOI) & set(KTQ.CHUA_CO)



# ---- Trang web ----------------------------------------------------------

@pytest.fixture
def web(monkeypatch, test_db_url, conn):
    """TestClient có cổng đăng nhập; `vao(ten)` tạo tài khoản và đăng nhập."""
    from kome.web import nguoi_dung as ND

    def _tao(bi_mat=BI_MAT, vercel=False):
        monkeypatch.delenv("KOME_CHI_DOC", raising=False)
        if bi_mat is None:
            monkeypatch.delenv("KOME_SESSION_SECRET", raising=False)
        else:
            monkeypatch.setenv("KOME_SESSION_SECRET", bi_mat)
        if vercel:
            monkeypatch.setenv("VERCEL", "1")
        else:
            monkeypatch.delenv("VERCEL", raising=False)
        return TestClient(create_app(db_url=test_db_url), follow_redirects=False,
                          base_url="https://testserver" if vercel else "http://testserver")

    def vao(c, ten="an"):
        if not ND.dat_quyen(conn, ten):
            ND.tao(conn, ten, MK)
        conn.commit()
        assert c.post("/dang-nhap", data={"ten": ten, "mat_khau": MK}).status_code == 303
        return c
    _tao.vao = vao
    return _tao


def _luu(c, bo_cuc):
    return c.post("/tong-quan/bo-cuc", content=json.dumps(bo_cuc),
                  headers={"Content-Type": "application/json"})


def _khoi_dau(html):
    """window.__KOME__ máy chủ chèn vào index.html (kome/web/spa.py)."""
    m = re.search(r"<script>window.__KOME__=(.*?)</script>", html, re.S)
    assert m, "trang không có dữ liệu khởi đầu"
    return json.loads(m.group(1))


def _bo_cuc(html):
    """Bố cục của bảng đang hiện (056: mỗi người nhiều bảng)."""
    kd = _khoi_dau(html)
    return next(b for b in kd["bang"] if b["id"] == kd["bang_hien_id"])["bo_cuc"]


def _thu_tu(html):
    return [o["id"] for o in _bo_cuc(html)]


def _luu_db(conn, ten="an"):
    return conn.execute("""SELECT b.bo_cuc FROM app.bang_tong_quan b
                           JOIN app.nguoi_dung n ON n.id = b.nguoi_dung_id
                           WHERE n.ten_dang_nhap = %s""", (ten,)).fetchone()[0]


def test_luu_roi_trang_ve_SAN_dung_thu_tu_va_kich_thuoc(web, conn):
    """Bố cục đã lưu nằm SẴN trong HTML đầu tiên (window.__KOME__) — giao diện
    vẽ đúng ngay, không có khung hình mặc định rồi giật sang bố cục của mình."""
    c = web.vao(web())
    r = _luu(c, [{"id": "han_su_dung", "rong": 3, "cao": 1}, {"id": "kpi", "rong": 1, "cao": 3}])
    assert r.status_code == 200
    assert r.json()["bo_cuc"][0] == {"id": "han_su_dung", "x": 0, "y": 0, "rong": 12, "cao": 3, "an": False, "xem": None}
    html = c.get("/").text
    bc = _bo_cuc(html)
    assert [o["id"] for o in bc][:2] == ["han_su_dung", "kpi"]
    assert bc[1] == {"id": "kpi", "x": 0, "y": 3, "rong": 4, "cao": 9, "an": False, "xem": None}
    assert _khoi_dau(html)["sap_xep_duoc"] is True
    luu = _luu_db(conn)
    assert [x["id"] for x in luu][:2] == ["han_su_dung", "kpi"] and len(luu) == len(MA)


def test_khoi_an_van_nam_trong_bo_cuc_voi_co_an(web):
    """Khối ẩn không biến khỏi bố cục — nó mang `an`, và ô "Thêm chức năng"
    hiện lại được."""
    c = web.vao(web())
    _luu(c, [{"id": "xu_huong", "an": True}])
    an = {o["id"]: o["an"] for o in _bo_cuc(c.get("/").text)}
    assert an["xu_huong"] is True and an["kpi"] is False and len(an) == len(MA)


def test_hai_nguoi_hai_bo_cuc(web):
    a = web.vao(web(), "an")
    _luu(a, [{"id": "tuong_quan"}])
    b = web.vao(web(), "binh")
    _luu(b, [{"id": "suc_khoe_khach"}])
    assert _thu_tu(a.get("/").text)[0] == "tuong_quan"
    assert _thu_tu(b.get("/").text)[0] == "suc_khoe_khach"


def test_ve_mac_dinh_bang_form_thuong(web, conn):
    c = web.vao(web())
    _luu(c, [{"id": "han_su_dung"}])
    bang = _khoi_dau(c.get("/").text)["bang_hien_id"]
    r = c.post("/tong-quan/bo-cuc/mac-dinh", data={"bang": str(bang)})
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert _thu_tu(c.get("/").text) == MAC
    assert _luu_db(conn) is None


def test_bo_cuc_rac_trong_csdl_khong_lam_hong_trang_chu(web, conn):
    c = web.vao(web())
    conn.execute("""INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, bo_cuc, thu_tu)
                    SELECT id, 'Rác', '{"la": "rac"}'::jsonb, 0 FROM app.nguoi_dung
                    WHERE ten_dang_nhap = 'an'""")
    conn.commit()
    r = c.get("/")
    assert r.status_code == 200 and _thu_tu(r.text) == MAC


def test_chi_nhan_json_va_chan_than_qua_lon(web):
    c = web.vao(web())
    assert c.post("/tong-quan/bo-cuc", data={"id": "chi_so"}).status_code == 415
    lon = [{"id": "chi_so", "rac": "x" * BC.DAI_TOI_DA}]
    assert _luu(c, lon).status_code == 413


def test_chua_dang_nhap_thi_bi_cong_chan(web):
    r = _luu(web(), [{"id": "can_han"}])
    assert r.status_code == 303 and r.headers["location"] == "/dang-nhap"


def test_khong_co_cong_dang_nhap_thi_khong_luu_duoc(web):
    """Máy trong công ty để trống KOME_SESSION_SECRET: không biết ai là ai —
    giao diện được báo `sap_xep_duoc: false` (xếp tạm, không lưu) và POST bị
    từ chối."""
    c = web(bi_mat=None)
    kd = _khoi_dau(c.get("/").text)
    assert kd["nguoi"] is None and kd["sap_xep_duoc"] is False and _thu_tu(c.get("/").text) == MAC
    assert _luu(c, [{"id": "han_su_dung"}]).status_code == 403


def test_ban_vercel_chi_doc_van_luu_duoc_bo_cuc(web):
    """Cùng lý lẽ POST /ngan-sach: chỉ-đọc là giới hạn của luồng NẠP OBC."""
    c = web.vao(web(vercel=True))
    assert _luu(c, [{"id": "can_han"}]).status_code == 200


def test_trang_react_chi_nap_file_tu_host(web):
    """R1: không CDN, không font ngoài — mọi <script src>/<link href> của trang
    trỏ về chính máy chủ (/assets, /static)."""
    html = web.vao(web()).get("/").text
    for src in re.findall(r'(?:src|href)="([^"]+)"', html):
        assert src.startswith(("/assets/", "/static/")), src


def test_ghi_bo_cuc_khong_them_truy_van_cho_trang_chu(web, monkeypatch, conn):
    """Bố cục đọc cùng lượt hỏi của cổng đăng nhập (cột trên app.nguoi_dung)
    — mở trang chủ khi CÓ bố cục đã lưu tốn đúng bằng số truy vấn khi không."""
    import psycopg
    c = web.vao(web())
    dem = {"n": 0}
    goc = psycopg.Connection.execute

    def dem_execute(self, *a, **k):
        dem["n"] += 1
        return goc(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", dem_execute)
    c.get("/")
    truoc = dem["n"]
    monkeypatch.setattr(psycopg.Connection, "execute", goc)
    _luu(c, [{"id": "can_han", "rong": 3}])
    monkeypatch.setattr(psycopg.Connection, "execute", dem_execute)
    dem["n"] = 0
    c.get("/")
    assert dem["n"] == truoc
