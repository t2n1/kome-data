// Điền nhanh của màn Ngân sách (2026-10-01): chỉ ĐỀ XUẤT số vào ô — không lưu gì, người dùng
// vẫn xem và bấm Lưu (biểu mẫu POST /ngan-sach thật). Không phải chỉ số: là cách chia một con
// số người ta gõ. Luật làm tròn: tiền là số nguyên yên, và phần chia PHẢI cộng lại ĐÚNG bằng
// tổng đã gõ (phần dư của phép làm tròn dồn vào phần lớn nhất) — lệch một yên là ô "còn" báo
// sai "còn ¥1 chưa chia".

/** Chia `tong` thành các phần nguyên theo trọng số (≥ 0). Σ kết quả = `tong` đúng từng yên.
 *  Mọi trọng số ≤ 0 / rỗng -> chia đều. */
export function chiaTheoTrongSo(tong: number, trongSo: number[]): number[] {
  const n = trongSo.length;
  if (!n) return [];
  const w = trongSo.map(v => (Number.isFinite(v) && v > 0 ? v : 0));
  const tw = w.reduce((s, v) => s + v, 0);
  const ts = tw > 0 ? w : w.map(() => 1);
  const t = tw > 0 ? tw : n;
  const ra = ts.map(v => Math.floor((tong * v) / t));
  const du = tong - ra.reduce((s, v) => s + v, 0);
  let lon = 0;
  ts.forEach((v, i) => { if (v > ts[lon]) lon = i; });
  ra[lon] += du;
  return ra;
}

/** Trọng số mùa từ thực tế năm trước: tháng không có số năm trước lấy TRUNG BÌNH các tháng có
 *  số (không phải 0 — tháng không biết không được thành tháng không bán). Không tháng nào có
 *  số -> chia đều. Năm trước âm (赤伝) coi như 0. */
export function trongSoMua(namTruoc: (number | null | undefined)[]): number[] {
  const co = namTruoc.filter((v): v is number => v != null).map(v => Math.max(v, 0));
  const tb = co.length ? co.reduce((s, v) => s + v, 0) / co.length : 1;
  return namTruoc.map(v => (v == null ? tb : Math.max(v, 0)));
}

/** Phần của từng sale trong một số tháng: `pt` là % (0–100) từng người. Phần chưa chia
 *  (100 − Σ%) KHÔNG giao cho ai — nó là ô "còn". Khi Σ% = 100 thì Σ kết quả = `tong`. */
export function chiaPhanTram(tong: number, pt: number[]): number[] {
  const tp = pt.reduce((s, v) => s + v, 0);
  if (tp <= 0) return pt.map(() => 0);
  const giao = tp >= 100 ? tong : Math.round((tong * tp) / 100);
  return chiaTheoTrongSo(giao, pt);
}

/** % từng người (số nguyên, Σ = 100) theo thực tế năm trước; không ai có số -> chia đều. */
export function phanTramTheo(thucTe: number[]): number[] {
  const n = thucTe.length;
  if (!n) return [];
  return chiaTheoTrongSo(100, thucTe.map(v => Math.max(v, 0)));
}

/** Kéo vạch giữa người i và i+1 trên thanh chia: dời `delta` điểm % từ người i+1 sang người i
 *  (âm = ngược lại), kẹp để không ai < 0. Tổng không đổi. */
export function keoVach(pt: number[], i: number, delta: number): number[] {
  const ra = [...pt];
  const d = Math.max(-ra[i], Math.min(ra[i + 1], Math.round(delta)));
  ra[i] += d;
  ra[i + 1] -= d;
  return ra;
}
