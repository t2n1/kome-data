import os
import time
from fastapi.testclient import TestClient
from kome.web.app import create_app

def test_trang_suc_khoe_mo_duoc(conn, test_db_url):
    client = TestClient(create_app(db_url=test_db_url))   # KHÔNG bao giờ để nó tự lấy DATABASE_URL
    r = client.get("/health")
    assert r.status_code == 200
    assert "在庫一覧" in r.text

def test_health_canh_bao_khi_sao_luu_qua_han(conn, test_db_url, tmp_path, monkeypatch):
    """Trang /health phải tự cảnh báo nếu bản sao lưu mới nhất cũ hơn 36 giờ,
    và hết cảnh báo khi có bản mới — sai phải hiện ngay lúc người ta còn ngồi đó."""
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    client = TestClient(create_app(db_url=test_db_url))

    z = tmp_path / "kome_20260101.zip"
    z.write_bytes(b"x")
    old = time.time() - 40 * 3600          # 40 giờ trước -> quá hạn
    os.utime(z, (old, old))

    r = client.get("/health")
    assert r.status_code == 200
    assert "Chưa sao lưu" in r.text

    new = time.time() - 1 * 3600           # 1 giờ trước -> còn mới
    os.utime(z, (new, new))

    r = client.get("/health")
    assert "Chưa sao lưu" not in r.text
    assert "Sao lưu gần nhất" in r.text

def test_upload_file_hong_tra_ve_loi_de_hieu(conn, test_db_url):
    client = TestClient(create_app(db_url=test_db_url))
    with open("tests/fixtures/zaiko_cat_cut.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 200
    assert "nghi file xuất một phần" in r.text

def test_undo_qua_http_xoa_du_lieu_giu_lich_su(conn, test_db_url):
    client = TestClient(create_app(db_url=test_db_url))
    with open("tests/fixtures/zaiko_ok.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 200

    n = conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0]
    assert n == 177

    batch_id = conn.execute(
        "SELECT batch_id FROM meta.ingest_batch ORDER BY batch_id DESC LIMIT 1"
    ).fetchone()[0]

    r = client.post(f"/undo/{batch_id}")
    assert r.status_code == 200

    n = conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0]
    assert n == 0

    rows = conn.execute(
        "SELECT undone_at FROM meta.ingest_batch WHERE batch_id = %s", (batch_id,)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] is not None

def test_health_hien_lan_nap_GAN_NHAT_khong_phai_lon_nhat(conn, test_db_url):
    """[IMPORTANT] max(loaded_at), max(row_count), max(total_amount) là ba hàm
    độc lập lấy từ ba dòng khác nhau. uriage nạp hằng ngày ~843 dòng; đầu tháng
    nạp đối soát cả tháng ~18.000 dòng — từ đó /health LUÔN hiện 18.000, kể cả
    hôm nay OBC xuất cắt cụt còn 60 dòng. Trang duy nhất để biết hệ thống có
    hỏng không lại không phản ánh lần nạp gần nhất."""
    for digest, rows, total, tre in (("to", 18000, 400_000_000, "2 hours"),
                                     ("nho", 60, 900_000, "1 minute")):
        conn.execute(
            """INSERT INTO meta.ingest_batch
                 (spec_name, source_file, digest, archived_to, row_count,
                  total_amount, loaded_at)
               VALUES ('uriage', 'u.xlsx', %s, '/tmp/u.xlsx', %s, %s, now() - %s::interval)""",
            (digest, rows, total, tre),
        )
    conn.commit()

    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/health")
    assert r.status_code == 200
    assert "60" in r.text and "900,000" in r.text
    assert "18,000" not in r.text and "400,000,000" not in r.text


def test_health_liet_ke_ngay_lam_viec_bi_thieu(conn, test_db_url, batch):
    """[IMPORTANT] Không có gì khác trong hệ thống phát hiện thiếu hẳn một
    ngày: nhân viên nghỉ ốm thứ Ba, không ai kéo–thả; thứ Tư nạp bình thường,
    /health xanh hết. Ba tháng sau báo cáo thiếu một ngày và không ai truy
    được ngày nào.

    Nạp hai ngày cách nhau đúng một ngày làm việc (Hai 2026-05-11 và Tư
    2026-05-13) -> trang phải nêu đích danh thứ Ba 2026-05-12."""
    from datetime import date
    import pandas as pd
    from kome.loaders import sales

    b = batch(1)
    rows = []
    for i, d in enumerate((date(2026, 5, 11), date(2026, 5, 13))):
        rows.append({
            "slip_no": f"0799{i}", "line_seq": 1, "sales_date": d,
            "customer_code": "000000009292", "product_code": "XT07",
            "pack_code": "02", "case_qty": 1, "qty": 6, "unit_price": 5250,
            "unit_cost": 3210, "amount": 29167, "tax_amount": 2333,
            "cost": 19260, "gross_profit": 9907, "paid_amount": 0,
            "batch_id": b,
        })
    sales.load(conn, pd.DataFrame(rows), date(2026, 5, 13), b)

    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/health")
    assert r.status_code == 200
    assert "2026-05-11" in r.text and "2026-05-13" in r.text   # kỳ dữ liệu
    assert "Thiếu 1 ngày làm việc" in r.text
    assert "2026-05-12" in r.text
    # cuối tuần 2026-05-09 (Bảy) / 2026-05-10 (CN) nằm ngoài kỳ, không được kể


def test_loi_ngoai_du_kien_hien_tieng_viet_khong_lo_chuoi_ngoai_le(
        conn, test_db_url, monkeypatch):
    """Nửa NHÌN THẤY ĐƯỢC của lỗi lô mồ côi: người dùng gặp trang 500 tiếng Anh
    khó hiểu rồi thử lại và được báo 'xanh'. Lỗi ngoài dự kiến phải ra thông
    báo tiếng Việt, và KHÔNG chứa nguyên văn chuỗi ngoại lệ của thư viện."""
    import kome.web.app as W

    def no_tung(*a, **kw):
        raise RuntimeError("psycopg.OperationalError: connection reset by peer")

    monkeypatch.setattr(W, "ingest", no_tung)
    client = TestClient(create_app(db_url=test_db_url), raise_server_exceptions=False)
    with open("tests/fixtures/zaiko_ok.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})

    assert r.status_code == 500
    assert "Hệ thống gặp lỗi" in r.text
    assert "Dữ liệu chưa được nạp" in r.text
    assert "connection reset by peer" not in r.text
    assert "RuntimeError" not in r.text
    assert "Traceback" not in r.text
