// Luật màu của màn Thị trường & đối thủ (đặc tả §3.1) — định nghĩa MỘT lần.
import { yen } from "../dinh_dang";
import { nhanDonVi, type QuanSat } from "./kieu";

// ĐỎ = bất lợi cho KOME (đối thủ rẻ hơn KOME), XANH = có lợi cho KOME, XÁM = ngang (±5%).
export const LECH_NGANG = 5;   // |%| ≤ 5 là ngang
export const NGAY_CU = 60;     // giá quá 60 ngày tuổi thì thanh mờ
export type MauLech = "do" | "xanh" | "xam";

/** p = % giá ĐỐI THỦ so với giá KOME đang chọn. p < −5 → đỏ; p > 5 → xanh; còn lại hoặc chưa biết → xám. */
export function mauLech(p: number | null | undefined): MauLech {
  if (p == null || Number.isNaN(p)) return "xam";
  return p < -LECH_NGANG ? "do" : p > LECH_NGANG ? "xanh" : "xam";
}

/** pKome = % giá KOME so với trung vị thị trường — ngược chiều: KOME đắt hơn > 5% → đỏ, rẻ hơn > 5% → xanh. */
export function mauKomeSoTT(pKome: number | null | undefined): MauLech {
  if (pKome == null || Number.isNaN(pKome)) return "xam";
  return pKome > LECH_NGANG ? "do" : pKome < -LECH_NGANG ? "xanh" : "xam";
}

/** % của `gia` so với `goc`, làm tròn số nguyên; thiếu giá hoặc gốc 0 → null (không bao giờ NaN / 0 thay chưa biết). */
export const phanTram = (gia: number | null | undefined, goc: number | null | undefined) =>
  (gia == null || !goc ? null : Math.round(100 * (gia / goc - 1)));

/** Giá BẤT THƯỜNG (cờ `bat_thuong` của mart.gia_doi_thu_hien_hanh — > 2× / < ½ mốc; mốc = trung vị nhóm ≥ 3 bên, không thì
 *  giá chuẩn KOME, B18): KHÔNG tô màu lệch, KHÔNG đếm vào ô số, vẽ xám; vẫn bấm được để sửa / xác nhận. Giao diện không tự
 *  xét lại — chỉ đọc cờ. */
export const laBatThuong = (q: Pick<QuanSat, "bat_thuong"> | null | undefined) => !!q?.bat_thuong;

/** Câu lý do cho ô nổi: "Giá bất thường: ¥1/kg dưới ½ giá chuẩn KOME ¥454/kg — không so, không đếm." */
export function lyDoBatThuong(q: Pick<QuanSat, "yen_chuan" | "don_vi_so" | "moc_bat_thuong" | "moc_bat_thuong_la">): string {
  const dv = q.don_vi_so === "kg" ? "kg" : nhanDonVi(q.don_vi_so.replace(/^don_vi:/, ""));
  const m = q.moc_bat_thuong ?? null, g = q.yen_chuan;
  const moc = m == null ? "giá tham chiếu của nhóm"
    : q.moc_bat_thuong_la === "kome" ? `giá chuẩn KOME ${yen(m)}/kg` : `trung vị nhóm ${yen(m)}/${dv}`;
  const chieu = g != null && m != null && g > m ? "trên 2×" : "dưới ½";
  return `Giá bất thường: ${yen(g)}/${dv} ${chieu} ${moc} — không so, không đếm.`;
}
