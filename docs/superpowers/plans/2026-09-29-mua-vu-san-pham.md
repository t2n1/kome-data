# Mùa vụ sản phẩm (`/mua-vu`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Màn `/mua-vu`: treemap ngành → mã đổi liên tục khi kéo thanh thời gian theo ngày (cửa sổ trượt 7/30/90 ngày), ba chỉ số doanh thu / lãi gộp / số lượng.

**Architecture:** Một view mart (`mart.mua_vu_ngay`, mã × ngày) → `kome/mua_vu.py::du_lieu` (1 lượt hỏi, JSON dạng cột) → `GET /api/mua-vu` qua ảnh chụp `chi_nap=True`. Trình duyệt dựng mảng luỹ kế một lần, mỗi nấc kéo tính cửa sổ O(1)/mã, chia ô bằng bản TS của `_squarify` (chạy chung file ca với Python).

**Tech Stack:** Postgres (migration SQL), Python/FastAPI, React + TS + TanStack Query, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-09-29-mua-vu-san-pham-design.md`

## Global Constraints

- OBC chỉ đọc — không UPDATE `core`; migration đã chạy không sửa, chỉ thêm `058_mua_vu.sql`; chạy migration bằng `postgres`.
- View mới đọc bảng bán PHẢI đọc `mart.ban_den_moc` (không `core.fact_sales_line`).
- Mã (`*_code`) là TEXT; số lượng có thập phân; tiền là số nguyên yên.
- Doanh thu thuần = `amount - tax_amount` (đúng cả `uriage` lẫn `meisai`).
- Phí = `mart.la_phi_dieu_chinh(product_code, kind_code)`, xét TRƯỚC POSM = `mart.la_hang_tang(food_category_name)`. Không viết lại vị từ.
- Ngành = `mart.ten_nganh(food_category_name)`; tên = `coalesce(nullif(product_name,''), product_code)`.
- Mọi số trên giao diện qua `giao_dien/src/dinh_dang.ts` (chuẩn Nhật, 万/億).
- `history.replaceState` / điều hướng JS phải bọc `giuKhoang()`.
- Sửa `giao_dien/` ⇒ `cd giao_dien && npm run build` (bản build commit ở `kome/web/spa/`).
- Test chạy trên `DATABASE_URL_TEST` (Postgres local); không chạy song song hai pytest trên `kome_test`.
- Commit kết thúc bằng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File Structure

| File | Trách nhiệm |
|---|---|
| `db/migrations/058_mua_vu.sql` (tạo) | view `mart.mua_vu_ngay` |
| `kome/mua_vu.py` (tạo) | `du_lieu(conn) -> dict` — 1 lượt hỏi, dạng cột |
| `kome/web/api.py` (sửa) | `KHOA_MUA_VU`, `GET /api/mua-vu` |
| `kome/web/app.py` (sửa) | `GET /mua-vu` trả vỏ React |
| `tests/test_mua_vu.py` (tạo) | view + `du_lieu` + API |
| `tests/du_lieu/squarify_ca.json` (tạo) | ca chia ô dùng chung Python/TS |
| `tests/test_squarify_ca.py` (tạo) | Python chạy file ca |
| `giao_dien/src/mua_vu/cay_o.ts` (+ `.test.ts`) | `squarify`, `xep` (hai tầng + không vẽ) |
| `giao_dien/src/mua_vu/du_lieu.ts` (+ `.test.ts`) | kiểu dữ liệu, `LuyKe`, cửa sổ, năm trước |
| `giao_dien/src/mua_vu/ManMuaVu.tsx` | màn: thanh chọn + treemap + không vẽ |
| `giao_dien/src/mua_vu/ThanhThoiGian.tsx` | thanh kéo + biểu đồ nền + mùa + phát |
| `giao_dien/src/mua_vu/mua_vu.css` | kiểu riêng màn |
| `giao_dien/src/main.tsx`, `khung/muc.ts` (sửa) | route + thanh bên |
| `CLAUDE.md`, `scripts/sinh_cot_dung.py`, `kome/web/tai_lieu_sinh.json`, `kome/web/cot_dung_sinh.json` | tài liệu sinh |

---

### Task 1: Migration 058 — `mart.mua_vu_ngay`

**Files:**
- Create: `db/migrations/058_mua_vu.sql`
- Test: `tests/test_mua_vu.py`

**Interfaces:**
- Produces: view `mart.mua_vu_ngay(ma text, ngay date, doanh_thu_thuan numeric, lai_gop numeric, so_luong numeric)`; `ma` ∈ mã OBC ∪ {`'__phi'`, `'__tang'`}.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_mua_vu.py
"""Mùa vụ sản phẩm (/mua-vu, migration 058) — đặc tả 2026-09-29-mua-vu-san-pham-design.md."""
from datetime import date, timedelta

import pytest

from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY

KHACH = "202607010001"


def _hang(conn, batch):
    b = batch(778_101)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, kind_code, kind_name, food_category_name, batch_id)
           VALUES ('XT07', 'Bánh phở', '0', '有形', '食材（常温）＿VNM', %s),
                  ('MKT18', 'Poster', '0', '有形', '雑貨_VNM', %s),
                  ('FEE1', '代引手数料', '1', '無形', '', %s),
                  ('FEE2', 'Phí lạ trong POSM', '1', '無形', '雑貨_VNM', %s)""",
        (b, b, b, b))
    conn.commit()
    _ho_so_khach(conn, batch, KHACH, "Quán A")


def _dong(conn):
    return {(r[0], r[1]): r[2:] for r in conn.execute(
        "SELECT ma, ngay, doanh_thu_thuan, lai_gop, so_luong FROM mart.mua_vu_ngay")}


def test_phi_va_posm_gop_ve_ma_gia_phi_xet_truoc(conn, batch):
    _hang(conn, batch)
    d = HOM_NAY - timedelta(days=2)
    for hang in ("XT07", "MKT18", "FEE1", "FEE2"):
        _mua(conn, batch, KHACH, d, hang=hang)
    _neo(conn, batch)
    dong = _dong(conn)
    assert ("XT07", d) in dong
    assert ("MKT18", d) not in dong and ("FEE1", d) not in dong and ("FEE2", d) not in dong
    assert dong[("__phi", d)][0] == 2 * 100_000       # FEE1 + FEE2 (phí xét trước POSM)
    assert dong[("__tang", d)][0] == 100_000          # MKT18


def test_tong_moi_ngay_KHONG_mat_tien_so_voi_ban_den_moc(conn, batch):
    _hang(conn, batch)
    for i, hang in enumerate(("XT07", "MKT18", "FEE1", "KHONG_CO_MASTER")):
        _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=i), hang=hang)
    _neo(conn, batch)
    a = dict(conn.execute("SELECT ngay, sum(doanh_thu_thuan) FROM mart.mua_vu_ngay GROUP BY 1"))
    b = dict(conn.execute("SELECT sales_date, sum(amount - tax_amount) FROM mart.ban_den_moc GROUP BY 1"))
    assert a == b


def test_cong_theo_thang_BANG_san_pham_theo_thang(conn, batch):
    _hang(conn, batch)
    for i in range(6):
        _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=9 * i), hang="XT07")
    _neo(conn, batch)
    a = {r[0]: r[1:] for r in conn.execute(
        """SELECT to_char(ngay, 'YYYY-MM'), sum(doanh_thu_thuan), sum(lai_gop), sum(so_luong)
           FROM mart.mua_vu_ngay WHERE ma = 'XT07' GROUP BY 1""")}
    b = {r[0]: r[1:] for r in conn.execute(
        """SELECT thang, doanh_thu_thuan, lai_gop, so_luong
           FROM mart.san_pham_theo_thang WHERE product_code = 'XT07'""")}
    assert a == b and a


def test_phieu_do_giu_so_am_va_ma_noi_bo_bi_bo(conn, batch):
    _hang(conn, batch)
    d = HOM_NAY - timedelta(days=1)
    _mua(conn, batch, KHACH, d, tien=-55_000, tax=-5_000, gp=-15_000, hang="XT07")
    _mua(conn, batch, "009000000001", d - timedelta(days=1), hang="XT07")   # nhân viên (044)
    _neo(conn, batch)
    dong = _dong(conn)
    assert dong[("XT07", d)][0] == -50_000
    assert ("XT07", d - timedelta(days=1)) not in dong


def test_moc_lui_cat_dung(conn, batch):
    _hang(conn, batch)
    _mua(conn, batch, KHACH, date(2026, 7, 1), hang="XT07")
    _neo(conn, batch)
    with conn.transaction():
        conn.execute("SELECT set_config('kome.moc', '2026-07-10', true)")
        ngay = {r[0] for r in conn.execute("SELECT ngay FROM mart.mua_vu_ngay")}
    assert max(ngay) <= date(2026, 7, 10)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mua_vu.py -v`
Expected: FAIL — `relation "mart.mua_vu_ngay" does not exist`.

- [ ] **Step 3: Write the migration**

```sql
-- db/migrations/058_mua_vu.sql
-- 058 — Mùa vụ sản phẩm (/mua-vu, đặc tả 2026-09-29-mua-vu-san-pham-design.md).
--
-- Mỗi dòng = một mã × một ngày có bán: doanh thu thuần, lãi gộp, số lượng. Màn kéo
-- thanh thời gian theo NGÀY rồi cộng cửa sổ 7/30/90 ngày ở trình duyệt, nên cần đúng
-- hạt ngày (mart.san_pham_theo_thang là tháng).
--
-- Đọc mart.ban_den_moc (040/044): quay về theo mốc, bỏ mã nội bộ, GIỮ 赤伝 (số âm).
-- Phí & điều chỉnh (048) và hàng tặng POSM (049) không phải sản phẩm: gộp về hai mã
-- giả '__phi' / '__tang' (mã OBC không có '_') để màn in dòng "Không vẽ" — tiền vẫn
-- đủ, Σ mọi dòng một ngày = Σ (amount − tax_amount) của ban_den_moc ngày đó.
-- Phí xét TRƯỚC (cùng thứ tự mart.la_dong_hang_tang). LEFT JOIN: mã bán không có
-- trong master vẫn có dòng, không rơi mất tiền.

CREATE VIEW mart.mua_vu_ngay AS
SELECT CASE WHEN mart.la_phi_dieu_chinh(f.product_code, p.kind_code) THEN '__phi'
            WHEN mart.la_hang_tang(p.food_category_name)             THEN '__tang'
            ELSE f.product_code END          AS ma,
       f.sales_date                          AS ngay,
       sum(f.amount - f.tax_amount)          AS doanh_thu_thuan,
       sum(f.gross_profit)                   AS lai_gop,
       sum(f.qty)                            AS so_luong
FROM mart.ban_den_moc f
LEFT JOIN core.dim_product p ON p.product_code = f.product_code
GROUP BY 1, 2;

GRANT SELECT ON mart.mua_vu_ngay TO kome_app, kome_report, kome_ingest;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mua_vu.py -v`
Expected: 5 PASS. (conftest `apply_all` tự chạy migration mới.) Nếu `test_phieu_do…` báo mã nhân viên vẫn có mặt: kiểm `mart.la_ma_noi_bo('009000000001')` — tiền tố `0090…` là nội bộ theo 044.

- [ ] **Step 5: Commit**

```bash
git add db/migrations/058_mua_vu.sql tests/test_mua_vu.py
git commit -m "feat(mua-vu): migration 058 mart.mua_vu_ngay (ma x ngay, phi/POSM gop ma gia)"
```

---

### Task 2: `kome/mua_vu.py::du_lieu` + `/api/mua-vu` + vỏ `/mua-vu`

**Files:**
- Create: `kome/mua_vu.py`
- Modify: `kome/web/api.py` (hằng khoá gần dòng 229; route ngay sau khối Sản phẩm ~dòng 710), `kome/web/app.py` (sau `/kho-hang` ~dòng 827)
- Test: `tests/test_mua_vu.py`

**Interfaces:**
- Consumes: `mart.mua_vu_ngay` (Task 1).
- Produces: `du_lieu(conn) -> dict` với khoá `ngay_dau: str|None`, `ngay_cuoi: str|None`, `ma: list[{ma, ten, nganh, an}]`, `nganh: list[str]`, `dong: {i: list[int], d: list[int], dt: list[int], lg: list[int], sl: list[float]}`, `phi: int|None`, `tang: int|None`. `GET /api/mua-vu` trả đúng dict đó.

- [ ] **Step 1: Write the failing tests** (thêm vào cuối `tests/test_mua_vu.py`)

```python
from kome import mua_vu as MV


def _web(test_db_url):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    return TestClient(create_app(db_url=test_db_url))


def test_du_lieu_dang_cot_giu_so_0_dau_va_so_thap_phan(conn, batch):
    _hang(conn, batch)
    b = batch(778_202)
    conn.execute("""INSERT INTO core.dim_product (product_code, product_name, kind_code,
                      kind_name, food_category_name, batch_id)
                    VALUES ('000123', 'Mã số 0 đầu', '0', '有形', '調味料_VNM', %s)""", (b,))
    conn.commit()
    _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=3), hang="000123")
    _mua(conn, batch, KHACH, HOM_NAY - timedelta(days=1), hang="FEE1")
    _neo(conn, batch)
    d = MV.du_lieu(conn)
    ma = [m["ma"] for m in d["ma"]]
    assert "000123" in ma and "__phi" in ma
    assert d["phi"] == ma.index("__phi") and d["tang"] is None
    k = ma.index("000123")
    j = d["dong"]["i"].index(k)
    assert d["dong"]["d"][j] == (HOM_NAY - timedelta(days=3) - date.fromisoformat(d["ngay_dau"])).days
    assert isinstance(d["dong"]["sl"][j], float) and isinstance(d["dong"]["dt"][j], int)
    m = d["ma"][k]
    assert m["ten"] == "Mã số 0 đầu" and m["nganh"] == "調味料_VNM" and m["an"] is False
    assert set(d["nganh"]) == {x["nganh"] for x in d["ma"] if x["nganh"]}   # mã giả: nganh ""
    assert len(d["dong"]["i"]) == len(d["dong"]["dt"]) == len(d["dong"]["sl"])


def test_du_lieu_ma_khong_co_master_van_co_ten_va_nganh(conn, batch):
    _ho_so_khach(conn, batch, KHACH, "Quán A")
    _mua(conn, batch, KHACH, HOM_NAY, hang="LA01")
    d = MV.du_lieu(conn)
    m = next(x for x in d["ma"] if x["ma"] == "LA01")
    assert m["ten"] == "LA01" and m["nganh"] == "(chưa phân loại)"


def test_du_lieu_kho_rong(conn):
    d = MV.du_lieu(conn)
    assert d["ngay_dau"] is None and d["ma"] == [] and d["dong"]["i"] == []


def test_du_lieu_DUNG_MOT_luot_hoi(conn, batch, monkeypatch):
    _hang(conn, batch)
    _mua(conn, batch, KHACH, HOM_NAY, hang="XT07")
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    MV.du_lieu(conn)
    assert dem["n"] == 1


def test_trang_va_api_mo_duoc_va_ngan_sach_luot_hoi(conn, batch, test_db_url, monkeypatch):
    import psycopg
    _hang(conn, batch)
    _mua(conn, batch, KHACH, HOM_NAY, hang="XT07")
    c = _web(test_db_url)
    r = c.get("/mua-vu")
    assert r.status_code == 200 and 'id="goc"' in r.text
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    r = c.get("/api/mua-vu")
    assert r.status_code == 200, r.text
    assert r.json()["ma"][0]["ma"]
    assert dem["n"] <= 2, f"/api/mua-vu chạy {dem['n']} lượt hỏi, trần 2"


def test_api_chua_dang_nhap_thi_401_json(test_db_url, monkeypatch):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    monkeypatch.setenv("KOME_SESSION_SECRET", "bi-mat-thu-" + "x" * 32)
    r = TestClient(create_app(db_url=test_db_url)).get("/api/mua-vu", follow_redirects=False)
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/json")
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_mua_vu.py -v -k "du_lieu or api or trang"`
Expected: FAIL — `ModuleNotFoundError: kome.mua_vu`.

- [ ] **Step 3: Implement `kome/mua_vu.py`**

```python
"""Mùa vụ sản phẩm (/mua-vu) — dữ liệu mã × ngày cho treemap kéo theo thời gian.

Đặc tả: docs/superpowers/specs/2026-09-29-mua-vu-san-pham-design.md. Chỉ số ở
mart.mua_vu_ngay (058); ở đây chỉ đổi sang dạng CỘT gọn (~48.000 dòng thật — một
object mỗi dòng là gấp mấy lần cỡ JSON). Cửa sổ 7/30/90 ngày cộng ở trình duyệt
(giao_dien/src/mua_vu/du_lieu.ts) — kéo thanh không hỏi lại máy chủ.
"""
from __future__ import annotations

# Hai mã giả của 058 — phải khớp chữ trong migration.
MA_PHI = "__phi"
MA_TANG = "__tang"

_SQL = """
WITH v AS MATERIALIZED (SELECT * FROM mart.mua_vu_ngay),
dm AS (
    SELECT x.ma,
           CASE x.ma WHEN %(phi)s THEN 'Phí & điều chỉnh'
                     WHEN %(tang)s THEN 'Hàng tặng (POSM)'
                     ELSE coalesce(nullif(p.product_name, ''), x.ma) END AS ten,
           CASE WHEN x.ma IN (%(phi)s, %(tang)s) THEN ''
                ELSE mart.ten_nganh(p.food_category_name) END           AS nganh,
           (x.ma IN (SELECT product_code FROM mart.ma_ngung_ban_an))    AS an
    FROM (SELECT DISTINCT ma FROM v) x
    LEFT JOIN core.dim_product p ON p.product_code = x.ma
)
SELECT (SELECT min(ngay) FROM v), (SELECT max(ngay) FROM v),
       (SELECT coalesce(json_agg(json_build_array(ma, ten, nganh, an) ORDER BY ma), '[]')
          FROM dm),
       (SELECT coalesce(json_agg(json_build_array(ma, ngay, doanh_thu_thuan, lai_gop, so_luong)
                                 ORDER BY ma, ngay), '[]')
          FROM v)
"""


def du_lieu(conn) -> dict:
    """ĐÚNG MỘT lượt hỏi. `dong.d` = số ngày tính từ `ngay_dau`; `dong.i` = chỉ số
    trong `ma`. Tiền là số nguyên, số lượng là số thập phân (bẫy #2)."""
    from datetime import date
    dau, cuoi, ds_ma, ds_dong = conn.execute(_SQL, {"phi": MA_PHI, "tang": MA_TANG}).fetchone()
    ma = [{"ma": m, "ten": t, "nganh": n, "an": bool(a)} for m, t, n, a in ds_ma]
    vi_tri = {m["ma"]: k for k, m in enumerate(ma)}
    dong = {"i": [], "d": [], "dt": [], "lg": [], "sl": []}
    for m, ngay, dt, lg, sl in ds_dong:
        dong["i"].append(vi_tri[m])
        dong["d"].append((date.fromisoformat(ngay) - dau).days)
        dong["dt"].append(int(dt or 0))
        dong["lg"].append(int(lg or 0))
        dong["sl"].append(float(sl or 0))
    return {
        "ngay_dau": dau.isoformat() if dau else None,
        "ngay_cuoi": cuoi.isoformat() if cuoi else None,
        "ma": ma,
        "nganh": sorted({m["nganh"] for m in ma if m["nganh"]}),
        "dong": dong,
        "phi": vi_tri.get(MA_PHI),
        "tang": vi_tri.get(MA_TANG),
    }
```

- [ ] **Step 4: Route API + vỏ React**

Trong `kome/web/api.py`, cạnh `KHOA_DANH_MUC`:

```python
KHOA_MUA_VU = "mua-vu"
```

Sau route `/san-pham/{ma}/ban-them` (cùng hàm dựng router, cùng thụt lề):

```python
    # ---- Mùa vụ sản phẩm (058) -----------------------------------------
    # Không theo khoảng xem: thanh kéo là trục thời gian của chính màn. Chỉ đọc
    # core/mart -> ảnh chụp theo phiên bản NẠP. Trúng: 1 lượt; trượt: 2.
    @r.get("/mua-vu")
    def mua_vu(request: Request):
        from kome import mua_vu as MV
        return _chup(request, KHOA_MUA_VU, MV.du_lieu,
                     "Không đọc được dữ liệu mùa vụ.", chi_nap=True)
```

Trong `kome/web/app.py`, sau `man_kho_hang`:

```python
    # Mùa vụ sản phẩm — dữ liệu qua /api/mua-vu (kome/mua_vu.py -> mart.mua_vu_ngay, 058).
    @app.get("/mua-vu", response_class=HTMLResponse)
    def man_mua_vu(request: Request):
        return _man_khach(request)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_mua_vu.py -v`
Expected: tất cả PASS. Nếu `_chup` gọi `tinh(conn)` với chữ ký khác (vd. `tinh(conn)` vs `tinh(conn, ts)`), đọc `anh_chup.lay` và đổi `MV.du_lieu` cho khớp — `SP.danh_muc` là mẫu đúng. Nếu `date.fromisoformat(ngay)` lỗi vì psycopg trả sẵn `str` hoặc `date` trong JSON: `json_agg` trả chuỗi ISO — giữ `fromisoformat`.

- [ ] **Step 6: Commit**

```bash
git add kome/mua_vu.py kome/web/api.py kome/web/app.py tests/test_mua_vu.py
git commit -m "feat(mua-vu): /api/mua-vu (1 luot hoi, dang cot) + vo React /mua-vu"
```

---

### Task 3: Squarify dùng chung Python ↔ TypeScript

**Files:**
- Create: `tests/du_lieu/squarify_ca.json`, `tests/test_squarify_ca.py`, `giao_dien/src/mua_vu/cay_o.ts`, `giao_dien/src/mua_vu/cay_o.test.ts`

**Interfaces:**
- Consumes: `kome.ve_phan_tich._squarify(gia_tri, x, y, w, h) -> list[(x, y, w, h)]`.
- Produces: `export type O = { x: number; y: number; w: number; h: number }`; `export function squarify(gia_tri: number[], x: number, y: number, w: number, h: number): O[]`.

- [ ] **Step 1: Sinh file ca từ bản Python (một lần, commit file)**

```bash
python - <<'EOF'
import json
from kome.ve_phan_tich import _squarify
ca = []
for ten, g, khung in [
    ("mot_o", [5], (0, 0, 100, 50)),
    ("hai_bang", [1, 1], (0, 0, 100, 100)),
    ("giam_dan", [6, 6, 4, 3, 2, 2, 1], (0, 0, 600, 400)),
    ("khung_doc", [9, 5, 3, 1], (10, 20, 120, 400)),
    ("khong_sap", [2, 7, 1, 4], (0, 0, 300, 200)),
    ("rong", [], (0, 0, 10, 10)),
]:
    ca.append({"ten": ten, "gia_tri": g, "khung": list(khung),
               "o": [list(o) for o in _squarify(g, *khung)]})
open("tests/du_lieu/squarify_ca.json", "w", encoding="utf-8").write(
    json.dumps(ca, ensure_ascii=False, indent=1))
EOF
```

- [ ] **Step 2: Test Python chạy file ca**

```python
# tests/test_squarify_ca.py
"""_squarify (Python, cây ô /bao-cao) và squarify (TS, /mua-vu) chạy CHUNG
tests/du_lieu/squarify_ca.json — sửa một bản là sửa cả hai (cùng nếp luoi_nen_ca.json)."""
import json
from pathlib import Path

import pytest

from kome.ve_phan_tich import _squarify

CA = json.loads((Path(__file__).parent / "du_lieu" / "squarify_ca.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("ca", CA, ids=[c["ten"] for c in CA])
def test_squarify_khop_file_ca(ca):
    o = _squarify(ca["gia_tri"], *ca["khung"])
    assert [list(x) for x in o] == pytest.approx(ca["o"]) if ca["o"] else o == []
```

Run: `pytest tests/test_squarify_ca.py -v` → PASS (6).

- [ ] **Step 3: Viết test TS (fail)**

```ts
// giao_dien/src/mua_vu/cay_o.test.ts
import { describe, expect, it } from "vitest";
import caTho from "../../../tests/du_lieu/squarify_ca.json";
import { squarify } from "./cay_o";

type Ca = { ten: string; gia_tri: number[]; khung: [number, number, number, number]; o: number[][] };
const CA = caTho as unknown as Ca[];

describe("squarify chạy chung file ca với Python", () => {
  for (const ca of CA) it(ca.ten, () => {
    const o = squarify(ca.gia_tri, ...ca.khung).map(r => [r.x, r.y, r.w, r.h]);
    expect(o.length).toBe(ca.o.length);
    o.forEach((r, i) => r.forEach((v, j) => expect(v).toBeCloseTo(ca.o[i][j], 6)));
  });
});
```

Run: `cd giao_dien && npx vitest run src/mua_vu/cay_o.test.ts` → FAIL (không có `./cay_o`).

- [ ] **Step 4: Port sang TS**

```ts
// giao_dien/src/mua_vu/cay_o.ts
// Treemap của màn Mùa vụ (/mua-vu). Hình học tính ở TRÌNH DUYỆT — ngoại lệ có chủ ý
// của nếp "hình học ở Python" (giai đoạn 3): kéo thanh thời gian ~570 nấc thì không
// hỏi máy chủ mỗi nấc được. `squarify` là bản chép của kome/ve_phan_tich.py::_squarify
// (Bruls–Huizing–van Wijk 2000); hai bản chạy CHUNG tests/du_lieu/squarify_ca.json
// (cay_o.test.ts ↔ tests/test_squarify_ca.py) — sửa một bản là sửa cả hai.
export type O = { x: number; y: number; w: number; h: number };

export function squarify(gia_tri: number[], x: number, y: number, w: number, h: number): O[] {
  if (!gia_tri.length) return [];
  if (gia_tri.some(v => !(v > 0))) throw new Error("squarify chỉ nhận giá trị DƯƠNG");
  const tong = gia_tri.reduce((a, b) => a + b, 0);
  const ty_le = (w * h) / tong;
  const dt = gia_tri.map(v => v * ty_le);
  const kq: (O | null)[] = dt.map(() => null);
  let cx = x, cy = y, cw = w, ch = h;

  const xauNhat = (hang: number[], canh: number) => {
    const s_list = hang.map(i => dt[i]);
    const s = s_list.reduce((a, b) => a + b, 0);
    if (s <= 0 || canh <= 0) return Infinity;
    return Math.max((canh * canh * Math.max(...s_list)) / (s * s),
                    (s * s) / (canh * canh * Math.min(...s_list)));
  };
  const datHang = (hang: number[]) => {
    const s = hang.reduce((a, i) => a + dt[i], 0);
    if (cw >= ch) {
      const rong = ch > 0 ? s / ch : 0;
      let yy = cy;
      for (const i of hang) { const hh = rong > 0 ? dt[i] / rong : 0; kq[i] = { x: cx, y: yy, w: rong, h: hh }; yy += hh; }
      cx += rong; cw -= rong;
    } else {
      const cao = cw > 0 ? s / cw : 0;
      let xx = cx;
      for (const i of hang) { const ww = cao > 0 ? dt[i] / cao : 0; kq[i] = { x: xx, y: cy, w: ww, h: cao }; xx += ww; }
      cy += cao; ch -= cao;
    }
  };

  let hang: number[] = [];
  let i = 0;
  while (i < dt.length) {
    const canh = Math.min(cw, ch);
    if (!hang.length) { hang = [i]; i++; continue; }
    const thu = [...hang, i];
    if (xauNhat(hang, canh) >= xauNhat(thu, canh)) { hang = thu; i++; }
    else { datHang(hang); hang = []; }
  }
  if (hang.length) datHang(hang);
  return kq.filter((o): o is O => o !== null);
}
```

- [ ] **Step 5: Run** `cd giao_dien && npx vitest run src/mua_vu/cay_o.test.ts` → PASS (6).

- [ ] **Step 6: Commit**

```bash
git add tests/du_lieu/squarify_ca.json tests/test_squarify_ca.py giao_dien/src/mua_vu/cay_o.ts giao_dien/src/mua_vu/cay_o.test.ts
git commit -m "feat(mua-vu): squarify ban TS chay chung file ca voi Python"
```

---

### Task 4: Tính toán ở trình duyệt — luỹ kế, cửa sổ, năm trước, xếp hai tầng

**Files:**
- Create: `giao_dien/src/mua_vu/du_lieu.ts`, `giao_dien/src/mua_vu/du_lieu.test.ts`
- Modify: `giao_dien/src/mua_vu/cay_o.ts`, `giao_dien/src/mua_vu/cay_o.test.ts`

**Interfaces:**
- Consumes: JSON của `/api/mua-vu` (Task 2), `squarify` (Task 3).
- Produces (du_lieu.ts):
  - `type ChiSo = "dt" | "lg" | "sl"`; `type MaMV = { ma: string; ten: string; nganh: string; an: boolean }`
  - `type DuLieuMV = { ngay_dau: string|null; ngay_cuoi: string|null; ma: MaMV[]; nganh: string[]; dong: { i: number[]; d: number[]; dt: number[]; lg: number[]; sl: number[] }; phi: number|null; tang: number|null }`
  - `class LuyKe { constructor(dl: DuLieuMV); so_ngay: number; so_ma: number; tong(cs: ChiSo, m: number, a: number, b: number): number; tongNgay: Float64Array /* dt mọi mã theo ngày */ }`
  - `function ngayCua(ngay_dau: string, d: number): string` (ISO)
  - `function cuaSo(b: number, n: number): { a: number; b: number; thieu: boolean }` (a kẹp ≥ 0)
  - `function namTruoc(ngay_dau: string, b: number, n: number): { a: number; b: number } | null`
- Produces (cay_o.ts):
  - `type ONganh = O & { n: number; v: number; ma: (O & { m: number; v: number })[] }`
  - `type KhongVe = { phi: number; tang: number; am: number; so_am: number; tat: number }`
  - `function xep(p: { gia_tri: ArrayLike<number>; nganh_cua: number[]; thu_tu_nganh: number[]; tat: Set<number>; phi: number|null; tang: number|null; w: number; h: number }): { nganh: ONganh[]; khong_ve: KhongVe; tong: number }`
    — `nganh_cua[m]` = chỉ số ngành (−1 cho mã giả).

- [ ] **Step 1: Test du_lieu.ts (fail)**

```ts
// giao_dien/src/mua_vu/du_lieu.test.ts
import { describe, expect, it } from "vitest";
import { LuyKe, cuaSo, namTruoc, ngayCua, type DuLieuMV } from "./du_lieu";

const DL: DuLieuMV = {
  ngay_dau: "2025-03-03", ngay_cuoi: "2025-03-10",
  ma: [{ ma: "A", ten: "A", nganh: "X", an: false }, { ma: "B", ten: "B", nganh: "Y", an: false }],
  nganh: ["X", "Y"],
  dong: { i: [0, 0, 1, 0], d: [0, 2, 2, 7], dt: [100, 50, -30, 10], lg: [10, 5, -3, 1], sl: [1.5, 1, -1, 0.25] },
  phi: null, tang: null,
};

describe("LuyKe", () => {
  const L = new LuyKe(DL);
  it("số ngày = ngay_cuoi − ngay_dau + 1", () => expect(L.so_ngay).toBe(8));
  it("tổng cửa sổ = cộng đúng các ngày trong [a, b]", () => {
    expect(L.tong("dt", 0, 0, 7)).toBe(160);
    expect(L.tong("dt", 0, 1, 2)).toBe(50);
    expect(L.tong("dt", 1, 0, 7)).toBe(-30);          // 赤伝 giữ số âm
    expect(L.tong("sl", 0, 0, 7)).toBeCloseTo(2.75);  // số lượng thập phân
  });
  it("a kẹp về 0, b kẹp về so_ngay − 1", () => expect(L.tong("dt", 0, -5, 99)).toBe(160));
  it("tổng theo ngày gồm mọi mã", () => expect(Array.from(L.tongNgay)).toEqual([100, 0, 20, 0, 0, 0, 0, 10]));
});

describe("cửa sổ và năm trước", () => {
  it("ngayCua", () => expect(ngayCua("2025-03-03", 30)).toBe("2025-04-02"));
  it("cửa sổ thiếu ngày đầu", () => expect(cuaSo(5, 30)).toEqual({ a: 0, b: 5, thieu: true }));
  it("cửa sổ đủ", () => expect(cuaSo(40, 30)).toEqual({ a: 11, b: 40, thieu: false }));
  it("năm trước trước dữ liệu → null", () => expect(namTruoc("2025-03-03", 200, 30)).toBeNull());
  it("năm trước cùng ngày lịch", () => {
    // b = 2026-07-15 ⇒ năm trước b' = 2025-07-15
    const b = (Date.UTC(2026, 6, 15) - Date.UTC(2025, 2, 3)) / 864e5;
    const r = namTruoc("2025-03-03", b, 30)!;
    expect(ngayCua("2025-03-03", r.b)).toBe("2025-07-15");
    expect(r.b - r.a + 1).toBe(30);
  });
  it("29/2 lùi về 28/2", () => {
    const b = (Date.UTC(2028, 1, 29) - Date.UTC(2025, 2, 3)) / 864e5;
    expect(ngayCua("2025-03-03", namTruoc("2025-03-03", b, 7)!.b)).toBe("2027-02-28");
  });
});
```

- [ ] **Step 2: Run** `cd giao_dien && npx vitest run src/mua_vu/du_lieu.test.ts` → FAIL.

- [ ] **Step 3: Implement du_lieu.ts**

```ts
// giao_dien/src/mua_vu/du_lieu.ts
// Dữ liệu màn Mùa vụ: /api/mua-vu (kome/mua_vu.py ← mart.mua_vu_ngay, 058) là mã × ngày
// dạng cột. Dựng mảng LUỸ KẾ một lần; tổng một cửa sổ [a, b] = L[b+1] − L[a] — O(1)/mã,
// nên kéo thanh thời gian không hỏi lại máy chủ. Chỉ số KHÔNG định nghĩa ở đây: số của
// từng (mã, ngày) là của mart, ở đây chỉ cộng các ngày.
export type ChiSo = "dt" | "lg" | "sl";
export type MaMV = { ma: string; ten: string; nganh: string; an: boolean };
export type DuLieuMV = {
  ngay_dau: string | null; ngay_cuoi: string | null; ma: MaMV[]; nganh: string[];
  dong: { i: number[]; d: number[]; dt: number[]; lg: number[]; sl: number[] };
  phi: number | null; tang: number | null;
};

const NGAY = 864e5;
const utc = (iso: string) => { const [y, m, d] = iso.split("-").map(Number); return Date.UTC(y, m - 1, d); };
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);

export function ngayCua(ngay_dau: string, d: number): string { return iso(utc(ngay_dau) + d * NGAY); }

export class LuyKe {
  so_ngay: number; so_ma: number;
  tongNgay: Float64Array;
  private L: Record<ChiSo, Float64Array>;
  constructor(dl: DuLieuMV) {
    this.so_ma = dl.ma.length;
    this.so_ngay = dl.ngay_dau && dl.ngay_cuoi ? Math.round((utc(dl.ngay_cuoi) - utc(dl.ngay_dau)) / NGAY) + 1 : 0;
    const w = this.so_ngay + 1;
    this.L = { dt: new Float64Array(this.so_ma * w), lg: new Float64Array(this.so_ma * w), sl: new Float64Array(this.so_ma * w) };
    this.tongNgay = new Float64Array(this.so_ngay);
    const { i, d } = dl.dong;
    for (const cs of ["dt", "lg", "sl"] as ChiSo[]) {
      const a = this.L[cs], v = dl.dong[cs];
      for (let k = 0; k < i.length; k++) a[i[k] * w + d[k] + 1] += v[k];
      for (let m = 0; m < this.so_ma; m++) for (let t = 1; t < w; t++) a[m * w + t] += a[m * w + t - 1];
    }
    for (let k = 0; k < i.length; k++) this.tongNgay[d[k]] += dl.dong.dt[k];
  }
  tong(cs: ChiSo, m: number, a: number, b: number): number {
    const w = this.so_ngay + 1;
    a = Math.max(0, a); b = Math.min(this.so_ngay - 1, b);
    if (b < a) return 0;
    return this.L[cs][m * w + b + 1] - this.L[cs][m * w + a];
  }
}

export function cuaSo(b: number, n: number): { a: number; b: number; thieu: boolean } {
  const a = b - n + 1;
  return { a: Math.max(0, a), b, thieu: a < 0 };
}

// Cùng ngày lịch năm trước (29/2 → 28/2, đúng mart.thang_den_hom_nay). Cửa sổ năm trước
// bắt đầu trước dữ liệu → null ("—"): không so một cửa sổ thiếu ngày.
export function namTruoc(ngay_dau: string, b: number, n: number): { a: number; b: number } | null {
  const [y, m, d] = ngayCua(ngay_dau, b).split("-").map(Number);
  const dd = m === 2 && d === 29 ? 28 : d;
  const b2 = Math.round((Date.UTC(y - 1, m - 1, dd) - utc(ngay_dau)) / NGAY);
  const a2 = b2 - n + 1;
  return a2 < 0 ? null : { a: a2, b: b2 };
}
```

- [ ] **Step 4: Run** du_lieu tests → PASS.

- [ ] **Step 5: Test `xep` (thêm vào cay_o.test.ts, fail)**

```ts
import { xep } from "./cay_o";

describe("xep hai tầng ngành → mã", () => {
  // mã: 0,1 ngành 0 · 2 ngành 1 · 3 ngành 1 (âm) · 4 ngành 2 (tắt) · 5 phí · 6 tặng
  const p = {
    gia_tri: [60, 20, 30, -5, 40, 7, 3], nganh_cua: [0, 0, 1, 1, 2, -1, -1],
    thu_tu_nganh: [1, 0, 2], tat: new Set([2]), phi: 5, tang: 6, w: 400, h: 300,
  };
  const r = xep(p);
  it("đối soát: vẽ + không vẽ = tổng", () => {
    const ve = r.nganh.reduce((s, n) => s + n.v, 0);
    const kv = r.khong_ve;
    expect(ve + kv.phi + kv.tang + kv.am + kv.tat).toBe(r.tong);
    expect(r.tong).toBe(155);
  });
  it("mã ≤ 0 vào khong_ve.am, ngành tắt vào khong_ve.tat, mã giả vào phi/tang", () => {
    expect(r.khong_ve).toEqual({ phi: 7, tang: 3, am: -5, so_am: 1, tat: 40 });
  });
  it("thứ tự ngành cố định theo thu_tu_nganh, không theo giá trị cửa sổ", () => {
    expect(r.nganh.map(n => n.n)).toEqual([1, 0]);
  });
  it("mã trong ngành xếp giảm dần, diện tích tỷ lệ giá trị", () => {
    const n0 = r.nganh.find(n => n.n === 0)!;
    expect(n0.ma.map(m => m.m)).toEqual([0, 1]);
    const dt = (o: { w: number; h: number }) => o.w * o.h;
    expect(dt(n0.ma[0]) / dt(n0.ma[1])).toBeCloseTo(3, 1);
  });
  it("mọi ngành tắt / rỗng → không ô nào, không nổ", () => {
    const r2 = xep({ ...p, tat: new Set([0, 1, 2]) });
    expect(r2.nganh).toEqual([]);
    expect(r2.khong_ve.tat).toBe(150);
  });
});
```

- [ ] **Step 6: Implement `xep` (thêm vào cay_o.ts)**

```ts
export type OMa = O & { m: number; v: number };
export type ONganh = O & { n: number; v: number; ma: OMa[] };
export type KhongVe = { phi: number; tang: number; am: number; so_am: number; tat: number };

// Dải nhãn ngành ở đầu mỗi khối ngành (chỉ khi khối đủ lớn để in chữ).
export const CAO_NHAN = 16;

// Hai tầng: ngành theo THỨ TỰ CỐ ĐỊNH (tổng toàn kỳ — ngành nhảy chỗ là mất dấu), mã
// trong ngành giảm dần theo giá trị cửa sổ. Diện tích ngành = tổng các mã DƯƠNG của nó
// (cùng lý lẽ `doanh_thu_ve` của ve_cay_o): mã ≤ 0 (赤伝) không vẽ được, cộng vào
// khong_ve.am. Bất biến đối soát (có test): Σ ngành.v + phi + tang + am + tat = tong.
export function xep(p: {
  gia_tri: ArrayLike<number>; nganh_cua: number[]; thu_tu_nganh: number[]; tat: Set<number>;
  phi: number | null; tang: number | null; w: number; h: number;
}): { nganh: ONganh[]; khong_ve: KhongVe; tong: number } {
  const kv: KhongVe = { phi: 0, tang: 0, am: 0, so_am: 0, tat: 0 };
  const theo: Map<number, { m: number; v: number }[]> = new Map();
  let tong = 0;
  for (let m = 0; m < p.nganh_cua.length; m++) {
    const v = p.gia_tri[m];
    tong += v;
    if (m === p.phi) { kv.phi += v; continue; }
    if (m === p.tang) { kv.tang += v; continue; }
    const n = p.nganh_cua[m];
    if (p.tat.has(n)) { kv.tat += v; continue; }
    if (!(v > 0)) { if (v !== 0) { kv.am += v; kv.so_am++; } continue; }
    if (!theo.has(n)) theo.set(n, []);
    theo.get(n)!.push({ m, v });
  }
  const thu_tu = p.thu_tu_nganh.filter(n => theo.has(n));
  const tong_n = thu_tu.map(n => theo.get(n)!.reduce((s, x) => s + x.v, 0));
  const o_n = squarify(tong_n, 0, 0, p.w, p.h);
  const nganh: ONganh[] = thu_tu.map((n, k) => {
    const o = o_n[k];
    const ds = theo.get(n)!.sort((a, b) => b.v - a.v);
    const nhan = o.h >= 40 && o.w >= 60 ? CAO_NHAN : 0;
    const x = o.x + 1, y = o.y + 1 + nhan, w = Math.max(0, o.w - 2), h = Math.max(0, o.h - 2 - nhan);
    const o_m = w > 0 && h > 0 ? squarify(ds.map(d => d.v), x, y, w, h) : ds.map(() => ({ x, y, w: 0, h: 0 }));
    return { ...o, n, v: tong_n[k], ma: ds.map((d, j) => ({ ...o_m[j], m: d.m, v: d.v })) };
  });
  return { nganh, khong_ve: kv, tong };
}
```

- [ ] **Step 7: Run** `cd giao_dien && npx vitest run src/mua_vu` → PASS toàn bộ.

- [ ] **Step 8: Commit**

```bash
git add giao_dien/src/mua_vu
git commit -m "feat(mua-vu): luy ke theo ngay, cua so, nam truoc, xep hai tang + doi soat khong ve"
```

---

### Task 5: Màn React `/mua-vu`

**Files:**
- Create: `giao_dien/src/mua_vu/ManMuaVu.tsx`, `giao_dien/src/mua_vu/ThanhThoiGian.tsx`, `giao_dien/src/mua_vu/mua_vu.css`
- Modify: `giao_dien/src/main.tsx` (lazy import + `man()`), `giao_dien/src/khung/muc.ts` (mục thanh bên + chú thích icon TA CHỌN)
- Test: `tests/test_mua_vu.py` (kiểm nguồn tĩnh), build

**Interfaces:**
- Consumes: `lay` (`../api`), `giuKhoang` (`../khung/khoang`), `Khoi` (`../chung/Khoi`, props `tieu_de, phu, cach_tinh, canh_bao, dang_tai, loi, children`), `ONoi`/`DongNoi` (`../chung/ONoi`), `useRong` (`../chung/hooks`), `yen/gon/so_luong/pc/ngay` (`../dinh_dang`), Task 3–4.
- Produces: `export default function ManMuaVu()`; `export function ThanhThoiGian(p: { so_ngay: number; ngay_dau: string; tong_ngay: Float64Array; b: number; n: number; datB: (b: number) => void })`.

- [ ] **Step 1: Test tĩnh (fail)** — thêm vào `tests/test_mua_vu.py`:

```python
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "giao_dien" / "src"


def test_muc_thanh_ben_va_route_co_mat():
    """Trang chạy được mà không có trong thanh điều hướng thì không ai vào được."""
    muc = (_SRC / "khung" / "muc.ts").read_text(encoding="utf-8")
    assert 'url: "/mua-vu"' in muc and "muavu" in muc
    assert '"/mua-vu"' in (_SRC / "main.tsx").read_text(encoding="utf-8")


def test_man_khong_tu_viet_lai_chi_so_va_dung_giu_khoang():
    src = (_SRC / "mua_vu" / "ManMuaVu.tsx").read_text(encoding="utf-8")
    assert "giuKhoang(" in src                       # replaceState qua giuKhoang
    assert "toFixed(" not in src and "de-DE" not in src   # định dạng qua dinh_dang.ts
    assert "/api/mua-vu" in src
```

Run: `pytest tests/test_mua_vu.py -v -k "muc or man_khong"` → FAIL.

- [ ] **Step 2: `ThanhThoiGian.tsx`**

```tsx
// Thanh thời gian của màn Mùa vụ: mỗi nấc = MỘT ngày; vùng tô = cửa sổ N ngày kết thúc ở
// nấc đó. Nền: doanh thu thuần theo ngày (mọi mã) + dải bốn mùa + vạch đầu tháng.
// <input type="range"> gốc lo bàn phím ← → / Home / End và trình đọc màn hình; Shift+← →
// nhảy 7 ngày. ▶ chạy 1 ngày / 80 ms, bấm lại dừng, tới cuối thì dừng.
import { useEffect, useMemo, useRef, useState } from "react";
import { useRong } from "../chung/hooks";
import { ngay } from "../dinh_dang";
import { ngayCua } from "./du_lieu";

const CAO = 56;
const MUA: Record<number, string> = { 3: "xuan", 4: "xuan", 5: "xuan", 6: "he", 7: "he", 8: "he",
  9: "thu", 10: "thu", 11: "thu", 12: "dong", 1: "dong", 2: "dong" };

export function ThanhThoiGian({ so_ngay, ngay_dau, tong_ngay, b, n, datB }: {
  so_ngay: number; ngay_dau: string; tong_ngay: Float64Array; b: number; n: number; datB: (b: number) => void;
}) {
  const [ref, rong] = useRong<HTMLDivElement>();
  const [chay, datChay] = useState(false);
  const bRef = useRef(b); bRef.current = b;

  useEffect(() => {
    if (!chay) return;
    const t = setInterval(() => {
      if (bRef.current >= so_ngay - 1) { datChay(false); return; }
      datB(bRef.current + 1);
    }, 80);
    return () => clearInterval(t);
  }, [chay, so_ngay, datB]);

  const hinh = useMemo(() => {
    if (!rong || !so_ngay) return null;
    const x = (d: number) => (d / Math.max(1, so_ngay - 1)) * rong;
    const max = Math.max(1, ...Array.from(tong_ngay));
    const duong = Array.from(tong_ngay, (v, d) => `${x(d).toFixed(1)},${(CAO - 4 - (Math.max(0, v) / max) * (CAO - 10)).toFixed(1)}`).join(" ");
    const mua: { x: number; w: number; ten: string }[] = [];
    const thang: { x: number; nhan: string }[] = [];
    let dau = 0, ten = "";
    for (let d = 0; d < so_ngay; d++) {
      const [yy, mm, dd] = ngayCua(ngay_dau, d).split("-").map(Number);
      const t = MUA[mm];
      if (t !== ten) { if (ten) mua.push({ x: x(dau), w: x(d) - x(dau), ten }); dau = d; ten = t; }
      if (dd === 1) thang.push({ x: x(d), nhan: mm === 1 ? `${yy}` : `${mm}` });
    }
    mua.push({ x: x(dau), w: x(so_ngay - 1) - x(dau), ten });
    return { x, duong, mua, thang };
  }, [rong, so_ngay, tong_ngay, ngay_dau]);

  const buoc = (k: number) => datB(Math.min(so_ngay - 1, Math.max(0, b + k)));

  return (
    <div className="mv-thanh">
      <div className="mv-nut">
        <button type="button" onClick={() => buoc(-1)} aria-label="Lùi một ngày">◀</button>
        <button type="button" onClick={() => { if (b >= so_ngay - 1) datB(0); datChay(c => !c); }}
                aria-label={chay ? "Dừng" : "Chạy"}>{chay ? "❚❚" : "▶"}</button>
        <button type="button" onClick={() => buoc(1)} aria-label="Tiến một ngày">▶</button>
      </div>
      <div className="mv-truot" ref={ref}>
        {hinh && (
          <svg width={rong} height={CAO} aria-hidden="true" focusable="false">
            {hinh.mua.map((m, k) => <rect key={k} x={m.x} y={0} width={m.w} height={CAO} className={"mv-mua-" + m.ten} />)}
            <rect x={hinh.x(Math.max(0, b - n + 1))} y={0} width={Math.max(2, hinh.x(b) - hinh.x(Math.max(0, b - n + 1)))}
                  height={CAO} className="mv-cua-so" />
            <polyline points={hinh.duong} fill="none" className="mv-duong-ngay" />
            {hinh.thang.map((t, k) => (
              <g key={k}><line x1={t.x} x2={t.x} y1={CAO - 8} y2={CAO} className="mv-vach" />
                <text x={t.x + 2} y={10} className="mv-nhan-thang">{t.nhan}</text></g>
            ))}
          </svg>
        )}
        <input type="range" min={0} max={Math.max(0, so_ngay - 1)} value={b}
               aria-label="Ngày cuối cửa sổ" aria-valuetext={ngay(ngayCua(ngay_dau, b))}
               onChange={e => { datChay(false); datB(Number(e.target.value)); }}
               onKeyDown={e => {
                 if (e.shiftKey && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
                   e.preventDefault(); datChay(false); buoc(e.key === "ArrowLeft" ? -7 : 7);
                 }
               }} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: `ManMuaVu.tsx`**

```tsx
// Màn "Mùa vụ sản phẩm" (/mua-vu, đặc tả 2026-09-29-mua-vu-san-pham-design.md): kéo thanh
// thời gian theo NGÀY, treemap ngành → mã đổi theo cửa sổ N ngày kết thúc ở ngày đó.
// Không theo khoảng xem chung (thanh kéo là trục thời gian riêng). Chỉ số (?cs=) và cửa
// sổ (?n=) nằm trên URL; vị trí thanh kéo thì không.
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { lay } from "../api";
import { useRong } from "../chung/hooks";
import { Khoi } from "../chung/Khoi";
import { DongNoi, ONoi } from "../chung/ONoi";
import { gon, ngay, pc, so_luong, yen } from "../dinh_dang";
import { giuKhoang } from "../khung/khoang";
import { CAO_NHAN, xep } from "./cay_o";
import { LuyKe, cuaSo, namTruoc, ngayCua, type ChiSo, type DuLieuMV } from "./du_lieu";
import { ThanhThoiGian } from "./ThanhThoiGian";
import "./mua_vu.css";

const CHI_SO: { ma: ChiSo; nhan: string }[] = [
  { ma: "dt", nhan: "Doanh thu" }, { ma: "lg", nhan: "Lãi gộp" }, { ma: "sl", nhan: "Số lượng" }];
const CUA_SO = [7, 30, 90];
const CAO_CAY = 460;

const docUrl = () => {
  const q = new URLSearchParams(location.search);
  const cs = (["dt", "lg", "sl"] as ChiSo[]).find(x => x === q.get("cs")) ?? "dt";
  const n = CUA_SO.find(x => String(x) === q.get("n")) ?? 30;
  return { cs, n };
};

const inSo = (cs: ChiSo, v: number) => (cs === "sl" ? so_luong(v) : yen(v));
const inGon = (cs: ChiSo, v: number) => (cs === "sl" ? so_luong(v, 0) : gon(v));

export default function ManMuaVu() {
  const q = useQuery({ queryKey: ["mua-vu"], queryFn: () => lay<DuLieuMV>("/api/mua-vu"), staleTime: 5 * 60e3 });
  const [{ cs, n }, datUrl] = useState(docUrl);
  const [b, datBTho] = useState<number | null>(null);
  const [tat, datTat] = useState<Set<number>>(new Set());
  const [danhDau, datDanhDau] = useState<number | null>(null);
  const [tim, datTim] = useState("");
  const [ref, rong] = useRong<HTMLDivElement>();

  // Gom nhiều cú kéo trong một khung hình thành một lần vẽ lại.
  const raf = useRef(0);
  const datB = useCallback((x: number) => {
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => datBTho(x));
  }, []);

  const doiUrl = (moi: { cs?: ChiSo; n?: number }) => {
    const gt = { cs, n, ...moi };
    datUrl(gt);
    const p = new URLSearchParams(location.search);
    p.set("cs", gt.cs); p.set("n", String(gt.n));
    history.replaceState(null, "", giuKhoang(`${location.pathname}?${p}`));
  };

  const dl = q.data;
  const L = useMemo(() => (dl ? new LuyKe(dl) : null), [dl]);
  const nganhCua = useMemo(() => dl?.ma.map(m => (m.nganh ? dl.nganh.indexOf(m.nganh) : -1)) ?? [], [dl]);
  // Thứ tự ngành cố định: tổng chỉ số trên TOÀN kỳ dữ liệu (không đổi khi kéo).
  const thuTu = useMemo(() => {
    if (!dl || !L) return [];
    const t = dl.nganh.map((_, k) => ({ k, v: 0 }));
    dl.ma.forEach((_, m) => { if (nganhCua[m] >= 0) t[nganhCua[m]].v += Math.max(0, L.tong(cs, m, 0, L.so_ngay - 1)); });
    return t.sort((a, c) => c.v - a.v).map(x => x.k);
  }, [dl, L, cs, nganhCua]);

  useEffect(() => { if (L && b === null) datBTho(L.so_ngay - 1); }, [L, b]);

  const bb = b ?? 0;
  const cua = cuaSo(bb, n);
  const truoc = dl?.ngay_dau ? namTruoc(dl.ngay_dau, bb, n) : null;
  const gia = useMemo(() => (L ? Float64Array.from({ length: L.so_ma }, (_, m) => L.tong(cs, m, cua.a, cua.b)) : new Float64Array()),
    [L, cs, cua.a, cua.b]);
  const cay = useMemo(() => (dl && rong ? xep({ gia_tri: gia, nganh_cua: nganhCua, thu_tu_nganh: thuTu, tat,
    phi: dl.phi, tang: dl.tang, w: rong, h: CAO_CAY }) : null), [dl, rong, gia, nganhCua, thuTu, tat]);

  if (q.isLoading || q.error || !dl || !L) {
    return <Khoi tieu_de="Mùa vụ sản phẩm" dang_tai={q.isLoading} loi={q.error ? String(q.error) : undefined} />;
  }
  if (!L.so_ngay) return <Khoi tieu_de="Mùa vụ sản phẩm" canh_bao="Kho chưa có dòng bán nào." />;

  const kv = cay?.khong_ve;
  const timMa = tim.trim().toLowerCase();
  const goiY = timMa ? dl.ma.map((m, k) => ({ m, k })).filter(({ m, k }) => nganhCua[k] >= 0
    && (m.ma.toLowerCase().includes(timMa) || m.ten.toLowerCase().includes(timMa))).slice(0, 8) : [];

  const canhBao = [
    cua.thieu ? `Cửa sổ chưa đủ ${n} ngày — dữ liệu chỉ có từ ${ngay(dl.ngay_dau)}.` : null,
    !truoc ? "Năm trước chưa có dữ liệu cho cửa sổ này — cột so năm trước in “—”." : null,
  ].filter(Boolean).join(" ");

  const cachTinh = `Mỗi ô = tổng ${n} ngày kết thúc ở ngày đang chọn. Doanh thu thuần (chưa thuế), đã gồm phiếu đỏ (trả hàng, số âm). Không tính mua hàng của nhân viên. Phí & điều chỉnh và hàng tặng không phải sản phẩm nên không vẽ, nhưng tiền vẫn có trong tổng.`
    + (cs === "sl" ? " Số lượng cộng lẫn thùng (ケース) và lẻ (バラ): so MỘT mã qua các mùa là đúng, so kích thước ô giữa hai mã khác nhau thì không." : "");

  return (
    <div className="mv">
      <div className="mv-chon">
        <div className="chip-nhom" role="group" aria-label="Chỉ số">
          {CHI_SO.map(c => <button key={c.ma} type="button" className={"chip" + (c.ma === cs ? " bat" : "")}
            aria-pressed={c.ma === cs} onClick={() => doiUrl({ cs: c.ma })}>{c.nhan}</button>)}
        </div>
        <div className="chip-nhom" role="group" aria-label="Cửa sổ">
          {CUA_SO.map(x => <button key={x} type="button" className={"chip" + (x === n ? " bat" : "")}
            aria-pressed={x === n} onClick={() => doiUrl({ n: x })}>{x} ngày</button>)}
        </div>
        <div className="mv-tim">
          <input type="search" placeholder="Đánh dấu một mã…" value={tim} onChange={e => datTim(e.target.value)}
                 onKeyDown={e => { if (e.key === "Escape") { datTim(""); datDanhDau(null); } }} />
          {goiY.length > 0 && (
            <ul className="mv-goi-y">{goiY.map(({ m, k }) => (
              <li key={m.ma}><button type="button" onClick={() => { datDanhDau(k); datTim(""); }}>{m.ma} · {m.ten}</button></li>))}
            </ul>)}
          {danhDau !== null && <button type="button" className="chip bat" onClick={() => datDanhDau(null)}>
            {dl.ma[danhDau].ma} ✕</button>}
        </div>
      </div>
      <div className="chip-nhom mv-nganh" role="group" aria-label="Ngành">
        {thuTu.map(k => (
          <button key={k} type="button" className={"chip mv-chip-n" + (tat.has(k) ? "" : " bat")} aria-pressed={!tat.has(k)}
            onClick={() => datTat(s => { const t = new Set(s); t.has(k) ? t.delete(k) : t.add(k); return t; })}>
            <i className={"mv-n" + (k % 12)} /> {dl.nganh[k]}
          </button>))}
      </div>

      <Khoi tieu_de={`${n} ngày · ${ngay(ngayCua(dl.ngay_dau!, cua.a))} → ${ngay(ngayCua(dl.ngay_dau!, cua.b))}`}
            phu={cay ? `Tổng ${inSo(cs, cay.tong)}` : undefined} cach_tinh={cachTinh} canh_bao={canhBao || undefined}>
        <div ref={ref} className="mv-cay">
          {cay && (
            <svg width={rong} height={CAO_CAY} role="img" aria-label="Treemap ngành và mã hàng">
              {cay.nganh.map(g => (
                <g key={"n" + g.n}>
                  <rect x={g.x} y={g.y} width={g.w} height={g.h} className={"mv-o-nganh mv-n" + (g.n % 12)} />
                  {g.h >= 40 && g.w >= 60 && <text x={g.x + 4} y={g.y + CAO_NHAN - 4} className="mv-chu-nganh">
                    {dl.nganh[g.n]} · {inGon(cs, g.v)}</text>}
                  {g.ma.map(o => {
                    const m = dl.ma[o.m];
                    const nt = truoc ? L.tong(cs, o.m, truoc.a, truoc.b) : null;
                    const hang = g.ma.indexOf(o) + 1;
                    return (
                      <ONoi key={m.ma} href={m.an ? undefined : giuKhoang(`/san-pham/${encodeURIComponent(m.ma)}`)}
                        nhan={m.ten}
                        noi_dung={<>
                          <b>{m.ten}</b> <span className="mo">{m.ma}</span>
                          <DongNoi nhan="Ngành" gia={m.nganh} />
                          <DongNoi nhan={`${n} ngày này`} gia={inSo(cs, o.v)} />
                          <DongNoi nhan="Cùng kỳ năm trước" gia={nt === null ? "—" : inSo(cs, nt)} />
                          <DongNoi nhan="Hạng trong ngành" gia={`${hang}/${g.ma.length} · ${pc(o.v / g.v)}`} />
                          {m.an && <div className="mo">Đã ngừng kinh doanh — không có trang sản phẩm.</div>}
                        </>}>
                        <g className={"mv-o-ma" + (o.m === danhDau ? " danh-dau" : "")}>
                          <rect x={o.x} y={o.y} width={o.w} height={o.h} />
                          {o.w >= 54 && o.h >= 22 && <text x={o.x + 3} y={o.y + 13} className="mv-chu-ma">
                            {m.ten.length > o.w / 7 ? m.ten.slice(0, Math.max(1, Math.floor(o.w / 7) - 1)) + "…" : m.ten}</text>}
                        </g>
                      </ONoi>);
                  })}
                </g>))}
            </svg>)}
        </div>
        {kv && (kv.phi || kv.tang || kv.am || kv.tat) ? (
          <p className="mv-khong-ve">Không vẽ:
            {kv.phi ? ` phí & điều chỉnh ${inSo(cs, kv.phi)} ·` : ""}
            {kv.tang ? ` hàng tặng ${inSo(cs, kv.tang)} ·` : ""}
            {kv.am ? ` ${kv.so_am} mã ≤ 0 trong cửa sổ ${inSo(cs, kv.am)} ·` : ""}
            {kv.tat ? ` ngành đang tắt ${inSo(cs, kv.tat)}` : ""}
          </p>) : null}
      </Khoi>

      <ThanhThoiGian so_ngay={L.so_ngay} ngay_dau={dl.ngay_dau!} tong_ngay={L.tongNgay} b={bb} n={n} datB={datB} />
    </div>
  );
}
```

Ghi chú khi làm:
- Nếu `ONoi` không bọc được phần tử SVG `<g>` (nó gắn `ref`/sự kiện vào `children`): đọc `chung/ONoi.tsx` dòng 17–90 — `BieuDo` dùng cách nào cho ô SVG thì làm y hệt (vd. truyền `className`/`style` hoặc bọc bằng `<foreignObject>`). Không viết ô nổi thứ hai.
- Tên class `chip`, `chip-nhom`, `bat`: kiểm `giao_dien/src/chung/chung.css` / `kome.css`; dùng class chip đang có ở `san_pham/ManSanPham.tsx` nếu tên khác.
- `Khoi` không có `dang_tai`/`loi` như dự kiến thì đọc `chung/Khoi.tsx:13` và theo đúng props.

- [ ] **Step 4: `mua_vu.css`**

```css
/* Màn Mùa vụ sản phẩm (/mua-vu). Màu ngành: 12 sắc độ cố định, độ bão hoà vừa phải để
   đọc được cả nền sáng lẫn tối (fill-opacity thay vì hai bảng màu). */
.mv{display:flex;flex-direction:column;gap:12px}
.mv-chon{display:flex;flex-wrap:wrap;gap:12px;align-items:center}
.mv-tim{position:relative;display:flex;gap:6px;align-items:center}
.mv-tim input{min-width:220px}
.mv-goi-y{position:absolute;top:100%;left:0;z-index:5;list-style:none;margin:2px 0 0;padding:4px;
  background:var(--nen-the);border:1px solid var(--vien);border-radius:6px;min-width:260px}
.mv-goi-y button{all:unset;display:block;padding:4px 6px;cursor:pointer;width:100%}
.mv-goi-y button:hover,.mv-goi-y button:focus-visible{background:var(--nen-phu)}
.mv-nganh{flex-wrap:wrap}
.mv-chip-n i{display:inline-block;width:10px;height:10px;border-radius:2px}
.mv-chip-n:not(.bat){opacity:.5}
.mv-cay{width:100%;min-height:460px}
.mv-o-nganh{stroke:var(--nen-the);stroke-width:2;fill-opacity:.35}
.mv-o-ma rect{fill:currentColor;fill-opacity:.0;stroke:var(--nen-the);stroke-width:1;
  transition:x .2s,y .2s,width .2s,height .2s}
.mv-o-ma:hover rect{fill-opacity:.18}
.mv-o-ma.danh-dau rect{stroke:var(--chu);stroke-width:3}
.mv-chu-nganh{font-size:12px;font-weight:600;fill:var(--chu)}
.mv-chu-ma{font-size:11px;fill:var(--chu);pointer-events:none}
.mv-o-nganh{transition:x .2s,y .2s,width .2s,height .2s}
@media (prefers-reduced-motion: reduce){.mv-o-ma rect,.mv-o-nganh{transition:none}}
.mv-khong-ve{margin:6px 0 0;color:var(--chu-mo);font-size:12px}
.mv-thanh{display:flex;gap:8px;align-items:center}
.mv-nut{display:flex;gap:4px}
.mv-truot{position:relative;flex:1;height:56px}
.mv-truot svg{position:absolute;inset:0}
.mv-truot input[type=range]{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:pointer}
.mv-truot:focus-within{outline:2px solid var(--lien-ket);outline-offset:2px;border-radius:4px}
.mv-cua-so{fill:var(--lien-ket);fill-opacity:.18;stroke:var(--lien-ket)}
.mv-duong-ngay{stroke:var(--chu-mo);stroke-width:1}
.mv-vach{stroke:var(--vien-dam)}
.mv-nhan-thang{font-size:10px;fill:var(--chu-mo)}
.mv-mua-xuan{fill:hsl(140 40% 55% / .10)} .mv-mua-he{fill:hsl(45 70% 55% / .12)}
.mv-mua-thu{fill:hsl(20 60% 55% / .10)}  .mv-mua-dong{fill:hsl(210 50% 60% / .10)}
.mv-n0{fill:hsl(210 55% 50%);background:hsl(210 55% 50%)} .mv-n1{fill:hsl(28 75% 52%);background:hsl(28 75% 52%)}
.mv-n2{fill:hsl(145 45% 42%);background:hsl(145 45% 42%)} .mv-n3{fill:hsl(355 60% 55%);background:hsl(355 60% 55%)}
.mv-n4{fill:hsl(265 40% 58%);background:hsl(265 40% 58%)} .mv-n5{fill:hsl(20 35% 45%);background:hsl(20 35% 45%)}
.mv-n6{fill:hsl(320 45% 60%);background:hsl(320 45% 60%)} .mv-n7{fill:hsl(0 0% 55%);background:hsl(0 0% 55%)}
.mv-n8{fill:hsl(60 55% 42%);background:hsl(60 55% 42%)}   .mv-n9{fill:hsl(185 55% 42%);background:hsl(185 55% 42%)}
.mv-n10{fill:hsl(240 35% 62%);background:hsl(240 35% 62%)} .mv-n11{fill:hsl(95 35% 50%);background:hsl(95 35% 50%)}
.mv-o-ma{color:var(--chu)}
```

- [ ] **Step 5: Route + thanh bên**

`giao_dien/src/main.tsx` — sau `const KhoHang = …`:

```tsx
const ManMuaVu = lazy(() => import("./mua_vu/ManMuaVu"));
```

trong `man()` sau dòng `/kho-hang`:

```tsx
  if (duong === "/mua-vu") return () => <ManMuaVu />;
```

(`boChon` không liệt kê `/mua-vu` nên trả `{ hien: false }` — đúng đặc tả: màn không theo khoảng xem. Không sửa `boChon`.)

`giao_dien/src/khung/muc.ts` — ngay sau dòng `sanpham`:

```ts
      { ma: "muavu", nhan: "Mùa vụ sản phẩm", url: "/mua-vu", icon: "chart" },
```

và thêm vào chú thích đầu file một dòng: `// "muavu" (Mùa vụ sản phẩm, 2026-09-29) dùng icon "chart" — TA CHỌN trong bộ 24 icon; gói thiết kế không có màn này.`

- [ ] **Step 6: Build + test**

```bash
cd giao_dien && npx tsc --noEmit && npx vitest run && npm run build
```
Rồi: `pytest tests/test_mua_vu.py tests/test_api.py::test_ban_build_khop_ma_nguon -v` → PASS.

- [ ] **Step 7: Kiểm bằng trình duyệt** — `preview_start` (`.claude/launch.json` nếu có cấu hình web app), mở `/mua-vu`: kéo thanh, đổi cửa sổ 7/30/90, đổi chỉ số, tắt một ngành (dòng "Không vẽ" hiện "ngành đang tắt"), đánh dấu một mã, rê một ô (ô nổi có "Cùng kỳ năm trước"), bấm ▶, thử chế độ tối (`resize_window colorScheme: dark`) và bề rộng 375px. `read_console_messages` không có lỗi. Chụp màn hình làm bằng chứng.

- [ ] **Step 8: Commit**

```bash
git add giao_dien/src kome/web/spa tests/test_mua_vu.py
git commit -m "feat(mua-vu): man React /mua-vu — treemap nganh -> ma + thanh thoi gian theo ngay"
```

---

### Task 6: Tài liệu sinh + CLAUDE.md + cả bộ test

**Files:**
- Modify: `scripts/sinh_cot_dung.py` (`MAN`), `CLAUDE.md`, `kome/web/tai_lieu_sinh.json`, `kome/web/cot_dung_sinh.json`

- [ ] **Step 1: Khai mô-đun mới** — trong `scripts/sinh_cot_dung.py::MAN` thêm `"kome/mua_vu.py": ["mua_vu"],`. Nếu script có bảng tên màn (tra `grep -n "san_pham\"" scripts/sinh_cot_dung.py`) thì thêm `"mua_vu": "Mùa vụ sản phẩm (/mua-vu)"` cùng chỗ.

- [ ] **Step 2: Chạy lại hai bộ sinh**

```bash
python scripts/sinh_tai_lieu.py
python scripts/sinh_cot_dung.py
```

- [ ] **Step 3: CLAUDE.md** — thêm một dòng vào bảng "Các trang của web app" (sau `/san-pham/{mã}`):

```
| `/mua-vu` | **Mùa vụ sản phẩm — React** (2026-09-29, đặc tả `2026-09-29-mua-vu-san-pham-design.md`): treemap ngành → mã (mọi mã) theo doanh thu / lãi gộp / số lượng của cửa sổ 7/30/90 ngày (`?cs=` `?n=`) kết thúc ở ngày của thanh kéo theo NGÀY; ô nổi so cùng cửa sổ năm trước; dòng "Không vẽ" (phí · POSM · mã ≤ 0 · ngành tắt). KHÔNG theo khoảng xem. `/api/mua-vu` — MỘT ảnh chụp dạng cột (1 lượt hỏi), cửa sổ cộng ở trình duyệt | `mart.mua_vu_ngay` (058), `core.dim_product`, `mart.ma_ngung_ban_an` |
```

và một mục bất biến (sau bất biến 057/khoảng xem):

```
**Bất biến (058, Mùa vụ sản phẩm — 2026-09-29):** số của từng (mã, ngày) là `mart.mua_vu_ngay` (đọc
`mart.ban_den_moc`; phí → `'__phi'`, POSM → `'__tang'`, phí xét trước; Σ mọi dòng một ngày = Σ doanh thu
thuần của `ban_den_moc` ngày đó). Cửa sổ và cây ô tính ở TRÌNH DUYỆT (`giao_dien/src/mua_vu/`) — ngoại lệ
có chủ ý của nếp "hình học ở Python": kéo ~570 nấc không hỏi máy chủ được. `cay_o.ts::squarify` là bản chép
của `ve_phan_tich._squarify`, hai bản chạy CHUNG `tests/du_lieu/squarify_ca.json` — sửa một bản là sửa cả
hai. Đối soát `Σ ô + phí + tặng + mã ≤ 0 + ngành tắt = tổng cửa sổ` có test (`cay_o.test.ts`). Thứ tự ngành
cố định theo tổng toàn kỳ. Có test canh: `tests/test_mua_vu.py`, `tests/test_squarify_ca.py`.
**Migration 058 phải chạy TRƯỚC khi triển khai.**
```

Sửa CLAUDE.md có đụng mục "Bẫy đã biết"? KHÔNG — nên không phải sinh lại vì nó; nhưng đã chạy `sinh_tai_lieu.py` ở Step 2 vì migration mới.

- [ ] **Step 4: Cả bộ test**

```bash
pytest -q
cd giao_dien && npx vitest run
```
Expected: xanh hết (~4 phút cho pytest). Nếu `tests/test_cot_dung.py` đỏ vì cột của `mua_vu_ngay` chưa phân loại: đọc thông báo, khai theo chỉ dẫn của test (thường là `MAN` hoặc `LUU_RIENG`) rồi chạy lại Step 2.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md scripts/sinh_cot_dung.py kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json
git commit -m "docs(mua-vu): CLAUDE.md + tai lieu sinh cho migration 058"
```

- [ ] **Step 6: Nhắc triển khai** — migration 058 chạy tay trên CSDL thật bằng `postgres` (và INSERT tên file vào `meta.schema_migration` nếu chạy trong SQL editor) TRƯỚC khi đẩy bản Vercel. Không tự chạy trên CSDL thật khi chưa được chủ DN đồng ý.
