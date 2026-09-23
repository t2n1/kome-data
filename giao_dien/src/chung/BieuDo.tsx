// Biểu đồ theo trục X rời rạc (ngày / tháng / quý) — cột, cột nền, đường, đường
// nét đứt. Vẽ bằng SVG như gói thiết kế (không thư viện chart), nhưng TƯƠNG TÁC:
//   * di chuột / chạm: vạch dọc + ô nổi đúng số mọi chuỗi đang bật;
//   * bấm chú giải: bật/tắt từng chuỗi;
//   * bấm một cột (nếu có `onBam`): đi tới danh sách đúng thứ đó;
//   * bàn phím: Tab vào biểu đồ rồi ←/→ đi qua từng điểm (ô nổi đọc được).
import { useMemo, useRef, useState } from "react";
import { useRong } from "./hooks";

export type Chuoi = {
  ten: string;
  kieu: "cot" | "cot_nen" | "duong" | "duong_dut";
  gia_tri: (number | null)[];
  mau: string;               // biến CSS, vd "var(--ok-vien)"
  mau_tung_cot?: (string | null)[]; // tô riêng từng cột (đạt/hụt ngân sách…)
  truc_phai?: boolean;       // trục phụ (tỷ lệ %) — thang riêng
  an_mac_dinh?: boolean;
};

type Props = {
  nhan: string[];                         // nhãn trục X
  nhan_day_du?: string[];                 // nhãn trong ô nổi (mặc định = nhan)
  chuoi: Chuoi[];
  cao?: number;
  dinh_dang: (v: number | null, c: Chuoi) => string;
  dinh_dang_truc?: (v: number) => string;
  onBam?: (i: number) => void;
  moi_nhan?: number;                      // cứ bao nhiêu điểm in một nhãn trục X
  mo_ta: string;                          // cho trình đọc màn hình
  vach?: { i: number; chu: string } | null;  // vạch dọc đánh dấu (vd "hôm nay")
};

export function BieuDo({ nhan, nhan_day_du, chuoi, cao = 200, dinh_dang, dinh_dang_truc, onBam,
  moi_nhan, mo_ta, vach }: Props) {
  const [khung, rong] = useRong<HTMLDivElement>();
  const [tat, datTat] = useState<Record<string, boolean>>(
    () => Object.fromEntries(chuoi.filter(c => c.an_mac_dinh).map(c => [c.ten, true])));
  const [tro, datTro] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const W = Math.max(rong, 200), H = cao;
  const tr = 44, ph = chuoi.some(c => c.truc_phai && !tat[c.ten]) ? 40 : 10, tren = 10, duoi = 22;
  const n = nhan.length;
  const bat = chuoi.filter(c => !tat[c.ten]);

  const [maxT, maxP] = useMemo(() => {
    let a = 0, b = 0;
    for (const c of bat) for (const v of c.gia_tri) if (v != null) {
      if (c.truc_phai) b = Math.max(b, v); else a = Math.max(a, v);
    }
    return [a || 1, b || 1];
  }, [bat]);
  const minT = useMemo(() => Math.min(0, ...bat.filter(c => !c.truc_phai).flatMap(c => c.gia_tri.filter((v): v is number => v != null))), [bat]);

  const x0 = tr, x1 = W - ph, bw = (x1 - x0) / Math.max(n, 1);
  const cx = (i: number) => x0 + bw * (i + 0.5);
  const yT = (v: number) => tren + (H - tren - duoi) * (1 - (v - minT) / (maxT - minT || 1));
  const yP = (v: number) => tren + (H - tren - duoi) * (1 - v / maxP);
  const cot = bat.filter(c => c.kieu === "cot" || c.kieu === "cot_nen");
  const soCot = Math.max(cot.filter(c => c.kieu === "cot").length, 1);
  const bCot = Math.min(bw * 0.72, 38) / (cot.some(c => c.kieu === "cot_nen") ? 1 : soCot);

  const vach_luoi = [0, 0.25, 0.5, 0.75, 1].map(t => minT + (maxT - minT) * t);
  const buoc = moi_nhan ?? Math.max(1, Math.ceil(n / Math.max(Math.floor((x1 - x0) / 64), 1)));

  const chon = (e: React.PointerEvent) => {
    const r = svgRef.current!.getBoundingClientRect();
    const x = (e.clientX - r.left) * (W / r.width);
    const i = Math.floor((x - x0) / bw);
    datTro(i >= 0 && i < n ? i : null);
  };

  return (
    <div className="bd" ref={khung}>
      <svg ref={svgRef} width="100%" height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={mo_ta}
        tabIndex={0} onPointerMove={chon} onPointerLeave={() => datTro(null)}
        onKeyDown={e => {
          if (e.key === "ArrowRight") datTro(t => Math.min((t ?? -1) + 1, n - 1));
          else if (e.key === "ArrowLeft") datTro(t => Math.max((t ?? n) - 1, 0));
          else if (e.key === "Enter" && tro != null) onBam?.(tro);
        }}
        onClick={() => { if (tro != null) onBam?.(tro); }}
        style={{ cursor: onBam ? "pointer" : "crosshair", display: "block" }}>
        {vach_luoi.map((v, k) => (
          <g key={k}>
            <line x1={x0} x2={x1} y1={yT(v)} y2={yT(v)} className="bd-luoi" />
            <text x={x0 - 6} y={yT(v) + 3} className="bd-truc" textAnchor="end">{(dinh_dang_truc ?? String)(v)}</text>
          </g>
        ))}
        {vach && vach.i >= 0 && vach.i < n && <g>
          <line x1={cx(vach.i)} x2={cx(vach.i)} y1={tren} y2={H - duoi} className="bd-vach" />
          <text x={cx(vach.i) + 4} y={tren + 9} className="bd-truc">{vach.chu}</text>
        </g>}
        {cot.map((c, k) => c.gia_tri.map((v, i) => {
          if (v == null) return null;
          const nen = c.kieu === "cot_nen";
          const ww = nen ? Math.min(bw * 0.86, 44) : bCot;
          const lech = nen ? -ww / 2 : -bCot * soCot / 2 + bCot * cot.filter(x => x.kieu === "cot").indexOf(c);
          const y = yT(Math.max(v, 0)), y0 = yT(Math.min(v, 0));
          return <rect key={`${k}-${i}`} x={cx(i) + lech + (nen ? 0 : 0.5)} y={y} width={Math.max(ww - 1, 1)}
            height={Math.max(y0 - y, v === 0 ? 0 : 1)} rx={2}
            fill={c.mau_tung_cot?.[i] ?? c.mau} opacity={tro != null && tro !== i ? 0.55 : 1} />;
        }))}
        {bat.filter(c => c.kieu === "duong" || c.kieu === "duong_dut").map((c, k) => {
          const y = c.truc_phai ? yP : yT;
          const d = c.gia_tri.map((v, i) => v == null ? null : `${cx(i).toFixed(1)},${y(v).toFixed(1)}`)
            .reduce((acc: string[][], p) => { if (p == null) acc.push([]); else acc[acc.length - 1].push(p); return acc; }, [[]])
            .filter(s => s.length).map(s => "M" + s.join("L")).join("");
          return <path key={k} d={d} fill="none" stroke={c.mau} strokeWidth={2} strokeLinejoin="round"
            strokeLinecap="round" strokeDasharray={c.kieu === "duong_dut" ? "5 4" : undefined} />;
        })}
        {nhan.map((t, i) => (i % buoc === 0 || i === n - 1) && (
          <text key={i} x={cx(i)} y={H - 6} className="bd-truc" textAnchor="middle">{t}</text>))}
        {tro != null && <g pointerEvents="none">
          <line x1={cx(tro)} x2={cx(tro)} y1={tren} y2={H - duoi} className="bd-tro" />
          {bat.filter(c => (c.kieu === "duong" || c.kieu === "duong_dut") && c.gia_tri[tro] != null).map((c, k) => (
            <circle key={k} cx={cx(tro)} cy={(c.truc_phai ? yP : yT)(c.gia_tri[tro]!)} r={3.5} fill={c.mau} />))}
        </g>}
      </svg>
      {tro != null && <div className="bd-noi" role="status"
        style={{ left: `${Math.min(Math.max(cx(tro) / W * 100, 12), 88)}%` }}>
        <strong>{(nhan_day_du ?? nhan)[tro]}</strong>
        {bat.map(c => <div key={c.ten}><i style={{ background: c.mau_tung_cot?.[tro] ?? c.mau }} />{c.ten}
          <b>{dinh_dang(c.gia_tri[tro] ?? null, c)}</b></div>)}
        {onBam && <em>bấm để xem chi tiết</em>}
      </div>}
      <div className="bd-chu-giai">
        {chuoi.map(c => (
          <button key={c.ten} type="button" aria-pressed={!tat[c.ten]} className={tat[c.ten] ? "tat" : ""}
            onClick={() => datTat(t => ({ ...t, [c.ten]: !t[c.ten] }))}>
            <i className={c.kieu} style={{ background: c.kieu.startsWith("duong") ? undefined : c.mau, borderColor: c.mau }} />
            {c.ten}
          </button>))}
      </div>
    </div>
  );
}
