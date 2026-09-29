// Cách vẽ C · Bảng nhiệt (đặc tả §4.2, bản phác ca-trang-8.html veNhiet): nhóm × bên. Ô = mặt hàng cùng thương hiệu
// rẻ nhất của bên đó, không có thì khác thương hiệu rẻ nhất (so_sanh_logic.ts::oNhiet). Màu mau.ts::mauLech, độ đậm ∝ |p|
// (tối đa ở 40 %); ô nhạt viền đứt + "≈" = chỉ có khác thương hiệu; "·n" = bên đó có n mặt hàng (ô nổi liệt kê hết).
// Cuộn ngang trong khung (không co chữ).
import { ONoi } from "../chung/ONoi";
import type { Nhom } from "./kieu";
import { mauLech } from "./mau";
import { NoiGia } from "./ONoiGia";
import { giaTai, khoaNhom, khoaONhiet, matHangCuaBen, oNhiet, pcDau, type SoLuong } from "./so_sanh_logic";
import type { MoSua } from "./BieuDoCot";

const CW = 62, LW = 200, RH = 32, TH = 72, DAM_TOI_DA = 40;
const MAU: Record<string, string> = { do: "var(--do)", xanh: "var(--ok-vien)", xam: "var(--chu-mo)" };
const ngan = (t: string, n: number) => (t.length > n ? t.slice(0, n - 1) + "…" : t);

export function BangNhiet({ ds, sl, gk, chiCung, mo }: { ds: Nhom[]; sl: SoLuong; gk: string; chiCung: boolean; mo: MoSua }) {
  const { ben, o } = oNhiet(ds, { sl, gk, chiCung });
  const W = LW + CW * Math.max(1, ben.length) + 4, H = TH + RH * ds.length + 4;
  return (
    <div className="dt-nhiet-khung">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="dt-svg" role="group" aria-label="Bảng nhiệt nhóm × đối thủ">
        {ben.map((b, i) => (
          <text key={b} transform={`translate(${LW + i * CW + CW / 2},${TH - 6}) rotate(-35)`} fontSize={10.5} className="t-nhat">
            {ngan(b, 16)}</text>))}
        {ds.map((n, j) => {
          const y = TH + j * RH;
          return (
            <g key={khoaNhom(n)}>
              <text x={LW - 8} y={y + 20} fontSize={11.5} textAnchor="end">{ngan(n.ten_nhom ?? n.nhom_khoa, 26)}</text>
              {ben.map((b, i) => {
                const c = o.get(khoaONhiet(n, b));
                if (!c) return null;
                const t = c.p == null ? 0 : Math.min(1, Math.abs(c.p) / DAM_TOI_DA);
                const dam = (0.2 + 0.7 * t) * (c.cung ? 1 : 0.45);
                const het = c.q.trang_thai === "het";
                const cx = LW + i * CW;
                const tatCa = matHangCuaBen(n, b, { sl, chiCung });
                // p chưa biết: mặt hàng chưa có giá → "?" cam, pop-up mở ở ô giá; thiếu giá KOME → "?" cam, pop-up mở thường.
                const thieuGia = giaTai(c.q, sl).gia == null;
                return (
                  <ONoi key={b} svg nhan={`${n.ten_nhom ?? n.nhom_khoa} · ${b}: ${pcDau(c.p)} so KOME${c.so > 1 ? `, ${c.so} mặt hàng` : ""}`}
                    onBam={() => mo(c.q, thieuGia ? "gia_goc" : undefined)}
                    noi_dung={<>{tatCa.map(q => <NoiGia key={`${q.nguon}${q.id}`} n={n} q={q} sl={sl} gk={gk} />)}</>}>
                    <rect className="dt-dich" x={cx + 2} y={y + 2} width={CW - 4} height={RH - 4} rx={4}
                      fill={MAU[mauLech(c.p)]} fillOpacity={dam}
                      stroke={het ? "var(--canh-chu)" : c.cung ? "none" : "var(--chu-mo)"} strokeWidth={het ? 2 : 1}
                      strokeDasharray={!het && !c.cung ? "3 2" : undefined} />
                    <text x={cx + CW / 2} y={y + 20} fontSize={10.5} textAnchor="middle" pointerEvents="none"
                      style={{ fill: c.p == null ? "var(--dt-cam)" : dam >= 0.6 ? "var(--dt-vach)" : "var(--chu)" }}>
                      {c.cung ? "" : "≈"}{c.p == null ? <tspan fontWeight={700}>?</tspan> : pcDau(c.p)}{c.so > 1 ? ` ·${c.so}` : ""}</text>
                  </ONoi>);
              })}
            </g>);
        })}
      </svg>
    </div>
  );
}

export function ChuGiaiNhiet() {
  return (
    <div className="dt-chu-giai">
      <span><i className="cg-o-do" />đối thủ rẻ hơn KOME</span><span><i className="cg-o-xanh" />KOME rẻ hơn</span>
      <span><i className="cg-nhat" />≈ chỉ có khác thương hiệu</span><span>·n = số mặt hàng của bên</span>
      <span><i className="cg-het" />đang hết</span>
    </div>
  );
}
