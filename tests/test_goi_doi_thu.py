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
    gia, _, _, _ = G.dung_goi([a, b, dict(a)], [], date(2026, 8, 31))
    assert len(gia) == 1 and gia[0]["gia_goc"] == "90" and "税込 ¥97" in gia[0]["ghi_chu"]


def test_gia_bat_thuong_thanh_can_xem_khong_chan():
    gia, _, _, canh = G.dung_goi([_d(gia_goc="5"), _d(ten_goc="X", gia_goc="0")], [], date(2026, 8, 31))
    assert [g["do_chac"] for g in gia] == ["can_xem", "can_xem"]
    assert canh


def test_jan_trung_hai_ma_cung_ben_khong_dung_lam_khoa():
    gia, _, _, _ = G.dung_goi([_d(jan="8934563321406", ten_goc="Nước dừa"),
                            _d(jan="8934563321406", ten_goc="Nha đam")], [], date(2026, 8, 31))
    assert not any(g["ma_hang_dt"].startswith("jan:") for g in gia)


def test_ma_dong_duy_nhat_va_du_cot():
    from kome.loaders.doi_thu import COT_GIA
    gia, _, _, _ = G.dung_goi([_d(), _d(ten_goc="Khác")], [], date(2026, 8, 31))
    assert len({g["ma_dong"] for g in gia}) == 2
    assert all(list(g) == COT_GIA for g in gia)


def test_web_api_co_word_boundary():
    """API and Google Sheet must be word-bounded, not match inside longer words."""
    gia, _, _, _ = G.dung_goi([_d(file="Tapioca-price.pdf", ten_goc="Item1"),
                            _d(file="RAPID-list.pdf", ten_goc="Item2")], [], date(2026, 8, 31))
    assert gia[0]["hinh_thuc_nguon"] == "file"
    assert gia[1]["hinh_thuc_nguon"] == "file"
    # But actual web sources should still match
    gia2, _, _, _ = G.dung_goi([_d(file="tdmvn.shop (API, tải 2026-09-29)")], [], date(2026, 8, 31))
    assert gia2[0]["hinh_thuc_nguon"] == "web"


def test_sap_ve_chi_khi_het_hoac_khong_ro():
    """sap_ve note only triggers sap_ve status if current status is het, khong_ro, or empty."""
    # Current status "con" + future delivery note → stay "con"
    assert G.suy_trang_thai(_d(trang_thai="con", ghi_chu="Dự kiến tháng 9 xuất hàng")) == "con"
    # Current status "het" + future delivery note → sap_ve
    assert G.suy_trang_thai(_d(trang_thai="het", ghi_chu="Dự kiến tháng 9 xuất hàng")) == "sap_ve"
    # Current status "khong_ro" + future delivery note → sap_ve
    assert G.suy_trang_thai(_d(trang_thai="khong_ro", ghi_chu="30/08入荷予定")) == "sap_ve"
    # Empty/None status + future delivery note → sap_ve
    assert G.suy_trang_thai(_d(trang_thai="", ghi_chu="sắp về")) == "sap_ve"


def test_chay_tren_console_khong_utf8_khong_vo(tmp_path):
    """Console Windows cp1252: dòng tóm tắt tiếng Việt không được làm script nổ UnicodeEncodeError."""
    import csv, os, subprocess, sys
    vao = tmp_path / "vao"; vao.mkdir()
    d = _d()
    with open(vao / "spike_THAK.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(d)); w.writeheader(); w.writerow(d)
    ra = tmp_path / "ra"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
    env["PYTHONUTF8"] = "0"
    r = subprocess.run([sys.executable, "scripts/goi_doi_thu.py", str(vao), "--ngay", "2026-08-31", "--ra", str(ra)],
                       env=env, capture_output=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert (ra / "doi_thu_gia_20260831.xlsx").exists()
    assert (ra / "doi_thu_dieu_kien_20260831.xlsx").exists()


def _dn(**kw):
    d = {"ben": "NEXT", "file": "NEXT.pdf", "vi_tri": "tr1", "ten_goc": "CÁ BASA", "quy_cach_goc": "500g×20袋",
         "gia_goc": "5500", "don_vi_gia": "thung", "kg_moi_don_vi_gia": "10", "thue": "chua", "trang_thai": "con"}
    d.update(kw)
    return d


def test_kiem_bac_chuan_hoa_va_bat_loi():
    ok, loi = G.kiem_bac('[{"tu": 5, "don_vi_sl": "thung", "gia": "5,300", "don_vi_gia": "thung"}]')
    assert loi is None and ok == [{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]
    assert G.kiem_bac("") == (None, None)
    for xau in ('{"tu": 5}', '[{"tu": 0, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "kg"}]',
                '[{"tu": 5, "don_vi_sl": "hop", "gia": 1, "don_vi_gia": "kg"}]', "khong phai json",
                "[" + ",".join(['{"tu": 1, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "kg"}'] * 11) + "]"):
        b, loi = G.kiem_bac(xau)
        assert b is None and loi, xau


def test_goi_mang_quy_cach_va_bac_va_so_nguyen():
    g, _, _, canh = G.dung_goi([_dn(so_goi_thung="20", kl_goi_g="500",
                                    bac='[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]')],
                               [], date(2026, 8, 31))
    assert g[0]["so_goi_thung"] == 20 and g[0]["kl_goi_g"] == 500.0
    assert g[0]["bac"] == '[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]'
    assert g[0]["do_chac"] == "chac" and not canh


def test_gia_goc_phai_la_gia_le_khong_duoc_re_hon_bac():
    # AI ghi bậc rẻ nhất (5.300) vào gia_goc còn bậc lẻ (5.500) nằm trong bac → cần xem
    g, _, _, canh = G.dung_goi([_dn(gia_goc="5300",
                                    bac='[{"tu": 1, "don_vi_sl": "thung", "gia": 5500, "don_vi_gia": "thung"}]')],
                               [], date(2026, 8, 31))
    assert g[0]["do_chac"] == "can_xem" and "giá lẻ" in g[0]["ghi_chu"]


def test_bac_hong_thi_can_xem_khong_chan_ca_goi():
    g, _, _, canh = G.dung_goi([_dn(bac="5cs: 5,300"), _dn(vi_tri="tr2", ten_goc="Khác")], [], date(2026, 8, 31))
    assert g[0]["bac"] is None and g[0]["do_chac"] == "can_xem" and len(g) == 2


def test_ghi_chu_cua_nguoi_doc_thanh_loai_ghi_chu_doc():
    assert G.la_ghi_chu_doc("mỗi mặt hàng in 'Kiện 1th' … — chép vào ghi_chu từng dòng; không in phí ship")
    assert G.la_ghi_chu_doc("Dữ liệu này KHÔNG có phí ship chung, vùng giao hay đơn tối thiểu")
    assert G.la_ghi_chu_doc("Không tìm thấy phí ship / ngưỡng miễn ship trên các trang đã đọc")
    assert not G.la_ghi_chu_doc("Kiện 28kg ghép 3 sản phẩm - bao thuế bao ship!")
    _, dk, _, _ = G.dung_goi([], [{"ben": "VIETCOOK", "file": "v.pdf", "loai": "ship",
                                   "noi_dung": "chép vào ghi_chu từng dòng; không in phí ship"}], date(2026, 8, 31))
    assert dk[0]["loai"] == "ghi_chu_doc"


def test_goi_giao_hang_ep_kieu_va_kiem_phu_phi():
    _, _, gh, canh = G.dung_goi([], [], date(2026, 8, 31), giao=[
        {"ben": "IMAI", "file": "imai.pdf", "bao_ship": "false", "phi_ship": "605", "phi_ship_theo": "thung",
         "mien_ship_tu": "20,000", "phu_phi": '{"tohoku": 400, "hokkaido": 800}', "phi_daibiki": "440",
         "nguon_chu": "Free delivery for over ¥20,000"},
        {"ben": "VIETNAM-HOUSE", "file": "vh.pdf", "phu_phi": '{"okinawa": "x"}'}])
    assert gh[0]["ma_dong"] == "IMAI-00001" and gh[0]["mien_ship_tu"] == 20000.0 and gh[0]["phi_ship_theo"] == "thung"
    assert gh[0]["phu_phi"] == '{"tohoku": 400, "hokkaido": 800}'
    assert gh[1]["phu_phi"] is None and any("phu_phi" in c for c in canh)   # chỉ nhận số ¥ hoặc "khong_nhan"


def test_main_ghi_file_giao_hang_khi_co_csv_giao_hang(tmp_path):
    import csv, subprocess, sys
    vao = tmp_path / "vao"; vao.mkdir()
    with open(vao / "spike_IMAI_giao_hang.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ben", "file", "phi_ship", "phi_ship_theo"]); w.writeheader()
        w.writerow({"ben": "IMAI", "file": "imai.pdf", "phi_ship": "605", "phi_ship_theo": "thung"})
    ra = tmp_path / "ra"
    r = subprocess.run([sys.executable, "scripts/goi_doi_thu.py", str(vao), "--ngay", "2026-08-31", "--ra", str(ra)],
                       capture_output=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert (ra / "doi_thu_giao_hang_20260831.xlsx").exists()
