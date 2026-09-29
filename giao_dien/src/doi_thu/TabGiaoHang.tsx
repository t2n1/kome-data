// Tab "Phí & giao hàng" (đặc tả giao diện mới §4.5, bản phác ca-trang-8.html): đơn mẫu (tiền · số thùng · vùng · trả) ·
// "Khách phải trả thêm bao nhiêu cho đơn này" (thanh ghép ship / vùng / daibiki mỗi bên, phi_giao.ts::tinh) · bảng điều kiện.
// Mọi ô bấm được → SuaGiaoHang. Gom / xếp / chữ ô: giao_hang_logic.ts. `useGiaoHang` dùng chung với "Tính cả phí giao".
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type KeyboardEvent } from "react";
import { lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { ONoi } from "../chung/ONoi";
import { ngay, so, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import { chuanGiao, DON_THUNG, DON_TIEN, DON_VUNG, oBang, TEN_VUNG, thanhPhi, truOPhan, type ThanhPhi } from "./giao_hang_logic";
import { giaoTrong } from "./ho_so_logic";
import type { GiaoHang, TongQuan } from "./kieu";
import { mauLech } from "./mau";
import type { DonMau } from "./phi_giao";
import { SuaGiaoHang } from "./SuaNho";

export type BangChung = { so_don_ship: number | null; don_ship_lon_nhat: number | null; so_don_dai_330: number | null;
  so_don_dai_300: number | null };
export type GiaoHangApi = { dong: GiaoHang[]; bang_chung: BangChung | null };

const soHoac = (v: unknown) => (v == null || v === "" || !Number.isFinite(Number(v)) ? null : Number(v));

/** GET /api/doi-thu/giao-hang — MỘT khoá truy vấn cho tab này và "Tính cả phí giao" của So sánh. Số đổi Number() ở đây. */
export function useGiaoHang(bat = true) {
  const kx = chuoiKhoang(useKhoang());
  return useQuery({ queryKey: ["doi-thu", "giao-hang", kx], enabled: bat,
    queryFn: () => lay<GiaoHangApi>(`/api/doi-thu/giao-hang${kx ? "?" + kx : ""}`).then((d): GiaoHangApi => ({
      dong: (d.dong ?? []).map(chuanGiao),
      bang_chung: d.bang_chung && {
        so_don_ship: soHoac(d.bang_chung.so_don_ship), don_ship_lon_nhat: soHoac(d.bang_chung.don_ship_lon_nhat),
        so_don_dai_330: soHoac(d.bang_chung.so_don_dai_330), so_don_dai_300: soHoac(d.bang_chung.so_don_dai_300) },
    })) });
}

/** Câu bằng chứng của dòng KOME (mart.giao_hang_kome_bang_chung). */
export function cauBangChung(b: BangChung | null) {
  if (!b) return null;
  return `Suy từ phiếu bán 180 ngày: 配送料 trên ${so(b.so_don_ship)} đơn (đơn lớn nhất ${yen(b.don_ship_lon_nhat)}) · `
    + `代引 ¥330 trên ${so(b.so_don_dai_330)} đơn · ¥300 trên ${so(b.so_don_dai_300)} đơn`;
}

const phim = (f: () => void) => (e: KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); f(); } };
const tenCua = (g: GiaoHang) => g.ten ?? g.ma_doi_thu;
const CACH_TINH = <>
  Ngoài tiền hàng, khách trả thêm: phí ship (khi đơn chưa tới ngưỡng miễn; theo đơn, thùng hoặc kiện) + phụ phí vùng (mỗi
  kiện; kiện = số thùng ÷ thùng/kiện, không biết thì 1 kiện) + phí daibiki (chỉ khi trả daibiki; từ ngưỡng thì dùng phí sau
  ngưỡng). "Bao ship" = phí đã nằm trong giá hàng — tab So sánh đã so giá đó. Phần bên đó không ghi là ô "?" và không cộng.
  Đỏ = khách trả ở bên đó ít hơn ở KOME quá 5% (tính trên tiền hàng + phí), xanh = nhiều hơn, xám = ngang. Dòng KOME suy từ
  phiếu bán cho tới khi có người xác nhận.</>;

export function TabGiaoHang() {
  const kx = chuoiKhoang(useKhoang());
  const q = useGiaoHang();
  const tq = useQuery({ queryKey: ["doi-thu", "tong-quan", kx],
    queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const [don, datDon] = useState<DonMau>({ tien: 15000, thung: 1, vung: "kanto", tra: "daibiki" });
  const [sua, datSua] = useState<{ g: GiaoHang; tru_o?: string } | null>(null);
  // Bên đang theo dõi mà chưa có dòng giao hàng nào → một dòng toàn "?" (bấm để điền), không bỏ sót.
  const ds = useMemo(() => {
    const co = q.data?.dong ?? [];
    const da = new Set(co.map(g => g.ma_doi_thu));
    return [...co, ...(tq.data?.ben ?? []).filter(b => !da.has(b.ma)).map(b => giaoTrong(b.ma, b.ten))];
  }, [q.data, tq.data]);
  const K = ds.find(g => g.ma_doi_thu === "KOME");
  const bc = q.data?.bang_chung ?? null;
  const mo = (g: GiaoHang, tru_o?: string) => datSua({ g, tru_o });
  const loi = q.error ? (q.error as Error).message : null;

  return (
    <div className="dt-phi">
      <div className="dt-dk dt-phi-dk">
        <span className="dt-dk-nhom" role="group" aria-label="Đơn của khách">
          <span className="dt-dk-nhan">Đơn của khách:</span>
          {DON_TIEN.map(t => <button key={t} type="button" className="chip" aria-pressed={don.tien === t}
            onClick={() => datDon({ ...don, tien: t })}>{yen(t)}</button>)}
        </span>
        <span className="dt-dk-nhom" role="group" aria-label="Số thùng">
          <span className="dt-dk-nhan">Số thùng:</span>
          {DON_THUNG.map(t => <button key={t} type="button" className="chip" aria-pressed={don.thung === t}
            onClick={() => datDon({ ...don, thung: t })}>{t}</button>)}
        </span>
        <span className="dt-dk-nhom" role="group" aria-label="Giao tới">
          <span className="dt-dk-nhan">Giao tới:</span>
          {DON_VUNG.map(([v, n]) => <button key={v} type="button" className="chip" aria-pressed={don.vung === v}
            onClick={() => datDon({ ...don, vung: v })}>{n}</button>)}
        </span>
        <span className="dt-dk-nhom" role="group" aria-label="Trả tiền">
          <span className="dt-dk-nhan">Trả tiền:</span>
          {([["daibiki", "Daibiki"], ["ck", "Chuyển khoản"]] as const).map(([m, n]) => (
            <button key={m} type="button" className="chip" aria-pressed={don.tra === m} onClick={() => datDon({ ...don, tra: m })}>{n}</button>))}
        </span>
      </div>

      <section className="dt-khoi">
        <Khoi tieu_de="Khách phải trả thêm bao nhiêu cho đơn này" dang_tai={q.isLoading} loi={loi} cach_tinh={CACH_TINH}>
          {q.data && <BieuDoPhi ds={ds} don={don} bc={bc} mo={mo} />}
          <div className="dt-chu-giai">
            <span><i className="cg-ship" />ship</span><span><i className="cg-vung" />phụ phí vùng</span>
            <span><i className="cg-dai-phi" />daibiki</span><span><i className="cg-le" /><b className="cg-cam">?</b>bên đó không ghi — bấm để điền</span>
            <span><i className="cg-kome-vien" />KOME</span>
          </div>
        </Khoi>
      </section>

      <section className="dt-khoi">
        <Khoi tieu_de="Điều kiện giao hàng từng bên" dang_tai={q.isLoading} loi={loi}
          cach_tinh={<>Mỗi ô bấm được để sửa. "?" cam = chưa ai điền; "?" vàng = bảng giá không nói giá đã gồm thuế hay chưa.
            Miễn ship từ: đỏ = bên đó miễn ship ở mức thấp hơn KOME, xanh = cao hơn.</>}>
          {q.data && <BangDieuKien ds={ds} K={K} bc={bc} mo={mo} />}
        </Khoi>
      </section>
      {sua && <SuaGiaoHang key={`${sua.g.ma_doi_thu}:${sua.tru_o ?? ""}`} dong={sua.g} tru_o={sua.tru_o}
        dong_lai={() => datSua(null)} xong={() => datSua(null)} />}
    </div>
  );
}

const W = 860, LW = 160, RH = 26, CHU = 290;

function BieuDoPhi({ ds, don, bc, mo }: { ds: GiaoHang[]; don: DonMau; bc: BangChung | null; mo: (g: GiaoHang, tru_o?: string) => void }) {
  const hang = thanhPhi(ds, don);
  const mx = Math.max(1500, ...hang.map(x => x.tong));
  const w = (v: number) => v / mx * (W - LW - CHU);
  const H = hang.length * RH + 8;
  const vung = TEN_VUNG[don.vung] ?? don.vung;
  return (
    <div className="dt-cuon">
      <svg viewBox={`0 0 ${W} ${H}`} className="dt-svg dt-svg-phi" role="group" aria-label="Phí khách trả thêm cho đơn mẫu, mỗi bên">
        {hang.map((t, i) => {
          const y = 4 + i * RH, ten = tenCua(t.g);
          const phan: [number, string, string][] = [[t.r.ship, "var(--dt-cam)", "ship"], [t.r.vung, "var(--dt-vung)", `phụ phí ${vung}`],
            [t.r.daibiki, "var(--dt-dai)", "daibiki"]];
          let cx = LW;
          // Không giao tới vùng đó: không có đơn nào để tính — không vẽ phần phí.
          const seg = phan.filter(([v]) => v > 0 && !t.r.khong_nhan).map(([v, m, n]) => {
            const r = <rect key={n} className="dt-dich" x={cx} y={y + 4} width={Math.max(2, w(v))} height={15} fill={m} />;
            cx += Math.max(2, w(v));
            return r;
          });
          const cuoiThanh = cx;
          const hoiX = (j: number) => cuoiThanh + 4 + j * 26;
          const chuX = hoiX(t.r.khong_nhan ? 0 : t.r.chua_ro.length) + 2;
          return (
            <g key={t.g.ma_doi_thu}>
              <ONoi svg nhan={`${ten}: ${nhanThanh(t, vung)} — sửa điều kiện`} onBam={() => mo(t.g)}
                noi_dung={<NoiPhi t={t} bc={bc} vung={vung} />}>
                <rect x={0} y={y + 1} width={Math.max(LW + 4, cuoiThanh + 4)} height={RH - 3} fill="transparent" />
                <text x={LW - 8} y={y + 16} fontSize={12} textAnchor="end" className={t.kome ? "t-kome" : ""}>{ngan(ten, 22)}</text>
                {t.kome && <rect x={LW - 2} y={y + 2} width={Math.max(4, cuoiThanh - LW) + 4} height={19} rx={3} fill="none"
                  stroke="var(--do)" strokeWidth={1.5} />}
                {seg}
              </ONoi>
              {!t.r.khong_nhan && t.r.chua_ro.map((p, j) => (
                <g key={p} role="button" tabIndex={0} className="dt-phi-hoi" aria-label={`${ten}: chưa rõ ${p} — điền`}
                  onClick={() => mo(t.g, truOPhan(p, t.g, don))} onKeyDown={phim(() => mo(t.g, truOPhan(p, t.g, don)))}>
                  <rect x={hoiX(j)} y={y + 4} width={22} height={15} rx={3} fill="none" stroke="var(--chu-mo)" strokeDasharray="3 2" />
                  <text x={hoiX(j) + 11} y={y + 15.5} fontSize={10.5} textAnchor="middle" className="t-cam t-dam">?</text>
                </g>))}
              <text x={chuX + 4} y={y + 16} fontSize={11.5}>
                {t.r.khong_nhan ? <tspan className="t-do t-dam">không giao {vung}</tspan> : <>
                  {t.tong > 0 || !t.r.chua_ro.length ? yen(t.tong) : ""}
                  {t.g.bao_ship && <tspan className="t-nhat"> bao ship</tspan>}
                  {t.r.chua_ro.length > 0 && <tspan className="t-nhat"> chưa rõ {t.r.chua_ro.join(", ")}</tspan>}
                  {t.lech != null && <tspan className={"t-dam t-" + mauLech(t.p)}>
                    {"  "}{t.lech < 0 ? `rẻ hơn KOME ${yen(-t.lech)}` : t.lech > 0 ? `đắt hơn KOME ${yen(t.lech)}` : "bằng KOME"}</tspan>}
                </>}
              </text>
            </g>);
        })}
      </svg>
    </div>
  );
}

const ngan = (t: string, n: number) => (t.length > n ? t.slice(0, n - 1) + "…" : t);
function nhanThanh(t: ThanhPhi, vung: string) {
  if (t.r.khong_nhan) return `không giao ${vung}`;
  return `${yen(t.tong)}${t.r.chua_ro.length ? `, chưa rõ ${t.r.chua_ro.join(", ")}` : ""}`
    + (t.lech == null ? "" : t.lech < 0 ? `, rẻ hơn KOME ${yen(-t.lech)}` : t.lech > 0 ? `, đắt hơn KOME ${yen(t.lech)}` : ", bằng KOME");
}

/** Ô nổi một thanh: từng phần + câu gốc (`nguon_chu`); dòng KOME in bằng chứng suy từ phiếu bán. */
function NoiPhi({ t, bc, vung }: { t: ThanhPhi; bc: BangChung | null; vung: string }) {
  const g = t.g;
  return (
    <div className="dt-ng">
      <p className="dt-ng-ben">{tenCua(g)}</p>
      <table><tbody>
        <tr><td>ship</td><td className="r">{t.r.chua_ro.includes("ship") ? "?" : g.bao_ship ? "bao ship" : yen(t.r.ship)}</td></tr>
        <tr><td>phụ phí {vung}</td><td className="r">{t.r.khong_nhan ? "không nhận" : t.r.chua_ro.includes("vùng") ? "?" : yen(t.r.vung)}</td></tr>
        <tr><td>daibiki</td><td className="r">{t.r.chua_ro.includes("daibiki") ? "?" : yen(t.r.daibiki)}</td></tr>
      </tbody></table>
      {g.nguon_chu && <p className="dt-ng-chu">Gốc: “{g.nguon_chu}”{g.ngay_nguon ? ` · ${ngay(g.ngay_nguon)}` : ""}</p>}
      {t.kome && g.suy && <p className="dt-ng-chu vang">{cauBangChung(bc) ?? "Suy từ phiếu bán"} — cần xác nhận</p>}
      {!g.nguon_chu && !t.kome && <p className="dt-ng-chu">Chưa có điều kiện giao hàng từ bảng giá của bên này</p>}
    </div>
  );
}

const COT = ["Phí ship", "Miễn ship từ", "Phụ phí vùng", "Phí daibiki", "Ghép kiện", "Kiện tối đa", "Giá gồm thuế"];

function BangDieuKien({ ds, K, bc, mo }: { ds: GiaoHang[]; K: GiaoHang | undefined; bc: BangChung | null;
  mo: (g: GiaoHang, tru_o?: string) => void }) {
  return (
    <div className="dt-cuon">
      <table className="bang dt-bang dt-bang-giao">
        <thead><tr><th>Bên</th>{COT.map(c => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{ds.map(g => {
          const kome = g.ma_doi_thu === "KOME", ten = tenCua(g);
          return (
            <tr key={g.ma_doi_thu} className={kome ? "kome" : undefined}>
              <td>
                <ONoi nhan={`${ten} — sửa điều kiện giao hàng`} onBam={() => mo(g)} className="dt-giao-ben"
                  noi_dung={<div className="o-noi-chu">{kome && g.suy ? `${cauBangChung(bc) ?? "Suy từ phiếu bán"} — cần xác nhận`
                    : g.nguon_chu ? `Gốc: “${g.nguon_chu}”` : "Chưa có câu gốc"}</div>}>
                  {ten}{kome && g.suy && <small className="dt-nhat"> (suy từ phiếu bán — cần xác nhận)</small>}
                </ONoi>
              </td>
              {oBang(g, K).map((o, i) => (
                <td key={i}>
                  <button type="button" aria-label={`${ten} · ${COT[i]}: ${o.chu ?? (o.vang ? "bảng không nói" : "chưa ai điền")} — sửa`}
                    className={"dt-giao-o" + (o.chu == null ? (o.vang ? " vang" : " cam") : "") + (o.mau ? " c-" + o.mau : "") + (o.nhat ? " dt-nhat" : "")}
                    onClick={() => mo(g, o.k)}>{o.chu ?? "?"}</button>
                </td>))}
            </tr>);
        })}</tbody>
      </table>
    </div>
  );
}

