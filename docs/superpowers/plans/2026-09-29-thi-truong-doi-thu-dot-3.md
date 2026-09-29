# Thị trường & đối thủ — Đợt 3 (liên kết nguồn Google Drive) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cạnh mỗi dòng giá đối thủ có nút mở nguồn gốc (thư mục Drive của tháng, tìm đúng tên file trong Drive, trang web
của bên) và giá sale nhập tay mang được một link bằng chứng — KHÔNG lưu ảnh.

**Architecture:** Migration 064 thêm `app.thu_muc_nguon` (một link thư mục Drive mỗi tháng), cột
`app.gia_doi_thu_tay.lien_ket_bang_chung`, và view `mart.nguon_quan_sat (nguon, id) → thang_lo, lien_ket_thu_muc, web_ben,
lien_ket_bang_chung` — ĐÚNG MỘT chỗ định nghĩa "tháng của dòng = tháng `data_date` của lô". Các câu đọc sẵn có
(`_SO_SANH`, `_HO_SO`, `_DUYET`) LEFT JOIN view đó (vẫn 1 lượt). Giao diện: một mô-đun thuần `doi_thu/nguon.ts` (link an toàn,
link tìm Drive) + một thành phần `doi_thu/NguonDong.tsx` dùng chung ở Duyệt / So sánh / Hồ sơ đối thủ.

**Tech Stack:** Postgres (Supabase), FastAPI, React/Vite/TS + TanStack Query, pytest, vitest.

**Spec:** `docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md` §11 (và §7 bước 4, §8 dòng Đợt 3, §10).

## Global Constraints

- KHÔNG lưu ảnh / file gốc trên web, KHÔNG gọi Google Drive API, KHÔNG đọc nội dung Drive (§10, §11).
- Chỉ nhận link `https://` (CHECK ở CSDL + kiểm ở máy chủ); giao diện chỉ vẽ link `https://` (kiểm lại lúc vẽ).
- Mọi liên kết ra ngoài: `target="_blank" rel="noopener noreferrer"` + `referrerPolicy="no-referrer"`.
- Tháng của một dòng nạp = tháng của `meta.ingest_batch.data_date` của lô — KHÔNG theo `ngay_nguon`.
- Không đổi `core`, bộ nạp, `config/files.yml`, mẫu gói; hoàn tác lô không đổi. `app.gia_doi_thu_tay` vẫn CHỈ THÊM.
- Mỗi lần ghi `app.thu_muc_nguon` thêm một dòng `app.doi_thu_nhat_ky` (`loai = 'thu_muc'`) trong CÙNG giao dịch.
- Mọi GET `/api/doi-thu/*` vẫn đúng số lượt hỏi cũ (1 + ảnh chụp); POST chỉ JSON; `ho_so()` của khách không đổi.
- Migration 064 chạy bằng `postgres` qua `python db/migrate.py` (không SQL Editor — bẫy RLS); 059–063 không sửa.
- Định dạng số qua `dinh_dang.ts`; `giuKhoang()` cho mọi đổi URL nội bộ; build `kome/web/spa` được commit.
- Sửa migration → chạy lại `python scripts/sinh_tai_lieu.py`; đổi cột đọc → `python scripts/sinh_cot_dung.py`.

---

### Task 1: Migration 064 + view nguồn

**Files:**
- Create: `db/migrations/064_lien_ket_nguon.sql`
- Test: `tests/test_doi_thu_bang.py` (thêm), `tests/test_mart_doi_thu.py` (thêm)
- Regenerate: `kome/web/tai_lieu_sinh.json` (`python scripts/sinh_tai_lieu.py`)

**Interfaces:**
- Produces: bảng `app.thu_muc_nguon(thang date PK, lien_ket text, sua_luc timestamptz, sua_boi bigint)`; cột
  `app.gia_doi_thu_tay.lien_ket_bang_chung text`; view `mart.nguon_quan_sat(nguon text, id bigint, thang_lo date,
  lien_ket_thu_muc text, web_ben text, lien_ket_bang_chung text)` — khoá `(nguon, id)` khớp `mart.gia_doi_thu_quan_sat`;
  `app.doi_thu_nhat_ky.loai` nhận thêm `'thu_muc'`.

- [ ] **Step 1: Write the failing tests**

`tests/test_doi_thu_bang.py` (thêm cuối file):

```python
def test_064_thu_muc_nguon_chi_nhan_mung_1_va_https(conn):
    conn.execute("INSERT INTO app.thu_muc_nguon (thang, lien_ket) VALUES ('2026-08-01', 'https://drive.google.com/x')")
    conn.commit()
    for thang, lk in [("2026-08-02", "https://drive.google.com/y"), ("2026-09-01", "http://drive.google.com/y"),
                      ("2026-09-01", "javascript:alert(1)")]:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("INSERT INTO app.thu_muc_nguon (thang, lien_ket) VALUES (%s, %s)", (thang, lk))
        conn.rollback()


def test_064_lien_ket_bang_chung_chi_https_va_bang_van_chi_them(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("""INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, trang_thai, loai_nguon,
                          lien_ket_bang_chung) VALUES ('THAK', 'ten:x|', 'x', 'het', 'chung_tu', 'ftp://a')""")
    conn.rollback()
    for quyen in ("UPDATE", "DELETE"):
        assert not conn.execute("SELECT has_table_privilege('kome_app', 'app.gia_doi_thu_tay', %s)", (quyen,)).fetchone()[0]


def test_064_nhat_ky_nhan_loai_thu_muc(conn):
    conn.execute("INSERT INTO app.doi_thu_nhat_ky (loai, doi_tuong) VALUES ('thu_muc', 'thang:2026-08')")
    conn.commit()
```

(`pytest`, `psycopg` đã được nhập ở đầu file — kiểm; thiếu thì thêm `import psycopg` / `import pytest`.)

`tests/test_mart_doi_thu.py` (thêm cuối file; `_hang`, `_qs` đã có trong file — `_qs` tạo lô với `data_date = ngay`):

```python
def test_nguon_quan_sat_thang_lo_theo_DATA_DATE_cua_lo_khong_theo_ngay_nguon(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 540, ngay=date(2026, 7, 20))          # lô data_date 2026-07-20
    conn.execute("UPDATE core.fact_gia_doi_thu SET ngay_nguon = '2026-06-30' WHERE id = %s", (fid,))
    conn.execute("INSERT INTO app.thu_muc_nguon (thang, lien_ket) VALUES ('2026-07-01', 'https://drive.google.com/t7')")
    conn.commit()
    r = conn.execute("""SELECT thang_lo, lien_ket_thu_muc, web_ben FROM mart.nguon_quan_sat
                        WHERE nguon = 'nap' AND id = %s""", (fid,)).fetchone()
    assert r == (date(2026, 7, 1), "https://drive.google.com/t7", "https://thak.jp/")


def test_nguon_quan_sat_gia_tay_mang_link_bang_chung(conn, batch):
    tid = conn.execute("""INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, gia_goc, don_vi_gia,
                            trang_thai, loai_nguon, lien_ket_bang_chung)
                          VALUES ('THAK', 'ten:x|', 'x', 500, 'kg', 'con', 'to_roi', 'https://drive.google.com/anh')
                          RETURNING id""").fetchone()[0]
    conn.commit()
    r = conn.execute("""SELECT thang_lo, lien_ket_thu_muc, lien_ket_bang_chung FROM mart.nguon_quan_sat
                        WHERE nguon = 'tay' AND id = %s""", (tid,)).fetchone()
    assert r == (None, None, "https://drive.google.com/anh")


def test_nguon_quan_sat_moi_quan_sat_dung_MOT_dong(conn, batch):
    _hang(conn, batch)
    for b, g in [("THAK", 540), ("HSC", 560)]:
        _qs(conn, batch, b, g)
    n_qs, n_ng = conn.execute("""SELECT (SELECT count(*) FROM mart.gia_doi_thu_quan_sat),
                                        (SELECT count(*) FROM mart.gia_doi_thu_quan_sat q
                                         JOIN mart.nguon_quan_sat n USING (nguon, id))""").fetchone()
    assert n_qs == n_ng == 2
```

(`date` đã nhập ở đầu file — kiểm.) Chạy `UPDATE core…` trong test là được: test chạy bằng vai trò của CSDL test,
không phải `kome_app`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest -q tests/test_doi_thu_bang.py tests/test_mart_doi_thu.py -k "064 or nguon_quan_sat"`
Expected: FAIL — `relation "app.thu_muc_nguon" does not exist` / `mart.nguon_quan_sat` does not exist.

- [ ] **Step 3: Write the migration**

`db/migrations/064_lien_ket_nguon.sql`:

```sql
-- 064 — Liên kết nguồn (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §11, Đợt 3).
-- Chủ DN chốt: KHÔNG lưu ảnh. File gốc nằm trên Google Drive dùng chung (Bang-gia-doi-thu/Tháng N/<bên>/);
-- web chỉ TRỎ tới: một link thư mục "Tháng N" mỗi tháng + link bằng chứng tuỳ chọn cho giá sale nhập.

CREATE TABLE app.thu_muc_nguon (
    thang     date PRIMARY KEY CHECK (extract(day FROM thang) = 1),
    lien_ket  text NOT NULL CHECK (lien_ket ~ '^https://[^[:space:]]+$' AND length(lien_ket) <= 2000),
    sua_luc   timestamptz NOT NULL DEFAULT now(),
    sua_boi   bigint REFERENCES app.nguoi_dung(id)
);
-- Sửa được (thay link sai) — KHÔNG chỉ-thêm; lịch sử nằm ở app.doi_thu_nhat_ky (loai 'thu_muc', cùng giao dịch).

ALTER TABLE app.gia_doi_thu_tay ADD COLUMN lien_ket_bang_chung text
    CHECK (lien_ket_bang_chung ~ '^https://[^[:space:]]+$' AND length(lien_ket_bang_chung) <= 2000);

ALTER TABLE app.doi_thu_nhat_ky DROP CONSTRAINT doi_thu_nhat_ky_loai_check;
ALTER TABLE app.doi_thu_nhat_ky ADD CONSTRAINT doi_thu_nhat_ky_loai_check
    CHECK (loai IN ('xac_nhan', 'sua', 'gia_moi', 'them', 'ghep', 'nhom', 'quy_cach', 'doi_thu', 'thu_muc'));

-- ĐÚNG MỘT chỗ định nghĩa nguồn của một quan sát (khoá (nguon, id) như mart.gia_doi_thu_quan_sat).
-- Tháng của dòng nạp = tháng của data_date của LÔ (gói tháng 8 dựng với --ngay 2026-08-31 → thư mục "Tháng 8"),
-- KHÔNG theo ngay_nguon (ngày trên từng file có thể là đầu tháng hay tháng trước).
CREATE VIEW mart.nguon_quan_sat AS
SELECT 'nap'::text AS nguon, f.id,
       date_trunc('month', b.data_date)::date AS thang_lo,
       tm.lien_ket                            AS lien_ket_thu_muc,
       d.web                                  AS web_ben,
       NULL::text                             AS lien_ket_bang_chung
FROM core.fact_gia_doi_thu f
JOIN meta.ingest_batch b ON b.batch_id = f.batch_id
LEFT JOIN app.thu_muc_nguon tm ON tm.thang = date_trunc('month', b.data_date)::date
LEFT JOIN app.doi_thu d ON d.ma = f.ma_doi_thu
UNION ALL
SELECT 'tay'::text, t.id, NULL::date, NULL::text, d.web, t.lien_ket_bang_chung
FROM app.gia_doi_thu_tay t
LEFT JOIN app.doi_thu d ON d.ma = t.ma_doi_thu;
```

(Quyền: `ALTER DEFAULT PRIVILEGES` của 009 cấp SELECT view `mart` và quyền `app` cho đúng vai trò — migration chạy bằng
`postgres`. Kiểm `pg_class.relrowsecurity` bằng test sẵn có `test_khong_bang_nao_bat_RLS`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q tests/test_doi_thu_bang.py tests/test_mart_doi_thu.py`
Expected: PASS (cả test cũ).

- [ ] **Step 5: Regenerate the docs snapshot and commit**

Run: `python scripts/sinh_tai_lieu.py && pytest -q tests/test_tai_lieu.py`
Expected: PASS.

```bash
git add db/migrations/064_lien_ket_nguon.sql tests/test_doi_thu_bang.py tests/test_mart_doi_thu.py kome/web/tai_lieu_sinh.json
git commit -m "feat(doi-thu): 064 — thu_muc_nguon, lien_ket_bang_chung, mart.nguon_quan_sat"
```

---

### Task 2: Máy chủ — ghi link, trả nguồn trong các câu đọc

**Files:**
- Modify: `kome/doi_thu.py` (`_COT_QS` + ba câu `_SO_SANH` / `_HO_SO` / `_DUYET`, `gia_moi`, hàm mới `kiem_lien_ket`,
  `dat_thu_muc`)
- Modify: `kome/web/api.py` (route `POST /api/doi-thu/thu-muc`)
- Modify: `kome/nhat_ky.py:106` (nhãn `"thu_muc"`)
- Test: `tests/test_doi_thu.py`, `tests/test_doi_thu_api.py` (thêm)
- Regenerate: `kome/web/cot_dung_sinh.json` (`python scripts/sinh_cot_dung.py`)

**Interfaces:**
- Consumes: Task 1 (`mart.nguon_quan_sat`, `app.thu_muc_nguon`, cột `lien_ket_bang_chung`, loai `'thu_muc'`).
- Produces:
  - `kiem_lien_ket(v, ten: str) -> str | None` — `None`/`""` → `None`; khác `str`, không `https://`, có khoảng trắng /
    ký tự điều khiển / surrogate, dài > 2000 → `LoiNhap`.
  - `dat_thu_muc(conn, thang: str, lien_ket: str, nguoi) -> None` — `thang` dạng `YYYY-MM`; upsert + nhật ký
    (`loai 'thu_muc'`, `doi_tuong 'thang:YYYY-MM'`, `truoc {lien_ket cũ}` / `sau {lien_ket mới}`).
  - `gia_moi(...)` nhận thêm khoá tuỳ chọn `lien_ket_bang_chung`.
  - Mọi quan sát trong JSON của `so_sanh`, `ho_so_ben().quan_sat`, `duyet` có thêm 4 khoá: `thang_lo` (`"YYYY-MM-DD"` |
    null), `lien_ket_thu_muc`, `web_ben`, `lien_ket_bang_chung` (chuỗi | null).
  - `POST /api/doi-thu/thu-muc` body `{"thang": "2026-08", "lien_ket": "https://…"}` → `{"ok": true}`; lỗi nhập 400
    `{"loi": …}`; không JSON 415.

- [ ] **Step 1: Write the failing tests**

`tests/test_doi_thu.py` (thêm cuối file; `_hang`, `_qs` nhập từ `tests.test_mart_doi_thu` như các test khác trong file):

```python
@pytest.mark.parametrize("lk", ["http://drive.google.com/x", "javascript:alert(1)", "https://a b", "https://x\n",
                                 "https://\ud800", 5, ["https://x"], "https://" + "a" * 2000])
def test_kiem_lien_ket_tu_choi_dang_sai(lk):
    from kome import doi_thu as DT
    with pytest.raises(DT.LoiNhap):
        DT.kiem_lien_ket(lk, "Link")


def test_kiem_lien_ket_rong_la_None_va_https_giu_nguyen():
    from kome import doi_thu as DT
    assert DT.kiem_lien_ket(None, "Link") is None and DT.kiem_lien_ket("", "Link") is None
    assert DT.kiem_lien_ket("https://drive.google.com/x?id=1", "Link") == "https://drive.google.com/x?id=1"


def test_dat_thu_muc_upsert_va_ghi_nhat_ky(conn):
    from kome import doi_thu as DT
    DT.dat_thu_muc(conn, "2026-08", "https://drive.google.com/a", None)
    DT.dat_thu_muc(conn, "2026-08", "https://drive.google.com/b", None)
    conn.commit()
    assert conn.execute("SELECT thang::text, lien_ket FROM app.thu_muc_nguon").fetchall() == [("2026-08-01", "https://drive.google.com/b")]
    nk = conn.execute("SELECT truoc, sau FROM app.doi_thu_nhat_ky WHERE loai = 'thu_muc' ORDER BY id").fetchall()
    assert nk == [(None, {"lien_ket": "https://drive.google.com/a"}),
                  ({"lien_ket": "https://drive.google.com/a"}, {"lien_ket": "https://drive.google.com/b"})]


@pytest.mark.parametrize("thang", ["2026-13", "2026-8", "08-2026", "", None, 202608])
def test_dat_thu_muc_thang_sai_dang(conn, thang):
    from kome import doi_thu as DT
    with pytest.raises(DT.LoiNhap):
        DT.dat_thu_muc(conn, thang, "https://drive.google.com/a", None)


def test_gia_moi_luu_link_bang_chung_va_tu_choi_link_sai(conn, batch):
    from kome import doi_thu as DT
    from tests.test_mart_doi_thu import _hang, _qs
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 540)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi",
                            "lien_ket_bang_chung": "https://drive.google.com/anh"}, None)
    conn.commit()
    assert conn.execute("SELECT lien_ket_bang_chung FROM app.gia_doi_thu_tay WHERE id = %s", (tid,)).fetchone()[0] \
        == "https://drive.google.com/anh"
    with pytest.raises(DT.LoiNhap):
        DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi",
                          "lien_ket_bang_chung": "javascript:x"}, None)


def test_cac_cau_doc_mang_4_khoa_nguon(conn, batch):
    from kome import doi_thu as DT
    from tests.test_mart_doi_thu import _hang, _qs
    _hang(conn, batch)
    for b, g in [("THAK", 540), ("HSC", 560), ("JVB", 580)]:
        _qs(conn, batch, b, g)                                            # lô data_date 2026-07-20
    DT.dat_thu_muc(conn, "2026-07", "https://drive.google.com/t7", None)
    conn.commit()
    qs = DT.so_sanh(conn)["nhom"][0]["quan_sat"] + DT.duyet(conn)["dong"] + DT.ho_so_ben(conn, "THAK")["quan_sat"]
    assert qs and all({"thang_lo", "lien_ket_thu_muc", "web_ben", "lien_ket_bang_chung"} <= set(q) for q in qs)
    thak = [q for q in DT.duyet(conn)["dong"] if q["ma_doi_thu"] == "THAK"][0]
    assert (thak["thang_lo"], thak["lien_ket_thu_muc"], thak["web_ben"]) == ("2026-07-01", "https://drive.google.com/t7",
                                                                             "https://thak.jp/")
```

`tests/test_doi_thu_api.py` (thêm cuối file; `_web`, `_nen` đã có trong file):

```python
def test_post_thu_muc_ghi_va_phien_ban_doi(conn, batch, test_db_url):
    _nen(conn, batch)
    c = _web(test_db_url)
    r = c.post("/api/doi-thu/thu-muc", json={"thang": "2026-07", "lien_ket": "https://drive.google.com/t7"})
    assert r.status_code == 200 and r.json()["ok"] is True
    dong = c.get("/api/doi-thu/duyet").json()["dong"]
    assert all(d["lien_ket_thu_muc"] == "https://drive.google.com/t7" for d in dong if d["nguon"] == "nap")


@pytest.mark.parametrize("than", [{"thang": "2026-07", "lien_ket": "javascript:x"}, {"thang": "2026-7", "lien_ket": "https://a"},
                                  {"lien_ket": "https://a"}, {"thang": "2026-07"}])
def test_post_thu_muc_sai_tra_400(conn, batch, test_db_url, than):
    c = _web(test_db_url)
    r = c.post("/api/doi-thu/thu-muc", json=than)
    assert r.status_code == 400 and "loi" in r.json()


def test_post_thu_muc_chi_nhan_json(test_db_url):
    c = _web(test_db_url)
    assert c.post("/api/doi-thu/thu-muc", data="thang=2026-07").status_code == 415


def test_nhat_ky_thao_tac_co_dong_dan_link_thu_muc(conn, batch):
    from kome import doi_thu as DT, nhat_ky as NK
    DT.dat_thu_muc(conn, "2026-07", "https://drive.google.com/t7", None)
    conn.commit()
    assert any(d.loai == "doi_thu" and "thư mục" in str(vars(d)).lower() for d in NK.dong_thoi_gian(conn))
```

Test đếm lượt hỏi sẵn có (`test_ngan_sach_luot_hoi`, tham số hoá theo URL) phải vẫn xanh KHÔNG sửa — đó là bằng chứng
"vẫn 1 lượt". Nếu `test_nhat_ky_…` không khớp cách `NK.dong_thoi_gian` trả nhãn, đọc `kome/nhat_ky.py:95-110` và khẳng
định trên đúng trường chứa nhãn hành động (nhãn phải chứa chữ "thư mục").

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest -q tests/test_doi_thu.py tests/test_doi_thu_api.py -k "lien_ket or thu_muc or 4_khoa"`
Expected: FAIL — `AttributeError: module 'kome.doi_thu' has no attribute 'kiem_lien_ket'` / 404 cho route mới.

- [ ] **Step 3: Implement**

`kome/doi_thu.py` — gần các hằng kiểm khác (sau `KHOA_NHOM`):

```python
LIEN_KET_TOI_DA = 2000
_LIEN_KET = re.compile(r"https://[^\s\x00-\x1f\x7f\ud800-\udfff]+")
_THANG = re.compile(r"(\d{4})-(0[1-9]|1[0-2])")


def kiem_lien_ket(v, ten: str):
    """Link ra ngoài (Drive, ảnh bằng chứng): rỗng → None; chỉ https://, không khoảng trắng / ký tự điều khiển /
    surrogate lẻ, ≤ LIEN_KET_TOI_DA. CHECK của 064 chặn lần nữa ở CSDL; giao diện kiểm lại lúc vẽ."""
    if v is None or v == "":
        return None
    if not isinstance(v, str) or len(v) > LIEN_KET_TOI_DA or not _LIEN_KET.fullmatch(v):
        raise LoiNhap(f"{ten} phải là một link https:// (dán nguyên link Google Drive).")
    return v


def dat_thu_muc(conn, thang, lien_ket, nguoi) -> None:
    """Link thư mục Drive "Tháng N" (đặc tả §11). Sửa được; mỗi lần ghi thêm một dòng nhật ký trong CÙNG giao dịch."""
    if not isinstance(thang, str) or not _THANG.fullmatch(thang):
        raise LoiNhap("Tháng phải có dạng YYYY-MM.")
    lk = kiem_lien_ket(lien_ket, "Link thư mục")
    if lk is None:
        raise LoiNhap("Dán link thư mục Google Drive của tháng.")
    ngay = f"{thang}-01"
    cu = conn.execute("SELECT lien_ket FROM app.thu_muc_nguon WHERE thang = %s", (ngay,)).fetchone()
    conn.execute("""INSERT INTO app.thu_muc_nguon (thang, lien_ket, sua_luc, sua_boi) VALUES (%s, %s, now(), %s)
                    ON CONFLICT (thang) DO UPDATE SET lien_ket = EXCLUDED.lien_ket, sua_luc = now(),
                      sua_boi = EXCLUDED.sua_boi""", (ngay, lk, nguoi))
    _ghi_nhat_ky(conn, "thu_muc", f"thang:{thang}", {"lien_ket": cu[0]} if cu else None, {"lien_ket": lk}, nguoi)
```

`gia_moi` — kiểm link TRƯỚC khi ghi, rồi đưa vào INSERT:

```python
    lk = kiem_lien_ket(du_lieu.get("lien_ket_bang_chung"), "Link bằng chứng")
```

đặt ngay sau khối kiểm `ln` (loại nguồn); thêm cột `lien_ket_bang_chung` vào danh sách cột + `%(lien_ket_bang_chung)s`
vào VALUES của câu `INSERT INTO app.gia_doi_thu_tay`, và `"lien_ket_bang_chung": lk` vào dict tham số. Nhật ký ghi
`v | {"loai_nguon": ln, "lien_ket_bang_chung": lk}`.

Câu đọc — thêm 4 cột vào `_COT_QS`:

```python
_COT_QS = """ma_doi_thu, ten_doi_thu, nguon, id, ma_hang_dt, ngay_nguon, hinh_thuc_nguon, nguon_file, vi_tri,
             ten_goc, quy_cach_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, kenh_gia, muc_gia,
             gia_bac, gia_truoc_km, trang_thai, khuyen_mai, loai_nguon, ghi_chu, ma_kome, nhan, nhom_khoa,
             ten_nhom, trang_thai_duyet, round(yen_chuan) AS yen_chuan, don_vi_so, nen_gia, tuoi_ngay, bat_thuong,
             thang_lo, lien_ket_thu_muc, web_ben, lien_ket_bang_chung"""
```

và ở MỖI chỗ dùng `_COT_QS` đổi nguồn `FROM` sang JOIN view nguồn (cột `nguon`, `id` gộp bằng `USING`, nên tên không
trùng):
- `_SO_SANH`: `FROM mart.gia_doi_thu_hien_hanh LEFT JOIN mart.nguon_quan_sat USING (nguon, id) WHERE nhom_khoa IS NOT NULL`
- `_HO_SO`: `FROM mart.gia_doi_thu_quan_sat LEFT JOIN mart.nguon_quan_sat USING (nguon, id) WHERE ma_doi_thu = %(ma)s`
  (giữ `.replace(', bat_thuong', '')` — `bat_thuong` đứng TRƯỚC 4 cột mới nên phép replace vẫn đúng; kiểm lại bằng test)
- `_DUYET`: `FROM mart.gia_doi_thu_hien_hanh h LEFT JOIN mart.nguon_quan_sat USING (nguon, id)` — các tham chiếu
  `h.ma_doi_thu`, `h.ma_hang_dt` trong `NOT EXISTS` vẫn đúng.

`kome/web/api.py` — cạnh `dt_gia_moi`:

```python
    @r.post("/doi-thu/thu-muc")
    async def dt_thu_muc(request: Request):
        from kome import doi_thu as DT
        return await _dt_ghi(request, lambda c, b, n: DT.dat_thu_muc(c, b.get("thang"), b.get("lien_ket"), n))
```

`kome/nhat_ky.py:106` — thêm vào bảng nhãn: `"thu_muc": "Dán link thư mục Drive"`.

Chạy `python scripts/sinh_cot_dung.py` (doi_thu.py nay đọc `mart.nguon_quan_sat`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q tests/test_doi_thu.py tests/test_doi_thu_api.py tests/test_mart_doi_thu.py tests/test_lien_he.py tests/test_nhat_ky.py tests/test_cot_dung.py tests/test_tai_lieu.py`
Expected: PASS (gồm `test_ngan_sach_luot_hoi` không sửa).

- [ ] **Step 5: Commit**

```bash
git add kome/doi_thu.py kome/web/api.py kome/nhat_ky.py kome/web/cot_dung_sinh.json tests/test_doi_thu.py tests/test_doi_thu_api.py
git commit -m "feat(doi-thu): dot 3 — link thu muc Drive theo thang, link bang chung, cau doc mang nguon"
```

---

### Task 3: Giao diện — nút nguồn, ô link thư mục, ô link bằng chứng

**Files:**
- Create: `giao_dien/src/doi_thu/nguon.ts`, `giao_dien/src/doi_thu/nguon.test.ts`, `giao_dien/src/doi_thu/NguonDong.tsx`
- Modify: `giao_dien/src/doi_thu/kieu.ts` (kiểu quan sát: 4 khoá mới), `TabDuyet.tsx` (đầu tab + dòng chọn + hai form),
  `TabSoSanh.tsx` (ô nổi dòng chi tiết, `:95`), `TabHoSo.tsx` (bảng mặt hàng)
- Build: `cd giao_dien && npm run build` (commit `kome/web/spa`)

**Interfaces:**
- Consumes: Task 2 JSON — mỗi quan sát có `thang_lo: string | null` (`"YYYY-MM-DD"`), `lien_ket_thu_muc`, `web_ben`,
  `lien_ket_bang_chung: string | null`, và sẵn có `nguon: "nap" | "tay"`, `hinh_thuc_nguon: "file" | "web" | null`,
  `nguon_file`, `vi_tri`, `loai_nguon`. `POST /api/doi-thu/thu-muc {thang: "YYYY-MM", lien_ket}`;
  `POST /api/doi-thu/gia-moi` nhận thêm `lien_ket_bang_chung`.
- Produces: `nguon.ts` — `lienKetAnToan(u: unknown): string | null`, `timTrongDrive(tenFile: string): string`,
  `thangCua(thangLo: string | null): string | null` (`"2026-08-01"` → `"2026-08"`), `nhanThang(t: string): string`
  (`"2026-08"` → `"Tháng 8/2026"`), `CAN_BANG_CHUNG: readonly string[]` (= `["chung_tu", "to_roi"]`),
  `cacThangCho(dong: {thang_lo: string | null}[]): string[]` (tháng khác nhau, mới trước, bỏ null).
  `NguonDong.tsx` — `<NguonDong q={quanSat} />` vẽ các nút của MỘT quan sát.

- [ ] **Step 1: Write the failing tests** — `giao_dien/src/doi_thu/nguon.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { CAN_BANG_CHUNG, cacThangCho, lienKetAnToan, nhanThang, thangCua, timTrongDrive } from "./nguon";

describe("lienKetAnToan", () => {
  it("chỉ nhận https://", () => {
    expect(lienKetAnToan("https://drive.google.com/x")).toBe("https://drive.google.com/x");
    for (const x of ["http://a", "javascript:alert(1)", " https://a", "https://a b", "", null, undefined, 5, "HTTPS://a"])
      expect(lienKetAnToan(x)).toBeNull();
  });
});

describe("timTrongDrive", () => {
  it("mã hoá tên file vào ô tìm của Drive", () => {
    expect(timTrongDrive("MENU HANG KHO 82026.pdf"))
      .toBe("https://drive.google.com/drive/search?q=" + encodeURIComponent("MENU HANG KHO 82026.pdf"));
    expect(timTrongDrive("a&b#c.pdf")).toContain("a%26b%23c.pdf");
  });
});

describe("tháng", () => {
  it("thangCua / nhanThang", () => {
    expect(thangCua("2026-08-01")).toBe("2026-08");
    expect(thangCua(null)).toBeNull();
    expect(nhanThang("2026-08")).toBe("Tháng 8/2026");
  });
  it("cacThangCho: khác nhau, mới trước, bỏ null", () => {
    expect(cacThangCho([{ thang_lo: "2026-07-01" }, { thang_lo: null }, { thang_lo: "2026-08-01" }, { thang_lo: "2026-07-01" }]))
      .toEqual(["2026-08", "2026-07"]);
  });
  it("loại nguồn cần bằng chứng", () => {
    expect([...CAN_BANG_CHUNG]).toEqual(["chung_tu", "to_roi"]);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd giao_dien && npx vitest run src/doi_thu/nguon.test.ts`
Expected: FAIL — cannot resolve `./nguon`.

- [ ] **Step 3: Implement `nguon.ts`**

```ts
// Liên kết nguồn (đặc tả §11): web KHÔNG lưu ảnh, chỉ trỏ sang Google Drive / trang của bên.
// Máy chủ đã chặn link không https:// lúc ghi; kiểm LẠI lúc vẽ (dữ liệu cũ / sửa tay không được mở `javascript:`).

export const CAN_BANG_CHUNG = ["chung_tu", "to_roi"] as const;

export function lienKetAnToan(u: unknown): string | null {
  return typeof u === "string" && /^https:\/\/\S+$/.test(u) ? u : null;
}

export function timTrongDrive(tenFile: string): string {
  return "https://drive.google.com/drive/search?q=" + encodeURIComponent(tenFile);
}

export function thangCua(thangLo: string | null): string | null {
  return thangLo ? thangLo.slice(0, 7) : null;
}

export function nhanThang(t: string): string {
  const [y, m] = t.split("-");
  return `Tháng ${Number(m)}/${y}`;
}

export function cacThangCho(dong: { thang_lo: string | null }[]): string[] {
  const s = new Set<string>();
  for (const d of dong) { const t = thangCua(d.thang_lo); if (t) s.add(t); }
  return [...s].sort().reverse();
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd giao_dien && npx vitest run src/doi_thu/nguon.test.ts`
Expected: PASS.

- [ ] **Step 5: `kieu.ts` + `NguonDong.tsx`**

`kieu.ts` — thêm vào kiểu quan sát (tên kiểu đang dùng cho một dòng quan sát trong file đó):

```ts
  thang_lo: string | null;
  lien_ket_thu_muc: string | null;
  web_ben: string | null;
  lien_ket_bang_chung: string | null;
```

`NguonDong.tsx`:

```tsx
import { CAN_BANG_CHUNG, lienKetAnToan, nhanThang, thangCua, timTrongDrive } from "./nguon";
import type { QuanSat } from "./kieu";   // dùng đúng tên kiểu quan sát có trong kieu.ts

function Ra({ href, children }: { href: string; children: React.ReactNode }) {
  return <a className="chip" href={href} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">{children}</a>;
}

/** Các nút mở nguồn của MỘT quan sát (đặc tả §11.2). */
export function NguonDong({ q }: { q: QuanSat }) {
  const thuMuc = lienKetAnToan(q.lien_ket_thu_muc);
  const web = lienKetAnToan(q.web_ben);
  const bangChung = lienKetAnToan(q.lien_ket_bang_chung);
  const t = thangCua(q.thang_lo);
  return (
    <span className="dt-nguon">
      {q.nguon === "nap" && q.hinh_thuc_nguon === "file" && q.nguon_file && <>
        {thuMuc && <Ra href={thuMuc}>Mở thư mục {t ? nhanThang(t).toLowerCase() : "tháng"} ↗</Ra>}
        <Ra href={timTrongDrive(q.nguon_file)}>Tìm file trong Drive ↗</Ra>
      </>}
      {q.nguon === "nap" && q.hinh_thuc_nguon === "web" && web && <Ra href={web}>Mở trang của bên ↗</Ra>}
      {q.nguon === "tay" && (bangChung
        ? <Ra href={bangChung}>bằng chứng ↗</Ra>
        : (CAN_BANG_CHUNG as readonly string[]).includes(q.loai_nguon ?? "") && <span className="dt-nhat">chưa có bằng chứng</span>)}
    </span>
  );
}
```

(`.chip`, `.dt-nhat` là lớp sẵn có của màn. Nếu `hinh_thuc_nguon` của dòng `tay` trong JSON không phải `null`, chỉ
dựa vào `q.nguon`.)

- [ ] **Step 6: Tab Duyệt**

- Đầu tab (trên bảng): với mỗi `t` trong `cacThangCho(dong)` một dòng "Thư mục Drive {nhanThang(t)}:"; tháng đã có
  link (lấy `lien_ket_thu_muc` của một dòng bất kỳ có `thangCua(thang_lo) === t`, qua `lienKetAnToan`) → `<Ra>` "Mở thư
  mục ↗" + nút "đổi"; chưa có hoặc đang đổi → `<input type="url" aria-label="Link thư mục Drive {nhanThang(t)}"
  placeholder="https://drive.google.com/…">` + nút "Lưu" gọi `gui("/api/doi-thu/thu-muc", {thang: t, lien_ket})` rồi
  `qc.invalidateQueries({queryKey: ["doi-thu"]})`; lỗi 400 hiện câu `loi` cạnh ô (cùng nếp `datLoiThem`).
- Dòng đang chọn (`TabDuyet.tsx:106`): sau câu "Nguồn: …" vẽ `<NguonDong q={chon} />`.
- Form "Giá đã đổi" (`:123-129`) và form "Thêm hàng AI bỏ sót" (`HANG_MOI_TRONG`, `:25`, `:82-90`): thêm
  `lien_ket_bang_chung: ""` vào state và một ô `<input type="url" aria-label="Link bằng chứng"
  placeholder="Link bằng chứng (tuỳ chọn) — ảnh trên Drive">`; gửi kèm trong body (chuỗi rỗng máy chủ coi là không có).

- [ ] **Step 7: So sánh + Hồ sơ đối thủ**

- `TabSoSanh.tsx:95`: trong nội dung ô nổi, sau dòng "Nguồn: …" thêm `<br /><NguonDong q={x} />`.
- `TabHoSo.tsx`, bảng mặt hàng: thêm `<NguonDong q={…} />` vào ô nguồn / cuối dòng của mỗi quan sát.

- [ ] **Step 8: Verify and build**

Run: `cd giao_dien && npx vitest run && npx tsc -b && npm run build`
Then: `pytest -q tests/test_api.py tests/test_doi_thu_api.py`
Expected: PASS (gồm `test_ban_build_khop_ma_nguon`).

- [ ] **Step 9: Commit**

```bash
git add giao_dien/src/doi_thu kome/web/spa
git commit -m "feat(doi-thu): dot 3 — nut mo nguon (thu muc thang, tim file Drive, web ben), o link bang chung"
```

---

### Task 4: Tài liệu + toàn bộ test

**Files:**
- Modify: `CLAUDE.md` (đoạn bất biến mới ngay sau đoạn 063), `docs/doi-thu/huong-dan-doc.md` (bước dán link thư mục)

- [ ] **Step 1: CLAUDE.md** — thêm sau đoạn "**Bất biến (063, …)**":

```markdown
**Bất biến (064, liên kết nguồn — chủ DN chốt 2026-09-29):** web KHÔNG lưu ảnh / file gốc và không gọi Google Drive API —
file gốc nằm trên Drive dùng chung (`Bang-gia-doi-thu/Tháng N/<bên>/`), web chỉ TRỎ tới. Một link thư mục mỗi tháng
(`app.thu_muc_nguon`, sửa được, mỗi lần ghi một dòng `app.doi_thu_nhat_ky` loai `thu_muc` cùng giao dịch); link bằng chứng
tuỳ chọn ở `app.gia_doi_thu_tay.lien_ket_bang_chung` (bảng vẫn chỉ thêm). Tháng của một dòng nạp = tháng `data_date` của
LÔ, định nghĩa ĐÚNG MỘT LẦN ở `mart.nguon_quan_sat` (khoá `(nguon, id)`), KHÔNG theo `ngay_nguon`. Chỉ `https://` (CHECK
ở CSDL + `doi_thu.kiem_lien_ket` + `doi_thu/nguon.ts::lienKetAnToan` lúc vẽ); mọi link ra ngoài `rel="noopener
noreferrer"` + `referrerPolicy="no-referrer"`. Nút "Tìm file trong Drive" dựng ở trình duyệt từ TÊN file. Có test canh:
`tests/test_doi_thu_bang.py`, `tests/test_mart_doi_thu.py`, `tests/test_doi_thu.py`, `giao_dien/src/doi_thu/nguon.test.ts`.
**Migration 064 phải chạy TRƯỚC khi triển khai.**
```

- [ ] **Step 2: `docs/doi-thu/huong-dan-doc.md`** — trong phần quy trình hằng tháng / sau khi nạp, thêm một dòng:
  "Sau khi nạp: mở `/doi-thu` › Duyệt / sửa, dán link thư mục Google Drive 'Tháng N' ở đầu tab (một lần mỗi tháng)."

- [ ] **Step 3: Full test runs**

Run: `python scripts/sinh_tai_lieu.py && pytest -q` then `cd giao_dien && npx vitest run`
Expected: tất cả PASS.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/doi-thu/huong-dan-doc.md kome/web/tai_lieu_sinh.json
git commit -m "docs(doi-thu): dot 3 — bat bien 064, huong dan dan link thu muc thang"
```
