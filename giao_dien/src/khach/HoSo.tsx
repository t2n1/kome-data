// Hồ sơ 360° (thiết kế lại 2026-09-26): thanh trên (← danh sách, ô chuyển
// khách, ‹ n/N ›) · đầu hồ sơ hai cột · cột trái "Việc với khách này" · cột
// phải sổ sức khoẻ + biểu đồ 12 tháng + 4 tab. Số THẬT từ
// /api/khach-hang/{mã} (kome/ho_so_khach.py). Khối không có nguồn: khung
// "chưa có dữ liệu" nói rõ thiếu gì.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { lay } from "../api";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../khung/khoang";
import { so } from "../dinh_dang";
import { docDanhSach } from "./loc";
import type { DsApi, HoSoApi } from "./kieu";
import { MAU_THANG, MAU_TT } from "./DanhSach";
import { BieuDo12Thang, OSoSucKhoe, TabCongNo, TabDonHang, TabHoSo, TabMatHang } from "./HoSoTab";
import { HoSoViec, ID_GHI_NHANH } from "./HoSoViec";
import { TAB_HO_SO, tabTuHash, type MaTabHoSo } from "./ho_so_logic";
import "./khach.css";
import { TN } from "../khoi_dau";

const TAB = TAB_HO_SO.filter(([m]) => m !== "cong_no" || TN.cong_no);

export default function HoSo({ ma }: { ma: string }) {
  const { data: h, error } = useQuery<HoSoApi>({
    queryKey: ["kh-ho-so", ma, chuoiKhoang(useKhoang())], queryFn: () => lay<HoSoApi>(voiKhoang(`/api/khach-hang/${encodeURIComponent(ma)}`)),
  });
  const [tab, datTab] = useState<MaTabHoSo>(() => tabTuHash(location.hash, TN.cong_no));
  const [moGhi, datMoGhi] = useState(false);
  useEffect(() => {
    const f = () => datTab(tabTuHash(location.hash, TN.cong_no));
    window.addEventListener("hashchange", f); return () => window.removeEventListener("hashchange", f);
  }, []);
  const chonTab = (t: MaTabHoSo) => { datTab(t); history.replaceState(null, "", "#" + t); };
  // Form ghi tiếp xúc của trang Jinja (/lien-he) gặp lỗi thì máy chủ quay về
  // đây kèm ?loi_tx=<câu lỗi> (POST /khach-hang/{mã}/tiep-xuc) — phải hiện ra.
  const loiTx = new URLSearchParams(location.search).get("loi_tx");
  const ds = docDanhSach();
  const vi = ds ? ds.ma.indexOf(ma) : -1;
  const di = (m: string) => { location.href = giuKhoang(`/khach-hang/${encodeURIComponent(m)}`); };
  useEffect(() => { if (h) document.title = `KOME — ${h.khach.ten}`; }, [h]);

  const thanhTren = (
    <div className="hs-tren">
      <a className="nut-nho" href={ds?.url ?? "/khach-hang"}>← Tất cả khách hàng</a>
      <ChuyenKhach />
      {vi >= 0 && ds && <span className="hs-tt">
        <button type="button" className="nut-nho" disabled={vi <= 0} onClick={() => di(ds.ma[vi - 1])} aria-label="Khách trước">‹</button>
        <span className="phu">{vi + 1}/{ds.ma.length}</span>
        <button type="button" className="nut-nho" disabled={vi >= ds.ma.length - 1} onClick={() => di(ds.ma[vi + 1])} aria-label="Khách sau">›</button>
      </span>}
    </div>);

  if (error) return <div className="kh">{thanhTren}<div className="khoi-loi">{(error as Error).message}</div></div>;
  if (!h) return <div className="kh">{thanhTren}<div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></div>;
  const k = h.khach, tn = h.thang_nay;

  return (
    <div className="kh hs hs2">
      {thanhTren}
      <header className="hs2-dau">
        <div className="hs2-dau-chu">
          <h1><span className="ten-jp">{k.ten}</span>
            {h.hang && <span className={"kh-hang-nhan lon h" + h.hang} title="hạng theo doanh thu 12 tháng">Hạng {h.hang}</span>}
            <span className={"nhan-vien " + (MAU_TT[k.trang_thai] ?? "nhat")}>{h.nhan_trang_thai[k.trang_thai] ?? k.trang_thai}</span>
            {tn && (tn.nhan === "tre" || tn.nhan === "da_mua" || tn.nhan === "chua_toi_ngay") && <span className={"nhan-vien " + (MAU_THANG[tn.nhan] ?? "nhat")}
              title={tn.nhan === "tre" ? h.cach_tinh_thang : undefined}>{h.nhan_thang[tn.nhan]}</span>}
          </h1>
          <div className="phu"><code>{k.ma}</code> · phụ trách <b>{(h.ho_so.ten_phu_trach as string) ?? k.nguoi_phu_trach ?? "— chưa giao —"}</b>
            {k.tinh && <> · <span className="ten-jp">{k.tinh}{k.thanh_pho ? " " + k.thanh_pho : ""}</span></>}
            {k.dien_thoai && <> · ☎ <a href={`tel:${k.dien_thoai}`}>{k.dien_thoai}</a></>}
            {k.dau_hieu_obc && <> · <span className="nhan-vien nhat">※{k.dau_hieu_obc}※</span></>}
            {h.hom_nay && <> · dữ liệu đến {h.hom_nay.split("-").reverse().join("/")}</>}</div>
          {h.the.length > 0 && <div className="hs2-the">{h.the.map(t => (
            <span key={t.chu} className={"nhan-vien " + (t.mau ?? "nhat")} title={t.vi}>{t.chu}</span>))}</div>}
        </div>
        <button type="button" className="nut-chinh" onClick={() => { datMoGhi(true);
          setTimeout(() => { const o = document.getElementById(ID_GHI_NHANH); o?.scrollIntoView({ behavior: "smooth", block: "center" }); o?.focus(); }, 50); }}>
          ✏️ Ghi liên hệ</button>
      </header>
      {loiTx && <p className="khoi-loi" role="alert">Chưa ghi được lần tiếp xúc: {loiTx}</p>}
      <div className="hs2-luoi">
        <HoSoViec h={h} moGhi={moGhi} datMoGhi={datMoGhi} />
        <div className="hs2-phai">
          <OSoSucKhoe h={h} />
          <BieuDo12Thang h={h} />
          <div className="hs-tab" role="tablist">
            {TAB.map(([m, nhan]) => (
              <button key={m} type="button" role="tab" aria-selected={tab === m} onClick={() => chonTab(m)}>
                {nhan}{m === "mat_hang" && h.o_so.so_ma_ngung > 0 && <span className="hs-cham" title={`${h.o_so.so_ma_ngung} mã đã ngừng mua`} />}
              </button>))}
          </div>
          <div role="tabpanel">
            {tab === "mat_hang" && <TabMatHang h={h} />}
            {tab === "don_hang" && <TabDonHang h={h} />}
            {tab === "cong_no" && <TabCongNo ma={k.ma} />}
            {tab === "ho_so" && <TabHoSo h={h} />}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Ô "Chuyển sang khách khác": tìm trên danh bạ (cùng API danh sách, mọi người phụ trách). */
function ChuyenKhach() {
  const [q, datQ] = useState(""), [tre, datTre] = useState("");
  const [mo, datMo] = useState(false);
  const o = useRef<HTMLDivElement>(null);
  useEffect(() => { const t = setTimeout(() => datTre(q.trim()), 250); return () => clearTimeout(t); }, [q]);
  useEffect(() => {
    const f = (e: MouseEvent) => { if (o.current && !o.current.contains(e.target as Node)) datMo(false); };
    document.addEventListener("mousedown", f); return () => document.removeEventListener("mousedown", f);
  }, []);
  const { data } = useQuery<DsApi>({
    queryKey: ["kh-tim", tre], enabled: tre.length >= 1,
    queryFn: () => lay<DsApi>(`/api/khach-hang/ds?nv=__moi_nguoi&tim=${encodeURIComponent(tre)}`),
  });
  const kq = data?.trang.khach.slice(0, 8) ?? [];
  return (
    <div className="hs-tim" ref={o}>
      <input type="search" placeholder="Chuyển sang khách khác — gõ mã hoặc tên…" value={q} aria-label="Chuyển sang khách khác"
        onChange={e => { datQ(e.target.value); datMo(true); }} onFocus={() => datMo(true)}
        onKeyDown={e => { if (e.key === "Enter" && kq[0]) location.href = giuKhoang(`/khach-hang/${encodeURIComponent(kq[0].ma)}`); if (e.key === "Escape") datMo(false); }} />
      {mo && tre && data && <div className="hs-tim-kq" role="listbox">
        <div className="phu">{so(data.trang.tong)} khách khớp "{tre}"</div>
        {kq.map(k => (
          <a key={k.ma} href={`/khach-hang/${encodeURIComponent(k.ma)}`} role="option">
            <i className={"cham " + (MAU_TT[k.trang_thai] ?? "nhat")} /><span className="ten-jp">{k.ten}</span>
            <span className="phu">{k.ma}{k.hang ? ` · ${k.hang}` : ""}</span></a>))}
      </div>}
    </div>
  );
}
