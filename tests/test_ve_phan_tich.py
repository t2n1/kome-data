"""Hình học SVG thuần Python cho các khối phân tích của đợt 5b — không cần
CSDL: mọi hàm ở kome/ve_phan_tich.py chỉ nhận dữ liệu đã có sẵn (dataclass
hoặc tuple đơn giản) và trả toạ độ để template vẽ.
"""
from datetime import date, timedelta

import pytest

from kome.bao_cao import NganhKy, NganhThang, O, TapTrung, KhachTapTrung, ve_bieu_do
from kome.ve_phan_tich import (
    _squarify,
    bac_tang_truong,
    ve_cay_o,
    ve_dong_gop,
    ve_duong_nho,
    ve_nhiet,
    ve_pareto,
    ve_xu_huong,
)


def _ngay(n: int, gia_tri=None):
    """`n` ngày liên tục, giá trị mặc định tăng dần 1,2,3... (đủ để phân
    biệt cột với đường trong test), CŨ -> MỚI."""
    d0 = date(2026, 1, 1)
    if gia_tri is None:
        gia_tri = list(range(1, n + 1))
    return [(d0 + timedelta(days=i), gia_tri[i]) for i in range(n)]


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


def test_squarify_gia_tri_0_nem_assert_khong_zerodivisionerror():
    """[Vòng soát 1, minor 2] Một giá trị 0 lẫn trong hàng có phần tử khác 0
    chia cho 0 ở công thức worst-ratio — assert phải chặn TRƯỚC khi rơi vào
    đó, không để lộ ZeroDivisionError khó dò."""
    import pytest
    with pytest.raises(AssertionError):
        _squarify([50, 0, 20], 0, 0, 100, 40)


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


def test_ve_duong_nho_diem_don_cho_diem_dung_le():
    """[Vòng soát 1, minor 4] Một điểm đứng lẻ giữa hai None vẫn phải có mặt
    trong diem_don để template vẽ chấm — không thì tháng đó biến mất khỏi
    biểu đồ."""
    d = ve_duong_nho([1, None, 5, None, 3])
    assert len(d["doan"]) == 3          # ba đoạn: [1], [5], [3] — đều lẻ
    assert len(d["diem_don"]) == 3
    xs = [x for x, _ in d["diem_don"]]
    assert xs == sorted(xs)             # đúng thứ tự thời gian


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


# ---- Đối soát tổng (soát vòng 1) --------------------------------------------
# `dt_nganh` PHẢI bằng đúng tổng các mã (dương + âm) của chính ngành đó để
# bất biến đối soát có ý nghĩa — đây là giả định của MART (hai tầng dữ liệu
# nhất quán), không phải một ràng buộc riêng của lớp vẽ.

def _tong_dau_vao(nhom):
    return sum(dt_nganh for _, dt_nganh, _, _ in nhom)


def _tong_ve(cq):
    return sum(n["doanh_thu_ve"] for n in cq["nganh"])


def test_doi_soat_a_nganh_duong_co_mot_ma_am():
    # dt_nganh = 1000 + (-100) = 900, đúng tổng hai mã.
    nhom = [("Gạo", 900, 0.1, [("G1", "Gạo ST25", 1000), ("G2", "Phí trả hàng", -100)])]
    cq = ve_cay_o(nhom)
    assert cq["nganh"][0]["doanh_thu"] == 900         # net, để hiện <title>
    assert cq["nganh"][0]["doanh_thu_ve"] == 1000      # diện tích thực vẽ
    assert cq["khong_ve"] == -100
    assert _tong_ve(cq) + cq["khong_ve"] == _tong_dau_vao(nhom)
    # không mã nào mất: mã dương duy nhất phải được vẽ riêng (không có "khác"
    # vì chỉ một mã dương, con_lai = 0).
    ten_ma = [m["ten"] for m in cq["nganh"][0]["ma"]]
    assert ten_ma == ["Gạo ST25"]


def test_doi_soat_b_hon_5_ma_duong_cong_mot_ma_am():
    duong = [("M1", "Mã 1", 300), ("M2", "Mã 2", 150), ("M3", "Mã 3", 100),
             ("M4", "Mã 4", 80), ("M5", "Mã 5", 50), ("M6", "Mã 6", 20)]
    am = ("M7", "Phí", -40)
    tong_duong = sum(dt for _, _, dt in duong)          # 700
    dt_nganh = tong_duong + am[2]                        # 660, đúng tổng mã
    nhom = [("Gạo", dt_nganh, None, duong + [am])]
    cq = ve_cay_o(nhom, toi_da_ma=5)
    n = cq["nganh"][0]
    assert n["doanh_thu"] == dt_nganh
    assert n["doanh_thu_ve"] == tong_duong               # 700, không đếm mã âm
    assert cq["khong_ve"] == -40
    assert cq["so_ma_khong_ve"] == 1
    assert _tong_ve(cq) + cq["khong_ve"] == _tong_dau_vao(nhom)
    # Không mã dương nào mất: 5 mã lớn nhất vẽ riêng, mã thứ 6 (20) nằm trọn
    # trong "(khác)".
    ten_rieng = {m["ten"] for m in n["ma"] if m["ten"] != "(khác)"}
    assert ten_rieng == {"Mã 1", "Mã 2", "Mã 3", "Mã 4", "Mã 5"}
    khac = next(m for m in n["ma"] if m["ten"] == "(khác)")
    assert khac["doanh_thu"] == 20


def test_doi_soat_c_ca_nganh_am():
    nhom = [("Gạo", 900, 0.1, [("G1", "Gạo ST25", 900)]),
            ("Chiết khấu", -50, None, [("C1", "Chiết khấu A", -30), ("C2", "Chiết khấu B", -20)])]
    cq = ve_cay_o(nhom)
    assert cq["khong_ve"] == -50
    assert cq["so_ma_khong_ve"] == 2   # cả hai mã của ngành bị bỏ đều được đếm
    assert len(cq["nganh"]) == 1
    assert _tong_ve(cq) + cq["khong_ve"] == _tong_dau_vao(nhom)


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


def test_ve_nhiet_thang_truoc_du_lieu_KHONG_phai_khong_ban():
    """[Vòng soát cuối, I-2] Tháng TRƯỚC `thang_dau_du_lieu` (kỳ 6 = 2024-08
    .. 2025-07 nhưng dữ liệu bán chỉ bắt đầu 2025-03) là "không biết" — bậc
    "truoc_du_lieu", KHÔNG PHẢI "khong_ban" (¥0), vì "không biết" khác "biết
    và bằng không" (NULL≠0). Ngành "Gạo" không có dòng nào trước 2025-03
    trong `dong` — đúng thực tế một view SQL sẽ trả về."""
    thang_ky = [f"2024-{t:02d}" for t in range(8, 13)] + [f"2025-{t:02d}" for t in range(1, 8)]
    dong = [_nt("2025-03", "Gạo", 1000, None, None),
            _nt("2025-04", "Gạo", 1200, None, None)]
    nh = ve_nhiet(dong, thang_ky, thang_cuoi_co_du_lieu="2025-07",
                  thang_dau_du_lieu="2025-03")
    o_gao = {o["thang"]: o for o in nh["o"] if o["nganh"] == "Gạo"}
    for th in ("2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
               "2025-01", "2025-02"):
        assert o_gao[th]["bac"] == "truoc_du_lieu", th
        assert o_gao[th]["doanh_thu"] is None, th
    # Tháng NẰM TRONG khoảng dữ liệu nhưng ngành không có dòng vẫn là
    # "khong_ban" như trước — hành vi cũ không đổi.
    assert nh["thang_dau_du_lieu"] == "2025-03"


def test_ve_nhiet_khong_ban_co_the_ck_false_khi_m12_truoc_du_lieu():
    """[Vòng soát cuối, I-2] Một tháng NẰM TRONG khoảng có dữ liệu mà ngành
    không bán gì ("khong_ban") chỉ được coi "cùng kỳ năm trước cũng vậy" khi
    tháng M-12 CŨNG nằm trong khoảng đã có dữ liệu. Với `thang_dau_du_lieu`
    = "2025-03", tháng "2026-01" có M-12 = "2025-01" (TRƯỚC ngày bắt đầu) ->
    `co_the_ck` phải là False; tháng "2026-04" có M-12 = "2025-04" (sau ngày
    bắt đầu) -> `co_the_ck` phải là True."""
    thang_ky = ["2026-01", "2026-04"]
    dong = [_nt("2025-04", "Gạo", 500, None, None)]  # neo ngành "Gạo" vào dữ liệu
    nh = ve_nhiet(dong, thang_ky, thang_cuoi_co_du_lieu="2026-07",
                  thang_dau_du_lieu="2025-03")
    o_gao = {o["thang"]: o for o in nh["o"] if o["nganh"] == "Gạo"}
    assert o_gao["2026-01"]["bac"] == "khong_ban"
    assert o_gao["2026-01"]["co_the_ck"] is False
    assert o_gao["2026-04"]["bac"] == "khong_ban"
    assert o_gao["2026-04"]["co_the_ck"] is True


def test_ve_nhiet_khong_truyen_thang_dau_giu_nguyen_hanh_vi_cu():
    """`thang_dau_du_lieu=None` (mặc định, gọi rời khỏi `/bao-cao` không biết
    ranh giới) phải giữ NGUYÊN hành vi cũ: không có bậc "truoc_du_lieu" nào,
    và "khong_ban" luôn có `co_the_ck=True`."""
    thang_ky = [f"2025-{t:02d}" for t in range(8, 13)] + [f"2026-{t:02d}" for t in range(1, 8)]
    dong = [_nt("2026-01", "Gạo", 1000, 900, 0.11)]
    nh = ve_nhiet(dong, thang_ky, thang_cuoi_co_du_lieu="2026-01")
    bac_gap = {o["bac"] for o in nh["o"] if o["nganh"] == "Gạo"}
    assert "truoc_du_lieu" not in bac_gap
    o_khong_ban = next(o for o in nh["o"]
                        if o["nganh"] == "Gạo" and o["bac"] == "khong_ban")
    assert o_khong_ban["co_the_ck"] is True
    assert nh["thang_dau_du_lieu"] is None


# ---- ve_pareto ---------------------------------------------------------------

def _kt(ma, dt, hang, luy_ke):
    return KhachTapTrung(ma=ma, ten=ma, doanh_thu=dt, thu_hang=hang, ty_trong=None, luy_ke=luy_ke)


def test_ve_pareto_luy_ke_qua_100_ke_o_mep_tren():
    tt = TapTrung(dong=[_kt("K1", -500, 1, 1.4), _kt("K2", 2000, 2, 0.9)],
                  so_khach=2, luy_ke_top10=None)
    pr = ve_pareto(tt)
    assert pr["co"] is True
    # điểm đầu tiên (luỹ kế 1.4, bị kẹp về 1.0) phải nằm ở mép trên của khung vẽ
    x0, y0 = pr["doan"][0].split(" ")[0].split(",")
    assert abs(float(y0) - 16.0) < 1e-6  # LE_TREN


def test_ve_pareto_rong_khong_co_khach():
    assert ve_pareto(TapTrung(dong=[], so_khach=0, luy_ke_top10=None)) == {"co": False}


def test_ve_pareto_luy_ke_none_cat_doan():
    """[Vòng soát 1, minor 3] Một khách chưa tính được luỹ kế (None) không
    được nối liền với khách kế bên — đường luỹ kế phải đứt tại đó."""
    tt = TapTrung(dong=[_kt("K1", 500, 1, 0.5), _kt("K2", 300, 2, None),
                        _kt("K3", 200, 3, 1.0)],
                  so_khach=3, luy_ke_top10=None)
    pr = ve_pareto(tt)
    assert len(pr["doan"]) == 2


# ---- ve_xu_huong (đợt 5b Task 5, dashboard `/`) -----------------------------

def test_ve_xu_huong_rong_khong_co_ngay():
    assert ve_xu_huong([]) == {"co": False}


def test_ve_xu_huong_it_hon_31_ngay_khong_co_duong():
    """30 ngày đúng khít cho cột, không còn ngày nào liền trước để so —
    KHÔNG được vẽ đường (khác "có đường nhưng đứt")."""
    r = ve_xu_huong(_ngay(30))
    assert r["co"] is True
    assert len(r["cot"]) == 30
    assert r["co_duong"] is False
    assert r["diem"] == []
    assert r["duong"] == ""


def test_ve_xu_huong_60_ngay_30_cot_30_diem():
    r = ve_xu_huong(_ngay(60))
    assert r["co"] is True
    assert len(r["cot"]) == 30
    assert r["co_duong"] is True
    assert len(r["diem"]) == 30
    # Cột là 30 ngày CUỐI, đường là 30 ngày NGAY TRƯỚC ĐÓ — không chồng ngày.
    ngay_cot = {c["ngay"] for c in r["cot"]}
    ngay_duong = {p["ngay"] for p in r["diem"]}
    assert ngay_cot.isdisjoint(ngay_duong)
    assert max(ngay_duong) < min(ngay_cot)


def test_ve_xu_huong_dinh_la_max_ca_hai_day():
    """`dinh` phải tính trên max của CẢ cột lẫn đường — nếu chỉ lấy max(cột),
    một ngày trong 30 ngày TRƯỚC (phần "đường") lớn hơn mọi ngày sau sẽ vẽ
    đường vọt khung. `_ngay(60, ...)` xếp CŨ -> MỚI nên chỉ số 0 (đầu dãy)
    thuộc về phần "đường" (30 ngày trước), KHÔNG phải phần "cột" (30 ngày
    cuối) — đặt đỉnh ở chỉ số 0 mới thật sự kiểm tra nhánh của đường."""
    gia_tri = [999] + [1] * 59  # ngày ĐẦU DÃY (thuộc phần "đường") rất lớn
    r = ve_xu_huong(_ngay(60, gia_tri))
    assert r["dinh"] == 999


def test_ve_xu_huong_31_ngay_can_phai_trung_o_cuoi():
    """[Soát vòng 1] 31 ngày -> đúng 1 điểm đường, phải CĂN PHẢI vào ô CUỐI
    của lưới 30 ô (cùng vị trí X với cột cuối cùng), không dồn về ô đầu."""
    r = ve_xu_huong(_ngay(31))
    assert r["co_duong"] is True
    assert len(r["diem"]) == 1
    assert len(r["cot"]) == 30
    tam_cot_cuoi = r["cot"][-1]["x"] + r["cot"][-1]["w"] / 2
    assert r["diem"][0]["x"] == pytest.approx(tam_cot_cuoi, abs=0.1)


def test_ve_xu_huong_45_ngay_can_phai_vao_dung_o():
    """31–59 ngày (đây: 45 -> 15 điểm đường) phải xếp vào 15 Ô CUỐI của lưới
    30 ô — điểm cuối cùng trùng cột cuối, điểm đầu trùng cột thứ 15 (0-based),
    KHÔNG dồn về các ô đầu (0..14)."""
    r = ve_xu_huong(_ngay(45))
    assert len(r["diem"]) == 15
    tam_cot_cuoi = r["cot"][-1]["x"] + r["cot"][-1]["w"] / 2
    assert r["diem"][-1]["x"] == pytest.approx(tam_cot_cuoi, abs=0.1)
    tam_cot_15 = r["cot"][15]["x"] + r["cot"][15]["w"] / 2
    assert r["diem"][0]["x"] == pytest.approx(tam_cot_15, abs=0.1)
