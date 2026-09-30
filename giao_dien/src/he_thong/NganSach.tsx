// Ngân sách theo tháng (041) — thiết kế lại 2026-10-01 (chủ DN: "tập trung vào nhập ngân sách công ty
// và chia cho từng sale", "nhiều chữ, rối mắt"; chọn kết hợp "một bảng" + "đặt theo năm, tháng tự chia"):
//   * trên: đặt số cả kỳ — tổng doanh thu công ty + biên lãi gộp + thanh chia % cho từng sale (kéo vạch
//     hoặc gõ %) — rồi "↓ Điền vào 12 tháng" (logic thuần `ngan_sach_logic.ts`, có test);
//   * dưới: MỘT bảng 12 tháng — Công ty · từng sale · "còn" (xanh đủ / vàng thiếu / đỏ vượt), gạt
//     Doanh thu | Lãi gộp, sửa thẳng từng ô, dán khối Excel, Enter / ↑↓ đi dòng.
//
// Vẫn là biểu mẫu POST /ngan-sach THẬT (một giao dịch; một ô rác => không ô nào được lưu, máy
// chủ trả lại đúng những gì vừa gõ — `da_go` — và đánh dấu ô sai). Tên ô:
// `o-<đối tượng>-<chỉ số>-<tháng>`. MỌI ô của cả hai chỉ số đều nằm trong DOM (bảng chỉ số kia
// ẩn bằng `hidden`), nên Lưu gửi đủ. Ô của người ĐANG ẨN thì không vẽ => không gửi => `luu()`
// không đụng tới (người bị ẩn không có chỉ tiêu nào trong kỳ — `ngan_sach.bang_nhap` luôn hiện
// người đã có số). "Điền vào 12 tháng" chỉ đổi Ô — chưa lưu gì cho tới khi bấm Lưu.
//
// Ngân sách công ty là số NHẬP THẲNG, không phải tổng từng người — màn in hai số cạnh nhau
// và phần chưa chia ("còn"), không bao giờ tự cộng thay. `inputMode="numeric"` chứ KHÔNG
// `type="number"`: cuộn chuột trên ô number là đổi số. Ô chưa đặt TRỐNG, không 0 — "chưa đặt"
// khác "bằng không". Tổng in "—" khi không ô nào đứng sau nó.
// "Năm trước" = thực tế cùng tháng kỳ trước (`mart.dong_ban_khoang`), chỉ để tham khảo.
import { useEffect, useMemo, useRef, useState } from "react";
import type { ClipboardEvent, KeyboardEvent, PointerEvent as PE } from "react";
import { KD } from "../khoi_dau";
import { gon, ngay, pc, yen } from "../dinh_dang";
import { ONoi } from "../chung/ONoi";
import { chiaPhanTram, chiaTheoTrongSo, keoVach, phanTramTheo, trongSoMua } from "./ngan_sach_logic";
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
// Màu từng sale trên thanh chia (theo thứ tự) — biến CSS, không mã màu.
const MAU_SALE = ["var(--ok-vien)", "var(--lien-ket)", "var(--canh-vien)", "var(--do)", "var(--chu-mo)"];

const cham = (n: number) => n.toLocaleString("ja-JP");
// Đọc thử ở trình duyệt — chỉ để tính tổng / đánh dấu ô sai TRƯỚC khi gửi. Máy chủ
// (`ngan_sach.doc_so`) vẫn là trọng tài; hàm này chép CÙNG luật nhóm ba chữ số (`1.5` là
// SAI chứ không phải 15), để ô Tổng không in một con số mà máy chủ sẽ từ chối.
const PHAN_CACH = /[.,\s_ 　 ]/g;
const NHOM = /^[0-9]{1,3}(?:[.,\s_ 　 ][0-9]{3})*$/;
function docSo(s: string): number | null | "sai" {
  const t = s.trim();
  if (!t) return null;
  return /^[0-9]+$/.test(t) || NHOM.test(t) ? Number(t.replace(PHAN_CACH, "")) : "sai";
}
/** Ô % (biên, phần của sale): nhận cả chấm lẫn phẩy thập phân. */
const docPt = (s: string): number | null => {
  const v = Number(s.trim().replace(",", ".").replace("%", ""));
  return s.trim() && Number.isFinite(v) && v >= 0 ? v : null;
};
const khoa = (doi: string, cs: ChiSo, th: string) => `${doi}-${cs}-${th}`;
const cong = (ds: number[]) => ds.reduce((s, v) => s + v, 0);
const tong = (ds: number[]) => ds.length ? yen(cong(ds)) : "—";
const thangCung = (th: string) => { const [y, m] = th.split("-"); return `${+y - 1}-${m}`; };
const laSo = (v: number | null | undefined): v is number => v != null;

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

  const [cs, datCs] = useState<ChiSo>(() => {
    try { return sessionStorage.getItem("ns-cs") === "lai_gop" ? "lai_gop" : "doanh_thu"; } catch { return "doanh_thu"; }
  });
  const [hienHet, datHienHet] = useState(false);
  const dangGui = useRef(false);
  useEffect(() => { try { sessionStorage.setItem("ns-cs", cs); } catch { /* không lưu được thì thôi */ } }, [cs]);
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
  const tt = (doi: string, c: ChiSo, th: string): number | undefined => m.thuc_te[khoa(doi, c, th)];
  const namTruoc = (doi: string, c: ChiSo, th: string) => tt(doi, c, thangCung(th));
  const cuaNguoi = (c: ChiSo, th: string) => nguoiHien.map(n => so(khoa(n.ma, c, th))).filter(laSo);

  // ---- lưới: mỗi chỉ số một ma trận khoá ô [dòng tháng][cột: công ty, rồi từng sale] — cho phím, dán khối.
  const luoi: Record<ChiSo, string[][]> = {
    doanh_thu: m.thang.map(th => [ct, ...nguoiHien.map(n => n.ma)].map(d => khoa(d, "doanh_thu", th))),
    lai_gop: m.thang.map(th => [ct, ...nguoiHien.map(n => n.ma)].map(d => khoa(d, "lai_gop", th))),
  };

  const dat = (thay: Record<string, string>) => datGt(g => ({ ...g, ...thay }));
  const oTai = (l: string, r: number, c: number) =>
    document.querySelector<HTMLInputElement>(`input[data-luoi="${l}"][data-r="${r}"][data-c="${c}"]`);

  const phim = (l: ChiSo, r: number, c: number) => (e: KeyboardEvent<HTMLInputElement>) => {
    const di: Record<string, [number, number]> = { Enter: [e.shiftKey ? -1 : 1, 0], ArrowDown: [1, 0], ArrowUp: [-1, 0] };
    const d = di[e.key];
    if (!d) return;
    e.preventDefault();   // Enter KHÔNG gửi biểu mẫu — gửi chỉ bằng nút Lưu.
    const o = oTai(l, r + d[0], c + d[1]);
    if (o) { o.focus(); o.select(); }
  };
  // Dán một khối Excel (tab giữa cột, xuống dòng giữa dòng) bắt đầu từ ô đang đứng.
  const dan = (l: ChiSo, r: number, c: number) => (e: ClipboardEvent<HTMLInputElement>) => {
    const txt = e.clipboardData.getData("text/plain");
    if (!/[\t\n]/.test(txt.replace(/\r?\n$/, ""))) return;   // một ô: để trình duyệt dán như thường
    e.preventDefault();
    const hang = txt.replace(/\r/g, "").replace(/\n$/, "").split("\n").map(h => h.split("\t"));
    const thay: Record<string, string> = {};
    hang.forEach((h, i) => h.forEach((v, j) => { const k = luoi[l][r + i]?.[c + j]; if (k) thay[k] = v.trim(); }));
    dat(thay);
  };

  const oNhap = (l: ChiSo, r: number, c: number, nhan: string, nen?: number | null) => {
    const k = luoi[l][r][c];
    const saiO = loiMay.has(k) || docSo(gt[k] ?? "") === "sai";
    const lop = [saiO ? "sai" : "", (gt[k] ?? "") !== (goc[k] ?? "") ? "da-sua" : ""].filter(Boolean).join(" ");
    // Vạch nền = thực tế năm trước của tháng đó (tỷ lệ trên tháng năm trước lớn nhất) — không cột chữ.
    const style = nen != null && nen > 0 ? { backgroundSize: `${Math.min(100, nen * 100).toFixed(1)}% 100%` } : undefined;
    return <input type="text" inputMode="numeric" autoComplete="off" name={"o-" + k} data-luoi={l} data-r={r} data-c={c}
      aria-label={nhan} className={[lop, nen != null ? "ns-nen" : ""].filter(Boolean).join(" ") || undefined}
      aria-invalid={saiO ? true : undefined} value={gt[k] ?? ""} style={style} placeholder="chưa đặt"
      onChange={e => dat({ [k]: e.target.value })} onKeyDown={phim(l, r, c)} onPaste={dan(l, r, c)}
      onFocus={e => e.target.select()} />;
  };

  // ---- số cả kỳ (theo số ĐANG GÕ)
  const ctDt = m.thang.map(th => so(khoa(ct, "doanh_thu", th)));
  const ctLg = m.thang.map(th => so(khoa(ct, "lai_gop", th)));
  const ntDt = m.thang.map(th => namTruoc(ct, "doanh_thu", th) ?? null);
  const ntLg = m.thang.map(th => namTruoc(ct, "lai_gop", th) ?? null);
  const coDt = ctDt.filter(laSo);
  // Biên gộp là TỶ SỐ CỦA CÁC TỔNG, chỉ trên các tháng có đủ cả hai số.
  const du2 = m.thang.map((_, i) => i).filter(i => ctDt[i] != null && ctLg[i] != null);
  const bienKy = du2.length && cong(du2.map(i => ctDt[i]!)) ? cong(du2.map(i => ctLg[i]!)) / cong(du2.map(i => ctDt[i]!)) : null;
  const tongNT = cong(ntDt.filter(laSo)), tongNTLg = cong(ntLg.filter(laSo));
  const bienNT = tongNT > 0 ? tongNTLg / tongNT : null;
  const ntSale = (ma: string) => cong(m.thang.map(th => namTruoc(ma, "doanh_thu", th)).filter(laSo));

  // ---- bảng điều khiển trên (chỉ là ĐỀ XUẤT — số thật nằm trong ô)
  // Chỉ điền sẵn khi cả 12 tháng đã đặt — tổng của vài tháng đem so cả năm trước là số nói sai.
  const [tongTxt, datTongTxt] = useState(() => (coDt.length === m.thang.length ? cham(cong(coDt)) : ""));
  const [bienTxt, datBienTxt] = useState(() => {
    const b = bienKy ?? bienNT;
    return b != null ? String(Math.round(b * 1000) / 10) : "";
  });
  const [pt, datPt] = useState<Record<string, number>>(() => {
    const ds = m.nguoi.filter(n => n.hien);
    const tongCt = cong(coDt);
    const cua = ds.map(n => cong(m.thang.map(th => so(khoa(n.ma, "doanh_thu", th))).filter(laSo)));
    // Đã chia rồi -> giữ đúng tỷ lệ đang có (không cần cộng đủ 100); chưa -> theo năm trước.
    const p = tongCt > 0 && cong(cua) > 0 ? cua.map(v => Math.round(v / tongCt * 100)) : phanTramTheo(ds.map(n => ntSale(n.ma)));
    return Object.fromEntries(ds.map((n, i) => [n.ma, p[i] ?? 0]));
  });
  const ptDs = nguoiHien.map(n => pt[n.ma] ?? 0);
  const tongPt = cong(ptDs);
  const tongGo = (() => { const v = docSo(tongTxt); return typeof v === "number" ? v : null; })();
  const bienGo = docPt(bienTxt);

  const dienThang = () => {
    if (tongGo == null) return;
    const dt = chiaTheoTrongSo(tongGo, trongSoMua(ntDt));
    const lg = bienGo != null ? chiaTheoTrongSo(Math.round(tongGo * bienGo / 100), dt) : null;
    const thay: Record<string, string> = {};
    m.thang.forEach((th, i) => {
      thay[khoa(ct, "doanh_thu", th)] = cham(dt[i]);
      if (lg) thay[khoa(ct, "lai_gop", th)] = cham(lg[i]);
      const pd = chiaPhanTram(dt[i], ptDs), pl = lg ? chiaPhanTram(lg[i], ptDs) : null;
      nguoiHien.forEach((n, j) => {
        if (!ptDs[j]) return;       // người 0% không bị ghi đè thành 0 — ô giữ nguyên (chưa đặt ≠ 0)
        thay[khoa(n.ma, "doanh_thu", th)] = cham(pd[j]);
        if (pl) thay[khoa(n.ma, "lai_gop", th)] = cham(pl[j]);
      });
    });
    const de = Object.entries(thay).filter(([k, v]) => (gt[k] ?? "").trim() && gt[k] !== v).length;
    if (de && !confirm(`${de} ô đang có số sẽ bị thay bằng số chia mới. Chưa lưu gì cho tới khi bấm Lưu. Tiếp tục?`)) return;
    dat(thay);
  };

  // Kéo vạch giữa hai sale trên thanh chia.
  const thanh = useRef<HTMLDivElement>(null);
  const keo = useRef<{ i: number; x0: number; w: number; p0: number[] } | null>(null);
  const batDauKeo = (i: number) => (e: PE<HTMLSpanElement>) => {
    if (!thanh.current) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    keo.current = { i, x0: e.clientX, w: thanh.current.getBoundingClientRect().width, p0: ptDs };
  };
  const dangKeo = (e: PE<HTMLSpanElement>) => {
    const k = keo.current;
    if (!k || !k.w) return;
    const moi = keoVach(k.p0, k.i, (e.clientX - k.x0) / k.w * 100);
    datPt(p => ({ ...p, ...Object.fromEntries(nguoiHien.map((n, j) => [n.ma, moi[j]])) }));
  };
  const phimVach = (i: number) => (e: KeyboardEvent<HTMLSpanElement>) => {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    datPt(p => {   // đọc % MỚI NHẤT (giữ phím là nhiều lần bấm trước một lần vẽ)
      const moi = keoVach(nguoiHien.map(n => p[n.ma] ?? 0), i, d);
      return { ...p, ...Object.fromEntries(nguoiHien.map((n, j) => [n.ma, moi[j]])) };
    });
  };

  const ky0 = m.thang[0], ky1 = m.thang[m.thang.length - 1];
  const tenThang = (th: string) => { const [y, t] = th.split("-"); return `T${+t}/${y}`; };
  const thNgan = (th: string) => `T${+th.slice(5)}`;
  const maxNT = (c: ChiSo) => Math.max(1, ...(c === "doanh_thu" ? ntDt : ntLg).filter(laSo));

  const conO = (c: ChiSo, th: string) => {
    const tc = so(khoa(ct, c, th)), ng = cuaNguoi(c, th);
    if (tc == null) return <span className="ns-con trong">—</span>;
    if (!ng.length) return <span className="ns-con thieu" title="Chưa chia cho ai">chưa chia</span>;
    const d = tc - cong(ng);
    return d === 0 ? <span className="ns-con du" title="Chia đủ">✓</span>
      : d > 0 ? <span className="ns-con thieu" title={`Còn ${yen(d)} chưa chia`}>{gon(d)}</span>
      : <span className="ns-con vuot" title={`Chia vượt ${yen(-d)}`}>vượt {gon(-d)}</span>;
  };

  return (
    <div className="sp ns">
      <div className="tieu-de-trang">
        <div><h1>Ngân sách · Kỳ {m.ky}</h1>
          <div className="phu">{tenThang(ky0)} → {tenThang(ky1)} · <a href={`/bao-cao?ky=${m.ky}`}>← Doanh thu</a>{" "}
            <ONoi nhan="Cách dùng" className="khoi-i" noi_dung={<div className="o-noi-chu">
              Ngân sách công ty là số NHẬP THẲNG — Tổng quan, Doanh thu và Dự báo so tiến độ với nó; chỉ tiêu từng sale dùng cho thanh
              tiến độ từng người (không bắt buộc). Ô trống = chưa đặt (khác 0). Enter / ↑↓ đi dòng · dán được cả khối từ Excel.
              "Điền vào 12 tháng" chỉ đổi ô, chưa lưu gì cho tới khi bấm Lưu.</div>}>ⓘ</ONoi></div></div>
        <nav className="sp-dau-phai ns-ky" aria-label="Kỳ kế toán">
          {/* Chỉ kỳ trước · kỳ này · kỳ sau — 11 nút kỳ là 11 chữ không ai đọc. */}
          {m.moi_ky.filter(k => Math.abs(k - m.ky) <= 1).map(k => <a key={k} href={`/ngan-sach?ky=${k}`} className="nut-nho"
            aria-current={k === m.ky ? "page" : undefined}>{k < m.ky ? "‹ " : ""}Kỳ {k}{k > m.ky ? " ›" : ""}</a>)}
        </nav>
      </div>

      {m.loi.length > 0 && <div className="ngay-thieu" role="alert">Có {m.loi.length} ô không đọc được thành số —{" "}
        <strong>chưa ô nào được lưu</strong>. Sửa những ô viền đỏ rồi bấm Lưu lại.</div>}

      <section className="kh-the ns-dat">
        <div className="ns-dat-hai">
          <div>
            <div className="ns-nhan">① Công ty cả kỳ {tongNT > 0 && <span className="nhat-chu">· năm trước {gon(tongNT)}</span>}
              {coDt.length > 0 && coDt.length < m.thang.length && <span className="nhat-chu"> · đã đặt {coDt.length}/12 tháng ({gon(cong(coDt))})</span>}</div>
            <div className="ns-dong">
              <input className="ns-o-lon" inputMode="numeric" aria-label="Tổng doanh thu công ty cả kỳ"
                placeholder={tongNT > 0 ? cham(tongNT) : "1,560,000,000"}
                value={tongTxt} onChange={e => datTongTxt(e.target.value)} />
              {tongGo != null && tongNT > 0 && <span className={tongGo >= tongNT ? "tang" : "giam"}>{tongGo >= tongNT ? "+" : ""}{pc(tongGo / tongNT - 1)}</span>}
            </div>
            <div className="ns-dong">
              <label className="nhat-chu">Biên lãi gộp <input className="ns-o-pt" inputMode="decimal" aria-label="Biên lãi gộp %" value={bienTxt}
                placeholder={bienNT != null ? String(Math.round(bienNT * 1000) / 10) : "28"} onChange={e => datBienTxt(e.target.value)} />%</label>
              {tongGo != null && bienGo != null && <span className="nhat-chu">= {gon(Math.round(tongGo * bienGo / 100))}</span>}
            </div>
            <MuaNamTruoc v={ntDt} />
          </div>
          <div>
            <div className="ns-nhan">② Chia cho {nguoiHien.length} sale</div>
            {nguoiHien.length > 0 ? <>
              <div className="ns-chia" ref={thanh} role="group" aria-label="Tỷ lệ chia cho từng sale">
                {nguoiHien.map((n, j) => <span key={n.ma} className="ns-chia-phan"
                  style={{ flexGrow: Math.max(ptDs[j], 0.0001), background: MAU_SALE[j % MAU_SALE.length] }}>
                  {ptDs[j] >= 8 && <b>{n.ten.split(" ").slice(-1)[0]} {ptDs[j]}%</b>}
                  {j < nguoiHien.length - 1 && <span className="ns-vach" role="slider" tabIndex={0} aria-label={`Vạch giữa ${n.ten} và ${nguoiHien[j + 1].ten}`}
                    aria-valuenow={ptDs[j]} aria-valuemin={0} aria-valuemax={100}
                    onPointerDown={batDauKeo(j)} onPointerMove={dangKeo} onPointerUp={() => { keo.current = null; }} onKeyDown={phimVach(j)} />}
                </span>)}
                {tongPt < 100 && <span className="ns-chia-phan con" style={{ flexGrow: 100 - tongPt }} />}
              </div>
              <div className="ns-sale-luoi">
                {nguoiHien.map((n, j) => { const nt = ntSale(n.ma); return (
                  <div key={n.ma}>
                    <div className="ns-sale-ten"><i style={{ background: MAU_SALE[j % MAU_SALE.length] }} />{n.ten}</div>
                    <label><input className="ns-o-pt" inputMode="decimal" aria-label={`% của ${n.ten}`} value={String(ptDs[j])}
                      onChange={e => { const v = docPt(e.target.value); datPt(p => ({ ...p, [n.ma]: v == null ? 0 : Math.min(100, Math.round(v)) })); }} />%</label>
                    <b className="so">{tongGo != null ? gon(Math.round(tongGo * ptDs[j] / 100)) : "—"}</b>
                    <div className="nhat-chu">{nt > 0 && tongNT > 0 ? `năm trước ${Math.round(nt / tongNT * 100)}%` : "năm trước —"}</div>
                  </div>); })}
              </div>
              <div className={"ns-con-pt " + (tongPt === 100 ? "du" : tongPt < 100 ? "thieu" : "vuot")}>
                {tongPt === 100 ? "✓ chia đủ 100%" : tongPt < 100 ? `còn ${100 - tongPt}% chưa chia` : `vượt ${tongPt - 100}%`}
                {tongGo != null && tongPt !== 100 && ` · ${gon(Math.abs(Math.round(tongGo * (100 - tongPt) / 100)))}`}
                {" "}<button type="button" className="nut-nho" onClick={() => {
                  const p = phanTramTheo(nguoiHien.map(n => ntSale(n.ma)));
                  datPt(q => ({ ...q, ...Object.fromEntries(nguoiHien.map((n, j) => [n.ma, p[j]])) }));
                }}>Theo năm trước</button>
              </div>
            </> : <p className="nhat-chu">Chưa có sale nào đang bán.</p>}
          </div>
        </div>
        <div className="ns-dat-cuoi">
          <button type="button" className="nut-chinh" disabled={tongGo == null} onClick={dienThang}
            title={tongGo == null ? "Gõ tổng cả kỳ trước" : "Chia tổng theo mùa năm trước, lãi gộp theo biên, từng sale theo %"}>↓ Điền vào 12 tháng</button>
        </div>
      </section>

      <form method="post" action="/ngan-sach" className="ns-form" onSubmit={e => {
        if (sai.length && !confirm(`${sai.length} ô không đọc được thành số — máy chủ sẽ từ chối cả lượt lưu. Vẫn gửi?`)) { e.preventDefault(); return; }
        dangGui.current = true;
      }}>
        <input type="hidden" name="ky" value={m.ky} />

        {/* Cả hai chỉ số luôn trong DOM để Lưu gửi đủ — bảng chỉ số kia ẩn bằng `hidden`. */}
        {HAI_CS.map(c => (
          <section key={c} className="kh-the ns-the" hidden={cs !== c}>
            <div className="ns-bang-dau"><h2>12 tháng</h2>
              <div className="tab-pill" role="group" aria-label="Chỉ số">
                {HAI_CS.map(x => <button key={x} type="button" aria-pressed={cs === x} onClick={() => datCs(x)}>{TEN_CS[x]}</button>)}
              </div>
              <span className="nhat-chu ns-meo">vạch nền = năm trước</span>
            </div>
            <div className="bang-cuon">
              <table className="bang ns-bang">
                <thead><tr><th>Tháng</th><th className="ns-cot-ct">Công ty</th>
                  {nguoiHien.map(n => <th key={n.ma} title={n.ma + (n.con_ban ? "" : ` · không bán ${m.ngay_con_ban} ngày`)}>{n.ten}</th>)}
                  <th>còn</th></tr></thead>
                <tbody>
                  {m.thang.map((th, r) => {
                    const nt = namTruoc(ct, c, th);
                    return <tr key={th}><th scope="row" className="ns-thang" title={nt != null ? `Năm trước ${yen(nt)}` : "Năm trước: không có số"}>{thNgan(th)}</th>
                      <td className="ns-cot-ct">{oNhap(c, r, 0, `Công ty — ${TEN_CS[c]} — ${th}`, nt != null ? nt / maxNT(c) : null)}</td>
                      {nguoiHien.map((n, ci) => <td key={n.ma}>{oNhap(c, r, ci + 1, `${n.ten} — ${TEN_CS[c]} — ${th}`)}</td>)}
                      <td className="so">{conO(c, th)}</td></tr>;
                  })}
                </tbody>
                <tfoot><tr className="tong"><th scope="row">Kỳ</th>
                  <td className="so">{tong(m.thang.map(th => so(khoa(ct, c, th))).filter(laSo))}
                    {c === "lai_gop" && bienKy != null && <small className="ns-nt">biên {pc(bienKy)}</small>}</td>
                  {nguoiHien.map(n => <td key={n.ma} className="so">{tong(m.thang.map(th => so(khoa(n.ma, c, th))).filter(laSo))}</td>)}
                  <td /></tr></tfoot>
              </table>
            </div>
          </section>))}

        {nguoiAn.length > 0 && <p className="ns-an">
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

/** 12 cột nhỏ: mùa của năm trước — hình dáng mà "Điền vào 12 tháng" sẽ chia theo. */
function MuaNamTruoc({ v }: { v: (number | null)[] }) {
  const w = trongSoMua(v), mx = Math.max(...w, 1);
  if (!v.some(laSo)) return <p className="nhat-chu ns-mua-chu">Không có số năm trước — sẽ chia đều 12 tháng.</p>;
  return <>
    <svg viewBox="0 0 240 40" className="ns-mua" role="img" aria-label="Tỷ trọng từng tháng của năm trước">
      {w.map((x, i) => <rect key={i} x={i * 20 + 2} y={40 - (x / mx) * 38} width={15} height={(x / mx) * 38} rx={2}
        className={v[i] == null ? "ns-mua-tb" : "ns-mua-c"}><title>{v[i] == null ? "không có số năm trước — lấy trung bình" : yen(v[i])}</title></rect>)}
    </svg>
    <div className="nhat-chu ns-mua-chu">chia 12 tháng theo mùa năm trước</div>
  </>;
}
