# Đợt 5b — Báo cáo phân tích + Dashboard chung — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm 7 khối phân tích vào `/bao-cao` và dựng lại `/` thành Dashboard chung, toàn bộ số đọc từ `mart`.

**Architecture:** Migration `029` thêm 7 view vào `mart` (định nghĩa chỉ số). `kome/bao_cao.py` và module mới `kome/tong_quan.py` chỉ hỏi và sắp xếp. Module mới `kome/ve_phan_tich.py` tính toạ độ SVG thuần Python. Template Jinja vẽ SVG phía máy chủ, không JS, không CDN.

**Tech Stack:** Python 3.14, FastAPI, Jinja2, psycopg 3, PostgreSQL (Supabase), pytest.

**Spec:** `docs/superpowers/specs/2026-09-23-dot-5b-bao-cao-dashboard-design.md` (đọc §3–§7 trước khi làm bất kỳ task nào).

## Global Constraints

- OBC chỉ đọc. Không UPDATE/DELETE gì trong `core`. Mọi định nghĩa chỉ số nằm trong `mart` (migration); Python/Jinja chỉ hỏi, sắp xếp, định dạng, tính toạ độ.
- Migration đã chạy thì không sửa; `029` là file mới. Nó PHẢI kết thúc bằng `GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;`.
- Tiền là số nguyên yên (`int(...)` khi đọc `Decimal`). Mã là TEXT.
- "Hôm nay" là `mart.moc_thoi_gian.hom_nay`, KHÔNG `current_date`, KHÔNG đồng hồ Python (trừ `kome/tuoi_du_lieu.py` đã có).
- Không biết ≠ bằng 0: NULL từ `mart` hiện thành "—" kèm lời giải thích, không bao giờ `0`/`0%`.
- Tỷ suất luôn là tỷ số của các TỔNG. Tăng trưởng chỉ khi mẫu số > 0 (view đã lo — Python không tự chia lại).
- Một câu lệnh tham chiếu cùng view `mart` hơn một lần → view đó vào CTE `AS MATERIALIZED` ghi tường minh.
- Không mã màu (hex/rgb) nào ngoài `kome/web/static/kome.css`. Token màu mới phải thêm vào CẢ BA khối: sáng (`:root`), `@media (prefers-color-scheme: dark){ :root:not([data-theme="sang"]) }`, `:root[data-theme="toi"]` — hai khối tối GIỐNG HỆT nhau (có test canh sẵn).
- Không thư viện JS, không CDN, không `fonts.googleapis.com`. Mọi `<svg>` trang trí có `aria-hidden`; mọi phần tử dữ liệu trong SVG có `<title>` ghi số thật.
- Hàm truy vấn nhận `conn`, không tự `connect()`. Route đọc dùng `open_app_conn()`.
- `kome/web/app.py` không nhập pandas/`kome.pipeline` ở mức module.
- Nhãn/chú thích trên trang bằng tiếng Việt; chú thích code tiếng Việt, cùng giọng file xung quanh.
- Test: chạy `python -u -m pytest ...` ở FOREGROUND, tuần tự, KHÔNG bao giờ hai lượt pytest song song (CSDL test dùng chung). KHÔNG chạy migration trên CSDL thật; `DATABASE_URL` chỉ được SELECT.
- Commit kết thúc bằng dòng: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

---

### Task 1: Migration 029 + test cho 7 view

**Files:**
- Create (đã viết sẵn, chưa commit): `db/migrations/029_mart_phan_tich.sql`
- Create: `tests/test_phan_tich_mart.py`

**Interfaces:**
- Produces (view, cột — chính xác như trong file SQL):
  - `mart.ban_theo_nganh_thang(thang, company_fy, nganh, doanh_thu_thuan, lai_gop)`
  - `mart.ban_theo_nganh_thang_so_sanh(thang, company_fy, nganh, doanh_thu_thuan, lai_gop, dt_cung_ky, co_cung_ky, tang_truong)`
  - `mart.nganh_ky_cung_ky(company_fy, nganh, doanh_thu_thuan, lai_gop, dt_doi_chieu, dt_cung_ky, chenh_lech, tang_truong)`
  - `mart.ky_cung_ky(company_fy, so_thang_doi_chieu, thang_dau_doi_chieu, thang_cuoi_doi_chieu, dt, lg, so_khach, dt_ck, lg_ck, so_khach_ck)`
  - `mart.tap_trung_khach(company_fy, customer_code, ten_khach, doanh_thu_thuan, thu_hang, ty_trong, luy_ke)`
  - `mart.ban_theo_ngay(ngay, thang, doanh_thu_thuan, lai_gop, so_phieu, so_khach)`
  - `mart.thang_den_hom_nay(thang, tu_ngay, den_ngay, tu_ngay_ck, den_ngay_ck, dt, lg, so_khach, so_phieu, co_cung_ky, dt_ck, lg_ck, so_khach_ck)` — 0 dòng khi kho rỗng.

SQL đã được kiểm trên CSDL thật bằng cách chạy thân view như truy vấn SELECT (2026-09-23): tổng ngành = ¥1.993.338.702 = tổng kho; `sum(chenh_lech)` kỳ 2026 = ¥64.781.757 = `dt − dt_ck` của `ky_cung_ky`. Nếu một test dưới đây lộ lỗi SQL, sửa SQL trong `029` (file chưa chạy ở đâu cả) và nói rõ trong báo cáo.

- [ ] **Step 1: Viết test** `tests/test_phan_tich_mart.py`, gieo dữ liệu qua loader thật theo đúng nếp `_ban()` của `tests/test_ngan_sach_mart.py` (dùng `kome.loaders.sales.load` với `pandas.DataFrame`, fixture `conn`, `batch`). Cần helper gieo `core.dim_product` (xem cách `tests/test_san_pham.py` gieo sản phẩm; nếu không có loader tiện, INSERT thẳng vào `core.dim_product` là chấp nhận được trong test) và `core.dim_customer` (xem `_ho_so_khach` trong `tests/test_san_pham.py`). Các test (tên gợi ý, mỗi test một docstring nói lỗi nó canh):
  1. `test_tong_cac_nganh_bang_tong_thang_ke_ca_dong_ma_hang_rong` — một dòng `product_code=''`, một dòng mã không có trong `dim_product`, một dòng mã có ngành → `sum` theo tháng của `ban_theo_nganh_thang` = `ban_theo_thang.doanh_thu_thuan`; hai dòng đầu nằm ở `nganh = '(chưa phân loại)'`.
  2. `test_nganh_ban_nam_ngoai_ma_nam_nay_khong_ban_van_co_dong` — ngành A bán 2025-05 và 2026-05 có ngành B chỉ bán 2025-05 → `ban_theo_nganh_thang_so_sanh` có dòng `(2026-05, B)` với `doanh_thu_thuan = 0`, `dt_cung_ky` = số năm ngoái.
  3. `test_khong_sinh_dong_cho_thang_khong_co_trong_kho` — dữ liệu 2025-05 và 2026-05 → không có dòng nào `thang = '2026-06'` hay `'2027-05'`.
  4. `test_khong_co_thang_M_tru_12_thi_co_cung_ky_sai_va_dt_cung_ky_NULL` — chỉ có 2026-05 → `co_cung_ky` false, `dt_cung_ky` NULL, `tang_truong` NULL.
  5. `test_co_thang_M_tru_12_ma_nganh_khong_ban_thi_dt_cung_ky_bang_0` — 2025-05 chỉ ngành A bán; 2026-05 ngành B bán → dòng `(2026-05, B)`: `co_cung_ky` true, `dt_cung_ky = 0`, `tang_truong` NULL.
  6. `test_tang_truong_NULL_khi_cung_ky_am` — cùng kỳ âm (赤伝) → `tang_truong` NULL.
  7. `test_tong_chenh_lech_nganh_bang_chenh_lech_ky` — nhiều ngành, 2 tháng có đối chiếu + 1 tháng không → `sum(chenh_lech)` của `nganh_ky_cung_ky` = `dt − dt_ck` của `ky_cung_ky` cùng `company_fy`.
  8. `test_ky_cung_ky_chi_tinh_thang_doi_chieu` — kỳ 2026 có 2025-09 (không có 2024-09) và 2026-05 (có 2025-05) → `so_thang_doi_chieu = 1`, `thang_dau_doi_chieu = thang_cuoi_doi_chieu = '2026-05'`, `dt` chỉ gồm tháng 5.
  9. `test_ky_cung_ky_dem_khach_DISTINCT_qua_nhieu_thang` — một khách mua cả 2026-04 và 2026-05 (đều có đối chiếu) → `so_khach = 1`.
  10. `test_ky_khong_co_thang_doi_chieu_van_co_dong_voi_so_thang_0` — kỳ chỉ có tháng không đối chiếu → một dòng, `so_thang_doi_chieu = 0`, `dt` NULL.
  11. `test_tap_trung_khach_mot_khach_hai_nguoi_phu_trach_chi_mot_dong` — cùng khách, hai `salesperson_code` trong kỳ → một dòng, tiền cộng lại; `luy_ke` của `thu_hang` lớn nhất = 1.
  12. `test_tap_trung_khach_thu_tu_xac_dinh_khi_bang_tien` — hai khách bằng tiền → `thu_hang` theo `customer_code` tăng dần.
  13. `test_ban_theo_ngay_ngay_khong_ban_co_dong_0_va_khong_qua_hom_nay` — bán 2026-05-11 và 2026-05-13 → có dòng 2026-05-12 với 0; không có dòng sau 2026-05-13.
  14. `test_thang_den_hom_nay_so_cung_so_ngay_khong_tron_thang` — hom_nay 2026-05-12; năm trước bán 2025-05-10 và 2025-05-20 → `dt_ck` chỉ gồm 2025-05-10.
  15. `test_thang_den_hom_nay_29_2_kep_ve_28_2` — hom_nay 2028-02-29 → `den_ngay_ck = 2027-02-28`. (`core.dim_date` phủ tới 2035 nên ngày này hợp lệ.)
  16. `test_thang_den_hom_nay_kho_rong_khong_co_dong`.
  17. `test_ba_vai_tro_deu_SELECT_duoc_moi_view_moi` — nếp `has_table_privilege` của `tests/test_ngan_sach_mart.py:300-313`, danh sách 7 view.
  18. `test_nganh_so_sanh_chi_quet_fact_sales_line_mot_lan` — `EXPLAIN (FORMAT JSON) SELECT * FROM mart.ban_theo_nganh_thang_so_sanh`, duyệt cây kế hoạch, đếm node có `"Relation Name" == "fact_sales_line"` → đúng 1. Làm tương tự cho `mart.ky_cung_ky`: đếm ≤ 3 (1 nối chính + 2 EXISTS của `doi`) — ghi rõ lý do trong docstring.

- [ ] **Step 2:** Chạy `python -u -m pytest tests/test_phan_tich_mart.py -v`. Fixture `conn` tự áp mọi migration (kể cả 029) lên CSDL test. Test nào đỏ vì SQL sai → sửa `029`, chạy lại. Test nào đỏ vì test sai → sửa test.
- [ ] **Step 3:** Chạy toàn bộ `python -u -m pytest -q` (foreground). Phải xanh.
- [ ] **Step 4:** Commit `db/migrations/029_mart_phan_tich.sql` + `tests/test_phan_tich_mart.py`: `feat: migration 029 - bay view phan tich cho bao cao va dashboard`.

---

### Task 2: Tầng dữ liệu của `/bao-cao`

**Files:**
- Modify: `kome/bao_cao.py` (`BaoCao`, `tinh_bao_cao`, thêm dataclass)
- Test: `tests/test_bao_cao_phan_tich.py` (tạo mới; Task 3–4 thêm tiếp vào file khác)

**Interfaces:**
- Consumes: các view của Task 1.
- Produces (thêm vào `kome/bao_cao.py`):
  ```python
  @dataclass
  class CungKy:                 # một dòng mart.ky_cung_ky
      so_thang: int             # so_thang_doi_chieu
      tu: str | None            # thang_dau_doi_chieu 'YYYY-MM'
      den: str | None
      dt: int | None; lg: int | None; so_khach: int | None
      dt_ck: int | None; lg_ck: int | None; so_khach_ck: int | None
      # property, KHÔNG phải định nghĩa mới — chỉ là tỷ số của hai cột tổng đã có:
      #   tang_dt / tang_lg / tang_khach -> float | None  (None nếu mẫu số None hoặc <= 0)
      #   ty_suat / ty_suat_ck -> float | None (lg/dt, None nếu dt None hoặc <= 0)
      #   chenh_ty_suat -> float | None  (điểm phần trăm, ty_suat - ty_suat_ck)

  @dataclass
  class NganhThang:  thang: str; nganh: str; doanh_thu: int; dt_cung_ky: int | None; co_cung_ky: bool; tang_truong: float | None
  @dataclass
  class NganhKy:     nganh: str; doanh_thu: int; lai_gop: int; dt_doi_chieu: int | None; dt_cung_ky: int | None; chenh_lech: int | None; tang_truong: float | None
  @dataclass
  class KhachTapTrung: ma: str; ten: str; doanh_thu: int; thu_hang: int; ty_trong: float | None; luy_ke: float | None
  @dataclass
  class TapTrung:    dong: list[KhachTapTrung]; so_khach: int; luy_ke_top10: float | None
  ```
  `BaoCao` thêm các trường (mặc định rỗng/None để nhánh "không có dữ liệu" vẫn dựng được): `cung_ky: CungKy | None`, `nganh_thang: list[NganhThang]`, `nganh_ky: list[NganhKy]`, `tap_trung: TapTrung | None`, `hang_theo_nganh: list[dict]` (mọi dòng `mart.ban_theo_san_pham` của kỳ; khoá dict: `ma, ten, nhom, doanh_thu, lai_gop, ty_suat, so_khach`). `O` thêm `so_khach: int` và `dt_cung_ky: int | None`.
  `BaoCao.hang` (top 10 lãi gộp) GIỮ tên và hình dạng cũ, nhưng lấy bằng `sorted(hang_theo_nganh, key=lai_gop, reverse=True)[:TOP]` (chú thích: sắp xếp hiển thị, tiết kiệm một lượt hỏi). `BaoCao.khach` GIỮ (template cũ còn dùng tới khi Task 4 đổi) = 10 dòng đầu `tap_trung` dạng dict cũ `ma, ten, tinh, doanh_thu, lai_gop, ty_suat, so_phieu, mua_gan_nhat` — HOẶC xoá hẳn nếu grep chứng minh chỉ `bao_cao.html` và `tong_quan.html` dùng nó và Task 4/5 thay; quyết định và ghi lý do trong báo cáo. (Ưu tiên: thay `khach` bằng `tap_trung`, cập nhật đúng chỗ dùng trong template ở Task 4.)

- [ ] **Step 1: Test thất bại** trong `tests/test_bao_cao_phan_tich.py`:
  - `test_bao_cao_khong_qua_11_truy_van` — gieo dữ liệu hai năm + một chỉ tiêu (`app.ngan_sach`), đếm bằng helper `_dem_truy_van` (chép nếp `tests/test_san_pham.py:50-62`) quanh `tinh_bao_cao(conn, fy)` + `tien_do_ngan_sach(conn, fy)` → `<= 11`.
  - `test_cung_ky_noi_so_thang_doi_chieu` — `bc.cung_ky.so_thang`, `tu`, `den` đúng; `tang_dt` = `dt/dt_ck - 1`.
  - `test_cung_ky_mau_so_am_thi_tang_truong_None`.
  - `test_nganh_ky_va_nganh_thang_doc_dung_ky` — không lẫn dòng của kỳ khác.
  - `test_tap_trung_top10_va_so_khach` — 12 khách → `len(dong) <= 20`, `so_khach = 12`, `luy_ke_top10` = `luy_ke` của hạng 10.
  - `test_hang_top10_theo_lai_gop_giu_nguyen_hanh_vi` — cùng kết quả như truy vấn cũ `ORDER BY lai_gop DESC LIMIT 10`.
  - `test_kho_rong_van_dung_duoc_bao_cao` — `tinh_bao_cao` trên kho rỗng không nổ, các trường mới rỗng/None.
- [ ] **Step 2:** Chạy test mới → đỏ.
- [ ] **Step 3:** Cài đặt. Thứ tự truy vấn gợi ý: (1) `mart.tong_theo_ky t LEFT JOIN mart.ky_cung_ky c USING (company_fy)` — một câu lấy mọi kỳ kèm cùng kỳ; (2) tháng — thêm `so_khach`, `dt_cung_ky` vào câu `ban_theo_thang_so_sanh` đang có; (3) `mart.tap_trung_khach WHERE company_fy=%s ORDER BY thu_hang LIMIT 20` + `count(*) OVER ()` để có `so_khach` trong cùng câu (chú ý: `count(*) OVER ()` phải đếm TRƯỚC LIMIT — dùng truy vấn con, hoặc lấy `max(thu_hang)`); (4) `mart.ban_theo_san_pham WHERE company_fy=%s`; (5) nhân viên (đang có); (6) `mart.ban_theo_nganh_thang_so_sanh WHERE company_fy=%s ORDER BY nganh, thang`; (7) `mart.nganh_ky_cung_ky WHERE company_fy=%s ORDER BY chenh_lech`. Không gộp (6) và (7) — xem spec §5 cuối.
- [ ] **Step 4:** Test mới xanh, rồi `python -u -m pytest -q` toàn bộ xanh (template cũ có thể cần sửa nhỏ nếu đổi `khach` — nếu đổi thì sửa luôn cho trang cũ render được).
- [ ] **Step 5:** Commit `feat: bao_cao doc so cung ky, nganh hang, tap trung khach tu mart`.

---

### Task 3: Hình học SVG (thuần Python)

**Files:**
- Create: `kome/ve_phan_tich.py`
- Modify: `kome/bao_cao.py::ve_bieu_do` (thêm đường cùng kỳ)
- Test: `tests/test_ve_phan_tich.py`

**Interfaces:**
- Consumes: `NganhThang`, `NganhKy`, `TapTrung`, `O` (Task 2) — nhưng các hàm nhận kiểu dữ liệu đơn giản khi được để test không cần CSDL.
- Produces (mỗi hàm trả `dict` có khoá `"co": bool`; `co=False` khi không có gì để vẽ):
  - `ve_duong_nho(so: list[int | float | None], rong=120, cao=32) -> dict` — `{"co", "rong", "cao", "doan": list[str]}`; mỗi phần tử `doan` là chuỗi `points` của một `<polyline>`; `None` cắt đường thành đoạn mới. Tất cả None → `co=False`.
  - `ve_bieu_do(thang)` (đã có) thêm khoá `"duong_ck": list[str]` (các đoạn polyline nét đứt của `dt_cung_ky`, cùng thang đo trục doanh thu; tháng `dt_cung_ky is None` cắt đoạn) — `dinh` phải tính trên max của CẢ doanh thu lẫn cùng kỳ để đường không vọt khỏi khung.
  - `ve_dong_gop(dong: list[NganhKy], rong=720) -> dict` — chỉ ngành có `chenh_lech is not None`; xếp giảm dần theo `chenh_lech`; trục giữa ở `x0`; mỗi thanh `{"nganh", "x", "w", "y", "am": bool, "chenh_lech", "tang_truong"}`; thang đo đối xứng theo `max(|chenh_lech|)`.
  - `ve_cay_o(nhom: list[tuple[str, int, float | None, list[tuple[str, str, int]]]], rong=720, cao=360, toi_da_ma=5) -> dict` — đầu vào: `(nganh, doanh_thu_nganh, tang_truong_nganh, [(ma, ten, doanh_thu), ...])`. Bỏ phần tử `doanh_thu <= 0` ở cả hai tầng, cộng dồn chúng vào `"khong_ve": int` (số âm/0 bị bỏ) và `"so_ma_khong_ve": int`. Tầng 1 squarified theo doanh thu ngành trong khung; tầng 2 trong mỗi ô ngành: tối đa `toi_da_ma` mã lớn nhất + một ô `"(khác)"` cho phần còn lại dương (doanh thu ngành đã lọc dương − tổng các mã vẽ riêng; nếu ≤ 0 thì không có ô "khác"). Trả `{"co", "rong", "cao", "nganh": [{"nganh", "x","y","w","h", "bac", "doanh_thu", "tang_truong", "ma": [{"ten","x","y","w","h","doanh_thu"}]}], "khong_ve", "so_ma_khong_ve"}`. `bac` = `bac_tang_truong(tang_truong)`.
  - `bac_tang_truong(t: float | None) -> str` — `"khong"` khi None; `"g2"` (≤ −20%), `"g1"` (−20…−5%), `"0"` (−5…+5%), `"t1"` (+5…+20%), `"t2"` (≥ +20%). Biên: −0.20 → `g2`, −0.05 → `g1`, +0.05 → `t1`, +0.20 → `t2` (ghi đúng thế trong docstring và test).
  - `ve_nhiet(dong: list[NganhThang], thang: list[str]) -> dict` — `thang` là 12 tháng của kỳ (dùng `kome.ngan_sach.thang_cua_ky`); hàng = ngành (xếp theo tổng doanh thu kỳ giảm dần, tính bằng `sorted` trên dữ liệu đã có — sắp xếp hiển thị), cột = tháng; mỗi ô `{"thang","nganh","bac","tang_truong","doanh_thu","co_cung_ky"}`; ô không có dòng hoặc `co_cung_ky=False` → `bac="khong_ck"`; ô `co_cung_ky=True` mà `tang_truong is None` → `bac="khong"` (cùng kỳ ≤ 0).
  - `ve_pareto(tt: TapTrung, rong=720, cao=260) -> dict` — cột theo `doanh_thu` (cột âm cao 0, vẫn có mặt), đường `luy_ke` theo trục 0–100% bên phải, `luy_ke` kẹp [0, 1] khi VẼ (số in ra giữ nguyên). Trả `{"co","cot":[...],"duong":str,"rong","cao"}`.
  - Thuật toán squarified: Bruls, Huizing, van Wijk (2000). Viết một hàm riêng `_squarify(gia_tri: list[float], x, y, w, h) -> list[tuple[x,y,w,h]]` (giá trị dương, đã xếp giảm dần), có docstring nói thuật toán và nguồn.

- [ ] **Step 1: Test thất bại** `tests/test_ve_phan_tich.py` (không cần CSDL):
  - `_squarify`: tổng diện tích = w·h (sai số 1e-6); không ô nào ra ngoài khung; mỗi ô có diện tích tỷ lệ với giá trị.
  - `ve_cay_o`: ngành âm bị bỏ và `khong_ve` bằng đúng tổng âm đó; mã âm trong ngành dương bị bỏ và cộng vào `khong_ve`; ô "(khác)" xuất hiện khi ngành có > 5 mã dương; tổng diện tích ô ngành = rong·cao.
  - `bac_tang_truong`: đủ các biên như trên, và None.
  - `ve_duong_nho([1, None, 3, 4])` → 2 đoạn; toàn None → `co=False`.
  - `ve_bieu_do` với tháng thiếu cùng kỳ → `duong_ck` bị cắt đoạn; không điểm nào có y ngoài khung khi cùng kỳ lớn hơn doanh thu.
  - `ve_nhiet`: ô không có cùng kỳ → `khong_ck`; ô cùng kỳ = 0 → `khong`; 12 cột luôn đủ kể cả tháng không có dòng.
  - `ve_dong_gop`: thanh âm nằm bên trái trục; ngành `chenh_lech=None` không có thanh.
  - `ve_pareto`: `luy_ke > 1` (có khách âm) vẽ kẹp ở mép trên.
- [ ] **Step 2:** Đỏ. **Step 3:** Cài đặt. **Step 4:** Xanh, rồi toàn bộ `python -u -m pytest -q` xanh.
- [ ] **Step 5:** Commit `feat: hinh hoc SVG cho cac khoi phan tich (treemap, nhiet, pareto, dong gop)`.

---

### Task 4: Trang `/bao-cao` + token màu

**Files:**
- Modify: `kome/web/templates/bao_cao.html`, `kome/web/app.py` (route `/bao-cao` — thêm ngữ cảnh vẽ), `kome/web/static/kome.css`
- Test: `tests/test_bao_cao_phan_tich_web.py`

**Interfaces:**
- Consumes: `BaoCao` (Task 2), mọi hàm `ve_*` (Task 3), `thang_cua_ky`.
- Route truyền thêm vào template: `"so_nho": {"dt": ve_duong_nho(...), "lg": ..., "ts": ..., "kh": ...}` (12 tháng của kỳ), `"dg": ve_dong_gop(bc.nganh_ky)`, `"co": ve_cay_o(...)` (dựng `nhom` từ `bc.nganh_ky` + `bc.hang_theo_nganh` nhóm theo `nhom`; `hang_theo_nganh.nhom` NULL/rỗng → `'(chưa phân loại)'` — **đây là chỗ thứ hai viết nhãn đó**: đặt hằng `NGANH_TRONG = '(chưa phân loại)'` trong `kome/bao_cao.py` kèm chú thích "phải khớp chữ trong 029 §3.1", và một test so hằng này với giá trị view trả ra), `"nh": ve_nhiet(bc.nganh_thang, thang_cua_ky(bc.ky.company_fy))`, `"pa": ve_pareto(bc.tap_trung)`.
- Token CSS mới (cả ba khối, hai khối tối giống hệt): `--nhiet-g2`, `--nhiet-g1`, `--nhiet-0`, `--nhiet-t1`, `--nhiet-t2`, `--nhiet-khong` (trung tính), `--nhiet-soc` (màu sọc cho "không có cùng kỳ"), `--duong-ck` (đường cùng kỳ). Chọn màu đỏ→trung tính→xanh từ tông đang có (`--do`, `--ok-vien`…), đủ tương phản cho chữ `--chu` đè lên ở cả sáng lẫn tối. Sọc bằng `<pattern>` SVG dùng `var(--nhiet-soc)`.

Bố cục đúng thứ tự spec §5. Tham khảo hình thức (không chép số, không chép màu hex): gói thiết kế ở `C:\Users\TRANTR~1\AppData\Local\Temp\claude\C--Antigravity-kome-data\3e5c9d1d-ad41-46bc-bd32-c6f6376347e0\scratchpad\dsg\design_handoff_kome\screens\Báo cáo.dc.html` dòng 44–55 (4 ô chỉ số), 215–251 (12 tháng), 253–270 (đóng góp), 273–302 (cây ô), 304–326 (nhiệt), 328–358 (Pareto), 360–392 (bảng chi tiết). Nếu đường dẫn không tồn tại, dựng theo spec là đủ.

Chữ bắt buộc (test khẳng định):
- Ô chỉ số khi có đối chiếu: `so cùng kỳ · {n} tháng đối chiếu ({tu} → {den})`; khi không: `chưa có cùng kỳ để so`. Tỷ suất so bằng `điểm`.
- Cây ô khi `khong_ve != 0`: `Không vẽ: ¥{khong_ve:,} của {so_ma_khong_ve} mã doanh thu âm hoặc bằng 0`.
- Nhiệt: chú giải có `không có cùng kỳ`.
- Pareto: `{10} khách lớn nhất = {x}% doanh thu kỳ này, trên {so_khach} khách có doanh thu`.
- Khối đóng góp khi không có tháng đối chiếu: tiêu đề vẫn hiện, kèm câu giải thích có chữ `không có tháng nào để so cùng kỳ`.

- [ ] **Step 1: Test thất bại** `tests/test_bao_cao_phan_tich_web.py` (dựng app qua fixture giống `tests/test_ngan_sach_bao_cao.py`; đọc file đó trước để chép nếp dựng `TestClient`):
  - trang 200 trên kho rỗng; trên kho có dữ liệu hai năm;
  - các chuỗi bắt buộc ở trên hiện đúng điều kiện (có và không có đối chiếu);
  - `NGANH_TRONG` khớp chữ view trả ra cho dòng mã hàng rỗng;
  - không có mã màu hex/rgb trong `bao_cao.html` (regex `#[0-9a-fA-F]{3,8}\b` ngoài `&#` và ngoài `href="#`; nếu repo đã có test chung cho mọi template thì chỉ cần nó xanh);
  - `test_giao_dien.py::test_hai_khoi_mau_toi_trong_css_GIONG_HET_NHAU` vẫn xanh (chạy lại);
  - mọi `<rect>`/`<circle>` dữ liệu trong 4 SVG mới có `<title>`;
  - chip kỳ, ba khối ngân sách 5a và bảng người phụ trách vẫn còn (các test 5a hiện có phải xanh nguyên).
- [ ] **Step 2:** Đỏ. **Step 3:** Cài đặt. **Step 4:** Xanh + toàn bộ `python -u -m pytest -q` xanh.
- [ ] **Step 5:** Mở thử bằng `uvicorn` với `DATABASE_URL_TEST` KHÔNG cần — test render là đủ; nhưng in HTML một lần ra file tạm và tự đọc để chắc bố cục hợp lý (không cần báo cáo ảnh).
- [ ] **Step 6:** Commit `feat: /bao-cao them 7 khoi phan tich`.

---

### Task 5: Dashboard `/`

**Files:**
- Create: `kome/tong_quan.py`
- Modify: `kome/web/app.py` (route `/`), `kome/web/templates/tong_quan.html` (viết lại), `kome/ve_phan_tich.py` (thêm `ve_xu_huong`)
- Test: `tests/test_tong_quan.py` (tạo mới; nếu đã có test cho `/` ở file khác — grep `"/"` và `tong_quan` trong `tests/` — cập nhật các khẳng định bố cục cũ thay vì xoá, và nói rõ trong báo cáo)

**Interfaces:**
- Consumes: `mart.thang_den_hom_nay`, `mart.ban_theo_ngay`, `mart.khach_360`, `kome.khach_hang.can_xu_ly(conn, gioi_han=5, sale=...)`, `kome.bao_cao.tien_do_ngan_sach(conn)`, `kome.san_pham.kho_hang(conn)` (dùng `.can_han[:5]`, `len(.qua_han)`), `kome.san_pham.CAN_HAN_NGAY`, `ve_duong_nho`.
- Produces:
  ```python
  @dataclass
  class ThangNay:  # một dòng mart.thang_den_hom_nay
      thang: str; tu_ngay: date; den_ngay: date; tu_ngay_ck: date; den_ngay_ck: date
      dt: int; lg: int; so_khach: int; so_phieu: int
      co_cung_ky: bool; dt_ck: int | None; lg_ck: int | None; so_khach_ck: int | None
      # property tang_dt / tang_lg / tang_khach / ty_suat / ty_suat_ck / chenh_ty_suat — cùng quy tắc CungKy (Task 2)
  @dataclass
  class TongQuan:
      thang_nay: ThangNay | None      # None khi kho rỗng
      ngay: list[tuple[date, int]]    # 60 ngày cuối (<= hom_nay), cũ → mới
      dem: dict[str, int]             # trang_thai -> số khách (như route cũ)
      can_goi: list                   # list[Khach] từ can_xu_ly
      ngan_sach: "TienDoNganSach | None"
      can_han: list[dict]; so_qua_han: int
  def tong_quan(conn, sale: str | None) -> TongQuan
  ```
  Nếu `CungKy` và `ThangNay` có cùng bộ property, rút một mixin/hàm dùng chung trong `kome/bao_cao.py` thay vì chép hai lần.
  `ve_xu_huong(ngay: list[tuple[date,int]], rong=720, cao=180) -> dict` trong `kome/ve_phan_tich.py`: 30 ngày cuối thành cột, 30 ngày trước đó thành đường (xếp theo thứ tự ngày: ngày thứ i với ngày thứ i); ít hơn 31 ngày dữ liệu thì không có đường; `dinh` = max của cả hai dãy. Test thuần trong `tests/test_ve_phan_tich.py`.
- Route `/`: `sale` = mã sale của người đăng nhập (dùng lại `_sale_dang_loc(request, tat_ca)` với `?tat_ca=1` để bỏ lọc — cùng nếp `/can-xu-ly`); truyền `co_quyen_ngan_sach` = người đăng nhập có `duoc_sua_ngan_sach` (xem cách `hien_ngan_sach` trong `app.py` quyết định mục nav — dùng CÙNG hàm/điều kiện, không viết điều kiện thứ hai). Route không gọi `tinh_bao_cao` nữa.
- Template: đúng thứ tự spec §6. Chữ bắt buộc: dải ngày `{tu_ngay} – {den_ngay} so với {tu_ngay_ck} – {den_ngay_ck}` (định dạng ngày Việt `dd/mm/yyyy`); `Chưa đặt chỉ tiêu tháng này`; liên kết `/ngan-sach` chỉ khi có quyền; `Danh sách của {tên}` + liên kết `?tat_ca=1` khi đang lọc; dòng `chưa có nguồn dữ liệu` liệt kê `Công nợ`, `Dòng tiền`, `Mua hàng`, `Khiếu nại`, `Thời tiết`; KHÔNG còn khối "Tồn kho" trong phần chưa có dữ liệu. Thanh sức khoẻ: mỗi đoạn là `<a href="/khach-hang?loc={trang_thai}">` (riêng `canh_bao` → `/can-xu-ly`, như trang cũ).

- [ ] **Step 1: Test thất bại** `tests/test_tong_quan.py`:
  - `test_trang_chu_khong_qua_11_truy_van` (đếm quanh `tong_quan(conn, None)` + `tinh_tuoi(conn)` — hoặc đếm qua route với conn được vá; chọn cách đếm được thật và ghi lý do).
  - `test_o_chi_so_so_cung_so_ngay` (qua dữ liệu, như test 14 của Task 1 nhưng ở tầng `ThangNay`).
  - `test_lien_ket_ngan_sach_chi_hien_khi_co_quyen` (cần cổng đăng nhập — chép nếp fixture `khach` của `tests/test_bao_mat.py` hoặc `tests/test_ngan_sach_web.py`).
  - `test_khong_con_khoi_ton_kho_chua_co_du_lieu` và dòng `chưa có nguồn dữ liệu` có đủ 5 tên.
  - `test_can_goi_mac_dinh_loc_theo_nguoi_dang_nhap` và `?tat_ca=1` bỏ lọc.
  - `test_trang_chu_kho_rong_van_200`.
  - `ve_xu_huong`: ít hơn 31 ngày → không có đường; 60 ngày → 30 cột + đường 30 điểm.
- [ ] **Step 2:** Đỏ. **Step 3:** Cài đặt. **Step 4:** Xanh + toàn bộ `python -u -m pytest -q` xanh.
- [ ] **Step 5:** Commit `feat: dung lai / thanh dashboard chung`.

---

### Task 6: Tài liệu

**Files:**
- Modify: `CLAUDE.md`, `docs/runbook.md`

- [ ] **Step 1:** `CLAUDE.md` — bảng "Các trang của web app": dòng `/` đổi nguồn thành `mart.thang_den_hom_nay`, `ban_theo_ngay`, `khach_360`, `tien_do_ngan_sach`, `ton_hien_tai` (qua `kho_hang`), `meta.ingest_batch`; dòng `/bao-cao` thêm `ky_cung_ky`, `ban_theo_nganh_thang_so_sanh`, `nganh_ky_cung_ky`, `tap_trung_khach`. Thêm các bất biến (mỗi cái một đoạn, giọng các bất biến hiện có, nêu lỗi cụ thể nếu phá và test canh):
  - so cùng kỳ ở `/bao-cao` là **cùng tháng với cùng tháng** (`mart.ky_cung_ky`) và luôn in số tháng đối chiếu; ở `/` là **cùng dải ngày** (`mart.thang_den_hom_nay`);
  - ngành hàng = `food_category_name` viết một lần trong `mart.ban_theo_nganh_thang`, LEFT JOIN, `(chưa phân loại)`; hằng `NGANH_TRONG` là bản chép có test canh;
  - `ban_theo_nganh_thang_so_sanh` FULL JOIN + lọc tháng có trong kho;
  - Pareto gộp theo khách, không theo `(khách, sale)`;
  - cây ô không vẽ được số âm và PHẢI in phần bị bỏ;
  - Dashboard: số tổng không lọc theo người đăng nhập, chỉ khối "cần gọi" lọc; không dựng khối thiếu nguồn.
  - Ngân sách truy vấn: `/bao-cao` ≤ 11, `/` ≤ 11 (có test đếm).
- [ ] **Step 2:** `docs/runbook.md` — mục "Danh sách việc sau migration": thêm `029` (không cần cấp quyền gì thêm; chỉ chạy `python db/migrate.py` bằng `postgres`) và KIỂM TAY của spec §8.
- [ ] **Step 3:** `python -u -m pytest -q` xanh (có test đọc `CLAUDE.md`? grep `CLAUDE.md` trong `tests/` — nếu có thì phải xanh).
- [ ] **Step 4:** Commit `docs: CLAUDE.md va runbook cho dot 5b`.
