// Ba chuỗi dán vào キャンペーン管理シート — đúng những ô người dùng gõ tay (mọi cột khác của sheet là công thức):
//   tab tháng: cột A 週目 + B 期間 (một dòng mỗi mã) và cột F 商品コード — HAI lần chép vì C–E nằm giữa
//              (C/D hình, E công thức: dán đè ô trống là mất công thức);
//   値段管理: cột của tuần, từ dòng 3, đúng thứ tự dòng của sheet (ô trống = mã không chạy).
// Mã xếp theo thứ tự chữ ở cả A–B lẫn F nên hai lần dán thẳng hàng nhau.
import type { MaKeHoach, Nhom, TuanKeHoach } from "./kieu";

export const NHOM: { ma: Nhom; nhan: string; giai: string; gap?: boolean }[] = [
  { ma: "uu_tien", nhan: "Ưu tiên", giai: "Sắp hết mà có lô sắp về — chạy để đẩy hết lô cũ" },
  { ma: "day_han", nhan: "Đẩy hạn", giai: "Có lô không kịp bán trước hạn dùng" },
  { ma: "thuong", nhan: "Theo nhịp", giai: "Đến lượt chạy (tuần trước nghỉ)" },
  { ma: "can_nhip", nhan: "Cân nhịp", giai: "Tuần trước đã chạy, kéo thêm để hai nhịp đều nhau (lãi gộp khi sale cao nhất)" },
  { ma: "loai", nhan: "Không chạy", giai: "Thiếu hàng, sắp hết mà không có lô về, giá sàn dưới giá vốn, hoặc sale làm giảm lãi gộp", gap: true },
  { ma: "nghi", nhan: "Nghỉ nhịp", giai: "Đã chạy tuần trước — tuần này nghỉ", gap: true },
];

export const macDinh = (t: TuanKeHoach): Set<string> => new Set(t.ma.filter(m => m.chon).map(m => m.ma));

const xep = (chon: Set<string>) => [...chon].sort();

export function chepAB(t: TuanKeHoach, chon: Set<string>): string {
  return xep(chon).map(() => `${t.tuan_so}\t${t.ky}`).join("\n");
}

export function chepF(chon: Set<string>): string {
  return xep(chon).join("\n");
}

export function chepGia(thu_tu: string[], chon: Set<string>): string {
  return thu_tu.map(m => (m && chon.has(m) ? m : "")).join("\n");
}

/** Mã đã chọn mà KHÔNG có dòng trên 値段管理 — chép cột tuần sẽ thiếu chúng (phải thêm dòng trên sheet trước). */
export function thieuDong(thu_tu: string[], chon: Set<string>): string[] {
  const co = new Set(thu_tu);
  return xep(chon).filter(m => !co.has(m));
}

export function theoNhom(ds: MaKeHoach[]): Map<Nhom, MaKeHoach[]> {
  const ra = new Map<Nhom, MaKeHoach[]>(NHOM.map(n => [n.ma, []]));
  for (const m of ds) ra.get(m.nhom)?.push(m);
  for (const v of ra.values()) v.sort((a, b) => a.ma.localeCompare(b.ma));
  return ra;
}

/** "2026-10-23" → "10/23". */
export const md = (iso: string | null | undefined) => (iso ? `${+iso.slice(5, 7)}/${+iso.slice(8, 10)}` : "—");

/** Số giờ từ lúc gửi tới `bay_gio` — bản soát cũ hơn 36 giờ (quá một ngày làm việc) thì màn cảnh báo. */
export const gioTu = (iso: string, bay_gio: Date) => (bay_gio.getTime() - new Date(iso).getTime()) / 3_600_000;
export const CU_GIO = 36;
