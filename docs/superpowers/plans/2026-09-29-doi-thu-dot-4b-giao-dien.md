# Đợt 4b + 4c — giao diện mới `/doi-thu` — kế hoạch thực hiện

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng lại màn `/doi-thu` theo bản vẽ phác đã duyệt:
- 5 tab: Tóm tắt · So sánh giá · Đối thủ · Tin thị trường · Phí & giao hàng;
- menu Dữ liệu ▾;
- biểu đồ nhiều hình;
- sửa ở mọi chỗ bằng pop-up, có lịch sử sửa và chống sửa đè.

Đợt này làm trên dữ liệu của đợt 4a.

**Architecture:**
- Máy chủ (`kome/doi_thu.py`, `kome/doi_thu_giao.py`, `kome/web/api.py`) thêm cột / endpoint đọc (mỗi GET 1 lượt hỏi) và endpoint ghi (POST chỉ JSON, 409 khi xung đột).
- Trình duyệt (`giao_dien/src/doi_thu/`):
  - logic thuần trong các file `*_logic.ts` / `mau.ts` / `nganh.ts`, có vitest;
  - thành phần React vẽ SVG tự làm, không thư viện biểu đồ;
  - ô nổi dùng `chung/ONoi.tsx`;
  - pop-up dùng MỘT thành phần hộp thoại chung.
- Chỉ số vẫn ở `mart`: máy chủ trả `gia_1/5/10/pallet`, giá KOME chuẩn / bảng / KM, `lech_trung_vi`, `gia_kome_lech`. Trình duyệt chỉ CHỌN cột, lọc, xếp và vẽ. Riêng phí đơn mẫu dùng `phi_giao.ts` (bản chép bắt buộc đã có).

**Tech Stack:** FastAPI, psycopg 3, Postgres 17; React 18 + TypeScript + TanStack Query + Vite; vitest; pytest.

**Spec:** `docs/superpowers/specs/2026-09-29-doi-thu-giao-dien-moi-design.md` (§1–§4, §5.5, §7, §9). Bản vẽ phác đã duyệt nằm ở `.superpowers/brainstorm/277-1790676676/content/`, trên đĩa, git-ignored. Đây là NGUỒN HÌNH để chép bố cục, màu, kích thước; mã JS trong đó chỉ để tham khảo, không chép nguyên. Các file:
- `ca-trang-8.html`: cả trang, bản cuối, có tab Phí & giao hàng;
- `popup-sua.html`: pop-up sửa;
- `goi-thung-3.html`: cột gói / thùng;
- `tooltip-thung-4.html`: ô nổi bảng giá;
- `ky-hieu-thay-the.html`: phương án C = màu, đã chọn.

## Global Constraints

- **Luật màu** (§3.1): **đỏ = bất lợi cho KOME** (đối thủ rẻ hơn KOME), **xanh lá = KOME có lợi**, xám = ±5%. `p` = % giá đối thủ so với giá KOME đang chọn. Định nghĩa MỘT lần: `doi_thu/mau.ts::mauLech(p)`.
- **Thương hiệu** (§3.2):
  - cùng thương hiệu = thanh xanh lam `var(--lam-chu)` / `#4a7fb5`; khác thương hiệu = thanh xám tối, tên mờ;
  - nhãn chữ "cùng thương hiệu" / "khác thương hiệu" ↔ mã CSDL `cung_hang` / `thay_the` (mã KHÔNG đổi);
  - một chỗ: `kieu.ts::NHAN_GHEP`;
  - không in chữ nhãn dưới tên.
- **Thiếu dữ liệu** là "?" màu cam, bấm được (mở pop-up, con trỏ nằm sẵn ở ô đó). Không bao giờ in 0 hay để trống thay cho chưa biết.
- **Thuế không rõ** là dấu "?" vàng cuối thanh. **Gồm ship** là 🚚. **Giá cũ** (`tuoi_ngay > 60`, `mau.ts::NGAY_CU`) thì thanh mờ.
- **Ít chữ**: không câu kết luận nào. Câu định nghĩa vào ⓘ của `Khoi`.
- **Sửa ở mọi chỗ**: mọi chỗ hiện một mặt hàng / điều kiện / bên đối thủ đều bấm được, mở pop-up. Có lịch sử sửa. Chống sửa đè bằng 409 và hỏi "Ghi đè / Giữ bản kia".
- **Tên ngành tiếng Việt** chỉ để hiển thị: `doi_thu/nganh.ts::tenNganh`. Bộ lọc vẫn gửi tên OBC.
- **Số theo chuẩn Nhật**: `dinh_dang.ts` (`yen`, `so`, …). Không tự `toFixed().replace(...)`.
- **URL**: `?tab=tom_tat|so_sanh|ben|tin|giao_hang|duyet|nhom|lech` (`tong_quan` cũ → `tom_tat`), cộng `sp`, `sl`, `xem`, `gk`, `cung`, `ben`, `nganh`. Mọi `replaceState` đi qua `giuKhoang()`.
- **API**: mỗi GET đúng 1 lượt hỏi + phiên bản (`tests/test_doi_thu_api.py` có trần 2). POST chỉ nhận JSON. Thân không phải object → 400. `LoiNhap` → 400. Xung đột → **409** `{loi, xung_dot: {ai, luc, sau}}`.
- **Ghi**: sổ sửa CHỈ THÊM, `app.doi_thu_nhat_ky` ghi trong CÙNG giao dịch. Khoá nhật ký (`doi_tuong`) dùng ĐÚNG chuỗi hiện có: `gia:<fact_id>` (dòng nạp), `tay:<id>` (dòng tay), `<ma_doi_thu>/<ma_hang_dt>` (ghép), `giao:<bên>`, `dk:<fact_id>` / `dk:tay:<bên>`. Thêm `ben:<mã>` cho sửa thông tin bên.
- Sửa `giao_dien/` → `cd giao_dien && npm run build`, commit `kome/web/spa/`. Sửa migration / `files.yml` → `python scripts/sinh_tai_lieu.py && python scripts/sinh_cot_dung.py`.
- Migration 067 CHƯA chạy trên CSDL thật, sửa tại chỗ được. 059–066 và 068 cũng chưa chạy thật, nhưng chỉ đụng tới khi task ghi rõ.
- Test: pytest trên CSDL test nội bộ (không bao giờ CSDL thật). vitest: `cd giao_dien && npx vitest run`. Commit kết thúc `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Ngân sách: đây là màn máy tính. Điện thoại chỉ cần xem được (≥ 375 px không tràn ngang toàn trang; biểu đồ được phép cuộn ngang trong khung của nó).

---

## Bản đồ file

| File | Việc |
|---|---|
| `db/migrations/067_mart_quan_sat_gia_bac.sql` (sửa tại chỗ) | `so_sanh_nhom` thêm cột cuối `gia_kome_so`, `lech_trung_vi`, `gia_kome_lech`, `kome_kg_goi`, `kome_goi_thung`, `kome_kg_thung` |
| `kome/doi_thu.py` | `_COT_QS` thêm cột 067 + `sua_cuoi`; `so_sanh` / `tong_quan` / `ho_so_ben` thêm khoá; hàm đọc `mat_hang`, `lich_su`; hàm ghi `sua_ben`, `sua_tay`, `sua_mat_hang`, `XungDot`, `kiem_xung_dot` |
| `kome/doi_thu_giao.py` | `giao_hang(conn)` (đọc); `da_xem` / `ghi_de` cho `sua_giao_hang`, `sua_dieu_kien` |
| `kome/web/api.py` | GET `/doi-thu/mat-hang/{nguon}/{id}`, `/doi-thu/lich-su`, `/doi-thu/giao-hang`; POST `/doi-thu/sua-mat-hang`, `/doi-thu/giao-hang`, `/doi-thu/dieu-kien`, `/doi-thu/ben`; `_dt_ghi` đổi `XungDot` → 409 |
| `giao_dien/src/api.ts` | `LoiApi.du_lieu` (thân JSON của lỗi) |
| `giao_dien/src/doi_thu/kieu.ts` | kiểu mới, `NHAN_GHEP` |
| `giao_dien/src/doi_thu/mau.ts` (+test) | `mauLech`, `NGAY_CU`, `LECH_NGANG` |
| `giao_dien/src/doi_thu/nganh.ts` (+test) | `tenNganh` |
| `giao_dien/src/doi_thu/url.ts` (+test) | đọc / ghi trạng thái trên URL |
| `giao_dien/src/doi_thu/HopThoai.tsx` | hộp thoại chung (nền mờ, Esc, bấm nền, bẫy focus) |
| `giao_dien/src/doi_thu/SuaMatHang.tsx`, `sua_logic.ts` (+test) | pop-up sửa mặt hàng; form → payload |
| `giao_dien/src/doi_thu/SuaNho.tsx` | pop-up điều kiện bán / thông tin bên / điều kiện giao hàng |
| `giao_dien/src/doi_thu/so_sanh_logic.ts` (+test) | chọn giá theo số lượng / giá KOME, dựng dòng, thu gọn, ô nhiệt, đếm ô trống |
| `giao_dien/src/doi_thu/TabSoSanh.tsx` (viết lại), `BieuDoCot.tsx`, `BieuDoCham.tsx`, `BangNhiet.tsx`, `ONoiGia.tsx` | tab So sánh |
| `giao_dien/src/doi_thu/TabTomTat.tsx`, `tom_tat_logic.ts` (+test) | tab Tóm tắt (thay `TabTongQuan.tsx`) |
| `giao_dien/src/doi_thu/TabHoSo.tsx` (viết lại) | tab Đối thủ |
| `giao_dien/src/doi_thu/TabTin.tsx` | tab Tin thị trường |
| `giao_dien/src/doi_thu/TabGiaoHang.tsx` | tab Phí & giao hàng |
| `giao_dien/src/doi_thu/TabGiaKomeLech.tsx` | Dữ liệu › Giá KOME lệch |
| `giao_dien/src/doi_thu/TabDuyet.tsx` | dùng pop-up chung thay khung sửa hai cột |
| `giao_dien/src/doi_thu/ManDoiThu.tsx`, `doi_thu.css` | thanh tab + menu Dữ liệu |
| `tests/test_doi_thu.py`, `tests/test_doi_thu_api.py`, `tests/test_doi_thu_giao.py`, `tests/test_mart_doi_thu.py` | test máy chủ |
| `CLAUDE.md` | dòng `/doi-thu` của bảng trang + bất biến màn mới |

---

### Task 1: Máy chủ — dữ liệu đọc cho màn mới

**Files:** `db/migrations/067_mart_quan_sat_gia_bac.sql` (sửa tại chỗ), `kome/doi_thu.py`, `kome/doi_thu_giao.py`, `kome/web/api.py`, test ở `tests/test_mart_doi_thu.py`, `tests/test_doi_thu.py`, `tests/test_doi_thu_api.py`, `tests/test_doi_thu_giao.py`.

**Interfaces (Produces) — JSON mà các task giao diện dựa vào:**
- Mỗi phần tử `quan_sat` (trong `/so-sanh`, `/ben/{ma}`, `/duyet`, `/mat-hang`) thêm:
  - `so_goi_thung`, `kl_goi_g`, `bac` (mảng | null), `kg_thung_dt`;
  - `gia_goi`, `gia_thung`, `gia_1`, `gia_5`, `gia_10`, `gia_pallet`: làm tròn `round()`, ¥/kg chưa thuế, có thể null;
  - `sua_cuoi` (int, 0 khi chưa sửa) = `max(app.doi_thu_nhat_ky.id)` trên các khoá của chính quan sát: `gia:<id>` (nap) hoặc `tay:<id>` (tay), và `<ma_doi_thu>/<ma_hang_dt>`.
- Mỗi nhóm của `/so-sanh` thêm:
  - `gia_kome_chuan`, `gia_kome_bang` (object bậc → ¥/kg), `gia_kome_km`;
  - `gia_kome_so` (= `coalesce(chuan, thực)`, giá KOME dùng để so), `lech_trung_vi` (số thực, `gia_kome_so / trung_vi − 1`), `gia_kome_lech` (bool, > 3× hoặc < ⅓ trung vị);
  - `kome_kg_goi`, `kome_goi_thung`, `kome_kg_thung` (quy cách của mã KOME chính — `mart.quy_cach_kome` của mã bán nhiều kg nhất, cùng mã `chinh` của 067).
- `/tong-quan`:
  - `khuyen_mai[]` và `het_hang[]` thêm `nguon`, `id`, `ma_hang_dt`, `ma_doi_thu` (`ben` giữ);
  - `het_hang[]` thêm `ten_doi_thu`;
  - `dieu_kien[]` đọc `mart.dieu_kien_hien_hanh`, thêm `id`, `fact_id`, `them_tay`.
- `/ben/{ma}`:
  - `dieu_kien[]` đọc `mart.dieu_kien_hien_hanh`, thêm `id`, `fact_id`, `them_tay`;
  - `quan_sat[]` thêm `gia_kome_so` (giá KOME để so của nhóm quan sát đó, null nếu không có);
  - `giao_hang` (dòng `mart.giao_hang_hien_hanh` của bên, hoặc null) và `sua_cuoi_ben` (`max` nhật ký `ben:<mã>`).
- GET `/api/doi-thu/mat-hang/{nguon}/{id}` → `{"quan_sat": <như trên>, "lich_su": [{"id", "loai", "ai", "luc", "truoc", "sau"}]}` (lịch sử mới nhất trước, tối đa 50; `ai` = tên người dùng hoặc null). 404 JSON khi không có. 1 lượt hỏi.
- GET `/api/doi-thu/lich-su?doi_tuong=a,b` (≤ 5 khoá) → `{"lich_su": [...]}` cùng hình dạng. 1 lượt, không ảnh chụp.
- GET `/api/doi-thu/giao-hang` → `{"dong": [<mart.giao_hang_hien_hanh + "sua_cuoi">...], "bang_chung": <mart.giao_hang_kome_bang_chung>}`. KOME đứng đầu. 1 lượt.

- [ ] **Step 1: Test hỏng.** Viết:
  - (a) `tests/test_mart_doi_thu.py`: `so_sanh_nhom` có sáu cột mới, đúng giá trị trên một nhóm có 標準価格:
    - `gia_kome_so` = chuẩn;
    - `lech_trung_vi` = so / trung vị − 1;
    - `gia_kome_lech` true khi KOME > 3× trung vị;
    - `kome_kg_thung` = `kg_02` của mã chính.
  - (b) `tests/test_doi_thu.py`: `so_sanh()` mang các khoá mới của nhóm và `quan_sat`. `sua_cuoi` = 0 trước khi sửa, bằng id nhật ký sau `DT.sua` (khoá `gia:<id>`) và sau `DT.dat_ghep` (khoá `<bên>/<hàng>`).
  - (c) `tong_quan()` mang `nguon`/`id`/`ma_hang_dt` trong `khuyen_mai` / `het_hang`. `dieu_kien` bỏ loại `ghi_chu_doc` và áp đính chính (dùng `DTG.sua_dieu_kien`).
  - (d) `ho_so_ben()` mang `giao_hang`, `sua_cuoi_ben`, `dieu_kien[].id`, `quan_sat[].gia_kome_so`.
  - (e) `tests/test_doi_thu_api.py`: `/mat-hang/nap/<id>` 200 kèm `lich_su`; `/mat-hang/nap/999999` 404; `/lich-su?doi_tuong=` quá 5 khoá → 400; `/giao-hang` KOME đứng đầu. Thêm ba URL mới vào bộ `parametrize` trần 2 lượt.
- [ ] **Step 2: 067 (sửa tại chỗ).** Ở câu SELECT cuối của `mart.so_sanh_nhom`, thêm vào CUỐI (sau `gia_kome_km`):
  ```sql
       CASE WHEN h.don_vi_so = 'kg' THEN coalesce(k.gia_kome_chuan, k.gia_kome) END                         AS gia_kome_so,
       CASE WHEN h.don_vi_so = 'kg' AND coalesce(k.gia_kome_chuan, k.gia_kome) > 0 AND percentile_cont(0.5) WITHIN GROUP (ORDER BY h.yen_chuan) > 0
            THEN coalesce(k.gia_kome_chuan, k.gia_kome) / percentile_cont(0.5) WITHIN GROUP (ORDER BY h.yen_chuan) - 1 END AS lech_trung_vi,
       CASE WHEN h.don_vi_so = 'kg' AND coalesce(k.gia_kome_chuan, k.gia_kome) > 0 AND percentile_cont(0.5) WITHIN GROUP (ORDER BY h.yen_chuan) > 0
            THEN coalesce(k.gia_kome_chuan, k.gia_kome) > 3 * percentile_cont(0.5) WITHIN GROUP (ORDER BY h.yen_chuan)
              OR coalesce(k.gia_kome_chuan, k.gia_kome) < percentile_cont(0.5) WITHIN GROUP (ORDER BY h.yen_chuan) / 3
            ELSE false END                                                                                    AS gia_kome_lech,
       q.kg_moi_goi AS kome_kg_goi, q.goi_moi_thung AS kome_goi_thung, q.kg_02 AS kome_kg_thung
  ```
  `LEFT JOIN chinh c USING (nhom_khoa) LEFT JOIN mart.quy_cach_kome q ON q.product_code = c.product_code`, và thêm `q.kg_moi_goi, q.goi_moi_thung, q.kg_02` vào `GROUP BY`. Nếu đọc `percentile_cont` lặp lại khó đọc, gói trung vị vào một CTE / subquery cùng kết quả. Ghi chú đầu 067 thêm một dòng về sáu cột mới. **`mart.gia_kome_lech` là định nghĩa MỘT lần** của "giá KOME lệch" (Tóm tắt không vẽ, Dữ liệu › Giá KOME lệch liệt kê). Giao diện không tự tính lại.
- [ ] **Step 3: `kome/doi_thu.py`.**
  - `_COT_QS` thêm `so_goi_thung, kl_goi_g, bac, kg_thung_dt, round(gia_goi) AS gia_goi, round(gia_thung) AS gia_thung, round(gia_1) AS gia_1, round(gia_5) AS gia_5, round(gia_10) AS gia_10, round(gia_pallet) AS gia_pallet`, và
    ```sql
    coalesce((SELECT max(nk.id) FROM app.doi_thu_nhat_ky nk
              WHERE nk.doi_tuong IN (CASE nguon WHEN 'nap' THEN 'gia:' ELSE 'tay:' END || id, ma_doi_thu || '/' || ma_hang_dt)), 0) AS sua_cuoi
    ```
    Nếu `_COT_QS` được dùng trong ngữ cảnh có bí danh bảng, viết đủ tên cột theo bí danh, và giữ `_HO_SO` (dùng `.replace(', bat_thuong', '')`) còn đúng. Thêm chỉ mục `app.doi_thu_nhat_ky (doi_tuong, id DESC)` bằng migration MỚI `069_doi_thu_nhat_ky_chi_muc.sql` (bảng có thể lớn dần; 2 lượt hỏi không đổi).
  - `_SO_SANH` thêm các khoá nhóm mới (`round()` cho giá; `lech_trung_vi` giữ số thực; `gia_kome_bang` nguyên jsonb).
  - `_TONG_QUAN`:
    - `khuyen_mai` và `het_hang` thêm `'nguon', nguon, 'id', id, 'ma_hang_dt', ma_hang_dt, 'ma_doi_thu', ma_doi_thu`, và `het_hang` thêm `'ten_doi_thu', ten_doi_thu`;
    - `dieu_kien` thay nguồn bằng `SELECT id, fact_id, ma_doi_thu, loai, noi_dung, ngay_nguon, them_tay FROM mart.dieu_kien_hien_hanh WHERE loai <> 'khac'`, giữ khoá `ben`/`loai`/`noi_dung`/`ngay`, thêm `id`/`fact_id`/`them_tay`;
    - bỏ CTE `dk0`/`dk` cũ.
  - `_HO_SO`:
    - `dieu_kien` từ `mart.dieu_kien_hien_hanh` (cùng khoá);
    - `quan_sat` thêm `gia_kome_so` bằng subquery vào `mart.so_sanh_nhom` theo `(nhom_khoa, don_vi_so)`. Đọc view nặng này MỘT lần qua CTE `AS MATERIALIZED` trong câu, KHÔNG mỗi dòng một lần;
    - thêm hai cột kết quả: `giao_hang` (`to_json` dòng `mart.giao_hang_hien_hanh` của bên) và `sua_cuoi_ben`. `ho_so_ben()` trả thêm hai khoá đó.
  - Hàm mới:
    ```python
    _LICH_SU = """SELECT coalesce(json_agg(json_build_object('id', nk.id, 'loai', nk.loai, 'doi_tuong', nk.doi_tuong,
                    'ai', coalesce(nd.ten_hien_thi, nd.ten_dang_nhap), 'luc', nk.luc, 'truoc', nk.truoc, 'sau', nk.sau)
                    ORDER BY nk.id DESC), '[]')
                  FROM (SELECT * FROM app.doi_thu_nhat_ky WHERE doi_tuong = ANY(%(khoa)s) ORDER BY id DESC LIMIT 50) nk
                  LEFT JOIN app.nguoi_dung nd ON nd.id = nk.nguoi_dung_id"""
    ```
    Tên cột thật của `app.nguoi_dung` phải kiểm (`grep -n "CREATE TABLE app.nguoi_dung" -A15 db/migrations/019_danh_tinh.sql`). Dùng cột tên hiển thị có thật, không có thì `ten_dang_nhap`.
    - `lich_su(conn, khoa: list[str]) -> list` (≤ 5 khoá, mỗi khoá ≤ 300 ký tự; sai → `LoiNhap`).
    - `mat_hang(conn, nguon: str, id: int) -> dict | None`: một câu, trả `{"quan_sat": ..., "lich_su": ...}`. `quan_sat` đọc `mart.gia_doi_thu_quan_sat` (KHÔNG chỉ hiện hành: sửa được cả dòng lịch sử), `LEFT JOIN mart.nguon_quan_sat`, cùng `_COT_QS` trừ `bat_thuong`, cộng `bat_thuong` lấy từ `mart.gia_doi_thu_hien_hanh` khi dòng là hiện hành. `lich_su` theo khoá của chính dòng. `nguon ∉ {'nap', 'tay'}` → `LoiNhap`.
  - `kome/doi_thu_giao.py` thêm `giao_hang(conn) -> dict`: một câu, `dong` = `mart.giao_hang_hien_hanh` `ORDER BY thu_tu, ma_doi_thu` kèm `sua_cuoi` (`max` nhật ký `giao:<ma>`), `bang_chung` = dòng duy nhất của `mart.giao_hang_kome_bang_chung`.
- [ ] **Step 4: Route** trong `kome/web/api.py`, cạnh các route `/doi-thu/*`, cùng nếp `_dt_doc` / `_chup`:
  - `GET /doi-thu/mat-hang/{nguon}/{id}` và `GET /doi-thu/lich-su`: KHÔNG ảnh chụp (đọc tươi để chống sửa đè). Mở `open_app_conn()`, đặt mốc như `_dt_doc` (`_voi_moc`) nếu route khác làm vậy. 404 JSON `{"loi": "Không có mặt hàng này."}`.
  - `GET /doi-thu/giao-hang` qua `_dt_doc` (ảnh chụp theo phiên bản; nhật ký có trong `_PHIEN_BAN`).
- [ ] **Step 5: Chạy** `pytest tests/test_mart_doi_thu.py tests/test_doi_thu.py tests/test_doi_thu_api.py tests/test_doi_thu_giao.py -q`, rồi cả bộ một lần. Sinh lại tài liệu sống (067 và 069 đổi). Commit.

---

### Task 2: Máy chủ — ghi từ pop-up (một giao dịch, chống sửa đè)

**Files:** `kome/doi_thu.py`, `kome/doi_thu_giao.py`, `kome/web/api.py`, test ở `tests/test_doi_thu.py`, `tests/test_doi_thu_giao.py`, `tests/test_doi_thu_api.py`.

**Interfaces:**
- `class XungDot(Exception)`: thuộc tính `ai: str | None`, `luc: str` (ISO), `sau: dict | None`.
- `kiem_xung_dot(conn, khoa: list[str], da_xem: int, ghi_de: bool) -> None`:
  - chạy `SELECT … FROM app.doi_thu_nhat_ky WHERE doi_tuong = ANY(khoa) AND id > da_xem ORDER BY id DESC LIMIT 1` kèm tên người;
  - có dòng và `not ghi_de` → `raise XungDot(...)`.
  - Gọi ĐẦU mỗi hàm ghi bên dưới, trong cùng giao dịch. Khoá hàng bằng `SELECT … FOR UPDATE` không có nghĩa với sổ chỉ thêm; nếu hai người bấm cùng lúc thì chấp nhận lần sau thắng, cả hai đều được ghi nhật ký.
- `sua_ben(conn, ma: str, du_lieu: {ten?, web?, ghi_chu?}, nguoi, da_xem=0, ghi_de=False) -> None`:
  - UPDATE `app.doi_thu`;
  - `ten` 1–80 ký tự (bắt buộc nếu có mặt); `web` qua `kiem_lien_ket` (https, cho phép `""` = xoá); `ghi_chu` ≤ 300;
  - nhật ký `loai 'doi_thu'`, khoá `ben:<ma>`, `truoc` / `sau`.
- `sua_tay(conn, tay_id: int, thay_doi: dict, nguoi) -> int`:
  - sửa một dòng `tay` = thêm dòng `app.gia_doi_thu_tay` MỚI, chép dòng cũ rồi áp `thay_doi` (các trường `TRUONG_SUA`, kiểm bằng `_kiem`), cùng `ma_doi_thu` / `ma_hang_dt` / `loai_nguon` / `nhom_khoa` / `customer_code` / `tiep_xuc_id` / `lien_ket_bang_chung`;
  - dòng mới thành hiện hành vì mới hơn;
  - nhật ký `loai 'sua'`, khoá `tay:<id cũ>` VÀ `tay:<id mới>` (hai dòng, để `sua_cuoi` của cả hai khớp);
  - trả id mới.
- `sua_mat_hang(conn, b: dict, nguoi) -> dict`, với `b`:
  ```json
  {"nguon": "nap"|"tay", "id": 123, "da_xem": 0, "ghi_de": false,
   "nhan": "cung_hang"|"thay_the"|"khong"|null,
   "thay_doi": {"<truong TRUONG_SUA>": "...", ...},
   "vi_sao_gia": "doc_sai"|"da_doi"|null, "loai_nguon": "...", "lien_ket_bang_chung": "...", "ghi_chu_nguon": "..."}
  ```
  1. Đọc dòng từ `mart.gia_doi_thu_quan_sat` (`ma_doi_thu`, `ma_hang_dt`, `ma_kome`, `nhom_khoa`, …). Không có → `LoiNhap`.
  2. `kiem_xung_dot(conn, [khoa dòng, "<bên>/<hàng>"], da_xem, ghi_de)`.
  3. `nhan` khác nhãn hiện tại → `dat_ghep(conn, bên, hàng, product_code = ma_kome hiện hành, nhom_id = nhóm hiện hành nếu `n:`, nhan, nguoi)`. `"khong"` = bỏ khỏi nhóm.
  4. `TRUONG_GIA = {"gia_goc", "don_vi_gia", "thue", "bac"}`. Nếu `thay_doi` có trường giá mà `vi_sao_gia` rỗng → `LoiNhap("Chọn vì sao đổi giá.")`.
  5. `vi_sao_gia == "da_doi"` → `gia_moi(conn, {fact_goc_id: id (nap) …, **thay_doi, loai_nguon, lien_ket_bang_chung, ghi_chu_nguon}, nguoi)`. Với dòng tay, dùng `sua_tay` rồi ghi `loai_nguon` mới. `loai_nguon` bắt buộc (`gia_moi` đã kiểm).
  6. Ngược lại: `nap` → `sua(conn, id, thay_doi, nguoi)`; `tay` → `sua_tay(conn, id, thay_doi, nguoi)`.
  7. Trả `{"sua_cuoi": <max nhật ký mới của các khoá>}`.

  Không có gì đổi → `LoiNhap("Không có gì để sửa.")`. Mọi bước chung một giao dịch (`_dt_ghi` commit một lần); lỗi ở bước nào thì không bước nào vào.
- `sua_giao_hang(..., da_xem=0, ghi_de=False)` và `sua_dieu_kien(..., da_xem=0, ghi_de=False)` gọi `kiem_xung_dot` với khoá `giao:<bên>` / `dk:<fact_id>` (dòng thêm tay: `dk:tay:<bên>`). Tham số mới có mặc định, nên lệnh gọi cũ vẫn chạy.
- API:
  - `POST /api/doi-thu/sua-mat-hang` (→ `sua_mat_hang`);
  - `POST /api/doi-thu/giao-hang` (`{ma_doi_thu, thay_doi, da_xem, ghi_de}`);
  - `POST /api/doi-thu/dieu-kien` (`{fact_id|null, ma_doi_thu, loai, noi_dung, bo, da_xem, ghi_de}`);
  - `POST /api/doi-thu/ben` (`{ma, ten?, web?, ghi_chu?, da_xem, ghi_de}`).

  `_dt_ghi` bắt `DT.XungDot` → `JSONResponse({"loi": "Có người vừa sửa mục này.", "xung_dot": {"ai", "luc", "sau"}}, 409)`.

- [ ] **Step 1: Test hỏng** (pytest):
  - nhãn `khong` → dòng ra khỏi nhóm (`mart.gia_doi_thu_quan_sat.nhom_khoa` null);
  - `thay_doi` gồm `so_goi_thung` + `khuyen_mai` → hai dòng `dinh_chinh_gia`, một nhật ký;
  - trường giá không có `vi_sao_gia` → 400;
  - `da_doi` không `loai_nguon` → 400;
  - `da_doi` hợp lệ → dòng `gia_doi_thu_tay` với `fact_goc_id`;
  - sửa dòng tay → dòng tay mới, hai nhật ký;
  - xung đột: `da_xem` cũ → 409 với `ai` / `luc`, và KHÔNG ghi gì; `ghi_de` → ghi;
  - một phần hỏng (`nhan` hợp lệ + `thay_doi` sai) → không phần nào vào;
  - `sua_ben`: web http → 400, `""` xoá web, nhật ký `ben:<ma>`;
  - `giao-hang` / `dieu-kien` 409 tương tự;
  - route: 415 không JSON, 400 thân mảng.
- [ ] **Step 2–4:** cài đặt, chạy test file liên quan, rồi cả bộ. Commit.

---

### Task 3: Giao diện — nền: kiểu, màu, ngành, URL, hộp thoại, thanh tab

**Files:** `giao_dien/src/api.ts`, `doi_thu/kieu.ts`, `doi_thu/mau.ts` (+`.test.ts`), `doi_thu/nganh.ts` (+test), `doi_thu/url.ts` (+test), `doi_thu/HopThoai.tsx`, `doi_thu/ManDoiThu.tsx`, `doi_thu/doi_thu.css`.

**Interfaces:**
```ts
// api.ts
export class LoiApi extends Error { constructor(public ma: number, thong_diep: string, public du_lieu?: unknown) { … } }
// lay() và gui(): khi !r.ok, đọc JSON một lần, gắn cả object vào du_lieu.

// kieu.ts — thêm vào QuanSat:
so_goi_thung: number | null; kl_goi_g: number | null; bac: Bac[] | null; kg_thung_dt: number | null;
gia_goi: number | null; gia_thung: number | null; gia_1: number | null; gia_5: number | null; gia_10: number | null;
gia_pallet: number | null; sua_cuoi: number; gia_kome_so?: number | null;
export type Bac = { tu: number; don_vi_sl: "thung" | "kg" | "goi" | "pallet"; gia: number; don_vi_gia: "thung" | "kg" | "goi" };
// Nhom thêm:
gia_kome_chuan: number | null; gia_kome_bang: Record<string, number> | null; gia_kome_km: number | null;
gia_kome_so: number | null; lech_trung_vi: number | null; gia_kome_lech: boolean;
kome_kg_goi: number | null; kome_goi_thung: number | null; kome_kg_thung: number | null;
export type LichSu = { id: number; loai: string; doi_tuong: string; ai: string | null; luc: string; truoc: unknown; sau: unknown };
export type DieuKien = { id: number; fact_id: number | null; ben: string; loai: string; noi_dung: string; ngay: string; them_tay: boolean };
export type GiaoHang = { ma_doi_thu: string; ten: string | null; bao_ship: boolean | null; phi_ship: number | null;
  phi_ship_theo: "don" | "thung" | "kien" | null; mien_ship_tu: number | null; mien_ship_kien: number | null;
  thung_moi_kien: number | null; phu_phi: Record<string, number | "khong_nhan"> | null; phi_daibiki: number | null;
  daibiki_tu: number | null; daibiki_sau: number | null; ck_mien_daibiki: boolean | null; kien_toi_da_kg: number | null;
  ghep_kien: string | null; thue: "bao" | "chua" | "khong_ro" | null; cach_gui: string | null; nguon_chu: string | null;
  ngay_nguon: string | null; suy: boolean; da_xac_nhan: boolean; sua_cuoi: number };
export const NHAN_GHEP: Record<"cung_hang" | "thay_the", string> = { cung_hang: "cùng thương hiệu", thay_the: "khác thương hiệu" };
// TongQuan.khuyen_mai/het_hang thêm nguon, id, ma_hang_dt, ma_doi_thu (+ ten_doi_thu ở het_hang); dieu_kien: DieuKien[].

// mau.ts
export const LECH_NGANG = 5;                 // ±5% = ngang
export const NGAY_CU = 60;
export type MauLech = "do" | "xanh" | "xam";
export function mauLech(p: number | null | undefined): MauLech   // p = % đối thủ so KOME; p < -5 → "do"; p > 5 → "xanh"; còn lại / null → "xam"
export function mauKomeSoTT(pKome: number | null | undefined): MauLech  // p = % KOME so trung vị: > 5 → "do" (KOME đắt), < -5 → "xanh"
export const phanTram = (gia: number | null | undefined, goc: number | null | undefined) => (gia == null || !goc ? null : Math.round(100 * (gia / goc - 1)));

// nganh.ts
export function tenNganh(food_category_name: string | null | undefined): string
// インスタント食品→"Mì & ăn liền", 冷凍食品→"Đông lạnh", 冷蔵食品→"Đồ mát", 調味料→"Gia vị", 食材（常温）→"Đồ khô",
// 飲料（アルコール）→"Bia rượu", 飲料（アルコール以外）→"Nước uống"; hậu tố _THA / ＿THA → + " (Thái)"; so bằng startsWith;
// "Phí & điều chỉnh", "Hàng tặng (POSM)", "(chưa phân loại)" giữ nguyên; mã lạ → nguyên văn; null/"" → "(chưa phân loại)".

// url.ts
export type Tab = "tom_tat" | "so_sanh" | "ben" | "tin" | "giao_hang" | "duyet" | "nhom" | "lech";
export type TrangThaiUrl = { tab: Tab; ben: string; nganh: string; sp: string[]; sl: "1" | "5" | "10" | "pallet";
  xem: "cot" | "cham" | "nhiet"; gk: string; cung: boolean };
export function docUrl(search: string): TrangThaiUrl      // tab lạ / "tong_quan" → "tom_tat"; sp tách dấu phẩy, bỏ rỗng, ≤ 8
export function vietUrl(t: TrangThaiUrl, search: string): string   // trả "?…" giữ tham số khác (khoảng xem…), bỏ giá trị mặc định (tab tom_tat, sl 1, xem cot, gk chuan, cung false)
```
Mặc định: `sl = "1"`, `xem = "cot"`, `gk = "chuan"`, `cung = false`, `sp = []`.

`HopThoai.tsx`:
```tsx
export function HopThoai({ tieu_de, dong, children, rong = 640 }: { tieu_de: ReactNode; dong: () => void; children: ReactNode; rong?: number })
```
- Portal vào `document.body`, lớp `.lop-phu.giua` (đã có trong `khung.css` / `tong_quan.css`).
- `role="dialog" aria-modal="true" aria-labelledby`.
- Esc đóng, bấm nền đóng. Focus vào phần tử có thể focus đầu tiên (hoặc phần tử mang `data-focus`), bẫy Tab trong hộp, trả focus về phần tử gọi khi đóng.
- Nút ✕ `aria-label="Đóng"`. Cuộn trong hộp khi cao hơn màn.

`ManDoiThu.tsx`:
- Thanh tab `Tóm tắt · So sánh giá · Đối thủ · Tin thị trường · Phí & giao hàng`, cộng nút **Dữ liệu ▾** ở phải.
- Menu Dữ liệu mở bằng bấm hoặc Enter, đóng bằng Esc / bấm ngoài, `aria-haspopup="menu"`, mục `role="menuitem"`. Có 4 mục: Duyệt / sửa bảng giá (`duyet`) · Nhóm & quy cách (`nhom`) · Giá KOME lệch (`lech`) · Thư mục Drive theo tháng (→ `duyet`, cuộn tới khối thư mục). Mỗi mục có một dòng giải thích nhỏ.
- Khi đang ở tab của menu, nút "Dữ liệu ▾" mang `aria-current` và tô như tab đang chọn.
- `url.ts` đọc / ghi trạng thái. Các tab chưa có ở task này thì render `TabTongQuan` / `TabSoSanh` / `TabHoSo` cũ để trang không vỡ giữa chừng; các task sau thay dần.

- [ ] **Step 1: vitest hỏng** cho `mauLech` (−6 đỏ, 6 xanh, 5 và −5 xám, null xám), `mauKomeSoTT` (ngược chiều), `phanTram`, `tenNganh` (đủ 8 tên ngành OBC đang có — lấy danh sách thật bằng `grep -rho "[^\"']*_VNM\|[^\"']*_THA" kome/web/spa` hoặc từ `tq.json` cũ; hậu tố THA; mã lạ), `docUrl` / `vietUrl` (khứ hồi, `tong_quan` → `tom_tat`, giữ `thang=`, bỏ mặc định).
- [ ] **Step 2: cài đặt; chạy vitest; build; `pytest tests/test_api.py -q -k ban_build`; commit.**

---

### Task 4: Giao diện — pop-up sửa (mặt hàng, điều kiện bán, thông tin bên, giao hàng) + lịch sử + 409

**Files:** `doi_thu/sua_logic.ts` (+test), `doi_thu/SuaMatHang.tsx`, `doi_thu/SuaNho.tsx`, `doi_thu/doi_thu.css`.

**Interfaces:**
```ts
// sua_logic.ts
export type BacNhap = { tu: string; don_vi_sl: Bac["don_vi_sl"]; gia: string; don_vi_gia: Bac["don_vi_gia"] };
export type FormMatHang = { nhan: "cung_hang" | "thay_the" | "khong"; trang_thai: string; khuyen_mai: string;
  so_goi_thung: string; kl_goi_g: string; gia_goc: string; don_vi_gia: string; thue: string; bac: BacNhap[];
  vi_sao_gia: "" | "doc_sai" | "da_doi"; loai_nguon: string; lien_ket_bang_chung: string };
export function formTu(q: QuanSat): FormMatHang          // số → chuỗi, null → ""
export function payload(q: QuanSat, f: FormMatHang, ghi_de: boolean): { body: object; doi_gia: boolean; rong: boolean }
// chỉ gửi trường ĐÃ ĐỔI so với formTu(q); doi_gia = có trường giá (gia_goc/don_vi_gia/thue/bac) đổi;
// body = {nguon, id, da_xem: q.sua_cuoi, ghi_de, nhan?, thay_doi, vi_sao_gia?, loai_nguon?, lien_ket_bang_chung?}
// bac gửi dạng mảng số (Number()), bậc trống cả hai ô bị bỏ; rong = không có gì đổi.
export const kgThung = (so_goi: string, kl_goi_g: string) => number | null   // "→ 1 thùng = … kg"
```

`SuaMatHang.tsx`:
```tsx
export function SuaMatHang({ nguon, id, tru_o, dong, xong }: { nguon: "nap" | "tay"; id: number; tru_o?: string; dong: () => void; xong: () => void })
```
- Mở ra thì tải `GET /api/doi-thu/mat-hang/{nguon}/{id}` (TanStack Query, `staleTime: 0`). Đang tải hiện khung giữ chỗ, lỗi hiện câu lỗi.
- Nội dung, bám `popup-sua.html` đã duyệt, nhãn C:
  - **Dòng đầu**: "Sửa: <bên> · <tên hàng>", kèm quy cách gốc · nguồn · ngày · kênh · link mở file gốc (`NguonDong` / `Ra` đã có).
  - **Phần 1**: "So với <tên nhóm KOME> là": Cùng thương hiệu / Khác thương hiệu / Không liên quan — bỏ khỏi nhóm. Radio dạng viên.
  - **Phần 2**: Tình trạng (Còn / Hết / Sắp về) · Khuyến mãi (ô chữ, để trống = không có).
  - **Phần 3**: Quy cách — Gói / thùng · Tịnh 1 gói (g) · "→ 1 thùng = … kg" (tự tính).
  - **Phần 4**: Giá như bảng in:
    - giá gốc + đơn vị + thuế (Đã gồm thuế / Chưa thuế / Không rõ);
    - bảng bậc: "từ [số] [thùng | kg | gói | pallet] → [giá] ¥ / [thùng | kg | gói]", nút ✕ từng bậc, "+ thêm bậc mua nhiều rẻ hơn";
    - đụng vào bất kỳ trường giá nào thì hiện "Vì sao đổi giá?": Máy đọc sai bảng giá / Giá đã đổi (có nguồn mới). Chọn "đã đổi" thì hiện chọn loại nguồn (5 loại từ `app.loai_nguon`: mã `bang_gia`, `chung_tu`, `to_roi`, `khach_ke`, `khac` với nhãn như `TabDuyet.tsx::LOAI_NGUON`) và ô link bằng chứng tuỳ chọn (`https://`).
  - **Lịch sử sửa (n)**: `<details>` liệt kê `lich_su` (ai · lúc · đổi gì — liệt kê khoá của `sau`), dòng cuối "Claude đọc từ bảng giá · <ngay_nguon>" cho dòng nạp.
  - **Nút**: Lưu (chính) · Huỷ · câu nhỏ "Bản gốc máy đọc vẫn giữ; lần sửa ghi vào Nhật ký".
- `tru_o` (`"so_goi_thung"` | `"kl_goi_g"` | …) → ô đó mang `data-focus`, được focus và viền cam khi mở.
- Lưu gọi `gui("/api/doi-thu/sua-mat-hang", body)`:
  - thành công → `qc.invalidateQueries({queryKey: ["doi-thu"]})`, `xong()`;
  - `LoiApi` 409 → hiện khung trong pop-up: "<ai | Ai đó> vừa sửa lúc <giờ:phút dd/mm>: <khoá của sau>" + **Ghi đè** (gửi lại `ghi_de: true`) + **Giữ bản kia** (đóng và làm mới);
  - 400 → câu lỗi dưới nút.
- Nhãn chữ lấy từ `NHAN_GHEP` / `NHAN_TRANG_THAI`. Không in "cùng hàng" / "thay thế".

`SuaNho.tsx` xuất ba hộp, cùng `HopThoai`, cùng xử lý 409:
- `SuaDieuKien({ ben, dk?: DieuKien, dong, xong })`: Loại (ship / thuế / thanh toán / khuyến mãi chung / khác) · Nội dung (1–300) · ☐ "Điều kiện này không còn đúng — bỏ đi" (chỉ khi sửa dòng có sẵn). Gửi `POST /api/doi-thu/dieu-kien`; `da_xem` lấy từ… (không có `sua_cuoi` cho điều kiện ở JSON đọc — gửi 0 và `ghi_de: false`; máy chủ so với nhật ký sau lần đọc trang: chấp nhận).
- `SuaBen({ ben: {ma, ten, web, ghi_chu}, sua_cuoi, dong, xong })`: Tên hiển thị · Website · Ghi chú. `POST /api/doi-thu/ben`.
- `SuaGiaoHang({ dong: GiaoHang, tru_o?, dong_lai, xong })`: đủ 15 trường, mỗi trường một ô (bool = chọn Có / Không / Chưa rõ; enum = chọn; `phu_phi` = một ô số cho mỗi vùng Hokkaido / Tohoku / Kyushu / Chugoku / Shikoku cộng chọn Okinawa: "?" / "+¥" / "không nhận"). Cộng câu gốc `nguon_chu`. Dòng KOME có thêm ☑ "Tôi xác nhận các số này" (gửi `xac_nhan: true`). Gửi `POST /api/doi-thu/giao-hang` với CHỈ trường đổi (`''` = xoá về "chưa rõ").

- [ ] **Step 1: vitest hỏng** cho `formTu` / `payload`: không đổi → `rong`; đổi `kl_goi_g` → chỉ trường đó; đổi `gia_goc` → `doi_gia`; bậc trống bị bỏ; bậc chuỗi `"5,300"` → 5300 (dùng hàm đọc số có sẵn của dự án nếu có, không thì bỏ dấu phẩy nghìn); `nhan` khác → có `nhan`; `da_xem = sua_cuoi`; `kgThung("20", "500") = 10`.
- [ ] **Step 2: cài đặt thành phần.** Chưa gắn vào tab nào; task 5–9 gọi. Viết một test vitest + testing-library NẾU dự án đã dùng testing-library (`grep -rn "@testing-library" giao_dien/package.json`); không có thì chỉ test logic.
- [ ] **Step 3: vitest, build, `ban_build`, commit.**

---

### Task 5: Giao diện — logic tab So sánh (thuần, có test)

**Files:** `doi_thu/so_sanh_logic.ts`, `doi_thu/so_sanh_logic.test.ts`.

**Interfaces:**
```ts
export type SoLuong = "1" | "5" | "10" | "pallet";
export const NHAN_SL: Record<SoLuong, string> = { "1": "1 thùng", "5": "5 thùng", "10": "10 thùng", pallet: "1 pallet" };
/** Giá (¥/kg) của một mặt hàng khi khách mua `sl`. Pallet không ghi → giá lẻ + khongGhiPallet = true. */
export function giaTai(q: QuanSat, sl: SoLuong): { gia: number | null; khongGhiPallet: boolean }
/** Giá KOME để so theo lựa chọn: "chuan" → gia_kome_chuan ?? gia_kome; "thuc" → gia_kome; "01".."10" → gia_kome_bang[lv] ?? null. */
export function giaKome(n: Nhom, gk: string): number | null
export const LUA_CHON_GK: { ma: string; nhan: string }[]   // chuan "標準価格", thuc "thực bán 90 ngày", 01,02,04,05,09 "売価No.x", 10 "売価No.10 · khuyến mãi"
export type Dong = { kome: boolean; q?: QuanSat; ben: string; ten: string; gia: number | null; giaLe: number | null;
  p: number | null; cung: boolean; soGoi: number | null; klGoi: number | null; thieu: boolean; cu: boolean;
  thueKhongRo: boolean; gomShip: boolean; het: boolean; km: boolean; khongGhiPallet: boolean };
/** Dòng của biểu đồ cột một nhóm: KOME + mọi mặt hàng (bỏ khách kể, bỏ bất thường? KHÔNG — bất thường vẫn vẽ nhưng mang cờ), lọc chiCung,
 *  xếp giá tăng (null cuối), rồi thu gọn nếu !moRong: giữ KOME + 5 rẻ nhất + mọi cùng thương hiệu. Trả số dòng bị ẩn. */
export function dongCot(n: Nhom, o: { sl: SoLuong; gk: string; chiCung: boolean; moRong: boolean }): { dong: Dong[]; an: number }
/** Ô bảng nhiệt: mỗi (nhóm, bên) — mặt hàng cùng thương hiệu rẻ nhất, không có thì khác thương hiệu rẻ nhất; kèm số mặt hàng của bên. */
export function oNhiet(ds: Nhom[], o: { sl: SoLuong; gk: string; chiCung: boolean }): { ben: string[]; o: Map<string, { q: QuanSat; p: number | null; so: number; cung: boolean }> }   // khoá `${nhom_khoa}|${ben}`; ben xếp theo số nhóm có mặt giảm dần
export const thieuQuyCach = (q: QuanSat) => q.so_goi_thung == null || q.kl_goi_g == null;
export function demThieu(ds: Nhom[]): { so: number; dau: QuanSat | null; truong: "so_goi_thung" | "kl_goi_g" | null }
export type NutNhanh = "" | "dat" | "het" | "thieu";
/** Danh sách cột trái: lọc ngành (tên OBC), tìm (bỏ dấu, theo ten_nhom + ma_kome), nút nhanh; xếp theo so_ben giảm dần
 *  ("dat": lech_trung_vi > 0.05, xếp giảm dần; "het": có mặt hàng het; "thieu": có mặt hàng thiếu quy cách, xếp số thiếu giảm dần). Bỏ nhóm gia_kome_lech. */
export function locDanhSach(ds: Nhom[], o: { nganh: string; tim: string; nhanh: NutNhanh }): Nhom[]
```
Quy tắc cố định:
- Khách kể (`loai_nguon = 'khach_ke'`) KHÔNG vẽ trong cột / chấm / nhiệt; tab khác lo phần đó.
- `p = phanTram(gia, giaKome)`. `het = trang_thai === "het"`. `km = khuyen_mai || gia_truoc_km != null`. `cu = (tuoi_ngay ?? 0) > NGAY_CU`. `thueKhongRo = thue === "khong_ro"`. `gomShip = gom_ship === "co"`.
- Dòng KOME: `gia = giaKome(n, gk)`, `soGoi = kome_goi_thung`, `klGoi = kome_kg_goi * 1000`. KOME luôn giữ khi thu gọn.
- Dùng `boDau` có sẵn trong `loc.ts` cho tìm kiếm.

- [ ] **Step 1: vitest hỏng** cho từng hàm, với dữ liệu mẫu nhỏ viết tay (một nhóm, 8 mặt hàng, 2 cùng thương hiệu, 1 thiếu quy cách, 1 hết, 1 pallet):
  - thu gọn giữ KOME + 5 rẻ nhất + cùng thương hiệu, `an` đúng;
  - `chiCung` bỏ khác thương hiệu;
  - pallet không ghi → `khongGhiPallet`;
  - `gk = "10"` lấy từ bảng;
  - `oNhiet` chọn cùng thương hiệu trước;
  - `demThieu` trả mặt hàng đầu + trường thiếu;
  - `locDanhSach` từng nút nhanh và bỏ nhóm lệch.
- [ ] **Step 2: cài đặt; vitest; commit** (không đổi giao diện nên chưa cần build; build ở task 6).

---

### Task 6: Giao diện — tab So sánh giá

**Files:** `doi_thu/TabSoSanh.tsx` (viết lại), `doi_thu/BieuDoCot.tsx`, `doi_thu/BieuDoCham.tsx`, `doi_thu/BangNhiet.tsx`, `doi_thu/ONoiGia.tsx`, `doi_thu/doi_thu.css`.

Bám `ca-trang-8.html` (tab So sánh), `goi-thung-3.html`, `tooltip-thung-4.html`, `ky-hieu-thay-the.html` (phương án C).

- **Bố cục**: hai cột `260px | 1fr` trên màn ≥ 900 px, xếp chồng dưới đó.
- **Cột trái** (`locDanhSach`):
  - ô tìm;
  - nút nhanh: Tất cả · KOME đắt nhất · Đối thủ đang hết · Còn ô trống;
  - chip ngành (`tenNganh`);
  - danh sách nhóm: ô chọn, hình (`HinhMa` của `ma_kome[0]`), tên, chấm màu `mauKomeSoTT(lech_trung_vi*100)`, "KOME ±x%" và "n mặt hàng đối thủ";
  - chọn tối đa 8 (vượt quá thì bỏ qua và nháy câu nhỏ "Tối đa 8");
  - mặc định khi `sp` trống: 3 nhóm có `so_ben` lớn nhất.
- **Thanh điều khiển**:
  - Khách mua (1 / 5 / 10 thùng / 1 pallet) · Cách vẽ (A · Cột / B · Chấm / C · Bảng nhiệt) · ☐ Chỉ cùng thương hiệu;
  - Giá KOME (ô chọn `LUA_CHON_GK`);
  - ☐ Tính cả phí giao: chưa hoạt động ở task này; task 9 nối. Ở task này ẨN hẳn, không hiện nút vô hiệu;
  - tất cả ghi lên URL qua `url.ts`.
- **Dòng đếm ô trống** (`demThieu`): chỉ hiện khi > 0, bấm thì mở pop-up của mặt hàng đầu với `tru_o`.
- **A · Cột** (`BieuDoCot`), mỗi nhóm một SVG:
  - đầu nhóm: hình + tên + quy cách + mã + "giá đối thủ khi khách mua <NHAN_SL>";
  - cột Đối thủ · Tên sản phẩm · gói / thùng · tịnh 1 gói, có tiêu đề cột và đường kẻ;
  - thanh: KOME đỏ; cùng thương hiệu xanh lam; khác thương hiệu xám tối, tên mờ; viền vàng khi hết;
  - dòng KOME: dải đỏ nhạt = khoảng `gia_kome_bang` (bỏ '10'), vạch trắng = thực bán khi `gk !== "thuc"`, nhãn **KM** + giá khi `gia_kome_km`;
  - khung viền đứt = giá lẻ khi giá tại số lượng rẻ hơn;
  - nhãn sau thanh: ¥/kg · p% (`mauLech`) · "↓ từ ¥…" · "hết" · "KM" · 🚚 khi gồm ship · ⓟ "?" vàng khi thuế không rõ;
  - "?" cam ở hai cột quy cách khi thiếu;
  - mờ khi cũ;
  - "xem thêm n mặt hàng ▾" / "thu gọn ▴".
- **B · Chấm** (`BieuDoCham`):
  - trục −60…+60 % quanh vạch KOME, nhãn "◀ đối thủ rẻ hơn KOME" (đỏ) và "KOME rẻ hơn ▶" (xanh);
  - mỗi nhóm một hàng; chấm đặc = cùng thương hiệu, vòng rỗng = khác thương hiệu, màu `mauLech`;
  - đuôi đứt từ giá lẻ khi rẻ đi nhờ mua nhiều; viền vàng khi hết.
- **C · Bảng nhiệt** (`BangNhiet`):
  - nhóm × bên (`oNhiet`); ô màu theo `mauLech` với độ đậm ∝ |p| (tối đa ở 40 %);
  - ô nhạt viền đứt + "≈" khi chỉ khác thương hiệu; "·n" khi bên đó có n mặt hàng;
  - cuộn ngang trong khung.
- **Ô nổi** (`ONoiGia`), dùng `ONoi` với `svg`:
  - bên, tên, quy cách gốc, nhãn thương hiệu / hết / KM;
  - 3 ô quy cách cạnh số KOME;
  - bảng bậc từ `q.bac` (đúng nhãn "từ 24 kg", "từ 5 thùng", "giá pallet"): ¥/gói (`gia × kl_goi_g/1000`), ¥/thùng (`gia × kg_thung_dt`), ¥/kg, so KOME. Bậc áp dụng cho `sl` tô đậm. Không có bậc → một dòng "mọi số lượng" + câu "Bên này không ghi giá bậc";
  - dòng KOME;
  - câu nhắc: đặt tối thiểu (bậc đầu > 1 thùng) · thùng khác cỡ (`kg_thung_dt ≠ kome_kg_thung`) · thuế không rõ · giá cũ · "không ghi giá pallet";
  - dòng nhỏ: giá gốc nguyên văn, `gia_bac` chữ gốc, kênh, ngày.
  - Giá bậc quy về ¥/kg đã ở `gia_1/5/10/pallet` (máy chủ). Bảng bậc trong ô nổi là HIỂN THỊ các bậc đã có trong `bac`. Quy từng bậc về ¥/kg ở trình duyệt là phép chia hiển thị, dùng đúng công thức của `mart.gia_bac_kg` (đơn vị giá: thùng ÷ `kg_thung_dt`, gói ÷ `kl_goi_g/1000`, kg giữ; ÷ 1,08 khi `thue === "co"`). Ghi chú trong mã rằng đây là bản hiển thị của hàm mart đó.
- **Bấm** thanh / chấm / ô / "?" → `SuaMatHang`. Bàn phím: thanh / chấm / ô có `tabindex=0`; Tab hiện ô nổi (ONoi đã lo), Enter mở pop-up.
- **Nhóm không có dòng so sánh** (`?nhom=` trỏ tới nhóm chỉ có khách kể): giữ câu báo cũ.
- **Chú giải dưới biểu đồ**: KOME · cùng thương hiệu · khác thương hiệu · dải bảng giá KOME · ? thuế · mờ = cũ · 🚚 gồm ship.

- [ ] **Step 1:** viết thành phần. Mọi quyết định logic dùng hàm của task 5; KHÔNG viết lại luật trong thành phần.
- [ ] **Step 2:** vitest (logic đã có), `npx tsc --noEmit` (hoặc lệnh build), `npm run build`, `pytest tests/test_api.py -q -k ban_build`, commit.

---

### Task 7: Giao diện — tab Tóm tắt

**Files:** `doi_thu/tom_tat_logic.ts` (+test), `doi_thu/TabTomTat.tsx`. Xoá `TabTongQuan.tsx` sau khi thay. Bám `ca-trang-8.html` tab Tóm tắt.

**Interfaces:**
```ts
export function tongSo(ss: Nhom[], tq: TongQuan): { coGia: number; datHon: number; maHet: number; km: number; soBenKm: number }
// coGia = nhóm don_vi_so 'kg' có gia_kome_so và !gia_kome_lech; datHon = số nhóm đó có lech_trung_vi > 0.05;
// maHet = số ma_kome khác nhau trong tq.het_hang trang_thai 'het'; km = tq.khuyen_mai.length; soBenKm = số ben khác nhau.
export function diemVitri(ss: Nhom[]): { nhom: Nhom; p: number; cot: number; tang: number }[]  // p = round(lech_trung_vi*100) kẹp [-60,70]; xếp chấm vào cột 1 %/cột... (beeswarm: cột = round((p+60)/130 * SO_COT), tang = thứ tự trong cột)
export function datNhat(ss: Nhom[], n = 6): Nhom[]; export function reNhat(ss: Nhom[], n = 6): Nhom[]   // theo lech_trung_vi, bỏ nhóm lệch, chỉ > 5% / < −5%
export function coHoi(tq: TongQuan, n = 8): { ma_kome: string; ten: string; ben: { ma: string; ten: string; nguon: string; id: number }[] }[]  // gộp het_hang 'het' theo ma_kome, xếp số bên giảm dần
export function bongNganh(tq: TongQuan): { ben: Ben[]; nganh: string[]; o: Map<string, number> }  // gộp luoi theo tenNganh (ngành THA gộp vào tên có "(Thái)"), xếp theo tổng
```
- **Ô tìm** (hàng / nhóm / đối thủ):
  - gõ thì hiện danh sách gợi ý (≤ 8): nhóm (từ so_sanh), đối thủ (từ `tq.ben`);
  - chọn nhóm → tab So sánh với `sp=<nhóm>`; chọn bên → tab Đối thủ.
- **4 ô số** (`tongSo`).
- **"KOME đứng đâu"**:
  - SVG beeswarm (`diemVitri`), màu `mauKomeSoTT`, ô nổi tên nhóm + %;
  - thanh tỉ lệ rẻ hơn / ngang / đắt hơn / KOME không bán (= nhóm có `gia_kome_so` null);
  - khi có nhóm `gia_kome_lech`: một dòng cảnh báo "n nhóm có giá KOME lệch > 3× — xem Dữ liệu › Giá KOME lệch", bấm được.
- **Đắt nhất / rẻ nhất**: hai khối cạnh nhau, dải giá (thấp → cao, vạch trung vị, chấm KOME), hình, tên, %, ¥/kg. Bấm dòng → So sánh `sp=<nhóm>`.
- **Cơ hội: đối thủ đang hết**: thẻ hình + tên + mã + "n bên đang hết" + chip tên bên. Chip bấm → `SuaMatHang(nguon, id)`.
- **Ai bán ngành nào**: SVG bóng (bán kính ∝ √số mã). Bấm → So sánh với `nganh` + `ben`. Bấm bóng mở So sánh lọc; phần lọc theo bên của So sánh (nếu có) giữ như `TabSoSanh` cũ (`ben` trên URL lọc mặt hàng của bên đó).
- **Khuyến mãi theo bên**: thanh đếm (8 bên nhiều nhất) + 4 thẻ có `gia_truoc_km`. Thẻ bấm → `SuaMatHang`.
- Dữ liệu: `/api/doi-thu/tong-quan` + `/api/doi-thu/so-sanh` (hai query song song, TanStack dùng chung key với tab So sánh).

- [ ] **Step 1: vitest hỏng** cho năm hàm logic (dữ liệu mẫu viết tay).
- [ ] **Step 2: thành phần; vitest; build; ban_build; commit.**

---

### Task 8: Giao diện — tab Đối thủ + tab Tin thị trường

**Files:** `doi_thu/TabHoSo.tsx` (viết lại), `doi_thu/TabTin.tsx`, `doi_thu/doi_thu.css`. Bám `ca-trang-8.html` tab Đối thủ / Tin thị trường.

**Tab Đối thủ** (`/api/doi-thu/ben/{ma}` + `/tong-quan` cho danh sách bên):
- Hàng chip mọi bên đang theo dõi, kèm số mặt hàng trùng KOME. Mặc định (không `ben` trên URL) = bên có nhiều mặt hàng hiện hành có `nhom_khoa` nhất (tính từ `tq.luoi` hoặc `ben.so_dong`; ghi rõ lựa chọn trong mã).
- Đầu trang: tên · ngày bảng giá mới nhất · số dòng · mở file gốc (`Ra`) · "✎ sửa thông tin bên" (`SuaBen`) · website (qua `lienKetAnToan`).
- 4 ô số: mặt hàng trùng KOME (quan sát hiện hành có `gia_kome_so`) · rẻ hơn KOME > 5% (`phanTram(yen_chuan, gia_kome_so) < -5`) · đang hết · khuyến mãi.
- **"Giá bên này so với KOME, từng sản phẩm"**: SVG thanh lệch trái / phải quanh vạch KOME, mỗi quan sát hiện hành có `gia_kome_so` một dòng, xếp theo p tăng dần.
  - Màu thanh theo thương hiệu (§3.2), số % theo `mauLech`, viền vàng khi hết, "KM" tím.
  - Tên hàng là `ten_nhom` (tên KOME) cho dễ đọc; ô nổi có tên gốc + giá.
  - Bấm → `SuaMatHang`.
- **Bán mạnh ngành nào**: thanh (`tenNganh`).
- **Điều kiện bán**:
  - chip `loai · noi_dung`, bấm → `SuaDieuKien`;
  - "+ thêm điều kiện";
  - **Giao hàng** tóm tắt 1 dòng (ship / miễn từ / daibiki) + nút "sửa" → `SuaGiaoHang`.
- **Khách đang mua của bên này** (Đợt 2): giữ bảng cũ.
- **Lịch sử giá từng hàng**: khi một hàng có ≥ 2 quan sát theo tháng, đường nhỏ (sparkline SVG) trong ô nổi của dòng đó. Không có thì bỏ.

**Tab Tin thị trường** (`/tong-quan`):
- **Đối thủ đang hết hàng KOME có**: lưới thẻ (`coHoi` của task 7 với n = 16). Chip bên bấm → `SuaMatHang`.
- **Khuyến mãi đang chạy**: thẻ gom theo bên, 4 dòng đầu + "+ n khuyến mãi khác" (mở rộng tại chỗ). Mỗi dòng bấm → `SuaMatHang`.
- **Tin hiện trường 30 ngày**: thanh ngang cho đối thủ / hàng / tỉnh (dữ liệu `hien_truong` có sẵn). Trống thì một câu. Bấm đối thủ → tab Đối thủ; bấm hàng → So sánh `sp`.

- [ ] Viết, build, ban_build, commit. Logic dùng lại `tom_tat_logic.ts` / `mau.ts` / `nganh.ts`. Nếu cần hàm thuần mới thì thêm vào `tom_tat_logic.ts` kèm test.

---

### Task 9: Giao diện — tab Phí & giao hàng, "Tính cả phí giao", Dữ liệu › Giá KOME lệch, Duyệt dùng pop-up

**Files:** `doi_thu/TabGiaoHang.tsx`, `doi_thu/TabGiaKomeLech.tsx`, `doi_thu/TabDuyet.tsx`, `doi_thu/TabSoSanh.tsx`, `doi_thu/so_sanh_logic.ts` (+test), `doi_thu/ManDoiThu.tsx`. Bám `ca-trang-8.html` tab Phí & giao hàng.

- **Phí & giao hàng** (`/api/doi-thu/giao-hang`):
  - Đơn mẫu:
    - giá trị ¥8,000 / 15,000 / 25,000 / 60,000;
    - số thùng 1 / 2 / 4;
    - giao tới Kanto·Kansai·Chubu (`kanto`) / Tohoku / Hokkaido / Kyushu / Okinawa;
    - trả Daibiki / Chuyển khoản.
  - Biểu đồ "Khách phải trả thêm bao nhiêu cho đơn này":
    - mỗi bên một thanh ghép ship (cam) / vùng (vàng) / daibiki (tím), tính bằng `phi_giao.ts::tinh(dong, don)`;
    - KOME viền đỏ;
    - nhãn "rẻ hơn KOME ¥…" / "đắt hơn KOME ¥…" theo `mauLech`, dấu theo phía KOME;
    - ô "?" đứt nét cho mỗi phần `chua_ro`; "không giao <vùng>" khi `khong_nhan`;
    - xếp: không nhận cuối, nhiều "?" sau, rồi theo tổng tăng dần;
    - ô nổi hiện `nguon_chu`; bấm → `SuaGiaoHang`.
  - Bảng điều kiện: Bên · Phí ship · Miễn ship từ · Phụ phí vùng · Phí daibiki · Ghép kiện · Kiện tối đa · Giá gồm thuế.
    - KOME đầu, nhãn "(suy từ phiếu bán — cần xác nhận)" khi `suy`; ô nổi in `bang_chung`: số đơn có phí ship, đơn lớn nhất, số đơn daibiki 330 / 300;
    - ô thiếu = "?" cam; mỗi ô bấm → `SuaGiaoHang` với `tru_o`.
  - Số trong `GiaoHang` về từ JSON dạng số. Nếu máy chủ trả chuỗi cho numeric thì đổi `Number()` ở ranh giới API, trước khi gọi `tinh`.
- **"Tính cả phí giao"** (So sánh, tắt mặc định, `?phi=1`):
  - thêm `giaCoPhi(gia: number, kgDon: number, phi: {ship, vung, daibiki, chua_ro})` vào `so_sanh_logic.ts`: `gia + (ship + vung + daibiki) / kgDon` khi `chua_ro` rỗng, không thì trả `gia` kèm cờ `chuaRo`;
  - đơn = đúng số thùng đang chọn của mặt hàng đó (pallet: bỏ qua, hiện câu "không áp cho pallet"), `kgDon = số thùng × kg_thung_dt` (KOME: `kome_kg_thung`), `tien = gia_thung × số thùng` (KOME: `giaKome × kome_kg_thung × số thùng`), Kanto, trả daibiki;
  - bên `bao_ship` không cộng ship (đã trong giá);
  - thiếu `kg_thung_dt` / điều kiện → dấu "?" trên thanh, không cộng;
  - cần `/giao-hang` (query chung key với tab Phí);
  - test cho `giaCoPhi`.
- **Dữ liệu › Giá KOME lệch** (`TabGiaKomeLech`): bảng các nhóm `gia_kome_lech` (từ `/so-sanh`), gồm tên, mã KOME, giá KOME để so, trung vị, lệch ×, quy cách hiện dùng (`kome_kg_goi` / `kome_goi_thung` / `kome_kg_thung`), nút "Sửa quy cách" mở hộp nhỏ ghi `POST /api/doi-thu/quy-cach` (đã có; lưu xong làm mới). Giải thích ngắn trong ⓘ: nguyên nhân hay gặp (một バラ là cả thùng; tên ba thừa số).
- **Duyệt / sửa**:
  - danh sách giữ;
  - khung sửa hai cột bên phải thay bằng: bấm dòng → `SuaMatHang`;
  - nút "Đúng rồi" (xác nhận) giữ trên từng dòng;
  - "Thêm hàng AI bỏ sót" giữ form cũ;
  - khối Thư mục Drive giữ.
- **ManDoiThu**: nối đủ các tab; xoá mọi nhánh tạm của task 3.

- [ ] Viết (test cho `giaCoPhi`), build, ban_build, commit.

---

### Task 10: Hoàn tất — CLAUDE.md, tài liệu, cả bộ test

- [ ] **`CLAUDE.md`**:
  - dòng `/doi-thu` của bảng trang: mô tả 5 tab + menu Dữ liệu, endpoint mới, "sửa ở mọi chỗ — pop-up chung, 409 chống sửa đè";
  - khối bất biến 065–068 thêm một đoạn "Màn mới (4b)":
    - luật màu một chỗ `mau.ts::mauLech`;
    - nhãn thương hiệu `kieu.ts::NHAN_GHEP`;
    - `tenNganh` chỉ hiển thị;
    - trình duyệt chỉ chọn cột giá, không tự quy đổi (ngoại lệ: ô nổi hiển thị bậc = bản chép `mart.gia_bac_kg`, và `phi_giao.ts`);
    - khoá nhật ký là nguồn của `sua_cuoi` / 409;
    - `mart.so_sanh_nhom.gia_kome_lech` là định nghĩa duy nhất của "giá KOME lệch".
- [ ] **Đặc tả §7**: đánh dấu endpoint đã làm. Ghi lệch có chủ ý nếu có (ví dụ khoá nhật ký dùng chuỗi cũ `gia:` / `tay:` / `<bên>/<hàng>` thay cho `fact:` / `ghep:` của đặc tả).
- [ ] Sinh lại tài liệu sống. **`pytest -q`** cả bộ, **`npx vitest run`**, build, commit.

---

## Kiểm trên trình duyệt (controller làm sau task 10, không phải task của subagent)

1. Dựng CSDL tạm nội bộ: `apply_all`, rồi chép CHỈ ĐỌC từ CSDL thật các bảng `core.dim_product`, `core.fact_price_list`, `core.fact_gia_doi_thu`, `core.fact_dieu_kien_doi_thu`, `meta.ingest_batch` (các lô liên quan), `core.fact_sales_line` 180 ngày gần nhất, `app.doi_thu` và các bảng `app` liên quan.
2. Chạy app cục bộ trên CSDL đó (không đăng nhập). Kiểm:
   - 5 tab và menu Dữ liệu;
   - 3 cách vẽ, ô nổi, "?" cam;
   - pop-up mở từ mọi chỗ, lưu và 409 (hai tab trình duyệt);
   - bàn phím;
   - 1440 px và 375 px, sáng và tối.
3. Chụp màn gửi chủ DN.
