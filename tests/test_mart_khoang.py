"""Migration 039 — hàm chỉ số theo khoảng ngày của `mart`.

Đổi cách tính sang hàm theo khoảng KHÔNG được làm đổi một con số nào đang hiện:
mỗi test dưới là một đẳng thức giữa hàm mới và view cũ (đặc tả khoảng xem §2).
"""
from datetime import date

from tests.test_phan_tich_mart import _ban, _nganh


def _gieo(conn, batch):
    _nganh(conn, batch, "AA01", "Ngành A")
    _ban(conn, batch, date(2025, 7, 3), "AA01", amount=55_000, tax=5_000, gp=10_000)
    _ban(conn, batch, date(2026, 6, 10), "AA01", amount=66_000, tax=6_000, gp=12_000)
    _ban(conn, batch, date(2026, 7, 2), "AA01", amount=110_000, tax=10_000, gp=30_000)
    _ban(conn, batch, date(2026, 7, 9), "", amount=22_000, tax=2_000, gp=3_000, khach="000000009293")
    # Phiếu đỏ (hàng trả lại): số ÂM, không được lọc.
    _ban(conn, batch, date(2026, 7, 15), "AA01", amount=-11_000, tax=-1_000, gp=-2_000,
         khach="000000009294", sale="0102")


def test_tong_thang_tron_BANG_ban_theo_thang(conn, batch):
    _gieo(conn, batch)
    t = conn.execute("SELECT dt, lg, so_phieu, so_khach FROM mart.tong_khoang('2026-07-01', '2026-07-31')").fetchone()
    v = conn.execute("""SELECT doanh_thu_thuan, lai_gop, so_phieu, so_khach
                          FROM mart.ban_theo_thang WHERE thang = '2026-07'""").fetchone()
    assert t == v
    assert t[0] == 100_000 + 20_000 - 10_000, "phiếu đỏ phải trừ vào doanh thu, không bị lọc"


def test_thang_hien_tai_BANG_thang_den_hom_nay(conn, batch):
    """Ô doanh thu của Tổng quan chuyển từ mart.thang_den_hom_nay sang
    khoang_xem + tong_khoang: dải ngày và số phải y hệt."""
    from kome import khoang_xem as KX
    _gieo(conn, batch)
    kx = KX.giai_conn(conn, KX.doc_tham_so())
    v = conn.execute("""SELECT tu_ngay, den_ngay, tu_ngay_ck, den_ngay_ck, dt, lg, so_khach,
                               co_cung_ky, dt_ck, lg_ck, so_khach_ck FROM mart.thang_den_hom_nay""").fetchone()
    nt = kx.so_sanh[0]
    assert (kx.tu, kx.den, nt.tu, nt.den) == v[:4]
    t = conn.execute("SELECT dt, lg, so_khach FROM mart.tong_khoang(%s, %s)", (kx.tu, kx.den)).fetchone()
    assert t == v[4:7]
    assert nt.co == v[7]
    ck = conn.execute("SELECT coalesce(dt, 0), coalesce(lg, 0), so_khach FROM mart.tong_khoang(%s, %s)",
                      (nt.tu, nt.den)).fetchone()
    assert ck == v[8:11]


def test_tong_ngay_va_tong_nganh_BANG_tong_khoang(conn, batch):
    _gieo(conn, batch)
    tu, den = date(2026, 6, 1), date(2026, 7, 31)
    t = conn.execute("SELECT dt, lg FROM mart.tong_khoang(%s, %s)", (tu, den)).fetchone()
    assert conn.execute("SELECT sum(dt), sum(lg) FROM mart.ngay_khoang(%s, %s)", (tu, den)).fetchone() == t
    assert conn.execute("SELECT sum(dt), sum(lg) FROM mart.nganh_khoang(%s, %s)", (tu, den)).fetchone() == t
    assert conn.execute("SELECT sum(dt), sum(lg) FROM mart.thang_khoang(%s, %s)", (tu, den)).fetchone() == t
    assert conn.execute("SELECT sum(dt), sum(lg) FROM mart.sale_khoang(%s, %s)", (tu, den)).fetchone() == t
    assert conn.execute("SELECT sum(dt), sum(lg) FROM mart.khach_khoang(%s, %s)", (tu, den)).fetchone() == t
    assert conn.execute("SELECT sum(dt), sum(lg) FROM mart.mat_hang_khoang(%s, %s)", (tu, den)).fetchone() == t


def test_ngay_khong_ban_co_dong_0(conn, batch):
    _gieo(conn, batch)
    rows = conn.execute("SELECT ngay, dt FROM mart.ngay_khoang('2026-07-01', '2026-07-05')").fetchall()
    assert [r[0].day for r in rows] == [1, 2, 3, 4, 5]
    assert rows[0][1] == 0 and rows[1][1] == 100_000


def test_thang_khoang_cat_theo_dai(conn, batch):
    _gieo(conn, batch)
    rows = conn.execute("SELECT thang, tu_ngay, den_ngay FROM mart.thang_khoang('2026-06-15', '2026-07-10')").fetchall()
    assert rows == [("2026-06", date(2026, 6, 15), date(2026, 6, 30)),
                    ("2026-07", date(2026, 7, 1), date(2026, 7, 10))]


def test_ten_nganh_khop_NGANH_TRONG_va_view(conn, batch):
    from kome.bao_cao import NGANH_PHI, NGANH_TRONG
    _gieo(conn, batch)
    assert conn.execute("SELECT mart.ten_nganh(''), mart.ten_nganh(NULL), mart.ten_nganh('X')").fetchone() \
        == (NGANH_TRONG, NGANH_TRONG, "X")
    v = {r[0] for r in conn.execute("SELECT nganh FROM mart.ban_theo_nganh_thang").fetchall()}
    h = {r[0] for r in conn.execute("SELECT nganh FROM mart.nganh_khoang('2025-01-01', '2026-12-31')").fetchall()}
    # 048: dòng không mã hàng (端数) là phí & điều chỉnh, không còn "(chưa phân loại)".
    assert v == h == {"Ngành A", NGANH_PHI}


def test_nganh_so_sanh_giu_nganh_chi_ban_ky_so_sanh(conn, batch):
    """FULL JOIN: ngành bán năm trước mà nay không bán vẫn phải CÓ dòng."""
    _nganh(conn, batch, "BB01", "Ngành B")
    _gieo(conn, batch)
    _ban(conn, batch, date(2025, 7, 4), "BB01", amount=44_000, tax=4_000, gp=8_000, khach="000000009295")
    rows = {r[0]: r[1:] for r in conn.execute(
        """SELECT nganh, dt, dt_doi_chieu, dt_cung_ky, chenh_lech, tang_truong
             FROM mart.nganh_so_sanh_khoang('2026-07-01', '2026-07-31', '2026-07-01', '2026-07-31',
                                            '2025-07-01', '2025-07-31')""").fetchall()}
    assert rows["Ngành B"][:4] == (0, 0, 40_000, -40_000)
    assert rows["Ngành A"][2] == 50_000
    assert float(rows["Ngành A"][4]) == (100_000 - 10_000) / 50_000 - 1
    khong = conn.execute(
        """SELECT count(*), count(dt_cung_ky) FROM mart.nganh_so_sanh_khoang(
             '2026-07-01', '2026-07-31', '2026-07-01', '2026-07-31', NULL, NULL)""").fetchone()
    assert khong == (2, 0), "không có phép so: không đẻ dòng, cột so sánh NULL"


def test_tap_trung_khoang_luy_ke_toi_1(conn, batch):
    _gieo(conn, batch)
    rows = conn.execute("""SELECT customer_code, thu_hang, luy_ke
                             FROM mart.tap_trung_khoang('2026-07-01', '2026-07-31') ORDER BY thu_hang""").fetchall()
    assert [r[1] for r in rows] == [1, 2, 3]
    assert float(rows[-1][2]) == 1.0
