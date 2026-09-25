// Màn "Sản phẩm" (Sản phẩm.dc.html): MỘT trang — ô tổng quan · danh mục (lọc
// nhóm / trạng thái / tìm, sắp theo cột) · hồ sơ 360° của mã đang chọn NGAY BÊN
// DƯỚI. /san-pham và /san-pham/{mã} là hai địa chỉ của màn này; chọn một dòng là
// pushState, không tải lại trang. Cả danh mục là MỘT ảnh chụp (/api/san-pham),
// nên lọc / sắp / tìm chạy ở trình duyệt, không hỏi lại máy chủ.
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { lay } from "../api";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../khung/khoang";
import { Spark } from "../chung/Khoi";
import { gon, ngay, pc, so, so_luong as soLuong, thay_doi, yen } from "../dinh_dang";
import { HoSoSanPham } from "./HoSoSanPham";
import type { DanhMucApi, DanhMucKhoangApi, MaHang } from "./kieu";
import { chuoiLocSp, docLocSp, locDanhMuc, SAP } from "./loc";
import type { LocSp } from "./loc";
import "./san_pham.css";
import { TN } from "../khoi_dau";

export function useDanhMuc() {
  const kx = chuoiKhoang(useKhoang());
  return useQuery<DanhMucApi>({ queryKey: ["sp-danh-muc", kx], placeholderData: keepPreviousData,
    queryFn: () => lay<DanhMucApi>(voiKhoang("/api/san-pham")) });
}

/** Doanh số trong khoảng xem của mọi mã (/api/san-pham/khoang — đợt C). */
function useDanhMucKhoang() {
  const kx = chuoiKhoang(useKhoang());
  return useQuery<DanhMucKhoangApi>({ queryKey: ["sp-khoang", kx], placeholderData: keepPreviousData,
    queryFn: () => lay<DanhMucKhoangApi>(voiKhoang("/api/san-pham/khoang")) });
}

function maTuUrl(): string | null {
  const m = location.pathname.match(/^\/san-pham\/([^/]+)$/);
  return m ? decodeURIComponent(m[1]) : null;
}

export default function ManSanPham() {
  const { data: d0, error } = useDanhMuc();
  const { data: kh } = useDanhMucKhoang();
  // Ghép số theo khoảng vào từng mã — chỉ gắn số của máy chủ, không tính gì.
  const d = useMemo(() => d0 && { ...d0, ma: d0.ma.map(m => {
    const x = kh?.dong[m.ma];
    return { ...m, dt_khoang: x?.[0] ?? 0, sl_khoang: x?.[2] ?? null, kh_khoang: x?.[3] ?? 0,
             dt_ss: kh?.so_sanh.co ? (x?.[4] ?? 0) : null };
  }) }, [d0, kh]);
  const [b, datB] = useState<LocSp>(() => docLocSp(location.search));
  const [ma, datMa] = useState<string | null>(maTuUrl);
  const [tim, datTim] = useState(b.tim);
  const hoSo = useRef<HTMLDivElement>(null);

  // URL = trạng thái (chia sẻ được, nút Back chạy đúng).
  useEffect(() => {
    const f = () => { datB(docLocSp(location.search)); datMa(maTuUrl()); };
    addEventListener("popstate", f); return () => removeEventListener("popstate", f);
  }, []);
  const ghi = (bb: LocSp, m: string | null, day = false) => {
    const q = chuoiLocSp(bb);
    const url = giuKhoang((m ? `/san-pham/${encodeURIComponent(m)}` : "/san-pham") + (q ? "?" + q : ""));
    if (url !== location.pathname + location.search) history[day ? "pushState" : "replaceState"](null, "", url);
  };
  const dat = (sua: Partial<LocSp>) => { const bb = { ...b, ...sua }; datB(bb); ghi(bb, ma); };
  const chon = (m: string | null, cuon = true) => {
    datMa(m); ghi(b, m, true);
    if (m && cuon) setTimeout(() => hoSo.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
  };
  useEffect(() => { const h = setTimeout(() => { if (tim !== b.tim) dat({ tim }); }, 200); return () => clearTimeout(h); }, [tim]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (maTuUrl() && d) setTimeout(() => hoSo.current?.scrollIntoView({ block: "start" }), 60); }, [!!d]); // eslint-disable-line react-hooks/exhaustive-deps

  const kq = useMemo(() => d ? locDanhMuc(d.ma, b, d.trang_thai) : null, [d, b]);
  const dong = useMemo(() => d && ma ? d.ma.find(x => x.ma === ma) ?? null : null, [d, ma]);
  useEffect(() => { document.title = dong ? `KOME — ${dong.ten}` : "KOME — sản phẩm"; }, [dong]);

  if (error) return <div className="sp"><h1>Sản phẩm</h1><div className="khoi-loi">Không tải được danh mục: {(error as Error).message}</div></div>;
  if (!d || !kq) return <div className="sp"><h1>Sản phẩm</h1><div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></div>;

  const tatCa = d.ma;
  const dt12 = tatCa.reduce((s, m) => s + m.dt_12t, 0), lg12 = tatCa.reduce((s, m) => s + m.lg_12t, 0);
  const coBan = tatCa.filter(m => m.dt_12t !== 0).length;
  const dem = (tt: string) => tatCa.filter(m => m.trang_thai === tt).length;
  const canDat = dem("het_hang") + dem("sap_thieu");
  const soTonChet = tatCa.filter(m => m.trang_thai === "ton_chet").length;
  const tongTT = Object.values(kq.dem_trang_thai).reduce((s, n) => s + n, 0);
  const tongNganh = kq.dem_nganh.reduce((s, [, n]) => s + n, 0);
  const locHopLe = b.loc in d.trang_thai ? b.loc : "";
  const kxNhan = kh?.khoang.nhan ?? "khoảng xem", ss = kh?.so_sanh;
  const dtKx = tatCa.reduce((s, m) => s + (m.dt_khoang ?? 0), 0);
  const dtSs = ss?.co ? tatCa.reduce((s, m) => s + (m.dt_ss ?? 0), 0) : null;
  const coBanKx = tatCa.filter(m => m.dt_khoang).length;
  const ten12 = d.thang.length ? `${d.thang[0].slice(5)}/${d.thang[0].slice(2, 4)} → ${d.thang[11].slice(5)}/${d.thang[11].slice(2, 4)}` : "";

  const cot = (k: string, chu: string, cls = "", title?: string) => {
    const dang = b.sap === k, tang = b.giam === "" ? SAP[k]?.tang : b.giam === "0";
    return <th className={"sap " + cls} title={title} aria-sort={dang ? (tang ? "ascending" : "descending") : "none"}
      onClick={() => dat({ sap: k, giam: dang ? (tang ? "1" : "0") : "" })}>{chu}{dang ? (tang ? " ▲" : " ▼") : ""}</th>;
  };

  return (
    <div className="sp">
      <div className="tieu-de-trang">
        <div><h1>Sản phẩm</h1>
          <div className="phu">Danh mục {so(tatCa.length)} mã hàng và hồ sơ 360° của mã đang chọn · dữ liệu đến hết {ngay(d.hom_nay)}</div></div>
        <div className="sp-dau-phai">
          <select value={ma ?? ""} onChange={e => chon(e.target.value || null)} aria-label="Chọn nhanh một mã hàng">
            <option value="">— chọn nhanh một mã ({so(tatCa.length)}) —</option>
            {[...tatCa].sort((x, y) => x.ma.localeCompare(y.ma)).map(m => <option key={m.ma} value={m.ma}>{m.ma} · {m.ten}</option>)}
          </select>
          <a className="nut-nho" href="/kho-hang">Tồn kho →</a>
        </div>
      </div>

      <div className="o-kpi-luoi sp-kpi">
        <div className="o-kpi"><div className="nhan">Doanh thu · {kxNhan}</div><div className="gia">{gon(dtKx)}</div>
          <div className={"dong-phu " + (!dtSs ? "nhat-chu" : dtKx >= dtSs ? "tang" : "giam")}>
            {!ss ? "…" : !ss.co ? `${ss.nhan}: không có dữ liệu để so` : dtSs ? `${thay_doi(dtKx / dtSs - 1)} so ${ss.nhan}` : `${ss.nhan}: không bán`}
            {" "}· {so(coBanKx)} mã có bán</div></div>
        <div className="o-kpi"><div className="nhan">Mã có bán trong 12 tháng</div><div className="gia">{so(coBan)}</div>
          <div className="dong-phu nhat-chu">trên {so(tatCa.length)} mã trong 商品マスタ</div></div>
        <div className="o-kpi"><div className="nhan">Doanh thu 12 tháng · cả danh mục</div><div className="gia">{gon(dt12)}</div>
          <div className="dong-phu nhat-chu">lãi gộp {gon(lg12)} · tỷ suất {pc(dt12 ? lg12 / dt12 : null)}</div></div>
        <a className="o-kpi" href="/kho-hang?tab=can_dat" title="Mở tab Cần đặt của màn Kho hàng">
          <div className="nhan">Cần đặt hàng →</div><div className={"gia" + (canDat ? " giam" : "")}>{so(canDat)}</div>
          <div className="dong-phu nhat-chu">{so(dem("het_hang"))} hết hàng · {so(dem("sap_thieu"))} sắp thiếu (&lt; 14 ngày)</div></a>
        <button type="button" className="o-kpi sp-kpi-nut" aria-pressed={locHopLe === "ton_chet"} onClick={() => dat({ loc: locHopLe === "ton_chet" ? "" : "ton_chet" })}>
          <div className="nhan">Tồn chết</div><div className={"gia" + (soTonChet ? " canh-chu" : "")}>{so(soTonChet)}</div>
          <div className="dong-phu nhat-chu">không bán 90 ngày, hoặc đủ bán &gt; 180 ngày · {so(dem("chua_ro_ton"))} mã chưa rõ tồn</div></button>
      </div>

      <section className="kh-the sp-dm">
        <div className="sp-dm-dau">
          <h2>Danh mục mã hàng</h2>
          <input type="search" className="kh-tim sp-tim" placeholder="Tìm mã, tên hàng, ngành…" value={tim}
            onChange={e => datTim(e.target.value)} aria-label="Tìm mã hàng" />
          <span className="phu">bấm một dòng để mở hồ sơ bên dưới</span>
        </div>
        <div className="sp-chip" role="group" aria-label="Ngành hàng">
          <button type="button" className="chip" aria-pressed={!b.nganh} onClick={() => dat({ nganh: "" })}>Mọi ngành ({so(tongNganh)})</button>
          {kq.dem_nganh.map(([n, c]) => (
            <button key={n} type="button" className="chip ten-jp" aria-pressed={b.nganh === n} onClick={() => dat({ nganh: b.nganh === n ? "" : n })}>
              {n} ({so(c)})</button>))}
          {b.nganh && !kq.dem_nganh.some(([n]) => n === b.nganh) &&
            <button type="button" className="chip ten-jp" aria-pressed onClick={() => dat({ nganh: "" })}>{b.nganh} (0)</button>}
        </div>
        <div className="sp-chip" role="group" aria-label="Trạng thái tồn">
          <button type="button" className="chip" aria-pressed={!locHopLe} onClick={() => dat({ loc: "" })}>Mọi trạng thái ({so(tongTT)})</button>
          {Object.entries(d.trang_thai).map(([k, [nhan, mau]]) => (
            <button key={k} type="button" className={"chip tt-" + mau} aria-pressed={locHopLe === k} onClick={() => dat({ loc: locHopLe === k ? "" : k })}>
              {nhan} ({so(kq.dem_trang_thai[k] ?? 0)})</button>))}
        </div>

        <div className="bang-cuon sp-bang-khung">
          <table className="bang sp-bang">
            <thead><tr>
              {cot("ten", "Mặt hàng")}{cot("nganh", "Ngành")}{cot("trang_thai", "Trạng thái")}
              {cot("ton", "Tồn", "so", "Tổng mọi kho, ảnh chụp 在庫一覧 mới nhất. — = chưa rõ tồn (không phải 0)")}
              {cot("toc_do", "Bán/ngày", "so", "Chia cho tuổi thật của mã (tối đa 90 ngày) — chính con số xếp trạng thái")}
              {cot("du_ban", "Còn đủ bán", "so", "Tồn ÷ Bán/ngày")}
              {cot("dt_khoang", `DT ${kxNhan}`, "so", "Doanh thu thuần trong khoảng đang xem")}
              {cot("so_khoang", ss ? `So ${ss.nhan}` : "So sánh", "so", ss ? `${ss.tu} → ${ss.den}` : undefined)}
              {cot("sl_khoang", "SL", "so", "Số lượng bán trong khoảng đang xem")}
              {cot("kh_khoang", "Khách mua", "so", "Số khách có mua mã này trong khoảng đang xem")}
              {cot("dt_12t", "DT 12 tháng", "so", "Doanh thu thuần 365 ngày tới mốc dữ liệu")}
              <th title={`Doanh thu theo tháng ${ten12}`}>12 tháng</th>
              {cot("ty_suat", "Tỷ suất 12T", "so", "Lãi gộp 12 tháng ÷ doanh thu 12 tháng")}
              {cot("so_khach", "Khách", "so", "Số khách đã từng mua (luỹ kế)")}
              {cot("lan_cuoi", "Bán gần nhất", "so")}
            </tr></thead>
            <tbody>
              {kq.hang.map(m => <Dong key={m.ma} m={m} chon={m.ma === ma} onChon={() => chon(m.ma)} />)}
              {!kq.hang.length && <tr><td colSpan={15} className="trong">Không có mã hàng nào khớp{b.tim ? ` với "${b.tim}"` : ""}. Thử bỏ bớt bộ lọc.</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="phu sp-ghi">{so(kq.hang.length)} mã đang hiện. <b>Chưa rõ tồn</b> KHÁC <b>hết hàng</b>: mã không có dòng nào trong
          在庫一覧 thì ta không biết kho còn bao nhiêu — cột Tồn hiện "—". <b>Ngừng kinh doanh</b> = tồn 0 và không bán suốt 90 ngày.
          <b> Tồn chết</b> gộp mã không bán gì suốt 90 ngày và mã còn đủ bán trên 180 ngày; mã ra mắt trong 90 ngày không bao giờ bị gọi là tồn chết.</p>
      </section>

      <div ref={hoSo} className="sp-ho-so-neo">
        {ma ? <HoSoSanPham ma={ma} dong={dong} onDong={() => chon(null, false)} />
          : <div className="sp-chua-chon">Chọn một mã trong danh mục (hoặc ô "chọn nhanh" ở trên) để xem hồ sơ 360°: bán theo ngày, khách đang mua / đã bỏ, tồn theo kho{TN.bang_gia ? ", giá theo bậc" : ""}.</div>}
      </div>
    </div>
  );
}

function Dong({ m, chon, onChon }: { m: MaHang; chon: boolean; onChon: () => void }) {
  return (
    <tr className={"sp-dong" + (chon ? " chon" : "")} onClick={e => { if (!(e.target as HTMLElement).closest("a")) onChon(); }}
      aria-selected={chon}>
      <td className="sp-ten"><a href={`/san-pham/${encodeURIComponent(m.ma)}`} className="ten-jp"
        onClick={e => { e.preventDefault(); onChon(); }}>{m.ten}</a><div className="ma-nho"><code>{m.ma}</code></div></td>
      <td className="sp-nhom ten-jp" title={m.nganh}>{m.nganh}</td>
      <td><span className={"nhan-vien " + m.mau}>{m.nhan_trang_thai}</span></td>
      <td className="so">{m.ton == null ? <span className="nhat-chu" title="chưa rõ tồn — không có dòng nào trong 在庫一覧">—</span> : soLuong(m.ton)}</td>
      <td className="so">{soLuong(m.toc_do_ngay_theo_tuoi)}</td>
      <td className={"so " + (m.du_ban_ngay != null && m.du_ban_ngay < 14 ? "giam" : "")}>{m.du_ban_ngay == null ? "—" : `${Math.round(m.du_ban_ngay)} ngày`}</td>
      <td className="so"><b>{m.dt_khoang ? yen(m.dt_khoang) : <span className="nhat-chu">¥0</span>}</b></td>
      <td className="so">{m.dt_ss ? <span className={(m.dt_khoang ?? 0) >= m.dt_ss ? "tang" : "giam"}>{thay_doi((m.dt_khoang ?? 0) / m.dt_ss - 1, 0)}</span> : <span className="nhat-chu">—</span>}</td>
      <td className="so">{m.sl_khoang == null ? <span className="nhat-chu">—</span> : soLuong(m.sl_khoang)}</td>
      <td className="so">{so(m.kh_khoang ?? 0)}</td>
      <td className="so">{m.dt_12t ? yen(m.dt_12t) : <span className="nhat-chu">¥0</span>}</td>
      <td className="sp-spark">{m.thang_dt.some(v => v) ? <Spark gia_tri={m.thang_dt} cao={20} mau="var(--lien-ket)" /> : <span className="nhat-chu">không bán</span>}</td>
      <td className="so">{pc(m.ts_12t)}</td>
      <td className="so">{so(m.so_khach)}</td>
      <td className="so nhat-chu">{ngay(m.lan_cuoi)}</td>
    </tr>
  );
}
