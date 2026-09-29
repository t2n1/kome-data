-- 059 — Thị trường & đối thủ: bảng (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4).
--
-- core = thứ NẠP qua cổng (kome_ingest, batch_id, hoàn tác theo lô) · app = thứ WEB GHI (kome_app).
-- Đối thủ không phải OBC nhưng luật "không UPDATE core" áp nguyên: sửa của sale ở app.
-- KHÔNG có khoá ngoại từ app sang core.fact_gia_doi_thu: hoàn tác lô phải xoá được dòng core;
-- đính chính mồ côi thì mart bỏ qua (060).

CREATE TABLE core.fact_gia_doi_thu (
    id                 bigserial PRIMARY KEY,
    batch_id           bigint NOT NULL REFERENCES meta.ingest_batch(batch_id),
    ma_dong            text   NOT NULL,
    ma_doi_thu         text   NOT NULL,
    ma_hang_dt         text   NOT NULL,
    ngay_nguon         date   NOT NULL,
    hinh_thuc_nguon    text   NOT NULL CHECK (hinh_thuc_nguon IN ('file', 'web')),
    nguon_file         text,
    vi_tri             text,
    ten_goc            text   NOT NULL,
    ten_nhat           text,
    jan                text,
    quy_cach_goc       text,
    gia_goc            numeric(12,2),
    don_vi_gia         text,
    kg_moi_don_vi_gia  numeric(12,4),
    thue               text   CHECK (thue IN ('chua', 'co', 'khong_ro')),
    gom_ship           text   CHECK (gom_ship IN ('co', 'khong', 'khong_ro')),
    kenh_gia           text,
    muc_gia            text,
    gia_bac            text,
    gia_truoc_km       numeric(12,2),
    trang_thai         text   NOT NULL CHECK (trang_thai IN ('con', 'het', 'sap_ve', 'khong_ro')),
    han_su_dung        text,
    khuyen_mai         text,
    ma_kome_de_xuat    text,
    nhan_de_xuat       text   CHECK (nhan_de_xuat IN ('cung_hang', 'thay_the')),
    ly_do_ghep         text,
    do_chac            text   NOT NULL CHECK (do_chac IN ('chac', 'can_xem')),
    ghi_chu            text,
    UNIQUE (batch_id, ma_dong)
);
CREATE INDEX fact_gia_doi_thu_hang ON core.fact_gia_doi_thu (ma_doi_thu, ma_hang_dt);

CREATE TABLE core.fact_dieu_kien_doi_thu (
    id          bigserial PRIMARY KEY,
    batch_id    bigint NOT NULL REFERENCES meta.ingest_batch(batch_id),
    ma_dong     text   NOT NULL,
    ma_doi_thu  text   NOT NULL,
    ngay_nguon  date   NOT NULL,
    nguon_file  text,
    vi_tri      text,
    loai        text   NOT NULL CHECK (loai IN ('ship', 'khuyen_mai', 'thanh_toan', 'thue', 'khac')),
    noi_dung    text   NOT NULL,
    UNIQUE (batch_id, ma_dong)
);

CREATE TABLE app.doi_thu (
    ma             text PRIMARY KEY,
    ten            text NOT NULL,
    web            text,
    ghi_chu        text,
    dang_theo_doi  boolean NOT NULL DEFAULT true
);
INSERT INTO app.doi_thu (ma, ten, web) VALUES
 ('ASIA-TRADING', 'Asia Trading', NULL), ('BOMPEX', 'Bompex Japan', NULL), ('BUI-TRAM', 'Bùi Trâm', NULL),
 ('DAIICHI', '第一株式会社 (Daiichi)', NULL), ('EIHATSU', 'Eihatsu', NULL), ('HSC', 'HSC Station', 'https://app.hscstation.com/'),
 ('ICHIBA', 'Ichiba Foods', NULL), ('IMAI', 'IMAI', NULL), ('JVB', 'JVB Food', 'https://jvbfood.asia/'),
 ('MT-ONE', 'MT-One', NULL), ('MUNDIAL', 'Mundial Foods', 'https://www.mundialfoods.co.jp/'),
 ('NEXT', 'NEXT', NULL), ('NICHIETSU', '日越合同会社 (Nichietsu)', NULL), ('OBA', 'OBA', NULL),
 ('THAI-DUONG', 'Thái Dương Mart', 'https://tdmvn.shop/all-products'), ('THAK', 'THAK JSC', 'https://thak.jp/'),
 ('VIETCOOK', 'Vietcook', NULL), ('VIETNAM-HOUSE', 'Vietnam House', NULL), ('YUMI', 'Yumi Foods', NULL),
 ('QUANG-KE', 'Quảng Kẹ', NULL), ('VIPRO', 'ViPro', 'https://sale.vipro-jp.com/');

CREATE TABLE app.loai_nguon (
    ma              text PRIMARY KEY,
    ten             text NOT NULL,
    thu_tu          int  NOT NULL UNIQUE,     -- độ tin cậy, 1 = cao nhất
    can_bang_chung  boolean NOT NULL DEFAULT false
);
INSERT INTO app.loai_nguon VALUES
 ('bang_gia', 'Bảng giá / web của đối thủ', 1, false),
 ('chung_tu', 'Chứng từ khách đưa (hoá đơn, phiếu giao)', 2, true),
 ('to_roi',   'Tờ rơi / tin nhắn đối thủ gửi', 3, true),
 ('khach_ke', 'Khách kể', 4, false),
 ('khac',     'Nghe nói / khác', 5, false);

CREATE TABLE app.nhom_so_sanh (
    id   bigserial PRIMARY KEY,
    ten  text NOT NULL UNIQUE CHECK (length(btrim(ten)) BETWEEN 1 AND 80)
);
CREATE TABLE app.nhom_so_sanh_ma (
    product_code  text PRIMARY KEY,
    nhom_id       bigint NOT NULL REFERENCES app.nhom_so_sanh(id) ON DELETE CASCADE
);

CREATE TABLE app.ghep_hang (
    ma_doi_thu     text NOT NULL,
    ma_hang_dt     text NOT NULL,
    product_code   text,
    nhom_id        bigint REFERENCES app.nhom_so_sanh(id) ON DELETE SET NULL,
    nhan           text NOT NULL CHECK (nhan IN ('cung_hang', 'thay_the', 'khong')),
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ma_doi_thu, ma_hang_dt)
);

CREATE TABLE app.dinh_chinh_gia (
    id             bigserial PRIMARY KEY,
    fact_id        bigint NOT NULL,
    truong         text   NOT NULL CHECK (truong IN ('xac_nhan', 'ten_goc', 'quy_cach_goc', 'gia_goc',
                        'don_vi_gia', 'kg_moi_don_vi_gia', 'thue', 'gom_ship', 'kenh_gia', 'muc_gia', 'trang_thai')),
    gia_tri_moi    text,
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX dinh_chinh_gia_fact ON app.dinh_chinh_gia (fact_id, truong, id DESC);

CREATE TABLE app.gia_doi_thu_tay (
    id                 bigserial PRIMARY KEY,
    ma_doi_thu         text NOT NULL REFERENCES app.doi_thu(ma),
    ma_hang_dt         text NOT NULL,
    fact_goc_id        bigint,                   -- dòng nạp mà quan sát này cập nhật (NULL = hàng mới)
    ten_goc            text NOT NULL CHECK (length(btrim(ten_goc)) > 0),
    quy_cach_goc       text,
    gia_goc            numeric(12,2) CHECK (gia_goc IS NULL OR gia_goc >= 0),
    don_vi_gia         text,
    kg_moi_don_vi_gia  numeric(12,4) CHECK (kg_moi_don_vi_gia IS NULL OR kg_moi_don_vi_gia > 0),
    thue               text CHECK (thue IN ('chua', 'co', 'khong_ro')),
    gom_ship           text CHECK (gom_ship IN ('co', 'khong', 'khong_ro')),
    kenh_gia           text,
    muc_gia            text,
    trang_thai         text NOT NULL DEFAULT 'con' CHECK (trang_thai IN ('con', 'het', 'sap_ve', 'khong_ro')),
    loai_nguon         text NOT NULL REFERENCES app.loai_nguon(ma),
    ghi_chu_nguon      text,
    customer_code      text,
    tiep_xuc_id        bigint,
    nguoi_dung_id      bigint REFERENCES app.nguoi_dung(id),
    luc                timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app.quy_cach_kome (
    product_code   text PRIMARY KEY,
    kg_moi_goi     numeric(12,4) CHECK (kg_moi_goi IS NULL OR kg_moi_goi > 0),
    goi_moi_thung  numeric(12,2) CHECK (goi_moi_thung IS NULL OR goi_moi_thung > 0),
    kg_moi_thung   numeric(12,4) CHECK (kg_moi_thung IS NULL OR kg_moi_thung > 0)
);

CREATE TABLE app.doi_thu_nhat_ky (
    id             bigserial PRIMARY KEY,
    loai           text NOT NULL CHECK (loai IN ('xac_nhan', 'sua', 'gia_moi', 'them', 'ghep', 'nhom', 'quy_cach', 'doi_thu')),
    doi_tuong      text NOT NULL,
    truoc          jsonb,
    sau            jsonb,
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now()
);

-- Quyền. Default privileges của 009/010 đã cấp: core → ingest SELECT/INSERT/UPDATE/DELETE, app & report SELECT;
-- app → kome_app CRUD, report SELECT. Ghi lại cho rõ và rút UPDATE/DELETE ở ba sổ chỉ thêm (nếp 030).
GRANT SELECT, INSERT, UPDATE, DELETE ON core.fact_gia_doi_thu, core.fact_dieu_kien_doi_thu TO kome_ingest;
GRANT SELECT ON core.fact_gia_doi_thu, core.fact_dieu_kien_doi_thu TO kome_app, kome_report;
REVOKE INSERT, UPDATE, DELETE ON core.fact_gia_doi_thu, core.fact_dieu_kien_doi_thu FROM kome_app;
GRANT SELECT ON app.ghep_hang, app.nhom_so_sanh, app.nhom_so_sanh_ma, app.doi_thu TO kome_ingest;  -- Claude đọc cặp ghép khi dựng gói
REVOKE UPDATE, DELETE ON app.dinh_chinh_gia, app.gia_doi_thu_tay, app.doi_thu_nhat_ky FROM kome_app;
