from pathlib import Path
from db.migrate import apply_all


def test_report_chi_duoc_doc(conn):
    apply_all(conn, Path("db/migrations"))
    r = conn.execute(
        """SELECT has_table_privilege('kome_report', 'core.fact_sales_line', 'SELECT'),
                  has_table_privilege('kome_report', 'core.fact_sales_line', 'INSERT')"""
    ).fetchone()
    assert r[0] is True and r[1] is False


def test_app_khong_duoc_ghi_vao_core(conn):
    apply_all(conn, Path("db/migrations"))
    r = conn.execute(
        """SELECT has_table_privilege('kome_app', 'core.fact_sales_line', 'SELECT'),
                  has_table_privilege('kome_app', 'core.fact_sales_line', 'UPDATE')"""
    ).fetchone()
    assert r[0] is True and r[1] is False   # luật bất biến #1
