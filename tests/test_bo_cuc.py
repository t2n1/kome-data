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


# ---- chuan_hoa: không tin trình duyệt ---------------------------------

@pytest.mark.parametrize("tho", [None, "", "không phải json", "{}", 42, [1, "x", None], {"id": "chi_so"}])
def test_rac_thi_ve_mac_dinh_khong_nem_loi(tho):
    assert BC.chuan_hoa(tho) == BC.mac_dinh()


def test_giu_thu_tu_va_noi_khoi_thieu_vao_cuoi():
    """Bố cục lưu từ trước khi code thêm một khối vẫn đọc được — khối mới
    nối vào CUỐI, không vứt cả bố cục về mặc định như gói thiết kế."""
    ra = BC.chuan_hoa([{"id": "can_han", "rong": 3, "cao": 1}, {"id": "chi_so", "rong": 1, "cao": 4}])
    assert [o.id for o in ra[:2]] == ["can_han", "chi_so"]
    assert (ra[0].rong, ra[0].cao, ra[1].rong, ra[1].cao) == (3, 1, 1, 4)
    assert sorted(o.id for o in ra) == sorted(MA)
    assert all(not o.an for o in ra)


def test_bo_ma_la_va_ma_trung():
    ra = BC.chuan_hoa([{"id": "xoa_du_lieu"}, {"id": "chi_so", "rong": 2},
                       {"id": "chi_so", "rong": 3}, {"id": "__proto__"}])
    assert [o.id for o in ra].count("chi_so") == 1
    assert ra[0].id == "chi_so" and ra[0].rong == 2
    assert len(ra) == len(MA)


@pytest.mark.parametrize("rong,cao,mong", [
    (0, 0, (1, 1)), (-5, 99, (1, 4)), (7, 2, (3, 2)), (2.9, 3.2, (2, 3)),
    ("3", "2", None), (True, True, None), (None, None, None),
])
def test_kich_thuoc_kep_trong_dai_kieu_sai_lay_mac_dinh(rong, cao, mong):
    o = BC.chuan_hoa([{"id": "xu_huong", "rong": rong, "cao": cao}])[0]
    if mong is None:          # chuỗi, bool, thiếu -> mặc định của khối (2, 2)
        mong = (2, 2)
    assert (o.rong, o.cao) == mong


def test_an_chi_nhan_dung_true():
    ra = {o.id: o.an for o in BC.chuan_hoa([{"id": "chi_so", "an": True}, {"id": "xu_huong", "an": "true"},
                                            {"id": "can_goi", "an": 1}])}
    assert ra["chi_so"] is True and ra["xu_huong"] is False and ra["can_goi"] is False


def test_doc_duoc_chuoi_json():
    ra = BC.chuan_hoa(json.dumps([{"id": "suc_khoe", "rong": 3, "cao": 1, "an": True}]))
    assert ra[0] == BC.O("suc_khoe", 3, 1, True)


def test_moi_khoi_trong_KHOI_co_macro_trong_template_va_nguoc_lai():
    """Thêm khối là thêm MỘT dòng vào KHOI và MỘT macro cùng tên — lệch là
    trang chủ nổ KeyError (khối chỉ có ở Python) hoặc khối vẽ được mà không
    bao giờ hiện (chỉ có ở template)."""
    html = (GOC / "kome/web/templates/tong_quan.html").read_text(encoding="utf-8")
    ve = re.search(r"\{% set VE = \{(.*?)\} %\}", html, re.S).group(1)
    assert set(re.findall(r'"(\w+)":\s*khoi_\1\b', ve)) == set(MA)
    for ma in MA:
        assert f"{{% macro khoi_{ma}(o) %}}" in html


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


def _thu_tu(html):
    return re.findall(r'<section class="khoi-tq" data-khoi="(\w+)"', html)


def test_luu_roi_trang_ve_SAN_dung_thu_tu_va_kich_thuoc(web, conn):
    """Máy chủ vẽ đúng bố cục đã lưu trong HTML đầu tiên — không có khung
    hình mặc định rồi giật sang bố cục của mình (cùng lý lẽ cookie giao diện)."""
    c = web.vao(web())
    r = _luu(c, [{"id": "can_han", "rong": 3, "cao": 1}, {"id": "chi_so", "rong": 1, "cao": 3}])
    assert r.status_code == 200
    assert r.json()["bo_cuc"][0] == {"id": "can_han", "rong": 3, "cao": 1, "an": False}

    html = c.get("/").text
    assert _thu_tu(html)[:2] == ["can_han", "chi_so"]
    assert re.search(r'data-khoi="can_han"[^>]*style="grid-column:span 3;grid-row:span 1"', html)
    assert re.search(r'data-khoi="chi_so"[^>]*style="grid-column:span 1;grid-row:span 3"', html)
    luu = conn.execute("SELECT bo_cuc_tong_quan FROM app.nguoi_dung WHERE ten_dang_nhap='an'").fetchone()[0]
    assert [x["id"] for x in luu][:2] == ["can_han", "chi_so"] and len(luu) == len(MA)


def test_khoi_an_van_co_trong_trang_nhung_hidden_va_nam_trong_o_them(web):
    """Khối ẩn vẫn được vẽ (thuộc tính `hidden`) để bấm "Hiện" là thấy ngay,
    không phải tải lại trang; và nó nằm trong ô "Thêm chức năng"."""
    c = web.vao(web())
    _luu(c, [{"id": "xu_huong", "an": True}])
    html = c.get("/").text
    assert re.search(r'data-khoi="xu_huong"[^>]*\bhidden\b', html)
    assert re.search(r'data-muc-an="xu_huong">', html)             # mục hiện lại KHÔNG hidden
    assert re.search(r'data-muc-an="chi_so" hidden', html)
    assert "(<span data-dem-an>1</span> đang ẩn)" in html


def test_hai_nguoi_hai_bo_cuc(web):
    a = web.vao(web(), "an")
    _luu(a, [{"id": "can_goi"}])
    b = web.vao(web(), "binh")
    _luu(b, [{"id": "suc_khoe"}])
    assert _thu_tu(a.get("/").text)[0] == "can_goi"
    assert _thu_tu(b.get("/").text)[0] == "suc_khoe"


def test_ve_mac_dinh_bang_form_thuong(web, conn):
    c = web.vao(web())
    _luu(c, [{"id": "can_han"}])
    r = c.post("/tong-quan/bo-cuc/mac-dinh")
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert _thu_tu(c.get("/").text) == MA
    assert conn.execute("SELECT bo_cuc_tong_quan FROM app.nguoi_dung WHERE ten_dang_nhap='an'").fetchone()[0] is None


def test_bo_cuc_rac_trong_csdl_khong_lam_hong_trang_chu(web, conn):
    c = web.vao(web())
    conn.execute("""UPDATE app.nguoi_dung SET bo_cuc_tong_quan = '{"la": "rac"}'::jsonb
                    WHERE ten_dang_nhap = 'an'""")
    conn.commit()
    r = c.get("/")
    assert r.status_code == 200 and _thu_tu(r.text) == MA


def test_chi_nhan_json_va_chan_than_qua_lon(web):
    c = web.vao(web())
    assert c.post("/tong-quan/bo-cuc", data={"id": "chi_so"}).status_code == 415
    lon = [{"id": "chi_so", "rac": "x" * BC.DAI_TOI_DA}]
    assert _luu(c, lon).status_code == 413


def test_chua_dang_nhap_thi_bi_cong_chan(web):
    r = _luu(web(), [{"id": "can_han"}])
    assert r.status_code == 303 and r.headers["location"] == "/dang-nhap"


def test_khong_co_cong_dang_nhap_thi_khong_co_nut_va_khong_luu(web):
    """Máy trong công ty để trống KOME_SESSION_SECRET: không biết ai là ai,
    nên không có nút nào hứa "lưu bố cục của bạn" — và POST bị từ chối."""
    c = web(bi_mat=None)
    html = c.get("/").text
    assert _thu_tu(html) == MA
    for dau in ('class="keo-khoi"', 'class="an-khoi"', 'class="co-gian"', 'src="/static/tong_quan.js"',
                "Về bố cục mặc định", "data-luu="):
        assert dau not in html, dau
    assert _luu(c, [{"id": "can_han"}]).status_code == 403


def test_ban_vercel_chi_doc_van_luu_duoc_bo_cuc(web):
    """Cùng lý lẽ POST /ngan-sach: chỉ-đọc là giới hạn của luồng NẠP OBC."""
    c = web.vao(web(vercel=True))
    assert _luu(c, [{"id": "can_han"}]).status_code == 200


def test_script_duy_nhat_la_file_tu_host_va_khong_goi_ra_ngoai(web):
    """File JS duy nhất của app: tự host (không CDN — R1) và chỉ gọi về chính
    máy chủ. Mọi trang khác vẫn không có <script> (test riêng từng trang)."""
    html = web.vao(web()).get("/").text
    assert re.findall(r"<script[^>]*>", html) == ['<script src="/static/tong_quan.js" defer>']
    js = (GOC / "kome/web/static/tong_quan.js").read_text(encoding="utf-8")
    assert "http://" not in js and "https://" not in js
    assert "localStorage" not in js


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
