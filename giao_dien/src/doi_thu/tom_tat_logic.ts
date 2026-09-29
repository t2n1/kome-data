// Logic thuần của tab "Tóm tắt" (đợt 4b task 7; bản phác ca-trang-8.html) — không React, có test (tom_tat_logic.test.ts).
// Dữ liệu: /api/doi-thu/so-sanh (Nhom[]) + /api/doi-thu/tong-quan (TongQuan). "Vị trí KOME" = lech_trung_vi của mart
// (giá KOME để so ÷ trung vị − 1); gia_kome_lech (> 3× / < ⅓ trung vị) KHÔNG vẽ, chỉ đếm để trỏ sang Dữ liệu › Giá KOME lệch.
import type { Ben, Nhom, TongQuan } from "./kieu";
import { boDau } from "./loc";
import { LECH_NGANG, mauKomeSoTT, type MauLech } from "./mau";
import { tenNganh } from "./nganh";

const NGUONG = LECH_NGANG / 100;   // ±5% — cùng ngưỡng xám của mau.ts

/** Nhóm đặt được lên trục "KOME đứng đâu": so theo kg, có giá KOME, không lệch bất thường, có lech_trung_vi. */
const coViTri = (n: Nhom): n is Nhom & { lech_trung_vi: number } =>
  n.don_vi_so === "kg" && n.gia_kome_so != null && !n.gia_kome_lech && n.lech_trung_vi != null;

export function tongSo(ss: Nhom[], tq: TongQuan): { coGia: number; datHon: number; maHet: number; km: number; soBenKm: number } {
  const co = ss.filter(n => n.don_vi_so === "kg" && n.gia_kome_so != null && !n.gia_kome_lech);
  return {
    coGia: co.length,
    datHon: co.filter(n => (n.lech_trung_vi ?? 0) > NGUONG).length,
    maHet: new Set(tq.het_hang.filter(h => h.trang_thai === "het").map(h => h.ma_kome)).size,
    km: tq.khuyen_mai.length,
    soBenKm: new Set(tq.khuyen_mai.map(k => k.ben)).size,
  };
}

/** Thanh tỉ lệ dưới biểu đồ: rẻ hơn / ngang (±5%) / đắt hơn trên nhóm có vị trí; `khongBan` = gia_kome_so null (mọi đơn vị);
 *  `lech` = số nhom_khoa KHÁC NHAU có gia_kome_lech (một nhóm nhiều đơn vị so vẫn là một); `tong` = mọi dòng nhóm. */
export function tiLe(ss: Nhom[]): { re: number; ngang: number; dat: number; khongBan: number; lech: number; tong: number } {
  const co = ss.filter(coViTri);
  return {
    re: co.filter(n => n.lech_trung_vi < -NGUONG).length,
    ngang: co.filter(n => Math.abs(n.lech_trung_vi) <= NGUONG).length,
    dat: co.filter(n => n.lech_trung_vi > NGUONG).length,
    khongBan: ss.filter(n => n.gia_kome_so == null).length,
    lech: new Set(ss.filter(n => n.gia_kome_lech).map(n => n.nhom_khoa)).size,
    tong: ss.length,
  };
}

/** Màu KOME so trung vị của một nhóm, tính từ lech_trung_vi CHƯA làm tròn — cùng ngưỡng > 5% / < −5% với datNhat / reNhat /
 *  tiLe, nên nhóm nằm trong "đắt nhất" (5,1%) không bao giờ xám dù % in ra làm tròn thành +5%. */
export const mauTT = (n: Pick<Nhom, "lech_trung_vi">): MauLech =>
  mauKomeSoTT(n.lech_trung_vi == null ? null : n.lech_trung_vi * 100);

export const P_THAP = -60, P_CAO = 70;
/** Số cột của beeswarm trên dải [P_THAP, P_CAO] (~9 px một cột ở khung 1 100 px) — ít hơn 130 nên % liền nhau có thể chung cột. */
export const SO_COT = 116;

/** Chấm của beeswarm: p = % KOME so trung vị (làm tròn, kẹp [−60, 70]); cột = round((p + 60) / 130 × SO_COT); tầng = thứ tự
 *  trong cột (0 = sát trục). Xếp lech_trung_vi tăng dần (ổn định). */
export function diemVitri(ss: Nhom[]): { nhom: Nhom; p: number; cot: number; tang: number }[] {
  const dem = new Map<number, number>();
  return ss.filter(coViTri).sort((a, b) => a.lech_trung_vi - b.lech_trung_vi).map(nhom => {
    const p = Math.max(P_THAP, Math.min(P_CAO, Math.round(nhom.lech_trung_vi * 100)));
    const cot = Math.round((p - P_THAP) / (P_CAO - P_THAP) * SO_COT);
    const tang = dem.get(cot) ?? 0;
    dem.set(cot, tang + 1);
    return { nhom, p, cot, tang };
  });
}

/** KOME đắt nhất so với thị trường: lệch > 5%, giảm dần. */
export const datNhat = (ss: Nhom[], n = 6): Nhom[] =>
  ss.filter(coViTri).filter(x => x.lech_trung_vi > NGUONG).sort((a, b) => b.lech_trung_vi - a.lech_trung_vi).slice(0, n);

/** KOME rẻ nhất so với thị trường: lệch < −5%, tăng dần. */
export const reNhat = (ss: Nhom[], n = 6): Nhom[] =>
  ss.filter(coViTri).filter(x => x.lech_trung_vi < -NGUONG).sort((a, b) => a.lech_trung_vi - b.lech_trung_vi).slice(0, n);

/** Cơ hội: mã KOME mà đối thủ đang HẾT (không tính 'sap_ve'), gộp theo ma_kome, MỘT chip mỗi bên (dòng đầu của bên đó
 *  là dòng mở pop-up sửa), xếp số bên giảm dần rồi tên. */
export function coHoi(tq: TongQuan, n = 8):
  { ma_kome: string; ten: string; ben: { ma: string; ten: string; nguon: string; id: number }[] }[] {
  const theoMa = new Map<string, { ma_kome: string; ten: string; ben: { ma: string; ten: string; nguon: string; id: number }[] }>();
  for (const h of tq.het_hang) {
    if (h.trang_thai !== "het") continue;
    const g = theoMa.get(h.ma_kome) ?? theoMa.set(h.ma_kome, { ma_kome: h.ma_kome, ten: h.ten_nhom ?? h.ma_kome, ben: [] }).get(h.ma_kome)!;
    if (g.ten === h.ma_kome && h.ten_nhom) g.ten = h.ten_nhom;
    if (!g.ben.some(b => b.ma === h.ma_doi_thu))
      g.ben.push({ ma: h.ma_doi_thu, ten: h.ten_doi_thu ?? h.ma_doi_thu, nguon: h.nguon, id: h.id });
  }
  return [...theoMa.values()].sort((a, b) => b.ben.length - a.ben.length || a.ten.localeCompare(b.ten, "vi")).slice(0, n);
}

/** Lưới "Ai bán ngành nào": gộp tq.luoi theo tenNganh (hai cách viết OBC của cùng ngành → một cột; ngành _THA đã mang
 *  "(Thái)"), chỉ bên đang theo dõi (tq.ben). Ngành và bên xếp theo tổng số mã giảm dần; bên không có ô nào vẫn có dòng.
 *  Khoá ô = `${ma_ben}|${ten ngành hiển thị}`. */
export function bongNganh(tq: TongQuan): { ben: Ben[]; nganh: string[]; o: Map<string, number> } {
  const biet = new Set(tq.ben.map(b => b.ma));
  const o = new Map<string, number>(), theoNganh = new Map<string, number>(), theoBen = new Map<string, number>();
  for (const x of tq.luoi) {
    if (!biet.has(x.ben)) continue;
    const g = tenNganh(x.nganh), k = `${x.ben}|${g}`;
    o.set(k, (o.get(k) ?? 0) + x.so_ma);
    theoNganh.set(g, (theoNganh.get(g) ?? 0) + x.so_ma);
    theoBen.set(x.ben, (theoBen.get(x.ben) ?? 0) + x.so_ma);
  }
  const nganh = [...theoNganh.keys()].sort((a, b) => theoNganh.get(b)! - theoNganh.get(a)! || a.localeCompare(b, "vi"));
  const ben = [...tq.ben].sort((a, b) => (theoBen.get(b.ma) ?? 0) - (theoBen.get(a.ma) ?? 0) || a.ten.localeCompare(b.ten, "vi"));
  return { ben, nganh, o };
}

/** Tên OBC gửi lên URL (?nganh=) cho một ngành HIỂN THỊ: cách viết có nhiều mã nhất (của `ben` nếu cho); không có → "". */
export function nganhObc(tq: TongQuan, ten: string, ben?: string): string {
  const dem = new Map<string, number>();
  for (const x of tq.luoi) if (tenNganh(x.nganh) === ten && (!ben || x.ben === ben)) dem.set(x.nganh, (dem.get(x.nganh) ?? 0) + x.so_ma);
  return [...dem.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? (ben ? nganhObc(tq, ten) : "");
}

/** Nhóm mở sẵn khi bấm một bóng: nhóm cùng ngành HIỂN THỊ có mặt hàng (không phải khách kể) của bên đó, không lệch;
 *  nhiều bên trước (cùng thứ tự "Tất cả" của cột trái tab So sánh). Trả nhom_khoa, không trùng, tối đa n. */
export function nhomCuaO(ss: Nhom[], nganh: string, ben: string, n = 3): string[] {
  const r = ss.filter(g => !g.gia_kome_lech && tenNganh(g.nganh) === nganh
    && g.quan_sat.some(q => q.ma_doi_thu === ben && q.loai_nguon !== "khach_ke"))
    .sort((a, b) => b.so_ben - a.so_ben);
  return [...new Set(r.map(g => g.nhom_khoa))].slice(0, n);
}

/** Số khuyến mãi theo bên (nhiều trước), tên từ tq.ben (không có → mã). */
export function kmTheoBen(tq: TongQuan, n = 8): { ma: string; ten: string; so: number }[] {
  const ten = new Map(tq.ben.map(b => [b.ma, b.ten]));
  const dem = new Map<string, number>();
  for (const k of tq.khuyen_mai) dem.set(k.ben, (dem.get(k.ben) ?? 0) + 1);
  return [...dem.entries()].map(([ma, so]) => ({ ma, ten: ten.get(ma) ?? ma, so }))
    .sort((a, b) => b.so - a.so || a.ten.localeCompare(b.ten, "vi")).slice(0, n);
}

/** Khuyến mãi có giảm giá rõ (gia_truoc_km > gia_goc), giảm nhiều nhất (theo %) trước. */
export const kmNoiBat = (tq: TongQuan, n = 4): TongQuan["khuyen_mai"] =>
  tq.khuyen_mai.filter(k => k.gia_goc != null && k.gia_truoc_km != null && k.gia_truoc_km > k.gia_goc)
    .map(k => ({ k, giam: 1 - k.gia_goc! / k.gia_truoc_km! })).sort((a, b) => b.giam - a.giam).slice(0, n).map(x => x.k);

export type GoiY = { loai: "ben" | "nhom"; khoa: string; ten: string; phu: string };

/** Gợi ý của ô tìm: bỏ dấu; bên (tên + mã, tối đa 3) trước, rồi nhóm (ten_nhom + mã KOME, một gợi ý mỗi nhom_khoa); tối đa n. */
export function goiY(ss: Nhom[], ben: Ben[], tim: string, n = 8): GoiY[] {
  const t = boDau(tim.trim());
  if (!t) return [];
  const b: GoiY[] = ben.filter(x => boDau(`${x.ten} ${x.ma}`).includes(t)).slice(0, 3)
    .map(x => ({ loai: "ben", khoa: x.ma, ten: x.ten, phu: x.ma }));
  const thay = new Set<string>(), g: GoiY[] = [];
  for (const x of ss) {
    if (thay.has(x.nhom_khoa) || !boDau(`${x.ten_nhom ?? ""} ${(x.ma_kome ?? []).join(" ")}`).includes(t)) continue;
    thay.add(x.nhom_khoa);
    g.push({ loai: "nhom", khoa: x.nhom_khoa, ten: x.ten_nhom ?? x.nhom_khoa, phu: (x.ma_kome ?? []).join(", ") });
  }
  return [...b, ...g].slice(0, n);
}
