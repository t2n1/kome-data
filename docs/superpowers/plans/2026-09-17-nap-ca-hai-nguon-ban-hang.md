# Nạp bán hàng từ cả 2 nguồn OBC (売上伝票データ + 売上明細表) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho `core.fact_sales_line` nhận dữ liệu từ **売上明細表** (meisai) như một nguồn **dự phòng**, dùng khi không xuất được **売上伝票データ** (uriage) — nguồn chính hiện tại vẫn giữ nguyên vai trò.

**Architecture:** `売上明細表` thiếu `明細行番号` (khoá dòng) nên `reader.read()` tự sinh `line_seq` bằng số thứ tự xuất hiện trong file theo từng `伝票No.` (cờ `synthesize_line_seq` mới trong `FileSpec`). Cả hai nguồn ghi vào CÙNG bảng `core.fact_sales_line`, phân biệt bằng cột `source` mới (`'uriage'` | `'meisai'`), khoá chính đổi thành `(slip_no, line_seq, source)` để không đụng nhau. `pipeline.ingest()` CHẶN nạp một nguồn cho ngày đã có dữ liệu từ nguồn kia — không cộng dồn doanh thu âm thầm. Không đổi bất kỳ view nào trong `mart/` — đó là việc của lúc THẬT SỰ cần chuyển hẳn sang `meisai` (xem "Việc cố tình để lại" cuối plan).

**Tech Stack:** Python, pandas, psycopg3, PostgreSQL (Supabase), pytest.

**Spec:** Không có tài liệu spec riêng — yêu cầu chốt qua hội thoại trong phiên làm việc 2026-09-17 (mục đích: dự phòng khi tương lai không lấy được `売上伝票データ`), có đối chiếu số liệu thật giữa hai file (cùng ngày 2026-08-03) đã lưu ở [docs/cot-day-du-ban-hang.md](../../cot-day-du-ban-hang.md).

## Global Constraints

- Không sửa file trong `db/migrations/` đã chạy rồi — chỉ thêm file mới (`CLAUDE.md`).
- Mọi migration chạy bằng vai trò `postgres` (`db/migrate.py` đã làm việc này) — không đổi.
- Mã (`*コード`) luôn là TEXT, giữ số 0 đầu.
- `赤伝` (số âm) không được lọc bỏ.
- Loader mới BẮT BUỘC có mục trong `UNDO_TABLES` (test lưới an toàn `test_moi_loader_deu_khai_bao_bang_can_don` đã có sẵn, không cần viết thêm).
- pytest chạy bằng `pytest -v`, dùng CSDL thử nghiệm (`DATABASE_URL_TEST`), không bao giờ chạm CSDL thật.

---

## Task 1: Migration — thêm cột `source` và đổi khoá chính `core.fact_sales_line`

**Files:**
- Create: `db/migrations/017_nguon_ban_hang_thay_the.sql`
- Test: `tests/test_migrate.py` (chạy lại toàn bộ bộ migration, không viết test mới — test đã có tự động áp toàn bộ `db/migrations/` từ đầu)

**Interfaces:**
- Produces: cột `core.fact_sales_line.source text NOT NULL DEFAULT 'uriage'`; khoá chính `(slip_no, line_seq, source)`; index `(source, sales_date)`.

- [ ] **Step 1: Viết file migration**

```sql
-- db/migrations/017_nguon_ban_hang_thay_the.sql
-- Cho core.fact_sales_line nhận dữ liệu từ HAI loại file OBC: 売上伝票データ
-- (uriage, đã có từ đầu) và 売上明細表 (meisai, dự phòng khi tương lai không
-- lấy được 売上伝票データ). Đối chiếu thật cùng ngày 2026-08-03 (sau khử
-- trùng): 粗利益/消費税額/原価 khớp TUYỆT ĐỐI, 金額 lệch 55/6.753.717đ (làm
-- tròn thuế khác cách — xem docs/cot-day-du-ban-hang.md).
ALTER TABLE core.fact_sales_line
    ADD COLUMN source text NOT NULL DEFAULT 'uriage';

ALTER TABLE core.fact_sales_line DROP CONSTRAINT fact_sales_line_pkey;
ALTER TABLE core.fact_sales_line ADD PRIMARY KEY (slip_no, line_seq, source);

CREATE INDEX ON core.fact_sales_line (source, sales_date);

COMMENT ON COLUMN core.fact_sales_line.source IS
  '''uriage'' = 売上伝票データ, 明細行番号 THẬT từ OBC. ''meisai'' = 売上明細表, '
  'KHÔNG có 明細行番号 trong file gốc -- reader tự sinh line_seq bằng số thứ '
  'tự xuất hiện trong file theo từng 伝票No. (xem synthesize_line_seq trong '
  'kome/reader.py). Ổn định khi nạp lại CÙNG một file, KHÔNG đảm bảo khớp '
  'nếu OBC xuất lại cùng kỳ với thứ tự dòng khác trong lần xuất sau. CHỈ '
  'nạp MỘT trong hai nguồn cho cùng một ngày -- pipeline.ingest() tự chặn '
  'nếu ngày đó đã có dữ liệu từ nguồn kia (xem _kiem_tra_trung_nguon).';
```

- [ ] **Step 2: Chạy lại bộ test migration để xác nhận áp được sạch từ đầu**

Run: `pytest tests/test_migrate.py tests/test_roles.py -v`
Expected: PASS (migration 017 chạy không lỗi, quyền các vai trò không đổi)

- [ ] **Step 3: Commit**

```bash
git add db/migrations/017_nguon_ban_hang_thay_the.sql
git commit -m "feat: them cot source cho fact_sales_line, chuan bi nap tu 2 nguon ban hang"
```

---

## Task 2: `FileSpec` — thêm cờ `synthesize_line_seq`

**Files:**
- Modify: `kome/config.py`

**Interfaces:**
- Produces: `FileSpec.synthesize_line_seq: bool = False`

- [ ] **Step 1: Viết test cho giá trị mặc định (giống mẫu `test_dedup_on_keys_mac_dinh_tat_cho_cac_spec_khac`)**

Thêm vào `tests/test_reader.py`:

```python
def test_synthesize_line_seq_mac_dinh_tat_cho_cac_spec_khac():
    """synthesize_line_seq là tính năng riêng cho 売上明細表 (không có
    明細行番号 trong file gốc). Các spec khác phải nhận mặc định False."""
    assert SPECS["zaiko"].synthesize_line_seq is False
    assert SPECS["uriage"].synthesize_line_seq is False
```

- [ ] **Step 2: Chạy test, xác nhận lỗi vì field chưa tồn tại**

Run: `pytest tests/test_reader.py::test_synthesize_line_seq_mac_dinh_tat_cho_cac_spec_khac -v`
Expected: FAIL với `TypeError: FileSpec.__init__() got an unexpected keyword argument` HOẶC `AttributeError` (field chưa có)

- [ ] **Step 3: Thêm field vào `FileSpec`**

Trong `kome/config.py`, sau dòng `dedup_on_keys: bool = False` (dòng 39):

```python
    # 売上明細表 không có 明細行番号 trong file gốc (chỉ 売上伝票データ có). Bật cờ
    # này để reader tự sinh line_seq = số thứ tự xuất hiện trong file, nhóm
    # theo slip_no -- ổn định khi nạp lại CÙNG một file, không đảm bảo khớp
    # giữa hai lần xuất khác nhau của cùng kỳ (xem migration 017).
    synthesize_line_seq: bool = False
```

- [ ] **Step 4: Chạy lại test, xác nhận qua**

Run: `pytest tests/test_reader.py::test_synthesize_line_seq_mac_dinh_tat_cho_cac_spec_khac -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kome/config.py tests/test_reader.py
git commit -m "feat: them co synthesize_line_seq vao FileSpec"
```

---

## Task 3: `reader.read()` — tự sinh `line_seq` khi spec bật cờ

**Files:**
- Modify: `kome/reader.py:38-87` (hàm `read()`)
- Test: `tests/test_reader.py`

**Interfaces:**
- Consumes: `FileSpec.synthesize_line_seq` (Task 2)
- Produces: `DataFrame` trả về từ `read()` có cột `line_seq` (int, duy nhất trong từng nhóm `slip_no`) khi spec bật cờ.

- [ ] **Step 1: Viết test — cột trùng tên trong file + line_seq tự sinh**

Thêm vào `tests/test_reader.py`:

```python
def test_meisai_tu_sinh_line_seq_va_lay_dung_cot_trung_ten(tmp_path):
    """売上明細表 không có 明細行番号, và có 2 cột CÙNG TÊN 荷姿区分コード (một
    bản luôn có giá trị, một bản tra theo danh mục sản phẩm nên rỗng ở dòng
    phụ phí/coupon không phải sản phẩm thật -- đã kiểm chứng trên dữ liệu
    thật 2026-08-03: 0 lệch giữa 2 bản khi cả hai đều có dữ liệu).

    pandas tự thêm hậu tố ".1" cho cột trùng thứ hai khi đọc -- khai tên
    KHÔNG hậu tố trong config/files.yml là lấy đúng bản luôn có giá trị.
    """
    import pandas as pd
    cols = ["伝票No.", "得意先コード", "商品コード", "荷姿区分コード", "荷姿区分名",
            "売上日付", "伝票区分", "担当者コード", "部門コード",
            "入数", "純売上数量", "単価", "単位原価",
            "税込純売上高", "消費税額", "売上原価", "粗利益", "粗利益率", "消費税率",
            "荷姿区分コード", "荷姿区分名"]     # 2 cột cuối là bản trùng tên, để trống
    rows = [
        # 2 dòng cùng 伝票No. 090001 -> phải được sinh line_seq 1, 2
        ["090001", "000000009292", "XT07", "02", "ケース（大：段ボール）",
         "2026-08-03", "債権計上", "0004", "0020", 1, 6, 5250, 3210,
         31500, 2333, 19260, 9907, 0.3145, 0.08, "02", "ケース（大：段ボール）"],
        ["090001", "000000009292", "XT08", "00", "バ　ラ（小：単品）",
         "2026-08-03", "債権計上", "0004", "0020", 1, 2, 1000, 600,
         2000, 148, 1200, 652, 0.326, 0.08, "00", "バ　ラ（小：単品）"],
        # dòng phụ phí COD: mã không phải sản phẩm thật -> bản tra danh mục rỗng
        ["090001", "000000009292", "000000000001", "00", "荷姿区分なし",
         "2026-08-03", "債権計上", "0004", "0020", 1, 1, 300, 0,
         300, 22, 0, 273, 1.0, 0.08, "", ""],
    ]
    df_out = pd.DataFrame(rows, columns=cols)
    p = tmp_path / "売上明細表_20260803.xlsx"
    df_out.to_excel(p, sheet_name="売上明細表", index=False)

    from kome.reader import read
    doc = read(p, SPECS["meisai"])

    assert list(doc["line_seq"]) == [1, 2, 3]
    assert doc["pack_code"].tolist() == ["02", "00", "00"]   # bản LUÔN có giá trị
    assert doc["amount"].sum() == 33_800
```

- [ ] **Step 2: Chạy test, xác nhận lỗi (spec `meisai` chưa tồn tại trong `config/files.yml`)**

Run: `pytest tests/test_reader.py::test_meisai_tu_sinh_line_seq_va_lay_dung_cot_trung_ten -v`
Expected: FAIL với `KeyError: 'meisai'`

*(Spec `meisai` được thêm ở Task 4 — chạy lại test này SAU Task 4, không dừng lại sửa ở đây.)*

- [ ] **Step 3: Thêm bước sinh `line_seq` vào `reader.read()`**

Trong `kome/reader.py`, sau dòng `df = df.dropna(how="all")` (dòng 56), TRƯỚC đoạn chuẩn hoá ô trống (dòng 58-71):

```python
    # 売上明細表 không có 明細行番号 trong file gốc -- sinh line_seq bằng số thứ
    # tự xuất hiện trong file, nhóm theo slip_no. PHẢI làm TRƯỚC dedup_on_keys
    # và trước cổng 3 (kiểm khoá trùng dùng spec.keys = [slip_no, line_seq]),
    # để line_seq tồn tại lúc cổng 3 kiểm tra.
    if spec.synthesize_line_seq:
        df["line_seq"] = df.groupby("slip_no").cumcount() + 1
```

- [ ] **Step 4: Chạy test lại (sau khi Task 4 xong) để xác nhận qua**

Run: `pytest tests/test_reader.py::test_meisai_tu_sinh_line_seq_va_lay_dung_cot_trung_ten -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kome/reader.py tests/test_reader.py
git commit -m "feat: reader tu sinh line_seq cho spec bat synthesize_line_seq"
```

---

## Task 4: `config/files.yml` — thêm spec `meisai`

**Files:**
- Modify: `config/files.yml`

**Interfaces:**
- Produces: `SPECS["meisai"]` — dùng bởi Task 3 (test), Task 5 (loader), Task 6 (pipeline).

- [ ] **Step 1: Thêm khối `meisai` vào cuối `config/files.yml`**

```yaml
meisai:
  display_name: 売上明細表
  filename_pattern: '^売上明細表_(?P<date>\d{8})\.xlsx$'
  sheet: 売上明細表
  header_row: 1
  min_rows: 50
  keys: [slip_no, line_seq]
  # KHÔNG có 明細行番号 trong file gốc -- reader tự sinh line_seq (xem
  # synthesize_line_seq trong kome/reader.py). Dự phòng khi không lấy được
  # 売上伝票データ -- đối chiếu số liệu thật giữa hai nguồn ở
  # docs/cot-day-du-ban-hang.md.
  synthesize_line_seq: true
  warn_row_drop_ratio: 0.3
  warn_total_spike: 5.0
  warn_total_drop: 0.2
  date_columns: [sales_date]
  columns:
    伝票No.: slip_no
    売上日付: sales_date
    伝票区分: slip_type
    得意先コード: customer_code
    担当者コード: salesperson_code
    部門コード: department_code
    商品コード: product_code
    荷姿区分コード: pack_code
    入数: case_qty
    純売上数量: qty
    単価: unit_price
    単位原価: unit_cost
    税込純売上高: amount
    消費税額: tax_amount
    売上原価: cost
    粗利益: gross_profit
    粗利益率: gross_margin
    消費税率: tax_rate
  # 荷姿区分コード/名 xuất hiện HAI LẦN trong file gốc, CÙNG TÊN CỘT: một bản đi
  # kèm ngay 商品名/商品コード ở đầu file (LUÔN có giá trị), một bản tra theo
  # danh mục sản phẩm (RỖNG ở dòng phụ phí/coupon như 代引手数料, 値引きクーポン --
  # không phải sản phẩm thật, ~24% số dòng trong mẫu đã kiểm). pandas tự
  # thêm hậu tố ".1" cho cột trùng THỨ HAI khi đọc, nên khai tên KHÔNG hậu
  # tố ở trên là lấy đúng bản luôn có giá trị -- đã kiểm chứng trên dữ liệu
  # thật: 0/926 dòng lệch nhau giữa 2 bản khi cả hai đều có dữ liệu.
  # Không có 請求先コード/請求日付/請求締日コード/入金額１/入金伝票No.１ trong file
  # gốc -- loader để các cột CSDL tương ứng là NULL/0 (xem kome/loaders/sales.py).
  code_columns: [slip_no, customer_code, salesperson_code, department_code, product_code, pack_code]
  money_columns: [unit_price, unit_cost, amount, tax_amount, cost, gross_profit]
  total_column: amount
  qty_columns: [case_qty, qty]
  rate_columns: [gross_margin, tax_rate]
  required_date_columns: [sales_date]
```

- [ ] **Step 2: Chạy lại test Task 3 (giờ spec đã tồn tại)**

Run: `pytest tests/test_reader.py::test_meisai_tu_sinh_line_seq_va_lay_dung_cot_trung_ten -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add config/files.yml
git commit -m "feat: khai bao spec meisai (uriage_明細表) trong files.yml"
```

---

## Task 5: `kome/loaders/sales.py` — cột `source` + loader cho `meisai`

**Files:**
- Modify: `kome/loaders/sales.py`
- Test: `tests/test_load_sales.py`

**Interfaces:**
- Consumes: `core.fact_sales_line.source` (Task 1)
- Produces: `sales.load(conn, df, data_date, batch_id, source="uriage")` (tương thích ngược, gọi 4 tham số như cũ vẫn chạy đúng); `sales.load_meisai(conn, df, data_date, batch_id)`.

- [ ] **Step 1: Viết test cho `load_meisai` và khoá 3 phần**

Thêm vào `tests/test_load_sales.py`:

```python
def _meisai_line(slip="090001", seq=1, amount=31500, profit=9907, batch_id=1):
    return {
        "slip_no": slip, "line_seq": seq, "sales_date": date(2026, 8, 3),
        "slip_type": "債権計上", "customer_code": "000000009292",
        "salesperson_code": "0004", "department_code": "0020",
        "product_code": "XT07", "pack_code": "02", "case_qty": 1, "qty": 6,
        "unit_price": 5250, "unit_cost": 3210, "amount": amount,
        "tax_amount": 2333, "cost": 19260, "gross_profit": profit,
        "gross_margin": 0.3145, "batch_id": batch_id,
    }


def test_load_meisai_ghi_source_dung(conn, batch):
    b = batch(1)
    df = pd.DataFrame([_meisai_line(batch_id=b)])
    assert sales.load_meisai(conn, df, date(2026, 8, 3), b) == 1
    r = conn.execute(
        "SELECT source, amount FROM core.fact_sales_line"
    ).fetchone()
    assert r == ("meisai", 31500)


def test_uriage_va_meisai_khong_dung_do_khoa_ba_phan(conn, batch):
    """slip_no+line_seq CÓ THỂ trùng giữa 2 nguồn (line_seq của meisai là số
    tự sinh, không liên quan gì tới line_seq thật của uriage) -- khoá chính
    phải có thêm source để không đè nhầm dữ liệu của nhau."""
    b1 = batch(1)
    sales.load(conn, pd.DataFrame([_meisai_line(seq=1, amount=29167, batch_id=b1)]),
               date(2026, 8, 3), b1)   # source mặc định "uriage"
    b2 = batch(2)
    sales.load_meisai(conn, pd.DataFrame([_meisai_line(seq=1, amount=31500, batch_id=b2)]),
                       date(2026, 8, 3), b2)
    r = conn.execute(
        "SELECT source, amount FROM core.fact_sales_line ORDER BY source"
    ).fetchall()
    assert r == [("meisai", 31500), ("uriage", 29167)]
```

- [ ] **Step 2: Chạy test, xác nhận lỗi (`load_meisai` chưa tồn tại)**

Run: `pytest tests/test_load_sales.py::test_load_meisai_ghi_source_dung tests/test_load_sales.py::test_uriage_va_meisai_khong_dung_do_khoa_ba_phan -v`
Expected: FAIL với `AttributeError: module 'kome.loaders.sales' has no attribute 'load_meisai'`

- [ ] **Step 3: Sửa `kome/loaders/sales.py`**

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
    "source",
]
_UPDATE = ", ".join(f"{c}=EXCLUDED.{c}" for c in COLUMNS if c not in ("slip_no", "line_seq", "source"))


def load(conn: psycopg.Connection, df: pd.DataFrame,
         data_date: date, batch_id: int, source: str = "uriage") -> int:
    """Upsert theo 伝票No. + số dòng + nguồn.

    Nhờ khoá này mà đối soát tháng hoạt động: nạp lại cả tháng thì phiếu
    đã sửa trong OBC được ghi đè, phiếu không đổi thì ghi lại y nguyên.
    Có `source` trong khoá để 売上伝票データ (source="uriage") và 売上明細表
    (source="meisai", xem load_meisai) không đè lên nhau dù line_seq trùng
    số -- line_seq của meisai là số THỨ TỰ TỰ SINH, không liên quan gì tới
    line_seq thật của uriage.

    LƯU Ý: 売上伝票データ xuất mỗi dòng nghiệp vụ HAI LẦN (出荷内訳 và 明細按分,
    cùng khoá slip_no+line_seq). Việc khử trùng phải xảy ra TRƯỚC khi tới đây
    (kome.reader.read() làm việc này qua cấu hình dedup_on_keys) — loader này
    chỉ upsert, không tự khử trùng, để dùng được cả cho dữ liệu test đã sạch.
    """
    df = df.copy()
    df["batch_id"] = batch_id
    df["source"] = source
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = None
    rows = list(df[COLUMNS].itertuples(index=False, name=None))
    with conn.cursor() as cur:
        cur.executemany(
            f"""INSERT INTO core.fact_sales_line ({', '.join(COLUMNS)})
                VALUES ({', '.join(['%s'] * len(COLUMNS))})
                ON CONFLICT (slip_no, line_seq, source) DO UPDATE SET {_UPDATE}""",
            rows,
        )
    conn.commit()
    return len(rows)


def load_meisai(conn: psycopg.Connection, df: pd.DataFrame,
                 data_date: date, batch_id: int) -> int:
    """売上明細表 (nguồn dự phòng) -- chỉ khác `load()` ở source="meisai"."""
    return load(conn, df, data_date, batch_id, source="meisai")
```

- [ ] **Step 4: Chạy toàn bộ test loader bán hàng, xác nhận qua hết**

Run: `pytest tests/test_load_sales.py -v`
Expected: PASS (bao gồm cả các test cũ — `source` mặc định `"uriage"` giữ nguyên hành vi trước đây)

- [ ] **Step 5: Commit**

```bash
git add kome/loaders/sales.py tests/test_load_sales.py
git commit -m "feat: loader ban hang ghi cot source, them load_meisai"
```

---

## Task 6: `kome/pipeline.py` — đăng ký `meisai` + chặn trùng nguồn cùng ngày

**Files:**
- Modify: `kome/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `sales.load_meisai` (Task 5), `SPECS["meisai"]` (Task 4)
- Produces: `LOADERS["meisai"]`, `UNDO_TABLES["meisai"]`, hàm `_kiem_tra_trung_nguon(conn, spec, df) -> list[gates.Blocker]`

- [ ] **Step 1: Viết test — nạp `meisai` cho ngày đã có `uriage` phải bị chặn**

Thêm vào `tests/test_pipeline.py`:

```python
def test_chan_nap_meisai_khi_ngay_do_da_co_uriage(conn, tmp_path):
    """Hai nguồn cùng ghi vào core.fact_sales_line -- nạp cả hai cho CÙNG
    một ngày sẽ cộng doanh thu hai lần trong mọi báo cáo mart mà không ai
    biết. pipeline.ingest() phải chặn, không chỉ cảnh báo."""
    from kome.config import load_specs
    spec = load_specs(Path("config/files.yml"))["uriage"]
    rows = []
    for i in range(60):
        rows.append({
            "slip_no": f"07{i:04d}", "line_seq": 1, "sales_date": date(2026, 8, 3),
            "billing_date": date(2026, 8, 31), "slip_type": "債権計上",
            "customer_code": "000000009292", "billing_customer_code": "000000009292",
            "salesperson_code": "0004", "department_code": "01", "shipto_code": "0001",
            "product_code": "XT07", "pack_code": "02", "case_qty": 1, "qty": 6,
            "unit_price": 5250, "unit_cost": 3210, "amount": 29167,
            "tax_amount": 2333, "cost": 19260, "gross_profit": 9907,
            "gross_margin": 0.3397, "tax_rate": 0.08, "paid_amount": 0,
            "payment_slip_no": "000000", "closing_day_code": "99",
        })
    import pandas as pd
    df = pd.DataFrame(rows)
    ja_of = {sys_col: ja for ja, sys_col in spec.columns.items()}
    df = df.rename(columns=ja_of)[list(spec.columns.keys())]
    p_uriage = tmp_path / "売上伝票データ_20260803.xlsx"
    df.to_excel(p_uriage, sheet_name=spec.sheet, index=False)

    r1 = ingest(conn, p_uriage, tmp_path / "archive")
    assert r1.ok, r1.blockers

    spec_m = load_specs(Path("config/files.yml"))["meisai"]
    rows_m = []
    for i in range(60):
        rows_m.append({
            "slip_no": f"09{i:04d}", "sales_date": date(2026, 8, 3),
            "slip_type": "債権計上", "customer_code": "000000009292",
            "salesperson_code": "0004", "department_code": "0020",
            "product_code": "XT07", "pack_code": "02", "case_qty": 1, "qty": 6,
            "unit_price": 5250, "unit_cost": 3210, "amount": 31500,
            "tax_amount": 2333, "cost": 19260, "gross_profit": 9907,
            "gross_margin": 0.3145, "tax_rate": 0.08,
        })
    df_m = pd.DataFrame(rows_m)
    ja_of_m = {sys_col: ja for ja, sys_col in spec_m.columns.items()}
    df_m = df_m.rename(columns=ja_of_m)[list(spec_m.columns.keys())]
    p_meisai = tmp_path / "売上明細表_20260803.xlsx"
    df_m.to_excel(p_meisai, sheet_name=spec_m.sheet, index=False)

    r2 = ingest(conn, p_meisai, tmp_path / "archive")
    assert not r2.ok
    assert any(b.gate == 3 and "uriage" in b.message for b in r2.blockers)

    n = conn.execute(
        "SELECT count(*) FROM core.fact_sales_line WHERE source = 'meisai'"
    ).fetchone()[0]
    assert n == 0   # không ghi gì cả khi bị chặn
```

- [ ] **Step 2: Chạy test, xác nhận lỗi (`meisai` chưa có trong `LOADERS`)**

Run: `pytest tests/test_pipeline.py::test_chan_nap_meisai_khi_ngay_do_da_co_uriage -v`
Expected: FAIL với `KeyError: 'meisai'` (từ `LOADERS[spec.name]` trong `ingest()`)

- [ ] **Step 3: Sửa `kome/pipeline.py`**

Thêm import và đăng ký loader (đầu file, cạnh `LOADERS`/`UNDO_TABLES` hiện có):

```python
from kome import archive, gates
from kome.config import SPECS, FileSpec
from kome.reader import read, ColumnMismatch
from kome.loaders import inventory, customer, sales, master, price

LOADERS = {
    "zaiko": inventory.load,
    "tokuisaki": customer.load,
    "uriage": sales.load,
    "meisai": sales.load_meisai,
    "shohin": master.make_loader(
        "core.dim_product", ["product_code"],
        ["product_code", "product_name", "name_ja", "kind_code", "kind_name",
         "food_category_code", "food_category_name", "rank_code", "rank_name",
         "compete_code", "barcode", "unit", "case_qty", "shelf_code", "introduced_on"]),
    "shiiresaki": master.make_loader(
        "core.dim_supplier", ["supplier_code"], ["supplier_code", "supplier_name"]),
    "chokusousaki": master.make_loader(
        "core.dim_shipto", ["shipto_code"],
        ["shipto_code", "shipto_name", "customer_code", "postcode", "prefecture",
         "city", "address", "phone", "lead_time_code"]),
    "tanka": price.load,
}

UNDO_TABLES = {
    "zaiko": ["core.fact_inventory_daily"],
    "tokuisaki": ["core.dim_customer"],
    "uriage": ["core.fact_sales_line"],
    "meisai": ["core.fact_sales_line"],
    "shohin": ["core.dim_product"],
    "shiiresaki": ["core.dim_supplier"],
    "chokusousaki": ["core.dim_shipto"],
    "tanka": ["core.fact_price_list"],
}
```

Thêm hàm mới ngay TRƯỚC `def ingest(...)`:

```python
def _kiem_tra_trung_nguon(conn, spec: FileSpec, df) -> list[gates.Blocker]:
    """Chặn nạp 売上伝票データ và 売上明細表 CHỒNG NGÀY nhau.

    Hai loại file này cùng ghi vào core.fact_sales_line (phân biệt bằng cột
    source) -- nếu cả hai cùng có dữ liệu một ngày thì MỌI báo cáo mart sẽ
    cộng doanh thu ngày đó hai lần mà không ai biết (mart/ chưa có logic
    chọn nguồn -- xem ghi chú "Việc cố tình để lại" trong plan triển khai
    tính năng này). Chỉ áp dụng cho hai spec này.
    """
    if spec.name not in ("uriage", "meisai"):
        return []
    nguon_khac = "meisai" if spec.name == "uriage" else "uriage"
    ngay = sorted(d for d in df["sales_date"].dropna().unique())
    if not ngay:
        return []
    rows = conn.execute(
        """SELECT DISTINCT sales_date FROM core.fact_sales_line
           WHERE source = %s AND sales_date = ANY(%s)""",
        (nguon_khac, list(ngay)),
    ).fetchall()
    if not rows:
        return []
    trung = sorted(r[0] for r in rows)
    return [gates.Blocker(
        3,
        f"Đã có dữ liệu nguồn {nguon_khac} cho {len(trung)} ngày "
        f"({trung[0]}..{trung[-1]}) — nạp thêm {spec.name} sẽ cộng doanh thu "
        f"hai lần. Hoàn tác lô {nguon_khac} trước nếu muốn đổi nguồn.")]
```

Sửa `ingest()` — chèn kiểm tra ngay sau dòng gọi `gates.check(...)`:

```python
    blockers, warnings = gates.check(path, spec, df, archive.previous_stats(conn, spec.name))
    blockers = blockers + _kiem_tra_trung_nguon(conn, spec, df)
    if blockers:
        return IngestResult(ok=False, spec_name=spec.name, blockers=blockers, warnings=warnings)
```

- [ ] **Step 4: Chạy lại test vừa viết + toàn bộ test pipeline/gates hiện có**

Run: `pytest tests/test_pipeline.py tests/test_load_sales.py tests/test_gates.py -v`
Expected: PASS toàn bộ, kể cả `test_moi_loader_deu_khai_bao_bang_can_don` và `test_moi_spec_trong_files_yml_deu_co_loader` (hai test lưới an toàn có sẵn, không cần sửa)

- [ ] **Step 5: Commit**

```bash
git add kome/pipeline.py tests/test_pipeline.py
git commit -m "feat: dang ky loader meisai, chan nap trung nguon cung ngay"
```

---

## Task 7: Chạy toàn bộ test + cập nhật tài liệu

**Files:**
- Modify: `docs/cot-day-du-ban-hang.md`
- Modify: `CLAUDE.md` (mục "Bẫy đã biết", điểm 4)

**Interfaces:**
- Không có — task tài liệu, không có code mới.

- [ ] **Step 1: Chạy toàn bộ test suite**

Run: `pytest -v`
Expected: PASS toàn bộ (không chỉ các file đã chạy riêng ở các Task trên — `test_bao_cao.py`, `test_khach_hang.py`, `test_coverage.py`, `test_web.py` đều gọi `sales.load(...)` với 4 tham số, phải vẫn xanh vì `source` có giá trị mặc định)

- [ ] **Step 2: Thêm kết quả đối chiếu thật vào `docs/cot-day-du-ban-hang.md`**

Thêm mục mới ở cuối file:

```markdown
## Đối chiếu thật với 売上明細表 (nguồn dự phòng, Task ngày 2026-09-17)

Cùng ngày 2026-08-03, sau khử trùng `売上伝票データ` theo (slip_no, line_seq):

| | 売上伝票データ | 売上明細表 | Lệch |
|---|---|---|---|
| Số dòng | 926 | 926 | 0 |
| 消費税額 | 509.889 | 509.889 | 0 |
| 原価 | 4.260.179 | 4.260.179 | 0 |
| 粗利益 | 1.983.539 | 1.983.539 | 0 |
| 金額/税込純売上高 | 6.753.717 | 6.753.662 | 55 (0,0008%) |

Kết luận: cả hai nguồn đáng tin ở mức số liệu. `売上伝票データ` vẫn là nguồn
CHÍNH vì có `明細行番号` (khoá dòng thật) và `入金額１`/`入金伝票No.１` (nối phiếu
thu). `売上明細表` chỉ dùng khi KHÔNG lấy được `売上伝票データ` — xem
`db/migrations/017_nguon_ban_hang_thay_the.sql` và `kome/loaders/sales.py`.

**Tên file khi xuất `売上明細表` để nạp qua `/nap`:** phải đặt tên đúng mẫu
`売上明細表_YYYYMMDD.xlsx` (giống mọi loại file khác) — bản test gửi trong
phiên này tên là `売上明細表.xlsx` (không có ngày), cổng 1 sẽ chặn nếu nạp
nguyên tên đó.
```

- [ ] **Step 3: Sửa điểm 4 trong "Bẫy đã biết" của `CLAUDE.md`**

Điểm này hiện viết: *"File báo cáo (`売上明細表`, `元帳`) có 5 dòng rác trước header."* — đo thật trên file `売上明細表_20260803` thì header nằm ở dòng 1, không có dòng rác. Sửa thành:

```markdown
4. File `元帳` có 5 dòng rác trước header (CHƯA kiểm chứng lại). `売上明細表`
   đã đo thật (2026-09-17): header ở dòng 1, KHÔNG có dòng rác — có thể do
   OBC đổi mẫu xuất, hoặc quan sát cũ chỉ đúng cho một cấu hình xuất khác.
   File master và `在庫一覧` thì header ở dòng 1.
```

- [ ] **Step 4: Commit**

```bash
git add docs/cot-day-du-ban-hang.md CLAUDE.md
git commit -m "docs: ghi doi chieu that uriage vs meisai, sua bay da biet ve header"
```

---

## Việc cố tình để lại (không làm trong plan này)

- **`mart/*` (16 view) không đổi.** Chúng vẫn đọc `core.fact_sales_line` không lọc theo `source` — nếu một ngày có CẢ HAI nguồn (không nên xảy ra vì Task 6 chặn), báo cáo sẽ cộng dồn. Đây là tính năng dự phòng cho một khả năng CHƯA xảy ra (theo lời người dùng) — khi nào `売上伝票データ` thật sự không lấy được nữa, việc cần làm lúc đó: thêm `AND source = 'uriage'` hoặc một view "chọn nguồn theo ngày, ưu tiên uriage" phía trước cả 16 view, rồi trỏ chúng sang view đó. Không làm trước vì YAGNI — có thể không bao giờ cần.
- **Trang `/nap` không có UI riêng để chọn "đây là file dự phòng".** Cổng 1 tự nhận diện qua tên file đúng mẫu `売上明細表_YYYYMMDD.xlsx`, không cần người dùng chọn gì thêm.
