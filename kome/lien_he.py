"""Đợt 7 — danh sách ưu tiên liên hệ + nhật ký tiếp xúc.

Hai nguồn, hai loại "hôm nay" — KHÔNG gộp:
- `mart.uu_tien_lien_he` (AI cần gọi) dựa trên mốc dữ liệu
  (`mart.moc_thoi_gian`), như mọi chỉ số khác.
- Việc TẠM ẨN khách vừa được liên hệ và ô "Hẹn gọi lại hôm nay" dựa trên
  ĐỒNG HỒ THẬT giờ Tokyo (`kome.tuoi_du_lieu.hom_nay_o_nhat`): hẹn gọi lại
  thứ Năm là thứ Năm ngoài đời, không phải "ngày bán mới nhất + n". Cùng ngoại
  lệ với ô tuổi dữ liệu (CLAUDE.md).

Cột thứ tư (036) nhìn theo THÁNG: khách mua đều mà tháng này chưa có đơn
(`kome.khach_thang`) — đi chung câu danh sách, không thêm lượt hỏi.

Ngân sách truy vấn của `/lien-he`: đúng 4 lượt hỏi (danh sách, hoạt động gần
đây, hẹn gọi lại, gợi ý "Nên chào" + danh sách người phụ trách) — có test đếm.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from kome import doi_thu as DT
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
    # Cột thứ tư (036) — nhìn theo THÁNG, không theo nhịp. Nguồn DUY NHẤT:
    # mart.khach_thang_nay.nhan = 'tre' (kome.khach_thang). Khách đã ở ba
    # cột trên thì không lặp lại ở đây (đếm vào Cot.trung).
    "thang_nay_chua_mua": ("Mua đều, tháng này chưa",
                           "Mua ≥ 2/3 tháng trước, mọi khi đến ngày này đã có đơn — tháng này chưa", "canh"),
}
# Cột theo tháng: số tiền trên thẻ là TB/tháng của 3 tháng trước, không phải
# doanh thu luỹ kế — ô tổng đầu trang không được cộng lẫn hai loại số.
COT_THANG = "thang_nay_chua_mua"

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
    so_thang: int | None = None          # cột tháng: số tháng có mua trong 3 tháng trước
    dt_thang_truoc: int | None = None    # cột tháng: doanh thu tháng trước

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
    trung: int = 0      # cột tháng: số khách bỏ vì đã ở cột khác / đang tạm ẩn


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
    """MỘT lượt hỏi: mọi khách của `mart.uu_tien_lien_he` + khách 'tre' của
    `mart.khach_thang_nay` (cột tháng, 036), lọc theo sale, kèm lần tiếp xúc
    MỚI NHẤT. Chia cột, ẩn, đếm làm bằng Python trên vài
    trăm dòng — rẻ hơn ba câu đếm riêng (mỗi câu dựng lại khach_360)."""
    if ly_do not in LY_DO:
        ly_do = None
    dk, ts = _loc_sale(sale, "salesperson_code")
    dk2, ts2 = _loc_sale(sale, "k.salesperson_code")
    rows = conn.execute(
        f"""WITH u AS (
                SELECT customer_code, ten, prefecture, phone, salesperson_code,
                       doanh_thu_thuan, so_ngay_im_lang, nhip_ngay, ty_le_im_lang,
                       ly_do, thu_tu, NULL::int AS so_thang, NULL::numeric AS dt_truoc
                  FROM mart.uu_tien_lien_he WHERE true {dk}
                UNION ALL
                SELECT k.customer_code, k.ten, d.prefecture, d.phone, k.salesperson_code,
                       k.dt_tb_3_thang, NULL, NULL, NULL,
                       '{COT_THANG}', 4, k.so_thang_mua_3, k.dt_thang_truoc
                  FROM mart.khach_thang_nay k
                  LEFT JOIN core.dim_customer d
                         ON d.customer_code = k.customer_code AND d.is_current
                 WHERE k.nhan = 'tre' {dk2})
            SELECT u.customer_code, u.ten, u.prefecture, u.phone,
                   coalesce(sp.ten, u.salesperson_code),
                   u.doanh_thu_thuan, u.so_ngay_im_lang, u.nhip_ngay, u.ty_le_im_lang,
                   u.ly_do, n.kieu, n.ket_qua, n.noi_dung, n.thoi_diem, n.hen_lai,
                   u.so_thang, u.dt_truoc
            FROM u
            LEFT JOIN core.dim_salesperson sp ON sp.salesperson_code = u.salesperson_code
            LEFT JOIN LATERAL (
                SELECT kieu, ket_qua, noi_dung, thoi_diem, hen_lai
                FROM app.nhat_ky_tiep_xuc x
                WHERE x.customer_code = u.customer_code
                ORDER BY x.thoi_diem DESC, x.id DESC LIMIT 1) n ON true
            ORDER BY u.thu_tu, u.doanh_thu_thuan DESC NULLS LAST, u.customer_code""",
        ts + ts2).fetchall()
    theo: dict[str, list[The]] = {k: [] for k in LY_DO}
    an: list[The] = []
    da_co: set[str] = set()   # khách đã ở ba cột nhịp (kể cả đang ẩn)
    trung = 0
    for r in rows:
        if r[9] == COT_THANG:
            if r[0] in da_co:
                trung += 1
                continue
        else:
            da_co.add(r[0])
        cuoi = (LanTiepXuc(kieu=r[10], ket_qua=r[11], noi_dung=r[12],
                           thoi_diem=r[13], hen_lai=r[14]) if r[13] else None)
        t = The(ma=r[0], ten=r[1], tinh=r[2], dien_thoai=r[3], phu_trach=r[4],
                doanh_thu=int(r[5] or 0), so_ngay_im_lang=r[6],
                nhip_ngay=float(r[7]) if r[7] is not None else None,
                ty_le=float(r[8]) if r[8] is not None else None,
                ly_do=r[9], cuoi=cuoi, so_thang=r[15],
                dt_thang_truoc=int(r[16]) if r[16] is not None else None)
        (an if dang_an(cuoi, hom_nay) else theo[t.ly_do]).append(t)
    cot = []
    for k, (nhan, mo_ta, mau) in LY_DO.items():
        ds = theo[k]
        cot.append(Cot(ly_do=k, nhan=nhan, mo_ta=mo_ta, mau=mau,
                       the=ds if ly_do == k else ds[:THE_MOI_COT], tong=len(ds),
                       doanh_thu=sum(t.doanh_thu for t in ds),
                       trung=trung if k == COT_THANG else 0))
    if ly_do:
        cot = [c for c in cot if c.ly_do == ly_do]
    return DanhSach(cot=cot, da_lien_he=an, hom_nay=hom_nay, ly_do=ly_do,
                    dem={k: len(v) for k, v in theo.items()})


# Số mã "Nên chào" trên mỗi thẻ.
SO_MA_GOI_Y = 3

# In ngay dưới dòng gợi ý — người đọc phải biết gợi ý dựa trên cái gì. Không có
# "% chắc chắn": không đo được (cùng lý lẽ đợt 8, /du-bao).
CACH_TINH_GOI_Y = ("Mã chính khách này đã mua đều (≥ 3 lần, có nhịp mua riêng), "
                   "xếp theo số lần mua rồi lần mua gần nhất — không gồm phí/điều chỉnh "
                   "và hàng tặng POSM.")


def goi_y_va_nhan_vien(conn, ma_khach: list[str], so_ma: int = SO_MA_GOI_Y) -> dict:
    """MỘT lượt hỏi: (1) tối đa `so_ma` mã "Nên chào" cho mỗi khách trong
    `ma_khach`, (2) danh sách người phụ trách cho ô chọn 担当者.

    Gợi ý ĐỌC `mart.khach_mat_hang` (view đó đã bỏ phí/điều chỉnh 048 và hàng
    tặng 049, đã quay về theo mốc 040) — không tự định nghĩa lại "mặt hàng".
    `nhip_ngay IS NOT NULL` = ≥ 3 lần mua (định nghĩa của chính view đó); cặp
    'khong_goi' (khách ※廃業※ / hạng OBC Z/ZZ/ZZZ — 055) không bao giờ được gợi ý. Cặp 'ngung' VẪN được
    gợi ý: khách ở cột "Lâu không mua" thì hầu hết mặt hàng quen đều đã quá 2×
    nhịp — bỏ chúng là đúng khách cần gọi nhất không có gợi ý nào; thẻ in số
    ngày từ lần cuối để sale tự thấy."""
    r = conn.execute(
        # LATERAL với `customer_code = k.ma` chứ KHÔNG `= ANY(%s)`: đo thật
        # 2026-09-26, vị từ `= ANY` không đẩy xuống được qua mart.nhip_mat_hang
        # (percentile_cont) nên view dựng lại cho MỌI cặp (~1,3 s); vị từ bằng
        # một mã thì đẩy xuống (~20 ms/khách).
        """WITH g AS (
               SELECT k.ma AS khach, h.*
                 FROM unnest(%s::text[]) k(ma)
                 CROSS JOIN LATERAL (
                     SELECT h.product_code AS ma, h.ten_hang AS ten, h.so_lan,
                            h.nhip_ngay::float8 AS nhip_ngay,
                            (m.hom_nay - h.lan_cuoi) AS so_ngay, h.trang_thai_cap AS trang_thai
                       FROM mart.khach_mat_hang h
                       CROSS JOIN mart.moc_thoi_gian m
                      WHERE h.customer_code = k.ma
                        AND h.nhip_ngay IS NOT NULL
                        AND h.trang_thai_cap <> 'khong_goi'
                      ORDER BY h.so_lan DESC, h.lan_cuoi DESC, h.product_code
                      LIMIT %s) h)
           SELECT (SELECT coalesce(json_agg(g ORDER BY g.khach, g.so_lan DESC, g.so_ngay, g.ma), '[]')
                     FROM g),
                  (SELECT coalesce(json_agg(json_build_object('ma', salesperson_code, 'ten', ten)
                                            ORDER BY salesperson_code), '[]')
                     FROM core.dim_salesperson)""",
        [list(ma_khach), so_ma]).fetchone()
    goi_y: dict[str, list] = {}
    for x in r[0]:
        goi_y.setdefault(x.pop("khach"), []).append(x)
    return {"goi_y": goi_y, "nhan_vien": r[1]}


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
    try:        # JSON cho phép nửa cặp UTF-16 lẻ loi (U+D800…U+DFFF) -> str không mã hoá UTF-8 được -> 500 ở psycopg
        noi_dung.encode("utf-8")
    except UnicodeEncodeError:
        raise LoiNhap("Nội dung có ký tự không hợp lệ (nửa ký tự UTF-16) — gõ hoặc dán lại câu.") from None
    hen = None
    if hen_lai:
        try:
            hen = date.fromisoformat(hen_lai)
        except ValueError:
            raise LoiNhap("Ngày hẹn lại không đọc được.") from None
    return kieu, ket_qua, noi_dung, hen


def ghi(conn, ma: str, nguoi_id: int | None, kieu: str, ket_qua: str,
        noi_dung: str, hen_lai: str = "") -> int:
    """Thêm MỘT dòng nhật ký, trả `id` của nó (người gọi cũ bỏ qua giá trị trả).
    Không commit — người gọi quyết định giao dịch."""
    kieu, ket_qua, noi_dung, hen = doc_bieu_mau(kieu, ket_qua, noi_dung, hen_lai)
    co = conn.execute(
        "SELECT 1 FROM core.dim_customer WHERE customer_code = %s AND is_current",
        (ma,)).fetchone()
    if co is None:
        raise LoiNhap(f"Không có khách mã {ma}.")
    return conn.execute(
        """INSERT INTO app.nhat_ky_tiep_xuc
             (customer_code, nguoi_dung_id, kieu, ket_qua, noi_dung, hen_lai)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (ma, nguoi_id, kieu, ket_qua, noi_dung, hen)).fetchone()[0]


# ---- Đợt 2 (063): tin hiện trường `@` -------------------------------------------------------------

MAX_THE = 30                      # số thẻ / số giá tối đa mỗi lần ghi


def _dict_list(v, ten: str) -> list[dict]:
    if v is None:
        return []
    if not isinstance(v, list) or not all(isinstance(x, dict) for x in v):
        raise LoiNhap(f"'{ten}' phải là một danh sách các đối tượng.")
    if len(v) > MAX_THE:
        raise LoiNhap(f"Tối đa {MAX_THE} mục '{ten}' mỗi lần ghi.")
    return v


def _int(v, ten: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise LoiNhap(f"Thẻ: '{ten}' phải là số nguyên.")
    return v


def _kiem_the(conn, noi_dung: str, nhac: list[dict]) -> list[tuple]:
    """Kiểm từng thẻ và đổi vị trí về ĐÚNG câu được lưu. Trả [(loai, khoa, vi_tri_dau, do_dai)].

    Giao diện gửi vị trí theo chuỗi JS (đơn vị UTF-16) trên ô chữ CHƯA cắt khoảng trắng; máy chủ lưu câu
    ĐÃ `strip()` và vị trí theo ký tự Unicode (Python) — hai bên chỉ khác nhau khi câu có khoảng trắng đầu
    hoặc ký tự ngoài BMP (emoji), nên phải đổi ở đây chứ không tin thẳng con số."""
    if not nhac:
        return []
    goc = noi_dung or ""
    u16 = goc.encode("utf-16-le", "surrogatepass")
    n_dv = len(u16) // 2
    luu = goc.strip()
    dau = len(goc) - len(goc.lstrip())
    ra: list[tuple] = []
    for t in nhac:
        loai, khoa = t.get("loai"), t.get("khoa")
        if loai not in ("doi_thu", "nhom") or not isinstance(khoa, str) or not DT.KHOA_SACH.fullmatch(khoa):
            raise LoiNhap("Thẻ @ không hợp lệ: loại hoặc khoá sai.")
        if loai == "nhom" and not DT.KHOA_NHOM.fullmatch(khoa):
            raise LoiNhap(f"Thẻ hàng '{khoa}' sai định dạng (ma:<mã> hoặc n:<số>).")
        vt, dd = _int(t.get("vi_tri_dau"), "vi_tri_dau"), _int(t.get("do_dai"), "do_dai")
        if vt < 0 or dd < 2 or vt + dd > n_dv:
            raise LoiNhap("Thẻ @ nằm ngoài câu ghi chú.")
        if u16[2 * vt:2 * vt + 2] != b"@\x00":
            raise LoiNhap("Thẻ @ lệch vị trí: chỗ đó trong câu không phải dấu @.")
        try:
            cp = len(u16[:2 * vt].decode("utf-16-le"))
            dd_cp = len(u16[2 * vt:2 * (vt + dd)].decode("utf-16-le"))
        except UnicodeDecodeError:
            raise LoiNhap("Thẻ @ cắt ngang một ký tự.") from None
        cp -= dau
        if cp < 0 or cp + dd_cp > len(luu):
            raise LoiNhap("Thẻ @ nằm ngoài câu ghi chú.")
        ra.append((loai, khoa, cp, dd_cp))
    ra.sort(key=lambda x: x[2])
    for a, b in zip(ra, ra[1:]):
        if a[2] + a[3] > b[2]:
            raise LoiNhap("Hai thẻ @ chồng lên nhau.")
    # Tồn tại: đối thủ trong app.doi_thu; nhóm 'ma:' trong core.dim_product, 'n:' trong app.nhom_so_sanh.
    dt = sorted({k for l, k, _, _ in ra if l == "doi_thu"})
    if dt:
        co = {r[0] for r in conn.execute("SELECT ma FROM app.doi_thu WHERE ma = ANY(%s)", (dt,))}
        for k in dt:
            if k not in co:
                raise LoiNhap(f"Không có đối thủ '{k}'.")
    ma = sorted({k[3:] for l, k, _, _ in ra if l == "nhom" and k.startswith("ma:")})
    if ma:
        co = {r[0] for r in conn.execute("SELECT product_code FROM core.dim_product WHERE product_code = ANY(%s)", (ma,))}
        for k in ma:
            if k not in co:
                raise LoiNhap(f"Không có mã KOME '{k}'.")
    ns = sorted({int(k[2:]) for l, k, _, _ in ra if l == "nhom" and k.startswith("n:")})
    if ns:
        co = {r[0] for r in conn.execute("SELECT id FROM app.nhom_so_sanh WHERE id = ANY(%s)", (ns,))}
        for k in ns:
            if k not in co:
                raise LoiNhap(f"Không có nhóm so sánh số {k}.")
    return ra


def ghi_kem_nhac(conn, ma: str, nguoi_id: int | None, kieu: str, ket_qua: str, noi_dung: str,
                 hen_lai: str = "", nhac: list[dict] | None = None, gia: list[dict] | None = None) -> dict:
    """Ghi MỘT lần tiếp xúc kèm thẻ `@` (`app.tiep_xuc_nhac`) và giá khách kể (`app.gia_doi_thu_tay`,
    `loai_nguon = 'khach_ke'`) — CÙNG một giao dịch. Trả {"id", "canh_bao": [...]}. Không commit.

    `nhac`: [{loai: 'doi_thu'|'nhom', khoa, vi_tri_dau, do_dai}] — `khoa` của nhóm là 'ma:<mã KOME>' hoặc
    'n:<id>'; vị trí do giao diện gửi (xem `_kiem_the`). `gia`: [{ma_doi_thu, nhom_khoa, gia_goc, don_vi_gia}] —
    mỗi giá PHẢI có thẻ đối thủ VÀ thẻ nhóm tương ứng trong chính `nhac` này (máy không tự đọc số trong
    câu: giá chỉ đến từ ô giá). Sai gì cũng `LoiNhap` và KHÔNG để lại dòng nào — kể cả khi người gọi bắt lỗi
    rồi vẫn commit (phần ghi nằm trong một SAVEPOINT).

    `canh_bao`: giá vừa ghi mà `mart.gia_doi_thu_hien_hanh` đánh cờ `bat_thuong` (> 2× hoặc < ½ trung vị
    của nhóm ≥ 3 bên) -> một câu nhắc kiểm lại đơn vị, in trung vị của `mart.so_sanh_nhom` (số tab So sánh giá
    hiện); KHÔNG chặn ghi. MỘT lượt hỏi cho mọi giá."""
    from kome.dinh_dang import yen

    # Kiểu / độ dài của chính câu ghi chú TRƯỚC (rẻ) — rồi mới mã hoá và dò từng thẻ.
    doc_bieu_mau(kieu, ket_qua, noi_dung, hen_lai)
    nhac, gia = _dict_list(nhac, "nhac"), _dict_list(gia, "gia")
    cac_the = _kiem_the(conn, noi_dung, nhac)
    co_dt = {k for l, k, _, _ in cac_the if l == "doi_thu"}
    co_nhom = {k for l, k, _, _ in cac_the if l == "nhom"}
    for g in gia:
        b, k = g.get("ma_doi_thu"), g.get("nhom_khoa")
        if not isinstance(b, str) or not isinstance(k, str) or b not in co_dt or k not in co_nhom:
            raise LoiNhap("Giá phải đi kèm thẻ @đối thủ và thẻ @hàng tương ứng trong câu ghi chú.")

    conn.execute("SAVEPOINT ghi_kem_nhac")
    try:
        tid = ghi(conn, ma, nguoi_id, kieu, ket_qua, noi_dung, hen_lai)
        if cac_the:
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO app.tiep_xuc_nhac (tiep_xuc_id, loai, khoa, vi_tri_dau, do_dai)
                       VALUES (%s, %s, %s, %s, %s)""", [(tid, *t) for t in cac_the])
        ids = []
        for g in gia:
            try:
                ids.append(DT.gia_khach_ke(conn, g["ma_doi_thu"], g["nhom_khoa"], ma, tid,
                                           g.get("gia_goc"), g.get("don_vi_gia"), nguoi_id))
            except DT.LoiNhap as e:
                raise LoiNhap(str(e)) from None
        canh_bao = []
        if ids:
            # Số in ra là trung vị của `mart.so_sanh_nhom` — đúng số tab So sánh giá hiện (bỏ giá bất thường),
            # KHÔNG phải `trung_vi_nhom` (trung vị dùng để BẮT bất thường, tính cả giá lệch): hai con số cùng
            # tên "trung vị" trên hai màn là người đọc đi đối chiếu rồi không khớp.
            for gia_goc, dv, dv_so, tv in conn.execute(
                    """SELECT h.gia_goc, h.don_vi_gia, h.don_vi_so, s.trung_vi
                       FROM mart.gia_doi_thu_hien_hanh h
                       LEFT JOIN mart.so_sanh_nhom s ON s.nhom_khoa = h.nhom_khoa AND s.don_vi_so = h.don_vi_so
                       WHERE h.nguon = 'tay' AND h.id = ANY(%s) AND h.bat_thuong ORDER BY h.id""",
                    (ids,)).fetchall():
                moc = (f"trung vị {yen(tv)}/{'kg' if dv_so == 'kg' else dv} của nhóm" if tv is not None
                       else "giá các bên khác của nhóm")
                canh_bao.append(f"Giá {yen(gia_goc)}/{dv} lệch xa {moc} — kiểm lại đơn vị?")
        conn.execute("RELEASE SAVEPOINT ghi_kem_nhac")
    except BaseException:
        try:
            conn.execute("ROLLBACK TO SAVEPOINT ghi_kem_nhac")
        except Exception:      # noqa: BLE001 — kết nối đã hỏng: giao dịch của người gọi tự thu lại
            pass
        raise
    return {"id": tid, "canh_bao": canh_bao}
