"""Dữ liệu cho `/` — dashboard chung của cả công ty (đợt 5b Task 5).

Một bố cục cho mọi người: không kéo thả, không chọn khối, không cài đặt theo
vai trò. Module này KHÔNG định nghĩa chỉ số nào — nó chỉ gọi lại các hàm/view
đã có (`mart.thang_den_hom_nay`, `mart.ban_theo_ngay`, `mart.khach_360`,
`kome.khach_hang.can_xu_ly`, `kome.bao_cao.tien_do_ngan_sach`,
`kome.san_pham.kho_hang`) và gói chúng lại thành một khối cho template — cùng
nguyên tắc "không tự mở kết nối, không chép lại công thức" của kome/bao_cao.py
và kome/khach_hang.py.

Trang `/` KHÔNG còn gọi `tinh_bao_cao`: hàm đó chạy trọn 5 lượt hỏi của trang
báo cáo chỉ để lấy ba con số của kỳ kế toán, trong khi dashboard cần con số
THÁNG đến hôm nay (mart.thang_den_hom_nay), một khái niệm khác hẳn.
"""
from dataclasses import dataclass
from datetime import date

from kome.bao_cao import TienDoNganSach, _SoCungKy, tien_do_ngan_sach
from kome.khach_hang import Khach, can_xu_ly
from kome.san_pham import kho_hang

# Bốn nhóm hiện trên thanh sức khoẻ — CÙNG bốn nhóm bản `/` cũ đã hiện.
# KHÔNG có 'chua_du_lich_su': đó là "chưa đủ dữ liệu để nói", không phải một
# tình trạng quan hệ, và trộn nó vào thanh sẽ pha loãng ba nhóm còn lại.
NHOM_SUC_KHOE = ("canh_bao", "da_roi_bo", "binh_thuong", "ngung_giao_dich")

# Bao nhiêu khách/lô hiện trên trang chủ — 5 vừa một cột không cuộn, "Xem tất
# cả" dẫn sang trang đầy đủ (/can-xu-ly, /kho-hang).
GIOI_HAN_CAN_GOI = 5
GIOI_HAN_CAN_HAN = 5

# 60 ngày cuối cho khối xu hướng: 30 ngày để vẽ cột + 30 ngày liền trước để vẽ
# đường so sánh (kome.ve_phan_tich.ve_xu_huong).
SO_NGAY_XU_HUONG = 60


@dataclass
class ThangNay(_SoCungKy):
    """Một dòng `mart.thang_den_hom_nay` — tháng hiện hành (từ mùng 1 đến
    hôm nay) so với CÙNG DẢI NGÀY năm trước, KHÔNG phải cả tháng năm trước.

    Cùng bộ cột (`dt`/`lg`/`so_khach`/`..._ck`) và cùng công thức tăng
    trưởng/tỷ suất với `kome.bao_cao.CungKy` — trộn sẵn qua mixin `_SoCungKy`
    thay vì chép lại các property đó lần thứ hai (xem docstring `_SoCungKy`).
    """
    thang: str
    tu_ngay: date
    den_ngay: date
    tu_ngay_ck: date
    den_ngay_ck: date
    dt: int
    lg: int
    so_khach: int
    so_phieu: int
    co_cung_ky: bool
    dt_ck: int | None
    lg_ck: int | None
    so_khach_ck: int | None


@dataclass
class TongQuan:
    thang_nay: ThangNay | None      # None khi kho chưa có dòng bán nào
    ngay: list[tuple[date, int]]    # 60 ngày cuối (<= hôm nay), CŨ -> MỚI
    dem: dict[str, int]             # trang_thai (mart.khach_360) -> số khách
    can_goi: list[Khach]            # 5 khách đầu của can_xu_ly()
    ngan_sach: "TienDoNganSach | None"
    can_han: list[dict]             # 5 lô đầu của Kho.can_han
    so_qua_han: int                 # len(Kho.qua_han)


def doan_suc_khoe(dem: dict[str, int]) -> list[dict]:
    """Chiều rộng % mỗi đoạn của thanh sức khoẻ khách hàng — hình học HIỂN
    THỊ thuần tuý (count / tổng bốn nhóm), không phải một chỉ số mới; công
    thức trạng thái thật nằm ở `mart.khach_360.trang_thai`. Tính ở Python
    (không phải Jinja) — cùng nguyên tắc "hình học ở tầng Python, template
    chỉ vẽ" của `kome.bao_cao`/`kome.ve_phan_tich`.

    Nhóm có 0 khách vẫn có mặt trong kết quả (rong=0) để template quyết định
    có vẽ đoạn đó hay không, không phải đoán từ việc thiếu khoá.
    """
    so = {n: dem.get(n, 0) for n in NHOM_SUC_KHOE}
    tong = sum(so.values()) or 1
    return [{"nhom": n, "so": so[n], "rong": so[n] / tong * 100} for n in NHOM_SUC_KHOE]


def _thang_nay_tu_dong(r) -> ThangNay:
    return ThangNay(
        thang=r[0], tu_ngay=r[1], den_ngay=r[2], tu_ngay_ck=r[3], den_ngay_ck=r[4],
        dt=int(r[5] or 0), lg=int(r[6] or 0), so_khach=r[7], so_phieu=r[8],
        co_cung_ky=r[9],
        dt_ck=int(r[10]) if r[10] is not None else None,
        lg_ck=int(r[11]) if r[11] is not None else None,
        so_khach_ck=r[12])


def tong_quan(conn, sale: str | None) -> TongQuan:
    """Số liệu cho `/`. `sale`: mặc định tiện dụng theo người đăng nhập —
    CHỈ áp cho khối "cần gọi hôm nay" (đúng nếp `/can-xu-ly`). Các khối số
    tổng (tháng, xu hướng, sức khoẻ, ngân sách, hàng cận hạn) KHÔNG lọc theo
    sale: dashboard trả lời "công ty đang thế nào", không phải "khách của
    riêng tôi đang thế nào" — câu hỏi đó đã có nhà ở /khach-hang?nv= và
    /bao-cao (bảng theo người phụ trách).

    Mỗi khối một câu lệnh riêng (không gộp): các view đứng sau khác hình,
    gộp chỉ để tiết kiệm vài chục ms là đổi lấy sự rõ ràng. Ngân sách CẢ
    TRANG (gồm cả tinh_tuoi ở tầng route) là <= 11 lượt hỏi — có test đếm.
    """
    r = conn.execute(
        """SELECT thang, tu_ngay, den_ngay, tu_ngay_ck, den_ngay_ck,
                  dt, lg, so_khach, so_phieu, co_cung_ky, dt_ck, lg_ck, so_khach_ck
           FROM mart.thang_den_hom_nay""").fetchone()
    thang_nay = _thang_nay_tu_dong(r) if r is not None else None

    # DESC LIMIT rồi đảo ngược ở Python: lấy đúng 60 ngày CUỐI của dải (view
    # đã nối từ lịch nên ngày không bán vẫn có dòng số 0 — không có khoảng
    # trống để lo). Đảo ngược để trả về CŨ -> MỚI, đúng thứ tự vẽ trục hoành.
    ngay = [(row[0], int(row[1] or 0)) for row in conn.execute(
        """SELECT ngay, doanh_thu_thuan FROM mart.ban_theo_ngay
           ORDER BY ngay DESC LIMIT %s""", (SO_NGAY_XU_HUONG,)).fetchall()][::-1]

    dem = dict(conn.execute(
        "SELECT trang_thai, count(*) FROM mart.khach_360 GROUP BY 1").fetchall())

    can_goi = can_xu_ly(conn, gioi_han=GIOI_HAN_CAN_GOI, sale=sale)

    ngan_sach = tien_do_ngan_sach(conn)

    kho = kho_hang(conn)

    return TongQuan(
        thang_nay=thang_nay, ngay=ngay, dem=dem, can_goi=can_goi,
        ngan_sach=ngan_sach, can_han=kho.can_han[:GIOI_HAN_CAN_HAN],
        so_qua_han=len(kho.qua_han))
