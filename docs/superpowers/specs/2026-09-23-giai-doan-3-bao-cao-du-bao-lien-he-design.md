# Giai đoạn 3 — Báo cáo · Dự báo · Cần liên hệ (React)

Ngày: 2026-09-23 · Đặc tả cha: `2026-09-23-giao-dien-react-design.md` §6 · Bảng so gói
thiết kế: `Báo cáo.dc.html`, `Dự báo.dc.html`, `CRM.dc.html`.

## 1. Phạm vi
`/bao-cao`, `/du-bao`, `/lien-he` chuyển sang React (template Jinja đã xoá). Dữ liệu qua:

| Endpoint | Gọi lại | Phiên bản ảnh chụp | Lượt hỏi |
|---|---|---|---|
| `GET /api/bao-cao?ky=` | `tinh_bao_cao` + `tien_do_ngan_sach` + hình học `ve_*` | đầy đủ (đọc `app.ngan_sach`) | ≤ 11 (bất biến) |
| `GET /api/du-bao` | `kome.du_bao.du_bao` + `kome.ve_du_bao` (cả 3 kịch bản) | đầy đủ | 3 (bất biến) |
| `GET /api/lien-he?tat_ca,nv,ly_do` | `LH.danh_sach` + `hoat_dong_gan_day` + `hen_goi_lai` | đầy đủ + ngày Tokyo | 3 (bất biến) |

**Nguyên tắc:** hình học biểu đồ vẫn tính ở Python (`kome/bao_cao.py`, `kome/ve_phan_tich.py`,
`kome/ve_du_bao.py`) — các bất biến đối soát ("không vẽ", cắt đường khi không có cùng kỳ,
kẹp thanh tiến độ, bậc màu 0) đã có test ở đó; React chỉ vẽ và thêm tương tác (chú thích khi
di chuột, đổi kỳ / kịch bản không tải lại trang, bấm cột Pareto mở hồ sơ khách). JSON đi qua
`api.thanh_json` — dataclass KÈM mọi `@property` (`rong_thanh`, `tang_dt`, `lech`, `xong`…).
Bốn số phụ của khối ngân sách (ngày còn lại, cần bán mỗi ngày, nhịp chuẩn, thiếu/vượt mốc)
tính ở MỘT chỗ — `kome.bao_cao.chi_so_phu` — cho cả `/` lẫn `/bao-cao`.

## 2. Quyết định khi gói thiết kế đòi thứ không có nguồn
| Gói thiết kế | Làm gì |
|---|---|
| CRM: Kanban **deal** 5 giai đoạn, "% khả năng chốt", nút Lùi/Tiếp, "＋ Deal mới" | Giữ BỐ CỤC (KPI → cột → "Hoạt động gần đây" \| "Việc cần làm hôm nay"), cột là **lý do cần gọi** (4 cột, gồm cột tháng 036). Không có bảng deal nào — lộ trình §8.2. Thẻ có nút "✏️ Ghi liên hệ" (form chung `GhiTiepXuc`); "Việc cần làm hôm nay" = hẹn gọi lại tới hạn |
| Báo cáo: tab "Lãi gộp" của khối ngân sách | vô hiệu kèm lý do (chỉ có ngân sách doanh thu) |
| Báo cáo: "Khách hiện hữu / khách mới theo kỳ" | khung "chưa có" — mart chưa định nghĩa 既存/新規得意先 theo kỳ |
| Báo cáo: luỹ kế theo NGÀY + điểm dự báo | giữ luỹ kế theo tháng của kỳ (`ve_luy_ke`); luỹ kế theo ngày + dự báo chốt ở `/du-bao` (có liên kết) |
| Báo cáo: nút "Tải Excel" | "⤓ Xuất CSV theo tháng" — làm ở trình duyệt từ số đã có |
| Dự báo: "% chắc chắn", "% nguy cơ", dải ±12% cố định | KHÔNG (bất biến đợt 8) — "x/y lần mua đúng nhịp", "n× nhịp mua riêng", khoảng = sai số thật |

## 3. Làm nóng
`anh_chup.lam_nong` tính sẵn `bao-cao` (kỳ gần nhất) và `du-bao` sau mỗi lần nạp / hoàn tác,
cùng danh bạ khách (giai đoạn 2) và các khối Tổng quan. Hàm dữ liệu ở cấp module
(`api.du_lieu_bao_cao`, `api.du_lieu_du_bao`) để hai đường dùng chung.

## 4. Kiểm thử
Test HTML của ba trang chuyển sang test API (cùng bất biến); câu chữ thuần hiển thị kiểm trên
mã React. Đếm lượt hỏi từng endpoint; 401 khi chưa đăng nhập; ba route trả vỏ React.
