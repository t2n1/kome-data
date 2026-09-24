"""Khoảng xem — chỗ DUY NHẤT hiểu "đang xem tháng / kỳ / khoảng nào".

Đặc tả: docs/superpowers/specs/2026-09-24-khoang-xem-thang-design.md §1.

Ba dạng, đọc từ URL:
  * Tháng  `?thang=YYYY-MM` — không tham số nào = tháng của ngày bán mới nhất
    (`mart.moc_thoi_gian`). Dải = mùng 1 → min(cuối tháng, hôm nay).
  * Kỳ     `?ky=<company_fy>` — 1/8 → 31/7, cắt theo dải dữ liệu.
  * Khoảng `?tu=YYYY-MM-DD&den=YYYY-MM-DD` — cắt theo dải dữ liệu.

Mỗi khoảng kèm các DẢI SO SÁNH, `so_sanh[0]` luôn là năm trước (so "chính",
cùng nếp "cùng kỳ" của cả dự án), `so_sanh[1]` là tháng trước / khoảng liền
trước. Giao diện KHÔNG tự tính ngày so sánh — chỉ in `mo_ta`.

Luật so sánh (có test canh, tests/test_khoang_xem.py):
  * Tháng dở dang: năm trước = cùng dải ngày trừ một năm (29/2 → 28/2, đúng
    phép `- interval '1 year'` của `mart.thang_den_hom_nay`); tháng trước =
    mùng 1 → min(ngày cuối dải, cuối tháng trước). Tháng TRỌN so trọn tháng.
  * Kỳ: so năm trước chỉ trên phần CẢ HAI phía có dữ liệu — cùng tập tháng đối
    chiếu với `mart.ky_cung_ky` (dữ liệu bắt đầu giữa chừng).
  * Khoảng: năm trước + khoảng liền trước dài bằng nó.
  * Một phép so chỉ `co` khi tháng chứa ngày đầu của nó đã có dữ liệu (cùng luật
    EXISTS-trong-tháng của `mart.thang_den_hom_nay`). Không có thì màn nói "không
    có dữ liệu để so", không bao giờ so với một dải thiếu dữ liệu mà im lặng.

`doc_tham_so` chỉ kiểm CÚ PHÁP (không hỏi CSDL) — khoá ảnh chụp dựng từ nó, nên
"trúng ảnh chụp: một lượt hỏi" vẫn đúng. `giai` cần dải dữ liệu (`pham_vi`, một
lượt hỏi) và chạy BÊN TRONG hàm tính của ảnh chụp.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta


class LoiKhoang(ValueError):
    """Tham số khoảng xem sai — API trả 400 kèm câu này."""


_THANG = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
_NGAY = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")


@dataclass(frozen=True)
class ThamSo:
    thang: str | None = None
    ky: int | None = None
    tu: date | None = None
    den: date | None = None

    @property
    def loai(self) -> str:
        if self.thang:
            return "thang"
        if self.ky is not None:
            return "ky"
        if self.tu is not None:
            return "khoang"
        return "mac_dinh"

    def khoa(self) -> dict[str, str]:
        """Tham số đã chuẩn hoá — phần khoảng của khoá ảnh chụp."""
        if self.thang:
            return {"thang": self.thang}
        if self.ky is not None:
            return {"ky": str(self.ky)}
        if self.tu is not None:
            return {"tu": self.tu.isoformat(), "den": self.den.isoformat()}
        return {}


def _doc_ngay(s: str, ten: str) -> date:
    m = _NGAY.match(s)
    try:
        if not m:
            raise ValueError
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        raise LoiKhoang(f"Ngày '{ten}' không đọc được — dạng YYYY-MM-DD.") from None


def doc_tham_so(thang: str | None = "", ky: str | int | None = "",
                tu: str | None = "", den: str | None = "") -> ThamSo:
    thang = (thang or "").strip()
    ky = str(ky if ky is not None else "").strip()
    tu, den = (tu or "").strip(), (den or "").strip()
    so_dang = sum(bool(x) for x in (thang, ky, tu or den))
    if so_dang > 1:
        raise LoiKhoang("Chỉ chọn một: tháng, kỳ hoặc khoảng ngày.")
    if thang:
        if not _THANG.match(thang):
            raise LoiKhoang("Tháng phải có dạng YYYY-MM.")
        return ThamSo(thang=thang)
    if ky:
        if not ky.isdigit():
            raise LoiKhoang("Kỳ phải là năm kết thúc kỳ (vd 2026).")
        return ThamSo(ky=int(ky))
    if tu or den:
        if not (tu and den):
            raise LoiKhoang("Khoảng ngày cần cả 'tu' lẫn 'den'.")
        a, b = _doc_ngay(tu, "tu"), _doc_ngay(den, "den")
        if b < a:
            raise LoiKhoang("Ngày 'den' phải sau ngày 'tu'.")
        return ThamSo(tu=a, den=b)
    return ThamSo()


@dataclass(frozen=True)
class KyDl:
    """Một kỳ kế toán, dải đã cắt theo dữ liệu có trong kho."""
    company_fy: int
    so_ky: int
    tu: date
    den: date


@dataclass(frozen=True)
class PhamVi:
    ngay_dau: date
    hom_nay: date
    ky: tuple[KyDl, ...]

    def ky_chua(self, d: date) -> KyDl | None:
        return next((k for k in self.ky if k.tu <= d <= k.den), None)


def pham_vi(conn) -> PhamVi | None:
    """Dải dữ liệu bán hàng + các kỳ của nó. Một lượt hỏi. None = kho rỗng.
    Kỳ lấy từ `core.dim_date` (company_fy / company_fy_no) — không tự tính lại
    quy tắc 1/8 → 31/7 ở đây."""
    rows = conn.execute(
        """WITH r AS (SELECT (SELECT min(sales_date) FROM core.fact_sales_line) AS dau,
                             (SELECT hom_nay FROM mart.moc_thoi_gian) AS cuoi)
           SELECT r.dau, r.cuoi, d.company_fy, min(d.company_fy_no),
                  min(d.date_key), max(d.date_key)
             FROM r JOIN core.dim_date d ON d.date_key BETWEEN r.dau AND r.cuoi
            GROUP BY r.dau, r.cuoi, d.company_fy
            ORDER BY d.company_fy""").fetchall()
    if not rows:
        return None
    return PhamVi(ngay_dau=rows[0][0], hom_nay=rows[0][1],
                  ky=tuple(KyDl(r[2], r[3], r[4], r[5]) for r in rows))


@dataclass(frozen=True)
class SoSanh:
    """Một phép so. `tu_nay`/`den_nay` = phần của khoảng đang xem được đem so
    (khác `tu`/`den` của khoảng chỉ ở dạng Kỳ, khi dữ liệu bắt đầu giữa chừng)."""
    ma: str          # 'nam_truoc' | 'thang_truoc' | 'lien_truoc'
    nhan: str
    tu: date
    den: date
    tu_nay: date
    den_nay: date
    co: bool


@dataclass(frozen=True)
class KhoangXem:
    loai: str                    # 'thang' | 'ky' | 'khoang'
    tu: date
    den: date
    nhan: str
    mo_ta: str
    thang: str | None            # 'YYYY-MM' ở dạng Tháng
    company_fy: int | None       # kỳ chứa ngày cuối khoảng
    so_ky: int | None
    mac_dinh: bool
    tron_thang: bool
    so_sanh: tuple[SoSanh, ...]
    ghi_chu: tuple[str, ...]

    @property
    def so_ngay(self) -> int:
        return (self.den - self.tu).days + 1


# ---- ngày ------------------------------------------------------------------

def _cuoi_thang(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def _tru_nam(d: date) -> date:
    """d − 1 năm; 29/2 → 28/2 (đúng `- interval '1 year'` của Postgres)."""
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return d.replace(year=d.year - 1, day=28)


def _dau_thang(d: date) -> date:
    return d.replace(day=1)


def _n(d: date, nam: bool = True) -> str:
    return f"{d.day}/{d.month}/{d.year}" if nam else f"{d.day}/{d.month}"


def _dai(a: date, b: date) -> str:
    return f"{_n(a, a.year != b.year)} → {_n(b)}"


def _so(ma: str, nhan: str, tu: date, den: date, tu_nay: date, den_nay: date,
        pv: PhamVi) -> SoSanh:
    co = _dau_thang(tu) >= _dau_thang(pv.ngay_dau) and tu_nay <= den_nay
    return SoSanh(ma, nhan, tu, den, tu_nay, den_nay, co)


def giai(pv: PhamVi, ts: ThamSo) -> KhoangXem:
    ghi_chu: list[str] = []
    thang = None
    tron = False
    if ts.loai in ("mac_dinh", "thang"):
        if ts.thang:
            y, m = int(ts.thang[:4]), int(ts.thang[5:])
        else:
            y, m = pv.hom_nay.year, pv.hom_nay.month
        tu = date(y, m, 1)
        if tu < _dau_thang(pv.ngay_dau) or tu > pv.hom_nay:
            raise LoiKhoang(f"Tháng {m}/{y} không có trong kho dữ liệu "
                            f"({_n(pv.ngay_dau)} → {_n(pv.hom_nay)}).")
        cuoi = _cuoi_thang(y, m)
        den = min(cuoi, pv.hom_nay)
        tron = den == cuoi
        thang = f"{y:04d}-{m:02d}"
        loai, nhan = "thang", f"Tháng {m}/{y}"
        ty, tm = (y, m - 1) if m > 1 else (y - 1, 12)
        cuoi_tt = _cuoi_thang(ty, tm)
        tu_nt = date(y - 1, m, 1)
        den_nt = _cuoi_thang(y - 1, m) if tron else _tru_nam(den)
        den_tt = cuoi_tt if tron else date(ty, tm, min(den.day, cuoi_tt.day))
        so_sanh = (_so("nam_truoc", "cùng tháng năm trước", tu_nt, den_nt, tu, den, pv),
                   _so("thang_truoc", "tháng trước", date(ty, tm, 1), den_tt, tu, den, pv))
        if tu < pv.ngay_dau:
            ghi_chu.append(f"Dữ liệu bắt đầu {_n(pv.ngay_dau)} — tháng này chưa đủ tháng.")
    elif ts.loai == "ky":
        k = next((x for x in pv.ky if x.company_fy == ts.ky), None)
        if k is None:
            raise LoiKhoang(f"Kỳ kết thúc 7/{ts.ky} không có trong kho dữ liệu.")
        tu, den = k.tu, k.den
        loai = "ky"
        nhan = f"Kỳ {k.so_ky} (8/{k.company_fy - 1} → 7/{k.company_fy})"
        tu_ss, tu_nay = _tru_nam(tu), tu
        if _dau_thang(tu_ss) < _dau_thang(pv.ngay_dau):
            tu_ss = _dau_thang(pv.ngay_dau)
            tu_nay = date(tu_ss.year + 1, tu_ss.month, 1)
        so_sanh = (_so("nam_truoc", "cùng kỳ năm trước", tu_ss, _tru_nam(den), tu_nay, den, pv),)
        if tu > date(k.company_fy - 1, 8, 1) or den < date(k.company_fy, 7, 31):
            ghi_chu.append(f"Kỳ này mới có dữ liệu {_dai(tu, den)}.")
    else:
        tu, den = max(ts.tu, pv.ngay_dau), min(ts.den, pv.hom_nay)
        if tu > den:
            raise LoiKhoang(f"Khoảng ngày nằm ngoài kho dữ liệu "
                            f"({_n(pv.ngay_dau)} → {_n(pv.hom_nay)}).")
        if (tu, den) != (ts.tu, ts.den):
            ghi_chu.append(f"Đã cắt theo dữ liệu có trong kho ({_n(pv.ngay_dau)} → {_n(pv.hom_nay)}).")
        loai, nhan = "khoang", _dai(tu, den)
        so = (den - tu).days
        so_sanh = (_so("nam_truoc", "cùng khoảng năm trước", _tru_nam(tu), _tru_nam(den), tu, den, pv),
                   _so("lien_truoc", "khoảng liền trước", tu - timedelta(days=so + 1),
                       tu - timedelta(days=1), tu, den, pv))

    ky = pv.ky_chua(den)
    phan = []
    for s in so_sanh:
        if not s.co:
            phan.append(f"{s.nhan}: không có dữ liệu để so")
        elif (s.tu_nay, s.den_nay) != (tu, den):
            phan.append(f"{_dai(s.tu_nay, s.den_nay)} với {_dai(s.tu, s.den)}")
        else:
            phan.append(_dai(s.tu, s.den))
    mo_ta = f"{nhan} · {_dai(tu, den)} · so " + " và ".join(phan)
    return KhoangXem(loai=loai, tu=tu, den=den, nhan=nhan, mo_ta=mo_ta, thang=thang,
                     company_fy=ky.company_fy if ky else None, so_ky=ky.so_ky if ky else None,
                     mac_dinh=ts.loai == "mac_dinh", tron_thang=tron,
                     so_sanh=so_sanh, ghi_chu=tuple(ghi_chu))


def giai_conn(conn, ts: ThamSo) -> KhoangXem | None:
    """Giải khoảng trên dải dữ liệu thật (+1 lượt hỏi). None = kho rỗng."""
    pv = pham_vi(conn)
    return None if pv is None else giai(pv, ts)
