-- 033: màn Nhật ký thao tác (20) và Cài đặt (21) — "ai làm gì" cho những thao
-- tác có hệ quả trên dữ liệu.
--
-- LƯU Ý BẤT BIẾN: chạy bằng vai trò `postgres` như mọi migration.
--
-- Nhật ký KHÔNG phải một bảng mới gom mọi thứ: bốn trong năm loại thao tác ĐÃ
-- được ghi ở nơi của chúng (meta.ingest_batch: nạp + hoàn tác · app.ngan_sach_nhat_ky:
-- sửa chỉ tiêu · app.nhat_ky_tiep_xuc: ghi tiếp xúc). Màn Nhật ký ĐỌC GỘP các
-- nguồn đó (kome/nhat_ky.py). Chép chúng sang một bảng thứ hai là hai sổ sẽ lệch
-- nhau đúng ngày một đường ghi quên ghi sổ kia. Migration này chỉ bù hai chỗ
-- còn thiếu: AI nạp / AI hoàn tác, và sổ thay đổi quyền.

-- ---------------------------------------------------------------------------
-- 1. Ai nạp, ai hoàn tác. NULL = máy trong công ty chưa bật đăng nhập (không
--    ai là ai), hoặc lô nạp trước 033. KHÔNG ON DELETE CASCADE.
-- ---------------------------------------------------------------------------
ALTER TABLE meta.ingest_batch
    ADD COLUMN nap_boi bigint NULL REFERENCES app.nguoi_dung,
    ADD COLUMN huy_boi bigint NULL REFERENCES app.nguoi_dung;

COMMENT ON COLUMN meta.ingest_batch.huy_boi IS
  'Người bấm Hoàn tác — nút duy nhất của hệ thống xoá được cả một tháng doanh thu.';

-- ---------------------------------------------------------------------------
-- 2. Quyền quản trị: được đổi cờ quyền của người khác trên màn Cài đặt.
--    Mặc định FALSE — cùng nếp duoc_vao_kho_du_lieu (019), duoc_sua_ngan_sach
--    (026). Người đầu tiên được cấp bằng script:
--      python scripts/tao_nguoi_dung.py quyen <tên> --quan-tri
--    Tạo tài khoản và đặt mật khẩu VẪN chỉ qua script (đặc tả đợt 3 §4.2): màn
--    Cài đặt không bao giờ nhận một mật khẩu.
-- ---------------------------------------------------------------------------
ALTER TABLE app.nguoi_dung
    ADD COLUMN duoc_quan_tri boolean NOT NULL DEFAULT false;

-- ---------------------------------------------------------------------------
-- 3. Sổ thay đổi quyền — CHỈ THÊM. Không khoá ngoại ở cột người bị đổi: sổ
--    phải sống sót sau khi tài khoản bị xoá (cùng lý lẽ ngan_sach_nhat_ky).
-- ---------------------------------------------------------------------------
CREATE TABLE app.nhat_ky_quyen (
    id             bigserial PRIMARY KEY,
    nguoi_dung_id  bigint NOT NULL,
    ten_dang_nhap  text NOT NULL,          -- chụp lại tên lúc đổi
    co             text NOT NULL CHECK (co IN ('duoc_vao_kho_du_lieu',
                                              'duoc_sua_ngan_sach', 'duoc_quan_tri')),
    gia_tri_cu     boolean NOT NULL,
    gia_tri_moi    boolean NOT NULL,
    sua_boi        bigint NULL REFERENCES app.nguoi_dung,
    sua_luc        timestamptz NOT NULL DEFAULT now(),
    CHECK (gia_tri_cu <> gia_tri_moi)
);
CREATE INDEX ON app.nhat_ky_quyen (sua_luc DESC);

-- "Chỉ thêm" là ràng buộc của CSDL (cùng nếp 030): 009 cấp mặc định
-- UPDATE/DELETE trên mọi bảng app cho kome_app.
REVOKE UPDATE, DELETE ON app.nhat_ky_quyen FROM kome_app;

COMMENT ON TABLE app.nhat_ky_quyen IS
  'Ai bật/tắt cờ quyền nào của ai, lúc nào. Chỉ thêm — không sửa, không xoá.';
