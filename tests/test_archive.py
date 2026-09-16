from pathlib import Path
from db.migrate import apply_all
from kome import archive

OK = Path("tests/fixtures/zaiko_ok.xlsx")

def test_hash_on_dinh():
    assert archive.sha256_of(OK) == archive.sha256_of(OK)

def test_nhan_ra_file_da_nap(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    d = archive.sha256_of(OK)
    assert archive.already_loaded(conn, d) is False
    archive.store(conn, OK, "zaiko", d, 177, 137_839_071, tmp_path)
    assert archive.already_loaded(conn, d) is True

def test_luu_tru_file_goc(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    d = archive.sha256_of(OK)
    archive.store(conn, OK, "zaiko", d, 177, 137_839_071, tmp_path)
    saved = list(tmp_path.rglob("*.xlsx"))
    assert len(saved) == 1
    assert d[:12] in saved[0].name

def test_previous_stats(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    archive.store(conn, OK, "zaiko", "aaa", 177, 137_839_071, tmp_path)
    prev = archive.previous_stats(conn, "zaiko")
    assert prev["row_count"] == 177 and prev["total"] == 137_839_071
