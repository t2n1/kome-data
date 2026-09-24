# Kho dữ liệu theo gói thiết kế + "Cột nào bỏ được"

Chủ doanh nghiệp (2026-09-24): màn Kho dữ liệu chưa theo `Kho dữ liệu.dc.html`; và muốn thấy
"mục nào trong dữ liệu web app đang lấy, nối với cột nào" — **mục đích: quyết định cột nào bỏ
khỏi bản xuất OBC lần sau**. Đã duyệt: theo trọn thiết kế (nạp hai bước) + màn đường đi từng cột.

Ba đợt: **A** — màn "Dữ liệu đi đâu" (`/kho-du-lieu/duong-di`) · **B** — khung thanh trái +
Tổng quan + Nạp hai bước · **C** — xem từng bảng. Tài liệu này chốt đợt A; B/C ghi hướng.

## A. Dữ liệu đi đâu — mỗi cột OBC một phán quyết

### A.1 Bốn loại (xét theo thứ tự, loại đầu tiên khớp thắng)
| Mã | Nhãn | Điều kiện | Bỏ được? |
|---|---|---|---|
| `nap` | Bộ nạp cần | cột hệ thống là khoá (`keys`), `total_column`, `product_check`, `required_date_columns`, hoặc được nhắc trong mã nạp (`kome/pipeline.py`, `reader.py`, `gates.py`, `so_cai.py`, `archive.py`) | Không |
| `man` | Màn hình đang dùng | cột `core` được một view `mart` đọc (trực tiếp hay qua view khác) mà view đó có màn đọc, **hoặc** một mô-đun màn hình có nhắc bảng `core` đó và nhắc tên cột | Không (mất số trên màn) |
| `luu` | Nạp vào kho, chưa màn nào dùng | còn lại, có khai báo trong `files.yml` | Được, sau khi sửa `files.yml` (không sửa thì cổng 2 chặn cả file) — mất lịch sử cột từ ngày bỏ |
| `khong_nap` | Có trong file, kho không nạp | có trên dòng tiêu đề file mẫu, không có trong `files.yml` | Được ngay |

**Sai nguy hiểm duy nhất là báo `luu` cho cột đang dùng**, nên mọi phép dò nghiêng về "đang dùng":
dò chữ trong mã Python (đếm là dùng cả khi chỉ trùng tên), view không màn nào đọc vẫn ghi ra.

### A.2 Nguồn — sinh, không chép tay
- OBC → hệ thống: `files.yml.columns`. Cột hệ thống → cột `core`: cùng tên trong `core_table`;
  ngoại lệ khai ở `LUU_RIENG` của script (bảng giá xoay 10 mức → `price_ex_tax`/`price_in_tax`;
  tên kho → `core.dim_warehouse`). **Test canh**: mọi cột hệ thống phải tìm được cột `core` hoặc
  nằm trong `LUU_RIENG` — không thì đỏ (buộc người sửa loader khai báo lại).
- `core` → `mart`: danh mục Postgres (`pg_depend` qua `pg_rewrite`, chính xác tới cột), đóng bao
  qua view đọc view; hàm `mart.*` (LANGUAGE sql — `pg_depend` không ghi thân hàm) dò chữ trong
  `prosrc`. Hạn chế in trên màn: chỉ biết "view X dùng cột Y", không biết cột nào của X.
- `mart`/`core` → màn: quét `kome/**/*.py`; mô-đun → màn khai ở `MAN` của script. **Test canh**:
  mọi mô-đun nhắc `mart.`/`core.` phải có trong `MAN` hoặc `MA_NAP`.
- Tiêu đề file thật: `config/obc_tieu_de.json`, sinh bằng `--doc-tieu-de` từ file mới nhất của
  `raw_archive*/` (CHỈ dòng tiêu đề). Không có file mẫu → màn nói "chưa có file mẫu" cho loại ⚪.
- Tất cả chụp vào `kome/web/cot_dung_sinh.json` (`python scripts/sinh_cot_dung.py`, cần
  `DATABASE_URL_TEST` đã migrate). Màn chạy **0 truy vấn**. Test canh ảnh chụp không cũ.

### A.3 Màn
Chọn file · bảng cột (huy hiệu loại, cột `core`, view, màn, lý do) · lọc "chỉ cột bỏ được" · tìm ·
tải CSV danh sách bỏ được · hình đường đi 4 cột (OBC → core → mart → màn, bấm để sáng) · sơ đồ
nối khoá (`files.yml.references` + khoá ngoại thật). Tab thứ tư của dải tab Kho dữ liệu.

## B. Khung + Tổng quan + Nạp hai bước (đã làm)
- Khung: `TabKho.tsx::KhungKho` — thanh trái 5 mục (Nạp ẩn ở bản chỉ-đọc); dưới 860px thành dải ngang.
- Tổng quan: sơ đồ 8 nguồn (`kho_du_lieu.O_NAP`; nhịp 'ngay' đọc `tinh_tuoi`, 'nen'/'ky' không bao giờ
  đỏ) · 4 ô số (một câu `pg_class.reltuples` — "khoảng") · lưới theo ngày MỘT tháng (`?ngay_thang=`,
  tái dùng `coverage.tinh_bang_ngay`) · DaiTuoi / sức khoẻ / bảng tháng giữ nguyên (thiết kế không có
  chỗ, lệch có chủ ý). "Nạp hôm nay" tính theo giờ Tokyo.
- Nạp: `pipeline.kiem` = `_chuan_bi` (5 cổng) của `ingest`, không ghi. File chờ: `kome/nap_cho.py` (mã
  32 hex kiểm dạng; tên file chỉ lấy phần tên). Xác nhận chạy lại `ingest` đầy đủ; bấm hai lần → "file
  chờ không còn". Năm dòng cổng: cổng 1/2 chặn thì cổng sau "không chạy".

## C. Xem từng bảng (đã làm)
- `/kho-du-lieu/bang/<schema.bảng>` (vỏ React) + `/api/kho-du-lieu/bang[/{tên}[/dong|/csv]]`
  (`kome/bang_kho.py`). Tabs: Dữ liệu (tìm trên cả dòng `t::text ILIKE`, 50 dòng/trang, "Tháng gần
  nhất" = từ mùng 1 của tháng có giá trị lớn nhất ở cột ngày đầu tiên, "Lô mới nhất" = `max(batch_id)`
  của chính bảng; "Có cảnh báo" để mờ — cổng kiểm cảnh báo theo LÔ, không đánh dấu dòng) · Cột & khoá
  (danh mục + tên gốc OBC từ files.yml) · Lần nạp (30 lô của các file đổ vào bảng; hoàn tác vẫn ở màn
  Nạp — nơi có câu "xoá bao nhiêu dòng"). "Tải Excel" của thiết kế → CSV có BOM (Excel mở thẳng; bản
  Vercel không có thư viện ghi .xlsx).
- An toàn: vai trò `kome_app`, `READ ONLY`, `statement_timeout` 20 s; tên bảng tra danh mục +
  `has_table_privilege`, rồi `sql.Identifier`; `app` bị loại. Đo thật (CSDL thật, chỉ đọc):
  fact_sales_line 291k dòng trang đầu 0,4 s (đếm riêng — `count(*) OVER ()` là 6,1 s), khach_360 1,6 s,
  san_pham_360 2,5 s.
- Màn xem bảng đọc `SELECT t.*` của bảng bất kỳ — nó KHÔNG phải một "chỗ dùng" cột theo nghĩa của §A
  (không hiện số nào cho nghiệp vụ), nên phép dò "cột nào bỏ được" không tính nó.
