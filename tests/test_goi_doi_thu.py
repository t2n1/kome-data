"""Dựng gói bảng giá đối thủ (đặc tả §4.1, §4.3, §7)."""
from datetime import date
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("goi", Path("scripts/goi_doi_thu.py"))
G = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(G)


def _d(**kw):
    d = {"ben": "THAK", "file": "THAK-HANG-KHO-2026.08.05.pdf", "vi_tri": "tr1", "ten_goc": "Bột năng Tài Ký 400g",
         "jan": "", "quy_cach_goc": "400g x 24", "gia_goc": "180", "don_vi_gia": "goi", "kg_moi_don_vi_gia": "0.4",
         "thue": "co", "gom_ship": "khong_ro", "kenh_gia": "", "trang_thai": "con", "ghi_chu": "", "do_chac": "chac"}
    d.update(kw)
    return d


def test_jan_chu_so_kiem():
    assert G.jan_hop_le("8934563321406")
    assert not G.jan_hop_le("8934781067026")       # IMAI tháng 8: sai chữ số kiểm
    assert not G.jan_hop_le("12345")


def test_khoa_hang_uu_tien_jan_roi_ma_ben_roi_ten():
    assert G.ma_hang_dt(_d(jan="8934563321406")) == "jan:8934563321406"
    assert G.ma_hang_dt(_d(vi_tri="danh mục gao · _id 680f5e1c · branches.main", ben="THAI-DUONG")) == "id:680f5e1c"
    assert G.ma_hang_dt(_d(ten_goc="Bột Năng  TÀI KÝ 400gr", quy_cach_goc="400g x 24")) == \
           G.ma_hang_dt(_d(ten_goc="bot nang tai ky 400g", quy_cach_goc="400g x 24"))


def test_id_trong_tu_khac_khong_thanh_khoa():
    assert G.ma_hang_dt(_d(vi_tri="video 12345 tr2")).startswith("ten:")


def test_ngay_lay_tu_ten_file_khong_thi_mac_dinh():
    md = date(2026, 8, 31)
    assert G.suy_ngay("THAK-HANG-KHO-2026.08.05.pdf", md) == date(2026, 8, 5)
    assert G.suy_ngay("2026-8-4 Menu bao gồm thuế.pdf", md) == date(2026, 8, 4)
    assert G.suy_ngay("tdmvn.shop (API, tải 2026-09-29)", md) == date(2026, 9, 29)
    assert G.suy_ngay("IMG_0339.JPG", md) == md


def test_sap_ve_va_muc_gia():
    assert G.suy_trang_thai(_d(trang_thai="het", ghi_chu="Dự kiến tháng 9 xuất hàng")) == "sap_ve"
    assert G.suy_trang_thai(_d(trang_thai="khong_ro", ghi_chu="30/08入荷予定")) == "sap_ve"
    assert G.suy_muc_gia(_d(ben="THAI-DUONG", ghi_chu="mức special (giá đặc biệt)")) == "dac_biet"
    assert G.suy_muc_gia(_d(ben="VIETCOOK", ghi_chu="Giá khách Vietcook = Pallet")) == "pallet"
    assert G.suy_muc_gia(_d()) is None


def test_gop_cap_chua_thue_co_thue_va_bo_trung():
    a = _d(ben="IMAI", thue="chua", gia_goc="90")
    b = _d(ben="IMAI", thue="co", gia_goc="97")
    gia, _, _ = G.dung_goi([a, b, dict(a)], [], date(2026, 8, 31))
    assert len(gia) == 1 and gia[0]["gia_goc"] == "90" and "税込 ¥97" in gia[0]["ghi_chu"]


def test_gia_bat_thuong_thanh_can_xem_khong_chan():
    gia, _, canh = G.dung_goi([_d(gia_goc="5"), _d(ten_goc="X", gia_goc="0")], [], date(2026, 8, 31))
    assert [g["do_chac"] for g in gia] == ["can_xem", "can_xem"]
    assert canh


def test_jan_trung_hai_ma_cung_ben_khong_dung_lam_khoa():
    gia, _, _ = G.dung_goi([_d(jan="8934563321406", ten_goc="Nước dừa"),
                            _d(jan="8934563321406", ten_goc="Nha đam")], [], date(2026, 8, 31))
    assert not any(g["ma_hang_dt"].startswith("jan:") for g in gia)


def test_ma_dong_duy_nhat_va_du_cot():
    from kome.loaders.doi_thu import COT_GIA
    gia, _, _ = G.dung_goi([_d(), _d(ten_goc="Khác")], [], date(2026, 8, 31))
    assert len({g["ma_dong"] for g in gia}) == 2
    assert all(list(g) == COT_GIA for g in gia)
