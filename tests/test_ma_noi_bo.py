"""044 — mã nội bộ (nhân viên 0090…/0099…, mã giữ chỗ OBC) ra khỏi MỌI số liệu bán
hàng, kể cả tổng doanh thu (chủ DN chọn 2026-09-25); ngày đăng ký đọc từ mã khách."""
from datetime import timedelta

import pytest

from kome import khach_hang as KH
from tests.test_khach_hang import HOM_NAY, _ho_so_khach, _mua, _neo

NHAN_VIEN = "009000000001"


@pytest.mark.parametrize("ma,noi_bo", [
    ("009000000001", True), ("009900000094", True),
    ("999999999999", True), ("202411000000", True),
    ("000000009292", False), ("202609240002", False),
    ("999999999991", False),     # ※使用禁止※ nhưng là công ty thật — cờ ※ lo phần đó
    (None, False),
])
def test_ma_noi_bo_dinh_nghia_MOT_LAN_o_mart(conn, ma, noi_bo):
    assert conn.execute("SELECT mart.la_ma_noi_bo(%s)", (ma,)).fetchone()[0] is noi_bo


def test_nhan_vien_mua_hang_khong_vao_so_lieu_nao(conn, batch):
    """Nhân viên có hồ sơ và có phiếu bán: không có trong danh sách khách, không
    thành "khách chưa mua", và phiếu của họ không vào TỔNG doanh thu tháng."""
    _ho_so_khach(conn, batch, NHAN_VIEN, "TRAN TRI NGUYEN")
    _ho_so_khach(conn, batch, "202607010001", "Quán thật")
    # Khác ngày với quán thật: bộ nạp bán hàng thay TRỌN một ngày mỗi lần nạp.
    _mua(conn, batch, NHAN_VIEN, HOM_NAY - timedelta(days=3), tien=55_000, tax=5_000)
    _mua(conn, batch, "202607010001", HOM_NAY - timedelta(days=2), tien=110_000, tax=10_000)
    _neo(conn, batch)

    thang = f"{HOM_NAY:%Y-%m}"
    tong = conn.execute("SELECT doanh_thu_thuan FROM mart.ban_theo_thang WHERE thang = %s",
                        (thang,)).fetchone()[0]
    assert tong == 100_000 + 100_000          # quán thật + _neo; KHÔNG có 50_000 của nhân viên
    assert conn.execute("SELECT count(*) FROM mart.khach_360 WHERE customer_code = %s",
                        (NHAN_VIEN,)).fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM mart.khach_chua_mua WHERE customer_code = %s",
                        (NHAN_VIEN,)).fetchone()[0] == 0
    ds = {k.ma for k in KH.danh_sach(conn, tim="").khach}
    assert NHAN_VIEN not in ds and "202607010001" in ds
    # core KHÔNG bị đụng: dòng bán vẫn còn nguyên (OBC chỉ đọc; Kho dữ liệu đối chiếu file).
    assert conn.execute("SELECT count(*) FROM core.fact_sales_line WHERE customer_code = %s",
                        (NHAN_VIEN,)).fetchone()[0] == 1


def test_ngay_dang_ky_doc_tu_ma_khach(conn, batch):
    assert KH.ngay_dang_ky("202609240002") == "2026-09-24"
    assert KH.ngay_dang_ky("000000009292") == KH.MA_CU_TRUOC
    assert KH.ngay_dang_ky("202411000000") is None     # "ngày 00" — không phải ngày thật
    _ho_so_khach(conn, batch, "202607010001", "Quán mới")
    _mua(conn, batch, "202607010001", HOM_NAY - timedelta(days=2))
    _neo(conn, batch)
    assert KH.ho_so(conn, "202607010001").ho_so["ngay_dang_ky"] == "2026-07-01"
