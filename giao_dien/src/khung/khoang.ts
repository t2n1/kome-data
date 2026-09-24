// Khoảng xem chung cả website (đặc tả 2026-09-24-khoang-xem-thang-design.md §4).
//
// Trạng thái nằm TRÊN URL (`?thang=` · `?ky=` · `?tu=&den=`; không tham số =
// tháng hiện tại) — không cookie, không localStorage: gửi link là người nhận
// thấy đúng khoảng đó, đóng trình duyệt mở lại là về tháng hiện tại.
// Máy chủ (kome/khoang_xem.py) là chỗ DUY NHẤT hiểu khoảng: file này chỉ đọc /
// ghi tham số và giữ chúng khi đổi màn — KHÔNG tự tính ngày so sánh.
import { useSyncExternalStore } from "react";
import { useQuery } from "@tanstack/react-query";
import { lay } from "../api";

export const THAM_SO = ["thang", "ky", "tu", "den"] as const;
export type Khoang = Partial<Record<(typeof THAM_SO)[number], string>>;

/** Object `khoang` máy chủ trả kèm mọi dữ liệu doanh số (kome/khoang_xem.py::KhoangXem). */
export type KhoangMayChu = {
  loai: "thang" | "ky" | "khoang"; tu: string; den: string; nhan: string; mo_ta: string;
  thang: string | null; company_fy: number | null; so_ky: number | null; mac_dinh: boolean;
  tron_thang: boolean; ghi_chu: string[]; ngay_dau: string; hom_nay: string; so_ngay: number; dang_lui: boolean;
  so_sanh: { ma: string; nhan: string; tu: string; den: string; tu_nay: string; den_nay: string; co: boolean }[];
};
export type PhamVi = { ngay_dau: string; hom_nay: string; ky: { company_fy: number; so_ky: number; tu: string; den: string }[] };

export function docKhoang(search: string = location.search): Khoang {
  const q = new URLSearchParams(search);
  const k: Khoang = {};
  for (const t of THAM_SO) { const v = q.get(t); if (v) k[t] = v; }
  // `thang` chỉ là khoảng xem khi đúng dạng YYYY-MM (phòng một bộ lọc cũ trùng tên).
  if (k.thang && !/^\d{4}-\d{2}$/.test(k.thang)) delete k.thang;
  return k;
}

/** Chuỗi tham số đã sắp — cùng khoảng thì cùng chuỗi (khoá TanStack Query). */
export function chuoiKhoang(k: Khoang): string {
  const q = new URLSearchParams();
  for (const t of THAM_SO) if (k[t]) q.set(t, k[t]!);
  return q.toString();
}

let hienTai = chuoiKhoang(docKhoang());
const nghe = new Set<() => void>();
const bao = () => nghe.forEach(f => f());

if (typeof window !== "undefined") {
  window.addEventListener("popstate", () => {
    const moi = chuoiKhoang(docKhoang());
    if (moi !== hienTai) { hienTai = moi; bao(); }
  });
}

/** Tham số khoảng đang xem (chuỗi query, có thể rỗng) — gắn vào lời gọi API doanh số. */
export function thamSoKhoang(): string { return hienTai; }

/** Nối tham số khoảng vào một URL API: `/api/bao-cao` + `?thang=…`. */
export function voiKhoang(url: string): string {
  if (!hienTai) return url;
  return url + (url.includes("?") ? "&" : "?") + hienTai;
}

/** Đổi khoảng: sửa URL tại chỗ (không tải lại trang) rồi báo mọi thành phần. */
export function datKhoang(k: Khoang) {
  const u = new URL(location.href);
  for (const t of THAM_SO) u.searchParams.delete(t);
  for (const t of THAM_SO) if (k[t]) u.searchParams.set(t, k[t]!);
  history.replaceState(history.state, "", u.pathname + u.search + u.hash);
  hienTai = chuoiKhoang(k);
  bao();
}

export function useKhoang(): Khoang {
  const s = useSyncExternalStore(f => { nghe.add(f); return () => { nghe.delete(f); }; }, () => hienTai);
  return docKhoang(s);
}

// Đường dẫn KHÔNG mang khoảng xem: đổi giao diện (tự quay về qua Referer, đã
// giữ khoảng), đăng xuất, tài nguyên tĩnh, API, nạp / hoàn tác.
const KHONG_GIU = /^\/(giao-dien|dang-xuat|dang-nhap|static|api|upload|undo)(\/|\?|$)/;

/** Gắn khoảng đang xem vào một đường dẫn nội bộ — trừ khi nó đã tự mang
 *  tham số khoảng riêng, hoặc thuộc nhóm KHONG_GIU. Dùng cho MỌI
 *  history.pushState / replaceState của từng màn (bộ lọc riêng của màn không
 *  được làm rơi khoảng xem). */
export function giuKhoang(url: string): string {
  if (!hienTai || !url.startsWith("/") || url.startsWith("//") || KHONG_GIU.test(url)) return url;
  const [truocHash, hash = ""] = url.split("#");
  const [duong, q = ""] = truocHash.split("?");
  const p = new URLSearchParams(q);
  if (THAM_SO.some(t => p.has(t))) return url;
  for (const [a, b] of new URLSearchParams(hienTai)) p.set(a, b);
  return duong + "?" + p.toString() + (hash ? "#" + hash : "");
}

/** Gắn MỘT lần (main.tsx): ngay trước khi người dùng bấm / mở tab mới / chép
 *  một liên kết nội bộ, viết lại `href` của nó thành `giuKhoang(href gốc)`.
 *  Một chỗ thay vì sửa ~70 liên kết rải khắp các màn. Giữ `href` gốc trong
 *  `data-href-goc` để đổi khoảng lần sau không cộng dồn tham số cũ. */
export function ganVietLaiLienKet() {
  const viet = (e: Event) => {
    const a = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
    if (!a) return;
    const hien = a.getAttribute("href") ?? "";
    // React đổi href từ lúc ta viết lại -> đó là href gốc mới.
    const goc = a.dataset.hrefViet === hien ? (a.dataset.hrefGoc ?? hien) : hien;
    const moi = giuKhoang(goc);
    a.dataset.hrefGoc = goc;
    a.dataset.hrefViet = moi;
    if (moi !== hien) a.setAttribute("href", moi);
  };
  for (const ten of ["pointerdown", "focusin", "contextmenu"]) document.addEventListener(ten, viet, true);
}

export function usePhamVi() {
  return useQuery<PhamVi | null>({ queryKey: ["pham-vi"], queryFn: () => lay<PhamVi | null>("/api/pham-vi") });
}

// Mô tả khoảng của máy chủ: API doanh số nào trả về cũng báo vào đây (api.ts),
// bộ chọn in đúng câu đó. Chỉ nhận khi nó thuộc khoảng đang xem.
let moTa: { khoa: string; k: KhoangMayChu } | null = null;
const ngheMoTa = new Set<() => void>();
export function baoKhoangMayChu(k: KhoangMayChu | null | undefined, khoa: string) {
  if (!k || !k.mo_ta || (moTa && moTa.khoa === khoa && moTa.k.mo_ta === k.mo_ta)) return;
  moTa = { khoa, k };
  ngheMoTa.forEach(f => f());
}
export function useKhoangMayChu(): KhoangMayChu | null {
  const k = useSyncExternalStore(f => { ngheMoTa.add(f); return () => { ngheMoTa.delete(f); }; }, () => moTa);
  const s = useSyncExternalStore(f => { nghe.add(f); return () => { nghe.delete(f); }; }, () => hienTai);
  return k && k.khoa === s ? k.k : null;
}

/** Nhãn cho các số "tính đến hôm nay": "hôm nay", hoặc "đến 31/3/2026" khi khoảng
 *  đang xem LÙI mốc thời gian (migration 040 — `KhoangMayChu.dang_lui`). */
export function useNhanMoc(): string {
  const k = useKhoangMayChu();
  if (!k?.dang_lui) return "hôm nay";
  const [y, m, d] = k.hom_nay.slice(0, 10).split("-");
  return `đến ${+d}/${+m}/${y}`;
}
