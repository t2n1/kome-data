"""Hình sản phẩm — MỘT nguồn: `config/hinh_san_pham.csv` (cột `sku,imageUrl`, chủ DN
gửi; cập nhật = THAY FILE, không bảng, không migration).

Mã là TEXT (strip, KHÔNG ép số — bẫy #1 số 0 đầu). Chỉ nhận URL bắt đầu đúng
`https://` — dòng khác bỏ qua, không bao giờ đưa `http:` / `javascript:` vào `src`.
File thiếu → `{}` (web vẫn chạy). Không đọc CSDL; web chèn kết quả vào
`window.__KOME__.hinh` (kome/web/app.py::_khoi_dau)."""
from __future__ import annotations

import csv
from pathlib import Path

DUONG = Path(__file__).resolve().parents[1] / "config" / "hinh_san_pham.csv"

_nho: tuple[Path, int, dict[str, str]] | None = None


def xoa_nho() -> None:
    global _nho
    _nho = None


def _doc_file(duong: Path) -> dict[str, str]:
    kq: dict[str, str] = {}
    with duong.open(encoding="utf-8-sig", newline="") as f:
        for dong in csv.DictReader(f):
            ma = (dong.get("sku") or "").strip()
            url = (dong.get("imageUrl") or "").strip()
            if ma and url.startswith("https://") and not any(c in url for c in ' "<>\\'):
                kq[ma] = url
    return kq


def doc() -> dict[str, str]:
    """Bản đồ mã → URL hình. Nhớ theo (đường dẫn, mtime) — thay file là đọc lại."""
    global _nho
    try:
        mtime = DUONG.stat().st_mtime_ns
    except OSError:
        return {}
    if _nho is not None and _nho[0] == DUONG and _nho[1] == mtime:
        return _nho[2]
    try:
        kq = _doc_file(DUONG)
    except (OSError, UnicodeDecodeError, csv.Error):
        return {}
    _nho = (DUONG, mtime, kq)
    return kq
