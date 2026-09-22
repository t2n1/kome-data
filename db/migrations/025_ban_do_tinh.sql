-- 025: nền dữ liệu cho màn "Bản đồ khách hàng" (đợt 4c, man 24) — bảng tra 47
-- tỉnh và view gộp theo tỉnh. Xem đặc tả đầy đủ ở
-- docs/superpowers/specs/2026-09-22-dot-4c-ban-do-khach-hang-design.md §5.

-- LƯỚI Ô, KHÔNG PHẢI BẢN ĐỒ THEO TỶ LỆ (§5.1). Bốn lý do, xếp theo sức nặng
-- — làm sai cái đầu tiên là hỏng cả lý do tồn tại của màn hình:
--   1. Ô quan trọng nhất phải bấm được. Theo tỷ lệ thật, 東京都 (290 khách,
--      đông nhất công ty) nằm lọt trong một cụm đô thị chật hẹp và gần như
--      biến mất trên màn hình; ô vuông bằng nhau cho mọi tỉnh cùng quyền
--      được nhìn thấy và bấm trúng.
--   2. Bất biến màu: "màu phải kèm thứ đọc được", không phải chỉ tooltip. Ô
--      đều nhau mới đủ chỗ in con số vào bên trong.
--   3. Khớp kiến trúc đang có: SVG dựng sẵn từ Python phía server, không JS,
--      không tài nguyên ngoài — chạy được sau tường lửa công ty và trên bản
--      Vercel. Ba template trước đó (San pham, Ho so ma hang, Kho hang) đã
--      làm đúng kiểu này.
--   4. Trung thực về độ phân giải: dữ liệu ta có là CẤP TỈNH, không có toạ độ
--      của từng khách và sẽ không bao giờ có từ OBC (đã đo — xem đặc tả
--      §3.2). Một tấm bản đồ có đường bờ biển thật sẽ mời người đọc tin vào
--      một độ chính xác mà dữ liệu không có.

-- BẢNG PHẢI ĐỦ 47 DÒNG, KỂ CẢ TỈNH CHƯA CÓ KHÁCH (§5.2). Bảng này được
-- LEFT JOIN sang số liệu khách ở tầng trên (Task 2/3), không phải GROUP BY
-- trên khách rồi vẽ ra bấy nhiêu ô. Gom theo khách thì một tỉnh không có
-- khách nào sẽ BIẾN MẤT khỏi bản đồ — mà "chúng ta chưa có mặt ở tỉnh này"
-- đúng là một trong những điều một tấm bản đồ bán hàng phải nói ra, không
-- phải một ô trống cần giấu đi.
--
-- [Vòng sửa 1] Câu "hôm nay cả 47 tỉnh đều có khách" từng đứng ở đây là SAI,
-- chép lại nguyên một câu sai từ đặc tả §5.2/§3.1. Đo lại
-- (`mart.khach_360`, người soát 2026-09-22): `core.dim_customer` đúng là có
-- đủ 47 tỉnh, nhưng `mart.khach_360` chỉ 46 — 和歌山県 có 1 khách trong
-- `dim_customer` nhưng KHÔNG khách nào có doanh số, nên khách đó không có
-- dòng trong `khach_360` (view đó dựng từ `mart.lan_mua`, tức PHẢI có ít
-- nhất một lần bán). Nghĩa là ô 0 khách ĐẦU TIÊN đã tồn tại sẵn hôm nay, ở
-- 和歌山県, không phải đợi lọc theo người phụ trách mới lộ ra. Người làm
-- Task 2/3 thấy 和歌山県 trống trên bản đồ TỔNG (không lọc gì) là ĐÚNG, không
-- phải dấu hiệu phép nối hỏng — đừng đi sửa cái không hỏng.

-- `ten` LÀ KHOÁ NỐI VỚI CHUỖI OBC GHI THẬT, không phải một mã tự đặt. Đo thật
-- trên CSDL 2026-09-22: `SELECT DISTINCT prefecture FROM core.dim_customer
-- WHERE is_current` cho đúng 47 giá trị, TẤT CẢ có hậu tố 都/道/府/県 (kể cả
-- 北海道 — hậu tố 道 đã nằm sẵn trong tên, không phải phần thêm). Sai một ký
-- tự trong 47 dòng gieo bên dưới là tỉnh đó rỗng VĨNH VIỄN trên bản đồ, và
-- KHÔNG LỖI NÀO NỔ RA — phép nối chỉ đơn giản không khớp dòng nào, y hệt một
-- tỉnh chưa có khách. Không có bảng chuẩn hoá tên ở đây: dữ liệu OBC đã sạch,
-- thêm một lớp chuẩn hoá cho một cột không cần chuẩn hoá chỉ thêm chỗ để sai.

-- VỊ TRÍ LƯỚI LÀ DỮ LIỆU, KHÔNG PHẢI MÃ LỆNH (§5.3): hang_luoi/cot_luoi nằm
-- trong bảng, không phải trong if/match của Python hay trong template — sửa
-- vị trí một ô là sửa một dòng dữ liệu, không phải một lần deploy code. Bảng
-- CỐ Ý không có vĩ độ/kinh độ: toạ độ mà màn này cần là toạ độ LƯỚI, còn
-- vĩ độ/kinh độ chỉ có nghĩa cho một phép chiếu bản đồ thật — thứ §5.1 đã
-- bác bỏ. Thêm hai cột không ai đọc là mời người sau dựng phép chiếu đó.

CREATE TABLE core.dim_prefecture (
    ma_jis     text PRIMARY KEY,
    ten        text NOT NULL UNIQUE,
    ten_latin  text NOT NULL,
    ten_ngan   text NOT NULL,
    vung       text NOT NULL,
    hang_luoi  int  NOT NULL,
    cot_luoi   int  NOT NULL,
    -- Hai tỉnh chồng ô thì một tỉnh BIẾN MẤT khỏi bản đồ mà không ai thấy —
    -- trang vẫn vẽ ra bình thường, chỉ thiếu đúng một ô, và không có lỗi nào
    -- nổ ra để lộ chuyện đó. Ràng buộc này chặn ngay lúc INSERT (migration
    -- này sẽ không chạy được nếu 47 dòng bên dưới chồng ô), và chặn cả một
    -- migration SAU NÀY lỡ sửa vị trí một tỉnh mà quên kiểm ô đã có ai chiếm.
    UNIQUE (hang_luoi, cot_luoi)
);

COMMENT ON TABLE core.dim_prefecture IS
  'Bảng tra 47 tỉnh của Nhật cho màn Bản đồ khách hàng (đợt 4c). Gieo TĨNH,
   không nạp từ OBC — không thay đổi giữa các lần chạy migration. LEFT JOIN
   từ bảng này sang số liệu khách, KHÔNG BAO GIỜ GROUP BY ngược từ khách rồi
   suy ra danh sách tỉnh: cách đó làm tỉnh không có khách biến mất khỏi bản
   đồ thay vì hiện ra là "0 khách". Xem §5.1, §5.2 của đặc tả đợt 4c.';
COMMENT ON COLUMN core.dim_prefecture.ten IS
  'KHOÁ NỐI với core.dim_customer.prefecture — phải khớp CHÍNH XÁC chuỗi OBC
   ghi (đo thật 2026-09-22: 47 giá trị, đều có hậu tố 都/道/府/県). Sai một ký
   tự là tỉnh đó rỗng vĩnh viễn trên bản đồ và KHÔNG LỖI NÀO NỔ RA — phép nối
   chỉ lặng lẽ không khớp dòng nào.';
COMMENT ON COLUMN core.dim_prefecture.ten_ngan IS
  'Tên rút gọn in bên trong ô lưới — ô nhỏ, tên đầy đủ (vd. 神奈川県) tràn ô.';
COMMENT ON COLUMN core.dim_prefecture.vung IS
  '8 地方 (vùng địa lý). Dùng để vẽ dải phân vùng và tô viền nhóm trên bản đồ.';
COMMENT ON COLUMN core.dim_prefecture.hang_luoi IS
  'Toạ độ LƯỚI (không phải vĩ độ/kinh độ — §5.3), 1..14. Sửa vị trí một tỉnh
   trên bản đồ là UPDATE một dòng, không phải sửa code.';
COMMENT ON COLUMN core.dim_prefecture.cot_luoi IS
  'Toạ độ LƯỚI (không phải vĩ độ/kinh độ — §5.3), 1..12. Cùng ghi chú với
   hang_luoi.';

-- 47 dòng, thứ tự theo mã JIS 01–47. Cột: ma_jis, ten, ten_latin, ten_ngan,
-- vung, hang_luoi, cot_luoi. Lưới 14 hàng x 12 cột, 北海道 trên cùng bên phải,
-- 沖縄県 dưới cùng bên trái, 東北 chạy dọc sườn phải, 九州沖縄 ở góc dưới trái —
-- xếp theo vị trí tương đối thật của các tỉnh (§5.1).
INSERT INTO core.dim_prefecture
    (ma_jis, ten, ten_latin, ten_ngan, vung, hang_luoi, cot_luoi)
VALUES
    ('01', '北海道',   'Hokkaido',  '北海道',   '北海道',      1, 12),
    ('02', '青森県',   'Aomori',    '青森',     '東北',        2, 11),
    ('03', '岩手県',   'Iwate',     '岩手',     '東北',        3, 11),
    ('04', '宮城県',   'Miyagi',    '宮城',     '東北',        4, 11),
    ('05', '秋田県',   'Akita',     '秋田',     '東北',        3, 10),
    ('06', '山形県',   'Yamagata',  '山形',     '東北',        4, 10),
    ('07', '福島県',   'Fukushima', '福島',     '東北',        5, 11),
    ('08', '茨城県',   'Ibaraki',   '茨城',     '関東',        6, 12),
    ('09', '栃木県',   'Tochigi',   '栃木',     '関東',        6, 11),
    ('10', '群馬県',   'Gunma',     '群馬',     '関東',        6, 10),
    ('11', '埼玉県',   'Saitama',   '埼玉',     '関東',        7, 10),
    ('12', '千葉県',   'Chiba',     '千葉',     '関東',        7, 12),
    ('13', '東京都',   'Tokyo',     '東京',     '関東',        7, 11),
    ('14', '神奈川県', 'Kanagawa',  '神奈川',   '関東',        8, 10),
    ('15', '新潟県',   'Niigata',   '新潟',     '中部',        5, 10),
    ('16', '富山県',   'Toyama',    '富山',     '中部',        6,  9),
    ('17', '石川県',   'Ishikawa',  '石川',     '中部',        6,  8),
    ('18', '福井県',   'Fukui',     '福井',     '中部',        7,  7),
    ('19', '山梨県',   'Yamanashi', '山梨',     '中部',        8,  9),
    ('20', '長野県',   'Nagano',    '長野',     '中部',        7,  9),
    ('21', '岐阜県',   'Gifu',      '岐阜',     '中部',        7,  8),
    ('22', '静岡県',   'Shizuoka',  '静岡',     '中部',        9,  9),
    ('23', '愛知県',   'Aichi',     '愛知',     '中部',        8,  8),
    ('24', '三重県',   'Mie',       '三重',     '近畿',        9,  8),
    ('25', '滋賀県',   'Shiga',     '滋賀',     '近畿',        8,  7),
    ('26', '京都府',   'Kyoto',     '京都',     '近畿',        8,  6),
    ('27', '大阪府',   'Osaka',     '大阪',     '近畿',        9,  7),
    ('28', '兵庫県',   'Hyogo',     '兵庫',     '近畿',        9,  6),
    -- [Vòng sửa 1] 奈良県 (135,83°Đ) nằm ĐÔNG của 和歌山県 (135,17°Đ) trên bản
    -- đồ thật. Bản đầu đặt ngược (奈良 ở cột 6, 和歌山 ở cột 7) — đã đổi chỗ.
    -- 和歌山 giờ nằm dưới 兵庫 (cột 6) thay vì dưới 大阪 (cột 7) — một xấp xỉ
    -- chấp nhận được của lưới ô rời rạc, vì thứ tự đông–tây giữa hai tỉnh
    -- liền kề mới là thứ mắt người dùng bản đồ dùng để định vị, không phải
    -- việc mỗi tỉnh nằm thẳng dưới đúng "tỉnh mẹ" nào ở hàng trên.
    ('29', '奈良県',   'Nara',      '奈良',     '近畿',       10,  7),
    ('30', '和歌山県', 'Wakayama',  '和歌山',   '近畿',       10,  6),
    ('31', '鳥取県',   'Tottori',   '鳥取',     '中国',        8,  5),
    ('32', '島根県',   'Shimane',   '島根',     '中国',        9,  4),
    ('33', '岡山県',   'Okayama',   '岡山',     '中国',        9,  5),
    ('34', '広島県',   'Hiroshima', '広島',     '中国',       10,  4),
    ('35', '山口県',   'Yamaguchi', '山口',     '中国',       10,  3),
    ('36', '徳島県',   'Tokushima', '徳島',     '四国',       11,  5),
    ('37', '香川県',   'Kagawa',    '香川',     '四国',       10,  5),
    ('38', '愛媛県',   'Ehime',     '愛媛',     '四国',       11,  4),
    ('39', '高知県',   'Kochi',     '高知',     '四国',       12,  4),
    ('40', '福岡県',   'Fukuoka',   '福岡',     '九州沖縄',   11,  2),
    ('41', '佐賀県',   'Saga',      '佐賀',     '九州沖縄',   12,  2),
    ('42', '長崎県',   'Nagasaki',  '長崎',     '九州沖縄',   12,  1),
    ('43', '熊本県',   'Kumamoto',  '熊本',     '九州沖縄',   12,  3),
    ('44', '大分県',   'Oita',      '大分',     '九州沖縄',   11,  3),
    ('45', '宮崎県',   'Miyazaki',  '宮崎',     '九州沖縄',   13,  3),
    ('46', '鹿児島県', 'Kagoshima', '鹿児島',   '九州沖縄',   13,  2),
    ('47', '沖縄県',   'Okinawa',   '沖縄',     '九州沖縄',   14,  1);


-- View gộp theo tỉnh: một dòng mỗi cặp (tỉnh, người phụ trách). Nối từ
-- mart.khach_360 (một dòng một khách, đã gộp SCD2 của core.dim_customer về
-- is_current) chứ không từ core.dim_customer thẳng — nối core.dim_customer
-- thẳng có thể nhân dòng nếu ai đó lỡ quên WHERE is_current sau này (§5.4).
CREATE VIEW mart.khach_theo_tinh AS
SELECT k.prefecture,
       k.salesperson_code,
       count(*)                       AS so_khach,
       -- Doanh thu ĐỌC mart.hang_doanh_thu.dt_12t — nơi "doanh thu 12 tháng"
       -- đã được định nghĩa MỘT LẦN (migration 020). KHÔNG tự viết lại
       -- sum(...) WHERE sales_date > hom_nay - 365 ở đây, và TUYỆT ĐỐI KHÔNG
       -- dùng khach_360.doanh_thu_thuan — đó là doanh thu TOÀN BỘ LỊCH SỬ,
       -- một con số khác hẳn mang cái tên rất dễ nhầm với "12 tháng". Nhầm
       -- cột này thì bản đồ so sánh tỉnh sai lệch hoàn toàn: một tỉnh có vài
       -- khách lâu năm doanh thu lịch sử lớn sẽ tô đậm hơn một tỉnh đang bán
       -- tốt trong năm nay.
       coalesce(sum(h.dt_12t), 0)::bigint AS doanh_thu_12t,
       -- can_goi dùng EXISTS, KHÔNG LEFT JOIN mart.khach_nhom_viec — đúng
       -- hình mẫu migration 022. Một khách có thể thuộc NHIỀU nhóm việc cùng
       -- lúc ('im' và 'tut' cùng lúc, xem chú thích của 020), nên JOIN thẳng
       -- sẽ NHÂN DÒNG khách lên và thổi phồng cả `so_khach` lẫn
       -- `doanh_thu_12t` của tỉnh đó — không chỉ can_goi sai, cả hai cột kia
       -- cũng sai theo vì GROUP BY gộp trên dòng đã bị nhân đôi.
       --
       -- Khách ※廃業※/※取引停止※ ĐƯỢC đếm ở so_khach/doanh_thu_12t (họ vẫn là
       -- khách thật, từng có doanh thu thật) nhưng KHÔNG được đếm ở can_goi:
       -- mart.khach_nhom_viec đã tự loại họ khỏi nhóm 'im' (migration 016,
       -- doanh nghiệp đã phá sản thì im lặng là đúng, không phải bất
       -- thường) — không được thêm cổng ※廃業※ nào nữa ở đây, làm vậy là
       -- kiểm tra trùng một điều kiện đã có nhà ở chỗ khác (đúng bài học của
       -- migration 024 về "một khái niệm, một công thức").
       count(*) FILTER (
           WHERE EXISTS (SELECT 1 FROM mart.khach_nhom_viec v
                          WHERE v.customer_code = k.customer_code
                            AND v.nhom = 'im')) AS can_goi
FROM mart.khach_360 k
LEFT JOIN mart.hang_doanh_thu h ON h.customer_code = k.customer_code
GROUP BY 1, 2;

COMMENT ON VIEW mart.khach_theo_tinh IS
  'Một dòng mỗi cặp (tỉnh, người phụ trách) — nguồn dữ liệu của màn Bản đồ
   khách hàng (đợt 4c). Nối k.prefecture đúng CHUỖI OBC ghi (khớp
   core.dim_prefecture.ten) — trang tiêu thụ view này phải LEFT JOIN từ
   core.dim_prefecture SANG đây, không phải ngược lại, để tỉnh chưa có khách
   vẫn hiện trên bản đồ với 0 (§5.2). Khách không có tỉnh (đúng 1/1.710, đo
   2026-09-22) rơi vào một dòng prefecture=NULL — trang phải tự hiện dòng đó
   riêng dưới dạng "(không rõ tỉnh)", không được để LEFT JOIN với
   dim_prefecture âm thầm đánh rơi nó.';
COMMENT ON COLUMN mart.khach_theo_tinh.doanh_thu_12t IS
  'ĐỌC mart.hang_doanh_thu.dt_12t — không tự tính lại, không dùng
   khach_360.doanh_thu_thuan (đó là TOÀN BỘ LỊCH SỬ). Xem chú thích tại chỗ
   trong migration này.';
COMMENT ON COLUMN mart.khach_theo_tinh.can_goi IS
  'Đếm qua EXISTS vào mart.khach_nhom_viec (nhom=''im''), không LEFT JOIN —
   một khách có thể thuộc nhiều nhóm việc cùng lúc. Khách ※廃業※ đã bị
   khach_nhom_viec tự loại nên không lọt vào đây, dù vẫn được đếm ở so_khach.';

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
