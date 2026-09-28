// Thanh tab các bảng Tổng quan của MỘT người (056) — thay dải "XEM THEO VAI TRÒ"
// (vai trò nay là MẪU khi tạo bảng, xem BangMoi.tsx). Không kéo tab: lẫn với kéo
// khối ngay bên dưới, và không dùng được bằng bàn phím — đổi thứ tự bằng mục
// "Dời trái / Dời phải" trong ⋯.
import { useEffect, useRef, useState } from "react";
import { gui } from "../api";
import type { BangTQ } from "../khoi_dau";

const LY_DO = "Máy này chưa bật đăng nhập — không lưu được bảng.";

export function ThanhBang({ ds, hien, sua_duoc, chuyen, damBaoCo, datDs, sauXoa, datLai, moBangMoi }: {
  ds: BangTQ[]; hien: BangTQ; sua_duoc: boolean;
  chuyen: (id: number | null) => void;
  damBaoCo: () => Promise<BangTQ>;               // bảng ảo -> dòng thật trước mọi thao tác
  datDs: (f: (d: BangTQ[]) => BangTQ[]) => void;
  sauXoa: (id: number) => void;                  // hiện bảng máy chủ chọn sau khi xoá
  datLai: () => void; moBangMoi: () => void;
}) {
  const [menu, datMenu] = useState(false);
  const [sua, datSua] = useState<string | null>(null);
  const [loi, datLoi] = useState("");
  const vung = useRef<HTMLDivElement>(null);
  const i = ds.findIndex(b => b.id === hien.id);

  useEffect(() => {
    if (!menu) return;
    const ngoai = (e: MouseEvent) => { if (!vung.current?.contains(e.target as Node)) datMenu(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") datMenu(false); };
    document.addEventListener("mousedown", ngoai);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", ngoai); document.removeEventListener("keydown", esc); };
  }, [menu]);

  const lam = async (f: () => Promise<void>) => {
    datLoi("");
    try { await f(); } catch (e: unknown) { datLoi(e instanceof Error ? e.message : "Không làm được — thử lại sau."); }
  };
  const doiTen = (ten: string) => lam(async () => {
    if (!ten.trim() || ten.trim() === hien.ten) { datSua(null); return; }
    const b = await damBaoCo();
    const r = await gui<{ bang: BangTQ }>(`/tong-quan/bang/${b.id}/ten`, { ten });
    datDs(d => d.map(x => x.id === b.id ? { ...x, ten: r.bang.ten } : x));
    datSua(null);
  });
  const doi = (buoc: number) => lam(async () => {
    datMenu(false);
    const b = await damBaoCo();
    const moi = [...ds.filter(x => x.id !== null)].map(x => x.id === b.id ? { ...x, ...b, bo_cuc: x.bo_cuc } : x);
    const j = moi.findIndex(x => x.id === b.id), k = j + buoc;
    if (j < 0 || k < 0 || k >= moi.length) return;
    [moi[j], moi[k]] = [moi[k], moi[j]];
    await gui("/tong-quan/bang/thu-tu", moi.map(x => x.id));
    datDs(() => moi);
  });
  const xoa = () => lam(async () => {
    datMenu(false);
    if (!window.confirm(`Xoá bảng "${hien.ten}"? Không hoàn tác được.`)) return;
    const b = await damBaoCo();
    const r = await gui<{ bang_hien: number }>(`/tong-quan/bang/${b.id}/xoa`, null);
    datDs(d => d.filter(x => x.id !== b.id));
    sauXoa(r.bang_hien);
  });

  return (
    <div className="thanh-bang">
      <div role="tablist" aria-label="Bảng Tổng quan của bạn" className="tab-bang">
        {ds.map(b => b.id === hien.id && sua !== null
          ? <input key={String(b.id)} className="o-ten-bang" autoFocus maxLength={40} value={sua} aria-label="Tên bảng"
              onChange={e => datSua(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") void doiTen(sua); if (e.key === "Escape") datSua(null); }}
              onBlur={() => void doiTen(sua)} />
          : <button key={String(b.id)} type="button" role="tab" aria-selected={b.id === hien.id} className="chip tab-mot"
              onClick={() => b.id !== hien.id && chuyen(b.id)}
              onDoubleClick={() => sua_duoc && b.id === hien.id && datSua(hien.ten)}>{b.ten}</button>)}
      </div>
      <div className="menu-bang" ref={vung}>
        <button type="button" className="nut-nho" aria-haspopup="menu" aria-expanded={menu} aria-label={`Thao tác với bảng "${hien.ten}"`}
          disabled={!sua_duoc} title={sua_duoc ? "Thao tác với bảng này" : LY_DO} onClick={() => datMenu(m => !m)}>⋯</button>
        {menu && (
          <div role="menu" className="menu-noi">
            <button role="menuitem" type="button" onClick={() => { datMenu(false); datSua(hien.ten); }}>Đổi tên</button>
            <button role="menuitem" type="button" onClick={() => { datMenu(false); moBangMoi(); }}>Nhân bản…</button>
            <button role="menuitem" type="button" disabled={i <= 0} onClick={() => void doi(-1)}>← Dời trái</button>
            <button role="menuitem" type="button" disabled={i >= ds.length - 1} onClick={() => void doi(1)}>Dời phải →</button>
            <button role="menuitem" type="button" onClick={() => { datMenu(false); datLai(); }}>Đặt lại bố cục</button>
            <button role="menuitem" type="button" className="giam" disabled={ds.length <= 1}
              title={ds.length <= 1 ? "Không xoá được bảng cuối cùng." : undefined} onClick={() => void xoa()}>Xoá bảng…</button>
          </div>)}
      </div>
      <button type="button" className="nut-nho" disabled={!sua_duoc} title={sua_duoc ? undefined : LY_DO}
        onClick={moBangMoi}>＋ Bảng mới</button>
      {loi && <span className="giam phu" role="alert">{loi}</span>}
    </div>
  );
}
