# Tự động lấy dữ liệu OBC và nạp vào web — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Một chương trình `obc_bot` chạy trên máy Windows có 商奉行クラウド, xuất file hằng ngày bằng cách bấm giao diện, rồi nạp lên web qua một endpoint JSON mới — đi qua đúng 5 cổng kiểm như kéo thả tay.

**Architecture:** Phía web thêm hai route JSON dưới `/api/kho-du-lieu/` (tự được middleware gác bằng `duoc_vao_kho_du_lieu`): `nap` (cùng thân với `POST /upload`) và `hom-nay` (đọc lại `kome.tuoi_du_lieu.tinh_tuoi`). `obc_bot/` là gói riêng ở gốc repo, không nhập `kome`: nửa `nap` (HTTP qua `requests`) và nửa `xuat` (pywinauto UIA) gặp nhau ở bộ điều phối `chay.py`, nơi mọi lần chạy kết thúc ở đúng một kết cục.

**Tech Stack:** Python 3.14, FastAPI (web có sẵn), pytest, `requests`, `pywinauto` 0.6.9 (backend `uia`), `keyring`, `tomllib`.

**Spec:** `docs/superpowers/specs/2026-10-14-tu-dong-lay-obc-design.md`

**Phạm vi:** bước 1–3 của đặc tả. Bước 4 (Task Scheduler, Credential Manager trên hai máy, mục runbook cài đặt) chủ DN hoãn — KHÔNG làm ở đây. Phần bấm từng màn OBC (Task 7) chỉ viết được SAU khi có cây điều khiển đo thật ở Task 6 — Task 7 là kế hoạch bổ sung, ghi lại vào cuối file này sau Task 6.

## Global Constraints

- OBC chỉ đọc: chương trình CHỈ xuất, không bao giờ ghi gì vào OBC; web không ghi `core` ngoài `pipeline.ingest` (luật số một).
- `obc_bot/` không nhập `kome` ở bất cứ đâu ngoài test; web (`kome/`) không nhập `obc_bot`.
- `kome/web/app.py` chỉ nhập `kome.pipeline` BÊN TRONG thân route (test canh `tests/test_bao_mat.py::test_trang_chi_doc_khong_phu_thuoc_pandas`).
- Mã `*コード` là TEXT; tên file ra phải khớp `filename_pattern` của `config/files.yml` (nhận diện chỉ theo tên).
- Ba mục và spec của chúng: `ban` → `meisai` (`売上明細表_YYYYMMDD.xlsx`, chỉ ngày hôm nay), `ton` → `zaiko` (`在庫一覧_YYYYMMDD.xlsx`), `khach` → `tokuisaki` (`得意先全情報_YYYYMMDD.xlsx`).
- "Hôm nay" = ngày Tokyo do web trả (`/api/kho-du-lieu/hom-nay`), không phải đồng hồ máy chạy.
- Mật khẩu web KHÔNG nằm trong file cấu hình — `keyring` (Windows Credential Manager), dịch vụ `kome-obc-bot`.
- Chọn điều khiển OBC theo tên / loại (UIA), không `click(x, y)`.
- Chạy test: `pytest -v` (CSDL test `DATABASE_URL_TEST`; không chạy song song với phiên Claude khác trên `kome_test`).
- Commit trên nhánh `feat/tu-dong-lay-obc`; cuối mỗi commit dòng `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

## Cấu trúc file

| File | Việc |
|---|---|
| `kome/web/app.py` (sửa) | `_nap_mot_buoc` (thân chung), `POST /api/kho-du-lieu/nap`, `GET /api/kho-du-lieu/hom-nay`, hằng `MUC_HANG_NGAY` |
| `tests/test_nap_tu_dong.py` (mới) | hai route mới: nạp, bỏ qua trùng, cổng chặn, 401/403, chỉ-đọc, hôm nay |
| `.vercelignore` (sửa) | thêm `obc_bot/` |
| `obc_bot/__init__.py`, `__main__.py` | lệnh `nap`, `chay`, `do`, `luu-mat-khau` |
| `obc_bot/ten_file.py` | `MUC_SPEC`, `ten_file(muc, ngay)` — bản chép của `files.yml` |
| `obc_bot/cau_hinh.py` | `CauHinh`, `doc(path)`, `CauHinhSai` |
| `obc_bot/web.py` | `KhachWeb` (đăng nhập, hôm nay, nạp), `LoiWeb`, `mat_khau_web` |
| `obc_bot/chay.py` | `KetCuc`, `LoiObc`, `MoiTruong`, `chay(ch, web, mt)` |
| `obc_bot/bao_cao.py` | log ngày, tệp báo lỗi OneDrive, thông báo Windows |
| `obc_bot/man_hinh.py` | `dang_khoa()`, `chup(duong)` |
| `obc_bot/obc/__init__.py` | `xuat(muc, ngay, thu_muc, pattern) -> Path`, `khoi_dong_lai()` — Task 5 tạm ném `LoiObc`, Task 7 viết thật |
| `obc_bot/obc/do.py` | `do_cay(...) -> str` — in cây điều khiển UIA |
| `obc_bot/requirements.txt`, `obc_bot/vi_du_may_b.toml`, `obc_bot/vi_du_may_long.toml` | gói cài và cấu hình mẫu |
| `tests/test_obc_bot_*.py` (mới) | test của gói, không cần OBC |
| `CLAUDE.md` (sửa) | một mục bất biến ngắn cho `obc_bot` |

---

### Task 1: `POST /api/kho-du-lieu/nap` — nạp một bước, trả JSON

**Files:**
- Modify: `kome/web/app.py:869-891` (route `/upload`) — tách thân ra `_nap_mot_buoc`, thêm route JSON ngay sau
- Test: `tests/test_nap_tu_dong.py` (mới)

**Interfaces:**
- Produces: `POST /api/kho-du-lieu/nap` multipart `files` → 200 `{"ket_qua": [{"ten_file", "ok", "skipped", "spec_name", "data_date" (ISO | null), "row_count", "batch_id", "blockers": [{"cong", "loi"}], "warnings": [{"cong", "loi"}]}]}`; 401 `{"loi"}` chưa đăng nhập; 403 `{"loi"}` thiếu cờ / bản chỉ-đọc; 500 `{"loi"}`.

- [ ] **Step 1: Viết test hỏng**

`tests/test_nap_tu_dong.py`:

```python
"""Nạp tự động từ obc_bot (đặc tả 2026-10-14-tu-dong-lay-obc-design.md §5).

Hai route JSON dưới /api/kho-du-lieu — cùng thân với POST /upload, cùng cổng
quyền của màn Kho dữ liệu (middleware gác theo tiền tố, không gác tay)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kome import nap_cho
from kome.web.app import create_app

OK = Path("tests/fixtures/zaiko_ok.xlsx")
TEN = "在庫一覧_20260916.xlsx"
MK = "mat-khau-obc-bot-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"


@pytest.fixture
def web(conn, test_db_url, tmp_path, monkeypatch):
    """Máy trong công ty, không cổng đăng nhập (mặc định conftest)."""
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "kho"))
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")
    return TestClient(create_app(db_url=test_db_url))


def _nap(c, ten=TEN, noi_dung=None):
    return c.post("/api/kho-du-lieu/nap",
                  files=[("files", (ten, noi_dung if noi_dung is not None else OK.read_bytes()))])


def test_nap_tra_json_va_tao_lo(web, conn):
    r = _nap(web)
    assert r.status_code == 200
    k = r.json()["ket_qua"][0]
    assert k["ten_file"] == TEN and k["ok"] and not k["skipped"]
    assert k["spec_name"] == "zaiko" and k["data_date"] == "2026-09-16"
    assert k["batch_id"] and k["row_count"] > 0 and k["blockers"] == []
    assert conn.execute("SELECT count(*) FROM meta.ingest_batch").fetchone()[0] == 1


def test_nap_lai_cung_file_la_bo_qua(web):
    _nap(web)
    k = _nap(web).json()["ket_qua"][0]
    assert k["ok"] and k["skipped"] and k["batch_id"] is None


def test_ten_file_la_bi_cong_1_chan_va_noi_ra(web, conn):
    k = _nap(web, ten="khong_ro.xlsx").json()["ket_qua"][0]
    assert not k["ok"] and k["blockers"][0]["cong"] == 1 and k["blockers"][0]["loi"]
    assert conn.execute("SELECT count(*) FROM meta.ingest_batch").fetchone()[0] == 0


def test_ban_chi_doc_tra_403_json(conn, test_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")
    r = _nap(TestClient(create_app(db_url=test_db_url)))
    assert r.status_code == 403 and r.json()["loi"]


@pytest.fixture
def co_cong(conn, test_db_url, tmp_path, monkeypatch):
    """Có cổng đăng nhập; trả hàm dựng client cho một tài khoản có / không cờ."""
    from kome.web import nguoi_dung as ND
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT)
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "kho"))
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")

    def _tao(kho_du_lieu: bool | None):
        c = TestClient(create_app(db_url=test_db_url))
        if kho_du_lieu is not None:
            ND.tao(conn, "obc-bot", MK, kho_du_lieu=kho_du_lieu)
            conn.commit()
            c.post("/dang-nhap", data={"ten": "obc-bot", "mat_khau": MK})
        return c
    return _tao


def test_chua_dang_nhap_401_json(co_cong):
    r = _nap(co_cong(None))
    assert r.status_code == 401 and r.json()["loi"]


def test_thieu_co_kho_du_lieu_403_json(co_cong):
    r = _nap(co_cong(False))
    assert r.status_code == 403 and r.json()["loi"]


def test_co_co_thi_nap_duoc_va_ghi_ai_nap(co_cong, conn):
    k = _nap(co_cong(True)).json()["ket_qua"][0]
    assert k["ok"] and k["batch_id"]
    conn.rollback()
    ai = conn.execute("""SELECT n.ten FROM meta.ingest_batch b
                         JOIN app.nguoi_dung n ON n.id = b.nap_boi""").fetchone()[0]
    assert ai == "obc-bot"
```

- [ ] **Step 2: Chạy test, xác nhận hỏng**

Run: `pytest tests/test_nap_tu_dong.py -v`
Expected: FAIL — 404/405 trên `/api/kho-du-lieu/nap` (route chưa có). Nếu `test_co_co_thi_nap_duoc_va_ghi_ai_nap` hỏng vì tên cột khác `nap_boi` / `ten`, đọc `db/migrations/033_*.sql` và `019_danh_tinh.sql` để lấy đúng tên rồi sửa test.

- [ ] **Step 3: Viết mã**

Trong `kome/web/app.py`, thay toàn bộ route `upload` (dòng 869-891) bằng:

```python
    def _nap_mot_buoc(request: Request, files: list[UploadFile]) -> list:
        """Thân CHUNG của POST /upload (màn React) và POST /api/kho-du-lieu/nap
        (obc_bot): `ingest` đầy đủ — 5 cổng, chặn trùng theo mã băm — rồi ghi AI
        nạp và làm nóng ảnh chụp. Trả [(tên file, IngestResult)]. Hai route chỉ
        khác cách TRẢ kết quả; viết thân hai lần là hai luồng nạp trôi khỏi nhau."""
        from kome.pipeline import ingest
        ket = []
        with open_conn() as conn:
            for f in files:
                ten = Path(f.filename or "").name
                with tempfile.TemporaryDirectory() as tmp:
                    staged = Path(tmp) / ten
                    with staged.open("wb") as out:
                        shutil.copyfileobj(f.file, out)
                    ket.append((ten, ingest(conn, staged, archive_luu)))
            _ghi_ai(conn, "nap_boi", [r.batch_id for _, r in ket if r.batch_id],
                    getattr(request.state, "nguoi", None))
        if any(r.batch_id for _, r in ket):
            anh_chup.lam_nong(open_app_conn)
        return ket

    @app.post("/upload", response_class=HTMLResponse)
    def upload(request: Request, files: list[UploadFile]):
        if chi_doc:
            return _cam(request)
        try:
            results = [r for _, r in _nap_mot_buoc(request, files)]
            with open_conn() as conn:
                ctx = _du_lieu_nap(conn)
            return _man_kho(request, {**ctx, "results": results})
        except Exception as e:
            return _loi(request, "nạp file dữ liệu", e)

    # Nạp tự động (obc_bot, đặc tả 2026-10-14): CÙNG thân với /upload, trả JSON.
    # Nằm dưới /api/kho-du-lieu nên middleware tự gác: 401 JSON khi chưa đăng
    # nhập, 403 JSON khi thiếu duoc_vao_kho_du_lieu — không gác tay ở đây.
    @app.post("/api/kho-du-lieu/nap")
    def api_nap(request: Request, files: list[UploadFile]):
        if chi_doc:
            return JSONResponse({"loi": "Bản này chỉ đọc — không nạp được."}, status_code=403)
        try:
            ket = _nap_mot_buoc(request, files)
        except Exception as e:
            return JSONResponse({"loi": f"Nạp file lỗi: {e}"}, status_code=500)

        def _cong(ds):
            return [{"cong": x.gate, "loi": x.message} for x in ds]
        return {"ket_qua": [{
            "ten_file": ten, "ok": r.ok, "skipped": r.skipped, "spec_name": r.spec_name,
            "data_date": r.data_date.isoformat() if r.data_date else None,
            "row_count": r.row_count, "batch_id": r.batch_id,
            "blockers": _cong(r.blockers), "warnings": _cong(r.warnings),
        } for ten, r in ket]}
```

Kiểm `JSONResponse` đã được nhập ở đầu `app.py` (đã dùng ở middleware dòng 363 — nếu nhập trong thân hàm thì thêm `from fastapi.responses import JSONResponse` ở đầu file).

- [ ] **Step 4: Chạy test, xác nhận qua**

Run: `pytest tests/test_nap_tu_dong.py tests/test_nap_vercel.py tests/test_bao_mat.py -v`
Expected: PASS hết (route `/upload` cũ không đổi hành vi; `test_trang_chi_doc_khong_phu_thuoc_pandas` vẫn xanh).

- [ ] **Step 5: Commit**

```bash
git add kome/web/app.py tests/test_nap_tu_dong.py
git commit -m "feat(nap): POST /api/kho-du-lieu/nap — nap mot buoc tra JSON cho obc_bot, chung than voi /upload"
```

---

### Task 2: `GET /api/kho-du-lieu/hom-nay` + `.vercelignore`

**Files:**
- Modify: `kome/web/app.py` (thêm hằng `MUC_HANG_NGAY` cạnh `DUONG_KHO_DU_LIEU`, route ngay sau `api_nap`)
- Modify: `.vercelignore`
- Modify: `docs/superpowers/specs/2026-10-14-tu-dong-lay-obc-design.md` §5.2 ("1 lượt hỏi" → "2 lượt — đọc lại `tinh_tuoi`")
- Test: `tests/test_nap_tu_dong.py`

**Interfaces:**
- Consumes: `kome.tuoi_du_lieu.tinh_tuoi(conn, bay_gio=None) -> Tuoi` (`Tuoi.hom_nay`, `Tuoi.nguon[*].spec`, `.trang_thai` ∈ `xanh|cho|do|nghi`); `kome.tuoi_du_lieu._bay_gio` (thay được trong test).
- Produces: `kome.web.app.MUC_HANG_NGAY = {"ban": "meisai", "ton": "zaiko", "khach": "tokuisaki"}`; `GET /api/kho-du-lieu/hom-nay` → `{"ngay": "YYYY-MM-DD", "la_ngay_kd": bool, "da_co": {"ban": bool, "ton": bool, "khach": bool}}`.

- [ ] **Step 1: Viết test hỏng** (thêm vào cuối `tests/test_nap_tu_dong.py`)

```python
from datetime import datetime

from kome import tuoi_du_lieu as TD
from kome.pipeline import ingest


def _dong_ho(monkeypatch, *args):
    monkeypatch.setattr(TD, "_bay_gio", lambda: datetime(*args, tzinfo=TD.MUI_GIO))


def test_hom_nay_noi_muc_nao_da_co(web, conn, tmp_path, monkeypatch):
    p = tmp_path / TEN
    p.write_bytes(OK.read_bytes())
    assert ingest(conn, p, None).ok
    _dong_ho(monkeypatch, 2026, 9, 16, 14, 0)        # thứ Tư
    j = web.get("/api/kho-du-lieu/hom-nay").json()
    assert j == {"ngay": "2026-09-16", "la_ngay_kd": True,
                 "da_co": {"ban": False, "ton": True, "khach": False}}


def test_hom_nay_ngay_nghi(web, monkeypatch):
    _dong_ho(monkeypatch, 2026, 9, 19, 14, 0)        # thứ Bảy
    assert web.get("/api/kho-du-lieu/hom-nay").json()["la_ngay_kd"] is False


def test_hom_nay_chua_dang_nhap_401(co_cong):
    assert co_cong(None).get("/api/kho-du-lieu/hom-nay").status_code == 401


def test_muc_hang_ngay_trung_nguon_hang_ngay_cua_tuoi_du_lieu():
    from kome.web.app import MUC_HANG_NGAY
    assert sorted(MUC_HANG_NGAY.values()) == sorted(TD.NGUON_HANG_NGAY)
```

- [ ] **Step 2: Chạy test, xác nhận hỏng**

Run: `pytest tests/test_nap_tu_dong.py -v -k "hom_nay or muc_hang_ngay"`
Expected: FAIL — `ImportError: MUC_HANG_NGAY` và 404/SPA trên `/api/kho-du-lieu/hom-nay`.

- [ ] **Step 3: Viết mã**

Trong `kome/web/app.py`, ngay sau `_thuoc_kho_du_lieu` (khoảng dòng 118):

```python
# Ba mục mà obc_bot xuất hằng ngày -> spec của ô 13:30 (`tuoi_du_lieu.NGUON_HANG_NGAY`).
# `obc_bot/ten_file.py::MUC_SPEC` là bản chép bắt buộc (có test canh).
MUC_HANG_NGAY = {"ban": "meisai", "ton": "zaiko", "khach": "tokuisaki"}
```

Ngay sau route `api_nap`:

```python
    @app.get("/api/kho-du-lieu/hom-nay")
    def api_hom_nay():
        """Cho obc_bot: hôm nay (giờ Tokyo) có phải ngày làm việc không, và mục
        nào ĐÃ có dữ liệu mang ngày hôm nay — đọc lại `tinh_tuoi`, cùng luật với
        ô 13:30 của /kho-du-lieu (không định nghĩa thứ hai)."""
        from kome import tuoi_du_lieu as TD
        try:
            with open_app_conn() as c:
                t = TD.tinh_tuoi(c)
        except Exception as e:
            return JSONResponse({"loi": f"Không đọc được tình trạng hôm nay: {e}"},
                                status_code=500)
        theo = {n.spec: n.trang_thai for n in t.nguon}
        return {"ngay": t.hom_nay.isoformat(),
                "la_ngay_kd": "nghi" not in theo.values(),
                "da_co": {m: theo[s] == "xanh" for m, s in MUC_HANG_NGAY.items()}}
```

Trong `.vercelignore`, thêm sau dòng `giao_dien/`:

```
# Chương trình bấm OBC chạy trên máy Windows trong công ty — web không nhập nó.
obc_bot/
```

Trong đặc tả §5.2 sửa tiêu đề `— 1 lượt hỏi` thành `— 2 lượt hỏi (đọc lại tinh_tuoi)`.

- [ ] **Step 4: Chạy test, xác nhận qua**

Run: `pytest tests/test_nap_tu_dong.py -v`
Expected: PASS hết.

- [ ] **Step 5: Commit**

```bash
git add kome/web/app.py tests/test_nap_tu_dong.py .vercelignore docs/superpowers/specs/2026-10-14-tu-dong-lay-obc-design.md
git commit -m "feat(nap): GET /api/kho-du-lieu/hom-nay cho obc_bot — doc lai tinh_tuoi; obc_bot khoi Vercel"
```

---

### Task 3: Gói `obc_bot` — tên file và cấu hình

**Files:**
- Create: `obc_bot/__init__.py` (rỗng, một dòng docstring), `obc_bot/ten_file.py`, `obc_bot/cau_hinh.py`, `obc_bot/requirements.txt`, `obc_bot/vi_du_may_b.toml`, `obc_bot/vi_du_may_long.toml`
- Test: `tests/test_obc_bot_co_ban.py`

**Interfaces:**
- Produces: `obc_bot.ten_file.MUC_SPEC: dict[str, str]`, `ten_file(muc: str, ngay: date) -> str`; `obc_bot.cau_hinh.CauHinh` (frozen dataclass: `muc: tuple[str, ...]`, `web_url: str`, `tai_khoan_web: str`, `thu_muc_ra: Path`, `thu_muc_bao_loi: Path | None`, `pattern: dict[str, int]`, `dem_nguoc_giay: int`, `ten_may: str`), `doc(duong: Path) -> CauHinh`, `CauHinhSai(Exception)`.

- [ ] **Step 1: Viết test hỏng**

`tests/test_obc_bot_co_ban.py`:

```python
"""obc_bot: tên file ra và cấu hình — không cần OBC, không cần mạng."""
from datetime import date
from pathlib import Path

import pytest

from obc_bot import cau_hinh as CH
from obc_bot.ten_file import MUC_SPEC, ten_file


@pytest.mark.parametrize("muc", sorted(MUC_SPEC))
def test_ten_file_duoc_pipeline_nhan_dung_spec_va_ngay(muc):
    """Bản chép của files.yml: tên obc_bot sinh ra phải qua cổng 1 đúng loại."""
    from kome.pipeline import identify
    spec, ngay = identify(Path(ten_file(muc, date(2026, 10, 14))))
    assert spec is not None and spec.name == MUC_SPEC[muc]
    assert ngay == date(2026, 10, 14)


def test_muc_spec_trung_ban_cua_web():
    from kome.web.app import MUC_HANG_NGAY
    assert MUC_SPEC == MUC_HANG_NGAY


def _viet(tmp_path, noi_dung: str) -> Path:
    p = tmp_path / "c.toml"
    p.write_text(noi_dung, encoding="utf-8")
    return p


HOP_LE = """
muc = ["ban", "ton"]
web_url = "https://kome.example.vercel.app/"
tai_khoan_web = "obc-bot"
thu_muc_ra = "C:/KOME/obc_xuat"
thu_muc_bao_loi = "C:/OneDrive/KOME自動取込"
ten_may = "may-b"
[pattern]
ban = 3
ton = 5
"""


def test_doc_cau_hinh_hop_le(tmp_path):
    ch = CH.doc(_viet(tmp_path, HOP_LE))
    assert ch.muc == ("ban", "ton") and ch.pattern == {"ban": 3, "ton": 5}
    assert ch.web_url == "https://kome.example.vercel.app"      # bỏ "/" cuối
    assert ch.thu_muc_ra == Path("C:/KOME/obc_xuat") and ch.dem_nguoc_giay == 0
    assert ch.ten_may == "may-b"


@pytest.mark.parametrize("sua, cau", [
    (('muc = ["ban", "ton"]', 'muc = ["ban", "la"]'), "mục lạ"),
    (('muc = ["ban", "ton"]', 'muc = []'), "ít nhất một mục"),
    (("ton = 5", ""), "pattern"),
    (("ton = 5", "ton = 0"), "pattern"),
    (('https://kome.example.vercel.app/', 'http://kome.example.com'), "https"),
])
def test_cau_hinh_sai_noi_ro_cho_sai(tmp_path, sua, cau):
    with pytest.raises(CH.CauHinhSai, match=cau):
        CH.doc(_viet(tmp_path, HOP_LE.replace(*sua)))


def test_http_chi_cho_may_noi_bo(tmp_path):
    ch = CH.doc(_viet(tmp_path, HOP_LE.replace("https://kome.example.vercel.app/",
                                               "http://127.0.0.1:8000")))
    assert ch.web_url == "http://127.0.0.1:8000"
```

- [ ] **Step 2: Chạy test, xác nhận hỏng**

Run: `pytest tests/test_obc_bot_co_ban.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'obc_bot'`.

- [ ] **Step 3: Viết mã**

`obc_bot/__init__.py`:

```python
"""Tự động lấy dữ liệu 商奉行クラウド và nạp vào web (đặc tả 2026-10-14-tu-dong-lay-obc-design.md)."""
```

`obc_bot/ten_file.py`:

```python
"""Tên file ra — BẢN CHÉP của `filename_pattern` trong config/files.yml.

Web nhận diện loại file CHỈ theo tên (cổng 1), nên một ký tự lệch ở đây là cả
lượt chạy bị chặn. Có test canh: tests/test_obc_bot_co_ban.py chạy từng tên qua
kome.pipeline.identify, và MUC_SPEC phải bằng kome.web.app.MUC_HANG_NGAY."""
from datetime import date

MUC_SPEC = {"ban": "meisai", "ton": "zaiko", "khach": "tokuisaki"}

_TIEN_TO = {"ban": "売上明細表", "ton": "在庫一覧", "khach": "得意先全情報"}


def ten_file(muc: str, ngay: date) -> str:
    return f"{_TIEN_TO[muc]}_{ngay:%Y%m%d}.xlsx"
```

`obc_bot/cau_hinh.py`:

```python
"""Cấu hình của MỘT máy chạy (TOML). Mật khẩu web KHÔNG nằm ở đây — keyring."""
import socket
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from obc_bot.ten_file import MUC_SPEC

_NOI_BO = {"127.0.0.1", "localhost", "testserver"}


class CauHinhSai(Exception):
    pass


@dataclass(frozen=True)
class CauHinh:
    muc: tuple[str, ...]
    web_url: str
    tai_khoan_web: str              # "" = web không có cổng đăng nhập (máy công ty để trống khoá)
    thu_muc_ra: Path
    thu_muc_bao_loi: Path | None
    pattern: dict[str, int]         # mục -> số 出力パターン trong OBC
    dem_nguoc_giay: int
    ten_may: str


def doc(duong: Path) -> CauHinh:
    with open(duong, "rb") as f:
        d = tomllib.load(f)
    muc = tuple(d.get("muc", ()))
    if not muc:
        raise CauHinhSai("`muc` phải có ít nhất một mục (ban / ton / khach).")
    la = [m for m in muc if m not in MUC_SPEC]
    if la or len(set(muc)) != len(muc):
        raise CauHinhSai(f"`muc` có mục lạ hoặc lặp: {list(muc)} — chỉ nhận {sorted(MUC_SPEC)}.")
    url = str(d.get("web_url", "")).rstrip("/")
    u = urlparse(url)
    if not (u.scheme == "https" or (u.scheme == "http" and u.hostname in _NOI_BO)):
        raise CauHinhSai(f"`web_url` phải là https:// (http chỉ cho máy nội bộ): {url!r}")
    pattern = {k: v for k, v in d.get("pattern", {}).items()}
    for m in muc:
        if not isinstance(pattern.get(m), int) or pattern[m] <= 0:
            raise CauHinhSai(f"Thiếu [pattern] {m} = <số 出力パターン > 0>.")
    loi = d.get("thu_muc_bao_loi")
    return CauHinh(
        muc=muc, web_url=url, tai_khoan_web=str(d.get("tai_khoan_web", "")),
        thu_muc_ra=Path(d["thu_muc_ra"]), thu_muc_bao_loi=Path(loi) if loi else None,
        pattern={m: pattern[m] for m in muc},
        dem_nguoc_giay=int(d.get("dem_nguoc_giay", 0)),
        ten_may=str(d.get("ten_may") or socket.gethostname()))
```

`obc_bot/requirements.txt`:

```
requests>=2.32
pywinauto>=0.6.9
keyring>=25
pillow>=10
```

`obc_bot/vi_du_may_b.toml`:

```toml
# Máy B (máy riêng) — tài khoản OBC của chủ DN. Chép thành may_b.toml rồi sửa.
muc = ["ban", "ton"]
web_url = "https://<địa chỉ bản Vercel>"
tai_khoan_web = "obc-bot"
thu_muc_ra = "C:/KOME/obc_xuat"
thu_muc_bao_loi = "C:/Users/<người dùng>/OneDrive - 株式会社KOME/KOME自動取込"

[pattern]          # số 出力パターン đã tạo trong OBC
ban = 1
ton = 1
```

`obc_bot/vi_du_may_long.toml`:

```toml
# Máy của Long — tài khoản OBC của Long (quyền 得意先). Chép thành may_long.toml rồi sửa.
muc = ["khach"]
web_url = "https://<địa chỉ bản Vercel>"
tai_khoan_web = "obc-bot"
thu_muc_ra = "C:/KOME/obc_xuat"
thu_muc_bao_loi = "C:/Users/<người dùng>/OneDrive - 株式会社KOME/KOME自動取込"
dem_nguoc_giay = 30   # Long đang ở máy: báo trước khi chiếm chuột

[pattern]
khach = 1
```

- [ ] **Step 4: Chạy test, xác nhận qua**

Run: `pytest tests/test_obc_bot_co_ban.py -v`
Expected: PASS hết.

- [ ] **Step 5: Commit**

```bash
git add obc_bot tests/test_obc_bot_co_ban.py
git commit -m "feat(obc_bot): ten file (ban chep files.yml) va cau hinh TOML tung may"
```

---

### Task 4: `obc_bot.web` — đăng nhập, hôm nay, nạp + lệnh `nap`, `luu-mat-khau`

**Files:**
- Create: `obc_bot/web.py`, `obc_bot/__main__.py`
- Test: `tests/test_obc_bot_web.py`

**Interfaces:**
- Consumes: Task 1–2 routes; `CauHinh`, `cau_hinh.doc` (Task 3).
- Produces: `obc_bot.web.LoiWeb(Exception)`; `KhachWeb(base_url: str, phien=None)` với `.dang_nhap(ten: str, mat_khau: str) -> None`, `.hom_nay() -> dict`, `.nap(files: list[Path]) -> list[dict]`; `mat_khau_web(ten: str) -> str` (ném `LoiWeb` khi chưa lưu); `DICH_VU_KEYRING = "kome-obc-bot"`. CLI: `python -m obc_bot nap --cau-hinh X.toml FILE...` (thoát 0 khi mọi file `ok`), `python -m obc_bot luu-mat-khau --cau-hinh X.toml`.

`phien` là bất cứ thứ gì có `.get(url)` / `.post(url, data=, files=)` trả `.status_code` / `.json()` và tự giữ cookie — `requests.Session` ở máy thật, `fastapi.testclient.TestClient` trong test (gọi thẳng web app thật, không máy chủ giả).

- [ ] **Step 1: Viết test hỏng**

`tests/test_obc_bot_web.py`:

```python
"""obc_bot.web gọi THẲNG web app thật qua TestClient (cùng giao diện .get/.post
với requests.Session) — chứng minh đầu-cuối: đăng nhập -> hôm nay -> nạp."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kome import nap_cho
from kome.web.app import create_app
from obc_bot.web import KhachWeb, LoiWeb

OK = Path("tests/fixtures/zaiko_ok.xlsx")
TEN = "在庫一覧_20260916.xlsx"
MK = "mat-khau-obc-bot-2026"


@pytest.fixture
def khach(conn, test_db_url, tmp_path, monkeypatch):
    from kome.web import nguoi_dung as ND
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    monkeypatch.setenv("KOME_SESSION_SECRET", "bi-mat-phien-du-dai-2026")
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "kho"))
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")

    def _tao(kho_du_lieu=True):
        ND.tao(conn, "obc-bot", MK, kho_du_lieu=kho_du_lieu)
        conn.commit()
        return KhachWeb("http://testserver", phien=TestClient(create_app(db_url=test_db_url)))
    return _tao


def _file(tmp_path) -> Path:
    p = tmp_path / TEN
    p.write_bytes(OK.read_bytes())
    return p


def test_dang_nhap_hom_nay_nap(khach, tmp_path):
    w = khach()
    w.dang_nhap("obc-bot", MK)
    assert set(w.hom_nay()["da_co"]) == {"ban", "ton", "khach"}
    k = w.nap([_file(tmp_path)])[0]
    assert k["ok"] and k["spec_name"] == "zaiko" and k["batch_id"]


def test_sai_mat_khau_noi_ro(khach):
    with pytest.raises(LoiWeb, match="mật khẩu"):
        khach().dang_nhap("obc-bot", "sai")


def test_chua_dang_nhap_noi_ro(khach, tmp_path):
    with pytest.raises(LoiWeb, match="đăng nhập"):
        khach().nap([_file(tmp_path)])


def test_thieu_co_kho_du_lieu_noi_ro(khach, tmp_path):
    w = khach(kho_du_lieu=False)
    w.dang_nhap("obc-bot", MK)
    with pytest.raises(LoiWeb, match="từ chối"):
        w.nap([_file(tmp_path)])
```

- [ ] **Step 2: Chạy test, xác nhận hỏng**

Run: `pytest tests/test_obc_bot_web.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'obc_bot.web'`.

- [ ] **Step 3: Viết mã**

`obc_bot/web.py`:

```python
"""Nửa NẠP: gửi file lên web như một người dùng (tài khoản obc-bot).

Không đụng CSDL — máy chạy không giữ mật khẩu CSDL nào. Mọi file đi qua
POST /api/kho-du-lieu/nap = pipeline.ingest, 5 cổng như kéo thả tay."""
from pathlib import Path

DICH_VU_KEYRING = "kome-obc-bot"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class LoiWeb(Exception):
    pass


def _loi(r) -> str:
    try:
        return r.json().get("loi") or r.text[:200]
    except Exception:
        return r.text[:200]


class KhachWeb:
    def __init__(self, base_url: str, phien=None):
        if phien is None:
            import requests
            phien = requests.Session()
        self.base = base_url.rstrip("/")
        self.phien = phien

    def dang_nhap(self, ten: str, mat_khau: str) -> None:
        r = self.phien.post(self.base + "/dang-nhap", data={"ten": ten, "mat_khau": mat_khau})
        if r.status_code == 401:
            raise LoiWeb(f"Sai tên hoặc mật khẩu tài khoản web {ten!r}.")
        if r.status_code >= 400:
            raise LoiWeb(f"Đăng nhập web lỗi {r.status_code}: {_loi(r)}")

    def hom_nay(self) -> dict:
        return self._json(self.phien.get(self.base + "/api/kho-du-lieu/hom-nay"))

    def nap(self, files: list[Path]) -> list[dict]:
        mo = [open(p, "rb") for p in files]
        try:
            r = self.phien.post(self.base + "/api/kho-du-lieu/nap",
                                files=[("files", (p.name, f, _XLSX)) for p, f in zip(files, mo)])
        finally:
            for f in mo:
                f.close()
        return self._json(r)["ket_qua"]

    @staticmethod
    def _json(r) -> dict:
        if r.status_code == 401:
            raise LoiWeb("Chưa đăng nhập web (sai mật khẩu obc-bot hoặc phiên hết hạn).")
        if r.status_code == 403:
            raise LoiWeb(f"Web từ chối: {_loi(r)}")
        if r.status_code != 200:
            raise LoiWeb(f"Web lỗi {r.status_code}: {_loi(r)}")
        return r.json()


def mat_khau_web(ten: str) -> str:
    import keyring
    mk = keyring.get_password(DICH_VU_KEYRING, ten)
    if not mk:
        raise LoiWeb(f"Chưa lưu mật khẩu web cho {ten!r} trên máy này — chạy: "
                     "python -m obc_bot luu-mat-khau --cau-hinh <file>.toml")
    return mk
```

`obc_bot/__main__.py`:

```python
"""python -m obc_bot <lệnh> --cau-hinh <máy>.toml ...

  nap FILE...      chỉ nạp file đã có (xuất tay) — lối dự phòng khi phần bấm OBC hỏng
  luu-mat-khau     lưu mật khẩu web của tai_khoan_web vào Windows Credential Manager
"""
import argparse
import getpass
import sys
from pathlib import Path

from obc_bot import cau_hinh as CH
from obc_bot.web import DICH_VU_KEYRING, KhachWeb, LoiWeb, mat_khau_web


def _web(ch: CH.CauHinh) -> KhachWeb:
    w = KhachWeb(ch.web_url)
    if ch.tai_khoan_web:
        w.dang_nhap(ch.tai_khoan_web, mat_khau_web(ch.tai_khoan_web))
    return w


def lenh_nap(ch: CH.CauHinh, files: list[Path]) -> int:
    try:
        kq = _web(ch).nap(files)
    except LoiWeb as e:
        print(f"LỖI WEB: {e}")
        return 1
    for k in kq:
        if k["ok"]:
            print(f"OK   {k['ten_file']}: {k['row_count']} dòng"
                  + (" (đã có, bỏ qua)" if k["skipped"] else ""))
        else:
            for b in k["blockers"]:
                print(f"CHẶN {k['ten_file']}: cổng {b['cong']}: {b['loi']}")
    return 0 if all(k["ok"] for k in kq) else 1


def lenh_luu_mat_khau(ch: CH.CauHinh) -> int:
    import keyring
    if not ch.tai_khoan_web:
        print("Cấu hình không có tai_khoan_web — không cần mật khẩu.")
        return 0
    keyring.set_password(DICH_VU_KEYRING, ch.tai_khoan_web,
                         getpass.getpass(f"Mật khẩu web của {ch.tai_khoan_web}: "))
    print("Đã lưu vào Windows Credential Manager.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="obc_bot")
    sub = p.add_subparsers(dest="lenh", required=True)
    for ten in ("nap", "luu-mat-khau"):
        s = sub.add_parser(ten)
        s.add_argument("--cau-hinh", required=True, type=Path)
        if ten == "nap":
            s.add_argument("files", nargs="+", type=Path)
    a = p.parse_args(argv)
    try:
        ch = CH.doc(a.cau_hinh)
    except CH.CauHinhSai as e:
        print(f"CẤU HÌNH SAI: {e}")
        return 2
    if a.lenh == "nap":
        return lenh_nap(ch, a.files)
    return lenh_luu_mat_khau(ch)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Chạy test, xác nhận qua**

Run: `pytest tests/test_obc_bot_web.py tests/test_obc_bot_co_ban.py -v`
Expected: PASS hết. Nếu `test_sai_mat_khau_noi_ro` hỏng vì TestClient theo chuyển hướng ra mã khác 401, in `r.status_code` để xem — `/dang-nhap` sai trả 401 trực tiếp (`app.py:424`), không chuyển hướng.

- [ ] **Step 5: Commit**

```bash
git add obc_bot/web.py obc_bot/__main__.py tests/test_obc_bot_web.py
git commit -m "feat(obc_bot): nua nap — dang nhap obc-bot, hoi hom nay, nap qua /api/kho-du-lieu/nap; lenh nap + luu-mat-khau"
```

---

### Task 5: Bộ điều phối `chay` — kết cục, báo lỗi, màn hình khoá

**Files:**
- Create: `obc_bot/chay.py`, `obc_bot/bao_cao.py`, `obc_bot/man_hinh.py`, `obc_bot/obc/__init__.py`
- Modify: `obc_bot/__main__.py` (thêm lệnh `chay`)
- Modify: `CLAUDE.md` (mục bất biến `obc_bot`)
- Test: `tests/test_obc_bot_chay.py`

**Interfaces:**
- Consumes: `KhachWeb`, `LoiWeb`, `mat_khau_web` (Task 4); `CauHinh` (Task 3); `ten_file` (Task 3).
- Produces:
  - `obc_bot.chay.LoiObc(buoc: str, loi: str, anh: Path | None = None)` — Exception có thuộc tính `buoc`, `loi`, `anh`.
  - `KetCuc(loai: str, chi_tiet: list[str], anh: list[Path])`, `.can_bao -> bool`; `loai` ∈ `xong | bo_qua | cong_chan | loi_obc | man_hinh_khoa | loi_web`.
  - `MoiTruong(man_hinh_khoa: Callable[[], bool], xuat: Callable[[str, date, Path, int], Path], khoi_dong_lai_obc: Callable[[], None], mat_khau: Callable[[str], str], thong_bao: Callable[[str, str], None], ngu: Callable[[int], None])`.
  - `chay(ch: CauHinh, web, mt: MoiTruong) -> KetCuc`.
  - `obc_bot.bao_cao.ghi(ch, kc: KetCuc, ngay: date) -> Path | None` (đường tệp báo lỗi, None khi không cần báo); `thong_bao_windows(tieu_de: str, noi_dung: str) -> None`.
  - `obc_bot.man_hinh.dang_khoa() -> bool`, `chup(duong: Path) -> Path | None`.
  - `obc_bot.obc.xuat(muc, ngay, thu_muc, pattern) -> Path`, `obc_bot.obc.khoi_dong_lai() -> None` — ở Task này cả hai ném `LoiObc("chưa viết", ...)`; Task 7 thay thân.

Thứ tự ưu tiên kết cục khi có nhiều vấn đề: `man_hinh_khoa` (dừng ngay) → `loi_web` → `loi_obc` → `cong_chan` → `xong`. Một mục xuất hỏng KHÔNG chặn nạp các mục đã xuất được.

- [ ] **Step 1: Viết test hỏng**

`tests/test_obc_bot_chay.py`:

```python
"""Bộ điều phối: mọi lượt chạy kết thúc ở ĐÚNG MỘT kết cục (đặc tả §6)."""
from datetime import date
from pathlib import Path

import pytest

from obc_bot import bao_cao
from obc_bot.cau_hinh import CauHinh
from obc_bot.chay import KetCuc, LoiObc, MoiTruong, chay
from obc_bot.ten_file import ten_file
from obc_bot.web import LoiWeb

NGAY = date(2026, 10, 14)


def _ch(tmp_path, muc=("ban", "ton"), dem=0, tai_khoan="obc-bot"):
    return CauHinh(muc=muc, web_url="https://x", tai_khoan_web=tai_khoan,
                   thu_muc_ra=tmp_path / "ra", thu_muc_bao_loi=tmp_path / "loi",
                   pattern={m: 1 for m in muc}, dem_nguoc_giay=dem, ten_may="may-b")


class WebGia:
    def __init__(self, da_co=None, la_ngay_kd=True, chan=(), loi_nap=None, loi_dang_nhap=None):
        self.da_co = {"ban": False, "ton": False, "khach": False, **(da_co or {})}
        self.la_ngay_kd, self.chan = la_ngay_kd, set(chan)
        self.loi_nap, self.loi_dang_nhap = loi_nap, loi_dang_nhap
        self.da_nap: list[Path] = []
        self.dang_nhap_voi = None

    def dang_nhap(self, ten, mk):
        if self.loi_dang_nhap:
            raise LoiWeb(self.loi_dang_nhap)
        self.dang_nhap_voi = (ten, mk)

    def hom_nay(self):
        return {"ngay": NGAY.isoformat(), "la_ngay_kd": self.la_ngay_kd, "da_co": self.da_co}

    def nap(self, files):
        if self.loi_nap:
            raise LoiWeb(self.loi_nap)
        self.da_nap += files
        return [{"ten_file": p.name, "ok": p.name not in self.chan, "skipped": False,
                 "row_count": 10, "blockers": [{"cong": 3, "loi": "dưới min_rows"}]
                 if p.name in self.chan else []} for p in files]


def _mt(khoa=False, hong=None, ghi=None):
    """`hong`: {muc: số lần xuất hỏng liên tiếp trước khi được}."""
    hong = dict(hong or {})
    ghi = ghi if ghi is not None else {"xuat": [], "khoi_dong_lai": 0, "thong_bao": [], "ngu": []}

    def xuat(muc, ngay, thu_muc, pattern):
        ghi["xuat"].append(muc)
        if hong.get(muc, 0) > 0:
            hong[muc] -= 1
            raise LoiObc("chọn pattern", "không thấy ô 出力パターン")
        thu_muc.mkdir(parents=True, exist_ok=True)
        p = thu_muc / ten_file(muc, ngay)
        p.write_bytes(b"x")
        return p

    def khoi_dong_lai():
        ghi["khoi_dong_lai"] += 1

    return MoiTruong(man_hinh_khoa=lambda: khoa, xuat=xuat, khoi_dong_lai_obc=khoi_dong_lai,
                     mat_khau=lambda ten: "mk", thong_bao=lambda t, n: ghi["thong_bao"].append(t),
                     ngu=lambda s: ghi["ngu"].append(s)), ghi


def test_man_hinh_khoa_dung_ngay_khong_bam_gi(tmp_path):
    mt, ghi = _mt(khoa=True)
    kc = chay(_ch(tmp_path), WebGia(), mt)
    assert kc.loai == "man_hinh_khoa" and kc.can_bao and ghi["xuat"] == []


def test_ngay_nghi_bo_qua(tmp_path):
    mt, ghi = _mt()
    kc = chay(_ch(tmp_path), WebGia(la_ngay_kd=False), mt)
    assert kc.loai == "bo_qua" and not kc.can_bao and ghi["xuat"] == []


def test_da_co_du_thi_khong_chiem_chuot(tmp_path):
    mt, ghi = _mt()
    kc = chay(_ch(tmp_path), WebGia(da_co={"ban": True, "ton": True}), mt)
    assert kc.loai == "bo_qua" and ghi["xuat"] == []


def test_chi_xuat_muc_con_thieu_va_nap_vao_thu_muc_thang(tmp_path):
    mt, ghi = _mt()
    w = WebGia(da_co={"ban": True})
    kc = chay(_ch(tmp_path), w, mt)
    assert kc.loai == "xong" and ghi["xuat"] == ["ton"]
    assert w.da_nap == [tmp_path / "ra" / "2026-10" / "在庫一覧_20261014.xlsx"]
    assert w.dang_nhap_voi == ("obc-bot", "mk")


def test_khong_tai_khoan_web_thi_khong_dang_nhap(tmp_path):
    mt, _ = _mt()
    w = WebGia()
    chay(_ch(tmp_path, tai_khoan=""), w, mt)
    assert w.dang_nhap_voi is None


def test_hong_mot_lan_thi_khoi_dong_lai_va_thu_lai(tmp_path):
    mt, ghi = _mt(hong={"ban": 1})
    kc = chay(_ch(tmp_path), WebGia(), mt)
    assert kc.loai == "xong" and ghi["khoi_dong_lai"] == 1
    assert ghi["xuat"] == ["ban", "ban", "ton"]


def test_hong_hai_lan_la_loi_obc_nhung_muc_khac_van_nap(tmp_path):
    mt, ghi = _mt(hong={"ban": 2})
    w = WebGia()
    kc = chay(_ch(tmp_path), w, mt)
    assert kc.loai == "loi_obc" and kc.can_bao
    assert "chọn pattern" in kc.chi_tiet[0] and "ban" in kc.chi_tiet[0]
    assert [p.name for p in w.da_nap] == ["在庫一覧_20261014.xlsx"]


def test_cong_chan_noi_nguyen_van(tmp_path):
    mt, _ = _mt()
    kc = chay(_ch(tmp_path), WebGia(chan={"在庫一覧_20261014.xlsx"}), mt)
    assert kc.loai == "cong_chan"
    assert any("cổng 3" in d and "dưới min_rows" in d for d in kc.chi_tiet)


def test_loi_web_khi_nap_noi_cho_de_file(tmp_path):
    mt, _ = _mt()
    kc = chay(_ch(tmp_path), WebGia(loi_nap="mạng"), mt)
    assert kc.loai == "loi_web" and any(str(tmp_path / "ra") in d for d in kc.chi_tiet)


def test_sai_mat_khau_web_la_loi_web_truoc_khi_bam(tmp_path):
    mt, ghi = _mt()
    kc = chay(_ch(tmp_path), WebGia(loi_dang_nhap="sai mật khẩu"), mt)
    assert kc.loai == "loi_web" and ghi["xuat"] == []


def test_dem_nguoc_bao_truoc_roi_moi_bam(tmp_path):
    mt, ghi = _mt()
    chay(_ch(tmp_path, muc=("khach",), dem=30), WebGia(), mt)
    assert ghi["ngu"] == [30] and ghi["thong_bao"] and ghi["xuat"] == ["khach"]


def test_bao_cao_ghi_log_va_tep_loi_chi_khi_can_bao(tmp_path):
    ch = _ch(tmp_path)
    assert bao_cao.ghi(ch, KetCuc("xong", ["ok"], []), NGAY) is None
    p = bao_cao.ghi(ch, KetCuc("cong_chan", ["cổng 3: dưới min_rows"], []), NGAY)
    assert p == tmp_path / "loi" / "2026-10-14_may-b_cong_chan.txt"
    assert "dưới min_rows" in p.read_text(encoding="utf-8")
    log = (tmp_path / "ra" / "log" / "2026-10-14.log").read_text(encoding="utf-8")
    assert "xong" in log and "cong_chan" in log
```

- [ ] **Step 2: Chạy test, xác nhận hỏng**

Run: `pytest tests/test_obc_bot_chay.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'obc_bot.chay'`.

- [ ] **Step 3: Viết mã**

`obc_bot/chay.py`:

```python
"""Một lượt chạy: kiểm trước -> xuất từng mục còn thiếu -> nạp -> MỘT kết cục.

Mọi thứ chạm thế giới thật (màn hình, OBC, keyring, thông báo, đồng hồ ngủ) đi
qua MoiTruong để test thay được — phần bấm OBC không có test tự động."""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

from obc_bot.cau_hinh import CauHinh
from obc_bot.ten_file import ten_file
from obc_bot.web import LoiWeb

CAN_BAO = ("cong_chan", "loi_obc", "man_hinh_khoa", "loi_web")
_UU_TIEN = ("loi_web", "loi_obc", "cong_chan")


class LoiObc(Exception):
    def __init__(self, buoc: str, loi: str, anh: Path | None = None):
        super().__init__(f"{buoc}: {loi}")
        self.buoc, self.loi, self.anh = buoc, loi, anh


@dataclass
class KetCuc:
    loai: str
    chi_tiet: list[str]
    anh: list[Path] = field(default_factory=list)

    @property
    def can_bao(self) -> bool:
        return self.loai in CAN_BAO


@dataclass
class MoiTruong:
    man_hinh_khoa: Callable[[], bool]
    xuat: Callable[[str, date, Path, int], Path]
    khoi_dong_lai_obc: Callable[[], None]
    mat_khau: Callable[[str], str]
    thong_bao: Callable[[str, str], None]
    ngu: Callable[[int], None]


def _xuat_thu_lai(ch: CauHinh, mt: MoiTruong, muc: str, ngay: date, thu_muc: Path) -> Path:
    """Hỏng lần đầu -> mở lại OBC rồi thử ĐÚNG một lần nữa (không giành phiên qua lại)."""
    try:
        p = mt.xuat(muc, ngay, thu_muc, ch.pattern[muc])
    except LoiObc:
        mt.khoi_dong_lai_obc()
        p = mt.xuat(muc, ngay, thu_muc, ch.pattern[muc])
    if p.name != ten_file(muc, ngay) or not p.exists():
        raise LoiObc("kiểm file ra", f"được {p}, cần {ten_file(muc, ngay)}")
    return p


def chay(ch: CauHinh, web, mt: MoiTruong) -> KetCuc:
    if mt.man_hinh_khoa():
        return KetCuc("man_hinh_khoa", ["Windows đang khoá màn hình hoặc ngủ — không bấm được OBC."])
    try:
        if ch.tai_khoan_web:
            web.dang_nhap(ch.tai_khoan_web, mt.mat_khau(ch.tai_khoan_web))
        hn = web.hom_nay()
    except LoiWeb as e:
        return KetCuc("loi_web", [str(e)])
    if not hn["la_ngay_kd"]:
        return KetCuc("bo_qua", [f"{hn['ngay']} không phải ngày làm việc."])
    can = [m for m in ch.muc if not hn["da_co"][m]]
    if not can:
        return KetCuc("bo_qua", [f"Hôm nay đã có đủ: {', '.join(ch.muc)}."])

    ngay = date.fromisoformat(hn["ngay"])
    thu_muc = ch.thu_muc_ra / f"{ngay:%Y-%m}"
    if ch.dem_nguoc_giay:
        mt.thong_bao("Sắp lấy dữ liệu OBC",
                     f"Sau {ch.dem_nguoc_giay} giây chương trình sẽ dùng chuột vài phút.")
        mt.ngu(ch.dem_nguoc_giay)

    van_de: list[tuple[str, str]] = []
    anh: list[Path] = []
    files: list[Path] = []
    for m in can:
        try:
            files.append(_xuat_thu_lai(ch, mt, m, ngay, thu_muc))
        except LoiObc as e:
            van_de.append(("loi_obc", f"{m}: bước '{e.buoc}': {e.loi}"))
            if e.anh:
                anh.append(e.anh)

    xong: list[str] = []
    if files:
        try:
            for k in web.nap(files):
                if k["ok"]:
                    xong.append(f"{k['ten_file']}: {k['row_count']} dòng"
                                + (" (đã có, bỏ qua)" if k["skipped"] else ""))
                else:
                    van_de += [("cong_chan", f"{k['ten_file']}: cổng {b['cong']}: {b['loi']}")
                               for b in k["blockers"]]
        except LoiWeb as e:
            van_de.append(("loi_web", f"{e} — file đã xuất nằm ở {thu_muc}, nạp tay được."))

    if not van_de:
        return KetCuc("xong", xong)
    loai = next(l for l in _UU_TIEN if any(v[0] == l for v in van_de))
    return KetCuc(loai, [v[1] for v in van_de] + xong, anh)
```

`obc_bot/bao_cao.py`:

```python
"""Log ngày + tệp báo lỗi vào thư mục OneDrive dùng chung + thông báo Windows."""
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path

from obc_bot.cau_hinh import CauHinh


def ghi(ch: CauHinh, kc, ngay: date) -> Path | None:
    log = ch.thu_muc_ra / "log" / f"{ngay:%Y-%m-%d}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%H:%M:%S} {kc.loai}\n")
        for d in kc.chi_tiet:
            f.write(f"    {d}\n")
    if not kc.can_bao or ch.thu_muc_bao_loi is None:
        return None
    ch.thu_muc_bao_loi.mkdir(parents=True, exist_ok=True)
    tep = ch.thu_muc_bao_loi / f"{ngay:%Y-%m-%d}_{ch.ten_may}_{kc.loai}.txt"
    tep.write_text(f"Máy: {ch.ten_may}\nKết cục: {kc.loai}\n\n" + "\n".join(kc.chi_tiet)
                   + "\n\nNạp tay: kéo thả file vào /kho-du-lieu, hoặc "
                     "python -m obc_bot nap --cau-hinh <máy>.toml <file>\n", encoding="utf-8")
    for a in kc.anh:
        if a.exists():
            shutil.copy2(a, ch.thu_muc_bao_loi / f"{tep.stem}_{a.name}")
    return tep


def thong_bao_windows(tieu_de: str, noi_dung: str) -> None:
    """Thông báo góc màn hình — cố gắng hết sức, không bao giờ làm hỏng lượt chạy."""
    ps = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
          "ContentType=WindowsRuntime] > $null;"
          "$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(1);"
          "$t = $x.GetElementsByTagName('text');"
          f"$t.Item(0).AppendChild($x.CreateTextNode({_ps(tieu_de)})) > $null;"
          f"$t.Item(1).AppendChild($x.CreateTextNode({_ps(noi_dung)})) > $null;"
          "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('KOME obc_bot')"
          ".Show([Windows.UI.Notifications.ToastNotification]::new($x))")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=15,
                       capture_output=True)
    except Exception:
        pass


def _ps(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"
```

`obc_bot/man_hinh.py`:

```python
"""Màn hình thật: đang khoá không, và chụp lại khi bấm hỏng."""
from pathlib import Path


def dang_khoa() -> bool:
    """Khoá / màn đăng nhập / ngủ = không mở được bàn làm việc nhận phím chuột."""
    import ctypes
    u = ctypes.windll.user32
    h = u.OpenInputDesktop(0, False, 0x0100)          # DESKTOP_SWITCHDESKTOP
    if not h:
        return True
    try:
        return not u.SwitchDesktop(h)
    finally:
        u.CloseDesktop(h)


def chup(duong: Path) -> Path | None:
    try:
        from PIL import ImageGrab
        duong.parent.mkdir(parents=True, exist_ok=True)
        ImageGrab.grab().save(duong)
        return duong
    except Exception:
        return None
```

`obc_bot/obc/__init__.py`:

```python
"""Nửa XUẤT — bấm 商奉行クラウド (pywinauto, backend uia).

Giao diện cố định cho chay.py: xuat(muc, ngay, thu_muc, pattern) -> Path đúng
tên `ten_file(muc, ngay)`; khoi_dong_lai() đóng hộp thoại lạ / mở lại OBC. Lỗi
nào cũng ném chay.LoiObc(bước, lỗi, ảnh chụp). Thân thật viết ở Task 7, SAU khi
có cây điều khiển đo thật (`python -m obc_bot do`)."""
from datetime import date
from pathlib import Path


def xuat(muc: str, ngay: date, thu_muc: Path, pattern: int) -> Path:
    from obc_bot.chay import LoiObc
    raise LoiObc("chưa viết", f"phần bấm OBC cho mục {muc!r} chưa có — xuất tay rồi dùng lệnh nap")


def khoi_dong_lai() -> None:
    return None
```

Trong `obc_bot/__main__.py`: thêm `"chay"` vào vòng `for ten in (...)` của `main`, nhánh `if a.lenh == "chay": return lenh_chay(ch)`, và hàm:

```python
def lenh_chay(ch: CH.CauHinh) -> int:
    import time
    from datetime import date
    from obc_bot import bao_cao, man_hinh, obc
    from obc_bot.chay import MoiTruong, chay
    mt = MoiTruong(man_hinh_khoa=man_hinh.dang_khoa, xuat=obc.xuat,
                   khoi_dong_lai_obc=obc.khoi_dong_lai, mat_khau=mat_khau_web,
                   thong_bao=bao_cao.thong_bao_windows, ngu=time.sleep)
    kc = chay(ch, KhachWeb(ch.web_url), mt)
    tep = bao_cao.ghi(ch, kc, date.today())
    bao_cao.thong_bao_windows(f"OBC → web: {kc.loai}",
                              (kc.chi_tiet[0] if kc.chi_tiet else "") + (f" — {tep}" if tep else ""))
    print(kc.loai)
    for d in kc.chi_tiet:
        print("  " + d)
    return 0 if kc.loai in ("xong", "bo_qua") else 1
```

(`date.today()` ở đây chỉ đặt tên log trên máy chạy — ngày dữ liệu luôn là ngày web trả.) Sửa docstring đầu `__main__.py` thêm dòng `chay   một lượt đầy đủ: kiểm -> xuất OBC -> nạp -> báo (Task Scheduler gọi lệnh này)`.

Trong `CLAUDE.md`, thêm ngay trước mục `## Hai bản chạy của web app`:

```markdown
**Bất biến (obc_bot, tự động lấy OBC — chủ DN chốt 2026-10-14):** `obc_bot/` bấm 商奉行クラウド (pywinauto, chọn
điều khiển theo TÊN) trên máy Windows có OBC rồi nạp qua `POST /api/kho-du-lieu/nap` bằng tài khoản web `obc-bot`
(cờ `duoc_vao_kho_du_lieu`) — KHÔNG ghi CSDL trực tiếp, KHÔNG ghi gì vào OBC; 5 cổng y như kéo thả tay (cùng thân
`_nap_mot_buoc` với `POST /upload`). Hai máy chia theo 権限 OBC: máy B `ban`+`ton`, máy Long `khach`. Ngày làm việc
và "đã có hôm nay" hỏi web (`GET /api/kho-du-lieu/hom-nay` = `tinh_tuoi`), không tự giữ lịch. `obc_bot/ten_file.py`
là bản chép của `files.yml` (test canh qua `pipeline.identify`; `MUC_SPEC` = `app.MUC_HANG_NGAY`). Mỗi lượt kết thúc
ở MỘT kết cục (`chay.KetCuc`); kết cục cần báo ghi tệp vào thư mục OneDrive dùng chung. Web không nhập `obc_bot`,
`obc_bot` không nhập `kome` (ngoài test); `.vercelignore` loại nó. Đặc tả: `docs/superpowers/specs/2026-10-14-tu-dong-lay-obc-design.md`.
```

Sau khi sửa `CLAUDE.md` chạy `python scripts/sinh_tai_lieu.py` nếu mục vừa thêm nằm trong "Bẫy đã biết" — KHÔNG, nó nằm ngoài mục đó, nên không cần; vẫn chạy `pytest tests/test_tai_lieu.py -v` để chắc.

- [ ] **Step 4: Chạy test, xác nhận qua**

Run: `pytest tests/test_obc_bot_chay.py tests/test_obc_bot_web.py tests/test_obc_bot_co_ban.py tests/test_nap_tu_dong.py tests/test_tai_lieu.py -v`
Expected: PASS hết.

Kiểm tay trên máy này: `python -c "from obc_bot import man_hinh; print(man_hinh.dang_khoa())"` → `False` khi đang ngồi máy.

- [ ] **Step 5: Commit**

```bash
git add obc_bot tests/test_obc_bot_chay.py CLAUDE.md
git commit -m "feat(obc_bot): bo dieu phoi chay — ket cuc, thu lai mot lan, bao loi OneDrive, kiem man hinh khoa"
```

---

### Task 6: Lệnh `do` — đo cây điều khiển 奉行クラウド thật (ĐIỂM DỪNG)

**Files:**
- Create: `obc_bot/obc/do.py`
- Modify: `obc_bot/__main__.py` (lệnh `do`)
- Create: `docs/obc-ui/*.txt` (kết quả đo, sau khi soát dữ liệu khách)

**Interfaces:**
- Produces: `obc_bot.obc.do.do_cay(tieu_de: str = ".*奉行クラウド.*", sau: int = 12) -> str`. CLI: `python -m obc_bot do --ra <file.txt> [--tieu-de REGEX] [--sau N]` (không cần `--cau-hinh`).

- [ ] **Step 1: Viết mã**

`obc_bot/obc/do.py`:

```python
"""In cây điều khiển UIA của cửa sổ 奉行クラウド đang mở — để viết Task 7 bằng
TÊN điều khiển đo thật, không đoán. Chỉ đọc: không bấm gì."""


def do_cay(tieu_de: str = ".*奉行クラウド.*", sau: int = 12) -> str:
    from pywinauto import Desktop
    goc = Desktop(backend="uia").window(title_re=tieu_de)
    goc.wait("exists", timeout=10)
    dong: list[str] = []

    def di(e, d):
        ei = e.element_info
        dong.append("  " * d + f"[{ei.control_type}] name={ei.name!r} "
                    f"auto_id={ei.automation_id!r} class={ei.class_name!r}")
        if d < sau:
            for c in e.children():
                di(c, d + 1)

    di(goc.wrapper_object(), 0)
    return "\n".join(dong)
```

Trong `obc_bot/__main__.py`, trong `main` trước vòng `for ten in (...)`:

```python
    s = sub.add_parser("do")
    s.add_argument("--ra", required=True, type=Path)
    s.add_argument("--tieu-de", default=".*奉行クラウド.*")
    s.add_argument("--sau", type=int, default=12)
```

và ngay sau `a = p.parse_args(argv)`:

```python
    if a.lenh == "do":
        from obc_bot.obc.do import do_cay
        a.ra.parent.mkdir(parents=True, exist_ok=True)
        a.ra.write_text(do_cay(a.tieu_de, a.sau), encoding="utf-8")
        print(f"Đã ghi {a.ra}")
        return 0
```

- [ ] **Step 2: Chạy thử với cửa sổ chính**

Mở 商奉行クラウド ở màn menu (như ảnh 2026-10-14), rồi:

Run: `python -m obc_bot do --ra docs/obc-ui/01_menu.txt`
Expected: file có dòng `[Window] name='奉行クラウド'` và các nút `売上明細表`, `得意先`, `取引単価`, `売上伝票` trên thanh công cụ. Không thấy chúng (chỉ một `[Pane]` trống) → DỪNG, báo chủ DN: UIA không đọc được, phải bàn lại cách nhận diện hình ảnh (đặc tả §4.1).

- [ ] **Step 3: Đo từng màn của luồng xuất (người mở màn, lệnh chỉ đọc)**

Mỗi màn chạy `python -m obc_bot do --ra docs/obc-ui/<tên>.txt` khi màn đó đang mở:

| File | Màn đang mở |
|---|---|
| `02_ban_dieu_kien.txt` | 売上明細表 — màn 条件 (chọn ngày, chọn 出力パターン) |
| `03_ban_xuat.txt` | hộp thoại xuất Excel / chọn nơi lưu của 売上明細表 |
| `04_ton_dieu_kien.txt` | 在庫一覧 — màn 条件 (ghi lại menu nào dẫn tới nó) |
| `05_ton_xuat.txt` | hộp thoại xuất / lưu của 在庫一覧 |
| `06_khach_dieu_kien.txt` | (máy Long) 得意先 — màn 条件 xuất 得意先全情報 |
| `07_khach_xuat.txt` | (máy Long) hộp thoại xuất / lưu |
| `08_hop_thoai_la.txt` | bất kỳ hộp thoại thông báo / xác nhận nào hiện ra trong luồng (nếu có) |

Ghi kèm vào `docs/obc-ui/LUONG.md` từng cú bấm người làm (menu nào → nút nào → ô nào), theo thứ tự.

- [ ] **Step 4: Soát dữ liệu khách trước khi commit**

Cây điều khiển của màn KẾT QUẢ (lưới phiếu, danh sách khách) chứa tên khách / số tiền thật. Chỉ đo màn điều kiện và hộp thoại; mở từng file `docs/obc-ui/*.txt`, xoá mọi dòng mang tên khách / mã khách / số tiền. Không chắc → không commit file đó, giữ ngoài git.

- [ ] **Step 5: Commit + ĐIỂM DỪNG**

```bash
git add obc_bot/obc/do.py obc_bot/__main__.py docs/obc-ui
git commit -m "feat(obc_bot): lenh do — do cay dieu khien UIA cua 奉行クラウド; ket qua do that cac man xuat"
```

DỪNG. Đưa `docs/obc-ui/LUONG.md` + các file đo cho người viết kế hoạch để viết Task 7 vào cuối file này.

---

### Task 7: Phần bấm từng màn — `obc_bot/obc/{phien,ban,ton,khach}.py` (VIẾT SAU TASK 6)

Task này KHÔNG viết sẵn được: tên điều khiển, thứ tự bấm, hộp thoại lưu file chỉ biết sau Task 6, và viết trước là đoán tên — đúng điều đặc tả §4.1 cấm. Ràng buộc đã cố định cho kế hoạch bổ sung:

- Giữ nguyên giao diện của Task 5: `obc_bot.obc.xuat(muc, ngay, thu_muc, pattern) -> Path` (file đúng `ten_file(muc, ngay)` trong `thu_muc`) và `obc_bot.obc.khoi_dong_lai()`; mọi lỗi ném `chay.LoiObc(buoc, loi, man_hinh.chup(...))` với `buoc` là tên bước đọc được ("mở 売上明細表", "chọn pattern 3", "lưu file").
- `phien.py`: tìm cửa sổ `.*奉行クラウド.*` (backend `uia`), về màn menu, đóng hộp thoại lạ đã đo ở `08_hop_thoai_la.txt`, thời hạn chờ mỗi điều khiển có tên hằng.
- `ban.py` / `ton.py` / `khach.py`: một hàm mỗi file, đi đúng `LUONG.md`; `売上明細表` đặt khoảng ngày = `ngay`..`ngay`; chọn 出力パターン theo SỐ `pattern`; lưu thẳng vào `thu_muc / ten_file(muc, ngay)` (ghi đè nếu đã có).
- Test tự động: không có (không có OBC trong CI). Kiểm tay: `python -m obc_bot chay --cau-hinh may_b.toml` một ngày thật; so file obc_bot xuất với file người xuất tay cùng ngày (cùng số dòng, cùng tổng `税抜純売上高`).
