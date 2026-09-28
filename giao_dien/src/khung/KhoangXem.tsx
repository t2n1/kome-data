// Bộ chọn khoảng xem chung — HAI THẺ (đặc tả 2026-09-28-ky-so-sanh-toan-web-design.md §5):
// "ĐANG XEM" (nét liền: Tháng / Kỳ / Khoảng · ‹ ô chọn ›) và "SO VỚI" (nét đứt: chip
// năm trước / tháng trước của máy chủ + kỳ tự chọn `ss_*`). Mọi dải ngày là CỦA MÁY
// CHỦ (kome/khoang_xem.py — bộ chọn không tự tính ngày so sánh); tính toán ở đây chỉ
// là điều hướng (tháng trước / sau, nút nhanh của dạng Khoảng) và đếm số ngày để in.
import { useState } from "react";
import { datKhoang, datSoSanh, useKhoang, useKhoangMayChu, usePhamVi, type Khoang, type KhoangMayChu,
  type PhamVi } from "./khoang";
import { MauSs } from "../chung/SoSanh";

const thangCua = (iso: string) => iso.slice(0, 7);
const cong = (thang: string, n: number) => {
  const [y, m] = thang.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + n, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
};
const lui = (iso: string, ngay: number) => {
  const d = new Date(iso.slice(0, 10) + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() - ngay);
  return d.toISOString().slice(0, 10);
};
const nhanThang = (t: string) => `Tháng ${+t.slice(5)}/${t.slice(0, 4)}`;
const hoa = (s: string) => s.replace(/^./, c => c.toUpperCase());
const _n = (iso: string, nam: boolean) => {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return nam ? `${+d}/${+m}/${y}` : `${+d}/${+m}`;
};
/** "1/9 → 28/9/2026" — cùng cách in với máy chủ (khoang_xem._dai). */
const dai = (tu: string, den: string) => `${_n(tu, tu.slice(0, 4) !== den.slice(0, 4))} → ${_n(den, true)}`;
const soNgay = (tu: string, den: string) =>
  Math.round((Date.parse(den.slice(0, 10)) - Date.parse(tu.slice(0, 10))) / 864e5) + 1;

export function KhoangXem({ mo }: { mo?: string }) {
  const k = useKhoang();
  const { data: pv } = usePhamVi();
  const kx = useKhoangMayChu();
  const [moKhoang, datMoKhoang] = useState(false);
  const loai: "thang" | "ky" | "khoang" = k.ky ? "ky" : k.tu ? "khoang" : "thang";

  if (mo) return <div className="kx kx-mo" role="note"><span className="kx-nhan">KHOẢNG XEM</span><span className="phu">{mo}</span></div>;
  if (pv === null) return null;                  // kho chưa có dòng bán nào
  if (!pv) return <div className="kx" aria-busy="true"><span className="kx-nhan">KHOẢNG XEM</span><span className="phu">Đang tải…</span></div>;

  const tDau = thangCua(pv.ngay_dau), tCuoi = thangCua(pv.hom_nay);
  const chon = (x: Khoang) => datKhoang(x);
  const chonThang = (t: string) => chon(t === tCuoi ? {} : { thang: t });
  const tDang = k.thang ?? tCuoi;
  const kyDang = k.ky ? +k.ky : pv.ky[pv.ky.length - 1]?.company_fy;
  const iKy = pv.ky.findIndex(x => x.company_fy === kyDang);

  const doiLoai = (l: typeof loai) => {
    if (l === "thang") chon({});
    else if (l === "ky") chon({ ky: String(pv.ky[pv.ky.length - 1].company_fy) });
    else { chon({ tu: kx?.tu ?? `${tCuoi}-01`, den: kx?.den ?? pv.hom_nay }); datMoKhoang(true); }
  };

  return (
    <div className="kx kx-hai" role="group" aria-label="Khoảng xem và kỳ so sánh">
      {/* Thẻ ĐANG XEM — nét liền, đúng mẫu của chuỗi chính trên mọi biểu đồ. */}
      <section className="kx-the kx-xem" aria-label="Đang xem">
        <div className="kx-dau">
          <span className="kx-nhan"><MauSs lien />ĐANG XEM</span>
          <div className="tab-pill" role="group" aria-label="Dạng khoảng xem">
            {(["thang", "ky", "khoang"] as const).map(l => (
              <button key={l} type="button" aria-pressed={loai === l} onClick={() => doiLoai(l)}>
                {l === "thang" ? "Tháng" : l === "ky" ? "Kỳ" : "Khoảng"}</button>))}
          </div>
        </div>
        <div className="kx-giua">
          <div className="kx-to">{kx?.nhan ?? (loai === "thang" ? nhanThang(tDang) : "…")}</div>
          {loai === "thang" && <div className="kx-dieu">
            <button type="button" className="nut-nho" aria-label="Tháng trước" disabled={tDang <= tDau}
              onClick={() => chonThang(cong(tDang, -1))}>‹</button>
            <input type="month" className="kx-o" value={tDang} min={tDau} max={tCuoi} aria-label="Chọn tháng"
              onChange={e => e.target.value && chonThang(e.target.value)} />
            <button type="button" className="nut-nho" aria-label="Tháng sau" disabled={tDang >= tCuoi}
              onClick={() => chonThang(cong(tDang, 1))}>›</button>
            {k.thang && <button type="button" className="nut-nho" onClick={() => chon({})}>Tháng hiện tại</button>}
          </div>}
          {loai === "ky" && <div className="kx-dieu">
            <button type="button" className="nut-nho" aria-label="Kỳ trước" disabled={iKy <= 0}
              onClick={() => chon({ ky: String(pv.ky[iKy - 1].company_fy) })}>‹</button>
            <select className="kx-o" value={String(kyDang)} aria-label="Chọn kỳ" onChange={e => chon({ ky: e.target.value })}>
              {pv.ky.map(x => <option key={x.company_fy} value={x.company_fy}>Kỳ {x.so_ky} (8/{x.company_fy - 1} → 7/{x.company_fy})</option>)}
            </select>
            <button type="button" className="nut-nho" aria-label="Kỳ sau" disabled={iKy >= pv.ky.length - 1}
              onClick={() => chon({ ky: String(pv.ky[iKy + 1].company_fy) })}>›</button>
          </div>}
        </div>
        {loai === "khoang" && <KhoangNgay k={k} pv={pv} mo={moKhoang} />}
        <div className="kx-dai phu" aria-live="polite">
          {kx ? <>{dai(kx.tu, kx.den)} · {soNgay(kx.tu, kx.den)} ngày{!kx.tron_thang && kx.loai === "thang" ? " · tháng đang chạy" : ""}
            {kx.ghi_chu.map(g => <span key={g} className="kx-ghi"> · {g}</span>)}</> : "…"}
        </div>
      </section>

      <span className="kx-vs" aria-hidden="true">so với</span>

      <SoVoi k={k} pv={pv} kx={kx} />
    </div>
  );
}

function KhoangNgay({ k, pv, mo }: { k: Khoang; pv: { ngay_dau: string; hom_nay: string }; mo: boolean }) {
  const [tu, datTu] = useState(k.tu ?? "");
  const [den, datDen] = useState(k.den ?? "");
  const hn = pv.hom_nay;
  const nhanh: [string, string, string][] = [
    ["30 ngày", lui(hn, 29), hn],
    ["3 tháng", `${cong(thangCua(hn), -2)}-01`, hn],
    ["Từ đầu năm", `${hn.slice(0, 4)}-01-01`, hn],
  ];
  const ap = (a: string, b: string) => {
    const a2 = a < pv.ngay_dau ? pv.ngay_dau : a;
    datTu(a2); datDen(b); datKhoang({ tu: a2, den: b });
  };
  return (
    <form className="kx-dieu" onSubmit={e => { e.preventDefault(); if (tu && den && tu <= den) ap(tu, den); }}>
      <input type="date" className="kx-o" value={tu} min={pv.ngay_dau} max={hn} aria-label="Từ ngày"
        autoFocus={mo} onChange={e => datTu(e.target.value)} />
      <span aria-hidden="true">→</span>
      <input type="date" className="kx-o" value={den} min={pv.ngay_dau} max={hn} aria-label="Đến ngày"
        onChange={e => datDen(e.target.value)} />
      <button type="submit" className="nut-nho chinh" disabled={!tu || !den || tu > den}>Xem</button>
      {nhanh.map(([n, a, b]) => <button key={n} type="button" className="nut-nho" onClick={() => ap(a, b)}>{n}</button>)}
    </form>
  );
}

/** Thẻ "SO VỚI" — nét đứt, đúng mẫu của kỳ so trên mọi biểu đồ. Chip mặc định lấy
 *  từ máy chủ (`lua_chon`); "Tuỳ chọn…" mở bộ chọn kỳ tự chọn (`ss_*`). Ô chọn giới
 *  hạn tới ngày cuối khoảng đang xem — kỳ so phải nằm trước đó (mốc, 040). */
function SoVoi({ k, pv, kx }: { k: Khoang; pv: PhamVi; kx: KhoangMayChu | null }) {
  const coSs = !!(k.ss_thang || k.ss_ky || k.ss_tu);
  const [mo, datMo] = useState(false);
  const [loai, datLoai] = useState<"thang" | "ky" | "khoang">(k.ss_ky ? "ky" : k.ss_tu ? "khoang" : "thang");
  const [tu, datTu] = useState(k.ss_tu ?? "");
  const [den, datDen] = useState(k.ss_den ?? "");
  const cuoi = kx?.den ?? pv.hom_nay;
  const tDau = thangCua(pv.ngay_dau), tCuoi = thangCua(cuoi);
  const s = kx?.so_sanh[0];
  const ap = (x: Parameters<typeof datSoSanh>[0]) => { datSoSanh(x); datMo(false); };
  // Phần của khoảng xem thật sự đem so khác cả khoảng (dạng Kỳ, dữ liệu bắt đầu giữa
  // chừng) · hai bên khác số ngày (kỳ tự chọn) — nói ra, đừng để người đọc tự suy.
  const catLai = !!s && !!kx && (s.tu_nay !== kx.tu || s.den_nay !== kx.den);
  const khacNgay = !!s && soNgay(s.tu_nay, s.den_nay) !== soNgay(s.tu, s.den);

  return (
    <section className="kx-the kx-ss" aria-label="So với">
      <div className="kx-dau">
        <span className="kx-nhan"><MauSs />SO VỚI</span>
        <div className="kx-chips" role="group" aria-label="Kỳ so">
          {(kx?.lua_chon ?? []).map(c => (
            <button key={c.ma} type="button" className="chip" aria-pressed={!coSs && c.chon}
              onClick={() => ap(c.ma === "nam_truoc" ? {} : { ss: "truoc" })}>{hoa(c.nhan)}</button>))}
          {coSs && <span className="chip kx-chip-tc">{s ? hoa(s.nhan) : "Kỳ đã chọn"}
            <button type="button" aria-label="Bỏ kỳ so tự chọn, về năm trước" onClick={() => ap({})}>✕</button></span>}
          <button type="button" className="chip" aria-expanded={mo} onClick={() => datMo(!mo)}>
            {coSs ? "Đổi…" : "Tuỳ chọn…"}</button>
        </div>
      </div>
      <div className="kx-giua"><div className="kx-to">{s ? hoa(s.nhan) : "…"}</div></div>
      <div className="kx-dai phu">
        {!s ? "…" : !s.co ? <span className="kx-ghi">Không có dữ liệu để so — kỳ này nằm trước dữ liệu trong kho.</span>
          : <>{dai(s.tu, s.den)}
            {catLai ? ` · so với phần ${dai(s.tu_nay, s.den_nay)} của khoảng xem` : ""}
            {khacNgay ? ` · ${soNgay(s.tu_nay, s.den_nay)} ngày với ${soNgay(s.tu, s.den)} ngày`
              : kx && !kx.tron_thang && kx.loai === "thang" ? ` · cắt cùng ${soNgay(kx.tu, kx.den)} ngày` : ""}</>}
      </div>

      {mo && <div className="kx-dieu kx-tuy-chon">
        <div className="tab-pill" role="group" aria-label="Dạng kỳ so sánh">
          {(["thang", "ky", "khoang"] as const).map(l => (
            <button key={l} type="button" aria-pressed={loai === l} onClick={() => datLoai(l)}>
              {l === "thang" ? "Tháng" : l === "ky" ? "Kỳ" : "Khoảng"}</button>))}
        </div>
        {loai === "thang" && <input type="month" className="kx-o" min={tDau} max={tCuoi}
          defaultValue={k.ss_thang ?? ""} aria-label="Tháng để so"
          onChange={e => e.target.value && ap({ ss_thang: e.target.value })} />}
        {loai === "ky" && <select className="kx-o" aria-label="Kỳ để so" defaultValue={k.ss_ky ?? ""}
          onChange={e => e.target.value && ap({ ss_ky: e.target.value })}>
          <option value="" disabled>— chọn kỳ —</option>
          {pv.ky.filter(x => x.tu <= cuoi).map(x =>
            <option key={x.company_fy} value={x.company_fy}>Kỳ {x.so_ky} (8/{x.company_fy - 1} → 7/{x.company_fy})</option>)}
        </select>}
        {loai === "khoang" && <form className="kx-dieu" onSubmit={e => {
          e.preventDefault(); if (tu && den && tu <= den) ap({ ss_tu: tu, ss_den: den }); }}>
          <input type="date" className="kx-o" value={tu} min={pv.ngay_dau} max={cuoi} aria-label="So từ ngày"
            onChange={e => datTu(e.target.value)} />
          <span aria-hidden="true">→</span>
          <input type="date" className="kx-o" value={den} min={pv.ngay_dau} max={cuoi} aria-label="So đến ngày"
            onChange={e => datDen(e.target.value)} />
          <button type="submit" className="nut-nho chinh" disabled={!tu || !den || tu > den}>So</button>
        </form>}
      </div>}
    </section>
  );
}
