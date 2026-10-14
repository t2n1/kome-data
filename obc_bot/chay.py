"""Một lượt chạy: kiểm trước -> xuất từng mục còn thiếu -> nạp -> MỘT kết cục.

Mọi thứ chạm thế giới thật (màn hình, OBC, keyring, thông báo, đồng hồ ngủ) đi
qua MoiTruong để test thay được — phần bấm OBC không có test tự động."""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

from obc_bot.cau_hinh import CauHinh
from obc_bot.ten_file import ten_file
from obc_bot.web import LoiWeb

CAN_BAO = ("cong_chan", "loi_obc", "man_hinh_khoa", "loi_web")
_UU_TIEN = ("loi_web", "loi_obc", "cong_chan")


class LoiObc(Exception):
    def __init__(self, buoc: str, loi: str, anh: Path | None = None):
        super().__init__(f"{buoc}: {loi}")
        self.buoc, self.loi, self.anh = buoc, loi, anh


@dataclass
class KetCuc:
    loai: str
    chi_tiet: list[str]
    anh: list[Path] = field(default_factory=list)

    @property
    def can_bao(self) -> bool:
        return self.loai in CAN_BAO


@dataclass
class MoiTruong:
    man_hinh_khoa: Callable[[], bool]
    xuat: Callable[[str, date, Path, int], Path]
    khoi_dong_lai_obc: Callable[[], None]
    mat_khau: Callable[[str], str]
    thong_bao: Callable[[str, str], None]
    ngu: Callable[[int], None]


def _xuat_thu_lai(ch: CauHinh, mt: MoiTruong, muc: str, ngay: date, thu_muc: Path) -> Path:
    """Hỏng lần đầu -> mở lại OBC rồi thử ĐÚNG một lần nữa (không giành phiên qua lại)."""
    try:
        p = mt.xuat(muc, ngay, thu_muc, ch.pattern[muc])
    except LoiObc:
        mt.khoi_dong_lai_obc()
        p = mt.xuat(muc, ngay, thu_muc, ch.pattern[muc])
    if p.name != ten_file(muc, ngay) or not p.exists():
        raise LoiObc("kiểm file ra", f"được {p}, cần {ten_file(muc, ngay)}")
    return p


def chay(ch: CauHinh, web, mt: MoiTruong) -> KetCuc:
    if mt.man_hinh_khoa():
        return KetCuc("man_hinh_khoa", ["Windows đang khoá màn hình hoặc ngủ — không bấm được OBC."])
    try:
        if ch.tai_khoan_web:
            web.dang_nhap(ch.tai_khoan_web, mt.mat_khau(ch.tai_khoan_web))
        hn = web.hom_nay()
    except LoiWeb as e:
        return KetCuc("loi_web", [str(e)])
    if not hn["la_ngay_kd"]:
        return KetCuc("bo_qua", [f"{hn['ngay']} không phải ngày làm việc."])
    can = [m for m in ch.muc if not hn["da_co"][m]]
    if not can:
        return KetCuc("bo_qua", [f"Hôm nay đã có đủ: {', '.join(ch.muc)}."])

    ngay = date.fromisoformat(hn["ngay"])
    thu_muc = ch.thu_muc_ra / f"{ngay:%Y-%m}"
    if ch.dem_nguoc_giay:
        mt.thong_bao("Sắp lấy dữ liệu OBC",
                     f"Sau {ch.dem_nguoc_giay} giây chương trình sẽ dùng chuột vài phút.")
        mt.ngu(ch.dem_nguoc_giay)

    van_de: list[tuple[str, str]] = []
    anh: list[Path] = []
    files: list[Path] = []
    for m in can:
        try:
            files.append(_xuat_thu_lai(ch, mt, m, ngay, thu_muc))
        except LoiObc as e:
            van_de.append(("loi_obc", f"{m}: bước '{e.buoc}': {e.loi}"))
            if e.anh:
                anh.append(e.anh)

    xong: list[str] = []
    if files:
        try:
            for k in web.nap(files):
                if k["ok"]:
                    xong.append(f"{k['ten_file']}: {k['row_count']} dòng"
                                + (" (đã có, bỏ qua)" if k["skipped"] else ""))
                else:
                    van_de += [("cong_chan", f"{k['ten_file']}: cổng {b['cong']}: {b['loi']}")
                               for b in k["blockers"]]
        except LoiWeb as e:
            van_de.append(("loi_web", f"{e} — file đã xuất nằm ở {thu_muc}, nạp tay được."))

    if not van_de:
        return KetCuc("xong", xong)
    loai = next(l for l in _UU_TIEN if any(v[0] == l for v in van_de))
    return KetCuc(loai, [v[1] for v in van_de] + xong, anh)
