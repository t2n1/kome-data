# Thiết kế lại hồ sơ khách 360° (`/khach-hang/{mã}`)

Ngày: 2026-09-26 · Phạm vi: **chỉ giao diện** (`giao_dien/src/khach/`), không đổi API, mart hay migration.

## 1. Vì sao

Chủ DN nêu ba vấn đề của màn hiện tại (bám `Customer 360.dc.html`, 5 tab):

1. **Quá tải**: tab Tổng quan có 11 khối, gần như khối nào cũng kèm một dòng giải thích cách tính, và phải bấm qua 5 tab mới hiểu được khách.
2. **Không phục vụ việc gọi khách**: lý do gọi, mã cần nhắc và lần liên hệ trước nằm rải ở ba tab.
3. **Giao diện cũ**: khoảng cách lẻ, nhiều khung "chưa có", thiếu thứ bậc thị giác.

Người dùng là **cả sale lẫn quản lý, ngang nhau**. Sale hỏi "gọi thì nói gì?", còn quản lý hỏi "khách này đang lên hay xuống?".

## 2. Bố cục: hai cột (phương án A)

```
┌ Đầu trang: tên · hạng theo DT 12 tháng · trạng thái · nhãn tháng · thẻ tự động ┐
│ mã · phụ trách · tỉnh · ☎ · ※OBC※ · dữ liệu đến …   [‹ n/N ›] [Ghi liên hệ]   │
├──────────────── cột trái (dính) ─┬──────────── cột phải ───────────────────────┤
│ Vì sao cần gọi                   │ 4 ô số sức khoẻ                             │
│ Mã đến ngày mua lại + chép k.bản │ Biểu đồ doanh thu 12 tháng                  │
│ Lần liên hệ trước + ghi nhanh    │ Tab: Mặt hàng · Đơn hàng · Công nợ ·        │
│ Công nợ                          │      Hồ sơ và nhật ký                       │
└──────────────────────────────────┴─────────────────────────────────────────────┘
```

- Cột trái rộng khoảng 320px và dùng `position: sticky` khi màn ≥ 1024px. Dưới 1024px, hai cột xếp chồng (trái trên, phải dưới) và cột trái không dính nữa.
- Thanh trên (← danh sách, ô chuyển khách, ‹ n/N ›) giữ nguyên hành vi.

## 3. Đầu trang

- Dòng 1 gồm tên (`ten-jp`), nhãn **"Hạng X"** (title "hạng theo doanh thu 12 tháng", theo bất biến hạng), nhãn trạng thái (`nhan_trang_thai`) và nhãn tháng (`nhan_thang`, chỉ với `tre`/`da_mua`/`chua_toi_ngay`, title = `cach_tinh_thang`).
- Dòng 2 gồm mã, người phụ trách, tỉnh/thành phố, ☎ `tel:`, `※dau_hieu_obc※`, "dữ liệu đến dd/mm/yyyy" (hoặc nhãn mốc lùi của `useNhanMoc`).
- Thẻ khách tự động (`h.the`) chuyển lên thành chip nhỏ dưới dòng 2 (title = `vi`). Dòng "Thẻ tay chưa có nơi lưu" bị bỏ.
- Nút "Ghi liên hệ" cuộn tới ô ghi nhanh ở cột trái, mở nó ra và đặt con trỏ vào ô đó. Nút không nhảy tab nữa.
- `?loi_tx=` vẫn hiện `khoi-loi` như cũ.

## 4. Cột trái: "Việc với khách này"

| Khối | Nguồn (có sẵn trong `HoSoApi`) | Ghi chú |
|---|---|---|
| **Vì sao cần gọi** | `h.dien_giai`, `k.trang_thai`, `k.ty_le_im_lang`, `h.thang_nay.nhan` | Viền trái màu theo `MAU_TT`. Giao diện KHÔNG tự viết câu lý do: in `dien_giai` của máy chủ. Câu phân bậc nhịp (< 1× / < 2× / < 4× / ≥ 4×) là câu đang có trong `TabTongQuan` và được chuyển nguyên văn sang đây. Khách `khong_goi` (※廃業※/※取引停止※) hiện "Khách đã ngừng giao dịch — không gọi" với viền xám, và ẩn khối mã. |
| **Mã đến ngày mua lại** | `h.lich` (`ma`, `so_tre`, `tong`), `h.da_ngung_mua.length` | Mỗi dòng là tên mã và "quá n ngày" / "còn n ngày" (đỏ < 0, vàng ≤ 7, xám còn lại). Tiêu đề góc là `so_tre/tong đã quá`. Dòng cuối "+ n mã đã ngừng mua" chuyển sang tab Mặt hàng và cuộn tới khối "Đã ngừng mua". **Tên cố ý KHÁC "Nên chào"** của `/lien-he` (định nghĩa khác: 3 mã mua nhiều lần nhất, `LH.CACH_TINH_GOI_Y`). Hai khối cùng tên thì phải cùng một định nghĩa. |
| **Chép kịch bản gọi** | như trên + `k`, `nhat_ky[0]` | Hàm `kichBan` của `lien_he/LienHe.tsx` chuyển ra `khach/kich_ban.ts` và được hai màn dùng chung. Ở hồ sơ, danh sách mã là các mã **đã quá** trong `h.lich` và dòng in là "Mã đến ngày mua lại:", không phải "Nên chào:". `/lien-he` giữ nguyên chữ và dữ liệu của nó. |
| **Lần liên hệ trước** | `h.nhat_ky[0]` | Gồm icon, kiểu, ngày, nhãn kết quả, nội dung, người ghi và "hẹn dd/mm" nếu có. Bên dưới là `GhiTiepXuc` chế độ `gon`, thu gọn sau nút "Ghi nhanh", với `lam_moi=[["kh-ho-so", mã]]`. |
| **Công nợ** | `useCongNoKhach` (`/api/cong-no/khach/{mã}`) | Trình bày lại nội dung của `OCongNo` (quá hạn, dư nợ, kỳ đến, nhãn "bên nhận HĐ"), liên kết sang `/cong-no?tim=`. Ba trạng thái (chưa có sổ · không có trong sổ · có số) giữ nguyên câu. Khối ẩn khi `TN.cong_no` tắt. |

## 5. Cột phải: "Sức khoẻ khách"

**4 ô số**:
1. DT theo khoảng xem, kèm `so_sanh` như cũ.
2. DT 30 ngày, so với 30 ngày trước.
3. Nhịp mua, gồm "n ngày" và "im n ngày · x× nhịp". Ô này thay đồng hồ `DongHo`.
4. Biên lãi gộp luỹ kế (`k.ty_suat`).

Ô "Số mã đang lấy" chuyển xuống đầu tab Mặt hàng. Ô công nợ đã sang cột trái.

**Biểu đồ 12 tháng** (`BieuDo12Thang` + `MatHangThang`) giữ nguyên hành vi.

**4 tab** (`#mat_hang`, `#don_hang`, `#cong_no`, `#ho_so`):

- **Mặt hàng**, theo thứ tự:
  1. Dòng tóm tắt "n mã đang lấy · m mã đã ngừng".
  2. Mặt hàng mua trong khoảng xem (bảng hiện tại, giữ nhóm phí 048 và hàng tặng 049).
  3. Top 10 hay mua kèm nhãn đề xuất.
  4. Đã ngừng mua và Tháng này chưa mua (hai khối cạnh nhau).
  5. Giỏ theo ngành.
  6. Lưới 26 tuần.
  7. Gợi ý hàng chưa từng mua.
  8. Tất cả mặt hàng (vẫn thu gọn).
- **Đơn hàng**: dòng thời gian cùng dự báo 14 ngày. Bỏ nút "Tạo đơn nháp" đang bị vô hiệu.
- **Công nợ**: `TabCongNo` giữ nguyên (ẩn khi `TN.cong_no` tắt).
- **Hồ sơ và nhật ký**: thông tin khách, điểm giao 直送先, nhật ký tiếp xúc đầy đủ kèm form ghi,
  và cuối tab là hai khối **"sắp có"** cạnh nhau (xếp chồng trên điện thoại):
  - **Ảnh cửa hàng**: hình rỗng 3 ô ảnh nét đứt · "Ảnh cửa hàng của khách." · "Cần để bật: nơi
    lưu ảnh theo mã khách."
  - **Chat Facebook**: hình rỗng 3 bong bóng chat nét đứt · "Tin nhắn gần nhất với khách trên
    Messenger — xem khách vừa hỏi gì trước khi gọi." · "Cần để bật: kết nối Messenger của trang KOME."

  Hai khối dùng chung thành phần `KhoiSapCo` (icon, tiêu đề, nhãn "Chưa có nguồn", hình rỗng,
  câu công dụng, điều kiện bật). Không có ảnh mẫu hay tin nhắn mẫu, cũng không có nút bị vô
  hiệu, để không ai tưởng là dữ liệu thật. Hai khối không lên cột trái, vì khung rỗng ở chỗ sale
  nhìn khi gọi là nhiễu. Khi có nguồn, chỉ thay nội dung khối.

**Hash cũ**: `#tong_quan` rơi về `#mat_hang`, `#san_pham` về `#mat_hang`, `#ho_so` giữ nguyên. Hash lạ về `#mat_hang`.

**Bỏ hẳn** (không có nguồn hoặc gây nhiễu):
- `PhanTan` (biểu đồ phân tán) và `DongHo`.
- Khung `ChuaCo` "Gợi ý tiếp khách". Ảnh cửa hàng và Chat Facebook KHÔNG bỏ: chúng được thiết kế
  lại thành khối "sắp có" (xem tab Hồ sơ và nhật ký).
- Khung "Bảng giá của bậc", câu nhắc giá theo bậc cũng bỏ.
- Nút "Tạo đơn nháp".
- Khối "Ghi chú" (trùng với "Lần liên hệ trước").

## 6. Giao diện

- **Chữ giải thích**: dòng `phu` dưới tiêu đề khối chuyển vào nút "Cách tính" ở góc khối. Nút là `<button aria-expanded>` bấm để mở, KHÔNG chỉ `title`, để điện thoại cũng mở được. Câu mà luật dự án bắt buộc in lộ (vd. "Đã thu (ước)" / FIFO công nợ, `CACH_TINH` của nhóm tháng khi khối liệt kê nhóm đó) thì vẫn in lộ.
- **Thẻ**: viền 1px `var(--vien)` (token có sẵn), bo 12px, đệm 16px, tiêu đề 14px. Thang khoảng cách 8/12/16/24.
- **Màu chỉ mang nghĩa**: đỏ `giam`/`do`, vàng `canh`, xanh `ok`/`tang`, còn lại xám. Không thêm biến màu mới. Chỉ dùng token của `kome.css`, không đụng hai khối màu tối (bất biến `test_hai_khoi_mau_toi_trong_css_GIONG_HET_NHAU`).
- **Số**: `font-variant-numeric: tabular-nums`, canh phải trong bảng. Ô số dùng `gon`, bảng dùng `yen`.
- Mọi CSS mới nằm trong `khach.css` dưới tiền tố `.hs2-` để khỏi đè lên danh sách / bản đồ.

## 7. Tệp

- `giao_dien/src/khach/HoSo.tsx`: khung hai cột, đầu trang, 4 tab, ánh xạ hash cũ.
- `giao_dien/src/khach/HoSoViec.tsx` (mới): bốn khối cột trái.
- `giao_dien/src/khach/HoSoTab.tsx`: bỏ `TabTongQuan`, `PhanTan`, `DongHo` và các `ChuaCo`, gộp nội dung vào `TabMatHang`, thêm nút "Cách tính" vào `The`.
- `giao_dien/src/khach/KhoiSapCo.tsx` (mới): khối "sắp có" dùng cho Ảnh cửa hàng và Chat Facebook.
- `giao_dien/src/khach/kich_ban.ts` (mới): `kichBan` dùng chung. `lien_he/LienHe.tsx` nhập từ đây, chữ không đổi.
- `giao_dien/src/cong_no/CongNoKhach.tsx`: thêm dạng hiển thị cột trái (`OCongNoGon`), dùng chung `useCongNoKhach`.
- `giao_dien/src/khach/khach.css`: kiểu `.hs2-*`.
- `kome/web/spa/`: bản build (bắt buộc commit).
- `CLAUDE.md`: cập nhật dòng `/khach-hang/{mã}` của bảng trang (5 tab thành hai cột + 4 tab).

## 8. Kiểm

- `pytest -v` xanh. Không đổi API nên ngân sách truy vấn của `ho_so()` (≤ 8) và `/khoang` (2) giữ nguyên. Tìm và sửa test nào bám vào chữ/khối đã bỏ.
- `cd giao_dien && npm run build` rồi `tests/test_api.py::test_ban_build_khop_ma_nguon` phải xanh.
- `npx tsc --noEmit` không lỗi.
- Kiểm trên trình duyệt (preview), chụp ảnh gửi chủ DN:
  - bốn loại khách: quá hạn mua lại, đang mua đều, ※廃業※, không có trong sổ công nợ;
  - sáng và tối;
  - 1280px và 375px;
  - hash cũ `#tong_quan` / `#san_pham`;
  - chép kịch bản và ghi nhanh một lần tiếp xúc trên `kome_test`, KHÔNG ghi lên CSDL thật.

## 9. Ngoài phạm vi

- Không thêm chỉ số, view hay endpoint nào. "Nên chào" theo định nghĩa `/lien-he` KHÔNG vào hồ sơ, vì nó cần thêm một lượt hỏi trong khi `ho_so()` đã chạm trần.
- Không đổi danh sách khách, bản đồ hay `/lien-he` (trừ việc chuyển `kichBan` sang tệp chung).
