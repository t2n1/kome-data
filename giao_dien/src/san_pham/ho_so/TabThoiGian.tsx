// Tab "Thời gian" của Sản phẩm 360 — TẠM (Task 6). `BanTheoNgay` và `XuHuong`
// chép NGUYÊN từ HoSoSanPham.tsx (đã xoá) để Task 7 dựng tab thật từ
// /api/san-pham/{mã}/thoi-gian (TabThoiGianApi) — chưa dùng ở đây nên xuất ra
// (export) để qua được `noUnusedLocals`, không phải vì chúng đã là API công khai.
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { useState } from "react";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { gon, ngay, so, so_luong as soLuong, thang_nhan, thay_doi, yen } from "../../dinh_dang";
import type { HoSoSpApi, NgayApi } from "../kieu";

const CHI_SO = [["so_luong", "Số lượng"], ["doanh_thu", "Doanh thu"], ["lai_gop", "Lãi gộp"]] as const;
type ChiSo = typeof CHI_SO[number][0];

export function BanTheoNgay({ ma, thang, ds_thang, datThang }: { ma: string; thang: string | null; ds_thang: string[]; datThang: (t: string) => void }) {
  const [cs, datCs] = useState<ChiSo>("so_luong");
  const { data, error, isFetching } = useQuery<NgayApi>({
    queryKey: ["sp-ngay", ma, thang], enabled: !!thang, placeholderData: keepPreviousData,
    queryFn: () => lay<NgayApi>(`/api/san-pham/${encodeURIComponent(ma)}/ngay?thang=${thang}`),
  });
  if (!thang) return <section className="kh-the sp-ngay" id="sp-ngay"><div className="kh-the-dau"><h2>Lượng bán theo ngày</h2></div>
    <p className="trong-nho">Mã này chưa từng có dòng bán.</p></section>;
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
  const iThang = ds_thang.indexOf(thang);
  // Cột nhạt = CÙNG NGÀY của tháng trước (ngày 31 không có ở tháng trước thì trống).
  const theoNgay = new Map(t.map(d => [+d.ngay.slice(8, 10), d]));

  return (
    <section className={"kh-the sp-ngay" + (isFetching ? " dang-tai" : "")} id="sp-ngay">
      <div className="kh-the-dau">
        <h2>Lượng bán theo ngày</h2>
        <span className="phu">tháng {tmoi}/{thang.slice(0, 4)}{mocNgay ? ` · đến ngày ${mocNgay}` : ""} · cột nhạt là cùng ngày tháng {ttruoc}</span>
        <span className="sp-thang-chon">
          <button type="button" className="nut-nho" disabled={iThang <= 0} onClick={() => datThang(ds_thang[iThang - 1])} aria-label="Tháng trước">‹</button>
          <select value={thang} onChange={e => datThang(e.target.value)} aria-label="Chọn tháng">
            {[...ds_thang].reverse().map(x => <option key={x} value={x}>Tháng {+x.slice(5)}/{x.slice(0, 4)}</option>)}</select>
          <button type="button" className="nut-nho" disabled={iThang < 0 || iThang >= ds_thang.length - 1} onClick={() => datThang(ds_thang[iThang + 1])} aria-label="Tháng sau">›</button>
        </span>
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
        <p className="phu sp-ghi">Cột xám = ngày nghỉ (thứ Bảy, Chủ nhật, ngày lễ — <code>mart.lich_kinh_doanh</code>). Ngày không có phiếu là 0. Bấm một tháng ở "Xu hướng theo tháng" bên dưới để xem tháng đó.</p>
      </>}
    </section>
  );
}

export function XuHuong({ h, chon, datThang }: { h: HoSoSpApi["h"]; chon: string | null; datThang: (t: string) => void }) {
  if (!h.thang.length) return null;
  const i = chon ? h.thang.findIndex(t => t.thang === chon) : -1;
  return (
    <section className="kh-the sp-xu-huong">
      <div className="kh-the-dau"><h2>Xu hướng theo tháng</h2>
        <span className="kh-the-goc nhat-chu">{thang_nhan(h.thang[0].thang)} → {thang_nhan(h.thang[h.thang.length - 1].thang)} · bấm một tháng để xem theo ngày</span></div>
      <BieuDo nhan={h.thang.map(t => thang_nhan(t.thang))} nhan_day_du={h.thang.map(t => `Tháng ${+t.thang.slice(5)}/${t.thang.slice(0, 4)}`)} cao={180}
        mo_ta="Doanh thu và lãi gộp theo tháng của mã này" onBam={k => datThang(h.thang[k].thang)}
        chuoi={[
          { ten: "Doanh thu", kieu: "cot", mau: "var(--lien-ket)", mau_tung_cot: h.thang.map((_, k) => k === i ? "var(--do)" : null),
            gia_tri: h.thang.map(t => t.doanh_thu == null ? null : Number(t.doanh_thu)) },
          { ten: "Lãi gộp", kieu: "duong", mau: "var(--ok-vien)", gia_tri: h.thang.map(t => t.lai_gop == null ? null : Number(t.lai_gop)) },
          { ten: "Số lượng", kieu: "duong_dut", mau: "var(--canh-vien)", truc_phai: true, an_mac_dinh: true,
            gia_tri: h.thang.map(t => t.so_luong == null ? null : Number(t.so_luong)) },
        ]}
        dinh_dang={(v, c) => c.ten === "Số lượng" ? soLuong(v) : yen(v)} dinh_dang_truc={v => gon(v)} />
    </section>
  );
}

export function TabThoiGian(_: { ma: string; thang: string | null }) { return <p className="phu">Đang dựng…</p>; }
