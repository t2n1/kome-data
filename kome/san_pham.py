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
from dataclasses import dataclass, field, replace
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
    # 050: mã ※終売※ (ngừng kinh doanh). Mã ※終売※ đã hết tồn không bao giờ tới
    # đây (mart.san_pham_360 lọc bỏ), nên True = "còn tồn, bán nốt".
    ngung_ban: bool = False

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
    # Theo LÔ (042): lô dự kiến còn hàng lúc hết hạn, và mã sắp phải chuyển lô
    # chờ lên lô đang xuất. `kho_dang_xuat` = mart.kho_dang_xuat() — giao diện
    # đọc nó để gọi tên lô, không tự viết cứng mã kho.
    khong_kip: list[dict] = field(default_factory=list)
    chuyen_lo: list[dict] = field(default_factory=list)
    kho_dang_xuat: str = ""


# Bộ cột CHUNG của mọi nhánh lượt hỏi 2 của kho_hang() (UNION ALL đòi cùng cột):
# `_COT_LO` trong nhánh (bí danh t = mart.ton_theo_lo, s = mart.san_pham_360,
# p = mart.dim_product), `_COT_LO_NGOAI` ở lớp ngoài — cùng thứ tự với `_dong`.
_COT_LO = """t.product_code AS ma, coalesce(s.ten_hang, t.product_code) AS ten,
             t.warehouse_code AS kho, t.ten_kho, t.so_luong, t.gia_tri,
             t.best_before, t.loai_han, t.han_con_lai, s.trang_thai, s.nhom,
             s.du_ban_ngay, s.toc_do_ngay_theo_tuoi AS toc_do,
             mart.ten_nganh(p.food_category_name) AS nganh,
             t.vai_tro_lo, t.bat_dau_ban_sau, t.ban_het_sau, t.khong_kip_ban,
             t.sl_khong_kip, t.gia_tri_khong_kip, t.lo_xuat_du_ban, t.ton_lo_cho,
             t.sap_chuyen_lo"""
_COT_LO_NGOAI = """ma, ten, kho, ten_kho, so_luong, gia_tri, best_before, loai_han,
             han_con_lai, trang_thai, nhom, du_ban_ngay, toc_do, nganh,
             vai_tro_lo, bat_dau_ban_sau, ban_het_sau, khong_kip_ban,
             sl_khong_kip, gia_tri_khong_kip, lo_xuat_du_ban, ton_lo_cho,
             sap_chuyen_lo"""
_TU_LO = """FROM t
               LEFT JOIN s ON s.product_code = t.product_code
               LEFT JOIN mart.dim_product p ON p.product_code = t.product_code"""


_COT = """product_code, ten_hang, nhom, doanh_thu_thuan, lai_gop, ty_suat,
          so_luong_ban, ton, toc_do_ngay, toc_do_ngay_theo_tuoi, du_ban_ngay,
          trang_thai, so_khach, lan_dau, lan_cuoi, ngung_ban"""


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
        lan_dau=r[13], lan_cuoi=r[14], ngung_ban=bool(r[15]))


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


def la_ma_ngung_ban_an(conn, ma: str) -> bool:
    """Mã ※終売※ đã hết tồn tính đến mốc (050, `mart.ma_ngung_ban_an`) — để màn nói
    "đã ngừng kinh doanh" thay vì "không có mã này". Chỉ chạy khi `ho_so` trả None,
    nên không tính vào trần 5 lượt hỏi của hồ sơ."""
    return conn.execute("SELECT EXISTS (SELECT 1 FROM mart.ma_ngung_ban_an WHERE product_code = %s)",
                        (ma,)).fetchone()[0]


def kho_hang(conn, kho: str = "", loc: str = "") -> Kho:
    """Màn Kho hàng = `kho_hang_tho` (SQL, KHÔNG lọc) rồi `loc_kho` (Python).

    Từ 2026-10-15 hai bộ lọc không còn ở SQL: đo thật trên Vercel mỗi tổ hợp
    (kho, trạng thái) là một ảnh chụp riêng tính lại từ đầu (~5–6,5 s, dựng
    `mart.san_pham_360` hai lần), nên mỗi cú bấm chip là một lần chờ. Nay API
    giữ MỘT ảnh chụp không lọc (thứ `anh_chup.lam_nong` tính sẵn sau mỗi lần
    nạp) và lọc trên nó — cùng nếp danh bạ khách (`KH._khop`)."""
    return replace(tho := kho_hang_tho(conn), **loc_kho(vars(tho), kho, loc))


def loc_kho(k, kho: str = "", loc: str = "") -> dict:
    """Áp hai bộ lọc lên dữ liệu KHÔNG lọc của `kho_hang_tho` (dataclass `Kho`
    qua `vars()` hoặc chính dict JSON của nó trong ảnh chụp) — trả các trường
    đổi theo bộ lọc. 0 lượt hỏi. MỘT chỗ viết luật "khối nào theo bộ lọc nào"
    (xem docstring `kho_hang_tho`):

      * bảng tồn, cận hạn, quá hạn, không kịp bán, ô "lô cận hạn", ô "giá trị
        tồn chết", ô "giá trị tồn": theo CẢ HAI;
      * "giá trị theo kho": chỉ theo trạng thái; "sắp chuyển lô": chỉ theo
        trạng thái (thuộc tính của MÃ, không của lô);
      * hai ô hết hàng / sắp thiếu: không theo bộ lọc nào.

    Lọc một danh sách đã xếp giữ nguyên thứ tự, nên mỗi khối ra đúng thứ tự mà
    `row_number()` của SQL cũ cho ra trên tập đã lọc."""
    hl = loc if loc in TRANG_THAI_TON else ""

    def theo_loc(d):
        return not hl or d["trang_thai"] == hl

    def ca_hai(d):
        return theo_loc(d) and (not kho or d["kho"] == kho)

    dong = [d for d in k["dong"] if ca_hai(d)]
    can_han = [d for d in k["can_han"] if ca_hai(d)]
    theo_kho: dict[tuple[str, str], dict] = {}
    for d in k["dong"]:
        if theo_loc(d):
            w = theo_kho.setdefault((d["kho"], d["ten_kho"]),
                                    {"ma": d["kho"], "ten": d["ten_kho"], "gia_tri": 0, "so_dong": 0})
            w["gia_tri"] += d["gia_tri"]
            w["so_dong"] += 1
    return {
        "o_tong_quan": {**k["o_tong_quan"], "can_han": len(can_han),
                        "gia_tri_ton_chet": sum(d["gia_tri"] for d in dong if d["trang_thai"] == "ton_chet")},
        "dong": dong, "gia_tri_ton": sum(d["gia_tri"] for d in dong),
        "theo_kho": [theo_kho[x] for x in sorted(theo_kho)],
        "can_han": can_han,
        "qua_han": [d for d in k["qua_han"] if ca_hai(d)],
        "khong_kip": [d for d in k["khong_kip"] if ca_hai(d)],
        "chuyen_lo": [d for d in k["chuyen_lo"] if theo_loc(d)],
        "kho": kho, "loc": loc,
    }


def kho_hang_tho(conn) -> Kho:
    """Màn Kho hàng KHÔNG lọc: bốn ô tổng quan, tồn hiện tại, cận hạn, giá trị
    theo kho. Hai bộ lọc áp sau, ở `loc_kho`.

    ĐÚNG HAI lượt hỏi (đặc tả 4b §5.5), có test canh. Chỉ lượt 2 dựng
    `mart.san_pham_360` (trước 2026-10-15 cả hai lượt — 2 × ~2,5 s trên CSDL thật).

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
    được — đúng câu hỏi của người vừa lọc theo kho. Không lọc nó theo kho thì một
    con số YÊN của mọi kho đứng ngay trên một bảng chỉ còn một kho, và công ty
    có 2 kho nên sai số gần 2× — trên đúng con số dùng để quyết định xả hàng.
    """
    # Lượt hỏi 1: danh sách kho + ngày chụp + lô đang xuất — KHÔNG đụng
    # mart.san_pham_360 (bốn ô số và "giá trị theo kho" nay cộng từ các dòng
    # của lượt 2, ở `loc_kho` / ngay dưới). ORDER BY ở LỚP NGOÀI.
    #
    # Danh sách kho đọc từ core.dim_warehouse chứ không từ chính các dòng tồn:
    # một kho tạm thời trống vẫn phải có trong ô lọc, và tên kho là tên nghiệp
    # vụ của OBC (`1002 新・賞味期限用`) — không viết cứng tên nào.
    tq = conn.execute("""
        SELECT khoi, khoa, ten, ngay FROM (
            SELECT 'dsk'::text AS khoi, w.warehouse_code AS khoa, w.warehouse_name AS ten,
                   NULL::date AS ngay
              FROM core.dim_warehouse w
            UNION ALL
            SELECT 'ngay', '', '', max(snapshot_date)
              FROM core.fact_inventory_daily
             WHERE snapshot_date <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date))
            UNION ALL
            SELECT 'ngay_dau', '', '', min(snapshot_date)
              FROM core.fact_inventory_daily
            UNION ALL
            SELECT 'kdx', mart.kho_dang_xuat(), '', NULL
        ) u ORDER BY khoi, khoa
    """).fetchall()

    ds_kho = [(r[1], r[2]) for r in tq if r[0] == "dsk"]
    ngay_chup = next((r[3] for r in tq if r[0] == "ngay"), None)
    # Ảnh chụp tồn SỚM NHẤT trong kho — để màn nói "chưa có ảnh chụp tồn tại mốc
    # này, ảnh chụp sớm nhất là …" khi xem lùi về trước nó (040).
    ngay_chup_dau = next((r[3] for r in tq if r[0] == "ngay_dau"), None)
    kho_dang_xuat = next((r[1] for r in tq if r[0] == "kdx"), "")

    # Lượt hỏi 2: bảng tồn + khối cận hạn + quá hạn + không kịp bán + sắp
    # chuyển lô, KHÔNG lọc (bộ lọc ở `loc_kho`). Cùng một view, cùng bộ cột —
    # lại đúng ca UNION ALL không phải đệm NULL cho nhánh nào.
    #
    # BA nhánh chứ không hai: `han_con_lai < 0` là ĐÃ QUÁ HẠN, một việc khác
    # hẳn "sắp hết hạn" với hàng thực phẩm. Xem ghi chú ở CAN_HAN_NGAY.
    #
    # KHÔNG có LIMIT ở nhánh nào: một ảnh chụp 在庫一覧 là ~177 dòng và bị chặn
    # trên bởi (số mã × số kho) = 232 × 2. Đặt LIMIT ở đây là tạo ra đúng loại
    # mâu thuẫn mà ô tổng quan sinh ra để tránh — ô nói "12 lô cận hạn" còn
    # bảng ngay dưới nó chỉ liệt kê 10.
    #
    # LEFT JOIN san_pham_360 (và mart.dim_product để lấy ngành): một mã có trong bản xuất tồn kho nhưng chưa có
    # trong 商品マスタ vẫn phải hiện ở bảng tồn. INNER JOIN làm nó biến mất khỏi
    # đúng màn hình lẽ ra phải phát hiện ra nó.
    #
    # HAI CTE `AS MATERIALIZED`, ghi TƯỜNG MINH: năm nhánh dưới đây tham chiếu
    # mart.ton_theo_lo và mart.san_pham_360 năm lần, mà Postgres KHÔNG gộp các
    # truy vấn con trùng nhau — mỗi lần tham chiếu là một lần ĐÁNH GIÁ LẠI cả
    # view (san_pham_360 ~2,5 s trên CSDL thật, kéo theo ty_suat_mat_hang,
    # toc_do_ban và CTE `sl`). Ngân sách "<= 2 truy vấn" đếm SỐ LƯỢT HỎI, không
    # đếm sức tính, nên nó không bắt được lớp lỗi này.
    #
    # Từ 042, CTE `t` của lượt này là mart.ton_theo_lo (= ton_hien_tai + các cột
    # theo LÔ): hai "kho" của OBC là lô đang xuất / lô chờ của cùng một kho vật
    # lý (CLAUDE.md bẫy #6). Thêm hai nhánh — 'kkb' (không kịp bán trước hạn) và
    # 'chuyen' (sắp chuyển lô) — vẫn trong CÙNG lượt hỏi, cùng bộ cột `_COT_LO`.
    # 'chuyen' là thuộc tính của MÃ nên KHÔNG theo bộ lọc kho (lọc kho 1002 thì
    # dòng lô đang xuất bị lọc mất, mà chính nó mang cờ); vẫn theo trạng thái
    # (`loc_kho`).
    rows = conn.execute(f"""
        WITH s AS MATERIALIZED (SELECT * FROM mart.san_pham_360),
             t AS MATERIALIZED (SELECT * FROM mart.ton_theo_lo)
        SELECT khoi, {_COT_LO_NGOAI}
        FROM (
            (SELECT 'dong'::text AS khoi, {_COT_LO},
                    row_number() OVER (ORDER BY t.gia_tri DESC NULLS LAST, t.product_code,
                                             t.warehouse_code, t.best_before) AS xep
               {_TU_LO}
)
            UNION ALL
            (SELECT 'han', {_COT_LO}, row_number() OVER (ORDER BY t.han_con_lai)
               {_TU_LO}
              WHERE {VI_TU_CAN_HAN})
            UNION ALL
            (SELECT 'qua', {_COT_LO}, row_number() OVER (ORDER BY t.han_con_lai)
               {_TU_LO}
              WHERE {VI_TU_QUA_HAN})
            UNION ALL
            (SELECT 'kkb', {_COT_LO},
                    row_number() OVER (ORDER BY t.gia_tri_khong_kip DESC, t.han_con_lai)
               {_TU_LO}
              WHERE t.khong_kip_ban)
            UNION ALL
            (SELECT 'chuyen', {_COT_LO},
                    row_number() OVER (ORDER BY t.lo_xuat_du_ban NULLS FIRST, t.product_code)
               {_TU_LO}
              WHERE t.sap_chuyen_lo)
            UNION ALL
            -- Hai ô hết hàng / sắp thiếu: MÃ của san_pham_360 ở trạng thái đó — đếm từ `s`, KHÔNG
            -- từ các dòng tồn: từ 073 mã hết hàng là mã VẮNG ở ảnh chụp mới nhất, nên nó không có
            -- dòng tồn nào. Chỉ `ma` + `trang_thai` có nghĩa, các cột khác NULL.
            (SELECT 'tt', s.product_code, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                    s.trang_thai, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0
               FROM s WHERE s.trang_thai IN ('het_hang', 'sap_thieu'))
        ) u ORDER BY khoi, xep
    """, [CAN_HAN_NGAY]).fetchall()

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
                "nhom": r[11], "du_ban_ngay": _so(r[12]), "toc_do": _so(r[13]),
                # Ngành hàng = 食品分類名 của 商品データ (mart.dim_product), qua
                # ĐÚNG hàm mart.ten_nganh — cùng nhãn "(chưa phân loại)" với Báo
                # cáo / Sản phẩm. KHÔNG đọc 食品分類 của chính file 在庫一覧 (từ
                # 2026-09-24 bản xuất có kèm hai cột đó): một khái niệm một
                # nguồn — mã chưa phân loại thì sửa ở 商品データ trong OBC.
                "nganh": r[14],
                # Theo LÔ (042, mart.ton_theo_lo). `vai_tro_lo`: 'dang_xuat' | 'cho'.
                "vai_tro_lo": r[15], "bat_dau_ban_sau": _so(r[16]),
                "ban_het_sau": _so(r[17]), "khong_kip_ban": r[18],
                "sl_khong_kip": _so(r[19]),
                "gia_tri_khong_kip": None if r[20] is None else int(r[20]),
                "lo_xuat_du_ban": _so(r[21]), "ton_lo_cho": _so(r[22]),
                "sap_chuyen_lo": bool(r[23])}

    dong = [_dong(r) for r in rows if r[0] == "dong"]
    # Hai ô hết hàng / sắp thiếu = số MÃ của san_pham_360 ở trạng thái đó (nhánh 'tt'). Có test canh
    # (`tests/test_san_pham.py::test_o_het_hang_sap_thieu_BANG_dem_tren_san_pham_360`).
    o_tong_quan = {tt: sum(1 for r in rows if r[0] == "tt" and r[10] == tt)
                   for tt in ("het_hang", "sap_thieu")}
    k = Kho(ngay_chup=ngay_chup, o_tong_quan=o_tong_quan, dong=dong, theo_kho=[],
            can_han=[_dong(r) for r in rows if r[0] == "han"],
            qua_han=[_dong(r) for r in rows if r[0] == "qua"],
            khong_kip=[_dong(r) for r in rows if r[0] == "kkb"],
            chuyen_lo=[_dong(r) for r in rows if r[0] == "chuyen"],
            kho_dang_xuat=kho_dang_xuat,
            ds_kho=ds_kho, kho="", loc="", ngay_chup_dau=ngay_chup_dau)
    # Ô số / tổng / "giá trị theo kho" của trạng thái KHÔNG lọc đi qua CÙNG hàm
    # với trạng thái có lọc — một chỗ cộng, không hai.
    return replace(k, **loc_kho(vars(k)))


def lo_can_han(conn, gioi_han: int = 5) -> tuple[list[dict], int]:
    """`gioi_han` lô cận hạn KHÔNG lọc theo kho/trạng thái + số lô ĐÃ quá hạn,
    ĐÚNG MỘT lượt hỏi trên `mart.ton_hien_tai` — KHÔNG đụng `mart.san_pham_360`.

    Vì sao có hàm riêng: dashboard `/` (kome.tong_quan.tong_quan()) trước đây
    gọi nguyên `kho_hang()` — HAI lượt hỏi, mỗi lượt vật hoá san_pham_360, VIEW
    NẶNG NHẤT của mart (kéo theo mart.ty_suat_mat_hang và hai lượt quét
    fact_sales_line, xem chú thích ở đầu kho_hang()) — chỉ để lấy 5 dòng cận
    hạn và một con số đếm. `lo_can_han()` chỉ cần TÊN HÀNG và HẠN SỬ DỤNG, cả
    hai đều có sẵn ở nguồn rẻ hơn nhiều: `mart.ton_hien_tai` + `mart.dim_product`.

    TÊN HÀNG tái tạo ĐÚNG công thức của `san_pham_360.ten_hang`
    (`coalesce(nullif(product_name, ''), product_code)`, migration 023) bằng
    cách LEFT JOIN thẳng `mart.dim_product` — không phải chép một biểu thức
    tương tự rồi hy vọng nó khớp. `san_pham_360` dựng TỪ `mart.dim_product`
    (`FROM mart.dim_product p`), nên với MỌI mã có trong `dim_product`, biểu
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
                   LEFT JOIN mart.dim_product p ON p.product_code = t.product_code
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
        `mart.doanh_thu_12t` (`sales_date > hom_nay - 365`, mốc dữ liệu) —
        một định nghĩa "12 tháng" cho cả dự án. `san_pham_360.doanh_thu_thuan`
        là LUỸ KẾ, hai cột cùng tồn tại và trang ghi rõ cột nào là cột nào.
      * `thang` — 12 THÁNG LỊCH gần nhất (tới tháng mốc) cho đường xu hướng.
      * `nganh` — ngành hàng (`mart.dim_product.food_category_name`).
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
          LEFT JOIN mart.dim_product p ON p.product_code = s.product_code
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
        sp = _sp(r[:16])
        chuoi = {t[0]: t for t in (r[18] or [])}
        ma.append({**sp.__dict__, "nhan_trang_thai": sp.nhan_trang_thai, "mau": sp.mau,
                   # NGÀNH hàng — cùng khái niệm "ngành" của /bao-cao. Rỗng -> ĐÚNG
                   # hằng NGANH_TRONG (bản chép bắt buộc ở tầng Python của biểu thức
                   # coalesce trong mart.ban_theo_nganh_thang — CLAUDE.md). `nhom`
                   # (kind_name) của san_pham_360 chỉ có 有形/無形, không lọc được.
                   "nganh": r[19] or NGANH_TRONG,
                   "dt_12t": int(r[16] or 0), "lg_12t": int(r[17] or 0),
                   # Tỷ số của các TỔNG (bất biến tỷ suất), NULL khi mẫu số 0 —
                   # cùng `nullif(sum(...), 0)` của mart.
                   "ts_12t": (float(r[17] or 0) / float(r[16])) if r[16] else None,
                   # Tháng không có dòng bán = 0 yên ĐÃ BIẾT (không có phiếu), cùng
                   # ngoại lệ tiền của `_sp`.
                   "thang_dt": [int(chuoi[t][1] or 0) if t in chuoi else 0 for t in thang],
                   "thang_sl": [_so(chuoi[t][2]) if t in chuoi else 0.0 for t in thang]})
    return {"hom_nay": hom_nay, "thang": thang, "ma": ma,
            "trang_thai": {k: list(v) for k, v in TRANG_THAI_TON.items()}}


def ban_theo_ngay(conn, ma: str, thang: str, lech: int | None = 1) -> dict:
    """Bán theo NGÀY của một mã trong `thang` ('YYYY-MM') và tháng liền trước
    (cột nhạt "cùng kỳ tháng trước" của gói thiết kế) — MỘT lượt hỏi trên
    `mart.dong_ban`. Ngày không có dòng bán không có dòng ở đây; giao diện vẽ ô
    trống cho ngày đó (không phải 0 bịa: "không có phiếu" CHÍNH LÀ 0 yên, nhưng
    ngày nghỉ thì giao diện tô khác — xem `la_ngay_kd`).

    `la_ngay_kd` đọc `mart.lich_kinh_doanh` — định nghĩa "ngày làm việc" DUY
    NHẤT của dự án (migration 031).

    `lech` (đặc tả 2026-09-28): tháng so = lùi `lech` tháng — `so_sanh[0].lech_thang`
    của khoảng xem (1 = tháng trước như cũ, 12 = cùng tháng năm trước). None = kỳ so
    không lệch tròn tháng: không có tháng so (`truoc` rỗng)."""
    y, m = int(thang[:4]), int(thang[5:7])
    dau = date(y, m, 1)
    t = y * 12 + m - 1 - (lech or 0)
    truoc = date(t // 12, t % 12 + 1, 1)
    # Tháng so liền ngay trước tháng xem thì một dải liền; lùi xa hơn thì chỉ cần
    # hai tháng rời — bỏ các tháng giữa bằng vị từ trên `n` / `b`.
    cuoi_truoc = date(truoc.year + (truoc.month == 12), truoc.month % 12 + 1, 1)
    sau = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    rows = conn.execute("""
        WITH n AS (
            SELECT l.ngay, l.la_ngay_kd FROM mart.lich_kinh_doanh l
             WHERE (l.ngay >= %(dau)s AND l.ngay < %(sau)s)
                OR (%(co)s AND l.ngay >= %(truoc)s AND l.ngay < %(cuoi_truoc)s)
        ), b AS (
            SELECT sales_date, sum(qty) AS sl, sum(doanh_thu_thuan) AS dt,
                   sum(gross_profit) AS lg, count(DISTINCT customer_code) AS kh
              FROM mart.dong_ban
             WHERE product_code = %(ma)s
               AND ((sales_date >= %(dau)s AND sales_date < %(sau)s)
                    OR (%(co)s AND sales_date >= %(truoc)s AND sales_date < %(cuoi_truoc)s))
             GROUP BY 1
        )
        SELECT n.ngay, n.la_ngay_kd, b.sl, b.dt, b.lg, b.kh,
               (SELECT hom_nay FROM mart.moc_thoi_gian)
          FROM n LEFT JOIN b ON b.sales_date = n.ngay
         ORDER BY n.ngay
    """, {"dau": dau, "sau": sau, "truoc": truoc, "cuoi_truoc": cuoi_truoc, "ma": ma,
          "co": lech is not None}).fetchall()
    hom_nay = rows[0][6] if rows else None

    def _ngay(r):
        return {"ngay": r[0], "la_ngay_kd": bool(r[1]), "so_luong": _so(r[2]) or 0.0,
                "doanh_thu": int(r[3] or 0), "lai_gop": int(r[4] or 0), "so_khach": int(r[5] or 0)}
    return {"thang": thang, "hom_nay": hom_nay, "lech": lech,
            "thang_so": f"{truoc:%Y-%m}" if lech is not None else None,
            "nay": [_ngay(r) for r in rows if r[0] >= dau],
            "truoc": [_ngay(r) for r in rows if r[0] < dau]}
