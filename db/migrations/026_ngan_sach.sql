-- 026: ngân sách — chỉ tiêu doanh thu theo nhân viên theo tháng.
--
-- LƯU Ý BẤT BIẾN: ALTER DEFAULT PRIVILEGES của 009/010 KHÔNG có mệnh đề
-- FOR ROLE, nên file này (như mọi migration) PHẢI chạy bằng vai trò
-- `postgres`. Chạy bằng vai trò khác thì hai bảng dưới đây âm thầm không
-- nhận quyền mặc định, và lỗi chỉ lộ ra bằng một `permission denied` nhiều
-- tháng sau, giữa lúc có người đang nhập chỉ tiêu.
--
-- OBC KHÔNG xuất ra chỉ tiêu. Đây là dữ liệu nhập tay, 5 người × 12 tháng.

-- ---------------------------------------------------------------------------
-- Chỉ tiêu
-- ---------------------------------------------------------------------------

CREATE TABLE app.ngan_sach (
    salesperson_code text NOT NULL REFERENCES core.dim_salesperson,
    -- `thang` là DATE mùng 1, không phải text 'YYYY-MM': CSDL tự chặn
    -- '2026-13' và '26-07', còn CHECK chặn nốt ngày khác mùng 1 — không tồn
    -- tại được hai dòng "cùng tháng" khác ngày.
    --
    -- Khoá ngoại tới core.dim_date (phủ 2024-01-01 → 2035-12-31) KHÔNG phải
    -- trang trí: mart.ngan_sach_thang nối sang dim_date để lấy company_fy,
    -- nên một dòng ngoài dải lịch sẽ biến mất khỏi MỌI báo cáo mà không lỗi
    -- nào nổ ra — dữ liệu còn trong bảng, chỉ là không ai nhìn thấy nữa.
    -- Có khoá ngoại thì nó là lỗi ghi ngay tại chỗ nhập, đọc ra được nguyên
    -- nhân ("không đặt được chỉ tiêu 2036"), khác hẳn "lưu xong mà báo cáo
    -- không thấy".
    thang            date NOT NULL REFERENCES core.dim_date (date_key)
                          CHECK (extract(day FROM thang) = 1),
    -- Tiền LUÔN là số nguyên yên (CLAUDE.md, bẫy số 2).
    muc_tieu         bigint NOT NULL CHECK (muc_tieu >= 0),
    sua_luc          timestamptz NOT NULL DEFAULT now(),
    -- NULL khi máy trong công ty để trống KOME_SESSION_SECRET — không có cổng
    -- đăng nhập thì không ai là ai. KHÔNG dùng ON DELETE CASCADE: xoá một tài
    -- khoản không được phép kéo theo chỉ tiêu của cả năm.
    sua_boi          bigint NULL REFERENCES app.nguoi_dung,
    PRIMARY KEY (salesperson_code, thang)
);

COMMENT ON TABLE app.ngan_sach IS
  'Chỉ tiêu doanh thu do chủ DN đặt. KHÔNG có dòng = chưa đặt; muc_tieu = 0 =
   đã đặt và đặt bằng không. Hai thứ khác nhau và màn hình phải hiện khác
   nhau — cùng nếp mart.san_pham_360.ton.';

-- Nhật ký sửa: CHỈ THÊM, không bao giờ UPDATE/DELETE.
-- KHÔNG có khoá ngoại tới app.ngan_sach, và đó là chủ ý: nhật ký phải sống
-- sót sau khi dòng chỉ tiêu bị xoá — chính lúc bị xoá mới là lúc cần biết ai
-- xoá.
CREATE TABLE app.ngan_sach_nhat_ky (
    id               bigserial PRIMARY KEY,
    salesperson_code text NOT NULL,
    thang            date NOT NULL,
    -- NULL ở cột cũ = đặt lần đầu. NULL ở cột mới = xoá chỉ tiêu.
    -- Cả hai cùng NULL không bao giờ được ghi.
    muc_tieu_cu      bigint NULL,
    muc_tieu_moi     bigint NULL,
    sua_boi          bigint NULL REFERENCES app.nguoi_dung,
    sua_luc          timestamptz NOT NULL DEFAULT now(),
    CHECK (muc_tieu_cu IS NOT NULL OR muc_tieu_moi IS NOT NULL)
);

-- Cổng vào màn Ngân sách: đặt và sửa chỉ tiêu của cả công ty.
-- Mặc định FALSE — quyền ghi phải được cấp TƯỜNG MINH, cùng nếp
-- duoc_vao_kho_du_lieu (019).
ALTER TABLE app.nguoi_dung
    ADD COLUMN duoc_sua_ngan_sach boolean NOT NULL DEFAULT false;

-- ---------------------------------------------------------------------------
-- Định nghĩa chỉ số
-- ---------------------------------------------------------------------------

-- Mẫu số của mọi phép "đến hôm nay".
--
-- HẠN CHẾ CÓ TÊN: core.dim_date KHÔNG có cột ngày lễ Nhật. is_weekend chỉ
-- loại thứ Bảy và Chủ nhật, nên tháng có Tuần lễ Vàng (5月) hay Obon (8月) bị
-- đếm thừa 2–4 ngày làm việc và vạch mốc khắt khe hơn thực tế ở đúng những
-- tháng đó. Ghi ra chứ KHÔNG bịa một định nghĩa thứ hai (ví dụ "ngày có phiếu
-- bán"): hai định nghĩa cùng tên là hai con số nói hai điều.
CREATE VIEW mart.ngay_kinh_doanh AS
SELECT to_char(d.date_key, 'YYYY-MM')                                 AS thang,
       count(*) FILTER (WHERE NOT d.is_weekend)                       AS ngay_kd,
       count(*) FILTER (WHERE NOT d.is_weekend AND d.date_key <= m.hom_nay)
                                                                      AS ngay_kd_da_qua
FROM core.dim_date d CROSS JOIN mart.moc_thoi_gian m
GROUP BY 1;

COMMENT ON VIEW mart.ngay_kinh_doanh IS
  'hom_nay = ngày bán mới nhất trong kho (mart.moc_thoi_gian), KHÔNG phải
   current_date. Kho rỗng thì hom_nay NULL và ngay_kd_da_qua = 0 — đúng, vì
   chưa có ngày nào có số liệu.';

-- Chỉ tiêu, đã đổi khoá sang chuỗi 'YYYY-MM'.
-- Đây là CHỖ DUY NHẤT đổi date -> 'YYYY-MM', và cũng là chỗ duy nhất tra
-- company_fy của tháng — lấy từ core.dim_date, KHÔNG tính tay (luật số 3 của
-- 014_mart_bao_cao.sql).
CREATE VIEW mart.ngan_sach_thang AS
SELECT to_char(n.thang, 'YYYY-MM') AS thang,
       d.company_fy,
       n.salesperson_code,
       n.muc_tieu
FROM app.ngan_sach n
JOIN core.dim_date d ON d.date_key = n.thang;

-- Thực tế theo người theo tháng. Cùng khuôn mart.ban_theo_nhan_vien (014),
-- chỉ đổi trục gộp từ kỳ sang tháng.
CREATE VIEW mart.ban_theo_nhan_vien_thang AS
SELECT thang,
       min(company_fy)      AS company_fy,
       salesperson_code,
       sum(doanh_thu_thuan) AS doanh_thu_thuan,
       sum(gross_profit)    AS lai_gop,
       -- Tỷ suất là TỶ SỐ CỦA CÁC TỔNG, không bao giờ là trung bình của các
       -- tỷ số từng dòng (bất biến đã ghi, migration 021).
       sum(gross_profit)::numeric / nullif(sum(doanh_thu_thuan), 0) AS ty_suat,
       count(DISTINCT customer_code) AS so_khach,
       count(DISTINCT slip_no)       AS so_phieu
FROM mart.dong_ban
GROUP BY thang, salesperson_code;

-- Nơi ở của công thức tiến độ.
--
-- FULL JOIN, KHÔNG LEFT JOIN theo chiều nào cả — đây là điểm dễ hỏng nhất:
--   - ngan_sach LEFT JOIN ban_theo: tháng có doanh thu mà QUÊN đặt chỉ tiêu
--     biến mất khỏi báo cáo, doanh thu thật không xuất hiện ở đâu.
--   - ban_theo LEFT JOIN ngan_sach: người CÓ chỉ tiêu mà bán 0 đồng biến mất
--     — đúng người cần nhìn nhất thì không có dòng nào.
-- Cả hai chiều đều mất dòng mà TRANG VẪN VẼ RA BÌNH THƯỜNG, không lỗi nào nổ
-- ra. Cùng lớp lỗi đã ghi cho /ban-do (dim_prefecture LEFT JOIN khach_theo_tinh).
--
-- ĐO THẬT 2026-09-22: chiều thứ nhất mất dòng NGAY HÔM NAY. Dữ liệu bán có 6
-- mã phụ trách (0000, 0002, 0004, 0102, 0104, 0105) còn core.dim_salesperson
-- chỉ có 5 — mã 0000 có 1 khách và ¥28.981 doanh thu kỳ 7, và không bao giờ
-- đặt được chỉ tiêu vì khoá ngoại chặn.
CREATE VIEW mart.tien_do_ngan_sach AS
SELECT coalesce(b.thang, n.thang)                        AS thang,
       coalesce(b.company_fy, n.company_fy)              AS company_fy,
       coalesce(b.salesperson_code, n.salesperson_code)  AS salesperson_code,
       n.muc_tieu,
       coalesce(b.doanh_thu_thuan, 0)::bigint            AS thuc_te,
       k.ngay_kd,
       k.ngay_kd_da_qua,
       (n.muc_tieu * k.ngay_kd_da_qua::numeric / nullif(k.ngay_kd, 0))::bigint
                                                         AS muc_tieu_den_hom_nay,
       -- nullif: chỉ tiêu 0 cho ra NULL và màn hình in "—". Chia cho 0 thì
       -- trang chết; in "∞" thì người đọc tưởng đã vượt mức.
       coalesce(b.doanh_thu_thuan, 0)::numeric / nullif(n.muc_tieu, 0) AS tien_do
FROM mart.ban_theo_nhan_vien_thang b
FULL JOIN mart.ngan_sach_thang     n ON n.thang = b.thang
                                    AND n.salesperson_code = b.salesperson_code
LEFT JOIN mart.ngay_kinh_doanh     k ON k.thang = coalesce(b.thang, n.thang);

COMMENT ON VIEW mart.tien_do_ngan_sach IS
  'FULL JOIN chỉ tiêu <-> thực tế. Đổi thành LEFT JOIN theo BẤT KỲ chiều nào
   cũng làm mất dòng mà trang vẫn vẽ bình thường. Có test canh cả hai chiều:
   tests/test_ngan_sach_mart.py.';

-- Quyền: 009/010 đã ALTER DEFAULT PRIVILEGES cho schema app (TABLES và
-- SEQUENCES) và cho mart, nên hai bảng app.* và bốn view mart.* trên tự nhận
-- quyền — với điều kiện file này chạy bằng vai trò `postgres`. NHƯNG dòng
-- ALTER DEFAULT PRIVILEGES của 009 (schema core, mart) chỉ kể tên
-- `kome_app, kome_report` — KHÔNG kể `kome_ingest`. Vì vậy bốn view mới
-- không tự có SELECT cho kome_ingest, và mọi migration trước đã thêm view
-- vào mart (014, 015, 016, 020, 021, 022, 023, 024, 025) đều kết thúc bằng
-- một dòng GRANT tường minh giống dòng dưới đây — quên dòng này thì lỗi
-- không nổ ra lúc migration chạy, nó nổ bằng `permission denied` nhiều
-- tháng sau, giữa lúc có người đang nạp dữ liệu lúc 13:30. Có test canh:
-- tests/test_ngan_sach_mart.py::test_bon_view_moi_deu_cap_SELECT_cho_ca_ba_vai_tro.
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;

-- kome_report tự nhận SELECT trên hai bảng mới. GIỮ NGUYÊN, không REVOKE như
-- đã làm với app.nguoi_dung: chỉ tiêu doanh thu là con số nghiệp vụ, không
-- phải hash mật khẩu.
--
-- LƯU Ý — chuyện KHÁC với đoạn GRANT ở trên: mart.ngan_sach_thang đọc
-- app.ngan_sach, mà kome_ingest KHÔNG có USAGE trên schema app. Chỗ ĐÓ vẫn
-- chạy được cho kome_ingest (một khi đã có SELECT trên chính view, như dòng
-- GRANT ở trên vừa cấp), vì Postgres kiểm quyền trên BẢNG NỀN mà view đọc
-- theo CHỦ SỞ HỮU VIEW (ở đây là postgres), không theo người đang gọi.
-- "Chủ sở hữu view" chỉ miễn kiểm tra CHO BẢNG NỀN — người gọi vẫn phải có
-- SELECT trên CHÍNH CÁI VIEW, và đó là thứ dòng GRANT ở trên cấp. Hai luật
-- khác nhau, đừng gộp làm một. Hệ quả vẫn giữ: đặt gì vào một view của mart
-- là công bố thứ đó cho MỌI vai trò đọc mart. Không đưa cột nhạy cảm nào
-- vào theo đường này.
