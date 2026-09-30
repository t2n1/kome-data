"""Trang Doanh thu (2026-09-30) — hình học bong bóng và cầu nối (thuần, không CSDL)."""
import pytest

from kome.bao_cao import NganhKy
from kome import ve_doanh_thu as V


def _n(nganh, dt, lg, dc, ck, tt="auto"):
    ch = dc - ck if dc is not None and ck is not None else None
    t = (dc / ck - 1 if ck else None) if tt == "auto" else tt
    return NganhKy(nganh=nganh, doanh_thu=dt, lai_gop=lg, dt_doi_chieu=dc, dt_cung_ky=ck,
                   chenh_lech=ch, tang_truong=t)


NGANH = [_n("Phở", 5000, 1500, 5000, 4000), _n("Gia vị", 3000, 600, 3000, 3300),
         _n("Mới", 800, 200, None, None, None), _n("Âm", -50, -10, -50, 20),
         _n("Bánh", 1200, 360, 1200, 1100), _n("Gạo", 900, 90, 900, 950)]


def test_cau_noi_DAU_cong_cac_buoc_BANG_CUOI_tung_yen():
    """[IMPORTANT] Đối soát: kỳ so + Σ bước = kỳ này (cùng dải đối chiếu). Danh mục
    không có số so không vào cầu nhưng được nói ra."""
    for toi_da in (1, 2, 8):
        c = V.ve_cau_noi(NGANH, toi_da=toi_da)
        buoc = [x for x in c["cot"] if x["loai"] in ("tang", "giam")]
        assert c["dau"] + sum(x["gia"] for x in buoc) == c["cuoi"]
        assert c["dau"] == sum(n.dt_cung_ky for n in NGANH if n.chenh_lech is not None)
        assert c["cuoi"] == sum(n.dt_doi_chieu for n in NGANH if n.chenh_lech is not None)
        assert c["khong_so"] == {"so": 1, "tien": 800}
        assert len(buoc) <= toi_da + 1
        # Cột cuối kết thúc đúng chỗ bước cuối dừng (vạch nối liền mạch).
        assert buoc[-1]["den"] == c["cuoi"]
    assert V.ve_cau_noi([_n("Mới", 1, 1, None, None, None)]) == {"co": False}


def test_bong_KHONG_VE_duoc_noi_ra_va_doi_soat():
    """[IMPORTANT] Σ tiền của bóng vẽ + `khong_ve` = Σ tiền đầu vào (cùng luật cây ô):
    danh mục doanh thu ≤ 0 hoặc không có số so KHÔNG vẽ nhưng không biến mất lặng lẽ."""
    b = V.bong_danh_muc(NGANH, 0.25)
    assert sum(x["tien"] for x in b["bong"]) + b["khong_ve"] == sum(n.doanh_thu for n in NGANH)
    assert b["so_khong_ve"] == 2 and b["khong_ve"] == 800 - 50
    # Biên là tỷ số các tổng của danh mục (cột mart), không suy diễn.
    pho = next(x for x in b["bong"] if x["ma"] == "Phở")
    assert pho["y"] == pytest.approx(0.3) and pho["x"] == pytest.approx(0.25)
    # Bóng to vẽ trước (nằm dưới), bóng nhỏ trên cùng.
    assert [x["kich"] for x in b["bong"]] == sorted((x["kich"] for x in b["bong"]), reverse=True)
    lg = V.bong_danh_muc(NGANH, 0.25, lg=True)
    assert sum(x["tien"] for x in lg["bong"]) + lg["khong_ve"] == sum(n.lai_gop for n in NGANH)


def test_bong_kep_tang_truong_o_mep_truc():
    b = V.ve_bong([{"ma": "a", "ten": "a", "x": 4.0, "y": .2, "kich": 10, "tien": 10},
                   {"ma": "b", "ten": "b", "x": .1, "y": .3, "kich": 5, "tien": 5}], kep_x=V.KEP_TANG, x_moc=0)
    a = next(x for x in b["bong"] if x["ma"] == "a")
    assert a["kep"] and a["x"] == 4.0          # ô nổi vẫn in số thật
    assert all(b["trai"] <= x["cx"] <= b["phai"] for x in b["bong"])


def test_bong_mat_hang_top_theo_doanh_thu_bo_dong_gop_khong_ma():
    hang = [{"ma": f"M{i}", "ten": f"M{i}", "nhom": "x", "doanh_thu": 100 + i, "lai_gop": 10,
             "ty_suat": .1, "so_khach": i} for i in range(50)]
    hang.append({"ma": "", "ten": "※終売※", "nhom": "x", "doanh_thu": 10**6, "lai_gop": 1,
                 "ty_suat": 0, "so_khach": None})
    b = V.bong_mat_hang(hang, .2)
    assert b["so_ma"] == V.TOP_MAT_HANG and "" not in {x["ma"] for x in b["bong"]}
    assert min(x["tien"] for x in b["bong"]) == 110
