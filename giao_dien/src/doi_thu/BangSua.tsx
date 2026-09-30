// Bảng sửa mặt hàng đối thủ (Dữ liệu › Duyệt / sửa — đặc tả 2026-09-30-doi-thu-bang-sua-design.md §4): mọi mặt hàng
// của bên đang chọn, sửa thẳng trong ô. Luật (cột, chữ trong ô, thân POST, di chuyển) ở bang_sua_logic.ts; thân POST đi
// qua CHÍNH sua_logic.ts::payload như pop-up SuaMatHang.
// Dữ liệu của bảng LÀ bộ đệm của truy vấn `khoaQ` (không có bản sao riêng): lưu xong thì vá thẳng vào đệm — gõ ô tìm,
// đổi chip rồi quay lại, hay tải lại đều thấy đúng số đã lưu, và lần lưu sau luôn mang sua_cuoi mới (không tự 409).
// Lưu TUẦN TỰ theo dòng; lần sau đọc dòng MỚI NHẤT từ đệm lúc chạy (dòng tay "đọc sai" thành dòng tay mới — khoá hiển
// thị `_k` giữ nguyên). Đổi ghép (mã KOME / thương hiệu) đụng mọi dòng cùng <bên>/<hàng> → tải lại cả bảng.
import { useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { memo, useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { gui, lay } from "../api";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import { cotHien, ghepDong, giaTriSua, hienThi, NHAN_O, oKeTiep, suaDuoc, thanO, timDong, type Cot, type Huong,
  type TruongO, type ViTri } from "./bang_sua_logic";
import { NHAN_DUYET, type GoiYApi, type QuanSat, type XungDot } from "./kieu";
import { lyDoBatThuong } from "./mau";
import { daSua, docXungDot, moTaXungDot } from "./sua_logic";

type Dong = QuanSat & { _k?: string };
type DuLieu = { dong: Dong[]; tong: number };
/** Trạng thái một ô: đang lưu · vừa lưu xong · lỗi (câu + chữ đã gõ — mở lại ô thì điền sẵn chữ đó). */
type TT = { kieu: "dang" | "xong" | "loi"; loi?: string; gt?: string };
type Cho = { ma: TruongO; gt: string; nhan?: "cung_hang" | "thay_the" };
/** 409 của một dòng + MỌI ô đã gõ của dòng đó từ lúc 409 (Ghi đè gửi hết, Lấy bản kia bỏ hết). */
type Xung = { x: XungDot; ds: Cho[] };
type Sua = { vt: ViTri; dau: string; phien: number };
/** Cách ô sửa đóng: ô kế tiếp (Enter / Tab) · ở lại ô này (chọn bằng chuột) · rời đi (blur). */
type Ket = Huong | "giu" | null;

const khoaDong = (q: Dong) => q._k ?? `${q.nguon}:${q.id}`;

/** Ô đang sửa: giữ chữ đang gõ trong state RIÊNG — gõ phím không vẽ lại cả bảng. */
function OSua({ cot, dau, goiY, xong, bo }: {
  cot: Cot; dau: string; goiY: string; xong: (gt: string, h: Ket) => void; bo: () => void;
}) {
  const [gt, datGt] = useState(dau);
  const daXong = useRef(false);
  const chuot = useRef(false);
  const ket = (h: Ket, v = gt) => { if (daXong.current) return; daXong.current = true; xong(v, h); };
  const phim = (e: KeyboardEvent) => {
    chuot.current = false;
    if (e.key === "Enter") { e.preventDefault(); ket("xuong"); }
    else if (e.key === "Tab") { e.preventDefault(); ket(e.shiftKey ? "tab_lui" : "tab"); }
    else if (e.key === "Escape") { e.preventDefault(); daXong.current = true; bo(); }
    e.stopPropagation();
  };
  if (cot.kieu === "chon")
    // Chọn bằng CHUỘT lưu ngay; bằng bàn phím thì chỉ đổi giá trị (Windows bắn `change` ở mỗi mũi tên trên ô đóng) —
    // lưu khi Enter / Tab / rời ô, Esc vẫn bỏ được.
    return (
      <select autoFocus aria-label={cot.nhan} value={gt} onKeyDown={phim} onBlur={() => ket(null)}
        onPointerDown={() => { chuot.current = true; }}
        onChange={e => { datGt(e.target.value); if (chuot.current) ket("giu", e.target.value); }}>
        {!cot.chon!.some(([m]) => m === gt) && <option value={gt}>{gt || "—"}</option>}
        {cot.chon!.map(([m, n]) => <option key={m} value={m}>{n}</option>)}
      </select>);
  return <input autoFocus aria-label={cot.nhan} value={gt} list={cot.kieu === "ma" ? goiY : undefined}
    inputMode={cot.kieu === "so" ? "decimal" : undefined} className={cot.kieu === "so" ? "bs-so" : undefined}
    onChange={e => datGt(e.target.value)} onKeyDown={phim} onBlur={() => ket(null)}
    onFocus={e => { const n = e.target.value.length; e.target.setSelectionRange(n, n); }} />;
}

type PropsDong = {
  q: Dong; k: string; d: number; cots: Cot[]; chonC: number; vaoDau: boolean; sua: Sua | null;
  tt: Record<string, TT> | undefined; xung: Xung | undefined; canNhan: { gt: string } | null; goiY: string; dangGui: boolean;
  bam: (d: number, c: number) => void; vao: (d: number, c: number) => void;
  xongSua: (d: number, c: number, gt: string, h: Ket) => void; boSua: () => void;
  chonNhan: (d: number, n: "cung_hang" | "thay_the" | null) => void;
  ghiDe: (k: string) => void; layBanKia: (k: string) => void; moPopup: (q: QuanSat) => void; xacNhan: (q: QuanSat) => void;
  taiLai: () => void;
};

/** Một dòng — memo: chọn / sửa một ô chỉ vẽ lại dòng đó (bảng tới 800 dòng × 14 ô). */
const DongBang = memo(function DongBang(p: PropsDong) {
  const { q, d, cots } = p;
  const thay = !!q.thay_boi;
  const loi = Object.entries(p.tt ?? {}).find(([, t]) => t.kieu === "loi");
  const nhanCot = (ma: string) => cots.find(c => c.ma === ma)?.nhan ?? ma;
  return <>
    <tr className={(q.bat_thuong ? "bt" : "") + (thay ? " thay" : "")}>
      {cots.map((c, i) => {
        const t = c.kieu ? p.tt?.[c.ma] : undefined;
        const o = t?.kieu === "loi" && t.gt != null ? { chu: t.gt, hoi: false } : hienThi(q, c);
        const dangSua = p.sua?.vt.c === i;
        const cls = [c.kieu ? "bs-sd" : "bs-cd", i === p.chonC ? "bs-chon" : "", o.hoi ? "bs-hoi" : "", t ? "bs-tt-" + t.kieu : "",
          c.kieu === "so" || c.ma === "yen_kg" ? "bs-so" : ""].filter(Boolean).join(" ");
        return (
          <td key={c.ma} className={cls} data-d={d} data-c={i} tabIndex={i === p.chonC || (p.vaoDau && i === 0) ? 0 : -1}
            onClick={() => p.bam(d, i)} onFocus={e => { if (e.target === e.currentTarget) p.vao(d, i); }}
            aria-label={`${c.nhan}: ${o.chu || (o.hoi ? "còn thiếu" : "trống")}`}>
            {dangSua ? <OSua key={p.sua!.phien} cot={c} dau={p.sua!.dau} goiY={p.goiY}
                xong={(gt, h) => p.xongSua(d, i, gt, h)} bo={p.boSua} />
              : <>
                {c.ma === "ten_goc" && q.bat_thuong && <span className="dt-bs-bt" title={lyDoBatThuong(q)} aria-label="bất thường">⚠ </span>}
                {o.hoi && !o.chu ? <span className="dt-hoi-o" aria-hidden="true">?</span> : o.chu}
                {c.ma === "ten_goc" && daSua(q) && <span className="dt-nhat" aria-hidden="true"> ✎</span>}
                {t?.kieu === "dang" && <span className="dt-bs-quay" aria-label="đang lưu" />}
                {t?.kieu === "xong" && <span className="dt-bs-ok" aria-label="đã lưu">✓</span>}
              </>}
            {c.ma === "ma_kome" && p.canNhan && (
              <span className="dt-bs-nhan" role="group" aria-label={`Ghép ${p.canNhan.gt}: chọn thương hiệu`}>
                <button type="button" className="chip" autoFocus onClick={e => { e.stopPropagation(); p.chonNhan(d, "cung_hang"); }}>
                  {NHAN_O[0][1]}</button>
                <button type="button" className="chip" onClick={e => { e.stopPropagation(); p.chonNhan(d, "thay_the"); }}>
                  {NHAN_O[1][1]}</button>
                <button type="button" className="chip" onClick={e => { e.stopPropagation(); p.chonNhan(d, null); }}>Bỏ</button>
              </span>)}
          </td>);
      })}
      <td className="bs-cd dt-bs-duyet">
        {q.nguon === "nap" && q.trang_thai_duyet !== "da_xac_nhan" && !thay
          ? <button type="button" className="chip dt-dung" disabled={p.dangGui} aria-label={`Đúng rồi: ${q.ten_goc}`}
              onClick={() => p.xacNhan(q)}>Đúng rồi</button>
          : <span className="dt-nhat">{NHAN_DUYET[q.trang_thai_duyet]}</span>}
      </td>
      <td className="bs-cd">
        <button type="button" className="chip" aria-label={`Mở pop-up sửa ${q.ten_goc}`} title="Bậc giá, khuyến mãi, giá đã đổi, lịch sử"
          disabled={thay} onClick={() => p.moPopup(q)}>⋯</button>
      </td>
    </tr>
    {(loi || p.xung || thay) && (
      <tr className="dt-bs-phu"><td colSpan={cots.length + 2}>
        {thay ? <span>Dòng này đã có bản mới hơn — không sửa bản cũ. <button type="button" className="chip" onClick={p.taiLai}>
            Tải bản mới</button></span>
          : p.xung ? <span role="alert">{moTaXungDot(p.xung.x)} — bạn vừa gõ: {p.xung.ds.map(c => `${nhanCot(c.ma)} = ${c.gt || "(trống)"}`).join(", ")}.{" "}
              <button type="button" className="nut-chinh" onClick={() => p.ghiDe(p.k)}>Ghi đè</button>{" "}
              <button type="button" className="chip" onClick={() => p.layBanKia(p.k)}>Lấy bản {p.xung.x.ai ? `của ${p.xung.x.ai}` : "kia"}</button></span>
          : <span role="alert" className="dt-loi">{nhanCot(loi![0])}: {loi![1].loi}</span>}
      </td></tr>)}
  </>;
});

export function BangSua({ khoaQ, dong, tim, moiBen, moPopup, xacNhan, dangGui, taiLai }: {
  khoaQ: QueryKey; dong: QuanSat[]; tim: string; moiBen: boolean; moPopup: (q: QuanSat) => void;
  xacNhan: (q: QuanSat) => void; dangGui: boolean; taiLai: () => void;
}) {
  const qc = useQueryClient();
  const kx = chuoiKhoang(useKhoang());
  const cots = cotHien(moiBen);
  const hien = useMemo(() => timDong(dong as Dong[], tim) as Dong[], [dong, tim]);
  const hienRef = useRef(hien); hienRef.current = hien;

  const [chon, datChon] = useState<ViTri | null>(null);
  const [sua, datSua] = useState<Sua | null>(null);
  const [tt, datTT] = useState<Record<string, Record<string, TT>>>({});
  const [xung, datXung] = useState<Record<string, Xung>>({});
  const [canNhan, datCanNhan] = useState<{ k: string; gt: string } | null>(null);
  const phien = useRef(0);
  const hang = useRef(new Map<string, Promise<void>>());
  const bang = useRef<HTMLTableElement>(null);
  // Bản mới nhất của state cho các hàm xử lý ỔN ĐỊNH (memo của DongBang chỉ có tác dụng khi hàm không đổi mỗi lần vẽ).
  const suaRef = useRef(sua); suaRef.current = sua;
  const xungRef = useRef(xung); xungRef.current = xung;
  const canNhanRef = useRef(canNhan); canNhanRef.current = canNhan;
  const ttRef = useRef(tt); ttRef.current = tt;

  const gy = useQuery({ queryKey: ["doi-thu", "goi-y-nhac"], staleTime: 5 * 60_000,
    queryFn: () => lay<GoiYApi>("/api/doi-thu/goi-y-nhac") });
  const maGoiY = (gy.data?.hang ?? []).filter(h => h.loai === "ma" && h.ma);

  // ---- bộ đệm là nguồn dữ liệu duy nhất
  const docDong = (k: string) => qc.getQueryData<DuLieu>(khoaQ)?.dong.find(r => khoaDong(r) === k);
  const vaDong = (k: string, f: (q: Dong) => Dong) => qc.setQueryData<DuLieu>(khoaQ, d => d && ({
    ...d, dong: d.dong.map(r => (khoaDong(r) === k ? { ...f(r), _k: k } : r)) }));

  const datO = (k: string, ma: string, t: TT | null) => datTT(s => {
    const r = { ...(s[k] ?? {}) };
    if (t) r[ma] = t; else delete r[ma];
    return { ...s, [k]: r };
  });
  // Trả tiêu điểm về ô SAU lần vẽ kế tiếp — useEffect chứ không requestAnimationFrame: rAF không chạy khi thẻ trình duyệt
  // bị ẩn, tiêu điểm rơi về <body> và phím mũi tên cuộn cả trang.
  const choTapTrung = useRef<ViTri | null>(null);
  const tapTrung = (v: ViTri | null) => { choTapTrung.current = v; };
  useEffect(() => {
    const v = choTapTrung.current;
    if (!v) return;
    choTapTrung.current = null;
    bang.current?.querySelector<HTMLElement>(`td[data-d="${v.d}"][data-c="${v.c}"]`)?.focus();
  });

  const docLai = async (k: string, nguon: string, id: number) => {
    const m = await lay<{ quan_sat: QuanSat }>(`/api/doi-thu/mat-hang/${nguon}/${id}${kx ? "?" + kx : ""}`);
    qc.setQueryData<DuLieu>(khoaQ, d => d && ({ ...d, dong: ghepDong(d.dong, { nguon, id }, { ...m.quan_sat, _k: k } as Dong) as Dong[] }));
  };

  /** Lưu MỘT ô, xếp hàng sau lần lưu trước của cùng dòng. Dòng đang 409 → không gửi, gom vào danh sách chờ của 409. */
  const luu = useCallback((k: string, ma: TruongO, gt: string, o: { ghi_de?: boolean; nhan?: "cung_hang" | "thay_the" } = {}) => {
    const truoc = hang.current.get(k) ?? Promise.resolve();
    const lan = truoc.then(async () => {
      const q = docDong(k);
      if (!q) return;
      if (!o.ghi_de && xungRef.current[k]) {
        datXung(s => (s[k] ? { ...s, [k]: { ...s[k], ds: [...s[k].ds.filter(c => c.ma !== ma), { ma, gt, nhan: o.nhan }] } } : s));
        return;
      }
      const t = thanO(q, ma, gt, o);
      if (t == null) { datO(k, ma, null); return; }
      if ("can_nhan" in t) { datCanNhan({ k, gt }); return; }
      if ("loi" in t) { datO(k, ma, { kieu: "loi", loi: t.loi, gt }); return; }
      datO(k, ma, { kieu: "dang" });
      const doiGhep = "ma_kome" in t.body || "nhan" in t.body;
      try {
        const r = await gui<{ nguon: "nap" | "tay"; id: number; sua_cuoi: number }>("/api/doi-thu/sua-mat-hang", t.body);
        vaDong(k, x => ({ ...x, nguon: r.nguon, id: r.id, sua_cuoi: r.sua_cuoi }));
        try { await docLai(k, r.nguon, r.id); } catch { /* đã lưu; đọc lại hỏng thì giữ số cũ tới lần tải sau */ }
        datO(k, ma, { kieu: "xong" });
        setTimeout(() => datTT(s => {
          if (s[k]?.[ma]?.kieu !== "xong") return s;
          const r2 = { ...s[k] }; delete r2[ma]; return { ...s, [k]: r2 };
        }), 1500);
        // Bảng này đã vá tại chỗ; bảng duyet khác (bên / lọc khác) đánh dấu cũ, tải khi mở; màn khác tải lại.
        qc.invalidateQueries({ queryKey: ["doi-thu", "duyet"], refetchType: "none" });
        qc.invalidateQueries({ queryKey: ["doi-thu"], predicate: x => x.queryKey[1] !== "duyet" });
        // Ghép đổi cho MỌI dòng cùng <bên>/<hàng> (và sua_cuoi của chúng): tải lại cả bảng.
        if (doiGhep) qc.invalidateQueries({ queryKey: khoaQ, exact: true });
      } catch (e) {
        const x = docXungDot(e);
        if (x?.thay_boi) { vaDong(k, y => ({ ...y, thay_boi: x.thay_boi })); datO(k, ma, null); }
        else if (x) {
          datXung(s => ({ ...s, [k]: { x, ds: [...(s[k]?.ds ?? []).filter(c => c.ma !== ma), { ma, gt, nhan: o.nhan }] } }));
          datO(k, ma, null);
        }
        else datO(k, ma, { kieu: "loi", loi: e instanceof Error ? e.message : String(e), gt });
      }
    });
    hang.current.set(k, lan.catch(() => undefined));
  }, [kx, qc, khoaQ]);   // eslint-disable-line react-hooks/exhaustive-deps

  const moSua = (v: ViTri, dau?: string) => {
    const q = hienRef.current[v.d], c = cots[v.c];
    if (!q || !suaDuoc(q, c)) return false;
    const loiCu = ttRef.current[khoaDong(q)]?.[c.ma];
    phien.current++;
    datChon(v);
    datSua({ vt: v, dau: dau ?? (loiCu?.kieu === "loi" && loiCu.gt != null ? loiCu.gt : giaTriSua(q, c.ma as TruongO)),
      phien: phien.current });
    return true;
  };

  const bam = useCallback((d: number, c: number) => {
    const v = { d, c }, s = suaRef.current;
    if (s && s.vt.d === d && s.vt.c === c) return;
    datChon(v);
    if (!moSua(v)) tapTrung(v);
  }, [moiBen]);   // eslint-disable-line react-hooks/exhaustive-deps
  const vao = useCallback((d: number, c: number) => {
    datChon(v => (v && v.d === d && v.c === c ? v : { d, c }));
  }, []);

  const xongSua = useCallback((d: number, c: number, gt: string, h: Ket) => {
    const q = hienRef.current[d];
    datSua(null);
    if (q) luu(khoaDong(q), cots[c].ma as TruongO, gt);
    if (h == null) return;                                  // rời ô bằng chuột: tiêu điểm đã ở chỗ người ta bấm
    if (h === "giu") { datChon({ d, c }); tapTrung({ d, c }); return; }
    // Enter / Tab: ô kế tiếp SỬA ĐƯỢC mở luôn để gõ tiếp (điền "tịnh 1 gói" cho cả loạt hàng).
    let v = oKeTiep({ d, c }, h, hienRef.current.length, cots);
    while (v && !suaDuoc(hienRef.current[v.d], cots[v.c])) v = oKeTiep(v, h, hienRef.current.length, cots);
    if (v) moSua(v); else { datChon({ d, c }); tapTrung({ d, c }); }
  }, [luu, moiBen]);   // eslint-disable-line react-hooks/exhaustive-deps

  const boSua = useCallback(() => {
    const s = suaRef.current;
    if (s) { datChon(s.vt); tapTrung(s.vt); }
    datSua(null);
  }, []);

  const chonNhan = useCallback((d: number, n: "cung_hang" | "thay_the" | null) => {
    const q = hienRef.current[d], cn = canNhanRef.current;
    datCanNhan(null);
    if (q && cn && n) luu(khoaDong(q), "ma_kome", cn.gt, { nhan: n });
    tapTrung({ d, c: cots.findIndex(c => c.ma === "ma_kome") });
    datChon({ d, c: cots.findIndex(c => c.ma === "ma_kome") });
  }, [luu, moiBen]);   // eslint-disable-line react-hooks/exhaustive-deps

  const ghiDe = useCallback((k: string) => {
    const x = xungRef.current[k];
    if (!x) return;
    datXung(s => { const n = { ...s }; delete n[k]; return n; });
    xungRef.current = { ...xungRef.current }; delete xungRef.current[k];
    for (const c of x.ds) luu(k, c.ma, c.gt, { ghi_de: true, nhan: c.nhan });
  }, [luu]);

  const layBanKia = useCallback((k: string) => {
    const q = docDong(k);
    datXung(s => { const n = { ...s }; delete n[k]; return n; });
    if (!q) return;
    docLai(k, q.nguon, q.id).catch(() => taiLai());
  }, [kx, taiLai]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Bàn phím khi KHÔNG sửa: mũi tên di chuyển, Enter / F2 mở ô, gõ ký tự mở ô bắt đầu bằng ký tự đó.
  const phim = (e: KeyboardEvent<HTMLTableElement>) => {
    if (sua || !chon || !(e.target as HTMLElement).matches("td")) return;
    const h: Huong | null = e.key === "ArrowDown" ? "xuong" : e.key === "ArrowUp" ? "len" : e.key === "ArrowLeft" ? "trai"
      : e.key === "ArrowRight" ? "phai" : e.key === "Tab" ? (e.shiftKey ? "tab_lui" : "tab") : null;
    if (h) {
      const v = oKeTiep(chon, h, hien.length, cots);
      if (!v && e.key === "Tab") return;          // ra khỏi bảng bằng Tab như bình thường
      e.preventDefault();
      if (v) { datChon(v); tapTrung(v); }
      return;
    }
    if (e.key === "Enter" || e.key === "F2") { e.preventDefault(); moSua(chon); return; }
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && cots[chon.c]?.kieu !== "chon") {
      if (moSua(chon, e.key)) e.preventDefault();
    }
  };

  const goiY = "dt-bs-goi-y";
  if (!hien.length) return <p className="dt-nhat">Không có dòng nào{tim.trim() ? " khớp ô tìm" : ""}.</p>;
  return (
    <div className="dt-bs-khung">
      <datalist id={goiY}>{maGoiY.map(h => <option key={h.ma} value={h.ma}>{h.ten}</option>)}</datalist>
      <table ref={bang} className="dt-bs" onKeyDown={phim} aria-label="Mặt hàng đối thủ — bấm ô để sửa">
        <thead><tr>{cots.map(c => <th key={c.ma} scope="col" className={c.kieu === "so" || c.ma === "yen_kg" ? "bs-so" : undefined}>
          {c.nhan}</th>)}<th scope="col">Duyệt</th><th scope="col"><span className="dt-an">Sửa thêm</span></th></tr></thead>
        <tbody>
          {hien.map((q, d) => { const k = khoaDong(q); return (
            <DongBang key={k} k={k} q={q} d={d} cots={cots} chonC={chon?.d === d ? chon.c : -1} vaoDau={!chon && d === 0}
              sua={sua?.vt.d === d ? sua : null} tt={tt[k]} xung={xung[k]} canNhan={canNhan?.k === k ? canNhan : null}
              goiY={goiY} dangGui={dangGui} bam={bam} vao={vao} xongSua={xongSua} boSua={boSua} chonNhan={chonNhan}
              ghiDe={ghiDe} layBanKia={layBanKia} moPopup={moPopup} xacNhan={xacNhan} taiLai={taiLai} />); })}
        </tbody>
      </table>
    </div>);
}
