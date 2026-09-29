# Thị trường & đối thủ — làm lại giao diện (`/doi-thu`) — đặc tả thiết kế

Đợt 4 của `2026-09-29-thi-truong-doi-thu-design.md` (gọi tắt **ĐT gốc**). Đợt 1–3 đã chạy trên CSDL thật
(059–064). Chủ DN xem trang sau Đợt 3: "khó nhìn quá — nhiều thông tin, xử lí không khéo thì rất dễ
loạn". Đặc tả này thay §5 của ĐT gốc (màn hình). Nó thêm phần dữ liệu mà màn mới cần, và sửa ba lỗi dữ
liệu tìm ra khi vẽ phác trên dữ liệu thật. §4, §6, §7, §11 của ĐT gốc vẫn giữ, trừ chỗ ghi rõ là đổi.

Bản vẽ phác đã được chủ DN duyệt từng bước (visual companion, dữ liệu thật tháng 8, chỉ đọc).
Bản cuối: `.superpowers/brainstorm/277-1790676676/content/ca-trang-8.html` (git-ignored). Các script sinh ra
nó nằm trong scratchpad của phiên. **Đặc tả này là nguồn duy nhất**; bản vẽ chỉ để minh hoạ.

## 1. Quyết định đã chốt (chủ DN, 2026-09-29)

| # | Câu hỏi | Chốt |
|---|---|---|
| 1 | Người mở trang để làm gì | **Cả ba việc ngang nhau**: (a) KOME đắt / rẻ ở đâu · (b) sale tra nhanh một hàng / một đối thủ · (c) có gì mới tháng này. Mỗi việc một chỗ riêng |
| 2 | Thiết bị | **Máy tính là chính**. Điện thoại chỉ cần xem được |
| 3 | Hướng trình bày | **Nhiều hình, ít chữ**. Chọn sản phẩm KOME rồi so với đối thủ bằng biểu đồ |
| 4 | Cách vẽ so sánh | **Giữ cả 3**: A cột từng sản phẩm · B chấm trên một trục · C bảng nhiệt sản phẩm × đối thủ |
| 5 | "Cùng hàng / thay thế" | Hiện bằng chữ **"cùng thương hiệu" / "khác thương hiệu"** và **bằng màu**: cùng thương hiệu = thanh xanh lam; khác thương hiệu = thanh xám tối + tên mờ. Không in chữ nhãn dưới tên |
| 6 | Mua nhiều rẻ hơn | Nút **"Khách mua: 1 thùng · 5 thùng · 10 thùng · 1 pallet"**. Biểu đồ chỉ hiện MỘT giá (ở số lượng đang chọn); các bậc giá nằm trong ô nổi |
| 7 | Ô nổi (rê chuột) | Bảng giá theo bậc: ¥/gói · ¥/thùng (thùng CỦA BÊN ĐÓ) · ¥/kg · so KOME. Có 3 ô quy cách đặt cạnh số của KOME |
| 8 | Cột trên biểu đồ cột | **Đối thủ · Tên sản phẩm · gói / thùng · tịnh 1 gói** là 4 cột riêng. KHÔNG in "thùng … kg" dưới tên |
| 9 | Sửa | **Bấm vào đâu sửa ở đó**, bằng **pop-up** giữa màn. "Ở tất cả nơi trong phần đối thủ chỗ nào cũng sửa được" — nhiều sale thấy sai chỗ nào thì sửa luôn chỗ đó |
| 10 | Câu kết luận mỗi sản phẩm | **Không làm** ("nhiều chữ nó rối") |
| 11 | Giá KOME mặc định | **標準価格** (giá tiêu chuẩn của `取引単価データ`). Đổi được sang thực bán 90 ngày / 売価No.1–10 |
| 12 | Phí giao hàng | **Thêm tab** so phí ship · ghép kiện · phí gửi · phí daibiki của các bên với KOME |
| 13 | Góp ý UX của Claude | Làm hết, trừ câu kết luận (#10) — xem §3 |

## 2. Cấu trúc trang

Thanh tab (`?tab=`, bỏ trống = `tom_tat`):

| Tab | `?tab=` | Việc (§1 #1) |
|---|---|---|
| Tóm tắt | `tom_tat` | nhìn một lượt cả ba việc |
| So sánh giá | `so_sanh` | (a) + (b) theo hàng |
| Đối thủ | `ben` | (b) theo bên |
| Tin thị trường | `tin` | (c) |
| Phí & giao hàng | `giao_hang` | so điều kiện giao hàng |
| **Dữ liệu ▾** (menu góc phải) | `duyet` · `nhom` | các màn sửa hàng loạt: Duyệt / sửa · Nhóm & quy cách · Thư mục Drive theo tháng · **Giá KOME lệch** (mới, §6.3) |

Tab cũ đổi tên: `tong_quan` → `tom_tat`, `ben` giữ nguyên. Link cũ có `?tab=tong_quan` phải mở Tóm tắt.
Mọi `replaceState` đi qua `giuKhoang()` (bất biến Khoảng xem). Theo khoảng xem như ĐT gốc (mốc = cuối
khoảng).

## 3. Luật trình bày chung (mọi tab)

1. **Màu nhìn từ phía KOME**: **đỏ = bất lợi cho KOME** (đối thủ rẻ hơn / KOME đắt hơn), **xanh lá = KOME
   có lợi**, xám = ngang (±5%). Cùng một luật ở mọi biểu đồ, ô nổi, bảng nhiệt, ô số. Định nghĩa MỘT lần:
   `doi_thu/mau.ts::mauLech(p)`, với `p` = % giá đối thủ so với giá KOME. Có test canh.
2. **Thương hiệu**: cùng thương hiệu = xanh lam `#4a7fb5`; khác thương hiệu = xám tối và tên mờ. Ở cách vẽ
   B (màu đã dùng cho rẻ / đắt): chấm đặc = cùng thương hiệu, vòng rỗng = khác thương hiệu. Ở cách vẽ C:
   ô đậm = có cùng thương hiệu, ô nhạt viền đứt kèm "≈" = chỉ có khác thương hiệu.
   **Nhãn hiển thị** "cùng thương hiệu" / "khác thương hiệu" ↔ mã CSDL `cung_hang` / `thay_the`, mã
   **không đổi**. Chỉ đổi chữ, ở MỘT chỗ: `doi_thu/kieu.ts::NHAN_GHEP`.
   Nghĩa `cung_hang` từ nay = cùng thương hiệu (quy cách khác vẫn là cùng thương hiệu, vì giá đã quy về
   ¥/kg). Sổ tay đọc (`huong-dan-doc.md`) sửa theo.
3. **Thiếu là "?" màu cam, bấm được**: ô chưa có dữ liệu không bao giờ in 0 hay để trống. Bấm vào mở
   pop-up sửa, con trỏ nằm sẵn ở đúng ô đó.
4. **Thuế không rõ** (`thue = 'khong_ro'`): dấu "?" vàng ở cuối thanh. Ô nổi nói: "đang tính như CHƯA thuế
   — nếu đã gồm 8% thì giá thật thấp hơn ~7%". (Đúng quy đổi hiện có của 060: chỉ ÷ 1,08 khi `thue='co'`.)
5. **Giá đã gồm ship** (`gom_ship = 'co'`, hoặc bên đó `bao_ship`, §5.4): dấu 🚚 nhỏ cạnh giá.
6. **Giá cũ**: quan sát có `tuoi_ngay` > 60 thì thanh mờ, ô nổi ghi "Bảng giá đã n ngày". Hằng
   `doi_thu/mau.ts::NGAY_CU = 60`.
7. **Ô nổi**: dùng chung `chung/ONoi.tsx` (rê chuột hiện; chạm lần 1 hiện, lần 2 mở pop-up). Bàn phím:
   Tab tới thanh / chấm / ô → hiện ô nổi; Enter / Space → mở pop-up sửa. Thanh SVG mang `tabindex="0"`
   và `aria-label`.
8. **Ít chữ**: không câu kết luận, không đoạn giải thích trên thân trang. Câu định nghĩa cách tính vào
   ⓘ của `Khoi` (nếp "Tổng quan ít chữ").
9. **Tên ngành tiếng Việt** (Đông lạnh, Đồ khô, Gia vị, Mì & ăn liền, Đồ mát, Nước uống, Bia rượu; hậu tố
   `_THA` → "(Thái)"). Chỉ để HIỂN THỊ trên màn này, ở MỘT chỗ: `doi_thu/nganh.ts::tenNganh(food_category_name)`.
   Mã lạ → giữ nguyên văn. Có test phủ đủ 8 ngành đang có. Bộ lọc vẫn gửi tên OBC nguyên văn lên máy chủ.
10. **Hình sản phẩm**: `chung/HinhMa.tsx` (bất biến Hình sản phẩm) ở cột trái và thẻ.
11. **Lựa chọn nằm trên URL**: `?tab=so_sanh&sp=<nhóm>,<nhóm>&sl=1|5|10|pallet&xem=cot|cham|nhiet&gk=chuan|thuc|01…10&cung=1`.
    Mặc định (không tham số) không ghi lên URL.

## 4. Các tab

### 4.1 Tóm tắt
- **Ô tìm** (hàng KOME / nhóm / đối thủ). Chọn một kết quả → tab So sánh với nhóm đó, hoặc tab Đối thủ
  với bên đó.
- **4 ô số**: nhóm có giá KOME để so · KOME đắt hơn thị trường > 5% · mã KOME mà đối thủ đang hết · khuyến
  mãi đang chạy (số bên).
- **"KOME đứng đâu"**: biểu đồ chấm, mỗi chấm một nhóm. Vị trí = % giá KOME lệch so với trung vị đối thủ.
  Dưới là thanh tỉ lệ: rẻ hơn · ngang · đắt hơn · nhóm KOME không bán. Nhóm có giá KOME lệch > 3× không
  vẽ; một dòng cảnh báo trỏ tới Dữ liệu › Giá KOME lệch.
- **Đắt nhất / rẻ nhất so với thị trường**, đặt cạnh nhau, mỗi bên 6 dòng. Mỗi dòng có dải giá (thấp →
  cao, vạch trung vị, chấm KOME). Bấm dòng → So sánh với nhóm đó.
- **Cơ hội: đối thủ đang hết**: thẻ có hình và chip tên các bên đang hết.
- **Ai bán ngành nào**: bóng đối thủ × ngành (thay lưới số cũ). Bấm bóng → So sánh lọc ngành + bên.
- **Khuyến mãi theo bên**: thanh đếm, kèm vài khuyến mãi có giá giảm rõ.

### 4.2 So sánh giá
- **Cột trái**:
  - Danh sách NHÓM so sánh (khoá `ma:`/`n:`), có hình mã KOME chính, chấm màu và "KOME ±x%" — CÙNG con
    số "vị trí KOME" của `mart.so_sanh_nhom` (giá lẻ, 標準価格 — §5.2, §5.3), luật màu §3.1.
  - Ô tìm, chip ngành, nút chọn nhanh: **KOME đắt nhất · Đối thủ đang hết · Còn ô trống**.
  - Chọn tối đa 8 nhóm.
- **Thanh điều khiển**: Khách mua (1 · 5 · 10 thùng · 1 pallet) · Cách vẽ (A · B · C) · "Chỉ cùng
  thương hiệu" · Giá KOME (**標準価格** mặc định · thực bán 90 ngày · 売価No.1–10) · "Tính cả phí giao"
  (tắt mặc định, §5.5).
- **Dòng đếm ô trống**: "✎ n mặt hàng còn thiếu gói / thùng hoặc tịnh 1 gói — bấm để điền cái đầu tiên".
  Chỉ hiện khi n > 0.
- **A · Cột**: mỗi nhóm một biểu đồ thanh ngang, mỗi thanh = một MẶT HÀNG đối thủ (không phải một bên),
  xếp rẻ → đắt.
  - 4 cột trước thanh: Đối thủ · Tên sản phẩm · gói / thùng · tịnh 1 gói.
  - Nhãn sau thanh: giá ¥/kg · % so KOME (màu §3.1) · "↓ từ ¥…" khi rẻ đi nhờ mua nhiều (khung viền
    đứt giữ độ dài giá 1 thùng) · "hết" · "KM".
  - Dòng KOME: thanh đỏ, **dải đỏ nhạt** = khoảng 売価No.1–9 (giá thường, §5.3), nhãn **KM** + giá 売価No.10 khi KOME đang có khuyến mãi, **vạch trắng** = thực bán 90 ngày (khi giá
    đang chọn không phải thực bán).
  - **Thu gọn**: mặc định KOME + 5 mặt hàng rẻ nhất + mọi mặt hàng cùng thương hiệu. Còn lại gom vào
    "xem thêm n mặt hàng ▾".
- **B · Chấm**: mỗi nhóm một dòng, mỗi chấm một mặt hàng, trục = % so giá KOME (vạch 0 = KOME). Đuôi đứt
  nối từ giá 1 thùng khi rẻ đi nhờ mua nhiều.
- **C · Bảng nhiệt**: nhóm × đối thủ. Ô lấy mặt hàng cùng thương hiệu rẻ nhất, không có thì lấy khác
  thương hiệu rẻ nhất. "·2" = bên đó có 2 mặt hàng; ô nổi liệt kê hết.
- **Ô nổi** (§1 #7):
  - Tên bên, tên hàng, quy cách gốc, nhãn thương hiệu / đang hết / khuyến mãi.
  - 3 ô: gói / thùng · tịnh 1 gói · 1 thùng (kg), mỗi ô kèm số của KOME.
  - Bảng bậc giá đúng như bảng giá của bên đó ghi ("từ 24 kg", "từ 5 thùng", "giá pallet"): ¥/gói ·
    ¥/thùng · ¥/kg · so KOME. Bậc đang áp dụng cho "Khách mua" tô đậm. Không có bậc thì một dòng "mọi số
    lượng" kèm câu "Bên này không ghi giá bậc".
  - Dòng KOME để đối chiếu.
  - Các câu nhắc khi cần: đặt tối thiểu · thùng hai bên khác cỡ, nên so ¥/kg · thuế không rõ · giá cũ.
  - Dòng nhỏ cuối: giá gốc nguyên văn, chữ bậc giá gốc, kênh, ngày nguồn.
- **Bấm** thanh / chấm / ô / "?" → pop-up sửa mặt hàng (§4.7).

### 4.3 Đối thủ
- **Hàng chip 19 bên**, mặc định là bên có nhiều mặt hàng trùng KOME nhất. Không còn trạng thái "chọn
  đối thủ" trống.
- Đầu trang: tên · ngày bảng giá mới nhất · số dòng · mở file gốc (§11 ĐT gốc) · **✎ sửa thông tin bên**.
- **4 ô số**: mặt hàng trùng KOME · rẻ hơn KOME > 5% · đang hết · khuyến mãi.
- **"Giá bên này so với KOME, từng sản phẩm"**: thanh lệch trái / phải quanh vạch KOME, màu thương hiệu
  §3.2, % theo luật màu §3.1. Bấm → pop-up sửa.
- Bên cạnh:
  - "Bán mạnh ngành nào" (thanh);
  - "Điều kiện bán" (chip ship / thuế / thanh toán / khuyến mãi chung — bấm để sửa, "+ thêm điều kiện");
  - "Khách đang mua của bên này" (Đợt 2, giữ nguyên);
  - lịch sử giá từng hàng qua các tháng (giữ từ ĐT gốc, dạng đường nhỏ khi có ≥ 2 tháng).

### 4.4 Tin thị trường
- **Đối thủ đang hết hàng KOME có**: thẻ có hình, chip tên bên (bấm → pop-up sửa, ví dụ đổi Hết → Còn).
- **Khuyến mãi đang chạy**: thẻ gom theo bên, 4 dòng đầu + "+ n khuyến mãi khác". Mỗi dòng bấm → pop-up sửa.
- **Tin hiện trường 30 ngày** (Đợt 2): đối thủ / hàng / tỉnh được nhắc, dạng thanh. Trống thì một câu.

### 4.5 Phí & giao hàng
- **Đơn mẫu**: giá trị đơn (¥8,000 · ¥15,000 · ¥25,000 · ¥60,000) · số thùng (1 · 2 · 4) · giao tới
  (Kanto·Kansai·Chubu · Tohoku · Hokkaido · Kyushu · Okinawa) · trả tiền (Daibiki · Chuyển khoản).
- **"Khách phải trả thêm bao nhiêu cho đơn này"**:
  - thanh ghép ship (cam) + phụ phí vùng (vàng) + daibiki (tím) cho mỗi bên; KOME có viền đỏ;
  - nhãn "rẻ hơn / đắt hơn KOME ¥…" theo luật màu §3.1;
  - phần không rõ = ô "?" đứt nét; bên không giao tới vùng đó → "không giao …";
  - "bao ship" = phí đã nằm trong giá hàng (tab So sánh đã so giá đó, dấu 🚚 §3.5).
- **Bảng điều kiện**: Phí ship · Miễn ship từ · Phụ phí vùng · Phí daibiki · Ghép kiện · Kiện tối đa ·
  Giá gồm thuế. Dòng KOME ở đầu. Ô nào cũng bấm được (pop-up §4.7).
- Cách tính phí của đơn mẫu: §5.4.

### 4.6 Dữ liệu ▾
Giữ các màn đã có (Duyệt / sửa, Nhóm & quy cách, Thư mục Drive — §5.4 ĐT gốc, §11). Thêm màn **Giá KOME
lệch** (§6.3). Duyệt / sửa mở CÙNG pop-up §4.7 thay khung sửa hai cột cũ.

### 4.7 Sửa ở mọi chỗ (pop-up)
MỘT thành phần `doi_thu/SuaMatHang.tsx`, mở từ mọi chỗ hiện một mặt hàng đối thủ. Có bốn phần, lưu
bằng MỘT nút "Lưu":

| Phần | Trường | Ghi vào |
|---|---|---|
| So với [hàng KOME] | Cùng thương hiệu · Khác thương hiệu · **Không liên quan — bỏ khỏi nhóm** | `app.ghep_hang` (`nhan` = `cung_hang`/`thay_the`/`khong`) — đã có, `dat_ghep` |
| Tình trạng & khuyến mãi | Còn · Hết · Sắp về · ô khuyến mãi · giá trước khuyến mãi | `app.dinh_chinh_gia` (`trang_thai`, **`khuyen_mai`, `gia_truoc_km`** — thêm vào `TRUONG_SUA`) |
| Quy cách | gói / thùng · tịnh 1 gói (g) → tự tính "1 thùng = … kg" | `app.dinh_chinh_gia` (**`so_goi_thung`, `kl_goi_g`** — §5.1) |
| Giá | giá ĐÚNG như bảng in + đơn vị (gói / thùng / kg) + thuế + các bậc "từ [n] [thùng / kg / gói] → [giá]" (thêm / xoá bậc) | đụng vào giá thì hỏi **"Vì sao đổi giá?"**: *Máy đọc sai* → `app.dinh_chinh_gia` (`gia_goc`, `don_vi_gia`, `thue`, **`bac`**) · *Giá đã đổi* → `app.gia_doi_thu_tay` (loại nguồn bắt buộc + link bằng chứng tuỳ chọn, §11) |

- Ô giá nhập **nguyên văn như bảng in**, kèm đã gồm thuế / chưa thuế. Máy quy đổi ở `mart`. Không bao giờ
  nhập ¥/kg.
- Cuối pop-up có **"Lịch sử sửa (n)"**, mở ra xem được: từng lần sửa (ai · lúc · đổi gì) và dòng gốc "Claude
  đọc từ bảng giá · ngày". Nguồn: `app.doi_thu_nhat_ky` theo `doi_tuong`. Lấy qua
  `GET /api/doi-thu/lich-su?doi_tuong=` (1 lượt), chỉ tải khi mở pop-up.
- Lưu xong: pop-up đóng, dòng đó mang dấu ✎, mọi tab (và khối ở `/san-pham/{mã}`) thấy số mới. Ảnh chụp
  đổi nhờ `app.doi_thu_nhat_ky` đã có trong `_PHIEN_BAN`. Bảng `app` mới của §5 phải vào `_PHIEN_BAN`
  hoặc ghi nhật ký cùng giao dịch (nếp 064).
- **Bỏ khỏi nhóm** thì dòng biến mất khỏi biểu đồ. Dưới biểu đồ có "Đã bỏ khỏi nhóm: … **hoàn tác**"
  (hoàn tác = ghi lại `nhan` cũ).
- **Pop-up nhỏ** cùng khung: *Điều kiện bán* (loại · nội dung · "không còn đúng — bỏ đi") · *Thông tin
  bên* (tên hiển thị · web · ghi chú, sửa `app.doi_thu`) · *Điều kiện giao hàng* (các trường §5.4).
- Đóng bằng ✕ / Huỷ / Esc / bấm ra ngoài. Focus bẫy trong pop-up; `role="dialog" aria-modal="true"`.
- Mọi người đăng nhập sửa được (như ĐT gốc). `nguoi_dung_id` NULL được.

**Chống sửa đè.**
- Mỗi đối tượng sửa được có một khoá `doi_tuong`, đúng chuỗi đang ghi vào `app.doi_thu_nhat_ky`
  (`fact:<id>`, `tay:<id>`, `ghep:<bên>|<ma_hang_dt>`, `dk:<id>`, `giao:<bên>`, `ben:<bên>`).
- Dữ liệu mỗi mặt hàng mang `sua_cuoi` = `max(id)` nhật ký của khoá đó. POST gửi lại `da_xem = sua_cuoi`.
- Máy chủ, trong CÙNG giao dịch ghi: nếu có dòng nhật ký mới hơn `da_xem` cho khoá đó → **409**, kèm
  {ai, lúc, đổi gì}. Pop-up hỏi: "Hải vừa sửa lúc 14:02: … — **Ghi đè** / **Giữ bản của Hải**".
- Ghi đè = gửi lại với `ghi_de: true`. Không có khoá / không có nhật ký → coi như 0.
- Lần sửa sau thắng, nhưng không mất gì: mọi bảng sửa vẫn CHỈ THÊM.

## 5. Dữ liệu mới

Luật ĐT gốc §4 giữ nguyên: `core` = nạp qua cổng, `app` = web ghi (chỉ thêm với đính chính), `mart` =
định nghĩa. Migration mới từ `065`. Migration chạy bằng `postgres` qua `db/migrate.py`, không qua SQL
Editor.

### 5.1 Quy cách gói của đối thủ
`core.fact_gia_doi_thu` thêm `so_goi_thung integer` và `kl_goi_g numeric(10,2)`, cả hai NULL được. Claude
đọc từ quy cách lúc dựng gói (`scripts/goi_doi_thu.py` kiểm: nguyên dương, `kl_goi_g` ≤ 30000). `mart`:
- `kg_thung_dt` = `kg_moi_don_vi_gia` khi giá theo thùng; không thì `so_goi_thung × kl_goi_g / 1000`;
  không đủ → NULL.
- `gia_goi` / `gia_thung` (¥ chưa thuế) suy từ `yen_chuan` và quy cách; thiếu → NULL, không đoán.

Đo trên bản phác tháng 8: đọc tạm bằng regex ra 492/573 mặt hàng có tịnh 1 gói, 414/573 có gói/thùng.
Bản thật do Claude đọc, phần còn lại sale điền qua "?".

### 5.2 Giá bậc có cấu trúc
Hôm nay `gia_bac` là chữ tự do (257 dòng tháng 8, mỗi bên một kiểu: "5cs: 5,300",
"25kg: 600y/kg | 50 kg: 580y/kg", "530¥/kg x 24kg; 510¥/kg x 48kg").
- `core.fact_gia_doi_thu` thêm **`bac jsonb`**: mảng `[{"tu": 5, "don_vi_sl": "thung"|"kg"|"goi"|"pallet", "gia": 5300,
  "don_vi_gia": "thung"|"kg"|"goi"}]`, cùng `thue` của dòng. CHECK `jsonb_typeof(bac) = 'array'`. Chữ
  `gia_bac` giữ lại làm nguyên văn.
- `gia_goc` = giá mua LẺ nhỏ nhất (1 thùng / 1 đơn vị). Gói KHÔNG được ghi bậc rẻ nhất vào `gia_goc`
  (lỗi thấy ở Vietnam House, NEXT tháng 8).
- `mart.gia_doi_thu_hien_hanh` thêm **`gia_1`, `gia_5`, `gia_10`, `gia_pallet`** (¥/kg chưa thuế tại số
  lượng đó). Giá tại N thùng = bậc rẻ nhất có `tu` ≤ N (quy `kg` → thùng bằng `kg_thung_dt`; `pallet` chỉ khi
  bảng ghi rõ pallet — dòng `muc_gia = 'pallet'` hoặc bậc `don_vi_sl = 'pallet'`, KHÔNG đoán "1 pallet = 40
  thùng"). Không có bậc nào áp → giá lẻ. Viết MỘT lần trong mart; trình duyệt chỉ chọn cột.
- `gia_pallet` NULL mà vẫn chọn "1 pallet" → dùng giá lẻ, và ô nổi ghi "bên này không ghi giá pallet".
- Sửa: `app.dinh_chinh_gia` với `truong = 'bac'`, `gia_tri_moi` = JSON. `doi_thu._kiem` kiểm đúng lược đồ
  trên (≤ 10 bậc, `tu` > 0, `gia` > 0).
- `trung_vi` / `thap_nhat` / `bat_thuong` của `mart.so_sanh_nhom` vẫn tính trên **giá lẻ** (`gia_1`), như cũ.
  "Khách mua" chỉ đổi cái được VẼ và % so KOME, không đổi thống kê nhóm (ⓘ nói ra).

### 5.3 標準価格 của KOME
- `取引単価データ` có `標準価格（税抜）` / `標準価格（税込）`, nhưng bộ nạp `tanka` bỏ qua. Đo file 2026-09-08:
  235 dòng có giá gồm thuế, 4 dòng có giá chưa thuế. `config/files.yml::tanka` thêm hai cột.
- `kome/loaders/price.py` xoay thành `price_level = 'std'`: cùng bảng `core.fact_price_list`, khoá chính
  đã gồm `price_level`, text.
- Mọi chỗ đọc `fact_price_list` theo 売価No phải lọc hoặc gắn nhãn `'std'`. Hôm nay có ba chỗ:
  `san_pham_360.py` (giá bậc, hiện nó là dòng đầu "標準価格"), `mart.sp_*` giá bậc, và khối cảnh báo bán dưới
  giá nếu có. Test canh: không chỗ nào hiện "売価No.std".
- `mart.gia_kome_chuan(ma)` → ¥/kg chưa thuế: giá chưa thuế nếu > 0, không thì giá gồm thuế ÷ 1,08, của
  pack thùng (`02`), ÷ kg/thùng từ `mart.quy_cach_kome`. Không có → NULL.
- `mart.so_sanh_nhom` thêm `gia_kome_chuan` và `gia_kome_bang` (jsonb 売価No → ¥/kg, cho dải đỏ nhạt).
- **売価No.10 = giá khuyến mãi của KOME** (chủ DN, 2026-09-29). Nó KHÔNG vào dải giá thường, và không bao giờ là
  mặc định. Ô chọn ghi "売価No.10 · khuyến mãi". Dòng KOME mang nhãn **KM** (như đối thủ) khi có giá No.10 > 0
  và thấp hơn 標準価格; ô nổi in giá đó. Định nghĩa MỘT lần: `mart.la_gia_km_kome(price_level)` (= `'10'`).
  **"Vị trí KOME", `ty_le_re_hon_kome` và chấm "KOME đứng đâu" tính trên 標準価格, không có thì thực bán**
  (ⓘ nói ra). `gia_kome` (thực bán 90 ngày) giữ nguyên nghĩa.
- Dữ liệu lạ để chủ DN kiểm ở OBC (không sửa ở đây): nhiều dòng 売価No có giá chưa thuế = 0; NT01 売価No.10
  (giá khuyến mãi) ghi chưa thuế ¥5,900 nhưng gồm thuế ¥4,900 — có thể một cột chưa cập nhật khi đổi giá
  khuyến mãi. Khi hai cột mâu thuẫn (gồm thuế < chưa thuế), màn dùng giá gồm thuế ÷ 1,08 và ô nổi ghi "bảng giá
  OBC hai cột lệch nhau".

### 5.4 Điều kiện giao hàng có cấu trúc
Hôm nay `core.fact_dieu_kien_doi_thu` là chữ tự do. Tab §4.5 cần số.
- **`core.fact_giao_hang_doi_thu`** (nạp, một dòng mỗi bên mỗi lô, sheet `giao_hang` của gói — file spec
  `doi_thu_giao_hang`, cùng ô nạp "Bảng giá đối thủ", `LOADERS`/`UNDO_TABLES`/mọi danh mục như §4.1 ĐT gốc):

  | Cột | Nghĩa |
  |---|---|
  | `bao_ship` bool | phí ship đã nằm trong giá hàng |
  | `phi_ship` numeric, `phi_ship_theo` ∈ `don`/`thung`/`kien` | phí khi không miễn |
  | `mien_ship_tu` numeric | miễn ship khi đơn ≥ ¥ |
  | `mien_ship_kien` int | … hoặc khi đủ n kiện |
  | `phu_phi` jsonb | `{"hokkaido": 800, "okinawa": "khong_nhan", "tohoku": 400, "kyushu": …}` — ¥ mỗi kiện |
  | `phi_daibiki` numeric | |
  | `daibiki_tu`, `daibiki_sau` numeric | từ ¥… thì phí daibiki còn … (0 = miễn) |
  | `ck_mien_daibiki` bool | chuyển khoản trước thì không phí daibiki |
  | `kien_toi_da_kg` numeric, `ghep_kien` text | ghép kiện |
  | `thue` ∈ `bao`/`chua`/`khong_ro` | giá hàng đã gồm thuế |
  | `cach_gui` text | phí gửi / cách gửi khác (宅急便, lấy tại kho, phí lạnh) |
  | `nguon_chu` text | câu gốc, để đối chiếu |

  Mọi cột số NULL = "không ghi" ("?"). NULL không bao giờ là 0.
- **KOME**: `app.giao_hang_kome` (một dòng, cùng cột, sửa được, ghi `app.doi_thu_nhat_ky` loai `giao_hang`
  cùng giao dịch). Khởi tạo bằng số SUY từ phiếu bán, chủ DN xác nhận ở pop-up:
  - `配送料500` có trên 985 đơn trong 180 ngày, mọi đơn đó dưới ¥20,000 → ship ¥500/đơn, miễn từ ¥20,000;
  - `代引手数料330（２万円未満）` / `代引手数料300（２万円以上）` → daibiki ¥330, từ ¥20,000 còn ¥300.

  Trước khi xác nhận, dòng KOME mang nhãn "suy từ phiếu bán". View `mart.giao_hang_kome_bang_chung` giữ
  phép đếm đó để ⓘ in ra.
- **Sửa của sale**: `app.dinh_chinh_giao_hang` (`ma_doi_thu`, `lo_id`, `truong`, `gia_tri_moi`, người,
  lúc) — CHỈ THÊM (`REVOKE UPDATE, DELETE` khỏi `kome_app`). `mart.giao_hang_hien_hanh` = lô mới nhất của
  bên + đính chính mới nhất từng trường. KOME đọc `app.giao_hang_kome`.
- **Phí của đơn mẫu**: MỘT thuật toán, hai bản (nếp `nen` / `squarify`): `kome/phi_giao.py::tinh` và
  `giao_dien/src/doi_thu/phi_giao.ts::tinh`, chạy CHUNG `tests/du_lieu/phi_giao_ca.json`. Vào: điều kiện
  một bên + (tiền, thùng, vùng, trả). Ra: `{ship, vung, daibiki, chua_ro: [...], khong_nhan}`. Luật:
  - miễn ship khi `tien ≥ mien_ship_tu` hoặc `thung ≥ mien_ship_kien`;
  - phí theo thùng × số thùng;
  - phụ phí vùng × số kiện (kiện = ⌈thùng ÷ thùng/kiện⌉, không biết thì 1 kiện);
  - daibiki chỉ khi trả daibiki;
  - trường NULL mà cần tới → vào `chua_ro`, không cộng 0.
  Trình duyệt tính vì phải đổi ngay khi bấm (ngoại lệ có chủ ý, như `/mua-vu`).
- **Tách ghi chú nội bộ**: câu Claude tự ghi lúc đọc ("chép vào ghi_chu từng dòng", "không in thông tin
  thuế", "Dữ liệu này KHÔNG có phí ship…") KHÔNG được vào `fact_dieu_kien_doi_thu`. Chúng vào cột
  `ghi_chu_doc` (mới, không hiện ở tab Đối thủ / Tin), hoặc sổ tay theo bên. `goi_doi_thu.py` từ chối dòng
  `dieu_kien` có dấu hiệu ghi chú của người đọc (danh sách mẫu, có test).
- **Sửa điều kiện bán** (chip ở tab Đối thủ): `app.dinh_chinh_dieu_kien` (`fact_id` | NULL cho dòng thêm
  tay, `loai`, `noi_dung`, `bo` bool, người, lúc) — CHỈ THÊM.

### 5.5 "Tính cả phí giao" (tab So sánh, tắt mặc định)
Bật thì mỗi giá (KOME và đối thủ) cộng phần phí của một đơn gồm đúng số thùng đang chọn của mặt hàng đó
(Kanto, trả daibiki), chia theo kg (`phi_giao.tinh`). Bên có `chua_ro` thì thanh mang dấu "?" và không cộng.
Bên bao ship thì không cộng gì (đã trong giá).

## 6. Sửa dữ liệu đi kèm

### 6.1 Đọc lại tháng 8
Claude đọc lại, trong phiên, các file tháng 8 đã có trên Drive: gói/thùng, tịnh 1 gói, bậc có cấu trúc,
`gia_goc` = giá lẻ, điều kiện giao hàng, tách ghi chú đọc. Gói mới nạp thành lô mới: lô mới thắng ở `mart`,
lô cũ còn để hoàn tác. `app.ghep_hang` theo `ma_hang_dt` nên ghép cũ tự áp. `app.dinh_chinh_gia` trên CSDL
thật hôm nay có 0 dòng, nên không có đính chính nào bị mồ côi.

### 6.2 Sổ tay đọc
`docs/doi-thu/huong-dan-doc.md` + `so-tay-theo-ben.md` thêm: cột mới §5.1–5.4, "cùng thương hiệu" (§3.2),
"`gia_goc` = giá lẻ", "không ghi ghi chú của người đọc vào điều kiện".

### 6.3 Giá KOME lệch (15 nhóm)
- 15 nhóm có giá KOME > 3× trung vị, ví dụ Xốt Barona thịt nướng sả: KOME ¥78,403/kg, trung vị ¥845.
- **Nguyên nhân (đo 2026-09-29)**: các mã xốt Barona / HVX / DK20 bán bằng pack `00` (バラ). Doanh thu ÷
  số lượng ≈ ¥6,266 mỗi đơn vị `00`, tức **một đơn vị `00` của các mã này là cả thùng**
  (80g × 20 × 4 = 6,4 kg → ≈ ¥979/kg, sát thị trường). Còn `mart.gia_kome_kg` đang coi `00` = 1 gói 80g.
- Sửa:
  1. `mart.quy_cach_kome` tách được dạng ba thừa số "80g x 20 packs × 4box" (`kg_moi_thung` =
     80 × 20 × 4 g);
  2. kg của MỘT đơn vị theo `pack_code` đọc từ 商品データ của OBC (`荷姿１..４－基準単位当り荷姿区分数` /
     `入数`), thay cho giả định "00 = 1 gói". Việc 2 cần đo file thật trước khi viết: cột có đủ và đúng
     không. Không đủ thì dừng ở việc 1 + sửa tay;
  3. màn **Dữ liệu › Giá KOME lệch** liệt kê nhóm có giá KOME > 3× hoặc < ⅓ trung vị, kèm nút sửa quy cách
     (`/api/doi-thu/quy-cach` đã có).
- Test canh: một mã bán bằng `00` = thùng ra đúng ¥/kg.

## 7. API và ngân sách lượt hỏi

| Endpoint | Đổi | Trần |
|---|---|---|
| `GET /api/doi-thu/tong-quan` | + dữ liệu Tóm tắt (4 ô số, điểm "đứng đâu", cơ hội, khuyến mãi theo bên) | 1 lượt + phiên bản |
| `GET /api/doi-thu/so-sanh` | + `gia_1/5/10/pallet`, `so_goi_thung`, `kl_goi_g`, `kg_thung_dt`, `bac`, `gom_ship`, `sua_cuoi`, `gia_kome_chuan`, `gia_kome_bang` | 1 |
| `GET /api/doi-thu/ben/{ma}` | + mặt hàng so KOME, điều kiện có `id` để sửa | 1 |
| `GET /api/doi-thu/giao-hang` (mới) | điều kiện hiện hành các bên + KOME + bằng chứng KOME | 1 |
| `GET /api/doi-thu/lich-su?doi_tuong=` (mới) | nhật ký của một đối tượng | 1, không ảnh chụp |
| `POST /api/doi-thu/sua-mat-hang` (mới) | pop-up §4.7: ghép + đính chính + (giá đã đổi) trong MỘT giao dịch, kèm `da_xem` / `ghi_de` | — |
| `POST /api/doi-thu/giao-hang` · `/dieu-kien` · `/ben` (mới) | pop-up nhỏ | — |

POST vẫn chỉ nhận JSON (thân không phải object → 400). Mỗi GET vẫn 1 lượt, có test đếm
(`NGAN_SACH_TRUY_VAN`). Endpoint POST cũ (`/sua`, `/xac-nhan`, `/gia-moi`, `/ghep`) giữ cho màn Duyệt.

## 8. Chia đợt con

| Đợt | Gồm |
|---|---|
| **4a · dữ liệu** | 065+ : §5.1 · §5.2 · §5.3 (bộ nạp tanka + `std`) · §5.4 (bảng + bộ nạp + app + `phi_giao` hai bản) · §6.3 việc 1 (+ việc 2 nếu file đủ) · `TRUONG_SUA` mới · gói/sổ tay §6.2 · đọc lại tháng 8 (§6.1, trong phiên) |
| **4b · giao diện** | §2 · §3 · §4.1–4.4 · §4.6 · §4.7 kèm chống sửa đè · lịch sử sửa |
| **4c · phí & giao hàng** | §4.5 · §5.5 |

Làm theo thứ tự: 4b cần cột của 4a; 4c cần §5.4.

## 9. Kiểm thử

Test mới (tên rõ, mỗi bất biến một test):
- `mauLech`: đối thủ rẻ hơn KOME ⇒ đỏ, ở MỌI cách vẽ (test TS). Tên ngành: 8/8 ngành có tên Việt, mã lạ
  giữ nguyên văn.
- `gia_1/5/10/pallet`: bậc `kg` quy thùng đúng · không bậc → giá lẻ · pallet không đoán · thuế ÷ 1,08
  đúng một lần · `bac` sửa qua `dinh_chinh_gia` thắng bậc đã nạp.
- Thống kê nhóm (`trung_vi`, `bat_thuong`) KHÔNG đổi theo số lượng (vẫn trên giá lẻ).
- `gia_kome_chuan`: chưa thuế > 0 thắng · gồm thuế ÷ 1,08 · thiếu kg → NULL · `'std'` không lọt vào mọi
  danh sách 売価No · 売価No.10 không vào dải giá thường, nhãn KM chỉ khi thấp hơn 標準価格 · hai cột mâu thuẫn →
  gồm thuế ÷ 1,08.
- `phi_giao`: hai bản cùng kết quả trên `phi_giao_ca.json` (miễn theo tiền / theo kiện, phụ phí vùng × kiện,
  không nhận, daibiki có ngưỡng, CK trước, NULL → `chua_ro` chứ không 0).
- Chống sửa đè: sửa với `da_xem` cũ → 409 kèm người / lúc; `ghi_de` → ghi; không nhật ký → ghi.
- Pop-up một giao dịch: ghép + ba đính chính + giá đã đổi, hỏng một phần → không phần nào vào.
- Mọi bảng `app` mới chỉ thêm (`kome_app` không UPDATE / DELETE); nằm trong `_PHIEN_BAN` hoặc ghi nhật ký
  cùng giao dịch.
- Gói: từ chối điều kiện là ghi chú của người đọc; `gia_goc` không được nhỏ hơn mọi bậc.
- §6.3: mã bán bằng `00` = thùng ra đúng ¥/kg.
- `?tab=tong_quan` cũ mở Tóm tắt; lựa chọn So sánh còn nguyên sau khi đổi khoảng xem.
- Build SPA (`test_ban_build_khop_ma_nguon`), CLAUDE.md thêm bất biến 065+.

Kiểm trên trình duyệt (CSDL tạm, số liệu thật chép chỉ đọc): cả 5 tab · 3 cách vẽ · ô nổi · pop-up từ mọi
chỗ · 409 · bàn phím · 1440 px và 375 px (điện thoại chỉ cần xem được).

## 10. Không làm (có chủ ý)

- Câu kết luận mỗi sản phẩm (§1 #10).
- Đoán "1 pallet = 40 thùng" hay đoán phí ship khi bảng giá không ghi.
- Giá theo số lượng cho KOME: bảng giá KOME theo loại khách (売価No), không theo số lượng. "Khách mua"
  chỉ đổi giá đối thủ.
- Gọi AI từ web; lưu ảnh / file gốc (§11 ĐT gốc).
- Thiết kế riêng cho điện thoại.
