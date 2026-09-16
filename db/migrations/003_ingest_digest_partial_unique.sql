-- Sửa lỗi: digest UNIQUE vô điều kiện làm cho lô đã hoàn tác không nạp lại được.
-- Chỉ những lô CÒN HIỆU LỰC mới cần duy nhất theo digest; lô đã huỷ thì không.
ALTER TABLE meta.ingest_batch DROP CONSTRAINT IF EXISTS ingest_batch_digest_key;
CREATE UNIQUE INDEX ingest_batch_digest_active
    ON meta.ingest_batch (digest) WHERE undone_at IS NULL;
