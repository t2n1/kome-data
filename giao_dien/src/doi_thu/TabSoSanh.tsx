import { useQuery } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { ONoi } from "../chung/ONoi";
import { ngay, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { Nhom } from "./kieu";
import { NHAN_DUYET } from "./kieu";
import { dangLocDong, locNhom, locQuanSat, viTriKome, type BoLoc } from "./loc";

export function TabSoSanh() {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "so-sanh", kx],
    queryFn: () => lay<{ nhom: Nhom[] }>(`/api/doi-thu/so-sanh${kx ? "?" + kx : ""}`) });
  const [l, datL] = useState<BoLoc>({ tim: "", chi_cung_hang: false, chi_xac_nhan: false });
  const [mo, datMo] = useState<string | null>(null);
  const ds = locNhom(q.data?.nhom ?? [], l);
  const donVi = (n: Nhom) => (n.don_vi_so === "kg" ? "/kg" : `/${n.don_vi_so.replace("don_vi:", "")}`);
  return (
    <section className="dt-khoi">
      <Khoi tieu_de="So sánh giá theo nhóm" dang_tai={q.isLoading} loi={q.error ? (q.error as Error).message : null}
        cach_tinh="Giá quy về chưa thuế (giá có thuế ÷ 1,08) và về ¥/kg khi biết khối lượng. Giá KOME = đơn giá thực 90 ngày (Σ doanh thu thuần ÷ Σ kg đã bán). Không tính hàng hết, giá khách kể và giá bất thường (> 2× hoặc < ½ trung vị khi nhóm có ≥ 3 bên). Số của nhóm gồm cả hàng cùng hàng và hàng thay thế."
        canh_bao={dangLocDong(l) ? "Bộ lọc chỉ ẩn dòng chi tiết — số của nhóm (thấp nhất, trung vị, cao nhất, vị trí KOME) vẫn tính trên mọi hàng, cả cùng hàng lẫn thay thế." : null}>
        <div className="dt-loc">
          <input type="search" placeholder="Tìm nhóm / mã KOME" aria-label="Tìm nhóm hoặc mã KOME" value={l.tim} onChange={e => datL({ ...l, tim: e.target.value })} />
          <label><input type="checkbox" checked={l.chi_cung_hang} onChange={e => datL({ ...l, chi_cung_hang: e.target.checked })} /> Chỉ cùng hàng</label>
          <label><input type="checkbox" checked={l.chi_xac_nhan} onChange={e => datL({ ...l, chi_xac_nhan: e.target.checked })} /> Chỉ số đã xác nhận</label>
        </div>
        <div className="dt-cuon">
          <table className="bang dt-bang">
            <thead><tr><th>Nhóm</th><th>KOME</th><th>Thấp nhất</th><th>Trung vị</th><th>Cao nhất</th><th>Số bên</th><th>Vị trí KOME</th></tr></thead>
            <tbody>{ds.map(n => { const k = n.nhom_khoa + "|" + n.don_vi_so; return (
              <Fragment key={k}>
                <tr className="dt-dong">
                  <th><button type="button" className="lien-ket" aria-expanded={mo === k}
                    onClick={() => datMo(mo === k ? null : k)}>{n.ten_nhom ?? n.nhom_khoa}</button></th>
                  <td>{n.gia_kome != null ? yen(n.gia_kome) + donVi(n) : "—"}</td>
                  <td>{yen(n.thap_nhat)}{donVi(n)} <span className="dt-nhat">{n.ben_thap_nhat}</span></td>
                  <td>{yen(n.trung_vi)}{donVi(n)}</td>
                  <td>{yen(n.cao_nhat)}{donVi(n)}</td>
                  <td>{n.so_ben}</td>
                  <td>{viTriKome(n) ?? "—"}</td>
                </tr>
                {mo === k && locQuanSat(n.quan_sat, l).map(x => (
                  <tr key={x.nguon + x.id} className={"dt-con" + (x.bat_thuong ? " bat-thuong" : "")}>
                    <td>{x.ten_doi_thu ?? x.ma_doi_thu}</td>
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
