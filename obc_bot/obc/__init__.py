"""Nửa XUẤT — bấm 商奉行クラウド (pywinauto, backend uia).

Giao diện cố định cho chay.py: xuat(muc, ngay, thu_muc, pattern) -> Path đúng
tên `ten_file(muc, ngay)`; khoi_dong_lai() đóng hộp thoại lạ / mở lại OBC. Lỗi
nào cũng ném chay.LoiObc(bước, lỗi, ảnh chụp). Thân thật viết ở Task 7, SAU khi
có cây điều khiển đo thật (`python -m obc_bot do`)."""
from datetime import date
from pathlib import Path


def xuat(muc: str, ngay: date, thu_muc: Path, pattern: int) -> Path:
    from obc_bot.chay import LoiObc
    raise LoiObc("chưa viết", f"phần bấm OBC cho mục {muc!r} chưa có — xuất tay rồi dùng lệnh nap")


def khoi_dong_lai() -> None:
    return None
