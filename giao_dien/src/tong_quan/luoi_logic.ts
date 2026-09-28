// Bộ máy xếp chỗ của lưới Tổng quan 12 cột (đặc tả 2026-09-29-tong-quan-luoi-12-cot-design.md §2.2).
// Thuần — không DOM, không React. `nen` ĐÚNG thuật toán của kome/web/bo_cuc.py::nen; hai bản
// chạy chung tests/du_lieu/luoi_nen_ca.json (luoi_logic.test.ts ↔ tests/test_bo_cuc.py).
import type { OBoCuc } from "../khoi_dau";

export const COT = 12, RONG_MIN = 3, CAO_MIN = 2, CAO_MAX = 16;

const kep = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));

export function chong(a: OBoCuc, x: number, y: number, rong: number, cao: number) {
  return a.x < x + rong && x < a.x + a.rong && a.y < y + cao && y < a.y + a.cao;
}

/** Khối đang kéo: khoá dọc riêng `ky` và đứng TRƯỚC khối khác khi hoà khoá. */
export type UuTien = { id: string; ky: number };

/** Nén dọc: xét khối hiện theo (y, x) — hoặc theo khoá `uu` của khối đang kéo —; khối
 *  đè lên khối đã đặt bị đẩy xuống ngay dưới khối đó, rồi nổi lên tới khi chạm. */
export function nen(ds: OBoCuc[], uu?: UuTien): OBoCuc[] {
  const ky = (o: OBoCuc) => (uu && o.id === uu.id ? uu.ky : o.y);
  const hien = ds.filter(o => !o.an).sort((a, b) => {
    const d = ky(a) - ky(b);
    if (d) return d;
    if (uu && a.id === uu.id) return -1;
    if (uu && b.id === uu.id) return 1;
    return a.x - b.x;
  });
  const dat: OBoCuc[] = [];
  for (const o of hien) {
    let y = o.y;
    for (;;) {
      const dung = dat.filter(p => chong(p, o.x, y, o.rong, o.cao));
      if (!dung.length) break;
      y = Math.max(...dung.map(p => p.y + p.cao));
    }
    while (y > 0 && !dat.some(p => chong(p, o.x, y - 1, o.rong, o.cao))) y--;
    dat.push({ ...o, y });
  }
  dat.sort((a, b) => a.y - b.y || a.x - b.x);
  return [...dat, ...ds.filter(o => o.an)];
}

/** Đặt khối `id` của bố cục GỐC (lúc bắt đầu kéo) vào ô (tx, ty). Kéo xuống vượt nửa chiều
 *  cao khối là qua mặt khối bên dưới; kéo lên cũng vậy; ngang hàng thì khối kéo được ưu tiên. */
export function datCho(goc: OBoCuc[], id: string, tx: number, ty: number): OBoCuc[] {
  const o = goc.find(x => x.id === id);
  if (!o) return goc;
  const x = kep(Math.round(tx), 0, COT - o.rong), y = Math.max(0, Math.round(ty));
  const ky = y > o.y ? y + o.cao / 2 : y < o.y ? y - o.cao / 2 : y;
  const moi = { ...o, x, y };
  let ds = goc.map(p => (p.id === id ? moi : p));
  // Kéo NGANG (chưa lệch quá nửa chiều cao): khối bị đè thử DẠT SANG chỗ trống gần nhất
  // cùng hàng (thường là chỗ khối kéo vừa bỏ) trước khi bị đẩy xuống — thả khối trái lên
  // khối phải là hai khối đổi chỗ, không phải khối phải rơi xuống dưới.
  if (Math.abs(y - o.y) < o.cao / 2) {
    for (const p of goc) {
      if (p.an || p.id === id || !chong(p, x, y, o.rong, o.cao)) continue;
      const khac = ds.filter(q => !q.an && q.id !== p.id);
      const cho = Array.from({ length: COT - p.rong + 1 }, (_, i) => i)
        .sort((a, b) => Math.abs(a - p.x) - Math.abs(b - p.x))
        .find(nx => !khac.some(q => chong(q, nx, p.y, p.rong, p.cao)));
      if (cho !== undefined) ds = ds.map(q => (q.id === p.id ? { ...q, x: cho } : q));
    }
  }
  return nen(ds, { id, ky });
}

/** Đổi cỡ khối `id` của bố cục gốc (giữ góc trên trái), các khối khác dạt ra. */
export function doiCo(goc: OBoCuc[], id: string, rong: number, cao: number): OBoCuc[] {
  const o = goc.find(x => x.id === id);
  if (!o) return goc;
  const r = kep(Math.round(rong), RONG_MIN, COT - o.x), c = kep(Math.round(cao), CAO_MIN, CAO_MAX);
  return nen(goc.map(p => (p.id === id ? { ...p, rong: r, cao: c } : p)), { id, ky: o.y });
}

/** Hiện lại khối đã ẩn: đặt ở ĐÁY, x = 0, rồi nén. */
export function hienODay(ds: OBoCuc[], id: string): OBoCuc[] {
  const day = Math.max(0, ...ds.filter(o => !o.an).map(o => o.y + o.cao));
  return nen(ds.map(o => (o.id === id ? { ...o, an: false, x: 0, y: day } : o)));
}

export function an(ds: OBoCuc[], id: string): OBoCuc[] {
  return nen(ds.map(o => (o.id === id ? { ...o, an: true } : o)));
}

/** Đáy của các khối hiện (số hàng lưới đang dùng). */
export const day = (ds: OBoCuc[]) => Math.max(0, ...ds.filter(o => !o.an).map(o => o.y + o.cao));

/** Bàn phím: mũi tên lên / xuống đổi chỗ với khối liền trên / liền dưới (cùng dải cột);
 *  trái / phải dời 1 cột. */
export function dichPhim(ds: OBoCuc[], id: string, phim: "len" | "xuong" | "trai" | "phai"): OBoCuc[] {
  const o = ds.find(x => x.id === id);
  if (!o) return ds;
  if (phim === "trai" || phim === "phai") return datCho(ds, id, o.x + (phim === "trai" ? -1 : 1), o.y);
  const cung = ds.filter(p => !p.an && p.id !== id && p.x < o.x + o.rong && o.x < p.x + p.rong);
  if (phim === "len") {
    const tren = cung.filter(p => p.y < o.y).sort((a, b) => b.y - a.y)[0];
    return tren ? datCho(ds, id, o.x, tren.y) : ds;
  }
  const duoi = cung.filter(p => p.y > o.y).sort((a, b) => a.y - b.y)[0];
  return duoi ? datCho(ds, id, o.x, duoi.y) : ds;
}

/** Hàng lưới tại độ lệch `px` (tính từ mép trên lưới), từ các cỡ hàng thật (px) + khe;
 *  quá hàng cuối thì ngoại suy bằng cỡ hàng chuẩn. Làm tròn về đầu hàng gần nhất. */
export function hangTai(px: number, hang: number[], khe: number, chuan: number): number {
  let dau = 0;
  for (let i = 0; ; i++) {
    const cao = i < hang.length ? hang[i] : chuan;
    if (px < dau + (cao + khe) / 2) return i;
    dau += cao + khe;
    if (i > 2000) return i;
  }
}

/** Số hàng mà một chiều cao px phủ khi bắt đầu từ hàng `y`. */
export function soHang(px: number, y: number, hang: number[], khe: number, chuan: number): number {
  let tong = 0;
  for (let i = y; ; i++) {
    const cao = i < hang.length ? hang[i] : chuan;
    if (px < tong + cao / 2) return Math.max(1, i - y);
    tong += cao + khe;
    if (i - y > CAO_MAX) return CAO_MAX;
  }
}
