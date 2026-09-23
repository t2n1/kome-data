// Biểu mẫu ghi MỘT lần tiếp xúc (app.nhat_ky_tiep_xuc, chỉ thêm — 030). Dùng
// chung cho hồ sơ 360° và thẻ khách ở Cần liên hệ. Từ vựng kiểu / kết quả do
// máy chủ gửi (kome.lien_he.KIEU / KET_QUA) — giao diện không tự chép.
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { gui } from "../api";

export function GhiTiepXuc({ ma, kieu_tx, ket_qua_tx, lam_moi, id, gon = false, xong }: {
  ma: string; kieu_tx: Record<string, [string, string]>; ket_qua_tx: Record<string, [string, string]>;
  lam_moi: unknown[][]; id?: string; gon?: boolean; xong?: () => void;
}) {
  const qc = useQueryClient();
  const [kieu, datKieu] = useState(Object.keys(kieu_tx)[0] ?? "goi");
  const [kq, datKq] = useState("binh");
  const [noi, datNoi] = useState(""), [hen, datHen] = useState("");
  const [loi, datLoi] = useState(""), [dang, datDang] = useState(false);
  const them = async (e: React.FormEvent) => {
    e.preventDefault(); datLoi(""); datDang(true);
    try {
      await gui(`/api/khach-hang/${encodeURIComponent(ma)}/tiep-xuc`, { kieu, ket_qua: kq, noi_dung: noi, hen_lai: hen });
      datNoi(""); datHen("");
      await Promise.all(lam_moi.map(k => qc.invalidateQueries({ queryKey: k })));
      xong?.();
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
      <textarea id={id} rows={2} placeholder="Nội dung trao đổi…" value={noi} onChange={e => datNoi(e.target.value)}
        maxLength={2000} aria-label="Nội dung trao đổi" />
      <div className="hs-form-cuoi">
        <label className="phu">Hẹn gọi lại <input type="date" value={hen} onChange={e => datHen(e.target.value)} /></label>
        <button type="submit" className="nut-chinh" disabled={!noi.trim() || dang}>{dang ? "Đang ghi…" : "Thêm"}</button>
      </div>
      {loi && <p className="khoi-loi" role="alert">{loi}</p>}
    </form>
  );
}
