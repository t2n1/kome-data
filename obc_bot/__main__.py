"""python -m obc_bot <lệnh> --cau-hinh <máy>.toml ...

  nap FILE...      chỉ nạp file đã có (xuất tay) — lối dự phòng khi phần bấm OBC hỏng
  xuat --muc ban|ton [--ngay YYYY-MM-DD]   chỉ bấm OBC ra file (không nạp) — để thử / xuất tay có kiểm
  chay   một lượt đầy đủ: kiểm -> xuất OBC -> nạp -> báo (Task Scheduler gọi lệnh này)
  luu-mat-khau     lưu mật khẩu web của tai_khoan_web vào Windows Credential Manager
"""
import argparse
import getpass
import sys
from pathlib import Path

from obc_bot import cau_hinh as CH
from obc_bot.web import DICH_VU_KEYRING, KhachWeb, LoiWeb, mat_khau_web


def _web(ch: CH.CauHinh) -> KhachWeb:
    w = KhachWeb(ch.web_url)
    if ch.tai_khoan_web:
        w.dang_nhap(ch.tai_khoan_web, mat_khau_web(ch.tai_khoan_web))
    return w


def lenh_nap(ch: CH.CauHinh, files: list[Path]) -> int:
    try:
        kq = _web(ch).nap(files)
    except LoiWeb as e:
        print(f"LỖI WEB: {e}")
        return 1
    for k in kq:
        if k["ok"]:
            print(f"OK   {k['ten_file']}: {k['row_count']} dòng"
                  + (" (đã có, bỏ qua)" if k["skipped"] else ""))
        else:
            for b in k["blockers"]:
                print(f"CHẶN {k['ten_file']}: cổng {b['cong']}: {b['loi']}")
    return 0 if all(k["ok"] for k in kq) else 1


def lenh_luu_mat_khau(ch: CH.CauHinh) -> int:
    import keyring
    if not ch.tai_khoan_web:
        print("Cấu hình không có tai_khoan_web — không cần mật khẩu.")
        return 0
    keyring.set_password(DICH_VU_KEYRING, ch.tai_khoan_web,
                         getpass.getpass(f"Mật khẩu web của {ch.tai_khoan_web}: "))
    print("Đã lưu vào Windows Credential Manager.")
    return 0


def lenh_xuat(ch: CH.CauHinh, muc: str, ngay) -> int:
    from obc_bot import obc
    from obc_bot.chay import LoiObc
    if muc not in ch.pattern:
        print(f"Cấu hình máy này không có mục {muc!r} ([pattern] {muc} = ...)")
        return 2
    try:
        p = obc.xuat(muc, ngay, ch.thu_muc_ra / f"{ngay:%Y-%m}", ch.pattern[muc])
    except LoiObc as e:
        print(f"LỖI OBC — bước '{e.buoc}': {e.loi}" + (f"\n  ảnh: {e.anh}" if e.anh else ""))
        return 1
    print(f"OK   {p}")
    return 0


def lenh_chay(ch: CH.CauHinh) -> int:
    import time
    from datetime import date
    from obc_bot import bao_cao, man_hinh, obc
    from obc_bot.chay import KetCuc, MoiTruong, chay
    mt = MoiTruong(man_hinh_khoa=man_hinh.dang_khoa, xuat=obc.xuat,
                   khoi_dong_lai_obc=obc.khoi_dong_lai, mat_khau=mat_khau_web,
                   thong_bao=bao_cao.thong_bao_windows, ngu=time.sleep, hoi=man_hinh.hoi)
    try:
        kc = chay(ch, KhachWeb(ch.web_url), mt)
    except Exception as e:                      # lưới cuối: luôn ra MỘT kết cục + báo
        kc = KetCuc("loi_obc", [f"Lỗi không lường trước: {e!r}"])
    tep = None
    try:
        tep = bao_cao.ghi(ch, kc, date.today())
    except OSError as e:
        print(f"KHÔNG GHI ĐƯỢC BÁO CÁO: {e}")
    if kc.can_bao or kc.loai == "xong":
        bao_cao.thong_bao_windows(f"OBC → web: {kc.loai}",
                                  (kc.chi_tiet[0] if kc.chi_tiet else "") + (f" — {tep}" if tep else ""))
    print(kc.loai)
    for d in kc.chi_tiet:
        print("  " + d)
    return 0 if kc.loai in ("xong", "bo_qua") else 1


def main(argv=None) -> int:
    for luong in (sys.stdout, sys.stderr):      # Task Scheduler chuyển hướng theo cp932
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="obc_bot")
    sub = p.add_subparsers(dest="lenh", required=True)
    s = sub.add_parser("do")
    s.add_argument("--ra", required=True, type=Path)
    s.add_argument("--tieu-de", default=".*奉行クラウド.*")
    s.add_argument("--sau", type=int, default=12)
    for ten in ("nap", "xuat", "chay", "luu-mat-khau"):
        s = sub.add_parser(ten)
        s.add_argument("--cau-hinh", required=True, type=Path)
        if ten == "nap":
            s.add_argument("files", nargs="+", type=Path)
        if ten == "xuat":
            s.add_argument("--muc", required=True, choices=["ban", "ton", "khach"])
            s.add_argument("--ngay", default=None, help="mặc định: hôm nay giờ Tokyo")
    a = p.parse_args(argv)
    if a.lenh == "do":
        from obc_bot.obc.do import do_cay
        a.ra.parent.mkdir(parents=True, exist_ok=True)
        a.ra.write_text(do_cay(a.tieu_de, a.sau), encoding="utf-8")
        print(f"Đã ghi {a.ra}")
        return 0
    try:
        ch = CH.doc(a.cau_hinh)
    except CH.CauHinhSai as e:
        print(f"CẤU HÌNH SAI: {e}")
        return 2
    if a.lenh == "nap":
        return lenh_nap(ch, a.files)
    if a.lenh == "xuat":
        from datetime import date, datetime
        from zoneinfo import ZoneInfo
        ngay = date.fromisoformat(a.ngay) if a.ngay else datetime.now(ZoneInfo("Asia/Tokyo")).date()
        return lenh_xuat(ch, a.muc, ngay)
    if a.lenh == "chay":
        return lenh_chay(ch)
    return lenh_luu_mat_khau(ch)


if __name__ == "__main__":
    sys.exit(main())
