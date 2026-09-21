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
--
-- `ELSE 'khong_ro'` (không phải `ELSE 'khong_han'`) là chủ ý: một chuỗi không
-- khớp regex ngày và không đúng y hệt '賞味期限なし' — '2028/06/09' nếu OBC đổi
-- mẫu xuất (đã từng đổi, xem bẫy số 4 của CLAUDE.md), số toàn giác, một ô gõ
-- tay sai — là "không đọc được", KHÔNG phải "hàng này không có hạn sử dụng".
-- Bắt-tất về 'khong_han' biến lô đó thành lời khẳng định sai và cho nó biến
-- mất KHỎI MỌI cảnh báo hạn một cách im lặng. Regex nới thành 1-2 chữ số cho
-- tháng/ngày vì to_date() không đòi số 0 đệm đầu (đã kiểm tra thật trên
-- Postgres của Supabase: to_date('2028年6月9日', 'YYYY"年"MM"月"DD"日"') và bản
-- có số 0 đệm cho cùng một kết quả) — một biến thể xuất chỉ khác cách đệm số
-- không đáng bị coi là "không đọc được".
CREATE VIEW mart.ton_hien_tai AS
SELECT i.product_code, i.warehouse_code, w.warehouse_name AS ten_kho,
       i.stock_qty AS so_luong, i.stock_value AS gia_tri, i.best_before,
       CASE WHEN i.best_before ~ '^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$' THEN 'ngay'
            WHEN i.best_before = '賞味期限なし'                        THEN 'khong_han'
            WHEN coalesce(i.best_before, '') = ''                     THEN 'trong'
            ELSE 'khong_ro' END AS loai_han,
       CASE WHEN i.best_before ~ '^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$'
            THEN to_date(i.best_before, 'YYYY"年"MM"月"DD"日"') - m.hom_nay
       END AS han_con_lai
FROM core.fact_inventory_daily i
JOIN core.dim_warehouse w ON w.warehouse_code = i.warehouse_code
CROSS JOIN mart.moc_thoi_gian m
WHERE i.snapshot_date = (SELECT max(snapshot_date) FROM core.fact_inventory_daily);

COMMENT ON VIEW mart.ton_hien_tai IS
  'Tên kho đọc từ core.dim_warehouse, không viết cứng — thêm kho mới trong OBC
   thì tự xuất hiện, không cần sửa view này. loai_han=''khong_ro'' nghĩa là
   "không đọc được", không phải "không có hạn" — hai điều khác nhau, xem
   chú thích phía trên CASE.';


-- Hồ sơ 360° của một mã hàng: doanh thu/lãi gộp toàn bộ lịch sử, tồn hiện tại,
-- tốc độ bán, và trạng thái cần chú ý.
--
-- doanh_thu_thuan/lai_gop/ty_suat KHÔNG tính lại ở đây — lấy thẳng từ
-- mart.ty_suat_mat_hang (021), một định nghĩa DUY NHẤT dùng chung cho cả màn
-- Khách 360 và màn Sản phẩm. Hôm nay tự tính lại cho ra cùng con số (SQL y
-- hệt 021), nhưng đó đúng là loại trùng lặp mà 021/022 được viết ra để dẹp:
-- sửa công thức ở 021 mà quên chỗ này thì hai màn nói hai số khác nhau cùng
-- một tên cột — người bán hàng không có cách nào biết mình đang đọc cái nào.
CREATE VIEW mart.san_pham_360 AS
WITH sl AS (
    -- Chỉ những gì mart.ty_suat_mat_hang KHÔNG có: số lượng, số khách, số lần
    -- bán, lần đầu/lần cuối. Đừng thêm doanh_thu_thuan/lai_gop/ty_suat vào
    -- đây — ba cột đó có nhà riêng ở 021.
    SELECT product_code,
           sum(qty)                      AS so_luong_ban,
           count(DISTINCT customer_code) AS so_khach,
           count(DISTINCT sales_date)    AS so_lan_mua,
           min(sales_date)               AS lan_dau,
           max(sales_date)               AS lan_cuoi
    FROM core.fact_sales_line
    GROUP BY product_code
),
ton AS (
    -- Gộp tồn qua mọi kho thành MỘT con số cho hồ sơ 360°. sum() trên một tập
    -- rỗng (mã không có dòng nào trong ton_hien_tai) sẽ không sinh dòng nào ở
    -- đây — LEFT JOIN từ dim_product biến nó thành NULL, đúng ý muốn.
    SELECT product_code, sum(so_luong) AS ton
    FROM mart.ton_hien_tai
    GROUP BY product_code
),
hieu_qua AS (
    -- Tốc độ bán "công bằng cho hàng mới": mart.toc_do_ban chia so_luong_90n
    -- cho HẰNG 90 — đúng và có test khoá riêng (test_toc_do_ban_la_trung_binh_90_ngay),
    -- KHÔNG đổi view đó. Nhưng một mã mới ra mắt 20 ngày, bán 30 đơn vị, chia
    -- cho 90 ra tốc độ THẤP HƠN THẬT gần 4,5 lần — rồi "còn đủ bán bao nhiêu
    -- ngày" (=tồn/tốc độ) bị THỔI PHỒNG đúng bấy nhiêu lần, đẩy một mã đang
    -- bán tốt vào nhãn 'ton_chet'. Ở ĐÂY — chỉ dùng cho du_ban_ngay và
    -- trang_thai của trang Sản phẩm — chia cho SỐ NGÀY MÃ THỰC SỰ CÓ MẶT
    -- trong 90 ngày gần nhất (chặn trên ở 90 cho mã cũ, để không đổi gì so
    -- với công thức cũ khi mã đã bán quá 90 ngày).
    SELECT v.product_code,
           v.so_luong_90n
             / nullif(least(90, m.hom_nay - sl.lan_dau + 1), 0) AS toc_do_ngay,
           -- "Mới": lần bán đầu trong 90 ngày VÀ chưa đủ 3 lần bán — thiếu vế
           -- sau thì một mã lâu năm bán 3 lần cách đây 80-82 ngày (đủ dữ liệu
           -- để kết luận là tồn chết) cũng lọt qua vì bản thân toàn bộ lịch sử
           -- bán của nó vẫn nằm trong cửa sổ 90 ngày.
           (sl.lan_dau > m.hom_nay - 90 AND coalesce(sl.so_lan_mua, 0) < 3) AS moi
    FROM mart.toc_do_ban v
    JOIN sl ON sl.product_code = v.product_code
    CROSS JOIN mart.moc_thoi_gian m
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
    v.toc_do_ngay,
    -- Số ngày còn đủ bán = tồn chia tốc độ (bản "công bằng cho hàng mới" ở
    -- CTE hieu_qua, không phải v.toc_do_ngay thẳng). <= 0 hoặc NULL (mã không
    -- bán trong 90 ngày, hoặc chỉ toàn 赤伝 khiến tổng số lượng ÂM) thì không
    -- chia được — để NULL, không phải 0, âm, hay vô cực.
    CASE WHEN hq.toc_do_ngay > 0 THEN ton.ton / hq.toc_do_ngay END AS du_ban_ngay,
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
      -- buộc này chỉ áp cho HAI NHÁNH tồn chết bên dưới (AND NOT hq.moi) —
      -- không đặt thành một nhánh 'du' riêng ở đầu CASE, vì làm vậy sẽ đè cả
      -- 'het_hang' lẫn 'ngung' ở trên, hai nhãn chẳng liên quan gì tới lý do
      -- "đừng vội gọi tồn chết".
      WHEN (hq.toc_do_ngay IS NULL OR hq.toc_do_ngay <= 0) AND NOT hq.moi
                                                              THEN 'ton_chet'
      WHEN hq.toc_do_ngay > 0 AND ton.ton / hq.toc_do_ngay < 14
                                                              THEN 'sap_thieu'
      WHEN hq.toc_do_ngay > 0 AND ton.ton / hq.toc_do_ngay > 180 AND NOT hq.moi
                                                              THEN 'ton_chet'
      ELSE 'du'
    END AS trang_thai,
    sl.so_khach,
    sl.lan_dau,
    sl.lan_cuoi
FROM core.dim_product p
LEFT JOIN sl ON sl.product_code = p.product_code
LEFT JOIN mart.ty_suat_mat_hang ts ON ts.product_code = p.product_code
LEFT JOIN mart.toc_do_ban v ON v.product_code = p.product_code
LEFT JOIN hieu_qua hq ON hq.product_code = p.product_code
LEFT JOIN ton ON ton.product_code = p.product_code;

COMMENT ON VIEW mart.san_pham_360 IS
  'Một dòng mỗi mã hàng trong core.dim_product — kể cả mã chưa từng bán và mã
   không có dòng tồn kho. ton là NULL khi mã không nằm trong 在庫一覧 gần nhất
   (90/232 mã) — không coalesce về 0. trang_thai có 6 nhãn: du, sap_thieu,
   het_hang, ton_chet, ngung, chua_ro_ton — hai nhãn cuối là bổ sung so với
   bản đầu, trang hiển thị phải xử lý cả hai.';


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
