# Giai đoạn 0 — Nền dữ liệu: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nạp được dữ liệu OBC hằng ngày từ Excel vào PostgreSQL qua trang kéo–thả, với 5 cổng kiểm tra chặn dữ liệu hỏng, nạp lại bao nhiêu lần cũng ra cùng kết quả, và có sao lưu đã thử khôi phục.

**Architecture:** Python đọc Excel theo cấu hình YAML (không hard-code tên cột) → 5 cổng kiểm tra → upsert vào PostgreSQL 3 lớp (`core` / `mart` / `app`). File gốc được chính trang nạp lưu trữ làm lớp `raw`. Web FastAPI phục vụ trang kéo–thả và trang kiểm tra sức khoẻ.

**Tech Stack:** Python 3.14 · pandas 3.0 + python-calamine · psycopg 3 · PostgreSQL 15+ (Supabase Free) · FastAPI + Jinja2 · pytest · PyYAML

**Spec:** `docs/superpowers/specs/2026-09-16-kome-data-platform-design.md`
**Liên kết dữ liệu:** `docs/data-linkage.md` — đọc trước khi viết bất kỳ migration nào

## Global Constraints

Sao chép nguyên văn từ đặc tả. **Mọi task đều ngầm chịu ràng buộc này.**

1. **Không bao giờ sửa dữ liệu OBC.** Sai thì sửa trong OBC rồi xuất lại. Hệ thống chỉ đọc.
2. **Nạp lại cùng file phải ra cùng kết quả.** Khoá tự nhiên, không dùng ID tự tăng làm khoá nghiệp vụ.
3. **Tiền luôn là số nguyên yên** — `BIGINT`. Không dùng `FLOAT`/`REAL` cho tiền. **Ngoại lệ: số lượng có phần thập phân thật** (`83.75` ケース) → `NUMERIC(14,4)`.
4. **Mọi cột `*コード` là `TEXT`**, ép `dtype=str` ngay lúc đọc Excel. `000000009292` mà thành `9292` là hỏng toàn bộ liên kết.
5. **Mỗi chỉ số chỉ định nghĩa một lần, trong `mart/`.**
6. **Không xoá dòng trong bảng SCD2** — chỉ đóng `valid_to`.
7. **Cổng kiểm tra 1–3 đã chặn thì không được bỏ qua.** Không có cờ `--force`.
8. **Mật khẩu chỉ nằm trong biến môi trường**, không bao giờ trong git.
9. `dim_salesperson` **chỉ chứa 5 `担当者` của OBC**, không gồm người nhập đơn.

**Mốc đối chiếu bắt buộc (dữ liệu thật đã đo):**

| Mốc | Giá trị |
|---|---|
| Tồn kho 2026-09-16 | **¥137.839.071** trên **177 dòng / 2 kho / 142 mã hàng** |
| Lãi gộp quý 2026-05→07 (`sum(gross_profit)`) | **¥114.315.334** — khớp tuyệt đối |
| Số dòng bán quý 2026-05→07 | **53.942** sau khi khử trùng |
| Doanh thu quý (`sum(amount - tax_amount)`) | **¥390.130.067** |

> **Khử trùng bắt buộc — nếu bỏ qua thì doanh thu sai gấp 2,16 lần.**
> File `売上伝票データ` 271 cột xuất **mỗi dòng hàng hai lần**: một lần dưới mục `出荷内訳`
> (chi tiết xuất kho), một lần dưới `明細按分` (phân bổ), mang cùng `金額` và cùng `粗利益`.
> 92.824 dòng thô → **53.942** khoá `伝票No. + 明細行番号`. Cột `明細行番号` là số thứ tự dòng.

> **Lưu ý về ¥3.217:** `売上明細表` báo doanh thu thuần quý là ¥390.126.850, còn tính từ
> `売上伝票データ` ra ¥390.130.067 — **hai bản xuất của chính OBC lệch nhau ¥3.217** (0,0008%)
> vì làm tròn thuế ở mức khác nhau: `売上明細表` có cột `税抜純売上高` do OBC làm tròn theo
> hoá đơn, `売上伝票データ` chỉ có `金額` đã gồm thuế. **Không được tự tính lại rồi coi là đúng** —
> lưu nguyên `金額` và `消費税額`, định nghĩa doanh thu thuần ở lớp `mart`.
> Lấy `粗利益` của OBC làm chuẩn cho lợi nhuận vì nó khớp tuyệt đối; nó cũng lệch ¥6.434 so với
> `(金額 − 消費税額) − 原価`, cùng lý do làm tròn.

---

## File Structure

| Đường dẫn | Trách nhiệm |
|---|---|
| `CLAUDE.md` | Ngữ cảnh nghiệp vụ cho AI. Đọc đầu mỗi phiên. |
| `config/files.yml` | Khai báo từng loại file OBC: sheet, dòng header, khoá, ánh xạ cột, kiểu dữ liệu |
| `config/salesperson_map.yml` | Ánh xạ mã `担当者` OBC ↔ mã người nhập đơn trên web |
| `db/migrate.py` | Chạy các file `.sql` theo thứ tự, ghi lại đã chạy cái nào |
| `db/migrations/*.sql` | Cấu trúc CSDL. Chỉ thêm file mới, **không sửa file cũ** |
| `kome/config.py` | Đọc `config/*.yml`, trả về đối tượng khai báo file |
| `kome/db.py` | Kết nối Postgres, helper `copy`/`execute` |
| `kome/reader.py` | Excel → DataFrame theo khai báo. Ép kiểu, chuẩn hoá tên cột |
| `kome/gates.py` | 5 cổng kiểm tra. Trả về danh sách lỗi chặn + cảnh báo |
| `kome/archive.py` | Lưu trữ file gốc + băm nội dung + nhật ký nạp |
| `kome/loaders/inventory.py` | `在庫一覧` → `dim_warehouse` + `fact_inventory_daily` |
| `kome/loaders/master.py` | Loader chung cho master data đơn giản, điều khiển bằng YAML |
| `kome/loaders/customer.py` | `得意先全情報` → `dim_customer` SCD2 |
| `kome/loaders/sales.py` | `売上伝票データ` → `fact_sales_line` |
| `kome/web/app.py` | FastAPI: trang kéo–thả, trang sức khoẻ, hoàn tác |
| `ops/backup.py` | Kết xuất hằng đêm + kiểm tra khôi phục |

---

## Task 1: Khung repo và tài liệu ngữ cảnh

**Files:**
- Create: `pyproject.toml`, `.env.example`, `CLAUDE.md`, `docs/glossary-ja-vi.md`, `kome/__init__.py`, `tests/__init__.py`
- Test: `tests/test_smoke.py`

**Interfaces:**
- Consumes: (không)
- Produces: gói `kome` import được; `pytest` chạy được

- [ ] **Step 1: Viết test khói**

```python
# tests/test_smoke.py
def test_package_importable():
    import kome
    assert kome.__version__
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kome'`

- [ ] **Step 3: Tạo gói và cấu hình**

```toml
# pyproject.toml
[project]
name = "kome-data"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pandas>=3.0",
    "python-calamine>=0.2",
    "psycopg[binary]>=3.2",
    "PyYAML>=6.0",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.setuptools.packages.find]
include = ["kome*"]
```

```python
# kome/__init__.py
__version__ = "0.1.0"
```

```bash
# .env.example  — sao chép thành .env và điền giá trị thật. KHÔNG commit .env
DATABASE_URL=postgresql://user:pass@host:5432/postgres
DATABASE_URL_TEST=postgresql://user:pass@host:5432/postgres_test
ARCHIVE_DIR=./raw_archive
```

- [ ] **Step 4: Cài và chạy test**

Run: `pip install -e ".[dev]" && pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Viết `CLAUDE.md`**

Nội dung bắt buộc — đây là thứ giữ cho dự án sống được 5 năm:

```markdown
# Ngữ cảnh dự án kome-data

## Công ty làm gì
株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật.
~¥1,5 tỷ doanh thu/năm · 2.080 khách hàng · 232 mã hàng · 5 nhân viên phụ trách khách.
Khách chủ yếu là tạp hoá Việt (577) và quán ăn Việt (269), trải 48 tỉnh.

## Luật số một
**OBC 奉行 là sổ cái kế toán chính thức. Dữ liệu của nó CHỈ ĐỌC.**
Số sai thì sửa trong OBC rồi xuất lại — không bao giờ UPDATE trong CSDL này.

## Quy trình hằng ngày
13:30 nhân viên xuất 3 file từ OBC, kéo thả vào trang nội bộ.
Đầu mỗi tháng xuất lại toàn bộ tháng trước để bắt các phiếu đã bị sửa/huỷ (đối soát tháng).

## Từ điển
得意先 = khách hàng · 請求先 = bên nhận hoá đơn (có thể khác 得意先)
伝票 = phiếu · 赤伝 = phiếu đỏ (hàng trả lại, số ÂM, không được lọc bỏ)
粗利益 = lãi gộp · 単価 = đơn giá · 単位原価 = giá vốn đơn vị
締め日 = ngày chốt công nợ · 直送先 = điểm giao thẳng
担当者 = người phụ trách khách · 倉庫 = kho · 賞味期限 = hạn sử dụng
荷姿区分 = quy cách đóng gói (00 = バラ lẻ, 02 = ケース thùng)

## Bẫy đã biết
1. Mã (`*コード`) là TEXT. `000000009292` đọc thành số sẽ mất số 0 đầu → hỏng mọi liên kết.
2. Số lượng CÓ phần thập phân (`83.75` ケース). Tiền thì luôn là số nguyên yên.
3. Có bản xuất `得意先全情報` chỉ 201 dòng (xuất một phần) và bản chỉ 5 cột (sai mẫu) — cổng 3 phải chặn.
4. File báo cáo (`売上明細表`, `元帳`) có 5 dòng rác trước header. File master và `在庫一覧` thì header ở dòng 1.
5. `担当者` của OBC (5 người) KHÁC người nhập đơn trên web (7 tài khoản, gồm 2 arubaito).

## Không được tự ý sửa
- File trong `db/migrations/` đã chạy rồi — chỉ thêm file mới
- Luật bất biến trong kế hoạch/đặc tả
- Định nghĩa chỉ số ở chỗ khác ngoài `mart/`

## Chạy test
pytest -v
```

- [ ] **Step 6: Viết `docs/glossary-ja-vi.md`** — mở rộng phần từ điển ở trên, mỗi thuật ngữ thêm cột "xuất hiện ở file nào".

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .env.example CLAUDE.md docs/glossary-ja-vi.md kome/ tests/
git commit -m "feat: khung repo, gói kome, tài liệu ngữ cảnh cho AI"
```

---

## Task 2: Kết nối CSDL và hệ thống migration

**Files:**
- Create: `kome/db.py`, `db/migrate.py`, `db/migrations/001_schemas.sql`, `tests/conftest.py`, `tests/test_migrate.py`

**Interfaces:**
- Consumes: biến môi trường `DATABASE_URL`, `DATABASE_URL_TEST`
- Produces:
  - `kome.db.connect(url: str | None = None) -> psycopg.Connection`
  - `db.migrate.apply_all(conn, migrations_dir: Path) -> list[str]` — trả về tên các file vừa chạy

- [ ] **Step 1: Viết test**

```python
# tests/conftest.py
import os, pytest, psycopg

@pytest.fixture
def test_db_url() -> str:
    """CHỈ CSDL thử nghiệm. Fixture conn sẽ XOÁ SẠCH schema — không bao giờ trỏ vào CSDL thật."""
    url = os.environ["DATABASE_URL_TEST"]
    assert url != os.environ.get("DATABASE_URL"), \
        "DATABASE_URL_TEST trùng DATABASE_URL — test sẽ xoá sạch CSDL thật"
    return url

@pytest.fixture
def conn(test_db_url):
    with psycopg.connect(test_db_url) as c:
        c.execute("DROP SCHEMA IF EXISTS core, mart, app, meta CASCADE")
        c.commit()
        yield c

@pytest.fixture
def batch(conn):
    """Tạo sẵn một dòng meta.ingest_batch và trả về batch_id.

    Mọi bảng fact/dim đều có batch_id REFERENCES meta.ingest_batch(batch_id),
    nên test nào ghi dữ liệu cũng phải có lô thật — truyền số 1 tuỳ tiện sẽ
    vi phạm khoá ngoại.
    """
    from pathlib import Path
    from db.migrate import apply_all
    apply_all(conn, Path("db/migrations"))

    def _make(n: int = 1) -> int:
        row = conn.execute(
            """INSERT INTO meta.ingest_batch
                 (spec_name, source_file, digest, archived_to, row_count)
               VALUES ('test', 'test.xlsx', %s, '/tmp/test.xlsx', 0)
               RETURNING batch_id""",
            (f"digest-{n}",),
        ).fetchone()
        conn.commit()
        return row[0]

    return _make
```

> **Lưu ý cho mọi task sau:** test nào ghi vào bảng có `batch_id` thì dùng fixture `batch` để lấy id thật, ví dụ `bid = batch(1)`. Đừng truyền số cứng.

```python
# tests/test_migrate.py
from pathlib import Path
from db.migrate import apply_all

def test_apply_all_creates_schemas(conn):
    applied = apply_all(conn, Path("db/migrations"))
    assert "001_schemas.sql" in applied
    row = conn.execute(
        "SELECT count(*) FROM information_schema.schemata "
        "WHERE schema_name IN ('core','mart','app','meta')"
    ).fetchone()
    assert row[0] == 4

def test_apply_all_is_idempotent(conn):
    first = apply_all(conn, Path("db/migrations"))
    second = apply_all(conn, Path("db/migrations"))
    assert first != []
    assert second == []   # lần hai không chạy lại gì
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_migrate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Viết migration đầu tiên**

```sql
-- db/migrations/001_schemas.sql
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS meta;

COMMENT ON SCHEMA core IS 'Dữ liệu OBC đã chuẩn hoá. CHỈ ĐỌC với mọi ứng dụng.';
COMMENT ON SCHEMA mart IS 'Bảng tổng hợp cho báo cáo. Định nghĩa chỉ số nằm ở đây.';
COMMENT ON SCHEMA app IS 'Dữ liệu do ứng dụng sinh ra. Đọc-ghi.';
COMMENT ON SCHEMA meta IS 'Nhật ký nạp, trạng thái migration.';
```

- [ ] **Step 4: Viết `kome/db.py` và `db/migrate.py`**

```python
# kome/db.py
import os
import psycopg

def connect(url: str | None = None) -> psycopg.Connection:
    """Mở kết nối Postgres. Mật khẩu chỉ đến từ biến môi trường."""
    return psycopg.connect(url or os.environ["DATABASE_URL"])
```

```python
# db/migrate.py
from pathlib import Path
import psycopg

_TRACKER = """
CREATE SCHEMA IF NOT EXISTS meta;
CREATE TABLE IF NOT EXISTS meta.schema_migration (
    filename    text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now()
);
"""

def apply_all(conn: psycopg.Connection, migrations_dir: Path) -> list[str]:
    """Chạy các file .sql chưa chạy, theo thứ tự tên. Trả về tên file vừa chạy."""
    conn.execute(_TRACKER)
    conn.commit()
    done = {r[0] for r in conn.execute("SELECT filename FROM meta.schema_migration")}
    applied = []
    for path in sorted(migrations_dir.glob("*.sql")):
        if path.name in done:
            continue
        conn.execute(path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO meta.schema_migration (filename) VALUES (%s)", (path.name,)
        )
        conn.commit()
        applied.append(path.name)
    return applied

if __name__ == "__main__":
    from kome.db import connect
    with connect() as c:
        for name in apply_all(c, Path(__file__).parent / "migrations"):
            print(f"đã chạy {name}")
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/test_migrate.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add kome/db.py db/ tests/conftest.py tests/test_migrate.py
git commit -m "feat: kết nối CSDL và hệ thống migration bằng file SQL đánh số"
```

---

## Task 3: Đọc Excel theo cấu hình YAML

**Files:**
- Create: `config/files.yml`, `kome/config.py`, `kome/reader.py`, `tests/test_reader.py`
- Test fixture: `tests/fixtures/zaiko_ok.xlsx` (chép từ `在庫一覧_20260916.xlsx` thật)

**Interfaces:**
- Consumes: `config/files.yml`
- Produces:
  - `kome.config.FileSpec` — dataclass: `name, sheet, header_row, keys, columns, code_columns, money_columns, qty_columns, rate_columns, min_rows`
  - `kome.config.load_specs(path: Path) -> dict[str, FileSpec]`
  - `kome.reader.read(path: Path, spec: FileSpec) -> pandas.DataFrame` — cột đã đổi sang tên tiếng Anh, đã ép kiểu

- [ ] **Step 1: Viết test**

```python
# tests/test_reader.py
from pathlib import Path
from decimal import Decimal
from kome.config import load_specs
from kome.reader import read

SPECS = load_specs(Path("config/files.yml"))

def test_reads_inventory_fixture():
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    assert len(df) == 177
    assert df["stock_value"].sum() == 137_839_071

def test_codes_keep_leading_zeros():
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    assert set(df["warehouse_code"]) == {"0001", "1002"}
    assert df["warehouse_code"].dtype == object   # không bao giờ là số

def test_quantity_keeps_decimals():
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    assert (df["stock_qty"] % 1 != 0).sum() == 20   # 20 dòng có phần lẻ

def test_money_is_integer():
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), SPECS["zaiko"])
    assert df["stock_value"].dtype.kind in "iu"
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_reader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kome.config'`

- [ ] **Step 3: Viết `config/files.yml`**

```yaml
# Khai báo từng loại file xuất từ OBC.
# OBC đổi tên cột khi nâng phiên bản → SỬA FILE NÀY, không sửa code.
zaiko:
  display_name: 在庫一覧
  filename_pattern: '^在庫一覧_(?P<date>\d{8})\.xlsx$'
  sheet: 在庫一覧表
  header_row: 1          # header ở dòng 1 (khác file báo cáo)
  min_rows: 50           # dưới ngưỡng này coi là xuất một phần → cổng 3 chặn
  keys: [product_code, warehouse_code]
  columns:
    商品コード:     product_code
    商品名:         product_name
    荷姿区分コード: pack_code
    荷姿区分名:     pack_name
    倉庫コード:     warehouse_code
    倉庫名:         warehouse_name
    日本語:         name_ja
    単位:           unit
    賞味期限:       best_before
    売上出荷数量:   shipped_qty      # số xuất TRONG NGÀY (đã xác nhận)
    在庫残数:       stock_qty
    在庫単価:       stock_unit_cost
    在庫金額:       stock_value
  code_columns:  [product_code, pack_code, warehouse_code]
  money_columns: [stock_unit_cost, stock_value]
  qty_columns:   [shipped_qty, stock_qty]
  rate_columns:  []
  # Đối chiếu cho cổng 5: cột tích = thừa số × thừa số
  product_check: {result: stock_value, factors: [stock_qty, stock_unit_cost]}
```

- [ ] **Step 4: Viết `kome/config.py`**

```python
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

def load_specs(path: Path) -> dict[str, FileSpec]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {name: FileSpec(name=name, **body) for name, body in raw.items()}
```

- [ ] **Step 5: Viết `kome/reader.py`**

```python
# kome/reader.py
from pathlib import Path
import pandas as pd
from kome.config import FileSpec

class ColumnMismatch(Exception):
    """Cột trong file không khớp khai báo — cổng 2 dùng lỗi này."""

def read(path: Path, spec: FileSpec) -> pd.DataFrame:
    """Đọc file Excel theo khai báo. Mọi mã giữ nguyên dạng chuỗi."""
    df = pd.read_excel(
        path,
        sheet_name=spec.sheet,
        header=spec.header_row - 1,
        engine="calamine",
        dtype=str,              # đọc TẤT CẢ dạng chuỗi trước, ép kiểu sau
    )
    df.columns = [str(c).strip() for c in df.columns]

    missing = [ja for ja in spec.columns if ja not in df.columns]
    if missing:
        raise ColumnMismatch(
            f"{spec.display_name}: thiếu {len(missing)} cột: {missing[:10]}"
        )

    df = df[list(spec.columns)].rename(columns=spec.columns)
    df = df.dropna(how="all")

    for col in spec.money_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).round().astype("int64")
    for col in spec.qty_columns + spec.rate_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype("float64")
    for col in spec.code_columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df.reset_index(drop=True)
```

- [ ] **Step 6: Tạo fixture và chạy test**

```bash
cp "$USERPROFILE/OneDrive - 株式会社KOME/Desktop/データバックアップ/在庫一覧_20260916.xlsx" tests/fixtures/zaiko_ok.xlsx
pytest tests/test_reader.py -v
```

Expected: 4 passed

> **Lưu ý:** file trong OneDrive có thể bị khoá (`PermissionError`). Luôn **chép ra rồi mới đọc**, đừng đọc thẳng.

- [ ] **Step 7: Commit**

```bash
git add config/files.yml kome/config.py kome/reader.py tests/test_reader.py tests/fixtures/zaiko_ok.xlsx
git commit -m "feat: đọc Excel theo cấu hình YAML, giữ số 0 đầu ở mã và thập phân ở số lượng"
```

---

## Task 4: Bộ 5 cổng kiểm tra

**Files:**
- Create: `kome/gates.py`, `tests/test_gates.py`
- Test fixtures: `tests/fixtures/zaiko_thieu_cot.xlsx`, `tests/fixtures/zaiko_cat_cut.xlsx`

**Interfaces:**
- Consumes: `kome.config.FileSpec`, `kome.reader.read`
- Produces:
  - `kome.gates.Blocker` (dataclass: `gate: int, message: str`)
  - `kome.gates.Warning_` (dataclass: `gate: int, message: str`)
  - `kome.gates.check(path, spec, df, previous: dict | None) -> tuple[list[Blocker], list[Warning_]]`

- [ ] **Step 1: Viết test**

```python
# tests/test_gates.py
from pathlib import Path
import pytest
from kome.config import load_specs
from kome.reader import read, ColumnMismatch
from kome.gates import check

SPECS = load_specs(Path("config/files.yml"))
OK = Path("tests/fixtures/zaiko_ok.xlsx")

def test_file_tot_khong_bi_chan():
    df = read(OK, SPECS["zaiko"])
    blockers, _ = check(OK, SPECS["zaiko"], df, previous=None)
    assert blockers == []

def test_cong_1_chan_sai_ten_file():
    df = read(OK, SPECS["zaiko"])
    blockers, _ = check(Path("bao_cao_linh_tinh.xlsx"), SPECS["zaiko"], df, None)
    assert any(b.gate == 1 for b in blockers)

def test_cong_2_chan_thieu_cot():
    with pytest.raises(ColumnMismatch):
        read(Path("tests/fixtures/zaiko_thieu_cot.xlsx"), SPECS["zaiko"])

def test_cong_3_chan_file_cat_cut():
    df = read(Path("tests/fixtures/zaiko_cat_cut.xlsx"), SPECS["zaiko"])
    blockers, _ = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert any(b.gate == 3 for b in blockers)

def test_cong_3_chan_khoa_trung():
    import pandas as pd
    df = read(OK, SPECS["zaiko"])
    doubled = pd.concat([df, df.iloc[[0]]], ignore_index=True)   # pandas 3: KHÔNG dùng _append
    blockers, _ = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], doubled, None)
    assert any(b.gate == 3 and "trùng" in b.message for b in blockers)

def test_cong_4_canh_bao_khi_tut_manh():
    df = read(OK, SPECS["zaiko"])
    prev = {"row_count": 400, "total": 300_000_000}
    _, warnings = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, prev)
    assert any(w.gate == 4 for w in warnings)

def test_cong_5_canh_bao_khi_tich_khong_khop():
    df = read(OK, SPECS["zaiko"])
    df.loc[0, "stock_value"] = 1
    _, warnings = check(Path("在庫一覧_20260916.xlsx"), SPECS["zaiko"], df, None)
    assert any(w.gate == 5 for w in warnings)
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_gates.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kome.gates'`

- [ ] **Step 3: Tạo hai fixture hỏng**

```python
# chạy một lần để sinh fixture, lưu thành scripts/make_bad_fixtures.py
import openpyxl
src = "tests/fixtures/zaiko_ok.xlsx"

wb = openpyxl.load_workbook(src); ws = wb.active
ws.delete_cols(11)                      # bỏ cột 在庫残数
wb.save("tests/fixtures/zaiko_thieu_cot.xlsx")

wb = openpyxl.load_workbook(src); ws = wb.active
ws.delete_rows(12, ws.max_row)          # chỉ còn 10 dòng dữ liệu
wb.save("tests/fixtures/zaiko_cat_cut.xlsx")
```

- [ ] **Step 4: Viết `kome/gates.py`**

```python
# kome/gates.py
from dataclasses import dataclass
from pathlib import Path
import re
import pandas as pd
from kome.config import FileSpec

@dataclass(frozen=True)
class Blocker:
    gate: int
    message: str

@dataclass(frozen=True)
class Warning_:
    gate: int
    message: str

def check(
    path: Path, spec: FileSpec, df: pd.DataFrame, previous: dict | None
) -> tuple[list[Blocker], list[Warning_]]:
    """5 cổng. Cổng 1-3 chặn, cổng 4-5 cảnh báo. Không bao giờ sửa dữ liệu."""
    blockers: list[Blocker] = []
    warnings: list[Warning_] = []

    # Cổng 1 — nhận diện file qua tên
    if not re.match(spec.filename_pattern, path.name):
        blockers.append(Blocker(1, f"Tên file không đúng mẫu {spec.display_name}: {path.name}"))

    # Cổng 2 — khớp cột: reader đã ném ColumnMismatch trước khi tới đây

    # Cổng 3 — hợp lý nghiệp vụ
    if len(df) < spec.min_rows:
        blockers.append(Blocker(3, f"Chỉ có {len(df)} dòng, tối thiểu {spec.min_rows} — nghi file xuất một phần"))
    dup = df.duplicated(subset=spec.keys).sum()
    if dup:
        blockers.append(Blocker(3, f"{dup} dòng trùng khoá {spec.keys}"))
    for col in spec.code_columns:
        if (df[col] == "").all():
            blockers.append(Blocker(3, f"Cột mã {col} rỗng toàn bộ"))

    # Cổng 4 — so với lần nạp trước
    total_col = spec.money_columns[-1] if spec.money_columns else None
    total = int(df[total_col].sum()) if total_col else 0
    if previous:
        prev_rows = previous.get("row_count") or 0
        prev_total = previous.get("total") or 0
        if prev_rows and len(df) < prev_rows * 0.5:
            warnings.append(Warning_(4, f"Số dòng rơi từ {prev_rows} xuống {len(df)}"))
        if prev_total and (total > prev_total * 3 or total < prev_total * 0.34):
            warnings.append(Warning_(4, f"Tổng tiền lệch mạnh: {prev_total:,} → {total:,}"))

    # Cổng 5 — đối chiếu tích
    pc = spec.product_check
    if pc:
        a, b = pc["factors"]
        expected = (df[a] * df[b]).round()
        bad = int((expected - df[pc["result"]]).abs().gt(1).sum())
        if bad:
            warnings.append(Warning_(5, f"{bad} dòng có {a} × {b} ≠ {pc['result']}"))

    return blockers, warnings
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/test_gates.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add kome/gates.py tests/test_gates.py tests/fixtures/ scripts/make_bad_fixtures.py
git commit -m "feat: 5 cổng kiểm tra, chặn được file cắt cụt và thiếu cột"
```

---

## Task 5: Nhật ký nạp, lưu trữ file gốc, nạp lại vô hại

**Files:**
- Create: `db/migrations/002_ingest_log.sql`, `kome/archive.py`, `tests/test_archive.py`

**Interfaces:**
- Consumes: `kome.db.connect`
- Produces:
  - `kome.archive.sha256_of(path) -> str`
  - `kome.archive.already_loaded(conn, digest) -> bool`
  - `kome.archive.store(conn, path, spec_name, digest, row_count, total, archive_dir) -> int` — trả về `batch_id`
  - `kome.archive.previous_stats(conn, spec_name) -> dict | None`
  - `kome.archive.undo(conn, batch_id) -> None`

- [ ] **Step 1: Viết test**

```python
# tests/test_archive.py
from pathlib import Path
from db.migrate import apply_all
from kome import archive

OK = Path("tests/fixtures/zaiko_ok.xlsx")

def test_hash_on_dinh():
    assert archive.sha256_of(OK) == archive.sha256_of(OK)

def test_nhan_ra_file_da_nap(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    d = archive.sha256_of(OK)
    assert archive.already_loaded(conn, d) is False
    archive.store(conn, OK, "zaiko", d, 177, 137_839_071, tmp_path)
    assert archive.already_loaded(conn, d) is True

def test_luu_tru_file_goc(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    d = archive.sha256_of(OK)
    archive.store(conn, OK, "zaiko", d, 177, 137_839_071, tmp_path)
    saved = list(tmp_path.rglob("*.xlsx"))
    assert len(saved) == 1
    assert d[:12] in saved[0].name

def test_previous_stats(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    archive.store(conn, OK, "zaiko", "aaa", 177, 137_839_071, tmp_path)
    prev = archive.previous_stats(conn, "zaiko")
    assert prev["row_count"] == 177 and prev["total"] == 137_839_071
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_archive.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kome.archive'`

- [ ] **Step 3: Viết migration**

```sql
-- db/migrations/002_ingest_log.sql
CREATE TABLE meta.ingest_batch (
    batch_id     bigserial PRIMARY KEY,
    spec_name    text        NOT NULL,
    source_file  text        NOT NULL,
    digest       text        NOT NULL UNIQUE,
    archived_to  text        NOT NULL,
    row_count    integer     NOT NULL,
    total_amount bigint      NOT NULL DEFAULT 0,
    loaded_at    timestamptz NOT NULL DEFAULT now(),
    undone_at    timestamptz
);
CREATE INDEX ON meta.ingest_batch (spec_name, loaded_at DESC);

COMMENT ON COLUMN meta.ingest_batch.digest IS
  'SHA-256 nội dung file. UNIQUE = nạp lại đúng file cũ sẽ bị từ chối.';
```

- [ ] **Step 4: Viết `kome/archive.py`**

```python
# kome/archive.py
import hashlib, shutil
from datetime import date
from pathlib import Path
import psycopg

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def already_loaded(conn: psycopg.Connection, digest: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM meta.ingest_batch WHERE digest = %s AND undone_at IS NULL",
        (digest,),
    ).fetchone()
    return row is not None

def store(conn, path: Path, spec_name: str, digest: str,
          row_count: int, total: int, archive_dir: Path) -> int:
    """Lưu file gốc rồi ghi nhật ký. Lưu file TRƯỚC khi ghi CSDL."""
    folder = Path(archive_dir) / spec_name / date.today().strftime("%Y/%m")
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{path.stem}__{digest[:12]}{path.suffix}"
    shutil.copy2(path, dest)

    row = conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count, total_amount)
           VALUES (%s,%s,%s,%s,%s,%s) RETURNING batch_id""",
        (spec_name, path.name, digest, str(dest), row_count, total),
    ).fetchone()
    conn.commit()
    return row[0]

def previous_stats(conn, spec_name: str) -> dict | None:
    row = conn.execute(
        """SELECT row_count, total_amount FROM meta.ingest_batch
           WHERE spec_name = %s AND undone_at IS NULL
           ORDER BY loaded_at DESC LIMIT 1""",
        (spec_name,),
    ).fetchone()
    return {"row_count": row[0], "total": row[1]} if row else None

def undo(conn, batch_id: int) -> None:
    """Đánh dấu lô đã huỷ. Loader xoá dữ liệu theo batch_id trước khi gọi hàm này."""
    conn.execute(
        "UPDATE meta.ingest_batch SET undone_at = now() WHERE batch_id = %s", (batch_id,)
    )
    conn.commit()
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/test_archive.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add db/migrations/002_ingest_log.sql kome/archive.py tests/test_archive.py
git commit -m "feat: nhật ký nạp, lưu trữ file gốc làm lớp raw, nhận diện file đã nạp"
```

---

## Task 6: Bảng ngày (`dim_date`) với năm tài chính Nhật

**Files:**
- Create: `db/migrations/004_dim_date.sql`, `tests/test_dim_date.py`

**Interfaces:**
- Produces: bảng `core.dim_date (date_key date PK, year, month, day, fiscal_year, fiscal_quarter, iso_week, day_of_week, is_weekend)`

- [ ] **Step 1: Viết test**

```python
# tests/test_dim_date.py
from pathlib import Path
from db.migrate import apply_all

def test_nam_tai_chinh_nhat(conn):
    apply_all(conn, Path("db/migrations"))
    # Tháng 4 trở đi thuộc năm tài chính cùng số; tháng 1-3 thuộc năm trước
    r = conn.execute("SELECT fiscal_year FROM core.dim_date WHERE date_key = '2026-09-16'").fetchone()
    assert r[0] == 2026
    r = conn.execute("SELECT fiscal_year FROM core.dim_date WHERE date_key = '2026-03-31'").fetchone()
    assert r[0] == 2025

def test_phu_du_pham_vi(conn):
    apply_all(conn, Path("db/migrations"))
    r = conn.execute("SELECT min(date_key), max(date_key), count(*) FROM core.dim_date").fetchone()
    assert str(r[0]) == "2024-01-01" and str(r[1]) == "2035-12-31"
    assert r[2] == 4383
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_dim_date.py -v`
Expected: FAIL — `relation "core.dim_date" does not exist`

- [ ] **Step 3: Viết migration**

```sql
-- db/migrations/004_dim_date.sql
CREATE TABLE core.dim_date (
    date_key       date    PRIMARY KEY,
    year           integer NOT NULL,
    month          integer NOT NULL,
    day            integer NOT NULL,
    fiscal_year    integer NOT NULL,
    fiscal_quarter integer NOT NULL,
    iso_week       integer NOT NULL,
    day_of_week    integer NOT NULL,
    is_weekend     boolean NOT NULL
);

COMMENT ON COLUMN core.dim_date.fiscal_year IS
  'Năm tài chính Nhật: bắt đầu 1/4. Tháng 1-3 thuộc năm tài chính trước.';

INSERT INTO core.dim_date
SELECT d::date,
       EXTRACT(year  FROM d)::int,
       EXTRACT(month FROM d)::int,
       EXTRACT(day   FROM d)::int,
       CASE WHEN EXTRACT(month FROM d) >= 4
            THEN EXTRACT(year FROM d)::int
            ELSE EXTRACT(year FROM d)::int - 1 END,
       ((EXTRACT(month FROM d)::int + 8) % 12) / 3 + 1,
       EXTRACT(week FROM d)::int,
       EXTRACT(isodow FROM d)::int,
       EXTRACT(isodow FROM d)::int >= 6
FROM generate_series('2024-01-01'::date, '2035-12-31'::date, '1 day') AS d;
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `pytest tests/test_dim_date.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add db/migrations/004_dim_date.sql tests/test_dim_date.py
git commit -m "feat: dim_date với năm tài chính Nhật (4月-3月)"
```

---

## Task 7: Nạp tồn kho — `dim_warehouse` + `fact_inventory_daily`

Đây là fact đơn giản nhất và **có mốc đối chiếu thật ¥137.839.071**, nên làm trước để kiểm chứng toàn bộ đường ống.

**Files:**
- Create: `db/migrations/005_inventory.sql`, `kome/loaders/__init__.py`, `kome/loaders/inventory.py`, `tests/test_load_inventory.py`

**Interfaces:**
- Consumes: `kome.reader.read`, `kome.config.FileSpec`
- Produces: `kome.loaders.inventory.load(conn, df, snapshot_date, batch_id) -> int` — trả về số dòng đã ghi

- [ ] **Step 1: Viết test**

```python
# tests/test_load_inventory.py
from pathlib import Path
from datetime import date
from db.migrate import apply_all
from kome.config import load_specs
from kome.reader import read
from kome.loaders import inventory

SPECS = load_specs(Path("config/files.yml"))
OK = Path("tests/fixtures/zaiko_ok.xlsx")
D = date(2026, 9, 16)

def _load(conn, batch, n=1):
    df = read(OK, SPECS["zaiko"])
    return inventory.load(conn, df, D, batch(n))   # batch() trả về batch_id thật

def test_khop_moc_doi_chieu(conn, batch):
    assert _load(conn, batch) == 177
    total, rows, whs = conn.execute(
        """SELECT sum(stock_value), count(*), count(DISTINCT warehouse_code)
           FROM core.fact_inventory_daily WHERE snapshot_date = %s""", (D,)
    ).fetchone()
    assert total == 137_839_071
    assert rows == 177
    assert whs == 2

def test_nap_ba_lan_van_the(conn, batch):
    for i in range(3):
        _load(conn, batch, n=i + 1)
    total, rows = conn.execute(
        """SELECT sum(stock_value), count(*) FROM core.fact_inventory_daily
           WHERE snapshot_date = %s""", (D,)
    ).fetchone()
    assert total == 137_839_071 and rows == 177

def test_giu_thap_phan_o_so_luong(conn, batch):
    _load(conn, batch)
    r = conn.execute(
        """SELECT count(*) FROM core.fact_inventory_daily
           WHERE snapshot_date = %s AND stock_qty <> trunc(stock_qty)""", (D,)
    ).fetchone()
    assert r[0] == 20

def test_dim_warehouse_duoc_tao(conn, batch):
    _load(conn, batch)
    rows = conn.execute("SELECT warehouse_code, warehouse_name FROM core.dim_warehouse ORDER BY 1").fetchall()
    assert rows == [("0001", "茨城第１倉庫（出荷専用）"), ("1002", "新・賞味期限用")]
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_load_inventory.py -v`
Expected: FAIL — `relation "core.fact_inventory_daily" does not exist`

- [ ] **Step 3: Viết migration**

```sql
-- db/migrations/005_inventory.sql
CREATE TABLE core.dim_warehouse (
    warehouse_code text PRIMARY KEY,
    warehouse_name text NOT NULL,
    first_seen     date NOT NULL DEFAULT current_date
);

CREATE TABLE core.fact_inventory_daily (
    snapshot_date   date          NOT NULL REFERENCES core.dim_date(date_key),
    product_code    text          NOT NULL,
    warehouse_code  text          NOT NULL REFERENCES core.dim_warehouse(warehouse_code),
    pack_code       text          NOT NULL DEFAULT '',
    product_name    text,
    name_ja         text,
    unit            text,
    best_before     text,                      -- giữ nguyên dạng '2028年06月09日'
    shipped_qty     numeric(14,4) NOT NULL DEFAULT 0,   -- xuất TRONG NGÀY
    stock_qty       numeric(14,4) NOT NULL DEFAULT 0,   -- CÓ phần thập phân
    stock_unit_cost bigint        NOT NULL DEFAULT 0,
    stock_value     bigint        NOT NULL DEFAULT 0,
    batch_id        bigint        NOT NULL REFERENCES meta.ingest_batch(batch_id),
    PRIMARY KEY (snapshot_date, product_code, warehouse_code)
);
CREATE INDEX ON core.fact_inventory_daily (product_code, snapshot_date DESC);
CREATE INDEX ON core.fact_inventory_daily (batch_id);

COMMENT ON TABLE core.fact_inventory_daily IS
  'Độ hạt: 商品コード + 倉庫コード + ngày. Đã kiểm chứng 177 khoá/177 dòng, 0 trùng.';
COMMENT ON COLUMN core.fact_inventory_daily.stock_qty IS
  'NUMERIC vì có phần thập phân thật (83.75 ケース). KHÔNG ép số nguyên.';
```

- [ ] **Step 4: Viết loader**

```python
# kome/loaders/__init__.py
```

```python
# kome/loaders/inventory.py
from datetime import date
import pandas as pd
import psycopg

def load(conn: psycopg.Connection, df: pd.DataFrame,
         snapshot_date: date, batch_id: int) -> int:
    """Ghi snapshot tồn kho. Nạp lại cùng ngày → ghi đè theo khoá."""
    warehouses = df[["warehouse_code", "warehouse_name"]].drop_duplicates()
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO core.dim_warehouse (warehouse_code, warehouse_name)
               VALUES (%s, %s)
               ON CONFLICT (warehouse_code) DO UPDATE SET warehouse_name = EXCLUDED.warehouse_name""",
            warehouses.itertuples(index=False, name=None),
        )
        rows = [
            (snapshot_date, r.product_code, r.warehouse_code, r.pack_code,
             r.product_name, r.name_ja, r.unit, r.best_before,
             r.shipped_qty, r.stock_qty, r.stock_unit_cost, r.stock_value, batch_id)
            for r in df.itertuples(index=False)
        ]
        cur.executemany(
            """INSERT INTO core.fact_inventory_daily
                 (snapshot_date, product_code, warehouse_code, pack_code,
                  product_name, name_ja, unit, best_before,
                  shipped_qty, stock_qty, stock_unit_cost, stock_value, batch_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (snapshot_date, product_code, warehouse_code) DO UPDATE SET
                 pack_code=EXCLUDED.pack_code, product_name=EXCLUDED.product_name,
                 name_ja=EXCLUDED.name_ja, unit=EXCLUDED.unit,
                 best_before=EXCLUDED.best_before, shipped_qty=EXCLUDED.shipped_qty,
                 stock_qty=EXCLUDED.stock_qty, stock_unit_cost=EXCLUDED.stock_unit_cost,
                 stock_value=EXCLUDED.stock_value, batch_id=EXCLUDED.batch_id""",
            rows,
        )
    conn.commit()
    return len(rows)
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/test_load_inventory.py -v`
Expected: 4 passed — **¥137.839.071 khớp**

- [ ] **Step 6: Commit**

```bash
git add db/migrations/005_inventory.sql kome/loaders/ tests/test_load_inventory.py
git commit -m "feat: nạp tồn kho, khớp mốc ¥137.839.071 trên 177 dòng / 2 kho"
```

---

## Task 8: Trang kéo–thả và trang kiểm tra sức khoẻ

**Files:**
- Create: `kome/pipeline.py`, `kome/web/__init__.py`, `kome/web/app.py`, `kome/web/templates/upload.html`, `kome/web/templates/health.html`, `tests/test_pipeline.py`, `tests/test_web.py`

**Interfaces:**
- Consumes: mọi thứ ở Task 3–7
- Produces:
  - `kome.pipeline.ingest(conn, path, archive_dir) -> IngestResult` (dataclass: `ok, spec_name, row_count, total, blockers, warnings, batch_id, skipped`)
  - Route `GET /` và `POST /upload`, `GET /health`, `POST /undo/{batch_id}`

- [ ] **Step 1: Viết test**

```python
# tests/test_pipeline.py
from pathlib import Path
import shutil
from db.migrate import apply_all
from kome.pipeline import ingest

OK = Path("tests/fixtures/zaiko_ok.xlsx")

def _staged(tmp_path):
    dest = tmp_path / "在庫一覧_20260916.xlsx"
    shutil.copy2(OK, dest)
    return dest

def test_nap_thanh_cong(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    r = ingest(conn, _staged(tmp_path), tmp_path / "archive")
    assert r.ok and r.row_count == 177 and r.total == 137_839_071
    assert r.blockers == []

def test_nap_lai_cung_file_bi_bo_qua(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    p = _staged(tmp_path)
    ingest(conn, p, tmp_path / "archive")
    second = ingest(conn, p, tmp_path / "archive")
    assert second.skipped is True

def test_file_cat_cut_bi_chan_va_khong_ghi_gi(conn, tmp_path):
    apply_all(conn, Path("db/migrations"))
    dest = tmp_path / "在庫一覧_20260916.xlsx"
    shutil.copy2("tests/fixtures/zaiko_cat_cut.xlsx", dest)
    r = ingest(conn, dest, tmp_path / "archive")
    assert not r.ok and any(b.gate == 3 for b in r.blockers)
    n = conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0]
    assert n == 0
```

```python
# tests/test_web.py
from pathlib import Path
from fastapi.testclient import TestClient
from db.migrate import apply_all
from kome.web.app import create_app

def test_trang_suc_khoe_mo_duoc(conn, test_db_url):
    apply_all(conn, Path("db/migrations"))
    client = TestClient(create_app(db_url=test_db_url))   # KHÔNG bao giờ để nó tự lấy DATABASE_URL
    r = client.get("/health")
    assert r.status_code == 200
    assert "在庫一覧" in r.text

def test_upload_file_hong_tra_ve_loi_de_hieu(conn, test_db_url):
    apply_all(conn, Path("db/migrations"))
    client = TestClient(create_app(db_url=test_db_url))
    with open("tests/fixtures/zaiko_cat_cut.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 200
    assert "nghi file xuất một phần" in r.text
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_pipeline.py tests/test_web.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kome.pipeline'`

- [ ] **Step 3: Viết `kome/pipeline.py`**

```python
# kome/pipeline.py
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re
from kome import archive, gates
from kome.config import load_specs, FileSpec
from kome.reader import read, ColumnMismatch
from kome.loaders import inventory

SPECS = load_specs(Path("config/files.yml"))
LOADERS = {"zaiko": inventory.load}

@dataclass
class IngestResult:
    ok: bool
    spec_name: str | None = None
    row_count: int = 0
    total: int = 0
    batch_id: int | None = None
    skipped: bool = False
    blockers: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

def identify(path: Path) -> tuple[FileSpec, date] | tuple[None, None]:
    """Cổng 1: nhận ra loại file và ngày dữ liệu từ tên file."""
    for spec in SPECS.values():
        m = re.match(spec.filename_pattern, path.name)
        if m:
            return spec, datetime.strptime(m.group("date"), "%Y%m%d").date()
    return None, None

def ingest(conn, path: Path, archive_dir: Path) -> IngestResult:
    spec, data_date = identify(path)
    if spec is None:
        return IngestResult(ok=False, blockers=[gates.Blocker(1, f"Không nhận ra loại file: {path.name}")])

    digest = archive.sha256_of(path)
    if archive.already_loaded(conn, digest):
        return IngestResult(ok=True, spec_name=spec.name, skipped=True)

    try:
        df = read(path, spec)
    except ColumnMismatch as e:
        return IngestResult(ok=False, spec_name=spec.name, blockers=[gates.Blocker(2, str(e))])

    blockers, warnings = gates.check(path, spec, df, archive.previous_stats(conn, spec.name))
    if blockers:
        return IngestResult(ok=False, spec_name=spec.name, blockers=blockers, warnings=warnings)

    total = int(df[spec.money_columns[-1]].sum()) if spec.money_columns else 0
    batch_id = archive.store(conn, path, spec.name, digest, len(df), total, archive_dir)
    LOADERS[spec.name](conn, df, data_date, batch_id)

    return IngestResult(ok=True, spec_name=spec.name, row_count=len(df),
                        total=total, batch_id=batch_id, warnings=warnings)
```

- [ ] **Step 4: Viết `kome/web/app.py` và hai template**

```python
# kome/web/app.py
import os, shutil, tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from kome.db import connect
from kome.pipeline import ingest, SPECS

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

def create_app(db_url: str | None = None) -> FastAPI:
    """db_url=None => lấy DATABASE_URL. Test LUÔN truyền DATABASE_URL_TEST."""
    app = FastAPI(title="KOME — nạp dữ liệu")
    archive_dir = Path(os.environ.get("ARCHIVE_DIR", "./raw_archive"))
    open_conn = lambda: connect(db_url)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return TEMPLATES.TemplateResponse("upload.html", {"request": request, "results": None})

    @app.post("/upload", response_class=HTMLResponse)
    def upload(request: Request, files: list[UploadFile]):
        results = []
        with open_conn() as conn:
            for f in files:
                with tempfile.TemporaryDirectory() as tmp:
                    staged = Path(tmp) / f.filename
                    with staged.open("wb") as out:
                        shutil.copyfileobj(f.file, out)
                    results.append(ingest(conn, staged, archive_dir))
        return TEMPLATES.TemplateResponse("upload.html", {"request": request, "results": results})

    @app.get("/health", response_class=HTMLResponse)
    def health(request: Request):
        with open_conn() as conn:
            rows = conn.execute(
                """SELECT spec_name, max(loaded_at), max(row_count), max(total_amount)
                   FROM meta.ingest_batch WHERE undone_at IS NULL GROUP BY spec_name"""
            ).fetchall()
        seen = {r[0]: r for r in rows}
        status = [
            {"name": s.display_name,
             "last": seen[k][1] if k in seen else None,
             "rows": seen[k][2] if k in seen else 0,
             "total": seen[k][3] if k in seen else 0}
            for k, s in SPECS.items()
        ]
        return TEMPLATES.TemplateResponse("health.html", {"request": request, "status": status})

    @app.post("/undo/{batch_id}")
    def undo(batch_id: int):
        with open_conn() as conn:
            conn.execute("DELETE FROM core.fact_inventory_daily WHERE batch_id = %s", (batch_id,))
            from kome import archive as A
            A.undo(conn, batch_id)
        return RedirectResponse("/health", status_code=303)

    return app

app = create_app()
```

```html
<!-- kome/web/templates/upload.html -->
<!doctype html><meta charset="utf-8"><title>KOME — nạp dữ liệu</title>
<style>
 body{font:16px/1.6 system-ui;max-width:760px;margin:2rem auto;padding:0 1rem}
 .drop{border:2px dashed #999;border-radius:12px;padding:3rem;text-align:center}
 .ok{color:#0a7} .warn{color:#b70} .err{color:#c00}
 li{margin:.4rem 0}
</style>
<h1>Nạp dữ liệu OBC</h1>
<form method="post" action="/upload" enctype="multipart/form-data">
  <div class="drop">Kéo thả file Excel vào đây<br><input type="file" name="files" multiple required></div>
  <p><button type="submit">Nạp</button> · <a href="/health">Kiểm tra sức khoẻ</a></p>
</form>
{% if results %}<h2>Kết quả</h2><ul>
{% for r in results %}<li>
  {% if r.skipped %}<span class="ok">⏭️ {{ r.spec_name }} — file này đã nạp rồi, bỏ qua</span>
  {% elif r.ok %}<span class="ok">✅ {{ r.spec_name }} — {{ "{:,}".format(r.row_count) }} dòng · ¥{{ "{:,}".format(r.total) }}</span>
  {% else %}<span class="err">❌ {{ r.spec_name or "?" }} — KHÔNG nạp</span>{% endif %}
  {% for b in r.blockers %}<div class="err">Cổng {{ b.gate }}: {{ b.message }}</div>{% endfor %}
  {% for w in r.warnings %}<div class="warn">⚠️ Cổng {{ w.gate }}: {{ w.message }}</div>{% endfor %}
</li>{% endfor %}</ul>{% endif %}
```

```html
<!-- kome/web/templates/health.html -->
<!doctype html><meta charset="utf-8"><title>KOME — sức khoẻ dữ liệu</title>
<style>
 body{font:16px/1.6 system-ui;max-width:760px;margin:2rem auto;padding:0 1rem}
 table{border-collapse:collapse;width:100%} td,th{border-bottom:1px solid #ddd;padding:.5rem;text-align:left}
 .missing{color:#c00;font-weight:600}
</style>
<h1>Sức khoẻ dữ liệu</h1>
<table><tr><th>Loại file</th><th>Nạp lần cuối</th><th>Số dòng</th><th>Tổng tiền</th></tr>
{% for s in status %}<tr>
 <td>{{ s.name }}</td>
 <td>{% if s.last %}{{ s.last.strftime("%Y-%m-%d %H:%M") }}{% else %}<span class="missing">CHƯA CÓ DỮ LIỆU</span>{% endif %}</td>
 <td>{{ "{:,}".format(s.rows) }}</td><td>¥{{ "{:,}".format(s.total) }}</td>
</tr>{% endfor %}</table>
<p><a href="/">← Nạp dữ liệu</a></p>
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/test_pipeline.py tests/test_web.py -v`
Expected: 5 passed

- [ ] **Step 6: Chạy thử thật**

```bash
uvicorn kome.web.app:app --reload --port 8000
```
Mở `http://localhost:8000`, kéo thả `在庫一覧_20260916.xlsx`, xác nhận thấy `✅ zaiko — 177 dòng · ¥137.839.071`.

- [ ] **Step 7: Commit**

```bash
git add kome/pipeline.py kome/web/ tests/test_pipeline.py tests/test_web.py
git commit -m "feat: trang kéo-thả, trang kiểm tra sức khoẻ, hoàn tác lần nạp"
```

---

## Task 9: Nạp `得意先全情報` → `dim_customer` SCD2

> **⚠️ CHẶN:** task này cần file mẫu `得意先全情報` bản **đầy đủ 317 cột** xuất theo mẫu hằng ngày (A1 trong đặc tả). Chưa có file thì không làm được ánh xạ cột.

**Files:**
- Create: `db/migrations/006_dim_customer.sql`, `kome/loaders/customer.py`, `tests/test_load_customer.py`
- Modify: `config/files.yml` (thêm mục `tokuisaki`)

**Interfaces:**
- Produces: `kome.loaders.customer.load(conn, df, snapshot_date, batch_id) -> dict` — trả về `{"inserted": n, "closed": n, "unchanged": n}`

**Tập cột so sánh để quyết định tạo phiên bản mới** — chỉ những cột này, không so toàn bộ 317 cột:

```
customer_name · branch_name · rank_code · category_code · order_app_code
salesperson_code · price_level_code · closing_day_code · billing_customer_code
postcode · prefecture · city · address · phone · invoice_reg_no · spot_flag
```

- [ ] **Step 1: Viết test**

```python
# tests/test_load_customer.py
from pathlib import Path
from datetime import date
import pandas as pd
from db.migrate import apply_all
from kome.loaders import customer

def _df(rank="0003"):
    return pd.DataFrame([{
        "customer_code": "000000009292", "customer_name": "株式会社ASIANEX",
        "branch_name": "あじさい支店", "rank_code": rank, "category_code": "0202",
        "order_app_code": "0001", "salesperson_code": "0105", "price_level_code": "10",
        "closing_day_code": "99", "billing_customer_code": "000000009292",
        "postcode": "3720855", "prefecture": "群馬県", "city": "伊勢崎市",
        "address": "長沼町 615-4", "phone": "0270-75-6396",
        "invoice_reg_no": "", "spot_flag": "0",
    }])

def test_lan_dau_tao_mot_phien_ban(conn):
    apply_all(conn, Path("db/migrations"))
    r = customer.load(conn, _df(), date(2026, 9, 16), 1)
    assert r["inserted"] == 1
    n = conn.execute("SELECT count(*) FROM core.dim_customer WHERE is_current").fetchone()[0]
    assert n == 1

def test_khong_doi_gi_thi_khong_tao_phien_ban_moi(conn):
    apply_all(conn, Path("db/migrations"))
    customer.load(conn, _df(), date(2026, 9, 16), 1)
    r = customer.load(conn, _df(), date(2026, 9, 17), 2)
    assert r["inserted"] == 0 and r["unchanged"] == 1
    n = conn.execute("SELECT count(*) FROM core.dim_customer").fetchone()[0]
    assert n == 1

def test_doi_hang_thi_tao_phien_ban_moi_va_dong_cai_cu(conn):
    apply_all(conn, Path("db/migrations"))
    customer.load(conn, _df(rank="0003"), date(2026, 9, 16), 1)
    r = customer.load(conn, _df(rank="0001"), date(2026, 9, 17), 2)
    assert r["inserted"] == 1 and r["closed"] == 1
    rows = conn.execute(
        """SELECT rank_code, valid_from, valid_to, is_current FROM core.dim_customer
           WHERE customer_code = '000000009292' ORDER BY valid_from"""
    ).fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "0003" and str(rows[0][2]) == "2026-09-16" and rows[0][3] is False
    assert rows[1][0] == "0001" and rows[1][3] is True

def test_khong_bao_gio_xoa_dong(conn):
    apply_all(conn, Path("db/migrations"))
    customer.load(conn, _df(rank="0003"), date(2026, 9, 16), 1)
    customer.load(conn, _df(rank="0001"), date(2026, 9, 17), 2)
    customer.load(conn, _df(rank="0002"), date(2026, 9, 18), 3)
    n = conn.execute("SELECT count(*) FROM core.dim_customer").fetchone()[0]
    assert n == 3   # luật bất biến #6
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_load_customer.py -v`
Expected: FAIL — `relation "core.dim_customer" does not exist`

- [ ] **Step 3: Viết migration**

```sql
-- db/migrations/006_dim_customer.sql
CREATE TABLE core.dim_customer (
    customer_sk           bigserial PRIMARY KEY,
    customer_code         text NOT NULL,
    valid_from            date NOT NULL,
    valid_to              date,
    is_current            boolean NOT NULL DEFAULT true,
    customer_name         text,
    branch_name           text,
    rank_code             text,
    category_code         text,
    order_app_code        text,
    salesperson_code      text,
    price_level_code      text,
    closing_day_code      text,
    billing_customer_code text,
    postcode              text,
    prefecture            text,
    city                  text,
    address               text,
    phone                 text,
    invoice_reg_no        text,
    spot_flag             text,
    batch_id              bigint NOT NULL REFERENCES meta.ingest_batch(batch_id)
);
CREATE UNIQUE INDEX ON core.dim_customer (customer_code) WHERE is_current;
CREATE INDEX ON core.dim_customer (customer_code, valid_from);

COMMENT ON TABLE core.dim_customer IS
  'SCD2. KHÔNG BAO GIỜ XOÁ DÒNG — chỉ đóng valid_to và đặt is_current=false.';
```

- [ ] **Step 4: Viết loader**

```python
# kome/loaders/customer.py
from datetime import date, timedelta
import pandas as pd
import psycopg

TRACKED = [
    "customer_name", "branch_name", "rank_code", "category_code", "order_app_code",
    "salesperson_code", "price_level_code", "closing_day_code", "billing_customer_code",
    "postcode", "prefecture", "city", "address", "phone", "invoice_reg_no", "spot_flag",
]

def load(conn: psycopg.Connection, df: pd.DataFrame,
         snapshot_date: date, batch_id: int) -> dict:
    """SCD2. Chỉ tạo phiên bản mới khi một trong TRACKED thay đổi.

    Bản xuất một phần chỉ chứa vài khách KHÔNG được hiểu là các khách
    khác đã biến mất — hàm này chỉ upsert, không bao giờ đóng dòng của
    khách vắng mặt trong file.
    """
    current = {
        r[0]: r[1:] for r in conn.execute(
            f"SELECT customer_code, {', '.join(TRACKED)} FROM core.dim_customer WHERE is_current"
        ).fetchall()
    }
    inserted = closed = unchanged = 0
    with conn.cursor() as cur:
        for row in df.itertuples(index=False):
            code = row.customer_code
            new = tuple(getattr(row, c) for c in TRACKED)
            old = current.get(code)
            if old is not None and old == new:
                unchanged += 1
                continue
            if old is not None:
                cur.execute(
                    """UPDATE core.dim_customer SET valid_to = %s, is_current = false
                       WHERE customer_code = %s AND is_current""",
                    (snapshot_date - timedelta(days=1), code),
                )
                closed += 1
            cur.execute(
                f"""INSERT INTO core.dim_customer
                      (customer_code, valid_from, is_current, {', '.join(TRACKED)}, batch_id)
                    VALUES (%s, %s, true, {', '.join(['%s'] * len(TRACKED))}, %s)""",
                (code, snapshot_date, *new, batch_id),
            )
            inserted += 1
    conn.commit()
    return {"inserted": inserted, "closed": closed, "unchanged": unchanged}
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/test_load_customer.py -v`
Expected: 4 passed

- [ ] **Step 6: Bổ sung `config/files.yml`**

Thêm mục `tokuisaki` với `header_row: 1`, `min_rows: 1000`, `keys: [customer_code]`, và ánh xạ cột lấy từ file mẫu thật (317 cột → chỉ giữ ~20 cột ở `TRACKED` cộng `customer_code`). Đăng ký loader vào `kome.pipeline.LOADERS`.

- [ ] **Step 7: Nạp thử file thật và kiểm tra**

Run: nạp `得意先全情報` bản đầy đủ qua trang web.
Expected: ~2.080 dòng; chạy lại cùng file → `skipped`; nạp bản tháng sau → chỉ vài chục dòng `inserted`.

- [ ] **Step 8: Commit**

```bash
git add db/migrations/006_dim_customer.sql kome/loaders/customer.py tests/test_load_customer.py config/files.yml
git commit -m "feat: dim_customer SCD2, giữ lịch sử đổi hạng và đổi người phụ trách"
```

---

## Task 10: Nạp `売上伝票データ` → `fact_sales_line`

> **⚠️ CHẶN:** cần file mẫu `売上伝票データ` xuất theo mẫu hằng ngày (A1).

**Files:**
- Create: `db/migrations/007_fact_sales.sql`, `kome/loaders/sales.py`, `tests/test_load_sales.py`
- Modify: `config/files.yml`, `kome/pipeline.py`

**Interfaces:**
- Produces: `kome.loaders.sales.load(conn, df, data_date, batch_id) -> int`

**Khoảng 40 cột giữ lại** (từ 271): `伝票No.` · số thứ tự dòng · `売上日付` · `請求日付` · `伝票区分` · `得意先コード` · `請求先コード` · `担当者コード` · `部門コード` · `直送先コード` · `商品コード` · `荷姿コード` · `入数` · `数量` · `単価` · `単位原価` · `金額` · `消費税額` · `原価` · `粗利益` · `粗利益率` · `消費税率` · `入金額１` · `入金伝票No.１` · `請求締日コード`

- [ ] **Step 1: Viết test**

```python
# tests/test_load_sales.py
from pathlib import Path
from datetime import date
import pandas as pd
from db.migrate import apply_all
from kome.loaders import sales

def _line(slip="079934", seq=1, amount=29167, profit=9907, qty=6):
    return {
        "slip_no": slip, "line_seq": seq, "sales_date": date(2026, 5, 1),
        "slip_type": "債権計上", "customer_code": "000000009292",
        "billing_customer_code": "000000009292", "salesperson_code": "0004",
        "product_code": "XT07", "pack_code": "02", "qty": qty, "unit_price": 5250,
        "unit_cost": 3210, "amount": amount, "tax_amount": 2333, "cost": 19260,
        "gross_profit": profit, "gross_margin": 0.3397, "batch_id": 1,
    }

def test_nap_va_cong_dung(conn):
    apply_all(conn, Path("db/migrations"))
    df = pd.DataFrame([_line(seq=1), _line(seq=2, amount=37778, profit=14498)])
    assert sales.load(conn, df, date(2026, 5, 1), 1) == 2
    r = conn.execute("SELECT sum(amount), sum(gross_profit) FROM core.fact_sales_line").fetchone()
    assert r[0] == 66_945 and r[1] == 24_405

def test_phieu_do_so_am_duoc_giu_nguyen(conn):
    apply_all(conn, Path("db/migrations"))
    df = pd.DataFrame([_line(seq=1), _line(seq=2, amount=-29167, profit=-9907, qty=-6)])
    sales.load(conn, df, date(2026, 5, 1), 1)
    total = conn.execute("SELECT sum(amount) FROM core.fact_sales_line").fetchone()[0]
    assert total == 0          # bán rồi trả lại = 0, KHÔNG lọc bỏ dòng âm
    n = conn.execute("SELECT count(*) FROM core.fact_sales_line").fetchone()[0]
    assert n == 2

def test_nap_ba_lan_van_the(conn):
    apply_all(conn, Path("db/migrations"))
    df = pd.DataFrame([_line()])
    for i in range(3):
        sales.load(conn, df, date(2026, 5, 1), 1)
    r = conn.execute("SELECT count(*), sum(amount) FROM core.fact_sales_line").fetchone()
    assert r[0] == 1 and r[1] == 29_167

def test_doi_soat_thang_ghi_de_phieu_da_sua(conn):
    apply_all(conn, Path("db/migrations"))
    sales.load(conn, pd.DataFrame([_line(amount=29167)]), date(2026, 5, 1), 1)
    sales.load(conn, pd.DataFrame([_line(amount=25000)]), date(2026, 5, 1), 2)
    r = conn.execute("SELECT sum(amount), count(*) FROM core.fact_sales_line").fetchone()
    assert r[0] == 25_000 and r[1] == 1
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_load_sales.py -v`
Expected: FAIL — `relation "core.fact_sales_line" does not exist`

- [ ] **Step 3: Viết migration**

```sql
-- db/migrations/007_fact_sales.sql
CREATE TABLE core.fact_sales_line (
    slip_no               text          NOT NULL,
    line_seq              integer       NOT NULL,
    sales_date            date          NOT NULL REFERENCES core.dim_date(date_key),
    billing_date          date,
    slip_type             text,
    customer_code         text          NOT NULL,
    billing_customer_code text,
    salesperson_code      text,
    department_code       text,
    shipto_code           text,
    product_code          text          NOT NULL,
    pack_code             text          NOT NULL DEFAULT '',
    case_qty              numeric(14,4) NOT NULL DEFAULT 0,
    qty                   numeric(14,4) NOT NULL DEFAULT 0,
    unit_price            bigint        NOT NULL DEFAULT 0,
    unit_cost             bigint        NOT NULL DEFAULT 0,
    amount                bigint        NOT NULL DEFAULT 0,
    tax_amount            bigint        NOT NULL DEFAULT 0,
    cost                  bigint        NOT NULL DEFAULT 0,
    gross_profit          bigint        NOT NULL DEFAULT 0,
    gross_margin          numeric(6,4),
    tax_rate              numeric(6,4),
    paid_amount           bigint        NOT NULL DEFAULT 0,
    payment_slip_no       text,
    closing_day_code      text,
    batch_id              bigint        NOT NULL REFERENCES meta.ingest_batch(batch_id),
    PRIMARY KEY (slip_no, line_seq)
);
CREATE INDEX ON core.fact_sales_line (sales_date);
CREATE INDEX ON core.fact_sales_line (customer_code, sales_date DESC);
CREATE INDEX ON core.fact_sales_line (product_code, sales_date DESC);
CREATE INDEX ON core.fact_sales_line (batch_id);

COMMENT ON TABLE core.fact_sales_line IS
  'Độ hạt: 伝票No. + số thứ tự dòng. 赤伝 (hàng trả) giữ nguyên số ÂM, không lọc bỏ.';
```

- [ ] **Step 4: Viết loader**

```python
# kome/loaders/sales.py
from datetime import date
import pandas as pd
import psycopg

COLUMNS = [
    "slip_no", "line_seq", "sales_date", "billing_date", "slip_type",
    "customer_code", "billing_customer_code", "salesperson_code", "department_code",
    "shipto_code", "product_code", "pack_code", "case_qty", "qty", "unit_price",
    "unit_cost", "amount", "tax_amount", "cost", "gross_profit", "gross_margin",
    "tax_rate", "paid_amount", "payment_slip_no", "closing_day_code", "batch_id",
]
_UPDATE = ", ".join(f"{c}=EXCLUDED.{c}" for c in COLUMNS if c not in ("slip_no", "line_seq"))

def load(conn: psycopg.Connection, df: pd.DataFrame,
         data_date: date, batch_id: int) -> int:
    """Upsert theo 伝票No. + số dòng.

    Nhờ khoá này mà đối soát tháng hoạt động: nạp lại cả tháng thì phiếu
    đã sửa trong OBC được ghi đè, phiếu không đổi thì ghi lại y nguyên.
    """
    df = df.copy()
    df["batch_id"] = batch_id
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = None
    rows = list(df[COLUMNS].itertuples(index=False, name=None))
    with conn.cursor() as cur:
        cur.executemany(
            f"""INSERT INTO core.fact_sales_line ({', '.join(COLUMNS)})
                VALUES ({', '.join(['%s'] * len(COLUMNS))})
                ON CONFLICT (slip_no, line_seq) DO UPDATE SET {_UPDATE}""",
            rows,
        )
    conn.commit()
    return len(rows)
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/test_load_sales.py -v`
Expected: 4 passed

- [ ] **Step 6: Nạp toàn bộ lịch sử và kiểm tra mốc**

Nạp 6 file `売上伝票データ` theo quý từ thư mục backup (bỏ qua thư mục `VOID`), rồi:

```sql
SELECT sum(amount) AS doanh_thu, sum(gross_profit) AS lai_gop, count(*) AS so_dong
FROM core.fact_sales_line
WHERE sales_date BETWEEN '2026-05-01' AND '2026-07-31';
```

Expected: `doanh_thu = 390126850`, `lai_gop = 114315334`

> Nếu lệch: kiểm tra đã lọc nhầm `赤伝` chưa, và `伝票区分` nào được tính vào doanh thu. **Không sửa số cho khớp** — tìm đúng nguyên nhân.

- [ ] **Step 7: Commit**

```bash
git add db/migrations/007_fact_sales.sql kome/loaders/sales.py tests/test_load_sales.py config/files.yml kome/pipeline.py
git commit -m "feat: nạp fact_sales_line, khớp mốc quý ¥390.126.850 / lãi gộp ¥114.315.334"
```

---

## Task 11: Master data còn lại (loader chung theo cấu hình)

**Files:**
- Create: `db/migrations/008_masters.sql`, `kome/loaders/master.py`, `tests/test_load_master.py`
- Modify: `config/files.yml` (thêm `shohin`, `shiiresaki`, `chokusousaki`, `tanka`)

**Interfaces:**
- Produces: `kome.loaders.master.make_loader(table: str, keys: list[str], columns: list[str]) -> Callable`

Bốn file master (`商品データ`, `仕入先`, `直送先`, `取引単価データ`) đều là upsert đơn giản theo khoá, **không cần lịch sử**. Viết **một** loader chung điều khiển bằng YAML thay vì bốn loader gần giống nhau — ít code hơn, ít chỗ hỏng hơn, và AI sửa dễ hơn.

- [ ] **Step 1: Viết test**

```python
# tests/test_load_master.py
from pathlib import Path
import pandas as pd
from datetime import date
from db.migrate import apply_all
from kome.loaders.master import make_loader

def test_upsert_theo_khoa(conn):
    apply_all(conn, Path("db/migrations"))
    load = make_loader("core.dim_supplier", ["supplier_code"], ["supplier_code", "supplier_name"])
    df = pd.DataFrame([{"supplier_code": "0001", "supplier_name": "BICH CHI FOOD COMPANY"}])
    assert load(conn, df, date(2026, 9, 16), 1) == 1
    df2 = pd.DataFrame([{"supplier_code": "0001", "supplier_name": "BICH CHI FOOD CO., LTD"}])
    load(conn, df2, date(2026, 9, 17), 2)
    rows = conn.execute("SELECT supplier_code, supplier_name FROM core.dim_supplier").fetchall()
    assert rows == [("0001", "BICH CHI FOOD CO., LTD")]

def test_ma_giu_so_khong_dau(conn):
    apply_all(conn, Path("db/migrations"))
    load = make_loader("core.dim_supplier", ["supplier_code"], ["supplier_code", "supplier_name"])
    load(conn, pd.DataFrame([{"supplier_code": "0001", "supplier_name": "X"}]), date(2026, 9, 16), 1)
    r = conn.execute("SELECT supplier_code FROM core.dim_supplier").fetchone()
    assert r[0] == "0001"
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_load_master.py -v`
Expected: FAIL — `relation "core.dim_supplier" does not exist`

- [ ] **Step 3: Viết migration `008_masters.sql`**

```sql
-- db/migrations/008_masters.sql
CREATE TABLE core.dim_supplier (
    supplier_code text PRIMARY KEY,
    supplier_name text,
    batch_id      bigint NOT NULL REFERENCES meta.ingest_batch(batch_id)
);

CREATE TABLE core.dim_product (
    product_code    text PRIMARY KEY,
    product_name    text,
    name_ja         text,
    kind_code       text,
    kind_name       text,
    food_category_code text,
    food_category_name text,
    rank_code       text,
    rank_name       text,
    compete_code    text,
    barcode         text,
    unit            text,
    case_qty        numeric(14,4) NOT NULL DEFAULT 0,
    shelf_code      text,
    introduced_on   text,
    batch_id        bigint NOT NULL REFERENCES meta.ingest_batch(batch_id)
);

CREATE TABLE core.dim_shipto (
    shipto_code   text PRIMARY KEY,
    shipto_name   text,
    customer_code text,            -- CÓ THỂ RỖNG: điểm giao không thuộc khách nào
    postcode      text,
    prefecture    text,
    city          text,
    address       text,
    phone         text,
    lead_time_code text,
    batch_id      bigint NOT NULL REFERENCES meta.ingest_batch(batch_id)
);
CREATE INDEX ON core.dim_shipto (customer_code);

CREATE TABLE core.fact_price_list (
    product_code text   NOT NULL,
    pack_code    text   NOT NULL,
    price_level  text   NOT NULL,      -- '01'..'10' ứng với 売価No.1..10
    valid_from   date   NOT NULL,
    price_ex_tax bigint NOT NULL DEFAULT 0,
    price_in_tax bigint NOT NULL DEFAULT 0,
    unit_cost    bigint NOT NULL DEFAULT 0,
    batch_id     bigint NOT NULL REFERENCES meta.ingest_batch(batch_id),
    PRIMARY KEY (product_code, pack_code, price_level, valid_from)
);

COMMENT ON TABLE core.fact_price_list IS
  'Giữ lịch sử giá. Ghép với dim_customer.price_level_code để ra giá đáng lẽ
   phải bán, so với fact_sales_line.unit_price để phát hiện bán dưới giá.
   Xem docs/data-linkage.md §3.4.';
COMMENT ON COLUMN core.dim_shipto.customer_code IS
  'Cho phép RỖNG — đã thấy 直送先 không gắn khách nào trong dữ liệu thật.';
```

- [ ] **Step 4: Viết `kome/loaders/master.py`**

```python
# kome/loaders/master.py
from datetime import date
from typing import Callable
import pandas as pd
import psycopg

def make_loader(table: str, keys: list[str], columns: list[str]) -> Callable:
    """Sinh loader upsert cho một bảng master. Không giữ lịch sử."""
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in columns if c not in keys)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}, batch_id) "
        f"VALUES ({', '.join(['%s'] * (len(columns) + 1))}) "
        f"ON CONFLICT ({', '.join(keys)}) DO UPDATE SET {updates}, batch_id=EXCLUDED.batch_id"
    )

    def load(conn: psycopg.Connection, df: pd.DataFrame,
             data_date: date, batch_id: int) -> int:
        rows = [tuple(getattr(r, c) for c in columns) + (batch_id,)
                for r in df.itertuples(index=False)]
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()
        return len(rows)

    return load
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/test_load_master.py -v`
Expected: 2 passed

- [ ] **Step 6: Đăng ký 4 loader vào `kome/pipeline.py` và nạp thử file thật**

Expected: `商品データ` 232 dòng · `仕入先` 50 · `直送先` 1.833 · `取引単価データ` 396

- [ ] **Step 7: Commit**

```bash
git add db/migrations/008_masters.sql kome/loaders/master.py tests/test_load_master.py config/files.yml kome/pipeline.py
git commit -m "feat: loader chung cho master data điều khiển bằng YAML"
```

---

## Task 12: Sao lưu hằng đêm và thử khôi phục

**Files:**
- Create: `ops/backup.py`, `ops/restore_check.py`, `docs/runbook.md`, `tests/test_backup.py`

**Interfaces:**
- Produces:
  - `ops.backup.dump(database_url, out_dir) -> Path`
  - `ops.backup.prune(out_dir, keep_daily=30, keep_monthly=12) -> list[Path]`
  - `ops.restore_check.verify(dump_path, scratch_url) -> dict`

Gói Supabase Free **không có sao lưu tự động** → phần này không phải tuỳ chọn.

- [ ] **Step 1: Viết test**

```python
# tests/test_backup.py
from pathlib import Path
from datetime import date, timedelta
from ops.backup import prune

def _touch(d: Path, day: date):
    p = d / f"kome_{day:%Y%m%d}.sql.gz"
    p.write_bytes(b"x")
    return p

def test_giu_30_ban_ngay_va_12_ban_thang(tmp_path):
    today = date(2026, 9, 16)
    for i in range(400):
        _touch(tmp_path, today - timedelta(days=i))
    kept = prune(tmp_path, keep_daily=30, keep_monthly=12)
    assert len(kept) <= 42
    assert (tmp_path / f"kome_{today:%Y%m%d}.sql.gz") in kept
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_backup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ops'`

- [ ] **Step 3: Viết `ops/backup.py`**

```python
# ops/backup.py
import gzip, shutil, subprocess
from datetime import date
from pathlib import Path

def dump(database_url: str, out_dir: Path) -> Path:
    """pg_dump nén gzip. Trả về đường dẫn file vừa tạo."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / f"kome_{date.today():%Y%m%d}.sql"
    subprocess.run(["pg_dump", "--no-owner", "--file", str(raw), database_url], check=True)
    gz = raw.with_suffix(".sql.gz")
    with raw.open("rb") as fi, gzip.open(gz, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    raw.unlink()
    return gz

def prune(out_dir: Path, keep_daily: int = 30, keep_monthly: int = 12) -> list[Path]:
    """Giữ N bản gần nhất theo ngày + bản đầu mỗi tháng trong M tháng. Xoá phần còn lại."""
    files = sorted(Path(out_dir).glob("kome_*.sql.gz"), reverse=True)
    keep = set(files[:keep_daily])
    seen_months: dict[str, Path] = {}
    for f in files:
        ym = f.stem[5:11]
        seen_months.setdefault(ym, f)
    for ym in sorted(seen_months, reverse=True)[:keep_monthly]:
        keep.add(seen_months[ym])
    for f in files:
        if f not in keep:
            f.unlink()
    return sorted(keep)
```

- [ ] **Step 4: Viết `ops/restore_check.py`**

```python
# ops/restore_check.py
import gzip, subprocess, tempfile
from pathlib import Path
import psycopg

def verify(dump_path: Path, scratch_url: str) -> dict:
    """Khôi phục bản sao lưu vào CSDL nháp rồi đếm dòng. Chạy mỗi quý.

    Một bản sao lưu chưa từng được thử khôi phục thì không phải bản sao lưu.
    """
    with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tmp:
        with gzip.open(dump_path, "rb") as fi:
            tmp.write(fi.read())
        sql_path = Path(tmp.name)
    subprocess.run(["psql", "--quiet", "--file", str(sql_path), scratch_url], check=True)
    sql_path.unlink()
    with psycopg.connect(scratch_url) as conn:
        return {
            "sales_lines": conn.execute("SELECT count(*) FROM core.fact_sales_line").fetchone()[0],
            "customers":   conn.execute("SELECT count(*) FROM core.dim_customer WHERE is_current").fetchone()[0],
            "inventory":   conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0],
        }
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `pytest tests/test_backup.py -v`
Expected: 1 passed

- [ ] **Step 6: Chạy thử khôi phục thật một lần**

```bash
python -c "from ops.backup import dump; import os,pathlib; print(dump(os.environ['DATABASE_URL'], pathlib.Path('backups')))"
python -c "from ops.restore_check import verify; import os,pathlib,sys; print(verify(sorted(pathlib.Path('backups').glob('*.gz'))[-1], os.environ['DATABASE_URL_TEST']))"
```

Expected: số dòng khớp với CSDL thật. **Đây là tiêu chí hoàn thành bắt buộc của Giai đoạn 0.**

- [ ] **Step 7: Viết `docs/runbook.md`**

Một bảng, mỗi dòng một sự cố, mỗi ô là lệnh cụ thể chép–dán được: nạp nhầm file · OBC đổi tên cột · số không khớp OBC · CSDL đầy 500 MB · mất sạch CSDL · web app không truy cập được. Nội dung lấy từ §9.6 của đặc tả.

- [ ] **Step 8: Commit**

```bash
git add ops/ docs/runbook.md tests/test_backup.py
git commit -m "feat: sao lưu hằng đêm, dọn bản cũ, và kiểm tra khôi phục thật"
```

---

## Task 13: Phân quyền bốn tài khoản CSDL

Yêu cầu §9.7 của đặc tả. Làm **cuối cùng** vì cần biết đủ tên bảng.

**Files:**
- Create: `db/migrations/009_roles.sql`, `tests/test_roles.py`

**Interfaces:**
- Produces: 4 vai trò `kome_ingest`, `kome_app`, `kome_report`, và quyền tương ứng

- [ ] **Step 1: Viết test**

```python
# tests/test_roles.py
from pathlib import Path
from db.migrate import apply_all

def test_report_chi_duoc_doc(conn):
    apply_all(conn, Path("db/migrations"))
    r = conn.execute(
        """SELECT has_table_privilege('kome_report', 'core.fact_sales_line', 'SELECT'),
                  has_table_privilege('kome_report', 'core.fact_sales_line', 'INSERT')"""
    ).fetchone()
    assert r[0] is True and r[1] is False

def test_app_khong_duoc_ghi_vao_core(conn):
    apply_all(conn, Path("db/migrations"))
    r = conn.execute(
        """SELECT has_table_privilege('kome_app', 'core.fact_sales_line', 'SELECT'),
                  has_table_privilege('kome_app', 'core.fact_sales_line', 'UPDATE')"""
    ).fetchone()
    assert r[0] is True and r[1] is False   # luật bất biến #1
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `pytest tests/test_roles.py -v`
Expected: FAIL — `role "kome_report" does not exist`

- [ ] **Step 3: Viết migration**

```sql
-- db/migrations/009_roles.sql
-- Vai trò KHÔNG có mật khẩu ở đây. Mật khẩu đặt riêng bằng ALTER ROLE
-- trên bảng điều khiển Supabase, không bao giờ nằm trong git (luật #8).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kome_ingest') THEN
        CREATE ROLE kome_ingest NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kome_app') THEN
        CREATE ROLE kome_app NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kome_report') THEN
        CREATE ROLE kome_report NOLOGIN;
    END IF;
END $$;

GRANT USAGE ON SCHEMA core, mart, meta TO kome_ingest, kome_app, kome_report;
GRANT USAGE ON SCHEMA app TO kome_app;

-- ingest: ghi được vào core và meta
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA core, meta TO kome_ingest;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA core, meta TO kome_ingest;

-- app: ĐỌC core (luật #1 — không bao giờ sửa dữ liệu OBC), đọc-ghi app
GRANT SELECT ON ALL TABLES IN SCHEMA core, mart TO kome_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO kome_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO kome_app;

-- report: chỉ đọc, mọi nơi
GRANT SELECT ON ALL TABLES IN SCHEMA core, mart, app TO kome_report;

-- Bảng tạo về sau cũng tự nhận quyền này
ALTER DEFAULT PRIVILEGES IN SCHEMA core, meta GRANT SELECT, INSERT, UPDATE ON TABLES TO kome_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA core, mart GRANT SELECT ON TABLES TO kome_app, kome_report;
ALTER DEFAULT PRIVILEGES IN SCHEMA app  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kome_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app  GRANT SELECT ON TABLES TO kome_report;
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `pytest tests/test_roles.py -v`
Expected: 2 passed

- [ ] **Step 5: Tạo tài khoản đăng nhập thật**

Trên Supabase SQL Editor — **chạy tay, không đưa vào git**:

```sql
CREATE USER kome_ingest_user LOGIN PASSWORD '<mật khẩu mạnh>' IN ROLE kome_ingest;
CREATE USER kome_app_user    LOGIN PASSWORD '<mật khẩu mạnh>' IN ROLE kome_app;
CREATE USER kome_report_user LOGIN PASSWORD '<mật khẩu mạnh>' IN ROLE kome_report;
```

Rồi đổi `DATABASE_URL` trong `.env` sang `kome_ingest_user`. Tài khoản `postgres` chỉ dùng khi chạy migration.

- [ ] **Step 6: Commit**

```bash
git add db/migrations/009_roles.sql tests/test_roles.py
git commit -m "feat: phân quyền 4 tài khoản CSDL, app không ghi được vào core"
```

---

## Tiêu chí hoàn thành Giai đoạn 0

Chạy `pytest -v` — toàn bộ phải xanh. Ngoài ra:

- [ ] Nạp 1 ngày dữ liệu thật từ 3 file, ra đúng số liệu
- [ ] Nạp lại cùng file 3 lần → kết quả không đổi
- [ ] File hỏng thật (`得意先全情報` bản 201 dòng, bản 5 cột) bị cổng kiểm tra **chặn**
- [ ] Nạp lại được toàn bộ lịch sử từ 2025-02 đến nay
- [ ] Tổng tồn kho 2026-09-16 = **¥137.839.071** / 177 dòng / 2 kho
- [ ] Quý 2026-05→07: **53.942 dòng** sau khử trùng, `sum(gross_profit)` = **¥114.315.334**, `sum(amount - tax_amount)` = **¥390.130.067**
- [ ] Trang sức khoẻ hiển thị đúng kỳ dữ liệu và cảnh báo khi thiếu ngày
- [ ] Sao lưu chạy được và **đã thử khôi phục thành công một lần**

---

## Ngoài phạm vi kế hoạch này

Thuộc **Giai đoạn 1**, sẽ có kế hoạch riêng sau khi Giai đoạn 0 chạy ổn định:

- Đồng bộ ngược master data ra 2 Google Sheet
- Lớp `mart` và hai báo cáo ① Tổng quan · ② Khách rời bỏ (có nút hành động)
- `fact_payment` từ `入金伝票データ` (đang thiếu dữ liệu lịch sử, cần xuất bổ sung)
- Lập chỉ mục 5.589 file PDF hoá đơn
