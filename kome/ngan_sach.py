"""Ngân sách theo tháng — CÔNG TY (doanh thu + lãi gộp, `app.ngan_sach_cong_ty`, 041) và
TỪNG NGƯỜI (`app.ngan_sach`: `muc_tieu` = doanh thu, `lai_gop`) — đọc bảng nhập và ghi nó.
Ngân sách công ty là số NHẬP THẲNG, không phải tổng từng người (đặc tả
2026-09-24-ngan-sach-cong-ty-design.md).

Module này KHÔNG biết gì về HTTP: không FastAPI, không biểu mẫu, không cookie.
Nó chỉ nói chuyện với `app.ngan_sach` và `app.ngan_sach_nhat_ky` (migration
026). Ranh giới đó giống hệt `kome/web/nguoi_dung.py`: một chỗ giữ "con số
này là bao nhiêu", một chỗ giữ "ai được phép đổi nó".

Cũng KHÔNG mở kết nối và KHÔNG tự commit: hàm nhận sẵn `conn`, người gọi
quyết định ranh giới giao dịch. Gọi connect() không tham số ở đây sẽ âm thầm
ghi vào CSDL THẬT trong khi test tưởng mình đang dùng CSDL thử nghiệm.

Mọi công thức ("tiến độ", "mốc đến hôm nay") nằm trong view của `mart`, không
nằm ở đây — xem db/migrations/026_ngan_sach.sql.
"""
import re
from dataclasses import dataclass, field
from datetime import date

# Dấu phân cách hàng nghìn mà người ta thật sự gõ: dấu chấm (kiểu Việt), dấu
# phẩy (kiểu Anh), dấu cách ASCII, dấu cách KHÔNG NGẮT (NBSP, U+00A0) mà Excel
# hay dán ra, dấu cách TOÀN CHIỀU RỘNG (U+3000, bàn phím IME tiếng Nhật gõ
# ra), dấu cách hẹp không ngắt (U+202F), tab, và gạch dưới.
#
# [Vòng soát cuối, việc 1] Danh sách này từng liệt kê " " (ASCII) HAI LẦN
# trong `dict` literal — Python tự gộp khoá trùng, nên bản "NBSP" biến mất
# không lỗi nào nổ, còn `_NHOM` bên dưới dùng `\s` (khớp NBSP, U+3000, tab...)
# nên chuỗi vẫn QUA được kiểm cấu trúc rồi mới nổ `ValueError` trần ở
# `translate`. Xây CẢ HAI từ đúng MỘT danh sách ký tự này — không viết tay
# lớp ký tự cho `_NHOM` lần thứ hai — để hai thứ không bao giờ bất đồng lại.
_KY_TU_PHAN_CACH = [".", ",", " ", " ", "　", " ", "\t", "_"]
_PHAN_CACH = str.maketrans({c: "" for c in _KY_TU_PHAN_CACH})
_NGUYEN = re.compile(r"^[0-9]+$")
# Kiểm CẤU TRÚC NHÓM, không chỉ "bỏ dấu ra rồi xem còn toàn chữ số không":
# phép kiểm lỏng đó biến `1.5` thành 15, một con số người gõ không hề định
# nhập, ghi vào CSDL không lỗi nào, và chỉ lộ ra khi ai đó nhìn thấy chỉ tiêu
# tháng là ¥15. Mọi nhóm sau dấu phân cách phải đúng 3 chữ số.
_LOP_KY_TU_PHAN_CACH = "".join(re.escape(c) for c in _KY_TU_PHAN_CACH)
_NHOM = re.compile(rf"^[0-9]{{1,3}}(?:[{_LOP_KY_TU_PHAN_CACH}][0-9]{{3}})*$")


# Đối tượng "công ty" trong khoá ô (tên ô biểu mẫu `o-__cong_ty-doanh_thu-2026-05`) và
# hai chỉ số — trùng giá trị CHECK của app.ngan_sach_nhat_ky.chi_so (041).
CONG_TY = "__cong_ty"
CHI_SO = ("doanh_thu", "lai_gop")


class LoiSo(ValueError):
    """Một ô không đọc được thành số nguyên yên."""


def doc_so(chuoi: str | None) -> int | None:
    """Đọc một ô của biểu mẫu. None = ô TRỐNG = chưa đặt chỉ tiêu.

    "Chưa đặt" KHÁC "bằng không" (cùng nếp mart.san_pham_360.ton): trả 0 cho ô
    trống là ghi vào CSDL một chỉ tiêu bằng 0 cho người chưa được giao chỉ
    tiêu nào, và màn hình sau đó in `0` vào chỗ đáng lẽ để trống.

    Chỉ nhận chữ số ASCII: tiền là số nguyên yên nên không có phần thập phân,
    và số âm không phải chỉ tiêu. Chữ số toàn chiều rộng (１２３) bị từ chối
    thay vì âm thầm đổi — người gõ nhầm bảng mã cần biết ngay.

    [Vòng soát cuối, việc 1] `int()` LUÔN đi qua try/except ở đây — không bao
    giờ để một `ValueError` trần lọt ra khỏi hàm này. `kome/web/app.py` chỉ
    bắt `except LoiSo`; một ValueError trần rơi xuống `except Exception` của
    route và thành trang lỗi 500, mất sạch 60 ô người ta vừa gõ. Trước bản
    sửa này `_NHOM` (dùng `\\s`, khớp cả NBSP/U+3000/tab) và `_PHAN_CACH`
    (từng thiếu đúng NBSP vì hai khoá `" "` trùng nhau trong `dict` literal)
    lệch nhau, nên một chuỗi qua được `_NHOM` mà `translate` không dịch hết —
    `int()` ăn phải một ký tự lạ và ném ValueError trần. Giờ cả hai xây từ
    cùng một danh sách nên không lệch được nữa, nhưng vẫn bọc `int()` làm lớp
    phòng thủ thứ hai — hàm này không bao giờ được phép ném gì khác `LoiSo`.
    """
    if chuoi is None:
        return None
    s = chuoi.strip()
    if not s:
        return None
    if _NGUYEN.match(s):
        return int(s)
    if _NHOM.match(s):
        try:
            return int(s.translate(_PHAN_CACH))
        except ValueError as e:
            raise LoiSo(chuoi) from e
    raise LoiSo(chuoi)


@dataclass(frozen=True)
class Nguoi:
    ma: str
    ten: str


@dataclass(frozen=True)
class BangNhap:
    """Một kỳ của bảng nhập: 5 hàng người × 12 cột tháng.

    `o` CHỈ chứa những ô đã đặt chỉ tiêu. Ô vắng mặt = chưa đặt, và màn hình
    phải để trống chứ không in 0.
    """
    company_fy: int
    moi_ky: list[int]
    thang: list[str]           # 12 tháng 'YYYY-MM' theo THỨ TỰ KỲ (8月 trước)
    nguoi: list[Nguoi]
    o: dict[tuple[str, str], int]   # (salesperson_code, 'YYYY-MM') -> chỉ tiêu doanh thu
    o_lg: dict[tuple[str, str], int] = field(default_factory=dict)     # -> chỉ tiêu lãi gộp
    cong_ty: dict[tuple[str, str], int] = field(default_factory=dict)  # (chi_so, 'YYYY-MM') -> ngân sách công ty


def thang_cua_ky(company_fy: int) -> list[str]:
    """12 tháng của kỳ, 8月 của năm trước tới 7月 của năm company_fy.

    CÔNG KHAI vì `kome/bao_cao.py` nhập nó. "12 tháng của một kỳ, 8月 trước"
    là MỘT định nghĩa; hai bản chép của nó là hai thứ sẽ trôi khỏi nhau đúng
    lúc ai đó đổi năm tài chính của công ty.
    """
    return ([f"{company_fy - 1}-{t:02d}" for t in range(8, 13)]
            + [f"{company_fy}-{t:02d}" for t in range(1, 8)])


def _mung_1(thang: str) -> date:
    nam, t = thang.split("-")
    return date(int(nam), int(t), 1)


def bang_nhap(conn, company_fy: int | None = None) -> BangNhap:
    """Bảng nhập của một kỳ. company_fy=None => kỳ của `hom_nay`.

    Danh sách kỳ lấy từ `core.dim_date`, KHÔNG từ `mart.tong_theo_ky`: chỉ
    tiêu được đặt TRƯỚC khi bán, nên một danh sách chỉ gồm những kỳ đã có
    doanh thu là một danh sách không bao giờ cho đặt chỉ tiêu cho năm sau.

    [CRITICAL, vòng soát cuối việc 5] CHỈ những kỳ có ĐỦ 12 tháng trong
    `core.dim_date`. Bảng đó phủ 2024-01-01 → 2035-12-31, nên hai kỳ ở hai
    đầu dải chỉ nằm MỘT PHẦN trong lịch: kỳ 2024 (8月/2023 … 7月/2024) thiếu
    năm cột đầu, kỳ 2036 (8月/2035 … 7月/2036) thiếu bảy cột cuối. `DISTINCT
    company_fy` trần vẫn liệt kê cả hai — màn nhập vẽ đủ 12 ô, người dùng gõ
    số vào một cột không tồn tại trong dim_date, bấm Lưu thì khoá ngoại
    `app.ngan_sach.thang REFERENCES core.dim_date` ném `ForeignKeyViolation`
    thẳng ra ngoài, mất cả biểu mẫu. `HAVING count(DISTINCT company_fy_month)
    = 12` loại đúng hai kỳ cụt đó mà không cần biết ranh giới dải lịch.
    """
    moi_ky = [r[0] for r in conn.execute(
        """SELECT company_fy FROM core.dim_date
           GROUP BY company_fy
           HAVING count(DISTINCT company_fy_month) = 12
           ORDER BY 1""").fetchall()]

    # hom_nay có thể NULL (kho chưa có dòng bán nào) — khi đó rơi về kỳ giữa
    # dải lịch thay vì nổ, để màn nhập vẫn dùng được trước khi nạp dữ liệu.
    r = conn.execute(
        """SELECT d.company_fy FROM mart.moc_thoi_gian m
           JOIN core.dim_date d ON d.date_key = m.hom_nay""").fetchone()
    mac_dinh = r[0] if r else moi_ky[len(moi_ky) // 2]
    ky = company_fy if company_fy in moi_ky else mac_dinh

    nguoi = [Nguoi(ma=r[0], ten=r[1]) for r in conn.execute(
        "SELECT salesperson_code, ten FROM core.dim_salesperson "
        "ORDER BY salesperson_code").fetchall()]

    thang = thang_cua_ky(ky)
    # MỘT câu cho cả hai bảng (UNION ALL, cột đầu NULL = công ty) — không thêm lượt hỏi.
    o, o_lg, cong_ty = {}, {}, {}
    for r in conn.execute(
            """SELECT salesperson_code, to_char(thang, 'YYYY-MM'), muc_tieu, lai_gop
                 FROM app.ngan_sach WHERE thang >= %s AND thang <= %s
               UNION ALL
               SELECT NULL, to_char(thang, 'YYYY-MM'), doanh_thu, lai_gop
                 FROM app.ngan_sach_cong_ty WHERE thang >= %s AND thang <= %s""",
            (_mung_1(thang[0]), _mung_1(thang[-1])) * 2).fetchall():
        if r[0] is None:
            if r[2] is not None:
                cong_ty[("doanh_thu", r[1])] = int(r[2])
            if r[3] is not None:
                cong_ty[("lai_gop", r[1])] = int(r[3])
        else:
            if r[2] is not None:
                o[(r[0], r[1])] = int(r[2])
            if r[3] is not None:
                o_lg[(r[0], r[1])] = int(r[3])

    return BangNhap(company_fy=ky, moi_ky=moi_ky, thang=thang, nguoi=nguoi, o=o,
                    o_lg=o_lg, cong_ty=cong_ty)


def luu(conn, gia_tri: dict[tuple, int | None], nguoi_id: int | None) -> int:
    """Ghi những ô ĐÃ ĐỔI, trả về số ô đã đổi. Không tự commit.

    Khoá ô: `(đối tượng, chi_so, 'YYYY-MM')` — đối tượng là mã phụ trách hoặc `CONG_TY`,
    `chi_so` ∈ `CHI_SO`. Khoá hai phần `(mã, 'YYYY-MM')` (bản trước 041) = doanh thu của
    người đó.

    Chỉ đụng ô đã đổi, vì `sua_luc`/`sua_boi` phải trả lời "ai đổi con số NÀY lần cuối",
    không phải "ai bấm Lưu lần cuối". Một DÒNG (người hay công ty × tháng) mang hai ô; dòng
    không còn ô nào thì xoá cả dòng (CHECK của 041 cấm dòng rỗng).

    Số câu lệnh là hằng, không theo số ô: đọc hiện trạng (một câu cho cả hai bảng) · ghi
    / xoá dòng từng người · ghi / xoá dòng công ty · nhật ký — câu nào không có việc thì
    không chạy. Mỗi vòng hỏi qua pooler Tokyo ~47 ms; 60 ô thành 60 câu là ~3 giây.
    `unnest` trên mảng song song thay vì `(a, b) = ANY(%s)`: psycopg 3 không có adapter
    cho list[tuple[str, date]].
    """
    if not gia_tri:
        return 0
    chuan: dict[tuple[str, str, str], int | None] = {}
    for k, v in gia_tri.items():
        chuan[(k[0], "doanh_thu", k[1]) if len(k) == 2 else k] = v

    dong_ds = sorted({(doi, th) for doi, _, th in chuan})
    ng = [(d, t) for d, t in dong_ds if d != CONG_TY]
    hien: dict[tuple[str, str], dict[str, int | None]] = {}
    for r in conn.execute(
            """SELECT ns.salesperson_code, ns.thang, ns.muc_tieu, ns.lai_gop
                 FROM app.ngan_sach ns
                 JOIN unnest(%s::text[], %s::date[]) AS x(ma, thang)
                   ON ns.salesperson_code = x.ma AND ns.thang = x.thang
               UNION ALL
               SELECT %s, c.thang, c.doanh_thu, c.lai_gop
                 FROM app.ngan_sach_cong_ty c WHERE c.thang = ANY(%s::date[])""",
            ([d for d, _ in ng], [_mung_1(t) for _, t in ng], CONG_TY,
             [_mung_1(t) for d, t in dong_ds if d == CONG_TY])).fetchall():
        hien[(r[0], to_thang(r[1]))] = {
            "doanh_thu": int(r[2]) if r[2] is not None else None,
            "lai_gop": int(r[3]) if r[3] is not None else None}

    nhat_ky, dong_moi, doi = [], {}, set()
    for (dt, cs, th), moi in chuan.items():
        dong = dong_moi.setdefault(
            (dt, th), dict(hien.get((dt, th), {"doanh_thu": None, "lai_gop": None})))
        cu = dong[cs]
        if cu == moi:
            continue
        dong[cs] = moi
        doi.add((dt, th))
        nhat_ky.append((None if dt == CONG_TY else dt, _mung_1(th), cs, cu, moi, nguoi_id))
    if not nhat_ky:
        return 0

    dat_ng, xoa_ng, dat_ct, xoa_ct = [], [], [], []
    for (dt, th) in sorted(doi):
        d = dong_moi[(dt, th)]
        rong = d["doanh_thu"] is None and d["lai_gop"] is None
        if dt == CONG_TY:
            (xoa_ct if rong else dat_ct).append((_mung_1(th), d["doanh_thu"], d["lai_gop"]))
        else:
            (xoa_ng if rong else dat_ng).append((dt, _mung_1(th), d["doanh_thu"], d["lai_gop"]))

    if dat_ng:
        conn.execute(
            """INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu, lai_gop, sua_boi)
               SELECT x.ma, x.thang, x.dt, x.lg, %s::bigint
               FROM unnest(%s::text[], %s::date[], %s::bigint[], %s::bigint[])
                    AS x(ma, thang, dt, lg)
               ON CONFLICT (salesperson_code, thang) DO UPDATE
                 SET muc_tieu = EXCLUDED.muc_tieu, lai_gop = EXCLUDED.lai_gop,
                     sua_boi  = EXCLUDED.sua_boi,  sua_luc = now()""",
            (nguoi_id, [d[0] for d in dat_ng], [d[1] for d in dat_ng],
             [d[2] for d in dat_ng], [d[3] for d in dat_ng]))
    if xoa_ng:
        conn.execute(
            """DELETE FROM app.ngan_sach ns
               USING unnest(%s::text[], %s::date[]) AS x(ma, thang)
               WHERE ns.salesperson_code = x.ma AND ns.thang = x.thang""",
            ([d[0] for d in xoa_ng], [d[1] for d in xoa_ng]))
    if dat_ct:
        conn.execute(
            """INSERT INTO app.ngan_sach_cong_ty (thang, doanh_thu, lai_gop, sua_boi)
               SELECT x.thang, x.dt, x.lg, %s::bigint
               FROM unnest(%s::date[], %s::bigint[], %s::bigint[]) AS x(thang, dt, lg)
               ON CONFLICT (thang) DO UPDATE
                 SET doanh_thu = EXCLUDED.doanh_thu, lai_gop = EXCLUDED.lai_gop,
                     sua_boi   = EXCLUDED.sua_boi,   sua_luc = now()""",
            (nguoi_id, [d[0] for d in dat_ct], [d[1] for d in dat_ct], [d[2] for d in dat_ct]))
    if xoa_ct:
        conn.execute("DELETE FROM app.ngan_sach_cong_ty WHERE thang = ANY(%s::date[])",
                     ([d[0] for d in xoa_ct],))

    conn.execute(
        """INSERT INTO app.ngan_sach_nhat_ky
             (salesperson_code, thang, chi_so, muc_tieu_cu, muc_tieu_moi, sua_boi)
           SELECT * FROM unnest(%s::text[], %s::date[], %s::text[], %s::bigint[],
                                %s::bigint[], %s::bigint[])""",
        tuple([n[i] for n in nhat_ky] for i in range(6)))
    return len(nhat_ky)


def to_thang(d: date) -> str:
    """`date` mùng 1 -> 'YYYY-MM'. Dùng để so khớp với khoá của `gia_tri`."""
    return f"{d.year}-{d.month:02d}"
