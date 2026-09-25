-- 045 — Nạp hằng ngày trên bản Vercel (đặc tả 2026-09-25-nap-tren-vercel-design.md).
--
-- Trên Vercel ổ đĩa là TẠM và bước Xác nhận có thể chạy ở một phiên bản hàm khác bước
-- Kiểm, nên hai thứ trước đây nằm trên đĩa phải đổi chỗ:
--
-- 1. File CHỜ XÁC NHẬN (nạp hai bước, kome/nap_cho.py) → bảng meta.nap_cho. Dòng sống
--    từ lúc Kiểm tới lúc Xác nhận / Huỷ, hoặc bị dọn sau 24 giờ. Máy trong công ty vẫn
--    dùng thư mục _cho_xac_nhan/ như cũ (KOME_KHO_NAP=dia).
--
-- 2. FILE GỐC (lớp raw, kome/archive.py) → trên Vercel KHÔNG lưu (chủ DN chọn
--    2026-09-25). archived_to NULL = "lô nạp ở nơi không lưu file gốc". Mã băm và số
--    dòng vẫn ghi, nên chặn nạp trùng (archive.already_loaded) không đổi.
--
-- QUYỀN: 009 cho kome_ingest SELECT/INSERT/UPDATE trên meta, KHÔNG DELETE — vì
-- meta.ingest_batch là sổ lịch sử (hoàn tác chỉ đặt undone_at). File chờ thì phải xoá
-- được, nên cấp DELETE trên ĐÚNG bảng này, không đụng quyền mặc định của schema.
-- kome_app / kome_report không có quyền gì: file chờ là dữ liệu thô CHƯA qua 5 cổng.

ALTER TABLE meta.ingest_batch ALTER COLUMN archived_to DROP NOT NULL;

CREATE TABLE meta.nap_cho (
    ma        text        PRIMARY KEY CHECK (ma ~ '^[0-9a-f]{32}$'),
    ten_file  text        NOT NULL,
    o         text        NOT NULL DEFAULT '',
    noi_dung  bytea       NOT NULL,
    luc       timestamptz NOT NULL DEFAULT now()
);

REVOKE ALL ON meta.nap_cho FROM kome_app, kome_report;
GRANT SELECT, INSERT, DELETE ON meta.nap_cho TO kome_ingest;
