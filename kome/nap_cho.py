"""Nạp hai bước (màn Kho dữ liệu → Nạp): file đã KIỂM, đang chờ người bấm Xác nhận.

Bước Kiểm (`POST /upload/kiem`) chép file vào `<archive_dir>/_cho_xac_nhan/<mã>/`
rồi chạy `pipeline.kiem` — không ghi gì vào CSDL. Bước Xác nhận
(`POST /upload/xac-nhan`) gọi `pipeline.ingest` đầy đủ trên đúng file đó (5 cổng
chạy lại) rồi xoá thư mục chờ; Huỷ chỉ xoá thư mục chờ.

Chỉ máy trong công ty có luồng này (bản Vercel chỉ-đọc, ổ đĩa tạm). Mã chờ là
32 ký tự hex ngẫu nhiên và được kiểm dạng trước khi ghép vào đường dẫn — một
biểu mẫu lạ gửi `../..` không chạm được file nào ngoài thư mục chờ. File chờ
quá `GIU_GIO` giờ bị dọn ở lần Kiểm sau: người bỏ đi giữa chừng không để lại
một bản sao 100 MB nằm mãi.
"""
from __future__ import annotations

import json
import re
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

THU_MUC = "_cho_xac_nhan"
GIU_GIO = 24
_MA = re.compile(r"^[0-9a-f]{32}$")


def _goc(archive_dir: Path) -> Path:
    return Path(archive_dir) / THU_MUC


def ten_an_toan(ten: str | None) -> str:
    """Chỉ phần TÊN của file tải lên (bỏ mọi thư mục người gửi kèm theo)."""
    ten = Path((ten or "").replace("\\", "/")).name
    return ten or "file.xlsx"


def luu(archive_dir: Path, nguon: BinaryIO, ten_file: str, o: str) -> tuple[str, Path]:
    ma = uuid.uuid4().hex
    thu_muc = _goc(archive_dir) / ma
    thu_muc.mkdir(parents=True)
    dich = thu_muc / ten_an_toan(ten_file)
    with dich.open("wb") as out:
        shutil.copyfileobj(nguon, out)
    (thu_muc / "cho.json").write_text(json.dumps(
        {"ten_file": dich.name, "o": o, "luc": datetime.now().isoformat(timespec="seconds")},
        ensure_ascii=False), encoding="utf-8")
    return ma, dich


def doc(archive_dir: Path, ma: str) -> tuple[Path, dict] | None:
    if not _MA.match(ma or ""):
        return None
    thu_muc = _goc(archive_dir) / ma
    try:
        meta = json.loads((thu_muc / "cho.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    f = thu_muc / ten_an_toan(meta.get("ten_file"))
    return (f, meta) if f.exists() else None


def xoa(archive_dir: Path, ma: str) -> None:
    if _MA.match(ma or ""):
        shutil.rmtree(_goc(archive_dir) / ma, ignore_errors=True)


def danh_sach(archive_dir: Path) -> list[dict]:
    """File đang chờ xác nhận, cũ nhất trước."""
    goc = _goc(archive_dir)
    if not goc.exists():
        return []
    ra = []
    for d in goc.iterdir():
        x = doc(archive_dir, d.name) if d.is_dir() else None
        if x:
            ra.append({"ma": d.name, **x[1]})
    return sorted(ra, key=lambda r: r.get("luc", ""))


def don_cu(archive_dir: Path, gio: int = GIU_GIO) -> None:
    goc = _goc(archive_dir)
    if not goc.exists():
        return
    han = time.time() - gio * 3600
    for d in goc.iterdir():
        if d.is_dir() and d.stat().st_mtime < han:
            shutil.rmtree(d, ignore_errors=True)
