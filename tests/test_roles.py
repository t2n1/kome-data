from pathlib import Path
from db.migrate import apply_all


def test_report_chi_duoc_doc(fresh_conn):
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_report', 'core.fact_sales_line', 'SELECT'),
                  has_table_privilege('kome_report', 'core.fact_sales_line', 'INSERT')"""
    ).fetchone()
    assert r[0] is True and r[1] is False


def test_app_khong_duoc_ghi_vao_core(fresh_conn):
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_app', 'core.fact_sales_line', 'SELECT'),
                  has_table_privilege('kome_app', 'core.fact_sales_line', 'UPDATE')"""
    ).fetchone()
    assert r[0] is True and r[1] is False   # luật bất biến #1


def test_ingest_lam_duoc_viec_cua_no(fresh_conn):
    """Không chỉ kiểm vai trò khác BỊ CHẶN — phải kiểm vai trò nạp dữ liệu
    LÀM ĐƯỢC VIỆC của nó. 009 cấp SELECT/INSERT/UPDATE nhưng THIẾU DELETE,
    trong khi kome/pipeline.py hoàn tác bằng DELETE FROM core.… WHERE batch_id.
    Ngay khi runbook bảo đổi DATABASE_URL sang kome_ingest_user thì sự cố đầu
    bảng của runbook và route /undo/{batch_id} đều chết với permission denied.
    """
    apply_all(fresh_conn, Path("db/migrations"))
    for bang in ("core.fact_sales_line", "core.dim_customer", "core.fact_inventory_daily"):
        r = fresh_conn.execute(
            """SELECT has_table_privilege('kome_ingest', %s, 'SELECT'),
                      has_table_privilege('kome_ingest', %s, 'INSERT'),
                      has_table_privilege('kome_ingest', %s, 'UPDATE'),
                      has_table_privilege('kome_ingest', %s, 'DELETE')""",
            (bang, bang, bang, bang),
        ).fetchone()
        assert all(r), f"{bang}: kome_ingest thiếu quyền {r}"


def test_ingest_khong_xoa_duoc_nhat_ky_nap(fresh_conn):
    """meta.ingest_batch là bảng lịch sử: hoàn tác chỉ đặt undone_at, không bao
    giờ xoá dòng (luật bất biến #6). CSDL phải giữ luôn điều đó."""
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_ingest', 'meta.ingest_batch', 'INSERT'),
                  has_table_privilege('kome_ingest', 'meta.ingest_batch', 'UPDATE'),
                  has_table_privilege('kome_ingest', 'meta.ingest_batch', 'DELETE')"""
    ).fetchone()
    assert r[0] is True and r[1] is True and r[2] is False
