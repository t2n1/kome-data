-- 023: chỉ số của màn Sản phẩm và màn Kho hàng (đợt 4b).
--
-- KHÔNG có MATERIALIZED VIEW — xem lý do ở 020_mart_khach_360.sql.

-- Tốc độ bán: TRUNG BÌNH số lượng mỗi ngày trong 90 ngày gần nhất.
--
-- KHÁC mart.nhip_mua (trung vị) MỘT CÁCH CÓ CHỦ Ý, và đây là chỗ người đọc sau
-- rất dễ "sửa cho nhất quán" rồi làm hỏng một trong hai:
--   * nhip_mua hỏi "khoảng cách ĐIỂN HÌNH giữa hai lần mua" — một kỳ nghỉ Tết
--     kéo trung bình lệch, nên phải dùng trung vị.
--   * toc_do_ban hỏi "bao nhiêu ngày nữa thì hết hàng" — đó là một phép chia
--     trên TỔNG lượng đã bán, nên trung bình mới đúng.
-- Hai câu hỏi khác nhau, hai công thức khác nhau.
--
-- 90 ngày chứ không phải cả lịch sử: hàng thực phẩm đổi mùa, và một mã bán chạy
-- năm ngoái mà ba tháng nay không ai mua thì trung bình toàn lịch sử sẽ nói dối
-- theo đúng hướng nguy hiểm — nó bảo hàng còn chạy trong khi nó đang chết.
CREATE VIEW mart.toc_do_ban AS
SELECT f.product_code,
       sum(f.qty)                        AS so_luong_90n,
       sum(f.amount - f.tax_amount)      AS doanh_thu_90n,
       sum(f.qty) / 90.0                 AS toc_do_ngay
FROM core.fact_sales_line f, mart.moc_thoi_gian m
WHERE f.sales_date > m.hom_nay - 90
GROUP BY f.product_code;


-- Tồn hiện tại: ảnh chụp MỚI NHẤT, một dòng mỗi (mã, kho).
--
-- best_before là TEXT và có ba dạng thật trong dữ liệu: '2028年06月09日',
-- '賞味期限なし' (không có hạn sử dụng), và rỗng. to_date() TRẦN trên cột này
-- làm cả truy vấn nổ và trang trắng — và nó chỉ nổ khi trong kho có đúng loại
-- hàng đó, tức sau khi đã triển khai. Kiểm dạng bằng regex trước.
CREATE VIEW mart.ton_hien_tai AS
SELECT i.product_code, i.warehouse_code, w.warehouse_name AS ten_kho,
       i.stock_qty AS so_luong, i.stock_value AS gia_tri, i.best_before,
       CASE WHEN i.best_before ~ '^[0-9]{4}年[0-9]{2}月[0-9]{2}日$' THEN 'ngay'
            WHEN coalesce(i.best_before, '') = ''                  THEN 'trong'
            ELSE 'khong_han' END AS loai_han,
       CASE WHEN i.best_before ~ '^[0-9]{4}年[0-9]{2}月[0-9]{2}日$'
            THEN to_date(i.best_before, 'YYYY"年"MM"月"DD"日"') - m.hom_nay
       END AS han_con_lai
FROM core.fact_inventory_daily i
JOIN core.dim_warehouse w ON w.warehouse_code = i.warehouse_code
CROSS JOIN mart.moc_thoi_gian m
WHERE i.snapshot_date = (SELECT max(snapshot_date) FROM core.fact_inventory_daily);

COMMENT ON VIEW mart.ton_hien_tai IS
  'Tên kho đọc từ core.dim_warehouse, không viết cứng — thêm kho mới trong OBC
   thì tự xuất hiện, không cần sửa view này.';


-- Hồ sơ 360° của một mã hàng: doanh thu/lãi gộp toàn bộ lịch sử, tồn hiện tại,
-- tốc độ bán, và trạng thái cần chú ý.
CREATE VIEW mart.san_pham_360 AS
SELECT
    p.product_code,
    coalesce(nullif(p.product_name, ''), p.product_code) AS ten_hang,
    p.kind_name                                          AS nhom,
    b.doanh_thu_thuan,
    b.lai_gop,
    -- nullif: mã chưa bán được đồng nào thì tỷ suất là NULL ("chưa có số"),
    -- không phải 0% (đọc thành "bán mà không lãi đồng nào") — y hệt 021.
    b.lai_gop::numeric / nullif(b.doanh_thu_thuan, 0)    AS ty_suat,
    b.so_luong_ban,
    -- "Không biết" khác "bằng không": 90/232 mã không có dòng tồn nào trong
    -- 在庫一覧. t.ton đến từ LEFT JOIN nên tự nhiên là NULL khi không có dòng —
    -- TUYỆT ĐỐI không coalesce cột này. 0 nói với người đọc "kho đã hết", còn
    -- NULL nói "chưa từng nhập kho hoặc không nằm trong bản xuất tồn kho" —
    -- hai điều khác nhau, và cái đầu xui người ta đi đặt hàng oan.
    t.ton,
    v.toc_do_ngay,
    -- Số ngày còn đủ bán = tồn chia tốc độ. toc_do_ngay = 0 hoặc NULL (mã
    -- không bán trong 90 ngày) thì không chia được — để NULL, không phải 0
    -- hay vô cực.
    CASE WHEN v.toc_do_ngay > 0 THEN t.ton / v.toc_do_ngay END AS du_ban_ngay,
    CASE
      -- Mã mới ra mắt trong 90 ngày KHÔNG bao giờ là tồn chết: bán chậm ở
      -- tuần đầu là chuyện bình thường, gắn nhãn tồn chết là xúi người ta
      -- xả một mã vừa mua về. NHƯNG "mới" một mình không đủ — một mã đã bán
      -- được VÀI LẦN (đo bằng so_lan_mua, y hệt "chưa đủ lịch sử" của
      -- mart.nhip_mua ở 015/020 dùng so_khoang) mà đã tích một núi tồn thì
      -- vẫn là tồn chết thật, bất kể lần bán đầu tiên cách đây bao lâu. Thiếu
      -- vế thứ hai này thì MỌI mã có lịch sử bán ngắn hơn 90 ngày — kể cả một
      -- mã đã bán đều 3 lần rồi im — sẽ luôn thoát khỏi mọi nhánh bên dưới.
      WHEN b.lan_dau > m.hom_nay - 90 AND coalesce(b.so_lan_mua, 0) < 3 THEN 'du'
      -- Tồn 0 mà KHÔNG bán gì 90 ngày = mã đã ngừng kinh doanh, không phải
      -- mã cần đặt gấp. Xếp nhầm là tạo việc giả mỗi ngày cho người giữ kho.
      WHEN coalesce(t.ton, 0) = 0 AND coalesce(v.so_luong_90n, 0) = 0 THEN 'ngung'
      WHEN coalesce(t.ton, 0) = 0                          THEN 'het_hang'
      WHEN v.toc_do_ngay IS NULL OR v.toc_do_ngay = 0      THEN 'ton_chet'
      WHEN t.ton / v.toc_do_ngay < 14                      THEN 'sap_thieu'
      WHEN t.ton / v.toc_do_ngay > 180                     THEN 'ton_chet'
      ELSE 'du'
    END AS trang_thai,
    b.so_khach,
    b.lan_dau,
    b.lan_cuoi
FROM core.dim_product p
LEFT JOIN (
    SELECT product_code,
           sum(amount - tax_amount)      AS doanh_thu_thuan,
           sum(gross_profit)             AS lai_gop,
           sum(qty)                      AS so_luong_ban,
           count(DISTINCT customer_code) AS so_khach,
           count(DISTINCT sales_date)    AS so_lan_mua,
           min(sales_date)               AS lan_dau,
           max(sales_date)               AS lan_cuoi
    FROM core.fact_sales_line
    GROUP BY product_code
) b ON b.product_code = p.product_code
LEFT JOIN mart.toc_do_ban v ON v.product_code = p.product_code
LEFT JOIN (
    -- Gộp tồn qua mọi kho thành MỘT con số cho hồ sơ 360°. sum() trên một tập
    -- rỗng (mã không có dòng nào trong ton_hien_tai) sẽ không sinh dòng nào ở
    -- đây — LEFT JOIN từ dim_product biến nó thành NULL, đúng ý muốn.
    SELECT product_code, sum(so_luong) AS ton
    FROM mart.ton_hien_tai
    GROUP BY product_code
) t ON t.product_code = p.product_code
CROSS JOIN mart.moc_thoi_gian m;

COMMENT ON VIEW mart.san_pham_360 IS
  'Một dòng mỗi mã hàng trong core.dim_product — kể cả mã chưa từng bán và mã
   không có dòng tồn kho. ton là NULL khi mã không nằm trong 在庫一覧 gần nhất
   (90/232 mã) — không coalesce về 0.';


-- Doanh thu/lãi gộp/số lượng theo tháng của một mã hàng — vẽ đường lịch sử
-- trên trang Sản phẩm. Song song mart.khach_theo_thang (015), nhóm theo
-- product_code thay vì customer_code.
--
-- Đi qua mart.dong_ban (không phải core.fact_sales_line thẳng) để doanh thu
-- thuần dùng chung một định nghĩa với cả dự án — y hệt lý do ở 021.
CREATE VIEW mart.san_pham_theo_thang AS
SELECT product_code,
       thang,
       sum(qty)              AS so_luong,
       sum(doanh_thu_thuan)  AS doanh_thu_thuan,
       sum(gross_profit)     AS lai_gop
FROM mart.dong_ban
GROUP BY product_code, thang;


GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
