"""Báo cáo theo khoảng xem (kome/ban_khoang.py).

Dạng Kỳ phải ra ĐÚNG số như màn Báo cáo trước đợt này; dạng Tháng phải khớp
view tháng cũ; các phép so phải so đúng dải ngày.
"""
from dataclasses import asdict
from datetime import date

from kome import ban_khoang as BK
from kome import bao_cao as BC
from kome import khoang_xem as KX
from tests.test_phan_tich_mart import _ban, _nganh


def _gieo(conn, batch):
    _nganh(conn, batch, "AA01", "Ngành A")
    _nganh(conn, batch, "BB01", "Ngành B")
    _ban(conn, batch, date(2025, 7, 3), "AA01", amount=55_000, tax=5_000, gp=10_000)
    _ban(conn, batch, date(2025, 7, 4), "BB01", amount=44_000, tax=4_000, gp=8_000, khach="000000009295")
    _ban(conn, batch, date(2026, 6, 10), "AA01", amount=66_000, tax=6_000, gp=12_000)
    _ban(conn, batch, date(2026, 7, 2), "AA01", amount=110_000, tax=10_000, gp=30_000)
    _ban(conn, batch, date(2026, 7, 9), "BB01", amount=22_000, tax=2_000, gp=3_000, khach="000000009293")
    _ban(conn, batch, date(2026, 7, 15), "AA01", amount=-11_000, tax=-1_000, gp=-2_000,
         khach="000000009294", sale="0102")


def _kx(conn, **ts):
    return KX.giai_conn(conn, KX.doc_tham_so(**ts))


def test_bao_cao_ky_GIU_NGUYEN_so(conn, batch):
    _gieo(conn, batch)
    a = BK.tinh_bao_cao(conn, _kx(conn, ky="2026"))
    b = BC.tinh_bao_cao(conn, 2026)
    assert asdict(a) == asdict(b)


def test_bao_cao_thang_tong_BANG_ban_theo_thang(conn, batch):
    _gieo(conn, batch)
    bc = BK.tinh_bao_cao(conn, _kx(conn, thang="2026-07"))
    v = conn.execute("""SELECT doanh_thu_thuan, lai_gop, so_khach, so_phieu
                          FROM mart.ban_theo_thang WHERE thang = '2026-07'""").fetchone()
    assert (bc.ky.doanh_thu, bc.ky.lai_gop, bc.ky.so_khach, bc.ky.so_phieu) == v
    assert bc.ky.nhan == "Tháng 7/2026" and bc.moi_ky == [] and bc.cung_ky is None
    assert sum(o.doanh_thu for o in bc.thang) == bc.ky.doanh_thu
    assert sum(n["doanh_thu"] for n in bc.nhan_vien) == bc.ky.doanh_thu
    assert sum(h["doanh_thu"] for h in bc.hang_theo_nganh) == bc.ky.doanh_thu
    assert {n.nganh for n in bc.nganh_ky} == {"Ngành A", "Ngành B"}


def test_so_sanh_nam_truoc_va_thang_truoc(conn, batch):
    _gieo(conn, batch)
    bc = BK.tinh_bao_cao(conn, _kx(conn))          # tháng hiện tại = 7/2026, tới 15/7
    nt, tt = bc.so_sanh
    assert (nt.ma, nt.tu, nt.den, nt.co) == ("nam_truoc", date(2025, 7, 1), date(2025, 7, 15), True)
    assert (nt.dt, nt.dt_ck) == (110_000, 90_000)
    assert abs(nt.tang_dt - (110_000 / 90_000 - 1)) < 1e-9
    assert (tt.ma, tt.tu, tt.den, tt.dt_ck) == ("thang_truoc", date(2026, 6, 1), date(2026, 6, 15), 60_000)
    b = next(n for n in bc.nganh_ky if n.nganh == "Ngành B")
    assert (b.dt_cung_ky, b.dt_doi_chieu) == (40_000, 20_000)


def test_so_sanh_khong_co_du_lieu_thi_ck_la_None(conn, batch):
    _gieo(conn, batch)
    bc = BK.tinh_bao_cao(conn, _kx(conn, thang="2025-07"))
    nt = bc.so_sanh[0]
    assert nt.co is False and nt.dt_ck is None and nt.tang_dt is None
    assert all(o.dt_cung_ky is None for o in bc.thang)
    assert all(n.dt_cung_ky is None for n in bc.nganh_ky)


def test_chuoi_ngay_khi_ngan_thang_khi_dai(conn, batch):
    _gieo(conn, batch)
    kieu, o = BK.chuoi(conn, _kx(conn, thang="2026-07"))
    assert kieu == "ngay" and len(o) == 15 and o[1].thang == "2026-07-02"
    assert o[2].dt_cung_ky == 50_000 and o[3].dt_cung_ky == 40_000
    assert not any(x.la_thang_chot for x in o), "ngày 7 của tháng không phải 'tháng chốt kỳ'"
    kieu, o = BK.chuoi(conn, _kx(conn, tu="2025-07-01", den="2026-07-15"))
    assert kieu == "thang" and o[0].thang == "2025-07" and o[-1].thang == "2026-07"
    assert o[0].la_thang_chot and sum(x.doanh_thu for x in o) == \
        conn.execute("SELECT dt FROM mart.tong_khoang('2025-07-01', '2026-07-15')").fetchone()[0]


def test_tien_do_ngan_sach_theo_thang_chon(conn, batch):
    _gieo(conn, batch)
    assert BC.tien_do_ngan_sach(conn, 2026, "2026-06").thang == "2026-06"
    assert BC.tien_do_ngan_sach(conn, 2026).thang == "2026-07"


def test_bao_cao_thang_khong_qua_11_truy_van(conn, batch, monkeypatch):
    from kome.web.api import du_lieu_bao_cao
    _gieo(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    for ts in ({}, {"thang": "2026-06"}, {"ky": "2026"}, {"tu": "2025-07-01", "den": "2026-07-15"}):
        dem["n"] = 0
        d = du_lieu_bao_cao(conn, KX.doc_tham_so(**ts))
        assert d["khoang"] is not None
        assert dem["n"] <= 11, f"{ts}: {dem['n']} truy vấn"
