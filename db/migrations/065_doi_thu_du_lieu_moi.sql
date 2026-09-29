-- 065 — Dữ liệu cho giao diện mới /doi-thu (đặc tả 2026-09-29-doi-thu-giao-dien-moi-design.md §5).
-- (1) Quy cách gói + giá bậc có cấu trúc của đối thủ (§5.1, §5.2). `bac` là MẢNG
--     [{"tu": 5, "don_vi_sl": "thung"|"kg"|"goi"|"pallet", "gia": 5300, "don_vi_gia": "thung"|"kg"|"goi"}] cùng `thue`
--     của dòng; chữ `gia_bac` giữ làm nguyên văn. Quy về ¥/kg chỉ ở mart (067).
-- (2) core.dim_product.pack1_*: 荷姿１ của 商品データ (§6.3 việc 2). pack1_code NULL = bản nạp chưa có cột này
--     (mart giữ luật cũ), '' = mã KHÔNG có 荷姿 nào → một đơn vị '00' là cả sản phẩm như tên ghi (xốt Barona/HVX).
-- (3) Điều kiện giao hàng có cấu trúc (§5.4): core = bản Claude đọc (nạp theo lô), app.giao_hang_kome = của KOME
--     (một dòng, sửa được, mặc định SUY từ phiếu bán: 配送料500 trên 985 đơn < ¥20,000 · 代引 ¥330 / ¥300 từ ¥20,000).
-- (4) Sổ sửa CHỈ THÊM của sale: dinh_chinh_giao_hang, dinh_chinh_dieu_kien. Không có trong anh_chup._PHIEN_BAN —
--     mọi đường ghi (kome/doi_thu_giao.py) ghi thêm app.doi_thu_nhat_ky CÙNG giao dịch (nếp 064).
-- 059–064 đã chạy trên CSDL thật — không sửa. Chạy bằng postgres qua python db/migrate.py (không SQL Editor — 061).

ALTER TABLE core.fact_gia_doi_thu
    ADD COLUMN so_goi_thung integer       CHECK (so_goi_thung IS NULL OR so_goi_thung > 0),
    ADD COLUMN kl_goi_g     numeric(10,2) CHECK (kl_goi_g IS NULL OR (kl_goi_g > 0 AND kl_goi_g <= 30000)),
    ADD COLUMN bac          jsonb         CHECK (bac IS NULL OR jsonb_typeof(bac) = 'array');
ALTER TABLE app.gia_doi_thu_tay
    ADD COLUMN so_goi_thung integer       CHECK (so_goi_thung IS NULL OR so_goi_thung > 0),
    ADD COLUMN kl_goi_g     numeric(10,2) CHECK (kl_goi_g IS NULL OR (kl_goi_g > 0 AND kl_goi_g <= 30000)),
    ADD COLUMN bac          jsonb         CHECK (bac IS NULL OR jsonb_typeof(bac) = 'array'),
    ADD COLUMN khuyen_mai   text,
    ADD COLUMN gia_truoc_km numeric(12,2) CHECK (gia_truoc_km IS NULL OR gia_truoc_km >= 0);

ALTER TABLE core.dim_product
    ADD COLUMN pack1_code     text,
    ADD COLUMN pack1_base_qty numeric(14,4);

ALTER TABLE app.dinh_chinh_gia DROP CONSTRAINT dinh_chinh_gia_truong_check;
ALTER TABLE app.dinh_chinh_gia ADD CONSTRAINT dinh_chinh_gia_truong_check CHECK (truong IN ('xac_nhan', 'ten_goc',
    'quy_cach_goc', 'gia_goc', 'don_vi_gia', 'kg_moi_don_vi_gia', 'thue', 'gom_ship', 'kenh_gia', 'muc_gia', 'trang_thai',
    'so_goi_thung', 'kl_goi_g', 'bac', 'khuyen_mai', 'gia_truoc_km'));

ALTER TABLE app.doi_thu_nhat_ky DROP CONSTRAINT doi_thu_nhat_ky_loai_check;
ALTER TABLE app.doi_thu_nhat_ky ADD CONSTRAINT doi_thu_nhat_ky_loai_check
    CHECK (loai IN ('xac_nhan', 'sua', 'gia_moi', 'them', 'ghep', 'nhom', 'quy_cach', 'doi_thu', 'thu_muc',
                    'giao_hang', 'dieu_kien'));

-- 'ghi_chu_doc' = câu người đọc tự ghi lúc đọc file ("chép vào ghi_chu…", "không in thông tin thuế") — KHÔNG phải
-- điều kiện của bên; mart.dieu_kien_hien_hanh (068) bỏ loại này (§5.4 "Tách ghi chú nội bộ").
ALTER TABLE core.fact_dieu_kien_doi_thu DROP CONSTRAINT fact_dieu_kien_doi_thu_loai_check;
ALTER TABLE core.fact_dieu_kien_doi_thu ADD CONSTRAINT fact_dieu_kien_doi_thu_loai_check
    CHECK (loai IN ('ship', 'khuyen_mai', 'thanh_toan', 'thue', 'khac', 'ghi_chu_doc'));

CREATE TABLE core.fact_giao_hang_doi_thu (
    id               bigserial PRIMARY KEY,
    batch_id         bigint NOT NULL REFERENCES meta.ingest_batch(batch_id),
    ma_dong          text   NOT NULL,
    ma_doi_thu       text   NOT NULL,
    ngay_nguon       date   NOT NULL,
    bao_ship         boolean,
    phi_ship         numeric(10,2) CHECK (phi_ship IS NULL OR phi_ship >= 0),
    phi_ship_theo    text   CHECK (phi_ship_theo IN ('don', 'thung', 'kien')),
    mien_ship_tu     numeric(12,2) CHECK (mien_ship_tu IS NULL OR mien_ship_tu >= 0),
    mien_ship_kien   integer CHECK (mien_ship_kien IS NULL OR mien_ship_kien > 0),
    thung_moi_kien   integer CHECK (thung_moi_kien IS NULL OR thung_moi_kien > 0),
    phu_phi          jsonb  CHECK (phu_phi IS NULL OR jsonb_typeof(phu_phi) = 'object'),
    phi_daibiki      numeric(10,2) CHECK (phi_daibiki IS NULL OR phi_daibiki >= 0),
    daibiki_tu       numeric(12,2) CHECK (daibiki_tu IS NULL OR daibiki_tu >= 0),
    daibiki_sau      numeric(10,2) CHECK (daibiki_sau IS NULL OR daibiki_sau >= 0),
    ck_mien_daibiki  boolean,
    kien_toi_da_kg   numeric(8,2) CHECK (kien_toi_da_kg IS NULL OR kien_toi_da_kg > 0),
    ghep_kien        text,
    thue             text   CHECK (thue IN ('bao', 'chua', 'khong_ro')),
    cach_gui         text,
    nguon_chu        text,
    nguon_file       text,
    UNIQUE (batch_id, ma_dong)
);
CREATE INDEX fact_giao_hang_doi_thu_ben ON core.fact_giao_hang_doi_thu (ma_doi_thu, batch_id DESC);

CREATE TABLE app.giao_hang_kome (
    id               boolean PRIMARY KEY DEFAULT true CHECK (id),
    bao_ship         boolean,
    phi_ship         numeric(10,2) CHECK (phi_ship IS NULL OR phi_ship >= 0),
    phi_ship_theo    text   CHECK (phi_ship_theo IN ('don', 'thung', 'kien')),
    mien_ship_tu     numeric(12,2) CHECK (mien_ship_tu IS NULL OR mien_ship_tu >= 0),
    mien_ship_kien   integer CHECK (mien_ship_kien IS NULL OR mien_ship_kien > 0),
    thung_moi_kien   integer CHECK (thung_moi_kien IS NULL OR thung_moi_kien > 0),
    phu_phi          jsonb  CHECK (phu_phi IS NULL OR jsonb_typeof(phu_phi) = 'object'),
    phi_daibiki      numeric(10,2) CHECK (phi_daibiki IS NULL OR phi_daibiki >= 0),
    daibiki_tu       numeric(12,2) CHECK (daibiki_tu IS NULL OR daibiki_tu >= 0),
    daibiki_sau      numeric(10,2) CHECK (daibiki_sau IS NULL OR daibiki_sau >= 0),
    ck_mien_daibiki  boolean,
    kien_toi_da_kg   numeric(8,2) CHECK (kien_toi_da_kg IS NULL OR kien_toi_da_kg > 0),
    ghep_kien        text,
    thue             text   CHECK (thue IN ('bao', 'chua', 'khong_ro')),
    cach_gui         text,
    da_xac_nhan      boolean NOT NULL DEFAULT false,
    sua_luc          timestamptz NOT NULL DEFAULT now(),
    sua_boi          bigint REFERENCES app.nguoi_dung(id)
);
INSERT INTO app.giao_hang_kome (bao_ship, phi_ship, phi_ship_theo, mien_ship_tu, phi_daibiki, daibiki_tu, daibiki_sau, thue)
VALUES (false, 500, 'don', 20000, 330, 20000, 300, 'chua');

CREATE TABLE app.dinh_chinh_giao_hang (
    id             bigserial PRIMARY KEY,
    ma_doi_thu     text NOT NULL REFERENCES app.doi_thu(ma),
    truong         text NOT NULL CHECK (truong IN ('bao_ship', 'phi_ship', 'phi_ship_theo', 'mien_ship_tu', 'mien_ship_kien',
                        'thung_moi_kien', 'phu_phi', 'phi_daibiki', 'daibiki_tu', 'daibiki_sau', 'ck_mien_daibiki',
                        'kien_toi_da_kg', 'ghep_kien', 'thue', 'cach_gui')),
    gia_tri_moi    text,                 -- '' = xoá về "không ghi"; jsonb cho phu_phi; 'true'/'false' cho bool
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX dinh_chinh_giao_hang_ben ON app.dinh_chinh_giao_hang (ma_doi_thu, truong, id DESC);

CREATE TABLE app.dinh_chinh_dieu_kien (
    id             bigserial PRIMARY KEY,
    fact_id        bigint,               -- dòng core.fact_dieu_kien_doi_thu được sửa; NULL = điều kiện sale THÊM tay
    ma_doi_thu     text NOT NULL REFERENCES app.doi_thu(ma),
    loai           text NOT NULL CHECK (loai IN ('ship', 'khuyen_mai', 'thanh_toan', 'thue', 'khac')),
    noi_dung       text NOT NULL CHECK (length(btrim(noi_dung)) BETWEEN 1 AND 300),
    bo             boolean NOT NULL DEFAULT false,   -- "không còn đúng — bỏ đi"
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX dinh_chinh_dieu_kien_fact ON app.dinh_chinh_dieu_kien (fact_id, id DESC);

GRANT SELECT, INSERT, UPDATE, DELETE ON core.fact_giao_hang_doi_thu TO kome_ingest;
GRANT SELECT ON core.fact_giao_hang_doi_thu TO kome_app, kome_report;
REVOKE INSERT, UPDATE, DELETE ON core.fact_giao_hang_doi_thu FROM kome_app;
GRANT SELECT, INSERT ON app.dinh_chinh_giao_hang, app.dinh_chinh_dieu_kien TO kome_app;
GRANT USAGE ON SEQUENCE app.dinh_chinh_giao_hang_id_seq, app.dinh_chinh_dieu_kien_id_seq TO kome_app;
REVOKE UPDATE, DELETE ON app.dinh_chinh_giao_hang, app.dinh_chinh_dieu_kien FROM kome_app;
GRANT SELECT, UPDATE ON app.giao_hang_kome TO kome_app;
REVOKE INSERT, DELETE ON app.giao_hang_kome FROM kome_app;
GRANT SELECT ON app.giao_hang_kome, app.dinh_chinh_giao_hang, app.dinh_chinh_dieu_kien TO kome_report, kome_ingest;
