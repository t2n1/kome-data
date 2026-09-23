// Hồ sơ 360° (Customer 360.dc.html — màn chi_tiet): thanh trên (← danh sách,
// ô chuyển khách, ‹ n/N ›) · đầu hồ sơ · câu diễn giải · 5 tab. Số THẬT từ
// /api/khach-hang/{mã} (kome/ho_so_khach.py). Khối không có nguồn: khung
// "chưa có dữ liệu" nói rõ thiếu gì.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { lay } from "../api";
import { so } from "../dinh_dang";
import { docDanhSach } from "./loc";
import type { DsApi, HoSoApi } from "./kieu";
import { MAU_THANG, MAU_TT } from "./DanhSach";
import { TabCongNo, TabDonHang, TabHoSo, TabSanPham, TabTongQuan } from "./HoSoTab";
import "./khach.css";

const TAB = [["tong_quan", "Tổng quan"], ["san_pham", "Sản phẩm"], ["don_hang", "Đơn hàng"],
  ["cong_no", "Công nợ"], ["ho_so", "Hồ sơ & liên hệ"]] as const;
type MaTab = typeof TAB[number][0];

export default function HoSo({ ma }: { ma: string }) {
  const { data: h, error } = useQuery<HoSoApi>({
    queryKey: ["kh-ho-so", ma], queryFn: () => lay<HoSoApi>(`/api/khach-hang/${encodeURIComponent(ma)}`),
  });
  const [tab, datTab] = useState<MaTab>(() => {
    const t = location.hash.slice(1) as MaTab;
    return TAB.some(x => x[0] === t) ? t : "tong_quan";
  });
  // Form ghi tiếp xúc của trang Jinja (/lien-he) gặp lỗi thì máy chủ quay về
  // đây kèm ?loi_tx=<câu lỗi> (POST /khach-hang/{mã}/tiep-xuc) — phải hiện ra.
  const loiTx = new URLSearchParams(location.search).get("loi_tx");
  const chonTab = (t: MaTab) => { datTab(t); history.replaceState(null, "", "#" + t); };
  const ds = docDanhSach();
  const vi = ds ? ds.ma.indexOf(ma) : -1;
  const di = (m: string) => { location.href = `/khach-hang/${encodeURIComponent(m)}`; };
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
    <div className="kh hs">
      {thanhTren}
      <div className="tieu-de-trang hs-dau">
        <div>
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
        </div>
        <button type="button" className="nut-chinh" onClick={() => { chonTab("ho_so"); setTimeout(() => document.getElementById("ghi-tx")?.focus(), 50); }}>✏️ Ghi liên hệ</button>
      </div>
      {loiTx && <p className="khoi-loi" role="alert">Chưa ghi được lần tiếp xúc: {loiTx}</p>}
      {h.dien_giai && <div className="hs-dien-giai">{h.dien_giai}</div>}

      <div className="hs-tab" role="tablist">
        {TAB.map(([m, nhan]) => (
          <button key={m} type="button" role="tab" aria-selected={tab === m} onClick={() => chonTab(m)}>
            {nhan}
            {m === "san_pham" && h.o_so.so_ma_ngung > 0 && <span className="hs-cham" title={`${h.o_so.so_ma_ngung} mã đã ngừng mua`} />}
          </button>))}
      </div>
      <div role="tabpanel">
        {tab === "tong_quan" && <TabTongQuan h={h} />}
        {tab === "san_pham" && <TabSanPham h={h} />}
        {tab === "don_hang" && <TabDonHang h={h} />}
        {tab === "cong_no" && <TabCongNo ma={k.ma} />}
        {tab === "ho_so" && <TabHoSo h={h} />}
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
        onKeyDown={e => { if (e.key === "Enter" && kq[0]) location.href = `/khach-hang/${encodeURIComponent(kq[0].ma)}`; if (e.key === "Escape") datMo(false); }} />
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
