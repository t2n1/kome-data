-- 031: đợt 8 (Dự báo) — MỘT định nghĩa "ngày làm việc" cho cả dự án.
--
-- LƯU Ý BẤT BIẾN: chạy bằng vai trò `postgres` như mọi migration.
--
-- Trước 031, "ngày làm việc" là biểu thức `NOT d.is_weekend` viết thẳng trong
-- mart.ngay_kinh_doanh (026). Đợt 8 cần CÙNG khái niệm đó ở mức TỪNG NGÀY
-- (đường luỹ kế của tháng, nhịp bán mỗi ngày làm việc) chứ không chỉ đếm theo
-- tháng. Chép lại biểu thức ở một chỗ thứ hai là hai định nghĩa sẽ trôi khỏi
-- nhau đúng ngày ai đó thêm ngày lễ Nhật vào một chỗ mà quên chỗ kia — nên
-- tách nó thành view riêng, và ngay_kinh_doanh ĐỌC lại view này.
--
-- HẠN CHẾ CÓ TÊN (giữ nguyên từ 026): core.dim_date chưa có cột ngày lễ, nên
-- la_ngay_kd chỉ loại thứ Bảy/Chủ nhật. Thêm ngày lễ là sửa ĐÚNG view này.

CREATE VIEW mart.lich_kinh_doanh AS
SELECT date_key AS ngay,
       NOT is_weekend AS la_ngay_kd
FROM core.dim_date;

COMMENT ON VIEW mart.lich_kinh_doanh IS
  'Một dòng mỗi ngày của core.dim_date. la_ngay_kd là định nghĩa DUY NHẤT của
   "ngày làm việc" — mart.ngay_kinh_doanh và màn Dự báo đều đọc từ đây.';

-- Cùng tên cột, cùng kiểu (count -> bigint) với bản 026: CREATE OR REPLACE
-- chỉ được thay thân view, không được đổi cột.
CREATE OR REPLACE VIEW mart.ngay_kinh_doanh AS
SELECT to_char(l.ngay, 'YYYY-MM')                                     AS thang,
       count(*) FILTER (WHERE l.la_ngay_kd)                           AS ngay_kd,
       count(*) FILTER (WHERE l.la_ngay_kd AND l.ngay <= m.hom_nay)   AS ngay_kd_da_qua
FROM mart.lich_kinh_doanh l CROSS JOIN mart.moc_thoi_gian m
GROUP BY 1;

-- kome_app/kome_report tự nhận SELECT trên view mới (009); kome_ingest thì
-- không — dòng này bắt buộc, cùng nếp 026–030.
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
