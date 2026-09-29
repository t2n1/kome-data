// Tab "Nhóm & quy cách" (đặc tả Đợt 1b §5): nhóm so sánh có tên (gộp nhiều mã KOME để so chung) và quy cách KOME
// (kg/gói · gói/thùng · kg/thùng — có kg thì giá KOME mới quy được về ¥/kg). Ghi qua /api/doi-thu/{nhom,nhom/them-ma,nhom/bo-ma,quy-cach};
// máy chủ kiểm mã và số, lỗi 400 hiện nguyên câu. Không tính chỉ số nào ở đây.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { gui, lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { so } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { NhomQuyCach, QuyCach } from "./kieu";
import { boDau, chuaCoKg, tachMa } from "./loc";

type Sua = { kg_moi_goi: string; goi_moi_thung: string; kg_moi_thung: string };
const chuoi = (v: number | null) => (v == null ? "" : String(v));
const cuaDong = (q: QuyCach): Sua => ({ kg_moi_goi: chuoi(q.kg_moi_goi), goi_moi_thung: chuoi(q.goi_moi_thung), kg_moi_thung: chuoi(q.kg_moi_thung) });

export function TabNhomQuyCach() {
  const kx = chuoiKhoang(useKhoang());
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["doi-thu", "nhom-quy-cach", kx],
    queryFn: () => lay<NhomQuyCach>(`/api/doi-thu/nhom-quy-cach${kx ? "?" + kx : ""}`) });
  const d = q.data;
  const [loi, datLoi] = useState<string | null>(null);      // lỗi của khối Nhóm
  const [loiQc, datLoiQc] = useState<string | null>(null);  // lỗi của khối Quy cách (lưu một dòng)
  const [dang_gui, datDangGui] = useState(false);
  const [tenMoi, datTenMoi] = useState("");
  const [maMoi, datMaMoi] = useState("");
  const [themVao, datThemVao] = useState<Record<number, string>>({});
  const [tim, datTim] = useState("");
  const [chiThieuKg, datChiThieuKg] = useState(false);
  const [sua, datSua] = useState<Record<string, Sua>>({});
  // Chống bấm đúp: mọi nút ghi khoá tới khi yêu cầu xong (thành công hay lỗi).
  const lam = (gui_di: () => Promise<unknown>, sau?: () => void, datL = datLoi) => {
    if (dang_gui) return;
    datDangGui(true);
    datL(null);
    gui_di().then(() => { sau?.(); qc.invalidateQueries({ queryKey: ["doi-thu"] }); })
      .catch((e: Error) => datL(e.message)).finally(() => datDangGui(false));
  };
  const t = boDau(tim.trim());
  const qcLoc = (d?.quy_cach ?? []).filter(x => (!chiThieuKg || chuaCoKg(x)) && (!t || boDau(`${x.ma} ${x.ten ?? ""} ${x.nganh}`).includes(t)));
  const soThieu = (d?.quy_cach ?? []).filter(chuaCoKg).length;
  const loiKhoi = q.error ? (q.error as Error).message : null;
  return (
    <div className="dt-nhom-qc">
      <section className="dt-khoi">
        <Khoi tieu_de="Nhóm so sánh có tên" dang_tai={q.isLoading} loi={loiKhoi} canh_bao={loi}>
          <p className="dt-nhat">Nhóm có tên gộp nhiều mã KOME để so chung. Mã không thuộc nhóm nào vẫn được so theo chính mã đó.</p>
          <ul className="dt-ds dt-nhom-ds">{d?.nhom.map(g => (
            <li key={g.id}>
              <b>{g.ten}</b>
              <ul className="dt-ma">{g.ma.map(m => (
                <li key={m.ma}><span>{m.ma}{m.ten ? ` · ${m.ten}` : ""}</span>
                  <button type="button" className="chip" disabled={dang_gui} aria-label={`Bỏ mã ${m.ma} khỏi nhóm ${g.ten}`}
                    onClick={() => lam(() => gui("/api/doi-thu/nhom/bo-ma", { product_code: m.ma }))}>✕</button></li>))}</ul>
              <div className="dt-them-ma">
                <input placeholder="Thêm mã KOME (cách nhau bằng dấu phẩy)" aria-label={`Thêm mã vào nhóm ${g.ten}`}
                  value={themVao[g.id] ?? ""} onChange={e => datThemVao({ ...themVao, [g.id]: e.target.value })} />
                <button type="button" className="chip" disabled={dang_gui || !tachMa(themVao[g.id] ?? "").length}
                  onClick={() => lam(() => gui("/api/doi-thu/nhom/them-ma", { nhom_id: g.id, ma_kome: tachMa(themVao[g.id] ?? "") }),
                    () => datThemVao({ ...themVao, [g.id]: "" }))}>Thêm mã</button>
              </div>
            </li>))}
            {d && !d.nhom.length && <li className="dt-nhat">Chưa có nhóm nào.</li>}
          </ul>
          <fieldset className="dt-tao-nhom"><legend>Tạo nhóm mới</legend>
            <input placeholder="Tên nhóm (1–80 ký tự)" aria-label="Tên nhóm mới" maxLength={80} value={tenMoi} onChange={e => datTenMoi(e.target.value)} />
            <textarea placeholder="Các mã KOME, cách nhau bằng dấu phẩy hoặc khoảng trắng" aria-label="Các mã KOME của nhóm mới" rows={2}
              value={maMoi} onChange={e => datMaMoi(e.target.value)} />
            <div className="dt-nut">
              <button type="button" className="chip" disabled={dang_gui || !tenMoi.trim() || !tachMa(maMoi).length}
                onClick={() => lam(() => gui("/api/doi-thu/nhom", { ten: tenMoi.trim(), ma_kome: tachMa(maMoi) }),
                  () => { datTenMoi(""); datMaMoi(""); })}>Tạo nhóm</button>
            </div>
          </fieldset>
        </Khoi>
      </section>
      <section className="dt-khoi">
        <Khoi tieu_de="Quy cách KOME" dang_tai={q.isLoading} loi={loiKhoi} canh_bao={loiQc}
          cach_tinh="Có kg thì giá KOME mới tính được ¥/kg (đơn giá thực 90 ngày).">
          <div className="dt-loc">
            <button type="button" className="chip" aria-pressed={chiThieuKg} onClick={() => datChiThieuKg(!chiThieuKg)}>
              Chưa có kg{d ? ` (${so(soThieu)})` : ""}</button>
            <input type="search" placeholder="Tìm mã / tên / ngành" aria-label="Tìm quy cách" value={tim} onChange={e => datTim(e.target.value)} />
          </div>
          <div className="dt-cuon">
            <table className="bang dt-bang">
              <thead><tr><th>Mã</th><th>Tên</th><th>Ngành</th><th>kg/gói</th><th>gói/thùng</th><th>kg/thùng</th><th>Nguồn</th><th><span className="dt-an">Thao tác</span></th></tr></thead>
              <tbody>{qcLoc.map(x => {
                const goc = cuaDong(x), gt = sua[x.ma] ?? goc;
                const doi = (k: keyof Sua, v: string) => { const { [x.ma]: _b, ...con } = sua; const moi = { ...gt, [k]: v };
                  datSua(JSON.stringify(moi) === JSON.stringify(goc) ? con : { ...con, [x.ma]: moi }); };
                const o = (k: keyof Sua, n: string) => (
                  <td><input className="dt-so" inputMode="decimal" aria-label={`${n} của ${x.ma}`} value={gt[k]} onChange={e => doi(k, e.target.value)} /></td>);
                return (
                  <tr key={x.ma}>
                    <th>{x.ma}</th><td>{x.ten ?? ""}</td><td>{x.nganh}</td>
                    {o("kg_moi_goi", "kg mỗi gói")}{o("goi_moi_thung", "gói mỗi thùng")}{o("kg_moi_thung", "kg mỗi thùng")}
                    <td>{x.da_sua ? "người sửa" : "tự tách từ tên"}</td>
                    <td><button type="button" className="chip" disabled={dang_gui || !sua[x.ma]} aria-label={`Lưu quy cách ${x.ma}`}
                      onClick={() => lam(() => gui("/api/doi-thu/quy-cach", { product_code: x.ma, ...gt }),
                        () => { const { [x.ma]: _b, ...con } = sua; datSua(con); }, datLoiQc)}>Lưu</button></td>
                  </tr>);
              })}</tbody>
            </table>
          </div>
        </Khoi>
      </section>
    </div>
  );
}
