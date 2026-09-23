// Tab "Danh sách khách" — bố cục Customer 360.dc.html (màn tong_quan). Số THẬT
// từ /api/khach-hang/ds (một lượt gọi: trang bảng + khối tổng quan). Lọc / sắp
// / đếm làm ở máy chủ trên ảnh chụp danh bạ (kome/khach_hang.py::_khop).
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { lay } from "../api";
import { gon, so, thay_doi, yen } from "../dinh_dang";
import type { BoLoc } from "./loc";
import { nhoDanhSach, thamSoDs } from "./loc";
import type { DsApi, KhachDong } from "./kieu";

const CHUA_CO_NO = "Cần sổ công nợ (請求先元帳 / 入金伝票) — chưa có bộ nạp.";
export const MAU_TT: Record<string, string> = {
  binh_thuong: "ok", canh_bao: "canh", da_roi_bo: "do", chua_du_lich_su: "nhat", ngung_giao_dich: "nhat",
};
export const MAU_THANG: Record<string, string> = { da_mua: "ok", tre: "canh", chua_toi_ngay: "nhat", khac: "nhat" };

export function useDs(b: BoLoc) {
  const q = thamSoDs(b);
  return useQuery<DsApi>({
    queryKey: ["kh-ds", q], queryFn: () => lay<DsApi>(`/api/khach-hang/ds${q ? "?" + q : ""}`),
    placeholderData: keepPreviousData,
  });
}

type Dat = (sua: Partial<BoLoc>, day?: boolean) => void;

function tenThang(iso: string | null) {
  if (!iso) return "tháng này";
  return `tháng ${+iso.slice(5, 7)}`;
}

export function DanhSach({ b, dat }: { b: BoLoc; dat: Dat }) {
  const { data: d, error, isFetching } = useDs(b);
  const [tim, datTim] = useState(b.tim);
  const [chon, datChon] = useState<Record<string, boolean>>({});
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
  const coLoc = !!(b.tim || b.loc || b.nhom || b.hang.length || b.tinh || b.thang || b.nv === d.pt_trong);
  const soChon = Object.values(chon).filter(Boolean).length;
  const dongChon = t.khach.filter(k => chon[k.ma]);
  const tang = t.tong_dt_thang_truoc_cung_ngay ? t.tong_dt_thang_nay / t.tong_dt_thang_truoc_cung_ngay - 1 : null;
  const ngayMoc = d.hom_nay ? +d.hom_nay.slice(8, 10) : null;

  const PHAN_KHUC: { ma: string; ten: string; mo: string; so: number | null; bat: boolean; ap: Partial<BoLoc> | null }[] = [
    { ma: "tat_ca", ten: "Toàn bộ danh bạ", mo: `${so(tq.tong)} khách${d.sale ? " của " + (d.ten_sale ?? d.sale) : " trong hệ thống"}`,
      so: tq.tong, bat: !b.nhom && !b.thang && b.nv !== d.pt_trong, ap: { nhom: "", thang: "", nv: b.nv === d.pt_trong ? "" : b.nv } },
    { ma: "no", ten: "Nợ quá hạn", mo: "cần thu trước khi giao đơn mới", so: null, bat: false, ap: null },
    { ma: "im", ten: "Im lặng ≥ 2× nhịp", mo: "đã quá chu kỳ mua thường lệ", so: tq.nhom.im, bat: b.nhom === "im", ap: { nhom: "im", thang: "" } },
    { ma: "tut", ten: "Hạng S·A đang tụt", mo: "30 ngày < 80% TB ba kỳ 30 ngày trước", so: tq.nhom.tut, bat: b.nhom === "tut", ap: { nhom: "tut", thang: "" } },
    { ma: "moi", ten: "Khách mới chưa quay lại", mo: "đơn đầu trong 90 ngày, đã im ≥ 1,2× nhịp", so: tq.nhom.moi, bat: b.nhom === "moi", ap: { nhom: "moi", thang: "" } },
    { ma: "thang", ten: "Mua đều, tháng này chưa", mo: "≥ 2/3 tháng trước có đơn đến ngày này", so: tq.thang.tre ?? 0, bat: b.thang === "tre", ap: { thang: "tre", nhom: "" } },
    { ma: "chuapt", ten: "Chưa ai phụ trách", mo: "mã phụ trách không có trong danh sách 担当者 · cả công ty", so: tq.chua_pt, bat: b.nv === d.pt_trong, ap: { nv: d.pt_trong, nhom: "", thang: "" } },
  ];

  const sapCot = (cot: string, chu: string, cls = "", title?: string) => (
    <th className={"sap " + cls} title={title} aria-sort={t.sap === cot ? (b.giam === "0" ? "ascending" : b.giam === "1" ? "descending" : "none") : "none"}
      onClick={() => dat({ sap: cot, giam: t.sap === cot ? (b.giam === "0" ? "1" : "0") : "" })}>
      {chu}{t.sap === cot ? (b.giam === "0" ? " ▲" : " ▼") : ""}</th>);

  const xuatCsv = () => {
    const cot = ["Mã", "Tên", "Tỉnh", "Điện thoại", "Phụ trách", "Hạng theo doanh thu 12 tháng", "DT tháng này", "Tháng trước cùng ngày", "TB 3 tháng",
      "Doanh thu luỹ kế", "Im lặng (× nhịp)", "Đơn cuối", "Trạng thái"];
    const dong = dongChon.map(k => [k.ma, k.ten, k.tinh ?? "", k.dien_thoai ?? "", tenNv[k.nguoi_phu_trach ?? ""] ?? k.nguoi_phu_trach ?? "",
      k.hang ?? "", k.thang_nay ?? "", k.thang_truoc_cung_ngay ?? "", k.tb_3_thang ?? "", k.doanh_thu,
      k.ty_le_im_lang ?? "", k.lan_cuoi ?? "", d.nhan_trang_thai[k.trang_thai] ?? k.trang_thai]);
    const csv = "﻿" + [cot, ...dong].map(r => r.map(x => `"${String(x).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = `khach-hang-${soChon}.csv`; a.click(); URL.revokeObjectURL(a.href);
  };

  const maxHang = Math.max(1, ...tq.hang.map(h => h[1]));
  const tinh6 = tq.tinh.slice(0, 6), maxTinh = Math.max(1, ...tinh6.map(x => x[1]));
  const maxNv = Math.max(1, ...tq.nhan_vien.map(n => n.so_khach));
  const dau = (t.trang - 1) * t.co;

  return (
    <div className={"kh-ds" + (isFetching ? " dang-tai" : "")}>
      {d.sale && <p className="kh-loc-nguoi">Đang xem khách của <strong>{d.ten_sale ?? d.sale}</strong>.{" "}
        <button type="button" className="lien-ket" onClick={() => dat({ nv: d.nv_moi_nguoi })}>Xem tất cả →</button></p>}

      <div className="o-kpi-luoi kh-kpi">
        <div className="o-kpi"><div className="nhan">Khách đang lọc</div><div className="gia">{so(t.tong)}</div>
          <div className="dong-phu nhat-chu">trên tổng {so(tq.tong_tat_ca)} · {so(t.so_can_xu_ly)} cần xử lý</div></div>
        <div className="o-kpi"><div className="nhan">Doanh thu {tenThang(d.hom_nay)}{ngayMoc ? ` (đến ngày ${ngayMoc})` : ""}</div>
          <div className="gia">{gon(t.tong_dt_thang_nay)}</div>
          <div className={"dong-phu " + (tang == null ? "nhat-chu" : tang >= 0 ? "tang" : "giam")}>
            {tang == null ? "tháng trước cùng ngày chưa có đơn" : `${thay_doi(tang)} so tháng trước cùng ngày`}</div></div>
        <div className="o-kpi"><div className="nhan">Im lặng ≥ 2× nhịp</div><div className="gia">{so(t.so_can_xu_ly)}</div>
          <div className="dong-phu nhat-chu">đã quá chu kỳ mua thường lệ</div></div>
        <div className="o-kpi chua" title={CHUA_CO_NO}><div className="nhan">Công nợ quá hạn</div><div className="gia">chưa có dữ liệu</div>
          <div className="dong-phu nhat-chu">cần sổ công nợ</div></div>
      </div>

      <div className="kh-muc"><h2>Danh sách làm việc</h2><span className="phu">chọn một nhóm để lọc danh bạ · số đếm theo người phụ trách đang xem</span></div>
      <div className="kh-phan-khuc">
        {PHAN_KHUC.map(p => (
          <button key={p.ma} type="button" className="kh-pk" aria-pressed={p.bat} disabled={!p.ap}
            title={p.ap ? undefined : CHUA_CO_NO} onClick={() => p.ap && dat(p.ap, true)}>
            <span className="kh-pk-dau"><b>{p.ten}</b><span className={"kh-pk-so" + (p.so ? " co" : "")}>{p.so == null ? "chưa có" : so(p.so)}</span></span>
            <span className="kh-pk-mo">{p.ma === "no" ? "chưa có dữ liệu công nợ" : p.mo}</span>
          </button>))}
      </div>

      <div className="kh-cong-cu">
        <input type="search" className="kh-tim" placeholder={`Tìm mã, tên, điện thoại, địa chỉ… (${so(tq.tong_tat_ca)} khách)`}
          value={tim} onChange={e => datTim(e.target.value)} aria-label="Tìm khách hàng" />
        <div className="kh-hang" role="group" aria-label="Hạng theo doanh thu 12 tháng">
          {["S", "A", "B", "C", "D"].map(h => (
            <button key={h} type="button" aria-pressed={b.hang.includes(h)} title={`Hạng ${h} theo doanh thu 12 tháng`}
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
        <label className="kh-chon" title="OBC chỉ xuất MÃ phân loại khách, không xuất tên — chưa hiện được loại hình.">
          <span>Loại hình</span><select disabled><option>chưa có tên loại hình</option></select></label>
        <button type="button" className="nut-nho" disabled={!coLoc}
          onClick={() => { datTim(""); dat({ tim: "", loc: "", nhom: "", hang: [], tinh: "", thang: "", nv: b.nv === d.pt_trong ? "" : b.nv }, true); }}>Xoá lọc</button>
      </div>

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

      <div className="bang-cuon kh-bang-khung">
        <table className="bang kh-bang">
          <thead><tr>
            <th className="kh-o-chon"><input type="checkbox" aria-label="Chọn cả trang"
              checked={t.khach.length > 0 && t.khach.every(k => chon[k.ma])}
              onChange={e => datChon(e.target.checked ? Object.fromEntries(t.khach.map(k => [k.ma, true])) : {})} /></th>
            {sapCot("ten", "Khách hàng")}{sapCot("hang", "Hạng", "", "hạng theo doanh thu 12 tháng (không phải 得意先ランク)")}{sapCot("pt", "Phụ trách")}
            {sapCot("thang_nay", `DT ${tenThang(d.hom_nay)}`, "so")}{sapCot("so_thang_truoc", "So tháng trước")}
            {sapCot("tb3", "TB 3 tháng", "so")}{sapCot("im_lang", "Im lặng", "so")}{sapCot("don_cuoi", "Đơn cuối", "so")}
            {sapCot("trang_thai", "Trạng thái")}
          </tr></thead>
          <tbody>
            {t.khach.map(k => <Dong key={k.ma} k={k} d={d} tenNv={tenNv} chon={!!chon[k.ma]}
              datChon={v => datChon(c => ({ ...c, [k.ma]: v }))} />)}
            {!t.khach.length && <tr><td colSpan={10} className="trong">Không có khách hàng nào khớp bộ lọc. Thử bỏ bớt điều kiện hoặc xoá ô tìm kiếm.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="kh-phan-trang">
        <span className="phu">Hiện {t.tong ? dau + 1 : 0}–{dau + t.khach.length} trong {so(t.tong)} khách · doanh thu luỹ kế nhóm {yen(t.tong_doanh_thu)}</span>
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

      <div className="kh-ba-khoi">
        <section className="kh-the"><h2>Phân bố theo hạng doanh thu 12 tháng</h2><p className="phu">không phải 得意先ランク của OBC</p>
          {tq.hang.map(([h, n]) => (
            <button key={h} type="button" className="kh-thanh-dong" aria-pressed={b.hang.includes(h)}
              onClick={() => dat({ hang: b.hang.includes(h) ? b.hang.filter(x => x !== h) : [h] })}>
              <span className="kh-td-nhan"><b title="hạng theo doanh thu 12 tháng">Hạng {h}</b><span>{so(n)} khách · {gon(tq.hang_tien[h] ?? 0)}</span></span>
              <span className="kh-td-thanh"><i style={{ width: `${n / maxHang * 100}%` }} /></span>
            </button>))}
        </section>
        <section className="kh-the"><h2>Tập trung ở đâu</h2><p className="phu">6 tỉnh đông khách nhất · bấm để lọc</p>
          {tinh6.map(([ten, n]) => {
            const v = ten === d.khong_ro ? d.tinh_trong : ten;
            return (
              <button key={ten} type="button" className="kh-thanh-dong" aria-pressed={b.tinh === v}
                onClick={() => dat({ tinh: b.tinh === v ? "" : v })}>
                <span className="kh-td-nhan"><b className="ten-jp">{ten}</b><span>{so(n)} · {gon(tq.tinh_tien[ten] ?? 0)}</span></span>
                <span className="kh-td-thanh mong"><i style={{ width: `${n / maxTinh * 100}%` }} /></span>
              </button>);
          })}
        </section>
        <section className="kh-the"><h2>Tải của từng nhân viên</h2><p className="phu">đỏ = cần gọi lại (nhóm im lặng ≥ 2× nhịp) · bấm để lọc</p>
          {tq.nhan_vien.map(n => (
            <button key={n.ma} type="button" className="kh-thanh-dong" aria-pressed={nvDang === n.ma}
              onClick={() => dat({ nv: nvDang === n.ma ? d.nv_moi_nguoi : n.ma })}>
              <span className="kh-td-nhan"><b>{n.ten}</b><span>{so(n.so_khach)} khách · {so(n.canh_bao)} cần xử lý · {gon(n.doanh_thu)}</span></span>
              <span className="kh-td-thanh mong doi" style={{ width: `${n.so_khach / maxNv * 100}%` }}>
                <i className="do" style={{ width: `${n.so_khach ? n.canh_bao / n.so_khach * 100 : 0}%` }} /><i /></span>
            </button>))}
        </section>
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

function Dong({ k, d, tenNv, chon, datChon }: { k: KhachDong; d: DsApi; tenNv: Record<string, string>;
  chon: boolean; datChon: (v: boolean) => void }) {
  const ss = k.thang_truoc_cung_ngay ? (k.thang_nay ?? 0) / k.thang_truoc_cung_ngay - 1 : null;
  const mo = () => { location.href = `/khach-hang/${encodeURIComponent(k.ma)}`; };
  return (
    <tr className={"kh-dong" + (chon ? " chon" : "")} onClick={e => { if (!(e.target as HTMLElement).closest("input,a")) mo(); }}>
      <td className="kh-o-chon"><input type="checkbox" checked={chon} onChange={e => datChon(e.target.checked)} aria-label={`Chọn ${k.ten}`} /></td>
      <td className="kh-ten"><a href={`/khach-hang/${encodeURIComponent(k.ma)}`} className="ten-jp">{k.ten}</a>
        <div className="ma-nho"><code>{k.ma}</code>{k.tinh ? ` · ${k.tinh}` : ""}{k.dau_hieu_obc ? ` · ※${k.dau_hieu_obc}※` : ""}</div></td>
      <td>{k.hang ? <span className={"kh-hang-nhan h" + k.hang}>{k.hang}</span> : <span className="nhat-chu">—</span>}</td>
      <td className="kh-pt">{k.nguoi_phu_trach ? (tenNv[k.nguoi_phu_trach] ?? k.nguoi_phu_trach) : <span className="nhat-chu">— chưa giao —</span>}</td>
      <td className="so"><b>{k.thang_nay == null ? "—" : yen(k.thang_nay)}</b></td>
      <td className="kh-ss">{ss == null ? <span className="nhat-chu">{k.thang_nay ? "tháng trước chưa mua" : "—"}</span> : <>
        <span className="kh-ss-thanh"><i className={ss >= 0 ? "tang" : ss > -0.2 ? "canh" : "giam"}
          style={{ width: `${Math.min(50, Math.abs(ss) * 50)}%`, [ss >= 0 ? "left" : "right"]: "50%" } as React.CSSProperties} /></span>
        <span className={ss >= 0 ? "tang" : ss > -0.2 ? "canh-chu" : "giam"}>{thay_doi(ss, 0)}</span></>}</td>
      <td className="so">{k.tb_3_thang == null ? "—" : gon(k.tb_3_thang)}</td>
      <td className={"so " + ((k.ty_le_im_lang ?? 0) >= 3 ? "giam" : (k.ty_le_im_lang ?? 0) >= 1.5 ? "canh-chu" : "")}
        title={k.nhip_ngay ? `im ${k.so_ngay_im_lang} ngày · nhịp ${Math.round(k.nhip_ngay)} ngày` : "chưa đủ 3 lần mua để có nhịp"}>
        {k.ty_le_im_lang == null ? "—" : `${k.ty_le_im_lang.toFixed(1).replace(".", ",")}×`}</td>
      <td className="so nhat-chu">{k.so_ngay_im_lang == null ? "—" : `${k.so_ngay_im_lang}n`}</td>
      <td><span className={"nhan-vien " + (MAU_TT[k.trang_thai] ?? "nhat")}>{d.nhan_trang_thai[k.trang_thai] ?? k.trang_thai}</span>
        {k.nhan_thang === "tre" && <span className="nhan-vien canh kh-nhan-thang" title={d.nhan_thang.tre}>tháng này chưa</span>}</td>
    </tr>
  );
}

