"""Nạp hai bước (màn Kho dữ liệu → Nạp): file đã KIỂM, đang chờ người bấm Xác nhận.

Bước Kiểm (`POST /upload/kiem`) chép file vào `<archive_dir>/_cho_xac_nhan/<mã>/`
rồi chạy `pipeline.kiem` — không ghi gì vào CSDL. Bước Xác nhận
(`POST /upload/xac-nhan`) gọi `pipeline.ingest` đầy đủ trên đúng file đó (5 cổng
chạy lại) rồi xoá thư mục chờ; Huỷ chỉ xoá thư mục chờ.

Hai kiểu kho (migration 045, đặc tả 2026-09-25-nap-tren-vercel-design.md):
`KhoDia` — thư mục trên đĩa, máy trong công ty; `KhoCsdl` — bảng `meta.nap_cho`, bản
Vercel (ổ đĩa tạm, và bước Xác nhận có thể chạy ở một phiên bản hàm khác bước Kiểm).
Chọn bằng `KOME_KHO_NAP` (`kieu_mac_dinh`). Mã chờ là
32 ký tự hex ngẫu nhiên và được kiểm dạng trước khi ghép vào đường dẫn — một
biểu mẫu lạ gửi `../..` không chạm được file nào ngoài thư mục chờ. File chờ
quá `GIU_GIO` giờ bị dọn ở lần Kiểm sau: người bỏ đi giữa chừng không để lại
một bản sao 100 MB nằm mãi.
"""
from __future__ import annotations

import json
import os
import tempfile
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


# ---- Kho hai kiểu (045) ---------------------------------------------------

# Nơi `KhoCsdl.doc` / `luu` bày file ra cho pipeline đọc (pipeline đọc từ `Path`).
# Thư mục tạm của máy — trên Vercel là /tmp, mất khi phiên bản hàm tắt, đúng ý.
THU_MUC_TAM = Path(tempfile.gettempdir()) / "kome_cho"


def kieu_mac_dinh() -> str:
    """`KOME_KHO_NAP` (`dia` | `csdl`); không đặt thì `csdl` trên Vercel, `dia` ở nơi khác."""
    kieu = os.environ.get("KOME_KHO_NAP", "").strip().lower()
    if kieu in ("dia", "csdl"):
        return kieu
    from kome.web.bao_mat import tren_mang
    return "csdl" if tren_mang() else "dia"


class KhoDia:
    """Thư mục `<archive_dir>/_cho_xac_nhan/` — đúng hành vi trước 045."""
    luu_file_goc = True

    def __init__(self, archive_dir: Path):
        self.archive_dir = Path(archive_dir)

    def luu(self, nguon: BinaryIO, ten_file: str, o: str) -> tuple[str, Path]:
        return luu(self.archive_dir, nguon, ten_file, o)

    def doc(self, ma: str) -> tuple[Path, dict] | None:
        return doc(self.archive_dir, ma)

    def xoa(self, ma: str) -> None:
        xoa(self.archive_dir, ma)

    def danh_sach(self) -> list[dict]:
        return danh_sach(self.archive_dir)

    def don_cu(self, gio: int = GIU_GIO) -> None:
        don_cu(self.archive_dir, gio)


class KhoCsdl:
    """Bảng `meta.nap_cho`. Mỗi thao tác một kết nối + commit riêng (vai trò
    kome_ingest — chỉ vai trò đó có quyền trên bảng này)."""
    luu_file_goc = False       # bản Vercel không lưu file gốc (chủ DN chọn 2026-09-25)

    def __init__(self, open_conn):
        self.open_conn = open_conn

    @staticmethod
    def _bay_ra(ma: str, ten: str, noi_dung: bytes) -> Path:
        thu_muc = THU_MUC_TAM / ma
        thu_muc.mkdir(parents=True, exist_ok=True)
        f = thu_muc / ten_an_toan(ten)
        f.write_bytes(noi_dung)
        return f

    def luu(self, nguon: BinaryIO, ten_file: str, o: str) -> tuple[str, Path]:
        ma, ten, noi_dung = uuid.uuid4().hex, ten_an_toan(ten_file), nguon.read()
        with self.open_conn() as c:
            c.execute("INSERT INTO meta.nap_cho (ma, ten_file, o, noi_dung) VALUES (%s,%s,%s,%s)",
                      (ma, ten, o or "", noi_dung))
            c.commit()
        return ma, self._bay_ra(ma, ten, noi_dung)

    def doc(self, ma: str) -> tuple[Path, dict] | None:
        if not _MA.match(ma or ""):
            return None
        with self.open_conn() as c:
            r = c.execute("SELECT ten_file, o, luc, noi_dung FROM meta.nap_cho WHERE ma = %s",
                          (ma,)).fetchone()
        if r is None:
            return None
        meta = {"ten_file": r[0], "o": r[1], "luc": r[2].isoformat(timespec="seconds")}
        return self._bay_ra(ma, r[0], bytes(r[3])), meta

    def xoa(self, ma: str) -> None:
        if not _MA.match(ma or ""):
            return
        with self.open_conn() as c:
            c.execute("DELETE FROM meta.nap_cho WHERE ma = %s", (ma,))
            c.commit()
        shutil.rmtree(THU_MUC_TAM / ma, ignore_errors=True)

    def danh_sach(self) -> list[dict]:
        """File đang chờ, cũ nhất trước — KHÔNG kéo cột nội dung."""
        with self.open_conn() as c:
            rows = c.execute("SELECT ma, ten_file, o, luc FROM meta.nap_cho ORDER BY luc").fetchall()
        return [{"ma": r[0], "ten_file": r[1], "o": r[2], "luc": r[3].isoformat(timespec="seconds")}
                for r in rows]

    def don_cu(self, gio: int = GIU_GIO) -> None:
        with self.open_conn() as c:
            c.execute("DELETE FROM meta.nap_cho WHERE luc < now() - make_interval(hours => %s)",
                      (gio,))
            c.commit()


def tao_kho(kieu: str, archive_dir: Path, open_conn) -> KhoDia | KhoCsdl:
    return KhoCsdl(open_conn) if kieu == "csdl" else KhoDia(archive_dir)
