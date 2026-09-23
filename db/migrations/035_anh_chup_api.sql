-- 035: ảnh chụp kết quả API theo PHIÊN BẢN DỮ LIỆU — để trang mở nhanh.
--
-- LƯU Ý BẤT BIẾN: chạy bằng vai trò `postgres` như mọi migration.
--
-- Đo thật 2026-09-23 (CSDL thật, chỉ SELECT): cả trang `/` cũ mất 9.039 ms ở
-- máy chủ; riêng count(*) trên mart.khach_nhom_viec 2.151 ms, san_pham_360
-- 1.591 ms, tien_do_ngan_sach 1.508 ms. Dữ liệu chỉ đổi khi nạp, hoàn tác, sửa
-- ngân sách, ghi tiếp xúc (và vài khối theo ngày Tokyo), nên tính lại các view
-- đó ở MỖI lượt xem là phí. Xem đặc tả
-- docs/superpowers/specs/2026-09-23-giao-dien-react-design.md §1b.
--
-- Một dòng = kết quả JSON của một khoá (vd 'tong-quan/ngan-sach') ở một phiên
-- bản dữ liệu. kome/web/anh_chup.py chỉ trả `du_lieu` khi `phien_ban` KHỚP
-- phiên bản hiện tại — không bao giờ trả số cũ hơn dữ liệu. Đây là bộ đệm,
-- KHÔNG phải nguồn sự thật: TRUNCATE lúc nào cũng an toàn (lượt xem sau tính lại).

CREATE TABLE app.anh_chup_api (
    khoa       text PRIMARY KEY,
    phien_ban  text NOT NULL,
    du_lieu    jsonb NOT NULL,
    tinh_luc   timestamptz NOT NULL DEFAULT now(),
    tinh_ms    integer NOT NULL          -- mất bao lâu để tính — để biết khối nào chậm
);

COMMENT ON TABLE app.anh_chup_api IS
  'Bộ đệm kết quả API theo phiên bản dữ liệu (kome/web/anh_chup.py). Xoá sạch lúc nào cũng an toàn.';

-- Phiên bản dữ liệu gồm cả migration mới nhất: một migration sửa view là số
-- đổi mà không có lô nạp nào, nên ảnh chụp cũ phải hết hiệu lực. kome_app cần
-- đọc được bảng theo dõi migration.
GRANT SELECT ON meta.schema_migration TO kome_app;
