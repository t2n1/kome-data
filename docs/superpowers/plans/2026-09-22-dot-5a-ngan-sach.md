# Đợt 5a — Ngân sách: kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho chủ doanh nghiệp đặt chỉ tiêu doanh thu từng nhân viên từng tháng, rồi thấy tiến độ thật so với chỉ tiêu đó trên màn Báo cáo.

**Architecture:** Một migration dựng hai bảng `app` (chỉ tiêu + nhật ký sửa) và bốn view `mart` giữ toàn bộ công thức. Một module Python thuần (`kome/ngan_sach.py`) đọc/ghi bảng nhập, không biết gì về HTTP. Một route `/ngan-sach` gác bằng cờ boolean mới trên `app.nguoi_dung`. Bốn khối hiển thị thêm vào màn `/bao-cao` đang có.

**Tech Stack:** Postgres 15 (Supabase) · psycopg 3 · FastAPI + Jinja2 · SVG tự tính toạ độ (không thư viện biểu đồ) · pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-dot-5a-ngan-sach-design.md`

## Global Constraints

Sao chép nguyên văn từ đặc tả và từ `CLAUDE.md`. **Mọi task đều chịu ràng buộc này**, kể cả khi thân task không nhắc lại.

- **OBC 奉行 là sổ cái chính thức, dữ liệu của nó CHỈ ĐỌC.** Không `UPDATE`/`DELETE` nào chạm `core.*`.
- **Tiền luôn là số nguyên yên.** `muc_tieu` là `bigint`. Không `numeric`, không `float`.
- **Mọi định nghĩa chỉ số nằm trong `db/migrations/*.sql` (schema `mart`).** Không viết lại công thức "tiến độ" hay "mốc đến hôm nay" trong Python hay Jinja.
- **Mốc thời gian là `mart.moc_thoi_gian.hom_nay`** (ngày bán mới nhất trong kho), KHÔNG BAO GIỜ `current_date`.
- **Không sửa file migration đã chạy.** Chỉ thêm file mới. File mới của đợt này là `db/migrations/026_ngan_sach.sql` — **đúng một file**.
- **Migration luôn chạy bằng vai trò `postgres`** (`ALTER DEFAULT PRIVILEGES` không có `FOR ROLE`).
- **Mã (`*コード`) là TEXT.** `salesperson_code` là `text`, không bao giờ ép sang số.
- **Mã hoá bằng màu phải kèm thứ đọc được** (`_chung.html:76-77`): mỗi thanh tiến độ, mỗi vạch mốc phải có con số in ra cạnh nó.
- **Không thư viện JavaScript nào.** Biểu đồ vẽ bằng SVG tính sẵn ở Python, như `kome/bao_cao.py::ve_bieu_do`. Trang phải chạy cả trên Vercel (CSP chặn script ngoài) lẫn ở máy không có mạng.
- **`kome/web/app.py` KHÔNG được nhập `kome.pipeline`/pandas ở mức ngoài cùng.** Chỉ nhập trong thân route.
- **Chạy test:** `python -u -m pytest -v` — **tuần tự, chạy ở TIỀN CẢNH, KHÔNG chạy nền, KHÔNG nối ống sang `tail`/`head`.** CSDL thử nghiệm dùng chung: hai lượt `pytest` chạy song song sẽ `DROP SCHEMA` giữa lượt của nhau và sinh ra lỗi giả (`DeadlockDetected`, `UndefinedTable`). Đã xảy ra thật ba lần trở lên trong dự án này.
- **Không bao giờ ghi vào `DATABASE_URL`** (CSDL thật). Test chỉ dùng `DATABASE_URL_TEST`.
- **Chữ trên màn hình là tiếng Việt.** Thuật ngữ OBC giữ nguyên tiếng Nhật.

---

## Cấu trúc file

| File | Trách nhiệm | Task |
|---|---|---|
| `db/migrations/026_ngan_sach.sql` | Hai bảng `app`, một cột cờ, bốn view `mart`. Toàn bộ công thức. | 1 |
| `tests/test_ngan_sach_mart.py` | Canh bốn view: hai chiều thiếu của `FULL JOIN`, mã ngoài `dim_salesperson`, tỷ suất, khoá ngoại lịch. | 1 |
| `kome/ngan_sach.py` | Đọc bảng nhập, đọc số người gõ, ghi những ô đã đổi + nhật ký. Không biết HTTP. | 2 |
| `tests/test_ngan_sach.py` | Canh `kome/ngan_sach.py`. | 2 |
| `kome/web/templates/ngan_sach.html` | Bảng 5 × 12 ô nhập. | 3 |
| `kome/web/templates/cam_ngan_sach.html` | Trang 403 cho người không có cờ. | 3 |
| `kome/web/app.py` | Route `GET`/`POST /ngan-sach`; cờ mới vào cổng middleware và vào `_ve`. | 3 |
| `kome/web/nguoi_dung.py` | Cột cờ mới trong `NguoiDung` và trong `tao`/`dat_quyen`. | 3 |
| `kome/web/templates/_nav.html` | Mục "Ngân sách", bọc cờ. | 3 |
| `tests/test_ngan_sach_web.py` | Canh cổng quyền và màn nhập. | 3 |
| `kome/bao_cao.py` | `tien_do_ngan_sach()` + `ve_luy_ke()`. | 4 |
| `kome/web/templates/bao_cao.html` | Bốn khối ngân sách. | 4 |
| `tests/test_ngan_sach_bao_cao.py` | Canh bốn khối. | 4 |
| `scripts/tao_nguoi_dung.py` | Cấp/thu cờ mới, hiện trong bảng liệt kê. | 5 |
| `CLAUDE.md`, `docs/runbook.md` | Bất biến mới, cạm bẫy, cách cấp quyền. | 5 |

---

## Task 1: Migration 026 — hai bảng, một cờ, bốn view

**Files:**
- Create: `db/migrations/026_ngan_sach.sql`
- Create: `tests/test_ngan_sach_mart.py`
- Modify: `tests/conftest.py` (thêm `core.dim_date` đã có; **không đổi gì** — đọc để hiểu fixture)

**Interfaces:**
- Consumes: `core.dim_salesperson` (019), `core.dim_date` (004 + 012), `app.nguoi_dung` (019), `mart.dong_ban` (014), `mart.moc_thoi_gian` (015).
- Produces: bảng `app.ngan_sach(salesperson_code, thang, muc_tieu, sua_luc, sua_boi)`; bảng `app.ngan_sach_nhat_ky(id, salesperson_code, thang, muc_tieu_cu, muc_tieu_moi, sua_boi, sua_luc)`; cột `app.nguoi_dung.duoc_sua_ngan_sach boolean NOT NULL DEFAULT false`; view `mart.ngay_kinh_doanh(thang, ngay_kd, ngay_kd_da_qua)`; view `mart.ngan_sach_thang(thang, company_fy, salesperson_code, muc_tieu)`; view `mart.ban_theo_nhan_vien_thang(thang, company_fy, salesperson_code, doanh_thu_thuan, lai_gop, ty_suat, so_khach, so_phieu)`; view `mart.tien_do_ngan_sach(thang, company_fy, salesperson_code, muc_tieu, thuc_te, ngay_kd, ngay_kd_da_qua, muc_tieu_den_hom_nay, tien_do)`.

- [ ] **Step 1: Viết test trước — bốn view chưa tồn tại nên test phải đỏ**

Tạo `tests/test_ngan_sach_mart.py`:

```python
"""Đợt 5a Task 1 — bốn view của schema `mart` cho ngân sách.

Mỗi test ở đây canh một cách hiểu SAI mà nếu lọt thì trang vẫn vẽ ra bình
thường, chỉ là thiếu dòng hoặc nói sai số. Đó là loại lỗi tệ nhất: không ai
thấy nó, và người ta ra quyết định dựa trên nó.
"""
from datetime import date

import pandas as pd
import pytest


def _ban(conn, batch, ngay: date, sale: str, amount=110_000, tax=10_000,
         gp=30_000, khach="000000009292"):
    """Một dòng bán thật qua loader, không SQL tay."""
    from kome.loaders import sales
    b = batch(abs(hash((ngay, sale, amount, khach))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{sale}", "line_seq": 1, "sales_date": ngay,
        "customer_code": khach, "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": amount, "tax_amount": tax, "cost": amount - tax - gp,
        "gross_profit": gp, "paid_amount": 0, "salesperson_code": sale,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()
    return b


def _chi_tieu(conn, sale: str, thang: date, muc_tieu: int):
    conn.execute(
        "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
        "VALUES (%s, %s, %s)", (sale, thang, muc_tieu))
    conn.commit()


def test_nguoi_co_chi_tieu_ma_KHONG_ban_duoc_dong_nao_van_co_dong(conn, batch):
    """[CRITICAL] Nối `ban_theo LEFT JOIN ngan_sach` làm người có chỉ tiêu mà
    doanh thu 0 biến mất — đúng người cần nhìn nhất thì không có dòng nào, và
    trang vẫn vẽ ra bình thường."""
    _ban(conn, batch, date(2026, 5, 11), "0104")
    _chi_tieu(conn, "0105", date(2026, 5, 1), 9_000_000)
    r = conn.execute(
        "SELECT muc_tieu, thuc_te FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0105'").fetchone()
    assert r is not None, "người có chỉ tiêu mà 0 doanh thu phải VẪN có dòng"
    assert r[0] == 9_000_000 and r[1] == 0


def test_thang_co_doanh_thu_ma_QUEN_dat_chi_tieu_van_co_dong(conn, batch):
    """[CRITICAL] Nối chiều ngược lại làm doanh thu thật không xuất hiện ở đâu."""
    _ban(conn, batch, date(2026, 5, 11), "0104")
    r = conn.execute(
        "SELECT muc_tieu, thuc_te FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0104'").fetchone()
    assert r is not None, "tháng có doanh thu mà chưa đặt chỉ tiêu phải VẪN có dòng"
    assert r[0] is None and r[1] == 100_000


def test_ma_phu_trach_ngoai_dim_salesperson_van_hien_doanh_thu(conn, batch):
    """[CRITICAL] Đo thật 2026-09-22: dữ liệu bán có 6 mã phụ trách, còn
    core.dim_salesperson chỉ có 5 — mã `0000` có 1 khách và ¥28.981 kỳ 7. Mã
    đó không bao giờ đặt được chỉ tiêu (khoá ngoại chặn), nên phép nối nào
    xuất phát từ chỉ tiêu cũng làm số tiền đó bốc hơi."""
    _ban(conn, batch, date(2026, 5, 11), "0000", amount=33_000, tax=3_000, gp=9_000)
    r = conn.execute(
        "SELECT thuc_te FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0000'").fetchone()
    assert r is not None and r[0] == 30_000


def test_chi_tieu_bang_0_cho_tien_do_NULL_khong_lam_no_trang(conn, batch):
    """Chia cho 0 thì trang chết; in "∞" thì người đọc tưởng đã vượt mức."""
    _ban(conn, batch, date(2026, 5, 11), "0104")
    _chi_tieu(conn, "0104", date(2026, 5, 1), 0)
    r = conn.execute(
        "SELECT tien_do FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0104'").fetchone()
    assert r[0] is None


def test_moc_den_hom_nay_theo_ngay_lam_viec_da_qua(conn, batch):
    """Mốc = chỉ tiêu × (ngày làm việc đã qua / tổng ngày làm việc của tháng).
    hom_nay = ngày bán mới nhất trong kho, KHÔNG phải current_date."""
    _ban(conn, batch, date(2026, 5, 15), "0104")     # hom_nay = 2026-05-15
    _chi_tieu(conn, "0104", date(2026, 5, 1), 10_000_000)
    r = conn.execute(
        """SELECT ngay_kd, ngay_kd_da_qua, muc_tieu_den_hom_nay
           FROM mart.tien_do_ngan_sach
           WHERE thang = '2026-05' AND salesperson_code = '0104'""").fetchone()
    # 5/2026: 21 ngày trong tuần; tới hết 15/5 là 11 ngày trong tuần.
    assert (r[0], r[1]) == (21, 11)
    # `::bigint` của Postgres LÀM TRÒN (không cắt cụt), nên cho phép lệch 1 yên
    # thay vì khẳng định một trong hai cách quy tròn — con số này không dùng để
    # đối chiếu sổ sách, nó là vạch mốc trên một thanh tiến độ.
    assert r[2] == pytest.approx(10_000_000 * 11 / 21, abs=1)


def test_thang_da_qua_han_thi_moc_bang_dung_chi_tieu(conn, batch):
    """Tháng đã trôi qua hết so với hom_nay thì mốc phải là 100% chỉ tiêu,
    không phải một con số tròn tuỳ tiện."""
    _ban(conn, batch, date(2026, 7, 31), "0104")     # hom_nay = 2026-07-31
    _chi_tieu(conn, "0104", date(2026, 5, 1), 10_000_000)
    r = conn.execute(
        "SELECT muc_tieu_den_hom_nay FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0104'").fetchone()
    assert r[0] == 10_000_000


def test_ty_suat_theo_thang_la_TY_SO_CUA_CAC_TONG(conn, batch):
    """[IMPORTANT] Bất biến của dự án: tỷ suất ở BẤT KỲ view nào của `mart`
    luôn là sum(lãi gộp)/sum(doanh thu thuần), không bao giờ là trung bình
    của các tỷ số từng dòng. Một dòng doanh thu thuần vài yên (mẫu số nhỏ do
    赤伝) cho ra tỷ số hàng chục lần và kéo lệch cả bảng."""
    _ban(conn, batch, date(2026, 5, 11), "0104", amount=110_000, tax=10_000, gp=30_000)
    _ban(conn, batch, date(2026, 5, 12), "0104", amount=1_100, tax=100, gp=900,
         khach="000000009293")
    r = conn.execute(
        "SELECT ty_suat FROM mart.ban_theo_nhan_vien_thang "
        "WHERE thang = '2026-05' AND salesperson_code = '0104'").fetchone()
    assert abs(float(r[0]) - (30_900 / 101_000)) < 1e-9


def test_chi_tieu_ngoai_dai_lich_bi_CHAN_ngay_luc_ghi(conn):
    """core.dim_date phủ 2024-01-01 → 2035-12-31. Không có khoá ngoại thì một
    dòng chỉ tiêu ngoài dải đó biến mất khỏi mọi báo cáo mà không lỗi nào nổ —
    dữ liệu còn trong bảng, chỉ là không ai nhìn thấy nữa."""
    import psycopg
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
            "VALUES ('0104', DATE '2036-01-01', 1000)")
    conn.rollback()


def test_khong_ghi_duoc_thang_khong_phai_mung_1(conn):
    """Hai dòng "cùng tháng" khác ngày là hai chỉ tiêu cho một tháng."""
    import psycopg
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
            "VALUES ('0104', DATE '2026-05-15', 1000)")
    conn.rollback()


def test_co_moi_mac_dinh_FALSE(conn):
    """Quyền ghi phải được cấp TƯỜNG MINH, không phải thứ ai cũng có vì người
    tạo tài khoản quên đặt."""
    from kome.web import nguoi_dung as ND
    ND.tao(conn, "an", "mat-khau-cua-an-2026")
    conn.commit()
    r = conn.execute(
        "SELECT duoc_sua_ngan_sach FROM app.nguoi_dung WHERE ten_dang_nhap='an'"
    ).fetchone()
    assert r[0] is False
```

- [ ] **Step 2: Chạy test để thấy nó đỏ**

Chạy: `python -u -m pytest tests/test_ngan_sach_mart.py -v`
Mong đợi: FAIL — `psycopg.errors.UndefinedTable: relation "mart.tien_do_ngan_sach" does not exist`.

- [ ] **Step 3: Viết migration**

Tạo `db/migrations/026_ngan_sach.sql`:

```sql
-- 026: ngân sách — chỉ tiêu doanh thu theo nhân viên theo tháng.
--
-- LƯU Ý BẤT BIẾN: ALTER DEFAULT PRIVILEGES của 009/010 KHÔNG có mệnh đề
-- FOR ROLE, nên file này (như mọi migration) PHẢI chạy bằng vai trò
-- `postgres`. Chạy bằng vai trò khác thì hai bảng dưới đây âm thầm không
-- nhận quyền mặc định, và lỗi chỉ lộ ra bằng một `permission denied` nhiều
-- tháng sau, giữa lúc có người đang nhập chỉ tiêu.
--
-- OBC KHÔNG xuất ra chỉ tiêu. Đây là dữ liệu nhập tay, 5 người × 12 tháng.

-- ---------------------------------------------------------------------------
-- Chỉ tiêu
-- ---------------------------------------------------------------------------

CREATE TABLE app.ngan_sach (
    salesperson_code text NOT NULL REFERENCES core.dim_salesperson,
    -- `thang` là DATE mùng 1, không phải text 'YYYY-MM': CSDL tự chặn
    -- '2026-13' và '26-07', còn CHECK chặn nốt ngày khác mùng 1 — không tồn
    -- tại được hai dòng "cùng tháng" khác ngày.
    --
    -- Khoá ngoại tới core.dim_date (phủ 2024-01-01 → 2035-12-31) KHÔNG phải
    -- trang trí: mart.ngan_sach_thang nối sang dim_date để lấy company_fy,
    -- nên một dòng ngoài dải lịch sẽ biến mất khỏi MỌI báo cáo mà không lỗi
    -- nào nổ ra — dữ liệu còn trong bảng, chỉ là không ai nhìn thấy nữa.
    -- Có khoá ngoại thì nó là lỗi ghi ngay tại chỗ nhập, đọc ra được nguyên
    -- nhân ("không đặt được chỉ tiêu 2036"), khác hẳn "lưu xong mà báo cáo
    -- không thấy".
    thang            date NOT NULL REFERENCES core.dim_date (date_key)
                          CHECK (extract(day FROM thang) = 1),
    -- Tiền LUÔN là số nguyên yên (CLAUDE.md, bẫy số 2).
    muc_tieu         bigint NOT NULL CHECK (muc_tieu >= 0),
    sua_luc          timestamptz NOT NULL DEFAULT now(),
    -- NULL khi máy trong công ty để trống KOME_SESSION_SECRET — không có cổng
    -- đăng nhập thì không ai là ai. KHÔNG dùng ON DELETE CASCADE: xoá một tài
    -- khoản không được phép kéo theo chỉ tiêu của cả năm.
    sua_boi          bigint NULL REFERENCES app.nguoi_dung,
    PRIMARY KEY (salesperson_code, thang)
);

COMMENT ON TABLE app.ngan_sach IS
  'Chỉ tiêu doanh thu do chủ DN đặt. KHÔNG có dòng = chưa đặt; muc_tieu = 0 =
   đã đặt và đặt bằng không. Hai thứ khác nhau và màn hình phải hiện khác
   nhau — cùng nếp mart.san_pham_360.ton.';

-- Nhật ký sửa: CHỈ THÊM, không bao giờ UPDATE/DELETE.
-- KHÔNG có khoá ngoại tới app.ngan_sach, và đó là chủ ý: nhật ký phải sống
-- sót sau khi dòng chỉ tiêu bị xoá — chính lúc bị xoá mới là lúc cần biết ai
-- xoá.
CREATE TABLE app.ngan_sach_nhat_ky (
    id               bigserial PRIMARY KEY,
    salesperson_code text NOT NULL,
    thang            date NOT NULL,
    -- NULL ở cột cũ = đặt lần đầu. NULL ở cột mới = xoá chỉ tiêu.
    -- Cả hai cùng NULL không bao giờ được ghi.
    muc_tieu_cu      bigint NULL,
    muc_tieu_moi     bigint NULL,
    sua_boi          bigint NULL REFERENCES app.nguoi_dung,
    sua_luc          timestamptz NOT NULL DEFAULT now(),
    CHECK (muc_tieu_cu IS NOT NULL OR muc_tieu_moi IS NOT NULL)
);

-- Cổng vào màn Ngân sách: đặt và sửa chỉ tiêu của cả công ty.
-- Mặc định FALSE — quyền ghi phải được cấp TƯỜNG MINH, cùng nếp
-- duoc_vao_kho_du_lieu (019).
ALTER TABLE app.nguoi_dung
    ADD COLUMN duoc_sua_ngan_sach boolean NOT NULL DEFAULT false;

-- ---------------------------------------------------------------------------
-- Định nghĩa chỉ số
-- ---------------------------------------------------------------------------

-- Mẫu số của mọi phép "đến hôm nay".
--
-- HẠN CHẾ CÓ TÊN: core.dim_date KHÔNG có cột ngày lễ Nhật. is_weekend chỉ
-- loại thứ Bảy và Chủ nhật, nên tháng có Tuần lễ Vàng (5月) hay Obon (8月) bị
-- đếm thừa 2–4 ngày làm việc và vạch mốc khắt khe hơn thực tế ở đúng những
-- tháng đó. Ghi ra chứ KHÔNG bịa một định nghĩa thứ hai (ví dụ "ngày có phiếu
-- bán"): hai định nghĩa cùng tên là hai con số nói hai điều.
CREATE VIEW mart.ngay_kinh_doanh AS
SELECT to_char(d.date_key, 'YYYY-MM')                                 AS thang,
       count(*) FILTER (WHERE NOT d.is_weekend)                       AS ngay_kd,
       count(*) FILTER (WHERE NOT d.is_weekend AND d.date_key <= m.hom_nay)
                                                                      AS ngay_kd_da_qua
FROM core.dim_date d CROSS JOIN mart.moc_thoi_gian m
GROUP BY 1;

COMMENT ON VIEW mart.ngay_kinh_doanh IS
  'hom_nay = ngày bán mới nhất trong kho (mart.moc_thoi_gian), KHÔNG phải
   current_date. Kho rỗng thì hom_nay NULL và ngay_kd_da_qua = 0 — đúng, vì
   chưa có ngày nào có số liệu.';

-- Chỉ tiêu, đã đổi khoá sang chuỗi 'YYYY-MM'.
-- Đây là CHỖ DUY NHẤT đổi date -> 'YYYY-MM', và cũng là chỗ duy nhất tra
-- company_fy của tháng — lấy từ core.dim_date, KHÔNG tính tay (luật số 3 của
-- 014_mart_bao_cao.sql).
CREATE VIEW mart.ngan_sach_thang AS
SELECT to_char(n.thang, 'YYYY-MM') AS thang,
       d.company_fy,
       n.salesperson_code,
       n.muc_tieu
FROM app.ngan_sach n
JOIN core.dim_date d ON d.date_key = n.thang;

-- Thực tế theo người theo tháng. Cùng khuôn mart.ban_theo_nhan_vien (014),
-- chỉ đổi trục gộp từ kỳ sang tháng.
CREATE VIEW mart.ban_theo_nhan_vien_thang AS
SELECT thang,
       min(company_fy)      AS company_fy,
       salesperson_code,
       sum(doanh_thu_thuan) AS doanh_thu_thuan,
       sum(gross_profit)    AS lai_gop,
       -- Tỷ suất là TỶ SỐ CỦA CÁC TỔNG, không bao giờ là trung bình của các
       -- tỷ số từng dòng (bất biến đã ghi, migration 021).
       sum(gross_profit)::numeric / nullif(sum(doanh_thu_thuan), 0) AS ty_suat,
       count(DISTINCT customer_code) AS so_khach,
       count(DISTINCT slip_no)       AS so_phieu
FROM mart.dong_ban
GROUP BY thang, salesperson_code;

-- Nơi ở của công thức tiến độ.
--
-- FULL JOIN, KHÔNG LEFT JOIN theo chiều nào cả — đây là điểm dễ hỏng nhất:
--   - ngan_sach LEFT JOIN ban_theo: tháng có doanh thu mà QUÊN đặt chỉ tiêu
--     biến mất khỏi báo cáo, doanh thu thật không xuất hiện ở đâu.
--   - ban_theo LEFT JOIN ngan_sach: người CÓ chỉ tiêu mà bán 0 đồng biến mất
--     — đúng người cần nhìn nhất thì không có dòng nào.
-- Cả hai chiều đều mất dòng mà TRANG VẪN VẼ RA BÌNH THƯỜNG, không lỗi nào nổ
-- ra. Cùng lớp lỗi đã ghi cho /ban-do (dim_prefecture LEFT JOIN khach_theo_tinh).
--
-- ĐO THẬT 2026-09-22: chiều thứ nhất mất dòng NGAY HÔM NAY. Dữ liệu bán có 6
-- mã phụ trách (0000, 0002, 0004, 0102, 0104, 0105) còn core.dim_salesperson
-- chỉ có 5 — mã 0000 có 1 khách và ¥28.981 doanh thu kỳ 7, và không bao giờ
-- đặt được chỉ tiêu vì khoá ngoại chặn.
CREATE VIEW mart.tien_do_ngan_sach AS
SELECT coalesce(b.thang, n.thang)                        AS thang,
       coalesce(b.company_fy, n.company_fy)              AS company_fy,
       coalesce(b.salesperson_code, n.salesperson_code)  AS salesperson_code,
       n.muc_tieu,
       coalesce(b.doanh_thu_thuan, 0)::bigint            AS thuc_te,
       k.ngay_kd,
       k.ngay_kd_da_qua,
       (n.muc_tieu * k.ngay_kd_da_qua::numeric / nullif(k.ngay_kd, 0))::bigint
                                                         AS muc_tieu_den_hom_nay,
       -- nullif: chỉ tiêu 0 cho ra NULL và màn hình in "—". Chia cho 0 thì
       -- trang chết; in "∞" thì người đọc tưởng đã vượt mức.
       coalesce(b.doanh_thu_thuan, 0)::numeric / nullif(n.muc_tieu, 0) AS tien_do
FROM mart.ban_theo_nhan_vien_thang b
FULL JOIN mart.ngan_sach_thang     n ON n.thang = b.thang
                                    AND n.salesperson_code = b.salesperson_code
LEFT JOIN mart.ngay_kinh_doanh     k ON k.thang = coalesce(b.thang, n.thang);

COMMENT ON VIEW mart.tien_do_ngan_sach IS
  'FULL JOIN chỉ tiêu <-> thực tế. Đổi thành LEFT JOIN theo BẤT KỲ chiều nào
   cũng làm mất dòng mà trang vẫn vẽ bình thường. Có test canh cả hai chiều:
   tests/test_ngan_sach_mart.py.';

-- Quyền: 009/010 đã ALTER DEFAULT PRIVILEGES cho schema app (TABLES và
-- SEQUENCES) và cho mart, nên hai bảng và bốn view trên tự nhận quyền — với
-- điều kiện file này chạy bằng vai trò `postgres`.
--
-- kome_report tự nhận SELECT trên hai bảng mới. GIỮ NGUYÊN, không REVOKE như
-- đã làm với app.nguoi_dung: chỉ tiêu doanh thu là con số nghiệp vụ, không
-- phải hash mật khẩu.
--
-- LƯU Ý: mart.ngan_sach_thang đọc app.ngan_sach, mà kome_ingest KHÔNG có
-- USAGE trên schema app. View vẫn chạy được cho nó, vì Postgres kiểm quyền
-- trên bảng nền theo CHỦ SỞ HỮU VIEW (ở đây là postgres). Đúng và mong muốn —
-- nhưng nó có nghĩa: đặt gì vào một view của mart là công bố thứ đó cho MỌI
-- vai trò đọc mart. Không đưa cột nhạy cảm nào vào theo đường này.
```

- [ ] **Step 4: Chạy test để thấy nó xanh**

Chạy: `python -u -m pytest tests/test_ngan_sach_mart.py -v`
Mong đợi: PASS toàn bộ 10 test.

- [ ] **Step 5: Chạy bộ test migration và vai trò**

Chạy: `python -u -m pytest tests/test_migrate.py tests/test_roles.py -v`
Mong đợi: PASS. Hai file này dùng fixture `fresh_conn` (dựng schema sạch từ đầu) nên chúng chứng kiến chính việc migration 026 chạy.

- [ ] **Step 6: Commit**

```bash
git add db/migrations/026_ngan_sach.sql tests/test_ngan_sach_mart.py
git commit -F - <<'MSG'
feat: migration 026 - bang ngan sach va bon view mart (dot 5a, task 1)

FULL JOIN chu khong LEFT JOIN: ca hai chieu deu mat dong ma trang van ve
binh thuong. Do that - du lieu ban co 6 ma phu trach, dim_salesperson chi
co 5, nen ma 0000 (1 khach, 28.981 yen ky 7) se boc hoi neu noi tu chi tieu.

thang co khoa ngoai toi core.dim_date: khong co no thi mot dong chi tieu
ngoai dai lich bien mat khoi moi bao cao ma khong loi nao no ra.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

## Task 2: `kome/ngan_sach.py` — đọc bảng nhập, đọc số, ghi ô đã đổi

**Files:**
- Create: `kome/ngan_sach.py`
- Create: `tests/test_ngan_sach.py`

**Interfaces:**
- Consumes: bảng và view của Task 1; `core.dim_salesperson`; `core.dim_date`; `mart.moc_thoi_gian`.
- Produces:
  - `class LoiSo(ValueError)` — một ô không đọc được thành số.
  - `def doc_so(chuoi: str) -> int | None` — `None` khi ô trống; ném `LoiSo` khi rác.
  - `@dataclass(frozen=True) class Nguoi: ma: str; ten: str`
  - `@dataclass(frozen=True) class BangNhap: company_fy: int; moi_ky: list[int]; thang: list[str]; nguoi: list[Nguoi]; o: dict[tuple[str, str], int]`
  - `def bang_nhap(conn, company_fy: int | None = None) -> BangNhap`
  - `def luu(conn, gia_tri: dict[tuple[str, str], int | None], nguoi_id: int | None) -> int` — trả về số ô đã đổi.

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_ngan_sach.py`:

```python
"""Đợt 5a Task 2 — tầng Python của màn nhập ngân sách."""
from datetime import date

import pandas as pd
import pytest

from kome.ngan_sach import BangNhap, LoiSo, bang_nhap, doc_so, luu


def _ban(conn, batch, ngay: date, sale: str = "0104"):
    from kome.loaders import sales
    b = batch(abs(hash((ngay, sale))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{sale}", "line_seq": 1, "sales_date": ngay,
        "customer_code": "000000009292", "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": 110_000, "tax_amount": 10_000, "cost": 70_000,
        "gross_profit": 30_000, "paid_amount": 0, "salesperson_code": sale,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


# ---- đọc số ---------------------------------------------------------------

@pytest.mark.parametrize("chuoi,mong", [
    ("12000000", 12_000_000),
    ("12.000.000", 12_000_000),
    ("12,000,000", 12_000_000),
    (" 12 000 000 ", 12_000_000),
    ("0", 0),
])
def test_doc_so_chap_nhan_moi_kieu_dau_phan_cach(chuoi, mong):
    """Người gõ 60 ô sẽ gõ theo thói quen của họ, không theo thói quen của
    lập trình viên. Ba kiểu phân cách đều phải ra cùng một số."""
    assert doc_so(chuoi) == mong


@pytest.mark.parametrize("chuoi", ["", "   ", None])
def test_o_trong_tra_None_chu_khong_phai_0(chuoi):
    """[CRITICAL] "Chưa đặt" KHÁC "bằng không" — cùng nếp
    mart.san_pham_360.ton. Ô trống trả 0 là ghi vào CSDL một chỉ tiêu bằng 0
    cho người chưa được giao chỉ tiêu nào."""
    assert doc_so(chuoi) is None


@pytest.mark.parametrize("chuoi", ["abc", "12x", "-5", "1.5", "１２３"])
def test_chuoi_rac_nem_LoiSo(chuoi):
    """[CRITICAL] `1.5` nằm trong danh sách này có chủ ý. Dấu chấm là dấu phân
    cách hàng nghìn kiểu Việt, nên một phép "bỏ hết dấu phân cách rồi kiểm tra
    còn toàn chữ số không" biến `1.5` thành **15** — một con số người gõ không
    hề định nhập, ghi vào CSDL không lỗi nào, và chỉ lộ ra khi ai đó nhìn thấy
    chỉ tiêu tháng là ¥15. Vì vậy `doc_so` kiểm CẤU TRÚC NHÓM: mọi nhóm sau
    dấu phân cách phải đúng 3 chữ số."""
    with pytest.raises(LoiSo):
        doc_so(chuoi)


# ---- bảng nhập ------------------------------------------------------------

def test_bang_nhap_co_du_12_thang_dung_thu_tu_ky(conn, batch):
    """Kỳ công ty chạy 1/8 → 31/7, nên tháng đầu bảng là 8月 chứ không phải
    1月. Sắp theo thứ tự lịch dương là bảng nói sai về kỳ."""
    _ban(conn, batch, date(2026, 5, 11))
    b = bang_nhap(conn)
    assert b.company_fy == 2026
    assert b.thang[0] == "2025-08" and b.thang[-1] == "2026-07"
    assert len(b.thang) == 12


def test_ky_CHUA_CO_doanh_thu_nao_van_chon_duoc(conn, batch):
    """[IMPORTANT] Chỉ tiêu được đặt TRƯỚC khi bán. Lấy danh sách kỳ từ
    mart.tong_theo_ky (chỉ những kỳ ĐÃ có doanh thu) thì không ai đặt được
    chỉ tiêu cho năm sau, và lỗi chỉ lộ ra đúng lúc cần dùng."""
    _ban(conn, batch, date(2026, 5, 11))            # chỉ có kỳ 2026
    b = bang_nhap(conn)
    assert 2027 in b.moi_ky, "kỳ chưa có doanh thu vẫn phải chọn được"
    b27 = bang_nhap(conn, 2027)
    assert b27.thang[0] == "2026-08" and len(b27.thang) == 12


def test_bang_nhap_co_du_nguoi_phu_trach_ke_ca_nguoi_chua_dat_chi_tieu(conn, batch):
    _ban(conn, batch, date(2026, 5, 11))
    b = bang_nhap(conn)
    assert [n.ma for n in b.nguoi] == ["0002", "0004", "0102", "0104", "0105"]
    assert b.o == {}, "chưa đặt gì thì không ô nào có giá trị"


def test_o_chua_dat_KHONG_co_trong_dict(conn, batch):
    """[CRITICAL] `o` chỉ chứa ô ĐÃ đặt. Trả 0 cho ô chưa đặt thì màn hình in
    `0` vào chỗ đáng lẽ để trống, và người đọc hiểu thành "chỉ tiêu bằng 0"."""
    _ban(conn, batch, date(2026, 5, 11))
    luu(conn, {("0104", "2026-05"): 0}, None)
    conn.commit()
    b = bang_nhap(conn)
    assert b.o == {("0104", "2026-05"): 0}
    assert ("0105", "2026-05") not in b.o


# ---- ghi ------------------------------------------------------------------

def _nhat_ky(conn):
    return conn.execute(
        """SELECT salesperson_code, thang, muc_tieu_cu, muc_tieu_moi
           FROM app.ngan_sach_nhat_ky ORDER BY id""").fetchall()


def test_luu_ghi_nhat_ky_cho_lan_dat_dau_tien(conn, batch):
    _ban(conn, batch, date(2026, 5, 11))
    assert luu(conn, {("0104", "2026-05"): 9_000_000}, None) == 1
    conn.commit()
    assert _nhat_ky(conn) == [("0104", date(2026, 5, 1), None, 9_000_000)]


def test_luu_KHONG_ghi_gi_khi_khong_co_gi_doi(conn, batch):
    """[CRITICAL] sua_luc/sua_boi phải trả lời "ai đổi con số NÀY lần cuối",
    không phải "ai bấm Lưu lần cuối". Ghi đè cả 60 ô mỗi lần bấm Lưu là xoá
    sạch thông tin đó và làm nhật ký đầy dòng không có gì thay đổi."""
    _ban(conn, batch, date(2026, 5, 11))
    luu(conn, {("0104", "2026-05"): 9_000_000}, None)
    conn.commit()
    assert luu(conn, {("0104", "2026-05"): 9_000_000}, None) == 0
    conn.commit()
    assert len(_nhat_ky(conn)) == 1


def test_o_de_trong_thi_XOA_chi_tieu_va_ghi_nhat_ky(conn, batch):
    _ban(conn, batch, date(2026, 5, 11))
    luu(conn, {("0104", "2026-05"): 9_000_000}, None)
    conn.commit()
    assert luu(conn, {("0104", "2026-05"): None}, None) == 1
    conn.commit()
    assert bang_nhap(conn).o == {}
    assert _nhat_ky(conn)[-1] == ("0104", date(2026, 5, 1), 9_000_000, None)


def test_luu_giu_nguoi_sua(conn, batch):
    from kome.web import nguoi_dung as ND
    _ban(conn, batch, date(2026, 5, 11))
    uid = ND.tao(conn, "an", "mat-khau-cua-an-2026")
    conn.commit()
    luu(conn, {("0104", "2026-05"): 9_000_000}, uid)
    conn.commit()
    r = conn.execute("SELECT sua_boi FROM app.ngan_sach").fetchone()
    assert r[0] == uid
    r2 = conn.execute("SELECT sua_boi FROM app.ngan_sach_nhat_ky").fetchone()
    assert r2[0] == uid


def test_luu_khong_qua_4_truy_van(conn, batch, monkeypatch):
    """[IMPORTANT] Mỗi vòng hỏi qua pooler Tokyo mất ~47 ms chỉ riêng mạng.
    60 ô ghi thành 60 câu lệnh là gần ba giây chỉ để bấm một nút Lưu.

    BỐN là trần: đọc hiện trạng · ghi · xoá · nhật ký. Biểu mẫu dưới đây chỉ
    đặt thêm chỉ tiêu nên nó chạy ba — phép đo vẫn bắt được vòng lặp một câu
    lệnh mỗi ô, thứ mà ngân sách này tồn tại để cấm."""
    _ban(conn, batch, date(2026, 5, 11))
    gia_tri = {(ma, f"2026-{t:02d}") : 1_000_000
               for ma in ("0002", "0004", "0102", "0104", "0105")
               for t in range(1, 8)}
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    luu(conn, gia_tri, None)
    assert dem["n"] <= 4, f"luu() chạy {dem['n']} truy vấn cho 35 ô"


def test_bang_nhap_khong_qua_4_truy_van(conn, batch, monkeypatch):
    _ban(conn, batch, date(2026, 5, 11))
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    bang_nhap(conn)
    assert dem["n"] <= 4, f"bang_nhap() chạy {dem['n']} truy vấn"
```

- [ ] **Step 2: Chạy test để thấy nó đỏ**

Chạy: `python -u -m pytest tests/test_ngan_sach.py -v`
Mong đợi: FAIL — `ModuleNotFoundError: No module named 'kome.ngan_sach'`.

- [ ] **Step 3: Viết module**

Tạo `kome/ngan_sach.py`:

```python
"""Chỉ tiêu doanh thu theo nhân viên theo tháng — đọc bảng nhập và ghi nó.

Module này KHÔNG biết gì về HTTP: không FastAPI, không biểu mẫu, không cookie.
Nó chỉ nói chuyện với `app.ngan_sach` và `app.ngan_sach_nhat_ky` (migration
026). Ranh giới đó giống hệt `kome/web/nguoi_dung.py`: một chỗ giữ "con số
này là bao nhiêu", một chỗ giữ "ai được phép đổi nó".

Cũng KHÔNG mở kết nối và KHÔNG tự commit: hàm nhận sẵn `conn`, người gọi
quyết định ranh giới giao dịch. Gọi connect() không tham số ở đây sẽ âm thầm
ghi vào CSDL THẬT trong khi test tưởng mình đang dùng CSDL thử nghiệm.

Mọi công thức ("tiến độ", "mốc đến hôm nay") nằm trong view của `mart`, không
nằm ở đây — xem db/migrations/026_ngan_sach.sql.
"""
import re
from dataclasses import dataclass
from datetime import date

# Kỳ công ty chạy 1/8 → 31/7 (core.dim_date.company_fy = năm KẾT THÚC kỳ).
SO_THANG_MOT_KY = 12

# Dấu phân cách hàng nghìn mà người ta thật sự gõ: dấu chấm (kiểu Việt), dấu
# phẩy (kiểu Anh), dấu cách, và dấu cách không ngắt mà Excel hay dán ra.
_PHAN_CACH = str.maketrans({".": "", ",": "", " ": "", " ": "", "_": ""})
_NGUYEN = re.compile(r"^[0-9]+$")
# Kiểm CẤU TRÚC NHÓM, không chỉ "bỏ dấu ra rồi xem còn toàn chữ số không":
# phép kiểm lỏng đó biến `1.5` thành 15, một con số người gõ không hề định
# nhập, ghi vào CSDL không lỗi nào, và chỉ lộ ra khi ai đó nhìn thấy chỉ tiêu
# tháng là ¥15. Mọi nhóm sau dấu phân cách phải đúng 3 chữ số.
_NHOM = re.compile(r"^[0-9]{1,3}(?:[.,\s _][0-9]{3})*$")


class LoiSo(ValueError):
    """Một ô không đọc được thành số nguyên yên."""


def doc_so(chuoi: str | None) -> int | None:
    """Đọc một ô của biểu mẫu. None = ô TRỐNG = chưa đặt chỉ tiêu.

    "Chưa đặt" KHÁC "bằng không" (cùng nếp mart.san_pham_360.ton): trả 0 cho ô
    trống là ghi vào CSDL một chỉ tiêu bằng 0 cho người chưa được giao chỉ
    tiêu nào, và màn hình sau đó in `0` vào chỗ đáng lẽ để trống.

    Chỉ nhận chữ số ASCII: tiền là số nguyên yên nên không có phần thập phân,
    và số âm không phải chỉ tiêu. Chữ số toàn chiều rộng (１２３) bị từ chối
    thay vì âm thầm đổi — người gõ nhầm bảng mã cần biết ngay.
    """
    if chuoi is None:
        return None
    s = chuoi.strip()
    if not s:
        return None
    if _NGUYEN.match(s):
        return int(s)
    if _NHOM.match(s):
        return int(s.translate(_PHAN_CACH))
    raise LoiSo(chuoi)


@dataclass(frozen=True)
class Nguoi:
    ma: str
    ten: str


@dataclass(frozen=True)
class BangNhap:
    """Một kỳ của bảng nhập: 5 hàng người × 12 cột tháng.

    `o` CHỈ chứa những ô đã đặt chỉ tiêu. Ô vắng mặt = chưa đặt, và màn hình
    phải để trống chứ không in 0.
    """
    company_fy: int
    moi_ky: list[int]
    thang: list[str]           # 12 tháng 'YYYY-MM' theo THỨ TỰ KỲ (8月 trước)
    nguoi: list[Nguoi]
    o: dict[tuple[str, str], int]   # (salesperson_code, 'YYYY-MM') -> muc_tieu


def thang_cua_ky(company_fy: int) -> list[str]:
    """12 tháng của kỳ, 8月 của năm trước tới 7月 của năm company_fy.

    CÔNG KHAI vì `kome/bao_cao.py` nhập nó. "12 tháng của một kỳ, 8月 trước"
    là MỘT định nghĩa; hai bản chép của nó là hai thứ sẽ trôi khỏi nhau đúng
    lúc ai đó đổi năm tài chính của công ty.
    """
    return ([f"{company_fy - 1}-{t:02d}" for t in range(8, 13)]
            + [f"{company_fy}-{t:02d}" for t in range(1, 8)])


def _mung_1(thang: str) -> date:
    nam, t = thang.split("-")
    return date(int(nam), int(t), 1)


def bang_nhap(conn, company_fy: int | None = None) -> BangNhap:
    """Bảng nhập của một kỳ. company_fy=None => kỳ của `hom_nay`.

    Danh sách kỳ lấy từ `core.dim_date`, KHÔNG từ `mart.tong_theo_ky`: chỉ
    tiêu được đặt TRƯỚC khi bán, nên một danh sách chỉ gồm những kỳ đã có
    doanh thu là một danh sách không bao giờ cho đặt chỉ tiêu cho năm sau.
    """
    moi_ky = [r[0] for r in conn.execute(
        "SELECT DISTINCT company_fy FROM core.dim_date ORDER BY 1").fetchall()]

    # hom_nay có thể NULL (kho chưa có dòng bán nào) — khi đó rơi về kỳ giữa
    # dải lịch thay vì nổ, để màn nhập vẫn dùng được trước khi nạp dữ liệu.
    r = conn.execute(
        """SELECT d.company_fy FROM mart.moc_thoi_gian m
           JOIN core.dim_date d ON d.date_key = m.hom_nay""").fetchone()
    mac_dinh = r[0] if r else moi_ky[len(moi_ky) // 2]
    ky = company_fy if company_fy in moi_ky else mac_dinh

    nguoi = [Nguoi(ma=r[0], ten=r[1]) for r in conn.execute(
        "SELECT salesperson_code, ten FROM core.dim_salesperson "
        "ORDER BY salesperson_code").fetchall()]

    thang = thang_cua_ky(ky)
    o = {(r[0], r[1]): int(r[2]) for r in conn.execute(
        """SELECT salesperson_code, to_char(thang, 'YYYY-MM'), muc_tieu
           FROM app.ngan_sach WHERE thang >= %s AND thang <= %s""",
        (_mung_1(thang[0]), _mung_1(thang[-1]))).fetchall()}

    return BangNhap(company_fy=ky, moi_ky=moi_ky, thang=thang, nguoi=nguoi, o=o)


def luu(conn, gia_tri: dict[tuple[str, str], int | None],
        nguoi_id: int | None) -> int:
    """Ghi những ô ĐÃ ĐỔI, trả về số ô đã đổi. Không tự commit.

    Chỉ đụng ô đã đổi, vì `sua_luc`/`sua_boi` phải trả lời "ai đổi con số NÀY
    lần cuối", không phải "ai bấm Lưu lần cuối". Ghi đè cả 60 ô mỗi lần bấm
    Lưu là xoá sạch thông tin đó và làm nhật ký đầy dòng không có gì thay đổi.

    BỐN câu lệnh là trần, không phải bốn chục: đọc hiện trạng · ghi những ô
    có giá trị mới · xoá những ô vừa bị để trống · ghi nhật ký. Một biểu mẫu
    chỉ đặt thêm chỉ tiêu (không xoá ô nào) chạy ba câu. Mỗi vòng hỏi qua
    pooler Tokyo mất ~47 ms chỉ riêng mạng, nên 60 ô ghi thành 60 câu lệnh là
    gần ba giây chỉ để bấm một nút Lưu.
    """
    if not gia_tri:
        return 0

    khoa = [(ma, _mung_1(th)) for ma, th in gia_tri]
    hien = {(r[0], to_thang(r[1])): int(r[2]) for r in conn.execute(
        """SELECT salesperson_code, thang, muc_tieu FROM app.ngan_sach
           WHERE (salesperson_code, thang) = ANY(%s)""", (khoa,)).fetchall()}

    dat, xoa, nhat_ky = [], [], []
    for (ma, th), moi in gia_tri.items():
        cu = hien.get((ma, th))
        if cu == moi:
            continue
        nhat_ky.append((ma, _mung_1(th), cu, moi, nguoi_id))
        if moi is None:
            xoa.append((ma, _mung_1(th)))
        else:
            dat.append((ma, _mung_1(th), moi, nguoi_id))

    if not nhat_ky:
        return 0

    if dat:
        conn.execute(
            """INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu, sua_boi)
               SELECT x.ma, x.thang, x.muc_tieu, x.sua_boi
               FROM unnest(%s::text[], %s::date[], %s::bigint[], %s::bigint[])
                    AS x(ma, thang, muc_tieu, sua_boi)
               ON CONFLICT (salesperson_code, thang) DO UPDATE
                 SET muc_tieu = EXCLUDED.muc_tieu,
                     sua_boi  = EXCLUDED.sua_boi,
                     sua_luc  = now()""",
            ([d[0] for d in dat], [d[1] for d in dat],
             [d[2] for d in dat], [d[3] for d in dat]))
    if xoa:
        conn.execute(
            """DELETE FROM app.ngan_sach
               WHERE (salesperson_code, thang) = ANY(%s)""", (xoa,))

    conn.execute(
        """INSERT INTO app.ngan_sach_nhat_ky
             (salesperson_code, thang, muc_tieu_cu, muc_tieu_moi, sua_boi)
           SELECT * FROM unnest(%s::text[], %s::date[], %s::bigint[],
                                %s::bigint[], %s::bigint[])""",
        ([n[0] for n in nhat_ky], [n[1] for n in nhat_ky],
         [n[2] for n in nhat_ky], [n[3] for n in nhat_ky],
         [n[4] for n in nhat_ky]))
    return len(nhat_ky)


def to_thang(d: date) -> str:
    """`date` mùng 1 -> 'YYYY-MM'. Dùng để so khớp với khoá của `gia_tri`."""
    return f"{d.year}-{d.month:02d}"
```

- [ ] **Step 4: Chạy test để thấy nó xanh**

Chạy: `python -u -m pytest tests/test_ngan_sach.py -v`
Mong đợi: PASS.

Nếu `= ANY(%s)` với danh sách bộ đôi không chạy trên psycopg 3, đổi câu đọc hiện trạng và câu xoá sang dạng `unnest` như hai câu còn lại — **không** đổi sang vòng lặp một câu lệnh mỗi ô, vì đó chính là thứ `test_luu_khong_qua_3_truy_van` cấm.

- [ ] **Step 5: Commit**

```bash
git add kome/ngan_sach.py tests/test_ngan_sach.py
git commit -F - <<'MSG'
feat: kome/ngan_sach.py - doc bang nhap, doc so, ghi o da doi (dot 5a, task 2)

O trong tra None chu khong phai 0: "chua dat" khac "bang khong", cung nep
mart.san_pham_360.ton. Tra 0 cho o trong la ghi vao CSDL mot chi tieu bang 0
cho nguoi chua duoc giao chi tieu nao.

luu() chi dung o DA DOI: sua_luc/sua_boi phai tra loi "ai doi con so NAY lan
cuoi", khong phai "ai bam Luu lan cuoi".

Danh sach ky lay tu core.dim_date chu khong tu mart.tong_theo_ky - chi tieu
duoc dat TRUOC khi ban, nen mot danh sach chi gom ky da co doanh thu la mot
danh sach khong bao gio cho dat chi tieu cho nam sau.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

## Task 3: Cờ quyền và màn `/ngan-sach`

**Files:**
- Modify: `kome/web/nguoi_dung.py` (dataclass `NguoiDung`, `_CHON`, `tao`, `dat_quyen`)
- Modify: `kome/web/app.py` (hằng đường dẫn, middleware, `_ve`, hai route mới)
- Create: `kome/web/templates/ngan_sach.html`
- Create: `kome/web/templates/cam_ngan_sach.html`
- Modify: `kome/web/templates/_nav.html`
- Create: `tests/test_ngan_sach_web.py`

**Interfaces:**
- Consumes: `kome.ngan_sach.bang_nhap`, `luu`, `doc_so`, `LoiSo`, `BangNhap`, `Nguoi` (Task 2); cột `app.nguoi_dung.duoc_sua_ngan_sach` (Task 1).
- Produces:
  - `NguoiDung.duoc_sua_ngan_sach: bool` (trường thứ sáu của dataclass, **sau** `duoc_vao_kho_du_lieu`, **trước** `ten_sale`).
  - `nguoi_dung.tao(conn, ten, mat_khau, salesperson_code=None, kho_du_lieu=False, ngan_sach=False) -> int`
  - `nguoi_dung.dat_quyen(conn, ten, kho_du_lieu=None, ngan_sach=None) -> bool` — `None` = không đổi cờ đó.
  - Route `GET /ngan-sach?ky=<company_fy>` và `POST /ngan-sach`.
  - Biến template `hien_ngan_sach` do `_ve` tính (song song với `hien_kho`).

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_ngan_sach_web.py`:

```python
"""Đợt 5a Task 3 — cổng quyền và màn nhập /ngan-sach.

Đây là đường GHI đầu tiên của app ngoài luồng nạp OBC, nên phần lớn test ở
đây canh cái CỬA chứ không canh con số.
"""
import re
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kome.web.app import create_app

MK = "mat-khau-cua-an-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"


@pytest.fixture
def khach(monkeypatch, test_db_url, conn):
    """Dựng app CÓ cổng đăng nhập và một tài khoản. `ngan_sach` là cờ mới."""
    from kome.web import nguoi_dung as ND

    def _tao(ngan_sach: bool = True):
        monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT)
        monkeypatch.delenv("VERCEL", raising=False)
        ND.tao(conn, "an", MK, kho_du_lieu=False, ngan_sach=ngan_sach)
        conn.commit()
        c = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
        c.post("/dang-nhap", data={"ten": "an", "mat_khau": MK})
        return c
    return _tao


def _ban(conn, batch, ngay: date = date(2026, 5, 11), sale: str = "0104"):
    from kome.loaders import sales
    b = batch(abs(hash((ngay, sale))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{sale}", "line_seq": 1, "sales_date": ngay,
        "customer_code": "000000009292", "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": 110_000, "tax_amount": 10_000, "cost": 70_000,
        "gross_profit": 30_000, "paid_amount": 0, "salesperson_code": sale,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


# ---- cổng quyền -----------------------------------------------------------

def test_khong_co_co_thi_403_o_CA_GET_lan_POST(khach, conn, batch):
    """[CRITICAL] Gác mỗi GET là để nguyên cửa ghi mở toang cho ai biết gõ
    `curl`. Cửa ghi phải bị chặn, và phải chặn TRƯỚC khi ghi được dòng nào."""
    _ban(conn, batch)
    c = khach(ngan_sach=False)
    assert c.get("/ngan-sach").status_code == 403
    r = c.post("/ngan-sach", data={"ky": "2026", "o-0104-2026-05": "9000000"})
    assert r.status_code == 403
    assert conn.execute("SELECT count(*) FROM app.ngan_sach").fetchone()[0] == 0


def test_403_giai_thich_chu_khong_chuyen_huong_im_lang(khach, conn, batch):
    """Người gõ thẳng địa chỉ cần biết vì sao mình không vào được, không phải
    tự hỏi trang có hỏng không."""
    _ban(conn, batch)
    r = khach(ngan_sach=False).get("/ngan-sach")
    assert r.status_code == 403
    assert "quyền" in r.text and "Ngân sách" in r.text


def test_thu_hoi_co_AN_NGAY_khong_doi_het_ve(khach, conn, batch):
    """[CRITICAL] Vé sống 12 giờ. Cờ nằm trong vé thì thu hồi quyền trên màn
    có nút ghi phải đợi tới ngày mai. Cùng bất biến đã ghi cho
    duoc_vao_kho_du_lieu: TRA app.nguoi_dung MỖI LƯỢT GỌI."""
    _ban(conn, batch)
    c = khach(ngan_sach=True)
    assert c.get("/ngan-sach").status_code == 200
    conn.execute("UPDATE app.nguoi_dung SET duoc_sua_ngan_sach = false")
    conn.commit()
    assert c.get("/ngan-sach").status_code == 403


def test_muc_ngan_sach_an_khoi_thanh_dieu_huong_khi_khong_co_co(khach, conn, batch):
    """Mời người ta bấm vào một thứ sẽ từ chối họ thì tệ hơn là không hiện."""
    _ban(conn, batch)
    assert 'href="/ngan-sach"' not in khach(ngan_sach=False).get("/bao-cao").text
    assert 'href="/ngan-sach"' in khach(ngan_sach=True).get("/bao-cao").text


def test_khong_co_cong_dang_nhap_thi_vao_duoc(conn, batch, test_db_url):
    """Máy trong công ty để trống KOME_SESSION_SECRET => không có cổng và
    không có phân quyền. Đây là CẠM BẪY đã ghi trong CLAUDE.md, không phải lỗ
    mới — nhưng test phải khẳng định đúng hành vi đó, vì nếu trang bỗng trả
    403 khi không có cổng thì máy trong công ty mất hẳn màn nhập."""
    _ban(conn, batch)
    c = TestClient(create_app(db_url=test_db_url))
    assert c.get("/ngan-sach").status_code == 200


# ---- màn nhập -------------------------------------------------------------

def test_luu_roi_tai_lai_thi_thay_dung_so_vua_nhap(khach, conn, batch):
    _ban(conn, batch)
    c = khach()
    r = c.post("/ngan-sach", data={"ky": "2026", "o-0104-2026-05": "9.000.000"})
    assert r.status_code == 303
    assert conn.execute(
        "SELECT muc_tieu FROM app.ngan_sach").fetchone()[0] == 9_000_000
    assert 'value="9.000.000"' in c.get("/ngan-sach?ky=2026").text


def test_mot_o_sai_thi_KHONG_ghi_o_nao(khach, conn, batch):
    """[CRITICAL] Ghi một nửa rồi báo lỗi là để người ta không biết nửa nào đã
    vào. Và biểu mẫu phải hiện lại ĐÚNG những gì họ vừa gõ — bắt gõ lại 60 ô
    vì một ô sai là cách chắc chắn để không ai dùng màn này lần thứ hai."""
    _ban(conn, batch)
    c = khach()
    r = c.post("/ngan-sach", data={"ky": "2026",
                                   "o-0104-2026-05": "9000000",
                                   "o-0105-2026-05": "chin trieu"})
    assert r.status_code == 400
    assert conn.execute("SELECT count(*) FROM app.ngan_sach").fetchone()[0] == 0
    assert "chin trieu" in r.text, "phải hiện lại đúng chữ người ta vừa gõ"
    assert 'value="9000000"' in r.text


def test_o_chua_dat_hien_TRONG_khong_hien_0(khach, conn, batch):
    """[CRITICAL] Hiện 0 cho thứ chưa biết là nói một điều sai bằng con số."""
    _ban(conn, batch)
    html = khach().get("/ngan-sach?ky=2026").text
    o = re.findall(r'name="o-0104-2026-05"[^>]*value="([^"]*)"', html)
    assert o == [""], f"ô chưa đặt phải trống, thấy {o}"


def test_ky_chua_co_doanh_thu_van_co_trong_dai_chip(khach, conn, batch):
    _ban(conn, batch)
    assert "ky=2027" in khach().get("/ngan-sach").text


def test_trang_ngan_sach_khong_qua_5_truy_van(khach, conn, batch, monkeypatch):
    """[IMPORTANT] Trang chậm dần từng đợt là cách nó chết mà không ai thấy
    ngày nào nó chết.

    NĂM chứ không phải bốn: `bang_nhap()` được cấp ngân sách 4 lượt hỏi, cộng
    một lượt của middleware tra người đăng nhập (`nguoi_dung.theo_id`) — lượt
    đó là giá của cổng quyền, có ở MỌI trang, và nó phải tra CSDL mỗi lượt
    gọi chứ không đọc từ vé (bất biến của đợt 3).

    Đo tại tầng psycopg chứ không bọc `conn` của fixture: route mở kết nối
    riêng của chính nó qua open_app_conn(), nên `conn` của fixture không hề
    được route dùng tới."""
    _ban(conn, batch)
    c = khach()
    import psycopg
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)

    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    c.get("/ngan-sach?ky=2026")
    monkeypatch.undo()
    # Trừ lượt tra người đăng nhập của middleware (1 câu, theo_id).
    assert dem["n"] <= 5, f"/ngan-sach chạy {dem['n']} truy vấn"
```

- [ ] **Step 2: Chạy test để thấy nó đỏ**

Chạy: `python -u -m pytest tests/test_ngan_sach_web.py -v`
Mong đợi: FAIL — `TypeError: tao() got an unexpected keyword argument 'ngan_sach'`.

- [ ] **Step 3: Thêm cờ vào `kome/web/nguoi_dung.py`**

Sửa bốn chỗ trong `kome/web/nguoi_dung.py`:

```python
_CHON = f"""SELECT n.id, n.ten_dang_nhap, n.salesperson_code,
                   n.duoc_vao_kho_du_lieu, n.duoc_sua_ngan_sach, s.ten
            FROM app.nguoi_dung n
            LEFT JOIN core.dim_salesperson s
                   ON s.salesperson_code = n.salesperson_code"""


@dataclass(frozen=True)
class NguoiDung:
    """Người đang đăng nhập. CỐ Ý không mang hash/salt: cái gì không có trong
    đối tượng thì không có đường nào lọt lên trang hay vào nhật ký."""
    id: int
    ten_dang_nhap: str
    salesperson_code: str | None
    duoc_vao_kho_du_lieu: bool
    duoc_sua_ngan_sach: bool
    ten_sale: str | None


def _nguoi(r) -> NguoiDung:
    return NguoiDung(id=r[0], ten_dang_nhap=r[1], salesperson_code=r[2],
                     duoc_vao_kho_du_lieu=r[3], duoc_sua_ngan_sach=r[4],
                     ten_sale=r[5])


def tao(conn, ten: str, mat_khau: str, salesperson_code: str | None = None,
        kho_du_lieu: bool = False, ngan_sach: bool = False) -> int:
    """Tạo tài khoản, trả về id. Ném UniqueViolation nếu tên đã có,
    ForeignKeyViolation nếu mã sale không có trong core.dim_salesperson.

    Hai cờ quyền mặc định FALSE: quyền ghi phải được cấp TƯỜNG MINH, không
    phải thứ ai cũng có vì người tạo tài khoản quên đặt.
    """
    salt = os.urandom(DAI_SALT)
    return conn.execute(
        """INSERT INTO app.nguoi_dung
             (ten_dang_nhap, mat_khau_hash, mat_khau_salt, salesperson_code,
              duoc_vao_kho_du_lieu, duoc_sua_ngan_sach)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (ten, bam(mat_khau, salt), salt, salesperson_code or None,
         kho_du_lieu, ngan_sach),
    ).fetchone()[0]


def dat_quyen(conn, ten: str, kho_du_lieu: bool | None = None,
              ngan_sach: bool | None = None) -> bool:
    """False nếu không có tài khoản tên đó.

    `None` = KHÔNG đổi cờ đó. Đặt mặc định False thay vì None sẽ làm lệnh
    "cấp quyền ngân sách" âm thầm thu hồi quyền Kho dữ liệu của cùng người —
    hai cờ độc lập, mỗi lệnh chỉ đụng cờ mà nó nói tới.
    """
    return conn.execute(
        """UPDATE app.nguoi_dung
           SET duoc_vao_kho_du_lieu = coalesce(%s, duoc_vao_kho_du_lieu),
               duoc_sua_ngan_sach   = coalesce(%s, duoc_sua_ngan_sach)
           WHERE ten_dang_nhap = %s""",
        (kho_du_lieu, ngan_sach, ten)).rowcount == 1
```

- [ ] **Step 4: Sửa `kome/web/app.py`**

Ba thay đổi, theo đúng nếp `duoc_vao_kho_du_lieu` đang có.

(a) Cạnh `DUONG_KHO_DU_LIEU` (dòng ~88) thêm:

```python
# Màn Ngân sách: đặt và sửa chỉ tiêu doanh thu của cả công ty. Cùng nếp
# DUONG_KHO_DU_LIEU — gác cả cửa đọc lẫn cửa ghi. Gác mỗi GET là để nguyên
# cửa ghi mở toang cho ai biết gõ `curl`.
DUONG_NGAN_SACH = ("/ngan-sach",)


def _thuoc_ngan_sach(duong: str) -> bool:
    return any(duong == d or duong.startswith(d + "/") for d in DUONG_NGAN_SACH)
```

(b) Trong `_ve` (dòng ~200), ngay sau `hien_kho`:

```python
        hien_kho = nguoi is None or nguoi.duoc_vao_kho_du_lieu
        # Cùng lý lẽ với hien_kho: mời người ta bấm vào một thứ sẽ từ chối họ
        # thì tệ hơn là không hiện. `nguoi is None` = không có cổng đăng nhập
        # (máy trong công ty) -> mọi thứ mở, y như trước đợt 3.
        hien_ngan_sach = nguoi is None or nguoi.duoc_sua_ngan_sach
```

và thêm `"hien_ngan_sach": hien_ngan_sach` vào dict truyền cho template.

(c) Trong middleware (dòng ~347), ngay sau khối `_thuoc_kho_du_lieu`:

```python
            if not nguoi.duoc_sua_ngan_sach and _thuoc_ngan_sach(request.url.path):
                # Chặn ở middleware nên nó chặn CẢ GET LẪN POST bằng một chỗ
                # duy nhất — không có đường nào cho một route mới quên gác.
                return _ve(request, "cam_ngan_sach.html",
                           {"trang": None}, status_code=403)
```

- [ ] **Step 5: Thêm hai route**

Trong `kome/web/app.py`, ngay sau route `/bao-cao`:

```python
    def _ngu_canh_ngan_sach(b) -> dict:
        """Đổi khoá bộ đôi sang khoá chuỗi cho Jinja, và cộng sẵn hai chiều
        tổng.

        `BangNhap.o` dùng khoá `(mã, tháng)` vì đó là khoá đúng ở tầng Python.
        Template thì tra bằng chính tên ô của biểu mẫu (`o-0104-2026-05`), nên
        đổi một lần ở đây thay vì để Jinja dựng lại bộ đôi ở mỗi trong 60 ô.

        Hai bảng tổng cộng từ `b.o` đã nằm sẵn trong bộ nhớ — KHÔNG thêm truy
        vấn nào. Ô chưa đặt không có mặt trong `b.o` nên nó không cộng vào
        tổng, đúng như phải thế: "chưa đặt" không phải "bằng không".
        """
        return {
            "b": b,
            "o_txt": {f"{ma}-{th}": v for (ma, th), v in b.o.items()},
            "tong_nguoi": {n.ma: sum(v for (m, _), v in b.o.items() if m == n.ma)
                           for n in b.nguoi},
            "tong_thang": {th: sum(v for (_, t), v in b.o.items() if t == th)
                           for th in b.thang},
        }

    @app.get("/ngan-sach", response_class=HTMLResponse)
    def ngan_sach(request: Request, ky: int | None = None):
        """Bảng nhập chỉ tiêu: 5 người phụ trách × 12 tháng của một kỳ.

        Cổng quyền nằm ở middleware (`_thuoc_ngan_sach`), không ở đây — một
        chỗ gác cho cả GET lẫn POST.
        """
        from kome.ngan_sach import bang_nhap
        try:
            with open_app_conn() as conn:
                b = bang_nhap(conn, ky)
            return _ve(request, "ngan_sach.html",
                       {**_ngu_canh_ngan_sach(b), "da_go": {}, "loi": [],
                        "trang": "ngan-sach"})
        except Exception as e:
            return _loi(request, "mở trang ngân sách", e)

    @app.post("/ngan-sach")
    async def luu_ngan_sach(request: Request):
        """Ghi cả biểu mẫu trong MỘT giao dịch.

        Một ô rác => KHÔNG ghi ô nào và hiện lại đúng những gì người ta vừa
        gõ. Ghi một nửa rồi báo lỗi là để người ta không biết nửa nào đã vào,
        và bắt gõ lại 60 ô vì một ô sai là cách chắc chắn để không ai dùng màn
        này lần thứ hai.
        """
        from kome.ngan_sach import LoiSo, bang_nhap, doc_so, luu
        form = await request.form()
        ky = int(form.get("ky") or 0) or None
        da_go = {k[2:]: str(v) for k, v in form.items() if k.startswith("o-")}

        gia_tri, loi = {}, []
        for khoa, chuoi in da_go.items():
            ma, thang = khoa.split("-", 1)
            try:
                gia_tri[(ma, thang)] = doc_so(chuoi)
            except LoiSo:
                loi.append(khoa)

        nguoi = getattr(request.state, "nguoi", None)
        try:
            with open_app_conn() as conn:
                if loi:
                    b = bang_nhap(conn, ky)
                    return _ve(request, "ngan_sach.html",
                               {**_ngu_canh_ngan_sach(b), "da_go": da_go,
                                "loi": loi, "trang": "ngan-sach"},
                               status_code=400)
                luu(conn, gia_tri, nguoi.id if nguoi else None)
                conn.commit()
            # `?ky=` (chuỗi rỗng) KHÔNG phải `None` với FastAPI — nó là một
            # chuỗi không ép được sang `int`, tức 422 chứ không phải "bỏ
            # trống". Một trang lỗi khó hiểu ngay sau khi vừa lưu THÀNH CÔNG
            # làm người dùng tưởng mất dữ liệu.
            return RedirectResponse(
                f"/ngan-sach?ky={ky}" if ky else "/ngan-sach", status_code=303)
        except Exception as e:
            return _loi(request, "lưu ngân sách", e)
```

- [ ] **Step 6: Viết hai template**

Tạo `kome/web/templates/cam_ngan_sach.html`:

```html
<!-- kome/web/templates/cam_ngan_sach.html
     403 cho người không có cờ duoc_sua_ngan_sach. Cùng khuôn
     cam_kho_du_lieu.html, chữ khác: hai màn bị từ chối vì hai lý do khác
     nhau, và một trang chung sẽ nói sai một trong hai. -->
<!doctype html><html lang="vi"><meta charset="utf-8">
<title>KOME — không có quyền</title>
{% include "_chung.html" %}
<style> h1{font-size:1.3rem} </style>
{% include "_nav.html" %}
<div class="ngay-thieu">
<h1>🔐 Bạn không có quyền sửa Ngân sách</h1>
<p>Màn <strong>Ngân sách</strong> là nơi đặt chỉ tiêu doanh thu cho từng nhân
viên từng tháng. Con số đó là thước đo mà cả công ty được đánh giá theo, nên
nó chỉ mở cho chủ doanh nghiệp.</p>
<p>Cần đặt hoặc sửa chỉ tiêu? Nhờ người quản trị cấp quyền cho tài khoản
{% if nguoi %}<strong>{{ nguoi.ten_dang_nhap }}</strong>{% endif %}.</p>
<p>Tiến độ so với chỉ tiêu vẫn xem được bình thường ở
<a href="/bao-cao">Báo cáo doanh thu</a>.</p>
</div>
</html>
</main>
```

Tạo `kome/web/templates/ngan_sach.html`:

```html
<!-- kome/web/templates/ngan_sach.html
     Bảng nhập chỉ tiêu: 5 người phụ trách × 12 tháng của một kỳ.

     `inputmode="numeric"` chứ KHÔNG `type="number"`: trên Chrome, cuộn chuột
     trên một ô type=number là đổi số trong ô đó — và người dùng bảng 60 ô
     chắc chắn sẽ cuộn.

     Ô chưa đặt chỉ tiêu hiện TRỐNG, không hiện 0. "Chưa đặt" khác "bằng
     không" — cùng nếp mart.san_pham_360.ton. -->
<!doctype html><html lang="vi"><meta charset="utf-8">
<title>KOME — ngân sách</title>
{% include "_chung.html" %}
<style>
 .chon-ky{display:flex;flex-wrap:wrap;gap:.4rem;margin:.5rem 0 1rem}
 .chon-ky a{padding:.3rem .8rem;border:1px solid var(--vien);border-radius:999px;
      text-decoration:none;font-size:.9rem}
 .chon-ky a.dang-xem{background:var(--nen-the);border-color:var(--do);
      color:var(--do-chu);font-weight:600}
 .bang-cuon{overflow-x:auto}
 table{font-size:.92rem}
 th.thang{font-variant-numeric:tabular-nums;white-space:nowrap}
 td input{width:7.5rem;text-align:right;font-family:var(--font-so);
      font-variant-numeric:tabular-nums;padding:.25rem .4rem;
      border:1px solid var(--vien);border-radius:6px;
      background:var(--nen-the);color:var(--chu)}
 td input.sai{border-color:var(--loi-vien);background:var(--loi-nen)}
 td.so,th.so{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
 .tong{font-weight:600;background:var(--nen-phu)}
 .luu{margin:1rem 0;padding:.5rem 1.2rem;border-radius:8px;border:1px solid var(--do);
      background:var(--do);color:#fff;font-size:.95rem;cursor:pointer}
 .ghi-chu{color:var(--chu-nhat);font-size:.85rem;margin:.25rem 0 .75rem}
</style>
{% include "_nav.html" %}
<h1>Ngân sách — chỉ tiêu doanh thu</h1>

<div class="chon-ky">
 {% for k in b.moi_ky %}
 <a href="/ngan-sach?ky={{ k }}"{% if k == b.company_fy %} class="dang-xem"{% endif %}>Kỳ {{ k }}</a>
 {% endfor %}
</div>

{% if loi %}
<div class="ngay-thieu">Có {{ loi|length }} ô không đọc được thành số —
<strong>chưa ô nào được lưu</strong>. Sửa những ô viền đỏ rồi bấm Lưu lại.
Chỉ nhận chữ số; dấu chấm, dấu phẩy và dấu cách đều bỏ qua được.</div>
{% endif %}

<p class="ghi-chu">Ô để trống nghĩa là <strong>chưa đặt chỉ tiêu</strong>.
Muốn đặt chỉ tiêu bằng không thì gõ số <code>0</code> — hai điều đó khác nhau,
và màn Báo cáo hiện chúng khác nhau.</p>

<form method="post" action="/ngan-sach">
<input type="hidden" name="ky" value="{{ b.company_fy }}">
<div class="bang-cuon">
<table>
 <tr><th>Nhân viên</th>
  {% for th in b.thang %}<th class="thang">{{ th }}</th>{% endfor %}
  <th class="so">Cả kỳ</th></tr>
 {% for n in b.nguoi %}
 <tr><td>{{ n.ten }}<br><small>{{ n.ma }}</small></td>
  {% for th in b.thang %}
  {% set khoa = n.ma ~ '-' ~ th %}
  {# Thứ tự ba nhánh của `value` là có nghĩa:
     1. `da_go` — biểu mẫu vừa bị từ chối vì một ô rác, phải hiện lại ĐÚNG
        những gì người ta gõ, kể cả ô sai. Bắt gõ lại 60 ô vì một ô sai là
        cách chắc chắn để không ai dùng màn này lần thứ hai.
     2. `o_txt` — giá trị đang lưu trong CSDL.
     3. rỗng — CHƯA ĐẶT. Không in 0: "chưa đặt" khác "bằng không". #}
  <td><input type="text" inputmode="numeric" autocomplete="off"
       name="o-{{ khoa }}"
       {% if khoa in loi %}class="sai"{% endif %}
       value="{% if khoa in da_go %}{{ da_go[khoa] }}{% elif khoa in o_txt %}{{ "{:,}".format(o_txt[khoa]).replace(",", ".") }}{% endif %}"></td>
  {% endfor %}
  <td class="so tong">¥{{ "{:,}".format(tong_nguoi[n.ma]).replace(",", ".") }}</td></tr>
 {% endfor %}
 <tr class="tong"><td>Cả nhóm</td>
  {% for th in b.thang %}
  <td class="so">¥{{ "{:,}".format(tong_thang[th]).replace(",", ".") }}</td>
  {% endfor %}
  <td class="so">¥{{ "{:,}".format(tong_nguoi.values() | sum).replace(",", ".") }}</td></tr>
</table>
</div>
<button class="luu" type="submit">Lưu</button>
</form>
</html>
</main>
```

- [ ] **Step 7: Thêm mục vào `_nav.html`**

Trong `kome/web/templates/_nav.html`, ngay TRƯỚC khối `{% if hien_kho %}`:

```html
    {# Ngân sách nằm trong nhóm TỔNG QUAN chứ không trong HỆ THỐNG: đặt chỉ
       tiêu là việc kinh doanh của chủ DN, không phải việc kỹ thuật. Nhưng nó
       CÓ bọc `hien_ngan_sach` — cùng lý lẽ với `hien_kho`: mời người ta bấm
       vào một thứ sẽ từ chối họ thì tệ hơn là không hiện.

       Icon `target` — TA CHỌN trong bộ 24 icon của gói thiết kế; gói đó
       không có mục "Ngân sách" riêng (nó là một khối bên trong Dashboard). #}
    {% if hien_ngan_sach %}
    <a href="/ngan-sach"{% if trang == 'ngan-sach' %} class="dang-xem" aria-current="page"{% endif %}><svg class="ic" viewBox="0 0 18 18" aria-hidden="true" focusable="false"><circle cx="9" cy="9" r="6.4"></circle><circle cx="9" cy="9" r="3.4"></circle><circle cx="9" cy="9" r="0.8"></circle></svg>Ngân sách</a>
    {% endif %}
```

Đặt nó ngay sau dòng `/bao-cao` trong nhóm TỔNG QUAN.

- [ ] **Step 8: Chạy test của task và cả bộ**

Chạy: `python -u -m pytest tests/test_ngan_sach_web.py tests/test_nguoi_dung.py tests/test_bao_mat.py tests/test_giao_dien.py -v`
Mong đợi: PASS. `test_giao_dien.py::test_moi_template_dung_nav_deu_dong_main` canh hai template mới có `</main>` — nếu đỏ thì thiếu dòng đó ở cuối file.

Chạy: `python -u -m pytest -v`
Mong đợi: PASS toàn bộ. `tests/test_tao_nguoi_dung.py` có thể đỏ vì chữ ký `dat_quyen` đổi — **đó là việc của Task 5**, ghi lại số test đỏ và tên chúng vào báo cáo, đừng sửa `scripts/` ở task này.

- [ ] **Step 9: Commit**

```bash
git add kome/web/nguoi_dung.py kome/web/app.py kome/web/templates/ngan_sach.html kome/web/templates/cam_ngan_sach.html kome/web/templates/_nav.html tests/test_ngan_sach_web.py
git commit -F - <<'MSG'
feat: man /ngan-sach va co quyen duoc_sua_ngan_sach (dot 5a, task 3)

Hang rao quyen THAT dau tien cua app ngoai luong nap OBC. Sao y nep
duoc_vao_kho_du_lieu: tra app.nguoi_dung MOI LUOT GOI (khong nhet vao ve -
ve song 12 gio, thu hoi quyen tren man co nut ghi phai an ngay hom nay), va
403 kem trang giai thich chu khong chuyen huong im lang.

Gac o middleware nen no gac CA GET LAN POST bang mot cho duy nhat. Gac moi
GET la de nguyen cua ghi mo toang cho ai biet go curl.

dat_quyen nhan None = khong doi co do. Mac dinh False se lam lenh "cap quyen
ngan sach" am tham thu hoi quyen Kho du lieu cua cung nguoi.

Mot o rac => KHONG ghi o nao, va bieu mau hien lai dung nhung gi nguoi ta vua
go. Ghi mot nua roi bao loi la de nguoi ta khong biet nua nao da vao.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

## Task 4: Bốn khối ngân sách trên `/bao-cao`

**Files:**
- Modify: `kome/bao_cao.py` (thêm dataclass + hai hàm ở cuối file)
- Modify: `kome/web/app.py` (route `/bao-cao` truyền thêm ngữ cảnh)
- Modify: `kome/web/templates/bao_cao.html` (bốn khối)
- Create: `tests/test_ngan_sach_bao_cao.py`

**Interfaces:**
- Consumes: `mart.tien_do_ngan_sach`, `mart.ngay_kinh_doanh` (Task 1); `core.dim_salesperson`; `mart.moc_thoi_gian`.
- Produces:
  - `@dataclass(frozen=True) class TienDoNguoi: ma: str; ten: str | None; thuc_te: int; muc_tieu: int | None; muc_tieu_den_hom_nay: int | None; tien_do: float | None; cung_ky: int | None`
  - `@dataclass(frozen=True) class MocLuyKe: thang: str; thuc_te: int | None; ngan_sach: int | None`
  - `@dataclass(frozen=True) class TienDoNganSach: company_fy: int; thang: str; hom_nay: date | None; ngay_kd: int; ngay_kd_da_qua: int; thuc_te: int; muc_tieu: int | None; muc_tieu_den_hom_nay: int | None; tien_do: float | None; nguoi: list[TienDoNguoi]; luy_ke: list[MocLuyKe]; co_ngan_sach: bool`
  - `def tien_do_ngan_sach(conn, company_fy: int | None = None) -> TienDoNganSach | None` — `None` khi kho chưa có dòng bán nào.
  - `def ve_luy_ke(td: TienDoNganSach) -> dict` — cùng hình dạng trả về với `ve_bieu_do`: `{"co": bool, ...}`.

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_ngan_sach_bao_cao.py`:

```python
"""Đợt 5a Task 4 — bốn khối ngân sách trên màn Báo cáo."""
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kome.bao_cao import tien_do_ngan_sach, ve_luy_ke
from kome.web.app import create_app


@pytest.fixture
def client(conn, test_db_url):
    return TestClient(create_app(db_url=test_db_url))


def _ban(conn, batch, ngay: date, sale: str, amount=110_000, tax=10_000, gp=30_000,
         khach="000000009292"):
    from kome.loaders import sales
    b = batch(abs(hash((ngay, sale, amount, khach))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{sale}", "line_seq": 1, "sales_date": ngay,
        "customer_code": khach, "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": amount, "tax_amount": tax, "cost": amount - tax - gp,
        "gross_profit": gp, "paid_amount": 0, "salesperson_code": sale,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


def _chi_tieu(conn, sale, thang: date, muc_tieu):
    conn.execute("INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
                 "VALUES (%s, %s, %s)", (sale, thang, muc_tieu))
    conn.commit()


def test_thang_lay_theo_HOM_NAY_khong_theo_dong_ho_that(conn, batch):
    """[CRITICAL] Đo thật 2026-09-22: phiếu bán mới nhất trong kho là
    2026-07-31 — gần hai tháng không ai nạp file bán hàng. Lấy current_date
    thì trang báo "tháng 9 đạt 0% ngân sách" trong khi sự thật là chưa ai nạp
    dữ liệu tháng 9, và người ta đi hỏi nhân viên vì sao không bán được gì."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    td = tien_do_ngan_sach(conn)
    assert td.thang == "2026-07"
    assert td.hom_nay == date(2026, 7, 31)


def test_kho_rong_thi_tra_None_chu_khong_no(conn):
    assert tien_do_ngan_sach(conn) is None


def test_ma_ngoai_dim_salesperson_co_dong_rieng_khong_bi_bo(conn, batch):
    """[CRITICAL] Bỏ dòng này đi là giấu doanh thu thật; gắn cho nó một chỉ
    tiêu là bịa ra một con số."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _ban(conn, batch, date(2026, 7, 30), "0000", amount=33_000, tax=3_000, gp=9_000,
         khach="000000009293")
    td = tien_do_ngan_sach(conn)
    la = next(n for n in td.nguoi if n.ma == "0000")
    assert la.ten is None, "mã ngoài danh sách phụ trách KHÔNG có tên"
    assert la.thuc_te == 30_000 and la.muc_tieu is None


def test_khong_ai_dat_chi_tieu_thi_co_ngan_sach_FALSE(conn, batch):
    """Khối rỗng phải nói "chưa đặt chỉ tiêu", KHÔNG hiện 0%."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    td = tien_do_ngan_sach(conn)
    assert td.co_ngan_sach is False
    assert td.muc_tieu is None and td.tien_do is None


def test_tong_nhom_cong_du_moi_nguoi(conn, batch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _ban(conn, batch, date(2026, 7, 30), "0105", khach="000000009293")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 6_000_000)
    _chi_tieu(conn, "0105", date(2026, 7, 1), 4_000_000)
    td = tien_do_ngan_sach(conn)
    assert td.muc_tieu == 10_000_000
    assert td.thuc_te == 200_000
    assert td.co_ngan_sach is True


def test_luy_ke_DUNG_o_thang_cua_hom_nay(conn, batch):
    """[IMPORTANT] Đường luỹ kế kéo dài tới hết kỳ bằng số 0 đọc thành "doanh
    thu sụp", không phải "chưa có dữ liệu"."""
    _ban(conn, batch, date(2025, 9, 15), "0104")
    _ban(conn, batch, date(2025, 10, 15), "0104", khach="000000009293")
    for t in ("2025-08", "2025-09", "2025-10", "2025-11"):
        _chi_tieu(conn, "0104", date(int(t[:4]), int(t[5:]), 1), 1_000_000)
    td = tien_do_ngan_sach(conn, 2026)
    sau = {m.thang: m.thuc_te for m in td.luy_ke}
    assert sau["2025-10"] == 200_000, "luỹ kế tới tháng của hom_nay"
    assert sau["2025-11"] is None, "sau hom_nay phải là None, không phải 0"
    ns = {m.thang: m.ngan_sach for m in td.luy_ke}
    assert ns["2025-11"] == 4_000_000, "nhịp ngân sách vẫn chạy hết kỳ"


def test_ve_luy_ke_khong_no_khi_chua_co_chi_tieu(conn, batch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    assert ve_luy_ke(tien_do_ngan_sach(conn))["co"] is False


def test_trang_bao_cao_in_ro_thang_va_ngay_moc(client, conn, batch):
    """Khối phải nói nó đang nói về tháng nào và số liệu tới ngày nào."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 6_000_000)
    html = client.get("/bao-cao").text
    assert "2026-07" in html
    assert "31/07/2026" in html


def test_trang_bao_cao_khong_co_chi_tieu_thi_moi_sang_man_ngan_sach(client, conn, batch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    html = client.get("/bao-cao").text
    assert "Chưa đặt chỉ tiêu" in html
    assert '/ngan-sach' in html


def test_tien_do_ngan_sach_khong_qua_3_truy_van(conn, batch, monkeypatch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 6_000_000)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    tien_do_ngan_sach(conn)
    assert dem["n"] <= 3, f"tien_do_ngan_sach() chạy {dem['n']} truy vấn"
```

- [ ] **Step 2: Chạy test để thấy nó đỏ**

Chạy: `python -u -m pytest tests/test_ngan_sach_bao_cao.py -v`
Mong đợi: FAIL — `ImportError: cannot import name 'tien_do_ngan_sach' from 'kome.bao_cao'`.

- [ ] **Step 3: Thêm vào `kome/bao_cao.py`**

Thêm vào cuối file (sau `ve_bieu_do`):

```python
# ---- Ngân sách (đợt 5a) -------------------------------------------------
# Mọi công thức nằm ở mart.tien_do_ngan_sach (migration 026). Ở đây chỉ hỏi
# và sắp xếp để hiển thị — cùng nguyên tắc đã ghi ở đầu file này.
#
# `thang_cua_ky` NHẬP từ kome/ngan_sach.py chứ không chép lại: "12 tháng của
# một kỳ, 8月 trước" là một định nghĩa, và hai bản chép của nó là hai thứ sẽ
# trôi khỏi nhau đúng lúc ai đó đổi năm tài chính của công ty. Dòng
# `from kome.ngan_sach import thang_cua_ky` đặt ở KHỐI NHẬP ĐẦU FILE, theo
# nếp của mọi module khác trong repo — không có vòng nhập nào vì
# kome/ngan_sach.py không nhập kome/bao_cao.py.

@dataclass(frozen=True)
class TienDoNguoi:
    ma: str
    ten: str | None          # None = mã KHÔNG có trong core.dim_salesperson
    thuc_te: int
    muc_tieu: int | None
    muc_tieu_den_hom_nay: int | None
    tien_do: float | None
    cung_ky: int | None      # doanh thu cùng tháng năm trước, None nếu không có


@dataclass(frozen=True)
class MocLuyKe:
    thang: str
    thuc_te: int | None      # None = tháng nằm SAU hom_nay (chưa có dữ liệu)
    ngan_sach: int | None


@dataclass(frozen=True)
class TienDoNganSach:
    company_fy: int
    thang: str
    hom_nay: date | None
    ngay_kd: int
    ngay_kd_da_qua: int
    thuc_te: int
    muc_tieu: int | None
    muc_tieu_den_hom_nay: int | None
    tien_do: float | None
    nguoi: list[TienDoNguoi]
    luy_ke: list[MocLuyKe]
    co_ngan_sach: bool


def tien_do_ngan_sach(conn, company_fy: int | None = None) -> "TienDoNganSach | None":
    """Tiến độ so với chỉ tiêu. None khi kho chưa có dòng bán nào.

    Tháng đang xét là tháng của `mart.moc_thoi_gian.hom_nay`, KHÔNG phải tháng
    theo đồng hồ thật. Đo thật 2026-09-22: phiếu bán mới nhất là 2026-07-31 —
    gần hai tháng không ai nạp file bán hàng. Lấy current_date thì trang báo
    "tháng 9 đạt 0% ngân sách" trong khi sự thật là chưa ai nạp dữ liệu tháng 9.
    """
    r = conn.execute(
        """SELECT m.hom_nay, d.company_fy, to_char(m.hom_nay, 'YYYY-MM')
           FROM mart.moc_thoi_gian m
           JOIN core.dim_date d ON d.date_key = m.hom_nay""").fetchone()
    if r is None:
        return None
    hom_nay, fy_hom_nay, thang_hom_nay = r[0], r[1], r[2]
    ky = company_fy or fy_hom_nay
    thang = thang_hom_nay if ky == fy_hom_nay else thang_cua_ky(ky)[-1]

    # Một câu cho cả dòng theo người của tháng đang xét, kèm tên và cùng kỳ.
    # LEFT JOIN dim_salesperson: mã ngoài danh sách phụ trách vẫn có dòng, chỉ
    # là không có tên (§7.3 của đặc tả).
    # Lấy luôn ngay_kd/ngay_kd_da_qua từ chính view này thay vì hỏi
    # mart.ngay_kinh_doanh một lượt nữa: chúng đã là cột của
    # mart.tien_do_ngan_sach và giống nhau ở mọi dòng của cùng một tháng.
    # Một lượt hỏi qua pooler Tokyo mất ~260 ms — không đáng cho hai con số
    # đã nằm sẵn trong kết quả.
    dong = conn.execute(
            """SELECT t.salesperson_code, s.ten, t.thuc_te, t.muc_tieu,
                      t.muc_tieu_den_hom_nay, t.tien_do, tr.doanh_thu_thuan,
                      t.ngay_kd, t.ngay_kd_da_qua
               FROM mart.tien_do_ngan_sach t
               LEFT JOIN core.dim_salesperson s
                      ON s.salesperson_code = t.salesperson_code
               LEFT JOIN mart.ban_theo_nhan_vien_thang tr
                      ON tr.salesperson_code = t.salesperson_code
                     AND tr.thang = to_char(
                           to_date(%s, 'YYYY-MM') - interval '1 year', 'YYYY-MM')
               WHERE t.thang = %s
               ORDER BY t.salesperson_code""", (thang, thang)).fetchall()

    nguoi = [TienDoNguoi(
        ma=x[0], ten=x[1], thuc_te=int(x[2] or 0),
        muc_tieu=int(x[3]) if x[3] is not None else None,
        muc_tieu_den_hom_nay=int(x[4]) if x[4] is not None else None,
        tien_do=float(x[5]) if x[5] is not None else None,
        cung_ky=int(x[6]) if x[6] is not None else None) for x in dong]
    # Tháng không có dòng nào (chọn một kỳ đã qua mà tháng cuối kỳ không có
    # doanh thu lẫn chỉ tiêu) -> 0/0. Khi đó `co_ngan_sach` cũng FALSE nên
    # màn hình hiện khối "chưa đặt chỉ tiêu", không hiện bộ đếm ngày.
    ngay_kd, ngay_kd_da_qua = (dong[0][7], dong[0][8]) if dong else (0, 0)

    # Luỹ kế 12 tháng của kỳ. Tháng SAU hom_nay trả None cho thực tế: một
    # đường rơi xuống 0 đọc thành "doanh thu sụp", không phải "chưa có dữ liệu".
    thang_ky = thang_cua_ky(ky)
    theo_thang = {x[0]: (int(x[1] or 0), int(x[2]) if x[2] is not None else None)
                  for x in conn.execute(
        """SELECT thang, sum(thuc_te), sum(muc_tieu)
           FROM mart.tien_do_ngan_sach WHERE company_fy = %s
           GROUP BY thang""", (ky,)).fetchall()}

    luy_ke, c_tt, c_ns = [], 0, 0
    for th in thang_ky:
        tt, ns = theo_thang.get(th, (0, None))
        c_tt += tt
        c_ns += ns or 0
        luy_ke.append(MocLuyKe(
            thang=th,
            thuc_te=c_tt if th <= thang_hom_nay else None,
            ngan_sach=c_ns if c_ns else None))

    tong_tt = sum(n.thuc_te for n in nguoi)
    co_mt = [n.muc_tieu for n in nguoi if n.muc_tieu is not None]
    tong_mt = sum(co_mt) if co_mt else None
    co_moc = [n.muc_tieu_den_hom_nay for n in nguoi
              if n.muc_tieu_den_hom_nay is not None]

    return TienDoNganSach(
        company_fy=ky, thang=thang, hom_nay=hom_nay,
        ngay_kd=ngay_kd, ngay_kd_da_qua=ngay_kd_da_qua,
        thuc_te=tong_tt, muc_tieu=tong_mt,
        muc_tieu_den_hom_nay=sum(co_moc) if co_moc else None,
        tien_do=(tong_tt / tong_mt) if tong_mt else None,
        nguoi=nguoi, luy_ke=luy_ke, co_ngan_sach=bool(co_mt))


def ve_luy_ke(td: "TienDoNganSach | None") -> dict:
    """Toạ độ hai đường luỹ kế (thực tế và nhịp ngân sách) trên cùng một trục.

    Tự tính toạ độ SVG như `ve_bieu_do`: trang phải chạy cả trên Vercel (CSP
    chặn script ngoài) lẫn ở máy không có mạng.
    """
    if td is None or not td.co_ngan_sach:
        return {"co": False}
    cao_ve = CAO - LE_TREN - LE_DUOI
    rong_ve = RONG - LE_T - LE_P
    dinh = max([m.thuc_te or 0 for m in td.luy_ke]
               + [m.ngan_sach or 0 for m in td.luy_ke]) or 1
    buoc = rong_ve / max(len(td.luy_ke) - 1, 1)

    def _duong(lay) -> str:
        diem = []
        for i, m in enumerate(td.luy_ke):
            v = lay(m)
            if v is None:
                continue
            x = LE_T + i * buoc
            y = LE_TREN + cao_ve - cao_ve * (v / dinh)
            diem.append(f"{round(x, 1)},{round(y, 1)}")
        return " ".join(diem)

    return {"co": True, "rong": RONG, "cao": CAO, "dinh": dinh,
            "thuc_te": _duong(lambda m: m.thuc_te),
            "ngan_sach": _duong(lambda m: m.ngan_sach),
            "nhan": [m.thang for m in td.luy_ke]}
```

Thêm `from datetime import date` đã có sẵn ở đầu file — kiểm tra lại, không nhập trùng.

- [ ] **Step 4: Sửa route `/bao-cao`**

```python
    @app.get("/bao-cao", response_class=HTMLResponse)
    def bao_cao(request: Request, ky: int | None = None):
        """Bảng điều khiển bán hàng. `?ky=` là company_fy (năm KẾT THÚC kỳ),
        bỏ trống thì lấy kỳ gần nhất có dữ liệu.

        Mọi định nghĩa chỉ số nằm ở schema `mart` (migration 014 và 026) —
        trang này chỉ hiển thị. Xem ghi chú đầu kome/bao_cao.py.
        """
        try:
            with open_app_conn() as conn:
                bc = tinh_bao_cao(conn, ky)
                td = tien_do_ngan_sach(conn, ky)
            return _ve(request, "bao_cao.html",
                       {"bc": bc, "bd": ve_bieu_do(bc.thang), "td": td,
                        "lk": ve_luy_ke(td), "trang": "bao-cao"})
        except Exception as e:
            return _loi(request, "mở trang báo cáo", e)
```

và sửa dòng nhập ở đầu `app.py`: `from kome.bao_cao import tinh_bao_cao, ve_bieu_do, tien_do_ngan_sach, ve_luy_ke`.

- [ ] **Step 5: Thêm bốn khối vào `bao_cao.html`**

Chèn ngay sau dải chip chọn kỳ, TRƯỚC biểu đồ 12 tháng đang có:

```html
{% if td %}
<h2>Tiến độ ngân sách — tháng {{ td.thang }}</h2>
{# Tháng lấy theo mart.moc_thoi_gian.hom_nay, KHÔNG theo đồng hồ thật. In ra
   cả tháng lẫn ngày mốc: dữ liệu bán có thể chậm hàng tuần so với hôm nay, và
   một khối không nói ngày mốc sẽ bị đọc là "tháng này bán được có thế". #}
<p class="ghi-chu">Số liệu đến {{ td.hom_nay.strftime("%d/%m/%Y") }} ·
{{ td.ngay_kd_da_qua }}/{{ td.ngay_kd }} ngày làm việc của tháng.
Ngày làm việc chưa trừ ngày lễ Nhật.</p>

{% if not td.co_ngan_sach %}
<div class="ngay-thieu">Chưa đặt chỉ tiêu cho kỳ này.
<a href="/ngan-sach?ky={{ td.company_fy }}">Đặt chỉ tiêu</a> rồi quay lại đây.</div>
{% else %}
<div class="so-lon">
 <div class="the"><div class="nhan">Thực tế</div>
  <div class="gia">¥{{ "{:,}".format(td.thuc_te) }}</div></div>
 <div class="the"><div class="nhan">Chỉ tiêu tháng</div>
  <div class="gia">¥{{ "{:,}".format(td.muc_tieu) }}</div></div>
 <div class="the"><div class="nhan">Tiến độ</div>
  <div class="gia">{{ "%.1f"|format(td.tien_do * 100) }}%</div></div>
 <div class="the"><div class="nhan">Mốc đến hôm nay</div>
  <div class="gia">¥{{ "{:,}".format(td.muc_tieu_den_hom_nay) }}</div>
  {# Con số in ra ngay cạnh vạch mốc: bất biến "mã hoá bằng màu phải kèm thứ
     đọc được" (_chung.html:76-77). #}
  <div class="nhan">{{ "%.1f"|format(td.muc_tieu_den_hom_nay / td.muc_tieu * 100) }}% chỉ tiêu</div></div>
</div>

<h2>Luỹ kế thực tế so với nhịp ngân sách</h2>
{% if lk.co %}
<div class="khung-bd">
<svg viewBox="0 0 {{ lk.rong }} {{ lk.cao }}" width="100%" height="{{ lk.cao }}"
     role="img" aria-label="Luỹ kế doanh thu so với nhịp ngân sách">
 <polyline points="{{ lk.ngan_sach }}" fill="none" stroke="var(--chu-nhat)"
           stroke-width="2" stroke-dasharray="5 4"></polyline>
 <polyline points="{{ lk.thuc_te }}" fill="none" stroke="var(--do)"
           stroke-width="2.5"></polyline>
</svg>
</div>
<div class="chu-thich">
 <span><i class="mau" style="background:var(--do)"></i>Luỹ kế thực tế</span>
 <span><i class="mau" style="background:var(--chu-nhat)"></i>Nhịp ngân sách</span>
 <span>Đỉnh trục: ¥{{ "{:,}".format(lk.dinh) }}</span>
</div>
{% endif %}
{% endif %}

{# Bảng này nằm NGOÀI nhánh `co_ngan_sach`: chưa đặt chỉ tiêu thì các cột
   chỉ tiêu in "—", nhưng cột Thực tế và Tỷ trọng vẫn là số thật và vẫn đáng
   xem. Tiêu đề cũng ở ngoài — một bảng không tiêu đề là một bảng người đọc
   không biết nó nói về tháng nào. #}
<h2>Kết quả theo từng nhân viên — tháng {{ td.thang }}</h2>

<div class="bang-cuon">
<table>
 <tr><th>Nhân viên</th><th class="so">Thực tế</th><th class="so">Chỉ tiêu</th>
  <th class="so">Tiến độ</th><th class="so">Mốc đến hôm nay</th>
  <th class="so">Cùng kỳ năm trước</th><th class="so">So cùng kỳ</th>
  <th class="so">Tỷ trọng</th></tr>
 {% for n in td.nguoi %}
 <tr>
  {# Mã ngoài core.dim_salesperson: bỏ dòng này đi là giấu doanh thu thật;
     gắn cho nó một chỉ tiêu là bịa ra một con số. #}
  <td>{% if n.ten %}{{ n.ten }}<br><small>{{ n.ma }}</small>
      {% else %}{{ n.ma }}<br><small>(mã không có trong danh sách phụ trách)</small>
      {% endif %}</td>
  <td class="so">¥{{ "{:,}".format(n.thuc_te) }}</td>
  <td class="so">{% if n.muc_tieu is not none %}¥{{ "{:,}".format(n.muc_tieu) }}{% else %}—{% endif %}</td>
  <td class="so">{% if n.tien_do is not none %}
      <span class="{{ 'manh' if n.tien_do >= 1 else 'yeu' }}">{{ "%.1f"|format(n.tien_do * 100) }}%</span>
      {% else %}—{% endif %}</td>
  <td class="so">{% if n.muc_tieu_den_hom_nay is not none %}¥{{ "{:,}".format(n.muc_tieu_den_hom_nay) }}{% else %}—{% endif %}</td>
  {# Dữ liệu bán bắt đầu 2025-03-03, trước mốc đó KHÔNG TỒN TẠI. Để trống và
     nói rõ, đúng nếp co_cung_ky của mart.ban_theo_thang_so_sanh. #}
  <td class="so">{% if n.cung_ky is not none %}¥{{ "{:,}".format(n.cung_ky) }}{% else %}không có dữ liệu{% endif %}</td>
  <td class="so">{% if n.cung_ky %}{{ "%+.1f"|format((n.thuc_te / n.cung_ky - 1) * 100) }}%{% else %}—{% endif %}</td>
  <td class="so">{% if td.thuc_te %}{{ "%.1f"|format(n.thuc_te / td.thuc_te * 100) }}%{% else %}—{% endif %}</td>
 </tr>
 {% endfor %}
</table>
</div>
{% endif %}
```

- [ ] **Step 6: Chạy test**

Chạy: `python -u -m pytest tests/test_ngan_sach_bao_cao.py tests/test_bao_cao.py -v`
Mong đợi: PASS.

- [ ] **Step 7: Commit**

```bash
git add kome/bao_cao.py kome/web/app.py kome/web/templates/bao_cao.html tests/test_ngan_sach_bao_cao.py
git commit -F - <<'MSG'
feat: bon khoi ngan sach tren /bao-cao (dot 5a, task 4)

Thang lay theo mart.moc_thoi_gian.hom_nay chu khong theo dong ho that, va
khoi IN RA ca thang lan ngay moc. Do that 2026-09-22: phieu ban moi nhat la
2026-07-31, gan hai thang khong ai nap file ban hang - lay current_date thi
trang bao "thang 9 dat 0% ngan sach" trong khi su that la chua ai nap du lieu
thang 9, va nguoi ta di hoi nhan vien vi sao khong ban duoc gi.

Duong luy ke DUNG o thang cua hom_nay chu khong keo dai toi het ky bang so 0:
mot duong roi xuong 0 doc thanh "doanh thu sup", khong phai "chua co du lieu".

Ma phu trach ngoai dim_salesperson co dong rieng, khong ten, khong chi tieu.
Bo dong do di la giau doanh thu that; gan cho no mot chi tieu la bia.

Chua ai dat chi tieu => noi "Chua dat chi tieu" kem lien ket sang /ngan-sach,
khong hien 0%.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

## Task 5: Script cấp quyền và tài liệu

**Files:**
- Modify: `scripts/tao_nguoi_dung.py`
- Modify: `tests/test_tao_nguoi_dung.py`
- Modify: `CLAUDE.md`
- Modify: `docs/runbook.md`

**Interfaces:**
- Consumes: `nguoi_dung.tao(..., ngan_sach=...)`, `nguoi_dung.dat_quyen(conn, ten, kho_du_lieu=None, ngan_sach=None)` (Task 3).
- Produces: cờ dòng lệnh `--ngan-sach` / `--bo-ngan-sach`; cột "Ngân sách" trong bảng liệt kê.

- [ ] **Step 1: Đọc test hiện có rồi mở rộng**

Mở `tests/test_tao_nguoi_dung.py`, tìm mọi chỗ gọi `dat_quyen` hoặc khẳng định trên bảng liệt kê, và sửa cho hợp chữ ký mới. Thêm ba test:

```python
def test_cap_co_ngan_sach_KHONG_dung_toi_co_kho_du_lieu(conn, capsys):
    """[CRITICAL] Hai cờ độc lập. Một lệnh cấp quyền ngân sách mà âm thầm thu
    hồi quyền Kho dữ liệu là mất quyền nạp dữ liệu của người phụ trách nạp —
    và không ai biết cho tới 13:30 hôm sau."""
    from kome.web import nguoi_dung as ND
    ND.tao(conn, "an", "mat-khau-cua-an-2026", kho_du_lieu=True)
    conn.commit()
    ND.dat_quyen(conn, "an", ngan_sach=True)
    conn.commit()
    n = ND.liet_ke(conn)[0]
    assert n.duoc_vao_kho_du_lieu is True and n.duoc_sua_ngan_sach is True


def test_bo_co_ngan_sach(conn):
    from kome.web import nguoi_dung as ND
    ND.tao(conn, "an", "mat-khau-cua-an-2026", ngan_sach=True)
    conn.commit()
    ND.dat_quyen(conn, "an", ngan_sach=False)
    conn.commit()
    assert ND.liet_ke(conn)[0].duoc_sua_ngan_sach is False


def test_liet_ke_hien_cot_ngan_sach(conn, capsys):
    from kome.web import nguoi_dung as ND
    from scripts.tao_nguoi_dung import chay
    ND.tao(conn, "an", "mat-khau-cua-an-2026", ngan_sach=True)
    conn.commit()
    chay([], conn)
    assert "Ngân sách" in capsys.readouterr().out
```

- [ ] **Step 2: Chạy test để thấy nó đỏ**

Chạy: `python -u -m pytest tests/test_tao_nguoi_dung.py -v`
Mong đợi: FAIL.

- [ ] **Step 3: Sửa `scripts/tao_nguoi_dung.py`**

Bốn chỗ:

(a) Docstring đầu file — thêm ví dụ:

```
    python scripts/tao_nguoi_dung.py them chu --ngan-sach
    python scripts/tao_nguoi_dung.py quyen chu --ngan-sach
    python scripts/tao_nguoi_dung.py quyen chu --bo-ngan-sach
```

và thêm đoạn giải thích cuối docstring:

```
--ngan-sach là quyền vào màn Ngân sách: đặt và sửa chỉ tiêu doanh thu của
từng nhân viên từng tháng. Con số đó là thước đo mà cả công ty được đánh giá
theo. Chỉ cấp cho chủ doanh nghiệp.

CẠM BẪY: cả hai cờ chỉ có tác dụng khi máy này CÓ đặt KOME_SESSION_SECRET.
Để trống biến đó là không có cổng đăng nhập và không có phân quyền — ai mở
được trang cũng bấm được nút Hoàn tác VÀ sửa được ngân sách.
```

(b) `HUONG_DAN` — thêm hai dòng tương ứng.

(c) `liet_ke` — thêm cột:

```python
def liet_ke(conn) -> int:
    ds = ND.liet_ke(conn)
    if not ds:
        print("Chưa có tài khoản nào. Tạo bằng:  python scripts/tao_nguoi_dung.py them <tên>")
        return 0
    print(f"{'Tên đăng nhập':<20}{'Mã sale':<10}{'Phụ trách':<24}"
          f"{'Kho dữ liệu':<14}Ngân sách")
    print("-" * 84)
    for n in ds:
        print(f"{n.ten_dang_nhap:<20}{n.salesperson_code or '—':<10}"
              f"{n.ten_sale or '—':<24}"
              f"{('CÓ' if n.duoc_vao_kho_du_lieu else '—'):<14}"
              f"{'CÓ' if n.duoc_sua_ngan_sach else '—'}")
    print("\nKho dữ liệu = được nạp file VÀ hoàn tác lần nạp (xoá dữ liệu khỏi kho).")
    print("Ngân sách   = được đặt và sửa chỉ tiêu doanh thu của cả công ty.")
    return 0
```

(d) `them` nhận thêm `ngan_sach`:

```python
def them(conn, ten: str, sale: str | None, kho_du_lieu: bool,
         ngan_sach: bool, doc_mat_khau) -> int:
    mk = _hoi_mat_khau(doc_mat_khau)
    if mk is None:
        return 1
    try:
        ND.tao(conn, ten, mk, salesperson_code=sale, kho_du_lieu=kho_du_lieu,
               ngan_sach=ngan_sach)
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        print(f"Đã có tài khoản tên '{ten}'. Đổi mật khẩu bằng:  "
              f"python scripts/tao_nguoi_dung.py doi-mat-khau {ten}")
        return 1
    except psycopg.errors.ForeignKeyViolation:
        conn.rollback()
        print(f"Không có người phụ trách mã '{sale}' trong OBC. "
              f"Chạy không tham số để xem các mã đang dùng, hoặc bỏ --sale nếu "
              f"người này không phụ trách khách nào.")
        return 1
    conn.commit()
    print(f"Đã tạo '{ten}'"
          + (f", phụ trách mã {sale}" if sale else ", không phụ trách khách nào")
          + (", CÓ quyền vào Kho dữ liệu" if kho_du_lieu
             else ", không có quyền vào Kho dữ liệu")
          + (", CÓ quyền sửa Ngân sách." if ngan_sach
             else ", không có quyền sửa Ngân sách."))
    return 0
```

(e) `quyen` đổi thành hai cờ độc lập:

```python
def quyen(conn, ten: str, kho_du_lieu: bool | None,
          ngan_sach: bool | None) -> int:
    """`None` = KHÔNG đụng tới cờ đó.

    Truyền False thay cho None sẽ làm lệnh "cấp quyền ngân sách" âm thầm thu
    hồi quyền Kho dữ liệu của cùng người — tức mất quyền nạp dữ liệu của
    người phụ trách nạp, và không ai biết cho tới 13:30 hôm sau.
    """
    if not ND.dat_quyen(conn, ten, kho_du_lieu=kho_du_lieu, ngan_sach=ngan_sach):
        print(f"Không có tài khoản tên '{ten}'. Chạy không tham số để xem danh sách.")
        return 1
    conn.commit()
    if kho_du_lieu is not None:
        print(f"'{ten}' " + ("GIỜ vào được" if kho_du_lieu else "KHÔNG còn vào được")
              + " màn Kho dữ liệu.")
    if ngan_sach is not None:
        print(f"'{ten}' " + ("GIỜ sửa được" if ngan_sach else "KHÔNG còn sửa được")
              + " Ngân sách.")
    print("Có hiệu lực ngay ở lượt bấm kế tiếp của họ.")
    return 0
```

(f) `chay()` — thêm hai cờ và sửa hai nhánh cuối:

```python
    kho = "--kho-du-lieu" in phan_con_lai
    bo_kho = "--bo-kho-du-lieu" in phan_con_lai
    ns = "--ngan-sach" in phan_con_lai
    bo_ns = "--bo-ngan-sach" in phan_con_lai
```

```python
    if lenh == "them":
        return them(conn, ten, sale, kho, ns, doc_mat_khau)
    if lenh == "doi-mat-khau":
        return doi_mat_khau(conn, ten, doc_mat_khau)
    # Hai cờ trái nhau: cấp và bỏ quyền cùng lúc là dấu hiệu người gõ không
    # chắc mình muốn gì. Không được im lặng chọn nhánh cấp quyền — đó là
    # nhánh nguy hiểm hơn.
    if kho and bo_kho:
        print("Vừa --kho-du-lieu vừa --bo-kho-du-lieu — chỉ chọn một.")
        return 2
    if ns and bo_ns:
        print("Vừa --ngan-sach vừa --bo-ngan-sach — chỉ chọn một.")
        return 2
    if not (kho or bo_kho or ns or bo_ns):
        print("Lệnh quyền cần một trong: --kho-du-lieu, --bo-kho-du-lieu, "
              "--ngan-sach, --bo-ngan-sach.")
        return 2
    # None = không đụng tới cờ đó. Một lệnh chỉ đổi cờ mà nó nói tới.
    return quyen(conn, ten,
                 kho_du_lieu=True if kho else (False if bo_kho else None),
                 ngan_sach=True if ns else (False if bo_ns else None))
```

- [ ] **Step 4: Chạy test**

Chạy: `python -u -m pytest tests/test_tao_nguoi_dung.py tests/test_nguoi_dung.py -v`
Mong đợi: PASS.

- [ ] **Step 5: Cập nhật `CLAUDE.md`**

(a) Trong bảng "Các trang của web app", thêm dòng sau `/bao-cao`:

```
| `/ngan-sach` | Đặt chỉ tiêu doanh thu: 5 người phụ trách × 12 tháng một kỳ. **Cần cờ `duoc_sua_ngan_sach`** | `app.ngan_sach`, `core.dim_salesperson`, `core.dim_date` |
```

(b) Thêm bốn bất biến mới vào đúng khu vực các bất biến khác:

```markdown
**Bất biến:** `mart.tien_do_ngan_sach` nối chỉ tiêu với thực tế bằng **`FULL
JOIN`**, không `LEFT JOIN` theo chiều nào cả. Nối từ chỉ tiêu sang thực tế thì
tháng có doanh thu mà QUÊN đặt chỉ tiêu biến mất khỏi báo cáo; nối ngược lại
thì người CÓ chỉ tiêu mà bán 0 đồng biến mất — đúng người cần nhìn nhất thì
không có dòng nào. Cả hai chiều đều mất dòng **mà trang vẫn vẽ ra bình
thường**, không lỗi nào nổ ra, cùng lớp lỗi đã ghi cho `/ban-do`. Đo thật
2026-09-22: dữ liệu bán có **6** mã phụ trách (`0000` `0002` `0004` `0102`
`0104` `0105`) trong khi `core.dim_salesperson` chỉ có **5** — `0000` có 1
khách và ¥28.981 doanh thu kỳ 7 và không bao giờ đặt được chỉ tiêu (khoá ngoại
chặn), nên phép nối xuất phát từ chỉ tiêu làm số tiền đó bốc hơi. Màn hình
hiện nó thành một dòng "(mã không có trong danh sách phụ trách)". Có test
canh: `tests/test_ngan_sach_mart.py::test_nguoi_co_chi_tieu_ma_KHONG_ban_duoc_dong_nao_van_co_dong`,
`::test_thang_co_doanh_thu_ma_QUEN_dat_chi_tieu_van_co_dong`,
`::test_ma_phu_trach_ngoai_dim_salesperson_van_hien_doanh_thu`.

**Bất biến:** `app.ngan_sach.thang` là **`date` mùng 1 có khoá ngoại tới
`core.dim_date`**, không phải `text 'YYYY-MM'`. `core.dim_date` phủ 2024-01-01
→ 2035-12-31, và `mart.ngan_sach_thang` nối sang nó để lấy `company_fy` — nên
một dòng chỉ tiêu ngoài dải lịch **biến mất khỏi mọi báo cáo mà không lỗi nào
nổ ra**: dữ liệu còn trong bảng, chỉ là không ai nhìn thấy nữa. Khoá ngoại
biến nó thành một lỗi ghi ngay tại chỗ nhập. Việc đổi `date` sang `'YYYY-MM'`
xảy ra ở **đúng một chỗ** — `mart.ngan_sach_thang` — vì mọi view khác của
`mart` đều dùng khoá tháng dạng chuỗi.

**Bất biến:** **không có dòng** trong `app.ngan_sach` = *chưa đặt chỉ tiêu*;
`muc_tieu = 0` = *đã đặt và đặt bằng không*. Màn nhập để ô trống cho cái thứ
nhất và in `0` cho cái thứ hai; `kome.ngan_sach.doc_so("")` trả `None` chứ
không trả `0`. Cùng nếp `mart.san_pham_360.ton` — hiện `0` cho thứ chưa biết
là nói một điều sai bằng con số. Và `kome.ngan_sach.luu()` **chỉ đụng những ô
đã đổi**: `sua_luc`/`sua_boi` phải trả lời "ai đổi con số NÀY lần cuối", không
phải "ai bấm Lưu lần cuối".

**Bất biến:** `core.dim_date` **không có cột ngày lễ Nhật**, nên
`mart.ngay_kinh_doanh` chỉ loại thứ Bảy và Chủ nhật. Tháng có Tuần lễ Vàng
(5月) hay Obon (8月) bị đếm thừa 2–4 ngày làm việc và vạch mốc "đáng lẽ đạt
tới hôm nay" **khắt khe hơn thực tế** ở đúng những tháng đó. Đây là hạn chế
CÓ TÊN, không phải thiếu sót chưa ai để ý: đừng "sửa" bằng cách bịa một định
nghĩa thứ hai (ví dụ "ngày có phiếu bán") — hai định nghĩa cùng tên là hai con
số nói hai điều. Cách sửa đúng là thêm cột ngày lễ vào `core.dim_date`, và đó
là một việc riêng.
```

(c) Trong mục "CẠM BẪY — cổng chỉ tồn tại khi có khoá ký", sửa câu cuối thành:

```markdown
Nói cách khác: **hai cờ quyền (`duoc_vao_kho_du_lieu` và `duoc_sua_ngan_sach`)
chỉ bảo vệ được nút Hoàn tác và màn Ngân sách khi máy trong công ty CŨNG đặt
`KOME_SESSION_SECRET`.**
```

- [ ] **Step 6: Cập nhật `docs/runbook.md`**

Thêm vào mục tạo tài khoản: cách cấp cờ `--ngan-sach`, và một dòng nói rõ chỉ chủ doanh nghiệp nên có cờ này. Thêm vào danh sách việc sau migration: chạy `python db/migrate.py` bằng vai trò `postgres` cho migration 026, rồi cấp cờ.

- [ ] **Step 7: Chạy TOÀN BỘ bộ test**

Chạy: `python -u -m pytest -v`
Mong đợi: PASS toàn bộ. Nếu `tests/test_kho_du_lieu.py` đỏ vì bộ dò tài liệu lỗi thời bắt một cụm từ trong `CLAUDE.md` vừa thêm: **đổi chữ trong `CLAUDE.md`, KHÔNG nới bộ dò** — bộ dò là so khớp chuỗi cố ý làm thô và nó nên giữ nguyên độ thô đó.

- [ ] **Step 8: Commit**

```bash
git add scripts/tao_nguoi_dung.py tests/test_tao_nguoi_dung.py CLAUDE.md docs/runbook.md
git commit -F - <<'MSG'
docs: cap quyen ngan sach qua script, va bon bat bien moi (dot 5a, task 5)

Lenh `quyen` chi dung co ma no noi toi: mot lenh cap quyen ngan sach ma am
tham thu hoi quyen Kho du lieu la mat quyen nap du lieu cua nguoi phu trach
nap, va khong ai biet cho toi 13:30 hom sau.

CLAUDE.md them bon bat bien: FULL JOIN cua tien_do_ngan_sach, khoa ngoai
thang -> dim_date, "chua dat" khac "bang khong", va han che CO TEN ve ngay le
Nhat. Cap nhat cam bay KOME_SESSION_SECRET de ke luon ca ngan sach.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

## Sau khi xong cả 5 task

Chạy `python -u -m pytest -v` một lần cuối trên cây đã gộp, rồi báo cho chủ sở hữu **KIỂM TAY §10 của đặc tả** — sáu việc, trong đó việc đầu tiên là chạy `python db/migrate.py` **bằng vai trò `postgres`**. Cho tới lúc đó, màn `/ngan-sach` và bốn khối mới trên `/bao-cao` sẽ lỗi trên bản đã triển khai vì migration 026 chưa chạy.
