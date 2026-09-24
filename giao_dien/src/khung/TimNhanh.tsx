import { giuKhoang } from "./khoang";
// Bảng lệnh ⌘K / Ctrl+K — nhảy tới bất kỳ màn nào có thật bằng bàn phím.
import { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "./icon";
import { nhomDieuHuong } from "./muc";

function bo_dau(s: string) {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
}

export function TimNhanh({ dong }: { dong: () => void }) {
  const [tu, datTu] = useState("");
  const [chon, datChon] = useState(0);
  const o = useRef<HTMLInputElement>(null);
  useEffect(() => { o.current?.focus(); }, []);

  const ds = useMemo(() => {
    const tat_ca = nhomDieuHuong().flatMap(g => g.muc.filter(m => m.url).map(m => ({ ...m, nhom: g.ten })));
    const q = bo_dau(tu.trim());
    return q ? tat_ca.filter(m => bo_dau(m.nhan + " " + m.nhom).includes(q)) : tat_ca;
  }, [tu]);

  const di = (i: number) => { const m = ds[i]; if (m?.url) location.href = giuKhoang(m.url); };

  return (
    <div className="lop-phu" onMouseDown={dong}>
      <div className="tim-hop" role="dialog" aria-modal="true" aria-label="Tìm nhanh" onMouseDown={e => e.stopPropagation()}>
        <div className="tim-o">
          <Icon ten="tim" />
          <input ref={o} value={tu} placeholder="Nhảy tới màn hình…" aria-label="Tìm màn hình"
            onChange={e => { datTu(e.target.value); datChon(0); }}
            onKeyDown={e => {
              if (e.key === "ArrowDown") { e.preventDefault(); datChon(c => Math.min(c + 1, ds.length - 1)); }
              else if (e.key === "ArrowUp") { e.preventDefault(); datChon(c => Math.max(c - 1, 0)); }
              else if (e.key === "Enter") di(chon);
            }} />
          <kbd>Esc</kbd>
        </div>
        <ul className="tim-ds" role="listbox">
          {ds.map((m, i) => (
            <li key={m.ma} role="option" aria-selected={i === chon} className={i === chon ? "chon" : ""}
                onMouseEnter={() => datChon(i)} onClick={() => di(i)}>
              <Icon ten={m.icon} /><span>{m.nhan}</span><em>{m.nhom}</em>
            </li>
          ))}
          {!ds.length && <li className="trong">Không có màn nào khớp.</li>}
        </ul>
      </div>
    </div>
  );
}
