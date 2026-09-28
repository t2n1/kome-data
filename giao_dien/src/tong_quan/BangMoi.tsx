// Hộp "Bảng mới" (056) — chọn xuất phát: chép bảng đang xem · một vai trò
// (bo_cuc.VAI_TRO, đọc từ KD.danh_muc — giao diện không tự chép danh mục) · đầy
// đủ. Tên gợi ý theo lựa chọn, tự thêm " (2)" khi trùng tên đã có.
import { useEffect, useRef, useState } from "react";
import { KD, type BangTQ } from "../khoi_dau";

export function BangMoi({ hien, ds, dong, tao }: {
  hien: BangTQ; ds: BangTQ[]; dong: () => void;
  tao: (ten: string, tu: string) => Promise<void>;   // tu: "chep" | "vai:<mã>" | "mac_dinh"
}) {
  const LUA_CHON = [
    { tu: "chep", nhan: `Chép "${hien.ten}"`, ten: `${hien.ten} (bản chép)` },
    ...KD.danh_muc.vai_tro.map(v => ({ tu: `vai:${v.id}`, nhan: `Vai trò: ${v.nhan}`, ten: v.nhan })),
    { tu: "mac_dinh", nhan: "Đầy đủ (mọi chức năng)", ten: "Bảng mới" },
  ];
  const khongTrung = (t: string) => {
    const co = new Set(ds.map(b => b.ten.trim().toLowerCase()));
    let x = t.slice(0, 40), n = 2;
    while (co.has(x.toLowerCase())) x = `${t.slice(0, 35)} (${n++})`;
    return x;
  };
  const [tu, datTu] = useState(LUA_CHON[0].tu);
  const [ten, datTen] = useState(() => khongTrung(LUA_CHON[0].ten));
  const [loi, datLoi] = useState("");
  const [dang, datDang] = useState(false);
  const o = useRef<HTMLInputElement>(null);
  useEffect(() => {
    o.current?.select();
    const f = (e: KeyboardEvent) => e.key === "Escape" && dong();
    document.addEventListener("keydown", f);
    return () => document.removeEventListener("keydown", f);
  }, [dong]);

  return (
    <div className="lop-phu giua" onMouseDown={dong}>
      <form className="bang-them hop-bang-moi" role="dialog" aria-modal="true" aria-labelledby="bm-td"
        onMouseDown={e => e.stopPropagation()}
        onSubmit={async e => {
          e.preventDefault(); datDang(true); datLoi("");
          try { await tao(ten.trim(), tu); }
          catch (x: unknown) { datLoi(x instanceof Error ? x.message : "Không tạo được bảng."); }
          finally { datDang(false); }
        }}>
        <div className="bang-them-dau"><strong id="bm-td">Bảng mới</strong>
          <button type="button" className="nut-dong" aria-label="Đóng" onClick={dong}>✕</button></div>
        <fieldset>
          <legend className="nhan-nho">BẮT ĐẦU TỪ</legend>
          {LUA_CHON.map(l => (
            <label key={l.tu} className="lua-chon">
              <input type="radio" name="tu" checked={tu === l.tu} onChange={() => { datTu(l.tu); datTen(khongTrung(l.ten)); }} />
              {l.nhan}
            </label>))}
        </fieldset>
        <label className="nhan-nho" htmlFor="bm-ten">TÊN BẢNG</label>
        <input id="bm-ten" ref={o} className="o-tim-nho" value={ten} maxLength={40} required onChange={e => datTen(e.target.value)} />
        {loi && <div className="giam phu" role="alert">{loi}</div>}
        <div className="nut-hop">
          <button type="button" className="nut-nho" onClick={dong}>Huỷ</button>
          <button type="submit" className="nut-chinh" disabled={dang || !ten.trim()}>{dang ? "Đang tạo…" : "Tạo bảng"}</button>
        </div>
      </form>
    </div>
  );
}
