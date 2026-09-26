// Tab Giá & lãi — đơn giá thực theo tháng × quy cách (cạnh giá bảng bậc) · biên theo tháng ·
// khách giá thấp / biên thấp · bảng giá theo bậc.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../../khung/khoang";
import { ngay, pc, so, yen } from "../../dinh_dang";
import { TN } from "../../khoi_dau";
import type { TabGiaApi, ThangMa } from "./kieu";

const lk = (ma: string) => giuKhoang(`/khach-hang/${encodeURIComponent(ma)}`);
const MAU = ["var(--ok-vien)", "var(--lien-ket)", "var(--canh-vien)", "var(--do)"];

export function TabGia({ ma, thang }: { ma: string; thang: ThangMa[] }) {
  const kx = chuoiKhoang(useKhoang());
  const { data, error } = useQuery<TabGiaApi>({ queryKey: ["sp360-gia", ma, kx],
    queryFn: () => lay<TabGiaApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/gia`)) });
  if (error) return <div className="khoi-loi">Không tải được tab Giá & lãi: {(error as Error).message}</div>;
  if (!data) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const t = data.t, ct = data.cach_tinh;
  const cacThang = [...new Set(t.don_gia.map(x => x.thang))].sort();
  const cacQc = [...new Set(t.don_gia.map(x => x.pack_code))];
  const t12 = thang.slice(-12);
  const theoGia = [...t.khach_gia].filter(k => k.don_gia != null).sort((a, b) => (a.don_gia! - b.don_gia!)).slice(0, 10);
  const theoBien = [...t.khach_gia].sort((a, b) => ((a.bien ?? 0) - (b.bien ?? 0))).slice(0, 10);
  return (<>
    <The tieu_de="Đơn giá thực bán theo tháng" cach_tinh={ct.don_gia}
      phu={t.bac_gia.length ? `Giá bảng mới nhất: ${t.bac_gia.map(g => `bậc ${g.bac} · ${g.quy_cach} ${yen(g.gia)}`).slice(0, 4).join(" · ")}` : "Chưa có bảng giá của mã này."}>
      {!cacThang.length ? <p className="phu">Chưa bán trong 12 tháng.</p> :
        <BieuDo nhan={cacThang.map(x => `${+x.slice(5)}/${x.slice(2, 4)}`)} cao={200}
          chuoi={cacQc.map((q, i) => ({ ten: t.don_gia.find(x => x.pack_code === q)!.quy_cach, kieu: "duong" as const,
            gia_tri: cacThang.map(th => t.don_gia.find(x => x.thang === th && x.pack_code === q)?.don_gia ?? null), mau: MAU[i % MAU.length] }))}
          dinh_dang={v => yen(v == null ? null : Math.round(v))} dinh_dang_truc={v => yen(Math.round(v))}
          mo_ta="Đơn giá thực bán theo tháng, mỗi quy cách một đường" />}
    </The>
    <The tieu_de="Biên lãi gộp theo tháng" cach_tinh={ct.bien}>
      {!t12.some(x => x.doanh_thu > 0) ? <p className="phu">Chưa bán trong 12 tháng.</p> :
        <BieuDo nhan={t12.map(x => `${+x.thang.slice(5)}/${x.thang.slice(2, 4)}`)} cao={170}
          chuoi={[{ ten: "Biên", kieu: "duong", gia_tri: t12.map(x => x.bien == null ? null : x.bien * 100), mau: "var(--ok-vien)" }]}
          dinh_dang={v => v == null ? "—" : `${v.toFixed(1)}%`} dinh_dang_truc={v => `${v.toFixed(0)}%`} mo_ta="Biên lãi gộp của mã theo tháng, 12 tháng" />}
    </The>
    <div className="sp3-luoi-2">
      <BangGia tieu_de="Khách mua giá thấp nhất" ds={theoGia} ct={ct.khach_gia} />
      <BangGia tieu_de="Khách biên thấp nhất" ds={theoBien} ct={ct.khach_gia} />
    </div>
    {TN.bang_gia && t.bac_gia.length > 0 && <The tieu_de="Giá theo bậc (売価No.)" cach_tinh={ct.bac_gia}>
      <div className="bang-cuon"><table className="bang"><thead><tr><th>Bậc</th><th>Quy cách</th><th className="so">Giá (chưa thuế)</th><th>Từ ngày</th></tr></thead>
        <tbody>{t.bac_gia.map(g => (<tr key={g.bac + "|" + g.pack_code}><td>{g.bac}</td><td>{g.quy_cach}</td><td className="so">{yen(g.gia)}</td><td>{ngay(g.tu_ngay)}</td></tr>))}</tbody></table></div>
    </The>}
  </>);
}

function BangGia({ tieu_de, ds, ct }: { tieu_de: string; ds: TabGiaApi["t"]["khach_gia"]; ct: string }) {
  return (<The tieu_de={tieu_de} cach_tinh={ct}>
    {!ds.length ? <p className="phu">Chưa khách nào mua ≥ 2 ngày trong 12 tháng.</p> :
      <div className="bang-cuon"><table className="bang"><thead><tr><th>Khách</th><th className="so">Đơn giá</th><th className="so">Biên</th><th className="so">Doanh thu</th><th className="so">Ngày mua</th></tr></thead>
        <tbody>{ds.map(k => (<tr key={k.ma}><td><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a></td>
          <td className="so">{k.don_gia == null ? "—" : yen(Math.round(k.don_gia))}</td><td className="so">{pc(k.bien)}</td>
          <td className="so">{yen(k.doanh_thu)}</td><td className="so">{so(k.so_lan)}</td></tr>))}</tbody></table></div>}
  </The>);
}
