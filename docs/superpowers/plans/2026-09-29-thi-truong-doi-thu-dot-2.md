# Thị trường & đối thủ — Đợt 2 (tin hiện trường `@`) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Sale gõ `@đối thủ` `@hàng` trong ô ghi tiếp xúc (hồ sơ khách 360 + thẻ `/lien-he`), kèm ô giá tuỳ chọn; tin đó nối vào hồ sơ khách, hồ sơ đối thủ, So sánh giá và Tổng quan thị trường.

**Architecture:** Câu ghi chú vẫn là chữ thường trong `app.nhat_ky_tiep_xuc` (không đổi 030). Thẻ vào bảng chỉ-thêm mới `app.tiep_xuc_nhac` (vị trí trong câu); giá khách kể vào `app.gia_doi_thu_tay` (`loai_nguon = 'khach_ke'`) với cột mới `nhom_khoa` để `mart` xếp đúng nhóm. Mọi thứ ghi trong MỘT giao dịch cùng dòng tiếp xúc. Đọc qua các hàm một-lượt-hỏi của `kome/doi_thu.py`.

**Spec:** `docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md` §6 (đọc cả §2, §4).

## Global Constraints
- `app.nhat_ky_tiep_xuc` KHÔNG đổi schema/CHECK; câu gốc không bao giờ sửa. `app.tiep_xuc_nhac` CHỈ THÊM (`REVOKE UPDATE, DELETE … FROM kome_app`).
- Thẻ `@hàng` luôn trỏ tới một NHÓM (`nhom_khoa` = `ma:<mã KOME>` hoặc `n:<id>` — cùng định dạng 060).
- Máy KHÔNG tự đọc số trong câu (quyết định 1A): giá chỉ đến từ ô giá tuỳ chọn.
- Giá khách kể không vào trung vị bảng giá (đã có ở 060); qua cùng quy đổi + bắt bất thường; tin trùng (khách, bên, nhóm) → mới nhất là hiện trạng; mặc định chỉ tính 90 ngày.
- Hồ sơ khách `ho_so()` vẫn ≤ 8 truy vấn — khối mới đi endpoint riêng (1 lượt). Mọi GET mới 1 lượt (+ ảnh chụp), không `chi_nap`.
- Migration 063 chạy bằng `postgres` qua `python db/migrate.py` (không qua SQL Editor — bẫy RLS, memory supabase-sql-editor-rls). 059–062 không sửa.
- Định dạng số qua `dinh_dang.ts`; `giuKhoang()` cho mọi đổi URL; build `kome/web/spa` được commit.

---

### Task 1: Migration 063 + chỉ số

**Files:** Create `db/migrations/063_tin_hien_truong.sql`; Test `tests/test_mart_doi_thu.py` (thêm), `tests/test_doi_thu_bang.py` (thêm).

```sql
-- 063 — Tin hiện trường `@` (đặc tả §6).
CREATE TABLE app.tiep_xuc_nhac (
    id           bigserial PRIMARY KEY,
    tiep_xuc_id  bigint NOT NULL REFERENCES app.nhat_ky_tiep_xuc(id),
    loai         text   NOT NULL CHECK (loai IN ('doi_thu', 'nhom')),
    khoa         text   NOT NULL,            -- doi_thu: app.doi_thu.ma · nhom: 'ma:<mã>' | 'n:<id>'
    vi_tri_dau   int    NOT NULL CHECK (vi_tri_dau >= 0),
    do_dai       int    NOT NULL CHECK (do_dai > 0)
);
CREATE INDEX tiep_xuc_nhac_khoa ON app.tiep_xuc_nhac (loai, khoa);
CREATE INDEX tiep_xuc_nhac_tx ON app.tiep_xuc_nhac (tiep_xuc_id);
REVOKE UPDATE, DELETE ON app.tiep_xuc_nhac FROM kome_app;
ALTER TABLE app.gia_doi_thu_tay ADD COLUMN nhom_khoa text;   -- giá khách kể: nhóm mà thẻ @hàng trỏ tới
```
Rồi `CREATE OR REPLACE VIEW mart.gia_doi_thu_quan_sat` = thân 060 với hai thay đổi, KHÔNG đổi danh sách/thứ tự cột ra:
(a) nhánh `tay` mang thêm `t.nhom_khoa` (và nhánh `nap` mang `NULL::text` cùng vị trí) — thêm như cột CUỐI của `nap`/`tay`
để `tat`/`ghep` có `nhom_ke`; (b) biểu thức `nhom_khoa` cuối cùng: `coalesce(x.nhom_ke, <CASE hiện có>)`, và `ten_nhom` cho
`nhom_ke` lấy tên nhóm có tên (`n:`) hoặc tên hàng KOME (`ma:`). Kiểm: `mart.gia_doi_thu_hien_hanh` / `so_sanh_nhom` vẫn tạo
lại được (chúng đọc `SELECT *`/cột theo tên) — nếu Postgres đòi, `CREATE OR REPLACE` lại hai view đó với thân y hệt 062/060.
Chú thích đầu file; `python scripts/sinh_tai_lieu.py`, `python scripts/sinh_cot_dung.py`.

Tests (viết trước): bảng mới chỉ-thêm cho kome_app; `test_khong_bang_nao_bat_RLS` vẫn xanh; một dòng `gia_doi_thu_tay`
`loai_nguon='khach_ke'`, `nhom_khoa='ma:NT01'` → `gia_doi_thu_quan_sat.nhom_khoa = 'ma:NT01'`; nó KHÔNG vào `so_sanh_nhom`
(trung vị), CÓ trong `gia_doi_thu_hien_hanh` với cờ `bat_thuong` khi lệch > 2× trung vị nhóm ≥ 3 bên; hai tin khách kể cùng
(bên, nhóm) → chỉ tin mới nhất `hien_hanh` (phân vùng hiện có theo `ma_doi_thu, ma_hang_dt` — nên `ma_hang_dt` của tin khách
kể phải là `'ke:' || khách || ':' || nhom_khoa` để tin của hai khách khác nhau KHÔNG đè nhau; khẳng định bằng test).

### Task 2: Máy chủ — ghi kèm thẻ, các khối đọc

**Files:** Modify `kome/lien_he.py`, `kome/doi_thu.py`, `kome/web/api.py`; Test `tests/test_lien_he.py`, `tests/test_doi_thu.py`, `tests/test_doi_thu_api.py`.

- `lien_he.ghi(...)` thêm `RETURNING id` và TRẢ id (người gọi cũ bỏ qua giá trị trả — giữ tương thích).
- Mới `lien_he.ghi_kem_nhac(conn, ma, nguoi_id, kieu, ket_qua, noi_dung, hen_lai, nhac: list[dict], gia: list[dict]) -> dict`:
  gọi `ghi` → id; kiểm từng thẻ: `noi_dung[vi_tri_dau]` phải là `'@'`, đoạn nằm trong câu, `loai`/`khoa` tồn tại
  (`app.doi_thu.ma`; nhóm: `ma:` phải là mã trong `core.dim_product`, `n:` phải là `app.nhom_so_sanh.id`) — sai → `LoiNhap`;
  chèn `app.tiep_xuc_nhac`; với mỗi `gia` `{ma_doi_thu, nhom_khoa, gia_goc, don_vi_gia}`: gọi hàm mới
  `doi_thu.gia_khach_ke(conn, ma_doi_thu, nhom_khoa, customer_code, tiep_xuc_id, gia_goc, don_vi_gia, nguoi)` (chèn
  `app.gia_doi_thu_tay` với `loai_nguon='khach_ke'`, `ma_hang_dt='ke:<khách>:<nhom_khoa>'`, `ten_goc` = tên nhóm,
  `kg_moi_don_vi_gia` = 1 nếu đơn vị `kg`, NULL nếu khác; thuế/ship `khong_ro`; + một dòng `doi_thu_nhat_ky` `'gia_moi'`).
  Giá phải có đối thủ + nhóm cùng nằm trong `nhac` của chính lần ghi này. Trả `{"id", "canh_bao": [...]}`: với mỗi giá vừa
  ghi, đọc `mart.gia_doi_thu_hien_hanh` theo id — `bat_thuong` → câu "Giá ¥X/<đv> lệch xa trung vị ¥Y của nhóm — kiểm lại
  đơn vị?" (MỘT lượt hỏi cho mọi giá). Không commit.
- `POST /api/khach-hang/{ma}/tiep-xuc` nhận thêm `nhac` / `gia` (mảng, tuỳ chọn; không có → như cũ) và trả `canh_bao`.
  Form POST cũ `POST /khach-hang/{ma}/tiep-xuc` giữ nguyên.
- Mới `doi_thu.goi_y_nhac(conn) -> {"doi_thu": [{ma, ten}], "hang": [{khoa, ten, loai: 'nhom'|'ma'}]}` — 1 lượt: đối thủ
  `dang_theo_doi`; nhóm có tên + mã KOME hàng thật (`mart.khong_phai_hang` như `nhom_va_quy_cach`). `GET /api/doi-thu/goi-y-nhac`.
- Mới `doi_thu.khach_doi_thu(conn, ma_khach) -> dict` — 1 lượt: tin 90 ngày của khách (đối thủ, nhóm + tên, giá, đơn vị, ngày,
  người ghi, câu gốc) + `ly_do_ngung`: các cặp `mart.khach_mat_hang` `trang_thai_cap = 'ngung'` của khách mà mã thuộc một
  nhóm được nhắc trong 90 ngày (mã → nhóm: `n:` qua `app.nhom_so_sanh_ma`, còn lại `ma:<mã>`) — dùng
  `mart.khach_mat_hang_cua(ARRAY[...])`? KHÔNG: đọc view lọc `customer_code = %s` (đã nhanh, đo ~10 ms). `GET /api/khach-hang/{ma}/doi-thu`.
- `ho_so_ben`: thêm `khach_dang_mua` (tin 90 ngày nhắc bên này: khách mã + tên hiện hành, nhóm, giá, ngày) TRONG câu sẵn có (vẫn 1 lượt).
- `tong_quan`: thêm `hien_truong` (30 ngày: số tin theo đối thủ, theo nhóm, theo tỉnh của khách — `core.dim_customer.prefecture`
  hiện hành) TRONG câu sẵn có.
- Mốc: "90/30 ngày" tính theo `hom_nay_o_nhat()` (đồng hồ thật — tin hiện trường là sự kiện ngoài đời, cùng lý lẽ ngoại lệ
  thứ hai của bất biến mốc: xem `/lien-he`), ghi rõ trong docstring.
- Tests: ghi kèm thẻ + giá trong MỘT giao dịch (lỗi ở thẻ → không có dòng tiếp xúc nào); thẻ lệch vị trí `@` → 400; giá không
  có thẻ tương ứng → 400; `canh_bao` khi giá lệch; `goi_y_nhac`, `khach_doi_thu` đúng 1 lượt; `ho_so()` vẫn ≤ 8; ngân sách
  lượt hỏi GET mới ≤ 2; `ly_do_ngung` ra đúng cặp đã ngừng mua cùng nhóm; `ho_so_ben.khach_dang_mua`; `tong_quan.hien_truong`.

### Task 3: Giao diện

**Files:** Modify `giao_dien/src/khach/GhiTiepXuc.tsx` (+ file logic thuần mới `giao_dien/src/khach/nhac.ts` + `nhac.test.ts`),
`giao_dien/src/khach/HoSoViec.tsx` hoặc `HoSoTab.tsx` (khối "Đang mua của đối thủ"), `giao_dien/src/doi_thu/TabHoSo.tsx`,
`TabTongQuan.tsx`, `TabSoSanh.tsx`, `kieu.ts`.

- `nhac.ts` (thuần, có test): tìm từ đang gõ sau `@` tại con trỏ; lọc gợi ý không dấu; chèn thẻ `@<nhãn>` và trả vị trí;
  sau mỗi lần sửa câu, dò lại vị trí từng thẻ (thẻ mất chữ thì bỏ); ghép cặp giá: mỗi thẻ hàng → đối thủ gần nhất đứng TRƯỚC nó.
- `GhiTiepXuc`: gõ `@` mở danh sách gợi ý (đối thủ trước, rồi hàng; ↑↓ Enter chọn, Esc đóng, chuột bấm được; `role="listbox"`,
  `aria-activedescendant`); dưới ô chữ, mỗi thẻ hàng một dòng nhỏ tuỳ chọn: "@<hàng> · đối thủ [chọn, điền sẵn theo ghép cặp]
  · giá [__] ¥ / [kg|gói|thùng]". Gửi `nhac` + `gia` (chỉ dòng có giá). Hiện `canh_bao` trả về (không chặn). Không có `@` →
  hành vi y như cũ. Dùng chung ở hồ sơ 360 và `/lien-he` (không sửa chỗ gọi, trừ khi cần truyền danh sách gợi ý).
- Hồ sơ khách: khối "Đang mua của đối thủ" (từ `/api/khach-hang/{ma}/doi-thu`): nhãn "đang mua @THAK: Basa (¥…/kg, 12/9)";
  nếu có `ly_do_ngung`: "Đã ngừng mua <mã> — tin 12/9: đang lấy của THAK". Ẩn khối khi rỗng.
- Hồ sơ đối thủ: bảng "Khách đang mua của bên này" (liên kết `/khach-hang/{mã}` qua giuKhoang).
- Tổng quan thị trường: khối "Hiện trường 30 ngày" (top đối thủ, top nhóm, theo tỉnh — danh sách/bảng, không bản đồ mới).
- So sánh giá: trong dòng chi tiết, quan sát `loai_nguon = 'khach_ke'` có nhãn "khách kể"; trên dòng nhóm thêm "khách kể:
  n tin" khi có (đếm/sắp là diễn đạt, không phải chỉ số mới).
- Kiểm: vitest (nhac.test.ts viết trước), `npm run build`, pytest API/build; controller xem trình duyệt.

### Task 4: Tài liệu + toàn bộ test
CLAUDE.md: một đoạn bất biến 063 (thẻ chỉ-thêm, câu gốc không đổi, giá khách kể qua ô, `ma_hang_dt` `ke:`, 90/30 ngày theo
đồng hồ thật); đặc tả §6 thêm ghi chú "đề xuất gắn thẻ bị quên → sau Đợt 2 (chưa làm)"; `pytest -q` + `vitest` toàn bộ.
