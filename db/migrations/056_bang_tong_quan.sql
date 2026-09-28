-- 056: NHIỀU bảng Tổng quan có tên cho mỗi người (thay 034: một người một bố cục).
--
-- LƯU Ý BẤT BIẾN: chạy bằng vai trò `postgres` như mọi migration.
-- Đặc tả: docs/superpowers/specs/2026-09-28-nhieu-bang-tong-quan-design.md
--
-- Mỗi dòng là một bảng RIÊNG của một người (không chia sẻ — chủ DN chốt
-- 2026-09-28). bo_cuc NULL = bố cục mặc định; nội dung luôn qua
-- kome/web/bo_cuc.py::chuan_hoa lúc ghi và lúc đọc (như 034). Quy tắc số lượng
-- (≤ 20 bảng, không xoá bảng cuối) ở kome/web/bang_tong_quan.py — CSDL chỉ canh
-- tên (độ dài + không trùng trong bảng của CÙNG người, không phân biệt hoa thường).
CREATE TABLE app.bang_tong_quan (
    id            bigserial PRIMARY KEY,
    nguoi_dung_id bigint NOT NULL REFERENCES app.nguoi_dung(id) ON DELETE CASCADE,
    ten           text   NOT NULL CHECK (length(btrim(ten)) BETWEEN 1 AND 40),
    bo_cuc        jsonb  NULL,
    thu_tu        int    NOT NULL,
    tao_luc       timestamptz NOT NULL DEFAULT now(),
    sua_luc       timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX bang_tong_quan_ten_uq ON app.bang_tong_quan (nguoi_dung_id, lower(btrim(ten)));
CREATE INDEX bang_tong_quan_nguoi_idx ON app.bang_tong_quan (nguoi_dung_id, thu_tu);

COMMENT ON TABLE app.bang_tong_quan IS
  'Bảng Tổng quan có tên của từng người (056). bo_cuc: [{id, rong 1-3, cao 1-4, an}], NULL = mặc định.';

-- Bảng xem gần nhất: CHỈ ghi khi người dùng chủ động chuyển tab / tạo bảng,
-- không ghi lúc tải trang. Xoá bảng thì về NULL (trang rơi về bảng đầu).
ALTER TABLE app.nguoi_dung
    ADD COLUMN bang_gan_nhat bigint NULL REFERENCES app.bang_tong_quan(id) ON DELETE SET NULL;

-- Quyền: 009 đã cấp mặc định cho bảng app mới; ghi lại tường minh, kể cả sequence.
GRANT SELECT, INSERT, UPDATE, DELETE ON app.bang_tong_quan TO kome_app;
GRANT USAGE ON SEQUENCE app.bang_tong_quan_id_seq TO kome_app;
GRANT SELECT ON app.bang_tong_quan TO kome_report;

-- Chép bố cục 034 thành "Bảng của tôi" — không ai mất cách xếp đang có.
-- Idempotent (NOT EXISTS) — tests/test_bang_tong_quan.py chạy lại khối này.
-- CHEP: bat dau
INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, bo_cuc, thu_tu)
SELECT n.id, 'Bảng của tôi', n.bo_cuc_tong_quan, 0
FROM app.nguoi_dung n
WHERE n.bo_cuc_tong_quan IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM app.bang_tong_quan b WHERE b.nguoi_dung_id = n.id);
UPDATE app.nguoi_dung n SET bang_gan_nhat = b.id
FROM app.bang_tong_quan b
WHERE b.nguoi_dung_id = n.id AND b.thu_tu = 0 AND n.bang_gan_nhat IS NULL;
-- CHEP: ket thuc

COMMENT ON COLUMN app.nguoi_dung.bo_cuc_tong_quan IS
  'NGỪNG DÙNG từ 056 — đã chép sang app.bang_tong_quan. Giữ làm lịch sử; không chỗ nào đọc/ghi.';
