# Bảng dữ liệu sửa trực tiếp — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trang Kho dữ liệu › Bảng dữ liệu, dạng bảng tính (tick chọn cột, sửa thẳng trong ô, nút Lưu). Trang cho sửa danh mục khách,
danh mục sản phẩm, giá 売価No. và tồn / hạn theo lô. Bản sửa nằm trong một sổ chỉ-thêm và có tác dụng ở mọi màn hình.
Khi OBC đổi đúng ô đó thì OBC thắng.

**Architecture:** Sổ `app.sua_du_lieu` và luật hiệu lực viết một lần (`mart.ap_sua` / `mart.lech_obc`). Bốn view hiệu lực:
`mart.dim_customer`, `mart.dim_product` (mới), `mart.bang_gia_kome`, `mart.ton_hien_tai` (thay thân). Migration dùng khối `DO`
viết lại mọi view / hàm `mart` đang đọc `core.dim_*` sang `mart.dim_*`. Python hiển thị đổi theo.
Mô-đun `kome/bang_du_lieu.py` cung cấp GET (1 lượt hỏi) và POST lưu (400 / 403 / 409). Giao diện React là một bảng tính
chỉ vẽ các dòng đang nhìn thấy.

**Tech Stack:** FastAPI + psycopg 3 + Postgres 17 (Supabase) · React 18 + Vite + TS + TanStack Query · pytest / vitest.

**Spec:** `docs/superpowers/specs/2026-09-30-bang-du-lieu-sua-design.md` (đọc trước mỗi task).

## Global Constraints

- `core` KHÔNG BAO GIỜ bị web UPDATE / INSERT / DELETE. Bản sửa chỉ vào `app.sua_du_lieu` (sổ CHỈ THÊM: `REVOKE UPDATE, DELETE` khỏi `kome_app`).
- Luật hiệu lực ĐÚNG MỘT chỗ: `mart.ap_sua(obc text, j jsonb, cot text)`, `mart.lech_obc(...)`. Không view / Python nào viết lại điều kiện.
- Với sổ rỗng, mọi số của mọi màn PHẢI y như trước: toàn bộ test cũ xanh, không sửa kỳ vọng của test cũ.
- Migration mới là `db/migrations/072_bang_du_lieu_sua.sql`. Không sửa 001–071. Migration chạy bằng `postgres` qua `db/migrate.py`.
- Mã (`customer_code`, `product_code`) không sửa được. Không thêm / xoá dòng. Ô giá / tồn mà OBC không có thì không sửa được.
- Cột được sửa (đúng danh sách của đặc tả §2):
  - khach: `customer_name, branch_name, rank_code, salesperson_code, closing_day_code, postcode, prefecture, city, address, building, phone, transfer_account`
  - san_pham: `product_name, name_ja, kind_code, food_category_code, rank_code, compete_code, barcode, unit, case_qty, shelf_code, introduced_on, pack1_code, pack1_base_qty`
  - gia: `gia_chua_thue` (khoa `mã|qc|bậc`)
  - ton: `stock_qty, best_before` (khoa `mã|kho`)
- Cờ quyền mới `duoc_sua_du_lieu`, thêm ở CUỐI `ND.CO_QUYEN`. Không có cổng đăng nhập (`request.state.nguoi` None) = được sửa.
- Nguồn Python / TS luôn LF. Sửa `giao_dien/` thì `npm run build` và commit `kome/web/spa/`.
- Chạy pytest THEO TỪNG FILE (`python -m pytest tests/<file>.py -q`); `kome_test` dùng chung, KHÔNG giết pytest giữa chừng.
- Mọi số trên web qua `giao_dien/src/dinh_dang.ts` (chuẩn Nhật). Tiền tố CSS mới `bdl-`.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `db/migrations/072_bang_du_lieu_sua.sql` | sổ, cờ, hàm luật, hai view hiệu lực, viết lại view/hàm mart, thân mới `bang_gia_kome` + `ton_hien_tai` |
| `tests/test_bang_du_lieu_mart.py` | luật hiệu lực, SCD2, cặp mã–tên, giá, tồn, test canh danh mục CSDL |
| `kome/bang_du_lieu.py` | định nghĩa cột, `doc(conn, loai)`, `luu(conn, loai, o, nguoi_id, co_quyen)` |
| `tests/test_bang_du_lieu.py` | doc / luu / 400 / 403 / 409 / API / trang / nhật ký / ảnh chụp |
| Python hiển thị (`kome/*.py` nhóm (a)) | `core.dim_*` → `mart.dim_*` |
| `tests/test_doc_hieu_luc.py` | test canh danh sách trắng file Python được đọc `core.dim_*` |
| `kome/web/anh_chup.py`, `kome/nhat_ky.py`, `kome/web/nguoi_dung.py`, `kome/web/app.py`, `scripts/tao_nguoi_dung.py` | phiên bản, nhật ký, cờ |
| `giao_dien/src/bang_du_lieu/logic.ts` (+ `.test.ts`) | logic thuần của bảng tính |
| `giao_dien/src/bang_du_lieu/ManBangDuLieu.tsx`, `BangTinh.tsx`, `bang_du_lieu.css`, `kieu.ts` | màn |
| `giao_dien/src/he_thong/TabKho.tsx`, `giao_dien/src/main.tsx`, `giao_dien/src/khoi_dau.ts` | điều hướng, kiểu |

---

### Task 1: Migration 072 — sổ, cờ, luật, `mart.dim_customer`, `mart.dim_product`

**Files:**
- Create: `db/migrations/072_bang_du_lieu_sua.sql` (phần 1)
- Create: `tests/test_bang_du_lieu_mart.py`

**Interfaces:**
- Produces:
  - `app.sua_du_lieu`
  - `app.nguoi_dung.duoc_sua_du_lieu`
  - `mart.sua_moi_nhat` (id, bang, khoa, cot, gia_tri, gia_tri_obc, bo, nguoi_dung_id, luc)
  - `mart.sua_theo_khoa` (bang, khoa, j jsonb)
  - `mart.ap_sua(text, jsonb, text) → text`
  - `mart.lech_obc(text, jsonb, text) → boolean`
  - `mart.dim_customer`, `mart.dim_product` (cột / kiểu / thứ tự y hệt bảng `core` cùng tên)

- [ ] **Step 1: Viết test hỏng** — `tests/test_bang_du_lieu_mart.py`:

```python
"""Bảng dữ liệu sửa (072): luật hiệu lực + view hiệu lực. Đặc tả 2026-09-30-bang-du-lieu-sua-design.md."""
from datetime import date

import psycopg
import pytest

D1, D2 = date(2026, 9, 1), date(2026, 9, 8)


def _sua(conn, bang, khoa, cot, gia_tri, obc, bo=False):
    conn.execute("""INSERT INTO app.sua_du_lieu (bang, khoa, cot, gia_tri, gia_tri_obc, bo)
                    VALUES (%s, %s, %s, %s, %s, %s)""", (bang, khoa, cot, gia_tri, obc, bo))
    conn.commit()


def _khach(conn, batch, ma, ten, ngay=D1, tinh="大阪府", hang=("0003", "C")):
    from kome.loaders import customer
    import pandas as pd
    b = batch(abs(hash((ma, ten, ngay))) % 90_000, ngay)
    df = pd.DataFrame([{"customer_code": ma, "customer_name": ten, "branch_name": "", "rank_code": hang[0],
                        "rank_name": hang[1], "salesperson_code": "0002", "salesperson_name": "A",
                        "closing_day_code": "", "closing_day_name": "", "postcode": "", "prefecture": tinh,
                        "city": "", "address": "", "building": "", "phone": "", "transfer_account": ""}])
    customer.load(conn, df, ngay, b)


def _hang(conn, batch, ma, ten, nganh=("01", "調味料_VNM")):
    b = batch(abs(hash((ma, ten))) % 90_000)
    conn.execute("""INSERT INTO core.dim_product (product_code, product_name, food_category_code, food_category_name,
                      kind_code, kind_name, case_qty, batch_id) VALUES (%s, %s, %s, %s, '0', '有形', 20, %s)
                    ON CONFLICT (product_code) DO UPDATE SET product_name = EXCLUDED.product_name,
                      food_category_code = EXCLUDED.food_category_code, food_category_name = EXCLUDED.food_category_name""",
                 (ma, ten, nganh[0], nganh[1], b))
    conn.commit()


def test_ap_sua_obc_giu_nguyen_thi_sua_thang_obc_doi_thi_obc_thang(conn):
    q = "SELECT mart.ap_sua(%s, %s::jsonb, 'x'), mart.lech_obc(%s, %s::jsonb, 'x')"
    j = '{"x": ["moi", "cu"]}'
    assert conn.execute(q, ("cu", j, "cu", j)).fetchone() == ("moi", True)
    assert conn.execute(q, ("khac", j, "khac", j)).fetchone() == ("khac", False)
    assert conn.execute(q, ("cu", None, "cu", None)).fetchone() == ("cu", False)
    assert conn.execute(q, (None, '{"x": ["moi", null]}', None, '{"x": ["moi", null]}')).fetchone() == ("moi", True)
    assert conn.execute(q, ("cu", '{"x": [null, "cu"]}', "cu", '{"x": [null, "cu"]}')).fetchone() == (None, True)


def test_dim_customer_ap_ban_sua_va_nap_obc_doi_dung_cot_thi_obc_thang(conn, batch):
    _khach(conn, batch, "K1", "Quán A")
    _sua(conn, "khach", "K1", "customer_name", "Quán A (Kyoto)", "Quán A")
    ten = lambda: conn.execute("SELECT customer_name FROM mart.dim_customer WHERE customer_code='K1' AND is_current").fetchone()[0]
    assert ten() == "Quán A (Kyoto)"
    _khach(conn, batch, "K1", "Quán A", ngay=D2, tinh="京都府")      # OBC đổi CỘT KHÁC → bản sửa vẫn thắng
    assert ten() == "Quán A (Kyoto)"
    _khach(conn, batch, "K1", "Quán B", ngay=date(2026, 9, 9))        # OBC đổi đúng cột → OBC thắng
    assert ten() == "Quán B"


def test_bo_ve_obc_va_dong_moi_nhat_thang(conn, batch):
    _khach(conn, batch, "K1", "Quán A")
    _sua(conn, "khach", "K1", "phone", "06-1", "")
    _sua(conn, "khach", "K1", "phone", None, "", bo=True)
    assert conn.execute("SELECT phone FROM mart.dim_customer WHERE customer_code='K1' AND is_current").fetchone()[0] == ""


def test_cot_cap_ma_ten_lay_ten_theo_ma_hieu_luc(conn, batch):
    _khach(conn, batch, "K1", "Quán A", hang=("0003", "C"))
    _khach(conn, batch, "K2", "Quán B", hang=("0001", "S"))
    _sua(conn, "khach", "K1", "rank_code", "0001", "0003")
    _sua(conn, "khach", "K1", "salesperson_code", "0004", "0002")
    r = conn.execute("""SELECT rank_code, rank_name, salesperson_code, salesperson_name FROM mart.dim_customer
                        WHERE customer_code='K1' AND is_current""").fetchone()
    ten_0004 = conn.execute("SELECT ten FROM core.dim_salesperson WHERE salesperson_code='0004'").fetchone()[0]
    assert r == ("0001", "S", "0004", ten_0004)


def test_dim_product_nganh_va_so(conn, batch):
    _hang(conn, batch, "P1", "Hang 1", ("01", "調味料_VNM"))
    _hang(conn, batch, "P2", "Hang 2", ("02", "冷凍食品_VNM"))
    _sua(conn, "san_pham", "P1", "food_category_code", "02", "01")
    _sua(conn, "san_pham", "P1", "case_qty", "24", "20.0000")
    r = conn.execute("SELECT food_category_code, food_category_name, case_qty FROM mart.dim_product WHERE product_code='P1'").fetchone()
    assert r[:2] == ("02", "冷凍食品_VNM") and float(r[2]) == 24


def test_view_hieu_luc_cung_cot_cung_kieu_voi_core(conn):
    q = """SELECT a.attname, format_type(a.atttypid, a.atttypmod) FROM pg_attribute a
           WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum"""
    for t in ("dim_customer", "dim_product"):
        assert conn.execute(q, (f"mart.{t}",)).fetchall() == conn.execute(q, (f"core.{t}",)).fetchall()


def test_so_chi_them_kome_app_khong_sua_khong_xoa(conn):
    for p in ("UPDATE", "DELETE"):
        assert conn.execute("SELECT has_table_privilege('kome_app', 'app.sua_du_lieu', %s)", (p,)).fetchone()[0] is False
    for p in ("SELECT", "INSERT"):
        assert conn.execute("SELECT has_table_privilege('kome_app', 'app.sua_du_lieu', %s)", (p,)).fetchone()[0] is True
    assert conn.execute("SELECT has_table_privilege('kome_app', 'mart.dim_customer', 'SELECT')").fetchone()[0] is True


def test_cot_la_bi_tu_choi(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO app.sua_du_lieu (bang, khoa, cot, gia_tri) VALUES ('khach', 'K1', 'customer_code', 'x')")
    conn.rollback()


def test_co_quyen_moi_va_so_quyen_nhan_co_do(conn):
    assert conn.execute("""SELECT column_default FROM information_schema.columns WHERE table_schema='app'
                           AND table_name='nguoi_dung' AND column_name='duoc_sua_du_lieu'""").fetchone()[0] == "false"
    d = conn.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='nhat_ky_quyen_co_check'").fetchone()[0]
    assert "duoc_sua_du_lieu" in d
```

(Điều chỉnh `_khach` cho khớp chữ ký thật của `kome/loaders/customer.py::load` và tên cột DataFrame mà nó nhận. Đọc file đó trước; nếu loader nhận tên cột OBC tiếng Nhật thì dựng DataFrame theo đó. Không đổi loader.)

- [ ] **Step 2: Chạy, xác nhận hỏng**: `python -m pytest tests/test_bang_du_lieu_mart.py -q` → lỗi "relation app.sua_du_lieu does not exist".

- [ ] **Step 3: Viết phần 1 của migration** — `db/migrations/072_bang_du_lieu_sua.sql`:

```sql
-- 072 — Bảng dữ liệu sửa trực tiếp (Kho dữ liệu › Bảng dữ liệu). Đặc tả 2026-09-30-bang-du-lieu-sua-design.md.
-- core VẪN chỉ đọc với web: bản sửa ở sổ CHỈ THÊM app.sua_du_lieu; mọi chỉ số đọc GIÁ TRỊ HIỆU LỰC qua mart.dim_customer,
-- mart.dim_product, mart.bang_gia_kome, mart.ton_hien_tai. Luật (chủ DN chốt 2026-09-30): OBC vẫn ghi đúng giá trị lúc sửa
-- → bản sửa thắng; OBC ghi khác (người ta đã sửa trong OBC) → OBC thắng. Viết MỘT lần: mart.ap_sua / mart.lech_obc.

CREATE TABLE app.sua_du_lieu (
    id            bigserial PRIMARY KEY,
    bang          text NOT NULL CHECK (bang IN ('khach', 'san_pham', 'gia', 'ton')),
    khoa          text NOT NULL CHECK (khoa <> ''),
    cot           text NOT NULL,
    gia_tri       text,
    gia_tri_obc   text,
    gia_tri_truoc text,
    bo            boolean NOT NULL DEFAULT false,
    nguoi_dung_id bigint REFERENCES app.nguoi_dung,
    luc           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT sua_du_lieu_cot_check CHECK (
        (bang = 'khach' AND cot IN ('customer_name', 'branch_name', 'rank_code', 'salesperson_code', 'closing_day_code',
                                    'postcode', 'prefecture', 'city', 'address', 'building', 'phone', 'transfer_account'))
     OR (bang = 'san_pham' AND cot IN ('product_name', 'name_ja', 'kind_code', 'food_category_code', 'rank_code',
                                       'compete_code', 'barcode', 'unit', 'case_qty', 'shelf_code', 'introduced_on',
                                       'pack1_code', 'pack1_base_qty'))
     OR (bang = 'gia' AND cot = 'gia_chua_thue')
     OR (bang = 'ton' AND cot IN ('stock_qty', 'best_before')))
);
CREATE INDEX sua_du_lieu_o ON app.sua_du_lieu (bang, khoa, cot, id DESC);
GRANT SELECT, INSERT ON app.sua_du_lieu TO kome_app;
GRANT USAGE ON SEQUENCE app.sua_du_lieu_id_seq TO kome_app;
REVOKE UPDATE, DELETE ON app.sua_du_lieu FROM kome_app;
GRANT SELECT ON app.sua_du_lieu TO kome_report, kome_ingest;

-- Cờ quyền thứ tư (đặc tả §4). Sổ đổi quyền nhận thêm cờ đó.
ALTER TABLE app.nguoi_dung ADD COLUMN duoc_sua_du_lieu boolean NOT NULL DEFAULT false;
ALTER TABLE app.nhat_ky_quyen DROP CONSTRAINT nhat_ky_quyen_co_check;
ALTER TABLE app.nhat_ky_quyen ADD CONSTRAINT nhat_ky_quyen_co_check
    CHECK (co IN ('duoc_vao_kho_du_lieu', 'duoc_sua_ngan_sach', 'duoc_quan_tri', 'duoc_sua_du_lieu'));

-- Dòng MỚI NHẤT của từng ô; bo = true nghĩa là không còn bản sửa (về OBC).
CREATE VIEW mart.sua_moi_nhat AS
SELECT DISTINCT ON (bang, khoa, cot) id, bang, khoa, cot, gia_tri, gia_tri_obc, bo, nguoi_dung_id, luc
FROM app.sua_du_lieu
ORDER BY bang, khoa, cot, id DESC;

CREATE VIEW mart.sua_theo_khoa AS
SELECT bang, khoa, jsonb_object_agg(cot, jsonb_build_array(gia_tri, gia_tri_obc)) AS j
FROM mart.sua_moi_nhat WHERE NOT bo
GROUP BY bang, khoa;

-- LUẬT HIỆU LỰC — ĐỊNH NGHĨA DUY NHẤT. obc = giá trị OBC hiện tại (::text của cột nguồn), j = mart.sua_theo_khoa.j.
CREATE FUNCTION mart.ap_sua(obc text, j jsonb, cot text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT CASE WHEN j ? cot AND (j -> cot ->> 1) IS NOT DISTINCT FROM obc THEN j -> cot ->> 0 ELSE obc END $$;

CREATE FUNCTION mart.lech_obc(obc text, j jsonb, cot text) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT coalesce(j ? cot AND (j -> cot ->> 1) IS NOT DISTINCT FROM obc, false) $$;

-- Danh mục khách hiệu lực: CÙNG cột / kiểu / thứ tự với core.dim_customer, mọi phiên bản SCD2; bản sửa chỉ áp lên
-- dòng is_current (không view nào đọc bản cũ). Cột cặp mã–tên: tên lấy theo MÃ hiệu lực khi mã bị sửa.
CREATE VIEW mart.dim_customer AS
WITH x AS (
    SELECT c.*, s.j
    FROM core.dim_customer c
    LEFT JOIN mart.sua_theo_khoa s ON c.is_current AND s.bang = 'khach' AND s.khoa = c.customer_code
)
SELECT x.customer_sk, x.customer_code, x.valid_from, x.valid_to, x.is_current,
       mart.ap_sua(x.customer_name, x.j, 'customer_name')       AS customer_name,
       mart.ap_sua(x.branch_name, x.j, 'branch_name')           AS branch_name,
       mart.ap_sua(x.rank_code, x.j, 'rank_code')               AS rank_code,
       x.category_code, x.order_app_code,
       mart.ap_sua(x.salesperson_code, x.j, 'salesperson_code') AS salesperson_code,
       x.price_level_code,
       mart.ap_sua(x.closing_day_code, x.j, 'closing_day_code') AS closing_day_code,
       x.billing_customer_code,
       mart.ap_sua(x.postcode, x.j, 'postcode')                 AS postcode,
       mart.ap_sua(x.prefecture, x.j, 'prefecture')             AS prefecture,
       mart.ap_sua(x.city, x.j, 'city')                         AS city,
       mart.ap_sua(x.address, x.j, 'address')                   AS address,
       mart.ap_sua(x.phone, x.j, 'phone')                       AS phone,
       x.invoice_reg_no, x.spot_flag, x.batch_id,
       mart.ap_sua(x.building, x.j, 'building')                 AS building,
       CASE WHEN mart.lech_obc(x.rank_code, x.j, 'rank_code')
            THEN (SELECT t.rank_name FROM core.dim_customer t
                  WHERE t.is_current AND t.rank_code = mart.ap_sua(x.rank_code, x.j, 'rank_code')
                    AND coalesce(t.rank_name, '') <> '' ORDER BY t.rank_name LIMIT 1)
            ELSE x.rank_name END                                  AS rank_name,
       CASE WHEN mart.lech_obc(x.salesperson_code, x.j, 'salesperson_code')
            THEN (SELECT t.ten FROM core.dim_salesperson t
                  WHERE t.salesperson_code = mart.ap_sua(x.salesperson_code, x.j, 'salesperson_code'))
            ELSE x.salesperson_name END                           AS salesperson_name,
       CASE WHEN mart.lech_obc(x.closing_day_code, x.j, 'closing_day_code')
            THEN (SELECT t.closing_day_name FROM core.dim_customer t
                  WHERE t.is_current AND t.closing_day_code = mart.ap_sua(x.closing_day_code, x.j, 'closing_day_code')
                    AND coalesce(t.closing_day_name, '') <> '' ORDER BY t.closing_day_name LIMIT 1)
            ELSE x.closing_day_name END                           AS closing_day_name,
       mart.ap_sua(x.transfer_account, x.j, 'transfer_account') AS transfer_account
FROM x;

CREATE VIEW mart.dim_product AS
WITH x AS (
    SELECT p.*, s.j
    FROM core.dim_product p
    LEFT JOIN mart.sua_theo_khoa s ON s.bang = 'san_pham' AND s.khoa = p.product_code
)
SELECT x.product_code,
       mart.ap_sua(x.product_name, x.j, 'product_name')             AS product_name,
       mart.ap_sua(x.name_ja, x.j, 'name_ja')                       AS name_ja,
       mart.ap_sua(x.kind_code, x.j, 'kind_code')                   AS kind_code,
       CASE WHEN mart.lech_obc(x.kind_code, x.j, 'kind_code')
            THEN (SELECT t.kind_name FROM core.dim_product t
                  WHERE t.kind_code = mart.ap_sua(x.kind_code, x.j, 'kind_code')
                    AND coalesce(t.kind_name, '') <> '' ORDER BY t.kind_name LIMIT 1)
            ELSE x.kind_name END                                      AS kind_name,
       mart.ap_sua(x.food_category_code, x.j, 'food_category_code') AS food_category_code,
       CASE WHEN mart.lech_obc(x.food_category_code, x.j, 'food_category_code')
            THEN (SELECT t.food_category_name FROM core.dim_product t
                  WHERE t.food_category_code = mart.ap_sua(x.food_category_code, x.j, 'food_category_code')
                    AND coalesce(t.food_category_name, '') <> '' ORDER BY t.food_category_name LIMIT 1)
            ELSE x.food_category_name END                             AS food_category_name,
       mart.ap_sua(x.rank_code, x.j, 'rank_code')                   AS rank_code,
       CASE WHEN mart.lech_obc(x.rank_code, x.j, 'rank_code')
            THEN (SELECT t.rank_name FROM core.dim_product t
                  WHERE t.rank_code = mart.ap_sua(x.rank_code, x.j, 'rank_code')
                    AND coalesce(t.rank_name, '') <> '' ORDER BY t.rank_name LIMIT 1)
            ELSE x.rank_name END                                      AS rank_name,
       mart.ap_sua(x.compete_code, x.j, 'compete_code')             AS compete_code,
       mart.ap_sua(x.barcode, x.j, 'barcode')                       AS barcode,
       mart.ap_sua(x.unit, x.j, 'unit')                             AS unit,
       mart.ap_sua(x.case_qty::text, x.j, 'case_qty')::numeric(14,4) AS case_qty,
       mart.ap_sua(x.shelf_code, x.j, 'shelf_code')                 AS shelf_code,
       mart.ap_sua(x.introduced_on, x.j, 'introduced_on')           AS introduced_on,
       x.batch_id,
       mart.ap_sua(x.pack1_code, x.j, 'pack1_code')                 AS pack1_code,
       mart.ap_sua(x.pack1_base_qty::text, x.j, 'pack1_base_qty')::numeric(14,4) AS pack1_base_qty
FROM x;

GRANT SELECT ON mart.sua_moi_nhat, mart.sua_theo_khoa, mart.dim_customer, mart.dim_product
    TO kome_app, kome_report, kome_ingest;
GRANT EXECUTE ON FUNCTION mart.ap_sua(text, jsonb, text), mart.lech_obc(text, jsonb, text)
    TO kome_app, kome_report, kome_ingest;
```

- [ ] **Step 4: Chạy lại**: `python -m pytest tests/test_bang_du_lieu_mart.py -q` → PASS. Rồi chạy `python -m pytest tests/test_migrate.py tests/test_roles.py -q` → PASS.

- [ ] **Step 5: Commit** `feat(072): so app.sua_du_lieu, luat ap_sua, view hieu luc dim_customer / dim_product, co duoc_sua_du_lieu`

---

### Task 2: Migration 072 — chuyển mọi view / hàm `mart` sang view hiệu lực; giá và tồn hiệu lực

**Files:**
- Modify: `db/migrations/072_bang_du_lieu_sua.sql` (thêm phần 2 ở CUỐI file; migration chưa chạy ở đâu nên sửa được)
- Modify: `tests/test_bang_du_lieu_mart.py`

**Interfaces:**
- Consumes: Task 1 (`mart.sua_theo_khoa`, `mart.ap_sua`, `mart.lech_obc`, `mart.dim_*`).
- Produces:
  - `mart.bang_gia_kome` thêm ở CUỐI hai cột: `gia_obc numeric` (giá chưa thuế theo OBC, trước bản sửa) và `da_sua boolean`.
  - `mart.ton_hien_tai` thêm ở CUỐI bốn cột: `so_luong_obc numeric(14,4)`, `best_before_obc text`, `sua_so_luong boolean`, `sua_han boolean`.
  - Khoá sổ: giá = `mã|qc|bậc`, tồn = `mã|kho`.

- [ ] **Step 1: Viết test hỏng** — thêm vào `tests/test_bang_du_lieu_mart.py`:

```python
def test_KHONG_view_ham_mart_nao_con_doc_danh_muc_OBC_tho(conn):
    """Test canh: migration sau chép thân view từ file cũ sẽ lặng lẽ đưa core.dim_* trở lại — bản sửa mất tác dụng ở màn đó."""
    v = conn.execute(r"""SELECT c.relname FROM pg_class c WHERE c.relnamespace = 'mart'::regnamespace AND c.relkind = 'v'
                         AND c.relname NOT IN ('dim_customer', 'dim_product')
                         AND pg_get_viewdef(c.oid) ~ '\mcore\.dim_(customer|product)\M'""").fetchall()
    f = conn.execute(r"""SELECT p.proname FROM pg_proc p WHERE p.pronamespace = 'mart'::regnamespace
                         AND p.prosrc ~ '\mcore\.dim_(customer|product)\M'""").fetchall()
    assert v == [] and f == []


def test_khach_360_doc_ten_da_sua(conn, batch):
    from tests.test_khach_hang import _mua
    _khach(conn, batch, "202601010001", "Quán A")
    _mua(conn, batch, "202601010001", D2)
    _sua(conn, "khach", "202601010001", "customer_name", "Quán A mới", "Quán A")
    assert conn.execute("SELECT ten_khach FROM mart.khach_360 WHERE customer_code='202601010001'").fetchone()[0] == "Quán A mới"


def _gia(conn, batch, ma, qc, lv, ex, inc, ngay=D2):
    b = batch(abs(hash((ma, qc, lv, ex, ngay))) % 90_000, ngay)
    conn.execute("""INSERT INTO core.fact_price_list (product_code, pack_code, price_level, valid_from, price_ex_tax,
                      price_in_tax, unit_cost, batch_id) VALUES (%s, %s, %s, %s, %s, %s, 1000, %s)""",
                 (ma, qc, lv, ngay, ex, inc, b))
    conn.commit()


def test_gia_sua_thang_khi_OBC_giu_nguyen_va_thua_khi_OBC_doi(conn, batch):
    _hang(conn, batch, "P1", "Hang 1")
    _gia(conn, batch, "P1", "02", "01", 5000, 5400)
    obc = conn.execute("SELECT gia_obc::text FROM mart.bang_gia_kome WHERE product_code='P1'").fetchone()[0]
    _sua(conn, "gia", "P1|02|01", "gia_chua_thue", "5200", obc)
    r = conn.execute("SELECT gia_chua_thue, gia_obc, da_sua FROM mart.bang_gia_kome WHERE product_code='P1'").fetchone()
    assert (float(r[0]), float(r[1]), r[2]) == (5200, 5000, True)
    _gia(conn, batch, "P1", "02", "01", 5100, 5508, ngay=date(2026, 9, 20))       # lần nạp mới, OBC đổi giá
    r = conn.execute("SELECT gia_chua_thue, da_sua FROM mart.bang_gia_kome WHERE product_code='P1' AND hien_hanh").fetchone()
    assert (float(r[0]), r[1]) == (5100, False)


def _ton(conn, batch, ma, kho, sl, han, ngay=D2):
    b = batch(abs(hash((ma, kho, sl, ngay))) % 90_000, ngay)
    conn.execute("INSERT INTO core.dim_warehouse (warehouse_code, warehouse_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                 (kho, "Kho " + kho))
    conn.execute("""INSERT INTO core.fact_inventory_daily (snapshot_date, product_code, warehouse_code, best_before, stock_qty,
                      stock_unit_cost, stock_value, batch_id) VALUES (%s, %s, %s, %s, %s, 100, %s, %s)""",
                 (ngay, ma, kho, han, sl, int(sl * 100), b))
    conn.commit()


def test_ton_va_han_sua_di_theo_gia_tri_va_loai_han(conn, batch):
    _hang(conn, batch, "P1", "Hang 1")
    _ton(conn, batch, "P1", "0001", 10, "2027年03月10日")
    _sua(conn, "ton", "P1|0001", "stock_qty", "12", "10.0000")
    _sua(conn, "ton", "P1|0001", "best_before", "賞味期限なし", "2027年03月10日")
    r = conn.execute("""SELECT so_luong, gia_tri, best_before, loai_han, sua_so_luong, sua_han, so_luong_obc
                        FROM mart.ton_hien_tai WHERE product_code='P1'""").fetchone()
    assert (float(r[0]), r[1], r[2], r[3], r[4], r[5], float(r[6])) == (12, 1200, "賞味期限なし", "khong_han", True, True, 10)


def test_so_rong_moi_view_y_nhu_truoc(conn, batch):
    _hang(conn, batch, "P1", "Hang 1")
    _ton(conn, batch, "P1", "0001", 10, "2027年03月10日")
    r = conn.execute("SELECT so_luong, gia_tri, sua_so_luong, sua_han FROM mart.ton_hien_tai").fetchone()
    assert (float(r[0]), r[1], r[2], r[3]) == (10, 1000, False, False)
```

(Kiểm tên cột `ten_khach` của `mart.khach_360` và chữ ký `tests/test_khach_hang.py::_mua` trước khi dùng; đổi theo tên thật nếu khác.)

- [ ] **Step 2: Chạy, xác nhận hỏng**: `python -m pytest tests/test_bang_du_lieu_mart.py -q` → test canh ra danh sách view, các test giá / tồn lỗi cột.

- [ ] **Step 3: Thêm phần 2 vào CUỐI `072_bang_du_lieu_sua.sql`**:

```sql
-- ---------------------------------------------------------------------------------------------------------------------
-- Phần 2 — mọi view / hàm của mart đang đọc danh mục OBC THÔ chuyển sang view hiệu lực. Đọc định nghĩa SỐNG trong danh mục
-- Postgres (không chép thân từ file cũ), đổi chuỗi, tạo lại. Cột ra y hệt (mart.dim_* cùng kiểu với core.dim_*) nên
-- CREATE OR REPLACE không phải DROP view phụ thuộc. Tên view hiệu lực TRÙNG tên bảng có chủ ý: pg_get_viewdef in
-- "dim_customer.cot" khi bảng không bí danh — đổi schema thì tên đó vẫn trỏ đúng.
-- Test canh: tests/test_bang_du_lieu_mart.py::test_KHONG_view_ham_mart_nao_con_doc_danh_muc_OBC_tho.
DO $do$
DECLARE r record; d text;
BEGIN
    PERFORM set_config('search_path', 'pg_catalog', true);   -- mọi tên in ra đều có schema
    FOR r IN SELECT c.oid, c.relname FROM pg_class c
             WHERE c.relnamespace = 'mart'::regnamespace AND c.relkind = 'v'
               AND c.relname NOT IN ('dim_customer', 'dim_product')
               AND pg_get_viewdef(c.oid) ~ '\mcore\.dim_(customer|product)\M'
    LOOP
        d := regexp_replace(pg_get_viewdef(r.oid), '\mcore\.dim_(customer|product)\M', 'mart.dim_\1', 'g');
        d := regexp_replace(d, ';\s*$', '');
        EXECUTE format('CREATE OR REPLACE VIEW mart.%I AS %s', r.relname, d);
    END LOOP;
    FOR r IN SELECT p.oid FROM pg_proc p
             WHERE p.pronamespace = 'mart'::regnamespace AND p.prosrc ~ '\mcore\.dim_(customer|product)\M'
    LOOP
        EXECUTE regexp_replace(pg_get_functiondef(r.oid), '\mcore\.dim_(customer|product)\M', 'mart.dim_\1', 'g');
    END LOOP;
END
$do$;
```

Sau đó, cũng ở cuối file, thay thân `mart.bang_gia_kome`. Chép NGUYÊN thân 071 (`db/migrations/071_mart_bang_gia_kome.sql`, câu
`CREATE VIEW mart.bang_gia_kome`), đổi thành `CREATE OR REPLACE VIEW`, rồi sửa riêng câu SELECT cuối cho giá hiệu lực:

```sql
-- Giá hiệu lực (đặc tả §3): khoa sổ = mã|quy cách|bậc; chỉ áp lên dòng hiện hành; hai_cot_lech giữ theo OBC.
CREATE OR REPLACE VIEW mart.bang_gia_kome AS
WITH f AS ( ... y hệt 071 ... ),
s AS ( ... y hệt 071 ... ),
d AS ( ... y hệt 071 ... ),
k AS ( ... y hệt 071 ... ),
nay AS ( ... y hệt 071 ... ),
truoc AS ( ... y hệt 071 ... ),
lv AS ( ... y hệt 071 ... ),
hl AS (
    SELECT k.product_code, k.pack_code, lv.price_level, n.product_code IS NOT NULL AS hien_hanh,
           k.tu_ngay, k.tu_ngay_truoc, n.price_ex_tax, n.price_in_tax, n.hai_cot_lech, n.unit_cost,
           n.gia_chua_thue AS gia_obc, t.gia_chua_thue AS gia_truoc,
           CASE WHEN n.product_code IS NOT NULL
                THEN mart.ap_sua(n.gia_chua_thue::text, sk.j, 'gia_chua_thue')::numeric END AS gia_hl,
           n.product_code IS NOT NULL AND mart.lech_obc(n.gia_chua_thue::text, sk.j, 'gia_chua_thue') AS da_sua
    FROM k
    JOIN lv ON lv.product_code = k.product_code AND lv.pack_code = k.pack_code
    LEFT JOIN nay n ON n.product_code = lv.product_code AND n.pack_code = lv.pack_code AND n.price_level = lv.price_level
    LEFT JOIN truoc t ON t.product_code = lv.product_code AND t.pack_code = lv.pack_code AND t.price_level = lv.price_level
    LEFT JOIN mart.sua_theo_khoa sk
           ON sk.bang = 'gia' AND sk.khoa = k.product_code || '|' || k.pack_code || '|' || lv.price_level
)
SELECT product_code, pack_code, price_level, hien_hanh, tu_ngay, tu_ngay_truoc, price_ex_tax, price_in_tax,
       gia_hl AS gia_chua_thue, coalesce(hai_cot_lech, false) AS hai_cot_lech, nullif(unit_cost, 0) AS gia_von,
       gia_truoc,
       (tu_ngay_truoc IS NOT NULL AND gia_hl IS DISTINCT FROM gia_truoc) AS doi,
       coalesce(unit_cost > 0 AND gia_hl < unit_cost, false) AS duoi_gia_von,
       gia_obc, da_sua
FROM hl;
```

(`... y hệt 071 ...` nghĩa là chép TỪNG CHỮ các CTE đó từ file 071. Không viết lại logic. Tên, thứ tự và kiểu của 14 cột đầu
phải y như 071. Chạy `SELECT * FROM mart.bang_gia_kome LIMIT 0` trước và sau để so.)

Rồi thay thân `mart.ton_hien_tai`. Thân cũ ở `db/migrations/040_moc_lui.sql` (câu `CREATE OR REPLACE VIEW mart.ton_hien_tai`,
khoảng dòng 159–182). Thân mới:

```sql
-- Tồn / hạn hiệu lực (đặc tả §3): khoa sổ = mã|kho, áp lên ảnh chụp ≤ mốc đang chọn. gia_tri = stock_value của OBC,
-- hoặc round(số lượng hiệu lực × stock_unit_cost) khi số lượng bị sửa. loai_han / han_con_lai trên hạn hiệu lực.
CREATE OR REPLACE VIEW mart.ton_hien_tai AS
WITH i AS (
    SELECT i.*, sk.j
    FROM core.fact_inventory_daily i
    LEFT JOIN mart.sua_theo_khoa sk ON sk.bang = 'ton' AND sk.khoa = i.product_code || '|' || i.warehouse_code
    WHERE i.snapshot_date = (SELECT max(snapshot_date) FROM core.fact_inventory_daily
                              WHERE snapshot_date <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date)))
),
h AS (
    SELECT i.*,
           mart.ap_sua(i.stock_qty::text, i.j, 'stock_qty')::numeric(14,4) AS sl,
           mart.ap_sua(i.best_before, i.j, 'best_before')                    AS bb,
           mart.lech_obc(i.stock_qty::text, i.j, 'stock_qty')                AS sua_sl,
           mart.lech_obc(i.best_before, i.j, 'best_before')                  AS sua_bb
    FROM i
)
SELECT h.product_code, h.warehouse_code, w.warehouse_name AS ten_kho,
       h.sl AS so_luong,
       CASE WHEN h.sua_sl THEN round(h.sl * h.stock_unit_cost)::bigint ELSE h.stock_value END AS gia_tri,
       h.bb AS best_before,
       CASE WHEN h.bb ~ '^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$' THEN 'ngay'
            WHEN btrim(h.bb, ' 　') = '賞味期限なし'            THEN 'khong_han'
            WHEN coalesce(h.bb, '') = ''                     THEN 'trong'
            ELSE 'khong_ro' END AS loai_han,
       CASE WHEN h.bb ~ '^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$'
            THEN to_date(h.bb, 'YYYY"年"MM"月"DD"日"') - m.hom_nay
       END AS han_con_lai,
       h.stock_qty AS so_luong_obc, h.best_before AS best_before_obc, h.sua_sl AS sua_so_luong, h.sua_bb AS sua_han
FROM h
JOIN core.dim_warehouse w ON w.warehouse_code = h.warehouse_code
CROSS JOIN mart.moc_thoi_gian m;
```

(Đối chiếu với thân 040: tên, kiểu và thứ tự 8 cột đầu phải y hệt. Nếu 040 khác đoạn trên ở chi tiết nào, ví dụ điều kiện
mốc hay danh sách ký tự `btrim`, thì theo ĐÚNG 040.)

- [ ] **Step 4: Chạy**:
  - `python -m pytest tests/test_bang_du_lieu_mart.py -q` → PASS.
  - Rồi chạy từng file, và tất cả phải PASS không sửa kỳ vọng: `tests/test_mart_doi_thu.py`, `tests/test_bang_gia.py`,
    `tests/test_ton_theo_lo.py`, `tests/test_san_pham.py`, `tests/test_khach_hang.py`, `tests/test_mart_sp360.py`,
    `tests/test_lien_he.py`, `tests/test_ngung_ban.py`, `tests/test_hang_obc.py`, `tests/test_cong_no.py`.

- [ ] **Step 5: Commit** `feat(072): moi view / ham mart doc danh muc hieu luc; gia va ton hieu luc`

---

### Task 3: Python đọc danh mục hiệu lực + phiên bản ảnh chụp + nhật ký + cờ quyền

**Files:**
- Modify (đổi `core.dim_customer` → `mart.dim_customer`, `core.dim_product` → `mart.dim_product`, CHỈ ở câu SQL):
  - `kome/ban_khoang.py`, `kome/bang_gia.py`, `kome/doi_thu.py`, `kome/khach_hang.py`, `kome/khoi_tong_quan.py`,
    `kome/lien_he.py`, `kome/mua_vu.py`, `kome/nhat_ky.py`, `kome/san_pham.py`, `kome/san_pham_360.py`, `kome/web/api.py`
  - KHÔNG đổi: `kome/loaders/*`, `kome/pipeline.py`, `kome/nhat_ky_nap.py`, `kome/bang_kho.py`, `kome/coverage.py`, `kome/reader.py`.
- Modify: `kome/web/anh_chup.py` (`_PHIEN_BAN`, `_PHIEN_BAN_NAP` + chú thích luật `chi_nap`)
- Modify: `kome/nhat_ky.py` (`_NGUON` nhánh `du_lieu`, `LOAI`, `Dong.noi_dung`, `Dong.truoc_sau`, `TEN_CO`)
- Modify: `kome/web/nguoi_dung.py` (`_COT`, `NguoiDung`, `CO_QUYEN`, `_nguoi`, `dat_quyen`, `tao`)
- Modify: `kome/web/app.py` (`_NHAN_CO`, `_khoi_dau` → `nguoi.duoc_sua_du_lieu`, `doi_quyen` truyền cờ thứ tư)
- Modify: `scripts/tao_nguoi_dung.py` (`quyen --sua-du-lieu | --bo-sua-du-lieu`, cột liệt kê)
- Modify: `giao_dien/src/khoi_dau.ts` (kiểu `NguoiDung.duoc_sua_du_lieu?: boolean`)
- Create: `tests/test_doc_hieu_luc.py`
- Modify: `tests/test_api.py` (tham số `doi` của `test_moi_nguon_doi_la_tinh_lai` thêm `sua_du_lieu`)

**Interfaces:**
- Consumes: Task 1–2.
- Produces:
  - `ND.CO_QUYEN == ("duoc_vao_kho_du_lieu", "duoc_sua_ngan_sach", "duoc_quan_tri", "duoc_sua_du_lieu")`
  - `ND.dat_quyen(conn, ten, kho_du_lieu=None, ngan_sach=None, quan_tri=None, sua_du_lieu=None, sua_boi=None)`
  - `NguoiDung.duoc_sua_du_lieu: bool` (mặc định False)
  - `window.__KOME__.nguoi.duoc_sua_du_lieu`
  - `NK.LOAI["du_lieu"]`

- [ ] **Step 1: Test hỏng** — `tests/test_doc_hieu_luc.py`:

```python
"""Test canh (072): chỉ những file RAW mới được đọc danh mục OBC thô — mọi màn đọc mart.dim_* (giá trị hiệu lực)."""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[1] / "kome"
DUOC_DOC_THO = {"loaders/customer.py", "pipeline.py", "nhat_ky_nap.py", "bang_du_lieu.py", "coverage.py", "reader.py",
                "bang_kho.py"}


def test_chi_file_RAW_doc_core_dim():
    lo = []
    for p in GOC.rglob("*.py"):
        ten = p.relative_to(GOC).as_posix()
        if ten in DUOC_DOC_THO:
            continue
        for i, dong in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bcore\.dim_(customer|product)\b", dong) and not dong.lstrip().startswith("#"):
                lo.append(f"{ten}:{i}: {dong.strip()}")
    assert lo == [], "\n".join(lo)
```

Thêm vào `tests/test_nhat_ky.py`: một test ghi thẳng một dòng `app.sua_du_lieu` rồi khẳng định
`NK.dong_thoi_gian(conn, ...)` (dùng đúng chữ ký hiện có trong file) có một dòng `loai == "du_lieu"`.

Thêm vào `tests/test_nguoi_dung.py`: `dat_quyen(conn, "an", sua_du_lieu=True)` bật cờ và ghi `app.nhat_ky_quyen` với `co='duoc_sua_du_lieu'`.

Thêm `sua_du_lieu` vào tham số `doi` của `tests/test_api.py::test_moi_nguon_doi_la_tinh_lai`: chèn một dòng `app.sua_du_lieu` →
phiên bản đổi. Thêm một test: phiên bản `chi_nap=True` cũng đổi khi sổ có dòng mới.

- [ ] **Step 2: Chạy, xác nhận hỏng** (từng file).

- [ ] **Step 3: Sửa.**
  - Python hiển thị: đổi tên bảng trong SQL. Chỉ chú thích và docstring thì giữ, hoặc sửa chữ cho đúng.
  - `anh_chup.py`: thêm dòng `(SELECT max(id) FROM app.sua_du_lieu),` vào CẢ HAI biểu thức. Chú thích luật `chi_nap`:
    "không đọc bảng app nào NGOÀI app.sua_du_lieu (072 — bản sửa là dữ liệu mới như một lần nạp)".
  - `nhat_ky.py`:
    - Nhánh mới:

```python
    UNION ALL
    SELECT 'du_lieu', s.luc, s.nguoi_dung_id, s.bang || ': ' || s.khoa, s.cot,
           s.gia_tri_truoc, CASE WHEN s.bo THEN '(về OBC)' ELSE s.gia_tri END
    FROM app.sua_du_lieu s
```

    - `LOAI["du_lieu"] = ("✎", "Sửa dữ liệu", "canh")`;
    - `TEN_CO["duoc_sua_du_lieu"] = "sửa Bảng dữ liệu (bản sửa đè OBC)"`;
    - `noi_dung` → `f"{self.doi_tuong} · {self.chi_tiet}"`.
  - `nguoi_dung.py`:
    - thêm cột `n.duoc_sua_du_lieu` vào CUỐI `_COT` (sau `duoc_quan_tri`, trước phần `{them}`), và dời chỉ số trong
      `_nguoi` cho đúng (đọc kỹ `_nguoi` trước);
    - `CO_QUYEN` thêm ở cuối; `dat_quyen` và `tao` nhận `sua_du_lieu`.
  - `app.py`:
    - `_NHAN_CO["duoc_sua_du_lieu"] = "Sửa dữ liệu"`;
    - `_khoi_dau` thêm `"duoc_sua_du_lieu": nguoi.duoc_sua_du_lieu`;
    - `doi_quyen` truyền `sua_du_lieu=moi["duoc_sua_du_lieu"]`.
  - `scripts/tao_nguoi_dung.py`: cờ `--sua-du-lieu / --bo-sua-du-lieu` (mẫu y như `--ngan-sach`), cột "Sửa dữ liệu"
    trong liệt kê, cập nhật `HUONG_DAN`.
  - `CaiDat.tsx`: kiểm `colSpan` của hàng "chưa có tài khoản" (đổi nếu cột tăng).

- [ ] **Step 4: Chạy lại TỪNG FILE**, phải PASS:
  - các test đã sửa;
  - `tests/test_tao_nguoi_dung.py`, `tests/test_bao_mat.py`, `tests/test_khach_hang_api.py`, `tests/test_doi_thu.py`,
    `tests/test_doi_thu_api.py`, `tests/test_tong_quan.py`, `tests/test_cot_dung.py`, `tests/test_tai_lieu.py`.
  - Nếu `test_cot_dung` / `test_tai_lieu` đỏ vì ảnh chụp cũ: `python scripts/sinh_cot_dung.py` và
    `python scripts/sinh_tai_lieu.py` (có `PYTHONIOENCODING=utf-8`), rồi chạy lại.
  - Nếu `sinh_cot_dung` đòi khai mô-đun mới: khai theo cách script báo.

- [ ] **Step 5: Commit** `feat(bang-du-lieu): man doc danh muc hieu luc, anh chup va nhat ky theo so sua, co duoc_sua_du_lieu`

---

### Task 4: `kome/bang_du_lieu.py` + API + trang

**Files:**
- Create: `kome/bang_du_lieu.py`
- Modify: `kome/web/api.py` (hai route dưới `/api/kho-du-lieu/bang-du-lieu`), `kome/web/app.py` (route HTML `/kho-du-lieu/bang-du-lieu` → `_spa(request, man={})`)
- Modify: `scripts/sinh_cot_dung.py` (`MAN_HINH["bang_du_lieu"] = ("Bảng dữ liệu", "/kho-du-lieu/bang-du-lieu")`, `MAN["kome/bang_du_lieu.py"] = ["bang_du_lieu"]`) rồi chạy lại script
- Create: `tests/test_bang_du_lieu.py`

**Interfaces:**
- Consumes: Task 1–3.
- Produces (JSON — Task 5–6 đọc đúng hình dạng này):

```
GET /api/kho-du-lieu/bang-du-lieu?loai=sp|kh  →
{ "loai": "sp",
  "sua_duoc": true,                        // cờ duoc_sua_du_lieu (hoặc không có cổng)
  "cot": [{"ma": "product_name", "nhan": "Tên hàng", "nhom": "Danh mục OBC", "kieu": "chu", "sua": true},
          {"ma": "food_category_code", "nhan": "Ngành", "nhom": "Danh mục OBC", "kieu": "chon", "sua": true,
           "chon": [["01", "調味料_VNM"], ...]},
          {"ma": "gia:02|01", "nhan": "No.1 · ケース", "nhom": "Giá 売価No. (chưa thuế)", "kieu": "so", "sua": true},
          {"ma": "ton:0001", "nhan": "Tồn · <tên kho>", "nhom": "Tồn & hạn theo lô", "kieu": "so", "sua": true},
          {"ma": "han:0001", "nhan": "Hạn · <tên kho>", "nhom": "Tồn & hạn theo lô", "kieu": "ngay", "sua": true},
          {"ma": "dt_12t", "nhan": "DT 12 tháng", "nhom": "Chỉ số (chỉ xem)", "kieu": "so", "sua": false}, ...],
  "dong": [{"k": "NT01", "o": {"product_name": "...", "gia:02|01": "5200", "han:0001": "2027-03-10", ...}}],
  "lech": {"NT01\tfood_category_code": {"obc": "調味料_VNM", "ai": "an", "luc": "2026-09-30T08:00:00+00:00"}},
  "anh_ton": "2026-09-30", "lan_nap_gia": "2026-09-08" }
POST /api/kho-du-lieu/bang-du-lieu/luu  {"loai": "sp", "o": [{"k": "NT01", "cot": "gia:02|01", "gia_tri": "5300", "thay": "5200"}]}
  → 200 {"dong": [<dòng đã đọc lại, cùng hình dạng dong>], "lech": {...các ô của những dòng đó...}, "so_o": n}
  → 400 {"loi": "...", "o_loi": {"NT01\tgia:02|01": "Giá phải là số > 0"}}
  → 403 {"loi": "Bạn cần cờ 'Sửa dữ liệu' để lưu."}
  → 409 {"loi": "...", "xung_dot": [{"k", "cot", "gia_tri": "<hiệu lực hiện tại>", "ai", "luc"}]}
```

Mọi giá trị ô là CHUỖI dạng chuẩn (hoặc null).
- Số: `::text` của cột (vd `"20.0000"`), giá dạng `round(...)::text`.
- Hạn: `YYYY-MM-DD` hoặc `"không hạn"` hoặc `""`.
- Chọn: MÃ.
- Khoá ô trên dây: `f"{k}\t{cot}"`.

Hằng và hàm trong `kome/bang_du_lieu.py`:
- `LOAI = ("sp", "kh")`
- `TOI_DA_O = 2000`
- `class LoiO(Exception)` với `.o_loi: dict`
- `class XungDotO(Exception)` với `.xung_dot: list`
- `class KhongDuQuyen(Exception)`
- `doc(conn, loai: str) -> dict` (ĐÚNG 1 lượt hỏi)
- `luu(conn, loai: str, o: list[dict], nguoi_id: int | None, co_quyen: bool) -> dict`
- `han_obc(iso_hoac_chu: str) -> str`: `"2027-03-10"` → `"2027年03月10日"`, `"không hạn"` → `"賞味期限なし"`, `""` → `""`, sai dạng → `ValueError`.
- `han_iso(chu_obc: str | None) -> str`: ngược lại. Chữ không đọc được thì trả nguyên văn.

Luật trong `luu` (đặc tả §5):
- Kiểm `co_quyen` → `KhongDuQuyen`.
- `loai` ∈ `LOAI`, `len(o) ≤ TOI_DA_O`, mỗi ô có `k`, `cot` hợp lệ (cột `sua: true` của loại đó).
- Chữ: `strip()`, ≤ 200 ký tự.
- Số (`case_qty`, `pack1_base_qty`, tồn): hữu hạn, ≥ 0, làm tròn 4 số lẻ. Giá: > 0, số nguyên yên.
- Chọn: mã ∈ `chon`. Tỉnh ∈ `core.dim_prefecture.ten`. Hạn qua `han_obc`.
- Ô giá / tồn không tồn tại trong OBC → lỗi ô.
- Mọi lỗi gom vào `LoiO` một lần, không ghi gì.
- Rồi `SELECT pg_advisory_xact_lock(hashtext('bang_du_lieu:' || loai))`.
- Đọc hiệu lực hiện tại của các ô. Khác `thay` → `XungDotO` (kèm ai / lúc từ `mart.sua_moi_nhat` nếu có).
- Đọc giá trị OBC hiện tại:
  - khach: `core.dim_customer WHERE is_current`, `cot::text`;
  - sp: `core.dim_product`;
  - giá: `mart.bang_gia_kome.gia_obc::text` của dòng `hien_hanh`;
  - tồn: `mart.ton_hien_tai.so_luong_obc::text` / `best_before_obc`.
- Ghi `INSERT INTO app.sua_du_lieu (bang, khoa, cot, gia_tri, gia_tri_obc, gia_tri_truoc, bo, nguoi_dung_id)`:
  - bang: `khach` | `san_pham` | `gia` | `ton`;
  - khoa: mã | `mã|qc|bậc` | `mã|kho`;
  - cot trong sổ: danh mục = tên cột; giá = `gia_chua_thue`; tồn = `stock_qty` / `best_before`.
  - `bo = (gia_tri == obc)`. Ô có giá trị mới == hiệu lực hiện tại thì bỏ qua.
- Commit do route làm.

Chỉ số chỉ xem:
- sp: `dt_12t` = Σ doanh thu thuần 365 ngày tới mốc từ `mart.ban_den_moc` theo mã; `ton_tong` = Σ `mart.ton_hien_tai.so_luong`.
- kh: `dt_12t` từ `mart.doanh_thu_12t`; `lan_cuoi` = max ngày mua từ `mart.lan_mua`.
- Nhóm cột "Danh mục OBC" nhãn tiếng Việt: Tên, Chi nhánh, Hạng OBC, Người phụ trách, Ngày chốt, Mã bưu điện, Tỉnh,
  Thành phố, Địa chỉ, Toà nhà, Điện thoại, TK chuyển khoản; Tên hàng, Tên Nhật, Loại (有形/無形), Ngành, Hạng, Mã cạnh tranh,
  JAN, Đơn vị, Số / thùng, Kệ, Ngày ra mắt, 荷姿, Số gói / 荷姿.
- Danh sách `chon`:
  - khach: `rank_code` (mã → tên, từ core bản hiện hành), `salesperson_code` (`core.dim_salesperson`), `closing_day_code`,
    `prefecture` (47 tên `core.dim_prefecture`, mã = tên);
  - sp: `kind_code`, `food_category_code`, `rank_code` (từ core).
- Dòng sp: mọi mã của `mart.dim_product` (kể cả phí / POSM — đây là trang dữ liệu gốc, không phải danh mục bán).
  Dòng kh: mọi khách `mart.dim_customer WHERE is_current`.
- Thứ tự: theo mã.

- [ ] **Step 1: Test hỏng** — `tests/test_bang_du_lieu.py`. Tối thiểu các test sau (gieo dữ liệu như `tests/test_bang_du_lieu_mart.py`,
  dùng lại helper bằng `from tests.test_bang_du_lieu_mart import _khach, _hang, _gia, _ton`):
  - `test_doc_mot_luot_hoi_va_hinh_dang`: đếm `conn.execute` == 1. Có cột `gia:02|01`, `ton:0001`, `han:0001`.
    Giá trị là chuỗi; hạn dạng ISO.
  - `test_luu_ghi_so_va_doc_lai_hieu_luc`: lưu tên hàng + giá + hạn → `doc` thấy giá trị mới, `lech` có 3 ô;
    `app.sua_du_lieu` có 3 dòng với `gia_tri_obc` đúng.
  - `test_luu_bang_OBC_la_ve_OBC`: lưu lại giá trị OBC → dòng `bo = true`, `lech` rỗng.
  - `test_400_gom_moi_loi_khong_ghi_gi`: giá âm + tỉnh lạ + cột không sửa được → `LoiO` với 3 khoá, sổ rỗng.
  - `test_409_khi_thay_khac_hien_luc`: lưu với `thay` cũ → `XungDotO`, sổ không thêm dòng.
  - `test_403_khong_co_co`: `co_quyen=False` → `KhongDuQuyen`.
  - `test_han_obc_va_han_iso`: hai chiều + `ValueError`.
  - `test_api_va_trang`:
    - không cổng: GET 200, POST lưu 200 và nhật ký `/nhat-ky` có loại `du_lieu`;
    - `c.get("/kho-du-lieu/bang-du-lieu")` 200 với `man(...) == {}`;
    - POST không phải JSON → 415.
  - `test_api_co_cong_can_co_sua_du_lieu`: dùng mẫu `tests/test_bao_mat.py` (`khach`, `_vao`). Người có `duoc_vao_kho_du_lieu`
    mà không có `duoc_sua_du_lieu`: GET 200 (`sua_duoc` false), POST 403 JSON.

- [ ] **Step 2: Chạy, xác nhận hỏng.**

- [ ] **Step 3: Viết `kome/bang_du_lieu.py`, route API, route trang.**
  - Route API dùng `open_app_conn()`.
  - GET trả qua `_jd`.
  - POST theo mẫu `_dt_ghi` (415 / 400 JSON). `co_quyen = nguoi is None or nguoi.duoc_sua_du_lieu`.
  - Ánh xạ lỗi: `LoiO` → 400 `{loi, o_loi}`, `XungDotO` → 409, `KhongDuQuyen` → 403; commit khi thành công.

- [ ] **Step 4: Chạy lại** `tests/test_bang_du_lieu.py`, `tests/test_cot_dung.py`, `tests/test_tai_lieu.py`, `tests/test_bao_mat.py` → PASS.

- [ ] **Step 5: Commit** `feat(bang-du-lieu): API doc / luu bang du lieu + trang`

---

### Task 5: Logic thuần bảng tính (`giao_dien/src/bang_du_lieu/logic.ts`)

**Files:**
- Create: `giao_dien/src/bang_du_lieu/kieu.ts`, `logic.ts`, `logic.test.ts`

**Interfaces:**
- Consumes: hình dạng JSON của Task 4.
- Produces:

```ts
// kieu.ts
export type Kieu = "chu" | "so" | "ngay" | "chon";
export type Cot = { ma: string; nhan: string; nhom: string; kieu: Kieu; sua: boolean; chon?: [string, string][] };
export type Dong = { k: string; o: Record<string, string | null> };
export type Lech = Record<string, { obc: string | null; ai: string | null; luc: string | null }>;
export type BangApi = { loai: "sp" | "kh"; sua_duoc: boolean; cot: Cot[]; dong: Dong[]; lech: Lech; anh_ton: string | null; lan_nap_gia: string | null };
export type Cho = Record<string, string>;          // khoaO -> chữ đang gõ (chưa lưu)
// logic.ts
export const khoaO: (k: string, cot: string) => string;                 // `${k}\t${cot}`
export function tachO(ko: string): [string, string];
export function giaTri(d: Dong, cot: string, cho: Cho): string | null;  // chữ đang gõ nếu có, không thì giá trị máy chủ
export function hienThi(c: Cot, v: string | null): string;              // số theo so_luong() của dinh_dang.ts; chọn: tên theo mã; ngày giữ ISO
export function kiemO(c: Cot, chu: string): { gt: string } | { loi: string };  // chuẩn hoá phía trình duyệt (máy chủ vẫn kiểm lại)
export function datO(cho: Cho, d: Dong, c: Cot, chu: string): Cho;      // bằng giá trị máy chủ -> xoá khỏi cho
export function dan(tsv: string, neo: { d: number; c: number }, cots: Cot[], dongs: Dong[]):
  { o: { k: string; cot: string; chu: string }[]; bo_qua: number };      // ô không sửa được / ngoài bảng = bỏ qua
export function thanLuu(loai: "sp" | "kh", cho: Cho, dongs: Dong[]):
  { loai: string; o: { k: string; cot: string; gia_tri: string; thay: string | null }[] };
export function locDong(ds: Dong[], tim: string, chiLech: boolean, lech: Lech): Dong[];  // tìm bỏ dấu trên mã + mọi ô chữ
export function cotMacDinh(loai: "sp" | "kh", cots: Cot[]): string[];
export function docCotDaChon(loai: string): string[] | null;            // localStorage "kome_bdl_cot_v1:<loai>", try/catch
export function ghiCotDaChon(loai: string, ma: string[]): void;
export function khungNhin(cuon: number, cao: number, soDong: number, caoDong: number, du = 10): { dau: number; cuoi: number };
```

Chi tiết:
- `kiemO`:
  - `so`: bỏ dấu phẩy ngăn nghìn, `¥`, khoảng trắng; phải là số hữu hạn ≥ 0. Nếu cột bắt đầu `gia:` thì phải > 0 và làm tròn
    số nguyên. Trả chuỗi số.
  - `ngay`: `YYYY-MM-DD` hợp lệ, hoặc "không hạn", hoặc rỗng.
  - `chon`: mã phải thuộc `chon`, hoặc nhận TÊN của một lựa chọn thì đổi ra mã.
  - `chu`: `trim`.
- `dan`:
  - tách dòng bằng `\r?\n` (bỏ dòng rỗng cuối), cột bằng `\t`;
  - áp từ ô `neo` sang phải / xuống dưới trên `cots` ĐANG HIỆN và `dongs` ĐANG HIỆN;
  - ô `sua: false` hoặc giá trị máy chủ `null` ở cột `gia:` / `ton:` / `han:` → `bo_qua++`.
- `cotMacDinh`:
  - sp: `product_name, food_category_code, rank_code, unit, case_qty` + hai cột giá đầu + `ton:*` và `han:*` của kho đầu + `dt_12t`;
  - kh: `customer_name, salesperson_code, rank_code, prefecture, phone, dt_12t, lan_cuoi`.
  - Chỉ những mã có trong `cots`.

- [ ] **Step 1: Test hỏng** — `logic.test.ts` phủ:
  - `kiemO` cho mọi kiểu (cả lỗi);
  - `datO` bằng máy chủ thì xoá;
  - `dan` (một khối 2×2, có ô khoá → `bo_qua`);
  - `thanLuu` (`thay` = giá trị máy chủ);
  - `locDong` (bỏ dấu, `chiLech`);
  - `khungNhin` (biên đầu / cuối);
  - `docCotDaChon` khi `localStorage` ném lỗi → null.
- [ ] **Step 2:** `cd giao_dien && npx vitest run src/bang_du_lieu` → FAIL.
- [ ] **Step 3:** Viết `logic.ts` / `kieu.ts`. Bỏ dấu: dùng lại `khopTim` hoặc `bo_dau` của `giao_dien/src/san_pham/loc.ts`
  (export nếu cần), không chép.
- [ ] **Step 4:** vitest PASS.
- [ ] **Step 5: Commit** `feat(bang-du-lieu): logic thuan bang tinh`

---

### Task 6: Màn `ManBangDuLieu` + `BangTinh` + điều hướng

**Files:**
- Create: `giao_dien/src/bang_du_lieu/ManBangDuLieu.tsx`, `BangTinh.tsx`, `bang_du_lieu.css`
- Modify:
  - `giao_dien/src/he_thong/TabKho.tsx`: thêm `["bang-du-lieu", "/kho-du-lieu/bang-du-lieu", "▦", "Bảng dữ liệu"]` vào `TAB`, sau "Nạp dữ liệu mới";
  - `giao_dien/src/main.tsx`: lazy import + nhánh `if (duong === "/kho-du-lieu/bang-du-lieu") return () => <ManBangDuLieu />;`
    trong khối `KD.man != null`.
- Test: thêm vào `tests/test_bang_du_lieu.py` một test đọc mã nguồn: `TabKho.tsx` có `/kho-du-lieu/bang-du-lieu`, `main.tsx`
  có route, `ManBangDuLieu.tsx` gọi `/api/kho-du-lieu/bang-du-lieu`, có `giuKhoang(`, có `beforeunload`, không `toFixed(` / `de-DE`.

**Interfaces:** Consumes Task 4 (JSON) và Task 5 (logic). Không sinh interface cho task sau.

Yêu cầu màn (theo phác thảo đã duyệt, đặc tả §6):
- **Khung**
  - `KhungKho dang="bang-du-lieu"` (thêm `"bang-du-lieu"` vào kiểu `MucKho` nếu cần).
  - Tiêu đề "Bảng dữ liệu". Hai nút tab Sản phẩm / Khách hàng (`aria-pressed`) đổi `?loai=` qua
    `history.replaceState(null, "", giuKhoang(...))`.
  - Còn ô chưa lưu mà đổi tab → `confirm` trước.
- **Dữ liệu**
  - `useQuery(["bdl", loai], () => lay("/api/kho-du-lieu/bang-du-lieu?loai=" + loai), { refetchOnWindowFocus: false })`.
  - Cache là nguồn dữ liệu duy nhất. Lưu xong thì vá các dòng trả về bằng `setQueryData`.
  - Sau lưu thành công, `invalidateQueries` mọi khoá khác (các màn khác đọc số mới).
- **Thanh công cụ**
  - ô tìm, nút "Chọn cột" (bật / tắt khung bên trái), nút lọc "Đã sửa trên web, OBC chưa có (n)", chữ "n ô chưa lưu", Huỷ, Lưu.
  - Lưu chỉ màu nhấn khi có ô chờ.
  - Không có `sua_duoc` → không có Huỷ / Lưu. Dải chữ nói: "Chỉ xem — cần cờ 'Sửa dữ liệu' (Cài đặt) để sửa".
- **Khung chọn cột**
  - nhóm theo `cot.nhom`, ô tick, cột `sua: false` có 🔒;
  - lưu qua `ghiCotDaChon`; lần đầu dùng `cotMacDinh`.
- **`BangTinh`**
  - `<table>` trong khung cuộn cao `70vh`; dòng tiêu đề `position: sticky; top: 0`; cột Mã `sticky; left: 0`.
  - Dòng cao cố định 30px. Chỉ vẽ `khungNhin(...)`, với hai `<tr>` đệm trên / dưới có chiều cao tương ứng.
  - Ô chọn neo theo KHOÁ dòng (`{k, c}`): dùng lại `oKeTiep` từ `giao_dien/src/doi_thu/bang_sua_logic.ts` (import, không chép).
  - Phím:
    - mũi tên di chuyển (tự cuộn tới ô chọn);
    - Enter / F2 mở ô sửa; gõ một ký tự in được mở ô sửa với ký tự đó (trừ `chon`);
    - Esc bỏ; Enter lưu vào chờ rồi xuống; Tab / Shift+Tab sang phải / trái;
    - Delete / Backspace trên ô sửa được đặt chờ rỗng.
  - Ô sửa:
    - `chon` → `<select>` (chuột chọn là xong; bàn phím xong khi Enter / Tab / blur);
    - `ngay` → `<input type="date">` kèm lựa chọn "không hạn" (nút nhỏ);
    - còn lại `<input>`.
  - Tiêu điểm trả về ô sau khi đóng ô sửa bằng `useEffect`, không dùng rAF.
  - Dán: `onPaste` trên bảng khi có ô chọn và không đang sửa → `dan(...)` → `datO` từng ô qua `kiemO`. Ô lỗi không
    nhận, đếm vào thông báo "Đã dán n ô · bỏ qua m ô".
  - Lớp ô:
    - `bdl-cho` (nền `--canh-nen`) khi có trong `cho`;
    - `bdl-lech` (vạch trái 3px `--lien-ket`) khi có trong `lech` và không trong `cho`,
      `title` = "OBC: <hienThi(obc)> · sửa bởi <ai> lúc <gio_tokyo(luc)>";
    - `bdl-khoa` (chữ `--chu-nhat`) khi `sua: false`;
    - `bdl-loi` (viền `--do`) khi 400 báo lỗi ô.
  - Ô lệch có nút nhỏ "↺" (hoặc chuột phải) "Về giá trị OBC": `datO(cho, d, c, obc)`.
- **Lưu**
  - POST `thanLuu(...)` qua hàm gửi JSON có sẵn của `giao_dien/src/api.ts` (xem cách `doi_thu` gửi POST và đọc 400 / 409).
  - 200: xoá `cho` của các ô đã gửi, vá dòng, thông báo "Đã lưu n ô".
  - 400: giữ `cho`, đánh dấu `o_loi`, thông báo `loi`.
  - 403: thông báo.
  - 409: dải "n ô vừa bị đổi ở nơi khác" với hai nút:
    - "Lấy bản mới": bỏ `cho` các ô đó, tải lại;
    - "Ghi đè": vá giá trị máy chủ = `xung_dot[i].gia_tri` vào cache rồi gửi lại cùng `cho`.
- `beforeunload` khi `cho` không rỗng.
- Dòng chú thích dưới bảng:
  - nền vàng = chưa lưu, vạch xanh = đã sửa trên web khác OBC, 🔒 = chỉ xem;
  - "Số tồn đổi mỗi ngày: bản sửa số tồn chỉ giữ tới khi ảnh chụp 在庫一覧 sau ghi khác";
  - ảnh chụp tồn `anh_ton`, lần nạp giá `lan_nap_gia`.
- Số hiển thị qua `dinh_dang.ts`. CSS chỉ dùng token có sẵn (`--canh-nen`, `--lien-ket`, `--do`, `--vien`, `--nen-the`,
  `--nen-phu`, `--chu-nhat`), tiền tố `bdl-`.

- [ ] **Step 1: Test hỏng** (test đọc mã nguồn ở trên) → FAIL.
- [ ] **Step 2: Viết màn.**
- [ ] **Step 3:** `cd giao_dien && npx tsc --noEmit -p . && npx vitest run && npm run build`.
- [ ] **Step 4:** `python -m pytest tests/test_bang_du_lieu.py tests/test_api.py -q` → PASS (gồm `test_ban_build_khop_ma_nguon`).
- [ ] **Step 5: Commit** `feat(bang-du-lieu): man bang tinh Kho du lieu › Bang du lieu`

---

### Task 7: Tài liệu

**Files:**
- Modify: `CLAUDE.md` (CRLF — giữ CRLF):
  - thêm dòng bảng trang `/kho-du-lieu/bang-du-lieu`;
  - thêm khối **Bất biến (072, bản sửa đè OBC — chủ DN chốt 2026-09-30)**: luật hiệu lực một chỗ, bốn view hiệu lực,
    test canh danh mục CSDL + danh sách trắng Python, `chi_nap` gồm sổ sửa, hạng OBC (055) nay là "OBC trừ khi sửa trên web",
    cờ thứ tư, **Migration 072 phải chạy TRƯỚC khi triển khai**;
  - mục "Luật số một" thêm một câu: web không bao giờ ghi `core`; bản sửa ở `app.sua_du_lieu`.
- Modify: `docs/runbook.md` (CRLF) — mục "Triển khai bảng dữ liệu sửa (migration `072`)":
  - chạy migrate bằng postgres;
  - kiểm `meta.schema_migration`;
  - test canh danh mục trên CSDL thật:

```sql
SELECT c.relname FROM pg_class c WHERE c.relnamespace='mart'::regnamespace AND c.relkind='v'
  AND c.relname NOT IN ('dim_customer','dim_product') AND pg_get_viewdef(c.oid) ~ '\mcore\.dim_(customer|product)\M';
```

    phải rỗng;
  - `has_table_privilege('kome_app','app.sua_du_lieu','UPDATE')` = false;
  - cấp cờ `python scripts/tao_nguoi_dung.py quyen <tên> --sua-du-lieu`.
- Chạy `python scripts/sinh_tai_lieu.py` (CLAUDE.md đổi mục "Bẫy đã biết"? Không. Nhưng migration mới → ảnh chụp tài liệu
  đổi) và `python scripts/sinh_cot_dung.py`. Chạy `tests/test_tai_lieu.py tests/test_cot_dung.py`.
- [ ] **Commit** `docs(072): bat bien ban sua de OBC, runbook`
