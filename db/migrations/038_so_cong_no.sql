-- 038 — Đợt 6: sổ công nợ theo BÊN NHẬN HOÁ ĐƠN (請求先元帳) + mart công nợ.
--
-- Nguồn: file OBC `請求先元帳`, đo thật 2026-09-24 (bản 2026-05-01 → 2026-07-31):
-- 5 dòng thông tin + 1 dòng header (header ở dòng 6 — bẫy #4 ĐÚNG với 元帳), 20
-- cột, 20.427 dòng, 215 bên nhận hoá đơn. Mỗi bên: một dòng `繰越残高` (số dư mang
-- sang đầu kỳ), các dòng chi tiết (phiếu bán: 債権額 có giá trị; phiếu thu: 入金額
-- có giá trị), và các dòng tổng phụ (伝票計 / ［ n月計］ / 【合計】). Bộ nạp GIỮ
-- dòng mang sang + dòng chi tiết, BỎ dòng tổng phụ sau khi đã dùng 【合計】 để đối
-- chiếu (cổng 5): mang sang + 債権額 + 債権調整額 − 入金額 − 入金調整額 = 残高 cuối.
-- Đo thật: 215/215 bên khớp tuyệt đối khi đối chiếu với 【合計】 — nhưng 12 bên
-- LỆCH nếu cộng tay 入金額 của từng dòng: nhóm mã 0090000000xx có phiếu thu mà
-- 残高 không đổi (phiếu bán 債権額 = 0). Nên số dư LUÔN lấy từ cột 残高 của OBC,
-- không tự cộng lại, và "đã thu trong kỳ" suy từ đẳng thức trên chứ không cộng
-- 入金額 từng dòng.
--
-- Mô hình: MỖI FILE LÀ MỘT ẢNH CHỤP của một kỳ (`period_from` → `period_to`, đọc từ
-- dòng 集計期間 của chính file). Không xoá/ghi đè lô cũ khi nạp lô mới; mart đọc
-- lô có `period_to` MỚI NHẤT (hoà thì lô nạp sau). Hoàn tác xoá dòng theo
-- `batch_id` như mọi bảng `core` — lô trước tự quay lại làm bản mới nhất.
CREATE TABLE core.fact_ar_ledger (
    batch_id              bigint  NOT NULL REFERENCES meta.ingest_batch(batch_id),
    row_seq               integer NOT NULL,          -- thứ tự dòng trong file (sau khi bỏ tổng phụ)
    billing_customer_code text    NOT NULL,          -- 請求先コード (TEXT, giữ số 0 đầu)
    billing_customer_name text,
    closing_day_code      text,
    closing_day_name      text,                      -- 請求締日名, vd. '末締/翌月10日'
    line_kind             text    NOT NULL CHECK (line_kind IN ('mang_sang', 'phieu_ban', 'phieu_thu')),
    entry_date            date,                      -- NULL ở dòng mang sang
    slip_no               text,
    bank_name             text,                      -- 法人口座名 (phiếu thu)
    receivable_amount     bigint  NOT NULL DEFAULT 0, -- 債権額
    receivable_adj        bigint  NOT NULL DEFAULT 0, -- 債権調整額
    sales_amount          bigint  NOT NULL DEFAULT 0, -- 売上額
    tax_amount            bigint  NOT NULL DEFAULT 0, -- 消費税額
    payment_amount        bigint  NOT NULL DEFAULT 0, -- 入金額
    payment_adj           bigint  NOT NULL DEFAULT 0, -- 入金調整額
    balance               bigint  NOT NULL DEFAULT 0, -- 残高 (số dư chạy, của OBC)
    memo                  text,
    period_from           date    NOT NULL,
    period_to             date    NOT NULL,
    PRIMARY KEY (batch_id, row_seq)
);
CREATE INDEX ON core.fact_ar_ledger (billing_customer_code);

COMMENT ON TABLE core.fact_ar_ledger IS
  'Sổ công nợ theo 請求先 (請求先元帳). Mỗi lô là ảnh chụp một kỳ; mart đọc lô period_to mới nhất. Số dư = cột 残高 của OBC, KHÔNG tự cộng lại.';

-- Lô sổ công nợ đang dùng: kỳ kết thúc muộn nhất, hoà thì lô nạp sau.
CREATE VIEW mart.so_cong_no_moi_nhat AS
SELECT l.*
FROM core.fact_ar_ledger l
WHERE l.batch_id = (
    SELECT a.batch_id
    FROM core.fact_ar_ledger a
    JOIN meta.ingest_batch b ON b.batch_id = a.batch_id AND b.undone_at IS NULL
    ORDER BY a.period_to DESC, a.batch_id DESC
    LIMIT 1);

-- Công nợ theo bên nhận hoá đơn — MỘT dòng mỗi 請求先 của lô mới nhất.
--   so_du      = 残高 của dòng cuối cùng (theo row_seq) — số của OBC.
--   da_thu_ky  = mang sang + Σ債権額 + Σ債権調整 − Σ入金調整 − số dư: phần 入金額
--                THẬT SỰ làm giảm số dư (đẳng thức đã đối chiếu ở cổng 5).
--   nguoi phụ trách / tên / số khách: từ core.dim_customer hiện hành (mã 請求先
--   cũng là một mã 得意先 trong OBC).
CREATE VIEW mart.cong_no_ben_tra AS
WITH s AS MATERIALIZED (SELECT * FROM mart.so_cong_no_moi_nhat),
g AS (
    SELECT billing_customer_code,
           max(billing_customer_name)                                     AS ten_so,
           max(closing_day_code)                                          AS closing_day_code,
           max(closing_day_name)                                          AS dieu_kien,
           min(period_from)                                               AS ky_tu,
           min(period_to)                                                 AS ky_den,
           coalesce(sum(balance) FILTER (WHERE line_kind = 'mang_sang'), 0) AS mang_sang,
           sum(receivable_amount)                                         AS ban_chiu_ky,
           sum(receivable_adj)                                            AS dieu_chinh_no,
           sum(payment_adj)                                               AS dieu_chinh_thu,
           (array_agg(balance ORDER BY row_seq DESC))[1]                  AS so_du,
           max(entry_date) FILTER (WHERE line_kind = 'phieu_thu')         AS lan_thu_cuoi,
           max(entry_date) FILTER (WHERE line_kind = 'phieu_ban')         AS lan_ban_cuoi,
           count(*) FILTER (WHERE line_kind = 'phieu_ban' AND receivable_amount <> 0) AS so_phieu_ban
    FROM s GROUP BY billing_customer_code
)
SELECT g.billing_customer_code,
       coalesce(nullif(c.customer_name, ''), g.ten_so)                    AS ten,
       g.closing_day_code, g.dieu_kien, g.ky_tu, g.ky_den,
       g.mang_sang, g.ban_chiu_ky, g.so_du,
       (g.mang_sang + g.ban_chiu_ky + g.dieu_chinh_no - g.dieu_chinh_thu - g.so_du) AS da_thu_ky,
       g.lan_thu_cuoi, g.lan_ban_cuoi, g.so_phieu_ban,
       c.salesperson_code,
       (SELECT count(*) FROM core.dim_customer k
         WHERE k.is_current AND k.billing_customer_code = g.billing_customer_code) AS so_khach
FROM g
LEFT JOIN core.dim_customer c
       ON c.customer_code = g.billing_customer_code AND c.is_current;

-- Phiếu còn nợ — chia số dư dương vào các phiếu bán theo giả định TRẢ CŨ TRƯỚC
-- (FIFO): phần còn nợ là của các phiếu MỚI NHẤT. Đi từ phiếu mới nhất về cũ, mỗi
-- phiếu nhận min(債権額, phần số dư chưa chia). Phần số dư lớn hơn tổng phiếu
-- trong kỳ là nợ MANG SANG từ trước kỳ (loai = 'truoc_ky', không có số phiếu).
-- OBC không ghi phiếu nào đã được trả — đây là giả định, màn hình in nguyên câu.
--
-- Hạn trả suy từ TÊN điều kiện (請求締日名), chỉ hai mẫu đọc được chắc chắn:
--   '末締/翌月末日' → chốt cuối tháng của phiếu, trả cuối tháng sau;
--   '末締/翌月N日'  → chốt cuối tháng của phiếu, trả ngày N tháng sau.
-- Mọi điều kiện khác (代引請求, その都度請求, 前払い, …) → han_tra NULL = "không
-- suy được hạn", KHÔNG bị tính là quá hạn.
-- Tuổi nợ đo từ NGÀY PHIẾU tới cuối kỳ sổ (period_to — mốc dữ liệu, không phải
-- đồng hồ thật), một định nghĩa cho mọi điều kiện trả.
CREATE VIEW mart.cong_no_phieu AS
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
