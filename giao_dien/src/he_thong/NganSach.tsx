// Ngân sách theo tháng (041) — thiết kế lại 2026-09-25: ô số + biểu đồ tổng thể, lưới XOAY
// (tháng là dòng, không cuộn ngang), hai tab Công ty | Từng người, điền nhanh theo cột, dán
// khối từ Excel, thanh Lưu dính chỉ hiện khi có ô đã sửa.
//
// Vẫn là biểu mẫu POST /ngan-sach THẬT (một giao dịch; một ô rác => không ô nào được lưu, máy
// chủ trả lại đúng những gì vừa gõ — `da_go` — và đánh dấu ô sai). Tên ô:
// `o-<đối tượng>-<chỉ số>-<tháng>`. MỌI ô của cả hai tab / cả hai chỉ số đều nằm trong DOM
// (tab ẩn bằng `hidden`), nên Lưu gửi đủ. Ô của người ĐANG ẨN thì không vẽ => không gửi =>
// `luu()` không đụng tới (nó chỉ ghi khoá được gửi lên, và người bị ẩn không có chỉ tiêu nào
// trong kỳ — `ngan_sach.bang_nhap` luôn hiện người đã có số).
//
// Ngân sách công ty là số NHẬP THẲNG, không phải tổng từng người — màn in hai số cạnh nhau
// và phần chưa chia, không bao giờ tự cộng thay. `inputMode="numeric"` chứ KHÔNG
// `type="number"`: cuộn chuột trên ô number là đổi số. Ô chưa đặt TRỐNG, không 0 — "chưa đặt"
// khác "bằng không". Tổng in "—" khi không ô nào đứng sau nó. Tiền dấu CHẤM — khớp /bao-cao.
// "Năm trước" = thực tế cùng tháng kỳ trước (`mart.ban_theo_nhan_vien_thang`), chỉ để tham khảo.
import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import type { ClipboardEvent, KeyboardEvent } from "react";
import { KD } from "../khoi_dau";
import { gon, ngay, pc, thang_nhan, yen } from "../dinh_dang";
import { BieuDo } from "../chung/BieuDo";
import "../san_pham/san_pham.css";
import "./he_thong.css";

type Nguoi = { ma: string; ten: string; hien: boolean; con_ban: boolean; ban_cuoi: string | null };
type Man = {
  moi_ky: number[]; ky: number; thang: string[]; nguoi: Nguoi[]; cong_ty: string; ngay_con_ban: number;
  o_txt: Record<string, number>; thuc_te: Record<string, number>; da_go: Record<string, string>; loi: string[];
};
type ChiSo = "doanh_thu" | "lai_gop";
const TEN_CS: Record<ChiSo, string> = { doanh_thu: "Doanh thu", lai_gop: "Lãi gộp" };
const HAI_CS: ChiSo[] = ["doanh_thu", "lai_gop"];

const cham = (n: number) => n.toLocaleString("de-DE");
// Đọc thử ở trình duyệt — chỉ để tính tổng / đánh dấu ô sai TRƯỚC khi gửi. Máy chủ
// (`ngan_sach.doc_so`) vẫn là trọng tài; hàm này chép CÙNG luật nhóm ba chữ số (`1.5` là
// SAI chứ không phải 15), để ô Tổng không in một con số mà máy chủ sẽ từ chối.
const PHAN_CACH = /[.,\s_\u00a0\u3000\u202f]/g;
const NHOM = /^[0-9]{1,3}(?:[.,\s_\u00a0\u3000\u202f][0-9]{3})*$/;
function docSo(s: string): number | null | "sai" {
  const t = s.trim();
  if (!t) return null;
  return /^[0-9]+$/.test(t) || NHOM.test(t) ? Number(t.replace(PHAN_CACH, "")) : "sai";
}
const khoa = (doi: string, cs: ChiSo, th: string) => `${doi}-${cs}-${th}`;
const cong = (ds: number[]) => ds.reduce((s, v) => s + v, 0);
const tong = (ds: number[]) => ds.length ? yen(cong(ds)) : "—";
const thangCung = (th: string) => { const [y, m] = th.split("-"); return `${+y - 1}-${m}`; };

type Menu = { luoi: string; c: number; kieu: "chia" | "nam_truoc" | "bien" | null } | null;

export default function NganSach() {
  const m = KD.man as Man;
  const ct = m.cong_ty;
  const coGo = Object.keys(m.da_go).length > 0;

  // Giá trị ĐANG LƯU của mọi ô (chuỗi hiển thị) — mốc để biết ô nào đã sửa.
  const goc = useMemo(() => {
    const g: Record<string, string> = {};
    for (const doi of [ct, ...m.nguoi.map(n => n.ma)]) for (const cs of HAI_CS) for (const th of m.thang) {
      const v = m.o_txt[khoa(doi, cs, th)];
      g[khoa(doi, cs, th)] = v != null ? cham(v) : "";
    }
    return g;
  }, [m, ct]);
  // Thứ tự có nghĩa: đúng những gì vừa gõ (bị từ chối) > giá trị đang lưu > rỗng (CHƯA ĐẶT).
  const [gt, datGt] = useState<Record<string, string>>(() => {
    const g = { ...goc };
    if (coGo) for (const [k, v] of Object.entries(m.da_go)) {
      // Tên ô cũ `<mã>-YYYY-MM` (trước 041) = doanh thu của người đó.
      const p = k.split("-");
      g[p.length === 3 ? `${p[0]}-doanh_thu-${p[1]}-${p[2]}` : k] = v;
    }
    return g;
  });
  const loiMay = new Set(m.loi.map(k => { const p = k.split("-"); return p.length === 3 ? `${p[0]}-doanh_thu-${p[1]}-${p[2]}` : k; }));

  const [tab, datTab] = useState<"cong_ty" | "nguoi">(() => {
    try { return sessionStorage.getItem("ns-tab") === "nguoi" ? "nguoi" : "cong_ty"; } catch { return "cong_ty"; }
  });
  const [csNguoi, datCsNguoi] = useState<ChiSo>("doanh_thu");
  const [hienHet, datHienHet] = useState(false);
  const [menu, datMenu] = useState<Menu>(null);
  const [thamSo, datThamSo] = useState("");
  const dangGui = useRef(false);
  useEffect(() => { try { sessionStorage.setItem("ns-tab", tab); } catch { /* không lưu được thì thôi */ } }, [tab]);
  useEffect(() => { document.title = "KOME — ngân sách"; }, []);

  const so = (k: string): number | null => { const v = docSo(gt[k] ?? ""); return typeof v === "number" ? v : null; };
  const suaDs = Object.keys(gt).filter(k => (gt[k] ?? "") !== (goc[k] ?? ""));
  const sai = Object.keys(gt).filter(k => docSo(gt[k] ?? "") === "sai");
  const bienDoi = suaDs.length > 0 || coGo;

  useEffect(() => {
    const f = (e: BeforeUnloadEvent) => { if (suaDs.length && !dangGui.current) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", f);
    return () => window.removeEventListener("beforeunload", f);
  }, [suaDs.length]);

  const nguoiHien = m.nguoi.filter(n => n.hien || hienHet);
  const nguoiAn = m.nguoi.filter(n => !n.hien);
  const tt = (doi: string, cs: ChiSo, th: string): number | undefined => m.thuc_te[khoa(doi, cs, th)];
  const namTruoc = (doi: string, cs: ChiSo, th: string) => tt(doi, cs, thangCung(th));
  const cuaNguoi = (cs: ChiSo, th: string) => nguoiHien.map(n => so(khoa(n.ma, cs, th))).filter((v): v is number => v != null);

  // ---- lưới: mỗi lưới là ma trận khoá ô [dòng tháng][cột] — cho phím mũi tên, dán khối, điền nhanh.
  const luoi: Record<string, string[][]> = {
    cong_ty: m.thang.map(th => HAI_CS.map(cs => khoa(ct, cs, th))),
    doanh_thu: m.thang.map(th => nguoiHien.map(n => khoa(n.ma, "doanh_thu", th))),
    lai_gop: m.thang.map(th => nguoiHien.map(n => khoa(n.ma, "lai_gop", th))),
  };
  const cotCuaLuoi = (l: string, c: number) => luoi[l].map(h => h[c]);

  const dat = (thay: Record<string, string>) => datGt(g => ({ ...g, ...thay }));
  const oTai = (l: string, r: number, c: number) =>
    document.querySelector<HTMLInputElement>(`input[data-luoi="${l}"][data-r="${r}"][data-c="${c}"]`);

  const phim = (l: string, r: number, c: number) => (e: KeyboardEvent<HTMLInputElement>) => {
    const di: Record<string, [number, number]> = { Enter: [e.shiftKey ? -1 : 1, 0], ArrowDown: [1, 0], ArrowUp: [-1, 0] };
    const d = di[e.key];
    if (!d) return;
    e.preventDefault();   // Enter KHÔNG gửi biểu mẫu — gửi chỉ bằng nút Lưu.
    const o = oTai(l, r + d[0], c + d[1]);
    if (o) { o.focus(); o.select(); }
  };
  // Dán một khối Excel (tab giữa cột, xuống dòng giữa dòng) bắt đầu từ ô đang đứng.
  const dan = (l: string, r: number, c: number) => (e: ClipboardEvent<HTMLInputElement>) => {
    const txt = e.clipboardData.getData("text/plain");
    if (!/[\t\n]/.test(txt.replace(/\r?\n$/, ""))) return;   // một ô: để trình duyệt dán như thường
    e.preventDefault();
    const hang = txt.replace(/\r/g, "").replace(/\n$/, "").split("\n").map(h => h.split("\t"));
    const thay: Record<string, string> = {};
    hang.forEach((h, i) => h.forEach((v, j) => { const k = luoi[l][r + i]?.[c + j]; if (k) thay[k] = v.trim(); }));
    dat(thay);
  };

  const oNhap = (l: string, r: number, c: number, nhan: string) => {
    const k = luoi[l][r][c];
    const saiO = loiMay.has(k) || docSo(gt[k] ?? "") === "sai";
    const lop = [saiO ? "sai" : "", (gt[k] ?? "") !== (goc[k] ?? "") ? "da-sua" : ""].filter(Boolean).join(" ");
    return <input type="text" inputMode="numeric" autoComplete="off" name={"o-" + k} data-luoi={l} data-r={r} data-c={c}
      aria-label={nhan} className={lop || undefined} aria-invalid={saiO ? true : undefined} value={gt[k] ?? ""}
      onChange={e => dat({ [k]: e.target.value })} onKeyDown={phim(l, r, c)} onPaste={dan(l, r, c)}
      onFocus={e => e.target.select()} />;
  };

  // ---- điền nhanh (chỉ đổi ô; chưa lưu gì cho tới khi bấm Lưu)
  const apDung = (l: string, c: number, lam: (k: string, i: number) => string | undefined) => {
    const thay: Record<string, string> = {};
    cotCuaLuoi(l, c).forEach((k, i) => { const v = lam(k, i); if (v !== undefined) thay[k] = v; });
    dat(thay); datMenu(null); datThamSo("");
  };
  const doiTuongCot = (l: string, c: number): [string, ChiSo] =>
    l === "cong_ty" ? [ct, HAI_CS[c]] : [nguoiHien[c].ma, l as ChiSo];
  const chiaDeu = (l: string, c: number, tongKy: number) => {
    const moi = Math.floor(tongKy / 12), du = tongKy - moi * 12;   // phần dư dồn vào tháng cuối => cộng lại ĐÚNG bằng tổng gõ
    apDung(l, c, (_, i) => cham(i === 11 ? moi + du : moi));
  };
  const theoNamTruoc = (l: string, c: number, phanTram: number) => {
    const [doi, cs] = doiTuongCot(l, c);
    apDung(l, c, (_, i) => { const v = namTruoc(doi, cs, m.thang[i]); return v == null ? undefined : cham(Math.max(0, Math.round(v * phanTram / 100))); });
  };
  const theoBien = (l: string, c: number, phanTram: number) => {
    const [doi] = doiTuongCot(l, c);
    apDung(l, c, (_, i) => { const dt = so(khoa(doi, "doanh_thu", m.thang[i])); return dt == null ? undefined : cham(Math.round(dt * phanTram / 100)); });
  };
  const dienXuong = (l: string, c: number) => {
    let tren = "";
    apDung(l, c, k => { const v = gt[k] ?? ""; if (v.trim()) { tren = v; return undefined; } return tren || undefined; });
  };

  const dauCot = (l: string, c: number, ten: string, phu?: string) => {
    const [doi, cs] = doiTuongCot(l, c);
    const coNT = m.thang.some(th => namTruoc(doi, cs, th) != null);
    const mo = menu && menu.luoi === l && menu.c === c ? menu : null;
    // KHÔNG phải <form>: nằm trong biểu mẫu Lưu, form lồng form là HTML sai. Enter ở đây điền, không gửi.
    const nhapSo = (goi: (n: number) => void, nhan: string, mau: string) => {
      const chay = () => { const v = docSo(thamSo); if (typeof v === "number") goi(v); };
      return <div className="ns-menu-so">
        <label>{nhan}<input autoFocus inputMode="numeric" value={thamSo} placeholder={mau} onChange={e => datThamSo(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); chay(); } }} /></label>
        <button type="button" className="nut-nho chinh" onClick={chay}>Điền</button>
      </div>;
    };
    return (
      <th className="ns-cot">
        <div className="ns-cot-dau"><span>{ten}{phu && <small className="nhat-chu">{phu}</small>}</span>
          <button type="button" className="ns-nut-menu" aria-haspopup="true" aria-expanded={!!mo}
            aria-label={`Điền nhanh cột ${ten}`} title="Điền nhanh cả cột"
            onClick={() => { datMenu(mo ? null : { luoi: l, c, kieu: null }); datThamSo(""); }}>⋯</button></div>
        {mo && <div className="ns-menu" role="menu" onKeyDown={e => { if (e.key === "Escape") datMenu(null); }}>
          {mo.kieu === null && <>
            <button type="button" role="menuitem" onClick={() => datMenu({ ...mo, kieu: "chia" })}>Chia đều một tổng cho 12 tháng…</button>
            <button type="button" role="menuitem" disabled={!coNT} title={coNT ? undefined : "Không có thực tế năm trước cho cột này"}
              onClick={() => { datMenu({ ...mo, kieu: "nam_truoc" }); datThamSo("100"); }}>Theo thực tế năm trước × %…</button>
            {cs === "lai_gop" && <button type="button" role="menuitem" onClick={() => datMenu({ ...mo, kieu: "bien" })}>Lãi gộp = doanh thu × biên %…</button>}
            <button type="button" role="menuitem" onClick={() => dienXuong(l, c)}>Điền ô trống bằng ô phía trên</button>
            <button type="button" role="menuitem" className="giam" onClick={() => apDung(l, c, () => "")}>Xoá cả cột (thành chưa đặt)</button>
          </>}
          {mo.kieu === "chia" && nhapSo(n => chiaDeu(l, c, n), "Tổng cả kỳ (¥)", "120.000.000")}
          {mo.kieu === "nam_truoc" && nhapSo(n => theoNamTruoc(l, c, n), "Bằng bao nhiêu % năm trước", "105")}
          {mo.kieu === "bien" && nhapSo(n => theoBien(l, c, n), "Biên gộp (%)", "22")}
          {mo.kieu !== null && <p className="nhat-chu">Chỉ điền vào ô — chưa lưu cho tới khi bấm Lưu.
            {mo.kieu === "nam_truoc" && " Tháng không có thực tế năm trước giữ nguyên."}
            {mo.kieu === "bien" && " Tháng chưa có doanh thu giữ nguyên."}</p>}
        </div>}
      </th>);
  };

  // ---- tổng hợp cho ô số + biểu đồ (theo số ĐANG GÕ, không chỉ số đã lưu)
  const ctDt = m.thang.map(th => so(khoa(ct, "doanh_thu", th)));
  const ctLg = m.thang.map(th => so(khoa(ct, "lai_gop", th)));
  const coDt = ctDt.filter((v): v is number => v != null);
  const coLg = ctLg.filter((v): v is number => v != null);
  // Biên gộp là TỶ SỐ CỦA CÁC TỔNG, chỉ trên các tháng có đủ cả hai số.
  const du2 = m.thang.map((_, i) => i).filter(i => ctDt[i] != null && ctLg[i] != null);
  const bienKy = du2.length ? cong(du2.map(i => ctLg[i]!)) / cong(du2.map(i => ctDt[i]!)) : null;
  const ntDt = m.thang.map(th => namTruoc(ct, "doanh_thu", th) ?? null);
  const ntLg = m.thang.map(th => namTruoc(ct, "lai_gop", th) ?? null);
  // So năm trước CHỈ trên các tháng mà cả hai phía có số — không đem 3 tháng ngân sách so 12 tháng thực tế.
  const soNT = m.thang.map((_, i) => i).filter(i => ctDt[i] != null && ntDt[i] != null);
  const tangNT = soNT.length && cong(soNT.map(i => ntDt[i]!)) > 0
    ? cong(soNT.map(i => ctDt[i]!)) / cong(soNT.map(i => ntDt[i]!)) - 1 : null;
  const ngDt = m.thang.map(th => { const d = cuaNguoi("doanh_thu", th); return d.length ? cong(d) : null; });
  const daChia = cong(ngDt.filter((v): v is number => v != null));
  const coNgDt = ngDt.some(v => v != null);
  const thucKy = m.thang.map(th => tt(ct, "doanh_thu", th) ?? null);
  const coNTDt = ntDt.filter((v): v is number => v != null);
  const coNTLg = ntLg.filter((v): v is number => v != null);

  const ky0 = m.thang[0], ky1 = m.thang[m.thang.length - 1];
  const tenThang = (th: string) => { const [y, t] = th.split("-"); return `T${+t}/${y}`; };

  return (
    <div className="sp ns">
      <div className="tieu-de-trang">
        <div><h1>Ngân sách</h1>
          <div className="phu">Chỉ tiêu doanh thu &amp; lãi gộp (粗利益) theo tháng — kỳ {m.ky}: {tenThang(ky0)} → {tenThang(ky1)}.
            Tổng quan, Báo cáo và Dự báo so tiến độ với <b>ngân sách công ty</b>; chỉ tiêu từng người dùng cho thanh tiến độ từng người.</div></div>
        <nav className="sp-dau-phai ns-ky" aria-label="Kỳ kế toán">
          {m.moi_ky.map(k => <a key={k} href={`/ngan-sach?ky=${k}`} className="nut-nho"
            aria-current={k === m.ky ? "page" : undefined}>Kỳ {k}</a>)}
        </nav>
      </div>

      {m.loi.length > 0 && <div className="ngay-thieu" role="alert">Có {m.loi.length} ô không đọc được thành số —{" "}
        <strong>chưa ô nào được lưu</strong>. Sửa những ô viền đỏ rồi bấm Lưu lại. Chỉ nhận chữ số; dấu chấm, dấu phẩy và dấu cách
        đều bỏ qua được.</div>}

      <div className="o-kpi-luoi sp-kpi">
        <div className={"o-kpi" + (coDt.length ? "" : " chua")}><div className="nhan">Ngân sách doanh thu cả kỳ</div>
          <div className="gia">{coDt.length ? gon(cong(coDt)) : "Chưa đặt"}</div>
          <div className="dong-phu nhat-chu">{coDt.length}/12 tháng đã đặt
            {tangNT != null && <> · <span className={tangNT >= 0 ? "ns-len" : "giam"}>{tangNT >= 0 ? "▲" : "▼"}{pc(Math.abs(tangNT))}</span> so năm trước ({soNT.length} tháng đối chiếu)</>}</div></div>
        <div className={"o-kpi" + (coLg.length ? "" : " chua")}><div className="nhan">Ngân sách lãi gộp cả kỳ</div>
          <div className="gia">{coLg.length ? gon(cong(coLg)) : "Chưa đặt"}</div>
          <div className="dong-phu nhat-chu">biên gộp dự kiến {pc(bienKy)}{du2.length > 0 && du2.length < 12 && ` (${du2.length} tháng đủ hai số)`}</div></div>
        <div className={"o-kpi" + (coNgDt ? "" : " chua")}><div className="nhan">Đã chia cho người phụ trách</div>
          <div className="gia">{coNgDt ? gon(daChia) : "Chưa chia"}</div>
          <div className="dong-phu nhat-chu">{coNgDt && coDt.length ? <>{pc(daChia / cong(coDt), 0)} ngân sách doanh thu công ty · còn {gon(cong(coDt) - daChia)} chưa chia</>
            : "không bắt buộc"}</div></div>
        <div className={"o-kpi" + (coNTDt.length ? "" : " chua")}><div className="nhan">Thực tế kỳ {m.ky - 1} (tham khảo)</div>
          <div className="gia">{coNTDt.length ? gon(cong(coNTDt)) : "Không có số"}</div>
          <div className="dong-phu nhat-chu">{coNTDt.length ? <>{coNTDt.length}/12 tháng có dữ liệu · lãi gộp {gon(cong(coNTLg))} · biên {pc(cong(coNTDt) ? cong(coNTLg) / cong(coNTDt) : null)}</>
            : "kho chưa có dữ liệu bán của kỳ trước"}</div></div>
      </div>

      <section className="kh-the ns-bieu-do">
        <div className="sp-dm-dau"><h2>12 tháng của kỳ {m.ky}</h2>
          <span className="phu">cập nhật ngay khi gõ · bấm chú giải để bật/tắt</span></div>
        <BieuDo nhan={m.thang.map(thang_nhan)} cao={190} mo_ta={`Ngân sách doanh thu công ty theo tháng của kỳ ${m.ky}, so với thực tế năm trước`}
          dinh_dang={v => v == null ? "—" : yen(v)} dinh_dang_truc={v => gon(v)}
          chuoi={[
            { ten: "Ngân sách công ty", kieu: "cot", mau: "var(--do)", gia_tri: ctDt },
            { ten: "Thực tế kỳ này", kieu: "cot_nen", mau: "var(--ok-nen)", gia_tri: thucKy, an_mac_dinh: !thucKy.some(v => v != null) },
            { ten: "Thực tế năm trước", kieu: "duong", mau: "var(--lien-ket)", gia_tri: ntDt },
            { ten: "Tổng chỉ tiêu từng người", kieu: "duong_dut", mau: "var(--canh-vien)", gia_tri: ngDt },
          ]} />
      </section>

      <form method="post" action="/ngan-sach" className="ns-form" onSubmit={e => {
        if (sai.length && !confirm(`${sai.length} ô không đọc được thành số — máy chủ sẽ từ chối cả lượt lưu. Vẫn gửi?`)) { e.preventDefault(); return; }
        dangGui.current = true;
      }}>
        <input type="hidden" name="ky" value={m.ky} />

        <div className="ns-thanh-tab">
          <div className="tab-pill" role="tablist" aria-label="Bảng nhập">
            <button type="button" role="tab" aria-pressed={tab === "cong_ty"} aria-selected={tab === "cong_ty"} onClick={() => datTab("cong_ty")}>Công ty</button>
            <button type="button" role="tab" aria-pressed={tab === "nguoi"} aria-selected={tab === "nguoi"} onClick={() => datTab("nguoi")}>
              Từng người phụ trách ({nguoiHien.length})</button>
          </div>
          {tab === "nguoi" && <div className="tab-pill" role="group" aria-label="Chỉ số">
            {HAI_CS.map(cs => <button key={cs} type="button" aria-pressed={csNguoi === cs} onClick={() => datCsNguoi(cs)}>{TEN_CS[cs]}</button>)}
          </div>}
          <span className="phu ns-meo">Ô trống = <b>chưa đặt</b> (khác <code>0</code>) · Enter / ↑↓ đi dòng · dán được cả khối từ Excel · <b>⋯</b> ở đầu cột để điền nhanh</span>
        </div>

        {/* TAB CÔNG TY */}
        <section className="kh-the ns-the" hidden={tab !== "cong_ty"}>
          <div className="bang-cuon">
            <table className="bang ns-bang">
              <thead><tr><th>Tháng</th>{dauCot("cong_ty", 0, "Doanh thu")}<th className="so ns-tk">Năm trước</th>
                {dauCot("cong_ty", 1, "Lãi gộp")}<th className="so ns-tk">Năm trước</th><th className="so">Biên gộp</th>
                <th className="so ns-tk">Thực tế kỳ này</th></tr></thead>
              <tbody>
                {m.thang.map((th, r) => {
                  const dt = ctDt[r], lg = ctLg[r];
                  return <tr key={th}><th scope="row" className="ns-thang">{tenThang(th)}</th>
                    <td>{oNhap("cong_ty", r, 0, `Công ty — Doanh thu — ${th}`)}</td>
                    <td className="so ns-tk">{yen(ntDt[r])}</td>
                    <td>{oNhap("cong_ty", r, 1, `Công ty — Lãi gộp — ${th}`)}</td>
                    <td className="so ns-tk">{yen(ntLg[r])}</td>
                    <td className="so">{dt != null && lg != null && dt ? pc(lg / dt) : "—"}</td>
                    <td className="so ns-tk">{yen(thucKy[r])}</td></tr>;
                })}
              </tbody>
              <tfoot><tr className="tong"><th scope="row">Cả kỳ</th><td className="so">{tong(coDt)}</td><td className="so ns-tk">{tong(coNTDt)}</td>
                <td className="so">{tong(coLg)}</td><td className="so ns-tk">{tong(coNTLg)}</td><td className="so">{pc(bienKy)}</td>
                <td className="so ns-tk">{tong(thucKy.filter((v): v is number => v != null))}</td></tr></tfoot>
            </table>
          </div>
          <p className="ghi-chu">Số của cả công ty, <b>nhập thẳng</b> — không cộng từ chỉ tiêu từng người. "Năm trước" / "Thực tế kỳ này" là
            doanh thu thuần &amp; lãi gộp đã bán (cùng số với Báo cáo), chỉ để tham khảo khi đặt số.</p>
        </section>

        {/* TAB TỪNG NGƯỜI — cả hai chỉ số luôn trong DOM để Lưu gửi đủ */}
        {HAI_CS.map(cs => (
          <section key={cs} className="kh-the ns-the" hidden={tab !== "nguoi" || csNguoi !== cs}>
            <div className="bang-cuon">
              <table className="bang ns-bang">
                <thead><tr><th>Tháng</th>
                  {nguoiHien.map((n, c) => <Fragment key={n.ma}>{dauCot(cs, c, n.ten, n.ma + (n.con_ban ? "" : ` · không bán ${m.ngay_con_ban} ngày`))}</Fragment>)}
                  <th className="so">Tổng từng người</th><th className="so ns-tk">Công ty</th><th className="so">Chưa chia</th></tr></thead>
                <tbody>
                  {m.thang.map((th, r) => {
                    const ng = cuaNguoi(cs, th), c = so(khoa(ct, cs, th));
                    return <tr key={th}><th scope="row" className="ns-thang">{tenThang(th)}</th>
                      {nguoiHien.map((n, ci) => <td key={n.ma}>{oNhap(cs, r, ci, `${n.ten} — ${TEN_CS[cs]} — ${th}`)}
                        <small className="ns-nt" title="Thực tế cùng tháng năm trước">{namTruoc(n.ma, cs, th) != null ? "NT " + gon(namTruoc(n.ma, cs, th)!) : " "}</small></td>)}
                      <td className="so">{tong(ng)}</td><td className="so ns-tk">{c != null ? yen(c) : "—"}</td>
                      <td className={"so" + (c != null && ng.length && c - cong(ng) < 0 ? " giam" : "")}>{c != null && ng.length ? yen(c - cong(ng)) : "—"}</td></tr>;
                  })}
                </tbody>
                <tfoot><tr className="tong"><th scope="row">Cả kỳ</th>
                  {nguoiHien.map(n => <td key={n.ma} className="so">{tong(m.thang.map(th => so(khoa(n.ma, cs, th))).filter((v): v is number => v != null))}</td>)}
                  <td className="so">{tong(m.thang.flatMap(th => cuaNguoi(cs, th)))}</td>
                  <td className="so ns-tk">{tong(m.thang.map(th => so(khoa(ct, cs, th))).filter((v): v is number => v != null))}</td><td></td></tr></tfoot>
              </table>
            </div>
            <p className="ghi-chu">Không bắt buộc. "Chưa chia" = ngân sách công ty − tổng từng người (âm = chỉ tiêu từng người cộng lại vượt
              ngân sách công ty). "NT" = thực tế cùng tháng năm trước của người đó.</p>
          </section>))}

        {nguoiAn.length > 0 && tab === "nguoi" && <p className="ns-an">
          {hienHet ? "Đang hiện cả" : "Đang ẩn"} {nguoiAn.length} người không có doanh số trong {m.ngay_con_ban} ngày tới mốc dữ liệu:{" "}
          {nguoiAn.map((n, i) => <span key={n.ma}>{i > 0 && ", "}<b>{n.ten}</b> <span className="nhat-chu">({n.ban_cuoi ? `bán lần cuối ${ngay(n.ban_cuoi)}` : "chưa có doanh số với khách"})</span></span>)}
          {" "}<button type="button" className="nut-nho" onClick={() => datHienHet(!hienHet)}>{hienHet ? "Ẩn lại" : "Hiện"}</button></p>}

        <div className={"ns-luu-thanh" + (bienDoi ? " hien" : "")} aria-live="polite">
          <span>{suaDs.length ? <><b>{suaDs.length}</b> ô đã sửa, chưa lưu</> : coGo ? "Chưa lưu — sửa các ô viền đỏ" : "Không có thay đổi"}
            {sai.length > 0 && <span className="giam"> · {sai.length} ô không phải số</span>}</span>
          <button type="button" className="nut-nho" disabled={!suaDs.length && !coGo} onClick={() => {
            if (confirm("Bỏ mọi thay đổi chưa lưu, trở về số đang lưu?")) datGt({ ...goc });
          }}>Bỏ thay đổi</button>
          <button type="submit" className="nut-chinh" disabled={!suaDs.length && !coGo}>Lưu</button>
        </div>
      </form>
    </div>
  );
}
