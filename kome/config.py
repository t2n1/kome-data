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
    rate_columns: list[str] = field(default_factory=list)
    product_check: dict | None = None
    warn_row_drop_ratio: float = 0.5  # ngưỡng cổng 4: số dòng rơi dưới này
    warn_total_spike: float = 3.0     # ngưỡng cổng 4: tổng tiền tăng quá này lần
    warn_total_drop: float = 0.34     # ngưỡng cổng 4: tổng tiền còn dưới này

def load_specs(path: Path) -> dict[str, FileSpec]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {name: FileSpec(name=name, **body) for name, body in raw.items()}
