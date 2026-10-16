// Cần liên hệ (/lien-he) — BỐ CỤC của CRM.dc.html (dải KPI → các cột thẻ →
// "Hoạt động gần đây" | "Việc cần làm hôm nay"), nhưng cột là LÝ DO cần gọi,
// không phải giai đoạn deal: hệ thống không có "deal" hay "xác suất chốt" nào —
// số của gói thiết kế là bịa (lộ trình §8.2). Thẻ rời cột khi DỮ LIỆU đổi
// (khách mua lại) hoặc khi có người ghi một lần tiếp xúc — không kéo–thả.
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { useState } from "react";
import { lay } from "../api";
import { HinhMa } from "../chung/HinhMa";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../khung/khoang";
import { gon, ngay, so, yen } from "../dinh_dang";
import { ChuThich } from "../chung/Khoi";
import { KD } from "../khoi_dau";
import { GhiTiepXuc } from "../khach/GhiTiepXuc";
import { dauKichBan, kichBanGoi } from "../khach/kich_ban";
import "../khach/khach.css";
import TheoSanPham from "./TheoSanPham";
import "./lien_he.css";

type Ltx = { kieu: string; ket_qua: string; noi_dung: string; thoi_diem: string; hen_lai: string | null; nguoi: string | null;
  ma_khach: string | null; ten_khach: string | null; icon: string; nhan_kieu: string; nhan_ket_qua: string; mau_ket_qua: string; ngay: string };
type The = { ma: string; ten: string; tinh: string | null; dien_thoai: string | null; phu_trach: string | null; doanh_thu: number;
  so_ngay_im_lang: number | null; nhip_ngay: number | null; ty_le: number | null; ly_do: string; cuoi: Ltx | null;
  so_thang: number | null; dt_thang_truoc: number | null; nhan_ly_do: string; mau: string };
type Cot = { ly_do: string; nhan: string; mo_ta: string; mau: string; the: The[]; tong: number; doanh_thu: number; trung: number };
type GoiY = { ma: string; ten: string; so_lan: number; nhip_ngay: number; so_ngay: number; trang_thai: string };
type LienHeApi = {
  goi_y: Record<string, GoiY[]>; nhan_vien: { ma: string; ten: string }[]; cach_tinh_goi_y: string;
  ds: { cot: Cot[]; da_lien_he: The[]; hom_nay: string; ly_do: string | null; dem: Record<string, number>; tong: number };
  hoat_dong: Ltx[]; hen: Ltx[]; hom_nay: string; sale: string | null; ten_sale: string | null; cot_thang: string;
  an_ngay: number; ly_do_ds: Record<string, [string, string, string]>; thu_tu_ly_do: string[]; kieu_tx: Record<string, [string, string]>; ket_qua_tx: Record<string, [string, string]>; nv_moi_nguoi: string;
};

// Mỗi LÝ DO một màu (đỏ → cam → vàng theo mức khẩn; xanh dương cho cột theo tháng,
// vốn là một kiểu nhìn khác) — dùng chung cho ô KPI, đầu cột, viền thẻ, nhãn ở
// bảng tạm ẩn. Bảng màu ở lien_he.css (.lh-m-<lý do>), pha từ token của kome.css
// nên tự đúng ở cả sáng lẫn tối. Chữ nhãn vẫn luôn đi kèm — màu không phải thứ duy nhất để đọc.
const lopMau = (ly_do: string) => "lh-m-" + ly_do;

function docLoc() {
  const q = new URLSearchParams(location.search);
  const ma = (q.get("ma") ?? "").split(",").map(x => x.trim()).filter(Boolean);
  // Tab "Theo sản phẩm" (2026-10-16): ?xem=sp, hoặc có ?ma= (link từ trang sản phẩm).
  return { nv: q.get("nv") ?? "", tat_ca: q.get("tat_ca") === "1", ly_do: q.get("ly_do") ?? "",
           xem: q.get("xem") === "sp" || ma.length ? "sp" : "", ma };
}

export default function LienHe() {
  const [loc, datLoc] = useState(docLoc);
  const dat = (s: Partial<ReturnType<typeof docLoc>>) => {
    const b = { ...loc, ...s };
    const q = new URLSearchParams();
    if (b.nv) q.set("nv", b.nv);
    if (b.tat_ca) q.set("tat_ca", "1");
    if (b.xem === "sp") {
      if (b.ma.length) q.set("ma", b.ma.join(",")); else q.set("xem", "sp");
    } else if (b.ly_do) q.set("ly_do", b.ly_do);
    history.pushState(null, "", giuKhoang("/lien-he" + (q.toString() ? "?" + q : "")));
    datLoc(b);
  };
  const q = new URLSearchParams(Object.entries({ nv: loc.nv, tat_ca: loc.tat_ca ? "1" : "", ly_do: loc.ly_do })
    .filter(([, v]) => v)).toString();
  const { data: d, error, isFetching } = useQuery<LienHeApi>({
    queryKey: ["lien-he", q, chuoiKhoang(useKhoang())], queryFn: () => lay<LienHeApi>(voiKhoang(`/api/lien-he${q ? "?" + q : ""}`)), placeholderData: keepPreviousData,
  });
  const [mo, datMo] = useState<string | null>(null);
  const [soHien, datSoHien] = useState(30);

  if (error) return <div className="khoi-loi">Không tải được danh sách: {(error as Error).message}</div>;
  if (!d) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const ds = d.ds, laThang = (c: string) => c === d.cot_thang;
  const tongLuyKe = ds.cot.filter(c => !laThang(c.ly_do)).reduce((s, c) => s + c.doanh_thu, 0);
  const nvDang = loc.nv || d.sale || d.nv_moi_nguoi;
  // Bốn ô lý do đọc nhãn / mô tả từ máy chủ (LH.LY_DO) và số đếm của CẢ bốn (ds.dem) — kể cả khi đang mở một lý do (?ly_do=).
  const nhomLyDo = (d.thu_tu_ly_do ?? Object.keys(d.ly_do_ds)).map(ly_do => ({ ly_do, nhan: d.ly_do_ds[ly_do][0], mo_ta: d.ly_do_ds[ly_do][1], dem: ds.dem[ly_do] ?? 0 }));
  const lyDoDang = ds.ly_do ?? (nhomLyDo.find(c => c.dem > 0) ?? nhomLyDo[0])?.ly_do;
  const cot = ds.cot.find(c => c.ly_do === lyDoDang);
  const hien = cot ? (ds.ly_do ? cot.the.slice(0, soHien) : cot.the) : [];
  const locNv = new URLSearchParams(Object.entries({ nv: loc.nv, tat_ca: loc.tat_ca ? "1" : "" }).filter(([, v]) => v)).toString();

  return (
    <div className={"lh" + (isFetching ? " dang-tai" : "")}>
      <div className="tieu-de-trang">
        <div><h1>Cần gọi</h1>
          {loc.xem === "sp" ? <div className="phu">Chọn mã hàng muốn bán — xem khách nào nên gọi</div> :
          <div className="phu">Khách lâu chưa đặt hàng hơn bình thường — nên gọi hỏi thăm{" "}
            <ChuThich>Khách đang im lặng lâu hơn <b>nhịp mua riêng của chính họ</b>, chia theo lý do. Ghi lại mỗi lần gọi —
              khách vừa liên hệ tạm ẩn tới ngày hẹn (hoặc {d.an_ngay} ngày nếu không hẹn). Hồ sơ và lịch sử mua ở màn Khách hàng.
              <br /><br />“Nên chào” trên mỗi thẻ: {d.cach_tinh_goi_y}</ChuThich></div>}</div>
        <label className="kh-chon lh-loc"><span>Người phụ trách</span>
          <select value={nvDang} onChange={e => dat({ nv: e.target.value, tat_ca: false })}>
            <option value={d.nv_moi_nguoi}>— mọi người phụ trách —</option>
            {d.nhan_vien.map(n => <option key={n.ma} value={n.ma}>{n.ten}{n.ma === KD.nguoi?.sale ? " (tôi)" : ""}</option>)}
            {d.sale && !d.nhan_vien.some(n => n.ma === d.sale) && <option value={d.sale}>{d.ten_sale ?? d.sale}</option>}
          </select></label>
      </div>

      <div className="kh-tab" role="tablist" aria-label="Cách xem">
        <button type="button" role="tab" aria-selected={loc.xem !== "sp"} onClick={() => dat({ xem: "" })}>Theo lý do</button>
        <button type="button" role="tab" aria-selected={loc.xem === "sp"} onClick={() => dat({ xem: "sp" })}>Theo sản phẩm</button>
      </div>

      {loc.xem === "sp" ? <TheoSanPham ma={loc.ma} datMa={ma => dat({ xem: "sp", ma })} locNv={locNv} /> : <>
      {/* Gọn lại 2026-10-16 (chủ DN: "nhiều chữ quá"): 4 ô số chọn lý do + MỘT danh sách dòng (cùng kiểu tab Theo sản phẩm).
          Câu mô tả từng lý do nằm trong title / ⓘ. Mặc định mở lý do đầu tiên có khách (gấp nhất trước). */}
      <div className="lh-sp-nhom" role="tablist" aria-label="Lý do cần gọi">
        {nhomLyDo.map(c => (
          <button key={c.ly_do} type="button" role="tab" aria-selected={c.ly_do === lyDoDang} title={c.mo_ta}
            className={"lh-sp-o " + lopMau(c.ly_do)} onClick={() => dat({ ly_do: c.ly_do })}>
            <span className="lh-sp-so">{so(c.dem)}</span><span className="lh-sp-nhan">{c.nhan}</span></button>))}
        <ChuThich>{nhomLyDo.map(c => <span key={c.ly_do}><b>{c.nhan}</b>: {c.mo_ta}.<br /></span>)}
          <br />Tổng {so(ds.tong)} khách · {gon(tongLuyKe)} tổng doanh thu đến nay{ds.dem[d.cot_thang] ? " (chưa gồm cột tháng)" : ""}.</ChuThich>
        <div className="lh-phu-o">
          <a href="#viec-hom-nay">📞 Hẹn hôm nay <b>{so(d.hen.length)}</b></a>
          <a href="#da-lien-he">Đang tạm ẩn <b>{so(ds.da_lien_he.length)}</b></a>
        </div>
      </div>

      {cot && <>
        <ul className={"lh-sp-ds " + lopMau(cot.ly_do)}>
          <li className="lh-sp-dong lh-ld-dong lh-ld-dau" aria-hidden="true"><span>Khách · phụ trách</span>
            <span>{laThang(cot.ly_do) ? "Lý do · trung bình/tháng" : "Lý do · tổng doanh thu"}</span><span>Nên chào</span><span>Gọi · ghi · chép</span></li>
          {hien.map(t => <DongLyDo key={t.ma} t={t} d={d} gy={d.goi_y[t.ma] ?? []} laThang={laThang(cot.ly_do)} mo={mo === t.ma}
            datMo={v => datMo(v ? t.ma : null)} />)}
        </ul>
        {!cot.the.length && <p className="phu lh-sp-rong">Không còn khách nào ở nhóm này.</p>}
        {cot.tong > hien.length && <p className="lh-sp-rong">{ds.ly_do
          ? <button type="button" className="lien-ket" onClick={() => datSoHien(soHien + 50)}>Xem thêm {so(Math.min(50, cot.the.length - hien.length))} khách</button>
          : <button type="button" className="lien-ket" onClick={() => dat({ ly_do: cot.ly_do })}>Xem cả {so(cot.tong)} khách</button>}</p>}
        {cot.trung > 0 && <p className="phu lh-sp-rong">+{cot.trung} khách cũng thuộc nhóm này nhưng đã nằm ở nhóm khác hoặc đang tạm ẩn.</p>}
      </>}

      {/* Ba nhóm việc KHÔNG vào cột (tut/moi dựng lại khach_360 — bất biến đợt 7): mở danh sách khách đã lọc sẵn. */}
      <p className="phu lh-ghi">Nhóm khác:{" "}
        <a href="/khach-hang?nhom=tut&tat_ca=1">khách S·A mua ít đi</a> ·{" "}
        <a href="/khach-hang?nhom=moi&tat_ca=1">mua một lần rồi thôi</a> ·{" "}
        <a href="/khach-hang?nv=__trong">chưa ai phụ trách</a></p>

      {/* Không có lời hẹn tới hạn thì không vẽ khối (ô "Hẹn hôm nay 0" ở trên đã nói). */}
      {d.hen.length > 0 && <section id="viec-hom-nay" className="kh-the lh-gap">
        <div className="kh-the-dau"><h2>Hẹn gọi lại hôm nay ({so(d.hen.length)})</h2><span className="kh-the-goc phu">{ngay(d.hom_nay)} (giờ Nhật)</span></div>
        {!d.hen.length ? <p className="phu">Không có lời hẹn nào tới hạn.</p> :
        <ul className="lh-ds">{d.hen.map((n, i) => (
          <li key={n.thoi_diem + i}><span className="lh-icon" aria-hidden="true">📞</span>
            <div><div><a href={`/khach-hang/${encodeURIComponent(n.ma_khach ?? "")}#ho_so`} className="ten-jp">{n.ten_khach || n.ma_khach}</a>{" "}
              {n.hen_lai && n.hen_lai < d.hom_nay ? <span className="nhan-vien do">trễ hẹn · {ngay(n.hen_lai)}</span> : <span className="nhan-vien canh">hôm nay</span>}</div>
              <div className="lh-nd">{n.noi_dung}</div></div></li>))}</ul>}
      </section>}

      <details className="kh-the lh-gap">
        <summary><h2>Hoạt động gần đây</h2></summary>
        <ul className="lh-ds">{d.hoat_dong.map((n, i) => (
          <li key={n.thoi_diem + i}><span className="lh-icon" aria-hidden="true">{n.icon}</span>
            <div><div><a href={`/khach-hang/${encodeURIComponent(n.ma_khach ?? "")}#ho_so`} className="ten-jp">{n.ten_khach || n.ma_khach}</a>{" "}
              <span className={"nhan-vien " + n.mau_ket_qua}>{n.nhan_ket_qua}</span></div>
              <div className="lh-nd">{n.noi_dung}</div>
              <div className="phu">{ngay(n.ngay)} · {n.nguoi || "(không rõ người ghi)"}</div></div></li>))}
          {!d.hoat_dong.length && <li className="phu">Chưa có lần tiếp xúc nào được ghi.</li>}</ul>
      </details>

      <details id="da-lien-he" className="kh-the lh-gap">
        <summary><h2>Đã liên hệ gần đây — đang tạm ẩn ({ds.da_lien_he.length})</h2></summary>
        <p className="phu">Khách vừa liên hệ tạm ẩn tới ngày hẹn (hoặc {d.an_ngay} ngày nếu không hẹn).</p>
        {!ds.da_lien_he.length ? <p className="phu">Chưa có khách nào đang tạm ẩn.</p> :
        <div className="bang-cuon"><table className="bang">
          <thead><tr><th>Khách hàng</th><th>Lý do</th><th>Lần tiếp xúc cuối</th><th>Hiện lại</th></tr></thead>
          <tbody>{ds.da_lien_he.map(t => (
            <tr key={t.ma}><td className="ten-jp"><a href={`/khach-hang/${encodeURIComponent(t.ma)}#ho_so`}>{t.ten}</a></td>
              <td><span className={"lh-nhan " + lopMau(t.ly_do)}>{t.nhan_ly_do}</span></td>
              <td title={t.cuoi?.noi_dung}>{t.cuoi?.icon} {ngay(t.cuoi?.ngay)} · <span className={"nhan-vien " + (t.cuoi?.mau_ket_qua ?? "nhat")}>{t.cuoi?.nhan_ket_qua}</span></td>
              <td>{t.cuoi?.hen_lai ? ngay(t.cuoi.hen_lai) : `sau ${d.an_ngay} ngày`}</td></tr>))}</tbody>
        </table></div>}
      </details>
      </>}
    </div>
  );
}

const nhip = (g: GoiY) => `đã mua ${g.so_lan} lần · thường ${Math.round(g.nhip_ngay)} ngày/lần · lần cuối ${g.so_ngay} ngày trước`;

// Kịch bản gọi — văn bản thuần để dán vào LINE / Zalo / ghi chú (khach/kich_ban.ts).
function kichBan(t: The, gy: GoiY[], laThang: boolean): string {
  return kichBanGoi({
    dau: dauKichBan(t.ten, t.ma, t.dien_thoai),
    ly_do: laThang ? `Mua đều (${t.so_thang}/3 tháng trước), tháng này chưa có đơn.`
      : `Lý do gọi: ${t.nhan_ly_do} — ${t.so_ngay_im_lang} ngày chưa mua${t.nhip_ngay ? ` (bình thường ${Math.round(t.nhip_ngay)} ngày/lần)` : ""}.`,
    tieu_de_ma: "Nên chào:", ma: gy.map(g => ({ ten: g.ten, chi_tiet: nhip(g) })), cuoi: t.cuoi,
  });
}

// Một DÒNG mỗi khách (thay thẻ cao ~10 dòng — chủ DN 2026-10-16: "nhiều chữ quá"): tên + người phụ trách · viên lý do ·
// doanh thu · hình các mã "Nên chào" (tên trong title) · ☎ · ✏️ · 📋. Nhịp mua, mã khách, tỉnh, lần gọi trước: trong title.
function DongLyDo({ t, d, gy, laThang, mo, datMo }: { t: The; d: LienHeApi; gy: GoiY[]; laThang: boolean; mo: boolean; datMo: (v: boolean) => void }) {
  const [daChep, datDaChep] = useState(false);
  const chep = async () => {
    try { await navigator.clipboard.writeText(kichBan(t, gy, laThang)); datDaChep(true); setTimeout(() => datDaChep(false), 1800); }
    catch { window.prompt("Chép kịch bản:", kichBan(t, gy, laThang)); }
  };
  const nhipChu = t.nhip_ngay ? `bình thường ${Math.round(t.nhip_ngay)} ngày mua một lần` : "";
  return (
    <li className="lh-sp-dong lh-ld-dong">
      <div className="lh-sp-ten">
        <a href={`/khach-hang/${encodeURIComponent(t.ma)}`} className="ten-jp" title={`${t.ma}${t.tinh ? " · " + t.tinh : ""}`}>{t.ten}</a>
        {t.phu_trach && <span className="phu">{t.phu_trach}</span>}
      </div>
      <div className="lh-sp-ly">
        {laThang ? <>
          <span className={"lh-sp-vien " + lopMau(t.ly_do)} title={`mua ${t.so_thang}/3 tháng trước · tháng trước ${yen(t.dt_thang_truoc ?? 0)}`}>tháng này chưa mua</span>
          <span className="lh-ld-dt" title={yen(t.doanh_thu) + "/tháng (trung bình 3 tháng trước)"}>{gon(t.doanh_thu)}/tháng</span></> : <>
          <span className={"lh-sp-vien " + lopMau(t.ly_do) + ((t.ty_le ?? 0) >= 4 ? " tre" : "")} title={nhipChu}>{t.so_ngay_im_lang} ngày chưa mua</span>
          <span className="lh-ld-dt" title={yen(t.doanh_thu) + " tổng doanh thu đến nay"}>{gon(t.doanh_thu)}</span></>}
        {t.cuoi && <span className="lh-sp-cuoi" title={`Lần trước ${ngay(t.cuoi.ngay)} · ${t.cuoi.nhan_ket_qua}: ${t.cuoi.noi_dung}`}>{t.cuoi.icon} {ngay(t.cuoi.ngay)}</span>}
      </div>
      {/* "Nên chào": chỉ HÌNH mã, tên + nhịp trong title (d.cach_tinh_goi_y trong ⓘ của tiêu đề trang). */}
      <div className="lh-ld-chao" aria-label="Nên chào">
        {gy.map(g => <a key={g.ma} href={`/san-pham/${encodeURIComponent(g.ma)}`} title={`Nên chào: ${g.ten} — ${nhip(g)}`}>
          <HinhMa ma={g.ma} ten={g.ten} co={26} trang_tri /></a>)}
      </div>
      <div className="lh-sp-nut">
        {t.dien_thoai ? <a className="nut-nho lh-sp-dt" href={`tel:${t.dien_thoai}`} title="Gọi">☎ {t.dien_thoai}</a>
          : <span className="lh-sp-dt phu">—</span>}
        <button type="button" className="nut-nho" aria-expanded={mo} title="Ghi liên hệ" aria-label="Ghi liên hệ"
          onClick={() => datMo(!mo)}>{mo ? "✕" : "✏️"}</button>
        <button type="button" className="nut-nho" title="Chép kịch bản gọi" aria-label="Chép kịch bản gọi"
          onClick={chep}>{daChep ? "✓" : "📋"}</button>
      </div>
      {mo && <div className="lh-sp-ghi"><GhiTiepXuc ma={t.ma} kieu_tx={d.kieu_tx} ket_qua_tx={d.ket_qua_tx} gon
        lam_moi={[["lien-he"], ["lien-he-sp"], ["kh-ho-so", t.ma]]} xong={() => datMo(false)} /></div>}
    </li>
  );
}
