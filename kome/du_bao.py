"""Đợt 8 — Dự báo doanh thu (màn `Dự báo.dc.html` của gói thiết kế).

Ba cách tính, cả ba ĐƠN GIẢN và GIẢI THÍCH ĐƯỢC bằng một câu (R2 của đặc tả
nền: "không ma thuật") — không mô hình thống kê, không tham số ẩn:

1. **Chốt tháng** = đã bán + (đã bán ÷ số ngày làm việc đã qua) × số ngày làm
   việc còn lại. Khoảng thấp–cao KHÔNG bịa hệ số: nó là sai số nhỏ nhất/lớn
   nhất của CHÍNH cách tính này khi áp lên các tháng trước, ở cùng số ngày làm
   việc đã qua (khối "Dự báo đã chuẩn tới đâu" hiện đúng các tháng đó).
2. **12 tháng tới** = doanh thu cùng tháng năm trước × hệ số tăng trưởng. Hệ số
   cơ sở là TỶ SỐ CỦA CÁC TỔNG trên các tháng đối chiếu được (bất biến tỷ số
   của CLAUDE.md), không phải trung bình các tỷ số; kịch bản thận trọng/lạc
   quan dùng tỷ số tháng thấp nhất/cao nhất trong chính các tháng đó.
3. **Đơn kỳ vọng 14 ngày** = khách mua đều có ngày dự kiến mua lại (lần cuối +
   nhịp mua riêng, `mart.khach_360`) rơi vào 14 ngày tới.

"Ngày làm việc" đọc từ `mart.lich_kinh_doanh` (031) — định nghĩa duy nhất.
Mốc "hôm nay" là `mart.moc_thoi_gian.hom_nay` như mọi chỉ số.
Toàn màn: đúng 3 lượt hỏi (lịch + bán theo ngày · theo người phụ trách ·
khách) — có test đếm. Dự báo là toàn công ty, KHÔNG lọc theo người đăng nhập
(cùng nếp các khối số tổng của `/`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Dự báo mở tháng sau ít nhất bấy nhiêu tháng đối chiếu cùng kỳ; khối "đã
# chuẩn tới đâu" hiện bấy nhiêu tháng gần nhất.
SO_THANG_KIEM = 6
# Khi tháng hiện tại đã đủ ngày (không còn gì để dự báo), khối "đã chuẩn tới
# đâu" kiểm cách tính ở mốc GIỮA tháng này thay vì ở mốc "hôm nay".
MOC_KIEM_GIUA_THANG = 10

KICH_BAN = {"thap": "Thận trọng", "cs": "Cơ sở", "cao": "Lạc quan"}


@dataclass
class Ngay:
    ngay: date
    la_kd: bool
    dt: int | None          # None = sau mốc hôm nay (chưa có dữ liệu)


def thang(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def cong_thang(th: str, n: int) -> str:
    y, m = int(th[:4]), int(th[5:])
    k = y * 12 + (m - 1) + n
    return f"{k // 12:04d}-{k % 12 + 1:02d}"


def doc_lich(conn) -> tuple[list[Ngay], date | None]:
    """MỘT lượt hỏi: mọi ngày từ ngày bán đầu tiên tới HẾT tháng của mốc hôm
    nay, kèm cờ ngày làm việc và doanh thu (NULL sau mốc). `mart.ban_theo_ngay`
    vào CTE MATERIALIZED vì câu lệnh tham chiếu nó hai lần (bất biến CTE-trùng)."""
    rows = conn.execute(
        """WITH b AS MATERIALIZED (SELECT ngay, doanh_thu_thuan FROM mart.ban_theo_ngay),
                m AS (SELECT hom_nay FROM mart.moc_thoi_gian)
           SELECT l.ngay, l.la_ngay_kd, b.doanh_thu_thuan, m.hom_nay
           FROM mart.lich_kinh_doanh l
           CROSS JOIN m
           LEFT JOIN b ON b.ngay = l.ngay
           WHERE l.ngay >= (SELECT min(ngay) FROM b)
             AND l.ngay <= (date_trunc('month', m.hom_nay) + interval '1 month - 1 day')::date
           ORDER BY l.ngay""").fetchall()
    if not rows:
        return [], None
    hom_nay = rows[0][3]
    return [Ngay(r[0], bool(r[1]), int(r[2]) if r[2] is not None and r[0] <= hom_nay else None)
            for r in rows], hom_nay


# ---- 1. Chốt tháng ---------------------------------------------------------

def _theo_thang(ds: list[Ngay]) -> dict[str, list[Ngay]]:
    ra: dict[str, list[Ngay]] = {}
    for n in ds:
        ra.setdefault(thang(n.ngay), []).append(n)
    return ra


def _day_du(ngay_thang: list[Ngay], tu: date) -> bool:
    """Tháng có dữ liệu đủ: mọi ngày đã qua mốc (không còn dt None) và kho
    không bắt đầu GIỮA tháng này. Dãy ngày bắt đầu đúng từ ngày bán đầu tiên,
    nên những ngày trước đó KHÔNG có trong `ngay_thang` — phải xét lịch: nếu
    giữa mùng 1 và ngày bán đầu tiên có một ngày thường (thứ Hai–Sáu) thì
    tháng đó thiếu. (Dùng thứ trong tuần chứ không `la_kd` vì chính các ngày
    đó không có dòng nào để đọc cờ.)"""
    if any(n.dt is None for n in ngay_thang):
        return False
    dau = ngay_thang[0].ngay.replace(day=1)
    if dau < tu <= ngay_thang[-1].ngay:
        d = dau
        while d < tu:
            if d.weekday() < 5:
                return False
            d = date.fromordinal(d.toordinal() + 1)
    return True


def _luy_ke_toi(ngay_thang: list[Ngay], e: int) -> tuple[int, int] | None:
    """(doanh thu luỹ kế tới HẾT ngày làm việc thứ e, số ngày làm việc cả tháng)."""
    n = sum(1 for x in ngay_thang if x.la_kd)
    dem = tong = 0
    for x in ngay_thang:
        tong += x.dt or 0
        if x.la_kd:
            dem += 1
            if dem == e:
                return tong, n
    return None


def du_bao_chot(S: int, e: int, n: int) -> float:
    """Công thức duy nhất của khối chốt tháng: đã bán + nhịp × ngày còn lại."""
    return S + (S / e) * (n - e) if e > 0 else float(S)


@dataclass
class Kiem:
    thang: str
    du_bao: int
    thuc_te: int

    @property
    def lech(self) -> float | None:
        """Lệch DƯƠNG = dự báo cao hơn thực tế (đúng quy ước của gói thiết kế)."""
        return self.du_bao / self.thuc_te - 1 if self.thuc_te > 0 else None


@dataclass
class ChotThang:
    thang: str
    hom_nay: date
    da_ban: int
    e: int                       # ngày làm việc đã qua
    n: int                       # ngày làm việc cả tháng
    co_so: int
    thap: int | None             # None = chưa đủ tháng cũ để tính khoảng
    cao: int | None
    ngay: list[Ngay]
    kiem: list[Kiem]
    moc_kiem: int                # kiểm ở ngày làm việc thứ mấy
    ngan_sach: int | None = None

    @property
    def xong(self) -> bool:
        return self.e >= self.n

    @property
    def so_ngan_sach(self) -> int | None:
        return self.co_so - self.ngan_sach if self.ngan_sach else None


def chot_thang(ds: list[Ngay], hom_nay: date, ngan_sach: int | None = None) -> ChotThang | None:
    if not ds or hom_nay is None:
        return None
    tt = _theo_thang(ds)
    th = thang(hom_nay)
    nay = tt.get(th, [])
    S = sum(x.dt or 0 for x in nay)
    e = sum(1 for x in nay if x.la_kd and x.ngay <= hom_nay)
    n = sum(1 for x in nay if x.la_kd)
    F = du_bao_chot(S, e, n)

    tu = ds[0].ngay
    cu = [k for k in sorted(tt) if k < th and _day_du(tt[k], tu)]
    # Hệ số sai số của phần CỘNG THÊM, ở cùng số ngày làm việc đã qua.
    q = []
    if 0 < e < n:
        for k in cu:
            lk = _luy_ke_toi(tt[k], e)
            if lk is None:
                continue
            s_p, n_p = lk
            A = sum(x.dt or 0 for x in tt[k])
            them = (s_p / e) * (n_p - e)
            if them > 0:
                q.append((A - s_p) / them)
    them_nay = F - S
    thap = cao = None
    if e >= n:
        thap = cao = S
    elif len(q) >= 3:
        thap, cao = round(S + them_nay * min(q)), round(S + them_nay * max(q))

    moc = e if 0 < e < n else MOC_KIEM_GIUA_THANG
    kiem = []
    for k in cu[-SO_THANG_KIEM:]:
        lk = _luy_ke_toi(tt[k], moc)
        if lk is None:
            continue
        s_p, n_p = lk
        kiem.append(Kiem(k, round(du_bao_chot(s_p, moc, n_p)),
                         sum(x.dt or 0 for x in tt[k])))
    return ChotThang(thang=th, hom_nay=hom_nay, da_ban=S, e=e, n=n, co_so=round(F),
                     thap=thap, cao=cao, ngay=nay, kiem=kiem, moc_kiem=moc,
                     ngan_sach=ngan_sach)


# ---- 2. 12 tháng tới -------------------------------------------------------

@dataclass
class ThangDuBao:
    thang: str
    co_so: int
    thap: int
    cao: int
    cung_ky: int

    def theo(self, kb: str) -> int:
        return {"thap": self.thap, "cao": self.cao}.get(kb, self.co_so)


@dataclass
class MuoiHaiThang:
    lich_su: list[tuple[str, int]]          # 12 tháng đủ gần nhất
    du_bao: list[ThangDuBao]
    he_so: float | None                     # tỷ số của các tổng
    he_so_thap: float | None
    he_so_cao: float | None
    doi_chieu: list[str] = field(default_factory=list)   # các tháng dùng để tính hệ số

    def tong(self, kb: str) -> int:
        return sum(t.theo(kb) for t in self.du_bao)

    @property
    def tong_cung_ky(self) -> int:
        """Tổng CÙNG CÁC THÁNG ĐÓ năm trước — mẫu số đúng của "so với năm
        trước". So với 12 tháng đã qua là so hai khoảng khác độ dài mỗi khi có
        tháng không dự báo được (tháng gốc năm trước chưa đủ ngày)."""
        return sum(t.cung_ky for t in self.du_bao)

    @property
    def tong_12_qua(self) -> int:
        return sum(v for _, v in self.lich_su)


def muoi_hai_thang(ds: list[Ngay], hom_nay: date) -> MuoiHaiThang:
    tt = _theo_thang(ds) if ds else {}
    tu = ds[0].ngay if ds else None
    A = {k: sum(x.dt or 0 for x in v) for k, v in tt.items() if tu and _day_du(v, tu)}
    ky = sorted(A)
    lich_su = [(k, A[k]) for k in ky[-12:]]
    doi = [k for k in ky if cong_thang(k, -12) in A][-12:]
    if not doi or sum(A[cong_thang(k, -12)] for k in doi) <= 0:
        return MuoiHaiThang(lich_su, [], None, None, None, doi)
    g = sum(A[k] for k in doi) / sum(A[cong_thang(k, -12)] for k in doi)
    r = [A[k] / A[cong_thang(k, -12)] for k in doi if A[cong_thang(k, -12)] > 0]
    g_thap, g_cao = min(r), max(r)
    dau = cong_thang(thang(hom_nay), 1)
    du_bao = []
    for i in range(12):
        m = cong_thang(dau, i)
        goc = A.get(cong_thang(m, -12))
        if goc is None:
            continue
        du_bao.append(ThangDuBao(m, round(goc * g), round(goc * g_thap), round(goc * g_cao), goc))
    return MuoiHaiThang(lich_su, du_bao, g, g_thap, g_cao, doi)


# ---- Theo người phụ trách ---------------------------------------------------

@dataclass
class DuBaoNguoi:
    ma: str
    ten: str | None
    da_ban: int
    co_so: int
    ngan_sach: int | None

    @property
    def tien_do(self) -> float | None:
        return self.co_so / self.ngan_sach if self.ngan_sach else None


def theo_nguoi(conn, th: str) -> list[DuBaoNguoi]:
    """Một lượt hỏi: `mart.tien_do_ngan_sach` của tháng đang xét (FULL JOIN
    chỉ tiêu ↔ thực tế — người có chỉ tiêu mà bán 0 đồng vẫn có dòng)."""
    ra = []
    for ma, ten, tt, ns, kd, qua in conn.execute(
            """SELECT t.salesperson_code, s.ten, t.thuc_te, t.muc_tieu, t.ngay_kd, t.ngay_kd_da_qua
               FROM mart.tien_do_ngan_sach t
               LEFT JOIN core.dim_salesperson s ON s.salesperson_code = t.salesperson_code
               WHERE t.thang = %s
               ORDER BY t.thuc_te DESC NULLS LAST, t.salesperson_code""", (th,)).fetchall():
        tt = int(tt or 0)
        ra.append(DuBaoNguoi(ma=ma, ten=ten, da_ban=tt,
                             co_so=round(du_bao_chot(tt, int(qua or 0), int(kd or 0))),
                             ngan_sach=int(ns) if ns is not None else None))
    return ra


# ---- 3 + 4. Khách: đơn kỳ vọng + nguy cơ ngừng mua --------------------------

@dataclass
class DonKyVong:
    ma: str
    ten: str
    du_kien: date
    gia_tri: int
    dung_nhip: int
    so_khoang: int

    @property
    def do_deu(self) -> float | None:
        return self.dung_nhip / self.so_khoang if self.so_khoang else None


@dataclass
class NguyCo:
    ma: str
    ten: str
    so_ngay_im_lang: int
    ty_le: float
    doanh_thu: int
    trang_thai: str


@dataclass
class Khach:
    ky_vong: list[DonKyVong]
    so_ky_vong: int
    tong_ky_vong: int
    nguy_co: list[NguyCo]
    so_nguy_co: int
    tien_nguy_co: int


def khach(conn, gioi_han_kv: int = 10, gioi_han_rr: int = 8) -> Khach:
    """MỘT lượt hỏi: `mart.khach_360` vật hoá ĐÚNG MỘT LẦN (CTE MATERIALIZED
    tường minh — view đắt nhất của mart, ~1,2 s trên CSDL thật), hai nhánh đọc
    từ đó.

    "Đúng nhịp" của một khoảng cách mua = nằm trong [0,5×; 1,5×] nhịp mua riêng
    — trả lời "khách này mua ĐỀU tới mức nào", hiện dạng "x/y lần" chứ không
    thành một phần trăm "chắc chắn" (gói thiết kế ghi "88% chắc chắn" — một
    con số ta không có cách nào đo)."""
    rows = conn.execute(
        """WITH k AS MATERIALIZED (
               SELECT customer_code, ten, doanh_thu_thuan, gia_tri_tb_moi_lan, lan_cuoi,
                      nhip_ngay, so_ngay_im_lang, ty_le_im_lang, trang_thai
               FROM mart.khach_360
               WHERE trang_thai IN ('binh_thuong', 'canh_bao', 'da_roi_bo')),
           kv AS (
               SELECT k.*, k.lan_cuoi + round(k.nhip_ngay)::int AS du_kien,
                      count(*) OVER () AS so, sum(k.gia_tri_tb_moi_lan) OVER () AS tong
               FROM k CROSS JOIN mart.moc_thoi_gian m
               WHERE k.trang_thai = 'binh_thuong'
                 AND k.lan_cuoi + round(k.nhip_ngay)::int BETWEEN m.hom_nay + 1 AND m.hom_nay + 14),
           deu AS (
               SELECT c.customer_code,
                      count(*) FILTER (WHERE c.so_ngay_cach BETWEEN kv.nhip_ngay * 0.5
                                                            AND kv.nhip_ngay * 1.5) AS dung,
                      count(*) AS tong
               FROM mart.khoang_cach_mua c JOIN kv USING (customer_code)
               WHERE c.so_ngay_cach IS NOT NULL
               GROUP BY c.customer_code),
           rr AS (
               SELECT k.*, count(*) OVER () AS so, sum(k.doanh_thu_thuan) OVER () AS tong
               FROM k WHERE k.trang_thai IN ('canh_bao', 'da_roi_bo'))
           (SELECT 'kv', kv.customer_code, kv.ten, kv.du_kien, kv.gia_tri_tb_moi_lan,
                   coalesce(d.dung, 0), coalesce(d.tong, 0), NULL::numeric, NULL::int,
                   NULL::text, kv.so, kv.tong
            FROM kv LEFT JOIN deu d USING (customer_code)
            ORDER BY kv.du_kien, kv.gia_tri_tb_moi_lan DESC, kv.customer_code LIMIT %s)
           UNION ALL
           (SELECT 'rr', customer_code, ten, NULL, doanh_thu_thuan, NULL, NULL,
                   ty_le_im_lang, so_ngay_im_lang, trang_thai, so, tong
            FROM rr ORDER BY doanh_thu_thuan DESC NULLS LAST, customer_code LIMIT %s)""",
        (gioi_han_kv, gioi_han_rr)).fetchall()
    kv = [r for r in rows if r[0] == "kv"]
    rr = [r for r in rows if r[0] == "rr"]
    return Khach(
        ky_vong=[DonKyVong(r[1], r[2], r[3], int(r[4] or 0), int(r[5]), int(r[6])) for r in kv],
        so_ky_vong=int(kv[0][10]) if kv else 0,
        tong_ky_vong=int(kv[0][11] or 0) if kv else 0,
        nguy_co=[NguyCo(r[1], r[2], int(r[8] or 0), float(r[7] or 0), int(r[4] or 0), r[9])
                 for r in rr],
        so_nguy_co=int(rr[0][10]) if rr else 0,
        tien_nguy_co=int(rr[0][11] or 0) if rr else 0)


# ---- Gộp màn ---------------------------------------------------------------

@dataclass
class DuBao:
    chot: ChotThang | None
    nam: MuoiHaiThang
    nguoi: list[DuBaoNguoi]
    kh: Khach


def du_bao(conn) -> DuBao | None:
    """Cả màn trong ĐÚNG 3 lượt hỏi. None khi kho chưa có dòng bán nào."""
    ds, hom_nay = doc_lich(conn)
    if hom_nay is None:
        return None
    nguoi = theo_nguoi(conn, thang(hom_nay))
    ns = [x.ngan_sach for x in nguoi if x.ngan_sach is not None]
    return DuBao(chot=chot_thang(ds, hom_nay, sum(ns) if ns else None),
                 nam=muoi_hai_thang(ds, hom_nay), nguoi=nguoi, kh=khach(conn))
