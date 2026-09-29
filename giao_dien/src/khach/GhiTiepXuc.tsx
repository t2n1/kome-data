// Biểu mẫu ghi MỘT lần tiếp xúc (app.nhat_ky_tiep_xuc, chỉ thêm — 030). Dùng
// chung cho hồ sơ 360° và thẻ khách ở Cần liên hệ. Từ vựng kiểu / kết quả do
// máy chủ gửi (kome.lien_he.KIEU / KET_QUA) — giao diện không tự chép.
// Đợt 2 (tin hiện trường): gõ `@` mở danh sách gợi ý (đối thủ trước, rồi hàng = nhóm so sánh);
// mỗi thẻ hàng có một dòng giá khách kể tuỳ chọn. Logic thẻ ở nhac.ts. Không có `@` → y như cũ.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import { gui, lay } from "../api";
import { DON_VI } from "../doi_thu/kieu";
import {
  chenThe, DON_VI_CHON, doLai, dsGoiY, ghepCap, locGoiY, thanGhi, tuDangGo,
  type DongGia, type GoiYApi, type MucGoiY, type The,
} from "./nhac";

export function GhiTiepXuc({ ma, kieu_tx, ket_qua_tx, lam_moi, id, gon = false, xong }: {
  ma: string; kieu_tx: Record<string, [string, string]>; ket_qua_tx: Record<string, [string, string]>;
  lam_moi: unknown[][]; id?: string; gon?: boolean; xong?: () => void;
}) {
  const qc = useQueryClient();
  const [kieu, datKieu] = useState(Object.keys(kieu_tx)[0] ?? "goi");
  const [kq, datKq] = useState("binh");
  const [noi, datNoi] = useState(""), [hen, datHen] = useState("");
  const [loi, datLoi] = useState(""), [dang, datDang] = useState(false);
  // Thẻ @ đã chọn, dòng giá theo khoá nhóm, con trỏ, gợi ý đang sáng, `@` đã đóng bằng Esc, cảnh báo sau khi ghi.
  const [the, datThe] = useState<The[]>([]);
  const [dongGia, datDongGia] = useState<Record<string, DongGia>>({});
  const [conTro, datConTro] = useState(0);
  const [sang, datSang] = useState(0);
  const [daDong, datDaDong] = useState<number | null>(null);
  const [canhBao, datCanhBao] = useState<string[]>([]);
  const o = useRef<HTMLTextAreaElement>(null);
  const choConTro = useRef<number | null>(null);
  // Làm mới dữ liệu bị HOÃN khi có cảnh báo: ở /lien-he `lam_moi` gồm ["lien-he"], làm mới ngay là khách vừa liên
  // hệ bị tạm ẩn, thẻ (và form này) tháo ra trước khi cảnh báo kịp hiện. Chạy khi bấm "Đã hiểu", lần ghi sau, hay tháo form.
  const hoan = useRef<(() => Promise<unknown>) | null>(null);
  const chayHoan = () => { const f = hoan.current; hoan.current = null; return f ? f() : Promise.resolve(); };
  useEffect(() => () => { void chayHoan(); }, []);
  const uid = useId(), idDs = `${uid}-goi-y`;

  const dangGo = tuDangGo(noi, conTro, the);
  const mo = !!dangGo && daDong !== dangGo.dau;
  // Chỉ tải danh sách gợi ý khi có người gõ `@` lần đầu — không có `@` thì không thêm lượt gọi nào.
  const gy = useQuery({ queryKey: ["doi-thu", "goi-y-nhac"], enabled: !!dangGo, staleTime: 5 * 60_000,
    queryFn: () => lay<GoiYApi>("/api/doi-thu/goi-y-nhac") });
  const tatCa = useMemo(() => (gy.data ? dsGoiY(gy.data) : []), [gy.data]);
  const goiY = mo && dangGo ? locGoiY(tatCa, dangGo.tu) : [];
  const iSang = goiY.length ? Math.min(sang, goiY.length - 1) : -1;
  const cap = ghepCap(the);
  const dsDt = [...new Map(the.filter(t => t.loai === "doi_thu").map(t => [t.khoa, t])).values()];

  useLayoutEffect(() => {
    const c = choConTro.current;
    if (c == null || !o.current) return;
    choConTro.current = null;
    o.current.focus(); o.current.setSelectionRange(c, c);
  }, [noi]);

  const doiNoi = (moi: string, c: number) => {
    datThe(doLai(noi, moi, the)); datNoi(moi); datConTro(c); datSang(0);
  };
  const chon = (m: MucGoiY) => {
    if (!dangGo) return;
    const r = chenThe(noi, dangGo.dau, conTro, m);
    datThe([...doLai(noi, r.text, the), r.the].sort((a, b) => a.vi_tri_dau - b.vi_tri_dau));
    datNoi(r.text); datConTro(r.con_tro); datSang(0);
    choConTro.current = r.con_tro;
  };
  const phim = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Đang soạn bằng bộ gõ (IME tiếng Nhật…): phím mũi tên / Enter thuộc về bộ gõ, không thuộc danh sách gợi ý.
    if (!mo || !dangGo || e.nativeEvent.isComposing) return;
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); datDaDong(dangGo.dau); return; }
    if (!goiY.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); datSang((iSang + 1) % goiY.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); datSang((iSang - 1 + goiY.length) % goiY.length); }
    else if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); chon(goiY[iSang]); }
  };
  const suaGia = (khoa: string, moi: Partial<DongGia>) =>
    datDongGia(d => ({ ...d, [khoa]: { ...(d[khoa] ?? { gia: "", don_vi: "kg" }), ...moi } }));

  const them = async (e: React.FormEvent) => {
    e.preventDefault(); datLoi(""); datCanhBao([]); void chayHoan();
    const { than, loi: loiGia } = thanGhi(kieu, kq, noi, hen, the, dongGia);
    if (!than) { datLoi(loiGia ?? ""); return; }
    datDang(true);
    try {
      const r = await gui<{ ok: boolean; id?: number; canh_bao?: string[] }>(
        `/api/khach-hang/${encodeURIComponent(ma)}/tiep-xuc`, than);
      const coThe = the.length > 0;
      datNoi(""); datHen(""); datThe([]); datDongGia({}); datDaDong(null);
      const k = [...lam_moi, ...(coThe ? [["kh-doi-thu", ma], ["doi-thu"]] : [])];
      const lamMoi = () => Promise.all(k.map(q => qc.invalidateQueries({ queryKey: q })));
      // Cảnh báo (giá lệch xa trung vị…) không chặn ghi — nhưng phải đọc được trước khi form đóng / thẻ bị ẩn:
      // hiện cảnh báo TRƯỚC, hoãn làm mới + xong() tới khi bấm "Đã hiểu". Không cảnh báo -> y như cũ.
      if (r.canh_bao?.length) { hoan.current = lamMoi; datCanhBao(r.canh_bao); }
      else { await lamMoi(); xong?.(); }
    } catch (x) { datLoi((x as Error).message); } finally { datDang(false); }
  };
  return (
    <form className={"hs-form" + (gon ? " gon" : "")} onSubmit={them}>
      <div className="hs-form-chip" role="radiogroup" aria-label="Kiểu tiếp xúc">
        {Object.entries(kieu_tx).map(([m, [ic, nhan]]) => (
          <button key={m} type="button" className="chip" role="radio" aria-checked={kieu === m} aria-pressed={kieu === m}
            onClick={() => datKieu(m)}>{ic} {gon ? "" : nhan}</button>))}
        <span className="hs-form-vach" aria-hidden="true" />
        {Object.entries(ket_qua_tx).map(([m, [nhan]]) => (
          <button key={m} type="button" className="chip" role="radio" aria-checked={kq === m} aria-pressed={kq === m}
            onClick={() => datKq(m)}>{nhan}</button>))}
      </div>
      <textarea ref={o} id={id} rows={2} placeholder="Nội dung trao đổi… (gõ @ để gắn đối thủ / hàng)" value={noi}
        onChange={e => doiNoi(e.target.value, e.target.selectionStart ?? e.target.value.length)}
        onSelect={e => datConTro(e.currentTarget.selectionStart ?? 0)}
        onKeyDown={phim} onBlur={() => dangGo && datDaDong(dangGo.dau)} onFocus={() => datDaDong(null)}
        maxLength={2000} aria-label="Nội dung trao đổi" aria-autocomplete="list"
        aria-controls={mo && goiY.length ? idDs : undefined}
        aria-activedescendant={mo && iSang >= 0 ? `${idDs}-${iSang}` : undefined} />
      {mo && (goiY.length ? (
        <ul className="hs-nhac-ds" role="listbox" id={idDs} aria-label="Gợi ý thẻ @">
          {goiY.map((m, i) => (
            <li key={m.loai + m.khoa} id={`${idDs}-${i}`} role="option" aria-selected={i === iSang}
              className={i === iSang ? "sang" : undefined}
              onMouseDown={e => { e.preventDefault(); chon(m); }} onMouseEnter={() => datSang(i)}>
              <span className="hs-nhac-loai" aria-hidden="true">{m.loai === "doi_thu" ? "Đối thủ" : "Hàng"}</span>
              <b>@{m.nhan}</b> <span className="phu">{m.phu}</span>
            </li>))}
        </ul>)
        : <p className="phu hs-nhac-trong" role="status">
            {gy.isLoading ? "Đang tải gợi ý…" : gy.error ? "Không tải được gợi ý." : "Không khớp đối thủ / hàng nào."}</p>)}
      {cap.length > 0 && (
        <div className="hs-nhac-gia">
          {cap.map(c => {
            const d = dongGia[c.nhom.khoa] ?? { gia: "", don_vi: "kg" };
            const dt = d.doi_thu && dsDt.some(t => t.khoa === d.doi_thu) ? d.doi_thu : c.doi_thu ?? "";
            const ten = "@" + c.nhom.nhan;
            return (
              <div className="hs-nhac-dong" key={c.nhom.khoa}>
                <span className="hs-nhac-ten" title={ten}>{ten}</span>
                <label>· đối thủ <select value={dt} aria-label={`Đối thủ của ${ten}`}
                  onChange={e => suaGia(c.nhom.khoa, { doi_thu: e.target.value })}>
                  <option value="">—</option>
                  {dsDt.map(t => <option key={t.khoa} value={t.khoa}>{t.nhan}</option>)}</select></label>
                <label>· giá <input inputMode="decimal" size={7} value={d.gia} placeholder="tuỳ chọn"
                  aria-label={`Giá khách kể của ${ten}`} onChange={e => suaGia(c.nhom.khoa, { gia: e.target.value })} /> ¥</label>
                <label>/ <select value={d.don_vi} aria-label={`Đơn vị giá của ${ten}`}
                  onChange={e => suaGia(c.nhom.khoa, { don_vi: e.target.value })}>
                  {DON_VI_CHON.map(v => <option key={v} value={v}>{DON_VI[v]}</option>)}</select></label>
              </div>);
          })}
        </div>)}
      <div className="hs-form-cuoi">
        <label className="phu">Hẹn gọi lại <input type="date" value={hen} onChange={e => datHen(e.target.value)} /></label>
        <button type="submit" className="nut-chinh" disabled={!noi.trim() || dang}>{dang ? "Đang ghi…" : "Thêm"}</button>
      </div>
      {loi && <p className="khoi-loi" role="alert">{loi}</p>}
      {canhBao.length > 0 && (
        <div className="hs-nhac-canh" role="status">
          <p>Đã ghi. Cần xem lại:</p>
          <ul>{canhBao.map((c, i) => <li key={i}>{c}</li>)}</ul>
          <button type="button" className="nut-nho" onClick={async () => { datCanhBao([]); await chayHoan(); xong?.(); }}>Đã hiểu</button>
        </div>)}
    </form>
  );
}
