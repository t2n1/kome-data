
def test_nam_tai_chinh_nhat(conn):
    # Tháng 4 trở đi thuộc năm tài chính cùng số; tháng 1-3 thuộc năm trước
    r = conn.execute("SELECT fiscal_year FROM core.dim_date WHERE date_key = '2026-09-16'").fetchone()
    assert r[0] == 2026
    r = conn.execute("SELECT fiscal_year FROM core.dim_date WHERE date_key = '2026-03-31'").fetchone()
    assert r[0] == 2025

def test_phu_du_pham_vi(conn):
    r = conn.execute("SELECT min(date_key), max(date_key), count(*) FROM core.dim_date").fetchone()
    assert str(r[0]) == "2024-01-01" and str(r[1]) == "2035-12-31"
    assert r[2] == 4383
