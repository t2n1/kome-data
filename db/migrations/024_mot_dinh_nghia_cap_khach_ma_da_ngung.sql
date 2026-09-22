-- 024: "cặp (khách, mã) đã ngừng" chỉ còn MỘT định nghĩa (đợt 4b, vòng sửa
-- toàn nhánh).
--
-- Trước file này, cùng một khái niệm được viết tay ở HAI chỗ với HAI công thức
-- khác nhau:
--   1. kome/khach_hang.py::ho_so  -> khối "Mặt hàng đã ngừng mua" của
--      /khach-hang/{mã}: ngưỡng CHUNG `hom_nay - lan_cuoi > 90` cộng
--      `so_lan >= 3`.
--   2. kome/san_pham.py::ho_so    -> khối "Khách đã ngừng mua mã này" của
--      /san-pham/{mã}: nhịp RIÊNG `tre_ngay >= nhip_ngay`.
--
-- Cùng một cặp (khách, mã) cho hai câu trả lời ngược nhau ở CẢ HAI chiều, và
-- người bán mở hai màn cạnh nhau không có cách nào biết tin màn nào:
--   * mua 7 ngày/lần, im 60 ngày  -> (1) nói "vẫn đang mua", (2) nói "đã ngừng"
--   * mua 120 ngày/lần, im 100 ngày -> (1) nói "đã ngừng", (2) nói "vẫn đang mua"
--
-- Và cả hai đều KHÔNG có cổng ※廃業※: mart.khach_mat_hang không biết gì về
-- migration 016, nên một doanh nghiệp đã phá sản vẫn rơi vào khối "đã ngừng
-- mua" — tức vẫn vào danh sách gọi lại, thẳng vào bất biến của CLAUDE.md.
--
-- Cách sửa: cột `ngung_mua` ở CUỐI view mang định nghĩa DUY NHẤT, hai chỗ
-- Python ĐỌC cột đó thay vì viết lại vị từ. Đúng nếp 022 (tai_nhan_vien.
-- so_khach_canh_bao ĐỌC khach_nhom_viec) và 021 (tỷ suất một nhà).
--
-- CHỌN NHỊP RIÊNG, KHÔNG PHẢI NGƯỠNG 90. Đó là bất biến đã ĐO của dự án:
-- ngưỡng chung 90 ngày bỏ sót 49 khách đang rời đi và báo động nhầm 34 khách
-- vẫn mua bình thường. Nghĩa là /khach-hang/{mã} đổi công thức, và điều kiện
-- `so_lan >= 3` của nó thành THỪA: `nhip_ngay` chỉ có giá trị khi đã có ít
-- nhất 2 khoảng cách, tức ít nhất 3 lần mua (xem `so_khoang >= 2` ở 020).
--
-- `tre_ngay` NULL (chưa đủ 3 lần mua) KHÔNG phải "đã ngừng" mà là "chưa đủ dữ
-- liệu" -> coalesce(..., false). Đoán bừa một nhịp rồi kết luận khách đã bỏ là
-- cách nhanh nhất làm nhân viên mất tin vào cảnh báo.
--
-- ĐÂY KHÔNG PHẢI BỘ LỌC DÒNG. khach_mat_hang còn phục vụ khối "khách đang mua
-- mã này" và bảng top-15 mặt hàng của hồ sơ khách — những chỗ đó là SỰ THẬT
-- LỊCH SỬ, không phải danh sách gọi lại. Lọc dòng ở đây thì hồ sơ của một
-- khách ※廃業※ mất sạch bảng mặt hàng và trang trắng trơn.
--
-- LẤY CỜ ※廃業※ TỪ mart.dau_hieu_khach, KHÔNG từ core.dim_customer và cũng
-- không từ mart.khach_360:
--   * core.dim_customer là SCD2 — lấy thẳng mà quên `is_current` thì một khách
--     từng đổi tên có nhiều dòng và JOIN nhân đôi mọi dòng của view này.
--     dau_hieu_khach đã chặn `WHERE is_current` sẵn, và 006 có UNIQUE INDEX
--     (customer_code) WHERE is_current nên nó chắc chắn một dòng mỗi khách.
--   * mart.khach_360 cũng có `da_ngung` và cũng khoá đơn, nhưng nó gộp TOÀN BỘ
--     mart.lan_mua để dựng một dòng mỗi khách — trả giá một lượt quét cả bảng
--     bán hàng để lấy đúng một cột boolean đọc từ TÊN khách. Kiểm chiều phụ
--     thuộc (bắt buộc, vì Postgres từ chối view vòng): khach_360 <- lan_mua,
--     dim_customer, nhip_mua, dau_hieu_khach, moc_thoi_gian — KHÔNG có
--     khach_mat_hang, nên dùng khach_360 ở đây cũng không tạo vòng. Chọn
--     dau_hieu_khach chỉ vì nó rẻ hơn và vì nó mới là NHÀ của cờ này (016);
--     khach_360.da_ngung chính là `coalesce(dau_hieu_khach.da_ngung, false)`.
--
-- `tre_ngay` được tính ở một lớp con RIÊNG (`y`) rồi mới dùng lại cho
-- `ngung_mua` ở lớp ngoài — viết lại biểu thức `hom_nay - du_kien_lan_toi`
-- lần thứ hai là đúng thứ mà chú thích của 020 đã cảnh báo.
CREATE OR REPLACE VIEW mart.khach_mat_hang AS
SELECT y.customer_code, y.product_code, y.ten_hang, y.doanh_thu_thuan,
       y.lai_gop, y.so_luong, y.so_lan, y.lan_dau, y.lan_cuoi, y.nhip_ngay,
       y.du_kien_lan_toi, y.tre_ngay,
       -- im lặng >= 2 x nhịp riêng của CHÍNH CẶP NÀY (tre_ngay = số ngày quá
       -- ngày dự kiến mua lại = lan_cuoi + nhip_ngay, nên tre >= nhip tương
       -- đương im lặng >= 2 nhịp — đúng ngưỡng 'canh_bao' mà mart.khach_360
       -- dùng cho quan hệ khách hàng), VÀ khách chưa bị OBC đánh dấu đóng cửa.
       coalesce(y.tre_ngay >= y.nhip_ngay, false)
         AND NOT coalesce(dh.da_ngung, false)              AS ngung_mua
FROM (
    SELECT x.customer_code, x.product_code, x.ten_hang, x.doanh_thu_thuan,
           x.lai_gop, x.so_luong, x.so_lan, x.lan_dau, x.lan_cuoi,
           x.nhip_ngay, x.du_kien_lan_toi,
           -- Chỉ tính khi ĐÃ quá hạn. Số âm ở cột "trễ" sẽ bị đọc thành
           -- "sớm", mà đó không phải điều cột này nói. du_kien_lan_toi NULL
           -- thì so sánh ra NULL luôn, không cần lặp lại điều kiện
           -- so_khoang >= 2 ở đây.
           CASE WHEN x.hom_nay > x.du_kien_lan_toi
                THEN x.hom_nay - x.du_kien_lan_toi END      AS tre_ngay
    FROM (
        SELECT f.customer_code, f.product_code,
               coalesce(nullif(s.product_name, ''), f.product_code) AS ten_hang,
               sum(f.amount - f.tax_amount) AS doanh_thu_thuan,
               sum(f.gross_profit)          AS lai_gop,
               sum(f.qty)                   AS so_luong,
               count(DISTINCT f.sales_date) AS so_lan,
               min(f.sales_date)            AS lan_dau,
               max(f.sales_date)            AS lan_cuoi,
               -- Dưới 2 khoảng cách = dưới 3 lần mua: không đủ để nói về
               -- "nhịp". NULL chứ không phải một con số, để trang hiện `—`.
               CASE WHEN n.so_khoang >= 2 THEN n.nhip_ngay END AS nhip_ngay,
               CASE WHEN n.so_khoang >= 2
                    THEN (max(f.sales_date) + n.nhip_ngay * interval '1 day')::date
               END AS du_kien_lan_toi,
               m.hom_nay AS hom_nay
        FROM core.fact_sales_line f
        LEFT JOIN core.dim_product s ON s.product_code = f.product_code
        LEFT JOIN mart.nhip_mat_hang n
               ON n.customer_code = f.customer_code
              AND n.product_code = f.product_code
        CROSS JOIN mart.moc_thoi_gian m
        GROUP BY f.customer_code, f.product_code, s.product_name,
                 n.so_khoang, n.nhip_ngay, m.hom_nay
    ) x
) y
LEFT JOIN mart.dau_hieu_khach dh ON dh.customer_code = y.customer_code;

COMMENT ON COLUMN mart.khach_mat_hang.ngung_mua IS
  'Cặp (khách, mã) NÀY đã ngừng: im lặng >= 2 x nhịp mua riêng của chính cặp
   đó VÀ khách chưa bị OBC đánh dấu ※廃業※/※取引停止※ (migration 016).
   Định nghĩa DUY NHẤT — /khach-hang/{mã} ("Mặt hàng đã ngừng mua") và
   /san-pham/{mã} ("Khách đã ngừng mua mã này") ĐỌC cột này, không chỗ nào
   viết lại vị từ. nhip_ngay NULL (dưới 3 lần mua) -> false: đó là "chưa đủ
   dữ liệu", không phải "đã ngừng". KHÔNG phải bộ lọc dòng: view vẫn giữ đủ
   mọi cặp, vì nó còn phục vụ hai khối SỰ THẬT LỊCH SỬ (khách đang mua mã
   này, top-15 mặt hàng của một khách). Có test canh:
   tests/test_san_pham.py::test_hai_man_tra_loi_GIONG_NHAU_ve_mot_cap_khach_ma.';

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
