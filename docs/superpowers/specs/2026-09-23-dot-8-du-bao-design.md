# Đặc tả thiết kế — Đợt 8: Dự báo doanh thu

**Ngày:** 2026-09-23 · **Trạng thái:** chủ dự án giao "làm hết" — quyết định ghi ở đây, đã triển khai
**Liên quan:** lộ trình §7 (đợt 8, màn 3) · gói thiết kế `Dự báo.dc.html`.

## 1. Năm khối, đúng thứ tự của gói thiết kế

| Khối | Cách tính (in nguyên câu dưới khối trên màn) | Nguồn |
|---|---|---|
| Chốt tháng (4 ô + đường luỹ kế + theo người phụ trách) | đã bán + (đã bán ÷ ngày làm việc đã qua) × ngày làm việc còn lại | `mart.lich_kinh_doanh`, `mart.ban_theo_ngay`, `mart.tien_do_ngan_sach` |
| Khoảng thấp – cao | sai số nhỏ nhất/lớn nhất của CHÍNH cách tính trên, áp lên các tháng đủ ngày trước ở cùng số ngày làm việc đã qua; < 3 tháng → "—" | như trên |
| 12 tháng tới (thận trọng/cơ sở/lạc quan, `?kb=`) | cùng tháng năm trước × hệ số; cơ sở = **tỷ số của các tổng** trên ≤ 12 tháng đối chiếu; thận trọng/lạc quan = tỷ số tháng thấp/cao nhất | `mart.ban_theo_ngay` |
| Đơn kỳ vọng 14 ngày | khách `binh_thuong` có lần cuối + nhịp riêng rơi vào 14 ngày tới; giá trị = trung bình mỗi lần; "x/y lần mua đúng nhịp" (khoảng cách trong 0,5–1,5× nhịp) | `mart.khach_360`, `mart.khoang_cach_mua` |
| Nguy cơ ngừng mua | khách `canh_bao`/`da_roi_bo` xếp theo doanh thu — CÙNG định nghĩa với `/lien-he` | `mart.khach_360` |
| Dự báo đã chuẩn tới đâu | 6 tháng đủ ngày gần nhất: dự báo chốt tháng lập ở cùng ngày làm việc (hoặc ngày thứ 10 khi tháng này đã đủ ngày) so với thực tế | `mart.ban_theo_ngay` |

## 2. Quyết định
- **Không phần trăm xác suất** ("88% chắc chắn", "72% nguy cơ" của prototype): không đo được. Thay bằng thứ đo được.
- **Không hệ số bịa** (0,88/1,28 của prototype): khoảng là sai số thật.
- **Một định nghĩa ngày làm việc**: migration `031` thêm `mart.lich_kinh_doanh` và cho `mart.ngay_kinh_doanh` đọc lại nó (cùng cột, `CREATE OR REPLACE`).
- **Toàn công ty**, không lọc theo người đăng nhập (cùng nếp các khối số tổng của `/`).
- **3 truy vấn** cả màn; `khach_360` vật hoá đúng một lần (CTE `MATERIALIZED`). Có test đếm.
- "So với năm trước" chia cho tổng cùng các tháng đó năm trước (không cho 12 tháng qua — khác độ dài khi có tháng không dự báo được; lỗi này đã thấy thật khi xem trên dữ liệu giả lập).
- Tháng đầu của kho bắt đầu giữa chừng không làm tháng đối chiếu/kiểm (xét theo lịch vì những ngày trước ngày bán đầu tiên không có dòng).
- Sidebar: "Dự báo doanh thu", icon `target` — đúng ánh xạ `dubao` của `kome-nav.js`.

## 3. Thành phần
`db/migrations/031_lich_kinh_doanh.sql` · `kome/du_bao.py` (tính) · `kome/ve_du_bao.py` (toạ độ SVG) · `templates/du_bao.html` · `kome.css` (khối "Đợt 8") · `_nav.html` · route `GET /du-bao` · `tests/test_du_bao.py`.

## 4. Không làm
Hệ số cuối tháng / tăng trưởng năm chỉnh tay (thanh trượt `heSoCuoiThang`/`tangTruongNam` của prototype — tham số ẩn, trái R2) · mùa vụ Tết/Obon viết cứng · dự báo theo mã hàng.
