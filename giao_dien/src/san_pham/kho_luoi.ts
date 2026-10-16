// Gom các dòng tồn (mã × lô) của /kho-hang thành MỘT thẻ mỗi mã cho lưới hình. Hàm thuần.
// Chỉ CỘNG các dòng đang hiện (sau bộ lọc lô / trạng thái / tìm / ngành) — tồn của một mã là tổng hai
// lô (bẫy #6), nên số lượng và giá trị cộng được; mọi số khác (bán hết sau, không kịp bán…) giữ nguyên
// từng lô như mart.ton_theo_lo trả, không tính lại.
import type { DongKho } from "./kieu";

export type TheKho = { ma: string; ten: string; nganh: string; nhan_trang_thai: string; mau: string;
  so_luong: number; gia_tri: number; lo: DongKho[]; khong_kip: boolean; han_gan: number | null };

/** Thứ tự thẻ = giá trị tồn của mã giảm dần (cùng chiều bảng: giá trị giảm dần); lô trong thẻ theo
 *  thứ tự bán (lô đang xuất trước, rồi lô chờ theo hạn tăng dần — đúng thứ tự bán của 042). */
export function gomTheoMa(dong: DongKho[]): TheKho[] {
  const m = new Map<string, TheKho>();
  for (const x of dong) {
    let t = m.get(x.ma);
    if (!t) {
      t = { ma: x.ma, ten: x.ten, nganh: x.nganh, nhan_trang_thai: x.nhan_trang_thai, mau: x.mau,
        so_luong: 0, gia_tri: 0, lo: [], khong_kip: false, han_gan: null };
      m.set(x.ma, t);
    }
    t.so_luong += x.so_luong ?? 0;
    t.gia_tri += x.gia_tri ?? 0;
    t.lo.push(x);
    if (x.khong_kip_ban) t.khong_kip = true;
    if (x.han_con_lai != null && (t.han_gan == null || x.han_con_lai < t.han_gan)) t.han_gan = x.han_con_lai;
  }
  const thuTu = (x: DongKho) => x.vai_tro_lo === "dang_xuat" ? 0 : 1;
  for (const t of m.values()) t.lo.sort((a, b) => thuTu(a) - thuTu(b) || (a.han_con_lai ?? 1e9) - (b.han_con_lai ?? 1e9));
  return [...m.values()].sort((a, b) => b.gia_tri - a.gia_tri || a.ma.localeCompare(b.ma));
}
