CREATE TABLE meta.ingest_batch (
    batch_id     bigserial PRIMARY KEY,
    spec_name    text        NOT NULL,
    source_file  text        NOT NULL,
    digest       text        NOT NULL UNIQUE,
    archived_to  text        NOT NULL,
    row_count    integer     NOT NULL,
    total_amount bigint      NOT NULL DEFAULT 0,
    loaded_at    timestamptz NOT NULL DEFAULT now(),
    undone_at    timestamptz
);
CREATE INDEX ON meta.ingest_batch (spec_name, loaded_at DESC);

COMMENT ON COLUMN meta.ingest_batch.digest IS
  'SHA-256 nội dung file. UNIQUE = nạp lại đúng file cũ sẽ bị từ chối.';
