-- 042 — Tồn theo LÔ: lô đang xuất / lô chờ, ngày dự kiến bán hết, "không kịp bán
-- trước hạn", "sắp chuyển lô".
--
-- Chủ DN xác nhận 2026-09-25 (CLAUDE.md, Bẫy đã biết #6): công ty có MỘT kho vật
-- lý; hai "kho" của OBC là hai LÔ theo hạn sử dụng của cùng hàng:
--   0001 茨城第１倉庫（出荷専用） = lô ĐANG XUẤT,
--   1002 新・賞味期限用          = lô hạn MỚI hơn, đang chờ.
-- Lô đang xuất của một mã hết thì tồn lô chờ của mã đó được chuyển lên 0001.
-- Đo trên ảnh chụp 2026-09-24: mọi 売上出荷数量 nằm ở 0001 (1002 = 0), 40 mã có
-- ở cả hai, 0 mã chỉ có ở 1002, không mã nào có hạn ở 1002 sớm hơn 0001.
--
-- VAI TRÒ LÔ đi theo MÃ KHO, không theo hạn: "lô nào đang xuất" là sự thật vận
-- hành (hàng chỉ đi ra từ 0001), không suy từ hạn được — một lô 1002 lỡ có hạn
-- sớm hơn vẫn KHÔNG được bán trước cho tới khi chuyển lên. Mã kho viết ĐÚNG MỘT
-- LẦN, trong hàm dưới đây; đổi thì viết migration MỚI. Tên kho vẫn đọc từ
-- core.dim_warehouse (bẫy #6: không viết cứng tên).

CREATE FUNCTION mart.kho_dang_xuat() RETURNS text
LANGUAGE sql IMMUTABLE
AS $$ SELECT '0001'::text $$;

COMMENT ON FUNCTION mart.kho_dang_xuat() IS
  'Mã "kho" OBC là lô ĐANG XUẤT (0001 茨城第１倉庫（出荷専用）). Các mã kho khác là lô chờ, bán sau. Chủ DN xác nhận 2026-09-25.';

-- Thứ tự bán của các lô một mã: lô đang xuất trước, rồi các lô chờ theo hạn tăng
-- dần (lô không có ngày hạn xếp sau), cuối cùng theo mã kho cho chắc thứ tự.
--
-- Tốc độ = mart.toc_do_ban.toc_do_ngay_theo_tuoi — ĐÚNG cột đã xếp trạng thái
-- sắp thiếu / tồn chết ở mart.san_pham_360 (CLAUDE.md: mọi con số dùng để ra
-- quyết định đi theo cột này). Nên "bán hết sau" của lô CUỐI một mã BẰNG
-- san_pham_360.du_ban_ngay (có test canh). Tồn âm (OBC cho phép) tính là 0 khi
-- cộng dồn: không có hàng âm nào để bán trước lô sau.
--
-- Ngưỡng 14 ngày của `sap_chuyen_lo` là CÙNG ngưỡng 'sap_thieu' của
-- mart.san_pham_360 — cùng câu hỏi "còn đủ bán dưới hai tuần", hỏi cho một lô.
--
-- Mốc thời gian: đọc mart.ton_hien_tai (ảnh chụp ≤ mốc) và mart.toc_do_ban (đọc
-- mart.ban_den_moc) nên quay về đúng mốc khi xem lùi (040), không cần gì thêm.
CREATE VIEW mart.ton_theo_lo AS
WITH x AS (
    SELECT t.*,
           (t.warehouse_code = mart.kho_dang_xuat()) AS la_lo_xuat,
           greatest(coalesce(t.so_luong, 0), 0)      AS sl_duong,
           v.toc_do_ngay_theo_tuoi                   AS toc_do
      FROM mart.ton_hien_tai t
      LEFT JOIN mart.toc_do_ban v ON v.product_code = t.product_code
),
o AS (
    SELECT x.*,
           row_number() OVER w AS thu_tu_lo,
           coalesce(sum(sl_duong) OVER (w ROWS BETWEEN UNBOUNDED PRECEDING
                                             AND 1 PRECEDING), 0) AS ton_truoc,
           sum(sl_duong) FILTER (WHERE la_lo_xuat)     OVER (PARTITION BY product_code) AS ton_lo_xuat,
           sum(sl_duong) FILTER (WHERE NOT la_lo_xuat) OVER (PARTITION BY product_code) AS ton_lo_cho
      FROM x
    WINDOW w AS (PARTITION BY product_code
                 ORDER BY la_lo_xuat DESC,
                          CASE WHEN loai_han = 'ngay' THEN han_con_lai END ASC NULLS LAST,
                          warehouse_code)
)
SELECT product_code, warehouse_code, ten_kho, so_luong, gia_tri, best_before,
       loai_han, han_con_lai, toc_do, thu_tu_lo,
       CASE WHEN la_lo_xuat THEN 'dang_xuat' ELSE 'cho' END AS vai_tro_lo,
       ton_truoc,
       -- Lô này bắt đầu được bán sau bao nhiêu ngày (lô đang xuất: 0) và bán hết
       -- sau bao nhiêu ngày. Không có tốc độ (không bán trong 90 ngày) ⇒ NULL,
       -- không phải "vô hạn" và không phải 0.
       CASE WHEN toc_do > 0 THEN ton_truoc / toc_do END            AS bat_dau_ban_sau,
       CASE WHEN toc_do > 0 THEN (ton_truoc + sl_duong) / toc_do END AS ban_het_sau,
       -- KHÔNG KỊP BÁN TRƯỚC HẠN: lô có ngày hạn, CHƯA quá hạn (quá hạn là khối
       -- riêng), còn hàng, có tốc độ, và ngày dự kiến bán hết rơi SAU hạn. Không
       -- tốc độ ⇒ NULL ("không tính được"), để nhãn tồn chết nói phần đó.
       CASE WHEN loai_han = 'ngay' AND han_con_lai >= 0 AND sl_duong > 0 AND toc_do > 0
            THEN (ton_truoc + sl_duong) / toc_do > han_con_lai END AS khong_kip_ban,
       -- Phần dự kiến còn lại lúc hết hạn = tồn lô − phần bán được tới hạn (tới
       -- hạn bán được han_con_lai × tốc độ, trong đó ton_truoc là của lô trước).
       CASE WHEN loai_han = 'ngay' AND han_con_lai >= 0 AND sl_duong > 0 AND toc_do > 0
            THEN greatest(0, sl_duong - greatest(0, han_con_lai * toc_do - ton_truoc))
       END AS sl_khong_kip,
       CASE WHEN loai_han = 'ngay' AND han_con_lai >= 0 AND sl_duong > 0 AND toc_do > 0
            THEN round(gia_tri * greatest(0, sl_duong - greatest(0, han_con_lai * toc_do - ton_truoc))
                       / sl_duong)
       END AS gia_tri_khong_kip,
       -- SẮP CHUYỂN LÔ — thuộc tính của MÃ, ghi ở dòng thu_tu_lo = 1: lô chờ còn
       -- hàng, và lô đang xuất đã hết / không có dòng / còn đủ bán < 14 ngày.
       coalesce(ton_lo_xuat, 0) AS ton_lo_xuat,
       coalesce(ton_lo_cho, 0)  AS ton_lo_cho,
       CASE WHEN toc_do > 0 THEN coalesce(ton_lo_xuat, 0) / toc_do END AS lo_xuat_du_ban,
       (thu_tu_lo = 1 AND coalesce(ton_lo_cho, 0) > 0
        AND (coalesce(ton_lo_xuat, 0) = 0
             OR (toc_do > 0 AND ton_lo_xuat / toc_do < 14))) AS sap_chuyen_lo
  FROM o;
