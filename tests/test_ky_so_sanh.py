"""Kỳ so sánh tự chọn (đặc tả 2026-09-25-ky-so-sanh-tu-chon-design.md §3).

Có `ss_*` thì cả website so với ĐÚNG kỳ đó — `so_sanh` còn một phần tử. Mỗi test
canh một cách cắt sai mà nếu lọt thì màn vẫn vẽ bình thường, chỉ so nhầm dải.
"""
from datetime import date

import pytest

from kome import khoang_xem as KX

PV = KX.PhamVi(ngay_dau=date(2023, 9, 4), hom_nay=date(2026, 9, 25), ky=(
    KX.KyDl(2024, 5, date(2023, 9, 4), date(2024, 7, 31)),
    KX.KyDl(2025, 6, date(2024, 8, 1), date(2025, 7, 31)),
    KX.KyDl(2026, 7, date(2025, 8, 1), date(2026, 7, 31)),
    KX.KyDl(2027, 8, date(2026, 8, 1), date(2026, 9, 25))))


def g(**kw):
    return KX.giai(PV, KX.doc_tham_so(**kw))


def test_khong_ss_thi_y_nhu_cu():
    k = g(thang="2026-03")
    assert not k.tu_chon and [s.ma for s in k.so_sanh] == ["nam_truoc", "thang_truoc"]


def test_ss_thay_ca_hai_phep_so_mac_dinh():
    k = g(thang="2026-06", ss_thang="2026-03")
    assert k.tu_chon and len(k.so_sanh) == 1
    s = k.so_sanh[0]
    assert (s.ma, s.tu, s.den, s.tu_nay, s.den_nay, s.co) == \
        ("tu_chon", date(2026, 3, 1), date(2026, 3, 31), date(2026, 6, 1), date(2026, 6, 30), True)
    assert s.nhan == "tháng 3/2026"


def test_thang_do_dang_cat_thang_so_theo_cung_dai_ngay():
    k = g(ss_thang="2026-03")                  # mặc định = 1 → 25/9/2026
    s = k.so_sanh[0]
    assert (s.tu, s.den) == (date(2026, 3, 1), date(2026, 3, 25))
    assert (s.tu_nay, s.den_nay) == (date(2026, 9, 1), date(2026, 9, 25))


def test_thang_do_dang_ngay_31_kep_ve_cuoi_thang_so():
    pv = KX.PhamVi(PV.ngay_dau, date(2026, 7, 30), PV.ky)      # 1 → 30/7 dở dang
    s = KX.giai(pv, KX.doc_tham_so(ss_thang="2026-02")).so_sanh[0]
    assert (s.tu, s.den) == (date(2026, 2, 1), date(2026, 2, 28))


def test_ky_do_dang_so_cung_vi_tri_trong_ky():
    s = g(ky="2027", ss_ky="2025").so_sanh[0]   # kỳ 8: 1/8 → 25/9/2026
    assert (s.tu, s.den, s.tu_nay, s.den_nay) == \
        (date(2024, 8, 1), date(2024, 9, 25), date(2026, 8, 1), date(2026, 9, 25))
    assert s.nhan.startswith("kỳ 6")


def test_ky_so_bat_dau_giua_chung_thi_cat_phia_dang_xem():
    # Kỳ 5 có dữ liệu từ 4/9/2023 → so từ THÁNG 9 cả hai phía (cùng luật dạng
    # Kỳ mặc định / `mart.ky_cung_ky`: đối chiếu theo tháng có dữ liệu).
    s = g(ky="2026", ss_ky="2024").so_sanh[0]
    assert (s.tu, s.den) == (date(2023, 9, 1), date(2024, 7, 31))
    assert (s.tu_nay, s.den_nay) == (date(2025, 9, 1), date(2026, 7, 31))


def test_to_hop_khac_so_nguyen_van_va_noi_so_ngay():
    k = g(ss_ky="2026")                          # 25 ngày với cả kỳ 7
    s = k.so_sanh[0]
    assert (s.tu, s.den, s.tu_nay, s.den_nay) == \
        (date(2025, 8, 1), date(2026, 7, 31), date(2026, 9, 1), date(2026, 9, 25))
    assert "25 ngày với 365 ngày" in k.mo_ta


def test_khoang_ngay_so_nguyen_van():
    s = g(tu="2026-09-01", den="2026-09-20", ss_tu="2026-05-01", ss_den="2026-05-20").so_sanh[0]
    assert (s.tu, s.den) == (date(2026, 5, 1), date(2026, 5, 20))


def test_ky_so_sau_ngay_cuoi_khoang_xem_bi_chan():
    with pytest.raises(KX.LoiKhoang, match="trước ngày cuối"):
        g(thang="2026-03", ss_thang="2026-06")
    with pytest.raises(KX.LoiKhoang):
        g(thang="2026-03", ss_tu="2026-03-20", ss_den="2026-04-02")
    # Chồng lấn nhưng kết thúc ≤ ngày cuối: được.
    g(thang="2026-03", ss_tu="2026-02-20", ss_den="2026-03-10")


def test_ky_so_truoc_du_lieu_thi_khong_co():
    k = g(ss_thang="2023-05")
    assert k.so_sanh[0].co is False and "không có dữ liệu để so" in k.mo_ta


def test_ss_bang_thang_truoc_trung_dai_mac_dinh():
    for kw in ({}, {"thang": "2026-06"}):
        mac_dinh = g(**kw).so_sanh[1]
        s = g(**kw, ss_thang=f"{mac_dinh.tu:%Y-%m}").so_sanh[0]
        assert (s.tu, s.den, s.tu_nay, s.den_nay) == \
            (mac_dinh.tu, mac_dinh.den, mac_dinh.tu_nay, mac_dinh.den_nay)


@pytest.mark.parametrize("kw", [
    {"ss_thang": "2026-3"}, {"ss_ky": "abc"}, {"ss_tu": "2026-01-01"},
    {"ss_thang": "2026-03", "ss_ky": "2026"}, {"ss_tu": "2026-02-01", "ss_den": "2026-01-01"}])
def test_cu_phap_ss_sai_bi_tu_choi(kw):
    with pytest.raises(KX.LoiKhoang, match="Kỳ so sánh"):
        KX.doc_tham_so(**kw)


def test_khoa_mang_ss_moc_khong_doi():
    ts = KX.doc_tham_so(thang="2026-06", ss_ky=" 2025 ")
    assert ts.khoa() == {"thang": "2026-06", "ss_ky": "2025"}
    assert ts.moc() == date(2026, 6, 30)
    assert ts.chinh().khoa() == {"thang": "2026-06"}
    assert KX.doc_tham_so(ss_tu="2026-1-2", ss_den="2026-01-05").khoa() == \
        {"ss_tu": "2026-01-02", "ss_den": "2026-01-05"}


# ---- Có CSDL: số theo kỳ so sánh, /bao-cao dạng Kỳ, API ---------------------

from kome import ban_khoang as BK  # noqa: E402
from tests.test_ban_khoang import _gieo, _kx  # noqa: E402


def test_so_voi_ky_tu_chon_BANG_so_mac_dinh_cung_dai(conn, batch):
    """ss_thang = cùng tháng năm trước ⇒ đúng số của phép so năm trước mặc định."""
    _gieo(conn, batch)
    nt = BK.tinh_bao_cao(conn, _kx(conn)).so_sanh[0]
    s, = BK.tinh_bao_cao(conn, _kx(conn, ss_thang="2025-07")).so_sanh
    assert (s.ma, s.tu, s.den) == ("tu_chon", nt.tu, nt.den)
    assert (s.dt, s.dt_ck, s.lg_ck) == (nt.dt, nt.dt_ck, nt.lg_ck)


def test_bao_cao_ky_co_ss_di_nhanh_khoang_khong_qua_11_truy_van(conn, batch, monkeypatch):
    from kome.web.api import du_lieu_bao_cao
    _gieo(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    d = du_lieu_bao_cao(conn, KX.doc_tham_so(ky="2026", ss_ky="2025"))
    assert dem["n"] <= 11, dem["n"]
    assert d["khoang"]["tu_chon"] is True and d["bc"]["cung_ky"] is None
    assert [s["ma"] for s in d["bc"]["so_sanh"]] == ["tu_chon"]


def test_api_nhan_ss_va_bao_loi_400(conn, batch, test_db_url):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    _gieo(conn, batch)
    conn.commit()
    c = TestClient(create_app(db_url=test_db_url))
    r = c.get("/api/bao-cao?thang=2026-07&ss_thang=2026-06")
    assert r.status_code == 200, r.text
    assert [s["ma"] for s in r.json()["khoang"]["so_sanh"]] == ["tu_chon"]
    r = c.get("/api/tong-quan/kpi?ss_thang=2026-06")
    assert r.status_code == 200, r.text
    assert [s["ma"] for s in r.json()["doanh_thu"]["so_sanh"]] == ["tu_chon"]
    assert c.get("/api/bao-cao?thang=2026-06&ss_thang=2026-07").status_code == 400
    assert c.get("/api/bao-cao?ss_thang=2026-6").status_code == 400
