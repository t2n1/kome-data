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
