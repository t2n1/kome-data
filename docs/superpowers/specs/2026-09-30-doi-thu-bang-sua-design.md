# Bảng sửa mặt hàng đối thủ (Dữ liệu › Duyệt / sửa) — đặc tả

Ngày: 2026-09-30 · Chủ DN duyệt thiết kế trong chat cùng ngày ("Oke, làm đi").
Thay danh sách một-dòng-chữ của `TabDuyet` bằng một BẢNG mọi mặt hàng đối thủ, sửa thẳng trong ô.

## 1. Vì sao

Màn Duyệt hiện chỉ mở sẵn "Cần xem" (419 dòng), mỗi dòng là một dải chữ; muốn sửa phải mở pop-up từng dòng. Người sửa
cần thấy cả danh sách của một bên như bảng giá gốc và điền nhanh (ví dụ "tịnh 1 gói" cho cả loạt hàng).

## 2. Số đo thật (CSDL thật, chỉ đọc, 2026-09-30)

- 3.856 dòng hiện hành, JSON của `DT.duyet(loc='')` = **5,26 MB** > trần phản hồi Vercel 4,5 MB → không tải hết một lượt.
- Bên nhiều nhất: NEXT 716 dòng (~1 MB). `EXPLAIN ANALYZE` của `_DUYET` cho NEXT: **0,5 s** ở máy chủ.
- 25 s / 123 s đo từ máy này là thời gian TẢI (đường mạng máy này → Supabase ≈ 33 KB/s: `repeat('x', 1e6)` mất 31 s),
  không phải câu truy vấn — không cần sửa SQL vì tốc độ.

## 3. Máy chủ (`kome/doi_thu.py::duyet`)

- Bộ lọc mới `loc = 'thieu_quy_cach'`: dòng không phải khách kể và `so_goi_thung IS NULL OR kl_goi_g IS NULL`
  (= `so_sanh_logic.ts::thieuQuyCach` + `veDuoc`). `LOC_DUYET` thêm giá trị này.
- Trần `DONG_TOI_DA_DUYET = 800` dòng mỗi lần (≥ bên lớn nhất 716; ~1,1 MB). Trả `{"dong": [...], "tong": n}` —
  `tong` = số dòng khớp bộ lọc TRƯỚC khi cắt. Vẫn MỘT lượt hỏi (`count(*) OVER ()` trong cùng câu).
- Thứ tự không đổi (bất thường → trạng thái duyệt → bên → tên).

## 4. Giao diện

### 4.1 Đầu bảng
- Chip "Mọi bên" + một chip mỗi bên (từ `/tong-quan` `ben`, kèm `so_dong`), xếp số dòng giảm dần. Bên nằm trên URL
  (`?ben=`, đã có). Chip lọc: Tất cả (mặc định) · Cần xem · Bất thường · Chưa ai xác nhận · Chưa ghép · Thiếu quy cách.
- Ô tìm theo tên hàng / quy cách / mã KOME (lọc ở trình duyệt, bỏ dấu `loc.ts::boDau`).
- `tong > dong.length` → câu "Đang hiện 800 / 3.856 dòng — chọn một bên để xem hết".
- Giữ nguyên: dải thư mục Drive theo tháng, "Thêm hàng AI bỏ sót".

### 4.2 Cột
| Cột | Trường | Sửa trong ô |
|---|---|---|
| Bên | `ma_doi_thu` (chỉ khi "Mọi bên") | không |
| Tên hàng | `ten_goc` | chữ |
| Quy cách | `quy_cach_goc` | chữ |
| Gói/thùng | `so_goi_thung` | số nguyên |
| Tịnh 1 gói (g) | `kl_goi_g` | số (phẩy = thập phân) |
| Giá | `gia_goc` | số — **"Máy đọc sai"** |
| Đơn vị | `don_vi_gia` | chọn (`DON_VI`) — "Máy đọc sai" |
| kg / đơn vị | `kg_moi_don_vi_gia` | số (phẩy = thập phân), > 0 — xem §6 |
| Thuế | `thue` | chọn — "Máy đọc sai" |
| Tình trạng | `trang_thai` | chọn (`NHAN_TRANG_THAI`) |
| Mã KOME | `ma_kome` (hoặc `ma_ghep`) | chữ + gợi ý (`/goi-y-nhac`) |
| Thương hiệu | `nhan` | chọn: cùng / khác / không ghép |
| ¥/kg | `yen_chuan` khi `don_vi_so = 'kg'`, không thì "chưa quy" | không (máy chủ tính) |
| Duyệt | nút "Đúng rồi" (dòng nạp chưa xác nhận) / nhãn | — |
| ⋯ | mở `SuaMatHang` (bậc giá, khuyến mãi, "Giá đã đổi", lịch sử) | — |

Ô trống hiện "?" cam (`dt-hoi-cam`); dòng đã sửa ✎ (`sua_logic.ts::daSua`); dòng bất thường ⚠ + lý do
(`mau.ts::lyDoBatThuong`). Điện thoại: bảng cuộn ngang trong khung, cột Tên hàng dính trái.

### 4.3 Sửa
- Một ô "đang chọn" (viền). Bấm ô / Enter / gõ ký tự → vào sửa (gõ ký tự: ô bắt đầu bằng ký tự đó). Mũi tên di chuyển
  khi KHÔNG sửa. Khi sửa: **Enter = lưu + sửa tiếp ô cùng cột dòng dưới**; **Tab / Shift+Tab = lưu + ô sửa được kế
  tiếp / trước trong dòng**; **Esc = bỏ**; rời ô (blur) = lưu. Giá trị không đổi → không gửi.
- Thân POST dựng bằng CHÍNH `sua_logic.ts::formTu` + `payload` + `kiemForm` (form lúc mở = `formTu(dòng)`, đổi đúng một
  trường) — một đường dựng thân với pop-up, không viết lại. `FormMatHang` thêm `ten_goc` / `quy_cach_goc` (pop-up không
  vẽ chúng — không đổi hành vi pop-up). Trường giá gửi `vi_sao_gia = 'doc_sai'`. "Giá đã đổi" chỉ qua ⋯.
- Mã KOME: đổi sang mã mới mà nhãn đang "không ghép" → ô hiện hai nút "cùng thương hiệu" / "khác thương hiệu"; bấm là
  lưu cả hai (máy chủ bắt buộc chọn, `kiemForm`). Xoá mã = bỏ ghép.
- Lưu **tuần tự theo dòng**: lần lưu sau của cùng dòng chờ lần trước và dùng `sua_cuoi` / `nguon` / `id` MỚI mà máy
  chủ trả (dòng tay sửa "đọc sai" thành dòng tay mới) — không thì hai ô liền nhau của một dòng tự 409 với chính mình.
- Sau khi lưu: GET `/mat-hang/{nguon}/{id}` → ghép đè vào dòng (giữ các cột `/mat-hang` không trả, như
  `moc_bat_thuong`); dòng đổi id thì thay tại chỗ. Các truy vấn `["doi-thu", …]` KHÁC bảng này bị invalidate; bảng
  không tải lại cả bên sau mỗi ô.
- Trạng thái ô: đang lưu (mờ + vòng quay) → ✓ ngắn → bình thường; lỗi 400 → ô đỏ, câu lỗi dưới dòng, ô giữ giá trị
  đã gõ để sửa lại. **409** → dải dưới dòng: `moTaXungDot` + [Ghi đè] (gửi lại `ghi_de`) · [Lấy bản kia] (tải lại
  dòng, bỏ giá trị đã gõ). **Dòng đã bị thay** (409 `thay_boi` hoặc `thay_boi` sẵn) → dòng mờ, không sửa, nút
  "Tải bản mới" (tải lại bảng).

### 4.4 Không làm (đợt này)
Chọn nhiều dòng để "Đúng rồi" một lượt; dán khối từ Excel; sắp theo cột.

## 5. Kiểm
- pytest: `thieu_quy_cach` (khách kể không vào; đủ hai ô thì không vào), trần + `tong`, vẫn MỘT lượt hỏi.
- vitest (`bang_sua_logic.test.ts`): thân POST từng cột (giá → `doc_sai`; không đổi → không gửi; mã mới cần nhãn),
  di chuyển Enter / Tab / mũi tên (bỏ cột không sửa, dừng ở biên), hiển thị ô ("?" khi trống, ¥/kg "chưa quy"),
  ghép dòng sau khi lưu (giữ cột thiếu, thay id), tìm bỏ dấu.
- Trình duyệt trên dữ liệu thật (bản chỉ đọc ở máy, không bấm lưu thật): bảng một bên, di chuyển bàn phím, 375 px,
  sáng / tối. Lưu + 409 kiểm trên CSDL test ở máy.

## 6. Phát hiện khi kiểm (2026-09-30): "tịnh 1 gói" KHÔNG quy giá ra ¥/kg

`mart.gia_doi_thu_quan_sat` (060/067) quy giá ra ¥/kg CHỈ bằng `kg_moi_don_vi_gia` (`don_vi_so = 'kg'` khi cột đó > 0);
`so_goi_thung` / `kl_goi_g` chỉ dùng cho `kg_thung_dt` và giá bậc. Điền "tịnh 1 gói = 200 g" cho giá ¥285/gói vẫn để dòng
ở `don_vi:goi` (đo trên CSDL giả: `yen_chuan` 285, `don_vi_so` 'don_vi:goi'); điền `kg_moi_don_vi_gia = 0,2` thì ra
¥1.425/kg. Vì vậy:
- Bảng có cột "kg / đơn vị" (`FormMatHang.kg_moi_don_vi_gia`, không thuộc TRUONG_GIA — không cần "vì sao đổi giá").
- Câu trên thẻ nhóm "giá theo gói, chưa quy ra ¥/kg" của So sánh (`BieuDoCot.tsx::DauNhom`) trước ghi "điền gói / thùng
  + tịnh 1 gói" — sai; nay trỏ tới cột "kg / đơn vị" của bảng này.
- CHƯA đổi mart: suy `kg_moi_don_vi_gia` từ `kl_goi_g` khi `don_vi_gia = 'goi'` (và từ `so_goi_thung × kl_goi_g` khi
  `'thung'`) là đổi định nghĩa quy đổi ở 060/067 → migration mới + chạy trên CSDL thật, chờ chủ DN quyết.
