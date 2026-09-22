# Đợt 4c (làm lại) — Bản đồ Leaflet + nền OpenStreetMap

> **Cho người thực thi:** BẮT BUỘC dùng sub-skill superpowers:subagent-driven-development
> để làm theo từng task. Các bước dùng cú pháp checkbox (`- [ ]`).

**Mục tiêu:** thay lưới 47 ô bằng bản đồ Nhật Bản thật (Leaflet + tile OpenStreetMap),
chấm đặt ở **thủ phủ từng tỉnh**, to nhỏ theo chỉ số. Lưới ô trở thành chế độ phụ.

**Kiến trúc:** Leaflet **tự host** trong `static/`; tile lấy từ máy chủ OSM; dữ liệu chấm
do máy chủ dựng sẵn thành JSON nhúng trong trang (không thêm endpoint API, không thêm lượt
hỏi). Bảng 47 dòng và dải vùng giữ nguyên từ bản trước.

**Đặc tả:** `docs/superpowers/specs/2026-09-22-dot-4c-ban-do-khach-hang-design.md`, đặc
biệt **§5.1a** (lật quyết định) và §5.3 đã sửa.

## Vì sao có kế hoạch này

Bản đầu của đợt 4c dựng lưới 47 ô vuông, với bốn lý do ở §5.1. Chủ dự án được trình bày
đầy đủ ba chi phí — không có toạ độ từng khách, 東京都 thành chấm nhỏ trên bản đồ theo tỷ
lệ, và đây là phụ thuộc mạng vào bên thứ ba đầu tiên của dự án — và **vẫn chọn** làm giống
gói thiết kế. Kế hoạch này thi hành quyết định đó.

## Global Constraints

- **Leaflet TỰ HOST** trong `kome/web/static/`, KHÔNG `<script src>` tới CDN. Dự án đã tự
  host font theo đúng nếp này. Nhờ vậy phụ thuộc bên thứ ba mới đúng **MỘT**: máy chủ tile
  của OSM.
- **Ghi công OpenStreetMap là BẮT BUỘC** — điều kiện trong chính chính sách dùng tile của
  họ, không phải tuỳ chọn thẩm mỹ. Thiếu nó là dùng sai giấy phép.
- **Trang phải còn dùng được khi tile không tải về.** Máy trong công ty có thể bị tường lửa
  chặn. Giữ `?che_do=luoi` (lưới 47 ô) và **luôn** hiện bảng 47 dòng ở mọi chế độ.
- **Chấm ở THỦ PHỦ tỉnh, không phải vị trí khách.** Trang phải nói thẳng ra. Để người đọc
  tưởng mỗi chấm là một cửa hàng là dựng ra một độ chính xác không tồn tại.
- Mọi mã hoá bằng màu/kích thước phải kèm một thứ ĐỌC ĐƯỢC. Bản đồ không đọc được bằng bàn
  phím → bảng 47 dòng là đường đọc chính thức, không phải phụ lục.
- Ngân sách vòng hỏi `/ban-do` **≤ 2** giữ nguyên. Dữ liệu chấm nhúng thẳng vào trang; KHÔNG
  thêm endpoint, KHÔNG gọi API sau khi tải.
- `kome/web/app.py` KHÔNG nhập `kome.pipeline`/pandas ở mức ngoài cùng.
- Không sửa migration đã chạy — chỉ thêm `026`.
- Chạy test ở TIỀN CẢNH bằng `python -u -m pytest`, KHÔNG pipe qua `tail`.

---

## Task 1: Migration `026` — toạ độ 47 tỉnh

**Files:**
- Tạo: `db/migrations/026_toa_do_tinh.sql`
- Test: `tests/test_ban_do.py` (nối thêm)

**Interfaces:**
- Produces: `core.dim_prefecture` có thêm `vi_do numeric(6,3) NOT NULL`,
  `kinh_do numeric(6,3) NOT NULL`.

- [ ] **Bước 1: viết test đỏ trước**

```python
def test_toa_do_47_tinh_nam_trong_hop_bao_nuoc_Nhat(conn):
    # Hộp bao Nhật Bản: vĩ độ 24-46, kinh độ 122-146. Một dấu trừ lạc hay hai
    # cột bị hoán chỗ sẽ ném cả nước sang châu Phi, và trên bản đồ thì nó hiện
    # ra là một tấm bản đồ TRỐNG — không lỗi nào nổ.
    xau = conn.execute("""
        SELECT ten, vi_do, kinh_do FROM core.dim_prefecture
         WHERE vi_do NOT BETWEEN 24 AND 46 OR kinh_do NOT BETWEEN 122 AND 146
    """).fetchall()
    assert xau == []


def test_okinawa_o_NAM_va_TAY_hokkaido(conn):
    # Một phép kiểm hướng thật, không phải kiểm phạm vi: hoán hai cột vi_do và
    # kinh_do vẫn lọt qua hộp bao ở test trên với một số tỉnh.
    o = dict((t, (float(a), float(b))) for t, a, b in conn.execute(
        "SELECT ten, vi_do, kinh_do FROM core.dim_prefecture").fetchall())
    assert o["沖縄県"][0] < o["北海道"][0]      # nam hơn
    assert o["沖縄県"][1] < o["北海道"][1]      # tây hơn
    assert o["東京都"][1] > o["福岡県"][1]      # Tokyo đông hơn Fukuoka


def test_thu_tu_dong_tay_khop_thu_tu_cot_luoi(conn):
    # Lưới ô (migration 025) và toạ độ thật (026) phải kể CÙNG một câu chuyện.
    # Lệch nhau nghĩa là một trong hai sai, và người dùng sẽ thấy khi đổi chế độ.
    # Kiểm tương quan hạng giữa `kinh_do` và `cot_luoi` trên cả 47 dòng.
    ...
```

- [ ] **Bước 2: chạy để thấy ĐỎ** — `python -u -m pytest tests/test_ban_do.py -v`

- [ ] **Bước 3: viết migration**

`ALTER TABLE core.dim_prefecture ADD COLUMN vi_do numeric(6,3), ADD COLUMN kinh_do
numeric(6,3);` rồi `UPDATE` 47 dòng, rồi `SET NOT NULL`. Thêm `COMMENT ON COLUMN`.

Toạ độ dưới đây là **thủ phủ** từng tỉnh (không phải trọng tâm hình học, cũng không phải vị
trí khách). Ghi rõ điều đó trong chú thích: thủ phủ là nơi khách thật sự tụ, và nó là quy
ước thông dụng khi đặt một chấm cho cả tỉnh — nhưng nó KHÔNG phải trọng tâm, nên đừng ai
dùng cột này để tính khoảng cách giao hàng.

```
01 北海道     43.064 141.347
02 青森県     40.825 140.740
03 岩手県     39.704 141.153
04 宮城県     38.269 140.872
05 秋田県     39.719 140.102
06 山形県     38.240 140.363
07 福島県     37.750 140.468
08 茨城県     36.342 140.447
09 栃木県     36.566 139.884
10 群馬県     36.391 139.061
11 埼玉県     35.857 139.649
12 千葉県     35.605 140.123
13 東京都     35.690 139.692
14 神奈川県   35.448 139.642
15 新潟県     37.902 139.023
16 富山県     36.695 137.211
17 石川県     36.595 136.626
18 福井県     36.065 136.222
19 山梨県     35.664 138.568
20 長野県     36.651 138.181
21 岐阜県     35.391 136.722
22 静岡県     34.977 138.383
23 愛知県     35.180 136.907
24 三重県     34.730 136.509
25 滋賀県     35.005 135.869
26 京都府     35.021 135.756
27 大阪府     34.686 135.520
28 兵庫県     34.691 135.183
29 奈良県     34.685 135.833
30 和歌山県   34.226 135.168
31 鳥取県     35.504 134.238
32 島根県     35.472 133.051
33 岡山県     34.662 133.935
34 広島県     34.396 132.460
35 山口県     34.186 131.471
36 徳島県     34.066 134.559
37 香川県     34.340 134.043
38 愛媛県     33.842 132.766
39 高知県     33.560 133.531
40 福岡県     33.607 130.418
41 佐賀県     33.249 130.300
42 長崎県     32.745 129.874
43 熊本県     32.790 130.742
44 大分県     33.238 131.613
45 宮崎県     31.911 131.424
46 鹿児島県   31.560 130.558
47 沖縄県     26.212 127.681
```

- [ ] **Bước 4: chạy test cho xanh, rồi chạy cả bộ.**

- [ ] **Bước 5: commit** (thông điệp chỉ ASCII, không dấu, không backtick).

---

## Task 2: Tự host Leaflet và dựng bản đồ

**Files:**
- Tạo: `kome/web/static/leaflet/leaflet.js`, `leaflet.css`, thư mục ảnh của Leaflet
- Sửa: `kome/ban_do.py`, `kome/web/templates/ban_do.html`, `kome/web/app.py`,
  `kome/web/static/kome.css`
- Test: `tests/test_ban_do.py`

**Interfaces:**
- Consumes: `vi_do`/`kinh_do` (Task 1); `TrangBanDo` và `O` đang có.
- Produces: `O` thêm `vi_do`, `kinh_do`; `TrangBanDo` thêm `che_do` (`"ban-do"` mặc định
  hoặc `"luoi"`) và `diem_json` (chuỗi JSON đã escape an toàn để nhúng).

- [ ] **Bước 1: lấy Leaflet về `static/`**

Tải bản phát hành Leaflet (`leaflet.js`, `leaflet.css` và thư mục `images/` mà CSS tham
chiếu) rồi đặt dưới `kome/web/static/leaflet/`. Ghi số phiên bản vào một dòng chú thích ở
đầu `leaflet.css` **và** vào `CLAUDE.md` ở Task 3 — một thư viện tự host không có số phiên
bản là thứ không ai dám nâng cấp.

Kiểm: `leaflet.css` tham chiếu ảnh marker theo đường dẫn tương đối; nếu thiếu thư mục
`images/` thì marker thành ô vuông vỡ. Mở thật một lần để xác nhận.

- [ ] **Bước 2: viết test đỏ trước**

```python
def test_khong_nap_tai_nguyen_nao_tu_CDN(client):
    # Tự host là ràng buộc, không phải sở thích: mỗi máy chủ ngoài là một chỗ
    # trang có thể chết mà ta không sửa được. Tile OSM là NGOẠI LỆ DUY NHẤT.
    html = client.get("/ban-do").text
    ngoai = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    assert all("tile.openstreetmap.org" in u for u in ngoai), ngoai


def test_ghi_cong_openstreetmap(client):
    # Điều kiện trong chính chính sách dùng tile của OSM. Thiếu = dùng sai
    # giấy phép, không phải thiếu thẩm mỹ.
    html = client.get("/ban-do").text
    assert "OpenStreetMap" in html
    assert "openstreetmap.org/copyright" in html


def test_bang_47_dong_hien_o_CA_HAI_che_do(client, batch):
    # Tile bị tường lửa chặn thì bản đồ là một ô trống. Bảng là đường đọc
    # chính thức, phải có ở mọi chế độ.
    for che_do in ("", "?che_do=luoi"):
        html = client.get("/ban-do" + che_do).text
        bang = _khoi(html, "Bảng xếp hạng 47 tỉnh")
        assert bang.count("<tr") >= 47


def test_che_do_luoi_van_ve_47_o_svg(client, batch):
    html = client.get("/ban-do?che_do=luoi").text
    assert len(re.findall(r'<g class="o"', html)) == 47


def test_trang_noi_ro_cham_dat_o_THU_PHU_khong_phai_vi_tri_khach(client):
    # Không nói ra thì người bán đọc bản đồ như một danh sách địa chỉ.
    html = client.get("/ban-do").text
    assert "thủ phủ" in html.lower()


def test_du_lieu_cham_nhung_thang_vao_trang_khong_goi_API(client, batch):
    # Ngân sách 2 lượt hỏi chỉ đúng nếu trang không đi hỏi thêm sau khi tải.
    html = client.get("/ban-do").text
    assert "fetch(" not in html and "XMLHttpRequest" not in html
```

- [ ] **Bước 3: chạy để thấy ĐỎ.**

- [ ] **Bước 4: dựng**

`kome/ban_do.py`: thêm `vi_do`/`kinh_do` vào truy vấn A và vào `O`; thêm `che_do`; dựng
`diem_json` bằng `json.dumps` rồi escape cho an toàn khi nhúng trong `<script
type="application/json">` (nhúng JSON vào HTML là chỗ kinh điển để lọt `</script>` — dùng
`json.dumps(...).replace("<", "\\u003c")` hoặc tương đương, và có test gieo một tên tỉnh
chứa `</script>`).

`ban_do.html`:
- `<script type="application/json" id="diem">` chứa dữ liệu; một đoạn JS ngắn đọc nó rồi
  dựng `L.map` + `L.circleMarker`. **Chỉ chỗ này được có JS**, và nó không được gọi mạng
  ngoài tile.
- Bán kính chấm theo `gia_tri` — dùng **căn bậc hai** của giá trị, không dùng tuyến tính:
  mắt người đọc DIỆN TÍCH chấm, nên bán kính tuyến tính làm 東京都 to gấp 29 lần về bán
  kính và gấp ~840 lần về diện tích. Ghi chú tại chỗ.
- Mỗi chấm có popup: tên tỉnh · số khách · doanh thu · cần gọi · liên kết
  `/khach-hang?tinh=…` (mã hoá URL).
- Ghi công OSM ở `attribution` của lớp tile.
- Dải chọn chế độ: `Bản đồ` / `Lưới ô` — là **liên kết**, không phải JS.
- Câu nói rõ chấm đặt ở **thủ phủ tỉnh**, không phải vị trí từng khách.

- [ ] **Bước 5: chạy test cho xanh, rồi chạy cả bộ.**

- [ ] **Bước 6: commit.**

---

## Task 3: Tài liệu

**Files:** Sửa `CLAUDE.md`

- [ ] **Bước 1:** cập nhật bất biến "không tài nguyên ngoài". Nó **không còn đúng nguyên
      văn** — phải ghi lại chính xác: app tự host mọi thứ (font, Leaflet), và có **đúng
      MỘT** phụ thuộc mạng ngoài là **tile của OpenStreetMap**, chỉ ở `/ban-do`, chỉ khi
      chế độ bản đồ. Ghi rõ: ghi công OSM là bắt buộc theo giấy phép, và trang phải còn
      dùng được khi tile bị chặn (`?che_do=luoi` + bảng 47 dòng).

- [ ] **Bước 2:** thêm bất biến:

```markdown
**Bất biến:** chấm trên `/ban-do` đặt ở **thủ phủ tỉnh** (`core.dim_prefecture.vi_do/
kinh_do`, migration `026`), KHÔNG phải vị trí của từng khách — OBC không có toạ độ khách và
sẽ không có. Trang phải nói ra điều này. Cột toạ độ đó cũng KHÔNG dùng để tính khoảng cách
giao hàng: thủ phủ không phải trọng tâm tỉnh.

**Bất biến:** bán kính chấm tỉ lệ với **căn bậc hai** của giá trị, không tuyến tính. Mắt
người đọc DIỆN TÍCH chấm: 東京都 có 290 khách và 佐賀県 có 1 thì bán kính tuyến tính cho ra
chênh lệch diện tích ~84.000 lần, và bốn mươi tỉnh nhỏ biến mất thành chấm kim.
```

- [ ] **Bước 3:** ghi số phiên bản Leaflet đang tự host.

- [ ] **Bước 4:** chạy cả bộ, commit.

---

## Tự soát kế hoạch

| Ràng buộc | Task |
|---|---|
| Toạ độ 47 tỉnh | 1 |
| Toạ độ khớp hướng đông–tây với lưới ô | 1 |
| Tự host Leaflet, không CDN | 2 |
| Ghi công OSM | 2 |
| Còn dùng được khi tile bị chặn | 2 |
| Chấm ở thủ phủ, nói rõ | 2, 3 |
| Bán kính theo căn bậc hai | 2, 3 |
| Không thêm lượt hỏi, không gọi API | 2 |
| Tài liệu | 3 |
