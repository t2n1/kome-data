// Biểu đồ bong bóng và cầu nối của trang Doanh thu (2026-09-30). Hình học tính ở
// kome/ve_doanh_thu.py (đối soát có test ở tests/test_ve_doanh_thu.py) — ở đây chỉ vẽ,
// ô nổi và liên kết. Kỳ so = VIỀN ĐỨT (cột "Kỳ so" của cầu nối); nét đứt không dùng
// cho thứ gì khác.
import type { ReactNode } from "react";
import { DongNoi, ONoi } from "../chung/ONoi";
import { gon, so, yen } from "../dinh_dang";

export type BongDiem = { ma: string; ten: string; x: number; y: number; kich: number; tien: number | null; kep: boolean;
  cx: number; cy: number; r: number };
export type BongVe = { co: boolean; rong: number; cao: number; trai: number; phai: number; tren: number; day: number;
  bong: BongDiem[]; khong_ve: number; so_khong_ve: number; x_moc: number | null; y_moc: number | null;
  truc_x: { x: number; v: number }[]; truc_y: { y: number; v: number }[]; so_ma?: number };
export type CauNoiVe = { co: boolean; rong: number; cao: number; trai: number; day_truc: number; dau: number; cuoi: number; day: number;
  cot: { nhan: string; x: number; w: number; y: number; h: number; loai: "dau" | "cuoi" | "tang" | "giam"; gia: number;
    tu: number; den: number; so_dm: number; cx: number }[];
  noi: { x1: number; x2: number; y: number }[]; truc: { y: number; nhan: string }[]; khong_so?: { so: number; tien: number } };

const pc = (v: number) => (v >= 0 ? "+" : "") + (v * 100).toFixed(1) + "%";
const p1 = (v: number) => (v * 100).toFixed(1) + "%";

/** Bóng: `nhan_x` định dạng trục X, `mau` tô từng bóng, `noi` thêm dòng ô nổi, `href` mở trang riêng. */
export function Bong({ v, nhan_x, ten_x, ten_y, mau, noi, href, mo_ta, so_nhan = 8 }: {
  v: BongVe; nhan_x: (x: number) => string; ten_x: string; ten_y: string; so_nhan?: number;
  mau: (b: BongDiem) => string; noi: (b: BongDiem) => ReactNode; href?: (b: BongDiem) => string; mo_ta: string;
}) {
  if (!v.co) return <p className="phu">Chưa có dữ liệu để vẽ.</p>;
  return (
    <svg viewBox={`0 0 ${v.rong} ${v.cao}`} width="100%" className="bc-svg dt-bong" role="group" aria-label={mo_ta}>
      {v.truc_y.map(t => <g key={"y" + t.y}><line x1={v.trai} x2={v.phai} y1={t.y} y2={t.y} className="luoi-truc" />
        <text x={v.trai - 4} y={t.y + 3} textAnchor="end" className="chu-truc">{p1(t.v)}</text></g>)}
      {v.truc_x.map(t => <text key={"x" + t.x} x={t.x} y={v.cao - 8} textAnchor="middle" className="chu-truc">{nhan_x(t.v)}</text>)}
      {v.x_moc != null && <line x1={v.x_moc} x2={v.x_moc} y1={v.tren} y2={v.day} className="dt-moc" />}
      {v.y_moc != null && <line x1={v.trai} x2={v.phai} y1={v.y_moc} y2={v.y_moc} className="dt-moc" />}
      <text x={v.phai} y={v.day - 4} textAnchor="end" className="chu-truc dt-ten-truc">{ten_x} →</text>
      <text x={v.trai + 4} y={v.tren + 10} className="chu-truc dt-ten-truc">↑ {ten_y}</text>
      {/* Bóng xếp to → nhỏ: chỉ ghi tên `so_nhan` bóng to nhất (còn lại trong ô nổi) — hết chồng chữ. */}
      {v.bong.map((b, i) => (
        <ONoi key={b.ma} svg href={href?.(b)} nhan={b.ten} noi_dung={<><b>{b.ten}</b>{noi(b)}</>}>
          <circle cx={b.cx} cy={b.cy} r={b.r} fill={mau(b)} className="dt-bong-c" />
          {i < so_nhan && b.r >= 14 && <text x={b.cx} y={b.cy + 3} textAnchor="middle" className="dt-bong-chu" pointerEvents="none">
            {b.ten.length > 9 ? b.ten.slice(0, 8) + "…" : b.ten}</text>}
        </ONoi>))}
    </svg>
  );
}

export const dongBong = { tang: (b: BongDiem, nhan_ss: string) => <DongNoi nhan={`So ${nhan_ss}`} gia={pc(b.x) + (b.kep ? " (ngoài trục)" : "")} />,
  bien: (b: BongDiem) => <DongNoi nhan="Biên lãi gộp" gia={p1(b.y)} />,
  khach: (b: BongDiem) => <DongNoi nhan="Khách mua" gia={so(b.x)} /> };

export function CauNoi({ v, nhan_ss }: { v: CauNoiVe; nhan_ss: string }) {
  if (!v.co) return <p className="phu">{nhan_ss}: không có số để so theo danh mục.</p>;
  const mau = (l: string) => l === "tang" ? "var(--ok-vien)" : l === "giam" ? "var(--loi-vien)" : "var(--lien-ket)";
  return (
    <svg viewBox={`0 0 ${v.rong} ${v.cao}`} width="100%" className="bc-svg" role="group" aria-label={`Doanh thu từ ${nhan_ss} tới kỳ này theo danh mục`}>
      {v.truc.map(t => <g key={t.y}><line x1={v.trai} x2={v.rong - 10} y1={t.y} y2={t.y} className="luoi-truc" />
        <text x={v.trai - 4} y={t.y + 3} textAnchor="end" className="chu-truc">{t.nhan}</text></g>)}
      {v.noi.map((n, i) => <line key={i} x1={n.x1} x2={n.x2} y1={n.y} y2={n.y} className="dt-noi" />)}
      {v.cot.map((c, i) => (
        <ONoi key={i} svg nhan={c.nhan} noi_dung={<><b>{c.nhan}</b>
          {c.loai === "dau" ? <DongNoi nhan={nhan_ss} gia={yen(c.gia)} />
            : c.loai === "cuoi" ? <DongNoi nhan="Kỳ này (cùng dải so)" gia={yen(c.gia)} />
            : <><DongNoi nhan={c.gia >= 0 ? "Kéo lên" : "Kéo xuống"} gia={yen(c.gia)} />
              {c.so_dm > 1 && <DongNoi nhan="Gộp" gia={`${c.so_dm} danh mục`} />}</>}</>}>
          {/* Kỳ so = cột viền đứt (luật chung: nét đứt chỉ cho kỳ so). */}
          <rect x={c.x} y={c.y} width={c.w} height={c.h} rx={2}
            fill={c.loai === "dau" ? "none" : mau(c.loai)} opacity={c.loai === "dau" ? 1 : 0.8}
            stroke={c.loai === "dau" ? "var(--vien-dam)" : "none"} strokeWidth={1.4} strokeDasharray={c.loai === "dau" ? "4 3" : undefined} />
          <text x={c.cx} y={c.y - 4} textAnchor="middle" className="chu-truc">{c.loai === "dau" || c.loai === "cuoi" ? gon(c.gia) : (c.gia >= 0 ? "+" : "") + gon(c.gia)}</text>
          <text x={c.cx} y={v.day_truc + 14} textAnchor="middle" className="chu-truc">{c.nhan.length > 6 ? c.nhan.slice(0, 5) + "…" : c.nhan}</text>
        </ONoi>))}
    </svg>
  );
}
