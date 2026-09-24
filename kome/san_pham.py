"""Sản phẩm và Kho hàng: danh sách mã hàng, hồ sơ một mã, và màn kho.

Như kome/khach_hang.py: KHÔNG định nghĩa chỉ số ở đây, không tự mở kết nối,
không tự commit. Mọi công thức nằm ở schema `mart` (migration 023).

HAI LUẬT RIÊNG CỦA FILE NÀY, cả hai đều đến từ dữ liệu thật:

1. **"Không biết" khác "bằng không".** `ton` là NULL cho 90/232 mã không có
   dòng nào trong bản xuất 在庫一覧. NULL phải đi qua tầng này NGUYÊN VẸN để
   trang hiện `—`. Một `or 0` biến "chưa từng nhập kho" thành "kho đã hết", và
   người đọc sẽ đi đặt hàng cho một mã có thể đang đầy kho. Ngoại lệ DUY NHẤT
   là TIỀN (xem ghi chú ở `_sp`).
2. **Số lượng CÓ phần thập phân** (`83.75 ケース`). Không ép `int` lên bất kỳ
   cột số lượng nào. Tiền thì luôn là số nguyên yên.
"""
from dataclasses import dataclass, field
from datetime import date

from kome.bao_cao import NGANH_TRONG

MOI_TRANG = 50

# Nhãn tiếng Việt + màu cho `mart.san_pham_360.trang_thai`. SÁU nhãn, không
# phải bốn: migration 023 tách "không biết tồn" (`chua_ro_ton`, 90/232 mã) ra
# khỏi "tồn bằng 0", và tách "đã ngừng kinh doanh" (`ngung`) ra khỏi "hết hàng
# cần đặt gấp". Thiếu một nhãn ở đây thì trang hiện mã thô cho đúng nhóm mã
# đông nhất.
#
# Thứ tự LÀ thứ tự ưu tiên hiển thị: việc cần làm gấp đứng trước, việc không
# làm gì được đứng sau.
TRANG_THAI_TON = {
    "het_hang":    ("Hết hàng", "loi"),
    "sap_thieu":   ("Sắp thiếu", "canh"),
    "ton_chet":    ("Tồn chết", "canh"),
    "du":          ("Đủ hàng", "ok"),
    "ngung":       ("Ngừng kinh doanh", "nhat"),
    "chua_ro_ton": ("Chưa rõ tồn", "nhat"),
}

# Nhãn cho `mart.ton_hien_tai.loai_han` — BỐN giá trị, và hai giá trị cuối
# KHÔNG được gộp làm một: `khong_han` là "hàng này không có hạn sử dụng" (một
# lời khẳng định về hàng), còn `khong_ro` là "ta không đọc được ô này" (một
# lời thú nhận về dữ liệu). Hiện chung một nhãn là biến cái thứ hai thành cái
# thứ nhất, và lô đó biến mất khỏi mọi cảnh báo hạn một cách im lặng.
LOAI_HAN = {
    "ngay":      ("Có hạn", "ok"),
    "khong_han": ("Không có hạn dùng", "nhat"),
    "trong":     ("Chưa ghi hạn", "canh"),
    "khong_ro":  ("Không đọc được hạn", "loi"),
}

# 荷姿区分 — hai mã thật sự có trong dữ liệu (xem CLAUDE.md). Mã lạ thì hiện
# nguyên mã chứ không đoán, y hệt kome/khach_hang.py::QUY_CACH.
QUY_CACH = {"00": "バラ (lẻ)", "02": "ケース (thùng)"}

# Cột được phép sắp xếp. Danh sách trắng, KHÔNG ghép thẳng tham số URL vào câu
# SQL — đó là đường mở cho SQL injection, và trang này sắp nằm trên Internet.
#
# `du_ban` xếp TĂNG dần: câu hỏi của cột đó là "cái nào sắp hết trước", nên số
# nhỏ mới là số đáng nhìn. NULLS LAST ở cả hai chiều vì "không tính được" chưa
# bao giờ là câu trả lời đáng đứng đầu bảng.
SAP_XEP = {
    "doanh_thu": "doanh_thu_thuan DESC NULLS LAST",
    "lai_gop":   "lai_gop DESC NULLS LAST",
    "ty_suat":   "ty_suat DESC NULLS LAST",
    "ton":       "ton DESC NULLS LAST",
    "du_ban":    "du_ban_ngay ASC NULLS LAST",
    "so_khach":  "so_khach DESC NULLS LAST",
    "ten":       "ten_hang ASC",
}

# Bao nhiêu ngày nữa thì gọi là "cận hạn".
#
# Đây là một NGƯỠNG NGHIỆP VỤ nằm trong Python, và luật của dự án nói định
# nghĩa chỉ số chỉ ở `mart/`. Lý do vẫn để ở đây: nó không phải một định nghĩa
# chỉ số mà là một CỬA SỔ NHÌN của màn kho — cùng loại với ngưỡng 90 ngày mà
# kome/khach_hang.py::ho_so() đã dùng cho khối "đã ngừng mua". Nếu ngày nào đó
# có thêm một màn thứ hai cũng hỏi "lô nào cận hạn", ngưỡng này phải chuyển
# thành một view ở mart chứ không được chép sang file kia.
#
# MỘT hằng cho CẢ ô tổng quan lẫn bảng cận hạn: ô nói "12 lô cận hạn" mà bảng
# ngay dưới liệt kê 30 dòng là hai con số mâu thuẫn trên cùng một màn hình.
#
# CHẶN DƯỚI là 0, không phải âm vô cực: "đã quá hạn" và "sắp hết hạn" là HAI
# việc khác nhau với hàng thực phẩm. Không có chặn dưới thì một lô quá hạn còn
# sót trong bản xuất đứng vĩnh viễn ở đầu bảng (xếp tăng dần theo số ngày còn
# lại) và cộng vào ô đếm mãi mãi — cái đang cần XỬ LÝ NGAY bị trộn vào danh
# sách cái cần theo dõi. Lô quá hạn có khối riêng: `Kho.qua_han`.
CAN_HAN_NGAY = 90

# Vị từ "lô cận hạn"/"lô đã quá hạn" trên mart.ton_hien_tai (bí danh BẮT BUỘC
# `t`), viết MỘT LẦN cho cả `kho_hang()` (hai lượt hỏi) và `lo_can_han()`
# (dùng riêng cho dashboard `/`) — hai bản chép tay là hai ngưỡng "cận hạn"
# sẽ trôi khỏi nhau, đúng bài học của `_vi_tu` ở kome/khach_hang.py.
VI_TU_CAN_HAN = "t.loai_han = 'ngay' AND t.han_con_lai BETWEEN 0 AND %s"
VI_TU_QUA_HAN = "t.loai_han = 'ngay' AND t.han_con_lai < 0"


@dataclass
class SanPham:
    ma: str
    ten: str
    nhom: str | None
    doanh_thu: int
    lai_gop: int
    ty_suat: float | None
    so_luong_ban: float | None
    # NULL = "mã không có dòng nào trong 在庫一覧", KHÔNG phải 0. Xem đầu file.
    ton: float | None
    # HAI cột tốc độ, cố ý. `toc_do_ngay` là trung bình mẫu số 90 cố định;
    # `toc_do_ngay_theo_tuoi` chia cho tuổi thật của mã và LÀ con số quyết định
    # `du_ban_ngay` với `trang_thai`. Trang phải hiện cột thứ hai — hiện cột
    # thứ nhất cạnh hai ô kia là bày ra ba con số không khớp nhau.
    toc_do_ngay: float | None
    toc_do_ngay_theo_tuoi: float | None
    du_ban_ngay: float | None
    trang_thai: str
    so_khach: int
    lan_dau: date | None
    lan_cuoi: date | None

    @property
    def nhan_trang_thai(self) -> str:
        return TRANG_THAI_TON.get(self.trang_thai, (self.trang_thai, "nhat"))[0]

    @property
    def mau(self) -> str:
        return TRANG_THAI_TON.get(self.trang_thai, ("", "nhat"))[1]


@dataclass
class TrangSanPham:
    hang: list[SanPham]
    tong: int
    trang: int
    so_trang: int
    tim: str
    loc: str
    sap: str
    # Số mã theo từng trạng thái, cho dải chip lọc. CÓ theo `tim`, KHÔNG theo
    # `loc` — xem docstring của danh_sach().
    dem_trang_thai: dict[str, int] = field(default_factory=dict)


@dataclass
class HoSoSanPham:
    sp: SanPham
    thang: list[dict]
    khach_mua: list[dict]
    khach_ngung: list[dict]
    ton: list[dict]
    bac_gia: list[dict]


@dataclass
class Kho:
    ngay_chup: date | None
    o_tong_quan: dict[str, int]
    dong: list[dict]
    theo_kho: list[dict]
    can_han: list[dict]
    ds_kho: list[tuple[str, str]]
    kho: str
    loc: str
    # Lô ĐÃ quá hạn, tách hẳn khỏi `can_han` (lô sắp hết hạn). Trộn hai thứ là
    # trộn "xử lý ngay" với "theo dõi" — xem ghi chú ở CAN_HAN_NGAY.
    qua_han: list[dict] = field(default_factory=list)
    # Tổng giá trị của ĐÚNG các dòng bảng tồn đang hiện (theo CẢ HAI bộ lọc) —
    # cộng lại từ `dong`, nên ô "Giá trị tồn" không thể lệch tổng của bảng.
    gia_tri_ton: int = 0
    # Ảnh chụp tồn sớm nhất trong kho (040) — `ngay_chup` None mà cột này có giá
    # trị nghĩa là đang xem lùi về TRƯỚC ảnh chụp đầu tiên.
    ngay_chup_dau: date | None = None


_COT = """product_code, ten_hang, nhom, doanh_thu_thuan, lai_gop, ty_suat,
          so_luong_ban, ton, toc_do_ngay, toc_do_ngay_theo_tuoi, du_ban_ngay,
          trang_thai, so_khach, lan_dau, lan_cuoi"""


def _so(x) -> float | None:
    """Số lượng/tỷ lệ: giữ phần thập phân, và giữ NULL là None.

    Không `or 0`: đó là cách "chưa từng nhập kho" biến thành "kho đã hết".
    Không `int()`: `83.75 ケース` là số thật trong dữ liệu OBC."""
    return float(x) if x is not None else None


def _sp(r) -> SanPham:
    # TIỀN là ngoại lệ DUY NHẤT của luật "giữ None": `doanh_thu_thuan` NULL ở
    # đây nghĩa là mã không có dòng bán nào, tức doanh thu đúng bằng 0 yên —
    # một số 0 ĐÃ BIẾT, khác hẳn `ton` (một con số ta không có). Và template
    # định dạng tiền bằng "{:,}".format(), vốn nổ trên None.
    return SanPham(
        ma=r[0], ten=r[1], nhom=r[2],
        doanh_thu=int(r[3] or 0), lai_gop=int(r[4] or 0), ty_suat=_so(r[5]),
        so_luong_ban=_so(r[6]), ton=_so(r[7]),
        toc_do_ngay=_so(r[8]), toc_do_ngay_theo_tuoi=_so(r[9]),
        du_ban_ngay=_so(r[10]), trang_thai=r[11], so_khach=int(r[12] or 0),
        lan_dau=r[13], lan_cuoi=r[14])


def _dk_tim(tim: str = "") -> tuple[str, list]:
    """Mảnh điều kiện của ô tìm kiếm. Tìm theo mã, tên hàng hoặc nhóm cùng lúc
    — người bán không nhớ mình đang cầm mảnh thông tin nào."""
    if not tim.strip():
        return "", []
    return ("""(product_code ILIKE %s OR ten_hang ILIKE %s OR nhom ILIKE %s)""",
            [f"%{tim.strip()}%"] * 3)


def _dk_loc(loc: str = "") -> tuple[str, list]:
    """Mảnh điều kiện của dải chip trạng thái tồn."""
    return ("trang_thai = %s", [loc]) if loc in TRANG_THAI_TON else ("", [])


def _vi_tu(tim: str = "", loc: str = "") -> tuple[str, list]:
    """Mệnh đề WHERE lọc `mart.san_pham_360`, viết MỘT LẦN cho mọi chỗ đọc.

    Vì sao dùng chung chứ không chép (bài học của đợt 4a): bộ đếm trạng thái và
    chính bảng mà nó mở ra phải lọc GIỐNG HỆT nhau. Hai bản chép tay là hai bộ
    lọc sẽ trôi khỏi nhau, và triệu chứng là một con số nói dối đúng cái danh
    sách nó mở ra.

    Hai mảnh tách riêng ở trên vì `danh_sach()` cần chúng RỜI NHAU (lọc `tim`
    một lần trong CTE, rồi lọc `loc` trên chính CTE đó) — nhưng vẫn chỉ có
    MỘT bản của mỗi mảnh, nên không có gì để trôi.
    """
    manh = [_dk_tim(tim), _dk_loc(loc)]
    dieu_kien = [sql for sql, _ in manh if sql]
    tham_so = [p for _, ps in manh for p in ps]
    return (("WHERE " + " AND ".join(dieu_kien)) if dieu_kien else ""), tham_so


def danh_sach(conn, tim: str = "", loc: str = "", sap: str = "doanh_thu",
              trang: int = 1) -> TrangSanPham:
    """Danh mục mã hàng, có tìm kiếm và lọc theo trạng thái tồn. HAI lượt hỏi.

    `dem_trang_thai` theo `tim` nhưng KHÔNG theo `loc`: nó chính là nhãn của
    dải chip trạng thái, và một ô điều khiển tự lọc theo mình thì bấm vào một
    chip xong các con số khác về 0 hết — không ai quay lại được.

    `tong` thì ngược lại, theo CẢ HAI: nó phải là số dòng mà chính bảng bên
    dưới đang hiện.
    """
    dk_tim, p_tim = _dk_tim(tim)
    dk_loc, p_loc = _dk_loc(loc)
    where, tham_so = _vi_tu(tim=tim, loc=loc)

    # Lượt hỏi 1: bộ đếm trạng thái + tổng, gộp làm một. ORDER BY nằm ở LỚP
    # NGOÀI — thứ tự dòng giữa các nhánh của UNION ALL không được Postgres bảo
    # đảm, và đợt 4a đã dính đúng lỗi đó một lần.
    #
    # `tong` do SQL đếm chứ không phải Python cộng dồn `dem_trang_thai`: hai bộ
    # đếm lọc khác nhau (`loc`), nên cộng dồn là ra một con số thứ ba không
    # thuộc về ai.
    #
    # CTE `AS MATERIALIZED`, ghi TƯỜNG MINH: hai nhánh dưới cùng đọc
    # mart.san_pham_360, và Postgres KHÔNG gộp hai truy vấn con giống nhau —
    # mỗi lần tham chiếu là một lần ĐÁNH GIÁ LẠI cả view, kéo theo
    # ty_suat_mat_hang, toc_do_ban (2 lượt quét fact_sales_line) và CTE `sl`.
    # Ngân sách "<= 2 truy vấn" đếm SỐ LƯỢT HỎI, không đếm sức tính, nên nó
    # không bắt được lớp lỗi này. 232 dòng thì vật hoá một lần rồi quét lại là
    # rẻ; cái đắt là dựng lại. Không dựa vào mặc định của Postgres 12+ (CTE chỉ
    # tham chiếu một lần thì được nội tuyến): chỗ này người sau cần ĐỌC THẤY ý
    # định, không phải suy ra nó từ số lần tham chiếu.
    #
    # `tim` lọc BÊN TRONG CTE (giữ được vị từ đẩy xuống), `loc` lọc TRÊN CTE —
    # đúng phân vai cũ: bộ đếm không theo `loc`, `tong` thì có.
    rows = conn.execute(f"""
        WITH sp AS MATERIALIZED (
            SELECT trang_thai FROM mart.san_pham_360
            {("WHERE " + dk_tim) if dk_tim else ""}
        )
        SELECT khoi, khoa, so FROM (
            SELECT 'dem'::text AS khoi, trang_thai AS khoa, count(*) AS so
              FROM sp
             GROUP BY trang_thai
            UNION ALL
            SELECT 'tong', '', count(*) FROM sp
            {("WHERE " + dk_loc) if dk_loc else ""}
        ) u ORDER BY khoi, khoa
    """, p_tim + p_loc).fetchall()
    dem = {khoa: int(so) for khoi, khoa, so in rows if khoi == "dem"}
    tong = next((int(so) for khoi, _, so in rows if khoi == "tong"), 0)

    thu_tu = SAP_XEP.get(sap, SAP_XEP["doanh_thu"])
    trang = max(1, trang)
    hang = conn.execute(
        f"""SELECT {_COT} FROM mart.san_pham_360 {where}
            ORDER BY {thu_tu} LIMIT %s OFFSET %s""",
        tham_so + [MOI_TRANG, (trang - 1) * MOI_TRANG]).fetchall()

    return TrangSanPham(
        hang=[_sp(r) for r in hang], tong=tong, trang=trang,
        so_trang=max(1, -(-tong // MOI_TRANG)), tim=tim, loc=loc, sap=sap,
        dem_trang_thai=dem)


def ho_so(conn, ma: str) -> HoSoSanPham | None:
    """Hồ sơ một mã hàng. None nếu mã không tồn tại.

    NGÂN SÁCH TRUY VẤN: đúng 5 lượt hỏi, và 5 là TRẦN (đặc tả 4b §5.5). Đo
    thật 2026-09-22: một round-trip rỗng tới pooler Tokyo mất 47 ms, một lượt
    hỏi thật ~260 ms. Có test canh — tests/test_san_pham.py::
    test_ho_so_san_pham_khong_qua_5_truy_van. Khối thứ sáu muốn thêm thì phải
    gộp vào một trong năm khối đã có, không nới trần.
    """
    r = conn.execute(
        f"SELECT {_COT} FROM mart.san_pham_360 WHERE product_code = %s",
        (ma,)).fetchone()
    if r is None:
        return None

    thang = [dict(zip(("thang", "so_luong", "doanh_thu", "lai_gop"), t))
             for t in conn.execute(
        """SELECT thang, so_luong, doanh_thu_thuan, lai_gop
           FROM mart.san_pham_theo_thang WHERE product_code = %s
           ORDER BY thang""", (ma,)).fetchall()]

    # Hai khối khách gộp làm MỘT lượt hỏi: cùng một view, cùng bộ cột, chỉ khác
    # vị từ — đúng ca mà UNION ALL không phải đệm NULL cho nhánh nào.
    #
    # HAI KHỐI ĐỌC `trang_thai_cap` CỦA mart.khach_mat_hang (migration 024),
    # không viết lại vị từ ở đây. Đó là định nghĩa DUY NHẤT của "cặp (khách,
    # mã) đang ở trạng thái nào", dùng chung với hai khối của /khach-hang/{mã}
    # — trước 024 hai màn có hai công thức và trả lời ngược nhau về cùng một
    # cặp.
    #
    # Nhãn ba giá trị: `'khong_goi'` (khách bị OBC đánh dấu ※廃業※, xét trước
    # hết), `'ngung'` (im lặng >= 2 × NHỊP RIÊNG của chính cặp đó), `'mua'`
    # (còn lại). Không phải ngưỡng chung: đo thật, ngưỡng 90 ngày bỏ sót 49
    # khách đang rời đi và báo động nhầm 34 khách vẫn mua bình thường. Khách
    # mua 7 ngày/lần im 60 ngày đã rời đi từ lâu; khách mua 120 ngày/lần im
    # 100 ngày vẫn đang mua bình thường.
    #
    # MỖI NHÁNH SO BẰNG VỚI ĐÚNG NHÃN CỦA MÌNH, KHÔNG NHÁNH NÀO DÙNG `NOT`.
    # Hai khối này là DANH SÁCH BÁN HÀNG, nên cả hai đều không được chứa khách
    # đã đóng cửa — và `'khong_goi'` là một giá trị RIÊNG nên nó tự rơi ra
    # ngoài cả hai mà không nhánh nào phải biết ※廃業※ là gì. Bản trước của 024
    # dùng boolean `ngung_mua` gói cổng ※廃業※ vào bên trong, nên `NOT
    # ngung_mua` LUÔN đúng với một doanh nghiệp đã đóng cửa: họ trượt thẳng từ
    # khối "đã ngừng" sang khối "ĐANG mua mã này" — trang khẳng định một công
    # ty đã phá sản vẫn đang lấy hàng — và nhánh 'mua' phải tự JOIN lấy
    # `k.da_ngung` để đắp lại. Nhãn dẹp chỗ đắp tay đó; `da_ngung` nay chỉ được
    # đọc một lần, trong view.
    #
    # Sự thật lịch sử của cặp đó KHÔNG mất: view vẫn giữ đủ dòng, và hồ sơ của
    # chính khách ※廃業※ vẫn hiện bảng top-15 mặt hàng như cũ.
    #
    # `xep` là hạng TRONG TỪNG NHÁNH, tính bằng row_number() theo đúng khoá mà
    # nhánh đó dùng để cắt top-N. ORDER BY ở lớp NGOÀI đọc `xep` chứ không tin
    # vào thứ tự dòng của nhánh — thứ tự đó không được bảo đảm qua UNION ALL,
    # và đợt 4a đã dính đúng lỗi này. (ORDER BY … LIMIT trong nhánh vẫn cần,
    # nhưng để CHỌN đúng top-N, không phải để giữ thứ tự.)
    #
    # LEFT JOIN khach_360 chứ không JOIN: một khách có dòng bán thì luôn có
    # dòng ở khach_360 hôm nay, nhưng mất tên khách là mất cả DÒNG nếu dùng
    # INNER — và đây là khối "ai đang mua mã này", nơi thiếu một khách nguy
    # hiểm hơn nhiều so với hiện mã thay cho tên. khach_360 ở đây CHỈ để lấy
    # TÊN: cờ ※廃業※ không còn được đọc ở chỗ này nữa, nó đã nằm trong nhãn.
    #
    # HAI CTE `AS MATERIALIZED`, ghi TƯỜNG MINH: cả hai nhánh đều đọc
    # khach_mat_hang và khach_360, mà Postgres KHÔNG gộp hai truy vấn con
    # giống nhau — mỗi lần tham chiếu là một lần dựng lại cả view (khach_360
    # gộp toàn bộ mart.lan_mua). Vị từ `product_code = %s` nằm BÊN TRONG CTE
    # nên vẫn đẩy xuống được; vật hoá ở đây chỉ bỏ đi lần dựng THỨ HAI.
    khach = conn.execute(f"""
        WITH h AS MATERIALIZED (
            SELECT customer_code, doanh_thu_thuan, so_luong, so_lan, lan_cuoi,
                   nhip_ngay, tre_ngay, trang_thai_cap
              FROM mart.khach_mat_hang WHERE product_code = %s
        ), k AS MATERIALIZED (
            SELECT customer_code, ten FROM mart.khach_360
        )
        SELECT khoi, ma, ten, doanh_thu, so_luong, so_lan, lan_cuoi, nhip, tre
        FROM (
            (SELECT 'mua'::text AS khoi, h.customer_code AS ma,
                    coalesce(nullif(k.ten, ''), h.customer_code) AS ten,
                    h.doanh_thu_thuan AS doanh_thu, h.so_luong, h.so_lan,
                    h.lan_cuoi, h.nhip_ngay AS nhip, h.tre_ngay AS tre,
                    row_number() OVER (ORDER BY h.doanh_thu_thuan DESC NULLS LAST)
                      AS xep
               FROM h
               LEFT JOIN k ON k.customer_code = h.customer_code
              WHERE h.trang_thai_cap = 'mua'
              ORDER BY h.doanh_thu_thuan DESC NULLS LAST
              LIMIT 20)
            UNION ALL
            (SELECT 'ngung', h.customer_code,
                    coalesce(nullif(k.ten, ''), h.customer_code),
                    h.doanh_thu_thuan, h.so_luong, h.so_lan, h.lan_cuoi,
                    h.nhip_ngay, h.tre_ngay,
                    row_number() OVER (ORDER BY h.doanh_thu_thuan DESC NULLS LAST)
               FROM h
               LEFT JOIN k ON k.customer_code = h.customer_code
              WHERE h.trang_thai_cap = 'ngung'
              ORDER BY h.doanh_thu_thuan DESC NULLS LAST
              LIMIT 10)
        ) u ORDER BY khoi, xep
    """, (ma,)).fetchall()

    def _khach(r):
        return {"ma": r[1], "ten": r[2], "doanh_thu": int(r[3] or 0),
                "so_luong": _so(r[4]), "so_lan": r[5], "lan_cuoi": r[6],
                "nhip": _so(r[7]), "tre": r[8]}

    khach_mua = [_khach(r) for r in khach if r[0] == "mua"]
    khach_ngung = [_khach(r) for r in khach if r[0] == "ngung"]

    # `nhan_han`/`mau_han` là CHUỖI ở cả hai màn — xem ghi chú ở kho_hang::_dong.
    ton = [{"kho": t[0], "ten_kho": t[1], "so_luong": _so(t[2]),
            "gia_tri": int(t[3] or 0), "best_before": t[4], "loai_han": t[5],
            "nhan_han": LOAI_HAN.get(t[5], (t[5] or "—", "nhat"))[0],
            "mau_han": LOAI_HAN.get(t[5], (t[5] or "—", "nhat"))[1],
            "han_con_lai": t[6]}
           for t in conn.execute(
        """SELECT warehouse_code, ten_kho, so_luong, gia_tri, best_before,
                  loai_han, han_con_lai
           FROM mart.ton_hien_tai WHERE product_code = %s
           ORDER BY warehouse_code, han_con_lai NULLS LAST""", (ma,)).fetchall()]

    # DISTINCT ON (price_level, pack_code) … ORDER BY valid_from DESC:
    # core.fact_price_list giữ LỊCH SỬ giá — kome/loaders/price.py ghi một dòng
    # MỚI mỗi lần nạp master. Không lọc thì sau ba lần nạp, một bậc giá hiện ba
    # con số khác nhau dưới nhãn "giá đáng lẽ phải bán", trên đúng màn hình
    # người ta nhìn TRƯỚC KHI báo giá cho khách.
    bac_gia = [{"bac": g[0], "quy_cach": QUY_CACH.get(g[1], g[1]),
                "gia": int(g[2]), "tu_ngay": g[3]}
               for g in conn.execute(
        """SELECT DISTINCT ON (price_level, pack_code)
                  price_level, pack_code, price_ex_tax, valid_from
           FROM core.fact_price_list WHERE product_code = %s
           ORDER BY price_level, pack_code, valid_from DESC""", (ma,)).fetchall()]

    return HoSoSanPham(sp=_sp(r), thang=thang, khach_mua=khach_mua,
                       khach_ngung=khach_ngung, ton=ton, bac_gia=bac_gia)


def kho_hang(conn, kho: str = "", loc: str = "") -> Kho:
    """Màn Kho hàng: bốn ô tổng quan, tồn hiện tại, cận hạn, giá trị theo kho.

    ĐÚNG HAI lượt hỏi (đặc tả 4b §5.5), có test canh.

    HAI BỘ LỌC, VÀ MỖI KHỐI THEO ĐÚNG NHỮNG BỘ LỌC NÓ KHÔNG ĐIỀU KHIỂN. Quy
    tắc (của `tong_quan_danh_ba` đợt 4a, và của `danh_sach()` ngay trên):

      * Khối NỘI DUNG theo MỌI bộ lọc: bảng tồn, khối cận hạn, khối quá hạn,
        ô đếm "số lô cận hạn", ô "giá trị tồn chết" — cả `kho` lẫn `loc`.
      * Khối ĐIỀU KHIỂN không theo bộ lọc của CHÍNH NÓ, nhưng vẫn theo bộ lọc
        kia: "giá trị theo kho" và danh sách kho điều khiển `kho` nên không
        theo `kho`, nhưng CÓ theo `loc`. Hai ô đếm trạng thái điều khiển `loc`
        nên không theo `loc`.

    Vì sao: một ô điều khiển tự lọc theo mình thì bấm vào một mục xong các con
    số khác về 0 hết, không ai quay lại được. Còn một con số KHÔNG theo bộ lọc
    trực giao thì tệ ngược lại — chọn `loc='ton_chet'` mà "giá trị theo kho"
    vẫn hiện tổng TOÀN BỘ kho là hai con số cạnh nhau trên một màn hình, không
    con số nào nói mình đang nói về tập nào.

    NGOẠI LỆ CÓ CHỦ Ý: hai ô đếm "số mã hết hàng"/"số mã sắp thiếu" không theo
    `kho`, và cũng không theo `loc` (chúng điều khiển `loc`). `trang_thai` là
    thuộc tính của MỘT MÃ tính trên tổng mọi kho (xem migration 023) — không
    có thứ gọi là "mã hết hàng ở kho 0001". Lọc chúng theo kho là bịa ra một
    con số không có định nghĩa nào ở `mart`.

    Ô "giá trị tồn chết" thì KHÔNG nằm trong ngoại lệ đó, dù nó cũng nói về
    `trang_thai`: cái được cộng là `gia_tri`, và giá trị thì CÓ theo từng kho.
    "Phần hàng chết đang chiếm chỗ tại kho này" là câu hỏi có nghĩa và tính
    được — đúng câu hỏi của người vừa lọc theo kho. Bỏ `{dk_kho}` ở đó thì một
    con số YÊN của mọi kho đứng ngay trên một bảng chỉ còn một kho, và công ty
    có 2 kho nên sai số gần 2× — trên đúng con số dùng để quyết định xả hàng.
    """
    # Lượt hỏi 1: bốn ô tổng quan + giá trị theo kho + danh sách kho + ngày
    # chụp. ORDER BY ở LỚP NGOÀI, không trong nhánh.
    #
    # Cột `so` mang nghĩa KHÁC NHAU theo `khoi` (số mã / số lô / số yên / số
    # dòng) — đó là cái giá của việc gộp, và hai vòng đọc ngay dưới là chỗ duy
    # nhất biết quy ước đó. `count(*)::numeric` ở nhánh đầu là bắt buộc: các
    # nhánh sau trả `sum(gia_tri)` kiểu numeric, và UNION ALL đòi cùng kiểu.
    #
    # Danh sách kho đọc từ core.dim_warehouse chứ không từ chính các dòng tồn:
    # một kho tạm thời trống vẫn phải có trong ô lọc, và tên kho là tên nghiệp
    # vụ của OBC (`1002 新・賞味期限用`) — không viết cứng tên nào.
    # Hai mảnh vị từ, dựng MỘT LẦN rồi dùng lại ở cả hai lượt hỏi — chép tay
    # là hai bộ lọc sẽ trôi khỏi nhau, đúng lớp lỗi mà `_vi_tu` ở trên né.
    # `dk_kho` cần bí danh `t` (mart.ton_hien_tai), `dk_loc` cần bí danh `s`
    # (mart.san_pham_360), nên mọi nhánh dùng chúng phải có đủ hai bí danh đó.
    dk_kho = "AND t.warehouse_code = %s" if kho else ""
    p_kho = [kho] if kho else []
    dk_loc = "AND s.trang_thai = %s" if loc in TRANG_THAI_TON else ""
    p_loc = [loc] if loc in TRANG_THAI_TON else []

    # THỨ TỰ THAM SỐ = thứ tự VĂN BẢN các mảnh xuất hiện bên dưới: nhánh
    # 'can_han' (CAN_HAN_NGAY, kho, loc), rồi 'gia_tri_ton_chet' (kho, loc),
    # rồi 'kho' (loc). Hai CTE ở đầu KHÔNG mang tham số nào.
    #
    # HAI CTE `AS MATERIALIZED`, ghi TƯỜNG MINH. Câu này tham chiếu
    # mart.san_pham_360 **5 lần** và mart.ton_hien_tai **3 lần**, mà Postgres
    # KHÔNG gộp các truy vấn con trùng nhau: mỗi lần tham chiếu là một lần
    # ĐÁNH GIÁ LẠI cả view, và san_pham_360 kéo theo ty_suat_mat_hang,
    # toc_do_ban (2 lượt quét fact_sales_line) cùng CTE `sl` — khoảng 32 lượt
    # quét bảng bán hàng cho MỘT lần mở trang. Ngân sách "<= 2 truy vấn" đếm
    # SỐ LƯỢT HỎI, không đếm sức tính, nên nó không bắt được lớp lỗi này; trên
    # CSDL test vài chục dòng màn hình vẫn xanh.
    #
    # Vật hoá là rẻ ở đúng hình dạng dữ liệu này: san_pham_360 là 232 dòng,
    # ton_hien_tai là một ảnh chụp ~177 dòng (chặn trên bởi số mã × số kho).
    # Quét lại một bảng tạm bé năm lần rẻ hơn hẳn dựng lại nó năm lần.
    #
    # KHÔNG nhét `dk_kho` vào CTE `t`: nhánh 'kho' (giá trị theo kho) CỐ Ý
    # không lọc theo kho — nó là ô điều khiển của chính bộ lọc đó.
    #
    # Tên CTE giữ đúng bí danh cũ (`s`, `t`) để mọi mảnh vị từ dựng sẵn ở trên
    # chạy nguyên văn.
    tq = conn.execute(f"""
        WITH s AS MATERIALIZED (SELECT * FROM mart.san_pham_360),
             t AS MATERIALIZED (SELECT * FROM mart.ton_hien_tai)
        SELECT khoi, khoa, ten, so, so2, ngay FROM (
            SELECT 'o'::text AS khoi, 'het_hang'::text AS khoa, ''::text AS ten,
                   count(*)::numeric AS so, 0::numeric AS so2, NULL::date AS ngay
              FROM s WHERE trang_thai = 'het_hang'
            UNION ALL
            SELECT 'o', 'sap_thieu', '', count(*), 0, NULL
              FROM s WHERE trang_thai = 'sap_thieu'
            UNION ALL
            SELECT 'o', 'can_han', '', count(*), 0, NULL
              FROM t
              LEFT JOIN s ON s.product_code = t.product_code
             WHERE {VI_TU_CAN_HAN}
                   {dk_kho} {dk_loc}
            UNION ALL
            SELECT 'o', 'gia_tri_ton_chet', '', coalesce(sum(t.gia_tri), 0), 0, NULL
              FROM t
              JOIN s ON s.product_code = t.product_code
             WHERE s.trang_thai = 'ton_chet' {dk_kho} {dk_loc}
            UNION ALL
            SELECT 'kho', t.warehouse_code, t.ten_kho,
                   coalesce(sum(t.gia_tri), 0), count(*), NULL
              FROM t
              LEFT JOIN s ON s.product_code = t.product_code
             WHERE true {dk_loc}
             GROUP BY t.warehouse_code, t.ten_kho
            UNION ALL
            SELECT 'dsk', w.warehouse_code, w.warehouse_name, 0, 0, NULL
              FROM core.dim_warehouse w
            UNION ALL
            SELECT 'ngay', '', '', 0, 0, max(snapshot_date)
              FROM core.fact_inventory_daily
             WHERE snapshot_date <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date))
            UNION ALL
            SELECT 'ngay_dau', '', '', 0, 0, min(snapshot_date)
              FROM core.fact_inventory_daily
        ) u ORDER BY khoi, khoa
    """, [CAN_HAN_NGAY] + p_kho + p_loc + p_kho + p_loc + p_loc).fetchall()

    o_tong_quan = {r[1]: int(r[3]) for r in tq if r[0] == "o"}
    theo_kho = [{"ma": r[1], "ten": r[2], "gia_tri": int(r[3]),
                 "so_dong": int(r[4])} for r in tq if r[0] == "kho"]
    ds_kho = [(r[1], r[2]) for r in tq if r[0] == "dsk"]
    ngay_chup = next((r[5] for r in tq if r[0] == "ngay"), None)
    # Ảnh chụp tồn SỚM NHẤT trong kho — để màn nói "chưa có ảnh chụp tồn tại mốc
    # này, ảnh chụp sớm nhất là …" khi xem lùi về trước nó (040).
    ngay_chup_dau = next((r[5] for r in tq if r[0] == "ngay_dau"), None)

    # Lượt hỏi 2: bảng tồn + khối cận hạn + khối quá hạn, cả ba đều theo CẢ
    # HAI bộ lọc (chúng là khối nội dung, không điều khiển gì). Cùng một view,
    # cùng bộ cột — lại đúng ca UNION ALL không phải đệm NULL cho nhánh nào.
    #
    # BA nhánh chứ không hai: `han_con_lai < 0` là ĐÃ QUÁ HẠN, một việc khác
    # hẳn "sắp hết hạn" với hàng thực phẩm. Xem ghi chú ở CAN_HAN_NGAY.
    #
    # KHÔNG có LIMIT ở nhánh nào: một ảnh chụp 在庫一覧 là ~177 dòng và bị chặn
    # trên bởi (số mã × số kho) = 232 × 2. Đặt LIMIT ở đây là tạo ra đúng loại
    # mâu thuẫn mà ô tổng quan sinh ra để tránh — ô nói "12 lô cận hạn" còn
    # bảng ngay dưới nó chỉ liệt kê 10.
    #
    # LEFT JOIN san_pham_360: một mã có trong bản xuất tồn kho nhưng chưa có
    # trong 商品マスタ vẫn phải hiện ở bảng tồn. INNER JOIN làm nó biến mất khỏi
    # đúng màn hình lẽ ra phải phát hiện ra nó.
    #
    # Lại HAI CTE `AS MATERIALIZED` như lượt hỏi 1, và vì đúng lý do đó: ba
    # nhánh dưới đây tham chiếu mart.ton_hien_tai 3 lần và mart.san_pham_360 3
    # lần, tức 3 lần dựng lại mỗi view nếu để nguyên.
    rows = conn.execute(f"""
        WITH s AS MATERIALIZED (SELECT * FROM mart.san_pham_360),
             t AS MATERIALIZED (SELECT * FROM mart.ton_hien_tai)
        SELECT khoi, ma, ten, kho, ten_kho, so_luong, gia_tri, best_before,
               loai_han, han_con_lai, trang_thai, nhom, du_ban_ngay, toc_do
        FROM (
            (SELECT 'dong'::text AS khoi, t.product_code AS ma,
                    coalesce(s.ten_hang, t.product_code) AS ten,
                    t.warehouse_code AS kho, t.ten_kho, t.so_luong, t.gia_tri,
                    t.best_before, t.loai_han, t.han_con_lai, s.trang_thai,
                    s.nhom, s.du_ban_ngay, s.toc_do_ngay_theo_tuoi AS toc_do,
                    row_number() OVER (ORDER BY t.gia_tri DESC NULLS LAST) AS xep
               FROM t
               LEFT JOIN s ON s.product_code = t.product_code
              WHERE true {dk_kho} {dk_loc})
            UNION ALL
            (SELECT 'han', t.product_code,
                    coalesce(s.ten_hang, t.product_code),
                    t.warehouse_code, t.ten_kho, t.so_luong, t.gia_tri,
                    t.best_before, t.loai_han, t.han_con_lai, s.trang_thai,
                    s.nhom, s.du_ban_ngay, s.toc_do_ngay_theo_tuoi,
                    row_number() OVER (ORDER BY t.han_con_lai)
               FROM t
               LEFT JOIN s ON s.product_code = t.product_code
              WHERE {VI_TU_CAN_HAN}
                    {dk_kho} {dk_loc})
            UNION ALL
            (SELECT 'qua', t.product_code,
                    coalesce(s.ten_hang, t.product_code),
                    t.warehouse_code, t.ten_kho, t.so_luong, t.gia_tri,
                    t.best_before, t.loai_han, t.han_con_lai, s.trang_thai,
                    s.nhom, s.du_ban_ngay, s.toc_do_ngay_theo_tuoi,
                    row_number() OVER (ORDER BY t.han_con_lai)
               FROM t
               LEFT JOIN s ON s.product_code = t.product_code
              WHERE {VI_TU_QUA_HAN}
                    {dk_kho} {dk_loc})
        ) u ORDER BY khoi, xep
    """, p_kho + p_loc + [CAN_HAN_NGAY] + p_kho + p_loc
         + p_kho + p_loc).fetchall()

    def _dong(r):
        # `nhan_*`/`mau_*` là CHUỖI, không phải tuple — cùng hình dạng với
        # SanPham.nhan_trang_thai/.mau. Một cái tên trả hai kiểu khác nhau ở
        # hai màn là bắt template viết `d.nhan_trang_thai[0]` ở màn này và
        # `sp.nhan_trang_thai` ở màn kia, rồi một ngày viết nhầm chỗ.
        nhan_han, mau_han = LOAI_HAN.get(r[8], (r[8] or "—", "nhat"))
        nhan_tt, mau_tt = TRANG_THAI_TON.get(r[10], (r[10] or "—", "nhat"))
        return {"ma": r[1], "ten": r[2], "kho": r[3], "ten_kho": r[4],
                "so_luong": _so(r[5]), "gia_tri": int(r[6] or 0),
                "best_before": r[7], "loai_han": r[8],
                "nhan_han": nhan_han, "mau_han": mau_han,
                "han_con_lai": r[9], "trang_thai": r[10],
                "nhan_trang_thai": nhan_tt, "mau": mau_tt,
                # Ba cột của CẢ MÃ (mọi kho, san_pham_360) — giao diện React ghi
                # rõ "của cả mã": không có "đủ bán" riêng từng kho ở mart.
                "nhom": r[11], "du_ban_ngay": _so(r[12]), "toc_do": _so(r[13])}

    dong = [_dong(r) for r in rows if r[0] == "dong"]
    return Kho(ngay_chup=ngay_chup, o_tong_quan=o_tong_quan,
               dong=dong, gia_tri_ton=sum(d["gia_tri"] for d in dong),
               theo_kho=theo_kho,
               can_han=[_dong(r) for r in rows if r[0] == "han"],
               qua_han=[_dong(r) for r in rows if r[0] == "qua"],
               ds_kho=ds_kho, kho=kho, loc=loc, ngay_chup_dau=ngay_chup_dau)


def lo_can_han(conn, gioi_han: int = 5) -> tuple[list[dict], int]:
    """`gioi_han` lô cận hạn KHÔNG lọc theo kho/trạng thái + số lô ĐÃ quá hạn,
    ĐÚNG MỘT lượt hỏi trên `mart.ton_hien_tai` — KHÔNG đụng `mart.san_pham_360`.

    Vì sao có hàm riêng: dashboard `/` (kome.tong_quan.tong_quan()) trước đây
    gọi nguyên `kho_hang()` — HAI lượt hỏi, mỗi lượt vật hoá san_pham_360, VIEW
    NẶNG NHẤT của mart (kéo theo mart.ty_suat_mat_hang và hai lượt quét
    fact_sales_line, xem chú thích ở đầu kho_hang()) — chỉ để lấy 5 dòng cận
    hạn và một con số đếm. `lo_can_han()` chỉ cần TÊN HÀNG và HẠN SỬ DỤNG, cả
    hai đều có sẵn ở nguồn rẻ hơn nhiều: `mart.ton_hien_tai` + `core.dim_product`.

    TÊN HÀNG tái tạo ĐÚNG công thức của `san_pham_360.ten_hang`
    (`coalesce(nullif(product_name, ''), product_code)`, migration 023) bằng
    cách LEFT JOIN thẳng `core.dim_product` — không phải chép một biểu thức
    tương tự rồi hy vọng nó khớp. `san_pham_360` dựng TỪ `core.dim_product`
    (`FROM core.dim_product p`), nên với MỌI mã có trong `dim_product`, biểu
    thức ở đây cho ra đúng con số mà `kho_hang()::_dong` hiện
    (`coalesce(s.ten_hang, t.product_code)`). Ca hiếm mã tồn kho không có
    trong `dim_product` (dữ liệu bất thường) cũng khớp: `p` là NULL qua LEFT
    JOIN ở CẢ HAI nơi, `nullif(NULL, '')` vẫn NULL, `coalesce` rơi về
    `product_code` ở cả hai — cùng một kết quả, không phải trùng hợp.

    Thứ tự VÀ ngưỡng dùng chung `VI_TU_CAN_HAN`/`VI_TU_QUA_HAN` với
    `kho_hang()` — một hằng, không phải hai bản chép của cùng một ngưỡng 90
    ngày (xem chú thích ở CAN_HAN_NGAY).

    CTE `t` vào `AS MATERIALIZED`: câu này tham chiếu `mart.ton_hien_tai` HAI
    lần (khối 'han' và khối đếm 'qua'), đúng bất biến CTE-trùng của CLAUDE.md.
    """
    rows = conn.execute(f"""
        WITH t AS MATERIALIZED (SELECT * FROM mart.ton_hien_tai),
             han AS (
                 SELECT t.product_code AS ma,
                        coalesce(nullif(p.product_name, ''), t.product_code) AS ten,
                        t.warehouse_code AS kho, t.ten_kho, t.han_con_lai,
                        row_number() OVER (ORDER BY t.han_con_lai) AS xep
                   FROM t
                   LEFT JOIN core.dim_product p ON p.product_code = t.product_code
                  WHERE {VI_TU_CAN_HAN}
             ),
             qua AS (SELECT count(*) AS n FROM t WHERE {VI_TU_QUA_HAN})
        SELECT 'han'::text AS khoi, ma, ten, kho, ten_kho, han_con_lai, xep,
               NULL::bigint AS n
          FROM han WHERE xep <= %s
        UNION ALL
        SELECT 'qua', NULL, NULL, NULL, NULL, NULL, NULL, n FROM qua
    """, [CAN_HAN_NGAY, gioi_han]).fetchall()

    can_han = sorted(
        ({"ma": r[1], "ten": r[2], "kho": r[3], "ten_kho": r[4],
          "han_con_lai": r[5]} for r in rows if r[0] == "han"),
        key=lambda d: d["han_con_lai"])
    so_qua_han = next((int(r[7] or 0) for r in rows if r[0] == "qua"), 0)
    return can_han, so_qua_han


# ---- Giao diện React (giai đoạn 4) ------------------------------------------

def danh_muc(conn) -> dict:
    """TOÀN BỘ danh mục (232 mã) cho màn Sản phẩm React — ĐÚNG MỘT lượt hỏi.

    Vì sao cả danh mục chứ không phân trang như `danh_sach()`: 232 dòng là
    ~60 KB JSON, còn mỗi cú bấm lọc / sắp / tìm mà phải hỏi lại máy chủ thì
    mỗi lần mất một vòng `mart.san_pham_360` (view nặng nhất của mart). Đi qua
    ảnh chụp theo phiên bản NẠP (không đọc bảng `app` nào), nên sau lần đầu
    màn này là 1 lượt hỏi (phiên bản) — cùng nếp danh bạ khách (giai đoạn 2).

    Hai thứ `san_pham_360` KHÔNG có, cùng câu lệnh:
      * `dt_12t`/`lg_12t` — doanh thu / lãi gộp **12 tháng**, đúng cửa sổ của
        `mart.hang_doanh_thu` (`sales_date > hom_nay - 365`, mốc dữ liệu) —
        một định nghĩa "12 tháng" cho cả dự án. `san_pham_360.doanh_thu_thuan`
        là LUỸ KẾ, hai cột cùng tồn tại và trang ghi rõ cột nào là cột nào.
      * `thang` — 12 THÁNG LỊCH gần nhất (tới tháng mốc) cho đường xu hướng.
      * `nganh` — ngành hàng (`core.dim_product.food_category_name`).
    Cả hai đọc MỘT CTE trên `mart.dong_ban` (không đi qua
    `mart.san_pham_theo_thang`, thứ đọc lại `dong_ban` một lần nữa) — cùng lý lẽ
    bất biến CTE-trùng.
    """
    rows = conn.execute(f"""
        WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
        s AS MATERIALIZED (SELECT {_COT} FROM mart.san_pham_360),
        b AS MATERIALIZED (
            SELECT d.product_code, d.thang, d.sales_date, d.qty,
                   d.doanh_thu_thuan, d.gross_profit
              FROM mart.dong_ban d, m
             WHERE d.sales_date > least(m.hom_nay - 365,
                                        (date_trunc('month', m.hom_nay)
                                         - interval '11 months')::date - 1)
        ),
        d12 AS (
            SELECT b.product_code, sum(b.doanh_thu_thuan) AS dt, sum(b.gross_profit) AS lg
              FROM b, m WHERE b.sales_date > m.hom_nay - 365
             GROUP BY 1
        ),
        th AS (
            SELECT product_code,
                   json_agg(json_build_array(thang, dt, sl) ORDER BY thang) AS j
              FROM (SELECT b.product_code, b.thang, sum(b.doanh_thu_thuan) AS dt,
                           sum(b.qty) AS sl
                      FROM b, m
                     WHERE b.sales_date >= (date_trunc('month', m.hom_nay)
                                            - interval '11 months')::date
                     GROUP BY 1, 2) x
             GROUP BY product_code
        )
        SELECT s.*, d12.dt, d12.lg, th.j, p.food_category_name, m.hom_nay
          FROM s CROSS JOIN m
          LEFT JOIN d12 ON d12.product_code = s.product_code
          LEFT JOIN th ON th.product_code = s.product_code
          LEFT JOIN core.dim_product p ON p.product_code = s.product_code
         ORDER BY s.doanh_thu_thuan DESC NULLS LAST, s.product_code
    """).fetchall()
    hom_nay = rows[0][-1] if rows else None
    thang: list[str] = []
    if hom_nay:
        y, mo = hom_nay.year, hom_nay.month
        for k in range(11, -1, -1):
            yy, mm = divmod(mo - 1 - k, 12)
            thang.append(f"{y + yy:04d}-{mm + 1:02d}")
    ma = []
    for r in rows:
        sp = _sp(r[:15])
        chuoi = {t[0]: t for t in (r[17] or [])}
        ma.append({**sp.__dict__, "nhan_trang_thai": sp.nhan_trang_thai, "mau": sp.mau,
                   # NGÀNH hàng — cùng khái niệm "ngành" của /bao-cao. Rỗng -> ĐÚNG
                   # hằng NGANH_TRONG (bản chép bắt buộc ở tầng Python của biểu thức
                   # coalesce trong mart.ban_theo_nganh_thang — CLAUDE.md). `nhom`
                   # (kind_name) của san_pham_360 chỉ có 有形/無形, không lọc được.
                   "nganh": r[18] or NGANH_TRONG,
                   "dt_12t": int(r[15] or 0), "lg_12t": int(r[16] or 0),
                   # Tỷ số của các TỔNG (bất biến tỷ suất), NULL khi mẫu số 0 —
                   # cùng `nullif(sum(...), 0)` của mart.
                   "ts_12t": (float(r[16] or 0) / float(r[15])) if r[15] else None,
                   # Tháng không có dòng bán = 0 yên ĐÃ BIẾT (không có phiếu), cùng
                   # ngoại lệ tiền của `_sp`.
                   "thang_dt": [int(chuoi[t][1] or 0) if t in chuoi else 0 for t in thang],
                   "thang_sl": [_so(chuoi[t][2]) if t in chuoi else 0.0 for t in thang]})
    return {"hom_nay": hom_nay, "thang": thang, "ma": ma,
            "trang_thai": {k: list(v) for k, v in TRANG_THAI_TON.items()}}


def ban_theo_ngay(conn, ma: str, thang: str) -> dict:
    """Bán theo NGÀY của một mã trong `thang` ('YYYY-MM') và tháng liền trước
    (cột nhạt "cùng kỳ tháng trước" của gói thiết kế) — MỘT lượt hỏi trên
    `mart.dong_ban`. Ngày không có dòng bán không có dòng ở đây; giao diện vẽ ô
    trống cho ngày đó (không phải 0 bịa: "không có phiếu" CHÍNH LÀ 0 yên, nhưng
    ngày nghỉ thì giao diện tô khác — xem `la_ngay_kd`).

    `la_ngay_kd` đọc `mart.lich_kinh_doanh` — định nghĩa "ngày làm việc" DUY
    NHẤT của dự án (migration 031)."""
    y, m = int(thang[:4]), int(thang[5:7])
    dau = date(y, m, 1)
    truoc = date(y - 1, 12, 1) if m == 1 else date(y, m - 1, 1)
    sau = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    rows = conn.execute("""
        WITH n AS (
            SELECT l.ngay, l.la_ngay_kd FROM mart.lich_kinh_doanh l
             WHERE l.ngay >= %s AND l.ngay < %s
        ), b AS (
            SELECT sales_date, sum(qty) AS sl, sum(doanh_thu_thuan) AS dt,
                   sum(gross_profit) AS lg, count(DISTINCT customer_code) AS kh
              FROM mart.dong_ban
             WHERE product_code = %s AND sales_date >= %s AND sales_date < %s
             GROUP BY 1
        )
        SELECT n.ngay, n.la_ngay_kd, b.sl, b.dt, b.lg, b.kh,
               (SELECT hom_nay FROM mart.moc_thoi_gian)
          FROM n LEFT JOIN b ON b.sales_date = n.ngay
         ORDER BY n.ngay
    """, (truoc, sau, ma, truoc, sau)).fetchall()
    hom_nay = rows[0][6] if rows else None

    def _ngay(r):
        return {"ngay": r[0], "la_ngay_kd": bool(r[1]), "so_luong": _so(r[2]) or 0.0,
                "doanh_thu": int(r[3] or 0), "lai_gop": int(r[4] or 0), "so_khach": int(r[5] or 0)}
    return {"thang": thang, "hom_nay": hom_nay,
            "nay": [_ngay(r) for r in rows if r[0] >= dau],
            "truoc": [_ngay(r) for r in rows if r[0] < dau]}
