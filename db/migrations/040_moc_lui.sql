-- 040 — Mốc thời gian dời được: "mọi thứ quay về tháng đó"
-- (đặc tả docs/superpowers/specs/2026-09-24-moc-thoi-gian-doi-duoc-design.md).
--
-- Mọi chỉ số "tính đến hôm nay" neo vào mart.moc_thoi_gian. 040 cho mốc đó LÙI được
-- TRONG MỘT GIAO DỊCH: `SELECT set_config('kome.moc', 'YYYY-MM-DD', true)` (true =
-- chỉ giao dịch hiện tại — KHÔNG dùng SET cấp phiên: Supavisor giữ nó sang kết nối
-- sau). Không đặt mốc ⇒ mọi view y hệt trước 040.
--
-- Cách làm: các view từng đọc thẳng core.fact_sales_line nay đọc mart.ban_den_moc
-- (bảng bán chỉ tới mốc) — CÙNG cột, KHÔNG đổi công thức nào. Mọi view dựng trên
-- chúng (nhịp mua, trạng thái, hạng, nhóm việc, tháng này chưa mua, cần liên hệ, …)
-- tự quay về. Đẳng thức có test canh: mốc D ≡ như thể kho chỉ có dữ liệu tới D
-- (tests/test_moc_lui.py).

-- Ngày mốc đang lùi về, hoặc NULL (= hiện tại). Mốc ≥ ngày bán mới nhất ⇒ NULL: xem
-- tháng hiện tại y như không dời (ảnh chụp tồn sau ngày bán cuối vẫn được dùng).
CREATE FUNCTION mart.moc_lui() RETURNS date
LANGUAGE sql STABLE
AS $$
    SELECT CASE WHEN x.g < (SELECT max(sales_date) FROM core.fact_sales_line) THEN x.g END
    FROM (SELECT nullif(current_setting('kome.moc', true), '')::date AS g) x
$$;

-- Bảng bán tới mốc — MỘT chỗ viết điều kiện "≤ mốc". `(SELECT …)` bọc lời gọi hàm để
-- Postgres tính nó MỘT lần (InitPlan), không lại mỗi dòng.
CREATE VIEW mart.ban_den_moc AS
SELECT f.*
FROM core.fact_sales_line f
WHERE f.sales_date <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date));

-- mart.moc_thoi_gian — ngày bán mới nhất KHÔNG SAU mốc.
CREATE OR REPLACE VIEW mart.moc_thoi_gian AS
SELECT max(sales_date) AS hom_nay FROM mart.ban_den_moc;

-- mart.dong_ban — thân như 014; đổi nguồn. Cột bảng bán liệt kê TƯỜNG MINH: `f.*`
-- của 014 đã đóng băng danh sách cột lúc đó, còn bảng bán có thêm `source` từ 017 —
-- `f.*` bây giờ sẽ chen `source` vào giữa và CREATE OR REPLACE bị từ chối.
CREATE OR REPLACE VIEW mart.dong_ban AS
SELECT f.slip_no, f.line_seq, f.sales_date, f.billing_date, f.slip_type, f.customer_code,
       f.billing_customer_code, f.salesperson_code, f.department_code, f.shipto_code,
       f.product_code, f.pack_code, f.case_qty, f.qty, f.unit_price, f.unit_cost, f.amount,
       f.tax_amount, f.cost, f.gross_profit, f.gross_margin, f.tax_rate, f.paid_amount,
       f.payment_slip_no, f.closing_day_code, f.batch_id,
       d.company_fy,
       d.company_fy_no,
       d.company_fy_label,
       d.company_fy_month,
       to_char(f.sales_date, 'YYYY-MM')        AS thang,
       f.amount - f.tax_amount                  AS doanh_thu_thuan
FROM mart.ban_den_moc f
JOIN core.dim_date d ON d.date_key = f.sales_date;

-- mart.lan_mua — thân chép nguyên từ 015; CHỈ đổi nguồn.
CREATE OR REPLACE VIEW mart.lan_mua AS
SELECT customer_code, sales_date, slip_no,
       sum(amount - tax_amount) AS doanh_thu_thuan,
       sum(gross_profit)        AS lai_gop,
       count(*)                 AS so_dong
FROM mart.ban_den_moc
GROUP BY customer_code, sales_date, slip_no;

-- mart.khach_chua_mua — thân chép nguyên từ 015_mart_khach_hang.sql; CHỈ đổi core.fact_sales_line -> mart.ban_den_moc (1 chỗ).
CREATE OR REPLACE VIEW mart.khach_chua_mua AS
SELECT d.customer_code,
       coalesce(nullif(d.customer_name, ''), '(chưa có tên)') AS ten,
       d.prefecture, d.city, d.phone, d.salesperson_code, d.category_code
FROM core.dim_customer d
WHERE d.is_current
  AND NOT EXISTS (SELECT 1 FROM mart.ban_den_moc f
                  WHERE f.customer_code = d.customer_code);

-- mart.khoang_cach_mat_hang — thân chép nguyên từ 020_mart_khach_360.sql; CHỈ đổi core.fact_sales_line -> mart.ban_den_moc (1 chỗ).
CREATE OR REPLACE VIEW mart.khoang_cach_mat_hang AS
SELECT customer_code, product_code, sales_date,
       sales_date - lag(sales_date) OVER (PARTITION BY customer_code, product_code
                                          ORDER BY sales_date) AS so_ngay_cach
FROM (SELECT DISTINCT customer_code, product_code, sales_date
      FROM mart.ban_den_moc) x;

-- mart.khach_mat_hang — thân chép nguyên từ 024_nhan_trang_thai_cap_khach_ma.sql; CHỈ đổi core.fact_sales_line -> mart.ban_den_moc (1 chỗ).
CREATE OR REPLACE VIEW mart.khach_mat_hang AS
SELECT y.customer_code, y.product_code, y.ten_hang, y.doanh_thu_thuan,
       y.lai_gop, y.so_luong, y.so_lan, y.lan_dau, y.lan_cuoi, y.nhip_ngay,
       y.du_kien_lan_toi, y.tre_ngay,
       CASE
         -- Khách bị OBC đánh dấu ※廃業※/※取引停止※ (016). Xét TRƯỚC hai nhánh
         -- kia: đã đóng cửa thì im lặng là đúng, không phải tín hiệu.
         WHEN coalesce(dh.da_ngung, false) THEN 'khong_goi'
         -- im lặng >= 2 x nhịp riêng của CHÍNH CẶP NÀY (tre_ngay = số ngày quá
         -- ngày dự kiến mua lại = lan_cuoi + nhip_ngay, nên tre >= nhip tương
         -- đương im lặng >= 2 nhịp — đúng ngưỡng 'canh_bao' mà mart.khach_360
         -- dùng cho quan hệ khách hàng).
         WHEN y.tre_ngay >= y.nhip_ngay THEN 'ngung'
         -- Còn lại. `tre_ngay` NULL (chưa đủ 3 lần mua, hoặc chưa tới ngày dự
         -- kiến) cho ra NULL ở nhánh trên nên rơi xuống đây — CỐ Ý: "chưa đủ
         -- dữ liệu" không phải "đã ngừng".
         ELSE 'mua'
       END                                                AS trang_thai_cap
FROM (
    SELECT x.customer_code, x.product_code, x.ten_hang, x.doanh_thu_thuan,
           x.lai_gop, x.so_luong, x.so_lan, x.lan_dau, x.lan_cuoi,
           x.nhip_ngay, x.du_kien_lan_toi,
           -- Chỉ tính khi ĐÃ quá hạn. Số âm ở cột "trễ" sẽ bị đọc thành
           -- "sớm", mà đó không phải điều cột này nói. du_kien_lan_toi NULL
           -- thì so sánh ra NULL luôn, không cần lặp lại điều kiện
           -- so_khoang >= 2 ở đây.
           CASE WHEN x.hom_nay > x.du_kien_lan_toi
                THEN x.hom_nay - x.du_kien_lan_toi END      AS tre_ngay
    FROM (
        SELECT f.customer_code, f.product_code,
               coalesce(nullif(s.product_name, ''), f.product_code) AS ten_hang,
               sum(f.amount - f.tax_amount) AS doanh_thu_thuan,
               sum(f.gross_profit)          AS lai_gop,
               sum(f.qty)                   AS so_luong,
               count(DISTINCT f.sales_date) AS so_lan,
               min(f.sales_date)            AS lan_dau,
               max(f.sales_date)            AS lan_cuoi,
               -- Dưới 2 khoảng cách = dưới 3 lần mua: không đủ để nói về
               -- "nhịp". NULL chứ không phải một con số, để trang hiện `—`.
               CASE WHEN n.so_khoang >= 2 THEN n.nhip_ngay END AS nhip_ngay,
               CASE WHEN n.so_khoang >= 2
                    THEN (max(f.sales_date) + n.nhip_ngay * interval '1 day')::date
               END AS du_kien_lan_toi,
               m.hom_nay AS hom_nay
        FROM mart.ban_den_moc f
        LEFT JOIN core.dim_product s ON s.product_code = f.product_code
        LEFT JOIN mart.nhip_mat_hang n
               ON n.customer_code = f.customer_code
              AND n.product_code = f.product_code
        CROSS JOIN mart.moc_thoi_gian m
        GROUP BY f.customer_code, f.product_code, s.product_name,
                 n.so_khoang, n.nhip_ngay, m.hom_nay
    ) x
) y
LEFT JOIN mart.dau_hieu_khach dh ON dh.customer_code = y.customer_code;

-- mart.toc_do_ban — thân chép nguyên từ 023_mart_san_pham.sql; CHỈ đổi core.fact_sales_line -> mart.ban_den_moc (2 chỗ).
CREATE OR REPLACE VIEW mart.toc_do_ban AS
WITH tuoi AS (
    -- Ngày bán ĐẦU TIÊN trong TOÀN BỘ lịch sử — không lọc theo 90 ngày, khác
    -- hẳn so_luong_90n bên dưới. Đây là nguồn DUY NHẤT cho "mã này bao nhiêu
    -- tuổi", dùng lại ở CTE `moi` của mart.san_pham_360.
    SELECT product_code, min(sales_date) AS lan_dau
    FROM mart.ban_den_moc
    GROUP BY product_code
)
SELECT f.product_code,
       sum(f.qty)                        AS so_luong_90n,
       sum(f.amount - f.tax_amount)      AS doanh_thu_90n,
       sum(f.qty) / 90.0                 AS toc_do_ngay,
       sum(f.qty)
         / least(90, m.hom_nay - tuoi.lan_dau + 1) AS toc_do_ngay_theo_tuoi
FROM mart.ban_den_moc f
JOIN tuoi ON tuoi.product_code = f.product_code
CROSS JOIN mart.moc_thoi_gian m
WHERE f.sales_date > m.hom_nay - 90
GROUP BY f.product_code, tuoi.lan_dau, m.hom_nay;

-- mart.ton_hien_tai — thân chép nguyên từ 023; đổi điều kiện ngày chụp.
CREATE OR REPLACE VIEW mart.ton_hien_tai AS
SELECT i.product_code, i.warehouse_code, w.warehouse_name AS ten_kho,
       i.stock_qty AS so_luong, i.stock_value AS gia_tri, i.best_before,
       CASE WHEN i.best_before ~ '^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$' THEN 'ngay'
            -- btrim với danh sách ký tự tường minh (dấu cách thường VÀ dấu
            -- cách toàn giác／全角, U+3000) — btrim() mặc định chỉ cắt dấu
            -- cách ASCII, một ô OBC có đệm khoảng trắng toàn giác ở đuôi sẽ
            -- KHÔNG khớp so sánh chuỗi trần và rơi nhầm xuống 'khong_ro'.
            WHEN btrim(i.best_before, ' 　') = '賞味期限なし'            THEN 'khong_han'
            WHEN coalesce(i.best_before, '') = ''                     THEN 'trong'
            ELSE 'khong_ro' END AS loai_han,
       CASE WHEN i.best_before ~ '^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$'
            THEN to_date(i.best_before, 'YYYY"年"MM"月"DD"日"') - m.hom_nay
       END AS han_con_lai
FROM core.fact_inventory_daily i
JOIN core.dim_warehouse w ON w.warehouse_code = i.warehouse_code
CROSS JOIN mart.moc_thoi_gian m
-- Ảnh chụp mới nhất KHÔNG SAU mốc đang xem (040). Xem một tháng cũ mà chưa có ảnh
-- chụp nào tới lúc đó ⇒ không dòng nào: màn nói "chưa có ảnh chụp tồn", KHÔNG lấy
-- ảnh chụp sau mốc (quyết định của chủ DN 2026-09-24).
WHERE i.snapshot_date = (SELECT max(snapshot_date) FROM core.fact_inventory_daily
                          WHERE snapshot_date <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date)));

-- mart.san_pham_360 — thân chép nguyên từ 023_mart_san_pham.sql; CHỈ đổi core.fact_sales_line -> mart.ban_den_moc (1 chỗ).
CREATE OR REPLACE VIEW mart.san_pham_360 AS
WITH sl AS (
    -- Chỉ những gì mart.ty_suat_mat_hang KHÔNG có: số lượng, số khách, số lần
    -- bán, lần đầu/lần cuối. Đừng thêm doanh_thu_thuan/lai_gop/ty_suat vào
    -- đây — ba cột đó có nhà riêng ở 021. TOÀN BỘ LỊCH SỬ, không lọc 90 ngày
    -- — khác mart.toc_do_ban — nên "mã đã ngừng bán 200 ngày" vẫn có dòng ở
    -- đây dù không còn dòng nào trong mart.toc_do_ban.
    SELECT product_code,
           sum(qty)                      AS so_luong_ban,
           count(DISTINCT customer_code) AS so_khach,
           count(DISTINCT sales_date)    AS so_lan_mua,
           min(sales_date)               AS lan_dau,
           max(sales_date)               AS lan_cuoi
    FROM mart.ban_den_moc
    GROUP BY product_code
),
moi AS (
    -- "Mới": lần bán đầu trong 90 ngày VÀ chưa đủ 3 lần bán — thiếu vế sau
    -- thì một mã lâu năm bán 3 lần cách đây 80-82 ngày (đủ dữ liệu để kết
    -- luận là tồn chết) cũng lọt qua vì bản thân toàn bộ lịch sử bán của nó
    -- vẫn nằm trong cửa sổ 90 ngày.
    --
    -- Tính TỪ `sl` (toàn bộ lịch sử), KHÔNG từ mart.toc_do_ban: một mã không
    -- bán gì trong 90 ngày không có dòng nào ở toc_do_ban, nên nếu "moi" phải
    -- JOIN qua đó thì nó sẽ là NULL cho đúng những mã cần bị coi là "không
    -- mới" nhất — và NOT NULL cũng là NULL, làm nhánh tồn chết phía dưới im
    -- lặng bỏ qua đúng mã đó (đã bắt được lỗi này thật ở vòng sửa trước, xem
    -- task-1-report.md).
    SELECT sl.product_code,
           (sl.lan_dau > m.hom_nay - 90 AND coalesce(sl.so_lan_mua, 0) < 3) AS la_moi
    FROM sl
    CROSS JOIN mart.moc_thoi_gian m
),
ton AS (
    -- Gộp tồn qua mọi kho thành MỘT con số cho hồ sơ 360°. sum() trên một tập
    -- rỗng (mã không có dòng nào trong ton_hien_tai) sẽ không sinh dòng nào ở
    -- đây — LEFT JOIN từ dim_product biến nó thành NULL, đúng ý muốn.
    SELECT product_code, sum(so_luong) AS ton
    FROM mart.ton_hien_tai
    GROUP BY product_code
)
SELECT
    p.product_code,
    coalesce(nullif(p.product_name, ''), p.product_code) AS ten_hang,
    p.kind_name                                          AS nhom,
    ts.doanh_thu_thuan,
    ts.lai_gop,
    ts.ty_suat,
    sl.so_luong_ban,
    -- "Không biết" khác "bằng không": 90/232 mã không có dòng tồn nào trong
    -- 在庫一覧. ton.ton đến từ LEFT JOIN nên tự nhiên là NULL khi không có
    -- dòng — TUYỆT ĐỐI không coalesce cột này. 0 nói với người đọc "kho đã
    -- hết", còn NULL nói "chưa từng nhập kho hoặc không nằm trong bản xuất
    -- tồn kho" — hai điều khác nhau, và cái đầu xui người ta đi đặt hàng oan.
    ton.ton,
    -- Xuất CẢ HAI cột tốc độ: v.toc_do_ngay (trung bình cố định — nếu chỉ
    -- hiện nó thì màn hình sẽ nói "tốc độ 0,33/ngày, còn đủ 140 ngày, trạng
    -- thái: đủ hàng" trên CÙNG một dòng — 200/0,33 = 600, không phải 140.
    -- trang_thai/du_ban_ngay dùng toc_do_ngay_theo_tuoi, nên PHẢI hiện đúng
    -- cột đó bên cạnh, không phải v.toc_do_ngay, kẻo người giữ kho không có
    -- cách nào đối chiếu con số trang hiện với nhãn trang gắn.
    v.toc_do_ngay,
    v.toc_do_ngay_theo_tuoi,
    -- Số ngày còn đủ bán = tồn chia tốc độ THEO TUỔI MÃ (không phải
    -- v.toc_do_ngay thẳng — xem chú thích ở mart.toc_do_ban). <= 0 hoặc NULL
    -- (mã không bán trong 90 ngày, hoặc chỉ toàn 赤伝 khiến tổng số lượng ÂM)
    -- thì không chia được — để NULL, không phải 0, âm, hay vô cực.
    CASE WHEN v.toc_do_ngay_theo_tuoi > 0
         THEN ton.ton / v.toc_do_ngay_theo_tuoi END AS du_ban_ngay,
    CASE
      -- "Không biết tồn" PHẢI đứng trước và tách khỏi "tồn bằng 0": một mã
      -- không nằm trong bản xuất 在庫一覧 (90/232 mã) mà vẫn bán đều không
      -- được hiện "hết hàng, đặt gấp" — đó là lời khẳng định chắc chắn về
      -- một con số ta không có. Ghép hai điều này bằng coalesce(ton,0) làm
      -- đúng một dòng vừa hiện ton='—' (không biết) vừa hiện trang_thai=
      -- 'het_hang' (biết chắc bằng 0) — tự mâu thuẫn ngay trên cùng một hàng.
      WHEN ton.ton IS NULL                                  THEN 'chua_ro_ton'
      -- Tồn 0 mà KHÔNG bán gì 90 ngày = mã đã ngừng kinh doanh, không phải
      -- mã cần đặt gấp. Xếp nhầm là tạo việc giả mỗi ngày cho người giữ kho.
      WHEN ton.ton = 0 AND coalesce(v.so_luong_90n, 0) = 0    THEN 'ngung'
      -- Tồn 0 mà CÓ bán gần đây LUÔN là hết hàng cần đặt gấp — kể cả khi mã
      -- còn mới/còn ít lần bán. Ngoại lệ "mã mới" (dưới) chỉ được phép chắn
      -- nhãn 'ton_chet', không được đè lên đây: một mã ra mắt 20 ngày trước,
      -- bán 2 lần, tồn về 0 vẫn đang cần nhập hàng GẤP, không phải "đủ hàng".
      WHEN ton.ton = 0                                       THEN 'het_hang'
      -- Mã mới ra mắt trong 90 ngày, CHƯA đủ 3 lần bán để kết luận, thì
      -- KHÔNG được gắn nhãn tồn chết: bán chậm ở tuần đầu là chuyện bình
      -- thường, gắn nhãn tồn chết là xúi người ta xả một mã vừa mua về. Ràng
      -- buộc này chỉ áp cho HAI NHÁNH tồn chết bên dưới (AND NOT ... la_moi)
      -- — không đặt thành một nhánh 'du' riêng ở đầu CASE, vì làm vậy sẽ đè
      -- cả 'het_hang' lẫn 'ngung' ở trên, hai nhãn chẳng liên quan gì tới lý
      -- do "đừng vội gọi tồn chết".
      --
      -- coalesce(moi.la_moi, false): một mã không bán gì trong 90 ngày
      -- KHÔNG có dòng ở mart.toc_do_ban, nhưng `moi` tính từ `sl` (toàn bộ
      -- lịch sử) nên VẪN có dòng — la_moi ở đó là false thật (mã lâu năm),
      -- không phải NULL. coalesce ở đây chỉ còn là lưới an toàn cho mã CHƯA
      -- TỪNG bán (moi cũng không có dòng) — hai nhánh 'chua_ro_ton'/'ngung'/
      -- 'het_hang' ở trên đã bắt các mã đó trước khi tới đây trong mọi test
      -- đã viết, nhưng coalesce vẫn giữ lại để không có đường nào NULL lọt
      -- xuống đây mà bị đọc nhầm thành "không loại trừ được, cứ cho đủ hàng".
      WHEN (v.toc_do_ngay_theo_tuoi IS NULL OR v.toc_do_ngay_theo_tuoi <= 0)
           AND NOT coalesce(moi.la_moi, false)               THEN 'ton_chet'
      WHEN v.toc_do_ngay_theo_tuoi > 0
           AND ton.ton / v.toc_do_ngay_theo_tuoi < 14         THEN 'sap_thieu'
      WHEN v.toc_do_ngay_theo_tuoi > 0
           AND ton.ton / v.toc_do_ngay_theo_tuoi > 180
           AND NOT coalesce(moi.la_moi, false)               THEN 'ton_chet'
      ELSE 'du'
    END AS trang_thai,
    sl.so_khach,
    sl.lan_dau,
    sl.lan_cuoi
FROM core.dim_product p
LEFT JOIN sl ON sl.product_code = p.product_code
LEFT JOIN moi ON moi.product_code = p.product_code
LEFT JOIN mart.ty_suat_mat_hang ts ON ts.product_code = p.product_code
LEFT JOIN mart.toc_do_ban v ON v.product_code = p.product_code
LEFT JOIN ton ON ton.product_code = p.product_code;

-- mart.so_cong_no_moi_nhat — thân chép nguyên từ 038; thêm điều kiện kỳ ≤ mốc.
CREATE OR REPLACE VIEW mart.so_cong_no_moi_nhat AS
SELECT l.*
FROM core.fact_ar_ledger l
WHERE l.batch_id = (
    SELECT a.batch_id
    FROM core.fact_ar_ledger a
    JOIN meta.ingest_batch b ON b.batch_id = a.batch_id AND b.undone_at IS NULL
    -- Sổ có kỳ kết thúc KHÔNG SAU mốc đang xem (040).
    WHERE a.period_to <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date))
    ORDER BY a.period_to DESC, a.batch_id DESC
    LIMIT 1);

-- Quyền: ALTER DEFAULT PRIVILEGES của 009 không có kome_ingest (bất biến GRANT, 026).
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
