-- 027: vòng soát cuối đợt 5a — hai lỗi của khối "So cùng kỳ" trên /bao-cao
-- (kome/web/templates/bao_cao.html, bảng "Kết quả theo từng nhân viên") và
-- một cạm bẫy vận hành của khoá ngoại `sua_boi` (026).
--
-- FILE MỚI, KHÔNG SỬA 026: 026 đã chạy trên CSDL thử nghiệm ở mọi phiên
-- test — luật của dự án là chỉ thêm migration mới, không bao giờ sửa một
-- migration đã chạy.

-- ---------------------------------------------------------------------------
-- 1) "So cùng kỳ" bị tính lại trong Jinja (sai) thay vì đọc từ mart (đúng)
-- ---------------------------------------------------------------------------
--
-- Trước bản này, kome/web/templates/bao_cao.html tự tính:
--     (n.thuc_te / n.cung_ky - 1) * 100
-- ngay trong template — vi phạm bất biến lớn nhất của dự án ("mọi định
-- nghĩa chỉ số nằm trong mart, không nằm ở Python hay Jinja") theo cách mà
-- test_dinh_nghia_chi_so_nam_o_mart_khong_o_python không bắt được: bộ dò đó
-- chỉ quét mã nguồn PYTHON, không quét template.
--
-- View này lặp lại đúng khuôn mart.ban_theo_thang_so_sanh (014), chỉ đổi
-- trục gộp từ "cả công ty theo tháng" sang "từng nhân viên theo tháng":
--
--   CASE WHEN tr.doanh_thu_thuan > 0
--        THEN t.doanh_thu_thuan::numeric / tr.doanh_thu_thuan - 1 END
--
-- VÌ SAO `> 0` CHỨ KHÔNG PHẢI `<> 0`: doanh thu thuần một tháng của MỘT
-- nhân viên CÓ THỂ ÂM — 赤伝 (phiếu đỏ, hàng trả lại, số ÂM, luật của dự án
-- cấm lọc bỏ) của một người trong một tháng có thể vượt doanh thu dương
-- cùng tháng. `thuc_te = 100.000` chia cho `cung_ky = -50.000` (một giá trị
-- ÂM nhưng KHÁC 0) cho ra `-300%` — trang nói doanh thu SỤT trong khi thật
-- ra nó TĂNG, và không lỗi nào nổ ra để lộ chuyện đó. `> 0` biến ca đó thành
-- NULL (cột `co_cung_ky` vẫn TRUE — xem mục 2 — nên màn hình in "—", không
-- phải "không có dữ liệu"), đúng nếp `mart.tien_do_ngan_sach.tien_do` đã
-- dùng `nullif(muc_tieu, 0)` cho lý do tương tự.
--
-- ---------------------------------------------------------------------------
-- 2) "Không có dữ liệu" bị dùng chung cho hai tình huống khác hẳn nhau
-- ---------------------------------------------------------------------------
--
-- `cung_ky IS NULL` (bản cũ, tính trong Python rồi LEFT JOIN) xảy ra ở HAI
-- tình huống:
--   (a) tháng đó KHÔNG TỒN TẠI trong kho — dữ liệu bán bắt đầu 2025-03-03,
--       trước mốc đó không có dòng nào để có. Đây mới đúng là "không có
--       dữ liệu".
--   (b) tháng đó CÓ dữ liệu nhưng người này không có dòng bán nào trong
--       tháng — sự thật là ¥0, không phải "không biết" (vi phạm ngược của
--       bất biến "0 khác chưa có dữ liệu" mà cả đợt 5a này tồn tại để giữ).
--
-- Cột `co_cung_ky` (= `tr.thang IS NOT NULL`, đúng nếp
-- mart.ban_theo_thang_so_sanh) phân biệt hai ca đó: FALSE chỉ khi
-- `mart.ban_theo_nhan_vien_thang` không có DÒNG nào cho (người, tháng trừ
-- 12) — tức ca (a). Ca (b) vẫn có dòng (LEFT JOIN nguồn dữ liệu là
-- mart.dong_ban qua GROUP BY, một tháng có doanh thu 0 của một người vẫn
-- chỉ xuất hiện nếu có ít nhất một dòng bán — nhưng NẾU người đó có tổng
-- doanh thu đúng bằng 0 mà vẫn có phiếu (ví dụ một phiếu 100 đồng và một
-- phiếu đỏ -100 đồng cùng tháng) thì `co_cung_ky` TRUE và `dt_cung_ky = 0`,
-- và khi đó `tang_truong` là NULL vì `0 > 0` sai — đây CHÍNH XÁC là ca "có
-- dữ liệu, giá trị bằng không, nhưng không tính được % tăng trưởng vì mẫu
-- số bằng 0", ba trạng thái phân biệt được rõ ràng qua (`co_cung_ky`,
-- `dt_cung_ky`, `tang_truong`) mà không cần thêm cột thứ tư.
CREATE VIEW mart.ban_theo_nhan_vien_thang_so_sanh AS
SELECT t.*,
       tr.doanh_thu_thuan     AS dt_cung_ky,
       (tr.thang IS NOT NULL) AS co_cung_ky,
       CASE WHEN tr.doanh_thu_thuan > 0
            THEN t.doanh_thu_thuan::numeric / tr.doanh_thu_thuan - 1 END AS tang_truong
FROM mart.ban_theo_nhan_vien_thang t
LEFT JOIN mart.ban_theo_nhan_vien_thang tr
       ON tr.salesperson_code = t.salesperson_code
      AND tr.thang = to_char(to_date(t.thang, 'YYYY-MM') - interval '1 year', 'YYYY-MM');

COMMENT ON VIEW mart.ban_theo_nhan_vien_thang_so_sanh IS
  'Cùng khuôn mart.ban_theo_thang_so_sanh (014), trục người thay vì trục cả
   công ty. tang_truong dùng `> 0` (KHÔNG `<> 0`) vì doanh thu một tháng của
   một người có thể ÂM do 赤伝 — chia cho một mẫu số âm cho ra phần trăm
   NGƯỢC DẤU. co_cung_ky phân biệt "tháng không tồn tại trong kho" (FALSE)
   với "tháng có dữ liệu, người này bán 0 đồng" (TRUE, dt_cung_ky NULL hoặc
   0 tuỳ nguồn). Có test canh: tests/test_ngan_sach_mart.py.';

-- kome_ingest KHÔNG nằm trong ALTER DEFAULT PRIVILEGES của schema mart (009)
-- — mọi migration thêm view vào mart đều phải kết thúc bằng dòng GRANT này.
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;

-- ---------------------------------------------------------------------------
-- 3) `sua_boi` chặn đúng thủ tục khẩn cấp mà runbook dạy
-- ---------------------------------------------------------------------------
--
-- 026 đặt `sua_boi REFERENCES app.nguoi_dung` với ON DELETE mặc định
-- (NO ACTION) trên CẢ HAI bảng. Ghi chú hoãn lúc đó nói "chưa có đường code
-- nào xoá app.nguoi_dung" — đúng về CODE, sai về VẬN HÀNH:
-- docs/runbook.md (bảng sự cố) và scripts/tao_nguoi_dung.py đều dạy thẳng
-- "cần chặn một người đã nghỉ việc / cần cắt NGAY thì xoá tài khoản: họ bị
-- chặn ở lượt bấm kế tiếp". Cơ chế đó là LOAD-BEARING —
-- kome/web/nguoi_dung.py::theo_id() ghi rõ "None nếu tài khoản đã bị xoá —
-- middleware dựa vào đó".
--
-- Từ 026, tài khoản ĐÃ TỪNG sửa ngân sách (tức chính chủ DN — người DUY
-- NHẤT có `duoc_sua_ngan_sach`) không `DELETE` được nữa, và vì
-- `app.ngan_sach_nhat_ky` là bảng chỉ-thêm không bao giờ xoá dòng, chặn đó
-- là VĨNH VIỄN — đúng người cần cắt quyền khẩn cấp nhất (người có quyền cao
-- nhất) lại là người không xoá được tài khoản.
--
-- SỬA: đổi cả hai khoá ngoại sang ON DELETE SET NULL. NULL đã có nghĩa hợp
-- lệ sẵn ở cả hai bảng — "không có cổng đăng nhập nên không ai là ai" (026
-- viết rõ cho ca máy trong công ty để trống KOME_SESSION_SECRET). GIỮ LẠI
-- DÒNG NHẬT KÝ quan trọng hơn GIỮ LẠI TÊN NGƯỜI SỬA: chỉ tiêu và lịch sử sửa
-- nó là dữ liệu nghiệp vụ sống mãi, còn "ai đổi con số này" là thông tin phụ
-- trợ — mất nó khi tài khoản bị xoá vẫn còn hơn khoá luôn thủ tục xoá tài
-- khoản của runbook.
ALTER TABLE app.ngan_sach
    DROP CONSTRAINT ngan_sach_sua_boi_fkey,
    ADD CONSTRAINT ngan_sach_sua_boi_fkey
        FOREIGN KEY (sua_boi) REFERENCES app.nguoi_dung ON DELETE SET NULL;

ALTER TABLE app.ngan_sach_nhat_ky
    DROP CONSTRAINT ngan_sach_nhat_ky_sua_boi_fkey,
    ADD CONSTRAINT ngan_sach_nhat_ky_sua_boi_fkey
        FOREIGN KEY (sua_boi) REFERENCES app.nguoi_dung ON DELETE SET NULL;
