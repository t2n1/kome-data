// Cách vẽ A · Cột (đặc tả §4.2, bản phác ca-trang-8.html + goi-thung-3.html + ky-hieu-thay-the.html C): MỘT nhóm =
// một SVG thanh ngang, mỗi thanh một MẶT HÀNG đối thủ, rẻ → đắt, KOME xen vào đúng chỗ. Bốn cột trước thanh:
// Đối thủ · Tên sản phẩm · gói / thùng · tịnh 1 gói. Chọn dòng / thu gọn / % / cờ: so_sanh_logic.ts::dongCot.
import { useState } from "react";
import { HinhMa } from "../chung/HinhMa";
import { ONoi } from "../chung/ONoi";
import { so_luong, yen } from "../dinh_dang";
import type { Nhom, QuanSat } from "./kieu";
import { mauLech } from "./mau";
import { NoiGia, NoiKome } from "./ONoiGia";
import { dongCot, giaKome, NHAN_SL, nhanKlGoi, pcDau, type Dong, type SoLuong } from "./so_sanh_logic";

export type MoSua = (q: QuanSat, tru_o?: string) => void;
type Chung = { sl: SoLuong; gk: string; chiCung: boolean; mo: MoSua };

const W = 960, LW = 440, PHAI = 170, RH = 26, TOP = 18;
const X_TEN = 128, C1 = 350, C2 = 410;           // mép phải cột gói / thùng và tịnh 1 gói
const ngan = (t: string, n: number) => (t.length > n ? t.slice(0, n - 1) + "…" : t);
const nhanDong = (d: Dong) => `${d.ben} · ${d.ten}: ${d.gia == null ? "chưa có giá" : yen(d.gia)}${d.p == null ? "" : `, ${pcDau(d.p)} so KOME`}`;

/** Chữ "?" cam bấm được (ô thiếu dữ liệu) — mở pop-up với con trỏ ở đúng ô. */
function Hoi({ x, y, neo = "end", nhan, bam }: { x: number; y: number; neo?: "end" | "start"; nhan: string; bam: () => void }) {
  return (
    <text x={x} y={y} fontSize={12} textAnchor={neo} className="t-cam t-dam" role="button" tabIndex={0} aria-label={nhan}
      onClick={bam} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); bam(); } }}>?</text>
  );
}

/** Tiêu đề một nhóm: hình + tên + quy cách KOME + mã + "giá đối thủ khi khách mua …". */
export function DauNhom({ n, sl, neo }: { n: Nhom; sl: SoLuong; neo?: (e: HTMLElement | null) => void }) {
  const ten = n.ten_nhom ?? n.nhom_khoa;
  const qc = [n.kome_kg_goi != null && n.kome_goi_thung != null ? `${nhanKlGoi(n.kome_kg_goi * 1000)} × ${so_luong(n.kome_goi_thung)}` : null,
    n.kome_kg_thung != null ? `${so_luong(n.kome_kg_thung, 1)} kg/thùng` : null].filter(Boolean).join(" · ") || "quy cách ?";
  return (
    <h3 className="dt-nhom-dau" ref={neo}>
      <HinhMa ma={n.ma_kome?.[0]} ten={ten} co={30} trang_tri />
      {ten}
      <small>{qc} · {(n.ma_kome ?? []).join(", ") || n.nhom_khoa} · giá đối thủ khi khách mua <b>{NHAN_SL[sl]}</b></small>
    </h3>
  );
}

export function BieuDoCot({ n, sl, gk, chiCung, mo, neo }: Chung & { n: Nhom; neo?: (e: HTMLElement | null) => void }) {
  const [moRong, datMoRong] = useState(false);
  const { dong, an } = dongCot(n, { sl, gk, chiCung, moRong });
  const gK = giaKome(n, gk);
  // Dải bảng giá KOME = 売価No. thường (bỏ No.10 khuyến mãi — §5.3); vạch trắng = thực bán khi giá đang chọn không phải nó.
  const dai = Object.entries(n.gia_kome_bang ?? {}).filter(([m]) => m !== "10").map(([, g]) => g);
  const thuc = gk !== "thuc" ? n.gia_kome : null;
  const mx = Math.max(1, ...dong.flatMap(d => [d.gia ?? 0, d.giaLe ?? 0]), ...dai, thuc ?? 0, n.gia_kome_km ?? 0) * 1.1;
  const x = (v: number) => LW + Math.max(0, v) / mx * (W - LW - PHAI);
  const H = TOP + dong.length * RH + 14;
  return (
    <div className="dt-nhom-cot">
      <DauNhom n={n} sl={sl} neo={neo} />
      <div className="dt-cuon">
        <svg viewBox={`0 0 ${W} ${H}`} className="dt-svg dt-svg-cot" role="group" aria-label={`Giá đối thủ — ${n.ten_nhom ?? n.nhom_khoa}`}>
          <line className="ke" x1={120} x2={120} y1={2} y2={H - 6} />
          <line className="ke" x1={C1 - 44} x2={C1 - 44} y1={2} y2={H - 6} />
          <line className="ke" x1={C2 + 8} x2={C2 + 8} y1={2} y2={H - 6} />
          <text x={4} y={11} fontSize={10} className="t-nhat">Đối thủ</text>
          <text x={X_TEN} y={11} fontSize={10} className="t-nhat">Tên sản phẩm</text>
          <text x={C1} y={11} fontSize={10} className="t-nhat" textAnchor="end">gói / thùng</text>
          <text x={C2} y={11} fontSize={10} className="t-nhat" textAnchor="end">tịnh 1 gói</text>
          {dong.map((d, i) => {
            const y = 6 + TOP + i * RH, q = d.q;
            const re = d.gia != null && d.giaLe != null && d.gia < d.giaLe;
            const lopTen = d.kome ? "t-kome" : d.cung ? "t-dam" : "t-mo";
            const soGoi = d.soGoi == null ? null : so_luong(d.soGoi), kl = nhanKlGoi(d.klGoi);
            const cuoi = d.gia == null ? LW : x(Math.max(d.gia, re ? d.giaLe! : 0));
            return (
              <g key={d.kome ? "kome" : `${q!.nguon}${q!.id}`}>
                <text x={4} y={y + 16} fontSize={11.5} className={lopTen}>{d.kome ? "KOME" : ngan(d.ben, 18)}</text>
                <text x={X_TEN} y={y + 16} fontSize={11.5} className={d.kome ? "t-kome" : d.cung ? "" : "t-mo"}>
                  {ngan(d.kome ? n.ten_nhom ?? n.nhom_khoa : d.ten, 28)}</text>
                {soGoi != null ? <text x={C1} y={y + 16} fontSize={12} textAnchor="end">{soGoi}</text>
                  : d.kome ? <text x={C1} y={y + 16} fontSize={12} textAnchor="end" className="t-mo">?</text>
                  : <Hoi x={C1} y={y + 16} nhan={`${d.ben} · ${d.ten}: thiếu số gói / thùng — điền`} bam={() => mo(q!, "so_goi_thung")} />}
                {kl != null ? <text x={C2} y={y + 16} fontSize={12} textAnchor="end">{kl}</text>
                  : d.kome ? <text x={C2} y={y + 16} fontSize={12} textAnchor="end" className="t-mo">?</text>
                  : <Hoi x={C2} y={y + 16} nhan={`${d.ben} · ${d.ten}: thiếu tịnh 1 gói — điền`} bam={() => mo(q!, "kl_goi_g")} />}
                {d.kome && dai.length > 0 && (
                  <rect x={x(Math.min(...dai))} y={y + 1} width={Math.max(2, x(Math.max(...dai)) - x(Math.min(...dai)))} height={21} rx={3}
                    fill="var(--do)" fillOpacity={0.16} />)}
                {re && <rect x={LW} y={y + 4} width={x(d.giaLe!) - LW} height={15} rx={3} fill="none" stroke="var(--chu-mo)" strokeDasharray="3 2" />}
                {d.kome
                  ? <ONoi svg nhan={`KOME: ${yen(gK)}`} noi_dung={<NoiKome n={n} gk={gk} />}>
                      {gK != null ? <rect className="dt-dich" x={LW} y={y + 4} width={Math.max(2, x(gK) - LW)} height={15} rx={3} fill="var(--do)" />
                        : <text x={LW + 2} y={y + 16} fontSize={12} className="t-mo">?</text>}
                    </ONoi>
                  : d.gia == null
                    ? <ONoi svg nhan={`${nhanDong(d)} — điền giá`} onBam={() => mo(q!, "gia_goc")} noi_dung={<NoiGia n={n} q={q!} sl={sl} gk={gk} />}>
                        <text x={LW + 2} y={y + 16} fontSize={12} className="t-cam t-dam">?</text>
                      </ONoi>
                    : <ONoi svg nhan={nhanDong(d)} onBam={() => mo(q!)} noi_dung={<NoiGia n={n} q={q!} sl={sl} gk={gk} />}>
                        <rect className="dt-dich" x={LW} y={y + 4} width={Math.max(2, x(d.gia) - LW)} height={15} rx={3}
                          fill={d.cung ? "var(--lam-chu)" : "var(--dt-khac)"} opacity={d.cu ? 0.4 : 1}
                          stroke={d.het ? "var(--canh-chu)" : undefined} strokeWidth={d.het ? 2 : undefined} />
                      </ONoi>}
                {d.kome && thuc != null && (
                  <g aria-hidden="true" pointerEvents="none">
                    <line x1={x(thuc)} x2={x(thuc)} y1={y + 1} y2={y + 22} stroke="var(--chu)" strokeOpacity={0.45} strokeWidth={4} />
                    <line x1={x(thuc)} x2={x(thuc)} y1={y + 1} y2={y + 22} stroke="var(--dt-vach)" strokeWidth={2} />
                  </g>)}
                {!d.kome && d.gia != null && d.thueKhongRo && (
                  <g className="dt-hoi-thue" role="button" tabIndex={0} aria-label={`${d.ben} · ${d.ten}: thuế không rõ — sửa`}
                    onClick={() => mo(q!, "thue")} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); mo(q!, "thue"); } }}>
                    <circle cx={Math.max(LW + 8, x(d.gia) - 8)} cy={y + 11.5} r={6} />
                    <text x={Math.max(LW + 8, x(d.gia) - 8)} y={y + 15.5} fontSize={10} textAnchor="middle">?</text>
                  </g>)}
                <text x={cuoi + 6} y={y + 16} fontSize={11.5} opacity={d.cu ? 0.5 : 1}>
                  {d.kome
                    ? <>{gK == null ? "" : yen(gK)}{n.gia_kome_km != null && <tspan className="t-km t-dam"> KM {yen(n.gia_kome_km)}</tspan>}</>
                    : d.gia == null ? null
                    : <>{yen(d.gia)} <tspan className={"t-dam t-" + mauLech(d.p)}>{pcDau(d.p)}</tspan>
                      {re && <tspan className="t-nhat"> ↓ từ {yen(d.giaLe)}</tspan>}
                      {d.het && <tspan className="t-vang"> hết</tspan>}
                      {d.km && <tspan className="t-km"> KM</tspan>}
                      {d.gomShip && <tspan> 🚚</tspan>}</>}
                </text>
              </g>);
          })}
        </svg>
      </div>
      {an > 0 ? <button type="button" className="dt-xem-them" onClick={() => datMoRong(true)}>xem thêm {an} mặt hàng ▾</button>
        : moRong ? <button type="button" className="dt-xem-them" onClick={() => datMoRong(false)}>thu gọn ▴</button> : null}
    </div>
  );
}

/** Chú giải dưới biểu đồ cột. */
export function ChuGiaiCot() {
  return (
    <div className="dt-chu-giai">
      <span><i className="cg-kome" />KOME</span><span><i className="cg-cung" />cùng thương hiệu</span>
      <span><i className="cg-khac" />khác thương hiệu</span><span><i className="cg-dai" />dải bảng giá KOME</span>
      <span><i className="cg-le" />giá mua 1 thùng</span><span><i className="cg-het" />đang hết</span>
      <span><b className="cg-vang">?</b>thuế</span><span><b className="cg-cam">?</b>thiếu — bấm để điền</span>
      <span className="cg-mo">mờ = cũ</span><span>🚚 gồm ship</span>
    </div>
  );
}
