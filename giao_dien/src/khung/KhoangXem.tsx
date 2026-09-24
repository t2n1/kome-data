// Bộ chọn khoảng xem chung (đặc tả khoảng xem §4): ‹ Tháng 7/2026 › · nút gạt
// Tháng / Kỳ / Khoảng · dòng mô tả CỦA MÁY CHỦ (kome/khoang_xem.py — bộ chọn
// không tự tính ngày so sánh). Chỉ tính toán ở đây là điều hướng: tháng trước /
// sau, và mấy nút nhanh của dạng Khoảng.
import { useState } from "react";
import { datKhoang, useKhoang, useKhoangMayChu, usePhamVi, type Khoang } from "./khoang";

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
    <div className="kx" role="group" aria-label="Khoảng xem">
      <span className="kx-nhan">KHOẢNG XEM</span>
      <div className="tab-pill" role="group" aria-label="Dạng khoảng xem">
        {(["thang", "ky", "khoang"] as const).map(l => (
          <button key={l} type="button" aria-pressed={loai === l} onClick={() => doiLoai(l)}>
            {l === "thang" ? "Tháng" : l === "ky" ? "Kỳ" : "Khoảng"}</button>))}
      </div>

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

      {loai === "khoang" && <KhoangNgay k={k} pv={pv} mo={moKhoang} />}

      <div className="kx-mo-ta phu" aria-live="polite">
        {kx ? <>{kx.mo_ta}{kx.ghi_chu.map(g => <span key={g} className="kx-ghi"> · {g}</span>)}</>
          : loai === "thang" ? nhanThang(tDang) : "…"}
      </div>
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
