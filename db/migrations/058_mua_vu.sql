-- 058 — Mùa vụ sản phẩm (/mua-vu, đặc tả 2026-09-29-mua-vu-san-pham-design.md).
--
-- Mỗi dòng = một mã × một ngày có bán: doanh thu thuần, lãi gộp, số lượng. Màn kéo
-- thanh thời gian theo NGÀY rồi cộng cửa sổ 7/30/90 ngày ở trình duyệt, nên cần đúng
-- hạt ngày (mart.san_pham_theo_thang là tháng).
--
-- Đọc mart.ban_den_moc (040/044): quay về theo mốc, bỏ mã nội bộ, GIỮ 赤伝 (số âm).
-- Phí & điều chỉnh (048) và hàng tặng POSM (049) không phải sản phẩm: gộp về hai mã
-- giả '__phi' / '__tang' (mã OBC không có '_') để màn in dòng "Không vẽ" — tiền vẫn
-- đủ, Σ mọi dòng một ngày = Σ (amount − tax_amount) của ban_den_moc ngày đó.
-- Phí xét TRƯỚC (cùng thứ tự mart.la_dong_hang_tang). LEFT JOIN: mã bán không có
-- trong master vẫn có dòng, không rơi mất tiền.

CREATE VIEW mart.mua_vu_ngay AS
SELECT CASE WHEN mart.la_phi_dieu_chinh(f.product_code, p.kind_code) THEN '__phi'
            WHEN mart.la_hang_tang(p.food_category_name)             THEN '__tang'
            ELSE f.product_code END          AS ma,
       f.sales_date                          AS ngay,
       sum(f.amount - f.tax_amount)          AS doanh_thu_thuan,
       sum(f.gross_profit)                   AS lai_gop,
       sum(f.qty)                            AS so_luong
FROM mart.ban_den_moc f
LEFT JOIN core.dim_product p ON p.product_code = f.product_code
GROUP BY 1, 2;

GRANT SELECT ON mart.mua_vu_ngay TO kome_app, kome_report, kome_ingest;
