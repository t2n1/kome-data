-- 069 — Chỉ mục sổ nhật ký đối thủ theo đối tượng (đợt 4b, kế hoạch 2026-09-29-doi-thu-dot-4b-giao-dien.md Task 1).
-- Mỗi quan sát / điều kiện / bên trả `sua_cuoi` = max(id) nhật ký trên khoá của chính nó ('gia:<id>', 'tay:<id>',
-- '<bên>/<hàng>', 'giao:<bên>', 'dk:<fact_id>', 'dk:tay:<bên>', 'ben:<mã>'), và pop-up sửa đọc lịch sử theo khoá —
-- sổ chỉ thêm nên lớn dần. Chỉ mục (doi_tuong, id DESC) cho cả hai phép đó một lần tra, không quét sổ; số lượt hỏi
-- không đổi.

CREATE INDEX doi_thu_nhat_ky_doi_tuong_idx ON app.doi_thu_nhat_ky (doi_tuong, id DESC);
