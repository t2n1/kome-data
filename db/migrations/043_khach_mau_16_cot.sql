-- 043 — 得意先全情報 theo mẫu xuất 16 cột (chủ DN chốt 2026-09-25).
--
-- Mẫu mới THÊM năm cột: ビル等 (building), ランク名 (rank_name), 売上主担当者名
-- (salesperson_name), 請求締日名 (closing_day_name), 振込専用口座番号１
-- (transfer_account — tài khoản chuyển khoản riêng của khách, để sale tra khi có
-- tiền về; TEXT, giữ số 0 đầu).
--
-- Mẫu mới BỎ sáu cột: 業種・カテゴリーコード, 注文アプリコード, 売価No.コード,
-- 請求先コード, インボイス登録番号, スポット区分コード. Cột trong bảng GIỮ NGUYÊN
-- (SCD2 là lịch sử — không xoá), nhưng bộ nạp không ghi chúng nữa, nên phiên bản mới
-- mang NULL. Không chỗ nào của web app được đọc sáu cột đó từ core.dim_customer nữa.

ALTER TABLE core.dim_customer
    ADD COLUMN building         text,
    ADD COLUMN rank_name        text,
    ADD COLUMN salesperson_name text,
    ADD COLUMN closing_day_name text,
    ADD COLUMN transfer_account text;

-- Bên nhận hoá đơn (請求先) của một khách — MỘT định nghĩa, hai chỗ đọc: tab Công
-- nợ của hồ sơ khách (kome/cong_no.py::cua_khach) và cột `so_khach` của
-- mart.cong_no_ben_tra.
--
-- Nguồn = 請求先コード trên PHIẾU BÁN gần nhất của khách (tới mốc: đọc
-- mart.ban_den_moc, bất biến 040). Đo thật 2026-09-25 (chỉ đọc): phiếu bán gần nhất
-- khớp 請求先コード của master ở 1.704/1.710 khách có bán; 6 khách còn lại đã đổi bên
-- nhận hoá đơn — phiếu mới nhất là cái OBC thật sự đang ghi nợ. Khách chưa có phiếu
-- bán nào thì tự là bên của chính mình (một 請求先 cũng là một mã 得意先 trong OBC) —
-- khách đó không có công nợ phát sinh từ bán hàng.
CREATE VIEW mart.ben_tra_cua_khach AS
WITH s AS (
    SELECT DISTINCT ON (customer_code) customer_code, billing_customer_code
      FROM mart.ban_den_moc
     WHERE nullif(billing_customer_code, '') IS NOT NULL
     ORDER BY customer_code, sales_date DESC, slip_no DESC, line_seq DESC
)
SELECT d.customer_code,
       coalesce(s.billing_customer_code, d.customer_code) AS billing_customer_code,
       (s.customer_code IS NOT NULL)                       AS tu_phieu_ban
  FROM core.dim_customer d
  LEFT JOIN s ON s.customer_code = d.customer_code
 WHERE d.is_current;

COMMENT ON VIEW mart.ben_tra_cua_khach IS
  '請求先 của từng khách = 請求先コード trên phiếu bán gần nhất (≤ mốc); chưa có phiếu bán thì là chính khách. 043: master 得意先全情報 không còn cột 請求先コード.';

-- mart.cong_no_ben_tra — thân như 038, chỉ đổi `so_khach`: đếm khách theo
-- mart.ben_tra_cua_khach (gộp MỘT lần rồi nối), không theo cột
-- core.dim_customer.billing_customer_code đã bỏ.
CREATE OR REPLACE VIEW mart.cong_no_ben_tra AS
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
),
bk AS (
    SELECT billing_customer_code, count(*) AS so_khach
      FROM mart.ben_tra_cua_khach GROUP BY 1
)
SELECT g.billing_customer_code,
       coalesce(nullif(c.customer_name, ''), g.ten_so)                    AS ten,
       g.closing_day_code, g.dieu_kien, g.ky_tu, g.ky_den,
       g.mang_sang, g.ban_chiu_ky, g.so_du,
       (g.mang_sang + g.ban_chiu_ky + g.dieu_chinh_no - g.dieu_chinh_thu - g.so_du) AS da_thu_ky,
       g.lan_thu_cuoi, g.lan_ban_cuoi, g.so_phieu_ban,
       c.salesperson_code,
       coalesce(bk.so_khach, 0)                                           AS so_khach
FROM g
LEFT JOIN core.dim_customer c
       ON c.customer_code = g.billing_customer_code AND c.is_current
LEFT JOIN bk ON bk.billing_customer_code = g.billing_customer_code;
