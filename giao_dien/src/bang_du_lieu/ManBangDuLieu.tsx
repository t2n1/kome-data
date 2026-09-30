// Kho dữ liệu › Bảng dữ liệu (đặc tả 2026-09-30-bang-du-lieu-sua §6): bảng tính Sản phẩm / Khách hàng, sửa thẳng trong
// ô, lưu vào sổ app.sua_du_lieu (chồng lên OBC — core vẫn chỉ đọc). Dữ liệu LÀ bộ đệm của truy vấn ["bdl", loai] (không có
// bản sao riêng); ô chưa lưu là `s.cho` (khoaO → chữ đã chuẩn hoá). Lưu xong VÁ các dòng máy chủ đọc lại vào đệm — dòng
// đọc lại KHÔNG mang chỉ số chỉ xem (dt_12t, lan_cuoi) nên GỘP `o` vào dòng cũ, không thay cả dòng. `thay` của mỗi ô =
// chữ máy chủ GHI LẠI lúc ô vào chờ (`s.thay`, logic.ts::datChoO) — KHÔNG đọc lại từ đệm lúc lưu: đệm bị thay (tải lại,
// "Lấy bản mới", dòng đọc lại mang số người khác vừa ghi) thì ô đang chờ vẫn so với cái người sửa đã thấy → 409 đúng lúc.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { gui, lay, LoiApi } from "../api";
import { gio_tokyo, ngay, so } from "../dinh_dang";
import { KhungKho } from "../he_thong/TabKho";
import "../he_thong/he_thong.css";
import { giuKhoang } from "../khung/khoang";
import { BangTinh } from "./BangTinh";
import "./bang_du_lieu.css";
import type { BangApi, ChoLuu, Cot, Dong, Lech } from "./kieu";
import { boCho, CHO_RONG, cotMacDinh, docCotDaChon, ghiCotDaChon, ghiDeCho, hienThi, khoaO, locDong, loiCho, sauLuu, tachO,
  thanLuu } from "./logic";

type Loai = "sp" | "kh";
type XungDot = { k: string; cot: string; gia_tri: string | null; ai: string | null; luc: string | null };
type KetQuaLuu = { dong: Dong[]; lech: Lech; so_o: number };

const TAB: [Loai, string][] = [["sp", "Sản phẩm"], ["kh", "Khách hàng"]];
const docLoai = (): Loai => (new URLSearchParams(location.search).get("loai") === "kh" ? "kh" : "sp");
const boKhoa = <T,>(o: Record<string, T>, ko: Iterable<string>): Record<string, T> => {
  const n = { ...o };
  for (const k of ko) delete n[k];
  return n;
};

export default function ManBangDuLieu() {
  const qc = useQueryClient();
  const [loai, datLoai] = useState<Loai>(docLoai);
  const khoaQ = useMemo(() => ["bdl", loai], [loai]);
  // Không tự tải lại (đổi cửa sổ / có mạng lại): tải lại thay đệm giữa lúc đang sửa — `thay` đã ghi nên không mất cập nhật,
  // nhưng ô chờ sẽ 409 vô cớ nếu chính mình vừa lưu ở thẻ khác. Tải lại chỉ khi người ta chọn ("Lấy bản mới", F5).
  const q = useQuery({ queryKey: khoaQ, queryFn: () => lay<BangApi>("/api/kho-du-lieu/bang-du-lieu?loai=" + loai),
    refetchOnWindowFocus: false, refetchOnReconnect: false });
  const data = q.data;

  const [s, datS] = useState<ChoLuu>(CHO_RONG);
  const sRef = useRef(s); sRef.current = s;
  const cho = s.cho;
  const [muonLuu, datMuonLuu] = useState(false);   // yêu cầu lưu SAU lần vẽ kế (khi chờ đã nhận ô vừa đóng)
  const [oLoi, datOLoi] = useState<Record<string, string>>({});
  const [xung, datXung] = useState<XungDot[] | null>(null);
  const [tim, datTim] = useState("");
  const [chiLech, datChiLech] = useState(false);
  const [moCot, datMoCot] = useState(false);
  const [cotLoai, datCotLoai] = useState<Partial<Record<Loai, string[]>>>({});
  const [bao, datBao] = useState<string | null>(null);
  const [dangLuu, datDangLuu] = useState(false);
  const soCho = Object.keys(cho).length;

  // Rời trang khi còn ô chưa lưu → trình duyệt hỏi.
  useEffect(() => {
    if (!soCho) return;
    const f = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ""; };
    addEventListener("beforeunload", f);
    return () => removeEventListener("beforeunload", f);
  }, [soCho]);

  const doiTab = (l: Loai) => {
    if (l === loai) return;
    const n = Object.keys(sRef.current.cho).length;
    if (n && !confirm(`Còn ${so(n)} ô chưa lưu — bỏ các ô đó và chuyển bảng?`)) return;
    datS(CHO_RONG); datOLoi({}); datXung(null); datBao(null); datChiLech(false); datTim("");   // ô tìm của bảng kia vô nghĩa ở đây
    datLoai(l);
    const p = new URLSearchParams(location.search);
    if (l === "kh") p.set("loai", "kh"); else p.delete("loai");
    const qs = p.toString();
    history.replaceState(null, "", giuKhoang(location.pathname + (qs ? "?" + qs : "") + location.hash));
  };

  // Cột đang hiện: lựa chọn của phiên này, không thì đã nhớ ở máy này (localStorage), không nữa thì mặc định.
  const chonMa = useMemo(() => {
    if (!data) return [];
    const co = new Set(data.cot.map(c => c.ma));
    return cotLoai[loai] ?? docCotDaChon(loai)?.filter(m => co.has(m)) ?? cotMacDinh(loai, data.cot);
  }, [data, cotLoai, loai]);
  const cots = useMemo(() => { const s = new Set(chonMa); return (data?.cot ?? []).filter(c => s.has(c.ma)); }, [data, chonMa]);
  const datCot = (ds: string[]) => {
    const s = new Set(ds), moi = (data?.cot ?? []).map(c => c.ma).filter(m => s.has(m));
    datCotLoai(x => ({ ...x, [loai]: moi }));
    ghiCotDaChon(loai, moi);
  };
  const nhom = useMemo(() => {
    const m = new Map<string, Cot[]>();
    for (const c of data?.cot ?? []) { const g = m.get(c.nhom); if (g) g.push(c); else m.set(c.nhom, [c]); }
    return [...m];
  }, [data]);

  const dongs = useMemo(() => (data ? locDong(data.dong, tim, chiLech, data.lech) : []), [data, tim, chiLech]);
  const soLech = data ? Object.keys(data.lech).length : 0;

  const doiCho = useCallback((f: (x: ChoLuu) => ChoLuu, ko: string[]) => {
    datS(f);
    if (ko.length) datOLoi(o => (ko.some(k => k in o) ? boKhoa(o, ko) : o));
  }, []);

  /** Vá đệm bằng các dòng máy chủ đọc lại: GỘP `o` (giữ chỉ số chỉ xem), thay `lech` của đúng các dòng đó. */
  const va = (r: KetQuaLuu) => qc.setQueryData<BangApi>(khoaQ, d => {
    if (!d) return d;
    const moi = new Map(r.dong.map(x => [x.k, x]));
    const lech: Lech = {};
    for (const [ko, v] of Object.entries(d.lech)) if (!moi.has(tachO(ko)[0])) lech[ko] = v;
    Object.assign(lech, r.lech);
    return { ...d, lech, dong: d.dong.map(x => { const m = moi.get(x.k); return m ? { k: x.k, o: { ...x.o, ...m.o } } : x; }) };
  });

  const luu = async () => {
    const d = qc.getQueryData<BangApi>(khoaQ);
    if (!d || dangLuu || !d.sua_duoc) return;
    const hien = sRef.current;
    const than = thanLuu(loai, hien, d.dong);
    if (!than.o.length) return;
    const cotTheoMa = new Map(d.cot.map(c => [c.ma, c]));
    const sai = than.o.filter(x => { const c = cotTheoMa.get(x.cot); return !c || loiCho(c, khoaO(x.k, x.cot), hien.cho, d.lech) != null; });
    if (sai.length) { datBao(`${so(sai.length)} ô chưa hợp lệ (viền đỏ) — sửa lại hoặc Huỷ trước khi lưu.`); return; }
    datDangLuu(true); datBao(null);
    try {
      const r = await gui<KetQuaLuu>("/api/kho-du-lieu/bang-du-lieu/luu", than);
      va(r);
      // Ô ĐÃ GỬI rời chờ; ô bị gõ lại trong lúc chờ máy chủ vẫn chờ, `thay` = giá trị vừa lưu.
      datS(x => sauLuu(x, than.o, r.dong));
      datOLoi({}); datXung(null);
      datBao(`Đã lưu ${so(r.so_o)} ô.`);
      qc.invalidateQueries({ predicate: x => x.queryKey[0] !== "bdl" });   // màn khác đọc số hiệu lực mới
    } catch (e) {
      if (e instanceof LoiApi && e.ma === 400) {
        const ol = (e.du_lieu as { o_loi?: Record<string, string> } | undefined)?.o_loi ?? {};
        const m: Record<string, string> = {};
        for (const [ko, loi] of Object.entries(ol)) {
          const i = /^#(\d+)$/.exec(ko);                    // ô sai dạng: máy chủ gọi theo thứ tự trong thân
          const x = i ? than.o[Number(i[1])] : undefined;
          m[x ? khoaO(x.k, x.cot) : ko] = loi;
        }
        datOLoi(m);
        datBao(e.message + (Object.keys(m).length ? ` (${so(Object.keys(m).length)} ô viền đỏ — rê chuột để xem)` : ""));
      } else if (e instanceof LoiApi && e.ma === 409) {
        const x = (e.du_lieu as { xung_dot?: XungDot[] } | undefined)?.xung_dot ?? [];
        datXung(x);
        datOLoi(Object.fromEntries(x.map(y => [khoaO(y.k, y.cot), "Vừa bị đổi ở nơi khác"])));
      } else datBao(e instanceof Error ? e.message : String(e));
    } finally { datDangLuu(false); }
  };

  const layBanMoi = () => {
    if (!xung) return;
    const ko = xung.map(x => khoaO(x.k, x.cot));
    // CHỈ các ô xung đột rời chờ; ô chờ khác giữ `thay` đã ghi (tải lại không "rebase" chúng lên số mới).
    datS(x => boCho(x, ko)); datOLoi({}); datXung(null);
    qc.invalidateQueries({ queryKey: khoaQ, exact: true });
    datBao("Đã tải bản mới — các ô xung đột bỏ phần bạn đã gõ.");
  };
  const ghiDe = () => {
    if (!xung) return;
    // `thay` của ĐÚNG các ô xung đột = giá trị máy chủ hiện giờ, rồi gửi lại cùng `cho` (sau lần vẽ kế).
    const x0 = xung;
    datS(x => ghiDeCho(x, x0)); datXung(null); datOLoi({});
    datMuonLuu(true);
  };
  const huy = () => {
    if (soCho && !confirm(`Bỏ ${so(soCho)} ô chưa lưu?`)) return;
    datS(CHO_RONG); datOLoi({}); datXung(null); datBao(null);
  };
  // Lưu theo yêu cầu (Ctrl+S trong ô sửa, Ghi đè): chạy SAU lần vẽ mà `s` đã nhận mọi thay đổi vừa đặt.
  useEffect(() => {
    if (!muonLuu) return;
    datMuonLuu(false);
    void luu();
  });   // eslint-disable-line react-hooks/exhaustive-deps
  const yeuCauLuu = useCallback(() => datMuonLuu(true), []);

  // Ctrl/⌘+S = Lưu (trình duyệt mặc định là "lưu trang"). Trong ô sửa: OSua đóng ô rồi gọi `yeuCauLuu`.
  const phimMan = (e: KeyboardEvent<HTMLDivElement>) => {
    if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === "s" && data?.sua_duoc) { e.preventDefault(); void luu(); }
  };

  const tenCot = (ma: string) => data?.cot.find(c => c.ma === ma);

  return (
    <KhungKho dang="bang-du-lieu" lop="kdl bdl">
      <div onKeyDown={phimMan}>
        <div className="bdl-dau">
          <h1>Bảng dữ liệu</h1>
          <div className="bdl-tab" role="group" aria-label="Bảng">
            {TAB.map(([ma, nhan]) => (
              <button key={ma} type="button" className="kdl-chip" aria-pressed={loai === ma} onClick={() => doiTab(ma)}>{nhan}</button>))}
          </div>
        </div>
        <p className="ghi-chu">Sửa thẳng trong ô. Bản sửa lưu vào sổ riêng và chồng lên số OBC trên mọi màn — dữ liệu OBC gốc
          không đổi; sửa ở OBC rồi nạp lại thì số OBC mới được hiện.</p>
        {data && !data.sua_duoc && (
          <p className="bdl-chi-xem" role="note">Chỉ xem — cần cờ “Sửa dữ liệu” (Cài đặt) để sửa.</p>)}

        {q.isError ? <div className="khoi-loi">{(q.error as Error).message}</div>
          : !data ? <p className="khong-ap-dung">Đang tải…</p> : <>
            <div className="bdl-cong-cu">
              <input type="search" placeholder="Tìm mã, tên, số điện thoại… (không cần dấu)" aria-label="Tìm trong bảng"
                value={tim} onChange={e => datTim(e.target.value)} />
              <button type="button" className="kdl-chip" aria-expanded={moCot} aria-controls="bdl-chon-cot"
                onClick={() => datMoCot(v => !v)}>Chọn cột ({so(cots.length)}/{so(data.cot.length)})</button>
              <button type="button" className="kdl-chip" aria-pressed={chiLech} onClick={() => datChiLech(v => !v)}>
                Đã sửa trên web, OBC chưa có ({so(soLech)} ô)</button>
              <span className="bdl-dem-dong">{so(dongs.length)}{dongs.length !== data.dong.length ? ` / ${so(data.dong.length)}` : ""} dòng</span>
              {data.sua_duoc && <>
                <span className="bdl-so-cho" aria-live="polite">{soCho ? `${so(soCho)} ô chưa lưu` : ""}</span>
                <button type="button" className="kdl-chip" disabled={!soCho || dangLuu} onClick={huy}>Huỷ</button>
                <button type="button" className={soCho ? "nut-chinh" : "kdl-chip"} disabled={!soCho || dangLuu}
                  onClick={() => void luu()} title="Ctrl+S">{dangLuu ? "Đang lưu…" : "Lưu"}</button>
              </>}
            </div>
            {bao && <p className="bdl-bao" role="status">{bao}</p>}
            {xung && (
              <div className="bdl-xung" role="alert">
                <p><b>{so(xung.length)} ô vừa bị đổi ở nơi khác</b> (người khác sửa hoặc lần nạp OBC) — chưa lưu ô nào.</p>
                <ul>
                  {xung.slice(0, 5).map(x => {
                    const c = tenCot(x.cot);
                    return <li key={khoaO(x.k, x.cot)}>{x.k} · {c?.nhan ?? x.cot}: nay là “{(c ? hienThi(c, x.gia_tri) : x.gia_tri) || "(trống)"}”
                      {x.ai || x.luc ? ` — ${x.ai ?? "sửa trên web"} lúc ${gio_tokyo(x.luc) || "?"}` : " — từ lần nạp OBC"}</li>;
                  })}
                  {xung.length > 5 && <li>… và {so(xung.length - 5)} ô khác</li>}
                </ul>
                <button type="button" className="kdl-chip" onClick={layBanMoi}>Lấy bản mới</button>{" "}
                <button type="button" className="nut-chinh" onClick={ghiDe}>Ghi đè</button>
              </div>)}
            <div className="bdl-than">
              {moCot && (
                <div id="bdl-chon-cot" className="bdl-chon-cot">
                  <div className="bdl-chon-cot-nut">
                    <button type="button" className="kdl-chip" onClick={() => datCot(cotMacDinh(loai, data.cot))}>Mặc định</button>
                    <button type="button" className="kdl-chip" onClick={() => datCot(data.cot.map(c => c.ma))}>Tất cả</button>
                  </div>
                  {nhom.map(([ten, ds]) => (
                    <fieldset key={ten}>
                      <legend>{ten}</legend>
                      {ds.map(c => (
                        <label key={c.ma}>
                          <input type="checkbox" checked={chonMa.includes(c.ma)}
                            onChange={e => datCot(e.target.checked ? [...chonMa, c.ma] : chonMa.filter(m => m !== c.ma))} />
                          {c.nhan}{!c.sua && <span title="Chỉ xem" aria-label="chỉ xem"> 🔒</span>}
                        </label>))}
                    </fieldset>))}
                </div>)}
              <BangTinh cots={cots} dongs={dongs} s={s} lech={data.lech} oLoi={oLoi} suaDuoc={data.sua_duoc}
                doiCho={doiCho} bao={datBao} luu={yeuCauLuu} />
            </div>
            <div className="bdl-chu-thich">
              <p><span className="bdl-mau bdl-mau-cho" aria-hidden="true" /> nền vàng = chưa lưu ·{" "}
                <span className="bdl-mau bdl-mau-lech" aria-hidden="true" /> vạch trái = đã sửa trên web, khác OBC (rê chuột xem số
                OBC; ↺ = về giá trị OBC) · 🔒 = chỉ xem · ô xám = OBC không có ô này.</p>
              <p>Phím: mũi tên di chuyển · Enter / F2 / gõ chữ để sửa · Esc bỏ · Enter / Tab lưu vào chờ rồi đi tiếp · Delete xoá ô ·
                dán khối từ Excel vào ô đang chọn · Ctrl+S lưu.</p>
              {loai === "sp" && <>
                <p>Số tồn đổi mỗi ngày: bản sửa số tồn chỉ giữ tới khi ảnh chụp 在庫一覧 sau ghi khác.</p>
                <p>Ảnh chụp tồn: <b>{ngay(data.anh_ton)}</b> · Lần nạp giá gần nhất: <b>{ngay(data.lan_nap_gia)}</b></p>
              </>}
            </div>
          </>}
      </div>
    </KhungKho>);
}
