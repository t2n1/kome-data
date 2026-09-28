// Treemap của màn Mùa vụ (/mua-vu). Hình học tính ở TRÌNH DUYỆT — ngoại lệ có chủ ý
// của nếp "hình học ở Python" (giai đoạn 3): kéo thanh thời gian ~570 nấc thì không
// hỏi máy chủ mỗi nấc được. `squarify` là bản chép của kome/ve_phan_tich.py::_squarify
// (Bruls–Huizing–van Wijk 2000); hai bản chạy CHUNG tests/du_lieu/squarify_ca.json
// (cay_o.test.ts ↔ tests/test_squarify_ca.py) — sửa một bản là sửa cả hai.
export type O = { x: number; y: number; w: number; h: number };

export function squarify(gia_tri: number[], x: number, y: number, w: number, h: number): O[] {
  if (!gia_tri.length) return [];
  if (gia_tri.some(v => !(v > 0))) throw new Error("squarify chỉ nhận giá trị DƯƠNG");
  const tong = gia_tri.reduce((a, b) => a + b, 0);
  const ty_le = (w * h) / tong;
  const dt = gia_tri.map(v => v * ty_le);
  const kq: (O | null)[] = dt.map(() => null);
  let cx = x, cy = y, cw = w, ch = h;

  const xauNhat = (hang: number[], canh: number) => {
    const s_list = hang.map(i => dt[i]);
    const s = s_list.reduce((a, b) => a + b, 0);
    if (s <= 0 || canh <= 0) return Infinity;
    return Math.max((canh * canh * Math.max(...s_list)) / (s * s),
                    (s * s) / (canh * canh * Math.min(...s_list)));
  };
  const datHang = (hang: number[]) => {
    const s = hang.reduce((a, i) => a + dt[i], 0);
    if (cw >= ch) {
      const rong = ch > 0 ? s / ch : 0;
      let yy = cy;
      for (const i of hang) { const hh = rong > 0 ? dt[i] / rong : 0; kq[i] = { x: cx, y: yy, w: rong, h: hh }; yy += hh; }
      cx += rong; cw -= rong;
    } else {
      const cao = cw > 0 ? s / cw : 0;
      let xx = cx;
      for (const i of hang) { const ww = cao > 0 ? dt[i] / cao : 0; kq[i] = { x: xx, y: cy, w: ww, h: cao }; xx += ww; }
      cy += cao; ch -= cao;
    }
  };

  let hang: number[] = [];
  let i = 0;
  while (i < dt.length) {
    const canh = Math.min(cw, ch);
    if (!hang.length) { hang = [i]; i++; continue; }
    const thu = [...hang, i];
    if (xauNhat(hang, canh) >= xauNhat(thu, canh)) { hang = thu; i++; }
    else { datHang(hang); hang = []; }
  }
  if (hang.length) datHang(hang);
  return kq.filter((o): o is O => o !== null);
}
