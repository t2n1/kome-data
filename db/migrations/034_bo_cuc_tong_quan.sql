-- 034: bố cục trang Tổng quan theo TỪNG TÀI KHOẢN (kéo thả khối, đổi kích thước,
-- ẩn/hiện — theo gói thiết kế Dashboard.dc.html).
--
-- LƯU Ý BẤT BIẾN: chạy bằng vai trò `postgres` như mọi migration.
--
-- Gói thiết kế lưu bố cục vào localStorage; ta lưu trên máy chủ, vì:
--   * bố cục đi theo NGƯỜI qua mọi máy, không theo trình duyệt;
--   * máy chủ vẽ đúng bố cục ngay trong HTML đầu tiên — không có khung hình
--     vẽ bố cục mặc định rồi giật sang bố cục đã lưu (cùng lý lẽ cookie
--     kome_giao_dien, CLAUDE.md);
--   * cổng đăng nhập ĐÃ đọc dòng app.nguoi_dung ở mỗi lượt gọi, nên đọc thêm
--     một cột là 0 truy vấn mới (ngân sách `/` ≤ 9 giữ nguyên).
--
-- NULL = chưa từng sắp xếp -> bố cục mặc định. Nội dung do
-- kome/web/bo_cuc.py::chuan_hoa lọc TRƯỚC khi ghi (chỉ mã khối đã biết, kích
-- thước kẹp trong dải) và lọc LẠI khi đọc — dòng cũ thiếu khối mới vẫn đọc được.
-- kome_app đã có UPDATE trên app.nguoi_dung (009, mặc định cho mọi bảng app).

ALTER TABLE app.nguoi_dung ADD COLUMN bo_cuc_tong_quan jsonb NULL;

COMMENT ON COLUMN app.nguoi_dung.bo_cuc_tong_quan IS
  'Bố cục trang Tổng quan của người này: [{id, rong 1-3, cao 1-4, an}] theo thứ tự hiện. NULL = mặc định.';
