// Dải thời gian của khối "Sản phẩm sắp hết hạn": trục ngang = số ngày còn tới hạn,
// cỡ chấm ∝ √giá trị tồn (diện tích ∝ tiền).
export function mienHan(con_lai: number[]): { tu: number; den: number } {
  return { tu: Math.min(-15, ...con_lai), den: Math.max(90, ...con_lai) };
}

export function xHan(c: number, m: { tu: number; den: number }): number {
  return Math.max(0, Math.min(1, (c - m.tu) / (m.den - m.tu || 1)));
}

export function banKinh(gia_tri: number, max: number): number {
  if (!(max > 0) || !(gia_tri > 0)) return 4;
  return 4 + 8 * Math.sqrt(Math.min(gia_tri, max) / max);
}
