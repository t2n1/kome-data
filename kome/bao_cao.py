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
    so_khach: int
    dt_cung_ky: int | None


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


class _SoCungKy:
    """Trộn sẵn các phép CHIA của hai bộ cột tổng `dt/lg/so_khach` và
    `..._ck` (cùng kỳ) — không định nghĩa chỉ số mới, chỉ là tỷ số của các
    TỔNG đã tính sẵn trong `mart` (`mart.ky_cung_ky`, và đợt 5b Task 5
    `mart.thang_den_hom_nay` dùng lại đúng lớp này qua `ThangNay`, cùng bộ
    cột). Một công thức viết MỘT LẦN ở đây, không phải mỗi dataclass tự chia
    lấy rồi trôi khỏi nhau.

    Tăng trưởng None khi mẫu số None hoặc <= 0: 赤伝 (phiếu đỏ) có thể làm
    doanh thu/lãi gộp cùng kỳ năm trước ÂM, và chia cho số âm ra phần trăm
    NGƯỢC DẤU — một con số sai còn tệ hơn không có con số.
    """
    dt: int | None
    lg: int | None
    so_khach: int | None
    dt_ck: int | None
    lg_ck: int | None
    so_khach_ck: int | None

    @staticmethod
    def _tang(tu_so, mau_so) -> float | None:
        if tu_so is None or mau_so is None or mau_so <= 0:
            return None
        return tu_so / mau_so - 1

    @property
    def tang_dt(self) -> float | None:
        return self._tang(self.dt, self.dt_ck)

    @property
    def tang_lg(self) -> float | None:
        return self._tang(self.lg, self.lg_ck)

    @property
    def tang_khach(self) -> float | None:
        return self._tang(self.so_khach, self.so_khach_ck)

    @staticmethod
    def _ty_suat(dt, lg) -> float | None:
        if dt is None or dt <= 0 or lg is None:
            return None
        return lg / dt

    @property
    def ty_suat(self) -> float | None:
        return self._ty_suat(self.dt, self.lg)

    @property
    def ty_suat_ck(self) -> float | None:
        return self._ty_suat(self.dt_ck, self.lg_ck)

    @property
    def chenh_ty_suat(self) -> float | None:
        """Chênh lệch tỷ suất tính bằng ĐIỂM PHẦN TRĂM (hiệu số), không phải
        tỷ lệ phần trăm — spec §5.2: "▲ 0,8 điểm", khác cách đọc %."""
        a, b = self.ty_suat, self.ty_suat_ck
        return None if a is None or b is None else a - b


@dataclass
class CungKy(_SoCungKy):
    """Một dòng `mart.ky_cung_ky` — kỳ hiện tại so với cùng kỳ năm trước,
    CHỈ TRÊN CÁC THÁNG ĐỐI CHIẾU (không phải cả kỳ, xem migration 029 §3.4)."""
    so_thang: int
    tu: str | None
    den: str | None
    dt: int | None
    lg: int | None
    so_khach: int | None
    dt_ck: int | None
    lg_ck: int | None
    so_khach_ck: int | None


@dataclass
class NganhThang:
    """Một dòng `mart.ban_theo_nganh_thang_so_sanh` — cho bản đồ nhiệt."""
    thang: str
    nganh: str
    doanh_thu: int
    dt_cung_ky: int | None
    co_cung_ky: bool
    tang_truong: float | None


@dataclass
class NganhKy:
    """Một dòng `mart.nganh_ky_cung_ky` — cho khối "ngành kéo lên/xuống"."""
    nganh: str
    doanh_thu: int
    lai_gop: int
    dt_doi_chieu: int | None
    dt_cung_ky: int | None
    chenh_lech: int | None
    tang_truong: float | None


@dataclass
class KhachTapTrung:
    """Một dòng `mart.tap_trung_khach` — một khách trên biểu đồ Pareto."""
    ma: str
    ten: str
    doanh_thu: int
    thu_hang: int
    ty_trong: float | None
    luy_ke: float | None


@dataclass
class TapTrung:
    """20 khách doanh thu cao nhất của kỳ, kèm tổng số khách có doanh thu và
    luỹ kế tại hạng 10 — con số cho câu tóm tắt "10 khách lớn nhất = X% doanh
    thu, trên N khách"."""
    dong: list[KhachTapTrung]
    so_khach: int
    luy_ke_top10: float | None


@dataclass
class BaoCao:
    ky: Ky
    moi_ky: list[Ky]
    thang: list[O]
    hang: list[dict]
    nhan_vien: list[dict]
    khong_co_du_lieu: bool = False
    canh_bao: list[str] = field(default_factory=list)
    # Đợt 5b — trường mới, mặc định rỗng/None để nhánh "không có dữ liệu"
    # vẫn dựng được BaoCao mà không phải viết nhánh riêng cho từng trường.
    cung_ky: CungKy | None = None
    nganh_thang: list[NganhThang] = field(default_factory=list)
    nganh_ky: list[NganhKy] = field(default_factory=list)
    tap_trung: TapTrung | None = None
    hang_theo_nganh: list[dict] = field(default_factory=list)


def _ky_tu_dong(r) -> Ky:
    return Ky(company_fy=r[0], so_ky=r[1], nhan=r[2], ngay_dau=r[3], ngay_cuoi=r[4],
              so_thang=r[5], doanh_thu=int(r[6] or 0), lai_gop=int(r[7] or 0),
              ty_suat=float(r[8]) if r[8] is not None else None,
              so_khach=r[9], so_phieu=r[10])


def _cung_ky_tu_dong(r) -> CungKy:
    # Chỉ số cột: 11=so_thang_doi_chieu, 12=tu, 13=den, 14=dt, 15=lg,
    # 16=so_khach, 17=dt_ck, 18=lg_ck, 19=so_khach_ck — xem SELECT trong
    # tinh_bao_cao(). so_thang không bao giờ NULL vì mart.ky_cung_ky đã
    # coalesce về 0, nhưng `or 0` phòng khi LEFT JOIN không khớp company_fy
    # nào (không nên xảy ra — ky_cung_ky phủ mọi company_fy trong dải bán).
    return CungKy(so_thang=r[11] or 0, tu=r[12], den=r[13],
                  dt=int(r[14]) if r[14] is not None else None,
                  lg=int(r[15]) if r[15] is not None else None,
                  so_khach=r[16],
                  dt_ck=int(r[17]) if r[17] is not None else None,
                  lg_ck=int(r[18]) if r[18] is not None else None,
                  so_khach_ck=r[19])


def tinh_bao_cao(conn, company_fy: int | None = None) -> BaoCao:
    """Số liệu cho một kỳ kế toán. company_fy=None => kỳ GẦN NHẤT có dữ liệu."""
    # (1) Một câu lấy MỌI kỳ kèm cùng kỳ: LEFT JOIN mart.ky_cung_ky USING
    # (company_fy) thay vì hỏi riêng — gộp "kỳ" và "cùng kỳ" của gợi ý brief.
    dong_ky = conn.execute(
        """SELECT t.company_fy, t.company_fy_no, t.nhan, t.ngay_dau, t.ngay_cuoi,
                  t.so_thang_co_du_lieu, t.doanh_thu_thuan, t.lai_gop, t.ty_suat,
                  t.so_khach, t.so_phieu,
                  c.so_thang_doi_chieu, c.thang_dau_doi_chieu, c.thang_cuoi_doi_chieu,
                  c.dt, c.lg, c.so_khach, c.dt_ck, c.lg_ck, c.so_khach_ck
           FROM mart.tong_theo_ky t
           LEFT JOIN mart.ky_cung_ky c USING (company_fy)
           ORDER BY t.company_fy""").fetchall()
    moi_ky = [_ky_tu_dong(r) for r in dong_ky]

    if not moi_ky:
        trong = Ky(0, 0, "(chưa có dữ liệu)", 0, 0, None, 0, 0, 0, None, None)
        return BaoCao(ky=trong, moi_ky=[], thang=[], hang=[],
                      nhan_vien=[], khong_co_du_lieu=True)

    ky = next((k for k in moi_ky if k.company_fy == company_fy), moi_ky[-1])
    cung_ky = _cung_ky_tu_dong(
        next(r for r in dong_ky if r[0] == ky.company_fy))

    # (2) Tháng — thêm so_khach, dt_cung_ky vào câu ban_theo_thang_so_sanh
    # đang có: cả hai cột ĐÃ có sẵn trong view (so_khach qua `t.*`, dt_cung_ky
    # do chính view định nghĩa), chỉ là trước Task 2 chưa được SELECT ra.
    thang = [
        O(thang=r[0], doanh_thu=int(r[1] or 0), lai_gop=int(r[2] or 0),
          ty_suat=float(r[3]) if r[3] is not None else None,
          co_cung_ky=r[4], tang_truong=float(r[5]) if r[5] is not None else None,
          la_thang_chot=r[0].endswith("-07"), so_phieu=r[6], so_khach=r[7],
          dt_cung_ky=int(r[8]) if r[8] is not None else None)
        for r in conn.execute(
            """SELECT thang, doanh_thu_thuan, lai_gop, ty_suat, co_cung_ky,
                      tang_truong, so_phieu, so_khach, dt_cung_ky
               FROM mart.ban_theo_thang_so_sanh
               WHERE company_fy = %s ORDER BY thang""", (ky.company_fy,)).fetchall()
    ]

    # (3) Pareto 20 khách + tổng số khách có doanh thu trong CÙNG một câu:
    # count(*) OVER() sẽ đếm SAU LIMIT nếu đặt thẳng trong SELECT ngoài, nên
    # lấy max(thu_hang) bằng truy vấn con — vẫn một round-trip duy nhất.
    dong_tt = conn.execute(
        """SELECT customer_code, ten_khach, doanh_thu_thuan, thu_hang,
                  ty_trong, luy_ke,
                  (SELECT max(thu_hang) FROM mart.tap_trung_khach
                    WHERE company_fy = %s) AS tong_so_khach
           FROM mart.tap_trung_khach WHERE company_fy = %s
           ORDER BY thu_hang LIMIT 20""", (ky.company_fy, ky.company_fy)).fetchall()
    tap_trung = None
    if dong_tt:
        khach_tt = [KhachTapTrung(
            ma=r[0], ten=r[1], doanh_thu=int(r[2]),
            thu_hang=r[3],
            ty_trong=float(r[4]) if r[4] is not None else None,
            luy_ke=float(r[5]) if r[5] is not None else None) for r in dong_tt]
        hang_10 = next((k for k in khach_tt if k.thu_hang == 10), None)
        tap_trung = TapTrung(dong=khach_tt, so_khach=dong_tt[0][6] or 0,
                             luy_ke_top10=hang_10.luy_ke if hang_10 else None)

    # (4) Mọi mặt hàng của kỳ, dùng cho cây ô VÀ để suy ra bảng "hang" (top
    # 10 lãi gộp) bằng cách sắp xếp trong Python — tiết kiệm một lượt hỏi so
    # với hỏi riêng ORDER BY lai_gop DESC LIMIT 10 như bản cũ.
    hang_theo_nganh = [dict(zip(("ma", "ten", "nhom", "doanh_thu", "lai_gop",
                                 "ty_suat", "so_khach"), r)) for r in conn.execute(
        """SELECT product_code, ten_hang, food_category_name, doanh_thu_thuan,
                  lai_gop, ty_suat, so_khach_mua
           FROM mart.ban_theo_san_pham WHERE company_fy = %s""",
        (ky.company_fy,)).fetchall()]
    hang = sorted(hang_theo_nganh, key=lambda h: h["lai_gop"], reverse=True)[:TOP]

    # (5) Người phụ trách — không đổi.
    nhan_vien = [dict(zip(("ma", "doanh_thu", "lai_gop", "ty_suat", "so_khach",
                           "so_phieu"), r)) for r in conn.execute(
        """SELECT salesperson_code, doanh_thu_thuan, lai_gop, ty_suat, so_khach, so_phieu
           FROM mart.ban_theo_nhan_vien WHERE company_fy = %s
           ORDER BY doanh_thu_thuan DESC""", (ky.company_fy,)).fetchall()]

    # (6) Ngành × tháng — cho bản đồ nhiệt.
    nganh_thang = [NganhThang(
        thang=r[0], nganh=r[1], doanh_thu=int(r[2] or 0),
        dt_cung_ky=int(r[3]) if r[3] is not None else None,
        co_cung_ky=r[4],
        tang_truong=float(r[5]) if r[5] is not None else None) for r in conn.execute(
        """SELECT thang, nganh, doanh_thu_thuan, dt_cung_ky, co_cung_ky, tang_truong
           FROM mart.ban_theo_nganh_thang_so_sanh
           WHERE company_fy = %s ORDER BY nganh, thang""", (ky.company_fy,)).fetchall()]

    # (7) Ngành × kỳ — cho khối "ngành kéo doanh thu lên/xuống". KHÔNG gộp
    # với (6): câu gộp sẽ đánh giá lại mart.ban_theo_nganh_thang_so_sanh một
    # lần trực tiếp và một lần qua nganh_ky_cung_ky, đúng lớp lỗi CTE-trùng
    # đã ghi ở CLAUDE.md (xem spec §5 cuối).
    nganh_ky = [NganhKy(
        nganh=r[0], doanh_thu=int(r[1] or 0), lai_gop=int(r[2] or 0),
        dt_doi_chieu=int(r[3]) if r[3] is not None else None,
        dt_cung_ky=int(r[4]) if r[4] is not None else None,
        chenh_lech=int(r[5]) if r[5] is not None else None,
        tang_truong=float(r[6]) if r[6] is not None else None) for r in conn.execute(
        """SELECT nganh, doanh_thu_thuan, lai_gop, dt_doi_chieu, dt_cung_ky,
                  chenh_lech, tang_truong
           FROM mart.nganh_ky_cung_ky
           WHERE company_fy = %s ORDER BY chenh_lech""", (ky.company_fy,)).fetchall()]

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
    return BaoCao(ky=ky, moi_ky=moi_ky, thang=thang, hang=hang,
                  nhan_vien=nhan_vien, canh_bao=canh_bao, cung_ky=cung_ky,
                  nganh_thang=nganh_thang, nganh_ky=nganh_ky, tap_trung=tap_trung,
                  hang_theo_nganh=hang_theo_nganh)


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

def _pct_rong(tu_so, mau_so) -> float | None:
    """Phần trăm chiều rộng một thanh/vạch mốc tiến độ, KẸP về [0, 100].

    Hình học thuần tuý cho việc VẼ (cùng nếp `ve_bieu_do`/`ve_luy_ke`), không
    phải một định nghĩa chỉ số — con số ĐỌC ĐƯỢC đi kèm mỗi thanh vẫn lấy từ
    `tien_do`/`muc_tieu_den_hom_nay` gốc (không kẹp), chỉ riêng CHIỀU RỘNG là
    kẹp để không vẽ sai:
      * mẫu số 0 hoặc NULL (chưa đặt chỉ tiêu, hoặc đặt bằng 0) -> None,
        KHÔNG chia cho 0 — không thanh nào để vẽ.
      * tử số ÂM (赤伝 — phiếu đỏ, doanh thu một tháng có thể âm) kẹp về 0:
        không vẽ chiều rộng âm.
      * tử số vượt mẫu số (đã vượt chỉ tiêu) kẹp về 100: thanh không tràn
        khỏi khung.
    """
    if not mau_so:
        return None
    return max(0.0, min(float(tu_so or 0) / float(mau_so) * 100, 100.0))


@dataclass(frozen=True)
class TienDoNguoi:
    ma: str
    ten: str | None          # None = mã KHÔNG có trong core.dim_salesperson
    thuc_te: int
    muc_tieu: int | None
    muc_tieu_den_hom_nay: int | None
    tien_do: float | None
    cung_ky: int | None      # doanh thu cùng tháng năm trước, None nếu không có
    # [Vòng soát cuối 2, việc 1] Ba cột này đọc THẲNG từ
    # mart.tien_do_ngan_sach (028) — KHÔNG tính lại ở Python hay Jinja.
    # `co_cung_ky` là một sự thật về KHO (tháng M-12 có tồn tại doanh thu ở
    # BẤT KỲ ai không), KHÔNG phải về riêng người này — phân biệt "tháng
    # cùng kỳ không tồn tại trong kho" (False) với "tồn tại nhưng người này
    # bán 0 đồng" (True, `cung_ky` = 0). Vòng soát cuối 1 (027) từng đặt hai
    # cột này vào một view riêng lọc theo THÁNG ĐANG XÉT — sai: nó làm mất
    # dữ liệu cùng kỳ của đúng người "có chỉ tiêu mà 0 doanh thu tháng này",
    # một hồi quy thật so với bản Jinja cũ (xem migration 028). `tang_truong`
    # đã qua gate `> 0` ở view — không phải `n.thuc_te / n.cung_ky - 1` như
    # bản Jinja cũ nhất, thứ ăn cả mẫu số ÂM (赤伝) và in ra phần trăm NGƯỢC
    # DẤU. Template chỉ nhân 100 và định dạng.
    co_cung_ky: bool
    tang_truong: float | None

    @property
    def rong_thanh(self) -> float | None:
        """[Vòng soát cuối, việc 9] % chiều rộng thanh tiến độ của MỘT
        người, kẹp [0, 100]. `_pct_rong` trả None khi `muc_tieu` là 0/None —
        template không vẽ thanh nào cho người chưa được giao chỉ tiêu."""
        return _pct_rong(self.thuc_te, self.muc_tieu)

    @property
    def rong_moc(self) -> float | None:
        """Vị trí % của vạch mốc `muc_tieu_den_hom_nay` trên thanh của
        người này, kẹp [0, 100]."""
        return _pct_rong(self.muc_tieu_den_hom_nay, self.muc_tieu)


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

    @property
    def rong_thanh(self) -> float | None:
        """[Vòng soát cuối, việc 9] % chiều rộng thanh tiến độ TOÀN NHÓM,
        kẹp [0, 100]. None khi `muc_tieu` (tổng cả công ty) là 0 hoặc chưa
        đặt — cùng hàm `_pct_rong` dùng cho từng người, một công thức một
        chỗ."""
        return _pct_rong(self.thuc_te, self.muc_tieu)

    @property
    def rong_moc(self) -> float | None:
        """Vị trí % của vạch mốc `muc_tieu_den_hom_nay` trên thanh toàn
        nhóm, kẹp [0, 100]."""
        return _pct_rong(self.muc_tieu_den_hom_nay, self.muc_tieu)

    @property
    def pct_moc_chi_tieu(self) -> float | None:
        """[Vòng soát cuối 2, việc 4] % của mốc đến hôm nay so với chỉ tiêu,
        KHÔNG KẸP (khác `rong_moc`, thứ chỉ dùng cho chiều rộng CSS) — con
        số ĐỌC ĐƯỢC in cạnh thẻ KPI "Mốc đến hôm nay" và cạnh thanh tiến độ
        toàn nhóm. Trước bản sửa, công thức `muc_tieu_den_hom_nay / muc_tieu
        * 100` bị chép tay HAI LẦN trong bao_cao.html (thẻ KPI và nhãn thanh
        tiến độ) — hai bản chép của cùng một phép tính sẽ trôi khỏi nhau.
        `muc_tieu` là mẫu số của CHỈ TIÊU (CHECK >= 0 ở app.ngan_sach),
        không phải doanh thu — không có bẫy dấu ÂM như 赤伝, nên chỉ cần
        kiểm "khác 0/None", không cần gate `> 0` phức tạp như tang_truong.
        """
        if not self.muc_tieu or self.muc_tieu_den_hom_nay is None:
            return None
        return self.muc_tieu_den_hom_nay / self.muc_tieu * 100


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
    #
    # [Vòng soát cuối 2, việc 1+2] `cung_ky`/`co_cung_ky`/`tang_truong` đọc
    # THẲNG từ mart.tien_do_ngan_sach (028) — không qua CTE hay JOIN nào ở
    # đây nữa. Vòng soát cuối 1 (027) từng bọc chúng vào một view riêng
    # (`ban_theo_nhan_vien_thang_so_sanh`) rồi lọc theo THÁNG ĐANG XÉT — sai:
    # view đó chỉ có dòng cho (người, tháng) có DOANH THU THẬT tháng đó, nên
    # một người có chỉ tiêu mà 0 đồng THÁNG NÀY (đúng người mà FULL JOIN của
    # 026 tồn tại để giữ) mất luôn cả dữ liệu cùng kỳ NĂM NGOÁI — một hồi quy
    # thật so với bản Jinja cũ. 028 đặt lại ba cột này NGAY TRONG
    # mart.tien_do_ngan_sach — view duy nhất đã có sẵn đúng tập dòng (đã qua
    # FULL JOIN) — nên không cần CTE lọc-theo-tháng ở tầng gọi nữa.
    dong = conn.execute(
            """SELECT t.salesperson_code, s.ten, t.thuc_te, t.muc_tieu,
                      t.muc_tieu_den_hom_nay, t.tien_do,
                      t.cung_ky, t.co_cung_ky, t.tang_truong,
                      t.ngay_kd, t.ngay_kd_da_qua
               FROM mart.tien_do_ngan_sach t
               LEFT JOIN core.dim_salesperson s
                      ON s.salesperson_code = t.salesperson_code
               WHERE t.thang = %s
               ORDER BY t.salesperson_code""", (thang,)).fetchall()

    nguoi = [TienDoNguoi(
        ma=x[0], ten=x[1], thuc_te=int(x[2] or 0),
        muc_tieu=int(x[3]) if x[3] is not None else None,
        muc_tieu_den_hom_nay=int(x[4]) if x[4] is not None else None,
        tien_do=float(x[5]) if x[5] is not None else None,
        cung_ky=int(x[6]) if x[6] is not None else None,
        co_cung_ky=bool(x[7]),
        tang_truong=float(x[8]) if x[8] is not None else None) for x in dong]
    # Tháng không có dòng nào (chọn một kỳ đã qua mà tháng cuối kỳ không có
    # doanh thu lẫn chỉ tiêu) -> 0/0. Khi đó `co_ngan_sach` cũng FALSE nên
    # màn hình hiện khối "chưa đặt chỉ tiêu", không hiện bộ đếm ngày.
    ngay_kd, ngay_kd_da_qua = (dong[0][9], dong[0][10]) if dong else (0, 0)

    # Luỹ kế 12 tháng của kỳ, VÀ tổng cả công ty của tháng đang xét — cùng một
    # câu. Alias bảng nguồn là `b`: câu này chỉ CỘNG DỒN các cột mart đã tính
    # sẵn (thuc_te, muc_tieu, muc_tieu_den_hom_nay) và chia hai tổng đó để ra
    # tiến độ công ty — không định nghĩa lại công thức nào, hỏi hẳn SQL thay
    # vì Python để không có phép cộng/chia chỉ số nào lọt vào phía Python.
    # `nullif(sum(b.muc_tieu), 0)` cho tiến độ NULL khi tổng chỉ tiêu bằng 0,
    # cùng nếp `nullif` mà mart.tien_do_ngan_sach đã dùng cho từng dòng.
    thang_ky = thang_cua_ky(ky)
    theo_thang = {x[0]: x[1:] for x in conn.execute(
        """SELECT thang, sum(b.thuc_te), sum(b.muc_tieu),
                  sum(b.muc_tieu_den_hom_nay),
                  sum(b.thuc_te)::numeric / nullif(sum(b.muc_tieu), 0)
           FROM mart.tien_do_ngan_sach b WHERE company_fy = %s
           GROUP BY thang""", (ky,)).fetchall()}

    luy_ke, c_tt, c_ns = [], 0, 0
    for th in thang_ky:
        row = theo_thang.get(th)
        tt = int(row[0] or 0) if row else 0
        ns = int(row[1]) if row and row[1] is not None else None
        c_tt += tt
        c_ns += ns or 0
        luy_ke.append(MocLuyKe(
            thang=th,
            thuc_te=c_tt if th <= thang_hom_nay else None,
            # [Vòng soát cuối, việc 10] `if c_ns else None` coi 0 và "chưa có
            # gì" là MỘT — đúng cái lẫn "chỉ tiêu bằng 0 khác chưa đặt" mà cả
            # đợt 5a này tồn tại để phân biệt (app.ngan_sach CHECK >= 0 cho
            # phép muc_tieu = 0 là một giá trị ĐÃ ĐẶT). Luỹ kế chỉ tiêu đúng
            # bằng 0 (ví dụ mọi tháng tới giờ đều đặt = 0) là một sự thật hợp
            # lệ, không phải "chưa có dữ liệu để vẽ" — `is not None` giữ
            # đúng con số 0 đó trên đường luỹ kế thay vì bỏ nó khỏi biểu đồ.
            ngan_sach=c_ns if c_ns is not None else None))

    # Tổng công ty của tháng đang xét: dòng CHÍNH LÀ một trong những dòng
    # `theo_thang` vừa gộp — không hỏi thêm câu nào, không cộng gì ở Python.
    r_thang = theo_thang.get(thang)
    tong_tt = int(r_thang[0] or 0) if r_thang else 0
    tong_mt = int(r_thang[1]) if r_thang and r_thang[1] is not None else None
    tong_moc = int(r_thang[2]) if r_thang and r_thang[2] is not None else None
    tien_do_ct = float(r_thang[3]) if r_thang and r_thang[3] is not None else None

    return TienDoNganSach(
        company_fy=ky, thang=thang, hom_nay=hom_nay,
        ngay_kd=ngay_kd, ngay_kd_da_qua=ngay_kd_da_qua,
        thuc_te=tong_tt, muc_tieu=tong_mt,
        muc_tieu_den_hom_nay=tong_moc,
        tien_do=tien_do_ct,
        nguoi=nguoi, luy_ke=luy_ke, co_ngan_sach=tong_mt is not None)


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

    # [Vòng soát cuối, việc 10] Toạ độ trục hoành TÍNH SẴN ở đây, cùng nguyên
    # tắc với ve_bieu_do (hình học ở Python, template chỉ vẽ). Bản trước trả
    # `nhan` là một list chuỗi TRẦN không kèm toạ độ — template không biết đặt
    # nhãn vào đâu nên bỏ qua luôn, và biểu đồ luỹ kế không nói điểm nào là
    # tháng nào. Chỉ in tháng đầu/cuối và các mốc quý (company_fy_month chia
    # hết cho 3) — in đủ 12 nhãn trên một trục 720px sẽ đè lên nhau.
    nhan = [{"x": round(LE_T + i * buoc, 1), "thang": m.thang,
             "hien": i == 0 or i == len(td.luy_ke) - 1 or (i + 1) % 3 == 0}
            for i, m in enumerate(td.luy_ke)]

    return {"co": True, "rong": RONG, "cao": CAO, "dinh": dinh,
            "thuc_te": _duong(lambda m: m.thuc_te),
            "ngan_sach": _duong(lambda m: m.ngan_sach),
            "nhan": nhan}
