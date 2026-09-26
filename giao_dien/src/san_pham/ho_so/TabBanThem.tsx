// Tab Tồn & bán thêm — tồn theo lô · mua kèm cùng phiếu · khách nên chào đầy đủ.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../../khung/khoang";
import { ngay, pc, so, so_luong as soLuong, yen } from "../../dinh_dang";
import type { TabBanThemApi } from "./kieu";

export function TabBanThem({ ma, ngungBan, nganh }: { ma: string; ngungBan: boolean; nganh: string }) {
  const kx = chuoiKhoang(useKhoang());
  const { data, error } = useQuery<TabBanThemApi>({ queryKey: ["sp360-bt", ma, kx],
    queryFn: () => lay<TabBanThemApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/ban-them`)) });
  if (error) return <div className="khoi-loi">Không tải được tab Tồn & bán thêm: {(error as Error).message}</div>;
  if (!data) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const t = data.t, ct = data.cach_tinh;
  return (<>
    <The tieu_de="Tồn theo lô" cach_tinh={ct.ton_lo} goc={<a className="nut-nho" href={giuKhoang(`/kho-hang?tim=${encodeURIComponent(ma)}`)}>Mở Kho hàng ›</a>}>
      {!t.ton.length ? <p className="phu">Chưa có ảnh chụp tồn của mã này tới thời điểm này.</p> :
        <table className="bang"><thead><tr><th>Lô</th><th className="so">Số lượng</th><th>Hạn</th><th className="so">Bán từ / hết sau</th></tr></thead>
          <tbody>{t.ton.map(l => (<tr key={l.kho + (l.best_before ?? "")}>
            <td className="ten-jp">{l.ten_kho} <span className="phu">({l.vai_tro_lo})</span></td>
            <td className="so">{l.so_luong == null ? "—" : soLuong(l.so_luong)}</td>
            <td><span className={"nhan-vien " + l.mau_han}>{l.nhan_han}</span> {l.best_before ?? ""}</td>
            <td className="so">{l.bat_dau_ban_sau == null ? "—" : `${so(Math.round(l.bat_dau_ban_sau))}`} / {l.ban_het_sau == null ? "—" : `${so(Math.round(l.ban_het_sau))} ngày`}
              {l.khong_kip_ban && <span className="nhan-vien do"> không kịp bán</span>}</td></tr>))}</tbody></table>}
    </The>
    <div className="sp3-luoi-2">
      <The tieu_de="Hay được mua cùng phiếu" cach_tinh={ct.mua_kem}
        phu={t.tong_phieu ? `Trên ${so(t.tong_phieu)} phiếu có mã này trong 12 tháng.` : undefined}>
        {!t.mua_kem.length ? <p className="phu">Chưa có phiếu nào có mã này cùng mã khác.</p> :
          <ul className="sp3-thanh-ds">{t.mua_kem.map(k => (
            <li key={k.ma} className="sp3-thanh"><a className="ten-jp" href={giuKhoang(`/san-pham/${encodeURIComponent(k.ma)}`)}>{k.ten}</a>
              <i style={{ width: `${Math.round((k.ty_le ?? 0) * 100)}%` }} /><span className="so">{pc(k.ty_le)} · {so(k.so_phieu)} phiếu</span></li>))}</ul>}
      </The>
      <The tieu_de="Khách nên chào" cach_tinh={ct.nen_chao}>
        {ngungBan ? <p className="phu">Không chào hàng đã ngừng kinh doanh (※終売※).</p> :
          !t.nen_chao.length ? <p className="phu">Chưa có khách mua đều mã cùng ngành ({nganh}) mà chưa mua mã này.</p> :
          <table className="bang"><thead><tr><th>Khách</th><th className="so">DT ngành 12 tháng</th><th className="so">Mã cùng ngành</th><th>Mua cuối</th></tr></thead>
            <tbody>{t.nen_chao.map(k => (<tr key={k.ma}><td><a className="ten-jp" href={giuKhoang(`/khach-hang/${encodeURIComponent(k.ma)}`)}>{k.ten}</a></td>
              <td className="so">{yen(k.doanh_thu_nganh)}</td><td className="so">{so(k.so_ma_nganh)}</td><td>{ngay(k.lan_cuoi)}</td></tr>))}</tbody></table>}
      </The>
    </div>
  </>);
}
