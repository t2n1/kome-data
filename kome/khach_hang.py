"""Khách hàng: danh sách, tìm kiếm, và hồ sơ 360°.

Như kome/bao_cao.py: KHÔNG định nghĩa chỉ số ở đây, không tự mở kết nối.
Mọi công thức nằm ở schema `mart` (migration 015, 016).
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime

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

# Nhãn hiển thị cho khách chưa có hồ sơ 得意先全情報 (prefecture NULL hoặc
# rỗng), và GIÁ TRỊ QUY ƯỚC mang nhãn đó đi trên URL.
#
# Vì sao phải là hai chuỗi khác nhau: đổ thẳng nhãn ra `<option value>` thì
# bấm vào nó gửi `tinh=(không rõ)`, rồi câu SQL chạy `prefecture = '(không
# rõ)'` — không dòng nào khớp. Khối "Tập trung ở đâu" nói "(không rõ): 37"
# ngay phía trên, bấm vào ra "Không có khách nào khớp": hai con số mâu thuẫn
# trên cùng một màn hình, và đúng nhóm khách CẦN dọn lại là nhóm không có
# đường nào mở ra.
KHONG_RO = "(không rõ)"
TINH_TRONG = "__trong"

# GIÁ TRỊ QUY ƯỚC cho mục "— mọi người phụ trách —" của ô lọc 担当者, cùng lý
# lẽ với TINH_TRONG ngay trên: chuỗi RỖNG đã có nghĩa khác rồi.
#
# `nv=""` nghĩa là "không chọn gì" -> trang rơi về mặc định tiện dụng của đợt
# 3 và lọc theo người ĐANG ĐĂNG NHẬP. Nên nếu mục đầu của ô chọn mang giá trị
# rỗng thì chọn nó không bỏ được lọc: ô hiện "— mọi người phụ trách —" trong
# khi danh sách vẫn chỉ có khách của mình — ô điều khiển nói một đằng, dữ
# liệu một nẻo, đúng cái mà test của ô Tỉnh được viết ra để chặn. Và vì form
# lọc chỉ mang `tat_ca` khi nó ĐÃ bật, trên bản Vercel một nhân viên không có
# đường nào từ ô đó ra xem toàn công ty.
NV_MOI_NGUOI = "__moi_nguoi"

# GIÁ TRỊ QUY ƯỚC cho "Chưa ai phụ trách" (phân khúc của gói thiết kế): mã
# phụ trách rỗng HOẶC không có trong core.dim_salesperson (đo thật: 1 khách,
# mã ''). Đi qua đúng tham số `sale` như một mã sale, nên mọi bộ đếm co theo
# `sale` co theo nó luôn.
PT_TRONG = "__trong"

# Nhãn tháng (mart.khach_thang_nay.nhan, 036) lọc được trên danh sách.
NHAN_THANG = ("da_mua", "tre", "chua_toi_ngay", "khac")

# Cỡ trang được phép (gói thiết kế: 50 / 100 / 200 dòng).
CO_TRANG = (50, 100, 200)

# 荷姿区分 — hai mã thật sự có trong dữ liệu (xem CLAUDE.md). Mã lạ thì hiện
# nguyên mã chứ không đoán: một nhãn đoán sai còn tệ hơn một mã khó đọc.
QUY_CACH = {"00": "バラ (lẻ)", "02": "ケース (thùng)"}

# Mã khách OBC từ 2023-08 = ngày đăng ký (YYYYMMDD) + số thứ tự 4 chữ số trong ngày
# (202609240002 = khách mới thứ 2 đăng ký ngày 2026-09-24); mã trước đó dạng
# 000000xxxxxx, không mang ngày. Chủ DN xác nhận 2026-09-25.
MA_CU_TRUOC = "trước 8/2023"


def ngay_dang_ky(ma: str | None) -> str | None:
    """Ngày đăng ký đọc từ MÃ khách: 'YYYY-MM-DD', `MA_CU_TRUOC` cho mã cũ
    000000…, None khi mã không theo mẫu nào (vd. ngày không có thật)."""
    ma = ma or ""
    if re.fullmatch(r"000000\d{6}", ma):
        return MA_CU_TRUOC
    if not re.fullmatch(r"20\d{10}", ma):
        return None
    try:
        return datetime.strptime(ma[:8], "%Y%m%d").date().isoformat()
    except ValueError:
        return None

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

# Giai đoạn 2: cột sắp xếp của bảng React -> (khoá trên dòng `danh_ba`, mặc
# định giảm dần). Danh sách TRẮNG như SAP_XEP — khoá lạ rơi về doanh thu.
_THU_HANG = {"S": 1, "A": 2, "B": 3, "C": 4, "D": 5}
COT_SAP = {
    "doanh_thu": (lambda k: k["doanh_thu"], True),
    "lai_gop": (lambda k: k["lai_gop"], True),
    "ty_suat": (lambda k: k["ty_suat"], True),
    "im_lang": (lambda k: k["ty_le_im_lang"], True),
    "gan_nhat": (lambda k: k["lan_cuoi"], True),
    "don_cuoi": (lambda k: k["lan_cuoi"], True),
    "ten": (lambda k: k["ten"], False),
    "pt": (lambda k: k["nguoi_phu_trach"], False),
    "trang_thai": (lambda k: list(TRANG_THAI).index(k["trang_thai"])
                   if k["trang_thai"] in TRANG_THAI else None, False),
    "hang": (lambda k: _THU_HANG.get(k["hang"]), False),
    "thang_nay": (lambda k: k["thang_nay"], True),
    "so_thang_truoc": (lambda k: (k["thang_nay"] / k["thang_truoc_cung_ngay"])
                       if k["thang_truoc_cung_ngay"] and k["thang_nay"] is not None else None, True),
    "tb3": (lambda k: k["tb_3_thang"], True),
    # Khoảng xem (đợt B): doanh thu trong khoảng và tỷ lệ so dải so sánh phụ
    # (tháng trước / khoảng liền trước) — trường do `ghep_khoang` gắn vào.
    "dt_khoang": (lambda k: k.get("dt_khoang"), True),
    "so_khoang": (lambda k: (k["dt_khoang"] / k["dt_ss"])
                  if k.get("dt_ss") and k.get("dt_khoang") is not None else None, True),
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
    # Giai đoạn 2 — chỉ danh_sach() điền (LEFT JOIN khach_thang_nay/hang_doanh_thu).
    hang: str | None = None
    thang_nay: int | None = None
    thang_truoc_cung_ngay: int | None = None
    tb_3_thang: int | None = None
    nhan_thang: str | None = None
    # Khoảng xem (đợt B) — `ghep_khoang` gắn; None = khoảng không có dòng bán.
    dt_khoang: int | None = None
    lg_khoang: int | None = None
    so_phieu_khoang: int | None = None
    dt_ss: int | None = None

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
    # Mã sale đang lọc (None = đang xem tất cả) và tên người đó để trang nói
    # rõ "đang lọc theo ai".
    #
    # `dem_trang_thai` và `tong_tat_ca` KHÔNG còn ở đây — chúng đã chuyển sang
    # TongQuan, nơi chúng được lấy trong cùng một lượt hỏi với bốn khối phân
    # tích. Xem ghi chú ở tong_quan_danh_ba().
    sale: str | None = None
    ten_sale: str | None = None
    # Ba bộ lọc mới của trang danh sách (đợt 4a): nhóm việc ('im'/'tut'/'moi'),
    # hạng doanh thu ('S'..'D'), và tỉnh — trang đọc lại để giữ nguyên lựa
    # chọn qua các liên kết phân trang/sắp xếp.
    nhom: str | None = None
    hang: str | None = None
    tinh: str | None = None
    # Giai đoạn 2: tổng của CẢ nhóm đang lọc (không chỉ trang này), lấy trong
    # chính câu đếm — ô KPI đầu trang.
    thang: str | None = None
    co: int = MOI_TRANG
    tong_dt_thang_nay: int = 0
    tong_dt_thang_truoc_cung_ngay: int = 0
    tong_doanh_thu: int = 0
    # Khoảng xem (đợt B): tổng doanh thu trong khoảng của CẢ nhóm đang lọc, và
    # của dải so sánh phụ (None = dải so sánh không có dữ liệu).
    co_mua: bool = False
    tong_dt_khoang: int = 0
    tong_dt_ss: int | None = None
    # = số khách nhóm 'im' của mart.khach_nhom_viec: nhánh đó của view ĐÚNG là
    # `trang_thai IN TRANG_THAI_CAN_XU_LY` (020), nên đếm thẳng bằng hằng này
    # thay vì EXISTS trên view (dựng lại khach_360 ba lần). Ô KPI "Im lặng >=
    # 2x nhịp" đọc con số này. Có test canh hai con số bằng nhau.
    so_can_xu_ly: int = 0


@dataclass
class HoSo:
    khach: Khach
    ho_so: dict
    thang: list[dict]
    mat_hang: list[dict]
    da_ngung_mua: list[dict]
    lan_mua_gan_day: list[dict]
    # Các khối của đợt 4a, lấy trong ĐÚNG HAI truy vấn (xem ho_so()). Khối
    # "bảng giá của bậc" đã bỏ ở 043: bản xuất 得意先全情報 không còn 売価No.コード,
    # nên không biết khách hưởng bậc giá nào.
    chua_mua_thang: list[dict] = field(default_factory=list)
    goi_y: list[dict] = field(default_factory=list)
    diem_giao: list[dict] = field(default_factory=list)
    # Đợt 7: khối "Nhật ký tiếp xúc" — lượt hỏi thứ 8, tức ĐÚNG chỗ trống đã
    # chừa sẵn ở vòng sửa cuối đợt 4a. Trần 8 giờ đã chạm; khối tiếp theo
    # phải GỘP truy vấn chứ không được nới trần.
    nhat_ky: list = field(default_factory=list)
    # Giai đoạn 2 (React): lấy trong CÙNG các lượt hỏi đã có, không thêm lượt.
    # `tat_ca_mat_hang` = MỌI mã của khách (mat_hang ở trên chỉ là 15 mã đầu),
    # kèm ngành + 3 tháng gần nhất; `ngay_mua` = mọi ngày mua trong 400 ngày
    # (dòng thời gian, lưới 26 tuần); `thang_nay` = dòng mart.khach_thang_nay
    # của khách (036/037) hoặc None nếu 4 tháng qua không mua.
    tat_ca_mat_hang: list[dict] = field(default_factory=list)
    ngay_mua: list[dict] = field(default_factory=list)
    thang_nay: dict | None = None
    hom_nay: date | None = None


_COT = """customer_code, ten, prefecture, city, phone, salesperson_code,
          doanh_thu_thuan, lai_gop, ty_suat, lan_cuoi, so_ngay_im_lang,
          nhip_ngay, ty_le_im_lang, trang_thai, dau_hieu_obc"""

# Khối "chi tiết" của hồ sơ 360°: tên tiếng Việt cho các cột lấy thêm trong
# CÙNG câu lệnh với `_COT` (xem ho_so()). Thứ tự ở đây PHẢI khớp thứ tự cột
# trong câu lệnh đó.
# 043 (mẫu 16 cột): bỏ phan_loai / bac_gia / vang_lai (cột đã bỏ khỏi bản xuất);
# thêm toa_nha (ビル等), hang_obc (ランク名 — 得意先ランク của OBC, KHÁC `hang_dt`
# là hạng theo doanh thu 12 tháng), tai_khoan_ck (振込専用口座番号１); `ngay_chot`
# là TÊN điều kiện chốt (請求締日名), rỗng thì rơi về mã.
_COT_CHI_TIET = ("chi_nhanh", "buu_chinh", "dia_chi", "toa_nha", "hang", "hang_obc",
                 "ngay_chot", "tai_khoan_ck", "lan_dau", "so_lan_mua",
                 "so_phieu", "gia_tri_tb", "hang_dt", "ten_phu_trach")


def _khach(r) -> Khach:
    return Khach(ma=r[0], ten=r[1], tinh=r[2], thanh_pho=r[3], dien_thoai=r[4],
                 nguoi_phu_trach=r[5], doanh_thu=int(r[6] or 0),
                 lai_gop=int(r[7] or 0),
                 ty_suat=float(r[8]) if r[8] is not None else None,
                 lan_cuoi=r[9], so_ngay_im_lang=r[10],
                 nhip_ngay=float(r[11]) if r[11] is not None else None,
                 ty_le_im_lang=float(r[12]) if r[12] is not None else None,
                 trang_thai=r[13], dau_hieu_obc=r[14])


def _ds_hang(hang) -> list[str]:
    """`hang` nhận 'S', 'S,A' hoặc list — gói thiết kế bật/tắt NHIỀU hạng."""
    if not hang:
        return []
    ds = hang if isinstance(hang, (list, tuple)) else str(hang).split(",")
    return [h for h in (x.strip() for x in ds) if h in ("S", "A", "B", "C", "D")]


# ---- Danh bạ: MỘT ảnh chụp, lọc bằng Python --------------------------------
# Giai đoạn 2 (đo thật 2026-09-23, CSDL thật): lọc bằng SQL thì MỖI tổ hợp bộ
# lọc dựng lại mart.khach_360 (~1,2 s một lần) — danh sách 3–6 s, khối tổng
# quan 4–10 s cho mỗi cú bấm. Công ty có ~1.710 khách, dữ liệu chỉ đổi khi nạp,
# nên đúng cách là: MỘT câu lấy cả danh bạ kèm mọi trường cần lọc (hạng, nhóm
# việc, nhãn tháng), đi qua ảnh chụp theo phiên bản dữ liệu nạp
# (kome/web/anh_chup.py), rồi lọc / sắp / đếm trên bộ nhớ — vài mili giây.
#
# `_khop` là bộ lọc DUY NHẤT: danh sách, bộ đếm chip trạng thái và mọi khối
# phân tích đều gọi nó, nên chúng KHÔNG thể trôi khỏi nhau (bài học của
# `_vi_tu` SQL cũ: "chip Tất cả (1.710) bấm vào ra 216 khách"). Lọc không phải
# định nghĩa chỉ số: mọi trường so sánh ở đây là cột của `mart`, đọc nguyên.

def danh_ba(conn) -> dict:
    """{"khach": [...], "nhan_vien": [...]} — ĐÚNG MỘT lượt hỏi (hai mảng JSON
    trong một dòng). `nhom`: nhóm việc của khách. Nhánh 'im' của
    mart.khach_nhom_viec ĐÚNG là `trang_thai IN TRANG_THAI_CAN_XU_LY` (020),
    nên nó đọc thẳng hằng đó; view chỉ được hỏi cho 'tut'/'moi' (điều kiện
    trên cột hằng của UNION ALL cắt hẳn nhánh 'im' — bớt một lần dựng
    khach_360). Có test canh hai định nghĩa trả cùng tập."""
    r = conn.execute("""
        WITH k AS MATERIALIZED (SELECT * FROM mart.khach_360),
        v AS (SELECT customer_code, array_agg(nhom ORDER BY nhom) AS nhom
                FROM mart.khach_nhom_viec WHERE nhom IN ('tut', 'moi') GROUP BY 1),
        d AS (
            SELECT k.customer_code AS ma, k.ten, k.prefecture AS tinh, k.city AS thanh_pho,
                   k.phone AS dien_thoai, k.salesperson_code AS nguoi_phu_trach,
                   coalesce(k.doanh_thu_thuan, 0)::bigint AS doanh_thu,
                   coalesce(k.lai_gop, 0)::bigint AS lai_gop, k.ty_suat::float8 AS ty_suat,
                   k.lan_cuoi, k.so_ngay_im_lang, k.nhip_ngay::float8 AS nhip_ngay,
                   k.ty_le_im_lang::float8 AS ty_le_im_lang, k.trang_thai, k.dau_hieu_obc,
                   k.address AS dia_chi, h.hang,
                   -- 振込専用口座番号１ (043): sale có tiền về thì gõ số tài khoản
                   -- vào ô tìm để ra khách. Đọc thẳng dòng hiện hành (chưa có trong
                   -- khach_360); chỉ mục duy nhất theo is_current nên không nhân dòng.
                   dc.transfer_account AS tai_khoan,
                   (CASE WHEN k.trang_thai = ANY(%s) THEN ARRAY['im'] ELSE ARRAY[]::text[] END)
                     || coalesce(v.nhom, ARRAY[]::text[]) AS nhom,
                   t.nhan AS nhan_thang, t.dt_thang_nay::bigint AS thang_nay,
                   t.dt_thang_truoc_den_ngay::bigint AS thang_truoc_cung_ngay,
                   t.dt_tb_3_thang AS tb_3_thang,
                   EXISTS (SELECT 1 FROM core.dim_salesperson ps
                            WHERE ps.salesperson_code = k.salesperson_code) AS co_pt
              FROM k
              LEFT JOIN mart.hang_doanh_thu h ON h.customer_code = k.customer_code
              LEFT JOIN v ON v.customer_code = k.customer_code
              LEFT JOIN mart.khach_thang_nay t ON t.customer_code = k.customer_code
              LEFT JOIN core.dim_customer dc ON dc.customer_code = k.customer_code
                                            AND dc.is_current)
        SELECT (SELECT coalesce(json_agg(d ORDER BY d.doanh_thu DESC, d.ma), '[]') FROM d),
               (SELECT coalesce(json_agg(n ORDER BY n.doanh_thu DESC, n.ma), '[]') FROM (
                    SELECT salesperson_code AS ma, ten, so_khach,
                           coalesce(doanh_thu, 0)::bigint AS doanh_thu,
                           so_khach_canh_bao AS canh_bao
                      FROM mart.tai_nhan_vien) n),
               (SELECT hom_nay FROM mart.moc_thoi_gian)
    """, [list(TRANG_THAI_CAN_XU_LY)]).fetchone()
    return {"khach": r[0], "nhan_vien": r[1], "hom_nay": r[2]}


def ghep_khoang(db: dict, kk: dict | None) -> dict:
    """Danh bạ + doanh số trong khoảng xem (`kome.ban_khoang.danh_ba_khoang`).
    Trả BẢN SAO nông (danh bạ là ảnh chụp dùng chung giữa các khoảng — không
    được sửa tại chỗ). Khách không có dòng trong khoảng: `dt_khoang` = 0 (trong
    dải dữ liệu, không có phiếu = bán 0 đồng), `so_phieu_khoang` = 0."""
    if kk is None:
        return db
    dong, co_ss = kk["dong"], kk["so_sanh"]["co"]
    khach = []
    for k in db["khach"]:
        d = dong.get(k["ma"]) or [None, None, None, None]
        khach.append({**k, "dt_khoang": d[0] or 0, "lg_khoang": d[1] or 0,
                      "so_phieu_khoang": d[2] or 0,
                      "dt_ss": (d[3] or 0) if co_ss else None})
    return {**db, "khach": khach}


def _khop(k: dict, *, tim: str = "", loc: str = "", sale: str | None = None,
          nhom: str | None = None, hang=None, tinh: str | None = None,
          thang: str | None = None, co_mua: bool = False) -> bool:
    """Một khách (dòng của `danh_ba`) có khớp bộ lọc không. Ngữ nghĩa từng bộ
    lọc giữ ĐÚNG như bản SQL cũ:
      * tim — chứa (không phân biệt hoa thường) trong tên, mã, điện thoại,
        địa chỉ, thành phố hoặc số tài khoản chuyển khoản riêng (043): nhân viên
        không nhớ mình đang cầm mảnh nào.
      * sale — `PT_TRONG` = mã phụ trách không có trong core.dim_salesperson.
      * tinh — `TINH_TRONG` = tỉnh NULL/rỗng (nhãn "(không rõ)" chỉ là nhãn
        hiển thị, không nằm trong CSDL).
      * hang — nhiều hạng (bật/tắt), hạng theo doanh thu 12 tháng.
      * thang — nhãn của mart.khach_thang_nay, SO BẰNG (không NOT)."""
    if tim:
        t = tim.strip().casefold()
        if t and not any(t in (k.get(c) or "").casefold()
                         for c in ("ten", "ma", "dien_thoai", "dia_chi", "thanh_pho",
                                   "tai_khoan")):
            return False
    if loc in TRANG_THAI and k["trang_thai"] != loc:
        return False
    if sale == PT_TRONG:
        if k["co_pt"]:
            return False
    elif sale and k["nguoi_phu_trach"] != sale:
        return False
    if nhom and nhom not in (k["nhom"] or []):
        return False
    ds = _ds_hang(hang)
    if ds and k["hang"] not in ds:
        return False
    if tinh == TINH_TRONG:
        if k["tinh"]:
            return False
    elif tinh and k["tinh"] != tinh:
        return False
    if thang in NHAN_THANG and k["nhan_thang"] != thang:
        return False
    if co_mua and not k.get("so_phieu_khoang"):
        return False
    return True


def _loc(ds: list[dict], **bo_loc) -> list[dict]:
    return [k for k in ds if _khop(k, **bo_loc)]


def _sap(ds: list[dict], sap: str, giam: bool | None) -> tuple[list[dict], str]:
    """Sắp xếp theo DANH SÁCH TRẮNG `COT_SAP` (khoá lạ rơi về doanh thu).
    NULL luôn xuống cuối, hoà thì theo mã — thứ tự ổn định giữa các trang."""
    if sap not in COT_SAP:
        sap = "doanh_thu"
    khoa, mac_dinh = COT_SAP[sap]
    chieu = mac_dinh if giam is None else giam
    co = [k for k in ds if khoa(k) is not None]
    khong = [k for k in ds if khoa(k) is None]
    co.sort(key=lambda k: k["ma"])
    co.sort(key=khoa, reverse=chieu)
    khong.sort(key=lambda k: k["ma"])
    return co + khong, sap


def _thanh_khach(k: dict) -> "Khach":
    lc = k["lan_cuoi"]
    return Khach(ma=k["ma"], ten=k["ten"], tinh=k["tinh"], thanh_pho=k["thanh_pho"],
                 dien_thoai=k["dien_thoai"], nguoi_phu_trach=k["nguoi_phu_trach"],
                 doanh_thu=int(k["doanh_thu"] or 0), lai_gop=int(k["lai_gop"] or 0),
                 ty_suat=k["ty_suat"],
                 lan_cuoi=date.fromisoformat(lc) if isinstance(lc, str) else lc,
                 so_ngay_im_lang=k["so_ngay_im_lang"], nhip_ngay=k["nhip_ngay"],
                 ty_le_im_lang=k["ty_le_im_lang"], trang_thai=k["trang_thai"],
                 dau_hieu_obc=k["dau_hieu_obc"], hang=k["hang"],
                 thang_nay=k["thang_nay"], thang_truoc_cung_ngay=k["thang_truoc_cung_ngay"],
                 tb_3_thang=k["tb_3_thang"], nhan_thang=k["nhan_thang"],
                 dt_khoang=k.get("dt_khoang"), lg_khoang=k.get("lg_khoang"),
                 so_phieu_khoang=k.get("so_phieu_khoang"), dt_ss=k.get("dt_ss"))


def trang_danh_sach(db: dict, tim: str = "", loc: str = "", sap: str = "doanh_thu",
                    trang: int = 1, sale: str | None = None,
                    ten_sale: str | None = None, nhom: str | None = None,
                    hang=None, tinh: str | None = None, thang: str | None = None,
                    giam: bool | None = None, co: int = MOI_TRANG,
                    co_mua: bool = False) -> TrangKhach:
    """Một trang của danh sách, tính trên danh bạ `db` (không SQL).

    Ô KPI đầu trang là TỔNG của CẢ nhóm đang lọc (không chỉ trang này), cùng
    bộ lọc với bảng — ô KPI không bao giờ nói về một nhóm khác cái bảng đang
    hiện. `so_can_xu_ly` = số khách nhóm 'im' (xem `danh_ba`).

    `sale` là MẶC ĐỊNH TIỆN DỤNG, không phải hàng rào bảo mật: công ty năm
    người, ai cũng biết khách của ai, và trang luôn có một liên kết bỏ lọc.
    Không có kiểm quyền nào ở đây, và đó là cố ý — xem đặc tả đợt 3 §5."""
    ds = _loc(db["khach"], tim=tim, loc=loc, sale=sale, nhom=nhom, hang=hang,
              tinh=tinh, thang=thang, co_mua=co_mua)
    ds, sap = _sap(ds, sap, giam)
    co = co if co in CO_TRANG else MOI_TRANG
    tong = len(ds)
    so_trang = max(1, -(-tong // co))
    trang = max(1, trang)
    return TrangKhach(
        khach=[_thanh_khach(k) for k in ds[(trang - 1) * co: trang * co]],
        tong=tong, trang=trang, so_trang=so_trang, tim=tim, loc=loc, sap=sap,
        sale=sale, ten_sale=ten_sale, nhom=nhom,
        hang=",".join(_ds_hang(hang)) or None, tinh=tinh,
        thang=thang if thang in NHAN_THANG else None, co=co,
        tong_dt_thang_nay=sum(k["thang_nay"] or 0 for k in ds),
        tong_dt_thang_truoc_cung_ngay=sum(k["thang_truoc_cung_ngay"] or 0 for k in ds),
        tong_doanh_thu=sum(k["doanh_thu"] or 0 for k in ds),
        co_mua=co_mua,
        tong_dt_khoang=sum(k.get("dt_khoang") or 0 for k in ds),
        tong_dt_ss=(sum(k.get("dt_ss") or 0 for k in ds)
                    if ds and ds[0].get("dt_ss") is not None else None),
        so_can_xu_ly=sum(1 for k in ds if k["trang_thai"] in TRANG_THAI_CAN_XU_LY))


def danh_sach(conn, tim: str = "", loc: str = "", sap: str = "doanh_thu",
              trang: int = 1, sale: str | None = None,
              ten_sale: str | None = None, nhom: str | None = None,
              hang=None, tinh: str | None = None, thang: str | None = None,
              giam: bool | None = None, co: int = MOI_TRANG) -> TrangKhach:
    """`trang_danh_sach` trên danh bạ vừa đọc — MỘT lượt hỏi."""
    return trang_danh_sach(danh_ba(conn), tim=tim, loc=loc, sap=sap, trang=trang,
                           sale=sale, ten_sale=ten_sale, nhom=nhom, hang=hang,
                           tinh=tinh, thang=thang, giam=giam, co=co)


def ho_so(conn, ma: str) -> HoSo | None:
    """Hồ sơ 360° của một khách. None nếu mã không tồn tại."""
    # MỘT lượt hỏi cho cả thẻ đầu trang lẫn khối chi tiết, chứ không hai.
    # Trước vòng sửa này đây là HAI câu `SELECT … FROM mart.khach_360 WHERE
    # customer_code = %s` giống hệt nhau về mệnh đề lọc, chỉ khác danh sách
    # cột — tức 47 ms mạng trả cho đúng một hàng đã nằm sẵn trong tay. Gộp
    # lại trả ngân sách truy vấn về 7/8, để khối tiếp theo ai đó muốn thêm
    # không phải phá bất biến mới thêm được.
    r = conn.execute(
        f"""SELECT {_COT},
                   branch_name, postcode, address, x.building, rank_code, x.rank_name,
                   coalesce(nullif(x.closing_day_name, ''), closing_day_code),
                   x.transfer_account, lan_dau,
                   so_lan_mua, so_phieu, gia_tri_tb_moi_lan,
                   -- Hạng theo doanh thu 12 tháng (KHÔNG phải rank_code OBC ở
                   -- trên) — cột cuối, cùng lượt hỏi (giai đoạn 2).
                   (SELECT hang FROM mart.hang_doanh_thu WHERE customer_code = %s),
                   -- Tên phụ trách: danh sách phụ trách trước; mã không có trong đó
                   -- (vd. 0000) thì lấy 売上主担当者名 đi kèm trong 得意先全情報.
                   coalesce((SELECT ps.ten FROM core.dim_salesperson ps
                              WHERE ps.salesperson_code = mart.khach_360.salesperson_code),
                            nullif(x.salesperson_name, ''))
            FROM mart.khach_360
            -- Năm cột mới của 043 chưa có trong khach_360 (view nặng — không dựng
            -- lại chỉ để thêm cột hiển thị): đọc thẳng dòng hiện hành. LATERAL chỉ
            -- chọn đúng các cột mới, nên tên cột của khach_360 không bị mơ hồ.
            LEFT JOIN LATERAL (
                SELECT dc.building, dc.rank_name, dc.closing_day_name,
                       dc.transfer_account, dc.salesperson_name
                  FROM core.dim_customer dc
                 WHERE dc.customer_code = mart.khach_360.customer_code AND dc.is_current
            ) x ON true
            WHERE customer_code = %s""", (ma, ma)).fetchone()
    if r is None:
        return None
    # `_khach` đọc 15 cột ĐẦU theo vị trí, phần đuôi cắt từ CUỐI lên theo số
    # tên trong `_COT_CHI_TIET`. Hai đầu độc lập nhau, nên thêm cột vào `_COT`
    # không làm lệch khối chi tiết (và ngược lại).
    k = _khach(r)
    ho = dict(zip(_COT_CHI_TIET, r[-len(_COT_CHI_TIET):]))
    ho["ngay_dang_ky"] = ngay_dang_ky(ma)

    # Nhãn tháng (036/037) đi CHUNG câu này (LEFT JOIN một dòng) — trần 8
    # lượt hỏi đã chạm, khối mới phải gộp vào câu có sẵn.
    rows_thang = conn.execute(
        """SELECT t.thang, t.doanh_thu_thuan, t.lai_gop, t.so_lan_mua,
                  x.nhan, x.thang, x.dt_thang_nay, x.dt_thang_truoc_den_ngay,
                  x.dt_thang_truoc, x.dt_tb_3_thang, x.so_thang_mua_3
           FROM mart.khach_theo_thang t
           LEFT JOIN (SELECT * FROM mart.khach_thang_nay WHERE customer_code = %s) x ON true
           WHERE t.customer_code = %s
           ORDER BY t.thang""", (ma, ma)).fetchall()
    thang = [dict(zip(("thang", "doanh_thu", "lai_gop", "so_lan"), t[:4])) for t in rows_thang]
    x = rows_thang[0] if rows_thang else None
    thang_nay = None if x is None or x[4] is None else {
        "nhan": x[4], "thang": x[5], "dt_thang_nay": int(x[6] or 0),
        "dt_thang_truoc_den_ngay": int(x[7] or 0), "dt_thang_truoc": int(x[8] or 0),
        "dt_tb_3_thang": int(x[9] or 0), "so_thang_mua_3": x[10]}

    # `nhip` là numeric từ Postgres — ép sang int khi HIỂN THỊ ở template
    # (`|int`), không ép ở đây: None phải đi qua nguyên vẹn để template hiện
    # "—" cho mã chưa đủ lịch sử để tính nhịp.
    # Cả ba cột nhịp (`nhip`, `du_kien`, `tre`) nằm sẵn trong CÙNG một view
    # mart.khach_mat_hang — lấy đủ ba ở cả hai khối bên dưới, không chỉ khối
    # đưa ra trong đặc tả gốc, vì bổ sung không tốn thêm truy vấn nào.
    # MỌI mã của khách trong MỘT lượt hỏi (giai đoạn 2): tab Sản phẩm cần cả
    # danh sách, giỏ theo ngành và 3 tháng gần nhất của từng mã; khối "đã ngừng
    # mua" nay LỌC từ chính các dòng này thay vì một câu riêng — trả lại một
    # chỗ trong trần 8 lượt hỏi. Ba tháng lấy từ mart.dong_ban (doanh thu thuần
    # định nghĩa ở đó), lọc đúng khách này + từ mùng 1 của hai tháng trước.
    # Ngành để THÔ (NULL/rỗng) — Python đổi sang kome.bao_cao.NGANH_TRONG, bản
    # chép bắt buộc của coalesce trong mart.ban_theo_nganh_thang (CLAUDE.md).
    tat_ca = [dict(zip(("ma", "ten", "doanh_thu", "lai_gop", "so_luong",
                        "so_lan", "lan_cuoi", "nhip", "du_kien", "tre",
                        "trang_thai_cap", "nganh", "t2", "t1", "t0"), h))
              for h in conn.execute(
        """WITH m AS MATERIALIZED (
               SELECT date_trunc('month', hom_nay)::date AS dau FROM mart.moc_thoi_gian),
           b AS (
               SELECT d.product_code,
                      sum(d.doanh_thu_thuan) FILTER (WHERE d.sales_date < m.dau - interval '1 month') AS t2,
                      sum(d.doanh_thu_thuan) FILTER (WHERE d.sales_date >= m.dau - interval '1 month'
                                                       AND d.sales_date < m.dau) AS t1,
                      sum(d.doanh_thu_thuan) FILTER (WHERE d.sales_date >= m.dau) AS t0
                 FROM mart.dong_ban d, m
                WHERE d.customer_code = %s AND d.sales_date >= m.dau - interval '2 month'
                GROUP BY d.product_code)
           SELECT h.product_code, h.ten_hang, h.doanh_thu_thuan, h.lai_gop, h.so_luong,
                  h.so_lan, h.lan_cuoi, h.nhip_ngay, h.du_kien_lan_toi, h.tre_ngay,
                  h.trang_thai_cap, p.food_category_name, b.t2, b.t1, b.t0
             FROM mart.khach_mat_hang h
             LEFT JOIN core.dim_product p ON p.product_code = h.product_code
             LEFT JOIN b ON b.product_code = h.product_code
            WHERE h.customer_code = %s
            ORDER BY h.doanh_thu_thuan DESC NULLS LAST, h.product_code""", (ma, ma)).fetchall()]
    from kome.bao_cao import NGANH_TRONG
    for m_ in tat_ca:
        m_["nganh"] = m_["nganh"] or NGANH_TRONG
        for c in ("t2", "t1", "t0"):
            m_[c] = int(m_[c]) if m_[c] is not None else 0
    mat_hang = [{k: m_[k] for k in ("ma", "ten", "doanh_thu", "lai_gop", "so_luong",
                                    "so_lan", "lan_cuoi", "nhip", "du_kien", "tre")}
                for m_ in tat_ca[:15]]

    # Mặt hàng khách TỪNG mua đều rồi NGỪNG hẳn. Đây là tín hiệu sớm hơn nhiều
    # so với việc khách ngừng mua toàn bộ: họ đang chuyển dần sang nhà cung cấp
    # khác, từng món một, và không ai để ý cho tới khi mất luôn khách.
    #
    # ĐỌC `trang_thai_cap` của mart.khach_mat_hang (migration 024), KHÔNG viết
    # lại vị từ. Trước 024 chỗ này dùng ngưỡng CHUNG (`hom_nay - lan_cuoi > 90`
    # cộng `so_lan >= 3`) còn /san-pham/{mã} dùng nhịp RIÊNG — cùng một cặp
    # (khách, mã) cho hai câu trả lời ngược nhau ở hai màn. Nay một khái niệm
    # một công thức, đúng nếp 021/022.
    #
    # SO BẰNG với `'ngung'`, và KHÔNG BAO GIỜ dùng `NOT` trên cột này: nhãn có
    # ba giá trị, nên phủ định nó là gộp bừa hai giá trị còn lại (trong đó có
    # `'khong_goi'` — khách ※廃業※) vào một khối. Đó đúng là lý do cột này là
    # nhãn chứ không phải boolean; xem chú thích của migration 024.
    #
    # `so_lan >= 3` đã bỏ vì THỪA, không phải vì nới lỏng: `nhip_ngay` chỉ có
    # giá trị khi đã có >= 2 khoảng cách, tức >= 3 lần mua (020). Để lại là
    # dựng thêm một bản sao của cùng điều kiện, ở đúng chỗ vừa dọn xong.
    da_ngung = [{k: m_[k] for k in ("ma", "ten", "so_lan", "lan_cuoi", "doanh_thu",
                                    "nhip", "du_kien", "tre")}
                for m_ in tat_ca if m_["trang_thai_cap"] == "ngung"][:10]

    # Mọi ngày mua trong 400 ngày tới mốc (lưới 26 tuần, DT 30 ngày, dòng thời
    # gian) CỘNG 12 ngày mua gần nhất dù cũ hơn (khối "12 lần mua gần nhất" của
    # khách đã im lâu). Tối đa ~260 dòng (đo thật: 256 ngày/400 ngày).
    rows_ngay = conn.execute(
        """SELECT l.sales_date, count(*), sum(l.doanh_thu_thuan), sum(l.lai_gop), m.hom_nay
           FROM mart.lan_mua l CROSS JOIN mart.moc_thoi_gian m
           WHERE l.customer_code = %s
             AND (l.sales_date > m.hom_nay - 400
                  OR l.sales_date >= (SELECT min(z.d) FROM (
                         SELECT DISTINCT sales_date AS d FROM mart.lan_mua
                          WHERE customer_code = %s ORDER BY 1 DESC LIMIT 12) z))
           GROUP BY l.sales_date, m.hom_nay
           ORDER BY l.sales_date DESC""", (ma, ma)).fetchall()
    ngay_mua = [dict(zip(("ngay", "so_phieu", "doanh_thu", "lai_gop"), l[:4])) for l in rows_ngay]
    gan_day = ngay_mua[:12]
    moc = rows_ngay[0][4] if rows_ngay else None

    # ---- Bốn khối mới của đợt 4a, gộp thành ĐÚNG HAI truy vấn -----------
    # NGÂN SÁCH TRUY VẤN: 8 là TRẦN. Từ giai đoạn 2 hàm chạy 7 (khối "đã ngừng
    # mua" gộp vào câu mặt hàng) — chỗ trống là cố ý. Đo thật
    # 2026-09-22: một round-trip rỗng tới pooler Tokyo mất 47 ms, một lượt
    # hỏi thật ~260 ms. Trang hồ sơ chậm dần từng đợt là cách nó chết mà
    # không ai thấy ngày nào nó chết. Có test canh —
    # tests/test_khach_hang.py::test_ho_so_khong_qua_8_truy_van.
    # Chỗ trống thứ 8 đã dùng cho nhật ký tiếp xúc (đợt 7): khối tiếp theo phải
    # GỘP vào một truy vấn có sẵn, không được nới trần.
    #
    # HAI truy vấn chứ không MỘT: gộp cả bốn khối vào một UNION ALL bốn tầng
    # thì mỗi nhánh phải đệm NULL cho khớp kiểu của ba nhánh kia, và câu lệnh
    # đó khó đọc hơn đúng cái nó tiết kiệm (47 ms).
    #
    # Hai cột `chu`/`so_a` mang nghĩa KHÁC NHAU theo `khoi` — đó là cái giá
    # của việc gộp, và vòng lặp Python ngay dưới là chỗ duy nhất biết quy ước
    # đó. `xep` là khoá sắp xếp của từng nhánh (doanh thu cho 'chua', tỷ suất
    # cho 'goi_y'); ORDER BY nằm ở lớp NGOÀI vì thứ tự dòng giữa các nhánh
    # của UNION ALL không được Postgres bảo đảm.
    #
    # KHÔNG lấy `ty_suat_mat_hang.gia_cao_nhat` ra đây, dù nó có sẵn: cột đó
    # là `max(unit_price)` KHÔNG tách theo 荷姿区分 (00 = バラ lẻ, 02 = ケース
    # thùng), nên với mã bán cả hai quy cách nó LUÔN là giá thùng. Khối này
    # hứa "mã chưa từng mua, xếp theo tỷ suất" — giá không nằm trong lời hứa,
    # và đây lại là con số DUY NHẤT trên hai trang mà người bán đọc rồi nói
    # thẳng ra cho khách. Báo giá lẻ bằng giá thùng sai hơn chục lần; không
    # có số còn hơn có số sai. Bảng giá đúng (tách 荷姿) nằm ở khối "Bảng giá
    # của bậc" ngay dưới, dựng từ core.fact_price_list.
    #
    # NHÁNH 'chua' ĐỌC ĐÚNG NHÃN `'mua'`, KHÔNG PHẢI MỘT NGƯỠNG NGÀY RIÊNG và
    # cũng không phải phủ định của nhãn "đã ngừng". Nó là dải giữa: đã quá ngày
    # dự kiến mua lại (`tre_ngay IS NOT NULL`, tức im lặng > 1 nhịp) nhưng CHƯA
    # tới 2 nhịp (`trang_thai_cap = 'mua'`) — "còn gọi kịp". Trước 024 vế thứ
    # hai là `hom_nay - lan_cuoi <= 90`, ăn khớp với ngưỡng 90 của khối "đã
    # ngừng mua" ngay dưới nó. Đổi khối kia sang nhịp riêng mà để nguyên chỗ
    # này thì hai khối CHỒNG NHAU: một mã nhịp 7 ngày im 60 ngày vừa "đã ngừng"
    # (60 >= 2x7) vừa "chưa mua tháng này" (60 <= 90) — cùng một mã, hai kết
    # luận, trên cùng một trang.
    #
    # KHÔNG CÒN JOIN mart.dau_hieu_khach Ở ĐÂY. Đây cũng là một DANH SÁCH GỌI
    # LẠI ("một cuộc điện thoại nhắc là đủ"), nên khách ※廃業※ không được vào —
    # và nhãn đã lo việc đó: họ mang `'khong_goi'`, nên `= 'mua'` tự loại họ.
    # Bản trước của 024 dùng boolean `NOT ngung_mua`, thứ LUÔN đúng với khách
    # đã đóng cửa vì cổng ※廃業※ nằm gói bên trong chính boolean đó, nên chỗ này
    # buộc phải tự JOIN lấy `da_ngung` để đắp lại — một cờ, hai nguồn, ba chỗ
    # chép. Nhãn dẹp cả ba: cờ ※廃業※ nay chỉ được đọc MỘT lần, trong view.
    # CTE `AS MATERIALIZED`: hai nhánh dưới đây đều đọc mart.khach_mat_hang,
    # và không CTE thì Postgres dựng view ĐÓ HAI LẦN cho một lần mở trang.
    # Vị từ `customer_code` nằm TRONG CTE chứ không ngoài — vật hoá cả view
    # rồi mới lọc một khách là đổi một trang nhanh lấy một lượt quét toàn
    # bảng, tức đúng thứ mà tối ưu này định tránh.
    them = conn.execute("""
        WITH h AS MATERIALIZED (
            SELECT product_code, ten_hang, lan_cuoi, tre_ngay, doanh_thu_thuan,
                   trang_thai_cap
              FROM mart.khach_mat_hang WHERE customer_code = %s
        )
        SELECT khoi, ma, ten, chu, so_a FROM (
            (SELECT 'chua'::text AS khoi, h.product_code AS ma,
                    h.ten_hang AS ten, h.lan_cuoi::text AS chu,
                    h.tre_ngay::numeric AS so_a,
                    h.doanh_thu_thuan::numeric AS xep
               FROM h
              WHERE h.tre_ngay IS NOT NULL AND h.trang_thai_cap = 'mua'
              ORDER BY h.doanh_thu_thuan DESC
              LIMIT 10)
            UNION ALL
            (SELECT 'goi_y', p.product_code,
                    coalesce(nullif(p.product_name, ''), p.product_code),
                    ''::text, t.ty_suat, t.ty_suat
               FROM core.dim_product p
               JOIN mart.ty_suat_mat_hang t ON t.product_code = p.product_code
              WHERE NOT EXISTS (SELECT 1 FROM h
                                 WHERE h.product_code = p.product_code)
                AND t.ty_suat IS NOT NULL
              ORDER BY t.ty_suat DESC
              LIMIT 8)
        ) u ORDER BY khoi, xep DESC
    """, (ma,)).fetchall()

    chua_mua, goi_y = [], []
    for khoi, ma_hang, ten_hang, chu, so_a in them:
        if khoi == "chua":
            chua_mua.append({"ma": ma_hang, "ten": ten_hang, "lan_cuoi": chu,
                             "tre": int(so_a) if so_a is not None else None})
        else:
            goi_y.append({"ma": ma_hang, "ten": ten_hang,
                          "ty_suat": float(so_a) if so_a is not None else None})

    # Truy vấn B: điểm giao thẳng. (Trước 043 câu này còn gộp bảng giá của bậc
    # giá khách đang hưởng — bỏ cùng cột 売価No.コード; giá theo bậc của từng mã
    # vẫn có ở hồ sơ mã, kome/san_pham.py.)
    hai = conn.execute("""
        SELECT shipto_code, coalesce(nullif(shipto_name, ''), shipto_code),
               coalesce(address, '')
          FROM core.dim_shipto WHERE customer_code = %s
         ORDER BY shipto_code
    """, (ma,)).fetchall()

    diem_giao = [{"ma": r[0], "ten": r[1], "dia_chi": r[2]} for r in hai]

    from kome.lien_he import nhat_ky_khach
    return HoSo(khach=k, ho_so=ho, thang=thang, mat_hang=mat_hang,
                da_ngung_mua=da_ngung, lan_mua_gan_day=gan_day,
                chua_mua_thang=chua_mua, goi_y=goi_y,
                diem_giao=diem_giao, nhat_ky=nhat_ky_khach(conn, ma),
                tat_ca_mat_hang=tat_ca, ngay_mua=ngay_mua, thang_nay=thang_nay,
                hom_nay=moc)


# Trạng thái nào được coi là "cần xử lý" — khách đang rời đi. MỘT hằng dùng ở
# cả can_xu_ly() và dem_va_can_xu_ly(), thay vì chép `IN ('canh_bao',
# 'da_roi_bo')` ở hai nơi: hai bản chép là hai định nghĩa sẽ trôi khỏi nhau
# đúng cái bài học mà `_vi_tu`/`TRANG_THAI` ở trên đã ghi.
TRANG_THAI_CAN_XU_LY = ("canh_bao", "da_roi_bo")


def can_xu_ly(conn, gioi_han: int = 100, sale: str | None = None) -> list[Khach]:
    """Danh sách việc cần làm: khách đang rời đi, xếp theo tiền đang mất.

    Xếp theo DOANH THU chứ không theo mức độ im lặng: gọi lại khách ¥5 triệu
    im 3 lần nhịp thì đáng hơn khách ¥50.000 im 10 lần nhịp, dù con số thứ hai
    trông đáng báo động hơn.

    `sale`: mặc định tiện dụng, như danh_sach() — không phải hàng rào.
    """
    dieu_kien = "AND salesperson_code = %s" if sale else ""
    tham_so = [list(TRANG_THAI_CAN_XU_LY)] + ([sale] if sale else []) + [gioi_han]
    return [_khach(r) for r in conn.execute(
        f"""SELECT {_COT} FROM mart.khach_360
            WHERE trang_thai = ANY(%s) {dieu_kien}
            ORDER BY doanh_thu_thuan DESC NULLS LAST LIMIT %s""",
        tham_so).fetchall()]


def dem_va_can_xu_ly(conn, gioi_han: int = 100,
                      sale: str | None = None) -> tuple[dict[str, int], list[Khach]]:
    """Bộ đếm trạng thái TOÀN CÔNG TY + danh sách "cần xử lý" của can_xu_ly(),
    ĐÚNG MỘT lượt hỏi — thay cho `count(*) GROUP BY trang_thai` riêng cộng
    can_xu_ly() riêng của kome.tong_quan.tong_quan().

    Vì sao gộp: đo thật trên CSDL thật (2026-09-23),
    `SELECT trang_thai, count(*) FROM mart.khach_360 GROUP BY 1` một mình đã
    mất ~1.185 ms — view đắt nhất bị ĐÁNH GIÁ LẠI mỗi lần được tham chiếu
    (bất biến CTE-trùng của CLAUDE.md). Trang chủ trước đây tham chiếu nó hai
    lần (đếm + can_xu_ly) trong hai câu lệnh riêng, tức dựng view đó hai lần
    cho một lần mở trang. CTE `k` ở đây vật hoá NÓ MỘT LẦN, `d` đếm trên đó,
    `c` lọc lấy danh sách cũng trên đó.

    Bộ đếm `d` KHÔNG lọc theo `sale` (dashboard dùng nó cho thanh sức khoẻ
    TOÀN CÔNG TY); danh sách `c` thì CÓ, giống can_xu_ly().

    `d` LUÔN có đúng một dòng (json_object_agg là hàm gộp, trả NULL chứ không
    trả rỗng khi không có dòng nào) — `LEFT JOIN c ON true` nên khi `c` rỗng
    (không khách nào khớp, kể cả CSDL trống) câu lệnh vẫn trả về đúng MỘT
    dòng với mọi cột của `c` là NULL; lọc chúng ra bằng cách kiểm tra
    `customer_code IS NOT NULL` trước khi coi một dòng là một Khach thật.
    """
    dieu_kien = "AND salesperson_code = %s" if sale else ""
    tham_so = ([list(TRANG_THAI_CAN_XU_LY)]
               + ([sale] if sale else []) + [gioi_han])
    rows = conn.execute(f"""
        WITH k AS MATERIALIZED (SELECT {_COT} FROM mart.khach_360),
             d AS (
                 SELECT json_object_agg(trang_thai, n) AS dem
                   FROM (SELECT trang_thai, count(*) AS n FROM k GROUP BY 1) x
             ),
             c AS (
                 SELECT * FROM k WHERE trang_thai = ANY(%s) {dieu_kien}
                 ORDER BY doanh_thu_thuan DESC NULLS LAST LIMIT %s
             )
        SELECT d.dem, c.* FROM d LEFT JOIN c ON true
        ORDER BY c.doanh_thu_thuan DESC NULLS LAST
    """, tham_so).fetchall()

    dem = rows[0][0] or {} if rows else {}
    khach = [_khach(r[1:]) for r in rows if r[1] is not None]
    return dem, khach



@dataclass
class TongQuan:
    """Bốn khối phân tích + hai bộ đếm của trang danh sách, MỘT truy vấn."""
    nhom: dict[str, int]
    tong: int
    hang: list[tuple[str, int]]
    tinh: list[tuple[str, int]]
    nhan_vien: list[dict]
    # Số khách theo từng trạng thái, dùng cho dải chip "Tất cả / Cần gọi lại
    # / …". CÓ theo nhom/hang/tinh/sale, KHÔNG theo `loc` — xem docstring của
    # tong_quan_danh_ba().
    dem_trang_thai: dict[str, int] = field(default_factory=dict)
    # Tổng khách TOÀN CÔNG TY cho liên kết "Xem tất cả N khách →". Không lọc
    # gì hết, kể cả sale: chính liên kết đó bỏ mọi bộ lọc, nên con số phải là
    # con số người ta sẽ thấy sau khi bấm.
    tong_tat_ca: int = 0
    # Giai đoạn 2 (cùng lượt hỏi): doanh thu luỹ kế theo hạng / tỉnh (khối
    # phân tích của gói thiết kế ghi "N khách · ¥…"), số khách theo nhãn tháng
    # (036 — phân khúc "Mua đều, tháng này chưa", theo `sale` như nhóm việc),
    # và số khách chưa ai phụ trách (TOÀN CÔNG TY: liên kết của nó thay bộ lọc
    # người phụ trách, nên con số là con số sau khi bấm).
    hang_tien: dict[str, int] = field(default_factory=dict)
    tinh_tien: dict[str, int] = field(default_factory=dict)
    thang: dict[str, int] = field(default_factory=dict)
    chua_pt: int = 0
    # Mọi tỉnh có khách (theo `sale`), đông -> ít — cho Ô CHỌN tỉnh; khối
    # "Tập trung ở đâu" vẫn là `tinh` (top 8 + "(không rõ)").
    tinh_day_du: list[tuple[str, int]] = field(default_factory=list)
    # Khoảng xem (đợt B): số khách CÓ phiếu trong khoảng (theo `sale`, như
    # nhóm việc) — chip "Có mua trong khoảng".
    co_mua: int = 0


# Thứ tự hiển thị của hạng. S trước D, không phải thứ tự bảng chữ cái ngẫu
# nhiên mà Postgres trả về.
THU_TU_HANG = ("S", "A", "B", "C", "D")


def tong_quan(db: dict, sale: str | None = None, nhom: str | None = None,
              hang=None, tinh: str | None = None, *, tim: str = "",
              thang: str | None = None, co_mua: bool = False) -> TongQuan:
    """Bốn khối phân tích + các bộ đếm của trang danh sách, trên danh bạ `db`.

    BỐN BỘ LỌC, HAI PHẠM VI (giữ nguyên từ bản SQL):
      * `sale` — mọi khối và mọi bộ đếm đều theo (trừ `tong_tat_ca`, `chua_pt`).
      * `nhom`/`hang`/`tinh` (và từ giai đoạn 2: `tim`, `thang` — ô chọn trạng
        thái của giao diện React GIỮ mọi bộ lọc khác khi đổi) — CHỈ
        `dem_trang_thai` theo. Khối phân tích thì KHÔNG: mỗi khối là ô ĐIỀU
        KHIỂN của chính bộ lọc mang tên nó; tự lọc theo mình thì bấm một mục
        xong các con số khác về 0 hết.
      * `loc` (trạng thái) — KHÔNG bộ đếm nào theo: `dem_trang_thai` chính là
        nhãn của ô chọn trạng thái.
    `tong_tat_ca` không lọc gì (liên kết của nó bỏ MỌI bộ lọc). `chua_pt` là
    toàn công ty (liên kết của nó THAY bộ lọc người phụ trách)."""
    theo_sale = _loc(db["khach"], sale=sale)
    dem_ds = _loc(theo_sale, nhom=nhom, hang=hang, tinh=tinh, tim=tim, thang=thang, co_mua=co_mua)
    nhom_dem = {n: sum(1 for k in theo_sale if n in (k["nhom"] or [])) for n in ("im", "tut", "moi")}
    hang_dem, hang_tien = {}, {}
    tinh_dem, tinh_tien = {}, {}
    thang_dem, dem = {}, {}
    for k in theo_sale:
        if k["hang"]:
            hang_dem[k["hang"]] = hang_dem.get(k["hang"], 0) + 1
            hang_tien[k["hang"]] = hang_tien.get(k["hang"], 0) + (k["doanh_thu"] or 0)
        t = k["tinh"] or KHONG_RO
        tinh_dem[t] = tinh_dem.get(t, 0) + 1
        tinh_tien[t] = tinh_tien.get(t, 0) + (k["doanh_thu"] or 0)
        if k["nhan_thang"]:
            thang_dem[k["nhan_thang"]] = thang_dem.get(k["nhan_thang"], 0) + 1
    for k in dem_ds:
        dem[k["trang_thai"]] = dem.get(k["trang_thai"], 0) + 1
    # "(không rõ)" phải được tách ra KHỎI phép xếp hạng trước khi cắt top 8,
    # không phải trộn chung rồi cắt: nhóm này thường chỉ vài khách nên đứng
    # NGOÀI top 8 nếu xếp chung — trộn rồi cắt sẽ âm thầm đánh rơi nó khỏi khối
    # "Tập trung ở đâu", đúng nhóm khách CẦN dọn lại.
    tinh_that = sorted(((t, n) for t, n in tinh_dem.items() if t != KHONG_RO),
                       key=lambda x: (-x[1], x[0]))[:8]
    tinh_ds = tinh_that + ([(KHONG_RO, tinh_dem[KHONG_RO])] if KHONG_RO in tinh_dem else [])
    return TongQuan(
        nhom=nhom_dem, tong=len(theo_sale),
        hang=[(h, hang_dem.get(h, 0)) for h in THU_TU_HANG], tinh=tinh_ds,
        # Xếp theo DOANH THU chứ không theo số khách: khối này trả lời "ai
        # đang gánh bao nhiêu tiền". Đọc mart.tai_nhan_vien (so_khach_canh_bao
        # ĐỌC nhóm việc — migration 022), không đếm lại ở đây.
        nhan_vien=[{"ma": n["ma"], "ten": n["ten"], "so_khach": n["so_khach"],
                    "doanh_thu": int(n["doanh_thu"] or 0), "canh_bao": int(n["canh_bao"] or 0)}
                   for n in db["nhan_vien"]],
        dem_trang_thai=dem, tong_tat_ca=len(db["khach"]),
        hang_tien=hang_tien, tinh_tien={t: tinh_tien[t] for t, _ in tinh_ds},
        thang=thang_dem, chua_pt=sum(1 for k in db["khach"] if not k["co_pt"]),
        co_mua=sum(1 for k in theo_sale if k.get("so_phieu_khoang")),
        tinh_day_du=sorted(tinh_dem.items(), key=lambda x: (x[0] == KHONG_RO, -x[1], x[0])),
    )


def tong_quan_danh_ba(conn, sale: str | None = None, nhom: str | None = None,
                      hang=None, tinh: str | None = None) -> TongQuan:
    """`tong_quan` trên danh bạ vừa đọc — ĐÚNG MỘT lượt hỏi."""
    return tong_quan(danh_ba(conn), sale, nhom=nhom, hang=hang, tinh=tinh)
