"""Hồ sơ khách 360° thiết kế lại (đặc tả 2026-09-26-ho-so-khach-360-thiet-ke-lai-design.md).
Canh bằng cách đọc mã nguồn TSX — cùng nếp tests/test_ban_do.py."""
from pathlib import Path

KH = Path(__file__).resolve().parents[1] / "giao_dien" / "src" / "khach"


def _doc(ten: str) -> str:
    return (KH / ten).read_text(encoding="utf-8")


def test_khoi_ma_cot_trai_KHONG_mang_ten_Nen_chao_cua_lien_he():
    """'Nên chào' của /lien-he là 3 mã mua nhiều lần nhất (LH.CACH_TINH_GOI_Y);
    khối hồ sơ đọc lich (ngày mua lại dự kiến). Hai định nghĩa, hai tên."""
    for f in ("HoSo.tsx", "HoSoViec.tsx", "HoSoTab.tsx"):
        assert "Nên chào" not in _doc(f), f
    assert "Mã đến ngày mua lại" in _doc("HoSoViec.tsx")


def test_khach_ngung_giao_dich_khong_co_khoi_ma_hay_kich_ban():
    v = _doc("HoSoViec.tsx")
    assert '"ngung_giao_dich"' in v


def test_khoi_khong_nguon_da_bo_va_hai_khoi_sap_co_con():
    tab = _doc("HoSoTab.tsx")
    for bo in ("PhanTan", "DongHo", "Gợi ý tiếp khách", "Tạo đơn nháp", "Bảng giá của bậc"):
        assert bo not in tab, bo
    assert "Ảnh cửa hàng" in tab and "Chat Facebook" in tab and "KhoiSapCo" in tab
    sc = _doc("KhoiSapCo.tsx")
    assert "Chưa có nguồn" in sc and "disabled" not in sc


def test_hash_cu_va_loi_tx_van_duoc_xu_ly():
    hs = _doc("HoSo.tsx")
    assert "tabTuHash" in hs and 'get("loi_tx")' in hs
    assert "TN.cong_no" in hs


def test_nhan_hang_noi_ro_la_hang_theo_doanh_thu():
    assert 'title="hạng theo doanh thu 12 tháng"' in _doc("HoSo.tsx")
