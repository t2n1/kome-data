"""obc_bot.obc.bang — kiểm bảng Excel OBC vừa đẩy ra, TRƯỚC khi lưu thành file nạp.

Ô ngày / ô pattern của OBC không đọc được qua UIA (docs/obc-ui/LUONG.md), nên đây là lớp kiểm
duy nhất ở phía máy: pattern lệch → thiếu cột; gõ ngày trượt → ngày trong file khác hôm nay."""
from datetime import date

import pytest

from obc_bot.chay import LoiObc
from obc_bot.obc import bang
from obc_bot.ten_file import MUC_SPEC

NGAY = date(2026, 10, 15)
SO = (NGAY - date(1899, 12, 30)).days          # 46310 — số ngày Excel


def test_so_ngay_excel_dung_mau_do_that():
    assert bang.so_ngay_excel(NGAY) == 46310 == SO


@pytest.mark.parametrize("muc", sorted(MUC_SPEC))
def test_cot_can_va_sheet_la_ban_chep_cua_files_yml(muc):
    from kome.config import SPECS
    spec = SPECS[MUC_SPEC[muc]]
    assert bang.COT_CAN[muc] == frozenset(spec.columns)
    assert bang.SHEET[muc] == spec.sheet


def _ban(*dong, hdr=None):
    hdr = hdr or ("売上日付", "伝票No.", "売上日付", "得意先コード", "担当者コード", "商品コード",
                  "荷姿区分コード", "純売上数量", "単価", "税抜純売上高", "粗利益", "粗利益率")
    return (hdr, *dong)


def test_ban_dung_ngay_tra_so_dong():
    assert bang.kiem_bang("ban", _ban((SO, "1", SO), (SO, "2", SO)), NGAY) == 2


def test_ban_mot_dong_lech_ngay_la_loi_noi_ra_ngay_trong_file():
    with pytest.raises(LoiObc, match="2026-09-30") as e:
        bang.kiem_bang("ban", _ban((SO, "1", SO), (SO - 15, "2", SO - 15)), NGAY)
    assert e.value.buoc == "kiểm ngày trong file"


def test_thieu_cot_la_pattern_lech():
    with pytest.raises(LoiObc, match="単価") as e:
        bang.kiem_bang("ban", _ban((SO, "1", SO), hdr=("売上日付", "伝票No.", "売上日付")), NGAY)
    assert e.value.buoc == "kiểm cột (pattern)"


def test_ton_khong_co_cot_ngay_chi_kiem_cot():
    hdr = ("食品分類コード", *sorted(bang.COT_CAN["ton"]))
    assert bang.kiem_bang("ton", (hdr, tuple("x" * len(hdr))), NGAY) == 1


def test_bang_chi_co_header_la_khong_dong():
    assert bang.kiem_bang("ban", _ban(), NGAY) == 0


def test_ton_bo_dong_don_vi_khac_KG_va_ケース_nhu_chu_DN_xoa_tay():
    """Chủ DN 2026-10-15: file tồn chỉ giữ 単位 = KG / ケース. Đo thật: còn lại 袋 / 本 / 個 / 缶 / trống là
    dòng LẺ trùng khoá (商品コード, 倉庫コード) với dòng thùng → cổng 3 chặn cả file."""
    hdr = ("商品コード", "倉庫コード", "単位")
    v = (hdr, ("BS01", "0001", "ケース"), ("BS01", "0001", "缶"), ("R1", "0001", "KG"), ("X", "0001", ""),
         ("Y", "0001", None), ("Z", "0001", "袋"))
    assert bang.dong_bo("ton", v) == [1, 3, 4, 5]          # chỉ số dòng dữ liệu (0 = dòng ngay dưới header)


def test_ban_khong_bo_dong_nao():
    assert bang.dong_bo("ban", _ban((SO, "1", SO))) == []


def test_bang_rong_la_loi():
    with pytest.raises(LoiObc):
        bang.kiem_bang("ban", (), NGAY)
