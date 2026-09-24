# Kỳ so sánh tự chọn — đặc tả

Ngày: 2026-09-25 · Nối tiếp: `2026-09-24-khoang-xem-thang-design.md`, `2026-09-24-moc-thoi-gian-doi-duoc-design.md`

## 1. Mục tiêu

Khoảng xem hôm nay kèm hai phép so CỐ ĐỊNH (`so_sanh[0]` năm trước, `so_sanh[1]` tháng trước /
khoảng liền trước). Chủ DN muốn chọn MỘT thời kỳ bất kỳ để so. Khi đã chọn, **cả website so với
đúng kỳ đó** (thay cả hai phép so mặc định); bỏ chọn là về mặc định.

## 2. URL

Ba dạng song song với khoảng xem, cùng luật cú pháp (chỉ một dạng; ngày `YYYY-MM-DD`; `ss_den ≥ ss_tu`):

| Tham số | Nghĩa |
|---|---|
| `?ss_thang=YYYY-MM` | so với một tháng |
| `?ss_ky=<company_fy>` | so với một kỳ (1/8 → 31/7) |
| `?ss_tu=&ss_den=` | so với một dải ngày |

Không có `ss_*` ⇒ hành vi y như hôm nay (mọi test cũ giữ nguyên). `ThamSo` mang thêm trường `ss`
(một `ThamSo` con, không có `ss` lồng); `ThamSo.khoa()` thêm các khoá `ss_*` — khoá ảnh chụp tách
theo kỳ so sánh, vẫn không hỏi CSDL. `ThamSo.moc()` KHÔNG đổi (mốc = ngày cuối khoảng đang xem).

## 3. Luật (kome/khoang_xem.py — chỗ DUY NHẤT hiểu phép so)

Có `ss` ⇒ `so_sanh` = đúng MỘT `SoSanh(ma='tu_chon', nhan=…)`. Mọi người đọc hiện có đã xử lý
tuple một phần tử (dạng Kỳ, `_ss_phu`), nên Tổng quan / Khách hàng / Sản phẩm / bản đồ tự đi theo.

Dải so sánh thô: Tháng = trọn tháng; Kỳ = dải của kỳ đó trong `PhamVi.ky` (đã cắt theo dữ liệu),
kỳ không có trong kho ⇒ trọn 1/8 → 31/7 (sẽ `co = false`); Khoảng = nguyên văn.

Cắt cho cân:
- **Tháng ↔ Tháng**: tháng đang xem dở dang (không `tron_thang`) ⇒ dải so = mùng 1 → min(ngày
  `den.day`, ngày cuối tháng so). Tháng trọn ⇒ trọn tháng. Cùng luật "tháng dở dang so cùng dải
  ngày" của `so_sanh` mặc định.
- **Kỳ ↔ Kỳ**: cùng vị trí trong kỳ. Độ lệch = `tu`/`den` đang xem so với 1/8 của kỳ đang xem;
  dải so = 1/8 của kỳ so + cùng độ lệch (ngày không tồn tại, vd 29/2, kẹp về ngày cuối tháng).
  Nếu dữ liệu của kỳ so bắt đầu muộn hơn → phía đang xem (`tu_nay`) dời cùng độ lệch (luật
  `ky_cung_ky`: chỉ so phần CẢ HAI phía có dữ liệu).
- **Mọi tổ hợp khác**: so nguyên văn. Khác số ngày ⇒ `mo_ta` in "(n ngày với m ngày)".

Chặn: dải so (sau khi cắt) kết thúc SAU `hom_nay` của khoảng đang xem (= mốc, 040) ⇒ `LoiKhoang`
"Kỳ so sánh phải nằm trước ngày cuối khoảng đang xem — muốn so ngược thì đổi chỗ hai kỳ." Lý do:
`mart.dong_ban` chỉ thấy dòng ≤ mốc; nới mốc thì hạng / trạng thái / tồn cũng dời — sai bất biến 040.
Chồng lấn với khoảng đang xem thì được.

`co`: cùng `_so` hiện có (tháng chứa ngày đầu dải so đã có dữ liệu). Không `co` ⇒ màn in "không có
dữ liệu để so" như hôm nay.

`mo_ta`: "<nhãn> · <dải> · so với <nhãn so>: <dải so>" (+ phần số ngày nếu khác). `KhoangXem` thêm
`tu_chon: bool` để giao diện biết đang so tự chọn.

## 4. /bao-cao dạng Kỳ

Hôm nay dạng Kỳ gọi thẳng `bao_cao.tinh_bao_cao` (so cùng kỳ cũ). Có `ss` ⇒ đi nhánh khoảng
(`BK.tong` / `chuoi` / `nganh` …, 7 lượt, ≤ 11). Không `ss` ⇒ số cũ, không đổi.

## 5. Giao diện

`khoang.ts`: `THAM_SO` thêm `ss_thang`, `ss_ky`, `ss_tu`, `ss_den` — `giuKhoang`, `voiKhoang`,
khoá TanStack đi theo. Bộ chọn chính đổi khoảng xem thì GIỮ `ss_*`.
`KhoangXem.tsx`: dòng "SO VỚI" — nút "Mặc định" · "Chọn kỳ…" (bộ gạt Tháng / Kỳ / Khoảng, ô chọn
giới hạn `max` = ngày cuối khoảng đang xem); đã chọn ⇒ chip "So với <nhãn> ✕". Giao diện không tự
tính ngày — dòng mô tả là `mo_ta` của máy chủ.
Nhãn cột "So …" của các màn đọc `so_sanh.nhan` — tự đúng.

## 6. Kiểm thử

- `tests/test_khoang_xem.py`: cú pháp `ss_*`; tháng dở dang cắt cùng dải; 31 → 30; kỳ dở dang;
  kỳ so bắt đầu giữa chừng; tổ hợp khác nguyên văn + số ngày; chặn sau mốc; `co = false`; khoá.
- Đẳng thức: `ss_thang` = tháng trước ⇒ cùng dải với `so_sanh[1]` mặc định.
- API: `?ss_thang=` đi qua các endpoint doanh số; ngân sách truy vấn không đổi; `/bao-cao?ky=&ss_ky=`
  ≤ 11.
- Build `giao_dien` → `kome/web/spa/`.

Không migration mới; không đổi định nghĩa chỉ số trong `mart`.
