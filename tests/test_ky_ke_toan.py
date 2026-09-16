"""Kỳ kế toán của công ty: 1 tháng 8 → 31 tháng 7 năm sau.

KHÔNG phải năm tài chính Nhật chuẩn (1/4 → 31/3). Tháng 7 là tháng chốt kỳ.
"""
from pathlib import Path
from db.migrate import apply_all


def test_ranh_gioi_ky(conn):
    """31/7 là ngày cuối kỳ, 1/8 là ngày đầu kỳ tiếp theo."""
    rows = {
        str(r[0]): (r[1], r[2])
        for r in conn.execute(
            """SELECT date_key, company_fy, company_fy_month FROM core.dim_date
               WHERE date_key IN ('2025-07-31','2025-08-01','2026-07-31','2026-08-01')"""
        ).fetchall()
    }
    assert rows["2025-07-31"] == (2025, 12)   # ngày cuối kỳ 2025, tháng thứ 12
    assert rows["2025-08-01"] == (2026, 1)    # ngày đầu kỳ 2026, tháng thứ 1
    assert rows["2026-07-31"] == (2026, 12)
    assert rows["2026-08-01"] == (2027, 1)


def test_moi_ky_du_12_thang(conn):
    r = conn.execute(
        """SELECT count(DISTINCT company_fy_month), count(*)
           FROM core.dim_date WHERE company_fy = 2026"""
    ).fetchone()
    assert r[0] == 12
    assert r[1] == 365          # 2025-08-01 .. 2026-07-31


def test_thang_chot_ky_la_thang_7(conn):
    r = conn.execute(
        """SELECT DISTINCT month FROM core.dim_date
           WHERE is_fy_end_month ORDER BY 1"""
    ).fetchall()
    assert r == [(7,)]


def test_quy_trong_ky(conn):
    """Quý 1 của kỳ = tháng 8,9,10 dương lịch."""
    rows = dict(
        conn.execute(
            """SELECT DISTINCT company_fy_quarter, array_agg(DISTINCT month ORDER BY month)
               FROM core.dim_date GROUP BY 1 ORDER BY 1"""
        ).fetchall()
    )
    assert rows[1] == [8, 9, 10]
    assert rows[2] == [1, 11, 12]
    assert rows[3] == [2, 3, 4]
    assert rows[4] == [5, 6, 7]


def test_khac_voi_nam_tai_chinh_nhat(conn):
    """Chứng minh hai lịch KHÁC nhau — nếu ai đó nhầm hai cột thì test này đỏ.

    Tháng 5/2026: năm tài chính Nhật là 2026, nhưng kỳ công ty là 2026 (1/8/25-31/7/26).
    Tháng 9/2025: năm tài chính Nhật là 2025, kỳ công ty là 2026. Khác nhau.
    """
    r = conn.execute(
        """SELECT fiscal_year, company_fy FROM core.dim_date WHERE date_key = '2025-09-15'"""
    ).fetchone()
    assert r == (2025, 2026)

    n = conn.execute(
        """SELECT count(*) FROM core.dim_date WHERE fiscal_year <> company_fy"""
    ).fetchone()[0]
    assert n > 0, "hai lịch phải khác nhau ở một số ngày"
