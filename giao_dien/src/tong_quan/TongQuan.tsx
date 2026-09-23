// Trang Tổng quan — Dashboard.dc.html: lời chào · "XEM THEO VAI TRÒ" · dải tóm
// tắt · thanh bố cục · lưới kéo thả · bảng "Thêm chức năng".
import { useEffect, useMemo, useRef, useState } from "react";
import { gui, useKhoi } from "../api";
import { gon, pc } from "../dinh_dang";
import { KD, type OBoCuc } from "../khoi_dau";
import { Luoi } from "./Luoi";
import { veKhoi } from "./khoi";
import { DaiTuoi } from "./DaiTuoi";
import "./tong_quan.css";

const THU = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];

function gioTokyo() {
  const p = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", hour12: false, weekday: "short" }).formatToParts(new Date());
  const g = (t: string) => p.find(x => x.type === t)?.value ?? "";
  const ngay = new Date(`${g("year")}-${g("month")}-${g("day")}T00:00:00`);
  return { gio: +g("hour") % 24, chu: `${THU[ngay.getDay()]} ${g("day")}/${g("month")}/${g("year")}` };
}

export function TongQuan() {
  const khoi = KD.danh_muc.khoi;
  const nhanCua = useMemo(() => Object.fromEntries(khoi.map(k => [k.id, k.nhan])), [khoi]);
  const [bo_cuc, datBoCucGoc] = useState<OBoCuc[]>(KD.bo_cuc.length ? KD.bo_cuc : khoi.map(k => ({ id: k.id, rong: k.rong, cao: k.cao, an: false })));
  const [chon, datChon] = useState(false);
  const [loiLuu, datLoiLuu] = useState("");
  const hen = useRef<number>(0);

  const datBoCuc = (b: OBoCuc[]) => {
    datBoCucGoc(b);
    if (!KD.sap_xep_duoc) return;          // máy chưa bật đăng nhập: xếp tạm, không lưu
    clearTimeout(hen.current);
    hen.current = window.setTimeout(() => {
      gui("/tong-quan/bo-cuc", b).then(() => datLoiLuu("")).catch(() => datLoiLuu("Không lưu được bố cục — thử lại sau."));
    }, 400);
  };

  const { gio, chu } = gioTokyo();
  const ten = KD.nguoi?.ten_sale?.split(" ").slice(-1)[0] || KD.nguoi?.ten_dang_nhap;
  const chao = (gio < 11 ? "Chào buổi sáng" : gio < 18 ? "Chào buổi chiều" : "Chào buổi tối") + (ten ? `, ${ten}` : "");

  const hienIds = new Set(bo_cuc.filter(o => !o.an).map(o => o.id));
  const vaiDang = KD.danh_muc.vai_tro.find(v => v.khoi.length === hienIds.size && v.khoi.every(id => hienIds.has(id)))?.id;
  const apVai = (khoiVai: string[] | null) => datBoCuc(bo_cuc.map(o => ({ ...o, an: khoiVai ? !khoiVai.includes(o.id) : false })));

  return (
    <div className="tq">
      <div className="tieu-de-trang">
        <div><h1>{chao}</h1><div className="phu">{chu} · giờ Tokyo</div></div>
        <div className="vai-tro" role="group" aria-label="Xem theo vai trò">
          <span className="nhan-nho">XEM THEO VAI TRÒ</span>
          {KD.danh_muc.vai_tro.map(v => (
            <button key={v.id} type="button" className="chip" aria-pressed={vaiDang === v.id}
              onClick={() => apVai(vaiDang === v.id ? null : v.khoi)}>{v.nhan}</button>))}
        </div>
      </div>
      <DaiTuoi />
      <TomTat />
      <div className="thanh-bo-cuc">
        {KD.sap_xep_duoc
          ? <span className="phu">⠿ kéo đầu khối để sắp xếp · đổi kích thước ở góc phải dưới</span>
          : <span className="phu">Máy này chưa bật đăng nhập — sắp xếp chỉ giữ tới khi tải lại trang.</span>}
        <span className="phu mo">{hienIds.size}/{khoi.length} chức năng đang hiện</span>
        <button type="button" className="nut-nho" onClick={() => datBoCuc(khoi.map(k => ({ id: k.id, rong: k.rong, cao: k.cao, an: false })))}>Đặt lại bố cục</button>
        {loiLuu && <span className="giam phu" role="alert">{loiLuu}</span>}
        <button type="button" className="nut-chinh them" onClick={() => datChon(true)}>＋ Thêm chức năng</button>
      </div>
      <Luoi bo_cuc={bo_cuc} datBoCuc={datBoCuc} sua_duoc={true} nhan={id => nhanCua[id] ?? id} ve={id => veKhoi(id, nhanCua[id] ?? id)} />
      {chon && <BangThem bo_cuc={bo_cuc} datBoCuc={datBoCuc} dong={() => datChon(false)} />}
    </div>
  );
}

/** Dải tóm tắt đầu trang — ghép từ ĐÚNG hai khối đã tải (không truy vấn riêng). */
function TomTat() {
  const { data: k } = useKhoi<any>("kpi");
  if (!k) return <div className="tom-tat cho">Đang tính…</div>;
  const cau: string[] = [];
  const cg = k.khach.can_goi + k.khach.roi_bo;
  if (cg) cau.push(`${cg} khách cần gọi lại`);
  const ns = k.ngan_sach;
  if (ns?.muc_tieu_den_hom_nay != null) {
    const lech = ns.thuc_te - ns.muc_tieu_den_hom_nay;
    cau.push(lech < 0 ? `ngân sách tháng chậm ${gon(-lech)} so mốc ${pc(ns.moc)}` : `ngân sách tháng vượt mốc ${gon(lech)}`);
  } else cau.push("chưa đặt chỉ tiêu tháng này");
  if (k.kho.qua_han) cau.push(`${k.kho.qua_han} lô đã quá hạn dùng`);
  if (k.kho.het_hang) cau.push(`${k.kho.het_hang} mã hết hàng`);
  const gap = k.kho.qua_han || k.kho.het_hang || k.khach.roi_bo;
  return <div className={"tom-tat" + (gap ? " canh" : "")}>{cau.length ? cau.join(" · ").replace(/^./, c => c.toUpperCase()) + "." : "Mọi thứ ổn."}</div>;
}

function BangThem({ bo_cuc, datBoCuc, dong }: { bo_cuc: OBoCuc[]; datBoCuc: (b: OBoCuc[]) => void; dong: () => void }) {
  const [tab, datTab] = useState("tat_ca");
  const [tim, datTim] = useState("");
  const o = useRef<HTMLInputElement>(null);
  useEffect(() => { o.current?.focus(); const f = (e: KeyboardEvent) => e.key === "Escape" && dong(); document.addEventListener("keydown", f); return () => document.removeEventListener("keydown", f); }, [dong]);
  const an = Object.fromEntries(bo_cuc.map(x => [x.id, x.an]));
  const q = tim.trim().toLowerCase();
  const ds = KD.danh_muc.khoi.filter(k => (tab === "tat_ca" || k.nhom === tab) && (!q || (k.nhan + " " + k.mo_ta).toLowerCase().includes(q)));
  const soHien = bo_cuc.filter(x => !x.an).length;
  return (
    <div className="lop-phu giua" onMouseDown={dong}>
      <div className="bang-them" role="dialog" aria-modal="true" aria-label="Thêm chức năng vào dashboard" onMouseDown={e => e.stopPropagation()}>
        <div className="bang-them-dau"><strong>Thêm chức năng vào dashboard</strong>
          <span className="phu">{soHien}/{KD.danh_muc.khoi.length} đang hiện</span>
          <button type="button" className="nut-dong" aria-label="Đóng" onClick={dong}>✕</button></div>
        <input ref={o} type="search" value={tim} onChange={e => datTim(e.target.value)} placeholder="Tìm kiếm…" aria-label="Tìm chức năng" className="o-tim-nho" />
        <div className="tab-pill" role="group" aria-label="Nhóm">{KD.danh_muc.nhom.map(n =>
          <button key={n.id} type="button" aria-pressed={tab === n.id} onClick={() => datTab(n.id)}>{n.nhan}</button>)}</div>
        <div className="the-them">{ds.map(k => (
          <button key={k.id} type="button" className={"the-mod" + (an[k.id] ? "" : " on")} aria-pressed={!an[k.id]}
            onClick={() => datBoCuc(bo_cuc.map(x => x.id === k.id ? { ...x, an: !x.an } : x))}>
            <span className="the-mod-dau"><b>{k.nhan}</b>
              <span className={"nhan-vien " + (an[k.id] ? "nhat" : "ok")}>{an[k.id] ? "Thêm" : "Đang hiện"}</span></span>
            <span className="phu">{k.mo_ta}</span>
            {KD.chua_co[k.id] && <span className="nhan-vien nhat" style={{ alignSelf: "flex-start" }}>chưa có dữ liệu</span>}
          </button>))}</div>
      </div>
    </div>
  );
}
