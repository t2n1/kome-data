# Đợt 2a — Kho dữ liệu (phần vận hành): Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gộp `/nap` + `/health` + `/phu-du-lieu` thành một màn `/kho-du-lieu`, thêm giao diện Hoàn tác, và cập nhật mọi tài liệu còn trỏ tới ba địa chỉ cũ.

**Architecture:** Năm bước tách rời. (1) Hai hàm đọc nhật ký nạp trong một module mới — thuần dữ liệu, không đụng giao diện. (2) Dựng màn mới với 6 khối, ba trang cũ vẫn chạy song song. (3) Thêm khối Hoàn tác. (4) Cắt sang màn mới: ba địa chỉ cũ trả 301, xoá ba template cũ. (5) Tài liệu. Ba trang cũ chỉ chết ở bước 4 — trước đó luôn có đường lùi.

**Tech Stack:** FastAPI + Jinja2, không JS mới, không gói mới. `RedirectResponse(status_code=301)` có sẵn trong FastAPI.

**Spec:** `docs/superpowers/specs/2026-09-21-dot-2a-kho-du-lieu-design.md`

## Global Constraints

- **Không đụng CSDL.** Không migration, không sửa `kome/db.py`, `kome/pipeline.py`, `kome/config.py`, `kome/tuoi_du_lieu.py`, `kome/coverage.py`.
- **`kome/web/app.py` KHÔNG nhập `kome.pipeline`, `pandas`, `calamine` ở mức ngoài cùng** — chỉ trong thân route. Test canh: `tests/test_bao_mat.py::test_trang_chi_doc_khong_phu_thuoc_pandas`.
- **Không thêm JavaScript.** Xác nhận hoàn tác dùng `<details>`, không dùng `confirm()`.
- **Không thêm gói nào vào `requirements.txt`.**
- **Không đổ bóng.** Phân tầng bằng viền `1px solid var(--vien)`.
- **Mọi `var(--x)` dùng ở bất kỳ đâu phải có định nghĩa trong `kome/web/static/kome.css`** — test canh: `test_moi_bien_dung_deu_duoc_dinh_nghia`.
- **Bốn tên `ok`/`canh`/`loi`/`nhat` không được dùng làm lớp CSS trần** ở bất kỳ đâu — test canh: `test_ten_badge_khong_duoc_dung_lam_lop_tran_trong_css`.
- **Mọi template include `_nav.html` phải có đúng một `</main>`** — test canh: `test_moi_template_dung_nav_deu_dong_main`.
- Thông điệp commit: **không dấu tiếng Việt**, theo nếp repo (`git log --oneline -10`).
- **`pytest -q` phải xanh toàn bộ, chạy MỘT MÌNH.** CSDL thử nghiệm dùng chung; chạy song song hai tiến trình pytest làm đỏ hàng loạt test vì lý do không liên quan.

---

## Bối cảnh quan trọng trước khi bắt đầu

**Màn này là thứ duy nhất trong hệ thống đang có người phụ thuộc hằng ngày** (quy trình 13:30). Hỏng nó là hỏng việc duy nhất hệ thống đang thật sự phục vụ.

**`TestClient` của Starlette tự đi theo chuyển hướng** (`follow_redirects=True` mặc định). Nghĩa là sau bước 4, `client.get("/health")` trong `tests/test_web.py` vẫn trả 200 và vẫn chứa nội dung cũ — vì nội dung đó giờ nằm trên màn gộp. **Phần lớn test hiện có sẽ TỰ XANH, đừng viết lại chúng.** Chỉ sửa test nào thật sự đỏ, và đọc kỹ lý do đỏ trước khi sửa. Muốn kiểm chính cái 301 thì phải truyền `follow_redirects=False`.

**Bài học từ đợt 1 — ba lỗi Critical, cả ba đều test xanh mà vẫn sai:** một biến CSS bị xoá còn template gọi; một lớp CSS mới trùng tên lớp badge **được ghép ở tầng Python** nên grep template không thấy; một font subset không có glyph tiếng Việt. Cả ba chỉ lộ ra khi mở trình duyệt nhìn. **Bước xem tận mắt trong kế hoạch này là bắt buộc, không phải thủ tục.**

---

## File Structure

| File | Trách nhiệm | Task |
|---|---|---|
| `kome/nhat_ky_nap.py` | **Tạo mới.** Hai hàm đọc `meta.ingest_batch` | 1 |
| `tests/test_nhat_ky_nap.py` | **Tạo mới.** Test cho hai hàm trên | 1 |
| `kome/web/templates/kho_du_lieu.html` | **Tạo mới.** Khung màn, include các partial | 2 |
| `kome/web/templates/_nap.html` | **Tạo mới.** Khối 2 — ô thả file + kết quả | 2 |
| `kome/web/templates/_suc_khoe.html` | **Tạo mới.** Khối 3+4 — sao lưu, kỳ, bảng 7 loại | 2 |
| `kome/web/templates/_phu_chu_giai.html` | **Tạo mới.** Chú giải ký hiệu + 2 hộp cảnh báo, dùng chung hai bảng | 2 |
| `kome/web/templates/_bang_thang.html` | **Tạo mới.** Khối 7 — bảng theo tháng | 2 |
| `kome/web/templates/_lo_nap.html` | **Tạo mới.** Khối 5 — lô nạp + Hoàn tác | 3 |
| `kome/web/templates/_tuoi_du_lieu.html` | Đã có, **không sửa** | — |
| `kome/web/templates/_bang_ngay.html` | Đã có, **không sửa** | — |
| `kome/web/templates/upload.html` · `health.html` · `phu_du_lieu.html` | **Xoá ở task 4** | 4 |
| `kome/web/app.py` | Route mới, 3 chuyển hướng, đổi đích 2 route POST | 2, 3, 4 |
| `tests/test_kho_du_lieu.py` | **Tạo mới.** Test của màn | 2, 3, 4 |
| `docs/runbook.md` · `CLAUDE.md` · `docs/trien-khai-vercel.md` | Cập nhật địa chỉ | 5 |

---

## Task 1: Hai hàm đọc nhật ký nạp

Thuần dữ liệu, không đụng giao diện. Làm trước để task 2 có sẵn thứ để gọi.

**Files:**
- Create: `kome/nhat_ky_nap.py`
- Create: `tests/test_nhat_ky_nap.py`

**Interfaces:**
- Produces:
  - `trang_thai_nap(conn) -> list[dict]` — mỗi dict có khoá `name`, `last`, `rows`, `total`, `co_tien`. **Đúng shape mà `health.html` đang dùng**, để task 2 tách partial là phép chuyển nguyên văn.
  - `lo_nap_gan_nhat(conn, gioi_han: int = 10) -> list[LoNap]`
  - `@dataclass(frozen=True) class LoNap` với các trường `batch_id: int`, `loai: str`, `ten_file: str`, `ngay_du_lieu: date`, `nap_luc: datetime`, `so_dong: int`, `tong_tien: int`, `co_tien: bool`

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_nhat_ky_nap.py`:

```python
"""Test hai hàm đọc nhật ký nạp (meta.ingest_batch).

Fixture `conn` và `test_db_url` nằm ở tests/conftest.py. Không test nào ở đây
dựng web app — chúng đọc CSDL trực tiếp.
"""
from kome.nhat_ky_nap import lo_nap_gan_nhat, trang_thai_nap


def _them_lo(conn, spec_name, source_file, data_date, row_count, total_amount,
             digest, undone_at=None):
    """Chèn một dòng nhật ký nạp. Không đụng bảng fact — hai hàm đang test
    chỉ đọc meta.ingest_batch."""
    conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count,
              total_amount, data_date, undone_at)
           VALUES (%s, %s, %s, 'test', %s, %s, %s, %s)""",
        (spec_name, source_file, digest, row_count, total_amount,
         data_date, undone_at))


def test_trang_thai_nap_lay_lan_nap_gan_nhat_cua_tung_loai(conn):
    """[IMPORTANT] Phải là lần nạp GẦN NHẤT của từng loại, không phải max()
    của từng cột riêng lẻ. Sau một lần đối soát tháng ~18.000 dòng, nếu lấy
    max(row_count) thì trang LUÔN hiện 18.000 kể cả hôm nay OBC xuất cắt cụt
    còn 60 dòng — tức trang giấu đúng cái sự cố nó sinh ra để báo."""
    conn.execute("DELETE FROM meta.ingest_batch")
    _them_lo(conn, "zaiko", "在庫一覧_20260101.xlsx", "2026-01-01", 18000, 0, "d1")
    _them_lo(conn, "zaiko", "在庫一覧_20260102.xlsx", "2026-01-02", 60, 0, "d2")

    ds = {r["name"]: r for r in trang_thai_nap(conn)}
    zaiko = [r for r in ds.values() if r["rows"] in (60, 18000)]
    assert zaiko and zaiko[0]["rows"] == 60, "phải lấy lô mới nhất (60), không phải max (18000)"


def test_trang_thai_nap_liet_ke_du_moi_loai_ke_ca_loai_chua_nap(conn):
    """Loại chưa nạp lần nào vẫn phải có dòng, với last=None — bảng thiếu
    hẳn một dòng thì người đọc tưởng loại đó không tồn tại, thay vì hiểu là
    nó chưa vào kho."""
    conn.execute("DELETE FROM meta.ingest_batch")
    ds = trang_thai_nap(conn)
    assert len(ds) >= 7, f"chỉ có {len(ds)} dòng, phải đủ mọi loại khai trong SPECS"
    assert all(r["last"] is None and r["rows"] == 0 for r in ds)


def test_lo_nap_gan_nhat_bo_qua_lo_da_hoan_tac(conn):
    """[IMPORTANT] Lô đã hoàn tác KHÔNG được hiện nút Hoàn tác lần nữa —
    bấm lần hai là xoá một thứ đã không còn, và người bấm thì tưởng lần
    đầu chưa ăn."""
    conn.execute("DELETE FROM meta.ingest_batch")
    _them_lo(conn, "zaiko", "con.xlsx", "2026-01-02", 10, 0, "d3")
    _them_lo(conn, "zaiko", "da_hoan_tac.xlsx", "2026-01-01", 10, 0, "d4",
             undone_at="2026-01-03")

    ds = lo_nap_gan_nhat(conn)
    ten = [l.ten_file for l in ds]
    assert "con.xlsx" in ten
    assert "da_hoan_tac.xlsx" not in ten


def test_lo_nap_gan_nhat_sap_moi_truoc_va_ton_trong_gioi_han(conn):
    """Lô mới nhất phải đứng đầu: người vừa nạp nhầm sẽ tìm nó ở dòng một,
    không phải cuộn xuống cuối."""
    conn.execute("DELETE FROM meta.ingest_batch")
    for i in range(1, 6):
        _them_lo(conn, "zaiko", f"f{i}.xlsx", f"2026-01-0{i}", i, 0, f"g{i}")

    ds = lo_nap_gan_nhat(conn, gioi_han=3)
    assert len(ds) == 3
    assert ds[0].ten_file == "f5.xlsx"
    assert ds[0].batch_id > ds[1].batch_id


def test_lo_nap_gan_nhat_hien_ten_tieng_nhat_cua_loai_file(conn):
    """Người vận hành nhận diện file bằng tên tiếng Nhật OBC xuất ra
    (在庫一覧…), không bằng mã nội bộ `zaiko`."""
    conn.execute("DELETE FROM meta.ingest_batch")
    _them_lo(conn, "zaiko", "在庫一覧_20260101.xlsx", "2026-01-01", 10, 0, "d5")
    assert lo_nap_gan_nhat(conn)[0].loai == "在庫一覧"
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `pytest tests/test_nhat_ky_nap.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kome.nhat_ky_nap'`

- [ ] **Step 3: Viết module**

Tạo `kome/nhat_ky_nap.py`:

```python
"""Đọc NHẬT KÝ NẠP (`meta.ingest_batch`) cho màn Kho dữ liệu.

Tách khỏi `kome/coverage.py` có chủ ý. File đó khai rõ nó là "MỘT nơi duy nhất
tính BẢNG PHỦ", và nó đọc thẳng từ kho dữ liệu chứ không đếm tên file. File này
trả lời câu khác: lô nào đã vào, lúc nào, bao nhiêu dòng. Hai câu hỏi khác nhau
trên hai nguồn khác nhau — gộp lại làm mờ đúng ranh giới mà docstring kia dựng.
"""
from dataclasses import dataclass
from datetime import date, datetime

from kome.config import SPECS


def _ten_loai(spec_name: str) -> str:
    """Mã nội bộ -> tên tiếng Nhật OBC xuất ra.

    Lô cũ có thể mang `spec_name` không còn trong SPECS (đổi cấu hình sau khi
    đã nạp). Trả về chính mã đó còn hơn ném lỗi: người đọc vẫn tra ngược được,
    còn một trang 500 thì không giúp được gì.
    """
    s = SPECS.get(spec_name)
    return s.display_name if s else spec_name


def trang_thai_nap(conn) -> list[dict]:
    """Mỗi loại file: nạp lần cuối lúc nào, bao nhiêu dòng, tổng tiền bao nhiêu.

    Trả về dict (không phải dataclass) vì mẫu `_suc_khoe.html` được tách nguyên
    văn từ `health.html` và đang đọc đúng các khoá này.

    DISTINCT ON lấy lần nạp GẦN NHẤT của từng loại. KHÔNG dùng
    max(loaded_at)/max(row_count)/max(total_amount): ba hàm đó độc lập, lấy từ
    ba dòng khác nhau, nên sau một lần đối soát tháng ~18.000 dòng thì trang
    LUÔN hiện 18.000 — kể cả hôm nay OBC xuất cắt cụt còn 60 dòng.
    """
    rows = conn.execute(
        """SELECT DISTINCT ON (spec_name)
                  spec_name, loaded_at, row_count, total_amount
           FROM meta.ingest_batch WHERE undone_at IS NULL
           ORDER BY spec_name, loaded_at DESC"""
    ).fetchall()
    seen = {r[0]: r for r in rows}
    return [
        {"name": s.display_name,
         "last": seen[k][1] if k in seen else None,
         "rows": seen[k][2] if k in seen else 0,
         "total": seen[k][3] if k in seen else 0,
         # File master / bảng giá KHÔNG mang giá trị tiền: `total_column` để
         # trống CÓ CHỦ Ý (xem kome/config.py). Cột "Tổng tiền" phải hiện "—",
         # không phải "¥0" — ¥0 làm người đọc tưởng hệ thống đếm hụt tiền và
         # đi báo một lỗi không tồn tại.
         "co_tien": s.total_column is not None}
        for k, s in SPECS.items()
    ]


@dataclass(frozen=True)
class LoNap:
    batch_id: int
    loai: str
    ten_file: str
    ngay_du_lieu: date
    nap_luc: datetime
    so_dong: int
    tong_tien: int
    co_tien: bool


def lo_nap_gan_nhat(conn, gioi_han: int = 10) -> list[LoNap]:
    """Các lô nạp gần nhất CHƯA bị hoàn tác, mới nhất đứng đầu.

    `undone_at IS NULL` là điều kiện bắt buộc, không phải bộ lọc cho gọn: lô
    đã hoàn tác mà vẫn hiện nút Hoàn tác thì lần bấm thứ hai xoá một thứ đã
    không còn, và người bấm tưởng lần đầu chưa ăn.
    """
    rows = conn.execute(
        """SELECT batch_id, spec_name, source_file, data_date, loaded_at,
                  row_count, total_amount
           FROM meta.ingest_batch
           WHERE undone_at IS NULL
           ORDER BY loaded_at DESC, batch_id DESC
           LIMIT %s""",
        (gioi_han,),
    ).fetchall()
    return [
        LoNap(batch_id=r[0], loai=_ten_loai(r[1]), ten_file=r[2],
              ngay_du_lieu=r[3], nap_luc=r[4], so_dong=r[5], tong_tien=r[6],
              co_tien=(SPECS[r[1]].total_column is not None) if r[1] in SPECS else False)
        for r in rows
    ]
```

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `pytest tests/test_nhat_ky_nap.py -v`
Expected: PASS — 5 test.

- [ ] **Step 5: Chạy toàn bộ, một mình**

Run: `pytest -q`
Expected: PASS toàn bộ (hiện là 211 + 5 mới).

- [ ] **Step 6: Commit**

```bash
git add kome/nhat_ky_nap.py tests/test_nhat_ky_nap.py
git commit -m "feat: kome/nhat_ky_nap.py - hai ham doc meta.ingest_batch"
```

---

## Task 2: Màn `/kho-du-lieu` với 6 khối

Ba trang cũ **vẫn chạy nguyên**. Task này chỉ thêm một màn mới song song — nếu có gì sai, đường lùi là không dùng nó.

**Files:**
- Create: `kome/web/templates/kho_du_lieu.html`, `_nap.html`, `_suc_khoe.html`, `_bang_thang.html`
- Create: `tests/test_kho_du_lieu.py`
- Modify: `kome/web/app.py` (thêm route `GET /kho-du-lieu`)

**Interfaces:**
- Consumes: `trang_thai_nap(conn)`, `lo_nap_gan_nhat(conn)` từ Task 1 (`lo_nap_gan_nhat` chưa dùng ở task này, dùng ở Task 3)
- Produces: route `/kho-du-lieu` với `trang="kho-du-lieu"`; template `kho_du_lieu.html` nhận các biến `tuoi`, `results`, `backup`, `ky`, `status`, `bang_ngay`, `bang`, `chi_doc`

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_kho_du_lieu.py`:

```python
"""Test màn Kho dữ liệu — màn gộp của /nap + /health + /phu-du-lieu."""
from fastapi.testclient import TestClient

from kome.web.app import create_app

# Mỗi khối một dấu hiệu nhận biết ổn định (không phải chuỗi trang trí dễ đổi).
DAU_HIEU_KHOI = {
    "tuoi du lieu": "hom-nay",
    "nap": 'id="nap"',
    "suc khoe": "Sức khoẻ dữ liệu",
    "bang 7 loai": "在庫一覧",
    "bang theo ngay": "theo-ngay",
    "bang theo thang": 'id="theo-thang"',
}


def test_man_kho_du_lieu_co_du_cac_khoi(conn, test_db_url):
    """[IMPORTANT] Gộp ba trang thành một là lúc dễ đánh rơi một khối nhất:
    trang vẫn 200, vẫn đẹp, chỉ thiếu đúng thứ ai đó cần. Test này đếm từng
    khối thay vì chỉ kiểm mã trả về."""
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/kho-du-lieu")
    assert r.status_code == 200
    for ten, dau_hieu in DAU_HIEU_KHOI.items():
        assert dau_hieu in r.text, f"thiếu khối: {ten}"


def test_man_co_hai_neo_cho_dau_trang_cu(conn, test_db_url):
    """Dấu trang cũ /nap và /phu-du-lieu sẽ được chuyển hướng kèm neo
    #nap / #theo-thang. Neo không tồn tại thì người bấm rơi lên đầu trang
    và phải cuộn đi tìm — đúng thứ chuyển hướng sinh ra để tránh."""
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert 'id="nap"' in html
    assert 'id="theo-thang"' in html


def test_ban_chi_doc_an_o_tha_file(conn, test_db_url, monkeypatch):
    """Bản công khai không nạp được. Hiện ô thả file ở đó là mời người ta
    kéo một file 100 MB vào một endpoint luôn trả 403."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert 'id="nap"' not in html
    assert "在庫一覧" in html, "khối chỉ-đọc khác vẫn phải hiện"
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `pytest tests/test_kho_du_lieu.py -v`
Expected: FAIL — `/kho-du-lieu` trả 404.

- [ ] **Step 3: Tách `_nap.html`**

Tạo `kome/web/templates/_nap.html` — chuyển phần thân của `upload.html` (form + danh sách kết quả), **giữ nguyên từng ký tự của phần HTML**, bọc trong một `<section id="nap">`:

```html
{# Khối NẠP DỮ LIỆU của màn Kho dữ liệu. Tách từ upload.html, giữ nguyên
   hành vi: MỘT ô nhận NHIỀU file.

   Vì sao không theo thiết kế (7 ô riêng, mỗi loại một ô): người làm việc
   13:30 thả 3 file một lần; 7 ô biến 1 thao tác thành 3 mỗi ngày. Câu hỏi
   "còn thiếu file nào" đã được ô tuổi dữ liệu ngay phía trên trả lời rồi.

   Khối này KHÔNG render ở bản chỉ-đọc — xem kho_du_lieu.html. #}
<section id="nap">
<h2>Nạp dữ liệu OBC</h2>
<form method="post" action="/upload" enctype="multipart/form-data">
  <div class="drop">Kéo thả file Excel vào đây<br><input type="file" name="files" multiple required></div>
  <p><button type="submit">Nạp</button></p>
</form>
{% if results %}<h3>Kết quả</h3><ul>
{% for r in results %}<li>
  {% if r.skipped %}<span class="kq-ok">⏭️ {{ r.spec_name }} — file này đã nạp rồi, bỏ qua</span>
  {% elif r.ok %}<span class="kq-ok">✅ {{ r.spec_name }} — {{ "{:,}".format(r.row_count) }} dòng · ¥{{ "{:,}".format(r.total) }}</span>
  {% else %}<span class="kq-loi">❌ {{ r.spec_name or "?" }} — KHÔNG nạp</span>{% endif %}
  {% for b in r.blockers %}<div class="kq-loi">Cổng {{ b.gate }}: {{ b.message }}</div>{% endfor %}
  {% for w in r.warnings %}<div class="kq-canh">⚠️ Cổng {{ w.gate }}: {{ w.message }}</div>{% endfor %}
</li>{% endfor %}</ul>{% endif %}
</section>
```

Các lớp `.drop`, `.kq-ok`, `.kq-canh`, `.kq-loi` hiện nằm trong `<style>` của `upload.html`. **Chuyển chúng vào `kome/web/static/kome.css`** (chúng thuộc về màn, không thuộc về một file sắp bị xoá):

```css
 /* ---- Khối nạp dữ liệu (màn Kho dữ liệu) ------------------------ */
 .drop{border:2px dashed var(--vien);border-radius:12px;padding:3rem;
   text-align:center;background:var(--nen-phu)}
 .kq-ok{color:var(--ok-chu)} .kq-canh{color:var(--canh-chu)} .kq-loi{color:var(--loi-chu)}
```

- [ ] **Step 4: Tách `_suc_khoe.html`**

Tạo `kome/web/templates/_suc_khoe.html` — chuyển **`health.html` dòng 8 đến hết file, trừ dòng `</html>` và `</main>` ở cuối** (tức từ ghi chú `{# backup = None ở bản chỉ-đọc… #}` tới hết bảng 7 loại). **Giữ nguyên từng ký tự**, kể cả toàn bộ ghi chú Jinja — chúng giải thích những quyết định đã kiểm chứng bằng dữ liệu thật, và viết lại chúng là đánh mất lý do.

Mở đầu file bằng `<h2>Sức khoẻ dữ liệu</h2>` (thay cho `<h1>` cũ: trên màn gộp nó là một khối, không phải tiêu đề trang).

Đối chiếu sau khi tách: `diff <(sed -n '8,$p' health.html)` với phần tương ứng — không được lệch dòng nào ngoài hai chỗ vừa nêu.

**Không** chuyển `{% include "_tuoi_du_lieu.html" %}` vào đây — khối đó do `kho_du_lieu.html` include trực tiếp, vì nó phải đứng **trên** khối nạp.

- [ ] **Step 5: Tách `_bang_thang.html`**

Ba phần của `phu_du_lieu.html` đi ba nơi khác nhau. Đã đọc và chia sẵn — làm đúng bảng này, đừng tự chia lại:

| Dòng | Nội dung | Đi đâu | Vì sao |
|---|---|---|---|
| 33 | `<h1>Bảng phủ dữ liệu</h1>` | **bỏ** | Màn gộp đã có `<h1>Kho dữ liệu</h1>` |
| 34–36 | `<p class="chu-thich">` "Mỗi dòng là một tháng…" | `_bang_thang.html`, ngay sau `<h2>` | Chỉ nói về bảng THÁNG |
| 38–60 | `<div class="chu-giai">` + `<div class="ky">` (ràng buộc vĩnh viễn) + `<div class="ngay-thieu">` (hạn chế của ô "không có dữ liệu") | **`_phu_chu_giai.html` (file mới)** | Giải thích ký hiệu và cảnh báo áp cho **cả hai** bảng, nên phải đứng trước cả hai |
| 63–102 | `<h2>Theo tháng…` tới hết "Loại dữ liệu CHƯA vào kho" | `_bang_thang.html` | Bảng THÁNG |
| 103–104 | `</html>` `</main>` | **bỏ** | Màn gộp tự đóng |

Tạo **`kome/web/templates/_phu_chu_giai.html`** chứa dòng 38–60 nguyên văn, và **`kome/web/templates/_bang_thang.html`** chứa dòng 63–102 nguyên văn (đặt `<p>` dòng 34–36 ngay sau `<h2>` của nó), bọc toàn bộ trong `<section id="theo-thang">` … `</section>`.

Các lớp CSS riêng trong `<style>` của `phu_du_lieu.html` chuyển vào `kome.css` — **trừ** `body{max-width:980px}`, dòng đó **xoá hẳn**: nó viết cho khung trước khi có sidebar, và đợt 1 đã phải sửa đúng lỗi này một lần rồi. Đừng mang nó theo.

- [ ] **Step 6: Viết `kho_du_lieu.html`**

```html
<!-- kome/web/templates/kho_du_lieu.html
     Màn Kho dữ liệu — gộp /nap + /health + /phu-du-lieu.

     Thứ tự khối có chủ ý: trả lời "tôi phải làm gì ngay bây giờ" trước
     (khối tuổi dữ liệu), rồi mới tới "có gì sai không" (sức khoẻ), cuối
     cùng là sổ sách (hai bảng phủ). Khối tuổi dữ liệu và khối nạp đứng
     cạnh nhau vì khối trên nói thiếu file nào, khối dưới là chỗ thả file
     đó vào — hôm nay hai thứ ấy nằm ở hai trang khác nhau. -->
<!doctype html><html lang="vi"><meta charset="utf-8">
<title>KOME — kho dữ liệu</title>
{% include "_chung.html" %}
{% include "_nav.html" %}
<h1>Kho dữ liệu</h1>
{% include "_tuoi_du_lieu.html" %}
{# Bản chỉ-đọc (Vercel) không nạp được: mỗi yêu cầu bị chặn ở 4,5 MB còn
   売上伝票データ nặng ~100 MB, và ổ đĩa là tạm nên lớp raw không tồn tại
   được. Ẩn hẳn khối, không hiện một nút luôn báo lỗi. #}
{% if not chi_doc %}{% include "_nap.html" %}{% endif %}
{% include "_suc_khoe.html" %}
{% include "_phu_chu_giai.html" %}
{% include "_bang_ngay.html" %}
{% include "_bang_thang.html" %}
</html>
</main>
```

- [ ] **Step 7: Thêm route**

Trong `kome/web/app.py`, thêm import ở đầu file cạnh các import `kome` khác:

```python
from kome.nhat_ky_nap import lo_nap_gan_nhat, trang_thai_nap
```

Thêm route (đặt ngay trước route `/health` hiện có):

```python
    def _du_lieu_kho(conn):
        """Mọi thứ màn Kho dữ liệu cần, gom một chỗ.

        Route GET và route POST /upload đều render cùng màn này, nên cùng
        gọi hàm này — tách ra để hai chỗ không bao giờ trôi khỏi nhau.
        """
        return {"status": trang_thai_nap(conn),
                "ky": _ky_du_lieu(conn),
                "tuoi": tinh_tuoi(conn),
                "bang": tinh_bang_phu(conn),
                "bang_ngay": tinh_bang_ngay(conn),
                "lo": lo_nap_gan_nhat(conn)}

    @app.get("/kho-du-lieu", response_class=HTMLResponse)
    def kho_du_lieu(request: Request):
        try:
            # BACKUP_DIR đọc mỗi lần gọi, không chốt lúc tạo app — test và
            # người vận hành đổi biến môi trường thì trang phải thấy ngay.
            backup_dir = Path(os.environ.get("BACKUP_DIR", "./backups"))
            with open_conn() as conn:
                ctx = _du_lieu_kho(conn)
            # Bản chỉ-đọc KHÔNG nói gì về sao lưu: sao lưu chạy trên máy nội
            # bộ, máy chủ công khai không nhìn thấy thư mục .zip đó nên sẽ
            # luôn kết luận "chưa sao lưu" — một dải đỏ vĩnh viễn dạy người
            # đọc bỏ qua dải đỏ.
            ctx["backup"] = None if chi_doc else backup_status(backup_dir)
            return _ve(request, "kho_du_lieu.html",
                       {**ctx, "trang": "kho-du-lieu"})
        except Exception as e:
            return _loi(request, "mở màn kho dữ liệu", e, chung)
```

- [ ] **Step 8: Chạy test**

Run: `pytest tests/test_kho_du_lieu.py -v`
Expected: PASS — 3 test.

- [ ] **Step 9: Chạy toàn bộ, một mình**

Run: `pytest -q`
Expected: PASS toàn bộ. Ba trang cũ chưa đụng nên test cũ phải xanh nguyên.

- [ ] **Step 10: Xem tận mắt**

Run: `python -m uvicorn kome.web.app:app --port 8021`
Mở `http://localhost:8021/kho-du-lieu` ở **cả chế độ sáng và tối**, và ở bề rộng 375px. Soi bốn thứ:
1. Đủ sáu khối, đúng thứ tự trong `kho_du_lieu.html`.
2. So với `/health` và `/phu-du-lieu` (vẫn còn sống): **số liệu từng khối phải khớp**. Mở song song hai tab mà đối chiếu.
3. Bảng rộng không cuộn ngang ở 375px.
4. Ô thả file nằm ngay dưới ô tuổi dữ liệu.

- [ ] **Step 11: Commit**

```bash
git add kome/web/templates kome/web/static/kome.css kome/web/app.py tests/test_kho_du_lieu.py
git commit -m "feat: man /kho-du-lieu gop /nap /health /phu-du-lieu"
```

---

## Task 3: Khối Hoàn tác

**Files:**
- Create: `kome/web/templates/_lo_nap.html`
- Modify: `kome/web/templates/kho_du_lieu.html` (include khối mới)
- Modify: `kome/web/static/kome.css` (kiểu cho khối)
- Modify: `tests/test_kho_du_lieu.py`

**Interfaces:**
- Consumes: `lo_nap_gan_nhat(conn) -> list[LoNap]` từ Task 1; biến `lo` đã có trong context từ Task 2

- [ ] **Step 1: Viết test thất bại**

Thêm vào `tests/test_kho_du_lieu.py`:

```python
def test_khoi_hoan_tac_hien_lo_va_giau_nut_sau_mot_buoc(conn, test_db_url):
    """[IMPORTANT] Hoàn tác XOÁ dữ liệu khỏi core và không thể hoàn lại.
    Nút không được nằm trần trên một màn người ta mở mỗi ngày: <details>
    bắt người bấm đọc hậu quả trước khi thấy cái nút."""
    conn.execute("DELETE FROM meta.ingest_batch")
    conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count,
              total_amount, data_date)
           VALUES ('zaiko', '在庫一覧_20260101.xlsx', 'dg1', 'test', 177, 0, '2026-01-01')""")
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text

    assert "在庫一覧_20260101.xlsx" in html
    assert "<details" in html and "Hoàn tác" in html
    assert "177" in html, "phải nói rõ sẽ xoá bao nhiêu dòng"
    assert "Không thể hoàn lại" in html


def test_ban_chi_doc_an_khoi_hoan_tac(conn, test_db_url, monkeypatch):
    """Bản công khai không hoàn tác được (route trả 403). Hiện nút ở đó là
    mời người ta bấm một thứ chắc chắn thất bại — và là nút XOÁ."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert "/undo/" not in html
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `pytest tests/test_kho_du_lieu.py -k hoan_tac -v`
Expected: FAIL — chưa có khối nào.

- [ ] **Step 3: Viết `_lo_nap.html`**

```html
{# Khối LÔ NẠP GẦN NHẤT + HOÀN TÁC.

   Hoàn tác chạy `DELETE FROM core.… WHERE batch_id = %s` — xoá thật, không
   hoàn lại được. Vì vậy nút nằm sau một <details>: người bấm phải mở ra và
   đọc "xoá bao nhiêu dòng, của file nào" trước khi thấy nút.

   Xác nhận bằng <details> chứ KHÔNG bằng JavaScript: đợt này không thêm JS,
   `confirm()` không tạo kiểu được và bị chặn ở một số cấu hình, còn <details>
   thì có sẵn, đọc được bằng trình đọc màn hình, và đứng yên khi JS tắt.

   Nút mang đúng số lô để người bấm đối chiếu với dòng mình định xoá.

   Khối này KHÔNG render ở bản chỉ-đọc — xem kho_du_lieu.html. #}
<section id="lo-nap">
<h2>Lô nạp gần nhất</h2>
{% if not lo %}
<p class="trong">Chưa có lô nạp nào.</p>
{% else %}
<div class="bang-cuon">
<table style="min-width:44rem">
  <tr><th>Loại file</th><th>Tên file</th><th>Ngày dữ liệu</th><th>Nạp lúc</th>
      <th class="so">Số dòng</th><th class="so">Tổng tiền</th><th>Hoàn tác</th></tr>
  {% for l in lo %}
  <tr>
    <td>{{ l.loai }}</td>
    <td>{{ l.ten_file }}</td>
    <td>{{ l.ngay_du_lieu }}</td>
    <td>{{ l.nap_luc.strftime("%Y-%m-%d %H:%M") }}</td>
    <td class="so">{{ "{:,}".format(l.so_dong) }}</td>
    <td class="so">{% if l.co_tien %}¥{{ "{:,}".format(l.tong_tien) }}{% else %}<span class="khong-ap-dung">—</span>{% endif %}</td>
    <td>
      <details class="hoan-tac">
        <summary>Hoàn tác</summary>
        <p>Xoá <strong>{{ "{:,}".format(l.so_dong) }} dòng</strong> đã nạp từ
           <strong>{{ l.ten_file }}</strong>. <strong>Không thể hoàn lại.</strong></p>
        <form method="post" action="/undo/{{ l.batch_id }}">
          <button type="submit">Xoá lô {{ l.batch_id }}</button>
        </form>
      </details>
    </td>
  </tr>
  {% endfor %}
</table>
</div>
{% endif %}
</section>
```

- [ ] **Step 4: Thêm kiểu vào `kome.css`**

```css
 /* Nút hoàn tác: hành động PHÁ HUỶ, nên mang màu lỗi chứ không phải màu
    hành động chính — nó không phải thứ ta mời người ta bấm. */
 .hoan-tac summary{cursor:pointer;color:var(--loi-chu);font-size:.85rem}
 .hoan-tac p{font-size:.85rem;margin:.4rem 0}
 .hoan-tac button{font:inherit;padding:.3rem .7rem;border-radius:9px;
   border:1px solid var(--loi-vien);background:var(--loi-nen);
   color:var(--loi-chu);cursor:pointer}
```

- [ ] **Step 5: Include vào màn**

Trong `kho_du_lieu.html`, thêm ngay **sau** `{% include "_suc_khoe.html" %}`:

```html
{% if not chi_doc %}{% include "_lo_nap.html" %}{% endif %}
```

- [ ] **Step 6: Chạy test**

Run: `pytest tests/test_kho_du_lieu.py -v`
Expected: PASS — 5 test.

- [ ] **Step 7: Chạy toàn bộ, một mình**

Run: `pytest -q`
Expected: PASS toàn bộ.

- [ ] **Step 8: Thử hoàn tác thật**

Run: `python -m uvicorn kome.web.app:app --port 8021`
1. Mở `/kho-du-lieu`, tìm khối "Lô nạp gần nhất".
2. Mở một `<details>` — phải thấy số dòng và tên file, rồi mới tới nút.
3. **Bấm nút trên một lô thật**, rồi kiểm: lô đó biến khỏi danh sách, và số ở bảng 7 loại đổi theo.
4. Ghi vào báo cáo số lô đã xoá và số dòng — để người soát đối chiếu được.

- [ ] **Step 9: Commit**

```bash
git add kome/web/templates kome/web/static/kome.css tests/test_kho_du_lieu.py
git commit -m "feat: khoi hoan tac lo nap tren man kho du lieu"
```

---

## Task 4: Cắt sang màn mới

Đây là bước duy nhất làm ba trang cũ chết. Làm sau cùng trong phần code, khi màn mới đã chạy và đã được nhìn tận mắt.

**Files:**
- Modify: `kome/web/app.py` (3 route thành chuyển hướng, `POST /upload` và `POST /undo` đổi đích)
- Delete: `kome/web/templates/upload.html`, `health.html`, `phu_du_lieu.html`
- Modify: `kome/web/templates/_nav.html` (3 mục thành 1)
- Modify: `tests/test_kho_du_lieu.py`, `tests/test_giao_dien.py`

**Interfaces:**
- Consumes: route `/kho-du-lieu` từ Task 2

- [ ] **Step 1: Viết test thất bại**

Thêm vào `tests/test_kho_du_lieu.py`:

```python
def test_ba_dia_chi_cu_chuyen_huong_301(conn, test_db_url):
    """[IMPORTANT] Ba địa chỉ này nằm trong runbook và trong dấu trang của
    người dùng. Trả 404 là phạt họ vì một thay đổi họ không gây ra.

    follow_redirects=False: TestClient mặc định ĐI THEO chuyển hướng, nên
    không tắt thì test này xanh cả khi route trả 200 mà chẳng chuyển hướng gì.
    """
    client = TestClient(create_app(db_url=test_db_url))
    mong_doi = {"/health": "/kho-du-lieu",
                "/nap": "/kho-du-lieu#nap",
                "/phu-du-lieu": "/kho-du-lieu#theo-thang"}
    for cu, moi in mong_doi.items():
        r = client.get(cu, follow_redirects=False)
        assert r.status_code == 301, f"{cu} trả {r.status_code}, phải 301"
        assert r.headers["location"] == moi, f"{cu} trỏ sai đích"


def test_nap_van_chuyen_huong_o_ban_chi_doc(conn, test_db_url, monkeypatch):
    """Dấu trang /nap cũ trên bản công khai phải rơi vào màn (tự ẩn khối
    nạp), không phải một trang 403. 403 cho một dấu trang cũ là phạt người
    dùng vì một thay đổi họ không gây ra."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/nap", follow_redirects=False)
    assert r.status_code == 301


def test_upload_render_man_gop(conn, test_db_url):
    """Nạp xong phải rơi lại vào màn gộp kèm kết quả — không phải một
    template đã bị xoá."""
    client = TestClient(create_app(db_url=test_db_url))
    with open("tests/fixtures/zaiko_cat_cut.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 200
    assert 'id="theo-thang"' in r.text, "phải là màn gộp, không phải trang nạp cũ"
    assert "nghi file xuất một phần" in r.text, "kết quả nạp vẫn phải hiện"
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `pytest tests/test_kho_du_lieu.py -k "301 or chi_doc or upload_render" -v`
Expected: FAIL — ba địa chỉ cũ đang trả 200.

- [ ] **Step 3: Đổi ba route thành chuyển hướng**

Trong `kome/web/app.py`, **thay** thân ba route `/nap`, `/health`, `/phu-du-lieu` bằng:

```python
    # Ba địa chỉ cũ -> màn gộp. 301 chứ không 302: chúng biến mất vĩnh viễn,
    # và 301 cho trình duyệt cập nhật dấu trang. Neo để người bấm dấu trang cũ
    # rơi đúng khối họ vẫn mở, không phải cuộn đi tìm.
    #
    # /nap VẪN chuyển hướng ở bản chỉ-đọc, không trả 403: màn đích tự ẩn khối
    # nạp, còn 403 cho một dấu trang cũ là phạt người dùng vì một thay đổi họ
    # không gây ra.
    #
    # Viết ba hàm rời chứ không một vòng lặp sinh route: ba dòng lặp lại đọc
    # thẳng hơn một closure sinh hàm, và repo này chọn "không ma thuật" (R2).

    @app.get("/nap", include_in_schema=False)
    def _cu_nap():
        return RedirectResponse("/kho-du-lieu#nap", status_code=301)

    @app.get("/health", include_in_schema=False)
    def _cu_health():
        return RedirectResponse("/kho-du-lieu", status_code=301)

    @app.get("/phu-du-lieu", include_in_schema=False)
    def _cu_phu_du_lieu():
        return RedirectResponse("/kho-du-lieu#theo-thang", status_code=301)
```

Xoá luôn các hàm route `/nap`, `/health`, `/phu-du-lieu` cũ và mọi import giờ không còn ai dùng.

- [ ] **Step 4: Đổi `POST /upload` render màn gộp**

Trong thân route `/upload`, chỗ `return _ve(request, "upload.html", {...})`, đổi thành:

```python
            backup_dir = Path(os.environ.get("BACKUP_DIR", "./backups"))
            with open_conn() as conn:
                ctx = _du_lieu_kho(conn)
            ctx["backup"] = None if chi_doc else backup_status(backup_dir)
            return _ve(request, "kho_du_lieu.html",
                       {**ctx, "results": results, "trang": "kho-du-lieu"})
```

(tên biến `results` giữ đúng như route đang dùng)

- [ ] **Step 5: Đổi đích chuyển hướng của `POST /undo`**

```python
            return RedirectResponse("/kho-du-lieu", status_code=303)
```

- [ ] **Step 6: Gộp ba mục điều hướng thành một**

Trong `kome/web/templates/_nav.html`, nhóm HỆ THỐNG hiện có ba mục. Thay bằng:

```html
    <p class="nhom">HỆ THỐNG</p>
    <a href="/kho-du-lieu"{% if trang == 'kho-du-lieu' %} class="dang-xem" aria-current="page"{% endif %}>Kho dữ liệu</a>
```

Mục này **không** bọc `{% if not chi_doc %}`: màn hiện được ở cả hai bản, chỉ khác là bản chỉ-đọc tự ẩn hai khối bên trong.

- [ ] **Step 7: Xoá ba template cũ**

```bash
git rm kome/web/templates/upload.html kome/web/templates/health.html kome/web/templates/phu_du_lieu.html
```

- [ ] **Step 8: Sửa `TRANG` trong `tests/test_giao_dien.py`**

```python
TRANG = ["/", "/khach-hang", "/bao-cao", "/can-xu-ly", "/kho-du-lieu"]
```

- [ ] **Step 9: Chạy toàn bộ, một mình, rồi ĐỌC KỸ trước khi sửa gì**

Run: `pytest -q`

`tests/test_web.py` gọi `/health` 5 lần và `/phu-du-lieu` 2 lần. **Phần lớn sẽ tự xanh** vì `TestClient` đi theo chuyển hướng và nội dung cũ giờ nằm trên màn gộp. Với mỗi test thật sự đỏ:
- Đỏ vì **nội dung không còn trên màn gộp** → đó là một khối bị đánh rơi ở Task 2. **Sửa màn, không sửa test.**
- Đỏ vì test khẳng định một chi tiết trình bày đã đổi có chủ ý (tiêu đề trang, thứ tự khối) → sửa test, và **ghi rõ trong báo cáo** bất biến cũ giờ được canh ở đâu.

- [ ] **Step 10: Xem tận mắt**

Run: `python -m uvicorn kome.web.app:app --port 8021`
1. Mở `/health` → phải nhảy sang `/kho-du-lieu`.
2. Mở `/phu-du-lieu` → nhảy sang `/kho-du-lieu#theo-thang`, **và cuộn đúng tới bảng tháng**.
3. Mở `/nap` → nhảy tới `#nap`.
4. Sidebar: nhóm HỆ THỐNG còn đúng một mục, bấm vào ra màn đúng, mục sáng lên.
5. Thả một file thật vào ô nạp → kết quả hiện trên màn gộp, không rơi ra trang lạ.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "feat: ba dia chi cu tra 301 ve /kho-du-lieu, xoa ba template cu"
```

---

## Task 5: Tài liệu

Sổ tay lạc hậu còn tệ hơn một địa chỉ xấu — người mở nó là người không rành kỹ thuật, và họ mở đúng lúc đang hỏng.

**Files:**
- Modify: `docs/runbook.md`, `CLAUDE.md`, `docs/trien-khai-vercel.md`
- Modify: `tests/test_kho_du_lieu.py`

- [ ] **Step 1: Viết test thất bại**

Thêm vào `tests/test_kho_du_lieu.py`:

```python
from pathlib import Path


def test_tai_lieu_khong_con_tro_toi_ba_dia_chi_cu():
    """[IMPORTANT] runbook.md là thứ người KHÔNG rành kỹ thuật mở ra đúng
    lúc đang hỏng. Một địa chỉ sai trong đó nguy hiểm hơn một địa chỉ sai
    trong code: code thì test bắt được, còn sổ tay thì không gì bắt —
    trừ test này."""
    canh = [Path("docs/runbook.md"), Path("CLAUDE.md"),
            Path("docs/trien-khai-vercel.md")]
    cu = ("/phu-du-lieu", "/health", "/nap")
    loi = []
    for f in canh:
        for i, dong in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            # Chỉ bắt địa chỉ dùng như ĐƯỜNG DẪN (có dấu / đứng trước),
            # không bắt chữ "nạp" tiếng Việt hay tên biến.
            if any(d in dong for d in cu):
                loi.append(f"{f}:{i}: {dong.strip()[:70]}")
    assert not loi, "tài liệu còn trỏ tới địa chỉ cũ:\n" + "\n".join(loi)
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `pytest tests/test_kho_du_lieu.py -k tai_lieu -v`
Expected: FAIL — liệt kê khoảng 12 dòng trong ba file.

- [ ] **Step 3: Sửa `docs/runbook.md`**

Đổi mọi `/health` và `/phu-du-lieu` và `/nap` thành `/kho-du-lieu`. Riêng hàng **"Nạp nhầm file"** (khoảng dòng 152) viết lại cột cách xử lý:

```
1) Mở trang **Kho dữ liệu**, khối **Lô nạp gần nhất**<br>2) Tìm dòng của file vừa nạp nhầm, bấm **Hoàn tác**, đọc số dòng sẽ bị xoá rồi xác nhận<br>3) Nạp lại đúng file qua ô kéo–thả ngay trên màn đó
```

Giữ `scripts/hoan_tac.py` trong cột "cách khác": nó là đường thoát khi web app không mở được — đúng tình huống hàng ngay dưới mô tả.

- [ ] **Step 4: Sửa `CLAUDE.md`**

Trong bảng "Các trang của web app", thay ba dòng `/nap`, `/health`, `/phu-du-lieu` bằng:

```
| `/kho-du-lieu` | Nạp file OBC · sức khoẻ · độ phủ · hoàn tác lô | `meta.ingest_batch`, `core.*` |
```

Ghi thêm một dòng ngay dưới bảng: ba địa chỉ cũ trả 301 về đây.

- [ ] **Step 5: Sửa `docs/trien-khai-vercel.md`**

Dòng ~99 dùng `/health` làm mục kiểm đăng nhập → đổi thành `/kho-du-lieu`. Dòng ~65 nhắc `kome_app` chưa chạy được `/health` → đổi tên trang cho khớp.

- [ ] **Step 6: Chạy test**

Run: `pytest tests/test_kho_du_lieu.py -k tai_lieu -v`
Expected: PASS.

- [ ] **Step 7: Chạy toàn bộ, một mình**

Run: `pytest -q`
Expected: PASS toàn bộ.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "docs: cap nhat runbook, CLAUDE.md, trien-khai-vercel theo dia chi moi"
```

---

## Sau khi xong cả năm task

- [ ] `pytest -q` một mình — xanh toàn bộ
- [ ] Mở `/kho-du-lieu` ở hai chế độ sáng/tối, desktop và 375px
- [ ] Đối chiếu số liệu với bản production hiện tại (`kome-data.vercel.app`) — màn gộp phải nói cùng số
- [ ] Merge vào `master` theo nếp repo (`git merge --no-ff`)
- [ ] **Sau khi deploy: mở `/health` trên bản công khai, phải nhảy về `/kho-du-lieu`.** Chuyển hướng là thứ dễ hỏng khác nhau giữa máy nội bộ và Vercel, và không test nào bắt được điều đó.
