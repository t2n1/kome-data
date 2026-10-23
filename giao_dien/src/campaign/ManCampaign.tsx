// Campaign tuần (/campaign, 074). Bản kế hoạch + soát do máy công ty lập (Google Sheet + Cybozu chỉ đọc được từ đó) và
// gửi lên — web KHÔNG tính gì: nhóm, lý do, phán định là của script. Ô tick chỉ đổi phần sẽ chép, không lưu (sheet
// キャンペーン管理シート vẫn là bản chính thức cho sếp xem). Đặc tả: 2026-10-23-campaign-tuan-design.md.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { lay } from "../api";
import { giuKhoang } from "../khung/khoang";
import { HinhMa } from "../chung/HinhMa";
import { so } from "../dinh_dang";
import { chepAB, chepF, chepGia, CU_GIO, gioTu, macDinh, md, NHOM, soSheet, theoNhom, theoSheet, thieuDong } from "./chep";
import type { BanCampaign, CampaignApi, MaKeHoach, Soat, TuanKeHoach } from "./kieu";
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
  if (!b.ke_hoach.length) return <p className="cp-ghi">Bản này chưa có tuần nào.</p>;
  return <>
    <p className="cp-ghi">Đề xuất từ tuần sau. Tuần đã có trên sheet được đề xuất lại theo nhịp của sheet (khác sheet chỉ vì tồn, lô về,
      lãi gộp) kèm so sánh thêm / bỏ. Trong mỗi nhóm, mã xếp theo lãi gộp thêm một tuần sale × mùa cùng kỳ năm trước. Mỗi tuần: bỏ / thêm mã bằng ô tick, rồi bấm chép và dán vào sheet. Tab tháng: dán <b>cột A–B</b> và <b>cột F</b> vào
      các dòng ngay dưới dòng <span className="ten-jp">合計</span> của tuần (không dán đè cột C–E — công thức).
      <span className="ten-jp"> 値段管理</span>: dán vào cột của tuần, bắt đầu ở <b>dòng 3</b>. Lựa chọn không được lưu — tải lại trang là về đề xuất.</p>
    {b.ke_hoach.map(t => <KhoiTuan key={t.tu} t={t} thu_tu={b.thu_tu_gia} />)}
  </>;
}

function KhoiTuan({ t, thu_tu }: { t: TuanKeHoach; thu_tu: string[] }) {
  const [chon, datChon] = useState<Set<string>>(() => macDinh(t));
  const [bao, datBao] = useState("");
  const nhom = theoNhom(t.ma);
  const thieu = thieuDong(thu_tu, chon);
  const ss = soSheet(t, chon);
  const bat = (ma: string) => datChon(c => { const n = new Set(c); if (n.has(ma)) n.delete(ma); else n.add(ma); return n; });
  const chep = async (ten: string, van: string) => {
    try { await navigator.clipboard.writeText(van); datBao(`Đã chép ${ten}.`); }
    catch { window.prompt(`Chép ${ten}:`, van); }
    setTimeout(() => datBao(""), 2500);
  };
  return (
    <section className="kh-the cp-tuan" aria-label={`Tuần ${t.ky}`}>
      <div className="cp-tuan-dau">
        <h2>Tuần {t.ky} <small>tab <span className="ten-jp">{t.tab}</span> · <span className="ten-jp">週目</span> {t.tuan_so}</small></h2>
        <b>{so(chon.size)} mã</b>
      </div>
      <div className="cp-nut">
        <button type="button" className="nut-chinh" onClick={() => chep("cột A–B", chepAB(t, chon))}>Chép cột A–B (<span className="ten-jp">週目 · 期間</span>)</button>
        <button type="button" className="nut-chinh" onClick={() => chep("cột F", chepF(chon))}>Chép cột F (<span className="ten-jp">商品コード</span>)</button>
        <button type="button" className="nut-chinh" onClick={() => chep("cột 値段管理", chepGia(thu_tu, chon))}>Chép cột <span className="ten-jp">値段管理</span></button>
        <button type="button" className="nut-nap" onClick={() => datChon(macDinh(t))}>Về đề xuất</button>
        {t.tren_sheet && <button type="button" className="nut-nap" onClick={() => datChon(theoSheet(t))}>Chọn theo sheet</button>}
        <span className="cp-bao" role="status">{bao}</span>
      </div>
      {ss && <p className="cp-sheet">Sheet đã có tuần này ({so(t.tren_sheet!.length)} mã). So với phần đang chọn:{" "}
        {!ss.them.length && !ss.bo.length ? <b>khớp sheet</b> : <>
          <b className="tang">thêm {ss.them.length}</b>{ss.them.length > 0 && `: ${ss.them.join(", ")}`} ·{" "}
          <b className="giam">bỏ {ss.bo.length}</b>{ss.bo.length > 0 && `: ${ss.bo.join(", ")}`}</>}</p>}
      {thieu.length > 0 && <p className="cp-cu">Chưa có dòng trên <span className="ten-jp">値段管理</span> (cột tuần sẽ thiếu): {thieu.join(", ")}</p>}
      {NHOM.map(n => {
        const ds = nhom.get(n.ma) ?? [];
        if (!ds.length) return null;
        const so_chon = ds.filter(m => chon.has(m.ma)).length;
        const tieu_de = <><b>{n.nhan}</b> · {ds.length} mã{n.gap && so_chon ? ` (đang chọn ${so_chon})` : ""} <span className="phu">— {n.giai}</span></>;
        const bang = <ul className="cp-ds">{ds.map(m => <DongMa key={m.ma} m={m} chon={chon.has(m.ma)} bat={bat} />)}</ul>;
        return n.gap
          ? <details key={n.ma} className="cp-nhom"><summary>{tieu_de}</summary>{bang}</details>
          : <div key={n.ma} className="cp-nhom"><div className="cp-nhom-ten">{tieu_de}</div>{bang}</div>;
      })}
    </section>
  );
}

function DongMa({ m, chon, bat }: { m: MaKeHoach; chon: boolean; bat: (ma: string) => void }) {
  return (
    <li className={chon ? "cp-chon" : undefined}>
      <label>
        <input type="checkbox" checked={chon} onChange={() => bat(m.ma)} />
        <HinhMa ma={m.ma} ten={m.ten} co={32} trang_tri />
        <span className="cp-ma"><a href={giuKhoang(`/san-pham/${encodeURIComponent(m.ma)}`)}><code>{m.ma}</code></a>
          <span className="ten-jp">{m.ten}</span>
          {m.tren_sheet && <span className="nhan-vien lam">trên sheet</span>}</span>
        <span className="cp-ly">{m.ly}</span>
      </label>
    </li>
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
