"""Sổ Excel mà OBC đẩy dữ liệu vào (đo thật 2026-10-15, docs/obc-ui/LUONG.md):
OBC KHÔNG hỏi nơi lưu — mỗi lần xuất nó mở MỘT TIẾN TRÌNH Excel MỚI với một sổ chưa lưu.
`GetActiveObject` chỉ bám một tiến trình (đọc nhầm sổ cũ), nên sổ được lấy qua CHÍNH cửa sổ
`XLMAIN` mới xuất hiện sau cú bấm 出力開始."""
import ctypes
import time
from ctypes import POINTER, byref
from pathlib import Path

_IID_IDISPATCH = "{00020400-0000-0000-C000-000000000046}"
_OBJID_NATIVEOM = -16
_XLSX = 51


def _co_so(h: int) -> bool:
    """Excel còn tạo nhiều `XLMAIN` ẨN không chứa sổ (đo thật: 5 cái) — chỉ tính cửa sổ đang hiện
    và có `XLDESK` › `EXCEL7`, không thì bắt nhầm cửa sổ ẩn và COM trả E_FAIL."""
    import win32gui
    if not win32gui.IsWindowVisible(h):
        return False
    desk = win32gui.FindWindowEx(h, 0, "XLDESK", None)
    return bool(desk and win32gui.FindWindowEx(desk, 0, "EXCEL7", None))


def cua_so() -> set[int]:
    import win32gui
    ds: list[int] = []
    win32gui.EnumWindows(lambda h, _: ds.append(h) if win32gui.GetClassName(h) == "XLMAIN" else None, None)
    return {h for h in ds if _co_so(h)}


def cho_cua_so_moi(truoc: set[int], giay: int) -> int | None:
    for _ in range(giay):
        time.sleep(1)
        moi = cua_so() - truoc
        if moi:
            time.sleep(3)                      # OBC còn đang đổ dữ liệu vào sổ
            return moi.pop()
    return None


def so_cua(hwnd: int, giay: int = 60):
    """Excel mới mở chưa phục vụ COM ngay (đo thật: E_FAIL 3 s sau khi cửa sổ hiện) — thử lại tới `giay`."""
    loi = None
    for _ in range(giay):
        try:
            wb = _so_cua(hwnd)
            wb.Name                            # chạm thử: sổ đã sẵn sàng
            return wb
        except Exception as e:
            loi = e
            time.sleep(1)
    raise loi


def _so_cua(hwnd: int):
    import comtypes.client
    import win32gui
    from comtypes import GUID
    from comtypes.automation import IDispatch
    desk = win32gui.FindWindowEx(hwnd, 0, "XLDESK", None)
    xl7 = win32gui.FindWindowEx(desk, 0, "EXCEL7", None)
    p = POINTER(IDispatch)()
    ctypes.oledll.oleacc.AccessibleObjectFromWindow(xl7, _OBJID_NATIVEOM, byref(GUID(_IID_IDISPATCH)), byref(p))
    return comtypes.client.dynamic.Dispatch(p).Parent      # Window.Parent = Workbook


def gia_tri(wb, sheet: str):
    """`UsedRange.Value2` (comtypes `.Value` có tham số nên lỗi COM; ngày là SỐ NGÀY Excel)."""
    return wb.Worksheets(sheet).UsedRange.Value2


def luu_va_dong(wb, duong: Path) -> Path:
    duong.parent.mkdir(parents=True, exist_ok=True)
    app = wb.Application
    app.DisplayAlerts = False                  # ghi đè file cùng tên của lần chạy trước trong ngày
    wb.SaveAs(str(duong.resolve()), _XLSX)
    dong(wb, app)
    return duong


def dong(wb, app=None) -> None:
    app = app or wb.Application
    wb.Close(False)
    if app.Workbooks.Count == 0:
        app.Quit()
