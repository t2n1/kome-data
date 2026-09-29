# Sổ tay theo bên — luật đọc rút ra từ các lần đọc / sửa trước

Mỗi luật: bên · điều gì · làm gì · nguồn (tháng, ai phát hiện). Claude đọc file này TRƯỚC mỗi lần đọc.

## Nguồn web (ưu tiên hơn file)
- HSC — `app.hscstation.com` đọc Google Sheet công khai (link trong `data.js`). Giá `priceJPY` là giá CẢ `spec`
  (thường là thùng), ĐÃ gồm thuế. `priceJPY` 0 hoặc < 50 = lỗi của web → `can_xem`. Bậc giá / giá Kyushu nằm ở `description`.
- THAI-DUONG — `tdmvn.shop`, API `https://api.tdmvn.shop/sync-products?revision=0`. Bỏ `deleted: true`.
  Hai mức: `branches.main` (`muc_gia=thuong`), `branches.special` (`muc_gia=dac_biet`, ~0,91× main, "mix từ 3th").
  Trường `sale` là bậc giá theo số thùng → `gia_bac`, không phải khuyến mãi.
- JVB — `jvbfood.asia` WooCommerce, trang danh sách công khai (Store API trả 404 → đọc trang).
- THAK — `thak.jp` WooCommerce Store API `/wp-json/wc/store/v1/products?per_page=100&page=N` (385 mã 2026-09-29).
  `prices.price` có `currency_minor_unit=1` ("80400" = ¥8.040) và là giá CẢ đơn vị bán (thùng / kiện).
  Giá đơn vị lấy từ `short_description` ("335 yên/dây"), KIỂM CHÉO bằng giá ÷ số đơn vị — giá trong TÊN đôi khi cũ.
  Giá web = giá ĐÃ gồm thuế (khớp đúng 税込 của PDF). File "25-06-THAK-THAI-LAN" có thể là bảng giá cũ.

## File
- NEXT — mỗi mã 3 giá: `tai_kho` / `giao` / `gui` (+送料別). "8月 (値段:税抜)" = chưa thuế. Ảnh có thể gửi TRÙNG trang (tháng 8: 2ef88dbb = trang 19).
- IMAI — mỗi bảng in cả cột 税抜 và 税込 → một dòng chưa thuế, giá có thuế vào `ghi_chu` (script gộp tự làm).
- ICHIBA — in "Barona 110g x 80" cho mọi sốt ¥95, thật là 80g (KOME BA*).
- MUNDIAL — giá "y" = yên, "chưa bao gồm thuế 8%" ở đầu file; ô gộp nhiều mã; ô "0y" / trống = không có giá.
- NICHIETSU — dấu TẠM HẾT đóng trên ẢNH sản phẩm, không trên dòng bảng.
- DAIICHI — "Khối lượng 1kg" + giá = ¥/kg; STT đánh lại theo từng mục; ảnh chụp màn hình chồng nhau.
- VIETCOOK — ba mức: xanh "Giá tại kho" (`kenh_gia=tai_kho`), cam "khách Vietcook = Pallet" (`muc_gia=pallet`), xanh lá "khách ngoài" (`muc_gia=khach_ngoai`).
- BOMPEX — có JAN; tem "Dự kiến tháng 9 / 19/8 xuất hàng" = `sap_ve`.
- YUMI — footer "Kiện 28kg ghép 3 (hoặc 4) sản phẩm - bao thuế bao ship".

## Luật đợt 4a (tháng 8, 2026-09-29) — quy cách gói, bậc, giao hàng
- NEXT — bậc "5cs / 2cs" in cạnh giá → `bac` (`don_vi_sl: thung`). Kênh `tai_kho` / `gui` / `giao` là ba dòng. Phí gửi
  "…円/cs + 冷蔵送料" không có số trọn → để trống số, ghi chữ vào `cach_gui`; `phi_ship` NULL.
- Vietnam House — bậc theo kg (25 / 50 kg) → `bac` `don_vi_sl: kg`; `gia_goc` PHẢI là mức 25 kg (giá lẻ nhỏ nhất, không phải
  mức 50 kg). Giao hàng: Hokkaido +¥1,200, Okinawa không nhận (`"khong_nhan"`); daibiki ¥330 (chuyển khoản trước không tính).
- OBA — bậc "×24kg / ×48kg" → bậc 24 kg ¥530, 48 kg ¥510; `gia_goc` 530. Bán theo kg, không có thùng → `so_goi_thung` để trống.
- ICHIBA — "Kiện 2 thùng Mix ok" → `thung_moi_kien` 2, `mien_ship_kien` 1, `thue = bao` (bao thuế).
- IMAI — ¥605 mỗi thùng khi đơn dưới ¥20,000 (`phi_ship_theo = thung`, `mien_ship_tu` 20000); Tohoku ¥400, Hokkaido ¥800; daibiki ¥440.
- BOMPEX — miễn ship và miễn daibiki từ ¥20,000; Okinawa có phụ thu nhưng số không ghi → để trống, KHÔNG ghi 0.
- EIHATSU — vài mặt hàng in hai giá "Daibiki / CK" → hai dòng, `kenh_gia` khác nhau (giá daibiki vs giá chuyển khoản).
- Chung — câu của người đọc (ví dụ "chép giá có thuế vào ghi_chu", "không in thông tin thuế") viết Ở ĐÂY, không vào `dieu_kien`.
