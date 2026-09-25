-- 046 — 売上明細表 theo MẪU XUẤT HẰNG NGÀY (20 cột).
--
-- Tên cũ `043_meisai_mau_hang_ngay.sql` (trùng số với 043_khach_mau_16_cot của
-- nhánh khác); CSDL thật đã chạy nó dưới tên cũ ngày 2026-09-25 nên
-- meta.schema_migration còn một dòng tên đó. Mọi câu dưới đây chạy lại vô hại
-- (DROP NOT NULL, COMMENT) — lần migrate sau chạy lại 046 là đúng ý.
--
-- Đo thật 2026-09-25 (`売上明細表_20260925.xlsx`): bản xuất hằng ngày chỉ còn 20
-- cột — 20 cột ĐẦU của bản 117 cột cũ (2026-08-03), giống hệt thứ tự. Tám cột
-- bản cũ có mà bản mới không: 伝票区分, 部門コード, 入数, 単位原価, 税込純売上高,
-- 消費税額, 売上原価, 消費税率. Chưa màn nào đọc sáu trong số đó (chỉ lưu); hai
-- cột tiền thì chỉ dùng qua hiệu `amount - tax_amount`.
--
-- Hai quyết định, cả hai ở tầng NẠP (config/files.yml mục meisai,
-- kome/loaders/sales.py::load_meisai), migration này chỉ nới ràng buộc + ghi
-- nghĩa cột:
--
-- 1. DOANH THU: với source = 'meisai', `amount` = 税抜純売上高 (CHƯA thuế) và
--    `tax_amount` = 0. Mọi view mart tính doanh thu thuần là
--    `amount - tax_amount`, nên con số trên màn không đổi nghĩa. Đo trên bản
--    117 cột: 税抜純売上高 = 税込純売上高 − 消費税額 ở 926/926 dòng, lệch 0.
--    Hệ quả phải nhớ: `amount` THÔ không còn cùng nghĩa giữa hai nguồn (uriage
--    có thuế, meisai chưa thuế) — không bao giờ cộng thẳng `amount` qua hai
--    nguồn; tổng tiền của lô meisai (meta.ingest_batch.total_amount) là số
--    CHƯA thuế.
--
-- 2. CỘT KHÔNG CÓ TRONG FILE = NULL, không phải 0. `case_qty`, `unit_cost`,
--    `cost` là NOT NULL DEFAULT 0 từ 007; ghi 0 là nói "giá vốn bằng không" —
--    đọc ở màn "Xem một bảng" ra một sự thật sai. Bỏ NOT NULL, GIỮ DEFAULT 0
--    (bộ nạp uriage vẫn ghi đủ số). Không view mart nào làm tính toán trên ba
--    cột này (040 `ban_den_moc` chỉ chuyển tiếp).
ALTER TABLE core.fact_sales_line ALTER COLUMN case_qty  DROP NOT NULL;
ALTER TABLE core.fact_sales_line ALTER COLUMN unit_cost DROP NOT NULL;
ALTER TABLE core.fact_sales_line ALTER COLUMN cost      DROP NOT NULL;

COMMENT ON COLUMN core.fact_sales_line.amount IS
  'uriage: 金額 (CÓ thuế). meisai: 税抜純売上高 (CHƯA thuế, tax_amount = 0 — '
  'migration 046). Doanh thu thuần LUÔN là amount - tax_amount; không cộng '
  'thẳng amount qua hai nguồn.';
COMMENT ON COLUMN core.fact_sales_line.tax_amount IS
  'uriage: 消費税額. meisai: 0 — bản xuất hằng ngày không có thuế, amount đã '
  'là số chưa thuế (migration 046).';
