// Lọc / đếm bảng giá KOME ở trình duyệt (một ảnh chụp /api/bang-gia). Hàm thuần.
// Cờ từng ô (đổi / dưới giá vốn / hai cột lệch) là của máy chủ (mart.bang_gia_kome, 071) — ở đây chỉ gộp "có ô nào"
// theo MÃ. Luật bộ đếm (cùng nếp san_pham/loc.ts): mỗi dải đếm theo mọi bộ lọc TRỪ của chính nó.
import { khopTim } from "../san_pham/loc";
import type { MaGia } from "./kieu";

export const CO = [
  { k: "doi", nhan: "Đã đổi giá", giai: "Có ô giá khác lần nạp trước, bậc mới hoặc bậc bị bỏ" },
  { k: "duoi", nhan: "Dưới giá vốn", giai: "Có bậc giá chưa thuế thấp hơn 単位原価 của chính quy cách đó" },
  { k: "lech", nhan: "Hai cột thuế mâu thuẫn", giai: "Giá gồm thuế nhỏ hơn giá chưa thuế — web lấy gồm thuế ÷ 1,08" },
  { k: "thieu_kg", nhan: "Thiếu kg", giai: "Có giá nhưng không biết kg mỗi gói / thùng — không so được với đối thủ" },
  { k: "chua_co", nhan: "Chưa có giá", giai: "Không có bậc giá nào trong lần nạp 取引単価データ mới nhất" },
] as const;
export type Co = typeof CO[number]["k"];

export function coCua(m: MaGia): Set<Co> {
  const o = m.dong.flatMap(d => Object.values(d.g));
  const s = new Set<Co>();
  if (o.some(x => x.doi)) s.add("doi");
  if (o.some(x => x.duoi)) s.add("duoi");
  if (o.some(x => x.lech && !x.bo)) s.add("lech");
  if (m.thieu_kg) s.add("thieu_kg");
  if (!o.some(x => !x.bo)) s.add("chua_co");
  return s;
}

export type LocBg = { tim: string; nganh: string; co: string };

export function docLocBg(search: string): LocBg {
  const q = new URLSearchParams(search);
  return { tim: q.get("tim") ?? "", nganh: q.get("nganh") ?? "", co: q.get("co") ?? "" };
}

export function chuoiLocBg(b: LocBg): string {
  const q = new URLSearchParams();
  if (b.tim.trim()) q.set("tim", b.tim.trim());
  if (b.nganh) q.set("nganh", b.nganh);
  if (b.co) q.set("co", b.co);
  return q.toString();
}

const laCo = (k: string): k is Co => CO.some(c => c.k === k);

/** `co` lạ = không lọc (cùng nếp khopLoc của san_pham/loc.ts). */
export function locBangGia(ds: MaGia[], b: LocBg) {
  const co = laCo(b.co) ? b.co : "";
  const theoTim = ds.filter(m => khopTim(m, b.tim)).map(m => ({ m, c: coCua(m) }));
  const hopNganh = (x: { m: MaGia }) => !b.nganh || x.m.nganh === b.nganh;
  const hopCo = (x: { c: Set<Co> }) => !co || x.c.has(co);
  const dem_co = Object.fromEntries(CO.map(c => [c.k, 0])) as Record<Co, number>;
  for (const x of theoTim) if (hopNganh(x)) for (const k of x.c) dem_co[k]++;
  const dem_nganh = new Map<string, number>();
  for (const x of theoTim) if (hopCo(x)) dem_nganh.set(x.m.nganh, (dem_nganh.get(x.m.nganh) ?? 0) + 1);
  return {
    hang: theoTim.filter(x => hopNganh(x) && hopCo(x)).map(x => x.m), co, dem_co,
    dem_nganh: [...dem_nganh.entries()].sort((a, c) => c[1] - a[1]),
    tong_co: theoTim.filter(hopNganh).length,       // chip "Tất cả" của dải cờ
    tong_nganh: theoTim.filter(hopCo).length,       // chip "Mọi ngành"
  };
}

/** Chữ ô nổi của một ô giá — "¥cũ → ¥mới (ngày → ngày)", bậc mới, bậc bị bỏ. */
export function giaiO(o: { gia: number | null; truoc: number | null; doi: boolean; bo: boolean }, tu: string, tu_truoc: string | null,
                      yen: (n: number) => string, ngay: (s: string) => string): string {
  if (o.bo) return `Bậc này có ở lần nạp ${tu_truoc ? ngay(tu_truoc) : "trước"} (${yen(o.truoc ?? 0)}) mà lần nạp ${ngay(tu)} không còn`;
  if (!o.doi || !tu_truoc) return "";
  if (o.truoc == null) return `Bậc mới ở lần nạp ${ngay(tu)} (lần ${ngay(tu_truoc)} chưa có)`;
  return `${yen(o.truoc)} → ${yen(o.gia ?? 0)} (${ngay(tu_truoc)} → ${ngay(tu)})`;
}
