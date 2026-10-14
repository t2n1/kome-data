"""Cấu hình của MỘT máy chạy (TOML). Mật khẩu web KHÔNG nằm ở đây — keyring."""
import socket
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from obc_bot.ten_file import MUC_SPEC

_NOI_BO = {"127.0.0.1", "localhost", "testserver"}


class CauHinhSai(Exception):
    pass


@dataclass(frozen=True)
class CauHinh:
    muc: tuple[str, ...]
    web_url: str
    tai_khoan_web: str              # "" = web không có cổng đăng nhập (máy công ty để trống khoá)
    thu_muc_ra: Path
    thu_muc_bao_loi: Path | None
    pattern: dict[str, int]         # mục -> số 出力パターン trong OBC
    dem_nguoc_giay: int
    ten_may: str


def doc(duong: Path) -> CauHinh:
    with open(duong, "rb") as f:
        d = tomllib.load(f)
    muc = tuple(d.get("muc", ()))
    if not muc:
        raise CauHinhSai("`muc` phải có ít nhất một mục (ban / ton / khach).")
    la = [m for m in muc if m not in MUC_SPEC]
    if la or len(set(muc)) != len(muc):
        raise CauHinhSai(f"`muc` có mục lạ hoặc lặp: {list(muc)} — chỉ nhận {sorted(MUC_SPEC)}.")
    url = str(d.get("web_url", "")).rstrip("/")
    u = urlparse(url)
    if not (u.scheme == "https" or (u.scheme == "http" and u.hostname in _NOI_BO)):
        raise CauHinhSai(f"`web_url` phải là https:// (http chỉ cho máy nội bộ): {url!r}")
    pattern = {k: v for k, v in d.get("pattern", {}).items()}
    for m in muc:
        if not isinstance(pattern.get(m), int) or pattern[m] <= 0:
            raise CauHinhSai(f"Thiếu [pattern] {m} = <số 出力パターン > 0>.")
    loi = d.get("thu_muc_bao_loi")
    return CauHinh(
        muc=muc, web_url=url, tai_khoan_web=str(d.get("tai_khoan_web", "")),
        thu_muc_ra=Path(d["thu_muc_ra"]), thu_muc_bao_loi=Path(loi) if loi else None,
        pattern={m: pattern[m] for m in muc},
        dem_nguoc_giay=int(d.get("dem_nguoc_giay", 0)),
        ten_may=str(d.get("ten_may") or socket.gethostname()))
