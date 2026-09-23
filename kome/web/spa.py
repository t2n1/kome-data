"""Phục vụ giao diện React (file build ở kome/web/spa/, commit vào git).

Chuyển TỪNG MÀN: route của một màn đã chuyển trả `index.html` của bản build
thay vì template Jinja. `index.html` được chèn hai thứ trước khi gửi:
  * `data-theme` trên <html> theo cookie — bất biến "không có khung hình sai
    màu" của CLAUDE.md, y như các trang Jinja;
  * `window.__KOME__` — người đang đăng nhập, cờ quyền, bố cục đã lưu — để
    trang vẽ được ngay, không tốn thêm một lượt gọi /api trước khi hiện khung.
"""
from __future__ import annotations

import json
from pathlib import Path

THU_MUC = Path(__file__).parent / "spa"


def van_tay_nguon() -> str | None:
    """Dấu vân tay mã nguồn giao_dien/ — CÙNG thuật toán giao_dien/ghi_van_tay.mjs
    (đường dẫn tương đối kiểu "/", nội dung đổi CRLF -> LF). None khi không có
    thư mục nguồn (bản Vercel: .vercelignore loại giao_dien/)."""
    import hashlib
    goc = THU_MUC.parents[2] / "giao_dien"
    if not (goc / "src").exists():
        return None
    tep = [p for p in (goc / "src").rglob("*") if p.is_file()]
    tep += [goc / t for t in ("index.html", "vite.config.ts", "package.json", "tsconfig.json")]
    h = hashlib.sha1()
    for p in sorted(tep, key=lambda p: p.relative_to(goc).as_posix()):
        h.update(p.relative_to(goc).as_posix().encode())
        h.update(p.read_bytes().decode("utf-8").replace(chr(13) + chr(10), chr(10)).encode())
    return h.hexdigest()


def co_ban_build() -> bool:
    return (THU_MUC / "index.html").exists()


def _an_toan_trong_script(s: str) -> str:
    # JSON nằm trong <script>: "</" đóng thẻ sớm, "<!--" mở chú thích.
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def trang(data_theme: str | None, khoi_dau: dict) -> str:
    html = (THU_MUC / "index.html").read_text(encoding="utf-8")
    the_html = '<html lang="vi"' + (f' data-theme="{data_theme}"' if data_theme else "")
    html = html.replace('<html lang="vi"', the_html, 1)
    tiem = ("<script>window.__KOME__=" +
            _an_toan_trong_script(json.dumps(khoi_dau, ensure_ascii=False, default=str)) +
            "</script>")
    return html.replace("</head>", tiem + "</head>", 1)
