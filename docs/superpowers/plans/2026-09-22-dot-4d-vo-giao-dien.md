# Đợt 4d — Vỏ giao diện: icon, logo, nút đổi sáng/tối

> **Cho người thực thi:** BẮT BUỘC dùng sub-skill superpowers:subagent-driven-development
> để làm theo từng task. Các bước dùng cú pháp checkbox (`- [ ]`).

**Mục tiêu:** đóng ba khoảng cách còn lại giữa app và gói thiết kế `design_handoff_kome`.

**Kiến trúc:** icon SVG nội tuyến trong `_nav.html` (chép nguyên từ `kome-nav.js` của gói
thiết kế); logo là file tĩnh; nút đổi giao diện chạy bằng **cookie + render phía máy chủ**,
không một dòng JS.

**Tech stack:** Starlette · Jinja2 · CSS custom properties · pytest.

**Đặc tả:** không có file đặc tả riêng. Ba việc này đã được đối chiếu trực tiếp với
`README.md` của gói thiết kế và được chủ dự án duyệt trong hội thoại. Bối cảnh ở ngay dưới.

## Bối cảnh — đã đo, không phải phỏng đoán

Đối chiếu `README.md` của gói handoff với `kome/web/static/kome.css`: **màu, chữ và bố
cục đã khớp chính xác** — nền `#FBF9F5`, thẻ `#FFFFFF`, nền chìm `#F6F3EC`, viền
`#E6E2D9`/`#F0EDE6`/`#D8D3C8`, đỏ công ty `#D62C27`, đỏ chữ `#B4231C`, xanh tăng
`#1E7A4D`; bảng tối `#17140F`/`#211D17`/`#342E26`/`#F4EFE6`; sidebar `196px`, nội dung
tối đa `1400px`, padding `1.1rem` đáy `3rem`. Không có việc phải làm ở đó.

Ba chỗ CHƯA khớp, và đây là toàn bộ phạm vi đợt này:

1. **Sidebar không có icon.** Gói thiết kế quy định 24 icon SVG vẽ tay trong `kome-nav.js`
   (object `I`), viewBox `0 0 18 18`, `stroke-width:1.4`, `stroke-linecap:round`, KHÔNG fill.
2. **Không có logo.** `kome-logo.png` tròn, hiện 28px ở đầu sidebar; nay đang là chữ "KOME".
3. **Không có nút đổi sáng/tối.** README muốn `sáng | tối | theo hệ thống` + tuỳ chọn tự
   đổi theo giờ (18:00–06:00 là tối). Nó thuộc màn Cài đặt (số 22), mà đợt 3 **cắt có chủ
   ý** (đặc tả đợt 3 §4.2: với 5–7 tài khoản đặt một lần thì một script đúng hơn một màn
   hình). Quyết định đó vẫn đúng cho phần quản lý người dùng, nhưng nó kéo theo mất luôn
   nút đổi giao diện — đợt này trả lại, đặt ở chân sidebar. Khi nào dựng màn Cài đặt thì
   chuyển vào đó.

## Global Constraints

Áp cho MỌI task:

- **KHÔNG một dòng JS máy khách nào trong đợt này.** README của gói thiết kế nói lưu lựa
  chọn ở `localStorage`; ta làm bằng **cookie + render phía máy chủ**. Lệch có chủ ý, hai
  lý do: app hiện chưa có JS nào, và cách cookie tránh được "nháy sai màu" lúc tải trang
  (`localStorage` đọc sau khi HTML đã vẽ). Hành vi người dùng thấy là như nhau.
- `kome/web/app.py` KHÔNG được nhập `kome.pipeline`/pandas ở mức ngoài cùng. Có test canh:
  `tests/test_bao_mat.py::test_trang_chi_doc_khong_phu_thuoc_pandas`.
- Mọi mã hoá bằng màu phải kèm một thứ ĐỌC ĐƯỢC — **icon KHÔNG được thay chữ**, chỉ đứng
  cạnh chữ. Sidebar vẫn phải đọc được khi icon không tải/không hiện.
- Icon phải có `aria-hidden="true"` và `focusable="false"`: nó là trang trí, chữ mới là
  nhãn. Trình đọc màn hình đọc hai lần cùng một mục là tệ hơn không có icon.
- Không đổi một giá trị token màu nào đang có (chúng đã khớp gói thiết kế).
- Mốc test hiện tại trên nhánh: **395 xanh** (+ 11 của `test_roles`/`test_migrate`).
- Chạy test ở TIỀN CẢNH bằng `python -u -m pytest`, KHÔNG pipe qua `tail`.

---

## Task 1: Icon và logo trong sidebar

**Files:**
- Sửa: `kome/web/templates/_nav.html`, `kome/web/static/kome.css`
- Tạo: `kome/web/static/kome-logo.png` (chép từ gói thiết kế)
- Test: `tests/test_giao_dien.py`

**Interfaces:**
- Produces: mỗi mục điều hướng có dạng `<a href=…><svg class="ic" …>…</svg>Nhãn</a>`.

- [ ] **Bước 1: chép logo**

Chép `C:\Users\TRANTR~1\AppData\Local\Temp\claude\C--Antigravity-kome-data\3e5c9d1d-ad41-46bc-bd32-c6f6376347e0\scratchpad\dsg\design_handoff_kome\screens\kome-logo.png`
sang `kome/web/static/kome-logo.png` (90 KB). Đây là tài sản của chính gói thiết kế.

- [ ] **Bước 2: viết test đỏ trước** — nối vào `tests/test_giao_dien.py`:

```python
def test_moi_muc_dieu_huong_co_icon_VA_van_con_chu(client):
    # Icon là trang trí, chữ mới là nhãn. Bất biến "màu/hình phải kèm thứ đọc
    # được" (_chung.html:76-77) áp cả ở đây: bỏ chữ đi thì sidebar thành tám ô
    # vuông không ai đoán được.
    html = client.get("/").text
    nav = re.search(r'<nav class="dieu-huong">(.*?)</nav>', html, re.S).group(1)
    muc = re.findall(r"<a [^>]*href=\"(/[^\"]*)\"[^>]*>(.*?)</a>", nav, re.S)
    assert len(muc) >= 8
    for duong_dan, ben_trong in muc:
        assert "<svg" in ben_trong, f"{duong_dan} thiếu icon"
        chu = re.sub(r"<svg.*?</svg>", "", ben_trong, flags=re.S).strip()
        assert len(chu) >= 3, f"{duong_dan} mất chữ, chỉ còn icon"


def test_icon_dieu_huong_an_voi_trinh_doc_man_hinh(client):
    # Đọc hai lần cùng một mục còn tệ hơn không có icon.
    html = client.get("/").text
    nav = re.search(r'<nav class="dieu-huong">(.*?)</nav>', html, re.S).group(1)
    for the in re.findall(r"<svg[^>]*>", nav):
        assert 'aria-hidden="true"' in the, the
        assert 'focusable="false"' in the, the


def test_logo_hien_trong_sidebar(client):
    html = client.get("/").text
    assert "/static/kome-logo.png" in html
```

- [ ] **Bước 3: chạy để thấy ĐỎ**

Chạy: `python -u -m pytest tests/test_giao_dien.py -v`
Mong đợi: FAIL — chưa có `<svg` trong điều hướng.

- [ ] **Bước 4: thêm icon và logo vào `_nav.html`**

Chín icon dưới đây chép **nguyên văn** từ object `I` trong `kome-nav.js` của gói thiết kế.
Bọc mỗi cái trong:

```html
<svg class="ic" viewBox="0 0 18 18" aria-hidden="true" focusable="false">…</svg>
```

Ánh xạ mục → icon. Sáu mục đầu lấy đúng ánh xạ của gói thiết kế (`NHOM` trong
`kome-nav.js`); hai mục cuối gói thiết kế không có mục tương đương nên chọn trong chính
bộ 24 icon đó — ghi chú lại trong template là ta chọn, không phải thiết kế chọn:

| Mục | Icon | Nguồn ánh xạ |
|---|---|---|
| Tổng quan | `dashboard` | thiết kế |
| Báo cáo doanh thu | `chart` | thiết kế |
| Khách hàng | `user` | thiết kế |
| Sản phẩm | `cube` | thiết kế |
| Kho hàng | `box` | thiết kế |
| Kho dữ liệu | `db` | thiết kế |
| Cần xử lý | `bell` | **ta chọn** — thiết kế không có mục này |
| Bản đồ | `pin` | **ta chọn** — thiết kế gộp bản đồ vào "Khách hàng & bản đồ" |
| Đăng xuất | `out` | thiết kế |

```
dashboard: <rect x="2.5" y="2.5" width="5" height="5" rx="1"></rect><rect x="10.5" y="2.5" width="5" height="5" rx="1"></rect><rect x="2.5" y="10.5" width="5" height="5" rx="1"></rect><rect x="10.5" y="10.5" width="5" height="5" rx="1"></rect>

chart: <path d="M3 14.5V8m4 6.5V4.5m4 10V10m4 4.5V6"></path>

user: <circle cx="9" cy="6" r="2.6"></circle><path d="M3.5 15c0-2.8 2.5-4.5 5.5-4.5s5.5 1.7 5.5 4.5"></path>

bell: <path d="M9 2.6a4.2 4.2 0 0 0-4.2 4.2c0 3.4-1.4 4.6-1.4 4.6h11.2s-1.4-1.2-1.4-4.6A4.2 4.2 0 0 0 9 2.6z"></path><path d="M7.6 14a1.6 1.6 0 0 0 2.8 0"></path>

pin: <path d="M9 16s5.2-5 5.2-8.6A5.2 5.2 0 0 0 9 2.2a5.2 5.2 0 0 0-5.2 5.2C3.8 11 9 16 9 16z"></path><circle cx="9" cy="7.3" r="1.8"></circle>

cube: <path d="M9 2.2 15.4 5.6v6.8L9 15.8 2.6 12.4V5.6z"></path><path d="M2.6 5.6 9 9l6.4-3.4M9 9v6.8"></path>

box: <path d="M2.6 5.4 9 2.2l6.4 3.2v7.2L9 15.8l-6.4-3.2z"></path><path d="M2.6 5.4 9 8.6l6.4-3.2M9 8.6v7.2"></path>

db: <ellipse cx="9" cy="4.6" rx="6" ry="2.2"></ellipse><path d="M3 4.6v8.8c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V4.6"></path><path d="M3 9c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2"></path>

out: <path d="M11.4 5.4V4a1.6 1.6 0 0 0-1.6-1.6H4.6A1.6 1.6 0 0 0 3 4v10a1.6 1.6 0 0 0 1.6 1.6h5.2a1.6 1.6 0 0 0 1.6-1.6v-1.4"></path><path d="M7.4 9h8"></path><path d="M13 6.6 15.4 9 13 11.4"></path>
```

Logo: thay `<a class="hieu" href="/">KOME</a>` thành logo 28px + chữ KOME cạnh nhau.
README gói thiết kế ghi: *"logo tròn, hiển thị 28px trong sidebar (nền tối thì bọc nền
sáng, bo tròn)"* — nên ở chế độ tối phải có nền sáng bọc quanh, không để logo chìm.

- [ ] **Bước 5: CSS cho icon** — thêm vào `kome.css`:

Icon `1.05em` vuông, `fill:none`, `stroke:currentColor`, `stroke-width:1.4`,
`stroke-linecap:round`, `stroke-linejoin:round`, `flex-shrink:0`. Mục điều hướng thành
`display:flex; align-items:center; gap:.55rem`. Icon thừa hưởng màu chữ, nên mục đang xem
tự đổi màu icon theo — không viết màu riêng cho icon.

Ở màn hẹp (`@media (max-width:720px)`) sidebar nằm ngang; kiểm icon không làm vỡ bố cục đó.

- [ ] **Bước 6: chạy test cho xanh** — `python -u -m pytest tests/test_giao_dien.py -v`

- [ ] **Bước 7: chạy cả bộ**

`python -u -m pytest -q --ignore=tests/test_roles.py --ignore=tests/test_migrate.py`
rồi `python -u -m pytest -q tests/test_roles.py tests/test_migrate.py`

- [ ] **Bước 8: commit** (thông điệp chỉ ASCII, không dấu tiếng Việt, không backtick).

---

## Task 2: Nút đổi giao diện — cookie, không JS

**Files:**
- Sửa: `kome/web/app.py`, `kome/web/templates/_chung.html`, `_nav.html`,
  `kome/web/static/kome.css`
- Test: `tests/test_giao_dien.py`

**Interfaces:**
- Consumes: giờ Asia/Tokyo — **dùng lại đúng hàm đang có** trong `kome/tuoi_du_lieu.py`,
  đừng viết bản thứ hai (đọc file đó trước).
- Produces: route `GET /giao-dien`, cookie `kome_giao_dien`, thuộc tính
  `<html data-theme="sang|toi">` (không đặt thuộc tính khi chế độ là `he-thong`).

**Bốn chế độ:** `he-thong` (mặc định) · `sang` · `toi` · `theo-gio` (18:00–06:00 giờ Nhật
là tối).

- [ ] **Bước 1: viết test đỏ trước**

```python
def test_mac_dinh_theo_he_thong_thi_KHONG_dat_data_theme(client):
    # Không đặt thuộc tính = để @media prefers-color-scheme quyết định.
    # Đặt cứng một giá trị là ép mọi người dùng mới vào một chế độ.
    html = client.get("/").text
    assert "data-theme=" not in html.split("</head>")[0]


def test_chon_sang_thi_ep_sang_KE_CA_khi_he_thong_dang_toi(client):
    r = client.get("/giao-dien?che_do=sang", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "kome_giao_dien=sang" in r.headers["set-cookie"]
    html = client.get("/", cookies={"kome_giao_dien": "sang"}).text
    assert 'data-theme="sang"' in html


def test_che_do_la_bay_khong_lam_no_trang(client):
    # Tham số URL gõ sai không được làm trang chết.
    r = client.get("/giao-dien?che_do=<script>", follow_redirects=False)
    assert r.status_code in (302, 303)
    html = client.get("/", cookies={"kome_giao_dien": "<script>"}).text
    assert "<script>" not in html
    assert "data-theme=" not in html.split("</head>")[0]


def test_theo_gio_doi_theo_gio_NHAT_khong_theo_gio_may_chu(monkeypatch, client):
    # CSDL chạy UTC; lấy giờ máy chủ thì 18:00 giờ Nhật vẫn là 09:00 UTC và
    # trang sáng trưng suốt buổi tối. Cùng cái bẫy mà ô "hôm nay đã có dữ liệu
    # chưa" đã ghi trong CLAUDE.md.
    # Gieo 20:00 giờ Nhật -> tối; 10:00 giờ Nhật -> sáng.
    ...


def test_hai_khoi_mau_toi_trong_css_GIONG_HET_NHAU():
    # Bảng tối phải viết HAI lần (một trong @media, một cho [data-theme="toi"])
    # vì CSS không gộp được hai selector đó. Hai bản trôi khỏi nhau là chọn
    # "tối" tay ra một bộ màu khác với "tối" theo hệ thống — và không ai thấy
    # cho tới khi nhìn hai máy cạnh nhau.
    css = Path("kome/web/static/kome.css").read_text(encoding="utf-8")
    khoi = re.findall(r"/\* BANG-TOI \*/(.*?)/\* HET-BANG-TOI \*/", css, re.S)
    assert len(khoi) == 2
    assert khoi[0].strip() == khoi[1].strip()
```

Test `theo_gio` gieo giờ bằng `monkeypatch` lên chính hàm giờ Nhật của
`kome/tuoi_du_lieu.py` — đọc file đó và test hiện có của nó để dùng lại đúng cách.

- [ ] **Bước 2: chạy để thấy ĐỎ** — `python -u -m pytest tests/test_giao_dien.py -v`

- [ ] **Bước 3: route `/giao-dien`**

Nhận `?che_do=`, chỉ chấp nhận bốn giá trị hợp lệ (giá trị lạ → `he-thong`), đặt cookie
`kome_giao_dien` (`httponly=False` không cần; `samesite="lax"`, `max_age` 1 năm, `secure`
theo đúng hàm `_chi_gui_qua_https` đang có trong `app.py` — đọc và dùng lại, đừng viết
điều kiện HTTPS thứ hai), rồi **redirect về trang gọi nó**.

Quan trọng: redirect chỉ được về **đường dẫn nội bộ**. Lấy từ header `Referer` nhưng
**chỉ giữ phần path** và bỏ nếu nó không bắt đầu bằng `/` — nhận nguyên `Referer` rồi
`RedirectResponse` là mở một cửa chuyển hướng ra ngoài. Không có `Referer` hợp lệ thì về `/`.

- [ ] **Bước 4: `_chung.html` đặt `data-theme`**

Chế độ `sang`/`toi` → đặt thẳng. Chế độ `theo-gio` → máy chủ tính theo giờ Nhật rồi đặt
`sang` hoặc `toi`. Chế độ `he-thong` → **không đặt thuộc tính nào**.

- [ ] **Bước 5: CSS**

Bọc bảng màu tối bằng hai mốc chú thích `/* BANG-TOI */ … /* HET-BANG-TOI */` và viết
đúng hai lần:

```css
@media (prefers-color-scheme: dark){
  :root:not([data-theme="sang"]){ /* BANG-TOI */ … /* HET-BANG-TOI */ }
}
:root[data-theme="toi"]{ /* BANG-TOI */ … /* HET-BANG-TOI */ }
```

`:root:not([data-theme="sang"])` chứ không phải `:root`: chọn "sáng" tay phải thắng cả khi
hệ thống đang tối. Có test canh hai khối giống hệt nhau (Bước 1).

- [ ] **Bước 6: nút ở chân sidebar**

Bốn liên kết `?che_do=…` trong `_nav.html`, đánh dấu cái đang chọn. Là **liên kết**, không
phải JS. Nhãn tiếng Việt: Sáng · Tối · Theo hệ thống · Theo giờ.

- [ ] **Bước 7: chạy test cho xanh, rồi chạy cả bộ** (hai lệnh như Task 1).

- [ ] **Bước 8: commit.**

---

## Task 3: Tài liệu

**Files:** Sửa `CLAUDE.md`

- [ ] **Bước 1:** thêm `/giao-dien` vào bảng "Các trang của web app" (cột dữ liệu: không đọc
      CSDL).

- [ ] **Bước 2:** thêm hai bất biến:

```markdown
**Bất biến:** lựa chọn sáng/tối lưu bằng **cookie + render phía máy chủ**, KHÔNG bằng
`localStorage`. Gói thiết kế ghi `localStorage`; ta lệch có chủ ý vì `localStorage` chỉ đọc
được sau khi HTML đã vẽ, nên mỗi lần tải trang người dùng thấy một nháy sai màu. Đổi sang
`localStorage` là mua lại đúng cái nháy đó.

**Bất biến:** bảng màu tối viết HAI lần trong `kome.css` — một lần trong
`@media (prefers-color-scheme: dark){ :root:not([data-theme="sang"]) }`, một lần cho
`:root[data-theme="toi"]` — vì CSS không gộp được hai selector đó vào một khối. Hai bản
PHẢI giống hệt nhau; trôi khỏi nhau là "tối" chọn tay ra một bộ màu khác "tối" theo hệ
thống, và không ai thấy cho tới khi đặt hai máy cạnh nhau. Có test canh:
`tests/test_giao_dien.py::test_hai_khoi_mau_toi_trong_css_GIONG_HET_NHAU`.
```

- [ ] **Bước 3:** trong mục nói về giao diện, ghi rõ **icon là trang trí, chữ mới là nhãn**
      (`aria-hidden="true"`, `focusable="false"`), và icon chép nguyên từ `kome-nav.js` của
      gói thiết kế — hai mục `Cần xử lý` (`bell`) và `Bản đồ` (`pin`) là **ta chọn**, vì gói
      thiết kế không có mục tương đương.

- [ ] **Bước 4:** chạy cả bộ, commit.

---

## Tự soát kế hoạch

| Việc | Task |
|---|---|
| Icon 24 bộ của gói thiết kế | 1 |
| Logo `kome-logo.png` 28px | 1 |
| Nút sáng / tối / theo hệ thống / theo giờ | 2 |
| Giờ Nhật chứ không giờ máy chủ | 2 |
| Chuyển hướng chỉ về đường dẫn nội bộ | 2 |
| Hai khối màu tối không được trôi khỏi nhau | 2 |
| Tài liệu | 3 |
