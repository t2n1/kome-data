// Logic thuần của bảng tính "Bảng dữ liệu" (đặc tả 2026-09-30-bang-du-lieu-sua §6). Không đọc DOM, không gọi mạng.
// Máy chủ (kome/bang_du_lieu.py) vẫn kiểm lại mọi ô — `kiemO` chỉ để báo lỗi sớm và gửi chữ ĐÃ chuẩn hoá.
import { so_luong, yen } from "../dinh_dang";
import { bo_dau } from "../san_pham/loc";
import type { Cho, Cot, Dong, Lech } from "./kieu";

export const khoaO = (k: string, cot: string): string => `${k}\t${cot}`;

export function tachO(ko: string): [string, string] {
  const i = ko.indexOf("\t");
  return i < 0 ? [ko, ""] : [ko.slice(0, i), ko.slice(i + 1)];
}

/** Chữ đang gõ nếu có, không thì giá trị máy chủ; thiếu khoá (vd dòng đọc lại không mang `dt_12t`) → null. */
export function giaTri(d: Dong, cot: string, cho: Cho): string | null {
  const ko = khoaO(d.k, cot);
  if (Object.prototype.hasOwnProperty.call(cho, ko)) return cho[ko];
  return d.o[cot] ?? null;
}

const LA_TIEN = (ma: string) => ma.startsWith("gia:") || ma === "dt_12t";

export function hienThi(c: Cot, v: string | null): string {
  if (v == null || v === "") return "";
  if (c.kieu === "so") {
    const n = Number(v);
    if (!isFinite(n)) return v;
    return LA_TIEN(c.ma) ? yen(n) : so_luong(n, 4);
  }
  if (c.kieu === "chon") return c.chon?.find(x => x[0] === v)?.[1] ?? v;
  return v;
}

// ---------------------------------------------------------------------------------------------------------------------

const TRANG = /[\s　]/g;
const SO_NGHIN = /^[0-9]{1,3}(,[0-9]{3})+(\.[0-9]+)?$/;
const SO_THUONG = /^([0-9]+(\.[0-9]*)?|\.[0-9]+)$/;
const NGAY_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;
export const KHONG_HAN = "không hạn";

function ngayHopLe(s: string): boolean {
  const m = NGAY_ISO.exec(s);
  if (!m) return false;
  const y = +m[1], mo = +m[2], d = +m[3];
  if (y < 1) return false;
  const t = new Date(Date.UTC(2000, mo - 1, d));        // dựng năm 2000 rồi đặt năm: tránh 0-99 bị hiểu thành 19xx
  t.setUTCFullYear(y);
  return t.getUTCFullYear() === y && t.getUTCMonth() === mo - 1 && t.getUTCDate() === d;
}

/** Số ≤ 4 chữ số thập phân, không mũ, bỏ số 0 thừa: "20.0000" → "20", "83.750" → "83.75". Giá: số nguyên yên > 0. */
function chuanSo(chu: string, gia: boolean): { gt: string } | { loi: string } {
  let s = chu.replace(/[¥￥]/g, "").replace(TRANG, "");
  if (SO_NGHIN.test(s)) s = s.replace(/,/g, "");             // chỉ khi ĐÚNG dạng nghìn — "1,5" là lỗi, như máy chủ
  if (s.startsWith("-") || s.startsWith("−")) return { loi: gia ? "Giá phải là số > 0" : "Số lượng phải ≥ 0" };
  if (s.startsWith("+")) s = s.slice(1);
  if (!SO_THUONG.test(s)) return { loi: "Phải là một số (vd 24 hoặc 83.75)" };
  const n = Number(s);
  if (!isFinite(n)) return { loi: "Phải là một số" };
  if (gia) {
    const r = Math.round(n);
    if (r <= 0) return { loi: "Giá phải là số > 0" };
    if (r >= 1e12) return { loi: "Giá quá lớn" };
    return { gt: String(r) };
  }
  if (n >= 1e10) return { loi: "Số quá lớn" };
  const t = n.toFixed(4).replace(/\.?0+$/, "");
  return { gt: t === "" ? "0" : t };
}

export function kiemO(c: Cot, chu: string): { gt: string } | { loi: string } {
  if (!c.sua) return { loi: "Cột này chỉ xem, không sửa được" };
  if (c.kieu === "so") return chuanSo(chu, c.ma.startsWith("gia:"));
  if (c.kieu === "ngay") {
    const s = chu.trim();
    if (s === "") return { gt: "" };
    if (s.toLowerCase() === KHONG_HAN) return { gt: KHONG_HAN };
    return ngayHopLe(s) ? { gt: s } : { loi: "Hạn phải dạng YYYY-MM-DD hoặc '" + KHONG_HAN + "'" };
  }
  if (c.kieu === "chon") {
    const s = chu.trim(), ds = c.chon ?? [];
    if (ds.some(x => x[0] === s)) return { gt: s };
    const theoTen = ds.find(x => x[1] === s) ?? ds.find(x => x[1].toLowerCase() === s.toLowerCase());
    if (theoTen) return { gt: theoTen[0] };
    return { loi: "Giá trị không có trong danh sách" };
  }
  return { gt: chu.trim() };
}

/** Hai chuỗi "cùng giá trị": rỗng ≡ null; cột số so theo SỐ ("20" ≡ "20.0000"). */
function cungGiaTri(c: Cot, a: string | null, b: string | null): boolean {
  const x = a ?? "", y = b ?? "";
  if (x === y) return true;
  if (c.kieu === "so" && x !== "" && y !== "") {
    const p = Number(x), q = Number(y);
    return isFinite(p) && isFinite(q) && p === q;
  }
  return false;
}

/** Ô vừa gõ xong: nếu (sau chuẩn hoá) bằng giá trị máy chủ thì BỎ khỏi `cho`. Hợp lệ → lưu chữ ĐÃ chuẩn hoá (để
 *  `thanLuu` gửi đúng dạng máy chủ nhận — vd "¥1,000" → "1000"); không hợp lệ → giữ nguyên chữ gõ để giao diện báo lỗi. */
export function datO(cho: Cho, d: Dong, c: Cot, chu: string): Cho {
  const ko = khoaO(d.k, c.ma), goc = d.o[c.ma] ?? null;
  const ra = { ...cho };
  if (chu.trim() === (goc ?? "")) { delete ra[ko]; return ra; }       // gõ lại đúng chữ máy chủ (kể cả rỗng ≡ null)
  const r = kiemO(c, chu);
  if ("gt" in r && cungGiaTri(c, r.gt, goc)) { delete ra[ko]; return ra; }
  ra[ko] = "gt" in r ? r.gt : chu;
  return ra;
}

const CAN_CO_O = /^(gia|ton|han):/;

export function dan(tsv: string, neo: { d: number; c: number }, cots: Cot[], dongs: Dong[]):
  { o: { k: string; cot: string; chu: string }[]; bo_qua: number } {
  const hang = tsv.split(/\r?\n/);
  while (hang.length && hang[hang.length - 1] === "") hang.pop();
  const o: { k: string; cot: string; chu: string }[] = [];
  let bo_qua = 0;
  hang.forEach((h, i) => h.split("\t").forEach((chu, j) => {
    const d = dongs[neo.d + i], c = cots[neo.c + j];
    if (!d || !c || !c.sua) { bo_qua++; return; }
    if (CAN_CO_O.test(c.ma) && d.o[c.ma] == null) { bo_qua++; return; }   // OBC không có ô này
    o.push({ k: d.k, cot: c.ma, chu });
  }));
  return { o, bo_qua };
}

export function thanLuu(loai: "sp" | "kh", cho: Cho, dongs: Dong[]):
  { loai: string; o: { k: string; cot: string; gia_tri: string; thay: string | null }[] } {
  const theoK = new Map(dongs.map(d => [d.k, d]));
  const o: { k: string; cot: string; gia_tri: string; thay: string | null }[] = [];
  for (const [ko, gia_tri] of Object.entries(cho)) {
    const [k, cot] = tachO(ko), d = theoK.get(k);
    if (!d) continue;
    o.push({ k, cot, gia_tri, thay: d.o[cot] ?? null });               // `thay` = ĐÚNG chữ máy chủ đã trả
  }
  return { loai, o };
}

export function locDong(ds: Dong[], tim: string, chiLech: boolean, lech: Lech): Dong[] {
  let ra = ds;
  if (chiLech) {
    const co = new Set(Object.keys(lech).map(ko => tachO(ko)[0]));
    ra = ra.filter(d => co.has(d.k));
  }
  const t = bo_dau(tim.trim());
  if (!t) return ra;
  return ra.filter(d => bo_dau(d.k).includes(t) || Object.values(d.o).some(v => v != null && bo_dau(v).includes(t)));
}

const SP_DAU = ["product_name", "food_category_code", "rank_code", "unit", "case_qty"];
const KH_DAU = ["customer_name", "salesperson_code", "rank_code", "prefecture", "phone", "dt_12t", "lan_cuoi"];

export function cotMacDinh(loai: "sp" | "kh", cots: Cot[]): string[] {
  const co = new Set(cots.map(c => c.ma));
  let ds: string[];
  if (loai === "kh") ds = KH_DAU;
  else {
    const ton = cots.find(c => c.ma.startsWith("ton:"));
    ds = [...SP_DAU, ...cots.filter(c => c.ma.startsWith("gia:")).slice(0, 2).map(c => c.ma),
      ...(ton ? [ton.ma, "han:" + ton.ma.slice(4)] : []), "dt_12t"];
  }
  return ds.filter(m => co.has(m));
}

// Cột đã chọn nhớ theo loại ở máy này — tiện nghi riêng, không phải dữ liệu; mọi truy cập đều có thể ném lỗi.
const KHOA_COT = (loai: string) => `kome_bdl_cot_v1:${loai}`;

export function docCotDaChon(loai: string): string[] | null {
  try {
    const v = JSON.parse(localStorage.getItem(KHOA_COT(loai)) || "null");
    return Array.isArray(v) && v.every(x => typeof x === "string") ? v : null;
  } catch { return null; }
}

export function ghiCotDaChon(loai: string, ma: string[]): void {
  try { localStorage.setItem(KHOA_COT(loai), JSON.stringify(ma)); } catch { /* */ }
}

/** Khoảng dòng cần vẽ [dau, cuoi) (cuoi loại trừ) — `du` dòng đệm mỗi phía. Dòng cao cố định `caoDong`. */
export function khungNhin(cuon: number, cao: number, soDong: number, caoDong: number, du = 10): { dau: number; cuoi: number } {
  if (soDong <= 0 || caoDong <= 0) return { dau: 0, cuoi: 0 };
  const c = Math.max(0, cuon);
  const dau = Math.min(soDong, Math.max(0, Math.floor(c / caoDong) - du));
  const cuoi = Math.min(soDong, Math.ceil((c + Math.max(0, cao)) / caoDong) + du);
  return { dau, cuoi: Math.max(cuoi, dau) };
}
