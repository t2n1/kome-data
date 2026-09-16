-- Khách đã đóng cửa / ngừng giao dịch: OBC ghi thẳng vào TÊN khách.
--
-- Phát hiện khi dựng hồ sơ 360°: 281/2.077 khách hiện hành có dấu ※…※ trong
-- tên. Đo thật ngày 2026-09-17:
--   ※廃業・精算※  210   (đóng cửa, đang thanh lý)
--   ※廃業・清算※   40   (cùng nghĩa — OBC có HAI cách viết, 精算 và 清算)
--   ※取引停止※     13   (ngừng giao dịch)
--   ※廃業※          8
--   ※取引禁止※      4   (cấm giao dịch)
--   ※取引停止・長期間取引なし※ 2 · ※使用禁止※ 2 · ※取引永久禁止※ 1 · ※取引永久※ 1
--
-- Vì sao phải xử lý, chứ không chỉ để đó: cả hệ thống cảnh báo rời bỏ dựa trên
-- "khách này im lặng bất thường". Một doanh nghiệp đã phá sản thì im lặng là
-- ĐÚNG, không phải bất thường. Để lẫn vào thì danh sách "hôm nay nên gọi ai"
-- đầy những số điện thoại không ai bắt máy — và nhân viên bỏ dùng công cụ
-- ngay tuần đầu. Một cảnh báo bị mất tin còn tệ hơn không có cảnh báo.
--
-- Đây KHÔNG phải sửa dữ liệu: tên khách giữ nguyên như OBC xuất ra. Chỉ là
-- ĐỌC thêm cái dấu mà OBC đã ghi sẵn trong đó.
--
-- Nếu sau này công ty dùng một cách đánh dấu khác, sửa ở đây bằng một
-- migration mới — đừng sửa file này.

CREATE VIEW mart.dau_hieu_khach AS
SELECT customer_code,
       customer_name,
       -- Lấy cụm trong cặp ※…※ đầu tiên, nếu có.
       (regexp_match(customer_name, '※([^※]{1,20})※'))[1] AS dau_hieu_obc,
       (customer_name ~ '※[^※]*(廃業|清算|精算|取引停止|取引禁止|取引永久|使用禁止)[^※]*※')
           AS da_ngung
FROM core.dim_customer
WHERE is_current;

COMMENT ON VIEW mart.dau_hieu_khach IS
  'Đọc dấu ※…※ mà OBC ghi trong tên khách. da_ngung = khách đã đóng cửa hoặc
   bị ngừng/cấm giao dịch — đừng đưa vào danh sách gọi lại.';


-- Dựng lại khach_360 có thêm hai cột ở CUỐI (CREATE OR REPLACE chỉ cho thêm
-- cột vào cuối, không cho đổi thứ tự cột đã có).
--
-- `trang_thai` nhận thêm một giá trị: 'ngung_giao_dich'. Nó được xét TRƯỚC mọi
-- nhánh khác — với khách đã đóng cửa thì nhịp mua và số ngày im lặng không còn
-- mang nghĩa gì.
CREATE OR REPLACE VIEW mart.khach_360 AS
SELECT
    k.customer_code,
    coalesce(nullif(d.customer_name, ''), '(chưa có tên)') AS ten,
    d.branch_name, d.phone, d.postcode, d.prefecture, d.city, d.address,
    d.salesperson_code, d.rank_code, d.category_code, d.closing_day_code,
    d.price_level_code, d.spot_flag,

    k.lan_dau, k.lan_cuoi, k.so_lan_mua, k.so_phieu,
    k.doanh_thu_thuan, k.lai_gop,
    k.lai_gop::numeric / nullif(k.doanh_thu_thuan, 0)          AS ty_suat,
    k.doanh_thu_thuan / k.so_lan_mua                            AS gia_tri_tb_moi_lan,
    (m.hom_nay - k.lan_cuoi)                                    AS so_ngay_im_lang,
    n.nhip_ngay,
    n.so_khoang,
    CASE WHEN n.nhip_ngay > 0
         THEN (m.hom_nay - k.lan_cuoi)::numeric / n.nhip_ngay END AS ty_le_im_lang,

    CASE
      WHEN coalesce(h.da_ngung, false) THEN 'ngung_giao_dich'
      WHEN n.nhip_ngay IS NULL OR n.so_khoang < 2 THEN 'chua_du_lich_su'
      WHEN (m.hom_nay - k.lan_cuoi)::numeric / n.nhip_ngay >= 4 THEN 'da_roi_bo'
      WHEN (m.hom_nay - k.lan_cuoi)::numeric / n.nhip_ngay >= 2 THEN 'canh_bao'
      ELSE 'binh_thuong'
    END AS trang_thai,

    h.dau_hieu_obc,
    coalesce(h.da_ngung, false) AS da_ngung
FROM (
    SELECT customer_code,
           min(sales_date) AS lan_dau, max(sales_date) AS lan_cuoi,
           count(DISTINCT sales_date) AS so_lan_mua,
           count(*) AS so_phieu,
           sum(doanh_thu_thuan) AS doanh_thu_thuan,
           sum(lai_gop) AS lai_gop
    FROM mart.lan_mua GROUP BY customer_code
) k
LEFT JOIN core.dim_customer d
       ON d.customer_code = k.customer_code AND d.is_current
LEFT JOIN mart.nhip_mua n ON n.customer_code = k.customer_code
LEFT JOIN mart.dau_hieu_khach h ON h.customer_code = k.customer_code
CROSS JOIN mart.moc_thoi_gian m;

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
