# Đặc tả thiết kế — Lộ trình dựng 24 màn hình từ gói thiết kế Kome

**Ngày:** 2026-09-21
**Công ty:** 株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật
**Phạm vi tài liệu:** phân rã gói thiết kế 24 màn hình (`design_handoff_kome`) thành
các đợt làm được, chốt công nghệ giao diện, và xác định những quyết định còn treo.
**Trạng thái:** Chờ duyệt
**Tài liệu liên quan:**
- `docs/superpowers/specs/2026-09-16-kome-data-platform-design.md` — gọi tắt **"đặc tả nền"**
- `docs/superpowers/specs/2026-09-17-dashboard-nguoi-dung-crm-dot-1-design.md` — gọi tắt **"spec đợt 1"**

Tài liệu này **không** thay thế hai tài liệu trên. Nó là tài liệu phân rã: chia một
gói thiết kế lớn thành các đợt, mỗi đợt về sau có đặc tả và kế hoạch riêng.

---

## 1. Bối cảnh

Gói `design_handoff_kome` gồm một `README.md` handoff và 24 màn hình prototype
(`.dc.html`) kèm 7 file dùng chung. Prototype là HTML + JS, style inline toàn bộ, dữ
liệu mẫu hard-code. README nói rõ đây là **bản thiết kế tham chiếu**, không phải code
production, và đề nghị dựng lại trong codebase đích.

Hiện trạng codebase: Giai đoạn 0+1 đã chạy (nạp dữ liệu từ OBC, `core`/`mart`, 8 trang
web FastAPI + Jinja). Spec đợt 1 (Giai đoạn 2) đã viết nhưng **chưa triển khai** —
migration `017` trong repo là `017_nguon_ban_hang_thay_the.sql`, nội dung khác hẳn.

Gói thiết kế bao trùm cả bốn giai đoạn của đặc tả nền cùng lúc. Việc đầu tiên phải làm
với nó là **phân rã**, không phải dựng.

---

## 2. Quan hệ với spec đợt 1

Đã đối chiếu từng mục. Spec đợt 1 **không bị thay thế** — nó bị **tách làm đôi** theo
lộ trình ở §7:

| Phần của spec đợt 1 | Đi vào |
|---|---|
| Đăng nhập theo người dùng, `core.dim_salesperson`, `app.nguoi_dung`, lọc theo `salesperson_code`, vé ký không trạng thái (§5.1, §5.3, §5.4) | **Đợt 3** |
| `mart.uu_tien_lien_he`, `app.nhat_ky_cham_soc` (§5.5, §5.6) | **Đợt 7** |
| Dashboard bố cục cố định theo vai trò (§2) | **Đợt 5** |

Ba sửa đổi so với bản đã viết, mỗi cái có lý do ở §8:

1. **Thêm cột `dashboard_mac_dinh`** vào `app.nguoi_dung` (§8.3). Cột `vai_tro` và
   CHECK của nó giữ nguyên.
2. **Enum `kenh` thêm `email`** — thiết kế có kênh thư, spec chưa có. Không lấy
   `sign`/`mat` của thiết kế vì đó không phải kênh liên hệ mà là giai đoạn của một cơ
   hội bán; chúng thuộc Kanban (§8.2), không thuộc nhật ký chăm sóc.
3. **Kanban cơ hội bán không vào đợt 7** — xem §8.2.

Chín điểm lệch đã đối chiếu đầy đủ; ba điểm nặng nhất (bố cục dashboard, công nghệ
frontend, CRM là hai thực thể khác nhau) được giải quyết ở §6, §7 và §8.2. Các điểm
còn lại không tạo mâu thuẫn: màn Đăng nhập của thiết kế im lặng về cơ chế, nên vé ký
không trạng thái của spec đợt 1 §5.1 vẫn dùng được nguyên.

---

## 3. Ràng buộc kế thừa

**R1–R6** của đặc tả nền §3 áp dụng nguyên vẹn. Ba ràng buộc chi phối tài liệu này
mạnh nhất:

- **R1** — công ty không có nhân sự IT → giảm tối đa số thứ có thể hỏng.
- **R2** — bảo trì bằng AI, chủ sở hữu là một người → "công nghệ phổ thông, schema
  tường minh, không ma thuật, mọi logic nằm trong file đọc được và lưu git".
- **R5** — vòng đời 5 năm → không khoá chân nhà cung cấp.

Cộng thêm mọi bất biến đã ghi trong `CLAUDE.md`: mã là TEXT, OBC chỉ đọc, mốc thời
gian là ngày bán mới nhất trong kho (trừ ô tuổi dữ liệu), trạng thái khách so với nhịp
mua riêng từng khách, khách `※廃業※` không vào danh sách gọi lại, `app.py` không nhập
`kome.pipeline` ở mức ngoài cùng, cổng 6543 tắt câu lệnh chuẩn bị sẵn.

---

## 4. Phạm vi

### 4.1 Hai mươi bốn màn, phân loại theo nguồn dữ liệu

| Nhóm | Màn | Trạng thái dữ liệu |
|---|---|---|
| **A — dựng được ngay** | Dashboard · Báo cáo · Dự báo · Customer 360 · Kho hàng · Sản phẩm · Kho dữ liệu · Bản đồ khách hàng | `core`/`mart` đã có |
| **B — OBC có file, chưa có bộ nạp** | Công nợ & thu tiền · Dòng tiền & phải trả | `得意先元帳`, `請求先元帳` — `kome/coverage.py:85-86` ghi "1 quý, chưa có bộ nạp" |
| **C — không có ở đâu, phải nhập mới** | Báo giá · Lên đơn hàng · Giao hàng · Mua hàng & NCC · Trả hàng & khiếu nại · Hiệu suất đội sale · CRM cơ hội bán | dữ liệu giao dịch hoặc nhập tay hoàn toàn mới |
| **D — hạ tầng** | Đăng nhập · Cài đặt · Nhật ký thao tác | một phần có (`meta.ingest_batch`) |
| **Cắt** | Web đặt hàng khách · Mẫu chứng từ · Thị trường & đối thủ · Sale mobile | §4.2 |

**Màn CRM (số 6) nằm ở nhóm C nhưng vẫn có đợt.** Thiết kế của nó là Kanban cơ hội bán
— 100% nhập tay, thuộc nhóm C. Nội dung đợt 7 là thứ **khác**: danh sách ưu tiên liên
hệ suy ra từ `mart.khach_360`, thuộc nhóm A. Lý do đổi ở §8.2.

**Trang `/can-xu-ly` hiện có không có màn tương ứng trong thiết kế.** Chức năng của nó
tách làm hai: phần lọc theo trạng thái vào "Danh sách làm việc" của Customer 360
(đợt 4), phần "ai cần gọi hôm nay" vào đợt 7. Route cũ giữ nguyên cho tới hết đợt 4,
bỏ khi đợt 7 xong — không bỏ sớm hơn, vì đó là trang đang được dùng.

### 4.2 Bốn màn cắt khỏi phạm vi, và vì sao

- **Web đặt hàng khách** — đặc tả nền §4.1 xếp vào Giai đoạn 3, và công ty **đã có hai
  app đặt hàng đang chạy**. Xây lại trước khi phần còn lại ổn định là đổi một thứ đang
  hoạt động lấy một thứ chưa chắc.
- **Mẫu chứng từ** — OBC đã in được phiếu giao hàng và hoá đơn. Giá trị thấp nhất
  trong 24 màn.
- **Thị trường & đối thủ** — đặc tả nền §4.1 đã quyết gộp vào CRM, vì "thực chất chỉ
  là vài bảng nhập tay".
- **Sale mobile** — màn duy nhất chạm React thật (`Sale mobile.dc.html`; 23 màn còn
  lại không có chỗ nào). Bản desktop là chuẩn nghiệp vụ; làm bản điện thoại trước khi
  chuẩn đó ổn định là làm hai lần.

Phạm vi còn **20 màn**: 14 màn có đường đi rõ ràng (§7), 6 màn nằm sau một quyết định
kinh doanh (§8.1).

### 4.3 Ngoài phạm vi tài liệu này

Đặc tả chi tiết của từng đợt (mỗi đợt có tài liệu riêng), kế hoạch triển khai, và mọi
thay đổi pipeline nạp ngoài đợt 6.

---

## 5. Quyết định đã chốt qua thảo luận

| Câu hỏi | Quyết định | Vì sao |
|---|---|---|
| Công nghệ giao diện | **Giữ FastAPI + Jinja, thêm `static/`**, JS thuần khi cần. Không npm, không bundler | R2: hệ thống được bảo trì bằng AI, một mình chủ sở hữu. Repo không build step, mọi thứ là file text đọc được, là điều kiện để điều đó còn đúng sau 5 năm |
| Nhóm C có phá Luật số một không | **Không** — đặc tả nền R3 đã lường trước: "đơn từ app phải quay về OBC" | Công ty đã có hai app nhận đơn; đơn từ chúng đã quay về OBC bằng cách nào đó. Luật chỉ bị phá nếu đơn nằm lại trong hệ thống này |
| Font | **Tự host IBM Plex trong `static/`; chữ Nhật dùng font hệ thống** | R1: một CDN ngoài là một thứ có thể hỏng mà không ai trong công ty sửa được — và chữ Nhật trong tên 得意先 mất font sẽ hỏng ở chỗ khó nhận ra nhất |
| Mã hoá bằng màu | **Giữ bất biến "màu + chữ"** đã ghi ở `_chung.html:76-77` | ~1/12 nam giới không phân biệt đỏ với xanh lá; tooltip `title` của thiết kế không tới được bằng bàn phím và không tồn tại trên điện thoại |
| Vai trò người dùng: 2 hay 4 | **Hai cột riêng** — `vai_tro` (lọc dữ liệu) và `dashboard_mac_dinh` (mặc định hiển thị) | Hai con số trả lời hai câu khác nhau; nhét vào một cột là chỗ sinh mâu thuẫn — §8.3 |
| CRM làm hình dáng nào trước | **Danh sách ưu tiên liên hệ** trước; Kanban để sau và thu hẹp phạm vi | Khảo sát thực địa có bằng chứng người cần cái trước, không có bằng chứng nào cho cái sau — §8.2 |
| Bốn màn cắt | Web đặt hàng · Chứng từ · Thị trường · Sale mobile | §4.2 |

---

## 6. Kiến trúc giao diện

### 6.1 Điểm xuất phát

Toàn bộ màu của app nằm trong **một file, một khối**: `kome/web/templates/_chung.html`
dòng 12–31. Không template nào khác chứa một mã màu nào (đã kiểm: `grep -l` trên
`templates/*.html` chỉ trả về `_chung.html`). Hệ biến hiện có đã đặt đúng các trục
thiết kế cần — `--nen` / `--chu` / `--vien`, bộ ba `ok`/`loi`/`canh` — và đã có sẵn
thành phần dùng lại: `.the-so` (thẻ KPI), `.vien` (badge), `.loc` (tab pill),
`.bang-cuon`, `td.so` có `tabular-nums`.

Đợt 1 vì vậy **không dựng hệ token mới — mà thay giá trị và bổ sung biến còn thiếu.**

### 6.2 Ánh xạ token

| Biến | Hiện tại | Thiết kế | Ghi chú |
|---|---|---|---|
| `--nen` | `#ffffff` | `#FBF9F5` | **tách đôi**: nền trang là giấy ấm |
| `--nen-the` | — | `#FFFFFF` | biến mới — nền thẻ/bảng |
| `--nen-phu` | `#f4f6f8` | `#F6F3EC` | |
| `--vien` | `#d7dce2` | `#E6E2D9` | |
| `--vien-phu` / `--vien-dam` | — | `#F0EDE6` / `#D8D3C8` | biến mới |
| `--chu` | `#1b1f23` | `#1A1714` | |
| `--chu-thuong` | — | `#474139` | biến mới |
| `--chu-nhat` | `#5a6570` | `#6E6A63` | |
| `--lien-ket` | `#0b57d0` | `#8A5E06` | đổi sang vàng đất |
| `--ok-nen` / `--ok-vien` / `--ok-chu` | xanh lam nhạt | `#E6F2EB` / `#1E7A4D` / `#14603E` | |
| `--loi-nen` / `--loi-vien` / `--loi-chu` | `#cc0000` | `#FDEDEC` / `#D62C27` / `#B4231C` | |
| `--canh-nen` / `--canh-vien` / `--canh-chu` | `#d9a400` | `#FFF9E8` / `#E6D08A` / `#8A5E06` | |
| `--chot-*` | tím `#7a5bc0` | **bỏ** | thiết kế dùng đỏ công ty cho trạng thái chọn; tím `#4B3CAF` chỉ dành cho thanh phân bổ theo nhân viên |
| `--do` | — | `#D62C27` | **biến mới quan trọng nhất** — hệ hiện tại không có màu hành động chính nào |

Bảng tối lấy 39 cặp từ `kome-theme.js` (nền `#17140F`, thẻ `#211D17`, viền `#342E26`,
chữ `#F4EFE6`), nhưng viết thành `@media (prefers-color-scheme: dark)` như
`_chung.html` đang làm. **Không** port cơ chế quét DOM đổi màu của prototype — quét
DOM để đổi màu là đúng loại "ma thuật" R2 cấm.

Bo góc `8/10/999px` → `6/9/11/12–14/99px`. Bề rộng nội dung `1100px` → `1400px`. Đổ
bóng: cả hai bên đều không dùng, không phải đổi gì.

### 6.3 Nơi đặt

`_chung.html` tách thành `kome/web/static/kome.css`, mount `StaticFiles`. Lý do: file
sẽ đi từ ~110 dòng lên vài trăm khi có 20 màn, và trình duyệt cache được nó thay vì
tải lại theo mỗi trang. `requirements.txt` không thêm gì — `StaticFiles` nằm sẵn trong
FastAPI.

Font tự host trong `static/`: IBM Plex Sans (400/500/600/700) và IBM Plex Mono
(400/500/600), bản **đầy đủ (không subset)** — bảy file woff2, ~50-70KB mỗi
file. **Không dùng bản subset `-Latin1`**: bản đó không có glyph tiếng Việt
(đo thật bằng `canvas.measureText` — mọi ký tự có dấu rơi về font hệ thống,
dấu tách rời khỏi chữ), mà toàn bộ giao diện này là tiếng Việt. Đây là bẫy đã
vấp thật một lần khi lập kế hoạch: tên file `-Latin1` nghe như "đủ dùng cho
chữ Latin" nhưng "Latin" ở đây chỉ nghĩa là Latin cơ bản (ASCII + Tây Âu),
không phải toàn bộ chữ Latin mở rộng có dấu.

**Chữ Nhật dùng ngăn xếp font hệ thống**, không tự host Noto Sans JP. Noto Sans
JP phủ toàn bộ CJK; tự host đúng cách là hơn 200 file mảnh `unicode-range`, một
cam kết bảo trì va thẳng R1. Windows có Yu Gothic UI, macOS có Hiragino Sans —
ý đồ của thiết kế (tên 得意先 hiện bằng font Nhật thật) vẫn đạt. Nếu về sau chữ
Nhật hiện xấu trên máy thật, xem lại quyết định này trước tiên.

### 6.4 Shell điều hướng

Từ thanh ngang hai tầng (`_nav.html`) sang **sidebar 196px cố định trái, 6 nhóm** theo
`kome-nav.js`. Ghi chú thiết kế trong `_nav.html` hiện tại — "để lẫn vào tầng trên thì
mục quan trọng nhất bị đẩy xuống ngang hàng với một việc kỹ thuật" — được cấu trúc mới
giải quyết triệt để hơn: nhóm HỆ THỐNG nằm cuối sidebar, tách hẳn.

`{% include %}` tĩnh hiện tại đổi thành `{% block %}` thật — đúng việc spec đợt 1 §4.1
đã dự trù.

### 6.5 Bất biến: mã hoá bằng màu phải kèm thứ đọc được

`_chung.html:76-77` đã ghi bất biến này. Thiết kế mới dựa nhiều vào màu đơn thuần:
treemap tô theo mức tăng/giảm, nhiệt đồ 6 mức màu, ô trạng thái nạp ở màn Kho dữ liệu,
chấm bản đồ theo hạng.

**Bất biến giữ nguyên, diễn đạt lại:** mọi ô mã hoá bằng màu phải kèm một thứ đọc được
— con số, hoặc ký hiệu `▲ ▼` mà thiết kế đã quy ước sẵn cho tăng/giảm. Tooltip `title`
là bổ sung, không phải thay thế. Ngoại lệ duy nhất: ô treemap nhỏ tới mức đã tự ẩn cả
nhãn — chỗ đó chấp nhận chỉ có màu, vì nó vốn không đọc được gì.

---

## 7. Lộ trình

Nguyên tắc xếp thứ tự: mỗi đợt phải **tự đứng được** (dùng thật ngay khi xong), và
**không đợt nào làm hai việc khó cùng lúc** (vừa đổi dữ liệu vừa đổi giao diện).

| Đợt | Nội dung | Màn | Dữ liệu mới |
|---|---|---|---|
| **1** | Nền giao diện: `static/kome.css`, token §6.2, font tự host, shell sidebar. Áp lên 8 trang đang có | — | không |
| **2a** | Kho dữ liệu — phần vận hành: gộp `/nap` + `/health` + `/phu-du-lieu` thành một màn (khối "Theo ngày" 90 ngày · "Theo tháng" toàn kỳ · luồng nạp 7 ô thả file qua 5 cổng · hoàn tác lô) | 19 (một phần) | không |
| **2b** | Kho dữ liệu — phần tài liệu sống: 4 tầng · 7 nguồn từ OBC · đối chiếu bắt buộc sau mỗi lần nạp · ai là sự thật về cái gì · cạm bẫy riêng của OBC · lộ trình · ma trận khoá · file này nối đi đâu · cột trong từng file | 19 (phần còn lại) | không |
| **3** | Danh tính: đăng nhập theo người, `core.dim_salesperson`, `app.nguoi_dung`, lọc theo `salesperson_code`. Kèm Cài đặt + Nhật ký thao tác | 22·21·20 | bảng mới, không từ OBC |
| **4** | Customer 360 · Sản phẩm · Kho hàng · Bản đồ | 5·17·15·24 | bảng tra 47 tỉnh → toạ độ (tĩnh) |
| **5** | Báo cáo + Dashboard bố cục cố định theo vai trò | 2·1 | ngân sách theo người |
| **6** | Công nợ + Dòng tiền. **Đợt duy nhất động vào pipeline nạp**: viết bộ nạp `得意先元帳` / `請求先元帳` | 12·14 | 2 nguồn OBC đã có file |
| **7** | CRM: danh sách ưu tiên liên hệ + nhật ký chăm sóc | 6 (phần suy ra) | nhập tay |
| **8** | Dự báo | 3 | không |

**Nhánh có điều kiện** (§8.1): Báo giá · Lên đơn · Giao hàng · Mua hàng & NCC · Trả
hàng & khiếu nại · Hiệu suất đội sale. Sáu màn này chỉ có nghĩa khi đường về OBC đã
rõ. Không xếp số đợt.

**Đợt 2 đứng trước đợt 3–8 có chủ ý.** Màn Kho dữ liệu là màn duy nhất trong lộ trình
đang được dùng thật hằng ngày (quy trình 13:30), nó không cần dữ liệu mới, và README
của gói thiết kế gọi nó là "màn hình quan trọng nhất để hiểu mô hình dữ liệu khi dựng
backend" — làm nó sớm thì sáu đợt sau có một bản tài liệu sống để tra.

Thiết kế **đã gộp sẵn** `/nap` vào màn này: nút "＋ Nạp dữ liệu mới"
(`Kho dữ liệu.dc.html:37,186-187`), 7 ô thả file, 5 cổng kiểm trước khi ghi, hoàn tác
cả lô. Bản chạy Vercel vẫn ẩn phần nạp theo `kome/web/app.py::_chi_doc`.

**Vì sao tách 2a và 2b.** Màn 19 có 11 khối `<h2>` cộng một luồng nạp nhiều bước —
nặng nhất trong 20 màn. Nhưng hai nửa của nó khác hẳn nhau về rủi ro:

- **2a thay thế ba trang đang chạy.** Nếu hỏng thì quy trình 13:30 hỏng theo, và đó là
  việc duy nhất của hệ thống hiện đang có người phụ thuộc vào mỗi ngày.
- **2b chỉ thêm nội dung để đọc.** Không route nào đổi, không luồng nào đụng tới. Hỏng
  thì chỉ là một trang thiếu chữ.

Gộp chung là một đợt vừa thay thứ đang chạy vừa thêm chín khối mới — vi phạm chính
nguyên tắc mở đầu §7 này ("không đợt nào làm hai việc khó cùng lúc"). Tách ra thì 2a
đứng được một mình (nó là bản thay thế 1-1 cho `/nap` + `/health` + `/phu-du-lieu`),
và 2b có thể hoãn bao lâu cũng được mà không chặn đợt nào.

**Ràng buộc riêng cho 2b: tài liệu sống phải sinh ra, không chép tay.** Ma trận khoá
và bảng "cột trong từng file" suy được từ `config/files.yml` và các migration đã có.
Viết tay chúng là tạo bản sao thứ ba của sự thật, sau `CLAUDE.md` và `docs/` — và bản
sao thứ ba sẽ mục trước tiên vì không ai chạy test lên nó. Phần văn xuôi (cạm bẫy OBC,
ai là sự thật về cái gì, đối chiếu bắt buộc) thì đọc từ `docs/` sẵn có, không gõ lại
vào template. Đặc tả đợt 2b phải chỉ rõ từng khối lấy dữ liệu từ đâu.

---

## 8. Ba nhánh quyết định

### 8.1 Đường đơn hàng quay về OBC

Đặc tả nền §3 R3 đã chốt: dữ liệu OBC chỉ đọc, **đơn từ app phải quay về OBC**. Nhóm C
không phá Luật số một; nó chỉ phá nếu đơn nằm lại trong hệ thống này.

Cái chưa biết hẹp hơn nhiều — đường về là gì:

| Đường | Điều kiện | Rủi ro |
|---|---|---|
| Nhập tay lại vào OBC | không cần gì, đang làm thế | Việc đôi; mỗi lần gõ lại là một cơ hội sai |
| Xuất file cho OBC nhận (`汎用データ受入`) | **chưa kiểm chứng** bản OBC của công ty có chức năng nhận không, và nhận được chứng từ nào | Nếu có, đây là đường đúng |
| API | gần như chắc chắn không có | — |

**Quyết định:** không để nhánh này ở trạng thái chờ. Biến nó thành **một việc kiểm
chứng cụ thể** — mở OBC, xem menu `随時処理` có `汎用データ受入` không, nhận được những
chứng từ nào. Một buổi làm việc với OBC trả lời xong. Kết quả quyết định nhóm C rẻ hay
đắt, nhưng **không chặn đợt 1–5**.

### 8.2 CRM — hai quy mô, không phải hai phương án

| | Danh sách ưu tiên liên hệ | Kanban cơ hội bán |
|---|---|---|
| Đơn vị công việc | một **cuộc gọi** | một **hợp đồng** |
| Số lượng | 2.080 khách mua lặp | 7 deal trong prototype |
| Nguồn | suy ra từ `mart.khach_360` đã có | 100% nhập tay |
| Chi phí | một view SQL + một bảng ghi chú | bảng mới + kỷ luật nhập liệu của 5 người |
| Bằng chứng có người cần | **có** | **không có** |

Khảo sát thực địa (spec đợt 1 §1) liệt kê đúng bốn thứ nhân viên Hà Huy Long tự xây
bằng Excel: chấm điểm gọi khách theo số ngày im lặng · cảnh báo khách lớn giảm tốc ·
gợi ý upsell theo mặt hàng · bảng ghi chú khách. **Không có phễu giai đoạn, không có
xác suất chốt.**

Mô hình "cơ hội có giai đoạn và xác suất" (`CRM.dc.html:111-113`: 5 giai đoạn, xác
suất 20/45/75/100/0) là mô hình bán hợp đồng lớn — đúng với 7 deal mẫu trong prototype
(hợp đồng năm, mở chuỗi mới ở Nagoya), sai với một khách tạp hoá mua gạo hàng tuần.

Đáng chú ý: **danh sách ưu tiên liên hệ không có màn riêng nào trong 24 màn.** Thứ gần
nhất là "Danh sách làm việc" — một bộ lọc sẵn bên trong Customer 360. Tức là tính năng
trung tâm của spec đợt 1 bị gói thiết kế thu lại thành một bộ lọc, trong khi một thực
thể chưa ai yêu cầu (deal) được cấp hẳn một màn.

**Quyết định:** đợt 7 làm danh sách ưu tiên liên hệ + nhật ký chăm sóc như spec đợt 1
§5.5–5.6 đã viết, và cấp cho nó một trang riêng chứ không nhét vào bộ lọc. Kanban để
lại; nếu làm thì làm đúng phạm vi của nó — **hợp đồng lớn, không phải 2.080 khách**.

### 8.3 Vai trò — hai cột, không phải một

Hai con số (2 của spec, 4 của thiết kế `Dashboard.dc.html:818-821`) trả lời hai câu
khác nhau:

- Spec hỏi **"được thấy dữ liệu của ai"** — ranh giới bảo mật, có test canh "lộ dữ
  liệu khách của người khác".
- Thiết kế hỏi **"mở lên thì thấy module nào"** — mặc định hiển thị, không có hệ quả
  bảo mật nào.

Nhét cả hai vào một cột là chỗ sinh mâu thuẫn: "Kế toán" không phải sale nên không có
`salesperson_code`, nhưng CHECK của spec chỉ cho phép NULL khi vai trò là `quan_ly`.

```
app.nguoi_dung
  vai_tro            text CHECK IN ('sale','quan_ly')   -- quyết định LỌC dữ liệu
  salesperson_code   text NULL   -- NULL khi và chỉ khi 'quan_ly'
                                 -- (CHECK của spec đợt 1, giữ nguyên)
  dashboard_mac_dinh text NULL CHECK IN ('giamdoc','kinhdoanh','ketoan','kho')
                                 -- chỉ quyết định module nào hiện sẵn
```

Kế toán và Kho là `quan_ly` về mặt lọc — thấy toàn công ty, không gắn với khách nào —
nhưng `dashboard_mac_dinh` khác nhau. CHECK của spec đợt 1 còn nguyên, ranh giới bảo
mật không bị nới, và 4 vai của thiết kế vẫn có chỗ. Thêm một vai trình bày thứ năm về
sau chỉ là thêm một giá trị enum, **không** đụng logic lọc dữ liệu.

---

## 9. Dữ liệu mới không đến từ OBC

Ba thứ lộ trình cần mà OBC không xuất ra. Cả ba đều nhỏ và nhập tay; ghi ở đây để
không đợt nào phát hiện muộn.

| Dữ liệu | Đợt | Quy mô | Ghi chú |
|---|---|---|---|
| Tài khoản đăng nhập + vai trò | 3 | 5–7 dòng | Chủ sở hữu đặt mật khẩu ban đầu, như `KOME_MAT_KHAU` hiện nay |
| Bảng tra 47 tỉnh → toạ độ | 4 | 47 dòng, tĩnh | Dữ liệu công khai, nạp một lần bằng migration |
| Ngân sách theo nhân viên theo tháng | 5 | 5 người × 12 tháng | Thiết kế coi là có sẵn (`Dashboard.dc.html:827` hard-code `ns:42934553`); repo không có bảng nào. Cần một bảng `app` và một cách nhập |

Hoa hồng & thưởng (màn 4) cũng thuộc loại này nhưng nằm trong nhánh có điều kiện §8.1,
chưa cần quyết.

---

## 10. Kiểm thử

Giữ nguyên nguyên tắc đặc tả nền §9.4: không đuổi theo tỷ lệ phủ, chỉ test chỗ thật sự
nguy hiểm. Các test hiện có phải **xanh nguyên** sau mỗi đợt, đặc biệt:

- `tests/test_bao_mat.py::test_trang_chi_doc_khong_phu_thuoc_pandas` — đợt 1 và 2a đụng
  vào `app.py` và template, đây là test dễ vỡ nhất.
- `tests/test_coverage.py` — đợt 2a thay ba trang mà bộ test này đang canh.
- `tests/test_roles.py` — đợt 3 thêm kết nối `kome_app`.

Test mới theo đợt:

| Đợt | Test | Chặn thảm hoạ gì |
|---|---|---|
| 1 | Mọi trang render được ở cả hai chế độ sáng/tối; không có mã màu nào ngoài `static/kome.css` | Trang không đọc được — lý do khối token ra đời (`_chung.html:1-10`) |
| 1 | Không template nào và `static/kome.css` không chứa chuỗi `fonts.googleapis.com` / `fonts.gstatic.com` / `cdn.` | Phụ thuộc CDN lọt vào mà không ai để ý |
| 2a | Màn Kho dữ liệu ở bản `_chi_doc` không hiện phần nạp và không nhập `kome.pipeline` | Trang Vercel chết khi khởi động |
| 2a | Màn mới trả đúng số liệu mà `/health` và `/phu-du-lieu` đang trả, trên cùng dữ liệu | Thay ba trang đang chạy bằng một trang nói số khác |
| 2b | Ma trận khoá và bảng cột sinh từ `config/files.yml`, không phải chuỗi viết tay trong template | Bản sao thứ ba của sự thật, mục trong im lặng |
| 3 | Sale đăng nhập chỉ nhận khách đúng `salesperson_code` của mình | Lộ dữ liệu khách của người khác |
| 3 | `vai_tro='sale'` + `salesperson_code=NULL` → CSDL từ chối | Tài khoản sale không lọc được khách |
| 3 | Kết nối `kome_app` thử `UPDATE core.dim_customer` → bị từ chối | Luật "OBC chỉ đọc" bị phá bởi một dòng code viết nhầm |
| 6 | Bộ nạp sổ cái qua đủ 5 cổng; nạp 3 lần cho cùng kết quả | Công nợ nhân ba |
| 6 | Tổng từ `mart` công nợ khớp tổng từ nguồn | Báo cáo nói dối |

---

## 11. Rủi ro & giả định cần xác nhận

| # | Vấn đề | Ảnh hưởng | Cách xử lý |
|---|---|---|---|
| L1 | Bản OBC của công ty có `汎用データ受入` hay không — **chưa kiểm chứng** | Cao với nhóm C, **không** ảnh hưởng đợt 1–5 | Việc kiểm chứng cụ thể ở §8.1, làm bất cứ lúc nào trước khi động tới nhánh có điều kiện |
| L2 | `得意先元帳` / `請求先元帳` mới có 1 quý dữ liệu (`coverage.py:85-86`), và `CLAUDE.md` bẫy #4 ghi file `元帳` có 5 dòng rác trước header — **chưa kiểm chứng lại** | Cao với đợt 6 | Đo file thật trước khi viết bộ nạp, như đã làm với `売上明細表` ngày 2026-09-17 |
| L3 | `kome_app_user` / `kome_ingest_user` / `kome_report_user` **chưa tồn tại** trên CSDL thật; `DATABASE_URL` đang chạy bằng `postgres` (đã kiểm chứng 2026-09-17, spec đợt 1 G5) | Cao — chặn đợt 3 | Tạo tài khoản tay trên SQL Editor Supabase theo `docs/runbook.md` **trước** khi viết code dùng `DATABASE_URL_APP` |
| L4 | Prototype dùng `localStorage` cho bố cục dashboard, cờ tính năng và theme | Trung bình | Đợt 3 trở đi chuyển sang hồ sơ người dùng phía máy chủ; `localStorage` chỉ giữ thứ thuần cá nhân của một trình duyệt |
| L5 | Thiết kế không phản ánh ràng buộc lọc theo `salesperson_code` — mọi màn mẫu đều hiện đủ 5 sale | Cao nếu port nguyên | Mỗi đợt từ 3 trở đi phải hỏi "màn này lọc theo ai" trước khi dựng, không suy ra từ prototype |
| L6 | Ngân sách theo nhân viên chưa có nguồn và chưa có người chịu trách nhiệm nhập | Trung bình với đợt 5 | Chốt người nhập và tần suất khi viết đặc tả đợt 5; nếu không chốt được thì Báo cáo bỏ khối tiến độ ngân sách, các khối còn lại vẫn đủ giá trị |
| L7 | Treemap squarified, nhiệt đồ, kéo–thả, Kanban phải viết tay (~150–250 dòng JS mỗi cái) | Trung bình | Chấp nhận; đây là cái giá đã cân nhắc khi chọn hướng giữ Jinja (§5). Viết một lần, dùng lại giữa các màn |

---

## 12. Tiêu chí hoàn thành của tài liệu này

- [ ] Chủ sở hữu duyệt lộ trình §7 (đợt 1 · 2a · 2b · 3–8) và nhánh có điều kiện
- [ ] Chủ sở hữu duyệt việc cắt 4 màn ở §4.2
- [ ] Spec đợt 1 được cập nhật trạng thái: ghi rõ nó tách làm đôi theo §2, kèm ba sửa đổi
- [ ] Ba nhánh §8 được ghi nhận là đã quyết (8.2, 8.3) hoặc đã chuyển thành việc kiểm chứng (8.1)

Lộ trình này **không** có tiêu chí hoàn thành của riêng nó — mỗi đợt có tiêu chí trong
đặc tả riêng của đợt đó.

---

## 13. Bước tiếp theo

1. Chủ sở hữu đọc và duyệt tài liệu này
2. Cập nhật spec đợt 1 theo §2 (tách làm đôi, ba sửa đổi)
3. Viết đặc tả chi tiết **đợt 1** (nền giao diện) — đợt duy nhất không đụng CSDL, làm
   trước để tám đợt sau rẻ hơn
4. Lập kế hoạch triển khai đợt 1 (writing-plans)
5. Việc kiểm chứng OBC ở §8.1 — làm song song, không chặn gì
