-- 021: tỷ suất lãi gộp theo MÃ HÀNG, gộp toàn bộ lịch sử (đợt 4a, sửa task 6).
--
-- Vì sao phải là một view trong `mart` chứ không phải một biểu thức trong câu
-- lệnh của trang: bản đầu của khối "Gợi ý hàng chưa từng mua" tính
--
--     avg(gross_profit / nullif(amount - tax_amount, 0))
--
-- tức TRUNG BÌNH CỦA TỶ SỐ TỪNG DÒNG. Mọi chỗ khác trong dự án tính TỶ SỐ CỦA
-- CÁC TỔNG — `014_mart_bao_cao.sql` (ban_theo_thang, ban_theo_khach,
-- ban_theo_san_pham, ban_theo_nhan_vien) và `015_mart_khach_hang.sql`
-- (khach_360.ty_suat). Hai công thức cho hai con số khác nhau, và người bán
-- hàng không có cách nào biết mình đang đọc cái nào.
--
-- Ở đây bản sai còn nguy hiểm hơn là chuyện thuần khiết: một dòng có doanh thu
-- thuần vài yên cho ra tỷ số hàng chục lần, mà khối gợi ý xếp theo tỷ suất
-- GIẢM DẦN rồi lấy 8 dòng đầu — nên đúng những mã rác đó chiếm trọn tám dòng
-- gợi ý của MỌI khách, kèm một phần trăm vô nghĩa hiện lên trang. 赤伝 (phiếu
-- đỏ, số ÂM, luật số 2 của 014 cấm lọc bỏ) làm mẫu số âm nhỏ, nên đây là
-- chuyện có thật chứ không phải giả định.
--
-- `mart.ban_theo_san_pham` (014) đã có ĐÚNG công thức này rồi, nhưng chia theo
-- KỲ KẾ TOÁN. Khối gợi ý hỏi "mã này lời bao nhiêu", không hỏi "trong kỳ nào",
-- nên nó cần một bản gộp toàn bộ lịch sử. Không sửa view cũ: trang /bao-cao
-- dựa vào nó và báo cáo thì BẮT BUỘC chia theo kỳ.
--
-- Đi qua mart.dong_ban (không phải core.fact_sales_line thẳng) để doanh thu
-- thuần dùng chung một định nghĩa với cả dự án: amount - tax_amount.
--
-- Lợi thêm, không phải lý do chính: bản cũ dùng LEFT JOIN LATERAL nên quét
-- bảng bán hàng MỘT LẦN CHO MỖI MÃ (232 mã thật); view này quét một lần rồi
-- gộp.
CREATE VIEW mart.ty_suat_mat_hang AS
SELECT b.product_code,
       sum(b.doanh_thu_thuan) AS doanh_thu_thuan,
       sum(b.gross_profit)    AS lai_gop,
       -- nullif: mã chưa bán được đồng nào thì tỷ suất là NULL để trang nói
       -- "chưa có số", không phải 0% (đọc thành "bán mà không lãi đồng nào").
       sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0) AS ty_suat,
       max(b.unit_price)      AS gia_cao_nhat
FROM mart.dong_ban b
GROUP BY b.product_code;

COMMENT ON VIEW mart.ty_suat_mat_hang IS
  'Tỷ suất lãi gộp theo mã hàng, toàn bộ lịch sử. TỶ SỐ CỦA CÁC TỔNG, y hệt
   mọi chỉ số tỷ suất khác trong mart — không phải trung bình của các tỷ số.';

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
