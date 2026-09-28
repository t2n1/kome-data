# Kỳ so sánh toàn web — một kỳ so, một cách vẽ

Ngày: 2026-09-28 · Chủ DN duyệt thiết kế trong phiên cùng ngày.
Kế thừa: `2026-09-24-khoang-xem-thang-design.md`, `2026-09-25-ky-so-sanh-tu-chon-design.md`.

## 1. Vấn đề

Thanh KHOẢNG XEM hiện là ba dòng chữ (dạng · SO VỚI · câu mô tả dài "so 1/9 → 28/9/2025 và
1/8 → 28/8") — khó đọc, và không nói rõ biểu đồ đang so với cái gì. Mặc định có HAI phép so
(năm trước + tháng trước), nhưng mỗi khối tự chọn một: ô số in cả hai, biểu đồ vẽ năm trước, cột
danh sách so tháng trước; nhiều biểu đồ so CỨNG (luỹ kế ngân sách luôn tháng trước, khối Theo
tháng luôn năm trước) và bỏ qua kỳ tự chọn; ba nhãn viết cứng "năm trước".

## 2. Nguyên tắc

1. **Một kỳ so duy nhất cho cả website** tại mỗi thời điểm. Mọi ô số / biểu đồ / cột có thể so
   theo thời gian đều đọc ĐÚNG kỳ đó (`khoang.so_sanh[0]`) — không ngoại lệ (bỏ luật "cột so sánh
   ở Khách hàng / Sản phẩm là phép so PHỤ").
2. **Một cách vẽ**: kỳ đang xem = nét liền / cột đặc; kỳ so = **nét đứt** (đường), **cột ma**
   (cột trong suốt viền đứt, đứng sau cột thật), **vạch đứt** (thanh ngang). Thanh chọn phía trên
   dùng đúng hai mẫu đó (`───` Đang xem, `╌╌╌` So với).
3. Máy chủ vẫn là chỗ duy nhất hiểu ngày so sánh; giao diện không tự tính dải.
4. Khối không có nghĩa khi so theo kỳ (tồn kho, công nợ, trạng thái khách, dự báo, Pareto,
   hạn sử dụng, lịch sử theo kỳ) — KHÔNG thêm phép so.

## 3. Tham số URL

| Tham số | Nghĩa |
|---|---|
| (không có) | so **năm trước** (`nam_truoc`) |
| `?ss=truoc` | so **kỳ liền trước**: tháng trước (dạng Tháng) / khoảng liền trước (dạng Khoảng). Dạng Kỳ không có — rơi về năm trước (= kỳ trước) |
| `?ss_thang=` · `?ss_ky=` · `?ss_tu=&ss_den=` | kỳ tự chọn (như cũ). Có `ss_*` thì `ss` bị bỏ (khoá chuẩn hoá không mang nó) |

`ss` sai giá trị → 400. `ThamSo.khoa()` mang `ss`; `ThamSo.chinh()` bỏ nó.

## 4. Máy chủ (`kome/khoang_xem.py`)

- `KhoangXem.so_sanh` luôn có **đúng một** phần tử = kỳ đang bật.
- `KhoangXem.lua_chon`: danh sách chip mặc định `[{ma, nhan, chon}]` (dạng Tháng: năm trước,
  tháng trước; Khoảng: năm trước, khoảng liền trước; Kỳ: năm trước). Với kỳ tự chọn mọi `chon`
  là false.
- `SoSanh.lech_thang: int | None` — kỳ so lệch kỳ xem bao nhiêu tháng TRÒN
  (`tu_nay` và `tu` cùng ngày trong tháng; 12 với năm trước, 1 với tháng trước, N với tháng/kỳ tự
  chọn). None khi không lệch tròn tháng (khoảng liền trước dài lẻ, khoảng tự chọn lệch ngày).
  Biểu đồ theo tháng có cửa sổ RIÊNG (các tháng của kỳ, 12 tháng, quý) dời đúng `lech_thang`
  để lấy chuỗi so; None → không vẽ đường so và in "kỳ so không lệch tròn tháng — không so theo
  tháng được". Quý: chỉ khi `lech_thang % 3 == 0`.
- `mo_ta` in một phép so.
- `kome/ban_khoang.py::_ss_phu` bỏ; mọi chỗ đọc `so_sanh[0]`.

## 5. Thanh chọn (`giao_dien/src/khung/KhoangXem.tsx`)

Hai thẻ cạnh nhau (xếp chồng khi hẹp):

- **ĐANG XEM** (viền liền màu chính, mẫu `───`): nút gạt Tháng / Kỳ / Khoảng · ‹ ô chọn › ·
  nhãn to (`Tháng 9/2026`) · dòng nhỏ `1/9 → 28/9/2026 · 28 ngày` · ghi chú máy chủ.
- **SO VỚI** (viền đứt, mẫu `╌╌╌`): chip theo `lua_chon` + chip "Tuỳ chọn…" (mở bộ chọn cũ) ·
  nhãn to của kỳ so · dòng nhỏ dải ngày + "cắt cùng n ngày" khi `tu_nay/den_nay` khác khoảng xem
  hoặc số ngày hai bên khác nhau · "không có dữ liệu để so" khi `!co`. Kỳ tự chọn: chip riêng kèm ✕.

## 6. Cách vẽ chung (`giao_dien/src/chung/`)

- `BieuDo`: thêm kiểu chuỗi `cot_ma` (hình học của `cot_nen`, nền trong suốt, viền đứt màu
  `--vien-dam`); `Chuoi.so_voi?: number` = chỉ số chuỗi kỳ so — ô nổi in thêm "▲x% so <tên>" cạnh
  chuỗi chính. Chú giải có mẫu riêng cho `cot_ma`.
- Biểu đồ đã có cột nền khác (khách mới: "Đăng ký" + "Đã có đơn") thì kỳ so là **nét đứt**, không
  thêm lớp cột thứ ba.
- `Spark`: tham số `so_sanh?: (number|null)[]` vẽ nét đứt cùng thang.
- `SoSanh.tsx` mới: `DongSoSanh` (ô số: "▲ 12,3% so ╌ Năm trước ¥14,1M" / "Năm trước: không có
  dữ liệu để so") và `VachSoSanh` (vạch đứt dọc trên thanh ngang).
- Nhãn kỳ so LUÔN lấy từ máy chủ (`so_sanh[0].nhan`) — bỏ mọi chữ "năm trước" / "cùng kỳ" viết
  cứng ở khối có phép so theo khoảng.

## 7. Phạm vi theo đợt

**Đợt 1 — thanh chọn + cách vẽ + Tổng quan** (`kome/khoi_tong_quan.py`, `tong_quan/khoi.tsx`):

| Khối | Thay đổi |
|---|---|
| Chỉ số (ô Doanh thu) | một dòng `DongSoSanh`; spark kèm nét đứt kỳ so (`spark_ss`, đã có trong `BK.chuoi`) |
| Xu hướng | nhãn theo kỳ so, ô nổi in % |
| Ngân sách tháng — đường luỹ kế | dạng Tháng: luỹ kế của `so_sanh[0]` theo VỊ TRÍ ngày từ `s.tu` (thay tháng trước cứng); dạng Kỳ: luỹ kế theo tháng dời `lech_thang` (+1 lượt hỏi) |
| Ngân sách tháng + Doanh thu theo sale | mỗi người thêm doanh thu kỳ so (`mart.sale_khoang(s.tu, s.den)`, +1 lượt) → vạch đứt + ▲▼ |
| Theo tháng | cột ma = tháng dời `lech_thang` (`mart.ban_theo_thang`); tháng đang chạy dở dang dùng tổng đúng dải `so_sanh[0]`; ô "So …" và cột bảng đổi nhãn |
| Danh sách khách | cột so = `so_sanh[0]` |
| Hiệu suất ngành | tiêu đề cột theo nhãn kỳ so |
| Khách mới | một phép so; biểu đồ 12 tháng thêm nét đứt "Đăng ký · kỳ so" (dời `lech_thang`, cùng một câu hỏi) |
| Biên theo quý | cột ma doanh thu + nét đứt biên của quý dời `lech_thang/3` (0 lượt thêm) |

Tự đổi theo nhờ §4 (không sửa giao diện): các màn đã đọc `so_sanh` (Báo cáo dạng Tháng/Khoảng,
danh sách khách, danh mục sản phẩm, ô DT·khoảng của hai hồ sơ).

**Đợt 2 — Báo cáo**: dạng Kỳ theo kỳ so, bản đồ nhiệt, cây ô (câu ô nổi), luỹ kế ngân sách, bảng
người phụ trách, sparks, chú giải biểu đồ chính.

**Đợt 3 — Khách hàng & Sản phẩm**: bản đồ (Δ theo tỉnh), hồ sơ khách 12 tháng (qua `/khoang`,
hồ sơ đã chạm trần 8), bảng mặt hàng, sản phẩm 360 (24 tháng, theo ngày theo khoảng xem, 26 tuần,
khách mới/quay lại).

## 8. Test và bất biến

- `tests/test_khoang_xem.py` / `test_ky_so_sanh.py`: đúng một phép so; `ss=truoc` chọn tháng
  trước / khoảng liền trước; dạng Kỳ rơi về năm trước; `ss_*` thắng `ss`; `lech_thang` 12/1/N/None;
  `ss` sai → lỗi; `khoa()` có `ss`, `chinh()` không.
- Tổng quan: mọi khối có phép so trả CÙNG `so_sanh[0]` (một test lặp qua `KHOI`); dời
  `lech_thang` khớp đúng `mart.ban_theo_thang` của tháng dời; luỹ kế kỳ so tại ngày cuối = tổng
  `mart.tong_khoang(s.tu, s.den)`.
- `tests/test_api.py::NGAN_SACH_TRUY_VAN`: `ns_thang` / `so_sanh_sale` +1.
- CLAUDE.md, bất biến "Khoảng xem": thêm luật một kỳ so + `?ss=`, bỏ câu "cột so sánh ở Khách
  hàng / Sản phẩm là phép so PHỤ (`so_sanh[1]`)".
