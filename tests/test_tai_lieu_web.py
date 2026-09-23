"""Test hai trang tài liệu sống của màn Kho dữ liệu (đợt 2b).

Không cần CSDL: hai trang này 0 truy vấn, và chính điều đó được test canh
bằng cách làm nổ mọi lần mở kết nối."""
import html as H
import re

import pytest
from fastapi.testclient import TestClient

import kome.web.app as A
from kome import tai_lieu as TL
from kome.config import SPECS


@pytest.fixture
def client(monkeypatch):
    """[IMPORTANT] `connect` bị thay bằng hàm nổ: trang nào lỡ mở kết nối là
    500 ngay, không lặng lẽ tốn thêm 47 ms mỗi lượt hỏi."""
    def no(*a, **k):
        raise AssertionError("trang tài liệu không được mở kết nối CSDL")
    monkeypatch.setattr(A, "connect", no)
    monkeypatch.delenv("KOME_SESSION_SECRET", raising=False)
    return TestClient(A.create_app(db_url="postgresql://khong-dung"))


def test_hai_trang_200_khong_truy_van(client):
    for d in ("/kho-du-lieu/luong", "/kho-du-lieu/cot-noi"):
        r = client.get(d)
        assert r.status_code == 200, d
        assert "Chưa sinh tài liệu" not in r.text, "ảnh chụp không được nạp"


def test_moi_cot_tren_trang_co_trong_files_yml(client):
    """[IMPORTANT] Bảng "Cột trong …" phải là files.yml, không hơn không kém —
    đúng câu lộ trình §7: tài liệu sống sinh ra, không chép tay."""
    for ten, s in SPECS.items():
        r = client.get(f"/kho-du-lieu/cot-noi?file={ten}")
        khoi = r.text.split('id="cot"', 1)[1]
        tren_trang = [H.unescape(x) for x in re.findall(r'<td class="cot-obc">(.*?)</td>', khoi)]
        assert tren_trang == list(s.columns), ten


def test_file_la_ve_mac_dinh(client):
    r = client.get("/kho-du-lieu/cot-noi?file=khong-co")
    assert r.status_code == 200
    assert "Cột trong 売上伝票データ" in r.text


def test_tab_danh_dau_trang_dang_xem(client):
    r = client.get("/kho-du-lieu/luong")
    assert re.search(r'href="/kho-du-lieu/luong" class="dang-xem" aria-current="page"', r.text)
    assert not re.search(r'href="/kho-du-lieu/cot-noi" class="dang-xem"', r.text)


def test_trang_luong_hien_cam_bay_cong_va_bang_moi(client):
    t = client.get("/kho-du-lieu/luong").text
    anh = TL.doc_anh_chup()
    assert t.count("<li>", t.index('id="cam-bay"'), t.index('id="lo-trinh"')) == len(anh["cam_bay"])
    for c in anh["cong"]:
        assert H.escape(c["ten"]) in t or c["ten"] in t
    assert "mart.thang_den_hom_nay" in t
    for s in SPECS.values():
        assert s.core_table in t


def test_cam_bay_khong_de_html_lot_qua(client):
    t = client.get("/kho-du-lieu/luong").text
    khoi = t[t.index('id="cam-bay"'):t.index('id="lo-trinh"')]
    assert "<code>" in khoi, "md_dong không được áp"
    assert "**" not in khoi


def test_man_van_hanh_co_tab(conn, test_db_url):
    r = TestClient(A.create_app(db_url=test_db_url)).get("/kho-du-lieu")
    assert 'href="/kho-du-lieu" class="dang-xem" aria-current="page"' in r.text


def test_khong_co_quyen_kho_du_lieu_thi_tai_lieu_cung_403():
    """Hai trang nằm dưới tiền tố /kho-du-lieu/ — middleware gác sẵn. Test
    canh để không ai "mở cửa riêng" cho chúng mà nới luôn cửa màn có nút xoá."""
    assert A._thuoc_kho_du_lieu("/kho-du-lieu/luong")
    assert A._thuoc_kho_du_lieu("/kho-du-lieu/cot-noi")
