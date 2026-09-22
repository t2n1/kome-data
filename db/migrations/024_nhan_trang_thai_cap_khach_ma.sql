-- 024: "cặp (khách, mã) đang ở trạng thái nào" chỉ còn MỘT định nghĩa, và nó
-- là một NHÃN ba giá trị chứ không phải một boolean (đợt 4b, vòng sửa toàn
-- nhánh).
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
-- Cách sửa: cột `trang_thai_cap` ở CUỐI view mang định nghĩa DUY NHẤT, hai chỗ
-- Python ĐỌC cột đó thay vì viết lại vị từ. Đúng nếp 022 (tai_nhan_vien.
-- so_khach_canh_bao ĐỌC khach_nhom_viec) và 021 (tỷ suất một nhà).
--
-- NHÃN BA GIÁ TRỊ, KHÔNG PHẢI BOOLEAN — ĐÂY LÀ ĐIỂM CHÍNH CỦA FILE NÀY.
-- Bản đầu của migration này là một boolean `ngung_mua` GÓI cổng ※廃業※ vào bên
-- trong (`tre_ngay >= nhip_ngay AND NOT da_ngung`). Một boolean như thế không
-- phủ định được: `NOT ngung_mua` LUÔN đúng với khách đã đóng cửa, nên mọi khối
-- viết "phần còn lại" bằng `NOT ngung_mua` lặng lẽ nhận lại trọn 281 khách đã
-- phá sản — đúng cái mà cổng bên trong nó tưởng đã chặn. Hậu quả có thật: khối
-- "Khách ĐANG mua mã này" của /san-pham/{mã} và khối "Tháng này chưa mua" của
-- /khach-hang/{mã} đều phải tự JOIN lại mart.dau_hieu_khach / mart.khach_360
-- để đắp tay cổng đó — một cờ, hai nguồn, ba chỗ chép. Tức là bản sửa nhằm dẹp
-- "một khái niệm hai công thức" lại đẻ ra đúng bệnh đó ở tầng trên.
--
-- Nhãn chữa tận gốc vì nó không có phủ định: mỗi khối so BẰNG với đúng giá trị
-- của mình (`= 'ngung'`, `= 'mua'`), nên khách ※廃業※ ('khong_goi') không thuộc
-- khối nào cả mà không khối nào phải biết ※廃業※ là gì. Và khi thêm trạng thái
-- thứ tư sau này, nó cũng KHÔNG âm thầm dồn vào một khối nào — mọi khối vẫn
-- chỉ nhận đúng nhãn nó hỏi. Đây là hình mẫu mart.khach_nhom_viec ('im'/'tut'/
-- 'moi') và mart.khach_360.trang_thai ('ngung_giao_dich'/'canh_bao'/…) đã dùng.
--
-- THỨ TỰ BA NHÁNH LÀ MỘT PHẦN CỦA ĐỊNH NGHĨA: 'khong_goi' xét TRƯỚC, y hệt
-- cách 016 đặt 'ngung_giao_dich' lên đầu CASE của khach_360.trang_thai — với
-- khách đã đóng cửa thì nhịp mua và số ngày im lặng không còn mang nghĩa gì.
--
-- CHỌN NHỊP RIÊNG, KHÔNG PHẢI NGƯỠNG 90. Đó là bất biến đã ĐO của dự án:
-- ngưỡng chung 90 ngày bỏ sót 49 khách đang rời đi và báo động nhầm 34 khách
-- vẫn mua bình thường. Nghĩa là /khach-hang/{mã} đổi công thức, và điều kiện
-- `so_lan >= 3` của nó thành THỪA: `nhip_ngay` chỉ có giá trị khi đã có ít
-- nhất 2 khoảng cách, tức ít nhất 3 lần mua (xem `so_khoang >= 2` ở 020).
--
-- `tre_ngay` NULL (chưa đủ 3 lần mua) KHÔNG phải "đã ngừng" mà là "chưa đủ dữ
-- liệu" -> rơi xuống nhánh ELSE 'mua'. Đoán bừa một nhịp rồi kết luận khách đã
-- bỏ là cách nhanh nhất làm nhân viên mất tin vào cảnh báo.
--
-- ĐÂY KHÔNG PHẢI BỘ LỌC DÒNG. khach_mat_hang còn phục vụ khối "khách đang mua
-- mã này" và bảng top-15 mặt hàng của hồ sơ khách — những chỗ đó là SỰ THẬT
-- LỊCH SỬ, không phải danh sách gọi lại. Lọc dòng ở đây thì hồ sơ của một
-- khách ※廃業※ mất sạch bảng mặt hàng và trang trắng trơn.
--
-- LẤY CỜ ※廃業※ TỪ mart.dau_hieu_khach, KHÔNG từ core.dim_customer và cũng
-- không từ mart.khach_360 — và lấy ĐÚNG MỘT LẦN, ở đây:
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
--   * "Một lần" là phần còn lại của bài học: sau file này KHÔNG chỗ nào ngoài
--     view này còn JOIN để lấy `da_ngung` cho khái niệm cặp (khách, mã) nữa.
--
-- LEFT JOIN + coalesce chứ không INNER: khách chưa có dòng 得意先全情報 vẫn
-- phải giữ đủ các cặp của mình, và "không có dòng" nghĩa là "không có dấu
-- ※…※", tức KHÔNG phải đã đóng cửa.
--
-- `tre_ngay` được tính ở một lớp con RIÊNG (`y`) rồi mới dùng lại cho
-- `trang_thai_cap` ở lớp ngoài — viết lại biểu thức `hom_nay - du_kien_lan_toi`
-- lần thứ hai là đúng thứ mà chú thích của 020 đã cảnh báo.
CREATE OR REPLACE VIEW mart.khach_mat_hang AS
SELECT y.customer_code, y.product_code, y.ten_hang, y.doanh_thu_thuan,
       y.lai_gop, y.so_luong, y.so_lan, y.lan_dau, y.lan_cuoi, y.nhip_ngay,
       y.du_kien_lan_toi, y.tre_ngay,
       CASE
         -- Khách bị OBC đánh dấu ※廃業※/※取引停止※ (016). Xét TRƯỚC hai nhánh
         -- kia: đã đóng cửa thì im lặng là đúng, không phải tín hiệu.
         WHEN coalesce(dh.da_ngung, false) THEN 'khong_goi'
         -- im lặng >= 2 x nhịp riêng của CHÍNH CẶP NÀY (tre_ngay = số ngày quá
         -- ngày dự kiến mua lại = lan_cuoi + nhip_ngay, nên tre >= nhip tương
         -- đương im lặng >= 2 nhịp — đúng ngưỡng 'canh_bao' mà mart.khach_360
         -- dùng cho quan hệ khách hàng).
         WHEN y.tre_ngay >= y.nhip_ngay THEN 'ngung'
         -- Còn lại. `tre_ngay` NULL (chưa đủ 3 lần mua, hoặc chưa tới ngày dự
         -- kiến) cho ra NULL ở nhánh trên nên rơi xuống đây — CỐ Ý: "chưa đủ
         -- dữ liệu" không phải "đã ngừng".
         ELSE 'mua'
       END                                                AS trang_thai_cap
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

COMMENT ON COLUMN mart.khach_mat_hang.trang_thai_cap IS
  'Trạng thái của CẶP (khách, mã) này — NHÃN ba giá trị, không phải boolean:
   ''khong_goi'' = khách bị OBC đánh dấu ※廃業※/※取引停止※ (016), xét TRƯỚC hai
   nhánh kia; ''ngung'' = im lặng >= 2 x nhịp mua riêng của chính cặp đó;
   ''mua'' = còn lại (gồm cả cặp chưa đủ 3 lần mua nên nhip_ngay NULL — đó là
   "chưa đủ dữ liệu", không phải "đã ngừng"). Định nghĩa DUY NHẤT —
   /khach-hang/{mã} ("Mặt hàng đã ngừng mua", "Tháng này chưa mua") và
   /san-pham/{mã} ("Khách đang mua", "Khách đã ngừng mua mã này") ĐỌC cột này
   và so BẰNG với đúng giá trị của mình. KHÔNG ĐƯỢC dùng NOT trên cột này: một
   boolean có cổng ※廃業※ gói bên trong thì phủ định nó mở cửa lại đúng cho
   281 khách đã phá sản — đó là lý do cột này là nhãn. So bằng cũng có nghĩa
   là thêm trạng thái thứ tư sau này không âm thầm dồn dòng vào khối nào.
   KHÔNG phải bộ lọc dòng: view vẫn giữ đủ mọi cặp, vì nó còn phục vụ hai khối
   SỰ THẬT LỊCH SỬ (khách đang mua mã này, top-15 mặt hàng của một khách).
   Có test canh: tests/test_san_pham.py::
   test_hai_man_tra_loi_GIONG_NHAU_ve_mot_cap_khach_ma và
   test_cap_cua_khach_da_dong_cua_mang_NHAN_RIENG_khong_phai_phu_dinh.';

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
