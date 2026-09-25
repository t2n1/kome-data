"""Nạp hằng ngày trên bản Vercel (đặc tả 2026-09-25-nap-tren-vercel-design.md).

Trên Vercel ổ đĩa là tạm: file chờ xác nhận nằm trong `meta.nap_cho` (migration 045), file
gốc KHÔNG được lưu (`archived_to` NULL). Sai nguy hiểm nhất: lô không file gốc làm hỏng chặn
nạp trùng hay hoàn tác, và quyền mới trên `meta` lỡ cho xoá sổ lịch sử `meta.ingest_batch`."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from kome import nap_cho
from kome.pipeline import ingest, undo_batch

OK = Path("tests/fixtures/zaiko_ok.xlsx")
TEN = "在庫一覧_20260916.xlsx"


def _chep(tmp_path) -> Path:
    p = tmp_path / TEN
    p.write_bytes(OK.read_bytes())
    return p


# ---- Task 1: lô không có file gốc + quyền của 045 -------------------------

def test_lo_khong_file_goc_van_chan_nap_trung_va_hoan_tac_duoc(conn, tmp_path):
    p = _chep(tmp_path)
    kq = ingest(conn, p, None)
    assert kq.ok and kq.batch_id and not kq.skipped
    assert conn.execute("SELECT archived_to FROM meta.ingest_batch WHERE batch_id = %s",
                        (kq.batch_id,)).fetchone()[0] is None
    # Mã băm vẫn ghi — nạp lại cùng file bị bỏ qua, không thành hai lô.
    assert ingest(conn, p, None).skipped
    assert undo_batch(conn, kq.batch_id) > 0
    assert conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0] == 0


def test_quyen_045_chi_xoa_duoc_file_cho_khong_xoa_duoc_so_lich_su(conn):
    """[CRITICAL] kome_ingest được DELETE đúng meta.nap_cho — sổ meta.ingest_batch vẫn
    không xoá được (hoàn tác chỉ đặt undone_at). kome_app không chạm được file chờ."""
    r = conn.execute(
        """SELECT has_table_privilege('kome_ingest', 'meta.nap_cho', 'INSERT'),
                  has_table_privilege('kome_ingest', 'meta.nap_cho', 'SELECT'),
                  has_table_privilege('kome_ingest', 'meta.nap_cho', 'DELETE'),
                  has_table_privilege('kome_ingest', 'meta.ingest_batch', 'DELETE'),
                  has_table_privilege('kome_app', 'meta.nap_cho', 'SELECT'),
                  has_table_privilege('kome_report', 'meta.nap_cho', 'SELECT')""").fetchone()
    assert r == (True, True, True, False, False, False)
