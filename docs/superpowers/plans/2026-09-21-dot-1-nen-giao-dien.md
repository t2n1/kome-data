# Đợt 1 — Nền giao diện: Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa 8 trang web đang chạy sang bảng màu, font và khung điều hướng của gói thiết kế `design_handoff_kome`, không đổi một dòng dữ liệu nào.

**Architecture:** Bốn bước tách rời, mỗi bước tự kiểm chứng được. (1) Chuyển khối CSS trong `_chung.html` ra `kome/web/static/kome.css` **giữ nguyên từng giá trị** — nếu trang hỏng thì hỏng vì việc chuyển, không phải vì màu. (2) Thay giá trị token sang bảng thiết kế. (3) Font tự host. (4) Đổi thanh điều hướng ngang hai tầng thành sidebar trái.

**Tech Stack:** FastAPI + Jinja2 + `StaticFiles` (có sẵn trong FastAPI, không thêm gói). CSS custom properties thuần. Không npm, không bundler, không JavaScript mới trong đợt này.

**Spec:** `docs/superpowers/specs/2026-09-21-lo-trinh-24-man-hinh-design.md` §6

## Global Constraints

- **Không đụng CSDL.** Không migration, không đổi truy vấn, không đổi `kome/db.py`.
- **`kome/web/app.py` KHÔNG được nhập `kome.pipeline`, `pandas`, `python-calamine` ở mức ngoài cùng** — chỉ nhập trong thân route. Test canh: `tests/test_bao_mat.py::test_trang_chi_doc_khong_phu_thuoc_pandas`.
- **Không thêm phụ thuộc mạng lúc chạy.** Không Google Fonts, không CDN. (Spec §5)
- **Không thêm gói vào `requirements.txt`.** `StaticFiles` nằm sẵn trong FastAPI.
- **Mọi ô mã hoá bằng màu phải kèm thứ đọc được** — số, hoặc `▲ ▼`. (Spec §6.5)
- **Mọi biến màu định nghĩa ở `:root` phải có bản tối tương ứng.** Thiếu một cặp là chữ sẫm trên nền sẫm. (Lý do khối token ra đời — ghi chú `_chung.html:1-10`)
- **Không đổ bóng.** Phân tầng bằng viền `1px solid var(--vien)` trên nền giấy.
- Thông điệp commit: **không dấu**, tiền tố `feat:` / `refactor:` / `test:` theo nếp repo.
- Sau mỗi task: `pytest -v` phải xanh toàn bộ, không chỉ test mới.

---

## File Structure

| File | Trách nhiệm | Task |
|---|---|---|
| `kome/web/static/kome.css` | **Tạo mới.** Nguồn duy nhất của mọi màu, cỡ chữ, khoảng cách, thành phần dùng lại | 1, 2, 4 |
| `kome/web/static/fonts/*.woff2` | **Tạo mới.** IBM Plex Sans 400/500/600/700 + IBM Plex Mono 400/500/600, bản Latin | 3 |
| `kome/web/templates/_chung.html` | Thu lại còn `<meta color-scheme>` + `<link>` tới `kome.css`. Không còn chứa CSS | 1 |
| `kome/web/templates/_nav.html` | Sidebar trái 196px, nhóm theo phân loại của thiết kế | 4 |
| `kome/web/app.py` | Thêm `app.mount("/static", …)`. Không đổi gì khác | 1 |
| `tests/test_giao_dien.py` | **Tạo mới.** Toàn bộ test của đợt này | 1–4 |

Mười sáu template còn lại **không sửa** ở task 1–3: chúng dùng `var(--…)` chứ không dùng mã màu (đã kiểm: `grep -l '#[0-9A-Fa-f]\{6\}' kome/web/templates/*.html` chỉ trả về `_chung.html`). Task 4 đụng chúng, nhưng chỉ ở chỗ bọc nội dung.

---

## Task 1: Tách CSS ra `static/`, không đổi một giá trị nào

Đây là một **phép chuyển thuần tuý**. Không đổi màu, không đổi cỡ chữ, không đổi gì. Mục đích: nếu trang hỏng sau task này, nguyên nhân là việc chuyển; nếu hỏng sau task 2, nguyên nhân là màu. Gộp hai việc thì không phân biệt được.

**Files:**
- Create: `kome/web/static/kome.css`
- Create: `tests/test_giao_dien.py`
- Modify: `kome/web/templates/_chung.html` (thay toàn bộ)
- Modify: `kome/web/app.py` (thêm mount, ~2 dòng)

**Interfaces:**
- Produces: đường dẫn tĩnh `/static/kome.css`; hằng `CSS = Path("kome/web/static/kome.css")` trong `tests/test_giao_dien.py` mà task 2–4 dùng lại.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_giao_dien.py`:

```python
"""Test của đợt 1 — nền giao diện.

Không có test nào ở đây chạm CSDL. Chúng đọc file và đọc HTML trả về.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from kome.web.app import create_app

CSS = Path("kome/web/static/kome.css")
TEMPLATES = Path("kome/web/templates")

# Mọi trang mở được mà không cần tham số. Trang hồ sơ khách và trang lỗi
# không nằm đây vì chúng cần dữ liệu hoặc một sự cố để hiện ra.
TRANG = ["/", "/khach-hang", "/bao-cao", "/can-xu-ly", "/health", "/phu-du-lieu"]


def test_css_duoc_phuc_vu(conn, test_db_url):
    """/static/kome.css phải trả về 200 và đúng kiểu nội dung.

    Chặn thảm hoạ: quên mount StaticFiles -> mọi trang mất sạch kiểu dáng
    nhưng vẫn trả 200, nên không test nào khác đỏ.
    """
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/static/kome.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
    assert "--nen" in r.text


def test_moi_trang_deu_noi_toi_css(conn, test_db_url):
    """Chặn thảm hoạ: một trang quên include _chung.html -> trang đó trơ
    trụi trong khi bảy trang kia đẹp, và không ai để ý cho tới khi mở đúng
    trang đó."""
    client = TestClient(create_app(db_url=test_db_url))
    for duong_dan in TRANG:
        r = client.get(duong_dan)
        assert r.status_code == 200, duong_dan
        assert "/static/kome.css" in r.text, duong_dan


def test_khong_ma_mau_nao_ngoai_kome_css():
    """Mọi màu chỉ có MỘT nhà. Chặn thảm hoạ: ai đó gõ thẳng #fff vào một
    template -> trang đó trắng toát ở chế độ tối, trong khi test màu vẫn
    xanh vì nó chỉ soi kome.css."""
    for f in sorted(TEMPLATES.glob("*.html")):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"#[0-9A-Fa-f]{6}\b", text), f"{f.name} chứa mã màu"
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `pytest tests/test_giao_dien.py -v`
Expected: FAIL — `test_css_duoc_phuc_vu` trả 404, `test_moi_trang_deu_noi_toi_css` không tìm thấy chuỗi, `test_khong_ma_mau_nao_ngoai_kome_css` đỏ vì `_chung.html` còn 14 dòng mã màu.

- [ ] **Step 3: Chuyển CSS ra file**

Tạo `kome/web/static/kome.css` chứa **đúng nội dung giữa `<style>` và `</style>` của `_chung.html` hiện tại**, không sửa một ký tự nào trong phần CSS. Thêm lên đầu file ghi chú đã có trong `_chung.html` (khối `{# … #}` dòng 1–9), chuyển sang cú pháp CSS:

```css
/* Nguồn DUY NHẤT của mọi màu trong app.

   Vì sao phải khai tường minh: trước đây các trang không đặt `color-scheme`
   cũng không đặt màu nền/màu chữ. Máy nào để giao diện TỐI thì trình duyệt
   vẽ nền tối còn chữ vẫn là màu sẫm mặc định của trang -> chữ sẫm trên nền
   sẫm, gần như không đọc được. Nguyên tắc nền tảng của hệ thống này là "sai
   phải THẤY NGAY trên màn hình"; một trang không đọc được thì không cảnh
   báo được gì cả.

   Bất biến: mọi biến khai ở :root PHẢI có bản tối tương ứng trong khối
   @media bên dưới. Có test canh — tests/test_giao_dien.py. */
```

- [ ] **Step 4: Thu `_chung.html` lại**

Thay **toàn bộ** `kome/web/templates/_chung.html` bằng:

```html
{# Phần <head> dùng chung cho mọi trang.

   Mọi màu và kiểu dáng nằm ở kome/web/static/kome.css — một file, một nhà.
   Trang nào quên include partial này thì mất sạch kiểu dáng; có test canh
   (tests/test_giao_dien.py::test_moi_trang_deu_noi_toi_css). #}
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="/static/kome.css">
```

- [ ] **Step 5: Mount thư mục tĩnh**

Trong `kome/web/app.py`, thêm vào nhóm import ở đầu file:

```python
from fastapi.staticfiles import StaticFiles
```

Trong `create_app()`, ngay sau dòng `app = FastAPI(title="KOME — dữ liệu")`:

```python
    # Phục vụ CSS và font từ đĩa. Dùng StaticFiles có sẵn trong FastAPI —
    # KHÔNG thêm gói nào vào requirements.txt (bản Vercel cố ý mỏng).
    app.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).parent / "static")),
        name="static",
    )
```

`Path` đã được nhập sẵn ở đầu `app.py` (dùng cho `TEMPLATES` và `archive_dir`) — không thêm import.

- [ ] **Step 6: Chạy test để chắc nó xanh**

Run: `pytest tests/test_giao_dien.py -v`
Expected: PASS — cả ba test.

- [ ] **Step 7: Chạy toàn bộ bộ test**

Run: `pytest -v`
Expected: PASS toàn bộ. Đặc biệt `tests/test_bao_mat.py::test_trang_chi_doc_khong_phu_thuoc_pandas` phải còn xanh — task này có sửa `app.py`.

- [ ] **Step 8: Xem tận mắt**

Run: `uvicorn kome.web.app:app --reload`
Mở `http://localhost:8000/` ở cả chế độ sáng và tối của hệ điều hành. Trang phải trông **y hệt trước khi sửa**. Nếu khác một chút nào, việc chuyển đã làm rơi mất thứ gì đó — tìm ra trước khi đi tiếp.

- [ ] **Step 9: Commit**

```bash
git add kome/web/static/kome.css kome/web/templates/_chung.html kome/web/app.py tests/test_giao_dien.py
git commit -m "refactor: tach CSS chung ra kome/web/static/kome.css, mount StaticFiles"
```

---

## Task 2: Thay giá trị token sang bảng màu thiết kế

**Files:**
- Modify: `kome/web/static/kome.css` (khối `:root` và khối `@media dark`, cộng `.loc a.dang-xem`)
- Modify: `tests/test_giao_dien.py` (thêm test)

**Interfaces:**
- Consumes: `CSS` từ task 1.
- Produces: các biến mới `--nen-the`, `--vien-phu`, `--vien-dam`, `--chu-thuong`, `--chu-mo`, `--do`, `--do-chu`, `--do-nen` mà task 4 dùng cho sidebar.

Cặp màu tối **không phải đoán** — lấy từ bảng `MAP` trong `kome-theme.js:9-49` của gói thiết kế. `#D62C27` (đỏ công ty) không có trong bảng đó: thiết kế cố ý giữ nguyên nó ở cả hai chế độ, xem `kome-nav.js:213` dùng thẳng mã này cho huy hiệu trong cả hai theme.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `tests/test_giao_dien.py`:

```python
def _bien_khai(khoi: str) -> set[str]:
    """Tên các biến được ĐỊNH NGHĨA trong một khối CSS.

    Chỉ khớp `--x:` (định nghĩa), không khớp `var(--x)` (sử dụng) — nên
    phần thân dưới file, vốn chỉ dùng biến, không lọt vào."""
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", khoi))


def test_moi_bien_mau_deu_co_ban_toi():
    """Chặn thảm hoạ đã từng xảy ra: thêm một biến màu, quên bản tối ->
    chữ sẫm trên nền sẫm ở máy để giao diện tối. Trang vẫn trả 200 nên
    không test nào khác bắt được."""
    css = CSS.read_text(encoding="utf-8")
    moc = "@media (prefers-color-scheme: dark)"
    assert moc in css, "mất khối màu tối"
    sang, toi = css.split(moc, 1)
    thieu = _bien_khai(sang) - _bien_khai(toi)
    assert not thieu, f"thiếu bản tối cho: {sorted(thieu)}"


def test_co_mau_hanh_dong_chinh_va_khong_con_mau_tim():
    """Bảng màu thiết kế dùng đỏ công ty #D62C27 cho hành động chính và
    trạng thái được chọn. Màu tím --chot-* của hệ cũ không còn chỗ đứng;
    để sót lại thì hai hệ màu cùng sống trong một file."""
    css = CSS.read_text(encoding="utf-8")
    assert "--do:#D62C27" in css.replace(" ", "")
    assert "--chot-" not in css
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `pytest tests/test_giao_dien.py -k "ban_toi or hanh_dong" -v`
Expected: FAIL — `test_co_mau_hanh_dong_chinh_va_khong_con_mau_tim` đỏ vì chưa có `--do` và còn `--chot-`. `test_moi_bien_mau_deu_co_ban_toi` **có thể xanh sẵn** (hệ cũ đã cân đối) — đó là đúng, nó là lưới an toàn cho bước sau chứ không phải test dẫn đường.

- [ ] **Step 3: Thay khối `:root`**

Trong `kome/web/static/kome.css`, thay khối `:root{…}` sáng bằng:

```css
 :root{
   color-scheme: light dark;
   /* Nền: trang là giấy ấm, thẻ/bảng mới là trắng. Hệ cũ dùng chung một
      màu cho cả hai — thiết kế phân tầng bằng chính sự chênh lệch này,
      vì nó không dùng đổ bóng. */
   --nen:#FBF9F5; --nen-the:#FFFFFF; --nen-phu:#F6F3EC;
   --vien:#E6E2D9; --vien-phu:#F0EDE6; --vien-dam:#D8D3C8;
   --chu:#1A1714; --chu-thuong:#474139; --chu-nhat:#6E6A63; --chu-mo:#8E8A82;
   --lien-ket:#8A5E06;
   /* Đỏ công ty: CHỈ dành cho hành động chính và trạng thái được chọn.
      Không dùng để tô cho đẹp. --do là nét/nền, --do-chu là chữ (đỏ đậm
      hơn để đủ tương phản trên nền sáng). */
   --do:#D62C27; --do-chu:#B4231C; --do-nen:#FDEDEC;
   --ok-nen:#E6F2EB;  --ok-vien:#1E7A4D;  --ok-chu:#14603E;
   --loi-nen:#FDEDEC; --loi-vien:#D62C27; --loi-chu:#B4231C;
   --canh-nen:#FFF9E8;--canh-vien:#E6D08A;--canh-chu:#8A5E06;
   --ngoai-nen:#F0EDE6;--ngoai-chu:#8E8A82;
 }
```

- [ ] **Step 4: Thay khối tối**

```css
 @media (prefers-color-scheme: dark){
   /* Từng cặp lấy từ bảng MAP trong kome-theme.js của gói thiết kế —
      không tự pha. #D62C27 không có trong bảng đó: thiết kế giữ nguyên
      đỏ công ty ở cả hai chế độ. */
   :root{
     --nen:#17140F; --nen-the:#211D17; --nen-phu:#262019;
     --vien:#342E26; --vien-phu:#2B251D; --vien-dam:#4A4239;
     --chu:#F4EFE6; --chu-thuong:#D6CFC2; --chu-nhat:#A79F92; --chu-mo:#978F83;
     --lien-ket:#E2A72E;
     --do:#D62C27; --do-chu:#F0776F; --do-nen:#3A1E1C;
     --ok-nen:#16301F;  --ok-vien:#3FA06C;  --ok-chu:#5FC492;
     --loi-nen:#3A1E1C; --loi-vien:#D62C27; --loi-chu:#F0776F;
     --canh-nen:#2E2713;--canh-vien:#4A3D14;--canh-chu:#E2A72E;
     --ngoai-nen:#2B251D;--ngoai-chu:#978F83;
   }
 }
```

- [ ] **Step 5: Sửa ba chỗ dùng biến đã bỏ**

Trong cùng file, `.loc a.dang-xem` đang dùng `--chot-*`. Thay bằng quy ước tab pill của thiết kế (nền thẻ, viền đỏ, chữ đỏ đậm, đậm nét):

```css
 .loc a.dang-xem{background:var(--nen-the);border-color:var(--do);
   color:var(--do-chu);font-weight:600}
```

`.vien.nhat` đang dùng `--ngoai-nen`/`--ngoai-chu` — hai biến này vẫn còn, không phải sửa.

Đổi thang bo góc sang thang của thiết kế (spec §6.2) — tìm và thay từng chỗ trong file:

| Chỗ | Cũ | Mới |
|---|---|---|
| `.the-so > div` | `10px` | `11px` |
| `.backup-bad`, `.loi-hop`, `.backup-ok`, `.ngay-thieu`, `.ky` | `8px` | `12px` |
| `.o-tim input[type=search]`, `.o-tim button` | `8px` | `9px` |
| `.trong` | `10px` | `12px` |
| `.vien`, `.loc a` | `999px` | `99px` |

Thêm nền thẻ cho các khối vốn dùng `--nen-phu` làm nền thẻ (thiết kế muốn thẻ trắng trên nền giấy):

```css
 .the-so > div{flex:1 1 9rem;background:var(--nen-the);border:1px solid var(--vien);
   border-radius:11px;padding:.75rem .9rem}
```

- [ ] **Step 6: Chạy test**

Run: `pytest tests/test_giao_dien.py -v`
Expected: PASS — cả năm test.

- [ ] **Step 7: Chạy toàn bộ**

Run: `pytest -v`
Expected: PASS toàn bộ.

- [ ] **Step 8: Xem tận mắt, cả hai chế độ**

Run: `uvicorn kome.web.app:app --reload`
Mở `/`, `/khach-hang`, `/bao-cao`, `/can-xu-ly`, `/health`, `/phu-du-lieu` ở **cả chế độ sáng lẫn tối**. Soi đúng ba thứ:
1. Chữ đọc được ở mọi chỗ trong chế độ tối — không có mảng nào chữ chìm vào nền.
2. Viên trạng thái (`.vien.ok`, `.vien.canh`, `.vien.loi`) vẫn đọc được bằng **chữ**, không chỉ bằng màu.
3. Biểu đồ SVG trong `/bao-cao` và `/khach-hang/{mã}` không bị lạc màu — chúng dùng `var(--…)`, nhưng đây là chỗ dễ sót nhất.

- [ ] **Step 9: Commit**

```bash
git add kome/web/static/kome.css tests/test_giao_dien.py
git commit -m "feat: ap bang mau thiet ke Kome cho toan bo web app"
```

---

## Task 3: Font tự host

**Files:**
- Create: `kome/web/static/fonts/` (7 file `.woff2`)
- Modify: `kome/web/static/kome.css` (`@font-face` + `body`/`code`/`td.so`)
- Modify: `tests/test_giao_dien.py` (thêm test)

### Sai lệch có chủ ý so với spec §6.3 — đọc trước khi làm

Spec §6.3 ghi tự host cả **Noto Sans JP 400/500**. Khi lập kế hoạch mới thấy cái giá: Noto Sans JP phủ toàn bộ CJK, bản woff2 đầy đủ nặng vài MB mỗi weight; Google phục vụ nó bằng hơn 120 mảnh `unicode-range` để trình duyệt chỉ tải phần cần. Tự host đúng cách nghĩa là cam kết ~240 file font vào một repo do một người bảo trì — va thẳng R1 ("giảm tối đa số thứ có thể hỏng").

**Kế hoạch này tự host IBM Plex Sans + Mono (bản Latin, 7 file), còn chữ Nhật dùng ngăn xếp font hệ thống.** Cả Windows (Yu Gothic UI) lẫn macOS (Hiragino Sans) đều có sẵn font Nhật dựng đàng hoàng; ý đồ của thiết kế — tên 得意先 hiện bằng một font Nhật thật, không phải font Latin đoán chữ — vẫn đạt.

**Bước cuối của task này cập nhật spec §6.3 cho khớp.** Không để kế hoạch và spec nói hai điều khác nhau.

- [ ] **Step 1: Tải font, một lần, bằng tay**

Tải bản phát hành IBM Plex từ `https://github.com/IBM/plex/releases` (giấy phép SIL OFL, cho phép nhúng và phân phối lại). Lấy đúng bảy file woff2 **bản Latin**, đặt vào `kome/web/static/fonts/` với đúng tên sau:

```
IBMPlexSans-Regular-Latin1.woff2
IBMPlexSans-Medium-Latin1.woff2
IBMPlexSans-SemiBold-Latin1.woff2
IBMPlexSans-Bold-Latin1.woff2
IBMPlexMono-Regular-Latin1.woff2
IBMPlexMono-Medium-Latin1.woff2
IBMPlexMono-SemiBold-Latin1.woff2
```

Nếu tên file trong bản phát hành khác, **đổi tên file cho khớp danh sách trên** thay vì sửa CSS — để tên trong repo không phụ thuộc vào cách IBM đặt tên ở từng bản phát hành.

- [ ] **Step 2: Viết test thất bại**

Thêm vào `tests/test_giao_dien.py`:

```python
FONTS = Path("kome/web/static/fonts")

TEN_FONT = [
    "IBMPlexSans-Regular-Latin1.woff2",
    "IBMPlexSans-Medium-Latin1.woff2",
    "IBMPlexSans-SemiBold-Latin1.woff2",
    "IBMPlexSans-Bold-Latin1.woff2",
    "IBMPlexMono-Regular-Latin1.woff2",
    "IBMPlexMono-Medium-Latin1.woff2",
    "IBMPlexMono-SemiBold-Latin1.woff2",
]


def test_du_bay_file_font_va_khong_rong():
    """Chặn thảm hoạ: @font-face trỏ tới file không có -> trình duyệt im
    lặng rơi về font hệ thống, trang vẫn 200, không ai biết."""
    for ten in TEN_FONT:
        f = FONTS / ten
        assert f.exists(), f"thiếu {ten}"
        assert f.stat().st_size > 10_000, f"{ten} có vẻ là file rỗng hoặc trang lỗi tải nhầm"


def test_khong_goi_ra_ngoai_mang():
    """Chặn thảm hoạ: một link Google Fonts lọt vào -> máy trong công ty
    mất mạng là chữ Nhật rơi về font mặc định, và đó là lúc khó nhận ra
    nhất. Spec §5 đã chốt tự host."""
    ngoai = ("fonts.googleapis.com", "fonts.gstatic.com", "cdnjs", "unpkg.com", "jsdelivr")
    canh = [CSS] + sorted(TEMPLATES.glob("*.html"))
    for f in canh:
        text = f.read_text(encoding="utf-8")
        for x in ngoai:
            assert x not in text, f"{f.name} gọi ra ngoài mạng: {x}"
```

- [ ] **Step 3: Chạy test để chắc nó đỏ**

Run: `pytest tests/test_giao_dien.py -k "font or ngoai_mang" -v`
Expected: `test_du_bay_file_font_va_khong_rong` PASS nếu step 1 đã làm xong, FAIL nếu chưa. `test_khong_goi_ra_ngoai_mang` PASS sẵn (chưa ai thêm link nào) — nó là lưới an toàn cho tương lai, không phải test dẫn đường.

- [ ] **Step 4: Khai báo `@font-face`**

Thêm lên **đầu** `kome/web/static/kome.css`, ngay sau khối ghi chú:

```css
/* Font tự host. Không gọi Google Fonts: một CDN ngoài là một thứ nữa có
   thể hỏng mà không ai trong công ty sửa được (R1). Có test canh.

   Chữ Nhật KHÔNG tự host — xem ngăn xếp --font-ui bên dưới. Noto Sans JP
   phủ toàn bộ CJK, tự host đúng cách là hơn 200 file mảnh unicode-range. */
@font-face{font-family:"IBM Plex Sans";font-style:normal;font-weight:400;
  font-display:swap;src:url("/static/fonts/IBMPlexSans-Regular-Latin1.woff2") format("woff2")}
@font-face{font-family:"IBM Plex Sans";font-style:normal;font-weight:500;
  font-display:swap;src:url("/static/fonts/IBMPlexSans-Medium-Latin1.woff2") format("woff2")}
@font-face{font-family:"IBM Plex Sans";font-style:normal;font-weight:600;
  font-display:swap;src:url("/static/fonts/IBMPlexSans-SemiBold-Latin1.woff2") format("woff2")}
@font-face{font-family:"IBM Plex Sans";font-style:normal;font-weight:700;
  font-display:swap;src:url("/static/fonts/IBMPlexSans-Bold-Latin1.woff2") format("woff2")}
@font-face{font-family:"IBM Plex Mono";font-style:normal;font-weight:400;
  font-display:swap;src:url("/static/fonts/IBMPlexMono-Regular-Latin1.woff2") format("woff2")}
@font-face{font-family:"IBM Plex Mono";font-style:normal;font-weight:500;
  font-display:swap;src:url("/static/fonts/IBMPlexMono-Medium-Latin1.woff2") format("woff2")}
@font-face{font-family:"IBM Plex Mono";font-style:normal;font-weight:600;
  font-display:swap;src:url("/static/fonts/IBMPlexMono-SemiBold-Latin1.woff2") format("woff2")}
```

- [ ] **Step 5: Thêm hai biến font và áp vào `body`**

Thêm vào khối `:root` (cả sáng — font không đổi theo chế độ nên **không** thêm vào khối tối; test parity chỉ soi biến màu nên hai biến này sẽ làm nó đỏ — vì vậy đặt chúng ở một khối `:root` **riêng**, đặt trước khối màu):

```css
 :root{
   /* Ngăn xếp: chữ Latin đi qua IBM Plex, chữ Nhật rơi xuống font hệ thống
      (Yu Gothic UI trên Windows, Hiragino Sans trên macOS). Trình duyệt tự
      chọn theo từng ký tự, nên một tên 得意先 lẫn chữ Latin vẫn đúng cả hai. */
   --font-ui:"IBM Plex Sans","Yu Gothic UI","Hiragino Sans","Noto Sans JP",system-ui,sans-serif;
   --font-so:"IBM Plex Mono",ui-monospace,SFMono-Regular,Consolas,monospace;
 }
```

Sửa `body` (đang là `font:16px/1.6 system-ui,sans-serif`):

```css
 body{font:16px/1.6 var(--font-ui);background:var(--nen);color:var(--chu);
      max-width:1100px;margin:0 auto;padding:1rem}
```

Áp font số cho mã và số liệu:

```css
 code{background:var(--nen-phu);color:var(--chu);padding:.5rem;display:block;
      overflow-x:auto;margin-top:.5rem;white-space:pre-wrap;font-family:var(--font-so)}
 td.so,th.so{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;
      font-family:var(--font-so)}
 .the-so .gia{font-size:1.45rem;font-weight:600;line-height:1.25;margin-top:.15rem;
      font-family:var(--font-so);font-variant-numeric:tabular-nums}
```

- [ ] **Step 6: Sửa test parity cho khớp**

Hai biến font nằm ở `:root` riêng phía trên và cố ý không có bản tối. Test `test_moi_bien_mau_deu_co_ban_toi` sẽ bắt chúng. Sửa hàm lọc trong `tests/test_giao_dien.py`:

```python
# Biến KHÔNG đổi theo chế độ sáng/tối: font là font, không có bản tối.
BIEN_KHONG_THEO_CHE_DO = {"--font-ui", "--font-so"}


def test_moi_bien_mau_deu_co_ban_toi():
    """Chặn thảm hoạ đã từng xảy ra: thêm một biến màu, quên bản tối ->
    chữ sẫm trên nền sẫm ở máy để giao diện tối. Trang vẫn trả 200 nên
    không test nào khác bắt được."""
    css = CSS.read_text(encoding="utf-8")
    moc = "@media (prefers-color-scheme: dark)"
    assert moc in css, "mất khối màu tối"
    sang, toi = css.split(moc, 1)
    thieu = _bien_khai(sang) - _bien_khai(toi) - BIEN_KHONG_THEO_CHE_DO
    assert not thieu, f"thiếu bản tối cho: {sorted(thieu)}"
```

- [ ] **Step 7: Chạy test**

Run: `pytest tests/test_giao_dien.py -v`
Expected: PASS — bảy test.

- [ ] **Step 8: Chạy toàn bộ**

Run: `pytest -v`
Expected: PASS toàn bộ.

- [ ] **Step 9: Xem tận mắt, và kiểm chữ Nhật**

Run: `uvicorn kome.web.app:app --reload`
Mở `/health` — trang này có tên loại file tiếng Nhật (`在庫一覧`, `得意先全情報`). Kiểm ba thứ:
1. Chữ Latin đã là IBM Plex Sans (mở DevTools → Computed → `font-family`, và tab Network thấy 1–2 file woff2 tải về từ `/static/fonts/`).
2. Chữ Nhật hiện đàng hoàng, không phải ô vuông đậu phụ (`□`).
3. Tab Network **không có** yêu cầu nào đi ra ngoài `localhost`.

- [ ] **Step 10: Cập nhật spec cho khớp**

Sửa `docs/superpowers/specs/2026-09-21-lo-trinh-24-man-hinh-design.md` §6.3, đoạn font, thành:

```
Font tự host trong `static/`: IBM Plex Sans (400/500/600/700) và IBM Plex Mono
(400/500/600), bản Latin — bảy file woff2.

**Chữ Nhật dùng ngăn xếp font hệ thống**, không tự host Noto Sans JP. Noto Sans
JP phủ toàn bộ CJK; tự host đúng cách là hơn 200 file mảnh `unicode-range`, một
cam kết bảo trì va thẳng R1. Windows có Yu Gothic UI, macOS có Hiragino Sans —
ý đồ của thiết kế (tên 得意先 hiện bằng font Nhật thật) vẫn đạt. Nếu về sau chữ
Nhật hiện xấu trên máy thật, xem lại quyết định này trước tiên.
```

Đồng thời sửa dòng tương ứng trong bảng §5 (hàng "Font") thành: *"Tự host IBM Plex trong `static/`; chữ Nhật dùng font hệ thống"*.

- [ ] **Step 11: Commit**

```bash
git add kome/web/static/fonts kome/web/static/kome.css tests/test_giao_dien.py docs/superpowers/specs/2026-09-21-lo-trinh-24-man-hinh-design.md
git commit -m "feat: tu host IBM Plex, chu Nhat dung font he thong

Spec 6.3 ghi tu host ca Noto Sans JP. Noto Sans JP phu toan bo CJK, tu host
dung cach la hon 200 file manh unicode-range — mot cam ket bao tri va thang
R1. Windows co Yu Gothic UI, macOS co Hiragino Sans. Da sua spec cho khop."
```

---

## Task 4: Sidebar trái thay thanh ngang hai tầng

**Files:**
- Modify: `kome/web/templates/_nav.html` (thay toàn bộ)
- Modify: `kome/web/static/kome.css` (khung trang + kiểu sidebar)
- Modify: `tests/test_giao_dien.py` (thêm test)

**Interfaces:**
- Consumes: `--nen-the`, `--do`, `--do-chu`, `--do-nen`, `--vien`, `--chu-nhat` từ task 2; `--font-ui` từ task 3. Biến `trang`, `chi_doc`, `co_mat_khau` mà `app.py::_ve` đã truyền cho mọi template (`kome/web/app.py:110`) — **không đổi `app.py` ở task này**.

### Sidebar của đợt 1 chỉ chứa trang đang có thật

Thiết kế có 24 mục; app hiện có 7 trang điều hướng được. Sidebar **không** hiện mục dẫn tới trang chưa tồn tại và **không** hiện mục mờ đi — một thanh điều hướng đầy mục bấm không được dạy người ta bỏ qua thanh điều hướng.

Nhóm theo đúng phân loại thiết kế (`kome-nav.js:32-67`), chỉ giữ ba nhóm có nội dung:

| Nhóm | Mục | Đường dẫn | `trang` |
|---|---|---|---|
| TỔNG QUAN | Tổng quan | `/` | `tong-quan` |
| | Báo cáo doanh thu | `/bao-cao` | `bao-cao` |
| KHÁCH HÀNG | Khách hàng | `/khach-hang` | `khach` |
| | Cần xử lý | `/can-xu-ly` | `can-xu-ly` |
| HỆ THỐNG | Nạp từ OBC | `/nap` | `nap` |
| | Sức khoẻ dữ liệu | `/health` | `suc-khoe` |
| | Bảng phủ dữ liệu | `/phu-du-lieu` | `phu` |

Ba mục HỆ THỐNG gộp thành một mục "Kho dữ liệu" ở **đợt 2a**, không phải bây giờ.

Màu mục đang mở lấy từ **code** chứ không từ README của gói thiết kế: `kome-nav.js:146-147` dùng nền `#FDEDEC` (`--do-nen`), chữ `#B4231C` (`--do-chu`), đậm nét, **không có** thanh đỏ bên trái. README mô tả nền `#FFF4D6` và một thanh đỏ — README lệch với chính prototype của nó, và prototype là thứ chạy được.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `tests/test_giao_dien.py`:

```python
def test_sidebar_hien_du_bay_muc_va_ba_nhom(conn, test_db_url):
    """Chặn thảm hoạ: đổi khung điều hướng làm rơi mất một trang khỏi
    sidebar -> trang đó vẫn chạy nhưng không ai vào được nữa."""
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/").text
    for duong_dan in ["/", "/bao-cao", "/khach-hang", "/can-xu-ly",
                      "/nap", "/health", "/phu-du-lieu"]:
        assert f'href="{duong_dan}"' in html, f"sidebar thiếu {duong_dan}"
    for nhom in ["TỔNG QUAN", "KHÁCH HÀNG", "HỆ THỐNG"]:
        assert nhom in html, f"sidebar thiếu nhóm {nhom}"


def test_muc_dang_mo_duoc_danh_dau(conn, test_db_url):
    """Đánh dấu mục đang mở bằng CẢ class lẫn aria-current: người dùng
    trình đọc màn hình không thấy màu nền."""
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/bao-cao").text
    assert 'href="/bao-cao" class="dang-xem" aria-current="page"' in html


def test_ban_chi_doc_an_han_muc_nap(conn, test_db_url, monkeypatch):
    """Bản chỉ-đọc không nạp được. Hiện mục Nạp ở đó là mời người ta bấm
    vào một đường dẫn thẳng tới 403.

    Dùng KOME_CHI_DOC chứ KHÔNG dùng VERCEL: đặt VERCEL=1 làm
    `bao_mat.kiem_cau_hinh` ném CauHinhSai ngay lúc dựng app nếu chưa có
    KOME_MAT_KHAU (bao_mat.py:55-62), và nếu đặt mật khẩu cho qua thì mọi
    trang lại chuyển hướng sang /dang-nhap — test sẽ đỏ vì hai lý do chẳng
    liên quan gì tới sidebar. app.py:48 chỉ sẵn đường này."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/").text
    assert 'href="/nap"' not in html
    assert 'href="/health"' in html
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `pytest tests/test_giao_dien.py -k "sidebar or dang_mo or chi_doc" -v`
Expected: FAIL — `test_sidebar_hien_du_bay_muc_va_ba_nhom` đỏ vì chưa có tên nhóm nào trong HTML.

- [ ] **Step 3: Thay `_nav.html`**

Thay **toàn bộ** `kome/web/templates/_nav.html`:

```html
{# Sidebar trái, 196px, cố định. Thay thanh ngang hai tầng của bản trước.

   Vì sao đổi: bản cũ để việc hằng ngày và việc kỹ thuật trên hai tầng của
   cùng một thanh, nên mục quan trọng nhất (Khách hàng) đứng ngang hàng với
   một việc làm mỗi ngày một lần. Sidebar tách hẳn nhóm HỆ THỐNG xuống dưới.

   Chỉ liệt kê trang ĐANG CÓ THẬT. Không hiện mục mờ dẫn tới trang chưa xây:
   một thanh điều hướng đầy mục bấm không được dạy người ta bỏ qua nó.

   `trang`: đánh dấu mục đang xem. Trang lỗi không truyền biến này nên không
   mục nào sáng — đúng, vì trang lỗi không thuộc mục nào cả.
   `chi_doc`: bản Vercel không nạp được, ẩn hẳn mục Nạp. #}
<aside class="canh">
  <a class="hieu" href="/">KOME</a>

  <nav class="dieu-huong">
    <p class="nhom">TỔNG QUAN</p>
    <a href="/"{% if trang == 'tong-quan' %} class="dang-xem" aria-current="page"{% endif %}>Tổng quan</a>
    <a href="/bao-cao"{% if trang == 'bao-cao' %} class="dang-xem" aria-current="page"{% endif %}>Báo cáo doanh thu</a>

    <p class="nhom">KHÁCH HÀNG</p>
    <a href="/khach-hang"{% if trang == 'khach' %} class="dang-xem" aria-current="page"{% endif %}>Khách hàng</a>
    <a href="/can-xu-ly"{% if trang == 'can-xu-ly' %} class="dang-xem" aria-current="page"{% endif %}>Cần xử lý</a>

    <p class="nhom">HỆ THỐNG</p>
    {% if not chi_doc %}
    <a href="/nap"{% if trang == 'nap' %} class="dang-xem" aria-current="page"{% endif %}>Nạp từ OBC</a>
    {% endif %}
    <a href="/health"{% if trang == 'suc-khoe' %} class="dang-xem" aria-current="page"{% endif %}>Sức khoẻ dữ liệu</a>
    <a href="/phu-du-lieu"{% if trang == 'phu' %} class="dang-xem" aria-current="page"{% endif %}>Bảng phủ dữ liệu</a>
  </nav>

  {% if co_mat_khau %}
  <form method="post" action="/dang-xuat" class="thoat"><button type="submit">Đăng xuất</button></form>
  {% endif %}
</aside>
<main class="noi-dung">
```

**Lưu ý:** partial này giờ **mở** thẻ `<main>` và không đóng. Xem step 4.

- [ ] **Step 4: Đóng `<main>`**

Vì `_nav.html` mở `<main>`, mỗi trang phải đóng nó. Thêm dòng `</main>` vào **cuối** mỗi template có `{% include "_nav.html" %}` — mười một file:

`bao_cao.html` · `can_xu_ly.html` · `chi_doc.html` · `error.html` · `health.html` · `khach_360.html` · `khach_hang.html` · `khong_thay.html` · `phu_du_lieu.html` · `tong_quan.html` · `upload.html`

(`dang_nhap.html` **không** include `_nav.html` — trang đăng nhập không có sidebar. Không sửa file đó.)

HTML5 cho phép bỏ qua thẻ đóng `</main>` cuối tài liệu, nhưng viết rõ ra thì người đọc sau không phải đoán, và trình duyệt không phải sửa giúp.

- [ ] **Step 5: Thay khung trang trong CSS**

Trong `kome/web/static/kome.css`, thay khối "Khung ứng dụng" và khối "Thanh điều hướng chung" bằng:

```css
 /* ---- Khung trang: sidebar trái cố định + vùng nội dung ---------- */
 body{display:flex;align-items:flex-start;max-width:none;margin:0;padding:0}
 .canh{position:sticky;top:0;flex-shrink:0;width:196px;height:100vh;
   box-sizing:border-box;display:flex;flex-direction:column;
   background:var(--nen-the);border-right:1px solid var(--vien);
   padding:1rem .7rem;overflow-y:auto}
 .noi-dung{flex:1;min-width:0;max-width:1400px;padding:1.1rem;padding-bottom:3rem}
 .hieu{display:flex;align-items:center;gap:.5rem;font-weight:700;letter-spacing:.08em;
   font-size:.84rem;text-decoration:none;color:var(--chu);padding:0 .3rem .8rem}
 .dieu-huong{display:flex;flex-direction:column;gap:.12rem}
 .nhom{margin:.9rem 0 .25rem;padding:0 .55rem;font-size:.68rem;font-weight:600;
   letter-spacing:.1em;color:var(--chu-nhat)}
 .nhom:first-child{margin-top:0}
 .dieu-huong a{padding:.42rem .55rem;border-radius:8px;font-size:.85rem;
   text-decoration:none;color:var(--chu-thuong)}
 .dieu-huong a:hover{background:var(--nen-phu)}
 /* Mục đang mở: nền và chữ lấy từ kome-nav.js:146-147 của gói thiết kế
    (KHÔNG theo README của gói — README ghi #FFF4D6 kèm thanh đỏ bên trái,
    lệch với chính prototype của nó). */
 .dieu-huong a.dang-xem{background:var(--do-nen);color:var(--do-chu);font-weight:600}
 .thoat{margin-top:auto;border-top:1px solid var(--vien);padding-top:.7rem}
 .thoat button{font:inherit;width:100%;text-align:left;padding:.4rem .55rem;
   border-radius:8px;border:0;background:transparent;color:var(--chu-nhat);cursor:pointer}
 .thoat button:hover{background:var(--nen-phu);color:var(--chu)}

 /* Màn hẹp: sidebar nằm ngang trên đầu thay vì chiếm 196px của 375px. */
 @media (max-width:720px){
   body{flex-direction:column}
   .canh{position:static;width:auto;height:auto;flex-direction:row;flex-wrap:wrap;
     align-items:center;gap:.25rem;border-right:0;border-bottom:1px solid var(--vien)}
   .dieu-huong{flex-direction:row;flex-wrap:wrap}
   .nhom{display:none}
   .thoat{margin-top:0;margin-left:auto;border-top:0;padding-top:0}
   .noi-dung{max-width:none;width:100%;box-sizing:border-box}
 }
```

Xoá khối `.dau-trang`, `.dieu-huong.phu` và `.dieu-huong .thoat` cũ — chúng không còn chỗ dùng.

- [ ] **Step 6: Chạy test**

Run: `pytest tests/test_giao_dien.py -v`
Expected: PASS — mười test.

- [ ] **Step 7: Chạy toàn bộ**

Run: `pytest -v`
Expected: PASS toàn bộ. `tests/test_web.py` và `tests/test_bao_mat.py` đọc nội dung HTML — nếu test nào đỏ vì cấu trúc trang đổi, **đọc kỹ trước khi sửa test**: có thể là trang thật sự mất nội dung chứ không phải test lỗi thời.

- [ ] **Step 8: Xem tận mắt, cả ba bề rộng**

Run: `uvicorn kome.web.app:app --reload`
1. Bề rộng máy tính: sidebar 196px bên trái, nội dung không quá 1400px, mục đang mở nền đỏ nhạt chữ đỏ đậm.
2. Thu cửa sổ xuống dưới 720px: sidebar thành hàng ngang trên đầu, tên nhóm ẩn, không có thanh cuộn ngang.
3. Chế độ tối: sidebar nền `#211D17` tách khỏi nền trang `#17140F` — nếu hai màu trông như một thì `--nen-the` chưa được dùng đúng chỗ.
4. Mở `/khach-hang/{một mã khách có thật}` và một đường dẫn sai để thấy trang lỗi — hai trang này cũng include `_nav.html` và dễ bị sót ở step 4.

- [ ] **Step 9: Commit**

```bash
git add kome/web/templates kome/web/static/kome.css tests/test_giao_dien.py
git commit -m "feat: sidebar trai 196px thay thanh dieu huong ngang hai tang"
```

---

## Sau khi xong cả bốn task

- [ ] Chạy `pytest -v` lần cuối — toàn bộ xanh
- [ ] Mở cả 8 trang ở hai chế độ sáng/tối, kiểm bất biến §6.5: mọi ô mã hoá bằng màu đều kèm số hoặc `▲ ▼`
- [ ] Merge nhánh vào `master` theo nếp repo (`git merge --no-ff`, thông điệp `merge: nen giao dien theo goi thiet ke`)
- [ ] Triển khai thử lên Vercel và mở bản công khai — đợt này thêm một thư mục tĩnh, và bản Vercel phục vụ file tĩnh theo cách khác bản chạy trong công ty. **Đây là rủi ro lớn nhất của cả đợt, và không test nào bắt được nó.** Nếu `/static/kome.css` trả 404 trên Vercel, xem `docs/trien-khai-vercel.md` và `server.py` trước khi sửa gì trong `app.py`.
