"""Bảng phủ dữ liệu: tháng nào / kỳ nào đang thiếu dữ liệu, theo từng loại file.

MỘT nơi duy nhất tính bảng này. Trang web `/phu-du-lieu` và lệnh terminal
`scripts/bang_phu_du_lieu.py` đều gọi hàm ở đây. Chép đôi logic là mời gọi
đúng loại lỗi mà hệ thống này sinh ra để chặn: sửa cách tính ở một chỗ, rồi
màn hình và terminal nói hai con số khác nhau, và không ai biết bên nào đúng.

Đọc thẳng từ kho dữ liệu chứ không đếm tên file — file xuất theo quý chứa 3
tháng, nên đếm file không cho biết tháng nào thiếu.

Kỳ kế toán lấy từ `core.dim_date` (`company_fy`, `company_fy_label`,
`company_fy_month`, `is_fy_end_month` — xem `db/migrations/012_*.sql`).
KHÔNG tính lại bằng Python: kỳ của công ty là 1/8 → 31/7, KHÔNG phải năm tài
chính Nhật chuẩn (1/4 → 31/3), và một công thức chép tay ở đây sẽ âm thầm
lệch với CSDL vào đúng lúc không ai để ý.

LƯU Ý QUAN TRỌNG về trạng thái `KHONG` ("không có dữ liệu"): nó KHÔNG phân
biệt được hai trường hợp —
  (a) chưa bao giờ xuất file cho tháng đó, và
  (b) đã xuất nhưng file bị cổng kiểm tra chặn (bản xuất thiếu, sai mẫu…).
Lý do: cổng kiểm tra chặn TRƯỚC khi ghi nhật ký nạp, nên kho không hề biết
file đó từng tồn tại. Muốn biết chắc thì đối chiếu với thư mục xuất của OBC.
"""
from dataclasses import dataclass
from datetime import date
import re

# --- trạng thái một ô ---------------------------------------------------
CO = "co"        # có dữ liệu trong kho
KHONG = "khong"  # không có dữ liệu (xem lưu ý ở đầu file)
NGOAI = "ngoai"  # ngoài phạm vi dữ liệu — công ty không còn lưu
NGHI = "nghi"    # ngày nghỉ cuối tuần — CHỈ bảng theo ngày

KY_HIEU = {CO: "●", KHONG: "·", NGOAI: "—", NGHI: " "}
MO_TA_TRANG_THAI = {
    CO: "có dữ liệu trong kho",
    KHONG: "KHÔNG có dữ liệu — hoặc chưa xuất, hoặc đã bị cổng kiểm tra chặn",
    NGOAI: "ngoài phạm vi dữ liệu — công ty không còn lưu, đừng đi tìm",
    NGHI: "ngày nghỉ cuối tuần — không ai xuất file, không phải thiếu",
}

# Ràng buộc VĨNH VIỄN (đặc tả §2.2.1): dữ liệu bán hàng bắt đầu 2025-03-03,
# trước mốc đó KHÔNG TỒN TẠI — công ty không còn lưu. Đây không phải thiếu
# tạm. Tháng trước mốc này phải hiện là "ngoài phạm vi", KHÔNG được hiện như
# thiếu dữ liệu: hai thứ đó đòi hai hành động hoàn toàn khác nhau.
DAU_DU_LIEU = date(2025, 3, 3)

# Bảng bắt đầu từ đầu kỳ 2025 (1/8/2024) để thấy được phần đầu kỳ trống rỗng.
DAU_BANG = date(2024, 8, 1)


@dataclass(frozen=True)
class CotLoaiFile:
    """Một cột của bảng = một loại file OBC."""
    nhan: str        # nhãn ngắn chữ Latin (terminal: ký tự tiếng Nhật rộng gấp đôi)
    khoa: str        # spec_name trong config/files.yml
    ten_obc: str     # tên gốc tiếng Nhật
    mo_ta: str       # giải thích tiếng Việt

    @property
    def chu_giai(self) -> str:
        return f"{self.ten_obc} — {self.mo_ta}"


@dataclass(frozen=True)
class LoaiChuaCo:
    """Loại dữ liệu OBC có tồn tại nhưng CHƯA có bộ nạp — không lên bảng."""
    ten_obc: str
    mo_ta: str
    ghi_chu: str


COT = [
    CotLoaiFile("Ban", "ban", "売上伝票データ", "bán hàng"),
    CotLoaiFile("Ton", "ton", "在庫一覧", "tồn kho, ô hiện SỐ NGÀY có ảnh chụp"),
    CotLoaiFile("Khach", "tokuisaki", "得意先全情報", "khách hàng"),
    CotLoaiFile("SP", "shohin", "商品データ", "sản phẩm"),
    CotLoaiFile("NCC", "shiiresaki", "仕入先", "nhà cung cấp"),
    CotLoaiFile("Giao", "chokusousaki", "直送先", "điểm giao thẳng"),
    CotLoaiFile("Gia", "tanka", "取引単価データ", "bảng giá"),
]

THIEU_BO_NAP = [
    LoaiChuaCo("入金伝票データ", "phiếu thu", "1 quý (2026-05→07), chưa có bộ nạp"),
    LoaiChuaCo("得意先元帳", "sổ cái khách", "1 quý, chưa có bộ nạp"),
    LoaiChuaCo("請求先元帳", "sổ cái bên trả", "1 quý, chưa có bộ nạp"),
    LoaiChuaCo("他勘定振替明細", "xuất khác / hàng hỏng", "1 quý, chưa có bộ nạp"),
    LoaiChuaCo("仕入データ", "MUA HÀNG", "KHÔNG CÓ — lỗ hổng lớn nhất"),
    LoaiChuaCo("受注データ", "đơn đặt", "KHÔNG CÓ"),
]

# Hai loại này có bảng fact riêng nên đếm theo NGÀY nghiệp vụ trong kho, không
# theo tên file đã nạp.
_CO_BANG_FACT = {"ban", "ton"}

# Bảng THEO NGÀY chỉ có 3 nguồn của nhịp 13:30 (CLAUDE.md, "Quy trình hằng
# ngày") — cùng bộ với ô cảnh báo ở `kome/tuoi_du_lieu.py`. 4 loại master còn
# lại (商品データ, 仕入先, 直送先, 取引単価データ) xuất vài lần mỗi năm; chiếu
# xuống từng ngày thì 99% số ô sẽ đỏ dù không ai làm sai, và một cột đỏ gần
# như thường trực dạy người đọc bỏ qua cả cột. Chúng ở lại bảng THÁNG.
KHOA_NGAY = ("ban", "ton", "tokuisaki")
COT_NGAY = [c for c in COT if c.khoa in KHOA_NGAY]

# Số ngày mặc định của bảng theo ngày. Đủ để thấy nhịp hằng ngày và bắt ngày
# quên nạp; nhìn xa hơn thì đã có bảng tháng ngay bên dưới.
SO_NGAY_MAC_DINH = 90


@dataclass(frozen=True)
class O:
    """Một ô của bảng: một tháng × một loại file."""
    cot: CotLoaiFile
    trang_thai: str
    so_ngay: int | None = None   # chỉ cột tồn kho: số ngày có ảnh chụp

    @property
    def ky_hieu(self) -> str:
        if self.so_ngay is not None:
            return str(self.so_ngay)
        return KY_HIEU[self.trang_thai]

    @property
    def mo_ta(self) -> str:
        if self.so_ngay is not None:
            return f"{self.so_ngay} ngày có ảnh chụp tồn kho trong tháng"
        return MO_TA_TRANG_THAI[self.trang_thai]


@dataclass(frozen=True)
class Thang:
    thang: str                  # 'YYYY-MM'
    company_fy: int             # năm KẾT THÚC kỳ (từ core.dim_date)
    company_fy_month: int       # tháng thứ mấy trong kỳ: 8月=1 … 7月=12
    la_thang_chot_ky: bool      # core.dim_date.is_fy_end_month (tháng 7)
    ngoai_pham_vi: bool         # trọn tháng nằm trước DAU_DU_LIEU
    o: list[O]


@dataclass(frozen=True)
class Ky:
    """Một kỳ kế toán công ty: 1/8 → 31/7 năm sau."""
    company_fy: int
    nhan: str                   # core.dim_date.company_fy_label, vd 'Kỳ 2026-07'
    dau: date
    cuoi: date
    thang: list[Thang]
    doanh_thu_thuan: int        # sum(amount - tax_amount)
    lai_gop: int                # sum(gross_profit)

    @property
    def ty_suat(self) -> float | None:
        """Tỷ suất lãi gộp. None khi chưa có doanh thu — KHÔNG trả 0:
        0% và "chưa có số" là hai chuyện khác nhau."""
        if not self.doanh_thu_thuan:
            return None
        return self.lai_gop / self.doanh_thu_thuan

    @property
    def du_12_thang(self) -> bool:
        return sum(1 for t in self.thang if not t.ngoai_pham_vi) == 12


@dataclass(frozen=True)
class BangPhu:
    database: str               # CHỈ dùng cho terminal, KHÔNG in ra HTML
    cot: list[CotLoaiFile]
    ky: list[Ky]
    dau_du_lieu: date
    thieu_bo_nap: list[LoaiChuaCo]

    @property
    def thang(self) -> list[Thang]:
        """Mọi tháng, phẳng, theo thứ tự thời gian."""
        return [t for k in self.ky for t in k.thang]


def _thang_master(conn) -> dict[str, set[str]]:
    """Tháng nào đã nạp file master, lấy từ NGÀY TRONG TÊN FILE (_YYYYMMDD).

    File master không có cột ngày nghiệp vụ trong kho — bản mới đè bản cũ —
    nên dấu vết duy nhất còn lại là tên file trong nhật ký nạp.
    Lô đã hoàn tác (`undone_at IS NOT NULL`) KHÔNG tính là có dữ liệu.
    """
    out: dict[str, set[str]] = {}
    rows = conn.execute(
        """SELECT spec_name, source_file FROM meta.ingest_batch
           WHERE undone_at IS NULL"""
    ).fetchall()
    for spec, src in rows:
        if spec in _CO_BANG_FACT or spec in ("zaiko", "uriage"):
            continue
        m = re.search(r"_(\d{4})(\d{2})\d{2}\.xlsx$", src)
        if m:
            out.setdefault(spec, set()).add(f"{m.group(1)}-{m.group(2)}")
    return out


def tinh_bang_phu(conn, hom_nay: date | None = None,
                  dau_bang: date = DAU_BANG) -> BangPhu:
    """Tính bảng phủ dữ liệu từ kho. `conn` là kết nối psycopg đang mở.

    Hàm KHÔNG tự mở kết nối: người gọi quyết định CSDL nào (trang web phải
    tôn trọng `create_app(db_url=…)`, test luôn trỏ vào CSDL thử nghiệm).
    """
    hom_nay = hom_nay or date.today()
    database = conn.execute("SELECT current_database()").fetchone()[0]

    ban = dict(conn.execute(
        """SELECT to_char(sales_date,'YYYY-MM'), count(*)
           FROM core.fact_sales_line GROUP BY 1"""
    ).fetchall())
    ton = dict(conn.execute(
        """SELECT to_char(snapshot_date,'YYYY-MM'), count(DISTINCT snapshot_date)
           FROM core.fact_inventory_daily GROUP BY 1"""
    ).fetchall())
    master = _thang_master(conn)

    # Kỳ kế toán ĐỌC TỪ core.dim_date, không tính lại trong Python.
    thang_rows = conn.execute(
        """SELECT to_char(date_key,'YYYY-MM') AS thang,
                  min(company_fy)             AS fy,
                  min(company_fy_label)       AS nhan,
                  min(company_fy_month)       AS thang_ky,
                  bool_or(is_fy_end_month)    AS chot
           FROM core.dim_date
           WHERE date_key BETWEEN %s AND %s
           GROUP BY 1 ORDER BY 1""",
        (dau_bang, hom_nay),
    ).fetchall()

    ky_rows = {
        r[0]: (r[1], r[2], r[3])
        for r in conn.execute(
            """SELECT company_fy, company_fy_label, min(date_key), max(date_key)
               FROM core.dim_date GROUP BY 1, 2"""
        ).fetchall()
    }

    tien = {
        r[0]: (int(r[1] or 0), int(r[2] or 0))
        for r in conn.execute(
            """SELECT d.company_fy,
                      sum(f.amount - f.tax_amount),
                      sum(f.gross_profit)
               FROM core.fact_sales_line f
               JOIN core.dim_date d ON d.date_key = f.sales_date
               GROUP BY 1"""
        ).fetchall()
    }

    theo_ky: dict[int, list[Thang]] = {}
    for thang, fy, _nhan, thang_ky, chot in thang_rows:
        y, m = int(thang[:4]), int(thang[5:])
        # Tháng nằm TRỌN trước mốc dữ liệu -> ngoài phạm vi, mọi cột.
        # Tháng 2025-03 chứa chính ngày 3/3 nên vẫn trong phạm vi.
        ngoai = (y, m) < (DAU_DU_LIEU.year, DAU_DU_LIEU.month)
        o = []
        for c in COT:
            if c.khoa == "ban":
                co = bool(ban.get(thang))
            elif c.khoa == "ton":
                co = bool(ton.get(thang))
            else:
                co = thang in master.get(c.khoa, set())
            if co:
                o.append(O(c, CO, ton.get(thang) if c.khoa == "ton" else None))
            else:
                o.append(O(c, NGOAI if ngoai else KHONG))
        theo_ky.setdefault(fy, []).append(
            Thang(thang, fy, thang_ky, bool(chot), ngoai, o)
        )

    ky = []
    for fy in sorted(theo_ky):
        nhan, dau, cuoi = ky_rows[fy]
        dt, lg = tien.get(fy, (0, 0))
        ky.append(Ky(fy, nhan, dau, cuoi, theo_ky[fy], dt, lg))

    return BangPhu(database, COT, ky, DAU_DU_LIEU, THIEU_BO_NAP)


# --- Bảng theo NGÀY ------------------------------------------------------
# Bảng tháng ở trên trả lời "tháng nào thiếu". Từ khi có nhịp xuất file 13:30
# hằng ngày, câu hỏi thật sự đổi thành "hôm qua có sót ngày nào không" — mà
# độ phân giải tháng không bao giờ trả lời được.


@dataclass(frozen=True)
class Ngay:
    ngay: date
    thu: int                # isodow: 1 = thứ Hai … 7 = Chủ nhật
    la_cuoi_tuan: bool
    o: list[O]

    @property
    def nhan_thu(self) -> str:
        return ("T2", "T3", "T4", "T5", "T6", "T7", "CN")[self.thu - 1]


@dataclass(frozen=True)
class BangNgay:
    cot: list[CotLoaiFile]
    ngay: list[Ngay]        # MỚI NHẤT TRƯỚC — hôm nay ở dòng đầu
    dau: date
    cuoi: date
    thieu: dict[str, int]   # khoá cột -> số NGÀY LÀM VIỆC thiếu trong khung

    @property
    def co_thieu(self) -> bool:
        return any(self.thieu.values())


def tinh_bang_ngay(conn, hom_nay: date | None = None,
                   so_ngay: int = SO_NGAY_MAC_DINH) -> BangNgay:
    """Độ phủ từng ngày của 3 nguồn hằng ngày, `so_ngay` ngày lùi từ hôm nay.

    Không tự mở kết nối (xem ghi chú ở `tinh_bang_phu`). `hom_nay` bơm được
    để test khỏi phụ thuộc đồng hồ thật.

    Ngày NGHỈ (cuối tuần VÀ ngày lễ Nhật, từ 032) KHÔNG bao giờ tính là thiếu
    và không vào `thieu`: không ai xuất file thứ Bảy, nên 26 ô đỏ mỗi quý chỉ
    dạy người đọc lướt qua cả cột. "Nghỉ" đọc từ `mart.lich_kinh_doanh` — định
    nghĩa DUY NHẤT của ngày làm việc, dùng chung với `/kho-du-lieu` và
    `kome/tuoi_du_lieu.py`.
    """
    from kome.tuoi_du_lieu import hom_nay_o_nhat

    hom_nay = hom_nay or hom_nay_o_nhat()
    khung = conn.execute(
        """SELECT ngay, extract(isodow FROM ngay)::int, NOT la_ngay_kd
           FROM mart.lich_kinh_doanh
           WHERE ngay <= %s ORDER BY ngay DESC LIMIT %s""",
        (hom_nay, so_ngay),
    ).fetchall()
    if not khung:
        return BangNgay(COT_NGAY, [], hom_nay, hom_nay,
                        {c.khoa: 0 for c in COT_NGAY})

    dau = khung[-1][0]
    co: dict[str, set[date]] = {
        "ban": {r[0] for r in conn.execute(
            """SELECT DISTINCT sales_date FROM core.fact_sales_line
               WHERE sales_date BETWEEN %s AND %s""", (dau, hom_nay)).fetchall()},
        "ton": {r[0] for r in conn.execute(
            """SELECT DISTINCT snapshot_date FROM core.fact_inventory_daily
               WHERE snapshot_date BETWEEN %s AND %s""", (dau, hom_nay)).fetchall()},
        # Master khách: đọc `data_date` của lô (migration 018), KHÔNG tách lại
        # từ tên file như `_thang_master`. `core.dim_customer` là SCD2 nên ngày
        # khách không đổi gì thì nạp xong không có dòng nào mang ngày hôm đó.
        "tokuisaki": {r[0] for r in conn.execute(
            """SELECT DISTINCT data_date FROM meta.ingest_batch
               WHERE spec_name = 'tokuisaki' AND undone_at IS NULL
                 AND data_date BETWEEN %s AND %s""", (dau, hom_nay)).fetchall()},
    }

    ngay, thieu = [], {c.khoa: 0 for c in COT_NGAY}
    for d, thu, cuoi_tuan in khung:
        o = []
        for c in COT_NGAY:
            if d < DAU_DU_LIEU:
                tt = NGOAI
            elif d in co[c.khoa]:
                tt = CO
            elif cuoi_tuan:
                tt = NGHI
            else:
                tt = KHONG
                thieu[c.khoa] += 1
            o.append(O(c, tt))
        ngay.append(Ngay(d, thu, cuoi_tuan, o))

    return BangNgay(COT_NGAY, ngay, dau, hom_nay, thieu)
