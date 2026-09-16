from pathlib import Path
from kome import archive

OK = Path("tests/fixtures/zaiko_ok.xlsx")

def test_hash_on_dinh():
    assert archive.sha256_of(OK) == archive.sha256_of(OK)

def test_nhan_ra_file_da_nap(conn, tmp_path):
    d = archive.sha256_of(OK)
    assert archive.already_loaded(conn, d) is False
    archive.store(conn, OK, "zaiko", d, 177, 137_839_071, tmp_path)
    assert archive.already_loaded(conn, d) is True

def test_luu_tru_file_goc(conn, tmp_path):
    d = archive.sha256_of(OK)
    archive.store(conn, OK, "zaiko", d, 177, 137_839_071, tmp_path)
    saved = list(tmp_path.rglob("*.xlsx"))
    assert len(saved) == 1
    assert d[:12] in saved[0].name

def test_previous_stats(conn, tmp_path):
    archive.store(conn, OK, "zaiko", "aaa", 177, 137_839_071, tmp_path)
    prev = archive.previous_stats(conn, "zaiko")
    assert prev["row_count"] == 177 and prev["total"] == 137_839_071

def test_undo_khong_xoa_dong(conn, tmp_path):
    d = archive.sha256_of(OK)
    bid = archive.store(conn, OK, "zaiko", d, 177, 137_839_071, tmp_path)
    archive.undo(conn, bid)
    n, undone = conn.execute(
        "SELECT count(*), count(undone_at) FROM meta.ingest_batch WHERE batch_id = %s", (bid,)
    ).fetchone()
    assert n == 1 and undone == 1          # luật bất biến #6: không xoá dòng

def test_hoan_tac_roi_nap_lai_duoc(conn, tmp_path):
    d = archive.sha256_of(OK)
    bid = archive.store(conn, OK, "zaiko", d, 177, 137_839_071, tmp_path)
    archive.undo(conn, bid)
    assert archive.already_loaded(conn, d) is False
    bid2 = archive.store(conn, OK, "zaiko", d, 177, 137_839_071, tmp_path)   # KHÔNG được crash
    assert bid2 != bid
    assert archive.already_loaded(conn, d) is True
