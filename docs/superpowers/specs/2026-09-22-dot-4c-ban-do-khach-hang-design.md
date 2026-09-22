# Đợt 4c — Bản đồ khách hàng: đặc tả thiết kế

**Màn:** 24 trong lộ trình 24 màn (`docs/superpowers/specs/2026-09-21-lo-trinh-24-man-hinh-design.md`)
**Đường dẫn mới:** `/ban-do`
**Dữ liệu mới:** `core.dim_prefecture` (47 dòng, gieo sẵn) — đây chính là "bảng tra 47
tỉnh" mà lộ trình xếp cho đợt 4.

---

## 1. Bối cảnh

KOME có 1.710 khách trải **cả 47 tỉnh** của Nhật. Ba màn của đợt 4a/4b trả lời "khách
nào", "mã nào", "kho nào" — không màn nào trả lời **"ở đâu"**. Khối "Tập trung ở đâu"
của `/khach-hang` có 9 dòng (top 8 + `(không rõ)`); nó nói được chỗ đông nhất, không
nói được chỗ TRỐNG, và không cho thấy hình dạng vùng miền.

Câu hỏi thật mà năm nhân viên đặt ra: đi công tác một chuyến thì ghé đâu cho đáng, vùng
nào đang im lặng cả cụm, và tỉnh nào công ty chưa có mặt.

---

## 2. Ràng buộc kế thừa

Từ `CLAUDE.md` và các đợt trước, không thương lượng:

- OBC chỉ đọc. `prefecture` là cột của `core.dim_customer` (SCD2), chỉ SELECT.
- Mốc thời gian là `mart.moc_thoi_gian.hom_nay`, không phải `current_date`.
- Khách ※廃業※ không vào danh sách gọi lại. Trên màn này: họ **vẫn được đếm** ở ô
  "số khách" (họ có thật, và một tỉnh toàn khách đã phá sản là thông tin quý), nhưng
  **không** vào ô "cần gọi".
- "Khách đang rời đi" có đúng MỘT định nghĩa: `mart.khach_nhom_viec` nhóm `'im'`. Màn
  này ĐỌC nó, không viết lại vị từ. Đây là chỗ thứ **tư** hiển thị khái niệm đó.
- Mọi mã hoá bằng màu phải kèm một thứ ĐỌC ĐƯỢC (`_chung.html:76-77`).
- Lọc theo `salesperson_code` là mặc định tiện dụng, KHÔNG phải hàng rào. `?nv=` và
  `?tat_ca=1` giữ đúng nếp đợt 3/4a.
- Ngân sách vòng hỏi: nút thắt là SỐ LƯỢT HỎI (~260 ms/lượt qua pooler Tokyo), và —
  bài học đợt 4b — ngân sách đó KHÔNG đo sức tính, nên view nào bị tham chiếu nhiều
  hơn một lần trong cùng câu lệnh phải vào CTE `AS MATERIALIZED`.

---

## 3. Đo đạc quyết định hình dạng đợt này

Ba phép đo trên CSDL thật (2026-09-22), và cả ba đều đổi thiết kế.

### 3.1 Dữ liệu tỉnh SẠCH — sạch hơn mọi cột khác đã gặp

`SELECT DISTINCT prefecture FROM core.dim_customer WHERE is_current` cho đúng **47 giá
trị**, tất cả là tên chuẩn có hậu tố 都/道/府/県 (`東京都`, `北海道`, `大阪府`, `沖縄県`
…), cộng một giá trị rỗng. **Đúng 1 trên 1.710 khách** không có tỉnh.

Hệ quả: không cần lớp chuẩn hoá tên, không cần bảng bí danh, không cần đoán. Khoá nối
là chính chuỗi tên tỉnh.

[Vòng sửa 1] Câu tiếp theo ở đây từng khẳng định "cả 47 tỉnh đều đã có khách [nên] ô
'tỉnh chưa có khách' hôm nay rỗng" — SAI, đo lại 2026-09-22: cả 47 tỉnh đều có khách
trong `core.dim_customer` (đúng như trên), nhưng `mart.khach_360` (một dòng một khách
CÓ ÍT NHẤT MỘT LẦN MUA) chỉ có **46** tỉnh — 和歌山県 có 1 khách trong `dim_customer`
nhưng khách đó chưa có doanh số nào, nên không có dòng ở `khach_360`. Nghĩa là ô 0
khách ĐẦU TIÊN đã tồn tại sẵn hôm nay, ở 和歌山県, không phải một tình huống giả định
chỉ lộ ra khi lọc theo người phụ trách. Bảng tra vẫn phải đủ 47 dòng dù vậy — xem §5.2.

### 3.2 Không có toạ độ của từng khách, và sẽ không bao giờ có từ OBC

`得意先全情報` cho `postcode`, `prefecture`, `city`, `address` — không có vĩ độ/kinh độ.
Muốn có điểm từng khách thì phải geocode 1.710 địa chỉ qua dịch vụ ngoài: tốn tiền, gửi
địa chỉ khách ra bên thứ ba, và cần một bước chạy định kỳ mà pipeline nạp hiện không có.

**Độ phân giải thật của dữ liệu là CẤP TỈNH.** Mọi thứ vẽ mịn hơn thế đều là bịa.

### 3.3 Chỗ đông nhất cũng là chỗ nhỏ nhất trên bản đồ thật

Bốn tỉnh đông khách nhất: 東京都 290 · 大阪府 241 · 埼玉県 191 · 愛知県 168. Ba trong
bốn nằm ở hai cụm đô thị chật nhất nước Nhật. Trên một bản đồ theo tỷ lệ thật, 東京都 —
ô quan trọng nhất màn hình — là một chấm gần như không bấm được, còn 北海道 (ít khách)
chiếm một phần năm khung hình. Đó là bản đồ **phản ánh diện tích đất**, trong khi câu
hỏi của người dùng là về **khách hàng**.

---

## 4. Phạm vi

### 4.1 Trong phạm vi — `/ban-do`

1. **Bản đồ 47 ô** (lưới ô vuông xếp theo hình nước Nhật), tô màu theo chỉ số đang
   chọn. Mỗi ô mang tên viết tắt của tỉnh **và con số của chính nó** — không ô nào chỉ
   có màu.
2. **Ba chỉ số để chọn:** số khách · doanh thu 12 tháng · số khách cần gọi (nhóm `im`).
   Đổi chỉ số thì cả bản đồ, chú giải và bảng đổi theo.
3. **Chú giải thang màu** 5 bậc, ghi rõ khoảng giá trị của từng bậc bằng số.
4. **Bảng xếp hạng đủ 47 tỉnh** dưới bản đồ: tên tỉnh · vùng · số khách · doanh thu 12
   tháng · số cần gọi · tỷ lệ cần gọi. Bản đồ để nhìn ra cụm; bảng để đọc ra số.
5. **Gộp theo 8 vùng (地方)**: một dải tổng ngắn — 北海道 · 東北 · 関東 · 中部 · 近畿 ·
   中国 · 四国 · 九州沖縄.
6. **Bấm một ô hoặc một dòng bảng → `/khach-hang?tinh=<tên tỉnh>`**, bộ lọc đã có sẵn
   từ đợt 4a. Bản đồ trở thành cửa vào danh bạ, không phải một ngõ cụt đẹp.
7. **Lọc theo người phụ trách**, cùng nếp `/khach-hang`: mặc định theo người đang đăng
   nhập, `?nv=<mã>` xem người khác, `?tat_ca=1` bỏ lọc, luôn còn liên kết bỏ lọc.

### 4.2 Cắt khỏi phạm vi, và vì sao

Gói thiết kế (`screens/Bản đồ khách hàng.html`) vẽ một màn dựa trên Leaflet + nền
OpenStreetMap với điểm từng khách. Cắt các phần sau:

- ~~**Nền bản đồ OSM và ba kiểu nền.**~~ **[ĐÃ LẬT — xem §5.1a]** Lý lẽ ban đầu: toàn
  bộ app khi đó **không có một dòng JS phía máy khách nào và không nạp một tài nguyên
  ngoài nào** — biểu đồ ở `bao_cao.html`, `khach_360.html`, `san_pham_360.html` đều là
  SVG dựng sẵn từ Python, font tự host; thêm Leaflet + tile OSM là thêm dependency ngoài
  đầu tiên, JS máy khách đầu tiên, và một phụ thuộc mạng vào bên thứ ba cho một công cụ
  nội bộ. Chi phí đó **vẫn có thật** — chủ dự án biết và vẫn chọn làm giống gói thiết kế.
  Ba kiểu nền thì vẫn cắt: một nền đủ dùng, và mỗi kiểu nền là một nguồn tile nữa.

- **Điểm từng khách và bản đồ nhiệt** — VẪN CẮT, kể cả sau khi lật §5.1. Không có toạ độ
  của từng khách (§3.2) và sẽ không có từ OBC. Chấm đặt ở **tâm tỉnh**; nếu sau này có
  geocode thì đó là một đợt riêng, có quyết định riêng của chủ dự án về việc gửi địa chỉ
  khách ra dịch vụ ngoài.
- **Lọc theo "sản phẩm chính".** Cần khái niệm "mã chính của một khách" mà chưa view
  nào định nghĩa. Thêm một định nghĩa chỉ số mới cho một bộ lọc là đi ngược "một khái
  niệm một công thức".
- **Ngưỡng tối thiểu doanh thu / lợi nhuận / lượng bán, và "mua lần cuối trong N
  ngày".** Ngưỡng ngày cố định đi ngược thẳng bất biến "so với nhịp riêng, không với
  ngưỡng chung". Ba ngưỡng tiền/lượng là ô nhập tự do — thuộc `/khach-hang`, nơi đã có
  năm bộ lọc, chứ không phải màn nhìn tổng thể.
- **Lọc theo hạng S/A/B/C/D.** `mart.hang_doanh_thu` có thật (đợt 4a) nên làm được,
  nhưng nó chia theo **phân vị toàn công ty**; lọc bản đồ theo hạng rồi tô màu theo số
  khách cho ra một tấm bản đồ trả lời câu hỏi rất hẹp. Để lại cho đợt sau nếu có người
  hỏi.

### 4.3 Không đụng tới

`mart.khach_360`, `khach_nhom_viec`, `khach_mat_hang`, `san_pham_360` và mọi view của
4a/4b: đợt này chỉ ĐỌC. Không sửa trang nào đang có, trừ thêm một mục vào `_nav.html`.

---

## 5. Quyết định đã chốt

### 5.1 Bản đồ lưới ô, không phải bản đồ theo tỷ lệ

47 ô vuông bằng nhau, xếp theo vị trí tương đối thật của các tỉnh (北海道 trên cùng bên
phải, 沖縄県 dưới cùng bên trái, 東北 chạy dọc sườn phải, 九州 ở góc dưới trái).

Bốn lý do, xếp theo sức nặng:

1. **Ô quan trọng nhất phải bấm được.** §3.3: theo tỷ lệ thật thì 東京都 gần như biến
   mất. Ô bằng nhau khiến mỗi tỉnh có cùng quyền được nhìn thấy.
2. **Bất biến màu.** Ô bằng nhau đủ chỗ để in con số vào trong — bất biến "màu phải kèm
   thứ đọc được" được thoả một cách tự nhiên, không phải bằng tooltip.
3. **Khớp kiến trúc đang có.** SVG dựng sẵn từ Python, không JS, không tài nguyên
   ngoài, chạy được sau tường lửa và trên bản Vercel. Ba template đã làm đúng như vậy.
4. **Trung thực về độ phân giải.** Lưới ô tự nói "đây là số liệu cấp tỉnh". Một tấm bản
   đồ có đường bờ biển mời người đọc tin vào độ chính xác mà dữ liệu không có.

Đánh đổi đã biết: người quen bản đồ thật sẽ mất vài giây định vị. Bù lại bằng nhãn tên
tỉnh trên từng ô và bảng 47 dòng ngay dưới.

### 5.2 `core.dim_prefecture` đủ 47 dòng, kể cả tỉnh không có khách

Bảng gieo sẵn trong migration, mỗi dòng: tên tỉnh (khoá, đúng chuỗi OBC ghi) · tên
Latin để đọc · tên viết tắt in trên ô · vùng (8 地方) · hàng và cột trong lưới · thứ tự
chuẩn (mã JIS 1–47).

**Bất biến:** bản đồ và bảng nối từ `dim_prefecture` **LEFT JOIN** sang số liệu khách,
chứ không GROUP BY trên khách rồi vẽ. Gom theo khách thì một tỉnh không có khách nào
**biến mất khỏi bản đồ** — mà "chúng ta chưa có mặt ở tỉnh này" đúng là một trong những
điều một tấm bản đồ bán hàng phải nói ra.

[Vòng sửa 1] Câu tiếp theo ở đây từng nói "hôm nay cả 47 tỉnh đều có khách nên lỗi này
sẽ KHÔNG lộ ra trên dữ liệu thật" — SAI (xem §3.1 đã sửa): `mart.khach_360` hôm nay chỉ
có 46 tỉnh, 和歌山県 đã là một ô 0 khách sẵn trên bản đồ TỔNG, không lọc gì. Nghĩa là lỗi
"GROUP BY làm tỉnh biến mất" ĐÃ có thể lộ ra ngay hôm nay ở đúng một tỉnh (和歌山県), và
sẽ lộ rộng hơn — ở gần bốn mươi tỉnh — khi lọc theo một người phụ trách.

### 5.3 Vị trí lưới là dữ liệu, không phải mã lệnh

47 cặp (hàng, cột) nằm trong bảng, không phải trong `if`/`match` của Python hay trong
template. Sửa vị trí một ô là sửa một dòng dữ liệu.

> **[Sửa sau khi chủ dự án lật quyết định — 2026-09-22]** Đoạn dưới đây từng nói bảng
> KHÔNG giữ vĩ độ/kinh độ, vì "toạ độ mà màn này cần là toạ độ LƯỚI" và vĩ độ/kinh độ chỉ
> có nghĩa cho một phép chiếu bản đồ thật — thứ §5.1 đã bác. **§5.1 nay đã bị lật** (xem
> §5.1a), nên kết luận đó không còn đứng được: chấm phải đặt được lên một bản đồ thật, tức
> cần toạ độ thật. Migration `026` thêm `vi_do`/`kinh_do` (tâm 47 tỉnh) vào
> `core.dim_prefecture`. Phần "vị trí lưới là dữ liệu" thì giữ nguyên và vẫn dùng, vì lưới
> ô trở thành chế độ phụ (§5.1a).

### 5.1a Lật quyết định: dùng Leaflet + nền OpenStreetMap

**Chủ dự án quyết, sau khi được trình bày đầy đủ lý lẽ của §5.1 và §4.2.** Ghi lại cho rõ
ai quyết cái gì: ba lý do kỹ thuật ở §3.2/§4.2/§5.1 **vẫn đúng nguyên** — không có toạ độ
từng khách, 東京都 thành chấm nhỏ trên bản đồ theo tỷ lệ, và đây là phụ thuộc mạng vào bên
thứ ba đầu tiên của dự án. Chủ dự án biết cả ba và vẫn chọn giống gói thiết kế.

Ba ràng buộc đi kèm, không thương lượng:

1. **Tự host Leaflet trong `static/`, KHÔNG lấy từ CDN.** Dự án đã tự host font theo đúng
   nếp này. Làm vậy thì phụ thuộc bên thứ ba mới đúng **MỘT** — máy chủ tile của OSM, thứ
   không tránh được khi đã chọn hướng này — thay vì hai.
2. **Ghi công OpenStreetMap là BẮT BUỘC**, không phải tuỳ chọn thẩm mỹ: đó là điều kiện
   trong chính chính sách dùng tile của họ. Thiếu nó là dùng sai giấy phép.
3. **Trang phải còn dùng được khi tile không tải về.** Máy trong công ty có thể bị tường
   lửa chặn. Lưới 47 ô của §5.1 KHÔNG bị bỏ — nó thành chế độ phụ (`?che_do=luoi`), và
   bảng 47 dòng LUÔN hiện dưới bản đồ ở mọi chế độ. Đó cũng là lý do `hang_luoi`/`cot_luoi`
   không thành cột chết.

Chấm đặt ở **tâm tỉnh**, to nhỏ theo chỉ số — KHÔNG phải vị trí thật của từng khách, vì
không có toạ độ đó (§3.2). Trang phải nói thẳng điều này ra, không để người đọc tưởng mỗi
chấm là một cửa hàng.

### 5.4 Một khách, một tỉnh, không đếm trùng

Nối từ `mart.khach_360` (một dòng một khách) chứ không từ `core.dim_customer` (SCD2 —
một khách đổi tên có nhiều dòng). Khách có tỉnh rỗng (đúng 1 người) **không** rơi vào
tỉnh nào; trang phải nói ra bằng một dòng "(không rõ tỉnh): 1 khách" dưới bảng, không
được im lặng đánh rơi.

### 5.5 Thang màu 5 bậc theo phân vị, không theo giá trị tuyệt đối

Chia bằng `ntile(5)` trên các tỉnh **có số > 0**. Chia đều theo giá trị thì 東京都 kéo
trần lên cao tới mức bốn mươi tỉnh còn lại rơi hết vào bậc thấp nhất và bản đồ một màu.
Tỉnh có giá trị 0 mang màu riêng "trống", không phải bậc 1 — "không có" khác "ít".

### 5.6 Ngân sách vòng hỏi

`/ban-do` chạy **không quá 2 lượt hỏi**. Có test đếm lúc chạy.

`mart.khach_theo_tinh` bị tham chiếu nhiều lần trong một câu (bản đồ · bảng · dải vùng
· chú giải) → CTE `AS MATERIALIZED`, theo đúng bất biến đã ghi trong `CLAUDE.md`.

---

## 6. Kiến trúc

### 6.1 Migration `025_ban_do_tinh.sql`

- `core.dim_prefecture` — bảng thật, 47 dòng gieo bằng `INSERT`.
- `mart.khach_theo_tinh` — view: mỗi tỉnh một dòng, kèm số khách, doanh thu 12 tháng,
  số khách nhóm `im`, và `salesperson_code` để lọc được theo người phụ trách.

Chạy bằng vai trò `postgres` như mọi migration.

### 6.2 Tầng Python — `kome/ban_do.py` (mới)

Một hàm `ban_do(conn, sale, chi_so)` trả về một dataclass đóng băng chứa: 47 ô (đã có
hàng/cột/màu/nhãn/số), 8 dòng vùng, bảng 47 dòng, chú giải 5 bậc, số khách không rõ
tỉnh, và tổng toàn công ty. Không hàm nào khác — màn này không có trang con.

### 6.3 Trang mới

`kome/web/templates/ban_do.html` + route `/ban-do` + một mục trong nhóm KHÁCH HÀNG của
`_nav.html` (ngay sau "Cần xử lý").

---

## 7. Rủi ro & giả định

| Rủi ro | Xử lý |
|---|---|
| Lưới 47 ô đặt sai vị trí một tỉnh | Test khoá: đủ 47 mã JIS, không hai tỉnh trùng ô, mỗi vùng liền khối |
| Người dùng mong bản đồ thật | §5.1 ghi rõ lý do; bảng 47 dòng bù phần đọc số |
| `prefecture` của OBC đổi cách viết | Khoá nối là chuỗi tên; tỉnh lạ không khớp sẽ rơi vào "(không rõ)" chứ không làm hỏng trang. Test canh một tỉnh rác |
| Màu không phân biệt được với người mù màu | Mỗi ô có số; thang màu một tông đậm dần, không đỏ-xanh |
| Migration 025 chưa chạy khi trang lên | Cùng ca với 020–024 — chủ dự án chạy migration trước, đã có trong runbook |

---

## 8. Kiểm thử

| # | Bất biến | Test |
|---|---|---|
| 1 | Đủ 47 tỉnh trên bản đồ kể cả tỉnh 0 khách | Gieo khách chỉ ở 2 tỉnh → vẫn đủ 47 ô |
| 2 | Không hai tỉnh cùng một ô lưới | Duyệt bảng, khẳng định 47 cặp (hàng, cột) phân biệt |
| 3 | Mỗi ô có con số đọc được, không chỉ màu | Regex theo Ô của SVG |
| 4 | Số cần gọi ĐỌC `khach_nhom_viec`, khớp `/can-xu-ly` | So tập khách của hai đường |
| 5 | Khách ※廃業※ được đếm ở "số khách" nhưng KHÔNG ở "cần gọi" | Gieo một khách ※廃業※ |
| 6 | Khách không có tỉnh không bị đánh rơi im lặng | Gieo 1 khách tỉnh rỗng → trang hiện con số đó |
| 7 | Tỉnh giá trị 0 khác bậc thấp nhất | Gieo tỉnh 0 và tỉnh ít → hai màu khác nhau |
| 8 | Bấm ô dẫn tới `/khach-hang?tinh=` đúng tên, đã mã hoá URL | Khẳng định `href` |
| 9 | Lọc `?nv=` co cả bản đồ lẫn bảng lẫn dải vùng | Gieo hai sale |
| 10 | `/ban-do` không quá 2 lượt hỏi | Đếm lúc chạy |
| 11 | Tổng của 47 ô + "không rõ" = tổng toàn công ty | Khẳng định số học |

Mốc hiện tại: **388 xanh** trên `master`.

---

## 9. Tiêu chí hoàn thành

- 11 test trên xanh, cả bộ xanh.
- `CLAUDE.md` có `/ban-do` trong bảng các trang, và bất biến LEFT JOIN từ
  `dim_prefecture` (§5.2).
- **KIỂM TAY (việc của chủ dự án, sau khi chạy migration bằng vai trò `postgres`):**
  1. Mở `/ban-do`, đối chiếu bốn tỉnh đông nhất với `/khach-hang?tinh=…` — số trên ô
     phải bằng số dòng danh sách mà chính ô đó mở ra.
  2. Đo thời gian đáp ứng `/ban-do` trên CSDL đầy, **lấy lần chạy THỨ HAI** (lần đầu là
     cache lạnh). Ngưỡng 1.500 ms.
  3. Nhìn bằng mắt: lưới có đọc ra hình nước Nhật không, tên tỉnh có bị tràn ô không.

---

## 10. Bước tiếp theo

Đợt 5 — Báo cáo + Dashboard bố cục cố định theo vai trò (màn 2·1).
