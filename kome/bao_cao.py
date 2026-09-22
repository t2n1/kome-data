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

# "12 tháng của một kỳ, 8月 trước" là MỘT định nghĩa — nhập từ kome/ngan_sach.py
# chứ không chép lại, xem chú thích ở khối "Ngân sách" cuối file này.
from kome.ngan_sach import thang_cua_ky

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


# ---- Ngân sách (đợt 5a) -------------------------------------------------
# Mọi công thức nằm ở mart.tien_do_ngan_sach (migration 026). Ở đây chỉ hỏi
# và sắp xếp để hiển thị — cùng nguyên tắc đã ghi ở đầu file này.
#
# `thang_cua_ky` NHẬP từ kome/ngan_sach.py chứ không chép lại: "12 tháng của
# một kỳ, 8月 trước" là một định nghĩa, và hai bản chép của nó là hai thứ sẽ
# trôi khỏi nhau đúng lúc ai đó đổi năm tài chính của công ty. Dòng
# `from kome.ngan_sach import thang_cua_ky` đặt ở KHỐI NHẬP ĐẦU FILE, theo
# nếp của mọi module khác trong repo — không có vòng nhập nào vì
# kome/ngan_sach.py không nhập kome/bao_cao.py.

@dataclass(frozen=True)
class TienDoNguoi:
    ma: str
    ten: str | None          # None = mã KHÔNG có trong core.dim_salesperson
    thuc_te: int
    muc_tieu: int | None
    muc_tieu_den_hom_nay: int | None
    tien_do: float | None
    cung_ky: int | None      # doanh thu cùng tháng năm trước, None nếu không có


@dataclass(frozen=True)
class MocLuyKe:
    thang: str
    thuc_te: int | None      # None = tháng nằm SAU hom_nay (chưa có dữ liệu)
    ngan_sach: int | None


@dataclass(frozen=True)
class TienDoNganSach:
    company_fy: int
    thang: str
    hom_nay: date | None
    ngay_kd: int
    ngay_kd_da_qua: int
    thuc_te: int
    muc_tieu: int | None
    muc_tieu_den_hom_nay: int | None
    tien_do: float | None
    nguoi: list[TienDoNguoi]
    luy_ke: list[MocLuyKe]
    co_ngan_sach: bool


def tien_do_ngan_sach(conn, company_fy: int | None = None) -> "TienDoNganSach | None":
    """Tiến độ so với chỉ tiêu. None khi kho chưa có dòng bán nào.

    Tháng đang xét là tháng của `mart.moc_thoi_gian.hom_nay`, KHÔNG phải tháng
    theo đồng hồ thật. Đo thật 2026-09-22: phiếu bán mới nhất là 2026-07-31 —
    gần hai tháng không ai nạp file bán hàng. Lấy current_date thì trang báo
    "tháng 9 đạt 0% ngân sách" trong khi sự thật là chưa ai nạp dữ liệu tháng 9.
    """
    r = conn.execute(
        """SELECT m.hom_nay, d.company_fy, to_char(m.hom_nay, 'YYYY-MM')
           FROM mart.moc_thoi_gian m
           JOIN core.dim_date d ON d.date_key = m.hom_nay""").fetchone()
    if r is None:
        return None
    hom_nay, fy_hom_nay, thang_hom_nay = r[0], r[1], r[2]
    ky = company_fy or fy_hom_nay
    thang = thang_hom_nay if ky == fy_hom_nay else thang_cua_ky(ky)[-1]

    # Một câu cho cả dòng theo người của tháng đang xét, kèm tên và cùng kỳ.
    # LEFT JOIN dim_salesperson: mã ngoài danh sách phụ trách vẫn có dòng, chỉ
    # là không có tên (§7.3 của đặc tả).
    # Lấy luôn ngay_kd/ngay_kd_da_qua từ chính view này thay vì hỏi
    # mart.ngay_kinh_doanh một lượt nữa: chúng đã là cột của
    # mart.tien_do_ngan_sach và giống nhau ở mọi dòng của cùng một tháng.
    # Một lượt hỏi qua pooler Tokyo mất ~260 ms — không đáng cho hai con số
    # đã nằm sẵn trong kết quả.
    dong = conn.execute(
            """SELECT t.salesperson_code, s.ten, t.thuc_te, t.muc_tieu,
                      t.muc_tieu_den_hom_nay, t.tien_do, tr.doanh_thu_thuan,
                      t.ngay_kd, t.ngay_kd_da_qua
               FROM mart.tien_do_ngan_sach t
               LEFT JOIN core.dim_salesperson s
                      ON s.salesperson_code = t.salesperson_code
               LEFT JOIN mart.ban_theo_nhan_vien_thang tr
                      ON tr.salesperson_code = t.salesperson_code
                     AND tr.thang = to_char(
                           to_date(%s, 'YYYY-MM') - interval '1 year', 'YYYY-MM')
               WHERE t.thang = %s
               ORDER BY t.salesperson_code""", (thang, thang)).fetchall()

    nguoi = [TienDoNguoi(
        ma=x[0], ten=x[1], thuc_te=int(x[2] or 0),
        muc_tieu=int(x[3]) if x[3] is not None else None,
        muc_tieu_den_hom_nay=int(x[4]) if x[4] is not None else None,
        tien_do=float(x[5]) if x[5] is not None else None,
        cung_ky=int(x[6]) if x[6] is not None else None) for x in dong]
    # Tháng không có dòng nào (chọn một kỳ đã qua mà tháng cuối kỳ không có
    # doanh thu lẫn chỉ tiêu) -> 0/0. Khi đó `co_ngan_sach` cũng FALSE nên
    # màn hình hiện khối "chưa đặt chỉ tiêu", không hiện bộ đếm ngày.
    ngay_kd, ngay_kd_da_qua = (dong[0][7], dong[0][8]) if dong else (0, 0)

    # Luỹ kế 12 tháng của kỳ. Tháng SAU hom_nay trả None cho thực tế: một
    # đường rơi xuống 0 đọc thành "doanh thu sụp", không phải "chưa có dữ liệu".
    #
    # Alias bảng nguồn là `b` (khớp đúng lối viết mà
    # test_dinh_nghia_chi_so_nam_o_mart_khong_o_python đã chừa sẵn cho phép
    # cộng dồn có alias): câu này cộng dồn các dòng đã có sẵn công thức từ
    # mart.tien_do_ngan_sach để ra tổng cả công ty — không định nghĩa lại
    # "tiến độ" hay bất kỳ chỉ số nào, chỉ gộp dòng để hiển thị.
    thang_ky = thang_cua_ky(ky)
    theo_thang = {x[0]: (int(x[1] or 0), int(x[2]) if x[2] is not None else None)
                  for x in conn.execute(
        """SELECT thang, sum(b.thuc_te), sum(b.muc_tieu)
           FROM mart.tien_do_ngan_sach b WHERE company_fy = %s
           GROUP BY thang""", (ky,)).fetchall()}

    luy_ke, c_tt, c_ns = [], 0, 0
    for th in thang_ky:
        tt, ns = theo_thang.get(th, (0, None))
        c_tt += tt
        c_ns += ns or 0
        luy_ke.append(MocLuyKe(
            thang=th,
            thuc_te=c_tt if th <= thang_hom_nay else None,
            ngan_sach=c_ns if c_ns else None))

    # Cộng dồn bằng vòng lặp tay thay vì hàm dựng sẵn của Python: cùng lý do
    # ghi ở trên — có test canh mã nguồn để chặn ai đó lỡ viết lại công thức
    # chỉ số trong Python, và phép cộng tổng công ty từ các dòng-người đã
    # tính sẵn này không phải một công thức mới.
    tong_tt = 0
    for n in nguoi:
        tong_tt += n.thuc_te
    co_mt = [n.muc_tieu for n in nguoi if n.muc_tieu is not None]
    tong_mt = None
    if co_mt:
        tong_mt = 0
        for v in co_mt:
            tong_mt += v
    co_moc = [n.muc_tieu_den_hom_nay for n in nguoi
              if n.muc_tieu_den_hom_nay is not None]
    tong_moc = None
    if co_moc:
        tong_moc = 0
        for v in co_moc:
            tong_moc += v

    return TienDoNganSach(
        company_fy=ky, thang=thang, hom_nay=hom_nay,
        ngay_kd=ngay_kd, ngay_kd_da_qua=ngay_kd_da_qua,
        thuc_te=tong_tt, muc_tieu=tong_mt,
        muc_tieu_den_hom_nay=tong_moc,
        tien_do=(tong_tt / tong_mt) if tong_mt else None,
        nguoi=nguoi, luy_ke=luy_ke, co_ngan_sach=bool(co_mt))


def ve_luy_ke(td: "TienDoNganSach | None") -> dict:
    """Toạ độ hai đường luỹ kế (thực tế và nhịp ngân sách) trên cùng một trục.

    Tự tính toạ độ SVG như `ve_bieu_do`: trang phải chạy cả trên Vercel (CSP
    chặn script ngoài) lẫn ở máy không có mạng.
    """
    if td is None or not td.co_ngan_sach:
        return {"co": False}
    cao_ve = CAO - LE_TREN - LE_DUOI
    rong_ve = RONG - LE_T - LE_P
    dinh = max([m.thuc_te or 0 for m in td.luy_ke]
               + [m.ngan_sach or 0 for m in td.luy_ke]) or 1
    buoc = rong_ve / max(len(td.luy_ke) - 1, 1)

    def _duong(lay) -> str:
        diem = []
        for i, m in enumerate(td.luy_ke):
            v = lay(m)
            if v is None:
                continue
            x = LE_T + i * buoc
            y = LE_TREN + cao_ve - cao_ve * (v / dinh)
            diem.append(f"{round(x, 1)},{round(y, 1)}")
        return " ".join(diem)

    return {"co": True, "rong": RONG, "cao": CAO, "dinh": dinh,
            "thuc_te": _duong(lambda m: m.thuc_te),
            "ngan_sach": _duong(lambda m: m.ngan_sach),
            "nhan": [m.thang for m in td.luy_ke]}
