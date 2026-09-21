"""Đọc NHẬT KÝ NẠP (`meta.ingest_batch`) cho màn Kho dữ liệu.

Tách khỏi `kome/coverage.py` có chủ ý. File đó khai rõ nó là "MỘT nơi duy nhất
tính BẢNG PHỦ", và nó đọc thẳng từ kho dữ liệu chứ không đếm tên file. File này
trả lời câu khác: lô nào đã vào, lúc nào, bao nhiêu dòng. Hai câu hỏi khác nhau
trên hai nguồn khác nhau — gộp lại làm mờ đúng ranh giới mà docstring kia dựng.
"""
from dataclasses import dataclass
from datetime import date, datetime

from kome.config import SPECS


def _ten_loai(spec_name: str) -> str:
    """Mã nội bộ -> tên tiếng Nhật OBC xuất ra.

    Lô cũ có thể mang `spec_name` không còn trong SPECS (đổi cấu hình sau khi
    đã nạp). Trả về chính mã đó còn hơn ném lỗi: người đọc vẫn tra ngược được,
    còn một trang 500 thì không giúp được gì.
    """
    s = SPECS.get(spec_name)
    return s.display_name if s else spec_name


def trang_thai_nap(conn) -> list[dict]:
    """Mỗi loại file: nạp lần cuối lúc nào, bao nhiêu dòng, tổng tiền bao nhiêu.

    Trả về dict (không phải dataclass) vì mẫu `_suc_khoe.html` được tách nguyên
    văn từ `health.html` và đang đọc đúng các khoá này.

    DISTINCT ON lấy lần nạp GẦN NHẤT của từng loại. KHÔNG dùng
    max(loaded_at)/max(row_count)/max(total_amount): ba hàm đó độc lập, lấy từ
    ba dòng khác nhau, nên sau một lần đối soát tháng ~18.000 dòng thì trang
    LUÔN hiện 18.000 — kể cả hôm nay OBC xuất cắt cụt còn 60 dòng.
    """
    rows = conn.execute(
        """SELECT DISTINCT ON (spec_name)
                  spec_name, loaded_at, row_count, total_amount
           FROM meta.ingest_batch WHERE undone_at IS NULL
           ORDER BY spec_name, loaded_at DESC, batch_id DESC"""
    ).fetchall()
    seen = {r[0]: r for r in rows}
    return [
        {"name": s.display_name,
         "last": seen[k][1] if k in seen else None,
         "rows": seen[k][2] if k in seen else 0,
         "total": seen[k][3] if k in seen else 0,
         # File master / bảng giá KHÔNG mang giá trị tiền: `total_column` để
         # trống CÓ CHỦ Ý (xem kome/config.py). Cột "Tổng tiền" phải hiện "—",
         # không phải "¥0" — ¥0 làm người đọc tưởng hệ thống đếm hụt tiền và
         # đi báo một lỗi không tồn tại.
         "co_tien": s.total_column is not None}
        for k, s in SPECS.items()
    ]


# Bốn loại master nạp bằng upsert: mỗi lần nạp dán batch_id MỚI lên mọi dòng,
# kể cả dòng đến từ lô trước. Nên `DELETE WHERE batch_id` của hoàn tác quét
# sạch cả bảng chứ không lùi về lô trước. Ba loại còn lại (fact_sales_line,
# fact_inventory_daily, dim_customer SCD2) lùi đúng một lô.
#
# Sự cố thật (2026-09-21): hoàn tác một lô shiiresaki (仕入先) 49 dòng, tưởng
# bảng lùi về lô trước còn 48 dòng — thực tế core.dim_supplier còn 0 dòng.
# Xem kome/pipeline.py::undo_batch và kome/loaders/master.py::make_loader.
_UPSERT_QUET_SACH = {"shohin", "shiiresaki", "chokusousaki", "tanka"}


@dataclass(frozen=True)
class LoNap:
    batch_id: int
    loai: str
    ten_file: str
    ngay_du_lieu: date
    nap_luc: datetime
    so_dong: int
    tong_tien: int
    co_tien: bool
    xoa_sach_bang: bool


def lo_nap_gan_nhat(conn, gioi_han: int = 10) -> list[LoNap]:
    """Các lô nạp gần nhất CHƯA bị hoàn tác, mới nhất đứng đầu.

    `undone_at IS NULL` là điều kiện bắt buộc, không phải bộ lọc cho gọn: lô
    đã hoàn tác mà vẫn hiện nút Hoàn tác thì lần bấm thứ hai xoá một thứ đã
    không còn, và người bấm tưởng lần đầu chưa ăn.
    """
    rows = conn.execute(
        """SELECT batch_id, spec_name, source_file, data_date, loaded_at,
                  row_count, total_amount
           FROM meta.ingest_batch
           WHERE undone_at IS NULL
           ORDER BY loaded_at DESC, batch_id DESC
           LIMIT %s""",
        (gioi_han,),
    ).fetchall()
    return [
        LoNap(batch_id=r[0], loai=_ten_loai(r[1]), ten_file=r[2],
              ngay_du_lieu=r[3], nap_luc=r[4], so_dong=r[5], tong_tien=r[6],
              co_tien=(SPECS[r[1]].total_column is not None) if r[1] in SPECS else False,
              xoa_sach_bang=(r[1] in _UPSERT_QUET_SACH))
        for r in rows
    ]
