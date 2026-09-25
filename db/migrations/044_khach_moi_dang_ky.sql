-- 044 — Khách mới đăng ký: ngày đăng ký đọc từ MÃ KHÁCH.
--
-- Mã khách OBC tạo từ 2023-08 có dạng YYYYMMDD + 4 số thứ tự
-- (`202607150003` = khách thứ 3 đăng ký ngày 15/7/2026). Đo thật 2026-09-26
-- trên core.dim_customer (is_current): 1.266 mã dạng này, 2023-08-01 →
-- 2026-09-25; ngày trong mã trùng ngày mua đầu ở trung vị (lệch 0 ngày).
-- Phần còn lại KHÔNG có ngày: 835 mã cũ `000000xxxxxx`, 855 mã ngắn (`0`…`9996`,
-- không dòng bán nào), 26 mã `009…`/`999…` (tài khoản nhân viên) — chúng
-- KHÔNG BAO GIỜ là "khách mới"; đoán ngày cho chúng là bịa số.
--
-- KHÁC nhóm 'moi' của mart.khach_nhom_viec (020): nhóm đó là "đơn ĐẦU trong 90
-- ngày mà đã im quá 1,2× nhịp" — một danh sách gọi lại, đọc theo ngày mua.
-- Ở đây là ngày ĐĂNG KÝ, gồm cả khách chưa mua lần nào.

-- Hàm DUY NHẤT đọc ngày từ mã. plpgsql chứ không phải sql: hàm sql IMMUTABLE bị
-- gộp vào câu gọi và Postgres gập hằng lúc lập kế hoạch, nên với một mã hằng
-- không khớp mẫu (`'0'`) nó vẫn có thể tính `substr(...)::int` và nổ — CASE
-- không che được biểu thức hằng. Ngày không có thật (29/2/2025, 31/4) -> NULL,
-- không bao giờ ném lỗi: một mã lạ không được làm trắng trang.
CREATE FUNCTION mart.ngay_dang_ky(ma text) RETURNS date
LANGUAGE plpgsql IMMUTABLE STRICT
AS $$
DECLARE
    dau date;
    ngay int;
BEGIN
    IF ma !~ '^20[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])[0-9]{4}$' THEN
        RETURN NULL;
    END IF;
    dau := make_date(substr(ma, 1, 4)::int, substr(ma, 5, 2)::int, 1);
    ngay := substr(ma, 7, 2)::int;
    IF ngay > extract(day FROM dau + interval '1 month' - interval '1 day') THEN
        RETURN NULL;
    END IF;
    RETURN dau + (ngay - 1);
END
$$;

COMMENT ON FUNCTION mart.ngay_dang_ky(text) IS
  'Ngày đăng ký đọc từ mã khách YYYYMMDD+4 số; NULL = mã không mang ngày (mã cũ, mã ngắn).';


-- Khách ĐĂNG KÝ trong [tu, den] — đọc đơn đầu / doanh thu qua mart.lan_mua
-- (← mart.ban_den_moc), nên khi mốc lùi về một tháng cũ thì "chưa mua" là chưa
-- mua TÍNH ĐẾN mốc đó (bất biến 040). Đăng ký sau mốc cũng không lọt vào: người
-- gọi truyền `den` = ngày cuối khoảng xem = mốc.
-- da_mua = có ít nhất một phiếu ≤ mốc (kể cả phiếu đỏ — "đã giao dịch").
-- doanh_thu = doanh thu thuần tới mốc (赤伝 không lọc bỏ).
CREATE FUNCTION mart.khach_moi_khoang(tu date, den date)
RETURNS TABLE (customer_code text, ten text, salesperson_code text, ngay_dang_ky date,
               lan_dau date, so_ngay_mua bigint, doanh_thu numeric, da_mua boolean,
               da_ngung boolean)
LANGUAGE sql STABLE
AS $$
    WITH k AS (
        SELECT c.customer_code, c.customer_name, c.salesperson_code,
               mart.ngay_dang_ky(c.customer_code) AS ngay_dk
        FROM core.dim_customer c
        WHERE c.is_current
    ), m AS (
        SELECT l.customer_code, min(l.sales_date) AS lan_dau,
               count(DISTINCT l.sales_date) AS so_ngay, sum(l.doanh_thu_thuan) AS dt
        FROM mart.lan_mua l
        WHERE l.customer_code IN (SELECT customer_code FROM k WHERE ngay_dk BETWEEN tu AND den)
        GROUP BY l.customer_code
    )
    SELECT k.customer_code, coalesce(nullif(k.customer_name, ''), '(chưa có tên)'),
           k.salesperson_code, k.ngay_dk, m.lan_dau, coalesce(m.so_ngay, 0),
           coalesce(m.dt, 0)::numeric, m.lan_dau IS NOT NULL,
           coalesce(h.da_ngung, false)
    FROM k
    LEFT JOIN m USING (customer_code)
    LEFT JOIN mart.dau_hieu_khach h USING (customer_code)
    WHERE k.ngay_dk BETWEEN tu AND den
$$;

COMMENT ON FUNCTION mart.khach_moi_khoang(date, date) IS
  'Khách có ngày đăng ký (mart.ngay_dang_ky) trong [tu, den]; đơn đầu / doanh thu tính tới mốc.';
