# Gộp mức giá theo mặt hàng + xoá (ẩn) mặt hàng đối thủ — đặc tả

Ngày: 2026-09-30 · Chủ DN duyệt thiết kế trong chat cùng ngày ("oke làm đi") sau ba lựa chọn: gộp ở CẢ bảng sửa lẫn so
sánh · giá so sánh = rẻ nhất cho khách thường · xoá = ẩn, có khôi phục. Tiếp nối `2026-09-30-doi-thu-bang-sua-design.md`.

## 1. Vì sao (số đo thật, CSDL thật, chỉ đọc, 2026-09-30)

- 439 cặp (bên, `ma_hang_dt`) hiện hành có > 1 dòng — 1.201 dòng. Gần hết là MỨC GIÁ của cùng một mặt hàng: `kenh_gia`
  (giao 238 · gửi 238 · tại kho 402) và `muc_gia` (pallet 132 · khách ngoài 85 · đặc biệt 32 · kyushu 16). NEXT ghi mỗi
  mặt hàng ba dòng (giao / gửi / tại kho), Vietcook ba (khách ngoài / pallet / tại kho).
- So sánh hiện tính MỖI DÒNG là một mặt hàng: nhóm Sứa (XT02) có 8 dòng = 4 mặt hàng của 3 bên, màn in "7 mặt hàng";
  trung vị, "rẻ hơn KOME", thấp / cao nhất lệch về bên ghi nhiều mức.
- Một số "trùng tên" là KHÁC quy cách (Eihatsu đậu đen túi 500 g / 1 kg) — `ma_hang_dt` đã khác nhau, không gộp.
- Thái Dương ghi giá "branches.special" (mức `dac_biet`) thành `ma_hang_dt` KHÁC vì quy cách chữ khác ("…, mix từ 1th")
  → cần gộp TAY.
- Chưa có cách bỏ một dòng rác (AI đọc nhầm dòng không phải hàng).

## 2. Khái niệm

- **Mặt hàng** = (`ma_doi_thu`, `mat_hang_khoa`); `mat_hang_khoa` = `ma_hang_dt` sau khi áp gộp tay (§3.2). Định nghĩa
  ĐÚNG MỘT LẦN ở `mart.gia_doi_thu_quan_sat.mat_hang_khoa`.
- **Mức giá** = một dòng hiện hành của mặt hàng (phân vùng hiện hành 067 đã là (bên, hàng, kenh, muc, khách kể)).
- **Mức cho khách thường** = `muc_gia IS NULL OR muc_gia = 'dac_biet'` (mọi `kenh_gia`). `pallet`, `khach_ngoai`,
  `kyushu` và mọi mức lạ KHÔNG phải khách thường. Viết ĐÚNG MỘT LẦN: hàm `mart.la_muc_khach_thuong(muc_gia text)`.

## 3. Dữ liệu (migration `070_doi_thu_mat_hang_an.sql`)

### 3.1 Ẩn / khôi phục — `app.an_quan_sat`
`(id bigserial, nguon text CHECK IN ('nap','tay'), quan_sat_id bigint, an boolean NOT NULL, nguoi_dung_id bigint NULL
REFERENCES app.nguoi_dung, luc timestamptz DEFAULT now())`. CHỈ THÊM: `REVOKE UPDATE, DELETE` khỏi `kome_app` (nếp 030).
Trạng thái = dòng `id` lớn nhất của (nguon, quan_sat_id). Chỉ mục (nguon, quan_sat_id, id DESC).

### 3.2 Gộp tay — `app.gop_mat_hang`
`(id bigserial, ma_doi_thu text REFERENCES app.doi_thu, ma_hang_dt text, vao_ma_hang_dt text NULL, nguoi_dung_id, luc)`.
CHỈ THÊM. Dòng mới nhất của (bên, hàng) thắng; `vao_ma_hang_dt` NULL = tách ra. CHECK `vao_ma_hang_dt <> ma_hang_dt`.
LUÔN một bước (mart chỉ tra một lần, không đệ quy): gộp A vào B mà B đang gộp vào C → máy chủ ghi A vào C; gộp A vào
đích Đ mà đang có hàng X gộp vào A → máy chủ ghi thêm X vào Đ (cùng giao dịch). Nhờ vậy mọi đích luôn là hàng KHÔNG gộp
vào đâu. Từ chối: gộp vào chính mình (sau khi quy đích), đích không có dòng hiện hành nào của cùng bên.

### 3.3 `mart.gia_doi_thu_quan_sat` (CREATE OR REPLACE, thêm cột CUỐI)
- `an boolean` = trạng thái mới nhất của 3.1 (không có dòng = false).
- `mat_hang_khoa text` = `coalesce(gộp mới nhất của (bên, ma_hang_dt).vao_ma_hang_dt, ma_hang_dt)`.
- `hien_hanh` đổi thành `NOT bi_thay AND rn = 1 AND NOT an` — `rn` VẪN tính trên mọi dòng (gồm dòng ẩn), nên ẩn một
  quan sát không làm quan sát CŨ hơn của cùng phân vùng sống lại thay nó. Lô tháng sau đọc lại thì là quan sát mới, hiện.
- `an_hien_hanh boolean` = `NOT bi_thay AND rn = 1 AND an` — bộ lọc "Đã xoá".

### 3.4 `mart.gia_doi_thu_hien_hanh` (DROP + CREATE cùng `so_sanh_nhom`, như 067)
Thêm `dai_dien boolean`: mỗi (nhom_khoa, don_vi_so, ma_doi_thu, mat_hang_khoa) ĐÚNG MỘT dòng `dai_dien = true` trong số
dòng không khách kể:
"Dùng được" = `trang_thai <> 'het'`, `yen_chuan IS NOT NULL`, KHÔNG bất thường. Hạng (nhỏ thắng):
0. khách thường VÀ dùng được; 1. không phải pallet VÀ dùng được (vd khách ngoài khi giá thường đang hết); 2. dùng được
(pallet); 3. khách thường (hết / bất thường); 4. còn lại. Trong cùng hạng: `yen_chuan` tăng dần (NULL cuối), `nguon`,
`id`. (Sửa sau rà Task 1: bản đầu xếp dòng HẾT lên trên dòng khách ngoài còn hàng → cả mặt hàng rơi khỏi so sánh.)
Khách kể: `dai_dien = false` (không vẽ, không đếm — như nay). Thêm `gia_pallet_mh numeric` = min `gia_pallet` các dòng
KHÔNG bất thường của mặt hàng (giá cho "Khách mua: 1 pallet"), `so_muc int` = số dòng của mặt hàng.
Mốc "bất thường" (`tv`): trung vị và số bên tính trên MỘT giá mỗi mặt hàng = rẻ nhất cho khách thường còn hàng, không có
thì rẻ nhất không-pallet còn hàng (cùng hai hạng đầu của đại diện, nhưng KHÔNG lọc bất thường — tránh vòng; không khách
kể), không còn trên từng dòng. Cờ `bat_thuong` vẫn theo TỪNG dòng.

### 3.5 `mart.so_sanh_nhom`
Đọc `WHERE dai_dien AND NOT bat_thuong AND trang_thai <> 'het'` (thay cho mọi dòng). `so_quan_sat` = số mặt hàng.

## 4. Máy chủ (`kome/doi_thu.py`, `kome/web/api.py`)

- `_COT_QS` thêm `mat_hang_khoa`, `an`; hiện hành thêm `dai_dien`, `gia_pallet_mh`, `so_muc`.
- `POST /api/doi-thu/an` `{nguon, id, an: bool, da_xem, ghi_de}` → `DT.dat_an`: kiểm dòng tồn tại, `kiem_xung_dot` trên
  khoá `gia:<id>` / `tay:<id>`, ghi `app.an_quan_sat` + `app.doi_thu_nhat_ky` (loai `an` / `hien`) CÙNG giao dịch.
- `POST /api/doi-thu/gop-mat-hang` `{ma_doi_thu, ma_hang_dt, vao_ma_hang_dt | null, da_xem, ghi_de}` → `DT.gop_mat_hang`:
  luật §3.2, 409 trên khoá `<bên>/<hàng>`, nhật ký loai `gop`; khi gộp, nếu (bên, hàng) chưa có ghép tường minh thì chép ghép
  (mã KOME, nhóm, nhãn) của mặt hàng đích qua `dat_ghep` CÙNG giao dịch (dòng gộp vào cùng nhóm so sánh).
- `duyet(loc='da_xoa')`: đọc `gia_doi_thu_quan_sat WHERE an_hien_hanh` (không có cột bất thường → false). Các lọc khác
  vẫn trên hiện hành (dòng ẩn không có ở đó). Thứ tự: bên → `mat_hang_khoa` → giá tăng dần, để các mức của một mặt hàng
  đứng liền nhau.
- `tong_quan.ben.so_dong` = số MẶT HÀNG (count DISTINCT mat_hang_khoa, không khách kể); thêm `so_muc` = số dòng.
- Ảnh chụp: mọi đường ghi mới ghi `app.doi_thu_nhat_ky` cùng giao dịch → phiên bản đổi (không thêm vào `_PHIEN_BAN`).

## 5. Giao diện

- `so_sanh_logic.ts::veDuoc` = không khách kể VÀ `dai_dien !== false` — MỘT chỗ; cột / chấm / bản đồ nhiệt / đếm /
  "Thiếu quy cách" / lọc bên tự đi theo. Giá "1 pallet" của mặt hàng đọc `gia_pallet_mh`.
- `ONoiGia`: thêm khối "Các mức giá khác của mặt hàng này" (dòng cùng bên + `mat_hang_khoa` trong nhóm, nhãn mức + giá).
- Tab Đối thủ (`ho_so_logic.ts`): mỗi mặt hàng một thanh (`dai_dien`).
- Bảng sửa: nhóm theo (bên, `mat_hang_khoa`). Dòng đầu = dòng đại diện, có chip "+n mức" (mặc định thu gọn) mở các dòng
  con; cột mới "Mức giá" (nhãn: `giao` Giao tận nơi · `gui` Gửi · `tai_kho` Tại kho · `pallet` Pallet · `dac_biet` Đặc biệt ·
  `khach_ngoai` Khách ngoài · `kyushu` Kyushu · khác nguyên văn · trống "Thường"). Nút 🗑 trên từng dòng (xác nhận nhẹ
  bằng chính nút: bấm lần 1 đổi thành "Xoá?", lần 2 mới gửi); chip lọc "Đã xoá" liệt kê dòng ẩn với nút "Khôi phục".
  "Gộp vào…" ở ⋯ của dòng: hộp chọn mặt hàng đích cùng bên (tìm theo tên); dòng đã gộp có "Tách ra".
- 409 của ẩn / gộp: cùng dải Ghi đè / Lấy bản kia của bảng.

## 6. Kiểm
- pytest (`tests/test_mart_doi_thu.py`, `tests/test_doi_thu.py`, `tests/test_doi_thu_api.py`): ẩn không làm dòng cũ
  sống lại + lô mới hiện lại; khôi phục; đại diện theo luật §3.4 (khách thường rẻ nhất, bỏ pallet / khách ngoài, bất thường,
  hết; rơi về); trung vị / so_ben / so_quan_sat theo mặt hàng; gộp tay (một bước, tách, chép ghép, từ chối tự gộp);
  sổ chỉ thêm (kome_app không UPDATE / DELETE); 409; một lượt hỏi cho mỗi GET.
- vitest: `veDuoc`, nhóm dòng bảng sửa, nhãn mức giá, các mức khác trong ô nổi.
- Trình duyệt trên CSDL giả ở máy (lưu thật) và dữ liệu thật (chỉ xem, POST bị chặn).
- **Migration 070 phải chạy TRƯỚC khi triển khai** (bằng `db/migrate.py`, vai trò postgres, chủ DN đồng ý).
