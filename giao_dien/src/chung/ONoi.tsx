// Ô nổi chung cho mọi thứ KHÔNG phải BieuDo (đặc tả 2026-09-28-tong-quan-it-chu-design.md §3.1):
//   * chuột: rê vào hiện, rời ẩn, bấm là đi liên kết;
//   * chạm: lần 1 hiện, lần 2 (cùng phần tử) đi; chạm ra ngoài / cuộn / Esc thì đóng;
//   * bàn phím: Tab tới thì hiện, Enter đi.
// Chỉ MỘT ô nổi mở tại một thời điểm. Ô nổi vẽ qua portal vào <body> (position: fixed) để
// không bị `overflow: hidden` của khối cắt mất.
import { useEffect, useId, useLayoutEffect, useRef, useState, useSyncExternalStore,
  type CSSProperties, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { buocCham, hoanToanNgoaiKhung, viTriNoi } from "./o_noi_logic";

let dangMo: string | null = null;
const nghe = new Set<() => void>();
const datMo = (id: string | null) => { dangMo = id; nghe.forEach(f => f()); };
const theoDoi = (f: () => void) => { nghe.add(f); return () => { nghe.delete(f); }; };

export function ONoi({ noi_dung, href, onBam, children, className, style, nhan, svg }: {
  noi_dung: ReactNode; href?: string; onBam?: () => void; children: ReactNode;
  className?: string; style?: CSSProperties; nhan?: string;
  // true khi bọc quanh phần tử SVG (<g>, <rect>…): một `<span>` không href
  // là phần tử SVG LẠ, trình duyệt coi cả cây con "không vẽ" — ép dùng `<a>`
  // (hợp lệ trong SVG dù không có href) để con vẫn hiện ra bình thường.
  svg?: boolean;
}) {
  const id = useId();
  const mo = useSyncExternalStore(theoDoi, () => dangMo === id);
  const goc = useRef<HTMLElement | null>(null);
  const noi = useRef<HTMLDivElement>(null);
  const kieu = useRef("mouse");
  const quaCon = useRef(false);   // focus do bấm/chạm (không phải Tab) — không tự mở
  const [vt, datVt] = useState<{ left: number; top: number } | null>(null);

  useLayoutEffect(() => {
    if (!mo || !goc.current || !noi.current) { datVt(null); return; }
    datVt(viTriNoi(goc.current.getBoundingClientRect(),
      { w: noi.current.offsetWidth, h: noi.current.offsetHeight }, { w: window.innerWidth, h: window.innerHeight }));
  }, [mo]);

  useEffect(() => {
    if (!mo) return;
    const ngoai = (e: PointerEvent) => { if (!goc.current?.contains(e.target as Node)) datMo(null); };
    // Cuộn (kể cả cuộn Tab đưa phần tử vào khung nhìn) ĐỊNH VỊ LẠI ô nổi thay vì đóng —
    // đóng ở đây từng làm Tab bàn phím mở ô nổi rồi tự đóng ngay khi trình duyệt cuộn tới.
    // Chỉ đóng khi phần tử gốc đã ra khỏi khung nhìn hẳn.
    const cuon = () => {
      const khung = { w: window.innerWidth, h: window.innerHeight };
      if (!goc.current || !noi.current) { datMo(null); return; }
      const r = goc.current.getBoundingClientRect();
      if (hoanToanNgoaiKhung(r, khung)) { datMo(null); return; }
      datVt(viTriNoi(r, { w: noi.current.offsetWidth, h: noi.current.offsetHeight }, khung));
    };
    document.addEventListener("pointerdown", ngoai);
    window.addEventListener("scroll", cuon, true);
    return () => { document.removeEventListener("pointerdown", ngoai); window.removeEventListener("scroll", cuon, true); };
  }, [mo]);

  const p = {
    ref: (e: HTMLElement | null) => { goc.current = e; },
    className: "o-noi-goc" + (className ? " " + className : ""),
    style,
    tabIndex: href ? undefined : 0,
    role: href ? undefined : onBam ? "button" : undefined,
    "aria-label": nhan,
    "aria-describedby": mo ? id : undefined,
    onPointerDown: (e: React.PointerEvent) => { kieu.current = e.pointerType; quaCon.current = true; },
    onPointerEnter: (e: React.PointerEvent) => { if (e.pointerType !== "touch") datMo(id); },
    onPointerLeave: (e: React.PointerEvent) => { if (e.pointerType !== "touch" && dangMo === id) datMo(null); },
    onFocus: () => { if (!quaCon.current) datMo(id); },
    onBlur: () => { quaCon.current = false; if (dangMo === id) datMo(null); },
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Escape") datMo(null);
      else if (e.key === "Enter" && !href) onBam?.();
      else if (e.key === " " && !href) { e.preventDefault(); onBam?.(); }
    },
    onClick: (e: React.MouseEvent) => {
      const b = buocCham(mo, kieu.current);
      kieu.current = "mouse";
      if (b === "mo") { e.preventDefault(); datMo(id); quaCon.current = false; return; }
      if (!href) onBam?.();
      quaCon.current = false;
    },
  };

  return (
    <>
      {href || svg ? <a href={href} {...p}>{children}</a> : <span {...p}>{children}</span>}
      {mo && createPortal(
        <div ref={noi} id={id} role="tooltip" className="bd-noi o-noi"
          style={vt ? { left: vt.left, top: vt.top } : { left: -9999, top: 0 }}>{noi_dung}</div>,
        document.body)}
    </>
  );
}

/** Một dòng trong ô nổi: nhãn … giá trị (cùng kiểu dòng của ô nổi BieuDo). */
export function DongNoi({ nhan, gia, mau }: { nhan: ReactNode; gia: ReactNode; mau?: string }) {
  return <div>{mau && <i style={{ background: mau }} />}{nhan}<b>{gia}</b></div>;
}
