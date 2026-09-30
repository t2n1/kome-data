// Trang Doanh thu (/bao-cao, 2026-09-30) — GỘP Báo cáo · Dự báo · Ngân sách (đặc tả
// 2026-09-30-doanh-thu-gop-design.md; chủ DN: "ít chữ, nhiều graph", "phải có lợi nhuận",
// "bubble graph"). Hai nguồn song song, KHÔNG endpoint mới: /api/bao-cao (số + hình học của
// kome/bao_cao.py, kome/ve_phan_tich.py, kome/ve_doanh_thu.py) và /api/du-bao (kome/du_bao.py).
// Công tắc Doanh thu | Lãi gộp đổi cả trang; khối chưa có số lãi gộp nói ra ở nhãn.
// Luật chữ như Tổng quan: câu định nghĩa cách tính vào ⓘ, câu ngoại lệ luôn hiện; nhãn kỳ so
// luôn hiện và mỗi phép so in số tháng đối chiếu (bất biến 5b).
// Kỳ so = NÉT ĐỨT / CỘT MA / VẠCH ĐỨT — nét đứt không dùng cho thứ gì khác (ngân sách và
// dự báo là nét liền / cột nền).
// Lệch có chủ ý so với gói thiết kế: KHÔNG "% chắc chắn" / "% nguy cơ" (bất biến đợt 8);
// "Khách hiện hữu / khách mới" chưa có định nghĩa trong mart.
import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { lay } from "../api";
import { chuoiKhoang, useKhoang, useNhanMoc, voiKhoang, type KhoangMayChu } from "../khung/khoang";
import { BieuDo, type Chuoi } from "../chung/BieuDo";
import { Khoi } from "../chung/Khoi";
import { DongNoi, ONoi } from "../chung/ONoi";
import { MauSs } from "../chung/SoSanh";
import { gon, ngay, so, yen } from "../dinh_dang";
import { KD } from "../khoi_dau";
import { Bong, CauNoi, dongBong, type BongDiem, type BongVe, type CauNoiVe } from "./Bong";
import "./bao_cao.css";

// 048 / 049: nhóm KHÔNG phải hàng (phí & điều chỉnh, hàng tặng POSM) — tổng do mart cộng.
type NhomRieng = { doanh_thu: number; lai_gop: number;
  dong: { ma: string; ten: string; doanh_thu: number | null; lai_gop: number | null; so_khach: number; so_luong: number | null }[] };

type O = { thang: string; doanh_thu: number; lai_gop: number; ty_suat: number | null; co_cung_ky: boolean;
  tang_truong: number | null; la_thang_chot: boolean; so_phieu: number; so_khach: number; dt_cung_ky: number | null;
  lg_cung_ky: number | null; so_khach_cung_ky: number | null; ty_suat_cung_ky: number | null };
type Ky = { company_fy: number; so_ky: number; nhan: string; doanh_thu: number; lai_gop: number; ty_suat: number | null;
  so_khach: number; so_phieu: number; so_thang: number; ngay_dau: string | null; ngay_cuoi: string | null };
type CungKy = { so_thang: number; tu: string | null; den: string | null; tang_dt: number | null; tang_lg: number | null;
  tang_khach: number | null; chenh_ty_suat: number | null };
/** Một phép so của khoảng xem dạng Tháng / Khoảng (kome/bao_cao.py::SoSanhSo). */
type SoSanhSo = { ma: string; nhan: string; co: boolean; tu: string; den: string; tu_nay: string; den_nay: string;
  tang_dt: number | null; tang_lg: number | null; tang_khach: number | null; chenh_ty_suat: number | null };
type KhTT = { ma: string; ten: string; doanh_thu: number; thu_hang: number; ty_trong: number | null; luy_ke: number | null };
type Nguoi = { ma: string; ten: string | null; thuc_te: number; muc_tieu: number | null; muc_tieu_den_hom_nay: number | null;
  tien_do: number | null; muc_tieu_lg: number | null; thuc_te_lg: number; tien_do_lg: number | null;
  muc_tieu_lg_den_hom_nay: number | null };
type ThangCty = { thang: string; thuc_te: number | null; ngan_sach: number | null; thuc_te_lg: number | null; ngan_sach_lg: number | null };
type Td = { company_fy: number; thang: string; hom_nay: string | null; ngay_kd: number; ngay_kd_da_qua: number; thuc_te: number;
  muc_tieu: number | null; muc_tieu_den_hom_nay: number | null; tien_do: number | null; nguoi: Nguoi[]; co_ngan_sach: boolean;
  pct_moc_chi_tieu: number | null; co_ngan_sach_lg: boolean; thuc_te_lg: number; muc_tieu_lg: number | null;
  tien_do_lg: number | null; pct_moc_chi_tieu_lg: number | null; thang_cty: ThangCty[] };
type Spark = { co: boolean; rong: number; cao: number; doan: string[]; diem_don: [number, number][]; doan_ss?: string[] };
type BaoCaoApi = {
  khoang: KhoangMayChu | null;
  bc: { ky: Ky; thang: O[];
    nhan_vien: { ma: string | null; doanh_thu: number; lai_gop: number; dt_ss?: number | null; dt_nay_ss?: number | null }[];
    khong_co_du_lieu: boolean; canh_bao: string[]; cung_ky: CungKy | null; so_sanh: SoSanhSo[];
    tap_trung: { dong: KhTT[]; so_khach: number; luy_ke_top10: number | null } | null;
    phi: NhomRieng; hang_tang: NhomRieng };
  td: Td | null;
  so_nho: Record<"dt" | "lg" | "ts" | "kh", Spark>;
  nh: { co: boolean; thang: string[]; thang_dau_du_lieu: string | null; hang: { nganh: string; o: { thang: string; nganh: string; bac: string;
    tang_truong: number | null; doanh_thu: number; co_the_ck?: boolean }[] }[] };
  pa: { co: boolean; rong: number; cao: number; cot: { x: number; y: number; w: number; h: number; khach: KhTT }[]; doan: string[];
    diem: { x: number; y: number; khach: KhTT }[]; dinh: number; truc_pct: { y: number; nhan: string }[] };
  ngay_dau_du_lieu: string | null;
  ss_thang: { thang: Record<string, [number | null, number | null]>; co_lg: boolean };
  cau_noi: CauNoiVe;
  bong_nganh: Record<"dt" | "lg", BongVe>;
  bong_ma: Record<"dt" | "lg", BongVe>;
};

type Kiem = { thang: string; du_bao: number; thuc_te: number; lech: number | null };
type Chot = { thang: string; hom_nay: string; da_ban: number; e: number; n: number; co_so: number; thap: number | null;
  cao: number | null; kiem: Kiem[]; moc_kiem: number; ngan_sach: number | null; xong: boolean };
type ThangDb = { thang: string; co_so: number; thap: number; cao: number; cung_ky: number };
type Nam = { du_bao: ThangDb[]; he_so: number | null; doi_chieu: string[]; tong_cung_ky: number };
type NguoiDb = { ma: string; ten: string | null; da_ban: number; co_so: number; ngan_sach: number | null;
  da_ban_lg: number; co_so_lg: number; ngan_sach_lg: number | null };
type NguyCo = { ma: string; ten: string; so_ngay_im_lang: number; ty_le: number; doanh_thu: number; trang_thai: string };
type VeChot = { co: boolean; rong: number; cao: number; trai: number; phai: number; truc: { y: number; nhan: string }[]; dai?: string; ns?: string;
  cao_?: string; thap?: string; cs?: string; tt: string; x_nay: number; y_nay: number; x_cuoi: number; y_cuoi: number;
  day_truc: number; nhan_ngay: { x: number; nhan: string }[] };
type DuBaoApi = {
  db: null | { chot: Chot | null; nam: Nam; nguoi: NguoiDb[]; chot_lg: Chot | null; nam_lg: Nam | null;
    kh: { nguy_co: NguyCo[]; so_nguy_co: number; tien_nguy_co: number } };
  kich_ban: Record<string, string>; tong: Record<string, number>; theo: Record<string, number[]>;
  tong_lg: Record<string, number>; theo_lg: Record<string, number[]>;
  ve_chot: VeChot; ve_chot_lg: VeChot;
};

const p1 = (v: number) => (v * 100).toFixed(1) + "%";
const hoa = (s: string) => s.replace(/^./, c => c.toUpperCase());
const dau = (v: number) => (v >= 0 ? "+" : "") + (v * 100).toFixed(1);
const tNhan = (t: string) => `${t.slice(5)}/${t.slice(0, 4)}`;
const thNgan = (t: string) => `T${+t.slice(5, 7)}`;
/** Câu ngoại lệ của khối: rỗng → null (không vẽ dải cảnh báo trống). */
const cb = (...xs: (string | false | null | undefined)[]) => xs.filter(Boolean).join(" ") || null;

function SoCungKy({ ck, tang, don_vi, ngay_dau }: { ck: CungKy | null; tang: number | null; don_vi: string; ngay_dau: string | null }) {
  if (!ck || ck.so_thang <= 0) return <>chưa có cùng kỳ để so{ngay_dau ? ` — dữ liệu bắt đầu ${ngay(ngay_dau)}` : ""}</>;
  return <>{tang != null ? <span className={tang >= 0 ? "tang" : "giam"}>{dau(tang)}{don_vi}</span>
    : <span title="Mẫu số cùng kỳ ≤ 0 (赤伝) — không tính được %, không phải bằng 0">—</span>}
    {" "}<MauSs />so cùng kỳ · {ck.so_thang} tháng đối chiếu ({ck.tu} → {ck.den})</>;
}

/** Dạng Tháng / Khoảng: phép so in luôn dải ngày nó so (bất biến 5b). */
function SoSanhDong({ ss, lay_tang, don_vi }: { ss: SoSanhSo[]; lay_tang: (s: SoSanhSo) => number | null; don_vi: string }) {
  return <>{ss.map(s => <div key={s.ma}>{!s.co ? <span className="nhat-chu">{s.nhan}: không có dữ liệu để so</span> : <>
    {lay_tang(s) != null ? <span className={lay_tang(s)! >= 0 ? "tang" : "giam"}>{dau(lay_tang(s)!)}{don_vi}</span> : <span>—</span>}
    {" "}so <MauSs />{s.nhan} ({ngay(s.tu)} → {ngay(s.den)})</>}</div>)}</>;
}

function SparkSvg({ s, mau }: { s: Spark; mau: string }) {
  if (!s?.co) return null;
  return (
    <svg className="bc-spark" viewBox={`0 0 ${s.rong} ${s.cao}`} preserveAspectRatio="none" aria-hidden="true" focusable="false">
      {(s.doan_ss ?? []).map((d, i) => <polyline key={"ss" + i} points={d} fill="none" stroke="var(--vien-dam)" strokeWidth={1.3}
        strokeDasharray="3 2.5" vectorEffect="non-scaling-stroke" />)}
      {s.doan.map((d, i) => <polyline key={i} points={d} fill="none" stroke={mau} strokeWidth={1.6} vectorEffect="non-scaling-stroke" />)}
      {s.diem_don.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={1.8} fill={mau} />)}
    </svg>);
}

function The({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={"kh-the bc-khoi " + className}>{children}</section>;
}

export default function BaoCao() {
  const kxs = chuoiKhoang(useKhoang());
  const nhanMoc = useNhanMoc();
  const [cs, datCs] = useState<"dt" | "lg">("dt");
  const [kb, datKb] = useState("cs");
  const { data: d, error, isFetching } = useQuery<BaoCaoApi>({
    queryKey: ["bao-cao", kxs], queryFn: () => lay<BaoCaoApi>(voiKhoang("/api/bao-cao")), placeholderData: keepPreviousData,
  });
  // Dự báo: cùng khoảng xem (mốc của khoảng) — ảnh chụp riêng, tải song song, không chặn trang.
  const { data: f } = useQuery<DuBaoApi>({
    queryKey: ["du-bao", kxs], queryFn: () => lay<DuBaoApi>(voiKhoang("/api/du-bao")), placeholderData: keepPreviousData,
  });

  if (error) return <div className="khoi-loi">Không tải được trang Doanh thu: {(error as Error).message}</div>;
  if (!d) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const { bc, td } = d;
  if (bc.khong_co_du_lieu) return <><h1>Doanh thu</h1>
    <div className="khoi-loi">Chưa có dòng bán hàng nào trong kho dữ liệu. Hãy nạp file <b>売上伝票データ</b> trước.</div></>;
  const lg = cs === "lg";
  const ten = lg ? "lãi gộp" : "doanh thu";
  const ck = bc.cung_ky;
  const kx = d.khoang;
  const theoKy = !kx || (kx.loai === "ky" && !kx.tu_chon);
  const ss = bc.so_sanh ?? [];
  const nhanSs = kx?.so_sanh[0]?.nhan ?? "cùng kỳ năm trước";
  const lechSs = kx?.so_sanh[0]?.lech_thang ?? 12;
  const theoNgay = bc.thang.length > 0 && bc.thang[0].thang.length === 10;

  // Dự báo chỉ áp khi tháng của mốc nằm trong khoảng đang xem (dạng Tháng: đúng tháng đó; dạng Kỳ:
  // tháng thuộc kỳ). Dạng Khoảng không có ngân sách / dự báo theo tháng.
  const db = f?.db ?? null;
  const chot = db ? (lg ? db.chot_lg : db.chot) : null;
  const trongKy = (t: string) => !!td?.thang_cty.some(x => x.thang === t);
  const coDuBao = !!chot && !!kx && (kx.loai === "thang" ? kx.thang === chot.thang : kx.loai === "ky" && trongKy(chot.thang));
  const nam = db ? (lg ? db.nam_lg : db.nam) : null;
  const theo = f ? (lg ? f.theo_lg : f.theo)[kb] ?? [] : [];

  const xuatCsv = () => {
    const cot = [theoNgay ? "Ngày" : "Tháng", "Doanh thu thuần", "Lãi gộp", "Tỷ suất", hoa(nhanSs), "Số phiếu", "Khách có đơn"];
    const dong = bc.thang.map(o => [o.thang, o.doanh_thu, o.lai_gop, o.ty_suat ?? "", o.co_cung_ky ? o.dt_cung_ky ?? "" : "", o.so_phieu, o.so_khach]);
    const csv = "﻿" + [cot, ...dong].map(r => r.map(x => `"${String(x).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = theoKy ? `doanh-thu-ky-${bc.ky.so_ky}.csv` : `doanh-thu-${kx!.tu}_${kx!.den}.csv`; a.click(); URL.revokeObjectURL(a.href);
  };

  // ---- Ô số ----
  const tienDo = td ? (lg ? td.tien_do_lg : td.tien_do) : null;
  const moc = td ? (lg ? td.pct_moc_chi_tieu_lg : td.pct_moc_chi_tieu) : null;
  const coNs = td ? (lg ? td.co_ngan_sach_lg : td.co_ngan_sach) : false;
  const lienNs = KD.hien_ngan_sach ? `/ngan-sach?ky=${td?.company_fy ?? bc.ky.company_fy}` : null;

  // ---- Biểu đồ chính: 12 tháng của kỳ ----
  const chuoiChinh = (): { nhan: string[]; chuoi: Chuoi[]; vach: { i: number; chu: string } | null } => {
    if (td && td.thang_cty.length) {
      const th = td.thang_cty.map(t => t.thang);
      const iDb = (t: string) => nam?.du_bao.findIndex(x => x.thang === t) ?? -1;
      const duBao = th.map(t => {
        if (!coDuBao || !chot) return null;
        if (t === chot.thang) return chot.co_so;
        const i = iDb(t);
        return t > chot.thang && i >= 0 ? theo[i] ?? null : null;
      });
      const ssk = d.ss_thang.thang;
      const ky_so = th.map(t => ssk[t] ? (lg ? (d.ss_thang.co_lg ? ssk[t][1] : null) : ssk[t][0]) : null);
      const iNay = coDuBao && chot ? th.indexOf(chot.thang) : -1;
      return {
        nhan: th.map(thNgan),
        chuoi: [
          { ten: "Thực tế", kieu: "cot", mau: "var(--lien-ket)", gia_tri: td.thang_cty.map(t => lg ? t.thuc_te_lg : t.thuc_te) },
          ...(duBao.some(v => v != null) ? [{ ten: `Dự báo (${f!.kich_ban[kb]})`, kieu: "cot_nen" as const, mau: "var(--do-nen)", gia_tri: duBao }] : []),
          { ten: "Ngân sách", kieu: "duong", mau: "var(--do)", gia_tri: td.thang_cty.map(t => lg ? t.ngan_sach_lg : t.ngan_sach) },
          ...(ky_so.some(v => v != null) ? [{ ten: hoa(nhanSs), kieu: "cot_ma" as const, mau: "var(--vien-dam)", gia_tri: ky_so, so_voi: 0 }] : []),
        ],
        vach: iNay >= 0 ? { i: iNay, chu: nhanMoc } : null,
      };
    }
    return {
      nhan: bc.thang.map(o => o.thang.length === 10 ? String(+o.thang.slice(8)) : thNgan(o.thang)),
      chuoi: [
        { ten: "Thực tế", kieu: "cot", mau: "var(--lien-ket)", gia_tri: bc.thang.map(o => lg ? o.lai_gop : o.doanh_thu) },
        { ten: hoa(nhanSs), kieu: "cot_ma", mau: "var(--vien-dam)", so_voi: 0,
          gia_tri: bc.thang.map(o => o.co_cung_ky ? (lg ? o.lg_cung_ky : o.dt_cung_ky) : null) },
      ],
      vach: null,
    };
  };
  const bd = chuoiChinh();
  const tongNam = f ? (lg ? f.tong_lg : f.tong)[kb] : null;

  const bn = d.bong_nganh[cs], bm = d.bong_ma[cs];
  const nguoiDb = db && coDuBao ? Object.fromEntries(db.nguoi.map(n => [n.ma ?? "", n])) : {};
  const ssNguoi = kx?.loai === "thang" && ss[0]?.co && !lg ? Object.fromEntries(bc.nhan_vien.map(n => [n.ma ?? "", n.dt_ss ?? null])) : null;

  return (
    <div className={"bc dt" + (isFetching ? " dang-tai" : "")}>
      <div className="tieu-de-trang">
        <div><h1>Doanh thu</h1>
          <div className="phu">{bc.ky.nhan}{theoKy ? ` · ${bc.ky.so_thang}/12 tháng` : ` · ${ngay(kx!.tu)} → ${ngay(kx!.den)}`}</div></div>
        <div className="bc-dk">
          <div className="tab-pill" role="group" aria-label="Chỉ số">
            <button type="button" aria-pressed={!lg} onClick={() => datCs("dt")}>Doanh thu</button>
            <button type="button" aria-pressed={lg} onClick={() => datCs("lg")}>Lãi gộp</button></div>
          {lienNs && <a className="nut-nho" href={lienNs}>✎ Sửa ngân sách</a>}
          <button type="button" className="nut-nho" onClick={xuatCsv} title={`Xuất CSV theo ${theoNgay ? "ngày" : "tháng"}`}>⤓ CSV</button>
        </div>
      </div>
      {bc.canh_bao.map(c => <div key={c} className="khoi-loi">⚠️ {c}</div>)}

      <div className="o-kpi-luoi bc-kpi">
        <div className="o-kpi"><div className="nhan">{lg ? "Lãi gộp" : "Đã bán"}</div><div className="gia">{gon(lg ? bc.ky.lai_gop : bc.ky.doanh_thu)}</div>
          <SparkSvg s={lg ? d.so_nho.lg : d.so_nho.dt} mau="var(--lien-ket)" />
          <div className="bc-ck">{theoKy ? <SoCungKy ck={ck} tang={(lg ? ck?.tang_lg : ck?.tang_dt) ?? null} don_vi="%" ngay_dau={d.ngay_dau_du_lieu} />
            : <SoSanhDong ss={ss} lay_tang={s => lg ? s.tang_lg : s.tang_dt} don_vi="%" />}</div></div>
        <div className="o-kpi"><div className="nhan">Dự kiến chốt {chot ? thNgan(chot.thang) : "tháng"}{" "}
          {coDuBao && chot && <ONoi nhan="Cách tính" className="khoi-i" noi_dung={<div className="o-noi-chu">
            Đã có + ({ten} đã có ÷ {chot.e} ngày làm việc đã qua) × {chot.n - chot.e} ngày làm việc còn lại. Khoảng thấp – cao là sai số thật
            của chính cách tính này trên các tháng trước.
            {chot.kiem.length > 0 && <><br /><b>Đã chuẩn tới đâu</b> (lập sau {chot.moc_kiem} ngày làm việc):
              {chot.kiem.map(k => <DongNoi key={k.thang} nhan={tNhan(k.thang)} gia={k.lech != null ? dau(k.lech) + "%" : "—"} />)}</>}
          </div>}>ⓘ</ONoi>}</div>
          {coDuBao && chot ? <>
            <div className="gia">{gon(chot.co_so)}</div>
            <div className="dong-phu nhat-chu">{chot.xong ? "tháng đã đủ ngày" : chot.thap != null && chot.cao != null
              ? `${gon(chot.thap)} – ${gon(chot.cao)}` : "chưa đủ 3 tháng cũ để đo sai số"}</div></>
            : <><div className="gia nhat-chu">—</div>
              <div className="dong-phu nhat-chu">{!f ? "đang tải dự báo…" : kx?.loai === "khoang" ? "dạng Khoảng không dự báo theo tháng" : "khoảng đang xem đã qua — không dự báo"}</div></>}</div>
        <div className="o-kpi"><div className="nhan">Ngân sách {td ? thNgan(td.thang) : ""}</div>
          {td && coNs ? <>
            <div className="gia">{tienDo != null ? p1(tienDo) : "—"}</div>
            <Thanh rong={tienDo} moc={moc != null ? moc / 100 : null} />
            <div className="dong-phu nhat-chu">mốc {nhanMoc} {moc != null ? p1(moc / 100) : "—"}</div></>
            : <><div className="gia nhat-chu">{td ? "Chưa đặt" : "—"}</div>
              <div className="dong-phu nhat-chu">{!td ? "ngân sách chỉ theo tháng / kỳ" : lienNs ? <a href={lienNs}>Đặt ngân sách {ten}</a> : `chưa đặt ngân sách ${ten}`}</div></>}</div>
        <div className="o-kpi"><div className="nhan">Biên lãi gộp</div><div className="gia">{bc.ky.ty_suat != null ? p1(bc.ky.ty_suat) : "—"}</div>
          <SparkSvg s={d.so_nho.ts} mau="var(--ok-vien)" />
          <div className="bc-ck">{theoKy ? <SoCungKy ck={ck} tang={ck?.chenh_ty_suat ?? null} don_vi=" điểm" ngay_dau={d.ngay_dau_du_lieu} />
            : <SoSanhDong ss={ss} lay_tang={s => s.chenh_ty_suat} don_vi=" điểm" />}</div></div>
      </div>

      <The className="dt-chinh">
        <Khoi tieu_de={td ? "12 tháng của kỳ" : `Theo ${theoNgay ? "ngày" : "tháng"}`}
          phu={<><MauSs />{nhanSs}</>}
          cach_tinh={<>Cột: {ten} thực tế. {coDuBao && <>Cột nhạt: dự báo — tháng này = chốt dự kiến, các tháng sau = {ten} cùng tháng năm trước ×
            hệ số (tỷ số các tổng của {nam?.doi_chieu.length ?? 0} tháng đối chiếu).{tongNam != null && nam && nam.tong_cung_ky > 0 &&
            <> Tổng {nam.du_bao.length} tháng tới: {gon(tongNam)} ({dau(tongNam / nam.tong_cung_ky - 1)}% so cùng các tháng năm trước).</>} </>}
            Đường: ngân sách công ty (nhập thẳng ở màn Ngân sách). Viền đứt: {nhanSs}.</>}
          canh_bao={!td ? "Dạng Khoảng: ngân sách và dự báo chỉ có theo tháng / kỳ." : !coNs ? `Chưa đặt ngân sách ${ten} tháng này.` : null}
          cach_xem={coDuBao && f ? { ds: Object.entries(f.kich_ban).map(([id, nhan]) => ({ id, nhan })), chon: kb, dat: datKb } : undefined}>
          <BieuDo nhan={bd.nhan} chuoi={bd.chuoi} cao={230} vach={bd.vach} mo_ta={`${hoa(ten)} theo tháng, ngân sách, dự báo và ${nhanSs}`}
            dinh_dang={v => v == null ? "—" : yen(v)} dinh_dang_truc={v => gon(v)} />
        </Khoi>
      </The>

      <div className="bc-hai">
        {coDuBao && (lg ? f!.ve_chot_lg : f!.ve_chot).co && <The>
          <Khoi tieu_de={`Luỹ kế ${chot ? thNgan(chot.thang) : ""}`} phu={`${chot!.e}/${chot!.n} ngày làm việc`}
            cach_tinh={<>Đường xanh: {ten} cộng dồn tới {nhanMoc}. Đường đỏ: dự báo cơ sở tới cuối tháng, vùng xám là khoảng thấp – cao.
              Đường xám: nhịp ngân sách theo ngày làm việc (đã trừ thứ Bảy, Chủ nhật, ngày lễ — chưa trừ ngày nghỉ riêng của công ty).</>}>
            <LuyKe v={lg ? f!.ve_chot_lg : f!.ve_chot} />
          </Khoi></The>}
        <The>
          <Khoi tieu_de="Người phụ trách" phu={td ? thNgan(td.thang) : undefined}
            cach_tinh={<>Mỗi thẻ một người. Thanh = ngân sách của chính người đó (đầy thanh = đạt 100%). Phần đậm: {ten} đã có; phần nhạt: dự báo thêm tới cuối tháng (cùng công thức chốt tháng). Vạch cam: mức lẽ ra phải đạt tới {nhanMoc} — ngân sách chia theo ngày làm việc đã qua.
              {ssNguoi && <> Vạch đứt: {nhanSs}.</>}</>}
            canh_bao={!td ? "Dạng Khoảng: không có ngân sách theo người." : null}>
            {td && <NguoiPhuTrach td={td} lg={lg} db={nguoiDb} ss={ssNguoi} nhan_ss={nhanSs} />}
          </Khoi></The>
      </div>

      <div className="bc-hai">
        <The>
          <Khoi tieu_de="Vì sao tăng / giảm" phu={<><MauSs />{nhanSs}</>}
            cach_tinh={<>Từ doanh thu {nhanSs} (cột viền đứt), mỗi danh mục cộng hoặc trừ phần chênh, ra kỳ này — cùng dải
              {theoKy && ck ? ` ${ck.so_thang} tháng đối chiếu` : " ngày so"}. Trục không bắt đầu từ 0.</>}
            canh_bao={cb(lg && "Cầu nối theo doanh thu (chưa có lãi gộp kỳ so theo danh mục).",
              !!d.cau_noi.co && !!d.cau_noi.khong_so && d.cau_noi.khong_so.so > 0 && `${d.cau_noi.khong_so.so} danh mục không có số so (${yen(d.cau_noi.khong_so.tien)}) — không vào cầu.`)}>
            <CauNoi v={d.cau_noi} nhan_ss={nhanSs} />
          </Khoi></The>
        <The>
          <Khoi tieu_de="Danh mục" phu="tăng/giảm × biên"
            cach_tinh={<>Mỗi bóng một danh mục (食品分類). Ngang: tăng / giảm doanh thu so {nhanSs}; dọc: biên lãi gộp;
              cỡ bóng: {ten}. Đường chữ thập: 0% và biên của cả công ty. Góc trên phải = tăng và lãi dày.</>}
            canh_bao={bn.so_khong_ve > 0 ? `Không vẽ: ${yen(bn.khong_ve)} của ${bn.so_khong_ve} danh mục (${ten} ≤ 0 hoặc không có số so).` : null}>
            <Bong v={bn} nhan_x={x => dau(x) + "%"} ten_x={`so ${nhanSs}`} ten_y="biên" mo_ta={`Danh mục theo tăng trưởng và biên lãi gộp, cỡ theo ${ten}`}
              mau={b => b.x >= 0 && (bn.y_moc == null || b.cy <= bn.y_moc) ? "var(--ok-vien)" : b.x < 0 && bn.y_moc != null && b.cy > bn.y_moc ? "var(--loi-vien)" : "var(--lien-ket)"}
              noi={b => <><DongNoi nhan={hoa(ten)} gia={yen(b.kich)} />{dongBong.tang(b, nhanSs)}{dongBong.bien(b)}</>} />
          </Khoi></The>
      </div>

      <div className="bc-hai">
        <The>
          <Khoi tieu_de="Mặt hàng" phu={`top ${bm.so_ma ?? 0} theo doanh thu`}
            cach_tinh={<>Mỗi bóng một mã. Ngang: số khách mua; dọc: biên lãi gộp; cỡ bóng: {ten}. Bóng bên phải mà thấp = nhiều người mua nhưng lãi
              mỏng — nên xem lại giá. Bấm bóng mở trang mã. Không gồm phí, hàng tặng POSM, hàng ※終売※ đã hết tồn.</>}
            canh_bao={bm.so_khong_ve > 0 ? `Không vẽ: ${bm.so_khong_ve} mã (${ten} ≤ 0 hoặc thiếu số).` : null}>
            <Bong v={bm} nhan_x={x => so(Math.round(x))} ten_x="khách mua" ten_y="biên" mo_ta={`Mặt hàng theo số khách mua và biên lãi gộp, cỡ theo ${ten}`}
              mau={() => "var(--lien-ket)"} href={b => `/san-pham/${encodeURIComponent(b.ma)}`} so_nhan={6}
              noi={(b: BongDiem) => <><DongNoi nhan={hoa(ten)} gia={yen(b.kich)} />{dongBong.khach(b)}{dongBong.bien(b)}</>} />
          </Khoi></The>
        <The>
          <Khoi tieu_de="Khách lớn" phu={bc.tap_trung?.luy_ke_top10 != null ? `10 khách = ${p1(bc.tap_trung.luy_ke_top10)}` : undefined}
            cach_tinh={<>Cột: doanh thu 20 khách lớn nhất; đường: luỹ kế % trên tổng ({so(bc.tap_trung?.so_khach ?? 0)} khách có đơn). Bấm cột mở hồ sơ khách.</>}
            canh_bao={lg ? "Theo doanh thu (Pareto chưa có lãi gộp)." : null}>
            <Pareto pa={d.pa} />
          </Khoi></The>
      </div>

      <The>
        <Khoi tieu_de="Danh mục × tháng" phu={<><MauSs />{lechSs === 12 ? "cùng tháng năm trước" : lechSs === 1 ? "tháng liền trước" : `lùi ${lechSs} tháng`}</>}
          cach_tinh={<>Mỗi ô: doanh thu của danh mục trong tháng so với cùng danh mục ở tháng {nhanSs}. Rê ô để xem số.</>}
          canh_bao={cb(kx?.so_sanh[0]?.lech_thang == null && !theoKy && `${hoa(nhanSs)} không lệch tròn tháng — không so theo tháng được.`,
            lg && "Theo doanh thu.")}>
          {d.nh.co ? <>
            <div className="bang-cuon"><table className="nhiet-bang">
              <thead><tr><th scope="col" />{d.nh.thang.map(t => <th key={t} scope="col">{t.slice(5)}</th>)}</tr></thead>
              <tbody>{d.nh.hang.map(h => <tr key={h.nganh}><th scope="row">{h.nganh}</th>{h.o.map(o => <ONhiet key={o.thang} o={o} dau_du_lieu={d.nh.thang_dau_du_lieu} nhan_ss={nhanSs} />)}</tr>)}</tbody>
            </table></div>
            <div className="chu-giai bc-cg">
              <span><i className="mau bac-g2" /> ≤ −20%</span><span><i className="mau bac-g1" /> −20…−5%</span><span><i className="mau bac-0" /> ±5%</span>
              <span><i className="mau bac-t1" /> +5…+20%</span><span><i className="mau bac-t2" /> ≥ +20%</span>
              <span><i className="mau bac-khong_ck" /> không có số để so</span><span><i className="mau bac-chua_toi" /> chưa có dữ liệu</span>
            </div></> : <p className="phu">Chưa có dữ liệu để vẽ khối này.</p>}
        </Khoi></The>

      {db && <The>
        <Khoi tieu_de="Nguy cơ ngừng mua" phu={`${db.kh.so_nguy_co} khách · ${gon(db.kh.tien_nguy_co)}`} lien_ket={{ href: "/lien-he?tat_ca=1", chu: "Gọi lại" }}
          cach_tinh={<>Khách đang im lặng quá 2 lần nhịp mua riêng — cùng định nghĩa "khách đang rời đi" với Cần liên hệ. Xếp theo doanh thu luỹ kế;
            thanh = số lần nhịp đã im lặng.</>} canh_bao={lg ? "Theo doanh thu." : null}>
          <div className="dt-nguy-co">
            {db.kh.nguy_co.map(k => (
              <ONoi key={k.ma} href={`/khach-hang/${encodeURIComponent(k.ma)}`} nhan={k.ten} className="dt-nc-dong"
                noi_dung={<><b>{k.ten}</b><DongNoi nhan="Im lặng" gia={`${k.so_ngay_im_lang} ngày`} />
                  <DongNoi nhan="So nhịp mua riêng" gia={`${k.ty_le.toFixed(1)}×`} /><DongNoi nhan="Doanh thu luỹ kế" gia={yen(k.doanh_thu)} /></>}>
                <span className="ten-jp">{k.ten}</span>
                <span className={"thanh-nho " + (k.trang_thai === "da_roi_bo" ? "loi" : "canh")}><span className="thanh-nho-nen">
                  <span style={{ display: "block", height: "100%", width: `${(Math.min(k.ty_le / 4, 1) * 100).toFixed(1)}%` }} /></span></span>
                <b className="so">{gon(k.doanh_thu)}</b>
              </ONoi>))}
            {!db.kh.nguy_co.length && <p className="phu">Không khách nào đang im lặng quá 2 lần nhịp.</p>}
          </div>
        </Khoi></The>}

      {(bc.phi.dong.length > 0 || bc.hang_tang.dong.length > 0) && <p className="phu dt-phi">
        Đã gồm trong tổng, không vào danh mục:{" "}
        {bc.phi.dong.length > 0 && <ONoi nhan="Phí & điều chỉnh" noi_dung={<><b>Phí &amp; điều chỉnh (無形 / làm tròn)</b>
          {bc.phi.dong.slice(0, 8).map(h => <DongNoi key={h.ma || h.ten} nhan={h.ten} gia={h.doanh_thu != null ? yen(h.doanh_thu) : "—"} />)}</>}>
          Phí &amp; điều chỉnh {yen(bc.phi.doanh_thu)}</ONoi>}
        {bc.phi.dong.length > 0 && bc.hang_tang.dong.length > 0 && " · "}
        {bc.hang_tang.dong.length > 0 && <ONoi nhan="Hàng tặng POSM" noi_dung={<><b>Hàng tặng POSM (雑貨_VNM)</b>
          {bc.hang_tang.dong.slice(0, 8).map(h => <DongNoi key={h.ma} nhan={h.ten} gia={h.lai_gop != null ? yen(h.lai_gop) : "—"} />)}</>}>
          Hàng tặng POSM · lãi gộp {yen(bc.hang_tang.lai_gop)}</ONoi>}
      </p>}
    </div>
  );
}

function LuyKe({ v }: { v: VeChot }) {
  return (
    <div className="dt-luy">
      <svg viewBox={`0 0 ${v.rong} ${v.cao}`} width="100%" role="img" aria-label="Luỹ kế tháng và dự báo chốt tháng">
        {v.truc.map(t => <g key={t.y}><line x1={v.trai} y1={t.y} x2={v.phai} y2={t.y} className="luoi-truc" />
          <text x={v.trai - 8} y={t.y + 4} textAnchor="end" className="chu-truc">{t.nhan}</text></g>)}
        {v.dai && <path d={v.dai} className="dai-db" />}
        {v.ns && <polyline points={v.ns} className="duong-ns" />}
        {v.cs && <polyline points={v.cs} className="duong-cs" />}
        <polyline points={v.tt} className="duong-tt" />
        <circle cx={v.x_nay} cy={v.y_nay} r={4.5} className="cham-tt" />
        {v.cs && <circle cx={v.x_cuoi} cy={v.y_cuoi} r={4.5} className="cham-cs" />}
        {v.nhan_ngay.map(n => <text key={n.x} x={n.x} y={v.cao - 10} textAnchor="middle" className="chu-truc">{n.nhan}</text>)}
      </svg>
    </div>);
}

function NguoiPhuTrach({ td, lg, db, ss, nhan_ss }: { td: Td; lg: boolean; db: Record<string, NguoiDb>;
  ss: Record<string, number | null> | null; nhan_ss: string }) {
  const nhanMoc = useNhanMoc();
  // Tháng đã qua hết ngày làm việc: mức "lẽ ra tới hôm nay" = chính ngân sách, không in dòng nhịp.
  const conNgay = td.ngay_kd_da_qua < td.ngay_kd;
  if (!td.nguoi.length) return <p className="phu">Chưa có dòng nào tháng này.</p>;
  return <div className="dt-nguoi">{td.nguoi.map(n => {
    const f = db[n.ma];
    const tt = lg ? n.thuc_te_lg : n.thuc_te, mt = lg ? n.muc_tieu_lg : n.muc_tieu;
    const moc = lg ? n.muc_tieu_lg_den_hom_nay : n.muc_tieu_den_hom_nay;
    // Tháng đã khép: dự kiến chốt = đã có, không in lại.
    const cs = f && conNgay ? (lg ? f.co_so_lg : f.co_so) : null;
    const s = ss?.[n.ma] ?? null, td_ = lg ? n.tien_do_lg : n.tien_do;
    // Thanh = 100% ngân sách của CHÍNH người này (không chung thước với người khác).
    const w = (v: number) => `${Math.max(0, Math.min(100, v / (mt as number) * 100))}%`;
    const coNs = mt != null && mt > 0;
    const lech = moc != null ? tt - moc : null;
    const ten = n.ten ?? n.ma;
    return (
      <ONoi key={n.ma} nhan={ten} className="dt-ng-the" noi_dung={<><b>{n.ten ?? `${n.ma} (không có trong danh sách phụ trách)`}</b>
        <DongNoi nhan="Đã có" gia={yen(tt)} />{cs != null && <DongNoi nhan="Dự kiến chốt" gia={yen(cs)} />}
        <DongNoi nhan="Ngân sách" gia={mt != null ? yen(mt) : "chưa đặt"} />
        {conNgay && moc != null && <DongNoi nhan={`Lẽ ra ${nhanMoc}`} gia={yen(moc)} />}
        {td_ != null && <DongNoi nhan="Tiến độ" gia={p1(td_)} />}
        {s != null && <DongNoi nhan={hoa(nhan_ss)} gia={yen(s)} />}</>}>
        <span className="dt-ng-ten">{ten}</span>
        <b className="dt-ng-so">{gon(tt)}</b>
        <span className="dt-ng-ns">{mt != null ? <>/ ngân sách {gon(mt)}</> : "chưa đặt ngân sách"}</span>
        {coNs && <span className="dt-ng-thanh" aria-hidden="true">
          {cs != null && cs > tt && <span className="dt-ng-db" style={{ width: w(cs) }} />}
          <span className="dt-ng-tt" style={{ width: w(tt) }} />
          {conNgay && moc != null && <span className="dt-ng-nhip" style={{ left: w(moc) }} />}
          {s != null && <span className="ss-vach" style={{ left: w(s) }} />}
        </span>}
        {td_ != null && <span className="dt-ng-pt">{p1(td_)}</span>}
        {conNgay && moc != null && lech != null && <span className={"dt-ng-lech " + (lech < 0 ? "thieu" : "vuot")}>
          Lẽ ra {nhanMoc} {gon(moc)} · đang {lech < 0 ? "thiếu" : "vượt"} {gon(Math.abs(lech))}</span>}
        <span className="dt-ng-phu">
          {mt != null && (tt < mt ? <>Còn thiếu {gon(mt - tt)}</> : <>Đã đạt ngân sách ✓</>)}
          {cs != null && <>{mt != null && " · "}dự kiến chốt {gon(cs)}</>}
          {s != null && <>{(mt != null || cs != null) && " · "}{nhan_ss} {gon(s)}</>}
        </span>
      </ONoi>);
  })}</div>;
}

function Pareto({ pa }: { pa: BaoCaoApi["pa"] }) {
  if (!pa.co) return <p className="phu">Chưa có dữ liệu để vẽ khối này.</p>;
  return (
    <svg viewBox={`0 0 ${pa.rong} ${pa.cao}`} width="100%" className="bc-svg" role="group" aria-label="Doanh thu và luỹ kế của 20 khách hàng lớn nhất">
      {pa.truc_pct.map(t => <g key={t.y}><line x1={0} y1={t.y} x2={pa.rong} y2={t.y} stroke="var(--vien)" strokeWidth={1} />
        <text x={pa.rong - 4} y={t.y - 3} fontSize={9} textAnchor="end" fill="var(--chu-nhat)">{t.nhan}</text></g>)}
      {pa.cot.map(c => <a key={c.khach.ma} href={`/khach-hang/${encodeURIComponent(c.khach.ma)}`}>
        <rect x={c.x} y={c.y} width={c.w} height={c.h} rx={2} fill="var(--lien-ket)" opacity={0.72} className="bc-cot-kh">
          <title>Thứ {c.khach.thu_hang} — {c.khach.ten}: {yen(c.khach.doanh_thu)}{c.khach.ty_trong != null ? ` (${p1(c.khach.ty_trong)})` : ""} · bấm để mở hồ sơ</title></rect></a>)}
      {pa.doan.map((s, i) => <polyline key={i} points={s} fill="none" stroke="var(--do)" strokeWidth={2} />)}
      {pa.diem.map(p => <circle key={p.khach.ma} cx={p.x} cy={p.y} r={2.5} fill="var(--do)">
        <title>Thứ {p.khach.thu_hang} — {p.khach.ten}: luỹ kế {p.khach.luy_ke != null ? p1(p.khach.luy_ke) : "—"}</title></circle>)}
    </svg>);
}

function ONhiet({ o, dau_du_lieu, nhan_ss }: { o: BaoCaoApi["nh"]["hang"][0]["o"][0]; dau_du_lieu: string | null; nhan_ss: string }) {
  const nhan = `${o.nganh} · ${o.thang}`;
  if (o.bac === "chua_toi") return <td className="bac-chua_toi" title={`${nhan}: chưa tới tháng này trong kỳ`}>·</td>;
  if (o.bac === "truoc_du_lieu") return <td className="bac-chua_toi" title={`${nhan}: chưa có dữ liệu (trước ${dau_du_lieu})`}>·</td>;
  if (o.bac === "khong_ban") return <td className="bac-khong_ban" title={`${nhan}: không bán tháng này${o.co_the_ck ? ` (và ở ${nhan_ss} cũng vậy)` : ""}`}>¥0</td>;
  if (o.bac === "khong_ck") return <td className="bac-khong_ck" title={`${nhan}: không có số ${nhan_ss} để so (${yen(o.doanh_thu)})`}>—</td>;
  if (o.tang_truong != null) return <td className={"bac-" + o.bac} title={`${nhan}: ${dau(o.tang_truong)}% so ${nhan_ss} (${yen(o.doanh_thu)})`}>{dau(o.tang_truong)}%</td>;
  return <td className="bac-khong" title={`${nhan}: ${nhan_ss} ≤ 0, không tính được % (${yen(o.doanh_thu)})`}>—</td>;
}

function Thanh({ rong, moc }: { rong: number | null; moc: number | null }) {
  if (rong == null) return null;
  const r = Math.max(0, Math.min(1, rong)) * 100;
  return <div className="thanh-tien-do vua" role="img" aria-label={`${r.toFixed(1)}% ngân sách`}>
    <div className="day" style={{ width: `${r}%` }} />{moc != null && <div className="moc" style={{ left: `${Math.max(0, Math.min(1, moc)) * 100}%` }} />}</div>;
}
