// Logic thuần của bảng tính "Bảng dữ liệu" (đặc tả 2026-09-30-bang-du-lieu-sua §6). Không đọc DOM, không gọi mạng.
// Máy chủ (kome/bang_du_lieu.py) vẫn kiểm lại mọi ô — `kiemO` chỉ để báo lỗi sớm và gửi chữ ĐÃ chuẩn hoá.
import { so, so_luong, yen } from "../dinh_dang";
import { bo_dau } from "../san_pham/loc";
import type { Cho, ChoLuu, Cot, Dong, Lech } from "./kieu";

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

/** Số ≤ 4 chữ số thập phân, không mũ, bỏ số 0 thừa: "20.0000" → "20", "83.750" → "83.75". Giá: số nguyên yên > 0.
 *  Làm bằng CHUỖI (không qua số thực): quá 4 chữ số thập phân / giá có phần lẻ là LỖI, không làm tròn lặng lẽ. */
function chuanSo(chu: string, gia: boolean): { gt: string } | { loi: string } {
  let s = chu.replace(/[¥￥]/g, "").replace(TRANG, "");
  if (SO_NGHIN.test(s)) s = s.replace(/,/g, "");             // chỉ khi ĐÚNG dạng nghìn — "1,5" là lỗi, như máy chủ
  if (s.startsWith("-") || s.startsWith("−")) return { loi: gia ? "Giá phải là số > 0" : "Số lượng phải ≥ 0" };
  if (s.startsWith("+")) s = s.slice(1);
  if (!SO_THUONG.test(s)) return { loi: "Phải là một số (vd 24 hoặc 83.75)" };
  const [nguyen0, le0 = ""] = s.split(".");
  const nguyen = nguyen0.replace(/^0+(?=\d)/, "") || "0", le = le0.replace(/0+$/, "");
  const gt = le ? `${nguyen}.${le}` : nguyen;
  if (gia) {
    if (le) return { loi: "Giá là số yên nguyên" };
    if (/^0+$/.test(nguyen)) return { loi: "Giá phải là số > 0" };
    if (nguyen.length > 12 || Number(nguyen) >= 1e12) return { loi: "Giá quá lớn" };
    return { gt };
  }
  if (le.length > 4) return { loi: "Tối đa 4 chữ số thập phân" };
  if (nguyen.length > 10) return { loi: "Số quá lớn" };               // ≥ 1e10 (nguyen đã bỏ số 0 đầu)
  return { gt };
}

/** Trần độ dài ô chữ — = kome/bang_du_lieu.py::DAI_TOI_DA (đếm theo ký tự Unicode như len() của Python). */
export const DAI_TOI_DA = 200;

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
  const t = chu.trim();
  if ([...t].length > DAI_TOI_DA) return { loi: `Tối đa ${DAI_TOI_DA} ký tự` };
  return { gt: t };
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
export function datO(cho: Cho, d: Dong, c: Cot, chu: string, goc: string | null = d.o[c.ma] ?? null): Cho {
  const ko = khoaO(d.k, c.ma);
  const ra = { ...cho };
  if (chu.trim() === (goc ?? "")) { delete ra[ko]; return ra; }       // gõ lại đúng chữ máy chủ (kể cả rỗng ≡ null)
  const r = kiemO(c, chu);
  if ("gt" in r && cungGiaTri(c, r.gt, goc)) { delete ra[ko]; return ra; }
  ra[ko] = "gt" in r ? r.gt : chu;
  return ra;
}

const CAN_CO_O = /^(gia|ton|han):/;

/** Ô (dòng, cột) sửa được theo DỮ LIỆU: cột không khoá, và với cột giá / tồn / hạn thì OBC phải có ô đó. (Cờ quyền
 *  `sua_duoc` của người đang xem là việc của màn hình.) */
export const suaDuocO = (d: Dong, c: Cot): boolean => c.sua && !(CAN_CO_O.test(c.ma) && d.o[c.ma] == null);

export function dan(tsv: string, neo: { d: number; c: number }, cots: Cot[], dongs: Dong[]):
  { o: { k: string; cot: string; chu: string }[]; bo_qua: number } {
  const hang = tsv.split(/\r?\n/);
  while (hang.length && hang[hang.length - 1] === "") hang.pop();
  if (!hang.length && /^(\r?\n)?$/.test(tsv)) hang.push("");        // đúng MỘT ô rỗng (Excel chép ô trống) = xoá ô neo
  const o: { k: string; cot: string; chu: string }[] = [];
  let bo_qua = 0;
  hang.forEach((h, i) => h.split("\t").forEach((chu, j) => {
    const d = dongs[neo.d + i], c = cots[neo.c + j];
    if (!d || !c || !suaDuocO(d, c)) { bo_qua++; return; }             // cột khoá / OBC không có ô này / ngoài bảng
    o.push({ k: d.k, cot: c.ma, chu });
  }));
  return { o, bo_qua };
}

/** Lỗi của MỘT ô đang chờ (null = hợp lệ / không chờ). Ngoại lệ: chữ chờ ĐÚNG bằng giá trị OBC của ô lệch ("↺ Về giá trị
 *  OBC") luôn hợp lệ — máy chủ nhận "về OBC" kể cả khi mã OBC không có trong danh sách chọn. */
export function loiCho(c: Cot, ko: string, cho: Cho, lech: Lech): string | null {
  if (!Object.prototype.hasOwnProperty.call(cho, ko)) return null;
  const v = cho[ko], l = lech[ko];
  if (l && v === (l.obc ?? "")) return null;
  const r = kiemO(c, v);
  return "loi" in r ? r.loi : null;
}

// ---- `thay` GHI LẠI lúc ô VÀO chờ ----------------------------------------------------------------------------------
// `thay` (chữ máy chủ người sửa đã THẤY) phải là giá trị lúc ô bắt đầu được sửa, KHÔNG đọc lại từ đệm lúc lưu: đệm có thể bị
// thay (tải lại, "Lấy bản mới", dòng đọc lại sau một lần lưu mang giá trị người khác vừa ghi) — đọc lúc lưu là lặng lẽ
// "rebase" ô đang chờ lên số mới và 409 không bao giờ nổ (mất cập nhật). `ChoLuu.thay` có ĐÚNG các khoá của `cho`.

const co = (o: object, k: string) => Object.prototype.hasOwnProperty.call(o, k);
export const CHO_RONG: ChoLuu = { cho: {}, thay: {} };

/** `datO` qua trạng thái chờ: giá trị đã thấy = `thay` đã ghi (ô đang chờ) hoặc giá trị đệm LÚC NÀY (ô mới vào chờ);
 *  "bằng máy chủ → bỏ" so với giá trị đã thấy đó. */
export function datChoO(s: ChoLuu, d: Dong, c: Cot, chu: string): ChoLuu {
  const ko = khoaO(d.k, c.ma);
  const thay0 = co(s.thay, ko) ? s.thay[ko] : d.o[c.ma] ?? null;
  const cho = datO(s.cho, d, c, chu, thay0);
  const thay = { ...s.thay };
  if (co(cho, ko)) thay[ko] = thay0; else delete thay[ko];
  return { cho, thay };
}

/** Bỏ các ô khỏi chờ (cả `cho` lẫn `thay`). */
export function boCho(s: ChoLuu, ko: Iterable<string>): ChoLuu {
  const cho = { ...s.cho }, thay = { ...s.thay };
  for (const k of ko) { delete cho[k]; delete thay[k]; }
  return { cho, thay };
}

/** Sau 200: ô đã gửi mà chưa bị gõ lại → rời chờ; ô bị gõ lại trong lúc chờ máy chủ → vẫn chờ, `thay` = giá trị VỪA LƯU
 *  (chữ máy chủ đọc lại nếu có — dạng máy chủ so khi báo 409, vd "24.0000" — không thì chữ đã gửi). */
export function sauLuu(s: ChoLuu, da_gui: { k: string; cot: string; gia_tri: string }[], dong_moi: Dong[]): ChoLuu {
  const moi = new Map(dong_moi.map(d => [d.k, d]));
  const cho = { ...s.cho }, thay = { ...s.thay };
  for (const x of da_gui) {
    const ko = khoaO(x.k, x.cot);
    if (!co(cho, ko)) continue;
    if (cho[ko] === x.gia_tri) { delete cho[ko]; delete thay[ko]; continue; }
    const m = moi.get(x.k);
    thay[ko] = m && co(m.o, x.cot) ? m.o[x.cot] : x.gia_tri;
  }
  return { cho, thay };
}

/** "Ghi đè" sau 409: `thay` của ĐÚNG các ô xung đột = giá trị máy chủ hiện giờ; ô khác giữ nguyên. */
export function ghiDeCho(s: ChoLuu, xung: { k: string; cot: string; gia_tri: string | null }[]): ChoLuu {
  const thay = { ...s.thay };
  for (const x of xung) { const ko = khoaO(x.k, x.cot); if (co(s.cho, ko)) thay[ko] = x.gia_tri; }
  return { cho: s.cho, thay };
}

export function thanLuu(loai: "sp" | "kh", s: ChoLuu, dongs: Dong[]):
  { loai: string; o: { k: string; cot: string; gia_tri: string; thay: string | null }[] } {
  const theoK = new Map(dongs.map(d => [d.k, d]));
  const o: { k: string; cot: string; gia_tri: string; thay: string | null }[] = [];
  for (const [ko, gia_tri] of Object.entries(s.cho)) {
    const [k, cot] = tachO(ko), d = theoK.get(k);
    if (!d) continue;
    // `thay` = chữ máy chủ đã thấy LÚC Ô VÀO CHỜ (ghi lại); thiếu (không nên xảy ra) mới rơi về đệm.
    o.push({ k, cot, gia_tri, thay: co(s.thay, ko) ? s.thay[ko] : d.o[cot] ?? null });
  }
  return { loai, o };
}

/** Số ô tối đa mỗi lần lưu — BẰNG `kome/bang_du_lieu.py::TOI_DA_O` (có test pytest đọc dòng này). */
export const TOI_DA_O = 2000;

/** Lời nhắn khi số ô đang chờ vượt trần của máy chủ (không gửi, khỏi chờ một 400 cả lô); null nếu còn trong trần. */
export function loiQuaNhieuO(n: number): string | null {
  return n > TOI_DA_O ? `Tối đa ${so(TOI_DA_O)} ô mỗi lần lưu — đang có ${so(n)} ô; lưu bớt rồi lưu tiếp` : null;
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
