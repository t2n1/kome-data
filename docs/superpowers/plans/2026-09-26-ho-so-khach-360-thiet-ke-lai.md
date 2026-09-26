# Thiết kế lại hồ sơ khách 360° — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đổi `/khach-hang/{mã}` từ 5 tab sang bố cục hai cột: cột trái "Việc với khách này" (dính khi cuộn), cột phải "Sức khoẻ khách" gồm 4 ô số, biểu đồ và 4 tab.

**Architecture:** Chỉ đổi giao diện React trong `giao_dien/src/khach/`. Không đổi API, mart hay migration. Logic thuần (ánh xạ hash, câu nhịp, dòng mã mua lại, kịch bản gọi) tách ra module `.ts` có test vitest. Thành phần hiển thị tách theo cột. Bản build commit vào `kome/web/spa/`.

**Tech Stack:** React 19 + TypeScript + TanStack Query, Vite 8, vitest 5, pytest (test đọc mã nguồn TSX theo nếp repo).

**Spec:** `docs/superpowers/specs/2026-09-26-ho-so-khach-360-thiet-ke-lai-design.md`

## Global Constraints

- Không sửa file nào trong `kome/`, `db/`, `config/`, trừ `kome/web/spa/` (bản build).
- Không định nghĩa chỉ số mới ở giao diện. Mọi con số đọc từ `HoSoApi`, `/khoang` và `/api/cong-no/khach/{mã}` có sẵn.
- Khối mã ở cột trái tên **"Mã đến ngày mua lại"**. Chuỗi `Nên chào` KHÔNG được xuất hiện trong `khach/HoSo*.tsx` (tên đó thuộc `/lien-he`, định nghĩa khác).
- Nhãn hạng luôn có `title="hạng theo doanh thu 12 tháng"`.
- Khách `trang_thai === "ngung_giao_dich"` (※廃業※/※取引停止※, migration 016) không bao giờ hiện khối mã hay nút kịch bản.
- Chỉ dùng token màu có sẵn của `kome.css` (`--vien`, `--vien-dam`, `--vien-phu`, `--nen-the`, `--nen-phu`, `--chu`, `--chu-nhat`, `--chu-mo`, `--do`, `--ok-vien`, `--canh-vien`, `--lien-ket`). Không thêm biến màu, không sửa `kome.css`.
- CSS mới nằm trong `giao_dien/src/khach/khach.css` với tiền tố `.hs2-`.
- Khối "sắp có" không có nút bị vô hiệu và không có ảnh hay tin nhắn mẫu.
- Mọi `history.replaceState` / điều hướng bằng JS đi qua `giuKhoang()` (bất biến Khoảng xem).
- `window.__KOME__.tinh_nang` (`TN`) quyết định ẩn/hiện công nợ. Công nợ hiện TẮT trên bản thật (`TN.cong_no = false`).
- Sửa bất cứ gì trong `giao_dien/` thì phải `cd giao_dien && npm run build` và commit `kome/web/spa/`.
- Test chạy trên `kome_test`, dùng chung với các phiên khác (xem memory `kome-test-shared`). Không ngắt pytest giữa chừng.

---

## Cấu trúc tệp

| Tệp | Trách nhiệm |
|---|---|
| `giao_dien/src/khach/ho_so_logic.ts` (mới) | Hàm thuần: `TAB_HO_SO`, `tabTuHash`, `cauNhip`, `dongMuaLai`, `laCanGoi` |
| `giao_dien/src/khach/ho_so_logic.test.ts` (mới) | vitest cho module trên |
| `giao_dien/src/khach/kich_ban.ts` (mới) | `dauKichBan`, `kichBanGoi` dùng chung cho `/lien-he` và hồ sơ |
| `giao_dien/src/khach/kich_ban.test.ts` (mới) | vitest: đầu ra của `/lien-he` không đổi một ký tự |
| `giao_dien/src/khach/KhoiSapCo.tsx` (mới) | Khối "Chưa có nguồn" (Ảnh cửa hàng, Chat Facebook) |
| `giao_dien/src/khach/HoSoViec.tsx` (mới) | Bốn khối cột trái |
| `giao_dien/src/khach/HoSoTab.tsx` | Ô số, biểu đồ, 4 tab. Bỏ `TabTongQuan`, `PhanTan`, `DongHo`, các `ChuaCo` |
| `giao_dien/src/khach/HoSo.tsx` | Khung hai cột, đầu trang, thanh tab |
| `giao_dien/src/cong_no/CongNoKhach.tsx` | Thêm `OCongNoGon` |
| `giao_dien/src/lien_he/LienHe.tsx` | `kichBan` gọi `kichBanGoi` |
| `giao_dien/src/khach/khach.css` | Kiểu `.hs2-*` |
| `tests/test_ho_so_360.py` (mới) | Canh bất biến giao diện bằng cách đọc mã nguồn |
| `tests/test_nguon_dung.py` | Bỏ mục `khach/HoSoTab.tsx: TN.bang_gia` (khối bảng giá đã bỏ) |
| `CLAUDE.md` | Dòng `/khach-hang/{mã}` của bảng trang |

---

### Task 1: Module logic thuần của hồ sơ

**Files:**
- Create: `giao_dien/src/khach/ho_so_logic.ts`
- Test: `giao_dien/src/khach/ho_so_logic.test.ts`

**Interfaces:**
- Consumes: `LichMa`, `HoSoApi` từ `./kieu`
- Produces:
  - `TAB_HO_SO: readonly (readonly [MaTabHoSo, string])[]`
  - `type MaTabHoSo = "mat_hang" | "don_hang" | "cong_no" | "ho_so"`
  - `tabTuHash(hash: string, coCongNo: boolean): MaTabHoSo`
  - `cauNhip(ty_le: number | null): string`
  - `type DongMuaLai = { ma: string; ten: string; con: number; muc: "qua" | "sap" | "xa"; nhan: string }`
  - `dongMuaLai(lich: LichMa[]): DongMuaLai[]`
  - `laCanGoi(mauTrangThai: string | undefined, nhanThang: string | undefined): boolean`

- [ ] **Step 1: Viết test hỏng**

`giao_dien/src/khach/ho_so_logic.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { cauNhip, dongMuaLai, laCanGoi, tabTuHash, TAB_HO_SO } from "./ho_so_logic";
import type { LichMa } from "./kieu";

const lm = (ma: string, con: number): LichMa => ({ ma, ten: "T" + ma, du_kien: "2026-09-01", con, nhip: 14,
  lan_cuoi: "2026-08-01", doanh_thu: 1000, tb_moi_lan: null });

describe("tabTuHash", () => {
  it("hash cũ của bản 5 tab rơi về Mặt hàng", () => {
    expect(tabTuHash("#tong_quan", true)).toBe("mat_hang");
    expect(tabTuHash("#san_pham", true)).toBe("mat_hang");
  });
  it("hash hợp lệ giữ nguyên, hash lạ về Mặt hàng", () => {
    expect(tabTuHash("#ho_so", true)).toBe("ho_so");
    expect(tabTuHash("#don_hang", false)).toBe("don_hang");
    expect(tabTuHash("#xyz", true)).toBe("mat_hang");
    expect(tabTuHash("", true)).toBe("mat_hang");
  });
  it("tab Công nợ tắt thì #cong_no về Mặt hàng", () => {
    expect(tabTuHash("#cong_no", false)).toBe("mat_hang");
    expect(tabTuHash("#cong_no", true)).toBe("cong_no");
  });
  it("đủ 4 tab đúng thứ tự", () => {
    expect(TAB_HO_SO.map(t => t[0])).toEqual(["mat_hang", "don_hang", "cong_no", "ho_so"]);
  });
});

describe("cauNhip", () => {
  it("giữ nguyên văn bốn bậc cũ của khối Nhịp mua", () => {
    expect(cauNhip(null)).toBe("Chưa đủ 3 lần mua để có nhịp — không đoán.");
    expect(cauNhip(0.5)).toBe("Vẫn trong nhịp mua thường lệ.");
    expect(cauNhip(1.5)).toBe("Đã quá ngày mua thường lệ — gọi trước khi trễ hẳn.");
    expect(cauNhip(3)).toBe("Im lặng 2–4× nhịp: quá hạn mua lại.");
    expect(cauNhip(4)).toBe("Im lặng ≥ 4× nhịp: đang mất khách.");
  });
});

describe("dongMuaLai", () => {
  it("phân mức: quá (<0), sắp (0..7), xa (>7) và in nhãn", () => {
    const r = dongMuaLai([lm("a", -12), lm("b", 0), lm("c", 7), lm("d", 20)]);
    expect(r.map(x => x.muc)).toEqual(["qua", "sap", "sap", "xa"]);
    expect(r.map(x => x.nhan)).toEqual(["quá 12 ngày", "hôm nay", "còn 7 ngày", "còn 20 ngày"]);
  });
  it("giữ thứ tự máy chủ gửi (lich đã sắp theo ngày)", () => {
    expect(dongMuaLai([lm("x", 3), lm("y", -1)]).map(d => d.ma)).toEqual(["x", "y"]);
  });
});

describe("laCanGoi", () => {
  it("đọc màu trạng thái có sẵn (MAU_TT) và nhãn tháng, không tự định nghĩa nhóm", () => {
    expect(laCanGoi("canh", "da_mua")).toBe(true);
    expect(laCanGoi("do", undefined)).toBe(true);
    expect(laCanGoi("ok", "tre")).toBe(true);
    expect(laCanGoi("ok", "da_mua")).toBe(false);
    expect(laCanGoi(undefined, undefined)).toBe(false);
  });
});
```

- [ ] **Step 2: Chạy để thấy hỏng**

Run: `cd giao_dien && npx vitest run src/khach/ho_so_logic.test.ts`
Expected: FAIL, "Failed to resolve import ./ho_so_logic".

- [ ] **Step 3: Viết mã**

`giao_dien/src/khach/ho_so_logic.ts`:

```ts
// Logic thuần của hồ sơ 360° (thiết kế lại 2026-09-26). KHÔNG định nghĩa chỉ số:
// mọi hàm chỉ đổi dạng số máy chủ đã tính (lich, ty_le_im_lang, trang_thai).
import type { LichMa } from "./kieu";

export const TAB_HO_SO = [["mat_hang", "Mặt hàng"], ["don_hang", "Đơn hàng"], ["cong_no", "Công nợ"],
  ["ho_so", "Hồ sơ và nhật ký"]] as const;
export type MaTabHoSo = typeof TAB_HO_SO[number][0];

// Hash của bản 5 tab (trước 2026-09-26) — liên kết cũ không được gãy.
const HASH_CU: Record<string, MaTabHoSo> = { tong_quan: "mat_hang", san_pham: "mat_hang" };

export function tabTuHash(hash: string, coCongNo: boolean): MaTabHoSo {
  const h = hash.replace(/^#/, "");
  if (h in HASH_CU) return HASH_CU[h];
  const co = TAB_HO_SO.some(([m]) => m === h) && (h !== "cong_no" || coCongNo);
  return co ? (h as MaTabHoSo) : "mat_hang";
}

/** Câu phân bậc nhịp — nguyên văn của khối "Nhịp mua" cũ (TabTongQuan). */
export function cauNhip(ty_le: number | null): string {
  if (ty_le == null) return "Chưa đủ 3 lần mua để có nhịp — không đoán.";
  if (ty_le < 1) return "Vẫn trong nhịp mua thường lệ.";
  if (ty_le < 2) return "Đã quá ngày mua thường lệ — gọi trước khi trễ hẳn.";
  if (ty_le < 4) return "Im lặng 2–4× nhịp: quá hạn mua lại.";
  return "Im lặng ≥ 4× nhịp: đang mất khách.";
}

export type DongMuaLai = { ma: string; ten: string; con: number; muc: "qua" | "sap" | "xa"; nhan: string };

/** Dòng của khối "Mã đến ngày mua lại" — đọc h.lich.ma (máy chủ đã tính `con`). */
export function dongMuaLai(lich: LichMa[]): DongMuaLai[] {
  return lich.map(x => ({
    ma: x.ma, ten: x.ten, con: x.con,
    muc: x.con < 0 ? "qua" : x.con <= 7 ? "sap" : "xa",
    nhan: x.con < 0 ? `quá ${-x.con} ngày` : x.con === 0 ? "hôm nay" : `còn ${x.con} ngày`,
  }));
}

/** Tiêu đề "Vì sao cần gọi" hay "Tình hình": đọc màu trạng thái đã có
 *  (DanhSach.MAU_TT: canh/do = cần gọi) và nhãn tháng 036 ('tre'). */
export function laCanGoi(mauTrangThai: string | undefined, nhanThang: string | undefined): boolean {
  return mauTrangThai === "canh" || mauTrangThai === "do" || nhanThang === "tre";
}
```

- [ ] **Step 4: Chạy để thấy qua**

Run: `cd giao_dien && npx vitest run src/khach/ho_so_logic.test.ts`
Expected: PASS (9 test).

- [ ] **Step 5: Commit**

```bash
git add giao_dien/src/khach/ho_so_logic.ts giao_dien/src/khach/ho_so_logic.test.ts
git commit -m "feat(ho-so): module logic thuan cho ho so 360 (tab, cau nhip, ma mua lai)"
```

---

### Task 2: Kịch bản gọi dùng chung

**Files:**
- Create: `giao_dien/src/khach/kich_ban.ts`
- Test: `giao_dien/src/khach/kich_ban.test.ts`
- Modify: `giao_dien/src/lien_he/LienHe.tsx:156-164` (hàm `kichBan`)

**Interfaces:**
- Produces:
  - `dauKichBan(ten: string, ma: string, dien_thoai: string | null): string`
  - `type MaKichBan = { ten: string; chi_tiet: string }`
  - `kichBanGoi(p: { dau: string; ly_do: string; tieu_de_ma: string; ma: MaKichBan[]; cuoi: { ngay: string; noi_dung: string } | null }): string`

- [ ] **Step 1: Viết test hỏng**

`giao_dien/src/khach/kich_ban.test.ts`. Chuỗi mong đợi là đầu ra của hàm `kichBan` cũ trong `LienHe.tsx` với cùng đầu vào:

```ts
import { describe, expect, it } from "vitest";
import { dauKichBan, kichBanGoi } from "./kich_ban";

describe("kichBanGoi", () => {
  it("đúng từng ký tự như kịch bản cũ của /lien-he", () => {
    const s = kichBanGoi({
      dau: dauKichBan("フォー大阪", "202301150002", "06-1234-5678"),
      ly_do: "Lý do gọi: Lâu không mua — im 34 ngày (nhịp thường 15 ngày).",
      tieu_de_ma: "Nên chào:",
      ma: [{ ten: "フォー麺", chi_tiet: "9 lần · nhịp 14 ngày · lần cuối 20 ngày trước" }],
      cuoi: { ngay: "2026-09-02", noi_dung: "Hẹn đầu tháng" },
    });
    expect(s).toBe([
      "フォー大阪 (202301150002) ☎ 06-1234-5678",
      "Lý do gọi: Lâu không mua — im 34 ngày (nhịp thường 15 ngày).",
      "Nên chào:",
      "- フォー麺 (9 lần · nhịp 14 ngày · lần cuối 20 ngày trước)",
      "Lần liên hệ trước (2026-09-02): Hẹn đầu tháng",
    ].join("\n"));
  });
  it("không có mã thì bỏ cả dòng tiêu đề, không có điện thoại thì bỏ ☎", () => {
    expect(kichBanGoi({ dau: dauKichBan("A", "1", null), ly_do: "L", tieu_de_ma: "X:", ma: [], cuoi: null }))
      .toBe("A (1)\nL");
  });
});
```

- [ ] **Step 2: Chạy để thấy hỏng**

Run: `cd giao_dien && npx vitest run src/khach/kich_ban.test.ts`
Expected: FAIL, không tìm thấy `./kich_ban`.

- [ ] **Step 3: Viết `kich_ban.ts`**

```ts
// Kịch bản gọi — văn bản thuần để dán vào LINE / Zalo / ghi chú. Dùng chung
// cho thẻ /lien-he ("Nên chào:") và hồ sơ 360° ("Mã đến ngày mua lại:") —
// hai danh sách mã KHÁC định nghĩa nên tiêu đề do bên gọi truyền vào.
export type MaKichBan = { ten: string; chi_tiet: string };

export const dauKichBan = (ten: string, ma: string, dien_thoai: string | null) =>
  `${ten} (${ma})${dien_thoai ? " ☎ " + dien_thoai : ""}`;

export function kichBanGoi(p: { dau: string; ly_do: string; tieu_de_ma: string; ma: MaKichBan[];
  cuoi: { ngay: string; noi_dung: string } | null }): string {
  const dong = [p.dau, p.ly_do];
  if (p.ma.length) dong.push(p.tieu_de_ma, ...p.ma.map(m => `- ${m.ten} (${m.chi_tiet})`));
  if (p.cuoi) dong.push(`Lần liên hệ trước (${p.cuoi.ngay}): ${p.cuoi.noi_dung}`);
  return dong.join("\n");
}
```

- [ ] **Step 4: Cho `LienHe.tsx` gọi hàm chung**

Thay thân `kichBan` ở `giao_dien/src/lien_he/LienHe.tsx:156-164` và thêm import `import { dauKichBan, kichBanGoi } from "../khach/kich_ban";`:

```ts
// Kịch bản gọi — văn bản thuần để dán vào LINE / Zalo / ghi chú (khach/kich_ban.ts).
function kichBan(t: The, gy: GoiY[], laThang: boolean): string {
  return kichBanGoi({
    dau: dauKichBan(t.ten, t.ma, t.dien_thoai),
    ly_do: laThang ? `Mua đều (${t.so_thang}/3 tháng trước), tháng này chưa có đơn.`
      : `Lý do gọi: ${t.nhan_ly_do} — im ${t.so_ngay_im_lang} ngày${t.nhip_ngay ? ` (nhịp thường ${Math.round(t.nhip_ngay)} ngày)` : ""}.`,
    tieu_de_ma: "Nên chào:", ma: gy.map(g => ({ ten: g.ten, chi_tiet: nhip(g) })), cuoi: t.cuoi,
  });
}
```

- [ ] **Step 5: Chạy test và kiểm kiểu**

Run: `cd giao_dien && npx vitest run && npx tsc -b --noEmit`
Expected: mọi test PASS, tsc không lỗi. Nếu `tsc -b --noEmit` bị từ chối vì dự án tham chiếu, chạy `npx tsc -p tsconfig.json --noEmit`.

- [ ] **Step 6: Commit**

```bash
git add giao_dien/src/khach/kich_ban.ts giao_dien/src/khach/kich_ban.test.ts giao_dien/src/lien_he/LienHe.tsx
git commit -m "refactor(lien-he): tach kich ban goi ra khach/kich_ban.ts de ho so dung chung"
```

---

### Task 3: Test canh bất biến giao diện (viết trước, sẽ đỏ tới Task 6)

**Files:**
- Create: `tests/test_ho_so_360.py`
- Modify: `tests/test_nguon_dung.py:44`

- [ ] **Step 1: Viết `tests/test_ho_so_360.py`**

```python
"""Hồ sơ khách 360° thiết kế lại (đặc tả 2026-09-26-ho-so-khach-360-thiet-ke-lai-design.md).
Canh bằng cách đọc mã nguồn TSX — cùng nếp tests/test_ban_do.py."""
from pathlib import Path

KH = Path(__file__).resolve().parents[1] / "giao_dien" / "src" / "khach"


def _doc(ten: str) -> str:
    return (KH / ten).read_text(encoding="utf-8")


def test_khoi_ma_cot_trai_KHONG_mang_ten_Nen_chao_cua_lien_he():
    """'Nên chào' của /lien-he là 3 mã mua nhiều lần nhất (LH.CACH_TINH_GOI_Y);
    khối hồ sơ đọc lich (ngày mua lại dự kiến). Hai định nghĩa, hai tên."""
    for f in ("HoSo.tsx", "HoSoViec.tsx", "HoSoTab.tsx"):
        assert "Nên chào" not in _doc(f), f
    assert "Mã đến ngày mua lại" in _doc("HoSoViec.tsx")


def test_khach_ngung_giao_dich_khong_co_khoi_ma_hay_kich_ban():
    v = _doc("HoSoViec.tsx")
    assert '"ngung_giao_dich"' in v


def test_khoi_khong_nguon_da_bo_va_hai_khoi_sap_co_con():
    tab = _doc("HoSoTab.tsx")
    for bo in ("PhanTan", "DongHo", "Gợi ý tiếp khách", "Tạo đơn nháp", "Bảng giá của bậc"):
        assert bo not in tab, bo
    assert "Ảnh cửa hàng" in tab and "Chat Facebook" in tab and "KhoiSapCo" in tab
    sc = _doc("KhoiSapCo.tsx")
    assert "Chưa có nguồn" in sc and "disabled" not in sc


def test_hash_cu_va_loi_tx_van_duoc_xu_ly():
    hs = _doc("HoSo.tsx")
    assert "tabTuHash" in hs and 'get("loi_tx")' in hs
    assert "TN.cong_no" in hs


def test_nhan_hang_noi_ro_la_hang_theo_doanh_thu():
    assert 'title="hạng theo doanh thu 12 tháng"' in _doc("HoSo.tsx")
```

- [ ] **Step 2: Sửa `tests/test_nguon_dung.py:44`**

Bỏ mục `"khach/HoSoTab.tsx": "TN.bang_gia"` khỏi dict. Khối "Bảng giá của bậc" đã bỏ khỏi hồ sơ, nên hồ sơ không còn gì đọc cờ đó. Giá theo bậc vẫn ở `san_pham/HoSoSanPham.tsx` và mục đó giữ nguyên. Dòng mới:

```python
    for f, dau_hieu in {"khung/muc.ts": "TN.cong_no", "tong_quan/khoi.tsx": "TN.cong_no && <OKpiCongNo",
                        "khach/HoSo.tsx": "TN.cong_no",
                        "khach/DanhSach.tsx": "TN.cong_no", "san_pham/HoSoSanPham.tsx": "TN.bang_gia"}.items():
```

- [ ] **Step 3: Chạy để thấy đỏ đúng chỗ**

Run: `pytest tests/test_ho_so_360.py tests/test_nguon_dung.py -v`
Expected: `test_nguon_dung` PASS. `test_ho_so_360` FAIL vì chưa có `HoSoViec.tsx` / `KhoiSapCo.tsx`. Đó là đích của Task 4–6.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ho_so_360.py tests/test_nguon_dung.py
git commit -m "test(ho-so): canh bat bien ho so 360 thiet ke lai (do toi Task 6)"
```

---

### Task 4: Khối "sắp có" và nút "Cách tính"

**Files:**
- Create: `giao_dien/src/khach/KhoiSapCo.tsx`
- Modify: `giao_dien/src/khach/HoSoTab.tsx:45-53` (thành phần `The`)
- Modify: `giao_dien/src/khach/khach.css` (thêm cuối tệp)

**Interfaces:**
- Produces:
  - `KhoiSapCo({ tieu_de, icon, hinh, cong_dung, can }: { tieu_de: string; icon: string; hinh: "anh" | "chat"; cong_dung: string; can: string })`
  - `The` nhận thêm `cach_tinh?: React.ReactNode` (ẩn sau nút) bên cạnh `phu` (luôn hiện). `The` được `export` để `HoSoViec.tsx` dùng.

- [ ] **Step 1: Viết `KhoiSapCo.tsx`**

```tsx
// Khối "sắp có" — chỗ dành cho nguồn CHƯA có (ảnh cửa hàng, chat Facebook).
// Hình rỗng nét đứt cho biết khối sẽ trông thế nào; KHÔNG ảnh / tin nhắn mẫu
// (không ai được tưởng là dữ liệu thật) và KHÔNG nút vô hiệu.
export function KhoiSapCo({ tieu_de, icon, hinh, cong_dung, can }: {
  tieu_de: string; icon: string; hinh: "anh" | "chat"; cong_dung: string; can: string;
}) {
  return (
    <section className="kh-the hs2-sap-co">
      <div className="kh-the-dau"><h2><span aria-hidden="true">{icon}</span> {tieu_de}</h2>
        <span className="hs2-nhan-sap-co">Chưa có nguồn</span></div>
      <div className={"hs2-hinh-rong " + hinh} aria-hidden="true">
        {hinh === "anh" ? <><i /><i /><i /></> : <><i /><i className="phai" /><i /></>}
      </div>
      <p className="hs2-cong-dung">{cong_dung}</p>
      <p className="hs2-can">Cần để bật: {can}</p>
    </section>);
}
```

- [ ] **Step 2: Thêm `cach_tinh` vào `The` và export nó**

Thay `function The(...)` ở `HoSoTab.tsx:45-53` và nhớ thêm `useState` vào import từ `react` nếu chưa có:

```tsx
export function The({ tieu_de, phu, cach_tinh, goc, children, className = "" }: { tieu_de: string; phu?: React.ReactNode;
  cach_tinh?: React.ReactNode; goc?: React.ReactNode; children: React.ReactNode; className?: string }) {
  const [mo, datMo] = useState(false);
  return (
    <section className={"kh-the " + className}>
      <div className="kh-the-dau"><h2>{tieu_de}</h2>
        {(goc || cach_tinh) && <span className="kh-the-goc">{goc}
          {cach_tinh && <button type="button" className="hs2-cach-tinh" aria-expanded={mo} onClick={() => datMo(x => !x)}>Cách tính</button>}</span>}</div>
      {phu && <p className="phu kh-the-phu">{phu}</p>}
      {cach_tinh && mo && <p className="phu kh-the-phu hs2-cach-tinh-noi">{cach_tinh}</p>}
      {children}
    </section>);
}
```

- [ ] **Step 3: Thêm CSS vào cuối `khach.css`**

```css
/* ===== Hồ sơ 360° thiết kế lại (2026-09-26) — tiền tố .hs2- ===== */
.hs2-cach-tinh{font:inherit;font-size:.7rem;font-weight:500;margin-left:.5rem;padding:.1rem .45rem;border:1px solid var(--vien);
  border-radius:6px;background:transparent;color:var(--chu-nhat);cursor:pointer}
.hs2-cach-tinh[aria-expanded="true"]{background:var(--nen-phu);color:var(--chu)}
.hs2-cach-tinh-noi{background:var(--nen-phu);border-radius:8px;padding:.45rem .6rem}
.hs2-sap-co .kh-the-dau{margin-bottom:.6rem}
.hs2-nhan-sap-co{margin-left:auto;font-size:.7rem;padding:.1rem .5rem;border-radius:6px;background:var(--nen-phu);color:var(--chu-nhat)}
.hs2-hinh-rong{border:1px dashed var(--vien-dam);border-radius:8px;padding:.75rem;margin-bottom:.6rem;display:grid;gap:.4rem}
.hs2-hinh-rong.anh{grid-template-columns:repeat(3,minmax(0,1fr))}
.hs2-hinh-rong.anh i{display:block;aspect-ratio:1;border:1px dashed var(--vien-dam);border-radius:6px}
.hs2-hinh-rong.chat i{display:block;height:.7rem;width:58%;border:1px dashed var(--vien-dam);border-radius:6px}
.hs2-hinh-rong.chat i.phai{margin-left:auto;width:44%}
.hs2-cong-dung{font-size:.8rem;margin:0;line-height:1.5;color:var(--chu-nhat)}
.hs2-can{font-size:.72rem;margin:.6rem 0 0;padding-top:.5rem;border-top:1px solid var(--vien-phu);color:var(--chu-nhat)}
```

- [ ] **Step 4: Kiểm kiểu**

Run: `cd giao_dien && npx tsc -p tsconfig.json --noEmit`
Expected: không lỗi.

- [ ] **Step 5: Commit**

```bash
git add giao_dien/src/khach/KhoiSapCo.tsx giao_dien/src/khach/HoSoTab.tsx giao_dien/src/khach/khach.css
git commit -m "feat(ho-so): khoi 'sap co' va nut 'Cach tinh' cho the ho so"
```

---

### Task 5: Cột trái "Việc với khách này"

**Files:**
- Create: `giao_dien/src/khach/HoSoViec.tsx`
- Modify: `giao_dien/src/cong_no/CongNoKhach.tsx` (thêm `OCongNoGon` sau `OCongNo`)
- Modify: `giao_dien/src/khach/khach.css`

**Interfaces:**
- Consumes: `cauNhip`, `dongMuaLai`, `laCanGoi` (Task 1) · `dauKichBan`, `kichBanGoi` (Task 2) · `The` (Task 4) · `GhiTiepXuc` · `useCongNoKhach` (đã có trong `CongNoKhach.tsx`) · `MAU_TT` từ `./DanhSach`
- Produces:
  - `HoSoViec({ h, moGhi, datMoGhi }: { h: HoSoApi; moGhi: boolean; datMoGhi: (v: boolean) => void })`. `HoSo.tsx` giữ state `moGhi` để nút "Ghi liên hệ" ở đầu trang mở được ô ghi nhanh.
  - `OCongNoGon({ ma }: { ma: string })`
  - Hằng id DOM `ID_GHI_NHANH = "ghi-tx-nhanh"` (export)

- [ ] **Step 1: Thêm `OCongNoGon` vào `CongNoKhach.tsx`**

Thêm ngay sau hàm `OCongNo`. Hàm dùng cùng hook và cùng ba câu trạng thái:

```tsx
/** Công nợ ở cột trái hồ sơ 360° (2026-09-26) — cùng hook, cùng ba câu trạng thái với OCongNo. */
export function OCongNoGon({ ma }: { ma: string }) {
  const { data: d } = useCongNoKhach(ma);
  const tieu_de = <h2>Công nợ{d?.ben && !d.la_chinh ? " (bên nhận HĐ)" : ""}</h2>;
  if (!d) return <section className="kh-the hs2-viec">{tieu_de}<p className="phu">…</p></section>;
  if (!d.co_so) return <section className="kh-the hs2-viec">{tieu_de}<p className="phu">Chưa nạp sổ công nợ.</p></section>;
  if (!d.ben || !d.tq) return <section className="kh-the hs2-viec">{tieu_de}<p className="phu">Bên nhận hoá đơn không có trong sổ.</p></section>;
  return (
    <section className="kh-the hs2-viec">{tieu_de}
      <a className="hs2-dong" href={`/cong-no?tim=${encodeURIComponent(d.ben_ma)}`}>
        <span>Quá hạn</span><b className={d.tq.qua_han ? "giam" : ""}>{gon(d.tq.qua_han)}</b></a>
      <div className="hs2-dong phu"><span>Dư nợ {gon(d.ben.so_du)} · đến {ngay(d.ben.ky_den)}</span></div>
    </section>);
}
```

- [ ] **Step 2: Viết `HoSoViec.tsx`**

```tsx
// Cột trái của hồ sơ 360° — "Việc với khách này" (đặc tả 2026-09-26 §4).
// Không định nghĩa chỉ số: câu lý do là dien_giai của máy chủ, mã đọc h.lich.
import { useState } from "react";
import { ngay } from "../dinh_dang";
import type { HoSoApi } from "./kieu";
import { MAU_TT } from "./DanhSach";
import { GhiTiepXuc } from "./GhiTiepXuc";
import { OCongNoGon } from "../cong_no/CongNoKhach";
import { The } from "./HoSoTab";
import { cauNhip, dongMuaLai, laCanGoi } from "./ho_so_logic";
import { dauKichBan, kichBanGoi } from "./kich_ban";
import { TN } from "../khoi_dau";

export const ID_GHI_NHANH = "ghi-tx-nhanh";

export function HoSoViec({ h, moGhi, datMoGhi }: { h: HoSoApi; moGhi: boolean; datMoGhi: (v: boolean) => void }) {
  const k = h.khach, mau = MAU_TT[k.trang_thai] ?? "nhat";
  const ngung = k.trang_thai === "ngung_giao_dich";
  return (
    <aside className="hs2-trai" aria-label="Việc với khách này">
      {ngung ? (
        <section className={"kh-the hs2-ly-do nhat"}>
          <h2>Tình hình</h2>
          <p>Khách đã ngừng giao dịch{k.dau_hieu_obc ? ` (※${k.dau_hieu_obc}※)` : ""} — không gọi.</p>
        </section>
      ) : (
        <section className={"kh-the hs2-ly-do " + mau}>
          <h2>{laCanGoi(mau, h.thang_nay?.nhan) ? "Vì sao cần gọi" : "Tình hình"}</h2>
          <p>{h.dien_giai || "Không có gì bất thường."}</p>
          <p className="phu">{cauNhip(k.ty_le_im_lang)}</p>
        </section>)}
      {!ngung && <MaMuaLai h={h} />}
      <LanTruoc h={h} moGhi={moGhi} datMoGhi={datMoGhi} />
      {TN.cong_no && <OCongNoGon ma={k.ma} />}
    </aside>);
}

function MaMuaLai({ h }: { h: HoSoApi }) {
  const ds = dongMuaLai(h.lich.ma);
  const [daChep, datDaChep] = useState(false);
  const ban = () => kichBanGoi({
    dau: dauKichBan(h.khach.ten, h.khach.ma, h.khach.dien_thoai),
    ly_do: h.dien_giai || "Đang mua đều.",
    tieu_de_ma: "Mã đến ngày mua lại:",
    ma: ds.filter(d => d.muc === "qua").map(d => ({ ten: d.ten, chi_tiet: d.nhan })),
    cuoi: h.nhat_ky[0] ? { ngay: h.nhat_ky[0].ngay, noi_dung: h.nhat_ky[0].noi_dung } : null,
  });
  const chep = async () => {
    try { await navigator.clipboard.writeText(ban()); datDaChep(true); setTimeout(() => datDaChep(false), 1800); }
    catch { window.prompt("Chép kịch bản:", ban()); }
  };
  const moNgung = () => { location.hash = "mat_hang"; setTimeout(() => document.getElementById("da-ngung-mua")?.scrollIntoView({ behavior: "smooth" }), 50); };
  return (
    <The tieu_de="Mã đến ngày mua lại" className="hs2-viec"
      goc={h.lich.tong ? <span className={h.lich.so_tre ? "giam" : "tang"}>{h.lich.so_tre}/{h.lich.tong} đã quá</span> : null}
      cach_tinh="ngày dự kiến = lần mua cuối + nhịp mua riêng của cặp khách–mã · 10 mã gần ngày nhất">
      {!ds.length ? <p className="phu">Chưa mã nào đủ 3 lần mua để có nhịp riêng.</p> :
        <ul className="hs2-ds">{ds.map(d => (
          <li key={d.ma} className="hs2-dong"><a className="ten-jp" href={`/san-pham/${encodeURIComponent(d.ma)}`}>{d.ten}</a>
            <b className={d.muc === "qua" ? "giam" : d.muc === "sap" ? "canh-chu" : "nhat-chu"}>{d.nhan}</b></li>))}</ul>}
      {h.da_ngung_mua.length > 0 && <button type="button" className="hs2-lien-ket" onClick={moNgung}>
        + {h.da_ngung_mua.length} mã đã ngừng mua — xem ›</button>}
      <button type="button" className="nut-nho hs2-rong" onClick={chep}>{daChep ? "✓ Đã chép" : "📋 Chép kịch bản gọi"}</button>
    </The>);
}

function LanTruoc({ h, moGhi, datMoGhi }: { h: HoSoApi; moGhi: boolean; datMoGhi: (v: boolean) => void }) {
  const n = h.nhat_ky[0];
  return (
    <section className="kh-the hs2-viec">
      <h2>Lần liên hệ trước</h2>
      {n ? <div className="hs2-lan-truoc">
        <div>{n.icon} {n.nhan_kieu} · {ngay(n.ngay)} <span className={"nhan-vien " + n.mau_ket_qua}>{n.nhan_ket_qua}</span>
          {n.hen_lai && <span className="phu"> · hẹn {ngay(n.hen_lai)}</span>}</div>
        <p>{n.noi_dung}</p>{n.nguoi && <span className="phu">— {n.nguoi}</span>}</div>
        : <p className="phu">Chưa ghi lần tiếp xúc nào.</p>}
      <button type="button" className="hs2-lien-ket" aria-expanded={moGhi} onClick={() => datMoGhi(!moGhi)}>
        {moGhi ? "Đóng ▴" : "Ghi nhanh ▾"}</button>
      {moGhi && <GhiTiepXuc ma={h.khach.ma} kieu_tx={h.kieu_tx} ket_qua_tx={h.ket_qua_tx} gon id={ID_GHI_NHANH}
        lam_moi={[["kh-ho-so", h.khach.ma]]} xong={() => datMoGhi(false)} />}
    </section>);
}
```

**Lưu ý về `location.hash = "mat_hang"`:** gán hash KHÔNG bắn `replaceState` nên không vi phạm `giuKhoang` (query giữ nguyên). `HoSo.tsx` (Task 6) nghe sự kiện `hashchange` để đổi tab.

- [ ] **Step 3: Thêm CSS cột trái vào `khach.css`**

```css
.hs2-trai{display:flex;flex-direction:column;gap:.75rem;min-width:0}
.hs2-trai .kh-the > h2{margin:0 0 .45rem;font-size:.8rem;font-weight:600;color:var(--chu-nhat)}
.hs2-ly-do{border-left:3px solid var(--vien-dam);border-radius:0 12px 12px 0}
.hs2-ly-do.canh{border-left-color:var(--canh-vien)} .hs2-ly-do.do{border-left-color:var(--do)}
.hs2-ly-do.ok{border-left-color:var(--ok-vien)}
.hs2-ly-do p{margin:0 0 .35rem;font-size:.86rem;line-height:1.5}
.hs2-ds{list-style:none;margin:0;padding:0}
.hs2-dong{display:flex;justify-content:space-between;gap:.6rem;font-size:.8rem;padding:.3rem 0;border-top:1px solid var(--vien-phu);
  color:var(--chu);text-decoration:none;font-variant-numeric:tabular-nums}
.hs2-dong:first-child{border-top:0}
.hs2-dong > a{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hs2-dong b{flex-shrink:0;font-weight:600}
.hs2-lien-ket{font:inherit;font-size:.76rem;background:none;border:0;padding:.35rem 0 0;color:var(--lien-ket);cursor:pointer;text-align:left}
.hs2-rong{width:100%;margin-top:.6rem}
.hs2-lan-truoc{font-size:.8rem}
.hs2-lan-truoc p{margin:.3rem 0;line-height:1.5}
```

- [ ] **Step 4: Kiểm kiểu và test**

Run: `cd giao_dien && npx tsc -p tsconfig.json --noEmit && npx vitest run`
Expected: không lỗi, vitest PASS.

- [ ] **Step 5: Commit**

```bash
git add giao_dien/src/khach/HoSoViec.tsx giao_dien/src/cong_no/CongNoKhach.tsx giao_dien/src/khach/khach.css
git commit -m "feat(ho-so): cot trai 'Viec voi khach nay' (ly do, ma den ngay mua lai, lan truoc, cong no)"
```

---

### Task 6: Cột phải, 4 tab và khung hai cột

**Files:**
- Modify: `giao_dien/src/khach/HoSoTab.tsx`
- Modify: `giao_dien/src/khach/HoSo.tsx`
- Modify: `giao_dien/src/khach/khach.css`

**Interfaces:**
- Consumes: `TAB_HO_SO`, `tabTuHash`, `MaTabHoSo` (Task 1) · `HoSoViec`, `ID_GHI_NHANH` (Task 5) · `KhoiSapCo` (Task 4)
- Produces (từ `HoSoTab.tsx`): `OSoSucKhoe({ h })`, `BieuDo12Thang({ h })` (export), `TabMatHang({ h })`, `TabDonHang({ h })`, `TabCongNo`, `TabHoSo({ h })`. `TabTongQuan` và `TabSanPham` bị xoá.

- [ ] **Step 1: `HoSoTab.tsx`: xoá và gộp**

1. Xoá hẳn `TabTongQuan`, `DongHo`, `PhanTan`, `ChuaCo`, `LichMua`, và import `ChuaCoDuLieu` nếu không còn ai dùng. Xoá các khối "Thẻ khách hàng", "Gợi ý tiếp khách", "Ghi chú".
2. Thêm `OSoSucKhoe`, gồm 3 ô đầu lấy nguyên văn từ `TabTongQuan` cũ (DT theo khoảng, DT 30 ngày, Biên lãi gộp) và ô Nhịp mua mới:

```tsx
export function OSoSucKhoe({ h }: { h: HoSoApi }) {
  const k = h.khach, o = h.o_so;
  const ss30 = tiLe(o.dt_30, o.dt_30_truoc);
  const { data: kh } = useKhoangKhach(k.ma);
  const nm = useNhanMoc();
  const im = k.ty_le_im_lang ?? 0;
  return (
    <div className="o-kpi-luoi hs2-o">
      <div className="o-kpi"><div className="nhan">DT · {kh?.khoang.nhan ?? "…"}</div>
        <div className="gia">{kh ? gon(kh.tong.dt) : "…"}</div>
        {kh?.so_sanh.map(s => <div key={s.ma} className={"dong-phu " + (!s.co || s.tang_dt == null ? "nhat-chu" : s.tang_dt >= 0 ? "tang" : "giam")}
          title={s.co ? `${ngay(s.tu)} → ${ngay(s.den)}: ${yen(s.dt_ck)}` : undefined}>
          {!s.co ? `${s.nhan}: không có dữ liệu` : s.tang_dt == null ? `${s.nhan}: ${s.dt_ck ? "—" : "chưa mua"}` : `${thay_doi(s.tang_dt, 0)} so ${s.nhan}`}</div>)}</div>
      <div className="o-kpi"><div className="nhan">DT 30 ngày · {nm}</div><div className="gia">{gon(o.dt_30)}</div>
        <div className={"dong-phu " + (ss30 == null ? "nhat-chu" : ss30 >= 0 ? "tang" : "giam")}>{ss30 == null ? "30 ngày trước chưa mua" : `${thay_doi(ss30, 0)} so 30 ngày trước`}</div></div>
      <div className="o-kpi" title="số ngày im lặng ÷ nhịp mua riêng của khách (trung vị khoảng cách giữa các lần mua)">
        <div className="nhan">Nhịp mua</div><div className="gia">{k.nhip_ngay == null ? "—" : `${Math.round(k.nhip_ngay)} ngày`}</div>
        <div className={"dong-phu " + (k.ty_le_im_lang == null ? "nhat-chu" : im >= 2 ? "giam" : im >= 1 ? "canh-chu" : "tang")}>
          {k.nhip_ngay == null ? "chưa đủ 3 lần mua" : `im ${k.so_ngay_im_lang} ngày · ${im.toFixed(1).replace(".", ",")}× nhịp`}</div></div>
      <div className="o-kpi"><div className="nhan">Biên lãi gộp</div><div className="gia">{pc(k.ty_suat)}</div>
        <div className="dong-phu nhat-chu">lãi gộp ÷ doanh thu thuần, luỹ kế</div></div>
    </div>);
}
```

3. Đổi `function BieuDo12Thang` thành `export function BieuDo12Thang`. Chuyển dòng `phu=` dài của nó sang `cach_tinh=`, giữ nguyên nội dung.
4. Đổi tên `TabSanPham` thành `TabMatHang`. Đầu hàm thêm dòng tóm tắt `<p className="phu hs2-tom">{so(h.o_so.so_ma_dang_mua)} mã đang lấy · {h.o_so.so_ma_ngung ? `${h.o_so.so_ma_ngung} mã đã ngừng` : "không mã nào ngừng"}</p>`. Sắp khối theo thứ tự đặc tả §5:
   1. Mặt hàng mua trong khoảng xem.
   2. Top 10.
   3. `<div className="hs-hang hai">`, trong đó khối "Sản phẩm đã ngừng mua" có thêm `id="da-ngung-mua"` trên `<section>` (truyền `className` hoặc bọc `<div id="da-ngung-mua">`) và đứng cạnh khối "Tháng này chưa mua".
   4. `<div className="hs-hang hai"><GioNganh h={h} /><Tuan26 h={h} /></div>`.
   5. Gợi ý hàng chưa từng mua, bỏ `TN.bang_gia` và câu nhắc giá.
   6. Tất cả mặt hàng.

   Mọi `phu=` chỉ mô tả cách tính chuyển thành `cach_tinh=`. Riêng `phu` của "Tháng này chưa mua" GIỮ lộ vì khối liệt kê nhóm 036.
5. `TabDonHang`: xoá dòng `<button ... disabled ...>Tạo đơn nháp</button>` và giữ phần còn lại.
6. `TabHoSo`: thay đoạn `<div className="hs-hang hai"><ChuaCo …Hình ảnh…/><ChuaCo …Chat Facebook…/></div>` bằng:

```tsx
    <div className="hs-hang hai">
      <KhoiSapCo tieu_de="Ảnh cửa hàng" icon="🖼" hinh="anh" cong_dung="Ảnh cửa hàng của khách."
        can="nơi lưu ảnh theo mã khách." />
      <KhoiSapCo tieu_de="Chat Facebook" icon="💬" hinh="chat"
        cong_dung="Tin nhắn gần nhất với khách trên Messenger — xem khách vừa hỏi gì trước khi gọi."
        can="kết nối Messenger của trang KOME." />
    </div>
```

   và thêm `import { KhoiSapCo } from "./KhoiSapCo";`. `NhatKy` giữ `id="ghi-tx"`.

- [ ] **Step 2: `HoSo.tsx`: khung hai cột**

Thay import `TabCongNo, TabDonHang, TabHoSo, TabSanPham, TabTongQuan` bằng:

```tsx
import { BieuDo12Thang, OSoSucKhoe, TabCongNo, TabDonHang, TabHoSo, TabMatHang } from "./HoSoTab";
import { HoSoViec, ID_GHI_NHANH } from "./HoSoViec";
import { TAB_HO_SO, tabTuHash, type MaTabHoSo } from "./ho_so_logic";
```

Xoá `TAB_DU` / `MaTab` / `TAB`, thay bằng:

```tsx
const TAB = TAB_HO_SO.filter(([m]) => m !== "cong_no" || TN.cong_no);
```

State tab và sự kiện hash:

```tsx
  const [tab, datTab] = useState<MaTabHoSo>(() => tabTuHash(location.hash, TN.cong_no));
  const [moGhi, datMoGhi] = useState(false);
  useEffect(() => {
    const f = () => datTab(tabTuHash(location.hash, TN.cong_no));
    window.addEventListener("hashchange", f); return () => window.removeEventListener("hashchange", f);
  }, []);
  const chonTab = (t: MaTabHoSo) => { datTab(t); history.replaceState(null, "", giuKhoang(location.pathname + location.search) + "#" + t); };
```

Trước khi viết `chonTab`, kiểm `giuKhoang` trong `khung/khoang.ts`. Nếu nó đã giữ query hiện tại của URL thì dùng dạng trên. Nếu không, dùng `location.pathname + location.search + "#" + t` (query đã có sẵn khoảng xem) và ghi chú lý do. Đừng làm mất `?thang=`.

Phần thân (thay từ `<div className="tieu-de-trang hs-dau">` tới hết `</div role="tabpanel">`):

```tsx
    <div className="kh hs hs2">
      {thanhTren}
      <header className="hs2-dau">
        <div className="hs2-dau-chu">
          <h1><span className="ten-jp">{k.ten}</span>
            {h.hang && <span className={"kh-hang-nhan lon h" + h.hang} title="hạng theo doanh thu 12 tháng">Hạng {h.hang}</span>}
            <span className={"nhan-vien " + (MAU_TT[k.trang_thai] ?? "nhat")}>{h.nhan_trang_thai[k.trang_thai] ?? k.trang_thai}</span>
            {tn && (tn.nhan === "tre" || tn.nhan === "da_mua" || tn.nhan === "chua_toi_ngay") && <span className={"nhan-vien " + (MAU_THANG[tn.nhan] ?? "nhat")}
              title={tn.nhan === "tre" ? h.cach_tinh_thang : undefined}>{h.nhan_thang[tn.nhan]}</span>}
          </h1>
          <div className="phu">{/* giữ NGUYÊN dòng phụ cũ: mã · phụ trách · tỉnh · ☎ · ※OBC※ · dữ liệu đến */}</div>
          {h.the.length > 0 && <div className="hs2-the">{h.the.map(t => (
            <span key={t.chu} className={"nhan-vien " + (t.mau ?? "nhat")} title={t.vi}>{t.chu}</span>))}</div>}
        </div>
        <button type="button" className="nut-chinh" onClick={() => { datMoGhi(true);
          setTimeout(() => { const o = document.getElementById(ID_GHI_NHANH); o?.scrollIntoView({ behavior: "smooth", block: "center" }); o?.focus(); }, 50); }}>
          ✏️ Ghi liên hệ</button>
      </header>
      {loiTx && <p className="khoi-loi" role="alert">Chưa ghi được lần tiếp xúc: {loiTx}</p>}
      <div className="hs2-luoi">
        <HoSoViec h={h} moGhi={moGhi} datMoGhi={datMoGhi} />
        <div className="hs2-phai">
          <OSoSucKhoe h={h} />
          <BieuDo12Thang h={h} />
          <div className="hs-tab" role="tablist">
            {TAB.map(([m, nhan]) => (
              <button key={m} type="button" role="tab" aria-selected={tab === m} onClick={() => chonTab(m)}>
                {nhan}{m === "mat_hang" && h.o_so.so_ma_ngung > 0 && <span className="hs-cham" title={`${h.o_so.so_ma_ngung} mã đã ngừng mua`} />}
              </button>))}
          </div>
          <div role="tabpanel">
            {tab === "mat_hang" && <TabMatHang h={h} />}
            {tab === "don_hang" && <TabDonHang h={h} />}
            {tab === "cong_no" && <TabCongNo ma={k.ma} />}
            {tab === "ho_so" && <TabHoSo h={h} />}
          </div>
        </div>
      </div>
    </div>
```

Chỗ ghi chú `{/* giữ NGUYÊN … */}` phải được thay bằng đúng khối `<code>{k.ma}</code> · phụ trách …` của `HoSo.tsx` hiện tại (dòng `<div className="phu">` trong `hs-dau`), không viết lại. Bỏ `{h.dien_giai && <div className="hs-dien-giai">…}`, vì câu đó đã lên cột trái.

- [ ] **Step 3: CSS khung hai cột vào `khach.css`**

```css
.hs2-dau{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;background:var(--nen-the);
  border:1px solid var(--vien);border-radius:12px;padding:1rem 1.1rem;margin-bottom:1rem}
.hs2-dau h1{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem;margin:0 0 .3rem;font-size:1.25rem}
.hs2-dau h1 .nhan-vien{font-size:.72rem}
.hs2-dau .phu code{font-size:.78rem;background:none;padding:0}
.hs2-dau-chu{min-width:0}
.hs2-the{display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.5rem}
.hs2-the .nhan-vien{font-size:.68rem}
.hs2-luoi{display:grid;grid-template-columns:320px minmax(0,1fr);gap:1rem;align-items:start}
.hs2-trai{position:sticky;top:1rem}
.hs2-phai{min-width:0;display:flex;flex-direction:column;gap:.75rem}
.hs2-phai > .kh-the,.hs2-phai [role="tabpanel"] > .kh-the{margin-bottom:0}
.hs2-phai [role="tabpanel"]{display:flex;flex-direction:column;gap:.75rem}
.hs2-phai [role="tabpanel"] > .hs-hang{margin-bottom:0}
.hs2-o{grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:0}
.hs2 .o-kpi .gia,.hs2 .bang td.so{font-variant-numeric:tabular-nums}
.hs2-tom{margin:0}
@media (max-width:1023px){
  .hs2-luoi{grid-template-columns:minmax(0,1fr)}
  .hs2-trai{position:static}
  .hs2-o{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:560px){ .hs2-dau{flex-direction:column} .hs2-dau .nut-chinh{width:100%} }
```

- [ ] **Step 4: Chạy test canh, kiểu và vitest**

Run: `cd giao_dien && npx tsc -p tsconfig.json --noEmit && npx vitest run && cd .. && pytest tests/test_ho_so_360.py tests/test_nguon_dung.py tests/test_lien_he.py -v`
Expected: tất cả PASS. Nếu `test_ho_so_360` đỏ vì chuỗi `Bảng giá của bậc` hay `Tạo đơn nháp` còn trong chú thích, xoá chú thích đó.

- [ ] **Step 5: Commit**

```bash
git add giao_dien/src/khach/HoSo.tsx giao_dien/src/khach/HoSoTab.tsx giao_dien/src/khach/khach.css
git commit -m "feat(ho-so): bo cuc hai cot, 4 o so suc khoe, 4 tab (Mat hang/Don hang/Cong no/Ho so)"
```

---

### Task 7: Build, pytest toàn bộ, CLAUDE.md

**Files:**
- Modify: `kome/web/spa/**` (bản build)
- Modify: `CLAUDE.md` (dòng `/khach-hang/{mã}` trong bảng "Các trang của web app")

- [ ] **Step 1: Build**

Run: `cd giao_dien && npm run build`
Expected: kết thúc không lỗi, `kome/web/spa/.nguon` được ghi lại.

- [ ] **Step 2: Sửa CLAUDE.md**

Trong ô "Việc" của dòng `/khach-hang/{mã}`, thay đoạn `5 tab (Tổng quan · Sản phẩm · Đơn hàng · Công nợ · Hồ sơ & liên hệ)` bằng:

```
hai cột (thiết kế lại 2026-09-26, đặc tả `2026-09-26-ho-so-khach-360-thiet-ke-lai-design.md`): cột trái dính "Việc với khách này" (lý do · **"Mã đến ngày mua lại"** — KHÁC "Nên chào" của `/lien-he` · chép kịch bản `khach/kich_ban.ts` · lần liên hệ trước + ghi nhanh · công nợ), cột phải 4 ô số + biểu đồ 12 tháng + 4 tab (Mặt hàng · Đơn hàng · Công nợ · Hồ sơ và nhật ký; `#tong_quan`/`#san_pham` cũ → Mặt hàng); Ảnh cửa hàng / Chat Facebook là khối "sắp có" (`KhoiSapCo`)
```

Phần còn lại của ô đó (khoảng xem, `/khoang`, biểu đồ bấm tháng, lưới 26 tuần, giỏ theo ngành, ghi tiếp xúc) giữ nguyên.

- [ ] **Step 3: pytest toàn bộ**

Run: `pytest -q`
Expected: toàn bộ xanh, gồm `tests/test_api.py::test_ban_build_khop_ma_nguon`. Nếu `tests/test_tai_lieu.py::test_anh_chup_tai_lieu_khong_cu` đỏ (CLAUDE.md chỉ đổi bảng trang, không đổi mục "Bẫy đã biết", nên nhiều khả năng không đỏ), chạy `python scripts/sinh_tai_lieu.py` và commit `kome/web/tai_lieu_sinh.json`.

- [ ] **Step 4: Commit**

```bash
git add kome/web/spa CLAUDE.md
git commit -m "build: ban build ho so 360 thiet ke lai + cap nhat CLAUDE.md"
```

---

### Task 8: Kiểm trên trình duyệt

**Files:** không sửa, trừ khi phát hiện lỗi (sửa thì quay lại task tương ứng, build lại, commit).

- [ ] **Step 1: Mở preview**

Xem `.claude/launch.json`. Nếu chưa có cấu hình uvicorn thì thêm:
`{"name":"kome-web","runtimeExecutable":"uvicorn","runtimeArgs":["kome.web.app:app","--port","8000"],"port":8000}`.
Mở bằng `preview_start {name:"kome-web"}`. CSDL phải là `kome_test` hoặc bản chỉ đọc. KHÔNG ghi tiếp xúc lên CSDL thật.

- [ ] **Step 2: Bốn loại khách**

Tìm mã bằng `/api/khach-hang/ds?nv=__moi_nguoi`: một khách `canh_bao`, một `binh_thuong`, một `ngung_giao_dich`, một khách không có trong sổ công nợ. Với mỗi khách, `read_page` để xác nhận:
- tiêu đề khối lý do là "Vì sao cần gọi" hoặc "Tình hình", đúng với màu trạng thái;
- khách `ngung_giao_dich` không có khối "Mã đến ngày mua lại" và câu là "Khách đã ngừng giao dịch… — không gọi";
- 4 tab hiện đúng (Công nợ ẩn khi `TN.cong_no` tắt);
- tab Hồ sơ có hai khối "Chưa có nguồn".

- [ ] **Step 3: Hành vi**

- Mở `/khach-hang/{mã}#tong_quan` thì tab Mặt hàng đang chọn.
- Bấm tab khi URL có `?thang=2026-08` thì query còn nguyên.
- Bấm "+ n mã đã ngừng mua" thì sang tab Mặt hàng và cuộn tới khối đó.
- Nút "Cách tính" mở và đóng được.
- "Ghi liên hệ" ở đầu trang mở ô ghi nhanh và đặt con trỏ vào đó.
- `read_console_messages` không có lỗi.

- [ ] **Step 4: Cỡ và chế độ màu**

`resize_window` 1280×900 và 375×812, `colorScheme` light/dark. Chụp màn ở 4 tổ hợp: cột trái dính ở 1280, xếp chồng ở 375, không cuộn ngang. Trả `resize_window preset:"desktop"` khi xong.

- [ ] **Step 5: Gửi ảnh chụp cho chủ DN**

Gửi ảnh qua `SendUserFile`, kèm danh sách những gì đã kiểm và điều gì chưa kiểm được (nếu có).
