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

## B, C (hướng, chốt ở đợt đó)
B: thanh trái 4 mục + danh sách bảng; Tổng quan (sơ đồ nguồn 8 nhánh, 4 ô số, lưới ngày theo
tháng có ‹ ›, lưới tháng; giữ dải tuổi dữ liệu / sao lưu / ngày thiếu); Nạp: mỗi loại một ô,
bước Kiểm (5 cổng, không ghi) → Xác nhận (chạy lại `ingest` đầy đủ) / Huỷ; sai ô → chặn.
C: `/kho-du-lieu/bang/<schema.bảng>` — Dữ liệu (tìm, 50 dòng/trang, CSV), Cột & khoá, Lần nạp
(+ hoàn tác); danh sách bảng cho phép là danh mục cố định (chặn chèn tên).
