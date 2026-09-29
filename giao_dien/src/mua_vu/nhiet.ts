// Bản đồ nhiệt mã × tháng của màn Mùa vụ (tab "Theo mùa"). Không định nghĩa chỉ số: mỗi ô =
// tổng các NGÀY của tháng đó từ `LuyKe.tong` (← mart.mua_vu_ngay, 058). Tính ở trình duyệt
// cùng lý do treemap (một ảnh chụp dạng cột, đổi chỉ số / cách tô không hỏi máy chủ).
import { ngayCua, type ChiSo, type LuyKe } from "./du_lieu";

export type Thang = { thang: string /* YYYY-MM */; a: number; b: number; do_dang: boolean };
export type KieuXep = "cao_diem" | "tong";

const NGAY = 864e5;
const utc = (iso: string) => { const [y, m, d] = iso.split("-").map(Number); return Date.UTC(y, m - 1, d); };
const soNgayThang = (y: number, m: number) => new Date(Date.UTC(y, m, 0)).getUTCDate();

/** Các tháng lịch từ tháng của `ngay_dau` tới tháng của `ngay_cuoi`. a/b = chỉ số ngày trong
 *  LuyKe (kẹp vào dải dữ liệu); `do_dang` = tháng không có trọn các ngày (đầu / cuối kỳ). */
export function thangCuaKy(ngay_dau: string, ngay_cuoi: string): Thang[] {
  const goc = utc(ngay_dau), het = Math.round((utc(ngay_cuoi) - goc) / NGAY);
  let [y, m] = ngay_dau.split("-").map(Number);
  const [y2, m2] = ngay_cuoi.split("-").map(Number);
  const kq: Thang[] = [];
  while (y < y2 || (y === y2 && m <= m2)) {
    const a0 = Math.round((Date.UTC(y, m - 1, 1) - goc) / NGAY);
    const b0 = a0 + soNgayThang(y, m) - 1;
    const a = Math.max(0, a0), b = Math.min(het, b0);
    kq.push({ thang: `${y}-${String(m).padStart(2, "0")}`, a, b, do_dang: a !== a0 || b !== b0 });
    if (++m > 12) { m = 1; y++; }
  }
  return kq;
}

/** Bảng hàng × cột: hàng h là mã `ma_hien[h]`, cột k là `thang[k]`. */
export function bangNhiet(L: LuyKe, cs: ChiSo, thang: Thang[], ma_hien: number[]): Float64Array {
  const c = thang.length, g = new Float64Array(ma_hien.length * c);
  ma_hien.forEach((m, h) => thang.forEach((t, k) => { g[h * c + k] = L.tong(cs, m, t.a, t.b); }));
  return g;
}

/** Bậc màu 0..5: 0 = trống (v ≤ 0 hoặc mẫu số ≤ 0); còn lại chia đều tỷ lệ 0–1 thành 5 bậc. */
export function bac(v: number, mau_so: number): number {
  if (!(v > 0) || !(mau_so > 0)) return 0;
  return Math.min(5, Math.max(1, Math.ceil((v / mau_so) * 5 - 1e-9)));
}

/** Tháng lịch (1–12) cao nhất của một hàng, CHỈ cột không dở dang. So TRUNG BÌNH mỗi năm của
 *  cùng tháng lịch, không so tổng: kỳ 19 tháng có tháng 4–8 hai lần mà tháng 10–2 một lần, cộng
 *  thẳng là tháng có hai năm dữ liệu luôn "cao điểm" chỉ vì được cộng hai lần. */
export function thangCaoDiem(hang: ArrayLike<number>, thang: Thang[]): number | null {
  const t = new Float64Array(13), n = new Float64Array(13);
  thang.forEach((x, k) => { if (!x.do_dang) { const m = +x.thang.slice(5); t[m] += hang[k]; n[m]++; } });
  for (let m = 1; m <= 12; m++) if (n[m]) t[m] /= n[m];
  let best: number | null = null;
  for (let m = 1; m <= 12; m++) if (t[m] > 0 && (best === null || t[m] > t[best])) best = m;
  return best;
}

/** Thứ tự hàng. "cao_diem": theo tháng cao điểm bắt đầu từ tháng 3 (xuân → hè → thu → đông),
 *  cùng tháng thì tổng giảm dần, không có cao điểm xuống cuối. "tong": tổng cả kỳ giảm dần. */
export function xepHang(g: Float64Array, so_cot: number, thang: Thang[], kieu: KieuXep): number[] {
  const n = so_cot ? g.length / so_cot : 0;
  const ds = Array.from({ length: n }, (_, h) => {
    const hang = g.subarray(h * so_cot, (h + 1) * so_cot);
    const cd = kieu === "cao_diem" ? thangCaoDiem(hang, thang) : null;
    return { h, tong: hang.reduce((a, b) => a + b, 0), vt: cd === null ? 99 : (cd + 9) % 12 };
  });
  ds.sort((x, y) => (kieu === "cao_diem" ? x.vt - y.vt : 0) || y.tong - x.tong || x.h - y.h);
  return ds.map(x => x.h);
}

/** Dải ngày để so "cùng tháng năm trước" với cột k. Tháng trọn → trọn cột cùng tháng năm trước
 *  (phải có trong dữ liệu và KHÔNG dở dang). Tháng k dở dang → CÙNG DẢI NGÀY năm trước (nếu năm
 *  trước có trọn dải đó) — nếp `mart.thang_den_hom_nay`. Không có → null ("—"). */
export function cungThangNamTruoc(thang: Thang[], k: number, ngay_dau: string):
  { a: number; b: number; cung_dai_ngay: boolean } | null {
  const [y, m] = thang[k].thang.split("-").map(Number);
  const ten = `${y - 1}-${String(m).padStart(2, "0")}`;
  const j = thang.findIndex(x => x.thang === ten);
  if (j < 0) return null;
  if (!thang[k].do_dang) return thang[j].do_dang ? null : { a: thang[j].a, b: thang[j].b, cung_dai_ngay: false };
  const lui = (d: number) => {
    const [yy, mm, dd] = ngayCua(ngay_dau, d).split("-").map(Number);
    return Math.round((Date.UTC(yy - 1, mm - 1, Math.min(dd, soNgayThang(yy - 1, mm))) - utc(ngay_dau)) / NGAY);
  };
  const a = lui(thang[k].a), b = lui(thang[k].b);
  // Năm trước phải có TRỌN dải đó (tháng j dở dang ở phần giao thì không so).
  return a < thang[j].a || b > thang[j].b || a < 0 ? null : { a, b, cung_dai_ngay: true };
}
