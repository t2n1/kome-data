"""Đọc trang React của máy chủ trong test (giai đoạn 5: không còn template Jinja).

Máy chủ trả vỏ `index.html` kèm `window.__KOME__` (kome/web/spa.py::trang) —
SỐ nằm ở đó (`man` = dữ liệu màn tính sẵn, `thong_bao` = trang lỗi / 403), còn
CÂU CHỮ cố định nằm trong mã React (giao_dien/src). Test kiểm hai tầng đó."""
import json
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "giao_dien" / "src"


def kd(html: str) -> dict:
    m = re.search(r"<script>window\.__KOME__=(.*?)</script>", html, re.S)
    assert m, "không thấy window.__KOME__ — không phải vỏ React?"
    return json.loads(m.group(1))


def man(html: str) -> dict:
    return kd(html)["man"]


def nguon(*duong: str) -> str:
    return SRC.joinpath(*duong).read_text(encoding="utf-8")
