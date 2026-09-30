// Bảng tính của màn "Bảng dữ liệu" (đặc tả 2026-09-30-bang-du-lieu-sua §6). Chỉ vẽ + bàn phím + chuột + dán: mọi LUẬT
// (chữ trong ô, kiểm ô, chờ lưu, dán TSV, khung nhìn) ở logic.ts; di chuyển ô dùng CHÍNH bang_sua_logic.ts::neoKeTiep.
// - Chỉ vẽ các dòng trong khung nhìn (dòng cao CỐ ĐỊNH `CAO_DONG`) + hai <tr> đệm — 2.142 khách không vẽ một lúc.
//   Khoảng dòng đang vẽ là STATE, chỉ đổi khi khoảng đổi (cuộn từng điểm ảnh không vẽ lại cả khung nhìn).
// - Ô chọn / ô đang sửa NEO theo KHOÁ dòng + MÃ cột (`O {k, ma}`): lọc ô tìm làm chỉ số dòng trượt, bật / tắt cột làm chỉ
//   số cột trượt — neo theo chỉ số là Enter ghi nhầm ô. Chỉ số (`Neo {k, c}` của neoKeTiep) chỉ suy ra lúc cần.
// - Chữ đang gõ ở state RIÊNG của ô sửa (gõ phím không vẽ lại cả bảng); bản sao ở `nhap` để cuộn dòng đang sửa ra khỏi
//   khung nhìn vẫn lưu được chữ đó vào chờ (dòng sắp bị gỡ khỏi DOM).
// - Tiêu điểm trả về ô bằng useEffect sau lần vẽ kế (không rAF: rAF không chạy khi thẻ trình duyệt bị ẩn).
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ClipboardEvent, type KeyboardEvent, type MutableRefObject } from "react";
import { gio_tokyo, so } from "../dinh_dang";
import { neoKeTiep, viTriNeo, type Huong, type Neo } from "../doi_thu/bang_sua_logic";
import type { ChoLuu, Cot, Dong, Lech } from "./kieu";
import { dan, datChoO, giaTri, hienThi, khoaO, khungNhin, kiemO, KHONG_HAN, loiCho, suaDuocO } from "./logic";

export const CAO_DONG = 30;
type CotDiChuyen = Parameters<typeof neoKeTiep>[3][number];
/** Một ô: khoá dòng + mã cột. */
type O = { k: string; ma: string };
/** Cách ô sửa đóng: sang ô kế (Enter / Tab) · ở lại (chọn bằng chuột, "không hạn", Ctrl+S) · rời đi (blur). */
type Ket = Huong | "giu" | null;
type Sua = { o: O; dau: string; phien: number };

export type PropsBangTinh = {
  cots: Cot[]; dongs: Dong[]; s: ChoLuu; lech: Lech;
  /** Lỗi ô máy chủ trả (400) hoặc xung đột (409), khoá `khoaO`. */
  oLoi: Record<string, string>;
  /** Cờ quyền "Sửa dữ liệu" của người đang xem. false = mọi ô chỉ xem. */
  suaDuoc: boolean;
  /** Đổi trạng thái chờ (hàm thuần trên bản mới nhất) — `ko` = các ô vừa đụng (màn bỏ lỗi máy chủ cũ của chúng). */
  doiCho: (f: (s: ChoLuu) => ChoLuu, ko: string[]) => void;
  bao: (chu: string) => void;
  /** Ctrl/⌘+S trong ô sửa: ô sửa đã đóng (chữ vào chờ) — màn lưu SAU lần vẽ kế (khi chờ đã có ô đó). */
  luu: () => void;
};

function OSua({ cot, dau, nhap, xong, bo, luu }: {
  cot: Cot; dau: string; nhap: MutableRefObject<string>; xong: (gt: string, h: Ket) => void; bo: () => void; luu: () => void;
}) {
  const [gt, datGt0] = useState(dau);
  const daXong = useRef(false);
  const chuot = useRef(false);
  useLayoutEffect(() => { nhap.current = dau; }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  const datGt = (v: string) => { nhap.current = v; datGt0(v); };
  const ket = (h: Ket, v = gt) => { if (daXong.current) return; daXong.current = true; xong(v, h); };
  const phim = (e: KeyboardEvent) => {
    chuot.current = false;
    if (e.key === "Enter") { e.preventDefault(); ket("xuong"); }
    else if (e.key === "Tab") { e.preventDefault(); ket(e.shiftKey ? "tab_lui" : "tab"); }
    else if (e.key === "Escape") { e.preventDefault(); daXong.current = true; bo(); }
    // Ctrl/⌘+S: không để trình duyệt mở "Lưu trang" — đóng ô (chữ vào chờ) rồi lưu.
    else if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === "s") { e.preventDefault(); ket("giu"); luu(); }
    e.stopPropagation();
  };
  if (cot.kieu === "chon") {
    const ds = cot.chon ?? [];
    // Chọn bằng CHUỘT xong ngay; bằng bàn phím chỉ đổi giá trị (Windows bắn `change` ở mỗi mũi tên trên ô đóng) —
    // xong khi Enter / Tab / rời ô, Esc vẫn bỏ được.
    return (
      <select autoFocus className="bdl-sua" aria-label={cot.nhan} value={gt} onKeyDown={phim} onBlur={() => ket(null)}
        onPointerDown={() => { chuot.current = true; }}
        onChange={e => { datGt(e.target.value); if (chuot.current) ket("giu", e.target.value); }}>
        {!ds.some(([m]) => m === gt) && <option value={gt}>{gt || "—"}</option>}
        {ds.map(([m, n]) => <option key={m} value={m}>{n}</option>)}
      </select>);
  }
  if (cot.kieu === "ngay")
    return (
      <span className="bdl-sua-ngay">
        <input type="date" autoFocus className="bdl-sua" aria-label={cot.nhan} value={gt === KHONG_HAN ? "" : gt}
          onChange={e => datGt(e.target.value)} onKeyDown={phim} onBlur={() => ket(null)} />
        {/* mousedown không lấy tiêu điểm: ô ngày không blur (blur = lưu ngày) trước khi nút kịp bấm. */}
        <button type="button" className="bdl-khong-han" tabIndex={-1} aria-pressed={gt === KHONG_HAN}
          onMouseDown={e => e.preventDefault()} onClick={() => ket("giu", KHONG_HAN)}>{KHONG_HAN}</button>
      </span>);
  return <input autoFocus className={"bdl-sua" + (cot.kieu === "so" ? " bdl-so" : "")} aria-label={cot.nhan} value={gt}
    inputMode={cot.kieu === "so" ? "decimal" : undefined} onChange={e => datGt(e.target.value)} onKeyDown={phim}
    onBlur={() => ket(null)} onFocus={e => { const n = e.target.value.length; e.target.setSelectionRange(n, n); }} />;
}

const cung = (a: O | null | undefined, b: O | null | undefined) => !!a && !!b && a.k === b.k && a.ma === b.ma;

export function BangTinh({ cots, dongs, s, lech, oLoi, suaDuoc, doiCho, bao, luu }: PropsBangTinh) {
  const cho = s.cho;
  const [chon, datChon] = useState<O | null>(null);
  const [sua, datSua] = useState<Sua | null>(null);
  const [khoang, datKhoang] = useState({ dau: 0, cuoi: 0 });
  const [cao, datCao] = useState(600);
  const khung = useRef<HTMLDivElement>(null);
  const dauBang = useRef<HTMLTableSectionElement>(null);
  const nhap = useRef("");
  const phien = useRef(0);
  const choTapTrung = useRef<O | null>(null);
  const oVuaCo = useRef<HTMLElement | null>(null);   // ô vừa có tiêu điểm — bị gỡ khỏi DOM (cuộn đi) thì giữ tiêu điểm ở khung
  const chonC = useRef(0);                            // chỉ số cột gần nhất của ô chọn — cột đó bị ẩn thì rơi về cột cạnh

  const khoa = useMemo(() => dongs.map(d => d.k), [dongs]);
  const theoK = useMemo(() => new Map(dongs.map(d => [d.k, d])), [dongs]);
  const cotMa = useMemo(() => new Map(cots.map(c => [c.ma, c])), [cots]);
  const viTriCot = useMemo(() => new Map(cots.map((c, i) => [c.ma, i])), [cots]);
  // Cột cho neoKeTiep: kieu null = Tab bỏ qua (chỉ xem). Luật "ô OBC không có" theo từng DÒNG nên xét riêng (`duocSua`).
  const cotDi = useMemo<CotDiChuyen[]>(() => cots.map(c => ({ ma: c.ma as CotDiChuyen["ma"], nhan: c.nhan,
    kieu: suaDuoc && c.sua ? "chu" : null })), [cots, suaDuoc]);
  const duocSua = (d: Dong | undefined, c: Cot | undefined): d is Dong => !!d && !!c && suaDuoc && suaDuocO(d, c);
  const neo = (o: O): Neo | null => { const c = viTriCot.get(o.ma); return c == null ? null : { k: o.k, c }; };
  const tuNeo = (n: Neo): O => ({ k: n.k, ma: cots[n.c].ma });

  useLayoutEffect(() => {
    const el = khung.current;
    if (!el) return;
    datCao(el.clientHeight);
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => datCao(el.clientHeight));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  /** Khoảng dòng cần vẽ ở vị trí cuộn `st` — đổi state CHỈ khi khoảng đổi. */
  const capNhatKhoang = (st: number) => {
    const r = khungNhin(st, cao, dongs.length, CAO_DONG);
    datKhoang(k => (k.dau === r.dau && k.cuoi === r.cuoi ? k : r));
    return r;
  };
  // Sau mỗi lần vẽ (trước khi trình duyệt vẽ lên màn): số dòng / chiều cao đổi, hoặc danh sách co lại (lọc ô tìm) làm
  // trình duyệt tự kẹp scrollTop mà KHÔNG bắn `scroll` — không đồng bộ là khung trống.
  useLayoutEffect(() => { if (khung.current) capNhatKhoang(khung.current.scrollTop); });

  // Cột của ô chọn bị ẩn (khung "Chọn cột") → sang cột đứng ở chỗ đó bây giờ (hoặc cột cuối); hết cột thì bỏ chọn.
  useEffect(() => {
    if (!chon || viTriCot.has(chon.ma)) return;
    datChon(cots.length ? { k: chon.k, ma: cots[Math.min(chonC.current, cots.length - 1)].ma } : null);
  }, [chon, cots, viTriCot]);
  if (chon) { const c = viTriCot.get(chon.ma); if (c != null) chonC.current = c; }
  // Dòng / cột của ô đang sửa không còn (lọc ô tìm, ẩn cột) → đóng ô sửa (chữ đã gõ vào chờ khi ô blur).
  useEffect(() => { if (sua && (!theoK.has(sua.o.k) || !viTriCot.has(sua.o.ma))) datSua(null); }, [sua, theoK, viTriCot]);

  /** Hẹn tiêu điểm về ô `o` (sau lần vẽ kế) và cuộn tới nó. */
  const tapTrung = (o: O) => { choTapTrung.current = o; hienDong(o); };
  /** Cuộn khung để dòng của `o` nằm trong vùng thấy được (dưới dòng tiêu đề đứng yên) — dòng ngoài khung nhìn chưa vẽ. */
  const hienDong = (o: O) => {
    const el = khung.current, i = khoa.indexOf(o.k);
    if (!el || i < 0) return;
    const tieuDe = dauBang.current?.offsetHeight ?? 0;
    let st = el.scrollTop;
    if (i * CAO_DONG < st) st = i * CAO_DONG;
    else if (tieuDe + (i + 1) * CAO_DONG > st + el.clientHeight) st = tieuDe + (i + 1) * CAO_DONG - el.clientHeight;
    if (st !== el.scrollTop) { el.scrollTop = st; capNhatKhoang(el.scrollTop); }
  };
  useEffect(() => {
    const el = khung.current;
    const o = choTapTrung.current;
    if (o && el) {
      const td = el.querySelector<HTMLElement>(`tr[data-k="${CSS.escape(o.k)}"] > td[data-ma="${CSS.escape(o.ma)}"]`);
      if (td) {
        choTapTrung.current = null;
        // Ngang: cột Mã đứng yên che mất phần trái — tự cuộn, rồi focus không cuộn thêm.
        const ma = el.querySelector<HTMLElement>("thead th.bdl-ma")?.offsetWidth ?? 0;
        if (td.offsetLeft < el.scrollLeft + ma) el.scrollLeft = Math.max(0, td.offsetLeft - ma);
        else if (td.offsetLeft + td.offsetWidth > el.scrollLeft + el.clientWidth) el.scrollLeft = td.offsetLeft + td.offsetWidth - el.clientWidth;
        td.focus({ preventScroll: true });
        return;
      }
      if (!khoa.includes(o.k) || !viTriCot.has(o.ma)) choTapTrung.current = null;   // ô đã đi — không chờ mãi
    }
    // Ô đang có tiêu điểm bị cuộn ra khỏi khung nhìn (gỡ khỏi DOM) → tiêu điểm về khung, phím mũi tên vẫn chạy.
    if (el && oVuaCo.current && !oVuaCo.current.isConnected && document.activeElement === document.body) {
      oVuaCo.current = null;
      el.focus({ preventScroll: true });
    }
  });

  /** Ô kế tiếp; Tab / Shift+Tab bỏ qua ô không sửa được (kể cả ô OBC không có của từng dòng). */
  const keTiep = (o: O, h: Huong): O | null => {
    const n0 = neo(o);
    if (!n0) return null;
    let v = neoKeTiep(khoa, n0, h, cotDi);
    if (h === "tab" || h === "tab_lui")
      while (v && !duocSua(theoK.get(v.k), cots[v.c])) v = neoKeTiep(khoa, v, h, cotDi);
    return v && tuNeo(v);
  };

  const moSua = (o: O, dau?: string) => {
    const d = theoK.get(o.k), c = cotMa.get(o.ma);
    if (!c || !duocSua(d, c)) return false;
    let v = dau ?? giaTri(d, c.ma, cho) ?? "";
    if (dau == null && c.kieu === "so") { const r = kiemO(c, v); if ("gt" in r) v = r.gt; }   // "20.0000" → "20"
    phien.current++;
    datChon(o);
    datSua({ o, dau: v, phien: phien.current });
    hienDong(o);                                            // Enter khi tiêu điểm ở khung (dòng chọn đã cuộn đi)
    return true;
  };

  const xongSua = (o: O, gt: string, h: Ket) => {
    datSua(null);
    const d = theoK.get(o.k), c = cotMa.get(o.ma);
    if (d && c) doiCho(x => datChoO(x, d, c, gt), [khoaO(d.k, c.ma)]);
    if (h == null) return;                                 // rời ô bằng chuột: tiêu điểm đã ở chỗ người ta bấm
    const v = h === "giu" ? o : keTiep(o, h) ?? o;
    datChon(v);
    tapTrung(v);
  };

  const boSua = () => {
    const x = sua;
    datSua(null);
    if (x) { datChon(x.o); tapTrung(x.o); }
  };

  const nhanCuon = (st: number) => {
    const r = capNhatKhoang(st);
    // Dòng đang sửa rời khung nhìn (sắp bị gỡ khỏi DOM) → lưu chữ đang gõ vào chờ trước.
    if (sua) {
      const i = khoa.indexOf(sua.o.k);
      if (i < r.dau || i >= r.cuoi) xongSua(sua.o, nhap.current, null);
    }
  };

  const trongBang = (e: { target: EventTarget; currentTarget: EventTarget }) =>
    e.target === e.currentTarget || (e.target as HTMLElement).matches("td");

  // Bàn phím khi KHÔNG sửa (ô sửa chặn lan phím của nó).
  const phim = (e: KeyboardEvent<HTMLDivElement>) => {
    if (sua || !chon || !trongBang(e)) return;
    const h: Huong | null = e.key === "ArrowDown" ? "xuong" : e.key === "ArrowUp" ? "len" : e.key === "ArrowLeft" ? "trai"
      : e.key === "ArrowRight" ? "phai" : e.key === "Tab" ? (e.shiftKey ? "tab_lui" : "tab") : null;
    if (h) {
      let v = keTiep(chon, h);
      if (!v && !theoK.has(chon.k) && khoa.length && cots.length) v = { k: khoa[0], ma: cots[0].ma };   // dòng chọn bị lọc mất
      if (!v && e.key === "Tab") return;                   // ra khỏi bảng bằng Tab như bình thường
      e.preventDefault();
      if (v) { datChon(v); tapTrung(v); }
      return;
    }
    const d = theoK.get(chon.k), c = cotMa.get(chon.ma);
    if (!d || !c) return;
    if (e.key === "Enter" || e.key === "F2") { e.preventDefault(); moSua(chon); return; }
    if (e.key === "Delete" || e.key === "Backspace") {
      if (duocSua(d, c)) { e.preventDefault(); doiCho(x => datChoO(x, d, c, ""), [khoaO(d.k, c.ma)]); }
      return;
    }
    // Gõ một ký tự in được = mở ô sửa bắt đầu bằng ký tự đó. Ô chọn: không (chữ không phải một lựa chọn); ô ngày: mở ô
    // ngày (ô <input type="date"> không nhận một ký tự lẻ).
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && c.kieu !== "chon")
      if (moSua(chon, c.kieu === "ngay" ? undefined : e.key)) e.preventDefault();
  };

  const danO = (e: ClipboardEvent<HTMLDivElement>) => {
    if (sua || !chon || !trongBang(e)) return;
    const n = neo(chon), v = n && viTriNeo(khoa, n);
    if (!v) return;
    e.preventDefault();
    if (!suaDuoc) { bao("Chỉ xem — không dán được."); return; }
    const r = dan(e.clipboardData.getData("text/plain"), v, cots, dongs);
    const nhan: { d: Dong; c: Cot; chu: string }[] = [];
    let boQua = r.bo_qua;
    for (const x of r.o) {
      const d = theoK.get(x.k), c = cotMa.get(x.cot);
      if (!d || !c || "loi" in kiemO(c, x.chu)) { boQua++; continue; }
      nhan.push({ d, c, chu: x.chu });
    }
    if (nhan.length) doiCho(cur => nhan.reduce((a, x) => datChoO(a, x.d, x.c, x.chu), cur), nhan.map(x => khoaO(x.d.k, x.c.ma)));
    bao(`Đã dán ${so(nhan.length)} ô · bỏ qua ${so(boQua)} ô`);
  };

  const chepO = (e: ClipboardEvent<HTMLDivElement>) => {
    if (sua || !chon || !trongBang(e)) return;
    const d = theoK.get(chon.k), c = cotMa.get(chon.ma);
    if (!d || !c) return;
    e.preventDefault();
    e.clipboardData.setData("text/plain", giaTri(d, c.ma, cho) ?? "");
  };

  const r = { dau: Math.min(khoang.dau, dongs.length), cuoi: Math.min(khoang.cuoi, dongs.length) };
  const hien = dongs.slice(r.dau, r.cuoi);
  const chonHien = !!chon && viTriCot.has(chon.ma) && hien.some(d => d.k === chon.k);
  const soCot = cots.length + 1;

  return (
    <div ref={khung} className="bdl-khung" tabIndex={-1} onKeyDown={phim} onPaste={danO} onCopy={chepO}
      onScroll={e => nhanCuon(e.currentTarget.scrollTop)}>
      <table className="bdl-bang" aria-label="Bảng dữ liệu — chọn ô bằng chuột hoặc mũi tên, Enter để sửa"
        aria-rowcount={dongs.length + 1}>
        <thead ref={dauBang}>
          <tr aria-rowindex={1}>
            <th scope="col" className="bdl-ma">Mã</th>
            {cots.map(c => (
              <th key={c.ma} scope="col" className={c.kieu === "so" ? "bdl-so" : undefined} title={`${c.nhom} · ${c.nhan}`}>
                {c.nhan}{!c.sua && <span aria-label="chỉ xem"> 🔒</span>}</th>))}
          </tr>
        </thead>
        <tbody>
          {r.dau > 0 && <tr className="bdl-dem" aria-hidden="true" style={{ height: r.dau * CAO_DONG }}><td colSpan={soCot} /></tr>}
          {hien.map((d, j) => (
            <tr key={d.k} data-k={d.k} aria-rowindex={r.dau + j + 2}>
              <th scope="row" className="bdl-ma">{d.k}</th>
              {cots.map((c, i) => {
                const ko = khoaO(d.k, c.ma), o: O = { k: d.k, ma: c.ma };
                const dangSua = cung(sua?.o, o);
                const coCho = Object.prototype.hasOwnProperty.call(cho, ko);
                const l = !coCho ? lech[ko] : undefined;
                const khong = !suaDuocO(d, c) && c.sua;                  // cột sửa được nhưng OBC không có ô này
                const loi = oLoi[ko] ?? (c.sua ? loiCho(c, ko, cho, lech) : null);
                const chu = hienThi(c, giaTri(d, c.ma, cho));
                const laChon = cung(chon, o);
                const cls = ["bdl-o", c.kieu === "so" ? "bdl-so" : "", !c.sua ? "bdl-khoa" : "", khong ? "bdl-khong" : "",
                  coCho ? "bdl-cho" : "", l ? "bdl-lech" : "", loi ? "bdl-loi" : "", laChon ? "bdl-chon" : "",
                  dangSua ? "bdl-dang-sua" : ""].filter(Boolean).join(" ");
                const title = [loi, l ? `OBC: ${hienThi(c, l.obc) || "(trống)"} · sửa bởi ${l.ai ?? "?"} lúc ${gio_tokyo(l.luc) || "?"}` : "",
                  khong ? "OBC không có ô này — không sửa được" : ""].filter(Boolean).join("\n");
                return (
                  <td key={c.ma} className={cls} data-c={i} data-ma={c.ma} title={title || undefined}
                    tabIndex={laChon && chonHien ? 0 : !chonHien && j === 0 && i === 0 ? 0 : -1}
                    aria-label={`${c.nhan}: ${chu || "trống"}${coCho ? " (chưa lưu)" : ""}${l ? " (đã sửa trên web)" : ""}${loi ? ` — lỗi: ${loi}` : ""}`}
                    onClick={() => { if (!dangSua) datChon(o); }}
                    onDoubleClick={() => { if (!dangSua) moSua(o); }}
                    onFocus={e => {
                      if (e.target !== e.currentTarget) return;
                      oVuaCo.current = e.currentTarget;
                      datChon(v => (cung(v, o) ? v : o));
                    }}>
                    {dangSua
                      ? <OSua key={sua!.phien} cot={c} dau={sua!.dau} nhap={nhap} xong={(gt, h) => xongSua(o, gt, h)} bo={boSua}
                          luu={luu} />
                      : <>
                        {chu}
                        {l && suaDuoc && (
                          <button type="button" className="bdl-ve" tabIndex={-1} title="Về giá trị OBC"
                            onMouseDown={e => e.preventDefault()}
                            aria-label={`Về giá trị OBC: ${hienThi(c, l.obc) || "trống"}`}
                            onClick={e => { e.stopPropagation(); doiCho(x => datChoO(x, d, c, l.obc ?? ""), [ko]); }}>↺</button>)}
                      </>}
                  </td>);
              })}
            </tr>))}
          {r.cuoi < dongs.length && (
            <tr className="bdl-dem" aria-hidden="true" style={{ height: (dongs.length - r.cuoi) * CAO_DONG }}><td colSpan={soCot} /></tr>)}
        </tbody>
      </table>
      {!dongs.length && <p className="bdl-rong">Không có dòng nào.</p>}
    </div>);
}
