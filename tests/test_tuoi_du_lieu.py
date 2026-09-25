"""Ô cảnh báo "hôm nay chưa có dữ liệu" cho 3 nguồn cập nhật hằng ngày.

Mọi test đều BƠM `bay_gio` vào: không test nào được phụ thuộc đồng hồ thật,
nếu không thì bộ test sẽ đổi kết quả theo giờ chạy và xanh/đỏ tuỳ lúc.
"""
from datetime import date, datetime

import pytest

from kome.tuoi_du_lieu import MUI_GIO, tinh_tuoi


def _lo(conn, spec: str, ngay: date, n: int = 0, da_huy: bool = False) -> int:
    """Một lô đã nạp cho `spec`, dữ liệu mang ngày `ngay`."""
    row = conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count,
              data_date, undone_at)
           VALUES (%s, 'x.xlsx', %s, '/tmp/x.xlsx', 0, %s, %s)
           RETURNING batch_id""",
        (spec, f"d-{spec}-{ngay}-{n}", ngay, datetime(2026, 1, 1) if da_huy else None),
    ).fetchone()
    conn.commit()
    return row[0]


def _luc(y: int, m: int, d: int, gio: int, phut: int = 0) -> datetime:
    return datetime(y, m, d, gio, phut, tzinfo=MUI_GIO)


# Thứ Năm 2026-09-17 — ngày làm việc, dùng cho phần lớn test.
THU_NAM = date(2026, 9, 17)


def test_du_ca_ba_nguon_mang_ngay_hom_nay_thi_xanh(conn):
    for spec in ("zaiko", "tokuisaki", "uriage"):
        _lo(conn, spec, THU_NAM)
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 14, 0))
    assert [n.trang_thai for n in t.nguon] == ["xanh", "xanh", "xanh"]
    assert t.co_thieu is False


def test_truoc_gio_chot_thi_cho_chu_khong_do(conn):
    """8 giờ sáng chưa ai xuất file là chuyện bình thường.

    Đỏ từ sáng nghĩa là sáng nào cũng đỏ, và một dải đỏ vĩnh viễn dạy người
    đọc bỏ qua dải đỏ — đúng thứ hệ thống này cần họ tin.
    """
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 8, 0))
    assert [n.trang_thai for n in t.nguon] == ["cho", "cho", "cho"]
    assert t.co_thieu is False


def test_qua_gio_chot_van_chua_co_thi_do(conn):
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 13, 31))
    assert [n.trang_thai for n in t.nguon] == ["do", "do", "do"]
    assert t.co_thieu is True


def test_dung_13h30_da_tinh_la_qua_gio(conn):
    """Biên: 13:30 là giờ chốt, không phải 13:31."""
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 13, 30))
    assert t.co_thieu is True


def test_cuoi_tuan_thi_im_lang(conn):
    """Thứ Bảy không ai xuất file. Báo đỏ ngày nghỉ là báo động giả.

    Ngày nghỉ lấy từ mart.lich_kinh_doanh (cuối tuần + ngày lễ Nhật, 032) —
    xem tests/test_ngay_le.py cho ca ngày lễ.
    """
    t = tinh_tuoi(conn, _luc(2026, 9, 19, 15, 0))   # thứ Bảy
    assert [n.trang_thai for n in t.nguon] == ["nghi", "nghi", "nghi"]
    assert t.co_thieu is False


def test_nguon_chua_nap_bao_gio(conn):
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 14, 0))
    assert [n.ngay for n in t.nguon] == [None, None, None]
    assert t.co_thieu is True


def test_lo_da_hoan_tac_khong_duoc_tinh(conn):
    """Bấm Hoàn tác xong mà ô vẫn xanh thì nó đang nói dối."""
    _lo(conn, "zaiko", THU_NAM, da_huy=True)
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 14, 0))
    assert t.nguon[0].trang_thai == "do"
    assert t.nguon[0].ngay is None


def test_tre_dem_theo_ngay_lam_viec_bo_cuoi_tuan(conn):
    """Dữ liệu từ thứ Sáu, hôm nay thứ Hai => trễ 1 ngày làm việc, không phải 3.
    (Bản trước dùng 18/9 → 21/9/2026 — nhưng 21/9/2026 là 敬老の日; từ 032 ngày
    đó là ngày nghỉ, nên đổi sang một tuần không có lễ.)"""
    _lo(conn, "zaiko", date(2026, 9, 11))           # thứ Sáu
    t = tinh_tuoi(conn, _luc(2026, 9, 14, 14, 0))   # thứ Hai
    assert t.nguon[0].tre == 1


def test_co_du_lieu_hom_nay_thi_tre_bang_khong(conn):
    _lo(conn, "zaiko", THU_NAM)
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 14, 0))
    assert t.nguon[0].tre == 0


def test_chua_nap_bao_gio_thi_khong_tinh_duoc_so_ngay_tre(conn):
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 14, 0))
    assert t.nguon[0].tre is None


def test_o_ban_hang_nhan_ca_meisai_lan_uriage(conn):
    """Từ 2026-09-24 file bán hằng ngày là 売上明細表 (meisai); 売上伝票データ
    (uriage) chỉ còn xuất theo quý. Sự cố thật 2026-09-25: đã nạp 売上明細表 hôm
    nay mà ô vẫn đỏ "売上伝票データ trễ 36 ngày" vì ô chỉ đọc uriage."""
    _lo(conn, "uriage", date(2026, 7, 31))
    for spec in ("zaiko", "tokuisaki", "meisai"):
        _lo(conn, spec, THU_NAM)
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 14, 0))
    ban = t.nguon[2]
    assert ban.spec == "meisai" and ban.trang_thai == "xanh" and ban.ngay == THU_NAM
    assert t.co_thieu is False


def test_o_ban_hang_lay_ngay_MOI_NHAT_cua_hai_loai(conn):
    _lo(conn, "meisai", date(2026, 9, 10))
    _lo(conn, "uriage", date(2026, 9, 14))
    t = tinh_tuoi(conn, _luc(2026, 9, 17, 14, 0))
    assert t.nguon[2].ngay == date(2026, 9, 14)
    assert t.nguon[0].ngay is None      # zaiko không mượn ngày của ô khác
