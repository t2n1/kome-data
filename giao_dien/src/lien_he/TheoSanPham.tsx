// Cần gọi — THEO SẢN PHẨM (2026-10-16, chủ DN: "sale sản phẩm đó thì có những khách nào cần gọi").
// Chọn ≤ 5 mã (?ma=A,B) → ba nhóm khách: đến lúc mua lại · đã ngừng mua mã này · chưa mua — nên chào.
// Định nghĩa ở máy chủ (kome/lien_he.py::theo_san_pham — đọc nhãn cặp khách–mã và mart.sp_khach_nen_chao);
// trang chỉ vẽ. "Nên chào" chậm (~1,4 s mỗi mã) nên hỏi bản nhanh (?nhanh=1) trước, bản đủ thay vào sau.
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { lay } from "../api";
import { HinhMa } from "../chung/HinhMa";
import { ChuThich } from "../chung/Khoi";
import { MAC_DINH_XEM } from "../chung/XemThem";
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

export default function TheoSanPham({ ma, datMa, locNv }: { ma: string[]; datMa: (ma: string[]) => void; locNv: string }) {
  const q = new URLSearchParams(locNv);
  if (ma.length) q.set("ma", ma.join(","));
  const url = `/api/lien-he/san-pham?${q}`;
  const coMa = ma.length > 0;
  const nhanh = useQuery<SpApi>({ queryKey: ["lien-he-sp", url, "nhanh"], queryFn: () => lay<SpApi>(url + "&nhanh=1"),
    enabled: coMa, placeholderData: keepPreviousData });
  const du = useQuery<SpApi>({ queryKey: ["lien-he-sp", url], queryFn: () => lay<SpApi>(url), enabled: coMa });
  // Bản đủ có thì dùng bản đủ; chưa có thì bản nhanh (hai nhóm đầu) + khung "đang tìm" cho nhóm chào.
  const d = du.data ?? nhanh.data;
  const [mo, datMo] = useState<string | null>(null);
  const [moNhom, datMoNhom] = useState<Record<string, boolean>>({});

  return (
    <div className="lh-sp">
      <ChonMa ma={ma} datMa={datMa} toi_da={d?.toi_da ?? 5} ten={Object.fromEntries((d?.san_pham ?? []).map(s => [s.ma, s.ten]))} />
      {!coMa ? null : (nhanh.error || du.error) && !d ? <div className="khoi-loi">Không tải được: {((nhanh.error || du.error) as Error).message}</div>
        : !d ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div> : <>
        <p className="lh-ghi phu">Khách cần gọi để bán {ma.length > 1 ? `${ma.length} mã đã chọn` : "mã đã chọn"}{" "}
          <ChuThich>{d.cach_tinh}</ChuThich>
          {d.nhom.filter(n => n.loai !== "chao").map(n => <span key={n.loai}> · <b>{so(n.tong)}</b> {n.nhan.toLowerCase()}</span>)}
          {d.du ? <> · <b>{so(d.nhom.find(n => n.loai === "chao")?.tong ?? 0)}</b> nên chào</> : " · đang tìm khách nên chào…"}</p>
        <div className="lh-cot">
          {d.nhom.map(n => { const hien = moNhom[n.loai] ? n.khach : n.khach.slice(0, MAC_DINH_XEM); return (
            <section key={n.loai} className={MAU[n.loai]} aria-labelledby={"sp-" + n.loai}>
              <div className="lh-cot-dau"><h2 id={"sp-" + n.loai}><span className="lh-nhan">{n.nhan}</span></h2>
                <span className="phu">{so(n.tong)} khách</span></div>
              <div className="lh-cot-mo">{n.mo_ta}</div>
              <div className="lh-the-ds">{hien.map(k => <TheKhach key={k.ma} k={k} d={d} nhieuMa={ma.length > 1} mo={mo === k.ma}
                datMo={v => datMo(v ? k.ma : null)} />)}</div>
              {!n.khach.length && <p className="lh-cot-mo">Không có khách nào.</p>}
              {n.khach.length > hien.length && <p className="lh-cot-mo"><button type="button" className="lien-ket"
                onClick={() => datMoNhom({ ...moNhom, [n.loai]: true })}>Xem thêm {so(n.khach.length - hien.length)} khách →</button></p>}
              {n.tong > n.khach.length && moNhom[n.loai] && <p className="lh-cot-mo">Hiện {so(n.khach.length)} khách đầu trên {so(n.tong)}.</p>}
            </section>); })}
          {!d.du && <section className={MAU.chao}><div className="lh-cot-dau"><h2><span className="lh-nhan">Chưa mua — nên chào</span></h2></div>
            <div className="khoi-cho" aria-busy="true"><span /><span /></div></section>}
        </div></>}
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
  return kichBanGoi({ dau: dauKichBan(k.ten, k.ma, k.dien_thoai), ly_do: "Gọi để bán:", tieu_de_ma: "", ma: ly,
    cuoi: k.cuoi ? { ngay: k.cuoi.ngay, noi_dung: k.cuoi.noi_dung } : null }).replace("\n\n", "\n");
}

function TheKhach({ k, d, nhieuMa, mo, datMo }: { k: Khach; d: SpApi; nhieuMa: boolean; mo: boolean; datMo: (v: boolean) => void }) {
  const [daChep, datDaChep] = useState(false);
  const chep = async () => {
    try { await navigator.clipboard.writeText(kichBan(k)); datDaChep(true); setTimeout(() => datDaChep(false), 1800); }
    catch { window.prompt("Chép kịch bản:", kichBan(k)); }
  };
  return (
    <div className={"lh-the " + MAU[k.nhom]}>
      <div className="lh-ten"><a href={`/khach-hang/${encodeURIComponent(k.ma)}`} className="ten-jp">{k.ten}</a></div>
      <div className="phu">{k.ma}{k.tinh ? ` · ${k.tinh}` : ""}{k.phu_trach ? ` · ${k.phu_trach}` : ""}</div>
      <ul className="lh-viec">{k.viec.map(v => (
        <li key={v.loai + v.ma} className={MAU[v.loai]}>
          {nhieuMa && <HinhMa ma={v.ma} ten={v.ten} co={18} trang_tri />}
          <div>{nhieuMa && <div className="ten-jp lh-goi-y-ten">{v.ten}</div>}
            <span className={v.loai === "lai" && (v.con ?? 0) < 0 ? "canh-chu" : "phu"}>{chuViec(v)}</span>
            {v.loai !== "chao" && v.doanh_thu > 0 && <span className="phu" title={yen(v.doanh_thu)}> · tổng đã mua mã này {gon(v.doanh_thu)}</span>}</div></li>))}</ul>
      {k.dien_thoai && <div className="phu">☎ <a href={`tel:${k.dien_thoai}`}>{k.dien_thoai}</a></div>}
      {k.cuoi && <div className="lh-cuoi">{k.da_lien_he && <b>Vừa liên hệ · </b>}Lần trước: {k.cuoi.icon} {ngay(k.cuoi.ngay)} ·{" "}
        <span className={"nhan-vien " + k.cuoi.mau_ket_qua}>{k.cuoi.nhan_ket_qua}</span> {k.cuoi.noi_dung.slice(0, 60)}</div>}
      <div className="lh-nut">
        <button type="button" className="nut-nho" aria-expanded={mo} onClick={() => datMo(!mo)}>{mo ? "Đóng" : "✏️ Ghi liên hệ"}</button>
        <button type="button" className="nut-nho" onClick={chep}>{daChep ? "✓ Đã chép" : "📋 Chép kịch bản"}</button>
      </div>
      {mo && <GhiTiepXuc ma={k.ma} kieu_tx={d.kieu_tx} ket_qua_tx={d.ket_qua_tx} gon
        lam_moi={[["lien-he-sp"], ["lien-he"], ["kh-ho-so", k.ma]]} xong={() => datMo(false)} />}
    </div>
  );
}
