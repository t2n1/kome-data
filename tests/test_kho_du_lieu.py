"""Test màn Kho dữ liệu — màn gộp của /nap + /health + /phu-du-lieu."""
from fastapi.testclient import TestClient

from kome.web.app import create_app

# Mỗi khối một dấu hiệu nhận biết ổn định (không phải chuỗi trang trí dễ đổi).
DAU_HIEU_KHOI = {
    "tuoi du lieu": "hom-nay",
    "nap": 'id="nap"',
    "suc khoe": "Sức khoẻ dữ liệu",
    "bang 7 loai": "在庫一覧",
    "bang theo ngay": "theo-ngay",
    "bang theo thang": 'id="theo-thang"',
}


def test_man_kho_du_lieu_co_du_cac_khoi(conn, test_db_url):
    """[IMPORTANT] Gộp ba trang thành một là lúc dễ đánh rơi một khối nhất:
    trang vẫn 200, vẫn đẹp, chỉ thiếu đúng thứ ai đó cần. Test này đếm từng
    khối thay vì chỉ kiểm mã trả về."""
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/kho-du-lieu")
    assert r.status_code == 200
    for ten, dau_hieu in DAU_HIEU_KHOI.items():
        assert dau_hieu in r.text, f"thiếu khối: {ten}"


def test_man_co_hai_neo_cho_dau_trang_cu(conn, test_db_url):
    """Dấu trang cũ /nap và /phu-du-lieu sẽ được chuyển hướng kèm neo
    #nap / #theo-thang. Neo không tồn tại thì người bấm rơi lên đầu trang
    và phải cuộn đi tìm — đúng thứ chuyển hướng sinh ra để tránh."""
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert 'id="nap"' in html
    assert 'id="theo-thang"' in html


def test_ban_chi_doc_an_o_tha_file(conn, test_db_url, monkeypatch):
    """Bản công khai không nạp được. Hiện ô thả file ở đó là mời người ta
    kéo một file 100 MB vào một endpoint luôn trả 403."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert 'id="nap"' not in html
    assert "在庫一覧" in html, "khối chỉ-đọc khác vẫn phải hiện"
