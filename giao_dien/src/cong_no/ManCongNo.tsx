// Màn "Công nợ & thu tiền" (Công nợ.dc.html) — đợt 6. Số THẬT từ /api/cong-no
// (kome/cong_no.py -> mart.cong_no_*, migration 038): MỘT ảnh chụp, lọc / tìm ở
// trình duyệt.
//
// Lệch gói thiết kế CÓ CHỦ Ý, và màn nói ra:
// - Đơn vị là PHIẾU BÁN của sổ 請求先元帳, không phải "hoá đơn INV-…" — OBC không
//   xuất số hoá đơn. Phần còn nợ từng phiếu là phép chia "trả cũ trước".
// - Không nút "Ghi nhận thu": thu tiền ghi trong OBC (luật số một), nạp lại sổ là
//   màn tự cập nhật. Không nút "Gửi nhắc thu": chưa có kênh gửi nào.
// - "Vượt hạn mức tín dụng": OBC không xuất hạn mức — khung "chưa có dữ liệu".
// - Mốc là CUỐI KỲ của sổ mới nhất, không phải hôm nay (sổ nạp theo quý).
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { lay } from "../api";
import { giuKhoang } from "../khung/khoang";
import { ChuaCoDuLieu } from "../chung/Khoi";
import { gon, ngay, ngay_ngan, pc, so, yen } from "../dinh_dang";
import { nhanHan, type Ben, type CongNoApi, type Phieu } from "./kieu";
import "../san_pham/san_pham.css";
import "./cong_no.css";

type Tab = "tat_ca" | "qua_han" | "sap" | "khong_han" | "ben";
const TAB: [Tab, string][] = [["tat_ca", "Tất cả phiếu còn nợ"], ["qua_han", "Quá hạn"], ["sap", "Sắp đến hạn"],
  ["khong_han", "Không suy được hạn"], ["ben", "Theo bên nhận hoá đơn"]];
const MAU_TUOI: Record<string, string> = { d30: "ok", d60: "canh", d90: "canh", d90p: "do", truoc_ky: "do" };
const TOI_DA = 300;

function docUrl() {
  const q = new URLSearchParams(location.search);
  const t = q.get("tab") as Tab | null;
  return { tab: (t && TAB.some(x => x[0] === t) ? t : "tat_ca") as Tab, nhom: q.get("nhom") ?? "", tim: q.get("tim") ?? "" };
}

function khop(p: { ten: string; ma: string; so?: string | null }, tim: string) {
  const t = tim.trim().toLowerCase();
  return !t || (p.ten + " " + p.ma + " " + (p.so ?? "")).toLowerCase().includes(t);
}

export default function ManCongNo() {
  const [b, datB] = useState(docUrl);
  const [tim, datTim] = useState(b.tim);
  const dat = (s: Partial<typeof b>) => {
    const bb = { ...b, ...s }; datB(bb);
    const q = new URLSearchParams();
    if (bb.tab !== "tat_ca") q.set("tab", bb.tab);
    if (bb.nhom) q.set("nhom", bb.nhom);
    if (bb.tim.trim()) q.set("tim", bb.tim.trim());
    history.replaceState(null, "", giuKhoang("/cong-no" + (q.toString() ? "?" + q : "")));
  };
  useEffect(() => { const h = setTimeout(() => { if (tim !== b.tim) dat({ tim }); }, 150); return () => clearTimeout(h); }, [tim]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { document.title = "KOME — công nợ"; }, []);

  const { data: d, error } = useQuery<CongNoApi>({ queryKey: ["cong-no"], queryFn: () => lay<CongNoApi>("/api/cong-no") });
  const benTheoMa = useMemo(() => new Map((d?.ben ?? []).map(x => [x.ma, x])), [d]);
  const quaHanBen = useMemo(() => {
    const m = new Map<string, number>();
    for (const p of d?.phieu ?? []) if ((p.qua_han ?? 0) > 0) m.set(p.ma, (m.get(p.ma) ?? 0) + p.con_lai);
    return m;
  }, [d]);
  const ten = (ma: string) => benTheoMa.get(ma)?.ten || ma;
  const sap = d?.sap_den_han_ngay ?? 7;

  const phieu = useMemo(() => (d?.phieu ?? []).filter(p => {
    if (b.nhom && p.nhom !== b.nhom) return false;
    if (b.tab === "qua_han" && !((p.qua_han ?? 0) > 0)) return false;
    if (b.tab === "sap" && !(p.qua_han != null && p.qua_han <= 0 && p.qua_han >= -sap)) return false;
    if (b.tab === "khong_han" && p.qua_han != null) return false;
    return khop({ ten: ten(p.ma), ma: p.ma, so: p.so }, b.tim);
  }), [d, b, sap]); // eslint-disable-line react-hooks/exhaustive-deps
  const ben = useMemo(() => (d?.ben ?? []).filter(x => khop({ ten: x.ten ?? "", ma: x.ma }, b.tim)), [d, b.tim]);

  if (error) return <div className="sp"><h1>Công nợ &amp; thu tiền</h1><div className="khoi-loi">Không tải được sổ công nợ: {(error as Error).message}</div></div>;
  if (!d) return <div className="sp"><h1>Công nợ &amp; thu tiền</h1><div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></div>;
  if (!d.co_du_lieu) return (
    <div className="sp"><div className="tieu-de-trang"><div><h1>Công nợ &amp; thu tiền</h1></div></div>
      <ChuaCoDuLieu tieu_de="Sổ công nợ" ly_do="Chưa nạp sổ 請求先元帳 nào. Xuất 請求先元帳 từ OBC (cả kỳ, tên file giữ nguyên) rồi kéo–thả vào màn Kho dữ liệu." /></div>);

  const tq = d.tq;
  const maxTuoi = Math.max(1, ...tq.tuoi.map(t => t.tien));
  const tongLoc = phieu.reduce((s, p) => s + p.con_lai, 0);
  const lich = d.phieu.filter(p => p.qua_han != null && p.qua_han <= 0 && p.qua_han >= -sap)
    .sort((x, y) => (x.han ?? "").localeCompare(y.han ?? "")).slice(0, 8);

  const xuatCsv = () => {
    const cot = ["Mã bên nhận HĐ", "Tên", "Điều kiện", "Số phiếu", "Ngày phiếu", "Tổng phiếu", "Đã thu (ước)", "Còn lại", "Hạn (suy)", "Quá hạn (ngày)", "Tuổi (ngày)"];
    const hang = phieu.map(p => { const x = benTheoMa.get(p.ma); return [p.ma, x?.ten ?? "", x?.dieu_kien ?? "", p.so ?? "(mang sang trước kỳ)",
      p.ngay ?? "", p.tong ?? "", p.da_thu ?? "", p.con_lai, p.han ?? "", p.qua_han ?? "", p.tuoi ?? ""]; });
    const csv = "﻿" + [cot, ...hang].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = `cong-no-${d.moc}.csv`; a.click(); URL.revokeObjectURL(a.href);
  };

  return (
    <div className="sp cn">
      <div className="tieu-de-trang">
        <div><h1>Công nợ &amp; thu tiền</h1>
          <div className="phu">Ai còn nợ, nợ bao lâu — tính đến <b>{ngay(d.moc)}</b>, cuối kỳ sổ <b className="ten-jp">請求先元帳</b> mới nhất
            ({ngay(d.ky_tu)} → {ngay(d.moc)}). Thu sau ngày đó chưa có ở đây cho tới khi nạp sổ kỳ sau.</div></div>
        <div className="sp-dau-phai">
          <button type="button" className="nut-nho" onClick={xuatCsv} disabled={!phieu.length || b.tab === "ben"} title="Xuất đúng các phiếu đang hiện (theo tab, cột tuổi và ô tìm)">⤓ Xuất CSV</button>
          <button type="button" className="nut-nho" disabled title="Chưa có kênh gửi nhắc thu nào — gọi khách rồi ghi tiếp xúc ở hồ sơ khách.">Gửi nhắc thu</button>
        </div>
      </div>

      <div className="o-kpi-luoi sp-kpi">
        <div className="o-kpi"><div className="nhan">Tổng phải thu</div><div className="gia">{gon(tq.tong_phai_thu)}</div>
          <div className="dong-phu nhat-chu">{so(tq.so_ben_no)} bên nhận hoá đơn còn dư nợ</div></div>
        <button type="button" className="o-kpi sp-kpi-nut" aria-pressed={b.tab === "qua_han"} onClick={() => dat({ tab: b.tab === "qua_han" ? "tat_ca" : "qua_han" })}>
          <div className="nhan">Quá hạn</div><div className={"gia" + (tq.qua_han ? " giam" : "")}>{gon(tq.qua_han)}</div>
          <div className="dong-phu nhat-chu">{so(tq.so_phieu_qua_han)} phiếu · {so(tq.so_ben_qua_han)} bên · {pc(tq.tong_phai_thu ? tq.qua_han / tq.tong_phai_thu : null, 0)} tổng nợ</div></button>
        <button type="button" className="o-kpi sp-kpi-nut" aria-pressed={b.tab === "sap"} onClick={() => dat({ tab: b.tab === "sap" ? "tat_ca" : "sap" })}>
          <div className="nhan">Đến hạn trong {sap} ngày sau mốc</div><div className={"gia" + (tq.sap_den_han ? " canh-chu" : "")}>{gon(tq.sap_den_han)}</div>
          <div className="dong-phu nhat-chu">{so(tq.so_phieu_sap)} phiếu cần theo</div></button>
        <button type="button" className="o-kpi sp-kpi-nut" aria-pressed={b.tab === "khong_han"} onClick={() => dat({ tab: b.tab === "khong_han" ? "tat_ca" : "khong_han" })}>
          <div className="nhan">Không suy được hạn</div><div className="gia">{gon(tq.khong_suy_han)}</div>
          <div className="dong-phu nhat-chu">代引 · その都度 · 前払い … — không tính là quá hạn</div></button>
        <div className="o-kpi"><div className="nhan">Đã thu trong kỳ</div><div className="gia ok-chu">{gon(tq.da_thu_ky)}</div>
          <div className="dong-phu nhat-chu">bán chịu trong kỳ {gon(tq.ban_chiu_ky)}</div></div>
        <div className="o-kpi"><div className="nhan">Khách trả dư</div><div className="gia">{gon(-tq.tra_du)}</div>
          <div className="dong-phu nhat-chu">{so(tq.so_ben_tra_du)} bên có số dư âm</div></div>
      </div>

      <div className="kho-hai-cot">
        <div className="kho-chinh cn-chinh">
          <section className="kh-the">
            <div className="sp-dm-dau"><h2>Tuổi nợ</h2><span className="phu">bấm một cột để lọc bảng · tuổi đếm từ ngày phiếu tới mốc</span>
              <span className="phu">tổng {yen(tq.tong_phai_thu)}</span></div>
            <div className="cn-tuoi">
              {tq.tuoi.map(t => (
                <button key={t.nhom} type="button" className="cn-o-tuoi" aria-pressed={b.nhom === t.nhom}
                  onClick={() => dat({ nhom: b.nhom === t.nhom ? "" : t.nhom, tab: b.tab === "ben" ? "tat_ca" : b.tab })}>
                  <div className="phu">{t.nhan}</div>
                  <div className={"cn-tien " + (MAU_TUOI[t.nhom] ?? "")}>{gon(t.tien)}</div>
                  <div className="kho-du-thanh cn-thanh"><i className={MAU_TUOI[t.nhom] === "do" ? "giam" : MAU_TUOI[t.nhom] === "canh" ? "canh-chu" : ""}
                    style={{ width: `${Math.max(2, t.tien / maxTuoi * 100)}%` }} /></div>
                  <div className="phu">{t.nhom === "truoc_ky" ? "không rõ phiếu" : `${so(t.dem)} phiếu`} · {pc(tq.tong_phai_thu ? t.tien / tq.tong_phai_thu : null, 0)}</div>
                </button>))}
            </div>
          </section>

          <section className="kh-the">
            <div className="sp-dm-dau">
              <div className="kho-tab cn-tab" role="tablist">
                {TAB.map(([t, nhan]) => <button key={t} type="button" role="tab" aria-selected={b.tab === t} onClick={() => dat({ tab: t })}>{nhan}</button>)}
              </div>
              <input type="search" className="kh-tim sp-tim" placeholder="Tìm tên, mã bên hoặc số phiếu…" value={tim}
                onChange={e => datTim(e.target.value)} aria-label="Tìm trong sổ công nợ" />
            </div>
            {b.nhom && b.tab !== "ben" && <p className="phu sp-ghi">Đang lọc tuổi nợ: <b>{tq.tuoi.find(t => t.nhom === b.nhom)?.nhan}</b> ·{" "}
              <button type="button" className="nut-chu" onClick={() => dat({ nhom: "" })}>bỏ lọc</button></p>}
            {b.tab === "ben" ? <BangBen ben={ben} quaHan={quaHanBen} chon={ma => { datTim(ma); dat({ tab: "tat_ca", tim: ma }); }} />
              : <BangPhieu phieu={phieu} ben={benTheoMa} />}
            <p className="phu sp-ghi">{b.tab === "ben"
              ? `${so(ben.length)} bên · tổng số dư ${yen(ben.reduce((s, x) => s + x.so_du, 0))}`
              : `${so(phieu.length)} phiếu${phieu.length > TOI_DA ? ` (hiện ${TOI_DA} đầu — tìm để thu hẹp)` : ""} · tổng còn lại ${yen(tongLoc)}`
                + (b.tim.trim() ? ` · đang tìm “${b.tim.trim()}”` : "")}</p>
            <p className="phu sp-ghi">{d.cach_tinh.fifo} {d.cach_tinh.han}</p>
          </section>
        </div>

        <aside className="kho-ben">
          <ChuaCoDuLieu tieu_de="Vượt hạn mức tín dụng" ly_do="OBC không xuất hạn mức tín dụng của khách trong file nào ta nạp — chưa có nguồn." />
          <section className="kh-the">
            <h2>Lịch thu {sap} ngày sau mốc</h2>
            <p className="phu">theo hạn suy từ điều kiện thanh toán</p>
            {lich.length ? <div className="cn-lich">{lich.map((p, i) => (
              <a key={i} className="cn-lich-dong" href={`/khach-hang/${encodeURIComponent(p.ma)}`}>
                <b>{p.han ? ngay_ngan(p.han) : "—"}</b>
                <span><span className="ten-jp">{ten(p.ma)}</span><span className="phu">phiếu {p.so}</span></span>
                <span className="so">{yen(p.con_lai)}</span></a>))}</div>
              : <p className="trong-nho">Không phiếu nào đến hạn trong {sap} ngày sau {ngay(d.moc)}.</p>}
          </section>
          <section className="kh-the cn-viec">
            <h2>Việc nên làm</h2>
            {d.viec.length ? <ul>{d.viec.map((v, i) => <li key={i}>{v}</li>)}</ul> : <p className="trong-nho">Không có gì nổi bật.</p>}
          </section>
          <section className="kh-the">
            <h2>Cách tính</h2>
            <ul className="cn-cach">{Object.values(d.cach_tinh).map((c, i) => <li key={i} className="phu">{c}</li>)}</ul>
            <p className="phu">Không có nút "Ghi nhận thu": tiền thu ghi trong OBC (sổ cái chính thức), nạp lại 請求先元帳 là màn này tự cập nhật.</p>
          </section>
        </aside>
      </div>
    </div>
  );
}

function BangPhieu({ phieu, ben }: { phieu: Phieu[]; ben: Map<string, Ben> }) {
  if (!phieu.length) return <p className="trong-nho">Không phiếu nào khớp bộ lọc.</p>;
  return (
    <div className="sp-bang-khung"><table className="bang cn-bang">
      <thead><tr><th>Số phiếu</th><th>Bên nhận hoá đơn</th><th>Ngày · hạn</th><th className="so">Tổng phiếu</th>
        <th className="so">Đã thu (ước)</th><th className="so">Còn lại</th><th>Tuổi nợ</th><th>Phụ trách</th></tr></thead>
      <tbody>{phieu.slice(0, TOI_DA).map((p, i) => {
        const x = ben.get(p.ma); const [nhan, mau] = nhanHan(p);
        return (
          <tr key={p.ma + (p.so ?? "_") + i}>
            <td><code>{p.so ?? "—"}</code>{p.loai === "truoc_ky" && <div className="ma-nho">nợ mang sang trước kỳ</div>}</td>
            <td className="sp-ten"><a href={`/khach-hang/${encodeURIComponent(p.ma)}`} className="ten-jp">{x?.ten ?? p.ma}</a>
              <div className="ma-nho">{p.ma} · <span className="ten-jp">{x?.dieu_kien ?? "—"}</span>{x && x.so_khach > 1 ? ` · ${x.so_khach} khách dùng chung` : ""}</div></td>
            <td className="nhat-chu">{p.ngay ? ngay(p.ngay) : "trước kỳ"}<div className="ma-nho">{p.han ? `hạn ${ngay(p.han)}` : "không suy được hạn"}</div></td>
            <td className="so">{yen(p.tong)}</td><td className="so nhat-chu">{p.da_thu ? yen(p.da_thu) : "—"}</td>
            <td className="so"><b>{yen(p.con_lai)}</b></td>
            <td><span className={"nhan-vien " + mau}>{nhan}</span></td>
            <td className="nhat-chu">{x?.ten_sale ?? (x?.sale ? `(mã ${x.sale})` : "—")}</td>
          </tr>);
      })}</tbody>
    </table></div>);
}

function BangBen({ ben, quaHan, chon }: { ben: Ben[]; quaHan: Map<string, number>; chon: (ma: string) => void }) {
  if (!ben.length) return <p className="trong-nho">Không bên nào khớp ô tìm.</p>;
  return (
    <div className="sp-bang-khung"><table className="bang cn-bang">
      <thead><tr><th>Bên nhận hoá đơn</th><th>Điều kiện</th><th className="so">Mang sang</th><th className="so">Bán chịu kỳ</th>
        <th className="so">Đã thu kỳ</th><th className="so">Số dư</th><th className="so">Quá hạn</th><th>Thu lần cuối</th><th>Phụ trách</th></tr></thead>
      <tbody>{ben.map(x => (
        <tr key={x.ma} className="sp-dong" onClick={() => chon(x.ma)} title="Bấm để xem các phiếu còn nợ của bên này">
          <td className="sp-ten"><a href={`/khach-hang/${encodeURIComponent(x.ma)}`} className="ten-jp" onClick={e => e.stopPropagation()}>{x.ten ?? x.ma}</a>
            <div className="ma-nho">{x.ma}{x.so_khach ? ` · ${x.so_khach} khách` : ""}</div></td>
          <td className="ten-jp nhat-chu">{x.dieu_kien ?? "—"}</td>
          <td className="so nhat-chu">{yen(x.mang_sang)}</td><td className="so">{yen(x.ban_chiu)}</td><td className="so">{yen(x.da_thu)}</td>
          <td className={"so" + (x.so_du < 0 ? " ok-chu" : "")}><b>{yen(x.so_du)}</b>{x.so_du < 0 && <div className="ma-nho">trả dư</div>}</td>
          <td className={"so" + (quaHan.get(x.ma) ? " giam" : " nhat-chu")}>{quaHan.get(x.ma) ? yen(quaHan.get(x.ma)) : "—"}</td>
          <td className="nhat-chu">{x.lan_thu_cuoi ? ngay(x.lan_thu_cuoi) : "trong kỳ chưa thu"}</td>
          <td className="nhat-chu">{x.ten_sale ?? (x.sale ? `(mã ${x.sale})` : "—")}</td>
        </tr>))}</tbody>
    </table></div>);
}
