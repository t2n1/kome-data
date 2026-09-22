-- 028: sửa hồi quy do chính vòng soát cuối trước (027) gây ra.
--
-- FILE MỚI, KHÔNG SỬA 026 CŨNG KHÔNG SỬA 027 — cả hai đã chạy trên CSDL thử
-- nghiệm ở mọi phiên test.
--
-- ---------------------------------------------------------------------------
-- Chuyện gì đã xảy ra
-- ---------------------------------------------------------------------------
--
-- 027 dựng `mart.ban_theo_nhan_vien_thang_so_sanh` để tính "so cùng kỳ" theo
-- TỪNG NGƯỜI, rồi kome/bao_cao.py lọc view đó theo `thang = <tháng đang xét>`
-- để lấy dữ liệu cùng kỳ. Nhưng view đó dựng `FROM mart.ban_theo_nhan_vien_
-- thang` — một view GROUP BY trên mart.dong_ban, tức CHỈ có dòng cho (người,
-- tháng) nào người đó THẬT SỰ có ít nhất một dòng bán. Lọc theo tháng ĐANG
-- XÉT (không phải tháng cùng kỳ) nghĩa là: một người CÓ chỉ tiêu nhưng KHÔNG
-- bán đồng nào trong tháng đang xét thì KHÔNG CÓ DÒNG NÀO trong view so sánh
-- cho tháng đó — bất kể năm ngoái cùng tháng người đó có bán được bao nhiêu.
--
-- Đây CHÍNH XÁC là người mà FULL JOIN của 026 tồn tại để giữ lại (chú thích
-- của 026 gọi là "đúng người cần nhìn nhất"), và CHÍNH XÁC là setup của
-- test_ngan_sach_mart.py::test_nguoi_co_chi_tieu_ma_KHONG_ban_duoc_dong_nao_van_co_dong
-- (mã 0105) — chỉ cần thêm một dòng bán cho 0105 ở tháng cùng kỳ là lỗi lộ ra,
-- và không test nào trong vòng sửa trước chạm đúng ca đó.
--
-- Bản CŨ (trước 027) không có lỗi này: nó lọc nhánh cùng kỳ theo
-- salesperson_code của mart.tien_do_ngan_sach (đã qua FULL JOIN) VÀ theo
-- tháng cùng kỳ ĐỘC LẬP — nên người 0 doanh thu tháng này vẫn đọc được doanh
-- thu cùng kỳ năm ngoái. 027 làm MẤT tính năng đó — đây là HỒI QUY, không
-- phải một giới hạn có sẵn.
--
-- ---------------------------------------------------------------------------
-- Ngữ nghĩa đúng — ba trạng thái, ba cách hiện khác nhau
-- ---------------------------------------------------------------------------
--
-- * co_cung_ky = tháng M-12 có TỒN TẠI TRONG KHO hay không — một sự thật về
--   KHO, không phải về người. Đúng nếp mart.ban_theo_thang_so_sanh (014):
--   dùng mart.ban_theo_thang (rollup CẢ CÔNG TY, có dòng cho MỌI tháng công
--   ty từng bán bất cứ gì) để hỏi "tháng đó có tồn tại không", KHÔNG hỏi
--   "người NÀY có dòng ở tháng đó không". Dữ liệu bán bắt đầu 2025-03-03;
--   trước mốc đó KHÔNG TỒN TẠI — đó là ca DUY NHẤT co_cung_ky = false.
-- * cung_ky = doanh thu CỦA CHÍNH NGƯỜI NÀY trong tháng M-12. Nếu tháng đó
--   tồn tại (co_cung_ky = true) mà người này không có dòng nào, sự thật là
--   ¥0 — KHÔNG PHẢI "không biết". coalesce(..., 0), nhưng CHỈ khi co_cung_ky
--   đúng; co_cung_ky sai thì cung_ky phải là NULL (không có mẫu để nói ¥0).
-- * tang_truong giữ nguyên gate `> 0` (027, bất biến 赤伝: doanh thu một
--   tháng của một người có thể ÂM). Cùng kỳ ¥0 hoặc ÂM thì tang_truong NULL
--   — màn hình in "—", KHÔNG PHẢI "không có dữ liệu" (vì tháng đó CÓ tồn tại).
--
-- ---------------------------------------------------------------------------
-- Vì sao đặt lại ở mart.tien_do_ngan_sach, không sửa view của 027
-- ---------------------------------------------------------------------------
--
-- mart.tien_do_ngan_sach là view DUY NHẤT đã có sẵn ĐÚNG tập dòng cần thiết
-- (đã qua FULL JOIN ngan_sach_thang <-> ban_theo_nhan_vien_thang) — thêm cột
-- vào nó là cách duy nhất giữ được cả người "có chỉ tiêu mà 0 doanh thu THÁNG
-- NÀY" lẫn "so cùng kỳ đúng cho người đó". `CREATE OR REPLACE VIEW` thêm cột
-- vào CUỐI danh sách cột — hợp lệ kể cả khi có view/quyền khác đang phụ
-- thuộc, không cần DROP.
--
-- `mart.ban_theo_nhan_vien_thang_so_sanh` (027) từ nay THỪA — không còn chỗ
-- nào đọc nó (kome/bao_cao.py đọc thẳng ba cột mới ở đây). DROP nó, không
-- để lại một view chết mang chú thích sai (027 nói dt_cung_ky "NULL hoặc 0
-- tuỳ nguồn" — sai: amount/tax_amount NOT NULL từ 007, sum() trên nhóm
-- không rỗng không bao giờ NULL; may là chỗ dùng nó chưa từng dựa vào NULL
-- nên không có ảnh hưởng thật, nhưng không có lý do giữ một view sai chú
-- thích mà không ai đọc).
--
-- ---------------------------------------------------------------------------
-- Chỉ MỘT lần đánh giá mart.ban_theo_nhan_vien_thang trong CẢ CÂU
-- ---------------------------------------------------------------------------
--
-- View cần đọc "ban_theo_nhan_vien_thang" ở HAI vị trí logic: làm vế trái
-- của FULL JOIN (`bt`) VÀ làm nguồn tra cùng kỳ năm trước (`tr`, cùng bảng,
-- lọc theo (salesperson_code, tháng - 1 năm)). Bọc nó trong MỘT CTE
-- `AS MATERIALIZED` rồi tham chiếu CTE đó HAI LẦN (làm `bt` và làm `tr`):
-- Postgres tính CTE MATERIALIZED đúng MỘT LẦN rồi dùng lại, nên
-- mart.ban_theo_nhan_vien_thang (một GROUP BY trên mart.dong_ban, tức
-- core.fact_sales_line JOIN dim_date) chỉ bị gộp lại MỘT LẦN cho toàn bộ
-- view.
--
-- [Vòng soát cuối 3, việc 1] `ct` (câu hỏi "tháng M-12 có tồn tại trong kho
-- không") KHÔNG hỏi mart.ban_theo_thang nữa — bản trước làm vậy và vô tình
-- THÊM MỚI một lượt gộp toàn bộ mart.dong_ban (HashAggregate trên
-- fact_sales_line) mà view GỐC (trước 027) chưa từng có, nên tổng KHÔNG
-- giảm so với bản gốc (bản gốc: 2 lượt gộp `fact_sales_line`; bản có
-- `ban_theo_thang`: vẫn 2, không phải 1 như chú thích cũ tuyên bố — phép
-- đếm lúc đó chỉ tìm node `GroupAggregate` nên bỏ sót đúng node
-- `HashAggregate` mà `ban_theo_thang` dùng).
--
-- Tập giá trị `thang` của mart.ban_theo_thang và của
-- mart.ban_theo_nhan_vien_thang BẰNG NHAU TUYỆT ĐỐI: cả hai GROUP BY trên
-- CÙNG mart.dong_ban, chỉ khác độ mịn (thang riêng so với thang +
-- salesperson_code) — Postgres gộp NULL salesperson_code thành một nhóm
-- riêng chứ không loại nó, nên không tháng nào "biến mất" ở độ mịn mịn hơn.
-- Vì vậy `ct AS (SELECT DISTINCT thang FROM bt)` trả lời CHÍNH XÁC câu hỏi
-- "tháng này có tồn tại trong kho không", chỉ đọc lại CTE `bt` đã có sẵn —
-- không một lượt gộp mới nào trên fact_sales_line.
--
-- ĐO THẬT bằng `EXPLAIN SELECT * FROM mart.tien_do_ngan_sach` ngay sau khi
-- migration này chạy: xem báo cáo soát cuối (đã dán nguyên văn kế hoạch).
-- Kỳ vọng: ĐÚNG 1 node gộp trên fact_sales_line (GroupAggregate dưới
-- "CTE bt"), scan lại hai lần qua "CTE Scan on bt" và "CTE Scan on bt tr",
-- và một "CTE Scan on ct" đọc lại CHÍNH `bt` — không HashAggregate nào
-- khác trên fact_sales_line ngoài node gộp duy nhất đó.
CREATE OR REPLACE VIEW mart.tien_do_ngan_sach AS
WITH bt AS MATERIALIZED (
    SELECT * FROM mart.ban_theo_nhan_vien_thang
),
ct AS (
    SELECT DISTINCT thang FROM bt
)
SELECT coalesce(bt.thang, n.thang)                        AS thang,
       coalesce(bt.company_fy, n.company_fy)              AS company_fy,
       coalesce(bt.salesperson_code, n.salesperson_code)  AS salesperson_code,
       n.muc_tieu,
       coalesce(bt.doanh_thu_thuan, 0)::bigint            AS thuc_te,
       k.ngay_kd,
       k.ngay_kd_da_qua,
       (n.muc_tieu * k.ngay_kd_da_qua::numeric / nullif(k.ngay_kd, 0))::bigint
                                                         AS muc_tieu_den_hom_nay,
       -- nullif: chỉ tiêu 0 cho ra NULL và màn hình in "—". Chia cho 0 thì
       -- trang chết; in "∞" thì người đọc tưởng đã vượt mức.
       coalesce(bt.doanh_thu_thuan, 0)::numeric / nullif(n.muc_tieu, 0) AS tien_do,
       -- MỚI (028): so cùng kỳ theo TỪNG NGƯỜI, đúng ba ngữ nghĩa ghi ở trên.
       -- ct (tập thang PHÂN BIỆT của chính bt — xem chú thích ở trên) trả
       -- lời "tháng M-12 có tồn tại trong kho không" — độc lập với người
       -- đang xét. tr (CTE bt tự nối) trả lời "người này bán được bao
       -- nhiêu ở tháng M-12".
       CASE WHEN ct.thang IS NOT NULL
            THEN coalesce(tr.doanh_thu_thuan, 0)::bigint END      AS cung_ky,
       (ct.thang IS NOT NULL)                                     AS co_cung_ky,
       CASE WHEN tr.doanh_thu_thuan > 0
            THEN coalesce(bt.doanh_thu_thuan, 0)::numeric
                 / tr.doanh_thu_thuan - 1 END                     AS tang_truong
FROM bt
FULL JOIN mart.ngan_sach_thang     n  ON n.thang = bt.thang
                                     AND n.salesperson_code = bt.salesperson_code
LEFT JOIN mart.ngay_kinh_doanh     k  ON k.thang = coalesce(bt.thang, n.thang)
LEFT JOIN bt                       tr ON tr.salesperson_code
                                          = coalesce(bt.salesperson_code, n.salesperson_code)
                                     AND tr.thang = to_char(
                                           to_date(coalesce(bt.thang, n.thang), 'YYYY-MM')
                                           - interval '1 year', 'YYYY-MM')
LEFT JOIN ct                          ON ct.thang = to_char(
                                           to_date(coalesce(bt.thang, n.thang), 'YYYY-MM')
                                           - interval '1 year', 'YYYY-MM');

COMMENT ON VIEW mart.tien_do_ngan_sach IS
  'FULL JOIN chỉ tiêu <-> thực tế. Đổi thành LEFT JOIN theo BẤT KỲ chiều nào
   cũng làm mất dòng mà trang vẫn vẽ bình thường. Có test canh cả hai chiều:
   tests/test_ngan_sach_mart.py.

   (028) cung_ky/co_cung_ky/tang_truong: co_cung_ky hỏi CẢ CÔNG TY (qua tập
   thang phân biệt của chính CTE bt — KHÔNG qua mart.ban_theo_thang, xem chú
   thích trong migration) xem tháng M-12 có tồn tại trong kho không — KHÔNG
   hỏi riêng người đang xét, vì một người 0 doanh thu tháng M-12 (khác với
   tháng M-12 không tồn tại) vẫn phải đọc được cung_ky = 0, không phải
   "không có dữ liệu". cung_ky là NULL CHỈ KHI co_cung_ky sai. tang_truong
   giữ gate `> 0` (赤伝 làm doanh thu một tháng có thể ÂM). CTE `bt AS
   MATERIALIZED` được tham chiếu BA LẦN (vế FULL JOIN chính, vế tra cùng kỳ
   `tr`, và nguồn của `ct`) để mart.ban_theo_nhan_vien_thang chỉ bị gộp lại
   ĐÚNG MỘT LẦN trong cả view — bất biến CLAUDE.md (ca kho_hang()). Đừng
   "dọn cho gọn" bằng cách bỏ CTE này, và đừng đổi `ct` sang đọc thẳng
   mart.ban_theo_thang — làm vậy sẽ THÊM LẠI một lượt gộp toàn bộ
   mart.dong_ban mà bản này cố tình tránh (đã từng xảy ra, xem vòng soát
   cuối 3 trong báo cáo).';

-- 027 dựng mart.ban_theo_nhan_vien_thang_so_sanh cho đúng việc trên nhưng
-- lọc sai trục (theo tháng đang xét thay vì để mart.tien_do_ngan_sach tự
-- FULL JOIN rồi tra cùng kỳ theo salesperson_code độc lập) — không còn chỗ
-- nào đọc nó nữa. Không giữ lại một view chết mang chú thích sai.
DROP VIEW mart.ban_theo_nhan_vien_thang_so_sanh;
