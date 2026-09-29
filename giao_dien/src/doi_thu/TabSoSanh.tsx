import { useQuery } from "@tanstack/react-query";
import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { ONoi } from "../chung/ONoi";
import { ngay, so, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { Nhom } from "./kieu";
import { NHAN_DUYET } from "./kieu";
import { BO_LOC_TRONG, dangLocDong, locNhom, locQuanSat, dongMoSan, kemGiaTri, luaChonLoc, viTriKome, type BoLoc } from "./loc";

// Giá khách kể (tin hiện trường @, 063): đã có trong quan_sat của nhóm nhưng KHÔNG vào thấp nhất / trung vị / cao nhất
// (mart 060) — ở đây chỉ gắn nhãn và đếm số dòng, không phải chỉ số mới. Đếm trên ĐÚNG các dòng chi tiết đang hiện
// (`locQuanSat` với bộ lọc hiện tại), để "khách kể: n tin" khớp số dòng mang nhãn khi mở nhóm.
const KHACH_KE = "khach_ke";
const keCua = (n: Nhom, l: BoLoc) => locQuanSat(n.quan_sat, l).filter(x => x.loai_nguon === KHACH_KE).length;
const TUOI = [[null, "Mọi tuổi"], [30, "≤ 30 ngày"], [90, "≤ 90 ngày"], [180, "≤ 180 ngày"]] as const;
type Props = {
  nganh: string; ben: string; nhom: string;   // đọc từ URL (?nganh= ?ben= ?nhom=) ở ManDoiThu
  datNganh: (n: string) => void; datBen: (b: string) => void; datNhom: (khoa: string) => void;
};

export function TabSoSanh({ nganh, ben, nhom, datNganh, datBen, datNhom }: Props) {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "so-sanh", kx],
    queryFn: () => lay<{ nhom: Nhom[] }>(`/api/doi-thu/so-sanh${kx ? "?" + kx : ""}`) });
  const [rieng, datRieng] = useState({ tim: "", chi_cung_hang: false, chi_xac_nhan: false, kenh: "", tuoi: null as number | null });
  const l: BoLoc = { ...BO_LOC_TRONG, ...rieng, nganh, ben };
  const datL = (moi: Partial<BoLoc>) => {
    const { nganh: n, ben: b, ...con } = moi;
    if (n !== undefined) datNganh(n);
    if (b !== undefined) datBen(b);
    if (Object.keys(con).length) datRieng({ ...rieng, ...con });
  };
  const [mo, datMo] = useState<string | null>(null);
  const tatCa = q.data?.nhom;
  const chon = useMemo(() => luaChonLoc(tatCa ?? []), [tatCa]);
  const dsBen = chon.ben.some(b => b.ma === ben) || !ben ? chon.ben : [...chon.ben, { ma: ben, ten: ben }];
  const ds = locNhom(tatCa ?? [], l);
  // ?nhom=<nhom_khoa>: mở sẵn nhóm đó rồi cuộn tới nó (một lần cho mỗi giá trị của tham số).
  const dong = useRef<Record<string, HTMLElement | null>>({});
  const daMo = useRef("");
  useEffect(() => {
    if (!nhom || daMo.current === nhom || !tatCa) return;
    const k = dongMoSan(ds, nhom);
    if (!k) return;
    daMo.current = nhom;
    const khoa = k.nhom_khoa + "|" + k.don_vi_so;
    datMo(khoa);
    requestAnimationFrame(() => dong.current[khoa]?.scrollIntoView?.({ block: "start" }));
  });
  // ?nhom= trỏ tới nhóm KHÔNG có dòng so sánh (vd chỉ có giá khách kể — mart 060 không tính chúng; hay đi từ
  // "Hàng được nhắc" ở Tổng quan): nói ra, không để bảng lặng lẽ không mở gì.
  const khongDong = !!nhom && !!tatCa && !tatCa.some(n => n.nhom_khoa === nhom);
  const donVi = (n: Nhom) => (n.don_vi_so === "kg" ? "/kg" : `/${n.don_vi_so.replace("don_vi:", "")}`);
  return (
    <section className="dt-khoi">
      <Khoi tieu_de="So sánh giá theo nhóm" dang_tai={q.isLoading} loi={q.error ? (q.error as Error).message : null}
        cach_tinh="Giá quy về chưa thuế (giá có thuế ÷ 1,08) và về ¥/kg khi biết khối lượng. Giá KOME = đơn giá thực 90 ngày (Σ doanh thu thuần ÷ Σ kg đã bán). Không tính hàng hết, giá khách kể và giá bất thường (> 2× hoặc < ½ trung vị khi nhóm có ≥ 3 bên). Số của nhóm gồm cả hàng cùng hàng và hàng thay thế."
        canh_bao={dangLocDong(l) ? "Bộ lọc chỉ ẩn dòng chi tiết — số của nhóm (thấp nhất, trung vị, cao nhất, vị trí KOME) vẫn tính trên mọi hàng, cả cùng hàng lẫn thay thế." : null}>
        <div className="dt-loc">
          <select aria-label="Ngành" value={nganh} onChange={e => datL({ nganh: e.target.value })}>
            <option value="">Mọi ngành</option>{kemGiaTri(chon.nganh, nganh).map(n => <option key={n} value={n}>{n}</option>)}</select>
          <select aria-label="Bên" value={ben} onChange={e => datL({ ben: e.target.value })}>
            <option value="">Mọi bên</option>{dsBen.map(b => <option key={b.ma} value={b.ma}>{b.ten}</option>)}</select>
          <select aria-label="Kênh hoặc mức giá" value={rieng.kenh} onChange={e => datL({ kenh: e.target.value })}>
            <option value="">Mọi kênh / mức</option>{chon.kenh.map(k => <option key={k} value={k}>{k}</option>)}</select>
          <select aria-label="Tuổi quan sát" value={rieng.tuoi ?? ""} onChange={e => datL({ tuoi: e.target.value === "" ? null : Number(e.target.value) })}>
            {TUOI.map(([v, t]) => <option key={t} value={v ?? ""}>{t}</option>)}</select>
          <input type="search" placeholder="Tìm nhóm / mã KOME" aria-label="Tìm nhóm hoặc mã KOME" value={l.tim} onChange={e => datL({ tim: e.target.value })} />
          <label><input type="checkbox" checked={l.chi_cung_hang} onChange={e => datL({ chi_cung_hang: e.target.checked })} /> Chỉ cùng hàng</label>
          <label><input type="checkbox" checked={l.chi_xac_nhan} onChange={e => datL({ chi_xac_nhan: e.target.checked })} /> Chỉ số đã xác nhận</label>
        </div>
        {khongDong && <p className="dt-nhat" role="status">Chưa có giá bảng giá cho nhóm này — chỉ có tin khách kể (xem Tổng quan › Hiện trường)</p>}
        <div className="dt-cuon">
          <table className="bang dt-bang">
            <thead><tr><th>Nhóm</th><th>KOME</th><th>Thấp nhất</th><th>Trung vị</th><th>Cao nhất</th><th>Số bên</th><th>Vị trí KOME</th></tr></thead>
            <tbody>{ds.map(n => { const k = n.nhom_khoa + "|" + n.don_vi_so; return (
              <Fragment key={k}>
                <tr className="dt-dong" ref={el => { dong.current[k] = el; }}>
                  <th><button type="button" className="lien-ket" aria-expanded={mo === k}
                    onClick={() => { daMo.current = mo === k ? "" : n.nhom_khoa; datMo(mo === k ? null : k); datNhom(daMo.current); }}>{n.ten_nhom ?? n.nhom_khoa}</button>
                    {keCua(n, l) > 0 && <span className="dt-nhat"> · khách kể: {so(keCua(n, l))} tin</span>}</th>
                  <td>{n.gia_kome != null ? yen(n.gia_kome) + donVi(n) : "—"}</td>
                  <td>{yen(n.thap_nhat)}{donVi(n)} <span className="dt-nhat">{n.ben_thap_nhat}</span></td>
                  <td>{yen(n.trung_vi)}{donVi(n)}</td>
                  <td>{yen(n.cao_nhat)}{donVi(n)}</td>
                  <td>{n.so_ben}</td>
                  <td>{viTriKome(n) ?? "—"}</td>
                </tr>
                {mo === k && locQuanSat(n.quan_sat, l).map(x => (
                  <tr key={x.nguon + x.id} className={"dt-con" + (x.bat_thuong ? " bat-thuong" : "")}>
                    <td>{x.ten_doi_thu ?? x.ma_doi_thu}{x.loai_nguon === KHACH_KE && <span className="dt-ke">khách kể</span>}</td>
                    <td colSpan={2}>{x.ten_goc} <span className="dt-nhat">{x.quy_cach_goc}</span></td>
                    <td><ONoi noi_dung={<div className="o-noi-chu">{x.nen_gia}<br />Nguồn: {x.nguon_file ?? x.loai_nguon} · {ngay(x.ngay_nguon)}{x.vi_tri ? ` · ${x.vi_tri}` : ""}</div>}>
                      {x.yen_chuan != null ? yen(x.yen_chuan) : "—"}</ONoi></td>
                    <td>{x.gia_goc != null ? `${yen(x.gia_goc)}/${x.don_vi_gia ?? "?"}` : "—"}</td>
                    <td>{x.nhan === "cung_hang" ? "cùng hàng" : "thay thế"}</td>
                    <td>{NHAN_DUYET[x.trang_thai_duyet]}{x.bat_thuong ? " · bất thường" : ""}</td>
                  </tr>))}
              </Fragment>); })}</tbody>
          </table>
        </div>
      </Khoi>
    </section>
  );
}
