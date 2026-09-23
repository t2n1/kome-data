# Đợt 2b — Tài liệu sống màn Kho dữ liệu — Kế hoạch triển khai

> **Cho người thực thi:** làm tuần tự từng task, TDD, commit sau mỗi task. pytest chạy
> tiền cảnh, tuần tự, `python -u -m pytest`, không bao giờ hai lượt cùng lúc (CSDL test
> dùng chung).

**Mục tiêu:** hai trang con `/kho-du-lieu/luong` và `/kho-du-lieu/cot-noi` dựng tám khối
tài liệu sinh từ nguồn máy đọc được, 0 truy vấn CSDL.

**Kiến trúc:** hàm thuần trong `kome/tai_lieu.py` đọc `files.yml` (lúc chạy) và một ảnh
chụp JSON `kome/web/tai_lieu_sinh.json` (sinh bởi `scripts/sinh_tai_lieu.py` từ
migration, CLAUDE.md, gates.py, đặc tả lộ trình — những thứ không có trên Vercel). Test
canh ảnh chụp không cũ.

**Đặc tả:** `docs/superpowers/specs/2026-09-23-dot-2b-tai-lieu-song-design.md`

## Ràng buộc chung

- `kome/tai_lieu.py` và `kome/web/app.py` KHÔNG nhập `pandas`, `kome.pipeline`,
  `kome.gates`, `kome.reader` ở mức ngoài cùng.
- Hai trang KHÔNG gọi `open_conn()`.
- Không mã màu hex ngoài `kome/web/static/kome.css`; hai khối màu tối phải giống hệt.
- Văn xuôi Markdown qua `md_dong`: escape trước, rồi mới `**…**`→`<strong>`, `` `…` ``→`<code>`.
- Ảnh chụp: `json.dumps(..., ensure_ascii=False, sort_keys=True, indent=1) + "\n"`.

---

### Task 1: Hai trường khai báo mới trong `files.yml`

**Files:** sửa `kome/config.py` (FileSpec), `config/files.yml`; test `tests/test_tai_lieu.py`.

**Produces:** `FileSpec.core_table: str | None = None`, `FileSpec.references: dict[str, str]`
(default `{}`).

- [ ] Test `test_core_table_khop_undo_tables`: mọi spec có `core_table` và
      `== pipeline.UNDO_TABLES[ten][0]`.
- [ ] Test `test_references_hop_le`: cột có trong `columns.values()`; spec đích tồn tại;
      đích có đúng một khoá.
- [ ] Thêm trường, khai giá trị theo bảng §3.3 của đặc tả. Chạy test, commit.

### Task 2: `kome/tai_lieu.py` — phần lúc chạy

**Produces:**
- `md_dong(s: str) -> Markup`
- `nguon_obc(specs) -> list[dict]` (khoá: `ten, ja, mo_ta, mau, header_row, keys, core_table, tan_suat`)
- `chua_nap() -> list[LoaiChuaCo]`
- `nguong(specs) -> list[dict]` (mỗi spec: `ja, min_rows, row_drop, spike, drop, product_check, required_date, dedup`)
- `khoa_chung(specs) -> list[str]`, `ma_tran(specs) -> list[dict]` (`ten, ja, o: list[str]` ký hiệu ◆●○ hoặc "")
- `noi_di_dau(specs, ten) -> dict` (`tro_ra: [(cot, spec_dich)]`, `tro_vao: [(spec_nguon, cot)]`)
- `cot_cua(specs, ten) -> list[dict]` (`ja, vi, kieu, vai, noi`)
- `chon_file(specs, ten|None) -> str` (lạ → `"uriage"`)

- [ ] Test: `md_dong` escape trước; ma trận có ◆ ở `uriage×slip_no`, ● ở `uriage×customer_code`,
      ○ ở `tokuisaki×salesperson_code`? (không phải khoá chung → không có cột; kiểm
      `salesperson_code` KHÔNG trong `khoa_chung`); `noi_di_dau(shohin)` có `uriage` trong `tro_vao`;
      `cot_cua` đủ số cột = `len(columns)`; kiểu `amount` = "tiền".
- [ ] Viết code, chạy test, commit.

### Task 3: Ảnh chụp sinh + phần đọc ảnh chụp

**Files:** `scripts/sinh_tai_lieu.py` (`sinh(goc: Path) -> dict`, `main()`),
`kome/web/tai_lieu_sinh.json`, thêm vào `kome/tai_lieu.py`:
`doc_anh_chup() -> dict | None`, `bon_tang(anh)`, `cong(anh)`, `cam_bay(anh)`, `lo_trinh(anh)`.

Khoá ảnh chụp: `bang` (`{schema: [tên…]}`), `cong` (`[{so, ten}]`), `cam_bay` (`[chuỗi]`),
`lo_trinh` (`{cot: [...], dong: [[...]]}`).

- [ ] Test `test_anh_chup_tai_lieu_khong_cu`, `test_cam_bay_dem_bang_so_muc_trong_claude_md`
      (đếm bằng regex `^\d+\. ` trong mục), `test_bon_tang_co_view_moi_nhat`
      (`thang_den_hom_nay` trong `mart`; `dim_customer` trong `core`), cổng có đủ 1..5.
- [ ] Viết, sinh file, chạy test, commit.

### Task 4: Route, template, tab, tài liệu

**Files:** `kome/web/app.py`, `templates/_tab_kho_du_lieu.html`, `kho_du_lieu_luong.html`,
`kho_du_lieu_cot_noi.html`, `kho_du_lieu.html` (include tab), `static/kome.css`,
`CLAUDE.md`, `docs/runbook.md`; test `tests/test_tai_lieu_web.py`.

- [ ] Test: 200 cho cả hai trang; `open_conn` nổ vẫn 200; mọi tên cột OBC trong bảng cột
      == `columns` với mọi spec; `?file=khong-co` hiện `売上伝票データ`; `aria-current`
      đúng tab; mỗi mục cạm bẫy hiện; tên cổng hiện.
- [ ] Viết, chạy cả bộ test, commit.
