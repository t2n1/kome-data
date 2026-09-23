# Giai đoạn 2 — Khách hàng 360 (React)

Ngày: 2026-09-23 · Đặc tả cha: `2026-09-23-giao-dien-react-design.md` §6 · Bảng so gói thiết
kế: `Customer 360.dc.html` + `Bản đồ khách hàng.html` · Kèm lời hẹn của đặc tả
`2026-09-23-nhin-theo-thang-design.md` §3 (danh sách + hồ sơ theo tháng).

## 1. Phạm vi
Ba đường dẫn chuyển sang React, CÙNG một màn "Khách hàng" của gói thiết kế:
- `/khach-hang` — tab **Danh sách khách**; `/ban-do` — cùng màn, tab **Bản đồ** (thanh bên
  vẫn có mục "Bản đồ khách hàng" trỏ `/ban-do`). Đổi tab là `pushState`, không tải lại trang,
  và **bộ lọc người phụ trách đi chung** giữa hai tab (bất biến `/ban-do` → `/khach-hang`
  mang `tat_ca`/`nv` được giữ bằng cấu trúc: một trạng thái lọc, hai cách xem).
- `/khach-hang/{mã}` — hồ sơ 360°, năm tab của gói thiết kế.
Template Jinja `khach_hang.html`, `khach_360.html`, `ban_do.html` bị xoá; test HTML của chúng
chuyển sang test API. `POST /khach-hang/{mã}/tiep-xuc` (form) giữ cho `/lien-he` (còn Jinja).

## 2. Quyết định (ruling) khi gói thiết kế đòi thứ không có nguồn
| Gói thiết kế | Làm gì |
|---|---|
| Bản đồ Leaflet toạ độ | **Giữ lưới 47 tỉnh** (bất biến LEFT JOIN, có test; Leaflet đang tạm dừng vì gửi địa chỉ ra ngoài). Bộ chỉ số / chú giải / xếp hạng / theo vùng như `/ban-do` cũ |
| Công nợ (ô KPI, cột "Quá hạn", phân khúc "Nợ quá hạn", tab Công nợ, trục "Thanh toán") | Khung "chưa có dữ liệu — cần sổ công nợ" (đợt 6 hoãn). Không cột rỗng giả |
| Gauge "Sức khoẻ" 4 trục có điểm 0–100 | Không bịa điểm. Thay bằng đồng hồ **im lặng ÷ nhịp mua riêng** (0 → 3×, vùng 1× / 2×) — đúng thước đo trạng thái của hệ thống |
| Loại hình / kênh | OBC chỉ xuất MÃ phân loại, không tên → ô chọn vô hiệu kèm lý do |
| Giao cho nhân viên / Thêm vào danh sách gọi | vô hiệu kèm lý do. **Xuất Excel** → xuất CSV các dòng đã chọn (làm ở trình duyệt, dữ liệu đã có) |
| Giá riêng & chiết khấu | thay bằng **Bảng giá của bậc** (`core.fact_price_list`, đã có); ghi rõ giá riêng chưa có |
| Dự báo đơn: "độ tin cậy %", "Tạo đơn nháp" | danh sách mã sắp đến ngày mua lại (14 ngày, `khach_mat_hang.du_kien_lan_toi`); KHÔNG % (bất biến đợt 8); nút tạo đơn vô hiệu |
| Gợi ý tiếp khách, thẻ tay, ghi chú, ảnh cửa hàng, chat Facebook | khung chưa có. **Thẻ tự động** chỉ từ dữ liệu thật (trạng thái, nhãn tháng, hạng, mua lẻ/thùng) |
| Nhóm hàng theo tiền tố mã | ngành thật `food_category_name` (`kome.bao_cao.NGANH_TRONG` cho rỗng) |
| "Đánh dấu xong" | bỏ — việc "đã gọi" là nhật ký tiếp xúc (chỉ thêm) |

## 3. Nhìn theo tháng (lời hẹn 036)
- Danh sách: phân khúc thứ bảy **"Mua đều, tháng này chưa"** (`mart.khach_thang_nay.nhan =
  'tre'`, đếm theo `sale`), bộ lọc `thang=da_mua|tre|chua_toi_ngay|khac`, cột **Tháng này** ·
  **So tháng trước cùng ngày** (thanh + %) · **TB 3 tháng**. So với tháng trước **cùng dải ngày**
  (không trọn tháng — nếp §3.7 của 029): migration `037` thêm cột `dt_thang_truoc_den_ngay`
  vào cuối view.
- Hồ sơ: biểu đồ 12 tháng — tháng không mua vẽ ô rỗng có chữ "không mua"; bấm một tháng mở
  bảng mặt hàng của tháng đó (`/api/khach-hang/{mã}/dong?tu=&den=`, gọi khi bấm). Nhãn tháng
  của khách hiện ở đầu hồ sơ và trong thẻ tự động.

## 4. API
| Endpoint | Gọi lại | Lượt hỏi |
|---|---|---|
| `GET /api/khach-hang/ds?tim,loc,nhom,hang(nhiều, phẩy),tinh,nv,tat_ca,thang,sap,giam,trang,co` | `KH.danh_ba` (ảnh chụp) → `KH.tong_quan` + `KH.trang_danh_sach` | **≤ 3** (thực tế 1) |
| `GET /api/khach-hang/{mã}` | `KH.ho_so` → `kome.ho_so_khach.cho_giao_dien` | **≤ 8** (thực tế 7) |
| `GET /api/khach-hang/{mã}/dong?tu=&den=` | dòng bán gộp ngày × mã × quy cách, ≤ 62 ngày | 1 |
| `POST /api/khach-hang/{mã}/tiep-xuc` (chỉ `application/json`) | `LH.ghi` | 1 |
| `GET /api/ban-do?chi_so,nv,tat_ca` | `BD.ban_do` | **2** (bất biến) |

**Đổi so với bản nháp (đo thật trên CSDL thật, 2026-09-23):** lọc bằng SQL thì mỗi
tổ hợp bộ lọc dựng lại `mart.khach_360` — danh sách 3–6 s, khối tổng quan 4–10 s
MỖI cú bấm. Nên: MỘT ảnh chụp danh bạ (~1.710 dòng, ~940 KB JSON, 5–13 s để dựng trên CSDL thật; lọc sau đó ~4 ms) theo
phiên bản CHỈ dữ liệu nạp (`anh_chup.lay(chi_nap=True)` — không cũ đi khi ai đó ghi
tiếp xúc), giữ bản đã giải mã trong tiến trình, lọc / sắp / đếm bằng MỘT bộ lọc
Python `KH._khop`. `danh_sach()` / `tong_quan_danh_ba()` giữ chữ ký, chạy trên cùng
đường đó — test bất biến cũ canh đúng mã màn đang chạy. Làm nóng trong `lam_nong`.

`ho_so` giữ trần 8 bằng cách gộp: "mặt hàng" trả **mọi** mã của khách (kèm `trang_thai_cap`,
ngành, 3 tháng gần nhất) nên khối "đã ngừng mua" không còn câu riêng; "lần mua gần đây" trả mọi
ngày mua trong 400 ngày + 12 lần gần nhất (đủ cho dòng thời gian, lưới 26 tuần, "DT 30 ngày");
hạng doanh thu 12 tháng và tên người phụ trách là hai cột thêm của câu đầu.
Tỷ trọng / biên theo ngành trong hồ sơ là tỷ số của các TỔNG.

## 5. Màn
Danh sách: tiêu đề · 4 ô KPI (khách đang lọc · DT tháng này của nhóm so tháng trước cùng ngày ·
im lặng ≥ 2× nhịp · công nợ chưa có) · 7 phân khúc (toàn bộ, nợ quá hạn [chưa có], im, tụt, mới,
chưa ai phụ trách, tháng này chưa) · thanh lọc (tìm, hạng S–D bật/tắt nhiều, phụ trách, tỉnh,
trạng thái, loại hình [chưa có], xoá lọc) · thanh chọn hàng loạt · bảng sắp xếp ở máy chủ, 50/100/
200 dòng · ba khối phân tích (hạng, tỉnh, tải nhân viên đôi màu).
Hồ sơ: thanh trên (← tất cả, ô chuyển khách, ‹ n/N › theo danh sách vừa xem — nhớ trong
sessionStorage) · đầu hồ sơ (tên, hạng, trạng thái, nhãn tháng, mã · phụ trách · tỉnh · điện
thoại) · câu diễn giải từ số thật · 5 tab như §2.
Bản đồ: như `/ban-do` cũ — ô SVG 47 tỉnh, đổi chỉ số, chú giải bậc, theo vùng, bảng xếp hạng;
bấm ô → tab danh sách lọc tỉnh đó, giữ bộ lọc người phụ trách.

## 6. Kiểm thử
Chuyển test HTML của ba trang sang API (cùng khẳng định số liệu); đếm lượt hỏi từng endpoint;
401 khi chưa đăng nhập; ba route trả `index.html`; `037` giữ nhãn cũ và thêm cột đúng; mã khách
lạ → API 404. Xem tận mắt 1440 / 375, sáng / tối.
