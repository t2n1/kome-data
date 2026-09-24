"""Màn Kho dữ liệu → "Dữ liệu đi đâu": cột OBC nào bỏ được ở lần xuất sau.

0 truy vấn CSDL — đọc ảnh chụp `kome/web/cot_dung_sinh.json`, do
`scripts/sinh_cot_dung.py` sinh từ danh mục Postgres + `config/files.yml` + mã
`kome/` (xem chú thích đầu script đó; đặc tả
docs/superpowers/specs/2026-09-24-kho-du-lieu-theo-thiet-ke-design.md §A).

KHÔNG nhập pandas / kome.pipeline ở đây — trang chạy cả trên Vercel.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ANH_CHUP = Path(__file__).resolve().parent / "web" / "cot_dung_sinh.json"

# Thứ tự loại = thứ tự xét (loại đầu tiên khớp thắng) = thứ tự hiện trên màn.
LOAI = ["nap", "man", "luu", "khong_nap"]
BO_DUOC = {"luu", "khong_nap"}
FILE_MAC_DINH = "uriage"


@lru_cache(maxsize=1)
def doc_anh_chup() -> dict:
    if not ANH_CHUP.exists():
        return {"files": [], "man": {}, "view_man": {}, "khoa": {"bang": [], "noi": []}}
    return json.loads(ANH_CHUP.read_text(encoding="utf-8"))


def man(file: str | None) -> dict:
    """Dữ liệu cho màn: tóm tắt mọi file + chi tiết MỘT file (ảnh chụp đủ ~250 KB,
    gửi hết xuống trình duyệt là phí — mỗi lần chỉ xem một file)."""
    anh = doc_anh_chup()
    ten = {f["ten"] for f in anh["files"]}
    chon = file if file in ten else (FILE_MAC_DINH if FILE_MAC_DINH in ten else next(iter(sorted(ten)), None))
    tom = [{"ten": f["ten"], "ja": f["ja"], "core_table": f["core_table"], "mau": f["mau"],
            "dem": {l: sum(1 for c in f["cot"] if c["loai"] == l) for l in LOAI}}
           for f in anh["files"]]
    f = next((x for x in anh["files"] if x["ten"] == chon), None)
    view = sorted({v for c in (f["cot"] if f else []) for v in c["view"]})
    return {
        "chon": chon, "files": tom, "file": f,
        "man_hinh": anh["man"],
        "view_man": {v: anh["view_man"].get(v, []) for v in view},
        "khoa": anh["khoa"],
    }
