-- 030: đợt 7 — danh sách ưu tiên liên hệ + nhật ký tiếp xúc.
--
-- LƯU Ý BẤT BIẾN: như mọi migration, PHẢI chạy bằng vai trò `postgres`
-- (ALTER DEFAULT PRIVILEGES của 009/010 không có FOR ROLE). Chạy bằng vai trò
-- khác thì bảng app.nhat_ky_tiep_xuc âm thầm không nhận quyền mặc định, và
-- kome_app nổ `permission denied` đúng lúc một sale vừa gọi xong bấm "Thêm".
--
-- OBC KHÔNG có dữ liệu này. Trước đợt 7, kết quả mọi cuộc gọi nằm trong đầu
-- hoặc tin nhắn riêng của từng nhân viên (đặc tả đợt 1 §1.3).

-- ---------------------------------------------------------------------------
-- Nhật ký tiếp xúc — CHỈ THÊM, không UPDATE/DELETE (như app.ngan_sach_nhat_ky).
-- Ghi sai thì thêm một dòng đính chính: sổ tay của năm người không có ai làm
-- "biên tập viên", và một dòng sửa lặng lẽ là một cuộc gọi không còn ai nhớ.
-- ---------------------------------------------------------------------------
CREATE TABLE app.nhat_ky_tiep_xuc (
    id             bigserial PRIMARY KEY,
    -- TEXT, giữ số 0 đầu (CLAUDE.md bẫy #1). KHÔNG có khoá ngoại: dim_customer
    -- là SCD2, customer_code không duy nhất trên cả bảng (chỉ duy nhất trong
    -- các dòng is_current). Tầng Python kiểm mã có tồn tại trước khi ghi.
    customer_code  text NOT NULL,
    -- NULL khi máy trong công ty để trống KOME_SESSION_SECRET (không ai là ai).
    -- Không ON DELETE CASCADE: xoá tài khoản không được kéo theo lịch sử gọi.
    nguoi_dung_id  bigint NULL REFERENCES app.nguoi_dung,
    thoi_diem      timestamptz NOT NULL DEFAULT now(),
    -- Ba kiểu của gói thiết kế (Customer 360.dc.html, KIEU_TX):
    -- goi = 📞 Gọi điện · ghe = 🚗 Ghé thăm · chat = 💬 Chat / Email.
    kieu           text NOT NULL CHECK (kieu IN ('goi', 'ghe', 'chat')),
    -- Ba mức của gói thiết kế (KQ_TX): tot = Tích cực · binh = Bình thường ·
    -- xau = Cần theo dõi.
    ket_qua        text NOT NULL CHECK (ket_qua IN ('tot', 'binh', 'xau')),
    noi_dung       text NOT NULL CHECK (length(btrim(noi_dung)) > 0),
    -- Hẹn liên hệ lại. Là NGÀY NGOÀI ĐỜI THẬT, không phải ngày của dữ liệu bán
    -- — nên so với đồng hồ thật giờ Tokyo (kome/lien_he.py), cùng ngoại lệ với
    -- ô tuổi dữ liệu, KHÔNG với mart.moc_thoi_gian.
    hen_lai        date NULL
);

CREATE INDEX ON app.nhat_ky_tiep_xuc (customer_code, thoi_diem DESC);
CREATE INDEX ON app.nhat_ky_tiep_xuc (thoi_diem DESC);

-- "Chỉ thêm" là ràng buộc của CSDL, không chỉ quy ước trong code: 009 cấp
-- mặc định SELECT/INSERT/UPDATE/DELETE trên mọi bảng app cho kome_app, nên
-- rút lại hai quyền sửa/xoá ở ĐÚNG bảng này. Code lỡ viết một câu UPDATE thì
-- CSDL từ chối. Có test canh (tests/test_lien_he.py).
REVOKE UPDATE, DELETE ON app.nhat_ky_tiep_xuc FROM kome_app;

COMMENT ON TABLE app.nhat_ky_tiep_xuc IS
  'Gọi, ghé thăm, chat đã ghi nhận. Chỉ thêm — ghi sai thì thêm dòng đính chính.';

-- ---------------------------------------------------------------------------
-- Lý do liên hệ — ĐỌC mart.khach_360, không viết định nghĩa mới.
--
-- 'lau_khong_mua' và 'qua_han' là ĐÚNG hai trạng thái của nhóm việc 'im'
-- (mart.khach_nhom_viec, 020/022) — định nghĩa DUY NHẤT của "khách đang rời
-- đi". Có test canh hai tập bằng nhau.
--
-- 'sap_den_han' là dải MỚI mà trước đợt 7 không hiện ở đâu cả: khách
-- 'binh_thuong' đã im lặng ≥ 1 lần nhịp mua riêng — đúng vùng Excel của Long
-- gọi là そろそろ連絡. Gọi được TRƯỚC khi khách trễ hẳn.
--
-- Hai nhóm 'tut'/'moi' của khach_nhom_viec KHÔNG vào đây: view đó tham chiếu
-- khach_360 ba lần (mỗi lần dựng lại cả view, ~1,2 s trên CSDL thật), nên kéo
-- nó vào là nhân bốn chi phí trang. Màn /lien-he trỏ sang
-- /khach-hang?nhom=tut|moi cho hai nhóm đó.
--
-- Loại 'ngung_giao_dich' (※廃業※/※取引停止※, 016) và 'chua_du_lich_su'
-- (chưa đủ 3 lần mua để có nhịp) — cùng cổng với /can-xu-ly.
-- ---------------------------------------------------------------------------
CREATE VIEW mart.uu_tien_lien_he AS
SELECT customer_code, ten, prefecture, phone, salesperson_code,
       doanh_thu_thuan, lan_cuoi, so_ngay_im_lang, nhip_ngay, ty_le_im_lang,
       trang_thai,
       CASE trang_thai
         WHEN 'da_roi_bo'   THEN 'lau_khong_mua'
         WHEN 'canh_bao'    THEN 'qua_han'
         ELSE                    'sap_den_han'
       END AS ly_do,
       CASE trang_thai
         WHEN 'da_roi_bo'   THEN 1
         WHEN 'canh_bao'    THEN 2
         ELSE                    3
       END AS thu_tu
FROM mart.khach_360
WHERE trang_thai IN ('da_roi_bo', 'canh_bao')
   OR (trang_thai = 'binh_thuong' AND ty_le_im_lang >= 1);

-- kome_app/kome_report tự nhận SELECT trên view mới (009), còn kome_ingest
-- thì KHÔNG — dòng này bắt buộc, cùng nếp 026–029.
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
