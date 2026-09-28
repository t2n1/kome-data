// Lưới 47 tỉnh dùng chung (bản đồ khách hàng + Sản phẩm 360). Hình học (x, y, bậc) do máy
// chủ tính (kome/ban_do.py) — ở đây chỉ vẽ. Bậc 0 = ĐÚNG BẰNG 0 (bất biến _tinh_bac).
import { useState } from "react";

export const MAU_O = ["var(--map-0)", "var(--map-1)", "var(--map-2)", "var(--map-3)", "var(--map-4)", "var(--map-5)"];
export const MAU_CHU = ["var(--chu-nhat)", "var(--chu)", "var(--chu)", "var(--map-chu-alt)", "var(--map-chu-alt)", "var(--map-chu-alt)"];

export type OTinh = { ma_jis: string; ten: string; ten_ngan: string; x: number; y: number; bac: number };

export function LuoiTinh<T extends OTinh>({ o, rong, cao, o_rong, o_cao, nhan, noi, mo_ta }: {
  o: T[]; rong: number; cao: number; o_rong: number; o_cao: number;
  nhan: (o: T) => string; noi: (o: T) => React.ReactNode; mo_ta: string;
}) {
  const [tro, datTro] = useState<T | null>(null);
  return (
    <div className="kh-bd-hinh">
      <svg viewBox={`0 0 ${rong} ${cao}`} role="img" aria-label={mo_ta}>
        {o.map(x => (
          <g key={x.ma_jis} className="kh-bd-o" tabIndex={0}
            onMouseEnter={() => datTro(x)} onMouseLeave={() => datTro(null)} onFocus={() => datTro(x)} onBlur={() => datTro(null)}>
            <rect x={x.x} y={x.y} width={o_rong} height={o_cao} rx={7} fill={MAU_O[x.bac]} />
            <text x={x.x + o_rong / 2} y={x.y + 23} textAnchor="middle" fontSize={12} fill={MAU_CHU[x.bac]}>{x.ten_ngan}</text>
            <text x={x.x + o_rong / 2} y={x.y + 41} textAnchor="middle" fontSize={10.5} fontWeight={600}
              fill={MAU_CHU[x.bac]} className="so">{nhan(x)}</text>
          </g>))}
      </svg>
      {tro && <div className="kh-bd-noi" role="status">{noi(tro)}</div>}
    </div>);
}
