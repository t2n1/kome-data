-- 049 — Hàng tặng POSM KHÔNG phải sản phẩm (chủ DN chốt 2026-09-26: nhóm riêng,
-- không gộp vào "Phí & điều chỉnh").
--
-- Đo thật 2026-09-26: ngành `雑貨_VNM` của core.dim_product = 23 mã MKT05–MKT27
-- (poster, túi Eco, ly rượu, wobbler Vinamilk…) — hàng POSM đi TẶNG khách: doanh
-- thu ¥0 trên mọi dòng bán, vài poster có giá vốn (lãi gộp cả nhóm −¥176.788),
-- không mã nào có dòng tồn. Phí thu tiền của khách; POSM là chi phí marketing —
-- hai nhóm, hai nhãn.
--
-- Định nghĩa viết ĐÚNG MỘT LẦN: mart.la_hang_tang(food_category_name) — theo NGÀNH
-- của OBC (chủ DN nói theo danh mục), không theo tiền tố mã `MKT`.
-- mart.khong_phai_hang(...) = phí & điều chỉnh HOẶC hàng tặng — vị từ lọc duy
-- nhất của phần "sản phẩm" (san_pham_360, khach_mat_hang, gợi ý hàng chưa mua).
--
-- Cùng phương án A của 048: tiền (¥0 doanh thu, giá vốn poster) VẪN trong mọi tổng.
-- Ngành: nhãn 'Hàng tặng (POSM)' (kome.bao_cao.NGANH_HANG_TANG là bản chép bắt
-- buộc). ban_theo_san_pham / mat_hang_khoang / khach_mat_hang_khoang GIỮ dòng, kèm
-- cột `la_hang_tang` (phí xét trước: một dòng không vừa phí vừa tặng).

CREATE FUNCTION mart.la_hang_tang(food_category_name text) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT coalesce(trim(food_category_name), '') = '雑貨_VNM' $$;

CREATE FUNCTION mart.khong_phai_hang(product_code text, kind_code text, food_category_name text)
RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT mart.la_phi_dieu_chinh(product_code, kind_code) OR mart.la_hang_tang(food_category_name) $$;

-- Cờ "hàng tặng" của MỘT dòng danh sách: phí xét TRƯỚC, cùng thứ tự mart.ten_nganh.
CREATE FUNCTION mart.la_dong_hang_tang(product_code text, kind_code text, food_category_name text)
RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT NOT mart.la_phi_dieu_chinh(product_code, kind_code) AND mart.la_hang_tang(food_category_name) $$;

-- Cùng chữ ký 048 (thân mới): phí xét TRƯỚC (một mã 無形 trong 雑貨_VNM vẫn là phí).
CREATE OR REPLACE FUNCTION mart.ten_nganh(food_category_name text, product_code text, kind_code text)
RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$ SELECT CASE WHEN mart.la_phi_dieu_chinh(product_code, kind_code) THEN 'Phí & điều chỉnh'
                  WHEN mart.la_hang_tang(food_category_name) THEN 'Hàng tặng (POSM)'
                  ELSE mart.ten_nganh(food_category_name) END $$;

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
       mart.la_phi_dieu_chinh(b.product_code, s.kind_code) AS la_phi,
       mart.la_dong_hang_tang(b.product_code, s.kind_code, s.food_category_name) AS la_hang_tang
FROM mart.dong_ban b
LEFT JOIN core.dim_product s ON s.product_code = b.product_code
GROUP BY b.company_fy, b.product_code, s.product_name, s.food_category_name, s.kind_code;

DROP FUNCTION mart.mat_hang_khoang(date, date);
CREATE FUNCTION mart.mat_hang_khoang(tu date, den date)
RETURNS TABLE (product_code text, ten_hang text, food_category_name text,
               dt numeric, lg numeric, ty_suat numeric, so_luong numeric, so_khach bigint,
               la_phi boolean, la_hang_tang boolean)
LANGUAGE sql STABLE
AS $$
    SELECT b.product_code,
           CASE WHEN coalesce(b.product_code, '') = '' THEN '(điều chỉnh làm tròn — không mã hàng)'
                ELSE coalesce(nullif(s.product_name, ''), b.product_code) END,
           s.food_category_name,
           sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric,
           sum(b.gross_profit)::numeric / nullif(sum(b.doanh_thu_thuan), 0),
           sum(b.qty)::numeric, count(DISTINCT b.customer_code),
           mart.la_phi_dieu_chinh(b.product_code, s.kind_code),
           mart.la_dong_hang_tang(b.product_code, s.kind_code, s.food_category_name)
    FROM mart.dong_ban_khoang(tu, den) b
    LEFT JOIN core.dim_product s ON s.product_code = b.product_code
    GROUP BY b.product_code, s.product_name, s.food_category_name, s.kind_code
$$;

DROP FUNCTION mart.khach_mat_hang_khoang(date, date);
CREATE FUNCTION mart.khach_mat_hang_khoang(tu date, den date)
RETURNS TABLE (customer_code text, product_code text, ten_hang text, dt numeric, lg numeric,
               so_luong numeric, so_ngay_mua bigint, lan_cuoi date, la_phi boolean,
               la_hang_tang boolean)
LANGUAGE sql STABLE
AS $$
    SELECT b.customer_code, b.product_code,
           CASE WHEN coalesce(b.product_code, '') = '' THEN '(điều chỉnh làm tròn — không mã hàng)'
                ELSE coalesce(nullif(s.product_name, ''), b.product_code) END,
           sum(b.doanh_thu_thuan)::numeric, sum(b.gross_profit)::numeric, sum(b.qty)::numeric,
           count(DISTINCT b.sales_date), max(b.sales_date),
           mart.la_phi_dieu_chinh(b.product_code, s.kind_code),
           mart.la_dong_hang_tang(b.product_code, s.kind_code, s.food_category_name)
    FROM mart.dong_ban_khoang(tu, den) b
    LEFT JOIN core.dim_product s ON s.product_code = b.product_code
    GROUP BY b.customer_code, b.product_code, s.product_name, s.kind_code, s.food_category_name
$$;

-- mart.khach_mat_hang — thân chép nguyên từ 048; CHỈ đổi vị từ lọc thành
-- mart.khong_phai_hang (phí & điều chỉnh + hàng tặng POSM).
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
        -- 048: phí thu hộ / phí gửi / giảm giá (無形) cũng vậy.
        -- 049: hàng tặng POSM (雑貨_VNM) cũng vậy — cùng một hàm.
        WHERE NOT mart.khong_phai_hang(f.product_code, s.kind_code, s.food_category_name)
        GROUP BY f.customer_code, f.product_code, s.product_name,
                 n.so_khoang, n.nhip_ngay, m.hom_nay
    ) x
) y
LEFT JOIN mart.dau_hieu_khach dh ON dh.customer_code = y.customer_code;

-- mart.san_pham_360 — thân chép nguyên từ 048; CHỈ đổi vị từ WHERE cuối.
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
-- 048/049: phí & điều chỉnh (無形 / không mã) và hàng tặng POSM không phải một
-- mặt hàng của danh mục.
WHERE NOT mart.khong_phai_hang(p.product_code, p.kind_code, p.food_category_name);
