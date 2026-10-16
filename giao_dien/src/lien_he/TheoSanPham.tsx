// Cần gọi — THEO SẢN PHẨM (2026-10-16, chủ DN: "sale sản phẩm đó thì có những khách nào cần gọi").
// Chọn ≤ 5 mã (?ma=A,B) → ba nhóm khách: đến lúc mua lại · đã ngừng mua mã này · chưa mua — nên chào.
// Định nghĩa ở máy chủ (kome/lien_he.py::theo_san_pham — đọc nhãn cặp khách–mã và mart.sp_khach_nen_chao);
// trang chỉ vẽ. "Nên chào" chậm (~1,4 s mỗi mã) nên hỏi bản nhanh (?nhanh=1) trước, bản đủ thay vào sau.
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { lay } from "../api";
import { HinhMa } from "../chung/HinhMa";
import { ChuThich } from "../chung/Khoi";
import { gon, ngay, so, yen } from "../dinh_dang";
import { GhiTiepXuc } from "../khach/GhiTiepXuc";
import { dauKichBan, kichBanGoi } from "../khach/kich_ban";
import { useDanhMuc } from "../san_pham/ManSanPham";
import { bo_dau } from "../san_pham/loc";

type Ltx = { kieu: string; ket_qua: string; noi_dung: string; hen_lai: string | null; icon: string;
  nhan_ket_qua: string; mau_ket_qua: string; ngay: string };
type Viec = { loai: "lai" | "ngung" | "chao"; ma: string; ten: string; doanh_thu: number; nhip: number | null;
  lan_cuoi: string | null; so_ngay: number | null; con: number | null };
type Khach = { ma: string; ten: string; tinh: string | null; dien_thoai: string | null; phu_trach: string | null;
  cuoi: Ltx | null; da_lien_he: boolean; viec: Viec[]; nhom: string };
type Nhom = { loai: string; nhan: string; mo_ta: string; tong: number; khach: Khach[] };
type SpApi = { san_pham: { ma: string; ten: string; co: boolean }[]; nhom: Nhom[]; du: boolean; toi_da: number;
  cach_tinh: string; kieu_tx: Record<string, [string, string]>; ket_qua_tx: Record<string, [string, string]> };

// Màu nhóm dùng lại bảng màu lý do của lien_he.css: mua lại = "sắp đến hạn", ngừng = "quá hạn", chào = xanh dương.
const MAU: Record<string, string> = { lai: "lh-m-sap_den_han", ngung: "lh-m-qua_han", chao: "lh-m-thang_nay_chua_mua" };

/** Một dòng lý do cho MỘT mã — chữ thường (luật "người không rành nhìn cũng hiểu"). */
export function chuViec(v: Viec): string {
  if (v.loai === "lai") {
    const nhip = v.nhip ? `thường ${Math.round(v.nhip)} ngày mua một lần` : "";
    const khi = v.con == null ? "" : v.con < 0 ? `trễ ${-v.con} ngày` : v.con === 0 ? "đúng hôm nay" : `còn ${v.con} ngày`;
    return [khi, nhip].filter(Boolean).join(" · ");
  }
  if (v.loai === "ngung") return `${v.so_ngay ?? "?"} ngày chưa mua lại${v.nhip ? ` (thường ${Math.round(v.nhip)} ngày/lần)` : ""}`;
  return `chưa từng mua · mua hàng cùng ngành ${gon(v.doanh_thu)}/12 tháng`;
}

/** Nhãn NGẮN cho một mã (đứng trong viên màu) — câu đầy đủ ở `chuViec`, trong title. */
export function nhanNgan(v: Viec): string {
  if (v.loai === "lai") return v.con == null ? "đến lúc mua" : v.con < 0 ? `trễ ${-v.con} ngày` : v.con === 0 ? "hôm nay" : `còn ${v.con} ngày`;
  if (v.loai === "ngung") return `${v.so_ngay ?? "?"} ngày chưa mua`;
  return "chưa mua";
}

const SO_DONG = 20;

export default function TheoSanPham({ ma, datMa, locNv }: { ma: string[]; datMa: (ma: string[]) => void; locNv: string }) {
  const q = new URLSearchParams(locNv);
  if (ma.length) q.set("ma", ma.join(","));
  const url = `/api/lien-he/san-pham?${q}`;
  const coMa = ma.length > 0;
  const nhanh = useQuery<SpApi>({ queryKey: ["lien-he-sp", url, "nhanh"], queryFn: () => lay<SpApi>(url + "&nhanh=1"),
    enabled: coMa, placeholderData: keepPreviousData });
  const du = useQuery<SpApi>({ queryKey: ["lien-he-sp", url], queryFn: () => lay<SpApi>(url), enabled: coMa });
  // Bản đủ có thì dùng bản đủ; chưa có thì bản nhanh (hai nhóm đầu) + "đang tìm" cho nhóm chào.
  const d = du.data ?? nhanh.data;
  const [chon, datChon] = useState<string | null>(null);
  const [mo, datMo] = useState<string | null>(null);
  const [soHien, datSoHien] = useState(SO_DONG);

  // Nhóm đang xem: người chọn, không thì nhóm đầu có khách (gấp nhất trước).
  const nhom = d && (d.nhom.find(n => n.loai === chon) ?? d.nhom.find(n => n.tong > 0) ?? d.nhom[0]);
  const chonNhom = (l: string) => { datChon(l); datSoHien(SO_DONG); datMo(null); };

  return (
    <div className="lh-sp">
      <ChonMa ma={ma} datMa={datMa} toi_da={d?.toi_da ?? 5} ten={Object.fromEntries((d?.san_pham ?? []).map(s => [s.ma, s.ten]))} />
      {!coMa ? null : (nhanh.error || du.error) && !d ? <div className="khoi-loi">Không tải được: {((nhanh.error || du.error) as Error).message}</div>
        : !d || !nhom ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div> : <>
        {/* Ba nhóm là ba ô có số to — câu giải thích nằm trong title / ⓘ, không in ra trang. */}
        <div className="lh-sp-nhom" role="tablist" aria-label="Nhóm khách">
          {d.nhom.map(n => (
            <button key={n.loai} type="button" role="tab" aria-selected={n.loai === nhom.loai} title={n.mo_ta}
              className={"lh-sp-o " + MAU[n.loai]} onClick={() => chonNhom(n.loai)}>
              <span className="lh-sp-so">{so(n.tong)}</span><span className="lh-sp-nhan">{n.nhan}</span></button>))}
          {!d.du && <div className="lh-sp-o cho lh-m-thang_nay_chua_mua" aria-busy="true">
            <span className="lh-sp-so">…</span><span className="lh-sp-nhan">Chưa mua — nên chào</span></div>}
          <ChuThich>{d.cach_tinh}</ChuThich>
        </div>

        <ul className={"lh-sp-ds " + MAU[nhom.loai]}>
          {nhom.khach.slice(0, soHien).map(k => <DongKhach key={k.ma} k={k} d={d} nhieuMa={ma.length > 1} mo={mo === k.ma}
            datMo={v => datMo(v ? k.ma : null)} />)}
        </ul>
        {!nhom.khach.length && <p className="phu lh-sp-rong">Không có khách nào trong nhóm này.</p>}
        {nhom.khach.length > soHien && <p className="lh-sp-rong"><button type="button" className="lien-ket"
          onClick={() => datSoHien(soHien + 50)}>Xem thêm {so(Math.min(50, nhom.khach.length - soHien))} khách</button></p>}
        {nhom.tong > nhom.khach.length && soHien >= nhom.khach.length &&
          <p className="phu lh-sp-rong">Hiện {so(nhom.khach.length)} khách đầu trên {so(nhom.tong)}.</p>}
      </>}
    </div>
  );
}

function ChonMa({ ma, datMa, toi_da, ten }: { ma: string[]; datMa: (ma: string[]) => void; toi_da: number; ten: Record<string, string> }) {
  const { data: dm } = useDanhMuc();
  const [tim, datTim] = useState("");
  const tenCua = (m: string) => dm?.ma.find(x => x.ma === m)?.ten ?? ten[m] ?? m;
  const khop = useMemo(() => {
    const t = bo_dau(tim.trim());
    if (!t || !dm) return [];
    return dm.ma.filter(m => !ma.includes(m.ma) && [m.ma, m.ten].some(x => bo_dau(x).includes(t))).slice(0, 8);
  }, [tim, dm, ma]);
  // Gợi ý khi chưa chọn gì: hàng tồn chết (bán chậm, còn nhiều) — thứ sale hay được giao "đẩy đi".
  const goiY = useMemo(() => (dm?.ma ?? []).filter(m => m.trang_thai === "ton_chet" && !ma.includes(m.ma))
    .sort((a, b) => (b.ton ?? 0) - (a.ton ?? 0)).slice(0, 8), [dm, ma]);
  const them = (m: string) => { if (ma.length < toi_da && !ma.includes(m)) datMa([...ma, m]); datTim(""); };
  const day = ma.length >= toi_da;

  return (
    <div className="kh-the lh-chon-ma">
      <div className="lh-chon-dong">
        <label className="lh-tim-ma"><span>Bạn muốn bán mã nào?</span>
          <input type="search" value={tim} disabled={day} placeholder={day ? `Đã chọn tối đa ${toi_da} mã` : "Gõ tên hoặc mã hàng…"}
            onChange={e => datTim(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && khop[0]) { e.preventDefault(); them(khop[0].ma); } }} /></label>
        {ma.length > 0 && <button type="button" className="lien-ket" onClick={() => datMa([])}>Bỏ chọn hết</button>}
      </div>
      {khop.length > 0 && <ul className="lh-goi-y-ma" role="listbox">{khop.map(m => (
        <li key={m.ma}><button type="button" onClick={() => them(m.ma)}><HinhMa ma={m.ma} ten={m.ten} co={28} trang_tri />
          <span className="ten-jp">{m.ten}</span><span className="phu">{m.ma}{m.ton != null ? ` · tồn ${so(m.ton)}` : ""}</span></button></li>))}</ul>}
      {tim.trim() && !dm && <p className="phu">Đang tải danh mục hàng…</p>}
      {tim.trim() && !khop.length && dm && <p className="phu">Không tìm thấy mã nào khớp “{tim}”.</p>}
      {ma.length > 0 && <div className="lh-da-chon">{ma.map(m => (
        <span key={m} className="lh-chip-ma"><HinhMa ma={m} ten={tenCua(m)} co={22} trang_tri />
          <a href={`/san-pham/${encodeURIComponent(m)}`} className="ten-jp">{tenCua(m)}</a>
          <button type="button" aria-label={`Bỏ ${tenCua(m)}`} onClick={() => datMa(ma.filter(x => x !== m))}>✕</button></span>))}</div>}
      {!ma.length && <>
        <p className="phu">Chọn một hoặc vài mã (tối đa {toi_da}) — trang sẽ liệt kê khách nên gọi để bán mã đó.</p>
        {goiY.length > 0 && <div className="lh-da-chon"><span className="phu">Hàng tồn lâu, nên đẩy:</span>{goiY.map(m => (
          <button key={m.ma} type="button" className="lh-chip-ma goi-y" onClick={() => them(m.ma)}>
            <HinhMa ma={m.ma} ten={m.ten} co={22} trang_tri /><span className="ten-jp">{m.ten}</span> ＋</button>))}</div>}
      </>}
    </div>
  );
}

function kichBan(k: Khach): string {
  const ly = k.viec.map(v => ({ ten: v.ten, chi_tiet: (v.loai === "lai" ? "đến lúc mua lại — " : v.loai === "ngung" ? "đã ngừng — " : "nên chào — ") + chuViec(v) }));
  return kichBanGoi({ dau: dauKichBan(k.ten, k.ma, k.dien_thoai), ly_do: "Lý do gọi: chào bán theo mã hàng.", tieu_de_ma: "Mã:",
    ma: ly, cuoi: k.cuoi ? { ngay: k.cuoi.ngay, noi_dung: k.cuoi.noi_dung } : null });
}

// Một DÒNG mỗi khách (thay thẻ cao 5 dòng — chủ DN 2026-10-16: "nhiều chữ quá"): tên + người phụ trách · viên lý do
// ngắn · ☎ · ✏️ · 📋. Chi tiết (nhịp, đã mua bao nhiêu, nội dung lần gọi trước) nằm trong title — rê chuột mới hiện.
function DongKhach({ k, d, nhieuMa, mo, datMo }: { k: Khach; d: SpApi; nhieuMa: boolean; mo: boolean; datMo: (v: boolean) => void }) {
  const [daChep, datDaChep] = useState(false);
  const chep = async () => {
    try { await navigator.clipboard.writeText(kichBan(k)); datDaChep(true); setTimeout(() => datDaChep(false), 1800); }
    catch { window.prompt("Chép kịch bản:", kichBan(k)); }
  };
  const cuoi = k.cuoi;
  return (
    <li className={"lh-sp-dong" + (k.da_lien_he ? " da-goi" : "")}>
      <div className="lh-sp-ten">
        <a href={`/khach-hang/${encodeURIComponent(k.ma)}`} className="ten-jp" title={`${k.ma}${k.tinh ? " · " + k.tinh : ""}`}>{k.ten}</a>
        {k.phu_trach && <span className="phu">{k.phu_trach}</span>}
      </div>
      <div className="lh-sp-ly">
        {k.viec.map(v => (
          <span key={v.loai + v.ma} className={"lh-sp-vien " + MAU[v.loai] + (v.loai === "lai" && (v.con ?? 0) < 0 ? " tre" : "")}
            title={`${v.ten}: ${chuViec(v)}${v.loai !== "chao" && v.doanh_thu > 0 ? ` · đã mua ${yen(v.doanh_thu)}` : ""}`}>
            {nhieuMa && <HinhMa ma={v.ma} ten={v.ten} co={16} trang_tri />}{nhanNgan(v)}</span>))}
        {cuoi && <span className={"lh-sp-cuoi" + (k.da_lien_he ? " vua" : "")}
          title={`Lần trước ${ngay(cuoi.ngay)} · ${cuoi.nhan_ket_qua}: ${cuoi.noi_dung}`}>
          {cuoi.icon} {k.da_lien_he ? "vừa gọi" : ngay(cuoi.ngay)}</span>}
      </div>
      <div className="lh-sp-nut">
        {k.dien_thoai ? <a className="nut-nho lh-sp-dt" href={`tel:${k.dien_thoai}`} title="Gọi">☎ {k.dien_thoai}</a>
          : <span className="lh-sp-dt phu">—</span>}
        <button type="button" className="nut-nho" aria-expanded={mo} title="Ghi liên hệ" aria-label="Ghi liên hệ"
          onClick={() => datMo(!mo)}>{mo ? "✕" : "✏️"}</button>
        <button type="button" className="nut-nho" title="Chép kịch bản gọi" aria-label="Chép kịch bản gọi"
          onClick={chep}>{daChep ? "✓" : "📋"}</button>
      </div>
      {mo && <div className="lh-sp-ghi"><GhiTiepXuc ma={k.ma} kieu_tx={d.kieu_tx} ket_qua_tx={d.ket_qua_tx} gon
        lam_moi={[["lien-he-sp"], ["lien-he"], ["kh-ho-so", k.ma]]} xong={() => datMo(false)} /></div>}
    </li>
  );
}
