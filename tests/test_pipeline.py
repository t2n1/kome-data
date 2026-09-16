from pathlib import Path
import shutil
from db.migrate import apply_all
from kome.pipeline import ingest

OK = Path("tests/fixtures/zaiko_ok.xlsx")

def _staged(tmp_path):
    dest = tmp_path / "在庫一覧_20260916.xlsx"
    shutil.copy2(OK, dest)
    return dest

def test_nap_thanh_cong(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    r = ingest(conn, _staged(tmp_path), tmp_path / "archive")
    assert r.ok and r.row_count == 177 and r.total == 137_839_071
    assert r.blockers == []

def test_nap_lai_cung_file_bi_bo_qua(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    p = _staged(tmp_path)
    ingest(conn, p, tmp_path / "archive")
    second = ingest(conn, p, tmp_path / "archive")
    assert second.skipped is True

def test_file_cat_cut_bi_chan_va_khong_ghi_gi(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    dest = tmp_path / "在庫一覧_20260916.xlsx"
    shutil.copy2("tests/fixtures/zaiko_cat_cut.xlsx", dest)
    r = ingest(conn, dest, tmp_path / "archive")
    assert not r.ok and any(b.gate == 3 for b in r.blockers)
    n = conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0]
    assert n == 0
