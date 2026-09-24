# Mốc thời gian dời được — "mọi thứ quay về tháng đó"

Chủ doanh nghiệp (2026-09-24), sau đợt khoảng xem: chọn tháng cũ thì **mọi thứ** (trạng thái
khách, cần gọi, hạng, nhịp mua, tồn, công nợ, dự báo…) phải như vào cuối tháng đó, không chỉ
số bán hàng. Tồn kho không có ảnh chụp lúc đó → **nói rõ là không có** (không lấy ảnh chụp gần
nhất).

## 1. Cách làm

Mọi chỉ số "tính đến hôm nay" của `mart` neo vào MỘT chỗ: `mart.moc_thoi_gian.hom_nay` (ngày
bán mới nhất). Migration `040` cho mốc đó **dời được trong một giao dịch**:

- `mart.moc_lui()` — ngày mốc đang xem LÙI VỀ, hoặc NULL (= hiện tại). Đọc tham số giao dịch
  `kome.moc` (`set_config('kome.moc', 'YYYY-MM-DD', true)` — `true` = CHỈ trong giao dịch
  hiện tại; `SET` cấp phiên bị pooler giữ lại sang kết nối sau, xem sự cố 2026-09-24). Mốc
  ≥ ngày bán mới nhất ⇒ NULL (xem tháng hiện tại = y như không dời).
- `mart.ban_den_moc` — `core.fact_sales_line` chỉ gồm dòng `sales_date ≤ mốc`. Mọi view từng
  đọc thẳng bảng bán (`dong_ban`, `lan_mua`, `khach_chua_mua`, `khach_mat_hang`,
  `khoang_cach_mat_hang`, `san_pham_360`, `toc_do_ban`) đọc view này thay — `CREATE OR REPLACE`,
  cùng cột, **không đổi công thức nào**. Mọi thứ dựng trên chúng (nhịp mua, trạng thái, hạng 12
  tháng, nhóm việc, tháng này chưa mua, cần liên hệ, tải nhân viên, bản đồ, dự báo…) tự quay về.
- `mart.moc_thoi_gian.hom_nay` = ngày bán mới nhất **≤ mốc**.
- `mart.ton_hien_tai` = ảnh chụp tồn mới nhất **≤ mốc** (không có ⇒ không dòng nào ⇒ màn nói
  "chưa có ảnh chụp tồn tại thời điểm này"). `mart.so_cong_no_moi_nhat` = sổ có kỳ kết thúc
  muộn nhất **≤ mốc**.

Không đặt mốc ⇒ mọi view y hệt trước `040` (có test canh).

## 2. Mốc của khoảng xem

Mốc = ngày cuối của khoảng, suy **theo cú pháp** (`ThamSo.moc()`, không hỏi CSDL): tháng →
ngày cuối tháng; kỳ → 31/7 của kỳ; khoảng → `den`; không tham số → không dời.
`khoang_xem.giai_conn` đặt mốc và đọc dải dữ liệu trong **một** lượt hỏi; màn không giải khoảng
dùng `khoang_xem.dat_moc` (+1 lượt, chỉ khi có tham số khoảng — mặc định 0 lượt, nên ngân sách
lượt hỏi của mọi màn ở chế độ mặc định không đổi).

## 3. Không quay về (có chủ ý, màn nói ra)

- Tên khách / người phụ trách / danh mục: bản hiện hành (`is_current`).
- Tạm ẩn sau khi liên hệ, "hẹn gọi lại hôm nay", ô "hôm nay đã nạp chưa": đồng hồ thật.
- Chỉ tiêu ngân sách: theo tháng như cũ.

## 4. Màn

Thanh KHOẢNG XEM bật ở MỌI màn nghiệp vụ, kể cả Kho hàng, Công nợ, Cần liên hệ, Dự báo. Nhãn
"hôm nay" của các khối đổi thành "đến <mốc>" khi đang xem lùi.

## 5. Kiểm

Đẳng thức vàng: **mốc D ≡ như thể kho chỉ có dữ liệu tới D** — tính các view với mốc D, rồi xoá
thật các dòng bán sau D, tính lại không mốc: phải bằng nhau (`khach_360`, `khach_nhom_viec`,
`khach_thang_nay`, `uu_tien_lien_he`, `khach_mat_hang`, `hang_doanh_thu`, `toc_do_ban`,
`tai_nhan_vien`, `khach_theo_tinh`). Không mốc = như cũ. Tồn / công nợ trước ảnh chụp đầu
tiên = rỗng. `set_config(…, true)` hết hiệu lực sau giao dịch.
