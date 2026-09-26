-- 048 — Phí & điều chỉnh KHÔNG phải sản phẩm (chủ DN chốt 2026-09-26, phương án A).
--
-- Đo thật 2026-09-26: 10 mã "(chưa phân loại)" của core.dim_product = 9 mã OBC
-- đánh dấu 無形 (kind_code = '1') + 1 mã ※使用禁止※ chưa bán lần nào. Chín mã đó là
-- 代引手数料 (300 / 330 / 調整), 配送料 (500 / 638 / その他), 値引き, 値引きクーポン
-- (8% / 10%) — phí thu hộ, phí gửi, giảm giá; không phải hàng. Cộng thêm các dòng
-- KHÔNG mã hàng (端数 làm tròn, 047) — cũng là điều chỉnh, không phải hàng.
--
-- Định nghĩa viết ĐÚNG MỘT LẦN: mart.la_phi_dieu_chinh(product_code, kind_code).
--
-- Phương án A: tiền của chúng VẪN nằm trong mọi tổng doanh thu / lãi gộp
-- (mart.dong_ban, ban_theo_thang, khach_360, tong_khoang …) — tổng web vẫn khớp sổ
-- OBC. Chỉ tách khỏi phần "sản phẩm":
--   * ngành: nhãn riêng 'Phí & điều chỉnh' thay vì rơi vào '(chưa phân loại)'
--     (mart.ten_nganh 3 tham số; Σ ngành vẫn = tổng — giao diện đưa nhóm này ra
--     khối riêng, kome.bao_cao.NGANH_PHI là bản chép bắt buộc, có test so khớp);
--   * mart.san_pham_360 (danh mục /san-pham): bỏ các mã đó;
--   * mart.khach_mat_hang (mặt hàng / nhịp / "đã ngừng mua" của khách): bỏ;
--   * mart.ban_theo_san_pham, mart.mat_hang_khoang, mart.khach_mat_hang_khoang:
--     GIỮ dòng (danh sách phải cộng đúng bằng tổng) nhưng mang cột `la_phi`.

CREATE FUNCTION mart.la_phi_dieu_chinh(product_code text, kind_code text) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT coalesce(product_code, '') = '' OR coalesce(trim(kind_code), '') = '1' $$;

-- Nhãn ngành có biết phí: gọi lại bản một tham số (039) — vẫn MỘT chỗ viết
-- '(chưa phân loại)'.
CREATE FUNCTION mart.ten_nganh(food_category_name text, product_code text, kind_code text)
RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT CASE WHEN mart.la_phi_dieu_chinh(product_code, kind_code) THEN 'Phí & điều chỉnh'
                  ELSE mart.ten_nganh(food_category_name) END $$;

CREATE OR REPLACE VIEW mart.ban_theo_nganh_thang AS
SELECT b.thang,
       min(b.company_fy) AS company_fy,
       mart.ten_nganh(p.food_category_name, b.product_code, p.kind_code) AS nganh,
       sum(b.doanh_thu_thuan) AS doanh_thu_thuan,
       sum(b.gross_profit)    AS lai_gop
FROM mart.dong_ban b
LEFT JOIN core.dim_product p ON p.product_code = b.product_code
GROUP BY b.thang, mart.ten_nganh(p.food_category_name, b.product_code, p.kind_code);

CREATE OR REPLACE FUNCTION mart.nganh_khoang(tu date, den date)
RETURNS TABLE (nganh text, dt numeric, lg numeric)
LANGUAGE sql STABLE
AS $$
    SELECT mart.ten_nganh(p.food_category_name, b.product_code, p.kind_code),
           sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric
    FROM mart.dong_ban_khoang(tu, den) b
    LEFT JOIN core.dim_product p ON p.product_code = b.product_code
    GROUP BY 1
$$;

-- Thêm cột CUỐI (CREATE OR REPLACE VIEW cho phép).
CREATE OR REPLACE VIEW mart.ban_theo_san_pham AS
SELECT b.company_fy,
       b.product_code,
       coalesce(nullif(s.product_name, ''), b.product_code) AS ten_hang,
       s.food_category_name,
       sum(b.doanh_thu_thuan) AS doanh_thu_thuan,
       sum(b.gross_profit)    AS lai_gop,
       sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0) AS ty_suat,
       sum(b.qty)             AS so_luong,
       count(DISTINCT b.customer_code) AS so_khach_mua,
       mart.la_phi_dieu_chinh(b.product_code, s.kind_code) AS la_phi
FROM mart.dong_ban b
LEFT JOIN core.dim_product s ON s.product_code = b.product_code
GROUP BY b.company_fy, b.product_code, s.product_name, s.food_category_name, s.kind_code;

-- Đổi kiểu trả về (thêm `la_phi`) nên phải DROP — không view nào dựa vào hai hàm này.
DROP FUNCTION mart.mat_hang_khoang(date, date);
CREATE FUNCTION mart.mat_hang_khoang(tu date, den date)
RETURNS TABLE (product_code text, ten_hang text, food_category_name text,
               dt numeric, lg numeric, ty_suat numeric, so_luong numeric, so_khach bigint,
               la_phi boolean)
LANGUAGE sql STABLE
AS $$
    SELECT b.product_code,
           CASE WHEN coalesce(b.product_code, '') = '' THEN '(điều chỉnh làm tròn — không mã hàng)'
                ELSE coalesce(nullif(s.product_name, ''), b.product_code) END,
           s.food_category_name,
           sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric,
           sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0),
           sum(b.qty)::numeric, count(DISTINCT b.customer_code),
           mart.la_phi_dieu_chinh(b.product_code, s.kind_code)
    FROM mart.dong_ban_khoang(tu, den) b
    LEFT JOIN core.dim_product s ON s.product_code = b.product_code
    GROUP BY b.product_code, s.product_name, s.food_category_name, s.kind_code
$$;

DROP FUNCTION mart.khach_mat_hang_khoang(date, date);
CREATE FUNCTION mart.khach_mat_hang_khoang(tu date, den date)
RETURNS TABLE (customer_code text, product_code text, ten_hang text, dt numeric, lg numeric,
               so_luong numeric, so_ngay_mua bigint, lan_cuoi date, la_phi boolean)
LANGUAGE sql STABLE
AS $$
    SELECT b.customer_code, b.product_code,
           CASE WHEN coalesce(b.product_code, '') = '' THEN '(điều chỉnh làm tròn — không mã hàng)'
                ELSE coalesce(nullif(s.product_name, ''), b.product_code) END,
           sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric, sum(b.qty)::numeric,
           count(DISTINCT b.sales_date), max(b.sales_date),
           mart.la_phi_dieu_chinh(b.product_code, s.kind_code)
    FROM mart.dong_ban_khoang(tu, den) b
    LEFT JOIN core.dim_product s ON s.product_code = b.product_code
    GROUP BY b.customer_code, b.product_code, s.product_name, s.kind_code
$$;

-- mart.khach_mat_hang — thân chép nguyên từ 047_mat_hang_khong_ma.sql; CHỈ đổi vị
-- từ lọc dòng không mã thành mart.la_phi_dieu_chinh (bao cả dòng không mã).
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
        -- 047: dòng KHÔNG có mã hàng (điều chỉnh làm tròn / 端数 của OBC, vài
        -- yên mỗi phiếu) không phải một mặt hàng khách "mua theo nhịp".
        -- 048: phí thu hộ / phí gửi / giảm giá (無形) cũng vậy — cùng một hàm.
        WHERE NOT mart.la_phi_dieu_chinh(f.product_code, s.kind_code)
        GROUP BY f.customer_code, f.product_code, s.product_name,
                 n.so_khoang, n.nhip_ngay, m.hom_nay
    ) x
) y
LEFT JOIN mart.dau_hieu_khach dh ON dh.customer_code = y.customer_code;

-- mart.san_pham_360 — thân chép nguyên từ 040_moc_lui.sql; CHỈ thêm WHERE cuối.
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
LEFT JOIN ton ON ton.product_code = p.product_code
-- 048: phí & điều chỉnh (無形 / không mã) không phải một mặt hàng của danh mục.
WHERE NOT mart.la_phi_dieu_chinh(p.product_code, p.kind_code);
