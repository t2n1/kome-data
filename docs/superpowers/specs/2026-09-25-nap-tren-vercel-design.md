# Nạp dữ liệu hằng ngày trên bản Vercel — đặc tả

Ngày: 2026-09-25 · Chủ DN chốt: nạp HẰNG NGÀY trên Vercel (phương án A), KHÔNG giữ file gốc
trên Vercel (phương án C), bật luồng nạp có sẵn (cách 1).

## 1. Vì sao, và phạm vi

Bản Vercel đang chỉ-đọc (`kome/web/app.py::_chi_doc` = `bao_mat.tren_mang()`), nên nhân
viên phải mở máy trong công ty mới nạp được file 13:30. Lý do cũ có ba: giới hạn 4,5 MB
mỗi yêu cầu, ổ đĩa tạm, nạp một quý ~88 s. Đo lại trên `raw_archive/` (2026-09-25):

| File | Cỡ thật |
|---|---|
| 仕入先 · 在庫一覧 · 取引単価 · 商品 · 直送先 | 10 KB – 320 KB |
| 得意先全情報 | ~2,5 MB |
| 売上伝票データ **một quý** (đối soát) | 63 – 106 MB |

Con số ~100 MB là file CẢ QUÝ; file bán hàng một ngày ≈ 1 MB. Vậy luồng hằng ngày lọt
dưới 4,5 MB. **Trong phạm vi:** nạp hai bước (Kiểm → Xác nhận / Huỷ), nạp một bước
`POST /upload`, hoàn tác `POST /undo/{lô}` — trên Vercel, cho file ≤ 4,5 MB.
**Ngoài phạm vi:** đối soát tháng / nạp lại cả quý (file lớn) — vẫn ở máy công ty; tải
file thẳng lên Supabase Storage; lưu file gốc trên Vercel.

## 2. Kho file — một lớp, hai kiểu

Hai chỗ đang ghi ổ đĩa: lớp `raw` (`kome/archive.py::store` chép file gốc vào
`raw_archive/`, không ai đọc lại — chỉ để lưu vết) và file chờ xác nhận
(`kome/nap_cho.py`, thư mục `_cho_xac_nhan/`). Trên Vercel, bước Xác nhận có thể chạy
trên một phiên bản hàm khác bước Kiểm, nên thư mục tạm không dùng được.

**File chờ** — `kome/nap_cho.py` giữ nguyên giao diện hàm (`luu`, `doc`, `xoa`,
`danh_sach`, `don_cu`) nhưng nhận một **kho** thay cho `archive_dir`:
- `KhoDia(archive_dir)` — đúng hành vi hiện nay (máy công ty).
- `KhoCsdl(open_conn)` — bảng `meta.nap_cho` (migration mới `045_nap_cho.sql`):
  `ma text PK` (32 hex, kiểm dạng như nay), `ten_file text`, `o text`, `noi_dung bytea`,
  `luc timestamptz default now()`. `doc` ghi nội dung ra một file trong thư mục tạm của
  lượt gọi rồi trả đường dẫn đó (pipeline vẫn đọc từ `Path`, không đổi). `xoa` = `DELETE`.
  `don_cu` = `DELETE … WHERE luc < now() - 24 giờ`. `danh_sach` không đọc cột `noi_dung`.
- Kiểu kho chọn bằng biến `KOME_KHO_NAP` (`dia` | `csdl`); mặc định `csdl` khi
  `bao_mat.tren_mang()`, `dia` ở nơi khác. Một chỗ quyết định, trong `create_app`.

**Quyền:** `kome_ingest` không có DELETE trên `meta` (bất biến 009 — `meta.ingest_batch`
là sổ lịch sử). Migration 045 cấp `SELECT, INSERT, DELETE` trên ĐÚNG bảng `meta.nap_cho`
cho `kome_ingest`, không đụng quyền mặc định của schema. `kome_app` không có quyền gì trên
bảng này (file chờ là dữ liệu kinh doanh thô chưa qua cổng). Migration chạy bằng
`postgres` như mọi migration.

**File gốc** — `archive.store` nhận `archive_dir: Path | None`. `None` = không chép file,
`archived_to` = NULL. Migration 045 `ALTER COLUMN archived_to DROP NOT NULL`; NULL nghĩa
là "nạp ở nơi không lưu file gốc". Mã băm (`digest`) và số dòng vẫn ghi như cũ nên chặn
nạp trùng (`already_loaded`) vẫn chạy. `pipeline._huy_lo_hong` đã bỏ qua `archived_to`
rỗng (`if row and row[0]`) — thêm test canh. Màn Xem bảng / lô nạp hiện ô trống cho NULL
kèm chú thích "không lưu file gốc (nạp trên web)".

## 3. Giới hạn cỡ và quyền

- **Trình duyệt kiểm cỡ trước khi gửi** (màn nạp, `giao_dien/src/he_thong/`): file
  > `GIOI_HAN_WEB` (4 MB — chừa phần đầu biểu mẫu multipart dưới trần 4,5 MB) bị chặn ngay
  ở ô, câu: "File này X MB — quá lớn cho bản web (tối đa 4 MB). Nạp ở máy trong công ty."
  Giới hạn chỉ áp khi máy chủ báo `gioi_han_tai_len` trong `window.__KOME__` (Vercel);
  máy công ty không có giới hạn này.
- **Ô "Nạp nhiều file"** gửi TỪNG FILE một yêu cầu `POST /upload/kiem` khi có giới hạn,
  gộp kết quả ở trình duyệt, để tổng một yêu cầu không vượt trần. Xác nhận gửi danh sách
  mã (nhỏ) như hiện nay.
- Máy chủ vẫn phải chịu được yêu cầu vượt trần mà trình duyệt lọt: Vercel trả 413 trước
  khi tới ứng dụng — màn nạp hiện câu tiếng Việt cho mã 413 thay vì trang lỗi trần.
- **Quyền:** không đổi — `/upload*` và `/undo/*` vẫn sau `duoc_vao_kho_du_lieu`
  (middleware), và Vercel luôn bắt đăng nhập (`KOME_SESSION_SECRET` bắt buộc), nên cổng
  quyền ở Vercel chặt hơn máy công ty. Vercel cần thêm biến `DATABASE_URL`
  (`kome_ingest_user`, cổng **6543**). Bộ nạp không dùng `SET`, khoá phiên, bảng tạm hay
  `COPY` (đã soát) — mỗi bước là một giao dịch đóng, hợp transaction pooler.

## 4. Những thứ đi theo

- **`_chi_doc`** chỉ còn theo `KOME_CHI_DOC`; bỏ nhánh `tren_mang()`. Docstring,
  `server.py`, CLAUDE.md (bảng "Hai bản chạy", đoạn `_chi_doc`, bất biến `POST /ngan-sach`)
  viết lại cho đúng. Thiếu `DATABASE_URL` trên Vercel thì màn nạp báo "bản này chưa cấu
  hình kết nối nạp" (không nổ lúc khởi động — trang đọc vẫn phải lên).
- **`requirements.txt`** thêm `pandas` + `python-calamine` (~120 MB, vẫn dưới trần gói
  500 MB). Bất biến "`app.py` không nhập pipeline / pandas ở mức ngoài cùng" GIỮ NGUYÊN —
  trang đọc không nạp hai thư viện đó, khởi động nguội không chậm thêm vì chúng. Test
  `test_trang_chi_doc_khong_phu_thuoc_pandas` giữ nguyên ý nghĩa; chú thích đầu
  `requirements.txt` viết lại.
- **Làm nóng ảnh chụp** (`anh_chup.lam_nong`) chạy luồng nền — trên Vercel luồng nền bị
  đóng băng khi trả lời xong. Trên Vercel **bỏ qua** làm nóng (người mở trang đầu tiên sau
  nạp chờ lâu hơn một lần); ảnh chụp vẫn KHÔNG bao giờ trả phiên bản cũ vì phiên bản đổi
  theo lô nạp — đúng đắn không phụ thuộc làm nóng.
- **Thời gian chạy:** đo trên bản Vercel thật một lượt nạp `得意先全情報` (file lớn nhất
  hằng ngày, SCD2 ghi từng dòng đổi) và một file bán hàng một ngày. Vượt 60 s thì thêm
  `vercel.json` đặt `maxDuration` cho `server.py`; ghi số đo vào đặc tả này.

## 5. Kiểm thử

- `KhoCsdl`: lưu → đọc ra đúng byte và tên → xoá; mã sai dạng trả None; `don_cu` xoá dòng
  quá 24 giờ, giữ dòng mới; `danh_sach` không kéo `noi_dung`.
- Luồng hai bước với `KOME_KHO_NAP=csdl`: Kiểm → Xác nhận nạp đúng lô, dòng chờ biến mất;
  Huỷ xoá dòng chờ; Kiểm lỗi cổng không để lại dòng chờ.
- Lô nạp không file gốc: `archived_to` NULL, nạp trùng vẫn bị chặn, hoàn tác chạy,
  `_huy_lo_hong` không nổ.
- `_chi_doc`: có `VERCEL` mà không `KOME_CHI_DOC` → nạp được; `KOME_CHI_DOC=1` → chặn.
- Quyền CSDL: `kome_ingest` xoá được `meta.nap_cho` nhưng vẫn KHÔNG xoá được
  `meta.ingest_batch`; `kome_app` không đọc được `meta.nap_cho`.
- Giao diện: file > 4 MB bị chặn khi có `gioi_han_tai_len`, không bị chặn khi không có.

## 6. Triển khai

1. Chạy `045_nap_cho.sql` bằng `postgres` TRƯỚC khi triển khai.
2. Thêm `DATABASE_URL` (cổng 6543, `kome_ingest_user`) vào biến môi trường Vercel.
3. Triển khai; nạp thử một file master nhỏ, rồi hoàn tác lô đó.
