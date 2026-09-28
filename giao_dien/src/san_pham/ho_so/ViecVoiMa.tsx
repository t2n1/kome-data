// Cột trái dính "Việc với mã này" — tồn + cảnh báo lô · khách đến ngày mua lại · khách nên chào.
// Mọi tên khách link /khach-hang/{mã} (qua giuKhoang — giữ khoảng xem).
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../../khung/khoang";
import { ngay, so, so_luong as soLuong, yen } from "../../dinh_dang";
import type { HoSoMaApi, NenChaoApi } from "./kieu";

const lk = (ma: string) => giuKhoang(`/khach-hang/${encodeURIComponent(ma)}`);

/** "Khách nên chào" — endpoint RIÊNG (`/nen-chao`, hàm chậm, không nằm trên đường mở trang).
 *  Cột trái và tab Tồn & bán thêm gọi hook này với CÙNG queryKey → MỘT lượt tải. */
export function useNenChao(ma: string) {
  const kx = chuoiKhoang(useKhoang());
  return useQuery<NenChaoApi>({ queryKey: ["sp360-nen-chao", ma, kx],
    queryFn: () => lay<NenChaoApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/nen-chao`)) });
}

function nhanCon(con: number | null) {
  if (con == null) return { chu: "—", lop: "nhat-chu" };
  if (con < 0) return { chu: `quá ${-con} ngày`, lop: "giam" };
  if (con === 0) return { chu: "hôm nay", lop: "canh-chu" };
  if (con <= 7) return { chu: `còn ${con} ngày`, lop: "canh-chu" };
  return { chu: `còn ${con} ngày`, lop: "nhat-chu" };
}

export function ViecVoiMa({ h, moTab }: { h: HoSoMaApi["h"]; moTab: (t: string) => void }) {
  const sp = h.sp;
  const nc = useNenChao(sp.ma);
  const canh: string[] = [];
  // 'het_hang' của mart.san_pham_360 = tồn 0 VÀ có bán trong 90 ngày — nói đúng chừng đó.
  if (sp.trang_thai === "het_hang") canh.push("Tồn 0 — mã vẫn có bán trong 90 ngày qua.");
  if (sp.trang_thai === "sap_thieu") canh.push("Sắp thiếu — còn dưới 14 ngày bán.");
  if (sp.trang_thai === "chua_ro_ton") canh.push("Chưa có ảnh chụp tồn của mã này tới thời điểm này.");
  if (h.ton.some(t => t.sap_chuyen_lo)) canh.push("Sắp chuyển lô: lô đang xuất sắp hết, lô chờ sẽ lên.");
  if (h.ton.some(t => t.khong_kip_ban)) canh.push("Có lô không kịp bán trước hạn sử dụng.");
  return (
    <aside className="hs2-trai">
      <The tieu_de="Tồn & tốc độ" className="hs2-viec" cach_tinh={h.cach_tinh.ton_toc_do}>
        <p className="sp3-so-lon">{sp.ton == null ? "—" : soLuong(sp.ton)}<span className="phu"> tồn</span></p>
        <p className="phu">Bán {sp.toc_do_ngay_theo_tuoi == null ? "—" : soLuong(sp.toc_do_ngay_theo_tuoi)}/ngày (theo tuổi) ·
          còn đủ {sp.du_ban_ngay == null ? "—" : `${so(Math.round(sp.du_ban_ngay))} ngày`}</p>
        {canh.map(c => <p key={c} className="sp3-canh">{c}</p>)}
        <button type="button" className="hs2-lien-ket" onClick={() => moTab("ban_them")}>Tồn theo lô ›</button>
      </The>

      <The tieu_de="Khách đến ngày mua lại" className="hs2-viec" cach_tinh={h.cach_tinh.mua_lai}
        goc={h.mua_lai_tong ? <span className="phu">{h.mua_lai.length}/{h.mua_lai_tong}</span> : null}>
        {!h.mua_lai.length ? <p className="phu">Chưa khách nào đủ 3 lần mua mã này để có nhịp riêng.</p> :
          <ul className="hs2-ds">{h.mua_lai.map(k => { const n = nhanCon(k.con); return (
            <li key={k.ma} className="hs2-dong"><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a>
              <b className={n.lop}>{n.chu}</b></li>); })}</ul>}
      </The>

      <The tieu_de="Khách nên chào" className="hs2-viec" cach_tinh={h.cach_tinh.nen_chao}
        goc={nc.data?.t.tong ? <span className="phu">{nc.data.t.tong} khách</span> : null}>
        {h.ngung_ban ? <p className="phu">Không chào hàng đã ngừng kinh doanh (※終売※).</p> :
          nc.error ? <div className="khoi-loi">Không tải được khách nên chào: {(nc.error as Error).message}</div> :
          !nc.data ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div> :
          !nc.data.t.nen_chao.length ? <p className="phu">Chưa có khách mua đều mã cùng ngành ({h.nganh}) mà chưa mua mã này.</p> :
          <ul className="hs2-ds">{nc.data.t.nen_chao.slice(0, 5).map(k => (
            <li key={k.ma} className="hs2-dong"><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a>
              <span className="phu" title={`${k.so_ma_nganh} mã cùng ngành · mua cuối ${ngay(k.lan_cuoi)}`}>{yen(k.doanh_thu_nganh)}</span></li>))}</ul>}
        {!h.ngung_ban && nc.data && nc.data.t.tong > 5 && <button type="button" className="hs2-lien-ket" onClick={() => moTab("ban_them")}>
          Xem hết {nc.data.t.tong} khách ›</button>}
      </The>
    </aside>);
}
