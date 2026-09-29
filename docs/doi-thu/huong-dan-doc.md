# Hướng dẫn trích bảng giá đối thủ (phép thử độ chính xác)

Mục tiêu: chép lại THẬT ĐÚNG những gì file gốc in ra, để người đối chiếu tay đo tỉ lệ đúng.
KHÔNG bao giờ đoán một con số. Không đọc rõ → để trống + `do_chac = can_xem` + ghi lý do ở `ghi_chu`.
File nguồn CHỈ ĐỌC — không sửa, không di chuyển, không tạo file trong thư mục nguồn.

## File 1: `spike_<ma_ben>.csv` (UTF-8 có BOM, `encoding="utf-8-sig"`, dùng module csv của Python)
Mỗi dòng = một mức giá của một mặt hàng (một mặt hàng có 3 mức giá "lấy tại kho / giao / gửi" → 3 dòng).

| cột | ý nghĩa |
|---|---|
| ben | tên bên (ví dụ `NEXT`) |
| file | tên file gốc |
| vi_tri | trang/ảnh + vị trí để người dò tìm nhanh (ví dụ `tr3, hàng 2 cột trái`, `ảnh 00ecd187, ô 5`) |
| ten_goc | tên in trên file, chép nguyên văn (giữ dấu) |
| ten_nhat | tên tiếng Nhật nếu có |
| jan | mã JAN nếu có in (TEXT, giữ nguyên chữ số) |
| quy_cach_goc | quy cách chép nguyên văn (`2kg×6袋`, `Thùng 24 chai`, `500g`) |
| gia_goc | số yên in ra, số nguyên, không dấu phẩy (`13000`) |
| don_vi_gia | giá tính cho cái gì: `kg` `tui` `goi` `con` `qua` `thung` `lon` `chai` `hop` `cay` `bao` `khac` |
| kg_moi_don_vi_gia | một đơn vị giá đó nặng bao nhiêu kg, CHỈ khi file cho biết (¥650/2KG → 2; ¥/kg → 1; thùng 2kg×6 → 12; túi 100g → 0.1). Không suy được → trống |
| thue | `chua` (税抜/chưa thuế) · `co` (税込/có thuế/bao thuế) · `khong_ro` |
| gom_ship | `co` (bao ship/送料込) · `khong` (送料別/+ship/lấy tại kho) · `khong_ro` |
| kenh_gia | `tai_kho` · `giao` · `gui` · trống nếu chỉ có một giá |
| muc_gia | mức khách nếu nguồn có nhiều mức: `thuong` · `dac_biet` (Thái Dương "special") · `pallet` · `khach_ngoai` (VIETCOOK) · `kyushu` · trống nếu chỉ một mức |
| gia_bac | giá theo bậc số lượng, chép nguyên văn nếu có |
| gia_truoc_km | giá cũ bị gạch nếu là giá sale (số nguyên), trống nếu không |
| trang_thai | `con` · `het` (SOLD OUT/TẠM HẾT) · `sap_ve` ("dự kiến … xuất", "入荷予定") · `khong_ro` |
| han_su_dung | nếu có in |
| khuyen_mai | khuyến mãi gắn với RIÊNG mặt hàng này, nguyên văn |
| ma_kome | mã KOME tương đương (xem `kome_ma.csv`), trống nếu không có |
| nhan_ghep | `cung_hang` (cùng hãng/cùng mặt hàng, JAN trùng hoặc tên+quy cách rõ ràng trùng) · `thay_the` (cùng loại hàng, khác hãng/khác quy cách) · trống |
| ly_do_ghep | ngắn gọn: `JAN trùng`, `cùng tên+500g`, `cùng loại basa cắt khúc, khác quy cách`… |
| do_chac | `chac` · `can_xem` |
| ghi_chu | chỗ nào mờ, bị che (dấu SOLD OUT đè lên giá), phải suy luận… |

## File 2: `spike_<ma_ben>_dieu_kien.csv` — điều kiện CỦA BÊN (không gắn một mã)
cột: `ben, file, vi_tri, loai, noi_dung` với `loai` ∈ `ship` · `khuyen_mai` · `thanh_toan` · `thue` · `khac`.
Ví dụ: `ship` "Kiện 28kg ghép 3 sản phẩm - bao thuế bao ship"; `khuyen_mai` "tặng 1 thùng khi mua 15 thùng";
`thue` "Giá chưa gồm thuế 8%". Nguyên văn.

## Cột mới (đợt 4a, 2026-09-29)
Thêm vào `spike_<ma_ben>.csv` (đặc tả `2026-09-29-doi-thu-giao-dien-moi-design.md` §5.1–5.4). Chỉ ghi khi bảng in RÕ; không suy từ kg thùng.

| cột | ý nghĩa |
|---|---|
| so_goi_thung | số gói / thùng, số nguyên dương. Bên bán theo kg, không có thùng (OBA) → để trống |
| kl_goi_g | khối lượng TỊNH của MỘT gói, gam (≤ 30000). "2kg×6袋" → 2000. Không in → trống |
| bac | giá theo bậc số lượng ở dạng JSON (xem dưới). Chữ gốc VẪN chép vào `gia_bac` |

**`bac`** = mảng `[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]` (≤ 10 bậc, `tu` > 0, `gia` > 0).
`don_vi_sl` ∈ `thung` / `kg` / `goi` / `pallet`; `don_vi_gia` ∈ `thung` / `kg` / `goi`; cùng `thue` của dòng. Ví dụ từ tháng 8:
- NEXT "5cs: 5,300" → `[{"tu":5,"don_vi_sl":"thung","gia":5300,"don_vi_gia":"thung"}]`;
- Vietnam House "25kg: 600y/kg | 50kg: 580y/kg" → hai bậc `don_vi_sl: "kg"` (`tu` 25 và 50, `don_vi_gia: "kg"`);
- OBA "530¥/kg x 24kg; 510¥/kg x 48kg" → bậc 24 kg ¥530 và 48 kg ¥510, và `gia_goc` = 530.

Bậc theo kg / gói mà dòng thiếu quy cách (kg thùng, số gói, tịnh gói) thì mart KHÔNG áp bậc đó — nên nhớ điền `so_goi_thung` / `kl_goi_g`
khi bảng cho. Bậc `pallet` chỉ khi bảng ghi rõ pallet; đừng đổi "1 pallet" ra thùng.

**`gia_goc` = giá mua LẺ nhỏ nhất** (1 thùng / 1 đơn vị), KHÔNG phải bậc rẻ nhất. Bậc rẻ hơn đi vào `bac`.

**"Cùng hàng" (`nhan_ghep = cung_hang`) nay nghĩa là cùng THƯƠNG HIỆU.** Khác quy cách vẫn là cùng thương hiệu, vì giá đã quy về ¥/kg.
`thay_the` vẫn là cùng loại hàng khác thương hiệu.

**Không ghi câu của người đọc vào `dieu_kien`** ("chép vào…", "không in…", "Dữ liệu này…"). Câu đó là ghi chú cho người đối chiếu,
không phải điều kiện của bên: đưa vào sổ tay theo bên (`so-tay-theo-ben.md`). Nếu lỡ ghi, gói tự chuyển nó thành loại `ghi_chu_doc`
(không hiện ở tab Đối thủ / Tin) — đừng dựa vào đó.

## File 3: `spike_<ma_ben>_giao_hang.csv` — điều kiện giao hàng của bên (MỘT dòng mỗi bên)
Cột = `COT_GIAO_HANG` (`kome/loaders/doi_thu.py`) trừ `ma_dong`, cộng `ben` và `file` — gói tự suy `ma_doi_thu` từ `ben`,
`ngay_nguon` từ `file`, `nguon_file` từ `file`, nên KHÔNG ghi ba cột đó:
`ben, file, bao_ship, phi_ship, phi_ship_theo, mien_ship_tu, mien_ship_kien, thung_moi_kien, phu_phi, phi_daibiki, daibiki_tu,
daibiki_sau, ck_mien_daibiki, kien_toi_da_kg, ghep_kien, thue, cach_gui, nguon_chu`.

| cột | ý nghĩa |
|---|---|
| bao_ship | `true` nếu phí ship đã nằm trong giá hàng |
| phi_ship, phi_ship_theo | phí khi không miễn; `phi_ship_theo` ∈ `don` / `thung` / `kien` |
| mien_ship_tu / mien_ship_kien | miễn ship khi đơn ≥ ¥ / hoặc khi đủ n kiện |
| thung_moi_kien | một kiện chứa mấy thùng |
| phu_phi | JSON `{"hokkaido": 800, "okinawa": "khong_nhan"}` — ¥ mỗi kiện; vùng ∈ hokkaido, tohoku, kanto, chubu, kansai, chugoku, shikoku, kyushu, okinawa |
| phi_daibiki, daibiki_tu, daibiki_sau | phí daibiki; từ ¥`daibiki_tu` thì còn `daibiki_sau` (0 = miễn) |
| ck_mien_daibiki | `true` nếu chuyển khoản trước thì không tính phí daibiki |
| kien_toi_da_kg, ghep_kien | giới hạn kiện, cách ghép kiện |
| thue | `bao` / `chua` / `khong_ro` — giá hàng đã gồm thuế |
| cach_gui | phí gửi / cách gửi khác (宅急便, lấy tại kho, phí lạnh) khi không có số |
| nguon_chu | câu gốc, để đối chiếu |

**Không ghi = để trống, KHÔNG ghi 0** (0 nghĩa là "miễn / không tốn"; trống nghĩa là "chưa biết", màn sẽ hiện "?" và không cộng vào phí).
Ví dụ lấy từ bảng điều kiện tháng 8 (đặc tả §5.4 và bản vẽ tab Phí & giao hàng): IMAI, Vietnam House, Bùi Trâm, Ichiba — mỗi bên MỘT dòng.

## Ghép mã KOME
`kome_ma.csv` (cùng thư mục) = 168 mã KOME đang bán: product_code, product_name (tiếng Việt không dấu kèm quy cách thùng),
name_ja, food_category_name, barcode (JAN), unit, case_qty.
1. JAN trùng `barcode` → `cung_hang`, `chac`.
2. Cùng hãng/cùng mặt hàng, quy cách khớp → `cung_hang`; không chắc → `can_xem`.
3. Cùng loại hàng (basa cắt khúc vs basa cắt khúc khác hãng, riềng xay vs riềng xay) → `thay_the`.
4. Không có gì tương đương → để trống. Đừng ép ghép.

## Công cụ
- Vẽ trang PDF thành ảnh: `"C:/Program Files/Calibre2/app/bin/pdftoppm.exe" -r 110 -f N -l N -png in.pdf out` (tăng -r 200 khi cần chữ nhỏ;
  cắt vùng nhỏ bằng Pillow nếu cần phóng to). Ảnh tạm để trong một thư mục con RIÊNG của scratchpad (tên theo mã bên + phần của mình).
- PDF có lớp chữ: `pypdf` `page.extract_text()` — nhanh, số chính xác, nhưng thứ tự/ghép ô có thể sai → đối chiếu ảnh khi bố cục không rõ.
- Ảnh .jpg/.jpeg: xem bằng Read.
- File đầu ra: nếu một bên được chia cho nhiều người, tên file là `spike_<ma_ben>_<phan>.csv` / `spike_<ma_ben>_<phan>_dieu_kien.csv`
  (cột `ben` vẫn là mã bên gốc). KHÔNG ghi đè file `spike_*.csv` đã có của người khác.
- Làm HẾT phần được giao, không lấy mẫu. Trang không có giá (bìa, giới thiệu, ảnh quảng cáo) → bỏ qua, ghi 1 dòng `khac` trong dieu_kien.

## Kết thúc
Báo lại: số dòng, số dòng `can_xem`, và những khó khăn riêng của file này (ngắn gọn, 5–8 dòng).

## Sau khi nạp
Sau khi nạp: mở `/doi-thu` › Duyệt / sửa, dán link thư mục Google Drive 'Tháng N' ở đầu tab (một lần mỗi tháng).
