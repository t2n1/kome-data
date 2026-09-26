// Báo cáo doanh thu (/bao-cao) — bố cục Báo cáo.dc.html. Mọi con số + hình học
// biểu đồ từ /api/bao-cao: hình học vẫn tính ở kome/bao_cao.py và
// kome/ve_phan_tich.py (các bất biến đối soát / "không vẽ" / cắt đường khi
// không có cùng kỳ có test ở đó) — màn này chỉ vẽ và thêm tương tác.
// Lệch có chủ ý so với gói thiết kế: tab "Lãi gộp" của khối ngân sách vô hiệu
// (chỉ có ngân sách DOANH THU); "Khách hiện hữu / khách mới" chưa có định nghĩa
// trong mart; điểm dự báo trên đường luỹ kế nằm ở /du-bao (không bịa ở đây).
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { lay } from "../api";
import { chuoiKhoang, useKhoang, voiKhoang, type KhoangMayChu } from "../khung/khoang";
import { ChuaCoDuLieu } from "../chung/Khoi";
import { gon, ngay, so, yen } from "../dinh_dang";
import { KD } from "../khoi_dau";
import "./bao_cao.css";

type O = { thang: string; doanh_thu: number; lai_gop: number; ty_suat: number | null; co_cung_ky: boolean;
  tang_truong: number | null; la_thang_chot: boolean; so_phieu: number; so_khach: number; dt_cung_ky: number | null };
type Ky = { company_fy: number; so_ky: number; nhan: string; doanh_thu: number; lai_gop: number; ty_suat: number | null;
  so_khach: number; so_phieu: number; so_thang: number; ngay_dau: string | null; ngay_cuoi: string | null };
type CungKy = { so_thang: number; tu: string | null; den: string | null; tang_dt: number | null; tang_lg: number | null;
  tang_khach: number | null; chenh_ty_suat: number | null };
/** Một phép so của khoảng xem dạng Tháng / Khoảng (kome/bao_cao.py::SoSanhSo). */
type SoSanhSo = { ma: string; nhan: string; co: boolean; tu: string; den: string; tu_nay: string; den_nay: string;
  tang_dt: number | null; tang_lg: number | null; tang_khach: number | null; chenh_ty_suat: number | null };
type KhTT = { ma: string; ten: string; doanh_thu: number; thu_hang: number; ty_trong: number | null; luy_ke: number | null };
type Nguoi = { ma: string; ten: string | null; thuc_te: number; muc_tieu: number | null; muc_tieu_den_hom_nay: number | null;
  tien_do: number | null; cung_ky: number | null; co_cung_ky: boolean; tang_truong: number | null; rong_thanh: number | null; rong_moc: number | null;
  muc_tieu_lg: number | null; thuc_te_lg: number; muc_tieu_lg_den_hom_nay: number | null; tien_do_lg: number | null;
  rong_thanh_lg: number | null; rong_moc_lg: number | null };
type Td = { company_fy: number; thang: string; hom_nay: string | null; ngay_kd: number; ngay_kd_da_qua: number; thuc_te: number;
  muc_tieu: number | null; muc_tieu_den_hom_nay: number | null; tien_do: number | null; nguoi: Nguoi[]; co_ngan_sach: boolean;
  rong_thanh: number | null; rong_moc: number | null; pct_moc_chi_tieu: number | null;
  // 041: lãi gộp của CÔNG TY (ngân sách công ty nhập thẳng).
  co_ngan_sach_lg: boolean; thuc_te_lg: number; muc_tieu_lg: number | null; muc_tieu_lg_den_hom_nay: number | null;
  tien_do_lg: number | null; rong_thanh_lg: number | null; rong_moc_lg: number | null; pct_moc_chi_tieu_lg: number | null };
type Spark = { co: boolean; rong: number; cao: number; doan: string[]; diem_don: [number, number][] };
type BaoCaoApi = {
  khoang: KhoangMayChu | null;
  bc: { ky: Ky; moi_ky: Ky[]; thang: O[]; hang: { ma: string; ten: string; nhom: string; doanh_thu: number | null; lai_gop: number | null; ty_suat: number | null; so_khach: number }[];
    nhan_vien: { ma: string | null; doanh_thu: number; lai_gop: number; ty_suat: number | null; so_khach: number; so_phieu: number }[];
    khong_co_du_lieu: boolean; canh_bao: string[]; cung_ky: CungKy | null; so_sanh: SoSanhSo[]; tap_trung: { dong: KhTT[]; so_khach: number; luy_ke_top10: number | null } | null;
    phi: { doanh_thu: number; lai_gop: number; dong: { ma: string; ten: string; doanh_thu: number | null; lai_gop: number | null; so_khach: number }[] } };
  td: Td | null;
  td_phu: { ngay_kd_con_lai: number; can_ban_moi_ngay: number | null; nhip_chuan: number | null; thieu_moc: number | null } | null;
  so_nho: Record<"dt" | "lg" | "ts" | "kh", Spark>;
  lk_lg: BaoCaoApi["lk"]; td_phu_lg: BaoCaoApi["td_phu"];
  lk: { co: boolean; rong: number; cao: number; ngan_sach: string; thuc_te: string; nhan: { x: number; thang: string; hien: boolean }[]; dinh: number };
  bd: { co: boolean; rong: number; cao: number; cot: { x: number; y: number; w: number; h: number; o: O }[]; diem: [number, number, O][];
    duong: string; duong_ck: string[]; ts_lo: number; ts_hi: number };
  dg: { co: boolean; rong: number; cao: number; x0: number; cao_hang: number; thanh: { nganh: string; x: number; w: number; y: number; am: boolean;
    tang_truong: number | null; nhan: string; nhan_x: number; nhan_neo: string; nhan_trong: boolean }[] };
  co: { co: boolean; rong: number; cao: number; khong_ve: number; so_ma_khong_ve: number; nganh: { nganh: string; x: number; y: number; w: number; h: number;
    bac: string; doanh_thu: number; tang_truong: number | null; ma: { ten: string; x: number; y: number; w: number; h: number; doanh_thu: number; nhan: string }[] }[] };
  nh: { co: boolean; thang: string[]; thang_dau_du_lieu: string | null; hang: { nganh: string; o: { thang: string; nganh: string; bac: string;
    tang_truong: number | null; doanh_thu: number; co_the_ck?: boolean }[] }[] };
  pa: { co: boolean; rong: number; cao: number; cot: { x: number; y: number; w: number; h: number; khach: KhTT }[]; doan: string[];
    diem: { x: number; y: number; khach: KhTT }[]; dinh: number; truc_pct: { y: number; nhan: string }[] };
  ngay_dau_du_lieu: string | null;
};

const p1 = (v: number) => (v * 100).toFixed(1).replace(".", ",") + "%";
const dau = (v: number) => (v >= 0 ? "+" : "") + (v * 100).toFixed(1).replace(".", ",");
const mauTd = (tien_do: number | null, moc: number | null) =>
  tien_do == null ? "nhat-chu" : (moc ? tien_do / moc : tien_do) >= 1 ? "tang" : (moc ? tien_do / moc : tien_do) >= 0.85 ? "canh-chu" : "giam";

function SoCungKy({ ck, tang, don_vi, khach = false, ngay_dau }: { ck: CungKy | null; tang: number | null; don_vi: string; khach?: boolean; ngay_dau: string | null }) {
  if (!ck || ck.so_thang <= 0) return <>chưa có cùng kỳ để so{ngay_dau ? ` — dữ liệu bắt đầu ${ngay(ngay_dau)}` : ""}</>;
  return <>{tang != null ? <span className={tang >= 0 ? "tang" : "giam"}>{dau(tang)}{don_vi}</span>
    : <span title={khach ? "Không có khách nào cùng kỳ năm trước — không tính được, không phải bằng 0"
      : "Mẫu số cùng kỳ ≤ 0 (赤伝 — phiếu đỏ có thể làm doanh thu/lãi gộp cùng kỳ âm) — không tính được %, không phải bằng 0"}>—</span>}
    {" "}so cùng kỳ · {ck.so_thang} tháng đối chiếu ({ck.tu} → {ck.den})</>;
}

/** Dạng Tháng / Khoảng: mỗi phép so một dòng, luôn in dải ngày nó so (bất biến 5b). */
function SoSanhDong({ ss, lay_tang, don_vi, khach = false }: { ss: SoSanhSo[]; lay_tang: (s: SoSanhSo) => number | null; don_vi: string; khach?: boolean }) {
  return <>{ss.map(s => <div key={s.ma}>{!s.co ? <span className="nhat-chu">{s.nhan}: không có dữ liệu để so</span> : <>
    {lay_tang(s) != null ? <span className={lay_tang(s)! >= 0 ? "tang" : "giam"}>{dau(lay_tang(s)!)}{don_vi}</span>
      : <span title={khach ? "Không có khách nào ở dải so sánh — không tính được, không phải bằng 0"
        : "Mẫu số ≤ 0 (赤伝 — phiếu đỏ có thể làm doanh thu/lãi gộp âm) — không tính được %, không phải bằng 0"}>—</span>}
    {" "}so {s.nhan} ({ngay(s.tu)} → {ngay(s.den)})</>}</div>)}</>;
}

function SparkSvg({ s, mau }: { s: Spark; mau: string }) {
  if (!s?.co) return null;
  return (
    <svg className="bc-spark" viewBox={`0 0 ${s.rong} ${s.cao}`} preserveAspectRatio="none" aria-hidden="true" focusable="false">
      {s.doan.map((d, i) => <polyline key={i} points={d} fill="none" stroke={mau} strokeWidth={1.6} vectorEffect="non-scaling-stroke" />)}
      {s.diem_don.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={1.8} fill={mau} />)}
    </svg>);
}

export default function BaoCao() {
  const kxs = chuoiKhoang(useKhoang());
  const { data: d, error, isFetching } = useQuery<BaoCaoApi>({
    queryKey: ["bao-cao", kxs], queryFn: () => lay<BaoCaoApi>(voiKhoang("/api/bao-cao")), placeholderData: keepPreviousData,
  });

  if (error) return <div className="khoi-loi">Không tải được báo cáo: {(error as Error).message}</div>;
  if (!d) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const { bc, td, td_phu } = d;
  if (bc.khong_co_du_lieu) return <><h1>Báo cáo doanh thu</h1>
    <div className="khoi-loi">Chưa có dòng bán hàng nào trong kho dữ liệu. Hãy nạp file <b>売上伝票データ</b> trước.</div></>;
  const ck = bc.cung_ky;
  const kx = d.khoang;
  // Dạng Kỳ = màn Báo cáo cũ (so cùng kỳ trên các tháng đối chiếu); dạng Tháng /
  // Khoảng so theo `bc.so_sanh` (năm trước + tháng trước / khoảng liền trước).
  // Dạng Kỳ có kỳ so sánh tự chọn cũng đi `bc.so_sanh` (máy chủ đã đi nhánh khoảng).
  const theoKy = !kx || (kx.loai === "ky" && !kx.tu_chon);
  const ss = bc.so_sanh ?? [];
  const chinh = ss[0];
  const theoNgay = bc.thang.length > 0 && bc.thang[0].thang.length === 10;
  const nhanX = (t: string) => t.length === 10 ? String(+t.slice(8)) : t.slice(5);

  const xuatCsv = () => {
    const cot = [theoNgay ? "Ngày" : "Tháng", "Doanh thu thuần", "Lãi gộp", "Tỷ suất", "Cùng kỳ", "So cùng kỳ", "Số phiếu", "Khách có đơn"];
    const dong = bc.thang.map(o => [o.thang, o.doanh_thu, o.lai_gop, o.ty_suat ?? "", o.co_cung_ky ? o.dt_cung_ky ?? "" : "",
      o.tang_truong ?? "", o.so_phieu, o.so_khach]);
    const csv = "﻿" + [cot, ...dong].map(r => r.map(x => `"${String(x).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = theoKy ? `bao-cao-ky-${bc.ky.so_ky}.csv` : `bao-cao-${kx!.tu}_${kx!.den}.csv`; a.click(); URL.revokeObjectURL(a.href);
  };

  return (
    <div className={"bc" + (isFetching ? " dang-tai" : "")}>
      <div className="tieu-de-trang">
        <div><h1>Báo cáo doanh thu</h1>
          <div className="phu">📅 <b>{bc.ky.nhan}</b>{theoKy
            ? <> · kỳ kế toán 1/8 → 31/7 · dữ liệu từ {ngay(bc.ky.ngay_dau)} đến {ngay(bc.ky.ngay_cuoi)} ({bc.ky.so_thang}/12 tháng)</>
            : <> · {ngay(kx!.tu)} → {ngay(kx!.den)} · đổi tháng / kỳ / khoảng ở thanh KHOẢNG XEM phía trên</>}</div></div>
        <div className="bc-dk">
          <button type="button" className="nut-nho" onClick={xuatCsv}>⤓ Xuất CSV theo {theoNgay ? "ngày" : "tháng"}</button>
        </div>
      </div>
      {bc.canh_bao.map(c => <div key={c} className="khoi-loi">⚠️ {c}</div>)}

      <div className="o-kpi-luoi bc-kpi">
        <div className="o-kpi"><div className="nhan">Doanh thu thuần</div><div className="gia">{gon(bc.ky.doanh_thu)}</div>
          <SparkSvg s={d.so_nho.dt} mau="var(--ok-vien)" />
          <div className="bc-ck">{theoKy ? <SoCungKy ck={ck} tang={ck?.tang_dt ?? null} don_vi="%" ngay_dau={d.ngay_dau_du_lieu} /> : <SoSanhDong ss={ss} lay_tang={s => s.tang_dt} don_vi={"%"} />}</div></div>
        <div className="o-kpi"><div className="nhan">Lãi gộp</div><div className="gia">{gon(bc.ky.lai_gop)}</div>
          <SparkSvg s={d.so_nho.lg} mau="var(--ok-vien)" />
          <div className="bc-ck">{theoKy ? <SoCungKy ck={ck} tang={ck?.tang_lg ?? null} don_vi="%" ngay_dau={d.ngay_dau_du_lieu} /> : <SoSanhDong ss={ss} lay_tang={s => s.tang_lg} don_vi={"%"} />}</div></div>
        <div className="o-kpi"><div className="nhan">Tỷ suất lãi gộp</div><div className="gia">{bc.ky.ty_suat != null ? p1(bc.ky.ty_suat) : "—"}</div>
          <SparkSvg s={d.so_nho.ts} mau="var(--lien-ket)" />
          <div className="bc-ck">{theoKy ? <SoCungKy ck={ck} tang={ck?.chenh_ty_suat ?? null} don_vi=" điểm" ngay_dau={d.ngay_dau_du_lieu} /> : <SoSanhDong ss={ss} lay_tang={s => s.chenh_ty_suat} don_vi={" điểm"} />}</div></div>
        <div className="o-kpi"><div className="nhan">Khách có đơn</div><div className="gia">{so(bc.ky.so_khach)}</div>
          <SparkSvg s={d.so_nho.kh} mau="var(--do)" />
          <div className="bc-ck">{theoKy ? <SoCungKy ck={ck} tang={ck?.tang_khach ?? null} don_vi="%" khach ngay_dau={d.ngay_dau_du_lieu} /> : <SoSanhDong ss={ss} lay_tang={s => s.tang_khach} don_vi={"%"} khach />}</div></div>
      </div>
      <p className="ghi-chu">Doanh thu thuần đã trừ thuế tiêu dùng. Phiếu đỏ (hàng trả lại) được tính vào như số âm — cố ý, vì hàng trả lại là doanh thu âm thật.</p>

      {td ? <NganSach td={td} phu={td_phu} lk={d.lk} phu_lg={d.td_phu_lg} lk_lg={d.lk_lg} />
        : kx?.loai === "khoang" && <section className="kh-the bc-khoi"><div className="kh-the-dau"><h2>Tiến độ ngân sách</h2></div>
          <p className="phu">Chỉ tiêu chỉ đặt theo tháng — chọn dạng <b>Tháng</b> hoặc <b>Kỳ</b> ở thanh KHOẢNG XEM để xem tiến độ.</p></section>}

      <section className="kh-the bc-khoi">
        <div className="kh-the-dau"><h2>{theoKy ? "Doanh thu 12 tháng so cùng kỳ"
          : `Doanh thu theo ${theoNgay ? "ngày" : "tháng"} · ${bc.ky.nhan}`}</h2></div>
        {!theoKy && chinh && <p className="phu">Nét đứt: {chinh.co ? `${chinh.nhan} (${ngay(chinh.tu)} → ${ngay(chinh.den)}), khớp theo thứ tự ${theoNgay ? "ngày" : "tháng"}` : `${chinh.nhan} — không có dữ liệu để so`}.</p>}
        {d.bd.co ? <>
          <svg viewBox={`0 0 ${d.bd.rong} ${d.bd.cao}`} width="100%" className="bc-svg" role="img" aria-label="Doanh thu và tỷ suất lãi gộp theo tháng, kèm cùng kỳ năm trước">
            {d.bd.cot.map((c, i) => <g key={c.o.thang} className="bc-cot">
              <rect x={c.x} y={c.y} width={c.w} height={c.h} rx={2} fill={c.o.la_thang_chot ? "var(--do)" : "var(--lien-ket)"} opacity={0.72}>
                <title>{c.o.thang}: {yen(c.o.doanh_thu)}{c.o.co_cung_ky && c.o.dt_cung_ky != null ? ` · cùng kỳ ${yen(c.o.dt_cung_ky)}` : ""}{c.o.tang_truong != null ? ` (${dau(c.o.tang_truong)}%)` : ""}</title></rect>
              {(!theoNgay || d.bd.cot.length <= 31 || i % 7 === 0) &&
                <text x={c.x + c.w / 2} y={d.bd.cao - 20} fontSize={10} textAnchor="middle" fill="var(--chu-nhat)">{nhanX(c.o.thang)}</text>}
              {(i === 0 || i === d.bd.cot.length - 1 || c.o.la_thang_chot) &&
                <text x={c.x + c.w / 2} y={d.bd.cao - 8} fontSize={9} textAnchor="middle" fill="var(--chu-nhat)">{c.o.thang.slice(0, 4)}</text>}
            </g>)}
            {d.bd.duong_ck.map((s, i) => <polyline key={i} points={s} fill="none" stroke="var(--duong-ck)" strokeWidth={1.75} strokeDasharray="5 4" />)}
            <polyline points={d.bd.duong} fill="none" stroke="var(--ok-vien)" strokeWidth={2} />
            {d.bd.diem.map(([x, y, o]) => <circle key={o.thang} cx={x} cy={y} r={3.5} fill="var(--ok-vien)" className="bc-diem">
              <title>{o.thang}: tỷ suất {o.ty_suat != null ? p1(o.ty_suat) : "—"}</title></circle>)}
          </svg>
          <div className="chu-giai bc-cg">
            <span><i className="mau" style={{ background: "var(--lien-ket)", opacity: .72 }} /> Doanh thu thuần (cột)</span>
            {!theoNgay && <span><i className="mau" style={{ background: "var(--do)", opacity: .72 }} /> Tháng 7 — chốt kỳ</span>}
            <span><i className="mau" style={{ background: "var(--ok-vien)" }} /> Tỷ suất lãi gộp (đường)</span>
            <span><i className="mau" style={{ background: "var(--duong-ck)" }} /> Doanh thu {theoKy ? "cùng kỳ" : "cùng ngày / tháng"} năm trước (nét đứt)</span>
            <span>Trục tỷ suất từ {Math.round(d.bd.ts_lo * 100)}% đến {Math.round(d.bd.ts_hi * 100)}%, không từ 0% — nếu từ 0 thì đường gần như phẳng và giấu mất chỗ cần nhìn.</span>
          </div></> : <p className="phu">Chưa có dữ liệu để vẽ khối này.</p>}
      </section>

      <div className="bc-hai">
        <section className="kh-the bc-khoi">
          <div className="kh-the-dau"><h2>Ngành hàng kéo doanh thu lên/xuống</h2></div>
          {(theoKy ? ck && ck.so_thang > 0 : chinh?.co) ? <>
            <p className="phu">{theoKy ? <>Chênh lệch so cùng kỳ trên {ck!.so_thang} tháng đối chiếu ({ck!.tu} → {ck!.den})</>
              : <>Chênh lệch so {chinh!.nhan} ({ngay(chinh!.tu)} → {ngay(chinh!.den)})</>} — phải trục kéo LÊN, trái kéo XUỐNG.</p>
            {d.dg.co ? <svg viewBox={`0 0 ${d.dg.rong} ${d.dg.cao}`} width="100%" className="bc-svg" role="group" aria-label="Chênh lệch doanh thu theo ngành so cùng kỳ">
              <line x1={d.dg.x0} y1={0} x2={d.dg.x0} y2={d.dg.cao} stroke="var(--vien-dam)" />
              {d.dg.thanh.map(t => <g key={t.nganh} className="bc-thanh">
                <rect x={t.x} y={t.y} width={t.w} height={d.dg.cao_hang} rx={2} fill={t.am ? "var(--loi-vien)" : "var(--ok-vien)"}>
                  <title>{t.nganh}: {t.nhan} so cùng kỳ{t.tang_truong != null ? ` (${dau(t.tang_truong)}%)` : ""}</title></rect>
                <text x={t.am ? d.dg.x0 + 4 : d.dg.x0 - 4} y={t.y + d.dg.cao_hang / 2 + 3} fontSize={10} fill="var(--chu-nhat)" textAnchor={t.am ? "start" : "end"}>{t.nganh}</text>
                <text x={t.nhan_x} y={t.y + d.dg.cao_hang / 2 + 3} fontSize={9.5} textAnchor={t.nhan_neo as "start" | "end"}
                  fill={t.nhan_trong ? (t.am ? "var(--dg-chu-am)" : "var(--nen-the)") : "var(--chu-nhat)"}>{t.nhan}</text>
              </g>)}
            </svg> : <p className="phu">Chưa có dữ liệu để vẽ khối này.</p>}
          </> : <p className="phu">{theoKy ? "Kỳ này không có tháng nào để so cùng kỳ." : "Không có dữ liệu năm trước để so."}</p>}
        </section>

        <section className="kh-the bc-khoi">
          <div className="kh-the-dau"><h2>Doanh thu đến từ danh mục nào</h2></div>
          <p className="phu">Diện tích mỗi ô tỷ lệ với doanh thu {theoKy ? "cả kỳ" : "cả khoảng xem"}; màu theo tăng trưởng của ngành {theoKy ? "(cùng dải tháng đối chiếu)" : `so ${chinh?.nhan ?? "năm trước"}`}. Ngành không có cùng kỳ tô màu trung tính.</p>
          {d.co.co ? <svg viewBox={`0 0 ${d.co.rong} ${d.co.cao}`} width="100%" className="bc-svg" role="group" aria-label="Doanh thu theo ngành hàng và mặt hàng">
            {d.co.nganh.map(n => {
              const tt = n.tang_truong != null ? ` · ${dau(n.tang_truong)}% so cùng kỳ` : " · không có cùng kỳ";
              const tt2 = n.tang_truong != null ? ` (${dau(n.tang_truong)}% so cùng kỳ)` : " (không có cùng kỳ)";
              return <g key={n.nganh}>
                <rect x={n.x} y={n.y} width={n.w} height={n.h} className={"cay-o-nganh bac-" + n.bac}><title>{n.nganh}: {yen(n.doanh_thu)}{tt}</title></rect>
                {n.ma.map(m => <g key={m.ten} className="bc-o-ma">
                  <rect x={m.x} y={m.y} width={m.w} height={m.h} className="cay-o-ma" fill="var(--nen-the)" opacity={0.18}>
                    <title>{n.nganh}{tt2} — {m.ten}: {yen(m.doanh_thu)}</title></rect>
                  {m.nhan && <text x={m.x + 3} y={m.y + 11} fontSize={11} fill="var(--chu)" pointerEvents="none">{m.nhan}</text>}
                </g>)}
                {!n.ma.length && n.w > 55 && n.h > 16 && <text x={n.x + 4} y={n.y + 13} fontSize={10.5} fontWeight={600} fill="var(--chu)" pointerEvents="none">{n.nganh}</text>}
              </g>;
            })}
          </svg> : <p className="phu">Chưa có dữ liệu để vẽ khối này.</p>}
          {d.co.khong_ve !== 0 && <p className="phu">Không vẽ: {yen(d.co.khong_ve)} của {d.co.so_ma_khong_ve} mã (doanh thu âm hoặc bằng 0, hoặc thuộc ngành có tổng âm)</p>}
          {bc.phi.dong.length > 0 && <p className="phu">Không gồm phí &amp; điều chỉnh ({yen(bc.phi.doanh_thu)}) — không phải hàng, xem khối riêng bên dưới.</p>}
        </section>
      </div>

      <section className="kh-the bc-khoi">
        <div className="kh-the-dau"><h2>Tăng trưởng theo tháng và ngành</h2></div>
        {!theoKy && bc.ky.so_ky > 0 && <p className="phu">Cả Kỳ {bc.ky.so_ky} chứa khoảng đang xem.</p>}
        {d.nh.co ? <>
          <div className="bang-cuon"><table className="nhiet-bang">
            <thead><tr><th scope="col" />{d.nh.thang.map(t => <th key={t} scope="col">{t.slice(5)}</th>)}</tr></thead>
            <tbody>{d.nh.hang.map(h => <tr key={h.nganh}><th scope="row">{h.nganh}</th>{h.o.map(o => <ONhiet key={o.thang} o={o} dau_du_lieu={d.nh.thang_dau_du_lieu} />)}</tr>)}</tbody>
          </table></div>
          <div className="chu-giai bc-cg">
            <span><i className="mau bac-g2" /> ≤ −20%</span><span><i className="mau bac-g1" /> −20…−5%</span><span><i className="mau bac-0" /> −5…+5%</span>
            <span><i className="mau bac-t1" /> +5…+20%</span><span><i className="mau bac-t2" /> ≥ +20%</span>
            <span><i className="mau bac-khong" /> có cùng kỳ, không tính được %</span><span><i className="mau bac-khong_ck" /> không có cùng kỳ</span>
            <span><i className="mau bac-khong_ban" /> không bán tháng này</span><span><i className="mau bac-chua_toi" /> chưa tới tháng / chưa có dữ liệu{d.nh.thang_dau_du_lieu ? ` (trước ${d.nh.thang_dau_du_lieu})` : ""}</span>
          </div></> : <p className="phu">Chưa có dữ liệu để vẽ khối này.</p>}
      </section>

      <section className="kh-the bc-khoi">
        <div className="kh-the-dau"><h2>Doanh thu tập trung ở khách nào</h2></div>
        {bc.tap_trung && bc.tap_trung.luy_ke_top10 != null &&
          <p className="phu">10 khách lớn nhất = <b>{p1(bc.tap_trung.luy_ke_top10)}</b> {theoKy ? <>doanh thu kỳ này, trên {so(bc.tap_trung.so_khach)} khách có phát sinh trong kỳ.</>
            : <>doanh thu khoảng này, trên {so(bc.tap_trung.so_khach)} khách có phát sinh trong khoảng.</>}</p>}
        <div className="bc-pareto">
          {d.pa.co ? <div><svg viewBox={`0 0 ${d.pa.rong} ${d.pa.cao}`} width="100%" className="bc-svg" role="group" aria-label="Doanh thu và luỹ kế của 20 khách hàng lớn nhất">
            {d.pa.truc_pct.map(t => <g key={t.y}><line x1={0} y1={t.y} x2={d.pa.rong} y2={t.y} stroke="var(--vien)" strokeWidth={1} strokeDasharray="2 3" />
              <text x={d.pa.rong - 4} y={t.y - 3} fontSize={9} textAnchor="end" fill="var(--chu-nhat)">{t.nhan}</text></g>)}
            {d.pa.cot.map(c => <a key={c.khach.ma} href={`/khach-hang/${encodeURIComponent(c.khach.ma)}`}>
              <rect x={c.x} y={c.y} width={c.w} height={c.h} rx={2} fill="var(--lien-ket)" opacity={0.72} className="bc-cot-kh">
                <title>Thứ {c.khach.thu_hang} — {c.khach.ten}: {yen(c.khach.doanh_thu)} · bấm để mở hồ sơ</title></rect></a>)}
            {d.pa.doan.map((s, i) => <polyline key={i} points={s} fill="none" stroke="var(--do)" strokeWidth={2} />)}
            {d.pa.diem.map(p => <circle key={p.khach.ma} cx={p.x} cy={p.y} r={2.5} fill="var(--do)">
              <title>Thứ {p.khach.thu_hang} — {p.khach.ten}: luỹ kế {p.khach.luy_ke != null ? p1(p.khach.luy_ke) : "—"}</title></circle>)}
          </svg>
            <div className="chu-giai bc-cg"><span><i className="mau" style={{ background: "var(--lien-ket)", opacity: .72 }} /> Doanh thu (cột)</span>
              <span><i className="mau" style={{ background: "var(--do)" }} /> Luỹ kế (đường, trục 0–100%)</span><span>Đỉnh trục cột: {yen(d.pa.dinh)}</span></div></div>
            : <p className="phu">Chưa có dữ liệu để vẽ khối này.</p>}
          <div className="bang-cuon bc-bang-kh"><table className="bang">
            <thead><tr><th className="so">#</th><th>Khách hàng</th><th className="so">Doanh thu thuần</th><th className="so">Tỷ trọng</th><th className="so">Luỹ kế</th></tr></thead>
            <tbody>{(bc.tap_trung?.dong ?? []).map(k => <tr key={k.ma}><td className="so">{k.thu_hang}</td>
              <td className="ten-jp"><a href={`/khach-hang/${encodeURIComponent(k.ma)}`}>{k.ten}</a></td><td className="so">{yen(k.doanh_thu)}</td>
              <td className="so">{k.ty_trong != null ? p1(k.ty_trong) : "—"}</td><td className="so">{k.luy_ke != null ? p1(k.luy_ke) : "—"}</td></tr>)}</tbody>
          </table></div>
        </div>
      </section>

      <div className="bc-hai">
        <section className="kh-the bc-khoi">
          <div className="kh-the-dau"><h2>10 mặt hàng lãi gộp cao nhất</h2></div>
          <div className="bang-cuon"><table className="bang">
            <thead><tr><th>Mặt hàng</th><th className="so">Doanh thu thuần</th><th className="so">Lãi gộp</th><th className="so">Tỷ suất</th><th className="so">Khách mua</th></tr></thead>
            <tbody>{bc.hang.map(h => <tr key={h.ma}><td className="ten-jp"><a href={`/san-pham/${encodeURIComponent(h.ma)}`}>{h.ten}</a></td>
              <td className="so">{h.doanh_thu != null ? yen(h.doanh_thu) : "—"}</td><td className="so">{h.lai_gop != null ? yen(h.lai_gop) : "—"}</td>
              <td className="so">{h.ty_suat != null ? p1(h.ty_suat) : "—"}</td><td className="so">{so(h.so_khach)}</td></tr>)}</tbody>
          </table></div>
        </section>
        <section className="kh-the bc-khoi">
          <div className="kh-the-dau"><h2>Theo người phụ trách khách (担当者)</h2></div>
          <div className="bang-cuon"><table className="bang">
            <thead><tr><th>Mã</th><th className="so">Doanh thu thuần</th><th className="so">Lãi gộp</th><th className="so">Tỷ suất</th><th className="so">Khách</th><th className="so">Phiếu</th></tr></thead>
            <tbody>{bc.nhan_vien.map((n, i) => <tr key={(n.ma ?? "") + i}><td>{n.ma || "(trống)"}</td>
              <td className="so">{yen(n.doanh_thu)}</td><td className="so">{yen(n.lai_gop)}</td><td className="so">{n.ty_suat != null ? p1(n.ty_suat) : "—"}</td>
              <td className="so">{so(n.so_khach)}</td><td className="so">{so(n.so_phieu)}</td></tr>)}</tbody>
          </table></div>
        </section>
      </div>

      {bc.phi.dong.length > 0 && <section className="kh-the bc-khoi">
        <div className="kh-the-dau"><h2>Phí &amp; điều chỉnh — không phải hàng</h2></div>
        <p className="phu">Phí thu hộ (代引手数料), phí gửi (配送料), giảm giá / phiếu giảm giá (値引き・クーポン) — mã OBC đánh dấu 無形 — và dòng làm tròn không mã hàng.
          Tiền của chúng VẪN nằm trong tổng doanh thu và lãi gộp ở trên (khớp sổ OBC), nhưng không tính vào ngành hàng hay xếp hạng mặt hàng.</p>
        <div className="bang-cuon"><table className="bang">
          <thead><tr><th>Khoản</th><th className="so">Doanh thu thuần</th><th className="so">Lãi gộp</th><th className="so">Khách</th></tr></thead>
          <tbody>{bc.phi.dong.map(h => <tr key={h.ma || "(khong-ma)"}><td className="ten-jp">{h.ten}</td>
            <td className="so">{h.doanh_thu != null ? yen(h.doanh_thu) : "—"}</td><td className="so">{h.lai_gop != null ? yen(h.lai_gop) : "—"}</td>
            <td className="so">{so(h.so_khach)}</td></tr>)}
            <tr><th scope="row">Cộng</th><td className="so"><b>{yen(bc.phi.doanh_thu)}</b></td><td className="so"><b>{yen(bc.phi.lai_gop)}</b></td><td /></tr></tbody>
        </table></div>
      </section>}

      <details className="kh-the bc-khoi">
        <summary>Bảng số chi tiết theo {theoNgay ? "ngày" : "tháng"} ({bc.thang.length} {theoNgay ? "ngày" : "tháng"})</summary>
        <div className="bang-cuon"><table className="bang">
          <thead><tr><th>{theoNgay ? "Ngày" : "Tháng"}</th><th className="so">Doanh thu thuần</th><th className="so">Lãi gộp</th><th className="so">Tỷ suất</th>
            <th className="so">Cùng kỳ</th><th className="so">So cùng kỳ</th><th className="so">Số phiếu</th></tr></thead>
          <tbody>{bc.thang.map(o => <tr key={o.thang}><td>{o.thang}{o.la_thang_chot ? " 🏁" : ""}</td>
            <td className="so">{yen(o.doanh_thu)}</td><td className="so">{yen(o.lai_gop)}</td><td className="so">{o.ty_suat != null ? p1(o.ty_suat) : "—"}</td>
            <td className="so">{o.co_cung_ky && o.dt_cung_ky != null ? yen(o.dt_cung_ky) : "—"}</td>
            <td className="so">{!o.co_cung_ky ? <span className="nhat-chu" title="Dải cùng kỳ năm trước không có trong kho dữ liệu">không có</span>
              : o.tang_truong != null ? <span className={o.tang_truong >= 0 ? "tang" : "giam"}>{dau(o.tang_truong)}%</span> : "—"}</td>
            <td className="so">{so(o.so_phieu)}</td></tr>)}</tbody>
        </table></div>
      </details>
    </div>
  );
}

function ONhiet({ o, dau_du_lieu }: { o: BaoCaoApi["nh"]["hang"][0]["o"][0]; dau_du_lieu: string | null }) {
  const nhan = `${o.nganh} · ${o.thang}`;
  if (o.bac === "chua_toi") return <td className="bac-chua_toi" title={`${nhan}: chưa tới tháng này trong kỳ`}>·</td>;
  if (o.bac === "truoc_du_lieu") return <td className="bac-chua_toi" title={`${nhan}: chưa có dữ liệu (trước ${dau_du_lieu})`}>·</td>;
  if (o.bac === "khong_ban") return <td className="bac-khong_ban" title={`${nhan}: không bán tháng này${o.co_the_ck ? " (và tháng cùng kỳ năm trước cũng vậy)" : ""}`}>¥0</td>;
  if (o.bac === "khong_ck") return <td className="bac-khong_ck" title={`${nhan}: không có cùng kỳ (${yen(o.doanh_thu)})`}>—</td>;
  if (o.tang_truong != null) return <td className={"bac-" + o.bac} title={`${nhan}: ${dau(o.tang_truong)}% so cùng kỳ (${yen(o.doanh_thu)})`}>{dau(o.tang_truong)}%</td>;
  return <td className="bac-khong" title={`${nhan}: mẫu số cùng kỳ ≤ 0, không tính được % (${yen(o.doanh_thu)})`}>—</td>;
}

function NganSach({ td, phu: phuDt, lk: lkDt, phu_lg, lk_lg }: { td: Td; phu: BaoCaoApi["td_phu"]; lk: BaoCaoApi["lk"];
  phu_lg: BaoCaoApi["td_phu"]; lk_lg: BaoCaoApi["lk"] }) {
  // 041: Doanh thu / Lãi gộp — cùng khối, cùng công thức, đổi cột (ngân sách CÔNG TY nhập thẳng).
  const [cs, datCs] = useState<"dt" | "lg">("dt");
  const lg = cs === "lg";
  const v = lg
    ? { co: td.co_ngan_sach_lg, tt: td.thuc_te_lg, mt: td.muc_tieu_lg, den: td.muc_tieu_lg_den_hom_nay, td: td.tien_do_lg,
        pct: td.pct_moc_chi_tieu_lg, rong: td.rong_thanh_lg, rmoc: td.rong_moc_lg }
    : { co: td.co_ngan_sach, tt: td.thuc_te, mt: td.muc_tieu, den: td.muc_tieu_den_hom_nay, td: td.tien_do,
        pct: td.pct_moc_chi_tieu, rong: td.rong_thanh, rmoc: td.rong_moc };
  const vn = (n: Nguoi) => lg
    ? { tt: n.thuc_te_lg, mt: n.muc_tieu_lg, den: n.muc_tieu_lg_den_hom_nay, td: n.tien_do_lg, rong: n.rong_thanh_lg, rmoc: n.rong_moc_lg }
    : { tt: n.thuc_te, mt: n.muc_tieu, den: n.muc_tieu_den_hom_nay, td: n.tien_do, rong: n.rong_thanh, rmoc: n.rong_moc };
  const phu = lg ? phu_lg : phuDt;
  const lk = lg ? lk_lg : lkDt;
  const ten = lg ? "lãi gộp" : "doanh thu";
  const moc = v.pct != null ? v.pct / 100 : null;
  const tNhan = `${td.thang.slice(5)}/${td.thang.slice(0, 4)}`;
  return (
    <section className="kh-the bc-khoi bc-ns">
      <div className="kh-the-dau"><h2>Tiến độ ngân sách tháng {tNhan}</h2>
        <div className="tab-pill" role="group" aria-label="Chỉ số">
          <button type="button" aria-pressed={!lg} onClick={() => datCs("dt")}>Doanh thu</button>
          <button type="button" aria-pressed={lg} onClick={() => datCs("lg")}>Lãi gộp</button></div>
        {phu && <span className="kh-the-goc"><span className="nhan-vien do">Còn {phu.ngay_kd_con_lai} ngày kinh doanh</span></span>}</div>
      <p className="phu">Số liệu đến {ngay(td.hom_nay)} · {td.ngay_kd_da_qua}/{td.ngay_kd} ngày làm việc của tháng (đã trừ thứ Bảy, Chủ nhật và ngày lễ quốc gia Nhật — chưa trừ ngày nghỉ riêng của công ty) · công ty = mart.tien_do_cong_ty (ngân sách công ty nhập thẳng), từng người = mart.tien_do_ngan_sach</p>
      {!v.co ? <div className="khoi-loi">Chưa đặt ngân sách {ten} của công ty cho tháng này.{" "}
        {KD.hien_ngan_sach && <><a href={`/ngan-sach?ky=${td.company_fy}`}>Đặt chỉ tiêu</a> rồi quay lại đây.</>}</div> : <>
        <div className="o-kpi-luoi bc-ns-o">
          <div className="o-kpi"><div className="nhan">Tiến độ tháng</div>
            <div className={"gia " + mauTd(v.td, moc)}>{v.td != null ? p1(v.td) : "—"}</div>
            <div className="dong-phu nhat-chu">mốc hôm nay {moc != null ? p1(moc) : "—"}</div></div>
          <div className="o-kpi"><div className="nhan">Thực tế ({ten})</div><div className="gia">{yen(v.tt)}</div>
            <div className="dong-phu nhat-chu">trên ngân sách {v.mt != null ? yen(v.mt) : "—"}</div></div>
          <div className="o-kpi"><div className="nhan">{phu?.thieu_moc != null && phu.thieu_moc > 0 ? "Thiếu so mốc hôm nay" : "Vượt mốc hôm nay"}</div>
            <div className={"gia " + (phu?.thieu_moc != null && phu.thieu_moc > 0 ? "giam" : "tang")}>{phu?.thieu_moc != null ? yen(Math.abs(phu.thieu_moc)) : "—"}</div>
            <div className="dong-phu nhat-chu">{phu?.thieu_moc != null && v.den ? `${p1(Math.abs(phu.thieu_moc) / v.den)} của mốc ${yen(v.den)}` : "—"}</div></div>
          <div className="o-kpi"><div className="nhan">{lg ? "Cần lãi gộp mỗi ngày" : "Cần bán mỗi ngày"}</div>
            <div className="gia canh-chu">{phu?.can_ban_moi_ngay != null ? yen(phu.can_ban_moi_ngay) : "—"}</div>
            <div className="dong-phu nhat-chu">{phu ? `${phu.ngay_kd_con_lai} ngày còn lại` : ""}{phu?.can_ban_moi_ngay != null && phu.nhip_chuan ? ` · gấp ${(phu.can_ban_moi_ngay / phu.nhip_chuan).toFixed(2).replace(".", ",")}× nhịp chuẩn` : ""}</div></div>
        </div>
        <div className="bc-ns-hai">
          <div>
            <h3>Luỹ kế thực tế so với nhịp ngân sách ({ten}) — cả kỳ</h3>
            {lk.co ? <><svg viewBox={`0 0 ${lk.rong} ${lk.cao}`} width="100%" className="bc-svg" role="img" aria-label="Luỹ kế doanh thu so với nhịp ngân sách">
              <polyline points={lk.ngan_sach} fill="none" stroke="var(--chu-nhat)" strokeWidth={2} strokeDasharray="5 4" />
              <polyline points={lk.thuc_te} fill="none" stroke="var(--do)" strokeWidth={2.5} />
              {lk.nhan.filter(n => n.hien).map(n => <text key={n.thang} x={n.x} y={lk.cao - 8} fontSize={9} textAnchor="middle" fill="var(--chu-nhat)">{n.thang.slice(5)}</text>)}
            </svg>
              <div className="chu-giai bc-cg"><span><i className="mau" style={{ background: "var(--do)" }} />Luỹ kế thực tế</span>
                <span><i className="mau" style={{ background: "var(--chu-nhat)" }} />Nhịp ngân sách</span><span>Đỉnh trục: {yen(lk.dinh)}</span>
                <span>Luỹ kế theo NGÀY trong tháng + dự báo chốt: <a href="/du-bao">Dự báo</a></span></div></> : <p className="phu">Chưa đủ dữ liệu.</p>}
          </div>
          <div>
            <h3>Tiến độ theo nhân viên</h3>
            <div className="bc-bullet tong"><div className="bc-bl-dau"><b>Toàn công ty</b>
              <span>{yen(v.tt)} / {v.mt != null ? yen(v.mt) : "—"} · <b className={mauTd(v.td, moc)}>{v.td != null ? p1(v.td) : "—"}</b></span></div>
              <Thanh rong={v.rong} moc={v.rmoc} lon /></div>
            {td.nguoi.map(n => { const x = vn(n); return (
              <div key={n.ma} className="bc-bullet"><div className="bc-bl-dau"><span>{n.ten ?? <>{n.ma} <small className="nhat-chu">(mã không có trong danh sách phụ trách)</small></>}</span>
                <span>{yen(x.tt)} / {x.mt != null ? yen(x.mt) : "—"}{x.td != null && <> · <b className={x.td >= 1 ? "tang" : "giam"}>{p1(x.td)}</b></>}</span></div>
                <Thanh rong={x.rong} moc={x.rmoc} /></div>); })}
            <p className="phu">Vạch đen là mốc đáng lẽ đạt tới hôm nay.</p>
          </div>
        </div>
      </>}
      <div className="bc-ns-hai">
        <ChuaCoDuLieuBoc tieu_de="Khách hiện hữu và khách mới" ly_do="Chưa có định nghĩa 既存 / 新規得意先 theo kỳ trong mart — không tự suy diễn." />
        <details className="bc-chi-tiet"><summary>Bảng số chi tiết theo nhân viên — tháng {tNhan}</summary>
          <div className="bang-cuon"><table className="bang">
            <thead><tr><th>Nhân viên</th><th className="so">Thực tế</th><th className="so">Chỉ tiêu</th><th className="so">Tiến độ</th>
              <th className="so">Mốc đến hôm nay</th><th className="so">Cùng kỳ năm trước</th><th className="so">So cùng kỳ</th><th className="so">Tỷ trọng</th></tr></thead>
            <tbody>{td.nguoi.map(n => <tr key={n.ma}><td>{n.ten ?? n.ma}<br /><small className="nhat-chu">{n.ten ? n.ma : "(mã không có trong danh sách phụ trách)"}</small></td>
              <td className="so">{yen(n.thuc_te)}</td><td className="so">{n.muc_tieu != null ? yen(n.muc_tieu) : "—"}</td>
              <td className="so">{n.tien_do != null ? <span className={n.tien_do >= 1 ? "tang" : "giam"}>{p1(n.tien_do)}</span> : "—"}</td>
              <td className="so">{n.muc_tieu_den_hom_nay != null ? yen(n.muc_tieu_den_hom_nay) : "—"}</td>
              <td className="so">{n.co_cung_ky ? yen(n.cung_ky ?? 0) : "không có dữ liệu"}</td>
              <td className="so">{n.tang_truong != null ? <span className={n.tang_truong >= 0 ? "tang" : "giam"}>{dau(n.tang_truong)}%</span> : n.co_cung_ky ? "—" : "không có dữ liệu"}</td>
              <td className="so">{td.thuc_te ? p1(n.thuc_te / td.thuc_te) : "—"}</td></tr>)}</tbody>
          </table></div></details>
      </div>
    </section>);
}

function Thanh({ rong, moc, lon = false }: { rong: number | null; moc: number | null; lon?: boolean }) {
  if (rong == null) return <div className="phu">chưa có chỉ tiêu</div>;
  return <div className={"thanh-tien-do" + (lon ? "" : " vua")} role="img" aria-label={`${rong.toFixed(1)}% chỉ tiêu`}>
    <div className="day" style={{ width: `${rong}%` }} />{moc != null && <div className="moc" style={{ left: `${moc}%` }} />}</div>;
}

function ChuaCoDuLieuBoc(p: { tieu_de: string; ly_do: string }) {
  return <div className="kh-chua-co"><ChuaCoDuLieu {...p} /></div>;
}
