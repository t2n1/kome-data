// Thang của thanh ngang / thanh chồng (đặc tả 2026-09-28-tong-quan-it-chu-design.md §3.3–3.4).
// Số ÂM (赤伝 — luật cấm lọc bỏ) vẽ thành thanh rộng 0; SỐ vẫn in số âm thật ở nơi gọi.

export function tyLeThanh(v: number | null | undefined, thang: number): number {
  if (v == null || !(thang > 0)) return 0;
  return Math.max(0, Math.min(1, v / thang));
}

export function thangChung(ds: { gia_tri: number; ss?: number | null }[]): number {
  let m = 0;
  for (const x of ds) m = Math.max(m, x.gia_tri, x.ss ?? 0);
  return m > 0 ? m : 1;
}

export function chiaKhuc(dem: number[]): number[] {
  const tong = dem.reduce((s, x) => s + (x > 0 ? x : 0), 0);
  return dem.map(x => (tong > 0 && x > 0 ? (x / tong) * 100 : 0));
}
