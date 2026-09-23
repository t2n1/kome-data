// Màn "Kho hàng" (Kho hàng.dc.html): ba tab — Tồn hiện tại · Hàng đang về ·
// Cần đặt. Số THẬT từ /api/kho-hang?kho=&loc= (kome/san_pham.py::kho_hang, 2
// lượt hỏi): mỗi khối theo đúng những bộ lọc nó KHÔNG điều khiển (xem docstring
// kho_hang) — giao diện chỉ hiện, không lọc lại, trừ ô TÌM (lọc chữ trên các
// dòng đã về, chỉ cho bảng chính và ghi rõ điều đó).
//
// Tên kho đọc từ core.dim_warehouse (bẫy #6: gói thiết kế viết cứng
// Osaka/Nagoya — kho ảo). Không có mã lô trong 在庫一覧 nên bảng là "tồn theo
// dòng" (mã × kho × hạn), không phải "theo lô".
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { lay } from "../api";
import { ChuaCoDuLieu } from "../chung/Khoi";
import { gon, ngay, so, so_luong, yen } from "../dinh_dang";
import type { DongKho, KhoApi } from "./kieu";
import { khopTim } from "./loc";
import { useDanhMuc } from "./ManSanPham";
import "./san_pham.css";

type Tab = "ton" | "ve" | "can_dat";
type Loc = { tab: Tab; kho: string; loc: string; tim: string };

function docUrl(): Loc {
  const q = new URLSearchParams(location.search);
  const t = q.get("tab");
  return { tab: t === "ve" || t === "can_dat" ? t : "ton", kho: q.get("kho") ?? "", loc: q.get("loc") ?? "", tim: q.get("tim") ?? "" };
}
function ghiUrl(b: Loc) {
  const q = new URLSearchParams();
  if (b.tab !== "ton") q.set("tab", b.tab);
  if (b.kho) q.set("kho", b.kho);
  if (b.loc) q.set("loc", b.loc);
  if (b.tim.trim()) q.set("tim", b.tim.trim());
  const s = q.toString();
  history.replaceState(null, "", "/kho-hang" + (s ? "?" + s : ""));
}

const conHan = (d: { han_con_lai: number | null }) =>
  d.han_con_lai == null ? "—" : d.han_con_lai < 0 ? `quá ${-d.han_con_lai} ngày` : `còn ${d.han_con_lai} ngày`;

export default function KhoHang() {
  const [b, datB] = useState<Loc>(docUrl);
  const [tim, datTim] = useState(b.tim);
  const dat = (sua: Partial<Loc>) => { const bb = { ...b, ...sua }; datB(bb); ghiUrl(bb); };
  useEffect(() => { const h = setTimeout(() => { if (tim !== b.tim) dat({ tim }); }, 150); return () => clearTimeout(h); }, [tim]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { document.title = "KOME — kho hàng"; }, []);

  const q = new URLSearchParams();
  if (b.kho) q.set("kho", b.kho);
  if (b.loc) q.set("loc", b.loc);
  const { data: d, error, isFetching } = useQuery<KhoApi>({
    queryKey: ["kho-hang", q.toString()], placeholderData: keepPreviousData,
    queryFn: () => lay<KhoApi>(`/api/kho-hang${q.toString() ? "?" + q : ""}`),
  });
  const dm = useDanhMuc();

  const dong = useMemo(() => (d?.k.dong ?? []).filter(x => khopTim(x, b.tim)), [d, b.tim]);
  const canDat = useMemo(() => (dm.data?.ma ?? []).filter(m => m.trang_thai === "het_hang" || m.trang_thai === "sap_thieu")
    .sort((x, y) => (x.du_ban_ngay ?? -1) - (y.du_ban_ngay ?? -1) || y.dt_12t - x.dt_12t), [dm.data]);

  if (error) return <div className="sp"><h1>Kho hàng</h1><div className="khoi-loi">Không tải được tồn kho: {(error as Error).message}</div></div>;
  if (!d) return <div className="sp"><h1>Kho hàng</h1><div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></div>;
  const k = d.k, o = k.o_tong_quan;
  const locHopLe = b.loc in d.trang_thai ? b.loc : "";
  const tenKho = (ma: string) => { const x = k.ds_kho.find(w => w[0] === ma); return x ? `${x[0]} ${x[1]}` : ma; };
  const maxKho = Math.max(1, ...k.theo_kho.map(w => w.gia_tri));
  const tongDong = dong.reduce((s, x) => s + x.gia_tri, 0);

  const xuatCsv = () => {
    const cot = ["Mã", "Tên hàng", "Kho", "Số lượng", "Giá trị", "Hạn sử dụng", "Loại hạn", "Còn lại (ngày)", "Đủ bán cả mã (ngày)", "Trạng thái"];
    const hang = dong.map(x => [x.ma, x.ten, tenKho(x.kho), x.so_luong ?? "", x.gia_tri, x.best_before ?? "", x.nhan_han,
      x.han_con_lai ?? "", x.du_ban_ngay == null ? "" : Math.round(x.du_ban_ngay), x.nhan_trang_thai]);
    const csv = "﻿" + [cot, ...hang].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = `ton-kho-${k.ngay_chup ?? "chua-co"}.csv`; a.click(); URL.revokeObjectURL(a.href);
  };

  return (
    <div className={"sp kho" + (isFetching ? " dang-tai" : "")}>
      <div className="tieu-de-trang">
        <div><h1>Kho hàng</h1>
          <div className="phu">{k.ngay_chup ? <>Ảnh chụp <b className="ten-jp">在庫一覧</b> ngày <b>{ngay(k.ngay_chup)}</b> — tồn lúc xuất file, không phải lúc này.
            Số ngày "còn"/"quá" đếm từ mốc dữ liệu (ngày bán mới nhất), có thể lệch vài ngày so với ngày chụp.</> : "Chưa có bản xuất 在庫一覧 nào trong kho dữ liệu."}</div></div>
        <div className="sp-dau-phai">
          <button type="button" className="nut-nho" onClick={xuatCsv} disabled={!dong.length} title="Xuất đúng các dòng bảng tồn đang hiện (theo bộ lọc + ô tìm)">⤓ Xuất CSV</button>
          <a className="nut-nho" href="/san-pham">Sản phẩm →</a>
        </div>
      </div>

      <div className="kho-tab" role="tablist">
        {([["ton", "Tồn hiện tại", so(k.dong.length) + " dòng"], ["ve", "Hàng đang về", "chưa có"], ["can_dat", "Cần đặt", so((o.het_hang ?? 0) + (o.sap_thieu ?? 0)) + " mã"]] as const).map(([t, nhan, sl]) => (
          <button key={t} type="button" role="tab" aria-selected={b.tab === t} onClick={() => dat({ tab: t })}>
            {nhan}<span className={"kho-tab-so" + (t === "ve" ? " nhat" : "")}>{sl}</span></button>))}
      </div>

      <div className="o-kpi-luoi kho-kpi">
        <div className="o-kpi"><div className="nhan">Giá trị tồn{b.kho || locHopLe ? " (đang lọc)" : ""}</div><div className="gia">{gon(k.gia_tri_ton)}</div>
          <div className="dong-phu nhat-chu">{so(k.dong.length)} dòng tồn · theo cả hai bộ lọc</div></div>
        <button type="button" className="o-kpi sp-kpi-nut" aria-pressed={locHopLe === "het_hang"} onClick={() => dat({ tab: "ton", loc: locHopLe === "het_hang" ? "" : "het_hang" })}>
          <div className="nhan">Mã hết hàng</div><div className={"gia" + (o.het_hang ? " giam" : "")}>{so(o.het_hang ?? 0)}</div>
          <div className="dong-phu nhat-chu">mọi kho · tồn 0, 90 ngày qua vẫn có đơn</div></button>
        <button type="button" className="o-kpi sp-kpi-nut" aria-pressed={locHopLe === "sap_thieu"} onClick={() => dat({ tab: "ton", loc: locHopLe === "sap_thieu" ? "" : "sap_thieu" })}>
          <div className="nhan">Mã sắp thiếu</div><div className={"gia" + (o.sap_thieu ? " canh-chu" : "")}>{so(o.sap_thieu ?? 0)}</div>
          <div className="dong-phu nhat-chu">mọi kho · đủ bán &lt; 14 ngày</div></button>
        <div className="o-kpi"><div className="nhan">Lô cận hạn (≤ {d.can_han_ngay} ngày)</div><div className={"gia" + (o.can_han ? " canh-chu" : "")}>{so(o.can_han ?? 0)}</div>
          <div className="dong-phu nhat-chu">theo bộ lọc · {so(k.qua_han.length)} lô đã quá hạn</div></div>
        <button type="button" className="o-kpi sp-kpi-nut" aria-pressed={locHopLe === "ton_chet"} onClick={() => dat({ tab: "ton", loc: locHopLe === "ton_chet" ? "" : "ton_chet" })}>
          <div className="nhan">Giá trị tồn chết</div><div className="gia">{gon(o.gia_tri_ton_chet ?? 0)}</div>
          <div className="dong-phu nhat-chu">theo cả hai bộ lọc · bấm để lọc tồn chết</div></button>
      </div>
      <p className="phu kho-ghi">Hai ô <b>hết hàng / sắp thiếu</b> luôn đếm trên <b>mọi kho</b> và không theo bộ lọc trạng thái — trạng thái là thuộc tính của một <em>mã</em>{" "}
        tính trên tổng mọi kho ("mã hết hàng ở kho 0001" không có định nghĩa), và chính chúng là nhãn của bộ lọc đó. Các ô còn lại đi theo cả hai bộ lọc.</p>

      {b.tab === "ton" && <div className="kho-hai-cot">
        <section className="kh-the kho-chinh">
          <div className="sp-dm-dau">
            <h2>Tồn theo dòng</h2>
            <input type="search" className="kh-tim sp-tim" placeholder="Tìm mã hoặc tên hàng…" value={tim} onChange={e => datTim(e.target.value)} aria-label="Tìm trong bảng tồn" />
          </div>
          <div className="sp-chip" role="group" aria-label="Trạng thái tồn">
            <button type="button" className="chip" aria-pressed={!locHopLe} onClick={() => dat({ loc: "" })}>Mọi trạng thái</button>
            {Object.entries(d.trang_thai).map(([m, [nhan]]) => (
              <button key={m} type="button" className="chip" aria-pressed={locHopLe === m} onClick={() => dat({ loc: locHopLe === m ? "" : m })}>{nhan}</button>))}
          </div>
          <div className="sp-chip" role="group" aria-label="Kho">
            <button type="button" className="chip" aria-pressed={!b.kho} onClick={() => dat({ kho: "" })}>Mọi kho</button>
            {k.ds_kho.map(([m, ten]) => (
              <button key={m} type="button" className="chip ten-jp" aria-pressed={b.kho === m} onClick={() => dat({ kho: b.kho === m ? "" : m })}>{m} {ten}</button>))}
            {b.kho && !k.ds_kho.some(w => w[0] === b.kho) &&
              <button type="button" className="chip" aria-pressed onClick={() => dat({ kho: "" })}>{b.kho} (không có trong danh sách kho)</button>}
          </div>
          <div className="bang-cuon sp-bang-khung">
            <table className="bang kho-bang">
              <thead><tr><th>Mặt hàng</th><th>Kho</th><th>Hạn sử dụng</th><th className="so">Số lượng</th>
                <th title="Tồn MỌI kho ÷ bán/ngày của cả mã (mart không có 'đủ bán' riêng từng kho)">Đủ bán (cả mã)</th>
                <th className="so">Giá trị</th><th>Trạng thái</th></tr></thead>
              <tbody>
                {dong.map((x, i) => <DongTon key={x.ma + x.kho + i} x={x} tenKho={tenKho} />)}
                {!dong.length && <tr><td colSpan={7} className="trong">{b.tim ? `Không dòng tồn nào khớp "${b.tim}".` : "Không dòng tồn nào khớp bộ lọc."}</td></tr>}
              </tbody>
            </table>
          </div>
          <p className="phu sp-ghi">{so(dong.length)} dòng · {yen(tongDong)}{b.tim ? ` (ô tìm chỉ lọc bảng này)` : ""}. Xếp theo giá trị giảm dần.
            Nhãn hạn có bốn giá trị: "Không có hạn dùng" (賞味期限なし) là lời khẳng định về hàng, còn "Không đọc được hạn" là lời thú nhận về dữ liệu.</p>
        </section>

        <div className="kho-ben">
          <section className="kh-the">
            <h2>Đã quá hạn</h2>
            <p className="phu">Lô đã qua 賞味期限 mà vẫn còn trong bản xuất — việc xử lý ngay, không phải theo dõi.</p>
            {k.qua_han.length ? <div className="kho-the-ds">{k.qua_han.map((x, i) => <TheHan key={i} x={x} tenKho={tenKho} qua />)}</div>
              : <p className="trong-nho">Không lô nào quá hạn. Tốt.</p>}
          </section>
          <section className="kh-the">
            <h2>Cận hạn sử dụng</h2>
            <p className="phu">Còn ≤ {d.can_han_ngay} ngày — xử lý sớm còn bán được giá. Chỉ tính lô có hạn thật.</p>
            {k.can_han.length ? <div className="kho-the-ds">{k.can_han.map((x, i) => <TheHan key={i} x={x} tenKho={tenKho} />)}</div>
              : <p className="trong-nho">Không lô nào cận hạn.</p>}
          </section>
          <section className="kh-the">
            <h2>Giá trị tồn theo kho</h2>
            <p className="phu">Không tự lọc theo kho (bấm để lọc){locHopLe ? `; có theo trạng thái "${d.trang_thai[locHopLe][0]}" — kho không còn dòng nào ở trạng thái đó vắng mặt` : ""}.</p>
            {k.theo_kho.length ? k.theo_kho.map(w => (
              <button key={w.ma} type="button" className="kh-thanh-dong" aria-pressed={b.kho === w.ma} onClick={() => dat({ kho: b.kho === w.ma ? "" : w.ma })}>
                <span className="kh-td-nhan"><b className="ten-jp">{w.ma} {w.ten}</b><span>{yen(w.gia_tri)}</span></span>
                <span className="kh-td-thanh"><i style={{ width: `${w.gia_tri / maxKho * 100}%` }} /></span>
                <span className="sp-khach-phu">{so(w.so_dong)} dòng tồn</span>
              </button>)) : <p className="trong-nho">Chưa có dòng tồn nào.</p>}
          </section>
        </div>
      </div>}

      {b.tab === "ve" && <section className="kh-the kh-chua-co">
        <ChuaCoDuLieu tieu_de="Hàng đang về — lịch container 14 ngày tới"
          ly_do="Cần đơn mua hàng / lịch tàu / nhà cung cấp (仕入・発注データ). OBC chưa xuất các file đó cho kho dữ liệu, nên chưa biết lô nào đang về, về kho nào, trễ hẹn không." />
      </section>}

      {b.tab === "can_dat" && <section className="kh-the">
        <div className="kh-the-dau"><h2>Cần đặt</h2><span className="kh-the-goc nhat-chu">{so(canDat.length)} mã hết hàng hoặc sắp thiếu · mọi kho</span></div>
        <p className="phu">Xếp theo "còn đủ bán" tăng dần. <b>Chưa đề xuất số lượng đặt</b>: cần lead time, MOQ và nhà cung cấp — OBC chưa xuất các dữ liệu đó.
          Tốc độ bán là trung bình 90 ngày chia cho tuổi thật của mã — cùng con số đã xếp trạng thái.</p>
        {dm.error ? <div className="khoi-loi">{(dm.error as Error).message}</div> : !dm.data ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div> :
          <div className="bang-cuon"><table className="bang">
            <thead><tr><th>Mặt hàng</th><th>Trạng thái</th><th className="so">Tồn</th><th className="so">Bán/ngày</th><th className="so">Còn đủ bán</th>
              <th className="so">DT 12 tháng</th><th className="so">Khách</th><th className="so">Bán gần nhất</th><th>Đặt hàng</th></tr></thead>
            <tbody>{canDat.map(m => (
              <tr key={m.ma}><td><a className="ten-jp" href={`/san-pham/${encodeURIComponent(m.ma)}`}>{m.ten}</a><div className="ma-nho"><code>{m.ma}</code> · <span className="ten-jp">{m.nganh}</span></div></td>
                <td><span className={"nhan-vien " + m.mau}>{m.nhan_trang_thai}</span></td>
                <td className="so">{so_luong(m.ton)}</td><td className="so">{so_luong(m.toc_do_ngay_theo_tuoi)}</td>
                <td className={"so " + (m.du_ban_ngay != null && m.du_ban_ngay < 7 ? "giam" : "canh-chu")}>{m.du_ban_ngay == null ? "—" : `${Math.round(m.du_ban_ngay)} ngày`}</td>
                <td className="so">{yen(m.dt_12t)}</td><td className="so">{so(m.so_khach)}</td><td className="so nhat-chu">{ngay(m.lan_cuoi)}</td>
                <td><button type="button" className="nut-nho" disabled title="Chưa có dữ liệu nhà cung cấp / đơn mua — không tạo được PO.">Tạo PO</button></td></tr>))}
              {!canDat.length && <tr><td colSpan={9} className="trong">Không mã nào hết hàng hay sắp thiếu.</td></tr>}</tbody>
          </table></div>}
      </section>}
    </div>
  );
}

function DongTon({ x, tenKho }: { x: DongKho; tenKho: (m: string) => string }) {
  const du = x.du_ban_ngay;
  const mau = du == null ? "" : du < 14 ? "giam" : du > 180 ? "canh-chu" : "tang";
  return (
    <tr>
      <td className="sp-ten"><a className="ten-jp" href={`/san-pham/${encodeURIComponent(x.ma)}`}>{x.ten}</a>
        <div className="ma-nho"><code>{x.ma}</code></div></td>
      <td className="ten-jp kho-ten-kho">{tenKho(x.kho)}</td>
      <td><span className={"nhan-vien " + x.mau_han}>{x.nhan_han}</span>
        <div className={"ma-nho " + (x.han_con_lai != null && x.han_con_lai < 0 ? "giam" : x.han_con_lai != null && x.han_con_lai <= 90 ? "canh-chu" : "")}>
          {x.best_before ? <span className="ten-jp">{x.best_before}</span> : null}{x.han_con_lai != null ? ` · ${conHan(x)}` : ""}</div></td>
      <td className="so"><b>{so_luong(x.so_luong)}</b></td>
      <td className="kho-du"><span className={mau}>{du == null ? "—" : `${Math.round(du)} ngày`}</span>
        {du != null && <span className="kho-du-thanh"><i className={mau} style={{ width: `${Math.min(100, du / 180 * 100)}%` }} /></span>}</td>
      <td className="so">{yen(x.gia_tri)}</td>
      <td><span className={"nhan-vien " + x.mau}>{x.nhan_trang_thai}</span></td>
    </tr>
  );
}

function TheHan({ x, tenKho, qua = false }: { x: DongKho; tenKho: (m: string) => string; qua?: boolean }) {
  return (
    <div className={"kho-the-han" + (qua ? " qua" : "")}>
      <a className="ten-jp" href={`/san-pham/${encodeURIComponent(x.ma)}`}><b>{x.ten}</b></a>
      <div className="phu"><code>{x.ma}</code> · {tenKho(x.kho)} · {so_luong(x.so_luong)} · {yen(x.gia_tri)}</div>
      <div className={qua ? "giam" : "canh-chu"}><b>{conHan(x)}</b>{x.best_before ? <span className="ten-jp"> · {x.best_before}</span> : null}</div>
      <a className="kho-the-lk" href={`/san-pham/${encodeURIComponent(x.ma)}`}>Khách đang mua mã này →</a>
    </div>
  );
}
