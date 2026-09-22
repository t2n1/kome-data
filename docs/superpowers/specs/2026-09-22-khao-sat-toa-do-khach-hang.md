# Khảo sát: đưa địa chỉ khách thành toạ độ

**Loại tài liệu:** khảo sát trên bàn giấy (NGHIÊN CỨU — chưa phải đặc tả thi công)
**Ngày:** 2026-09-22
**Câu hỏi của chủ dự án:** *"Khách của tôi có địa chỉ cụ thể mà không làm được chấm bản đồ à?"*
**Trả lời ngắn:** làm được, tới mức **khu phố (町域)**, **miễn phí**, **không gửi một địa chỉ nào ra ngoài**. Cái không làm được là mức **số nhà**.

**Cam kết đã giữ trong lúc khảo sát:** không một mã khách, tên khách hay địa chỉ nào
rời khỏi máy này. Không thử một địa chỉ thật trên API nào. Không ghi vào CSDL — mọi
con số dưới đây đến từ `SELECT`.

---

## 1. Vì sao tài liệu này tồn tại

Đặc tả đợt 4c §3.2 viết:

> "Muốn có điểm từng khách thì phải geocode 1.710 địa chỉ qua dịch vụ ngoài: tốn
> tiền, gửi địa chỉ khách ra bên thứ ba, và cần một bước chạy định kỳ mà pipeline nạp
> hiện không có."

Câu đó **sai ở vế đầu**, và cái sai của nó đắt: nó đóng một cánh cửa còn mở. Nhật Bản
có sẵn bảng công khai ánh xạ mã bưu điện → vĩ độ/kinh độ, tải về được, giữ trong CSDL
của chính mình, không gọi API nào. Phần còn lại của §3.2 — "độ phân giải thật của dữ
liệu là CẤP TỈNH" — cũng sai: độ phân giải thật của dữ liệu là **cấp mã bưu điện**, và
đo được rằng đó là một mức mịn hơn tỉnh rất nhiều.

Tài liệu này sửa lại phép đo đó, rồi cân ba đường đi.

---

## 2. Đo trên CSDL thật (2026-09-22, chỉ SELECT)

Hai tập cần phân biệt ngay, vì mọi con số bên dưới đổi theo tập:

| Tập | Số dòng | Là gì |
|---|---|---|
| `core.dim_customer WHERE is_current` | **2.080** | mọi khách OBC từng đăng ký, kể cả tài khoản kỹ thuật |
| `mart.khach_360` | **1.710** | khách có ít nhất một lần bán — đây là tập lên bản đồ |

### 2.1 Mã bưu điện: gần như đủ, nhưng ba định dạng lẫn lộn

| | Số khách |
|---|---|
| Có `postcode` khác rỗng (trên 2.080) | **2.072** (99,6%) |
| Dạng `123-4567` (8 ký tự) | 1.289 |
| Dạng `1234567` (7 ký tự, không gạch) | 775 |
| **Dạng 6 ký tự** | **8** |
| Rỗng | 8 |
| Có `postcode` (trong 1.710 của `khach_360`) | **1.709** |

Tám dòng rỗng **không phải lỗi dữ liệu**, mà là tài khoản kỹ thuật — `その他`,
`代引き登録用データ`, `代引専用（福山通運・佐川急便）`, `株式会社KOME` (chính công ty),
và hai mã chỉ có số. Chúng cũng không có `prefecture`, `city`, `address`. Trên bản đồ
chúng phải biến mất một cách có chủ ý, không phải rơi ra vì phép nối hụt.

**Tám mã 6 ký tự là bẫy số 1 của `CLAUDE.md` hiện hình trong cột `postcode`.** Cả tám
đều ở **北海道** — tỉnh duy nhất có mã bưu điện bắt đầu bằng số 0:

```
861602  北海道 標津郡標津町      →  086-1602
708043  北海道 旭川市            →  070-8043
640807  北海道 札幌市中央区      →  064-0807
400011  北海道 函館市            →  040-0011
700031  北海道 旭川市            →  070-0031
600063  北海道 札幌市中央区\t\t  →  060-0063
802473  北海道 帯広市            →  080-2473
640808  北海道 札幌市中央区      →  064-0808
```

Cột là `text`, nhưng số 0 đầu đã rụng **trước khi** vào CSDL — ở khâu xuất của OBC
hoặc ở Excel. Hậu quả nếu ghép thô: 8 khách Hokkaido không có chấm. Hậu quả nếu ai đó
"sửa" bằng cách đệm số 0 vào **cuối** hay cắt chuỗi: mã `640807` thành `6408070`, một
mã có thật ở **京都府** — chấm bay sang đảo khác và **không lỗi nào nổ ra**.

Để ý luôn `札幌市中央区\t\t`: cột `city` có ký tự tab dính đuôi. Mọi phép so chuỗi phải
`btrim` trước, nếu không một khách sẽ lặng lẽ không khớp.

### 2.2 `city` và `address`: khớp chính xác với `postcode`

Đúng **2.072** khách có `city` khác rỗng, **2.072** có `address` khác rỗng, và **2.072**
có đủ cả ba. Không có khách nào có mã bưu điện mà thiếu địa chỉ, hay ngược lại. Đây là
cột dữ liệu sạch thứ hai của dự án sau `prefecture` — và nó có nghĩa là mọi đường đi
dưới đây đều có đầu vào đầy đủ, không đường nào phải xử lý "thiếu một nửa".

### 2.3 Mã bưu điện phân biệt: chấm KHÔNG chồng nhau như tưởng

Đây là con số quyết định, và nó ngược với trực giác:

| | `dim_customer` (2.072) | `khach_360` (1.709) |
|---|---|---|
| Mã bưu điện phân biệt | **1.520** | **1.325** |
| Trung bình khách/mã | **1,36** | **1,29** |
| Mã chỉ có **1** khách | 1.222 (80,4%) | **1.108 (83,6%)** |
| Mã đông nhất | **20** | **16** |
| Mã có ≥ 5 khách | 25 | — |

Phân bố đuôi rất ngắn (trên 2.080): 1.222 mã có 1 khách · 186 mã có 2 · 65 mã có 3 ·
22 mã có 4 · rồi thưa dần tới hai mã cá biệt là 17 và 20.

Top mã đông nhất, cả hai đều ở 新宿区 — khu người Việt của Tokyo:

```
169-0073  新宿区 (百人町)        20 khách   (16 trong khach_360)
169-0075  新宿区 (高田馬場)      17 khách   (16 trong khach_360)
270-0034  千葉県 松戸市          11
544-0001  大阪府 大阪市生野区    11
332-0021  埼玉県 川口市          10
557-0016  大阪府 大阪市西成区    10
```

**Cái mà con số này làm được, nói cho gọn:**

| Tỉnh | Khách (`khach_360`) | Chấm hôm nay | Chấm theo mã bưu điện |
|---|---|---|---|
| 東京都 | 234 | **1** | **135** |
| 大阪府 | 195 | 1 | 140 |
| 愛知県 | 150 | 1 | 132 |
| 埼玉県 | 150 | 1 | 105 |
| 千葉県 | 99 | 1 | 76 |

234 khách Tokyo chồng lên một chấm hôm nay; theo mã bưu điện họ thành 135 chấm, trong
đó phần lớn là chấm **một khách**. Đây không phải cải thiện dần dần — đây là đổi hẳn
loại câu hỏi mà màn hình trả lời được: từ "tỉnh nào đông" sang "**khu nào** đông", và
"đi Tokyo một buổi thì ghé cụm nào".

### 2.4 `address` có đủ số nhà — mịn hơn mức mã bưu điện

Mẫu thật (chọn ngẫu nhiên, đây là báo cáo nội bộ):

```
茨城県  水戸市            桜川1-5-14
高知県  南国市            元町1-1-20
東京都  台東区            上野4-7-8
埼玉県  比企郡嵐山町      志賀222-166
福岡県  北九州市小倉北区  砂津2丁目5番17
静岡県  浜松市中区        相生町15-2
大阪府  大阪市中央区      千日前１丁目７−６
京都府  久世郡久御山町    林９１−１
大阪府  堺市南区          御池台1-11-3
東京都  杉並区            和田 1-29-3
兵庫県  神戸市中央区      中山手通1丁目4-15-2F
```

Thống kê trên 2.072 địa chỉ:

| | Số dòng |
|---|---|
| Có ít nhất một chữ số | **2.069** (99,86%) |
| Có dạng `số-số` (番地 đầy đủ) | 1.667 (80,5%) |
| Có chữ 丁目 viết ra | 565 |
| **Không có chữ số nào** | **3** (`常盤町`, `本町`, `神立中央`) |
| Độ dài trung bình | 9,3 ký tự (ngắn nhất 2, dài nhất 28) |

Tức là: **địa chỉ trong OBC đủ chi tiết để geocode tới số nhà** — chỉ 3 khách trên
2.072 là không. Nó không phải "chỉ có tên toà nhà" như lo ngại; ngược lại, phần đuôi
toà nhà (`2F`) là thứ hiếm, không phải thứ thường.

Ba chỗ bẩn cần biết trước khi ai đó viết mã chuẩn hoá:
- **Chữ số toàn rộng lẫn nửa rộng** trong cùng một tập (`千日前１丁目７−６` dùng `１７６`
  và gạch nối `−` U+2212, trong khi `上野4-7-8` dùng ASCII). Một biểu thức chính quy chỉ
  bắt `[0-9-]` sẽ im lặng bỏ qua hàng trăm dòng.
- **Ba lối viết cùng một thứ**: `4-7-8` · `2丁目5番17` · `1丁目4-15`. Không chuẩn hoá
  thì mỗi lối là một nhánh khớp khác nhau.
- **Khoảng trắng lạc** (`和田 1-29-3`) và **tab dính đuôi** trong `city`.

Ngoài ra: 2.080 khách nằm trên **2.008 địa chỉ phân biệt**; **63 địa chỉ có nhiều hơn
một khách**, đông nhất là 8. Đây là chuyện có thật và đúng nghiệp vụ — nhiều pháp nhân
cùng một toà nhà, hoặc một chủ nhiều cửa hàng — nên **kể cả geocode tới số nhà, chấm
vẫn chồng nhau**, chỉ là ít hơn. Đừng chọn một giải pháp giả định "mịn hơn thì hết
chồng".

---

## 3. Đường A — tra cứu OFFLINE theo mã bưu điện

**Kết luận trước: giả thuyết của chủ dự án ĐÚNG. Đây là đường đáng đi.**

### 3.1 Dữ liệu có thật, và miễn phí ở cả hai nửa

Không có một file chính thức nào tên "mã bưu điện → vĩ độ/kinh độ". Có **hai nửa**, mỗi
nửa do một cơ quan nhà nước phát hành, và người ta ghép lại:

**Nửa thứ nhất — mã bưu điện → tên khu phố.** `KEN_ALL.CSV` của 日本郵便, khoảng
**12万 dòng**, CSV nén zip vài MB, cập nhật **hằng tháng**. Điều khoản là thứ hiếm thấy:

> 日本郵便株式会社は郵便番号データに限っては著作権を主張しません。自由に配布していた
> だいて結構です。
> *(Nhật Bản Bưu Chính không đòi bản quyền riêng với dữ liệu mã bưu điện. Cứ tự do phân phối.)*

Không giấy phép, không ghi công bắt buộc, không giới hạn thương mại.

**Nửa thứ hai — tên khu phố → vĩ độ/kinh độ.** Ba nguồn, xếp theo thứ tự nên dùng:

| Nguồn | Mức | Giấy phép | Tình trạng |
|---|---|---|---|
| **アドレス・ベース・レジストリ** (デジタル庁) | 町字 + 位置参照拡張, có cả bảng `町字マスター郵便番号` | **PDL 1.0** | mới nhất, cập nhật liên tục từ tự trị thể |
| **位置参照情報** (国土交通省) — 大字・町丁目レベル / 街区レベル | 町丁目 và 街区 | **PDL 1.0** | cập nhật 1 lần/năm từ 2003 |
| **Geolonia 住所データ** (`japanese-addresses-v2`) | 町字 + 住居表示/地番, đã kèm vĩ độ/kinh độ | **CC BY 4.0** (dữ liệu) / MIT (script) | dựng từ ABR, Geolonia cập nhật **hằng tháng** |

Bản `japanese-addresses` (v1, 277.543 dòng, CSV + SQLite) **đã ngừng cập nhật** — repo
tự chỉ sang v2. Ai chép một đường dẫn v1 từ một bài blog cũ sẽ cài một tập dữ liệu
đóng băng mà không biết.

Một người Nhật đã công bố bảng ghép sẵn **124.436 dòng** (mã bưu điện + vĩ độ/kinh độ).
Con số này hữu ích để biết quy mô kết quả — **một bảng khoảng 12 vạn dòng, cỡ vài MB**
— nhưng chính tác giả ghi "素人作成" (do người nghiệp dư làm), không công bố tỷ lệ khớp,
không có phương pháp kiểm chứng. **Không dùng bảng đó.** Tự ghép từ hai nửa chính thức:
công sức chênh nhau một buổi, còn trách nhiệm về con số thì chênh nhau hẳn một bậc.

### 3.2 Giấy phép: dùng được, nhưng phải ghi công đúng chỗ

PDL 1.0 (公共データ利用規約第1.0版) áp cho cả 位置参照情報 lẫn ABR. Ba điều ràng buộc:

1. **Phải ghi xuất xứ.** Mẫu chính thức: `出典：位置参照情報ダウンロードサービス（国土
   交通省）（URL）`. Với ABR: `出典：アドレス・ベース・レジストリ（デジタル庁）（URL）`.
2. **Sửa/chế biến thì phải nói là đã sửa**, và nói ai sửa — tách riêng khỏi dòng xuất
   xứ. Ghép KEN_ALL với 位置参照情報 **chính là** "chế biến", nên câu này bắt buộc.
3. **Cấm trình bày bản đã chế biến như thể do nhà nước làm ra.** Nghĩa là dòng ghi công
   không được để người đọc tưởng chấm trên bản đồ là toạ độ chính thức của 国交省.

Thương mại: PDL 1.0 không cấm. Phần mềm nội bộ của một công ty bán buôn dùng được.

CC BY 4.0 của Geolonia thì đơn giản hơn — ghi công tác giả — nhưng **nó cộng thêm một
dòng ghi công nữa**, không thay thế dòng của 国交省/デジタル庁 nếu ta cũng dùng nguồn gốc.

Dự án đã có sẵn chỗ cho việc này: dòng ghi công OpenStreetMap mà kế hoạch Leaflet bắt
buộc. Thêm một dòng nữa vào cùng chỗ đó là xong — **và đó là lý do nên gộp: một khu ghi
công duy nhất ở chân bản đồ, không phải ba chỗ rải rác rồi mất một chỗ lúc sửa giao diện.**

### 3.3 Độ chính xác: một mã bưu điện phủ **một 町域**, không phủ một thành phố

Đây là chỗ hay bị nói mơ hồ, nên nói cho chính xác: mã bưu điện 7 số của Nhật được đặt
cho **町域** — tên khu phố **đã bỏ phần 丁目**. Chính dữ liệu của ta xác nhận điều đó:
`169-0073` = 新宿区**百人町** (gộp cả 1〜4丁目), `169-0075` = 新宿区**高田馬場**
(gộp cả 1〜4丁目).

Hệ quả thực tế:

- **Ở đô thị**, một 町域 là vài trăm mét mỗi chiều. 百人町 vào khoảng nửa cây số ngang.
  Chấm đặt ở điểm đại diện của nó lệch so với cửa hàng **cỡ 200–400 m** — tức đi bộ
  vài phút, nhìn thấy nhau từ chỗ đứng.
- **Ở nông thôn / miền núi**, một 町域 có thể là **vài cây số**, và điểm đại diện là
  trọng tâm chứ không phải trung tâm dân cư. Chấm lệch **1–3 km** là chuyện bình thường.
  Địa chỉ như `埼玉県 比企郡嵐山町 志賀222-166` rơi đúng vào loại này.
- Ước lượng độ lớn (**phép tính của tôi, không phải số trích nguồn**): 124.000 mã bưu
  điện trên 378.000 km² → trung bình ~3 km²/mã, tức ~1,7 km mỗi chiều nếu trải đều. Đô
  thị mịn hơn nhiều, nông thôn thô hơn nhiều. Coi đây là bậc độ lớn, không phải cam kết.

So với hôm nay — chấm ở **thủ phủ tỉnh**, lệch tới **hàng trăm km** — thì đây là cải
thiện hai bậc độ lớn.

**Ba ca hỏng cần biết trước:** một mã bưu điện trải qua nhiều 町域; một 町域 mang nhiều
mã; mã vắt qua ranh giới thành phố hoặc tỉnh (di sản của các đợt sáp nhập). Thêm nữa,
**toà nhà lớn và doanh nghiệp gửi nhiều thư có mã riêng** (大口事業所個別番号), nằm ở
file **`jigyosyo.csv` tách riêng, KHÔNG có trong `KEN_ALL.CSV`**. Khách của KOME là
doanh nghiệp, nên khả năng có vài khách mang mã loại này là có thật — và biểu hiện của
nó là **không khớp**, không phải khớp sai. Chưa đo được tỷ lệ (xem §8).

### 3.4 Cập nhật và mã bưu điện đổi

KEN_ALL ra bản mới **hằng tháng**; 位置参照情報 mỗi năm một lần; ABR/Geolonia hằng tháng.
Mã bưu điện đổi khi có sáp nhập hành chính hoặc chia lại khu vực giao thư — hiếm, nhưng
có thật.

**Điều này KHÔNG thêm bước nào vào quy trình 13:30 hằng ngày.** Bảng tra là dữ liệu
tham chiếu, không phải dữ liệu giao dịch; nó nằm trong một migration gieo sẵn, y như
`core.dim_prefecture` 47 dòng của đợt 4c. Nạp lại mỗi năm một lần là dư dả, và nếu
không ai nạp lại thì cái hỏng là "một vài khách mới ở khu vực mới chưa có chấm" — một
khách thiếu chấm, không phải một con số sai.

**Và đây là điểm mạnh thật sự của đường A so với đường B:** sự đúng đắn của nó không
phụ thuộc vào việc hôm nay có ai trả tiền, có ai giữ khoá API, hay một nhà cung cấp có
đổi điều khoản hay không.

### 3.5 Hình dạng nếu làm

Một migration mới, không đụng file cũ:

```
core.dim_postcode (
    ma          text PRIMARY KEY,   -- 7 số, KHÔNG gạch, đã đệm số 0 đầu
    prefecture  text NOT NULL,      -- để ĐỐI CHIẾU, không để hiển thị
    city        text,
    town        text,
    vi_do       numeric(9,6) NOT NULL,
    kinh_do     numeric(9,6) NOT NULL,
    nguon       text NOT NULL       -- 'ABR' / 'ISJ' — để biết dòng nào từ đâu
)
```

Khoảng 12 vạn dòng, vài MB trong CSDL. Nối bằng
`replace(btrim(dim_customer.postcode), '-', '')` đã `lpad(…, 7, '0')`.

**Bất biến đề nghị — ĐỐI CHIẾU TỈNH, KHÔNG ĐOÁN.** Sau khi nối, so
`dim_postcode.prefecture` với `dim_customer.prefecture`. Lệch thì **bỏ chấm của khách
đó** và đếm nó vào một ô "chưa định vị được", chứ không lấy toạ độ. Lý do là tám dòng
Hokkaido ở §2.1: một mã bưu điện hỏng vẫn có thể khớp **trúng một dòng có thật ở tỉnh
khác**, và lúc đó lỗi không hiện ra bằng một dòng trống — nó hiện ra bằng **một chấm
trông hoàn toàn bình thường ở sai chỗ**, thứ mà không ai đi kiểm. `prefecture` của OBC
đã được đo là sạch tuyệt đối (47 giá trị chuẩn, đợt 4c §3.1); dùng chính nó làm trọng
tài là dùng thứ đáng tin nhất ta có.

**Bất biến đề nghị — SỐ KHÁCH CHƯA ĐỊNH VỊ ĐƯỢC PHẢI HIỆN RA TRÊN TRANG.** Không phải
trong log. Một bản đồ lặng lẽ đánh rơi 40 khách trông y hệt một bản đồ đầy đủ.

**Chi phí:** 0 yên, mãi mãi. Không gửi gì ra ngoài. Không thêm bước vào quy trình hằng
ngày. Chạy được trên Vercel (vài MB trong CSDL, không phải trong gói cài).

---

## 4. Đường B — geocode bằng dịch vụ ngoài

### 4.1 Giá

| Nhà cung cấp | Lần đầu 1.710 địa chỉ | Vài chục địa chỉ mới/tháng |
|---|---|---|
| **Google Geocoding API** | **$0** (10.000 lượt/tháng miễn phí, rồi $5/1.000) | $0 |
| **Mapbox Temporary** | $0 (100.000 lượt/tháng miễn phí) | $0 |
| **Mapbox Permanent** | ~**$8,55** ($5/1.000, **không có bậc miễn phí**) | ~$0,25 |
| **Yahoo! JAPAN ジオコーダAPI** | $0 (5 vạn lượt/ngày) | $0 |
| **Geolonia「クイック住所変換」** | 10.000 JPY (gói tới 5.000 dòng) | trong gói |
| **Geolonia API コンテナ** (tự chạy tại chỗ) | **từ 1.000.000 JPY/năm** | trong gói |

Giá gần như bằng không. **Giá không phải là vấn đề của đường B. Điều khoản mới là.**

### 4.2 Điều khoản LƯU toạ độ — đây là chỗ quyết định

**Google: KHÔNG được lưu quá 30 ngày.** Điều khoản dịch vụ riêng của Google Maps
Platform cho phép "temporarily cache latitude and longitude values … for up to 30
consecutive calendar days, after which Customer must delete the cached values". Hết 30
ngày phải **xoá**. Ngoại lệ duy nhất là `place_id`.

Nghĩa cụ thể cho KOME: mỗi tháng phải gọi lại **toàn bộ 1.710 địa chỉ** để làm mới bộ
đệm — tức **thêm một bước định kỳ vào quy trình**, đúng cái mà §3.2 của đặc tả 4c đã lo
nhưng lại quy cho sai nguyên nhân. Và một cột toạ độ **sẽ hết hạn** trong CSDL là một
khái niệm mới, xa lạ với dự án này: `core` cho tới nay chỉ chứa thứ OBC nói, và không
dòng nào trong đó tự hỏng theo thời gian.

**Mapbox: phải trả tiền cho quyền lưu.** Mapbox chia hẳn hai sản phẩm — Temporary
(miễn phí tới 100.000 lượt/tháng, **cấm lưu**) và Permanent (**$5/1.000, không có bậc
miễn phí**, cho lưu vô hạn định). Đây là nhà cung cấp trả lời câu hỏi rõ ràng nhất:
1.710 địa chỉ = **~$8,55, một lần, lưu vĩnh viễn hợp pháp**. Kết quả Permanent chỉ được
dùng cho nội bộ doanh nghiệp, không được phân phối lại — điều đó khớp với ca dùng ở đây.

**Yahoo! JAPAN: miễn phí nhất, nhưng điều khoản mập mờ nhất.** 5 vạn lượt/ngày, nhưng
hướng dẫn của Yahoo ghi rằng web service của họ dành cho "**非商用目的**" (mục đích phi
thương mại), kèm câu không cấm hẳn doanh nghiệp mà bảo "**法人デベロッパーの方は…相談し
てください**" (pháp nhân thì liên hệ hỏi). Nghĩa là: dùng cho một hệ thống nội bộ của
công ty thương mại là vùng xám **phải hỏi mới biết** — và trong lúc chưa hỏi thì đó là
một rủi ro pháp lý mang tên "chắc là được".

**Nominatim của OpenStreetMap: không dùng được cho việc này.** Chính sách sử dụng cấm
"systematic queries" và đặt trần tuyệt đối **1 lượt/giây**; ai cần bộ dữ liệu đầy đủ thì
"get it from the OSM planet or an extract". Chạy 1.710 địa chỉ qua đó là đúng loại việc
chính sách nêu tên để cấm. Dữ liệu ODbL còn kèm điều khoản share-alike.

### 4.3 Gửi cái gì ra đâu

Đi đường B là **gửi toàn bộ 2.072 địa chỉ khách ra máy chủ của một công ty Mỹ hoặc
Nhật**. Nói cho đủ: đó là địa chỉ **cơ sở kinh doanh** (tạp hoá, quán ăn), phần lớn đã
công khai trên biển hiệu và Google Maps — **không phải** địa chỉ nhà riêng. Mức nhạy cảm
vì thế thấp hơn nhiều so với cảm giác ban đầu.

Nhưng cái không thấp là **cái gói ghép lại**: gửi đi không phải một địa chỉ, mà **danh
sách khách hàng của KOME** — chính xác 1.710 dòng, trong một lô, một lần. Nhà cung cấp
lưu log truy vấn bao lâu là điều khoản của họ, không phải của ta, và câu trả lời thay
đổi theo từng bên. **Và điểm mấu chốt: chủ dự án chưa đồng ý cho gửi.** Đường A không
cần xin phép đó.

### 4.4 Cái đường B mua được, mà đường A không có

Công bằng mà nói: **mức số nhà**. Google/Mapbox trả về toạ độ của đúng `上野4-7-8`, chứ
không phải điểm đại diện của 上野. Với 80,5% địa chỉ có 番地 đầy đủ (§2.4), đường B cho
chấm **đúng cửa** thay vì đúng khu phố.

Đó là thứ có giá trị thật — chỉ là chưa chắc đáng đổi lấy một cột dữ liệu hết hạn sau
30 ngày, hoặc một danh sách khách gửi ra ngoài.

---

## 5. Đường C — bộ geocode chạy tại chỗ

**`jageocoder`** — bộ geocode địa chỉ Nhật viết bằng Python thuần.

| | |
|---|---|
| Giấy phép | **MIT** |
| Python | ≥ 3.9.2 |
| Phụ thuộc | không cần pandas, không cần phần mở rộng C |
| Nguồn dữ liệu | 位置参照情報 / CSVアドレスマッチング của 東大 CSIS, cùng dòng với DAMS mà 地理院地図 dùng |
| Bảo trì | còn sống — 306 commit, từ điển bản 2025-04 |
| Độ mịn | tới **街区/地番** (mức 7) và **toà nhà** (mức 8) |
| **Từ điển** | **4,5 GB nén · trên 20 GB sau khi giải nén** |

Dòng cuối là dấu chấm hết cho đường C ở dự án này, và không phải vì hơi to:

- Vercel: gói cài cố ý không có pandas vì ~120 MB đã là quá nhiều. **20 GB** không phải
  là "cùng vấn đề, lớn hơn" — nó là vấn đề khác hẳn.
- Ổ đĩa trên Vercel là **tạm**. Một từ điển 20 GB dựng lại mỗi lần khởi động là điều
  không tồn tại.
- Ngay cả ở máy trong công ty, 20 GB cho một màn bản đồ là cái giá không tương xứng.

**Nhưng đường C vẫn dùng được, theo một cách khác: chạy MỘT LẦN, ngoài ứng dụng.**
Cài `jageocoder` trên máy trong công ty, chạy 2.072 địa chỉ, ghi kết quả vào một bảng
`core.dim_customer_toa_do`, rồi **gỡ từ điển đi**. Ứng dụng chỉ đọc bảng toạ độ; nó
không bao giờ biết `jageocoder` từng tồn tại. Như thế ta có:

- độ mịn **mức số nhà** của đường B,
- **không gửi một địa chỉ nào ra ngoài** như đường A,
- không một byte nào của 20 GB kia dính vào `requirements.txt`.

Cái phải trả: một quy trình chạy tay, không nằm trong pipeline, và phải nhớ chạy lại khi
có khách mới. Với "vài chục khách mới mỗi tháng" thì đó là một việc **hằng quý**, không
phải hằng ngày — và nếu quên, hậu quả là khách mới tạm chưa có chấm, **không** phải một
con số sai. Hậu quả của việc quên là thứ nên cân, không phải bản thân việc quên.

*(`pydams` — wrapper Python của DAMS — nhanh hơn nhưng cần biên dịch thư viện C tại chỗ,
tức thêm một chuỗi công cụ build vào máy Windows của công ty. `jageocoder` là bản Python
thuần của cùng dòng dữ liệu; chọn nó.)*

---

## 6. Hai câu hỏi thiết kế

### 6.1 Chấm chồng nhau — vấn đề nhỏ hơn dự đoán, nhưng có thật

Số đo (§2.3) đổi câu trả lời: theo mã bưu điện, **83,6% mã chỉ có đúng một khách**, và
chỉ **217 mã** (trên 1.325) có từ 2 khách trở lên. Ca xấu nhất là 16 khách. Đây không
phải bài toán "1.710 chấm đè lên nhau" mà người ta thường tưởng.

Ba kỹ thuật thông dụng:

| Cách | Làm gì | Hợp với ta? |
|---|---|---|
| **Gom cụm** (`Leaflet.markercluster`, BSD-2-Clause, ~30 KB, tự host được) | chấm gần nhau gộp thành một vòng tròn mang **số đếm**; zoom vào thì tách | **Có** — xử lý đúng ca "nhìn cả nước / nhìn cả Kantō", và bung ra chính xác khi zoom |
| **Toả nhẹ** (jitter / spiderfy) | dịch mỗi chấm một đoạn nhỏ ngẫu nhiên, hoặc xoè thành nan hoa khi bấm | **Chỉ spiderfy** — jitter ngẫu nhiên là **bịa ra vị trí**, đúng thứ đợt 4c đã bác bỏ. Spiderfy (bấm vào mới xoè, có đường nối về điểm gốc) thì trung thực, và markercluster có sẵn |
| **Đếm số trên chấm** | một chấm cho một mã bưu điện, to nhỏ / mang số theo số khách | **Có** — và đây là nền, không phải phương án thay thế |

**Đề nghị cho một công cụ nội bộ của 5 người:** gộp cả ba theo tầng — **một chấm cho
một mã bưu điện, mang con số của chính nó** (đúng bất biến "màu phải kèm thứ đọc được"
đã có); **markercluster** cho mức zoom rộng; **spiderfy** khi bấm vào cụm; và **bảng
danh sách bên cạnh bản đồ** làm đường đọc chính thức — vì bản đồ không đọc được bằng bàn
phím, đúng như kế hoạch Leaflet đã chốt. Không jitter ngẫu nhiên, ở bất kỳ mức nào.

Nhắc lại §2.4: **63 địa chỉ có nhiều hơn một khách** (đông nhất 8). Chồng chấm không
biến mất kể cả ở mức số nhà — nên markercluster là thứ cần trong mọi đường đi, không
phải chỉ trong đường A.

### 6.2 Trung thực về độ chính xác — viết ra, không ẩn trong tooltip

Rủi ro cụ thể: một nhân viên bán hàng lái xe tới cái chấm, đứng giữa 百人町 và không
thấy cửa hàng nào. Lần đó anh ta mất 20 phút. Lần sau anh ta không tin bản đồ nữa — và
mất niềm tin thì cả màn hình thành vô dụng, không chỉ một chấm.

Bốn điều bắt buộc, theo thứ tự sức nặng:

1. **Nhãn thường trực ngay dưới bản đồ**, không phải tooltip, không phải chú thích cuối
   trang: *"Chấm đặt ở giữa khu vực mã bưu điện — KHÔNG phải vị trí cửa hàng. Sai lệch
   thường vài trăm mét ở thành phố, có thể vài cây số ở nông thôn."* Tooltip là thứ chỉ
   người đã nghi ngờ mới đi tìm; người sắp lái xe thì không.
2. **Popup của mỗi chấm phải hiện ĐỊA CHỈ ĐẦY ĐỦ dạng chữ** (`prefecture + city +
   address`), đặt nổi hơn cả toạ độ. Người bán không cần toạ độ — họ cần một chuỗi chữ
   để gõ vào điện thoại. Đây vừa là trung thực vừa là tính năng hữu dụng nhất của popup.
3. **Khách chưa định vị được phải đếm và hiện ra** (§3.5). Kèm cách xem danh sách đó.
4. **Trang phải nói dữ liệu toạ độ đến từ đâu và cũ tới mức nào** — cùng chỗ với dòng
   ghi công OpenStreetMap. Một dòng: nguồn, tháng của bản dữ liệu.

Nếu sau này đi đường C (mức số nhà) thì nhãn ở mục 1 **phải đổi theo**, và tốt nhất là
**mỗi chấm mang mức chính xác của chính nó** (`số nhà` / `khu phố` / `chưa định vị`) —
vì một bảng geocode thật bao giờ cũng lẫn nhiều mức, và một nhãn chung "chính xác tới số
nhà" trên một tập lẫn lộn là lời nói dối tệ hơn cả nhãn thô ban đầu.

---

## 7. So ba đường

| | **A · offline theo mã bưu điện** | **B · API ngoài** | **C · jageocoder chạy một lần** |
|---|---|---|---|
| Độ mịn | **町域** (~200–400 m đô thị, 1–3 km nông thôn) | **số nhà** | **số nhà** |
| Tokyo: 1 chấm → | **135 chấm** | ~230 chấm | ~230 chấm |
| Tiền | **0** | $0–8,55 một lần | **0** |
| Gửi địa chỉ ra ngoài | **không** | **có, 1.710 dòng, một lô** | **không** |
| Được lưu toạ độ? | **hiển nhiên** | Google: **30 ngày** · Mapbox Permanent: có | **hiển nhiên** |
| Thêm bước hằng ngày | **không** | Google: **có** (làm mới hằng tháng) | không (chạy tay theo quý) |
| Chạy trên Vercel | **được** | được | được (từ điển không lên Vercel) |
| Công sức lần đầu | **một migration + một script ghép** | một script + một khoá API | cài 20 GB, chạy, gỡ |
| Hỏng thì hỏng thế nào | vài khách thiếu chấm | **hết hạn / đổi điều khoản / hết khoá** | vài khách thiếu chấm |

---

## 8. Điều CHƯA đo được, và vì sao

Nói thẳng, vì mấy chỗ này là chỗ ước lượng ở trên có thể sai:

1. **Tỷ lệ khớp thật.** Tôi **chưa tải `KEN_ALL.CSV` về** nên chưa biết trong 1.325 mã
   bưu điện phân biệt của ta có bao nhiêu mã tìm được trong bảng tra. Tôi đoán trên 97%,
   nhưng đó là **suy đoán**. Phép đo này tốn khoảng 15 phút, **không gửi một byte dữ
   liệu công ty nào ra ngoài** (chỉ tải một file công khai vài MB về), và nó là việc
   **đầu tiên** phải làm trước khi viết bất kỳ đặc tả thi công nào. Tôi không tự làm vì
   nó là một lượt tải file từ nguồn ngoài, và khảo sát này chưa được cấp phép đó.
2. **Bao nhiêu khách mang mã 大口事業所個別番号** (không có trong KEN_ALL). Chỉ đo được
   sau khi ghép thật. Biểu hiện là "không khớp", không phải "khớp sai" — nên nó làm hụt
   chấm chứ không làm sai chấm.
3. **Sai lệch thật tính bằng mét.** Con số "200–400 m đô thị" là suy ra từ cỡ một 町域 ở
   新宿, không phải đo trên chính dữ liệu của ta. Đo được sau khi có bảng tra: lấy toạ độ
   theo mã bưu điện so với toạ độ theo số nhà (đường C) cho vài chục khách, rồi lấy
   trung vị. **Cho tới lúc đó, đừng in một con số mét cụ thể lên trang.**
4. **Chất lượng bộ dữ liệu GeoNames cho Nhật.** Nó tồn tại, CC BY 4.0, có mã bưu điện +
   toạ độ trong một file duy nhất — hấp dẫn vì đơn giản — nhưng chính trang mô tả của nó
   ghi cột `admin_name3` (町域) chỉ có ở **32%** số dòng. Tôi **không tin** bộ này cho
   Nhật và không đo được nó mà không tải về. Nếu ai đó chọn nó vì "một file là xong",
   hãy đo cột đó trước.
5. **Điều khoản Yahoo! JAPAN cho pháp nhân.** Chính họ bảo đi hỏi. Tôi không hỏi.
6. **Tôi chưa chạy `jageocoder`.** Tỷ lệ phân giải tới mức 7/8 trên **đúng tập địa chỉ
   này** — với chữ số toàn rộng, ba lối viết 丁目, và khoảng trắng lạc — là chưa biết.
   Con số "~230 chấm cho Tokyo" ở bảng §7 giả định nó phân giải gần như hết; giả định đó
   chưa được kiểm.

---

## 9. Khuyến nghị

**Đi đường A.** Không phải vì nó chính xác nhất — nó không phải — mà vì nó là đường duy
nhất mà **sự đúng đắn của nó không phụ thuộc vào ai cả**: không khoá API, không điều
khoản có thể đổi, không cột dữ liệu hết hạn sau 30 ngày, không một lượt gửi danh sách
khách hàng ra ngoài, không một bước mới trong buổi 13:30. Nó biến 234 khách Tokyo từ một
chấm thành 135 chấm, và 83,6% số chấm đó là chấm một khách. Đó đã là đổi hẳn loại câu
hỏi mà màn hình trả lời được.

**Giữ đường C trong túi.** Nếu sau một mùa dùng thật mà nhân viên nói "gần đúng chưa đủ,
tôi cần đúng cửa", thì `jageocoder` chạy một lần ngoài ứng dụng nâng lên mức số nhà mà
**vẫn không gửi gì ra ngoài** — và bảng `core.dim_customer_toa_do` của đường A đã sẵn
đúng hình dạng để nhận kết quả đó, chỉ thêm một cột `muc_chinh_xac`. Thiết kế đường A
sao cho đường C lắp vào được, ngay từ đầu.

**Đường B chỉ nên mở lại nếu chủ dự án muốn mức số nhà NGAY và chấp nhận gửi 1.710 địa
chỉ ra ngoài.** Trong ca đó thì chọn **Mapbox Permanent** (~$8,55 một lần, được lưu vĩnh
viễn, điều khoản viết rõ ràng nhất) — **không** chọn Google, vì điều khoản 30 ngày của
Google biến một việc làm một lần thành một nghĩa vụ hằng tháng, vĩnh viễn.

**Việc kế tiếp, trước mọi đặc tả thi công:** tải `KEN_ALL.CSV` (công khai, vài MB, không
gửi gì đi) và đo tỷ lệ khớp thật trên 1.325 mã bưu điện của ta. Nếu tỷ lệ đó dưới ~95%,
cả khuyến nghị này phải xét lại.

---

## Nguồn

- [位置参照情報ダウンロードサービス — 国土交通省](https://nlftp.mlit.go.jp/isj/index.html)
- [国土数値情報・位置参照情報 利用約款 (PDL 1.0)](https://nlftp.mlit.go.jp/ksj/other/agreement.html)
- [アドレス・ベース・レジストリ — デジタル庁](https://www.digital.go.jp/policies/base_registry_address) · [データ配布サイト](https://dataset.address-br.digital.go.jp/) · [利用規約](https://www.digital.go.jp/policies/base_registry_address_tos)
- [郵便番号データダウンロード — 日本郵便](https://www.post.japanpost.jp/zipcode/download.html) · [データの説明](https://www.post.japanpost.jp/zipcode/dl/readme.html)
- [Geolonia 住所データ](https://geolonia.github.io/japanese-addresses/) · [japanese-addresses-v2](https://github.com/geolonia/japanese-addresses-v2) · [community-geocoder](https://github.com/geolonia/community-geocoder)
- [郵便番号・住所・緯度経度の体系について — フューチャー技術ブログ](https://future-architect.github.io/articles/20220719b/)
- [郵便番号と緯度経度の紐づけデータ (124.436 dòng, do cá nhân làm)](https://note.com/tsuguro/n/n5496d0d443b3)
- [Google Maps Platform Service Specific Terms](https://cloud.google.com/maps-platform/terms/maps-service-terms) · [Pricing](https://developers.google.com/maps/billing-and-pricing/pricing)
- [Mapbox Geocoding API](https://docs.mapbox.com/api/search/geocoding/) · [Pricing](https://www.mapbox.com/pricing)
- [Yahoo! JAPAN コンテンツジオコーダAPI](https://developer.yahoo.co.jp/webapi/map/openlocalplatform/v1/contentsgeocoder.html)
- [Nominatim Usage Policy — OSM Foundation](https://operations.osmfoundation.org/policies/nominatim/)
- [jageocoder](https://github.com/t-sagara/jageocoder) · [Tài liệu cài đặt](https://jageocoder.readthedocs.io/ja/latest/install.html) · [GeoNLP](https://geonlp.ex.nii.ac.jp/jageocoder/)
- [Geolonia Maps 料金](https://www.geolonia.com/pricing/) · [クイック住所変換](https://geo-news.jp/archives/6330)
- [Postal Codes Dataset for Japan — GeoNames/datahub](https://datahub.io/logistics/postal-codes-jp)
