# Hạng khách lấy từ OBC (得意先ランク) — 2026-09-28

Chủ DN chốt 2026-09-28: hạng khách trên web **lấy từ file 得意先全情報**, không tự tính.
Thay bất biến cũ "`mart.hang_doanh_thu` là hạng do ta tự tính theo doanh thu 12 tháng".

## Quyết định
1. **Hạng = 得意先ランク của OBC**, bản hiện hành của `core.dim_customer` (không quay về theo
   mốc — OBC không cho biết hạng ngày cũ; cùng nếp tên khách / người phụ trách).
2. **Một định nghĩa**: `mart.hang_obc(rank_code, rank_name)` → nhãn ngắn
   `0001..0005` → S A B C D · `0006/0007/0008` → Z ZZ ZZZ · `0011` → キャンペーン不要 ·
   `0999` → 対象外 · trống → NULL · mã lạ → nguyên văn `rank_name`.
   Tên đầy đủ (`rank_name`) đi kèm để hiện khi di chuột.
3. **Thay ở mọi chỗ**: huy hiệu hồ sơ, huy hiệu ⭐ S/A, cột + sắp + CSV + chip lọc + khối
   "Phân bố theo hạng" của danh sách, ô tìm khách, nhóm việc `'tut'` (S/A của OBC).
   Nhãn: "Hạng OBC". Hạng tự tính (cume_dist) bị bỏ; `mart.hang_doanh_thu` thay bằng
   `mart.doanh_thu_12t` (chỉ `dt_12t`, cho bản đồ).
4. **Z / ZZ / ZZZ không vào danh sách gọi.** Cờ `khong_goi` định nghĩa ĐÚNG MỘT LẦN ở
   `mart.dau_hieu_khach` = `da_ngung` (※廃業※ …) HOẶC hạng OBC ∈ {Z, ZZ, ZZZ}; `mart.khach_360`
   mang lại cờ đó. Mọi danh sách gọi đọc cờ này: ba nhóm việc (`im`/`tut`/`moi` → kéo theo
   `tai_nhan_vien.so_khach_canh_bao`, `khach_theo_tinh.can_goi`), `mart.uu_tien_lien_he`,
   nhãn `'khong_goi'` của `mart.khach_thang_nay` và `trang_thai_cap` của
   `mart.khach_mat_hang_cua` (→ Nên chào, mã đến ngày mua lại, khách nên chào của SP 360),
   `can_xu_ly` / `dem_va_can_xu_ly` (danh sách + ô KPI "cần gọi"), nhánh `'im'` của `danh_ba`.
5. **Không đổi**: `trang_thai` của khách Z/ZZ/ZZZ (không thành "Ngừng giao dịch" — 583/604
   khách ZZZ vẫn mua), thanh sức khoẻ khách (đếm theo trạng thái), mọi tổng doanh thu, danh
   sách / hồ sơ khách (vẫn hiện), `/du-bao` (phân tích, không phải danh sách gọi).
   Hồ sơ khách hiện "OBC: không gọi (ZZZ)".

## Việc làm
- Migration `055_hang_obc.sql` (thứ tự: hàm → `dau_hieu_khach` → `khach_360` → `doanh_thu_12t`
  → `khach_nhom_viec` → `khach_theo_tinh` → DROP `hang_doanh_thu` → `uu_tien_lien_he` →
  `khach_thang_nay` → `khach_mat_hang_cua`).
- Python: `kome/khach_hang.py`, `kome/ho_so_khach.py`, `kome/khoi_tong_quan.py`.
- React: `giao_dien/src/khach/*` rồi `npm run build`.
- Test: `tests/test_hang_obc.py` (ánh xạ; mọi danh sách gọi không có khách Z/ZZ/ZZZ; nhóm tụt
  theo S/A OBC), sửa test cũ về nhãn "12 tháng" / `hang_doanh_thu`.
- CLAUDE.md: viết lại bất biến hạng; `scripts/sinh_tai_lieu.py`, `scripts/sinh_cot_dung.py`.
- **Migration 055 phải chạy TRƯỚC khi triển khai.**
