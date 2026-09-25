# Nạp hằng ngày trên Vercel — kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bản Vercel nạp / kiểm / xác nhận / huỷ / hoàn tác được file OBC hằng ngày (≤ 4 MB).

**Architecture:** File chờ xác nhận đi qua một "kho" hai kiểu (`KhoDia` giữ nguyên hành vi ổ
đĩa, `KhoCsdl` = bảng `meta.nap_cho`); trên Vercel không lưu file gốc (`archived_to` NULL).
`_chi_doc` thôi phụ thuộc `VERCEL`. Trình duyệt chặn file quá cỡ khi máy chủ báo giới hạn.

**Tech Stack:** FastAPI, psycopg 3, Postgres (Supabase), React + Vite (build commit ở `kome/web/spa/`).

**Spec:** `docs/superpowers/specs/2026-09-25-nap-tren-vercel-design.md`

## Global Constraints

- Migration mới chạy bằng `postgres`; không sửa migration đã chạy.
- `kome/web/app.py` không nhập `kome.pipeline` / pandas ở mức ngoài cùng.
- `kome_ingest` KHÔNG được DELETE `meta.ingest_batch`; chỉ được DELETE `meta.nap_cho`.
- `kome_app` không có quyền gì trên `meta.nap_cho`.
- Giới hạn trình duyệt: `GIOI_HAN_WEB = 4_000_000` byte, chỉ khi `tren_mang()`.
- Sửa `giao_dien/` ⇒ `cd giao_dien && npm run build`; sửa migration ⇒ `python scripts/sinh_tai_lieu.py` và `python scripts/sinh_cot_dung.py`.
- KHÔNG chạy nhiều pytest song song (mỗi phiên dựng lại schema kome_test).

---

### Task 1: Migration 045 + lô không có file gốc

**Files:**
- Create: `db/migrations/045_nap_cho.sql`
- Modify: `kome/archive.py` (`store`), `kome/pipeline.py` (`ingest` chữ ký)
- Test: `tests/test_nap_vercel.py` (mới)

**Interfaces:**
- Produces: bảng `meta.nap_cho(ma text PK, ten_file text, o text, noi_dung bytea, luc timestamptz)`;
  `archive.store(..., archive_dir: Path | None, ...)`; `pipeline.ingest(conn, path, archive_dir: Path | None)`.

- [ ] Viết test: `ingest(conn, OK, None)` → lô có `archived_to IS NULL`; nạp lại cùng file → `skipped`;
  `undo_batch` lô đó chạy; `kome_ingest` DELETE được `meta.nap_cho`, không DELETE được
  `meta.ingest_batch`; `kome_app` SELECT `meta.nap_cho` bị từ chối (dùng `SET LOCAL ROLE` trong giao dịch).
- [ ] Chạy test → đỏ.
- [ ] Viết `045_nap_cho.sql`:
```sql
ALTER TABLE meta.ingest_batch ALTER COLUMN archived_to DROP NOT NULL;
CREATE TABLE meta.nap_cho (
    ma text PRIMARY KEY CHECK (ma ~ '^[0-9a-f]{32}$'),
    ten_file text NOT NULL, o text NOT NULL DEFAULT '',
    noi_dung bytea NOT NULL, luc timestamptz NOT NULL DEFAULT now());
REVOKE ALL ON meta.nap_cho FROM kome_app, kome_report;
GRANT SELECT, INSERT, DELETE ON meta.nap_cho TO kome_ingest;
```
- [ ] `archive.store`: `archive_dir is None` ⇒ không chép, `dest = None`, INSERT `archived_to` NULL.
- [ ] Chạy test → xanh; `python scripts/sinh_tai_lieu.py`; commit.

### Task 2: Kho file chờ hai kiểu + nối vào route

**Files:**
- Modify: `kome/nap_cho.py` (thêm `KhoDia`, `KhoCsdl`, `tao_kho`), `kome/web/app.py` (route `/upload*`, `_du_lieu_nap`, `_chi_doc`, `lam_nong` trên Vercel)
- Test: `tests/test_nap_vercel.py`, sửa `tests/test_bao_mat.py`, `tests/test_bo_cuc.py`

**Interfaces:**
- Produces: lớp có `luu(nguon, ten_file, o) -> (ma, Path)`, `doc(ma) -> (Path, dict) | None`,
  `xoa(ma)`, `danh_sach() -> list[dict]`, `don_cu(gio=GIU_GIO)`; `nap_cho.tao_kho(kieu, archive_dir, open_conn)`;
  `nap_cho.kieu_mac_dinh() -> "dia" | "csdl"` (env `KOME_KHO_NAP`, mặc định `csdl` khi `tren_mang()`).

- [ ] Test `KhoCsdl`: lưu → đọc đúng byte + tên → xoá; mã sai dạng → None; `don_cu` xoá dòng có `luc` lùi 25 giờ, giữ dòng mới.
- [ ] Test luồng hai bước với `KOME_KHO_NAP=csdl`: kiểm → 1 dòng chờ; xác nhận → lô có `archived_to` NULL, 0 dòng chờ; huỷ → 0 dòng chờ; thả nhầm ô → 0 dòng chờ.
- [ ] Test `_chi_doc`: `VERCEL=1` không `KOME_CHI_DOC` → `POST /upload` nạp được; `KOME_CHI_DOC=1` → 403.
- [ ] Sửa test cũ khẳng định "Vercel chỉ-đọc" (`test_tren_vercel_khong_nap_va_khong_hoan_tac_duoc`, `test_ban_chi_doc_an_han_muc_nap_du_lieu`, `test_ban_vercel_chi_doc_van_luu_duoc_bo_cuc`) sang `KOME_CHI_DOC=1`.
- [ ] Chạy → đỏ. Cài: `KhoDia` bọc các hàm module sẵn có; `KhoCsdl` mở `open_conn()` mỗi thao tác, `doc` ghi `noi_dung` ra `tempfile.gettempdir()/kome_cho/<ma>/<ten>`.
  `app.py`: `kho = nap_cho.tao_kho(...)`; `archive_luu = archive_dir if kho là KhoDia else None`; mọi `nap_cho.X(archive_dir, …)` → `kho.X(…)`; `ingest(conn, …, archive_luu)`.
  `_chi_doc` chỉ đọc `KOME_CHI_DOC`, cộng thêm `chi_doc = _chi_doc() or không có DATABASE_URL`.
  `anh_chup.lam_nong` không làm gì khi `tren_mang()`.
- [ ] Chạy test → xanh; commit.

### Task 3: Giới hạn cỡ ở trình duyệt

**Files:**
- Modify: `kome/web/app.py` (khởi đầu: `gioi_han_tai_len`), `giao_dien/src/khoi_dau.ts`, `giao_dien/src/he_thong/KhoDuLieu.tsx`
- Test: `tests/test_nap_vercel.py`

- [ ] Test: `VERCEL=1` → `kd()["gioi_han_tai_len"] == 4_000_000`; không → `None`; nguồn `KhoDuLieu.tsx` có câu "quá lớn cho bản web".
- [ ] Cài: ô từng loại kiểm `file.size` trước `requestSubmit()`; ô nhiều file kiểm TỔNG trong `onSubmit`, quá thì `preventDefault()` và hiện câu (gợi ý thả từng file vào ô riêng). Câu chỉ-đọc đổi thành "Bản này đang tắt nạp dữ liệu — nạp ở máy trong công ty."
- [ ] `npm run build`; chạy test → xanh; commit.

### Task 4: Tài liệu + cấu hình Vercel

**Files:** `requirements.txt`, `server.py`, `CLAUDE.md`, `docs/trien-khai-vercel.md`, `kome/web/app.py` (docstring `_chi_doc`), đặc tả.

- [ ] `requirements.txt` thêm `pandas>=2.2`, `python-calamine>=0.2`; viết lại chú thích.
- [ ] CLAUDE.md: bảng "Hai bản chạy", đoạn `_chi_doc`, bất biến 045.
- [ ] `python scripts/sinh_tai_lieu.py`, `python scripts/sinh_cot_dung.py`; toàn bộ `pytest`; commit.
