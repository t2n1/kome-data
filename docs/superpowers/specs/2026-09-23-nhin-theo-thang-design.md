# Nhìn theo tháng: khách mua đều mà tháng này chưa mua

Ngày: 2026-09-23 · Trạng thái: đã duyệt (chủ doanh nghiệp) · Migration: `036`

## 1. Lý do
Chủ doanh nghiệp: "Công ty chạy doanh thu theo từng tháng, nên dữ liệu phân
tích cứ chia theo từng tháng — ví dụ tháng này khách này chưa mua hàng."
Các màn hiện tại nhìn theo nhịp mua riêng (im lặng n× nhịp) và theo dải trượt
(12 tháng, 7N/30N/90N); câu hỏi hằng ngày của người phụ trách lại là
"khách quen nào tháng này chưa có đơn".

## 2. Định nghĩa (đã chốt với chủ DN)
Một view: `mart.khach_thang_nay`, mỗi khách có lần mua trong 4 tháng gần nhất
một dòng. "Tháng này" = tháng của `mart.moc_thoi_gian.hom_nay` (bất biến mốc).
"Tháng có mua" = có một phiếu doanh thu thuần > 0 (tháng chỉ có 赤伝 không
tính); doanh thu cộng đủ, kể cả phiếu đỏ.

| Nhãn (xét theo thứ tự) | Nghĩa |
|---|---|
| `khong_goi` | ※廃業※ / ※取引停止※ |
| `da_mua` | tháng này đã có phiếu |
| `tre` | mua ≥ 2/3 tháng trước **và** ≥ 2 tháng trong đó đã có đơn đến cùng ngày này — giờ chưa |
| `chua_toi_ngay` | mua đều, nhưng thường mua muộn hơn trong tháng |
| `khac` | còn lại |

Lựa chọn thay thế đã cân nhắc (đếm trên dữ liệu thật, mốc 31/7/2026, 1.572
khách còn giao dịch): tháng trước có/tháng này chưa 116 · ≥2/3 tháng 86 ·
3/3 tháng 18 · mọi khách chưa mua 553. Chọn ≥2/3.

"Đến cùng ngày": `extract(day) <= ngày của mốc` (tháng ngắn tự kẹp); mốc là
NGÀY CUỐI tháng thì các tháng trước tính trọn tháng. Nhóm này KHÁC nhóm 'im'
(nhịp riêng) — hai tên, không gộp; mỗi khối in câu cách tính
(`kome.khach_thang.CACH_TINH`).

## 3. Các màn
- **Tổng quan** — khối mới `thang_nay_chua_mua` (ngoài 21 khối gói thiết kế):
  bộ đếm toàn công ty, số khách đã mua so với cùng dải ngày tháng trước
  (`thang_truoc_den_ngay`), danh sách `tre` lọc theo người đăng nhập (nút
  "Khách của mọi người"), số `chua_toi_ngay` hiện mờ. 1 truy vấn.
- **Cần liên hệ** — cột thứ tư "Mua đều, tháng này chưa", đi chung câu danh
  sách (vẫn 3 truy vấn). Khách đã ở ba cột nhịp (kể cả đang tạm ẩn) không
  lặp lại; cột ghi "+n khách". Thẻ ghi TB/tháng; ô tổng đầu trang không cộng
  lẫn TB/tháng với doanh thu luỹ kế.
- **Việc hôm nay** — tự nhận 3 thẻ đầu của cột thứ tư.
- **Danh sách khách + hồ sơ** — làm trong giai đoạn 2 React (Khách hàng 360):
  bộ lọc theo nhãn, cột tháng này/tháng trước/TB 3 tháng, lưới 12 tháng.

## 4. Kiểm thử
`tests/test_khach_thang.py`: từng nhãn ở mốc giữa tháng; 赤伝; mốc 30/6 (cuối
tháng ngắn), 29/6, 31/7; khối đếm toàn công ty / danh sách theo sale; ba chỗ
đọc cùng một tập; bỏ trùng với cột nhịp; trang `/lien-he` hiện cột. Ngân sách
truy vấn khối: 1.

## 5. Đo thật
View trên CSDL thật: ~220 ms phía máy chủ (quét `fact_sales_line` một lượt).
Mốc 12/7 mô phỏng: 115 `tre`, 171 `chua_toi_ngay`.
