// Logic thuần của tab "So sánh giá" (đợt 4b, đặc tả §5) — không React, có test (so_sanh_logic.test.ts).
// Giá đã là ¥/kg chưa thuế; gia_1/5/10 máy chủ đã lấy min(giá lẻ, bậc áp dụng). Khách kể KHÔNG vẽ ở đây.
import { boDau } from "./loc";
import { NGAY_CU, phanTram } from "./mau";
import type { Nhom, QuanSat } from "./kieu";

export type SoLuong = "1" | "5" | "10" | "pallet";
export const NHAN_SL: Record<SoLuong, string> = { "1": "1 thùng", "5": "5 thùng", "10": "10 thùng", pallet: "1 pallet" };

/** Giá (¥/kg) của một mặt hàng khi khách mua `sl`. Pallet không ghi → giá lẻ + khongGhiPallet = true (không đoán). */
export function giaTai(q: QuanSat, sl: SoLuong): { gia: number | null; khongGhiPallet: boolean } {
  const le = q.gia_1 ?? q.yen_chuan ?? null;
  if (sl === "1") return { gia: le, khongGhiPallet: false };
  if (sl === "5") return { gia: q.gia_5 ?? le, khongGhiPallet: false };
  if (sl === "10") return { gia: q.gia_10 ?? le, khongGhiPallet: false };
  return q.gia_pallet != null ? { gia: q.gia_pallet, khongGhiPallet: false } : { gia: le, khongGhiPallet: true };
}

/** Giá KOME để so: "chuan" → 標準価格 (thiếu thì giá thực bán); "thuc" → thực bán 90 ngày; "01".."10" → bảng 売価No (thiếu → null). */
export function giaKome(n: Nhom, gk: string): number | null {
  if (gk === "chuan") return n.gia_kome_chuan ?? n.gia_kome;
  if (gk === "thuc") return n.gia_kome;
  return n.gia_kome_bang?.[gk] ?? null;
}

export const LUA_CHON_GK: { ma: string; nhan: string }[] = [
  { ma: "chuan", nhan: "標準価格" }, { ma: "thuc", nhan: "thực bán 90 ngày" },
  { ma: "01", nhan: "売価No.01" }, { ma: "02", nhan: "売価No.02" }, { ma: "04", nhan: "売価No.04" },
  { ma: "05", nhan: "売価No.05" }, { ma: "09", nhan: "売価No.09" }, { ma: "10", nhan: "売価No.10 · khuyến mãi" },
];

export type Dong = { kome: boolean; q?: QuanSat; ben: string; ten: string; gia: number | null; giaLe: number | null;
  p: number | null; cung: boolean; soGoi: number | null; klGoi: number | null; thieu: boolean; cu: boolean;
  thueKhongRo: boolean; gomShip: boolean; het: boolean; km: boolean; khongGhiPallet: boolean };

export const thieuQuyCach = (q: QuanSat) => q.so_goi_thung == null || q.kl_goi_g == null;
const veDuoc = (q: QuanSat) => q.loai_nguon !== "khach_ke";
const tenBen = (q: QuanSat) => q.ten_doi_thu ?? q.ma_doi_thu;
/** So giá tăng dần, null xếp cuối (ổn định). */
const theoGia = (a: number | null, b: number | null) => (a == null ? (b == null ? 0 : 1) : b == null ? -1 : a - b);

function dongTu(q: QuanSat, sl: SoLuong, gK: number | null): Dong {
  const { gia, khongGhiPallet } = giaTai(q, sl);
  return { kome: false, q, ben: tenBen(q), ten: q.ten_goc, gia, giaLe: giaTai(q, "1").gia, p: phanTram(gia, gK),
    cung: q.nhan === "cung_hang", soGoi: q.so_goi_thung, klGoi: q.kl_goi_g, thieu: thieuQuyCach(q),
    cu: (q.tuoi_ngay ?? 0) > NGAY_CU, thueKhongRo: q.thue === "khong_ro", gomShip: q.gom_ship === "co",
    het: q.trang_thai === "het", km: !!q.khuyen_mai || q.gia_truoc_km != null, khongGhiPallet };
}

/** Dòng của biểu đồ cột một nhóm: KOME + mọi mặt hàng (bỏ khách kể; bất thường vẫn vẽ, cờ ở `q.bat_thuong`), lọc chiCung,
 *  xếp giá tăng (null cuối); chưa mở rộng thì giữ KOME + 5 hàng rẻ nhất + mọi cùng thương hiệu. `an` = số dòng bị ẩn. */
export function dongCot(n: Nhom, o: { sl: SoLuong; gk: string; chiCung: boolean; moRong: boolean }): { dong: Dong[]; an: number } {
  const gK = giaKome(n, o.gk);
  const kome: Dong = { kome: true, ben: "KOME", ten: "KOME", gia: gK, giaLe: gK, p: null, cung: false,
    soGoi: n.kome_goi_thung, klGoi: n.kome_kg_goi == null ? null : n.kome_kg_goi * 1000, thieu: false, cu: false,
    thueKhongRo: false, gomShip: false, het: false, km: false, khongGhiPallet: false };
  const hang = n.quan_sat.filter(q => veDuoc(q) && (!o.chiCung || q.nhan === "cung_hang"))
    .map(q => dongTu(q, o.sl, gK)).sort((a, b) => theoGia(a.gia, b.gia));
  const giu = o.moRong ? null : new Set([...hang.slice(0, 5), ...hang.filter(d => d.cung)]);
  const hien = giu ? hang.filter(d => giu.has(d)) : hang;
  return { dong: [kome, ...hien].sort((a, b) => theoGia(a.gia, b.gia)), an: hang.length - hien.length };
}

/** Ô bảng nhiệt: mỗi (nhóm, bên) — mặt hàng cùng thương hiệu rẻ nhất, không có thì khác thương hiệu rẻ nhất.
 *  `ben` = tên hiển thị (ten_doi_thu ?? ma_doi_thu), xếp theo số nhóm có mặt giảm dần; khoá ô `${nhom_khoa}|${ben}`. */
export function oNhiet(ds: Nhom[], o: { sl: SoLuong; gk: string; chiCung: boolean }):
  { ben: string[]; o: Map<string, { q: QuanSat; p: number | null; so: number; cung: boolean }> } {
  const ket = new Map<string, { q: QuanSat; p: number | null; so: number; cung: boolean }>();
  const soNhom = new Map<string, number>();
  for (const n of ds) {
    const gK = giaKome(n, o.gk);
    const theoBen = new Map<string, QuanSat[]>();
    for (const q of n.quan_sat) {
      if (!veDuoc(q) || (o.chiCung && q.nhan !== "cung_hang")) continue;
      const b = tenBen(q);
      (theoBen.get(b) ?? theoBen.set(b, []).get(b)!).push(q);
    }
    for (const [b, ds2] of theoBen) {
      const cung = ds2.filter(q => q.nhan === "cung_hang");
      const chon = (cung.length ? cung : ds2).map(q => ({ q, gia: giaTai(q, o.sl).gia })).sort((x, y) => theoGia(x.gia, y.gia))[0];
      ket.set(`${n.nhom_khoa}|${b}`, { q: chon.q, p: phanTram(chon.gia, gK), so: ds2.length, cung: cung.length > 0 });
      soNhom.set(b, (soNhom.get(b) ?? 0) + 1);
    }
  }
  const ben = [...soNhom.keys()].sort((a, b) => soNhom.get(b)! - soNhom.get(a)! || a.localeCompare(b, "vi"));
  return { ben, o: ket };
}

/** Đếm mặt hàng thiếu quy cách (không tính khách kể): số lượng, mặt hàng đầu tiên, và trường thiếu của nó (để mở pop-up đúng ô). */
export function demThieu(ds: Nhom[]): { so: number; dau: QuanSat | null; truong: "so_goi_thung" | "kl_goi_g" | null } {
  let so = 0; let dau: QuanSat | null = null;
  for (const n of ds) for (const q of n.quan_sat) if (veDuoc(q) && thieuQuyCach(q)) { so++; dau ??= q; }
  return { so, dau, truong: dau ? (dau.so_goi_thung == null ? "so_goi_thung" : "kl_goi_g") : null };
}

export type NutNhanh = "" | "dat" | "het" | "thieu";
const soThieu = (n: Nhom) => n.quan_sat.filter(q => veDuoc(q) && thieuQuyCach(q)).length;

/** Danh sách cột trái: lọc ngành (tên OBC), tìm (bỏ dấu, ten_nhom + ma_kome), nút nhanh; xếp so_ben giảm dần
 *  ("dat": KOME đắt hơn trung vị > 5%, xếp lệch giảm dần; "het": có mặt hàng hết; "thieu": có mặt hàng thiếu quy cách, xếp số thiếu giảm dần).
 *  Nhóm `gia_kome_lech` (giá KOME lệch bất thường — thường sai đơn vị) không hiện. */
export function locDanhSach(ds: Nhom[], o: { nganh: string; tim: string; nhanh: NutNhanh }): Nhom[] {
  const t = boDau(o.tim.trim());
  const r = ds.filter(n => !n.gia_kome_lech && (!o.nganh || n.nganh === o.nganh)
    && (!t || boDau(`${n.ten_nhom ?? ""} ${(n.ma_kome ?? []).join(" ")}`).includes(t))
    && (o.nhanh === "" || (o.nhanh === "dat" ? (n.lech_trung_vi ?? 0) > 0.05
      : o.nhanh === "het" ? n.quan_sat.some(q => veDuoc(q) && q.trang_thai === "het") : soThieu(n) > 0)));
  return r.sort((a, b) => o.nhanh === "dat" ? (b.lech_trung_vi ?? 0) - (a.lech_trung_vi ?? 0)
    : o.nhanh === "thieu" ? soThieu(b) - soThieu(a) || b.so_ben - a.so_ben : b.so_ben - a.so_ben);
}
