"""Bố cục trang Tổng quan theo từng tài khoản (migration 034).

Theo gói thiết kế Dashboard.dc.html: lưới 3 cột, mỗi khối rộng 1–3 cột và cao
1–4 hàng (hàng tối thiểu 150px, lưới tự lấp chỗ trống), kéo để đổi chỗ, kéo
góc để đổi kích thước, ẩn/hiện từng khối. Khác gói thiết kế ở chỗ lưu: gói
ghi localStorage, ta ghi `app.nguoi_dung.bo_cuc_tong_quan` — xem chú thích
đầu migration 034.

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
from dataclasses import dataclass

RONG_TOI_DA = 3   # số cột của lưới — đổi là đổi cả giao_dien/src/tong_quan/Luoi.tsx (RONG) và CSS .luoi-tq
CAO_TOI_DA = 4

# (mã, nhãn, rộng, cao, nhóm, mô tả) — ĐÚNG danh mục `MODULES` và thứ tự /
# kích thước `BO_CUC_MAC_DINH` của Dashboard.dc.html (21 khối) + khối tháng (036). Khối không có
# nguồn dữ liệu vẫn có mặt (khung "chưa có dữ liệu", kome/khoi_tong_quan.py
# ::CHUA_CO) — lựa chọn của chủ doanh nghiệp, đặc tả giao diện React §2.
KHOI = (
    ("kpi", "Chỉ số hôm nay", 3, 1, "tong_quan", "Sáu con số mở đầu ngày, mỗi ô dẫn thẳng tới màn hình của nó"),
    ("ns_thang", "Tiến độ ngân sách tháng", 3, 1, "tong_quan", "Từng sale so với mốc đáng lẽ đạt tới hôm nay"),
    ("theo_thang", "Kết quả theo từng tháng", 3, 3, "tong_quan", "12 tháng của kỳ kế toán so ngân sách và cùng kỳ"),
    ("viec_hom_nay", "Việc cần làm hôm nay", 2, 3, "tong_quan", "Gom việc từ khách cần gọi, hẹn gọi lại, kho và dữ liệu"),
    # Ngoài 21 khối của gói thiết kế — thêm 2026-09-23 theo yêu cầu chủ DN
    # ("công ty chạy doanh thu theo tháng"), nguồn: mart.khach_thang_nay (036).
    ("thang_nay_chua_mua", "Tháng này chưa mua", 1, 3, "khach_hang", "Khách mua đều hằng tháng mà tháng này chưa có đơn"),
    ("cong_no", "Tuổi nợ phải thu", 1, 2, "tien", "Chia 0–30 / 30–60 / trên 60 ngày và ai nợ lâu nhất"),
    ("xu_huong", "Xu hướng doanh thu", 2, 2, "tien", "Doanh thu ngày, có đường so sánh kỳ trước"),
    ("dong_tien", "Dòng tiền 8 tuần", 1, 2, "tien", "Tiền vào trừ tiền ra theo tuần và số dư dự kiến"),
    ("mua_hang", "Đơn đặt nhà cung cấp", 1, 1, "hang_hoa", "PO đang mở, đơn trễ hẹn và đơn chờ duyệt"),
    ("khieu_nai", "Trả hàng & khiếu nại", 1, 1, "hang_hoa", "Phiếu đang mở, quá hạn xử lý và chi phí bồi hoàn"),
    ("suc_khoe_khach", "Sức khoẻ khách hàng", 1, 1, "khach_hang", "Bao nhiêu khách khoẻ, cần theo dõi, đang rời bỏ"),
    ("danh_sach_khach", "Danh sách khách hàng", 3, 2, "khach_hang", "Doanh thu, nhịp mua và việc cần làm"),
    ("hang_sap_ve", "Sản phẩm sắp về kho", 3, 2, "hang_hoa", "Container đang trên đường và lô nào trễ hẹn"),
    ("han_su_dung", "Sản phẩm sắp hết hạn", 3, 2, "hang_hoa", "Lô cận date và giá trị tồn đang có rủi ro"),
    ("hieu_suat_nganh", "Hiệu suất theo ngành hàng", 2, 2, "thi_truong", "Tỷ trọng doanh thu và biên lãi gộp từng nhóm"),
    ("so_sanh_sale", "Doanh thu theo sale", 1, 2, "khach_hang", "Ai đang đạt, ai đang hụt ngân sách cá nhân"),
    ("tuong_quan", "Doanh thu × tần suất mua", 2, 2, "khach_hang", "Mỗi chấm một khách, thấy ngay ai to mà thưa đơn"),
    ("nhip_mua", "Tỷ lệ im lặng theo tuần", 1, 2, "khach_hang", "Khoảng cách giữa các đơn đang giãn ra hay thu lại"),
    ("bien_loi_nhuan", "Biên lợi nhuận theo quý", 2, 2, "tien", "Biên lãi gộp sáu quý gần nhất"),
    ("tang_truong", "Số khách đang mua", 1, 2, "khach_hang", "Số khách có đơn theo từng kỳ kế toán"),
    ("thoi_tiet", "Thời tiết 7 ngày tới", 2, 2, "thi_truong", "Nắng nóng đẩy bia và nước, mưa to ảnh hưởng lịch xe"),
    ("don_hang", "Nạp dữ liệu / phiếu gần nhất", 3, 2, "tong_quan", "Nhật ký nạp và các phiếu bán mới nhất"),
)
NHOM = (("tat_ca", "Tất cả"), ("tong_quan", "Tổng quan"), ("tien", "Tiền"),
        ("khach_hang", "Khách hàng"), ("hang_hoa", "Hàng hóa"), ("thi_truong", "Thị trường"))
# "Xem theo vai trò" = một bộ khối hiện sẵn (VAI_TRO của gói thiết kế). Bấm là
# ÁP vào bố cục của chính mình — vẫn kéo/ẩn tiếp được, không phải phân quyền.
VAI_TRO = (
    ("giamdoc", "Giám đốc", ("kpi", "ns_thang", "theo_thang", "cong_no", "dong_tien", "xu_huong",
                             "bien_loi_nhuan", "hieu_suat_nganh", "so_sanh_sale", "mua_hang", "tang_truong")),
    ("kinhdoanh", "Trưởng phòng KD", ("kpi", "viec_hom_nay", "thang_nay_chua_mua", "ns_thang", "theo_thang", "danh_sach_khach",
                                      "suc_khoe_khach", "nhip_mua", "tuong_quan", "so_sanh_sale",
                                      "xu_huong", "thoi_tiet")),
    ("ketoan", "Kế toán", ("kpi", "cong_no", "dong_tien", "theo_thang", "bien_loi_nhuan", "khieu_nai",
                           "don_hang", "xu_huong")),
    ("kho", "Kho & giao hàng", ("kpi", "viec_hom_nay", "hang_sap_ve", "han_su_dung", "mua_hang",
                                "khieu_nai", "thoi_tiet")),
)
# Mã khối của bản Jinja (034, 6 khối) -> mã mới: bố cục đã lưu trước ngày đổi
# giao diện vẫn đọc được, không vứt đi.
MA_CU = {"chi_so": "kpi", "ngan_sach": "ns_thang", "suc_khoe": "suc_khoe_khach",
         "can_han": "han_su_dung", "can_goi": "viec_hom_nay"}


def danh_muc() -> dict:
    """Danh mục khối cho giao diện — MỘT nguồn, giao diện không tự chép lại."""
    return {"khoi": [{"id": k[0], "nhan": k[1], "rong": k[2], "cao": k[3], "nhom": k[4], "mo_ta": k[5]}
                     for k in KHOI],
            "nhom": [{"id": a, "nhan": b} for a, b in NHOM],
            "vai_tro": [{"id": a, "nhan": b, "khoi": list(c)} for a, b, c in VAI_TRO]}


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

    @property
    def nhan(self) -> str:
        return NHAN[self.id]

    def dict(self) -> dict:
        return {"id": self.id, "rong": self.rong, "cao": self.cao, "an": self.an}


def mac_dinh() -> list[O]:
    return [O(k[0], k[2], k[3]) for k in KHOI]


def _so(v, thap: int, cao: int, mac: int) -> int:
    # bool là int trong Python — `True` không được hiểu thành rộng 1.
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return mac
    return max(thap, min(cao, int(v)))


def chuan_hoa(tho) -> list[O]:
    """Bố cục bất kỳ (list/JSON/None/rác) -> bố cục hợp lệ ĐỦ mọi khối.

    - chỉ giữ mã khối đã biết, lần xuất hiện ĐẦU TIÊN (trùng thì bỏ);
    - rộng kẹp về 1..3, cao về 1..4; kiểu sai thì lấy mặc định của khối;
    - khối còn thiếu nối vào CUỐI với kích thước mặc định, đang hiện.
    Không bao giờ ném lỗi: bố cục hỏng không được làm hỏng trang chủ.
    """
    if isinstance(tho, (str, bytes)):
        try:
            tho = json.loads(tho)
        except ValueError:
            tho = None
    ds, da_co = [], set()
    for x in tho if isinstance(tho, list) else []:
        if not isinstance(x, dict):
            continue
        ma = x.get("id")
        ma = MA_CU.get(ma, ma) if isinstance(ma, str) else ma
        if not isinstance(ma, str) or ma not in _MAC_DINH or ma in da_co:
            continue
        r0, c0 = _MAC_DINH[ma]
        ds.append(O(ma, _so(x.get("rong"), 1, RONG_TOI_DA, r0),
                    _so(x.get("cao"), 1, CAO_TOI_DA, c0), x.get("an") is True))
        da_co.add(ma)
    ds += [o for o in mac_dinh() if o.id not in da_co]
    return ds


def luu(conn, nguoi_dung_id: int, bo_cuc: list[O] | None) -> None:
    """Ghi bố cục (đã chuẩn hoá) của một người. None = về mặc định. Không tự
    commit — người gọi quyết định ranh giới giao dịch."""
    gia_tri = None if bo_cuc is None else json.dumps([o.dict() for o in bo_cuc])
    conn.execute("UPDATE app.nguoi_dung SET bo_cuc_tong_quan = %s WHERE id = %s",
                 (gia_tri, nguoi_dung_id))
