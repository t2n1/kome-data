# Đặc tả thiết kế — Đợt 2b: Kho dữ liệu, phần tài liệu sống

**Ngày:** 2026-09-23
**Phạm vi:** hai trang con chỉ-đọc của màn Kho dữ liệu, dựng tám khối tài liệu sống
của màn 19 trong gói thiết kế (`Kho dữ liệu.dc.html`, chế độ `laLuong` và `laNoi`).
**Trạng thái:** Đã duyệt thiết kế trong hội thoại (2026-09-23)
**Tài liệu liên quan:** lộ trình `2026-09-21-lo-trinh-24-man-hinh-design.md` §7 (ràng
buộc riêng cho 2b), đặc tả đợt 2a §2.2.

---

## 1. Mục tiêu

Người mới (hoặc một AI bảo trì) mở màn Kho dữ liệu phải trả lời được, không cần đọc
code: file OBC nào vào bảng nào · khoá nào nối file nào với file nào · mỗi lần nạp bị
kiểm những gì, ngưỡng bao nhiêu · những bẫy nào của OBC đã từng làm hỏng dữ liệu.

**Ràng buộc gốc (lộ trình §7):** tài liệu sống phải **sinh ra, không chép tay**. Mọi
tên cột, tên khoá, ngưỡng, tên bảng hiện trên trang phải đến từ một nguồn máy đọc
được đã có trong repo. Chép tay là bản sao thứ ba của sự thật và sẽ mục trước tiên.

---

## 2. Hình dáng

| Đường dẫn | Tên | Khối |
|---|---|---|
| `/kho-du-lieu/luong` | Sơ đồ luồng | Bốn tầng · Bảy nguồn từ OBC · Đối chiếu bắt buộc sau mỗi lần nạp · Cạm bẫy riêng của OBC · Lộ trình |
| `/kho-du-lieu/cot-noi` | Cột nối | Ma trận khoá · File này nối đi đâu · Cột trong từng file |

- Đầu màn `/kho-du-lieu` và hai trang con có một dải tab ba mục: **Vận hành**
  (`/kho-du-lieu`) · **Sơ đồ luồng** · **Cột nối**. Tab đang xem có
  `aria-current="page"`.
- `/kho-du-lieu/cot-noi?file=<tên spec>` chọn file cho hai khối cuối (mặc định
  `uriage`). Tên không có trong `files.yml` → dùng mặc định, không 404, không lỗi.
  Máy chủ vẽ, không JS.
- **Không truy vấn CSDL nào** (0 lượt hỏi, có test đếm). Không `open_conn()`.
- Chạy được ở bản chỉ-đọc (Vercel) — không có gì để ẩn.
- **Quyền:** hai đường dẫn nằm dưới tiền tố `/kho-du-lieu/` nên middleware hiện có đã
  gác bằng `duoc_vao_kho_du_lieu`. Giữ nguyên, không thêm ngoại lệ — một ngoại lệ
  trong hàm gác cửa màn có nút xoá dữ liệu là thứ không đáng đổi lấy việc người
  không có quyền đọc được tài liệu kỹ thuật. (Lệch khỏi câu "ai đăng nhập cũng xem"
  trong bản trình bày; đổi vì đơn giản hơn và không nới cửa nào.)

---

## 3. Nguồn của từng khối

### 3.1 Hai loại nguồn

`.vercelignore` loại `docs/`, `db/`, `scripts/`, `tests/` khỏi bản Vercel. Nên:

- **Nguồn đọc lúc chạy:** `config/files.yml` (qua `kome.config.load_specs`) và
  `kome.coverage` (thuần Python, không pandas). Có mặt ở mọi bản chạy.
- **Nguồn đọc lúc sinh:** `db/migrations/*.sql`, `CLAUDE.md`, đặc tả lộ trình,
  `kome/gates.py` (nhập pandas nên không được nhập từ web). Script
  `scripts/sinh_tai_lieu.py` đọc chúng và ghi **ảnh chụp**
  `kome/web/tai_lieu_sinh.json` (commit vào git, UTF-8, `ensure_ascii=False`,
  `sort_keys=True`, thụt 1 — để diff đọc được).

**Bất biến:** test `test_anh_chup_tai_lieu_khong_cu` sinh lại ảnh chụp trong bộ nhớ và
so bằng với file đã commit. Sửa migration / CLAUDE.md / gates.py mà quên chạy
`python scripts/sinh_tai_lieu.py` là test đỏ, không phải trang nói sai lặng lẽ.

### 3.2 Bảng nguồn

| Khối | Nguồn | Sinh thế nào |
|---|---|---|
| Bốn tầng | ảnh chụp ← `db/migrations/*.sql` | Regex `CREATE (OR REPLACE )?(TABLE|VIEW|MATERIALIZED VIEW) (IF NOT EXISTS )?(raw|core|mart|app|meta)\.(\w+)` trên mọi file, bỏ những gì bị `DROP TABLE/VIEW` ở migration SAU đó. Tầng `raw` là thư mục file (`raw_archive/`), không phải schema — mô tả cố định. Mỗi tầng: mã, tên, một câu mô tả (hằng trong `kome/tai_lieu.py`, 4 câu — đây là phần văn xuôi duy nhất viết trong code), danh sách bảng/view sinh ra, số lượng |
| Bảy nguồn từ OBC | lúc chạy ← `files.yml` + `coverage` | Mỗi spec: `display_name`, mô tả tiếng Việt (`coverage.COT[*].mo_ta`; `meisai` không có trong `COT` → "bán hàng (nguồn dự phòng)" lấy từ một hằng có chú thích), mẫu tên file, `header_row`, `keys`, `core_table`, tần suất ("hằng ngày 13:30" nếu khoá coverage thuộc `KHOA_NGAY`, còn lại "vài lần mỗi năm"). Bên dưới: `coverage.THIEU_BO_NAP` thành bảng "OBC có, chưa nạp" |
| Đối chiếu bắt buộc | ảnh chụp ← `kome/gates.py`; lúc chạy ← `files.yml` | Tên cổng: hằng mới `kome.gates.TEN_CONG` + `CHAN` (bản đầu tách chú thích `# Cổng N — …` ra câu cụt, nên đổi sang hằng khai tường minh; test canh mọi số cổng `check()` phát ra đều có tên). Ngưỡng từng file: `min_rows`, `warn_row_drop_ratio`, `warn_total_spike`, `warn_total_drop`, `product_check`, `required_date_columns`, `dedup_on_keys` |
| Cạm bẫy riêng của OBC | ảnh chụp ← `CLAUDE.md` | Mục `## Bẫy đã biết`: mỗi mục đánh số `N. ` tới hết đoạn (dòng thụt lề nối tiếp gộp vào). Giữ nguyên văn |
| Lộ trình | ảnh chụp ← đặc tả lộ trình §7 | Bảng markdown đầu tiên sau `## 7. Lộ trình`: cột Đợt · Nội dung · Màn · Dữ liệu mới |
| Ma trận khoá | lúc chạy ← `files.yml` | Hàng = spec; cột = **khoá chung**: mọi cột là `keys` của ít nhất một spec, hoặc là đích của một `references`. Ô: `◆` khoá chính (trong `keys`), `●` khoá ngoại (trong `references`), `○` có cột nhưng không phải khoá, trống = không có |
| File này nối đi đâu | lúc chạy ← `files.yml` | Hai danh sách: "trỏ ra" (`references` của file đang chọn) và "được trỏ vào" (spec khác có `references` tới file này) |
| Cột trong từng file | lúc chạy ← `files.yml` | Mỗi cột: tên OBC · tên hệ thống · kiểu (mã/tiền/số lượng/tỷ lệ/ngày/chữ — suy từ các danh sách `*_columns`) · vai (◆/●/—) · nối tới (spec đích nếu là khoá ngoại) |

Văn xuôi Markdown (`**đậm**`, `` `mã` ``) trong ảnh chụp hiển thị bằng một hàm nhỏ
`md_dong(chuoi) -> Markup`: **escape toàn bộ trước**, rồi mới thay hai mẫu đó bằng
`<strong>`/`<code>`. Không thư viện markdown, không `|safe` trên chuỗi thô.

### 3.3 Hai trường mới trong `config/files.yml`

- **`core_table: <schema.bảng>`** — bảng đích chính. Bắt buộc với mọi spec.
  Test canh: `core_table == pipeline.UNDO_TABLES[tên][0]` với mọi spec (test chạy ở
  máy có pandas). Không nhập `kome.pipeline` từ web — lý do tồn tại của trường này.
- **`references: {<cột>: <tên spec đích>}`** — khoá ngoại theo nghĩa nghiệp vụ.
  Mặc định `{}`. Test canh: cột phải có trong `columns` của chính spec, spec đích
  phải tồn tại, và cột đó (hoặc, với `billing_customer_code`, cột khoá của đích)
  phải là `keys` duy nhất của spec đích. Cụ thể: tên cột nguồn KHÔNG cần trùng tên
  khoá đích (`billing_customer_code → tokuisaki` trỏ vào `customer_code`); đích phải
  có đúng một khoá.

Khai báo ban đầu (đối chiếu `docs/data-linkage.md` §1–2):

| Spec | `references` |
|---|---|
| zaiko | `product_code → shohin` |
| tokuisaki | `billing_customer_code → tokuisaki` |
| uriage | `customer_code → tokuisaki`, `billing_customer_code → tokuisaki`, `product_code → shohin`, `shipto_code → chokusousaki` |
| meisai | `customer_code → tokuisaki`, `product_code → shohin` |
| chokusousaki | `customer_code → tokuisaki` |
| tanka | `product_code → shohin` |
| shohin, shiiresaki | — |

`salesperson_code`, `warehouse_code`, `pack_code` không có spec làm master (người phụ
trách và kho không có file xuất riêng) nên KHÔNG khai làm `references` — chúng vẫn
hiện trong ma trận khi là `keys` của ai đó (`warehouse_code` của `zaiko`,
`pack_code` của `tanka`).

`FileSpec` thêm hai trường tương ứng (`core_table: str | None = None` để test cũ
tạo spec tay vẫn chạy; test mới đòi mọi spec trong `files.yml` có giá trị).

---

## 4. Thành phần

| File | Việc |
|---|---|
| `kome/tai_lieu.py` | Hàm thuần: `bon_tang(anh)`, `nguon_obc(specs)`, `doi_chieu(anh, specs)`, `cam_bay(anh)`, `lo_trinh(anh)`, `ma_tran(specs)`, `noi_di_dau(specs, ten)`, `cot_cua(specs, ten)`, `md_dong(s)`, `doc_anh_chup()`. Không nhập pandas/pipeline/db |
| `scripts/sinh_tai_lieu.py` | `sinh() -> dict` (dùng lại được trong test) + `main()` ghi file |
| `kome/web/tai_lieu_sinh.json` | Ảnh chụp đã commit |
| `kome/web/templates/kho_du_lieu_luong.html`, `kho_du_lieu_cot_noi.html`, `_tab_kho_du_lieu.html` | Hai trang + dải tab (include cả ở `kho_du_lieu.html`) |
| `kome/web/app.py` | Hai route GET, `trang="kho-du-lieu"` để sidebar sáng đúng mục |
| `kome/web/static/kome.css` | Chỉ thêm lớp nếu cần (ma trận ô); không mã màu mới ngoài bảng biến |

## 5. Lỗi

- Ảnh chụp thiếu/hỏng lúc chạy → khối tương ứng hiện một dòng "chưa sinh tài liệu —
  chạy `python scripts/sinh_tai_lieu.py`", các khối lấy từ `files.yml` vẫn vẽ. Không
  trang lỗi.
- `?file=` lạ → mặc định `uriage`.

## 6. Test

| Test | Chặn gì |
|---|---|
| `test_anh_chup_tai_lieu_khong_cu` | Ảnh chụp cũ so với nguồn |
| `test_core_table_khop_undo_tables` | Hai khai báo bảng đích trôi khỏi nhau |
| `test_references_hop_le` | Khoá ngoại trỏ vào cột/spec không tồn tại |
| `test_cam_bay_dem_bang_so_muc_trong_claude_md` | Bộ tách bỏ sót mục nhiều dòng |
| `test_bon_tang_co_view_moi_nhat` | Ví dụ `mart.thang_den_hom_nay` (029) phải có trong tầng `mart` |
| `test_moi_cot_tren_trang_co_trong_files_yml` | Render `/kho-du-lieu/cot-noi?file=X` cho mọi spec; mọi tên cột OBC trong `<td>` của bảng cột đúng bằng `columns` |
| `test_trang_tai_lieu_khong_truy_van` | `open_conn` bị thay bằng hàm nổ — trang vẫn 200 |
| `test_trang_tai_lieu_khong_can_pandas` | Cùng nếp `test_trang_chi_doc_khong_phu_thuoc_pandas` |
| `test_md_dong_escape_truoc` | `<script>` trong nguồn ra `&lt;script&gt;` |
| `test_file_la_ve_mac_dinh` | `?file=khong-co` → 200, hiện `売上伝票データ` |
| `test_tab_danh_dau_trang_dang_xem` | `aria-current` đúng tab |

## 7. Ngoài phạm vi

Đường cong SVG nối cột của gói thiết kế (thay bằng hai danh sách) · số dòng/ngày cập
nhật từng bảng (đã có ở khối sức khoẻ của `/kho-du-lieu`; ở đây là 0 truy vấn) ·
mọi thay đổi pipeline.

## 8. Tài liệu cập nhật

`CLAUDE.md` bảng trang: thêm hai dòng; ghi bất biến ảnh chụp (§3.1). `docs/runbook.md`:
một dòng "sửa migration/CLAUDE.md → chạy `python scripts/sinh_tai_lieu.py`".
