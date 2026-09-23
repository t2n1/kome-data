// Lưới 3 cột kéo thả + đổi cỡ góc — chép Dashboard.dc.html (grid-auto-flow:
// dense, hàng tối thiểu 150px, rộng 1–3 cột, cao 1–4 hàng). Khác gói thiết
// kế: bố cục LƯU MÁY CHỦ theo tài khoản (POST /tong-quan/bo-cuc, migration
// 034) chứ không localStorage; kéo từ ĐẦU khối (chữ trong khối vẫn bôi đen /
// bấm liên kết được); có nút ⠿ cho bàn phím.
import { useRef, useState, type ReactNode } from "react";
import type { OBoCuc } from "../khoi_dau";

const RONG = 3, CAO = 4, HANG = 150;

export function Luoi({ bo_cuc, datBoCuc, sua_duoc, ve, nhan }: {
  bo_cuc: OBoCuc[];
  datBoCuc: (b: OBoCuc[]) => void;
  sua_duoc: boolean;
  ve: (id: string) => ReactNode;
  nhan: (id: string) => string;
}) {
  const luoi = useRef<HTMLDivElement>(null);
  const [keo, datKeo] = useState<string | null>(null);
  const [dich, datDich] = useState<{ id: string; truoc: boolean } | null>(null);
  const [bao, datBao] = useState("");
  // Kéo CHỈ khi bấm xuống ở đầu khối. Phải quyết định trong dragstart (đồng
  // bộ), không qua state: trình duyệt chốt "có kéo không" trước khi React kịp
  // vẽ lại, nên bật `draggable` bằng state là không bao giờ kéo được.
  const tuDau = useRef(false);
  // Khối đang kéo — ref cho logic (cập nhật NGAY trong dragstart; dragover đầu
  // tiên có thể tới trước khi state kịp vẽ lại), state chỉ để tô mờ.
  const dangKeo = useRef<string | null>(null);
  const dichRef = useRef<{ id: string; truoc: boolean } | null>(null);

  const chuyen = (id: string, toi: string, truoc: boolean) => {
    if (id === toi) return;
    const ds = bo_cuc.filter(o => o.id !== id);
    const i = ds.findIndex(o => o.id === toi);
    ds.splice(truoc ? i : i + 1, 0, bo_cuc.find(o => o.id === id)!);
    datBoCuc(ds);
  };
  const datCo = (id: string, rong: number, cao: number) =>
    datBoCuc(bo_cuc.map(o => o.id === id ? { ...o, rong: Math.max(1, Math.min(RONG, rong)), cao: Math.max(1, Math.min(CAO, cao)) } : o));

  const batDauCo = (id: string, e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault(); e.stopPropagation();
    const the = e.currentTarget.parentElement!;
    const kieu = getComputedStyle(luoi.current!);
    const khe = parseFloat(kieu.columnGap) || 12;
    const oRong = (luoi.current!.clientWidth - (RONG - 1) * khe) / RONG + khe;
    const oCao = HANG + (parseFloat(kieu.rowGap) || 12);
    const x0 = e.clientX, y0 = e.clientY, w0 = the.offsetWidth, h0 = the.offsetHeight;
    const goc = e.currentTarget;
    goc.setPointerCapture(e.pointerId);
    let r = 0, c = 0;
    const di = (ev: PointerEvent) => {
      r = Math.round((w0 + ev.clientX - x0) / oRong); c = Math.round((h0 + ev.clientY - y0) / oCao);
      the.style.gridColumn = `span ${Math.max(1, Math.min(RONG, r))}`;
      the.style.gridRow = `span ${Math.max(1, Math.min(CAO, c))}`;
    };
    const nha = () => {
      goc.removeEventListener("pointermove", di); goc.removeEventListener("pointerup", nha);
      if (r && c) datCo(id, r, c);
    };
    goc.addEventListener("pointermove", di); goc.addEventListener("pointerup", nha);
  };

  const phim = (o: OBoCuc, e: React.KeyboardEvent) => {
    const hien = bo_cuc.filter(x => !x.an), i = hien.findIndex(x => x.id === o.id);
    if (e.shiftKey && e.key.startsWith("Arrow")) {
      e.preventDefault();
      const r = o.rong + (e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0);
      const c = o.cao + (e.key === "ArrowDown" ? 1 : e.key === "ArrowUp" ? -1 : 0);
      datCo(o.id, r, c); datBao(`${nhan(o.id)}: rộng ${Math.max(1, Math.min(RONG, r))} cột, cao ${Math.max(1, Math.min(CAO, c))} hàng.`);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp" || e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      const lui = e.key === "ArrowLeft" || e.key === "ArrowUp", j = lui ? i - 1 : i + 1;
      if (j < 0 || j >= hien.length) return;
      chuyen(o.id, hien[j].id, lui);
      datBao(`${nhan(o.id)} ở vị trí ${j + 1} trên ${hien.length}.`);
      requestAnimationFrame(() => (document.querySelector(`[data-khoi="${o.id}"] .khoi-tay`) as HTMLElement | null)?.focus());
    }
  };

  return (
    <>
      <div className="luoi-tq" ref={luoi}>
        {bo_cuc.filter(o => !o.an).map(o => (
          <section key={o.id} data-khoi={o.id} aria-label={nhan(o.id)}
            className={"o-luoi" + (keo === o.id ? " dang-keo" : "") + (dich?.id === o.id ? (dich.truoc ? " dich-truoc" : " dich-sau") : "")}
            style={{ gridColumn: `span ${o.rong}`, gridRow: `span ${o.cao}` }}
            draggable={sua_duoc}
            onPointerDown={e => { const t = e.target as HTMLElement; tuDau.current = !!t.closest("[data-keo]") && !t.closest("a,button,input"); }}
            onDragStart={e => {
              if (!tuDau.current) { e.preventDefault(); return; }
              dangKeo.current = o.id; datKeo(o.id);
              e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", o.id);
            }}
            onDragEnter={e => { if (dangKeo.current && dangKeo.current !== o.id) e.preventDefault(); }}
            onDragOver={e => {
              if (!dangKeo.current || dangKeo.current === o.id) return;
              e.preventDefault();
              const r = e.currentTarget.getBoundingClientRect();
              const d = { id: o.id, truoc: e.clientX < r.left + r.width / 2 };
              dichRef.current = d;
              if (dich?.id !== d.id || dich.truoc !== d.truoc) datDich(d);
            }}
            onDrop={e => {
              e.preventDefault();
              const k = dangKeo.current, d = dichRef.current;
              if (k && d) chuyen(k, d.id, d.truoc);
              dangKeo.current = null; dichRef.current = null; datDich(null); datKeo(null);
            }}
            onDragEnd={() => { dangKeo.current = null; dichRef.current = null; datKeo(null); datDich(null); }}>
            {sua_duoc && <>
              <button type="button" className="khoi-tay" aria-label={`Sắp xếp khối ${nhan(o.id)} — mũi tên đổi chỗ, Shift + mũi tên đổi cỡ`}
                title="Kéo đầu khối để sắp xếp" onKeyDown={e => phim(o, e)}>⠿</button>
              <button type="button" className="khoi-an" aria-label={`Ẩn khối ${nhan(o.id)}`} title="Ẩn khối"
                onClick={() => { datBoCuc(bo_cuc.map(x => x.id === o.id ? { ...x, an: true } : x)); datBao(`Đã ẩn ${nhan(o.id)} — hiện lại ở "Thêm chức năng".`); }}>✕</button>
              <div className="khoi-co" title="Kéo để đổi kích thước" aria-hidden="true" onPointerDown={e => batDauCo(o.id, e)} />
            </>}
            {ve(o.id)}
          </section>
        ))}
      </div>
      <span className="sr" aria-live="polite">{bao}</span>
    </>
  );
}
