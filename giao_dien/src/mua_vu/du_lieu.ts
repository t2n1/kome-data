// Dữ liệu màn Mùa vụ: /api/mua-vu (kome/mua_vu.py ← mart.mua_vu_ngay, 058) là mã × ngày
// dạng cột. Dựng mảng LUỸ KẾ một lần; tổng một cửa sổ [a, b] = L[b+1] − L[a] — O(1)/mã,
// nên kéo thanh thời gian không hỏi lại máy chủ. Chỉ số KHÔNG định nghĩa ở đây: số của
// từng (mã, ngày) là của mart, ở đây chỉ cộng các ngày.
import { gon, so_luong, yen } from "../dinh_dang";

export type ChiSo = "dt" | "lg" | "sl";

/** In một giá trị của chỉ số: tiền theo ¥, số lượng giữ phần thập phân (ケース lẻ). */
export const inSo = (cs: ChiSo, v: number) => (cs === "sl" ? so_luong(v) : yen(v));
export const inGon = (cs: ChiSo, v: number) => (cs === "sl" ? so_luong(v, 0) : gon(v));

/** Câu nói rõ khi cộng số lượng — dùng chung cho mọi khối của màn khi `cs = sl`. */
export const CAU_SO_LUONG = " Số lượng cộng lẫn thùng (ケース) và lẻ (バラ): so MỘT mã qua các mùa là đúng, so kích thước ô giữa hai mã khác nhau thì không.";

/** Tháng lịch → mùa (lớp CSS `.mv-mua-<mùa>`). MỘT ánh xạ cho thanh thời gian và bản đồ nhiệt. */
export const MUA: Record<number, "xuan" | "he" | "thu" | "dong"> = {
  3: "xuan", 4: "xuan", 5: "xuan", 6: "he", 7: "he", 8: "he",
  9: "thu", 10: "thu", 11: "thu", 12: "dong", 1: "dong", 2: "dong",
};
export type MaMV = { ma: string; ten: string; nganh: string; an: boolean };
export type DuLieuMV = {
  ngay_dau: string | null; ngay_cuoi: string | null; ma: MaMV[]; nganh: string[];
  dong: { i: number[]; d: number[]; dt: number[]; lg: number[]; sl: number[] };
  phi: number | null; tang: number | null;
};

const NGAY = 864e5;
const utc = (iso: string) => { const [y, m, d] = iso.split("-").map(Number); return Date.UTC(y, m - 1, d); };
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);

export function ngayCua(ngay_dau: string, d: number): string { return iso(utc(ngay_dau) + d * NGAY); }

export class LuyKe {
  so_ngay: number; so_ma: number;
  tongNgay: Float64Array;
  private L: Record<ChiSo, Float64Array>;
  constructor(dl: DuLieuMV) {
    this.so_ma = dl.ma.length;
    this.so_ngay = dl.ngay_dau && dl.ngay_cuoi ? Math.round((utc(dl.ngay_cuoi) - utc(dl.ngay_dau)) / NGAY) + 1 : 0;
    const w = this.so_ngay + 1;
    this.L = { dt: new Float64Array(this.so_ma * w), lg: new Float64Array(this.so_ma * w), sl: new Float64Array(this.so_ma * w) };
    this.tongNgay = new Float64Array(this.so_ngay);
    const { i, d } = dl.dong;
    for (const cs of ["dt", "lg", "sl"] as ChiSo[]) {
      const a = this.L[cs], v = dl.dong[cs];
      for (let k = 0; k < i.length; k++) a[i[k] * w + d[k] + 1] += v[k];
      for (let m = 0; m < this.so_ma; m++) for (let t = 1; t < w; t++) a[m * w + t] += a[m * w + t - 1];
    }
    for (let k = 0; k < i.length; k++) this.tongNgay[d[k]] += dl.dong.dt[k];
  }
  tong(cs: ChiSo, m: number, a: number, b: number): number {
    const w = this.so_ngay + 1;
    a = Math.max(0, a); b = Math.min(this.so_ngay - 1, b);
    if (b < a) return 0;
    return this.L[cs][m * w + b + 1] - this.L[cs][m * w + a];
  }
}

export function cuaSo(b: number, n: number): { a: number; b: number; thieu: boolean } {
  const a = b - n + 1;
  return { a: Math.max(0, a), b, thieu: a < 0 };
}

// Cùng ngày lịch năm trước (29/2 → 28/2, đúng mart.thang_den_hom_nay). Cửa sổ năm trước
// bắt đầu trước dữ liệu → null ("—"): không so một cửa sổ thiếu ngày.
export function namTruoc(ngay_dau: string, b: number, n: number): { a: number; b: number } | null {
  const [y, m, d] = ngayCua(ngay_dau, b).split("-").map(Number);
  const dd = m === 2 && d === 29 ? 28 : d;
  const b2 = Math.round((Date.UTC(y - 1, m - 1, dd) - utc(ngay_dau)) / NGAY);
  const a2 = b2 - n + 1;
  return a2 < 0 ? null : { a: a2, b: b2 };
}
