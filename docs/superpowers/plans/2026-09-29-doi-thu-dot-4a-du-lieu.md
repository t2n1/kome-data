# Đợt 4a — dữ liệu cho giao diện mới `/doi-thu` — kế hoạch thực hiện

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm phần dữ liệu mà màn `/doi-thu` mới cần:
- quy cách gói của đối thủ;
- giá bậc có cấu trúc và giá tại 1 / 5 / 10 thùng / pallet;
- 標準価格 của KOME cùng dải 売価No;
- điều kiện giao hàng có cấu trúc (của đối thủ và của KOME);
- sửa được mọi trường mới;
- sửa lỗi kg của KOME (15 nhóm giá lệch).

**Architecture:** Bốn migration mới:

| Migration | Nội dung |
|---|---|
| 065 | bảng và cột |
| 066 | mart phía KOME |
| 067 | mart quan sát đối thủ |
| 068 | mart giao hàng / điều kiện |

Mọi quy đổi viết đúng một lần ở `mart`. Bộ nạp, gói và hàm ghi ở Python chỉ chở dữ liệu và kiểm đầu vào. Thuật toán phí đơn mẫu có hai bản (Python + TS) chạy chung một file ca kiểm, theo nếp `nen` / `squarify`.

**Tech Stack:** Postgres 17 (Supabase), psycopg 3, FastAPI (không đụng route ở đợt này), pandas / calamine (bộ đọc), TypeScript + vitest (chỉ `phi_giao.ts`).

**Spec:** `docs/superpowers/specs/2026-09-29-doi-thu-giao-dien-moi-design.md`. §5 là chính; §6.2, §6.3 việc 1–2 cũng thuộc đợt này. Đặc tả gốc là `docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md` §4.

## Global Constraints

- Migration chỉ THÊM file mới (`db/migrations/065_…` → `068_…`). 059–064 đã chạy trên CSDL thật, **không sửa**. Chạy bằng `postgres` qua `python db/migrate.py`, không bao giờ qua SQL Editor (bẫy RLS, 061).
- `core` = nạp qua cổng (`kome_ingest`), `app` = web ghi (`kome_app`), `mart` = định nghĩa. Sửa của sale KHÔNG đụng dòng `core`.
- Sổ đính chính mới **CHỈ THÊM**: `REVOKE UPDATE, DELETE … FROM kome_app`. Mỗi lần ghi của web có thêm một dòng `app.doi_thu_nhat_ky` trong CÙNG giao dịch (bảng không có trong `anh_chup._PHIEN_BAN` nên ảnh chụp đổi nhờ dòng nhật ký — nếp 064).
- NULL = "không ghi / chưa rõ", **không bao giờ là 0**. Không đoán: không "1 pallet = 40 thùng", không phí ship khi bảng không ghi.
- Mã là TEXT (bẫy #1). Tiền yên nguyên văn như bảng in; quy về ¥/kg chưa thuế chỉ ở `mart` (÷ 1,08 đúng một lần khi `thue = 'co'`).
- Tỷ suất / giá gộp nhóm là **tỷ số của các tổng**, không trung bình tỷ số.
- `売価No.10` = giá khuyến mãi của KOME: không vào dải giá thường, không bao giờ mặc định. Định nghĩa một lần ở `mart.la_gia_km_kome(price_level)`.
- Hai cột giá OBC mâu thuẫn (gồm thuế > 0 và gồm thuế < chưa thuế) hoặc chưa thuế = 0 → dùng gồm thuế ÷ 1,08.
- Sửa `db/migrations/*.sql` hoặc `config/files.yml` → chạy lại `python scripts/sinh_tai_lieu.py` và `python scripts/sinh_cot_dung.py`, commit JSON sinh ra.
- Sửa bất cứ gì trong `giao_dien/` → `cd giao_dien && npm run build`, commit `kome/web/spa/`.
- Test: `pytest -q` (CSDL test nội bộ `DATABASE_URL_TEST`, Postgres 17 localhost — cả bộ ~4 phút). Mỗi task chạy file test của nó; task cuối chạy cả bộ.
- Thông điệp commit kết thúc bằng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

## Bản đồ file

| File | Việc |
|---|---|
| `db/migrations/065_doi_thu_du_lieu_moi.sql` (mới) | cột mới `core.fact_gia_doi_thu` / `app.gia_doi_thu_tay` / `core.dim_product`; `core.fact_giao_hang_doi_thu`; `app.giao_hang_kome` (+ dòng mặc định); `app.dinh_chinh_giao_hang`, `app.dinh_chinh_dieu_kien`; CHECK mới của `dinh_chinh_gia.truong`, `doi_thu_nhat_ky.loai`, `fact_dieu_kien_doi_thu.loai` |
| `db/migrations/066_mart_kome_quy_cach_bang_gia.sql` (mới) | `mart.quy_cach_kome` (+`kg_00`, `kg_02`), `mart.gia_kome_kg` theo pack, `mart.la_gia_km_kome`, `mart.gia_kome_bang`, `mart.gia_kome_chuan` |
| `db/migrations/067_mart_quan_sat_gia_bac.sql` (mới) | `mart.gia_bac_kg`, `mart.gia_doi_thu_quan_sat` (+ cột mới), tạo lại `mart.gia_doi_thu_hien_hanh`, `mart.so_sanh_nhom` (+ `gia_kome_chuan`, `gia_kome_bang`, `gia_kome_km`) |
| `db/migrations/068_mart_giao_hang_dieu_kien.sql` (mới) | `mart.giao_hang_hien_hanh`, `mart.giao_hang_kome_bang_chung`, `mart.dieu_kien_hien_hanh` |
| `config/files.yml` | `doi_thu_gia` + 3 cột; spec mới `doi_thu_giao_hang`; `shohin` + 2 cột 荷姿１; `tanka` + 2 cột 標準価格 |
| `kome/loaders/doi_thu.py` | `COT_GIA` + 3 cột; `COT_GIAO_HANG`, `load_giao_hang` |
| `kome/loaders/price.py` | xoay thêm `price_level = 'std'` |
| `kome/pipeline.py`, `kome/nhat_ky_nap.py`, `kome/kho_du_lieu.py`, `kome/tai_lieu.py` | đăng ký spec `doi_thu_giao_hang`; `shohin` thêm 2 cột |
| `kome/san_pham_360.py` | `_bac_gia`: nhãn `標準価格` / `10 · khuyến mãi`, giá theo luật hai cột |
| `scripts/goi_doi_thu.py` | cột mới, kiểm `bac`, luật `gia_goc` = giá lẻ, file `doi_thu_giao_hang_*.xlsx`, tách ghi chú của người đọc |
| `kome/doi_thu.py` | `TRUONG_SUA` + 5 trường, kiểm, cho phép xoá khuyến mãi / bậc |
| `kome/doi_thu_giao.py` (mới) | `sua_giao_hang`, `sua_dieu_kien` (hàm ghi, chưa có route) |
| `kome/phi_giao.py` (mới), `giao_dien/src/doi_thu/phi_giao.ts` (+`.test.ts`), `tests/du_lieu/phi_giao_ca.json` (mới) | thuật toán phí đơn mẫu, hai bản |
| `tests/test_doi_thu_bang.py`, `tests/test_nap_doi_thu.py`, `tests/test_goi_doi_thu.py`, `tests/test_mart_doi_thu.py`, `tests/test_doi_thu.py`, `tests/test_doi_thu_giao.py` (mới), `tests/test_phi_giao.py` (mới), `tests/test_load_price.py` (hoặc file test tanka hiện có), `tests/conftest.py` | test |
| `docs/doi-thu/huong-dan-doc.md`, `docs/doi-thu/so-tay-theo-ben.md`, `CLAUDE.md` | §6.2 + bất biến 065–068 |

---

### Task 1: Migration 065 — bảng và cột mới

**Files:**
- Create: `db/migrations/065_doi_thu_du_lieu_moi.sql`
- Modify: `tests/conftest.py` (thêm `app.giao_hang_kome` vào `GIU_LAI`)
- Test: `tests/test_doi_thu_bang.py`

**Interfaces:**
- Produces:
  - `core.fact_gia_doi_thu.{so_goi_thung int, kl_goi_g numeric(10,2), bac jsonb}` (cùng ba cột trên `app.gia_doi_thu_tay`, bảng tay thêm `khuyen_mai text`, `gia_truoc_km numeric(12,2)`);
  - `core.dim_product.{pack1_code text, pack1_base_qty numeric(14,4)}`: `pack1_code` NULL = chưa nạp bản có cột 荷姿, `''` = mã không có 荷姿 nào;
  - `core.fact_giao_hang_doi_thu`, `app.giao_hang_kome` (MỘT dòng, khoá `id boolean`), `app.dinh_chinh_giao_hang`, `app.dinh_chinh_dieu_kien`;
  - `dinh_chinh_gia.truong` nhận thêm `so_goi_thung`, `kl_goi_g`, `bac`, `khuyen_mai`, `gia_truoc_km`;
  - `doi_thu_nhat_ky.loai` nhận thêm `giao_hang`, `dieu_kien`;
  - `fact_dieu_kien_doi_thu.loai` nhận thêm `ghi_chu_doc`.

- [ ] **Step 1: Viết test hỏng** — thêm vào cuối `tests/test_doi_thu_bang.py`:

```python
# ---------------------------------------------------------------- 065 (đợt 4a)

def test_065_cot_quy_cach_va_bac_tren_fact_va_bang_tay(conn):
    for bang in ("core.fact_gia_doi_thu", "app.gia_doi_thu_tay"):
        cot = {r[0]: r[1] for r in conn.execute(
            """SELECT column_name, data_type FROM information_schema.columns
               WHERE table_schema || '.' || table_name = %s""", (bang,))}
        assert cot["so_goi_thung"] == "integer", bang
        assert cot["kl_goi_g"] == "numeric", bang
        assert cot["bac"] == "jsonb", bang
    cot_tay = {r[0] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='app' AND table_name='gia_doi_thu_tay'")}
    assert {"khuyen_mai", "gia_truoc_km"} <= cot_tay


def test_065_bac_phai_la_mang_va_quy_cach_duong(conn, batch):
    b = batch(1)
    def them(**kw):
        conn.execute(
            f"""INSERT INTO core.fact_gia_doi_thu (batch_id, ma_dong, ma_doi_thu, ma_hang_dt, ngay_nguon, hinh_thuc_nguon,
                  ten_goc, trang_thai, do_chac{''.join(', ' + k for k in kw)})
                VALUES (%s, %s, 'THAK', 'ten:x', '2026-08-01', 'file', 'x', 'con', 'chac'{', %s' * len(kw)})""",
            (b, f"d{len(kw)}{list(kw.values())}", *kw.values()))
    them(bac='[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]', so_goi_thung=20, kl_goi_g=500)
    conn.commit()
    for xau in ({"bac": '{"tu": 5}'}, {"so_goi_thung": 0}, {"kl_goi_g": 0}, {"kl_goi_g": 30001}):
        with pytest.raises(psycopg.errors.CheckViolation):
            them(**xau)
        conn.rollback()


def test_065_so_moi_CHI_THEM_kome_app(conn):
    for bang in ("app.dinh_chinh_giao_hang", "app.dinh_chinh_dieu_kien"):
        assert _quyen(conn, "kome_app", bang, "INSERT"), bang
        assert _quyen(conn, "kome_app", bang, "SELECT"), bang
        assert not _quyen(conn, "kome_app", bang, "UPDATE"), bang
        assert not _quyen(conn, "kome_app", bang, "DELETE"), bang
    assert _quyen(conn, "kome_app", "app.giao_hang_kome", "UPDATE")          # KOME sửa được, lịch sử ở nhật ký
    assert not _quyen(conn, "kome_app", "app.giao_hang_kome", "DELETE")
    assert _quyen(conn, "kome_ingest", "core.fact_giao_hang_doi_thu", "DELETE")   # nút Hoàn tác
    assert not _quyen(conn, "kome_app", "core.fact_giao_hang_doi_thu", "INSERT")


def test_065_kome_mac_dinh_suy_tu_phieu_ban_chua_xac_nhan(conn):
    r = conn.execute("""SELECT bao_ship, phi_ship, phi_ship_theo, mien_ship_tu, phi_daibiki, daibiki_tu, daibiki_sau,
                               thue, da_xac_nhan FROM app.giao_hang_kome""").fetchall()
    assert r == [(False, 500, "don", 20000, 330, 20000, 300, "chua", False)]


def test_065_check_moi_nhan_truong_va_loai_moi(conn):
    for t in ("so_goi_thung", "kl_goi_g", "bac", "khuyen_mai", "gia_truoc_km"):
        conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (1, %s, '1')", (t,))
    for loai in ("giao_hang", "dieu_kien"):
        conn.execute("INSERT INTO app.doi_thu_nhat_ky (loai, doi_tuong) VALUES (%s, 'x')", (loai,))
    conn.commit()
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO app.dinh_chinh_giao_hang (ma_doi_thu, truong, gia_tri_moi) VALUES ('THAK', 'khong_co', '1')")
    conn.rollback()


def test_065_dim_product_co_cot_hanh_dong_goi(conn):
    cot = {r[0] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name='dim_product'")}
    assert {"pack1_code", "pack1_base_qty"} <= cot
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_doi_thu_bang.py -q -k 065`
Expected: FAIL (`KeyError: 'so_goi_thung'`, relation `app.giao_hang_kome` không tồn tại, …)

- [ ] **Step 3: Viết migration** `db/migrations/065_doi_thu_du_lieu_moi.sql`:

```sql
-- 065 — Dữ liệu cho giao diện mới /doi-thu (đặc tả 2026-09-29-doi-thu-giao-dien-moi-design.md §5).
-- (1) Quy cách gói + giá bậc có cấu trúc của đối thủ (§5.1, §5.2). `bac` là MẢNG
--     [{"tu": 5, "don_vi_sl": "thung"|"kg"|"goi"|"pallet", "gia": 5300, "don_vi_gia": "thung"|"kg"|"goi"}] cùng `thue`
--     của dòng; chữ `gia_bac` giữ làm nguyên văn. Quy về ¥/kg chỉ ở mart (067).
-- (2) core.dim_product.pack1_*: 荷姿１ của 商品データ (§6.3 việc 2). pack1_code NULL = bản nạp chưa có cột này
--     (mart giữ luật cũ), '' = mã KHÔNG có 荷姿 nào → một đơn vị '00' là cả sản phẩm như tên ghi (xốt Barona/HVX).
-- (3) Điều kiện giao hàng có cấu trúc (§5.4): core = bản Claude đọc (nạp theo lô), app.giao_hang_kome = của KOME
--     (một dòng, sửa được, mặc định SUY từ phiếu bán: 配送料500 trên 985 đơn < ¥20,000 · 代引 ¥330 / ¥300 từ ¥20,000).
-- (4) Sổ sửa CHỈ THÊM của sale: dinh_chinh_giao_hang, dinh_chinh_dieu_kien. Không có trong anh_chup._PHIEN_BAN —
--     mọi đường ghi (kome/doi_thu_giao.py) ghi thêm app.doi_thu_nhat_ky CÙNG giao dịch (nếp 064).
-- 059–064 đã chạy trên CSDL thật — không sửa. Chạy bằng postgres qua python db/migrate.py (không SQL Editor — 061).

ALTER TABLE core.fact_gia_doi_thu
    ADD COLUMN so_goi_thung integer       CHECK (so_goi_thung IS NULL OR so_goi_thung > 0),
    ADD COLUMN kl_goi_g     numeric(10,2) CHECK (kl_goi_g IS NULL OR (kl_goi_g > 0 AND kl_goi_g <= 30000)),
    ADD COLUMN bac          jsonb         CHECK (bac IS NULL OR jsonb_typeof(bac) = 'array');
ALTER TABLE app.gia_doi_thu_tay
    ADD COLUMN so_goi_thung integer       CHECK (so_goi_thung IS NULL OR so_goi_thung > 0),
    ADD COLUMN kl_goi_g     numeric(10,2) CHECK (kl_goi_g IS NULL OR (kl_goi_g > 0 AND kl_goi_g <= 30000)),
    ADD COLUMN bac          jsonb         CHECK (bac IS NULL OR jsonb_typeof(bac) = 'array'),
    ADD COLUMN khuyen_mai   text,
    ADD COLUMN gia_truoc_km numeric(12,2) CHECK (gia_truoc_km IS NULL OR gia_truoc_km >= 0);

ALTER TABLE core.dim_product
    ADD COLUMN pack1_code     text,
    ADD COLUMN pack1_base_qty numeric(14,4);

ALTER TABLE app.dinh_chinh_gia DROP CONSTRAINT dinh_chinh_gia_truong_check;
ALTER TABLE app.dinh_chinh_gia ADD CONSTRAINT dinh_chinh_gia_truong_check CHECK (truong IN ('xac_nhan', 'ten_goc',
    'quy_cach_goc', 'gia_goc', 'don_vi_gia', 'kg_moi_don_vi_gia', 'thue', 'gom_ship', 'kenh_gia', 'muc_gia', 'trang_thai',
    'so_goi_thung', 'kl_goi_g', 'bac', 'khuyen_mai', 'gia_truoc_km'));

ALTER TABLE app.doi_thu_nhat_ky DROP CONSTRAINT doi_thu_nhat_ky_loai_check;
ALTER TABLE app.doi_thu_nhat_ky ADD CONSTRAINT doi_thu_nhat_ky_loai_check
    CHECK (loai IN ('xac_nhan', 'sua', 'gia_moi', 'them', 'ghep', 'nhom', 'quy_cach', 'doi_thu', 'thu_muc',
                    'giao_hang', 'dieu_kien'));

-- 'ghi_chu_doc' = câu người đọc tự ghi lúc đọc file ("chép vào ghi_chu…", "không in thông tin thuế") — KHÔNG phải
-- điều kiện của bên; mart.dieu_kien_hien_hanh (068) bỏ loại này (§5.4 "Tách ghi chú nội bộ").
ALTER TABLE core.fact_dieu_kien_doi_thu DROP CONSTRAINT fact_dieu_kien_doi_thu_loai_check;
ALTER TABLE core.fact_dieu_kien_doi_thu ADD CONSTRAINT fact_dieu_kien_doi_thu_loai_check
    CHECK (loai IN ('ship', 'khuyen_mai', 'thanh_toan', 'thue', 'khac', 'ghi_chu_doc'));

CREATE TABLE core.fact_giao_hang_doi_thu (
    id               bigserial PRIMARY KEY,
    batch_id         bigint NOT NULL REFERENCES meta.ingest_batch(batch_id),
    ma_dong          text   NOT NULL,
    ma_doi_thu       text   NOT NULL,
    ngay_nguon       date   NOT NULL,
    bao_ship         boolean,
    phi_ship         numeric(10,2) CHECK (phi_ship IS NULL OR phi_ship >= 0),
    phi_ship_theo    text   CHECK (phi_ship_theo IN ('don', 'thung', 'kien')),
    mien_ship_tu     numeric(12,2) CHECK (mien_ship_tu IS NULL OR mien_ship_tu >= 0),
    mien_ship_kien   integer CHECK (mien_ship_kien IS NULL OR mien_ship_kien > 0),
    thung_moi_kien   integer CHECK (thung_moi_kien IS NULL OR thung_moi_kien > 0),
    phu_phi          jsonb  CHECK (phu_phi IS NULL OR jsonb_typeof(phu_phi) = 'object'),
    phi_daibiki      numeric(10,2) CHECK (phi_daibiki IS NULL OR phi_daibiki >= 0),
    daibiki_tu       numeric(12,2) CHECK (daibiki_tu IS NULL OR daibiki_tu >= 0),
    daibiki_sau      numeric(10,2) CHECK (daibiki_sau IS NULL OR daibiki_sau >= 0),
    ck_mien_daibiki  boolean,
    kien_toi_da_kg   numeric(8,2) CHECK (kien_toi_da_kg IS NULL OR kien_toi_da_kg > 0),
    ghep_kien        text,
    thue             text   CHECK (thue IN ('bao', 'chua', 'khong_ro')),
    cach_gui         text,
    nguon_chu        text,
    nguon_file       text,
    UNIQUE (batch_id, ma_dong)
);
CREATE INDEX fact_giao_hang_doi_thu_ben ON core.fact_giao_hang_doi_thu (ma_doi_thu, batch_id DESC);

CREATE TABLE app.giao_hang_kome (
    id               boolean PRIMARY KEY DEFAULT true CHECK (id),
    bao_ship         boolean,
    phi_ship         numeric(10,2) CHECK (phi_ship IS NULL OR phi_ship >= 0),
    phi_ship_theo    text   CHECK (phi_ship_theo IN ('don', 'thung', 'kien')),
    mien_ship_tu     numeric(12,2) CHECK (mien_ship_tu IS NULL OR mien_ship_tu >= 0),
    mien_ship_kien   integer CHECK (mien_ship_kien IS NULL OR mien_ship_kien > 0),
    thung_moi_kien   integer CHECK (thung_moi_kien IS NULL OR thung_moi_kien > 0),
    phu_phi          jsonb  CHECK (phu_phi IS NULL OR jsonb_typeof(phu_phi) = 'object'),
    phi_daibiki      numeric(10,2) CHECK (phi_daibiki IS NULL OR phi_daibiki >= 0),
    daibiki_tu       numeric(12,2) CHECK (daibiki_tu IS NULL OR daibiki_tu >= 0),
    daibiki_sau      numeric(10,2) CHECK (daibiki_sau IS NULL OR daibiki_sau >= 0),
    ck_mien_daibiki  boolean,
    kien_toi_da_kg   numeric(8,2) CHECK (kien_toi_da_kg IS NULL OR kien_toi_da_kg > 0),
    ghep_kien        text,
    thue             text   CHECK (thue IN ('bao', 'chua', 'khong_ro')),
    cach_gui         text,
    da_xac_nhan      boolean NOT NULL DEFAULT false,
    sua_luc          timestamptz NOT NULL DEFAULT now(),
    sua_boi          bigint REFERENCES app.nguoi_dung(id)
);
INSERT INTO app.giao_hang_kome (bao_ship, phi_ship, phi_ship_theo, mien_ship_tu, phi_daibiki, daibiki_tu, daibiki_sau, thue)
VALUES (false, 500, 'don', 20000, 330, 20000, 300, 'chua');

CREATE TABLE app.dinh_chinh_giao_hang (
    id             bigserial PRIMARY KEY,
    ma_doi_thu     text NOT NULL REFERENCES app.doi_thu(ma),
    truong         text NOT NULL CHECK (truong IN ('bao_ship', 'phi_ship', 'phi_ship_theo', 'mien_ship_tu', 'mien_ship_kien',
                        'thung_moi_kien', 'phu_phi', 'phi_daibiki', 'daibiki_tu', 'daibiki_sau', 'ck_mien_daibiki',
                        'kien_toi_da_kg', 'ghep_kien', 'thue', 'cach_gui')),
    gia_tri_moi    text,                 -- '' = xoá về "không ghi"; jsonb cho phu_phi; 'true'/'false' cho bool
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX dinh_chinh_giao_hang_ben ON app.dinh_chinh_giao_hang (ma_doi_thu, truong, id DESC);

CREATE TABLE app.dinh_chinh_dieu_kien (
    id             bigserial PRIMARY KEY,
    fact_id        bigint,               -- dòng core.fact_dieu_kien_doi_thu được sửa; NULL = điều kiện sale THÊM tay
    ma_doi_thu     text NOT NULL REFERENCES app.doi_thu(ma),
    loai           text NOT NULL CHECK (loai IN ('ship', 'khuyen_mai', 'thanh_toan', 'thue', 'khac')),
    noi_dung       text NOT NULL CHECK (length(btrim(noi_dung)) BETWEEN 1 AND 300),
    bo             boolean NOT NULL DEFAULT false,   -- "không còn đúng — bỏ đi"
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX dinh_chinh_dieu_kien_fact ON app.dinh_chinh_dieu_kien (fact_id, id DESC);

GRANT SELECT, INSERT, UPDATE, DELETE ON core.fact_giao_hang_doi_thu TO kome_ingest;
GRANT SELECT ON core.fact_giao_hang_doi_thu TO kome_app, kome_report;
REVOKE INSERT, UPDATE, DELETE ON core.fact_giao_hang_doi_thu FROM kome_app;
GRANT SELECT, INSERT ON app.dinh_chinh_giao_hang, app.dinh_chinh_dieu_kien TO kome_app;
GRANT USAGE ON SEQUENCE app.dinh_chinh_giao_hang_id_seq, app.dinh_chinh_dieu_kien_id_seq TO kome_app;
REVOKE UPDATE, DELETE ON app.dinh_chinh_giao_hang, app.dinh_chinh_dieu_kien FROM kome_app;
GRANT SELECT, UPDATE ON app.giao_hang_kome TO kome_app;
REVOKE INSERT, DELETE ON app.giao_hang_kome FROM kome_app;
GRANT SELECT ON app.giao_hang_kome, app.dinh_chinh_giao_hang, app.dinh_chinh_dieu_kien TO kome_report, kome_ingest;
```

Kiểm tên ràng buộc trước khi chạy (Postgres đặt `<bảng>_<cột>_check`): `SELECT conname FROM pg_constraint WHERE conrelid = 'app.dinh_chinh_gia'::regclass;`. Tên khác thì sửa lệnh `DROP CONSTRAINT` cho khớp.

Sửa `tests/conftest.py`: dòng mặc định phải sống qua `TRUNCATE` giữa các test.

```python
GIU_LAI = {"meta.schema_migration", "core.dim_date", "core.dim_salesperson",
           "core.dim_prefecture", "app.loai_nguon", "app.doi_thu", "app.giao_hang_kome"}
```

- [ ] **Step 4: Chạy, thấy qua**

Run: `pytest tests/test_doi_thu_bang.py tests/test_migrate.py tests/test_roles.py -q`
Expected: PASS. `test_khong_bang_nao_bat_RLS` vẫn qua.

- [ ] **Step 5: Sinh lại tài liệu sống rồi commit**

```bash
python scripts/sinh_tai_lieu.py && python scripts/sinh_cot_dung.py
pytest tests/test_tai_lieu.py tests/test_cot_dung.py -q
git add db/migrations/065_doi_thu_du_lieu_moi.sql tests/conftest.py tests/test_doi_thu_bang.py kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json
git commit -m "feat(doi-thu): 065 — cot quy cach goi, bac jsonb, pack 荷姿1, bang giao hang, so sua chi them

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Nạp — cột mới, spec `doi_thu_giao_hang`, 荷姿１, 標準価格

**Files:**
- Modify: `config/files.yml` (specs `doi_thu_gia`, `shohin`, `tanka`; thêm `doi_thu_giao_hang` ngay sau `doi_thu_dieu_kien`)
- Modify: `kome/loaders/doi_thu.py`, `kome/loaders/price.py`, `kome/pipeline.py`, `kome/nhat_ky_nap.py`, `kome/kho_du_lieu.py`, `kome/tai_lieu.py`, `kome/san_pham_360.py`
- Test: `tests/test_nap_doi_thu.py`, `tests/test_san_pham_360.py` (hoặc file test đang canh `_bac_gia` — tìm bằng `grep -rn "bac_gia" tests/`), test của `price.load` (tìm bằng `grep -rln "price_level" tests/`)

**Interfaces:**
- Consumes: bảng / cột của Task 1.
- Produces:
  - `kome.loaders.doi_thu.COT_GIA` (thêm `so_goi_thung`, `kl_goi_g`, `bac` vào CUỐI danh sách);
  - `kome.loaders.doi_thu.COT_GIAO_HANG: list[str]`;
  - `kome.loaders.doi_thu.load_giao_hang(conn, df, data_date, batch_id) -> int`;
  - `core.fact_price_list` có dòng `price_level = 'std'`;
  - `core.dim_product.pack1_code` = `''` khi mã không có 荷姿.

- [ ] **Step 1: Viết test hỏng** — thêm vào `tests/test_nap_doi_thu.py`:

```python
from kome.loaders.doi_thu import COT_GIAO_HANG


def test_nap_gia_mang_quy_cach_goi_va_bac_la_json(conn, tmp_path):
    bac = '[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]'
    p = _goi_gia(tmp_path, [_dong(1, so_goi_thung="20", kl_goi_g="500", bac=bac), _dong(2)])
    r = ingest(conn, p, tmp_path / "archive")
    assert r.ok, r.blockers
    rows = conn.execute("SELECT so_goi_thung, kl_goi_g, bac FROM core.fact_gia_doi_thu ORDER BY ma_dong").fetchall()
    assert rows[0][0] == 20 and float(rows[0][1]) == 500
    assert rows[0][2] == [{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]
    assert rows[1] == (None, None, None)          # trống = NULL, không phải 0


def _goi_giao_hang(tmp_path, dong, ngay="20260831"):
    p = tmp_path / f"doi_thu_giao_hang_{ngay}.xlsx"
    pd.DataFrame(dong, columns=COT_GIAO_HANG).to_excel(p, sheet_name="giao_hang", index=False)
    return p


def test_nap_giao_hang_NULL_la_khong_ghi_va_phu_phi_la_json(conn, tmp_path):
    d = {c: None for c in COT_GIAO_HANG}
    d.update(ma_dong="IMAI-00001", ma_doi_thu="IMAI", ngay_nguon="2026-08-31", bao_ship="false", phi_ship="605",
             phi_ship_theo="thung", mien_ship_tu="20000", phu_phi='{"tohoku": 400, "hokkaido": 800}', phi_daibiki="440",
             nguon_chu="Free delivery for over ¥20,000")
    r = ingest(conn, _goi_giao_hang(tmp_path, [d]), tmp_path / "archive")
    assert r.ok, r.blockers
    row = conn.execute("""SELECT bao_ship, phi_ship, phi_ship_theo, mien_ship_tu, phu_phi, phi_daibiki, daibiki_tu, thue
                          FROM core.fact_giao_hang_doi_thu""").fetchone()
    assert row[0] is False and row[1] == 605 and row[2] == "thung" and row[3] == 20000
    assert row[4] == {"tohoku": 400, "hokkaido": 800} and row[5] == 440
    assert row[6] is None and row[7] is None       # không ghi → NULL


def test_hoan_tac_giao_hang_xoa_sach_lo(conn, tmp_path):
    d = {c: None for c in COT_GIAO_HANG}
    d.update(ma_dong="YUMI-00001", ma_doi_thu="YUMI", ngay_nguon="2026-08-31", bao_ship="true")
    r = ingest(conn, _goi_giao_hang(tmp_path, [d]), tmp_path / "archive")
    undo_batch(conn, r.batch_id)
    assert conn.execute("SELECT count(*) FROM core.fact_giao_hang_doi_thu").fetchone()[0] == 0
```

Sửa test cũ `test_mot_o_nap_nhan_ca_hai_loai_file` cho đúng danh sách mới:

```python
def test_mot_o_nap_nhan_ca_ba_loai_file():
    from kome.kho_du_lieu import O_CUA
    assert O_CUA["doi_thu"]["specs"] == ["doi_thu_gia", "doi_thu_dieu_kien", "doi_thu_giao_hang"]
```

Thêm test 標準価格 vào file test đang có của `price.load`. Nếu chưa có file nào thì tạo `tests/test_load_price.py`:

```python
import pandas as pd
from datetime import date
from kome.loaders import price


def _df(**kw):
    d = {"product_code": "NT01", "pack_code": "02", "unit_cost": 4000, "price_ex_std": 0, "price_in_std": 4900}
    for i in range(1, 11):
        d[f"price_ex_{i:02d}"] = 0
        d[f"price_in_{i:02d}"] = 0
    d["price_in_01"] = 5540
    d.update(kw)
    return pd.DataFrame([d])


def test_tieu_chuan_thanh_bac_std_va_bac_trong_bi_bo(conn, batch):
    b = batch(1)
    conn.execute("INSERT INTO core.dim_product (product_code, product_name, batch_id) VALUES ('NT01', 'x', %s)", (b,))
    assert price.load(conn, _df(), date(2026, 9, 8), b) == 2           # 売価No.1 + std, 9 bậc trống bị bỏ
    r = dict(conn.execute("SELECT price_level, price_in_tax FROM core.fact_price_list").fetchall())
    assert r == {"01": 5540, "std": 4900}


def test_khong_co_tieu_chuan_thi_khong_co_dong_std(conn, batch):
    b = batch(1)
    conn.execute("INSERT INTO core.dim_product (product_code, product_name, batch_id) VALUES ('NT01', 'x', %s)", (b,))
    price.load(conn, _df(price_in_std=0), date(2026, 9, 8), b)
    assert conn.execute("SELECT count(*) FROM core.fact_price_list WHERE price_level='std'").fetchone()[0] == 0
```

Thêm test cho `_bac_gia` (Sản phẩm 360):

```python
def test_bac_gia_ghi_nhan_tieu_chuan_va_khuyen_mai_va_luat_hai_cot(conn, batch):
    from kome.san_pham_360 import _bac_gia
    b = batch(1)
    conn.execute("INSERT INTO core.dim_product (product_code, product_name, batch_id) VALUES ('NT01', 'x', %s)", (b,))
    for lv, ex, inc in (("std", 0, 4900), ("01", 5130, 5540), ("10", 5900, 4900)):
        conn.execute("""INSERT INTO core.fact_price_list (product_code, pack_code, price_level, valid_from, price_ex_tax,
                          price_in_tax, unit_cost, batch_id) VALUES ('NT01', '02', %s, '2026-09-08', %s, %s, 0, %s)""",
                     (lv, ex, inc, b))
    conn.commit()
    g = {x["bac"]: x["gia"] for x in _bac_gia(conn, "NT01")}
    assert g == {"標準価格": round(4900 / 1.08), "01": 5130, "10 · khuyến mãi": round(4900 / 1.08)}
    assert [x["bac"] for x in _bac_gia(conn, "NT01")][0] == "標準価格"      # tiêu chuẩn đứng đầu
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_nap_doi_thu.py tests/test_load_price.py -q` (thêm file test `_bac_gia`)
Expected: FAIL (`ImportError: COT_GIAO_HANG`, số dòng tanka sai, nhãn `_bac_gia` sai)

- [ ] **Step 3a: `config/files.yml`**
  - `doi_thu_gia.columns` thêm `so_goi_thung: so_goi_thung, kl_goi_g: kl_goi_g, bac: bac`. KHÔNG thêm vào `money_columns` / `qty_columns`: trống ≠ 0.
  - `shohin.columns` thêm:
    ```yaml
        荷姿１－荷姿区分コード: pack1_code
        荷姿１－基準単位当り荷姿区分数: pack1_base_qty
    ```
    và thêm `pack1_code` vào `code_columns`, để ô trống thành `''` (= "không có 荷姿"). `pack1_base_qty` KHÔNG vào `qty_columns` (trống phải là NULL). Trước khi sửa, đo file thật `raw_archive/shohin/**/商品データ_*.xlsx` mới nhất để chắc hai tiêu đề có đúng như trên (đo 2026-09-29: có; 173/231 mã có 荷姿１).
  - `tanka.columns` thêm `標準価格（税抜）: price_ex_std` và `標準価格（税込）: price_in_std`, hai cột vào `money_columns`.
  - Spec mới (ngay sau `doi_thu_dieu_kien`):
    ```yaml
    doi_thu_giao_hang:
      display_name: Điều kiện giao hàng của đối thủ
      core_table: core.fact_giao_hang_doi_thu
      filename_pattern: '^doi_thu_giao_hang_(?P<date>\d{8})\.xlsx$'
      sheet: giao_hang
      header_row: 1
      min_rows: 1
      keys: [ma_dong]
      columns: {ma_dong: ma_dong, ma_doi_thu: ma_doi_thu, ngay_nguon: ngay_nguon, bao_ship: bao_ship, phi_ship: phi_ship,
                phi_ship_theo: phi_ship_theo, mien_ship_tu: mien_ship_tu, mien_ship_kien: mien_ship_kien,
                thung_moi_kien: thung_moi_kien, phu_phi: phu_phi, phi_daibiki: phi_daibiki, daibiki_tu: daibiki_tu,
                daibiki_sau: daibiki_sau, ck_mien_daibiki: ck_mien_daibiki, kien_toi_da_kg: kien_toi_da_kg,
                ghep_kien: ghep_kien, thue: thue, cach_gui: cach_gui, nguon_chu: nguon_chu, nguon_file: nguon_file}
      code_columns: [ma_dong, ma_doi_thu]
      money_columns: []
      qty_columns: []
      date_columns: [ngay_nguon]
      required_date_columns: [ngay_nguon]
      warn_row_drop_ratio: 0
    ```

- [ ] **Step 3b: `kome/loaders/doi_thu.py`** — thêm cột và bộ nạp:

```python
import json

COT_GIA = [
    "ma_dong", "ma_doi_thu", "ma_hang_dt", "ngay_nguon", "hinh_thuc_nguon", "nguon_file", "vi_tri",
    "ten_goc", "ten_nhat", "jan", "quy_cach_goc", "gia_goc", "don_vi_gia", "kg_moi_don_vi_gia",
    "thue", "gom_ship", "kenh_gia", "muc_gia", "gia_bac", "gia_truoc_km", "trang_thai", "han_su_dung",
    "khuyen_mai", "ma_kome_de_xuat", "nhan_de_xuat", "ly_do_ghep", "do_chac", "ghi_chu",
    "so_goi_thung", "kl_goi_g", "bac",
]
COT_GIAO_HANG = [
    "ma_dong", "ma_doi_thu", "ngay_nguon", "bao_ship", "phi_ship", "phi_ship_theo", "mien_ship_tu", "mien_ship_kien",
    "thung_moi_kien", "phu_phi", "phi_daibiki", "daibiki_tu", "daibiki_sau", "ck_mien_daibiki", "kien_toi_da_kg",
    "ghep_kien", "thue", "cach_gui", "nguon_chu", "nguon_file",
]
_SO = {"gia_goc", "gia_truoc_km", "kg_moi_don_vi_gia", "so_goi_thung", "kl_goi_g",
       "phi_ship", "mien_ship_tu", "mien_ship_kien", "thung_moi_kien", "phi_daibiki", "daibiki_tu", "daibiki_sau",
       "kien_toi_da_kg"}
_JSON = {"bac", "phu_phi"}
_BOOL = {"bao_ship", "ck_mien_daibiki"}


def _json(v):
    s = _chu(v)
    return None if s is None else json.dumps(json.loads(s), ensure_ascii=False)   # gói đã kiểm lược đồ (goi_doi_thu.py)


def _bool(v):
    s = _chu(v)
    if s is None:
        return None
    return {"true": True, "1": True, "co": True, "false": False, "0": False, "khong": False}[s.lower()]


def _gia_tri(cot, v, data_date):
    if cot in _SO:
        return _so(v)
    if cot in _JSON:
        return _json(v)
    if cot in _BOOL:
        return _bool(v)
    if cot == "ngay_nguon":
        return v or data_date
    return _chu(v)


def load_giao_hang(conn: psycopg.Connection, df: pd.DataFrame, data_date: date, batch_id: int) -> int:
    return _nap(conn, "core.fact_giao_hang_doi_thu", COT_GIAO_HANG, df, data_date, batch_id)
```

`_so` trả `Decimal`; cột `integer` nhận `Decimal('20')` được, nhưng `Decimal('20.5')` sẽ lỗi. Gói (Task 3) đã ép số nguyên.

- [ ] **Step 3c: đăng ký spec mới ở mọi danh mục**
  - `kome/pipeline.py`: `LOADERS["doi_thu_giao_hang"] = doi_thu.load_giao_hang`, `UNDO_TABLES["doi_thu_giao_hang"] = ["core.fact_giao_hang_doi_thu"]`. `LOADERS["shohin"]` thêm `"pack1_code", "pack1_base_qty"` vào CUỐI danh sách cột của `make_loader`.
  - `kome/nhat_ky_nap.py`: `BANG_THEO_LOAI["doi_thu_giao_hang"] = ["core.fact_giao_hang_doi_thu"]`, `TEN_BANG_VI` (dòng ~96) thêm `"doi_thu_giao_hang": "điều kiện giao hàng của đối thủ"`.
  - `kome/kho_du_lieu.py`: ô `doi_thu` → `"specs": ["doi_thu_gia", "doi_thu_dieu_kien", "doi_thu_giao_hang"]`.
  - `kome/tai_lieu.py` (dòng ~34): thêm `"doi_thu_giao_hang": "điều kiện giao hàng của đối thủ (đi cùng gói bảng giá đối thủ)"`.
  - `kome/nguon_dung.py` / `scripts/sinh_cot_dung.py`: nếu test đỏ vì loại file mới chưa khai, khai như `doi_thu_dieu_kien`.

- [ ] **Step 3d: `kome/loaders/price.py`**

```python
PRICE_LEVELS = [f"{i:02d}" for i in range(1, 11)] + ["std"]   # '01'..'10' = 売価No.1..10 · 'std' = 標準価格
```

Vòng lặp đọc `getattr(r, f"price_ex_{level}")` giữ nguyên: cột đổi tên là `price_ex_std` / `price_in_std`. Sửa docstring đầu file: "20 cột giá … + 2 cột 標準価格 → `price_level = 'std'`".

- [ ] **Step 3e: `kome/san_pham_360.py::_bac_gia`**

```python
NHAN_BAC = {"std": "標準価格", "10": "10 · khuyến mãi"}   # 売価No.10 = giá khuyến mãi (chủ DN 2026-09-29) — cùng luật mart.la_gia_km_kome


def _bac_gia(conn, ma: str) -> list[dict]:
    """Giá theo bậc — dòng MỚI NHẤT mỗi (bậc, quy cách). 1 lượt hỏi. 標準価格 đứng đầu.
    Giá chưa thuế: cột chưa thuế nếu > 0 và không mâu thuẫn cột gồm thuế; không thì gồm thuế ÷ 1,08
    (cùng luật mart.gia_kome_bang, 066)."""
    rows = conn.execute(
        """SELECT DISTINCT ON (price_level, pack_code)
                  price_level, pack_code, price_ex_tax, price_in_tax, valid_from
           FROM core.fact_price_list WHERE product_code = %s
           ORDER BY price_level, pack_code, valid_from DESC""", (ma,)).fetchall()
    def gia(ex, inc):
        return int(ex) if ex > 0 and not (0 < inc < ex) else round(inc / 1.08)
    ra = [{"bac": NHAN_BAC.get(g[0], g[0]), "quy_cach": QUY_CACH.get(g[1], g[1]), "pack_code": g[1],
           "gia": gia(g[2], g[3]), "tu_ngay": g[4]} for g in rows]
    return sorted(ra, key=lambda x: (x["bac"] != "標準価格",))
```

(`sorted` giữ ổn định thứ tự `ORDER BY` cho các bậc còn lại.) Bỏ lời giải thích cũ nếu mâu thuẫn; giữ đoạn chú thích về `DISTINCT ON`.

- [ ] **Step 4: Chạy, thấy qua**

Run: `pytest tests/test_nap_doi_thu.py tests/test_load_price.py tests/test_pipeline.py tests/test_nhat_ky_nap.py tests/test_kho_du_lieu.py tests/test_san_pham_360.py -q` (bỏ tên file không tồn tại). Sau đó chạy `pytest -q -k "dang_ky or loader or files_yml or core_table"` để bắt test canh danh mục.
Expected: PASS

- [ ] **Step 5: Sinh lại tài liệu sống, commit**

```bash
python scripts/sinh_tai_lieu.py && python scripts/sinh_cot_dung.py
pytest tests/test_tai_lieu.py tests/test_cot_dung.py -q
git add -A config/files.yml kome tests kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json
git commit -m "feat(doi-thu): nap cot quy cach goi + bac, spec doi_thu_giao_hang, 荷姿1 cua 商品データ, 標準価格 = bac std

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Gói — cột mới, kiểm bậc, luật giá lẻ, file giao hàng, tách ghi chú của người đọc

**Files:**
- Modify: `scripts/goi_doi_thu.py`
- Test: `tests/test_goi_doi_thu.py`

**Interfaces:**
- Consumes: `COT_GIA`, `COT_GIAO_HANG`, `COT_DIEU_KIEN` (Task 2).
- Produces:
  - `dung_goi(gia, dk, ngay, giao=None) -> tuple[list[dict], list[dict], list[dict], list[str]]` — thêm tham số `giao` (dòng CSV giao hàng) và phần tử kết quả thứ ba (dòng `COT_GIAO_HANG`). **Đổi chữ ký**: mọi chỗ gọi `dung_goi` (test cũ, `main`) sửa theo;
  - `kiem_bac(s) -> tuple[list[dict] | None, str | None]` (bậc đã chuẩn hoá, lý do lỗi);
  - `la_ghi_chu_doc(noi_dung) -> bool`.

- [ ] **Step 1: Viết test hỏng** — thêm vào `tests/test_goi_doi_thu.py` (dùng dict tối thiểu như test hiện có của file; hàm `_d(**kw)` dưới đây dựng một dòng CSV giá):

```python
from scripts.goi_doi_thu import dung_goi, kiem_bac, la_ghi_chu_doc
from datetime import date


def _d(**kw):
    d = {"ben": "NEXT", "file": "NEXT.pdf", "vi_tri": "tr1", "ten_goc": "CÁ BASA", "quy_cach_goc": "500g×20袋",
         "gia_goc": "5500", "don_vi_gia": "thung", "kg_moi_don_vi_gia": "10", "thue": "chua", "trang_thai": "con"}
    d.update(kw)
    return d


def test_kiem_bac_chuan_hoa_va_bat_loi():
    ok, loi = kiem_bac('[{"tu": 5, "don_vi_sl": "thung", "gia": "5,300", "don_vi_gia": "thung"}]')
    assert loi is None and ok == [{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]
    assert kiem_bac("") == (None, None)
    for xau in ('{"tu": 5}', '[{"tu": 0, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "kg"}]',
                '[{"tu": 5, "don_vi_sl": "hop", "gia": 1, "don_vi_gia": "kg"}]', "khong phai json",
                "[" + ",".join(['{"tu": 1, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "kg"}'] * 11) + "]"):
        b, loi = kiem_bac(xau)
        assert b is None and loi, xau


def test_goi_mang_quy_cach_va_bac_va_so_nguyen():
    g, _, _, canh = dung_goi([_d(so_goi_thung="20", kl_goi_g="500",
                                bac='[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]')], [], date(2026, 8, 31))
    assert g[0]["so_goi_thung"] == 20 and g[0]["kl_goi_g"] == 500.0
    assert g[0]["bac"] == '[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]'
    assert g[0]["do_chac"] == "chac" and not canh


def test_gia_goc_phai_la_gia_le_khong_duoc_re_hon_bac():
    # AI ghi bậc rẻ nhất (5.300) vào gia_goc còn bậc lẻ (5.500) nằm trong bac → cần xem
    g, _, _, canh = dung_goi([_d(gia_goc="5300",
                                bac='[{"tu": 1, "don_vi_sl": "thung", "gia": 5500, "don_vi_gia": "thung"}]')], [], date(2026, 8, 31))
    assert g[0]["do_chac"] == "can_xem" and "giá lẻ" in g[0]["ghi_chu"]


def test_bac_hong_thi_can_xem_khong_chan_ca_goi():
    g, _, _, canh = dung_goi([_d(bac="5cs: 5,300"), _d(vi_tri="tr2", ten_goc="Khác")], [], date(2026, 8, 31))
    assert g[0]["bac"] is None and g[0]["do_chac"] == "can_xem" and len(g) == 2


def test_ghi_chu_cua_nguoi_doc_thanh_loai_ghi_chu_doc():
    assert la_ghi_chu_doc("mỗi mặt hàng in 'Kiện 1th' … — chép vào ghi_chu từng dòng; không in phí ship")
    assert la_ghi_chu_doc("Dữ liệu này KHÔNG có phí ship chung, vùng giao hay đơn tối thiểu")
    assert la_ghi_chu_doc("Không tìm thấy phí ship / ngưỡng miễn ship trên các trang đã đọc")
    assert not la_ghi_chu_doc("Kiện 28kg ghép 3 sản phẩm - bao thuế bao ship!")
    _, dk, _, _ = dung_goi([], [{"ben": "VIETCOOK", "file": "v.pdf", "loai": "ship",
                                  "noi_dung": "chép vào ghi_chu từng dòng; không in phí ship"}], date(2026, 8, 31))
    assert dk[0]["loai"] == "ghi_chu_doc"


def test_goi_giao_hang_ep_kieu_va_kiem_phu_phi():
    _, _, gh, canh = dung_goi([], [], date(2026, 8, 31), giao=[
        {"ben": "IMAI", "file": "imai.pdf", "bao_ship": "false", "phi_ship": "605", "phi_ship_theo": "thung",
         "mien_ship_tu": "20,000", "phu_phi": '{"tohoku": 400, "hokkaido": 800}', "phi_daibiki": "440",
         "nguon_chu": "Free delivery for over ¥20,000"},
        {"ben": "VIETNAM-HOUSE", "file": "vh.pdf", "phu_phi": '{"okinawa": "x"}'}])
    assert gh[0]["ma_dong"] == "IMAI-00001" and gh[0]["mien_ship_tu"] == 20000.0 and gh[0]["phi_ship_theo"] == "thung"
    assert gh[0]["phu_phi"] == '{"tohoku": 400, "hokkaido": 800}'
    assert gh[1]["phu_phi"] is None and any("phu_phi" in c for c in canh)   # chỉ nhận số ¥ hoặc "khong_nhan"
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_goi_doi_thu.py -q`
Expected: FAIL (`ImportError: kiem_bac`; test cũ vỡ vì `dung_goi` trả 4 phần tử — sửa luôn các test cũ: `g, d, canh = dung_goi(...)` → `g, d, _, canh = dung_goi(...)`)

- [ ] **Step 3: Sửa `scripts/goi_doi_thu.py`**

Thêm vào đầu file (sau các `import`):

```python
import json
from kome.loaders.doi_thu import COT_GIA, COT_DIEU_KIEN, COT_GIAO_HANG  # noqa: E402

DON_VI_SL = ("thung", "kg", "goi", "pallet")
DON_VI_GIA_BAC = ("thung", "kg", "goi")
BAC_TOI_DA = 10
# Câu người ĐỌC tự ghi (không phải điều kiện của bên) — tháng 8 lọt vào dieu_kien (VIETCOOK, HSC, JVB, EIHATSU, THAK).
_GHI_CHU_DOC = re.compile(r"chép vào|ghi_chu|không in (phí|thông tin)|không tìm thấy|dữ liệu này|trên các trang đã đọc"
                          r"|in ở từng ô|mỗi (ô|mặt hàng) (ghi|in)|— không chép", re.I)
_VUNG = ("hokkaido", "tohoku", "kanto", "chubu", "kansai", "chugoku", "shikoku", "kyushu", "okinawa")


def la_ghi_chu_doc(noi_dung: str) -> bool:
    return bool(_GHI_CHU_DOC.search(noi_dung or ""))


def kiem_bac(s) -> tuple[list[dict] | None, str | None]:
    """Chữ JSON của cột `bac` → danh sách bậc chuẩn hoá (lược đồ 065) hoặc (None, lý do). Trống → (None, None)."""
    if s is None or str(s).strip() == "":
        return None, None
    try:
        v = json.loads(s)
    except (TypeError, ValueError):
        return None, f"bac không phải JSON: {str(s)[:40]}"
    if not isinstance(v, list) or not 1 <= len(v) <= BAC_TOI_DA:
        return None, f"bac phải là mảng 1–{BAC_TOI_DA} bậc"
    ra = []
    for b in v:
        if not isinstance(b, dict):
            return None, "mỗi bậc phải là object"
        tu, gia = _so(b.get("tu")), _so(b.get("gia"))
        if not tu or tu <= 0 or not gia or gia <= 0:
            return None, "bậc cần tu > 0 và gia > 0"
        if b.get("don_vi_sl") not in DON_VI_SL or b.get("don_vi_gia") not in DON_VI_GIA_BAC:
            return None, f"đơn vị bậc phải thuộc {DON_VI_SL} / {DON_VI_GIA_BAC}"
        ra.append({"tu": int(tu) if tu == int(tu) else tu, "don_vi_sl": b["don_vi_sl"],
                   "gia": int(gia) if gia == int(gia) else gia, "don_vi_gia": b["don_vi_gia"]})
    return ra, None


def _nguyen(v):
    x = _so(v)
    return int(x) if x is not None and x == int(x) and x > 0 else None


def _phu_phi(s) -> tuple[str | None, str | None]:
    if s is None or str(s).strip() == "":
        return None, None
    try:
        v = json.loads(s)
    except (TypeError, ValueError):
        return None, "phu_phi không phải JSON"
    if not isinstance(v, dict) or any(k not in _VUNG for k in v) or \
            any(not (x == "khong_nhan" or (isinstance(x, (int, float)) and x >= 0)) for x in v.values()):
        return None, 'phu_phi: {"<vùng>": ¥ hoặc "khong_nhan"}, vùng thuộc ' + "/".join(_VUNG)
    return json.dumps(v, ensure_ascii=False), None
```

Trong `dung_goi`, sau khi dựng `ly_do` và TRƯỚC khi tính `do_chac`, thêm đoạn kiểm bậc và giá lẻ:

```python
        bac, loi_bac = kiem_bac(d.get("bac"))
        if loi_bac:
            ly_do.append(loi_bac)
        if bac and g is not None:
            cung_dv = [b["gia"] for b in bac if b["don_vi_gia"] == (d.get("don_vi_gia") or "")]
            if cung_dv and max(cung_dv) > g:
                ly_do.append("gia_goc phải là giá lẻ (bậc mua ít nhất), không phải bậc rẻ nhất")
```

Trong dict `o`, thêm:

```python
            "so_goi_thung": _nguyen(d.get("so_goi_thung")),
            "kl_goi_g": _so(d.get("kl_goi_g")) if (_so(d.get("kl_goi_g")) or 0) > 0 else None,
            "bac": json.dumps(bac, ensure_ascii=False) if bac else None,
```

Trong vòng điều kiện:

```python
        loai = d.get("loai") if d.get("loai") in ("ship", "khuyen_mai", "thanh_toan", "thue", "khac") else "khac"
        if la_ghi_chu_doc(d.get("noi_dung")):
            loai = "ghi_chu_doc"
```

Đổi chữ ký và thêm phần giao hàng ở cuối `dung_goi`:

```python
def dung_goi(gia: list[dict], dk: list[dict], ngay: date, giao: list[dict] | None = None
             ) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    ...
    gh_ra, dem_gh = [], {}
    for d in giao or []:
        ben = d["ben"]
        dem_gh[ben] = dem_gh.get(ben, 0) + 1
        pp, loi = _phu_phi(d.get("phu_phi"))
        if loi:
            canh.append(f"{ben} giao hàng: {loi}")
        theo = d.get("phi_ship_theo") if d.get("phi_ship_theo") in ("don", "thung", "kien") else None
        thue = d.get("thue") if d.get("thue") in ("bao", "chua", "khong_ro") else None
        gh_ra.append({
            "ma_dong": f"{ben}-{dem_gh[ben]:05d}", "ma_doi_thu": ben,
            "ngay_nguon": suy_ngay(d.get("file") or "", ngay).isoformat(),
            "bao_ship": d.get("bao_ship") or None, "phi_ship": _so(d.get("phi_ship")), "phi_ship_theo": theo,
            "mien_ship_tu": _so(d.get("mien_ship_tu")), "mien_ship_kien": _nguyen(d.get("mien_ship_kien")),
            "thung_moi_kien": _nguyen(d.get("thung_moi_kien")), "phu_phi": pp, "phi_daibiki": _so(d.get("phi_daibiki")),
            "daibiki_tu": _so(d.get("daibiki_tu")), "daibiki_sau": _so(d.get("daibiki_sau")),
            "ck_mien_daibiki": d.get("ck_mien_daibiki") or None, "kien_toi_da_kg": _so(d.get("kien_toi_da_kg")),
            "ghep_kien": d.get("ghep_kien") or None, "thue": thue, "cach_gui": d.get("cach_gui") or None,
            "nguon_chu": d.get("nguon_chu") or None, "nguon_file": d.get("file") or None,
        })
    return ra, [x for x in dk_ra if (x["noi_dung"] or "").strip()], gh_ra, canh
```

`main()`: gom thêm file `spike_*_giao_hang.csv` vào `giao` (sửa điều kiện `p.stem.endswith(...)`: `_dieu_kien` → dk, `_giao_hang` → giao, còn lại → giá). Ghi thêm `doi_thu_giao_hang_{s}.xlsx`, sheet `giao_hang`, cột `COT_GIAO_HANG`, chỉ khi có dòng. In số dòng giao hàng. Docstring đầu file thêm file thứ ba.

- [ ] **Step 4: Chạy, thấy qua**

Run: `pytest tests/test_goi_doi_thu.py tests/test_nap_doi_thu.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/goi_doi_thu.py tests/test_goi_doi_thu.py
git commit -m "feat(doi-thu): goi — quy cach goi, kiem bac, gia_goc = gia le, file giao hang, tach ghi chu nguoi doc

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Migration 066 — kg KOME theo quy cách OBC, bảng giá KOME (標準価格, 売価No, khuyến mãi)

**Files:**
- Create: `db/migrations/066_mart_kome_quy_cach_bang_gia.sql`
- Test: `tests/test_mart_doi_thu.py`

**Interfaces:**
- Consumes: `core.dim_product.pack1_*`, `core.fact_price_list` dòng `'std'` (Task 1–2).
- Produces:
  - `mart.quy_cach_kome` thêm cột CUỐI `kg_00`, `kg_02` (kg của MỘT đơn vị pack `00` / `02`);
  - `mart.gia_kome_kg` (cùng cột, dùng `kg_00` / `kg_02`);
  - `mart.la_gia_km_kome(text) -> boolean`;
  - view `mart.gia_kome_bang(product_code, price_level, pack_code, gia_chua_thue, yen_kg, hai_cot_lech)`;
  - `mart.gia_kome_chuan(p_ma text) -> numeric` (¥/kg chưa thuế, NULL nếu không có).

- [ ] **Step 1: Viết test hỏng** — thêm vào `tests/test_mart_doi_thu.py`:

```python
def _hang_pack(conn, batch, ma, ten, pack1_code, pack1_base_qty=None):
    b = batch(9002)
    conn.execute("""INSERT INTO core.dim_product (product_code, product_name, food_category_name, pack1_code, pack1_base_qty, batch_id)
                    VALUES (%s, %s, '調味料_VNM', %s, %s, %s)""", (ma, ten, pack1_code, pack1_base_qty, b))
    conn.commit()


def _kg(conn, ma):
    r = conn.execute("SELECT kg_00, kg_02 FROM mart.quy_cach_kome WHERE product_code=%s", (ma,)).fetchone()
    return tuple(None if x is None else float(x) for x in r)


def test_066_kg_theo_hanh_dong_goi_OBC(conn, batch):
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")      # không 荷姿: 00 = cả sản phẩm
    _hang_pack(conn, batch, "DK20", "Ngu Vi Huong 3g (3g x 100 pack x 4 boxes)", "02", 400)   # 02 = 400 × 00
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _hang(conn, batch, "NT09", "Ca X (500g x 20 packs)")                                      # chưa nạp 荷姿 → luật cũ
    assert _kg(conn, "BA02") == (pytest.approx(6.4), pytest.approx(6.4))
    assert _kg(conn, "DK20") == (pytest.approx(0.003), pytest.approx(1.2))
    assert _kg(conn, "NT01") == (pytest.approx(0.5), pytest.approx(10))
    assert _kg(conn, "NT09") == (pytest.approx(0.5), pytest.approx(10))


def test_066_gia_kome_kg_ma_ban_bang_00_la_ca_thung(conn, batch):
    """15 nhóm lệch (đo 2026-09-29): xốt Barona bán bằng '00' mà một '00' là cả thùng 6,4 kg."""
    import pandas as pd
    from kome.loaders import sales
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")
    b = batch(9003, HOM_NAY)
    # Cùng hình dạng dòng như tests/test_khach_hang.py::_mua, nhưng pack '00', qty 1, doanh thu thuần ¥6.266.
    sales.load(conn, pd.DataFrame([{
        "slip_no": "SBA02", "line_seq": 1, "sales_date": HOM_NAY, "customer_code": "202601010001",
        "product_code": "BA02", "pack_code": "00", "case_qty": 0, "qty": 1, "unit_price": 6266, "unit_cost": 5000,
        "amount": 6266, "tax_amount": 0, "cost": 5000, "gross_profit": 1266, "paid_amount": 0, "batch_id": b,
    }]), HOM_NAY, b)
    conn.commit()
    y = conn.execute("SELECT yen_kg FROM mart.gia_kome_kg WHERE product_code='BA02'").fetchone()[0]
    assert float(y) == pytest.approx(6266 / 6.4, rel=1e-6)      # ¥979/kg — KHÔNG phải ¥78.325/kg (coi '00' = 80g)
```

```python
def _bang_gia(conn, batch, ma, lv, ex, inc, pack="02"):
    b = batch(9100 + len(lv) + ex % 97)
    conn.execute("""INSERT INTO core.fact_price_list (product_code, pack_code, price_level, valid_from, price_ex_tax,
                      price_in_tax, unit_cost, batch_id) VALUES (%s, %s, %s, '2026-09-08', %s, %s, 0, %s)""",
                 (ma, pack, lv, ex, inc, b))
    conn.commit()


def test_066_gia_kome_chuan_va_luat_hai_cot(conn, batch):
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _bang_gia(conn, batch, "NT01", "std", 0, 4900)          # chỉ có gồm thuế → ÷ 1,08
    _bang_gia(conn, batch, "NT01", "01", 5130, 5540)        # hai cột khớp → chưa thuế
    _bang_gia(conn, batch, "NT01", "10", 5900, 4900)        # gồm thuế < chưa thuế → mâu thuẫn → gồm thuế ÷ 1,08
    assert float(conn.execute("SELECT mart.gia_kome_chuan('NT01')").fetchone()[0]) == pytest.approx(4900 / 1.08 / 10)
    r = {x[0]: (float(x[1]), x[2]) for x in conn.execute(
        "SELECT price_level, yen_kg, hai_cot_lech FROM mart.gia_kome_bang WHERE product_code='NT01'")}
    assert r["01"] == (pytest.approx(513), False)
    assert r["10"] == (pytest.approx(4900 / 1.08 / 10), True)
    assert conn.execute("SELECT mart.la_gia_km_kome('10'), mart.la_gia_km_kome('01'), mart.la_gia_km_kome('std')").fetchone() \
        == (True, False, False)
    assert conn.execute("SELECT mart.gia_kome_chuan('KHONG_CO')").fetchone()[0] is None


def test_066_bang_gia_ma_chi_co_00_dung_kg_00(conn, batch):
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")
    _bang_gia(conn, batch, "BA02", "std", 0, 6804, pack="00")
    assert float(conn.execute("SELECT mart.gia_kome_chuan('BA02')").fetchone()[0]) == pytest.approx(6804 / 1.08 / 6.4)
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_mart_doi_thu.py -q -k 066`
Expected: FAIL (`column "kg_00" does not exist`, function không tồn tại)

- [ ] **Step 3: Viết migration** `db/migrations/066_mart_kome_quy_cach_bang_gia.sql`:

```sql
-- 066 — KOME: kg của MỘT đơn vị theo 荷姿 của OBC + bảng giá KOME (đặc tả giao diện mới §5.3, §6.3).
-- Đo 2026-09-29: 15 nhóm có giá KOME > 3× trung vị (xốt Barona ¥78,403/kg vs ¥845). Các mã đó KHÔNG có 荷姿 nào ở
-- 商品データ (pack1_code = '') và bán bằng '00' — một '00' là CẢ sản phẩm như tên ghi (80g × 20 × 4 = 6,4 kg), còn 060
-- coi '00' = một gói 80g. Có 荷姿１ thì '02' = pack1_base_qty × '00' (Ngũ vị hương 3g: 400 × 3g = 1,2 kg; 060 tách
-- tên "3g x 100 pack x 4 boxes" ra 0,3 kg). pack1_code NULL (chưa nạp lại 商品データ bản có cột) → giữ luật 060.
-- Tên dạng ba thừa số "a g x b x c" → kg_moi_thung = a × b × c (người sửa ở app.quy_cach_kome vẫn thắng).
-- CREATE OR REPLACE: cột cũ giữ nguyên thứ tự, kg_00 / kg_02 thêm ở CUỐI.

CREATE OR REPLACE VIEW mart.quy_cach_kome AS
WITH t AS (
    SELECT p.product_code, nullif(p.pack1_code, '') AS pack1, p.pack1_code = '' AS khong_hanh, p.pack1_base_qty,
           regexp_match(p.product_name, '(\d+(?:[.,]\d+)?)\s*(kg|gr|g)\s*[x×*]\s*(\d+)', 'i') AS m1,
           regexp_match(p.product_name, '(\d+(?:[.,]\d+)?)\s*kg\s*/\s*case', 'i')             AS m2,
           regexp_match(p.product_name, '(\d+(?:[.,]\d+)?)\s*(kg|gr|g)\s*[x×*]\s*(\d+)\s*[[:alpha:]]*\s*[x×*]\s*(\d+)', 'i') AS m3
    FROM core.dim_product p
),
q AS (
    SELECT t.*, o.product_code IS NOT NULL AS da_sua,
           coalesce(o.kg_moi_goi, CASE WHEN t.m1 IS NOT NULL THEN replace(t.m1[1], ',', '.')::numeric
                                       / CASE WHEN lower(t.m1[2]) = 'kg' THEN 1 ELSE 1000 END END) AS kg_moi_goi,
           coalesce(o.goi_moi_thung, t.m1[3]::numeric)                                            AS goi_moi_thung,
           coalesce(o.kg_moi_thung, replace(t.m2[1], ',', '.')::numeric,
                    CASE WHEN t.m3 IS NOT NULL THEN replace(t.m3[1], ',', '.')::numeric
                         / CASE WHEN lower(t.m3[2]) = 'kg' THEN 1 ELSE 1000 END
                         * t.m3[3]::numeric * t.m3[4]::numeric END)                                AS kg_moi_thung,
           o.kg_moi_thung IS NOT NULL                                                              AS thung_nguoi_sua
    FROM t LEFT JOIN app.quy_cach_kome o USING (product_code)
)
SELECT q.product_code, q.kg_moi_goi, q.goi_moi_thung, q.kg_moi_thung, q.da_sua,
       CASE WHEN q.khong_hanh THEN coalesce(q.kg_moi_thung, q.kg_moi_goi * q.goi_moi_thung)
            ELSE q.kg_moi_goi END                                                                 AS kg_00,
       CASE WHEN NOT q.thung_nguoi_sua AND q.pack1 = '02' AND q.pack1_base_qty > 0 AND q.kg_moi_goi IS NOT NULL
            THEN q.kg_moi_goi * q.pack1_base_qty
            ELSE coalesce(q.kg_moi_thung, q.kg_moi_goi * q.goi_moi_thung) END                     AS kg_02
FROM q;

CREATE OR REPLACE VIEW mart.gia_kome_kg AS
SELECT f.product_code,
       sum(f.amount - f.tax_amount)                                AS doanh_thu,
       sum(f.qty * k.kg)                                           AS kg_ban,
       sum(f.amount - f.tax_amount) / nullif(sum(f.qty * k.kg), 0) AS yen_kg
FROM mart.ban_den_moc f
CROSS JOIN mart.moc_thoi_gian m
JOIN mart.quy_cach_kome q ON q.product_code = f.product_code
CROSS JOIN LATERAL (SELECT CASE f.pack_code WHEN '02' THEN q.kg_02 WHEN '00' THEN q.kg_00 END AS kg) k
WHERE f.sales_date > m.hom_nay - 90 AND k.kg IS NOT NULL
GROUP BY f.product_code;

-- 売価No.10 = giá KHUYẾN MÃI của KOME (chủ DN 2026-09-29). ĐỊNH NGHĨA MỘT LẦN; kome/san_pham_360.py::NHAN_BAC chép nhãn.
CREATE FUNCTION mart.la_gia_km_kome(p_level text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$ SELECT p_level = '10' $$;

-- Bảng giá KOME quy về ¥/kg chưa thuế, bản mới nhất ≤ mốc (040) mỗi (mã, bậc, quy cách). Luật hai cột: chưa thuế nếu > 0
-- và KHÔNG mâu thuẫn (gồm thuế > 0 mà nhỏ hơn chưa thuế); không thì gồm thuế ÷ 1,08. Mỗi (mã, bậc) một dòng: ưu tiên
-- quy cách '02' khi biết kg, không thì '00'.
CREATE VIEW mart.gia_kome_bang AS
WITH m AS (
    SELECT DISTINCT ON (product_code, pack_code, price_level) product_code, pack_code, price_level, price_ex_tax, price_in_tax
    FROM core.fact_price_list
    WHERE valid_from <= coalesce(mart.moc_lui(), 'infinity'::date) AND (price_ex_tax > 0 OR price_in_tax > 0)
    ORDER BY product_code, pack_code, price_level, valid_from DESC
),
g AS (
    SELECT m.product_code, m.price_level, m.pack_code,
           CASE WHEN m.price_ex_tax > 0 AND NOT (m.price_in_tax > 0 AND m.price_in_tax < m.price_ex_tax)
                THEN m.price_ex_tax::numeric ELSE m.price_in_tax / 1.08 END                  AS gia_chua_thue,
           (m.price_ex_tax > 0 AND m.price_in_tax > 0 AND m.price_in_tax < m.price_ex_tax)    AS hai_cot_lech,
           CASE m.pack_code WHEN '02' THEN q.kg_02 WHEN '00' THEN q.kg_00 END                 AS kg
    FROM m JOIN mart.quy_cach_kome q USING (product_code)
)
SELECT DISTINCT ON (product_code, price_level) product_code, price_level, pack_code, gia_chua_thue,
       gia_chua_thue / kg AS yen_kg, hai_cot_lech
FROM g WHERE kg > 0
ORDER BY product_code, price_level, (pack_code = '02') DESC;

CREATE FUNCTION mart.gia_kome_chuan(p_ma text) RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT yen_kg FROM mart.gia_kome_bang WHERE product_code = p_ma AND price_level = 'std'
$$;

GRANT SELECT ON mart.quy_cach_kome, mart.gia_kome_kg, mart.gia_kome_bang TO kome_app, kome_report, kome_ingest;
GRANT EXECUTE ON FUNCTION mart.la_gia_km_kome(text), mart.gia_kome_chuan(text) TO kome_app, kome_report, kome_ingest;
```

- [ ] **Step 4: Chạy, thấy qua**

Run: `pytest tests/test_mart_doi_thu.py tests/test_doi_thu.py tests/test_doi_thu_api.py -q`
Expected: PASS. Test quy cách cũ (`test_quy_cach_*`, `test_gia_kome_kg_*`) vẫn qua vì `_hang` không đặt `pack1_code` (NULL → luật 060).

- [ ] **Step 5: Sinh lại tài liệu sống, commit**

```bash
python scripts/sinh_tai_lieu.py && python scripts/sinh_cot_dung.py
git add db/migrations/066_mart_kome_quy_cach_bang_gia.sql tests/test_mart_doi_thu.py kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json
git commit -m "feat(doi-thu): 066 — kg KOME theo 荷姿 OBC (sua 15 nhom lech), bang gia KOME ¥/kg, 標準価格, 売価No.10 = KM

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Migration 067 — quan sát đối thủ: quy cách gói, giá tại 1 / 5 / 10 thùng / pallet, KOME chuẩn ở So sánh

**Files:**
- Create: `db/migrations/067_mart_quan_sat_gia_bac.sql`
- Test: `tests/test_mart_doi_thu.py`

**Interfaces:**
- Consumes:
  - cột `so_goi_thung`, `kl_goi_g`, `bac` (Task 1);
  - `dinh_chinh_gia.truong` mới;
  - `mart.gia_kome_chuan`, `mart.gia_kome_bang`, `mart.la_gia_km_kome` (Task 4).
- Produces:
  - `mart.gia_bac_kg(p_bac jsonb, p_sl numeric, p_pallet boolean, p_kg_thung numeric, p_so_goi integer, p_kl_goi numeric, p_thue text) -> numeric`;
  - `mart.gia_doi_thu_quan_sat` thêm ở CUỐI: `so_goi_thung, kl_goi_g, bac, kg_thung_dt, gia_goi, gia_thung, gia_1, gia_5, gia_10, gia_pallet`; `khuyen_mai`, `gia_truoc_km` giờ áp đính chính (sửa được, xoá được bằng `''`);
  - `mart.gia_doi_thu_hien_hanh`: tạo lại, như 060 (`q.*` + ba cột);
  - `mart.so_sanh_nhom`: tạo lại, cột của 062 giữ nguyên thứ tự, thêm ở CUỐI `gia_kome_chuan numeric`, `gia_kome_bang jsonb` ({bậc: ¥/kg}, bỏ `std`), `gia_kome_km numeric` (売価No.10 khi thấp hơn chuẩn). `ty_le_re_hon_kome` so với `coalesce(gia_kome_chuan, gia_kome)`.

- [ ] **Step 1: Viết test hỏng** — thêm vào `tests/test_mart_doi_thu.py`:

```python
import json


def _qs_bac(conn, batch, ben, gia_goc, don_vi, kg, bac, thue="chua", so_goi=None, kl_goi=None, muc=None):
    b = batch(abs(hash((ben, gia_goc, str(bac)))) % 50_000 + 60_000)
    r = conn.execute(
        """INSERT INTO core.fact_gia_doi_thu (batch_id, ma_dong, ma_doi_thu, ma_hang_dt, ngay_nguon, hinh_thuc_nguon,
             ten_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, trang_thai, ma_kome_de_xuat, nhan_de_xuat,
             do_chac, bac, so_goi_thung, kl_goi_g, muc_gia)
           VALUES (%s, 'x-1', %s, %s, '2026-08-20', 'file', 'Basa', %s, %s, %s, %s, 'khong_ro', 'con', 'NT01', 'cung_hang',
                   'chac', %s, %s, %s, %s) RETURNING id""",
        (b, ben, f"ten:basa|{ben}", gia_goc, don_vi, kg, thue, json.dumps(bac) if bac is not None else None,
         so_goi, kl_goi, muc)).fetchone()[0]
    conn.commit()
    return r


def _gia(conn, fid):
    r = conn.execute("""SELECT gia_1, gia_5, gia_10, gia_pallet, kg_thung_dt, gia_goi, gia_thung
                        FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s""", (fid,)).fetchone()
    return tuple(None if x is None else float(x) for x in r)


def test_067_gia_tai_so_luong_theo_bac_thung(conn, batch):
    _hang(conn, batch)
    fid = _qs_bac(conn, batch, "NEXT", 5500, "thung", 10,
                  [{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}], so_goi=20, kl_goi=500)
    g1, g5, g10, gp, kgt, ggoi, gth = _gia(conn, fid)
    assert (g1, g5, g10) == (pytest.approx(550), pytest.approx(530), pytest.approx(530))
    assert gp is None                                  # không ghi pallet → KHÔNG đoán
    assert kgt == pytest.approx(10) and ggoi == pytest.approx(275) and gth == pytest.approx(5500)


def test_067_bac_theo_kg_quy_ra_thung_bang_quy_cach(conn, batch):
    _hang(conn, batch)
    # Vietnam House: 25kg → 600/kg · 50kg → 580/kg; thùng 20 × 500g = 10 kg ⇒ 25 kg = 2,5 thùng, 50 kg = 5 thùng
    fid = _qs_bac(conn, batch, "VH", 610, "kg", 1,
                  [{"tu": 25, "don_vi_sl": "kg", "gia": 600, "don_vi_gia": "kg"},
                   {"tu": 50, "don_vi_sl": "kg", "gia": 580, "don_vi_gia": "kg"}], so_goi=20, kl_goi=500)
    g1, g5, g10, *_ = _gia(conn, fid)
    assert (g1, g5, g10) == (pytest.approx(610), pytest.approx(580), pytest.approx(580))


def test_067_bac_kg_khong_biet_quy_cach_thi_khong_ap_khong_doan(conn, batch):
    _hang(conn, batch)
    fid = _qs_bac(conn, batch, "OBA", 530, "kg", 1, [{"tu": 48, "don_vi_sl": "kg", "gia": 510, "don_vi_gia": "kg"}])
    assert _gia(conn, fid)[:3] == (pytest.approx(530), pytest.approx(530), pytest.approx(530))


def test_067_bac_pallet_chi_ap_cho_pallet_va_thue_chia_mot_lan(conn, batch):
    _hang(conn, batch)
    fid = _qs_bac(conn, batch, "A", 5400, "thung", 10,
                  [{"tu": 1, "don_vi_sl": "pallet", "gia": 4860, "don_vi_gia": "thung"}], thue="co")
    g1, g5, g10, gp, *_ = _gia(conn, fid)
    assert g1 == pytest.approx(500) and g10 == pytest.approx(500) and gp == pytest.approx(450)


def test_067_dinh_chinh_bac_va_quy_cach_thang_ban_nap(conn, batch):
    _hang(conn, batch)
    fid = _qs_bac(conn, batch, "NEXT", 5500, "thung", 10, None)
    for t, v in (("bac", '[{"tu": 10, "don_vi_sl": "thung", "gia": 5000, "don_vi_gia": "thung"}]'),
                 ("so_goi_thung", "20"), ("kl_goi_g", "500"), ("khuyen_mai", "mua 10 tặng 1")):
        conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, %s, %s)", (fid, t, v))
    conn.commit()
    g1, g5, g10, *_ = _gia(conn, fid)
    assert (g1, g5, g10) == (pytest.approx(550), pytest.approx(550), pytest.approx(500))
    km, sg = conn.execute("SELECT khuyen_mai, so_goi_thung FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()
    assert km == "mua 10 tặng 1" and sg == 20
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, 'khuyen_mai', '')", (fid,))
    conn.commit()
    assert conn.execute("SELECT khuyen_mai FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()[0] is None


def test_067_thong_ke_nhom_van_tren_gia_le(conn, batch):
    _hang(conn, batch)
    for ben, g in (("A", 5400), ("B", 5600), ("C", 5800)):
        _qs_bac(conn, batch, ben, g, "thung", 10, [{"tu": 5, "don_vi_sl": "thung", "gia": 3000, "don_vi_gia": "thung"}])
    tv = conn.execute("SELECT trung_vi FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'").fetchone()[0]
    assert float(tv) == pytest.approx(560)             # bậc 5 thùng (300/kg) KHÔNG kéo trung vị


def test_067_so_sanh_nhom_mang_gia_kome_chuan_va_bang_va_km(conn, batch):
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _qs(conn, batch, "A", 540)
    _bang_gia(conn, batch, "NT01", "std", 0, 4900)
    _bang_gia(conn, batch, "NT01", "01", 5130, 5540)
    _bang_gia(conn, batch, "NT01", "10", 4500, 4860)
    r = conn.execute("""SELECT gia_kome_chuan, gia_kome_bang, gia_kome_km, ty_le_re_hon_kome
                        FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'""").fetchone()
    assert float(r[0]) == pytest.approx(4900 / 1.08 / 10)
    assert set(r[1]) == {"01"}                          # std và 10 (khuyến mãi) KHÔNG vào dải giá thường
    assert float(r[2]) == pytest.approx(450)
    assert float(r[3]) == 0                             # A ¥540 không rẻ hơn chuẩn ¥453,7
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_mart_doi_thu.py -q -k 067`
Expected: FAIL (`column "gia_1" does not exist`)

- [ ] **Step 3: Viết migration** `db/migrations/067_mart_quan_sat_gia_bac.sql`. Thân `mart.gia_doi_thu_quan_sat` = đúng bản 063 (`db/migrations/063_tin_hien_truong.sql`, từ `CREATE OR REPLACE VIEW mart.gia_doi_thu_quan_sat` đến trước `GRANT`), CHÉP NGUYÊN rồi đổi đúng những chỗ ghi dưới đây. Không sửa file 063.

```sql
-- 067 — Quan sát đối thủ: quy cách gói + giá bậc có cấu trúc (đặc tả giao diện mới §5.1, §5.2); So sánh mang giá KOME
-- chuẩn (§5.3). Giá tại N thùng = bậc RẺ NHẤT có `tu` (quy ra thùng) ≤ N, không bậc nào áp → giá lẻ. 'kg' → thùng bằng
-- kg_thung_dt; 'goi' → thùng bằng so_goi_thung; thiếu quy cách → bậc đó KHÔNG áp (không đoán). Pallet CHỈ khi bảng ghi
-- rõ (bậc don_vi_sl 'pallet' hoặc dòng muc_gia 'pallet') — không "1 pallet = 40 thùng". Thống kê nhóm (trung vị, bất
-- thường, thấp / cao nhất) vẫn trên GIÁ LẺ (yen_chuan) — "Khách mua" chỉ đổi cái được vẽ.
-- quan_sat: CREATE OR REPLACE (cột cũ giữ thứ tự, cột mới ở CUỐI) — hien_hanh dùng q.* nên phải DROP + tạo lại cùng
-- so_sanh_nhom (không view nào khác phụ thuộc hai view đó — kiểm bằng pg_depend trước khi chạy).

CREATE FUNCTION mart.gia_bac_kg(p_bac jsonb, p_sl numeric, p_pallet boolean, p_kg_thung numeric, p_so_goi integer,
                                p_kl_goi numeric, p_thue text) RETURNS numeric LANGUAGE sql IMMUTABLE AS $$
    SELECT min(b.gia_kg)
    FROM (
        SELECT CASE e->>'don_vi_gia' WHEN 'kg'    THEN (e->>'gia')::numeric
                                     WHEN 'thung' THEN (e->>'gia')::numeric / nullif(p_kg_thung, 0)
                                     WHEN 'goi'   THEN (e->>'gia')::numeric / nullif(p_kl_goi / 1000, 0) END
               / CASE WHEN p_thue = 'co' THEN 1.08 ELSE 1 END                                        AS gia_kg,
               CASE e->>'don_vi_sl' WHEN 'thung' THEN (e->>'tu')::numeric
                                    WHEN 'kg'    THEN (e->>'tu')::numeric / nullif(p_kg_thung, 0)
                                    WHEN 'goi'   THEN (e->>'tu')::numeric / nullif(p_so_goi, 0) END  AS tu_thung,
               e->>'don_vi_sl' = 'pallet'                                                            AS la_pallet
        FROM jsonb_array_elements(coalesce(p_bac, '[]'::jsonb)) e
    ) b
    WHERE CASE WHEN p_pallet THEN b.la_pallet OR b.tu_thung IS NOT NULL
               ELSE NOT b.la_pallet AND b.tu_thung <= p_sl END
$$;
```

Các chỗ đổi trong thân `quan_sat` (so với 063):
1. CTE `p` thêm năm dòng:
   ```sql
           max(gia_tri_moi) FILTER (WHERE truong = 'so_goi_thung')      AS so_goi_thung,
           max(gia_tri_moi) FILTER (WHERE truong = 'kl_goi_g')          AS kl_goi_g,
           max(gia_tri_moi) FILTER (WHERE truong = 'bac')               AS bac,
           max(gia_tri_moi) FILTER (WHERE truong = 'khuyen_mai')        AS khuyen_mai,
           max(gia_tri_moi) FILTER (WHERE truong = 'gia_truoc_km')      AS gia_truoc_km,
   ```
2. CTE `nap`:
   - `f.gia_bac, f.gia_truoc_km, …, f.khuyen_mai` đổi thành
     ```sql
     f.gia_bac,
     CASE WHEN p.gia_truoc_km IS NULL THEN f.gia_truoc_km
          WHEN p.gia_truoc_km ~ '^\s*\d+(\.\d+)?\s*$' THEN p.gia_truoc_km::numeric END AS gia_truoc_km,
     coalesce(p.trang_thai, f.trang_thai) AS trang_thai,
     CASE WHEN p.khuyen_mai IS NULL THEN f.khuyen_mai ELSE nullif(p.khuyen_mai, '') END AS khuyen_mai
     ```
     (đính chính `''` = đã xoá);
   - sau `NULL::text AS nhom_ke` thêm:
     ```sql
     , coalesce(CASE WHEN p.so_goi_thung ~ '^\s*\d+\s*$' THEN p.so_goi_thung::int END, f.so_goi_thung) AS so_goi_thung,
       coalesce(CASE WHEN p.kl_goi_g ~ '^\s*\d+(\.\d+)?\s*$' THEN p.kl_goi_g::numeric END, f.kl_goi_g) AS kl_goi_g,
       CASE WHEN p.bac IS NULL THEN f.bac ELSE p.bac::jsonb END AS bac
     ```
     (`doi_thu._kiem`, Task 6, bảo đảm `p.bac` là JSON hợp lệ; `'[]'` = đã xoá bậc).
3. CTE `tay`:
   - hai `NULL::text` / `NULL::numeric` ở vị trí `gia_bac` / `gia_truoc_km` → `NULL::text, t.gia_truoc_km`;
   - `NULL::text` ở vị trí `khuyen_mai` (sau `t.trang_thai`) → `t.khuyen_mai`;
   - cuối danh sách, sau `mart.nhom_cua_khoa(t.nhom_khoa)`, thêm `, t.so_goi_thung, t.kl_goi_g, t.bac`.
4. Câu SELECT cuối của 063 thành CTE `r` (bọc `WITH … , r AS (SELECT … FROM ghep x LEFT JOIN …)`). Thêm `x.so_goi_thung, x.kl_goi_g, x.bac` vào CUỐI danh sách cột của `r`, sau `tuoi_ngay`. Rồi:
   ```sql
   , k AS (
       SELECT r.*,
              CASE WHEN r.don_vi_gia IN ('thung', 'cs', 'case', 'ctn') AND r.kg_moi_don_vi_gia > 0 THEN r.kg_moi_don_vi_gia
                   WHEN r.so_goi_thung > 0 AND r.kl_goi_g > 0 THEN r.so_goi_thung * r.kl_goi_g / 1000 END AS kg_thung_dt
       FROM r
   )
   SELECT k.*,
          CASE WHEN k.don_vi_so = 'kg' AND k.kl_goi_g > 0 THEN k.yen_chuan * k.kl_goi_g / 1000 END      AS gia_goi,
          CASE WHEN k.don_vi_so = 'kg' AND k.kg_thung_dt > 0 THEN k.yen_chuan * k.kg_thung_dt END       AS gia_thung,
          CASE WHEN k.don_vi_so = 'kg'
               THEN least(k.yen_chuan, mart.gia_bac_kg(k.bac, 1, false, k.kg_thung_dt, k.so_goi_thung, k.kl_goi_g, k.thue))
               ELSE k.yen_chuan END                                                                     AS gia_1,
          CASE WHEN k.don_vi_so = 'kg'
               THEN least(k.yen_chuan, mart.gia_bac_kg(k.bac, 5, false, k.kg_thung_dt, k.so_goi_thung, k.kl_goi_g, k.thue))
               ELSE k.yen_chuan END                                                                     AS gia_5,
          CASE WHEN k.don_vi_so = 'kg'
               THEN least(k.yen_chuan, mart.gia_bac_kg(k.bac, 10, false, k.kg_thung_dt, k.so_goi_thung, k.kl_goi_g, k.thue))
               ELSE k.yen_chuan END                                                                     AS gia_10,
          CASE WHEN k.don_vi_so <> 'kg' THEN NULL
               WHEN k.muc_gia = 'pallet' THEN k.yen_chuan
               WHEN EXISTS (SELECT 1 FROM jsonb_array_elements(coalesce(k.bac, '[]'::jsonb)) e WHERE e->>'don_vi_sl' = 'pallet')
               THEN least(k.yen_chuan, mart.gia_bac_kg(k.bac, NULL, true, k.kg_thung_dt, k.so_goi_thung, k.kl_goi_g, k.thue))
          END                                                                                           AS gia_pallet
   FROM k;
   ```
   `least()` của Postgres bỏ NULL, nên không bậc nào áp thì ra giá lẻ.

Sau view:

```sql
DROP VIEW mart.so_sanh_nhom;
DROP VIEW mart.gia_doi_thu_hien_hanh;

CREATE VIEW mart.gia_doi_thu_hien_hanh AS
WITH q AS MATERIALIZED (SELECT * FROM mart.gia_doi_thu_quan_sat WHERE hien_hanh),
tv AS (
    SELECT nhom_khoa, don_vi_so,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY yen_chuan) AS trung_vi,
           count(DISTINCT ma_doi_thu)                             AS so_ben
    FROM q
    WHERE nhom_khoa IS NOT NULL AND yen_chuan IS NOT NULL AND trang_thai <> 'het' AND loai_nguon <> 'khach_ke'
    GROUP BY 1, 2
)
SELECT q.*, tv.trung_vi AS trung_vi_nhom, tv.so_ben AS so_ben_nhom,
       q.trang_thai_duyet NOT IN ('da_xac_nhan', 'da_sua')
         AND mart.la_gia_bat_thuong(q.yen_chuan, tv.trung_vi::numeric, tv.so_ben) AS bat_thuong
FROM q LEFT JOIN tv USING (nhom_khoa, don_vi_so);

-- Thân = 062, thêm giá KOME chuẩn / bảng / khuyến mãi (066). "Vị trí" (ty_le_re_hon_kome) so với 標準価格, không có thì
-- thực bán 90 ngày. Nhóm nhiều mã: chuẩn = trung bình có trọng số kg đã bán 90 ngày (tỷ số các tổng), không mã nào
-- bán thì trung bình thường; bảng / khuyến mãi lấy của mã bán nhiều kg nhất trong nhóm.
CREATE VIEW mart.so_sanh_nhom AS
WITH h AS MATERIALIZED (
    SELECT * FROM mart.gia_doi_thu_hien_hanh
    WHERE nhom_khoa IS NOT NULL AND yen_chuan IS NOT NULL AND trang_thai <> 'het'
      AND loai_nguon <> 'khach_ke' AND NOT bat_thuong
),
thanh_vien AS (
    SELECT DISTINCT nhom_khoa, substr(nhom_khoa, 4) AS product_code FROM h WHERE nhom_khoa LIKE 'ma:%'
    UNION
    SELECT 'n:' || nhom_id, product_code FROM app.nhom_so_sanh_ma
),
tv_gia AS (
    SELECT tv.nhom_khoa, tv.product_code, g.doanh_thu, g.kg_ban, mart.gia_kome_chuan(tv.product_code) AS chuan
    FROM thanh_vien tv LEFT JOIN mart.gia_kome_kg g USING (product_code)
),
chinh AS (      -- mã "chính" của nhóm: bán nhiều kg nhất (không ai bán → mã nhỏ nhất)
    SELECT DISTINCT ON (nhom_khoa) nhom_khoa, product_code FROM tv_gia
    ORDER BY nhom_khoa, kg_ban DESC NULLS LAST, product_code
),
kome AS (
    SELECT t.nhom_khoa, array_agg(t.product_code ORDER BY t.product_code) AS ma_kome,
           sum(t.doanh_thu) / nullif(sum(t.kg_ban), 0) AS gia_kome,
           coalesce(sum(t.chuan * t.kg_ban) FILTER (WHERE t.chuan IS NOT NULL)
                      / nullif(sum(t.kg_ban) FILTER (WHERE t.chuan IS NOT NULL), 0),
                    avg(t.chuan)) AS gia_kome_chuan,
           mode() WITHIN GROUP (ORDER BY mart.ten_nganh(p.food_category_name, p.product_code, p.kind_code)) AS nganh
    FROM tv_gia t LEFT JOIN core.dim_product p USING (product_code)
    GROUP BY t.nhom_khoa
),
bang AS (
    SELECT c.nhom_khoa,
           jsonb_object_agg(b.price_level, round(b.yen_kg, 1)) FILTER (WHERE b.price_level <> 'std' AND NOT mart.la_gia_km_kome(b.price_level)) AS gia_kome_bang,
           min(b.yen_kg) FILTER (WHERE mart.la_gia_km_kome(b.price_level))                                                         AS km
    FROM chinh c JOIN mart.gia_kome_bang b USING (product_code)
    GROUP BY c.nhom_khoa
)
SELECT h.nhom_khoa, max(h.ten_nhom) AS ten_nhom, h.don_vi_so, k.ma_kome,
       CASE WHEN h.don_vi_so = 'kg' THEN k.gia_kome END                                 AS gia_kome,
       count(DISTINCT h.ma_doi_thu)                                                     AS so_ben,
       count(*)                                                                         AS so_quan_sat,
       min(h.yen_chuan)                                                                 AS thap_nhat,
       (array_agg(h.ma_doi_thu ORDER BY h.yen_chuan))[1]                                AS ben_thap_nhat,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY h.yen_chuan)                         AS trung_vi,
       max(h.yen_chuan)                                                                 AS cao_nhat,
       CASE WHEN h.don_vi_so = 'kg' AND coalesce(k.gia_kome_chuan, k.gia_kome) IS NOT NULL
            THEN avg((h.yen_chuan < coalesce(k.gia_kome_chuan, k.gia_kome))::int) END   AS ty_le_re_hon_kome,
       k.nganh,
       CASE WHEN h.don_vi_so = 'kg' THEN k.gia_kome_chuan END                           AS gia_kome_chuan,
       CASE WHEN h.don_vi_so = 'kg' THEN b.gia_kome_bang END                            AS gia_kome_bang,
       CASE WHEN h.don_vi_so = 'kg' AND b.km < coalesce(k.gia_kome_chuan, 'infinity') THEN b.km END AS gia_kome_km
FROM h LEFT JOIN kome k USING (nhom_khoa) LEFT JOIN bang b USING (nhom_khoa)
GROUP BY h.nhom_khoa, h.don_vi_so, k.ma_kome, k.gia_kome, k.nganh, k.gia_kome_chuan, b.gia_kome_bang, b.km;

GRANT SELECT ON mart.gia_doi_thu_quan_sat, mart.gia_doi_thu_hien_hanh, mart.so_sanh_nhom TO kome_app, kome_report, kome_ingest;
GRANT EXECUTE ON FUNCTION mart.gia_bac_kg(jsonb, numeric, boolean, numeric, integer, numeric, text) TO kome_app, kome_report, kome_ingest;
```

Trước khi `DROP`, chạy trên CSDL test sau `apply_all`:
`SELECT DISTINCT dependent_view.relname FROM pg_depend JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid JOIN pg_class dependent_view ON pg_rewrite.ev_class = dependent_view.oid JOIN pg_class source ON pg_depend.refobjid = source.oid WHERE source.relname IN ('gia_doi_thu_hien_hanh','so_sanh_nhom');`
Có view nào ngoài hai view này thì tạo lại nó y hệt trong 067, và ghi vào ledger.

- [ ] **Step 4: Chạy, thấy qua**

Run: `pytest tests/test_mart_doi_thu.py tests/test_doi_thu.py tests/test_doi_thu_api.py tests/test_lien_he.py -q`
Expected: PASS. Test cũ về `ty_le_re_hon_kome` có thể đổi số khi test đó có dòng 標準価格. Test cũ không gieo `fact_price_list` nên `gia_kome_chuan` NULL → giữ số cũ.

- [ ] **Step 5: Sinh lại tài liệu, commit**

```bash
python scripts/sinh_tai_lieu.py && python scripts/sinh_cot_dung.py
git add db/migrations/067_mart_quan_sat_gia_bac.sql tests/test_mart_doi_thu.py kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json
git commit -m "feat(doi-thu): 067 — quan sat mang quy cach goi + gia tai 1/5/10 thung/pallet; so sanh mang gia KOME chuan / bang / KM

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Sửa trường mới trên dòng giá (`kome/doi_thu.py`)

**Files:**
- Modify: `kome/doi_thu.py` (`TRUONG_SUA`, `_kiem`, `sua`, `gia_moi`)
- Test: `tests/test_doi_thu.py`

**Interfaces:**
- Consumes: `dinh_chinh_gia.truong` mới (Task 1), view 067.
- Produces:
  - `TRUONG_SUA` = cũ + `("so_goi_thung", "kl_goi_g", "bac", "khuyen_mai", "gia_truoc_km")`;
  - `TRUONG_XOA_DUOC = ("khuyen_mai", "gia_truoc_km", "bac")` (gửi `""` / `[]` = xoá);
  - `kiem_bac_nhap(v) -> str` (JSON chuẩn hoá). `gia_moi` nhận thêm năm trường đó.

- [ ] **Step 1: Viết test hỏng** — thêm vào `tests/test_doi_thu.py` (dùng helper tạo dòng nạp có sẵn trong file; nếu chưa có thì dùng `tests.test_mart_doi_thu._hang/_qs`):

```python
import json
from tests.test_mart_doi_thu import _hang, _qs
from kome import doi_thu as DT


def test_sua_quy_cach_goi_va_bac_va_khuyen_mai(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    DT.sua(conn, fid, {"so_goi_thung": "20", "kl_goi_g": "500",
                       "bac": [{"tu": 5, "don_vi_sl": "thung", "gia": "5,300", "don_vi_gia": "thung"}],
                       "khuyen_mai": "mua 10 tặng 1"}, None)
    conn.commit()
    r = conn.execute("SELECT so_goi_thung, kl_goi_g, bac, khuyen_mai FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()
    assert r[0] == 20 and float(r[1]) == 500 and r[2] == [{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]
    assert r[3] == "mua 10 tặng 1"


def test_xoa_khuyen_mai_va_bac_duoc_nhung_khong_xoa_gia(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    DT.sua(conn, fid, {"khuyen_mai": "", "bac": []}, None)
    conn.commit()
    km, bac = conn.execute("SELECT khuyen_mai, bac FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()
    assert km is None and bac == []
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {"gia_goc": ""}, None)


@pytest.mark.parametrize("truong,v", [
    ("so_goi_thung", "0"), ("so_goi_thung", "2.5"), ("so_goi_thung", "100001"),
    ("kl_goi_g", "0"), ("kl_goi_g", "30001"),
    ("bac", [{"tu": 0, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "kg"}]),
    ("bac", [{"tu": 1, "don_vi_sl": "hop", "gia": 1, "don_vi_gia": "kg"}]),
    ("bac", "khong phai json"), ("bac", [{"tu": 1, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "kg"}] * 11),
    ("gia_truoc_km", "-1"),
])
def test_truong_moi_kiem_dau_vao(conn, batch, truong, v):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {truong: v}, None)
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_doi_thu.py -q -k "quy_cach_goi or xoa_khuyen_mai or truong_moi"`
Expected: FAIL (`LoiNhap: Không sửa được trường 'so_goi_thung'`)

- [ ] **Step 3: Sửa `kome/doi_thu.py`**

```python
TRUONG_SUA = ("ten_goc", "quy_cach_goc", "gia_goc", "don_vi_gia", "kg_moi_don_vi_gia",
              "thue", "gom_ship", "kenh_gia", "muc_gia", "trang_thai",
              "so_goi_thung", "kl_goi_g", "bac", "khuyen_mai", "gia_truoc_km")
TRUONG_XOA_DUOC = ("khuyen_mai", "gia_truoc_km", "bac")   # "" / [] = xoá (khuyến mãi hết, bậc sai)
DON_VI_SL = ("thung", "kg", "goi", "pallet")               # cùng lược đồ `bac` của 065 / scripts/goi_doi_thu.py
DON_VI_GIA_BAC = ("thung", "kg", "goi")
BAC_TOI_DA = 10
GOI_TOI_DA = 100000
KL_GOI_TOI_DA = Decimal("30000")


def kiem_bac_nhap(v) -> str:
    """Bậc người nhập (list hoặc chữ JSON) → chữ JSON chuẩn hoá cho app.dinh_chinh_gia. [] = xoá bậc."""
    if isinstance(v, str):
        try:
            v = json.loads(v) if v.strip() else []
        except ValueError:
            raise LoiNhap("Bậc giá không đọc được.")
    if not isinstance(v, list) or len(v) > BAC_TOI_DA:
        raise LoiNhap(f"Tối đa {BAC_TOI_DA} bậc giá.")
    ra = []
    for b in v:
        if not isinstance(b, dict) or b.get("don_vi_sl") not in DON_VI_SL or b.get("don_vi_gia") not in DON_VI_GIA_BAC:
            raise LoiNhap("Mỗi bậc cần: từ bao nhiêu (thùng / kg / gói / pallet) và giá (/ thùng / kg / gói).")
        tu, gia = _so(b.get("tu"), "Số lượng của bậc", True), _so(b.get("gia"), "Giá của bậc", True)
        if tu is None or gia is None:
            raise LoiNhap("Bậc giá thiếu số lượng hoặc giá.")
        ra.append({"tu": int(tu) if tu == tu.to_integral_value() else float(tu), "don_vi_sl": b["don_vi_sl"],
                   "gia": int(gia) if gia == gia.to_integral_value() else float(gia), "don_vi_gia": b["don_vi_gia"]})
    return json.dumps(ra, ensure_ascii=False)
```

Trong `_kiem`, thêm trước `for ten, tap in …`:

```python
    if truong == "bac":
        return kiem_bac_nhap(v)
    if truong == "so_goi_thung":
        x = _so(v, "Số gói / thùng", True)
        if x is None:
            return None
        if x != x.to_integral_value() or x > GOI_TOI_DA:
            raise LoiNhap("Số gói / thùng phải là số nguyên.")
        return str(int(x))
    if truong == "kl_goi_g":
        x = _so(v, "Khối lượng 1 gói", True, True)
        if x is not None and x > KL_GOI_TOI_DA:
            raise LoiNhap("Khối lượng 1 gói (g) quá lớn.")
        return None if x is None else format(x, "f")
    if truong == "gia_truoc_km":
        return _chuoi_so(v, "Giá trước khuyến mãi") if v not in (None, "") else ""
```

Trong `sua`, sửa vòng chặn giá trị trống cho các trường xoá được:

```python
    for k, v in thay_doi.items():
        if k in TRUONG_XOA_DUOC:
            continue
        if v is None or not str(v).strip():
            raise LoiNhap("Để trống không xoá được giá trị AI đã đọc — nhập giá trị đúng, hoặc dùng 'Giá đã đổi'.")
    sach = {k: _kiem(k, v) for k, v in thay_doi.items()}
    sach = {k: ("" if (k in TRUONG_XOA_DUOC and v is None) else v) for k, v in sach.items()}
```

Kết quả: `khuyen_mai` trống → `""`, `gia_truoc_km` trống → `""`, `bac` rỗng → `"[]"`. View 067 hiểu `''` là xoá.

`gia_moi` (giá đã đổi / thêm tay): khi ghi `app.gia_doi_thu_tay`, thêm năm cột. Mở rộng danh sách cột của câu `INSERT` bằng `so_goi_thung, kl_goi_g, bac, khuyen_mai, gia_truoc_km`, lấy giá trị từ `v` (đã `_kiem`). Trong `gia_moi`, `bac` rỗng → NULL, `khuyen_mai` rỗng → NULL. Khi có `fact_goc_id`, sao chép `so_goi_thung, kl_goi_g` của dòng gốc (thêm hai cột vào câu `SELECT … FROM mart.gia_doi_thu_quan_sat` và tuple `k`). Thêm test:

```python
def test_gia_moi_mang_quy_cach_va_bac(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    DT.sua(conn, fid, {"so_goi_thung": "20", "kl_goi_g": "500"}, None)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "5200", "loai_nguon": "to_roi",
                            "bac": [{"tu": 5, "don_vi_sl": "thung", "gia": 5000, "don_vi_gia": "thung"}]}, None)
    conn.commit()
    r = conn.execute("SELECT so_goi_thung, kl_goi_g, bac FROM app.gia_doi_thu_tay WHERE id=%s", (tid,)).fetchone()
    assert r[0] == 20 and float(r[1]) == 500 and r[2][0]["gia"] == 5000
```

- [ ] **Step 4: Chạy, thấy qua**

Run: `pytest tests/test_doi_thu.py tests/test_doi_thu_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kome/doi_thu.py tests/test_doi_thu.py
git commit -m "feat(doi-thu): sua duoc goi/thung, tinh 1 goi, bac gia, khuyen mai (xoa duoc)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Migration 068 + hàm ghi — điều kiện giao hàng và điều kiện bán hiện hành

**Files:**
- Create: `db/migrations/068_mart_giao_hang_dieu_kien.sql`
- Create: `kome/doi_thu_giao.py`
- Test: `tests/test_doi_thu_giao.py` (mới)

**Interfaces:**
- Consumes: bảng của Task 1, `kome.doi_thu._ghi_nhat_ky`, `LoiNhap`, `_so`.
- Produces:
  - view `mart.giao_hang_hien_hanh(ma_doi_thu, ten, <15 trường giao hàng>, nguon_chu, ngay_nguon, suy bool, da_xac_nhan bool)` — một dòng mỗi bên có dữ liệu; `'KOME'` đứng đầu;
  - view `mart.giao_hang_kome_bang_chung(so_don_ship, don_ship_lon_nhat, so_don_dai_330, so_don_dai_300)`;
  - view `mart.dieu_kien_hien_hanh(id, fact_id, ma_doi_thu, loai, noi_dung, ngay_nguon, them_tay bool)`;
  - `doi_thu_giao.TRUONG_GIAO_HANG: tuple[str, ...]`;
  - `sua_giao_hang(conn, ma_doi_thu: str, thay_doi: dict, nguoi) -> None`;
  - `sua_dieu_kien(conn, *, fact_id: int | None, ma_doi_thu: str, loai: str, noi_dung: str, bo: bool, nguoi) -> int`.

- [ ] **Step 1: Viết test hỏng** — `tests/test_doi_thu_giao.py`:

```python
"""068 + kome/doi_thu_giao.py — điều kiện giao hàng / điều kiện bán hiện hành (đặc tả giao diện mới §5.4)."""
from datetime import date
import pytest

from kome import doi_thu_giao as G
from kome.doi_thu import LoiNhap


@pytest.fixture
def kome_mac_dinh(conn):
    """app.giao_hang_kome sống qua TRUNCATE (GIU_LAI) — test nào sửa nó thì trả về mặc định 065 khi xong."""
    yield
    conn.rollback()
    conn.execute("""UPDATE app.giao_hang_kome SET bao_ship=false, phi_ship=500, phi_ship_theo='don', mien_ship_tu=20000,
                      mien_ship_kien=NULL, thung_moi_kien=NULL, phu_phi=NULL, phi_daibiki=330, daibiki_tu=20000,
                      daibiki_sau=300, ck_mien_daibiki=NULL, kien_toi_da_kg=NULL, ghep_kien=NULL, thue='chua',
                      cach_gui=NULL, da_xac_nhan=false""")
    conn.commit()


def _nap(conn, batch, ben, ngay=date(2026, 8, 31), **kw):
    b = batch(abs(hash((ben, ngay, str(kw)))) % 50_000 + 70_000, ngay)
    cot = ", ".join(kw)
    conn.execute(f"""INSERT INTO core.fact_giao_hang_doi_thu (batch_id, ma_dong, ma_doi_thu, ngay_nguon{', ' + cot if kw else ''})
                     VALUES (%s, 'x', %s, %s{', %s' * len(kw)})""", (b, ben, ngay, *kw.values()))
    conn.commit()
    return b


def _hh(conn, ben):
    return conn.execute("SELECT * FROM mart.giao_hang_hien_hanh WHERE ma_doi_thu=%s", (ben,)).fetchone()


def _cot(conn, ben, cot):
    return conn.execute(f"SELECT {cot} FROM mart.giao_hang_hien_hanh WHERE ma_doi_thu=%s", (ben,)).fetchone()[0]


def test_kome_dung_dau_va_mang_nhan_suy_khi_chua_xac_nhan(conn):
    r = conn.execute("SELECT ma_doi_thu, phi_ship, suy FROM mart.giao_hang_hien_hanh").fetchall()
    assert r[0] == ("KOME", 500, True)


def test_lo_moi_nhat_cua_ben_thang_va_sua_sau_lo_thang_lo(conn, batch):
    _nap(conn, batch, "IMAI", date(2026, 7, 31), phi_ship=500)
    _nap(conn, batch, "IMAI", date(2026, 8, 31), phi_ship=605, phi_daibiki=440)
    assert _cot(conn, "IMAI", "phi_ship") == 605
    G.sua_giao_hang(conn, "IMAI", {"phi_daibiki": "400", "phu_phi": {"hokkaido": 800, "okinawa": "khong_nhan"}}, None)
    conn.commit()
    assert _cot(conn, "IMAI", "phi_daibiki") == 400
    assert _cot(conn, "IMAI", "phu_phi") == {"hokkaido": 800, "okinawa": "khong_nhan"}
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='giao_hang' AND doi_tuong='giao:IMAI'").fetchone()[0] == 1


def test_lo_nap_SAU_lan_sua_thi_lo_thang(conn, batch):
    _nap(conn, batch, "IMAI", date(2026, 8, 31), phi_ship=605)
    G.sua_giao_hang(conn, "IMAI", {"phi_ship": "600"}, None)
    conn.commit()
    conn.execute("UPDATE app.dinh_chinh_giao_hang SET luc = luc - interval '1 day'")   # sửa XONG trước lô sau
    conn.commit()
    _nap(conn, batch, "IMAI", date(2026, 9, 30), phi_ship=650)
    assert _cot(conn, "IMAI", "phi_ship") == 650


def test_xoa_ve_khong_ghi_la_NULL_khong_phai_0(conn, batch):
    _nap(conn, batch, "IMAI", phi_daibiki=440)
    G.sua_giao_hang(conn, "IMAI", {"phi_daibiki": ""}, None)
    conn.commit()
    assert _cot(conn, "IMAI", "phi_daibiki") is None


def test_ben_chua_co_lo_van_sua_duoc(conn):
    G.sua_giao_hang(conn, "JVB", {"bao_ship": True, "thue": "bao"}, None)
    conn.commit()
    assert (_cot(conn, "JVB", "bao_ship"), _cot(conn, "JVB", "thue")) == (True, "bao")


def test_kome_sua_la_update_va_danh_dau_xac_nhan(conn, kome_mac_dinh):
    G.sua_giao_hang(conn, "KOME", {"phu_phi": {"hokkaido": 1000}, "xac_nhan": True}, None)
    conn.commit()
    assert conn.execute("SELECT phu_phi, da_xac_nhan FROM app.giao_hang_kome").fetchone() == ({"hokkaido": 1000}, True)
    assert _cot(conn, "KOME", "suy") is False


@pytest.mark.parametrize("thay", [{"khong_co": "1"}, {"phi_ship": "-1"}, {"phi_ship_theo": "tuan"}, {"thue": "co"},
                                  {"phu_phi": {"mars": 1}}, {"phu_phi": {"hokkaido": -5}}, {"mien_ship_kien": "1.5"}])
def test_kiem_dau_vao(conn, thay):
    with pytest.raises(LoiNhap):
        G.sua_giao_hang(conn, "IMAI", thay, None)


def test_bang_chung_kome_dem_tu_phieu_ban(conn):
    r = conn.execute("SELECT * FROM mart.giao_hang_kome_bang_chung").fetchone()
    assert r is not None                                    # CSDL test không có phiếu phí → đếm 0, không lỗi


def test_dieu_kien_hien_hanh_bo_ghi_chu_doc_ap_sua_va_them_tay(conn, batch):
    b = batch(5)
    for i, (loai, nd) in enumerate((("ship", "Kiện 28kg"), ("ghi_chu_doc", "chép vào ghi_chu"), ("thue", "Bao thuế"))):
        conn.execute("""INSERT INTO core.fact_dieu_kien_doi_thu (batch_id, ma_dong, ma_doi_thu, ngay_nguon, loai, noi_dung)
                        VALUES (%s, %s, 'YUMI', '2026-08-31', %s, %s)""", (b, f"d{i}", loai, nd))
    conn.commit()
    ids = dict(conn.execute("SELECT noi_dung, id FROM core.fact_dieu_kien_doi_thu").fetchall())
    G.sua_dieu_kien(conn, fact_id=ids["Kiện 28kg"], ma_doi_thu="YUMI", loai="ship", noi_dung="Kiện 30kg", bo=False, nguoi=None)
    G.sua_dieu_kien(conn, fact_id=ids["Bao thuế"], ma_doi_thu="YUMI", loai="thue", noi_dung="Bao thuế", bo=True, nguoi=None)
    G.sua_dieu_kien(conn, fact_id=None, ma_doi_thu="YUMI", loai="thanh_toan", noi_dung="Chuyển khoản trước", bo=False, nguoi=None)
    conn.commit()
    r = sorted(conn.execute("SELECT loai, noi_dung, them_tay FROM mart.dieu_kien_hien_hanh WHERE ma_doi_thu='YUMI'").fetchall())
    assert r == [("ship", "Kiện 30kg", False), ("thanh_toan", "Chuyển khoản trước", True)]
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='dieu_kien'").fetchone()[0] == 3


def test_dieu_kien_chi_lay_lo_moi_nhat_cua_ben(conn, batch):
    for ngay, nd in ((date(2026, 7, 31), "cũ"), (date(2026, 8, 31), "mới")):
        b = batch(abs(hash(nd)) % 1000 + 3000, ngay)
        conn.execute("""INSERT INTO core.fact_dieu_kien_doi_thu (batch_id, ma_dong, ma_doi_thu, ngay_nguon, loai, noi_dung)
                        VALUES (%s, 'd', 'YUMI', %s, 'ship', %s)""", (b, ngay, nd))
    conn.commit()
    assert [r[0] for r in conn.execute("SELECT noi_dung FROM mart.dieu_kien_hien_hanh WHERE ma_doi_thu='YUMI'")] == ["mới"]
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_doi_thu_giao.py -q`
Expected: FAIL (`ModuleNotFoundError: kome.doi_thu_giao`)

- [ ] **Step 3a: Migration** `db/migrations/068_mart_giao_hang_dieu_kien.sql`:

```sql
-- 068 — Điều kiện giao hàng / điều kiện bán HIỆN HÀNH (đặc tả giao diện mới §5.4).
-- Giao hàng của một bên = lô nạp mới nhất của bên đó (meta.ingest_batch chưa hoàn tác, data_date rồi batch_id), mỗi
-- trường: đính chính của sale thắng NẾU ghi SAU lúc nạp lô đó (loaded_at) — "mới nhất thắng" giữa người đọc và người sửa;
-- bên chưa có lô nào mà sale đã điền → vẫn có dòng. '' = xoá về "không ghi" (NULL). KOME: app.giao_hang_kome
-- (`suy` = chưa ai xác nhận số suy từ phiếu bán). Điều kiện bán: lô mới nhất của bên, bỏ loại 'ghi_chu_doc', áp sửa / bỏ
-- mới nhất theo fact_id, cộng dòng sale thêm tay (fact_id NULL, không bị bỏ).

CREATE VIEW mart.giao_hang_hien_hanh AS
WITH lo AS (
    SELECT DISTINCT ON (f.ma_doi_thu) f.*, b.loaded_at
    FROM core.fact_giao_hang_doi_thu f JOIN meta.ingest_batch b USING (batch_id)
    WHERE b.undone_at IS NULL
    ORDER BY f.ma_doi_thu, b.data_date DESC, f.batch_id DESC, f.id DESC
),
dc AS (
    SELECT DISTINCT ON (ma_doi_thu, truong) ma_doi_thu, truong, gia_tri_moi, luc
    FROM app.dinh_chinh_giao_hang ORDER BY ma_doi_thu, truong, id DESC
),
ben AS (SELECT ma_doi_thu FROM lo UNION SELECT ma_doi_thu FROM dc),
v AS (
    SELECT b.ma_doi_thu, l.ngay_nguon, l.nguon_chu, l.loaded_at,
           l.bao_ship, l.phi_ship, l.phi_ship_theo, l.mien_ship_tu, l.mien_ship_kien, l.thung_moi_kien, l.phu_phi,
           l.phi_daibiki, l.daibiki_tu, l.daibiki_sau, l.ck_mien_daibiki, l.kien_toi_da_kg, l.ghep_kien, l.thue, l.cach_gui
    FROM ben b LEFT JOIN lo l USING (ma_doi_thu)
)
SELECT v.ma_doi_thu, d.ten,
       CASE WHEN x.bao_ship IS NULL THEN v.bao_ship ELSE nullif(x.bao_ship, '')::boolean END                      AS bao_ship,
       CASE WHEN x.phi_ship IS NULL THEN v.phi_ship ELSE nullif(x.phi_ship, '')::numeric END                      AS phi_ship,
       CASE WHEN x.phi_ship_theo IS NULL THEN v.phi_ship_theo ELSE nullif(x.phi_ship_theo, '') END                AS phi_ship_theo,
       CASE WHEN x.mien_ship_tu IS NULL THEN v.mien_ship_tu ELSE nullif(x.mien_ship_tu, '')::numeric END          AS mien_ship_tu,
       CASE WHEN x.mien_ship_kien IS NULL THEN v.mien_ship_kien ELSE nullif(x.mien_ship_kien, '')::int END        AS mien_ship_kien,
       CASE WHEN x.thung_moi_kien IS NULL THEN v.thung_moi_kien ELSE nullif(x.thung_moi_kien, '')::int END        AS thung_moi_kien,
       CASE WHEN x.phu_phi IS NULL THEN v.phu_phi ELSE nullif(x.phu_phi, '')::jsonb END                           AS phu_phi,
       CASE WHEN x.phi_daibiki IS NULL THEN v.phi_daibiki ELSE nullif(x.phi_daibiki, '')::numeric END             AS phi_daibiki,
       CASE WHEN x.daibiki_tu IS NULL THEN v.daibiki_tu ELSE nullif(x.daibiki_tu, '')::numeric END                AS daibiki_tu,
       CASE WHEN x.daibiki_sau IS NULL THEN v.daibiki_sau ELSE nullif(x.daibiki_sau, '')::numeric END             AS daibiki_sau,
       CASE WHEN x.ck_mien_daibiki IS NULL THEN v.ck_mien_daibiki ELSE nullif(x.ck_mien_daibiki, '')::boolean END AS ck_mien_daibiki,
       CASE WHEN x.kien_toi_da_kg IS NULL THEN v.kien_toi_da_kg ELSE nullif(x.kien_toi_da_kg, '')::numeric END    AS kien_toi_da_kg,
       CASE WHEN x.ghep_kien IS NULL THEN v.ghep_kien ELSE nullif(x.ghep_kien, '') END                            AS ghep_kien,
       CASE WHEN x.thue IS NULL THEN v.thue ELSE nullif(x.thue, '') END                                           AS thue,
       CASE WHEN x.cach_gui IS NULL THEN v.cach_gui ELSE nullif(x.cach_gui, '') END                               AS cach_gui,
       v.nguon_chu, v.ngay_nguon, false AS suy, false AS da_xac_nhan, 1 AS thu_tu
FROM v
LEFT JOIN app.doi_thu d ON d.ma = v.ma_doi_thu
CROSS JOIN LATERAL (
    SELECT max(gia_tri_moi) FILTER (WHERE truong = 'bao_ship')        AS bao_ship,
           max(gia_tri_moi) FILTER (WHERE truong = 'phi_ship')        AS phi_ship,
           max(gia_tri_moi) FILTER (WHERE truong = 'phi_ship_theo')   AS phi_ship_theo,
           max(gia_tri_moi) FILTER (WHERE truong = 'mien_ship_tu')    AS mien_ship_tu,
           max(gia_tri_moi) FILTER (WHERE truong = 'mien_ship_kien')  AS mien_ship_kien,
           max(gia_tri_moi) FILTER (WHERE truong = 'thung_moi_kien')  AS thung_moi_kien,
           max(gia_tri_moi) FILTER (WHERE truong = 'phu_phi')         AS phu_phi,
           max(gia_tri_moi) FILTER (WHERE truong = 'phi_daibiki')     AS phi_daibiki,
           max(gia_tri_moi) FILTER (WHERE truong = 'daibiki_tu')      AS daibiki_tu,
           max(gia_tri_moi) FILTER (WHERE truong = 'daibiki_sau')     AS daibiki_sau,
           max(gia_tri_moi) FILTER (WHERE truong = 'ck_mien_daibiki') AS ck_mien_daibiki,
           max(gia_tri_moi) FILTER (WHERE truong = 'kien_toi_da_kg')  AS kien_toi_da_kg,
           max(gia_tri_moi) FILTER (WHERE truong = 'ghep_kien')       AS ghep_kien,
           max(gia_tri_moi) FILTER (WHERE truong = 'thue')            AS thue,
           max(gia_tri_moi) FILTER (WHERE truong = 'cach_gui')        AS cach_gui
    FROM dc WHERE dc.ma_doi_thu = v.ma_doi_thu AND (v.loaded_at IS NULL OR dc.luc > v.loaded_at)
) x
UNION ALL
SELECT 'KOME', 'KOME', k.bao_ship, k.phi_ship, k.phi_ship_theo, k.mien_ship_tu, k.mien_ship_kien, k.thung_moi_kien,
       k.phu_phi, k.phi_daibiki, k.daibiki_tu, k.daibiki_sau, k.ck_mien_daibiki, k.kien_toi_da_kg, k.ghep_kien, k.thue,
       k.cach_gui, NULL, (k.sua_luc AT TIME ZONE 'Asia/Tokyo')::date, NOT k.da_xac_nhan, k.da_xac_nhan, 0
FROM app.giao_hang_kome k
ORDER BY thu_tu, ma_doi_thu;

-- Bằng chứng cho dòng KOME (đặc tả §5.4): đếm trên phiếu 180 ngày tới mốc. Mã phí nhận theo TÊN OBC (配送料… / 代引手数料…).
CREATE VIEW mart.giao_hang_kome_bang_chung AS
WITH don AS (
    SELECT f.slip_no,
           sum(f.amount) FILTER (WHERE NOT mart.la_phi_dieu_chinh(f.product_code, p.kind_code))  AS tien_hang,
           bool_or(p.product_name LIKE '配送料%')                                                  AS co_ship,
           bool_or(p.product_name LIKE '代引手数料330%')                                           AS dai_330,
           bool_or(p.product_name LIKE '代引手数料300%')                                           AS dai_300
    FROM mart.ban_den_moc f CROSS JOIN mart.moc_thoi_gian m
    LEFT JOIN core.dim_product p ON p.product_code = f.product_code
    WHERE f.sales_date > m.hom_nay - 180
    GROUP BY f.slip_no
)
SELECT count(*) FILTER (WHERE co_ship) AS so_don_ship, max(tien_hang) FILTER (WHERE co_ship) AS don_ship_lon_nhat,
       count(*) FILTER (WHERE dai_330) AS so_don_dai_330, count(*) FILTER (WHERE dai_300) AS so_don_dai_300
FROM don;

CREATE VIEW mart.dieu_kien_hien_hanh AS
WITH lo AS (
    SELECT DISTINCT ON (f.ma_doi_thu) f.ma_doi_thu, f.batch_id
    FROM core.fact_dieu_kien_doi_thu f JOIN meta.ingest_batch b USING (batch_id)
    WHERE b.undone_at IS NULL
    ORDER BY f.ma_doi_thu, b.data_date DESC, f.batch_id DESC
),
sua AS (
    SELECT DISTINCT ON (fact_id) fact_id, loai, noi_dung, bo FROM app.dinh_chinh_dieu_kien
    WHERE fact_id IS NOT NULL ORDER BY fact_id, id DESC
)
SELECT f.id, f.id AS fact_id, f.ma_doi_thu, coalesce(s.loai, f.loai) AS loai, coalesce(s.noi_dung, f.noi_dung) AS noi_dung,
       f.ngay_nguon, false AS them_tay
FROM core.fact_dieu_kien_doi_thu f JOIN lo USING (ma_doi_thu, batch_id)
LEFT JOIN sua s ON s.fact_id = f.id
WHERE f.loai <> 'ghi_chu_doc' AND NOT coalesce(s.bo, false)
UNION ALL
SELECT -t.id, NULL, t.ma_doi_thu, t.loai, t.noi_dung, (t.luc AT TIME ZONE 'Asia/Tokyo')::date, true
FROM app.dinh_chinh_dieu_kien t
WHERE t.fact_id IS NULL AND NOT t.bo;

GRANT SELECT ON mart.giao_hang_hien_hanh, mart.giao_hang_kome_bang_chung, mart.dieu_kien_hien_hanh
    TO kome_app, kome_report, kome_ingest;
```

Kiểm tên cột của `meta.ingest_batch` (`loaded_at`, `undone_at`, `data_date`) và chữ ký `mart.la_phi_dieu_chinh` trước khi chạy: `grep -n "loaded_at\|undone_at" db/migrations/0*.sql | head`, `grep -n "FUNCTION mart.la_phi_dieu_chinh" db/migrations/*.sql`. Tên khác thì dùng tên thật.

Bỏ một dòng THÊM TAY: ghi một dòng `fact_id = NULL, bo = true` có CÙNG `ma_doi_thu, loai, noi_dung`; view loại mọi dòng thêm tay có dòng `bo` cùng bộ ba ghi SAU nó (không thêm cột). Nhánh `UNION ALL` thứ hai của view ở trên phải là bản dưới đây (dùng bản này, không dùng bản ngắn ở trên):

```sql
-- thay nhánh UNION ALL thứ hai ở trên bằng:
SELECT -t.id, NULL, t.ma_doi_thu, t.loai, t.noi_dung, (t.luc AT TIME ZONE 'Asia/Tokyo')::date, true
FROM app.dinh_chinh_dieu_kien t
WHERE t.fact_id IS NULL AND NOT t.bo
  AND NOT EXISTS (SELECT 1 FROM app.dinh_chinh_dieu_kien b
                  WHERE b.fact_id IS NULL AND b.bo AND b.id > t.id
                    AND (b.ma_doi_thu, b.loai, b.noi_dung) = (t.ma_doi_thu, t.loai, t.noi_dung));
```

Thêm test:

```python
def test_bo_dong_them_tay(conn):
    G.sua_dieu_kien(conn, fact_id=None, ma_doi_thu="YUMI", loai="khac", noi_dung="Nghỉ Obon", bo=False, nguoi=None)
    G.sua_dieu_kien(conn, fact_id=None, ma_doi_thu="YUMI", loai="khac", noi_dung="Nghỉ Obon", bo=True, nguoi=None)
    conn.commit()
    assert conn.execute("SELECT count(*) FROM mart.dieu_kien_hien_hanh WHERE ma_doi_thu='YUMI'").fetchone()[0] == 0
```

- [ ] **Step 3b: `kome/doi_thu_giao.py`**

```python
"""Ghi điều kiện giao hàng / điều kiện bán (đặc tả 2026-09-29-doi-thu-giao-dien-moi-design.md §4.7, §5.4).

Đối thủ: sổ CHỈ THÊM (app.dinh_chinh_giao_hang / app.dinh_chinh_dieu_kien). KOME: app.giao_hang_kome (một dòng,
UPDATE). Mỗi lần ghi thêm một dòng app.doi_thu_nhat_ky CÙNG giao dịch — hai sổ đó KHÔNG có trong anh_chup._PHIEN_BAN,
ảnh chụp đổi nhờ dòng nhật ký (nếp 064). '' = xoá về "không ghi" (NULL ở mart.giao_hang_hien_hanh), không phải 0.
"""
import json
from decimal import Decimal

from kome.doi_thu import LoiNhap, _ghi_nhat_ky, _so, DAI_TOI_DA

TRUONG_GIAO_HANG = ("bao_ship", "phi_ship", "phi_ship_theo", "mien_ship_tu", "mien_ship_kien", "thung_moi_kien",
                    "phu_phi", "phi_daibiki", "daibiki_tu", "daibiki_sau", "ck_mien_daibiki", "kien_toi_da_kg",
                    "ghep_kien", "thue", "cach_gui")
VUNG = ("hokkaido", "tohoku", "kanto", "chubu", "kansai", "chugoku", "shikoku", "kyushu", "okinawa")
_SO = {"phi_ship", "mien_ship_tu", "phi_daibiki", "daibiki_tu", "daibiki_sau", "kien_toi_da_kg"}
_NGUYEN = {"mien_ship_kien", "thung_moi_kien"}
_BOOL = {"bao_ship", "ck_mien_daibiki"}
_TAP = {"phi_ship_theo": ("don", "thung", "kien"), "thue": ("bao", "chua", "khong_ro")}
LOAI_DK = ("ship", "khuyen_mai", "thanh_toan", "thue", "khac")


def _kiem_truong(t: str, v):
    """→ chữ lưu vào gia_tri_moi ('' = xoá), hoặc giá trị Python cho app.giao_hang_kome."""
    if t not in TRUONG_GIAO_HANG:
        raise LoiNhap(f"Không sửa được trường '{t}'.")
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if t in _BOOL:
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s not in ("true", "false"):
            raise LoiNhap(f"{t} chỉ nhận có / không.")
        return s == "true"
    if t in _SO:
        return _so(v, t)
    if t in _NGUYEN:
        x = _so(v, t, True)
        if x != x.to_integral_value():
            raise LoiNhap(f"{t} phải là số nguyên.")
        return int(x)
    if t in _TAP:
        if v not in _TAP[t]:
            raise LoiNhap(f"{t} chỉ nhận {', '.join(_TAP[t])}.")
        return v
    if t == "phu_phi":
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except ValueError:
                raise LoiNhap("Phụ phí vùng không đọc được.")
        if not isinstance(v, dict) or any(k not in VUNG for k in v) or any(
                not (x == "khong_nhan" or (isinstance(x, (int, float)) and not isinstance(x, bool) and x >= 0))
                for x in v.values()):
            raise LoiNhap("Phụ phí vùng: mỗi vùng một số ¥ (≥ 0) hoặc 'khong_nhan'.")
        return v
    return str(v).strip()[:DAI_TOI_DA]


def _chu(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, Decimal):
        return format(v, "f")
    return str(v)


def sua_giao_hang(conn, ma_doi_thu: str, thay_doi: dict, nguoi) -> None:
    """Một lần bấm Lưu ở pop-up giao hàng. ma_doi_thu 'KOME' → app.giao_hang_kome (khoá 'xac_nhan': True = chủ DN
    xác nhận số suy từ phiếu bán). Đối thủ → một dòng app.dinh_chinh_giao_hang mỗi trường đổi."""
    thay_doi = dict(thay_doi or {})
    xac_nhan = bool(thay_doi.pop("xac_nhan", False))
    if not thay_doi and not xac_nhan:
        raise LoiNhap("Không có gì để sửa.")
    sach = {t: _kiem_truong(t, v) for t, v in thay_doi.items()}
    if ma_doi_thu == "KOME":
        cu = conn.execute(f"SELECT {', '.join(sach) or 'da_xac_nhan'} FROM app.giao_hang_kome").fetchone()
        dat = [f"{t} = %s" for t in sach] + ["sua_luc = now()", "sua_boi = %s"] + (["da_xac_nhan = true"] if xac_nhan else [])
        conn.execute(f"UPDATE app.giao_hang_kome SET {', '.join(dat)}",
                     [json.dumps(v) if isinstance(v, dict) else v for v in sach.values()] + [nguoi])
        _ghi_nhat_ky(conn, "giao_hang", "giao:KOME", dict(zip(sach, cu)) if sach else None,
                     {**{t: _chu(v) for t, v in sach.items()}, **({"xac_nhan": True} if xac_nhan else {})}, nguoi)
        return
    if not conn.execute("SELECT 1 FROM app.doi_thu WHERE ma = %s", (ma_doi_thu,)).fetchone():
        raise LoiNhap("Không có đối thủ này.")
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO app.dinh_chinh_giao_hang (ma_doi_thu, truong, gia_tri_moi, nguoi_dung_id)
                           VALUES (%s, %s, %s, %s)""", [(ma_doi_thu, t, _chu(v), nguoi) for t, v in sach.items()])
    _ghi_nhat_ky(conn, "giao_hang", f"giao:{ma_doi_thu}", None, {t: _chu(v) for t, v in sach.items()}, nguoi)


def sua_dieu_kien(conn, *, fact_id, ma_doi_thu: str, loai: str, noi_dung: str, bo: bool, nguoi) -> int:
    """Sửa / bỏ một điều kiện đã nạp (fact_id), hoặc thêm tay (fact_id None). Bỏ dòng thêm tay = gọi lại với bo=True
    và CÙNG (ma_doi_thu, loai, noi_dung) — xem mart.dieu_kien_hien_hanh (068)."""
    if loai not in LOAI_DK:
        raise LoiNhap(f"Loại điều kiện chỉ nhận {', '.join(LOAI_DK)}.")
    nd = (noi_dung or "").strip()
    if not 1 <= len(nd) <= 300:
        raise LoiNhap("Nội dung điều kiện 1–300 ký tự.")
    if fact_id is not None and not conn.execute(
            "SELECT 1 FROM core.fact_dieu_kien_doi_thu WHERE id = %s AND ma_doi_thu = %s", (fact_id, ma_doi_thu)).fetchone():
        raise LoiNhap("Không tìm thấy điều kiện này (có thể lô đã bị hoàn tác).")
    if not conn.execute("SELECT 1 FROM app.doi_thu WHERE ma = %s", (ma_doi_thu,)).fetchone():
        raise LoiNhap("Không có đối thủ này.")
    i = conn.execute("""INSERT INTO app.dinh_chinh_dieu_kien (fact_id, ma_doi_thu, loai, noi_dung, bo, nguoi_dung_id)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                     (fact_id, ma_doi_thu, loai, nd, bool(bo), nguoi)).fetchone()[0]
    _ghi_nhat_ky(conn, "dieu_kien", f"dk:{fact_id}" if fact_id is not None else f"dk:tay:{ma_doi_thu}",
                 None, {"loai": loai, "noi_dung": nd, "bo": bool(bo)}, nguoi)
    return i
```

- [ ] **Step 4: Chạy, thấy qua**

Run: `pytest tests/test_doi_thu_giao.py tests/test_doi_thu_bang.py -q`
Expected: PASS

- [ ] **Step 5: Sinh lại tài liệu, commit**

```bash
python scripts/sinh_tai_lieu.py && python scripts/sinh_cot_dung.py
git add db/migrations/068_mart_giao_hang_dieu_kien.sql kome/doi_thu_giao.py tests/test_doi_thu_giao.py kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json
git commit -m "feat(doi-thu): 068 — giao hang / dieu kien ban hien hanh + ham sua (so chi them, nhat ky cung giao dich)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

`scripts/sinh_cot_dung.py` có `MAN` / `LUU_RIENG`: nếu test `tests/test_cot_dung.py` đỏ vì `kome/doi_thu_giao.py` đọc `mart` mà chưa khai, thì khai nó cạnh `"kome/doi_thu.py": ["doi_thu"]`.

---

### Task 8: Phí của đơn mẫu — hai bản, chung ca kiểm

**Files:**
- Create: `kome/phi_giao.py`, `giao_dien/src/doi_thu/phi_giao.ts`, `giao_dien/src/doi_thu/phi_giao.test.ts`, `tests/du_lieu/phi_giao_ca.json`, `tests/test_phi_giao.py`
- Modify: `kome/web/spa/` (build)

**Interfaces:**
- Consumes: hình dạng một dòng `mart.giao_hang_hien_hanh` (Task 7) dạng dict / object JSON.
- Produces:
  - `kome.phi_giao.tinh(dk: dict, don: dict) -> dict`;
  - `phi_giao.ts::tinh(dk: DieuKienGiao, don: DonMau): KetQuaPhi`;
  - `don = {"tien": số ¥ tiền hàng, "thung": số thùng, "vung": "kanto"|…|"okinawa", "tra": "daibiki"|"ck"}`;
  - kết quả `{"ship": số, "vung": số, "daibiki": số, "chua_ro": [chuỗi], "khong_nhan": bool}`.

**Luật** (§5.4 đặc tả; viết đúng một lần mỗi bản):
1. Ship:
   - `bao_ship = true` → 0;
   - miễn khi `tien ≥ mien_ship_tu` (NULL = không có ngưỡng) HOẶC `thung ≥ mien_ship_kien × (thung_moi_kien ?? 1)`;
   - không miễn thì `phi_ship` × (1 nếu `don`; `thung` nếu `thung`; số kiện nếu `kien`);
   - `phi_ship` NULL → `"ship"` vào `chua_ro`, ship = 0;
   - `bao_ship` NULL mà `phi_ship` cũng NULL → cũng `chua_ro`.
2. Số kiện = ⌈thung ÷ thung_moi_kien⌉; `thung_moi_kien` NULL → 1 kiện.
3. Phụ phí vùng: vùng `kanto`, `chubu`, `kansai` → 0 nếu không ghi. Vùng khác:
   - `phu_phi[vùng] = "khong_nhan"` → `khong_nhan = true`;
   - số → × số kiện;
   - vùng không có trong `phu_phi` mà `phu_phi` là NULL → `"vùng"` vào `chua_ro`;
   - `phu_phi` là object nhưng thiếu vùng → 0 (bên đó đã liệt kê vùng phụ thu, vùng này không có).
4. Daibiki chỉ khi `tra = "daibiki"`:
   - `daibiki_tu` có và `tien ≥ daibiki_tu` → `daibiki_sau ?? 0`;
   - không thì `phi_daibiki`, NULL → `"daibiki"` vào `chua_ro`.

  `tra = "ck"` → 0 (`ck_mien_daibiki` chỉ để hiển thị).

- [ ] **Step 1: Viết ca kiểm chung** `tests/du_lieu/phi_giao_ca.json` (mảng; mỗi ca `{ten, dk, don, ra}`). Ít nhất các ca sau, `dk` ghi đủ 15 khoá, khoá không ghi thì `null`:

```json
[
 {"ten": "KOME đơn nhỏ daibiki", "dk": {"bao_ship": false, "phi_ship": 500, "phi_ship_theo": "don", "mien_ship_tu": 20000, "mien_ship_kien": null, "thung_moi_kien": null, "phu_phi": null, "phi_daibiki": 330, "daibiki_tu": 20000, "daibiki_sau": 300, "ck_mien_daibiki": null, "kien_toi_da_kg": null, "ghep_kien": null, "thue": "chua", "cach_gui": null},
  "don": {"tien": 15000, "thung": 1, "vung": "kanto", "tra": "daibiki"}, "ra": {"ship": 500, "vung": 0, "daibiki": 330, "chua_ro": [], "khong_nhan": false}},
 {"ten": "KOME đơn lớn: miễn ship, daibiki 300", "dk": "<như trên>", "don": {"tien": 25000, "thung": 2, "vung": "kanto", "tra": "daibiki"}, "ra": {"ship": 0, "vung": 0, "daibiki": 300, "chua_ro": [], "khong_nhan": false}},
 {"ten": "KOME Hokkaido: phu_phi NULL → chưa rõ vùng", "dk": "<như trên>", "don": {"tien": 15000, "thung": 1, "vung": "hokkaido", "tra": "ck"}, "ra": {"ship": 500, "vung": 0, "daibiki": 0, "chua_ro": ["vùng"], "khong_nhan": false}},
 {"ten": "IMAI theo thùng dưới ngưỡng", "dk": {"bao_ship": false, "phi_ship": 605, "phi_ship_theo": "thung", "mien_ship_tu": 20000, "mien_ship_kien": null, "thung_moi_kien": null, "phu_phi": {"tohoku": 400, "hokkaido": 800}, "phi_daibiki": 440, "daibiki_tu": null, "daibiki_sau": null, "ck_mien_daibiki": true, "kien_toi_da_kg": null, "ghep_kien": null, "thue": null, "cach_gui": null},
  "don": {"tien": 15000, "thung": 2, "vung": "tohoku", "tra": "daibiki"}, "ra": {"ship": 1210, "vung": 400, "daibiki": 440, "chua_ro": [], "khong_nhan": false}},
 {"ten": "IMAI Kyushu không có trong phu_phi → 0", "dk": "<như IMAI>", "don": {"tien": 25000, "thung": 1, "vung": "kyushu", "tra": "ck"}, "ra": {"ship": 0, "vung": 0, "daibiki": 0, "chua_ro": [], "khong_nhan": false}},
 {"ten": "Vietnam House Okinawa không nhận", "dk": {"bao_ship": true, "phi_ship": null, "phi_ship_theo": null, "mien_ship_tu": null, "mien_ship_kien": null, "thung_moi_kien": null, "phu_phi": {"hokkaido": 1200, "okinawa": "khong_nhan"}, "phi_daibiki": 330, "daibiki_tu": null, "daibiki_sau": null, "ck_mien_daibiki": true, "kien_toi_da_kg": 25, "ghep_kien": "3–4 loại", "thue": null, "cach_gui": null},
  "don": {"tien": 15000, "thung": 1, "vung": "okinawa", "tra": "daibiki"}, "ra": {"ship": 0, "vung": 0, "daibiki": 330, "chua_ro": [], "khong_nhan": true}},
 {"ten": "Ichiba miễn khi đủ 1 kiện 2 thùng", "dk": {"bao_ship": false, "phi_ship": null, "phi_ship_theo": "kien", "mien_ship_tu": null, "mien_ship_kien": 1, "thung_moi_kien": 2, "phu_phi": null, "phi_daibiki": null, "daibiki_tu": null, "daibiki_sau": null, "ck_mien_daibiki": null, "kien_toi_da_kg": null, "ghep_kien": null, "thue": "bao", "cach_gui": null},
  "don": {"tien": 8000, "thung": 2, "vung": "kanto", "tra": "ck"}, "ra": {"ship": 0, "vung": 0, "daibiki": 0, "chua_ro": [], "khong_nhan": false}},
 {"ten": "Ichiba 1 thùng: chưa đủ kiện, phí không ghi → chưa rõ", "dk": "<như Ichiba>", "don": {"tien": 8000, "thung": 1, "vung": "kanto", "tra": "daibiki"}, "ra": {"ship": 0, "vung": 0, "daibiki": 0, "chua_ro": ["ship", "daibiki"], "khong_nhan": false}},
 {"ten": "Bùi Trâm phụ phí theo kiện × số kiện", "dk": {"bao_ship": true, "phi_ship": null, "phi_ship_theo": null, "mien_ship_tu": null, "mien_ship_kien": null, "thung_moi_kien": 2, "phu_phi": {"kyushu": 850, "hokkaido": 850}, "phi_daibiki": null, "daibiki_tu": null, "daibiki_sau": null, "ck_mien_daibiki": null, "kien_toi_da_kg": 28, "ghep_kien": null, "thue": "bao", "cach_gui": null},
  "don": {"tien": 15000, "thung": 4, "vung": "kyushu", "tra": "ck"}, "ra": {"ship": 0, "vung": 1700, "daibiki": 0, "chua_ro": [], "khong_nhan": false}},
 {"ten": "JVB không ghi gì", "dk": {"bao_ship": null, "phi_ship": null, "phi_ship_theo": null, "mien_ship_tu": null, "mien_ship_kien": null, "thung_moi_kien": null, "phu_phi": null, "phi_daibiki": null, "daibiki_tu": null, "daibiki_sau": null, "ck_mien_daibiki": null, "kien_toi_da_kg": null, "ghep_kien": null, "thue": null, "cach_gui": null},
  "don": {"tien": 15000, "thung": 1, "vung": "hokkaido", "tra": "daibiki"}, "ra": {"ship": 0, "vung": 0, "daibiki": 0, "chua_ro": ["ship", "vùng", "daibiki"], "khong_nhan": false}}
]
```

Trong file thật, thay mỗi `"<như …>"` bằng đúng object `dk` của ca được nhắc (JSON không có tham chiếu). Thứ tự `chua_ro` cố định: `ship` → `vùng` → `daibiki`.

- [ ] **Step 2: Viết test hỏng** `tests/test_phi_giao.py`:

```python
import json
from pathlib import Path
import pytest
from kome.phi_giao import tinh

CA = json.loads((Path(__file__).parent / "du_lieu" / "phi_giao_ca.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("ca", CA, ids=[c["ten"] for c in CA])
def test_phi_giao_ca_chung(ca):
    assert tinh(ca["dk"], ca["don"]) == ca["ra"]


def test_ca_du_15_khoa():
    from kome.doi_thu_giao import TRUONG_GIAO_HANG
    for c in CA:
        assert set(c["dk"]) == set(TRUONG_GIAO_HANG), c["ten"]
```

`giao_dien/src/doi_thu/phi_giao.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import ca from "../../../tests/du_lieu/phi_giao_ca.json";
import { tinh } from "./phi_giao";

describe("phí đơn mẫu — cùng ca với kome/phi_giao.py", () => {
  for (const c of ca as any[]) it(c.ten, () => expect(tinh(c.dk, c.don)).toEqual(c.ra));
});
```

(Nếu cấu hình vite / tsconfig không cho `import` JSON ngoài `src/`, làm theo cách `luoi_logic.test.ts` hoặc `cay_o.test.ts` đang đọc `tests/du_lieu/*.json` — `grep -rn "du_lieu" giao_dien/src/**/*.test.ts`.)

- [ ] **Step 3: Chạy, thấy hỏng**

Run: `pytest tests/test_phi_giao.py -q` và `cd giao_dien && npx vitest run src/doi_thu/phi_giao.test.ts`
Expected: FAIL (module chưa có)

- [ ] **Step 4: Viết hai bản**

`kome/phi_giao.py`:

```python
"""Phí khách trả THÊM cho một đơn mẫu theo điều kiện giao hàng của một bên (đặc tả giao diện mới §5.4).

MỘT thuật toán, hai bản: file này và giao_dien/src/doi_thu/phi_giao.ts — cả hai chạy tests/du_lieu/phi_giao_ca.json;
sửa một bản là sửa cả hai. Trường NULL mà cần tới → vào `chua_ro`, KHÔNG cộng 0 lặng lẽ. Không đoán phí.
"""
import math

VUNG_GOC = ("kanto", "chubu", "kansai")     # vùng không phụ thu khi bên đó không ghi


def _so(v):
    return None if v is None else float(v)


def tinh(dk: dict, don: dict) -> dict:
    tien, thung, vung, tra = float(don["tien"]), float(don["thung"]), don["vung"], don["tra"]
    ra = {"ship": 0, "vung": 0, "daibiki": 0, "chua_ro": [], "khong_nhan": False}
    tmk = dk.get("thung_moi_kien")
    kien = math.ceil(thung / tmk) if tmk else 1
    mien = (dk.get("mien_ship_tu") is not None and tien >= float(dk["mien_ship_tu"])) or \
           (dk.get("mien_ship_kien") is not None and thung >= dk["mien_ship_kien"] * (tmk or 1))
    if not dk.get("bao_ship") and not mien:
        if dk.get("phi_ship") is None:
            ra["chua_ro"].append("ship")
        else:
            he = {"thung": thung, "kien": kien}.get(dk.get("phi_ship_theo"), 1)
            ra["ship"] = _so(dk["phi_ship"]) * he
    if vung not in VUNG_GOC:
        pp = dk.get("phu_phi")
        if pp is None:
            ra["chua_ro"].append("vùng")
        elif pp.get(vung) == "khong_nhan":
            ra["khong_nhan"] = True
        elif pp.get(vung) is not None:
            ra["vung"] = float(pp[vung]) * kien
    if tra == "daibiki":
        if dk.get("daibiki_tu") is not None and tien >= float(dk["daibiki_tu"]):
            ra["daibiki"] = _so(dk.get("daibiki_sau")) or 0
        elif dk.get("phi_daibiki") is None:
            ra["chua_ro"].append("daibiki")
        else:
            ra["daibiki"] = _so(dk["phi_daibiki"])
    for k in ("ship", "vung", "daibiki"):          # số nguyên yên khi tròn — so khớp JSON của bản TS
        if float(ra[k]).is_integer():
            ra[k] = int(ra[k])
    return ra
```

`giao_dien/src/doi_thu/phi_giao.ts`:

```ts
// Phí khách trả THÊM cho một đơn mẫu (đặc tả giao diện mới §5.4). MỘT thuật toán, hai bản: file này và kome/phi_giao.py —
// cả hai chạy tests/du_lieu/phi_giao_ca.json; sửa một bản là sửa cả hai. NULL cần tới → `chua_ro`, không cộng 0.
export type Vung = "hokkaido" | "tohoku" | "kanto" | "chubu" | "kansai" | "chugoku" | "shikoku" | "kyushu" | "okinawa";
export type DieuKienGiao = {
  bao_ship: boolean | null; phi_ship: number | null; phi_ship_theo: "don" | "thung" | "kien" | null;
  mien_ship_tu: number | null; mien_ship_kien: number | null; thung_moi_kien: number | null;
  phu_phi: Partial<Record<Vung, number | "khong_nhan">> | null; phi_daibiki: number | null; daibiki_tu: number | null;
  daibiki_sau: number | null; ck_mien_daibiki: boolean | null; kien_toi_da_kg: number | null; ghep_kien: string | null;
  thue: "bao" | "chua" | "khong_ro" | null; cach_gui: string | null;
};
export type DonMau = { tien: number; thung: number; vung: Vung; tra: "daibiki" | "ck" };
export type KetQuaPhi = { ship: number; vung: number; daibiki: number; chua_ro: string[]; khong_nhan: boolean };

const VUNG_GOC: Vung[] = ["kanto", "chubu", "kansai"];

export function tinh(dk: DieuKienGiao, don: DonMau): KetQuaPhi {
  const ra: KetQuaPhi = { ship: 0, vung: 0, daibiki: 0, chua_ro: [], khong_nhan: false };
  const tmk = dk.thung_moi_kien;
  const kien = tmk ? Math.ceil(don.thung / tmk) : 1;
  const mien = (dk.mien_ship_tu != null && don.tien >= dk.mien_ship_tu)
    || (dk.mien_ship_kien != null && don.thung >= dk.mien_ship_kien * (tmk || 1));
  if (!dk.bao_ship && !mien) {
    if (dk.phi_ship == null) ra.chua_ro.push("ship");
    else ra.ship = dk.phi_ship * (dk.phi_ship_theo === "thung" ? don.thung : dk.phi_ship_theo === "kien" ? kien : 1);
  }
  if (!VUNG_GOC.includes(don.vung)) {
    const pp = dk.phu_phi;
    if (pp == null) ra.chua_ro.push("vùng");
    else if (pp[don.vung] === "khong_nhan") ra.khong_nhan = true;
    else if (pp[don.vung] != null) ra.vung = (pp[don.vung] as number) * kien;
  }
  if (don.tra === "daibiki") {
    if (dk.daibiki_tu != null && don.tien >= dk.daibiki_tu) ra.daibiki = dk.daibiki_sau ?? 0;
    else if (dk.phi_daibiki == null) ra.chua_ro.push("daibiki");
    else ra.daibiki = dk.phi_daibiki;
  }
  return ra;
}
```

- [ ] **Step 5: Chạy, thấy qua; build; commit**

```bash
pytest tests/test_phi_giao.py -q
cd giao_dien && npx vitest run src/doi_thu/phi_giao.test.ts && npm run build && cd ..
pytest tests/test_api.py -q -k ban_build
git add kome/phi_giao.py tests/test_phi_giao.py tests/du_lieu/phi_giao_ca.json giao_dien/src/doi_thu/phi_giao.ts giao_dien/src/doi_thu/phi_giao.test.ts kome/web/spa
git commit -m "feat(doi-thu): phi giao hang cua don mau — mot thuat toan hai ban (py + ts) chung ca kiem

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Sổ tay đọc, CLAUDE.md, cả bộ test

**Files:**
- Modify: `docs/doi-thu/huong-dan-doc.md`, `docs/doi-thu/so-tay-theo-ben.md`, `CLAUDE.md`
- Modify (nếu test đòi): `kome/web/tai_lieu_sinh.json`, `kome/web/cot_dung_sinh.json`

- [ ] **Step 1: `docs/doi-thu/huong-dan-doc.md`** — thêm mục "Cột mới (đợt 4a, 2026-09-29)" với các ý:
  - `so_goi_thung` (số gói / thùng, số nguyên) · `kl_goi_g` (khối lượng TỊNH một gói, gam). Chỉ ghi khi bảng in rõ; không suy từ kg thùng.
  - `bac`: JSON `[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]`. `don_vi_sl` ∈ thung/kg/goi/pallet, `don_vi_gia` ∈ thung/kg/goi, cùng `thue` của dòng. Ví dụ từ tháng 8:
    - NEXT "5cs: 5,300" → `[{"tu":5,"don_vi_sl":"thung","gia":5300,"don_vi_gia":"thung"}]`;
    - Vietnam House "25kg: 600y/kg | 50kg: 580y/kg" → hai bậc `don_vi_sl: "kg"`;
    - OBA "530¥/kg x 24kg; 510¥/kg x 48kg" → bậc 24 kg ¥530, 48 kg ¥510, và `gia_goc` = 530.
    - Chữ gốc vẫn chép vào `gia_bac`.
  - **`gia_goc` = giá mua LẺ nhỏ nhất** (1 thùng / 1 đơn vị), KHÔNG phải bậc rẻ nhất.
  - "Cùng hàng" (`nhan_ghep = cung_hang`) nay nghĩa là **cùng thương hiệu**. Khác quy cách vẫn là cùng thương hiệu, vì giá đã quy về ¥/kg.
  - Không ghi câu của người đọc vào `dieu_kien` ("chép vào…", "không in…", "Dữ liệu này…"). Câu đó vào sổ tay theo bên. Gói tự chuyển nó thành `ghi_chu_doc`.
  - File mới `spike_<bên>_giao_hang.csv`: cột = `COT_GIAO_HANG` trừ `ma_dong`, cộng `ben`, `file`. Mỗi bên MỘT dòng. `phu_phi` JSON `{"hokkaido": 800, "okinawa": "khong_nhan"}`. Không ghi = để trống, KHÔNG ghi 0. Ví dụ: IMAI, Vietnam House, Bùi Trâm, Ichiba — lấy từ bảng điều kiện tháng 8 (đặc tả §5.4 và bản vẽ tab Phí & giao hàng).
- [ ] **Step 2: `docs/doi-thu/so-tay-theo-ben.md`** — thêm cho từng bên đã thấy trong tháng 8:
  - **NEXT**: bậc "5cs / 2cs" in cạnh giá; kênh `tai_kho` / `gui` / `giao` là ba dòng; phí gửi "…円/cs + 冷蔵送料" để trống số → `cach_gui`, `phi_ship` NULL.
  - **Vietnam House**: bậc theo kg (25 / 50 kg); `gia_goc` phải là mức 25 kg; Hokkaido +¥1,200, Okinawa không nhận; daibiki ¥330 (CK trước không tính).
  - **OBA**: bậc "×24kg / ×48kg"; bán theo kg, không có thùng → `so_goi_thung` trống.
  - **Ichiba**: "Kiện 2 thùng Mix ok" → `thung_moi_kien` 2, `mien_ship_kien` 1, bao thuế.
  - **IMAI**: ¥605/thùng dưới ¥20,000, Tohoku ¥400, Hokkaido ¥800, daibiki ¥440.
  - **Bompex**: miễn ship và daibiki từ ¥20,000, Okinawa phụ thu (số không ghi).
  - **Eihatsu**: hai giá Daibiki / CK cho vài mặt hàng → hai dòng, `kenh_gia`.
- [ ] **Step 3: `CLAUDE.md`** — thêm một khối bất biến sau khối "064":

```markdown
**Bất biến (065–068, dữ liệu cho giao diện mới `/doi-thu` — chủ DN chốt 2026-09-29):**
- **Quy cách gói và giá bậc của đối thủ.** `so_goi_thung`, `kl_goi_g`, `bac` (jsonb, lược đồ ở 065) nằm trên
  `core.fact_gia_doi_thu` / `app.gia_doi_thu_tay`. Chữ `gia_bac` giữ làm nguyên văn.
  - `gia_goc` = giá LẺ (gói kiểm, `scripts/goi_doi_thu.py`).
  - Giá tại 1 / 5 / 10 thùng / pallet chỉ ở `mart.gia_doi_thu_quan_sat.gia_1/5/10/pallet`, qua MỘT hàm `mart.gia_bac_kg` (067).
  - Bậc theo kg / gói mà thiếu quy cách thì KHÔNG áp. Pallet chỉ khi bảng ghi rõ — không "1 pallet = 40 thùng".
  - Trung vị / bất thường / thấp / cao nhất của nhóm vẫn trên giá lẻ.
- **Sửa quy cách, bậc, khuyến mãi** đi qua `app.dinh_chinh_gia` (`doi_thu.TRUONG_SUA`). `''` / `[]` = xoá; chỉ
  `TRUONG_XOA_DUOC` mới xoá được.
- **kg KOME theo 荷姿 của OBC** (066). `core.dim_product.pack1_code`:
  - NULL = chưa nạp bản có cột → luật 060;
  - `''` = mã không có 荷姿 → một `'00'` là cả sản phẩm như tên ghi (xốt Barona / HVX: 80g × 20 × 4);
  - `'02'` → `kg_02 = pack1_base_qty × kg_00`.

  Đo thật: đây là nguyên nhân 15 nhóm giá KOME > 3× thị trường.
- **Bảng giá KOME** = `mart.gia_kome_bang` (¥/kg chưa thuế; luật hai cột: chưa thuế nếu > 0 và không mâu thuẫn,
  không thì gồm thuế ÷ 1,08).
  - 標準価格 = `price_level 'std'` (bộ nạp `tanka`); `mart.gia_kome_chuan`.
  - 売価No.10 = KHUYẾN MÃI: `mart.la_gia_km_kome`. Không vào dải giá thường, không bao giờ mặc định.
    `kome/san_pham_360.py::NHAN_BAC` là bản chép nhãn.
  - "Vị trí KOME" của `mart.so_sanh_nhom` so với 標準価格 (không có thì thực bán 90 ngày).
- **Điều kiện giao hàng** = `mart.giao_hang_hien_hanh` (068).
  - Đối thủ: lô mới nhất + đính chính ghi SAU lúc nạp lô đó (sổ chỉ thêm `app.dinh_chinh_giao_hang`).
  - KOME: `app.giao_hang_kome`. Một dòng, sửa được; mặc định SUY từ phiếu bán, `suy = true` tới khi chủ DN xác nhận
    (bằng chứng: `mart.giao_hang_kome_bang_chung`).
  - Điều kiện bán = `mart.dieu_kien_hien_hanh`: bỏ loại `ghi_chu_doc` (câu của người đọc, không phải của bên).
  - Mọi đường ghi (`kome/doi_thu_giao.py`) thêm dòng `app.doi_thu_nhat_ky` cùng giao dịch. Hai sổ mới KHÔNG có trong
    `_PHIEN_BAN`.
- **Phí của đơn mẫu**: MỘT thuật toán, hai bản — `kome/phi_giao.py` và `giao_dien/src/doi_thu/phi_giao.ts`. Chạy chung
  `tests/du_lieu/phi_giao_ca.json`; sửa một bản là sửa cả hai. NULL cần tới → `chua_ro`, không cộng 0.

Có test canh: `tests/test_doi_thu_bang.py`, `tests/test_mart_doi_thu.py`, `tests/test_doi_thu.py`,
`tests/test_doi_thu_giao.py`, `tests/test_phi_giao.py`, `tests/test_goi_doi_thu.py`, `tests/test_nap_doi_thu.py`.
**Migration 065–068 phải chạy TRƯỚC khi triển khai**. Sau đó nạp lại `商品データ` và `取引単価データ` mới nhất
(để có 荷姿 / 標準価格).
```

Trong bảng trang của CLAUDE.md, dòng `/doi-thu` cột "Dữ liệu lấy từ" thêm `mart.gia_kome_bang`, `mart.giao_hang_hien_hanh`, `mart.dieu_kien_hien_hanh`, `core.fact_giao_hang_doi_thu`.

- [ ] **Step 4: Sinh lại tài liệu sống, chạy CẢ bộ test**

```bash
python scripts/sinh_tai_lieu.py && python scripts/sinh_cot_dung.py
pytest -q
cd giao_dien && npx vitest run && cd ..
```

Expected: toàn bộ PASS (mốc trước đợt: 1568 pytest + 181 vitest; con số mới lớn hơn).

- [ ] **Step 5: Commit**

```bash
git add docs/doi-thu CLAUDE.md kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json
git commit -m "docs(doi-thu): dot 4a — so tay doc (quy cach goi, bac, giao hang), bat bien 065–068

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Ngoài kế hoạch này (làm trong phiên sau khi 4a xong, cần chủ DN đồng ý)

1. **Chạy 065–068 trên CSDL thật**: `python db/migrate.py` bằng `postgres`, cần chủ DN đồng ý. Sau đó kiểm chỉ đọc: không bảng nào bật RLS, quyền đúng, số dòng `so_sanh_nhom` không đổi.
2. **Nạp lại** `商品データ` + `取引単価データ` mới nhất (`/kho-du-lieu/nap`). Kiểm lại: 15 nhóm giá KOME lệch còn bao nhiêu.
3. **Đọc lại tháng 8** (§6.1 đặc tả): Claude đọc các file tháng 8 ra CSV mới (thêm quy cách gói, bậc, giao hàng), dựng gói bằng `scripts/goi_doi_thu.py`, rồi chủ DN nạp. Việc này dài; chia theo bên.
