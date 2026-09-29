"""Chuẩn hoá tên hàng để làm khoá (bỏ dấu, thường hoá, 500gr→500g) — đặc tả Thị trường & đối thủ §4.3."""
import re
import unicodedata


def chuan_ten(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"(\d)\s*gr\b", r"\1g", s)
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", s)).strip()
