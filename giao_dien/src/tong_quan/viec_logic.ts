// Logic thuần của khối "Việc cần làm hôm nay" (đặc tả 2026-09-28-tong-quan-it-chu-design.md §5).
// `chu` là câu của MÁY CHỦ (kome/khoi_tong_quan.py) — dòng chỉ hiện TÊN, câu đầy đủ vào ô nổi.
export type ViecTho = { muc: "gap" | "canh" | "thuong"; tag: string; chu: string };

export function tenViec(chu: string): string {
  const m = /^Gọi(?:\s+lại)?\s+(.+?)(?:\s+—\s|$)/.exec(chu);
  return m ? m[1] : chu;
}

const THU_TU: Record<ViecTho["muc"], number> = { gap: 0, canh: 1, thuong: 2 };

export function sapViec<T extends ViecTho>(v: T[]): T[] {
  return v.map((x, i) => [x, i] as const).sort((a, b) => THU_TU[a[0].muc] - THU_TU[b[0].muc] || a[1] - b[1]).map(x => x[0]);
}

export function demTheoTag(v: ViecTho[]): { tag: string; muc: ViecTho["muc"]; dem: number }[] {
  const m = new Map<string, { tag: string; muc: ViecTho["muc"]; dem: number }>();
  for (const x of v) {
    const c = m.get(x.tag);
    if (c) c.dem += 1; else m.set(x.tag, { tag: x.tag, muc: x.muc, dem: 1 });
  }
  return [...m.values()];
}
