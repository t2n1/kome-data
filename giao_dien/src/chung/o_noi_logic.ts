// Logic thuần của ô nổi (đặc tả 2026-09-28-tong-quan-it-chu-design.md §3.1) — tách khỏi
// ONoi.tsx để Vitest (môi trường node, không DOM) canh được.

/** Bấm vào phần tử có ô nổi: chạm lần 1 chỉ MỞ ô nổi, chạm lần 2 mới đi liên kết.
 *  Chuột / bút có rê (ô nổi đã hiện lúc rê) nên bấm là đi. */
export function buocCham(daMo: boolean, kieu: string): "mo" | "di" {
  return kieu === "touch" && !daMo ? "mo" : "di";
}

/** Toạ độ `position: fixed` của ô nổi: dưới phần tử (lật lên khi sát đáy và phía trên
 *  đủ chỗ), căn giữa theo phần tử, không tràn mép trái / phải. */
export function viTriNoi(goc: { left: number; top: number; right: number; bottom: number },
  noi: { w: number; h: number }, khung: { w: number; h: number }, le = 8): { left: number; top: number } {
  const giua = (goc.left + goc.right) / 2;
  const left = Math.max(le, Math.min(giua - noi.w / 2, khung.w - noi.w - le));
  const duoi = goc.bottom + 6, tren = goc.top - 6 - noi.h;
  const top = duoi + noi.h <= khung.h - le || tren < le ? duoi : tren;
  return { left: Math.round(left), top: Math.round(top) };
}
