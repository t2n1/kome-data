# Ngân sách công ty theo tháng — doanh thu + lãi gộp

Chủ doanh nghiệp (2026-09-24): màn Ngân sách sai — ngân sách đặt **theo từng tháng, có doanh
thu và lợi nhuận**. Đã chọn: **công ty + từng người**; "lợi nhuận" = **lãi gộp 粗利益**.

## 1. Dữ liệu (migration 041)

- `app.ngan_sach_cong_ty` — mỗi tháng một dòng: `doanh_thu`, `lai_gop` (bigint ≥ 0, mỗi cột
  NULL được — ô trống = chưa đặt, `0` = đặt bằng không; dòng phải có ít nhất một cột). Khoá
  `thang` = date mùng 1, khoá ngoại `core.dim_date` (cùng lý lẽ `app.ngan_sach`).
- `app.ngan_sach` (từng người) thêm `lai_gop`; `muc_tieu` (doanh thu) thôi NOT NULL; dòng
  phải có ít nhất một cột.
- `app.ngan_sach_nhat_ky` thêm `chi_so` (`doanh_thu`/`lai_gop`), `salesperson_code` NULL =
  công ty. Cùng MỘT sổ cho cả hai bảng ⇒ `anh_chup._PHIEN_BAN` không cần thêm gì (đã đọc
  `max(id)` của sổ này), và `/nhat-ky` không cần nhánh mới.
- `mart.ngan_sach_cong_ty_thang` — chỗ DUY NHẤT đổi khoá date → 'YYYY-MM' của bảng công ty
  (cùng nếp `mart.ngan_sach_thang` cho bảng từng người).
- `mart.tien_do_cong_ty` — mỗi tháng: thực tế doanh thu / lãi gộp (`mart.ban_theo_thang`),
  ngân sách, mốc đến hôm nay (`ngân sách × ngay_kd_da_qua ÷ ngay_kd`, đúng công thức
  `tien_do_ngan_sach`), tiến độ. FULL JOIN (tháng có bán mà chưa đặt / đặt mà chưa bán đều có
  dòng).
- `mart.tien_do_ngan_sach` (từng người) thêm các cột lãi gộp cùng công thức.

## 2. Luật

**Ngân sách công ty là số NHẬP THẲNG, không phải tổng của từng người.** Chưa đặt ngân sách công
ty ⇒ "chưa đặt" (KHÔNG rơi về tổng từng người — hai định nghĩa cùng tên). Mọi chỗ đọc tiến độ
công ty (Tổng quan, Báo cáo, Dự báo) đọc `mart.tien_do_cong_ty`. Màn nhập in "Tổng từng người"
và phần lệch so với ngân sách công ty để thấy phần chưa chia.

## 3. Màn

- `/ngan-sach`: khối **Ngân sách công ty** (12 tháng × Doanh thu / Lãi gộp + cả kỳ + dòng chỉ
  xem "biên gộp dự kiến" = tỷ số của các tổng) · khối **Chỉ tiêu từng người** (mỗi người hai
  dòng, không bắt buộc) + Tổng từng người + lệch. Một biểu mẫu, một giao dịch như cũ.
- `/` khối Tiến độ ngân sách tháng: hai dòng công ty (Doanh thu · Lãi gộp) trước, rồi từng
  người; biểu đồ luỹ kế đổi Doanh thu / Lãi gộp. Ô KPI và khối theo tháng đọc ngân sách công ty.
- `/bao-cao`: tiến độ công ty có thêm lãi gộp; luỹ kế đọc ngân sách công ty.
- `/du-bao`: chốt tháng so với ngân sách doanh thu công ty.

## 4. Kiểm

Công ty đặt, từng người không đặt ⇒ vẫn có tiến độ công ty; từng người đặt, công ty không ⇒
công ty "chưa đặt"; mốc lãi gộp = công thức ngày làm việc; ô trống ≠ 0 ở cả bốn loại ô; nhật
ký ghi đúng `chi_so` và NULL cho công ty; ngân sách lượt hỏi không đổi.
