// Cách vẽ B · Chấm (đặc tả §4.2, bản phác ca-trang-8.html veCham): mỗi nhóm một hàng, mỗi chấm một mặt hàng đối thủ,
// trục = % so giá KOME đang chọn (vạch 0 = KOME), kẹp −60…+60 %. Chấm đặc = cùng thương hiệu, vòng rỗng = khác thương
// hiệu, màu mau.ts::mauLech; đuôi đứt từ giá 1 thùng khi rẻ đi nhờ mua nhiều; viền vàng khi hết. Dòng: dongCot (mở rộng).
import { Fragment } from "react";
import { ONoi } from "../chung/ONoi";
import { yen } from "../dinh_dang";
import type { Nhom } from "./kieu";
import { mauLech, phanTram } from "./mau";
import { NoiGia } from "./ONoiGia";
import { dongCot, giaKome, pcDau, type SoLuong } from "./so_sanh_logic";
import type { MoSua } from "./BieuDoCot";

const W = 760, LW = 200, RH = 50, TREN = 30, LO = -60, HI = 60;
const MAU: Record<string, string> = { do: "var(--do)", xanh: "var(--ok-vien)", xam: "var(--chu-mo)" };
const x = (p: number) => LW + (Math.max(LO, Math.min(HI, p)) - LO) / (HI - LO) * (W - LW - 20);
const ngan = (t: string, n: number) => (t.length > n ? t.slice(0, n - 1) + "…" : t);

export function BieuDoCham({ ds, sl, gk, chiCung, mo }: { ds: Nhom[]; sl: SoLuong; gk: string; chiCung: boolean; mo: MoSua }) {
  const H = TREN + ds.length * RH + 22;
  return (
    <div className="dt-cuon">
      <svg viewBox={`0 0 ${W} ${H}`} className="dt-svg dt-svg-cham" role="group" aria-label="Giá đối thủ so với KOME, theo phần trăm">
        {[-50, -25, 0, 25, 50].map(p => (
          <Fragment key={p}>
            <line x1={x(p)} x2={x(p)} y1={20} y2={H - 18} stroke={p ? "var(--vien)" : "var(--do)"} strokeWidth={p ? 1 : 2}
              strokeDasharray={p ? "2 3" : undefined} />
            <text x={x(p)} y={H - 4} fontSize={10} textAnchor="middle" className="t-nhat">{pcDau(p)}</text>
          </Fragment>))}
        <text x={x(0)} y={12} fontSize={11} textAnchor="middle" className="t-kome">KOME</text>
        <text x={x(-40)} y={12} fontSize={11} className="t-do">◀ đối thủ rẻ hơn KOME</text>
        <text x={x(40)} y={12} fontSize={11} textAnchor="end" className="t-xanh">KOME rẻ hơn ▶</text>
        {ds.map((n, i) => {
          const y = TREN + i * RH + RH / 2, gK = giaKome(n, gk);
          const hang = dongCot(n, { sl, gk, chiCung, moRong: true }).dong.filter(d => !d.kome);
          const thieu = hang.filter(d => d.gia == null);   // thiếu giá của MẶT HÀNG (thiếu giá KOME đã nói ở nhãn hàng)
          return (
            <g key={n.nhom_khoa + n.don_vi_so}>
              <line x1={LW} x2={W - 20} y1={y} y2={y} stroke="var(--vien-phu)" />
              <text x={LW - 8} y={y - 2} fontSize={11.5} textAnchor="end">{ngan(n.ten_nhom ?? n.nhom_khoa, 26)}</text>
              <text x={LW - 8} y={y + 12} fontSize={10} textAnchor="end" className="t-nhat">
                {gK == null ? "chưa có giá KOME" : `KOME ${yen(gK)}${n.don_vi_so === "kg" ? "/kg" : ""}`}</text>
              {hang.map((d, j) => {
                if (d.p == null) return null;
                const yy = y + (j % 3 - 1) * 8, m = MAU[mauLech(d.p)];
                const p1 = phanTram(d.giaLe, gK);
                const q = d.q!;
                return (
                  <g key={`${q.nguon}${q.id}`} opacity={d.cu ? 0.4 : 1}>
                    {p1 != null && p1 !== d.p && (
                      <g aria-hidden="true" pointerEvents="none">
                        <line x1={x(p1)} x2={x(d.p)} y1={yy} y2={yy} stroke="var(--chu-mo)" strokeDasharray="2 2" />
                        <circle cx={x(p1)} cy={yy} r={2.5} fill="var(--chu-mo)" />
                      </g>)}
                    <ONoi svg nhan={`${d.ben} · ${d.ten}: ${yen(d.gia)}, ${pcDau(d.p)} so KOME`} onBam={() => mo(q)}
                      noi_dung={<NoiGia n={n} q={q} sl={sl} gk={gk} />}>
                      <circle className="dt-dich" cx={x(d.p)} cy={yy} r={d.cung ? 7 : 6} fill={d.cung ? m : "var(--nen-the)"}
                        fillOpacity={d.cung ? 0.85 : 1} stroke={d.het ? "var(--canh-chu)" : m} strokeWidth={d.het || !d.cung ? 2 : 1} />
                    </ONoi>
                  </g>);
              })}
              {thieu.length > 0 && (
                <text x={W - 20} y={y - 8} fontSize={11} textAnchor="end" className="t-cam t-dam" role="button" tabIndex={0}
                  aria-label={`${thieu.length} mặt hàng chưa có giá — điền`} onClick={() => mo(thieu[0].q!, "gia_goc")}
                  onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); mo(thieu[0].q!, "gia_goc"); } }}>
                  ? {thieu.length}</text>)}
            </g>);
        })}
      </svg>
    </div>
  );
}

export function ChuGiaiCham() {
  return (
    <div className="dt-chu-giai">
      <span><i className="cg-cham" />cùng thương hiệu</span><span><i className="cg-vong" />khác thương hiệu</span>
      <span><i className="cg-le" />đuôi đứt = giá mua 1 thùng</span><span><i className="cg-het" />đang hết</span>
      <span className="cg-mo">mờ = cũ</span>
    </div>
  );
}
