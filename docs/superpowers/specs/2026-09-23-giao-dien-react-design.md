# Giao diện ứng dụng trình duyệt (React) — bám sát gói thiết kế

**Ngày:** 2026-09-23 · **Người quyết:** chủ doanh nghiệp (chọn trong phiên làm việc)
**Thay thế:** nguyên tắc "không JavaScript / máy chủ vẽ HTML" của lộ trình §5 (hàng "Công nghệ
giao diện") và của mọi đặc tả đợt 1–8. Mọi bất biến SỐ LIỆU trong `CLAUDE.md` giữ nguyên.

## 1. Vì sao

Chủ doanh nghiệp so app thật với gói thiết kế (`design_handoff_kome`) và thấy "khác xa nhau, UX/UI
không giống, tính năng cũng khác". Bảng so từng màn (phiên 2026-09-23, 7 phần) cho thấy nguyên nhân
lớn nhất lặp ở mọi màn là **kiến trúc**: gói thiết kế là ứng dụng chạy trên trình duyệt (tab đổi
tức thì, lọc khi gõ, sắp xếp khi bấm tiêu đề, ô nổi, kéo thả), còn app vẽ HTML ở máy chủ nên mọi
thao tác là một lượt tải trang. Hai nguyên nhân còn lại — thiếu nguồn dữ liệu, và bố cục/mật độ
làm sơ sài — thì một cái không sửa được bằng code, một cái sửa được ở mọi màn.

README của gói thiết kế gợi ý đúng stack: **React + TypeScript + Vite**, TanStack Query cho dữ
liệu, chart nhẹ.

## 1b. Bốn mục tiêu (lời chủ doanh nghiệp: "đẹp, load nhanh, tương tác graph được, dữ liệu chuẩn")

Bản cũ bị chê "vừa xấu vừa chậm, không khác gì coi dữ liệu thô". Mỗi mục tiêu có thước đo, và
giai đoạn nào cũng phải đạt cả bốn trước khi coi là xong:

| Mục tiêu | Thước đo |
|---|---|
| **Đẹp** | Đặt cạnh bản mẫu ở 1440px, sáng + tối: cùng bố cục, cùng mật độ, cùng kiểu biểu đồ. Không bảng số trần nào ở nơi bản mẫu vẽ biểu đồ |
| **Nhanh** | Mở màn (đã có cache trình duyệt): khung hiện < 300 ms, mọi khối có số < 1 s trên CSDL thật. Mỗi endpoint p50 < 300 ms đo trên CSDL thật. Đổi tab/lọc/sắp xếp: tức thì, không gọi máy chủ khi dữ liệu đã có |
| **Biểu đồ tương tác** | Mọi biểu đồ: di chuột/chạm → ô nổi đúng số; bấm chú giải bật/tắt chuỗi; biểu đồ theo thời gian đổi được khung (7N/30N/90N/1N…); bấm vào cột/ô/đoạn → đi tới danh sách đã lọc đúng thứ đó |
| **Dữ liệu chuẩn** | Mọi số từ `mart` qua đúng các hàm hiện có; mọi bất biến `CLAUDE.md` và toàn bộ test số liệu giữ nguyên; không số mẫu ở bất cứ đâu |

**Nhanh ở máy chủ, không chỉ ở trình duyệt.** Đo thật 2026-09-23 (CSDL thật, chỉ SELECT, vai trò
`kome_app`): `kome.tong_quan.tong_quan()` — cả trang `/` hiện nay — mất **9.039 ms**; riêng
`count(*)` trên `mart.khach_nhom_viec` 2.151 ms, `mart.san_pham_360` 1.591 ms,
`mart.tien_do_ngan_sach` 1.508 ms; một lượt hỏi trống 50–240 ms.

Dữ liệu chỉ đổi khi: nạp, hoàn tác, sửa ngân sách, ghi tiếp xúc, và (với vài khối) khi sang NGÀY
MỚI giờ Tokyo. Nên kết quả của mỗi endpoint được **lưu sẵn theo phiên bản dữ liệu**:

- Bảng `app.anh_chup_api(khoa, phien_ban, du_lieu jsonb, tinh_luc, tinh_ms)` (migration mới).
- `phien_ban` = một chuỗi ghép từ `max(batch_id)` + `max(undone_at)` của `meta.ingest_batch`,
  `max(sua_luc)` của `app.ngan_sach_nhat_ky`, `max(id)` của `app.nhat_ky_tiep_xuc`, và ngày Tokyo —
  đọc CÙNG lượt hỏi với việc tra ảnh chụp (một round-trip khi trúng).
- Trúng → trả `du_lieu`. Trượt → tính bằng đúng hàm cũ, ghi đè, trả. Không bao giờ trả ảnh chụp của
  phiên bản cũ: **số không bao giờ cũ hơn dữ liệu**.
- Sau nạp / hoàn tác, máy công ty **tính sẵn** mọi khối không tham số (chạy nền, nuốt lỗi — luồng
  13:30 không được hỏng vì bước làm nóng), nên người đầu tiên mở trang cũng không chờ.
- Test số liệu cũ không đổi (không đụng view `mart`); test mới canh: phiên bản đổi đúng khi từng
  nguồn đổi, và kết quả qua ảnh chụp BẰNG kết quả tính thẳng.
- Thêm: gzip cho JSON, `ETag` = phiên bản để trình duyệt nhận `304` khi dữ liệu chưa đổi.

Chọn cách này thay vì `MATERIALIZED VIEW`: đổi tên view để vật hoá làm các view phụ thuộc vẫn trỏ
view cũ (Postgres gắn theo OID), `REFRESH` cần quyền chủ sở hữu (`postgres`), và hàng trăm test nạp
dữ liệu rồi đọc `mart` ngay sẽ thấy số cũ.

## 2. Ba quyết định của chủ doanh nghiệp

| Câu hỏi | Chọn |
|---|---|
| Thứ tự | **Từng màn một.** Màn nào xong thì thay màn cũ; màn chưa làm vẫn dùng bản Jinja. Luôn có bản chạy được |
| File build | **Commit sẵn vào git** (`kome/web/spa/`). Máy công ty chỉ `git pull`, không cài Node. Vercel không build |
| Khối không có nguồn dữ liệu | **Dựng đúng khung như gói thiết kế**, bên trong ghi "Chưa có dữ liệu — cần <nguồn cụ thể>". Không bao giờ số mẫu |

## 3. Kiến trúc

```
trình duyệt ── GET /<màn đã chuyển> ──▶ FastAPI trả spa/index.html (Jinja: data-theme từ cookie)
           ── GET /assets/*          ──▶ file build (StaticFiles)
           ── GET /api/...           ──▶ JSON, gọi lại ĐÚNG hàm kome/*.py đang có
           ── GET /<màn chưa chuyển> ──▶ template Jinja cũ (như trước)
```

- **Máy chủ** — `kome/web/api.py` (APIRouter `/api`). Mỗi endpoint gọi hàm tính sẵn (`kome.tong_quan`,
  `kome.khach_hang`, …) và trả dataclass → JSON (`date` → ISO, `Decimal` → số). **Không định nghĩa
  lại chỉ số nào ở API hay ở React**: mọi con số vẫn đến từ `mart`. Ngân sách truy vấn đo theo từng
  endpoint, có test đếm như các trang cũ.
- **Cổng đăng nhập** giữ nguyên middleware `chan_cua`. Với `/api/*`, chưa đăng nhập trả **401 JSON**
  (không 303); giao diện chuyển về `/dang-nhap`. Cờ quyền vẫn tra CSDL mỗi lượt.
- **Chế độ sáng/tối** giữ bất biến cookie + render máy chủ: `index.html` là template Jinja nhỏ đặt
  `data-theme` trên `<html>` trước khi React chạy — không có khung hình sai màu.
- **Mã nguồn giao diện** ở `giao_dien/` (Vite + React + TS). `npm run build` ghi vào `kome/web/spa/`
  (được commit). `.vercelignore` loại `giao_dien/` — Vercel chỉ thấy file build, không thấy
  `package.json` nên không nhận nhầm dự án là Node.
- **Chuyển từng màn:** `kome/web/spa.py::MAN_DA_CHUYEN` là tập đường dẫn đã chuyển. Route Jinja cũ
  của màn đó trả `index.html` thay vì template. Thanh điều hướng của CẢ HAI kiểu trang trỏ cùng địa
  chỉ, nên đi qua lại giữa màn mới và màn cũ là một lượt tải trang bình thường.
- **Thư viện:** `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`. **Không thư viện
  biểu đồ**: gói thiết kế tự vẽ SVG/flex, ta chép đúng cách vẽ đó (giống nhất, ít phụ thuộc nhất).
  Không CSS framework: token lấy từ `kome.css` (đã khớp gói thiết kế), style theo file CSS cạnh
  component.

## 4. Bám gói thiết kế đến đâu

- **Bố cục, tương tác, mật độ thông tin: chép gói thiết kế.** Mở bản mẫu cạnh bản dựng (máy chủ tĩnh
  `handoff` trong `.claude/launch.json`) và so từng khối ở 1440px, sáng + tối.
- **Khối/thẻ/nút không có nguồn:** giữ vị trí và khung, nội dung là `<ChuaCoDuLieu can="…"/>`. Nút
  thao tác không nối vào đâu (gửi nhắc thu, tạo đơn nháp, giao cho nhân viên…) hiện ở trạng thái vô
  hiệu kèm lý do — không `alert()` giả như bản mẫu.
- **Lệch có chủ ý vẫn giữ** (mỗi màn liệt kê ở đặc tả con): tên kho thật (bẫy #6); "hạng theo doanh
  thu 12 tháng"; không % xác suất bịa ở Dự báo; màu luôn kèm chữ; sổ tiếp xúc chỉ thêm; bố cục lưu
  máy chủ theo tài khoản (không localStorage); mọi bất biến số liệu của `CLAUDE.md`.

## 5. Giai đoạn 1 — khung chung + Tổng quan

### 5.1 Khung chung
- Thanh bên theo `kome-nav.js`: logo, chuông, ô "Tìm nhanh ⌘K", 6 nhóm / 24 mục đúng thứ tự và icon
  của gói thiết kế. Mục CÓ màn → liên kết; mục chưa có màn → mờ, không bấm được, ghi chú "chưa có".
  Bốn màn bị cắt (lộ trình §4.2) không hiện. Mục Kho dữ liệu / Ngân sách ẩn theo cờ quyền như nay.
  Cuối thanh: người đăng nhập, Đăng xuất, bốn chế độ giao diện.
- **⌘K / Ctrl+K**: bảng lệnh nhảy màn (danh sách tĩnh các màn có thật).
- **Chuông**: chỉ thông báo có nguồn thật — khách cần gọi, lô cận hạn/quá hạn, hôm nay chưa nạp.
- Thành phần dùng chung: tiêu đề trang (h1 1.5rem + phụ đề + nút cùng hàng), thẻ khối, ô KPI có
  sparkline, tab pill, bảng dày (header nền chìm, chữ nhỏ viết hoa), `ChuaCoDuLieu`, định dạng
  `¥1.234.567` và `¥11,7M` như gói thiết kế.

### 5.2 Tổng quan (`/`)
Theo `Dashboard.dc.html`: lời chào + phụ đề ngày/mốc dữ liệu · "XEM THEO VAI TRÒ" (Giám đốc /
Trưởng phòng KD / Kế toán / Kho & giao hàng) · dải tóm tắt việc · thanh bố cục (kéo sắp xếp, đếm
khối đang hiện, "Đặt lại bố cục", "+ Thêm chức năng" mở bảng chọn có tab nhóm + ô tìm) · lưới 3 cột
kéo thả + đổi cỡ góc.

21 khối của gói thiết kế, chia theo nguồn:

| Khối | Nguồn |
|---|---|
| Chỉ số hôm nay (6 ô) | 4 ô có nguồn (doanh thu tháng đến hôm nay, tiến độ ngân sách, kho cần xử lý, khách cần gọi); **Phải thu quá hạn**, **Phải trả 7 ngày** → chưa có dữ liệu |
| Tiến độ ngân sách tháng · Kết quả theo từng tháng · Xu hướng doanh thu (7N/30N/90N/1N) · Sức khoẻ khách hàng · Danh sách khách hàng (không cột nợ) · Sản phẩm sắp hết hạn · Hiệu suất theo ngành hàng · Doanh thu theo sale · Doanh thu × tần suất mua · Số khách đang mua (theo kỳ) · Biên lợi nhuận theo quý (chỉ biên GỘP) · Nạp dữ liệu gần nhất | có — `mart.*`, `meta.ingest_batch` |
| Việc cần làm hôm nay | một phần — gom từ khách cần gọi, hẹn gọi lại, lô cận hạn, chưa nạp hôm nay; ghi rõ công nợ/mua hàng/khiếu nại chưa có |
| Tuổi nợ phải thu · Dòng tiền 8 tuần · Đơn đặt nhà cung cấp · Trả hàng & khiếu nại · Sản phẩm sắp về kho · Thời tiết 7 ngày · Tỷ lệ im lặng theo tuần | chưa có dữ liệu (khung + lý do) |

- Mỗi khối lấy dữ liệu **riêng** (`/api/tong-quan/<khối>`), chỉ khi đang hiện — khối ẩn không tốn
  truy vấn. Mỗi endpoint ≤ 2 truy vấn, có test đếm. Bất biến dashboard cũ giữ: số tổng không lọc
  theo người đăng nhập, riêng "khách cần gọi" lọc theo `sale` (và `?tat_ca=1`).
- **Bố cục** vẫn lưu `app.nguoi_dung.bo_cuc_tong_quan` (034) qua `POST /tong-quan/bo-cuc`;
  `kome/web/bo_cuc.py::KHOI` mở rộng lên đủ 21 khối (bố cục cũ 6 khối đọc tiếp được — chuan_hoa nối
  khối mới vào cuối). Vai trò = một bộ khối hiện sẵn, bấm là áp vào bố cục của mình (vẫn sửa tiếp).

## 6. Các giai đoạn sau (mỗi giai đoạn một đặc tả con, bảng so từng màn làm danh sách phải giống)

2. Khách hàng (danh sách · hồ sơ 360° 5 tab · bản đồ là tab) · 3. Báo cáo · Dự báo · Cần liên hệ ·
4. Sản phẩm · Kho hàng · 5. Kho dữ liệu · Nhật ký · Cài đặt · Đăng nhập. Hết giai đoạn 5 thì xoá
template Jinja, `static/tong_quan.js`, và các test HTML tương ứng (test dữ liệu/API ở lại).

## 7. Kiểm thử

- **pytest**: mỗi endpoint — hình dạng JSON, số truy vấn, 401 khi chưa đăng nhập, cờ quyền; route màn
  đã chuyển trả `index.html` có `data-theme` đúng cookie; mọi test số liệu cũ giữ nguyên.
- **Vitest**: định dạng tiền/số, chuẩn hoá bố cục phía client, logic lọc/sắp xếp.
- Xem tận mắt từng màn cạnh bản mẫu: 1440px + 375px, sáng + tối, không cuộn ngang ở 375px.
- `npm run build` phải sạch; bản build commit khớp mã nguồn (test so dấu vân tay `giao_dien/src` ↔
  `kome/web/spa/.nguon`).

## 8. Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Quên build trước khi commit → máy công ty chạy giao diện cũ | test dấu vân tay ở §7 đỏ |
| Vercel nhận nhầm là dự án Node | `giao_dien/` trong `.vercelignore`; không `package.json` ở gốc |
| Bundle to làm chậm lần mở đầu | chia code theo màn (lazy route); mục tiêu < 250 KB gzip giai đoạn 1 |
| Nhiều khối × một truy vấn mỗi khối | chạy song song; khối ẩn không gọi; đo trên CSDL thật |
