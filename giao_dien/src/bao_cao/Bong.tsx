// Biểu đồ bong bóng và cầu nối của trang Doanh thu (2026-09-30). Hình học tính ở
// kome/ve_doanh_thu.py (đối soát có test ở tests/test_ve_doanh_thu.py) — ở đây chỉ vẽ,
// ô nổi và liên kết. Kỳ so = VIỀN ĐỨT (cột "Kỳ so" của cầu nối); nét đứt không dùng
// cho thứ gì khác.
import { useState, type ReactNode } from "react";
import { DongNoi, ONoi } from "../chung/ONoi";
import { gon, so, yen } from "../dinh_dang";
import { tenNganh } from "../chung/nganh";

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
  bien: (b: BongDiem) => <DongNoi nhan="Tỷ lệ lãi gộp" gia={p1(b.y)} />,
  khach: (b: BongDiem) => <DongNoi nhan="Khách mua" gia={so(b.x)} /> };

// Cắt nhãn trục theo bề rộng ô cột (~11 đơn vị mỗi ký tự) — tên đủ nằm trong ô nổi.
const catNhan = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

export function CauNoi({ v, nhan_ss }: { v: CauNoiVe; nhan_ss: string }) {
  if (!v.co) return <p className="phu">{nhan_ss}: không có số để so theo danh mục.</p>;
  const mau = (l: string) => l === "tang" ? "var(--ok-vien)" : l === "giam" ? "var(--loi-vien)" : "var(--lien-ket)";
  return (
    <svg viewBox={`0 0 ${v.rong} ${v.cao}`} width="100%" className="bc-svg" role="group" aria-label={`Doanh thu từ ${nhan_ss} tới kỳ này theo danh mục`}>
      {v.truc.map(t => <g key={t.y}><line x1={v.trai} x2={v.rong - 10} y1={t.y} y2={t.y} className="luoi-truc" />
        <text x={v.trai - 4} y={t.y + 3} textAnchor="end" className="chu-truc">{t.nhan}</text></g>)}
      {v.noi.map((n, i) => <line key={i} x1={n.x1} x2={n.x2} y1={n.y} y2={n.y} className="dt-noi" />)}
      {v.cot.map((c, i) => (
        <ONoi key={i} svg nhan={tenNganh(c.nhan)} noi_dung={<><b>{tenNganh(c.nhan)}</b>
          {c.loai === "dau" ? <DongNoi nhan={nhan_ss} gia={yen(c.gia)} />
            : c.loai === "cuoi" ? <DongNoi nhan="Kỳ này (cùng dải so)" gia={yen(c.gia)} />
            : <><DongNoi nhan={c.gia >= 0 ? "Kéo lên" : "Kéo xuống"} gia={yen(c.gia)} />
              {c.so_dm > 1 && <DongNoi nhan="Gộp" gia={`${c.so_dm} danh mục`} />}</>}</>}>
          {/* Kỳ so = cột viền đứt (luật chung: nét đứt chỉ cho kỳ so). */}
          <rect x={c.x} y={c.y} width={c.w} height={c.h} rx={2}
            fill={c.loai === "dau" ? "none" : mau(c.loai)} opacity={c.loai === "dau" ? 1 : 0.8}
            stroke={c.loai === "dau" ? "var(--vien-dam)" : "none"} strokeWidth={1.4} strokeDasharray={c.loai === "dau" ? "4 3" : undefined} />
          <text x={c.cx} y={c.y - 4} textAnchor="middle" className="chu-truc">{c.loai === "dau" || c.loai === "cuoi" ? gon(c.gia) : (c.gia >= 0 ? "+" : "") + gon(c.gia)}</text>
          <text x={c.cx} y={v.day_truc + 14} textAnchor="middle" className="chu-truc">{catNhan(tenNganh(c.nhan), Math.max(4, Math.floor(c.w / 0.64 / 11)))}</text>
        </ONoi>))}
    </svg>
  );
}

// ---- Danh sách thay cho bong bóng (2026-10-16, chủ DN: "người không rành nhìn cũng hiểu") -------------------
// Cùng số của `ve_bong` (bóng đã vẽ + "Không vẽ"), chỉ đổi cách bày: thanh ngang xếp hạng, không trục đôi.

/** Danh mục tăng / giảm so kỳ so: thanh lệch hai phía quanh 0 (xanh tăng, đỏ giảm), xếp tăng nhiều nhất trước. */
export function TangGiam({ v, ten, nhan_ss }: { v: BongVe; ten: string; nhan_ss: string }) {
  if (!v.co) return <p className="phu">Chưa có số để so.</p>;
  const ds = [...v.bong].sort((a, b) => b.x - a.x);
  const max = Math.max(0.05, ...ds.map(b => Math.min(Math.abs(b.x), 1)));
  return (
    <div className="dt-tg">
      {ds.map(b => {
        const w = Math.min(Math.abs(b.x), 1) / max * 50;
        return (
          <ONoi key={b.ma} className="dt-tg-dong" nhan={tenNganh(b.ten)} noi_dung={<><b>{tenNganh(b.ten)}</b>
            <DongNoi nhan={ten.replace(/^./, c => c.toUpperCase())} gia={yen(b.kich)} />
            <DongNoi nhan={`So với ${nhan_ss}`} gia={pc(b.x)} /><DongNoi nhan="Tỷ lệ lãi gộp" gia={p1(b.y)} /></>}>
            <span className="dt-tg-ten" title={b.ten}>{tenNganh(b.ten)}</span>
            <span className="dt-tg-thanh"><i className={b.x >= 0 ? "tang" : "giam"}
              style={{ width: `${w}%`, [b.x >= 0 ? "left" : "right"]: "50%" } as React.CSSProperties} /></span>
            <b className={b.x >= 0 ? "tang" : "giam"}>{pc(b.x)}</b>
            <span className="so nhat-chu">{gon(b.kich)}</span>
          </ONoi>);
      })}
    </div>
  );
}

/** Mặt hàng bán chạy: thanh theo doanh thu, kèm số khách mua và tỷ lệ lãi — bấm mở trang mã. */
export function BanChay({ v, ten, n = 10 }: { v: BongVe; ten: string; n?: number }) {
  if (!v.co) return <p className="phu">Chưa có dữ liệu.</p>;
  const ds = [...v.bong].sort((a, b) => b.kich - a.kich);
  const max = Math.max(1, ...ds.map(b => b.kich));
  const [mo, datMo] = useState(false);
  const hien = mo ? ds : ds.slice(0, n);
  return (
    <div className="dt-bc">
      {hien.map((b, i) => (
        <a key={b.ma} className="dt-bc-dong" href={`/san-pham/${encodeURIComponent(b.ma)}`}
          title={`${b.ten} · ${ten} ${yen(b.kich)} · ${so(b.x)} khách mua · tỷ lệ lãi ${p1(b.y)}`}>
          <span className="nhat-chu">{i + 1}</span>
          <span className="dt-bc-ten ten-jp">{b.ten}</span>
          <span className="dt-bc-thanh"><i style={{ width: `${b.kich / max * 100}%` }} /></span>
          <b className="so">{gon(b.kich)}</b>
          <span className="nhat-chu">{so(b.x)} khách · lãi {p1(b.y)}</span>
        </a>))}
      {ds.length > n && <button type="button" className="nut-xem-them" onClick={() => datMo(!mo)} aria-expanded={mo}>
        {mo ? "Thu gọn ▴" : `Xem thêm ${so(ds.length - n)} mã ▾`}</button>}
    </div>
  );
}
