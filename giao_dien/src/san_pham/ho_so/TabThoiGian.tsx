// Tab Thời gian — bán theo ngày (khối cũ, /ngay) · 26 tuần · nhịp mua lại · cỡ đơn.
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, useKhoang, voiKhoang } from "../../khung/khoang";
import { gon, ngay, so, so_luong as soLuong, thay_doi, yen } from "../../dinh_dang";
import type { NgayApi } from "../kieu";
import type { TabThoiGianApi } from "./kieu";

const CHI_SO = [["so_luong", "Số lượng"], ["doanh_thu", "Doanh thu"], ["lai_gop", "Lãi gộp"]] as const;
type ChiSo = typeof CHI_SO[number][0];

const NHAN_NHIP: Record<string, string> = { "≤7": "≤ 7 ngày", "8–14": "8–14", "15–30": "15–30", "31–60": "31–60", ">60": "> 60", chua_du: "chưa đủ 3 lần" };
const NHAN_CO: Record<string, string> = { tra_lai: "trả lại (赤伝)", khong_sl: "không số lượng" };

function BanTheoNgay({ ma, thangDau }: { ma: string; thangDau: string }) {
  const [thang, datThang] = useState(thangDau);
  useEffect(() => { datThang(thangDau); }, [thangDau]);
  const [cs, datCs] = useState<ChiSo>("so_luong");
  const { data, error, isFetching } = useQuery<NgayApi>({
    queryKey: ["sp-ngay", ma, thang], placeholderData: keepPreviousData,
    queryFn: () => lay<NgayApi>(`/api/san-pham/${encodeURIComponent(ma)}/ngay?thang=${thang}`),
  });
  const n = data?.nay ?? [], t = data?.truoc ?? [];
  const mocNgay = data?.hom_nay && data.hom_nay.slice(0, 7) === thang ? +data.hom_nay.slice(8, 10) : null;
  const trongMoc = (d: { ngay: string }) => mocNgay == null || +d.ngay.slice(8, 10) <= mocNgay;
  const tong = (ds: typeof n, k: ChiSo) => ds.filter(trongMoc).reduce((s, d) => s + d[k], 0);
  const nay = tong(n, cs), truoc = tong(t, cs);
  const ss = truoc ? nay / truoc - 1 : null;
  const dinh = n.reduce<(typeof n)[number] | null>((a, d) => (!a || d[cs] > a[cs] ? d : a), null);
  const ngayCoBan = n.filter(d => d.so_luong !== 0).length;
  const fmt = (v: number | null) => v == null ? "—" : cs === "so_luong" ? soLuong(v) : yen(v);
  const tmoi = +thang.slice(5), ttruoc = tmoi === 1 ? 12 : tmoi - 1;
  // Cột nhạt = CÙNG NGÀY của tháng trước (ngày 31 không có ở tháng trước thì trống).
  const theoNgay = new Map(t.map(d => [+d.ngay.slice(8, 10), d]));

  return (
    <section className={"kh-the sp-ngay" + (isFetching ? " dang-tai" : "")} id="sp-ngay">
      <div className="kh-the-dau">
        <h2>Lượng bán theo ngày</h2>
        <span className="phu">tháng {tmoi}/{thang.slice(0, 4)}{mocNgay ? ` · đến ngày ${mocNgay}` : ""} · cột nhạt là cùng ngày tháng {ttruoc}</span>
        <span className="tab-pill" role="group" aria-label="Chỉ số">
          {CHI_SO.map(([k, nhan]) => <button key={k} type="button" aria-pressed={cs === k} onClick={() => datCs(k)}>{nhan}</button>)}</span>
      </div>
      {error ? <div className="khoi-loi">{(error as Error).message}</div> : !data ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div> : <>
        <div className="so-khoi sp-ngay-o">
          <div><div className="nhan">{CHI_SO.find(c => c[0] === cs)![1]} tháng {tmoi}{mocNgay ? ` (1–${mocNgay})` : ""}</div><div className="gia">{fmt(nay)}</div></div>
          <div><div className="nhan">So tháng {ttruoc} {mocNgay ? "cùng ngày" : "cả tháng"}</div>
            <div className={"gia " + (ss == null ? "nhat-chu" : ss >= 0 ? "tang" : "giam")}>{ss == null ? "—" : thay_doi(ss)}</div>
            <div className="phu">tháng {ttruoc}: {fmt(truoc)}</div></div>
          <div><div className="nhan">Ngày bán nhiều nhất</div><div className="gia">{dinh && dinh[cs] ? fmt(dinh[cs]) : "—"}</div>
            <div className="phu">{dinh && dinh[cs] ? ngay(dinh.ngay) : "không có ngày nào có đơn"}</div></div>
          <div><div className="nhan">Số ngày có đơn</div><div className="gia">{so(ngayCoBan)}</div>
            <div className="phu">trên {so(n.filter(d => d.la_ngay_kd && trongMoc(d)).length)} ngày làm việc</div></div>
        </div>
        <BieuDo nhan={n.map(d => String(+d.ngay.slice(8, 10)))}
          nhan_day_du={n.map(d => `${ngay(d.ngay)}${d.la_ngay_kd ? "" : " · ngày nghỉ"}`)} cao={190} moi_nhan={n.length > 20 ? 2 : 1}
          mo_ta={`Lượng bán theo ngày của mã ${ma}, tháng ${tmoi}/${thang.slice(0, 4)}`}
          chuoi={[
            { ten: `Tháng ${ttruoc} cùng ngày`, kieu: "cot_nen", mau: "var(--do-nen)",
              gia_tri: n.map(d => theoNgay.get(+d.ngay.slice(8, 10))?.[cs] ?? null) },
            { ten: `Tháng ${tmoi}`, kieu: "cot", mau: "var(--do)",
              mau_tung_cot: n.map(d => d.la_ngay_kd ? null : "var(--chu-mo)"),
              gia_tri: n.map(d => mocNgay != null && +d.ngay.slice(8, 10) > mocNgay ? null : d[cs]) },
          ]}
          dinh_dang={v => fmt(v)} dinh_dang_truc={v => cs === "so_luong" ? soLuong(v, 0) : gon(v)}
          vach={mocNgay ? { i: mocNgay - 1, chu: "mốc dữ liệu" } : null} />
        <p className="phu sp-ghi">Cột xám = ngày nghỉ (thứ Bảy, Chủ nhật, ngày lễ — <code>mart.lich_kinh_doanh</code>). Ngày không có phiếu là 0.</p>
      </>}
    </section>
  );
}

export function TabThoiGian({ ma, thang }: { ma: string; thang: string | null }) {
  const kx = chuoiKhoang(useKhoang());
  const { data, error } = useQuery<TabThoiGianApi>({ queryKey: ["sp360-tg", ma, kx],
    queryFn: () => lay<TabThoiGianApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/thoi-gian`)) });
  return (<>
    {thang && <BanTheoNgay ma={ma} thangDau={thang} />}
    {error ? <div className="khoi-loi">Không tải được tab Thời gian: {(error as Error).message}</div> :
     !data ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div> : <>
      <The tieu_de="26 tuần" cach_tinh={data.cach_tinh.tuan}>
        <BieuDo nhan={data.t.tuan.map(x => x.tuan.slice(5).split("-").reverse().join("/"))} cao={180} moi_nhan={2}
          chuoi={[{ ten: "Số lượng", kieu: "cot", gia_tri: data.t.tuan.map(x => x.so_luong), mau: "var(--ok-vien)" },
                  { ten: "Doanh thu", kieu: "duong", gia_tri: data.t.tuan.map(x => x.doanh_thu), mau: "var(--lien-ket)", truc_phai: true, an_mac_dinh: true }]}
          dinh_dang={(v, c) => c.truc_phai ? yen(v) : soLuong(v)} mo_ta="Số lượng bán theo tuần, 26 tuần gần nhất" />
      </The>
      <div className="sp3-luoi-2">
        <The tieu_de="Nhịp mua lại của khách" cach_tinh={data.cach_tinh.nhip}>
          <BieuDo nhan={data.t.nhip.map(x => NHAN_NHIP[x.nhom] ?? x.nhom)} cao={170}
            chuoi={[{ ten: "Số cặp khách–mã", kieu: "cot", gia_tri: data.t.nhip.map(x => x.so_cap), mau: "var(--ok-vien)" }]}
            dinh_dang={v => so(v)} mo_ta="Phân bố nhịp mua lại (ngày) của các khách mua mã này" />
        </The>
        <The tieu_de="Cỡ đơn mỗi lần mua" cach_tinh={data.cach_tinh.co_don}>
          {!data.t.co_don.length ? <p className="phu">Chưa bán trong 12 tháng.</p> :
            <table className="bang"><thead><tr><th>Quy cách</th><th>Số lượng / dòng</th><th className="so">Số dòng</th><th className="so">Tổng SL</th></tr></thead>
              <tbody>{data.t.co_don.map(x => (<tr key={x.pack_code + x.nhom}>
                <td>{x.quy_cach}</td><td>{NHAN_CO[x.nhom] ?? x.nhom}</td><td className="so">{so(x.so_dong)}</td><td className="so">{soLuong(x.so_luong)}</td></tr>))}</tbody></table>}
        </The>
      </div></>}
  </>);
}
