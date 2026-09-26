// Cần liên hệ (/lien-he) — BỐ CỤC của CRM.dc.html (dải KPI → các cột thẻ →
// "Hoạt động gần đây" | "Việc cần làm hôm nay"), nhưng cột là LÝ DO cần gọi,
// không phải giai đoạn deal: hệ thống không có "deal" hay "xác suất chốt" nào —
// số của gói thiết kế là bịa (lộ trình §8.2). Thẻ rời cột khi DỮ LIỆU đổi
// (khách mua lại) hoặc khi có người ghi một lần tiếp xúc — không kéo–thả.
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { useState } from "react";
import { lay } from "../api";
import { chuoiKhoang, giuKhoang, useKhoang, voiKhoang } from "../khung/khoang";
import { ngay, so, yen } from "../dinh_dang";
import { KD } from "../khoi_dau";
import { GhiTiepXuc } from "../khach/GhiTiepXuc";
import { dauKichBan, kichBanGoi } from "../khach/kich_ban";
import "../khach/khach.css";
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
  an_ngay: number; kieu_tx: Record<string, [string, string]>; ket_qua_tx: Record<string, [string, string]>; nv_moi_nguoi: string;
};

// Mỗi LÝ DO một màu (đỏ → cam → vàng theo mức khẩn; xanh dương cho cột theo tháng,
// vốn là một kiểu nhìn khác) — dùng chung cho ô KPI, đầu cột, viền thẻ, nhãn ở
// bảng tạm ẩn. Bảng màu ở lien_he.css (.lh-m-<lý do>), pha từ token của kome.css
// nên tự đúng ở cả sáng lẫn tối. Chữ nhãn vẫn luôn đi kèm — màu không phải thứ duy nhất để đọc.
const lopMau = (ly_do: string) => "lh-m-" + ly_do;

function docLoc() {
  const q = new URLSearchParams(location.search);
  return { nv: q.get("nv") ?? "", tat_ca: q.get("tat_ca") === "1", ly_do: q.get("ly_do") ?? "" };
}

export default function LienHe() {
  const [loc, datLoc] = useState(docLoc);
  const dat = (s: Partial<ReturnType<typeof docLoc>>) => {
    const b = { ...loc, ...s };
    const q = new URLSearchParams();
    if (b.nv) q.set("nv", b.nv);
    if (b.tat_ca) q.set("tat_ca", "1");
    if (b.ly_do) q.set("ly_do", b.ly_do);
    history.pushState(null, "", giuKhoang("/lien-he" + (q.toString() ? "?" + q : "")));
    datLoc(b);
  };
  const q = new URLSearchParams(Object.entries({ nv: loc.nv, tat_ca: loc.tat_ca ? "1" : "", ly_do: loc.ly_do })
    .filter(([, v]) => v)).toString();
  const { data: d, error, isFetching } = useQuery<LienHeApi>({
    queryKey: ["lien-he", q, chuoiKhoang(useKhoang())], queryFn: () => lay<LienHeApi>(voiKhoang(`/api/lien-he${q ? "?" + q : ""}`)), placeholderData: keepPreviousData,
  });
  const [mo, datMo] = useState<string | null>(null);

  if (error) return <div className="khoi-loi">Không tải được danh sách: {(error as Error).message}</div>;
  if (!d) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const ds = d.ds, laThang = (c: string) => c === d.cot_thang;
  const tongLuyKe = ds.cot.filter(c => !laThang(c.ly_do)).reduce((s, c) => s + c.doanh_thu, 0);
  const nvDang = loc.nv || d.sale || d.nv_moi_nguoi;

  return (
    <div className={"lh" + (isFetching ? " dang-tai" : "")}>
      <div className="tieu-de-trang">
        <div><h1>Cần liên hệ</h1>
          <div className="phu">Khách đang im lặng lâu hơn <b>nhịp mua riêng của chính họ</b>, chia theo lý do · ghi lại mỗi lần gọi —
            khách vừa liên hệ tạm ẩn tới ngày hẹn (hoặc {d.an_ngay} ngày nếu không hẹn) · hồ sơ và lịch sử mua ở <a href="/khach-hang">Khách hàng</a></div></div>
        <label className="kh-chon lh-loc"><span>担当者</span>
          <select value={nvDang} onChange={e => dat({ nv: e.target.value, tat_ca: false })}>
            <option value={d.nv_moi_nguoi}>— mọi người phụ trách —</option>
            {d.nhan_vien.map(n => <option key={n.ma} value={n.ma}>{n.ten}{n.ma === KD.nguoi?.sale ? " (tôi)" : ""}</option>)}
            {d.sale && !d.nhan_vien.some(n => n.ma === d.sale) && <option value={d.sale}>{d.ten_sale ?? d.sale}</option>}
          </select></label>
      </div>

      <div className="o-kpi-luoi lh-kpi">
        <div className="o-kpi"><div className="nhan">Cần liên hệ</div><div className="gia">{so(ds.tong)}</div>
          <div className="dong-phu nhat-chu">khách · {yen(tongLuyKe)} doanh thu luỹ kế{ds.dem[d.cot_thang] ? " (chưa gồm cột tháng)" : ""}</div></div>
        {ds.cot.map(c => (
          <button key={c.ly_do} type="button" className={"o-kpi lh-o " + lopMau(c.ly_do)} aria-pressed={loc.ly_do === c.ly_do}
            onClick={() => dat({ ly_do: loc.ly_do === c.ly_do ? "" : c.ly_do })}>
            <div className="nhan">{c.nhan}</div><div className="gia">{so(ds.dem[c.ly_do] ?? 0)}</div>
            <div className="dong-phu nhat-chu">{c.mo_ta}</div></button>))}
        <div className="o-kpi"><div className="nhan">Hẹn gọi lại hôm nay</div><div className="gia">{so(d.hen.length)}</div>
          <div className="dong-phu nhat-chu">{ngay(d.hom_nay)} (giờ Nhật)</div></div>
        <a className="o-kpi" href="#da-lien-he"><div className="nhan">Đã liên hệ, đang tạm ẩn</div><div className="gia">{so(ds.da_lien_he.length)}</div>
          <div className="dong-phu nhat-chu">xem danh sách ↓</div></a>
      </div>

      <p className="phu lh-ghi">Hai nhóm khác của danh sách làm việc:{" "}
        <a href="/khach-hang?nhom=tut&tat_ca=1">khách lớn đang giảm tốc</a> · <a href="/khach-hang?nhom=moi&tat_ca=1">khách mới đã im lặng</a>.
        {ds.ly_do && <> <button type="button" className="lien-ket" onClick={() => dat({ ly_do: "" })}>← Mọi lý do</button></>}
        <br />“Nên chào” trên mỗi thẻ: {d.cach_tinh_goi_y}</p>

      <div className={"lh-cot" + (ds.ly_do ? " mot" : "")}>
        {ds.cot.map(c => (
          <section key={c.ly_do} className={lopMau(c.ly_do)} aria-labelledby={"cot-" + c.ly_do}>
            <div className="lh-cot-dau"><h2 id={"cot-" + c.ly_do}><span className="lh-nhan">{c.nhan}</span></h2>
              <span className="phu">{so(c.tong)} khách</span>
              <span className="lh-tong">{yen(c.doanh_thu)}{laThang(c.ly_do) ? "/tháng" : ""}</span></div>
            <div className="lh-cot-mo">{c.mo_ta}</div>
            <div className="lh-the-ds">{c.the.map(t => <The key={t.ma} t={t} d={d} gy={d.goi_y[t.ma] ?? []} laThang={laThang(c.ly_do)} mo={mo === t.ma}
              datMo={v => datMo(v ? t.ma : null)} />)}</div>
            {!c.the.length && <p className="lh-cot-mo">Không còn khách nào ở cột này.</p>}
            {c.trung > 0 && <p className="lh-cot-mo">+{c.trung} khách cũng thuộc nhóm này nhưng đã nằm ở cột khác hoặc đang tạm ẩn.</p>}
            {c.tong > c.the.length && <p className="lh-cot-mo"><button type="button" className="lien-ket" onClick={() => dat({ ly_do: c.ly_do })}>Xem cả {so(c.tong)} khách →</button></p>}
          </section>))}
      </div>

      <div className="lh-hai">
        <section className="kh-the"><div className="kh-the-dau"><h2>Hoạt động gần đây</h2></div>
          <ul className="lh-ds">{d.hoat_dong.map((n, i) => (
            <li key={n.thoi_diem + i}><span className="lh-icon" aria-hidden="true">{n.icon}</span>
              <div><div><a href={`/khach-hang/${encodeURIComponent(n.ma_khach ?? "")}#ho_so`} className="ten-jp">{n.ten_khach || n.ma_khach}</a>{" "}
                <span className={"nhan-vien " + n.mau_ket_qua}>{n.nhan_ket_qua}</span></div>
                <div className="lh-nd">{n.noi_dung}</div>
                <div className="phu">{n.nhan_kieu} · {ngay(n.ngay)} · {n.nguoi || "(không rõ người ghi)"}</div></div></li>))}
            {!d.hoat_dong.length && <li className="phu">Chưa có lần tiếp xúc nào được ghi.</li>}</ul>
        </section>
        <section className="kh-the"><div className="kh-the-dau"><h2>Việc cần làm hôm nay</h2><span className="kh-the-goc phu">hẹn gọi lại tới hạn</span></div>
          <ul className="lh-ds">{d.hen.map((n, i) => (
            <li key={n.thoi_diem + i}><span className="lh-icon" aria-hidden="true">📞</span>
              <div><div><a href={`/khach-hang/${encodeURIComponent(n.ma_khach ?? "")}#ho_so`} className="ten-jp">{n.ten_khach || n.ma_khach}</a>{" "}
                {n.hen_lai && n.hen_lai < d.hom_nay ? <span className="nhan-vien do">trễ hẹn · {ngay(n.hen_lai)}</span> : <span className="nhan-vien canh">hôm nay</span>}</div>
                <div className="lh-nd">{n.noi_dung}</div>
                <div className="phu">{n.icon} {n.nhan_kieu} ngày {ngay(n.ngay)} · {n.nguoi || "(không rõ người ghi)"}</div></div></li>))}
            {!d.hen.length && <li className="phu">Không có lời hẹn nào tới hạn.</li>}</ul>
          <p className="phu">Gọi xong thì ghi lại ở thẻ của khách — lời hẹn cũ được trả, việc tự rời danh sách.</p>
        </section>
      </div>

      <section id="da-lien-he" className="kh-the lh-an">
        <div className="kh-the-dau"><h2>Đã liên hệ gần đây — đang tạm ẩn ({ds.da_lien_he.length})</h2></div>
        {!ds.da_lien_he.length ? <p className="phu">Chưa có khách nào đang tạm ẩn.</p> :
        <div className="bang-cuon"><table className="bang">
          <thead><tr><th>Khách hàng</th><th>Lý do</th><th>Lần tiếp xúc cuối</th><th>Kết quả</th><th>Hiện lại</th><th className="so">Doanh thu</th></tr></thead>
          <tbody>{ds.da_lien_he.map(t => (
            <tr key={t.ma}><td className="ten-jp"><a href={`/khach-hang/${encodeURIComponent(t.ma)}#ho_so`}>{t.ten}</a></td>
              <td><span className={"lh-nhan " + lopMau(t.ly_do)}>{t.nhan_ly_do}</span></td>
              <td>{t.cuoi?.icon} {ngay(t.cuoi?.ngay)} — {(t.cuoi?.noi_dung ?? "").slice(0, 60)}</td>
              <td><span className={"nhan-vien " + (t.cuoi?.mau_ket_qua ?? "nhat")}>{t.cuoi?.nhan_ket_qua}</span></td>
              <td>{t.cuoi?.hen_lai ? ngay(t.cuoi.hen_lai) : `sau ${d.an_ngay} ngày`}</td>
              <td className="so">{yen(t.doanh_thu)}{laThang(t.ly_do) ? "/tháng" : ""}</td></tr>))}</tbody>
        </table></div>}
      </section>
    </div>
  );
}

const nhip = (g: GoiY) => `${g.so_lan} lần · nhịp ${Math.round(g.nhip_ngay)} ngày · lần cuối ${g.so_ngay} ngày trước`;

// Kịch bản gọi — văn bản thuần để dán vào LINE / Zalo / ghi chú (khach/kich_ban.ts).
function kichBan(t: The, gy: GoiY[], laThang: boolean): string {
  return kichBanGoi({
    dau: dauKichBan(t.ten, t.ma, t.dien_thoai),
    ly_do: laThang ? `Mua đều (${t.so_thang}/3 tháng trước), tháng này chưa có đơn.`
      : `Lý do gọi: ${t.nhan_ly_do} — im ${t.so_ngay_im_lang} ngày${t.nhip_ngay ? ` (nhịp thường ${Math.round(t.nhip_ngay)} ngày)` : ""}.`,
    tieu_de_ma: "Nên chào:", ma: gy.map(g => ({ ten: g.ten, chi_tiet: nhip(g) })), cuoi: t.cuoi,
  });
}

function The({ t, d, gy, laThang, mo, datMo }: { t: The; d: LienHeApi; gy: GoiY[]; laThang: boolean; mo: boolean; datMo: (v: boolean) => void }) {
  const [daChep, datDaChep] = useState(false);
  const chep = async () => {
    try { await navigator.clipboard.writeText(kichBan(t, gy, laThang)); datDaChep(true); setTimeout(() => datDaChep(false), 1800); }
    catch { window.prompt("Chép kịch bản:", kichBan(t, gy, laThang)); }
  };
  return (
    <div className={"lh-the " + lopMau(t.ly_do)}>
      <div className="lh-ten"><a href={`/khach-hang/${encodeURIComponent(t.ma)}`} className="ten-jp">{t.ten}</a></div>
      <div className="phu">{t.ma}{t.tinh ? ` · ${t.tinh}` : ""}{t.phu_trach ? ` · ${t.phu_trach}` : ""}</div>
      <div className="lh-so">{laThang ? <>
        <b>{yen(t.doanh_thu)}/tháng</b><span className="phu">mua {t.so_thang}/3 tháng trước · tháng trước {yen(t.dt_thang_truoc ?? 0)}</span></> : <>
        <b>{yen(t.doanh_thu)}</b>
        <span className={(t.ty_le ?? 0) >= 4 ? "giam" : (t.ty_le ?? 0) >= 2 ? "canh-chu" : "phu"}>
          im {t.so_ngay_im_lang} ngày{t.ty_le ? ` · ${t.ty_le.toFixed(1).replace(".", ",")}× nhịp ${Math.round(t.nhip_ngay ?? 0)} ngày` : ""}</span></>}</div>
      {t.dien_thoai && <div className="phu">☎ <a href={`tel:${t.dien_thoai}`}>{t.dien_thoai}</a></div>}
      {t.cuoi && <div className="lh-cuoi">Lần trước: {t.cuoi.icon} {ngay(t.cuoi.ngay)} · <span className={"nhan-vien " + t.cuoi.mau_ket_qua}>{t.cuoi.nhan_ket_qua}</span> {t.cuoi.noi_dung.slice(0, 60)}</div>}
      {gy.length > 0 && <div className="lh-goi-y" title={d.cach_tinh_goi_y}>
        <div className="lh-goi-y-dau">Nên chào</div>
        <ul>{gy.map(g => <li key={g.ma}><a href={`/san-pham/${encodeURIComponent(g.ma)}`} className="ten-jp">{g.ten}</a>
          <span className="phu">{nhip(g)}</span></li>)}</ul></div>}
      <div className="lh-nut">
        <button type="button" className="nut-nho" aria-expanded={mo} onClick={() => datMo(!mo)}>{mo ? "Đóng" : "✏️ Ghi liên hệ"}</button>
        <button type="button" className="nut-nho" onClick={chep}>{daChep ? "✓ Đã chép" : "📋 Chép kịch bản"}</button>
      </div>
      {mo && <GhiTiepXuc ma={t.ma} kieu_tx={d.kieu_tx} ket_qua_tx={d.ket_qua_tx} gon lam_moi={[["lien-he"], ["kh-ho-so", t.ma]]} xong={() => datMo(false)} />}
    </div>
  );
}
