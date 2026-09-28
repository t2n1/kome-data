// Lưới Tổng quan 12 cột (đặc tả 2026-09-29-tong-quan-luoi-12-cot-design.md). Mỗi khối có
// toạ độ (x, y) + cỡ theo ô lưới; xếp chỗ + nén dọc ở luoi_logic.ts (cùng thuật toán máy chủ).
//
// Kéo bằng POINTER EVENTS (chuột / bút / cảm ứng như nhau), không HTML5 drag & drop:
//   * kéo từ ĐẦU khối ([data-keo], trừ nút / liên kết / ⓘ), bắt đầu khi rời điểm bấm > 4px;
//   * khối bay theo con trỏ bằng `transform` (không qua React mỗi khung hình); ô BÓNG ở chỗ
//     khối sẽ rơi; các khối khác dạt ra bằng FLIP (chụp vị trí trước → đổi bố cục → trượt về);
//   * thả: khối trượt vào ô bóng; Esc huỷ; sát mép cửa sổ thì tự cuộn;
//   * góc phải dưới đổi cỡ liền mạch theo pixel, ô bóng cho cỡ đã khớp lưới.
// Khối đang bay GIỮ ô lưới gốc suốt lúc kéo (transform tính từ đó), bố cục tạm chỉ dời khối khác.
// Màn hẹp (< 900px): một cột theo (y, x), không kéo bằng chuột — bàn phím vẫn được.
import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import type { OBoCuc } from "../khoi_dau";
import { COT, an as anKhoi, datCho, day, dichPhim, doiCo, hangTai, soHang } from "./luoi_logic";

const HANG = 40, KHE = 12, NGUONG = 4, MEP_CUON = 64;
const RONG_MAN = "(min-width: 901px)";

function useManRong() {
  const [r, dat] = useState(() => matchMedia(RONG_MAN).matches);
  useEffect(() => {
    const m = matchMedia(RONG_MAN), f = () => dat(m.matches);
    m.addEventListener("change", f);
    return () => m.removeEventListener("change", f);
  }, []);
  return r;
}
const itChuyenDong = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const vung = (o: OBoCuc): CSSProperties => ({ gridColumn: `${o.x + 1} / span ${o.rong}`, gridRow: `${o.y + 1} / span ${o.cao}` });
const theoViTri = (ds: OBoCuc[]) => ds.filter(o => !o.an).sort((a, b) => a.y - b.y || a.x - b.x);

type Keo = { id: string; kieu: "doi" | "co" };

export function Luoi({ bo_cuc, datBoCuc, sua_duoc, ve, nhan, hien_luoi }: {
  bo_cuc: OBoCuc[];
  datBoCuc: (b: OBoCuc[]) => void;
  sua_duoc: boolean;
  ve: (o: OBoCuc) => ReactNode;
  nhan: (id: string) => string;
  hien_luoi: boolean;
}) {
  const luoi = useRef<HTMLDivElement>(null);
  const rongMan = useManRong();
  const keoDuoc = sua_duoc && rongMan;
  const [tam, datTam] = useState<OBoCuc[] | null>(null);   // bố cục tạm lúc đang kéo / đổi cỡ
  const [keo, datKeo] = useState<Keo | null>(null);
  const [bao, datBao] = useState("");
  const truoc = useRef<Map<string, DOMRect> | null>(null);
  const dangBay = useRef<string | null>(null);              // khối theo con trỏ — FLIP bỏ qua
  const hien = tam ?? bo_cuc;

  /** Chụp vị trí NHÌN THẤY của mọi khối ngay trước khi đổi bố cục (FLIP: First). */
  const chup = () => {
    const m = new Map<string, DOMRect>();
    luoi.current?.querySelectorAll<HTMLElement>("[data-khoi]").forEach(el => m.set(el.dataset.khoi!, el.getBoundingClientRect()));
    truoc.current = m;
  };
  // FLIP: Last → Invert → Play, sau khi React đã đặt bố cục mới.
  useLayoutEffect(() => {
    const m = truoc.current;
    truoc.current = null;
    if (!m || !luoi.current || itChuyenDong()) return;
    luoi.current.querySelectorAll<HTMLElement>("[data-khoi]").forEach(el => {
      const id = el.dataset.khoi!, a = m.get(id);
      if (!a || id === dangBay.current) return;
      el.style.transition = "none";
      el.style.transform = "";
      const b = el.getBoundingClientRect();
      const dx = a.left - b.left, dy = a.top - b.top;
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return;
      el.style.transform = `translate(${dx}px, ${dy}px)`;
      void el.offsetWidth;
      el.style.transition = "transform 200ms cubic-bezier(.2,.7,.3,1)";
      el.style.transform = "";
      el.addEventListener("transitionend", () => { el.style.transition = ""; }, { once: true });
    });
  }, [hien]);

  const doLuoi = () => {
    const el = luoi.current!, k = getComputedStyle(el);
    const khe = parseFloat(k.columnGap) || KHE, kheH = parseFloat(k.rowGap) || KHE;
    return {
      oRong: (el.clientWidth - (COT - 1) * khe) / COT + khe, khe, kheH,
      // Cỡ THẬT của từng hàng (hàng giãn theo nội dung) — Chrome/Firefox trả mọi hàng, kể cả hàng ngầm.
      hang: k.gridTemplateRows.split(" ").map(parseFloat).filter(v => !Number.isNaN(v)),
      khung: el.getBoundingClientRect(),
    };
  };

  const batDau = (o: OBoCuc, e: React.PointerEvent<HTMLElement>) => {
    if (!keoDuoc || e.button !== 0 || keo) return;
    const t = e.target as HTMLElement;
    const laCo = !!t.closest(".khoi-co");
    if (!laCo && (!t.closest("[data-keo]") || t.closest("a,button,input,select,textarea,label,.o-noi-goc,.khoi-i"))) return;
    if (laCo) { e.preventDefault(); e.stopPropagation(); }
    const the = e.currentTarget, goc = bo_cuc, id = o.id, pid = e.pointerId;
    const x0 = e.clientX, y0 = e.clientY, cuon0 = window.scrollY;
    const d0 = doLuoi(), r0 = the.getBoundingClientRect();
    const ox = r0.left - d0.khung.left, oy = r0.top - d0.khung.top;
    let dang = false, cuoi = goc, px = x0, py = y0, raf = 0, oCu = "";

    const capNhat = () => {
      const dx = px - x0, dy = py - y0 + (window.scrollY - cuon0), d = doLuoi();
      let khoa: string, moi: () => OBoCuc[];
      if (laCo) {
        const w = Math.max(80, r0.width + dx), h = Math.max(60, r0.height + dy);
        the.style.width = `${w}px`;
        the.style.height = `${h}px`;
        const rong = Math.round((w + d.khe) / d.oRong), cao = soHang(h, o.y, d.hang, d.kheH, HANG);
        khoa = `${rong}x${cao}`;
        moi = () => doiCo(goc, id, rong, cao);
      } else {
        the.style.transform = `translate(${dx}px, ${dy}px) rotate(.5deg)`;
        const x = Math.round((ox + dx) / d.oRong), y = hangTai(Math.max(0, oy + dy), d.hang, d.kheH, HANG);
        khoa = `${x},${y}`;
        moi = () => datCho(goc, id, x, y);
      }
      if (khoa === oCu) return;
      oCu = khoa;
      cuoi = moi();
      chup();
      datTam(cuoi);
    };
    const cuon = () => {
      raf = 0;
      if (!dang) return;
      const v = py < MEP_CUON ? -(MEP_CUON - py) / 3 : py > innerHeight - MEP_CUON ? (py - innerHeight + MEP_CUON) / 3 : 0;
      if (!v) return;
      window.scrollBy(0, v);
      capNhat();
      raf = requestAnimationFrame(cuon);
    };
    const di = (ev: PointerEvent) => {
      if (ev.pointerId !== pid) return;
      px = ev.clientX; py = ev.clientY;
      if (!dang) {
        if (!laCo && Math.hypot(px - x0, py - y0) < NGUONG) return;
        dang = true;
        dangBay.current = id;
        the.style.transition = "none";
        datKeo({ id, kieu: laCo ? "co" : "doi" });
        datTam(goc);
        document.body.classList.add("dang-xep-luoi");
      }
      ev.preventDefault();
      capNhat();
      if (!raf) raf = requestAnimationFrame(cuon);
    };
    const xong = (huy: boolean) => {
      removeEventListener("pointermove", di);
      removeEventListener("pointerup", nha);
      removeEventListener("pointercancel", bo);
      removeEventListener("keydown", esc, true);
      cancelAnimationFrame(raf);
      if (!dang) return;
      dang = false;
      document.body.classList.remove("dang-xep-luoi");
      chup();                         // chụp cả khối đang bay → nó trượt từ chỗ thả vào ô
      dangBay.current = null;
      the.style.transform = ""; the.style.width = ""; the.style.height = ""; the.style.transition = "";
      datTam(null); datKeo(null);
      if (huy || JSON.stringify(cuoi) === JSON.stringify(goc)) { if (huy) datBao("Đã huỷ — bố cục giữ nguyên."); return; }
      datBoCuc(cuoi);
      const n = cuoi.find(x => x.id === id)!;
      datBao(`${nhan(id)}: cột ${n.x + 1}, hàng ${n.y + 1}, rộng ${n.rong}, cao ${n.cao}.`);
    };
    const nha = (ev: PointerEvent) => { if (ev.pointerId === pid) xong(false); };
    const bo = (ev: PointerEvent) => { if (ev.pointerId === pid) xong(true); };
    const esc = (ev: KeyboardEvent) => { if (ev.key === "Escape" && dang) { ev.preventDefault(); ev.stopPropagation(); xong(true); } };
    addEventListener("pointermove", di, { passive: false });
    addEventListener("pointerup", nha);
    addEventListener("pointercancel", bo);
    addEventListener("keydown", esc, true);
  };

  const PHIM = { ArrowUp: "len", ArrowDown: "xuong", ArrowLeft: "trai", ArrowRight: "phai" } as const;
  const phim = (o: OBoCuc, e: React.KeyboardEvent) => {
    const m = PHIM[e.key as keyof typeof PHIM];
    if (!m) return;
    e.preventDefault();
    const moi = e.shiftKey
      ? doiCo(bo_cuc, o.id, o.rong + (m === "phai" ? 1 : m === "trai" ? -1 : 0), o.cao + (m === "xuong" ? 1 : m === "len" ? -1 : 0))
      : dichPhim(bo_cuc, o.id, m);
    chup();
    datBoCuc(moi);
    const n = moi.find(x => x.id === o.id)!;
    datBao(`${nhan(o.id)}: cột ${n.x + 1}, hàng ${n.y + 1}, rộng ${n.rong}, cao ${n.cao}.`);
    requestAnimationFrame(() => (document.querySelector(`[data-khoi="${o.id}"] .khoi-tay`) as HTMLElement | null)?.focus());
  };

  const coLuoi = rongMan && (hien_luoi || !!keo);
  const soHangLuoi = Math.max(day(hien), keo ? day(bo_cuc) : 0) + (keo ? 4 : 0);
  const bong = keo ? hien.find(x => x.id === keo.id) : undefined;

  return (
    <>
      <div ref={luoi} className={"luoi-tq" + (keo ? " dang-xep" : "") + (coLuoi ? " co-luoi" : "") + (keoDuoc ? " keo-duoc" : "")}>
        {coLuoi && Array.from({ length: soHangLuoi * COT }, (_, i) =>
          <div key={"o" + i} className="o-luoi-o" aria-hidden="true" style={{ gridColumn: String(i % COT + 1), gridRow: String(Math.floor(i / COT) + 1) }} />)}
        {bong && <div className="o-bong" aria-hidden="true" style={vung(bong)} />}
        {theoViTri(hien).map(o => {
          // Khối đang kéo giữ ô GỐC (transform tính từ đó); khối khác theo bố cục tạm.
          const v = keo?.id === o.id ? bo_cuc.find(x => x.id === o.id) ?? o : o;
          return (
            <section key={o.id} data-khoi={o.id} aria-label={nhan(o.id)} style={vung(v)}
              className={"o-luoi" + (keo?.id === o.id ? (keo.kieu === "co" ? " dang-co" : " dang-bay") : "")}
              onPointerDown={e => batDau(v, e)}>
              {sua_duoc && <>
                <button type="button" className="khoi-tay" onKeyDown={e => phim(v, e)}
                  aria-label={`Sắp xếp khối ${nhan(o.id)} — mũi tên đổi chỗ, Shift + mũi tên đổi cỡ`}
                  title="Kéo đầu khối để sắp xếp">⠿</button>
                <button type="button" className="khoi-an" aria-label={`Ẩn khối ${nhan(o.id)}`} title="Ẩn khối"
                  onClick={() => { chup(); datBoCuc(anKhoi(bo_cuc, o.id)); datBao(`Đã ẩn ${nhan(o.id)} — hiện lại ở "Thêm chức năng".`); }}>✕</button>
                {keoDuoc && <div className="khoi-co" title="Kéo để đổi kích thước" aria-hidden="true" />}
              </>}
              {ve(o)}
            </section>);
        })}
      </div>
      <span className="sr" aria-live="polite">{bao}</span>
    </>
  );
}
