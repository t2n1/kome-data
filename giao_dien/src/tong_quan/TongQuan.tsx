// Trang Tổng quan — Dashboard.dc.html: lời chào · thanh các bảng (056) · dải tóm
// tắt · thanh bố cục · lưới kéo thả · bảng "Thêm chức năng".
//
// Mỗi người có NHIỀU bảng có tên (app.bang_tong_quan, 056). Mọi bảng đi sẵn trong
// window.__KOME__ nên chuyển tab không gọi máy chủ; dữ liệu khối dùng lại bộ nhớ
// đệm TanStack (cùng khoá) — chỉ bố cục đổi. Bảng ảo (id null, người chưa lưu gì)
// thành dòng thật ở lần lưu đầu.
import { useEffect, useMemo, useRef, useState } from "react";
import { gui, useKhoi } from "../api";
import { gon, pc } from "../dinh_dang";
import { KD, type BangTQ, type MucKhoi, type OBoCuc } from "../khoi_dau";
import { giuKhoang } from "../khung/khoang";
import { Luoi } from "./Luoi";
import { veKhoi } from "./khoi";
import { DaiTuoi } from "./DaiTuoi";
import { ThanhBang } from "./ThanhBang";
import { BangMoi } from "./BangMoi";
import "./tong_quan.css";

const THU = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];

function gioTokyo() {
  const p = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", hour12: false, weekday: "short" }).formatToParts(new Date());
  const g = (t: string) => p.find(x => x.type === t)?.value ?? "";
  const ngay = new Date(`${g("year")}-${g("month")}-${g("day")}T00:00:00`);
  return { gio: +g("hour") % 24, chu: `${THU[ngay.getDay()]} ${g("day")}/${g("month")}/${g("year")}` };
}

const macDinh = (khoi: MucKhoi[]): OBoCuc[] => khoi.map(k => ({ id: k.id, rong: k.rong, cao: k.cao, an: false }));

/** Ghi ?bang= lên URL, giữ khoảng xem (bất biến Khoảng xem: mọi pushState qua giuKhoang). */
function ghiUrl(id: number | null, thay: boolean) {
  const p = new URLSearchParams(location.search);
  if (id === null) p.delete("bang"); else p.set("bang", String(id));
  const q = p.toString();
  const url = giuKhoang("/" + (q ? "?" + q : ""));
  if (thay) history.replaceState(null, "", url); else history.pushState(null, "", url);
}

export function TongQuan() {
  const khoi = KD.danh_muc.khoi;
  const nhanCua = useMemo(() => Object.fromEntries(khoi.map(k => [k.id, k.nhan])), [khoi]);
  const [ds, datDs] = useState<BangTQ[]>(() => KD.bang.length ? KD.bang : [{ id: null, ten: "Bảng của tôi", bo_cuc: macDinh(khoi) }]);
  const [hienId, datHienId] = useState<number | null>(KD.bang_hien_id);
  const hien = ds.find(b => b.id === hienId) ?? ds[0];
  const bo_cuc = hien.bo_cuc;
  const [chon, datChon] = useState(false);
  const [moi, datMoi] = useState(false);
  const [loiLuu, datLoiLuu] = useState("");
  // Lượt tự lưu đang chờ (400 ms sau lần kéo cuối) — ĐẨY NGAY trước khi chuyển bảng.
  const hen = useRef<{ t: number; chay?: () => Promise<BangTQ | null> }>({ t: 0 });

  const thayBang = (id: number | null, b: BangTQ) => datDs(d => d.map(x => x.id === id ? b : x));
  const luuNgay = async (): Promise<BangTQ | null> => {
    clearTimeout(hen.current.t);
    const f = hen.current.chay;
    hen.current.chay = undefined;
    return f ? f() : null;
  };

  const datBoCuc = (b: OBoCuc[]) => {
    const id = hien.id;
    thayBang(id, { ...hien, bo_cuc: b });
    if (!KD.sap_xep_duoc) return;          // máy chưa bật đăng nhập: xếp tạm, không lưu
    clearTimeout(hen.current.t);
    hen.current.chay = () => gui<{ bang: BangTQ }>(`/tong-quan/bang/${id ?? "moi"}/bo-cuc`, b)
      .then(r => {
        datLoiLuu("");
        if (id === null) { thayBang(null, r.bang); datHienId(r.bang.id); ghiUrl(r.bang.id, true); }
        return r.bang;
      })
      .catch(() => { datLoiLuu("Không lưu được bố cục — thử lại sau."); return null; });
    hen.current.t = window.setTimeout(() => { void luuNgay(); }, 400);
  };

  // Bảng ảo phải thành dòng thật trước mọi thao tác ⋯ / nhân bản.
  const damBaoCo = async (): Promise<BangTQ> => {
    const vua = await luuNgay();
    if (hien.id !== null) return hien;
    if (vua && vua.id !== null) return vua;
    const r = await gui<{ bang: BangTQ }>("/tong-quan/bang/moi/bo-cuc", hien.bo_cuc);
    thayBang(null, r.bang); datHienId(r.bang.id); ghiUrl(r.bang.id, true);
    return r.bang;
  };

  const chuyen = async (id: number | null) => {
    await luuNgay();
    datHienId(id); ghiUrl(id, false);
    // Ghi "bảng gần nhất" — lỗi thì nuốt: không phải lỗi người dùng cần thấy.
    if (id !== null && KD.sap_xep_duoc) gui(`/tong-quan/bang/${id}/mo`, null).catch(() => {});
  };

  const tao = async (ten: string, tu: string) => {
    // Bảng ảo đang có (người chưa lưu gì) được lưu thành "Bảng của tôi" trước —
    // không thì tạo bảng thứ hai xong tab đầu biến mất và người ta tưởng mất bảng.
    const dau = await damBaoCo();
    const nguon = tu === "chep" ? `chep:${dau.id}` : tu;
    const r = await gui<{ bang: BangTQ }>("/tong-quan/bang", { ten, tu: nguon });
    datDs(d => [...d, r.bang]);
    datHienId(r.bang.id); ghiUrl(r.bang.id, false);
    datMoi(false);
  };

  useEffect(() => {
    const doc = () => {
      const p = new URLSearchParams(location.search).get("bang");
      const b = ds.find(x => String(x.id) === p);
      if (b) datHienId(b.id);
    };
    window.addEventListener("popstate", doc);
    return () => window.removeEventListener("popstate", doc);
  }, [ds]);
  useEffect(() => { document.title = `Tổng quan · ${hien.ten}`; }, [hien.ten]);

  const { gio, chu } = gioTokyo();
  const ten = KD.nguoi?.ten_sale?.split(" ").slice(-1)[0] || KD.nguoi?.ten_dang_nhap;
  const chao = (gio < 11 ? "Chào buổi sáng" : gio < 18 ? "Chào buổi chiều" : "Chào buổi tối") + (ten ? `, ${ten}` : "");
  const hienIds = new Set(bo_cuc.filter(o => !o.an).map(o => o.id));

  return (
    <div className="tq">
      <div className="tieu-de-trang">
        <div><h1>{chao}</h1><div className="phu">{chu} · giờ Tokyo</div></div>
      </div>
      <ThanhBang ds={ds} hien={hien} sua_duoc={KD.sap_xep_duoc} chuyen={id => void chuyen(id)} damBaoCo={damBaoCo}
        datDs={datDs} sauXoa={id => { datHienId(id); ghiUrl(id, true); }}
        datLai={() => datBoCuc(macDinh(khoi))} moBangMoi={() => datMoi(true)} />
      <DaiTuoi />
      <TomTat />
      <div className="thanh-bo-cuc">
        {KD.sap_xep_duoc
          ? <span className="phu">⠿ kéo đầu khối để sắp xếp · đổi kích thước ở góc phải dưới</span>
          : <span className="phu">Máy này chưa bật đăng nhập — sắp xếp chỉ giữ tới khi tải lại trang.</span>}
        <span className="phu mo">{hienIds.size}/{khoi.length} chức năng đang hiện</span>
        <button type="button" className="nut-nho" onClick={() => datBoCuc(macDinh(khoi))}>Đặt lại bố cục</button>
        {loiLuu && <span className="giam phu" role="alert">{loiLuu}</span>}
        <button type="button" className="nut-chinh them" onClick={() => datChon(true)}>＋ Thêm chức năng</button>
      </div>
      <Luoi bo_cuc={bo_cuc} datBoCuc={datBoCuc} sua_duoc={true} nhan={id => nhanCua[id] ?? id} ve={id => veKhoi(id, nhanCua[id] ?? id)} />
      {chon && <BangThem bo_cuc={bo_cuc} datBoCuc={datBoCuc} dong={() => datChon(false)} />}
      {moi && <BangMoi hien={hien} ds={ds} dong={() => datMoi(false)} tao={tao} />}
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
  } else if (!k.ngan_sach_chi_theo_thang) cau.push(`chưa đặt chỉ tiêu ${k.khoang?.nhan?.toLowerCase() ?? "tháng này"}`);
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
