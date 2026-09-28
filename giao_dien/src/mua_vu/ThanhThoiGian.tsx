// Thanh thời gian của màn Mùa vụ: mỗi nấc = MỘT ngày; vùng tô = cửa sổ N ngày kết thúc ở
// nấc đó. Nền: doanh thu thuần theo ngày (mọi mã) + dải bốn mùa + vạch đầu tháng.
// <input type="range"> gốc lo bàn phím ← → / Home / End và trình đọc màn hình; Shift+← →
// nhảy 7 ngày. ▶ chạy 1 ngày / 80 ms, bấm lại dừng, tới cuối thì dừng.
import { useEffect, useMemo, useRef, useState } from "react";
import { useRong } from "../chung/hooks";
import { ngay } from "../dinh_dang";
import { ngayCua } from "./du_lieu";

const CAO = 56;
const MUA: Record<number, string> = {
  3: "xuan", 4: "xuan", 5: "xuan", 6: "he", 7: "he", 8: "he",
  9: "thu", 10: "thu", 11: "thu", 12: "dong", 1: "dong", 2: "dong",
};

export function ThanhThoiGian({ so_ngay, ngay_dau, tong_ngay, b, n, datB }: {
  so_ngay: number; ngay_dau: string; tong_ngay: Float64Array; b: number; n: number; datB: (b: number) => void;
}) {
  const [ref, rong] = useRong<HTMLDivElement>();
  const [chay, datChay] = useState(false);
  const bRef = useRef(b); bRef.current = b;

  useEffect(() => {
    if (!chay) return;
    const t = setInterval(() => {
      if (bRef.current >= so_ngay - 1) { datChay(false); return; }
      datB(bRef.current + 1);
    }, 80);
    return () => clearInterval(t);
  }, [chay, so_ngay, datB]);

  const hinh = useMemo(() => {
    if (!rong || !so_ngay) return null;
    const x = (d: number) => (d / Math.max(1, so_ngay - 1)) * rong;
    const max = Math.max(1, ...Array.from(tong_ngay));
    const duong = Array.from(tong_ngay, (v, d) =>
      `${x(d).toFixed(1)},${(CAO - 4 - (Math.max(0, v) / max) * (CAO - 10)).toFixed(1)}`).join(" ");
    const mua: { x: number; w: number; ten: string }[] = [];
    const thang: { x: number; nhan: string }[] = [];
    let dau = 0, ten = "";
    for (let d = 0; d < so_ngay; d++) {
      const [yy, mm, dd] = ngayCua(ngay_dau, d).split("-").map(Number);
      const t = MUA[mm];
      if (t !== ten) { if (ten) mua.push({ x: x(dau), w: x(d) - x(dau), ten }); dau = d; ten = t; }
      if (dd === 1) thang.push({ x: x(d), nhan: mm === 1 ? `${yy}` : `${mm}` });
    }
    mua.push({ x: x(dau), w: x(so_ngay - 1) - x(dau), ten });
    return { x, duong, mua, thang };
  }, [rong, so_ngay, tong_ngay, ngay_dau]);

  const buoc = (k: number) => datB(Math.min(so_ngay - 1, Math.max(0, b + k)));

  return (
    <div className="mv-thanh">
      <div className="mv-nut">
        <button type="button" onClick={() => buoc(-1)} aria-label="Lùi một ngày">◀</button>
        <button type="button" onClick={() => { if (b >= so_ngay - 1) datB(0); datChay(c => !c); }}
                aria-label={chay ? "Dừng" : "Chạy"}>{chay ? "❚❚" : "▶"}</button>
        <button type="button" onClick={() => buoc(1)} aria-label="Tiến một ngày">▶</button>
      </div>
      <div className="mv-truot" ref={ref}>
        {hinh && (
          <svg width={rong} height={CAO} aria-hidden="true" focusable="false">
            {hinh.mua.map((m, k) => <rect key={k} x={m.x} y={0} width={m.w} height={CAO} className={"mv-mua-" + m.ten} />)}
            <rect x={hinh.x(Math.max(0, b - n + 1))} y={0} width={Math.max(2, hinh.x(b) - hinh.x(Math.max(0, b - n + 1)))}
                  height={CAO} className="mv-cua-so" />
            <polyline points={hinh.duong} fill="none" className="mv-duong-ngay" />
            {hinh.thang.map((t, k) => (
              <g key={k}><line x1={t.x} x2={t.x} y1={CAO - 8} y2={CAO} className="mv-vach" />
                <text x={t.x + 2} y={10} className="mv-nhan-thang">{t.nhan}</text></g>
            ))}
          </svg>
        )}
        <input type="range" min={0} max={Math.max(0, so_ngay - 1)} value={b}
               aria-label="Ngày cuối cửa sổ" aria-valuetext={ngay(ngayCua(ngay_dau, b))}
               onChange={e => { datChay(false); datB(Number(e.target.value)); }}
               onKeyDown={e => {
                 if (e.shiftKey && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
                   e.preventDefault(); datChay(false); buoc(e.key === "ArrowLeft" ? -7 : 7);
                 }
               }} />
      </div>
    </div>
  );
}
