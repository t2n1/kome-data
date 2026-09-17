"""Hôm nay đã có dữ liệu chưa? — cho 3 nguồn nhân viên xuất mỗi ngày.

Trả lời đúng một câu hỏi: kho đã có dữ liệu MANG NGÀY HÔM NAY của 在庫一覧,
得意先全情報 và 売上伝票データ chưa. Trang chỉ hiển thị; mọi quy tắc nằm ở đây
để lệnh terminal dùng lại được và để test bơm giờ giả vào.
"""
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from kome.config import SPECS

# Ba nguồn của nhịp 13:30 hằng ngày (xem CLAUDE.md, "Quy trình hằng ngày").
# 5 spec còn lại (商品データ, 仕入先, 直送先, 取引単価データ, 売上明細表) xuất
# thưa hoặc chỉ dùng khi cần, nên KHÔNG nằm trong ô cảnh báo này — đưa chúng
# vào là tạo ra một dải đỏ gần như thường trực.
NGUON_HANG_NGAY = ("zaiko", "tokuisaki", "uriage")

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
    """Cuối tuần theo core.dim_date. Ngày lễ Nhật KHÔNG có trong dim_date nên
    vẫn bị coi là ngày làm việc — giống hệt cách /health xử lý ngày thiếu.

    dim_date chỉ trải 2024-2035. Ngoài khoảng đó thì lùi về thứ trong tuần của
    Python: thà tính đúng cuối tuần bằng cách khác còn hơn coi mọi ngày năm
    2036 là ngày làm việc và đỏ suốt.
    """
    row = conn.execute(
        "SELECT is_weekend FROM core.dim_date WHERE date_key = %s", (ngay,)
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
            """WITH m AS (
                 SELECT spec_name, max(data_date) AS ngay
                 FROM meta.ingest_batch
                 WHERE undone_at IS NULL AND spec_name = ANY(%s)
                 GROUP BY spec_name)
               SELECT m.spec_name, m.ngay,
                      (SELECT count(*) FROM core.dim_date d
                        WHERE d.is_weekend = false
                          AND d.date_key > m.ngay AND d.date_key <= %s)
               FROM m""",
            (list(NGUON_HANG_NGAY), hom_nay),
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
