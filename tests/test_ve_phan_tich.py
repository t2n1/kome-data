"""Hình học SVG thuần Python cho các khối phân tích của đợt 5b — không cần
CSDL: mọi hàm ở kome/ve_phan_tich.py chỉ nhận dữ liệu đã có sẵn (dataclass
hoặc tuple đơn giản) và trả toạ độ để template vẽ.
"""
from kome.bao_cao import NganhKy, NganhThang, O, TapTrung, KhachTapTrung, ve_bieu_do
from kome.ve_phan_tich import (
    _squarify,
    bac_tang_truong,
    ve_cay_o,
    ve_dong_gop,
    ve_duong_nho,
    ve_nhiet,
    ve_pareto,
)


# ---- _squarify -----------------------------------------------------------

def test_squarify_tong_dien_tich_bang_khung():
    o = _squarify([50, 30, 20, 10, 5], 0, 0, 100, 40)
    tong = sum(w * h for _, _, w, h in o)
    assert abs(tong - 100 * 40) < 1e-6


def test_squarify_khong_o_nao_ra_ngoai_khung():
    o = _squarify([50, 30, 20, 10, 5, 3, 1], 10, 20, 200, 90)
    for x, y, w, h in o:
        assert x >= 10 - 1e-9
        assert y >= 20 - 1e-9
        assert x + w <= 210 + 1e-9
        assert y + h <= 110 + 1e-9


def test_squarify_dien_tich_ty_le_voi_gia_tri():
    gia_tri = [80, 40, 20, 10]
    o = _squarify(gia_tri, 0, 0, 120, 60)
    ti_le = [(w * h) / v for (_, _, w, h), v in zip(o, gia_tri)]
    for t in ti_le[1:]:
        assert abs(t - ti_le[0]) < 1e-6


def test_squarify_rong_khong_co_gi():
    assert _squarify([], 0, 0, 100, 50) == []


def test_squarify_mot_phan_tu_lap_day_toan_bo_khung():
    o = _squarify([42], 5, 5, 30, 20)
    assert o == [(5, 5, 30, 20)]


# ---- bac_tang_truong -------------------------------------------------------

def test_bac_tang_truong_none_la_khong():
    assert bac_tang_truong(None) == "khong"


def test_bac_tang_truong_bien_am():
    assert bac_tang_truong(-0.21) == "g2"
    assert bac_tang_truong(-0.20) == "g2"
    assert bac_tang_truong(-0.199) == "g1"
    assert bac_tang_truong(-0.05) == "g1"
    assert bac_tang_truong(-0.049) == "0"


def test_bac_tang_truong_bien_giua_va_duong():
    assert bac_tang_truong(0.0) == "0"
    assert bac_tang_truong(0.049) == "0"
    assert bac_tang_truong(0.05) == "t1"
    assert bac_tang_truong(0.199) == "t1"
    assert bac_tang_truong(0.20) == "t2"
    assert bac_tang_truong(0.21) == "t2"


# ---- ve_duong_nho ----------------------------------------------------------

def test_ve_duong_nho_cat_doan_tai_none():
    d = ve_duong_nho([1, None, 3, 4])
    assert d["co"] is True
    assert len(d["doan"]) == 2


def test_ve_duong_nho_toan_none():
    assert ve_duong_nho([None, None]) == {"co": False}


# ---- ve_bieu_do (thêm duong_ck) --------------------------------------------

def _o(thang, dt, dt_ck):
    return O(thang=thang, doanh_thu=dt, lai_gop=0, ty_suat=0.3, co_cung_ky=dt_ck is not None,
              tang_truong=None, la_thang_chot=False, so_phieu=1, so_khach=1, dt_cung_ky=dt_ck)


def test_ve_bieu_do_duong_ck_cat_doan_khi_thieu_cung_ky():
    thang = [_o("2026-01", 100, 90), _o("2026-02", 110, None), _o("2026-03", 120, 130)]
    bd = ve_bieu_do(thang)
    assert bd["co"] is True
    assert len(bd["duong_ck"]) == 2  # đứt tại tháng 2, không nối liền


def test_ve_bieu_do_dinh_tinh_tren_ca_hai_chuoi():
    """Cùng kỳ lớn hơn doanh thu ở một vài tháng: đỉnh trục phải bao trọn cả
    hai chuỗi, không để đường cùng kỳ vọt khỏi khung."""
    thang = [_o("2026-01", 100, 500), _o("2026-02", 110, 90)]
    bd = ve_bieu_do(thang)
    for pt in bd["duong_ck"]:
        for xy in pt.split(" "):
            _, y = xy.split(",")
            assert 16.0 - 1e-6 <= float(y) <= 260 - 34 + 1e-6


def test_ve_bieu_do_rong_khong_co_duong_ck():
    assert ve_bieu_do([]) == {"co": False}


# ---- ve_dong_gop -----------------------------------------------------------

def _nk(nganh, chenh_lech, tang_truong=None):
    return NganhKy(nganh=nganh, doanh_thu=1000, lai_gop=100, dt_doi_chieu=900,
                   dt_cung_ky=900, chenh_lech=chenh_lech, tang_truong=tang_truong)


def test_ve_dong_gop_thanh_am_nam_ben_trai_truc():
    dong = [_nk("Gạo", 500), _nk("Nước mắm", -300), _nk("Mì", None)]
    dg = ve_dong_gop(dong)
    assert dg["co"] is True
    ten_ve = {t["nganh"] for t in dg["thanh"]}
    assert "Mì" not in ten_ve  # chenh_lech=None không có thanh
    x0 = dg["x0"]
    for t in dg["thanh"]:
        if t["am"]:
            assert t["x"] < x0
            assert abs((t["x"] + t["w"]) - x0) < 1e-6
        else:
            assert t["x"] == x0


def test_ve_dong_gop_rong_khong_co_gi():
    assert ve_dong_gop([]) == {"co": False}


# ---- ve_cay_o ---------------------------------------------------------------

def test_ve_cay_o_bo_nganh_am_va_cong_don_khong_ve():
    nhom = [
        ("Gạo", 1000, 0.1, [("G1", "Gạo ST25", 600), ("G2", "Gạo Jasmine", 400)]),
        ("Chiết khấu", -50, None, []),
    ]
    cq = ve_cay_o(nhom)
    assert cq["co"] is True
    assert cq["khong_ve"] == -50
    ten_nganh = {n["nganh"] for n in cq["nganh"]}
    assert "Chiết khấu" not in ten_nganh


def test_ve_cay_o_bo_ma_am_trong_nganh_duong():
    nhom = [
        ("Gạo", 1000, 0.1, [("G1", "Gạo ST25", 900), ("G2", "Phí trả hàng", -100)]),
    ]
    cq = ve_cay_o(nhom)
    assert cq["khong_ve"] == -100
    assert cq["so_ma_khong_ve"] == 1
    ten_ma = {m["ten"] for m in cq["nganh"][0]["ma"]}
    assert "Phí trả hàng" not in ten_ma


def test_ve_cay_o_khac_xuat_hien_khi_qua_5_ma():
    mat_hang = [(f"M{i}", f"Mã {i}", 100 - i) for i in range(8)]  # 8 mã dương
    nhom = [("Gạo", sum(dt for _, _, dt in mat_hang), 0.0, mat_hang)]
    cq = ve_cay_o(nhom, toi_da_ma=5)
    ten_ma = [m["ten"] for m in cq["nganh"][0]["ma"]]
    assert "(khác)" in ten_ma
    assert len(ten_ma) == 6  # 5 mã lớn nhất + 1 ô khác


def test_ve_cay_o_tong_dien_tich_o_nganh_bang_khung():
    nhom = [
        ("Gạo", 1000, 0.1, [("G1", "Gạo", 1000)]),
        ("Nước mắm", 400, -0.3, [("N1", "Nước mắm", 400)]),
        ("Mì", 200, 0.0, [("M1", "Mì", 200)]),
    ]
    cq = ve_cay_o(nhom, rong=720, cao=360)
    tong = sum(n["w"] * n["h"] for n in cq["nganh"])
    assert abs(tong - 720 * 360) < 1.0


def test_ve_cay_o_rong_khi_khong_con_nganh_duong():
    cq = ve_cay_o([("Chiết khấu", -50, None, [])])
    assert cq["co"] is False
    assert cq["khong_ve"] == -50


# ---- ve_nhiet ---------------------------------------------------------------

def _nt(thang, nganh, dt, dt_ck, tang_truong):
    return NganhThang(thang=thang, nganh=nganh, doanh_thu=dt, dt_cung_ky=dt_ck,
                       co_cung_ky=dt_ck is not None, tang_truong=tang_truong)


def test_ve_nhiet_du_12_cot_ke_ca_thang_khong_co_dong():
    thang_ky = [f"2025-{t:02d}" for t in range(8, 13)] + [f"2026-{t:02d}" for t in range(1, 8)]
    dong = [_nt("2026-01", "Gạo", 1000, 900, 0.11)]
    nh = ve_nhiet(dong, thang_ky)
    assert nh["co"] is True
    o_gao = [o for o in nh["o"] if o["nganh"] == "Gạo"]
    assert len(o_gao) == 12
    thieu = next(o for o in o_gao if o["thang"] == "2025-08")
    assert thieu["bac"] == "khong_ck"
    assert thieu["co_cung_ky"] is False


def test_ve_nhiet_o_khong_co_cung_ky_la_khong_ck():
    thang_ky = ["2026-01", "2026-02"]
    dong = [_nt("2026-01", "Gạo", 1000, None, None)]
    nh = ve_nhiet(dong, thang_ky)
    o = next(o for o in nh["o"] if o["thang"] == "2026-01" and o["nganh"] == "Gạo")
    assert o["bac"] == "khong_ck"


def test_ve_nhiet_cung_ky_bang_khong_la_khong():
    thang_ky = ["2026-01"]
    dong = [NganhThang(thang="2026-01", nganh="Gạo", doanh_thu=1000, dt_cung_ky=0,
                        co_cung_ky=True, tang_truong=None)]
    nh = ve_nhiet(dong, thang_ky)
    o = nh["o"][0]
    assert o["bac"] == "khong"


# ---- ve_pareto ---------------------------------------------------------------

def _kt(ma, dt, hang, luy_ke):
    return KhachTapTrung(ma=ma, ten=ma, doanh_thu=dt, thu_hang=hang, ty_trong=None, luy_ke=luy_ke)


def test_ve_pareto_luy_ke_qua_100_ke_o_mep_tren():
    tt = TapTrung(dong=[_kt("K1", -500, 1, 1.4), _kt("K2", 2000, 2, 0.9)],
                  so_khach=2, luy_ke_top10=None)
    pr = ve_pareto(tt)
    assert pr["co"] is True
    # điểm đầu tiên (luỹ kế 1.4, bị kẹp về 1.0) phải nằm ở mép trên của khung vẽ
    x0, y0 = pr["duong"].split(" ")[0].split(",")
    assert abs(float(y0) - 16.0) < 1e-6  # LE_TREN


def test_ve_pareto_rong_khong_co_khach():
    assert ve_pareto(TapTrung(dong=[], so_khach=0, luy_ke_top10=None)) == {"co": False}
