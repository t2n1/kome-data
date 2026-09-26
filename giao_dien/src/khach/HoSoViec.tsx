// Cột trái của hồ sơ 360° — "Việc với khách này" (đặc tả 2026-09-26 §4).
// Không định nghĩa chỉ số: câu lý do là dien_giai của máy chủ, mã đọc h.lich.
import { useState } from "react";
import { ngay } from "../dinh_dang";
import type { HoSoApi } from "./kieu";
import { MAU_TT } from "./DanhSach";
import { GhiTiepXuc } from "./GhiTiepXuc";
import { OCongNoGon } from "../cong_no/CongNoKhach";
import { The } from "./HoSoTab";
import { cauNhip, dongMuaLai, laCanGoi } from "./ho_so_logic";
import { dauKichBan, kichBanGoi } from "./kich_ban";
import { TN } from "../khoi_dau";

export const ID_GHI_NHANH = "ghi-tx-nhanh";

export function HoSoViec({ h, moGhi, datMoGhi }: { h: HoSoApi; moGhi: boolean; datMoGhi: (v: boolean) => void }) {
  const k = h.khach, mau = MAU_TT[k.trang_thai] ?? "nhat";
  const ngung = k.trang_thai === "ngung_giao_dich";
  return (
    <aside className="hs2-trai" aria-label="Việc với khách này">
      {ngung ? (
        <section className={"kh-the hs2-ly-do nhat"}>
          <h2>Tình hình</h2>
          <p>Khách đã ngừng giao dịch{k.dau_hieu_obc ? ` (※${k.dau_hieu_obc}※)` : ""} — không gọi.</p>
        </section>
      ) : (
        <section className={"kh-the hs2-ly-do " + mau}>
          <h2>{laCanGoi(mau, h.thang_nay?.nhan) ? "Vì sao cần gọi" : "Tình hình"}</h2>
          <p>{h.dien_giai || "Không có gì bất thường."}</p>
          <p className="phu">{cauNhip(k.ty_le_im_lang)}</p>
        </section>)}
      {!ngung && <MaMuaLai h={h} />}
      <LanTruoc h={h} moGhi={moGhi} datMoGhi={datMoGhi} />
      {TN.cong_no && <OCongNoGon ma={k.ma} />}
    </aside>);
}

function MaMuaLai({ h }: { h: HoSoApi }) {
  const ds = dongMuaLai(h.lich.ma);
  const [daChep, datDaChep] = useState(false);
  const ban = () => kichBanGoi({
    dau: dauKichBan(h.khach.ten, h.khach.ma, h.khach.dien_thoai),
    ly_do: h.dien_giai || "Đang mua đều.",
    tieu_de_ma: "Mã đến ngày mua lại:",
    ma: ds.filter(d => d.muc === "qua").map(d => ({ ten: d.ten, chi_tiet: d.nhan })),
    cuoi: h.nhat_ky[0] ? { ngay: h.nhat_ky[0].ngay, noi_dung: h.nhat_ky[0].noi_dung } : null,
  });
  const chep = async () => {
    try { await navigator.clipboard.writeText(ban()); datDaChep(true); setTimeout(() => datDaChep(false), 1800); }
    catch { window.prompt("Chép kịch bản:", ban()); }
  };
  const moNgung = () => { location.hash = "mat_hang"; setTimeout(() => document.getElementById("da-ngung-mua")?.scrollIntoView({ behavior: "smooth" }), 50); };
  return (
    <The tieu_de="Mã đến ngày mua lại" className="hs2-viec"
      goc={h.lich.tong ? <span className={h.lich.so_tre ? "giam" : "tang"}>{h.lich.so_tre}/{h.lich.tong} đã quá</span> : null}
      cach_tinh="ngày dự kiến = lần mua cuối + nhịp mua riêng của cặp khách–mã · 10 mã gần ngày nhất">
      {!ds.length ? <p className="phu">Chưa mã nào đủ 3 lần mua để có nhịp riêng.</p> :
        <ul className="hs2-ds">{ds.map(d => (
          <li key={d.ma} className="hs2-dong"><a className="ten-jp" href={`/san-pham/${encodeURIComponent(d.ma)}`}>{d.ten}</a>
            <b className={d.muc === "qua" ? "giam" : d.muc === "sap" ? "canh-chu" : "nhat-chu"}>{d.nhan}</b></li>))}</ul>}
      {h.o_so.so_ma_ngung > 0 && <button type="button" className="hs2-lien-ket" onClick={moNgung}>
        + {h.o_so.so_ma_ngung} mã đã ngừng mua — xem ›</button>}
      <button type="button" className="nut-nho hs2-rong" onClick={chep}>{daChep ? "✓ Đã chép" : "📋 Chép kịch bản gọi"}</button>
    </The>);
}

function LanTruoc({ h, moGhi, datMoGhi }: { h: HoSoApi; moGhi: boolean; datMoGhi: (v: boolean) => void }) {
  const n = h.nhat_ky[0];
  return (
    <section className="kh-the hs2-viec">
      <h2>Lần liên hệ trước</h2>
      {n ? <div className="hs2-lan-truoc">
        <div>{n.icon} {n.nhan_kieu} · {ngay(n.ngay)} <span className={"nhan-vien " + n.mau_ket_qua}>{n.nhan_ket_qua}</span>
          {n.hen_lai && <span className="phu"> · hẹn {ngay(n.hen_lai)}</span>}</div>
        <p>{n.noi_dung}</p>{n.nguoi && <span className="phu">— {n.nguoi}</span>}</div>
        : <p className="phu">Chưa ghi lần tiếp xúc nào.</p>}
      <button type="button" className="hs2-lien-ket" aria-expanded={moGhi} onClick={() => datMoGhi(!moGhi)}>
        {moGhi ? "Đóng ▴" : "Ghi nhanh ▾"}</button>
      {moGhi && <GhiTiepXuc ma={h.khach.ma} kieu_tx={h.kieu_tx} ket_qua_tx={h.ket_qua_tx} gon id={ID_GHI_NHANH}
        lam_moi={[["kh-ho-so", h.khach.ma]]} xong={() => datMoGhi(false)} />}
    </section>);
}
