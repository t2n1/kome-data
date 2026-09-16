from pathlib import Path
from fastapi.testclient import TestClient
from db.migrate import apply_all
from kome.web.app import create_app

def test_trang_suc_khoe_mo_duoc(conn, test_db_url):
    apply_all(conn, Path("db/migrations"))
    client = TestClient(create_app(db_url=test_db_url))   # KHÔNG bao giờ để nó tự lấy DATABASE_URL
    r = client.get("/health")
    assert r.status_code == 200
    assert "在庫一覧" in r.text

def test_upload_file_hong_tra_ve_loi_de_hieu(conn, test_db_url):
    apply_all(conn, Path("db/migrations"))
    client = TestClient(create_app(db_url=test_db_url))
    with open("tests/fixtures/zaiko_cat_cut.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 200
    assert "nghi file xuất một phần" in r.text

def test_undo_qua_http_xoa_du_lieu_giu_lich_su(conn, test_db_url):
    apply_all(conn, Path("db/migrations"))
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
