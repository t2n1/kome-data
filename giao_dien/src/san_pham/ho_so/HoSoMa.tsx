// Sản phẩm 360 — trang riêng (đặc tả 2026-09-26-san-pham-360-trang-rieng-design.md). Bố cục
// như hồ sơ khách 360 (khach/HoSo.tsx): thanh trên · đầu trang · HAI CỘT (hs2-luoi): cột trái dính
// "Việc với mã này" (ViecVoiMa.tsx), cột phải = 4 ô số + 24 tháng + 4 tab tải lười.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { lay } from "../../api";
import { BieuDo } from "../../chung/BieuDo";
import { DongSoSanh } from "../../chung/SoSanh";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang, useNhanMoc, voiKhoang } from "../../khung/khoang";
import { ngay, pc, so, so_luong as soLuong, yen } from "../../dinh_dang";
import { docDanhMuc, docLocSp, khopTim, locDanhMuc } from "../loc";
import { useDanhMucGhep } from "../ManSanPham";
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

  // ‹ n/N ›: thứ tự danh mục vừa xem (sessionStorage); không có thì thứ tự MẶC ĐỊNH của danh mục
  // (bộ lọc rỗng, sắp mặc định) trên CÙNG ảnh chụp /api/san-pham mà màn danh mục đọc.
  const { d: dm } = useDanhMucGhep();
  const nho = useMemo(() => docDanhMuc(), []);
  const ds = useMemo(() => nho ?? (dm ? { ma: locDanhMuc(dm.ma, docLocSp(""), dm.trang_thai).hang.map(m => m.ma), url: "/san-pham" } : null),
    [nho, dm]);
  const vi = ds ? ds.ma.indexOf(ma) : -1;
  const di = (m: string) => { location.href = giuKhoang(`/san-pham/${encodeURIComponent(m)}`); };
  const thanhTren = (
    <div className="hs-tren">
      <a className="nut-nho" href={giuKhoang(ds?.url ?? "/san-pham")}>← Danh mục sản phẩm</a>
      <ChuyenMa ds={dm?.ma ?? null} />
      {vi >= 0 && ds && <span className="hs-tt">
        <button type="button" className="nut-nho" disabled={vi <= 0} onClick={() => di(ds.ma[vi - 1])} aria-label="Mã trước">‹</button>
        <span className="phu">{vi + 1}/{ds.ma.length}</span>
        <button type="button" className="nut-nho" disabled={vi >= ds.ma.length - 1} onClick={() => di(ds.ma[vi + 1])} aria-label="Mã sau">›</button>
      </span>}
    </div>);

  if (error) return <div className="kh">{thanhTren}<div className="khoi-loi">{(error as Error).message}</div></div>;
  if (!data) return <div className="kh">{thanhTren}<div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></div>;
  const h = data.h, sp = h.sp;
  // Danh sách tháng cho bộ chọn "Lượng bán theo ngày" — chỉ tháng CÓ bán, trừ khi
  // không tháng nào có (mã chưa từng bán) thì cho chọn cả 24 tháng.
  const coBan = h.thang.filter(x => x.so_luong !== 0 || x.doanh_thu !== 0).map(x => x.thang);
  const dsThang = coBan.length ? coBan : h.thang.map(x => x.thang);

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
              {kh === undefined ? <div className="dong-phu nhat-chu">…</div> : kh === null ? <div className="dong-phu nhat-chu">—</div>
                : <DongSoSanh nhan={kh.so_sanh.nhan} co={kh.so_sanh.co} nay={kh.tong.dt} ss={kh.dt_ss} dinh_dang={yen} />}</div>
            <div className="o-kpi"><div className="nhan">Bán / ngày (theo tuổi)</div>
              <div className="gia">{sp.toc_do_ngay_theo_tuoi == null ? "—" : soLuong(sp.toc_do_ngay_theo_tuoi)}</div>
              <div className="dong-phu nhat-chu">90 ngày, chia cho số ngày mã có mặt</div></div>
            <div className="o-kpi"><div className="nhan">Biên lãi gộp 12 tháng</div>
              <div className="gia">{pc(h.bien_12t)}</div>
              <div className="dong-phu nhat-chu">DT 12 tháng {yen(h.dt_12t)}</div></div>
            <div className="o-kpi"><div className="nhan">Khách đang mua / đã ngừng</div>
              <div className="gia">{so(h.so_dang_mua)} / {so(h.so_da_ngung)}</div>
              <div className="dong-phu nhat-chu">theo cặp khách–mã này</div></div>
          </div>
          {/* Kỳ so (đặc tả 2026-09-28) = CỘT MA theo `thang_ss` của /khoang (tháng dời
              `lech_thang`); chưa tải xong / không so theo tháng được thì không vẽ cột so. */}
          <The tieu_de="24 tháng" cach_tinh={<>{h.cach_tinh.thang}{kh ? (kh.thang_ss ? <> Cột viền đứt = {kh.so_sanh.nhan} (cùng vị trí tháng).</>
            : <> {kh.so_sanh.nhan}: không so theo tháng được.</>) : null}</>}>
            <BieuDo nhan={h.thang.map(x => `${+x.thang.slice(5)}/${x.thang.slice(2, 4)}`)} cao={220} moi_nhan={2}
              chuoi={[
                { ten: "Doanh thu", kieu: "cot", gia_tri: h.thang.map(x => x.doanh_thu), mau: "var(--ok-vien)", so_voi: kh?.thang_ss ? 2 : undefined },
                { ten: "Lãi gộp", kieu: "duong", gia_tri: h.thang.map(x => x.lai_gop), mau: "var(--lien-ket)" },
                ...(kh?.thang_ss ? [{ ten: kh.so_sanh.nhan.replace(/^./, c => c.toUpperCase()), kieu: "cot_ma" as const,
                  gia_tri: h.thang.map(x => kh.thang_ss![x.thang] ?? null), mau: "var(--vien-dam)" }] : []),
              ]}
              dinh_dang={v => yen(v)} dinh_dang_truc={v => yen(v)}
              onBam={i => { datThangNgay(h.thang[i].thang); chonTab("thoi_gian"); }}
              mo_ta={`Doanh thu và lãi gộp 24 tháng, cột viền đứt là ${kh?.so_sanh.nhan ?? "kỳ so"}; bấm một tháng để xem theo ngày`} />
          </The>
          <div className="hs-tab" role="tablist">
            {TAB.map(([m, nhan]) => (
              <button key={m} type="button" role="tab" aria-selected={tab === m} onClick={() => chonTab(m)}>{nhan}</button>))}
          </div>
          <div role="tabpanel">
            {tab === "khach" && <TabKhach ma={ma} khoang={kh ?? null} />}
            {tab === "thoi_gian" && <TabThoiGian ma={ma} thang={thangNgay ?? h.hom_nay?.slice(0, 7) ?? null}
              dsThang={dsThang} chuaTungBan={!sp.lan_cuoi} />}
            {tab === "gia" && <TabGia ma={ma} thang={h.thang} />}
            {tab === "ban_them" && <TabBanThem ma={ma} ngungBan={h.ngung_ban} nganh={h.nganh} />}
          </div>
        </div>
      </div>
    </div>);
}

/** Ô "Chuyển sang mã khác": tìm mã / tên / ngành trên ảnh chụp danh mục (lọc ở trình duyệt,
 *  cùng `khopTim` của màn danh mục — không hỏi thêm máy chủ). */
function ChuyenMa({ ds }: { ds: { ma: string; ten: string; nganh: string; nhan_trang_thai: string }[] | null }) {
  const [q, datQ] = useState("");
  const [mo, datMo] = useState(false);
  const o = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const f = (e: MouseEvent) => { if (o.current && !o.current.contains(e.target as Node)) datMo(false); };
    document.addEventListener("mousedown", f); return () => document.removeEventListener("mousedown", f);
  }, []);
  const tim = q.trim();
  const khop = useMemo(() => (tim && ds ? ds.filter(m => khopTim(m, tim)) : []), [ds, tim]);
  const kq = khop.slice(0, 8);
  const di = (m: string) => { location.href = giuKhoang(`/san-pham/${encodeURIComponent(m)}`); };
  return (
    <div className="hs-tim" ref={o}>
      <input type="search" placeholder="Chuyển sang mã khác — gõ mã, tên hoặc ngành…" value={q} aria-label="Chuyển sang mã khác"
        onChange={e => { datQ(e.target.value); datMo(true); }} onFocus={() => datMo(true)}
        onKeyDown={e => { if (e.key === "Enter" && kq[0]) di(kq[0].ma); if (e.key === "Escape") datMo(false); }} />
      {mo && tim && <div className="hs-tim-kq" role="listbox">
        <div className="phu">{ds ? `${so(khop.length)} mã khớp "${tim}"` : "Đang tải danh mục…"}</div>
        {kq.map(m => (
          <a key={m.ma} href={giuKhoang(`/san-pham/${encodeURIComponent(m.ma)}`)} role="option">
            <span className="ten-jp">{m.ten}</span><span className="phu">{m.ma} · {m.nganh}</span></a>))}
      </div>}
    </div>
  );
}
