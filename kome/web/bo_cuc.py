"""Bố cục trang Tổng quan theo từng tài khoản (migration 034).

Từ 2026-09-29 (đặc tả 2026-09-29-tong-quan-luoi-12-cot-design.md): lưới TOẠ ĐỘ
12 cột, hàng 40px — mỗi khối có x, y, rộng 3–12, cao 2–16 và NÉN DỌC (khối nổi
lên tới khi chạm khối phía trên, `nen`). Bố cục cũ (034/056: thứ tự + đơn vị 3
cột, không có x/y) vẫn đọc được — đổi đơn vị rồi xếp chỗ theo thứ tự (`_xep_dau`).
Mỗi ô còn mang `xem` = cách xem đang chọn của khối (`CACH_XEM`). Lưu ở
`app.bang_tong_quan.bo_cuc` (056); gói thiết kế ghi localStorage — xem 034.

Module này KHÔNG tin dữ liệu đến từ trình duyệt: mọi bố cục đi qua
`chuan_hoa` cả lúc GHI lẫn lúc ĐỌC. Lúc đọc là để dòng lưu từ trước khi code
thêm một khối mới vẫn dùng được — khối mới tự nối vào cuối, thay vì như gói
thiết kế (bố cục lưu thiếu một khối là vứt cả bố cục về mặc định).

Thêm một khối: thêm MỘT dòng vào KHOI, rồi hoặc một hàm dữ liệu trong
kome/khoi_tong_quan.py::KHOI + thành phần trong giao_dien/src/tong_quan/khoi.tsx
(VE), hoặc một câu "chưa có dữ liệu" trong khoi_tong_quan.CHUA_CO. Có test canh.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace

from kome import man_chua_co as MCC
from kome.nguon_dung import tinh_nang

# Số cột của lưới — đổi là đổi cả giao_dien/src/tong_quan/luoi_logic.ts (COT) và CSS .luoi-tq.
RONG_TOI_DA = 12
RONG_TOI_THIEU = 3
CAO_TOI_DA = 16
CAO_TOI_THIEU = 2
Y_TOI_DA = 400     # chặn bố cục rác đẩy một khối xuống hàng nghìn
# Đơn vị của bố cục CŨ (lưới 3 cột, hàng 150px): 1 cột cũ = 4 cột mới, 1 hàng cũ
# ≈ 3 hàng mới (3 × 40 + 2 × 12 = 144px).
DOI_CU = (4, 3)

# (mã, nhãn, rộng, cao, nhóm, mô tả) — rộng/cao theo lưới 12 cột (từ 2026-09-29 = số cũ × DOI_CU) — ĐÚNG danh mục `MODULES` và thứ tự /
# kích thước `BO_CUC_MAC_DINH` của Dashboard.dc.html (21 khối) + khối tháng (036). Khối không có
# nguồn dữ liệu vẫn có mặt (khung "chưa có dữ liệu", kome/khoi_tong_quan.py
# ::CHUA_CO) — lựa chọn của chủ doanh nghiệp, đặc tả giao diện React §2.
# Chiều cao LỆCH CÓ CHỦ Ý khỏi BO_CUC_MAC_DINH của gói thiết kế từ 2026-09-28 (đặc tả
# 2026-09-28-tong-quan-it-chu-design.md §5): khối từng chứa bảng thấp còn 2, khối chưa có
# nguồn còn 1. Bố cục đã lưu (app.bang_tong_quan) không tự đổi.
_KHOI_DAY_DU = (
    ("kpi", "Chỉ số hôm nay", 12, 3, "tong_quan", "Sáu con số mở đầu ngày, mỗi ô dẫn thẳng tới màn hình của nó"),
    ("ns_thang", "Tiến độ ngân sách tháng", 12, 3, "tong_quan", "Từng sale so với mốc đáng lẽ đạt tới hôm nay"),
    ("theo_thang", "Kết quả theo từng tháng", 12, 6, "tong_quan", "12 tháng của kỳ kế toán so ngân sách và cùng kỳ"),
    ("viec_hom_nay", "Việc cần làm hôm nay", 8, 6, "tong_quan", "Gom việc từ khách cần gọi, hẹn gọi lại, kho và dữ liệu"),
    # Ngoài 21 khối của gói thiết kế — thêm 2026-09-23 theo yêu cầu chủ DN
    # ("công ty chạy doanh thu theo tháng"), nguồn: mart.khach_thang_nay (036).
    ("thang_nay_chua_mua", "Tháng này chưa mua", 4, 6, "khach_hang", "Khách mua đều hằng tháng mà tháng này chưa có đơn"),
    # Ngoài gói thiết kế — thêm 2026-09-26 theo yêu cầu chủ DN: khách mới theo
    # ngày đăng ký đọc từ mã khách (mart.khach_moi_khoang, 044).
    ("khach_moi", "Khách mới đăng ký", 8, 6, "khach_hang", "Khách đăng ký trong khoảng xem, ai đã có đơn, ai chưa"),
    ("cong_no", "Tuổi nợ phải thu", 4, 6, "tien", "Chia 0–30 / 30–60 / trên 60 ngày và ai nợ lâu nhất"),
    ("xu_huong", "Xu hướng doanh thu", 8, 6, "tien", "Doanh thu ngày, có đường so sánh kỳ trước"),
    ("dong_tien", "Dòng tiền 8 tuần", 4, 3, "tien", "Tiền vào trừ tiền ra theo tuần và số dư dự kiến"),
    ("mua_hang", "Đơn đặt nhà cung cấp", 4, 3, "hang_hoa", "PO đang mở, đơn trễ hẹn và đơn chờ duyệt"),
    ("khieu_nai", "Trả hàng & khiếu nại", 4, 3, "hang_hoa", "Phiếu đang mở, quá hạn xử lý và chi phí bồi hoàn"),
    ("suc_khoe_khach", "Sức khoẻ khách hàng", 4, 3, "khach_hang", "Bao nhiêu khách khoẻ, cần theo dõi, đang rời bỏ"),
    ("danh_sach_khach", "Danh sách khách hàng", 12, 6, "khach_hang", "Doanh thu, nhịp mua và việc cần làm"),
    ("hang_sap_ve", "Sản phẩm sắp về kho", 12, 3, "hang_hoa", "Container đang trên đường và lô nào trễ hẹn"),
    ("han_su_dung", "Sản phẩm sắp hết hạn", 12, 6, "hang_hoa", "Lô cận date và giá trị tồn đang có rủi ro"),
    ("hieu_suat_nganh", "Hiệu suất theo ngành hàng", 8, 6, "thi_truong", "Tỷ trọng doanh thu và biên lãi gộp từng nhóm"),
    ("so_sanh_sale", "Doanh thu theo sale", 4, 6, "khach_hang", "Ai đang đạt, ai đang hụt ngân sách cá nhân"),
    ("tuong_quan", "Doanh thu × tần suất mua", 8, 6, "khach_hang", "Mỗi chấm một khách, thấy ngay ai to mà thưa đơn"),
    ("nhip_mua", "Tỷ lệ im lặng theo tuần", 4, 3, "khach_hang", "Khoảng cách giữa các đơn đang giãn ra hay thu lại"),
    ("bien_loi_nhuan", "Biên lợi nhuận theo quý", 8, 6, "tien", "Biên lãi gộp sáu quý gần nhất"),
    ("tang_truong", "Số khách đang mua", 4, 6, "khach_hang", "Số khách có đơn theo từng kỳ kế toán"),
    ("thoi_tiet", "Thời tiết 7 ngày tới", 8, 3, "thi_truong", "Nắng nóng đẩy bia và nước, mưa to ảnh hưởng lịch xe"),
    ("don_hang", "Nạp dữ liệu / phiếu gần nhất", 12, 6, "tong_quan", "Nhật ký nạp và các phiếu bán mới nhất"),
)
# Khối sống nhờ một tính năng mà công ty chưa dùng (kome/nguon_dung.py) không
# vào danh mục: không hiện, không có trong "Xem theo vai trò", bố cục đã lưu
# có nó thì `chuan_hoa` bỏ qua — bật lại nguồn là khối tự nối vào cuối.
KHOI_CAN = {"cong_no": "cong_no"}
_TN = tinh_nang()
# Khối CHƯA LÀM (kome/man_chua_co.py) cũng rời danh mục khi công tắc tắt — cùng nếp trên.
KHOI = tuple(k for k in _KHOI_DAY_DU if _TN.get(KHOI_CAN.get(k[0], ""), True)
             and (MCC.HIEN or k[0] not in MCC.KHOI))
_CO = {k[0] for k in KHOI}
NHOM = (("tat_ca", "Tất cả"), ("tong_quan", "Tổng quan"), ("tien", "Tiền"),
        ("khach_hang", "Khách hàng"), ("hang_hoa", "Hàng hóa"), ("thi_truong", "Thị trường"))
# "Xem theo vai trò" = một bộ khối hiện sẵn (VAI_TRO của gói thiết kế). Bấm là
# ÁP vào bố cục của chính mình — vẫn kéo/ẩn tiếp được, không phải phân quyền.
VAI_TRO = (
    ("giamdoc", "Giám đốc", ("kpi", "ns_thang", "theo_thang", "cong_no", "dong_tien", "xu_huong",
                             "bien_loi_nhuan", "hieu_suat_nganh", "so_sanh_sale", "mua_hang", "tang_truong",
                             "khach_moi")),
    ("kinhdoanh", "Trưởng phòng KD", ("kpi", "viec_hom_nay", "thang_nay_chua_mua", "khach_moi", "ns_thang", "theo_thang", "danh_sach_khach",
                                      "suc_khoe_khach", "nhip_mua", "tuong_quan", "so_sanh_sale",
                                      "xu_huong", "thoi_tiet")),
    ("ketoan", "Kế toán", ("kpi", "cong_no", "dong_tien", "theo_thang", "bien_loi_nhuan", "khieu_nai",
                           "don_hang", "xu_huong")),
    ("kho", "Kho & giao hàng", ("kpi", "viec_hom_nay", "hang_sap_ve", "han_su_dung", "mua_hang",
                                "khieu_nai", "thoi_tiet")),
)
VAI_TRO = tuple((a, b, tuple(x for x in c if x in _CO)) for a, b, c in VAI_TRO)
# Mã khối của bản Jinja (034, 6 khối) -> mã mới: bố cục đã lưu trước ngày đổi
# giao diện vẫn đọc được, không vứt đi.
MA_CU = {"chi_so": "kpi", "ngan_sach": "ns_thang", "suc_khoe": "suc_khoe_khach",
         "can_han": "han_su_dung", "can_goi": "viec_hom_nay"}


# Các CÁCH XEM của một khối (2026-09-29, ý 4 của chủ DN) — cách đầu là mặc định. Chỉ là
# cách VẼ LẠI số khối đã tải (khoi.tsx đọc `xem`), không có endpoint hay chỉ số mới.
# Lựa chọn lưu trong ô bố cục (`O.xem`), mỗi bảng một cách nhìn. Có test canh: mọi mã ở
# đây phải có nhánh vẽ trong giao_dien/src/tong_quan/khoi.tsx (tests/test_cach_xem.py).
CACH_XEM: dict[str, tuple[tuple[str, str], ...]] = {
    # 2026-09-29 (chủ DN): Doanh thu · Lãi gộp · Khách mới; "bien" cũ gộp vào "lai_gop" (XEM_CU).
    "theo_thang": (("cot", "Doanh thu"), ("lai_gop", "Lãi gộp"), ("khach_moi", "Khách mới"), ("luy_ke", "Luỹ kế")),
    "xu_huong": (("doanh_thu", "Doanh thu"), ("luy_ke", "Luỹ kế"), ("lai_gop", "Lãi gộp"), ("so_khach", "Số khách")),
    "ns_thang": (("doanh_thu", "Doanh thu"), ("lai_gop", "Lãi gộp")),
    "so_sanh_sale": (("tien_do", "Tiến độ"), ("doanh_thu", "Doanh thu"), ("lai_gop", "Lãi gộp")),
    "hieu_suat_nganh": (("ty_trong", "Tỷ trọng"), ("doanh_thu", "Doanh thu"), ("bien", "Biên gộp")),
    "danh_sach_khach": (("doanh_thu", "Doanh thu"), ("im_lang", "Im lặng")),
    "suc_khoe_khach": (("thanh", "Thanh"), ("vong", "Vòng")),
    "tang_truong": (("so_khach", "Số khách"), ("doanh_thu", "Doanh thu")),
    "cong_no": (("tuoi", "Tuổi nợ"), ("lau_nhat", "Nợ lâu nhất")),
}


def danh_muc() -> dict:
    """Danh mục khối cho giao diện — MỘT nguồn, giao diện không tự chép lại.
    `mac_dinh` = bố cục mặc định ĐÃ xếp chỗ (nút "Đặt lại bố cục" dùng nó)."""
    return {"khoi": [{"id": k[0], "nhan": k[1], "rong": k[2], "cao": k[3], "nhom": k[4], "mo_ta": k[5],
                      "cach_xem": [{"id": a, "nhan": b} for a, b in CACH_XEM.get(k[0], ())]}
                     for k in KHOI],
            "nhom": [{"id": a, "nhan": b} for a, b in NHOM],
            "vai_tro": [{"id": a, "nhan": b, "khoi": list(c)} for a, b, c in VAI_TRO],
            "mac_dinh": [o.dict() for o in mac_dinh()]}


NHAN = {k[0]: k[1] for k in KHOI}
_MAC_DINH = {k[0]: (k[2], k[3]) for k in KHOI}

# Một bố cục hợp lệ không bao giờ dài hơn vài trăm byte; chặn thân yêu cầu
# lớn để một POST rác không bắt máy chủ phân tích cả megabyte JSON.
DAI_TOI_DA = 8192


@dataclass(frozen=True)
class O:
    id: str
    rong: int
    cao: int
    an: bool = False
    x: int = 0
    y: int = 0
    xem: str | None = None    # None = cách xem đầu tiên của khối (CACH_XEM)

    @property
    def nhan(self) -> str:
        return NHAN[self.id]

    def dict(self) -> dict:
        return {"id": self.id, "x": self.x, "y": self.y, "rong": self.rong, "cao": self.cao,
                "an": self.an, "xem": self.xem}


def _chong(a: O, x: int, y: int, rong: int, cao: int) -> bool:
    return a.x < x + rong and x < a.x + a.rong and a.y < y + cao and y < a.y + a.cao


def nen(ds: list[O]) -> list[O]:
    """Nén dọc: xét khối HIỆN theo (y, x); mỗi khối đè lên khối đã đặt thì bị đẩy
    xuống ngay dưới khối đó (lặp), rồi nổi lên tới khi chạm. Khối ẩn giữ nguyên.
    Trả về theo (y, x), khối ẩn ở cuối. ĐÚNG thuật toán `nen` của
    giao_dien/src/tong_quan/luoi_logic.ts — hai bản chạy chung
    tests/du_lieu/luoi_nen_ca.json."""
    hien = sorted((o for o in ds if not o.an), key=lambda o: (o.y, o.x))
    dat: list[O] = []
    for o in hien:
        y = o.y
        while True:
            dung = [p for p in dat if _chong(p, o.x, y, o.rong, o.cao)]
            if not dung:
                break
            y = max(p.y + p.cao for p in dung)
        while y > 0 and not any(_chong(p, o.x, y - 1, o.rong, o.cao) for p in dat):
            y -= 1
        dat.append(replace(o, y=y))
    return sorted(dat, key=lambda o: (o.y, o.x)) + [o for o in ds if o.an]


def _xep_dau(ds: list[O], co_san: list[O] = (), y0: int = 0) -> list[O]:
    """Đặt từng khối HIỆN, theo thứ tự, vào chỗ trống ĐẦU TIÊN từ hàng `y0` (quét hàng
    rồi cột), tránh các khối `co_san` — tinh thần `grid-auto-flow: dense` của lưới cũ.
    Dùng cho bố cục mặc định, bố cục cũ chưa có toạ độ và khối mới nối vào đáy. Khối
    ẩn về (0, 0)."""
    dat: list[O] = [o for o in co_san if not o.an]
    ra = []
    for o in ds:
        if o.an:
            ra.append(replace(o, x=0, y=0))
            continue
        y = y0
        while True:
            x = next((x for x in range(RONG_TOI_DA - o.rong + 1)
                      if not any(_chong(p, x, y, o.rong, o.cao) for p in dat)), None)
            if x is not None:
                break
            y += 1
        p = replace(o, x=x, y=y)
        dat.append(p)
        ra.append(p)
    return ra


def mac_dinh() -> list[O]:
    return nen(_xep_dau([O(k[0], k[2], k[3]) for k in KHOI]))


def _so(v, thap: int, cao: int, mac: int | None) -> int | None:
    # bool là int trong Python — `True` không được hiểu thành rộng 1.
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return mac
    return max(thap, min(cao, int(v)))


def _la_toa_do(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# Mã cách xem đã đổi tên: bố cục đã lưu vẫn giữ lựa chọn.
XEM_CU = {("theo_thang", "bien"): "lai_gop"}


def _xem(ma: str, v) -> str | None:
    v = XEM_CU.get((ma, v), v) if isinstance(v, str) else v
    return v if isinstance(v, str) and any(v == a for a, _ in CACH_XEM.get(ma, ())) else None


def chuan_hoa(tho) -> list[O]:
    """Bố cục bất kỳ (list/JSON/None/rác) -> bố cục hợp lệ ĐỦ mọi khối, đã xếp chỗ.

    - chỉ giữ mã khối đã biết, lần xuất hiện ĐẦU TIÊN (trùng thì bỏ);
    - bố cục CŨ (có ô thiếu x/y số): rộng kẹp 1..3, cao 1..4 rồi × DOI_CU, xếp chỗ theo
      thứ tự đã lưu (`_xep_dau`); bố cục mới: rộng 3..12, cao 2..16, x 0..12−rộng;
      kiểu sai thì lấy mặc định của khối;
    - `xem` không thuộc CACH_XEM của khối -> None;
    - khối còn thiếu nối vào ĐÁY (chỗ trống đầu tiên dưới mọi khối), cỡ mặc định, đang hiện;
    - cuối cùng `nen` — không bao giờ có hai khối hiện chồng lên nhau.
    Không bao giờ ném lỗi: bố cục hỏng không được làm hỏng trang chủ.
    """
    if isinstance(tho, (str, bytes)):
        try:
            tho = json.loads(tho)
        except ValueError:
            tho = None
    tho_ds, da_co = [], set()
    for x in tho if isinstance(tho, list) else []:
        if not isinstance(x, dict):
            continue
        ma = x.get("id")
        ma = MA_CU.get(ma, ma) if isinstance(ma, str) else ma
        if not isinstance(ma, str) or ma not in _MAC_DINH or ma in da_co:
            continue
        tho_ds.append((ma, x))
        da_co.add(ma)
    cu = any(not (_la_toa_do(x.get("x")) and _la_toa_do(x.get("y"))) for _, x in tho_ds)
    ds = []
    for ma, x in tho_ds:
        r0, c0 = _MAC_DINH[ma]
        an, xem = x.get("an") is True, _xem(ma, x.get("xem"))
        if cu:
            r, c = _so(x.get("rong"), 1, 3, None), _so(x.get("cao"), 1, 4, None)
            ds.append(O(ma, r * DOI_CU[0] if r else r0, c * DOI_CU[1] if c else c0, an, xem=xem))
        else:
            r = _so(x.get("rong"), RONG_TOI_THIEU, RONG_TOI_DA, r0)
            ds.append(O(ma, r, _so(x.get("cao"), CAO_TOI_THIEU, CAO_TOI_DA, c0), an,
                        _so(x.get("x"), 0, RONG_TOI_DA - r, 0), _so(x.get("y"), 0, Y_TOI_DA, 0), xem))
    if cu:
        ds = _xep_dau(ds)
    day = max((o.y + o.cao for o in ds if not o.an), default=0)
    ds += _xep_dau([O(k[0], k[2], k[3]) for k in KHOI if k[0] not in da_co], ds, day)
    return nen(ds)


def luu(conn, nguoi_dung_id: int, bo_cuc: list[O] | None) -> None:
    """Ghi bố cục (đã chuẩn hoá) của một người. None = về mặc định. Không tự
    commit — người gọi quyết định ranh giới giao dịch."""
    gia_tri = None if bo_cuc is None else json.dumps([o.dict() for o in bo_cuc])
    conn.execute("UPDATE app.nguoi_dung SET bo_cuc_tong_quan = %s WHERE id = %s",
                 (gia_tri, nguoi_dung_id))
