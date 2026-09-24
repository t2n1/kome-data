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
                  spec_name, loaded_at, row_count, total_amount, data_date
           FROM meta.ingest_batch WHERE undone_at IS NULL
           ORDER BY spec_name, loaded_at DESC, batch_id DESC"""
    ).fetchall()
    seen = {r[0]: r for r in rows}
    return [
        {"name": s.display_name, "spec": k,
         "last": seen[k][1] if k in seen else None,
         "data_date": seen[k][4] if k in seen else None,
         "rows": seen[k][2] if k in seen else 0,
         "total": seen[k][3] if k in seen else 0,
         # File master / bảng giá KHÔNG mang giá trị tiền: `total_column` để
         # trống CÓ CHỦ Ý (xem kome/config.py). Cột "Tổng tiền" phải hiện "—",
         # không phải "¥0" — ¥0 làm người đọc tưởng hệ thống đếm hụt tiền và
         # đi báo một lỗi không tồn tại.
         "co_tien": s.total_column is not None}
        for k, s in SPECS.items()
    ]


# Bảng đích của từng loại file. PHẢI trùng `kome.pipeline.UNDO_TABLES` —
# đó là danh sách mà `undo_batch()` thật sự chạy `DELETE FROM … WHERE batch_id`
# lên. Chép tay ở đây CÓ CHỦ Ý, không nhập từ `kome.pipeline`: file này được
# `kome/web/app.py` nhập ở mức ngoài cùng, còn `kome.pipeline` kéo theo pandas +
# python-calamine (~120 MB) mà `requirements.txt` của bản Vercel cố ý không có —
# nhập vào đây là làm trang chết ngay lúc khởi động.
# Có test canh hai bản không bao giờ trôi khỏi nhau:
# tests/test_nhat_ky_nap.py::test_bang_theo_loai_trung_khop_undo_tables.
BANG_THEO_LOAI = {
    "zaiko": ["core.fact_inventory_daily"],
    "tokuisaki": ["core.dim_customer"],
    "uriage": ["core.fact_sales_line"],
    "meisai": ["core.fact_sales_line"],
    "shohin": ["core.dim_product"],
    "shiiresaki": ["core.dim_supplier"],
    "chokusousaki": ["core.dim_shipto"],
    "tanka": ["core.fact_price_list"],
    "seikyu_motocho": ["core.fact_ar_ledger"],
}

# Tên bảng bằng tiếng Việt cho người vận hành. Không in tên bảng SQL lên màn
# hình: người bấm nút Hoàn tác không biết `core.fact_sales_line` là cái gì,
# nhưng biết rất rõ "doanh thu" nghĩa là gì.
# Chữ "bảng" nằm TRONG tên chứ không ghép ở template: tên nghiệp vụ của
# core.fact_price_list vốn đã là "bảng giá", ghép thêm ra "bảng bảng giá".
TEN_BANG_VI = {
    "zaiko": "bảng tồn kho",
    "tokuisaki": "bảng khách hàng",
    "uriage": "bảng doanh thu",
    "meisai": "bảng doanh thu",
    "shohin": "bảng sản phẩm",
    "shiiresaki": "bảng nhà cung cấp",
    "chokusousaki": "bảng điểm giao thẳng",
    "tanka": "bảng giá",
    "seikyu_motocho": "sổ công nợ",
}


@dataclass(frozen=True)
class LoNap:
    batch_id: int
    loai: str
    ten_file: str
    ngay_du_lieu: date
    nap_luc: datetime
    so_dong: int          # row_count: số dòng FILE mang vào LÚC nạp
    tong_tien: int
    co_tien: bool
    ten_bang: str | None      # tên bảng đích, tiếng Việt (None = loại lạ)
    so_dong_xoa: int | None   # ĐẾM THẬT: hoàn tác bây giờ sẽ xoá bao nhiêu dòng
    tong_bang: int | None     # tổng số dòng đang có trong bảng đích

    @property
    def lam_trong_bang(self) -> bool:
        """Hoàn tác lô này có làm bảng đích TRỐNG SẠCH không?

        So số đếm thật với tổng số dòng của bảng, KHÔNG đoán theo loại file.
        Bản cũ đoán bằng một tập hằng bốn loại master và sai 2/7 loại: nó
        không cảnh báo cho uriage/meisai (đối soát tháng dán lô mới lên cả
        tháng ~18.000 dòng — hoàn tác xoá sạch cả tháng doanh thu), còn với
        tanka thì cảnh báo "sẽ trống hoàn toàn" trong khi khoá của bảng giá
        CÓ valid_from nên nó lùi đúng một lô.
        """
        return (self.so_dong_xoa is not None and self.so_dong_xoa > 0
                and self.so_dong_xoa == self.tong_bang)

    @property
    def nhieu_hon_luc_nap(self) -> bool:
        """Lô đang GIỮ nhiều dòng hơn số nó nạp vào?

        Xảy ra khi một dòng nguồn nở ra nhiều dòng đích (tanka: 10 mức giá
        nằm ngang -> tối đa 10 dòng dọc). Người đọc thấy "nạp 232 dòng" trên
        cột Số dòng mà câu xác nhận nói "xoá 1.914 dòng" thì phải được giải
        thích, nếu không họ kết luận màn hình sai và bỏ qua cả cảnh báo.
        """
        return self.so_dong_xoa is not None and self.so_dong_xoa > self.so_dong


def _dem_dong(conn, bang: list[str], lo: list[int]) -> tuple[dict, dict]:
    """Đếm THẬT: mỗi (bảng, lô) có bao nhiêu dòng, và mỗi bảng tổng bao nhiêu.

    Một câu truy vấn UNION ALL cho tất cả bảng thay vì một câu mỗi bảng: mỗi
    vòng hỏi–đáp qua pooler Tokyo mất ~60 ms, mà màn này mở hằng ngày.

    Tên bảng nội suy thẳng vào câu SQL là AN TOÀN ở đây: chúng đến từ hằng
    `BANG_THEO_LOAI` ngay trên, không từ dữ liệu người dùng. Riêng `batch_id`
    vẫn đi qua tham số.
    """
    if not bang or not lo:
        return {}, {}
    cau = " UNION ALL ".join(
        f"SELECT '{t}' AS bang, batch_id AS lo, count(*) AS n FROM {t}"
        f"  WHERE batch_id = ANY(%s) GROUP BY batch_id"
        f" UNION ALL SELECT '{t}', NULL::bigint, count(*) FROM {t}"
        for t in bang
    )
    dem: dict[tuple[str, int], int] = {}
    tong: dict[str, int] = {}
    for b, l, n in conn.execute(cau, [lo] * len(bang)).fetchall():
        if l is None:
            tong[b] = n
        else:
            dem[(b, l)] = n
    return dem, tong


def lo_nap_gan_nhat(conn, gioi_han: int = 10) -> list[LoNap]:
    """Các lô nạp gần nhất CHƯA bị hoàn tác, mới nhất đứng đầu.

    `undone_at IS NULL` là điều kiện bắt buộc, không phải bộ lọc cho gọn: lô
    đã hoàn tác mà vẫn hiện nút Hoàn tác thì lần bấm thứ hai xoá một thứ đã
    không còn, và người bấm tưởng lần đầu chưa ăn.

    `so_dong_xoa` ĐẾM THẬT trong bảng đích thay vì suy ra từ loại file. Mọi
    loader đều upsert, nên `batch_id` trên một dòng là "lô ĐỘNG VÀO nó lần
    cuối", không phải "lô sinh ra nó": sau một lần đối soát tháng, cả ~18.000
    dòng của tháng mang lô mới và `DELETE WHERE batch_id` xoá sạch cả tháng —
    kể cả phần do 20 lô hằng ngày trước đó nạp vào. Chỉ có đếm mới nói đúng.

    Dòng SCD2 bị ĐÈ TẠI CHỖ (`meta.ingest_batch.scd2_preimage`) cũng mang lô
    này nhưng hoàn tác HOÀN NGUYÊN chứ không xoá, nên phải trừ ra —
    `jsonb_array_length` đếm đúng số dòng đó. Với các loại không phải SCD2
    thì cột này NULL, `coalesce` cho 0, không cần rẽ nhánh.
    """
    rows = conn.execute(
        """SELECT batch_id, spec_name, source_file, data_date, loaded_at,
                  row_count, total_amount,
                  coalesce(jsonb_array_length(scd2_preimage), 0)
           FROM meta.ingest_batch
           WHERE undone_at IS NULL
           ORDER BY loaded_at DESC, batch_id DESC
           LIMIT %s""",
        (gioi_han,),
    ).fetchall()
    moi_bang = sorted({t for r in rows for t in BANG_THEO_LOAI.get(r[1], [])})
    dem, tong = _dem_dong(conn, moi_bang, [r[0] for r in rows])

    ds = []
    for r in rows:
        spec_name = r[1]
        bang = BANG_THEO_LOAI.get(spec_name, [])
        if bang:
            so_dong_xoa = max(0, sum(dem.get((t, r[0]), 0) for t in bang) - r[7])
            tong_bang = sum(tong.get(t, 0) for t in bang)
        else:
            so_dong_xoa = tong_bang = None
        ds.append(LoNap(
            batch_id=r[0], loai=_ten_loai(spec_name), ten_file=r[2],
            ngay_du_lieu=r[3], nap_luc=r[4], so_dong=r[5], tong_tien=r[6],
            co_tien=(SPECS[spec_name].total_column is not None)
                    if spec_name in SPECS else False,
            ten_bang=TEN_BANG_VI.get(spec_name),
            so_dong_xoa=so_dong_xoa, tong_bang=tong_bang))
    return ds
