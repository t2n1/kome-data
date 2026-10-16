-- 073 — Mã vắng ở ảnh chụp tồn mới nhất = HẾT HÀNG, không phải "chưa rõ tồn" (chủ DN chốt 2026-10-16).
--
-- OBC 在庫一覧 KHÔNG xuất dòng tồn bằng 0 (đo thật: bản xuất tay 24/9 có 175 dòng, bản 14/10 có 199 dòng,
-- 0 dòng nào 在庫残数 = 0). Nên một mã vừa bán hết thì BIẾN MẤT khỏi file, và trước bản này
-- `san_pham_360.ton` của nó là NULL ("chưa rõ tồn") — đo thật 15/10: 15 mã đang bán (vd BS04 bia
-- Sài Gòn, có tồn ở 41 ảnh chụp tới 14/10) hiện "Chưa rõ tồn", còn ô "Mã hết hàng" luôn = 0. Chủ DN:
-- "đang hết hàng thôi mà".
--
-- Luật mới, viết ở ĐÚNG MỘT chỗ (CTE `ton` của view này):
--   * mã có dòng ở ảnh chụp đang dùng (mart.ton_hien_tai, ≤ mốc)      → tổng như cũ;
--   * mã KHÔNG có dòng ở đó nhưng có ở một ảnh chụp TRƯỚC đó (≤ mốc)  → 0 (hết hàng);
--   * mã chưa từng có trong ảnh chụp nào ≤ mốc                        → NULL ("chưa rõ tồn") như cũ.
-- Không có ảnh chụp nào ≤ mốc thì max(...) NULL ⇒ nhánh mới rỗng ⇒ y như cũ.
-- Thân view = định nghĩa SỐNG (pg_get_viewdef sau 072, đọc mart.dim_product) — chỉ đổi CTE `ton`;
-- cùng cột, cùng thứ tự, nên CREATE OR REPLACE giữ mọi view phụ thuộc.

CREATE OR REPLACE VIEW mart.san_pham_360 AS
 WITH sl AS (
         SELECT ban_den_moc.product_code,
            sum(ban_den_moc.qty) AS so_luong_ban,
            count(DISTINCT ban_den_moc.customer_code) AS so_khach,
            count(DISTINCT ban_den_moc.sales_date) AS so_lan_mua,
            min(ban_den_moc.sales_date) AS lan_dau,
            max(ban_den_moc.sales_date) AS lan_cuoi
           FROM mart.ban_den_moc
          GROUP BY ban_den_moc.product_code
        ), moi AS (
         SELECT sl_1.product_code,
            sl_1.lan_dau > (m.hom_nay - 90) AND COALESCE(sl_1.so_lan_mua, 0::bigint) < 3 AS la_moi
           FROM sl sl_1
             CROSS JOIN mart.moc_thoi_gian m
        ), ton AS (
         SELECT ton_hien_tai.product_code,
            sum(ton_hien_tai.so_luong) AS ton
           FROM mart.ton_hien_tai
          GROUP BY ton_hien_tai.product_code
        UNION ALL
         -- 073: mã ĐÃ có trong một ảnh chụp tồn trước (≤ mốc) mà vắng ở ảnh chụp đang dùng = HẾT HÀNG
         -- (tồn 0). OBC không xuất dòng tồn 0 (đo thật: 0 dòng tồn 0 trong mọi bản 在庫一覧).
         -- `NOT IN (subquery)` chứ không `NOT EXISTS`: Postgres băm mart.ton_hien_tai MỘT lần (hashed
         -- SubPlan) thay vì dựng lại view đó cho từng mã (đo thật: 6,3 s với NOT EXISTS).
         SELECT p.product_code,
            0::numeric AS ton
           FROM ( SELECT DISTINCT i.product_code
                   FROM core.fact_inventory_daily i
                  WHERE i.snapshot_date < (SELECT max(f.snapshot_date) FROM core.fact_inventory_daily f
                                            WHERE f.snapshot_date <= COALESCE(mart.moc_lui(), 'infinity'::date))) p
          WHERE p.product_code NOT IN (SELECT t.product_code FROM mart.ton_hien_tai t WHERE t.product_code IS NOT NULL)
        )
 SELECT p.product_code,
    COALESCE(NULLIF(p.product_name, ''::text), p.product_code) AS ten_hang,
    p.kind_name AS nhom,
    ts.doanh_thu_thuan,
    ts.lai_gop,
    ts.ty_suat,
    sl.so_luong_ban,
    ton.ton,
    v.toc_do_ngay,
    v.toc_do_ngay_theo_tuoi,
        CASE
            WHEN v.toc_do_ngay_theo_tuoi > 0::numeric THEN ton.ton / v.toc_do_ngay_theo_tuoi
            ELSE NULL::numeric
        END AS du_ban_ngay,
        CASE
            WHEN ton.ton IS NULL THEN 'chua_ro_ton'::text
            WHEN ton.ton = 0::numeric AND COALESCE(v.so_luong_90n, 0::numeric) = 0::numeric THEN 'ngung'::text
            WHEN ton.ton = 0::numeric THEN 'het_hang'::text
            WHEN (v.toc_do_ngay_theo_tuoi IS NULL OR v.toc_do_ngay_theo_tuoi <= 0::numeric) AND NOT COALESCE(moi.la_moi, false) THEN 'ton_chet'::text
            WHEN v.toc_do_ngay_theo_tuoi > 0::numeric AND (ton.ton / v.toc_do_ngay_theo_tuoi) < 14::numeric AND NOT mart.la_ngung_ban(p.rank_code, p.product_name) THEN 'sap_thieu'::text
            WHEN v.toc_do_ngay_theo_tuoi > 0::numeric AND (ton.ton / v.toc_do_ngay_theo_tuoi) > 180::numeric AND NOT COALESCE(moi.la_moi, false) THEN 'ton_chet'::text
            ELSE 'du'::text
        END AS trang_thai,
    sl.so_khach,
    sl.lan_dau,
    sl.lan_cuoi,
    mart.la_ngung_ban(p.rank_code, p.product_name) AS ngung_ban
   FROM mart.dim_product p
     LEFT JOIN sl ON sl.product_code = p.product_code
     LEFT JOIN moi ON moi.product_code = p.product_code
     LEFT JOIN mart.ty_suat_mat_hang ts ON ts.product_code = p.product_code
     LEFT JOIN mart.toc_do_ban v ON v.product_code = p.product_code
     LEFT JOIN ton ON ton.product_code = p.product_code
  WHERE NOT mart.khong_phai_hang(p.product_code, p.kind_code, p.food_category_name) AND NOT (EXISTS ( SELECT 1
           FROM mart.ma_ngung_ban_an a
          WHERE a.product_code = p.product_code));
