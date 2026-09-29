// Dữ liệu › Giá KOME lệch (đặc tả giao diện mới §6.3): nhóm có giá KOME để so > 3× hoặc < ⅓ trung vị đối thủ
// (`gia_kome_lech` của mart.so_sanh_nhom — giao diện không tự tính lại). Gần như luôn là quy cách mã KOME sai, không phải
// giá: nút "Sửa quy cách" ghi POST /api/doi-thu/quy-cach (máy chủ coi ô bằng giá trị hiện dùng là "không sửa").
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { gui, lay } from "../api";
import { HinhMa } from "../chung/HinhMa";
import { Khoi } from "../chung/Khoi";
import { so, so_luong, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import { HopThoai } from "./HopThoai";
import type { Nhom, NhomQuyCach } from "./kieu";
import { khoaNhom } from "./so_sanh_logic";
import { NutLuu } from "./SuaNho";

const CACH_TINH = <>
  Nhóm có giá KOME để so (標準価格, thiếu thì thực bán 90 ngày, quy về ¥/kg) lớn hơn 3× hoặc nhỏ hơn ⅓ trung vị giá đối thủ.
  Lệch cỡ này gần như luôn là quy cách mã KOME sai chứ không phải giá. Hay gặp: một đơn vị バラ (00) của mã thật ra là cả
  thùng; tên ghi ba thừa số (80g × 20 × 4) nên kg/thùng tách thiếu một thừa số. Sửa kg/gói · gói/thùng · kg/thùng — nhóm
  hết lệch sẽ tự rời danh sách này và hiện lại ở So sánh giá.</>;

/** "×92.8" · "×0.25": giá KOME để so ÷ trung vị. */
const nhanLech = (x: number | null) => (x == null ? "—" : `×${so_luong(x, x >= 10 ? 0 : x >= 1 ? 1 : 2)}`);
const lechCua = (n: Nhom) => (n.gia_kome_so != null && n.trung_vi > 0 ? n.gia_kome_so / n.trung_vi : null);
const kg = (v: number) => `${so_luong(v, 3)} kg`;

export function TabGiaKomeLech() {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "so-sanh", kx],
    queryFn: () => lay<{ nhom: Nhom[] }>(`/api/doi-thu/so-sanh${kx ? "?" + kx : ""}`) });
  const ds = useMemo(() => (q.data?.nhom ?? []).filter(n => n.gia_kome_lech)
    .sort((a, b) => { const x = lechCua(a) ?? 1, y = lechCua(b) ?? 1; return Math.max(y, 1 / y) - Math.max(x, 1 / x); }), [q.data]);
  const [sua, datSua] = useState<Nhom | null>(null);
  return (
    <section className="dt-khoi">
      <Khoi tieu_de="Giá KOME lệch" dang_tai={q.isLoading} loi={q.error ? (q.error as Error).message : null} cach_tinh={CACH_TINH}
        nhan={q.data ? `${so(ds.length)} nhóm` : undefined} mau_nhan={ds.length ? "canh" : "ok"}>
        {q.data && !ds.length && <p className="dt-nhat" role="status">Không có nhóm nào lệch.</p>}
        {ds.length > 0 && (
          <div className="dt-cuon">
            <table className="bang dt-bang dt-bang-lech">
              <thead><tr><th>Nhóm</th><th>Mã KOME</th><th className="r">Giá KOME để so</th><th className="r">Trung vị đối thủ</th>
                <th className="r">Lệch</th><th>kg / gói</th><th>gói / thùng</th><th>kg / thùng</th><th><span className="dt-an">Thao tác</span></th></tr></thead>
              <tbody>{ds.map(n => {
                const ten = n.ten_nhom ?? n.nhom_khoa;
                return (
                  <tr key={khoaNhom(n)}>
                    <td className="dt-lech-o"><span className="dt-lech-ten"><HinhMa ma={n.ma_kome?.[0]} ten={ten} co={26} trang_tri />{ten}</span></td>
                    <td>{(n.ma_kome ?? []).join(", ") || "—"}</td>
                    <td className="r">{yen(n.gia_kome_so)}/kg</td>
                    <td className="r">{yen(n.trung_vi)}/kg</td>
                    <td className="r c-do t-dam">{nhanLech(lechCua(n))}</td>
                    {([["kg / gói", n.kome_kg_goi == null ? null : kg(n.kome_kg_goi)],
                       ["gói / thùng", n.kome_goi_thung == null ? null : so_luong(n.kome_goi_thung)],
                       ["kg / thùng", n.kome_kg_thung == null ? null : kg(n.kome_kg_thung)]] as const).map(([nhan, v]) => (
                      <td key={nhan}>{v ?? <button type="button" className="dt-hoi-cam" disabled={!n.ma_kome?.length}
                        aria-label={`${ten}: chưa có ${nhan} — sửa quy cách`} onClick={() => datSua(n)}>?</button>}</td>))}
                    <td><button type="button" className="chip" disabled={!n.ma_kome?.length} aria-label={`Sửa quy cách ${ten}`}
                      onClick={() => datSua(n)}>Sửa quy cách</button></td>
                  </tr>);
              })}</tbody>
            </table>
          </div>)}
      </Khoi>
      {sua && <SuaQuyCach n={sua} dong={() => datSua(null)} />}
    </section>
  );
}

type O3 = { kg_moi_goi: string; goi_moi_thung: string; kg_moi_thung: string };
const chuoi = (v: number | null | undefined) => (v == null ? "" : String(v));

/** Hộp sửa quy cách MỘT mã KOME của nhóm (nhóm nhiều mã: chọn mã). Điền sẵn số hiện dùng của mã đó
 *  (/api/doi-thu/nhom-quy-cach — cùng khoá truy vấn với tab Nhóm & quy cách). Lưu xong làm mới mọi truy vấn "doi-thu". */
export function SuaQuyCach({ n, dong }: { n: Nhom; dong: () => void }) {
  const kx = chuoiKhoang(useKhoang());
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["doi-thu", "nhom-quy-cach", kx],
    queryFn: () => lay<NhomQuyCach>(`/api/doi-thu/nhom-quy-cach${kx ? "?" + kx : ""}`) });
  const ma = n.ma_kome ?? [];
  const [chon, datChon] = useState(ma[0] ?? "");
  const [o, datO] = useState<Record<string, O3>>({});
  const [dang, datDang] = useState(false);
  const [loi, datLoi] = useState<string | null>(null);
  const dongQc = q.data?.quy_cach.find(x => x.ma === chon);
  const goc: O3 = dongQc ? { kg_moi_goi: chuoi(dongQc.kg_moi_goi), goi_moi_thung: chuoi(dongQc.goi_moi_thung), kg_moi_thung: chuoi(dongQc.kg_moi_thung) }
    : { kg_moi_goi: "", goi_moi_thung: "", kg_moi_thung: "" };
  const gt = o[chon] ?? goc;
  const doi = JSON.stringify(gt) !== JSON.stringify(goc);
  const luu = () => {
    if (dang) return;
    datDang(true); datLoi(null);
    gui("/api/doi-thu/quy-cach", { product_code: chon, ...gt })
      .then(() => { qc.invalidateQueries({ queryKey: ["doi-thu"] }); dong(); })
      .catch((e: Error) => datLoi(e.message)).finally(() => datDang(false));
  };
  const oNhap = ({ k, nhan }: { k: keyof O3; nhan: string }) => (
    <label>{nhan}<input className="dt-so" inputMode="decimal" placeholder="?" value={gt[k]}
      onChange={e => datO({ ...o, [chon]: { ...gt, [k]: e.target.value } })} /></label>);
  return (
    <HopThoai tieu_de={`Sửa quy cách · ${n.ten_nhom ?? n.nhom_khoa}`} dong={dong} rong={480}>
      <div className="dt-nho">
        <p className="dt-nhat">Giá KOME để so {yen(n.gia_kome_so)}/kg · trung vị đối thủ {yen(n.trung_vi)}/kg ({nhanLech(lechCua(n))})</p>
        {ma.length > 1 && <label>Mã KOME<select value={chon} onChange={e => datChon(e.target.value)}>
          {ma.map(m => <option key={m} value={m}>{m}{q.data?.quy_cach.find(x => x.ma === m)?.ten ? ` · ${q.data.quy_cach.find(x => x.ma === m)!.ten}` : ""}</option>)}
        </select></label>}
        {ma.length === 1 && <p><b>{chon}</b>{dongQc?.ten ? ` · ${dongQc.ten}` : ""}</p>}
        {q.isLoading ? <p className="dt-nhat">Đang tải quy cách…</p>
          : q.error ? <p role="alert" className="dt-loi">{(q.error as Error).message}</p>
          : !dongQc ? <p role="alert" className="dt-loi">Không tìm thấy quy cách của mã {chon}.</p>
          : <div className="dt-luoi-2">
              {oNhap({ k: "kg_moi_goi", nhan: "kg / gói" })}{oNhap({ k: "goi_moi_thung", nhan: "gói / thùng" })}
              {oNhap({ k: "kg_moi_thung", nhan: "kg / thùng" })}
              <p className="dt-nhat">Nguồn hiện tại: {dongQc.da_sua ? "người sửa" : "tự tách từ tên / 荷姿"}</p>
            </div>}
        <NutLuu luu={luu} dong={dong} tat={!doi || !dongQc} dang={dang} loi={loi} chu="Để trống = bỏ số người sửa." />
      </div>
    </HopThoai>
  );
}
