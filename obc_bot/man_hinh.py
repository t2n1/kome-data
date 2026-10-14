"""Màn hình thật: đang khoá không, và chụp lại khi bấm hỏng."""
from pathlib import Path


def dang_khoa() -> bool:
    """Khoá / màn đăng nhập / ngủ = không mở được bàn làm việc nhận phím chuột."""
    import ctypes
    u = ctypes.windll.user32
    u.OpenInputDesktop.restype = ctypes.c_void_p
    u.OpenInputDesktop.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    u.SwitchDesktop.argtypes = [ctypes.c_void_p]
    u.CloseDesktop.argtypes = [ctypes.c_void_p]
    h = u.OpenInputDesktop(0, False, 0x0100)          # DESKTOP_SWITCHDESKTOP
    if not h:
        return True
    try:
        return not u.SwitchDesktop(h)
    finally:
        u.CloseDesktop(h)


def chup(duong: Path) -> Path | None:
    try:
        from PIL import ImageGrab
        duong.parent.mkdir(parents=True, exist_ok=True)
        ImageGrab.grab().save(duong)
        return duong
    except Exception:
        return None
