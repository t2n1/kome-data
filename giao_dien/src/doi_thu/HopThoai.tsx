// Hộp thoại dùng chung của màn Thị trường & đối thủ (pop-up sửa giá, điều kiện, bên…).
// Portal vào <body>, lớp .lop-phu.giua (khung.css / tong_quan.css). Esc / bấm nền đóng; focus vào phần tử
// mang `data-focus` (hoặc phần tử focus được đầu tiên TRONG NỘI DUNG, rồi mới tới ✕), bẫy Tab trong hộp,
// trả focus về phần tử đã gọi khi đóng. Mở chồng nhau: chỉ hộp trên cùng nhận Esc / Tab (hop_thoai_logic.ts).
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { dayVao, goRa, laDinh } from "./hop_thoai_logic";

const FOCUS_DUOC = 'a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

export function HopThoai({ tieu_de, dong, children, rong = 640 }: {
  tieu_de: ReactNode; dong: () => void; children: ReactNode; rong?: number;
}) {
  const id = useId();
  const hop = useRef<HTMLDivElement>(null);
  const noi_dung = useRef<HTMLDivElement>(null);
  // Phần tử gọi hộp: chụp NGAY khi dựng lần đầu (giai đoạn render, trước commit) — con có `autoFocus` được focus
  // trong lúc commit, TRƯỚC cả useLayoutEffect của cha, nên chụp ở effect thì đã muộn.
  const [goi] = useState(() => document.activeElement as HTMLElement | null);
  const batDauNen = useRef(false);   // nền chỉ đóng khi nhấn VÀ thả đều trên nền (kéo chọn chữ ra ngoài hộp không đóng)
  const dongRef = useRef(dong);           // để nhấn Esc luôn gọi bản `dong` mới nhất mà không gắn lại bộ nghe
  dongRef.current = dong;

  useEffect(() => {
    const ma = dayVao();
    const ds = () => Array.from(hop.current?.querySelectorAll<HTMLElement>(FOCUS_DUOC) ?? []).filter(e => e.offsetParent !== null || e === document.activeElement);
    const dau = noi_dung.current?.querySelector<HTMLElement>("[data-focus]")
      ?? noi_dung.current?.querySelector<HTMLElement>(FOCUS_DUOC) ?? ds()[0];
    if (!noi_dung.current?.contains(document.activeElement)) (dau ?? hop.current)?.focus();   // con đã autoFocus thì giữ

    const phim = (e: KeyboardEvent) => {
      if (!laDinh(ma)) return;   // hộp chồng lên trên đang giữ Esc / Tab
      if (e.key === "Escape") { e.stopPropagation(); dongRef.current(); return; }
      if (e.key !== "Tab") return;
      const d = ds();
      if (!d.length) { e.preventDefault(); hop.current?.focus(); return; }
      const dauT = d[0], cuoi = d[d.length - 1], hien = document.activeElement;
      if (e.shiftKey && (hien === dauT || !hop.current?.contains(hien))) { e.preventDefault(); cuoi.focus(); }
      else if (!e.shiftKey && (hien === cuoi || !hop.current?.contains(hien))) { e.preventDefault(); dauT.focus(); }
    };
    document.addEventListener("keydown", phim, true);
    return () => {
      document.removeEventListener("keydown", phim, true);
      goRa(ma);
      if (goi && document.contains(goi)) goi.focus();
    };
  }, []);

  return createPortal(
    <div className="lop-phu giua"
      onMouseDown={e => { batDauNen.current = e.target === e.currentTarget; }}
      onClick={e => { if (batDauNen.current && e.target === e.currentTarget) dong(); batDauNen.current = false; }}>
      <div ref={hop} className="dt-hop" role="dialog" aria-modal="true" aria-labelledby={id} tabIndex={-1}
        style={{ maxWidth: rong }}>
        <div className="dt-hop-dau">
          <strong id={id}>{tieu_de}</strong>
          <button type="button" className="nut-dong" aria-label="Đóng" onClick={dong}>✕</button>
        </div>
        <div ref={noi_dung} className="dt-hop-than">{children}</div>
      </div>
    </div>,
    document.body);
}
