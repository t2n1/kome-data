# Kỳ so sánh toàn web — Đợt 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Một kỳ so duy nhất (`?ss=truoc` / mặc định năm trước / `ss_*`), thanh chọn hai thẻ, cách vẽ chung (nét đứt · cột ma · vạch đứt) và mọi khối so được của Tổng quan đi theo kỳ đó.

**Architecture:** `kome/khoang_xem.py` chọn đúng một `SoSanh` và tính `lech_thang`; các hàm khối của `kome/khoi_tong_quan.py` đọc `so_sanh[0]` (dời cửa sổ tháng theo `lech_thang`). Giao diện: `BieuDo` thêm `cot_ma` + `so_voi`, `Spark` thêm `so_sanh`, component mới `chung/SoSanh.tsx`, thanh chọn viết lại.

**Tech Stack:** Python 3 + psycopg + Postgres (mart), React + TS + TanStack Query (Vite), pytest.

**Spec:** `docs/superpowers/specs/2026-09-28-ky-so-sanh-toan-web-design.md`

## Global Constraints

- OBC chỉ đọc; không migration mới (chỉ đọc `mart.ban_theo_thang`, `mart.sale_khoang`, `mart.tong_khoang`, `mart.ngay_khoang` đã có).
- Tỷ suất = tỷ số của các tổng. Giao diện không tự tính ngày so sánh.
- `/` ≤ 9 truy vấn; `NGAN_SACH_TRUY_VAN` của `ns_thang`/`so_sanh_sale` +1.
- Sửa `giao_dien/` ⇒ `cd giao_dien && npm run build` (bản build commit ở `kome/web/spa/`).
- Test chạy trên CSDL test cục bộ (`DATABASE_URL_TEST`), không chạy song song hai phiên pytest.

---

### Task 1: Một kỳ so trong `khoang_xem`

**Files:** Modify `kome/khoang_xem.py`, `kome/web/api.py::_ts`, `kome/ban_khoang.py` (bỏ `_ss_phu`), `kome/khoi_tong_quan.py::danh_sach_khach`. Test: `tests/test_khoang_xem.py`, `tests/test_ky_so_sanh.py`, sửa các test đọc `so_sanh[1]` (`test_ban_khoang.py`, `test_khoang_khach.py`, `test_khach_moi.py`).

**Produces:** `ThamSo.ss_ma: str|None` ('truoc'); `doc_tham_so(..., ss="")`; `SoSanh.lech_thang: int|None`; `KhoangXem.lua_chon: tuple[dict, ...]` với `{"ma", "nhan", "chon"}`; `len(kx.so_sanh) == 1` luôn.

- [ ] Test (thêm vào `tests/test_khoang_xem.py`):

```python
def test_mac_dinh_chi_MOT_phep_so_la_nam_truoc():
    k = KX.giai(PV, KX.doc_tham_so())
    assert [s.ma for s in k.so_sanh] == ["nam_truoc"] and k.so_sanh[0].lech_thang == 12
    assert [(c["ma"], c["chon"]) for c in k.lua_chon] == [("nam_truoc", True), ("thang_truoc", False)]

def test_ss_truoc_chon_thang_truoc_va_khoang_lien_truoc():
    k = KX.giai(PV, KX.doc_tham_so(ss="truoc"))
    assert [s.ma for s in k.so_sanh] == ["thang_truoc"] and k.so_sanh[0].lech_thang == 1
    k = KX.giai(PV, KX.doc_tham_so(tu="2026-06-01", den="2026-06-10", ss="truoc"))
    assert k.so_sanh[0].ma == "lien_truoc" and k.so_sanh[0].lech_thang is None

def test_dang_ky_ss_truoc_roi_ve_nam_truoc():
    k = KX.giai(PV, KX.doc_tham_so(ky="2026", ss="truoc"))
    assert [s.ma for s in k.so_sanh] == ["nam_truoc"] and k.so_sanh[0].lech_thang == 12
    assert [c["ma"] for c in k.lua_chon] == ["nam_truoc"]

def test_ss_sai_bi_tu_choi_va_khoa():
    with pytest.raises(KX.LoiKhoang):
        KX.doc_tham_so(ss="abc")
    ts = KX.doc_tham_so(thang="2026-06", ss="truoc")
    assert ts.khoa() == {"thang": "2026-06", "ss": "truoc"} and ts.chinh().khoa() == {"thang": "2026-06"}
    assert KX.doc_tham_so(ss="truoc", ss_thang="2026-03").khoa() == {"ss_thang": "2026-03"}
```

và trong `tests/test_ky_so_sanh.py`: `lech_thang` của `ss_thang` cách 3 tháng = 3; `ss_tu/ss_den` lệch ngày → None; `lua_chon` mọi `chon` false khi `tu_chon`.
- [ ] Chạy `pytest tests/test_khoang_xem.py tests/test_ky_so_sanh.py -q` → FAIL.
- [ ] Cài đặt: `_doc_mot` không đổi; `doc_tham_so` nhận `ss`, chấp nhận `""`/`"nam_truoc"`/`"truoc"` (nam_truoc chuẩn hoá thành None), bỏ khi có `ss_*`. `khoa()` thêm `"ss": "truoc"`. `giai` dựng cặp mặc định như cũ rồi `so_sanh = (cap[1],) if ts.ss_ma == "truoc" and len(cap) > 1 else (cap[0],)`; `lua_chon` từ cặp. `_so` tính `lech_thang = (tu_nay.y*12+tu_nay.m) - (tu.y*12+tu.m)` khi `tu.day == tu_nay.day` hoặc (cả hai là ngày cuối tháng), ngược lại None. `_voi_ss` giữ `lua_chon` với `chon=False`. `api._ts` truyền `q.get("ss", "")`. `ban_khoang`: `_ss_phu(kx)` → `kx.so_sanh[0]` (xoá hàm, thay 3 chỗ). `danh_sach_khach`: `ss = kx.so_sanh[0]`.
- [ ] Sửa các test cũ đọc `so_sanh[1]` thành `doc_tham_so(..., ss="truoc")` + `so_sanh[0]`.
- [ ] `pytest tests/test_khoang_xem.py tests/test_ky_so_sanh.py tests/test_ban_khoang.py tests/test_khoang_khach.py tests/test_khach_moi.py -q` → PASS. Commit.

### Task 2: Tổng quan — khối theo kỳ so (máy chủ)

**Files:** Modify `kome/khoi_tong_quan.py`; Test: `tests/test_tong_quan_ky_so.py` (mới), `tests/test_api.py::NGAN_SACH_TRUY_VAN`.

**Consumes:** Task 1. **Produces (JSON):**
- `kpi.doanh_thu.spark_ss: list[int|None]`, `doanh_thu.so_sanh` một phần tử.
- `ns_thang.duong.nhan_ss = s.nhan`; điểm `ss`/`ss_lg` = luỹ kế kỳ so (Tháng: ngày thứ i từ `s.tu`, dừng ở `s.den`; Kỳ: tháng dời `lech_thang` từ `mart.ban_theo_thang`).
- `ns_thang.nguoi[].dt_ss`, `so_sanh_sale.nguoi[].dt_ss` (`mart.sale_khoang(s.tu, s.den)`), cùng `so_sanh: {ma, nhan, co, tu, den}` ở gốc.
- `theo_thang.thang[].cung_ky` = doanh thu tháng dời `lech_thang` (tháng đang chạy dở dang = `mart.tong_khoang(s.tu, s.den).dt`), `theo_thang.so_sanh = {ma, nhan, co, lech_thang}`; `lech_thang` None → mọi `cung_ky` None.
- `khach_moi.thang[].so_khach_ss` (tháng dời `lech_thang`, None nếu không dời được).
- `bien_loi_nhuan.quy[].doanh_thu_ss/bien_gop_ss` (quý dời `lech_thang//3` khi `lech_thang % 3 == 0`), `bien_loi_nhuan.so_sanh`.

- [ ] Test (mẫu, dùng fixture `conn`, `batch` như `tests/test_khach_moi.py`):

```python
def test_moi_khoi_co_phep_so_doc_CUNG_so_sanh_0(conn, batch):
    # nạp bán 2025-06..2026-07; so tháng trước
    ts = KX.doc_tham_so(thang="2026-07", ss="truoc")
    for ma in ("kpi", "xu_huong", "theo_thang", "ns_thang", "so_sanh_sale", "khach_moi",
               "danh_sach_khach", "hieu_suat_nganh", "bien_loi_nhuan"):
        d = KTQ.KHOI[ma][0](conn, None, ts)
        assert d["khoang"].so_sanh[0].ma == "thang_truoc", ma

def test_theo_thang_doi_dung_lech_thang(conn, batch):
    # tháng 2026-06 so tháng trước: cung_ky của 2026-06 = doanh thu 2026-05 của mart.ban_theo_thang
    ...
def test_luy_ke_ky_so_tai_ngay_cuoi_bang_tong_khoang(conn, batch): ...
```
- [ ] FAIL → cài đặt → PASS; cập nhật `NGAN_SACH_TRUY_VAN` (+1 `ns_thang`, `so_sanh_sale`); `pytest tests/test_tong_quan*.py tests/test_api.py -q`. Commit.

### Task 3: Cách vẽ chung (giao diện)

**Files:** Modify `giao_dien/src/chung/BieuDo.tsx`, `giao_dien/src/chung/Khoi.tsx` (`Spark`), CSS chung; Create `giao_dien/src/chung/SoSanh.tsx`.

**Produces:** `Chuoi.kieu` thêm `"cot_ma"`; `Chuoi.so_voi?: number`; `Spark({gia_tri, so_sanh?})`; `DongSoSanh({nhan, co, nay, ss, dinh_dang?})`; `VachSoSanh({ty_le})` (vị trí % trên thanh); `MauSs` (mẫu ╌ inline).
- [ ] Cài đặt; `npx tsc --noEmit` sạch. Commit cùng Task 5.

### Task 4: Thanh chọn hai thẻ

**Files:** `giao_dien/src/khung/khoang.ts` (THAM_SO_SS thêm `ss`; kiểu `lua_chon`, `lech_thang`), `giao_dien/src/khung/KhoangXem.tsx`, CSS `.kx*`.
- [ ] Viết lại theo spec §5; chip mặc định gọi `datSoSanh(ma === "thang_truoc" || ma === "lien_truoc" ? {ss: "truoc"} : {})`.

### Task 5: Khối Tổng quan dùng cách vẽ mới

**Files:** `giao_dien/src/tong_quan/khoi.tsx`.
- [ ] KPI (DongSoSanh + Spark nét đứt), Xu hướng (`so_voi`), DuongNganSach (nhãn máy chủ), KhoiNganSach/KhoiSale (VachSoSanh + ▲▼), KhoiTheoThang (`cot_ma`, nhãn), Ngành (tiêu đề cột), KhachMoi (nét đứt), KhoiBien (`cot_ma` + nét đứt biên).
- [ ] `cd giao_dien && npm run build`; `pytest tests/test_api.py -q`; kiểm tay trên preview (ảnh chụp màn). Commit.

### Task 6: CLAUDE.md + toàn bộ test

- [ ] Sửa bất biến "Khoảng xem" (một kỳ so, `?ss=`, bỏ "phép so PHỤ"). `pytest -q` toàn bộ. Commit.
