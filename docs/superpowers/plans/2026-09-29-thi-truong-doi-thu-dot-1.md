# Thị trường & đối thủ — Đợt 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nạp bảng giá đối thủ (gói `.xlsx` do Claude dựng mỗi tháng) vào kho, cho sale duyệt/sửa trên web, và dựng màn `/doi-thu` (Tổng quan · So sánh · Hồ sơ đối thủ · Duyệt) cùng khối "giá đối thủ" ở Sản phẩm 360.

**Architecture:** Dòng nạp vào `core.fact_gia_doi_thu` / `core.fact_dieu_kien_doi_thu` qua đúng luồng nạp hai bước (5 cổng, hoàn tác theo lô). Sale ghi vào `app.*` (chỉ thêm cho đính chính / quan sát tay / nhật ký). Mọi chỉ số (quy đổi ¥/kg, ghép hiện hành, nhóm, bất thường, giá KOME) là view/hàm `mart`. `kome/doi_thu.py` chỉ hỏi `mart` và ghi `app`; `/api/doi-thu/*` qua ảnh chụp theo phiên bản; React ở `giao_dien/src/doi_thu/`.

**Tech Stack:** Postgres 17 (Supabase), Python 3 + psycopg 3 + FastAPI, pandas/calamine (bộ đọc), React + TS + TanStack Query + Vite, pytest, vitest.

**Spec:** `docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md` (đọc CẢ file trước khi làm bất kỳ task nào).

## Global Constraints

- Mã (`*code*`, `ma_*`, `jan`) là TEXT — không bao giờ ép số (bẫy #1).
- Không UPDATE/DELETE dòng `core` ngoài bộ nạp và hoàn tác; sửa của sale nằm ở `app`.
- `app.dinh_chinh_gia`, `app.gia_doi_thu_tay`, `app.doi_thu_nhat_ky` CHỈ THÊM: `REVOKE UPDATE, DELETE ... FROM kome_app`.
- Chỉ số chỉ định nghĩa ở `mart`. Tỷ số là tỷ số của các TỔNG. View mới đọc bảng bán phải đọc `mart.ban_den_moc`.
- Quay về theo mốc: quan sát chỉ thấy khi `ngay_nguon <= mart.moc_lui()` (hoặc `moc_lui()` NULL).
- Mọi bảng web ghi mà màn đọc phải vào `kome/web/anh_chup.py::_PHIEN_BAN`; ảnh chụp đọc chúng KHÔNG dùng `chi_nap=True`.
- Migration mới đánh số 059, 060; chạy bằng `postgres`; file đã chạy không bao giờ sửa.
- `kome/web/app.py` không nhập `kome.pipeline`/pandas ở mức ngoài cùng.
- Định dạng số chuẩn Nhật: chỉ qua `giao_dien/src/dinh_dang.ts` (không `toFixed(`, không `"de-DE"`).
- Mọi `history.pushState/replaceState` đi qua `giuKhoang()`.
- Sửa `giao_dien/` ⇒ `cd giao_dien && npm run build` (bản build commit ở `kome/web/spa/`).
- Sửa migration / files.yml / mã đọc cột ⇒ chạy `python scripts/sinh_tai_lieu.py` và `python scripts/sinh_cot_dung.py`.
- `kome_test` dùng chung: chạy pytest theo lượt, không ngắt giữa chừng (memory: pytest-orphan-lock, kome-test-shared).
- Commit message kết thúc bằng dòng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `db/migrations/059_doi_thu_bang.sql` | Bảng `core.fact_*doi_thu*`, bảng `app.*` của tính năng, seed 21 đối thủ + 5 loại nguồn, quyền |
| `db/migrations/060_mart_doi_thu.sql` | `mart.quy_cach_kome`, `mart.gia_kome_kg`, `mart.la_gia_bat_thuong`, `mart.gia_doi_thu_quan_sat`, `mart.gia_doi_thu_hien_hanh`, `mart.so_sanh_nhom` |
| `kome/loaders/doi_thu.py` | Hai bộ nạp `load_gia`, `load_dieu_kien` |
| `config/files.yml` | Hai spec `doi_thu_gia`, `doi_thu_dieu_kien` |
| `scripts/goi_doi_thu.py` | Dựng gói `.xlsx` từ CSV đọc được (khoá `ma_hang_dt`, kiểm giá/JAN, lọc trùng, suy `muc_gia`/`sap_ve`/`ngay_nguon`) |
| `kome/doi_thu.py` | Đọc (`tong_quan`, `so_sanh`, `ho_so_ben`, `duyet`, `khoi_san_pham`) + ghi (`xac_nhan`, `sua`, `gia_moi`, `dat_ghep`, `tao_nhom`, `sua_quy_cach`) |
| `kome/web/api.py` | `/api/doi-thu/*` (GET + POST), `/api/san-pham/{ma}/doi-thu` |
| `kome/web/app.py` | Route `/doi-thu` |
| `kome/web/anh_chup.py` | `_PHIEN_BAN` + 3 bảng |
| `kome/nhat_ky.py` | Nhánh `doi_thu` của `_NGUON` |
| `giao_dien/src/doi_thu/*` | `ManDoiThu.tsx`, `TabTongQuan.tsx`, `TabSoSanh.tsx`, `TabHoSo.tsx`, `TabDuyet.tsx`, `kieu.ts`, `loc.ts`, `loc.test.ts`, `doi_thu.css` |
| `giao_dien/src/san_pham/ho_so/KhoiDoiThu.tsx` | Khối cột trái Sản phẩm 360 |
| `docs/doi-thu/huong-dan-doc.md`, `docs/doi-thu/so-tay-theo-ben.md` | Hướng dẫn đọc (từ `HUONG_DAN.md` phép thử) + luật riêng từng bên |
| Tests | `tests/test_doi_thu_bang.py`, `tests/test_nap_doi_thu.py`, `tests/test_goi_doi_thu.py`, `tests/test_mart_doi_thu.py`, `tests/test_doi_thu.py`, `tests/test_doi_thu_api.py` |

---

### Task 0: Nhánh, đặc tả, tài liệu đọc

**Files:**
- Create: `docs/doi-thu/huong-dan-doc.md`, `docs/doi-thu/so-tay-theo-ben.md`
- Commit: `docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md`, file plan này

- [ ] **Step 1: Tạo nhánh từ HEAD hiện tại** (`feat/mua-vu` — migration 058 nằm ở đó, nên 059/060 phải đi sau nó)

```bash
git switch -c feat/doi-thu
```

- [ ] **Step 2: Chép hướng dẫn đọc vào repo**

Chép nguyên văn `HUONG_DAN.md` của phép thử (thư mục tạm của phiên: `C:\Users\TRANTR~1\AppData\Local\Temp\claude\C--Antigravity-kome-data\abd73e57-76bc-42c2-972f-2c0ca8050dd8\scratchpad\HUONG_DAN.md`) vào `docs/doi-thu/huong-dan-doc.md`, rồi THÊM hai cột vào bảng File 1 (sau `kenh_gia`):

```markdown
| muc_gia | mức khách nếu nguồn có nhiều mức: `thuong` · `dac_biet` (Thái Dương "special") · `pallet` · `khach_ngoai` (VIETCOOK) · `kyushu` · trống nếu chỉ một mức |
```

và đổi dòng `trang_thai` thành:

```markdown
| trang_thai | `con` · `het` (SOLD OUT/TẠM HẾT) · `sap_ve` ("dự kiến … xuất", "入荷予定") · `khong_ro` |
```

- [ ] **Step 3: Viết sổ tay theo bên** — `docs/doi-thu/so-tay-theo-ben.md`:

```markdown
# Sổ tay theo bên — luật đọc rút ra từ các lần đọc / sửa trước

Mỗi luật: bên · điều gì · làm gì · nguồn (tháng, ai phát hiện). Claude đọc file này TRƯỚC mỗi lần đọc.

## Nguồn web (ưu tiên hơn file)
- HSC — `app.hscstation.com` đọc Google Sheet công khai (link trong `data.js`). Giá `priceJPY` là giá CẢ `spec`
  (thường là thùng), ĐÃ gồm thuế. `priceJPY` 0 hoặc < 50 = lỗi của web → `can_xem`. Bậc giá / giá Kyushu nằm ở `description`.
- THAI-DUONG — `tdmvn.shop`, API `https://api.tdmvn.shop/sync-products?revision=0`. Bỏ `deleted: true`.
  Hai mức: `branches.main` (`muc_gia=thuong`), `branches.special` (`muc_gia=dac_biet`, ~0,91× main, "mix từ 3th").
  Trường `sale` là bậc giá theo số thùng → `gia_bac`, không phải khuyến mãi.
- JVB — `jvbfood.asia` WooCommerce, trang danh sách công khai (Store API trả 404 → đọc trang).
- THAK — `thak.jp` WooCommerce Store API `/wp-json/wc/store/v1/products?per_page=100&page=N` (385 mã 2026-09-29).
  `prices.price` có `currency_minor_unit=1` ("80400" = ¥8.040) và là giá CẢ đơn vị bán (thùng / kiện).
  Giá đơn vị lấy từ `short_description` ("335 yên/dây"), KIỂM CHÉO bằng giá ÷ số đơn vị — giá trong TÊN đôi khi cũ.
  Giá web = giá ĐÃ gồm thuế (khớp đúng 税込 của PDF). File "25-06-THAK-THAI-LAN" có thể là bảng giá cũ.

## File
- NEXT — mỗi mã 3 giá: `tai_kho` / `giao` / `gui` (+送料別). "8月 (値段:税抜)" = chưa thuế. Ảnh có thể gửi TRÙNG trang (tháng 8: 2ef88dbb = trang 19).
- IMAI — mỗi bảng in cả cột 税抜 và 税込 → một dòng chưa thuế, giá có thuế vào `ghi_chu` (script gộp tự làm).
- ICHIBA — in "Barona 110g x 80" cho mọi sốt ¥95, thật là 80g (KOME BA*).
- MUNDIAL — giá "y" = yên, "chưa bao gồm thuế 8%" ở đầu file; ô gộp nhiều mã; ô "0y" / trống = không có giá.
- NICHIETSU — dấu TẠM HẾT đóng trên ẢNH sản phẩm, không trên dòng bảng.
- DAIICHI — "Khối lượng 1kg" + giá = ¥/kg; STT đánh lại theo từng mục; ảnh chụp màn hình chồng nhau.
- VIETCOOK — ba mức: xanh "Giá tại kho" (`kenh_gia=tai_kho`), cam "khách Vietcook = Pallet" (`muc_gia=pallet`), xanh lá "khách ngoài" (`muc_gia=khach_ngoai`).
- BOMPEX — có JAN; tem "Dự kiến tháng 9 / 19/8 xuất hàng" = `sap_ve`.
- YUMI — footer "Kiện 28kg ghép 3 (hoặc 4) sản phẩm - bao thuế bao ship".
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md docs/superpowers/plans/2026-09-29-thi-truong-doi-thu-dot-1.md docs/doi-thu/
git commit -m "docs(doi-thu): dac ta, ke hoach dot 1, huong dan doc va so tay theo ben

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 1: Migration 059 — bảng và quyền

**Files:**
- Create: `db/migrations/059_doi_thu_bang.sql`
- Modify: `tests/conftest.py` (thêm `app.loai_nguon`, `app.doi_thu` vào `GIU_LAI`)
- Test: `tests/test_doi_thu_bang.py`

**Interfaces:**
- Produces: bảng `core.fact_gia_doi_thu`, `core.fact_dieu_kien_doi_thu`, `app.doi_thu`, `app.loai_nguon`, `app.nhom_so_sanh`, `app.nhom_so_sanh_ma`, `app.ghep_hang`, `app.dinh_chinh_gia`, `app.gia_doi_thu_tay`, `app.quy_cach_kome`, `app.doi_thu_nhat_ky` (cột như SQL dưới).

- [ ] **Step 1: Viết test hỏng** — `tests/test_doi_thu_bang.py`:

```python
"""Migration 059 — bảng Thị trường & đối thủ (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4)."""


def _quyen(conn, vai, bang, q):
    return conn.execute("SELECT has_table_privilege(%s, %s, %s)", (vai, bang, q)).fetchone()[0]


def test_ba_so_CHI_THEM_kome_app_khong_sua_khong_xoa_duoc(conn):
    for bang in ("app.dinh_chinh_gia", "app.gia_doi_thu_tay", "app.doi_thu_nhat_ky"):
        assert _quyen(conn, "kome_app", bang, "INSERT"), bang
        assert _quyen(conn, "kome_app", bang, "SELECT"), bang
        assert not _quyen(conn, "kome_app", bang, "UPDATE"), bang
        assert not _quyen(conn, "kome_app", bang, "DELETE"), bang


def test_bang_nap_chi_kome_ingest_ghi_duoc(conn):
    for bang in ("core.fact_gia_doi_thu", "core.fact_dieu_kien_doi_thu"):
        assert _quyen(conn, "kome_ingest", bang, "INSERT"), bang
        assert _quyen(conn, "kome_ingest", bang, "DELETE"), bang     # nút Hoàn tác
        assert _quyen(conn, "kome_app", bang, "SELECT"), bang
        assert not _quyen(conn, "kome_app", bang, "INSERT"), bang
        assert not _quyen(conn, "kome_app", bang, "UPDATE"), bang


def test_bang_sua_duoc_cua_app(conn):
    for bang in ("app.ghep_hang", "app.nhom_so_sanh", "app.nhom_so_sanh_ma", "app.quy_cach_kome", "app.doi_thu"):
        assert _quyen(conn, "kome_app", bang, "UPDATE"), bang


def test_seed_loai_nguon_va_doi_thu(conn):
    ln = conn.execute("SELECT ma, thu_tu FROM app.loai_nguon ORDER BY thu_tu").fetchall()
    assert ln == [("bang_gia", 1), ("chung_tu", 2), ("to_roi", 3), ("khach_ke", 4), ("khac", 5)]
    ma = {r[0] for r in conn.execute("SELECT ma FROM app.doi_thu")}
    assert {"THAK", "HSC", "THAI-DUONG", "NEXT", "QUANG-KE", "VIPRO"} <= ma and len(ma) == 21


def test_dinh_chinh_chi_nhan_truong_hop_le(conn):
    import psycopg, pytest
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (1, 'xoa_het', 'x')")
    conn.rollback()


def test_gia_tay_bat_buoc_loai_nguon_co_that(conn):
    import psycopg, pytest
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute("""INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, loai_nguon)
                        VALUES ('THAK', 'x', 'x', 'bua')""")
    conn.rollback()
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_doi_thu_bang.py -v`
Expected: FAIL (`relation "app.dinh_chinh_gia" does not exist`)

- [ ] **Step 3: Viết migration** — `db/migrations/059_doi_thu_bang.sql`:

```sql
-- 059 — Thị trường & đối thủ: bảng (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4).
--
-- core = thứ NẠP qua cổng (kome_ingest, batch_id, hoàn tác theo lô) · app = thứ WEB GHI (kome_app).
-- Đối thủ không phải OBC nhưng luật "không UPDATE core" áp nguyên: sửa của sale ở app.
-- KHÔNG có khoá ngoại từ app sang core.fact_gia_doi_thu: hoàn tác lô phải xoá được dòng core;
-- đính chính mồ côi thì mart bỏ qua (060).

CREATE TABLE core.fact_gia_doi_thu (
    id                 bigserial PRIMARY KEY,
    batch_id           bigint NOT NULL REFERENCES meta.ingest_batch(batch_id),
    ma_dong            text   NOT NULL,
    ma_doi_thu         text   NOT NULL,
    ma_hang_dt         text   NOT NULL,
    ngay_nguon         date   NOT NULL,
    hinh_thuc_nguon    text   NOT NULL CHECK (hinh_thuc_nguon IN ('file', 'web')),
    nguon_file         text,
    vi_tri             text,
    ten_goc            text   NOT NULL,
    ten_nhat           text,
    jan                text,
    quy_cach_goc       text,
    gia_goc            numeric(12,2),
    don_vi_gia         text,
    kg_moi_don_vi_gia  numeric(12,4),
    thue               text   CHECK (thue IN ('chua', 'co', 'khong_ro')),
    gom_ship           text   CHECK (gom_ship IN ('co', 'khong', 'khong_ro')),
    kenh_gia           text,
    muc_gia            text,
    gia_bac            text,
    gia_truoc_km       numeric(12,2),
    trang_thai         text   NOT NULL CHECK (trang_thai IN ('con', 'het', 'sap_ve', 'khong_ro')),
    han_su_dung        text,
    khuyen_mai         text,
    ma_kome_de_xuat    text,
    nhan_de_xuat       text   CHECK (nhan_de_xuat IN ('cung_hang', 'thay_the')),
    ly_do_ghep         text,
    do_chac            text   NOT NULL CHECK (do_chac IN ('chac', 'can_xem')),
    ghi_chu            text,
    UNIQUE (batch_id, ma_dong)
);
CREATE INDEX fact_gia_doi_thu_hang ON core.fact_gia_doi_thu (ma_doi_thu, ma_hang_dt);

CREATE TABLE core.fact_dieu_kien_doi_thu (
    id          bigserial PRIMARY KEY,
    batch_id    bigint NOT NULL REFERENCES meta.ingest_batch(batch_id),
    ma_dong     text   NOT NULL,
    ma_doi_thu  text   NOT NULL,
    ngay_nguon  date   NOT NULL,
    nguon_file  text,
    vi_tri      text,
    loai        text   NOT NULL CHECK (loai IN ('ship', 'khuyen_mai', 'thanh_toan', 'thue', 'khac')),
    noi_dung    text   NOT NULL,
    UNIQUE (batch_id, ma_dong)
);

CREATE TABLE app.doi_thu (
    ma             text PRIMARY KEY,
    ten            text NOT NULL,
    web            text,
    ghi_chu        text,
    dang_theo_doi  boolean NOT NULL DEFAULT true
);
INSERT INTO app.doi_thu (ma, ten, web) VALUES
 ('ASIA-TRADING', 'Asia Trading', NULL), ('BOMPEX', 'Bompex Japan', NULL), ('BUI-TRAM', 'Bùi Trâm', NULL),
 ('DAIICHI', '第一株式会社 (Daiichi)', NULL), ('EIHATSU', 'Eihatsu', NULL), ('HSC', 'HSC Station', 'https://app.hscstation.com/'),
 ('ICHIBA', 'Ichiba Foods', NULL), ('IMAI', 'IMAI', NULL), ('JVB', 'JVB Food', 'https://jvbfood.asia/'),
 ('MT-ONE', 'MT-One', NULL), ('MUNDIAL', 'Mundial Foods', 'https://www.mundialfoods.co.jp/'),
 ('NEXT', 'NEXT', NULL), ('NICHIETSU', '日越合同会社 (Nichietsu)', NULL), ('OBA', 'OBA', NULL),
 ('THAI-DUONG', 'Thái Dương Mart', 'https://tdmvn.shop/all-products'), ('THAK', 'THAK JSC', 'https://thak.jp/'),
 ('VIETCOOK', 'Vietcook', NULL), ('VIETNAM-HOUSE', 'Vietnam House', NULL), ('YUMI', 'Yumi Foods', NULL),
 ('QUANG-KE', 'Quảng Kẹ', NULL), ('VIPRO', 'ViPro', 'https://sale.vipro-jp.com/');

CREATE TABLE app.loai_nguon (
    ma              text PRIMARY KEY,
    ten             text NOT NULL,
    thu_tu          int  NOT NULL UNIQUE,     -- độ tin cậy, 1 = cao nhất
    can_bang_chung  boolean NOT NULL DEFAULT false
);
INSERT INTO app.loai_nguon VALUES
 ('bang_gia', 'Bảng giá / web của đối thủ', 1, false),
 ('chung_tu', 'Chứng từ khách đưa (hoá đơn, phiếu giao)', 2, true),
 ('to_roi',   'Tờ rơi / tin nhắn đối thủ gửi', 3, true),
 ('khach_ke', 'Khách kể', 4, false),
 ('khac',     'Nghe nói / khác', 5, false);

CREATE TABLE app.nhom_so_sanh (
    id   bigserial PRIMARY KEY,
    ten  text NOT NULL UNIQUE CHECK (length(btrim(ten)) BETWEEN 1 AND 80)
);
CREATE TABLE app.nhom_so_sanh_ma (
    product_code  text PRIMARY KEY,
    nhom_id       bigint NOT NULL REFERENCES app.nhom_so_sanh(id) ON DELETE CASCADE
);

CREATE TABLE app.ghep_hang (
    ma_doi_thu     text NOT NULL,
    ma_hang_dt     text NOT NULL,
    product_code   text,
    nhom_id        bigint REFERENCES app.nhom_so_sanh(id) ON DELETE SET NULL,
    nhan           text NOT NULL CHECK (nhan IN ('cung_hang', 'thay_the', 'khong')),
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ma_doi_thu, ma_hang_dt)
);

CREATE TABLE app.dinh_chinh_gia (
    id             bigserial PRIMARY KEY,
    fact_id        bigint NOT NULL,
    truong         text   NOT NULL CHECK (truong IN ('xac_nhan', 'ten_goc', 'quy_cach_goc', 'gia_goc',
                        'don_vi_gia', 'kg_moi_don_vi_gia', 'thue', 'gom_ship', 'kenh_gia', 'muc_gia', 'trang_thai')),
    gia_tri_moi    text,
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX dinh_chinh_gia_fact ON app.dinh_chinh_gia (fact_id, truong, id DESC);

CREATE TABLE app.gia_doi_thu_tay (
    id                 bigserial PRIMARY KEY,
    ma_doi_thu         text NOT NULL REFERENCES app.doi_thu(ma),
    ma_hang_dt         text NOT NULL,
    fact_goc_id        bigint,                   -- dòng nạp mà quan sát này cập nhật (NULL = hàng mới)
    ten_goc            text NOT NULL CHECK (length(btrim(ten_goc)) > 0),
    quy_cach_goc       text,
    gia_goc            numeric(12,2) CHECK (gia_goc IS NULL OR gia_goc >= 0),
    don_vi_gia         text,
    kg_moi_don_vi_gia  numeric(12,4) CHECK (kg_moi_don_vi_gia IS NULL OR kg_moi_don_vi_gia > 0),
    thue               text CHECK (thue IN ('chua', 'co', 'khong_ro')),
    gom_ship           text CHECK (gom_ship IN ('co', 'khong', 'khong_ro')),
    kenh_gia           text,
    muc_gia            text,
    trang_thai         text NOT NULL DEFAULT 'con' CHECK (trang_thai IN ('con', 'het', 'sap_ve', 'khong_ro')),
    loai_nguon         text NOT NULL REFERENCES app.loai_nguon(ma),
    ghi_chu_nguon      text,
    customer_code      text,
    tiep_xuc_id        bigint,
    nguoi_dung_id      bigint REFERENCES app.nguoi_dung(id),
    luc                timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app.quy_cach_kome (
    product_code   text PRIMARY KEY,
    kg_moi_goi     numeric(12,4) CHECK (kg_moi_goi IS NULL OR kg_moi_goi > 0),
    goi_moi_thung  numeric(12,2) CHECK (goi_moi_thung IS NULL OR goi_moi_thung > 0),
    kg_moi_thung   numeric(12,4) CHECK (kg_moi_thung IS NULL OR kg_moi_thung > 0)
);

CREATE TABLE app.doi_thu_nhat_ky (
    id             bigserial PRIMARY KEY,
    loai           text NOT NULL CHECK (loai IN ('xac_nhan', 'sua', 'gia_moi', 'them', 'ghep', 'nhom', 'quy_cach', 'doi_thu')),
    doi_tuong      text NOT NULL,
    truoc          jsonb,
    sau            jsonb,
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now()
);

-- Quyền. Default privileges của 009/010 đã cấp: core → ingest SELECT/INSERT/UPDATE/DELETE, app & report SELECT;
-- app → kome_app CRUD, report SELECT. Ghi lại cho rõ và rút UPDATE/DELETE ở ba sổ chỉ thêm (nếp 030).
GRANT SELECT, INSERT, UPDATE, DELETE ON core.fact_gia_doi_thu, core.fact_dieu_kien_doi_thu TO kome_ingest;
GRANT SELECT ON core.fact_gia_doi_thu, core.fact_dieu_kien_doi_thu TO kome_app, kome_report;
REVOKE INSERT, UPDATE, DELETE ON core.fact_gia_doi_thu, core.fact_dieu_kien_doi_thu FROM kome_app;
GRANT SELECT ON app.ghep_hang, app.nhom_so_sanh, app.nhom_so_sanh_ma, app.doi_thu TO kome_ingest;  -- Claude đọc cặp ghép khi dựng gói
REVOKE UPDATE, DELETE ON app.dinh_chinh_gia, app.gia_doi_thu_tay, app.doi_thu_nhat_ky FROM kome_app;
```

- [ ] **Step 4: Thêm hai bảng tham chiếu vào `GIU_LAI`** — `tests/conftest.py`, đoạn `GIU_LAI = {...}`:

```python
GIU_LAI = {"meta.schema_migration", "core.dim_date", "core.dim_salesperson",
           "core.dim_prefecture", "app.loai_nguon", "app.doi_thu"}
```

và thêm vào chú thích ngay trên:

```python
#  - app.loai_nguon, app.doi_thu: gieo TĨNH bởi 059 (5 loại nguồn, 21 đối thủ), bảng khác
#    trỏ khoá ngoại vào — cùng lý do với core.dim_prefecture.
```

- [ ] **Step 5: Chạy test**

Run: `pytest tests/test_doi_thu_bang.py tests/test_roles.py tests/test_migrate.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add db/migrations/059_doi_thu_bang.sql tests/conftest.py tests/test_doi_thu_bang.py
git commit -m "feat(doi-thu): migration 059 — bang nap, bang app, quyen chi-them

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Hai spec + bộ nạp + đăng ký trong mọi danh mục

**Files:**
- Modify: `config/files.yml` (thêm cuối file), `kome/pipeline.py:19-51` (`LOADERS`, `UNDO_TABLES`), `kome/nhat_ky_nap.py` (`BANG_THEO_LOAI`, `TEN_BANG_VI`), `kome/kho_du_lieu.py:24-33` (`O_NAP`), `kome/coverage.py:75-84` (`COT`)
- Create: `kome/loaders/doi_thu.py`
- Test: `tests/test_nap_doi_thu.py`

**Interfaces:**
- Consumes: bảng của Task 1.
- Produces: spec `doi_thu_gia` / `doi_thu_dieu_kien`; `kome.loaders.doi_thu.COT_GIA: list[str]`, `COT_DIEU_KIEN: list[str]` (thứ tự cột của gói — Task 3 dùng), `load_gia(conn, df, data_date, batch_id) -> int`, `load_dieu_kien(...) -> int`.

- [ ] **Step 1: Viết test hỏng** — `tests/test_nap_doi_thu.py`:

```python
"""Nạp gói bảng giá đối thủ qua luồng nạp chung (5 cổng, hoàn tác theo lô)."""
from datetime import date
import pandas as pd

from kome.loaders.doi_thu import COT_GIA, COT_DIEU_KIEN
from kome.pipeline import ingest, undo_batch


def _dong(i, **kw):
    d = {c: None for c in COT_GIA}
    d.update(ma_dong=f"THAK-{i:05d}", ma_doi_thu="THAK", ma_hang_dt=f"jan:893000000000{i}",
             ngay_nguon="2026-08-05", hinh_thuc_nguon="file", nguon_file="THAK-HANG-KHO.pdf",
             vi_tri=f"tr{i}", ten_goc=f"Hàng {i}", gia_goc="335", don_vi_gia="goi",
             kg_moi_don_vi_gia="0.052", thue="co", gom_ship="khong_ro", trang_thai="con", do_chac="chac")
    d.update(kw)
    return d


def _goi_gia(tmp_path, dong, ngay="20260831"):
    p = tmp_path / f"doi_thu_gia_{ngay}.xlsx"
    pd.DataFrame(dong, columns=COT_GIA).to_excel(p, sheet_name="gia", index=False)
    return p


def test_nap_gia_giu_ma_la_chu_va_gia_trong_la_NULL(conn, tmp_path):
    p = _goi_gia(tmp_path, [_dong(1), _dong(2, gia_goc=None, jan="0012345678905"), _dong(3, gia_goc="172.5")])
    r = ingest(conn, p, tmp_path / "archive")
    assert r.ok, r.blockers
    rows = conn.execute("SELECT ma_dong, gia_goc, jan, ngay_nguon FROM core.fact_gia_doi_thu ORDER BY ma_dong").fetchall()
    assert rows[0][1] == 335 and rows[1][1] is None and float(rows[2][1]) == 172.5
    assert rows[1][2] == "0012345678905"          # số 0 đầu còn nguyên (bẫy #1)
    assert rows[0][3] == date(2026, 8, 5)


def test_hoan_tac_xoa_sach_lo(conn, tmp_path):
    r = ingest(conn, _goi_gia(tmp_path, [_dong(1), _dong(2)]), tmp_path / "archive")
    undo_batch(conn, r.batch_id)
    assert conn.execute("SELECT count(*) FROM core.fact_gia_doi_thu").fetchone()[0] == 0


def test_dieu_kien_nap_rieng(conn, tmp_path):
    p = tmp_path / "doi_thu_dieu_kien_20260831.xlsx"
    pd.DataFrame([{"ma_dong": "YUMI-00001", "ma_doi_thu": "YUMI", "ngay_nguon": "2026-08-01",
                   "nguon_file": "YUMI FOODS.pdf", "vi_tri": "tr1", "loai": "ship",
                   "noi_dung": "Kiện 28kg ghép 3 sản phẩm - bao thuế bao ship!"}],
                 columns=COT_DIEU_KIEN).to_excel(p, sheet_name="dieu_kien", index=False)
    assert ingest(conn, p, tmp_path / "archive").ok
    assert conn.execute("SELECT loai FROM core.fact_dieu_kien_doi_thu").fetchone()[0] == "ship"


def test_mot_o_nap_nhan_ca_hai_loai_file():
    from kome.kho_du_lieu import O_CUA
    assert O_CUA["doi_thu"]["specs"] == ["doi_thu_gia", "doi_thu_dieu_kien"]
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_nap_doi_thu.py -v`
Expected: FAIL (`ModuleNotFoundError: kome.loaders.doi_thu`)

- [ ] **Step 3: Bộ nạp** — `kome/loaders/doi_thu.py`:

```python
"""Bộ nạp gói bảng giá đối thủ (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4.1).

Gói do scripts/goi_doi_thu.py dựng — tên cột của file = tên cột hệ thống (files.yml khai
ánh xạ đồng nhất). `gia_goc`, `gia_truoc_km`, `kg_moi_don_vi_gia` KHÔNG khai money_columns:
bộ đọc ép ô trống thành 0, còn ở đây trống ≠ 0 và có giá lẻ .5 yên — đổi sang số ở ĐÂY.
Chỉ INSERT (mỗi lô là một lần đọc; lô mới hơn thắng ở mart), không upsert.
"""
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
import psycopg

COT_GIA = [
    "ma_dong", "ma_doi_thu", "ma_hang_dt", "ngay_nguon", "hinh_thuc_nguon", "nguon_file", "vi_tri",
    "ten_goc", "ten_nhat", "jan", "quy_cach_goc", "gia_goc", "don_vi_gia", "kg_moi_don_vi_gia",
    "thue", "gom_ship", "kenh_gia", "muc_gia", "gia_bac", "gia_truoc_km", "trang_thai", "han_su_dung",
    "khuyen_mai", "ma_kome_de_xuat", "nhan_de_xuat", "ly_do_ghep", "do_chac", "ghi_chu",
]
COT_DIEU_KIEN = ["ma_dong", "ma_doi_thu", "ngay_nguon", "nguon_file", "vi_tri", "loai", "noi_dung"]
_SO = {"gia_goc", "gia_truoc_km", "kg_moi_don_vi_gia"}


def _so(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return None
    try:
        return Decimal(str(v).replace(",", "").strip())
    except InvalidOperation:
        return None


def _chu(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None


def _gia_tri(cot, v, data_date):
    if cot in _SO:
        return _so(v)
    if cot == "ngay_nguon":
        return v or data_date
    return _chu(v)


def _nap(conn, bang, cot, df, data_date, batch_id) -> int:
    rows = [tuple(_gia_tri(c, getattr(r, c), data_date) for c in cot) + (batch_id,)
            for r in df.itertuples(index=False)]
    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO {bang} ({', '.join(cot)}, batch_id) VALUES ({', '.join(['%s'] * (len(cot) + 1))})",
            rows)
    conn.commit()
    return len(rows)


def load_gia(conn: psycopg.Connection, df: pd.DataFrame, data_date: date, batch_id: int) -> int:
    return _nap(conn, "core.fact_gia_doi_thu", COT_GIA, df, data_date, batch_id)


def load_dieu_kien(conn: psycopg.Connection, df: pd.DataFrame, data_date: date, batch_id: int) -> int:
    return _nap(conn, "core.fact_dieu_kien_doi_thu", COT_DIEU_KIEN, df, data_date, batch_id)
```

- [ ] **Step 4: Hai spec** — thêm vào cuối `config/files.yml`:

```yaml
# Thị trường & đối thủ (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4.1). KHÔNG phải file OBC:
# gói do scripts/goi_doi_thu.py dựng từ bảng giá / web đối thủ. Tên cột = tên hệ thống.
# warn_row_drop_ratio 0: tháng này 19 bên, tháng sau 5 bên cập nhật — số dòng "sụt" là bình thường.
# jan / ma_kome_de_xuat KHÔNG vào code_columns: cổng 3 chặn cột mã trống toàn bộ, mà nhiều gói không có JAN.
doi_thu_gia:
  display_name: Bảng giá đối thủ
  core_table: core.fact_gia_doi_thu
  filename_pattern: '^doi_thu_gia_(?P<date>\d{8})\.xlsx$'
  sheet: gia
  header_row: 1
  min_rows: 1
  keys: [ma_dong]
  columns: {ma_dong: ma_dong, ma_doi_thu: ma_doi_thu, ma_hang_dt: ma_hang_dt, ngay_nguon: ngay_nguon,
            hinh_thuc_nguon: hinh_thuc_nguon, nguon_file: nguon_file, vi_tri: vi_tri, ten_goc: ten_goc,
            ten_nhat: ten_nhat, jan: jan, quy_cach_goc: quy_cach_goc, gia_goc: gia_goc, don_vi_gia: don_vi_gia,
            kg_moi_don_vi_gia: kg_moi_don_vi_gia, thue: thue, gom_ship: gom_ship, kenh_gia: kenh_gia,
            muc_gia: muc_gia, gia_bac: gia_bac, gia_truoc_km: gia_truoc_km, trang_thai: trang_thai,
            han_su_dung: han_su_dung, khuyen_mai: khuyen_mai, ma_kome_de_xuat: ma_kome_de_xuat,
            nhan_de_xuat: nhan_de_xuat, ly_do_ghep: ly_do_ghep, do_chac: do_chac, ghi_chu: ghi_chu}
  code_columns: [ma_dong, ma_doi_thu, ma_hang_dt]
  money_columns: []
  qty_columns: []
  date_columns: [ngay_nguon]
  required_date_columns: [ngay_nguon]
  warn_row_drop_ratio: 0

doi_thu_dieu_kien:
  display_name: Điều kiện bán của đối thủ
  core_table: core.fact_dieu_kien_doi_thu
  filename_pattern: '^doi_thu_dieu_kien_(?P<date>\d{8})\.xlsx$'
  sheet: dieu_kien
  header_row: 1
  min_rows: 1
  keys: [ma_dong]
  columns: {ma_dong: ma_dong, ma_doi_thu: ma_doi_thu, ngay_nguon: ngay_nguon, nguon_file: nguon_file,
            vi_tri: vi_tri, loai: loai, noi_dung: noi_dung}
  code_columns: [ma_dong, ma_doi_thu]
  money_columns: []
  qty_columns: []
  date_columns: [ngay_nguon]
  required_date_columns: [ngay_nguon]
  warn_row_drop_ratio: 0
```

- [ ] **Step 5: Đăng ký ở mọi danh mục** (test sẵn có canh từng chỗ)

`kome/pipeline.py` — dòng import: `from kome.loaders import inventory, customer, sales, master, price, so_cai, doi_thu`; thêm vào `LOADERS`:

```python
    "doi_thu_gia": doi_thu.load_gia,
    "doi_thu_dieu_kien": doi_thu.load_dieu_kien,
```

vào `UNDO_TABLES`:

```python
    "doi_thu_gia": ["core.fact_gia_doi_thu"],
    "doi_thu_dieu_kien": ["core.fact_dieu_kien_doi_thu"],
```

`kome/nhat_ky_nap.py` — `BANG_THEO_LOAI` thêm đúng hai dòng như `UNDO_TABLES`; `TEN_BANG_VI` thêm:

```python
    "doi_thu_gia": "bảng giá đối thủ",
    "doi_thu_dieu_kien": "điều kiện bán của đối thủ",
```

`kome/kho_du_lieu.py` — `O_NAP` thêm dòng cuối:

```python
    {"ma": "doi_thu", "nhan": "Bảng giá đối thủ", "specs": ["doi_thu_gia", "doi_thu_dieu_kien"], "nhip": "ky"},
```

`kome/coverage.py` — `COT` thêm dòng cuối:

```python
    CotLoaiFile("DT", "doi_thu_gia", "Bảng giá đối thủ", "bảng giá đối thủ (không phải OBC), ô có khi tháng có gói"),
```

Rồi đọc `kome/coverage.py::tinh_luoi_phu` và kiểm cột mới đi đúng nhánh "không theo ngày" như `shohin` (không bị tính "thiếu n ngày làm việc"); nếu hàm có nhánh theo từng `khoa`, thêm `"doi_thu_gia"` vào đúng tập của `shohin`.

- [ ] **Step 6: Sinh lại tài liệu sống, chạy test**

```bash
python scripts/sinh_tai_lieu.py
python scripts/sinh_cot_dung.py
pytest tests/test_nap_doi_thu.py tests/test_pipeline.py tests/test_tai_lieu.py tests/test_nhat_ky_nap.py tests/test_cot_dung.py tests/test_kho_du_lieu*.py -v
```

Expected: PASS. Nếu `test_cot_dung.py` báo cột nạp mà chưa ai đọc: đúng — Task 4 sẽ đọc; chạy lại `sinh_cot_dung.py` sau Task 4.

- [ ] **Step 7: Commit**

```bash
git add config/files.yml kome/loaders/doi_thu.py kome/pipeline.py kome/nhat_ky_nap.py kome/kho_du_lieu.py kome/coverage.py kome/web/*.json tests/test_nap_doi_thu.py
git commit -m "feat(doi-thu): bo nap goi bang gia doi thu, o nap rieng, hoan tac theo lo

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Script dựng gói — `scripts/goi_doi_thu.py`

**Files:**
- Create: `scripts/goi_doi_thu.py`, `kome/ten_hang.py`
- Test: `tests/test_goi_doi_thu.py`

**Interfaces:**
- Consumes: `kome.loaders.doi_thu.COT_GIA`, `COT_DIEU_KIEN`; CSV theo `docs/doi-thu/huong-dan-doc.md` (`spike_<bên>[_<phần>].csv`, `..._dieu_kien.csv`, UTF-8 BOM).
- Produces: `jan_hop_le(s: str) -> bool`, `chuan_ten(s: str) -> str`, `ma_hang_dt(dong: dict) -> str`, `suy_muc_gia(dong) -> str | None`, `suy_trang_thai(dong) -> str`, `suy_ngay(file: str, mac_dinh: date) -> date`, `dung_goi(gia: list[dict], dk: list[dict], ngay: date) -> tuple[list[dict], list[dict], list[str]]`; CLI `python scripts/goi_doi_thu.py <thư mục CSV> --ngay YYYY-MM-DD --ra <thư mục>` ghi `doi_thu_gia_YYYYMMDD.xlsx` + `doi_thu_dieu_kien_YYYYMMDD.xlsx`.

- [ ] **Step 1: Viết test hỏng** — `tests/test_goi_doi_thu.py`:

```python
"""Dựng gói bảng giá đối thủ (đặc tả §4.1, §4.3, §7)."""
from datetime import date
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("goi", Path("scripts/goi_doi_thu.py"))
G = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(G)


def _d(**kw):
    d = {"ben": "THAK", "file": "THAK-HANG-KHO-2026.08.05.pdf", "vi_tri": "tr1", "ten_goc": "Bột năng Tài Ký 400g",
         "jan": "", "quy_cach_goc": "400g x 24", "gia_goc": "180", "don_vi_gia": "goi", "kg_moi_don_vi_gia": "0.4",
         "thue": "co", "gom_ship": "khong_ro", "kenh_gia": "", "trang_thai": "con", "ghi_chu": "", "do_chac": "chac"}
    d.update(kw)
    return d


def test_jan_chu_so_kiem():
    assert G.jan_hop_le("8934563321406")
    assert not G.jan_hop_le("8934781067026")       # IMAI tháng 8: sai chữ số kiểm
    assert not G.jan_hop_le("12345")


def test_khoa_hang_uu_tien_jan_roi_ma_ben_roi_ten():
    assert G.ma_hang_dt(_d(jan="8934563321406")) == "jan:8934563321406"
    assert G.ma_hang_dt(_d(vi_tri="danh mục gao · _id 680f5e1c · branches.main", ben="THAI-DUONG")) == "id:680f5e1c"
    assert G.ma_hang_dt(_d(ten_goc="Bột Năng  TÀI KÝ 400gr", quy_cach_goc="400g x 24")) == \
           G.ma_hang_dt(_d(ten_goc="bot nang tai ky 400g", quy_cach_goc="400g x 24"))


def test_ngay_lay_tu_ten_file_khong_thi_mac_dinh():
    md = date(2026, 8, 31)
    assert G.suy_ngay("THAK-HANG-KHO-2026.08.05.pdf", md) == date(2026, 8, 5)
    assert G.suy_ngay("2026-8-4 Menu bao gồm thuế.pdf", md) == date(2026, 8, 4)
    assert G.suy_ngay("tdmvn.shop (API, tải 2026-09-29)", md) == date(2026, 9, 29)
    assert G.suy_ngay("IMG_0339.JPG", md) == md


def test_sap_ve_va_muc_gia():
    assert G.suy_trang_thai(_d(trang_thai="het", ghi_chu="Dự kiến tháng 9 xuất hàng")) == "sap_ve"
    assert G.suy_trang_thai(_d(trang_thai="khong_ro", ghi_chu="30/08入荷予定")) == "sap_ve"
    assert G.suy_muc_gia(_d(ben="THAI-DUONG", ghi_chu="mức special (giá đặc biệt)")) == "dac_biet"
    assert G.suy_muc_gia(_d(ben="VIETCOOK", ghi_chu="Giá khách Vietcook = Pallet")) == "pallet"
    assert G.suy_muc_gia(_d()) is None


def test_gop_cap_chua_thue_co_thue_va_bo_trung():
    a = _d(ben="IMAI", thue="chua", gia_goc="90")
    b = _d(ben="IMAI", thue="co", gia_goc="97")
    gia, _, _ = G.dung_goi([a, b, dict(a)], [], date(2026, 8, 31))
    assert len(gia) == 1 and gia[0]["gia_goc"] == "90" and "税込 ¥97" in gia[0]["ghi_chu"]


def test_gia_bat_thuong_thanh_can_xem_khong_chan():
    gia, _, canh = G.dung_goi([_d(gia_goc="5"), _d(ten_goc="X", gia_goc="0")], [], date(2026, 8, 31))
    assert [g["do_chac"] for g in gia] == ["can_xem", "can_xem"]
    assert canh


def test_jan_trung_hai_ma_cung_ben_khong_dung_lam_khoa():
    gia, _, _ = G.dung_goi([_d(jan="8934563321406", ten_goc="Nước dừa"),
                            _d(jan="8934563321406", ten_goc="Nha đam")], [], date(2026, 8, 31))
    assert not any(g["ma_hang_dt"].startswith("jan:") for g in gia)


def test_ma_dong_duy_nhat_va_du_cot():
    from kome.loaders.doi_thu import COT_GIA
    gia, _, _ = G.dung_goi([_d(), _d(ten_goc="Khác")], [], date(2026, 8, 31))
    assert len({g["ma_dong"] for g in gia}) == 2
    assert all(list(g) == COT_GIA for g in gia)
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_goi_doi_thu.py -v`
Expected: FAIL (`FileNotFoundError: scripts/goi_doi_thu.py`)

- [ ] **Step 3a: Hàm chuẩn hoá tên dùng chung** — `kome/ten_hang.py` (script này VÀ `kome/doi_thu.py` Task 5 cùng dùng; hai chỗ tự viết là hai khoá khác nhau cho cùng một hàng):

```python
"""Chuẩn hoá tên hàng để làm khoá (bỏ dấu, thường hoá, 500gr→500g) — đặc tả Thị trường & đối thủ §4.3."""
import re
import unicodedata


def chuan_ten(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"(\d)\s*gr\b", r"\1g", s)
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", s)).strip()
```

- [ ] **Step 3b: Viết script** — `scripts/goi_doi_thu.py`:

```python
"""Dựng gói bảng giá đối thủ từ các CSV đã đọc (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4.1, §4.3, §7).

    python scripts/goi_doi_thu.py <thư mục CSV> --ngay 2026-08-31 --ra <thư mục ra>

Đọc mọi `spike_*.csv` (giá) và `spike_*_dieu_kien.csv` (điều kiện), ghi hai file nạp được:
doi_thu_gia_YYYYMMDD.xlsx, doi_thu_dieu_kien_YYYYMMDD.xlsx. Không chặn cả gói vì một dòng xấu:
dòng xấu mang do_chac=can_xem + lý do ở ghi_chu (cổng 5 của nguồn này, đặc tả §4.1).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kome.loaders.doi_thu import COT_GIA, COT_DIEU_KIEN  # noqa: E402
from kome.ten_hang import chuan_ten  # noqa: E402

GIA_THAP = 20          # giá < 20 yên (một gói / một kg) gần như chắc là lỗi của nguồn
_WEB = re.compile(r"\.(jp|com|shop|asia|top)\b|Google Sheet|API", re.I)
_NGAY = [re.compile(r"(20\d\d)[.\-/](\d{1,2})[.\-/](\d{1,2})"), re.compile(r"(20\d\d)(\d\d)(\d\d)")]
_ID_BEN = re.compile(r"(?:_id|id|mã SP|商品コード)\s*[:=]?\s*([A-Za-z0-9\-]{4,})")


def jan_hop_le(s: str) -> bool:
    s = (s or "").strip()
    if not re.fullmatch(r"\d{13}", s):
        return False
    tong = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(s[:12]))
    return (10 - tong % 10) % 10 == int(s[12])


def ma_hang_dt(d: dict, jan_dung_duoc: bool = True) -> str:
    jan = (d.get("jan") or "").strip()
    if jan_dung_duoc and jan_hop_le(jan):
        return "jan:" + jan
    m = _ID_BEN.search(d.get("vi_tri") or "")
    if m:
        return "id:" + m.group(1)
    return "ten:" + chuan_ten(d.get("ten_goc", "")) + "|" + chuan_ten(d.get("quy_cach_goc", ""))


def suy_ngay(file: str, mac_dinh: date) -> date:
    for p in _NGAY:
        m = p.search(file or "")
        if m:
            try:
                return date(int(m[1]), int(m[2]), int(m[3]))
            except ValueError:
                pass
    return mac_dinh


def suy_trang_thai(d: dict) -> str:
    ghi = (d.get("ghi_chu") or "") + " " + (d.get("khuyen_mai") or "")
    if re.search(r"dự kiến|入荷予定|sắp về", ghi, re.I):
        return "sap_ve"
    t = d.get("trang_thai") or "khong_ro"
    return t if t in ("con", "het", "sap_ve", "khong_ro") else "khong_ro"


def suy_muc_gia(d: dict) -> str | None:
    if d.get("muc_gia"):
        return d["muc_gia"]
    ghi = (d.get("ghi_chu") or "").lower()
    if "special" in ghi or "đặc biệt" in ghi:
        return "dac_biet"
    if "pallet" in ghi:
        return "pallet"
    if "khách ngoài" in ghi or "ngoài vietcook" in ghi:
        return "khach_ngoai"
    if "kyushu" in ghi:
        return "kyushu"
    return None


def _so(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def dung_goi(gia: list[dict], dk: list[dict], ngay: date) -> tuple[list[dict], list[dict], list[str]]:
    canh: list[str] = []
    # 1. Gộp cặp chưa thuế / có thuế của CÙNG một ô (IMAI in cả hai cột): giữ dòng chưa thuế.
    nhom: dict[tuple, list[dict]] = {}
    for d in gia:
        nhom.setdefault((d.get("ben"), d.get("vi_tri"), d.get("ten_goc"), d.get("jan"), d.get("kenh_gia")), []).append(d)
    bo: set[int] = set()
    for ds in nhom.values():
        chua = [d for d in ds if d.get("thue") == "chua"]
        co = [d for d in ds if d.get("thue") == "co"]
        if len(chua) >= 1 and len(co) >= 1:
            chua[0]["ghi_chu"] = ((chua[0].get("ghi_chu") or "") + f" · 税込 ¥{co[0].get('gia_goc')}").strip(" ·")
            bo.update(id(x) for x in co)
    gia = [d for d in gia if id(d) not in bo]
    # 2. Bỏ dòng trùng y hệt (ảnh gửi trùng trang).
    thay, sach = set(), []
    for d in gia:
        k = (d.get("ben"), d.get("ten_goc"), d.get("quy_cach_goc"), d.get("gia_goc"), d.get("kenh_gia"),
             suy_muc_gia(d), d.get("don_vi_gia"))
        if k not in thay:
            thay.add(k)
            sach.append(d)
    # 3. JAN dùng làm khoá chỉ khi không trùng hai tên trong cùng bên.
    ten_cua_jan: dict[tuple, set] = {}
    for d in sach:
        if jan_hop_le(d.get("jan") or ""):
            ten_cua_jan.setdefault((d["ben"], d["jan"]), set()).add(chuan_ten(d.get("ten_goc", "")))
    ra, dem = [], {}
    for d in sach:
        ben = d["ben"]
        dem[ben] = dem.get(ben, 0) + 1
        ly_do = []
        jan = (d.get("jan") or "").strip()
        jan_ok = jan_hop_le(jan) and len(ten_cua_jan.get((ben, jan), ())) == 1
        if jan and not jan_hop_le(jan):
            ly_do.append(f"JAN {jan} sai chữ số kiểm")
        elif jan and not jan_ok:
            ly_do.append(f"JAN {jan} trùng nhiều mã cùng bên")
        g = _so(d.get("gia_goc"))
        if g is not None and g < GIA_THAP:
            ly_do.append(f"giá {d.get('gia_goc')} bất thường (< {GIA_THAP})")
        do_chac = "can_xem" if ly_do or d.get("do_chac") == "can_xem" else "chac"
        ghi = " · ".join(x for x in [d.get("ghi_chu") or "", *ly_do] if x)
        if ly_do:
            canh.append(f"{ben} {d.get('vi_tri')}: {'; '.join(ly_do)}")
        file = d.get("file") or ""
        o = {
            "ma_dong": f"{ben}-{dem[ben]:05d}", "ma_doi_thu": ben, "ma_hang_dt": ma_hang_dt(d, jan_ok),
            "ngay_nguon": suy_ngay(file, ngay).isoformat(), "hinh_thuc_nguon": "web" if _WEB.search(file) else "file",
            "nguon_file": file, "vi_tri": d.get("vi_tri"), "ten_goc": d.get("ten_goc"), "ten_nhat": d.get("ten_nhat"),
            "jan": jan or None, "quy_cach_goc": d.get("quy_cach_goc"), "gia_goc": d.get("gia_goc") or None,
            "don_vi_gia": d.get("don_vi_gia"), "kg_moi_don_vi_gia": d.get("kg_moi_don_vi_gia") or None,
            "thue": d.get("thue") or "khong_ro", "gom_ship": d.get("gom_ship") or "khong_ro",
            "kenh_gia": d.get("kenh_gia") or None, "muc_gia": suy_muc_gia(d), "gia_bac": d.get("gia_bac"),
            "gia_truoc_km": d.get("gia_truoc_km") or None, "trang_thai": suy_trang_thai(d),
            "han_su_dung": d.get("han_su_dung"), "khuyen_mai": d.get("khuyen_mai"),
            "ma_kome_de_xuat": d.get("ma_kome") or None,
            "nhan_de_xuat": d.get("nhan_ghep") if d.get("nhan_ghep") in ("cung_hang", "thay_the") else None,
            "ly_do_ghep": d.get("ly_do_ghep"), "do_chac": do_chac, "ghi_chu": ghi or None,
        }
        ra.append({c: o[c] for c in COT_GIA})
    dk_ra, dem_dk = [], {}
    for d in dk:
        ben = d["ben"]
        dem_dk[ben] = dem_dk.get(ben, 0) + 1
        loai = d.get("loai") if d.get("loai") in ("ship", "khuyen_mai", "thanh_toan", "thue", "khac") else "khac"
        dk_ra.append({"ma_dong": f"{ben}-{dem_dk[ben]:05d}", "ma_doi_thu": ben,
                      "ngay_nguon": suy_ngay(d.get("file") or "", ngay).isoformat(),
                      "nguon_file": d.get("file"), "vi_tri": d.get("vi_tri"), "loai": loai,
                      "noi_dung": d.get("noi_dung")})
    return ra, [x for x in dk_ra if (x["noi_dung"] or "").strip()], canh


def _doc(p: Path) -> list[dict]:
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    import pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("thu_muc", type=Path)
    ap.add_argument("--ngay", type=date.fromisoformat, required=True)
    ap.add_argument("--ra", type=Path, required=True)
    a = ap.parse_args()
    gia, dk = [], []
    for p in sorted(a.thu_muc.glob("spike_*.csv")):
        (dk if p.stem.endswith("_dieu_kien") else gia).extend(_doc(p))
    g, d, canh = dung_goi(gia, dk, a.ngay)
    a.ra.mkdir(parents=True, exist_ok=True)
    s = a.ngay.strftime("%Y%m%d")
    pd.DataFrame(g, columns=COT_GIA).to_excel(a.ra / f"doi_thu_gia_{s}.xlsx", sheet_name="gia", index=False)
    pd.DataFrame(d, columns=COT_DIEU_KIEN).to_excel(a.ra / f"doi_thu_dieu_kien_{s}.xlsx", sheet_name="dieu_kien", index=False)
    print(f"{len(g)} dòng giá · {len(d)} điều kiện · {len(canh)} cảnh báo")
    for c in canh[:50]:
        print("  ", c)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Chạy test**

Run: `pytest tests/test_goi_doi_thu.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/goi_doi_thu.py kome/ten_hang.py tests/test_goi_doi_thu.py
git commit -m "feat(doi-thu): script dung goi nap tu CSV doc duoc (khoa hang, JAN, loc trung)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Migration 060 — chỉ số `mart`

**Files:**
- Create: `db/migrations/060_mart_doi_thu.sql`
- Test: `tests/test_mart_doi_thu.py`

**Interfaces:**
- Consumes: bảng Task 1; `mart.ban_den_moc`, `mart.moc_thoi_gian(hom_nay)`, `mart.moc_lui()`.
- Produces (cột dùng ở Task 5):
  - `mart.quy_cach_kome(product_code, kg_moi_goi, goi_moi_thung, kg_moi_thung, da_sua)`
  - `mart.gia_kome_kg(product_code, doanh_thu, kg_ban, yen_kg)`
  - `mart.la_gia_bat_thuong(gia numeric, trung_vi numeric, so_ben bigint) RETURNS boolean`
  - `mart.gia_doi_thu_quan_sat(nguon, id, batch_id, ma_doi_thu, ten_doi_thu, ma_hang_dt, ngay_nguon, hinh_thuc_nguon, nguon_file, vi_tri, ten_goc, quy_cach_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, kenh_gia, muc_gia, gia_bac, gia_truoc_km, trang_thai, khuyen_mai, loai_nguon, thu_tu_nguon, ghi_chu, ma_kome, nhan, nhom_khoa, ten_nhom, trang_thai_duyet, yen_chuan, don_vi_so, nen_gia, hien_hanh, tuoi_ngay)`
  - `mart.gia_doi_thu_hien_hanh` = như trên (chỉ `hien_hanh`) + `trung_vi_nhom`, `so_ben_nhom`, `bat_thuong`
  - `mart.so_sanh_nhom(nhom_khoa, ten_nhom, don_vi_so, ma_kome text[], gia_kome, so_ben, so_quan_sat, thap_nhat, ben_thap_nhat, trung_vi, cao_nhat, ty_le_re_hon_kome)`

- [ ] **Step 1: Viết test hỏng** — `tests/test_mart_doi_thu.py`:

```python
"""Migration 060 — chỉ số mart của Thị trường & đối thủ (đặc tả §4.4)."""
from datetime import date
import pytest

from tests.test_khach_hang import _mua, HOM_NAY


def _hang(conn, batch, ma="NT01", ten="Ca Ba sa cat khuc (500g x 20 packs)"):
    b = batch(9001)
    conn.execute("""INSERT INTO core.dim_product (product_code, product_name, food_category_name, batch_id)
                    VALUES (%s, %s, '冷凍食品_VNM', %s) ON CONFLICT DO NOTHING""", (ma, ten, b))
    conn.commit()


def _qs(conn, batch, ben, gia, kg=1, thue="chua", ma="NT01", ngay=date(2026, 7, 20), trang="con",
        hang=None, nhan="thay_the", do_chac="chac"):
    b = batch(abs(hash((ben, gia, hang, ngay))) % 50_000 + 20_000, ngay)
    r = conn.execute(
        """INSERT INTO core.fact_gia_doi_thu (batch_id, ma_dong, ma_doi_thu, ma_hang_dt, ngay_nguon, hinh_thuc_nguon,
             ten_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, trang_thai, ma_kome_de_xuat, nhan_de_xuat, do_chac)
           VALUES (%s, 'x-1', %s, %s, %s, 'file', 'Basa', %s, 'kg', %s, %s, 'khong_ro', %s, %s, %s, %s) RETURNING id""",
        (b, ben, hang or f"ten:basa|{ben}", ngay, gia, kg, thue, trang, ma, nhan, do_chac)).fetchone()[0]
    conn.commit()
    return r


def test_quy_cach_tach_tu_ten_va_nguoi_sua_thang(conn, batch):
    _hang(conn, batch)
    _hang(conn, batch, "NT04", "Ca ro phi nguyen con (10kg/case)")
    q = dict(((r[0], (r[1], r[2], r[3])) for r in conn.execute(
        "SELECT product_code, kg_moi_goi, goi_moi_thung, kg_moi_thung FROM mart.quy_cach_kome")))
    assert q["NT01"] == (pytest.approx(0.5), 20, None)
    assert q["NT04"][2] == 10
    conn.execute("INSERT INTO app.quy_cach_kome (product_code, kg_moi_goi) VALUES ('NT01', 0.45)")
    conn.commit()
    assert float(conn.execute("SELECT kg_moi_goi FROM mart.quy_cach_kome WHERE product_code='NT01'").fetchone()[0]) == 0.45


def test_gia_kome_kg_la_TY_SO_CAC_TONG_doc_ban_den_moc(conn, batch):
    _hang(conn, batch)
    # _mua: pack_code '02', qty 6, amount 110.000, tax 10.000 → 100.000 ÷ (6 thùng × 20 × 0,5 kg) = ¥1.666,7/kg
    _mua(conn, batch, "202601010001", HOM_NAY, hang="NT01")
    _mua(conn, batch, "009000000001", HOM_NAY, hang="NT01")     # mã nội bộ (044) — không được lọt
    y = conn.execute("SELECT yen_kg FROM mart.gia_kome_kg WHERE product_code='NT01'").fetchone()[0]
    assert float(y) == pytest.approx(100_000 / 60, rel=1e-6)


def test_quy_doi_chia_thue_dung_mot_lan_va_khong_kg_thi_don_vi(conn, batch):
    _hang(conn, batch)
    _qs(conn, batch, "A", 540, thue="co")
    _qs(conn, batch, "B", 100, kg=None)
    r = dict(conn.execute("SELECT ma_doi_thu, (yen_chuan, don_vi_so) FROM mart.gia_doi_thu_quan_sat").fetchall())
    assert float(r["A"][0]) == pytest.approx(500)
    assert r["B"][1] == "don_vi:kg"


def test_dinh_chinh_ap_tren_ban_nap_khong_dung_core(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "A", 850)
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, 'gia_goc', '580')", (fid,))
    conn.commit()
    g, tt = conn.execute("SELECT gia_goc, trang_thai_duyet FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()
    assert g == 580 and tt == "da_sua"
    assert conn.execute("SELECT gia_goc FROM core.fact_gia_doi_thu WHERE id=%s", (fid,)).fetchone()[0] == 850


def test_dinh_chinh_mo_coi_sau_hoan_tac_khong_no(conn, batch):
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (999999, 'gia_goc', '1')")
    conn.commit()
    assert conn.execute("SELECT count(*) FROM mart.gia_doi_thu_quan_sat").fetchone()[0] == 0


def test_bat_thuong_hon_2_lan_trung_vi_khi_du_3_ben_va_khong_vao_trung_vi(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580), ("D", 1400)]:
        _qs(conn, batch, ben, g)
    bt = dict(conn.execute("SELECT ma_doi_thu, bat_thuong FROM mart.gia_doi_thu_hien_hanh").fetchall())
    assert bt == {"A": False, "B": False, "C": False, "D": True}
    tv = conn.execute("SELECT trung_vi, cao_nhat, so_ben FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'").fetchone()
    assert float(tv[0]) == 560 and float(tv[1]) == 580 and tv[2] == 3


def test_nhom_duoi_3_ben_khong_xet_bat_thuong(conn, batch):
    _hang(conn, batch)
    _qs(conn, batch, "A", 100); _qs(conn, batch, "B", 900)
    assert not any(r[0] for r in conn.execute("SELECT bat_thuong FROM mart.gia_doi_thu_hien_hanh"))


def test_xac_nhan_go_co_bat_thuong(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580)]:
        _qs(conn, batch, ben, g)
    fid = _qs(conn, batch, "D", 1400)
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong) VALUES (%s, 'xac_nhan')", (fid,))
    conn.commit()
    assert conn.execute("SELECT bat_thuong FROM mart.gia_doi_thu_hien_hanh WHERE id=%s", (fid,)).fetchone()[0] is False


def test_het_hang_khong_vao_trung_vi(conn, batch):
    _hang(conn, batch)
    _qs(conn, batch, "A", 500); _qs(conn, batch, "B", 600); _qs(conn, batch, "C", 100, trang="het")
    assert float(conn.execute("SELECT thap_nhat FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'").fetchone()[0]) == 500


def test_quan_sat_moi_hon_thang_cu_va_quay_ve_moc(conn, batch):
    _hang(conn, batch)
    _mua(conn, batch, "202601010001", date(2026, 9, 20), hang="NT01")   # mốc dữ liệu = 20/9
    _qs(conn, batch, "A", 500, hang="h1", ngay=date(2026, 8, 5))
    _qs(conn, batch, "A", 520, hang="h1", ngay=date(2026, 9, 5))
    assert conn.execute("SELECT gia_goc FROM mart.gia_doi_thu_hien_hanh").fetchone()[0] == 520
    conn.execute("SELECT set_config('kome.moc', '2026-08-31', true)")
    assert conn.execute("SELECT gia_goc FROM mart.gia_doi_thu_hien_hanh").fetchone()[0] == 500
    conn.rollback()


def test_ghep_cua_nguoi_thang_de_xuat_va_nhom_co_ten_gop_ma(conn, batch):
    _hang(conn, batch); _hang(conn, batch, "NT99", "Ca Ba sa cat khuc (1kg x 10 packs)")
    _qs(conn, batch, "A", 500, hang="h1")
    _qs(conn, batch, "B", 520, hang="h2", ma="NT99")
    conn.execute("INSERT INTO app.ghep_hang (ma_doi_thu, ma_hang_dt, product_code, nhan) VALUES ('A', 'h1', NULL, 'khong')")
    n = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Basa cắt khúc') RETURNING id").fetchone()[0]
    conn.execute("INSERT INTO app.nhom_so_sanh_ma VALUES ('NT01', %s), ('NT99', %s)", (n, n))
    conn.commit()
    r = dict(conn.execute("SELECT ma_doi_thu, (ma_kome, nhom_khoa, ten_nhom) FROM mart.gia_doi_thu_quan_sat").fetchall())
    assert r["A"][0] is None and r["A"][1] is None               # người nói "không ghép" → ra khỏi mọi nhóm
    assert r["B"][1] == f"n:{n}" and r["B"][2] == "Basa cắt khúc"
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_mart_doi_thu.py -v`
Expected: FAIL (`relation "mart.quy_cach_kome" does not exist`)

- [ ] **Step 3: Viết migration** — `db/migrations/060_mart_doi_thu.sql`:

```sql
-- 060 — Chỉ số Thị trường & đối thủ (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4.4).
-- Mọi quy đổi / ghép / nhóm / bất thường viết ĐÚNG MỘT LẦN ở đây. kome/doi_thu.py chỉ hỏi.

-- Quy cách KOME: tách từ product_name "(500g x 20 packs)" / "(10kg/case)"; app.quy_cach_kome (người sửa) thắng.
CREATE VIEW mart.quy_cach_kome AS
WITH t AS (
    SELECT p.product_code,
           regexp_match(p.product_name, '\(\s*(\d+(?:[.,]\d+)?)\s*(kg|gr|g)\s*[x×]\s*(\d+)', 'i') AS m1,
           regexp_match(p.product_name, '(\d+(?:[.,]\d+)?)\s*kg\s*/\s*case', 'i')             AS m2
    FROM core.dim_product p
)
SELECT t.product_code,
       coalesce(o.kg_moi_goi, CASE WHEN t.m1 IS NOT NULL THEN replace(t.m1[1], ',', '.')::numeric
                                   / CASE WHEN lower(t.m1[2]) = 'kg' THEN 1 ELSE 1000 END END) AS kg_moi_goi,
       coalesce(o.goi_moi_thung, t.m1[3]::numeric)                                             AS goi_moi_thung,
       coalesce(o.kg_moi_thung, replace(t.m2[1], ',', '.')::numeric)                           AS kg_moi_thung,
       (o.product_code IS NOT NULL)                                                            AS da_sua
FROM t LEFT JOIN app.quy_cach_kome o USING (product_code);

-- Đơn giá thực 90 ngày của KOME quy về ¥/kg: TỶ SỐ CÁC TỔNG, đọc mart.ban_den_moc (quay về mốc, bỏ mã
-- nội bộ). pack_code '02' = thùng. Dòng mà quy cách không cho ra kg thì không vào tử lẫn mẫu (không đoán).
CREATE VIEW mart.gia_kome_kg AS
SELECT f.product_code,
       sum(f.amount - f.tax_amount)                                AS doanh_thu,
       sum(f.qty * k.kg)                                           AS kg_ban,
       sum(f.amount - f.tax_amount) / nullif(sum(f.qty * k.kg), 0) AS yen_kg
FROM mart.ban_den_moc f
CROSS JOIN mart.moc_thoi_gian m
JOIN mart.quy_cach_kome q ON q.product_code = f.product_code
CROSS JOIN LATERAL (SELECT CASE WHEN f.pack_code = '02' THEN coalesce(q.kg_moi_thung, q.kg_moi_goi * q.goi_moi_thung)
                                ELSE q.kg_moi_goi END AS kg) k
WHERE f.sales_date > m.hom_nay - 90 AND k.kg IS NOT NULL
GROUP BY f.product_code;

-- Bất thường: MỘT định nghĩa.
CREATE FUNCTION mart.la_gia_bat_thuong(gia numeric, trung_vi numeric, so_ben bigint) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
    SELECT coalesce(so_ben >= 3 AND trung_vi > 0 AND gia IS NOT NULL AND (gia > 2 * trung_vi OR gia < 0.5 * trung_vi), false)
$$;

CREATE VIEW mart.gia_doi_thu_quan_sat AS
WITH dc AS (
    SELECT DISTINCT ON (fact_id, truong) fact_id, truong, gia_tri_moi
    FROM app.dinh_chinh_gia ORDER BY fact_id, truong, id DESC
),
p AS (
    SELECT fact_id,
           max(gia_tri_moi) FILTER (WHERE truong = 'ten_goc')           AS ten_goc,
           max(gia_tri_moi) FILTER (WHERE truong = 'quy_cach_goc')      AS quy_cach_goc,
           max(gia_tri_moi) FILTER (WHERE truong = 'gia_goc')           AS gia_goc,
           max(gia_tri_moi) FILTER (WHERE truong = 'don_vi_gia')        AS don_vi_gia,
           max(gia_tri_moi) FILTER (WHERE truong = 'kg_moi_don_vi_gia') AS kg,
           max(gia_tri_moi) FILTER (WHERE truong = 'thue')              AS thue,
           max(gia_tri_moi) FILTER (WHERE truong = 'gom_ship')          AS gom_ship,
           max(gia_tri_moi) FILTER (WHERE truong = 'kenh_gia')          AS kenh_gia,
           max(gia_tri_moi) FILTER (WHERE truong = 'muc_gia')           AS muc_gia,
           max(gia_tri_moi) FILTER (WHERE truong = 'trang_thai')        AS trang_thai,
           bool_or(truong = 'xac_nhan')                                 AS xac_nhan,
           bool_or(truong <> 'xac_nhan')                                AS da_sua
    FROM dc GROUP BY fact_id
),
nap AS (
    SELECT 'nap'::text AS nguon, f.id, f.batch_id, f.ma_doi_thu, f.ma_hang_dt, f.ngay_nguon, f.hinh_thuc_nguon,
           f.nguon_file, f.vi_tri,
           coalesce(p.ten_goc, f.ten_goc) AS ten_goc, coalesce(p.quy_cach_goc, f.quy_cach_goc) AS quy_cach_goc,
           coalesce(nullif(p.gia_goc, '')::numeric, f.gia_goc) AS gia_goc,
           coalesce(p.don_vi_gia, f.don_vi_gia) AS don_vi_gia,
           coalesce(nullif(p.kg, '')::numeric, f.kg_moi_don_vi_gia) AS kg_moi_don_vi_gia,
           coalesce(p.thue, f.thue) AS thue, coalesce(p.gom_ship, f.gom_ship) AS gom_ship,
           coalesce(p.kenh_gia, f.kenh_gia) AS kenh_gia, coalesce(p.muc_gia, f.muc_gia) AS muc_gia,
           f.gia_bac, f.gia_truoc_km, coalesce(p.trang_thai, f.trang_thai) AS trang_thai, f.khuyen_mai,
           'bang_gia'::text AS loai_nguon, f.ghi_chu, f.ma_kome_de_xuat, f.nhan_de_xuat,
           CASE WHEN p.da_sua THEN 'da_sua' WHEN p.xac_nhan THEN 'da_xac_nhan'
                WHEN f.do_chac = 'can_xem' THEN 'can_xem' ELSE 'ai_doc' END AS trang_thai_duyet
    FROM core.fact_gia_doi_thu f LEFT JOIN p ON p.fact_id = f.id
),
tay AS (
    SELECT 'tay'::text, t.id, NULL::bigint, t.ma_doi_thu, t.ma_hang_dt, (t.luc AT TIME ZONE 'Asia/Tokyo')::date,
           'tay'::text, NULL::text, NULL::text, t.ten_goc, t.quy_cach_goc, t.gia_goc, t.don_vi_gia,
           t.kg_moi_don_vi_gia, t.thue, t.gom_ship, t.kenh_gia, t.muc_gia, NULL::text, NULL::numeric,
           t.trang_thai, NULL::text, t.loai_nguon, t.ghi_chu_nguon,
           NULL::text, NULL::text, 'nhap_tay'::text
    FROM app.gia_doi_thu_tay t
),
tat AS (SELECT * FROM nap UNION ALL SELECT * FROM tay),
ghep AS (
    SELECT a.*, g.ma_doi_thu IS NOT NULL AS co_ghep,
           CASE WHEN g.ma_doi_thu IS NULL THEN a.ma_kome_de_xuat
                WHEN g.nhan = 'khong' THEN NULL ELSE g.product_code END AS ma_kome,
           CASE WHEN g.ma_doi_thu IS NULL THEN a.nhan_de_xuat
                WHEN g.nhan = 'khong' THEN NULL ELSE g.nhan END         AS nhan,
           g.nhom_id AS nhom_ghep
    FROM tat a LEFT JOIN app.ghep_hang g USING (ma_doi_thu, ma_hang_dt)
    WHERE mart.moc_lui() IS NULL OR a.ngay_nguon <= mart.moc_lui()
)
SELECT x.nguon, x.id, x.batch_id, x.ma_doi_thu, d.ten AS ten_doi_thu, x.ma_hang_dt, x.ngay_nguon,
       x.hinh_thuc_nguon, x.nguon_file, x.vi_tri, x.ten_goc, x.quy_cach_goc, x.gia_goc, x.don_vi_gia,
       x.kg_moi_don_vi_gia, x.thue, x.gom_ship, x.kenh_gia, x.muc_gia, x.gia_bac, x.gia_truoc_km, x.trang_thai,
       x.khuyen_mai, x.loai_nguon, ln.thu_tu AS thu_tu_nguon, x.ghi_chu, x.ma_kome, x.nhan,
       CASE WHEN x.nhom_ghep IS NOT NULL THEN 'n:' || x.nhom_ghep
            WHEN nm.nhom_id IS NOT NULL THEN 'n:' || nm.nhom_id
            WHEN x.ma_kome IS NOT NULL THEN 'ma:' || x.ma_kome END                    AS nhom_khoa,
       coalesce(ng.ten, nn.ten, kp.product_name)                                      AS ten_nhom,
       x.trang_thai_duyet,
       x.gia_goc / coalesce(nullif(x.kg_moi_don_vi_gia, 0), 1)
                 / CASE WHEN x.thue = 'co' THEN 1.08 ELSE 1 END                        AS yen_chuan,
       CASE WHEN x.kg_moi_don_vi_gia > 0 THEN 'kg' ELSE 'don_vi:' || coalesce(x.don_vi_gia, '?') END AS don_vi_so,
       concat_ws(' · ', CASE x.thue WHEN 'co' THEN 'có thuế (đã quy về chưa thuế)' WHEN 'chua' THEN 'chưa thuế'
                                  ELSE 'thuế không rõ' END,
                        CASE x.gom_ship WHEN 'co' THEN 'gồm ship' WHEN 'khong' THEN 'chưa ship' ELSE 'ship không rõ' END,
                        x.kenh_gia, x.muc_gia)                                         AS nen_gia,
       row_number() OVER (PARTITION BY x.ma_doi_thu, x.ma_hang_dt, coalesce(x.kenh_gia, ''), coalesce(x.muc_gia, ''),
                                       (x.loai_nguon = 'khach_ke')
                          ORDER BY x.ngay_nguon DESC, ln.thu_tu, (x.nguon = 'tay') DESC, x.batch_id DESC NULLS FIRST, x.id DESC) = 1
                                                                                       AS hien_hanh,
       (SELECT hom_nay FROM mart.moc_thoi_gian) - x.ngay_nguon                         AS tuoi_ngay
FROM ghep x
LEFT JOIN app.doi_thu d ON d.ma = x.ma_doi_thu
LEFT JOIN app.loai_nguon ln ON ln.ma = x.loai_nguon
LEFT JOIN app.nhom_so_sanh_ma nm ON nm.product_code = x.ma_kome AND x.nhom_ghep IS NULL
LEFT JOIN app.nhom_so_sanh ng ON ng.id = x.nhom_ghep
LEFT JOIN app.nhom_so_sanh nn ON nn.id = nm.nhom_id
LEFT JOIN core.dim_product kp ON kp.product_code = x.ma_kome;

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

CREATE VIEW mart.so_sanh_nhom AS
WITH h AS MATERIALIZED (
    SELECT * FROM mart.gia_doi_thu_hien_hanh
    WHERE nhom_khoa IS NOT NULL AND yen_chuan IS NOT NULL AND trang_thai <> 'het'
      AND loai_nguon <> 'khach_ke' AND NOT bat_thuong
),
thanh_vien AS (      -- mã KOME của từng nhóm: nhóm ngầm định = đúng mã đó; nhóm có tên = nhom_so_sanh_ma
    SELECT DISTINCT nhom_khoa, substr(nhom_khoa, 4) AS product_code FROM h WHERE nhom_khoa LIKE 'ma:%'
    UNION
    SELECT 'n:' || nhom_id, product_code FROM app.nhom_so_sanh_ma
),
kome AS (
    SELECT tv.nhom_khoa, array_agg(tv.product_code ORDER BY tv.product_code) AS ma_kome,
           sum(g.doanh_thu) / nullif(sum(g.kg_ban), 0) AS gia_kome
    FROM thanh_vien tv LEFT JOIN mart.gia_kome_kg g USING (product_code)
    GROUP BY tv.nhom_khoa
)
SELECT h.nhom_khoa, max(h.ten_nhom) AS ten_nhom, h.don_vi_so, k.ma_kome,
       CASE WHEN h.don_vi_so = 'kg' THEN k.gia_kome END                                 AS gia_kome,
       count(DISTINCT h.ma_doi_thu)                                                     AS so_ben,
       count(*)                                                                         AS so_quan_sat,
       min(h.yen_chuan)                                                                 AS thap_nhat,
       (array_agg(h.ma_doi_thu ORDER BY h.yen_chuan))[1]                                AS ben_thap_nhat,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY h.yen_chuan)                         AS trung_vi,
       max(h.yen_chuan)                                                                 AS cao_nhat,
       CASE WHEN h.don_vi_so = 'kg' AND k.gia_kome IS NOT NULL
            THEN avg((h.yen_chuan < k.gia_kome)::int) END                               AS ty_le_re_hon_kome
FROM h LEFT JOIN kome k USING (nhom_khoa)
GROUP BY h.nhom_khoa, h.don_vi_so, k.ma_kome, k.gia_kome;

GRANT SELECT ON mart.quy_cach_kome, mart.gia_kome_kg, mart.gia_doi_thu_quan_sat, mart.gia_doi_thu_hien_hanh,
                mart.so_sanh_nhom TO kome_app, kome_report, kome_ingest;
GRANT EXECUTE ON FUNCTION mart.la_gia_bat_thuong(numeric, numeric, bigint) TO kome_app, kome_report, kome_ingest;
```

- [ ] **Step 4: Chạy test, sửa tới khi xanh**

Run: `pytest tests/test_mart_doi_thu.py -v`
Expected: PASS. Nếu `mart.moc_thoi_gian` / `mart.ban_den_moc` khác tên cột (`hom_nay`, `sales_date`, `pack_code`, `amount`, `tax_amount`, `qty`): đọc `db/migrations/040_*.sql` và `044_*.sql`, sửa SQL cho đúng — KHÔNG sửa migration cũ.

- [ ] **Step 5: Sinh lại tài liệu sống, chạy nhóm test liên quan**

```bash
python scripts/sinh_tai_lieu.py
pytest tests/test_mart_doi_thu.py tests/test_tai_lieu.py tests/test_moc_lui.py tests/test_ma_noi_bo.py -v
```

- [ ] **Step 6: Commit**

```bash
git add db/migrations/060_mart_doi_thu.sql tests/test_mart_doi_thu.py kome/web/tai_lieu_sinh.json
git commit -m "feat(doi-thu): migration 060 — quy doi yen/kg, ghep hien hanh, nhom, bat thuong, gia KOME 90 ngay

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `kome/doi_thu.py` — đọc và ghi

**Files:**
- Create: `kome/doi_thu.py`
- Modify: `kome/web/anh_chup.py:54-59` (`_PHIEN_BAN`)
- Test: `tests/test_doi_thu.py`

**Interfaces:**
- Consumes: view Task 4.
- Produces:
  - `class LoiNhap(Exception)`
  - `TRUONG_SUA: tuple[str, ...]`, `THUE`, `SHIP`, `TRANG_THAI`
  - `tong_quan(conn) -> dict` (1 lượt): `{ben:[{ma,ten,web,ngay_moi,hinh_thuc,so_dong,cho_duyet}], luoi:[{ben,nganh,so_ma}], khuyen_mai:[...], dieu_kien:[{ben,loai,noi_dung,ngay}], het_hang:[{ben,ten_goc,ma_kome,ten_nhom,trang_thai}]}`
  - `so_sanh(conn) -> dict` (1 lượt): `{nhom:[{nhom_khoa,ten_nhom,don_vi_so,ma_kome,gia_kome,so_ben,thap_nhat,ben_thap_nhat,trung_vi,cao_nhat,ty_le_re_hon_kome,quan_sat:[...]}]}`
  - `ho_so_ben(conn, ma) -> dict | None` (≤ 2 lượt)
  - `duyet(conn, ben="", loc="") -> dict` (1 lượt), `loc ∈ {"", "can_xem", "bat_thuong", "chua_ghep", "chua_xac_nhan"}`
  - `khoi_san_pham(conn, ma) -> dict | None` (1 lượt)
  - `xac_nhan(conn, fact_id, nguoi)`, `sua(conn, fact_id, thay_doi: dict, nguoi)`, `gia_moi(conn, du_lieu: dict, nguoi) -> int`, `dat_ghep(conn, ma_doi_thu, ma_hang_dt, product_code, nhom_id, nhan, nguoi)`, `tao_nhom(conn, ten, ma_kome: list[str], nguoi) -> int`, `sua_quy_cach(conn, product_code, kg_moi_goi, goi_moi_thung, kg_moi_thung, nguoi)` — không commit; `nguoi` = id hoặc None; mọi hàm ghi thêm một dòng `app.doi_thu_nhat_ky`.

- [ ] **Step 1: Viết test hỏng** — `tests/test_doi_thu.py`:

```python
"""kome/doi_thu.py — đọc/ghi của màn /doi-thu (đặc tả §4, §5)."""
from datetime import date
import pytest

from kome import doi_thu as DT
from tests.test_mart_doi_thu import _hang, _qs


def _dem(conn, monkeypatch):
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    return dem


def test_sua_KHONG_dung_core_va_ghi_nhat_ky(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850)
    DT.sua(conn, fid, {"gia_goc": "580", "thue": "co"}, None)
    conn.commit()
    assert conn.execute("SELECT gia_goc FROM core.fact_gia_doi_thu WHERE id=%s", (fid,)).fetchone()[0] == 850
    assert conn.execute("SELECT count(*) FROM app.dinh_chinh_gia WHERE fact_id=%s", (fid,)).fetchone()[0] == 2
    assert conn.execute("SELECT loai FROM app.doi_thu_nhat_ky").fetchone()[0] == "sua"


def test_sua_tu_choi_truong_la_va_gia_tri_sai(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850)
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {"batch_id": "1"}, None)
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {"thue": "co_le"}, None)
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {"gia_goc": "-5"}, None)


def test_gia_moi_bat_buoc_loai_nguon(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850, hang="h1")
    with pytest.raises(DT.LoiNhap):
        DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "550"}, None)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "550", "loai_nguon": "to_roi",
                            "ghi_chu_nguon": "Zalo 29/9"}, None)
    conn.commit()
    r = conn.execute("SELECT ma_doi_thu, ma_hang_dt, ten_goc, gia_goc FROM app.gia_doi_thu_tay WHERE id=%s", (tid,)).fetchone()
    assert r == ("THAK", "h1", "Basa", 550)          # chép khoá hàng từ dòng gốc


def test_dat_ghep_ghi_de_va_nhat_ky(conn, batch):
    DT.dat_ghep(conn, "THAK", "h1", "NT01", None, "cung_hang", None)
    DT.dat_ghep(conn, "THAK", "h1", None, None, "khong", None)
    conn.commit()
    assert conn.execute("SELECT nhan FROM app.ghep_hang").fetchone()[0] == "khong"
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='ghep'").fetchone()[0] == 2


def test_tong_quan_so_sanh_duyet_moi_cai_MOT_luot(conn, batch, monkeypatch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580)]:
        _qs(conn, batch, ben, g)
    for ham in (DT.tong_quan, DT.so_sanh, lambda c: DT.duyet(c), lambda c: DT.khoi_san_pham(c, "NT01")):
        dem = _dem(conn, monkeypatch)
        ham(conn)
        assert dem["n"] == 1, ham
        monkeypatch.undo()


def test_so_sanh_tra_quan_sat_cua_tung_nhom(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580)]:
        _qs(conn, batch, ben, g)
    n = DT.so_sanh(conn)["nhom"][0]
    assert n["nhom_khoa"] == "ma:NT01" and n["so_ben"] == 3 and len(n["quan_sat"]) == 3


def test_duyet_loc_bat_thuong(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580), ("D", 1400)]:
        _qs(conn, batch, ben, g)
    assert [d["ma_doi_thu"] for d in DT.duyet(conn, loc="bat_thuong")["dong"]] == ["D"]
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_doi_thu.py -v`
Expected: FAIL (`ImportError: cannot import name 'doi_thu'`)

- [ ] **Step 3: Viết module** — `kome/doi_thu.py`:

```python
"""Thị trường & đối thủ (/doi-thu) — đặc tả docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md.

Chỉ số ở mart (060): ở đây chỉ HỎI và gói JSON (mỗi hàm đọc ĐÚNG MỘT lượt hỏi), và GHI vào app
(mọi hàm ghi thêm một dòng app.doi_thu_nhat_ky trong CÙNG giao dịch; không commit — route commit).
Không bao giờ ghi core: sửa lỗi đọc = app.dinh_chinh_gia, giá đã đổi = app.gia_doi_thu_tay.
"""
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from kome.ten_hang import chuan_ten

TRUONG_SUA = ("ten_goc", "quy_cach_goc", "gia_goc", "don_vi_gia", "kg_moi_don_vi_gia",
              "thue", "gom_ship", "kenh_gia", "muc_gia", "trang_thai")
THUE = ("chua", "co", "khong_ro")
SHIP = ("co", "khong", "khong_ro")
TRANG_THAI = ("con", "het", "sap_ve", "khong_ro")
NHAN = ("cung_hang", "thay_the", "khong")
LOC_DUYET = ("", "can_xem", "bat_thuong", "chua_ghep", "chua_xac_nhan")
DAI_TOI_DA = 300


class LoiNhap(Exception):
    """Dữ liệu người nhập không hợp lệ — route trả 400 kèm câu này."""


def _so(v, ten, duong=False):
    if v in (None, ""):
        return None
    try:
        x = Decimal(str(v).replace(",", "").strip())
    except InvalidOperation:
        raise LoiNhap(f"{ten} phải là số.")
    if x < 0 or (duong and x == 0):
        raise LoiNhap(f"{ten} không được âm{' hoặc bằng 0' if duong else ''}.")
    return x


def _kiem(truong: str, v):
    if truong not in TRUONG_SUA:
        raise LoiNhap(f"Không sửa được trường '{truong}'.")
    if truong == "gia_goc":
        return None if _so(v, "Giá") is None else str(_so(v, "Giá"))
    if truong == "kg_moi_don_vi_gia":
        return None if _so(v, "Số kg", True) is None else str(_so(v, "Số kg", True))
    for ten, tap in (("thue", THUE), ("gom_ship", SHIP), ("trang_thai", TRANG_THAI)):
        if truong == ten and v not in tap:
            raise LoiNhap(f"{ten} chỉ nhận {', '.join(tap)}.")
    s = (str(v).strip() if v is not None else "")[:DAI_TOI_DA]
    if truong == "ten_goc" and not s:
        raise LoiNhap("Tên hàng không được trống.")
    return s or None


def _ghi_nhat_ky(conn, loai, doi_tuong, truoc, sau, nguoi):
    conn.execute("""INSERT INTO app.doi_thu_nhat_ky (loai, doi_tuong, truoc, sau, nguoi_dung_id)
                    VALUES (%s, %s, %s, %s, %s)""",
                 (loai, doi_tuong, json.dumps(truoc, ensure_ascii=False, default=str) if truoc is not None else None,
                  json.dumps(sau, ensure_ascii=False, default=str) if sau is not None else None, nguoi))


# ---------------------------------------------------------------- ghi

def xac_nhan(conn, fact_id: int, nguoi) -> None:
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, nguoi_dung_id) VALUES (%s, 'xac_nhan', %s)",
                 (fact_id, nguoi))
    _ghi_nhat_ky(conn, "xac_nhan", f"gia:{fact_id}", None, None, nguoi)


def sua(conn, fact_id: int, thay_doi: dict, nguoi) -> None:
    if not thay_doi:
        raise LoiNhap("Không có gì để sửa.")
    sach = {k: _kiem(k, v) for k, v in thay_doi.items()}
    cu = conn.execute(f"SELECT {', '.join(sach)} FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s",
                      (fact_id,)).fetchone()
    if cu is None:
        raise LoiNhap("Không tìm thấy dòng giá này (có thể lô đã bị hoàn tác).")
    with conn.cursor() as cur:
        cur.executemany("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi, nguoi_dung_id) VALUES (%s,%s,%s,%s)",
                        [(fact_id, k, v, nguoi) for k, v in sach.items()])
    _ghi_nhat_ky(conn, "sua", f"gia:{fact_id}", dict(zip(sach, cu)), sach, nguoi)


def gia_moi(conn, du_lieu: dict, nguoi) -> int:
    """'Giá đã đổi' (có fact_goc_id) hoặc 'thêm hàng AI bỏ sót' (có ma_doi_thu + ten_goc). Loại nguồn bắt buộc."""
    ln = du_lieu.get("loai_nguon")
    if not ln or not conn.execute("SELECT 1 FROM app.loai_nguon WHERE ma=%s", (ln,)).fetchone():
        raise LoiNhap("Chọn loại nguồn của giá này.")
    goc = None
    if du_lieu.get("fact_goc_id"):
        goc = conn.execute("""SELECT ma_doi_thu, ma_hang_dt, ten_goc, quy_cach_goc, don_vi_gia, kg_moi_don_vi_gia,
                                     thue, gom_ship, kenh_gia, muc_gia
                              FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s""",
                           (int(du_lieu["fact_goc_id"]),)).fetchone()
        if goc is None:
            raise LoiNhap("Không tìm thấy dòng giá gốc.")
    k = ("ma_doi_thu", "ma_hang_dt", "ten_goc", "quy_cach_goc", "don_vi_gia", "kg_moi_don_vi_gia",
         "thue", "gom_ship", "kenh_gia", "muc_gia")
    v = dict(zip(k, goc)) if goc else {}
    for truong in TRUONG_SUA:
        if truong in du_lieu and truong != "trang_thai":
            v[truong] = _kiem(truong, du_lieu[truong])
    v["ma_doi_thu"] = v.get("ma_doi_thu") or du_lieu.get("ma_doi_thu")
    if not v.get("ma_doi_thu") or not v.get("ten_goc"):
        raise LoiNhap("Thiếu đối thủ hoặc tên hàng.")
    if not v.get("ma_hang_dt"):
        v["ma_hang_dt"] = "tay:" + chuan_ten(v["ten_goc"]) + "|" + chuan_ten(v.get("quy_cach_goc") or "")
    tt = _kiem("trang_thai", du_lieu.get("trang_thai") or "con")
    tid = conn.execute(
        """INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, fact_goc_id, ten_goc, quy_cach_goc, gia_goc,
             don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, kenh_gia, muc_gia, trang_thai, loai_nguon,
             ghi_chu_nguon, nguoi_dung_id)
           VALUES (%(ma_doi_thu)s, %(ma_hang_dt)s, %(fact_goc_id)s, %(ten_goc)s, %(quy_cach_goc)s, %(gia_goc)s,
             %(don_vi_gia)s, %(kg_moi_don_vi_gia)s, %(thue)s, %(gom_ship)s, %(kenh_gia)s, %(muc_gia)s,
             %(trang_thai)s, %(loai_nguon)s, %(ghi_chu_nguon)s, %(nguoi)s) RETURNING id""",
        {**{x: v.get(x) for x in k}, "gia_goc": v.get("gia_goc"), "fact_goc_id": du_lieu.get("fact_goc_id"),
         "trang_thai": tt, "loai_nguon": ln, "ghi_chu_nguon": (du_lieu.get("ghi_chu_nguon") or "")[:DAI_TOI_DA] or None,
         "nguoi": nguoi}).fetchone()[0]
    _ghi_nhat_ky(conn, "gia_moi" if goc else "them", f"tay:{tid}", None, v | {"loai_nguon": ln}, nguoi)
    return tid


def dat_ghep(conn, ma_doi_thu: str, ma_hang_dt: str, product_code, nhom_id, nhan: str, nguoi) -> None:
    if nhan not in NHAN:
        raise LoiNhap("Nhãn ghép chỉ nhận cùng hàng / thay thế / không ghép.")
    cu = conn.execute("SELECT product_code, nhom_id, nhan FROM app.ghep_hang WHERE ma_doi_thu=%s AND ma_hang_dt=%s",
                      (ma_doi_thu, ma_hang_dt)).fetchone()
    conn.execute("""INSERT INTO app.ghep_hang (ma_doi_thu, ma_hang_dt, product_code, nhom_id, nhan, nguoi_dung_id)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (ma_doi_thu, ma_hang_dt) DO UPDATE SET product_code=EXCLUDED.product_code,
                      nhom_id=EXCLUDED.nhom_id, nhan=EXCLUDED.nhan, nguoi_dung_id=EXCLUDED.nguoi_dung_id, luc=now()""",
                 (ma_doi_thu, ma_hang_dt, product_code or None, nhom_id or None, nhan, nguoi))
    _ghi_nhat_ky(conn, "ghep", f"{ma_doi_thu}/{ma_hang_dt}",
                 dict(zip(("product_code", "nhom_id", "nhan"), cu)) if cu else None,
                 {"product_code": product_code, "nhom_id": nhom_id, "nhan": nhan}, nguoi)


def tao_nhom(conn, ten: str, ma_kome: list[str], nguoi) -> int:
    ten = (ten or "").strip()
    if not 1 <= len(ten) <= 80:
        raise LoiNhap("Tên nhóm dài 1–80 ký tự.")
    if conn.execute("SELECT 1 FROM app.nhom_so_sanh WHERE lower(btrim(ten)) = lower(%s)", (ten,)).fetchone():
        raise LoiNhap("Đã có nhóm tên này.")
    nid = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES (%s) RETURNING id", (ten,)).fetchone()[0]
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO app.nhom_so_sanh_ma (product_code, nhom_id) VALUES (%s, %s)
                           ON CONFLICT (product_code) DO UPDATE SET nhom_id = EXCLUDED.nhom_id""",
                        [(m, nid) for m in ma_kome])
    _ghi_nhat_ky(conn, "nhom", f"nhom:{nid}", None, {"ten": ten, "ma_kome": ma_kome}, nguoi)
    return nid


def sua_quy_cach(conn, product_code: str, kg_moi_goi, goi_moi_thung, kg_moi_thung, nguoi) -> None:
    v = (_so(kg_moi_goi, "Kg mỗi gói", True), _so(goi_moi_thung, "Gói mỗi thùng", True),
         _so(kg_moi_thung, "Kg mỗi thùng", True))
    cu = conn.execute("SELECT kg_moi_goi, goi_moi_thung, kg_moi_thung FROM mart.quy_cach_kome WHERE product_code=%s",
                      (product_code,)).fetchone()
    if cu is None:
        raise LoiNhap("Không có mã KOME này.")
    conn.execute("""INSERT INTO app.quy_cach_kome VALUES (%s,%s,%s,%s)
                    ON CONFLICT (product_code) DO UPDATE SET kg_moi_goi=EXCLUDED.kg_moi_goi,
                      goi_moi_thung=EXCLUDED.goi_moi_thung, kg_moi_thung=EXCLUDED.kg_moi_thung""",
                 (product_code, *v))
    _ghi_nhat_ky(conn, "quy_cach", product_code, dict(zip(("kg_moi_goi", "goi_moi_thung", "kg_moi_thung"), cu)),
                 dict(zip(("kg_moi_goi", "goi_moi_thung", "kg_moi_thung"), v)), nguoi)


# ---------------------------------------------------------------- đọc (mỗi hàm ĐÚNG MỘT lượt hỏi)

_COT_QS = """ma_doi_thu, ten_doi_thu, nguon, id, ma_hang_dt, ngay_nguon, hinh_thuc_nguon, nguon_file, vi_tri,
             ten_goc, quy_cach_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, kenh_gia, muc_gia,
             gia_bac, gia_truoc_km, trang_thai, khuyen_mai, loai_nguon, ghi_chu, ma_kome, nhan, nhom_khoa,
             ten_nhom, trang_thai_duyet, round(yen_chuan) AS yen_chuan, don_vi_so, nen_gia, tuoi_ngay, bat_thuong"""

_TONG_QUAN = f"""
WITH h AS MATERIALIZED (SELECT * FROM mart.gia_doi_thu_hien_hanh),
dk AS (SELECT DISTINCT ON (ma_doi_thu, loai, noi_dung) ma_doi_thu, loai, noi_dung, ngay_nguon
       FROM core.fact_dieu_kien_doi_thu
       WHERE mart.moc_lui() IS NULL OR ngay_nguon <= mart.moc_lui()
       ORDER BY ma_doi_thu, loai, noi_dung, ngay_nguon DESC)
SELECT json_build_object(
  'ben', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten, 'web', d.web,
            'ngay_moi', x.ngay_moi, 'hinh_thuc', x.hinh_thuc, 'so_dong', coalesce(x.so_dong, 0),
            'cho_duyet', coalesce(x.cho_duyet, 0)) ORDER BY d.ma), '[]')
          FROM app.doi_thu d LEFT JOIN (
            SELECT ma_doi_thu, max(ngay_nguon) ngay_moi, max(hinh_thuc_nguon) hinh_thuc, count(*) so_dong,
                   count(*) FILTER (WHERE trang_thai_duyet IN ('can_xem', 'ai_doc') OR bat_thuong) cho_duyet
            FROM h GROUP BY 1) x ON x.ma_doi_thu = d.ma WHERE d.dang_theo_doi),
  'luoi', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'nganh', nganh, 'so_ma', n)), '[]') FROM (
            SELECT h.ma_doi_thu, mart.ten_nganh(p.food_category_name) nganh, count(DISTINCT h.ma_hang_dt) n
            FROM h JOIN core.dim_product p ON p.product_code = h.ma_kome GROUP BY 1, 2) z),
  'khuyen_mai', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'ten_goc', ten_goc, 'gia_goc', gia_goc,
            'gia_truoc_km', gia_truoc_km, 'khuyen_mai', khuyen_mai, 'ngay', ngay_nguon) ORDER BY ma_doi_thu, ten_goc), '[]')
          FROM h WHERE gia_truoc_km IS NOT NULL OR nullif(khuyen_mai, '') IS NOT NULL),
  'dieu_kien', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'loai', loai, 'noi_dung', noi_dung,
            'ngay', ngay_nguon) ORDER BY ma_doi_thu, loai), '[]') FROM dk WHERE loai <> 'khac'),
  'het_hang', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'ten_goc', ten_goc, 'ma_kome', ma_kome,
            'ten_nhom', ten_nhom, 'trang_thai', trang_thai) ORDER BY ten_nhom, ma_doi_thu), '[]')
          FROM h WHERE trang_thai IN ('het', 'sap_ve') AND ma_kome IS NOT NULL))
"""


def tong_quan(conn) -> dict:
    return conn.execute(_TONG_QUAN).fetchone()[0]


_SO_SANH = f"""
WITH h AS MATERIALIZED (SELECT {_COT_QS} FROM mart.gia_doi_thu_hien_hanh WHERE nhom_khoa IS NOT NULL)
SELECT coalesce(json_agg(json_build_object(
         'nhom_khoa', s.nhom_khoa, 'ten_nhom', s.ten_nhom, 'don_vi_so', s.don_vi_so, 'ma_kome', s.ma_kome,
         'gia_kome', round(s.gia_kome), 'so_ben', s.so_ben, 'thap_nhat', round(s.thap_nhat), 'ben_thap_nhat', s.ben_thap_nhat,
         'trung_vi', round(s.trung_vi::numeric), 'cao_nhat', round(s.cao_nhat), 'ty_le_re_hon_kome', s.ty_le_re_hon_kome,
         'quan_sat', (SELECT coalesce(json_agg(to_json(h) ORDER BY h.yen_chuan NULLS LAST), '[]') FROM h
                      WHERE h.nhom_khoa = s.nhom_khoa AND h.don_vi_so = s.don_vi_so))
       ORDER BY s.so_ben DESC, s.ten_nhom), '[]')
FROM mart.so_sanh_nhom s
"""


def so_sanh(conn) -> dict:
    return {"nhom": conn.execute(_SO_SANH).fetchone()[0]}


_HO_SO = f"""
SELECT (SELECT to_json(d) FROM app.doi_thu d WHERE d.ma = %(ma)s),
       (SELECT coalesce(json_agg(json_build_object('loai', loai, 'noi_dung', noi_dung, 'ngay', ngay_nguon)
                ORDER BY ngay_nguon DESC), '[]') FROM core.fact_dieu_kien_doi_thu WHERE ma_doi_thu = %(ma)s
                AND (mart.moc_lui() IS NULL OR ngay_nguon <= mart.moc_lui())),
       (SELECT coalesce(json_agg(to_json(q) ORDER BY q.ten_goc, q.ngay_nguon DESC), '[]')
          FROM (SELECT {_COT_QS.replace(', bat_thuong', '')}, hien_hanh FROM mart.gia_doi_thu_quan_sat
                WHERE ma_doi_thu = %(ma)s) q)
"""


def ho_so_ben(conn, ma: str) -> dict | None:
    ben, dk, qs = conn.execute(_HO_SO, {"ma": ma}).fetchone()
    return None if ben is None else {"ben": ben, "dieu_kien": dk, "quan_sat": qs}


_DUYET = f"""
SELECT coalesce(json_agg(to_json(h) ORDER BY h.bat_thuong DESC, h.trang_thai_duyet, h.ma_doi_thu, h.ten_goc), '[]')
FROM (SELECT {_COT_QS} FROM mart.gia_doi_thu_hien_hanh
      WHERE (%(ben)s = '' OR ma_doi_thu = %(ben)s)
        AND CASE %(loc)s WHEN 'can_xem' THEN trang_thai_duyet = 'can_xem'
                         WHEN 'bat_thuong' THEN bat_thuong
                         WHEN 'chua_ghep' THEN ma_kome IS NULL
                         WHEN 'chua_xac_nhan' THEN trang_thai_duyet IN ('ai_doc', 'can_xem')
                         ELSE true END) h
"""


def duyet(conn, ben: str = "", loc: str = "") -> dict:
    if loc not in LOC_DUYET:
        loc = ""
    return {"dong": conn.execute(_DUYET, {"ben": ben, "loc": loc}).fetchone()[0]}


_KHOI_SP = """
SELECT to_json(s) FROM mart.so_sanh_nhom s
WHERE s.don_vi_so = 'kg' AND %(ma)s = ANY(s.ma_kome)
ORDER BY s.so_ben DESC LIMIT 1
"""


def khoi_san_pham(conn, ma: str) -> dict | None:
    r = conn.execute(_KHOI_SP, {"ma": ma}).fetchone()
    return r[0] if r else None
```

- [ ] **Step 4: Phiên bản ảnh chụp** — `kome/web/anh_chup.py`, `_PHIEN_BAN` thành:

```python
_PHIEN_BAN = """concat_ws('|',
    (SELECT max(batch_id) FROM meta.ingest_batch),
    (SELECT max(undone_at) FROM meta.ingest_batch),
    (SELECT max(id) FROM app.ngan_sach_nhat_ky),
    (SELECT max(id) FROM app.nhat_ky_tiep_xuc),
    (SELECT max(id) FROM app.doi_thu_nhat_ky),
    (SELECT max(filename) FROM meta.schema_migration))"""
```

(Mọi hàm ghi của `kome/doi_thu.py` đều thêm một dòng `app.doi_thu_nhat_ky`, nên MỘT dòng này bao cả đính chính, giá tay, ghép, nhóm, quy cách.)

- [ ] **Step 5: Chạy test**

```bash
pytest tests/test_doi_thu.py tests/test_goi_doi_thu.py tests/test_anh_chup.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add kome/doi_thu.py kome/web/anh_chup.py tests/test_doi_thu.py
git commit -m "feat(doi-thu): doc/ghi cua man doi thu (moi ham doc 1 luot, moi ham ghi co nhat ky)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: API + route + nhật ký thao tác

**Files:**
- Modify: `kome/web/api.py` (thêm khối endpoint trong `tao_api`), `kome/web/app.py` (route `/doi-thu` cạnh `/mua-vu`), `kome/nhat_ky.py` (`LOAI`, `_NGUON`, `Dong.noi_dung`)
- Test: `tests/test_doi_thu_api.py`

**Interfaces:**
- Consumes: `kome.doi_thu` (Task 5); `_ts`, `_voi_moc`, `_khoa`, `_chup`, `_loi`, `open_app_conn` của `api.py`.
- Produces: `GET /api/doi-thu/tong-quan`, `/api/doi-thu/so-sanh`, `/api/doi-thu/ben/{ma}`, `/api/doi-thu/duyet?ben=&loc=`, `/api/san-pham/{ma}/doi-thu` (mọi cái nhận `thang/ky/tu/den`); `POST /api/doi-thu/xac-nhan {fact_id}`, `/sua {fact_id, thay_doi}`, `/gia-moi {...}`, `/ghep {ma_doi_thu, ma_hang_dt, product_code, nhom_id, nhan}`, `/nhom {ten, ma_kome}`, `/quy-cach {product_code, kg_moi_goi, goi_moi_thung, kg_moi_thung}` → `{"ok": true, ...}`.

- [ ] **Step 1: Viết test hỏng** — `tests/test_doi_thu_api.py`:

```python
"""API /doi-thu — ngân sách lượt hỏi, POST chỉ JSON, sửa xong số đổi ngay (đặc tả §5, §9)."""
from pathlib import Path
import psycopg
import pytest

from tests.test_mart_doi_thu import _hang, _qs
from tests.test_mua_vu import _web

_SRC = Path(__file__).resolve().parents[1] / "giao_dien" / "src"


def _nen(conn, batch):
    _hang(conn, batch)
    return [_qs(conn, batch, b, g) for b, g in [("A", 540), ("B", 560), ("C", 580), ("D", 1400)]]


@pytest.mark.parametrize("url, tran", [("/api/doi-thu/tong-quan", 2), ("/api/doi-thu/so-sanh", 2),
                                        ("/api/doi-thu/ben/A", 2), ("/api/doi-thu/duyet?loc=bat_thuong", 2),
                                        ("/api/san-pham/NT01/doi-thu", 2)])
def test_ngan_sach_luot_hoi(conn, batch, test_db_url, monkeypatch, url, tran):
    _nen(conn, batch)
    c = _web(test_db_url)
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    r = c.get(url)
    assert r.status_code == 200, r.text
    assert dem["n"] <= tran, f"{url}: {dem['n']} lượt hỏi, trần {tran}"


def test_post_chi_nhan_json(conn, batch, test_db_url):
    fid = _nen(conn, batch)[3]
    c = _web(test_db_url)
    assert c.post("/api/doi-thu/xac-nhan", data={"fact_id": fid}).status_code == 415


def test_xac_nhan_xong_bat_thuong_mat_ngay(conn, batch, test_db_url, monkeypatch):
    monkeypatch.setenv("KOME_ANH_CHUP", "1")               # ảnh chụp BẬT: sửa phải làm nó cũ đi
    fid = _nen(conn, batch)[3]
    c = _web(test_db_url)
    assert len(c.get("/api/doi-thu/duyet?loc=bat_thuong").json()["dong"]) == 1
    assert c.post("/api/doi-thu/xac-nhan", json={"fact_id": fid}).json()["ok"]
    assert c.get("/api/doi-thu/duyet?loc=bat_thuong").json()["dong"] == []


def test_sua_sai_tra_400_kem_cau(conn, batch, test_db_url):
    fid = _nen(conn, batch)[0]
    r = _web(test_db_url).post("/api/doi-thu/sua", json={"fact_id": fid, "thay_doi": {"thue": "?"}})
    assert r.status_code == 400 and "thue" in r.json()["loi"]


def test_trang_mo_duoc_va_co_trong_thanh_ben(test_db_url):
    assert _web(test_db_url).get("/doi-thu").status_code == 200
    assert 'url: "/doi-thu"' in (_SRC / "khung" / "muc.ts").read_text(encoding="utf-8")
    assert '"/doi-thu"' in (_SRC / "main.tsx").read_text(encoding="utf-8")


def test_nhat_ky_thao_tac_thay_sua_doi_thu(conn, batch):
    from kome import doi_thu as DT, nhat_ky as NK
    fid = _nen(conn, batch)[0]
    DT.sua(conn, fid, {"gia_goc": "550"}, None)
    conn.commit()
    assert "doi_thu" in NK.LOAI
    assert any(d.loai == "doi_thu" for d in NK.dong_thoi_gian(conn))
```

- [ ] **Step 2: Chạy, thấy hỏng**

Run: `pytest tests/test_doi_thu_api.py -v`
Expected: FAIL (404 ở `/api/doi-thu/tong-quan`)

- [ ] **Step 3: Endpoint** — `kome/web/api.py`, trong `tao_api`, ngay sau khối Mùa vụ:

```python
    # ---- Thị trường & đối thủ (059–060) --------------------------------
    # Đọc app (đính chính, giá tay, ghép) -> phiên bản ĐẦY ĐỦ (không chi_nap). Theo mốc của khoảng xem.
    def _dt_doc(request, goc, tinh, thang, ky, tu, den, loi, **them):
        try:
            ts = _ts(request, thang, ky, tu, den).chinh()
        except KX.LoiKhoang as e:
            return _loi(str(e), 400)
        return _chup(request, _khoa(goc, **them, **ts.khoa()), _voi_moc(ts, tinh), loi)

    @r.get("/doi-thu/tong-quan")
    def dt_tong_quan(request: Request, thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        from kome import doi_thu as DT
        return _dt_doc(request, "doi-thu/tong-quan", DT.tong_quan, thang, ky, tu, den, "Không đọc được tổng quan thị trường.")

    @r.get("/doi-thu/so-sanh")
    def dt_so_sanh(request: Request, thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        from kome import doi_thu as DT
        return _dt_doc(request, "doi-thu/so-sanh", DT.so_sanh, thang, ky, tu, den, "Không đọc được bảng so sánh.")

    @r.get("/doi-thu/ben/{ma}")
    def dt_ben(request: Request, ma: str, thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        """Không có đối thủ này -> {"khong_co": true} (200), giao diện nói rõ; không để _chup biến nó thành 500."""
        from kome import doi_thu as DT
        return _dt_doc(request, "doi-thu/ben", lambda c: DT.ho_so_ben(c, ma) or {"khong_co": True},
                       thang, ky, tu, den, "Không đọc được hồ sơ đối thủ.", ma=ma)

    @r.get("/doi-thu/duyet")
    def dt_duyet(request: Request, ben: str = "", loc: str = "", thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        from kome import doi_thu as DT
        return _dt_doc(request, "doi-thu/duyet", lambda c: DT.duyet(c, ben, loc), thang, ky, tu, den,
                       "Không đọc được danh sách duyệt.", ben=ben, loc=loc)

    @r.get("/san-pham/{ma}/doi-thu")
    def sp_doi_thu(request: Request, ma: str, thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        from kome import doi_thu as DT
        return _dt_doc(request, "san-pham/doi-thu", lambda c: {"nhom": DT.khoi_san_pham(c, ma)},
                       thang, ky, tu, den, "Không đọc được giá đối thủ.", ma=ma)

    async def _dt_ghi(request: Request, lam):
        from kome import doi_thu as DT
        if not request.headers.get("content-type", "").startswith("application/json"):
            return _loi("Chỉ nhận JSON.", 415)
        try:
            b = await request.json()
        except Exception:
            return _loi("Thân yêu cầu không phải JSON.", 400)
        nguoi = getattr(request.state, "nguoi", None)
        try:
            with open_app_conn() as conn:
                ra = lam(conn, b, nguoi.id if nguoi else None)
                conn.commit()
        except (DT.LoiNhap, KeyError, TypeError, ValueError) as e:
            return _loi(str(e) if isinstance(e, DT.LoiNhap) else "Thiếu hoặc sai trường dữ liệu.", 400)
        except Exception:
            traceback.print_exc()
            return _loi("Không ghi được.")
        return JSONResponse({"ok": True, **(ra or {})})

    @r.post("/doi-thu/xac-nhan")
    async def dt_xac_nhan(request: Request):
        from kome import doi_thu as DT
        return await _dt_ghi(request, lambda c, b, n: DT.xac_nhan(c, int(b["fact_id"]), n))

    @r.post("/doi-thu/sua")
    async def dt_sua(request: Request):
        from kome import doi_thu as DT
        return await _dt_ghi(request, lambda c, b, n: DT.sua(c, int(b["fact_id"]), dict(b["thay_doi"]), n))

    @r.post("/doi-thu/gia-moi")
    async def dt_gia_moi(request: Request):
        from kome import doi_thu as DT
        return await _dt_ghi(request, lambda c, b, n: {"id": DT.gia_moi(c, dict(b), n)})

    @r.post("/doi-thu/ghep")
    async def dt_ghep(request: Request):
        from kome import doi_thu as DT
        return await _dt_ghi(request, lambda c, b, n: DT.dat_ghep(
            c, str(b["ma_doi_thu"]), str(b["ma_hang_dt"]), b.get("product_code"), b.get("nhom_id"), str(b["nhan"]), n))

    @r.post("/doi-thu/nhom")
    async def dt_nhom(request: Request):
        from kome import doi_thu as DT
        return await _dt_ghi(request, lambda c, b, n: {"id": DT.tao_nhom(c, str(b["ten"]), list(b.get("ma_kome") or []), n)})

    @r.post("/doi-thu/quy-cach")
    async def dt_quy_cach(request: Request):
        from kome import doi_thu as DT
        return await _dt_ghi(request, lambda c, b, n: DT.sua_quy_cach(
            c, str(b["product_code"]), b.get("kg_moi_goi"), b.get("goi_moi_thung"), b.get("kg_moi_thung"), n))
```

- [ ] **Step 4: Route trang** — `kome/web/app.py`, ngay sau `man_mua_vu`:

```python
    # Thị trường & đối thủ — dữ liệu qua /api/doi-thu/* (kome/doi_thu.py -> mart, 059–060). NGOÀI
    # DUONG_KHO_DU_LIEU: mọi người đăng nhập vào và sửa được (đặc tả §2 "Ai sửa được": A).
    @app.get("/doi-thu", response_class=HTMLResponse)
    def man_doi_thu(request: Request):
        return _man_khach(request)
```

- [ ] **Step 5: Nhật ký thao tác** — `kome/nhat_ky.py`:
  - `LOAI` thêm `"doi_thu": ("🏷", "Giá đối thủ", "<màu như mục ngan_sach>")` (chép đúng dạng bộ ba của mục `ngan_sach`).
  - `_NGUON` thêm MỘT nhánh `UNION ALL`, chép nguyên nhánh của `app.ngan_sach_nhat_ky` rồi thay bảng và cột: `'doi_thu' AS loai, n.luc, <cùng biểu thức 'ai' như nhánh ngân sách, nối n.nguoi_dung_id>, n.doi_tuong, n.loai AS chi_tiet, n.truoc::text, n.sau::text FROM app.doi_thu_nhat_ky n`.
  - `Dong.noi_dung` thêm nhánh: `loai == "doi_thu"` → `f"{ {'sua':'Sửa giá','xac_nhan':'Xác nhận giá','gia_moi':'Cập nhật giá mới','them':'Thêm hàng','ghep':'Ghép hàng','nhom':'Tạo nhóm so sánh','quy_cach':'Sửa quy cách KOME','doi_thu':'Sửa đối thủ'}.get(self.chi_tiet, self.chi_tiet)} · {self.doi_tuong}"`.
  - `he_thong/NhatKy.tsx`: nếu màn lọc theo danh sách loại cứng, thêm `doi_thu`.

- [ ] **Step 6: Chạy test**

```bash
pytest tests/test_doi_thu_api.py tests/test_nhat_ky.py tests/test_bao_mat.py tests/test_api.py -v
```
Expected: PASS (`test_trang_mo_duoc_va_co_trong_thanh_ben` còn đỏ ở phần `muc.ts`/`main.tsx` — xanh sau Task 7).

- [ ] **Step 7: Commit**

```bash
git add kome/web/api.py kome/web/app.py kome/nhat_ky.py giao_dien/src/he_thong/NhatKy.tsx tests/test_doi_thu_api.py
git commit -m "feat(doi-thu): API doc/ghi, route /doi-thu, nhanh nhat ky thao tac

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Màn React `/doi-thu`

**Files:**
- Create: `giao_dien/src/doi_thu/kieu.ts`, `loc.ts`, `loc.test.ts`, `ManDoiThu.tsx`, `TabTongQuan.tsx`, `TabSoSanh.tsx`, `TabHoSo.tsx`, `TabDuyet.tsx`, `doi_thu.css`
- Modify: `giao_dien/src/main.tsx` (lazy + route + `boChon`), `giao_dien/src/khung/muc.ts` (mục + chú thích đầu file)
- Test: `giao_dien/src/doi_thu/loc.test.ts`, `tests/test_doi_thu_api.py::test_trang_mo_duoc_va_co_trong_thanh_ben`

**Interfaces:**
- Consumes: JSON của Task 6.
- Produces: màn; `loc.ts` export `locNhom(ds, {nganh?, chi_cung_hang, chi_xac_nhan, tim}) `, `nhanNen(qs)`, `viTriKome(n)`.

- [ ] **Step 1: Kiểu** — `giao_dien/src/doi_thu/kieu.ts`:

```ts
// Kiểu JSON của /api/doi-thu/* (kome/doi_thu.py). Số đã làm tròn ở máy chủ; định dạng qua dinh_dang.ts.
export type QuanSat = {
  ma_doi_thu: string; ten_doi_thu: string | null; nguon: "nap" | "tay"; id: number; ma_hang_dt: string;
  ngay_nguon: string; hinh_thuc_nguon: string; nguon_file: string | null; vi_tri: string | null;
  ten_goc: string; quy_cach_goc: string | null; gia_goc: number | null; don_vi_gia: string | null;
  kg_moi_don_vi_gia: number | null; thue: string | null; gom_ship: string | null; kenh_gia: string | null;
  muc_gia: string | null; gia_bac: string | null; gia_truoc_km: number | null; trang_thai: string;
  khuyen_mai: string | null; loai_nguon: string; ghi_chu: string | null; ma_kome: string | null;
  nhan: "cung_hang" | "thay_the" | null; nhom_khoa: string | null; ten_nhom: string | null;
  trang_thai_duyet: "ai_doc" | "can_xem" | "da_xac_nhan" | "da_sua" | "nhap_tay";
  yen_chuan: number | null; don_vi_so: string; nen_gia: string; tuoi_ngay: number | null; bat_thuong?: boolean;
};
export type Nhom = {
  nhom_khoa: string; ten_nhom: string | null; don_vi_so: string; ma_kome: string[] | null; gia_kome: number | null;
  so_ben: number; thap_nhat: number; ben_thap_nhat: string; trung_vi: number; cao_nhat: number;
  ty_le_re_hon_kome: number | null; quan_sat: QuanSat[];
};
export type Ben = { ma: string; ten: string; web: string | null; ngay_moi: string | null; hinh_thuc: string | null;
                    so_dong: number; cho_duyet: number };
export type TongQuan = {
  ben: Ben[]; luoi: { ben: string; nganh: string; so_ma: number }[];
  khuyen_mai: { ben: string; ten_goc: string; gia_goc: number | null; gia_truoc_km: number | null; khuyen_mai: string | null; ngay: string }[];
  dieu_kien: { ben: string; loai: string; noi_dung: string; ngay: string }[];
  het_hang: { ben: string; ten_goc: string; ma_kome: string; ten_nhom: string | null; trang_thai: string }[];
};
export const NHAN_DUYET: Record<QuanSat["trang_thai_duyet"], string> = {
  ai_doc: "AI đọc", can_xem: "Cần xem", da_xac_nhan: "Đã xác nhận", da_sua: "Đã sửa", nhap_tay: "Nhập tay" };
export const NHAN_TRANG_THAI: Record<string, string> = { con: "Còn", het: "Hết", sap_ve: "Sắp về", khong_ro: "?" };
```

- [ ] **Step 2: Logic lọc + test** — `giao_dien/src/doi_thu/loc.ts`:

```ts
import type { Nhom, QuanSat } from "./kieu";

export type BoLoc = { tim: string; chi_cung_hang: boolean; chi_xac_nhan: boolean };

const bo_dau = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").toLowerCase();

/** Quan sát còn lại của một nhóm sau bộ lọc (không đổi số của máy chủ — chỉ ẩn dòng). */
export function locQuanSat(ds: QuanSat[], l: BoLoc): QuanSat[] {
  return ds.filter(q => (!l.chi_cung_hang || q.nhan === "cung_hang")
    && (!l.chi_xac_nhan || q.trang_thai_duyet === "da_xac_nhan" || q.trang_thai_duyet === "da_sua" || q.trang_thai_duyet === "nhap_tay"));
}

export function locNhom(ds: Nhom[], l: BoLoc): Nhom[] {
  const t = bo_dau(l.tim.trim());
  return ds.filter(n => (!t || bo_dau(`${n.ten_nhom ?? ""} ${(n.ma_kome ?? []).join(" ")}`).includes(t))
    && locQuanSat(n.quan_sat, l).length > 0);
}

/** Vị trí giá KOME trong nhóm, dạng câu ngắn. */
export function viTriKome(n: Nhom): string | null {
  if (n.gia_kome == null || n.ty_le_re_hon_kome == null) return null;
  const p = Math.round(n.ty_le_re_hon_kome * 100);
  return p === 0 ? "KOME rẻ nhất" : p === 100 ? "KOME đắt nhất" : `${p}% giá đối thủ rẻ hơn KOME`;
}
```

`giao_dien/src/doi_thu/loc.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { locNhom, locQuanSat, viTriKome } from "./loc";
import type { Nhom, QuanSat } from "./kieu";

const qs = (o: Partial<QuanSat>): QuanSat => ({ nhan: "thay_the", trang_thai_duyet: "ai_doc", ...o } as QuanSat);
const nhom = (o: Partial<Nhom>): Nhom => ({ ten_nhom: "Ca Ba sa cat khuc", ma_kome: ["NT01"], quan_sat: [qs({})], ...o } as Nhom);
const L = { tim: "", chi_cung_hang: false, chi_xac_nhan: false };

describe("lọc so sánh", () => {
  it("chỉ cùng hàng ẩn hàng thay thế", () => {
    expect(locQuanSat([qs({ nhan: "cung_hang" }), qs({})], { ...L, chi_cung_hang: true })).toHaveLength(1);
  });
  it("nhóm không còn quan sát nào thì ẩn", () => {
    expect(locNhom([nhom({})], { ...L, chi_xac_nhan: true })).toHaveLength(0);
  });
  it("tìm không dấu, theo cả mã KOME", () => {
    expect(locNhom([nhom({})], { ...L, tim: "basa" })).toHaveLength(0);
    expect(locNhom([nhom({})], { ...L, tim: "ba sa" })).toHaveLength(1);
    expect(locNhom([nhom({})], { ...L, tim: "nt01" })).toHaveLength(1);
  });
  it("vị trí KOME", () => {
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0 }))).toBe("KOME rẻ nhất");
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0.25 }))).toBe("25% giá đối thủ rẻ hơn KOME");
    expect(viTriKome(nhom({ gia_kome: null, ty_le_re_hon_kome: null }))).toBeNull();
  });
});
```

Run: `cd giao_dien && npx vitest run src/doi_thu/loc.test.ts` → PASS.

- [ ] **Step 3: Vỏ màn + tab trên URL** — `giao_dien/src/doi_thu/ManDoiThu.tsx`:

```tsx
// Màn "Thị trường & đối thủ" (/doi-thu, đặc tả 2026-09-29-thi-truong-doi-thu-design.md §5). Bốn tab (?tab=):
// tong_quan (mặc định) · so_sanh · ben (hồ sơ một đối thủ, ?ben=) · duyet. Theo khoảng xem (mốc = cuối khoảng).
import { useState } from "react";
import { giuKhoang } from "../khung/khoang";
import { TabTongQuan } from "./TabTongQuan";
import { TabSoSanh } from "./TabSoSanh";
import { TabHoSo } from "./TabHoSo";
import { TabDuyet } from "./TabDuyet";
import "./doi_thu.css";

type Tab = "tong_quan" | "so_sanh" | "ben" | "duyet";
const TAB: { ma: Tab; nhan: string }[] = [
  { ma: "tong_quan", nhan: "Tổng quan thị trường" }, { ma: "so_sanh", nhan: "So sánh giá" },
  { ma: "ben", nhan: "Hồ sơ đối thủ" }, { ma: "duyet", nhan: "Duyệt / sửa" }];

const docUrl = () => {
  const q = new URLSearchParams(location.search);
  const tab = (TAB.find(t => t.ma === q.get("tab"))?.ma ?? "tong_quan") as Tab;
  return { tab, ben: q.get("ben") ?? "" };
};

export default function ManDoiThu() {
  const [{ tab, ben }, dat] = useState(docUrl);
  const doi = (moi: { tab?: Tab; ben?: string }) => {
    const gt = { tab, ben, ...moi };
    dat(gt);
    const p = new URLSearchParams(location.search);
    gt.tab === "tong_quan" ? p.delete("tab") : p.set("tab", gt.tab);
    gt.ben ? p.set("ben", gt.ben) : p.delete("ben");
    history.replaceState(null, "", giuKhoang(`${location.pathname}?${p}`));
  };
  return (
    <main className="man-doi-thu">
      <h1>Thị trường &amp; đối thủ</h1>
      <div role="tablist" className="dt-tab">
        {TAB.map(t => <button key={t.ma} role="tab" type="button" aria-selected={tab === t.ma}
          onClick={() => doi({ tab: t.ma })}>{t.nhan}</button>)}
      </div>
      {tab === "tong_quan" && <TabTongQuan moBen={b => doi({ tab: "ben", ben: b })} />}
      {tab === "so_sanh" && <TabSoSanh />}
      {tab === "ben" && <TabHoSo ben={ben} chonBen={b => doi({ ben: b })} />}
      {tab === "duyet" && <TabDuyet ben={ben} />}
    </main>
  );
}
```

- [ ] **Step 4: Bốn tab** — mỗi tab một file, dữ liệu qua `useQuery` + `lay()` với khoảng xem:

`giao_dien/src/doi_thu/TabTongQuan.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { ngay, so, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { TongQuan } from "./kieu";
import { NHAN_TRANG_THAI } from "./kieu";

export function TabTongQuan({ moBen }: { moBen: (ma: string) => void }) {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "tong-quan", kx],
    queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const d = q.data;
  const nganh = d ? [...new Set(d.luoi.map(x => x.nganh))].sort() : [];
  const o = (ben: string, n: string) => d?.luoi.find(x => x.ben === ben && x.nganh === n)?.so_ma ?? 0;
  return (
    <div className="dt-luoi-khoi">
      <section className="khoi dt-rong">
        <Khoi tieu_de="Đối thủ × ngành hàng" dang_tai={q.isLoading} loi={q.error?.message ?? null}
          cach_tinh="Ô = số mặt hàng của đối thủ ghép được với ngành đó của KOME (cùng hàng hoặc thay thế).">
          <table className="dt-bang">
            <thead><tr><th>Đối thủ</th>{nganh.map(n => <th key={n}>{n}</th>)}<th>Nguồn mới nhất</th><th>Chờ duyệt</th></tr></thead>
            <tbody>{d?.ben.map(b => (
              <tr key={b.ma}>
                <th><button type="button" className="lien-ket" onClick={() => moBen(b.ma)}>{b.ten}</button></th>
                {nganh.map(n => { const v = o(b.ma, n); return <td key={n} className={v ? "dt-o co" : "dt-o"}>{v ? so(v) : ""}</td>; })}
                <td>{b.ngay_moi ? `${ngay(b.ngay_moi)} · ${b.hinh_thuc === "web" ? "web" : "file"}` : "chưa có"}</td>
                <td>{b.cho_duyet ? so(b.cho_duyet) : ""}</td>
              </tr>))}</tbody>
          </table>
        </Khoi>
      </section>
      <section className="khoi">
        <Khoi tieu_de="Đối thủ đang hết / sắp về" dang_tai={q.isLoading}
          cach_tinh="Hàng ghép được với mã KOME mà bảng giá mới nhất của đối thủ ghi hết hàng hoặc sắp về — cơ hội chào hàng.">
          <ul className="dt-ds">{d?.het_hang.map((h, i) => (
            <li key={i}><b>{h.ten_nhom ?? h.ma_kome}</b> · {h.ben} · {NHAN_TRANG_THAI[h.trang_thai]}
              {" "}<a href={`/san-pham/${encodeURIComponent(h.ma_kome)}`}>mã {h.ma_kome} →</a></li>))}</ul>
        </Khoi>
      </section>
      <section className="khoi">
        <Khoi tieu_de="Khuyến mãi đang chạy" dang_tai={q.isLoading}>
          <ul className="dt-ds">{d?.khuyen_mai.slice(0, 60).map((k, i) => (
            <li key={i}><b>{k.ben}</b> · {k.ten_goc} · {k.gia_goc != null ? yen(k.gia_goc) : ""}
              {k.gia_truoc_km != null && <s> {yen(k.gia_truoc_km)}</s>} {k.khuyen_mai}</li>))}</ul>
        </Khoi>
      </section>
      <section className="khoi dt-rong">
        <Khoi tieu_de="Điều kiện bán của từng bên" dang_tai={q.isLoading}>
          <table className="dt-bang"><tbody>{d?.dieu_kien.map((k, i) => (
            <tr key={i}><th>{k.ben}</th><td>{k.loai}</td><td>{k.noi_dung}</td><td>{ngay(k.ngay)}</td></tr>))}</tbody></table>
        </Khoi>
      </section>
    </div>
  );
}
```

`giao_dien/src/doi_thu/TabSoSanh.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { ONoi } from "../chung/ONoi";
import { ngay, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { Nhom } from "./kieu";
import { NHAN_DUYET } from "./kieu";
import { locNhom, locQuanSat, viTriKome, type BoLoc } from "./loc";

export function TabSoSanh() {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "so-sanh", kx],
    queryFn: () => lay<{ nhom: Nhom[] }>(`/api/doi-thu/so-sanh${kx ? "?" + kx : ""}`) });
  const [l, datL] = useState<BoLoc>({ tim: "", chi_cung_hang: false, chi_xac_nhan: false });
  const [mo, datMo] = useState<string | null>(null);
  const ds = locNhom(q.data?.nhom ?? [], l);
  const donVi = (n: Nhom) => (n.don_vi_so === "kg" ? "/kg" : `/${n.don_vi_so.replace("don_vi:", "")}`);
  return (
    <section className="khoi">
      <Khoi tieu_de="So sánh giá theo nhóm" dang_tai={q.isLoading} loi={q.error?.message ?? null}
        cach_tinh="Giá quy về chưa thuế (giá có thuế ÷ 1,08) và về ¥/kg khi biết khối lượng. Giá KOME = đơn giá thực 90 ngày (Σ doanh thu thuần ÷ Σ kg đã bán). Không tính hàng hết, giá khách kể và giá bất thường (> 2× hoặc < ½ trung vị khi nhóm có ≥ 3 bên).">
        <div className="dt-loc">
          <input type="search" placeholder="Tìm nhóm / mã KOME" value={l.tim} onChange={e => datL({ ...l, tim: e.target.value })} />
          <label><input type="checkbox" checked={l.chi_cung_hang} onChange={e => datL({ ...l, chi_cung_hang: e.target.checked })} /> Chỉ cùng hàng</label>
          <label><input type="checkbox" checked={l.chi_xac_nhan} onChange={e => datL({ ...l, chi_xac_nhan: e.target.checked })} /> Chỉ số đã xác nhận</label>
        </div>
        <table className="dt-bang">
          <thead><tr><th>Nhóm</th><th>KOME</th><th>Thấp nhất</th><th>Trung vị</th><th>Cao nhất</th><th>Số bên</th><th>Vị trí KOME</th></tr></thead>
          <tbody>{ds.map(n => (
            <Fragment key={n.nhom_khoa + n.don_vi_so}>
              <tr className="dt-dong" onClick={() => datMo(mo === n.nhom_khoa ? null : n.nhom_khoa)}>
                <th>{n.ten_nhom ?? n.nhom_khoa}</th>
                <td>{n.gia_kome != null ? yen(n.gia_kome) + donVi(n) : "—"}</td>
                <td>{yen(n.thap_nhat)}{donVi(n)} <span className="nhat">{n.ben_thap_nhat}</span></td>
                <td>{yen(n.trung_vi)}{donVi(n)}</td>
                <td>{yen(n.cao_nhat)}{donVi(n)}</td>
                <td>{n.so_ben}</td>
                <td>{viTriKome(n) ?? "—"}</td>
              </tr>
              {mo === n.nhom_khoa && locQuanSat(n.quan_sat, l).map(x => (
                <tr key={x.nguon + x.id} className={"dt-con" + (x.bat_thuong ? " bat-thuong" : "")}>
                  <td>{x.ten_doi_thu ?? x.ma_doi_thu}</td>
                  <td colSpan={2}>{x.ten_goc} <span className="nhat">{x.quy_cach_goc}</span></td>
                  <td><ONoi noi_dung={<div className="o-noi-chu">{x.nen_gia}<br />Nguồn: {x.nguon_file ?? x.loai_nguon} · {ngay(x.ngay_nguon)}{x.vi_tri ? ` · ${x.vi_tri}` : ""}</div>}>
                    {x.yen_chuan != null ? yen(x.yen_chuan) : "—"}</ONoi></td>
                  <td>{x.gia_goc != null ? `${yen(x.gia_goc)}/${x.don_vi_gia ?? "?"}` : "—"}</td>
                  <td>{x.nhan === "cung_hang" ? "cùng hàng" : "thay thế"}</td>
                  <td>{NHAN_DUYET[x.trang_thai_duyet]}{x.bat_thuong ? " · bất thường" : ""}</td>
                </tr>))}
            </Fragment>))}</tbody>
        </table>
      </Khoi>
    </section>
  );
}
```

`giao_dien/src/doi_thu/TabHoSo.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { ngay, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { QuanSat, TongQuan } from "./kieu";
import { NHAN_TRANG_THAI } from "./kieu";

type HoSo = { ben: { ma: string; ten: string; web: string | null; ghi_chu: string | null };
              dieu_kien: { loai: string; noi_dung: string; ngay: string }[]; quan_sat: (QuanSat & { hien_hanh: boolean })[] };

export function TabHoSo({ ben, chonBen }: { ben: string; chonBen: (ma: string) => void }) {
  const kx = chuoiKhoang(useKhoang());
  const tq = useQuery({ queryKey: ["doi-thu", "tong-quan", kx], queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const q = useQuery({ queryKey: ["doi-thu", "ben", ben, kx], enabled: !!ben,
    queryFn: () => lay<HoSo>(`/api/doi-thu/ben/${encodeURIComponent(ben)}${kx ? "?" + kx : ""}`) });
  const hien = q.data?.quan_sat.filter(x => x.hien_hanh) ?? [];
  const lich_su = (x: QuanSat) => q.data?.quan_sat.filter(y => y.ma_hang_dt === x.ma_hang_dt && y.kenh_gia === x.kenh_gia && y.muc_gia === x.muc_gia) ?? [];
  return (
    <section className="khoi">
      <Khoi tieu_de={q.data?.ben.ten ?? "Hồ sơ đối thủ"} dang_tai={!!ben && q.isLoading} loi={q.error?.message ?? null}>
        <select value={ben} onChange={e => chonBen(e.target.value)} aria-label="Chọn đối thủ">
          <option value="">— chọn đối thủ —</option>
          {tq.data?.ben.map(b => <option key={b.ma} value={b.ma}>{b.ten}</option>)}
        </select>
        {q.data?.ben.web && <p><a href={q.data.ben.web} rel="noreferrer" target="_blank">{q.data.ben.web}</a></p>}
        {q.data && <>
          <h3>Điều kiện</h3>
          <ul className="dt-ds">{q.data.dieu_kien.map((k, i) => <li key={i}>{k.loai} · {k.noi_dung} · {ngay(k.ngay)}</li>)}</ul>
          <h3>Mặt hàng ({hien.length})</h3>
          <table className="dt-bang"><thead><tr><th>Hàng</th><th>Giá</th><th>¥ quy đổi</th><th>Trạng thái</th><th>Ghép KOME</th><th>Lịch sử</th></tr></thead>
            <tbody>{hien.map(x => (
              <tr key={x.nguon + x.id}>
                <td>{x.ten_goc} <span className="nhat">{x.quy_cach_goc}</span></td>
                <td>{x.gia_goc != null ? `${yen(x.gia_goc)}/${x.don_vi_gia ?? "?"}` : "—"}</td>
                <td>{x.yen_chuan != null ? yen(x.yen_chuan) : "—"}</td>
                <td>{NHAN_TRANG_THAI[x.trang_thai]}</td>
                <td>{x.ma_kome ? <a href={`/san-pham/${encodeURIComponent(x.ma_kome)}`}>{x.ma_kome}</a> : ""}</td>
                <td>{lich_su(x).map(y => `${ngay(y.ngay_nguon)} ${y.gia_goc != null ? yen(y.gia_goc) : "—"}`).join(" · ")}</td>
              </tr>))}</tbody></table>
        </>}
      </Khoi>
    </section>
  );
}
```

`giao_dien/src/doi_thu/TabDuyet.tsx`:

```tsx
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { gui, lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { ngay, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { QuanSat } from "./kieu";
import { NHAN_DUYET } from "./kieu";

const LOC = [["", "Tất cả"], ["can_xem", "Cần xem"], ["bat_thuong", "Bất thường"], ["chua_xac_nhan", "Chưa ai xác nhận"], ["chua_ghep", "Chưa ghép"]];
const LOAI_NGUON = [["bang_gia", "Bảng giá / web"], ["chung_tu", "Chứng từ khách đưa"], ["to_roi", "Tờ rơi / tin nhắn"], ["khach_ke", "Khách kể"], ["khac", "Nghe nói / khác"]];
const TRUONG: [keyof QuanSat, string][] = [["ten_goc", "Tên"], ["quy_cach_goc", "Quy cách"], ["gia_goc", "Giá"], ["don_vi_gia", "Đơn vị"],
  ["kg_moi_don_vi_gia", "Kg / đơn vị"], ["thue", "Thuế (chua/co/khong_ro)"], ["gom_ship", "Ship (co/khong/khong_ro)"],
  ["kenh_gia", "Kênh"], ["muc_gia", "Mức"], ["trang_thai", "Trạng thái (con/het/sap_ve/khong_ro)"]];

export function TabDuyet({ ben }: { ben: string }) {
  const kx = chuoiKhoang(useKhoang());
  const qc = useQueryClient();
  const [loc, datLoc] = useState("can_xem");
  const url = `/api/doi-thu/duyet?${new URLSearchParams({ ben, loc })}${kx ? "&" + kx : ""}`;
  const q = useQuery({ queryKey: ["doi-thu", "duyet", ben, loc, kx], queryFn: () => lay<{ dong: QuanSat[] }>(url) });
  const [chon, datChon] = useState<QuanSat | null>(null);
  const [sua, datSua] = useState<Record<string, string>>({});
  const [nguon, datNguon] = useState({ loai_nguon: "", ghi_chu_nguon: "" });
  const [loi, datLoi] = useState<string | null>(null);
  const xong = () => { datChon(null); datSua({}); datLoi(null); qc.invalidateQueries({ queryKey: ["doi-thu"] }); };
  const lam = (p: Promise<unknown>) => p.then(xong).catch((e: Error) => datLoi(e.message));
  return (
    <div className="dt-duyet">
      <section className="khoi">
        <Khoi tieu_de="Dòng cần duyệt" dang_tai={q.isLoading} loi={q.error?.message ?? null}>
          <div className="dt-loc" role="group" aria-label="Lọc">
            {LOC.map(([m, n]) => <button key={m} type="button" aria-pressed={loc === m} onClick={() => datLoc(m)}>{n}</button>)}
          </div>
          <ul className="dt-ds dt-chon">{q.data?.dong.map(x => (
            <li key={x.nguon + x.id}><button type="button" aria-pressed={chon?.id === x.id && chon.nguon === x.nguon}
              onClick={() => { datChon(x); datSua({}); datLoi(null); }}>
              <b>{x.ma_doi_thu}</b> · {x.ten_goc} · {x.gia_goc != null ? yen(x.gia_goc) : "—"}/{x.don_vi_gia ?? "?"} ·{" "}
              {NHAN_DUYET[x.trang_thai_duyet]}{x.bat_thuong ? " · bất thường" : ""}</button></li>))}</ul>
        </Khoi>
      </section>
      {chon && chon.nguon === "nap" && (
        <section className="khoi dt-sua">
          <Khoi tieu_de={chon.ten_goc} canh_bao={loi}>
            <p className="nhat">Nguồn: {chon.nguon_file} · {chon.vi_tri} · {ngay(chon.ngay_nguon)}{chon.ghi_chu ? ` · ${chon.ghi_chu}` : ""}</p>
            {TRUONG.map(([k, n]) => (
              <label key={k}>{n}<input value={sua[k] ?? String(chon[k] ?? "")} onChange={e => datSua({ ...sua, [k]: e.target.value })} /></label>))}
            <div className="dt-nut">
              <button type="button" onClick={() => lam(gui("/api/doi-thu/xac-nhan", { fact_id: chon.id }))}>Đúng rồi</button>
              <button type="button" disabled={!Object.keys(sua).length}
                onClick={() => lam(gui("/api/doi-thu/sua", { fact_id: chon.id, thay_doi: sua }))}>Lưu sửa (AI đọc sai)</button>
            </div>
            <fieldset><legend>Giá đã đổi (nguồn mới)</legend>
              <select value={nguon.loai_nguon} onChange={e => datNguon({ ...nguon, loai_nguon: e.target.value })} aria-label="Loại nguồn">
                <option value="">— loại nguồn (bắt buộc) —</option>
                {LOAI_NGUON.map(([m, n]) => <option key={m} value={m}>{n}</option>)}</select>
              <input placeholder="Ghi chú nguồn (Zalo 29/9, hoá đơn khách …)" value={nguon.ghi_chu_nguon}
                onChange={e => datNguon({ ...nguon, ghi_chu_nguon: e.target.value })} />
              <button type="button" disabled={!nguon.loai_nguon || !sua.gia_goc}
                onClick={() => lam(gui("/api/doi-thu/gia-moi", { fact_goc_id: chon.id, ...sua, ...nguon }))}>Lưu giá mới</button>
            </fieldset>
            <fieldset><legend>Ghép với KOME</legend>
              <input placeholder="Mã KOME (trống = không ghép)" defaultValue={chon.ma_kome ?? ""} id="dt-ma-kome" />
              {(["cung_hang", "thay_the", "khong"] as const).map(n => (
                <button key={n} type="button" onClick={() => {
                  const ma = (document.getElementById("dt-ma-kome") as HTMLInputElement).value.trim();
                  lam(gui("/api/doi-thu/ghep", { ma_doi_thu: chon.ma_doi_thu, ma_hang_dt: chon.ma_hang_dt,
                    product_code: n === "khong" ? null : ma || null, nhom_id: null, nhan: n }));
                }}>{n === "cung_hang" ? "Cùng hàng" : n === "thay_the" ? "Thay thế" : "Không ghép"}</button>))}
            </fieldset>
          </Khoi>
        </section>)}
    </div>
  );
}
```

`giao_dien/src/doi_thu/doi_thu.css` — dùng token màu có sẵn (đọc `kome/web/spa` biến CSS trong `giao_dien/src/khung/*.css`, ví dụ `var(--vien)`, `var(--nen-2)`, `var(--do)`); tối thiểu:

```css
.man-doi-thu { padding: 16px; }
.dt-tab { display: flex; gap: 8px; margin: 12px 0; flex-wrap: wrap; }
.dt-luoi-khoi { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
.dt-rong { grid-column: 1 / -1; }
.dt-bang { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
.dt-bang th, .dt-bang td { padding: 4px 8px; border-bottom: 1px solid var(--vien); text-align: left; }
.dt-o.co { background: color-mix(in srgb, var(--lam, #3b82f6) 18%, transparent); text-align: center; }
.dt-dong { cursor: pointer; }
.dt-con td { font-size: .9em; }
.dt-con.bat-thuong td { color: var(--do); }
.dt-loc { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.dt-ds { list-style: none; padding: 0; margin: 0; max-height: 420px; overflow: auto; }
.dt-chon button { width: 100%; text-align: left; }
.dt-duyet { display: grid; grid-template-columns: minmax(280px, 1fr) minmax(320px, 1fr); gap: 16px; }
.dt-sua label { display: grid; grid-template-columns: 160px 1fr; gap: 8px; margin: 4px 0; }
.dt-nut { display: flex; gap: 8px; margin: 8px 0; }
.nhat { opacity: .7; }
@media (max-width: 760px) { .dt-duyet { grid-template-columns: 1fr; } .dt-sua label { grid-template-columns: 1fr; } }
```

- [ ] **Step 5: Định tuyến + thanh bên**

`giao_dien/src/main.tsx`: cạnh `ManMuaVu` thêm `const ManDoiThu = lazy(() => import("./doi_thu/ManDoiThu"));`; trong `man()` sau dòng `/mua-vu`: `if (duong === "/doi-thu") return () => <ManDoiThu />;`; trong `boChon()` thêm `"/doi-thu"` vào mảng `["/cong-no", "/kho-hang", "/lien-he", "/du-bao"]`.

`giao_dien/src/khung/muc.ts`: thêm mục vào nhóm Khách hàng (ngay sau mục bản đồ): `{ ma: "doithu", nhan: "Thị trường & đối thủ", url: "/doi-thu", icon: "<một icon có sẵn trong I của khung/icon.tsx, ví dụ 'target' nếu có, không thì 'chart'>" }`; sửa chú thích đầu file: bỏ "thị trường & đối thủ" khỏi danh sách "bốn màn bị cắt" và thêm dòng: `// "doithu" (Thị trường & đối thủ, 2026-09-29) — lộ trình §4.2 từng cắt, đặc tả 2026-09-29-thi-truong-doi-thu-design.md §0 đảo lại; icon "<tên>" TA CHỌN.`

- [ ] **Step 6: Build + kiểm**

```bash
cd giao_dien && npx vitest run && npm run build && cd ..
pytest tests/test_doi_thu_api.py tests/test_api.py::test_ban_build_khop_ma_nguon -v
```
Expected: PASS

- [ ] **Step 7: Xem thật trong trình duyệt** — chạy preview (`preview_start` với cấu hình dev server có sẵn trong `.claude/launch.json`), mở `/doi-thu`: bốn tab mở được, không lỗi console, cỡ 375px không cuộn ngang. Chụp ảnh làm bằng chứng.

- [ ] **Step 8: Commit**

```bash
git add giao_dien/src/doi_thu giao_dien/src/main.tsx giao_dien/src/khung/muc.ts kome/web/spa
git commit -m "feat(doi-thu): man React /doi-thu — tong quan, so sanh, ho so doi thu, duyet/sua

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Khối "giá đối thủ" ở Sản phẩm 360

**Files:**
- Create: `giao_dien/src/san_pham/ho_so/KhoiDoiThu.tsx`
- Modify: file cột trái của `/san-pham/{mã}` trong `giao_dien/src/san_pham/ho_so/` (tìm component render "Việc với mã này") — thêm `<KhoiDoiThu ma={ma} />` cuối cột trái
- Test: `tests/test_doi_thu_api.py` (thêm test dưới)

- [ ] **Step 1: Test** — thêm vào `tests/test_doi_thu_api.py`:

```python
def test_khoi_san_pham_tra_nhom_theo_kg(conn, batch, test_db_url):
    _nen(conn, batch)
    d = _web(test_db_url).get("/api/san-pham/NT01/doi-thu").json()
    assert d["nhom"]["nhom_khoa"] == "ma:NT01" and d["nhom"]["so_ben"] == 3
    assert (_SRC / "san_pham" / "ho_so" / "KhoiDoiThu.tsx").exists()
```

- [ ] **Step 2: Component** — `giao_dien/src/san_pham/ho_so/KhoiDoiThu.tsx`:

```tsx
// Cột trái Sản phẩm 360: "Đối thủ bán nhóm này" (đặc tả Thị trường & đối thủ §5.5). 1 lượt hỏi, endpoint riêng
// (/api/san-pham/{mã}/doi-thu) — ngoài trần 5 của hồ sơ.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { yen } from "../../dinh_dang";
import { chuoiKhoang, giuKhoang, useKhoang } from "../../khung/khoang";
import type { Nhom } from "../../doi_thu/kieu";
import { viTriKome } from "../../doi_thu/loc";

export function KhoiDoiThu({ ma }: { ma: string }) {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["san-pham", ma, "doi-thu", kx],
    queryFn: () => lay<{ nhom: Nhom | null }>(`/api/san-pham/${encodeURIComponent(ma)}/doi-thu${kx ? "?" + kx : ""}`) });
  const n = q.data?.nhom;
  if (!n) return null;
  return (
    <div className="viec-khoi">
      <h3>Đối thủ bán nhóm này</h3>
      <p>Thấp nhất {yen(n.thap_nhat)}/kg ({n.ben_thap_nhat}) · trung vị {yen(n.trung_vi)} · {n.so_ben} bên</p>
      <p>KOME {n.gia_kome != null ? `${yen(n.gia_kome)}/kg` : "—"}{viTriKome(n) ? ` · ${viTriKome(n)}` : ""}</p>
      <a href={giuKhoang(`/doi-thu?tab=so_sanh`)}>Xem so sánh →</a>
    </div>
  );
}
```

- [ ] **Step 3: Build, test, commit**

```bash
cd giao_dien && npm run build && cd ..
pytest tests/test_doi_thu_api.py tests/test_san_pham_360.py tests/test_api.py::test_ban_build_khop_ma_nguon -v
git add giao_dien/src/san_pham kome/web/spa tests/test_doi_thu_api.py
git commit -m "feat(doi-thu): khoi gia doi thu o cot trai San pham 360

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: CLAUDE.md, tài liệu sống, toàn bộ test

**Files:**
- Modify: `CLAUDE.md` (bảng "Các trang của web app" + một mục bất biến), `scripts/sinh_cot_dung.py` (`MAN` khai `kome/doi_thu.py`)

- [ ] **Step 1: CLAUDE.md** — thêm một dòng vào bảng trang:

```markdown
| `/doi-thu` | **Thị trường & đối thủ — React** (2026-09-29, đặc tả `2026-09-29-thi-truong-doi-thu-design.md`): 4 tab (Tổng quan thị trường · So sánh giá theo nhóm · Hồ sơ đối thủ · Duyệt / sửa). Mọi người đăng nhập sửa được (ngoài `DUONG_KHO_DU_LIEU`). `/api/doi-thu/*` (mỗi GET 1 lượt + phiên bản), POST chỉ JSON. Khối "Đối thủ bán nhóm này" ở `/san-pham/{mã}` (`/api/san-pham/{mã}/doi-thu`) | `mart.gia_doi_thu_hien_hanh`, `mart.so_sanh_nhom`, `mart.gia_kome_kg`, `core.fact_gia_doi_thu`, `core.fact_dieu_kien_doi_thu`, `app.*doi_thu*` |
```

và mục bất biến (sau bất biến 058):

```markdown
**Bất biến (059–060, Thị trường & đối thủ — chủ DN chốt 2026-09-29):** bảng giá đối thủ vào `core.fact_gia_doi_thu`
qua ô nạp "Bảng giá đối thủ" (gói do `scripts/goi_doi_thu.py` dựng — Claude đọc file / web đối thủ TRONG PHIÊN, web không
gọi AI). Sửa của sale KHÔNG đụng `core`: sửa lỗi đọc = `app.dinh_chinh_gia`, giá đã đổi = `app.gia_doi_thu_tay` (loại
nguồn bắt buộc, `app.loai_nguon`) — cả hai + `app.doi_thu_nhat_ky` CHỈ THÊM. Quy đổi ¥/kg chưa thuế, ghép hiện hành
(`app.ghep_hang` thắng đề xuất AI), nhóm (có tên → nhóm ngầm định theo mã KOME), bất thường (`mart.la_gia_bat_thuong`:
> 2× / < ½ trung vị khi ≥ 3 bên) và giá KOME (`mart.gia_kome_kg`, tỷ số các tổng 90 ngày, đọc `ban_den_moc`) viết ĐÚNG
MỘT LẦN ở 060. Trung vị không gồm hàng hết, giá khách kể, giá bất thường. Quan sát quay về mốc (`ngay_nguon ≤ moc_lui()`).
Khoá hàng đối thủ qua các tháng `ma_hang_dt` (JAN hợp lệ → mã của bên → tên chuẩn hoá `kome/ten_hang.py`). Luật đọc
riêng từng bên: `docs/doi-thu/so-tay-theo-ben.md`. Có test canh: `tests/test_doi_thu_bang.py`, `tests/test_mart_doi_thu.py`,
`tests/test_doi_thu.py`, `tests/test_doi_thu_api.py`. **Migration 059–060 phải chạy TRƯỚC khi triển khai.**
```

- [ ] **Step 2: Tài liệu sinh** — mở `scripts/sinh_cot_dung.py`, thêm `kome/doi_thu.py` vào `MAN` theo đúng dạng các mục sẵn có (tên màn "Thị trường & đối thủ", đường `/doi-thu`); chạy:

```bash
python scripts/sinh_tai_lieu.py
python scripts/sinh_cot_dung.py
```

- [ ] **Step 3: Toàn bộ test** (chạy một mình trên `kome_test`, không ngắt giữa chừng; ~4 phút)

```bash
pytest -q
cd giao_dien && npx vitest run && cd ..
```
Expected: tất cả PASS. Có đỏ thì sửa tới khi xanh — không bỏ qua test.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md scripts/sinh_cot_dung.py kome/web/*.json
git commit -m "docs(doi-thu): CLAUDE.md — trang /doi-thu va bat bien 059–060; tai lieu song sinh lai

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Nạp tháng 8 thật (cần chủ DN đồng ý từng bước ghi vào CSDL thật)

**Files:** không sửa mã. Dữ liệu vào: CSV phép thử trong thư mục tạm của phiên.

- [ ] **Step 1: Dựng gói** (chỉ ghi file vào thư mục tạm)

```bash
python scripts/goi_doi_thu.py "C:/Users/TRANTR~1/AppData/Local/Temp/claude/C--Antigravity-kome-data/abd73e57-76bc-42c2-972f-2c0ca8050dd8/scratchpad" --ngay 2026-08-31 --ra "C:/Users/TRANTR~1/AppData/Local/Temp/claude/C--Antigravity-kome-data/abd73e57-76bc-42c2-972f-2c0ca8050dd8/scratchpad/goi"
```
Expected: in số dòng (≈ 4.000) và danh sách cảnh báo; kiểm tay 10 dòng ngẫu nhiên của `doi_thu_gia_20260831.xlsx` so với CSV.

- [ ] **Step 2: DỪNG — hỏi chủ DN** trước khi chạy migration 059–060 trên CSDL thật (chạy bằng `postgres`; nếu chạy trong SQL editor thì INSERT tên file vào `meta.schema_migration` — memory `manual-migration-log`) và trước khi nạp gói. Nạp qua `/kho-du-lieu/nap`, ô "Bảng giá đối thủ" (người có cờ kho dữ liệu bấm Xác nhận).

- [ ] **Step 3: Kiểm sau nạp** (chỉ đọc, `BEGIN READ ONLY` — memory `pooler-set-leak`): số dòng `core.fact_gia_doi_thu` theo bên khớp gói; `mart.so_sanh_nhom` có ≥ 100 nhóm; mở `/doi-thu` bốn tab. Báo chủ DN kết quả kèm ảnh chụp.

---

## Self-Review

- **Spec coverage:** §4.1 → Task 1–3; §4.2 → Task 1, 5; §4.3 → Task 3 (`kome/ten_hang.py`); §4.4 → Task 4; §5.1–5.4 → Task 7; §5.5 → Task 8; §7 bước 3–4 → Task 3, 10; §9 test + ngân sách → Task 4–6, 9; §6 (Đợt 2) và ảnh (Đợt 3) cố ý KHÔNG có ở đây; `tiep_xuc_nhac` không tạo ở 059 (Đợt 2 tự thêm migration riêng).
- **Chỗ phải đọc code thật khi làm** (đã ghi rõ trong bước, không phải chỗ trống): nhánh `tinh_luoi_phu` cho cột mới (Task 2 Step 5), dạng bộ ba `LOAI` và biểu thức `ai` của nhánh ngân sách (Task 6 Step 5), tên icon có sẵn (Task 7 Step 5), component cột trái Sản phẩm 360 (Task 8), dạng mục `MAN` (Task 9).
- **Nhất quán tên:** `COT_GIA`/`COT_DIEU_KIEN` (Task 2 → 3), `ma_hang_dt`, `nhom_khoa` (`ma:`/`n:`), `trang_thai_duyet`, `yen_chuan`, `don_vi_so`, `bat_thuong` — cùng tên ở SQL, Python, TS.
