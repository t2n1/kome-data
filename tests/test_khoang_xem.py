"""Khoảng xem (đặc tả 2026-09-24-khoang-xem-thang-design.md §1).

`kome.khoang_xem` là chỗ DUY NHẤT hiểu khoảng xem. Mỗi test canh một cách hiểu
sai mà nếu lọt thì màn vẫn vẽ ra bình thường, chỉ là so nhầm dải ngày.
"""
from datetime import date

import pytest

from kome import khoang_xem as KX

PV = KX.PhamVi(ngay_dau=date(2025, 3, 3), hom_nay=date(2026, 7, 24), ky=(
    KX.KyDl(2025, 6, date(2025, 3, 3), date(2025, 7, 31)),
    KX.KyDl(2026, 7, date(2025, 8, 1), date(2026, 7, 24))))


def test_mac_dinh_la_thang_cua_hom_nay_mung_1_den_hom_nay():
    k = KX.giai(PV, KX.doc_tham_so())
    assert (k.loai, k.tu, k.den, k.thang, k.mac_dinh, k.tron_thang) == \
        ("thang", date(2026, 7, 1), date(2026, 7, 24), "2026-07", True, False)
    nt, tt = k.so_sanh
    assert (nt.ma, nt.tu, nt.den, nt.co) == ("nam_truoc", date(2025, 7, 1), date(2025, 7, 24), True)
    assert (tt.ma, tt.tu, tt.den, tt.co) == ("thang_truoc", date(2026, 6, 1), date(2026, 6, 24), True)
    assert k.company_fy == 2026 and k.so_ky == 7


def test_thang_tron_so_tron_thang():
    k = KX.giai(PV, KX.doc_tham_so(thang="2026-03"))
    assert (k.tu, k.den, k.tron_thang, k.mac_dinh) == (date(2026, 3, 1), date(2026, 3, 31), True, False)
    assert (k.so_sanh[0].tu, k.so_sanh[0].den) == (date(2025, 3, 1), date(2025, 3, 31))
    assert (k.so_sanh[1].tu, k.so_sanh[1].den) == (date(2026, 2, 1), date(2026, 2, 28))


def test_thang_do_dang_ngay_cuoi_kep_ve_cuoi_thang_truoc():
    pv = KX.PhamVi(date(2025, 3, 3), date(2026, 3, 31), PV.ky)
    k = KX.giai(pv, KX.doc_tham_so())
    assert k.tron_thang and k.so_sanh[1].den == date(2026, 2, 28)
    pv = KX.PhamVi(date(2025, 3, 3), date(2026, 3, 30), PV.ky)
    k = KX.giai(pv, KX.doc_tham_so())
    assert not k.tron_thang and k.so_sanh[1].den == date(2026, 2, 28)


def test_29_2_tru_mot_nam_kep_ve_28_2():
    pv = KX.PhamVi(date(2027, 1, 5), date(2028, 2, 29), ())
    assert KX.giai(pv, KX.doc_tham_so()).so_sanh[0].den == date(2027, 2, 28)
    pv = KX.PhamVi(date(2027, 1, 5), date(2028, 3, 15), ())
    k = KX.giai(pv, KX.doc_tham_so(thang="2028-02"))
    assert (k.den, k.so_sanh[0].den) == (date(2028, 2, 29), date(2027, 2, 28))


def test_so_vao_truoc_du_lieu_thi_khong_co():
    k = KX.giai(PV, KX.doc_tham_so(thang="2025-05"))
    assert k.so_sanh[0].co is False and k.so_sanh[1].co is True
    k = KX.giai(PV, KX.doc_tham_so(thang="2025-03"))
    assert k.so_sanh[1].co is False
    assert any("bắt đầu" in g for g in k.ghi_chu), "tháng đầu kho phải nói là chưa đủ tháng"


def test_thang_ngoai_dai_bi_tu_choi():
    with pytest.raises(KX.LoiKhoang):
        KX.giai(PV, KX.doc_tham_so(thang="2026-08"))
    with pytest.raises(KX.LoiKhoang):
        KX.giai(PV, KX.doc_tham_so(thang="2025-02"))


def test_ky_so_tren_thang_doi_chieu_nhu_ky_cung_ky():
    k = KX.giai(PV, KX.doc_tham_so(ky="2026"))
    assert (k.loai, k.tu, k.den, k.so_ky, k.company_fy) == ("ky", date(2025, 8, 1), date(2026, 7, 24), 7, 2026)
    (s,) = k.so_sanh
    assert (s.tu_nay, s.den_nay, s.tu, s.den, s.co) == \
        (date(2026, 3, 1), date(2026, 7, 24), date(2025, 3, 1), date(2025, 7, 24), True)


def test_ky_dau_khong_co_gi_de_so():
    (s,) = KX.giai(PV, KX.doc_tham_so(ky="2025")).so_sanh
    assert s.co is False


def test_ky_khong_co_trong_kho_bi_tu_choi():
    with pytest.raises(KX.LoiKhoang):
        KX.giai(PV, KX.doc_tham_so(ky="2024"))


def test_khoang_cat_vao_dai_du_lieu_va_so_lien_truoc():
    k = KX.giai(PV, KX.doc_tham_so(tu="2026-06-01", den="2026-12-31"))
    assert (k.loai, k.tu, k.den) == ("khoang", date(2026, 6, 1), date(2026, 7, 24))
    nt, lt = k.so_sanh
    assert (nt.ma, nt.tu, nt.den) == ("nam_truoc", date(2025, 6, 1), date(2025, 7, 24))
    assert (lt.ma, lt.tu, lt.den) == ("lien_truoc", date(2026, 4, 8), date(2026, 5, 31))
    assert (lt.den - lt.tu).days == (k.den - k.tu).days


def test_khoang_rong_sau_khi_cat_bi_tu_choi():
    with pytest.raises(KX.LoiKhoang):
        KX.giai(PV, KX.doc_tham_so(tu="2027-01-01", den="2027-02-01"))


@pytest.mark.parametrize("ts", [
    dict(thang="2026-13"), dict(thang="x"), dict(ky="abc"), dict(tu="2026-01-01"),
    dict(tu="2026-02-01", den="2026-01-01"), dict(thang="2026-07", ky="2026"),
    dict(tu="2026-01-01", den="2026-01-40")])
def test_tham_so_sai_bi_tu_choi(ts):
    with pytest.raises(KX.LoiKhoang):
        KX.doc_tham_so(**ts)


def test_khoa_chuan_hoa():
    assert KX.doc_tham_so().khoa() == {}
    assert KX.doc_tham_so(thang="2026-07").khoa() == {"thang": "2026-07"}
    assert KX.doc_tham_so(ky=" 2026 ").khoa() == {"ky": "2026"}
    assert KX.doc_tham_so(tu="2026-7-1", den="2026-07-05").khoa() == \
        {"tu": "2026-07-01", "den": "2026-07-05"}


def test_mo_ta_noi_ro_so_voi_gi():
    k = KX.giai(PV, KX.doc_tham_so())
    assert k.nhan == "Tháng 7/2026"
    assert "1/7 → 24/7/2026" in k.mo_ta
    assert "1/7 → 24/7/2025" in k.mo_ta and "1/6 → 24/6/2026" in k.mo_ta
    k = KX.giai(PV, KX.doc_tham_so(thang="2025-05"))
    assert "không có dữ liệu" in k.mo_ta


def test_pham_vi_tu_csdl(conn, batch):
    from tests.test_phan_tich_mart import _ban
    assert KX.pham_vi(conn) is None
    _ban(conn, batch, date(2025, 7, 30), "AA01")
    _ban(conn, batch, date(2025, 8, 2), "AA01")
    pv = KX.pham_vi(conn)
    assert (pv.ngay_dau, pv.hom_nay) == (date(2025, 7, 30), date(2025, 8, 2))
    assert [(k.company_fy, k.so_ky, k.tu, k.den) for k in pv.ky] == [
        (2025, 6, date(2025, 7, 30), date(2025, 7, 31)),
        (2026, 7, date(2025, 8, 1), date(2025, 8, 2))]
