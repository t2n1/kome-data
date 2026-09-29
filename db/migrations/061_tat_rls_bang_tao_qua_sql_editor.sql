-- 061 — Tắt RLS trên các bảng được tạo qua SQL Editor của Supabase (sự cố thật 2026-09-29).
--
-- Supabase SQL Editor tự bật ROW LEVEL SECURITY cho bảng mới tạo trong đó; `python db/migrate.py`
-- thì không. Phân quyền của hệ thống này là theo VAI TRÒ (009: GRANT/REVOKE cho kome_ingest /
-- kome_app / kome_report), không dùng RLS — và không có policy nào, nên RLS bật = kome_app,
-- kome_ingest không thấy dòng nào và không ghi được gì (đo thật: app.doi_thu 21 dòng seed đọc ra 0).
-- Bảng dính: 059 (chạy tay qua SQL Editor) và meta.nap_cho (045).
-- Chạy lại vô hại (DISABLE trên bảng đã tắt là no-op). Chạy migration mới qua SQL Editor thì
-- PHẢI chạy kèm file này cho bảng mới tạo — xem docs/runbook.md.

ALTER TABLE core.fact_gia_doi_thu       DISABLE ROW LEVEL SECURITY;
ALTER TABLE core.fact_dieu_kien_doi_thu DISABLE ROW LEVEL SECURITY;
ALTER TABLE app.doi_thu                 DISABLE ROW LEVEL SECURITY;
ALTER TABLE app.loai_nguon              DISABLE ROW LEVEL SECURITY;
ALTER TABLE app.nhom_so_sanh            DISABLE ROW LEVEL SECURITY;
ALTER TABLE app.nhom_so_sanh_ma         DISABLE ROW LEVEL SECURITY;
ALTER TABLE app.ghep_hang               DISABLE ROW LEVEL SECURITY;
ALTER TABLE app.dinh_chinh_gia          DISABLE ROW LEVEL SECURITY;
ALTER TABLE app.gia_doi_thu_tay         DISABLE ROW LEVEL SECURITY;
ALTER TABLE app.quy_cach_kome           DISABLE ROW LEVEL SECURITY;
ALTER TABLE app.doi_thu_nhat_ky         DISABLE ROW LEVEL SECURITY;
ALTER TABLE meta.nap_cho                DISABLE ROW LEVEL SECURITY;
