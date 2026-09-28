# Tổng quan ít chữ — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Màn `/` (Tổng quan) còn ít chữ nhất có thể: mỗi khối một hình + tối đa một số lớn, mọi chi tiết trong ô nổi (rê chuột / chạm), không còn bảng.

**Architecture:** Ba linh kiện chung mới trong `giao_dien/src/chung/` (`ONoi` ô nổi, `ThanhNgang`, `ThanhChong`, cùng `SoLon`/`MucSo`), logic thuần tách ra file `*_logic.ts` có Vitest (môi trường `node`, không jsdom). `Khoi` có hai chỗ chữ mới `cach_tinh` (ⓘ) và `canh_bao` (luôn hiện). Sau đó viết lại từng khối trong `giao_dien/src/tong_quan/khoi.tsx` dùng các linh kiện đó — KHÔNG đổi API, SQL hay migration.

**Tech Stack:** React 19 + TypeScript + Vite + TanStack Query, Vitest 5 (`environment: "node"`), SVG/HTML tự vẽ (không thư viện biểu đồ). Python pytest cho test quét mã nguồn.

**Spec:** `docs/superpowers/specs/2026-09-28-tong-quan-it-chu-design.md`

## Global Constraints

- Không đụng máy chủ: không đổi `kome/khoi_tong_quan.py`, SQL, migration. `/` ≤ 9 lượt hỏi, `tests/test_api.py::NGAN_SACH_TRUY_VAN` không đổi. (Ngoại lệ duy nhất: `kome/web/bo_cuc.py` — chiều cao mặc định, Task 9.)
- Nhãn kỳ so luôn là `so_sanh[0].nhan` của MÁY CHỦ, LUÔN hiện. Nét đứt / cột ma / vạch đứt (`VachSoSanh`) CHỈ dùng cho kỳ so — không dùng cho "tháng trước" của khối Tháng này chưa mua hay thứ gì khác.
- Câu định nghĩa cách tính → `Khoi.cach_tinh` (ⓘ). Câu ngoại lệ đang xảy ra → `Khoi.canh_bao` (luôn hiện). `cach_tinh` của máy chủ (`d.cach_tinh`) truyền thẳng, không chép câu vào giao diện.
- Sau Task 9, `giao_dien/src/tong_quan/khoi.tsx` không còn `<table`, không còn `className="phu"`/`className={"phu …`, không in `{d.cach_tinh}` làm con JSX.
- Giữ nguyên các chuỗi mà test cũ canh: `` `/khach-hang?loc=${n}&tat_ca=1` `` (tests/test_tong_quan.py:238), `TN.cong_no && <OKpiCongNo` (tests/test_nguon_dung.py:43).
- Màu dùng biến CSS có sẵn (`--lien-ket`, `--ok-vien`, `--do`, `--chu-mo`, `--vien`, `--vien-dam`, `--nen-the`…) — mọi CSS mới phải đúng ở cả sáng lẫn tối mà không cần khối màu riêng.
- Mỗi task đổi `giao_dien/` phải `cd giao_dien && npm test && npm run build` rồi commit CẢ `kome/web/spa/` (bản build được commit; `tests/test_api.py::test_ban_build_khop_ma_nguon` so dấu vân tay).
- CSDL test là Postgres localhost (`DATABASE_URL_TEST`); nếu pytest bị ngắt giữa chừng, xem memory "pytest bị ngắt để lại khoá".
- Commit kết thúc bằng dòng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File Structure

| File | Trách nhiệm |
|---|---|
| `giao_dien/src/chung/o_noi_logic.ts` (mới) | `buocCham`, `viTriNoi` — logic thuần của ô nổi |
| `giao_dien/src/chung/o_noi_logic.test.ts` (mới) | Vitest |
| `giao_dien/src/chung/ONoi.tsx` (mới) | `ONoi`, `DongNoi` |
| `giao_dien/src/chung/thanh_logic.ts` (mới) | `tyLeThanh`, `thangChung`, `chiaKhuc` |
| `giao_dien/src/chung/thanh_logic.test.ts` (mới) | Vitest |
| `giao_dien/src/chung/Hinh.tsx` (mới) | `ThanhNgang`, `ThanhChong`, `SoLon`, `MucSo`, `HangSo` |
| `giao_dien/src/chung/Khoi.tsx` | + `cach_tinh`, `canh_bao`; `ChuaCoDuLieu` + `gon` |
| `giao_dien/src/chung/BieuDo.tsx` | chạm 2 lần mới `onBam`; + `them_noi` |
| `giao_dien/src/chung/chung.css` | CSS của các linh kiện trên |
| `giao_dien/src/tong_quan/viec_logic.ts` (+ `.test.ts`, mới) | `tenViec`, `sapViec`, `demTheoTag` |
| `giao_dien/src/tong_quan/han_logic.ts` (+ `.test.ts`, mới) | `mienHan`, `xHan`, `banKinh` |
| `giao_dien/src/tong_quan/DaiHan.tsx` (mới) | dải thời gian lô sắp hết hạn |
| `giao_dien/src/tong_quan/khoi.tsx` | viết lại 17 khối |
| `giao_dien/src/tong_quan/tong_quan.css` | CSS riêng Tổng quan |
| `giao_dien/src/tong_quan/Luoi.tsx:89` | không bắt đầu kéo khối khi bấm vào ⓘ / ô nổi |
| `kome/web/bo_cuc.py` | chiều cao mặc định (Task 9) |
| `tests/test_tong_quan_it_chu.py` (mới) | test quét mã nguồn luật chữ |
| `CLAUDE.md` | bất biến mới + sửa ba câu "in dưới khối" |

---

### Task 1: Logic thuần của ô nổi và thanh

**Files:**
- Create: `giao_dien/src/chung/o_noi_logic.ts`, `giao_dien/src/chung/o_noi_logic.test.ts`
- Create: `giao_dien/src/chung/thanh_logic.ts`, `giao_dien/src/chung/thanh_logic.test.ts`

**Interfaces:**
- Produces:
  - `buocCham(daMo: boolean, kieu: string): "mo" | "di"`
  - `viTriNoi(goc: { left: number; top: number; right: number; bottom: number }, noi: { w: number; h: number }, khung: { w: number; h: number }, le?: number): { left: number; top: number }`
  - `tyLeThanh(v: number | null | undefined, thang: number): number` (0..1)
  - `thangChung(ds: { gia_tri: number; ss?: number | null }[]): number` (> 0)
  - `chiaKhuc(dem: number[]): number[]` (phần trăm, Σ = 100 khi có khúc dương)

- [ ] **Step 1: Viết test thất bại**

`giao_dien/src/chung/o_noi_logic.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { buocCham, viTriNoi } from "./o_noi_logic";

describe("buocCham", () => {
  it("chạm lần 1 (chưa mở) chỉ mở ô nổi", () => expect(buocCham(false, "touch")).toBe("mo"));
  it("chạm lần 2 (đã mở) mới đi", () => expect(buocCham(true, "touch")).toBe("di"));
  it("chuột bấm là đi, dù ô nổi chưa mở", () => {
    expect(buocCham(false, "mouse")).toBe("di");
    expect(buocCham(true, "mouse")).toBe("di");
  });
  it("bút coi như chuột (có rê)", () => expect(buocCham(false, "pen")).toBe("di"));
});

describe("viTriNoi", () => {
  const khung = { w: 375, h: 800 };
  it("mặc định nằm DƯỚI phần tử, căn giữa", () => {
    expect(viTriNoi({ left: 100, top: 100, right: 200, bottom: 120 }, { w: 100, h: 50 }, khung))
      .toEqual({ left: 100, top: 126 });
  });
  it("sát đáy thì lật LÊN trên", () => {
    expect(viTriNoi({ left: 100, top: 760, right: 200, bottom: 780 }, { w: 100, h: 50 }, khung))
      .toEqual({ left: 100, top: 704 });
  });
  it("không tràn mép trái / phải của điện thoại 375 px", () => {
    expect(viTriNoi({ left: 0, top: 100, right: 20, bottom: 120 }, { w: 200, h: 50 }, khung).left).toBe(8);
    expect(viTriNoi({ left: 360, top: 100, right: 375, bottom: 120 }, { w: 200, h: 50 }, khung).left).toBe(167);
  });
  it("ô nổi rộng hơn màn hình thì dính mép trái", () => {
    expect(viTriNoi({ left: 100, top: 100, right: 200, bottom: 120 }, { w: 500, h: 50 }, khung).left).toBe(8);
  });
  it("không chỗ nào vừa thì vẫn nằm dưới (không đẩy lên khỏi mép trên)", () => {
    expect(viTriNoi({ left: 100, top: 20, right: 200, bottom: 40 }, { w: 100, h: 900 }, khung).top).toBe(46);
  });
});
```

`giao_dien/src/chung/thanh_logic.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { chiaKhuc, thangChung, tyLeThanh } from "./thanh_logic";

describe("tyLeThanh", () => {
  it("tỷ lệ theo thang", () => expect(tyLeThanh(50, 200)).toBe(0.25));
  it("số ÂM (赤伝) → 0, không âm, không lỗi", () => expect(tyLeThanh(-30, 200)).toBe(0));
  it("vượt thang → kẹp 1", () => expect(tyLeThanh(300, 200)).toBe(1));
  it("null / thang 0 → 0", () => {
    expect(tyLeThanh(null, 200)).toBe(0);
    expect(tyLeThanh(10, 0)).toBe(0);
  });
});

describe("thangChung", () => {
  it("lớn nhất của cả thực tế lẫn kỳ so", () =>
    expect(thangChung([{ gia_tri: 10, ss: 40 }, { gia_tri: 30 }])).toBe(40));
  it("toàn số âm / rỗng → 1 (không chia 0)", () => {
    expect(thangChung([{ gia_tri: -5 }])).toBe(1);
    expect(thangChung([])).toBe(1);
  });
});

describe("chiaKhuc", () => {
  it("Σ = 100", () => {
    const p = chiaKhuc([173, 176, 905, 163]);
    expect(p.reduce((s, x) => s + x, 0)).toBeCloseTo(100);
  });
  it("khúc 0 / âm được 0% và không làm lệch khúc khác", () =>
    expect(chiaKhuc([0, 3, -2, 1])).toEqual([0, 75, 0, 25]));
  it("toàn 0 → toàn 0", () => expect(chiaKhuc([0, 0])).toEqual([0, 0]));
});
```

- [ ] **Step 2: Chạy, xác nhận thất bại**

Run: `cd giao_dien && npx vitest run src/chung/o_noi_logic.test.ts src/chung/thanh_logic.test.ts`
Expected: FAIL — "Failed to resolve import ./o_noi_logic" / "./thanh_logic".

- [ ] **Step 3: Viết mã**

`giao_dien/src/chung/o_noi_logic.ts`:
```ts
// Logic thuần của ô nổi (đặc tả 2026-09-28-tong-quan-it-chu-design.md §3.1) — tách khỏi
// ONoi.tsx để Vitest (môi trường node, không DOM) canh được.

/** Bấm vào phần tử có ô nổi: chạm lần 1 chỉ MỞ ô nổi, chạm lần 2 mới đi liên kết.
 *  Chuột / bút có rê (ô nổi đã hiện lúc rê) nên bấm là đi. */
export function buocCham(daMo: boolean, kieu: string): "mo" | "di" {
  return kieu === "touch" && !daMo ? "mo" : "di";
}

/** Toạ độ `position: fixed` của ô nổi: dưới phần tử (lật lên khi sát đáy và phía trên
 *  đủ chỗ), căn giữa theo phần tử, không tràn mép trái / phải. */
export function viTriNoi(goc: { left: number; top: number; right: number; bottom: number },
  noi: { w: number; h: number }, khung: { w: number; h: number }, le = 8): { left: number; top: number } {
  const giua = (goc.left + goc.right) / 2;
  const left = Math.max(le, Math.min(giua - noi.w / 2, khung.w - noi.w - le));
  const duoi = goc.bottom + 6, tren = goc.top - 6 - noi.h;
  const top = duoi + noi.h <= khung.h - le || tren < le ? duoi : tren;
  return { left: Math.round(left), top: Math.round(top) };
}
```

`giao_dien/src/chung/thanh_logic.ts`:
```ts
// Thang của thanh ngang / thanh chồng (đặc tả 2026-09-28-tong-quan-it-chu-design.md §3.3–3.4).
// Số ÂM (赤伝 — luật cấm lọc bỏ) vẽ thành thanh rộng 0; SỐ vẫn in số âm thật ở nơi gọi.

export function tyLeThanh(v: number | null | undefined, thang: number): number {
  if (v == null || !(thang > 0)) return 0;
  return Math.max(0, Math.min(1, v / thang));
}

export function thangChung(ds: { gia_tri: number; ss?: number | null }[]): number {
  let m = 0;
  for (const x of ds) m = Math.max(m, x.gia_tri, x.ss ?? 0);
  return m > 0 ? m : 1;
}

export function chiaKhuc(dem: number[]): number[] {
  const tong = dem.reduce((s, x) => s + (x > 0 ? x : 0), 0);
  return dem.map(x => (tong > 0 && x > 0 ? (x / tong) * 100 : 0));
}
```

- [ ] **Step 4: Chạy, xác nhận qua**

Run: `cd giao_dien && npx vitest run src/chung/o_noi_logic.test.ts src/chung/thanh_logic.test.ts`
Expected: PASS (5 + 9 test).

- [ ] **Step 5: Commit**

```bash
git add giao_dien/src/chung/o_noi_logic.ts giao_dien/src/chung/o_noi_logic.test.ts giao_dien/src/chung/thanh_logic.ts giao_dien/src/chung/thanh_logic.test.ts
git commit -m "feat(giao-dien): logic thuan cua o noi va thanh (buocCham, viTriNoi, tyLeThanh, chiaKhuc)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `ONoi`, `DongNoi` và hai chỗ chữ mới của `Khoi`

**Files:**
- Create: `giao_dien/src/chung/ONoi.tsx`
- Modify: `giao_dien/src/chung/Khoi.tsx` (toàn file — `Khoi`, `ChuaCoDuLieu`)
- Modify: `giao_dien/src/chung/chung.css` (thêm cuối file)
- Modify: `giao_dien/src/tong_quan/Luoi.tsx:89` (điều kiện `tuDau`)

**Interfaces:**
- Consumes: `buocCham`, `viTriNoi` (Task 1); `giuKhoang` không cần (thẻ `<a>` đã được `ganVietLaiLienKet` viết lại lúc `pointerdown`).
- Produces:
  - `ONoi({ noi_dung: ReactNode; href?: string; onBam?: () => void; children: ReactNode; className?: string; style?: CSSProperties; nhan?: string })` — có `href` thì gốc là `<a>`, không thì `<span tabIndex=0>`.
  - `DongNoi({ nhan: ReactNode; gia: ReactNode; mau?: string })` — một dòng `nhãn … giá trị` trong ô nổi.
  - `Khoi` thêm props `cach_tinh?: ReactNode`, `canh_bao?: ReactNode`.
  - `ChuaCoDuLieu` thêm prop `gon?: boolean`.

- [ ] **Step 1: Viết `ONoi.tsx`**

```tsx
// Ô nổi chung cho mọi thứ KHÔNG phải BieuDo (đặc tả 2026-09-28-tong-quan-it-chu-design.md §3.1):
//   * chuột: rê vào hiện, rời ẩn, bấm là đi liên kết;
//   * chạm: lần 1 hiện, lần 2 (cùng phần tử) đi; chạm ra ngoài / cuộn / Esc thì đóng;
//   * bàn phím: Tab tới thì hiện, Enter đi.
// Chỉ MỘT ô nổi mở tại một thời điểm. Ô nổi vẽ qua portal vào <body> (position: fixed) để
// không bị `overflow: hidden` của khối cắt mất.
import { useEffect, useId, useLayoutEffect, useRef, useState, useSyncExternalStore,
  type CSSProperties, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { buocCham, viTriNoi } from "./o_noi_logic";

let dangMo: string | null = null;
const nghe = new Set<() => void>();
const datMo = (id: string | null) => { dangMo = id; nghe.forEach(f => f()); };
const theoDoi = (f: () => void) => { nghe.add(f); return () => { nghe.delete(f); }; };

export function ONoi({ noi_dung, href, onBam, children, className, style, nhan }: {
  noi_dung: ReactNode; href?: string; onBam?: () => void; children: ReactNode;
  className?: string; style?: CSSProperties; nhan?: string;
}) {
  const id = useId();
  const mo = useSyncExternalStore(theoDoi, () => dangMo === id);
  const goc = useRef<HTMLElement | null>(null);
  const noi = useRef<HTMLDivElement>(null);
  const kieu = useRef("mouse");
  const quaCon = useRef(false);   // focus do bấm/chạm (không phải Tab) — không tự mở
  const [vt, datVt] = useState<{ left: number; top: number } | null>(null);

  useLayoutEffect(() => {
    if (!mo || !goc.current || !noi.current) { datVt(null); return; }
    datVt(viTriNoi(goc.current.getBoundingClientRect(),
      { w: noi.current.offsetWidth, h: noi.current.offsetHeight }, { w: window.innerWidth, h: window.innerHeight }));
  }, [mo]);

  useEffect(() => {
    if (!mo) return;
    const ngoai = (e: PointerEvent) => { if (!goc.current?.contains(e.target as Node)) datMo(null); };
    const cuon = () => datMo(null);
    document.addEventListener("pointerdown", ngoai);
    window.addEventListener("scroll", cuon, true);
    return () => { document.removeEventListener("pointerdown", ngoai); window.removeEventListener("scroll", cuon, true); };
  }, [mo]);

  const p = {
    ref: (e: HTMLElement | null) => { goc.current = e; },
    className: "o-noi-goc" + (className ? " " + className : ""),
    style,
    tabIndex: href ? undefined : 0,
    role: href ? undefined : onBam ? "button" : undefined,
    "aria-label": nhan,
    "aria-describedby": mo ? id : undefined,
    onPointerDown: (e: React.PointerEvent) => { kieu.current = e.pointerType; quaCon.current = true; },
    onPointerEnter: (e: React.PointerEvent) => { if (e.pointerType === "mouse") datMo(id); },
    onPointerLeave: (e: React.PointerEvent) => { if (e.pointerType === "mouse" && dangMo === id) datMo(null); },
    onFocus: () => { if (!quaCon.current) datMo(id); },
    onBlur: () => { quaCon.current = false; if (dangMo === id) datMo(null); },
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Escape") datMo(null);
      else if (e.key === "Enter" && !href) onBam?.();
    },
    onClick: (e: React.MouseEvent) => {
      const b = buocCham(mo, kieu.current);
      kieu.current = "mouse";
      if (b === "mo") { e.preventDefault(); datMo(id); return; }
      if (!href) onBam?.();
    },
  };

  return (
    <>
      {href ? <a href={href} {...p}>{children}</a> : <span {...p}>{children}</span>}
      {mo && createPortal(
        <div ref={noi} id={id} role="tooltip" className="bd-noi o-noi"
          style={vt ? { left: vt.left, top: vt.top } : { left: -9999, top: 0 }}>{noi_dung}</div>,
        document.body)}
    </>
  );
}

/** Một dòng trong ô nổi: nhãn … giá trị (cùng kiểu dòng của ô nổi BieuDo). */
export function DongNoi({ nhan, gia, mau }: { nhan: ReactNode; gia: ReactNode; mau?: string }) {
  return <div>{mau && <i style={{ background: mau }} />}{nhan}<b>{gia}</b></div>;
}
```

- [ ] **Step 2: Sửa `Khoi.tsx`** — thay hàm `Khoi` và `ChuaCoDuLieu` (giữ nguyên `Spark`, `ThanhMoc`, `mauTienDo`):

```tsx
// Nội dung chung của một khối: tiêu đề + nhãn + liên kết "Mở →" + thân.
// Vỏ ngoài (kéo thả, đổi cỡ, nút ✕) do lưới Tổng quan lo (tong_quan/Luoi.tsx).
// Luật chữ (đặc tả 2026-09-28-tong-quan-it-chu-design.md §4): câu ĐỊNH NGHĨA cách tính vào
// `cach_tinh` (ⓘ cạnh tiêu đề), câu NGOẠI LỆ đang xảy ra vào `canh_bao` (luôn hiện).
// `phu` chỉ còn cho nhãn kỳ so / nhãn mốc ngắn.
import type { ReactNode } from "react";
import { ONoi } from "./ONoi";

export function Khoi({ tieu_de, phu, nhan, mau_nhan = "do", lien_ket, children, dang_tai, loi, cach_tinh, canh_bao }: {
  tieu_de: string;
  phu?: ReactNode;
  nhan?: ReactNode;
  mau_nhan?: "do" | "canh" | "ok" | "lam" | "nhat";
  lien_ket?: { href: string; chu?: string };
  children?: ReactNode;
  dang_tai?: boolean;
  loi?: string | null;
  cach_tinh?: ReactNode;
  canh_bao?: ReactNode;
}) {
  return (
    <>
      <div className="khoi-dau" data-keo="1">
        <h2>{tieu_de}</h2>
        {cach_tinh != null && <ONoi noi_dung={<div className="o-noi-chu">{cach_tinh}</div>} nhan="Cách tính" className="khoi-i">ⓘ</ONoi>}
        {nhan != null && <span className={"nhan-vien " + mau_nhan}>{nhan}</span>}
        {phu != null && <span className="khoi-phu">{phu}</span>}
        {lien_ket && <a className="khoi-mo" href={lien_ket.href}>{lien_ket.chu ?? "Mở"} →</a>}
      </div>
      {loi ? <div className="khoi-loi">Không tải được khối này: {loi}</div>
        : dang_tai ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>
        : <>{children}{canh_bao != null && canh_bao !== false && <div className="khoi-canh" role="note">{canh_bao}</div>}</>}
    </>
  );
}

/** Khối của gói thiết kế chưa có nguồn dữ liệu thật: giữ khung, nói rõ thiếu gì.
 *  `gon` (Tổng quan): chỉ tiêu đề + nhãn "chưa có", lý do trong ⓘ. */
export function ChuaCoDuLieu({ tieu_de, ly_do, gon = false }: { tieu_de: string; ly_do: string; gon?: boolean }) {
  if (gon) return <Khoi tieu_de={tieu_de} nhan="chưa có dữ liệu" mau_nhan="nhat"
    cach_tinh={<>{ly_do}<br />Không hiện số mẫu: khối này sẽ tự có số khi nguồn được nạp.</>} />;
  return (
    <Khoi tieu_de={tieu_de} nhan="chưa có dữ liệu" mau_nhan="nhat">
      <div className="chua-co">
        <svg viewBox="0 0 18 18" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.4"
          aria-hidden="true" focusable="false"><ellipse cx="9" cy="4.6" rx="6" ry="2.2" /><path d="M3 4.6v8.8c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V4.6" /></svg>
        <p>{ly_do}</p>
        <p className="phu">Không hiện số mẫu: khối này sẽ tự có số khi nguồn được nạp.</p>
      </div>
    </Khoi>
  );
}
```

- [ ] **Step 3: Thêm CSS cuối `giao_dien/src/chung/chung.css`**

```css
/* Ô nổi chung (chung/ONoi.tsx) — dùng lại kiểu .bd-noi, nhưng fixed + portal */
.o-noi{position:fixed;transform:none;max-width:min(320px,calc(100vw - 16px));z-index:60}
.o-noi div{white-space:normal}
.o-noi-chu{display:block;line-height:1.45;color:var(--chu-thuong);font-size:.74rem}
.o-noi-goc{cursor:default}
a.o-noi-goc,.o-noi-goc[role="button"]{cursor:pointer}
.o-noi-goc:focus-visible{outline:2px solid var(--do);outline-offset:2px;border-radius:6px}
.khoi-i{display:inline-flex;align-items:center;justify-content:center;width:1.15rem;height:1.15rem;border-radius:50%;
  font-size:.78rem;color:var(--chu-mo);cursor:help;user-select:none}
.khoi-i:hover{color:var(--chu)}
.khoi-canh{margin-top:.45rem;font-size:.72rem;color:var(--canh-chu);line-height:1.4}
```

- [ ] **Step 4: Sửa `giao_dien/src/tong_quan/Luoi.tsx:89`** — bấm ⓘ không được bắt đầu kéo khối:

```tsx
            onPointerDown={e => { const t = e.target as HTMLElement; tuDau.current = !!t.closest("[data-keo]") && !t.closest("a,button,input,.o-noi-goc"); }}
```

- [ ] **Step 5: Kiểm kiểu + test + build**

Run: `cd giao_dien && npm test && npm run build`
Expected: vitest PASS (cũ + Task 1); `tsc -b` không lỗi; build ghi `kome/web/spa/`.

- [ ] **Step 6: Commit**

```bash
git add giao_dien/src/chung/ONoi.tsx giao_dien/src/chung/Khoi.tsx giao_dien/src/chung/chung.css giao_dien/src/tong_quan/Luoi.tsx kome/web/spa
git commit -m "feat(giao-dien): o noi chung (ONoi) + Khoi.cach_tinh (i) va Khoi.canh_bao

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `ThanhNgang`, `ThanhChong`, `SoLon`, `MucSo`, `HangSo`

**Files:**
- Create: `giao_dien/src/chung/Hinh.tsx`
- Modify: `giao_dien/src/chung/chung.css` (thêm cuối file)

**Interfaces:**
- Consumes: `ONoi`, `DongNoi` (Task 2); `tyLeThanh`, `thangChung`, `chiaKhuc` (Task 1); `VachSoSanh` (`chung/SoSanh.tsx`).
- Produces:
  ```ts
  export type DongThanh = { khoa: string; ten: ReactNode; gia_tri: number; ss?: number | null; chu: ReactNode;
    phu?: ReactNode; mau?: string; href?: string; chi_tiet: ReactNode; ten_jp?: boolean };
  export function ThanhNgang(p: { dong: DongThanh[]; nhan_ss?: string; thang?: number }): JSX.Element
  export type Khuc = { khoa: string; nhan: string; dem: number; mau: string; href?: string; onBam?: () => void;
    chi_tiet?: ReactNode; chon?: boolean };
  export function ThanhChong(p: { khuc: Khuc[]; dinh_dang: (v: number) => string; don_vi?: string }): JSX.Element
  export function SoLon(p: { gia: ReactNode; nhan: ReactNode; chi_tiet?: ReactNode; href?: string; lop?: string; mau?: string }): JSX.Element
  export function MucSo(p: { nhan: ReactNode; gia: ReactNode; lop?: string; chi_tiet?: ReactNode }): JSX.Element
  export function HangSo(p: { children: ReactNode }): JSX.Element
  ```
  `ss` của `ThanhNgang` CHỈ là kỳ so (vẽ `VachSoSanh`, nét đứt) — muốn so với thứ khác thì để trong `chi_tiet`.

- [ ] **Step 1: Viết `Hinh.tsx`**

```tsx
// Hình dùng chung của các màn ít chữ (đặc tả 2026-09-28-tong-quan-it-chu-design.md §3.3–3.4):
// thanh ngang xếp hạng, thanh chồng nhiều khúc, số lớn, hàng số nhỏ. Mọi chi tiết vào ONoi.
import type { ReactNode } from "react";
import { DongNoi, ONoi } from "./ONoi";
import { VachSoSanh } from "./SoSanh";
import { chiaKhuc, thangChung, tyLeThanh } from "./thanh_logic";

export type DongThanh = { khoa: string; ten: ReactNode; gia_tri: number; ss?: number | null; chu: ReactNode;
  phu?: ReactNode; mau?: string; href?: string; chi_tiet: ReactNode; ten_jp?: boolean };

/** Thanh ngang xếp hạng. `ss` = KỲ SO (vạch đứt) — không dùng cho so sánh nào khác.
 *  `thang` mặc định = lớn nhất của thực tế và kỳ so. */
export function ThanhNgang({ dong, nhan_ss, thang }: { dong: DongThanh[]; nhan_ss?: string; thang?: number }) {
  const m = thang ?? thangChung(dong);
  return (
    <div className="tng-ds">
      {dong.map(x => (
        <ONoi key={x.khoa} href={x.href} className="tng-dong"
          noi_dung={<><strong className={x.ten_jp ? "ten-jp" : undefined}>{x.ten}</strong>{x.chi_tiet}</>}>
          <span className={"tng-ten" + (x.ten_jp ? " ten-jp" : "")}>{x.ten}</span>
          <span className="tng-thanh ss-thanh">
            <span className="tng-day" style={{ width: `${tyLeThanh(x.gia_tri, m) * 100}%`, background: x.mau ?? "var(--lien-ket)" }} />
            {x.ss != null && nhan_ss && <VachSoSanh ty_le={tyLeThanh(x.ss, m)} nhan={nhan_ss} />}
          </span>
          <b className="tng-so">{x.chu}</b>
          {x.phu != null && <span className="tng-phu">{x.phu}</span>}
        </ONoi>))}
    </div>
  );
}

export type Khuc = { khoa: string; nhan: string; dem: number; mau: string; href?: string; onBam?: () => void;
  chi_tiet?: ReactNode; chon?: boolean };

/** Một thanh chia khúc + chú giải chấm màu. Khúc ≤ 0 không vẽ nhưng vẫn có trong chú giải. */
export function ThanhChong({ khuc, dinh_dang, don_vi = "" }: { khuc: Khuc[]; dinh_dang: (v: number) => string; don_vi?: string }) {
  const pt = chiaKhuc(khuc.map(k => k.dem));
  const noi = (k: Khuc, i: number) => <>
    <strong>{k.nhan}</strong>
    <DongNoi mau={k.mau} nhan={don_vi || "Số"} gia={dinh_dang(k.dem)} />
    <DongNoi nhan="Tỷ lệ" gia={`${pt[i].toFixed(1).replace(".", ",")}%`} />
    {k.chi_tiet}
  </>;
  return (
    <div className="tc">
      <div className="tc-thanh">
        {khuc.map((k, i) => pt[i] > 0 && (
          <ONoi key={k.khoa} href={k.href} onBam={k.onBam} nhan={`${k.nhan}: ${dinh_dang(k.dem)}`}
            className={"tc-khuc" + (k.chon ? " chon" : "")} style={{ width: `${pt[i]}%`, background: k.mau }}
            noi_dung={noi(k, i)}><span /></ONoi>))}
      </div>
      <div className="tc-chu-giai">
        {khuc.map((k, i) => (
          <ONoi key={k.khoa} href={k.href} onBam={k.onBam} className={"tc-muc" + (k.chon ? " chon" : "")} noi_dung={noi(k, i)}>
            <i style={{ background: k.mau }} />{k.nhan}<b>{dinh_dang(k.dem)}</b>
          </ONoi>))}
      </div>
    </div>
  );
}

/** Số lớn của khối, chi tiết trong ô nổi. */
export function SoLon({ gia, nhan, chi_tiet, href, lop, mau }: {
  gia: ReactNode; nhan: ReactNode; chi_tiet?: ReactNode; href?: string; lop?: string; mau?: string }) {
  const than = <><b className={lop} style={mau ? { color: mau } : undefined}>{gia}</b><span>{nhan}</span></>;
  return chi_tiet == null && !href ? <div className="so-lon">{than}</div>
    : <ONoi href={href} className="so-lon" noi_dung={<><strong>{nhan}</strong>{chi_tiet}</>}>{than}</ONoi>;
}

/** Hàng số nhỏ thay cho lưới ô số: "Luỹ kế ¥188,2M · ▲1,4% so … · …". */
export function HangSo({ children }: { children: ReactNode }) {
  return <div className="hang-so">{children}</div>;
}

export function MucSo({ nhan, gia, lop, chi_tiet }: { nhan: ReactNode; gia: ReactNode; lop?: string; chi_tiet?: ReactNode }) {
  const than = <><span className="hs-nhan">{nhan}</span> <b className={lop}>{gia}</b></>;
  return chi_tiet == null ? <span className="hs-muc">{than}</span>
    : <ONoi className="hs-muc" noi_dung={<><strong>{nhan}</strong>{chi_tiet}</>}>{than}</ONoi>;
}
```

- [ ] **Step 2: Thêm CSS cuối `giao_dien/src/chung/chung.css`**

```css
/* Hình dùng chung (chung/Hinh.tsx) */
.tng-ds{display:grid;gap:.3rem}
.tng-dong{display:grid;grid-template-columns:minmax(0,9.5rem) 1fr auto auto;align-items:center;gap:.5rem;
  padding:.12rem .2rem;border-radius:6px;color:inherit;text-decoration:none}
a.tng-dong:hover,.tng-dong:focus-visible{background:var(--nen-phu)}
.tng-ten{font-size:.76rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tng-thanh{height:9px;border-radius:99px;background:var(--vien-phu)}
.tng-day{display:block;height:100%;border-radius:99px}
.tng-so{font-size:.76rem;font-variant-numeric:tabular-nums;text-align:right}
.tng-phu{font-size:.7rem;font-variant-numeric:tabular-nums;min-width:3rem;text-align:right}
@media (max-width:520px){.tng-dong{grid-template-columns:minmax(0,6.5rem) 1fr auto}.tng-phu{display:none}}
.tc-thanh{display:flex;height:14px;border-radius:99px;overflow:hidden;background:var(--vien-phu)}
.tc-khuc{display:block;height:100%}
.tc-khuc:hover,.tc-khuc.chon{filter:brightness(1.12)}
.tc-chu-giai{display:flex;flex-wrap:wrap;gap:.25rem .85rem;margin-top:.45rem}
.tc-muc{display:inline-flex;align-items:center;gap:.3rem;font-size:.72rem;color:var(--chu-nhat);text-decoration:none}
.tc-muc b{color:var(--chu);font-variant-numeric:tabular-nums}
.tc-muc i{width:9px;height:9px;border-radius:50%;display:inline-block}
.tc-muc.chon{color:var(--chu);font-weight:600}
.so-lon{display:inline-flex;align-items:baseline;gap:.4rem;margin-bottom:.5rem;color:inherit;text-decoration:none}
.so-lon b{font-size:1.45rem;font-weight:700;letter-spacing:-.015em;font-variant-numeric:tabular-nums}
.so-lon span{font-size:.76rem;color:var(--chu-nhat)}
.hang-so{display:flex;flex-wrap:wrap;gap:.25rem 1rem;margin-bottom:.5rem;font-size:.76rem}
.hs-nhan{color:var(--chu-nhat)}
.hs-muc b{font-variant-numeric:tabular-nums}
```

- [ ] **Step 3: Kiểm kiểu + test + build**

Run: `cd giao_dien && npm test && npm run build`
Expected: PASS, không lỗi `tsc`.

- [ ] **Step 4: Commit**

```bash
git add giao_dien/src/chung/Hinh.tsx giao_dien/src/chung/chung.css kome/web/spa
git commit -m "feat(giao-dien): ThanhNgang, ThanhChong, SoLon, HangSo dung chung

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `BieuDo` — chạm hai lần mới `onBam`, và dòng ô nổi thêm

**Files:**
- Modify: `giao_dien/src/chung/BieuDo.tsx`

**Interfaces:**
- Consumes: `buocCham` (Task 1).
- Produces: `BieuDo` thêm prop `them_noi?: (i: number) => ReactNode` — nội dung thêm cuối ô nổi của điểm `i`.

- [ ] **Step 1: Sửa import và `Props`**

```tsx
import { useMemo, useRef, useState, type ReactNode } from "react";
import { useRong } from "./hooks";
import { buocCham } from "./o_noi_logic";
```
Trong `type Props` thêm sau `vach?`:
```tsx
  them_noi?: (i: number) => ReactNode;      // dòng thêm cuối ô nổi (vd %NS, biên gộp của tháng i)
```
Chữ ký hàm: `export function BieuDo({ nhan, nhan_day_du, chuoi, cao = 200, dinh_dang, dinh_dang_truc, onBam, moi_nhan, mo_ta, vach, them_noi }: Props) {`

- [ ] **Step 2: Chạm lần 1 chỉ chọn điểm.** Sau `const svgRef = useRef<SVGSVGElement>(null);` thêm:
```tsx
  const kieu = useRef("mouse");
  const daChon = useRef<number | null>(null);   // điểm đã hiện ô nổi trước lần chạm này
```
Thay `onPointerMove={chon}` … `onClick={...}` của `<svg>` bằng:
```tsx
        onPointerMove={chon} onPointerLeave={e => { if (e.pointerType === "mouse") datTro(null); }}
        onPointerDown={e => { kieu.current = e.pointerType; daChon.current = tro; chon(e); }}
        onKeyDown={e => {
          if (e.key === "ArrowRight") datTro(t => Math.min((t ?? -1) + 1, n - 1));
          else if (e.key === "ArrowLeft") datTro(t => Math.max((t ?? n) - 1, 0));
          else if (e.key === "Enter" && tro != null) onBam?.(tro);
          else if (e.key === "Escape") datTro(null);
        }}
        onClick={() => {
          if (tro == null) return;
          if (buocCham(daChon.current === tro, kieu.current) === "di") onBam?.(tro);
          kieu.current = "mouse";
        }}
```
(Chạm: `pointerdown` chọn điểm và nhớ điểm đã chọn TRƯỚC đó; `click` chỉ gọi `onBam` khi chạm lại đúng điểm đang mở. Chuột không đổi.)

- [ ] **Step 3: `them_noi` trong ô nổi.** Ngay trước `{onBam && <em>bấm để xem chi tiết</em>}` thêm:
```tsx
        {them_noi?.(tro)}
```
và đổi chữ gợi ý thành `{onBam && <em>{kieu.current === "touch" ? "chạm lần nữa để xem chi tiết" : "bấm để xem chi tiết"}</em>}`.

- [ ] **Step 4: Kiểm kiểu + test + build**

Run: `cd giao_dien && npm test && npm run build`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add giao_dien/src/chung/BieuDo.tsx kome/web/spa
git commit -m "feat(bieu-do): cham lan 1 hien so, lan 2 moi di; them_noi cho o noi

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Khối tiền — Chỉ số, Ngân sách, Theo tháng, Xu hướng, Tuổi nợ

**Files:**
- Modify: `giao_dien/src/tong_quan/khoi.tsx` — `KhoiKpi`, `OKpiCongNo`, `KhoiCongNo`, `DuongNganSach`, `KhoiNganSach`, `KhoiTheoThang`, `KhoiXuHuong`; imports.

**Interfaces:**
- Consumes: `ONoi`, `DongNoi` (Task 2); `ThanhChong`, `SoLon`, `HangSo`, `MucSo` (Task 3); `BieuDo.them_noi` (Task 4); `Khoi.cach_tinh`/`canh_bao`.
- Produces: helper nội bộ `OKpi` (dùng lại ở Task 7 không cần).

- [ ] **Step 1: Import** — đầu `khoi.tsx` thêm:
```tsx
import { DongNoi, ONoi } from "../chung/ONoi";
import { HangSo, MucSo, SoLon, ThanhChong, ThanhNgang, type DongThanh } from "../chung/Hinh";
```

- [ ] **Step 2: `KhoiKpi` + ô `OKpi`** — thay nguyên `KhoiKpi` và thêm `OKpi` ngay trên nó:

```tsx
/** Một ô của khối Chỉ số: nhãn · số lớn · (con: dòng kỳ so, đường nhỏ). Chi tiết trong ô nổi. */
function OKpi({ href, nhan, gia, lop, chi_tiet, chua, children }: {
  href?: string; nhan: string; gia: React.ReactNode; lop?: string; chi_tiet?: React.ReactNode; chua?: boolean; children?: React.ReactNode }) {
  return (
    <ONoi href={href} className={"o-kpi" + (chua ? " chua" : "")} noi_dung={<><strong>{nhan}</strong>{chi_tiet}</>}>
      <div className="nhan">{nhan}</div><div className={"gia" + (lop ? " " + lop : "")}>{gia}</div>{children}
    </ONoi>);
}

export function KhoiKpi() {
  const { data: d, isLoading, error } = useKhoi<Kpi>("kpi");
  const nm = useNhanMoc();
  const ns = d?.ngan_sach;
  return (
    <Khoi tieu_de={`Chỉ số · ${d?.khoang?.nhan ?? "tháng này"}`} dang_tai={isLoading} loi={error?.message}
      cach_tinh={d?.doanh_thu.tu_ngay ? `Doanh thu ${ngay(d.doanh_thu.tu_ngay)} – ${ngay(d.doanh_thu.den_ngay)}. Kho và khách tính ${nm}.` : undefined}>
      {d && <div className="o-kpi-luoi">
        <OKpi href="/bao-cao" nhan="Doanh thu" gia={gon(d.doanh_thu.gia_tri)}
          chi_tiet={<><DongNoi nhan={d.khoang?.nhan ?? "Tháng này"} gia={yen(d.doanh_thu.gia_tri)} />
            {d.doanh_thu.so_sanh.map(s => <DongNoi key={s.ma} nhan={hoa(s.nhan)} gia={s.co ? yen(s.dt_ck) : "không có dữ liệu"} />)}</>}>
          {d.doanh_thu.so_sanh.map(s => <DongSoSanh key={s.ma} nhan={s.nhan} co={s.co} nay={d.doanh_thu.gia_tri} ss={s.dt_ck} />)}
          <Spark gia_tri={d.doanh_thu.spark} so_sanh={d.doanh_thu.spark_ss} mau={(d.doanh_thu.tang ?? 0) >= 0 ? LUC.ok : LUC.do} />
        </OKpi>
        {d.ngan_sach_chi_theo_thang
          ? <OKpi chua nhan="Ngân sách" gia="chỉ theo tháng" chi_tiet={<div className="o-noi-chu">{NS_THEO_THANG}</div>} />
          : ns ? <OKpi href={KD.hien_ngan_sach ? "/ngan-sach" : "/bao-cao"} nhan={`Ngân sách ${thang_nhan(ns.thang)}`}
              gia={<span style={{ color: mauTienDo(ns.tien_do, ns.moc) }}>{pc(ns.tien_do)}</span>}
              chi_tiet={<><DongNoi nhan="Mốc hôm nay" gia={pc(ns.moc)} />
                <DongNoi nhan={ns.muc_tieu_den_hom_nay != null && ns.thuc_te < ns.muc_tieu_den_hom_nay ? "Thiếu so mốc" : "Vượt mốc"}
                  gia={ns.muc_tieu_den_hom_nay != null ? yen(Math.abs(ns.muc_tieu_den_hom_nay - ns.thuc_te)) : "—"} />
                <DongNoi nhan="Đã bán" gia={yen(ns.thuc_te)} /><DongNoi nhan="Ngân sách" gia={yen(ns.muc_tieu)} /></>}>
              <Spark gia_tri={ns.spark} mau={mauTienDo(ns.tien_do, ns.moc)} />
            </OKpi>
          : <OKpi href={KD.hien_ngan_sach ? "/ngan-sach" : undefined} chua nhan="Ngân sách" gia="chưa đặt"
              chi_tiet={<div className="o-noi-chu">Chưa đặt chỉ tiêu tháng này — đặt ở màn Ngân sách.</div>} />}
        {TN.cong_no && <OKpiCongNo />}
        <OKpi chua nhan="Phải trả 7 ngày" gia="chưa có" chi_tiet={<div className="o-noi-chu">{KD.chua_co.dong_tien ?? "Cần sổ phải trả."}</div>} />
        <OKpi href="/kho-hang" nhan="Kho cần xử lý" gia={so(d.kho.het_hang + d.kho.can_han + d.kho.qua_han)}
          lop={d.kho.het_hang + d.kho.qua_han ? "giam" : undefined}
          chi_tiet={<><DongNoi mau={LUC.do} nhan="Mã hết hàng" gia={so(d.kho.het_hang)} />
            <DongNoi mau={LUC.canh} nhan="Lô cận hạn" gia={so(d.kho.can_han)} />
            <DongNoi mau={LUC.do} nhan="Lô quá hạn" gia={so(d.kho.qua_han)} />
            <em>tính {nm}</em></>} />
        <OKpi href="/lien-he?tat_ca=1" nhan="Khách cần gọi" gia={so(d.khach.can_goi + d.khach.roi_bo)}
          chi_tiet={<><DongNoi mau={LUC.canh} nhan="Im lặng quá nhịp" gia={so(d.khach.can_goi)} />
            <DongNoi mau={LUC.do} nhan="Đã rời bỏ" gia={so(d.khach.roi_bo)} /><em>tính {nm}</em></>} />
      </div>}
    </Khoi>
  );
}
```
`NS_THEO_THANG` đang khai sau `DuongNganSach` — dời dòng `const NS_THEO_THANG = …` lên ngay trên `KhoiKpi` (sau `trongKhoang`).

- [ ] **Step 3: `OKpiCongNo` + `KhoiCongNo`** — thay cả hai:

```tsx
/** Ô "Phải thu quá hạn" của khối Chỉ số — đọc chung ảnh chụp của khối Tuổi nợ. */
function OKpiCongNo() {
  const { data: d, isLoading } = useKhoi<CongNo>("cong_no");
  if (isLoading) return <OKpi nhan="Phải thu quá hạn" gia="…" chua />;
  if (!d) return <OKpi chua nhan="Phải thu quá hạn" gia="chưa có" chi_tiet={<div className="o-noi-chu">Chưa nạp sổ 請求先元帳 nào.</div>} />;
  return (
    <OKpi href="/cong-no?tab=qua_han" nhan="Phải thu quá hạn" gia={gon(d.tq.qua_han)} lop={d.tq.qua_han ? "giam" : undefined}
      chi_tiet={<><DongNoi nhan="Phiếu quá hạn" gia={so(d.tq.so_phieu_qua_han)} />
        <DongNoi nhan="Tổng phải thu" gia={yen(d.tq.tong_phai_thu)} /><em>đến {ngay(d.moc)}</em></>} />);
}

export function KhoiCongNo() {
  const { data: d, isLoading, error } = useKhoi<CongNo>("cong_no");
  if (!isLoading && !error && !d) return <ChuaCoDuLieu gon tieu_de="Tuổi nợ phải thu" ly_do="Chưa nạp sổ 請求先元帳 nào — xuất từ OBC rồi nạp ở màn Kho dữ liệu." />;
  return (
    <Khoi tieu_de="Tuổi nợ phải thu" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/cong-no" }}
      phu={d ? `đến ${ngay_ngan(d.moc)}` : undefined} cach_tinh={d?.cach_tinh}>
      {d && <>
        <SoLon href="/cong-no?tab=qua_han" gia={gon(d.tq.qua_han)} lop={d.tq.qua_han ? "giam" : undefined} nhan="quá hạn"
          chi_tiet={<><DongNoi nhan="Tổng phải thu" gia={yen(d.tq.tong_phai_thu)} />
            <DongNoi nhan="Phiếu quá hạn" gia={so(d.tq.so_phieu_qua_han)} />
            <DongNoi nhan="Bên nhận hoá đơn quá hạn" gia={so(d.tq.so_ben_qua_han)} />
            {d.lau_nhat.length > 0 && <em>Nợ lâu / quá hạn nhiều nhất:</em>}
            {d.lau_nhat.map(x => <DongNoi key={x.ma} nhan={<span className="ten-jp">{x.ten}</span>} gia={gon(x.tien)} />)}</>} />
        <ThanhChong dinh_dang={gon} don_vi="Còn nợ"
          khuc={d.tq.tuoi.map(t => ({ khoa: t.nhom, nhan: t.nhan, dem: t.tien, mau: MAU_TUOI[t.nhom] ?? LUC.nhat,
            href: `/cong-no?nhom=${t.nhom}`, chi_tiet: <DongNoi nhan="Số phiếu" gia={so(t.dem)} /> }))} />
      </>}
    </Khoi>
  );
}
```

- [ ] **Step 4: `DuongNganSach`** — thay dòng `{!coSS && duong.nhan_ss && <div className="phu">…</div>}` bằng:
```tsx
      {!coSS && duong.nhan_ss && <div className="khoi-canh">{hoa(duong.nhan_ss)}: không vẽ được đường luỹ kế để so (không có dữ liệu, hoặc kỳ so không cùng gốc tháng).</div>}
```

- [ ] **Step 5: `KhoiNganSach`** — thay nguyên hàm:

```tsx
export function KhoiNganSach() {
  const { data: d, isLoading, error } = useKhoi<NganSach | null>("ns_thang");
  if (d?.chi_theo_thang) return <ChuaCoDuLieu gon tieu_de="Tiến độ ngân sách" ly_do={NS_THEO_THANG} />;
  const nguoi = [...(d?.nguoi ?? [])].sort((a, b) => b.thuc_te - a.thuc_te);
  const maxNS = Math.max(1, ...nguoi.map(n => Math.max(n.muc_tieu ?? 0, n.thuc_te, n.dt_ss ?? 0)));
  const ssN = d?.so_sanh;
  const vuot = !!d && d.muc_tieu_den_hom_nay != null && d.thuc_te >= d.muc_tieu_den_hom_nay;
  return (
    <Khoi tieu_de={`Ngân sách ${d ? thang_nhan(d.thang) : ""}`} dang_tai={isLoading} loi={error?.message}
      nhan={d ? `Còn ${d.ngay_kd_con_lai} ngày làm việc` : undefined} lien_ket={{ href: "/bao-cao", chu: "Xem chi tiết" }}
      phu={ssN?.co ? <>so {ssN.nhan}</> : undefined}
      cach_tinh={d ? <>{d.co_ngan_sach ? `Vạch đen = mốc đáng lẽ đạt tới hôm nay (${pc(d.moc)}) — tính theo ngày làm việc, trừ ngày lễ.` : "Thanh = doanh thu thực tế của từng người phụ trách."}
        {ssN?.co ? ` Vạch đứt = doanh thu ${ssN.nhan}.` : ""}</> : undefined}
      canh_bao={d && !d.co_ngan_sach ? <>Chưa đặt chỉ tiêu tháng này.{KD.hien_ngan_sach && <> <a href="/ngan-sach">Đặt chỉ tiêu →</a></>}</>
        : ssN && !ssN.co ? `${hoa(ssN.nhan)}: không có dữ liệu để so.` : undefined}>
      {d && <div className="ns-luoi">
        <div className="ns-so">
          {d.co_ngan_sach
            ? <SoLon gia={pc(d.tien_do)} mau={mauTienDo(d.tien_do, d.moc)} nhan="tiến độ công ty"
                chi_tiet={<><DongNoi nhan="Mốc hôm nay" gia={pc(d.moc)} />
                  <DongNoi nhan={vuot ? "Vượt mốc" : "Thiếu so mốc"} gia={yen(Math.abs((d.muc_tieu_den_hom_nay ?? 0) - d.thuc_te))} />
                  <DongNoi nhan="Ngân sách" gia={yen(d.muc_tieu)} />
                  <DongNoi nhan="Cần bán mỗi ngày" gia={yen(d.can_ban_moi_ngay)} />
                  {d.can_ban_moi_ngay != null && d.nhip_chuan
                    ? <DongNoi nhan="So nhịp chuẩn" gia={`${(d.can_ban_moi_ngay / d.nhip_chuan).toFixed(2).replace(".", ",")}×`} />
                    : <em>tháng đã hết ngày làm việc</em>}</>} />
            : <SoLon gia={gon(d.thuc_te)} nhan="đã bán tháng này"
                chi_tiet={<DongNoi nhan="Ngày làm việc" gia={`${d.ngay_kd_da_qua}/${d.ngay_kd}`} />} />}
        </div>
        <div className="ns-thanh">
          {/* Ngân sách CHUNG của công ty đứng trước (doanh thu + lãi gộp, nhập thẳng — 041), rồi mới tới từng người. */}
          <div className="ns-cong-ty">
            {([["Doanh thu", d.thuc_te, d.muc_tieu, d.tien_do, d.moc, d.co_ngan_sach],
               ["Lãi gộp", d.thuc_te_lg, d.muc_tieu_lg, d.tien_do_lg, d.moc_lg, d.co_ngan_sach_lg]] as const).map(([ten, tt, mt, td, moc, co]) => (
              <ONoi key={ten} className="ns-khoi-dong" noi_dung={<><strong>{ten} · toàn công ty</strong>
                <DongNoi nhan="Thực tế" gia={yen(tt)} /><DongNoi nhan="Ngân sách" gia={co ? yen(mt) : "chưa đặt"} />
                {co && <DongNoi nhan="Mốc hôm nay" gia={pc(moc)} />}</>}>
                <div className="ns-dong"><span>{ten}</span>
                  {co ? <b style={{ color: mauTienDo(td, moc) }}>{pc(td)}</b> : <em className="nhat-chu">chưa đặt</em>}</div>
                {co && <ThanhMoc ty_le={td} moc={moc} mau={mauTienDo(td, moc)} />}
              </ONoi>))}
          </div>
          {nguoi.map(n => (
            <ONoi key={n.ma} className="ns-khoi-dong" noi_dung={<><strong>{tenNguoi(n.ten, n.ma)}</strong>
              <DongNoi nhan="Doanh thu" gia={yen(n.thuc_te)} />
              <DongNoi nhan="Chỉ tiêu" gia={n.muc_tieu ? yen(n.muc_tieu) : "chưa có"} />
              {n.muc_tieu_den_hom_nay != null && <DongNoi nhan="Mốc hôm nay" gia={yen(n.muc_tieu_den_hom_nay)} />}
              {n.muc_tieu_lg != null && <DongNoi nhan="Lãi gộp" gia={pc(n.tien_do_lg)} />}
              {ssN?.co && <DongNoi nhan={hoa(ssN.nhan)} gia={yen(n.dt_ss)} />}</>}>
              <div className="ns-dong"><span>{tenNguoi(n.ten, n.ma)}</span>
                {ssN && <TdSs nay={n.thuc_te} ss={n.dt_ss} nhan={ssN.nhan} />}
                <b style={{ color: mauTienDo(n.tien_do, d.moc) }}>{n.muc_tieu ? pc(n.tien_do) : gon(n.thuc_te)}</b></div>
              <div className="ns-ba-lop">
                <div className="lop-ns" style={{ width: `${(n.muc_tieu ?? 0) / maxNS * 100}%` }} />
                <div className="lop-tt" style={{ width: `${Math.min(n.thuc_te / maxNS, 1) * 100}%`, background: n.muc_tieu ? mauTienDo(n.tien_do, d.moc) : LUC.nhat }} />
                {n.muc_tieu_den_hom_nay != null && <div className="lop-moc" style={{ left: `${n.muc_tieu_den_hom_nay / maxNS * 100}%` }} />}
                {ssN && <VachSoSanh ty_le={n.dt_ss != null ? n.dt_ss / maxNS : null} nhan={`${hoa(ssN.nhan)}: ${yen(n.dt_ss)}`} />}
              </div>
            </ONoi>))}
        </div>
      </div>}
      {d?.duong && <DuongNganSach duong={d.duong} />}
    </Khoi>
  );
}
```
Thêm vào `tong_quan.css`: `.ns-khoi-dong{display:block}`.

- [ ] **Step 6: `KhoiTheoThang`** — thay phần `return (…)` (giữ nguyên các biến tính phía trên):

```tsx
  return (
    <Khoi tieu_de="Theo từng tháng" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao", chu: "Báo cáo" }}
      phu={ss ? <>so {ss.nhan}</> : undefined}
      cach_tinh={d?.company_fy ? `Cả kỳ chứa ${kx?.nhan ?? "khoảng xem"} (kỳ kết thúc 7/${d.company_fy}). Cột đậm = thuộc khoảng xem; cột viền đứt = ${ss?.nhan ?? "kỳ so"}; đường = ngân sách tháng.` : undefined}
      canh_bao={!d ? undefined
        : ss && ss.co && ss.lech_thang == null ? "Kỳ so không lệch tròn tháng — không so theo tháng được."
        : ss && !ck ? `${hoa(ss.nhan)}: không có dữ liệu để so.`
        : thangNay && t.some(x => x.thang === thangNay)
          ? (d.cat_cung_ngay ? `Tháng đang chạy chưa đủ ngày — %NS chưa so ngang được; cột ma của tháng này đã cắt cùng dải ngày ở ${ss?.nhan}.`
            : "Tháng đang chạy chưa đủ ngày — %NS và phép so của tháng này chưa so ngang được.")
          : undefined}>
      {d && <>
        <HangSo>
          <MucSo nhan="Luỹ kế" gia={gon(tong)} chi_tiet={<DongNoi nhan="Tháng có dữ liệu"
            gia={t.length ? `${t.length} (${thang_nhan(t[0].thang)} – ${thang_nhan(t[t.length - 1].thang)})` : "0"} />} />
          <MucSo nhan={<>so {ss?.nhan ?? "kỳ so"}</>} gia={ck ? thay_doi(dtCK / ck - 1) : "—"} lop={ck ? (dtCK >= ck ? "tang" : "giam") : undefined}
            chi_tiet={ck ? <><DongNoi nhan="Tháng đối chiếu" gia={so(coCK.length)} /><DongNoi nhan="Chênh" gia={gon(dtCK - ck)} /></> : undefined} />
          <MucSo nhan="Đạt ngân sách" gia={coNS.length ? `${dat}/${coNS.length}` : "—"}
            chi_tiet={<div className="o-noi-chu">{coNS.length ? "Số tháng đã khép lại đạt ngân sách." : "Chưa đặt chỉ tiêu tháng nào."}</div>} />
          <MucSo nhan="Cao nhất" gia={cao ? thang_nhan(cao.thang) : "—"}
            chi_tiet={cao ? <><DongNoi nhan="Doanh thu" gia={yen(cao.doanh_thu)} /><DongNoi nhan="Biên gộp" gia={pc(cao.ty_suat)} /></> : undefined} />
        </HangSo>
        <BieuDo nhan={t.map(x => thang_nhan(x.thang))} chuoi={chuoi} cao={200} mo_ta={`Doanh thu từng tháng của kỳ so ngân sách và ${ss?.nhan ?? "kỳ so"}`}
          dinh_dang={v => yen(v)} dinh_dang_truc={v => gon(v)}
          vach={thangNay ? { i: t.findIndex(x => x.thang === thangNay), chu: "đang chạy" } : null}
          them_noi={i => { const x = t[i]; return x && <>
            <div>%NS<b>{x.ngan_sach ? pc(x.doanh_thu / x.ngan_sach, 0) : "—"}</b></div>
            <div>Biên gộp<b>{pc(x.ty_suat)}</b></div>
            <div>Khách<b>{so(x.so_khach)}</b></div></>; }} />
      </>}
    </Khoi>
  );
```

- [ ] **Step 7: `KhoiXuHuong`** — thay phần `return (…)`:

```tsx
  return (
    <Khoi tieu_de={`Xu hướng · ${kx?.nhan ?? ""}`} dang_tai={isLoading} loi={error?.message}
      phu={ss?.co ? <>so {ss.nhan}</> : undefined}
      cach_tinh={ss?.co ? `${ds.length <= 40 ? "Cột viền đứt" : "Nét đứt"}: ${ss.nhan} (${ngay(ss.tu)} → ${ngay(ss.den)}).` : undefined}
      canh_bao={ss && !ss.co ? `${hoa(ss.nhan)}: không có dữ liệu để so.` : ss && !coCk ? "Kỳ so khác độ dài — chỉ so tổng." : undefined}>
      {d && <>
        <HangSo>
          <MucSo nhan={`Tổng ${ds.length} ${theoNgay ? "ngày" : "tháng"}`} gia={gon(tong)} />
          <MucSo nhan={<>so {ss?.nhan ?? "—"}</>} gia={coCk && tongCk > 0 ? thay_doi(tong / tongCk - 1) : "—"} lop={tong >= tongCk ? "tang" : "giam"}
            chi_tiet={coCk ? <DongNoi nhan={hoa(ss?.nhan)} gia={yen(tongCk)} /> : undefined} />
          <MucSo nhan={theoNgay ? "TB / ngày có bán" : "TB / tháng"} gia={gon(theoNgay ? (coNgay ? tong / coNgay : null) : (ds.length ? tong / ds.length : null))} />
        </HangSo>
        <BieuDo nhan={ds.map(x => theoNgay ? ngay_ngan(x[0]) : thang_nhan(x[0]))} nhan_day_du={ds.map(x => theoNgay ? ngay(x[0]) : thang_nhan(x[0]))}
          cao={200} mo_ta={`Doanh thu ${kx?.nhan ?? ""} so ${ss?.nhan ?? ""}`}
          chuoi={[
            { ten: theoNgay ? "Doanh thu ngày" : "Doanh thu tháng", kieu: ds.length <= 40 ? "cot" : "duong", gia_tri: ds.map(x => x[1]), mau: "var(--lien-ket)", so_voi: 1 },
            // Cột → cột ma, đường → nét đứt (đặc tả 2026-09-28 §6).
            { ten: hoa(ss?.nhan) || "Kỳ so", kieu: ds.length <= 40 ? "cot_ma" : "duong_dut", gia_tri: ds.map(x => x[4]), mau: MAU_SS },
          ]}
          dinh_dang={v => yen(v)} dinh_dang_truc={v => gon(v)} />
      </>}
    </Khoi>
  );
```

- [ ] **Step 8: Dọn CSS/biến thừa** — xoá `max` không dùng trong `KhoiCongNo` cũ (đã thay), xoá quy tắc `.tuoi-no*` trong `tong_quan.css` nếu không còn class nào dùng (`grep -n "tuoi-no" giao_dien/src -r`).

- [ ] **Step 9: Test + build + kiểm lượt hỏi**

Run: `cd giao_dien && npm test && npm run build && cd .. && pytest tests/test_tong_quan.py tests/test_nguon_dung.py tests/test_api.py -q`
Expected: tất cả PASS (gồm `test_ban_build_khop_ma_nguon`, `test_trang_chu_khong_qua_9_truy_van`).

- [ ] **Step 10: Commit**

```bash
git add giao_dien/src/tong_quan/khoi.tsx giao_dien/src/tong_quan/tong_quan.css kome/web/spa
git commit -m "feat(tong-quan): khoi tien it chu - chi so, ngan sach, theo thang, xu huong, tuoi no

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Logic việc hôm nay và dải hạn dùng

**Files:**
- Create: `giao_dien/src/tong_quan/viec_logic.ts`, `giao_dien/src/tong_quan/viec_logic.test.ts`
- Create: `giao_dien/src/tong_quan/han_logic.ts`, `giao_dien/src/tong_quan/han_logic.test.ts`

**Interfaces:**
- Produces:
  - `type ViecTho = { muc: "gap" | "canh" | "thuong"; tag: string; chu: string }`
  - `tenViec(chu: string): string` — `"Gọi X — im 53 ngày"` → `"X"`; câu khác giữ nguyên.
  - `sapViec<T extends ViecTho>(v: T[]): T[]` — `gap` → `canh` → `thuong`, ổn định trong cùng mức.
  - `demTheoTag(v: ViecTho[]): { tag: string; muc: ViecTho["muc"]; dem: number }[]` — theo thứ tự xuất hiện đầu tiên.
  - `mienHan(con_lai: number[]): { tu: number; den: number }` — `tu = min(-15, min)`, `den = max(90, max)`.
  - `xHan(c: number, m: { tu: number; den: number }): number` (0..1)
  - `banKinh(gia_tri: number, max: number): number` — 4..12 px, ∝ √.

- [ ] **Step 1: Viết test thất bại**

`giao_dien/src/tong_quan/viec_logic.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { demTheoTag, sapViec, tenViec } from "./viec_logic";

describe("tenViec", () => {
  it("lấy tên khách ra khỏi câu gọi", () => {
    expect(tenViec("Gọi MANH NGA合同会社 — im 53 ngày")).toBe("MANH NGA合同会社");
    expect(tenViec("Gọi AMILY — mua đều 3/3 tháng, tháng này chưa có đơn")).toBe("AMILY");
  });
  it("câu không phải gọi khách giữ nguyên", () =>
    expect(tenViec("Chưa nạp 得意先全情報 hôm nay")).toBe("Chưa nạp 得意先全情報 hôm nay"));
});

describe("sapViec", () => {
  it("gấp trước, cảnh sau, thường cuối — giữ thứ tự trong cùng mức", () => {
    const v = [{ muc: "thuong", tag: "a", chu: "1" }, { muc: "gap", tag: "b", chu: "2" },
      { muc: "canh", tag: "c", chu: "3" }, { muc: "gap", tag: "b", chu: "4" }] as const;
    expect(sapViec([...v]).map(x => x.chu)).toEqual(["2", "4", "3", "1"]);
  });
});

describe("demTheoTag", () => {
  it("đếm theo tag, thứ tự xuất hiện đầu tiên", () => {
    const v = [{ muc: "canh", tag: "Quá hạn", chu: "1" }, { muc: "gap", tag: "Lâu không mua", chu: "2" },
      { muc: "canh", tag: "Quá hạn", chu: "3" }] as const;
    expect(demTheoTag([...v])).toEqual([{ tag: "Quá hạn", muc: "canh", dem: 2 }, { tag: "Lâu không mua", muc: "gap", dem: 1 }]);
  });
});
```

`giao_dien/src/tong_quan/han_logic.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { banKinh, mienHan, xHan } from "./han_logic";

describe("mienHan", () => {
  it("luôn phủ ít nhất −15 → 90 ngày", () => expect(mienHan([10, 40])).toEqual({ tu: -15, den: 90 }));
  it("giãn theo lô quá hạn lâu / còn xa", () => expect(mienHan([-40, 150])).toEqual({ tu: -40, den: 150 }));
  it("rỗng vẫn có miền", () => expect(mienHan([])).toEqual({ tu: -15, den: 90 }));
});

describe("xHan", () => {
  it("tuyến tính trong miền, kẹp 0..1", () => {
    const m = { tu: -10, den: 90 };
    expect(xHan(-10, m)).toBe(0);
    expect(xHan(40, m)).toBe(0.5);
    expect(xHan(200, m)).toBe(1);
  });
});

describe("banKinh", () => {
  it("4 px cho 0, 12 px cho lớn nhất, ∝ căn bậc hai", () => {
    expect(banKinh(0, 100)).toBe(4);
    expect(banKinh(100, 100)).toBe(12);
    expect(banKinh(25, 100)).toBe(8);
  });
  it("giá trị âm / max 0 → 4", () => { expect(banKinh(-5, 100)).toBe(4); expect(banKinh(5, 0)).toBe(4); });
});
```

- [ ] **Step 2: Chạy, xác nhận thất bại**

Run: `cd giao_dien && npx vitest run src/tong_quan/viec_logic.test.ts src/tong_quan/han_logic.test.ts`
Expected: FAIL — không tìm thấy module.

- [ ] **Step 3: Viết mã**

`giao_dien/src/tong_quan/viec_logic.ts`:
```ts
// Logic thuần của khối "Việc cần làm hôm nay" (đặc tả 2026-09-28-tong-quan-it-chu-design.md §5).
// `chu` là câu của MÁY CHỦ (kome/khoi_tong_quan.py) — dòng chỉ hiện TÊN, câu đầy đủ vào ô nổi.
export type ViecTho = { muc: "gap" | "canh" | "thuong"; tag: string; chu: string };

export function tenViec(chu: string): string {
  const m = /^Gọi\s+(.+?)\s+—\s/.exec(chu);
  return m ? m[1] : chu;
}

const THU_TU: Record<ViecTho["muc"], number> = { gap: 0, canh: 1, thuong: 2 };

export function sapViec<T extends ViecTho>(v: T[]): T[] {
  return v.map((x, i) => [x, i] as const).sort((a, b) => THU_TU[a[0].muc] - THU_TU[b[0].muc] || a[1] - b[1]).map(x => x[0]);
}

export function demTheoTag(v: ViecTho[]): { tag: string; muc: ViecTho["muc"]; dem: number }[] {
  const m = new Map<string, { tag: string; muc: ViecTho["muc"]; dem: number }>();
  for (const x of v) {
    const c = m.get(x.tag);
    if (c) c.dem += 1; else m.set(x.tag, { tag: x.tag, muc: x.muc, dem: 1 });
  }
  return [...m.values()];
}
```

`giao_dien/src/tong_quan/han_logic.ts`:
```ts
// Dải thời gian của khối "Sản phẩm sắp hết hạn": trục ngang = số ngày còn tới hạn,
// cỡ chấm ∝ √giá trị tồn (diện tích ∝ tiền).
export function mienHan(con_lai: number[]): { tu: number; den: number } {
  return { tu: Math.min(-15, ...con_lai), den: Math.max(90, ...con_lai) };
}

export function xHan(c: number, m: { tu: number; den: number }): number {
  return Math.max(0, Math.min(1, (c - m.tu) / (m.den - m.tu || 1)));
}

export function banKinh(gia_tri: number, max: number): number {
  if (!(max > 0) || !(gia_tri > 0)) return 4;
  return 4 + 8 * Math.sqrt(Math.min(gia_tri, max) / max);
}
```

- [ ] **Step 4: Chạy, xác nhận qua**

Run: `cd giao_dien && npx vitest run src/tong_quan/viec_logic.test.ts src/tong_quan/han_logic.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add giao_dien/src/tong_quan/viec_logic.ts giao_dien/src/tong_quan/viec_logic.test.ts giao_dien/src/tong_quan/han_logic.ts giao_dien/src/tong_quan/han_logic.test.ts
git commit -m "feat(tong-quan): logic thuan viec hom nay va dai han dung

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Khối khách — Việc, Tháng này chưa mua, Khách mới, Sức khoẻ, Danh sách khách

**Files:**
- Modify: `giao_dien/src/tong_quan/khoi.tsx` — `KhoiViec`, `KhoiThangNay`, `KhoiKhachMoi`, `KhoiSucKhoe`, `KhoiDanhSachKhach` (xoá `UU_TIEN`, `CotSap`); import `viec_logic`.
- Modify: `giao_dien/src/tong_quan/tong_quan.css`

**Interfaces:**
- Consumes: `ThanhNgang`, `DongThanh`, `ThanhChong`, `SoLon` (Task 3); `DongNoi`, `ONoi` (Task 2); `tenViec`, `sapViec`, `demTheoTag` (Task 6).

- [ ] **Step 1: Import** — thêm vào đầu `khoi.tsx`:
```tsx
import { demTheoTag, sapViec, tenViec } from "./viec_logic";
```

- [ ] **Step 2: `KhoiViec`** — thay nguyên hàm:

```tsx
const MAU_MUC: Record<Viec["muc"], string> = { gap: LUC.do, canh: LUC.canh, thuong: LUC.nhat };
const SO_VIEC_GON = 5;

export function KhoiViec() {
  const [tatCa, datTatCa] = useState(false);
  const [loc, datLoc] = useState<string | null>(null);
  const [moRong, datMoRong] = useState(false);
  const { data: d, isLoading, error } = useKhoi<{ viec: Viec[]; thieu_nguon: string[] }>("viec_hom_nay", true, tatCa ? "tat_ca=1" : "");
  const khoa = `kome_viec_xong_${new Date().toISOString().slice(0, 10)}`;
  const [xong, datXong] = useState<Record<string, boolean>>(() => { try { return JSON.parse(localStorage.getItem(khoa) || "{}"); } catch { return {}; } });
  const v = d?.viec ?? [];
  const soXong = v.filter(x => xong[x.chu]).length;
  const bat = (c: string) => { const m = { ...xong, [c]: !xong[c] }; datXong(m); try { localStorage.setItem(khoa, JSON.stringify(m)); } catch { /* */ } };
  const ds = sapViec(v.filter(x => !loc || x.tag === loc));
  const hien = moRong || loc ? ds : ds.slice(0, SO_VIEC_GON);
  return (
    <Khoi tieu_de="Việc hôm nay" dang_tai={isLoading} loi={error?.message}
      nhan={v.length ? `${soXong}/${v.length} xong` : undefined} mau_nhan={soXong === v.length ? "ok" : "nhat"}
      phu={KD.nguoi?.sale ? <button type="button" className="chip" aria-pressed={!tatCa} onClick={() => datTatCa(t => !t)}>{tatCa ? "Mọi người" : "Của tôi"}</button> : undefined}
      cach_tinh={d ? `Chưa gom được việc từ ${d.thieu_nguon.join(", ")} — chưa có nguồn dữ liệu. Dấu "xong" chỉ nhớ trên máy này, trong hôm nay. Bấm một khúc của thanh để lọc theo lý do.` : undefined}>
      {d && <>
        {v.length > 0 && <ThanhChong dinh_dang={so} don_vi="Việc"
          khuc={demTheoTag(v).map(t => ({ khoa: t.tag, nhan: t.tag, dem: t.dem, mau: MAU_MUC[t.muc], chon: loc === t.tag,
            onBam: () => datLoc(l => (l === t.tag ? null : t.tag)) }))} />}
        <div className="viec-ds">
          {hien.map(x => (
            <div key={x.chu} className={"viec-dong" + (xong[x.chu] ? " xong" : "")}>
              <input type="checkbox" checked={!!xong[x.chu]} onChange={() => bat(x.chu)} aria-label={`Đánh dấu xong: ${x.chu}`} />
              <i className="viec-cham" style={{ background: MAU_MUC[x.muc] }} aria-hidden="true" />
              <ONoi href={x.lien_ket} className="viec-chu ten-jp"
                noi_dung={<><strong>{x.tag}</strong><div className="o-noi-chu">{x.chu}</div>{x.han && <DongNoi nhan="Hạn" gia={x.han} />}</>}>
                {tenViec(x.chu)}</ONoi>
            </div>))}
          {!v.length && <div className="trong">Không có việc nào hôm nay.</div>}
          {!moRong && !loc && ds.length > SO_VIEC_GON &&
            <button type="button" className="lien-ket viec-them" onClick={() => datMoRong(true)}>+{ds.length - SO_VIEC_GON} việc</button>}
        </div>
      </>}
    </Khoi>
  );
}
```
CSS thêm vào `tong_quan.css`:
```css
.viec-ds{margin-top:.55rem}
.viec-cham{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0}
.viec-dong .viec-chu{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:inherit;text-decoration:none}
.viec-them{font-size:.74rem;margin-top:.35rem}
```
(Giữ quy tắc `.viec-dong` sẵn có; xoá `.viec-han`, `.viec-tt` nếu `grep` không còn chỗ dùng.)

- [ ] **Step 3: `KhoiThangNay`** — thay phần `return (…)` (giữ các dòng tính `tatCa`, `d`, `giu`, `da`, `truoc`):

```tsx
  return (
    <Khoi tieu_de="Tháng này chưa mua" dang_tai={isLoading} loi={error?.message}
      phu={d?.thang ? <>{thang_nhan(d.thang)} · đến {ngay_ngan(d.ngay_moc ?? "")}
        {KD.nguoi?.sale && <button type="button" className="chip" aria-pressed={!tatCa} onClick={() => datTatCa(t => !t)}
          style={{ marginLeft: ".4rem" }}>{tatCa ? "Mọi người" : "Của tôi"}</button>}</> : undefined}
      lien_ket={{ href: `/lien-he?ly_do=thang_nay_chua_mua${giu}` }}
      cach_tinh={d ? `${d.cach_tinh} Bộ đếm là của cả công ty; thanh = trung bình mỗi tháng, xếp giảm dần.` : undefined}>
      {d && <>
        <SoLon gia={so(d.dem.tre ?? 0)} nhan="khách mua đều chưa có đơn"
          chi_tiet={<><DongNoi nhan="Đã mua tháng này" gia={`${so(da)} khách`} />
            {truoc > 0 && <DongNoi nhan="Tháng trước đến cùng ngày" gia={<>{so(truoc)} <span className={da >= truoc ? "tang" : "giam"}>({thay_doi(da / truoc - 1, 0)})</span></>} />}
            {(d.dem.chua_toi_ngay ?? 0) > 0 && <DongNoi nhan="Thường mua muộn hơn — chưa tới ngày" gia={so(d.dem.chua_toi_ngay)} />}</>} />
        {d.khach.length
          ? <ThanhNgang dong={d.khach.slice(0, 10).map((k): DongThanh => ({
              khoa: k.ma, ten: k.ten, ten_jp: true, gia_tri: k.tb_thang, chu: gon(k.tb_thang), mau: LUC.canh,
              href: `/khach-hang/${k.ma}`,
              chi_tiet: <><DongNoi nhan="Mua" gia={`${k.so_thang}/3 tháng trước`} /><DongNoi nhan="TB / tháng" gia={yen(k.tb_thang)} />
                <DongNoi nhan="Tháng trước" gia={yen(k.thang_truoc)} /></> }))} />
          : <div className="trong">Không có khách mua đều nào đang trễ tháng này.</div>}
      </>}
    </Khoi>
  );
```
(Không truyền `ss` cho `ThanhNgang`: "tháng trước" KHÔNG phải kỳ so — vạch đứt chỉ dành cho kỳ so.)

- [ ] **Step 4: `KhoiKhachMoi`** — thay nguyên hàm:

```tsx
export function KhoiKhachMoi() {
  const { data: d, isLoading, error } = useKhoi<KhachMoiKhoi>("khach_moi");
  const t = d?.thang ?? [];
  const chua = (d?.khach ?? []).filter(k => !k.da_mua);
  return (
    <Khoi tieu_de="Khách mới" phu={d?.khoang?.nhan} cach_tinh={d?.cach_tinh}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}>
      {d && <>
        <SoLon gia={so(d.so_khach)} nhan="khách mới đăng ký" />
        {d.so_sanh.map(s => <DongSoSanh key={s.ma} nhan={s.nhan} co={s.co && s.so_khach != null}
          nay={s.so_khach_nay} ss={s.so_khach} />)}
        <ThanhChong dinh_dang={so} don_vi="Khách" khuc={[
          { khoa: "da", nhan: "Đã có đơn", dem: d.da_mua, mau: "var(--lien-ket)" },
          { khoa: "chua", nhan: "Chưa có đơn", dem: d.chua_mua, mau: LUC.canh,
            chi_tiet: <>{chua.slice(0, 10).map(k => <DongNoi key={k.ma} nhan={<span className="ten-jp">{k.ten}</span>} gia={ngay_ngan(k.ngay_dang_ky)} />)}
              {d.chua_mua > Math.min(chua.length, 10) && <em>… và {so(d.chua_mua - Math.min(chua.length, 10))} khách nữa</em>}</> },
        ]} />
        <BieuDo nhan={t.map(x => thang_nhan(x.thang))} nhan_day_du={t.map(x => `Tháng ${thang_nhan(x.thang)}`)} cao={130}
          mo_ta="Số khách mới đăng ký từng tháng, 12 tháng gần nhất, và số đã có đơn"
          chuoi={[
            { ten: "Đăng ký", kieu: "cot_nen", gia_tri: t.map(x => x.so_khach), mau: "var(--vien)", so_voi: t.some(x => x.so_khach_ss != null) ? 2 : undefined },
            { ten: "Đã có đơn", kieu: "cot", gia_tri: t.map(x => x.da_mua), mau: "var(--lien-ket)",
              mau_tung_cot: t.map(x => trongKhoang(d.khoang, x.thang) ? "var(--lien-ket)" : MO) },
            // Đã có hai lớp cột -> kỳ so là NÉT ĐỨT, không thêm lớp cột thứ ba (đặc tả §6).
            ...(t.some(x => x.so_khach_ss != null) ? [{ ten: `Đăng ký · ${d.ss?.nhan ?? "kỳ so"}`, kieu: "duong_dut" as const,
              gia_tri: t.map(x => x.so_khach_ss), mau: MAU_SS }] : []),
          ]}
          dinh_dang={v => `${so(v)} khách`} dinh_dang_truc={v => so(v)} />
      </>}
    </Khoi>
  );
}
```

- [ ] **Step 5: `KhoiSucKhoe`** — thay phần `return (…)`:

```tsx
  return (
    <Khoi tieu_de="Sức khoẻ khách" phu={`tính ${nm}`} dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}
      cach_tinh="Cần gọi lại = im lặng quá nhịp mua riêng của CHÍNH từng khách (không phải một ngưỡng chung). Bấm một khúc để mở danh sách khách đó.">
      {d && <>
        <SoLon gia={so(hd)} nhan="khách đang mua" />
        <ThanhChong dinh_dang={so} don_vi="Khách"
          khuc={d.nhom.map(n => ({ khoa: n, nhan: d.nhan[n], dem: d.dem[n] ?? 0, mau: MAU_TT[n], href: `/khach-hang?loc=${n}&tat_ca=1` }))} />
      </>}
    </Khoi>
  );
```
(Biến `tong` trong hàm không còn dùng — xoá.)

- [ ] **Step 6: `KhoiDanhSachKhach`** — thay nguyên hàm, xoá `UU_TIEN` và `CotSap`:

```tsx
const VIEC_TT: Record<string, string> = { da_roi_bo: "Gọi lại ngay", canh_bao: "Gọi lại trong tuần" };
const SO_KHACH_GON = 15;

export function KhoiDanhSachKhach() {
  const { data: d, isLoading, error } = useKhoi<{ khach: KhachDS[]; nhan: Record<string, string>; khoang: KhoangMayChu | null;
    so_sanh: { ma: string; nhan: string; co: boolean; tu: string; den: string } | null }>("danh_sach_khach");
  const nm = useNhanMoc();
  const ss = d?.so_sanh;
  const ds = [...(d?.khach ?? [])].sort((a, b) => b.thang_nay - a.thang_nay).slice(0, SO_KHACH_GON);
  return (
    <Khoi tieu_de="Khách lớn nhất" phu={d ? <>{d.khoang?.nhan}{ss?.co ? <> · so {ss.nhan}</> : null}</> : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}
      cach_tinh={`${SO_KHACH_GON} khách doanh thu cao nhất trong khoảng xem. Màu thanh: đỏ = gọi lại ngay, cam = gọi lại trong tuần, xanh = bình thường. Im lặng = số ngày chưa mua ÷ nhịp mua riêng của khách, tính ${nm}.${ss?.co ? ` Vạch đứt = ${ss.nhan}.` : ""}`}
      canh_bao={ss && !ss.co ? `${hoa(ss.nhan)}: không có dữ liệu để so.` : undefined}>
      {d && <ThanhNgang nhan_ss={ss?.co ? hoa(ss.nhan) : undefined} dong={ds.map((k): DongThanh => ({
        khoa: k.ma, ten: k.ten, ten_jp: true, gia_tri: k.thang_nay, ss: ss?.co ? k.thang_truoc : null, chu: gon(k.thang_nay),
        phu: <TdSs nay={k.thang_nay} ss={k.thang_truoc} nhan={ss?.nhan ?? ""} />,
        mau: MAU_TT[k.trang_thai] ?? LUC.nhat, href: `/khach-hang/${k.ma}`,
        chi_tiet: <>
          <DongNoi nhan={d.khoang?.nhan ?? "Khoảng xem"} gia={yen(k.thang_nay)} />
          {ss?.co && <DongNoi nhan={hoa(ss.nhan)} gia={k.thang_truoc != null ? yen(k.thang_truoc) : "—"} />}
          <DongNoi nhan="Doanh thu 12 tháng" gia={gon(k.doanh_thu)} />
          <DongNoi nhan="Im lặng" gia={k.ty_le_im_lang != null ? `${k.ty_le_im_lang.toFixed(1).replace(".", ",")}×${k.nhip_ngay ? ` (im ${k.so_ngay_im_lang} / nhịp ${Math.round(k.nhip_ngay)} ngày)` : ""}` : "—"} />
          <DongNoi nhan="Phụ trách" gia={tenNguoi(k.ten_sale, k.sale ?? "—")} />
          <DongNoi mau={MAU_TT[k.trang_thai]} nhan="Cần làm" gia={VIEC_TT[k.trang_thai] ?? d.nhan[k.trang_thai]} /></> }))} />}
    </Khoi>
  );
}
```
Xoá `useMemo` khỏi import React nếu không còn chỗ dùng.

- [ ] **Step 7: Test + build**

Run: `cd giao_dien && npm test && npm run build && cd .. && pytest tests/test_tong_quan.py tests/test_nguon_dung.py tests/test_api.py -q`
Expected: PASS (gồm test canh `/khach-hang?loc=${n}&tat_ca=1`).

- [ ] **Step 8: Commit**

```bash
git add giao_dien/src/tong_quan/khoi.tsx giao_dien/src/tong_quan/tong_quan.css kome/web/spa
git commit -m "feat(tong-quan): khoi khach it chu - viec, thang nay chua mua, khach moi, suc khoe, khach lon nhat

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Khối còn lại — Sale, Ngành, Sắp hết hạn, Tương quan, Tăng trưởng, Biên, Nạp, khối chưa có

**Files:**
- Create: `giao_dien/src/tong_quan/DaiHan.tsx`
- Modify: `giao_dien/src/tong_quan/khoi.tsx` — `KhoiSale`, `KhoiNganh`, `KhoiHanSuDung`, `KhoiTuongQuan`, `KhoiTangTruong`, `KhoiBien`, `KhoiNap`, `veKhoi`
- Modify: `giao_dien/src/tong_quan/tong_quan.css`

**Interfaces:**
- Consumes: `mienHan`, `xHan`, `banKinh` (Task 6); `buocCham` (Task 1); `ONoi`, `DongNoi`, `ThanhNgang`, `SoLon`.
- Produces: `DaiHan({ lo: Lo[] })`, với `Lo` export từ `khoi.tsx`? — KHÔNG: khai `Lo` trong `DaiHan.tsx` và `khoi.tsx` import `type Lo` từ đó (xoá khai báo `Lo` cũ trong `khoi.tsx`).

- [ ] **Step 1: `DaiHan.tsx`**

```tsx
// Dải thời gian lô sắp hết hạn (đặc tả 2026-09-28-tong-quan-it-chu-design.md §5): trục ngang =
// số ngày còn tới hạn (vùng quá hạn · 0–30 · 30–60 · 60+), mỗi lô một chấm, cỡ ∝ √giá trị tồn.
// Chấm là HTML (ONoi) chứ không phải SVG — ô nổi / liên kết / bàn phím dùng chung một linh kiện.
import { DongNoi, ONoi } from "../chung/ONoi";
import { ngay, so, yen } from "../dinh_dang";
import { banKinh, mienHan, xHan } from "./han_logic";

export type Lo = { ma: string; ten: string; kho: string; ten_kho: string | null; han: string; con_lai: number; so_luong: number; gia_tri: number };

const xuLy = (c: number): [string, string] =>
  c < 0 ? ["Quá hạn — xử lý", "var(--do)"] : c < 30 ? ["Xả hàng ngay", "var(--do)"] : c < 60 ? ["Chào ưu tiên", "var(--lien-ket)"] : ["Theo dõi", "var(--chu-mo)"];

export function DaiHan({ lo }: { lo: Lo[] }) {
  const m = mienHan(lo.map(x => x.con_lai));
  const maxGT = Math.max(0, ...lo.map(x => x.gia_tri));
  const pc = (c: number) => `${xHan(c, m) * 100}%`;
  const vung = [[m.tu, 0, "dh-qua"], [0, 30, "dh-30"], [30, 60, "dh-60"], [60, m.den, "dh-xa"]] as const;
  return (
    <div className="dh">
      <div className="dh-ray">
        {vung.map(([a, b, lop]) => <div key={lop} className={"dh-vung " + lop} style={{ left: pc(a), width: `calc(${pc(b)} - ${pc(a)})` }} />)}
        {lo.map((x, i) => {
          const [chu, mau] = xuLy(x.con_lai), r = banKinh(x.gia_tri, maxGT);
          return (
            <ONoi key={`${x.ma}-${x.kho}-${x.han}`} href={`/san-pham/${x.ma}`} className="dh-cham" nhan={`${x.ten}: còn ${x.con_lai} ngày`}
              style={{ left: pc(x.con_lai), top: `${18 + (i % 4) * 18}%`, width: r * 2, height: r * 2, background: mau }}
              noi_dung={<><strong>{x.ten}</strong>
                <DongNoi nhan="Mã" gia={x.ma} /><DongNoi nhan="Lô" gia={x.ten_kho || x.kho} />
                <DongNoi nhan="Hạn dùng" gia={ngay(x.han)} /><DongNoi nhan="Còn lại" gia={`${x.con_lai} ngày`} />
                <DongNoi nhan="Tồn" gia={so(x.so_luong)} /><DongNoi nhan="Giá trị tồn" gia={yen(x.gia_tri)} />
                <DongNoi mau={mau} nhan="Xử lý" gia={chu} /></>}><span /></ONoi>);
        })}
      </div>
      <div className="dh-truc">
        {[0, 30, 60, 90].filter(c => c >= m.tu && c <= m.den).map(c => <span key={c} style={{ left: pc(c) }}>{c === 0 ? "hạn" : `${c} ngày`}</span>)}
      </div>
    </div>
  );
}
```
CSS thêm vào `tong_quan.css`:
```css
.dh-ray{position:relative;height:110px;border-radius:8px;overflow:hidden;background:var(--nen-phu)}
.dh-vung{position:absolute;top:0;bottom:0}
.dh-qua{background:color-mix(in srgb, var(--do) 16%, transparent)}
.dh-30{background:color-mix(in srgb, var(--do) 8%, transparent)}
.dh-60{background:color-mix(in srgb, var(--lien-ket) 8%, transparent)}
.dh-cham{position:absolute;transform:translate(-50%,0);border-radius:50%;opacity:.8;border:1px solid var(--nen-the)}
.dh-cham:hover,.dh-cham:focus-visible{opacity:1}
.dh-truc{position:relative;height:1.1rem;font-size:.66rem;color:var(--chu-mo)}
.dh-truc span{position:absolute;transform:translateX(-50%);white-space:nowrap}
```

- [ ] **Step 2: `KhoiHanSuDung`** — thay nguyên hàm (và xoá `type Lo` cũ, thêm `import { DaiHan, type Lo } from "./DaiHan";`):

```tsx
export function KhoiHanSuDung() {
  const { data: d, isLoading, error } = useKhoi<{ can_han_ngay: number; lo: Lo[] }>("han_su_dung");
  const lo = d?.lo ?? [];
  const duoi30 = new Set(lo.filter(x => x.con_lai < 30).map(x => x.ma)).size;
  return (
    <Khoi tieu_de="Sắp hết hạn" nhan={lo.length ? `${duoi30} mã dưới 30 ngày` : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/kho-hang" }}
      cach_tinh={lo.length ? `Trục ngang = số ngày còn tới hạn; mỗi chấm một lô, cỡ chấm theo giá trị tồn. Tổng giá trị tồn rủi ro ${yen(lo.reduce((s, x) => s + x.gia_tri, 0))}.` : undefined}>
      {d && (lo.length ? <DaiHan lo={lo} /> : <div className="trong">Không lô nào hết hạn trong {d.can_han_ngay} ngày tới.</div>)}
    </Khoi>
  );
}
```

- [ ] **Step 3: `KhoiSale`** — thay phần `return (…)`:

```tsx
  return (
    <Khoi tieu_de="Theo sale" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}
      phu={ssN?.co ? <>so {ssN.nhan}</> : undefined}
      cach_tinh={d ? `${d.co_ngan_sach ? `% = tiến độ so ngân sách cá nhân tháng ${thang_nhan(d.thang).slice(1)}` : `Doanh thu tháng ${thang_nhan(d.thang).slice(1)} — chưa đặt chỉ tiêu nên chưa có %`}.${ssN?.co ? ` Vạch đứt = ${ssN.nhan}.` : ""}` : undefined}
      canh_bao={ssN && !ssN.co ? `${hoa(ssN.nhan)}: không có dữ liệu để so.` : undefined}>
      {d && <ThanhNgang thang={1} nhan_ss={ssN?.co ? hoa(ssN.nhan) : undefined} dong={nguoi.map((n): DongThanh => ({
        khoa: n.ma, ten: tenNguoi(n.ten, n.ma),
        gia_tri: n.muc_tieu ? (n.tien_do ?? 0) : n.thuc_te / max,
        ss: ssN?.co && n.dt_ss != null ? (n.muc_tieu ? n.dt_ss / n.muc_tieu : n.dt_ss / max) : null,
        chu: n.muc_tieu ? pc(n.tien_do) : gon(n.thuc_te),
        phu: ssN ? <TdSs nay={n.thuc_te} ss={n.dt_ss} nhan={ssN.nhan} /> : undefined,
        mau: n.muc_tieu ? mauTienDo(n.tien_do, d.moc) : LUC.canh,
        chi_tiet: <><DongNoi nhan="Doanh thu" gia={yen(n.thuc_te)} />
          <DongNoi nhan="Chỉ tiêu" gia={n.muc_tieu ? yen(n.muc_tieu) : "chưa có"} />
          {ssN?.co && <DongNoi nhan={hoa(ssN.nhan)} gia={yen(n.dt_ss)} />}</> }))} />}
    </Khoi>
  );
```
(Thang 1 vì `gia_tri` đã chuẩn hoá: tiến độ khi có chỉ tiêu, doanh thu ÷ max khi chưa — đúng như bản cũ.)

- [ ] **Step 4: `KhoiNganh`** — thay phần `return (…)` (xoá biến `max` cũ):

```tsx
  return (
    <Khoi tieu_de="Ngành hàng" phu={d?.thang ? <>{d.thang}{ss?.co ? <> · so {ss.nhan}</> : null}</> : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}
      cach_tinh="Thanh = tỷ trọng doanh thu của ngành; số bên phải = tăng / giảm so kỳ so. Biên gộp = tổng lãi gộp ÷ tổng doanh thu thuần."
      canh_bao={ss && !ss.co ? `${hoa(ss.nhan)}: không có dữ liệu để so.` : undefined}>
      {d && <ThanhNgang dong={d.nganh.map((n): DongThanh => ({
        khoa: n.nganh, ten: n.nganh, gia_tri: n.ty_trong ?? 0, chu: pc(n.ty_trong),
        phu: <span className={(n.tang_truong ?? 0) >= 0 ? "tang" : "giam"}>{n.tang_truong != null ? thay_doi(n.tang_truong) : n.co_cung_ky ? "—" : "chưa có"}</span>,
        mau: "var(--lien-ket)",
        chi_tiet: <><DongNoi nhan="Doanh thu" gia={yen(n.doanh_thu)} /><DongNoi nhan="Lãi gộp" gia={yen(n.lai_gop)} />
          <DongNoi nhan="Biên gộp" gia={pc(n.ty_suat)} />
          <DongNoi nhan={<>so {ss?.nhan ?? "kỳ so"}</>} gia={n.tang_truong != null ? thay_doi(n.tang_truong) : "—"} /></> }))} />}
    </Khoi>
  );
```

- [ ] **Step 5: `KhoiTuongQuan`** — import `useRef` (React) và `buocCham` (`"../chung/o_noi_logic"`). Đầu hàm, sau `const [tro, datTro] = …`, thêm:
```tsx
  const nm = useNhanMoc();
  const kieu = useRef("mouse");
```
Thẻ `Khoi` mở đầu đổi thành:
```tsx
    <Khoi tieu_de="Doanh thu × tần suất" phu={d?.khoang?.nhan} dang_tai={isLoading} loi={error?.message}
      cach_tinh={`Mỗi chấm một khách; màu = trạng thái ${nm}; hai trục thang log. Rê / chạm để xem, bấm (chạm lần nữa) để mở hồ sơ.`}>
```
Thẻ `<circle>` đổi thành:
```tsx
          {k.map(x => <circle key={x.ma} cx={px(x)} cy={py(x)} r={tro?.ma === x.ma ? 6 : 4} fill={MAU_TT[x.trang_thai] ?? LUC.nhat}
            opacity={tro && tro.ma !== x.ma ? 0.35 : 0.72} style={{ cursor: "pointer" }}
            onPointerDown={e => { kieu.current = e.pointerType; }}
            onPointerEnter={e => { if (e.pointerType === "mouse") datTro(x); }} onPointerLeave={e => { if (e.pointerType === "mouse") datTro(null); }}
            onClick={() => {
              const b = buocCham(tro?.ma === x.ma, kieu.current);
              kieu.current = "mouse";
              if (b === "mo") { datTro(x); return; }
              location.href = giuKhoang(`/khach-hang/${x.ma}`);
            }} />)}
```
(`onPointerEnter` bỏ qua chạm: nếu không, `pointerenter` của chạm đặt `tro = x` TRƯỚC `click` và lần chạm đầu đã đi luôn.) Bỏ `<em>bấm để mở hồ sơ</em>` khỏi ô nổi và chú giải "khoẻ / cần theo dõi / đang rời bỏ" GIỮ (là chú giải màu, không phải câu).

- [ ] **Step 6: `KhoiTangTruong`** — thay phần `return (…)`:

```tsx
  return (
    <Khoi tieu_de="Khách đang mua" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}
      cach_tinh="Số khách có đơn theo từng kỳ kế toán (1/8 → 31/7)."
      canh_bao={cuoi && cuoi.so_thang < 12 ? `${cuoi.nhan} mới có ${cuoi.so_thang} tháng — số khách thấp hơn, đừng so thẳng với kỳ đủ.` : undefined}>
      {d && <>
        {cuoi && <SoLon gia={so(cuoi.so_khach)} nhan={`khách có đơn · ${cuoi.nhan}`} />}
        <BieuDo nhan={ky.map(x => x.nhan.replace(/^Kỳ\s*/, "K"))} nhan_day_du={ky.map(x => `${x.nhan} · ${x.so_thang} tháng dữ liệu`)} cao={150}
          mo_ta="Số khách có đơn theo từng kỳ kế toán"
          chuoi={[{ ten: "Khách có đơn", kieu: "cot", gia_tri: ky.map(x => x.so_khach), mau: "var(--lien-ket)",
            mau_tung_cot: ky.map(x => x.company_fy === d.chon ? "var(--lien-ket)" : MO) }]}
          dinh_dang={v => `${so(v)} khách`} dinh_dang_truc={v => so(v)} />
      </>}
    </Khoi>
  );
```

- [ ] **Step 7: `KhoiBien`** — đổi `Khoi` mở đầu và xoá khối `<div className="phu">…</div>` cuối:

```tsx
    <Khoi tieu_de="Biên theo quý" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}
      phu={ss && coSs ? <>so {ss.nhan}</> : undefined}
      cach_tinh="Biên gộp = tổng lãi gộp ÷ tổng doanh thu thuần. Biên RÒNG của gói thiết kế chưa có — cần chi phí vận hành, chưa có nguồn."
      canh_bao={ss && !coSs ? (d?.so_quy == null ? `${hoa(ss.nhan)} không lệch tròn quý — không so theo quý được.` : `${hoa(ss.nhan)}: không có dữ liệu để so.`) : undefined}>
```

- [ ] **Step 8: `KhoiNap`** — thay phần thân (bỏ `<table>`):

```tsx
      {d && <div className="hai-cot-tt">
        <div><div className="tieu-muc">LẦN NẠP GẦN NHẤT</div>
          <div className="nap-ds">{d.lo.map((x, i) => (
            <ONoi key={i} className="nap-dong" noi_dung={<><strong>{x.loai}</strong><DongNoi nhan="File" gia={x.ten_file} />
              <DongNoi nhan="Ngày dữ liệu" gia={ngay(x.ngay_du_lieu)} /></>}>
              <span>{x.loai}</span><b>{so(x.so_dong)} dòng</b><span className="nhat-chu">{gio_tokyo(x.nap_luc)}</span></ONoi>))}</div></div>
        <div><div className="tieu-muc">PHIẾU BÁN MỚI NHẤT</div>
          <div className="nap-ds">{d.phieu.map(x => (
            <a key={x.so} className="nap-dong" href={`/khach-hang/${x.ma}`}>
              <span className="ten-jp">{x.ten}</span><b>{yen(x.tien)}</b><span className="nhat-chu">{ngay_ngan(x.ngay)}</span></a>))}</div></div>
      </div>}
```
Cả hai danh sách cùng dạng "chữ · số · phụ". CSS thêm vào `tong_quan.css`:
```css
.nap-ds{display:grid;gap:.15rem}
.nap-dong{display:grid;grid-template-columns:1fr auto auto;gap:.6rem;align-items:baseline;font-size:.76rem;padding:.15rem .2rem;
  border-radius:6px;color:inherit;text-decoration:none}
.nap-dong > :first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nap-dong b{font-variant-numeric:tabular-nums;font-weight:500}
a.nap-dong:hover{background:var(--nen-phu)}
```

- [ ] **Step 9: `veKhoi`** — khối chưa có dữ liệu dùng bản gọn:

```tsx
  return <ChuaCoDuLieu gon tieu_de={nhan} ly_do={KD.chua_co[id] ?? "Chưa có nguồn dữ liệu cho khối này."} />;
```
Và trong `KhoiSale` dòng `ChuaCoDuLieu` cũng thêm `gon`.

- [ ] **Step 10: Test + build**

Run: `cd giao_dien && npm test && npm run build && cd .. && pytest tests/test_tong_quan.py tests/test_nguon_dung.py tests/test_api.py -q`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add giao_dien/src/tong_quan kome/web/spa
git commit -m "feat(tong-quan): khoi con lai it chu - sale, nganh, dai han dung, bien, nap, khoi chua co

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Test canh luật chữ, chiều cao mặc định, CLAUDE.md

**Files:**
- Create: `tests/test_tong_quan_it_chu.py`
- Modify: `kome/web/bo_cuc.py` (`_KHOI_DAY_DU`)
- Modify: `CLAUDE.md`

- [ ] **Step 1: Viết test**

`tests/test_tong_quan_it_chu.py`:
```python
"""Luật chữ của Tổng quan (đặc tả 2026-09-28-tong-quan-it-chu-design.md §4):
không bảng, không dòng `phu` tự do, câu cách tính của máy chủ đi qua ⓘ (`cach_tinh=`)."""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
KHOI = (GOC / "giao_dien/src/tong_quan/khoi.tsx").read_text(encoding="utf-8")


def test_tong_quan_khong_con_bang():
    assert "<table" not in KHOI


def test_tong_quan_khong_con_dong_phu_tu_do():
    # `className="phu"`, `className="phu nhat-chu"`, `className={"phu …` — KHÔNG khớp `khoi-phu`, `tng-phu`.
    assert re.findall(r'className=\{?["`]phu(?![-\w])', KHOI) == []
    assert 'className="phu"' not in KHOI


def test_cach_tinh_may_chu_di_qua_i_khong_in_tran():
    assert re.findall(r">\s*\{d\??\.cach_tinh\}", KHOI) == []
    assert "cach_tinh={d?.cach_tinh}" in KHOI


def test_net_dut_chi_cho_ky_so_thang_nay_chua_mua_khong_ve_vach():
    """Khối Tháng này chưa mua so với THÁNG TRƯỚC — không phải kỳ so, nên không truyền `ss`
    / `nhan_ss` cho ThanhNgang (vạch đứt dành riêng cho kỳ so)."""
    than = KHOI.split("export function KhoiThangNay")[1].split("export function")[0]
    assert "nhan_ss" not in than and "ss:" not in than
```

- [ ] **Step 2: Chạy**

Run: `pytest tests/test_tong_quan_it_chu.py -v`
Expected: PASS (Task 5–8 đã làm xong). Nếu FAIL: sửa `khoi.tsx` chỗ test chỉ ra, build lại.

- [ ] **Step 3: Chiều cao mặc định** — trong `kome/web/bo_cuc.py::_KHOI_DAY_DU` đổi cột `cao`: `theo_thang` 3→2, `viec_hom_nay` 3→2, `thang_nay_chua_mua` 3→2, `khach_moi` 3→2, và `dong_tien`, `mua_hang`, `khieu_nai`, `hang_sap_ve`, `thoi_tiet`, `nhip_mua` (khối chưa có nguồn) → 1. Thêm chú thích ngay trên `_KHOI_DAY_DU`:
```python
# Chiều cao LỆCH CÓ CHỦ Ý khỏi BO_CUC_MAC_DINH của gói thiết kế từ 2026-09-28 (đặc tả
# 2026-09-28-tong-quan-it-chu-design.md §5): khối từng chứa bảng thấp còn 2, khối chưa có
# nguồn còn 1. Bố cục đã lưu (app.bang_tong_quan) không tự đổi.
```
Kiểm `nhip_mua` và `hang_sap_ve` đúng là khối chưa có nguồn: `python -c "from kome.khoi_tong_quan import CHUA_CO; print(sorted(CHUA_CO))"` — chỉ hạ về 1 những mã có trong danh sách in ra.

- [ ] **Step 4: CLAUDE.md** — thêm bất biến sau đoạn "**Bất biến (056, …)**":
```markdown
**Bất biến (Tổng quan ít chữ — chủ DN chốt 2026-09-28):** màn `/` là HÌNH + tối đa một số lớn mỗi
khối; mọi chi tiết trong ô nổi `chung/ONoi.tsx` (chuột: rê hiện / bấm đi; chạm: lần 1 hiện, lần 2 đi;
bàn phím: Tab hiện / Enter đi). Không bảng nào. Luật chữ: câu ĐỊNH NGHĨA cách tính vào `Khoi.cach_tinh`
(ⓘ) — vẫn là `cach_tinh` của máy chủ truyền thẳng, không chép câu; câu NGOẠI LỆ đang xảy ra (tháng
chưa đủ ngày, kỳ so không so được, kỳ thiếu tháng…) vào `Khoi.canh_bao`, LUÔN hiện; nhãn kỳ so LUÔN
hiện. Vạch đứt của `ThanhNgang` (`ss`) chỉ dành cho kỳ so. Có test canh: `tests/test_tong_quan_it_chu.py`.
Đặc tả: `docs/superpowers/specs/2026-09-28-tong-quan-it-chu-design.md`.
```
Sửa ba câu "in dưới khối" cho Tổng quan:
- đoạn 036: "mỗi khối in `khach_thang.CACH_TINH`" → "mỗi khối in `khach_thang.CACH_TINH` (ở Tổng quan: trong ⓘ của khối)";
- đoạn 044 khách mới: "khối in `CACH_TINH_KHACH_MOI`" → "khối in `CACH_TINH_KHACH_MOI` (ở Tổng quan: trong ⓘ)";
- đoạn Đợt 6 công nợ: sau "Màn phải in câu đó (`kome.cong_no.CACH_TINH["fifo"]`)" thêm "(khối Tuổi nợ của Tổng quan: trong ⓘ)".

- [ ] **Step 5: Chạy lại toàn bộ**

Run: `cd giao_dien && npm test && npm run build && cd .. && pytest -q`
Expected: toàn bộ PASS. Test nào ghim chiều cao mặc định (tìm bằng `grep -rn '"cao"' tests/test_bo_cuc.py tests/test_bang_tong_quan.py`) mà đỏ vì Step 3 thì sửa số mong đợi — không đổi ý test. `tests/test_tai_lieu.py::test_anh_chup_tai_lieu_khong_cu` chỉ đỏ nếu đã sửa mục "Bẫy đã biết" (không sửa) — nếu đỏ, chạy `python scripts/sinh_tai_lieu.py`.

- [ ] **Step 6: Commit**

```bash
git add tests/test_tong_quan_it_chu.py kome/web/bo_cuc.py CLAUDE.md kome/web/spa
git commit -m "test(tong-quan): canh luat chu it chu; ha chieu cao mac dinh; bat bien CLAUDE.md

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Kiểm bằng mắt — ba cỡ màn hình, sáng + tối

**Files:** không đổi mã trừ khi thấy lỗi (khi đó sửa, build, commit riêng `fix(tong-quan): …`).

- [ ] **Step 1: Mở bản xem thử** — `preview_start` tên `ky-so-xem` (cổng 8071; nếu không chạy được thì chạy `uvicorn kome.web.app:app --port 8000` qua một cấu hình mới trong `.claude/launch.json` trỏ CSDL thật CHỈ ĐỌC hoặc CSDL test có dữ liệu).
- [ ] **Step 2: 1440×900 sáng** — `resize_window {width:1440,height:900,colorScheme:"light"}`, chờ tải xong ("Đang tải dữ liệu" biến mất), chụp màn. Rê chuột vào: một ô Chỉ số, một khúc Sức khoẻ khách, một dòng Khách lớn nhất, một chấm Sắp hết hạn, ⓘ của Tháng này chưa mua → mỗi lần có ô nổi đúng số. `read_console_messages {onlyErrors:true}` rỗng.
- [ ] **Step 3: 1440×900 tối** — `colorScheme:"dark"`, chụp màn; ô nổi, thanh, vùng dải hạn đọc được.
- [ ] **Step 4: 768 và 375 (mobile, chạm)** — `resize_window {preset:"tablet"}` rồi `{preset:"mobile"}`, tải lại trang. Ở 375: không cuộn ngang (`javascript_tool: document.documentElement.scrollWidth <= innerWidth`), bấm (chạm) một dòng Khách lớn nhất → ô nổi hiện, URL CHƯA đổi; bấm lần nữa → sang `/khach-hang/{mã}`.
- [ ] **Step 5: Đặt lại** — `resize_window {preset:"desktop"}`; gửi ảnh chụp trước/sau cho chủ DN (`SendUserFile`).
