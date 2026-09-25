-- 044 — Mã nội bộ ra khỏi số liệu bán hàng · hạn trả của その都度請求.
--
-- Chủ DN xác nhận 2026-09-25:
--   * `0090…` / `0099…` là mã NHÂN VIÊN mua hàng (0099 = nhân viên cũ, mang
--     ※取引禁止※); `999999999999` ("代引き登録用データ") và `202411000000` (không tên)
--     là mã giữ chỗ của OBC. Tất cả BỎ khỏi web app — kể cả khỏi TỔNG doanh thu
--     (chủ DN chọn: nhân viên mua không phải doanh thu bán hàng). Đo thật 2026-09-25:
--     15 mã nhân viên có phiếu bán, tổng ¥388.667 (≈ 0,02%); hai mã giữ chỗ không có
--     phiếu nào. Hệ quả có chủ ý: tổng doanh thu trên web THẤP hơn sổ OBC đúng phần đó —
--     đối soát tháng phải trừ ra. Trang Kho dữ liệu (độ phủ nạp, đối chiếu tổng file)
--     vẫn đọc thẳng core.fact_sales_line: nó đối chiếu với FILE, nên phải đủ dòng.
--   * その都度請求 trả trong 5 ngày làm việc sau ngày xuất hàng.
--
-- "Mã nội bộ" viết ĐÚNG MỘT LẦN (hàm dưới). Lọc ở mart.ban_den_moc — lớp mọi view
-- bán hàng đều đọc (bất biến 040) — nên danh sách khách, hạng, cần liên hệ, bản đồ,
-- báo cáo, dự báo, sản phẩm cùng bỏ một tập, không chỗ nào tự chép điều kiện.
-- Dữ liệu trong core KHÔNG bị xoá hay sửa (OBC chỉ đọc).

CREATE FUNCTION mart.la_ma_noi_bo(ma text) RETURNS boolean
LANGUAGE sql IMMUTABLE
AS $$ SELECT coalesce(ma ~ '^00(90|99)' OR ma IN ('999999999999', '202411000000'), false) $$;

COMMENT ON FUNCTION mart.la_ma_noi_bo(text) IS
  'Mã khách NỘI BỘ, không phải khách hàng: 0090…/0099… = nhân viên mua hàng; 999999999999, 202411000000 = mã giữ chỗ OBC. Chủ DN xác nhận 2026-09-25.';

-- Thân như 040, thêm điều kiện mã nội bộ. `f.*` giữ đúng danh sách cột hiện có.
CREATE OR REPLACE VIEW mart.ban_den_moc AS
SELECT f.*
FROM core.fact_sales_line f
WHERE f.sales_date <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date))
  AND NOT mart.la_ma_noi_bo(f.customer_code);

-- Thân như 040, thêm điều kiện: mã nội bộ không có phiếu bán (sau lọc) thì cũng
-- không được hiện thành "khách chưa mua".
CREATE OR REPLACE VIEW mart.khach_chua_mua AS
SELECT d.customer_code,
       coalesce(nullif(d.customer_name, ''), '(chưa có tên)') AS ten,
       d.prefecture, d.city, d.phone, d.salesperson_code, d.category_code
FROM core.dim_customer d
WHERE d.is_current
  AND NOT mart.la_ma_noi_bo(d.customer_code)
  AND NOT EXISTS (SELECT 1 FROM mart.ban_den_moc f
                  WHERE f.customer_code = d.customer_code);

-- mart.cong_no_phieu — thân như 038, thêm MỘT mẫu hạn trả: その都度請求.
-- Công nợ đọc sổ 請求先元帳 (không qua ban_den_moc) và KHÔNG lọc mã nội bộ: sổ
-- công nợ là số tiền thật phải thu, nhân viên nợ thì vẫn là nợ.
CREATE OR REPLACE VIEW mart.cong_no_phieu AS
WITH s AS MATERIALIZED (SELECT * FROM mart.so_cong_no_moi_nhat),
b AS (
    SELECT billing_customer_code, so_du
    FROM mart.cong_no_ben_tra WHERE so_du > 0
),
p AS (
    SELECT s.billing_customer_code, s.slip_no, s.entry_date, s.receivable_amount,
           s.closing_day_name, s.period_from, s.period_to, s.row_seq, b.so_du,
           sum(s.receivable_amount) OVER (PARTITION BY s.billing_customer_code
               ORDER BY s.entry_date DESC, s.row_seq DESC
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cong_moi_hon
    FROM s JOIN b USING (billing_customer_code)
    WHERE s.line_kind = 'phieu_ban' AND s.receivable_amount > 0
),
c AS (
    SELECT p.*,
           greatest(0, least(p.receivable_amount,
                             p.so_du - (p.cong_moi_hon - p.receivable_amount))) AS con_lai
    FROM p
),
tk AS (
    SELECT b.billing_customer_code,
           b.so_du - coalesce((SELECT sum(receivable_amount) FROM p
                               WHERE p.billing_customer_code = b.billing_customer_code), 0) AS con_lai,
           (SELECT min(period_from) FROM s) AS period_from,
           (SELECT min(period_to) FROM s)   AS period_to,
           (SELECT max(closing_day_name) FROM s
             WHERE s.billing_customer_code = b.billing_customer_code) AS closing_day_name
    FROM b
),
tat_ca AS (
    SELECT billing_customer_code, 'phieu'::text AS loai, slip_no, entry_date,
           receivable_amount AS tong, con_lai, closing_day_name, period_to
    FROM c WHERE con_lai > 0
    UNION ALL
    SELECT billing_customer_code, 'truoc_ky', NULL, NULL,
           NULL, con_lai, closing_day_name, period_to
    FROM tk WHERE con_lai > 0
),
h AS (
    SELECT t.*,
           CASE
             WHEN t.entry_date IS NULL THEN NULL
             WHEN t.closing_day_name = '末締/翌月末日'
               THEN (date_trunc('month', t.entry_date) + interval '2 month - 1 day')::date
             WHEN t.closing_day_name ~ '^末締/翌月[0-9]{1,2}日$'
               THEN (date_trunc('month', t.entry_date) + interval '1 month')::date
                    + (substring(t.closing_day_name FROM '翌月([0-9]{1,2})日')::int - 1)
             -- 044: その都度請求 = trả trong 5 NGÀY LÀM VIỆC sau ngày xuất hàng (ngày
             -- phiếu). Ngày làm việc = mart.lich_kinh_doanh.la_ngay_kd — định nghĩa duy
             -- nhất (không thứ Bảy/Chủ nhật, không lễ quốc gia; ngày nghỉ RIÊNG của công
             -- ty chưa có nguồn — hạn chế đã ghi ở CLAUDE.md).
             WHEN t.closing_day_name = 'その都度請求'
               THEN (SELECT l.ngay FROM mart.lich_kinh_doanh l
                      WHERE l.ngay > t.entry_date AND l.la_ngay_kd
                      ORDER BY l.ngay OFFSET 4 LIMIT 1)
           END AS han_tra
    FROM tat_ca t
)
SELECT billing_customer_code, loai, slip_no, entry_date, tong, con_lai,
       CASE WHEN tong IS NULL THEN NULL ELSE tong - con_lai END AS da_thu,
       closing_day_name AS dieu_kien, han_tra, period_to AS moc,
       CASE WHEN entry_date IS NULL THEN NULL ELSE period_to - entry_date END AS tuoi_ngay,
       CASE WHEN han_tra IS NULL THEN NULL ELSE period_to - han_tra END AS qua_han_ngay,
       CASE
         WHEN entry_date IS NULL               THEN 'truoc_ky'
         WHEN period_to - entry_date <= 30     THEN 'd30'
         WHEN period_to - entry_date <= 60     THEN 'd60'
         WHEN period_to - entry_date <= 90     THEN 'd90'
         ELSE 'd90p'
       END AS nhom_tuoi
FROM h;
