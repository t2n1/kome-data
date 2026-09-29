// Tab "Tóm tắt" (đợt 4b task 7; bản phác đã duyệt ca-trang-8.html tab Tóm tắt): ô tìm · 4 ô số · "KOME đứng đâu" (beeswarm) ·
// đắt nhất / rẻ nhất · cơ hội đối thủ đang hết · ai bán ngành nào (bóng) · khuyến mãi theo bên. Mọi luật ở tom_tat_logic.ts;
// ở đây chỉ vẽ + nối. Hai query dùng CHUNG key với tab So sánh (["doi-thu","so-sanh",kx]) nên đổi tab không tải lại.
import { useQuery } from "@tanstack/react-query";
import { Fragment, useId, useMemo, useState } from "react";
import { lay } from "../api";
import { HinhMa } from "../chung/HinhMa";
import { Khoi } from "../chung/Khoi";
import { DongNoi, ONoi } from "../chung/ONoi";
import { so, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { Nhom, TongQuan } from "./kieu";
import { pcDau } from "./so_sanh_logic";
import { SuaMatHang } from "./SuaMatHang";
import { bongNganh, coHoi, datNhat, diemVitri, goiY, kmNoiBat, kmTheoBen, mauTT, nganhObc, nhomCuaO, P_CAO, P_THAP, reNhat, SO_COT,
  tiLe, tongSo, type GoiY } from "./tom_tat_logic";

type MoSoSanh = (o: { sp?: string[]; nganh?: string; ben?: string }) => void;
type Props = { moSoSanh: MoSoSanh; moBen: (ma: string) => void; moLech: () => void; moTin: () => void };
type Sua = { nguon: "nap" | "tay"; id: number };

const MAU: Record<string, string> = { do: "var(--do)", xanh: "var(--ok-vien)", xam: "var(--chu-mo)" };
const pTT = (n: Nhom) => (n.lech_trung_vi == null ? null : Math.round(n.lech_trung_vi * 100));
const tenNhom = (n: Nhom) => n.ten_nhom ?? n.nhom_khoa;
const khoa = (ds: Nhom[]) => [...new Set(ds.map(n => n.nhom_khoa))];

export function TabTomTat({ moSoSanh, moBen, moLech, moTin }: Props) {
  const kx = chuoiKhoang(useKhoang());
  const qTq = useQuery({ queryKey: ["doi-thu", "tong-quan", kx],
    queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const qSs = useQuery({ queryKey: ["doi-thu", "so-sanh", kx],
    queryFn: () => lay<{ nhom: Nhom[] }>(`/api/doi-thu/so-sanh${kx ? "?" + kx : ""}`) });
  const tq = qTq.data, ss = qSs.data?.nhom;
  const [sua, datSua] = useState<Sua | null>(null);
  const tenBen = useMemo(() => new Map((tq?.ben ?? []).map(b => [b.ma, b.ten])), [tq]);
  const loiTq = qTq.error ? (qTq.error as Error).message : null, loiSs = qSs.error ? (qSs.error as Error).message : null;
  const moSua = (x: { nguon: string; id: number }) => datSua({ nguon: x.nguon as Sua["nguon"], id: x.id });

  const ts = tq && ss ? tongSo(ss, tq) : null;
  const dat = useMemo(() => datNhat(ss ?? []), [ss]), re = useMemo(() => reNhat(ss ?? []), [ss]);
  const ch = useMemo(() => (tq ? coHoi(tq) : []), [tq]);
  const nhomTheoMa = useMemo(() => {
    const m = new Map<string, string>();
    for (const n of ss ?? []) for (const ma of n.ma_kome ?? []) if (!m.has(ma)) m.set(ma, n.nhom_khoa);
    return m;
  }, [ss]);

  return (
    <div className="dt-tt">
      <TimNhanh ss={ss ?? []} tq={tq} chon={g => (g.loai === "ben" ? moBen(g.khoa) : moSoSanh({ sp: [g.khoa] }))} />

      <div className="dt-tt-o4">
        <div className="dt-tt-o"><small>Nhóm có giá KOME để so</small><b>{ts ? so(ts.coGia) : "…"}</b>
          {ss && <em>/ {so(ss.length)} nhóm</em>}</div>
        <div className="dt-tt-o"><small>KOME đắt hơn thị trường &gt; 5%</small><b className="c-do">{ts ? so(ts.datHon) : "…"}</b></div>
        <div className="dt-tt-o"><small>Mã KOME mà đối thủ đang hết</small><b className="c-vang">{ts ? so(ts.maHet) : "…"}</b></div>
        <div className="dt-tt-o"><small>Khuyến mãi đang chạy</small><b className="c-km">{ts ? so(ts.km) : "…"}</b>
          {ts && <em>{so(ts.soBenKm)} bên</em>}</div>
      </div>

      <section className="dt-khoi">
        <Khoi tieu_de="KOME đứng đâu so với thị trường" dang_tai={qSs.isLoading} loi={loiSs}
          phu={<button type="button" className="dt-tt-xem" onClick={() => moSoSanh({})}>xem tất cả →</button>}
          cach_tinh="Mỗi chấm = một nhóm hàng so theo kg; vị trí = giá KOME (標準価格, thiếu thì thực bán 90 ngày) lệch bao nhiêu so với trung vị giá lẻ của đối thủ (¥/kg chưa thuế). Đỏ = KOME đắt hơn quá 5%, xanh = rẻ hơn quá 5%, xám = ngang. Ngoài −60% / +70% vẽ ở mép. Nhóm có giá KOME lệch hơn 3× trung vị không vẽ.">
          {ss && <ViTri ss={ss} moNhom={k => moSoSanh({ sp: [k] })} moLech={moLech} />}
        </Khoi>
      </section>

      <div className="dt-tt-hai">
        <section className="dt-khoi">
          <Khoi tieu_de="KOME đắt nhất so với thị trường" dang_tai={qSs.isLoading} loi={loiSs}
            phu={<button type="button" className="dt-tt-xem" onClick={() => moSoSanh({ sp: khoa(datNhat(ss ?? [], 8)) })}>xem tất cả →</button>}
            cach_tinh="Thanh = giá thấp nhất → cao nhất của đối thủ · vạch = trung vị · chấm = KOME. % = giá KOME so với trung vị.">
            <DaiGia ds={dat} tenBen={tenBen} mo={k => moSoSanh({ sp: [k] })} />
          </Khoi>
        </section>
        <section className="dt-khoi">
          <Khoi tieu_de="KOME rẻ nhất so với thị trường" dang_tai={qSs.isLoading} loi={loiSs}
            phu={<button type="button" className="dt-tt-xem" onClick={() => moSoSanh({ sp: khoa(reNhat(ss ?? [], 8)) })}>xem tất cả →</button>}
            cach_tinh="Thanh = giá thấp nhất → cao nhất của đối thủ · vạch = trung vị · chấm = KOME. % = giá KOME so với trung vị.">
            <DaiGia ds={re} tenBen={tenBen} mo={k => moSoSanh({ sp: [k] })} />
          </Khoi>
        </section>
      </div>

      <section className="dt-khoi">
        <Khoi tieu_de="Cơ hội — đối thủ đang hết hàng KOME có" dang_tai={qTq.isLoading} loi={loiTq}
          phu={<button type="button" className="dt-tt-xem" onClick={moTin}>xem tất cả →</button>}
          cach_tinh="Theo bảng giá mới nhất của từng bên: mặt hàng ghép được với mã KOME mà bên đó ghi hết hàng. Xếp theo số bên đang hết. Bấm tên bên để sửa dòng đó.">
          {ch.length === 0 ? <p className="dt-nhat">Không bên nào đang hết hàng KOME có.</p> : (
            <div className="dt-tt-chs">{ch.map(c => {
              const k = nhomTheoMa.get(c.ma_kome);
              return (
                <div key={c.ma_kome} className="dt-tt-ch">
                  <HinhMa ma={c.ma_kome} ten={c.ten} co={64} trang_tri />
                  {k ? <button type="button" className="dt-tt-ten" onClick={() => moSoSanh({ sp: [k] })}>{c.ten}</button>
                    : <b className="dt-tt-ten">{c.ten}</b>}
                  <small>{c.ma_kome} · <span className="c-vang">{so(c.ben.length)} bên đang hết</span></small>
                  <div>{c.ben.map(b => (
                    <button key={b.ma} type="button" className="dt-tt-chip" aria-label={`Sửa: ${b.ten} đang hết ${c.ten}`}
                      onClick={() => moSua(b)}>{b.ten}</button>))}</div>
                </div>);
            })}</div>)}
        </Khoi>
      </section>

      <div className="dt-tt-hai">
        <section className="dt-khoi">
          <Khoi tieu_de="Ai bán ngành nào" dang_tai={qTq.isLoading} loi={loiTq}
            cach_tinh="Bóng càng to = đối thủ càng nhiều mặt hàng ghép được với mã KOME ở ngành đó (bán kính theo căn bậc hai số mặt hàng). Bấm bóng mở So sánh giá lọc ngành + bên đó; bấm tên bên mở hồ sơ bên.">
            {tq && <Bong tq={tq} ss={ss ?? []} moSoSanh={moSoSanh} moBen={moBen} />}
          </Khoi>
        </section>
        <section className="dt-khoi">
          <Khoi tieu_de="Khuyến mãi đang chạy" dang_tai={qTq.isLoading} loi={loiTq}
            phu={<button type="button" className="dt-tt-xem" onClick={moTin}>xem tất cả →</button>}
            cach_tinh="Số dòng có khuyến mãi (ghi chú khuyến mãi hoặc giá trước KM) trong bảng giá hiện hành, theo bên — 8 bên nhiều nhất; bốn thẻ = giảm giá nhiều nhất theo %. Bấm thẻ để sửa.">
            {tq && <KhuyenMai tq={tq} tenBen={tenBen} moBen={moBen} moSua={moSua} />}
          </Khoi>
        </section>
      </div>

      {sua && <SuaMatHang nguon={sua.nguon} id={sua.id} dong={() => datSua(null)} xong={() => datSua(null)} />}
    </div>
  );
}

// ---------------------------------------------------------------- ô tìm

function TimNhanh({ ss, tq, chon }: { ss: Nhom[]; tq: TongQuan | undefined; chon: (g: GoiY) => void }) {
  const [tim, datTim] = useState("");
  const [mo, datMo] = useState(false);
  const [i, datI] = useState(0);
  const id = useId();
  const ds = useMemo(() => goiY(ss, tq?.ben ?? [], tim), [ss, tq, tim]);
  const hien = mo && ds.length > 0;
  const chot = (g: GoiY | undefined) => { if (!g) return; datMo(false); datTim(""); chon(g); };
  return (
    <div className="dt-tt-tim">
      <input type="search" role="combobox" aria-expanded={hien} aria-controls={`${id}-ds`} aria-autocomplete="list"
        aria-activedescendant={hien ? `${id}-${i}` : undefined} aria-label="Tìm mặt hàng KOME hoặc đối thủ"
        placeholder="🔍 Tìm mặt hàng KOME hoặc đối thủ…" value={tim}
        onChange={e => { datTim(e.target.value); datMo(true); datI(0); }} onFocus={() => datMo(true)} onBlur={() => datMo(false)}
        onKeyDown={e => {
          if (e.key === "ArrowDown") { e.preventDefault(); datMo(true); datI(x => (ds.length ? (x + 1) % ds.length : 0)); }
          else if (e.key === "ArrowUp") { e.preventDefault(); datI(x => (ds.length ? (x - 1 + ds.length) % ds.length : 0)); }
          else if (e.key === "Enter") { e.preventDefault(); chot(ds[i] ?? ds[0]); }
          else if (e.key === "Escape") datMo(false);
        }} />
      {hien && (
        <ul id={`${id}-ds`} role="listbox" className="dt-tt-goi-y" aria-label="Gợi ý">
          {ds.map((g, j) => (
            <li key={g.loai + g.khoa} id={`${id}-${j}`} role="option" aria-selected={j === i}
              onMouseDown={e => e.preventDefault()} onClick={() => chot(g)} onMouseEnter={() => datI(j)}>
              <span className="dt-tt-loai">{g.loai === "ben" ? "Đối thủ" : "Nhóm"}</span>
              <b>{g.ten}</b>{g.phu && <small>{g.phu}</small>}
            </li>))}
        </ul>)}
    </div>
  );
}

// ---------------------------------------------------------------- KOME đứng đâu (beeswarm)

const VW = 1100, X0 = 30, X1 = 1080, BUOC = 9, TREN = 28;
const xP = (p: number) => X0 + (p - P_THAP) / (P_CAO - P_THAP) * (X1 - X0);
const xCot = (c: number) => X0 + c / SO_COT * (X1 - X0);

function ViTri({ ss, moNhom, moLech }: { ss: Nhom[]; moNhom: (k: string) => void; moLech: () => void }) {
  const d = useMemo(() => diemVitri(ss), [ss]);
  const tl = useMemo(() => tiLe(ss), [ss]);
  const tang = Math.max(10, ...d.map(x => x.tang + 1));
  const day = TREN + tang * BUOC, H = day + 26;
  return (
    <>
      <div className="dt-cuon">
        <svg viewBox={`0 0 ${VW} ${H}`} className="dt-svg dt-svg-tt" role="group" aria-label="Giá KOME so với trung vị thị trường, mỗi chấm một nhóm">
          <text x={xP(0) + 6} y={16} fontSize={10} className="t-nhat">= trung vị thị trường</text>
          <text x={xP(-45)} y={16} fontSize={11} className="t-xanh t-dam">◀ KOME rẻ hơn</text>
          <text x={xP(55)} y={16} fontSize={11} textAnchor="end" className="t-do t-dam">KOME đắt hơn ▶</text>
          {[-50, -25, 0, 25, 50].map(p => (
            <Fragment key={p}>
              <line x1={xP(p)} x2={xP(p)} y1={22} y2={day + 4} className="ke" strokeDasharray={p ? "2 3" : undefined} />
              <text x={xP(p)} y={day + 20} fontSize={10} textAnchor="middle" className="t-nhat">{pcDau(p)}</text>
            </Fragment>))}
          {d.map(({ nhom, cot, tang: t }) => {
            const that = pTT(nhom)!;
            return (
              <ONoi key={nhom.nhom_khoa + "|" + nhom.don_vi_so} svg nhan={`${tenNhom(nhom)}: KOME ${pcDau(that)} so trung vị`}
                onBam={() => moNhom(nhom.nhom_khoa)} noi_dung={<>
                  <div className="o-noi-chu"><b>{tenNhom(nhom)}</b></div>
                  <DongNoi nhan="KOME so trung vị" gia={pcDau(that)} mau={MAU[mauTT(nhom)]} />
                  <DongNoi nhan="Giá KOME" gia={`${yen(nhom.gia_kome_so)}/kg`} />
                  <DongNoi nhan={`Trung vị · ${so(nhom.so_ben)} bên`} gia={`${yen(nhom.trung_vi)}/kg`} />
                </>}>
                <circle className="dt-dich" cx={xCot(cot)} cy={day - 4 - t * BUOC} r={4} fill={MAU[mauTT(nhom)]} />
              </ONoi>);
          })}
        </svg>
      </div>
      <div className="dt-tt-thanh" aria-hidden="true">
        <i style={{ flex: tl.re, background: "var(--ok-vien)" }} /><i style={{ flex: tl.ngang, background: "var(--chu-mo)" }} />
        <i style={{ flex: tl.dat, background: "var(--do)" }} /><i style={{ flex: tl.khongBan, background: "var(--vien)" }} />
      </div>
      <div className="dt-tt-cg">
        <span><i className="cg-xanh" /><b>{so(tl.re)}</b> rẻ hơn</span><span><i className="cg-xam" /><b>{so(tl.ngang)}</b> ngang (±5%)</span>
        <span><i className="cg-do" /><b>{so(tl.dat)}</b> đắt hơn</span>
        <span><i className="cg-trong" /><b>{so(tl.khongBan)}</b> nhóm KOME không bán</span>
      </div>
      {tl.lech > 0 && (
        <button type="button" className="dt-tt-canh" onClick={moLech}>
          ⚠ {so(tl.lech)} nhóm có giá KOME lệch &gt; 3× — xem Dữ liệu › Giá KOME lệch</button>)}
    </>
  );
}

// ---------------------------------------------------------------- đắt nhất / rẻ nhất

function DaiGia({ ds, tenBen, mo }: { ds: Nhom[]; tenBen: Map<string, string>; mo: (k: string) => void }) {
  if (!ds.length) return <p className="dt-nhat">Không có nhóm nào.</p>;
  return (
    <ul className="dt-tt-dais">{ds.map(n => {
      const p = pTT(n), m = MAU[mauTT(n)], k = n.gia_kome_so!;
      const lo = Math.min(n.thap_nhat, k), hi = Math.max(n.cao_nhat, k);
      const x = (v: number) => (hi > lo ? 6 + (v - lo) / (hi - lo) * 228 : 120);
      return (
        <li key={n.nhom_khoa + "|" + n.don_vi_so}>
          <button type="button" className="dt-tt-dai" onClick={() => mo(n.nhom_khoa)}
            aria-label={`${tenNhom(n)}: KOME ${pcDau(p)} so trung vị — mở So sánh giá`}>
            <HinhMa ma={n.ma_kome?.[0]} ten={tenNhom(n)} co={34} trang_tri />
            <span className="dt-tt-dt"><b>{tenNhom(n)}</b>
              <small>{[n.ma_kome?.[0], `${so(n.so_ben)} bên`, `thấp nhất ${tenBen.get(n.ben_thap_nhat) ?? n.ben_thap_nhat}`]
                .filter(Boolean).join(" · ")}</small></span>
            <svg viewBox="0 0 240 34" className="dt-tt-dai-svg" aria-hidden="true">
              <line x1={x(n.thap_nhat)} x2={x(n.cao_nhat)} y1={17} y2={17} className="dt-tt-dai-nen" strokeWidth={8} strokeLinecap="round" />
              <line x1={x(n.trung_vi)} x2={x(n.trung_vi)} y1={9} y2={25} className="dt-tt-dai-tv" strokeWidth={2} />
              <circle cx={x(k)} cy={17} r={6} fill={m} className="dt-tt-dai-kome" strokeWidth={2} />
            </svg>
            <span className="dt-tt-pc" style={{ color: m }}>{pcDau(p)}</span>
            <span className="dt-tt-gia">{yen(k)}/kg<small>TV {yen(n.trung_vi)}</small></span>
          </button>
        </li>);
    })}</ul>
  );
}

// ---------------------------------------------------------------- ai bán ngành nào (bóng)

const BLW = 150, BCOT = 66, BHANG = 22, BTREN = 38;

function Bong({ tq, ss, moSoSanh, moBen }: { tq: TongQuan; ss: Nhom[]; moSoSanh: MoSoSanh; moBen: (ma: string) => void }) {
  const { ben, nganh, o } = useMemo(() => bongNganh(tq), [tq]);
  const lon = Math.max(1, ...o.values());
  const W = BLW + 20 + nganh.length * BCOT, H = BTREN + ben.length * BHANG + 6;
  const xN = (j: number) => BLW + 20 + j * BCOT + BCOT / 2;
  if (!nganh.length) return <p className="dt-nhat">Chưa có mặt hàng đối thủ nào ghép được với mã KOME.</p>;
  return (
    <div className="dt-cuon">
      <svg viewBox={`0 0 ${W} ${H}`} className="dt-svg dt-svg-bong" style={{ minWidth: Math.min(W, 520) }} role="group"
        aria-label="Số mặt hàng trùng KOME theo đối thủ và ngành">
        {/* Tên ngành so le hai dòng — cột 66 px hẹp hơn tên dài ("Nước uống (Thái)"). */}
        {nganh.map((g, j) => <text key={g} x={xN(j)} y={j % 2 ? 28 : 14} fontSize={10.5} textAnchor="middle" className="t-nhat">{g}</text>)}
        {ben.map((b, i) => {
          const y = BTREN + i * BHANG + BHANG / 2;
          return (
            <g key={b.ma}>
              <text x={BLW} y={y + 4} fontSize={11} textAnchor="end" role="button" tabIndex={0} className="t-ben"
                aria-label={`Hồ sơ ${b.ten}`} onClick={() => moBen(b.ma)}
                onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); moBen(b.ma); } }}>{b.ten}</text>
              {nganh.map((g, j) => {
                const v = o.get(`${b.ma}|${g}`);
                if (!v) return null;
                const t = Math.sqrt(v / lon);
                return (
                  <ONoi key={g} svg nhan={`${b.ten} · ${g}: ${so(v)} mặt hàng — mở So sánh giá`}
                    onBam={() => moSoSanh({ nganh: nganhObc(tq, g, b.ma), ben: b.ma, sp: nhomCuaO(ss, g, b.ma) })}
                    noi_dung={<div className="o-noi-chu"><b>{b.ten}</b> · {g}: {so(v)} mặt hàng</div>}>
                    <circle className="dt-dich dt-bong" cx={xN(j)} cy={y} r={2.5 + 8.5 * t} fillOpacity={0.4 + 0.55 * t} />
                  </ONoi>);
              })}
            </g>);
        })}
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------- khuyến mãi theo bên

function KhuyenMai({ tq, tenBen, moBen, moSua }: {
  tq: TongQuan; tenBen: Map<string, string>; moBen: (ma: string) => void; moSua: (x: { nguon: string; id: number }) => void;
}) {
  const theoBen = useMemo(() => kmTheoBen(tq), [tq]);
  const noiBat = useMemo(() => kmNoiBat(tq), [tq]);
  if (!tq.khuyen_mai.length) return <p className="dt-nhat">Không có khuyến mãi nào trong bảng giá hiện hành.</p>;
  const lon = Math.max(1, ...theoBen.map(x => x.so));
  return (
    <>
      <ul className="dt-tt-kmb">{theoBen.map(x => (
        <li key={x.ma}>
          <button type="button" onClick={() => moBen(x.ma)} aria-label={`${x.ten}: ${so(x.so)} khuyến mãi — mở hồ sơ bên`}>
            <span>{x.ten}</span><span className="dt-tt-kmb-o"><i style={{ width: `${100 * x.so / lon}%` }} /></span><b>{so(x.so)}</b>
          </button>
        </li>))}</ul>
      {noiBat.length > 0 && (
        <div className="dt-tt-kms">{noiBat.map(k => (
          <button key={`${k.nguon}${k.id}`} type="button" className="dt-tt-km" onClick={() => moSua(k)}
            aria-label={`Sửa: ${tenBen.get(k.ben) ?? k.ben} — ${k.ten_goc}`}>
            <small>{tenBen.get(k.ben) ?? k.ben}</small><b>{k.ten_goc}</b>
            <span>{yen(k.gia_goc)} <s>{yen(k.gia_truoc_km)}</s></span>
          </button>))}</div>)}
    </>
  );
}
