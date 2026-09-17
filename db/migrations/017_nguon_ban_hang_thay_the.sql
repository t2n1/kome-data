-- db/migrations/017_nguon_ban_hang_thay_the.sql
-- Cho core.fact_sales_line nhận dữ liệu từ HAI loại file OBC: 売上伝票データ
-- (uriage, đã có từ đầu) và 売上明細表 (meisai, dự phòng khi tương lai không
-- lấy được 売上伝票データ). Đối chiếu thật cùng ngày 2026-08-03 (sau khử
-- trùng): 粗利益/消費税額/原価 khớp TUYỆT ĐỐI, 金額 lệch 55/6.753.717đ (làm
-- tròn thuế khác cách — xem docs/cot-day-du-ban-hang.md).
ALTER TABLE core.fact_sales_line
    ADD COLUMN source text NOT NULL DEFAULT 'uriage';

ALTER TABLE core.fact_sales_line DROP CONSTRAINT fact_sales_line_pkey;
ALTER TABLE core.fact_sales_line ADD PRIMARY KEY (slip_no, line_seq, source);

CREATE INDEX ON core.fact_sales_line (source, sales_date);

COMMENT ON COLUMN core.fact_sales_line.source IS
  '''uriage'' = 売上伝票データ, 明細行番号 THẬT từ OBC. ''meisai'' = 売上明細表, '
  'KHÔNG có 明細行番号 trong file gốc -- reader tự sinh line_seq bằng số thứ '
  'tự xuất hiện trong file theo từng 伝票No. (xem synthesize_line_seq trong '
  'kome/reader.py). Ổn định khi nạp lại CÙNG một file, KHÔNG đảm bảo khớp '
  'nếu OBC xuất lại cùng kỳ với thứ tự dòng khác trong lần xuất sau. CHỈ '
  'nạp MỘT trong hai nguồn cho cùng một ngày -- pipeline.ingest() tự chặn '
  'nếu ngày đó đã có dữ liệu từ nguồn kia (xem _kiem_tra_trung_nguon).';
