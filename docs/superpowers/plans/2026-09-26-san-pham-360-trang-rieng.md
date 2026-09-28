# Sản phẩm 360 — trang riêng: Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến `/san-pham/{mã}` thành trang riêng hai cột kiểu hồ sơ khách 360, có 4 tab tải lười và 10 khối insight mới, liên kết hai chiều với `/khach-hang/{mã}`.

**Architecture:** Chỉ số mới là hàm `mart.sp_*(p_ma)` `LANGUAGE sql STABLE` (migration 051–053) đọc `mart.ban_den_moc`. Mô-đun `kome/san_pham_360.py` gọi các hàm đó: `ho_so` (mở trang, ≤ 5 lượt) và bốn hàm tab (≤ 2–3 lượt). API thêm 4 route con dưới `/api/san-pham/{mã}/`. Giao diện React mới ở `giao_dien/src/san_pham/ho_so/`, dùng lại `BieuDo`, `The`, lớp `.hs2-*`.

**Tech Stack:** PostgreSQL (Supabase), Python 3 + FastAPI + psycopg 3, pytest; React + TypeScript + Vite + TanStack Query; SVG tự vẽ (không thư viện biểu đồ).

**Spec:** `docs/superpowers/specs/2026-09-26-san-pham-360-trang-rieng-design.md`

## Global Constraints

- OBC chỉ đọc: không `UPDATE`/`DELETE` nào trên `core`. Migration chỉ `CREATE OR REPLACE FUNCTION` trong schema `mart`.
- Không sửa migration đã chạy ở CSDL thật (≤ 050). Đang phát triển mà cần sửa 051–053 thì chạy trên `kome_test`: `DELETE FROM meta.schema_migration WHERE filename = '05x_….sql'` rồi chạy lại pytest (hàm là `CREATE OR REPLACE` nên chạy lại an toàn).
- Mọi hàm mới đọc `mart.ban_den_moc`, **không bao giờ** đọc thẳng `core.fact_sales_line` (bất biến 040/044).
- DT thuần luôn là `amount - tax_amount` (bẫy #8). Số lượng là cột `qty`.
- Tỷ suất / đơn giá luôn là **tỷ số của các tổng**, không trung bình tỷ số.
- 赤伝 (dòng số âm) không bị lọc khỏi tổng.
- Cửa sổ "12 tháng" = `sales_date > hom_nay - 365`, `hom_nay` từ `mart.moc_thoi_gian`.
- Nhãn `trang_thai_cap` so bằng (`= 'mua'`), không bao giờ `NOT`.
- Mã tiền là số nguyên yên; mã (`*_code`) là TEXT.
- Không in phần trăm xác suất nào.
- Một view `mart` tham chiếu > 1 lần trong một câu → CTE `AS MATERIALIZED` ghi tường minh.
- Trần lượt hỏi: `/api/san-pham/{mã}` ≤ 5 · `/khach` ≤ 3 · `/thoi-gian` ≤ 2 · `/gia` ≤ 2 · `/ban-them` ≤ 2 · `/khoang` ≤ 2 · `/ngay` 1.
- `kome/web/app.py`/`api.py` không nhập pandas ở mức ngoài cùng.
- Sửa `giao_dien/` ⇒ `cd giao_dien && npm run build` và commit `kome/web/spa/`.
- `kome_test` dùng chung giữa các phiên: không chạy pytest song song với phiên khác; không kill pytest giữa chừng.
- Commit kết thúc bằng dòng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File Structure

| File | Trách nhiệm |
|---|---|
| `db/migrations/051_sp360_khach.sql` (tạo) | `mart.sp_tap_trung_khach`, `sp_theo_tinh`, `sp_theo_nguoi`, `sp_khach_moi_thang` |
| `db/migrations/052_sp360_thoi_gian_gia.sql` (tạo) | `mart.sp_theo_tuan`, `sp_co_don`, `sp_don_gia_thang`, `sp_khach_gia` |
| `db/migrations/053_sp360_ban_them.sql` (tạo) | `mart.sp_mua_kem`, `sp_khach_nen_chao` |
| `tests/test_mart_sp360.py` (tạo) | test tầng SQL của 10 hàm |
| `kome/san_pham_360.py` (tạo) | `ho_so`, `tab_khach`, `tab_thoi_gian`, `tab_gia`, `tab_ban_them`, `CACH_TINH` |
| `kome/san_pham.py` (sửa) | xoá `ho_so()` + dataclass `HoSoSanPham` (chuyển sang mô-đun mới) |
| `kome/web/api.py` (sửa) | `/api/san-pham/{mã}` gọi `SP360.ho_so`; thêm 4 route tab |
| `tests/test_san_pham_360.py` (tạo) | tầng Python + API + trần lượt hỏi |
| `tests/test_san_pham.py` (sửa) | các test dùng `SP.ho_so` chuyển sang `SP360` |
| `giao_dien/src/chung/LuoiTinh.tsx` (tạo) | lưới 47 tỉnh dùng chung + `MAU_O`/`MAU_CHU` |
| `giao_dien/src/khach/BanDo.tsx` (sửa) | nhập `MAU_O`/`MAU_CHU` từ `chung/LuoiTinh` |
| `giao_dien/src/san_pham/ho_so/kieu.ts` (tạo) | kiểu dữ liệu 5 endpoint |
| `giao_dien/src/san_pham/ho_so/HoSoMa.tsx` (tạo) | khung trang: thanh trên, đầu trang, hai cột, ô số, 24 tháng, tab |
| `giao_dien/src/san_pham/ho_so/ViecVoiMa.tsx` (tạo) | cột trái dính |
| `giao_dien/src/san_pham/ho_so/TabKhach.tsx`, `TabThoiGian.tsx`, `TabGia.tsx`, `TabBanThem.tsx` (tạo) | 4 tab |
| `giao_dien/src/san_pham/ho_so/ho_so.css` (tạo) | vài lớp riêng (`.sp3-*`) |
| `giao_dien/src/san_pham/ManSanPham.tsx` (sửa) | bấm dòng → điều hướng; bỏ hồ sơ dưới bảng; nhớ thứ tự danh mục |
| `giao_dien/src/san_pham/HoSoSanPham.tsx` (xoá) | thay bằng `ho_so/` |
| `giao_dien/src/main.tsx` (sửa) | `/san-pham/{mã}` → `HoSoMa` |
| `tests/test_nguon_dung.py`, `tests/test_san_pham.py` (sửa) | test đọc mã nguồn trỏ sang file mới |
| `scripts/sinh_cot_dung.py` (sửa) | khai `kome/san_pham_360.py` vào `MAN` |
| `CLAUDE.md` (sửa) | dòng `/san-pham`, `/san-pham/{mã}` + bất biến 051–053 |

---

### Task 1: Migration 051 — "Ai mua & ở đâu"

**Files:**
- Create: `db/migrations/051_sp360_khach.sql`
- Test: `tests/test_mart_sp360.py`

**Interfaces:**
- Consumes: `mart.ban_den_moc`, `mart.moc_thoi_gian(hom_nay)`, `core.dim_customer`, `core.dim_prefecture(ma_jis, ten, ten_ngan, vung, hang_luoi, cot_luoi)`, `core.dim_salesperson(salesperson_code, ten)`.
- Produces:
  - `mart.sp_tap_trung_khach(p_ma text) RETURNS TABLE(customer_code text, ten text, doanh_thu numeric, ty_trong numeric, luy_ke numeric)` — xếp DT giảm.
  - `mart.sp_theo_tinh(p_ma text) RETURNS TABLE(ma_jis text, ten text, ten_ngan text, vung text, hang_luoi int, cot_luoi int, doanh_thu numeric, so_khach bigint)` — luôn 47 dòng.
  - `mart.sp_theo_nguoi(p_ma text) RETURNS TABLE(salesperson_code text, ten text, doanh_thu numeric, lai_gop numeric, so_khach bigint)`.
  - `mart.sp_khach_moi_thang(p_ma text) RETURNS TABLE(thang text, khach_moi bigint, khach_quay_lai bigint)` — luôn 12 dòng.

- [ ] **Step 1: Kiểm kiểu cột `dim_prefecture` (hang_luoi/cot_luoi là int?)**

Run: `grep -n "CREATE TABLE core.dim_prefecture" -A10 db/migrations/025_ban_do_tinh.sql`
Nếu `hang_luoi`/`cot_luoi`/`ma_jis` khác kiểu trên, sửa kiểu trong `RETURNS TABLE` ở Step 3 cho khớp (hàm SQL trả sai kiểu là lỗi khi CREATE).

- [ ] **Step 2: Viết test thất bại**

Tạo `tests/test_mart_sp360.py`:

```python
"""Tầng SQL của Sản phẩm 360 (migration 051–053): các hàm mart.sp_*(mã).

Mỗi test khoá một bất biến đã ghi trong CLAUDE.md, không chỉ "chạy được"."""
from datetime import timedelta

import pandas as pd

from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY
from tests.test_mart_san_pham import _ban_qty, _san_pham


def _dong(conn, batch, ma_khach, ngay, ma_hang, qty=1, tien=110_000, tax=10_000, gp=30_000,
          phieu=None, dong=1, pack="02", sale="0104"):
    """Một dòng bán đầy đủ tuỳ biến (phiếu, dòng, quy cách, người phụ trách)."""
    from kome.loaders import sales
    b = batch(abs(hash((ma_khach, ngay, ma_hang, phieu, dong, qty))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": phieu or f"D{ma_khach[-4:]}{ngay:%m%d}{ma_hang}", "line_seq": dong,
        "sales_date": ngay, "customer_code": ma_khach, "product_code": ma_hang,
        "salesperson_code": sale, "pack_code": pack, "case_qty": qty, "qty": qty,
        "unit_price": 0, "unit_cost": 0, "amount": tien, "tax_amount": tax,
        "cost": tien - tax - gp, "gross_profit": gp, "paid_amount": 0, "batch_id": b,
    }]), ngay, b)
    conn.commit()


# ------------------------------------------------------------------ 051

def test_tap_trung_gop_theo_KHACH_khong_theo_nguoi_phu_trach(conn, batch):
    """Bất biến tap_trung_khach: một khách đổi người phụ trách giữa kỳ vẫn MỘT dòng."""
    _san_pham(conn, batch, "T1")
    _ho_so_khach(conn, batch, "KT01", "Quán A")
    _dong(conn, batch, "KT01", HOM_NAY - timedelta(days=40), "T1", sale="0102")
    _dong(conn, batch, "KT01", HOM_NAY - timedelta(days=5), "T1", sale="0104")
    _ho_so_khach(conn, batch, "KT02", "Quán B")
    _dong(conn, batch, "KT02", HOM_NAY - timedelta(days=5), "T1", tien=55_000, tax=5_000)
    _neo(conn, batch)
    r = conn.execute("SELECT customer_code, doanh_thu, luy_ke FROM mart.sp_tap_trung_khach('T1')").fetchall()
    assert [x[0] for x in r] == ["KT01", "KT02"]
    assert r[0][1] == 200_000
    assert abs(float(r[1][2]) - 1.0) < 1e-9


def test_theo_tinh_du_47_o_ke_ca_tinh_khong_ai_mua(conn, batch):
    """LEFT JOIN từ dim_prefecture: tỉnh không có khách mua mã này vẫn là một ô 0."""
    _san_pham(conn, batch, "T2")
    _ho_so_khach(conn, batch, "KT03", "Quán Osaka", prefecture="大阪府")
    _dong(conn, batch, "KT03", HOM_NAY - timedelta(days=3), "T2")
    _neo(conn, batch)
    r = conn.execute("SELECT ten, doanh_thu, so_khach FROM mart.sp_theo_tinh('T2')").fetchall()
    assert len(r) == 47
    d = {x[0]: (x[1], x[2]) for x in r}
    assert d["大阪府"] == (100_000, 1)
    assert d["和歌山県"] == (0, 0)


def test_theo_nguoi_giu_ma_ngoai_danh_sach_phu_trach(conn, batch):
    """Nếp FULL JOIN ngân sách: mã phụ trách '0000' không có trong dim_salesperson vẫn có dòng."""
    _san_pham(conn, batch, "T3")
    _ho_so_khach(conn, batch, "KT04", "Quán C")
    _dong(conn, batch, "KT04", HOM_NAY - timedelta(days=3), "T3", sale="0000")
    _neo(conn, batch)
    r = conn.execute("SELECT salesperson_code, ten, doanh_thu FROM mart.sp_theo_nguoi('T3')").fetchall()
    assert r == [("0000", None, 100_000)]


def test_khach_moi_thang_dem_lan_DAU_mua_ma_nay(conn, batch):
    _san_pham(conn, batch, "T4")
    _ho_so_khach(conn, batch, "KT05", "Quán cũ")
    _dong(conn, batch, "KT05", HOM_NAY - timedelta(days=400), "T4")   # lần đầu từ năm trước
    _dong(conn, batch, "KT05", HOM_NAY - timedelta(days=2), "T4")
    _ho_so_khach(conn, batch, "KT06", "Quán mới")
    _dong(conn, batch, "KT06", HOM_NAY - timedelta(days=1), "T4")
    _neo(conn, batch)
    r = conn.execute("SELECT thang, khach_moi, khach_quay_lai FROM mart.sp_khach_moi_thang('T4')").fetchall()
    assert len(r) == 12 and r[-1][0] == f"{HOM_NAY:%Y-%m}"
    assert (r[-1][1], r[-1][2]) == (1, 1)


def test_ma_noi_bo_khong_vao_ham_nao_cua_051(conn, batch):
    """044: 0090…/0099… là nhân viên mua — ban_den_moc đã lọc, hàm mới không được lọt."""
    _san_pham(conn, batch, "T5")
    _dong(conn, batch, "009000000001", HOM_NAY - timedelta(days=3), "T5")
    _neo(conn, batch)
    assert conn.execute("SELECT count(*) FROM mart.sp_tap_trung_khach('T5')").fetchone()[0] == 0
    assert conn.execute("SELECT coalesce(sum(so_khach),0) FROM mart.sp_theo_tinh('T5')").fetchone()[0] == 0
```

- [ ] **Step 3: Chạy test để thấy thất bại**

Run: `pytest tests/test_mart_sp360.py -v`
Expected: FAIL — `function mart.sp_tap_trung_khach(unknown) does not exist`.

- [ ] **Step 4: Viết migration**

Tạo `db/migrations/051_sp360_khach.sql`:

```sql
-- 051 — Sản phẩm 360, nhóm "Ai mua & ở đâu" (đặc tả 2026-09-26-san-pham-360-trang-rieng-design.md §4).
-- Mọi hàm đọc mart.ban_den_moc (bỏ mã nội bộ 044, quay về theo mốc 040). Cửa sổ 12 tháng =
-- sales_date > hom_nay - 365 (cùng cửa sổ mart.hang_doanh_thu). DT thuần = amount - tax_amount.

CREATE OR REPLACE FUNCTION mart.sp_tap_trung_khach(p_ma text)
RETURNS TABLE (customer_code text, ten text, doanh_thu numeric, ty_trong numeric, luy_ke numeric)
LANGUAGE sql STABLE AS $$
    -- Gộp theo KHÁCH (không theo khách × người phụ trách) — nếp mart.tap_trung_khach.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    k AS (
        SELECT f.customer_code, sum(f.amount - f.tax_amount)::numeric AS dt
          FROM mart.ban_den_moc f CROSS JOIN m
         WHERE f.product_code = p_ma AND f.sales_date > m.hom_nay - 365
         GROUP BY f.customer_code
    ),
    t AS (SELECT sum(dt) AS tong FROM k)
    SELECT k.customer_code,
           coalesce(nullif(c.customer_name, ''), k.customer_code),
           k.dt,
           k.dt / nullif(t.tong, 0),
           sum(k.dt) OVER (ORDER BY k.dt DESC, k.customer_code) / nullif(t.tong, 0)
      FROM k CROSS JOIN t
      LEFT JOIN core.dim_customer c ON c.customer_code = k.customer_code AND c.is_current
     ORDER BY k.dt DESC, k.customer_code
$$;

CREATE OR REPLACE FUNCTION mart.sp_theo_tinh(p_ma text)
RETURNS TABLE (ma_jis text, ten text, ten_ngan text, vung text, hang_luoi int, cot_luoi int,
               doanh_thu numeric, so_khach bigint)
LANGUAGE sql STABLE AS $$
    -- LEFT JOIN TỪ dim_prefecture: đủ 47 ô kể cả tỉnh không ai mua (bất biến /ban-do).
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    k AS (
        SELECT c.prefecture, sum(f.amount - f.tax_amount)::numeric AS dt,
               count(DISTINCT f.customer_code) AS n
          FROM mart.ban_den_moc f CROSS JOIN m
          LEFT JOIN core.dim_customer c ON c.customer_code = f.customer_code AND c.is_current
         WHERE f.product_code = p_ma AND f.sales_date > m.hom_nay - 365
         GROUP BY c.prefecture
    )
    SELECT p.ma_jis, p.ten, p.ten_ngan, p.vung, p.hang_luoi, p.cot_luoi,
           coalesce(k.dt, 0), coalesce(k.n, 0)
      FROM core.dim_prefecture p
      LEFT JOIN k ON k.prefecture = p.ten
     ORDER BY p.ma_jis
$$;

CREATE OR REPLACE FUNCTION mart.sp_theo_nguoi(p_ma text)
RETURNS TABLE (salesperson_code text, ten text, doanh_thu numeric, lai_gop numeric, so_khach bigint)
LANGUAGE sql STABLE AS $$
    -- Xuất phát từ DÒNG BÁN, LEFT JOIN tên: mã ngoài dim_salesperson (vd '0000') vẫn có dòng.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian)
    SELECT coalesce(f.salesperson_code, ''), s.ten,
           sum(f.amount - f.tax_amount)::numeric, sum(f.gross_profit)::numeric,
           count(DISTINCT f.customer_code)
      FROM mart.ban_den_moc f CROSS JOIN m
      LEFT JOIN core.dim_salesperson s ON s.salesperson_code = f.salesperson_code
     WHERE f.product_code = p_ma AND f.sales_date > m.hom_nay - 365
     GROUP BY coalesce(f.salesperson_code, ''), s.ten
     ORDER BY 3 DESC, 1
$$;

CREATE OR REPLACE FUNCTION mart.sp_khach_moi_thang(p_ma text)
RETURNS TABLE (thang text, khach_moi bigint, khach_quay_lai bigint)
LANGUAGE sql STABLE AS $$
    -- "Tháng có mua" = (khách, tháng) có DT thuần > 0 (nếp 036). "Mới" = tháng đó là tháng
    -- của lần ĐẦU khách mua mã này (tính trên mọi dữ liệu ≤ mốc). 12 tháng, tháng trống = 0.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    ct AS (
        SELECT f.customer_code, to_char(f.sales_date, 'YYYY-MM') AS thang
          FROM mart.ban_den_moc f
         WHERE f.product_code = p_ma
         GROUP BY 1, 2
        HAVING sum(f.amount - f.tax_amount) > 0
    ),
    dau AS (SELECT customer_code, min(thang) AS thang_dau FROM ct GROUP BY 1),
    g AS (
        SELECT to_char(x, 'YYYY-MM') AS thang
          FROM m, generate_series(date_trunc('month', m.hom_nay) - interval '11 months',
                                  date_trunc('month', m.hom_nay), interval '1 month') AS x
    )
    SELECT g.thang,
           count(ct.customer_code) FILTER (WHERE dau.thang_dau = g.thang),
           count(ct.customer_code) FILTER (WHERE dau.thang_dau < g.thang)
      FROM g
      LEFT JOIN ct ON ct.thang = g.thang
      LEFT JOIN dau ON dau.customer_code = ct.customer_code
     GROUP BY g.thang
     ORDER BY g.thang
$$;
```

- [ ] **Step 5: Chạy test để thấy qua**

Run: `pytest tests/test_mart_sp360.py -v`
Expected: 5 PASS. (conftest tự chạy migration mới trên `kome_test`.)

- [ ] **Step 6: Commit**

```bash
git add db/migrations/051_sp360_khach.sql tests/test_mart_sp360.py
git commit -m "feat(mart): 051 ham san pham 360 nhom khach (tap trung, tinh, nguoi, moi/quay lai)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Migration 052 — "Thời gian" và "Giá & lãi"

**Files:**
- Create: `db/migrations/052_sp360_thoi_gian_gia.sql`
- Test: `tests/test_mart_sp360.py` (thêm)

**Interfaces:**
- Consumes: `_dong` helper (Task 1), `mart.ban_den_moc`, `mart.moc_thoi_gian`.
- Produces:
  - `mart.sp_theo_tuan(p_ma text) RETURNS TABLE(tuan date, so_luong numeric, doanh_thu numeric)` — 26 dòng, `tuan` = thứ Hai.
  - `mart.sp_co_don(p_ma text) RETURNS TABLE(pack_code text, nhom text, thu_tu int, so_dong bigint, so_luong numeric)` — `nhom` ∈ `tra_lai`,`khong_sl`,`1`,`2`,`3–5`,`6–10`,`>10`.
  - `mart.sp_don_gia_thang(p_ma text) RETURNS TABLE(thang text, pack_code text, so_luong numeric, doanh_thu numeric, don_gia numeric)`.
  - `mart.sp_khach_gia(p_ma text) RETURNS TABLE(customer_code text, ten text, pack_code text, so_lan bigint, so_luong numeric, doanh_thu numeric, lai_gop numeric, don_gia numeric, bien numeric)`.

- [ ] **Step 1: Viết test thất bại** — thêm vào cuối `tests/test_mart_sp360.py`:

```python
# ------------------------------------------------------------------ 052

def test_theo_tuan_du_26_tuan_tuan_trong_bang_0(conn, batch):
    _san_pham(conn, batch, "T6")
    _ho_so_khach(conn, batch, "KT07", "Quán D")
    _dong(conn, batch, "KT07", HOM_NAY, "T6", qty=3)
    _neo(conn, batch)
    r = conn.execute("SELECT tuan, so_luong FROM mart.sp_theo_tuan('T6')").fetchall()
    assert len(r) == 26
    assert all(t.isoweekday() == 1 for t, _ in r)
    assert float(r[-1][1]) == 3 and float(r[0][1]) == 0


def test_co_don_dem_dong_TRA_LAI_rieng_khong_loc(conn, batch):
    """赤伝 không bị lọc: dòng âm vào nhóm 'tra_lai'."""
    _san_pham(conn, batch, "T7")
    _ho_so_khach(conn, batch, "KT08", "Quán E")
    _dong(conn, batch, "KT08", HOM_NAY - timedelta(days=9), "T7", qty=4)
    _dong(conn, batch, "KT08", HOM_NAY - timedelta(days=2), "T7", qty=-1, tien=-27_500, tax=-2_500, gp=-7_000)
    _neo(conn, batch)
    r = {(x[0], x[1]): x[3] for x in conn.execute("SELECT * FROM mart.sp_co_don('T7')").fetchall()}
    assert r[("02", "3–5")] == 1 and r[("02", "tra_lai")] == 1


def test_don_gia_la_TY_SO_CAC_TONG(conn, batch):
    """[CRITICAL] 021: trung bình tỷ số bị dòng mẫu số tí hon thổi phồng.
    Hai dòng: 10 đv / ¥100.000 thuần và 1 đv / ¥1.000 thuần.
    Tỷ số các tổng = 101.000 / 11 ≈ 9.181,8; trung bình đơn giá = (10.000 + 1.000)/2 = 5.500."""
    _san_pham(conn, batch, "T8")
    _ho_so_khach(conn, batch, "KT09", "Quán F")
    _dong(conn, batch, "KT09", HOM_NAY - timedelta(days=3), "T8", qty=10, tien=110_000, tax=10_000)
    _dong(conn, batch, "KT09", HOM_NAY - timedelta(days=2), "T8", qty=1, tien=1_100, tax=100)
    _neo(conn, batch)
    r = conn.execute("SELECT don_gia FROM mart.sp_don_gia_thang('T8') WHERE thang = %s AND pack_code = '02'",
                     (f"{HOM_NAY:%Y-%m}",)).fetchone()
    assert abs(float(r[0]) - 101_000 / 11) < 0.01


def test_don_gia_NULL_khi_tong_so_luong_khong_duong(conn, batch):
    _san_pham(conn, batch, "T9")
    _ho_so_khach(conn, batch, "KT10", "Quán G")
    _dong(conn, batch, "KT10", HOM_NAY - timedelta(days=2), "T9", qty=-2, tien=-22_000, tax=-2_000, gp=-5_000)
    _neo(conn, batch)
    r = conn.execute("SELECT don_gia FROM mart.sp_don_gia_thang('T9')").fetchall()
    assert r and r[0][0] is None


def test_khach_gia_chi_khach_DT_duong_va_it_nhat_2_lan(conn, batch):
    _san_pham(conn, batch, "T10")
    _ho_so_khach(conn, batch, "KT11", "Quán hai lần")
    _dong(conn, batch, "KT11", HOM_NAY - timedelta(days=20), "T10", qty=2)
    _dong(conn, batch, "KT11", HOM_NAY - timedelta(days=2), "T10", qty=2)
    _ho_so_khach(conn, batch, "KT12", "Quán một lần")
    _dong(conn, batch, "KT12", HOM_NAY - timedelta(days=2), "T10", qty=2)
    _neo(conn, batch)
    r = conn.execute("SELECT customer_code, so_lan, bien FROM mart.sp_khach_gia('T10')").fetchall()
    assert [x[0] for x in r] == ["KT11"]
    assert r[0][1] == 2 and abs(float(r[0][2]) - 0.3) < 1e-9
```

- [ ] **Step 2: Chạy để thấy thất bại**

Run: `pytest tests/test_mart_sp360.py -v -k "tuan or co_don or don_gia or khach_gia"`
Expected: FAIL — `function mart.sp_theo_tuan(unknown) does not exist`.

- [ ] **Step 3: Viết migration** — tạo `db/migrations/052_sp360_thoi_gian_gia.sql`:

```sql
-- 052 — Sản phẩm 360, nhóm "Thời gian" và "Giá & lãi" (đặc tả §4). Đọc mart.ban_den_moc.

CREATE OR REPLACE FUNCTION mart.sp_theo_tuan(p_ma text)
RETURNS TABLE (tuan date, so_luong numeric, doanh_thu numeric)
LANGUAGE sql STABLE AS $$
    -- 26 tuần ISO (thứ Hai) kết thúc ở tuần chứa mốc; tuần không bán = 0.
    WITH m AS (SELECT date_trunc('week', hom_nay)::date AS t FROM mart.moc_thoi_gian),
    g AS (SELECT (m.t - 7 * i) AS tuan FROM m, generate_series(0, 25) AS i),
    b AS (
        SELECT date_trunc('week', f.sales_date)::date AS tuan,
               sum(f.qty)::numeric AS sl, sum(f.amount - f.tax_amount)::numeric AS dt
          FROM mart.ban_den_moc f CROSS JOIN m
         WHERE f.product_code = p_ma AND f.sales_date >= m.t - 7 * 25
         GROUP BY 1
    )
    SELECT g.tuan, coalesce(b.sl, 0), coalesce(b.dt, 0)
      FROM g LEFT JOIN b USING (tuan)
     ORDER BY g.tuan
$$;

CREATE OR REPLACE FUNCTION mart.sp_co_don(p_ma text)
RETURNS TABLE (pack_code text, nhom text, thu_tu int, so_dong bigint, so_luong numeric)
LANGUAGE sql STABLE AS $$
    -- Phân bố SL mỗi dòng bán theo quy cách, 12 tháng. Dòng âm (赤伝) KHÔNG lọc: nhóm 'tra_lai'.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    d AS (
        SELECT f.pack_code, f.qty,
               CASE WHEN f.qty < 0 THEN 'tra_lai' WHEN f.qty = 0 THEN 'khong_sl'
                    WHEN f.qty <= 1 THEN '1' WHEN f.qty <= 2 THEN '2'
                    WHEN f.qty <= 5 THEN '3–5' WHEN f.qty <= 10 THEN '6–10' ELSE '>10' END AS nhom,
               CASE WHEN f.qty < 0 THEN 7 WHEN f.qty = 0 THEN 6
                    WHEN f.qty <= 1 THEN 1 WHEN f.qty <= 2 THEN 2
                    WHEN f.qty <= 5 THEN 3 WHEN f.qty <= 10 THEN 4 ELSE 5 END AS thu_tu
          FROM mart.ban_den_moc f CROSS JOIN m
         WHERE f.product_code = p_ma AND f.sales_date > m.hom_nay - 365
    )
    SELECT pack_code, nhom, thu_tu, count(*), sum(qty)::numeric
      FROM d GROUP BY pack_code, nhom, thu_tu
     ORDER BY pack_code, thu_tu
$$;

CREATE OR REPLACE FUNCTION mart.sp_don_gia_thang(p_ma text)
RETURNS TABLE (thang text, pack_code text, so_luong numeric, doanh_thu numeric, don_gia numeric)
LANGUAGE sql STABLE AS $$
    -- Đơn giá thực = Σ DT thuần / Σ qty theo (tháng, quy cách) — TỶ SỐ CÁC TỔNG, không
    -- trung bình unit_price. Σ qty ≤ 0 (tháng toàn trả lại) -> NULL. 12 tháng lịch tới mốc.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian)
    SELECT to_char(f.sales_date, 'YYYY-MM'), f.pack_code,
           sum(f.qty)::numeric, sum(f.amount - f.tax_amount)::numeric,
           CASE WHEN sum(f.qty) > 0 THEN sum(f.amount - f.tax_amount)::numeric / sum(f.qty) END
      FROM mart.ban_den_moc f CROSS JOIN m
     WHERE f.product_code = p_ma
       AND f.sales_date >= (date_trunc('month', m.hom_nay) - interval '11 months')::date
     GROUP BY 1, 2
     ORDER BY 1, 2
$$;

CREATE OR REPLACE FUNCTION mart.sp_khach_gia(p_ma text)
RETURNS TABLE (customer_code text, ten text, pack_code text, so_lan bigint, so_luong numeric,
               doanh_thu numeric, lai_gop numeric, don_gia numeric, bien numeric)
LANGUAGE sql STABLE AS $$
    -- Theo khách, 12 tháng. Chỉ khách DT thuần > 0 VÀ ≥ 2 ngày mua (tránh mẫu số tí hon do
    -- 赤伝 — bài học 021). Đơn giá tính trên quy cách phổ biến nhất của mã (nhiều dòng nhất),
    -- biên = Σ lãi gộp / Σ DT thuần. Cả hai là tỷ số các tổng.
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    f AS MATERIALIZED (
        SELECT b.customer_code, b.sales_date, b.pack_code, b.qty,
               b.amount - b.tax_amount AS dt, b.gross_profit
          FROM mart.ban_den_moc b CROSS JOIN m
         WHERE b.product_code = p_ma AND b.sales_date > m.hom_nay - 365
    ),
    q AS (SELECT f.pack_code FROM f GROUP BY f.pack_code ORDER BY count(*) DESC, f.pack_code LIMIT 1),
    k AS (
        SELECT f.customer_code,
               count(DISTINCT f.sales_date) AS so_lan,
               sum(f.dt)::numeric AS dt, sum(f.gross_profit)::numeric AS lg,
               sum(f.qty) FILTER (WHERE f.pack_code = (SELECT pack_code FROM q))::numeric AS sl_q,
               sum(f.dt)  FILTER (WHERE f.pack_code = (SELECT pack_code FROM q))::numeric AS dt_q
          FROM f GROUP BY f.customer_code
    )
    SELECT k.customer_code, coalesce(nullif(c.customer_name, ''), k.customer_code),
           (SELECT pack_code FROM q), k.so_lan, k.sl_q, k.dt, k.lg,
           CASE WHEN k.sl_q > 0 THEN k.dt_q / k.sl_q END,
           k.lg / k.dt
      FROM k
      LEFT JOIN core.dim_customer c ON c.customer_code = k.customer_code AND c.is_current
     WHERE k.dt > 0 AND k.so_lan >= 2
     ORDER BY k.lg / k.dt, k.customer_code
$$;
```

- [ ] **Step 4: Chạy test để thấy qua**

Run: `pytest tests/test_mart_sp360.py -v`
Expected: 10 PASS.

- [ ] **Step 5: Commit**

```bash
git add db/migrations/052_sp360_thoi_gian_gia.sql tests/test_mart_sp360.py
git commit -m "feat(mart): 052 ham san pham 360 thoi gian va gia (tuan, co don, don gia, khach gia)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Migration 053 — "Bán thêm"

**Files:**
- Create: `db/migrations/053_sp360_ban_them.sql`
- Test: `tests/test_mart_sp360.py` (thêm)

**Interfaces:**
- Consumes: `_dong` (Task 1); `mart.khong_phai_hang(product_code, kind_code, food_category_name)`, `mart.ma_ngung_ban_an(product_code)`, `mart.la_ngung_ban(rank_code, product_name)`, `mart.ten_nganh(food_category_name, product_code, kind_code)`, `mart.khach_mat_hang(customer_code, product_code, lan_cuoi, trang_thai_cap, …)`.
- Produces:
  - `mart.sp_mua_kem(p_ma text) RETURNS TABLE(product_code text, ten_hang text, so_phieu bigint, ty_le numeric, tong_phieu bigint)` — top 15.
  - `mart.sp_khach_nen_chao(p_ma text) RETURNS TABLE(customer_code text, ten text, nganh text, doanh_thu_nganh numeric, so_ma_nganh bigint, lan_cuoi date)`.

- [ ] **Step 1: Xem cách test cũ gieo mã phí/POSM/※終売※**

Run: `grep -n "def _\|kind_code\|food_category_name\|rank_code" tests/test_phi_dieu_chinh.py tests/test_hang_tang.py tests/test_ngung_ban.py | head -40`
Dùng đúng cách chèn `core.dim_product` của các file đó cho helper `_sp_du` dưới đây (nếu tên cột khác, sửa helper cho khớp).

- [ ] **Step 2: Viết test thất bại** — thêm vào cuối `tests/test_mart_sp360.py`:

```python
# ------------------------------------------------------------------ 053

def _sp_du(conn, batch, ma, ten="Hàng", nganh="米_VNM", kind="0", rank=None):
    """dim_product có ngành / loại / hạng — cần cho mua kèm và khách nên chào."""
    b = batch(abs(hash(("spd", ma))) % 60_000 + 1)
    conn.execute(
        """INSERT INTO core.dim_product (product_code, product_name, kind_code, kind_name,
                                         food_category_name, rank_code, batch_id)
           VALUES (%s, %s, %s, 'x', %s, %s, %s) ON CONFLICT (product_code) DO NOTHING""",
        (ma, ten, kind, nganh, rank, b))
    conn.commit()


def test_mua_kem_bo_phi_POSM_va_hang_ngung_ban_het_ton(conn, batch):
    _sp_du(conn, batch, "M1")
    _sp_du(conn, batch, "M2", ten="Bánh")
    _sp_du(conn, batch, "PHI", ten="配送料", kind="1")
    _sp_du(conn, batch, "MKT1", ten="Poster", nganh="雑貨_VNM")
    _sp_du(conn, batch, "OLD", ten="※終売※ cũ", rank="0999")
    _ho_so_khach(conn, batch, "KM01", "Quán H")
    ngay = HOM_NAY - timedelta(days=3)
    for i, ma in enumerate(["M1", "M2", "PHI", "MKT1", "OLD"], start=1):
        _dong(conn, batch, "KM01", ngay, ma, phieu="P-KEM-1", dong=i)
    _dong(conn, batch, "KM01", ngay - timedelta(days=7), "M1", phieu="P-KEM-2", dong=1)
    _neo(conn, batch)
    r = conn.execute("SELECT product_code, so_phieu, ty_le, tong_phieu FROM mart.sp_mua_kem('M1')").fetchall()
    assert [x[0] for x in r] == ["M2"]
    assert r[0][1] == 1 and r[0][3] == 2 and abs(float(r[0][2]) - 0.5) < 1e-9


def test_khach_nen_chao_cung_nganh_chua_mua_khong_co_khach_dong_cua(conn, batch):
    _sp_du(conn, batch, "C1", nganh="米_VNM")
    _sp_du(conn, batch, "C2", nganh="米_VNM")
    _sp_du(conn, batch, "X9", nganh="麺_VNM")
    # KC01: mua đều C2 (cùng ngành), chưa mua C1 -> NÊN CHÀO
    _ho_so_khach(conn, batch, "KC01", "Quán mua gạo")
    for i in range(3):
        _dong(conn, batch, "KC01", HOM_NAY - timedelta(days=i * 7), "C2")
    # KC02: đã mua C1 -> không chào
    _ho_so_khach(conn, batch, "KC02", "Quán đã mua")
    for i in range(3):
        _dong(conn, batch, "KC02", HOM_NAY - timedelta(days=i * 7), "C2")
    _dong(conn, batch, "KC02", HOM_NAY - timedelta(days=1), "C1")
    # KC03: ※廃業※ -> nhãn 'khong_goi', không chào
    _ho_so_khach(conn, batch, "KC03", "※廃業※ Quán đóng cửa")
    for i in range(3):
        _dong(conn, batch, "KC03", HOM_NAY - timedelta(days=i * 7), "C2")
    # KC04: chỉ mua ngành khác -> không chào
    _ho_so_khach(conn, batch, "KC04", "Quán mì")
    for i in range(3):
        _dong(conn, batch, "KC04", HOM_NAY - timedelta(days=i * 7), "X9")
    _neo(conn, batch)
    r = conn.execute("SELECT customer_code, so_ma_nganh FROM mart.sp_khach_nen_chao('C1')").fetchall()
    assert r == [("KC01", 1)]


def test_khach_nen_chao_RONG_voi_ma_ngung_kinh_doanh(conn, batch):
    """050: không chào hàng đã ngừng kinh doanh — kể cả còn tồn."""
    _sp_du(conn, batch, "N1", ten="※終売※ gạo", nganh="米_VNM", rank="0999")
    _sp_du(conn, batch, "N2", nganh="米_VNM")
    _ho_so_khach(conn, batch, "KN01", "Quán I")
    for i in range(3):
        _dong(conn, batch, "KN01", HOM_NAY - timedelta(days=i * 7), "N2")
    _neo(conn, batch)
    assert conn.execute("SELECT count(*) FROM mart.sp_khach_nen_chao('N1')").fetchone()[0] == 0
```

- [ ] **Step 3: Chạy để thấy thất bại**

Run: `pytest tests/test_mart_sp360.py -v -k "mua_kem or nen_chao"`
Expected: FAIL — `function mart.sp_mua_kem(unknown) does not exist`.

- [ ] **Step 4: Viết migration** — tạo `db/migrations/053_sp360_ban_them.sql`:

```sql
-- 053 — Sản phẩm 360, nhóm "Bán thêm" (đặc tả §4). Đọc mart.ban_den_moc / mart.khach_mat_hang.

CREATE OR REPLACE FUNCTION mart.sp_mua_kem(p_ma text)
RETURNS TABLE (product_code text, ten_hang text, so_phieu bigint, ty_le numeric, tong_phieu bigint)
LANGUAGE sql STABLE AS $$
    -- Trong các phiếu (slip_no) 12 tháng có dòng MUA (qty > 0) mã này: mỗi mã khác có dòng mua
    -- trên bao nhiêu phiếu đó. Bỏ phí / POSM (khong_phai_hang, 048/049) và mã ※終売※ hết tồn (050).
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    p AS MATERIALIZED (
        SELECT DISTINCT f.slip_no
          FROM mart.ban_den_moc f CROSS JOIN m
         WHERE f.product_code = p_ma AND f.qty > 0 AND f.sales_date > m.hom_nay - 365
    ),
    t AS (SELECT count(*) AS n FROM p),
    k AS (
        SELECT f.product_code, count(DISTINCT f.slip_no) AS so_phieu
          FROM mart.ban_den_moc f JOIN p ON p.slip_no = f.slip_no
         WHERE f.product_code <> p_ma AND f.qty > 0
         GROUP BY f.product_code
    )
    SELECT k.product_code, coalesce(nullif(d.product_name, ''), k.product_code),
           k.so_phieu, k.so_phieu::numeric / nullif(t.n, 0), t.n
      FROM k CROSS JOIN t
      LEFT JOIN core.dim_product d ON d.product_code = k.product_code
     WHERE NOT mart.khong_phai_hang(k.product_code, d.kind_code, d.food_category_name)
       AND NOT EXISTS (SELECT 1 FROM mart.ma_ngung_ban_an a WHERE a.product_code = k.product_code)
     ORDER BY k.so_phieu DESC, k.product_code
     LIMIT 15
$$;

CREATE OR REPLACE FUNCTION mart.sp_khach_nen_chao(p_ma text)
RETURNS TABLE (customer_code text, ten text, nganh text, doanh_thu_nganh numeric,
               so_ma_nganh bigint, lan_cuoi date)
LANGUAGE sql STABLE AS $$
    -- Khách đang mua đều (trang_thai_cap = 'mua', so BẰNG — 024) ≥ 1 mã CÙNG NGÀNH, chưa từng có
    -- dòng với mã này (≤ mốc). ※廃業※ mang 'khong_goi' nên tự rơi ra. Mã ※終売※ (kể cả còn tồn),
    -- ngành chưa phân loại / phí / POSM -> rỗng. Xếp theo DT thuần ngành đó 12 tháng.
    -- LATERAL `= mã` cho khach_mat_hang: `= ANY`/JOIN không đẩy vị từ qua nhip_mat_hang (đo thật ở
    -- /lien-he: 2 s -> 0,1 s).
    WITH m AS (SELECT hom_nay FROM mart.moc_thoi_gian),
    sp AS (
        SELECT mart.ten_nganh(d.food_category_name, d.product_code, d.kind_code) AS nganh,
               mart.la_ngung_ban(d.rank_code, d.product_name) AS ngung
          FROM core.dim_product d WHERE d.product_code = p_ma
    ),
    cung AS (
        SELECT d.product_code
          FROM core.dim_product d CROSS JOIN sp
         WHERE d.product_code <> p_ma
           AND mart.ten_nganh(d.food_category_name, d.product_code, d.kind_code) = sp.nganh
           AND NOT sp.ngung
           AND sp.nganh NOT IN ('(chưa phân loại)', 'Phí & điều chỉnh', 'Hàng tặng (POSM)')
    ),
    k AS (
        SELECT h.customer_code, count(*) AS so_ma, max(h.lan_cuoi) AS lan_cuoi
          FROM cung
          CROSS JOIN LATERAL (
              SELECT x.customer_code, x.lan_cuoi FROM mart.khach_mat_hang x
               WHERE x.product_code = cung.product_code AND x.trang_thai_cap = 'mua') h
         GROUP BY h.customer_code
    ),
    dt AS (
        SELECT f.customer_code, sum(f.amount - f.tax_amount)::numeric AS dt
          FROM mart.ban_den_moc f CROSS JOIN m
          JOIN cung ON cung.product_code = f.product_code
         WHERE f.sales_date > m.hom_nay - 365
           AND f.customer_code IN (SELECT customer_code FROM k)
         GROUP BY f.customer_code
    )
    SELECT k.customer_code, coalesce(nullif(c.customer_name, ''), k.customer_code),
           sp.nganh, coalesce(dt.dt, 0), k.so_ma, k.lan_cuoi
      FROM k CROSS JOIN sp
      LEFT JOIN dt ON dt.customer_code = k.customer_code
      LEFT JOIN core.dim_customer c ON c.customer_code = k.customer_code AND c.is_current
     WHERE NOT EXISTS (SELECT 1 FROM mart.ban_den_moc f
                        WHERE f.customer_code = k.customer_code AND f.product_code = p_ma)
     ORDER BY coalesce(dt.dt, 0) DESC, k.customer_code
$$;
```

Kiểm chuỗi `'(chưa phân loại)'` đúng y hệt `kome.bao_cao.NGANH_TRONG` (`grep -n "NGANH_TRONG =" kome/bao_cao.py`); lệch một ký tự thì sửa trong SQL.

- [ ] **Step 5: Chạy test để thấy qua**

Run: `pytest tests/test_mart_sp360.py -v`
Expected: 13 PASS.

- [ ] **Step 6: Commit**

```bash
git add db/migrations/053_sp360_ban_them.sql tests/test_mart_sp360.py
git commit -m "feat(mart): 053 ham san pham 360 ban them (mua kem, khach nen chao)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `kome/san_pham_360.py::ho_so` + đổi `/api/san-pham/{mã}`

**Files:**
- Create: `kome/san_pham_360.py`
- Modify: `kome/san_pham.py` (xoá `ho_so()` dòng ~338-480 và dataclass `HoSoSanPham`; GIỮ `la_ma_ngung_ban_an`, `_COT`, `_sp`, `_so`, `LOAI_HAN`, `QUY_CACH`)
- Modify: `kome/web/api.py:549-576` (route `sp_ho_so`)
- Create: `tests/test_san_pham_360.py`
- Modify: `tests/test_san_pham.py` (test dùng `SP.ho_so`)

**Interfaces:**
- Consumes: `SP._COT`, `SP._sp(row) -> SanPham`, `SP._so`, `SP.LOAI_HAN`, `SP.QUY_CACH`, `mart.sp_khach_nen_chao` (Task 3).
- Produces:
  - `SP360.ho_so(conn, ma: str) -> dict | None` với khoá: `sp` (SanPham), `nganh` (str), `hom_nay` (date), `thang` (list[{thang, so_luong, doanh_thu, lai_gop, dt_nam_truoc}] — 24 tháng lịch kết thúc tháng của mốc, tháng trống = 0), `ton` (list — như `ton` cũ), `mua_lai` (list[{ma, ten, du_kien, con, nhip, lan_cuoi, doanh_thu}] ≤ 10), `mua_lai_tong` (int), `nen_chao` (list[{ma, ten, doanh_thu_nganh, so_ma_nganh, lan_cuoi}] ≤ 5), `nen_chao_tong` (int), `so_dang_mua` (int), `so_da_ngung` (int), `cach_tinh` (dict = `CACH_TINH`).
  - `SP360._ton_lo(conn, ma) -> list[dict]`, `SP360._khach_dang_ngung(conn, ma) -> tuple[list, list]`, `SP360._bac_gia(conn, ma) -> list[dict]` (Task 5 dùng).
  - `SP360.CACH_TINH: dict[str, str]`.

- [ ] **Step 1: Viết test thất bại** — tạo `tests/test_san_pham_360.py`:

```python
"""Tầng Python + API của Sản phẩm 360 (kome/san_pham_360.py)."""
from datetime import timedelta

import pytest

from kome import khach_hang as KH
from kome import ho_so_khach as HSK
from kome import san_pham_360 as SP360
from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY
from tests.test_mart_san_pham import _san_pham, _ton
from tests.test_san_pham import _dem_truy_van, _gia, _khach_web


def _gieo_mot_ma(conn, batch, ma="Q1"):
    _san_pham(conn, batch, ma, ten="Gạo thử 360")
    _ton(conn, batch, ma, sl=300)
    _ho_so_khach(conn, batch, "KQ01", "Quán đều")
    for i in range(4):
        _mua(conn, batch, "KQ01", HOM_NAY - timedelta(days=i * 7), hang=ma)
    _gia(conn, batch, ma, "03", 5250)
    _neo(conn, batch)


def test_ho_so_khong_co_ma_tra_None(conn, batch):
    _neo(conn, batch)
    assert SP360.ho_so(conn, "KHONG-CO") is None


def test_ho_so_khong_qua_5_truy_van_va_khong_rong(conn, batch, monkeypatch):
    _gieo_mot_ma(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    h = SP360.ho_so(conn, "Q1")
    assert h is not None and h["sp"].ma == "Q1"
    assert dem["n"] <= 5, f"ho_so() chạy {dem['n']} truy vấn"


def test_ho_so_24_thang_co_cot_nam_truoc(conn, batch):
    _gieo_mot_ma(conn, batch)
    t = SP360.ho_so(conn, "Q1")["thang"]
    assert len(t) == 24 and t[-1]["thang"] == f"{HOM_NAY:%Y-%m}"
    assert t[-1]["doanh_thu"] > 0
    assert t[-1]["dt_nam_truoc"] == t[-13]["doanh_thu"]


def test_mua_lai_TRUNG_TAP_voi_lich_mua_cua_ho_so_khach(conn, batch):
    """[CRITICAL] Một khái niệm hai chiều: cặp (khách, mã) nằm ở "khách đến ngày mua lại"
    của mã khi và chỉ khi mã nằm ở "Mã đến ngày mua lại" (lich_mua) của khách."""
    _gieo_mot_ma(conn, batch)
    h = SP360.ho_so(conn, "Q1")
    ma_khach = {x["ma"] for x in h["mua_lai"]}
    kh = KH.ho_so(conn, "KQ01")
    lich = HSK.lich_mua(kh.tat_ca_mat_hang, HOM_NAY)   # đúng lời gọi của ho_so_khach.py:154
    co_q1 = any(m["ma"] == "Q1" for m in lich["ma"])
    assert ("KQ01" in ma_khach) == co_q1
    assert co_q1, "gieo hỏng: KQ01 mua 4 lần nhịp 7 ngày phải có ngày dự kiến"
```

- [ ] **Step 2: Chạy để thấy thất bại**

Run: `pytest tests/test_san_pham_360.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kome.san_pham_360'`.

- [ ] **Step 3: Viết mô-đun** — tạo `kome/san_pham_360.py`:

```python
"""Sản phẩm 360 — trang riêng `/san-pham/{mã}` (đặc tả 2026-09-26-san-pham-360-trang-rieng-design.md).

`ho_so` phục vụ lúc MỞ trang (trần 5 lượt hỏi). Bốn hàm `tab_*` phục vụ từng tab, tải khi bấm.
Chỉ số mới là hàm `mart.sp_*` (migration 051–053) — Python không định nghĩa chỉ số, chỉ hỏi
và đổi hình dạng.
"""
from datetime import date

from kome import san_pham as SP
from kome.san_pham import _COT, _so, _sp, LOAI_HAN, QUY_CACH

# Một câu cách tính cho mỗi khối — màn in ngay dưới khối (nút "Cách tính").
CACH_TINH = {
    "thang": "doanh thu thuần (chưa thuế) theo tháng; cột mờ = cùng tháng năm trước",
    "mua_lai": "ngày dự kiến = lần mua cuối + nhịp mua riêng của cặp khách–mã (≥ 3 lần mua) · "
               "cùng cách tính khối \"Mã đến ngày mua lại\" của hồ sơ khách",
    "nen_chao": "khách đang mua đều ít nhất một mã CÙNG NGÀNH mà chưa từng mua mã này · "
                "xếp theo doanh thu ngành đó 12 tháng · bỏ khách ※廃業※/※取引停止※",
    "tap_trung": "doanh thu thuần 12 tháng tới mốc, gộp theo khách, luỹ kế từ khách lớn nhất",
    "tinh": "tỉnh theo hồ sơ khách hiện hành · doanh thu thuần 12 tháng",
    "nguoi": "người phụ trách ghi trên từng dòng bán · 12 tháng",
    "khach_moi": "khách mới = tháng đó là lần đầu khách mua mã này; tháng có mua = doanh thu thuần > 0",
    "tuan": "26 tuần (thứ Hai → Chủ nhật) tới tuần chứa mốc",
    "nhip": "nhịp mua riêng của từng cặp khách–mã (trung vị khoảng cách, cần ≥ 3 lần mua)",
    "co_don": "số lượng trên từng dòng bán theo quy cách, 12 tháng · dòng âm là hàng trả lại (赤伝), đếm riêng",
    "don_gia": "đơn giá thực = tổng doanh thu thuần ÷ tổng số lượng, theo tháng và quy cách",
    "bien": "biên lãi gộp = tổng lãi gộp ÷ tổng doanh thu thuần của tháng",
    "khach_gia": "khách có doanh thu thuần > 0 và mua ≥ 2 ngày trong 12 tháng · đơn giá theo quy cách "
                 "bán nhiều nhất của mã",
    "mua_kem": "trong các phiếu 12 tháng có mã này: mã khác xuất hiện trên bao nhiêu % số phiếu đó · "
               "bỏ phí, hàng tặng, hàng ngừng kinh doanh đã hết tồn",
}


def _thang_lui(t: str, n: int) -> str:
    y, m = int(t[:4]), int(t[5:7]) - n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y}-{m:02d}"


def _ton_lo(conn, ma: str) -> list[dict]:
    """Tồn theo LÔ (042, bẫy #6), xếp theo thứ tự bán. 1 lượt hỏi."""
    return [{"kho": t[0], "ten_kho": t[1], "so_luong": _so(t[2]),
             "gia_tri": int(t[3] or 0), "best_before": t[4], "loai_han": t[5],
             "nhan_han": LOAI_HAN.get(t[5], (t[5] or "—", "nhat"))[0],
             "mau_han": LOAI_HAN.get(t[5], (t[5] or "—", "nhat"))[1],
             "han_con_lai": t[6], "vai_tro_lo": t[7],
             "bat_dau_ban_sau": _so(t[8]), "ban_het_sau": _so(t[9]),
             "khong_kip_ban": t[10], "sap_chuyen_lo": t[11]}
            for t in conn.execute(
        """SELECT warehouse_code, ten_kho, so_luong, gia_tri, best_before,
                  loai_han, han_con_lai, vai_tro_lo, bat_dau_ban_sau,
                  ban_het_sau, khong_kip_ban, sap_chuyen_lo
           FROM mart.ton_theo_lo WHERE product_code = %s
           ORDER BY thu_tu_lo""", (ma,)).fetchall()]
```

Tiếp tục cùng file — dán NGUYÊN khối `khach = conn.execute(f"""WITH h AS MATERIALIZED …""")` và `_khach(r)` từ `SP.ho_so` cũ (kome/san_pham.py, đoạn từ chú thích "Hai khối khách gộp làm MỘT lượt hỏi" tới `khach_ngung = …`, GIỮ nguyên chú thích dài) vào hàm:

```python
def _khach_dang_ngung(conn, ma: str) -> tuple[list[dict], list[dict]]:
    """Khách đang mua (top 20) / đã ngừng mua (top 10) mã này — ĐỌC trang_thai_cap (024).
    1 lượt hỏi. (Chuyển nguyên từ SP.ho_so cũ.)"""
    # <<< dán nguyên khối SQL + chú thích từ SP.ho_so cũ ở đây >>>
    return khach_mua, khach_ngung


def _bac_gia(conn, ma: str) -> list[dict]:
    """Giá theo bậc — dòng MỚI NHẤT mỗi (bậc, quy cách). 1 lượt hỏi. (Chuyển từ SP.ho_so cũ.)"""
    # DISTINCT ON … ORDER BY valid_from DESC: fact_price_list giữ LỊCH SỬ giá.
    return [{"bac": g[0], "quy_cach": QUY_CACH.get(g[1], g[1]), "pack_code": g[1],
             "gia": int(g[2]), "tu_ngay": g[3]}
            for g in conn.execute(
        """SELECT DISTINCT ON (price_level, pack_code)
                  price_level, pack_code, price_ex_tax, valid_from
           FROM core.fact_price_list WHERE product_code = %s
           ORDER BY price_level, pack_code, valid_from DESC""", (ma,)).fetchall()]


def ho_so(conn, ma: str) -> dict | None:
    """Phần mở trang của Sản phẩm 360. None nếu mã không có trong san_pham_360.

    NGÂN SÁCH: 4 lượt hỏi (trần 5, có test đếm). 1) san_pham_360 + ngành + mốc;
    2) 24 tháng; 3) tồn theo lô; 4) cột trái: khách đến ngày mua lại + khách nên chào
    + hai số đếm, gộp MỘT câu.
    """
    r = conn.execute(
        f"""SELECT {', '.join('s.' + c.strip() for c in _COT.split(','))},
                   mart.ten_nganh(p.food_category_name, p.product_code, p.kind_code),
                   (SELECT hom_nay FROM mart.moc_thoi_gian)
              FROM mart.san_pham_360 s
              LEFT JOIN core.dim_product p ON p.product_code = s.product_code
             WHERE s.product_code = %s""", (ma,)).fetchone()
    if r is None:
        return None
    sp, nganh, hom_nay = _sp(r[:16]), r[16], r[17]

    cuoi = f"{hom_nay:%Y-%m}" if hom_nay else None
    theo = {t[0]: t for t in conn.execute(
        """SELECT thang, so_luong, doanh_thu_thuan, lai_gop
             FROM mart.san_pham_theo_thang
            WHERE product_code = %s AND thang >= %s ORDER BY thang""",
        (ma, _thang_lui(cuoi, 35) if cuoi else "0000-00")).fetchall()}
    thang = []
    if cuoi:
        for i in range(23, -1, -1):
            t = _thang_lui(cuoi, i)
            x, y = theo.get(t), theo.get(_thang_lui(t, 12))
            thang.append({"thang": t, "so_luong": _so(x[1]) if x else 0.0,
                          "doanh_thu": int(x[2] or 0) if x else 0,
                          "lai_gop": int(x[3] or 0) if x else 0,
                          "dt_nam_truoc": int(y[2] or 0) if y else 0})

    ton = _ton_lo(conn, ma)

    # Cột trái — MỘT câu. `h` vật hoá khach_mat_hang của ĐÚNG mã này (vị từ trong CTE, đẩy
    # xuống được) vì ba nhánh cùng đọc nó. Vị từ "đến ngày mua lại" = của
    # kome/ho_so_khach.py::lich_mua: trang_thai_cap = 'mua' AND du_kien_lan_toi IS NOT NULL.
    trai = conn.execute("""
        WITH h AS MATERIALIZED (
            SELECT customer_code, du_kien_lan_toi, nhip_ngay, lan_cuoi, doanh_thu_thuan, trang_thai_cap
              FROM mart.khach_mat_hang WHERE product_code = %s
        ), c AS MATERIALIZED (SELECT * FROM mart.sp_khach_nen_chao(%s))
        SELECT 'lai'::text, h.customer_code, coalesce(nullif(d.customer_name, ''), h.customer_code),
               h.du_kien_lan_toi, h.nhip_ngay::numeric, h.lan_cuoi, h.doanh_thu_thuan::numeric, NULL::bigint
          FROM h LEFT JOIN core.dim_customer d ON d.customer_code = h.customer_code AND d.is_current
         WHERE h.trang_thai_cap = 'mua' AND h.du_kien_lan_toi IS NOT NULL
        UNION ALL
        (SELECT 'chao', c.customer_code, c.ten, NULL::date, NULL::numeric, c.lan_cuoi,
                c.doanh_thu_nganh, c.so_ma_nganh FROM c
          ORDER BY c.doanh_thu_nganh DESC, c.customer_code LIMIT 5)
        UNION ALL
        SELECT 'dem', NULL, NULL, NULL, count(*) FILTER (WHERE trang_thai_cap = 'mua'), NULL,
               count(*) FILTER (WHERE trang_thai_cap = 'ngung'), (SELECT count(*) FROM c)
          FROM h
    """, (ma, ma)).fetchall()

    mua_lai = sorted(
        ({"ma": x[1], "ten": x[2], "du_kien": x[3],
          "con": (x[3] - hom_nay).days if hom_nay else None,
          "nhip": _so(x[4]), "lan_cuoi": x[5], "doanh_thu": int(x[6] or 0)}
         for x in trai if x[0] == "lai"),
        key=lambda d: (d["con"], -d["doanh_thu"]))
    nen_chao = [{"ma": x[1], "ten": x[2], "lan_cuoi": x[5], "doanh_thu_nganh": int(x[6] or 0),
                 "so_ma_nganh": int(x[7] or 0)} for x in trai if x[0] == "chao"]
    dem = next(x for x in trai if x[0] == "dem")
    return {"sp": sp, "nganh": nganh, "hom_nay": hom_nay, "thang": thang, "ton": ton,
            "mua_lai": mua_lai[:10], "mua_lai_tong": len(mua_lai),
            "nen_chao": nen_chao, "nen_chao_tong": int(dem[7] or 0),
            "so_dang_mua": int(dem[4] or 0), "so_da_ngung": int(dem[6] or 0),
            "ngung_ban": sp.ngung_ban, "cach_tinh": CACH_TINH}
```

Lưu ý: kiểm cột `sap_chuyen_lo` có trong `mart.ton_theo_lo` (`grep -n "sap_chuyen_lo" db/migrations/042_*.sql`). Nếu `_COT` có khoảng trắng/xuống dòng, biểu thức `', '.join('s.' + c.strip() …)` đã xử lý. `r[:16]` vì `_COT` có đúng 16 cột.

- [ ] **Step 4: Xoá `ho_so` cũ khỏi `kome/san_pham.py`**

Xoá hàm `ho_so()` và dataclass `HoSoSanPham` trong `kome/san_pham.py`. Chạy `grep -rn "SP.ho_so\|san_pham.ho_so\|HoSoSanPham" kome/ scripts/ tests/` — mọi chỗ còn lại xử lý ở Step 5–6.

- [ ] **Step 5: Đổi route API** — trong `kome/web/api.py`, route `sp_ho_so`, thay thân `tinh_`:

```python
        def tinh_(c):
            from kome import san_pham_360 as SP360
            h = SP360.ho_so(c, ma)
            if h is None:
                # 050: hàng ※終売※ hết tồn không phân tích — nói rõ, không "không có mã".
                return NGUNG_BAN if SP.la_ma_ngung_ban_an(c, ma) else None
            return thanh_json({"h": h, "quy_cach": SP.QUY_CACH})
```

Docstring route: "Phần mở trang của Sản phẩm 360 (`SP360.ho_so`, 4 lượt hỏi, trần 5; +1 đặt mốc khi có khoảng xem — 040)."

- [ ] **Step 6: Chuyển các test cũ của `SP.ho_so`** trong `tests/test_san_pham.py`:
  - `test_ho_so_ma_khong_ton_tai_tra_None`, `test_ho_so_san_pham_khong_qua_5_truy_van`: XOÁ (đã có bản mới ở `tests/test_san_pham_360.py`).
  - `test_ho_so_co_du_nam_khoi`: đổi phần khẳng định thành
    ```python
    from kome import san_pham_360 as SP360
    h = SP360.ho_so(conn, "P019")
    assert h["sp"].ma == "P019" and h["sp"].ten == "Gạo ST25"
    mua, ngung = SP360._khach_dang_ngung(conn, "P019")
    assert [k["ma"] for k in mua] == ["KP19"] and [k["ma"] for k in ngung] == ["KP20"]
    assert [t["kho"] for t in h["ton"]] == ["0001"]
    assert sorted(g["quy_cach"] for g in SP360._bac_gia(conn, "P019")) == \
        sorted([SP.QUY_CACH["00"], SP.QUY_CACH["02"]])
    ```
  - `test_bac_gia_chi_hien_dong_MOI_NHAT_cua_tung_quy_cach`: `bg = SP360._bac_gia(conn, "P022")`.
  - `test_khach_ngung_mua_ma_nay_…`, `test_hai_man_tra_loi_GIONG_NHAU_…`, `test_khach_da_dong_cua_…`, `test_cap_cua_khach_da_dong_cua_…`: thay `h = SP.ho_so(conn, X)` / `sp = SP.ho_so(conn, X)` bằng `mua, ngung = SP360._khach_dang_ngung(conn, X)` và `h.khach_mua`/`sp.khach_mua` → `mua`, `h.khach_ngung`/`sp.khach_ngung` → `ngung`.
  - `test_ho_so_hien_dung_cot_toc_do_…`: `sp = SP360.ho_so(conn, "P021")["sp"]`.
  - Thêm `from kome import san_pham_360 as SP360` ở đầu file.

- [ ] **Step 7: Chạy test**

Run: `pytest tests/test_san_pham_360.py tests/test_san_pham.py tests/test_khoang_san_pham.py tests/test_ngung_ban.py -v`
Expected: tất cả PASS. Nếu `test_ngan_sach_luot_hoi_tung_endpoint[/api/san-pham/P100-5]` đỏ: đếm lại, `ho_so` phải 4 lượt.

- [ ] **Step 8: Commit**

```bash
git add kome/san_pham_360.py kome/san_pham.py kome/web/api.py tests/test_san_pham_360.py tests/test_san_pham.py
git commit -m "feat(san-pham): ho so 360 phan mo trang (24 thang, cot trai mua lai + nen chao)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Bốn hàm tab + bốn route API

**Files:**
- Modify: `kome/san_pham_360.py` (thêm `tab_khach`, `tab_thoi_gian`, `tab_gia`, `tab_ban_them`)
- Modify: `kome/web/api.py` (thêm 4 route ngay sau `sp_ngay`)
- Test: `tests/test_san_pham_360.py` (thêm)

**Interfaces:**
- Consumes: 10 hàm `mart.sp_*` (Task 1–3), `_ton_lo`, `_khach_dang_ngung`, `_bac_gia` (Task 4), `kome.ban_do.O_RONG/O_CAO/KHE/_tinh_bac`.
- Produces:
  - `tab_khach(conn, ma) -> dict`: `tap_trung` (list[{ma, ten, doanh_thu, ty_trong, luy_ke}]), `top10_ty_trong` (float|None), `tinh` ({o: list[{ma_jis, ten, ten_ngan, vung, x, y, doanh_thu, so_khach, bac}], rong, cao, o_rong, o_cao, khong_ro: int}), `nguoi` (list[{ma, ten, doanh_thu, lai_gop, so_khach}]), `khach_moi` (list[{thang, moi, quay_lai}]), `dang_mua`, `da_ngung` (như `_khach_dang_ngung`). **3 lượt.**
  - `tab_thoi_gian(conn, ma) -> dict`: `tuan` (list[{tuan, so_luong, doanh_thu}]), `nhip` (list[{nhom, so_cap}] — nhóm `≤7`, `8–14`, `15–30`, `31–60`, `>60`, `chua_du`), `co_don` (list[{pack_code, quy_cach, nhom, thu_tu, so_dong, so_luong}]). **2 lượt.**
  - `tab_gia(conn, ma) -> dict`: `don_gia` (list[{thang, pack_code, quy_cach, so_luong, doanh_thu, don_gia}]), `bac_gia`, `khach_gia` (list[{ma, ten, pack_code, so_lan, so_luong, doanh_thu, lai_gop, don_gia, bien}]). **2 lượt.** (biên theo tháng lấy từ `ho_so.thang` ở giao diện — không hỏi lại.)
  - `tab_ban_them(conn, ma) -> dict`: `ton`, `mua_kem` (list[{ma, ten, so_phieu, ty_le}]), `tong_phieu` (int), `nen_chao` (list đầy đủ, ≤ 50). **2 lượt.**
  - Route: `GET /api/san-pham/{ma}/khach`, `/thoi-gian`, `/gia`, `/ban-them` → `{"t": <dict>, "cach_tinh": CACH_TINH}`.

- [ ] **Step 1: Viết test thất bại** — thêm vào `tests/test_san_pham_360.py`:

```python
def test_tab_khach_khong_qua_3_luot(conn, batch, monkeypatch):
    _gieo_mot_ma(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    t = SP360.tab_khach(conn, "Q1")
    assert t["tap_trung"] and len(t["tinh"]["o"]) == 47
    assert [k["ma"] for k in t["dang_mua"]] == ["KQ01"]
    assert dem["n"] <= 3, dem["n"]


def test_tab_khach_tinh_bac_0_la_DUNG_BANG_0(conn, batch):
    _gieo_mot_ma(conn, batch)
    o = {x["ten"]: x for x in SP360.tab_khach(conn, "Q1")["tinh"]["o"]}
    assert o["東京都"]["bac"] > 0 and o["和歌山県"]["bac"] == 0


@pytest.mark.parametrize("ham, tran", [("tab_thoi_gian", 2), ("tab_gia", 2), ("tab_ban_them", 2)])
def test_tab_con_lai_trong_tran(conn, batch, monkeypatch, ham, tran):
    _gieo_mot_ma(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    t = getattr(SP360, ham)(conn, "Q1")
    assert t, "đếm một hàm trả rỗng thì không đếm gì"
    assert dem["n"] <= tran, f"{ham} chạy {dem['n']} lượt"


def test_tab_thoi_gian_nhip_dem_cap_chua_du_rieng(conn, batch):
    _gieo_mot_ma(conn, batch)
    nhip = {x["nhom"]: x["so_cap"] for x in SP360.tab_thoi_gian(conn, "Q1")["nhip"]}
    assert nhip.get("≤7") == 1          # KQ01 nhịp 7 ngày
    assert nhip.get("chua_du") == 0     # khách neo 000000000999 mua XT07, không phải Q1
```

```python
@pytest.mark.parametrize("duoi, tran", [("khach", 3), ("thoi-gian", 2), ("gia", 2), ("ban-them", 2), ("", 5)])
def test_ngan_sach_luot_hoi_api_360(conn, batch, test_db_url, monkeypatch, duoi, tran):
    import psycopg
    _gieo_mot_ma(conn, batch)
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    url = "/api/san-pham/Q1" + (f"/{duoi}" if duoi else "")
    r = _khach_web(test_db_url).get(url)
    assert r.status_code == 200, r.text
    assert dem["n"] <= tran, f"{url} chạy {dem['n']} lượt, trần {tran}"


def test_api_tab_ma_khong_co_tra_404(conn, batch, test_db_url):
    _neo(conn, batch)
    c = _khach_web(test_db_url)
    for duoi in ("khach", "thoi-gian", "gia", "ban-them"):
        assert c.get(f"/api/san-pham/KHONG-CO/{duoi}").status_code == 404, duoi
```

- [ ] **Step 2: Chạy để thấy thất bại**

Run: `pytest tests/test_san_pham_360.py -v`
Expected: FAIL — `AttributeError: module 'kome.san_pham_360' has no attribute 'tab_khach'`.

- [ ] **Step 3: Viết bốn hàm tab** — thêm vào `kome/san_pham_360.py`:

```python
def tab_khach(conn, ma: str) -> dict | None:
    """Tab Khách hàng. 3 lượt: 1) tập trung + người phụ trách + mới/quay lại + tồn tại mã;
    2) 47 tỉnh; 3) khách đang mua / đã ngừng."""
    from kome import ban_do as BD
    r = conn.execute("""
        SELECT EXISTS (SELECT 1 FROM mart.san_pham_360 WHERE product_code = %s),
               (SELECT coalesce(json_agg(json_build_object('ma', customer_code, 'ten', ten,
                        'doanh_thu', doanh_thu, 'ty_trong', ty_trong, 'luy_ke', luy_ke)), '[]')
                  FROM mart.sp_tap_trung_khach(%s)),
               (SELECT coalesce(json_agg(json_build_object('ma', salesperson_code, 'ten', ten,
                        'doanh_thu', doanh_thu, 'lai_gop', lai_gop, 'so_khach', so_khach)), '[]')
                  FROM mart.sp_theo_nguoi(%s)),
               (SELECT coalesce(json_agg(json_build_object('thang', thang, 'moi', khach_moi,
                        'quay_lai', khach_quay_lai) ORDER BY thang), '[]')
                  FROM mart.sp_khach_moi_thang(%s))
    """, (ma, ma, ma, ma)).fetchone()
    if not r[0]:
        return None
    tap_trung = r[1]
    tong = sum(x["doanh_thu"] or 0 for x in tap_trung)
    top10 = (sum(x["doanh_thu"] or 0 for x in tap_trung[:10]) / tong) if tong else None

    rows = conn.execute(
        """SELECT ma_jis, ten, ten_ngan, vung, hang_luoi, cot_luoi, doanh_thu, so_khach
             FROM mart.sp_theo_tinh(%s)""", (ma,)).fetchall()
    bac = BD._tinh_bac([int(x[6]) for x in rows])
    max_hang = max(x[4] for x in rows)
    max_cot = max(x[5] for x in rows)
    o = [{"ma_jis": x[0], "ten": x[1], "ten_ngan": x[2], "vung": x[3],
          "x": (x[5] - 1) * (BD.O_RONG + BD.KHE), "y": (x[4] - 1) * (BD.O_CAO + BD.KHE),
          "doanh_thu": int(x[6]), "so_khach": int(x[7]), "bac": b}
         for x, b in zip(rows, bac)]
    tinh = {"o": o, "o_rong": BD.O_RONG, "o_cao": BD.O_CAO,
            "rong": max_cot * BD.O_RONG + (max_cot - 1) * BD.KHE,
            "cao": max_hang * BD.O_CAO + (max_hang - 1) * BD.KHE,
            "khong_ro": int(tong - sum(x["doanh_thu"] for x in o))}

    dang_mua, da_ngung = _khach_dang_ngung(conn, ma)
    return {"tap_trung": tap_trung, "top10_ty_trong": top10, "tinh": tinh,
            "nguoi": r[2], "khach_moi": r[3], "dang_mua": dang_mua, "da_ngung": da_ngung}


_NHOM_NHIP = (("≤7", 7), ("8–14", 14), ("15–30", 30), ("31–60", 60), (">60", None))


def tab_thoi_gian(conn, ma: str) -> dict | None:
    """Tab Thời gian. 2 lượt: 1) 26 tuần + tồn tại mã; 2) nhịp + cỡ đơn.
    (Bán theo ngày vẫn là /ngay, 1 lượt riêng.)"""
    r = conn.execute("""
        SELECT EXISTS (SELECT 1 FROM mart.san_pham_360 WHERE product_code = %s),
               (SELECT coalesce(json_agg(json_build_object('tuan', tuan, 'so_luong', so_luong,
                        'doanh_thu', doanh_thu) ORDER BY tuan), '[]') FROM mart.sp_theo_tuan(%s))
    """, (ma, ma)).fetchone()
    if not r[0]:
        return None
    r2 = conn.execute("""
        SELECT (SELECT coalesce(json_agg(nhip_ngay), '[]')
                  FROM mart.khach_mat_hang WHERE product_code = %s AND trang_thai_cap <> 'khong_goi'),
               (SELECT coalesce(json_agg(json_build_object('pack_code', pack_code, 'nhom', nhom,
                        'thu_tu', thu_tu, 'so_dong', so_dong, 'so_luong', so_luong)
                        ORDER BY pack_code, thu_tu), '[]') FROM mart.sp_co_don(%s))
    """, (ma, ma)).fetchone()
    dem = {n: 0 for n, _ in _NHOM_NHIP} | {"chua_du": 0}
    for v in r2[0]:
        if v is None:
            dem["chua_du"] += 1
            continue
        for n, tran in _NHOM_NHIP:
            if tran is None or v <= tran:
                dem[n] += 1
                break
    nhip = [{"nhom": n, "so_cap": c} for n, c in dem.items()]
    co_don = [x | {"quy_cach": QUY_CACH.get(x["pack_code"], x["pack_code"])} for x in r2[1]]
    return {"tuan": r[1], "nhip": nhip, "co_don": co_don}


def tab_gia(conn, ma: str) -> dict | None:
    """Tab Giá & lãi. 2 lượt: 1) đơn giá theo tháng + khách giá/biên + tồn tại mã; 2) bảng giá bậc."""
    r = conn.execute("""
        SELECT EXISTS (SELECT 1 FROM mart.san_pham_360 WHERE product_code = %s),
               (SELECT coalesce(json_agg(json_build_object('thang', thang, 'pack_code', pack_code,
                        'so_luong', so_luong, 'doanh_thu', doanh_thu, 'don_gia', don_gia)
                        ORDER BY thang, pack_code), '[]') FROM mart.sp_don_gia_thang(%s)),
               (SELECT coalesce(json_agg(json_build_object('ma', customer_code, 'ten', ten,
                        'pack_code', pack_code, 'so_lan', so_lan, 'so_luong', so_luong,
                        'doanh_thu', doanh_thu, 'lai_gop', lai_gop, 'don_gia', don_gia, 'bien', bien)), '[]')
                  FROM mart.sp_khach_gia(%s))
    """, (ma, ma, ma)).fetchone()
    if not r[0]:
        return None
    don_gia = [x | {"quy_cach": QUY_CACH.get(x["pack_code"], x["pack_code"])} for x in r[1]]
    return {"don_gia": don_gia, "khach_gia": r[2], "bac_gia": _bac_gia(conn, ma)}


def tab_ban_them(conn, ma: str) -> dict | None:
    """Tab Tồn & bán thêm. 2 lượt: 1) mua kèm + khách nên chào + tồn tại mã; 2) tồn theo lô."""
    # sp_mua_kem đọc hai lần -> CTE AS MATERIALIZED (bất biến CTE-trùng).
    r = conn.execute("""
        WITH k AS MATERIALIZED (SELECT * FROM mart.sp_mua_kem(%s))
        SELECT EXISTS (SELECT 1 FROM mart.san_pham_360 WHERE product_code = %s),
               (SELECT coalesce(json_agg(json_build_object('ma', product_code, 'ten', ten_hang,
                        'so_phieu', so_phieu, 'ty_le', ty_le) ORDER BY so_phieu DESC, product_code), '[]') FROM k),
               (SELECT coalesce(max(tong_phieu), 0) FROM k),
               (SELECT coalesce(json_agg(x), '[]') FROM (
                    SELECT customer_code AS ma, ten, doanh_thu_nganh, so_ma_nganh, lan_cuoi
                      FROM mart.sp_khach_nen_chao(%s) LIMIT 50) x)
    """, (ma, ma, ma)).fetchone()
    if not r[0]:
        return None
    return {"mua_kem": r[1], "tong_phieu": int(r[2]), "nen_chao": r[3], "ton": _ton_lo(conn, ma)}
```

- [ ] **Step 4: Thêm 4 route** — trong `kome/web/api.py`, ngay sau route `sp_ngay`:

```python
    def _tab_sp(request: Request, ma: str, ten: str, thang: str, ky: str, tu: str, den: str):
        """Một tab của Sản phẩm 360 — ảnh chụp riêng, tính đến MỐC của khoảng xem (040)."""
        from kome import san_pham_360 as SP360
        try:
            ts = _ts(request, thang, ky, tu, den).chinh()
        except KX.LoiKhoang as e:
            return _loi(str(e), 400)
        ham = {"khach": SP360.tab_khach, "thoi-gian": SP360.tab_thoi_gian,
               "gia": SP360.tab_gia, "ban-them": SP360.tab_ban_them}[ten]

        def tinh_(c):
            t = ham(c, ma)
            return None if t is None else thanh_json({"t": t, "cach_tinh": SP360.CACH_TINH})
        try:
            with open_app_conn() as conn:
                du_lieu, pb = anh_chup.lay(conn, _khoa(f"san-pham/tab-{ten}", ma=ma, **ts.khoa()),
                                           _voi_moc(ts, tinh_), chi_nap=True)
        except Exception:
            traceback.print_exc()
            return _loi("Không đọc được dữ liệu tab này.")
        if du_lieu == "null":
            return _loi(f"Không có mã hàng {ma}.", 404)
        return _json(request, du_lieu, pb)

    @r.get("/san-pham/{ma}/khach")
    def sp_tab_khach(request: Request, ma: str, thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        """Tab Khách hàng của Sản phẩm 360. ≤ 3 lượt hỏi."""
        return _tab_sp(request, ma, "khach", thang, ky, tu, den)

    @r.get("/san-pham/{ma}/thoi-gian")
    def sp_tab_thoi_gian(request: Request, ma: str, thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        """Tab Thời gian của Sản phẩm 360. ≤ 2 lượt hỏi."""
        return _tab_sp(request, ma, "thoi-gian", thang, ky, tu, den)

    @r.get("/san-pham/{ma}/gia")
    def sp_tab_gia(request: Request, ma: str, thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        """Tab Giá & lãi của Sản phẩm 360. ≤ 2 lượt hỏi."""
        return _tab_sp(request, ma, "gia", thang, ky, tu, den)

    @r.get("/san-pham/{ma}/ban-them")
    def sp_tab_ban_them(request: Request, ma: str, thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        """Tab Tồn & bán thêm của Sản phẩm 360. ≤ 2 lượt hỏi."""
        return _tab_sp(request, ma, "ban-them", thang, ky, tu, den)
```

Kiểm `_json`, `_khoa`, `open_app_conn`, `anh_chup`, `traceback`, `json` đã được nhập ở đầu `api.py` (route `sp_ho_so` dùng chúng — cùng file). Thêm 4 URL mới vào `test_chua_dang_nhap_thi_401_json` (tests/test_san_pham.py) — parametrize thêm `"/api/san-pham/P1/khach"`, `"/api/san-pham/P1/gia"`.

- [ ] **Step 5: Chạy test**

Run: `pytest tests/test_san_pham_360.py tests/test_san_pham.py -v`
Expected: tất cả PASS.

- [ ] **Step 6: Commit**

```bash
git add kome/san_pham_360.py kome/web/api.py tests/test_san_pham_360.py tests/test_san_pham.py
git commit -m "feat(san-pham): 4 tab san pham 360 (khach, thoi gian, gia, ban them) + API

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Giao diện — khung trang riêng + cột trái + điều hướng

**Files:**
- Create: `giao_dien/src/chung/LuoiTinh.tsx`, `giao_dien/src/san_pham/ho_so/kieu.ts`, `HoSoMa.tsx`, `ViecVoiMa.tsx`, `ho_so.css`
- Modify: `giao_dien/src/khach/BanDo.tsx:17-18` (nhập màu từ `chung/LuoiTinh`)
- Modify: `giao_dien/src/main.tsx:29,54` ; `giao_dien/src/san_pham/ManSanPham.tsx`
- Delete: `giao_dien/src/san_pham/HoSoSanPham.tsx` (chuyển `BanTheoNgay`, `XuHuong` sang `ho_so/TabThoiGian.tsx` ở Task 7 — tạm thời Task 6 để `TabThoiGian.tsx` chỉ chứa `BanTheoNgay` chép nguyên)
- Modify: `tests/test_nguon_dung.py:45`, `tests/test_san_pham.py` (các test đọc `HoSoSanPham.tsx`)

**Interfaces:**
- Consumes: JSON `/api/san-pham/{mã}` = `{h: HoSoMaApi, quy_cach}` (Task 4); `/api/san-pham/{mã}/khoang` (có sẵn, kiểu `KhoangMaApi` trong `san_pham/kieu.ts` — dùng lại kiểu đang có ở `HoSoSanPham.tsx`); `The` từ `khach/HoSoTab`; `BieuDo` từ `chung/BieuDo`.
- Produces: `export default function HoSoMa({ ma }: { ma: string })`; `export function LuoiTinh(props)`; `export const MAU_O, MAU_CHU`; `nhoDanhMuc(ma: string[], url: string)` / `docDanhMuc()` trong `san_pham/loc.ts`; kiểu `HoSoMaApi`, `TabKhachApi`, `TabThoiGianApi`, `TabGiaApi`, `TabBanThemApi` trong `ho_so/kieu.ts`.

- [ ] **Step 1: Test đọc mã nguồn (thất bại trước)** — thêm vào `tests/test_san_pham.py`:

```python
def test_trang_rieng_360_co_khung_hai_cot_va_lien_ket_khach():
    """Trang riêng dùng bố cục hs2 của khách 360 và link mọi khách sang /khach-hang/{mã}."""
    ho = _SRC / "ho_so"
    src = "".join((ho / f).read_text(encoding="utf-8") for f in ("HoSoMa.tsx", "ViecVoiMa.tsx"))
    assert "hs2-luoi" in src and "hs2-trai" in src
    assert "/khach-hang/${encodeURIComponent(" in src
    assert "giuKhoang(" in src
    assert not (_SRC / "HoSoSanPham.tsx").exists(), "hồ sơ dưới bảng phải bỏ"
    man = _nguon("ManSanPham.tsx")
    assert "HoSoSanPham" not in man and "location.href = giuKhoang(" in man
```

Sửa các test đang đọc `HoSoSanPham.tsx`:
- `tests/test_nguon_dung.py:45`: `"san_pham/HoSoSanPham.tsx": "TN.bang_gia"` → `"san_pham/ho_so/TabGia.tsx": "TN.bang_gia"` (TabGia tạo ở Task 7 — test này sẽ đỏ cho tới Task 7; ghi chú trong commit).
- `tests/test_san_pham.py` dòng ~746: `src + _nguon("HoSoSanPham.tsx")` → `src + (_SRC / "ho_so" / "HoSoMa.tsx").read_text(encoding="utf-8") + (_SRC / "ho_so" / "ViecVoiMa.tsx").read_text(encoding="utf-8")`.
- dòng ~769: tuple `("ManSanPham.tsx", "HoSoSanPham.tsx", "KhoHang.tsx")` → `("ManSanPham.tsx", "ho_so/HoSoMa.tsx", "ho_so/ViecVoiMa.tsx", "KhoHang.tsx")`.

Run: `pytest tests/test_san_pham.py -k "trang_rieng_360" -v` → FAIL (file chưa có).

- [ ] **Step 2: `chung/LuoiTinh.tsx`** (tách màu khỏi BanDo, thêm lưới dùng chung)

```tsx
// Lưới 47 tỉnh dùng chung (bản đồ khách hàng + Sản phẩm 360). Hình học (x, y, bậc) do máy
// chủ tính (kome/ban_do.py) — ở đây chỉ vẽ. Bậc 0 = ĐÚNG BẰNG 0 (bất biến _tinh_bac).
import { useState } from "react";

export const MAU_O = ["var(--map-0)", "var(--map-1)", "var(--map-2)", "var(--map-3)", "var(--map-4)", "var(--map-5)"];
export const MAU_CHU = ["var(--chu-nhat)", "var(--chu)", "var(--chu)", "var(--map-chu-alt)", "var(--map-chu-alt)", "var(--map-chu-alt)"];

export type OTinh = { ma_jis: string; ten: string; ten_ngan: string; x: number; y: number; bac: number };

export function LuoiTinh<T extends OTinh>({ o, rong, cao, o_rong, o_cao, nhan, noi, mo_ta }: {
  o: T[]; rong: number; cao: number; o_rong: number; o_cao: number;
  nhan: (o: T) => string; noi: (o: T) => React.ReactNode; mo_ta: string;
}) {
  const [tro, datTro] = useState<T | null>(null);
  return (
    <div className="kh-bd-hinh">
      <svg viewBox={`0 0 ${rong} ${cao}`} role="img" aria-label={mo_ta}>
        {o.map(x => (
          <g key={x.ma_jis} className="kh-bd-o" tabIndex={0}
            onMouseEnter={() => datTro(x)} onMouseLeave={() => datTro(null)} onFocus={() => datTro(x)} onBlur={() => datTro(null)}>
            <rect x={x.x} y={x.y} width={o_rong} height={o_cao} rx={7} fill={MAU_O[x.bac]} />
            <text x={x.x + o_rong / 2} y={x.y + 23} textAnchor="middle" fontSize={12} fill={MAU_CHU[x.bac]}>{x.ten_ngan}</text>
            <text x={x.x + o_rong / 2} y={x.y + 41} textAnchor="middle" fontSize={10.5} fontWeight={600}
              fill={MAU_CHU[x.bac]} className="so">{nhan(x)}</text>
          </g>))}
      </svg>
      {tro && <div className="kh-bd-noi" role="status">{noi(tro)}</div>}
    </div>);
}
```

Trong `khach/BanDo.tsx`: xoá hai dòng `const MAU_O = …` / `const MAU_CHU = …`, thêm `import { MAU_CHU, MAU_O } from "../chung/LuoiTinh";`. (BanDo giữ SVG riêng vì có bấm-mở-danh-sách; chỉ màu là dùng chung — không chép.)

- [ ] **Step 3: `ho_so/kieu.ts`**

```ts
import type { SanPhamApi } from "../kieu";   // kiểu `sp` của hồ sơ cũ — kiểm tên thật trong san_pham/kieu.ts (HoSoSpApi["h"]["sp"])

export type LoTon = { kho: string; ten_kho: string; so_luong: number | null; gia_tri: number; best_before: string | null;
  loai_han: string; nhan_han: string; mau_han: string; han_con_lai: number | null; vai_tro_lo: string;
  bat_dau_ban_sau: number | null; ban_het_sau: number | null; khong_kip_ban: boolean | null; sap_chuyen_lo: boolean | null };
export type KhachMuaLai = { ma: string; ten: string; du_kien: string; con: number; nhip: number | null; lan_cuoi: string; doanh_thu: number };
export type KhachNenChao = { ma: string; ten: string; lan_cuoi: string | null; doanh_thu_nganh: number; so_ma_nganh: number };
export type ThangMa = { thang: string; so_luong: number; doanh_thu: number; lai_gop: number; dt_nam_truoc: number };
export type CachTinh = Record<string, string>;

export type HoSoMaApi = { h: {
  sp: SanPhamApi; nganh: string; hom_nay: string | null; thang: ThangMa[]; ton: LoTon[];
  mua_lai: KhachMuaLai[]; mua_lai_tong: number; nen_chao: KhachNenChao[]; nen_chao_tong: number;
  so_dang_mua: number; so_da_ngung: number; ngung_ban: boolean; cach_tinh: CachTinh;
}; quy_cach: Record<string, string> };

export type KhachDong = { ma: string; ten: string; doanh_thu: number; so_luong: number | null; so_lan: number;
  lan_cuoi: string; nhip: number | null; tre: number | null };
export type OTinhMa = { ma_jis: string; ten: string; ten_ngan: string; vung: string; x: number; y: number;
  doanh_thu: number; so_khach: number; bac: number };
export type TabKhachApi = { t: {
  tap_trung: { ma: string; ten: string; doanh_thu: number; ty_trong: number | null; luy_ke: number | null }[];
  top10_ty_trong: number | null;
  tinh: { o: OTinhMa[]; rong: number; cao: number; o_rong: number; o_cao: number; khong_ro: number };
  nguoi: { ma: string; ten: string | null; doanh_thu: number; lai_gop: number; so_khach: number }[];
  khach_moi: { thang: string; moi: number; quay_lai: number }[];
  dang_mua: KhachDong[]; da_ngung: KhachDong[];
}; cach_tinh: CachTinh };
export type TabThoiGianApi = { t: {
  tuan: { tuan: string; so_luong: number; doanh_thu: number }[];
  nhip: { nhom: string; so_cap: number }[];
  co_don: { pack_code: string; quy_cach: string; nhom: string; thu_tu: number; so_dong: number; so_luong: number }[];
}; cach_tinh: CachTinh };
export type TabGiaApi = { t: {
  don_gia: { thang: string; pack_code: string; quy_cach: string; so_luong: number; doanh_thu: number; don_gia: number | null }[];
  bac_gia: { bac: string; quy_cach: string; pack_code: string; gia: number; tu_ngay: string }[];
  khach_gia: { ma: string; ten: string; pack_code: string; so_lan: number; so_luong: number | null; doanh_thu: number;
    lai_gop: number; don_gia: number | null; bien: number | null }[];
}; cach_tinh: CachTinh };
export type TabBanThemApi = { t: {
  mua_kem: { ma: string; ten: string; so_phieu: number; ty_le: number | null }[]; tong_phieu: number;
  nen_chao: KhachNenChao[]; ton: LoTon[];
}; cach_tinh: CachTinh };
```

Mở `san_pham/kieu.ts`, xem `HoSoSpApi` để lấy đúng kiểu `sp` (và kiểu của `/khoang`) — nếu không có kiểu `SanPhamApi` riêng thì `export type SanPhamApi = HoSoSpApi["h"]["sp"]` trong `san_pham/kieu.ts` trước khi xoá `HoSoSpApi`. Sau Task 6, xoá `HoSoSpApi` nếu không còn ai dùng.

- [ ] **Step 4: Nhớ thứ tự danh mục** — thêm vào `san_pham/loc.ts`:

```ts
// Danh mục vừa xem (để trang 360 có ‹ n/N ›) — tiện nghi riêng máy này, cùng nếp khach/loc.ts.
const KHOA_DM = "kome_sp_dm_v1";
export function nhoDanhMuc(ma: string[], url: string) {
  try { sessionStorage.setItem(KHOA_DM, JSON.stringify({ ma, url })); } catch { /* */ }
}
export function docDanhMuc(): { ma: string[]; url: string } | null {
  try { return JSON.parse(sessionStorage.getItem(KHOA_DM) || "null"); } catch { return null; }
}
```

- [ ] **Step 5: `ManSanPham.tsx` — bấm dòng điều hướng, bỏ hồ sơ dưới bảng**
  - Xoá `import { HoSoSanPham }`, state `ma`/`datMa`, `hoSo` ref, khối `sp-ho-so-neo` và `maTuUrl`.
  - Hàm chọn dòng (chỗ đang `ghi(b, m, true)` / `datMa(m)`) đổi thành:
    ```tsx
    const moMa = (m: string) => {
      nhoDanhMuc(dsLoc.map(x => x.ma), location.pathname + location.search);
      location.href = giuKhoang(`/san-pham/${encodeURIComponent(m)}`);
    };
    ```
    (`dsLoc` = danh sách đã lọc/sắp đang hiện trong bảng — dùng đúng biến mà bảng đang `.map`.)
  - `ghi(bb, m, day)` bỏ tham số `m`: luôn ghi `/san-pham` + query.
  - Đổi chú thích đầu file: "/san-pham là danh mục; bấm một dòng mở trang riêng /san-pham/{mã} (ho_so/HoSoMa.tsx)."

- [ ] **Step 6: `main.tsx`**

```tsx
const HoSoMa = lazy(() => import("./san_pham/ho_so/HoSoMa"));
// …
  if (duong === "/san-pham") return () => <ManSanPham />;
  const mSp = duong.match(/^\/san-pham\/([^/]+)$/);
  if (mSp) { const ma = decodeURIComponent(mSp[1]); return () => <HoSoMa ma={ma} />; }
```
(thay dòng 54 hiện tại; giữ dòng 83 cho mục thanh bên đang sáng.)

- [ ] **Step 7: `ho_so/ViecVoiMa.tsx`**

```tsx
// Cột trái dính "Việc với mã này" — tồn + cảnh báo lô · khách đến ngày mua lại · khách nên chào.
// Mọi tên khách link /khach-hang/{mã} (qua giuKhoang — giữ khoảng xem).
import { The } from "../../khach/HoSoTab";
import { giuKhoang } from "../../khung/khoang";
import { ngay, so, so_luong as soLuong, yen } from "../../dinh_dang";
import type { HoSoMaApi } from "./kieu";

const lk = (ma: string) => giuKhoang(`/khach-hang/${encodeURIComponent(ma)}`);

function nhanCon(con: number) {
  if (con < 0) return { chu: `quá ${-con} ngày`, lop: "giam" };
  if (con === 0) return { chu: "hôm nay", lop: "canh-chu" };
  if (con <= 7) return { chu: `còn ${con} ngày`, lop: "canh-chu" };
  return { chu: `còn ${con} ngày`, lop: "nhat-chu" };
}

export function ViecVoiMa({ h, moTab }: { h: HoSoMaApi["h"]; moTab: (t: string) => void }) {
  const sp = h.sp;
  const canh: string[] = [];
  if (sp.trang_thai === "het_hang") canh.push("Hết hàng — còn khách đang mua đều.");
  if (sp.trang_thai === "sap_thieu") canh.push("Sắp thiếu — còn dưới 14 ngày bán.");
  if (sp.trang_thai === "chua_ro_ton") canh.push("Chưa có ảnh chụp tồn của mã này tới thời điểm này.");
  if (h.ton.some(t => t.sap_chuyen_lo)) canh.push("Sắp chuyển lô: lô đang xuất sắp hết, lô chờ sẽ lên.");
  if (h.ton.some(t => t.khong_kip_ban)) canh.push("Có lô không kịp bán trước hạn sử dụng.");
  return (
    <aside className="hs2-trai">
      <The tieu_de="Tồn & tốc độ" className="hs2-viec">
        <p className="sp3-so-lon">{sp.ton == null ? "—" : soLuong(sp.ton)}<span className="phu"> tồn</span></p>
        <p className="phu">Bán {sp.toc_do_ngay_theo_tuoi == null ? "—" : soLuong(sp.toc_do_ngay_theo_tuoi)}/ngày (theo tuổi) ·
          còn đủ {sp.du_ban_ngay == null ? "—" : `${so(Math.round(sp.du_ban_ngay))} ngày`}</p>
        {canh.map(c => <p key={c} className="khoi-canh">{c}</p>)}
        <button type="button" className="hs2-lien-ket" onClick={() => moTab("ban_them")}>Tồn theo lô ›</button>
      </The>

      <The tieu_de="Khách đến ngày mua lại" className="hs2-viec" cach_tinh={h.cach_tinh.mua_lai}
        goc={h.mua_lai_tong ? <span className="phu">{h.mua_lai.length}/{h.mua_lai_tong}</span> : null}>
        {!h.mua_lai.length ? <p className="phu">Chưa khách nào đủ 3 lần mua mã này để có nhịp riêng.</p> :
          <ul className="hs2-ds">{h.mua_lai.map(k => { const n = nhanCon(k.con); return (
            <li key={k.ma} className="hs2-dong"><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a>
              <b className={n.lop}>{n.chu}</b></li>); })}</ul>}
      </The>

      <The tieu_de="Khách nên chào" className="hs2-viec" cach_tinh={h.cach_tinh.nen_chao}
        goc={h.nen_chao_tong ? <span className="phu">{h.nen_chao_tong} khách</span> : null}>
        {h.ngung_ban ? <p className="phu">Không chào hàng đã ngừng kinh doanh (※終売※).</p> :
          !h.nen_chao.length ? <p className="phu">Chưa có khách mua đều mã cùng ngành ({h.nganh}) mà chưa mua mã này.</p> :
          <ul className="hs2-ds">{h.nen_chao.map(k => (
            <li key={k.ma} className="hs2-dong"><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a>
              <span className="phu" title={`${k.so_ma_nganh} mã cùng ngành · mua cuối ${ngay(k.lan_cuoi)}`}>{yen(k.doanh_thu_nganh)}</span></li>))}</ul>}
        {h.nen_chao_tong > h.nen_chao.length && <button type="button" className="hs2-lien-ket" onClick={() => moTab("ban_them")}>
          Xem hết {h.nen_chao_tong} khách ›</button>}
      </The>
    </aside>);
}
```

Kiểm tên lớp `khoi-canh`, `canh-chu`, `nhat-chu`, `giam` có trong CSS chung (`grep -rn "\.khoi-canh\|\.canh-chu" giao_dien/src`); lớp nào không có thì dùng lớp `.sp3-canh` định nghĩa ở `ho_so.css`.

- [ ] **Step 8: `ho_so/HoSoMa.tsx`**

```tsx
// Sản phẩm 360 — trang riêng (đặc tả 2026-09-26-san-pham-360-trang-rieng-design.md). Bố cục
// như hồ sơ khách 360 (khach/HoSo.tsx): thanh trên · đầu trang · HAI CỘT (hs2-luoi): cột trái dính
// "Việc với mã này" (ViecVoiMa.tsx), cột phải = 4 ô số + 24 tháng + 4 tab tải lười.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, useNhanMoc, voiKhoang } from "../../khung/khoang";
import { ngay, pc, so, so_luong as soLuong, thay_doi, yen } from "../../dinh_dang";
import { docDanhMuc } from "../loc";
import type { HoSoMaApi } from "./kieu";
import { ViecVoiMa } from "./ViecVoiMa";
import { TabKhach } from "./TabKhach";
import { TabThoiGian } from "./TabThoiGian";
import { TabGia } from "./TabGia";
import { TabBanThem } from "./TabBanThem";
import "../../khach/khach.css";
import "../san_pham.css";
import "./ho_so.css";

const TAB = [["khach", "Khách hàng"], ["thoi_gian", "Thời gian"], ["gia", "Giá & lãi"], ["ban_them", "Tồn & bán thêm"]] as const;
type MaTab = (typeof TAB)[number][0];
const tabTuHash = (h: string): MaTab => (TAB.find(([m]) => "#" + m === h)?.[0] ?? "khach");

export default function HoSoMa({ ma }: { ma: string }) {
  const kx = chuoiKhoang(useKhoang());
  const nhanMoc = useNhanMoc();
  const { data, error } = useQuery<HoSoMaApi>({ queryKey: ["sp360", ma, kx],
    queryFn: () => lay<HoSoMaApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}`)) });
  const { data: kh } = useQuery<any>({ queryKey: ["sp-ma-khoang", ma, kx],
    queryFn: () => lay(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/khoang`)) });
  const [tab, datTab] = useState<MaTab>(() => tabTuHash(location.hash));
  const [thangNgay, datThangNgay] = useState<string | null>(null);
  useEffect(() => { const f = () => datTab(tabTuHash(location.hash));
    addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  const chonTab = (t: string) => { datTab(t as MaTab); history.replaceState(null, "", giuKhoang(location.pathname + location.search) + "#" + t); };
  useEffect(() => { if (data) document.title = `KOME — ${data.h.sp.ten}`; }, [data]);

  const ds = docDanhMuc();
  const vi = ds ? ds.ma.indexOf(ma) : -1;
  const di = (m: string) => { location.href = giuKhoang(`/san-pham/${encodeURIComponent(m)}`); };
  const thanhTren = (
    <div className="hs-tren">
      <a className="nut-nho" href={giuKhoang(ds?.url ?? "/san-pham")}>← Danh mục sản phẩm</a>
      {vi >= 0 && ds && <span className="hs-tt">
        <button type="button" className="nut-nho" disabled={vi <= 0} onClick={() => di(ds.ma[vi - 1])} aria-label="Mã trước">‹</button>
        <span className="phu">{vi + 1}/{ds.ma.length}</span>
        <button type="button" className="nut-nho" disabled={vi >= ds.ma.length - 1} onClick={() => di(ds.ma[vi + 1])} aria-label="Mã sau">›</button>
      </span>}
    </div>);

  if (error) return <div className="kh">{thanhTren}<div className="khoi-loi">{(error as Error).message}</div></div>;
  if (!data) return <div className="kh">{thanhTren}<div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></div>;
  const h = data.h, sp = h.sp;
  const t12 = h.thang.slice(-12);
  const dt12 = t12.reduce((a, x) => a + x.doanh_thu, 0), lg12 = t12.reduce((a, x) => a + x.lai_gop, 0);

  return (
    <div className="kh hs hs2 sp3">
      {thanhTren}
      <header className="hs2-dau"><div className="hs2-dau-chu">
        <h1><span className="ten-jp">{sp.ten}</span>
          <span className="nhan-vien nhat">{h.nganh}</span>
          {h.ngung_ban && <span className="nhan-vien canh">bán nốt tồn</span>}</h1>
        <div className="phu"><code>{sp.ma}</code> · bán lần đầu {ngay(sp.lan_dau)} · lần cuối {ngay(sp.lan_cuoi)}
          {h.hom_nay && <> · dữ liệu {nhanMoc} {ngay(h.hom_nay)}</>}</div>
      </div></header>
      <div className="hs2-luoi">
        <ViecVoiMa h={h} moTab={chonTab} />
        <div className="hs2-phai">
          <div className="o-kpi-luoi hs2-o">
            <div className="o-kpi"><span className="phu">Doanh thu trong khoảng xem</span>
              <b>{kh ? yen(kh.tong.dt) : "…"}</b>
              {kh?.tang != null && <span className={kh.tang >= 0 ? "tang" : "giam"}>{thay_doi(kh.tang)} {kh.so_sanh?.nhan ?? ""}</span>}</div>
            <div className="o-kpi"><span className="phu">Bán / ngày (theo tuổi)</span>
              <b>{sp.toc_do_ngay_theo_tuoi == null ? "—" : soLuong(sp.toc_do_ngay_theo_tuoi)}</b></div>
            <div className="o-kpi"><span className="phu">Biên lãi gộp 12 tháng</span>
              <b>{dt12 > 0 ? pc(lg12 / dt12) : "—"}</b></div>
            <div className="o-kpi"><span className="phu">Khách đang mua / đã ngừng</span>
              <b>{so(h.so_dang_mua)} / {so(h.so_da_ngung)}</b></div>
          </div>
          <The tieu_de="24 tháng" cach_tinh={h.cach_tinh.thang}>
            <BieuDo nhan={h.thang.map(x => `${+x.thang.slice(5)}/${x.thang.slice(2, 4)}`)} cao={220} moi_nhan={2}
              chuoi={[
                { ten: "Cùng tháng năm trước", kieu: "cot_nen", gia_tri: h.thang.map(x => x.dt_nam_truoc), mau: "var(--chu-mo)" },
                { ten: "Doanh thu", kieu: "cot", gia_tri: h.thang.map(x => x.doanh_thu), mau: "var(--ok-vien)" },
                { ten: "Lãi gộp", kieu: "duong", gia_tri: h.thang.map(x => x.lai_gop), mau: "var(--lien-ket)" },
              ]}
              dinh_dang={v => yen(v)} dinh_dang_truc={v => yen(v)}
              onBam={i => { datThangNgay(h.thang[i].thang); chonTab("thoi_gian"); }}
              mo_ta="Doanh thu và lãi gộp 24 tháng, cột mờ là cùng tháng năm trước; bấm một tháng để xem theo ngày" />
          </The>
          <div className="hs-tab" role="tablist">
            {TAB.map(([m, nhan]) => (
              <button key={m} type="button" role="tab" aria-selected={tab === m} onClick={() => chonTab(m)}>{nhan}</button>))}
          </div>
          <div role="tabpanel">
            {tab === "khach" && <TabKhach ma={ma} khoang={kh} />}
            {tab === "thoi_gian" && <TabThoiGian ma={ma} thang={thangNgay ?? h.hom_nay?.slice(0, 7) ?? null} />}
            {tab === "gia" && <TabGia ma={ma} thang={h.thang} />}
            {tab === "ban_them" && <TabBanThem ma={ma} ngungBan={h.ngung_ban} nganh={h.nganh} />}
          </div>
        </div>
      </div>
    </div>);
}
```

Thay `useQuery<any>` cho `/khoang` bằng kiểu có sẵn trong `san_pham/kieu.ts` (kiểu mà `HoSoSanPham.tsx` cũ đã dùng cho `/api/san-pham/{mã}/khoang`); đọc trường so sánh đúng như `HoSoSanPham.tsx` cũ đọc (xem file cũ trước khi xoá). Kiểm lớp `o-kpi` đúng tên lớp ô số trong `OSoSucKhoe` (`khach/HoSoTab.tsx:66-88`) — chép cấu trúc HTML ô của nó.

Trong Task 6, tạo tạm bốn file tab tối thiểu để build qua (Task 7 viết thật):

```tsx
// ho_so/TabKhach.tsx (tạm — Task 7 thay)
export function TabKhach(_: { ma: string; khoang: unknown }) { return <p className="phu">Đang dựng…</p>; }
```
(tương tự `TabThoiGian({ma, thang})`, `TabGia({ma, thang})`, `TabBanThem({ma, ngungBan, nganh})`.)

- [ ] **Step 9: `ho_so/ho_so.css`**

```css
/* Sản phẩm 360 — chỉ phần riêng; bố cục hai cột dùng .hs2-* của khach.css. */
.sp3-so-lon { font-size: 1.8rem; font-weight: 700; margin: 0; font-variant-numeric: tabular-nums; }
.sp3-canh { color: var(--canh-chu, var(--chu)); background: var(--canh-nen, transparent); border-radius: 6px; padding: .25rem .5rem; margin: .25rem 0; }
.sp3-luoi-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.sp3-thanh { display: grid; grid-template-columns: minmax(0, 12rem) minmax(0, 1fr) auto; gap: .5rem; align-items: center; }
.sp3-thanh i { display: block; height: .6rem; border-radius: 3px; background: var(--ok-vien); }
@media (max-width: 900px) { .sp3-luoi-2 { grid-template-columns: minmax(0, 1fr); } }
```
Kiểm tên biến màu `--canh-chu`/`--canh-nen` trong `kome/web/static/kome.css` hoặc `giao_dien/src/**.css` (`grep -rn "\-\-canh" giao_dien/src kome/web/static | head`) và dùng đúng tên có thật.

- [ ] **Step 10: Xoá `HoSoSanPham.tsx`** — trước khi xoá, chép `BanTheoNgay` và `XuHuong` (cùng hằng `CHI_SO` và các import chúng cần) sang `ho_so/TabThoiGian.tsx` dưới dạng hàm chưa export (Task 7 dùng). Rồi `git rm giao_dien/src/san_pham/HoSoSanPham.tsx`.

- [ ] **Step 11: Build + test**

Run: `cd giao_dien && npx tsc -b && npm test && cd ..`
Expected: không lỗi kiểu, vitest xanh.
Run: `pytest tests/test_san_pham.py -v`
Expected: PASS (trừ `test_nguon_dung.py::test_giao_dien_doc_co_tinh_nang…` sẽ xanh sau Task 7 — không chạy file đó ở bước này).

- [ ] **Step 12: Commit** (chưa build `spa/` — build ở Task 8)

```bash
git add giao_dien/src tests/test_san_pham.py tests/test_nguon_dung.py
git commit -m "feat(giao-dien): khung trang rieng San pham 360 + cot trai, bo ho so duoi danh muc

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Giao diện — bốn tab

**Files:**
- Modify: `giao_dien/src/san_pham/ho_so/TabKhach.tsx`, `TabThoiGian.tsx`, `TabGia.tsx`, `TabBanThem.tsx`
- Test: `tests/test_san_pham.py` (thêm test đọc mã nguồn)

**Interfaces:**
- Consumes: kiểu `Tab*Api`, `ThangMa`, `LoTon` (Task 6); `LuoiTinh` (Task 6); `The`, `BieuDo`; `TN` từ `khoi_dau`.
- Produces: `TabKhach({ma, khoang})`, `TabThoiGian({ma, thang})`, `TabGia({ma, thang})`, `TabBanThem({ma, ngungBan, nganh})`.

- [ ] **Step 1: Test đọc mã nguồn (thất bại)** — thêm vào `tests/test_san_pham.py`:

```python
def test_bon_tab_360_tai_luoi_va_link_khach_san_pham():
    ho = _SRC / "ho_so"
    tabs = {f: (ho / f).read_text(encoding="utf-8") for f in
            ("TabKhach.tsx", "TabThoiGian.tsx", "TabGia.tsx", "TabBanThem.tsx")}
    assert "/api/san-pham/${encodeURIComponent(ma)}/khach" in tabs["TabKhach.tsx"]
    assert "/thoi-gian" in tabs["TabThoiGian.tsx"] and "/ngay?thang=" in tabs["TabThoiGian.tsx"]
    assert "/gia" in tabs["TabGia.tsx"] and "TN.bang_gia" in tabs["TabGia.tsx"]
    assert "/ban-them" in tabs["TabBanThem.tsx"]
    assert "/khach-hang/${encodeURIComponent(" in tabs["TabKhach.tsx"] + tabs["TabGia.tsx"] + tabs["TabBanThem.tsx"]
    assert "/san-pham/${encodeURIComponent(" in tabs["TabBanThem.tsx"], "mua kèm phải link sang mã kia"
    assert "Đang dựng" not in "".join(tabs.values())
    for sai in ("ton ?? 0", "ton || 0"):
        assert sai not in "".join(tabs.values())
```

Run: `pytest tests/test_san_pham.py -k bon_tab_360 -v` → FAIL.

- [ ] **Step 2: `TabKhach.tsx`**

```tsx
// Tab Khách hàng — Pareto tập trung · 47 tỉnh · người phụ trách · khách mới/quay lại · bảng khách.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { LuoiTinh } from "../../chung/LuoiTinh";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../../khung/khoang";
import { gon, ngay, pc, so, so_luong as soLuong, yen } from "../../dinh_dang";
import type { KhachDong, TabKhachApi } from "./kieu";

const lk = (ma: string) => giuKhoang(`/khach-hang/${encodeURIComponent(ma)}`);

export function TabKhach({ ma, khoang }: { ma: string; khoang: { khach?: { ma: string; ten: string; doanh_thu: number; so_luong: number | null; so_ngay: number; lan_cuoi: string }[] } | undefined }) {
  const kx = chuoiKhoang(useKhoang());
  const { data, error } = useQuery<TabKhachApi>({ queryKey: ["sp360-khach", ma, kx],
    queryFn: () => lay<TabKhachApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/khach`)) });
  if (error) return <div className="khoi-loi">Không tải được tab Khách hàng: {(error as Error).message}</div>;
  if (!data) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const t = data.t, ct = data.cach_tinh, top = t.tap_trung.slice(0, 30);
  return (<>
    <div className="sp3-luoi-2">
      <The tieu_de="Tập trung khách" cach_tinh={ct.tap_trung}
        phu={t.top10_ty_trong == null ? "Chưa có doanh thu 12 tháng." : `10 khách lớn nhất chiếm ${pc(t.top10_ty_trong)} doanh thu 12 tháng của mã (${so(t.tap_trung.length)} khách).`}>
        {top.length > 0 && <BieuDo nhan={top.map((_, i) => String(i + 1))} nhan_day_du={top.map(k => k.ten)} cao={200}
          chuoi={[{ ten: "Doanh thu", kieu: "cot", gia_tri: top.map(k => k.doanh_thu), mau: "var(--ok-vien)" },
                  { ten: "Luỹ kế %", kieu: "duong", gia_tri: top.map(k => k.luy_ke == null ? null : k.luy_ke * 100), mau: "var(--lien-ket)", truc_phai: true }]}
          dinh_dang={(v, c) => c.truc_phai ? `${(v ?? 0).toFixed(1)}%` : yen(v)} dinh_dang_truc={v => gon(v)}
          onBam={i => { location.href = lk(top[i].ma); }} mo_ta="Doanh thu 12 tháng theo khách xếp giảm dần, đường luỹ kế phần trăm" />}
      </The>
      <The tieu_de="Theo tỉnh" cach_tinh={ct.tinh}
        phu={t.tinh.khong_ro ? `Không rõ tỉnh: ${yen(t.tinh.khong_ro)}.` : undefined}>
        <LuoiTinh o={t.tinh.o} rong={t.tinh.rong} cao={t.tinh.cao} o_rong={t.tinh.o_rong} o_cao={t.tinh.o_cao}
          nhan={o => gon(o.doanh_thu)} mo_ta="Doanh thu 12 tháng của mã theo 47 tỉnh"
          noi={o => <><strong className="ten-jp">{o.ten}</strong><div>Doanh thu <b>{yen(o.doanh_thu)}</b></div><div>Khách <b>{so(o.so_khach)}</b></div></>} />
      </The>
    </div>
    <div className="sp3-luoi-2">
      <The tieu_de="Theo người phụ trách" cach_tinh={ct.nguoi}>
        {!t.nguoi.length ? <p className="phu">Chưa bán trong 12 tháng.</p> :
          <table className="bang"><thead><tr><th>Người phụ trách</th><th className="so">Doanh thu</th><th className="so">Biên</th><th className="so">Khách</th></tr></thead>
            <tbody>{t.nguoi.map(n => (<tr key={n.ma}>
              <td>{n.ten ?? `(mã ${n.ma || "trống"} không có trong danh sách phụ trách)`}</td>
              <td className="so">{yen(n.doanh_thu)}</td><td className="so">{n.doanh_thu > 0 ? pc(n.lai_gop / n.doanh_thu) : "—"}</td>
              <td className="so">{so(n.so_khach)}</td></tr>))}</tbody></table>}
      </The>
      <The tieu_de="Khách mới / quay lại theo tháng" cach_tinh={ct.khach_moi}>
        <BieuDo nhan={t.khach_moi.map(x => `${+x.thang.slice(5)}/${x.thang.slice(2, 4)}`)} cao={180}
          chuoi={[{ ten: "Quay lại", kieu: "cot", gia_tri: t.khach_moi.map(x => x.quay_lai), mau: "var(--chu-mo)" },
                  { ten: "Mới", kieu: "cot", gia_tri: t.khach_moi.map(x => x.moi), mau: "var(--ok-vien)" }]}
          dinh_dang={v => so(v)} mo_ta="Số khách mới và khách quay lại mua mã này theo tháng" />
      </The>
    </div>
    {khoang?.khach && khoang.khach.length > 0 && <The tieu_de="Khách mua trong khoảng xem">
      <table className="bang"><thead><tr><th>Khách</th><th className="so">Doanh thu</th><th className="so">SL</th><th className="so">Ngày mua</th><th>Lần cuối</th></tr></thead>
        <tbody>{khoang.khach.map(k => (<tr key={k.ma}><td><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a></td>
          <td className="so">{yen(k.doanh_thu)}</td><td className="so">{soLuong(k.so_luong)}</td><td className="so">{so(k.so_ngay)}</td><td>{ngay(k.lan_cuoi)}</td></tr>))}</tbody></table>
    </The>}
    <div className="sp3-luoi-2">
      <BangKhach tieu_de="Khách đang mua" ds={t.dang_mua} rong="Chưa khách nào đang mua đều." />
      <BangKhach tieu_de="Khách đã ngừng mua mã này" ds={t.da_ngung} rong="Không khách nào ngừng mua (im lặng ≥ 2× nhịp riêng)." />
    </div>
  </>);
}

function BangKhach({ tieu_de, ds, rong }: { tieu_de: string; ds: KhachDong[]; rong: string }) {
  return (<The tieu_de={tieu_de}>
    {!ds.length ? <p className="phu">{rong}</p> :
      <table className="bang"><thead><tr><th>Khách</th><th className="so">Doanh thu</th><th className="so">Nhịp</th><th>Lần cuối</th></tr></thead>
        <tbody>{ds.map(k => (<tr key={k.ma}><td><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a></td>
          <td className="so">{yen(k.doanh_thu)}</td><td className="so">{k.nhip == null ? "—" : `${Math.round(k.nhip)} ngày`}</td>
          <td>{ngay(k.lan_cuoi)}</td></tr>))}</tbody></table>}
  </The>);
}
```

- [ ] **Step 3: `TabThoiGian.tsx`** — giữ `BanTheoNgay` đã chép ở Task 6 (đổi nó nhận `ma` + `thang` từ props thay vì state cũ), thêm:

```tsx
// Tab Thời gian — bán theo ngày (khối cũ, /ngay) · 26 tuần · nhịp mua lại · cỡ đơn.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, useKhoang, voiKhoang } from "../../khung/khoang";
import { so, so_luong as soLuong, yen } from "../../dinh_dang";
import type { TabThoiGianApi } from "./kieu";
// (+ các import mà BanTheoNgay cần — giữ nguyên như đã chép)

const NHAN_NHIP: Record<string, string> = { "≤7": "≤ 7 ngày", "8–14": "8–14", "15–30": "15–30", "31–60": "31–60", ">60": "> 60", chua_du: "chưa đủ 3 lần" };
const NHAN_CO: Record<string, string> = { tra_lai: "trả lại (赤伝)", khong_sl: "không số lượng" };

export function TabThoiGian({ ma, thang }: { ma: string; thang: string | null }) {
  const kx = chuoiKhoang(useKhoang());
  const { data, error } = useQuery<TabThoiGianApi>({ queryKey: ["sp360-tg", ma, kx],
    queryFn: () => lay<TabThoiGianApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/thoi-gian`)) });
  return (<>
    {thang && <BanTheoNgay ma={ma} thangDau={thang} />}
    {error ? <div className="khoi-loi">Không tải được tab Thời gian: {(error as Error).message}</div> :
     !data ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div> : <>
      <The tieu_de="26 tuần" cach_tinh={data.cach_tinh.tuan}>
        <BieuDo nhan={data.t.tuan.map(x => x.tuan.slice(5).split("-").reverse().join("/"))} cao={180} moi_nhan={2}
          chuoi={[{ ten: "Số lượng", kieu: "cot", gia_tri: data.t.tuan.map(x => x.so_luong), mau: "var(--ok-vien)" },
                  { ten: "Doanh thu", kieu: "duong", gia_tri: data.t.tuan.map(x => x.doanh_thu), mau: "var(--lien-ket)", truc_phai: true, an_mac_dinh: true }]}
          dinh_dang={(v, c) => c.truc_phai ? yen(v) : soLuong(v)} mo_ta="Số lượng bán theo tuần, 26 tuần gần nhất" />
      </The>
      <div className="sp3-luoi-2">
        <The tieu_de="Nhịp mua lại của khách" cach_tinh={data.cach_tinh.nhip}>
          <BieuDo nhan={data.t.nhip.map(x => NHAN_NHIP[x.nhom] ?? x.nhom)} cao={170}
            chuoi={[{ ten: "Số cặp khách–mã", kieu: "cot", gia_tri: data.t.nhip.map(x => x.so_cap), mau: "var(--ok-vien)" }]}
            dinh_dang={v => so(v)} mo_ta="Phân bố nhịp mua lại (ngày) của các khách mua mã này" />
        </The>
        <The tieu_de="Cỡ đơn mỗi lần mua" cach_tinh={data.cach_tinh.co_don}>
          {!data.t.co_don.length ? <p className="phu">Chưa bán trong 12 tháng.</p> :
            <table className="bang"><thead><tr><th>Quy cách</th><th>Số lượng / dòng</th><th className="so">Số dòng</th><th className="so">Tổng SL</th></tr></thead>
              <tbody>{data.t.co_don.map(x => (<tr key={x.pack_code + x.nhom}>
                <td>{x.quy_cach}</td><td>{NHAN_CO[x.nhom] ?? x.nhom}</td><td className="so">{so(x.so_dong)}</td><td className="so">{soLuong(x.so_luong)}</td></tr>))}</tbody></table>}
        </The>
      </div></>}
  </>);
}
```

`BanTheoNgay` cũ tự giữ state tháng; đổi thành `useState(thangDau)` + `useEffect(() => datThang(thangDau), [thangDau])` để bấm tháng ở biểu đồ 24 tháng mở đúng tháng. Xoá hàm `XuHuong` đã chép (biểu đồ 24 tháng ở HoSoMa thay nó).

- [ ] **Step 4: `TabGia.tsx`**

```tsx
// Tab Giá & lãi — đơn giá thực theo tháng × quy cách (cạnh giá bảng bậc) · biên theo tháng ·
// khách giá thấp / biên thấp · bảng giá theo bậc.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../../khung/khoang";
import { ngay, pc, so, yen } from "../../dinh_dang";
import { TN } from "../../khoi_dau";
import type { TabGiaApi, ThangMa } from "./kieu";

const lk = (ma: string) => giuKhoang(`/khach-hang/${encodeURIComponent(ma)}`);
const MAU = ["var(--ok-vien)", "var(--lien-ket)", "var(--canh-vien)", "var(--do)"];

export function TabGia({ ma, thang }: { ma: string; thang: ThangMa[] }) {
  const kx = chuoiKhoang(useKhoang());
  const { data, error } = useQuery<TabGiaApi>({ queryKey: ["sp360-gia", ma, kx],
    queryFn: () => lay<TabGiaApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/gia`)) });
  if (error) return <div className="khoi-loi">Không tải được tab Giá & lãi: {(error as Error).message}</div>;
  if (!data) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const t = data.t, ct = data.cach_tinh;
  const cacThang = [...new Set(t.don_gia.map(x => x.thang))].sort();
  const cacQc = [...new Set(t.don_gia.map(x => x.pack_code))];
  const t12 = thang.slice(-12);
  const theoGia = [...t.khach_gia].filter(k => k.don_gia != null).sort((a, b) => (a.don_gia! - b.don_gia!)).slice(0, 10);
  const theoBien = [...t.khach_gia].sort((a, b) => ((a.bien ?? 0) - (b.bien ?? 0))).slice(0, 10);
  return (<>
    <The tieu_de="Đơn giá thực bán theo tháng" cach_tinh={ct.don_gia}
      phu={t.bac_gia.length ? `Giá bảng mới nhất: ${t.bac_gia.map(g => `bậc ${g.bac} · ${g.quy_cach} ${yen(g.gia)}`).slice(0, 4).join(" · ")}` : "Chưa có bảng giá của mã này."}>
      {!cacThang.length ? <p className="phu">Chưa bán trong 12 tháng.</p> :
        <BieuDo nhan={cacThang.map(x => `${+x.slice(5)}/${x.slice(2, 4)}`)} cao={200}
          chuoi={cacQc.map((q, i) => ({ ten: t.don_gia.find(x => x.pack_code === q)!.quy_cach, kieu: "duong" as const,
            gia_tri: cacThang.map(th => t.don_gia.find(x => x.thang === th && x.pack_code === q)?.don_gia ?? null), mau: MAU[i % MAU.length] }))}
          dinh_dang={v => yen(v == null ? null : Math.round(v))} mo_ta="Đơn giá thực bán theo tháng, mỗi quy cách một đường" />}
    </The>
    <The tieu_de="Biên lãi gộp theo tháng" cach_tinh={ct.bien}>
      <BieuDo nhan={t12.map(x => `${+x.thang.slice(5)}/${x.thang.slice(2, 4)}`)} cao={170}
        chuoi={[{ ten: "Biên", kieu: "duong", gia_tri: t12.map(x => x.doanh_thu > 0 ? x.lai_gop / x.doanh_thu * 100 : null), mau: "var(--ok-vien)" }]}
        dinh_dang={v => v == null ? "—" : `${v.toFixed(1)}%`} mo_ta="Biên lãi gộp của mã theo tháng, 12 tháng" />
    </The>
    <div className="sp3-luoi-2">
      <BangGia tieu_de="Khách mua giá thấp nhất" ds={theoGia} ct={ct.khach_gia} />
      <BangGia tieu_de="Khách biên thấp nhất" ds={theoBien} ct={ct.khach_gia} />
    </div>
    {TN.bang_gia && t.bac_gia.length > 0 && <The tieu_de="Giá theo bậc (売価No.)">
      <table className="bang"><thead><tr><th>Bậc</th><th>Quy cách</th><th className="so">Giá (chưa thuế)</th><th>Từ ngày</th></tr></thead>
        <tbody>{t.bac_gia.map(g => (<tr key={g.bac + g.pack_code}><td>{g.bac}</td><td>{g.quy_cach}</td><td className="so">{yen(g.gia)}</td><td>{ngay(g.tu_ngay)}</td></tr>))}</tbody></table>
    </The>}
  </>);
}

function BangGia({ tieu_de, ds, ct }: { tieu_de: string; ds: TabGiaApi["t"]["khach_gia"]; ct: string }) {
  return (<The tieu_de={tieu_de} cach_tinh={ct}>
    {!ds.length ? <p className="phu">Chưa khách nào mua ≥ 2 ngày trong 12 tháng.</p> :
      <table className="bang"><thead><tr><th>Khách</th><th className="so">Đơn giá</th><th className="so">Biên</th><th className="so">Doanh thu</th><th className="so">Ngày mua</th></tr></thead>
        <tbody>{ds.map(k => (<tr key={k.ma}><td><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a></td>
          <td className="so">{k.don_gia == null ? "—" : yen(Math.round(k.don_gia))}</td><td className="so">{pc(k.bien)}</td>
          <td className="so">{yen(k.doanh_thu)}</td><td className="so">{so(k.so_lan)}</td></tr>))}</tbody></table>}
  </The>);
}
```

Kiểm `TN.bang_gia` vẫn là tên cờ trong `khoi_dau.ts` (file cũ `HoSoSanPham.tsx:150` dùng nó).

- [ ] **Step 5: `TabBanThem.tsx`**

```tsx
// Tab Tồn & bán thêm — tồn theo lô · mua kèm cùng phiếu · khách nên chào đầy đủ.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../../khung/khoang";
import { ngay, pc, so, so_luong as soLuong, yen } from "../../dinh_dang";
import type { TabBanThemApi } from "./kieu";

export function TabBanThem({ ma, ngungBan, nganh }: { ma: string; ngungBan: boolean; nganh: string }) {
  const kx = chuoiKhoang(useKhoang());
  const { data, error } = useQuery<TabBanThemApi>({ queryKey: ["sp360-bt", ma, kx],
    queryFn: () => lay<TabBanThemApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/ban-them`)) });
  if (error) return <div className="khoi-loi">Không tải được tab Tồn & bán thêm: {(error as Error).message}</div>;
  if (!data) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const t = data.t, ct = data.cach_tinh;
  return (<>
    <The tieu_de="Tồn theo lô" goc={<a className="nut-nho" href={giuKhoang(`/kho-hang?tim=${encodeURIComponent(ma)}`)}>Mở Kho hàng ›</a>}>
      {!t.ton.length ? <p className="phu">Chưa có ảnh chụp tồn của mã này tới thời điểm này.</p> :
        <table className="bang"><thead><tr><th>Lô</th><th className="so">Số lượng</th><th>Hạn</th><th className="so">Bán từ / hết sau</th></tr></thead>
          <tbody>{t.ton.map(l => (<tr key={l.kho + (l.best_before ?? "")}>
            <td className="ten-jp">{l.ten_kho} <span className="phu">({l.vai_tro_lo})</span></td>
            <td className="so">{l.so_luong == null ? "—" : soLuong(l.so_luong)}</td>
            <td><span className={"nhan-vien " + l.mau_han}>{l.nhan_han}</span> {l.best_before ?? ""}</td>
            <td className="so">{l.bat_dau_ban_sau == null ? "—" : `${so(Math.round(l.bat_dau_ban_sau))}`} / {l.ban_het_sau == null ? "—" : `${so(Math.round(l.ban_het_sau))} ngày`}
              {l.khong_kip_ban && <span className="nhan-vien do"> không kịp bán</span>}</td></tr>))}</tbody></table>}
    </The>
    <div className="sp3-luoi-2">
      <The tieu_de="Hay được mua cùng phiếu" cach_tinh={ct.mua_kem}
        phu={t.tong_phieu ? `Trên ${so(t.tong_phieu)} phiếu có mã này trong 12 tháng.` : undefined}>
        {!t.mua_kem.length ? <p className="phu">Chưa có phiếu nào có mã này cùng mã khác.</p> :
          <ul className="sp3-thanh-ds">{t.mua_kem.map(k => (
            <li key={k.ma} className="sp3-thanh"><a className="ten-jp" href={giuKhoang(`/san-pham/${encodeURIComponent(k.ma)}`)}>{k.ten}</a>
              <i style={{ width: `${Math.round((k.ty_le ?? 0) * 100)}%` }} /><span className="so">{pc(k.ty_le)} · {so(k.so_phieu)} phiếu</span></li>))}</ul>}
      </The>
      <The tieu_de="Khách nên chào" cach_tinh={ct.nen_chao}>
        {ngungBan ? <p className="phu">Không chào hàng đã ngừng kinh doanh (※終売※).</p> :
          !t.nen_chao.length ? <p className="phu">Chưa có khách mua đều mã cùng ngành ({nganh}) mà chưa mua mã này.</p> :
          <table className="bang"><thead><tr><th>Khách</th><th className="so">DT ngành 12 tháng</th><th className="so">Mã cùng ngành</th><th>Mua cuối</th></tr></thead>
            <tbody>{t.nen_chao.map(k => (<tr key={k.ma}><td><a className="ten-jp" href={giuKhoang(`/khach-hang/${encodeURIComponent(k.ma)}`)}>{k.ten}</a></td>
              <td className="so">{yen(k.doanh_thu_nganh)}</td><td className="so">{so(k.so_ma_nganh)}</td><td>{ngay(k.lan_cuoi)}</td></tr>))}</tbody></table>}
      </The>
    </div>
  </>);
}
```

Thêm `.sp3-thanh-ds { list-style: none; padding: 0; margin: 0; display: grid; gap: .35rem; }` vào `ho_so.css`.

- [ ] **Step 6: Build + test**

Run: `cd giao_dien && npx tsc -b && npm test && cd .. && pytest tests/test_san_pham.py tests/test_nguon_dung.py -v`
Expected: không lỗi kiểu; tất cả PASS.

- [ ] **Step 7: Commit**

```bash
git add giao_dien/src tests/test_san_pham.py
git commit -m "feat(giao-dien): bon tab San pham 360 (khach, thoi gian, gia, ban them)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Build, tài liệu sinh, CLAUDE.md, kiểm trên trình duyệt

**Files:**
- Modify: `kome/web/spa/**` (build), `kome/web/tai_lieu_sinh.json`, `kome/web/cot_dung_sinh.json`, `scripts/sinh_cot_dung.py`, `CLAUDE.md`

- [ ] **Step 1: Khai mô-đun mới vào `MAN`**

Run: `grep -n "MAN = \|MAN=\|\"kome/san_pham.py\"\|san_pham" scripts/sinh_cot_dung.py | head`
Thêm mục cho `kome/san_pham_360.py` cạnh mục `kome/san_pham.py`, cùng hình dạng (màn `/san-pham/{mã}`).

- [ ] **Step 2: Build giao diện**

Run: `cd giao_dien && npm run build && cd ..`
Expected: build xong, `kome/web/spa/.nguon` cập nhật.

- [ ] **Step 3: Sinh lại tài liệu sống**

Run: `python scripts/sinh_tai_lieu.py && python scripts/sinh_cot_dung.py`
Expected: hai file JSON cập nhật (051–053 vào danh sách migration).

- [ ] **Step 4: CLAUDE.md** — trong bảng "Các trang của web app":
  - Dòng `/san-pham`: bỏ "hồ sơ mã đang chọn ngay bên dưới"; thêm "bấm dòng mở trang riêng `/san-pham/{mã}` (nhớ thứ tự danh mục cho ‹ n/N ›, `sessionStorage`)".
  - Dòng `/san-pham/{mã}`: thay bằng
    "**Sản phẩm 360 — trang riêng React** (2026-09-26, đặc tả `2026-09-26-san-pham-360-trang-rieng-design.md`): bố cục hồ sơ khách 360 — cột trái dính 'Việc với mã này' (tồn + cảnh báo lô · khách đến ngày mua lại — CÙNG vị từ `ho_so_khach.lich_mua` · khách nên chào), cột phải 4 ô số + 24 tháng (cột mờ năm trước; bấm tháng → tab Thời gian) + 4 tab tải lười: Khách hàng (Pareto · 47 tỉnh · người phụ trách · mới/quay lại) · Thời gian (ngày · 26 tuần · nhịp · cỡ đơn) · Giá & lãi (đơn giá thực × quy cách · biên · khách giá/biên thấp · giá bậc) · Tồn & bán thêm (lô · mua kèm cùng phiếu · khách nên chào). `/api/san-pham/{mã}` (4 lượt, trần 5) + `/khoang` (2) + `/khach` (3) · `/thoi-gian` (2) · `/gia` (2) · `/ban-them` (2) · `/ngay` (1)" — cột nguồn: `mart.san_pham_360`, `san_pham_theo_thang`, `ton_theo_lo`, `khach_mat_hang`, `mart.sp_*` (051–053), `core.fact_price_list`.
  - Thêm mục bất biến sau mục 050:

    ```markdown
    **Bất biến (051–053, Sản phẩm 360 — 2026-09-26):** mười chỉ số của trang riêng là hàm
    `mart.sp_*(mã)` đọc `mart.ban_den_moc` (quay về theo mốc, bỏ mã nội bộ). Tập trung khách gộp
    theo KHÁCH; 47 tỉnh LEFT JOIN từ `dim_prefecture` (bậc 0 = đúng bằng 0); đơn giá thực = Σ DT
    thuần ÷ Σ qty (tỷ số các tổng, Σ qty ≤ 0 → NULL); cỡ đơn đếm dòng 赤伝 riêng; mua kèm bỏ phí /
    POSM / ※終売※ hết tồn; khách nên chào = khách `trang_thai_cap = 'mua'` với mã cùng ngành, chưa
    từng mua mã này, rỗng với mã ※終売※. "Khách đến ngày mua lại" dùng ĐÚNG vị từ của
    `kome/ho_so_khach.py::lich_mua` (có test canh hai chiều:
    `tests/test_san_pham_360.py::test_mua_lai_TRUNG_TAP_voi_lich_mua_cua_ho_so_khach`). Có test canh:
    `tests/test_mart_sp360.py`. **Migration 051–053 phải chạy TRƯỚC khi triển khai.**
    ```

- [ ] **Step 5: Chạy toàn bộ test** (không chạy song song với phiên khác trên `kome_test`)

Run: `pytest -q`
Expected: tất cả PASS. Đặc biệt `tests/test_api.py::test_ban_build_khop_ma_nguon`, `tests/test_tai_lieu.py::test_anh_chup_tai_lieu_khong_cu`, `tests/test_cot_dung.py`.

- [ ] **Step 6: Kiểm trên trình duyệt**

Mở preview (`.claude/launch.json` — dùng cấu hình máy chủ web có sẵn; nếu chưa có thì thêm `uvicorn kome.web.app:app --port 8000`), vào `/san-pham`, bấm một mã có doanh thu:
- trang riêng mở, cột trái dính khi cuộn, 4 ô số có số, biểu đồ 24 tháng có cột mờ;
- bấm từng tab: không lỗi console, mỗi tab một request `/api/san-pham/{mã}/<tab>` 200;
- bấm tên khách → sang `/khach-hang/{mã}`; ở hồ sơ khách bấm một mã → về trang riêng;
- ‹ › đi đúng thứ tự danh mục; `?thang=` được giữ khi chuyển trang;
- thu hẹp < 900px: một cột.
Chụp màn hình làm bằng chứng.

- [ ] **Step 7: Đo trên CSDL thật (chỉ đọc)** — với một mã bán chạy, đo `SELECT * FROM mart.sp_khach_nen_chao('<mã>')` và `mart.sp_mua_kem('<mã>')` trong `BEGIN READ ONLY` qua `kome_app` (xem memory "Pooler giữ SET": không `SET` cấp phiên). Ghi thời gian vào đặc tả §5. Quá 500 ms thì báo lại trước khi triển khai — không tự đổi thiết kế.

- [ ] **Step 8: Commit**

```bash
git add kome/web/spa kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json scripts/sinh_cot_dung.py CLAUDE.md docs/superpowers/specs/2026-09-26-san-pham-360-trang-rieng-design.md
git commit -m "build: San pham 360 trang rieng + tai lieu sinh + CLAUDE.md

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
