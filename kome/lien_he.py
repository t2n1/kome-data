"""Đợt 7 — danh sách ưu tiên liên hệ + nhật ký tiếp xúc.

Hai nguồn, hai loại "hôm nay" — KHÔNG gộp:
- `mart.uu_tien_lien_he` (AI cần gọi) dựa trên mốc dữ liệu
  (`mart.moc_thoi_gian`), như mọi chỉ số khác.
- Việc TẠM ẨN khách vừa được liên hệ và ô "Hẹn gọi lại hôm nay" dựa trên
  ĐỒNG HỒ THẬT giờ Tokyo (`kome.tuoi_du_lieu.hom_nay_o_nhat`): hẹn gọi lại
  thứ Năm là thứ Năm ngoài đời, không phải "ngày bán mới nhất + n". Cùng ngoại
  lệ với ô tuổi dữ liệu (CLAUDE.md).

Ngân sách truy vấn của `/lien-he`: đúng 3 lượt hỏi (danh sách, hoạt động gần
đây, hẹn gọi lại) — có test đếm.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from kome.tuoi_du_lieu import MUI_GIO

# Ba kiểu tiếp xúc và ba mức kết quả — ĐÚNG từ vựng của gói thiết kế
# (Customer 360.dc.html: KIEU_TX, KQ_TX). CHECK của app.nhat_ky_tiep_xuc
# (migration 030) giữ cùng ba khoá; thêm một kiểu là sửa CẢ HAI chỗ.
KIEU = {"goi": ("📞", "Gọi điện"), "ghe": ("🚗", "Ghé thăm"), "chat": ("💬", "Chat / Email")}
KET_QUA = {"tot": ("Tích cực", "ok"), "binh": ("Bình thường", "nhat"),
           "xau": ("Cần theo dõi", "loi")}

# Ba lý do, theo thứ tự cột trên màn. Nhãn + mô tả + lớp màu (.vien.<lớp>).
LY_DO = {
    "lau_khong_mua": ("Lâu không mua", "Im lặng ≥ 4 lần nhịp mua riêng — đang mất khách", "loi"),
    "qua_han": ("Quá hạn mua lại", "Im lặng 2–4 lần nhịp mua riêng", "canh"),
    "sap_den_han": ("Sắp đến hạn", "Im lặng 1–2 lần nhịp — gọi trước khi khách trễ hẳn", "ok"),
}

# Không đặt ngày hẹn thì khách vừa liên hệ ẩn khỏi danh sách bấy nhiêu ngày.
# Ẩn mãi là mất khách khỏi tầm mắt; không ẩn là khách hiện lại y nguyên hôm
# sau như chưa ai gọi (đặc tả đợt 1 §2 — lý do nhật ký tồn tại).
AN_KHI_KHONG_HEN = 7

# Số thẻ mỗi cột trên màn tổng; bấm "xem cả cột" (?ly_do=) thì hiện hết.
THE_MOI_COT = 12

DO_DAI_NOI_DUNG = 2000


class LoiNhap(ValueError):
    """Dữ liệu biểu mẫu không ghi được — thông điệp đọc được bằng tiếng Việt."""


@dataclass
class LanTiepXuc:
    kieu: str
    ket_qua: str
    noi_dung: str
    thoi_diem: datetime
    hen_lai: date | None
    nguoi: str | None = None
    ma_khach: str | None = None
    ten_khach: str | None = None

    @property
    def icon(self) -> str:
        return KIEU.get(self.kieu, ("•", "Khác"))[0]

    @property
    def nhan_kieu(self) -> str:
        return KIEU.get(self.kieu, ("•", "Khác"))[1]

    @property
    def nhan_ket_qua(self) -> str:
        return KET_QUA.get(self.ket_qua, (self.ket_qua, "nhat"))[0]

    @property
    def mau_ket_qua(self) -> str:
        return KET_QUA.get(self.ket_qua, ("", "nhat"))[1]

    @property
    def ngay(self) -> date:
        """Ngày GIỜ NHẬT của lần tiếp xúc — CSDL lưu timestamptz (UTC)."""
        return self.thoi_diem.astimezone(MUI_GIO).date()


@dataclass
class The:
    """Một khách trên danh sách ưu tiên."""
    ma: str
    ten: str
    tinh: str | None
    dien_thoai: str | None
    phu_trach: str | None
    doanh_thu: int
    so_ngay_im_lang: int | None
    nhip_ngay: float | None
    ty_le: float | None
    ly_do: str
    cuoi: LanTiepXuc | None = None

    @property
    def nhan_ly_do(self) -> str:
        return LY_DO[self.ly_do][0]

    @property
    def mau(self) -> str:
        return LY_DO[self.ly_do][2]


@dataclass
class Cot:
    ly_do: str
    nhan: str
    mo_ta: str
    mau: str
    the: list[The]
    tong: int
    doanh_thu: int


@dataclass
class DanhSach:
    cot: list[Cot]
    da_lien_he: list[The]          # đang tạm ẩn — hiện ở khối riêng, không biến mất
    hom_nay: date
    ly_do: str | None = None       # đang xem trọn một cột
    dem: dict = field(default_factory=dict)

    @property
    def tong(self) -> int:
        return sum(c.tong for c in self.cot)


def dang_an(cuoi: LanTiepXuc | None, hom_nay: date) -> bool:
    """Khách vừa liên hệ thì tạm ẩn: tới ngày hẹn (nếu có), hoặc
    AN_KHI_KHONG_HEN ngày kể từ lần tiếp xúc. Ngày hẹn = hôm nay thì HIỆN —
    hôm nay chính là ngày phải gọi."""
    if cuoi is None:
        return False
    if cuoi.hen_lai is not None:
        return cuoi.hen_lai > hom_nay
    return cuoi.ngay > hom_nay - timedelta(days=AN_KHI_KHONG_HEN)


def _loc_sale(sale: str | None, cot: str) -> tuple[str, list]:
    return (f"AND {cot} = %s", [sale]) if sale else ("", [])


def danh_sach(conn, hom_nay: date, sale: str | None = None,
              ly_do: str | None = None) -> DanhSach:
    """MỘT lượt hỏi: mọi khách của `mart.uu_tien_lien_he` (lọc theo sale)
    kèm lần tiếp xúc MỚI NHẤT. Chia cột, ẩn, đếm làm bằng Python trên vài
    trăm dòng — rẻ hơn ba câu đếm riêng (mỗi câu dựng lại khach_360)."""
    if ly_do not in LY_DO:
        ly_do = None
    dk, ts = _loc_sale(sale, "u.salesperson_code")
    rows = conn.execute(
        f"""SELECT u.customer_code, u.ten, u.prefecture, u.phone,
                   coalesce(sp.ten, u.salesperson_code),
                   u.doanh_thu_thuan, u.so_ngay_im_lang, u.nhip_ngay, u.ty_le_im_lang,
                   u.ly_do, n.kieu, n.ket_qua, n.noi_dung, n.thoi_diem, n.hen_lai
            FROM mart.uu_tien_lien_he u
            LEFT JOIN core.dim_salesperson sp ON sp.salesperson_code = u.salesperson_code
            LEFT JOIN LATERAL (
                SELECT kieu, ket_qua, noi_dung, thoi_diem, hen_lai
                FROM app.nhat_ky_tiep_xuc x
                WHERE x.customer_code = u.customer_code
                ORDER BY x.thoi_diem DESC, x.id DESC LIMIT 1) n ON true
            WHERE true {dk}
            ORDER BY u.thu_tu, u.doanh_thu_thuan DESC NULLS LAST, u.customer_code""",
        ts).fetchall()
    theo: dict[str, list[The]] = {k: [] for k in LY_DO}
    an: list[The] = []
    for r in rows:
        cuoi = (LanTiepXuc(kieu=r[10], ket_qua=r[11], noi_dung=r[12],
                           thoi_diem=r[13], hen_lai=r[14]) if r[13] else None)
        t = The(ma=r[0], ten=r[1], tinh=r[2], dien_thoai=r[3], phu_trach=r[4],
                doanh_thu=int(r[5] or 0), so_ngay_im_lang=r[6],
                nhip_ngay=float(r[7]) if r[7] is not None else None,
                ty_le=float(r[8]) if r[8] is not None else None,
                ly_do=r[9], cuoi=cuoi)
        (an if dang_an(cuoi, hom_nay) else theo[t.ly_do]).append(t)
    cot = []
    for k, (nhan, mo_ta, mau) in LY_DO.items():
        ds = theo[k]
        cot.append(Cot(ly_do=k, nhan=nhan, mo_ta=mo_ta, mau=mau,
                       the=ds if ly_do == k else ds[:THE_MOI_COT], tong=len(ds),
                       doanh_thu=sum(t.doanh_thu for t in ds)))
    if ly_do:
        cot = [c for c in cot if c.ly_do == ly_do]
    return DanhSach(cot=cot, da_lien_he=an, hom_nay=hom_nay, ly_do=ly_do,
                    dem={k: len(v) for k, v in theo.items()})


_COT_LTX = """n.kieu, n.ket_qua, n.noi_dung, n.thoi_diem, n.hen_lai,
              coalesce(s.ten, nd.ten_dang_nhap), n.customer_code, c.customer_name"""

_TU_LTX = """FROM app.nhat_ky_tiep_xuc n
             LEFT JOIN core.dim_customer c
                    ON c.customer_code = n.customer_code AND c.is_current
             LEFT JOIN app.nguoi_dung nd ON nd.id = n.nguoi_dung_id
             LEFT JOIN core.dim_salesperson s ON s.salesperson_code = nd.salesperson_code"""


def _ltx(r) -> LanTiepXuc:
    return LanTiepXuc(kieu=r[0], ket_qua=r[1], noi_dung=r[2], thoi_diem=r[3],
                      hen_lai=r[4], nguoi=r[5], ma_khach=r[6], ten_khach=r[7])


def hoat_dong_gan_day(conn, sale: str | None = None, gioi_han: int = 12) -> list[LanTiepXuc]:
    """Khối "Hoạt động gần đây" (CRM.dc.html). Lọc theo KHÁCH CỦA sale (người
    phụ trách hiện tại trong OBC), không theo người bấm ghi — arubaito ghi hộ
    vẫn phải hiện ở danh sách của sale phụ trách khách đó."""
    dk, ts = _loc_sale(sale, "c.salesperson_code")
    return [_ltx(r) for r in conn.execute(
        f"""SELECT {_COT_LTX} {_TU_LTX} WHERE true {dk}
            ORDER BY n.thoi_diem DESC, n.id DESC LIMIT %s""", ts + [gioi_han]).fetchall()]


def hen_goi_lai(conn, hom_nay: date, sale: str | None = None) -> list[LanTiepXuc]:
    """Khối "Hẹn gọi lại hôm nay": lần tiếp xúc MỚI NHẤT của mỗi khách mà có
    ngày hẹn ≤ hôm nay. Chỉ lần mới nhất: gọi lại xong và ghi một dòng không
    hẹn thì lời hẹn cũ đã được trả, không được hiện mãi."""
    dk, ts = _loc_sale(sale, "c.salesperson_code")
    return [_ltx(r) for r in conn.execute(
        f"""SELECT {_COT_LTX}
            FROM (SELECT DISTINCT ON (customer_code) *
                  FROM app.nhat_ky_tiep_xuc
                  ORDER BY customer_code, thoi_diem DESC, id DESC) n
            LEFT JOIN core.dim_customer c
                   ON c.customer_code = n.customer_code AND c.is_current
            LEFT JOIN app.nguoi_dung nd ON nd.id = n.nguoi_dung_id
            LEFT JOIN core.dim_salesperson s ON s.salesperson_code = nd.salesperson_code
            WHERE n.hen_lai IS NOT NULL AND n.hen_lai <= %s {dk}
            ORDER BY n.hen_lai, n.thoi_diem""", [hom_nay] + ts).fetchall()]


def nhat_ky_khach(conn, ma: str, gioi_han: int = 30) -> list[LanTiepXuc]:
    """Khối "Nhật ký tiếp xúc" của hồ sơ khách — MỘT lượt hỏi."""
    return [_ltx(r) for r in conn.execute(
        f"""SELECT {_COT_LTX} {_TU_LTX} WHERE n.customer_code = %s
            ORDER BY n.thoi_diem DESC, n.id DESC LIMIT %s""", (ma, gioi_han)).fetchall()]


def doc_bieu_mau(kieu: str, ket_qua: str, noi_dung: str, hen_lai: str) -> tuple:
    """Kiểm biểu mẫu TRƯỚC khi chạm CSDL — lỗi trả về một câu đọc được, không
    phải một CheckViolation tiếng Anh."""
    if kieu not in KIEU:
        raise LoiNhap("Chọn kiểu tiếp xúc: gọi điện, ghé thăm hoặc chat.")
    if ket_qua not in KET_QUA:
        raise LoiNhap("Chọn kết quả: tích cực, bình thường hoặc cần theo dõi.")
    noi_dung = (noi_dung or "").strip()
    if not noi_dung:
        raise LoiNhap("Ghi lại nội dung trao đổi — một dòng trống không nói được gì cho người sau.")
    if len(noi_dung) > DO_DAI_NOI_DUNG:
        raise LoiNhap(f"Nội dung dài quá {DO_DAI_NOI_DUNG} ký tự.")
    hen = None
    if hen_lai:
        try:
            hen = date.fromisoformat(hen_lai)
        except ValueError:
            raise LoiNhap("Ngày hẹn lại không đọc được.") from None
    return kieu, ket_qua, noi_dung, hen


def ghi(conn, ma: str, nguoi_id: int | None, kieu: str, ket_qua: str,
        noi_dung: str, hen_lai: str = "") -> None:
    """Thêm MỘT dòng nhật ký. Không commit — người gọi quyết định giao dịch."""
    kieu, ket_qua, noi_dung, hen = doc_bieu_mau(kieu, ket_qua, noi_dung, hen_lai)
    co = conn.execute(
        "SELECT 1 FROM core.dim_customer WHERE customer_code = %s AND is_current",
        (ma,)).fetchone()
    if co is None:
        raise LoiNhap(f"Không có khách mã {ma}.")
    conn.execute(
        """INSERT INTO app.nhat_ky_tiep_xuc
             (customer_code, nguoi_dung_id, kieu, ket_qua, noi_dung, hen_lai)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (ma, nguoi_id, kieu, ket_qua, noi_dung, hen))
