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
from tests.spa_kd import kd, man, nguon


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
    m = man(client.get("/kho-du-lieu/luong").text)
    for khoa in ("cong", "cam_bay", "lo_trinh"):
        assert m[khoa], f"ảnh chụp không được nạp ({khoa} rỗng)"
    assert all(t["muc"] for t in m["tang"]), "ảnh chụp không được nạp (bốn tầng)"


def test_moi_cot_tren_trang_co_trong_files_yml(client):
    """[IMPORTANT] Bảng "Cột trong …" phải là files.yml, không hơn không kém —
    đúng câu lộ trình §7: tài liệu sống sinh ra, không chép tay."""
    for ten, s in SPECS.items():
        r = client.get(f"/kho-du-lieu/cot-noi?file={ten}")
        tren_trang = [c["ja"] for c in man(r.text)["cot"]]
        assert tren_trang == list(s.columns), ten
    assert '<td className="cot-obc">{c.ja}</td>' in nguon("he_thong", "TaiLieu.tsx")


def test_file_la_ve_mac_dinh(client):
    r = client.get("/kho-du-lieu/cot-noi?file=khong-co")
    assert r.status_code == 200
    m = man(r.text)
    assert m["file"] == "uriage" and m["file_ja"] == "売上伝票データ"


def test_tab_danh_dau_trang_dang_xem(client):
    src = nguon("he_thong", "TaiLieu.tsx")
    assert '<KhungKho dang="luong">' in src and '<KhungKho dang="cot-noi">' in src
    tab = nguon("he_thong", "TabKho.tsx")
    assert 'aria-current={dang === ma ? "page" : undefined}' in tab


def test_trang_luong_hien_cam_bay_cong_va_bang_moi(client):
    t = client.get("/kho-du-lieu/luong").text
    m = man(t)
    anh = TL.doc_anh_chup()
    assert len(m["cam_bay"]) == len(anh["cam_bay"])
    # "Ai là sự thật": mọi bảng app của migration hiện ở thẻ của app
    ten_ranh = {x["ten"] for r in m["ranh_gioi"] for x in r["muc"]}
    for b in anh["bang"]["app"]:
        assert f"app.{b}" in ten_ranh
    for c in anh["cong"]:
        assert H.escape(c["ten"]) in t or c["ten"] in t
    assert "mart.thang_den_hom_nay" in t
    for s in SPECS.values():
        assert s.core_table in t


def test_cam_bay_khong_de_html_lot_qua(client):
    """[CRITICAL] Nguồn là CLAUDE.md / đặc tả — ai cũng sửa được. Thẻ HTML lọt
    qua là một chỗ chèn script vào màn có nút xoá dữ liệu. Giao diện dựng
    `**đậm**` / `` `mã` `` thành PHẦN TỬ React (md()), không bao giờ innerHTML;
    JSON trong <script> thoát `<`."""
    t = client.get("/kho-du-lieu/luong").text
    assert any("`" in c["cach"] for c in man(t)["cam_bay"]), "cạm bẫy phải còn đánh dấu mã để md() dựng"
    src = nguon("he_thong", "TaiLieu.tsx")
    assert "dangerouslySetInnerHTML" not in src
    assert "export function md(" in src and "<code key={k++}>" in src
    assert "</script>" not in t.split("window.__KOME__=", 1)[1].split("</script>", 1)[0]


def test_man_van_hanh_co_tab(conn, test_db_url):
    r = TestClient(A.create_app(db_url=test_db_url)).get("/kho-du-lieu")
    assert r.status_code == 200 and "man" in kd(r.text)
    src = nguon("he_thong", "KhoDuLieu.tsx")
    assert '<KhungKho dang="tong-quan" lop="kdl">' in src and '<KhungKho dang="nap" lop="kdl">' in src


def test_khong_co_quyen_kho_du_lieu_thi_tai_lieu_cung_403():
    """Hai trang nằm dưới tiền tố /kho-du-lieu/ — middleware gác sẵn. Test
    canh để không ai "mở cửa riêng" cho chúng mà nới luôn cửa màn có nút xoá."""
    assert A._thuoc_kho_du_lieu("/kho-du-lieu/luong")
    assert A._thuoc_kho_du_lieu("/kho-du-lieu/cot-noi")
