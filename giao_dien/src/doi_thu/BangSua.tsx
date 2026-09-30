// Bảng sửa mặt hàng đối thủ (Dữ liệu › Duyệt / sửa — đặc tả 2026-09-30-doi-thu-bang-sua-design.md §4): mọi mặt hàng
// của bên đang chọn, sửa thẳng trong ô. Luật (cột, chữ trong ô, thân POST, di chuyển) ở bang_sua_logic.ts; thân POST đi
// qua CHÍNH sua_logic.ts::payload như pop-up SuaMatHang.
// Dữ liệu của bảng LÀ bộ đệm của truy vấn `khoaQ` (không có bản sao riêng): lưu xong thì vá thẳng vào đệm — gõ ô tìm,
// đổi chip rồi quay lại, hay tải lại đều thấy đúng số đã lưu, và lần lưu sau luôn mang sua_cuoi mới (không tự 409).
// Lưu TUẦN TỰ theo dòng; lần sau đọc dòng MỚI NHẤT từ đệm lúc chạy (dòng tay "đọc sai" thành dòng tay mới — khoá hiển
// thị `_k` giữ nguyên). Đổi ghép (mã KOME / thương hiệu) đụng mọi dòng cùng <bên>/<hàng> → tải lại cả bảng.
// 070 (đặc tả 2026-09-30-doi-thu-gop-mat-hang-design.md §5): dòng NHÓM theo mặt hàng (bên + mat_hang_khoa) — dòng đầu là
// dòng đại diện, chip "+n mức" mở các mức giá khác ngay dưới. Ô chọn / ô đang sửa NEO theo KHOÁ dòng + cột (`Neo`):
// ẩn một dòng, mở / đóng nhóm, tải lại đều làm chỉ số dòng trượt — neo theo chỉ số thì Enter lưu nhầm vào dòng khác. Chỉ số
// d (di chuyển bằng bàn phím) suy ra lúc cần từ danh sách khoá ĐANG HIỆN (`khoaRef`: đầu nhóm + con đang mở).
// 🗑 (ẩn) / Khôi phục đi CÙNG hàng đợi theo dòng với lưu ô (`guiHang`); "Gộp vào…" (⇲) mở HopThoai. Lọc "Đã xoá": CHỈ ĐỌC.
import { useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { memo, useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { gui, lay } from "../api";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import { cotHien, daGop, dichGop, dongHien, ghepDong, giaTriSua, hienThi, khoaDong, NHAN_O, nhanMuc, neoKeTiep, nhomBang,
  suaDuoc, thanO, timDong, type Cot, type DongHien, type Huong, type Neo, type TruongO } from "./bang_sua_logic";
import { HopThoai } from "./HopThoai";
import { NHAN_DUYET, type GoiYApi, type QuanSat, type XungDot } from "./kieu";
import { lyDoBatThuong } from "./mau";
import { KhungXungDot } from "./SuaNho";
import { daSua, docXungDot, moTaXungDot } from "./sua_logic";

type Dong = QuanSat & { _k?: string };
type DuLieu = { dong: Dong[]; tong: number };
/** Trạng thái một ô: đang lưu · vừa lưu xong · lỗi (câu + chữ đã gõ — mở lại ô thì điền sẵn chữ đó). Khoá "an" = nút 🗑 /
 *  Khôi phục của dòng. */
type TT = { kieu: "dang" | "xong" | "loi"; loi?: string; gt?: string };
/** Một thao tác chờ của dòng đang 409: một ô đã gõ, hoặc ẩn / khôi phục dòng. */
type Cho = { loai?: undefined; ma: TruongO; gt: string; nhan?: "cung_hang" | "thay_the" } | { loai: "an"; an: boolean };
/** 409 của một dòng + MỌI thao tác của dòng đó từ lúc 409 (Ghi đè gửi hết, Lấy bản kia bỏ hết). */
type Xung = { x: XungDot; ds: Cho[] };
/** Ô đang sửa — NEO theo khoá dòng (không theo chỉ số dòng: ẩn / mở nhóm / tải lại làm chỉ số trượt). */
type Sua = { n: Neo; dau: string; phien: number };
/** Cách ô sửa đóng: ô kế tiếp (Enter / Tab) · ở lại ô này (chọn bằng chuột) · rời đi (blur). */
type Ket = Huong | "giu" | null;

const MA_AN = "an";
const coLoi = (t: Record<string, TT> | undefined) => Object.values(t ?? {}).some(x => x.kieu === "loi");

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

/** 🗑 xác nhận nhẹ bằng chính nút: lần 1 đổi thành "Xoá?" (tự trở lại sau 3 s), lần 2 mới gửi. Ở lọc "Đã xoá": Khôi phục. */
function NutXoa({ ten, khoiPhuc, dang, tat, bam }: { ten: string; khoiPhuc: boolean; dang: boolean; tat: boolean; bam: () => void }) {
  const [hoi, datHoi] = useState(false);
  useEffect(() => {
    if (!hoi) return;
    const t = setTimeout(() => datHoi(false), 3000);
    return () => clearTimeout(t);
  }, [hoi]);
  if (khoiPhuc)
    return <button type="button" className="chip" disabled={dang || tat} aria-label={`Khôi phục ${ten}`} onClick={bam}>
      {dang ? "Đang khôi phục…" : "Khôi phục"}</button>;
  return (
    <button type="button" className={"chip bs-xoa" + (hoi ? " bs-xoa-hoi" : "")} disabled={dang || tat}
      aria-label={hoi ? `Bấm lần nữa để xoá ${ten}` : `Xoá ${ten}`} title={hoi ? "Bấm lần nữa để xoá" : "Xoá (ẩn) dòng giá này"}
      onClick={() => { if (hoi) { datHoi(false); bam(); } else datHoi(true); }}>
      {dang ? "…" : hoi ? "Xoá?" : "🗑"}</button>);
}

type PropsDong = {
  q: Dong; k: string; cots: Cot[]; chonC: number; vaoDau: boolean; sua: Sua | null;
  tt: Record<string, TT> | undefined; xung: Xung | undefined; canNhan: { gt: string } | null; goiY: string; dangGui: boolean;
  /** Nhóm: `soCon` null = dòng con; số = dòng đầu có bấy nhiêu mức giá khác. */
  kn: string; soCon: number | null; mo: boolean; ep: boolean; daXoa: boolean;
  bam: (k: string, c: number) => void; vao: (k: string, c: number) => void;
  xongSua: (k: string, c: number, gt: string, h: Ket) => void; boSua: () => void;
  chonNhan: (k: string, n: "cung_hang" | "thay_the" | null) => void;
  ghiDe: (k: string) => void; layBanKia: (k: string) => void; moPopup: (q: QuanSat) => void; xacNhan: (q: QuanSat) => void;
  taiLai: () => void; moNhom: (kn: string) => void; datAn: (k: string, an: boolean) => void; moGop: (k: string) => void;
};

const nhanCho = (c: Cho, nhanCot: (ma: string) => string) =>
  c.loai === "an" ? (c.an ? "xoá dòng" : "khôi phục dòng") : `${nhanCot(c.ma)} = ${c.gt || "(trống)"}`;

/** Một dòng — memo: chọn / sửa một ô chỉ vẽ lại dòng đó (bảng tới 800 dòng × 14 ô). */
const DongBang = memo(function DongBang(p: PropsDong) {
  const { q, k, cots } = p;
  const thay = !!q.thay_boi;
  const loi = Object.entries(p.tt ?? {}).find(([, t]) => t.kieu === "loi");
  const nhanCot = (ma: string) => (ma === MA_AN ? (p.daXoa ? "Khôi phục" : "Xoá") : cots.find(c => c.ma === ma)?.nhan ?? ma);
  const cls = [q.bat_thuong ? "bt" : "", thay ? "thay" : "", p.soCon == null ? "bs-con" : ""].filter(Boolean).join(" ");
  return <>
    <tr className={cls || undefined} data-k={k}>
      {cots.map((c, i) => {
        const t = c.kieu ? p.tt?.[c.ma] : undefined;
        const o = t?.kieu === "loi" && t.gt != null ? { chu: t.gt, hoi: false } : hienThi(q, c);
        const dangSua = p.sua?.n.c === i;
        const cls = [c.kieu && !p.daXoa ? "bs-sd" : "bs-cd", i === p.chonC ? "bs-chon" : "", o.hoi ? "bs-hoi" : "", t ? "bs-tt-" + t.kieu : "",
          c.kieu === "so" || c.ma === "yen_kg" ? "bs-so" : ""].filter(Boolean).join(" ");
        return (
          <td key={c.ma} className={cls} data-c={i} tabIndex={i === p.chonC || (p.vaoDau && i === 0) ? 0 : -1}
            onClick={() => p.bam(k, i)} onFocus={e => { if (e.target === e.currentTarget) p.vao(k, i); }}
            aria-label={`${c.nhan}: ${o.chu || (o.hoi ? "còn thiếu" : "trống")}`}>
            {dangSua ? <OSua key={p.sua!.phien} cot={c} dau={p.sua!.dau} goiY={p.goiY}
                xong={(gt, h) => p.xongSua(k, i, gt, h)} bo={p.boSua} />
              : <>
                {c.ma === "ten_goc" && !!p.soCon && (
                  <button type="button" className="chip bs-muc" aria-expanded={p.mo} aria-disabled={p.ep || undefined}
                    aria-label={`${p.mo ? "Đóng" : "Mở"} ${p.soCon} mức giá khác của ${q.ten_goc}`}
                    title={p.ep ? "Có dòng con đang lỗi / xung đột — nhóm mở tới khi xử lý xong" : `${p.soCon} mức giá khác của mặt hàng này`}
                    onClick={e => { e.stopPropagation(); if (!p.ep) p.moNhom(p.kn); }}>{p.mo ? "−" : "+"}{p.soCon} mức</button>)}
                {c.ma === "ten_goc" && q.bat_thuong && <span className="dt-bs-bt" title={lyDoBatThuong(q)} aria-label="bất thường">⚠ </span>}
                {o.hoi && !o.chu ? <span className="dt-hoi-o" aria-hidden="true">?</span> : o.chu}
                {c.ma === "ten_goc" && daSua(q) && <span className="dt-nhat" aria-hidden="true"> ✎</span>}
                {t?.kieu === "dang" && <span className="dt-bs-quay" aria-label="đang lưu" />}
                {t?.kieu === "xong" && <span className="dt-bs-ok" aria-label="đã lưu">✓</span>}
              </>}
            {c.ma === "ma_kome" && p.canNhan && (
              <span className="dt-bs-nhan" role="group" aria-label={`Ghép ${p.canNhan.gt}: chọn thương hiệu`}>
                <button type="button" className="chip" autoFocus onClick={e => { e.stopPropagation(); p.chonNhan(k, "cung_hang"); }}>
                  {NHAN_O[0][1]}</button>
                <button type="button" className="chip" onClick={e => { e.stopPropagation(); p.chonNhan(k, "thay_the"); }}>
                  {NHAN_O[1][1]}</button>
                <button type="button" className="chip" onClick={e => { e.stopPropagation(); p.chonNhan(k, null); }}>Bỏ</button>
              </span>)}
          </td>);
      })}
      <td className="bs-cd dt-bs-duyet">
        {q.nguon === "nap" && q.trang_thai_duyet !== "da_xac_nhan" && !thay && !p.daXoa
          ? <button type="button" className="chip dt-dung" disabled={p.dangGui} aria-label={`Đúng rồi: ${q.ten_goc}`}
              onClick={() => p.xacNhan(q)}>Đúng rồi</button>
          : <span className="dt-nhat">{NHAN_DUYET[q.trang_thai_duyet]}</span>}
      </td>
      <td className="bs-cd bs-nut">
        {/* Ở "Đã xoá" dòng CHỈ ĐỌC: sửa một dòng ẩn (nhất là "giá đã đổi" → dòng tay mới an = false) là lặng lẽ hiện lại nó. */}
        {!p.daXoa && <button type="button" className="chip" aria-label={`Mở pop-up sửa ${q.ten_goc}`} title="Bậc giá, khuyến mãi, giá đã đổi, lịch sử"
          disabled={thay} onClick={() => p.moPopup(q)}>⋯</button>}
        {!p.daXoa && <button type="button" className="chip" aria-label={`Gộp ${q.ten_goc} vào mặt hàng khác / tách ra`}
          title="Gộp vào mặt hàng khác / tách ra" disabled={thay} onClick={() => p.moGop(k)}>⇲</button>}
      </td>
      <td className="bs-cd">
        <NutXoa ten={q.ten_goc} khoiPhuc={p.daXoa} dang={p.tt?.[MA_AN]?.kieu === "dang"} tat={thay}
          bam={() => p.datAn(k, !p.daXoa)} />
      </td>
    </tr>
    {(loi || p.xung || thay) && (
      <tr className="dt-bs-phu"><td colSpan={cots.length + 3}>
        {thay ? <span>Dòng này đã có bản mới hơn — không sửa bản cũ. <button type="button" className="chip" onClick={p.taiLai}>
            Tải bản mới</button></span>
          : p.xung ? <span role="alert">{moTaXungDot(p.xung.x)} — bạn vừa {p.xung.ds.some(c => c.loai !== "an") ? "gõ" : "bấm"}: {p.xung.ds.map(c => nhanCho(c, nhanCot)).join(", ")}.{" "}
              <button type="button" className="nut-chinh" onClick={() => p.ghiDe(k)}>Ghi đè</button>{" "}
              <button type="button" className="chip" onClick={() => p.layBanKia(k)}>Lấy bản {p.xung.x.ai ? `của ${p.xung.x.ai}` : "kia"}</button></span>
          : <span role="alert" className="dt-loi">{nhanCot(loi![0])}: {loi![1].loi}</span>}
      </td></tr>)}
  </>;
});

/** "Gộp vào…": chọn mặt hàng đích cùng bên (từ bộ đệm bảng), hoặc "Tách ra" khi dòng đang được gộp. 409 → KhungXungDot. */
function HopGop({ q, ds, chay, dong, giu }: {
  q: Dong; ds: Dong[]; chay: (vao: string | null, ghi_de: boolean) => Promise<unknown>; dong: () => void; giu: () => void;
}) {
  const [tim, datTim] = useState("");
  const [dang, datDang] = useState(false);
  const [loi, datLoi] = useState<string | null>(null);
  const [xung, datXung] = useState<{ x: XungDot; vao: string | null } | null>(null);
  const dich = useMemo(() => dichGop(ds, q, tim), [ds, q, tim]);
  const TOI_DA = 100;
  const lam = (vao: string | null, ghi_de = false) => {
    if (dang) return;
    datDang(true); datLoi(null); datXung(null);
    chay(vao, ghi_de).then(dong).catch((e: unknown) => {
      const x = docXungDot(e);
      if (x) datXung({ x, vao }); else datLoi(e instanceof Error ? e.message : String(e));
    }).finally(() => datDang(false));
  };
  const gop = daGop(q);
  return (
    <HopThoai tieu_de={`Gộp “${q.ten_goc}” vào mặt hàng khác`} dong={dong} rong={560}>
      <p className="dt-nhat">Gộp cả mặt hàng (mọi mức giá cùng mã hàng của {q.ten_doi_thu ?? q.ma_doi_thu}) vào một mặt hàng
        khác của CÙNG bên — sau đó chúng là các mức giá của một mặt hàng.</p>
      {gop && (
        <p className="dt-gop-tach">Dòng này đang được gộp vào mặt hàng khác.{" "}
          <button type="button" className="chip" disabled={dang} onClick={() => lam(null)}>Tách ra</button></p>)}
      {xung && <KhungXungDot x={xung.x} dang={dang} ghiDe={() => lam(xung.vao, true)} giu={giu} />}
      {loi && <p role="alert" className="dt-loi">{loi}</p>}
      <input type="search" className="dt-gop-tim" data-focus placeholder="🔍 Tìm tên mặt hàng đích…" aria-label="Tìm mặt hàng đích"
        value={tim} onChange={e => datTim(e.target.value)} />
      {dich.length ? (
        <ul className="dt-gop-ds" aria-label="Mặt hàng đích">
          {dich.slice(0, TOI_DA).map(x => (
            <li key={khoaDong(x)}>
              <button type="button" disabled={dang} onClick={() => lam(x.mat_hang_khoa)}>
                <b>{x.ten_goc}</b>{x.quy_cach_goc ? ` · ${x.quy_cach_goc}` : ""}
                <small> · {nhanMuc(x)}{(x.so_muc ?? 1) > 1 ? ` · ${x.so_muc} mức` : ""}</small>
              </button>
            </li>))}
        </ul>)
        : <p className="dt-nhat">{tim.trim() ? "Không có mặt hàng nào khác của bên này khớp ô tìm (chỉ tìm trong các dòng đang lọc)."
          : "Không có mặt hàng khác của bên này trong các dòng đang lọc — chọn lọc “Tất cả” để thấy hết."}</p>}
      {dich.length > TOI_DA && <p className="dt-nhat">Đang hiện {TOI_DA} / {dich.length} — gõ thêm để lọc.</p>}
      {dang && <p className="dt-nhat" role="status">Đang gộp…</p>}
    </HopThoai>);
}

export function BangSua({ khoaQ, dong, tim, moiBen, daXoa = false, moPopup, xacNhan, dangGui, taiLai }: {
  khoaQ: QueryKey; dong: QuanSat[]; tim: string; moiBen: boolean; daXoa?: boolean; moPopup: (q: QuanSat) => void;
  xacNhan: (q: QuanSat) => void; dangGui: boolean; taiLai: () => void;
}) {
  const qc = useQueryClient();
  const kx = chuoiKhoang(useKhoang());
  const cots = useMemo(() => cotHien(moiBen), [moiBen]);   // mảng ỔN ĐỊNH — không thì memo của DongBang vô tác dụng
  const hien = useMemo(() => timDong(dong as Dong[], tim) as Dong[], [dong, tim]);

  // Ô chọn / ô sửa NEO theo khoá dòng (bang_sua_logic.ts::Neo); chỉ số d chỉ suy ra lúc cần từ `khoaRef`.
  const [chon, datChon] = useState<Neo | null>(null);
  const [sua, datSua] = useState<Sua | null>(null);
  const [tt, datTT] = useState<Record<string, Record<string, TT>>>({});
  const [xung, datXung] = useState<Record<string, Xung>>({});
  const [canNhan, datCanNhan] = useState<{ k: string; gt: string } | null>(null);
  const [mo, datMo] = useState<ReadonlySet<string>>(() => new Set());
  const [gop, datGop] = useState<string | null>(null);   // khoá dòng đang mở hộp "Gộp vào…"
  const phien = useRef(0);
  const hang = useRef(new Map<string, Promise<void>>());
  const bang = useRef<HTMLTableElement>(null);

  // Dòng ĐANG HIỆN: mỗi mặt hàng một dòng đầu + dòng con của nhóm đang mở (hoặc đang có lỗi / 409 / chọn thương hiệu).
  const nhom = useMemo(() => nhomBang(hien), [hien]);
  const nhomRef = useRef(nhom); nhomRef.current = nhom;
  const dsHien = useMemo(() => dongHien(nhom, mo, q => {
    const k = khoaDong(q);
    return !!xung[k] || coLoi(tt[k]) || canNhan?.k === k;
  }), [nhom, mo, tt, xung, canNhan]);
  const dongD = useMemo(() => dsHien.map(x => x.q), [dsHien]);
  // MỌI ánh xạ chỉ số d ↔ dòng đọc danh sách này (đầu nhóm + con đang mở), không đọc `hien`.
  const hienRef = useRef<Dong[]>(dongD); hienRef.current = dongD;
  const khoaD = useMemo(() => dongD.map(khoaDong), [dongD]);
  const khoaRef = useRef(khoaD); khoaRef.current = khoaD;
  const theoKhoa = useMemo(() => new Map(dongD.map(q => [khoaDong(q), q])), [dongD]);
  const theoKhoaRef = useRef(theoKhoa); theoKhoaRef.current = theoKhoa;
  const dsHienRef = useRef<DongHien<Dong>[]>(dsHien); dsHienRef.current = dsHien;
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
  // Bảng này đã vá tại chỗ; bảng duyet khác (bên / lọc khác) đánh dấu cũ, tải khi mở; màn khác tải lại.
  const lamCuNoiKhac = () => {
    qc.invalidateQueries({ queryKey: ["doi-thu", "duyet"], refetchType: "none" });
    qc.invalidateQueries({ queryKey: ["doi-thu"], predicate: x => x.queryKey[1] !== "duyet" });
  };

  const datO = (k: string, ma: string, t: TT | null) => datTT(s => {
    const r = { ...(s[k] ?? {}) };
    if (t) r[ma] = t; else delete r[ma];
    return { ...s, [k]: r };
  });
  // Trả tiêu điểm về ô SAU lần vẽ kế tiếp — useEffect chứ không requestAnimationFrame: rAF không chạy khi thẻ trình duyệt
  // bị ẩn, tiêu điểm rơi về <body> và phím mũi tên cuộn cả trang.
  // Ô theo khoá dòng. `cho` = khoá của dòng sắp rời bảng: ô đích chưa vẽ (dòng con của nhóm đang đóng — nó lên làm dòng
  // đầu khi dòng kia đi) thì chờ tới lần vẽ mà dòng đó đã rời bảng.
  const choTapTrung = useRef<(Neo & { cho?: string }) | null>(null);
  const tapTrung = (n: (Neo & { cho?: string }) | null) => { choTapTrung.current = n; };
  useEffect(() => {
    const n = choTapTrung.current;
    if (!n) return;
    const td = bang.current?.querySelector<HTMLElement>(`tr[data-k="${CSS.escape(n.k)}"] > td[data-c="${n.c}"]`);
    if (!td && n.cho && khoaRef.current.includes(n.cho)) return;
    choTapTrung.current = null;
    td?.focus();
  });
  // Dòng của ô đang sửa không còn hiện (ẩn / tải lại đổi khoá) → đóng ô sửa; chữ đang gõ bỏ (dòng đã đi).
  useEffect(() => { if (sua && !theoKhoa.has(sua.n.k)) datSua(null); }, [sua, theoKhoa]);

  /** Xếp một thao tác ghi của dòng `k` sau thao tác trước của CÙNG dòng (lưu ô, ẩn / khôi phục, gộp). */
  const guiHang = useCallback(<T,>(k: string, fn: () => Promise<T>): Promise<T> => {
    const lan = (hang.current.get(k) ?? Promise.resolve()).then(fn);
    hang.current.set(k, lan.then(() => undefined, () => undefined));
    return lan;
  }, []);

  const docLai = async (k: string, nguon: string, id: number) => {
    const m = await lay<{ quan_sat: QuanSat }>(`/api/doi-thu/mat-hang/${nguon}/${id}${kx ? "?" + kx : ""}`);
    qc.setQueryData<DuLieu>(khoaQ, d => d && ({ ...d, dong: ghepDong(d.dong, { nguon, id }, { ...m.quan_sat, _k: k } as Dong) as Dong[] }));
  };

  /** Ghi 409 của dòng `k`, gom thêm thao tác `c` (thay thao tác cũ cùng loại / cùng ô). */
  const themCho = (k: string, x: XungDot | null, c: Cho) => datXung(s => {
    const cu = s[k];
    if (!cu && !x) return s;
    const ds = (cu?.ds ?? []).filter(y => (c.loai === "an" ? y.loai !== "an" : y.loai === "an" || y.ma !== c.ma));
    return { ...s, [k]: { x: x ?? cu!.x, ds: [...ds, c] } };
  });

  /** Lưu MỘT ô, xếp hàng sau lần lưu trước của cùng dòng. Dòng đang 409 → không gửi, gom vào danh sách chờ của 409. */
  const luu = useCallback((k: string, ma: TruongO, gt: string, o: { ghi_de?: boolean; nhan?: "cung_hang" | "thay_the" } = {}) => {
    void guiHang(k, async () => {
      const q = docDong(k);
      if (!q) return;
      if (!o.ghi_de && xungRef.current[k]) { themCho(k, null, { ma, gt, nhan: o.nhan }); return; }
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
        lamCuNoiKhac();
        // Ghép đổi cho MỌI dòng cùng <bên>/<hàng> (và sua_cuoi của chúng): tải lại cả bảng.
        if (doiGhep) qc.invalidateQueries({ queryKey: khoaQ, exact: true });
      } catch (e) {
        const x = docXungDot(e);
        if (x?.thay_boi) { vaDong(k, y => ({ ...y, thay_boi: x.thay_boi })); datO(k, ma, null); }
        else if (x) { themCho(k, x, { ma, gt, nhan: o.nhan }); datO(k, ma, null); }
        else datO(k, ma, { kieu: "loi", loi: e instanceof Error ? e.message : String(e), gt });
      }
    });
  }, [kx, qc, khoaQ, guiHang]);   // eslint-disable-line react-hooks/exhaustive-deps

  /** 🗑 (an = true) / Khôi phục (an = false) — CÙNG hàng đợi theo dòng với lưu ô. Thành công → dòng rời bảng đang xem
   *  (bỏ khỏi đệm ngay), rồi tải lại bảng: máy chủ chọn lại dòng đại diện của mặt hàng. */
  const datAn = useCallback((k: string, an: boolean, o: { ghi_de?: boolean } = {}) => {
    void guiHang(k, async () => {
      const q = docDong(k);
      if (!q) return;
      if (!o.ghi_de && xungRef.current[k]) { themCho(k, null, { loai: "an", an }); return; }
      datO(k, MA_AN, { kieu: "dang" });
      try {
        await gui("/api/doi-thu/an", { nguon: q.nguon, id: q.id, an, da_xem: q.sua_cuoi, ghi_de: !!o.ghi_de });
        // Tiêu điểm đang ở trong dòng sắp biến mất → về ô đầu của dòng thế chỗ (không rơi về <body>): dòng con đầu của
        // chính mặt hàng đó (nó lên làm dòng đầu), không thì dòng dưới, không nữa thì dòng trên.
        const tr = (document.activeElement as HTMLElement | null)?.closest?.("tr");
        if (tr && tr.getAttribute("data-k") === k) {
          const i = khoaRef.current.indexOf(k);
          const con = nhomRef.current.find(g => g.dau === hienRef.current[i])?.con[0];
          const ke = con ?? hienRef.current[i + 1] ?? hienRef.current[i - 1];
          if (i >= 0 && ke) { const n = { k: khoaDong(ke), c: 0 }; datChon(n); tapTrung({ ...n, cho: k }); }
        }
        qc.setQueryData<DuLieu>(khoaQ, d => d && ({ ...d, dong: d.dong.filter(r => khoaDong(r) !== k), tong: Math.max(0, d.tong - 1) }));
        datTT(s => { if (!s[k]) return s; const n = { ...s }; delete n[k]; return n; });
        datXung(s => { if (!s[k]) return s; const n = { ...s }; delete n[k]; return n; });
        lamCuNoiKhac();
        qc.invalidateQueries({ queryKey: khoaQ, exact: true });
      } catch (e) {
        const x = docXungDot(e);
        if (x?.thay_boi) { vaDong(k, y => ({ ...y, thay_boi: x.thay_boi })); datO(k, MA_AN, null); }
        else if (x) { themCho(k, x, { loai: "an", an }); datO(k, MA_AN, null); }
        else datO(k, MA_AN, { kieu: "loi", loi: e instanceof Error ? e.message : String(e) });
      }
    });
  }, [qc, khoaQ, guiHang]);   // eslint-disable-line react-hooks/exhaustive-deps

  /** Gộp mặt hàng của dòng `k` vào `vao` (khoá mặt hàng đích) / tách ra (`vao` null). Lỗi (kể cả 409) ném về hộp. */
  const chayGop = useCallback((k: string, vao: string | null, ghi_de: boolean) => guiHang(k, async () => {
    const q = docDong(k);
    if (!q) throw new Error("Dòng này không còn trong bảng — tải lại rồi thử lại.");
    await gui("/api/doi-thu/gop-mat-hang", { ma_doi_thu: q.ma_doi_thu, ma_hang_dt: q.ma_hang_dt, vao_ma_hang_dt: vao,
      da_xem: q.sua_cuoi, ghi_de });
    lamCuNoiKhac();
    // Nhóm / đại diện đổi cho nhiều dòng: tải lại cả bảng (đợi xong mới đóng hộp).
    await qc.invalidateQueries({ queryKey: khoaQ, exact: true });
  }), [qc, khoaQ, guiHang]);   // eslint-disable-line react-hooks/exhaustive-deps

  /** Mở ô sửa tại ô neo `n`. Ở lọc "Đã xoá" bảng CHỈ ĐỌC (di chuyển bằng bàn phím vẫn được). */
  const moSua = (n: Neo, dau?: string) => {
    const q = theoKhoaRef.current.get(n.k), c = cots[n.c];
    if (daXoa || !q || !c || !suaDuoc(q, c)) return false;
    const loiCu = ttRef.current[n.k]?.[c.ma];
    phien.current++;
    datChon(n);
    datSua({ n, dau: dau ?? (loiCu?.kieu === "loi" && loiCu.gt != null ? loiCu.gt : giaTriSua(q, c.ma as TruongO)),
      phien: phien.current });
    return true;
  };

  const bam = useCallback((k: string, c: number) => {
    const n = { k, c }, s = suaRef.current;
    if (s && s.n.k === k && s.n.c === c) return;
    datChon(n);
    if (!moSua(n)) tapTrung(n);
  }, [cots, daXoa]);   // eslint-disable-line react-hooks/exhaustive-deps
  const vao = useCallback((k: string, c: number) => {
    datChon(v => (v && v.k === k && v.c === c ? v : { k, c }));
  }, []);

  /** Ô sửa đóng: lưu vào ĐÚNG dòng đã mở ô (khoá `k`), rồi (Enter / Tab) mở ô sửa được kế tiếp tính từ vị trí HIỆN TẠI
   *  của dòng đó. */
  const xongSua = useCallback((k: string, c: number, gt: string, h: Ket) => {
    datSua(null);
    luu(k, cots[c].ma as TruongO, gt);
    if (h == null) return;                                  // rời ô bằng chuột: tiêu điểm đã ở chỗ người ta bấm
    const goc = { k, c };
    if (h === "giu") { datChon(goc); tapTrung(goc); return; }
    // Enter / Tab: ô kế tiếp SỬA ĐƯỢC mở luôn để gõ tiếp (điền "tịnh 1 gói" cho cả loạt hàng).
    let n = neoKeTiep(khoaRef.current, goc, h, cots);
    while (n && !suaDuoc(theoKhoaRef.current.get(n.k)!, cots[n.c])) n = neoKeTiep(khoaRef.current, n, h, cots);
    if (n) moSua(n); else { datChon(goc); tapTrung(goc); }
  }, [luu, cots, daXoa]);   // eslint-disable-line react-hooks/exhaustive-deps

  const boSua = useCallback(() => {
    const s = suaRef.current;
    if (s) { datChon(s.n); tapTrung(s.n); }
    datSua(null);
  }, []);

  const chonNhan = useCallback((k: string, n: "cung_hang" | "thay_the" | null) => {
    const cn = canNhanRef.current;
    datCanNhan(null);
    if (cn && n) luu(k, "ma_kome", cn.gt, { nhan: n });
    const o = { k, c: cots.findIndex(c => c.ma === "ma_kome") };
    tapTrung(o); datChon(o);
  }, [luu, cots]);

  const ghiDe = useCallback((k: string) => {
    const x = xungRef.current[k];
    if (!x) return;
    datXung(s => { const n = { ...s }; delete n[k]; return n; });
    xungRef.current = { ...xungRef.current }; delete xungRef.current[k];
    // Ô trước, ẩn / khôi phục sau cùng (dòng rời bảng thì các ô xếp sau nó không còn gì để lưu).
    for (const c of x.ds) if (c.loai !== "an") luu(k, c.ma, c.gt, { ghi_de: true, nhan: c.nhan });
    for (const c of x.ds) if (c.loai === "an") datAn(k, c.an, { ghi_de: true });
  }, [luu, datAn]);

  const layBanKia = useCallback((k: string) => {
    const q = docDong(k);
    datXung(s => { const n = { ...s }; delete n[k]; return n; });
    if (!q) return;
    docLai(k, q.nguon, q.id).catch(() => taiLai());
  }, [kx, taiLai]);   // eslint-disable-line react-hooks/exhaustive-deps

  /** Mở / đóng nhóm (ô chọn neo theo khoá nên không dời). Đóng nhóm mà ô chọn nằm ở dòng con → về dòng đầu. Nhóm bị ép
   *  mở (dòng con đang lỗi / 409) thì không đóng được. */
  const moNhom = useCallback((kn: string) => {
    const ds = dsHienRef.current;
    const x = ds.find(y => y.kn === kn && y.soCon != null);
    if (!x || !x.soCon || x.ep) return;
    const moi = !x.mo;
    datMo(s => { const n = new Set(s); if (moi) n.add(kn); else n.delete(kn); return n; });
    if (!moi) {
      const con = new Set(ds.filter(y => y.kn === kn && y.soCon == null).map(y => khoaDong(y.q)));
      const dau = khoaDong(x.q);
      datChon(v => (v && con.has(v.k) ? { k: dau, c: v.c } : v));
    }
  }, []);

  const moGop = useCallback((k: string) => datGop(k), []);

  // Bàn phím khi KHÔNG sửa: mũi tên di chuyển, Enter / F2 mở ô, gõ ký tự mở ô bắt đầu bằng ký tự đó.
  const phim = (e: KeyboardEvent<HTMLTableElement>) => {
    if (sua || !chon || !(e.target as HTMLElement).matches("td")) return;
    const h: Huong | null = e.key === "ArrowDown" ? "xuong" : e.key === "ArrowUp" ? "len" : e.key === "ArrowLeft" ? "trai"
      : e.key === "ArrowRight" ? "phai" : e.key === "Tab" ? (e.shiftKey ? "tab_lui" : "tab") : null;
    if (h) {
      const v = neoKeTiep(khoaRef.current, chon, h, cots);
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

  const chonHien = !!chon && theoKhoa.has(chon.k);   // ô chọn thuộc dòng đã rời bảng → dòng đầu nhận Tab vào bảng
  const qGop = gop ? (dong as Dong[]).find(r => khoaDong(r) === gop) : undefined;
  const goiY = "dt-bs-goi-y";
  if (!hien.length) return <p className="dt-nhat">Không có dòng nào{tim.trim() ? " khớp ô tìm" : ""}.</p>;
  return (
    <div className="dt-bs-khung">
      <datalist id={goiY}>{maGoiY.map(h => <option key={h.ma} value={h.ma}>{h.ten}</option>)}</datalist>
      <table ref={bang} className="dt-bs" onKeyDown={phim} aria-label="Mặt hàng đối thủ — bấm ô để sửa">
        <thead><tr>{cots.map(c => <th key={c.ma} scope="col" className={c.kieu === "so" || c.ma === "yen_kg" ? "bs-so" : undefined}>
          {c.nhan}</th>)}<th scope="col">Duyệt</th><th scope="col"><span className="dt-an">Sửa thêm</span></th>
          <th scope="col"><span className="dt-an">{daXoa ? "Khôi phục" : "Xoá"}</span></th></tr></thead>
        <tbody>
          {dsHien.map(({ q, kn, soCon, mo: m, ep }, d) => { const k = khoaD[d]; return (
            <DongBang key={k} k={k} q={q} cots={cots} chonC={chon?.k === k ? chon.c : -1} vaoDau={!chonHien && d === 0}
              sua={sua?.n.k === k ? sua : null} tt={tt[k]} xung={xung[k]} canNhan={canNhan?.k === k ? canNhan : null}
              goiY={goiY} dangGui={dangGui} kn={kn} soCon={soCon} mo={m} ep={ep} daXoa={daXoa}
              bam={bam} vao={vao} xongSua={xongSua} boSua={boSua} chonNhan={chonNhan}
              ghiDe={ghiDe} layBanKia={layBanKia} moPopup={moPopup} xacNhan={xacNhan} taiLai={taiLai}
              moNhom={moNhom} datAn={datAn} moGop={moGop} />); })}
        </tbody>
      </table>
      {qGop && <HopGop key={gop!} q={qGop} ds={dong as Dong[]} chay={(vao, ghi_de) => chayGop(gop!, vao, ghi_de)}
        dong={() => datGop(null)} giu={() => { qc.invalidateQueries({ queryKey: khoaQ, exact: true }); datGop(null); }} />}
    </div>);
}
