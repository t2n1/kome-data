// Campaign tuần (/campaign, 074). Bản kế hoạch + soát do máy công ty lập (Google Sheet + Cybozu chỉ đọc được từ đó) và
// gửi lên — web KHÔNG tính gì: nhóm, lý do, phán định là của script. Ô tick chỉ đổi phần sẽ chép, không lưu (sheet
// キャンペーン管理シート vẫn là bản chính thức cho sếp xem). Đặc tả: 2026-10-23-campaign-tuan-design.md.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { lay } from "../api";
import { giuKhoang } from "../khung/khoang";
import { HinhMa } from "../chung/HinhMa";
import { ChuThich } from "../chung/Khoi";
import { gon, pc, so } from "../dinh_dang";
import { chepAB, chepF, chepGia, CU_GIO, demSheet, gioTu, macDinh, md, NHOM, theoNhom, theoSheet, thieuDong, trangSheet, xepMa } from "./chep";
import type { CotXep, TrangSheet } from "./chep";
import type { BanCampaign, CampaignApi, MaKeHoach, Nhom, Soat, TuanKeHoach } from "./kieu";
import "./campaign.css";

type Tab = "ke_hoach" | "soat";
const docTab = (): Tab => (new URLSearchParams(location.search).get("tab") === "soat" ? "soat" : "ke_hoach");

export default function ManCampaign() {
  const { data: d, error } = useQuery<CampaignApi>({ queryKey: ["campaign"], queryFn: () => lay<CampaignApi>("/api/campaign") });
  const [tab, datTab] = useState<Tab>(docTab);
  useEffect(() => { document.title = "KOME — campaign tuần"; }, []);
  useEffect(() => {
    const f = () => datTab(docTab());
    addEventListener("popstate", f); return () => removeEventListener("popstate", f);
  }, []);
  const doi = (t: Tab) => {
    datTab(t);
    history.replaceState(null, "", giuKhoang("/campaign" + (t === "soat" ? "?tab=soat" : "")));
  };

  const dau = <h1>Campaign tuần</h1>;
  if (error) return <div className="cp">{dau}<div className="khoi-loi">Không tải được: {(error as Error).message}</div></div>;
  if (!d) return <div className="cp">{dau}<div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></div>;
  if (!d.du_lieu || !d.nop_luc) return (
    <div className="cp">{dau}
      <p className="cp-ghi">Chưa có bản nào. Máy công ty gửi bản kế hoạch + soát lên mỗi ngày làm việc lúc 8:30 và 14:00
        (tác vụ <code>KOME Soat campaign</code>).</p></div>);
  const b = d.du_lieu;
  const gio = gioTu(d.nop_luc, new Date());

  return (
    <div className="cp">
      <div className="tieu-de-trang"><div>{dau}
        <div className="phu">Lập lúc {b.lap_luc.replace("T", " ")} · gửi lên {new Date(d.nop_luc).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" })}.
          Sheet <span className="ten-jp">キャンペーン管理シート</span> vẫn là bản chính thức — trang này đưa dữ liệu để dán vào đó.</div></div></div>
      {gio > CU_GIO && <p className="cp-cu" role="alert">Bản này đã {so(gio)} giờ — máy công ty chưa gửi bản mới (máy tắt, hoặc
        tác vụ <code>KOME Soat campaign</code> lỗi: xem <code>raw_archive/campaign_soat/loi.log</code>). Lịch hàng về có thể đã đổi.</p>}
      <div role="tablist" className="kh-tab" aria-label="Campaign tuần">
        <button role="tab" type="button" aria-selected={tab === "ke_hoach"} onClick={() => doi("ke_hoach")}>
          Kế hoạch đề xuất ({b.ke_hoach.length} tuần)</button>
        <button role="tab" type="button" aria-selected={tab === "soat"} onClick={() => doi("soat")}>
          Soát hằng ngày ({so(b.soat.tuan.reduce((s, t) => s + t.dong.length, 0))} mã cần xem)</button>
      </div>
      {tab === "ke_hoach" ? <KeHoach b={b} /> : <SoatNgay s={b.soat} />}
      <p className="phu cp-nguon">{b.nguon}</p>
    </div>
  );
}

function KeHoach({ b }: { b: BanCampaign }) {
  // Phần chọn của MỖI tuần sống ở đây (đổi tuần không mất tick); không lưu — tải lại trang là về đề xuất.
  const [o, datO] = useState(0);
  const [chon, datChonTat] = useState<Record<string, Set<string>>>({});
  if (!b.ke_hoach.length) return <p className="cp-ghi">Bản này chưa có tuần nào.</p>;
  const cua = (t: TuanKeHoach) => chon[t.tu] ?? macDinh(t);
  const t = b.ke_hoach[Math.min(o, b.ke_hoach.length - 1)];
  return <>
    <div className="cp-tuan-chon" role="tablist" aria-label="Chọn tuần">
      {b.ke_hoach.map((x, i) => {
        const c = cua(x), d = demSheet(x, c);
        return <button key={x.tu} type="button" role="tab" aria-selected={x === t} onClick={() => datO(i)}>
          <b>{md(x.tu)}</b>{!x.tren_sheet && <span className="cp-moi">mới</span>}
          <small>{so(c.size)} mã{d && <> · <span className="tang">+{d.them}</span> <span className="giam">−{d.bo}</span></>}</small>
        </button>;
      })}
    </div>
    <KhoiTuan key={t.tu} t={t} thu_tu={b.thu_tu_gia} chon={cua(t)}
      datChon={c => datChonTat(x => ({ ...x, [t.tu]: c }))} />
  </>;
}

const COT: { cot: CotXep; nhan: string; giai: string }[] = [
  { cot: "ngay", nhan: "Còn bán", giai: "Tồn đầu tuần đủ bán bao nhiêu ngày (theo tốc độ bán, tuần sale × hệ số riêng của mã)" },
  { cot: "bien", nhan: "Lãi giá sàn", giai: "(giá sàn chưa thuế − giá vốn) ÷ giá sàn — đúng công thức cột 粗利額 của tab tháng" },
  { cot: "lai", nhan: "Lãi thêm/lần sale", giai: "Một lần sale (tuần sale + tuần ngay sau) làm lãi gộp hơn hai tuần thường cùng mùa bao nhiêu — đo trên lịch sử sale từ 2025/6; ~ = ước vì chưa đủ 2 lần đo; \"chưa chắc\" = lúc lời lúc lỗ" },
  { cot: "mua", nhan: "Mùa", giai: "Cùng kỳ năm trước bán gấp mấy lần bình thường — chỉ hiện khi lệch rõ" },
];

function KhoiTuan({ t, thu_tu, chon, datChon }: {
  t: TuanKeHoach; thu_tu: string[]; chon: Set<string>; datChon: (c: Set<string>) => void;
}) {
  const [bao, datBao] = useState("");
  const [loc_nhom, datLocNhom] = useState<Nhom | null>(null);
  const [loc_sheet, datLocSheet] = useState<TrangSheet | null>(null);
  const [cot, datCot] = useState<CotXep | null>(null);
  const [mo, datMo] = useState<Set<Nhom>>(new Set());
  const nhom = theoNhom(t.ma);
  const thieu = thieuDong(thu_tu, chon);
  const d = demSheet(t, chon);
  const bat = (ma: string) => { const n = new Set(chon); if (n.has(ma)) n.delete(ma); else n.add(ma); datChon(n); };
  const chep = async (ten: string, van: string) => {
    try { await navigator.clipboard.writeText(van); datBao(`Đã chép ${ten}.`); }
    catch { window.prompt(`Chép ${ten}:`, van); }
    setTimeout(() => datBao(""), 2500);
  };
  const menu = (ten: string, van: string) => (e: React.MouseEvent) => {
    e.currentTarget.closest("details")?.removeAttribute("open");
    void chep(ten, van);
  };
  const so_cot = t.tren_sheet ? 8 : 7;
  return (
    <section className="kh-the cp-tuan" aria-label={`Tuần ${t.ky}`}>
      <div className="cp-dau">
        <div>
          <h2>Tuần {t.ky} <ChuThich nhan="Cách dùng">
            Đề xuất từ tuần sau, nhịp xen kẽ đều nối từ tuần đầu (kể cả tuần đã có trên sheet). Lãi của một lần sale = tuần sale +
            tuần ngay sau, so với tuần thường cùng mùa, đo trên lịch sử sale từ 2025/6; mã sale lỗ ổn định không chạy. Trong mỗi
            nhóm, mã xếp theo lãi thêm × mùa cùng kỳ năm trước; bấm tiêu đề cột để xếp lại.
            Rê chuột lên một dòng để xem lý do đầy đủ.<br /><br />
            Tick để bỏ / thêm mã rồi bấm <b>Chép ▾</b>. Tab tháng: dán <b>cột A–B</b> và <b>cột F</b> vào các dòng ngay dưới dòng
            合計 của tuần (không dán đè cột C–E — công thức). 値段管理: dán vào cột của tuần, bắt đầu ở <b>dòng 3</b>.
            Lựa chọn không được lưu — tải lại trang là về đề xuất.</ChuThich></h2>
          <div className="phu">tab <span className="ten-jp">{t.tab}</span> · <span className="ten-jp">週目</span> {t.tuan_so} ·
            đang chọn <b>{so(chon.size)}</b> mã{!t.tren_sheet && " · sheet chưa có tuần này"}</div>
        </div>
        {d && <div className="cp-so-sheet" role="group" aria-label="So với sheet">
          {([["giu", d.giu, "giống sheet"], ["them", d.them, "mình thêm"], ["bo", d.bo, "mình bỏ"]] as const).map(([k, n, nhan]) =>
            <button key={k} type="button" className={"cp-sh-" + k} aria-pressed={loc_sheet === k}
              onClick={() => datLocSheet(loc_sheet === k ? null : k)}>
              <b>{k === "them" ? "+" : k === "bo" ? "−" : ""}{so(n)}</b><small>{nhan}</small></button>)}
        </div>}
        <div className="cp-nut">
          <button type="button" className="nut-nap" onClick={() => datChon(macDinh(t))}>Về đề xuất</button>
          {t.tren_sheet && <button type="button" className="nut-nap" onClick={() => datChon(theoSheet(t))}>Theo sheet</button>}
          <details className="cp-chep">
            <summary className="nut-chinh">Chép ▾</summary>
            <div className="cp-menu">
              <button type="button" onClick={menu("cột A–B", chepAB(t, chon))}>Cột A–B<small><span className="ten-jp">週目 · 期間</span> — {so(chon.size)} dòng</small></button>
              <button type="button" onClick={menu("cột F", chepF(chon))}>Cột F<small><span className="ten-jp">商品コード</span> — mỗi dòng một mã</small></button>
              <button type="button" onClick={menu("cột 値段管理", chepGia(thu_tu, chon))}>Cột tuần của <span className="ten-jp">値段管理</span><small>dán từ dòng 3</small></button>
            </div>
          </details>
          <span className="cp-bao" role="status">{bao}</span>
        </div>
      </div>
      {thieu.length > 0 && <p className="cp-cu">Chưa có dòng trên <span className="ten-jp">値段管理</span> (cột tuần sẽ thiếu): {thieu.join(", ")}</p>}
      {loc_sheet === "bo" && d && d.ngoai.length > 0 &&
        <p className="cp-ghi">Sheet còn có (không nằm trong danh sách đề xuất): {d.ngoai.join(", ")}</p>}
      <div className="cp-loc" role="group" aria-label="Lọc nhóm">
        <button type="button" aria-pressed={!loc_nhom} onClick={() => datLocNhom(null)}>Tất cả <i>{t.ma.length}</i></button>
        {NHOM.filter(n => nhom.get(n.ma)?.length).map(n =>
          <button key={n.ma} type="button" aria-pressed={loc_nhom === n.ma} onClick={() => datLocNhom(loc_nhom === n.ma ? null : n.ma)}>
            {n.nhan} <i>{nhom.get(n.ma)!.length}</i></button>)}
      </div>
      <div className="bang-cuon"><table className="bang cp-bang">
        <thead><tr>
          <th><span className="cp-an">Chọn</span></th><th>Mã</th>
          <ThXep c={COT[0]} cot={cot} dat={datCot} />
          <th>Lô về / lô hạn</th>
          {COT.slice(1).map(c => <ThXep key={c.cot} c={c} cot={cot} dat={datCot} />)}
          {t.tren_sheet && <th title="✓ sheet có, mình cũng chọn · + mình thêm · − sheet có, mình bỏ">Sheet</th>}
        </tr></thead>
        {NHOM.map(n => {
          if (loc_nhom && loc_nhom !== n.ma) return null;
          const ds = xepMa((nhom.get(n.ma) ?? []).filter(m => !loc_sheet || trangSheet(t, chon, m) === loc_sheet), cot);
          if (!ds.length) return null;
          const so_chon = ds.filter(m => chon.has(m.ma)).length;
          const ep = loc_nhom === n.ma || loc_sheet != null;     // đang lọc: luôn mở
          const mo_ra = !n.gap || ep || mo.has(n.ma);
          return <tbody key={n.ma} className={"cp-n-" + n.ma}>
            <tr className="cp-nhom-dong"><td colSpan={so_cot}>
              <button type="button" aria-expanded={mo_ra} disabled={!n.gap || ep}
                onClick={() => datMo(x => { const y = new Set(x); if (y.has(n.ma)) y.delete(n.ma); else y.add(n.ma); return y; })}>
                {n.gap && !ep && <span aria-hidden="true">{mo_ra ? "▾ " : "▸ "}</span>}<b>{n.nhan}</b> ({ds.length}
                {n.gap && so_chon > 0 ? ` · đang chọn ${so_chon}` : ""})<span className="phu"> — {n.giai}</span></button></td></tr>
            {mo_ra && ds.map(m => <DongMa key={m.ma} m={m} chon={chon.has(m.ma)} bat={bat}
              sh={trangSheet(t, chon, m)} co_sheet={!!t.tren_sheet} />)}
          </tbody>;
        })}
      </table></div>
    </section>
  );
}

function ThXep({ c, cot, dat }: { c: (typeof COT)[number]; cot: CotXep | null; dat: (c: CotXep | null) => void }) {
  return <th className={c.cot === "mua" ? undefined : "so"} aria-sort={cot === c.cot ? "descending" : "none"}>
    <button type="button" className="cp-xep" title={c.giai} onClick={() => dat(cot === c.cot ? null : c.cot)}>
      {c.nhan}{cot === c.cot ? " ↓" : ""}</button></th>;
}

const KY_SHEET: Record<TrangSheet, [string, string]> = {
  giu: ["✓", "sheet có, mình cũng chọn"], them: ["+", "mình thêm (sheet chưa có)"], bo: ["−", "sheet có, mình bỏ"],
};
/** Hạn dùng ISO → "4/15/27"; dạng lạ (chữ OBC) giữ nguyên. */
const hanNgan = (iso: string) => (/^\d{4}-\d\d-\d\d$/.test(iso) ? `${md(iso)}/${iso.slice(2, 4)}` : iso);

function DongMa({ m, chon, bat, sh, co_sheet }: {
  m: MaKeHoach; chon: boolean; bat: (ma: string) => void; sh: TrangSheet | null; co_sheet: boolean;
}) {
  const s = m.so;
  return (
    <tr className={chon ? "cp-chon" : "cp-tat"} title={m.ly}
      onClick={e => { if (!(e.target as HTMLElement).closest("a, input")) bat(m.ma); }}>
      <td><input type="checkbox" checked={chon} onChange={() => bat(m.ma)} aria-label={`Chọn ${m.ma}`} /></td>
      <td><span className="cp-ma-o"><HinhMa ma={m.ma} ten={m.ten} co={32} trang_tri />
        <span className="cp-ma"><a href={giuKhoang(`/san-pham/${encodeURIComponent(m.ma)}`)}><code>{m.ma}</code></a>
          <span className="ten-jp">{m.ten}</span>
          {s?.ngan && <span className="cp-ngan">{s.ngan}</span>}</span></span></td>
      {!s ? <td colSpan={5} className="cp-ly">{m.ly}</td> : <>
        <td className="so">{s.ngay == null ? "—" :
          <span className="cp-con" title={s.ton != null ? `đầu tuần ~${so(s.ton)} thùng` : undefined}>
            <span className="cp-thanh" aria-hidden="true"><i className={s.ngay < 14 ? "do" : s.ngay <= 30 ? "canh" : "ok"}
              style={{ width: `${Math.min(100, s.ngay / 90 * 100)}%` }} /></span>
            {s.ngay >= 999 ? "rất lâu" : `${so(s.ngay)} ngày`}</span>}</td>
        <td className="cp-lo">
          {s.lo && <div>{md(s.lo.ngay)} · {so(s.lo.sl)} thùng{s.lo.tt && <span className="cp-tt ten-jp">{s.lo.tt}</span>}</div>}
          {s.han && <div>hạn {hanNgan(s.han.ngay)} · ~{so(s.han.sl)} thùng <span className="cp-tt do">không kịp bán</span></div>}
          {s.canh && <div className="cp-canh">⚠ {s.canh}</div>}
          {s.ngung && <div><span className="cp-tt">※終売※ bán nốt tồn</span></div>}</td>
        <td className="so">{s.bien == null ? "—" : pc(s.bien, 0)}</td>
        <td className="so">{s.lai == null ? "—" : <span className={s.lai < 0 ? "giam" : s.uoc ? "phu" : undefined}
          title={s.uoc ? "ước — chưa đủ 2 lần sale đo được" : `lời ${s.lan_loi ?? "?"}/${s.tuan_do} lần sale`
            + (s.on_dinh === "" ? " — lúc lời lúc lỗ, chưa chắc" : "")}>
          {s.uoc ? "~" : ""}{s.lai >= 0 ? "+" : ""}{gon(s.lai)}</span>}
          {!s.uoc && s.tuan_do != null && s.lai != null && <small className="phu"> {s.lan_loi != null ? `${s.lan_loi}/` : ""}{s.tuan_do}
            {s.on_dinh === "" && " chưa chắc"}</small>}</td>
        <td>{s.mua == null ? null : s.mua < 0.2
          ? <span className="cp-mua thap" title="cùng kỳ năm trước gần như không bán (có thể khi đó hết hàng)">≈0</span>
          : <span className={"cp-mua " + (s.mua >= 1 ? "cao" : "thap")} title={`cùng kỳ năm trước bán ×${s.mua} bình thường`}>
            {s.mua >= 1 ? "▲" : "▼"}×{s.mua}</span>}</td></>}
      {co_sheet && <td>{sh && <span className={"cp-sh " + sh} title={KY_SHEET[sh][1]}>{KY_SHEET[sh][0]}</span>}</td>}
    </tr>
  );
}

const MAU_PD: Record<string, string> = { "THIẾU HÀNG": "do", "PHỤ THUỘC LÔ CHƯA CHỐT": "canh", "?": "nhat" };

function SoatNgay({ s }: { s: Soat }) {
  const hom_nay = new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });
  return <>
    <section className="kh-the cp-muc">
      <h2>Lịch hàng về thay đổi <small>từ lần soát trước ({s.lan_truoc ? s.lan_truoc.replace("T", " ") : "—"}): {s.lich_doi.length}</small></h2>
      {s.lich_doi.length ? <ul className="cp-ds-gon">{s.lich_doi.map((x, i) => (
        <li key={i}><span className="nhan-vien canh">{x.kieu}</span> {md(x.ngay)} [{x.trang_thai}] <span className="ten-jp">{x.tieu_de}</span>
          {x.truoc != null && <span className="phu"> (trước: {x.truoc})</span>}
          {x.ma.length > 0 && <div className="phu">→ mã trong kế hoạch bị ảnh hưởng: {x.ma.join(", ")}</div>}</li>))}</ul>
        : <p className="phu">Không có gì đổi.</p>}
    </section>

    <section className="kh-the cp-muc">
      <h2>Kế hoạch cần xem lại <small>★ = mới phát sinh từ lần soát trước</small></h2>
      {s.tuan.map(t => (
        <div key={t.tu} className="cp-nhom">
          <div className="cp-nhom-ten"><b>Tuần {md(t.tu)}–{md(t.den)}</b> ({t.tu <= hom_nay ? "đang chạy" : `bắt đầu ${md(t.tu)}`}): {t.so_ma} mã,{" "}
            {t.dong.length ? <b className="giam">{t.dong.length} cần xem</b> : <span className="tang">đủ hàng hết</span>}</div>
          {t.dong.length > 0 && <ul className="cp-ds-gon">{t.dong.map(x => (
            <li key={x.ma}><span className="cp-sao" aria-label={x.moi ? "mới" : undefined}>{x.moi ? "★" : ""}</span>
              <HinhMa ma={x.ma} ten={x.ten} co={24} trang_tri /> <code>{x.ma}</code>{" "}
              <span className={"nhan-vien " + (MAU_PD[x.pd] ?? "nhat")}>{x.pd === "?" ? "chưa rõ tồn" : x.pd.toLowerCase()}</span>{" "}
              {x.ly}</li>))}</ul>}
        </div>))}
      {!s.tuan.length && <p className="phu">Sheet chưa có tuần nào từ hôm nay trở đi.</p>}
    </section>

    {s.goi_y.length > 0 && <section className="kh-the cp-muc">
      <h2>Gợi ý <small>sắp hết, có lô về trong 21 ngày, chưa có trong kế hoạch 2 tuần tới</small></h2>
      <ul className="cp-ds-gon">{s.goi_y.map(x => (
        <li key={x.ma}><HinhMa ma={x.ma} ten={x.ten} co={24} trang_tri /> <code>{x.ma}</code> còn ~{so(x.ton)} thùng (~{so(x.con_ngay)} ngày bán) ·
          lô {md(x.lo_ngay)} {so(x.lo_sl)} thùng [{x.trang_thai}] · <b>{x.cach}</b> <span className="ten-jp phu">{x.ten}</span></li>))}</ul>
    </section>}

    <section className="kh-the cp-muc">
      <h2>Lô đã qua ngày về mà OBC chưa nhập kho <small>tính như về hôm nay — kiểm lại nếu thật ra bị trễ: {s.lo_qua_han.length}</small></h2>
      <BangLo ds={s.lo_qua_han} />
      <h2>Ngày hàng về lệch giữa OBC (<span className="ten-jp">入荷更新</span>) và Cybozu <small>tính theo ngày Cybozu: {s.lo_lech.length}</small></h2>
      <BangLo ds={s.lo_lech} lech />
      {s.khong_cybozu.length > 0 && <p className="phu">Không tìm thấy container trên Cybozu — coi là chưa chắc:{" "}
        {s.khong_cybozu.map(x => `${x.ma} ${md(x.ngay)}`).join(", ")}</p>}
    </section>
  </>;
}

function BangLo({ ds, lech }: { ds: Soat["lo_lech"]; lech?: boolean }) {
  if (!ds.length) return <p className="phu">Không có.</p>;
  return (
    <div className="bang-cuon"><table className="bang">
      <thead><tr><th>Mã</th><th className="so">Thùng</th>{lech && <th>OBC</th>}<th>{lech ? "Cybozu" : "Ngày"}</th><th>Trạng thái</th><th>Container</th></tr></thead>
      <tbody>{ds.map((x, i) => (
        <tr key={i}><td><code>{x.ma}</code></td><td className="so">{so(x.sl)}</td>{lech && <td>{md(x.ngay_obc)}</td>}
          <td>{md(x.ngay)}</td><td>{x.trang_thai}</td><td className="ten-jp">{x.cybozu}</td></tr>))}</tbody>
    </table></div>
  );
}
