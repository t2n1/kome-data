// Sản phẩm 360 — trang riêng (đặc tả 2026-09-26-san-pham-360-trang-rieng-design.md). Bố cục
// như hồ sơ khách 360 (khach/HoSo.tsx): thanh trên · đầu trang · HAI CỘT (hs2-luoi): cột trái dính
// "Việc với mã này" (ViecVoiMa.tsx), cột phải = 4 ô số + 24 tháng + 4 tab tải lười.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, useNhanMoc, voiKhoang } from "../../khung/khoang";
import { ngay, pc, so, so_luong as soLuong, thay_doi, yen } from "../../dinh_dang";
import { docDanhMuc } from "../loc";
import type { KhoangMaApi } from "../kieu";
import type { HoSoMaApi } from "./kieu";
import { ViecVoiMa } from "./ViecVoiMa";
import { TabKhach } from "./TabKhach";
import { TabThoiGian } from "./TabThoiGian";
import { TabGia } from "./TabGia";
import { TabBanThem } from "./TabBanThem";
import "../../khach/khach.css";
import "../san_pham.css";
import "./ho_so.css";

const TAB = [["khach", "Khách hàng"], ["thoi_gian", "Thời gian"], ["gia", "Giá & lãi"], ["ban_them", "Tồn & bán thêm"]] as const;
type MaTab = (typeof TAB)[number][0];
const tabTuHash = (h: string): MaTab => (TAB.find(([m]) => "#" + m === h)?.[0] ?? "khach");

export default function HoSoMa({ ma }: { ma: string }) {
  const kx = chuoiKhoang(useKhoang());
  const nhanMoc = useNhanMoc();
  const { data, error } = useQuery<HoSoMaApi>({ queryKey: ["sp360", ma, kx],
    queryFn: () => lay<HoSoMaApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}`)) });
  const { data: kh } = useQuery<KhoangMaApi>({ queryKey: ["sp-ma-khoang", ma, kx],
    queryFn: () => lay<KhoangMaApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/khoang`)) });
  const [tab, datTab] = useState<MaTab>(() => tabTuHash(location.hash));
  const [thangNgay, datThangNgay] = useState<string | null>(null);
  useEffect(() => { const f = () => datTab(tabTuHash(location.hash));
    addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  const chonTab = (t: string) => { datTab(t as MaTab); history.replaceState(null, "", giuKhoang(location.pathname + location.search) + "#" + t); };
  useEffect(() => { if (data) document.title = `KOME — ${data.h.sp.ten}`; }, [data]);

  const ds = docDanhMuc();
  const vi = ds ? ds.ma.indexOf(ma) : -1;
  const di = (m: string) => { location.href = giuKhoang(`/san-pham/${encodeURIComponent(m)}`); };
  const thanhTren = (
    <div className="hs-tren">
      <a className="nut-nho" href={giuKhoang(ds?.url ?? "/san-pham")}>← Danh mục sản phẩm</a>
      {vi >= 0 && ds && <span className="hs-tt">
        <button type="button" className="nut-nho" disabled={vi <= 0} onClick={() => di(ds.ma[vi - 1])} aria-label="Mã trước">‹</button>
        <span className="phu">{vi + 1}/{ds.ma.length}</span>
        <button type="button" className="nut-nho" disabled={vi >= ds.ma.length - 1} onClick={() => di(ds.ma[vi + 1])} aria-label="Mã sau">›</button>
      </span>}
    </div>);

  if (error) return <div className="kh">{thanhTren}<div className="khoi-loi">{(error as Error).message}</div></div>;
  if (!data) return <div className="kh">{thanhTren}<div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></div>;
  const h = data.h, sp = h.sp;

  return (
    <div className="kh hs hs2 sp3">
      {thanhTren}
      <header className="hs2-dau"><div className="hs2-dau-chu">
        <h1><span className="ten-jp">{sp.ten}</span>
          <span className="nhan-vien nhat">{h.nganh}</span>
          {h.ngung_ban && <span className="nhan-vien canh">bán nốt tồn</span>}</h1>
        <div className="phu"><code>{sp.ma}</code> · bán lần đầu {ngay(sp.lan_dau)} · lần cuối {ngay(sp.lan_cuoi)}
          {h.hom_nay && <> · dữ liệu {nhanMoc} {ngay(h.hom_nay)}</>}</div>
      </div></header>
      <div className="hs2-luoi">
        <ViecVoiMa h={h} moTab={chonTab} />
        <div className="hs2-phai">
          <div className="o-kpi-luoi hs2-o">
            <div className="o-kpi"><div className="nhan">Doanh thu · {kh?.khoang.nhan ?? "khoảng xem"}</div>
              <div className="gia">{kh === undefined ? "…" : kh === null ? "—" : yen(kh.tong.dt)}</div>
              <div className={"dong-phu " + (kh && kh.so_sanh.co && kh.tang != null ? (kh.tang >= 0 ? "tang" : "giam") : "nhat-chu")}>
                {kh === undefined ? "…" : kh === null ? "—"
                  : kh.so_sanh.co && kh.tang != null ? `${thay_doi(kh.tang)} so ${kh.so_sanh.nhan}` : "không có dữ liệu để so"}</div></div>
            <div className="o-kpi"><div className="nhan">Bán / ngày (theo tuổi)</div>
              <div className="gia">{sp.toc_do_ngay_theo_tuoi == null ? "—" : soLuong(sp.toc_do_ngay_theo_tuoi)}</div>
              <div className="dong-phu nhat-chu">90 ngày, chia cho số ngày mã có mặt</div></div>
            <div className="o-kpi"><div className="nhan">Biên lãi gộp 12 tháng</div>
              <div className="gia">{h.dt_12t > 0 ? pc(h.lg_12t / h.dt_12t) : "—"}</div>
              <div className="dong-phu nhat-chu">DT 12 tháng {yen(h.dt_12t)}</div></div>
            <div className="o-kpi"><div className="nhan">Khách đang mua / đã ngừng</div>
              <div className="gia">{so(h.so_dang_mua)} / {so(h.so_da_ngung)}</div>
              <div className="dong-phu nhat-chu">theo cặp khách–mã này</div></div>
          </div>
          <The tieu_de="24 tháng" cach_tinh={h.cach_tinh.thang}>
            <BieuDo nhan={h.thang.map(x => `${+x.thang.slice(5)}/${x.thang.slice(2, 4)}`)} cao={220} moi_nhan={2}
              chuoi={[
                { ten: "Cùng tháng năm trước", kieu: "cot_nen", gia_tri: h.thang.map(x => x.dt_nam_truoc), mau: "var(--chu-mo)" },
                { ten: "Doanh thu", kieu: "cot", gia_tri: h.thang.map(x => x.doanh_thu), mau: "var(--ok-vien)" },
                { ten: "Lãi gộp", kieu: "duong", gia_tri: h.thang.map(x => x.lai_gop), mau: "var(--lien-ket)" },
              ]}
              dinh_dang={v => yen(v)} dinh_dang_truc={v => yen(v)}
              onBam={i => { datThangNgay(h.thang[i].thang); chonTab("thoi_gian"); }}
              mo_ta="Doanh thu và lãi gộp 24 tháng, cột mờ là cùng tháng năm trước; bấm một tháng để xem theo ngày" />
          </The>
          <div className="hs-tab" role="tablist">
            {TAB.map(([m, nhan]) => (
              <button key={m} type="button" role="tab" aria-selected={tab === m} onClick={() => chonTab(m)}>{nhan}</button>))}
          </div>
          <div role="tabpanel">
            {tab === "khach" && <TabKhach ma={ma} khoang={kh ?? null} />}
            {tab === "thoi_gian" && <TabThoiGian ma={ma} thang={thangNgay ?? h.hom_nay?.slice(0, 7) ?? null} />}
            {tab === "gia" && <TabGia ma={ma} thang={h.thang} />}
            {tab === "ban_them" && <TabBanThem ma={ma} ngungBan={h.ngung_ban} nganh={h.nganh} />}
          </div>
        </div>
      </div>
    </div>);
}
