"""Bảng điều khiển: đọc số từ `mart`, KHÔNG tự định nghĩa chỉ số ở đây.

Mọi công thức ("doanh thu thuần là gì", "tỷ suất tính thế nào") nằm trong
db/migrations/014_mart_bao_cao.sql. Module này chỉ hỏi và sắp xếp để hiển thị.

Vì sao tách bạch: nếu một công thức được viết lại ở đây cho tiện, thì trang web
và câu SQL người ta gõ tay sẽ trả hai con số khác nhau, và không ai biết bên nào
đúng. Mất niềm tin vào con số thì cả hệ thống này vô dụng.

Cũng KHÔNG mở kết nối: hàm nhận sẵn `conn`. Gọi connect() không tham số ở đây
sẽ âm thầm đọc CSDL THẬT trong khi test tưởng mình đang dùng CSDL thử nghiệm.
"""
from dataclasses import dataclass, field
from datetime import date

# Bao nhiêu dòng trong mỗi bảng xếp hạng. 10 vừa một màn hình; dài hơn thì
# người đọc cuộn qua chứ không đọc.
TOP = 10

# Số tháng tối thiểu để một kỳ được đem so với kỳ khác.
DU_MOT_KY = 12


@dataclass
class O:
    """Một tháng trên biểu đồ."""
    thang: str
    doanh_thu: int
    lai_gop: int
    ty_suat: float | None
    co_cung_ky: bool
    tang_truong: float | None
    la_thang_chot: bool
    so_phieu: int


@dataclass
class Ky:
    company_fy: int
    so_ky: int
    nhan: str
    doanh_thu: int
    lai_gop: int
    ty_suat: float | None
    so_khach: int
    so_phieu: int
    so_thang: int
    ngay_dau: date | None
    ngay_cuoi: date | None

    @property
    def du_12_thang(self) -> bool:
        return self.so_thang >= DU_MOT_KY


@dataclass
class BaoCao:
    ky: Ky
    moi_ky: list[Ky]
    thang: list[O]
    khach: list[dict]
    hang: list[dict]
    nhan_vien: list[dict]
    khong_co_du_lieu: bool = False
    canh_bao: list[str] = field(default_factory=list)


def _ky_tu_dong(r) -> Ky:
    return Ky(company_fy=r[0], so_ky=r[1], nhan=r[2], ngay_dau=r[3], ngay_cuoi=r[4],
              so_thang=r[5], doanh_thu=int(r[6] or 0), lai_gop=int(r[7] or 0),
              ty_suat=float(r[8]) if r[8] is not None else None,
              so_khach=r[9], so_phieu=r[10])


def tinh_bao_cao(conn, company_fy: int | None = None) -> BaoCao:
    """Số liệu cho một kỳ kế toán. company_fy=None => kỳ GẦN NHẤT có dữ liệu."""
    moi_ky = [_ky_tu_dong(r) for r in conn.execute(
        """SELECT company_fy, company_fy_no, nhan, ngay_dau, ngay_cuoi,
                  so_thang_co_du_lieu, doanh_thu_thuan, lai_gop, ty_suat,
                  so_khach, so_phieu
           FROM mart.tong_theo_ky ORDER BY company_fy""").fetchall()]

    if not moi_ky:
        trong = Ky(0, 0, "(chưa có dữ liệu)", 0, 0, None, 0, 0, 0, None, None)
        return BaoCao(ky=trong, moi_ky=[], thang=[], khach=[], hang=[],
                      nhan_vien=[], khong_co_du_lieu=True)

    ky = next((k for k in moi_ky if k.company_fy == company_fy), moi_ky[-1])

    thang = [
        O(thang=r[0], doanh_thu=int(r[1] or 0), lai_gop=int(r[2] or 0),
          ty_suat=float(r[3]) if r[3] is not None else None,
          co_cung_ky=r[4], tang_truong=float(r[5]) if r[5] is not None else None,
          la_thang_chot=r[0].endswith("-07"), so_phieu=r[6])
        for r in conn.execute(
            """SELECT thang, doanh_thu_thuan, lai_gop, ty_suat, co_cung_ky,
                      tang_truong, so_phieu
               FROM mart.ban_theo_thang_so_sanh
               WHERE company_fy = %s ORDER BY thang""", (ky.company_fy,)).fetchall()
    ]

    khach = [dict(zip(("ma", "ten", "tinh", "doanh_thu", "lai_gop", "ty_suat",
                       "so_phieu", "mua_gan_nhat"), r)) for r in conn.execute(
        """SELECT customer_code, ten_khach, prefecture, doanh_thu_thuan, lai_gop,
                  ty_suat, so_phieu, mua_gan_nhat
           FROM mart.ban_theo_khach WHERE company_fy = %s
           ORDER BY doanh_thu_thuan DESC LIMIT %s""", (ky.company_fy, TOP)).fetchall()]

    hang = [dict(zip(("ma", "ten", "nhom", "doanh_thu", "lai_gop", "ty_suat",
                      "so_khach"), r)) for r in conn.execute(
        """SELECT product_code, ten_hang, food_category_name, doanh_thu_thuan,
                  lai_gop, ty_suat, so_khach_mua
           FROM mart.ban_theo_san_pham WHERE company_fy = %s
           ORDER BY lai_gop DESC LIMIT %s""", (ky.company_fy, TOP)).fetchall()]

    nhan_vien = [dict(zip(("ma", "doanh_thu", "lai_gop", "ty_suat", "so_khach",
                           "so_phieu"), r)) for r in conn.execute(
        """SELECT salesperson_code, doanh_thu_thuan, lai_gop, ty_suat, so_khach, so_phieu
           FROM mart.ban_theo_nhan_vien WHERE company_fy = %s
           ORDER BY doanh_thu_thuan DESC""", (ky.company_fy,)).fetchall()]

    canh_bao = []
    if not ky.du_12_thang:
        canh_bao.append(
            f"{ky.nhan} mới có {ky.so_thang}/12 tháng dữ liệu — đừng đem tổng "
            f"kỳ này so với kỳ đủ 12 tháng.")
    if any(not o.co_cung_ky for o in thang):
        thieu = [o.thang for o in thang if not o.co_cung_ky]
        canh_bao.append(
            f"{len(thieu)} tháng KHÔNG có dữ liệu cùng kỳ năm trước "
            f"({thieu[0]}…{thieu[-1]}) — công ty không còn lưu dữ liệu bán trước "
            f"2025-03-03. Cột 'So cùng kỳ' để trống là đúng, không phải lỗi.")
    return BaoCao(ky=ky, moi_ky=moi_ky, thang=thang, khach=khach, hang=hang,
                  nhan_vien=nhan_vien, canh_bao=canh_bao)


# ---- Vẽ biểu đồ ---------------------------------------------------------
# Tự tính toạ độ SVG thay vì dùng thư viện biểu đồ JavaScript: trang phải chạy
# được cả trên Vercel (nơi CSP chặn script ngoài) lẫn ở máy không có mạng, và
# nguyên tắc của dự án là giảm tối đa số thứ có thể hỏng.

RONG, CAO, LE_T, LE_P, LE_TREN, LE_DUOI = 720, 260, 8, 8, 16, 34


def ve_bieu_do(thang: list[O]) -> dict:
    """Toạ độ cột doanh thu + đường tỷ suất lãi gộp, cùng một trục hoành."""
    if not thang:
        return {"co": False}
    cao_ve = CAO - LE_TREN - LE_DUOI
    rong_ve = RONG - LE_T - LE_P
    dinh = max((o.doanh_thu for o in thang), default=0) or 1
    buoc = rong_ve / len(thang)
    rong_cot = max(buoc * 0.62, 3)

    cot, diem = [], []
    ts = [o.ty_suat for o in thang if o.ty_suat is not None]
    # Trục tỷ suất KHÔNG bắt đầu từ 0: khoảng dao động thật là 26–38%, vẽ từ 0
    # thì đường gần như phẳng và giấu mất đúng thứ cần nhìn. Nới hai đầu 2 điểm
    # phần trăm để đỉnh và đáy không dính mép.
    lo, hi = (min(ts) - 0.02, max(ts) + 0.02) if ts else (0.0, 1.0)
    if hi - lo < 0.01:
        lo, hi = lo - 0.05, hi + 0.05

    for i, o in enumerate(thang):
        x = LE_T + i * buoc
        h = max(cao_ve * (o.doanh_thu / dinh), 0) if o.doanh_thu > 0 else 0
        cot.append({"x": round(x + (buoc - rong_cot) / 2, 1),
                    "y": round(LE_TREN + cao_ve - h, 1),
                    "w": round(rong_cot, 1), "h": round(h, 1), "o": o})
        if o.ty_suat is not None:
            y = LE_TREN + cao_ve - cao_ve * (o.ty_suat - lo) / (hi - lo)
            diem.append((round(x + buoc / 2, 1), round(y, 1), o))

    return {"co": True, "rong": RONG, "cao": CAO, "cot": cot, "diem": diem,
            "duong": " ".join(f"{x},{y}" for x, y, _ in diem),
            "ts_lo": lo, "ts_hi": hi, "dinh_doanh_thu": dinh}
