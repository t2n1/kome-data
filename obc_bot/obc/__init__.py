"""Nửa XUẤT — bấm 商奉行クラウド (pywinauto, backend uia) theo luồng đo thật ở docs/obc-ui/LUONG.md.

Giao diện cố định cho chay.py: xuat(muc, ngay, thu_muc, pattern) -> Path đúng tên `ten_file(muc, ngay)`;
khoi_dong_lai() đóng báo cáo đang mở dở. Lỗi nào cũng ném chay.LoiObc(bước, lỗi, ảnh chụp).
`pattern` = VỊ TRÍ dòng trong hộp thoại パターン選択 (1 = dòng đầu) — tên pattern không đọc được qua UIA;
pattern lệch thì `bang.kiem_bang` bắt bằng header."""
from datetime import date, datetime
from pathlib import Path

from obc_bot.chay import LoiObc
from obc_bot.ten_file import ten_file

CHO_EXCEL_GIAY = 300          # bản xuất lớn (得意先全情報 ~2,5 MB) cần thời gian


def _chup(thu_muc: Path) -> Path | None:
    from obc_bot import man_hinh
    return man_hinh.chup(thu_muc / "_loi" / f"{datetime.now():%Y%m%d_%H%M%S}.png")


def xuat(muc: str, ngay: date, thu_muc: Path, pattern: int) -> Path:
    from obc_bot.obc import bang, excel, man
    if muc not in man.MAN:
        raise LoiObc("chưa đo", f"luồng bấm OBC cho mục {muc!r} chưa đo trên máy có quyền — xuất tay rồi dùng lệnh nap")
    m = man.MAN[muc]
    wb = None
    try:
        top = man.mo_bao_cao(m)
        man.chon_pattern(top, pattern)
        if m.co_ngay:
            man.go_ngay(top, ngay)
        truoc = excel.cua_so()
        man.xuat_sang_excel(top)
        h = excel.cho_cua_so_moi(truoc, CHO_EXCEL_GIAY)
        if h is None:
            raise LoiObc("chờ Excel", f"sau {CHO_EXCEL_GIAY} s không thấy Excel mở sổ mới")
        wb = excel.so_cua(h)
        bang.kiem_bang(muc, excel.gia_tri(wb, bang.SHEET[muc]), ngay)
        duong = excel.luu_va_dong(wb, thu_muc / ten_file(muc, ngay))
        wb = None
        man.dong_bao_cao(m.cua_so)
        return duong
    except LoiObc as e:
        if e.anh is None:
            e.anh = _chup(thu_muc)
        raise
    except Exception as e:                     # pywinauto / COM: báo bằng bước chung, kèm ảnh
        raise LoiObc(f"xuất {muc}", repr(e), _chup(thu_muc)) from e
    finally:
        if wb is not None:                     # sổ sai / lỗi giữa chừng: đóng không lưu, không để Excel treo
            try:
                excel.dong(wb)
            except Exception:
                pass


def khoi_dong_lai() -> None:
    from obc_bot.obc import man
    for m in man.MAN.values():
        man.dong_bao_cao(m.cua_so)
