"""Khách hàng: danh sách, tìm kiếm, và hồ sơ 360°.

Như kome/bao_cao.py: KHÔNG định nghĩa chỉ số ở đây, không tự mở kết nối.
Mọi công thức nằm ở schema `mart` (migration 015, 016).
"""
from dataclasses import dataclass, field
from datetime import date

MOI_TRANG = 50

# Nhãn tiếng Việt cho `mart.khach_360.trang_thai`, kèm màu để màn hình đọc được
# bằng mắt chứ không phải bằng cách tra bảng. Thứ tự ở đây LÀ thứ tự ưu tiên
# hiển thị: việc cần làm đứng trước, việc không làm gì được đứng sau.
TRANG_THAI = {
    "canh_bao":        ("Cần gọi lại", "canh"),
    "da_roi_bo":       ("Đã rời bỏ", "loi"),
    "binh_thuong":     ("Bình thường", "ok"),
    "chua_du_lich_su": ("Chưa đủ lịch sử", "nhat"),
    "ngung_giao_dich": ("Ngừng giao dịch", "nhat"),
}

# Cột được phép sắp xếp. Danh sách trắng, KHÔNG ghép thẳng tham số URL vào câu
# SQL — đó là đường mở cho SQL injection, và trang này sắp nằm trên Internet.
SAP_XEP = {
    "doanh_thu": "doanh_thu_thuan DESC NULLS LAST",
    "lai_gop":   "lai_gop DESC NULLS LAST",
    "ty_suat":   "ty_suat DESC NULLS LAST",
    "im_lang":   "ty_le_im_lang DESC NULLS LAST",
    "gan_nhat":  "lan_cuoi DESC NULLS LAST",
    "ten":       "ten ASC",
}


@dataclass
class Khach:
    ma: str
    ten: str
    tinh: str | None
    thanh_pho: str | None
    dien_thoai: str | None
    nguoi_phu_trach: str | None
    doanh_thu: int
    lai_gop: int
    ty_suat: float | None
    lan_cuoi: date | None
    so_ngay_im_lang: int | None
    nhip_ngay: float | None
    ty_le_im_lang: float | None
    trang_thai: str
    dau_hieu_obc: str | None

    @property
    def nhan_trang_thai(self) -> str:
        return TRANG_THAI.get(self.trang_thai, (self.trang_thai, "nhat"))[0]

    @property
    def mau(self) -> str:
        return TRANG_THAI.get(self.trang_thai, ("", "nhat"))[1]


@dataclass
class TrangKhach:
    khach: list[Khach]
    tong: int
    trang: int
    so_trang: int
    tim: str
    loc: str
    sap: str
    dem_trang_thai: dict[str, int]
    # Mã sale đang lọc (None = đang xem tất cả), tên người đó để trang nói rõ
    # "đang lọc theo ai", và tổng số khách TOÀN CÔNG TY cho nút "Xem tất cả".
    sale: str | None = None
    ten_sale: str | None = None
    tong_tat_ca: int = 0


@dataclass
class HoSo:
    khach: Khach
    ho_so: dict
    thang: list[dict]
    mat_hang: list[dict]
    da_ngung_mua: list[dict]
    lan_mua_gan_day: list[dict]


_COT = """customer_code, ten, prefecture, city, phone, salesperson_code,
          doanh_thu_thuan, lai_gop, ty_suat, lan_cuoi, so_ngay_im_lang,
          nhip_ngay, ty_le_im_lang, trang_thai, dau_hieu_obc"""


def _khach(r) -> Khach:
    return Khach(ma=r[0], ten=r[1], tinh=r[2], thanh_pho=r[3], dien_thoai=r[4],
                 nguoi_phu_trach=r[5], doanh_thu=int(r[6] or 0),
                 lai_gop=int(r[7] or 0),
                 ty_suat=float(r[8]) if r[8] is not None else None,
                 lan_cuoi=r[9], so_ngay_im_lang=r[10],
                 nhip_ngay=float(r[11]) if r[11] is not None else None,
                 ty_le_im_lang=float(r[12]) if r[12] is not None else None,
                 trang_thai=r[13], dau_hieu_obc=r[14])


def danh_sach(conn, tim: str = "", loc: str = "", sap: str = "doanh_thu",
              trang: int = 1, sale: str | None = None,
              ten_sale: str | None = None) -> TrangKhach:
    """Danh sách khách, có tìm kiếm và lọc theo trạng thái.

    `sale` là MẶC ĐỊNH TIỆN DỤNG, không phải hàng rào bảo mật: công ty năm
    người, ai cũng biết khách của ai, và trang luôn có một liên kết bỏ lọc.
    Không có kiểm quyền nào ở đây, và đó là cố ý — xem đặc tả đợt 3 §5.
    """
    dieu_kien, tham_so = [], []
    if tim.strip():
        # Tìm theo tên, mã, điện thoại hoặc địa chỉ cùng lúc — nhân viên không
        # nhớ mình đang có mảnh thông tin nào trong tay.
        dieu_kien.append("""(ten ILIKE %s OR customer_code ILIKE %s
                             OR phone ILIKE %s OR address ILIKE %s
                             OR city ILIKE %s)""")
        tham_so += [f"%{tim.strip()}%"] * 5
    if loc in TRANG_THAI:
        dieu_kien.append("trang_thai = %s")
        tham_so.append(loc)
    if sale:
        dieu_kien.append("salesperson_code = %s")
        tham_so.append(sale)
    where = ("WHERE " + " AND ".join(dieu_kien)) if dieu_kien else ""

    tong = conn.execute(
        f"SELECT count(*) FROM mart.khach_360 {where}", tham_so).fetchone()[0]

    thu_tu = SAP_XEP.get(sap, SAP_XEP["doanh_thu"])
    trang = max(1, trang)
    rows = conn.execute(
        f"""SELECT {_COT} FROM mart.khach_360 {where}
            ORDER BY {thu_tu} LIMIT %s OFFSET %s""",
        tham_so + [MOI_TRANG, (trang - 1) * MOI_TRANG]).fetchall()

    # Số lượng từng trạng thái KHÔNG theo bộ lọc trạng thái đang bật — nếu
    # không thì bấm vào "Cần gọi lại" xong các con số khác về 0 hết. Nhưng
    # CÓ theo bộ lọc sale: đang xem khách của mình mà bộ đếm khoe con số toàn
    # công ty thì bấm vào một mục xong ra danh sách ngắn hơn hẳn số vừa đọc.
    dem_dk = "WHERE salesperson_code = %s" if sale else ""
    dem = dict(conn.execute(
        f"SELECT trang_thai, count(*) FROM mart.khach_360 {dem_dk} GROUP BY 1",
        [sale] if sale else []).fetchall())

    # Số THẬT cho liên kết "Xem tất cả khách (N)". Viết cứng một con số ở
    # template là để nó sai đúng vào ngày công ty có thêm khách.
    tong_tat_ca = conn.execute("SELECT count(*) FROM mart.khach_360").fetchone()[0]

    return TrangKhach(
        khach=[_khach(r) for r in rows], tong=tong, trang=trang,
        so_trang=max(1, -(-tong // MOI_TRANG)), tim=tim, loc=loc, sap=sap,
        dem_trang_thai=dem, sale=sale, ten_sale=ten_sale, tong_tat_ca=tong_tat_ca)


def ho_so(conn, ma: str) -> HoSo | None:
    """Hồ sơ 360° của một khách. None nếu mã không tồn tại."""
    r = conn.execute(
        f"SELECT {_COT} FROM mart.khach_360 WHERE customer_code = %s", (ma,)).fetchone()
    if r is None:
        return None
    k = _khach(r)

    chi_tiet = conn.execute(
        """SELECT branch_name, postcode, address, rank_code, category_code,
                  closing_day_code, price_level_code, spot_flag, lan_dau,
                  so_lan_mua, so_phieu, gia_tri_tb_moi_lan
           FROM mart.khach_360 WHERE customer_code = %s""", (ma,)).fetchone()
    ho = dict(zip(("chi_nhanh", "buu_chinh", "dia_chi", "hang", "phan_loai",
                   "ngay_chot", "bac_gia", "vang_lai", "lan_dau", "so_lan_mua",
                   "so_phieu", "gia_tri_tb"), chi_tiet))

    thang = [dict(zip(("thang", "doanh_thu", "lai_gop", "so_lan"), t))
             for t in conn.execute(
        """SELECT thang, doanh_thu_thuan, lai_gop, so_lan_mua
           FROM mart.khach_theo_thang WHERE customer_code = %s
           ORDER BY thang""", (ma,)).fetchall()]

    # `nhip` là numeric từ Postgres — ép sang int khi HIỂN THỊ ở template
    # (`|int`), không ép ở đây: None phải đi qua nguyên vẹn để template hiện
    # "—" cho mã chưa đủ lịch sử để tính nhịp.
    mat_hang = [dict(zip(("ma", "ten", "doanh_thu", "lai_gop", "so_luong",
                          "so_lan", "lan_cuoi", "nhip", "du_kien"), h))
                for h in conn.execute(
        """SELECT product_code, ten_hang, doanh_thu_thuan, lai_gop, so_luong,
                  so_lan, lan_cuoi, nhip_ngay, du_kien_lan_toi
           FROM mart.khach_mat_hang WHERE customer_code = %s
           ORDER BY doanh_thu_thuan DESC LIMIT 15""", (ma,)).fetchall()]

    # Mặt hàng khách TỪNG mua đều rồi NGỪNG hẳn. Đây là tín hiệu sớm hơn nhiều
    # so với việc khách ngừng mua toàn bộ: họ đang chuyển dần sang nhà cung cấp
    # khác, từng món một, và không ai để ý cho tới khi mất luôn khách.
    da_ngung = [dict(zip(("ma", "ten", "so_lan", "lan_cuoi", "doanh_thu", "tre"), h))
                for h in conn.execute(
        """SELECT h.product_code, h.ten_hang, h.so_lan, h.lan_cuoi,
                  h.doanh_thu_thuan, h.tre_ngay
           FROM mart.khach_mat_hang h, mart.moc_thoi_gian m
           WHERE h.customer_code = %s
             AND h.so_lan >= 3
             AND m.hom_nay - h.lan_cuoi > 90
           ORDER BY h.doanh_thu_thuan DESC LIMIT 10""", (ma,)).fetchall()]

    gan_day = [dict(zip(("ngay", "so_phieu", "doanh_thu", "lai_gop"), l))
               for l in conn.execute(
        """SELECT sales_date, count(*), sum(doanh_thu_thuan), sum(lai_gop)
           FROM mart.lan_mua WHERE customer_code = %s
           GROUP BY sales_date ORDER BY sales_date DESC LIMIT 12""", (ma,)).fetchall()]

    return HoSo(khach=k, ho_so=ho, thang=thang, mat_hang=mat_hang,
                da_ngung_mua=da_ngung, lan_mua_gan_day=gan_day)


def can_xu_ly(conn, gioi_han: int = 100, sale: str | None = None) -> list[Khach]:
    """Danh sách việc cần làm: khách đang rời đi, xếp theo tiền đang mất.

    Xếp theo DOANH THU chứ không theo mức độ im lặng: gọi lại khách ¥5 triệu
    im 3 lần nhịp thì đáng hơn khách ¥50.000 im 10 lần nhịp, dù con số thứ hai
    trông đáng báo động hơn.

    `sale`: mặc định tiện dụng, như danh_sach() — không phải hàng rào.
    """
    dieu_kien = "AND salesperson_code = %s" if sale else ""
    tham_so = ([sale] if sale else []) + [gioi_han]
    return [_khach(r) for r in conn.execute(
        f"""SELECT {_COT} FROM mart.khach_360
            WHERE trang_thai IN ('canh_bao', 'da_roi_bo') {dieu_kien}
            ORDER BY doanh_thu_thuan DESC NULLS LAST LIMIT %s""",
        tham_so).fetchall()]


def ve_duong(thang: list[dict], rong: int = 640, cao: int = 120) -> dict:
    """Đường doanh thu theo tháng cho hồ sơ 360°. Tự tính toạ độ — không dùng
    thư viện JavaScript nào (xem ghi chú ở kome/bao_cao.py)."""
    if not thang:
        return {"co": False}
    le = 6
    dinh = max((t["doanh_thu"] or 0) for t in thang) or 1
    n = len(thang)
    buoc = (rong - 2 * le) / max(n - 1, 1)
    diem = [(round(le + i * buoc, 1),
             round(cao - le - (cao - 2 * le) * ((t["doanh_thu"] or 0) / dinh), 1), t)
            for i, t in enumerate(thang)]
    return {"co": True, "rong": rong, "cao": cao, "diem": diem,
            "duong": " ".join(f"{x},{y}" for x, y, _ in diem),
            "vung": f"{le},{cao-le} " + " ".join(f"{x},{y}" for x, y, _ in diem)
                    + f" {round(le + (n-1)*buoc, 1)},{cao-le}",
            "dinh": dinh}
