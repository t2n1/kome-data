-- 022: "khách đang rời đi" chỉ còn MỘT định nghĩa (đợt 4a, vòng sửa toàn nhánh).
--
-- Trước file này, vị từ `trang_thai IN ('canh_bao', 'da_roi_bo')` được viết
-- tay ở BA chỗ:
--   1. mart.khach_nhom_viec, nhánh 'im'            (020)
--   2. mart.tai_nhan_vien.so_khach_canh_bao        (020)  <- cột "Cần gọi"
--   3. kome/khach_hang.py::can_xu_ly                      <- trang /can-xu-ly
--
-- Đặc tả §5.4 viết bất biến cho HAI chỗ (1 và 3) và có test canh đúng hai chỗ
-- đó. Đợt 4a thêm chỗ thứ ba mà không ai canh. Đợt 7 sẽ đổi định nghĩa này —
-- khi đó cột "Cần gọi" của bảng "Tải của từng nhân viên" âm thầm trôi khỏi hai
-- chỗ kia, và nó chính là con số quản lý nhìn để chia việc cho năm người.
--
-- Cách sửa: chỗ (2) ĐỌC chỗ (1) thay vì viết lại vị từ. Một khái niệm, một
-- công thức — cùng nguyên tắc mà 021 viết ra cho tỷ suất.
--
-- EXISTS chứ không JOIN: mart.khach_nhom_viec có thể có NHIỀU dòng cho một
-- khách (một khách thuộc nhiều nhóm việc), nên JOIN sẽ nhân đôi dòng và làm
-- cả `so_khach` lẫn `doanh_thu` của bảng này đếm sai — hai con số không liên
-- quan gì tới thay đổi này.
--
-- Vẫn là `count(*) FILTER`, vẫn LEFT JOIN từ dim_salesperson: người chưa có
-- khách nào phải hiện với số 0, không được biến mất khỏi bảng. Với họ,
-- k.customer_code là NULL nên EXISTS không khớp dòng nào -> FILTER sai -> 0.
CREATE OR REPLACE VIEW mart.tai_nhan_vien AS
SELECT s.salesperson_code, s.ten,
       count(k.customer_code)                  AS so_khach,
       coalesce(sum(k.doanh_thu_thuan), 0)     AS doanh_thu,
       count(*) FILTER (
           WHERE EXISTS (SELECT 1 FROM mart.khach_nhom_viec v
                          WHERE v.customer_code = k.customer_code
                            AND v.nhom = 'im'))
                                               AS so_khach_canh_bao
FROM core.dim_salesperson s
LEFT JOIN mart.khach_360 k ON k.salesperson_code = s.salesperson_code
GROUP BY s.salesperson_code, s.ten;

COMMENT ON COLUMN mart.tai_nhan_vien.so_khach_canh_bao IS
  'Số khách đang rời đi. ĐỌC mart.khach_nhom_viec (nhom=''im''), không viết
   lại vị từ — đổi định nghĩa "đang rời đi" thì sửa MỘT chỗ ở 020 và cả ba
   chỗ hiển thị đi theo. Có test canh: tests/test_mart_khach_360.py::
   test_ba_cho_noi_ve_khach_dang_roi_di_deu_cho_cung_mot_tap.';


-- Ghi chú cho cột `gia_cao_nhat` của 021 — KHÔNG sửa 021 (đã chạy), chỉ dán
-- nhãn cảnh báo lên cột.
--
-- Vòng review toàn nhánh gỡ cột "Đơn giá cao nhất đã bán" khỏi khối "Gợi ý
-- hàng chưa từng mua": `max(unit_price)` KHÔNG nhóm theo `pack_code`, mà
-- 00 = バラ (lẻ) và 02 = ケース (thùng) là hai mức giá cách nhau hơn chục
-- lần. Mã bán cả hai quy cách thì con số này LUÔN là giá thùng, và nó từng
-- hiện dưới một cái nhãn không nói gì về 荷姿 — trên đúng màn hình người bán
-- nhìn TRƯỚC KHI đọc một con số tiền cho khách nghe.
--
-- Để cột lại chứ không bỏ: bỏ một cột khỏi view là một migration nữa cho
-- một thứ không ai còn đọc, và cột này vẫn đúng cho câu hỏi "mã này từng bán
-- cao nhất bao nhiêu, bất kể quy cách".
COMMENT ON COLUMN mart.ty_suat_mat_hang.gia_cao_nhat IS
  'max(unit_price) TRỘN mọi 荷姿区分 (00 = バラ lẻ, 02 = ケース thùng). KHÔNG
   dùng để báo giá: mã bán cả hai quy cách thì đây luôn là giá thùng. Không
   còn hiển thị ở màn nào kể từ vòng sửa cuối đợt 4a. Giá để báo cho khách
   lấy ở core.fact_price_list, tách theo pack_code — xem khối "Bảng giá của
   bậc" ở kome/web/templates/khach_360.html.';

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
