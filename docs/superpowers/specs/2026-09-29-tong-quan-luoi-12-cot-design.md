# Tổng quan: lưới 12 cột, kéo thả mượt, ⋯ trên tab, nhiều cách xem mỗi khối

Ngày: 2026-09-29 · Yêu cầu của chủ DN (4 ý), chủ DN giao "làm hết, tuỳ bạn quyết định".

1. Dashboard có **lưới** để kéo thả module dễ hơn.
2. Tuỳ chọn bảng (⋯) nằm **ngay trên tab** của bảng đó, không phải một nút riêng.
3. Kéo thả **mượt** hơn.
4. Một module có **nhiều cách xem** (kiểu biểu đồ / chỉ số khác nhau).

## 1. Hiện trạng (trước đặc tả này)

- `Luoi.tsx`: CSS grid 3 cột, `grid-auto-flow: dense`, hàng ≥ 150 px. Bố cục chỉ là THỨ TỰ +
  rộng 1–3 / cao 1–4 — không có toạ độ, không đặt được khối vào một chỗ cụ thể.
- Kéo bằng HTML5 drag & drop: ảnh mờ của trình duyệt, vạch đỏ trái/phải, khối khác không dời
  cho tới khi thả → giật. Không chạy trên màn cảm ứng.
- Nút ⋯ của bảng đứng riêng sau dãy tab.
- Chỉ khối ngân sách có một nút tự chế (Doanh thu / Lãi gộp), không nhớ lại được.

## 2. Quyết định

### 2.1 Lưới toạ độ 12 cột (ý 1)

- Lưới **12 cột**, hàng **40 px**, khe 12 px. Mỗi khối có `x` (0–11), `y` (≥ 0), `rong`
  (3–12), `cao` (2–16). Đặt bằng `grid-column: x+1 / span rong; grid-row: y+1 / span cao` —
  vẫn là CSS grid (hàng `minmax(40px, auto)`: nội dung dài thì hàng giãn, không bao giờ cắt chữ).
- **Nén dọc** (như Grafana): khối tự nổi lên tới khi chạm khối phía trên — không để lỗ hổng lơ
  lửng. Vị trí ngang (`x`) là của người dùng; thứ tự dọc do kéo quyết định.
- Khi đang kéo / đổi cỡ: **hiện lưới ô** (12 × số hàng + 4 hàng trống phía dưới để thả xuống
  cuối) và một **ô bóng** ở đúng chỗ khối sẽ rơi. Nút "▦ Lưới" ở thanh bố cục bật lưới thường trực
  (không lưu — chỉ là cách nhìn lúc xếp).
- Màn hẹp (< 900 px): một cột, thứ tự theo `(y, x)`; kéo / đổi cỡ bằng chuột tắt (bàn phím
  vẫn được) — một cột thì toạ độ 12 cột không có nghĩa.

### 2.2 Kéo thả mượt (ý 3)

- Bỏ HTML5 drag & drop, dùng **pointer events** (chuột, bút, cảm ứng như nhau). Kéo từ đầu khối
  (`[data-keo]`, trừ nút / liên kết / ⓘ), bắt đầu khi rời điểm bấm > 4 px — bấm thường vẫn là bấm.
- Khối đang kéo **đi theo con trỏ** (`transform`, không qua React mỗi khung hình), nâng lên
  (bóng đổ, hơi nghiêng 1°); ô bóng nhảy theo ô lưới; các khối khác **dạt ra có hiệu ứng** (FLIP,
  180 ms). Thả: khối trượt vào ô bóng. `Esc` huỷ và trả mọi khối về chỗ cũ.
- Tự cuộn trang khi con trỏ sát mép trên / dưới cửa sổ.
- Đổi cỡ: khối giãn **liền mạch theo pixel**, ô bóng cho cỡ đã khớp lưới; thả là khớp.
- `prefers-reduced-motion`: không hiệu ứng trượt.
- Bàn phím (nút ⠿ khi Tab tới): mũi tên dời 1 cột / nửa khối; Shift + mũi tên đổi cỡ 1 ô;
  thông báo vị trí qua `aria-live`.

**Luật đặt chỗ** (`datCho`) — MỘT thuật toán, viết ở hai ngôn ngữ, cùng bộ ca thử:
- `nen(ds, uu_tien?)`: xét khối hiện theo khoá `(y, x)`; mỗi khối bắt đầu ở `y` của nó, đè lên
  khối đã đặt thì bị đẩy xuống ngay dưới khối đó (lặp), rồi nổi lên tới khi chạm. Khối ẩn không
  tham gia (giữ toạ độ cũ).
- Khối đang kéo đặt ở `(tx, ty)` với khoá dọc `ty + cao/2` nếu kéo xuống, `ty − cao/2` nếu kéo
  lên, và đứng TRƯỚC khối khác khi hoà khoá → vượt quá nửa chiều cao khối bên cạnh là đổi chỗ, và
  thả lên ngang một khối là khối đó nhường chỗ.
- Python (`kome/web/bo_cuc.py::nen`) và TypeScript (`giao_dien/src/tong_quan/luoi_logic.ts::nen`)
  chạy CÙNG file ca `tests/du_lieu/luoi_nen_ca.json` — hai bản trôi khỏi nhau là test đỏ.

### 2.3 Dữ liệu bố cục (không cần migration)

`app.bang_tong_quan.bo_cuc` là jsonb — chỉ thêm khoá. Một ô: `{id, x, y, rong, cao, an, xem}`.

- `chuan_hoa` (lúc ghi VÀ lúc đọc, như cũ) kẹp mọi số, bỏ mã lạ / trùng, `xem` không thuộc danh
  mục cách xem của khối → `null`, rồi `nen` (hết chồng lấn).
- **Bố cục cũ** (bất kỳ ô nào thiếu `x` hoặc `y` số) = đơn vị 3 cột: `rong × 4`, `cao × 3`
  (hàng 150 px cũ ≈ 3 × 40 + 2 × 12), rồi xếp theo thứ tự đã lưu bằng **lấp chỗ trống đầu tiên**
  (đúng tinh thần `dense` cũ). Không vứt bố cục nào.
- Khối mới (chưa có trong bố cục đã lưu) nối vào **đáy**, `x = 0`.
- Danh mục `KHOI` đổi sang đơn vị 12 cột (×4 / ×3); `danh_muc()` trả thêm `mac_dinh` (bố cục mặc
  định ĐÃ xếp chỗ) — giao diện "Đặt lại bố cục" dùng nó, không tự xếp lại.
- Hiện lại một khối đã ẩn: đặt ở đáy, `x = 0`, rồi `nen`.

### 2.4 ⋯ nằm trên tab (ý 2)

- Tab đang xem là một "viên" gồm tên + nút ⋯ nhỏ dính liền bên phải; menu mở ngay dưới viên đó.
  Chuột phải lên tab đang xem cũng mở menu. Nút ⋯ riêng sau dãy tab bị bỏ.
- Tab khác không có ⋯ (bấm vào để chuyển bảng trước) — một ⋯ trên mỗi tab là rối, và mọi thao
  tác đều là "với bảng đang xem".
- Hai tab không phải nút lồng nhau (HTML cấm) — viên là một `<span>` bọc `<button role="tab">` và
  `<button aria-haspopup="menu">`.

### 2.5 Nhiều cách xem mỗi khối (ý 4)

- Danh mục cách xem sống ở máy chủ: `bo_cuc.CACH_XEM = {mã khối: ((mã, nhãn), …)}`, cách đầu là
  mặc định; `danh_muc()` gửi `cach_xem` theo từng khối. Giao diện ĐỌC danh mục (không chép).
- Lựa chọn **lưu theo bảng** (`xem` trong ô bố cục) — mỗi bảng một cách nhìn, cùng nếp bố cục.
- Chỉ là cách VẼ LẠI số khối đã tải: **không endpoint mới, không chỉ số mới** (bất biến "API không
  định nghĩa chỉ số"). Tỷ suất vẫn là tỷ số các tổng; luỹ kế là cộng dồn số đã có. Cách xem nào
  không có kỳ so (dữ liệu không mang) thì nói ra ở `canh_bao`, không vẽ nét đứt giả.
- Chọn bằng dải nút nhỏ ở đầu khối (`Khoi.cach_xem`), `aria-pressed`.

| Khối | Cách xem |
|---|---|
| `theo_thang` | Doanh thu (cột, như cũ) · Lãi gộp (cột + kỳ so lãi gộp + ngân sách lãi gộp; biên trong ô số) · Khách mới (khách ĐĂNG KÝ theo tháng, `mart.khach_moi_khoang`, cùng câu SQL) · Luỹ kế — sửa 2026-09-29 theo chủ DN; `bien` cũ → `lai_gop` (`bo_cuc.XEM_CU`) |
| `xu_huong` | Doanh thu (như cũ) · Luỹ kế · Lãi gộp · Số khách |
| `ns_thang` | Doanh thu · Lãi gộp (thay nút tự chế trong đường luỹ kế) |
| `so_sanh_sale` | Tiến độ % (như cũ) · Doanh thu · Lãi gộp |
| `hieu_suat_nganh` | Tỷ trọng (như cũ) · Doanh thu (có vạch kỳ so) · Biên gộp |
| `danh_sach_khach` | Doanh thu (như cũ) · Im lặng (15 khách im lâu nhất so nhịp, trong 60 khách lớn nhất của khoảng) |
| `suc_khoe_khach` | Thanh (như cũ) · Vòng (vòng tròn chia khúc, cùng dữ liệu) |
| `tang_truong` | Số khách (như cũ) · Doanh thu theo kỳ |
| `cong_no` | Tuổi nợ (như cũ) · Nợ lâu nhất (thanh xếp hạng) |

## 3. Phạm vi file

- `kome/web/bo_cuc.py` — đơn vị 12 cột, `O(x, y, xem)`, `nen`, `xep_cu`, `CACH_XEM`, `mac_dinh`
  đã xếp chỗ, `danh_muc()["mac_dinh"]`, `khoi[i].cach_xem`.
- `kome/web/bang_tong_quan.py` — mẫu vai trò dùng `dataclasses.replace`.
- `giao_dien/src/tong_quan/luoi_logic.ts` (+ test) — `nen`, `datCho`, `doiCo`, `datDay`.
- `giao_dien/src/tong_quan/Luoi.tsx` — viết lại: pointer, ô bóng, lưới ô, FLIP, tự cuộn, bàn phím.
- `giao_dien/src/tong_quan/ThanhBang.tsx` — ⋯ trong viên tab.
- `giao_dien/src/tong_quan/TongQuan.tsx`, `khoi.tsx`, `chung/Khoi.tsx`, `chung/Hinh.tsx` (`Vong`),
  CSS, `khoi_dau.ts` (kiểu).
- Test: `tests/test_bo_cuc.py` (đơn vị mới, bố cục cũ, `nen` theo file ca, `xem`),
  `tests/test_bang_tong_quan.py`, `tests/test_cach_xem.py` (mọi cách xem có nhánh vẽ trong
  `khoi.tsx`).

## 4. Không làm

- Không kéo tab (đã quyết ở 056). Không kéo khối giữa hai bảng. Không cách xem dạng bảng (luật
  "Tổng quan ít chữ": không bảng nào).
