"""Hôm nay đã có dữ liệu chưa? — cho 3 nguồn nhân viên xuất mỗi ngày.

Trả lời đúng một câu hỏi: kho đã có dữ liệu MANG NGÀY HÔM NAY của 在庫一覧,
得意先全情報 và dữ liệu bán hàng chưa (売上明細表 hằng ngày — hoặc 売上伝票データ). Trang chỉ hiển thị; mọi quy tắc nằm ở đây
để lệnh terminal dùng lại được và để test bơm giờ giả vào.
"""
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from kome.config import SPECS

# Ba nguồn của nhịp 13:30 hằng ngày (xem CLAUDE.md, "Quy trình hằng ngày").
# Từ 2026-09-24 file bán hằng ngày là 売上明細表 (`meisai`); 売上伝票データ
# (`uriage`) chỉ còn xuất theo quý. Ô "bán hàng" vì vậy là MỘT ô cho cả hai
# spec (`CUNG_O`): lô nào của hai loại mang ngày mới nhất thì tính — đòi riêng
# `uriage` là ô đỏ "trễ 36 ngày" trong khi hôm nay đã nạp đủ (sự cố thật
# 2026-09-25). Các spec còn lại (商品データ, 仕入先, 直送先, 取引単価データ) xuất
# thưa, nên KHÔNG nằm trong ô cảnh báo này — đưa chúng vào là tạo ra một dải
# đỏ gần như thường trực.
NGUON_HANG_NGAY = ("zaiko", "tokuisaki", "meisai")
CUNG_O = {"meisai": ("meisai", "uriage")}


def spec_cua_o(spec: str) -> tuple[str, ...]:
    """Các spec cùng đổ vào ô `spec` của nhịp hằng ngày."""
    return CUNG_O.get(spec, (spec,))

# 13:30 là giờ nhân viên xuất file từ OBC (CLAUDE.md). Trước giờ này mà chưa
# có dữ liệu thì KHÔNG phải sự cố.
GIO_CHOT = time(13, 30)

# "Hôm nay" là hôm nay Ở NHẬT, không phải hôm nay của máy chủ. CSDL chạy múi
# giờ UTC (đo ngày 2026-09-17: SHOW timezone -> UTC), nên `current_date` của
# Postgres vẫn là HÔM QUA trong suốt 00:00-09:00 giờ Nhật — tức là suốt buổi
# sáng làm việc, đúng lúc người ta nhìn ô này nhiều nhất.
MUI_GIO = ZoneInfo("Asia/Tokyo")


@dataclass(frozen=True)
class TuoiNguon:
    spec: str
    ten: str
    ngay: date | None       # ngày dữ liệu mới nhất đang có; None = chưa nạp bao giờ
    trang_thai: str         # "xanh" | "cho" | "do" | "nghi"
    tre: int | None         # số ngày LÀM VIỆC trễ; None khi chưa nạp bao giờ


@dataclass(frozen=True)
class Tuoi:
    hom_nay: date
    nguon: list[TuoiNguon]
    co_thieu: bool          # có nguồn nào đang ở trạng thái "do" không


def _bay_gio() -> datetime:
    """Đồng hồ, tách riêng để test thay được.

    Test KHÔNG được phụ thuộc giờ chạy thật: một bộ test xanh buổi sáng và đỏ
    buổi chiều thì không chứng minh được gì.
    """
    return datetime.now(MUI_GIO)


def hom_nay_o_nhat() -> date:
    """Hôm nay Ở NHẬT — dùng chung cho mọi chỗ cần đồng hồ thật.

    Đừng thay bằng `date.today()`: máy chủ Vercel chạy UTC, nên suốt
    00:00–09:00 giờ Nhật nó trả về HÔM QUA — tức suốt buổi sáng làm việc.
    """
    return _bay_gio().date()


def _la_ngay_nghi(conn, ngay: date) -> bool:
    """Ngày nghỉ = KHÔNG phải ngày làm việc theo `mart.lich_kinh_doanh` (cuối
    tuần và ngày lễ Nhật, từ 032) — định nghĩa duy nhất, dùng chung với bảng
    phủ theo ngày và danh sách ngày thiếu của /kho-du-lieu. Ngày lễ mà đỏ thì
    dải đỏ dạy người đọc bỏ qua dải đỏ.

    dim_date chỉ trải 2024-2035. Ngoài khoảng đó thì lùi về thứ trong tuần của
    Python: thà tính đúng cuối tuần bằng cách khác còn hơn coi mọi ngày năm
    2036 là ngày làm việc và đỏ suốt.
    """
    row = conn.execute(
        "SELECT NOT la_ngay_kd FROM mart.lich_kinh_doanh WHERE ngay = %s", (ngay,)
    ).fetchone()
    return row[0] if row else ngay.weekday() >= 5


def tinh_tuoi(conn, bay_gio: datetime | None = None) -> Tuoi:
    """`bay_gio` bơm được để test khỏi phụ thuộc đồng hồ thật."""
    bay_gio = bay_gio or _bay_gio()
    hom_nay = bay_gio.date()
    qua_gio_chot = bay_gio.timetz().replace(tzinfo=None) >= GIO_CHOT

    nghi = _la_ngay_nghi(conn, hom_nay)

    # Ngày mới nhất của từng nguồn KÈM số ngày làm việc đã trôi qua kể từ đó,
    # gộp một lượt: mỗi vòng hỏi-đáp qua pooler Tokyo mất ~60 ms.
    moi_nhat = {
        r[0]: (r[1], r[2]) for r in conn.execute(
            """WITH o AS (SELECT * FROM unnest(%s::text[], %s::text[]) AS o(o, spec)),
               m AS (
                 SELECT o.o AS spec_name, max(b.data_date) AS ngay
                 FROM meta.ingest_batch b JOIN o ON o.spec = b.spec_name
                 WHERE b.undone_at IS NULL
                 GROUP BY o.o)
               SELECT m.spec_name, m.ngay,
                      (SELECT count(*) FROM mart.lich_kinh_doanh d
                        WHERE d.la_ngay_kd
                          AND d.ngay > m.ngay AND d.ngay <= %s)
               FROM m""",
            ([o for o in NGUON_HANG_NGAY for _ in spec_cua_o(o)],
             [s for o in NGUON_HANG_NGAY for s in spec_cua_o(o)], hom_nay),
        ).fetchall()
    }

    nguon = []
    for spec in NGUON_HANG_NGAY:
        ngay, tre = moi_nhat.get(spec, (None, None))
        if nghi:
            trang_thai = "nghi"
        elif ngay is not None and ngay >= hom_nay:
            trang_thai = "xanh"
        else:
            trang_thai = "do" if qua_gio_chot else "cho"
        nguon.append(TuoiNguon(spec=spec, ten=SPECS[spec].display_name,
                               ngay=ngay, trang_thai=trang_thai, tre=tre))

    return Tuoi(hom_nay=hom_nay, nguon=nguon,
                co_thieu=any(n.trang_thai == "do" for n in nguon))
