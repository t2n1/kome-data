# Gộp mức giá theo mặt hàng + ẩn mặt hàng đối thủ — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mỗi mặt hàng đối thủ (bên + mã hàng) tính MỘT lần trong so sánh (giá đại diện = rẻ nhất cho khách thường), các
mức giá của nó gộp thành một dòng trong bảng sửa; thêm ẩn / khôi phục và gộp tay mặt hàng.

**Architecture:** Migration 070 thêm hai sổ chỉ-thêm (`app.an_quan_sat`, `app.gop_mat_hang`) và dựng lại ba view
(`mart.gia_doi_thu_quan_sat` +`an`/`mat_hang_khoa`/`an_hien_hanh`; `mart.gia_doi_thu_hien_hanh` +`dai_dien`/
`gia_pallet_mh`/`so_muc`, trung vị theo mặt hàng; `mart.so_sanh_nhom` chỉ đọc dòng đại diện). Máy chủ thêm hai đường ghi
(ẩn, gộp) theo nếp 409 + nhật ký của `/doi-thu`. Giao diện: MỘT chỗ `veDuoc` đọc `dai_dien`; bảng sửa nhóm dòng theo
mặt hàng, có 🗑 / Khôi phục / Gộp vào….

**Tech Stack:** Postgres 17 (mart views, SQL), Python 3 / FastAPI / psycopg (`kome/doi_thu.py`, `kome/web/api.py`),
React 18 + TS + TanStack Query + vitest (`giao_dien/src/doi_thu/`).

**Spec:** `docs/superpowers/specs/2026-09-30-doi-thu-gop-mat-hang-design.md` (đọc TRƯỚC — nó là trọng tài).
Nền: `docs/superpowers/specs/2026-09-30-doi-thu-bang-sua-design.md`, `CLAUDE.md` (mục "Bất biến (065–068…)" và
"Bất biến (Màn mới, đợt 4b…)").

## Global Constraints

- Migration đã chạy (≤ 069) KHÔNG sửa; chỉ thêm `db/migrations/070_doi_thu_mat_hang_an.sql`. Migration chạy bằng vai trò
  `postgres` (test tự dựng schema từ `db/migrations/`).
- OBC / `core.*` CHỈ ĐỌC. Không UPDATE / DELETE `core.fact_gia_doi_thu`. Hai sổ mới CHỈ THÊM: `REVOKE UPDATE, DELETE`
  khỏi `kome_app` (nếp 030 / 063).
- Mỗi đường ghi mới: `kiem_xung_dot` ĐẦU hàm, cùng giao dịch; ghi `app.doi_thu_nhat_ky` cùng giao dịch (khoá `gia:<id>` /
  `tay:<id>` cho ẩn, `<bên>/<hàng>` cho gộp). Không thêm bảng vào `anh_chup._PHIEN_BAN` (nhật ký làm phiên bản đổi).
- Một view mart tham chiếu > 1 lần trong một câu → CTE `AS MATERIALIZED` ghi tường minh.
- "Mức cho khách thường" viết ĐÚNG MỘT LẦN: `mart.la_muc_khach_thuong(muc_gia)` = `muc_gia IS NULL OR muc_gia = 'dac_biet'`.
- Mọi GET `/api/doi-thu/*` vẫn 1 lượt hỏi (+ phiên bản) — có test đếm (`tests/test_doi_thu_api.py`, `tests/test_doi_thu.py`).
- NULL ≠ 0; tỷ số là tỷ số các tổng. Không tự quy đổi giá ở trình duyệt (chỉ CHỌN cột máy chủ trả).
- Sửa `giao_dien/` ⇒ `cd giao_dien && npm run build` (bản build commit ở `kome/web/spa/`, test
  `tests/test_api.py::test_ban_build_khop_ma_nguon`). Sửa migration ⇒ `python scripts/sinh_tai_lieu.py` và
  `python scripts/sinh_cot_dung.py` (test `tests/test_tai_lieu.py`, `tests/test_cot_dung.py`).
- CSDL test `DATABASE_URL_TEST` (Postgres 17 localhost) DÙNG CHUNG với phiên khác — chạy pytest theo file / theo `-k`,
  không kill giữa chừng. Cả bộ ~9 phút.
- Chữ trên màn: tiếng Việt, số theo `giao_dien/src/dinh_dang.ts`.

## File Structure

| File | Việc |
|---|---|
| `db/migrations/070_doi_thu_mat_hang_an.sql` (mới) | hai sổ + hàm `la_muc_khach_thuong` + ba view dựng lại + GRANT/REVOKE |
| `kome/doi_thu.py` | `_COT_QS` thêm cột; `dat_an`, `gop_mat_hang`; `duyet` lọc `da_xoa` + thứ tự; `tong_quan` so_dong theo mặt hàng |
| `kome/web/api.py` | `POST /api/doi-thu/an`, `POST /api/doi-thu/gop-mat-hang` |
| `tests/test_mart_doi_thu.py`, `tests/test_doi_thu.py`, `tests/test_doi_thu_api.py` | test mart / hàm / route |
| `giao_dien/src/doi_thu/kieu.ts` | kiểu `QuanSat` thêm cột; `NHAN_MUC` |
| `giao_dien/src/doi_thu/so_sanh_logic.ts` | `veDuoc` đọc `dai_dien`; `giaTai` pallet đọc `gia_pallet_mh`; `mucKhac` |
| `giao_dien/src/doi_thu/ho_so_logic.ts` | `cuaBang` đọc `dai_dien` |
| `giao_dien/src/doi_thu/bang_sua_logic.ts` | `nhanMuc`, `nhomBang` (nhóm dòng theo mặt hàng), cột "Mức giá" |
| `giao_dien/src/doi_thu/BangSua.tsx`, `TabDuyet.tsx`, `ONoiGia.tsx`, `doi_thu.css` | nhóm / 🗑 / Khôi phục / Gộp vào… / các mức khác |
| `CLAUDE.md`, `docs/runbook.md` | bất biến 070, migration 070 trước triển khai |

---

### Task 1: Migration 070 — sổ ẩn / gộp, mặt hàng, đại diện

**Files:**
- Create: `db/migrations/070_doi_thu_mat_hang_an.sql`
- Test: `tests/test_mart_doi_thu.py` (thêm cuối file)
- Regenerate: `kome/web/tai_lieu_sinh.json`, `kome/web/cot_dung_sinh.json` (qua hai script)

**Interfaces:**
- Produces (SQL): `app.an_quan_sat(id, nguon, quan_sat_id, an, nguoi_dung_id, luc)`,
  `app.gop_mat_hang(id, ma_doi_thu, ma_hang_dt, vao_ma_hang_dt, nguoi_dung_id, luc)`,
  `mart.la_muc_khach_thuong(text) → boolean`,
  `mart.gia_doi_thu_quan_sat` + cột `an boolean`, `mat_hang_khoa text`, `an_hien_hanh boolean` (CUỐI view),
  `mart.gia_doi_thu_hien_hanh` + cột `dai_dien boolean`, `gia_pallet_mh numeric`, `so_muc bigint` (CUỐI view),
  `mart.so_sanh_nhom` (cột không đổi; chỉ đọc dòng `dai_dien`).

- [ ] **Step 1: Viết test hỏng** — thêm vào cuối `tests/test_mart_doi_thu.py` (dùng `_hang`, `_qs` sẵn có đầu file):

```python
# ---------------------------------------------------------------- 070: mặt hàng · đại diện · ẩn · gộp tay

def _muc(conn, fid, kenh=None, muc=None):
    conn.execute("UPDATE core.fact_gia_doi_thu SET kenh_gia = %s, muc_gia = %s WHERE id = %s", (kenh, muc, fid))
    conn.commit()


def _hh(conn, ben):
    return conn.execute("""SELECT id, kenh_gia, muc_gia, dai_dien, mat_hang_khoa, gia_pallet_mh, so_muc
                           FROM mart.gia_doi_thu_hien_hanh WHERE ma_doi_thu = %s ORDER BY id""", (ben,)).fetchall()


def test_070_dai_dien_la_gia_re_nhat_cho_khach_thuong_moi_mat_hang(conn, batch):
    _hang(conn, batch)
    giao = _qs(conn, batch, "NEXT", 650, hang="h1")
    gui = _qs(conn, batch, "NEXT", 600, hang="h1")
    kho = _qs(conn, batch, "NEXT", 580, hang="h1")
    ngoai = _qs(conn, batch, "NEXT", 500, hang="h1")
    pal = _qs(conn, batch, "NEXT", 450, hang="h1")
    _muc(conn, giao, kenh="giao"); _muc(conn, gui, kenh="gui"); _muc(conn, kho, kenh="tai_kho")
    _muc(conn, ngoai, muc="khach_ngoai"); _muc(conn, pal, muc="pallet")
    r = {x[0]: x for x in _hh(conn, "NEXT")}
    assert [i for i, x in r.items() if x[3]] == [kho]                    # rẻ nhất trong mức khách thường
    assert {x[4] for x in r.values()} == {"h1"} and {x[6] for x in r.values()} == {5}
    assert all(x[5] is None or float(x[5]) == 450 for x in r.values())   # pallet của mặt hàng = dòng muc 'pallet'


def test_070_dai_dien_roi_ve_khi_khong_co_muc_khach_thuong(conn, batch):
    _hang(conn, batch)
    ngoai = _qs(conn, batch, "VC", 300, hang="h2")
    pal = _qs(conn, batch, "VC", 280, hang="h2")
    _muc(conn, ngoai, muc="khach_ngoai"); _muc(conn, pal, muc="pallet")
    assert [x[0] for x in _hh(conn, "VC") if x[3]] == [ngoai]            # không phải pallet trước


def test_070_so_sanh_nhom_dem_moi_mat_hang_mot_lan(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580)]:
        _qs(conn, batch, ben, g, hang=f"h{ben}")
    for i, g in enumerate((700, 720)):                                    # bên A thêm 2 mức của CÙNG mặt hàng
        f = _qs(conn, batch, "A", g, hang="hA")
        _muc(conn, f, kenh=("giao", "gui")[i])
    s = conn.execute("SELECT so_ben, so_quan_sat, trung_vi, thap_nhat FROM mart.so_sanh_nhom WHERE nhom_khoa = 'ma:NT01'").fetchone()
    assert (s[0], s[1]) == (3, 3)
    assert float(s[2]) == 560 and float(s[3]) == 540


def test_070_an_khong_lam_dong_cu_song_lai_va_lo_moi_hien_lai(conn, batch):
    _hang(conn, batch)
    cu = _qs(conn, batch, "A", 500, hang="hX", ngay=date(2026, 7, 1))
    moi = _qs(conn, batch, "A", 520, hang="hX", ngay=date(2026, 8, 1))
    conn.execute("INSERT INTO app.an_quan_sat (nguon, quan_sat_id, an) VALUES ('nap', %s, true)", (moi,))
    conn.commit()
    assert _hh(conn, "A") == []                                           # không dòng nào hiện hành, kể cả dòng cũ
    assert conn.execute("SELECT id FROM mart.gia_doi_thu_quan_sat WHERE an_hien_hanh").fetchall() == [(moi,)]
    moi2 = _qs(conn, batch, "A", 530, hang="hX", ngay=date(2026, 9, 1))
    assert [x[0] for x in _hh(conn, "A")] == [moi2]
    conn.execute("INSERT INTO app.an_quan_sat (nguon, quan_sat_id, an) VALUES ('nap', %s, false)", (moi,))
    conn.commit()
    assert [x[0] for x in _hh(conn, "A")] == [moi2]                      # khôi phục dòng cũ hơn: lô mới vẫn thắng


def test_070_gop_tay_mot_buoc(conn, batch):
    _hang(conn, batch)
    a = _qs(conn, batch, "TD", 285, hang="bun|a")
    b = _qs(conn, batch, "TD", 240, hang="bun|b")
    _muc(conn, b, muc="dac_biet")
    conn.execute("INSERT INTO app.gop_mat_hang (ma_doi_thu, ma_hang_dt, vao_ma_hang_dt) VALUES ('TD', 'bun|b', 'bun|a')")
    conn.commit()
    r = {x[0]: x for x in _hh(conn, "TD")}
    assert r[a][4] == r[b][4] == "bun|a"
    assert [i for i, x in r.items() if x[3]] == [b]                       # 'dac_biet' là khách thường, rẻ hơn
    conn.execute("INSERT INTO app.gop_mat_hang (ma_doi_thu, ma_hang_dt, vao_ma_hang_dt) VALUES ('TD', 'bun|b', NULL)")
    conn.commit()
    assert {x[4] for x in _hh(conn, "TD")} == {"bun|a", "bun|b"}


def test_070_hai_so_chi_them_kome_app_khong_sua_khong_xoa(conn):
    for bang in ("app.an_quan_sat", "app.gop_mat_hang"):
        for quyen in ("UPDATE", "DELETE"):
            assert not conn.execute("SELECT has_table_privilege('kome_app', %s, %s)", (bang, quyen)).fetchone()[0]
        assert conn.execute("SELECT has_table_privilege('kome_app', %s, 'INSERT')", (bang,)).fetchone()[0]


def test_070_la_muc_khach_thuong(conn):
    r = conn.execute("""SELECT mart.la_muc_khach_thuong(NULL), mart.la_muc_khach_thuong('dac_biet'),
                               mart.la_muc_khach_thuong('pallet'), mart.la_muc_khach_thuong('khach_ngoai'),
                               mart.la_muc_khach_thuong('kyushu')""").fetchone()
    assert r == (True, True, False, False, False)
```

(`_qs` ghi `ma_hang_dt = hang`, `ma_kome_de_xuat = 'NT01'`, nhãn 'thay_the', `kg_moi_don_vi_gia = 1`, đơn vị 'kg' — mọi dòng
vào nhóm `ma:NT01` theo kg. `date` đã import đầu file; nếu chưa thì thêm `from datetime import date`.)

- [ ] **Step 2: Chạy, xác nhận hỏng**

Run: `python -m pytest -q tests/test_mart_doi_thu.py -k 070`
Expected: FAIL (relation "app.an_quan_sat" does not exist / column dai_dien does not exist).

- [ ] **Step 3: Viết migration** `db/migrations/070_doi_thu_mat_hang_an.sql`. Cấu trúc (đúng thứ tự):

1. Chú thích đầu file (tiếng Việt): mục đích (§1 đặc tả, số đo), ba view DROP + CREATE (không view nào khác phụ thuộc —
   đã kiểm: chỉ `gia_doi_thu_hien_hanh` và `so_sanh_nhom` đọc `gia_doi_thu_quan_sat`), sổ chỉ thêm.
2. Hai bảng:

```sql
CREATE TABLE app.an_quan_sat (
    id            bigserial PRIMARY KEY,
    nguon         text   NOT NULL CHECK (nguon IN ('nap', 'tay')),
    quan_sat_id   bigint NOT NULL,
    an            boolean NOT NULL,
    nguoi_dung_id bigint REFERENCES app.nguoi_dung(id),
    luc           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX an_quan_sat_moi_nhat ON app.an_quan_sat (nguon, quan_sat_id, id DESC);

CREATE TABLE app.gop_mat_hang (
    id             bigserial PRIMARY KEY,
    ma_doi_thu     text NOT NULL REFERENCES app.doi_thu(ma),
    ma_hang_dt     text NOT NULL,
    vao_ma_hang_dt text,
    nguoi_dung_id  bigint REFERENCES app.nguoi_dung(id),
    luc            timestamptz NOT NULL DEFAULT now(),
    CHECK (vao_ma_hang_dt IS NULL OR vao_ma_hang_dt <> ma_hang_dt)
);
CREATE INDEX gop_mat_hang_moi_nhat ON app.gop_mat_hang (ma_doi_thu, ma_hang_dt, id DESC);

REVOKE UPDATE, DELETE ON app.an_quan_sat, app.gop_mat_hang FROM kome_app;
GRANT SELECT, INSERT ON app.an_quan_sat, app.gop_mat_hang TO kome_app;
GRANT USAGE ON SEQUENCE app.an_quan_sat_id_seq, app.gop_mat_hang_id_seq TO kome_app;
GRANT SELECT ON app.an_quan_sat, app.gop_mat_hang TO kome_report, kome_ingest;
```

   (Kiểm kiểu của `app.nguoi_dung.id` trong `019_danh_tinh.sql` — dùng đúng kiểu đó cho FK. Kiểm cách 030 / 063 viết
   REVOKE / GRANT sequence và chép nếp.)
2b. Nhật ký nhận ba loại mới (chép danh sách của 065 — kiểm `grep -rn doi_thu_nhat_ky_loai_check db/migrations` để chắc
   không có bản mới hơn):

```sql
ALTER TABLE app.doi_thu_nhat_ky DROP CONSTRAINT doi_thu_nhat_ky_loai_check;
ALTER TABLE app.doi_thu_nhat_ky ADD CONSTRAINT doi_thu_nhat_ky_loai_check
    CHECK (loai IN ('xac_nhan', 'sua', 'gia_moi', 'them', 'ghep', 'nhom', 'quy_cach', 'doi_thu', 'thu_muc',
                    'giao_hang', 'dieu_kien', 'an', 'hien', 'gop'));
```
3. Hàm:

```sql
CREATE FUNCTION mart.la_muc_khach_thuong(p_muc text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
    SELECT p_muc IS NULL OR p_muc = 'dac_biet'
$$;
```
4. `DROP VIEW mart.so_sanh_nhom; DROP VIEW mart.gia_doi_thu_hien_hanh; DROP VIEW mart.gia_doi_thu_quan_sat;`
5. `CREATE VIEW mart.gia_doi_thu_quan_sat AS` — **chép NGUYÊN VĂN thân 067 (dòng 45–202 của
   `067_mart_quan_sat_gia_bac.sql`)** rồi áp ĐÚNG các sửa sau:
   - (a) thêm hai CTE ngay sau `thay AS MATERIALIZED (...)`:

```sql
an_ AS (      -- 070: trạng thái MỚI NHẤT của sổ ẩn (không có dòng = không ẩn)
    SELECT DISTINCT ON (nguon, quan_sat_id) nguon, quan_sat_id AS id, an
    FROM app.an_quan_sat ORDER BY nguon, quan_sat_id, id DESC
),
gop_ AS (     -- 070: gộp tay MỚI NHẤT của (bên, hàng); vao NULL = đã tách. Luôn một bước (máy chủ giữ luật).
    SELECT DISTINCT ON (ma_doi_thu, ma_hang_dt) ma_doi_thu, ma_hang_dt, vao_ma_hang_dt
    FROM app.gop_mat_hang ORDER BY ma_doi_thu, ma_hang_dt, id DESC
),
```
   - (b) trong CTE `ghep`, thêm hai cột và hai LEFT JOIN:

```sql
           th.id IS NOT NULL AS bi_thay,
           coalesce(an_.an, false) AS an,
           coalesce(gp.vao_ma_hang_dt, a.ma_hang_dt) AS mat_hang_khoa
    FROM tat a LEFT JOIN app.ghep_hang g USING (ma_doi_thu, ma_hang_dt)
    LEFT JOIN thay th ON th.nguon = a.nguon AND th.id = a.id
    LEFT JOIN an_ ON an_.nguon = a.nguon AND an_.id = a.id
    LEFT JOIN gop_ gp ON gp.ma_doi_thu = a.ma_doi_thu AND gp.ma_hang_dt = a.ma_hang_dt
```
   - (c) trong CTE `r`, thay biểu thức `hien_hanh` bằng (rn VẪN tính trên dòng ẩn — ẩn không làm dòng cũ sống lại):

```sql
       NOT x.bi_thay AND NOT x.an AND row_number() OVER w = 1                               AS hien_hanh,
```
     và thêm ở CUỐI danh sách cột của `r` (sau `x.so_goi_thung, x.kl_goi_g, x.bac`):

```sql
       , x.an, x.mat_hang_khoa, (NOT x.bi_thay AND x.an AND row_number() OVER w = 1) AS an_hien_hanh
```
     và thêm mệnh đề cửa sổ ngay trước `),` đóng CTE `r` (sau các LEFT JOIN của `r`):

```sql
WINDOW w AS (PARTITION BY x.ma_doi_thu, x.ma_hang_dt, coalesce(x.kenh_gia, ''), coalesce(x.muc_gia, ''),
                          (x.loai_nguon = 'khach_ke'), x.bi_thay
             ORDER BY x.ngay_nguon DESC, ln.thu_tu, (x.nguon = 'tay') DESC, x.batch_id DESC NULLS FIRST, x.id DESC)
```
     (phân vùng / thứ tự GIỮ ĐÚNG như 067 — dùng `ma_hang_dt` gốc, không `mat_hang_khoa`: gộp tay không làm hai mức
     khác phân vùng tranh nhau "hiện hành").
6. `CREATE VIEW mart.gia_doi_thu_hien_hanh AS` — chép thân 067 (dòng 226–291) và sửa:
   - thay CTE `tv` bằng hai CTE (trung vị / số bên theo MẶT HÀNG, giá rẻ nhất cho khách thường, KHÔNG lọc bất thường —
     bất thường cần chính mốc này):

```sql
mh AS (       -- 070: MỘT giá mỗi mặt hàng cho mốc "bất thường" — rẻ nhất cho khách thường, không hết, không khách kể
    SELECT nhom_khoa, don_vi_so, ma_doi_thu, mat_hang_khoa, min(yen_chuan) AS gia
    FROM q
    WHERE nhom_khoa IS NOT NULL AND yen_chuan IS NOT NULL AND trang_thai <> 'het' AND loai_nguon <> 'khach_ke'
      AND mart.la_muc_khach_thuong(muc_gia)
    GROUP BY 1, 2, 3, 4
),
tv AS (
    SELECT nhom_khoa, don_vi_so,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY gia) AS trung_vi,
           count(DISTINCT ma_doi_thu)                       AS so_ben
    FROM mh GROUP BY 1, 2
),
```
   - đổi SELECT cuối của 067 thành CTE `x AS (SELECT q.*, ... FROM q LEFT JOIN tv ... CROSS JOIN LATERAL (...) m)` (thân
     nguyên văn), rồi SELECT cuối mới:

```sql
SELECT x.*,
       x.loai_nguon <> 'khach_ke' AND row_number() OVER mh_w = 1                             AS dai_dien,
       min(x.gia_pallet) OVER (PARTITION BY x.nhom_khoa, x.don_vi_so, x.ma_doi_thu, x.mat_hang_khoa,
                                            (x.loai_nguon = 'khach_ke'))                    AS gia_pallet_mh,
       count(*) OVER (PARTITION BY x.nhom_khoa, x.don_vi_so, x.ma_doi_thu, x.mat_hang_khoa,
                                   (x.loai_nguon = 'khach_ke'))                             AS so_muc
FROM x
WINDOW mh_w AS (
    PARTITION BY x.nhom_khoa, x.don_vi_so, x.ma_doi_thu, x.mat_hang_khoa, (x.loai_nguon = 'khach_ke')
    ORDER BY CASE WHEN mart.la_muc_khach_thuong(x.muc_gia) AND x.trang_thai <> 'het' AND x.yen_chuan IS NOT NULL
                       AND NOT x.bat_thuong THEN 0
                  WHEN coalesce(x.muc_gia, '') <> 'pallet' THEN 1 ELSE 2 END,
             x.yen_chuan NULLS LAST, x.nguon, x.id);
```
7. `CREATE VIEW mart.so_sanh_nhom AS` — chép thân 067 (dòng 296–329), CHỈ sửa WHERE của CTE `h`:

```sql
    WHERE nhom_khoa IS NOT NULL AND yen_chuan IS NOT NULL AND trang_thai <> 'het'
      AND loai_nguon <> 'khach_ke' AND NOT bat_thuong AND dai_dien
```
8. GRANT (chép dòng 331–333 của 067 cho ba view + `GRANT EXECUTE ON FUNCTION mart.la_muc_khach_thuong(text) TO kome_app,
   kome_report, kome_ingest;`).

- [ ] **Step 4: Chạy test mart**

Run: `python -m pytest -q tests/test_mart_doi_thu.py`
Expected: PASS toàn file (test cũ 060–068 phải còn xanh; nếu test cũ đếm `so_quan_sat` theo DÒNG của cùng mặt hàng, đó là
hành vi đổi có chủ ý — sửa kỳ vọng và ghi một câu vì sao trong test).

- [ ] **Step 5: Sinh lại tài liệu sống**

Run: `python scripts/sinh_tai_lieu.py && python scripts/sinh_cot_dung.py && python -m pytest -q tests/test_tai_lieu.py tests/test_cot_dung.py tests/test_migrate.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add db/migrations/070_doi_thu_mat_hang_an.sql tests/test_mart_doi_thu.py kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json
git commit -m "feat(doi-thu): migration 070 — mat hang (ma_hang_dt + gop tay), dai dien re nhat cho khach thuong, trung vi theo mat hang, so an chi them"
```

---

### Task 2: Máy chủ — cột mới, ẩn / khôi phục, gộp tay, "Đã xoá", số mặt hàng

**Files:**
- Modify: `kome/doi_thu.py` (`_COT_QS` ~752, `_TONG_QUAN` ~836, `_DUYET` ~1072, `duyet`, thêm `dat_an`, `gop_mat_hang`,
  `LOC_DUYET`)
- Modify: `kome/web/api.py` (cạnh `@r.post("/doi-thu/sua-mat-hang")` ~929)
- Test: `tests/test_doi_thu.py`, `tests/test_doi_thu_api.py`

**Interfaces:**
- Consumes: view / bảng của Task 1.
- Produces:
  - `DT.dat_an(conn, b: dict, nguoi) -> dict` — `b = {nguon, id, an: bool, da_xem, ghi_de}` → `{"nguon", "id",
    "sua_cuoi"}`.
  - `DT.gop_mat_hang(conn, b: dict, nguoi) -> dict` — `b = {ma_doi_thu, ma_hang_dt, vao_ma_hang_dt | None, da_xem, ghi_de}`
    → `{"ma_doi_thu", "ma_hang_dt", "vao_ma_hang_dt" (đích ĐÃ QUY), "sua_cuoi"}`.
  - `POST /api/doi-thu/an`, `POST /api/doi-thu/gop-mat-hang` (qua `_dt_ghi`, POST chỉ JSON như route cạnh).
  - `DT.duyet(conn, ben, loc)` nhận `loc = 'da_xoa'`; mọi dòng trả mang `mat_hang_khoa`, `an`, và (hiện hành)
    `dai_dien`, `gia_pallet_mh`, `so_muc` — dòng "Đã xoá" mang `dai_dien = false`, `so_muc = 1`, `gia_pallet_mh = null`.
  - `tong_quan()["ben"][i]["so_dong"]` = số MẶT HÀNG (distinct `mat_hang_khoa`, không khách kể); thêm `so_muc` = số dòng.

- [ ] **Step 1: Test hỏng** — thêm vào `tests/test_doi_thu.py` (dùng `_hang`, `_qs`, `_dem` có sẵn):

```python
def test_dat_an_an_va_khoi_phuc_ghi_nhat_ky_va_409(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "A", 540, hang="hA")
    r = DT.dat_an(conn, {"nguon": "nap", "id": fid, "an": True, "da_xem": 0}, None)
    conn.commit()
    assert r["sua_cuoi"] > 0
    assert DT.duyet(conn)["dong"] == []
    assert [x["id"] for x in DT.duyet(conn, loc="da_xoa")["dong"]] == [fid]
    with pytest.raises(DT.XungDot):                                   # người khác vừa ẩn: da_xem cũ
        DT.dat_an(conn, {"nguon": "nap", "id": fid, "an": False, "da_xem": 0}, None)
    DT.dat_an(conn, {"nguon": "nap", "id": fid, "an": False, "da_xem": r["sua_cuoi"]}, None)
    conn.commit()
    assert [x["id"] for x in DT.duyet(conn)["dong"]] == [fid]
    assert [x[0] for x in conn.execute("SELECT loai FROM app.doi_thu_nhat_ky ORDER BY id")] == ["an", "hien"]


def test_dat_an_tu_choi_dong_khong_co(conn, batch):
    with pytest.raises(DT.LoiNhap):
        DT.dat_an(conn, {"nguon": "nap", "id": 999999, "an": True, "da_xem": 0}, None)
    with pytest.raises(DT.LoiNhap):
        DT.dat_an(conn, {"nguon": "nap", "id": 1, "an": "co", "da_xem": 0}, None)


def test_gop_mat_hang_mot_buoc_va_chep_ghep(conn, batch):
    _hang(conn, batch)
    _qs(conn, batch, "A", 500, hang="h1")
    _qs(conn, batch, "A", 480, hang="h2", ma=None)                   # h2 chưa có mã KOME
    _qs(conn, batch, "A", 470, hang="h3", ma=None)
    DT.dat_ghep(conn, "A", "h1", "NT01", None, "cung_hang", None)
    r = DT.gop_mat_hang(conn, {"ma_doi_thu": "A", "ma_hang_dt": "h2", "vao_ma_hang_dt": "h1", "da_xem": 0}, None)
    conn.commit()
    assert r["vao_ma_hang_dt"] == "h1"
    g = conn.execute("SELECT product_code, nhan FROM app.ghep_hang WHERE ma_doi_thu='A' AND ma_hang_dt='h2'").fetchone()
    assert g == ("NT01", "cung_hang")                                  # chép ghép của đích
    # gộp h1 vào h3: h2 (đang trỏ h1) cũng chuyển sang h3 — mọi đích là hàng không gộp vào đâu
    DT.gop_mat_hang(conn, {"ma_doi_thu": "A", "ma_hang_dt": "h1", "vao_ma_hang_dt": "h3", "da_xem": None}, None)
    conn.commit()
    k = dict(conn.execute("SELECT ma_hang_dt, mat_hang_khoa FROM mart.gia_doi_thu_hien_hanh WHERE ma_doi_thu='A'").fetchall())
    assert k == {"h1": "h3", "h2": "h3", "h3": "h3"}
    # gộp h3 vào h2: đích h2 đang trỏ h3 → quy về h3 = chính nó → từ chối
    with pytest.raises(DT.LoiNhap):
        DT.gop_mat_hang(conn, {"ma_doi_thu": "A", "ma_hang_dt": "h3", "vao_ma_hang_dt": "h2", "da_xem": None}, None)
    DT.gop_mat_hang(conn, {"ma_doi_thu": "A", "ma_hang_dt": "h2", "vao_ma_hang_dt": None, "da_xem": None}, None)
    conn.commit()
    k = dict(conn.execute("SELECT ma_hang_dt, mat_hang_khoa FROM mart.gia_doi_thu_hien_hanh WHERE ma_doi_thu='A'").fetchall())
    assert k["h2"] == "h2"


def test_gop_mat_hang_tu_choi_dich_khong_co(conn, batch):
    _hang(conn, batch)
    _qs(conn, batch, "A", 500, hang="h1")
    with pytest.raises(DT.LoiNhap):
        DT.gop_mat_hang(conn, {"ma_doi_thu": "A", "ma_hang_dt": "h1", "vao_ma_hang_dt": "khong-co", "da_xem": None}, None)


def test_duyet_va_tong_quan_mang_cot_mat_hang_va_dem_mat_hang(conn, batch, monkeypatch):
    _hang(conn, batch)
    for i, k in enumerate(("giao", "gui", "tai_kho")):
        f = _qs(conn, batch, "NEXT", 600 + i, hang="h1")
        conn.execute("UPDATE core.fact_gia_doi_thu SET kenh_gia = %s WHERE id = %s", (k, f))
    conn.commit()
    d = DT.duyet(conn, ben="NEXT")["dong"]
    assert {x["mat_hang_khoa"] for x in d} == {"h1"} and sum(x["dai_dien"] for x in d) == 1
    assert {x["so_muc"] for x in d} == {3}
    ben = {b["ma"]: b for b in DT.tong_quan(conn)["ben"]}
    assert ben["NEXT"]["so_dong"] == 1 and ben["NEXT"]["so_muc"] == 3
    dem = _dem(conn, monkeypatch)
    DT.duyet(conn, loc="da_xoa")
    assert dem["n"] == 1
```

  và vào `tests/test_doi_thu_api.py` (dựng client như các test POST có sẵn trong file — xem `test_post_thu_muc_chi_nhan_json`
  và test gọi `/api/doi-thu/sua-mat-hang`):

```python
def test_post_an_va_gop_mat_hang_chi_nhan_json_va_tra_409(client_doi_thu):
    ...  # chép đúng mẫu fixture / helper mà file đang dùng cho /sua-mat-hang:
         # 1) POST /api/doi-thu/an {"nguon":"nap","id":<fid>,"an":true,"da_xem":0} -> 200, body có sua_cuoi
         # 2) POST lại với da_xem 0 -> 409, body {"loi", "xung_dot": {...}}
         # 3) POST /api/doi-thu/an với data=<chữ thô> (không JSON) -> 400/415 như test chi_nhan_json có sẵn
         # 4) POST /api/doi-thu/gop-mat-hang {"ma_doi_thu":"A","ma_hang_dt":"hB","vao_ma_hang_dt":"hA","da_xem":0} -> 200
```
  (Test này PHẢI được viết đầy đủ theo mẫu có sẵn của file — đọc file trước; không để `...` trong code commit.)

- [ ] **Step 2: Chạy, xác nhận hỏng**

Run: `python -m pytest -q tests/test_doi_thu.py -k "dat_an or gop_mat_hang or mat_hang_va_dem" tests/test_doi_thu_api.py -k "an_va_gop"`
Expected: FAIL (AttributeError: module 'kome.doi_thu' has no attribute 'dat_an').

- [ ] **Step 3: Cài đặt** trong `kome/doi_thu.py`:
  - `_COT_QS`: thêm `mat_hang_khoa, an,` (sau `so_goi_thung, kl_goi_g, bac, ...` — trước `sua_cuoi`). Hằng mới
    `_COT_MH = "dai_dien, round(gia_pallet_mh) AS gia_pallet_mh, so_muc"` chèn vào các câu đọc TỪ `gia_doi_thu_hien_hanh`
    (`_DUYET`, `_SO_SANH` CTE `h`); câu đọc từ `gia_doi_thu_quan_sat` (`_HO_SO`, `_MAT_HANG`) lấy ba cột đó qua CTE
    `bt` / subquery của hiện hành như `bat_thuong` đang làm (không hiện hành → `false`, `NULL`, `1`).
  - `LOC_DUYET` thêm `"da_xoa"`. `duyet(conn, ben, loc)`: `loc == "da_xoa"` → câu riêng `_DUYET_DA_XOA` đọc
    `mart.gia_doi_thu_quan_sat WHERE an_hien_hanh AND (%(ben)s = '' OR ma_doi_thu = %(ben)s)` với
    `_COT_QS_KHONG_BT`, `false AS bat_thuong, NULL::numeric AS moc_bat_thuong, NULL::text AS moc_bat_thuong_la,
    false AS dai_dien, NULL::numeric AS gia_pallet_mh, 1::bigint AS so_muc`, cùng trần `DONG_TOI_DA_DUYET` + `tong`.
    Thứ tự của CẢ HAI câu: `ORDER BY ma_doi_thu, mat_hang_khoa, dai_dien DESC, yen_chuan NULLS LAST, nguon, id` (bỏ thứ tự
    "bất thường trước" cũ — các mức của một mặt hàng phải liền nhau; bộ lọc "Bất thường" vẫn có). Sửa test cũ nào khẳng
    định thứ tự cũ (nếu có) và nói vì sao.
  - `_TONG_QUAN` CTE `x`: `count(DISTINCT mat_hang_khoa) FILTER (WHERE loai_nguon <> 'khach_ke') so_dong, count(*) so_muc`,
    và `'so_muc', coalesce(x.so_muc, 0)` trong `json_build_object` của `ben`.
  - `dat_an`:

```python
def dat_an(conn, b: dict, nguoi) -> dict:
    """Ẩn / khôi phục MỘT quan sát (070): sổ app.an_quan_sat CHỈ THÊM + nhật ký 'an' / 'hien' trên khoá của chính dòng
    ('gia:<id>' | 'tay:<id>' — cùng khoá 409 của pop-up), CÙNG giao dịch. Ẩn không xoá gì ở core."""
    if not isinstance(b, dict):
        raise LoiNhap("Thân yêu cầu phải là một đối tượng JSON.")
    nguon = b.get("nguon")
    if nguon not in ("nap", "tay"):
        raise LoiNhap("Nguồn chỉ nhận nap / tay.")
    id_ = doc_id(b.get("id"))
    an = b.get("an")
    if not isinstance(an, bool):
        raise LoiNhap("an phải là true / false.")
    khoa = f"{'gia' if nguon == 'nap' else 'tay'}:{id_}"
    kiem_xung_dot(conn, [khoa], doc_da_xem(b.get("da_xem")) if "da_xem" in b else None, b.get("ghi_de") is True)
    r = conn.execute("SELECT an FROM mart.gia_doi_thu_quan_sat WHERE nguon = %s AND id = %s", (nguon, id_)).fetchone()
    if r is None:
        raise LoiNhap("Không tìm thấy dòng giá này (có thể lô đã bị hoàn tác).")
    conn.execute("INSERT INTO app.an_quan_sat (nguon, quan_sat_id, an, nguoi_dung_id) VALUES (%s, %s, %s, %s)",
                 (nguon, id_, an, nguoi))
    _ghi_nhat_ky(conn, "an" if an else "hien", khoa, {"an": r[0]}, {"an": an}, nguoi)
    return {"nguon": nguon, "id": id_, "sua_cuoi": sua_cuoi_cua(conn, [khoa, *_khoa_ghep(conn, nguon, id_)])}
```
    với `_khoa_ghep(conn, nguon, id_) -> list[str]` trả `[f"{bên}/{hàng}"]` của dòng (để `sua_cuoi` trả về BẰNG `sua_cuoi`
    của các câu đọc, vốn gộp cả hai khoá). CHECK của `app.doi_thu_nhat_ky.loai` đã nhận `an` / `hien` / `gop` từ 070 (Task 1, bước 2b).
  - `gop_mat_hang`:

```python
def gop_mat_hang(conn, b: dict, nguoi) -> dict:
    """Gộp tay (bên, hàng) vào mặt hàng đích cùng bên (070; vao None = tách ra). LUÔN một bước: đích đang gộp vào C →
    ghi vào C; hàng đang gộp vào (bên, hàng) → ghi lại vào đích mới. Đích phải có dòng hiện hành của cùng bên; quy xong
    mà đích == chính nó → LoiNhap. Gộp (không phải tách) mà (bên, hàng) chưa có dòng app.ghep_hang → chép ghép của đích
    qua dat_ghep (cùng nhóm so sánh). 409 + nhật ký 'gop' trên '<bên>/<hàng>'. CÙNG giao dịch."""
```
    thân: kiểm kiểu (`ma_doi_thu`, `ma_hang_dt` chữ 1–`DAI_TOI_DA`, `vao_ma_hang_dt` None hoặc chữ); `kiem_xung_dot` trên
    `[f"{ben}/{hang}"]`; nguồn (bên, hàng) phải có dòng trong `mart.gia_doi_thu_quan_sat`; quy đích:
    `SELECT vao_ma_hang_dt FROM app.gop_mat_hang WHERE ma_doi_thu=%s AND ma_hang_dt=%s ORDER BY id DESC LIMIT 1` — có
    giá trị thì đích = giá trị đó; đích == hàng → LoiNhap("Không gộp một mặt hàng vào chính nó."); đích phải có
    `SELECT 1 FROM mart.gia_doi_thu_hien_hanh WHERE ma_doi_thu=%s AND ma_hang_dt=%s`; INSERT dòng gộp; con trỏ cũ:
    `SELECT DISTINCT ON (ma_hang_dt) ma_hang_dt, vao_ma_hang_dt FROM app.gop_mat_hang WHERE ma_doi_thu=%s ORDER BY
    ma_hang_dt, id DESC` lọc `vao_ma_hang_dt = hang` → INSERT mỗi hàng đó với đích mới (tách: giữ nguyên, chúng vẫn trỏ
    hàng này và hàng này nay không gộp đâu — hợp lệ); chép ghép nếu cần; `_ghi_nhat_ky(conn, "gop", khoa, {"vao": cũ},
    {"vao": dich}, nguoi)`; trả dict như Interfaces.
  - `kome/web/api.py`: hai route theo đúng mẫu `dt_sua_mat_hang` (docstring một dòng thân vào / ra):

```python
    @r.post("/doi-thu/an")
    async def dt_an(request: Request):
        """{nguon, id, an, da_xem, ghi_de} -> {ok, nguon, id, sua_cuoi} (DT.dat_an). Người khác vừa sửa -> 409."""
        from kome import doi_thu as DT
        return await _dt_ghi(request, lambda c, b, n: DT.dat_an(c, b, n))

    @r.post("/doi-thu/gop-mat-hang")
    async def dt_gop_mat_hang(request: Request):
        """{ma_doi_thu, ma_hang_dt, vao_ma_hang_dt|null, da_xem, ghi_de} -> {ok, …, vao_ma_hang_dt} (DT.gop_mat_hang)."""
        from kome import doi_thu as DT
        return await _dt_ghi(request, lambda c, b, n: DT.gop_mat_hang(c, b, n))
```

- [ ] **Step 4: Chạy**

Run: `python -m pytest -q tests/test_doi_thu.py tests/test_doi_thu_api.py tests/test_mart_doi_thu.py tests/test_lien_he.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kome/doi_thu.py kome/web/api.py tests/test_doi_thu.py tests/test_doi_thu_api.py
git commit -m "feat(doi-thu): an / khoi phuc va gop tay mat hang doi thu (409 + nhat ky), duyet 'da_xoa', so mat hang cua ben"
```

---

### Task 3: Giao diện — logic thuần (một chỗ `veDuoc`, nhóm dòng bảng sửa, mức giá)

**Files:**
- Modify: `giao_dien/src/doi_thu/kieu.ts`, `so_sanh_logic.ts`, `ho_so_logic.ts`, `bang_sua_logic.ts`
- Test: `so_sanh_logic.test.ts`, `ho_so_logic.test.ts`, `bang_sua_logic.test.ts`

**Interfaces:**
- Consumes: cột `mat_hang_khoa: string`, `an: boolean`, `dai_dien?: boolean`, `gia_pallet_mh?: number | null`,
  `so_muc?: number` trên mỗi quan sát (Task 2); `TongQuan.ben[i].so_muc?: number`.
- Produces:
  - `kieu.ts`: các trường trên vào `QuanSat`; `NHAN_MUC: Record<string, string>` = `{ giao: "Giao tận nơi", gui: "Gửi",
    tai_kho: "Tại kho", pallet: "Pallet", dac_biet: "Đặc biệt", khach_ngoai: "Khách ngoài", kyushu: "Kyushu" }`.
  - `so_sanh_logic.ts`: `veDuoc(q)` = `q.loai_nguon !== "khach_ke" && q.dai_dien !== false` (export nó);
    `giaTai(q, "pallet")` đọc `q.gia_pallet_mh ?? q.gia_pallet`; `mucKhac(n: Nhom, q: QuanSat): QuanSat[]` = dòng
    khác `q` cùng `ma_doi_thu` + `mat_hang_khoa` trong `n.quan_sat` (không khách kể), rẻ trước.
  - `ho_so_logic.ts`: `cuaBang` và mọi chỗ lọc "hiện hành không khách kể" để VẼ / ĐẾM thêm `q.dai_dien !== false`
    (dòng lịch sử không hiện hành không mang cờ → giữ như cũ).
  - `bang_sua_logic.ts`: `nhanMuc(q): string` = nhãn `muc_gia` (nếu có) · nhãn `kenh_gia` (nếu có), nối " · ", trống →
    "Thường", mã lạ → nguyên văn; `COT` thêm `{ ma: "muc", nhan: "Mức giá", kieu: null }` ngay sau "Bên" (MaCot thêm
    `"muc"`, `hienThi` trả `nhanMuc`); `nhomBang(ds: QuanSat[]): { dau: QuanSat; con: QuanSat[] }[]` — nhóm theo
    (`ma_doi_thu`, `mat_hang_khoa`) giữ thứ tự lần gặp đầu; `dau` = dòng `dai_dien` đầu tiên của nhóm, không có thì dòng
    đầu; `con` = các dòng còn lại theo thứ tự đến.

- [ ] **Step 1: Test hỏng** (thêm vào các file test; fixture `qs` / `nh` có sẵn trong từng file):

```ts
// so_sanh_logic.test.ts
describe("070 — mỗi mặt hàng một lần", () => {
  it("veDuoc bỏ dòng không đại diện (mức giá khác của cùng mặt hàng); dòng thiếu cờ vẫn vẽ (tương thích)", () => {
    expect(veDuoc(qs({ dai_dien: false } as Partial<QuanSat>))).toBe(false);
    expect(veDuoc(qs({ dai_dien: true } as Partial<QuanSat>))).toBe(true);
    expect(veDuoc(qs({}))).toBe(true);
    const n = nh({ quan_sat: [qs({ dai_dien: true } as Partial<QuanSat>), qs({ dai_dien: false } as Partial<QuanSat>)] });
    expect(soMatHang(n)).toBe(1);
  });
  it("giá pallet của mặt hàng", () => {
    expect(giaTai(qs({ gia_1: 900, gia_pallet: null, gia_pallet_mh: 700 } as Partial<QuanSat>), "pallet"))
      .toEqual({ gia: 700, khongGhiPallet: false });
  });
  it("mucKhac: các mức khác cùng bên + mặt hàng, rẻ trước", () => {
    const a = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1", yen_chuan: 600, dai_dien: true } as Partial<QuanSat>);
    const b = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1", yen_chuan: 650, kenh_gia: "giao", dai_dien: false } as Partial<QuanSat>);
    const c = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1", yen_chuan: 620, kenh_gia: "gui", dai_dien: false } as Partial<QuanSat>);
    const d = qs({ ma_doi_thu: "M", mat_hang_khoa: "h1", yen_chuan: 500 } as Partial<QuanSat>);
    expect(mucKhac(nh({ quan_sat: [a, b, c, d] }), a).map(x => x.id)).toEqual([c.id, b.id]);
  });
});

// bang_sua_logic.test.ts
describe("070 — nhóm dòng theo mặt hàng", () => {
  it("nhanMuc", () => {
    expect(nhanMuc(qs({ kenh_gia: "tai_kho", muc_gia: null }))).toBe("Tại kho");
    expect(nhanMuc(qs({ kenh_gia: null, muc_gia: "pallet" }))).toBe("Pallet");
    expect(nhanMuc(qs({ kenh_gia: "tai_kho", muc_gia: "dac_biet" }))).toBe("Đặc biệt · Tại kho");
    expect(nhanMuc(qs({ kenh_gia: null, muc_gia: null }))).toBe("Thường");
    expect(nhanMuc(qs({ kenh_gia: "xyz", muc_gia: null }))).toBe("xyz");
  });
  it("nhomBang: đầu nhóm là dòng đại diện, giữ thứ tự lần gặp đầu", () => {
    const a1 = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1", dai_dien: false } as Partial<QuanSat>);
    const a2 = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1", dai_dien: true } as Partial<QuanSat>);
    const b1 = qs({ ma_doi_thu: "N", mat_hang_khoa: "h2", dai_dien: true } as Partial<QuanSat>);
    const c1 = qs({ ma_doi_thu: "M", mat_hang_khoa: "h1" } as Partial<QuanSat>);
    const g = nhomBang([a1, b1, a2, c1]);
    expect(g.map(x => [x.dau.id, x.con.map(y => y.id)])).toEqual([[a2.id, [a1.id]], [b1.id, []], [c1.id, []]]);
  });
  it("cột Mức giá chỉ đọc, đứng sau Bên", () => {
    const c = cotHien(true).map(x => x.ma);
    expect(c.indexOf("muc")).toBe(c.indexOf("ben") + 1);
    expect(COT.find(x => x.ma === "muc")!.kieu).toBeNull();
  });
});
```
  và `ho_so_logic.test.ts`: một test cho thấy hai dòng hiện hành cùng mặt hàng (một `dai_dien: false`) chỉ ra MỘT thanh ở
  hàm vẽ tương ứng (`dongSoKome` — đọc file để lấy tên hàm / fixture đúng).
  (`qs` trong `bang_sua_logic.test.ts` và `so_sanh_logic.test.ts` phải thêm mặc định `mat_hang_khoa: \`h${seq}\``,
  `an: false`.)

- [ ] **Step 2: Chạy, xác nhận hỏng** — Run: `cd giao_dien && npx vitest run src/doi_thu` · Expected: FAIL (không có
  `mucKhac` / `nhanMuc` / `nhomBang`, `veDuoc` chưa export).
- [ ] **Step 3: Cài đặt** đúng Interfaces trên (không đổi hành vi nào khác). `hienThi(q, cot("muc"))` →
  `{ chu: nhanMuc(q), hoi: false }`. `oKeTiep` không cần đổi (cột `kieu: null` bị Tab bỏ qua).
- [ ] **Step 4: Chạy** — `cd giao_dien && npx vitest run && npx tsc --noEmit -p .` · Expected: PASS, sạch.
- [ ] **Step 5: Commit** — `git add giao_dien/src/doi_thu && git commit -m "feat(doi-thu): logic 070 — veDuoc doc dai_dien, gia pallet cua mat hang, cac muc khac, nhom dong bang sua"`

---

### Task 4: Giao diện — bảng sửa nhóm theo mặt hàng, 🗑 / Khôi phục, Gộp vào…, ô nổi các mức khác

**Files:**
- Modify: `giao_dien/src/doi_thu/BangSua.tsx`, `TabDuyet.tsx`, `ONoiGia.tsx`, `doi_thu.css`
- Build: `kome/web/spa/` (qua `npm run build`)

**Interfaces:**
- Consumes: Task 2 (`POST /api/doi-thu/an`, `/gop-mat-hang`, `duyet?loc=da_xoa`), Task 3 (`nhomBang`, `nhanMuc`,
  `mucKhac`, cột "muc").
- Produces: không (màn cuối).

Yêu cầu (đặc tả §5):
- [ ] **Step 1: `TabDuyet.tsx`** — `LOC` thêm `["da_xoa", "Đã xoá"]` (cuối). Chip bên in `so_dong` (nay là số MẶT HÀNG);
  thêm `title` = `${so_muc} mức giá`.
- [ ] **Step 2: `BangSua.tsx` — nhóm** — dựng hàng hiển thị từ `nhomBang(hien)`: mỗi nhóm 1 dòng `dau`; nếu `con.length`
  thì ô Tên hàng của dòng đầu thêm nút chip `+{con.length} mức` (`aria-expanded`), bấm → mở / đóng các dòng con ngay dưới
  (state `mo: Set<string>` theo khoá nhóm `${ma_doi_thu}|${mat_hang_khoa}`; mặc định đóng). Dòng con có lớp `bs-con`
  (thụt lề ô tên, nền `--nen-phu`). Chỉ số `d` của bàn phím chạy trên DANH SÁCH DÒNG ĐANG HIỆN (đầu + con đang mở) — giữ
  `hienRef` là danh sách đó. Nhóm đang có ô lỗi / 409 ở dòng con thì tự mở.
- [ ] **Step 3: 🗑 / Khôi phục** — thêm cột cuối (sau ⋯) nút 🗑 (`aria-label="Xoá <tên>"`): bấm lần 1 đổi thành chữ
  "Xoá?" (lớp `bs-xoa-hoi`, tự trở lại sau 3 s), bấm lần 2 → `POST /api/doi-thu/an {nguon, id, an: true, da_xem:
  sua_cuoi}` qua CÙNG hàng đợi theo dòng của `luu` (tách hàm `guiHang(k, fn)` dùng chung). Thành công → bỏ dòng khỏi bộ
  đệm (`setQueryData` lọc bỏ theo khoá dòng), `invalidateQueries(["doi-thu"])` trừ `duyet` (như `luu`) + `["doi-thu",
  "duyet"]` `refetchType: "none"`. Ở lọc `da_xoa`: nút là "Khôi phục" (`an: false`), thành công → bỏ dòng khỏi bảng
  đang xem. 409 → dải 409 sẵn có (thêm kiểu chờ `{ loai: "an", an: bool }` vào `Xung.ds` để Ghi đè gửi lại).
- [ ] **Step 4: Gộp vào…** — trong pop-up ⋯ KHÔNG đổi `SuaMatHang`; thay vào đó thêm nút thứ hai "⇲" cạnh ⋯ (`title="Gộp
  vào mặt hàng khác / tách ra"`) mở `HopThoai` (chung `HopThoai.tsx`) liệt kê các MẶT HÀNG khác cùng bên (từ bộ đệm bảng
  hiện tại: `nhomBang` → `dau` khác nhóm này) với ô tìm (`timDong`), chọn một → `POST /api/doi-thu/gop-mat-hang
  {ma_doi_thu, ma_hang_dt, vao_ma_hang_dt: đích.mat_hang_khoa, da_xem: sua_cuoi}`; dòng đã gộp (`mat_hang_khoa !==
  ma_hang_dt`) có nút "Tách ra" (`vao_ma_hang_dt: null`). Thành công → `invalidateQueries({queryKey: khoaQ, exact:
  true})` (nhóm / đại diện đổi cho nhiều dòng). 409 → khung `KhungXungDot` trong hộp.
- [ ] **Step 5: `ONoiGia.tsx`** — khi `mucKhac(n, q).length`, thêm khối "Các mức giá khác" (mỗi dòng: `nhanMuc` · giá
  `yen(gia_1)` /kg hoặc `yen(yen_chuan)` + `/đơn vị` khi không so theo kg) — CHỈ hiển thị, không quyết định gì.
- [ ] **Step 6: CSS** (`doi_thu.css`, khối "Bảng sửa"): `.dt-bs tr.bs-con td:first-child{padding-left:1.4rem}`,
  `.dt-bs tr.bs-con td{background:var(--nen-phu)}`, `.bs-xoa-hoi{color:var(--do-chu);font-weight:700}`, chip `+n mức`
  cỡ nhỏ. Chỉ token có sẵn.
- [ ] **Step 7: Build + kiểm** — `cd giao_dien && npx tsc --noEmit -p . && npx vitest run && npm run build`, rồi
  `python -m pytest -q tests/test_api.py -k ban_build`. Expected: sạch / PASS.
- [ ] **Step 8: Commit** — `git add giao_dien kome/web/spa && git commit -m "feat(doi-thu): bang sua nhom muc gia theo mat hang, xoa (an) / khoi phuc, gop vao / tach ra, o noi cac muc gia khac"`

---

### Task 5: Tài liệu

**Files:** `CLAUDE.md` (bảng trang `/doi-thu`, mục bất biến `/doi-thu`), `docs/runbook.md` (migration 070 trước triển khai).

- [ ] **Step 1:** Thêm vào CLAUDE.md, trong khối "Bất biến (Màn mới, đợt 4b…)", một gạch đầu dòng **"Mặt hàng & mức giá
  (070)"**: định nghĩa mặt hàng = (bên, `mat_hang_khoa`), `mart.la_muc_khach_thuong` là định nghĩa DUY NHẤT của "khách
  thường", `dai_dien` (luật ba hạng) là cờ DUY NHẤT để vẽ / đếm (`so_sanh_logic.ts::veDuoc`), trung vị / số bên theo mặt
  hàng; ẩn = sổ chỉ thêm, `rn` tính cả dòng ẩn (dòng cũ không sống lại), lô sau hiện lại; gộp tay luôn một bước. Thêm
  "**Migration 070 phải chạy TRƯỚC khi triển khai.**". Bảng trang: `/doi-thu` thêm "(070: mỗi mặt hàng một dòng, 🗑 /
  Đã xoá, Gộp vào…)" và thêm `app.an_quan_sat`, `app.gop_mat_hang` vào cột nguồn (đã có `app.*doi_thu*` — thêm tường minh).
- [ ] **Step 2:** `docs/runbook.md`: dòng migration 070 cạnh 065–069 (cách chạy `db/migrate.py`, kiểm sau khi chạy).
- [ ] **Step 3:** `python scripts/sinh_tai_lieu.py` (nếu CLAUDE.md "Bẫy đã biết" không đổi thì không cần — chạy
  `python -m pytest -q tests/test_tai_lieu.py` để chắc). Commit `docs(doi-thu): CLAUDE.md + runbook — mat hang & muc gia (070)`.
