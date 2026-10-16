// Tab "Danh sách khách" — bố cục Customer 360.dc.html (màn tong_quan). Số THẬT
// từ /api/khach-hang/ds (một lượt gọi: trang bảng + khối tổng quan). Lọc / sắp
// / đếm làm ở máy chủ trên ảnh chụp danh bạ (kome/khach_hang.py::_khop).
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { lay } from "../api";
import { giuKhoang } from "../khung/khoang";
import { chuoiKhoang, useKhoang, voiKhoang } from "../khung/khoang";
import { gon, so, thay_doi, yen } from "../dinh_dang";
import type { BoLoc } from "./loc";
import { nhoDanhSach, thamSoDs } from "./loc";
import type { DsApi, KhachDong } from "./kieu";
import { lopHang } from "./ho_so_logic";

export const MAU_TT: Record<string, string> = {
  binh_thuong: "ok", canh_bao: "canh", da_roi_bo: "do", chua_du_lich_su: "nhat", ngung_giao_dich: "nhat",
};
export const MAU_THANG: Record<string, string> = { da_mua: "ok", tre: "canh", chua_toi_ngay: "nhat", khac: "nhat" };

const KHOA_COT = "kome_kh_cot_du_v1";

export function useDs(b: BoLoc) {
  const q = thamSoDs(b);
  const kx = chuoiKhoang(useKhoang());
  return useQuery<DsApi>({
    queryKey: ["kh-ds", q, kx], queryFn: () => lay<DsApi>(voiKhoang(`/api/khach-hang/ds${q ? "?" + q : ""}`)),
    placeholderData: keepPreviousData,
  });
}

type Dat = (sua: Partial<BoLoc>, day?: boolean) => void;

export function DanhSach({ b, dat }: { b: BoLoc; dat: Dat }) {
  const { data: d, error, isFetching } = useDs(b);
  const [tim, datTim] = useState(b.tim);
  const [chon, datChon] = useState<Record<string, boolean>>({});
  const [moLoc, datMoLoc] = useState(false);
  // Cột phụ (hạng, bình quân/tháng) ẩn mặc định cho bảng dễ đọc — tiện nghi riêng từng máy (chủ DN 2026-10-16).
  const [du, datDuS] = useState(() => { try { return localStorage.getItem(KHOA_COT) === "1"; } catch { return false; } });
  const datDu = (v: boolean) => { datDuS(v); try { localStorage.setItem(KHOA_COT, v ? "1" : "0"); } catch { /* riêng tư */ } };
  useEffect(() => { datTim(b.tim); }, [b.tim]);
  useEffect(() => {
    const h = setTimeout(() => { if (tim !== b.tim) dat({ tim }); }, 280);
    return () => clearTimeout(h);
  }, [tim]); // eslint-disable-line react-hooks/exhaustive-deps

  const t = d?.trang, tq = d?.tq;
  const tenNv = useMemo(() => Object.fromEntries((tq?.nhan_vien ?? []).map(n => [n.ma, n.ten])), [tq]);
  useEffect(() => { if (t) nhoDanhSach(t.khach.map(k => k.ma), location.pathname + location.search); }, [t]);

  if (error) return <div className="khoi-loi">Không tải được danh sách: {(error as Error).message}</div>;
  if (!d || !t || !tq) return <div className="kh-cho" aria-busy="true"><div className="khoi-cho"><span /><span /><span /></div></div>;

  const nvDang = b.nv || d.sale || d.nv_moi_nguoi;
  const coLoc = !!(b.tim || b.loc || b.nhom || b.hang.length || b.tinh || b.thang || b.co_mua || b.nv === d.pt_trong);
  const soChon = Object.values(chon).filter(Boolean).length;
  const dongChon = t.khach.filter(k => chon[k.ma]);
  const kxNhan = d.khoang?.nhan ?? "khoảng xem";
  const ssp = d.so_sanh_phu;
  const tang = t.tong_dt_ss ? t.tong_dt_khoang / t.tong_dt_ss - 1 : null;

  // Nhóm việc đang bật (đến từ trang Cần gọi hoặc link cũ ?nhom=) — 2026-10-16 bỏ dải 8 chip "Danh sách làm việc":
  // trang này chỉ còn TRA CỨU; danh sách làm việc bắt đầu ở /lien-he. Bộ lọc vẫn nhận đủ tham số cũ.
  const NHOM_TEN: Record<string, string> = { im: "Lâu chưa mua", tut: "Hạng S·A đang mua ít đi", moi: "Khách mới chưa quay lại" };
  const dangNhom = b.nhom ? NHOM_TEN[b.nhom] ?? b.nhom : b.thang === "tre" ? "Mua đều, tháng này chưa"
    : b.nv === d.pt_trong ? "Chưa ai phụ trách" : null;
  const soLocThem = b.hang.length + (b.tinh ? 1 : 0) + (b.loc ? 1 : 0) + (b.thang && b.thang !== "tre" ? 1 : 0) + (b.co_mua ? 1 : 0)
    + (b.nv && b.nv !== d.pt_trong ? 1 : 0);

  const sapCot = (cot: string, chu: string, cls = "", title?: string) => (
    <th className={"sap " + cls} title={title} aria-sort={t.sap === cot ? (b.giam === "0" ? "ascending" : b.giam === "1" ? "descending" : "none") : "none"}
      onClick={() => dat({ sap: cot, giam: t.sap === cot ? (b.giam === "0" ? "1" : "0") : "" })}>
      {chu}{t.sap === cot ? (b.giam === "0" ? " ▲" : " ▼") : ""}</th>);

  const xuatCsv = () => {
    const cot = ["Mã", "Tên", "Tỉnh", "Điện thoại", "Phụ trách", "Hạng OBC", `DT ${kxNhan}`, ssp ? `DT ${ssp.nhan}` : "So sánh", "Bình quân/tháng",
      "Tổng doanh thu đến nay", "Lâu chưa mua (so bình thường)", "Đơn cuối", "Trạng thái"];
    const dong = dongChon.map(k => [k.ma, k.ten, k.tinh ?? "", k.dien_thoai ?? "", tenNv[k.nguoi_phu_trach ?? ""] ?? k.nguoi_phu_trach ?? "",
      k.hang ?? "", k.dt_khoang ?? "", k.dt_ss ?? "", k.tb_3_thang ?? "", k.doanh_thu,
      k.ty_le_im_lang ?? "", k.lan_cuoi ?? "", d.nhan_trang_thai[k.trang_thai] ?? k.trang_thai]);
    const csv = "﻿" + [cot, ...dong].map(r => r.map(x => `"${String(x).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = `khach-hang-${soChon}.csv`; a.click(); URL.revokeObjectURL(a.href);
  };

  const dau = (t.trang - 1) * t.co;

  return (
    <div className={"kh-ds" + (isFetching ? " dang-tai" : "")}>
      {d.sale && <p className="kh-loc-nguoi">Đang xem khách của <strong>{d.ten_sale ?? d.sale}</strong>.{" "}
        <button type="button" className="lien-ket" onClick={() => dat({ nv: d.nv_moi_nguoi })}>Xem tất cả →</button></p>}

      <p className="kh-tom-tat">
        <b>{so(t.tong)}</b> khách{t.tong !== tq.tong_tat_ca && <span className="nhat-chu"> (trên tổng {so(tq.tong_tat_ca)})</span>} · doanh thu {kxNhan}{" "}
        <b title={yen(t.tong_dt_khoang)}>{gon(t.tong_dt_khoang)}</b>
        {ssp?.co && tang != null && <span className={tang >= 0 ? "tang" : "giam"}> ({thay_doi(tang)} so {ssp.nhan})</span>}
        {t.so_can_xu_ly > 0 && <> · <a href="/lien-he">{so(t.so_can_xu_ly)} khách lâu chưa mua — xem ở Cần gọi →</a></>}
      </p>

      {dangNhom && <p className="kh-dang-nhom">Đang xem nhóm <b>{dangNhom}</b>{" "}
        <button type="button" className="nut-nho" onClick={() => dat({ nhom: "", thang: b.thang === "tre" ? "" : b.thang,
          nv: b.nv === d.pt_trong ? "" : b.nv }, true)}>✕ Bỏ nhóm</button></p>}

      <div className="kh-cong-cu">
        <input type="search" className="kh-tim" placeholder={`Tìm mã, tên, điện thoại, địa chỉ, số TK chuyển khoản… (${so(tq.tong_tat_ca)} khách)`}
          value={tim} onChange={e => datTim(e.target.value)} aria-label="Tìm khách hàng" />
        <button type="button" className="nut-nho" aria-expanded={moLoc || soLocThem > 0} aria-controls="kh-loc-them"
          onClick={() => datMoLoc(!(moLoc || soLocThem > 0))}>Lọc thêm{soLocThem ? ` (${soLocThem})` : ""} ▾</button>
        <button type="button" className="nut-nho" disabled={!coLoc}
          onClick={() => { datTim(""); dat({ tim: "", loc: "", nhom: "", hang: [], tinh: "", thang: "", co_mua: false, nv: b.nv === d.pt_trong ? "" : b.nv }, true); }}>Xoá lọc</button>
      </div>
      {(moLoc || soLocThem > 0) && <div className="kh-cong-cu kh-loc-them" id="kh-loc-them">
        <div className="kh-hang" role="group" aria-label="Hạng OBC (得意先ランク)">
          {tq.hang.map(([h]) => (
            <button key={h} type="button" aria-pressed={b.hang.includes(h)} title={`Hạng OBC ${h}`}
              onClick={() => dat({ hang: b.hang.includes(h) ? b.hang.filter(x => x !== h) : [...b.hang, h] })}>{h}</button>))}
        </div>
        <label className="kh-chon"><span>Phụ trách</span>
          <select value={nvDang} onChange={e => dat({ nv: e.target.value, tat_ca: false })}>
            <option value={d.nv_moi_nguoi}>Mọi nhân viên</option>
            <option value={d.pt_trong}>Chưa ai phụ trách</option>
            {tq.nhan_vien.map(n => <option key={n.ma} value={n.ma}>{n.ten}</option>)}
            {d.sale && d.sale !== d.pt_trong && !tq.nhan_vien.some(n => n.ma === d.sale) && <option value={d.sale}>{d.sale}</option>}
          </select></label>
        <label className="kh-chon"><span>Tỉnh</span>
          <select value={b.tinh} onChange={e => dat({ tinh: e.target.value })}>
            <option value="">Mọi tỉnh</option>
            {tq.tinh_day_du.map(([ten, n]) => {
              const v = ten === d.khong_ro ? d.tinh_trong : ten;
              return <option key={v} value={v}>{ten} ({so(n)})</option>;
            })}
            {b.tinh && !tq.tinh_day_du.some(([ten]) => (ten === d.khong_ro ? d.tinh_trong : ten) === b.tinh) &&
              <option value={b.tinh}>{b.tinh === d.tinh_trong ? d.khong_ro : b.tinh}</option>}
          </select></label>
        <label className="kh-chon"><span>Trạng thái</span>
          <select value={b.loc} onChange={e => dat({ loc: e.target.value })}>
            <option value="">Mọi trạng thái</option>
            {Object.entries(d.nhan_trang_thai).map(([k, v]) => <option key={k} value={k}>{v} ({so(tq.dem_trang_thai[k] ?? 0)})</option>)}
          </select></label>
        <label className="kh-chon"><span>Tháng này</span>
          <select value={b.thang} onChange={e => dat({ thang: e.target.value })}>
            <option value="">Mọi khách</option>
            {Object.entries(d.nhan_thang).filter(([k]) => k !== "khong_goi").map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></label>
        <label className="kh-chon kh-co-mua"><input type="checkbox" checked={b.co_mua}
          onChange={e => dat({ co_mua: e.target.checked })} /> <span>Có mua · {kxNhan} ({so(tq.co_mua)})</span></label>
      </div>}

      {soChon > 0 && <div className="kh-thanh-chon">
        <b>{soChon} khách đã chọn</b>
        <button type="button" className="nut-nho" onClick={() => datChon(Object.fromEntries(t.khach.map(k => [k.ma, true])))}>Chọn cả {t.khach.length} khách trang này</button>
        <span className="day-phai">
          <button type="button" className="nut-nho" disabled title="Chưa có nơi giao việc cho nhân viên trong hệ thống.">Giao cho nhân viên</button>
          <button type="button" className="nut-nho" disabled title="Danh sách gọi là trang Cần liên hệ — tự tính theo nhịp mua, không thêm tay.">Thêm vào danh sách gọi</button>
          <button type="button" className="nut-nho chinh" onClick={xuatCsv}>⤓ Xuất CSV</button>
          <button type="button" className="nut-nho" onClick={() => datChon({})}>Bỏ chọn</button>
        </span>
      </div>}

      <div className="kh-cot-them">
        <button type="button" className="nut-nho" aria-pressed={du} onClick={() => datDu(!du)}>
          {du ? "− Bớt cột" : "＋ Thêm cột (hạng OBC, bình quân/tháng)"}</button>
      </div>
      <div className="bang-cuon kh-bang-khung">
        <table className="bang kh-bang">
          <thead><tr>
            <th className="kh-o-chon"><input type="checkbox" aria-label="Chọn cả trang"
              checked={t.khach.length > 0 && t.khach.every(k => chon[k.ma])}
              onChange={e => datChon(e.target.checked ? Object.fromEntries(t.khach.map(k => [k.ma, true])) : {})} /></th>
            {sapCot("ten", "Khách hàng")}{du && sapCot("hang", "Hạng", "", "hạng OBC (得意先ランク)")}{sapCot("pt", "Phụ trách")}
            {sapCot("dt_khoang", "Doanh thu", "so", `doanh thu thuần ${kxNhan}`)}{sapCot("so_khoang", ssp ? `So với ${ssp.nhan}` : "So sánh", "", ssp ? `${ssp.tu} → ${ssp.den}` : undefined)}
            {du && sapCot("tb3", "Bình quân/tháng", "so")}{sapCot("don_cuoi", "Lần mua cuối", "so", "số ngày từ lần đặt hàng cuối; đỏ = lâu hơn nhiều so với bình thường của khách")}
            {sapCot("trang_thai", "Trạng thái")}
          </tr></thead>
          <tbody>
            {t.khach.map(k => <Dong key={k.ma} k={k} d={d} du={du} tenNv={tenNv} chon={!!chon[k.ma]}
              datChon={v => datChon(c => ({ ...c, [k.ma]: v }))} />)}
            {!t.khach.length && <tr><td colSpan={du ? 9 : 7} className="trong">Không có khách hàng nào khớp bộ lọc. Thử bỏ bớt điều kiện hoặc xoá ô tìm kiếm.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="kh-phan-trang">
        <span className="phu">Hiện {t.tong ? dau + 1 : 0}–{dau + t.khach.length} trong {so(t.tong)} khách · doanh thu {kxNhan} của nhóm {yen(t.tong_dt_khoang)}</span>
        <span className="day-phai">
          <button type="button" className="nut-nho" disabled={t.trang <= 1} onClick={() => dat({ trang: t.trang - 1 })}>‹ Trước</button>
          {cacTrang(t.trang, t.so_trang).map((p, i) => p === 0 ? <span key={"g" + i} className="phu">…</span> :
            <button key={p} type="button" className="nut-nho" aria-current={p === t.trang ? "page" : undefined}
              onClick={() => dat({ trang: p })}>{p}</button>)}
          <button type="button" className="nut-nho" disabled={t.trang >= t.so_trang} onClick={() => dat({ trang: t.trang + 1 })}>Sau ›</button>
          <select value={t.co} onChange={e => dat({ co: +e.target.value })} aria-label="Số dòng mỗi trang">
            {[50, 100, 200].map(n => <option key={n} value={n}>{n} dòng</option>)}
          </select>
        </span>
      </div>

    </div>
  );
}

function cacTrang(tr: number, tong: number): number[] {
  const s = new Set([1, tong, tr - 1, tr, tr + 1].filter(p => p >= 1 && p <= tong));
  const ds = [...s].sort((a, b) => a - b), ra: number[] = [];
  ds.forEach((p, i) => { if (i && p - ds[i - 1] > 1) ra.push(0); ra.push(p); });
  return ra;
}

function Dong({ k, d, du, tenNv, chon, datChon }: { k: KhachDong; d: DsApi; du: boolean; tenNv: Record<string, string>;
  chon: boolean; datChon: (v: boolean) => void }) {
  const ss = k.dt_ss ? (k.dt_khoang ?? 0) / k.dt_ss - 1 : null;
  const mo = () => { location.href = giuKhoang(`/khach-hang/${encodeURIComponent(k.ma)}`); };
  return (
    <tr className={"kh-dong" + (chon ? " chon" : "")} onClick={e => { if (!(e.target as HTMLElement).closest("input,a")) mo(); }}>
      <td className="kh-o-chon"><input type="checkbox" checked={chon} onChange={e => datChon(e.target.checked)} aria-label={`Chọn ${k.ten}`} /></td>
      <td className="kh-ten"><a href={`/khach-hang/${encodeURIComponent(k.ma)}`} className="ten-jp">{k.ten}</a>
        <div className="ma-nho"><code>{k.ma}</code>{k.tinh ? ` · ${k.tinh}` : ""}{k.dau_hieu_obc ? ` · ※${k.dau_hieu_obc}※` : ""}</div></td>
      {du && <td>{k.hang ? <span className={"kh-hang-nhan " + lopHang(k.hang)} title={k.hang_ten ?? undefined}>{k.hang}</span> : <span className="nhat-chu">—</span>}</td>}
      <td className="kh-pt">{k.nguoi_phu_trach ? (tenNv[k.nguoi_phu_trach] ?? k.nguoi_phu_trach) : <span className="nhat-chu">— chưa giao —</span>}</td>
      <td className="so"><b>{k.dt_khoang == null ? "—" : yen(k.dt_khoang)}</b></td>
      <td className="kh-ss">{ss == null ? <span className="nhat-chu">{k.dt_ss == null ? "—" : k.dt_khoang ? "kỳ so chưa mua" : "—"}</span> : <>
        <span className="kh-ss-thanh"><i className={ss >= 0 ? "tang" : ss > -0.2 ? "canh" : "giam"}
          style={{ width: `${Math.min(50, Math.abs(ss) * 50)}%`, [ss >= 0 ? "left" : "right"]: "50%" } as React.CSSProperties} /></span>
        <span className={ss >= 0 ? "tang" : ss > -0.2 ? "canh-chu" : "giam"}>{thay_doi(ss, 0)}</span></>}</td>
      {du && <td className="so">{k.tb_3_thang == null ? "—" : gon(k.tb_3_thang)}</td>}
      <td className={"so " + ((k.ty_le_im_lang ?? 0) >= 3 ? "giam" : (k.ty_le_im_lang ?? 0) >= 1.5 ? "canh-chu" : "nhat-chu")}
        title={k.nhip_ngay ? `bình thường ${Math.round(k.nhip_ngay)} ngày mua một lần` : "mua chưa đủ 3 lần, chưa biết thói quen"}>
        {k.so_ngay_im_lang == null ? "—" : k.so_ngay_im_lang === 0 ? "mới mua" : `${k.so_ngay_im_lang} ngày trước`}</td>
      <td><span className={"nhan-vien " + (MAU_TT[k.trang_thai] ?? "nhat")}>{d.nhan_trang_thai[k.trang_thai] ?? k.trang_thai}</span>
        {k.nhan_thang === "tre" && <span className="nhan-vien canh kh-nhan-thang" title={d.nhan_thang.tre}>tháng này chưa</span>}</td>
    </tr>
  );
}

