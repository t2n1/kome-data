// Luật màu của màn Thị trường & đối thủ (đặc tả §3.1) — định nghĩa MỘT lần.
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
