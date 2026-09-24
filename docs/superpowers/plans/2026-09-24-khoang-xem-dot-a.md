# Khoảng xem — đợt A (nền + Tổng quan + Báo cáo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cả website có một "khoảng xem" (Tháng mặc định · Kỳ · Khoảng) trên URL; Tổng quan và Báo cáo tính số bán hàng theo khoảng đó.

**Architecture:** `kome/khoang_xem.py` là chỗ duy nhất hiểu khoảng xem (đọc tham số → giải thành dải ngày + các dải so sánh + câu mô tả). Chỉ số theo khoảng là hàm SQL có tham số trong `mart` (migration 039). `kome/ban_khoang.py` hỏi các hàm đó và dựng dữ liệu cùng hình dạng với `kome/bao_cao.py` để giao diện dùng lại. React có một bộ chọn chung ở đầu vùng nội dung và một kho trạng thái đọc/ghi URL.

**Tech Stack:** Python 3.14 · FastAPI · psycopg 3 · Postgres (Supabase) · React 18 + TS + TanStack Query + Vite.

**Spec:** `docs/superpowers/specs/2026-09-24-khoang-xem-thang-design.md`

## Global Constraints

- Định nghĩa chỉ số CHỈ ở `mart` (migration mới 039; không sửa migration đã chạy).
- Tỷ suất = tỷ số của các tổng. Doanh thu thuần = amount − tax. Không lọc 赤伝.
- Mốc "hôm nay" = `mart.moc_thoi_gian.hom_nay`, không `current_date`.
- Nhãn ngành `coalesce(nullif(food_category_name,''),'(chưa phân loại)')` viết đúng MỘT lần (039 chuyển vào `mart.ten_nganh`).
- Khoá ảnh chụp = đường dẫn + tham số khoảng chuẩn hoá theo cú pháp (không hỏi CSDL).
- `/bao-cao` ≤ 11 truy vấn; mỗi khối Tổng quan theo khoảng = ngân sách cũ + 1 (`pham_vi`).
- Migration chạy bằng `postgres`; trên CSDL thật chỉ khi chủ DN bảo.
- Sửa `giao_dien/` ⇒ `cd giao_dien && npm run build`, commit `kome/web/spa/`.
- pytest chạy tuần tự, không hai lượt cùng lúc (CSDL test dùng chung).
- Commit kết thúc bằng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Thứ tự so sánh: `so_sanh[0]` luôn là **năm trước** (so "chính"); `so_sanh[1]` là tháng trước / khoảng liền trước (dạng Tháng / Khoảng).

---

### Task 1: `kome/khoang_xem.py`

**Files:**
- Create: `kome/khoang_xem.py`
- Test: `tests/test_khoang_xem.py`

**Interfaces — Produces:**
- `class LoiKhoang(ValueError)`
- `@dataclass(frozen=True) ThamSo(thang: str|None, ky: int|None, tu: date|None, den: date|None)` với `.loai` ('mac_dinh'|'thang'|'ky'|'khoang') và `.khoa() -> dict[str,str]`
- `doc_tham_so(thang="", ky="", tu="", den="") -> ThamSo` (raise `LoiKhoang`)
- `@dataclass(frozen=True) KyDl(company_fy:int, so_ky:int, tu:date, den:date)`
- `@dataclass(frozen=True) PhamVi(ngay_dau:date, hom_nay:date, ky:tuple[KyDl,...])` với `.ky_chua(d) -> KyDl|None`
- `pham_vi(conn) -> PhamVi|None` (1 truy vấn)
- `@dataclass(frozen=True) SoSanh(ma:str, nhan:str, tu:date, den:date, tu_nay:date, den_nay:date, co:bool)`
- `@dataclass(frozen=True) KhoangXem(loai, tu, den, nhan, mo_ta, thang:str|None, company_fy:int, so_ky:int, mac_dinh:bool, tron_thang:bool, so_sanh:tuple[SoSanh,...], ghi_chu:tuple[str,...])` với `.so_ngay`
- `giai(pv: PhamVi, ts: ThamSo) -> KhoangXem` (thuần, raise `LoiKhoang`)
- `giai_conn(conn, ts) -> KhoangXem|None` (None = kho chưa có dòng bán)

Luật (spec §1): Tháng = mùng 1 → min(cuối tháng, hôm nay); năm trước = cùng dải trừ 1 năm (29/2→28/2), riêng tháng TRỌN thì trọn tháng năm trước; tháng trước = mùng 1 → min(ngày cuối dải, cuối tháng trước), tháng trọn thì trọn tháng trước. Kỳ = [max(1/8, ngày đầu dữ liệu), min(31/7, hôm nay)]; so năm trước chỉ trên phần có dữ liệu cả hai phía (tu_nay dời tới tháng(ngày đầu)+1 năm) — cùng tập tháng với `mart.ky_cung_ky`. Khoảng = [tu, den] cắt vào dải dữ liệu; so năm trước + liền trước cùng số ngày. `co` = tháng của `tu` so sánh ≥ tháng của ngày đầu dữ liệu, và `tu_nay ≤ den_nay`.

- [ ] Step 1: viết `tests/test_khoang_xem.py` (thuần, không CSDL, trừ một test `pham_vi`):

```python
from datetime import date
import pytest
from kome import khoang_xem as KX

PV = KX.PhamVi(ngay_dau=date(2025, 3, 3), hom_nay=date(2026, 7, 24), ky=(
    KX.KyDl(2025, 6, date(2025, 3, 3), date(2025, 7, 31)),
    KX.KyDl(2026, 7, date(2025, 8, 1), date(2026, 7, 24))))

def test_mac_dinh_la_thang_cua_hom_nay_mung_1_den_hom_nay():
    k = KX.giai(PV, KX.doc_tham_so())
    assert (k.loai, k.tu, k.den, k.thang, k.mac_dinh, k.tron_thang) == \
        ("thang", date(2026, 7, 1), date(2026, 7, 24), "2026-07", True, False)
    nt, tt = k.so_sanh
    assert (nt.ma, nt.tu, nt.den, nt.co) == ("nam_truoc", date(2025, 7, 1), date(2025, 7, 24), True)
    assert (tt.ma, tt.tu, tt.den, tt.co) == ("thang_truoc", date(2026, 6, 1), date(2026, 6, 24), True)
    assert k.company_fy == 2026 and k.so_ky == 7

def test_thang_tron_so_tron_thang():
    k = KX.giai(PV, KX.doc_tham_so(thang="2026-03"))
    assert (k.tu, k.den, k.tron_thang) == (date(2026, 3, 1), date(2026, 3, 31), True)
    assert (k.so_sanh[0].tu, k.so_sanh[0].den) == (date(2025, 3, 1), date(2025, 3, 31))
    assert (k.so_sanh[1].tu, k.so_sanh[1].den) == (date(2026, 2, 1), date(2026, 2, 28))

def test_thang_do_dang_31_kep_ve_cuoi_thang_truoc():
    pv = KX.PhamVi(date(2025, 3, 3), date(2026, 3, 31), PV.ky)
    k = KX.giai(pv, KX.doc_tham_so())
    assert k.tron_thang and k.so_sanh[1].den == date(2026, 2, 28)
    pv = KX.PhamVi(date(2025, 3, 3), date(2026, 3, 30), PV.ky)
    assert KX.giai(pv, KX.doc_tham_so()).so_sanh[1].den == date(2026, 2, 28)

def test_29_2_tru_mot_nam_kep_ve_28_2():
    pv = KX.PhamVi(date(2027, 1, 5), date(2028, 2, 29), ())
    k = KX.giai(pv, KX.doc_tham_so())
    assert k.so_sanh[0].den == date(2027, 2, 28)

def test_so_vao_truoc_du_lieu_thi_khong_co():
    k = KX.giai(PV, KX.doc_tham_so(thang="2025-05"))
    assert k.so_sanh[0].co is False and k.so_sanh[1].co is True
    k = KX.giai(PV, KX.doc_tham_so(thang="2025-03"))
    assert k.so_sanh[1].co is False
    assert any("bắt đầu" in g for g in k.ghi_chu)

def test_thang_ngoai_dai_bi_tu_choi():
    with pytest.raises(KX.LoiKhoang):
        KX.giai(PV, KX.doc_tham_so(thang="2026-08"))
    with pytest.raises(KX.LoiKhoang):
        KX.giai(PV, KX.doc_tham_so(thang="2025-02"))

def test_ky_so_tren_thang_doi_chieu_nhu_ky_cung_ky():
    k = KX.giai(PV, KX.doc_tham_so(ky="2026"))
    assert (k.loai, k.tu, k.den, k.so_ky) == ("ky", date(2025, 8, 1), date(2026, 7, 24), 7)
    (s,) = k.so_sanh
    assert (s.tu_nay, s.den_nay, s.tu, s.den, s.co) == \
        (date(2026, 3, 1), date(2026, 7, 24), date(2025, 3, 1), date(2025, 7, 24), True)

def test_ky_dau_khong_co_gi_de_so():
    (s,) = KX.giai(PV, KX.doc_tham_so(ky="2025")).so_sanh
    assert s.co is False

def test_khoang_cat_vao_dai_du_lieu_va_so_lien_truoc():
    k = KX.giai(PV, KX.doc_tham_so(tu="2026-06-01", den="2026-12-31"))
    assert (k.loai, k.tu, k.den) == ("khoang", date(2026, 6, 1), date(2026, 7, 24))
    nt, lt = k.so_sanh
    assert (nt.tu, nt.den) == (date(2025, 6, 1), date(2025, 7, 24))
    assert (lt.ma, lt.tu, lt.den) == ("lien_truoc", date(2026, 4, 8), date(2026, 5, 31))
    assert (lt.den - lt.tu).days == (k.den - k.tu).days

def test_khoang_rong_sau_khi_cat_bi_tu_choi():
    with pytest.raises(KX.LoiKhoang):
        KX.giai(PV, KX.doc_tham_so(tu="2027-01-01", den="2027-02-01"))

@pytest.mark.parametrize("ts", [dict(thang="2026-13"), dict(thang="x"), dict(ky="abc"),
    dict(tu="2026-01-01"), dict(tu="2026-02-01", den="2026-01-01"),
    dict(thang="2026-07", ky="2026"), dict(tu="2026-01-01", den="2026-01-40")])
def test_tham_so_sai_bi_tu_choi(ts):
    with pytest.raises(KX.LoiKhoang):
        KX.doc_tham_so(**ts)

def test_khoa_chuan_hoa():
    assert KX.doc_tham_so().khoa() == {}
    assert KX.doc_tham_so(thang="2026-07").khoa() == {"thang": "2026-07"}
    assert KX.doc_tham_so(tu="2026-7-1", den="2026-07-05").khoa() == {"tu": "2026-07-01", "den": "2026-07-05"}

def test_mo_ta_noi_ro_so_voi_gi():
    k = KX.giai(PV, KX.doc_tham_so())
    assert k.nhan == "Tháng 7/2026"
    assert "1/7 → 24/7/2026" in k.mo_ta and "1/7 → 24/7/2025" in k.mo_ta and "1/6 → 24/6/2026" in k.mo_ta

def test_pham_vi_tu_csdl(conn, batch):
    from tests.test_phan_tich_mart import _ban
    assert KX.pham_vi(conn) is None
    _ban(conn, batch, date(2025, 7, 30), "AA01")
    _ban(conn, batch, date(2025, 8, 2), "AA01")
    pv = KX.pham_vi(conn)
    assert (pv.ngay_dau, pv.hom_nay) == (date(2025, 7, 30), date(2025, 8, 2))
    assert [(k.company_fy, k.so_ky, k.tu, k.den) for k in pv.ky] == [
        (2025, 6, date(2025, 7, 30), date(2025, 7, 31)), (2026, 7, date(2025, 8, 1), date(2025, 8, 2))]
```

- [ ] Step 2: `pytest tests/test_khoang_xem.py -q` → FAIL (module missing).
- [ ] Step 3: viết `kome/khoang_xem.py` (mã ở Task 1 của nhật ký thực thi — xem file đã commit).
- [ ] Step 4: `pytest tests/test_khoang_xem.py -q` → PASS.
- [ ] Step 5: commit `feat(khoang): kome/khoang_xem — mot cho hieu khoang xem`.

### Task 2: migration 039 — hàm khoảng trong `mart`

**Files:**
- Create: `db/migrations/039_mart_khoang.sql`
- Test: `tests/test_mart_khoang.py`

**Interfaces — Produces (SQL):** `mart.ten_nganh(text)`, `mart.dong_ban_khoang(tu,den)`, `mart.tong_khoang(tu,den) → (dt, lg, ty_suat, so_phieu, so_khach, so_dong)`, `mart.ngay_khoang(tu,den) → (ngay, dt, lg, so_phieu, so_khach)`, `mart.thang_khoang(tu,den) → (thang, tu, den, dt, lg, so_phieu, so_khach)`, `mart.sale_khoang(tu,den) → (salesperson_code, dt, lg, ty_suat, so_khach, so_phieu)`, `mart.mat_hang_khoang(tu,den) → (product_code, ten_hang, food_category_name, dt, lg, ty_suat, so_luong, so_khach)`, `mart.khach_khoang(tu,den) → (customer_code, dt, lg, ty_suat, so_phieu, so_ngay_mua, lan_cuoi)`, `mart.nganh_khoang(tu,den) → (nganh, dt, lg)`, `mart.nganh_so_sanh_khoang(tu,den,tu_dc,den_dc,tu_ss,den_ss) → (nganh, dt, lg, dt_doi_chieu, dt_cung_ky, chenh_lech, tang_truong)` (FULL JOIN), `mart.tap_trung_khoang(tu,den) → (customer_code, ten_khach, dt, thu_hang, ty_trong, luy_ke)`. `CREATE OR REPLACE VIEW mart.ban_theo_nganh_thang` gọi `mart.ten_nganh`.

Tests (bốn đẳng thức spec §2 + FULL JOIN + ngày trống + phiếu đỏ):
`test_tong_thang_tron_BANG_ban_theo_thang`, `test_thang_hien_tai_BANG_thang_den_hom_nay`,
`test_tong_ngay_va_tong_nganh_BANG_tong_khoang`, `test_ten_nganh_khop_NGANH_TRONG_va_view`,
`test_nganh_so_sanh_giu_nganh_chi_ban_ky_so_sanh`, `test_ngay_khong_ban_co_dong_0`,
`test_phieu_do_khong_bi_loc`, `test_tap_trung_khoang_luy_ke_toi_1`.

- [ ] Step 1 test · Step 2 FAIL · Step 3 migration · Step 4 PASS · Step 5 commit `feat(mart): 039 ham theo khoang ngay`.

### Task 3: `kome/ban_khoang.py` + Báo cáo theo khoảng

**Files:**
- Create: `kome/ban_khoang.py`
- Modify: `kome/bao_cao.py` (`BaoCao.so_sanh`, `SoSanhSo`, `tien_do_ngan_sach(conn, company_fy=None, thang=None)`)
- Test: `tests/test_ban_khoang.py`

**Interfaces — Produces:**
- `bao_cao.SoSanhSo(_SoCungKy)`: `ma, nhan, co, tu, den, tu_nay, den_nay, dt, lg, so_khach, dt_ck, lg_ck, so_khach_ck` (+ property tang_dt/tang_lg/tang_khach/ty_suat/ty_suat_ck/chenh_ty_suat thừa kế)
- `bao_cao.BaoCao.so_sanh: list[SoSanhSo] = []`
- `ban_khoang.tong(conn, kx) -> tuple[dict, list[SoSanhSo]]` (1 truy vấn)
- `ban_khoang.chuoi(conn, kx) -> tuple[str, list[O]]` ('ngay'|'thang', 1 truy vấn; `dt_cung_ky` = so_sanh[0] khớp theo thứ tự)
- `ban_khoang.nganh(conn, kx) -> list[NganhKy]`, `mat_hang(conn,kx) -> list[dict]`, `sale(conn,kx) -> list[dict]`, `tap_trung(conn,kx) -> TapTrung|None`, `khach(conn, kx, gioi_han) -> list[dict]`
- `ban_khoang.tinh_bao_cao(conn, kx) -> BaoCao` (dạng thang/khoang; dạng ky gọi `bao_cao.tinh_bao_cao(conn, kx.company_fy)`)

Tests: `test_bao_cao_ky_GIU_NGUYEN_so` (so với tinh_bao_cao), `test_bao_cao_thang_tong_BANG_ban_theo_thang`, `test_so_sanh_nam_truoc_va_thang_truoc`, `test_chuoi_ngay_khi_ngan_thang_khi_dai`, `test_tien_do_ngan_sach_theo_thang_chon`, `test_bao_cao_thang_khong_qua_11_truy_van`.

- [ ] Step 1 test · 2 FAIL · 3 code · 4 PASS · 5 commit.

### Task 4: API + Tổng quan theo khoảng

**Files:**
- Modify: `kome/web/api.py` (`/api/pham-vi`, `/api/bao-cao?thang|ky|tu&den`, `/api/tong-quan/{khoi}?…`, 400 cho `LoiKhoang`), `kome/khoi_tong_quan.py` (KHOI 4 phần tử: `(ham, theo_ngay, theo_sale, theo_khoang)`; `kpi`, `ngan_sach`, `theo_thang`, `xu_huong`, `hieu_suat_nganh`, `tuong_quan`, `danh_sach_khach`, `tang_truong`, `bien_loi_nhuan` nhận `kx`), `kome/web/anh_chup.py` (`lam_nong` gọi hàm 4 phần tử), `tests/test_api.py` (ngân sách +1), `tests/test_tong_quan.py`.
- Test: `tests/test_khoang_api.py`

Mỗi response theo khoảng có `"khoang": thanh_json(kx)`. Khối Tổng quan theo khoảng: khoá `tong-quan/<khoi>?<khoa khoảng>`.

- [ ] Step 1 test · 2 FAIL · 3 code · 4 PASS (+ `tests/test_api.py tests/test_tong_quan.py tests/test_bao_cao*.py`) · 5 commit.

### Task 5: Giao diện — bộ chọn chung + giữ khoảng trên URL

**Files:**
- Create: `giao_dien/src/khung/khoang.ts`, `giao_dien/src/khung/KhoangXem.tsx`
- Modify: `giao_dien/src/main.tsx` (vẽ `<KhoangXem>` theo đường dẫn, gắn bộ viết lại liên kết), `khung/khung.css`, `bao_cao/BaoCao.tsx`, `khach/loc.ts`, `san_pham/loc.ts`, `san_pham/ManSanPham.tsx`, `lien_he/LienHe.tsx`, `san_pham/KhoHang.tsx`, `cong_no/ManCongNo.tsx`, `du_bao/DuBao.tsx` (mọi `history.*State` qua `giuKhoang`), `api.ts` (`useKhoi` gắn khoảng).

`khoang.ts`: `THAM_SO = ["thang","ky","tu","den"]`, `docKhoang(search) -> Record<string,string>`, `thamSoKhoang() -> string`, `giuKhoang(url) -> string`, `datKhoang(ts)` (replaceState + phát sự kiện), `useKhoang()` (useSyncExternalStore), `ganVietLaiLienKet()`, `usePhamVi()`.

- [ ] build · xem thử · commit.

### Task 6: Giao diện — Báo cáo + khối Tổng quan theo khoảng

**Files:** `bao_cao/BaoCao.tsx` (bỏ `<select>` kỳ, đọc `khoang`, `so_sanh`, nhãn biểu đồ), `tong_quan/khoi.tsx` (kpi, xu_huong bỏ nút 7N/30N, theo_thang tô đậm, hieu_suat_nganh, tuong_quan, danh_sach_khach, tiêu đề ghi khoảng).

- [ ] build · xem thử ba dạng + mobile 375 · commit.

### Task 7: Tài liệu + toàn bộ test + merge

- `CLAUDE.md`: bảng trang (`/`, `/bao-cao`), bất biến "Khoảng xem"; `python scripts/sinh_tai_lieu.py`; full `pytest -q`; merge `--no-ff` vào master. Migration 039 lên CSDL thật + push: CHỜ chủ DN.
