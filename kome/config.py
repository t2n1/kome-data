# kome/config.py
from dataclasses import dataclass, field
from pathlib import Path
import yaml

@dataclass(frozen=True)
class FileSpec:
    name: str
    display_name: str
    filename_pattern: str
    sheet: str
    header_row: int
    min_rows: int
    keys: list[str]
    columns: dict[str, str]           # tên cột OBC -> tên cột hệ thống
    code_columns: list[str]
    money_columns: list[str]
    qty_columns: list[str]
    # Cột tiền ĐẠI DIỆN cho file: "tổng tiền" hiện trên màn hình nạp và
    # trang /health, và là số mà cổng 4 đem so với lần nạp trước.
    # PHẢI khai tay, KHÔNG suy ra từ money_columns[-1]: thứ tự cột trong
    # files.yml là thứ tự của OBC, không phải thứ tự quan trọng — lấy cột
    # cuối cho 売上伝票データ ra 入金額１ (gần như luôn bằng 0), làm tắt im
    # lặng nhánh cảnh báo lệch tiền của cổng 4 cho đúng file chở ¥1,5 tỷ/năm.
    # None = file này không có tiền đại diện (file master, bảng giá): tổng
    # bằng 0 và cổng 4 bỏ qua nhánh tiền — bỏ qua CÓ CHỦ Ý.
    total_column: str | None = None
    rate_columns: list[str] = field(default_factory=list)
    date_columns: list[str] = field(default_factory=list)
    # Cột ngày mà mỗi dòng BẮT BUỘC phải đọc được (vd. sales_date có khoá
    # ngoại tới core.dim_date). Ép kiểu lỗi -> None (xem date_columns) —
    # cổng 3 dùng danh sách này để CHẶN trước khi lô được lưu, tránh lô mồ
    # côi trong meta.ingest_batch hoặc vi phạm khoá ngoại giữa chừng.
    required_date_columns: list[str] = field(default_factory=list)
    # Một số bản xuất OBC lặp lại CÙNG một dòng nghiệp vụ nhiều lần dưới các
    # mục con khác nhau (vd. 売上伝票データ: 出荷内訳 và 明細按分). Bật cờ này để
    # reader giữ dòng đầu tiên của mỗi khoá (`keys`), bỏ các bản sao còn lại,
    # NGAY SAU KHI ĐỌC — trước khi tới cổng 3 (chặn khoá trùng).
    dedup_on_keys: bool = False
    product_check: dict | None = None
    warn_row_drop_ratio: float = 0.5  # ngưỡng cổng 4: số dòng rơi dưới này
    warn_total_spike: float = 3.0     # ngưỡng cổng 4: tổng tiền tăng quá này lần
    warn_total_drop: float = 0.34     # ngưỡng cổng 4: tổng tiền còn dưới này

def load_specs(path: Path) -> dict[str, FileSpec]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {name: FileSpec(name=name, **body) for name, body in raw.items()}
