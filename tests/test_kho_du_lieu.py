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


def test_khoi_hoan_tac_hien_lo_va_giau_nut_sau_mot_buoc(conn, test_db_url):
    """[IMPORTANT] Hoàn tác XOÁ dữ liệu khỏi core và không thể hoàn lại.
    Nút không được nằm trần trên một màn người ta mở mỗi ngày: <details>
    bắt người bấm đọc hậu quả trước khi thấy cái nút."""
    conn.execute("DELETE FROM meta.ingest_batch")
    conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count,
              total_amount, data_date)
           VALUES ('zaiko', '在庫一覧_20260101.xlsx', 'dg1', 'test', 177, 0, '2026-01-01')""")
    conn.commit()
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text

    assert "在庫一覧_20260101.xlsx" in html
    assert "<details" in html and "Hoàn tác" in html
    assert "177" in html, "phải nói rõ sẽ xoá bao nhiêu dòng"
    assert "Không thể hoàn lại" in html


def test_ban_chi_doc_an_khoi_hoan_tac(conn, test_db_url, monkeypatch):
    """Bản công khai không hoàn tác được (route trả 403). Hiện nút ở đó là
    mời người ta bấm một thứ chắc chắn thất bại — và là nút XOÁ."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert "/undo/" not in html


def test_hoan_tac_master_upsert_hien_canh_bao_se_trong(conn, test_db_url):
    """[IMPORTANT] Bốn loại master (shohin/shiiresaki/chokusousaki/tanka) nạp
    bằng upsert: mỗi lần nạp dán batch_id MỚI lên mọi dòng, nên hoàn tác
    (`DELETE WHERE batch_id`) quét sạch CẢ BẢNG chứ không lùi về lô trước —
    khác hẳn ba loại fact/SCD2 còn lại. Sự cố thật đã xảy ra vì thiếu cảnh báo
    này: hoàn tác một lô shiiresaki 49 dòng, tưởng lùi về 48, thực tế còn 0."""
    conn.execute("DELETE FROM meta.ingest_batch")
    conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count,
              total_amount, data_date)
           VALUES ('shiiresaki', '仕入先_20260908.xlsx', 'dg2', 'test', 49, 0, '2026-09-08')""")
    conn.commit()
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert "sẽ trống hoàn toàn" in html
    assert "không lùi về lần nạp trước" in html


def test_hoan_tac_fact_khong_hien_canh_bao_se_trong(conn, test_db_url):
    """Ba loại fact/SCD2 (uriage/meisai/zaiko/tokuisaki) lùi đúng một lô khi
    hoàn tác. Dán cảnh báo "sẽ trống" lên cả loại không cần sẽ dạy người đọc
    coi thường cảnh báo — quan trọng ngang test trên."""
    conn.execute("DELETE FROM meta.ingest_batch")
    conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count,
              total_amount, data_date)
           VALUES ('uriage', '売上伝票データ_20260916.xlsx', 'dg3', 'test', 100, 5000, '2026-09-16')""")
    conn.commit()
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert "sẽ trống hoàn toàn" not in html


def test_ba_dia_chi_cu_chuyen_huong_301(conn, test_db_url):
    """[IMPORTANT] Ba địa chỉ này nằm trong runbook và trong dấu trang của
    người dùng. Trả 404 là phạt họ vì một thay đổi họ không gây ra.

    follow_redirects=False: TestClient mặc định ĐI THEO chuyển hướng, nên
    không tắt thì test này xanh cả khi route trả 200 mà chẳng chuyển hướng gì.
    """
    client = TestClient(create_app(db_url=test_db_url))
    mong_doi = {"/health": "/kho-du-lieu",
                "/nap": "/kho-du-lieu#nap",
                "/phu-du-lieu": "/kho-du-lieu#theo-thang"}
    for cu, moi in mong_doi.items():
        r = client.get(cu, follow_redirects=False)
        assert r.status_code == 301, f"{cu} trả {r.status_code}, phải 301"
        assert r.headers["location"] == moi, f"{cu} trỏ sai đích"


def test_nap_van_chuyen_huong_o_ban_chi_doc(conn, test_db_url, monkeypatch):
    """Dấu trang /nap cũ trên bản công khai phải rơi vào màn (tự ẩn khối
    nạp), không phải một trang 403. 403 cho một dấu trang cũ là phạt người
    dùng vì một thay đổi họ không gây ra."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/nap", follow_redirects=False)
    assert r.status_code == 301


def test_upload_render_man_gop(conn, test_db_url):
    """Nạp xong phải rơi lại vào màn gộp kèm kết quả — không phải một
    template đã bị xoá."""
    client = TestClient(create_app(db_url=test_db_url))
    with open("tests/fixtures/zaiko_cat_cut.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 200
    assert 'id="theo-thang"' in r.text, "phải là màn gộp, không phải trang nạp cũ"
    assert "nghi file xuất một phần" in r.text, "kết quả nạp vẫn phải hiện"
