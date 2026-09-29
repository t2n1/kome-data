-- 063 — Tin hiện trường `@` (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §6, đợt 2).
-- (1) app.tiep_xuc_nhac: thẻ @ trong câu ghi chú (vị trí trong câu). CHỈ THÊM (nếp 030/059): `kome_app` không
--     UPDATE/DELETE. Câu gốc ở app.nhat_ky_tiep_xuc KHÔNG đổi.
-- (2) app.gia_doi_thu_tay.nhom_khoa: giá khách kể (loai_nguon = 'khach_ke') mang sẵn nhóm mà thẻ @hàng trỏ tới
--     ('ma:<mã KOME>' | 'n:<id>', cùng định dạng 060) — không có bước ghép, vì sale chọn nhóm ngay trong thẻ.
-- (3) mart.gia_doi_thu_quan_sat thay lại: thân GIỐNG HỆT 060 trừ (a) nap/tay mang thêm cột trong `nhom_ke`
--     (nap: NULL, tay: mart.nhom_cua_khoa(t.nhom_khoa) — xem (4)) và (b) `nhom_khoa` = coalesce(nhom_ke, biểu thức cũ), `ten_nhom` của nhom_ke lấy
--     tên nhóm có tên hoặc tên hàng KOME. Danh sách/thứ tự cột RA không đổi (CREATE OR REPLACE VIEW), nên
--     mart.gia_doi_thu_hien_hanh / so_sanh_nhom (060, 062) đọc lại được không cần tạo lại.
--     Tin khách kể vẫn ngoài trung vị (`loai_nguon <> 'khach_ke'` ở 060/062) và ma_hang_dt RA = 'ke:<khách>:<nhóm HIỆN
--     HÀNH>' (dựng lúc đọc, xem nhánh `tay`) nên phân vùng `hien_hanh` của 060 tách theo (khách, bên, nhóm): tin trùng
--     → mới nhất; hai khách không đè nhau.
-- (4) mart.nhom_cua_khoa(khoa): khoá nhóm HIỆN HÀNH của một khoá đã lưu — 'ma:<mã>' mà mã đó nằm trong một
--     nhóm có tên (app.nhom_so_sanh_ma) -> 'n:<nhóm>'; còn lại giữ nguyên. Giải LÚC ĐỌC (thẻ và giá đã lưu giữ
--     nguyên như lúc ghi — sổ chỉ thêm), nên đổi thành viên nhóm sau này thì mọi chỗ đi theo. ĐỊNH NGHĨA MỘT LẦN:
--     view (3) và mọi truy vấn gộp / đếm thẻ `@` (kome/doi_thu.py) gọi hàm này, không tự chép CASE.
--     Không có nó, giá khách kể gắn `@<mã>` của một mã thuộc nhóm có tên nằm ở nhóm ngầm định 'ma:<mã>' — không
--     so với các bên cùng nhóm (không bao giờ bất thường), không lên So sánh giá, Hiện trường đếm thành hai món.
-- 059–062 đã chạy trên CSDL thật — không sửa. Chạy bằng `postgres` qua `python db/migrate.py` (không SQL Editor — bẫy RLS, 061).

CREATE TABLE app.tiep_xuc_nhac (
    id           bigserial PRIMARY KEY,
    tiep_xuc_id  bigint NOT NULL REFERENCES app.nhat_ky_tiep_xuc(id),
    loai         text   NOT NULL CHECK (loai IN ('doi_thu', 'nhom')),
    khoa         text   NOT NULL,            -- doi_thu: app.doi_thu.ma · nhom: 'ma:<mã>' | 'n:<id>'
    vi_tri_dau   int    NOT NULL CHECK (vi_tri_dau >= 0),
    do_dai       int    NOT NULL CHECK (do_dai > 0)
);
CREATE INDEX tiep_xuc_nhac_khoa ON app.tiep_xuc_nhac (loai, khoa);
CREATE INDEX tiep_xuc_nhac_tx ON app.tiep_xuc_nhac (tiep_xuc_id);
GRANT SELECT, INSERT ON app.tiep_xuc_nhac TO kome_app;
GRANT USAGE ON SEQUENCE app.tiep_xuc_nhac_id_seq TO kome_app;
REVOKE UPDATE, DELETE ON app.tiep_xuc_nhac FROM kome_app;
GRANT SELECT ON app.tiep_xuc_nhac TO kome_report, kome_ingest;

ALTER TABLE app.gia_doi_thu_tay ADD COLUMN nhom_khoa text;   -- giá khách kể: nhóm mà thẻ @hàng trỏ tới

CREATE FUNCTION mart.nhom_cua_khoa(p_khoa text) RETURNS text LANGUAGE sql STABLE AS $$
    SELECT coalesce((SELECT 'n:' || nm.nhom_id FROM app.nhom_so_sanh_ma nm
                     WHERE left(p_khoa, 3) = 'ma:' AND nm.product_code = substr(p_khoa, 4)), p_khoa)
$$;
GRANT EXECUTE ON FUNCTION mart.nhom_cua_khoa(text) TO kome_app, kome_report, kome_ingest;

CREATE OR REPLACE VIEW mart.gia_doi_thu_quan_sat AS
WITH dc AS (
    SELECT DISTINCT ON (fact_id, truong) fact_id, truong, gia_tri_moi
    FROM app.dinh_chinh_gia ORDER BY fact_id, truong, id DESC
),
p AS (
    SELECT fact_id,
           max(gia_tri_moi) FILTER (WHERE truong = 'ten_goc')           AS ten_goc,
           max(gia_tri_moi) FILTER (WHERE truong = 'quy_cach_goc')      AS quy_cach_goc,
           max(gia_tri_moi) FILTER (WHERE truong = 'gia_goc')           AS gia_goc,
           max(gia_tri_moi) FILTER (WHERE truong = 'don_vi_gia')        AS don_vi_gia,
           max(gia_tri_moi) FILTER (WHERE truong = 'kg_moi_don_vi_gia') AS kg,
           max(gia_tri_moi) FILTER (WHERE truong = 'thue')              AS thue,
           max(gia_tri_moi) FILTER (WHERE truong = 'gom_ship')          AS gom_ship,
           max(gia_tri_moi) FILTER (WHERE truong = 'kenh_gia')          AS kenh_gia,
           max(gia_tri_moi) FILTER (WHERE truong = 'muc_gia')           AS muc_gia,
           max(gia_tri_moi) FILTER (WHERE truong = 'trang_thai')        AS trang_thai,
           bool_or(truong = 'xac_nhan')                                 AS xac_nhan,
           bool_or(truong <> 'xac_nhan')                                AS da_sua
    FROM dc GROUP BY fact_id
),
nap AS (
    SELECT 'nap'::text AS nguon, f.id, f.batch_id, f.ma_doi_thu, f.ma_hang_dt, f.ngay_nguon, f.hinh_thuc_nguon,
           f.nguon_file, f.vi_tri,
           coalesce(p.ten_goc, f.ten_goc) AS ten_goc, coalesce(p.quy_cach_goc, f.quy_cach_goc) AS quy_cach_goc,
           coalesce(CASE WHEN p.gia_goc ~ '^\s*\d+(\.\d+)?\s*$' THEN p.gia_goc::numeric END, f.gia_goc) AS gia_goc,
           coalesce(p.don_vi_gia, f.don_vi_gia) AS don_vi_gia,
           coalesce(CASE WHEN p.kg ~ '^\s*\d+(\.\d+)?\s*$' THEN p.kg::numeric END, f.kg_moi_don_vi_gia) AS kg_moi_don_vi_gia,
           coalesce(p.thue, f.thue) AS thue, coalesce(p.gom_ship, f.gom_ship) AS gom_ship,
           coalesce(p.kenh_gia, f.kenh_gia) AS kenh_gia, coalesce(p.muc_gia, f.muc_gia) AS muc_gia,
           f.gia_bac, f.gia_truoc_km, coalesce(p.trang_thai, f.trang_thai) AS trang_thai, f.khuyen_mai,
           'bang_gia'::text AS loai_nguon, f.ghi_chu, f.ma_kome_de_xuat, f.nhan_de_xuat,
           CASE WHEN p.da_sua THEN 'da_sua' WHEN p.xac_nhan THEN 'da_xac_nhan'
                WHEN f.do_chac = 'can_xem' THEN 'can_xem' ELSE 'ai_doc' END AS trang_thai_duyet,
           NULL::text AS nhom_ke
    FROM core.fact_gia_doi_thu f LEFT JOIN p ON p.fact_id = f.id
),
tay AS (
    -- Giá khách kể: khoá chuỗi (ma_hang_dt) dựng LÚC ĐỌC từ nhóm HIỆN HÀNH — 'ke:<khách>:<nhom_cua_khoa(khoá đã ghi)>'
    -- — để "tin mới nhất của (khách, bên, nhóm) là hiện trạng" đúng cả khi cùng hàng được gắn lúc 'ma:<mã>', lúc
    -- 'n:<nhóm>' (hay mã được thêm vào nhóm sau). Cột lưu app.gia_doi_thu_tay.ma_hang_dt giữ nguyên (sổ chỉ thêm).
    SELECT 'tay'::text, t.id, NULL::bigint, t.ma_doi_thu,
           CASE WHEN t.loai_nguon = 'khach_ke' AND t.nhom_khoa IS NOT NULL AND t.customer_code IS NOT NULL
                THEN 'ke:' || t.customer_code || ':' || mart.nhom_cua_khoa(t.nhom_khoa)
                ELSE t.ma_hang_dt END,
           (t.luc AT TIME ZONE 'Asia/Tokyo')::date,
           'tay'::text, NULL::text, NULL::text, t.ten_goc, t.quy_cach_goc, t.gia_goc, t.don_vi_gia,
           t.kg_moi_don_vi_gia, t.thue, t.gom_ship, t.kenh_gia, t.muc_gia, NULL::text, NULL::numeric,
           t.trang_thai, NULL::text, t.loai_nguon, t.ghi_chu_nguon,
           NULL::text, NULL::text, 'nhap_tay'::text, mart.nhom_cua_khoa(t.nhom_khoa)
    FROM app.gia_doi_thu_tay t
),
tat AS (SELECT * FROM nap UNION ALL SELECT * FROM tay),
ghep AS (
    SELECT a.*, g.ma_doi_thu IS NOT NULL AS co_ghep,
           CASE WHEN g.ma_doi_thu IS NULL THEN a.ma_kome_de_xuat
                WHEN g.nhan = 'khong' THEN NULL ELSE g.product_code END AS ma_kome,
           CASE WHEN g.ma_doi_thu IS NULL THEN a.nhan_de_xuat
                WHEN g.nhan = 'khong' THEN NULL ELSE g.nhan END         AS nhan,
           CASE WHEN g.nhan = 'khong' THEN NULL ELSE g.nhom_id END AS nhom_ghep
    FROM tat a LEFT JOIN app.ghep_hang g USING (ma_doi_thu, ma_hang_dt)
    WHERE a.ngay_nguon <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date))
)
SELECT x.nguon, x.id, x.batch_id, x.ma_doi_thu, d.ten AS ten_doi_thu, x.ma_hang_dt, x.ngay_nguon,
       x.hinh_thuc_nguon, x.nguon_file, x.vi_tri, x.ten_goc, x.quy_cach_goc, x.gia_goc, x.don_vi_gia,
       x.kg_moi_don_vi_gia, x.thue, x.gom_ship, x.kenh_gia, x.muc_gia, x.gia_bac, x.gia_truoc_km, x.trang_thai,
       x.khuyen_mai, x.loai_nguon, ln.thu_tu AS thu_tu_nguon, x.ghi_chu, x.ma_kome, x.nhan,
       coalesce(x.nhom_ke,
                CASE WHEN x.nhom_ghep IS NOT NULL THEN 'n:' || x.nhom_ghep
                     WHEN nm.nhom_id IS NOT NULL THEN 'n:' || nm.nhom_id
                     WHEN x.ma_kome IS NOT NULL THEN 'ma:' || x.ma_kome END)          AS nhom_khoa,
       CASE WHEN x.nhom_ke IS NOT NULL THEN coalesce(nk.ten, kk.product_name)
            ELSE coalesce(ng.ten, nn.ten, kp.product_name) END                        AS ten_nhom,
       x.trang_thai_duyet,
       x.gia_goc / coalesce(nullif(x.kg_moi_don_vi_gia, 0), 1)
                 / CASE WHEN x.thue = 'co' THEN 1.08 ELSE 1 END                        AS yen_chuan,
       CASE WHEN x.kg_moi_don_vi_gia > 0 THEN 'kg' ELSE 'don_vi:' || coalesce(x.don_vi_gia, '?') END AS don_vi_so,
       concat_ws(' · ', CASE x.thue WHEN 'co' THEN 'có thuế (đã quy về chưa thuế)' WHEN 'chua' THEN 'chưa thuế'
                                  ELSE 'thuế không rõ' END,
                        CASE x.gom_ship WHEN 'co' THEN 'gồm ship' WHEN 'khong' THEN 'chưa ship' ELSE 'ship không rõ' END,
                        x.kenh_gia, x.muc_gia)                                         AS nen_gia,
       row_number() OVER (PARTITION BY x.ma_doi_thu, x.ma_hang_dt, coalesce(x.kenh_gia, ''), coalesce(x.muc_gia, ''),
                                       (x.loai_nguon = 'khach_ke')
                          ORDER BY x.ngay_nguon DESC, ln.thu_tu, (x.nguon = 'tay') DESC, x.batch_id DESC NULLS FIRST, x.id DESC) = 1
                                                                                       AS hien_hanh,
       (SELECT hom_nay FROM mart.moc_thoi_gian) - x.ngay_nguon                         AS tuoi_ngay
FROM ghep x
LEFT JOIN app.doi_thu d ON d.ma = x.ma_doi_thu
LEFT JOIN app.loai_nguon ln ON ln.ma = x.loai_nguon
LEFT JOIN app.nhom_so_sanh_ma nm ON nm.product_code = x.ma_kome AND x.nhom_ghep IS NULL
LEFT JOIN app.nhom_so_sanh ng ON ng.id = x.nhom_ghep
LEFT JOIN app.nhom_so_sanh nn ON nn.id = nm.nhom_id
LEFT JOIN core.dim_product kp ON kp.product_code = x.ma_kome
LEFT JOIN app.nhom_so_sanh nk ON nk.id = CASE WHEN x.nhom_ke ~ '^n:[0-9]+$' THEN substr(x.nhom_ke, 3)::bigint END
LEFT JOIN core.dim_product kk ON kk.product_code = CASE WHEN x.nhom_ke LIKE 'ma:%' THEN substr(x.nhom_ke, 4) END;

GRANT SELECT ON mart.gia_doi_thu_quan_sat TO kome_app, kome_report, kome_ingest;
