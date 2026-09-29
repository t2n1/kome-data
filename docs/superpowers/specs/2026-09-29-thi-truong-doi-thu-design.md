# Thị trường & đối thủ (`/doi-thu`) — đặc tả thiết kế

Ngày: 2026-09-29 · Người yêu cầu: chủ DN · Trạng thái: **chờ duyệt** (các quyết định §2 đã chốt trong trò chuyện)

## 0. Đảo một quyết định cũ

Lộ trình 24 màn (`2026-09-21-lo-trinh-24-man-hinh-design.md` dòng 87, 105) và đặc tả nền
(`2026-09-16-kome-data-platform-design.md` dòng 191, 197) đã CẮT "Thị trường & đối thủ", gộp vào
CRM với lý do "chỉ là vài bảng nhập tay". Phép thử tháng 8 (§3) cho thấy lý do đó không còn đúng:
19 bên, 93 file, **4.068 dòng giá** một tháng — không phải vài bảng nhập tay. Đặc tả này **đảo**
quyết định đó; chú thích đầu `giao_dien/src/khung/muc.ts` phải sửa theo.

## 1. Mục đích

Một chỗ để **nhìn chung thị trường** và **so KOME với đối thủ**: quy cách, giá, khuyến mãi, điều
kiện ship, hết hàng — của 19 bên đang theo dõi. Ba nguồn:

1. **Bảng giá / web của đối thủ** — sale gom mỗi tháng vào `Bang-gia-doi-thu\Tháng N\<bên>\`,
   Claude đọc trong một phiên làm việc (không có AI chạy trên web), xuất một **gói chuẩn** nạp qua
   `/kho-du-lieu/nap`.
2. **Sale sửa / cập nhật** ngay trên web (`/doi-thu`, tab Duyệt).
3. **Tin hiện trường** — sale gõ `@đối thủ` `@hàng` trong ô ghi tiếp xúc khách.

## 2. Quyết định đã chốt

| Câu hỏi | Chốt |
|---|---|
| Nơi đặt | **Trong web KOME** (Hướng 1) — nối được với giá / doanh số / khách thật |
| AI đọc file ở đâu | **Chỉ trong phiên làm việc với Claude** (B). Web không gọi API AI nào |
| "Hàng tương đương" | **Hai nhãn**: `cung_hang` (cùng hãng + quy cách) · `thay_the` (cùng loại, khác hãng/quy cách). Mặc định so `cung_hang`; bật thêm `thay_the` |
| Trục so sánh | **Nhóm so sánh** (ví dụ "Riềng xay đông lạnh") — mã KOME và hàng đối thủ cùng gắn vào. 80% hàng cạnh tranh là `thay_the`, nên mã KOME không đủ làm trục |
| Giá KOME để so | **Đơn giá thực 90 ngày** quy về ¥/kg (Σ doanh thu thuần ÷ Σ kg đã bán) |
| Ai sửa được | **Mọi người đã đăng nhập** (A). Nhật ký ghi ai sửa; bản gốc không bao giờ mất |
| Sửa giá = hai việc | **Sửa lỗi đọc** (nguồn vẫn là file cũ) ≠ **Cập nhật giá mới** (quan sát mới, nguồn mới bắt buộc) |
| Loại nguồn | 5 loại, **sửa được không cần code**: bảng giá/web · chứng từ khách đưa · tờ rơi/tin nhắn đối thủ · khách kể · nghe nói/khác |
| Giá khách kể trong `@` | **Ô tuỳ chọn ngay sau thẻ hàng** (1A). Máy KHÔNG tự đọc số trong câu |
| Web đối thủ | **Ưu tiên web khi có** (HSC, Thái Dương, JVB, THAK) — chính xác và mới hơn file |

## 3. Bằng chứng từ phép thử tháng 8 (2026-09-29)

Đọc hết 19 bên → `phep_thu_bang_gia_doi_thu_thang8.xlsx` (thư mục tạm của phiên, không vào git).

| Nguồn | Bên | Dòng |
|---|---|---|
| Web / dữ liệu có cấu trúc | HSC (Google Sheet công khai), Thái Dương (API), JVB (WooCommerce) | 940 |
| PDF có lớp chữ | BOMPEX, EIHATSU, ICHIBA, IMAI, THAK | 1.370 |
| Ảnh / PDF toàn ảnh | NEXT, VIETCOOK, VIETNAM HOUSE, YUMI, DAIICHI, Nichietsu, BUI TRAM, OBA | 1.487 |
| Tin nhắn / docx | MT-ONE, MUNDIAL, ASIA TRADING | 311 |

Những điều thiết kế phải chịu được (mỗi điều có ví dụ thật):
- **Đơn vị giá hỗn loạn**: ¥/kg · túi · gói · con · quả · 2kg · thùng · lon · khay · chiếc.
  Giá thùng và giá lẻ lẫn nhau (web THAK: ¥8.040 = thùng 24 dây, 335¥/dây nằm trong TÊN).
- **Nền giá khác nhau**: có/chưa thuế, gồm/chưa ship, và **3 kênh** (NEXT: lấy tại kho / giao /
  gửi +送料別) và **mức khách** (Thái Dương main/special; VIETCOOK tại kho/khách pallet/khách ngoài;
  HSC giá chung/Kyushu). Phần lớn dòng `thue`/`gom_ship` = không rõ.
- **Lỗi nằm ở chính file đối thủ** hơn là ở khâu đọc: HSC 82 mã giá ¥0–49 trên web; Mundial
  "0y", "690y, 725y" một ô; DAIICHI mít đỏ ¥180/kg cạnh mít ¥720/kg; ICHIBA in Barona "110g"
  (thật 80g); BOMPEX hai mã chung một JAN.
- **Trạng thái có 4 giá trị**: còn · hết (SOLD OUT/TẠM HẾT) · **sắp về** ("dự kiến 19/8 xuất",
  "dd/08入荷予定") · không rõ.
- **JAN chỉ giúp một phần**: mã `893…` của nhà sản xuất VN trùng được (BOMPEX 6, IMAI 35 dòng);
  mã `458…` đối thủ tự đăng ký thì không bao giờ trùng.
- **Độ phủ**: 138/168 mã KOME đang bán có đối thủ; hàng đông lạnh 11–14/19 bên cùng bán.
- **Độ chính xác đọc**: tự dò 57/57 dòng khớp trên hai trang dễ; tỉ lệ thật chờ sale dò. Khoảng
  10% dòng AI tự báo "cần xem".

## 4. Dữ liệu

Ranh giới schema theo đúng vai trò hiện có (009): **`core` = thứ NẠP qua cổng** (vai trò
`kome_ingest`, có `batch_id`, hoàn tác theo lô), **`app` = thứ WEB GHI** (vai trò `kome_app`),
**`mart` = định nghĩa chỉ số**. Không tạo schema mới: không có tiền lệ sau `001`, và một schema mới
phải tự cấp quyền + default privileges + thêm vào `tests/conftest.py::SCHEMAS`.
Đối thủ KHÔNG phải OBC, nhưng `core` là "dữ liệu nguồn đã qua cổng" — luật "không UPDATE `core`"
áp nguyên: sửa của sale nằm ở `app`, không bao giờ ghi đè dòng đã nạp.

### 4.1 Nạp (`core`, có `batch_id`, hoàn tác theo lô)

**`core.fact_gia_doi_thu`** — mỗi dòng = một mức giá của một mặt hàng trong một nguồn.
Cột = đúng mẫu cột của phép thử (`HUONG_DAN.md`) cộng:
`ma_doi_thu` (TEXT, khoá tới `app.doi_thu.ma`) · `ma_hang_dt` (khoá ổn định của hàng đối thủ qua các
tháng — xem 4.3) · `ngay_nguon` (ngày của bảng giá / ngày tải web) · `loai_nguon` (`bang_gia`/`web`) ·
`muc_gia` (TEXT tự do có chuẩn hoá: `thuong`, `dac_biet`, `pallet`, `khach_ngoai`, `kyushu`…) ·
`trang_thai` ∈ `con`/`het`/`sap_ve`/`khong_ro` · `nguon_file`, `vi_tri` (để dò lại) ·
`ma_kome_de_xuat`, `nhan_de_xuat`, `do_chac`, `ly_do_ghep` (đề xuất của AI — ghép hiện hành ở §4.2) ·
`id bigserial` (khoá mà đính chính trỏ vào; KHÔNG có khoá ngoại từ `app` sang, để hoàn tác lô xoá được —
đính chính mồ côi thì `mart` bỏ qua).
Giá lưu **nguyên văn** (`gia_goc`, `don_vi_gia`, `kg_moi_don_vi_gia`, `thue`, `gom_ship`) — quy đổi
làm ở `mart`, không ở bộ nạp.

**`core.fact_dieu_kien_doi_thu`** — điều kiện CỦA BÊN: `ma_doi_thu, loai (ship/khuyen_mai/
thanh_toan/thue/khac), noi_dung, ngay_nguon, nguon_file, vi_tri`.

**Gói chuẩn** = MỘT file `.xlsx` mỗi lần đọc (bộ đọc hiện chỉ nhận Excel — `kome/reader.py:58-78`),
tên `bang_gia_doi_thu_YYYY-MM-DD.xlsx`, hai sheet `gia` và `dieu_kien`, header dòng 1. Khai trong
`config/files.yml` như mọi file (`min_rows`, `keys`, `code_columns` gồm `jan` và `ma_hang_dt` —
bẫy #1: mã là TEXT). Một lô = một lần đọc (thường cả tháng, hoặc một bên cập nhật giữa tháng).

Đăng ký bộ nạp theo đúng danh mục test canh: `LOADERS` + `UNDO_TABLES` (hai bảng trên),
`nhat_ky_nap.BANG_THEO_LOAI`, `TEN_BANG_VI`, một ô `O_NAP` ("Bảng giá đối thủ", nhịp `ky`),
`coverage.COT` (một cột trên lưới độ phủ, theo tháng), chạy lại `scripts/sinh_cot_dung.py` và
`scripts/sinh_tai_lieu.py`. KHÔNG vào `tuoi_du_lieu.NGUON_HANG_NGAY` (không phải file 13:30).

Cổng: 1–3 như mọi file. Cổng 4 TẮT nhánh số dòng (`warn_row_drop_ratio: 0`): tháng này 19 bên,
tháng sau 5 bên cập nhật thì số dòng "sụt 70%" là bình thường. Các kiểm riêng của nguồn này (giá
≤ 0 hoặc < 20, JAN hỏng chữ số kiểm, JAN trùng hai mã cùng bên) chạy trong `scripts/goi_doi_thu.py`
lúc DỰNG gói — dòng dính thì mang `do_chac = can_xem` + lý do, không chặn cả gói.

Hai loại file, MỘT ô nạp ("Bảng giá đối thủ", `specs: [doi_thu_gia, doi_thu_dieu_kien]`):
`doi_thu_gia_YYYYMMDD.xlsx` và `doi_thu_dieu_kien_YYYYMMDD.xlsx` (bộ đọc đọc MỘT sheet mỗi file).
Hai lô, hoàn tác riêng. Nạp lại cùng tháng: lô mới hơn thắng ở `mart` (tie-break `batch_id`),
lô cũ không bị xoá — cùng nếp `mart.so_cong_no_moi_nhat`.
`gia_goc`, `kg_moi_don_vi_gia` KHÔNG khai `money_columns` (bộ đọc ép ô trống thành 0; ở đây trống ≠ 0,
và có giá lẻ .5 yên) — bộ nạp tự đổi sang `numeric`, trống → NULL.

### 4.2 Web ghi (`app`)

| Bảng | Nội dung | Ghi |
|---|---|---|
| `app.doi_thu` | `ma` (TEXT, ví dụ `THAK`), tên hiển thị, web, ghi chú, `dang_theo_doi` | sửa được |
| `app.loai_nguon` | `ma`, tên, `thu_tu` (độ tin cậy, 1 = cao nhất), `can_bang_chung` (gợi ý đính kèm) | sửa được; 5 dòng khởi tạo |
| `app.nhom_so_sanh` | `id`, tên ("Basa cắt khúc") | sửa được |
| `app.nhom_so_sanh_ma` | `product_code` (duy nhất) → `nhom_id`: mã KOME thuộc nhóm có tên | sửa được |
| `app.ghep_hang` | (`ma_doi_thu`, `ma_hang_dt`) → `product_code` NULL được, `nhom_id` NULL được, `nhan` (`cung_hang`/`thay_the`/`khong`), `nguoi_dung_id`, `luc` | ghi đè (ghép hiện hành) |
| `app.doi_thu_nhat_ky` | MỌI thao tác ghi của màn này: `loai`, `doi_tuong`, `truoc`, `sau`, `nguoi_dung_id`, `luc` — ghi trong CÙNG giao dịch | **chỉ thêm**; MỘT sổ cho `_PHIEN_BAN` và `/nhat-ky` (nếp `ngan_sach_nhat_ky`) |
| `app.dinh_chinh_gia` | sửa lỗi đọc: `fact_id` (dòng đã nạp), `truong`, `gia_tri_moi`, `nguoi_dung_id`, `luc`; `truong = 'xac_nhan'` = "đúng rồi" | **chỉ thêm** (`REVOKE UPDATE, DELETE` khỏi `kome_app`) |
| `app.gia_doi_thu_tay` | cập nhật giá mới / thêm tay: cùng cột giá như `fact_gia_doi_thu` + `loai_nguon` (bắt buộc) + `ghi_chu_nguon` + `customer_code` NULL được + `tiep_xuc_id` NULL được + `nguoi_dung_id`, `luc` | **chỉ thêm** |
| `app.tiep_xuc_nhac` | thẻ `@` của một dòng `app.nhat_ky_tiep_xuc`: `tiep_xuc_id`, `loai` (`doi_thu`/`nhom`/`ma_kome`), khoá tương ứng, `vi_tri_dau`, `do_dai` (vị trí trong câu) | **chỉ thêm** |
| `app.quy_cach_kome` | `product_code` → `kg_moi_goi`, `goi_moi_thung` — CHỈ phần người sửa; mặc định tách từ `product_name` ("(500g x 20 packs)") ở `mart.quy_cach_kome` | sửa được |

`nguoi_dung_id` luôn **NULL được** (cổng đăng nhập có thể tắt ở máy công ty).
`_PHIEN_BAN` thêm `max(id)` của `app.doi_thu_nhat_ky`, `app.dinh_chinh_gia`, `app.gia_doi_thu_tay`;
màn nào đọc chúng KHÔNG dùng `chi_nap=True`.

**Nhóm của một quan sát** = `ghep_hang.nhom_id` nếu có; không thì nhóm có tên chứa mã KOME đã ghép
(`nhom_so_sanh_ma`); không thì **nhóm ngầm định theo đúng mã KOME** (khoá `ma:<mã>`, tên = tên hàng
KOME). Nên chưa ai tạo nhóm nào thì So sánh vẫn chạy ngay; tạo nhóm có tên chỉ để GỘP nhiều mã KOME.
**Ghép hiện hành** = `app.ghep_hang` nếu có, không thì đề xuất của AI trong dòng nạp mới nhất
(`ma_kome_de_xuat`, `nhan_de_xuat`).

### 4.3 Khoá hàng đối thủ qua các tháng (`ma_hang_dt`)

Để cặp ghép của tháng trước tự áp cho tháng sau. Thứ tự ưu tiên, sinh lúc xuất gói:
1. **JAN** hợp lệ (13 số, đúng chữ số kiểm, không trùng hai mã trong cùng bên);
2. **mã của đối thủ** nếu nguồn có (HSC `id`, Thái Dương `_id`, THAK/JVB WooCommerce `id`,
   EIHATSU 商品コード, MUNDIAL mã SP);
3. **tên chuẩn hoá + quy cách** (bỏ dấu, thường hoá, gộp khoảng trắng; "500gr"→"500g").
Đổi (3) sang (1)/(2) khi nguồn bắt đầu có mã → `app.ghep_hang` giữ bản đồ cũ → mới (một dòng nhật ký).

### 4.4 Chỉ số (`mart`)

- **`mart.gia_doi_thu_hien_hanh`** — mọi quan sát sau khi áp đính chính: dòng nạp + `dinh_chinh_gia`
  (giá trị mới nhất của từng trường) ∪ `gia_doi_thu_tay`. Cột thêm:
  - `trang_thai_duyet` ∈ `ai_doc` · `can_xem` · `da_xac_nhan` · `da_sua` · `nhap_tay`;
  - `yen_chuan` = giá quy về **¥/kg chưa thuế** (`gia_goc ÷ kg_moi_don_vi_gia`, ÷ 1,08 khi `thue='co'`);
    đơn vị không quy được kg → ¥/đơn vị với `don_vi_so = 'don_vi'`;
  - `nen_gia` = nhãn ghép `thue` + `gom_ship` + `kenh` + `muc_gia` — MỌI con số so sánh in kèm nhãn này;
  - `hien_hanh` = quan sát mới nhất của (bên, `ma_hang_dt`, kênh, mức) — cũ hơn là lịch sử;
  - `tuoi_ngay` = mốc − `ngay_nguon`.
  Quay về theo mốc (`mart.moc_lui()`, bất biến 040): chỉ thấy quan sát có `ngay_nguon` ≤ mốc.
- **`mart.gia_kome_kg(p_ma)`** — đơn giá thực 90 ngày của KOME quy về ¥/kg: Σ(amount − tax_amount) ÷
  Σ(qty × kg theo `pack_code` từ `app.quy_cach_kome`), đọc `mart.ban_den_moc` (bỏ mã nội bộ, quay về
  mốc). Tỷ số của các TỔNG (bất biến tỷ suất). Không có quy cách → NULL, không đoán.
- **`mart.so_sanh_nhom`** — mỗi nhóm: giá KOME, số bên, thấp nhất / trung vị / cao nhất của đối thủ
  (chỉ quan sát `hien_hanh`, `con`, cùng `don_vi_so`), vị trí của KOME (phân vị), số quan sát
  "khách kể" tách riêng (KHÔNG trộn vào trung vị bảng giá).
- **Bắt giá bất thường** (MỘT định nghĩa, `mart.la_gia_bat_thuong`): quan sát lệch > 2× hoặc < 0,5×
  trung vị của nhóm, khi nhóm có ≥ 3 bên. Quan sát bất thường → `can_xem`, không vào trung vị.
  Không phải lỗi thì người duyệt bấm "đúng rồi" → ra khỏi diện bất thường.
- **Ưu tiên nguồn** khi cùng (bên, hàng) có nhiều quan sát cùng ngày: `app.loai_nguon.thu_tu` nhỏ hơn thắng.

## 5. Màn hình

`/doi-thu` (React, `giao_dien/src/doi_thu/`), NGOÀI `DUONG_KHO_DU_LIEU` (mọi người đăng nhập vào
được); thanh bên nhóm "Khách hàng & thị trường", icon chọn trong bộ 24 của gói thiết kế và GHI RÕ
là ta chọn (bất biến 4d). Theo khoảng xem: mốc = cuối khoảng (xem lùi tháng 8 là thấy thị trường
tháng 8). Định dạng số chuẩn Nhật (`dinh_dang.ts`).

### 5.1 Tab Tổng quan thị trường
- **Lưới đối thủ × ngành**: ô = số mã đối thủ bán trong ngành đó; bấm → tab So sánh lọc ngành + bên.
- **Khuyến mãi đang chạy** (từ `khuyen_mai`, `gia_truoc_km`, điều kiện `khuyen_mai`) theo bên.
- **Điều kiện của 19 bên**: ship · đơn tối thiểu · kiện · thanh toán · thuế — một bảng đọc ngang.
- **Đối thủ đang hết / sắp về** hàng thuộc nhóm KOME có bán → cơ hội chào hàng (bấm → danh sách khách
  mua đều mã đó, `mart.khach_mat_hang`).
- **Độ tươi dữ liệu**: mỗi bên — ngày nguồn mới nhất, nguồn (web/file), số dòng chờ duyệt.
- (Đợt 2) **Hiện trường 30 ngày**: đối thủ / nhóm được nhắc nhiều nhất, lưới 47 tỉnh.

### 5.2 Tab So sánh giá
Mỗi nhóm một dòng: giá KOME ¥/kg · thấp nhất (bên) · trung vị · cao nhất · vị trí KOME · số bên ·
(Đợt 2) giá khách kể. Bấm dòng → từng quan sát (bên, giá gốc nguyên văn, nền giá, nguồn, ngày, trạng
thái duyệt). Lọc: ngành · chỉ `cung_hang` · chỉ đã xác nhận · kênh/mức · bỏ quan sát cũ hơn N ngày.
Ô nổi của mọi con số: nguồn + nền giá + ngày.

### 5.3 Tab Hồ sơ đối thủ
Mạnh ở ngành nào (số mã, số nhóm trùng KOME) · điều kiện · lịch sử giá từng hàng qua các tháng ·
nguồn (web/file, ngày) · (Đợt 2) khách đang mua của bên này.

### 5.4 Tab Duyệt / sửa
- Danh sách quan sát, lọc: bên · tháng · `can_xem` · bất thường · chưa ai xác nhận · chưa ghép.
- Chọn một dòng → khung sửa: giá, đơn vị, kg, quy cách, thuế, ship, kênh, mức, trạng thái, ghép
  (nhóm + mã KOME + nhãn). Nút:
  - **Đúng rồi** → `dinh_chinh_gia(truong='xac_nhan')`;
  - **Lưu sửa** (sửa lỗi đọc) → một dòng `dinh_chinh_gia` mỗi trường đổi;
  - **Giá đã đổi** (cập nhật giá mới) → `gia_doi_thu_tay` với **loại nguồn bắt buộc** + ghi chú nguồn;
  - **Thêm hàng AI bỏ sót** → `gia_doi_thu_tay`.
- Ghép sửa ở đây áp cho MỌI tháng của cặp (bên, `ma_hang_dt`).
- Đợt 1 hiện `nguon_file` + `vi_tri` (chữ). Ảnh trang gốc cạnh dòng là Đợt 3 (§8).

### 5.5 Khối trên màn khác
- `/san-pham/{mã}` cột trái: "Đối thủ bán nhóm này: thấp nhất ¥…/kg (bên X) · trung vị ¥… · KOME ¥…"
  → liên kết `/doi-thu?tab=so_sanh&nhom=`. Một lượt hỏi thêm, ngoài trần 5 của hồ sơ (endpoint riêng).
- (Đợt 2) hồ sơ khách 360, `/lien-he` — §6.

## 6. Tin hiện trường bằng `@` (Đợt 2)

- **Nhập**: `giao_dien/src/khach/GhiTiepXuc.tsx` (dùng chung ở `HoSoViec.tsx`, `HoSoTab.tsx`,
  `LienHe.tsx`). Gõ `@` → gợi ý đối thủ (`app.doi_thu`); `@` tiếp → gợi ý nhóm so sánh + mã KOME.
  Chọn xong = thẻ. Ngay sau thẻ hàng hiện **ô tuỳ chọn** "giá ___ ¥ / kg·gói·thùng".
- **Lưu**: `noi_dung` VẪN là chữ thường như gõ (`@THAK`, không đánh dấu đặc biệt) — nhật ký, CSV,
  `/nhat-ky` không đổi. Thẻ vào `app.tiep_xuc_nhac` (vị trí trong câu); giá vào `app.gia_doi_thu_tay`
  với `loai_nguon = 'khach_ke'`, `customer_code`, `tiep_xuc_id`. `kome/lien_he.py::ghi` thêm
  `RETURNING id`; ghi dòng tiếp xúc + thẻ + giá trong MỘT giao dịch. CHECK / chỉ-thêm của
  `nhat_ky_tiep_xuc` (030) không đổi.
- **Xử lý**: giá khách kể qua cùng quy đổi + bắt bất thường (nghi nhầm đơn vị → báo lại ngay cho người
  ghi); tin trùng (khách, bên, nhóm) → mới nhất là hiện trạng; mặc định chỉ tính 90 ngày.
- **Nối**: hồ sơ khách — nhãn "đang mua @THAK: Basa" (trong 90 ngày); nếu khách có cặp
  `trang_thai_cap = 'ngung'` (bất biến 024) với mã cùng nhóm → hiện ngay lý do ngừng mua. Hồ sơ đối
  thủ — "khách đang mua của bên này". So sánh — cột giá khách kể. Tổng quan — hiện trường 30 ngày.
- **Hằng tháng (Claude)**: đọc ghi chú chữ tự do, đề xuất gắn thẻ bị quên → danh sách chờ duyệt
  (bấm đồng ý mới thêm `tiep_xuc_nhac`; câu gốc không bao giờ sửa).

## 7. Quy trình hằng tháng (trong phiên với Claude)

1. Sale thả file vào `Bang-gia-doi-thu\Tháng N\<bên>\`.
2. Claude: bên có web công khai → lấy từ web (chỉ đọc, không đăng nhập); còn lại đọc file. Áp **sổ tay
   theo bên** (`docs/doi-thu/so-tay-theo-ben.md`, trong git — luật rút ra từ lần sửa trước, ví dụ
   "ICHIBA in Barona 110g, thật 80g") và **cặp ghép đã xác nhận** (đọc `app.ghep_hang`, chỉ đọc).
3. `scripts/goi_doi_thu.py` gộp kết quả thành gói `.xlsx` chuẩn (sinh `ma_hang_dt`, kiểm cột,
   lọc trang trùng, gộp cặp chưa thuế/có thuế).
4. Nạp qua `/kho-du-lieu/nap` (người có cờ `duoc_vao_kho_du_lieu`); sale duyệt ở `/doi-thu`.
5. Lần đọc sau: Claude đọc `app.dinh_chinh_gia` của các lô trước → cập nhật sổ tay theo bên; báo
   **tỉ lệ sửa theo bên** (đây là phép đo độ chính xác liên tục).

Hướng dẫn đọc (`HUONG_DAN.md` của phép thử) chuyển vào `docs/doi-thu/huong-dan-doc.md`.

## 8. Chia đợt

| Đợt | Gồm | Ghi chú |
|---|---|---|
| **1** | §4 toàn bộ bảng trừ `tiep_xuc_nhac` · bộ nạp + gói · `/doi-thu` bốn tab · khối Sản phẩm 360 · nạp tháng 8 thật | Lõi. Làm được ngay |
| **2** | §6 tin hiện trường `@` · nối hồ sơ khách / `/lien-he` / hồ sơ đối thủ · hiện trường 30 ngày | Sau khi Đợt 1 có dữ liệu thật |
| **3** | Ảnh: trang gốc cạnh dòng duyệt + ảnh bằng chứng sale đính kèm (nguồn loại 2, 3) | **Cần chọn chỗ lưu ảnh** — web hiện không có (chỉ `meta.nap_cho` bytea, 24 giờ). Mỗi tháng ~400 trang; Vercel 4,5 MB/yêu cầu. Đề xuất Supabase Storage; quyết định riêng |

## 9. Kiểm thử và ngân sách

- Test canh bất biến mới (mỗi cái một test tên rõ):
  - sửa của sale **không đụng** dòng `core` (so trước/sau); `dinh_chinh_gia`, `gia_doi_thu_tay`,
    `tiep_xuc_nhac` chỉ thêm (`kome_app` không UPDATE/DELETE được);
  - `yen_chuan`: ÷ 1,08 đúng một lần khi có thuế; không kg → `don_vi`, không đoán;
  - bất thường: > 2× / < 0,5× trung vị, nhóm < 3 bên → không xét; "đúng rồi" gỡ cờ;
  - trung vị bảng giá KHÔNG gồm khách kể; quan sát `het` không vào trung vị;
  - `gia_kome_kg` = tỷ số các tổng, đọc `ban_den_moc` (mã nội bộ không lọt), quay về mốc;
  - quay về mốc: xem tháng 8 không thấy quan sát `ngay_nguon` tháng 9;
  - hoàn tác lô: dòng `core` mất, đính chính của lô đó thành mồ côi → `mart` bỏ qua, không nổ;
  - đăng ký bộ nạp khớp mọi danh mục (test sẵn có sẽ đỏ nếu thiếu);
  - `_PHIEN_BAN` có đủ bảng `app` mới (sửa xong màn đổi ngay).
- Ngân sách lượt hỏi: `/api/doi-thu` tổng quan ≤ 3 · so sánh ≤ 2 · hồ sơ đối thủ ≤ 3 · duyệt ≤ 2 ·
  khối Sản phẩm 360 = 1. Có test đếm.
- `npm run build` + `spa/.nguon` như mọi thay đổi `giao_dien/`.
- Migration mới (059+) chạy bằng `postgres`, TRƯỚC khi triển khai.

## 10. Không làm (có chủ ý)

- Không gọi AI trên web; không tự đọc số trong câu văn của sale.
- Không đăng nhập web đối thủ, không dùng tài khoản của ai; web cần đăng nhập → chỉ dùng file sale gửi.
- Không in "% khả năng" hay dự đoán đối thủ sẽ làm gì.
- Không tự đề xuất giá bán cho KOME — màn chỉ đặt số cạnh nhau, quyết định là của người.
- Không dùng `core.dim_product.compete_code` (独占or競合商品コード) cho tới khi chủ DN nói nó nghĩa là gì.
