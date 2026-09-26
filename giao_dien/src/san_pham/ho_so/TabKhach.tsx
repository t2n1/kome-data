// Tab Khách hàng — Pareto tập trung · 47 tỉnh · người phụ trách · khách mới/quay lại · bảng khách.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { LuoiTinh } from "../../chung/LuoiTinh";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../../khung/khoang";
import { gon, ngay, pc, so, so_luong as soLuong, yen } from "../../dinh_dang";
import type { KhoangMaApi } from "../kieu";
import type { KhachDong, TabKhachApi } from "./kieu";

const lk = (ma: string) => giuKhoang(`/khach-hang/${encodeURIComponent(ma)}`);

export function TabKhach({ ma, khoang }: { ma: string; khoang: KhoangMaApi }) {
  const kx = chuoiKhoang(useKhoang());
  const { data, error } = useQuery<TabKhachApi>({ queryKey: ["sp360-khach", ma, kx],
    queryFn: () => lay<TabKhachApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/khach`)) });
  if (error) return <div className="khoi-loi">Không tải được tab Khách hàng: {(error as Error).message}</div>;
  if (!data) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const t = data.t, ct = data.cach_tinh, top = t.tap_trung.slice(0, 30);
  return (<>
    <div className="sp3-luoi-2">
      <The tieu_de="Tập trung khách" cach_tinh={ct.tap_trung}
        phu={t.top10_ty_trong == null ? "Chưa có doanh thu 12 tháng." : `10 khách lớn nhất chiếm ${pc(t.top10_ty_trong)} doanh thu 12 tháng của mã (${so(t.tap_trung.length)} khách).`}>
        {top.length > 0 && <BieuDo nhan={top.map((_, i) => String(i + 1))} nhan_day_du={top.map(k => k.ten)} cao={200}
          chuoi={[{ ten: "Doanh thu", kieu: "cot", gia_tri: top.map(k => k.doanh_thu), mau: "var(--ok-vien)" },
                  { ten: "Luỹ kế %", kieu: "duong", gia_tri: top.map(k => k.luy_ke == null ? null : k.luy_ke * 100), mau: "var(--lien-ket)", truc_phai: true }]}
          dinh_dang={(v, c) => c.truc_phai ? (v == null ? "—" : `${v.toFixed(1)}%`) : yen(v)} dinh_dang_truc={v => gon(v)}
          onBam={i => { location.href = lk(top[i].ma); }} mo_ta="Doanh thu 12 tháng theo khách xếp giảm dần, đường luỹ kế phần trăm" />}
      </The>
      <The tieu_de="Theo tỉnh" cach_tinh={ct.tinh}
        phu={t.tinh.khong_ro ? `Không rõ tỉnh: ${yen(t.tinh.khong_ro)}.` : undefined}>
        <LuoiTinh o={t.tinh.o} rong={t.tinh.rong} cao={t.tinh.cao} o_rong={t.tinh.o_rong} o_cao={t.tinh.o_cao}
          nhan={o => gon(o.doanh_thu)} mo_ta="Doanh thu 12 tháng của mã theo 47 tỉnh"
          noi={o => <><strong className="ten-jp">{o.ten}</strong><div>Doanh thu <b>{yen(o.doanh_thu)}</b></div><div>Khách <b>{so(o.so_khach)}</b></div></>} />
      </The>
    </div>
    <div className="sp3-luoi-2">
      <The tieu_de="Theo người phụ trách" cach_tinh={ct.nguoi}>
        {!t.nguoi.length ? <p className="phu">Chưa bán trong 12 tháng.</p> :
          <table className="bang"><thead><tr><th>Người phụ trách</th><th className="so">Doanh thu</th><th className="so">Biên</th><th className="so">Khách</th></tr></thead>
            <tbody>{t.nguoi.map(n => (<tr key={n.ma}>
              <td>{n.ten ?? `(mã ${n.ma || "trống"} không có trong danh sách phụ trách)`}</td>
              <td className="so">{yen(n.doanh_thu)}</td><td className="so">{pc(n.bien)}</td>
              <td className="so">{so(n.so_khach)}</td></tr>))}</tbody></table>}
      </The>
      <The tieu_de="Khách mới / quay lại theo tháng" cach_tinh={ct.khach_moi}>
        <BieuDo nhan={t.khach_moi.map(x => `${+x.thang.slice(5)}/${x.thang.slice(2, 4)}`)} cao={180}
          chuoi={[{ ten: "Quay lại", kieu: "cot", gia_tri: t.khach_moi.map(x => x.quay_lai), mau: "var(--chu-mo)" },
                  { ten: "Mới", kieu: "cot", gia_tri: t.khach_moi.map(x => x.moi), mau: "var(--ok-vien)" }]}
          dinh_dang={v => so(v)} mo_ta="Số khách mới và khách quay lại mua mã này theo tháng" />
      </The>
    </div>
    {khoang && <The tieu_de="Khách mua trong khoảng xem" cach_tinh={ct.khoang}>
      {!khoang.khach.length ? <p className="phu">Không khách nào mua mã này trong khoảng xem.</p> :
        <table className="bang"><thead><tr><th>Khách</th><th className="so">Doanh thu</th><th className="so">SL</th><th className="so">Ngày mua</th><th>Lần cuối</th></tr></thead>
          <tbody>{khoang.khach.map(k => (<tr key={k.ma}><td><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a></td>
            <td className="so">{yen(k.doanh_thu)}</td><td className="so">{soLuong(k.so_luong)}</td><td className="so">{so(k.so_ngay)}</td><td>{ngay(k.lan_cuoi)}</td></tr>))}</tbody></table>}
    </The>}
    <div className="sp3-luoi-2">
      <BangKhach tieu_de="Khách đang mua" ds={t.dang_mua} rong="Chưa khách nào đang mua đều." ct={ct.khach_cap} />
      <BangKhach tieu_de="Khách đã ngừng mua mã này" ds={t.da_ngung} rong="Không khách nào ngừng mua (im lặng ≥ 2× nhịp riêng)." ct={ct.khach_cap} />
    </div>
  </>);
}

function BangKhach({ tieu_de, ds, rong, ct }: { tieu_de: string; ds: KhachDong[]; rong: string; ct: string }) {
  return (<The tieu_de={tieu_de} cach_tinh={ct}>
    {!ds.length ? <p className="phu">{rong}</p> :
      <table className="bang"><thead><tr><th>Khách</th><th className="so">Doanh thu</th><th className="so">Nhịp</th><th>Lần cuối</th></tr></thead>
        <tbody>{ds.map(k => (<tr key={k.ma}><td><a className="ten-jp" href={lk(k.ma)}>{k.ten}</a></td>
          <td className="so">{yen(k.doanh_thu)}</td><td className="so">{k.nhip == null ? "—" : `${Math.round(k.nhip)} ngày`}</td>
          <td>{ngay(k.lan_cuoi)}</td></tr>))}</tbody></table>}
  </The>);
}
