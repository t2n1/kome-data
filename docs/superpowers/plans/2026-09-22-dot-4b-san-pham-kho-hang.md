# Đợt 4b — Sản phẩm · Kho hàng: Kế hoạch triển khai

> **Dành cho người thực thi (kể cả tác nhân AI):** BẮT BUỘC dùng kỹ năng
> `superpowers:subagent-driven-development` (khuyến nghị) hoặc
> `superpowers:executing-plans`. Các bước dùng ô đánh dấu (`- [ ]`).

**Mục tiêu:** ba trang mới — `/san-pham`, `/san-pham/{mã}`, `/kho-hang` — theo gói
thiết kế, trừ những khối không có dữ liệu.

**Kiến trúc:** mọi chỉ số mới nằm trong `mart` (migration `023`). Tầng Python là một
file mới `kome/san_pham.py` chỉ hiển thị và lọc. Ngân sách vòng hỏi: `/san-pham` ≤ 2,
`/san-pham/{mã}` ≤ 5, `/kho-hang` ≤ 2 — cả ba có test đếm.

**Công nghệ:** Python 3.12 · FastAPI · Jinja2 · psycopg 3 · Postgres · SVG tự tính toạ
độ. **Không thêm gói, không một dòng JavaScript.**

**Đặc tả:** `docs/superpowers/specs/2026-09-22-dot-4b-san-pham-kho-hang-design.md`

---

## Ràng buộc toàn cục

- **Không thêm gói** vào `requirements.txt` / `pyproject.toml`. **Không một dòng JavaScript.**
- **Định nghĩa chỉ số CHỈ nằm ở `mart/`.** `kome/san_pham.py` hiển thị và lọc, không tính.
- **Migration LUÔN chạy bằng vai trò `postgres`**; file đã chạy thì KHÔNG sửa, chỉ thêm
  file mới. File mới của đợt này là `023_mart_san_pham.sql`.
- Mọi route chỉ đọc dùng `open_app_conn`; chỉ `upload`/`kho_du_lieu`/`undo` dùng
  `open_conn`. **Có test duyệt AST canh** — ba route mới sẽ bị nó soi.
- `kome/web/app.py` KHÔNG nhập `kome.pipeline`/pandas/calamine ở mức ngoài cùng.
- Mọi template `include "_nav.html"` phải tự đóng `</main>` đúng một lần. Có test canh.
- Mốc thời gian là `mart.moc_thoi_gian.hom_nay`, **không bao giờ** `current_date`.
- **Mã hàng là TEXT.** Không ép `int` ở bất kỳ đâu.
- **Số lượng CÓ phần thập phân** (`83.75 ケース`). Giữ `numeric`/`float`, không ép `int`.
  Tiền thì luôn là số nguyên yên.
- Ngôn ngữ code/ghi chú/commit: tiếng Việt (commit không dấu). Ghi chú giải thích
  **vì sao**, không phải *cái gì*.
- Chạy test: `python -u -m pytest -q` ở **TIỀN CẢNH**, `timeout: 600000`. Chạy nền +
  ghi ra file làm output Python bị đệm 8 KB → tưởng treo. Nếu 10 phút không đủ, chia hai
  lượt (`--ignore=tests/test_roles.py --ignore=tests/test_migrate.py`, rồi hai file đó).
- Cuối commit thêm: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## Cấu trúc file

| File | Trách nhiệm | Task |
|---|---|---|
| `db/migrations/023_mart_san_pham.sql` | **Tạo:** 4 view | 1 |
| `tests/test_mart_san_pham.py` | **Tạo:** test cho 4 view | 1 |
| `kome/san_pham.py` | **Tạo:** `danh_sach`, `ho_so`, `kho_hang` | 2 |
| `tests/test_san_pham.py` | **Tạo:** test tầng Python + đếm truy vấn | 2 |
| `kome/web/app.py` | **Sửa:** ba route mới | 3 |
| `kome/web/templates/san_pham.html`, `san_pham_360.html`, `kho_hang.html` | **Tạo** | 3 |
| `kome/web/templates/_nav.html` | **Sửa:** nhóm HÀNG HOÁ, hai mục | 3 |
| `CLAUDE.md` | **Sửa:** chỉ số mới, bất biến | 4 |

---

## Task 1: Migration 023 — bốn view

**Files:** Tạo `db/migrations/023_mart_san_pham.sql`, `tests/test_mart_san_pham.py`

**Interfaces — Task 2 đọc đúng những tên này:**
- `mart.toc_do_ban(product_code, so_luong_90n, doanh_thu_90n, toc_do_ngay)`
- `mart.ton_hien_tai(product_code, warehouse_code, ten_kho, so_luong, gia_tri, best_before, loai_han, han_con_lai)`
- `mart.san_pham_360(product_code, ten_hang, nhom, doanh_thu_thuan, lai_gop, ty_suat, so_luong_ban, ton, toc_do_ngay, du_ban_ngay, trang_thai, so_khach, lan_dau, lan_cuoi)`
- `mart.san_pham_theo_thang(product_code, thang, so_luong, doanh_thu_thuan, lai_gop)`

- [ ] **Bước 1: Viết test thất bại** — `tests/test_mart_san_pham.py`

```python
"""Chỉ số của màn Sản phẩm và Kho hàng (migration 023).

Hai thứ được canh kỹ nhất ở đây: **cột `best_before` là TEXT và có giá trị CHỮ**
(`賞味期限なし`) lẫn trong đó, nên một `to_date()` trần sẽ làm cả trang trắng; và
**"không có dòng tồn" khác "tồn bằng 0"** — nhầm hai thứ đó là xếp một mã chưa
bao giờ nhập kho vào danh sách cần đặt hàng gấp.
"""
from datetime import date, timedelta

from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY


def _ton(conn, batch, ma_hang, kho="0001", sl=100, gia=1000, han="2028年06月09日"):
    """Một dòng tồn kho ở ngày chụp HOM_NAY."""
    b = batch(abs(hash((ma_hang, kho, han))) % 70_000 + 1)
    conn.execute(
        """INSERT INTO core.dim_warehouse (warehouse_code, warehouse_name)
           VALUES (%s, %s) ON CONFLICT DO NOTHING""",
        (kho, f"Kho {kho}"))
    conn.execute(
        """INSERT INTO core.fact_inventory_daily
             (snapshot_date, product_code, warehouse_code, pack_code, product_name,
              best_before, shipped_qty, stock_qty, stock_unit_cost, stock_value, batch_id)
           VALUES (%s, %s, %s, '00', %s, %s, 0, %s, %s, %s, %s)""",
        (HOM_NAY, ma_hang, kho, f"Hàng {ma_hang}", han, sl, gia, int(sl * gia), b))
    conn.commit()


def _san_pham(conn, batch, ma_hang, ten="Hàng thử"):
    b = batch(abs(hash(("sp", ma_hang))) % 60_000 + 1)
    conn.execute(
        """INSERT INTO core.dim_product (product_code, product_name, kind_name, batch_id)
           VALUES (%s, %s, 'Gạo', %s) ON CONFLICT (product_code) DO NOTHING""",
        (ma_hang, ten, b))
    conn.commit()


def test_han_su_dung_chu_khong_lam_no_truy_van(conn, batch):
    """[CRITICAL] `賞味期限なし` nghĩa là 'không có hạn sử dụng'. Một `to_date()`
    trần trên cột này làm cả truy vấn nổ và trang trắng — và nó chỉ nổ khi có
    đúng loại hàng đó trong kho, tức sau khi đã triển khai."""
    _san_pham(conn, batch, "K001")
    _ton(conn, batch, "K001", han="賞味期限なし")
    r = conn.execute(
        """SELECT loai_han, han_con_lai FROM mart.ton_hien_tai
           WHERE product_code = 'K001'""").fetchone()
    assert r[0] == "khong_han"
    assert r[1] is None, "hàng không hạn thì không có 'còn lại bao nhiêu ngày'"


def test_han_su_dung_rong_van_dem_duoc(conn, batch):
    """Một lô không rõ hạn phải ĐẾM ĐƯỢC, không được biến mất. Đo thật: 1/177
    dòng tồn hiện tại rỗng hạn."""
    _san_pham(conn, batch, "K002")
    _ton(conn, batch, "K002", han="")
    r = conn.execute(
        "SELECT loai_han FROM mart.ton_hien_tai WHERE product_code='K002'").fetchone()
    assert r[0] == "trong"


def test_han_su_dung_ngay_tinh_duoc_so_ngay_con_lai(conn, batch):
    _san_pham(conn, batch, "K003")
    sau = HOM_NAY + timedelta(days=30)
    _ton(conn, batch, "K003", han=f"{sau.year}年{sau.month:02d}月{sau.day:02d}日")
    _mua(conn, batch, "X0001", HOM_NAY, hang="K003")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT loai_han, han_con_lai FROM mart.ton_hien_tai WHERE product_code='K003'"
    ).fetchone()
    assert r[0] == "ngay" and r[1] == 30


def test_ton_0_ma_khong_ban_gi_90_ngay_thi_KHONG_phai_het_hang(conn, batch):
    """[IMPORTANT] Mã đã ngừng kinh doanh không phải mã cần đặt gấp. Xếp nhầm
    là tạo việc giả mỗi ngày cho người phụ trách kho."""
    _san_pham(conn, batch, "K004")
    _ton(conn, batch, "K004", sl=0)
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai FROM mart.san_pham_360 WHERE product_code='K004'").fetchone()
    assert r[0] != "het_hang"


def test_ton_0_ma_CO_ban_gan_day_thi_la_het_hang(conn, batch):
    _san_pham(conn, batch, "K005")
    _ton(conn, batch, "K005", sl=0)
    _ho_so_khach(conn, batch, "KH005", "Quán K005")
    for i in range(5):
        _mua(conn, batch, "KH005", HOM_NAY - timedelta(days=i * 7), hang="K005")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai FROM mart.san_pham_360 WHERE product_code='K005'").fetchone()
    assert r[0] == "het_hang"


def test_ma_moi_ra_mat_khong_bao_gio_la_ton_chet(conn, batch):
    """[IMPORTANT] Mã vừa nhập về tuần trước bán chậm là chuyện bình thường.
    Gắn nhãn 'tồn chết' cho nó là xúi người ta xả một mã vừa mua."""
    _san_pham(conn, batch, "K006")
    _ton(conn, batch, "K006", sl=500)
    _ho_so_khach(conn, batch, "KH006", "Quán K006")
    _mua(conn, batch, "KH006", HOM_NAY - timedelta(days=5), hang="K006")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai FROM mart.san_pham_360 WHERE product_code='K006'").fetchone()
    assert r[0] != "ton_chet"


def test_ma_ton_nhieu_ban_cham_la_ton_chet(conn, batch):
    _san_pham(conn, batch, "K007")
    _ton(conn, batch, "K007", sl=10_000)
    _ho_so_khach(conn, batch, "KH007", "Quán K007")
    for i in range(3):
        _mua(conn, batch, "KH007", HOM_NAY - timedelta(days=80 + i), hang="K007")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai, du_ban_ngay FROM mart.san_pham_360 WHERE product_code='K007'"
    ).fetchone()
    assert r[0] == "ton_chet"


def test_ma_khong_co_dong_ton_thi_ton_la_NULL_khong_phai_0(conn, batch):
    """[IMPORTANT] "Không biết" khác "bằng không". 90/232 mã không có dòng tồn
    nào; hiện 0 cho chúng là nói rằng kho đã hết, và người đọc sẽ đi đặt hàng."""
    _san_pham(conn, batch, "K008")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT ton FROM mart.san_pham_360 WHERE product_code='K008'").fetchone()
    assert r[0] is None


def test_toc_do_ban_la_trung_binh_90_ngay(conn, batch):
    """Khác `mart.nhip_mua` (trung vị) CÓ CHỦ Ý — xem ghi chú trong 023."""
    _san_pham(conn, batch, "K009")
    _ho_so_khach(conn, batch, "KH009", "Quán K009")
    for i in range(9):                      # 9 lần × 6 đơn vị = 54 trong 90 ngày
        _mua(conn, batch, "KH009", HOM_NAY - timedelta(days=i * 10), hang="K009")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT so_luong_90n, toc_do_ngay FROM mart.toc_do_ban WHERE product_code='K009'"
    ).fetchone()
    assert float(r[0]) == 54.0
    assert abs(float(r[1]) - 54.0 / 90) < 0.001


def test_so_luong_giu_phan_thap_phan(conn, batch):
    """`83.75 ケース` là số thật trong dữ liệu OBC. Ép int là mất 0,75 thùng."""
    _san_pham(conn, batch, "K010")
    _ton(conn, batch, "K010", sl=83.75)
    r = conn.execute(
        "SELECT so_luong FROM mart.ton_hien_tai WHERE product_code='K010'").fetchone()
    assert abs(float(r[0]) - 83.75) < 0.001


def test_ten_kho_lay_tu_dim_warehouse(conn, batch):
    """Bộ lọc kho phải đọc từ bảng, không viết cứng tên. Thêm kho thứ ba thì nó
    phải tự xuất hiện — gói thiết kế viết cứng ba tên KHÔNG có thật trong OBC."""
    _san_pham(conn, batch, "K011")
    _ton(conn, batch, "K011", kho="9999")
    r = conn.execute(
        "SELECT ten_kho FROM mart.ton_hien_tai WHERE product_code='K011'").fetchone()
    assert r[0] == "Kho 9999"
```

- [ ] **Bước 2: Chạy test, thấy ĐỎ**

`python -u -m pytest tests/test_mart_san_pham.py -v` → `relation "mart.ton_hien_tai" does not exist`.

- [ ] **Bước 3: Viết migration** — `db/migrations/023_mart_san_pham.sql`

Bốn view, theo đúng thứ tự phụ thuộc. Điểm bắt buộc:

```sql
-- 023: chỉ số của màn Sản phẩm và màn Kho hàng (đợt 4b).
--
-- KHÔNG có MATERIALIZED VIEW — xem lý do ở 020_mart_khach_360.sql.

-- Tốc độ bán: TRUNG BÌNH số lượng mỗi ngày trong 90 ngày gần nhất.
--
-- KHÁC mart.nhip_mua (trung vị) MỘT CÁCH CÓ CHỦ Ý, và đây là chỗ người đọc sau
-- rất dễ "sửa cho nhất quán" rồi làm hỏng một trong hai:
--   * nhip_mua hỏi "khoảng cách ĐIỂN HÌNH giữa hai lần mua" — một kỳ nghỉ Tết
--     kéo trung bình lệch, nên phải dùng trung vị.
--   * toc_do_ban hỏi "bao nhiêu ngày nữa thì hết hàng" — đó là một phép chia
--     trên TỔNG lượng đã bán, nên trung bình mới đúng.
-- Hai câu hỏi khác nhau, hai công thức khác nhau.
--
-- 90 ngày chứ không phải cả lịch sử: hàng thực phẩm đổi mùa, và một mã bán chạy
-- năm ngoái mà ba tháng nay không ai mua thì trung bình toàn lịch sử sẽ nói dối
-- theo đúng hướng nguy hiểm — nó bảo hàng còn chạy trong khi nó đang chết.
CREATE VIEW mart.toc_do_ban AS
SELECT f.product_code,
       sum(f.qty)                        AS so_luong_90n,
       sum(f.amount - f.tax_amount)      AS doanh_thu_90n,
       sum(f.qty) / 90.0                 AS toc_do_ngay
FROM core.fact_sales_line f, mart.moc_thoi_gian m
WHERE f.sales_date > m.hom_nay - 90
GROUP BY f.product_code;


-- Tồn hiện tại: ảnh chụp MỚI NHẤT, một dòng mỗi (mã, kho).
--
-- best_before là TEXT và có ba dạng thật trong dữ liệu: '2028年06月09日',
-- '賞味期限なし' (không có hạn sử dụng), và rỗng. to_date() TRẦN trên cột này
-- làm cả truy vấn nổ và trang trắng — và nó chỉ nổ khi trong kho có đúng loại
-- hàng đó, tức sau khi đã triển khai. Kiểm dạng bằng regex trước.
CREATE VIEW mart.ton_hien_tai AS
SELECT i.product_code, i.warehouse_code, w.warehouse_name AS ten_kho,
       i.stock_qty AS so_luong, i.stock_value AS gia_tri, i.best_before,
       CASE WHEN i.best_before ~ '^[0-9]{4}年[0-9]{2}月[0-9]{2}日$' THEN 'ngay'
            WHEN coalesce(i.best_before, '') = ''                  THEN 'trong'
            ELSE 'khong_han' END AS loai_han,
       CASE WHEN i.best_before ~ '^[0-9]{4}年[0-9]{2}月[0-9]{2}日$'
            THEN to_date(i.best_before, 'YYYY"年"MM"月"DD"日"') - m.hom_nay
       END AS han_con_lai
FROM core.fact_inventory_daily i
JOIN core.dim_warehouse w ON w.warehouse_code = i.warehouse_code
CROSS JOIN mart.moc_thoi_gian m
WHERE i.snapshot_date = (SELECT max(snapshot_date) FROM core.fact_inventory_daily);
```

`mart.san_pham_360` gộp `dim_product` LEFT JOIN các view trên. Bốn trạng thái:

```sql
       CASE
         -- Mã mới ra mắt trong 90 ngày KHÔNG bao giờ là tồn chết: bán chậm ở
         -- tuần đầu là chuyện bình thường, gắn nhãn tồn chết là xúi người ta
         -- xả một mã vừa mua về.
         WHEN b.lan_dau > m.hom_nay - 90                      THEN 'du'
         -- Tồn 0 mà KHÔNG bán gì 90 ngày = mã đã ngừng kinh doanh, không phải
         -- mã cần đặt gấp. Xếp nhầm là tạo việc giả mỗi ngày cho người giữ kho.
         WHEN coalesce(t.ton, 0) = 0 AND coalesce(v.so_luong_90n, 0) = 0 THEN 'ngung'
         WHEN coalesce(t.ton, 0) = 0                          THEN 'het_hang'
         WHEN v.toc_do_ngay IS NULL OR v.toc_do_ngay = 0      THEN 'ton_chet'
         WHEN t.ton / v.toc_do_ngay < 14                      THEN 'sap_thieu'
         WHEN t.ton / v.toc_do_ngay > 180                     THEN 'ton_chet'
         ELSE 'du' END AS trang_thai
```

**`ton` phải là NULL khi mã không có dòng tồn nào** (không `coalesce` ở cột `ton` — chỉ
`coalesce` bên trong `CASE`). "Không biết" khác "bằng không": 90/232 mã không có dòng tồn.

`mart.san_pham_theo_thang` song song `mart.khach_theo_thang` của 015, nhóm theo
`product_code` thay vì `customer_code`.

Kết thúc file bằng `GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;`

- [ ] **Bước 4: Chạy test, thấy XANH.** Cả bộ một lần, rồi commit.

---

## Task 2: `kome/san_pham.py`

**Files:** Tạo `kome/san_pham.py`, `tests/test_san_pham.py`

**Interfaces — Task 3 dùng:**
- `danh_sach(conn, tim="", loc="", sap="doanh_thu", trang=1) -> TrangSanPham`
  (`.hang`, `.tong`, `.trang`, `.so_trang`, `.tim`, `.loc`, `.sap`, `.dem_trang_thai`)
- `ho_so(conn, ma) -> HoSoSanPham | None`
  (`.sp`, `.thang`, `.khach_mua`, `.khach_ngung`, `.ton`, `.bac_gia`)
- `kho_hang(conn, kho="", loc="") -> Kho`
  (`.ngay_chup`, `.o_tong_quan`, `.dong`, `.theo_kho`, `.can_han`, `.ds_kho`, `.kho`, `.loc`)
- `TRANG_THAI_TON` — dict nhãn + màu, đúng nếp `kome/khach_hang.py::TRANG_THAI`

- [ ] **Bước 1: Viết test thất bại** — `tests/test_san_pham.py`

Tối thiểu phải có ba test đếm truy vấn (dùng đúng nếp `tests/test_khach_hang.py::
test_ho_so_khong_qua_8_truy_van` — bọc `conn.execute` rồi đếm lúc chạy, **không** đếm
bằng AST):

```python
def test_danh_sach_san_pham_khong_qua_2_truy_van(conn, batch, monkeypatch):
    ...
    assert dem["n"] <= 2, f"danh_sach() chạy {dem['n']} truy vấn"


def test_ho_so_san_pham_khong_qua_5_truy_van(conn, batch, monkeypatch):
    ...


def test_kho_hang_khong_qua_2_truy_van(conn, batch, monkeypatch):
    ...
```

Cộng các test hành vi: mã không có dòng tồn hiện `None` chứ không phải `0`; số lượng giữ
phần thập phân qua cả tầng Python; `kho_hang()` trả `ngay_chup` bằng đúng ngày chụp mới
nhất; danh sách kho lấy từ dữ liệu chứ không viết cứng.

- [ ] **Bước 2: ĐỎ.** `ModuleNotFoundError: No module named 'kome.san_pham'`

- [ ] **Bước 3: Viết module.** Cùng nếp `kome/khach_hang.py`: dataclass ở đầu, hằng
      `MOI_TRANG`, `SAP_XEP` (danh sách trắng — **không** ghép tham số URL vào SQL),
      `TRANG_THAI_TON`; hàm nhận `conn`, không tự mở kết nối, **không tính chỉ số nào**.

      Bốn ô tổng quan của `/kho-hang` và bảng "giá trị theo kho" gộp vào **một** truy vấn
      `UNION ALL` với cột `khoi` phân biệt — đúng nếp `tong_quan_danh_ba` của 4a. Nhớ:
      `ORDER BY` phải nằm ở **lớp ngoài**, không trong nhánh `UNION ALL`.

- [ ] **Bước 4: XANH.** Cả bộ một lần, rồi commit.

---

## Task 3: Ba trang + điều hướng

**Files:** Tạo ba template; sửa `kome/web/app.py`, `kome/web/templates/_nav.html`

- [ ] **Bước 1:** ba route trong `create_app`, tất cả dùng `open_app_conn`:

```python
    @app.get("/san-pham", response_class=HTMLResponse)
    def ds_san_pham(request: Request, tim: str = "", loc: str = "",
                    sap: str = "doanh_thu", trang: int = 1):
        try:
            with open_app_conn() as conn:
                t = SP.danh_sach(conn, tim=tim, loc=loc, sap=sap, trang=trang)
            return _ve(request, "san_pham.html",
                       {"t": t, "trang_thai": SP.TRANG_THAI_TON, "trang": "san-pham"})
        except Exception as e:
            return _loi(request, "mở danh sách sản phẩm", e)
```

(và tương tự `/san-pham/{ma}`, `/kho-hang`. Chú ý: đợt 4a đã bỏ tham số `chung` khỏi
`_loi`, nên chữ ký nay là `_loi(request, viec, exc)` — **ba** tham số, và nó nằm **bên
trong** `create_app`. Đọc chữ ký thật trước khi viết.)

Nhập `from kome import san_pham as SP` ở mức ngoài cùng — module này chỉ dùng thư viện
chuẩn + psycopg, **không** kéo pandas.

- [ ] **Bước 2:** ba template. Mỗi cái `include "_chung.html"` + `_nav.html`, và **tự đóng
      `</main>` đúng một lần**. Màu và khoảng cách lấy từ `kome/web/static/kome.css`.

  - `san_pham.html` — bảng 232 mã, ô tìm, dải chip trạng thái tồn có số đếm, phân trang.
    Cột "Tồn": hiện `—` khi `None`, **không** hiện `0`.
  - `san_pham_360.html` — 5 khối theo đặc tả §4.1 mục 3–7. Biểu đồ tháng vẽ SVG như
    `kome/khach_hang.py::ve_duong`.
  - `kho_hang.html` — bốn ô tổng quan, bảng tồn (lọc theo kho + trạng thái), khối cận hạn,
    bảng giá trị theo kho. **Hiện `ngay_chup` ở đầu trang** — §5.4.

- [ ] **Bước 3:** `_nav.html` — nhóm mới **HÀNG HOÁ** với hai mục `Sản phẩm` và
      `Kho hàng`, đặt giữa nhóm KHÁCH HÀNG và nhóm HỆ THỐNG. Giữ nguyên `{% if hien_kho %}`
      của nhóm HỆ THỐNG.

- [ ] **Bước 4:** test giao diện — ba trang mở được và trả 200; `—` hiện cho mã không có
      dòng tồn; `ngay_chup` có mặt trên `/kho-hang`; ba mục điều hướng có mặt.

- [ ] **Bước 5:** chạy cả bộ (test duyệt AST sẽ soi ba route mới — nếu nó đỏ thì bạn đã
      dùng nhầm `open_conn`), rồi commit.

---

## Task 4: Tài liệu

**Files:** Sửa `CLAUDE.md`

- [ ] **Bước 1:** thêm ba trang vào bảng "Các trang của web app", kèm cột nguồn dữ liệu
      đúng (`mart.san_pham_360`, `mart.ton_hien_tai`, `mart.toc_do_ban`,
      `mart.san_pham_theo_thang`, `core.fact_price_list`).

- [ ] **Bước 2:** thêm ba bất biến:

```markdown
**Bất biến:** `mart.toc_do_ban` dùng **trung bình 90 ngày**, còn `mart.nhip_mua` dùng
**trung vị** — KHÁC NHAU CÓ CHỦ Ý. `toc_do_ban` trả lời "bao nhiêu ngày nữa thì hết
hàng" (một phép chia trên tổng lượng, nên trung bình đúng); `nhip_mua` trả lời "khoảng
cách điển hình giữa hai lần mua" (nơi một kỳ nghỉ Tết làm trung bình lệch). Đừng "sửa
cho nhất quán".

**Bất biến:** `core.fact_inventory_daily.best_before` là **TEXT** và chứa cả giá trị chữ
`賞味期限なし` lẫn chuỗi rỗng. **Không bao giờ `to_date()` trần trên cột này** — một giá
trị chữ làm cả truy vấn nổ và trang trắng, mà nó chỉ nổ khi trong kho có đúng loại hàng
đó, tức sau khi đã triển khai. `mart.ton_hien_tai` kiểm dạng bằng regex trước và phân ba
loại: `ngay` / `khong_han` / `trong`.

**Bất biến:** `mart.san_pham_360.ton` là **NULL** khi mã không có dòng tồn nào, không
phải `0`. 90/232 mã chưa từng có dòng trong `在庫一覧`. "Không biết" khác "bằng không" —
hiện `0` là nói kho đã hết, và người đọc sẽ đi đặt hàng.
```

- [ ] **Bước 3:** thêm vào mục "Bẫy đã biết": tên kho của OBC là **tên nghiệp vụ**
      (`1002 新・賞味期限用` = ngăn dùng cho hạn sử dụng), không phải địa điểm — và gói
      thiết kế viết cứng ba tên (Osaka/Nagoya/Kho lạnh Osaka) **không có thật**.

- [ ] **Bước 4:** chạy cả bộ, commit.

---

## Tự soát kế hoạch

| Mục đặc tả | Task |
|---|---|
| §4.1 (1)(2) danh sách SKU + lọc | 1, 2, 3 |
| §4.1 (3)–(7) hồ sơ mã hàng | 1, 2, 3 |
| §4.1 (8)–(11) màn kho hàng | 1, 2, 3 |
| §5.1 tốc độ bán một nhà | 1 |
| §5.2 bốn trạng thái tồn | 1 |
| §5.3 ba ca hạn sử dụng | 1 |
| §5.4 ngày chụp luôn hiện | 2, 3 |
| §5.5 ngân sách vòng hỏi | 2 |
| §8 bảng 10 test | 1, 2, 3 |

**Ba chỗ người thực thi PHẢI dừng lại hỏi:**

1. Nếu một trong ba ngân sách truy vấn không đạt được mà vẫn đọc được — báo lại,
   **đừng nới trần**.
2. Nếu `to_date` với định dạng `'YYYY"年"MM"月"DD"日"'` không chạy trên Postgres của
   Supabase — báo lại kèm thông báo lỗi thật, đừng tự đổi sang cắt chuỗi.
3. Nếu một test trong kế hoạch này sai (đã xảy ra năm lần ở các đợt trước) — **dừng lại
   hỏi trước khi sửa** khẳng định được giao nguyên văn.
