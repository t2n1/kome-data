// Bảng giá KOME (/bang-gia, 071): mọi mã × quy cách × 売価No. của lần nạp 取引単価データ mới nhất, kèm lần nạp trước.
// CHỈ XEM — giá là dữ liệu OBC (luật số một): sửa trong OBC rồi nạp lại. Một ảnh chụp /api/bang-gia; lọc ở trình
// duyệt (loc.ts). Mọi cờ ô (đổi / dưới giá vốn / hai cột lệch) là của máy chủ — màn chỉ tô.
import { useQuery } from "@tanstack/react-query";
import { Fragment, useEffect, useMemo, useState } from "react";
import { lay } from "../api";
import { giuKhoang } from "../khung/khoang";
import { ngay, so, yen } from "../dinh_dang";
import type { BangGiaApi, DongGia, MaGia } from "./kieu";
import { chuoiLocBg, CO, coCua, docLocBg, giaiO, locBangGia } from "./loc";
import type { LocBg } from "./loc";
import "./bang_gia.css";

export default function ManBangGia() {
  const { data: d, error } = useQuery<BangGiaApi>({ queryKey: ["bang-gia"], queryFn: () => lay<BangGiaApi>("/api/bang-gia") });
  const [b, datB] = useState<LocBg>(() => docLocBg(location.search));
  const [tim, datTim] = useState(b.tim);

  useEffect(() => {
    const f = () => datB(docLocBg(location.search));
    addEventListener("popstate", f); return () => removeEventListener("popstate", f);
  }, []);
  const dat = (sua: Partial<LocBg>) => {
    const bb = { ...b, ...sua }; datB(bb);
    const q = chuoiLocBg(bb);
    const url = giuKhoang("/bang-gia" + (q ? "?" + q : ""));
    if (url !== location.pathname + location.search) history.replaceState(null, "", url);
  };
  useEffect(() => { const h = setTimeout(() => { if (tim !== b.tim) dat({ tim }); }, 200); return () => clearTimeout(h); }, [tim]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { document.title = "KOME — bảng giá"; }, []);
  const kq = useMemo(() => d ? locBangGia(d.ma, b) : null, [d, b]);

  if (error) return <div className="bg"><h1>Bảng giá KOME</h1><div className="khoi-loi">Không tải được bảng giá: {(error as Error).message}</div></div>;
  if (!d || !kq) return <div className="bg"><h1>Bảng giá KOME</h1><div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></div>;

  const coGia = d.ma.filter(m => !coCua(m).has("chua_co")).length;
  const coStd = d.bac.some(x => x.ma === "std");

  return (
    <div className="bg">
      <div className="tieu-de-trang">
        <div><h1>Bảng giá KOME</h1>
          <div className="phu">{so(coGia)}/{so(d.ma.length)} mã có giá · lần nạp 取引単価データ mới nhất {ngay(d.moi_nhat)} · giá <b>chưa thuế</b></div></div>
      </div>
      <p className="bg-chi-xem" role="note">Trang này <b>chỉ để xem</b>. Giá là dữ liệu của OBC: muốn đổi giá thì sửa trong OBC rồi
        xuất lại <span className="ten-jp">取引単価データ</span> và nạp ở <a href="/kho-du-lieu">Kho dữ liệu › Nạp</a>.
        {!coStd && <> Chưa có cột <span className="ten-jp">標準価格</span> — file đã nạp là bản xuất cũ; xuất lại bản có cột đó để
          trang đối thủ so với giá chuẩn thay vì giá thực bán.</>}</p>

      <section className="kh-the">
        <div className="bg-dau">
          <input type="search" className="kh-tim" placeholder="Tìm mã, tên hàng, ngành…" value={tim}
            onChange={e => datTim(e.target.value)} aria-label="Tìm mã hàng" />
        </div>
        <div className="bg-chip" role="group" aria-label="Cần soát">
          <button type="button" className="chip" aria-pressed={!kq.co} onClick={() => dat({ co: "" })}>Tất cả ({so(kq.tong_co)})</button>
          {CO.map(c => (
            <button key={c.k} type="button" className={"chip bg-co-" + c.k} title={c.giai} aria-pressed={kq.co === c.k}
              onClick={() => dat({ co: kq.co === c.k ? "" : c.k })}>{c.nhan} ({so(kq.dem_co[c.k])})</button>))}
        </div>
        <div className="bg-chip" role="group" aria-label="Ngành hàng">
          <button type="button" className="chip" aria-pressed={!b.nganh} onClick={() => dat({ nganh: "" })}>Mọi ngành ({so(kq.tong_nganh)})</button>
          {kq.dem_nganh.map(([n, c]) => (
            <button key={n} type="button" className="chip ten-jp" aria-pressed={b.nganh === n} onClick={() => dat({ nganh: b.nganh === n ? "" : n })}>
              {n} ({so(c)})</button>))}
          {b.nganh && !kq.dem_nganh.some(([n]) => n === b.nganh) &&
            <button type="button" className="chip ten-jp" aria-pressed onClick={() => dat({ nganh: "" })}>{b.nganh} (0)</button>}
        </div>

        <div className="bang-cuon bg-khung">
          <table className="bang bg-bang">
            <thead><tr>
              <th>Mặt hàng</th><th>Quy cách</th>
              <th className="so" title="単位原価 của quy cách đó (lần nạp mới nhất)">Giá vốn</th>
              {d.bac.map(x => <th key={x.ma} className="so ten-jp">{x.nhan}</th>)}
              <th title="Ngày của lần nạp đang hiện · lần nạp trước (để so)">Từ ngày</th>
            </tr></thead>
            <tbody>
              {kq.hang.map(m => <Ma key={m.ma} m={m} bac={d.bac.map(x => x.ma)} />)}
              {!kq.hang.length && <tr><td colSpan={d.bac.length + 4} className="trong">Không có mã hàng nào khớp{b.tim ? ` với "${b.tim}"` : ""}. Thử bỏ bớt bộ lọc.</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="phu bg-ghi">{so(kq.hang.length)} mã đang hiện. <span className="bg-o-doi">Ô tô vàng</span> = đổi so với lần nạp
          trước (rê chuột xem giá cũ) · <s>gạch ngang</s> = bậc có ở lần trước mà nay không còn · <span className="bg-duoi">chữ đỏ</span> =
          dưới giá vốn · ⚠ = hai cột thuế mâu thuẫn (web lấy gồm thuế ÷ 1,08). <span className="ten-jp">売価No.10</span> là giá khuyến mãi.
          Danh sách mã giống màn Sản phẩm (bỏ phí, hàng tặng POSM, <span className="ten-jp">※終売※</span> đã hết tồn).</p>
      </section>
    </div>
  );
}

function Ma({ m, bac }: { m: MaGia; bac: string[] }) {
  const ten = (
    <td className="bg-ten" rowSpan={Math.max(1, m.dong.length)}>
      <a href={giuKhoang(`/san-pham/${encodeURIComponent(m.ma)}`)} className="ten-jp">{m.ten}</a>
      <div className="ma-nho"><code>{m.ma}</code> · <span className="ten-jp">{m.nganh}</span>
        {m.ngung_ban && <> · <span className="nhan-vien canh" title="Đã ngừng kinh doanh (※終売※) — chỉ còn bán nốt tồn">bán nốt tồn</span></>}
        {m.thieu_kg && <> · <span className="nhan-vien canh" title="Không biết kg mỗi gói / thùng — giá này không vào phần so với đối thủ. Sửa quy cách ở Thị trường & đối thủ › Giá KOME lệch">thiếu kg</span></>}
      </div></td>);
  if (!m.dong.length) return <tr className="bg-dau-ma">{ten}<td colSpan={bac.length + 3} className="nhat-chu">chưa có giá trong lần nạp mới nhất</td></tr>;
  return <>{m.dong.map((d, i) => <Dong key={d.qc} d={d} bac={bac} dau={i === 0 ? ten : null} />)}</>;
}

function Dong({ d, bac, dau }: { d: DongGia; bac: string[]; dau: React.ReactNode }) {
  return (
    <tr className={dau ? "bg-dau-ma" : undefined}>
      {dau}
      <td className="ten-jp bg-qc">{d.ten_qc}</td>
      <td className="so nhat-chu">{d.gia_von == null ? "—" : yen(d.gia_von)}</td>
      {bac.map(lv => {
        const o = d.g[lv];
        if (!o) return <td key={lv} />;
        const giai = [giaiO(o, d.tu, d.tu_truoc, yen, ngay), o.duoi && d.gia_von != null ? `Dưới giá vốn ${yen(d.gia_von)}` : "",
                      o.lech ? "Cột gồm thuế nhỏ hơn cột chưa thuế — web lấy gồm thuế ÷ 1,08" : ""].filter(Boolean).join(" · ");
        const cls = ["so", o.doi ? "bg-o-doi" : "", o.duoi ? "bg-duoi" : ""].filter(Boolean).join(" ");
        return (
          <td key={lv} className={cls} title={giai || undefined}>
            {o.bo ? <s className="nhat-chu">{yen(o.truoc)}</s> : <Fragment>
              {o.lech && <span aria-label="hai cột thuế mâu thuẫn">⚠ </span>}{yen(o.gia)}
              {o.doi && o.truoc != null && <span className="bg-mui" aria-hidden="true">{(o.gia ?? 0) > o.truoc ? " ▲" : " ▼"}</span>}
              {o.doi && o.truoc == null && d.tu_truoc && <span className="bg-mui"> mới</span>}
            </Fragment>}
          </td>);
      })}
      <td className="nhat-chu bg-ngay">{ngay(d.tu)}{d.tu_truoc && <div>trước: {ngay(d.tu_truoc)}</div>}</td>
    </tr>
  );
}
