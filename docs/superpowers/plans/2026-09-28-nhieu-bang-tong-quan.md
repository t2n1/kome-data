# Nhiều bảng Tổng quan có tên — kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mỗi người tạo / đặt tên / đổi thứ tự / xoá nhiều bảng Tổng quan riêng; mở `/` ra bảng xem gần nhất.

**Architecture:** Bảng `app.bang_tong_quan` (056) thay cột `app.nguoi_dung.bo_cuc_tong_quan`; danh sách bảng đọc bằng truy vấn con `json_agg` trong câu cổng đăng nhập (0 lượt hỏi mới) và chèn vào `window.__KOME__`. Mô-đun `kome/web/bang_tong_quan.py` giữ mọi quy tắc; `app.py` chỉ là lớp route mỏng. Giao diện thêm thanh tab + hộp "Bảng mới", bỏ dải chip vai trò.

**Tech Stack:** Postgres (Supabase), psycopg 3, FastAPI, React + TS + TanStack Query (Vite), pytest.

**Spec:** `docs/superpowers/specs/2026-09-28-nhieu-bang-tong-quan-design.md`

## Global Constraints

- Migration chạy bằng `postgres`; file đã chạy không sửa; chạy tay thì `INSERT` tên file vào `meta.schema_migration`.
- Tên bảng sau `strip()`: 1–40 ký tự; duy nhất theo `(nguoi_dung_id, lower(btrim(ten)))`; tối đa 20 bảng/người; không xoá bảng cuối.
- Bảng của người khác → 404 (y như không tồn tại). Chưa đăng nhập (máy không có cổng) → 403 JSON.
- Mọi bố cục qua `kome.web.bo_cuc.chuan_hoa` lúc ghi và lúc đọc. Thân > `bo_cuc.DAI_TOI_DA` → 413; không phải JSON → 415.
- `/` vẫn ≤ 9 truy vấn; cổng đăng nhập vẫn 1 lượt hỏi; `liet_ke` (màn Cài đặt) KHÔNG đọc `app.bang_tong_quan`.
- Đường ghi KHÔNG bị `_chi_doc` chặn. Không ghi `/nhat-ky`, không thêm vào `anh_chup._PHIEN_BAN`.
- Mọi đường trả JSON (kể cả thành công không có dữ liệu → `{}` 200 — `api.ts::gui` luôn gọi `r.json()`; đặc tả ghi 204, đổi thành 200 `{}` vì lý do này).
- `app.py` không nhập pandas / `kome.pipeline` ở mức ngoài cùng (mô-đun mới không nhập gì nặng).
- Sửa `giao_dien/` ⇒ `cd giao_dien && npm run build` và commit `kome/web/spa/`.
- `kome_test` dùng chung giữa các phiên: chạy pytest theo từng file khi làm, cả bộ một lần ở cuối.

---

### Task 1: Migration 056

**Files:**
- Create: `db/migrations/056_bang_tong_quan.sql`
- Test: `tests/test_bang_tong_quan.py` (mới)

**Interfaces:**
- Produces: bảng `app.bang_tong_quan(id bigserial, nguoi_dung_id bigint, ten text, bo_cuc jsonb, thu_tu int, tao_luc, sua_luc)`; chỉ mục duy nhất `bang_tong_quan_ten_uq` trên `(nguoi_dung_id, lower(btrim(ten)))`; cột `app.nguoi_dung.bang_gan_nhat bigint`. Khối chép dữ liệu nằm giữa hai dòng đánh dấu `-- CHEP: bat dau` / `-- CHEP: ket thuc`, idempotent.

- [ ] **Step 1: Viết test đỏ**

```python
"""Nhiều bảng Tổng quan có tên cho mỗi người (056, kome/web/bang_tong_quan.py).
Đặc tả: docs/superpowers/specs/2026-09-28-nhieu-bang-tong-quan-design.md"""
import json
import re
from pathlib import Path

import psycopg
import pytest

GOC = Path(__file__).resolve().parents[1]
MIG = GOC / "db" / "migrations" / "056_bang_tong_quan.sql"


def _nguoi(conn, ten, bo_cuc=None):
    from kome.web import nguoi_dung as ND
    ND.tao(conn, ten, "mat-khau-bang-2026")
    if bo_cuc is not None:
        conn.execute("UPDATE app.nguoi_dung SET bo_cuc_tong_quan = %s WHERE ten_dang_nhap = %s",
                     (json.dumps(bo_cuc), ten))
    return conn.execute("SELECT id FROM app.nguoi_dung WHERE ten_dang_nhap = %s", (ten,)).fetchone()[0]


def _khoi_chep():
    m = re.search(r"-- CHEP: bat dau\n(.*?)-- CHEP: ket thuc", MIG.read_text(encoding="utf-8"), re.S)
    assert m, "056 thiếu khối chép dữ liệu cũ"
    return m.group(1)


def test_056_chep_bo_cuc_cu_thanh_bang_cua_toi(conn):
    a = _nguoi(conn, "an", [{"id": "kpi", "rong": 1}])
    b = _nguoi(conn, "binh")                     # chưa từng sắp xếp
    conn.execute(_khoi_chep())
    conn.execute(_khoi_chep())                   # chạy lại không nhân dòng
    ds = conn.execute("SELECT nguoi_dung_id, ten, bo_cuc, thu_tu FROM app.bang_tong_quan").fetchall()
    assert [(r[0], r[1], r[3]) for r in ds] == [(a, "Bảng của tôi", 0)]
    assert ds[0][2][0]["id"] == "kpi"
    gan = dict(conn.execute("SELECT id, bang_gan_nhat FROM app.nguoi_dung").fetchall())
    assert gan[a] is not None and gan[b] is None


def test_ten_trung_khong_phan_biet_hoa_thuong_va_khoang_trang(conn):
    a = _nguoi(conn, "an")
    conn.execute("INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, thu_tu) VALUES (%s, 'Kho', 0)", (a,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute("INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, thu_tu) VALUES (%s, ' kho ', 1)", (a,))


def test_xoa_bang_gan_nhat_dat_ve_null(conn):
    a = _nguoi(conn, "an")
    bid = conn.execute("INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, thu_tu) VALUES (%s, 'X', 0) RETURNING id",
                       (a,)).fetchone()[0]
    conn.execute("UPDATE app.nguoi_dung SET bang_gan_nhat = %s WHERE id = %s", (bid, a))
    conn.execute("DELETE FROM app.bang_tong_quan WHERE id = %s", (bid,))
    assert conn.execute("SELECT bang_gan_nhat FROM app.nguoi_dung WHERE id = %s", (a,)).fetchone()[0] is None


def test_quyen_kome_app_ghi_duoc_kome_report_chi_doc(conn):
    q = lambda vai, p: conn.execute("SELECT has_table_privilege(%s, 'app.bang_tong_quan', %s)", (vai, p)).fetchone()[0]
    assert all(q("kome_app", p) for p in ("SELECT", "INSERT", "UPDATE", "DELETE"))
    assert q("kome_report", "SELECT") and not q("kome_report", "INSERT")
    assert conn.execute("SELECT has_sequence_privilege('kome_app', 'app.bang_tong_quan_id_seq', 'USAGE')").fetchone()[0]
```

- [ ] **Step 2: Chạy, thấy đỏ**

Run: `pytest tests/test_bang_tong_quan.py -v`
Expected: FAIL — `056 thiếu khối chép` / `relation "app.bang_tong_quan" does not exist`.

- [ ] **Step 3: Viết migration**

```sql
-- 056: NHIỀU bảng Tổng quan có tên cho mỗi người (thay 034: một người một bố cục).
--
-- LƯU Ý BẤT BIẾN: chạy bằng vai trò `postgres` như mọi migration.
-- Đặc tả: docs/superpowers/specs/2026-09-28-nhieu-bang-tong-quan-design.md
--
-- Mỗi dòng là một bảng RIÊNG của một người (không chia sẻ — chủ DN chốt
-- 2026-09-28). bo_cuc NULL = bố cục mặc định; nội dung luôn qua
-- kome/web/bo_cuc.py::chuan_hoa lúc ghi và lúc đọc (như 034). Quy tắc số lượng
-- (≤ 20 bảng, không xoá bảng cuối) ở kome/web/bang_tong_quan.py — CSDL chỉ canh
-- tên (độ dài + không trùng trong bảng của CÙNG người, không phân biệt hoa thường).
CREATE TABLE app.bang_tong_quan (
    id            bigserial PRIMARY KEY,
    nguoi_dung_id bigint NOT NULL REFERENCES app.nguoi_dung(id) ON DELETE CASCADE,
    ten           text   NOT NULL CHECK (length(btrim(ten)) BETWEEN 1 AND 40),
    bo_cuc        jsonb  NULL,
    thu_tu        int    NOT NULL,
    tao_luc       timestamptz NOT NULL DEFAULT now(),
    sua_luc       timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX bang_tong_quan_ten_uq ON app.bang_tong_quan (nguoi_dung_id, lower(btrim(ten)));
CREATE INDEX bang_tong_quan_nguoi_idx ON app.bang_tong_quan (nguoi_dung_id, thu_tu);

COMMENT ON TABLE app.bang_tong_quan IS
  'Bảng Tổng quan có tên của từng người (056). bo_cuc: [{id, rong 1-3, cao 1-4, an}], NULL = mặc định.';

-- Bảng xem gần nhất: CHỈ ghi khi người dùng chủ động chuyển tab / tạo bảng,
-- không ghi lúc tải trang. Xoá bảng thì về NULL (trang rơi về bảng đầu).
ALTER TABLE app.nguoi_dung
    ADD COLUMN bang_gan_nhat bigint NULL REFERENCES app.bang_tong_quan(id) ON DELETE SET NULL;

-- Quyền: 009 đã cấp mặc định cho bảng app mới; ghi lại tường minh, kể cả sequence.
GRANT SELECT, INSERT, UPDATE, DELETE ON app.bang_tong_quan TO kome_app;
GRANT USAGE ON SEQUENCE app.bang_tong_quan_id_seq TO kome_app;
GRANT SELECT ON app.bang_tong_quan TO kome_report;

-- Chép bố cục 034 thành "Bảng của tôi" — không ai mất cách xếp đang có.
-- Idempotent (NOT EXISTS) — tests/test_bang_tong_quan.py chạy lại khối này.
-- CHEP: bat dau
INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, bo_cuc, thu_tu)
SELECT n.id, 'Bảng của tôi', n.bo_cuc_tong_quan, 0
FROM app.nguoi_dung n
WHERE n.bo_cuc_tong_quan IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM app.bang_tong_quan b WHERE b.nguoi_dung_id = n.id);
UPDATE app.nguoi_dung n SET bang_gan_nhat = b.id
FROM app.bang_tong_quan b
WHERE b.nguoi_dung_id = n.id AND b.thu_tu = 0 AND n.bang_gan_nhat IS NULL;
-- CHEP: ket thuc

COMMENT ON COLUMN app.nguoi_dung.bo_cuc_tong_quan IS
  'NGỪNG DÙNG từ 056 — đã chép sang app.bang_tong_quan. Giữ làm lịch sử; không chỗ nào đọc/ghi.';
```

- [ ] **Step 4: Chạy, thấy xanh**

Run: `pytest tests/test_bang_tong_quan.py -v` (conftest tự áp migration mới)
Expected: 4 PASS. Nếu `test_migrate.py` / `test_roles.py` có danh sách bảng `app` cứng, chạy chúng và cập nhật.

- [ ] **Step 5: Commit**

```bash
git add db/migrations/056_bang_tong_quan.sql tests/test_bang_tong_quan.py
git commit -m "feat(tong-quan): migration 056 nhieu bang Tong quan co ten"
```

---

### Task 2: Mô-đun `kome/web/bang_tong_quan.py`

**Files:**
- Create: `kome/web/bang_tong_quan.py`
- Test: `tests/test_bang_tong_quan.py` (nối thêm)

**Interfaces:**
- Consumes: `kome.web.bo_cuc` (`O`, `chuan_hoa`, `mac_dinh`, `VAI_TRO`), bảng 056.
- Produces (mọi hàm nhận `conn` KHÔNG tự commit; sai quy tắc ném `LoiBang(ma, loi)`):
  - `TOI_DA = 20`, `DAI_TEN = 40`, `TEN_MAC_DINH = "Bảng của tôi"`
  - `class LoiBang(Exception)`: thuộc tính `ma: int` (404/409/422), `loi: str`
  - `@dataclass(frozen=True) class Bang: id: int | None; ten: str; bo_cuc: tuple[O, ...]` + `dict() -> {"id", "ten", "bo_cuc": [...]}`
  - `ao() -> Bang` (bảng ảo, `id=None`)
  - `chuan_ten(ten) -> str`
  - `tu_tho(tho) -> list[Bang]` (JSON thô của `json_agg` → danh sách, bỏ phần tử hỏng)
  - `chon(ds: list[Bang], tham_so: str | None, gan_nhat: int | None) -> Bang`
  - `tao(conn, nguoi_id: int, ten, tu: str) -> Bang`
  - `luu_bo_cuc(conn, nguoi_id: int, bang_id: int | None, bo_cuc: list[O] | None) -> Bang`
  - `doi_ten(conn, nguoi_id, bang_id: int, ten) -> Bang`
  - `xoa(conn, nguoi_id, bang_id: int) -> int` (id bảng hiện tiếp)
  - `mo(conn, nguoi_id, bang_id: int) -> None`
  - `sap_thu_tu(conn, nguoi_id, ids: list) -> None`

- [ ] **Step 1: Viết test đỏ** (nối vào `tests/test_bang_tong_quan.py`)

```python
from kome.web import bang_tong_quan as BT
from kome.web import bo_cuc as BC


def _ds(conn, nid):
    return conn.execute("SELECT id, ten, thu_tu FROM app.bang_tong_quan WHERE nguoi_dung_id = %s ORDER BY thu_tu",
                        (nid,)).fetchall()


def _loi(ham, *a):
    with pytest.raises(BT.LoiBang) as e:
        ham(*a)
    return e.value.ma


@pytest.mark.parametrize("ten,mong", [("  Kho  ", "Kho"), ("x" * 40, "x" * 40)])
def test_chuan_ten_cat_khoang_trang(ten, mong):
    assert BT.chuan_ten(ten) == mong


@pytest.mark.parametrize("ten", ["", "   ", "x" * 41, None, 5])
def test_chuan_ten_sai_la_422(ten):
    assert _loi(BT.chuan_ten, ten) == 422


def test_tu_tho_bo_phan_tu_hong_va_chuan_hoa_bo_cuc():
    ds = BT.tu_tho([{"id": 3, "ten": "A", "bo_cuc": [{"id": "kpi", "rong": 9}]}, {"ten": "không id"}, "rác"])
    assert [b.id for b in ds] == [3] and ds[0].bo_cuc[0] == BC.O("kpi", 3, 1)
    assert len(ds[0].bo_cuc) == len(BC.KHOI)
    assert BT.tu_tho(None) == [] and BT.tu_tho("không phải json") == []


def test_chon_theo_thu_tu_uu_tien():
    a, b = BT.Bang(1, "A", ()), BT.Bang(2, "B", ())
    assert BT.chon([a, b], "2", 1).id == 2          # ?bang= của mình
    assert BT.chon([a, b], "99", 2).id == 2         # ?bang= lạ -> gần nhất
    assert BT.chon([a, b], "x", None).id == 1       # rác, không gần nhất -> đầu
    assert BT.chon([a, b], None, 77).id == 1        # gần nhất không còn -> đầu
    assert BT.chon([], "1", 1).id is None           # không bảng nào -> ảo


def test_tao_tu_mac_dinh_vai_tro_va_chep(conn):
    a = _nguoi(conn, "an")
    m = BT.tao(conn, a, "Đầy đủ", "mac_dinh")
    assert m.bo_cuc == tuple(BC.mac_dinh())
    ma_vai, _, khoi_vai = BC.VAI_TRO[2]
    v = BT.tao(conn, a, "Kế toán", f"vai:{ma_vai}")
    assert {o.id for o in v.bo_cuc if not o.an} == set(khoi_vai)
    BT.luu_bo_cuc(conn, a, m.id, BC.chuan_hoa([{"id": "xu_huong", "rong": 1, "cao": 4}]))
    c = BT.tao(conn, a, "Bản chép", f"chep:{m.id}")
    assert c.bo_cuc[0] == BC.O("xu_huong", 1, 4)
    assert [r[2] for r in _ds(conn, a)] == [0, 1, 2]
    assert conn.execute("SELECT bang_gan_nhat FROM app.nguoi_dung WHERE id = %s", (a,)).fetchone()[0] == c.id


def test_tao_sai_quy_tac(conn):
    a, b = _nguoi(conn, "an"), _nguoi(conn, "binh")
    cua_b = BT.tao(conn, b, "Của Bình", "mac_dinh")
    BT.tao(conn, a, "Kho", "mac_dinh")
    assert _loi(BT.tao, conn, a, "  KHO ", "mac_dinh") == 409          # trùng
    assert _loi(BT.tao, conn, a, "X", "vai:khong_co") == 422
    assert _loi(BT.tao, conn, a, "X", "linh_tinh") == 422
    assert _loi(BT.tao, conn, a, "X", f"chep:{cua_b.id}") == 404       # chép bảng người khác
    for i in range(BT.TOI_DA - 1):
        BT.tao(conn, a, f"B{i}", "mac_dinh")
    assert _loi(BT.tao, conn, a, "Thừa", "mac_dinh") == 409
    assert len(_ds(conn, a)) == BT.TOI_DA


def test_bang_ao_luu_lan_dau_tao_DUNG_MOT_dong(conn):
    a = _nguoi(conn, "an")
    b1 = BT.luu_bo_cuc(conn, a, None, BC.chuan_hoa([{"id": "kpi", "rong": 1}]))
    b2 = BT.luu_bo_cuc(conn, a, None, BC.chuan_hoa([{"id": "kpi", "rong": 2}]))
    assert b1.id == b2.id and b1.ten == BT.TEN_MAC_DINH and len(_ds(conn, a)) == 1
    assert b2.bo_cuc[0].rong == 2


def test_so_huu_bang_nguoi_khac_la_404_va_khong_doi(conn):
    a, b = _nguoi(conn, "an"), _nguoi(conn, "binh")
    x = BT.tao(conn, b, "Của Bình", "mac_dinh")
    BT.tao(conn, a, "Của An", "mac_dinh")
    assert _loi(BT.luu_bo_cuc, conn, a, x.id, BC.mac_dinh()) == 404
    assert _loi(BT.doi_ten, conn, a, x.id, "Chiếm") == 404
    assert _loi(BT.xoa, conn, a, x.id) == 404
    assert _loi(BT.mo, conn, a, x.id) == 404
    assert _ds(conn, b)[0][1] == "Của Bình"


def test_doi_ten_xoa_va_bang_cuoi(conn):
    a = _nguoi(conn, "an")
    x, y = BT.tao(conn, a, "X", "mac_dinh"), BT.tao(conn, a, "Y", "mac_dinh")
    assert _loi(BT.doi_ten, conn, a, x.id, "y") == 409
    assert BT.doi_ten(conn, a, x.id, " Sáng thứ Hai ").ten == "Sáng thứ Hai"
    assert BT.doi_ten(conn, a, x.id, "sáng thứ hai").ten == "sáng thứ hai"   # đổi hoa thường chính nó: được
    BT.mo(conn, a, y.id)
    assert BT.xoa(conn, a, y.id) == x.id
    assert conn.execute("SELECT bang_gan_nhat FROM app.nguoi_dung WHERE id = %s", (a,)).fetchone()[0] is None
    assert _loi(BT.xoa, conn, a, x.id) == 409


def test_sap_thu_tu_phai_dung_tap_bang_cua_minh(conn):
    a = _nguoi(conn, "an")
    x, y, z = (BT.tao(conn, a, t, "mac_dinh") for t in "XYZ")
    BT.sap_thu_tu(conn, a, [z.id, x.id, y.id])
    assert [r[1] for r in _ds(conn, a)] == ["Z", "X", "Y"]
    assert _loi(BT.sap_thu_tu, conn, a, [z.id, x.id]) == 422
    assert _loi(BT.sap_thu_tu, conn, a, [z.id, x.id, y.id, 999]) == 422
    assert _loi(BT.sap_thu_tu, conn, a, "rác") == 422
```

- [ ] **Step 2: Chạy, thấy đỏ**

Run: `pytest tests/test_bang_tong_quan.py -v`
Expected: FAIL — `ModuleNotFoundError: kome.web.bang_tong_quan`.

- [ ] **Step 3: Viết mô-đun**

```python
"""Nhiều bảng Tổng quan có tên cho mỗi người (migration 056).

Mỗi bảng là một bố cục (kome/web/bo_cuc.py) + một tên, RIÊNG của một người
(chủ DN chốt 2026-09-28 — không chia sẻ). Mọi quy tắc sống ở đây; app.py chỉ
đọc thân yêu cầu và đổi LoiBang thành JSON. Không hàm nào tự commit.

- Mọi câu ghi có `AND nguoi_dung_id = %s`: bảng người khác -> 404, y như không
  tồn tại (không lộ là có).
- Người chưa có dòng nào có một bảng ẢO (`id=None`). Lưu bố cục lần đầu trên
  bảng ảo tạo dòng thật "Bảng của tôi" (ON CONFLICT theo tên: hai tab cùng lưu
  lần đầu vẫn ra MỘT dòng).
- `bang_gan_nhat` chỉ ghi khi người dùng CHỦ ĐỘNG chuyển tab / tạo bảng.
Đặc tả: docs/superpowers/specs/2026-09-28-nhieu-bang-tong-quan-design.md
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import psycopg

from kome.web import bo_cuc as BC

TOI_DA = 20      # chặn vòng lặp lỗi phía trình duyệt sinh hàng nghìn dòng
DAI_TEN = 40     # = CHECK của 056
TEN_MAC_DINH = "Bảng của tôi"


class LoiBang(Exception):
    def __init__(self, ma: int, loi: str):
        super().__init__(loi)
        self.ma, self.loi = ma, loi


_KHONG_THAY = LoiBang(404, "Không tìm thấy bảng này.")


@dataclass(frozen=True)
class Bang:
    id: int | None
    ten: str
    bo_cuc: tuple

    def dict(self) -> dict:
        return {"id": self.id, "ten": self.ten, "bo_cuc": [o.dict() for o in self.bo_cuc]}


def ao() -> Bang:
    return Bang(None, TEN_MAC_DINH, tuple(BC.mac_dinh()))


def chuan_ten(ten) -> str:
    t = ten.strip() if isinstance(ten, str) else ""
    if not 1 <= len(t) <= DAI_TEN:
        raise LoiBang(422, f"Tên bảng phải có 1–{DAI_TEN} ký tự.")
    return t


def tu_tho(tho) -> list[Bang]:
    """JSON thô (json_agg của cổng đăng nhập) -> danh sách bảng. Không tin gì:
    phần tử thiếu id / tên thì bỏ, bố cục qua chuan_hoa. Không bao giờ ném lỗi."""
    if isinstance(tho, (str, bytes)):
        try:
            tho = json.loads(tho)
        except ValueError:
            tho = None
    ds = []
    for x in tho if isinstance(tho, list) else []:
        if (isinstance(x, dict) and isinstance(x.get("id"), int) and not isinstance(x["id"], bool)
                and isinstance(x.get("ten"), str)):
            ds.append(Bang(x["id"], x["ten"], tuple(BC.chuan_hoa(x.get("bo_cuc")))))
    return ds


def chon(ds: list[Bang], tham_so: str | None, gan_nhat: int | None) -> Bang:
    """?bang= của mình > bảng gần nhất > bảng đầu > bảng ảo. Thuần Python."""
    theo_id = {b.id: b for b in ds}
    if isinstance(tham_so, str) and tham_so.isdigit() and int(tham_so) in theo_id:
        return theo_id[int(tham_so)]
    if gan_nhat in theo_id:
        return theo_id[gan_nhat]
    return ds[0] if ds else ao()


def _doc(conn, nguoi_id: int, bang_id) -> Bang:
    if not isinstance(bang_id, int) or isinstance(bang_id, bool):
        raise _KHONG_THAY
    r = conn.execute("SELECT id, ten, bo_cuc FROM app.bang_tong_quan WHERE id = %s AND nguoi_dung_id = %s",
                     (bang_id, nguoi_id)).fetchone()
    if r is None:
        raise _KHONG_THAY
    return Bang(r[0], r[1], tuple(BC.chuan_hoa(r[2])))


def _json(bo_cuc) -> str | None:
    return None if bo_cuc is None else json.dumps([o.dict() for o in bo_cuc])


def _xuat_phat(conn, nguoi_id: int, tu) -> list | None:
    if tu == "mac_dinh":
        return None
    if isinstance(tu, str) and tu.startswith("vai:"):
        vai = {a: set(c) for a, _, c in BC.VAI_TRO}.get(tu[4:])
        if vai is None:
            raise LoiBang(422, "Không có vai trò này.")
        return [BC.O(o.id, o.rong, o.cao, o.id not in vai) for o in BC.mac_dinh()]
    if isinstance(tu, str) and tu.startswith("chep:") and tu[5:].isdigit():
        return list(_doc(conn, nguoi_id, int(tu[5:])).bo_cuc)
    raise LoiBang(422, "Không rõ bảng mới bắt đầu từ đâu.")


def _mo(conn, nguoi_id: int, bang_id: int) -> None:
    conn.execute("UPDATE app.nguoi_dung SET bang_gan_nhat = %s WHERE id = %s", (bang_id, nguoi_id))


def _chen(conn, nguoi_id: int, ten: str, bo_cuc) -> int:
    try:
        with conn.transaction():          # savepoint: trùng tên không làm hỏng giao dịch ngoài
            return conn.execute(
                """INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, bo_cuc, thu_tu)
                   SELECT %s, %s, %s, coalesce(max(thu_tu) + 1, 0)
                   FROM app.bang_tong_quan WHERE nguoi_dung_id = %s
                   RETURNING id""", (nguoi_id, ten, _json(bo_cuc), nguoi_id)).fetchone()[0]
    except psycopg.errors.UniqueViolation:
        raise LoiBang(409, "Đã có bảng tên này.") from None


def tao(conn, nguoi_id: int, ten, tu: str) -> Bang:
    ten = chuan_ten(ten)
    bo_cuc = _xuat_phat(conn, nguoi_id, tu)
    so = conn.execute("SELECT count(*) FROM app.bang_tong_quan WHERE nguoi_dung_id = %s",
                      (nguoi_id,)).fetchone()[0]
    if so >= TOI_DA:
        raise LoiBang(409, f"Mỗi người tối đa {TOI_DA} bảng — xoá bớt một bảng trước.")
    bid = _chen(conn, nguoi_id, ten, bo_cuc)
    _mo(conn, nguoi_id, bid)
    return Bang(bid, ten, tuple(BC.chuan_hoa(None if bo_cuc is None else [o.dict() for o in bo_cuc])))


def luu_bo_cuc(conn, nguoi_id: int, bang_id: int | None, bo_cuc) -> Bang:
    """Ghi bố cục (đã chuẩn hoá; None = về mặc định). `bang_id` None = bảng ảo."""
    if bang_id is None:
        bid = conn.execute(
            """INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, bo_cuc, thu_tu)
               SELECT %s, %s, %s, coalesce(max(thu_tu) + 1, 0)
               FROM app.bang_tong_quan WHERE nguoi_dung_id = %s
               ON CONFLICT (nguoi_dung_id, lower(btrim(ten)))
               DO UPDATE SET bo_cuc = EXCLUDED.bo_cuc, sua_luc = now()
               RETURNING id""", (nguoi_id, TEN_MAC_DINH, _json(bo_cuc), nguoi_id)).fetchone()[0]
        _mo(conn, nguoi_id, bid)
        return _doc(conn, nguoi_id, bid)
    n = conn.execute("UPDATE app.bang_tong_quan SET bo_cuc = %s, sua_luc = now() WHERE id = %s AND nguoi_dung_id = %s",
                     (_json(bo_cuc), bang_id, nguoi_id)).rowcount
    if n == 0:
        raise _KHONG_THAY
    return _doc(conn, nguoi_id, bang_id)


def doi_ten(conn, nguoi_id: int, bang_id: int, ten) -> Bang:
    ten = chuan_ten(ten)
    _doc(conn, nguoi_id, bang_id)
    try:
        with conn.transaction():
            conn.execute("UPDATE app.bang_tong_quan SET ten = %s, sua_luc = now() WHERE id = %s AND nguoi_dung_id = %s",
                         (ten, bang_id, nguoi_id))
    except psycopg.errors.UniqueViolation:
        raise LoiBang(409, "Đã có bảng tên này.") from None
    return _doc(conn, nguoi_id, bang_id)


def xoa(conn, nguoi_id: int, bang_id: int) -> int:
    """Xoá; trả id bảng hiện tiếp (bảng đầu còn lại)."""
    _doc(conn, nguoi_id, bang_id)
    con = [r[0] for r in conn.execute(
        "SELECT id FROM app.bang_tong_quan WHERE nguoi_dung_id = %s AND id <> %s ORDER BY thu_tu, id",
        (nguoi_id, bang_id)).fetchall()]
    if not con:
        raise LoiBang(409, "Không xoá được bảng cuối cùng.")
    conn.execute("DELETE FROM app.bang_tong_quan WHERE id = %s AND nguoi_dung_id = %s", (bang_id, nguoi_id))
    return con[0]


def mo(conn, nguoi_id: int, bang_id: int) -> None:
    _doc(conn, nguoi_id, bang_id)
    _mo(conn, nguoi_id, bang_id)


def sap_thu_tu(conn, nguoi_id: int, ids) -> None:
    co = {r[0] for r in conn.execute("SELECT id FROM app.bang_tong_quan WHERE nguoi_dung_id = %s",
                                     (nguoi_id,)).fetchall()}
    if (not isinstance(ids, list) or len(ids) != len(co)
            or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids) or set(ids) != co):
        raise LoiBang(422, "Thứ tự phải gồm đúng các bảng của bạn.")
    for i, bid in enumerate(ids):
        conn.execute("UPDATE app.bang_tong_quan SET thu_tu = %s WHERE id = %s AND nguoi_dung_id = %s",
                     (i, bid, nguoi_id))
```

Lưu ý khi làm: nếu `conn` của fixture test không cho `conn.transaction()` lồng (psycopg 3 cho — savepoint), giữ nguyên; nếu `ON CONFLICT` không suy được chỉ mục biểu thức, dùng `ON CONFLICT ON CONSTRAINT` không được (đó là INDEX, không phải constraint) — khi đó biểu thức trong `ON CONFLICT (...)` phải viết ĐÚNG y như chỉ mục.

- [ ] **Step 4: Chạy, thấy xanh**

Run: `pytest tests/test_bang_tong_quan.py -v`
Expected: tất cả PASS.

- [ ] **Step 5: Commit**

```bash
git add kome/web/bang_tong_quan.py tests/test_bang_tong_quan.py
git commit -m "feat(tong-quan): mo-dun bang_tong_quan (tao/luu/doi ten/xoa/thu tu)"
```

---

### Task 3: Cổng đăng nhập + `window.__KOME__` + route

**Files:**
- Modify: `kome/web/nguoi_dung.py` (`_CHON`, `NguoiDung`, `_nguoi`, `liet_ke`)
- Modify: `kome/web/app.py` (`_khoi_dau` ~dòng 431–456; route `/tong-quan/bo-cuc*` ~dòng 504–545; route mới)
- Modify: `tests/test_bo_cuc.py` (đọc `bang` thay `bo_cuc`, cột DB mới)
- Test: `tests/test_bang_tong_quan.py` (nối thêm phần web)

**Interfaces:**
- Consumes: `kome.web.bang_tong_quan` (Task 2).
- Produces:
  - `NguoiDung.bang` (JSON thô, `compare=False`), `NguoiDung.bang_gan_nhat: int | None` — THAY `NguoiDung.bo_cuc`.
  - `window.__KOME__.bang: [{id, ten, bo_cuc}]` (luôn ≥ 1 phần tử; bảng ảo `id: null`), `bang_hien_id: int | null`. Khoá `bo_cuc` bỏ.
  - Route (JSON, cần đăng nhập): `POST /tong-quan/bang` → 201 `{bang}`; `POST /tong-quan/bang/{ma}/bo-cuc` (`ma` = số hoặc `moi`) → `{bang}`; `POST /tong-quan/bang/{ma}/ten` `{ten}` → `{bang}`; `POST /tong-quan/bang/{ma}/xoa` → `{bang_hien}` (id); `POST /tong-quan/bang/{ma}/mo` → `{}`; `POST /tong-quan/bang/thu-tu` `[id…]` → `{}`. Cũ: `POST /tong-quan/bo-cuc` ghi bảng đang chọn theo `chon(…, None, gan_nhat)`; form `POST /tong-quan/bo-cuc/mac-dinh` nhận trường `bang`.

- [ ] **Step 1: Viết test đỏ** (nối vào `tests/test_bang_tong_quan.py`; tái dùng fixture `web` và helper của `test_bo_cuc.py`)

```python
from tests.test_bo_cuc import _khoi_dau, web  # noqa: F401  (fixture)


def _gui(c, url, du_lieu=None):
    return c.post(url, content=json.dumps(du_lieu), headers={"Content-Type": "application/json"})


def _hien(kd):
    return next(b for b in kd["bang"] if b["id"] == kd["bang_hien_id"])


def test_nguoi_moi_thay_bang_ao_va_mo_trang_khong_ghi_gi(web, conn):
    c = web.vao(web())
    kd = _khoi_dau(c.get("/").text)
    assert kd["bang_hien_id"] is None and [b["ten"] for b in kd["bang"]] == ["Bảng của tôi"]
    assert "bo_cuc" not in kd
    assert conn.execute("SELECT count(*) FROM app.bang_tong_quan").fetchone()[0] == 0


def test_tao_chuyen_va_mo_lai_ra_bang_gan_nhat(web):
    c = web.vao(web())
    r = _gui(c, "/tong-quan/bang", {"ten": "Kho", "tu": "vai:kho"})
    assert r.status_code == 201
    kho = r.json()["bang"]
    _gui(c, "/tong-quan/bang", {"ten": "Họp", "tu": "mac_dinh"})
    assert _khoi_dau(c.get("/").text)["bang_hien_id"] != kho["id"]      # vừa tạo "Họp" -> gần nhất
    assert _gui(c, f"/tong-quan/bang/{kho['id']}/mo").json() == {}
    kd = _khoi_dau(c.get("/").text)
    assert kd["bang_hien_id"] == kho["id"] and [b["ten"] for b in kd["bang"]] == ["Kho", "Họp"]
    # ?bang= chọn thẳng nhưng KHÔNG đổi bảng gần nhất
    hop = kd["bang"][1]["id"]
    assert _khoi_dau(c.get(f"/?bang={hop}").text)["bang_hien_id"] == hop
    assert _khoi_dau(c.get("/").text)["bang_hien_id"] == kho["id"]


def test_luu_bo_cuc_bang_ao_roi_bang_that(web):
    c = web.vao(web())
    r = _gui(c, "/tong-quan/bang/moi/bo-cuc", [{"id": "han_su_dung", "rong": 3, "cao": 1}])
    assert r.status_code == 200
    bid = r.json()["bang"]["id"]
    _gui(c, f"/tong-quan/bang/{bid}/bo-cuc", [{"id": "kpi", "rong": 1, "cao": 3}])
    assert _hien(_khoi_dau(c.get("/").text))["bo_cuc"][0] == {"id": "kpi", "rong": 1, "cao": 3, "an": False}


def test_bang_nguoi_khac_la_404_qua_web(web):
    b = web.vao(web(), "binh")
    x = _gui(b, "/tong-quan/bang", {"ten": "Của Bình", "tu": "mac_dinh"}).json()["bang"]["id"]
    a = web.vao(web(), "an")
    for duong, than in [("bo-cuc", []), ("ten", {"ten": "Chiếm"}), ("xoa", None), ("mo", None)]:
        assert _gui(a, f"/tong-quan/bang/{x}/{duong}", than).status_code == 404, duong
    assert _khoi_dau(a.get(f"/?bang={x}").text)["bang_hien_id"] is None


def test_loi_quy_tac_tra_json_tieng_viet(web):
    c = web.vao(web())
    assert _gui(c, "/tong-quan/bang", {"ten": "", "tu": "mac_dinh"}).status_code == 422
    x = _gui(c, "/tong-quan/bang", {"ten": "Kho", "tu": "mac_dinh"}).json()["bang"]["id"]
    r = _gui(c, "/tong-quan/bang", {"ten": "kho", "tu": "mac_dinh"})
    assert r.status_code == 409 and r.json()["loi"] == "Đã có bảng tên này."
    assert _gui(c, f"/tong-quan/bang/{x}/xoa").status_code == 409
    assert _gui(c, "/tong-quan/bang/thu-tu", [x, 999]).status_code == 422
    assert c.post("/tong-quan/bang", data={"ten": "x"}).status_code == 415
    assert _gui(c, "/tong-quan/bang/abc/mo").status_code == 404


def test_duong_cu_bo_cuc_ghi_vao_bang_gan_nhat(web):
    c = web.vao(web())
    _gui(c, "/tong-quan/bang", {"ten": "A", "tu": "mac_dinh"})
    b = _gui(c, "/tong-quan/bang", {"ten": "B", "tu": "mac_dinh"}).json()["bang"]["id"]
    _gui(c, "/tong-quan/bo-cuc", [{"id": "tuong_quan"}])
    kd = _khoi_dau(c.get("/").text)
    assert kd["bang_hien_id"] == b and _hien(kd)["bo_cuc"][0]["id"] == "tuong_quan"


def test_khong_co_cong_dang_nhap_thi_403(web):
    c = web(bi_mat=None)
    assert _gui(c, "/tong-quan/bang", {"ten": "A", "tu": "mac_dinh"}).status_code == 403
    kd = _khoi_dau(c.get("/").text)
    assert kd["bang_hien_id"] is None and len(kd["bang"]) == 1


def test_cai_dat_khong_doc_bang_tong_quan():
    from kome.web import nguoi_dung as ND
    import inspect
    assert "bang_tong_quan" not in inspect.getsource(ND.liet_ke)
```

Sửa `tests/test_bo_cuc.py` (bộ test 034 cũ, giữ ý nghĩa, đổi nguồn):
- `_thu_tu(html)`: `kd = _khoi_dau(html); return [o["id"] for o in next(b for b in kd["bang"] if b["id"] == kd["bang_hien_id"])["bo_cuc"]]`.
- `test_luu_roi_trang_ve_SAN_...`: đọc `kd["bang"]`/`bang_hien_id` thay `kd["bo_cuc"]`; câu SQL cuối đổi thành `SELECT bo_cuc FROM app.bang_tong_quan b JOIN app.nguoi_dung n ON n.id = b.nguoi_dung_id WHERE n.ten_dang_nhap='an'`.
- `test_khoi_an_van_nam_...`: dùng `_thu_tu`-kiểu đọc bảng hiện.
- `test_ve_mac_dinh_bang_form_thuong`: gửi `data={"bang": str(id)}` (id lấy từ `bang_hien_id` sau lần lưu); câu SQL cuối kiểm `app.bang_tong_quan.bo_cuc IS NULL`.
- `test_bo_cuc_rac_trong_csdl_...`: `INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, bo_cuc, thu_tu) SELECT id, 'R', '{"la":"rac"}'::jsonb, 0 FROM app.nguoi_dung WHERE ten_dang_nhap='an'`.
- `test_ghi_bo_cuc_khong_them_truy_van_cho_trang_chu`: giữ nguyên (nay canh thêm truy vấn con `json_agg`).

- [ ] **Step 2: Chạy, thấy đỏ**

Run: `pytest tests/test_bang_tong_quan.py tests/test_bo_cuc.py -v`
Expected: FAIL — `KeyError: 'bang'` / 404 cho route mới.

- [ ] **Step 3: Sửa `kome/web/nguoi_dung.py`**

```python
# Cột dùng chung cho kiem_tra/theo_id/liet_ke. LEFT JOIN chứ không JOIN: …(giữ chú thích cũ)
_COT = """SELECT n.id, n.ten_dang_nhap, n.salesperson_code,
                 n.duoc_vao_kho_du_lieu, n.duoc_sua_ngan_sach, s.ten,
                 n.duoc_quan_tri{them}
          FROM app.nguoi_dung n
          LEFT JOIN core.dim_salesperson s
                 ON s.salesperson_code = n.salesperson_code"""
# Cổng đăng nhập kéo luôn các bảng Tổng quan (056) trong CÙNG lượt hỏi — trang chủ
# không tốn thêm truy vấn. liet_ke (màn Cài đặt) KHÔNG kéo: không cần bố cục của cả công ty.
_CHON = _COT.format(them=""",
                 n.bang_gan_nhat,
                 (SELECT json_agg(json_build_object('id', b.id, 'ten', b.ten, 'bo_cuc', b.bo_cuc)
                                  ORDER BY b.thu_tu, b.id)
                    FROM app.bang_tong_quan b WHERE b.nguoi_dung_id = n.id)""")
_CHON_GON = _COT.format(them="")
```

Trong `NguoiDung`: thay trường `bo_cuc` bằng

```python
    # Các bảng Tổng quan (056), JSON thô của json_agg — CHƯA tin được, luôn qua
    # kome.web.bang_tong_quan.tu_tho. Đọc cùng lượt hỏi của cổng đăng nhập.
    bang: object = field(default=None, compare=False, hash=False)
    bang_gan_nhat: int | None = field(default=None, compare=False, hash=False)
```

`_nguoi(r)`: `bang=r[8] if len(r) > 8 else None, bang_gan_nhat=r[7] if len(r) > 8 else None` (bỏ `bo_cuc=r[7]`). `liet_ke` dùng `_CHON_GON`; `kiem_tra`/`theo_id` giữ `_CHON`. Grep `\.bo_cuc\b` trong `kome/` và `tests/` để không sót chỗ đọc `NguoiDung.bo_cuc`.

- [ ] **Step 4: Sửa `kome/web/app.py`**

Nhập ở đầu file (cạnh `bo_cuc as BC`): `from kome.web import bang_tong_quan as BT`.

Trong `_khoi_dau`, thay dòng `"bo_cuc": …` bằng (tính trước `return`):

```python
        ds = BT.tu_tho(nguoi.bang) if nguoi else []
        hien = BT.chon(ds, request.query_params.get("bang"), nguoi.bang_gan_nhat if nguoi else None)
```

và trong dict:

```python
            "bang": [b.dict() for b in (ds or [hien])],
            "bang_hien_id": hien.id,
```

Thay khối route `/tong-quan/bo-cuc` + `/tong-quan/bo-cuc/mac-dinh` bằng:

```python
    async def _doc_json(request: Request):
        """(nguoi, thân JSON) hoặc JSONResponse lỗi. Không bị `_chi_doc` chặn —
        cùng lý lẽ `POST /ngan-sach` (CLAUDE.md)."""
        nguoi = getattr(request.state, "nguoi", None)
        if nguoi is None:
            return JSONResponse({"loi": "Máy này chưa bật đăng nhập — không biết lưu bảng cho ai."},
                                status_code=403)
        if not request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"loi": "Cần gửi JSON."}, status_code=415)
        than = await request.body()
        if len(than) > BC.DAI_TOI_DA:
            return JSONResponse({"loi": "Dữ liệu quá lớn."}, status_code=413)
        try:
            return nguoi, (json.loads(than) if than else None)
        except ValueError:
            return nguoi, None

    def _chay_bang(nguoi, viec, status_code: int = 200):
        """Chạy `viec(conn)` trong một giao dịch kome_app; LoiBang -> JSON đúng mã."""
        try:
            with open_app_conn() as conn:
                kq = viec(conn)
                conn.commit()
        except BT.LoiBang as e:
            return JSONResponse({"loi": e.loi}, status_code=e.ma)
        except Exception:
            traceback.print_exc()
            return JSONResponse({"loi": "Không lưu được bảng."}, status_code=500)
        return JSONResponse(kq, status_code=status_code)

    def _ma_bang(ma: str) -> int:
        if not ma.isdigit():
            raise BT.LoiBang(404, "Không tìm thấy bảng này.")
        return int(ma)

    @app.post("/tong-quan/bang")
    async def tao_bang(request: Request):
        kq = await _doc_json(request)
        if isinstance(kq, JSONResponse):
            return kq
        nguoi, than = kq
        than = than if isinstance(than, dict) else {}
        return _chay_bang(nguoi, lambda c: {"bang": BT.tao(c, nguoi.id, than.get("ten"), than.get("tu")).dict()},
                          status_code=201)

    @app.post("/tong-quan/bang/thu-tu")
    async def thu_tu_bang(request: Request):
        kq = await _doc_json(request)
        if isinstance(kq, JSONResponse):
            return kq
        nguoi, than = kq
        return _chay_bang(nguoi, lambda c: BT.sap_thu_tu(c, nguoi.id, than) or {})

    @app.post("/tong-quan/bang/{ma}/bo-cuc")
    async def luu_bo_cuc_bang(request: Request, ma: str):
        """Tự lưu bố cục của MỘT bảng (400 ms sau lần kéo cuối). `ma = moi` = bảng ảo."""
        kq = await _doc_json(request)
        if isinstance(kq, JSONResponse):
            return kq
        nguoi, than = kq
        bo_cuc = BC.chuan_hoa(than)
        return _chay_bang(nguoi, lambda c: {"bang": BT.luu_bo_cuc(
            c, nguoi.id, None if ma == "moi" else _ma_bang(ma), bo_cuc).dict()})

    @app.post("/tong-quan/bang/{ma}/ten")
    async def doi_ten_bang(request: Request, ma: str):
        kq = await _doc_json(request)
        if isinstance(kq, JSONResponse):
            return kq
        nguoi, than = kq
        ten = than.get("ten") if isinstance(than, dict) else None
        return _chay_bang(nguoi, lambda c: {"bang": BT.doi_ten(c, nguoi.id, _ma_bang(ma), ten).dict()})

    @app.post("/tong-quan/bang/{ma}/xoa")
    async def xoa_bang(request: Request, ma: str):
        kq = await _doc_json(request)
        if isinstance(kq, JSONResponse):
            return kq
        nguoi, _ = kq
        return _chay_bang(nguoi, lambda c: {"bang_hien": BT.xoa(c, nguoi.id, _ma_bang(ma))})

    @app.post("/tong-quan/bang/{ma}/mo")
    async def mo_bang(request: Request, ma: str):
        kq = await _doc_json(request)
        if isinstance(kq, JSONResponse):
            return kq
        nguoi, _ = kq
        return _chay_bang(nguoi, lambda c: BT.mo(c, nguoi.id, _ma_bang(ma)) or {})

    @app.post("/tong-quan/bo-cuc")
    async def luu_bo_cuc(request: Request):
        """ĐƯỜNG CŨ (trước 056) — giữ một bản đời cho tab đang mở bản build cũ lúc
        triển khai: ghi vào bảng mà `/` đang hiện (bảng gần nhất / bảng đầu / ảo).
        Xoá ở đợt sau."""
        kq = await _doc_json(request)
        if isinstance(kq, JSONResponse):
            return kq
        nguoi, than = kq
        bo_cuc = BC.chuan_hoa(than)
        bid = BT.chon(BT.tu_tho(nguoi.bang), None, nguoi.bang_gan_nhat).id
        return _chay_bang(nguoi, lambda c: {"bo_cuc": [o.dict() for o in
                                                       BT.luu_bo_cuc(c, nguoi.id, bid, bo_cuc).bo_cuc]})

    @app.post("/tong-quan/bo-cuc/mac-dinh")
    async def bo_cuc_mac_dinh(request: Request):
        """Form "Đặt lại bố cục" — chạy được không cần JavaScript. Trường `bang`
        = bảng cần đặt lại; thiếu / lạ thì bảng đang hiện."""
        nguoi = getattr(request.state, "nguoi", None)
        if nguoi is not None:
            ma = (await request.form()).get("bang")
            ds = BT.tu_tho(nguoi.bang)
            b = BT.chon(ds, ma if isinstance(ma, str) else None, nguoi.bang_gan_nhat)
            try:
                with open_app_conn() as conn:
                    BT.luu_bo_cuc(conn, nguoi.id, b.id, None)
                    conn.commit()
            except Exception as e:
                return _loi(request, "đưa bố cục về mặc định", e)
        return RedirectResponse("/", status_code=303)
```

(`json` và `traceback` đã được nhập trong `app.py` — kiểm lại; nếu chưa có `json` thì thêm `import json`.) Route `/tong-quan/bang/thu-tu` PHẢI khai TRƯỚC `/tong-quan/bang/{ma}/…` không bắt buộc (đường khác độ sâu), nhưng giữ thứ tự như trên cho dễ đọc.

- [ ] **Step 5: Chạy, thấy xanh**

Run: `pytest tests/test_bang_tong_quan.py tests/test_bo_cuc.py tests/test_api.py tests/test_tong_quan.py tests/test_bao_mat.py tests/test_nhat_ky.py -v`
Expected: PASS (`test_ban_build_khop_ma_nguon` có thể đỏ nếu `giao_dien/` đang dở — xanh lại ở Task 4). `test_trang_chu_khong_qua_9_truy_van` và `test_ghi_bo_cuc_khong_them_truy_van_cho_trang_chu` PHẢI xanh.

- [ ] **Step 6: Commit**

```bash
git add kome/web/nguoi_dung.py kome/web/app.py tests/test_bo_cuc.py tests/test_bang_tong_quan.py
git commit -m "feat(tong-quan): API nhieu bang + bang trong window.__KOME__ (0 luot hoi moi)"
```

---

### Task 4: Giao diện — thanh tab, hộp Bảng mới

**Files:**
- Modify: `giao_dien/src/khoi_dau.ts` (kiểu `KhoiDau`: bỏ `bo_cuc`, thêm `bang`, `bang_hien_id`; mặc định)
- Create: `giao_dien/src/tong_quan/ThanhBang.tsx`
- Create: `giao_dien/src/tong_quan/BangMoi.tsx`
- Modify: `giao_dien/src/tong_quan/TongQuan.tsx`
- Modify: `giao_dien/src/tong_quan/tong_quan.css`
- Build: `kome/web/spa/`

**Interfaces:**
- Consumes: `window.__KOME__.bang`, `bang_hien_id` (Task 3); route Task 3; `gui` (`api.ts`), `giuKhoang` (`khung/khoang.ts`).
- Produces: `export type BangTQ = { id: number | null; ten: string; bo_cuc: OBoCuc[] }` trong `khoi_dau.ts`.

- [ ] **Step 1: `khoi_dau.ts`**

Thay `bo_cuc: OBoCuc[];` bằng

```ts
  // Các bảng Tổng quan của người đăng nhập (056) — luôn ≥ 1; bảng ảo id = null.
  bang: BangTQ[];
  bang_hien_id: number | null;
```

thêm `export type BangTQ = { id: number | null; ten: string; bo_cuc: OBoCuc[] };` cạnh `OBoCuc`, và trong mặc định `KD`: `bang: [], bang_hien_id: null,` thay `bo_cuc: [],`.

- [ ] **Step 2: `TongQuan.tsx` — trạng thái nhiều bảng**

Thay khối trạng thái / `datBoCuc` / `vaiDang` / `apVai` / dải `.vai-tro`:

```tsx
const macDinh = (khoi: MucKhoi[]): OBoCuc[] => khoi.map(k => ({ id: k.id, rong: k.rong, cao: k.cao, an: false }));

export function TongQuan() {
  const khoi = KD.danh_muc.khoi;
  const nhanCua = useMemo(() => Object.fromEntries(khoi.map(k => [k.id, k.nhan])), [khoi]);
  const [ds, datDs] = useState<BangTQ[]>(KD.bang.length ? KD.bang : [{ id: null, ten: "Bảng của tôi", bo_cuc: macDinh(khoi) }]);
  const [hienId, datHienId] = useState<number | null>(KD.bang_hien_id);
  const hien = ds.find(b => b.id === hienId) ?? ds[0];
  const bo_cuc = hien.bo_cuc;
  const [chon, datChon] = useState(false);
  const [loiLuu, datLoiLuu] = useState("");
  const hen = useRef<{ t: number; chay?: () => Promise<void> }>({ t: 0 });

  const thayBang = (id: number | null, moi: BangTQ) => datDs(d => d.map(b => b.id === id ? moi : b));
  const luuNgay = async () => { clearTimeout(hen.current.t); const f = hen.current.chay; hen.current.chay = undefined; if (f) await f(); };

  const datBoCuc = (b: OBoCuc[]) => {
    const id = hien.id;
    thayBang(id, { ...hien, bo_cuc: b });
    if (!KD.sap_xep_duoc) return;          // máy chưa bật đăng nhập: xếp tạm, không lưu
    clearTimeout(hen.current.t);
    hen.current.chay = () => gui<{ bang: BangTQ }>(`/tong-quan/bang/${id ?? "moi"}/bo-cuc`, b)
      .then(r => { datLoiLuu(""); if (id === null) { thayBang(null, r.bang); datHienId(r.bang.id); ghiUrl(r.bang.id, true); } })
      .catch(() => datLoiLuu("Không lưu được bố cục — thử lại sau."));
    hen.current.t = window.setTimeout(() => { void luuNgay(); }, 400);
  };

  // Bảng ảo phải thành dòng thật trước mọi thao tác ⋯ / nhân bản.
  const damBaoCo = async (): Promise<BangTQ> => {
    await luuNgay();
    if (hien.id !== null) return hien;
    const r = await gui<{ bang: BangTQ }>("/tong-quan/bang/moi/bo-cuc", hien.bo_cuc);
    thayBang(null, r.bang); datHienId(r.bang.id); ghiUrl(r.bang.id, true);
    return r.bang;
  };

  const chuyen = async (id: number | null) => {
    await luuNgay();
    datHienId(id); ghiUrl(id, false);
    if (id !== null && KD.sap_xep_duoc) gui(`/tong-quan/bang/${id}/mo`, null).catch(() => {});
  };

  useEffect(() => {
    const doc = () => { const p = new URLSearchParams(location.search).get("bang"); if (p && ds.some(b => String(b.id) === p)) datHienId(+p); };
    window.addEventListener("popstate", doc);
    return () => window.removeEventListener("popstate", doc);
  }, [ds]);
  useEffect(() => { document.title = `Tổng quan · ${hien.ten}`; }, [hien.ten]);
  // …(gioTokyo / chao giữ nguyên)
```

với hàm module:

```ts
function ghiUrl(id: number | null, thay: boolean) {
  const p = new URLSearchParams(location.search);
  if (id === null) p.delete("bang"); else p.set("bang", String(id));
  const url = giuKhoang("/" + (p.toString() ? "?" + p.toString() : ""));
  if (thay) history.replaceState(null, "", url); else history.pushState(null, "", url);
}
```

JSX: bỏ `<div className="vai-tro">…</div>`; ngay dưới `tieu-de-trang` đặt

```tsx
      <ThanhBang ds={ds} hien={hien} sua_duoc={KD.sap_xep_duoc} chuyen={chuyen} damBaoCo={damBaoCo}
        datDs={datDs} datHienId={id => { datHienId(id); ghiUrl(id, true); }}
        datLai={() => datBoCuc(macDinh(khoi))} moBangMoi={() => datMoi(true)} />
```

(thêm `const [moi, datMoi] = useState(false);` và `{moi && <BangMoi hien={hien} dong={() => datMoi(false)} tao={async (ten, tu) => { await luuNgay(); const r = await gui<{ bang: BangTQ }>("/tong-quan/bang", { ten, tu: tu === "chep" ? `chep:${(await damBaoCo()).id}` : tu }); datDs(d => [...d.filter(b => b.id !== null), r.bang]); datHienId(r.bang.id); ghiUrl(r.bang.id, false); datMoi(false); }} />}`). Nút "Đặt lại bố cục" của `.thanh-bo-cuc` gọi `datBoCuc(macDinh(khoi))` như cũ. Import `ThanhBang`, `BangMoi`, `type BangTQ`, `type MucKhoi`, `giuKhoang`.

- [ ] **Step 3: `ThanhBang.tsx`**

```tsx
// Thanh tab các bảng Tổng quan của MỘT người (056) — thay dải "XEM THEO VAI TRÒ".
// Không kéo tab (lẫn với kéo khối ngay dưới, và không dùng được bằng bàn phím):
// đổi thứ tự bằng mục "Dời trái / Dời phải" trong ⋯.
import { useState } from "react";
import { gui } from "../api";
import type { BangTQ } from "../khoi_dau";

export function ThanhBang({ ds, hien, sua_duoc, chuyen, damBaoCo, datDs, datHienId, datLai, moBangMoi }: {
  ds: BangTQ[]; hien: BangTQ; sua_duoc: boolean;
  chuyen: (id: number | null) => void; damBaoCo: () => Promise<BangTQ>;
  datDs: (f: (d: BangTQ[]) => BangTQ[]) => void; datHienId: (id: number | null) => void;
  datLai: () => void; moBangMoi: () => void;
}) {
  const [menu, datMenu] = useState(false);
  const [sua, datSua] = useState<string | null>(null);
  const [loi, datLoi] = useState("");
  const i = ds.findIndex(b => b.id === hien.id);
  const LY_DO = "Máy này chưa bật đăng nhập — không lưu được bảng.";

  const lam = async (f: () => Promise<void>) => { datLoi(""); try { await f(); } catch (e: any) { datLoi(e?.message ?? "Không làm được — thử lại sau."); } };
  const doiTen = (ten: string) => lam(async () => {
    const b = await damBaoCo();
    const r = await gui<{ bang: BangTQ }>(`/tong-quan/bang/${b.id}/ten`, { ten });
    datDs(d => d.map(x => x.id === b.id ? { ...x, ten: r.bang.ten } : x)); datSua(null);
  });
  const doi = (buoc: number) => lam(async () => {
    const b = await damBaoCo();
    const moi = [...ds.filter(x => x.id !== null)];
    const j = moi.findIndex(x => x.id === b.id), k = j + buoc;
    if (k < 0 || k >= moi.length) return;
    [moi[j], moi[k]] = [moi[k], moi[j]];
    await gui("/tong-quan/bang/thu-tu", moi.map(x => x.id));
    datDs(() => moi); datMenu(false);
  });
  const xoa = () => lam(async () => {
    if (!confirm(`Xoá bảng "${hien.ten}"? Không hoàn tác được.`)) return;
    const b = await damBaoCo();
    const r = await gui<{ bang_hien: number }>(`/tong-quan/bang/${b.id}/xoa`, null);
    datDs(d => d.filter(x => x.id !== b.id)); datHienId(r.bang_hien); datMenu(false);
  });

  return (
    <div className="thanh-bang">
      <div role="tablist" aria-label="Bảng Tổng quan của bạn" className="tab-bang">
        {ds.map(b => b.id === hien.id && sua !== null
          ? <input key={String(b.id)} className="o-ten-bang" autoFocus maxLength={40} value={sua} aria-label="Tên bảng"
              onChange={e => datSua(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") doiTen(sua); if (e.key === "Escape") datSua(null); }}
              onBlur={() => datSua(null)} />
          : <button key={String(b.id)} type="button" role="tab" aria-selected={b.id === hien.id} className="chip"
              onClick={() => b.id !== hien.id && chuyen(b.id)}>{b.ten}</button>)}
      </div>
      <div className="menu-bang">
        <button type="button" className="nut-nho" aria-haspopup="menu" aria-expanded={menu}
          disabled={!sua_duoc} title={sua_duoc ? "Thao tác với bảng này" : LY_DO} onClick={() => datMenu(m => !m)}>⋯</button>
        {menu && (
          <div role="menu" className="menu-noi">
            <button role="menuitem" type="button" onClick={() => { datSua(hien.ten); datMenu(false); }}>Đổi tên</button>
            <button role="menuitem" type="button" onClick={() => { datMenu(false); moBangMoi(); }}>Nhân bản…</button>
            <button role="menuitem" type="button" disabled={i <= 0} onClick={() => doi(-1)}>← Dời trái</button>
            <button role="menuitem" type="button" disabled={i >= ds.length - 1} onClick={() => doi(1)}>Dời phải →</button>
            <button role="menuitem" type="button" onClick={() => { datLai(); datMenu(false); }}>Đặt lại bố cục</button>
            <button role="menuitem" type="button" className="giam" disabled={ds.length <= 1}
              title={ds.length <= 1 ? "Không xoá được bảng cuối cùng." : undefined} onClick={xoa}>Xoá bảng…</button>
          </div>)}
      </div>
      <button type="button" className="nut-chinh" disabled={!sua_duoc} title={sua_duoc ? undefined : LY_DO}
        onClick={moBangMoi}>＋ Bảng mới</button>
      {loi && <span className="giam phu" role="alert">{loi}</span>}
    </div>
  );
}
```

- [ ] **Step 4: `BangMoi.tsx`**

```tsx
// Hộp "Bảng mới" — chọn xuất phát: chép bảng đang xem · một vai trò (bo_cuc.VAI_TRO,
// đọc từ KD.danh_muc — không tự chép) · đầy đủ. Tên gợi ý theo lựa chọn, tự " (2)" khi trùng.
import { useState } from "react";
import { KD, type BangTQ } from "../khoi_dau";

export function BangMoi({ hien, ds, dong, tao }: {
  hien: BangTQ; ds: BangTQ[]; dong: () => void; tao: (ten: string, tu: string) => Promise<void>;
}) {
  const LUA_CHON = [
    { tu: "chep", nhan: `Chép "${hien.ten}"`, ten: `${hien.ten} (bản chép)` },
    ...KD.danh_muc.vai_tro.map(v => ({ tu: `vai:${v.id}`, nhan: v.nhan, ten: v.nhan })),
    { tu: "mac_dinh", nhan: "Đầy đủ (mặc định)", ten: "Bảng mới" },
  ];
  const khongTrung = (t: string) => {
    const co = new Set(ds.map(b => b.ten.trim().toLowerCase()));
    let x = t.slice(0, 40), n = 2;
    while (co.has(x.toLowerCase())) x = `${t.slice(0, 35)} (${n++})`;
    return x;
  };
  const [tu, datTu] = useState(LUA_CHON[0].tu);
  const [ten, datTen] = useState(khongTrung(LUA_CHON[0].ten));
  const [loi, datLoi] = useState("");
  const [dang, datDang] = useState(false);

  return (
    <div className="phu-man" role="dialog" aria-modal="true" aria-labelledby="bm-td" onClick={e => e.target === e.currentTarget && dong()}>
      <form className="hop-bang-moi" onSubmit={async e => {
        e.preventDefault(); datDang(true); datLoi("");
        try { await tao(ten.trim(), tu); } catch (x: any) { datLoi(x?.message ?? "Không tạo được bảng."); } finally { datDang(false); }
      }}>
        <h2 id="bm-td">Bảng mới</h2>
        <fieldset><legend className="nhan-nho">BẮT ĐẦU TỪ</legend>
          {LUA_CHON.map(l => (
            <label key={l.tu} className="lua-chon">
              <input type="radio" name="tu" checked={tu === l.tu} onChange={() => { datTu(l.tu); datTen(khongTrung(l.ten)); }} />
              {l.nhan}
            </label>))}
        </fieldset>
        <label className="nhan-nho" htmlFor="bm-ten">TÊN BẢNG</label>
        <input id="bm-ten" value={ten} maxLength={40} required onChange={e => datTen(e.target.value)} />
        {loi && <div className="giam phu" role="alert">{loi}</div>}
        <div className="nut-hop">
          <button type="button" className="nut-nho" onClick={dong}>Huỷ</button>
          <button type="submit" className="nut-chinh" disabled={dang || !ten.trim()}>Tạo bảng</button>
        </div>
      </form>
    </div>
  );
}
```

(Trong `TongQuan.tsx`, truyền `ds={ds}` cho `BangMoi`. Nếu kho có sẵn lớp hộp thoại `.phu-man` / `.hop` ở `BangThem` — dùng lại đúng lớp đó thay vì đặt tên mới.)

- [ ] **Step 5: CSS**

Nối vào `tong_quan.css` (dùng biến màu có sẵn, không màu cứng; bỏ luật `.vai-tro` nếu không còn ai dùng):

```css
.thanh-bang{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin:.6rem 0 .2rem}
.tab-bang{display:flex;flex-wrap:wrap;gap:.35rem}
.o-ten-bang{font:inherit;padding:.25rem .5rem;border:1px solid var(--vien);border-radius:999px;background:var(--nen);color:var(--chu)}
.menu-bang{position:relative}
.menu-noi{position:absolute;z-index:20;top:calc(100% + .25rem);left:0;min-width:11rem;display:flex;flex-direction:column;
  background:var(--nen-the,var(--nen));border:1px solid var(--vien);border-radius:.5rem;padding:.3rem;box-shadow:0 6px 20px rgb(0 0 0 / .15)}
.menu-noi button{text-align:left;background:none;border:0;padding:.4rem .6rem;border-radius:.35rem;color:inherit;font:inherit;cursor:pointer}
.menu-noi button:hover:not(:disabled){background:var(--nen-phu,rgba(127,127,127,.12))}
.menu-noi button:disabled{opacity:.45;cursor:not-allowed}
.hop-bang-moi{display:flex;flex-direction:column;gap:.6rem;min-width:min(24rem,90vw)}
.hop-bang-moi fieldset{border:0;padding:0;margin:0;display:flex;flex-direction:column;gap:.3rem}
.hop-bang-moi .nut-hop{display:flex;justify-content:flex-end;gap:.5rem}
```

(Kiểm tên biến thật trong `kome.css` — `--vien`, `--nen`, `--chu`… — và đổi cho khớp.)

- [ ] **Step 6: Build + typecheck**

Run: `cd giao_dien && npm run build`
Expected: build xong, không lỗi TS; `kome/web/spa/.nguon` đổi.
Run: `pytest tests/test_api.py::test_ban_build_khop_ma_nguon tests/test_bo_cuc.py tests/test_bang_tong_quan.py -v`
Expected: PASS.

- [ ] **Step 7: Kiểm trên trình duyệt**

Chạy dev server (preview_start theo `.claude/launch.json`), đăng nhập tài khoản test, kiểm: tạo bảng từ vai trò "Kế toán" → đúng bộ khối; đổi tên (Enter/Esc); dời trái/phải; xoá (bảng cuối mờ); chuyển tab giữ `?thang=`; tải lại ra bảng gần nhất; Back quay bảng trước; không lỗi console. Chụp màn hình làm bằng chứng.

- [ ] **Step 8: Commit**

```bash
git add giao_dien/src/khoi_dau.ts giao_dien/src/tong_quan/ kome/web/spa/
git commit -m "feat(tong-quan): thanh tab nhieu bang + hop Bang moi (vai tro thanh mau)"
```

---

### Task 5: Tài liệu + tài liệu sinh + cả bộ test

**Files:**
- Modify: `CLAUDE.md` (dòng `/` trong bảng "Các trang"; bất biến 034 → thêm bất biến 056)
- Regenerate: `kome/web/tai_lieu_sinh.json`, `kome/web/cot_dung_sinh.json`
- Modify: `docs/superpowers/specs/2026-09-28-nhieu-bang-tong-quan-design.md` (204 → 200 `{}`)

- [ ] **Step 1: CLAUDE.md** — trong ô "Việc" của dòng `/` thêm "· NHIỀU bảng có tên mỗi người (056, thanh tab; vai trò là mẫu khi tạo bảng)"; cột nguồn thêm `app.bang_tong_quan`. Đoạn "Bất biến (034, bố cục Tổng quan)" sửa câu "Lưu ở `app.nguoi_dung.bo_cuc_tong_quan`" thành trỏ sang 056, và thêm ngay sau:

```markdown
**Bất biến (056, nhiều bảng Tổng quan — chủ DN chốt 2026-09-28):** mỗi người có NHIỀU bảng có tên
(`app.bang_tong_quan`), RIÊNG từng người — không chia sẻ. Mọi quy tắc ở `kome/web/bang_tong_quan.py`
(≤ 20 bảng, tên 1–40 ký tự không trùng theo `lower(btrim)`, không xoá bảng cuối); bảng người khác →
**404**. Danh sách bảng đọc bằng truy vấn con `json_agg` trong câu cổng đăng nhập (`nguoi_dung._CHON`)
— 0 lượt hỏi mới, `/` vẫn ≤ 9; `liet_ke` (Cài đặt) KHÔNG đọc nó. Người chưa có dòng nào có bảng ẢO
(`id` null), lưu lần đầu mới tạo "Bảng của tôi". `bang_gan_nhat` CHỈ ghi khi chủ động chuyển tab / tạo
bảng — mở `/` hay `?bang=` không ghi gì. Vai trò (`bo_cuc.VAI_TRO`) là MẪU khi tạo bảng, không còn là
chip áp đè lên bảng đang xem. `app.nguoi_dung.bo_cuc_tong_quan` NGỪNG DÙNG (đã chép sang bảng mới).
`POST /tong-quan/bo-cuc` chỉ còn là đường đời cho bản build cũ. Có test canh:
`tests/test_bang_tong_quan.py`. **Migration 056 phải chạy TRƯỚC khi triển khai.**
```

- [ ] **Step 2: Sinh lại tài liệu**

Run: `python scripts/sinh_tai_lieu.py` rồi `python scripts/sinh_cot_dung.py`
Expected: hai file JSON cập nhật (nếu `sinh_cot_dung` không đổi gì cũng được).

- [ ] **Step 3: Sửa đặc tả** — §5 bảng route: `204` → `{}` (200) kèm lý do `api.ts::gui` luôn đọc JSON.

- [ ] **Step 4: Cả bộ test**

Run: `pytest -q` (chia lượt với phiên khác trên `kome_test` — xem memory)
Expected: xanh, trừ các test đã đỏ TRƯỚC thay đổi này (ghi rõ tên nếu có, ví dụ `test_nguon_dung::test_giao_dien_doc_co_tinh_nang…` chờ TabGia.tsx).

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md kome/web/tai_lieu_sinh.json kome/web/cot_dung_sinh.json docs/superpowers/specs/2026-09-28-nhieu-bang-tong-quan-design.md
git commit -m "docs: bat bien 056 nhieu bang Tong quan + sinh lai tai lieu"
```
