-- Hồ sơ khách hàng 360° và trạng thái quan hệ.
--
-- Ý tưởng trung tâm: **mỗi khách có nhịp mua riêng.** Một quán ăn lấy hàng 7
-- ngày/lần mà im 20 ngày là chuyện lớn; một tiệm tạp hoá 60 ngày/lần mà im 20
-- ngày thì bình thường. Một ngưỡng chung ("90 ngày không mua") sẽ báo động
-- nhầm ở nhóm sau và **im lặng** ở nhóm trước — tức là bỏ sót đúng những khách
-- đang rời đi nhanh nhất.
--
-- Nên trạng thái tính bằng TỶ LỆ giữa số ngày im lặng và nhịp mua của CHÍNH
-- khách đó, chứ không bằng số ngày tuyệt đối.

CREATE SCHEMA IF NOT EXISTS mart;

-- Ngày bán mới nhất trong kho = "hôm nay" của mọi phép tính ở đây.
-- KHÔNG dùng current_date: dữ liệu được nạp theo mẻ, và nếu hôm nay chưa ai
-- nạp file thì current_date sẽ biến cả 1.710 khách thành "im lặng thêm 1 ngày"
-- — cảnh báo nhảy loạn vì lý do không liên quan gì tới khách hàng.
CREATE VIEW mart.moc_thoi_gian AS
SELECT max(sales_date) AS hom_nay FROM core.fact_sales_line;


-- Một dòng mỗi lần khách đặt hàng (gộp các dòng cùng phiếu, cùng ngày).
CREATE VIEW mart.lan_mua AS
SELECT customer_code, sales_date, slip_no,
       sum(amount - tax_amount) AS doanh_thu_thuan,
       sum(gross_profit)        AS lai_gop,
       count(*)                 AS so_dong
FROM core.fact_sales_line
GROUP BY customer_code, sales_date, slip_no;


CREATE VIEW mart.khoang_cach_mua AS
SELECT customer_code, sales_date,
       sales_date - lag(sales_date) OVER (PARTITION BY customer_code
                                          ORDER BY sales_date) AS so_ngay_cach
FROM (SELECT DISTINCT customer_code, sales_date FROM mart.lan_mua) x;


-- Nhịp mua: dùng TRUNG VỊ chứ không phải trung bình. Một khách mua đều 7 ngày
-- một lần rồi nghỉ Tết 30 ngày sẽ có trung bình ~9 ngày — đủ để làm ngưỡng
-- cảnh báo lệch đi. Trung vị bỏ qua những lần bất thường đó.
CREATE VIEW mart.nhip_mua AS
SELECT customer_code,
       count(*)                                                   AS so_khoang,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY so_ngay_cach)   AS nhip_ngay
FROM mart.khoang_cach_mua
WHERE so_ngay_cach IS NOT NULL
GROUP BY customer_code;


CREATE VIEW mart.khach_360 AS
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

    -- Tỷ lệ im lặng: 1,0 = đúng bằng nhịp thường lệ, 3,0 = im gấp ba lần.
    CASE WHEN n.nhip_ngay > 0
         THEN (m.hom_nay - k.lan_cuoi)::numeric / n.nhip_ngay END AS ty_le_im_lang,

    CASE
      -- Chưa đủ 3 lần mua thì CHƯA BIẾT nhịp của khách này. Đoán bừa một nhịp
      -- rồi báo động là cách nhanh nhất làm nhân viên mất tin vào cảnh báo.
      WHEN n.nhip_ngay IS NULL OR n.so_khoang < 2 THEN 'chua_du_lich_su'
      WHEN (m.hom_nay - k.lan_cuoi)::numeric / n.nhip_ngay >= 4 THEN 'da_roi_bo'
      WHEN (m.hom_nay - k.lan_cuoi)::numeric / n.nhip_ngay >= 2 THEN 'canh_bao'
      ELSE 'binh_thuong'
    END AS trang_thai
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
CROSS JOIN mart.moc_thoi_gian m;

COMMENT ON VIEW mart.khach_360 IS
  'Một dòng mỗi khách ĐÃ TỪNG MUA. Khách có hồ sơ nhưng chưa mua lần nào KHÔNG
   xuất hiện ở đây — xem mart.khach_chua_mua.
   trang_thai so số ngày im lặng với NHỊP MUA RIÊNG của khách đó, không so với
   một ngưỡng chung: 90 ngày im lặng là thảm hoạ với khách mua hằng tuần và là
   bình thường với khách mua hai tháng một lần.';


-- Có hồ sơ mà chưa từng mua: 370 khách. Đây là danh sách bán hàng, không phải
-- danh sách lỗi — nhưng nếu một khách mở hồ sơ đã lâu mà chưa mua gì thì đáng
-- hỏi vì sao.
CREATE VIEW mart.khach_chua_mua AS
SELECT d.customer_code,
       coalesce(nullif(d.customer_name, ''), '(chưa có tên)') AS ten,
       d.prefecture, d.city, d.phone, d.salesperson_code, d.category_code
FROM core.dim_customer d
WHERE d.is_current
  AND NOT EXISTS (SELECT 1 FROM core.fact_sales_line f
                  WHERE f.customer_code = d.customer_code);


-- Mặt hàng của một khách — để hồ sơ 360° trả lời "khách này mua gì" và
-- "khách này đã NGỪNG mua gì".
CREATE VIEW mart.khach_mat_hang AS
SELECT f.customer_code, f.product_code,
       coalesce(nullif(s.product_name, ''), f.product_code) AS ten_hang,
       sum(f.amount - f.tax_amount) AS doanh_thu_thuan,
       sum(f.gross_profit)          AS lai_gop,
       sum(f.qty)                   AS so_luong,
       count(DISTINCT f.sales_date) AS so_lan,
       min(f.sales_date)            AS lan_dau,
       max(f.sales_date)            AS lan_cuoi
FROM core.fact_sales_line f
LEFT JOIN core.dim_product s ON s.product_code = f.product_code
GROUP BY f.customer_code, f.product_code, s.product_name;


-- Doanh thu theo tháng của một khách — vẽ đường lịch sử trên hồ sơ 360°.
CREATE VIEW mart.khach_theo_thang AS
SELECT customer_code,
       to_char(sales_date, 'YYYY-MM') AS thang,
       sum(doanh_thu_thuan) AS doanh_thu_thuan,
       sum(lai_gop)         AS lai_gop,
       count(DISTINCT sales_date) AS so_lan_mua
FROM mart.lan_mua
GROUP BY customer_code, to_char(sales_date, 'YYYY-MM');


GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
