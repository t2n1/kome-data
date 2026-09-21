# Kế hoạch triển khai — Đợt 3: Danh tính

> **Dành cho người thực thi (kể cả tác nhân AI):** BẮT BUỘC dùng kỹ năng
> `superpowers:subagent-driven-development` (khuyến nghị) hoặc
> `superpowers:executing-plans` để làm từng task một. Các bước dùng cú pháp
> ô đánh dấu (`- [ ]`) để theo dõi.

**Mục tiêu:** thay mật khẩu chung `KOME_MAT_KHAU` bằng đăng nhập riêng từng
người, chặn màn Kho dữ liệu theo quyền, và mặc định chỉ hiện "khách của tôi".

**Kiến trúc:** Tài khoản nằm ở `app.nguoi_dung` (scrypt + salt riêng từng
người). Vé đăng nhập vẫn **không trạng thái** — cookie `<id>.<hạn>.<HMAC>` ký
bằng `KOME_SESSION_SECRET`, tách hẳn khỏi mật khẩu của bất kỳ ai. Middleware
`chan_cua` đọc vé, tra một dòng `app.nguoi_dung` mỗi lượt, và gắn người dùng
vào `request.state.nguoi` cho mọi trang dùng. Web app có **hai kết nối CSDL**:
`DATABASE_URL` (vai trò nạp — chỉ màn Kho dữ liệu) và `DATABASE_URL_APP` (vai
trò `kome_app`, không ghi được vào `core` — mọi trang còn lại).

**Công nghệ:** Python 3.12 · FastAPI · Jinja2 · psycopg 3 · Postgres
(Supabase) · `hashlib.scrypt` + `hmac` của thư viện chuẩn. **Không thêm gói
nào**, không thêm JavaScript.

**Đặc tả:** `docs/superpowers/specs/2026-09-21-dot-3-danh-tinh-design.md`
(dưới đây gọi là **"đặc tả"**; mọi tham chiếu §x.y là của tài liệu đó)

---

## Ràng buộc toàn cục

Áp cho MỌI task, không nhắc lại ở từng task:

- **Không thêm gói nào** vào `requirements.txt` hay `pyproject.toml`. `scrypt`
  và `hmac` có sẵn trong thư viện chuẩn Python (R2 — bảo trì bằng AI, công
  nghệ phổ thông).
- **Không thêm một dòng JavaScript nào.**
- `kome/web/app.py` **KHÔNG được nhập** `kome.pipeline`, `pandas`,
  `python-calamine` ở mức ngoài cùng — chỉ nhập trong thân route. Có test
  canh: `tests/test_bao_mat.py::test_trang_chi_doc_khong_phu_thuoc_pandas`.
- **Migration LUÔN chạy bằng vai trò `postgres`.** `ALTER DEFAULT PRIVILEGES`
  trong repo này không có mệnh đề `FOR ROLE`.
- **File trong `db/migrations/` đã chạy thì KHÔNG sửa** — chỉ thêm file mới.
- **Mật khẩu, khoá, chuỗi bí mật KHÔNG BAO GIỜ vào git**, không vào thông báo
  commit, không vào file nào của repo. Chỉ nằm ở `.env` (đã trong
  `.gitignore`) và bảng Environment Variables của Vercel.
- **Không có kho phiên ở máy chủ.** Vercel chạy mỗi lượt gọi trong một tiến
  trình có thể khác nhau; bộ nhớ không dùng chung.
- Mọi test dựng app đều truyền `create_app(db_url=test_db_url)` — **không bao
  giờ** để nó tự lấy `DATABASE_URL`.
- Mọi template `include "_nav.html"` **phải tự đóng `</main>`** đúng một lần.
  Có test canh: `tests/test_giao_dien.py::test_moi_template_dung_nav_deu_dong_main`.
- Chạy test: `pytest -v` (từ gốc dự án). Chạy một file:
  `pytest tests/test_x.py -v`.
- Ngôn ngữ của code, ghi chú, commit: **tiếng Việt**, theo nếp repo. Thông báo
  commit không dấu (xem `git log`).
- Cuối mỗi commit thêm dòng: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## Việc tay phải làm TRƯỚC Task 1 (chủ sở hữu, ngoài git)

Đặc tả §8. Task 1–8 **chạy được và test xanh mà không cần ba việc này** (test
kiểm quyền bằng `has_table_privilege` trên vai trò `NOLOGIN`, không cần tài
khoản đăng nhập nào tồn tại). Nhưng **bản chạy thật sẽ không đúng thiết kế**
nếu thiếu:

1. SQL Editor của Supabase:
   `CREATE USER kome_app_user LOGIN PASSWORD '<mật khẩu mạnh>' IN ROLE kome_app;`
2. Thêm vào `.env` (máy công ty) **và** Environment Variables của Vercel:
   - `DATABASE_URL_APP` — cùng máy chủ, nhưng user là `kome_app_user`
   - `KOME_SESSION_SECRET` — chuỗi ngẫu nhiên, **tối thiểu 12 ký tự**
3. Sau khi triển khai: tạo tài khoản từng người bằng `scripts/tao_nguoi_dung.py`
   (Task 7), cấp `--kho-du-lieu` cho **đúng** người phụ trách nạp và chủ DN.

---

## Bốn chỗ đặc tả chưa lường tới — quyết định của kế hoạch này

Đọc kỹ code hiện tại làm lộ ra bốn chuyện đặc tả không nói. Ghi ở đây thay vì
giấu trong task, vì mỗi cái đều đổi hành vi thật:

### (a) Cổng chặn chỉ có hiệu lực khi `KOME_SESSION_SECRET` được đặt

Hôm nay `kome/web/app.py:146` chỉ gắn middleware `chan_cua` **nếu** có
`KOME_MAT_KHAU`. Máy trong công ty để trống nên **không có đăng nhập** — đó là
chủ ý đã ghi trong `CLAUDE.md` ("Đăng nhập: không bắt buộc").

Cơ chế mới giữ nguyên hình dạng đó: có `KOME_SESSION_SECRET` thì có cổng,
không có thì không. Hệ quả **phải nói thẳng**:

> Nút Hoàn tác — nút mà đợt 2a phát hiện có thể xoá cả một tháng doanh thu —
> **chỉ tồn tại trên máy trong công ty** (bản Vercel trả 403 cho `/upload` và
> `/undo` với mọi người). Nên cờ `duoc_vao_kho_du_lieu` chỉ thật sự bảo vệ
> được cái nút đó **khi máy trong công ty CŨNG đặt `KOME_SESSION_SECRET`**.

Đặc tả §8 việc 2 đã bảo đặt biến này vào **cả `.env`**, nên đây đúng là ý
định. Task 8 phải ghi rõ trong `runbook.md` và `CLAUDE.md`: **để trống
`KOME_SESSION_SECRET` ở máy công ty = mọi người vẫn bấm được nút xoá.**

### (b) Thanh điều hướng cần cờ quyền ở MỌI trang, không chỉ ở `/kho-du-lieu`

§6.4 bảo tra CSDL "mỗi lần vào những đường dẫn đó" (các đường dẫn Kho dữ
liệu). Nhưng §9 lại có test *"Người không có quyền: sidebar không chứa liên
kết Kho dữ liệu"* — mà sidebar vẽ ở **mọi trang**.

**Quyết định:** tra một dòng `app.nguoi_dung` **một lần mỗi lượt gọi**, ngay
trong middleware, dùng chung cho cả sidebar lẫn cổng chặn. Lý do: hai nguồn sự
thật cho cùng một cờ (vé mang một bản, CSDL mang bản khác) là một xưởng đẻ lỗi;
và một `SELECT ... WHERE id = %s` theo khoá chính rẻ hơn nhiều so với 4–6 truy
vấn tổng hợp mà mỗi trang đang chạy sẵn. Đổi lại: thu hồi quyền có hiệu lực ở
**lượt gọi kế tiếp**, đúng thứ §6.4 muốn.

### (c) Đăng nhập xong đang bị đẩy thẳng vào `/kho-du-lieu`

`bao_mat.duong_dan_an_toan` trả `/kho-du-lieu` khi không có nơi định đến
(`bao_mat.py:113`). Giữ nguyên thì **một sale đăng nhập xong nhận ngay 403** —
trang đầu tiên họ thấy là một lời từ chối. Task 4 đổi mặc định thành `/`.

### (d) Test có sẵn sẽ vỡ hàng loạt ngay khi `.env` có `KOME_SESSION_SECRET`

`tests/conftest.py:16` gọi `nap_env(bat_buoc=False)` — tức pytest **đọc
`.env`**. Đặc tả §8 bảo đặt `KOME_SESSION_SECRET` vào `.env`. Từ giây phút đó,
mọi `create_app()` trong test tự mọc cổng đăng nhập và ~30 test đỏ vì lý do
chẳng liên quan gì tới thứ chúng kiểm.

**Quyết định:** Task 4 thêm một fixture `autouse` vào `conftest.py` gỡ
`KOME_SESSION_SECRET` và `DATABASE_URL_APP` khỏi môi trường của **mọi** test.
Test nào muốn có cổng thì tự đặt lại (`tests/test_bao_mat.py`).

---

## Cấu trúc file

| File | Trách nhiệm | Task |
|---|---|---|
| `db/migrations/019_danh_tinh.sql` | **Tạo:** `core.dim_salesperson`, `app.nguoi_dung`, quyền cho `kome_app` | 1 |
| `tests/conftest.py` | **Sửa:** giữ `core.dim_salesperson` khỏi TRUNCATE; gỡ biến môi trường đăng nhập | 1, 4 |
| `tests/test_roles.py` | **Sửa:** thêm 3 test quyền của bảng mới | 1 |
| `kome/web/nguoi_dung.py` | **Tạo:** băm mật khẩu + đọc/ghi `app.nguoi_dung`. **Không** biết gì về HTTP | 2 |
| `tests/test_nguoi_dung.py` | **Tạo:** test cho module trên | 2 |
| `kome/web/bao_mat.py` | **Sửa:** vé theo người + `KOME_SESSION_SECRET`; xoá cơ chế mật khẩu chung | 3, 4 |
| `tests/test_bao_mat.py` | **Sửa:** viết lại cho cơ chế mới | 3, 4, 5 |
| `kome/web/app.py` | **Sửa:** hai kết nối, đăng nhập theo tài khoản, cổng quyền | 4, 5, 6 |
| `kome/web/templates/dang_nhap.html` | **Sửa:** thêm ô tên đăng nhập | 4 |
| `kome/web/templates/_nav.html` | **Sửa:** ẩn mục Kho dữ liệu, hiện tên người đang đăng nhập | 4, 5 |
| `kome/web/templates/cam_kho_du_lieu.html` | **Tạo:** trang 403 giải thích | 5 |
| `kome/khach_hang.py` | **Sửa:** tham số lọc `sale` cho `danh_sach` và `can_xu_ly` | 6 |
| `tests/test_khach_hang.py` | **Sửa:** test bộ lọc theo sale | 6 |
| `kome/web/templates/khach_hang.html`, `can_xu_ly.html` | **Sửa:** dải "khách của tôi" + nút xem tất cả | 6 |
| `scripts/tao_nguoi_dung.py` | **Tạo:** quản lý tài khoản bằng dòng lệnh | 7 |
| `tests/test_tao_nguoi_dung.py` | **Tạo:** test cho script trên | 7 |
| `docs/runbook.md`, `CLAUDE.md`, `docs/trien-khai-vercel.md`, `.env.example`, spec đợt 1 | **Sửa:** tài liệu | 8 |

---

## Task 1: Migration 019 — hai bảng mới và quyền của chúng

**Files:**
- Tạo: `db/migrations/019_danh_tinh.sql`
- Sửa: `tests/conftest.py:27` (hằng `GIU_LAI`)
- Test: `tests/test_roles.py` (thêm vào cuối), `tests/test_migrate.py` (không sửa, chỉ chạy lại)

**Interfaces:**
- Sản xuất: bảng `core.dim_salesperson(salesperson_code text PK, ten text)` với
  5 dòng seed; bảng `app.nguoi_dung(id bigserial PK, ten_dang_nhap text UNIQUE,
  mat_khau_hash bytea, mat_khau_salt bytea, salesperson_code text NULL FK,
  duoc_vao_kho_du_lieu boolean NOT NULL DEFAULT false, tao_luc timestamptz)`.
  Task 2 đọc/ghi hai bảng này.

- [ ] **Bước 1: Viết test thất bại** — thêm vào cuối `tests/test_roles.py`

```python
def test_app_doc_duoc_nhat_ky_nap(fresh_conn):
    """kome_app CỐ Ý không ghi được vào core, nhưng việc nó không ĐỌC được
    meta là một khoảng trống chứ không phải chủ ý: trang chủ `/` cần
    meta.ingest_batch cho ô "hôm nay đã có dữ liệu chưa". Thiếu quyền này thì
    trang chủ của bản chạy bằng kome_app_user trả 500."""
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_app', 'meta.ingest_batch', 'SELECT'),
                  has_table_privilege('kome_app', 'meta.ingest_batch', 'INSERT'),
                  has_table_privilege('kome_app', 'meta.ingest_batch', 'UPDATE')"""
    ).fetchone()
    assert r[0] is True, "kome_app không đọc được nhật ký nạp -> trang chủ 500"
    assert r[1] is False and r[2] is False, "kome_app chỉ được ĐỌC meta"


def test_app_ghi_duoc_bang_tai_khoan(fresh_conn):
    """app.nguoi_dung thuộc schema `app` — vai trò kome_app phải đọc-ghi được,
    nếu không thì chính việc đăng nhập (và đổi mật khẩu) không chạy."""
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_app', 'app.nguoi_dung', 'SELECT'),
                  has_table_privilege('kome_app', 'app.nguoi_dung', 'INSERT'),
                  has_table_privilege('kome_app', 'app.nguoi_dung', 'UPDATE')"""
    ).fetchone()
    assert all(r), f"kome_app thiếu quyền trên app.nguoi_dung: {r}"


def test_report_khong_doc_duoc_bam_mat_khau(fresh_conn):
    """kome_report là vai trò cho công cụ báo cáo/BI ngoài ứng dụng chính.
    ALTER DEFAULT PRIVILEGES của 009 cấp cho nó SELECT trên MỌI bảng schema
    `app` — nghĩa là bảng tài khoản vừa tạo cũng tự lọt vào tầm với của nó.
    Một công cụ vẽ biểu đồ doanh thu không có việc gì phải đọc hash mật khẩu
    của nhân viên; 019 thu lại quyền đó."""
    apply_all(fresh_conn, Path("db/migrations"))
    assert fresh_conn.execute(
        "SELECT has_table_privilege('kome_report', 'app.nguoi_dung', 'SELECT')"
    ).fetchone()[0] is False


def test_nam_nguoi_phu_trach_cua_obc_duoc_nap_san(conn):
    """5 担当者 của OBC là dữ liệu THAM CHIẾU do migration nạp — app.nguoi_dung
    trỏ khoá ngoại vào đây. Dùng fixture `conn` (không phải fresh_conn) để test
    này CŨNG canh luôn việc bảng sống sót qua TRUNCATE giữa các test."""
    rows = conn.execute(
        "SELECT salesperson_code, ten FROM core.dim_salesperson ORDER BY 1"
    ).fetchall()
    assert [r[0] for r in rows] == ["0002", "0004", "0102", "0104", "0105"]
    assert dict(rows)["0102"] == "NGUYEN PHUONG DUNG"
```

- [ ] **Bước 2: Chạy test cho chắc là nó ĐỎ**

Chạy: `pytest tests/test_roles.py -v`
Mong đợi: FAIL — `relation "app.nguoi_dung" does not exist` /
`relation "core.dim_salesperson" does not exist`.

- [ ] **Bước 3: Viết migration** — `db/migrations/019_danh_tinh.sql`

```sql
-- 019: danh tính — ai đang đăng nhập, và ai phụ trách khách nào.
--
-- LƯU Ý BẤT BIẾN: ALTER DEFAULT PRIVILEGES của 009/010 KHÔNG có mệnh đề
-- FOR ROLE, nên file này (như mọi migration) PHẢI chạy bằng vai trò
-- `postgres`. Chạy bằng vai trò khác thì hai bảng dưới đây âm thầm không
-- nhận quyền mặc định, và lỗi chỉ lộ ra bằng một `permission denied` nhiều
-- tháng sau.

-- 担当者 của OBC. KHÁI NIỆM NÀY KHÔNG PHẢI "người dùng web": OBC có 5 người
-- phụ trách khách, còn web lên đơn có 7 tài khoản (gồm 2 arubaito chỉ nhập
-- đơn, không phụ trách khách nào). Hai bảng riêng, không bao giờ trộn —
-- xem CLAUDE.md, mục "Bẫy đã biết" số 5.
CREATE TABLE core.dim_salesperson (
    salesperson_code text PRIMARY KEY,
    ten              text NOT NULL
);

-- Số liệu lấy từ đặc tả nền §12.2 (đã ĐO từ dữ liệu thật), không suy đoán mới.
INSERT INTO core.dim_salesperson (salesperson_code, ten) VALUES
    ('0002', '西村 巧'),
    ('0004', 'TRINH CONG MINH'),
    ('0102', 'NGUYEN PHUONG DUNG'),
    ('0104', 'TRAN THI LAN THANH'),
    ('0105', 'HA HUY LONG');

CREATE TABLE app.nguoi_dung (
    id                   bigserial PRIMARY KEY,
    ten_dang_nhap        text UNIQUE NOT NULL,
    -- scrypt + salt RIÊNG từng người (kome/web/nguoi_dung.py). Salt riêng để
    -- hai người vô tình đặt trùng mật khẩu vẫn ra hai hash khác nhau.
    mat_khau_hash        bytea NOT NULL,
    mat_khau_salt        bytea NOT NULL,
    -- NULL = người này không phụ trách khách nào (chủ DN, kế toán, kho).
    -- Khi NULL thì trang khách hàng không lọc gì.
    salesperson_code     text NULL REFERENCES core.dim_salesperson,
    -- Cổng vào màn Kho dữ liệu: nạp file, hoàn tác lô. Mặc định FALSE —
    -- quyền phá huỷ phải được cấp TƯỜNG MINH, không phải thứ ai cũng có vì
    -- người tạo tài khoản quên đặt.
    duoc_vao_kho_du_lieu boolean NOT NULL DEFAULT false,
    tao_luc              timestamptz NOT NULL DEFAULT now()
);

-- kome_app đọc được nhật ký nạp. Vai trò này CỐ Ý không ghi được vào `core`,
-- nhưng việc nó không ĐỌC được `meta` là một khoảng trống chứ không phải chủ
-- ý: trang chủ `/` cần meta.ingest_batch cho ô "hôm nay đã có dữ liệu chưa".
-- Chỉ SELECT — không INSERT/UPDATE/DELETE.
-- (009 đã cấp USAGE trên schema meta cho kome_app; nhắc lại cho đọc được
--  trọn ý ở một chỗ, GRANT là thao tác idempotent.)
GRANT USAGE ON SCHEMA meta TO kome_app;
GRANT SELECT ON meta.ingest_batch TO kome_app;

-- kome_report (công cụ báo cáo/BI ngoài ứng dụng) tự nhận SELECT trên mọi
-- bảng schema `app` theo ALTER DEFAULT PRIVILEGES của 009 — kể cả bảng vừa
-- tạo ở trên. Một công cụ vẽ biểu đồ doanh thu không có việc gì phải đọc
-- hash và salt mật khẩu của nhân viên. Thu lại.
REVOKE SELECT ON app.nguoi_dung FROM kome_report;
```

- [ ] **Bước 4: Giữ bảng tham chiếu khỏi bị TRUNCATE** — sửa `tests/conftest.py`

Sửa khối `GIU_LAI` (dòng 21–27) thành:

```python
# Bảng KHÔNG được dọn giữa hai test:
#  - meta.schema_migration: xoá là mất dấu vết migration -> mỗi test lại chạy
#    lại cả bộ migration (đo được: 3,6 giây/lần, chủ yếu do 004_dim_date.sql
#    chèn ~4.380 dòng qua pooler Tokyo).
#  - core.dim_date: dữ liệu THAM CHIẾU do chính migration nạp, mọi bảng fact
#    đều có khoá ngoại tới nó. Xoá đi là mọi lần nạp đều vỡ khoá ngoại.
#  - core.dim_salesperson: y hệt lý do trên — 5 担当者 của OBC do 019 nạp, và
#    app.nguoi_dung.salesperson_code trỏ khoá ngoại vào đây. Không giữ lại
#    thì TRUNCATE ... CASCADE cuốn theo cả bảng tài khoản, và mọi test tạo
#    người dùng có mã sale đều vỡ khoá ngoại ở test thứ hai trở đi.
GIU_LAI = {"meta.schema_migration", "core.dim_date", "core.dim_salesperson"}
```

- [ ] **Bước 5: Chạy test cho chắc là nó XANH**

Chạy: `pytest tests/test_roles.py tests/test_migrate.py -v`
Mong đợi: PASS toàn bộ (4 test cũ + 4 test mới).

- [ ] **Bước 6: Chạy cả bộ test — migration mới không được làm vỡ gì**

Chạy: `pytest -v`
Mong đợi: PASS toàn bộ.

- [ ] **Bước 7: Commit**

```bash
git add db/migrations/019_danh_tinh.sql tests/conftest.py tests/test_roles.py
git commit -m "feat: migration 019 - dim_salesperson va app.nguoi_dung

kome_app doc duoc meta.ingest_batch (trang chu can, 009 bo sot).
kome_report bi thu SELECT tren app.nguoi_dung - cong cu BI khong co viec
gi doc hash mat khau.
core.dim_salesperson vao GIU_LAI cua conftest: du lieu tham chieu do
migration nap, va app.nguoi_dung tro khoa ngoai vao no.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: `kome/web/nguoi_dung.py` — tài khoản và mật khẩu

**Files:**
- Tạo: `kome/web/nguoi_dung.py`
- Test: `tests/test_nguoi_dung.py`

**Interfaces:**
- Tiêu thụ: hai bảng của Task 1.
- Sản xuất — Task 4, 5, 6, 7 dùng đúng những tên này:
  - `NguoiDung` — dataclass đông cứng: `id: int`, `ten_dang_nhap: str`,
    `salesperson_code: str | None`, `duoc_vao_kho_du_lieu: bool`,
    `ten_sale: str | None`
  - `tao(conn, ten, mat_khau, salesperson_code=None, kho_du_lieu=False) -> int`
  - `kiem_tra(conn, ten, mat_khau) -> NguoiDung | None`
  - `theo_id(conn, id_nguoi) -> NguoiDung | None`
  - `doi_mat_khau(conn, ten, mat_khau_moi) -> bool`
  - `dat_quyen(conn, ten, kho_du_lieu) -> bool`
  - `liet_ke(conn) -> list[NguoiDung]`

Mọi hàm nhận `conn` từ ngoài và **không tự commit** — trừ chỗ nói rõ. Người
gọi commit, đúng nếp `kome/khach_hang.py` và `kome/bao_cao.py`.

- [ ] **Bước 1: Viết test thất bại** — `tests/test_nguoi_dung.py`

```python
"""Tài khoản đăng nhập: băm mật khẩu, xác thực, và quyền vào Kho dữ liệu.

Mọi test ở đây bảo vệ một câu: **mật khẩu không bao giờ nằm ở dạng đọc được
trong CSDL**, và **sai mật khẩu thì không vào được**.
"""
import pytest
import psycopg

from kome.web import nguoi_dung as ND

MK = "mat-khau-cua-an-2026"


def test_tao_roi_dang_nhap_duoc(conn):
    ND.tao(conn, "an", MK, salesperson_code="0104", kho_du_lieu=True)
    conn.commit()
    n = ND.kiem_tra(conn, "an", MK)
    assert n is not None
    assert n.ten_dang_nhap == "an"
    assert n.salesperson_code == "0104"
    assert n.duoc_vao_kho_du_lieu is True
    # Tên người lấy từ core.dim_salesperson — trang khách hàng cần nó để nói
    # rõ "đang lọc theo ai", chứ không phải khoe một mã bốn chữ số.
    assert n.ten_sale == "TRAN THI LAN THANH"


def test_sai_mat_khau_va_sai_ten_deu_tra_ve_none(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert ND.kiem_tra(conn, "an", "doan-bua-mot-cai") is None
    assert ND.kiem_tra(conn, "khong-co-nguoi-nay", MK) is None
    assert ND.kiem_tra(conn, "an", "") is None


def test_mat_khau_khong_bao_gio_nam_trong_csdl_o_dang_doc_duoc(conn):
    """[CRITICAL] Ai đọc được CSDL (bản sao lưu, công cụ BI, một câu SELECT lỡ
    tay) cũng không được đọc ra mật khẩu của nhân viên."""
    ND.tao(conn, "an", MK)
    conn.commit()
    h, s = conn.execute(
        "SELECT mat_khau_hash, mat_khau_salt FROM app.nguoi_dung WHERE ten_dang_nhap='an'"
    ).fetchone()
    assert MK.encode() not in bytes(h)
    assert MK.encode() not in bytes(s)
    assert len(bytes(h)) == ND.DAI_HASH and len(bytes(s)) == ND.DAI_SALT


def test_hai_nguoi_cung_mat_khau_van_ra_hai_hash_khac_nhau(conn):
    """Salt riêng từng người. Không có nó thì nhìn bảng là biết ngay ai đang
    dùng chung mật khẩu với ai — và bẻ được một cái là bẻ được cả nhóm."""
    ND.tao(conn, "an", MK)
    ND.tao(conn, "binh", MK)
    conn.commit()
    rows = conn.execute("SELECT mat_khau_hash FROM app.nguoi_dung ORDER BY id").fetchall()
    assert rows[0][0] != rows[1][0]


def test_doi_mat_khau_thi_mat_khau_cu_het_dung_duoc(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert ND.doi_mat_khau(conn, "an", "mat-khau-moi-cua-an") is True
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK) is None
    assert ND.kiem_tra(conn, "an", "mat-khau-moi-cua-an") is not None
    assert ND.doi_mat_khau(conn, "khong-co-ai", "abc") is False


def test_dat_quyen_bat_va_tat_duoc(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is False   # mặc định
    assert ND.dat_quyen(conn, "an", True) is True
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is True
    ND.dat_quyen(conn, "an", False)
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is False
    assert ND.dat_quyen(conn, "khong-co-ai", True) is False


def test_quyen_vao_kho_du_lieu_mac_dinh_la_khong(conn):
    """[IMPORTANT] Màn Kho dữ liệu có nút xoá được cả tháng doanh thu. Quyền
    đó phải được cấp tường minh, không phải thứ ai cũng có vì người tạo tài
    khoản quên đặt."""
    ND.tao(conn, "an", MK)
    conn.commit()
    assert conn.execute(
        "SELECT duoc_vao_kho_du_lieu FROM app.nguoi_dung WHERE ten_dang_nhap='an'"
    ).fetchone()[0] is False


def test_trung_ten_dang_nhap_bi_tu_choi(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    with pytest.raises(psycopg.errors.UniqueViolation):
        ND.tao(conn, "an", "mat-khau-khac-han")
    conn.rollback()


def test_ma_sale_khong_co_that_bi_tu_choi(conn):
    """Khoá ngoại tới core.dim_salesperson: gõ nhầm mã sale phải nổ NGAY lúc
    tạo tài khoản, không phải lặng lẽ tạo một người lọc ra 0 khách."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        ND.tao(conn, "an", MK, salesperson_code="9999")
    conn.rollback()


def test_theo_id_tra_ve_dung_nguoi_va_none_khi_da_xoa(conn):
    """theo_id là thứ middleware gọi MỖI LƯỢT: vé còn hạn nhưng tài khoản đã
    bị xoá thì phải trả None, để người đó bị đá về trang đăng nhập ngay."""
    ma = ND.tao(conn, "an", MK, kho_du_lieu=True)
    conn.commit()
    n = ND.theo_id(conn, ma)
    assert n is not None and n.ten_dang_nhap == "an" and n.duoc_vao_kho_du_lieu
    conn.execute("DELETE FROM app.nguoi_dung WHERE id = %s", (ma,))
    conn.commit()
    assert ND.theo_id(conn, ma) is None
    assert ND.theo_id(conn, 999_999) is None


def test_liet_ke_khong_tra_ve_hash_hay_salt(conn):
    """Lệnh liệt kê của scripts/tao_nguoi_dung.py in thẳng thứ hàm này trả
    về. Không có hash/salt trong dataclass thì không có đường nào in nhầm."""
    ND.tao(conn, "an", MK, salesperson_code="0104")
    ND.tao(conn, "binh", MK, kho_du_lieu=True)
    conn.commit()
    ds = ND.liet_ke(conn)
    assert [n.ten_dang_nhap for n in ds] == ["an", "binh"]
    assert not any(hasattr(n, t) for n in ds for t in ("mat_khau_hash", "mat_khau_salt"))
```

- [ ] **Bước 2: Chạy test cho chắc là nó ĐỎ**

Chạy: `pytest tests/test_nguoi_dung.py -v`
Mong đợi: FAIL — `ModuleNotFoundError: No module named 'kome.web.nguoi_dung'`.

- [ ] **Bước 3: Viết module** — `kome/web/nguoi_dung.py`

```python
"""Tài khoản đăng nhập: băm mật khẩu, xác thực, và quyền vào Kho dữ liệu.

Module này KHÔNG biết gì về HTTP — không FastAPI, không cookie, không vé.
Nó chỉ nói chuyện với `app.nguoi_dung` (migration 019). Vé đăng nhập nằm ở
kome/web/bao_mat.py, và ranh giới đó là cố ý: một chỗ giữ "mật khẩu này có
đúng không", một chỗ giữ "cái cookie này có phải do mình ký không".

Băm bằng `hashlib.scrypt` của THƯ VIỆN CHUẨN — không thêm gói nào (R2: công
ty không có nhân sự IT, mỗi gói phụ thuộc là một thứ nữa có thể hỏng khi cài
lại). scrypt cố ý chậm và tốn bộ nhớ: đo trên chính máy này là ~50 ms một lần
băm, tức một người đăng nhập không thấy chậm, còn ai lấy được bản sao CSDL thì
dò mật khẩu chậm hơn hàng triệu lần so với SHA-256 trần.

Không tự commit: người gọi quyết định ranh giới giao dịch.
"""
import hashlib
import hmac
import os
from dataclasses import dataclass

# Tham số scrypt. n=2^14, r=8, p=1 tốn ~16 MB bộ nhớ mỗi lần băm — nằm gọn
# trong giới hạn mặc định của OpenSSL, đã chạy thật trên máy này.
# ĐỔI BỘ SỐ NÀY LÀ MỌI MẬT KHẨU CŨ HẾT XÁC THỰC ĐƯỢC. Muốn đổi thì phải đặt
# lại mật khẩu cho tất cả mọi người (scripts/tao_nguoi_dung.py doi-mat-khau).
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
DAI_HASH = 32
DAI_SALT = 16

_COT = """id, ten_dang_nhap, salesperson_code, duoc_vao_kho_du_lieu"""

# Truy vấn dùng chung cho kiem_tra/theo_id/liet_ke. LEFT JOIN chứ không JOIN:
# người không phụ trách khách nào (chủ DN, kế toán) có salesperson_code NULL
# và vẫn phải đăng nhập được.
_CHON = f"""SELECT n.id, n.ten_dang_nhap, n.salesperson_code,
                   n.duoc_vao_kho_du_lieu, s.ten
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
    ten_sale: str | None


def _nguoi(r) -> NguoiDung:
    return NguoiDung(id=r[0], ten_dang_nhap=r[1], salesperson_code=r[2],
                     duoc_vao_kho_du_lieu=r[3], ten_sale=r[4])


def bam(mat_khau: str, salt: bytes) -> bytes:
    return hashlib.scrypt(mat_khau.encode("utf-8"), salt=salt,
                          n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=DAI_HASH)


def tao(conn, ten: str, mat_khau: str, salesperson_code: str | None = None,
        kho_du_lieu: bool = False) -> int:
    """Tạo tài khoản, trả về id. Ném UniqueViolation nếu tên đã có,
    ForeignKeyViolation nếu mã sale không có trong core.dim_salesperson."""
    salt = os.urandom(DAI_SALT)
    return conn.execute(
        """INSERT INTO app.nguoi_dung
             (ten_dang_nhap, mat_khau_hash, mat_khau_salt, salesperson_code,
              duoc_vao_kho_du_lieu)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (ten, bam(mat_khau, salt), salt, salesperson_code or None, kho_du_lieu),
    ).fetchone()[0]


def kiem_tra(conn, ten: str, mat_khau: str) -> NguoiDung | None:
    """Tên + mật khẩu có đúng không. None nếu sai bất cứ thứ gì."""
    r = conn.execute(
        "SELECT mat_khau_hash, mat_khau_salt FROM app.nguoi_dung WHERE ten_dang_nhap = %s",
        (ten,)).fetchone()
    if r is None:
        # Vẫn băm một lần với salt vứt đi rồi mới trả None. Trả thẳng None ở
        # đây thì "tên không tồn tại" trả lời trong ~0 ms còn "sai mật khẩu"
        # mất ~50 ms — chênh lệch đó đủ để người ngoài dò ra DANH SÁCH TÊN
        # ĐĂNG NHẬP của công ty mà không cần biết mật khẩu nào.
        bam(mat_khau, b"\x00" * DAI_SALT)
        return None
    if not hmac.compare_digest(bytes(r[0]), bam(mat_khau, bytes(r[1]))):
        return None
    return _nguoi(conn.execute(
        f"{_CHON} WHERE n.ten_dang_nhap = %s", (ten,)).fetchone())


def theo_id(conn, id_nguoi: int) -> NguoiDung | None:
    """Tra người theo id trong vé. None nếu tài khoản đã bị xoá — middleware
    dựa vào đó để một vé còn hạn của người đã xoá không vào được nữa."""
    r = conn.execute(f"{_CHON} WHERE n.id = %s", (id_nguoi,)).fetchone()
    return _nguoi(r) if r else None


def doi_mat_khau(conn, ten: str, mat_khau_moi: str) -> bool:
    """False nếu không có tài khoản tên đó. Salt cũng đổi theo — mật khẩu mới
    thì mọi thứ dẫn tới nó đều mới."""
    salt = os.urandom(DAI_SALT)
    return conn.execute(
        """UPDATE app.nguoi_dung SET mat_khau_hash = %s, mat_khau_salt = %s
           WHERE ten_dang_nhap = %s""",
        (bam(mat_khau_moi, salt), salt, ten)).rowcount == 1


def dat_quyen(conn, ten: str, kho_du_lieu: bool) -> bool:
    """False nếu không có tài khoản tên đó."""
    return conn.execute(
        "UPDATE app.nguoi_dung SET duoc_vao_kho_du_lieu = %s WHERE ten_dang_nhap = %s",
        (kho_du_lieu, ten)).rowcount == 1


def liet_ke(conn) -> list[NguoiDung]:
    return [_nguoi(r) for r in conn.execute(
        f"{_CHON} ORDER BY n.ten_dang_nhap").fetchall()]
```

- [ ] **Bước 4: Chạy test cho chắc là nó XANH**

Chạy: `pytest tests/test_nguoi_dung.py -v`
Mong đợi: PASS (11 test).

- [ ] **Bước 5: Commit**

```bash
git add kome/web/nguoi_dung.py tests/test_nguoi_dung.py
git commit -m "feat: kome/web/nguoi_dung.py - tai khoan va mat khau scrypt

Salt rieng tung nguoi. Ten khong ton tai van bam mot lan roi moi tra None,
de thoi gian tra loi khong to ra danh sach ten dang nhap.
NguoiDung co y khong mang hash/salt: khong co trong doi tuong thi khong co
duong nao lot len trang.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: Vé đăng nhập theo từng người

**Files:**
- Sửa: `kome/web/bao_mat.py` (**chỉ THÊM**, chưa xoá gì)
- Test: `tests/test_bao_mat.py` (thêm một khối mới)

**Interfaces:**
- Sản xuất — Task 4 dùng:
  - `bi_mat_phien() -> str | None` — đọc `KOME_SESSION_SECRET`
  - `tao_ve_cho(id_nguoi: int, bi_mat: str, bay_gio: float | None = None) -> str`
  - `doc_ve(ve: str | None, bi_mat: str, bay_gio: float | None = None) -> int | None`
  - `kiem_cau_hinh_phien(bi_mat: str | None, cong_khai: bool) -> None`

**Task này CHỈ THÊM, không xoá `mat_khau`/`tao_ve`/`ve_hop_le`/`kiem_cau_hinh`.**
`kome/web/app.py:113` đang gọi `bao_mat.mat_khau()`; xoá ở đây là cả bộ test đỏ
giữa hai task. Task 4 xoá chúng cùng lúc với việc thay chỗ dùng.

- [ ] **Bước 1: Viết test thất bại** — thêm vào `tests/test_bao_mat.py`, ngay
      sau khối `# ---- Vé đăng nhập ----`

```python
# ---- Vé theo từng người (đợt 3) ---------------------------------------

BI_MAT = "bi-mat-phien-du-dai-2026"


def test_ve_mang_dung_id_nguoi_dang_nhap():
    assert bao_mat.doc_ve(bao_mat.tao_ve_cho(7, BI_MAT), BI_MAT) == 7


def test_doi_id_trong_ve_khong_hoa_than_duoc_thanh_nguoi_khac():
    """[CRITICAL] Đây là chỗ dễ sai nhất của cả đợt. Nếu chữ ký chỉ phủ phần
    HẠN mà không phủ ID, thì sửa một con số trong cookie là thành người khác —
    ví dụ thành đúng người có quyền vào Kho dữ liệu, nơi có nút xoá cả tháng
    doanh thu. Chữ ký PHẢI phủ cả hai."""
    ve = bao_mat.tao_ve_cho(7, BI_MAT)
    ma, het, chu_ky = ve.split(".")
    assert bao_mat.doc_ve(f"1.{het}.{chu_ky}", BI_MAT) is None
    assert bao_mat.doc_ve(f"999.{het}.{chu_ky}", BI_MAT) is None


def test_ve_het_han_thi_vo_hieu_du_chu_ky_dung():
    ve = bao_mat.tao_ve_cho(7, BI_MAT, bay_gio=1_000_000)
    assert bao_mat.doc_ve(ve, BI_MAT, bay_gio=1_000_000 + bao_mat.HAN_PHIEN_GIAY - 1) == 7
    assert bao_mat.doc_ve(ve, BI_MAT, bay_gio=1_000_000 + bao_mat.HAN_PHIEN_GIAY + 1) is None


def test_doi_bi_mat_phien_huy_moi_ve_dang_luu_hanh():
    """[IMPORTANT] Không có kho phiên ở máy chủ, nên đổi KOME_SESSION_SECRET
    là cách DUY NHẤT đăng xuất tất cả mọi người cùng lúc khi nghi rò rỉ."""
    assert bao_mat.doc_ve(bao_mat.tao_ve_cho(7, BI_MAT), BI_MAT + "-moi") is None


def test_ve_meo_mo_bi_tu_choi():
    ma, het, chu_ky = bao_mat.tao_ve_cho(7, BI_MAT).split(".")
    assert bao_mat.doc_ve(None, BI_MAT) is None
    assert bao_mat.doc_ve("", BI_MAT) is None
    assert bao_mat.doc_ve("khong-co-dau-cham", BI_MAT) is None
    assert bao_mat.doc_ve(f"{het}.{chu_ky}", BI_MAT) is None          # thiếu id
    assert bao_mat.doc_ve(f"7.{het}.{chu_ky}.thua", BI_MAT) is None   # thừa đoạn
    assert bao_mat.doc_ve(f"7.khong-phai-so.{chu_ky}", BI_MAT) is None
    assert bao_mat.doc_ve(f"khong-phai-so.{het}.{chu_ky}", BI_MAT) is None


def test_hai_nguoi_khac_nhau_khong_bao_gio_dung_chung_ve():
    a = bao_mat.tao_ve_cho(7, BI_MAT, bay_gio=1_000_000)
    b = bao_mat.tao_ve_cho(8, BI_MAT, bay_gio=1_000_000)
    assert a != b


def test_cong_khai_ma_thieu_bi_mat_phien_thi_app_chet_ngay():
    """[CRITICAL] Bỏ mật khẩu chung là bỏ luôn chốt an toàn cũ. Chốt mới phải
    cùng hình dạng: công khai mà không có khoá ký thì KHÔNG dựng app."""
    with pytest.raises(bao_mat.CauHinhSai, match="KOME_SESSION_SECRET"):
        bao_mat.kiem_cau_hinh_phien(None, cong_khai=True)
    with pytest.raises(bao_mat.CauHinhSai, match="ký tự"):
        bao_mat.kiem_cau_hinh_phien("ngan", cong_khai=True)
    # Máy trong công ty: không có khoá cũng không sao, không có cổng đăng nhập.
    bao_mat.kiem_cau_hinh_phien(None, cong_khai=False)


def test_bi_mat_phien_doc_tu_bien_moi_truong(monkeypatch):
    monkeypatch.delenv("KOME_SESSION_SECRET", raising=False)
    assert bao_mat.bi_mat_phien() is None
    monkeypatch.setenv("KOME_SESSION_SECRET", "   ")
    assert bao_mat.bi_mat_phien() is None      # khoảng trắng = chưa đặt
    monkeypatch.setenv("KOME_SESSION_SECRET", f"  {BI_MAT}  ")
    assert bao_mat.bi_mat_phien() == BI_MAT
```

- [ ] **Bước 2: Chạy test cho chắc là nó ĐỎ**

Chạy: `pytest tests/test_bao_mat.py -v -k "ve_mang_dung_id or doi_id_trong_ve or bi_mat_phien"`
Mong đợi: FAIL — `AttributeError: module 'kome.web.bao_mat' has no attribute 'tao_ve_cho'`.

- [ ] **Bước 3: Thêm cơ chế mới vào `kome/web/bao_mat.py`**

Thêm vào cuối file (giữ nguyên mọi thứ đang có):

```python
# ---- Vé theo từng người (đợt 3) ---------------------------------------
# Cơ chế cũ ở trên suy khoá ký TỪ CHÍNH mật khẩu chung, nên đổi mật khẩu là
# mọi vé chết ngay. Cách đó không dùng được khi có nhiều tài khoản: đổi mật
# khẩu MỘT người không được phép làm bốn người còn lại bị đăng xuất.
#
# Khoá ký giờ là của HỆ THỐNG (KOME_SESSION_SECRET), không phải mật khẩu của
# ai cả. Thu hồi quyền vì thế tách làm hai mức:
#   * đổi KOME_SESSION_SECRET -> đăng xuất TẤT CẢ (dùng khi nghi rò rỉ)
#   * đổi mật khẩu một người  -> chỉ họ, ở lượt đăng nhập kế tiếp
# Vé đang có hiệu lực của người bị đổi mật khẩu sống tới hết hạn (12 giờ).
# Vô hiệu hoá tức thì cần kho phiên, mà kho phiên phá luật Vercel.
#
# Riêng quyền vào Kho dữ liệu KHÔNG nằm trong vé mà tra CSDL mỗi lượt gọi —
# xem kome/web/app.py. Đó là màn có nút xoá, thu hồi phải ăn ngay.


def bi_mat_phien() -> str | None:
    """Khoá ký vé, hoặc None nếu không đặt (máy trong công ty, không có cổng)."""
    return os.environ.get("KOME_SESSION_SECRET", "").strip() or None


def kiem_cau_hinh_phien(bi_mat: str | None, cong_khai: bool) -> None:
    """Gọi lúc dựng app. Ném CauHinhSai nếu cấu hình không an toàn.

    Cùng hình dạng với kiem_cau_hinh() của cơ chế mật khẩu chung mà nó thay
    thế: một bản chạy công khai KHÔNG CÓ CỔNG NÀO là hỏng theo cách tệ nhất,
    nên phải chết lúc khởi động, nơi người triển khai đọc được nhật ký Vercel.

    CỐ Ý không kiểm "đã có tài khoản nào trong CSDL chưa": làm vậy là buộc
    việc dựng app phụ thuộc CSDL, và một CSDL chậm sẽ thành app không khởi
    động được.
    """
    if bi_mat is None:
        if cong_khai:
            raise CauHinhSai(
                "Trang đang chạy trên hạ tầng công khai nhưng chưa đặt biến môi "
                "trường KOME_SESSION_SECRET.\n"
                "Vào Vercel → Settings → Environment Variables, thêm "
                "KOME_SESSION_SECRET là một chuỗi ngẫu nhiên dài ít nhất "
                f"{DAI_TOI_THIEU} ký tự, rồi triển khai lại."
            )
        return
    if len(bi_mat) < DAI_TOI_THIEU:
        raise CauHinhSai(
            f"KOME_SESSION_SECRET chỉ dài {len(bi_mat)} ký tự — phải từ "
            f"{DAI_TOI_THIEU} trở lên.\n"
            "Đây là khoá ký vé đăng nhập: đoán ra nó là tự ký được vé cho bất "
            "kỳ tài khoản nào, không cần biết mật khẩu của ai."
        )


def _ky(noi_dung: str, bi_mat: str) -> str:
    return hmac.new(bi_mat.encode("utf-8"), noi_dung.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def tao_ve_cho(id_nguoi: int, bi_mat: str, bay_gio: float | None = None) -> str:
    """Vé `<id>.<hạn>.<chữ ký>`, hết hạn sau HAN_PHIEN_GIAY."""
    het = int((bay_gio if bay_gio is not None else time.time()) + HAN_PHIEN_GIAY)
    than = f"{id_nguoi}.{het}"
    return f"{than}.{_ky(than, bi_mat)}"


def doc_ve(ve: str | None, bi_mat: str, bay_gio: float | None = None) -> int | None:
    """id người trong vé, hoặc None nếu vé sai chữ ký / hết hạn / méo mó.

    CHỮ KÝ PHỦ CẢ id LẪN HẠN. Ký riêng phần hạn thôi thì sửa một con số trong
    cookie là hoá thân thành người khác mà chữ ký vẫn đúng — kể cả thành người
    có quyền bấm nút xoá dữ liệu.

    Giữ nguyên thứ tự "so chữ ký TRƯỚC khi đọc hạn" của cơ chế cũ:
    hmac.compare_digest chạy hết thời gian như nhau dù sai ở ký tự nào, nên
    không đo được chữ ký đúng là gì.
    """
    if not ve:
        return None
    phan = ve.split(".")
    if len(phan) != 3:
        return None
    ma, het, chu_ky = phan
    if not hmac.compare_digest(chu_ky, _ky(f"{ma}.{het}", bi_mat)):
        return None
    try:
        if (bay_gio if bay_gio is not None else time.time()) >= int(het):
            return None
        return int(ma)
    except ValueError:
        return None
```

- [ ] **Bước 4: Chạy test cho chắc là nó XANH**

Chạy: `pytest tests/test_bao_mat.py -v`
Mong đợi: PASS toàn bộ — cả test cũ (cơ chế chung vẫn còn nguyên) lẫn 8 test mới.

- [ ] **Bước 5: Chạy cả bộ test**

Chạy: `pytest -v`
Mong đợi: PASS toàn bộ.

- [ ] **Bước 6: Commit**

```bash
git add kome/web/bao_mat.py tests/test_bao_mat.py
git commit -m "feat: ve dang nhap theo tung nguoi, ky bang KOME_SESSION_SECRET

Ve la <id>.<han>.<HMAC(id.han)> - chu ky phu CA id lan han, neu khong thi
sua mot con so trong cookie la hoa than thanh nguoi khac.
Khoa ky tach hoi mat khau: doi mat khau mot nguoi khong duoc lam bon nguoi
con lai bi dang xuat.
Co che mat khau chung VAN CON o day - task 4 xoa cung luc voi cho dung.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Thay cổng đăng nhập chung bằng tài khoản riêng

**Files:**
- Sửa: `kome/web/app.py:99-201` (chữ ký `create_app`, hai kết nối, middleware,
  ba route đăng nhập), và mọi route đổi sang kết nối đọc
- Sửa: `kome/web/bao_mat.py` (xoá cơ chế mật khẩu chung)
- Sửa: `kome/web/templates/dang_nhap.html`, `kome/web/templates/_nav.html`
- Sửa: `tests/conftest.py` (fixture autouse gỡ biến môi trường)
- Test: `tests/test_bao_mat.py` (viết lại fixture `khach` và các test cổng)

**Interfaces:**
- Tiêu thụ: `bao_mat.bi_mat_phien`, `bao_mat.tao_ve_cho`, `bao_mat.doc_ve`,
  `bao_mat.kiem_cau_hinh_phien` (Task 3); `nguoi_dung.kiem_tra`,
  `nguoi_dung.theo_id`, `NguoiDung` (Task 2).
- Sản xuất — Task 5, 6 dùng:
  - `create_app(db_url=None, db_url_app=None)`
  - `request.state.nguoi` — `NguoiDung | None` ở mọi route
  - biến template: `nguoi` (NguoiDung | None), `co_dang_nhap` (bool),
    `hien_kho` (bool)
  - `open_app_conn()` — kết nối vai trò `kome_app` (mọi trang chỉ đọc)

- [ ] **Bước 1: Viết test thất bại** — viết lại phần cổng của `tests/test_bao_mat.py`

Thay **toàn bộ** fixture `khach` (dòng 19–38) bằng:

```python
MK = "mat-khau-cua-an-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"


@pytest.fixture
def khach(monkeypatch, test_db_url, conn):
    """Trình duyệt KHÔNG tự đi theo chuyển hướng — phải thấy tận mắt mã 303.

    `bi_mat=None` => KHÔNG có cổng đăng nhập (máy trong công ty để trống
    KOME_SESSION_SECRET). Đó cũng là mặc định của mọi test khác trong repo,
    xem fixture autouse `_khong_cong_dang_nhap` ở conftest.py.
    """
    from kome.web import nguoi_dung as ND

    def _tao(bi_mat: str | None = BI_MAT, vercel: bool = False,
             tai_khoan: bool = True, kho_du_lieu: bool = True,
             sale: str | None = None):
        monkeypatch.delenv("KOME_CHI_DOC", raising=False)
        if bi_mat is None:
            monkeypatch.delenv("KOME_SESSION_SECRET", raising=False)
        else:
            monkeypatch.setenv("KOME_SESSION_SECRET", bi_mat)
        if vercel:
            monkeypatch.setenv("VERCEL", "1")
        else:
            monkeypatch.delenv("VERCEL", raising=False)
        if tai_khoan:
            ND.tao(conn, "an", MK, salesperson_code=sale, kho_du_lieu=kho_du_lieu)
            conn.commit()
        # vercel=True => base_url https: bản công khai LUÔN chạy HTTPS, và
        # cookie phiên ở đó mang cờ Secure nên trình duyệt không gửi lại qua
        # HTTP. Giả lập bằng http:// sẽ dựng nên một thế giới không có thật,
        # nơi đăng nhập "thành công" rồi trang sau lại đòi đăng nhập.
        return TestClient(create_app(db_url=test_db_url), follow_redirects=False,
                          base_url="https://testserver" if vercel else "http://testserver")
    return _tao


def _vao(c, ten: str = "an", mat_khau: str = MK):
    """Đăng nhập, trả về phản hồi của POST /dang-nhap."""
    return c.post("/dang-nhap", data={"ten": ten, "mat_khau": mat_khau})
```

Sửa các test cổng có sẵn (dòng 86–214) — nội dung mới:

```python
# ---- Cấu hình phải an toàn ngay từ lúc khởi động ------------------------

def test_tren_vercel_ma_khong_co_khoa_ky_thi_app_chet_ngay(khach):
    """[CRITICAL] Không có cổng + công khai = số liệu công ty mở cho cả
    Internet. Phải nổ lúc dựng app, nơi người triển khai đọc được nhật ký."""
    with pytest.raises(bao_mat.CauHinhSai, match="KOME_SESSION_SECRET"):
        khach(bi_mat=None, vercel=True)


def test_khoa_ky_qua_ngan_bi_tu_choi(khach):
    with pytest.raises(bao_mat.CauHinhSai, match="ký tự"):
        khach(bi_mat="ngan")


def test_chay_o_may_ca_nhan_khong_bat_buoc_dang_nhap(khach):
    """Máy trong công ty chạy ở 127.0.0.1 — bắt đăng nhập ở đó chỉ làm chậm
    công việc hằng ngày mà không chặn được ai. Để TRỐNG KOME_SESSION_SECRET
    là không có cổng, y như để trống KOME_MAT_KHAU trước đây.

    ĐÁNH ĐỔI PHẢI BIẾT: không có cổng thì cũng KHÔNG CÓ phân quyền — ai mở
    được trang cũng bấm được nút Hoàn tác. Xem docs/runbook.md."""
    r = khach(bi_mat=None, tai_khoan=False).get("/kho-du-lieu")
    assert r.status_code == 200


# ---- Cổng chặn trên mọi trang ------------------------------------------

@pytest.mark.parametrize("duong_dan", ["/", "/kho-du-lieu", "/khach-hang"])
def test_chua_dang_nhap_thi_moi_trang_deu_bi_chan(khach, duong_dan):
    r = khach().get(duong_dan)
    assert r.status_code == 303
    assert r.headers["location"] == "/dang-nhap"
    assert "¥" not in r.text and "得意先" not in r.text


def test_dang_nhap_dung_thi_xem_duoc_va_sai_thi_khong(khach):
    c = khach()
    r = _vao(c, mat_khau="doan-bua-mot-cai")
    assert r.status_code == 401
    assert bao_mat.TEN_COOKIE not in c.cookies

    r = _vao(c, ten="khong-co-nguoi-nay")
    assert r.status_code == 401
    assert bao_mat.TEN_COOKIE not in c.cookies

    r = _vao(c)
    assert r.status_code == 303
    assert c.get("/kho-du-lieu").status_code == 200


def test_dang_nhap_xong_ve_trang_chu_chu_khong_phai_kho_du_lieu(khach):
    """[IMPORTANT] Không phải ai cũng vào được Kho dữ liệu (đợt 3). Đẩy mọi
    người vào đó sau khi đăng nhập nghĩa là một sale vừa gõ đúng mật khẩu
    xong thấy ngay một trang 403 — lời chào tệ nhất có thể."""
    c = khach(kho_du_lieu=False)
    assert _vao(c).headers["location"] == "/"


def test_dang_nhap_xong_quay_lai_dung_trang_dinh_xem(khach):
    c = khach()
    c.get("/khach-hang")                        # bị đẩy về /dang-nhap
    assert _vao(c).headers["location"] == "/khach-hang"


def test_doi_mat_khau_mot_nguoi_khong_lam_nguoi_khac_bi_dang_xuat(khach, conn):
    """[CRITICAL] Đây ĐÚNG LÀ cái lỗi của cơ chế cũ mà đợt 3 sinh ra để sửa:
    khoá ký suy từ chính mật khẩu chung, nên đổi mật khẩu là cả công ty bị
    đăng xuất. Giờ khoá ký là của hệ thống, tách hẳn khỏi mật khẩu của ai."""
    from kome.web import nguoi_dung as ND
    c = khach()
    ND.tao(conn, "binh", "mat-khau-cua-binh-2026")
    conn.commit()
    _vao(c)
    assert c.get("/").status_code == 200

    ND.doi_mat_khau(conn, "binh", "mat-khau-moi-cua-binh")
    conn.commit()
    assert c.get("/").status_code == 200, "đổi mật khẩu người khác làm mình văng ra"


def test_xoa_tai_khoan_thi_ve_con_han_cung_het_vao_duoc(khach, conn):
    """[IMPORTANT] Người nghỉ việc phải bị chặn NGAY, không phải chờ 12 giờ
    cho vé cũ hết hạn. Vé không trạng thái nên chữ ký vẫn đúng — thứ chặn họ
    là việc middleware tra CSDL mỗi lượt và không thấy tài khoản nữa."""
    c = khach()
    _vao(c)
    assert c.get("/").status_code == 200
    conn.execute("DELETE FROM app.nguoi_dung WHERE ten_dang_nhap = 'an'")
    conn.commit()
    r = c.get("/")
    assert r.status_code == 303 and r.headers["location"] == "/dang-nhap"


def test_doi_khoa_ky_thi_dang_xuat_tat_ca(khach, monkeypatch, test_db_url):
    """[IMPORTANT] Nghi rò rỉ thì phải có một cái công tắc đăng xuất TẤT CẢ."""
    c = khach()
    _vao(c)
    assert c.get("/").status_code == 200
    monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT + "-doi-roi")
    c2 = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
    c2.cookies.update(c.cookies)          # cùng cái vé, app đã đổi khoá ký
    assert c2.get("/").status_code == 303


def test_cookie_phien_khong_doc_duoc_bang_javascript(khach):
    dat = _vao(khach()).headers["set-cookie"]
    assert "httponly" in dat.lower()
    assert "samesite=lax" in dat.lower()


def test_tren_hang_tang_cong_khai_cookie_luon_co_co_secure(khach):
    """[IMPORTANT] Không có cờ Secure thì trình duyệt chịu gửi vé đăng nhập
    qua HTTP thường, nơi ai chung mạng Wi-Fi cũng đọc được."""
    assert "secure" in _vao(khach(vercel=True)).headers["set-cookie"].lower()


def test_o_may_ca_nhan_khong_gan_secure(khach):
    assert "secure" not in _vao(khach()).headers["set-cookie"].lower()


def test_thoat_thi_het_xem_duoc(khach):
    c = khach()
    _vao(c)
    assert c.get("/kho-du-lieu").status_code == 200
    c.post("/dang-xuat")
    assert c.get("/kho-du-lieu").status_code == 303


def test_mat_khau_khong_bao_gio_hien_tren_trang(khach):
    """Kể cả trang đăng nhập sai — người đứng sau lưng cũng đọc được màn hình."""
    c = khach()
    for r in (c.get("/dang-nhap"), _vao(c, mat_khau="sai")):
        assert MK not in r.text
```

`test_static_khong_bi_chan_boi_cong_dang_nhap` giữ nguyên (fixture mới đã lo).
Trong hai test chế độ chỉ-đọc, thay `c.post("/dang-nhap", data={"mat_khau": MK})`
bằng `_vao(c)`.

Sửa `test_khong_lam_ban_dap_chuyen_huong` — đích mặc định đổi:

```python
@pytest.mark.parametrize("tiep,mong", [
    ("/khach-hang", "/khach-hang"),
    ("https://site-gia.example", "/"),   # địa chỉ tuyệt đối
    ("//site-gia.example", "/"),         # cũng là tuyệt đối
    (None, "/"),
])
def test_khong_lam_ban_dap_chuyen_huong(tiep, mong):
    """Trang đăng nhập của công ty không được đẩy người dùng sang site lạ.

    Đích mặc định là "/" chứ KHÔNG còn là /kho-du-lieu (đợt 3): không phải ai
    cũng vào được màn đó nữa."""
    assert bao_mat.duong_dan_an_toan(tiep) == mong
```

Và xoá bốn test của cơ chế cũ đã không còn hàm để gọi:
`test_ve_hop_le_chi_voi_dung_mat_khau`, `test_ve_het_han_sau_han_phien`,
`test_ve_gia_mao_bi_tu_choi`, `test_doi_mat_khau_huy_moi_ve_dang_luu_hanh` —
bốn bất biến chúng canh đã có test tương đương ở khối "Vé theo từng người"
(Task 3), không mất cái nào.

- [ ] **Bước 2: Chạy test cho chắc là nó ĐỎ**

Chạy: `pytest tests/test_bao_mat.py -v`
Mong đợi: FAIL — `TypeError: nhan_dang_nhap() got an unexpected keyword
argument 'ten'` / 401 ở mọi lần đăng nhập.

- [ ] **Bước 3: Chặn biến môi trường rò sang test khác** — `tests/conftest.py`

Thêm ngay sau fixture `test_db_url`:

```python
@pytest.fixture(autouse=True)
def _khong_cong_dang_nhap(monkeypatch):
    """[QUAN TRỌNG] Mặc định MỌI test dựng app KHÔNG có cổng đăng nhập.

    conftest gọi nap_env() nên pytest ĐỌC .env — và từ đợt 3, .env của máy
    trong công ty có KOME_SESSION_SECRET (docs/runbook.md bảo đặt). Không có
    fixture này thì mọi test dựng app tự mọc cổng đăng nhập và ~30 test đỏ
    hàng loạt với 303 /dang-nhap, vì một lý do chẳng liên quan gì tới thứ
    chúng kiểm — mà chỉ đỏ trên máy có .env, không đỏ trong CI.

    DATABASE_URL_APP cũng phải gỡ: test luôn truyền db_url tường minh, nhưng
    để biến đó sót lại là để một đường cho test đọc nhầm CSDL THẬT.

    Test nào CẦN cổng thì tự đặt lại — xem fixture `khach` ở
    tests/test_bao_mat.py.
    """
    monkeypatch.delenv("KOME_SESSION_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_URL_APP", raising=False)
```

- [ ] **Bước 4: Viết lại cổng trong `kome/web/app.py`**

Đổi chữ ký và phần đầu `create_app` (dòng 99–120):

```python
def create_app(db_url: str | None = None, db_url_app: str | None = None) -> FastAPI:
    """db_url=None => lấy DATABASE_URL. Test LUÔN truyền DATABASE_URL_TEST."""
    app = FastAPI(title="KOME — dữ liệu")
    app.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).parent / "static")),
        name="static",
    )
    archive_dir = Path(os.environ.get("ARCHIVE_DIR", "./raw_archive"))
    open_conn = lambda: connect(db_url)
    chi_doc = _chi_doc()

    # Hai kết nối, hai vai trò CSDL (đặc tả đợt 3 §6.3):
    #   open_conn     -> DATABASE_URL     (kome_ingest_user): NẠP và HOÀN TÁC,
    #                                      chỉ màn Kho dữ liệu dùng
    #   open_app_conn -> DATABASE_URL_APP (kome_app_user): mọi trang còn lại,
    #                                      vai trò KHÔNG ghi được vào `core`
    # Lỡ tay viết một câu UPDATE core.… ở một trang đọc thì chính CSDL từ
    # chối — lớp an toàn ở tầng quyền, không phụ thuộc review code có bắt
    # được hay không.
    #
    # db_url truyền TƯỜNG MINH (test luôn truyền) thì kết nối app đi theo
    # đúng CSDL đó. Không có dòng này thì test chạy trên CSDL thử nghiệm
    # nhưng lại đọc app.nguoi_dung của CSDL THẬT trên máy có DATABASE_URL_APP.
    if db_url_app is None:
        db_url_app = db_url if db_url is not None else os.environ.get("DATABASE_URL_APP")
    if db_url_app is None:
        # Cảnh báo chứ không chết: vai trò CSDL là lớp phòng thủ thứ hai, còn
        # cổng đăng nhập mới là thứ chặn người lạ. Giết cả trang vì thiếu một
        # lớp phòng thủ thứ hai là đổi một rủi ro lấy một sự cố chắc chắn.
        print("[KOME] CẢNH BÁO: chưa đặt DATABASE_URL_APP — các trang chỉ đọc "
              "đang chạy bằng vai trò nạp dữ liệu, tức có quyền ghi vào core. "
              "Xem docs/runbook.md, mục 'Hai kết nối CSDL'.")
    open_app_conn = lambda: connect(db_url_app)

    bi_mat = bao_mat.bi_mat_phien()
    # Ném CauHinhSai ngay lúc dựng app, trước khi phục vụ dòng nào.
    bao_mat.kiem_cau_hinh_phien(bi_mat, cong_khai=bao_mat.tren_mang())

    # Biến mà MỌI trang đều cần để vẽ đúng thanh điều hướng. Gom vào một chỗ
    # để không trang nào bị sót: sót `chi_doc` thì trang đó vẫn mời người ta
    # bấm "Nạp dữ liệu" — một liên kết dẫn thẳng tới 403 trên bản công khai.
    chung = {"chi_doc": chi_doc, "co_dang_nhap": bool(bi_mat)}
```

Thêm `from kome.web import nguoi_dung as ND` vào khối nhập ở đầu file (cạnh
`from kome.web import bao_mat`). Module này chỉ dùng `hashlib`/`hmac`/`psycopg`
— **không** kéo theo pandas, nên không phá bất biến "app.py không nhập nặng".

Đổi `_ve` (dòng 122–123):

```python
    def _ve(request: Request, ten: str, ctx: dict, **kw) -> HTMLResponse:
        # `nguoi` gắn bởi middleware chan_cua. getattr có mặc định vì KHÔNG
        # PHẢI lúc nào cũng có middleware: máy trong công ty để trống
        # KOME_SESSION_SECRET thì không có cổng, và /dang-nhap thì chạy
        # TRƯỚC khi ai kịp là ai.
        nguoi = getattr(request.state, "nguoi", None)
        return TEMPLATES.TemplateResponse(
            request, ten, {**ctx, **chung, "nguoi": nguoi}, **kw)
```

Thay toàn bộ khối `if mk:` (dòng 146–201) bằng:

```python
    if bi_mat:
        @app.middleware("http")
        async def chan_cua(request: Request, call_next):
            # Miễn trừ /static/ CÓ CHỦ Ý — đây là một lỗ thủng trong cổng bảo
            # mật, không phải sót. /static/ chỉ chứa kome.css và font: tài sản
            # thiết kế thuần tuý, không một byte dữ liệu kinh doanh nào đi qua
            # đường này. Thiếu dòng này thì CHÍNH trang đăng nhập — màn hình
            # ĐẦU TIÊN của bản Vercel — bị 303 mất cả CSS lẫn font. Có test
            # canh: tests/test_bao_mat.py::
            # test_static_khong_bi_chan_boi_cong_dang_nhap.
            if (request.url.path == "/dang-nhap"
                    or request.url.path.startswith("/static/")):
                return await call_next(request)

            # Vé chỉ mang ID. Mọi thứ khác (còn tài khoản không, quyền gì) tra
            # CSDL MỖI LƯỢT — vé sống 12 giờ, mà người nghỉ việc thì phải bị
            # chặn ngay hôm nay, không phải 12 giờ nữa.
            ma = bao_mat.doc_ve(request.cookies.get(bao_mat.TEN_COOKIE), bi_mat)
            nguoi = None
            if ma is not None:
                with open_app_conn() as c:
                    nguoi = ND.theo_id(c, ma)
            if nguoi is None:
                tiep = request.url.path
                if request.url.query:
                    tiep += "?" + request.url.query
                resp = RedirectResponse("/dang-nhap", status_code=303)
                # Nhớ nơi người ta định đến để đăng nhập xong quay lại đúng
                # chỗ, nhưng chỉ nhớ trong cookie tạm — không đưa vào địa chỉ,
                # vì địa chỉ thì lộ ra lịch sử duyệt web và nhật ký máy chủ.
                resp.set_cookie("kome_tiep", tiep, max_age=600, httponly=True,
                                samesite="lax", secure=_chi_gui_qua_https(request))
                return resp

            request.state.nguoi = nguoi
            return await call_next(request)

        @app.get("/dang-nhap", response_class=HTMLResponse)
        def form_dang_nhap(request: Request):
            return _ve(request, "dang_nhap.html", {"trang": None, "sai": False})

        @app.post("/dang-nhap")
        def nhan_dang_nhap(request: Request, ten: str = Form(""),
                           mat_khau: str = Form("")):
            with open_app_conn() as c:
                nguoi = ND.kiem_tra(c, ten.strip(), mat_khau)
            if nguoi is None:
                # MỘT thông báo duy nhất cho cả "sai tên" lẫn "sai mật khẩu":
                # nói rõ cái nào sai là xác nhận giúp người ngoài rằng tên đó
                # CÓ TỒN TẠI trong công ty.
                return _ve(request, "dang_nhap.html",
                           {"trang": None, "sai": True}, status_code=401)
            resp = RedirectResponse(
                bao_mat.duong_dan_an_toan(request.cookies.get("kome_tiep")),
                status_code=303)
            resp.set_cookie(
                bao_mat.TEN_COOKIE, bao_mat.tao_ve_cho(nguoi.id, bi_mat),
                max_age=bao_mat.HAN_PHIEN_GIAY, httponly=True, samesite="lax",
                secure=_chi_gui_qua_https(request))
            resp.delete_cookie("kome_tiep")
            return resp

        @app.post("/dang-xuat")
        def dang_xuat():
            resp = RedirectResponse("/dang-nhap", status_code=303)
            resp.delete_cookie(bao_mat.TEN_COOKIE)
            return resp
```

Đổi kết nối của bốn route chỉ đọc — `tong_quan`, `ds_khach`, `ho_so_khach`,
`can_xu_ly`, `bao_cao`: đổi `with open_conn() as conn:` thành
`with open_app_conn() as conn:`. **Giữ nguyên `open_conn`** ở `kho_du_lieu`,
`upload`, `undo` — ba chỗ thật sự ghi và xoá.

Đổi đích mặc định trong `kome/web/bao_mat.py::duong_dan_an_toan` (dòng 113):

```python
    return "/"
```

và sửa docstring của nó, thêm: *"Đích mặc định là trang chủ chứ không phải
/kho-du-lieu: từ đợt 3 không phải ai cũng vào được màn đó."*

- [ ] **Bước 5: Xoá cơ chế mật khẩu chung khỏi `kome/web/bao_mat.py`**

Xoá: `mat_khau()`, `kiem_cau_hinh()`, `_khoa()`, `tao_ve()`, `ve_hop_le()`,
`dung_mat_khau()` (dòng 37–39, 53–70, 73–100). Viết lại docstring đầu file:

```python
"""Cổng đăng nhập: vé không trạng thái, ký bằng khoá của hệ thống.

Mỗi người một tài khoản riêng (app.nguoi_dung, migration 019) — trước đợt 3
cả công ty dùng chung một mật khẩu `KOME_MAT_KHAU`, và hệ quả là không ai
biết ai vừa bấm nút Hoàn tác, còn một người nghỉ việc thì phải đổi mật khẩu
của tất cả mọi người.

Vé đăng nhập là cookie tự chứng thực: `<id>.<hạn>.<chữ ký HMAC-SHA256>`.
Không có kho phiên ở máy chủ — điều kiện bắt buộc để chạy được trên Vercel,
nơi mỗi lần gọi có thể rơi vào một tiến trình khác và bộ nhớ không dùng chung.

Việc "mật khẩu này có đúng không" nằm ở kome/web/nguoi_dung.py. File này chỉ
giữ "cái cookie này có phải do mình ký không".
"""
```

- [ ] **Bước 6: Sửa `kome/web/templates/dang_nhap.html`**

Thêm ô tên đăng nhập trước ô mật khẩu; đổi nhãn và chú thích:

```html
  <h1>🔒 Dữ liệu KOME</h1>
  {% if sai %}<div class="sai">Tên đăng nhập hoặc mật khẩu không đúng.</div>{% endif %}
  <form method="post" action="/dang-nhap">
    <label for="ten">Tên đăng nhập</label>
    <input id="ten" type="text" name="ten" required autofocus
           autocomplete="username">
    <label for="mk">Mật khẩu</label>
    <input id="mk" type="password" name="mat_khau" required
           autocomplete="current-password">
    <button type="submit">Vào xem</button>
  </form>
  <p class="nho">Mỗi người một tài khoản riêng. Quên mật khẩu thì nhờ người
     quản trị đặt lại — không gửi mật khẩu của mình cho ai.</p>
```

Thêm vào khối `<style>` để ô text có cùng kiểu dáng ô mật khẩu:

```css
 input[type=text],
 input[type=password]{width:100%;box-sizing:border-box;font:inherit;padding:.6rem;
      border-radius:8px;border:1px solid var(--vien);background:var(--nen);color:var(--chu)}
 label{display:block;margin-top:.75rem}
```

(xoá dòng `input[type=password]{…}` cũ)

- [ ] **Bước 7: Sửa `kome/web/templates/_nav.html`** — đổi khối cuối (dòng 37–39)

```html
  {% if co_dang_nhap %}
  <div class="thoat">
    {% if nguoi %}<p class="nhom">{{ nguoi.ten_sale or nguoi.ten_dang_nhap }}</p>{% endif %}
    <form method="post" action="/dang-xuat"><button type="submit">Đăng xuất</button></form>
  </div>
  {% endif %}
```

- [ ] **Bước 8: Chạy test cho chắc là nó XANH**

Chạy: `pytest tests/test_bao_mat.py -v`
Mong đợi: PASS toàn bộ.

- [ ] **Bước 9: Chạy cả bộ test**

Chạy: `pytest -v`
Mong đợi: PASS toàn bộ. Nếu `tests/test_giao_dien.py` đỏ ở chỗ nhắc
`KOME_MAT_KHAU` trong docstring `test_ban_chi_doc_van_hien_muc_kho_du_lieu`,
sửa docstring đó cho đúng cơ chế mới (`KOME_SESSION_SECRET`) — chỉ chữ, không
đổi test.

- [ ] **Bước 10: Commit**

```bash
git add kome/web/app.py kome/web/bao_mat.py kome/web/templates/dang_nhap.html \
        kome/web/templates/_nav.html tests/conftest.py tests/test_bao_mat.py \
        tests/test_giao_dien.py
git commit -m "feat: dang nhap rieng tung nguoi, bo han KOME_MAT_KHAU

Middleware doc ve lay id roi tra app.nguoi_dung MOI LUOT: xoa tai khoan la
chan duoc ngay, khong cho 12 gio cho ve het han.
Hai ket noi CSDL: trang chi doc di qua DATABASE_URL_APP (vai tro kome_app,
khong ghi duoc vao core), chi man Kho du lieu dung DATABASE_URL.
Dich mac dinh sau dang nhap doi tu /kho-du-lieu sang / - khong phai ai cung
vao duoc man do nua.
conftest go KOME_SESSION_SECRET khoi moi test: .env tu dot 3 co bien do, de
nguyen thi ~30 test do vi mot ly do khong lien quan.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Chặn màn Kho dữ liệu theo quyền

**Files:**
- Sửa: `kome/web/app.py` (middleware `chan_cua`, `_ve`)
- Tạo: `kome/web/templates/cam_kho_du_lieu.html`
- Sửa: `kome/web/templates/_nav.html`
- Test: `tests/test_bao_mat.py` (khối mới ở cuối)

**Interfaces:**
- Tiêu thụ: `request.state.nguoi` (Task 4), `NguoiDung.duoc_vao_kho_du_lieu`.
- Sản xuất: biến template `hien_kho: bool`.

- [ ] **Bước 1: Viết test thất bại** — thêm vào cuối `tests/test_bao_mat.py`

```python
# ---- Quyền vào màn Kho dữ liệu (đợt 3) ---------------------------------

def test_khong_co_quyen_thi_moi_duong_vao_kho_du_lieu_deu_403(khach):
    """[CRITICAL] Màn Kho dữ liệu là màn có nút xoá. Đợt 2a đã phát hiện bấm
    nhầm lô đối soát sẽ xoá CẢ MỘT THÁNG doanh thu — trước đợt 3, bất kỳ ai
    biết mật khẩu chung đều bấm được nút đó.

    Chặn cả POST: ẩn cái nút đi mà vẫn nhận POST thì người gõ thẳng địa chỉ
    (hoặc một trang lạ tự gửi form) vẫn xoá được dữ liệu."""
    c = khach(kho_du_lieu=False)
    _vao(c)
    r = c.get("/kho-du-lieu")
    assert r.status_code == 403
    assert "在庫一覧" not in r.text, "trang 403 vẫn lộ nội dung màn Kho dữ liệu"
    assert c.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", b"x")}).status_code == 403
    assert c.post("/undo/1").status_code == 403


def test_ba_dia_chi_cu_cung_bi_chan(khach):
    """/nap, /health, /phu-du-lieu chỉ 301 sang /kho-du-lieu, nhưng để hở
    chúng thì người không có quyền vẫn dò được cấu trúc màn bị cấm."""
    c = khach(kho_du_lieu=False)
    _vao(c)
    for d in ("/nap", "/health", "/phu-du-lieu"):
        assert c.get(d).status_code == 403, d


def test_trang_403_noi_ro_vi_sao_chu_khong_chuyen_huong_im_lang(khach):
    """Người gõ thẳng địa chỉ cần biết vì sao mình không vào được, không phải
    tự hỏi trang có hỏng không."""
    c = khach(kho_du_lieu=False)
    _vao(c)
    t = c.get("/kho-du-lieu").text
    assert "không có quyền" in t
    assert 'href="/"' in t          # còn đường quay ra


def test_co_quyen_thi_van_vao_binh_thuong(khach):
    c = khach(kho_du_lieu=True)
    _vao(c)
    assert c.get("/kho-du-lieu").status_code == 200


def test_bo_co_quyen_thi_luot_goi_KE_TIEP_da_bi_chan(khach, conn):
    """[CRITICAL] Thu hồi quyền phá huỷ mà phải đợi 12 giờ cho vé hết hạn là
    không thu hồi được. Cờ quyền CỐ Ý không nằm trong vé, chính vì chuyện
    này — nó được tra lại ở mỗi lượt gọi."""
    from kome.web import nguoi_dung as ND
    c = khach(kho_du_lieu=True)
    _vao(c)
    assert c.get("/kho-du-lieu").status_code == 200
    ND.dat_quyen(conn, "an", False)
    conn.commit()
    assert c.get("/kho-du-lieu").status_code == 403


def test_khong_co_quyen_thi_sidebar_khong_moi_bam_vao_kho_du_lieu(khach):
    """Một liên kết luôn dẫn tới trang từ chối thì tệ hơn là không có."""
    c = khach(kho_du_lieu=False)
    _vao(c)
    t = c.get("/khach-hang").text
    assert 'href="/kho-du-lieu"' not in t
    assert 'href="/khach-hang"' in t        # các mục khác vẫn còn


def test_co_quyen_thi_sidebar_van_co_muc_kho_du_lieu(khach):
    c = khach(kho_du_lieu=True)
    _vao(c)
    assert 'href="/kho-du-lieu"' in c.get("/khach-hang").text


def test_khong_co_cong_dang_nhap_thi_khong_chan_ai(khach):
    """Máy trong công ty để trống KOME_SESSION_SECRET: không có đăng nhập thì
    cũng không có khái niệm quyền — mọi thứ mở như trước đợt 3."""
    c = khach(bi_mat=None, tai_khoan=False)
    assert c.get("/kho-du-lieu").status_code == 200
    assert 'href="/kho-du-lieu"' in c.get("/khach-hang").text
```

- [ ] **Bước 2: Chạy test cho chắc là nó ĐỎ**

Chạy: `pytest tests/test_bao_mat.py -v -k "quyen or 403 or sidebar"`
Mong đợi: FAIL — nhận 200 ở chỗ mong 403.

- [ ] **Bước 3: Thêm cổng quyền vào `kome/web/app.py`**

Thêm hằng và hàm cạnh `SO_NGAY_SOAT` (mức ngoài cùng của module):

```python
# Mọi đường dẫn thuộc màn Kho dữ liệu — màn DUY NHẤT có nút xoá dữ liệu.
# Ba địa chỉ cũ (/nap, /health, /phu-du-lieu) nằm trong danh sách dù chúng chỉ
# 301: để hở chúng là để người không có quyền dò ra cấu trúc màn bị cấm.
DUONG_KHO_DU_LIEU = ("/kho-du-lieu", "/upload", "/undo",
                     "/nap", "/health", "/phu-du-lieu")


def _thuoc_kho_du_lieu(duong: str) -> bool:
    """`/undo/12` cũng thuộc màn này, nên so bằng tiền tố có ranh giới `/`
    chứ không so bằng nhau — nhưng `/khach-hang` KHÔNG được dính vào
    `/kho-du-lieu` chỉ vì cùng vài ký tự đầu."""
    return any(duong == d or duong.startswith(d + "/") for d in DUONG_KHO_DU_LIEU)
```

Trong `chan_cua`, thêm ngay **sau** `request.state.nguoi = nguoi`:

```python
            request.state.nguoi = nguoi
            if not nguoi.duoc_vao_kho_du_lieu and _thuoc_kho_du_lieu(request.url.path):
                # 403 kèm trang giải thích, KHÔNG chuyển hướng im lặng: người
                # gõ thẳng địa chỉ cần biết vì sao mình không vào được, không
                # phải tự hỏi trang có hỏng không.
                return _ve(request, "cam_kho_du_lieu.html",
                           {"trang": None}, status_code=403)
            return await call_next(request)
```

Sửa `_ve` để tính `hien_kho`:

```python
    def _ve(request: Request, ten: str, ctx: dict, **kw) -> HTMLResponse:
        nguoi = getattr(request.state, "nguoi", None)
        # `nguoi is None` = không có cổng đăng nhập (máy trong công ty để
        # trống KOME_SESSION_SECRET) -> mọi thứ mở, y như trước đợt 3.
        hien_kho = nguoi is None or nguoi.duoc_vao_kho_du_lieu
        return TEMPLATES.TemplateResponse(
            request, ten, {**ctx, **chung, "nguoi": nguoi, "hien_kho": hien_kho}, **kw)
```

- [ ] **Bước 4: Tạo `kome/web/templates/cam_kho_du_lieu.html`**

```html
<!-- kome/web/templates/cam_kho_du_lieu.html
     403 cho người không có cờ duoc_vao_kho_du_lieu. Cố ý KHÔNG chuyển hướng
     im lặng: người gõ thẳng địa chỉ (hoặc bấm một dấu trang cũ) cần biết vì
     sao mình không vào được, không phải tự hỏi trang có hỏng không.

     Khác hẳn chi_doc.html: ở đó là "máy chủ này không làm nổi việc đó", ở
     đây là "bạn không được cấp quyền làm việc đó". Hai câu khác nhau, và
     gộp chung sẽ nói sai một trong hai. -->
<!doctype html><html lang="vi"><meta charset="utf-8">
<title>KOME — không có quyền</title>
{% include "_chung.html" %}
<style> h1{font-size:1.3rem} </style>
{% include "_nav.html" %}
<div class="ngay-thieu">
<h1>🔐 Bạn không có quyền vào Kho dữ liệu</h1>
<p>Màn <strong>Kho dữ liệu</strong> là nơi nạp file từ OBC và
<strong>hoàn tác</strong> một lần nạp — thao tác xoá được cả một tháng doanh
thu khỏi kho nếu bấm nhầm lô. Vì vậy nó chỉ mở cho người phụ trách nạp dữ liệu
và chủ doanh nghiệp.</p>
<p>Cần vào đây để làm việc? Nhờ người quản trị cấp quyền cho tài khoản
{% if nguoi %}<strong>{{ nguoi.ten_dang_nhap }}</strong>{% endif %}.</p>
<p>Mọi số liệu bán hàng, khách hàng và báo cáo vẫn xem được bình thường:
<a href="/">Tổng quan</a> · <a href="/khach-hang">Khách hàng</a> ·
<a href="/bao-cao">Báo cáo doanh thu</a>.</p>
</div>
</html>
</main>
```

- [ ] **Bước 5: Ẩn mục Kho dữ liệu trong `_nav.html`**

Đổi khối `HỆ THỐNG` (dòng 33–34):

```html
    {% if hien_kho %}
    <p class="nhom">HỆ THỐNG</p>
    <a href="/kho-du-lieu"{% if trang == 'kho-du-lieu' %} class="dang-xem" aria-current="page"{% endif %}>Kho dữ liệu</a>
    {% endif %}
```

Và sửa ghi chú Jinja đầu file (dòng 13–15) cho khỏi nói sai:

```
   Mục "Kho dữ liệu" KHÔNG bọc `{% if not chi_doc %}`: màn đó hiện được ở cả
   hai bản chạy, chỉ khác là bản chỉ-đọc tự ẩn khối nạp và khối hoàn tác bên
   trong chính nó (xem kho_du_lieu.html).

   Nó CÓ bọc `{% if hien_kho %}` — chuyện khác hẳn: từ đợt 3, chỉ người được
   cấp cờ `duoc_vao_kho_du_lieu` mới vào được màn đó (đường dẫn trả 403).
   Mời người ta bấm vào một thứ sẽ từ chối họ thì tệ hơn là không hiện.
   `hien_kho` do kome/web/app.py::_ve tính, mặc định TRUE khi không có cổng
   đăng nhập (máy trong công ty).
```

- [ ] **Bước 6: Chạy test cho chắc là nó XANH**

Chạy: `pytest tests/test_bao_mat.py tests/test_giao_dien.py -v`
Mong đợi: PASS toàn bộ (kể cả
`test_moi_template_dung_nav_deu_dong_main` cho template mới).

- [ ] **Bước 7: Chạy cả bộ test**

Chạy: `pytest -v`
Mong đợi: PASS toàn bộ.

- [ ] **Bước 8: Commit**

```bash
git add kome/web/app.py kome/web/templates/cam_kho_du_lieu.html \
        kome/web/templates/_nav.html tests/test_bao_mat.py
git commit -m "feat: chan man Kho du lieu theo co duoc_vao_kho_du_lieu

403 co trang giai thich, khong chuyen huong im lang. Chan ca POST /upload
va POST /undo: an cai nut di ma van nhan POST thi go thang dia chi van xoa
duoc du lieu.
Co quyen khong nam trong ve ma tra CSDL moi luot, nen bo co la luot goi ke
tiep da bi chan - khong cho 12 gio.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: Mặc định "khách của tôi"

**Files:**
- Sửa: `kome/khach_hang.py` (`TrangKhach`, `danh_sach`, `can_xu_ly`)
- Sửa: `kome/web/app.py` (route `ds_khach`, `can_xu_ly`)
- Sửa: `kome/web/templates/khach_hang.html`, `kome/web/templates/can_xu_ly.html`
- Test: `tests/test_khach_hang.py`, `tests/test_bao_mat.py`

**Interfaces:**
- Tiêu thụ: `NguoiDung.salesperson_code`, `NguoiDung.ten_sale` (Task 2);
  `request.state.nguoi` (Task 4).
- Sản xuất: `danh_sach(conn, tim, loc, sap, trang, sale=None)`,
  `can_xu_ly(conn, gioi_han=100, sale=None)`; `TrangKhach` thêm ba trường
  `sale: str | None`, `ten_sale: str | None`, `tong_tat_ca: int`.

**Đây KHÔNG phải hàng rào bảo mật** (đặc tả §5, §6.5): năm sale không cần giấu
nhau. Bộ lọc là **mặc định tiện dụng**, một cú bấm là xem được tất cả. Không
có kiểm quyền nào ở task này, và điều đó là cố ý.

- [ ] **Bước 1: Viết test thất bại** — thêm vào cuối `tests/test_khach_hang.py`

```python
# ---- Mặc định "khách của tôi" (đợt 3) ----------------------------------

def _hai_sale(conn, batch):
    """Hai khách của 0104, một khách của 0102."""
    for ma, ten, sale in (("K0104A", "Quán A", "0104"),
                          ("K0104B", "Quán B", "0104"),
                          ("K0102C", "Quán C", "0102")):
        _ho_so_khach(conn, batch, ma, ten, salesperson_code=sale)
        _mua_deu(conn, batch, ma, nhip=14, so_lan=5)
    _neo(conn, batch)


def test_loc_theo_sale_chi_hien_khach_cua_nguoi_do(conn, batch):
    _hai_sale(conn, batch)
    t = KH.danh_sach(conn, sale="0104")
    assert {k.ma for k in t.khach} == {"K0104A", "K0104B"}
    assert t.tong == 2
    assert t.sale == "0104"


def test_khong_truyen_sale_thi_hien_tat_ca(conn, batch):
    _hai_sale(conn, batch)
    t = KH.danh_sach(conn)
    assert {k.ma for k in t.khach} == {"K0104A", "K0104B", "K0102C"}
    assert t.sale is None


def test_bo_dem_trang_thai_di_theo_bo_loc_sale(conn, batch):
    """Đang lọc "khách của tôi" mà bộ đếm vẫn khoe con số toàn công ty thì
    bấm vào một mục xong ra danh sách ngắn hơn hẳn con số vừa đọc."""
    _hai_sale(conn, batch)
    assert sum(KH.danh_sach(conn, sale="0104").dem_trang_thai.values()) == 2
    assert sum(KH.danh_sach(conn).dem_trang_thai.values()) == 3


def test_tong_tat_ca_luon_dem_toan_bo_du_dang_loc(conn, batch):
    """Số trên nút "Xem tất cả khách (N)" phải là số THẬT lấy từ truy vấn,
    không phải con số của bộ lọc đang bật."""
    _hai_sale(conn, batch)
    assert KH.danh_sach(conn, sale="0104").tong_tat_ca == 3


def test_loc_sale_ket_hop_duoc_voi_tim_kiem_va_loc_trang_thai(conn, batch):
    _hai_sale(conn, batch)
    t = KH.danh_sach(conn, tim="Quán A", sale="0104")
    assert [k.ma for k in t.khach] == ["K0104A"]
    assert KH.danh_sach(conn, tim="Quán C", sale="0104").tong == 0


def test_can_xu_ly_loc_duoc_theo_sale(conn, batch):
    """Khách im lặng của 0102 không được lẫn vào danh sách gọi lại của 0104."""
    for ma, sale in (("R0104", "0104"), ("R0102", "0102")):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}", salesperson_code=sale)
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=90)
    _neo(conn, batch)
    assert {k.ma for k in KH.can_xu_ly(conn, sale="0104")} == {"R0104"}
    assert {k.ma for k in KH.can_xu_ly(conn)} == {"R0104", "R0102"}
```

Và thêm vào cuối `tests/test_bao_mat.py`:

```python
# ---- Mặc định "khách của tôi" (đợt 3) ----------------------------------

def test_dang_nhap_co_ma_sale_thi_trang_khach_mac_dinh_loc_theo_minh(khach):
    """Mặc định TIỆN DỤNG, không phải hàng rào: trang nói rõ đang lọc theo ai
    và có một liên kết hiện rõ để xem tất cả."""
    c = khach(sale="0104")
    _vao(c)
    t = c.get("/khach-hang").text
    assert "TRAN THI LAN THANH" in t
    assert "tat_ca=1" in t, "không có đường thoát khỏi bộ lọc"


def test_bam_xem_tat_ca_thi_bo_loc(khach):
    c = khach(sale="0104")
    _vao(c)
    r = c.get("/khach-hang?tat_ca=1")
    assert r.status_code == 200
    assert "Đang xem khách của" not in r.text


def test_nguoi_khong_phu_trach_khach_nao_thay_toan_bo_ngay_tu_dau(khach):
    """[IMPORTANT] Chủ DN, kế toán, kho có salesperson_code NULL. Lọc theo
    NULL thì họ mở lên thấy danh sách rỗng và tưởng hệ thống mất dữ liệu."""
    c = khach(sale=None)
    _vao(c)
    assert "Đang xem khách của" not in c.get("/khach-hang").text
```

- [ ] **Bước 2: Chạy test cho chắc là nó ĐỎ**

Chạy: `pytest tests/test_khach_hang.py -v -k "sale or tat_ca"`
Mong đợi: FAIL — `TypeError: danh_sach() got an unexpected keyword argument 'sale'`.

- [ ] **Bước 3: Thêm bộ lọc vào `kome/khach_hang.py`**

Sửa dataclass `TrangKhach`:

```python
@dataclass
class TrangKhach:
    khach: list[Khach]
    tong: int
    trang: int
    so_trang: int
    tim: str
    loc: str
    sap: str
    dem_trang_thai: dict[str, int]
    # Mã sale đang lọc (None = đang xem tất cả), tên người đó để trang nói rõ
    # "đang lọc theo ai", và tổng số khách TOÀN CÔNG TY cho nút "Xem tất cả".
    sale: str | None = None
    ten_sale: str | None = None
    tong_tat_ca: int = 0
```

Sửa `danh_sach`:

```python
def danh_sach(conn, tim: str = "", loc: str = "", sap: str = "doanh_thu",
              trang: int = 1, sale: str | None = None,
              ten_sale: str | None = None) -> TrangKhach:
    """Danh sách khách, có tìm kiếm và lọc theo trạng thái.

    `sale` là MẶC ĐỊNH TIỆN DỤNG, không phải hàng rào bảo mật: công ty năm
    người, ai cũng biết khách của ai, và trang luôn có một liên kết bỏ lọc.
    Không có kiểm quyền nào ở đây, và đó là cố ý — xem đặc tả đợt 3 §5.
    """
    dieu_kien, tham_so = [], []
    if tim.strip():
        # Tìm theo tên, mã, điện thoại hoặc địa chỉ cùng lúc — nhân viên không
        # nhớ mình đang có mảnh thông tin nào trong tay.
        dieu_kien.append("""(ten ILIKE %s OR customer_code ILIKE %s
                             OR phone ILIKE %s OR address ILIKE %s
                             OR city ILIKE %s)""")
        tham_so += [f"%{tim.strip()}%"] * 5
    if loc in TRANG_THAI:
        dieu_kien.append("trang_thai = %s")
        tham_so.append(loc)
    if sale:
        dieu_kien.append("salesperson_code = %s")
        tham_so.append(sale)
    where = ("WHERE " + " AND ".join(dieu_kien)) if dieu_kien else ""

    tong = conn.execute(
        f"SELECT count(*) FROM mart.khach_360 {where}", tham_so).fetchone()[0]

    thu_tu = SAP_XEP.get(sap, SAP_XEP["doanh_thu"])
    trang = max(1, trang)
    rows = conn.execute(
        f"""SELECT {_COT} FROM mart.khach_360 {where}
            ORDER BY {thu_tu} LIMIT %s OFFSET %s""",
        tham_so + [MOI_TRANG, (trang - 1) * MOI_TRANG]).fetchall()

    # Số lượng từng trạng thái KHÔNG theo bộ lọc trạng thái đang bật — nếu
    # không thì bấm vào "Cần gọi lại" xong các con số khác về 0 hết. Nhưng
    # CÓ theo bộ lọc sale: đang xem khách của mình mà bộ đếm khoe con số toàn
    # công ty thì bấm vào một mục xong ra danh sách ngắn hơn hẳn số vừa đọc.
    dem_dk = "WHERE salesperson_code = %s" if sale else ""
    dem = dict(conn.execute(
        f"SELECT trang_thai, count(*) FROM mart.khach_360 {dem_dk} GROUP BY 1",
        [sale] if sale else []).fetchall())

    # Số THẬT cho liên kết "Xem tất cả khách (N)". Viết cứng một con số ở
    # template là để nó sai đúng vào ngày công ty có thêm khách.
    tong_tat_ca = conn.execute("SELECT count(*) FROM mart.khach_360").fetchone()[0]

    return TrangKhach(
        khach=[_khach(r) for r in rows], tong=tong, trang=trang,
        so_trang=max(1, -(-tong // MOI_TRANG)), tim=tim, loc=loc, sap=sap,
        dem_trang_thai=dem, sale=sale, ten_sale=ten_sale, tong_tat_ca=tong_tat_ca)
```

Sửa `can_xu_ly`:

```python
def can_xu_ly(conn, gioi_han: int = 100, sale: str | None = None) -> list[Khach]:
    """Danh sách việc cần làm: khách đang rời đi, xếp theo tiền đang mất.

    Xếp theo DOANH THU chứ không theo mức độ im lặng: gọi lại khách ¥5 triệu
    im 3 lần nhịp thì đáng hơn khách ¥50.000 im 10 lần nhịp, dù con số thứ hai
    trông đáng báo động hơn.

    `sale`: mặc định tiện dụng, như danh_sach() — không phải hàng rào.
    """
    dieu_kien = "AND salesperson_code = %s" if sale else ""
    tham_so = ([sale] if sale else []) + [gioi_han]
    return [_khach(r) for r in conn.execute(
        f"""SELECT {_COT} FROM mart.khach_360
            WHERE trang_thai IN ('canh_bao', 'da_roi_bo') {dieu_kien}
            ORDER BY doanh_thu_thuan DESC NULLS LAST LIMIT %s""",
        tham_so).fetchall()]
```

- [ ] **Bước 4: Nối bộ lọc vào hai route** — `kome/web/app.py`

```python
    def _sale_dang_loc(request: Request, tat_ca: int) -> tuple[str | None, str | None]:
        """(mã sale, tên người) đang lọc, hoặc (None, None) nếu xem tất cả.

        Không có người đăng nhập (máy trong công ty không bật cổng) hoặc người
        đó không phụ trách khách nào (chủ DN, kế toán, kho) => KHÔNG lọc gì.
        Lọc theo NULL thì họ mở lên thấy danh sách rỗng và tưởng mất dữ liệu.
        """
        nguoi = getattr(request.state, "nguoi", None)
        if tat_ca or nguoi is None or not nguoi.salesperson_code:
            return None, None
        return nguoi.salesperson_code, nguoi.ten_sale or nguoi.ten_dang_nhap

    @app.get("/khach-hang", response_class=HTMLResponse)
    def ds_khach(request: Request, tim: str = "", loc: str = "",
                 sap: str = "doanh_thu", trang: int = 1, tat_ca: int = 0):
        try:
            sale, ten_sale = _sale_dang_loc(request, tat_ca)
            with open_app_conn() as conn:
                t = KH.danh_sach(conn, tim=tim, loc=loc, sap=sap, trang=trang,
                                 sale=sale, ten_sale=ten_sale)
            return _ve(request, "khach_hang.html",
                       {"t": t, "trang_thai": KH.TRANG_THAI, "trang": "khach",
                        "tat_ca": bool(tat_ca)})
        except Exception as e:
            return _loi(request, "mở danh sách khách hàng", e, chung)

    @app.get("/can-xu-ly", response_class=HTMLResponse)
    def can_xu_ly(request: Request, tat_ca: int = 0):
        try:
            sale, ten_sale = _sale_dang_loc(request, tat_ca)
            with open_app_conn() as conn:
                ds = KH.can_xu_ly(conn, sale=sale)
            return _ve(request, "can_xu_ly.html",
                       {"ds": ds, "trang": "can-xu-ly", "sale": sale,
                        "ten_sale": ten_sale})
        except Exception as e:
            return _loi(request, "mở danh sách cần xử lý", e, chung)
```

- [ ] **Bước 5: Sửa `kome/web/templates/khach_hang.html`**

Ngay sau `<h1>Khách hàng</h1>`, thêm:

```html
{# Mặc định tiện dụng, KHÔNG phải hàng rào: năm sale không cần giấu nhau
   (đặc tả đợt 3 §5). Liên kết bỏ lọc phải hiện rõ, và con số trên nó lấy
   từ truy vấn chứ không viết cứng. #}
{% if t.sale %}
<p class="ghi-chu">Đang xem khách của <strong>{{ t.ten_sale }}</strong> ({{ "{:,}".format(t.tong) }} khách).
  <a href="/khach-hang?tat_ca=1">Xem tất cả {{ "{:,}".format(t.tong_tat_ca) }} khách →</a></p>
{% endif %}
```

Giữ tham số `tat_ca` qua mọi liên kết trong trang. Ngay dưới `<h1>` (trước
khối trên), thêm:

```html
{% set giu = "&tat_ca=1" if tat_ca else "" %}
```

rồi thêm `{{ giu }}` vào cuối mọi `href="/khach-hang?..."` đang có trong file
(ô tìm kiếm, dải bộ lọc trạng thái, các tiêu đề cột sắp xếp, hai nút phân
trang). Với `<form class="o-tim">`, thêm một ô ẩn:

```html
  {% if tat_ca %}<input type="hidden" name="tat_ca" value="1">{% endif %}
```

- [ ] **Bước 6: Sửa `kome/web/templates/can_xu_ly.html`**

Ngay sau `<h1>Cần xử lý</h1>`, thêm:

```html
{% if sale %}
<p class="ghi-chu">Đang xem khách của <strong>{{ ten_sale }}</strong>.
  <a href="/can-xu-ly?tat_ca=1">Xem tất cả →</a></p>
{% endif %}
```

Và sửa dòng "Không có khách nào trong diện cảnh báo." thành:

```html
<div class="trong">Không có khách nào trong diện cảnh báo{% if sale %} trong
  danh sách của {{ ten_sale }} — <a href="/can-xu-ly?tat_ca=1">xem tất cả</a>{% endif %}.</div>
```

- [ ] **Bước 7: Chạy test cho chắc là nó XANH**

Chạy: `pytest tests/test_khach_hang.py tests/test_bao_mat.py -v`
Mong đợi: PASS toàn bộ.

- [ ] **Bước 8: Chạy cả bộ test**

Chạy: `pytest -v`
Mong đợi: PASS toàn bộ.

- [ ] **Bước 9: Commit**

```bash
git add kome/khach_hang.py kome/web/app.py kome/web/templates/khach_hang.html \
        kome/web/templates/can_xu_ly.html tests/test_khach_hang.py tests/test_bao_mat.py
git commit -m "feat: /khach-hang va /can-xu-ly mac dinh loc theo khach cua minh

MAC DINH TIEN DUNG, khong phai hang rao: nam sale khong can giau nhau, mot
cu bam la xem duoc tat ca. Khong co kiem quyen nao o day va do la co y.
Nguoi khong phu trach khach nao (chu DN, ke toan) khong bi loc gi - loc theo
NULL thi ho mo len thay danh sach rong va tuong mat du lieu.
Bo dem trang thai di theo bo loc sale; so tren nut Xem tat ca lay tu truy van.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: `scripts/tao_nguoi_dung.py` — quản lý tài khoản

**Files:**
- Tạo: `scripts/tao_nguoi_dung.py`
- Test: `tests/test_tao_nguoi_dung.py`

**Interfaces:**
- Tiêu thụ: `kome.web.nguoi_dung` (Task 2).
- Sản xuất: `chay(argv: list[str], conn, doc_mat_khau) -> int` — mã thoát;
  `doc_mat_khau` là hàm không tham số trả về chuỗi, tách ra để test được mà
  không phải vá `getpass` toàn cục.

Đặc tả §4.2 đã quyết: **một script đúng hơn một màn hình** cho 5–7 tài khoản
đặt một lần. Đúng nếp `scripts/hoan_tac.py`.

- [ ] **Bước 1: Viết test thất bại** — `tests/test_tao_nguoi_dung.py`

```python
"""Script quản lý tài khoản. Chạy bằng tay, in ra thứ cần biết.

Bất biến quan trọng nhất: **script không bao giờ in mật khẩu, hash hay salt**
— màn hình của người quản trị cũng là một nơi dữ liệu rò ra được.
"""
import pytest

from kome.web import nguoi_dung as ND
from scripts.tao_nguoi_dung import chay

MK = "mat-khau-cua-an-2026"


def _doc(*mat_khau):
    """Giả lập getpass: trả lần lượt các mật khẩu được đưa vào."""
    it = iter(mat_khau)
    return lambda: next(it)


def test_them_tai_khoan_va_dang_nhap_duoc(conn, capsys):
    assert chay(["them", "an", "--sale", "0104"], conn, _doc(MK, MK)) == 0
    conn.commit()
    n = ND.kiem_tra(conn, "an", MK)
    assert n is not None and n.salesperson_code == "0104"
    assert n.duoc_vao_kho_du_lieu is False      # không đưa --kho-du-lieu


def test_co_kho_du_lieu_thi_cap_quyen(conn):
    chay(["them", "an", "--kho-du-lieu"], conn, _doc(MK, MK))
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is True


def test_go_lai_lan_hai_khong_khop_thi_khong_tao_gi(conn):
    """Gõ nhầm mật khẩu lúc tạo tài khoản = một người không đăng nhập được và
    không ai biết vì sao. Hỏi hai lần, lệch thì dừng."""
    assert chay(["them", "an"], conn, _doc(MK, "go-nham-roi")) != 0
    conn.rollback()
    assert ND.liet_ke(conn) == []


def test_mat_khau_qua_ngan_bi_tu_choi(conn):
    assert chay(["them", "an"], conn, _doc("ngan", "ngan")) != 0
    conn.rollback()
    assert ND.liet_ke(conn) == []


def test_liet_ke_khong_in_hash_khong_in_salt_khong_in_mat_khau(conn, capsys):
    """[CRITICAL] Màn hình của người quản trị cũng là chỗ dữ liệu rò ra."""
    ND.tao(conn, "an", MK, salesperson_code="0104", kho_du_lieu=True)
    conn.commit()
    assert chay([], conn, _doc()) == 0
    ra = capsys.readouterr().out
    assert "an" in ra and "0104" in ra
    assert MK not in ra
    for cam in ("mat_khau_hash", "mat_khau_salt", "\\x", "b'"):
        assert cam not in ra


def test_doi_mat_khau(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert chay(["doi-mat-khau", "an"], conn, _doc("mat-khau-moi-2026", "mat-khau-moi-2026")) == 0
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK) is None
    assert ND.kiem_tra(conn, "an", "mat-khau-moi-2026") is not None


def test_quyen_bat_va_tat(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert chay(["quyen", "an", "--kho-du-lieu"], conn, _doc()) == 0
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is True
    assert chay(["quyen", "an", "--bo-kho-du-lieu"], conn, _doc()) == 0
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is False


def test_khong_co_tai_khoan_do_thi_bao_ro_chu_khong_im_lang(conn, capsys):
    """Mã thoát khác 0 VÀ nói ra tên không tìm thấy. Im lặng rồi thoát 0 là
    người quản trị tưởng đã đổi xong mật khẩu cho một người không tồn tại."""
    assert chay(["doi-mat-khau", "khong-co-ai"], conn, _doc(MK, MK)) != 0
    assert "khong-co-ai" in capsys.readouterr().out
    assert chay(["quyen", "khong-co-ai", "--kho-du-lieu"], conn, _doc()) != 0
    assert "khong-co-ai" in capsys.readouterr().out


def test_ma_sale_khong_co_that_bao_loi_de_hieu(conn, capsys):
    assert chay(["them", "an", "--sale", "9999"], conn, _doc(MK, MK)) != 0
    conn.rollback()
    ra = capsys.readouterr().out
    assert "9999" in ra
```

- [ ] **Bước 2: Chạy test cho chắc là nó ĐỎ**

Chạy: `pytest tests/test_tao_nguoi_dung.py -v`
Mong đợi: FAIL — `ModuleNotFoundError: No module named 'scripts.tao_nguoi_dung'`.
(Nếu `scripts/` chưa có `__init__.py`, thêm file rỗng `scripts/__init__.py` —
`tests/` đã có sẵn một cái, cùng nếp.)

- [ ] **Bước 3: Viết script** — `scripts/tao_nguoi_dung.py`

```python
"""Tạo, sửa và liệt kê tài khoản đăng nhập của trang nội bộ.

Chạy (từ thư mục dự án, cả PowerShell lẫn Git Bash đều được):
    python scripts/tao_nguoi_dung.py                        liệt kê tài khoản
    python scripts/tao_nguoi_dung.py them an --sale 0104
    python scripts/tao_nguoi_dung.py them minh --kho-du-lieu
    python scripts/tao_nguoi_dung.py doi-mat-khau an
    python scripts/tao_nguoi_dung.py quyen an --kho-du-lieu
    python scripts/tao_nguoi_dung.py quyen an --bo-kho-du-lieu
    (thêm --test ở cuối để chạy trên CSDL thử nghiệm)

Script tự đọc .env, không cần nạp biến môi trường trước.

MẬT KHẨU LUÔN NHẬP QUA BÀN PHÍM, không bao giờ nhận qua tham số dòng lệnh:
tham số nằm lại trong lịch sử shell và trong danh sách tiến trình, nơi ai
đăng nhập cùng máy cũng đọc được.

Vì sao là script chứ không phải một màn hình trong web app: 5–7 tài khoản đặt
một lần thì một màn hình là nhiều việc hơn để dựng, để bảo trì và để làm hỏng.
Dựng màn hình khi số tài khoản đủ nhiều để việc sửa tay thành phiền.

--kho-du-lieu là quyền vào màn Kho dữ liệu: nạp file VÀ hoàn tác một lần nạp.
Hoàn tác nhầm lô đối soát tháng sẽ xoá cả một tháng doanh thu khỏi kho. Chỉ
cấp cho người phụ trách nạp và chủ doanh nghiệp.
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg

from kome.web import nguoi_dung as ND

DAI_TOI_THIEU = 12

HUONG_DAN = """    python scripts/tao_nguoi_dung.py                        liệt kê tài khoản
    python scripts/tao_nguoi_dung.py them <tên> [--sale <mã>] [--kho-du-lieu]
    python scripts/tao_nguoi_dung.py doi-mat-khau <tên>
    python scripts/tao_nguoi_dung.py quyen <tên> --kho-du-lieu | --bo-kho-du-lieu
    (thêm --test ở cuối để chạy trên CSDL thử nghiệm)"""


def _hoi_mat_khau(doc_mat_khau) -> str | None:
    """Hỏi hai lần. None nếu lệch nhau hoặc quá ngắn."""
    a = doc_mat_khau()
    b = doc_mat_khau()
    if a != b:
        print("Hai lần gõ không khớp nhau. Chưa đổi gì cả.")
        return None
    if len(a) < DAI_TOI_THIEU:
        print(f"Mật khẩu chỉ dài {len(a)} ký tự — phải từ {DAI_TOI_THIEU} trở lên.")
        return None
    return a


def liet_ke(conn) -> int:
    ds = ND.liet_ke(conn)
    if not ds:
        print("Chưa có tài khoản nào. Tạo bằng:  python scripts/tao_nguoi_dung.py them <tên>")
        return 0
    print(f"{'Tên đăng nhập':<20}{'Mã sale':<10}{'Phụ trách':<24}Kho dữ liệu")
    print("-" * 70)
    for n in ds:
        print(f"{n.ten_dang_nhap:<20}{n.salesperson_code or '—':<10}"
              f"{n.ten_sale or '—':<24}{'CÓ' if n.duoc_vao_kho_du_lieu else '—'}")
    print("\nKho dữ liệu = được nạp file VÀ hoàn tác lần nạp (xoá dữ liệu khỏi kho).")
    return 0


def them(conn, ten: str, sale: str | None, kho_du_lieu: bool, doc_mat_khau) -> int:
    mk = _hoi_mat_khau(doc_mat_khau)
    if mk is None:
        return 1
    try:
        ND.tao(conn, ten, mk, salesperson_code=sale, kho_du_lieu=kho_du_lieu)
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
          + (", CÓ quyền vào Kho dữ liệu." if kho_du_lieu
             else ", không có quyền vào Kho dữ liệu."))
    return 0


def doi_mat_khau(conn, ten: str, doc_mat_khau) -> int:
    mk = _hoi_mat_khau(doc_mat_khau)
    if mk is None:
        return 1
    if not ND.doi_mat_khau(conn, ten, mk):
        print(f"Không có tài khoản tên '{ten}'. Chạy không tham số để xem danh sách.")
        return 1
    conn.commit()
    print(f"Đã đổi mật khẩu cho '{ten}'. Lần đăng nhập sau của họ dùng mật khẩu mới;\n"
          f"phiên đang mở của họ vẫn chạy tới khi hết hạn (12 giờ).\n"
          f"Cần cắt NGAY thì xoá tài khoản, hoặc đổi KOME_SESSION_SECRET "
          f"(đăng xuất tất cả mọi người).")
    return 0


def quyen(conn, ten: str, kho_du_lieu: bool) -> int:
    if not ND.dat_quyen(conn, ten, kho_du_lieu):
        print(f"Không có tài khoản tên '{ten}'. Chạy không tham số để xem danh sách.")
        return 1
    conn.commit()
    print(f"'{ten}' " + ("GIỜ vào được" if kho_du_lieu else "KHÔNG còn vào được")
          + " màn Kho dữ liệu. Có hiệu lực ngay ở lượt bấm kế tiếp của họ.")
    return 0


def chay(argv: list[str], conn, doc_mat_khau=None) -> int:
    """Mã thoát 0 = xong, khác 0 = có lỗi. `doc_mat_khau` tách ra để test
    được mà không phải vá getpass toàn cục."""
    doc_mat_khau = doc_mat_khau or (lambda: getpass.getpass("Mật khẩu: "))
    argv = [a for a in argv if a != "--test"]
    if not argv:
        return liet_ke(conn)

    lenh, *phan_con_lai = argv
    ten = next((a for a in phan_con_lai if not a.startswith("--")), None)
    kho = "--kho-du-lieu" in phan_con_lai
    bo_kho = "--bo-kho-du-lieu" in phan_con_lai
    sale = None
    if "--sale" in phan_con_lai:
        i = phan_con_lai.index("--sale")
        sale = phan_con_lai[i + 1] if i + 1 < len(phan_con_lai) else None

    if lenh not in ("them", "doi-mat-khau", "quyen") or not ten:
        print(f"Không hiểu lệnh. Cách dùng:\n{HUONG_DAN}")
        return 2
    if lenh == "them":
        return them(conn, ten, sale, kho, doc_mat_khau)
    if lenh == "doi-mat-khau":
        return doi_mat_khau(conn, ten, doc_mat_khau)
    if not kho and not bo_kho:
        print("Lệnh quyền cần --kho-du-lieu hoặc --bo-kho-du-lieu.")
        return 2
    return quyen(conn, ten, kho)


if __name__ == "__main__":
    import os
    from kome.db import connect
    from kome.env import nap_env

    nap_env()
    url = os.environ["DATABASE_URL_TEST" if "--test" in sys.argv else "DATABASE_URL"]
    with connect(url) as c:
        sys.exit(chay(sys.argv[1:], c))
```

Lưu ý: `--sale` lấy giá trị bằng chỉ số, nên `ten` phải tìm phần tử **không**
bắt đầu bằng `--`; nếu mã sale vô tình đứng trước tên thì lệnh sai — chấp nhận
được cho một script chạy tay, và thông báo "Không hiểu lệnh" in ra hướng dẫn.

- [ ] **Bước 4: Chạy test cho chắc là nó XANH**

Chạy: `pytest tests/test_tao_nguoi_dung.py -v`
Mong đợi: PASS toàn bộ.

- [ ] **Bước 5: Thử tay trên CSDL thử nghiệm**

```bash
python scripts/tao_nguoi_dung.py --test
```
Mong đợi: in bảng tài khoản (hoặc "Chưa có tài khoản nào"), **không** in chuỗi
nào trông như hash (`\x...`).

- [ ] **Bước 6: Chạy cả bộ test rồi commit**

Chạy: `pytest -v` → PASS toàn bộ.

```bash
git add scripts/tao_nguoi_dung.py scripts/__init__.py tests/test_tao_nguoi_dung.py
git commit -m "feat: scripts/tao_nguoi_dung.py - quan ly tai khoan bang dong lenh

Mat khau nhap qua getpass, hoi hai lan, khong bao gio nhan qua tham so dong
lenh (tham so nam lai trong lich su shell va danh sach tien trinh).
Lenh liet ke in ten/ma sale/quyen - khong in hash, khong in salt.
Logic tach ra ham chay(argv, conn, doc_mat_khau) de test duoc ma khong phai
va getpass toan cuc.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: Tài liệu

**Files:**
- Sửa: `CLAUDE.md`, `docs/runbook.md`, `docs/trien-khai-vercel.md`,
  `.env.example`
- Sửa: `docs/superpowers/specs/2026-09-17-dashboard-nguoi-dung-crm-dot-1-design.md`
  (chỉ phần đầu)

Không có test tự động cho task này. Tiêu chí: **đọc tài liệu rồi làm theo là
dựng được bản chạy đúng**, và không còn chỗ nào dạy sai về `KOME_MAT_KHAU`.

- [ ] **Bước 1: `CLAUDE.md`** — ba chỗ

(a) Bảng "Hai bản chạy của web app", dòng Đăng nhập:

```
| Đăng nhập | tài khoản riêng (bật khi có `KOME_SESSION_SECRET`) | **bắt buộc** (`KOME_SESSION_SECRET`) |
```

(b) Thêm một mục mới sau bảng đó:

```markdown
## Danh tính và quyền (Đợt 3, `db/migrations/019_danh_tinh.sql`)

Mỗi người một tài khoản (`app.nguoi_dung`), mật khẩu băm bằng `scrypt` với
salt riêng. Vé đăng nhập là cookie `<id>.<hạn>.<HMAC>` ký bằng
`KOME_SESSION_SECRET` — **khoá của hệ thống, không phải mật khẩu của ai**, nên
đổi mật khẩu một người không làm bốn người kia bị đăng xuất.

**Bất biến:** chữ ký của vé phải phủ **cả `id` lẫn `hạn`**. Ký riêng phần hạn
thì sửa một con số trong cookie là hoá thân thành người khác — kể cả thành
người có quyền bấm nút xoá dữ liệu. Có test canh: `tests/test_bao_mat.py::
test_doi_id_trong_ve_khong_hoa_than_duoc_thanh_nguoi_khac`.

**Bất biến:** cờ `duoc_vao_kho_du_lieu` **không nằm trong vé** — tra
`app.nguoi_dung` mỗi lượt gọi. Vé sống 12 giờ, mà thu hồi quyền trên màn có
nút xoá thì phải ăn ngay hôm nay.

**Bất biến:** lọc theo `salesperson_code` là **mặc định tiện dụng, KHÔNG phải
hàng rào bảo mật**. Công ty năm người, ai cũng biết khách của ai; đăng nhập
riêng là để cá nhân hoá, không phải để chặn. Không được thêm kiểm quyền vào
`/khach-hang` hay `/can-xu-ly`.

**CẠM BẪY — cổng chỉ tồn tại khi có khoá ký.** Để trống `KOME_SESSION_SECRET`
ở máy trong công ty là **không có đăng nhập và không có phân quyền**: ai mở
được trang cũng bấm được nút Hoàn tác — nút xoá được cả một tháng doanh thu.
Bản Vercel không dính (nó từ chối khởi động nếu thiếu khoá), nhưng bản Vercel
cũng không nạp/hoàn tác được gì. Nói cách khác: **cờ quyền chỉ bảo vệ được cái
nút nguy hiểm khi máy trong công ty CŨNG đặt `KOME_SESSION_SECRET`.**

Tạo và sửa tài khoản: `python scripts/tao_nguoi_dung.py` (xem `docs/runbook.md`).

### Hai kết nối CSDL
| Biến | Vai trò | Dùng cho |
|---|---|---|
| `DATABASE_URL` | `kome_ingest_user` | Màn Kho dữ liệu: nạp, hoàn tác |
| `DATABASE_URL_APP` | `kome_app_user` | Đăng nhập và mọi trang chỉ đọc |

Thiếu `DATABASE_URL_APP` thì app vẫn chạy (in cảnh báo) nhưng các trang đọc
chạy bằng vai trò có quyền ghi vào `core` — mất lớp phòng thủ, không mất trang.
```

(c) Bảng "Các trang của web app": thêm một dòng ghi chú dưới bảng —

```
Trang `/khach-hang` và `/can-xu-ly` mặc định chỉ hiện khách của người đang
đăng nhập; `?tat_ca=1` bỏ lọc. Người có `salesperson_code` NULL (chủ DN, kế
toán) thấy toàn bộ ngay từ đầu.
```

- [ ] **Bước 2: `docs/runbook.md`** — sửa hai dòng trong bảng sự cố và thêm mục mới

Dòng 44 và 46 đổi thành:

```
| Trang không mở, Vercel báo lỗi khởi động | Thiếu `KOME_SESSION_SECRET`, hoặc chuỗi ngắn dưới 12 ký tự | Vercel → Settings → Environment Variables → sửa → **Redeploy** |
| Cần chặn một người đã nghỉ việc | Tài khoản của họ vẫn còn | Xoá tài khoản: họ bị chặn ở **lượt bấm kế tiếp**, không cần chờ hết phiên. Nghi lộ khoá ký thì đổi `KOME_SESSION_SECRET` → **mọi người** phải đăng nhập lại |
```

Thêm một mục mới:

```markdown
## Tài khoản đăng nhập

    python scripts/tao_nguoi_dung.py                      xem danh sách
    python scripts/tao_nguoi_dung.py them an --sale 0104
    python scripts/tao_nguoi_dung.py them minh --kho-du-lieu
    python scripts/tao_nguoi_dung.py doi-mat-khau an
    python scripts/tao_nguoi_dung.py quyen an --kho-du-lieu
    python scripts/tao_nguoi_dung.py quyen an --bo-kho-du-lieu

`--sale <mã>` gắn tài khoản với một trong 5 người phụ trách của OBC
(`core.dim_salesperson`) — trang khách hàng khi đó mặc định chỉ hiện khách của
họ. Bỏ `--sale` cho người không phụ trách khách nào (chủ DN, kế toán, kho): họ
thấy toàn bộ.

`--kho-du-lieu` mở màn Kho dữ liệu, tức **nạp file VÀ hoàn tác một lần nạp**.
Hoàn tác nhầm lô đối soát tháng sẽ xoá cả một tháng doanh thu khỏi kho. Chỉ
cấp cho người phụ trách nạp và chủ doanh nghiệp.

**Phải đặt `KOME_SESSION_SECRET` trong `.env` của máy trong công ty.** Để
trống thì trang chạy KHÔNG có đăng nhập và KHÔNG có phân quyền — ai mở được
trang cũng bấm được nút Hoàn tác. Đây cũng đúng là máy DUY NHẤT nạp và hoàn
tác được, nên để trống là vô hiệu hoá toàn bộ phần bảo vệ của đợt 3.

Quên mật khẩu: không có luồng tự phục hồi (cố ý — 5–7 người, một luồng khôi
phục qua email là thêm một cửa để tấn công). Người quản trị đặt lại bằng
`doi-mat-khau`.
```

- [ ] **Bước 3: `docs/trien-khai-vercel.md`** — ba chỗ

- Bảng biến môi trường (dòng ~80): đổi `KOME_MAT_KHAU` thành hai dòng
  `KOME_SESSION_SECRET` (chuỗi ngẫu nhiên ≥12 ký tự) và `DATABASE_URL_APP`
  (cùng CSDL, user `kome_app_user`, **cổng 6543**).
- Dòng ~115: thay lời khuyên "đổi `KOME_MAT_KHAU` mỗi khi có người nghỉ việc"
  bằng: *"Người nghỉ việc thì **xoá tài khoản của họ** —
  `scripts/tao_nguoi_dung.py` trên máy trong công ty; họ bị chặn ở lượt bấm kế
  tiếp. Chỉ đổi `KOME_SESSION_SECRET` khi nghi khoá ký bị lộ, vì đổi nó là bắt
  **tất cả mọi người** đăng nhập lại."*
- Dòng ~163: đổi `KOME_MAT_KHAU` thành `KOME_SESSION_SECRET` trong đoạn giải
  thích miễn trừ `/static/`.

- [ ] **Bước 4: `.env.example`** — thay khối `KOME_MAT_KHAU` (dòng 11–15)

```bash
# Khoá ký vé đăng nhập. CHUỖI NGẪU NHIÊN, tối thiểu 12 ký tự — KHÔNG phải mật
# khẩu của ai cả. Sinh một chuỗi bằng:
#     python -c "import secrets; print(secrets.token_urlsafe(32))"
#
# Để TRỐNG = trang chạy KHÔNG CÓ ĐĂNG NHẬP và KHÔNG CÓ PHÂN QUYỀN: ai mở được
# trang cũng bấm được nút Hoàn tác (xoá được cả một tháng doanh thu). Máy
# trong công ty NÊN đặt. Trên Vercel thì BẮT BUỘC — app từ chối khởi động nếu
# thiếu. Đổi chuỗi này = đăng xuất tất cả mọi người.
# KOME_SESSION_SECRET=

# Kết nối thứ hai, chạy bằng vai trò kome_app_user (chỉ ĐỌC core/mart). Mọi
# trang trừ màn Kho dữ liệu đi qua đây, nên một câu lệnh ghi viết nhầm vào
# `core` sẽ bị chính CSDL từ chối. Thiếu biến này thì app vẫn chạy nhưng in
# cảnh báo và mất lớp phòng thủ đó.
# DATABASE_URL_APP=postgresql://kome_app_user:pass@host:5432/postgres
```

- [ ] **Bước 5: Ghi rõ spec đợt 1 đã bị thay thế phần danh tính**

Thêm ngay dưới tiêu đề của
`docs/superpowers/specs/2026-09-17-dashboard-nguoi-dung-crm-dot-1-design.md`:

```markdown
> **⚠️ Tài liệu này đã được TÁCH LÀM ĐÔI (2026-09-21).** Lộ trình 24 màn §2
> chia nó thành hai đợt:
>
> - **Phần danh tính (§5.1, §5.3, §5.4) bị thay thế** bởi
>   `2026-09-21-dot-3-danh-tinh-design.md`. Một **tiền đề ở đây đã sai**: tài
>   liệu này đóng khung việc lọc theo `salesperson_code` như một *ranh giới
>   bảo mật* ("sale chỉ thấy khách của mình") và đòi một test canh việc chặn
>   lộ dữ liệu khách của người khác. Chủ sở hữu đã quyết ngược lại — năm sale
>   **không cần giấu nhau**; bộ lọc chỉ là mặc định tiện dụng. Test đó đã bị
>   **bỏ**, không phải giữ. Cột `vai_tro` cũng bị bỏ, thay bằng một boolean
>   `duoc_vao_kho_du_lieu`.
> - **Phần CRM** vẫn còn hiệu lực, xếp ở đợt 7.
```

- [ ] **Bước 6: Chạy cả bộ test rồi commit**

Chạy: `pytest -v` → PASS toàn bộ.

```bash
git add CLAUDE.md docs/runbook.md docs/trien-khai-vercel.md .env.example \
        docs/superpowers/specs/2026-09-17-dashboard-nguoi-dung-crm-dot-1-design.md
git commit -m "docs: cap nhat tai lieu cho dot 3 - danh tinh

Ghi ro cam bay lon nhat: de trong KOME_SESSION_SECRET o may trong cong ty =
khong dang nhap VA khong phan quyen, tuc nut Hoan tac lai mo cho tat ca - ma
do dung la may DUY NHAT hoan tac duoc.
Spec dot 1 duoc danh dau da tach lam doi va noi ro mot tien de cua no da sai.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Kiểm tay sau khi merge — bắt buộc trước khi coi là xong

Đặc tả §11 có hai tiêu chí không test tự động nào thay được:

- [ ] **Máy trong công ty:** đặt `KOME_SESSION_SECRET` và `DATABASE_URL_APP`
      vào `.env`, chạy `python db/migrate.py` (bằng vai trò `postgres`), tạo
      tài khoản cho từng người, khởi động `uvicorn kome.web.app:app`.
- [ ] Đăng nhập bằng tài khoản **không** có `--kho-du-lieu`: sidebar không có
      mục Kho dữ liệu; gõ thẳng `/kho-du-lieu` nhận trang 403 giải thích.
- [ ] Đăng nhập bằng tài khoản có `--sale`: `/khach-hang` mặc định chỉ hiện
      khách của họ, bấm "Xem tất cả" ra đủ 2.080 khách.
- [ ] Nạp thử một file OBC bằng tài khoản **có** quyền — luồng 13:30 vẫn chạy.
- [ ] **Vercel:** thêm hai biến môi trường, Redeploy. Chưa đăng nhập thì mọi
      trang đẩy về `/dang-nhap` và trang đó **có CSS, có font**. Đăng nhập
      xong `/` mở được.
- [ ] Mở `/` trên Vercel khoảng 30 lần liên tiếp — không lỗi
      `prepared statement`. (Cổng 6543 + `prepare_threshold=None`; kết nối thứ
      hai `DATABASE_URL_APP` là đường mới nên đáng kiểm lại.)

---

## Tự soát kế hoạch

**Phủ đặc tả:**

| Mục đặc tả | Task |
|---|---|
| §6.1 migration 019, hai bảng, GRANT meta | 1 |
| §6.2 vé không trạng thái, chữ ký phủ id+hạn, scrypt | 2, 3 |
| §6.3 hai kết nối CSDL | 4 |
| §6.4 chặn Kho dữ liệu, tra CSDL mỗi lượt, 403 + ẩn sidebar | 5 |
| §6.5 mặc định "khách của tôi", nút xem tất cả, người NULL thấy hết | 6 |
| §6.6 chốt an toàn thay `KOME_MAT_KHAU`, bỏ hẳn cơ chế cũ | 3, 4 |
| §7 `scripts/tao_nguoi_dung.py`, 4 lệnh, getpass, không in hash | 7 |
| §9 bảng 13 test | 1 (2 dòng cuối), 3, 4, 5, 6 |
| §11 tiêu chí hoàn thành | tất cả + mục kiểm tay |

**Ba việc đặc tả đòi mà kế hoạch KHÔNG làm, có lý do:**

1. §4.2 đã cắt màn Cài đặt và màn Nhật ký thao tác — kế hoạch giữ nguyên quyết
   định đó.
2. Không có luồng khôi phục mật khẩu (§10 D5) — chủ sở hữu đặt lại bằng script.
3. 7 khách có `salesperson_code` rỗng (`''`) sẽ không hiện cho ai khi đang lọc
   (§10 D4). Chấp nhận được: nút "Xem tất cả" vẫn thấy họ. **Lưu ý cho người
   thực thi:** điều kiện lọc là `salesperson_code = %s`, nên chuỗi rỗng không
   khớp mã nào — đúng như D4 mô tả, không phải lỗi.
