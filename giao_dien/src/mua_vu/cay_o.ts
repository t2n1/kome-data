// Treemap của màn Mùa vụ (/mua-vu). Hình học tính ở TRÌNH DUYỆT — ngoại lệ có chủ ý
// của nếp "hình học ở Python" (giai đoạn 3): kéo thanh thời gian ~570 nấc thì không
// hỏi máy chủ mỗi nấc được. `squarify` là bản chép của kome/ve_phan_tich.py::_squarify
// (Bruls–Huizing–van Wijk 2000); hai bản chạy CHUNG tests/du_lieu/squarify_ca.json
// (cay_o.test.ts ↔ tests/test_squarify_ca.py) — sửa một bản là sửa cả hai.
export type O = { x: number; y: number; w: number; h: number };
export type OMa = O & { m: number; v: number };
export type ONganh = O & { n: number; v: number; ma: OMa[] };
export type KhongVe = { phi: number; tang: number; am: number; so_am: number; tat: number };

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

// Dải nhãn ngành ở đầu mỗi khối ngành (chỉ khi khối đủ lớn để in chữ).
export const CAO_NHAN = 16;

// Hai tầng: ngành theo THỨ TỰ CỐ ĐỊNH (tổng toàn kỳ — ngành nhảy chỗ là mất dấu), mã
// trong ngành giảm dần theo giá trị cửa sổ. Diện tích ngành = tổng các mã DƯƠNG của nó
// (cùng lý lẽ `doanh_thu_ve` của ve_cay_o): mã ≤ 0 (赤伝) không vẽ được, cộng vào
// khong_ve.am — CHECK TRƯỚC khi xét ngành có tắt hay không, vì một mã âm trong một
// ngành đã tắt vẫn phải kể là "âm", không phải "tắt" (tắt = tổng dương bị ẩn bởi người
// dùng; âm = không có diện tích để vẽ, hai lý do khác nhau không được gộp một bên).
// Bất biến đối soát (có test): Σ ngành.v + phi + tang + am + tat = tong.
export function xep(p: {
  gia_tri: ArrayLike<number>; nganh_cua: number[]; thu_tu_nganh: number[]; tat: Set<number>;
  phi: number | null; tang: number | null; w: number; h: number;
}): { nganh: ONganh[]; khong_ve: KhongVe; tong: number } {
  const kv: KhongVe = { phi: 0, tang: 0, am: 0, so_am: 0, tat: 0 };
  const theo: Map<number, { m: number; v: number }[]> = new Map();
  let tong = 0;
  for (let m = 0; m < p.nganh_cua.length; m++) {
    const v = p.gia_tri[m];
    tong += v;
    if (m === p.phi) { kv.phi += v; continue; }
    if (m === p.tang) { kv.tang += v; continue; }
    if (!(v > 0)) { if (v !== 0) { kv.am += v; kv.so_am++; } continue; }
    const n = p.nganh_cua[m];
    if (p.tat.has(n)) { kv.tat += v; continue; }
    if (!theo.has(n)) theo.set(n, []);
    theo.get(n)!.push({ m, v });
  }
  const thu_tu = p.thu_tu_nganh.filter(n => theo.has(n));
  const tong_n = thu_tu.map(n => theo.get(n)!.reduce((s, x) => s + x.v, 0));
  const o_n = squarify(tong_n, 0, 0, p.w, p.h);
  const nganh: ONganh[] = thu_tu.map((n, k) => {
    const o = o_n[k];
    const ds = theo.get(n)!.sort((a, b) => b.v - a.v);
    const nhan = o.h >= 40 && o.w >= 60 ? CAO_NHAN : 0;
    const x = o.x + 1, y = o.y + 1 + nhan, w = Math.max(0, o.w - 2), h = Math.max(0, o.h - 2 - nhan);
    const o_m = w > 0 && h > 0 ? squarify(ds.map(d => d.v), x, y, w, h) : ds.map(() => ({ x, y, w: 0, h: 0 }));
    return { ...o, n, v: tong_n[k], ma: ds.map((d, j) => ({ ...o_m[j], m: d.m, v: d.v })) };
  });
  return { nganh, khong_ve: kv, tong };
}
