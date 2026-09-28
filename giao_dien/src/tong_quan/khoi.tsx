// Các khối của Tổng quan — bố cục theo Dashboard.dc.html, số THẬT từ
// /api/tong-quan/<khối> (kome/khoi_tong_quan.py). Không số mẫu ở đâu cả.
import { Fragment, useRef, useState, type ReactNode } from "react";
import { useKhoi } from "../api";
import { giuKhoang } from "../khung/khoang";
import { BieuDo, type Chuoi } from "../chung/BieuDo";
import { ChuaCoDuLieu, Khoi, Spark, ThanhMoc, mauTienDo, type CachXem } from "../chung/Khoi";
import { gio_tokyo, gon, ngay, ngay_ngan, pc, so, thang_nhan, thay_doi, yen } from "../dinh_dang";
import { KD, TN } from "../khoi_dau";
import { useNhanMoc, type KhoangMayChu } from "../khung/khoang";
import { DongSoSanh, VachSoSanh } from "../chung/SoSanh";
import { DongNoi, ONoi } from "../chung/ONoi";
import { buocCham } from "../chung/o_noi_logic";
import { HangSo, MucSo, SoLon, ThanhChong, ThanhNgang, Vong, type DongThanh, type Khuc } from "../chung/Hinh";
import { demTheoTag, sapViec, tenViec } from "./viec_logic";
import { DaiHan, type Lo } from "./DaiHan";

const LUC = { ok: "var(--ok-vien)", canh: "var(--lien-ket)", do: "var(--do)", nhat: "var(--chu-mo)", nen: "var(--vien)" };
/** Nhiều ngoại lệ có thể cùng xảy ra (đặc tả §4: LUÔN hiện, không phải chỉ ngoại lệ đầu tiên
 *  của một chuỗi ternary) — lọc bỏ cái không áp dụng rồi in mỗi cái một dòng. */
function canhBaoNhieu(ds: (ReactNode | null | undefined | false)[]): ReactNode | undefined {
  const ap = ds.filter((x): x is ReactNode => x != null && x !== false);
  return ap.length ? <>{ap.map((m, i) => <Fragment key={i}>{i > 0 && <br />}{m}</Fragment>)}</> : undefined;
}
const tenNguoi = (ten: string | null | undefined, ma: string) => ten || `(mã ${ma})`;
const MO = "color-mix(in srgb, var(--lien-ket) 35%, var(--nen-the))";
// Kỳ so (đặc tả 2026-09-28): một kỳ cho cả trang, nhãn của MÁY CHỦ. Màu chung của
// mọi nét đứt / cột ma; chữ hoa đầu câu cho chú giải.
const MAU_SS = "var(--vien-dam)";
const hoa = (s: string | null | undefined) => (s ?? "").replace(/^./, c => c.toUpperCase());
type SsKhoi = { ma: string; nhan: string; co: boolean; tu: string; den: string; lech_thang: number | null } | null;
const tdSs = (a: number | null | undefined, b: number | null | undefined) => (a != null && b ? a / b - 1 : null);
/** "▲12% so tháng trước" nhỏ, cạnh một số — không in gì khi không so được. */
function TdSs({ nay, ss, nhan }: { nay: number | null | undefined; ss: number | null | undefined; nhan: string }) {
  const td = tdSs(nay, ss);
  return td == null ? null : <span className={"so-nhat " + (td >= 0 ? "tang" : "giam")} title={`${hoa(nhan)}: ${yen(ss)}`}>{thay_doi(td, 0)}</span>;
}

/** Tháng 'YYYY-MM' có nằm trong khoảng xem không (tô đậm cột). */
const trongKhoang = (kx: KhoangMayChu | null | undefined, thang: string) =>
  !!kx && thang >= kx.tu.slice(0, 7) && thang <= kx.den.slice(0, 7);
// ---- Cách xem (2026-09-29) ---------------------------------------------------
// Danh mục cách xem là của MÁY CHỦ (kome/web/bo_cuc.py::CACH_XEM, qua KD.danh_muc); lựa chọn
// lưu trong ô bố cục của bảng đang xem (`xem`, null = cách đầu). Mỗi cách chỉ VẼ LẠI số khối đã
// tải — không chỉ số mới; cách nào dữ liệu không mang kỳ so thì nói ra ở canh_bao.
export type XemP = { xem: string | null; datXem: (ma: string | null) => void };
function useCachXem(id: string, p: XemP): CachXem {
  const ds = KD.danh_muc.khoi.find(k => k.id === id)?.cach_xem ?? [];
  const chon = ds.some(x => x.id === p.xem) ? p.xem! : ds[0]?.id ?? "";
  return { ds, chon, dat: m => p.datXem(m === ds[0]?.id ? null : m) };
}
/** Cộng dồn; gặp ô trống thì mọi điểm sau là null (không nối luỹ kế qua lỗ). */
function luyKe(ds: (number | null | undefined)[]): (number | null)[] {
  let t = 0, dut = false;
  return ds.map(v => { if (dut || v == null) { dut = true; return null; } t += v; return t; });
}
const CHI_DT = (ss: { nhan: string } | null | undefined) => ss ? `${hoa(ss.nhan)}: khối này chỉ mang số kỳ so của doanh thu — chọn cách xem Doanh thu để so.` : undefined;

const NS_THEO_THANG = "Chỉ tiêu chỉ đặt theo tháng — chọn dạng Tháng hoặc Kỳ ở thanh KHOẢNG XEM để xem tiến độ.";

// ---- Chỉ số hôm nay ---------------------------------------------------------
type SoSanhKpi = { ma: string; nhan: string; co: boolean; tu: string; den: string; dt_ck: number | null; tang: number | null };
type Kpi = {
  khoang: KhoangMayChu | null;
  ngan_sach_chi_theo_thang: boolean;
  doanh_thu: { gia_tri: number; tu_ngay: string | null; den_ngay: string | null; cung_ky: number | null; tang: number | null; spark: number[];
    spark_ss: (number | null)[]; so_sanh: SoSanhKpi[] };
  ngan_sach: null | { tien_do: number | null; thuc_te: number; muc_tieu: number | null; muc_tieu_den_hom_nay: number | null; moc: number | null; spark: number[]; thang: string };
  kho: { het_hang: number; can_han: number; qua_han: number };
  khach: { can_goi: number; roi_bo: number };
};

/** Một ô của khối Chỉ số: nhãn · số lớn · (con: dòng kỳ so, đường nhỏ). Chi tiết trong ô nổi. */
function OKpi({ href, nhan, gia, lop, chi_tiet, chua, children }: {
  href?: string; nhan: string; gia: React.ReactNode; lop?: string; chi_tiet?: React.ReactNode; chua?: boolean; children?: React.ReactNode }) {
  return (
    <ONoi href={href} className={"o-kpi" + (chua ? " chua" : "")} noi_dung={<><strong>{nhan}</strong>{chi_tiet}</>}>
      <div className="nhan">{nhan}</div><div className={"gia" + (lop ? " " + lop : "")}>{gia}</div>{children}
    </ONoi>);
}

export function KhoiKpi() {
  const { data: d, isLoading, error } = useKhoi<Kpi>("kpi");
  const nm = useNhanMoc();
  const ns = d?.ngan_sach;
  return (
    <Khoi tieu_de={`Chỉ số · ${d?.khoang?.nhan ?? "tháng này"}`} dang_tai={isLoading} loi={error?.message}
      cach_tinh={d?.doanh_thu.tu_ngay ? `Doanh thu ${ngay(d.doanh_thu.tu_ngay)} – ${ngay(d.doanh_thu.den_ngay)}. Kho và khách tính ${nm}.` : undefined}>
      {d && <div className="o-kpi-luoi">
        <OKpi href="/bao-cao" nhan="Doanh thu" gia={gon(d.doanh_thu.gia_tri)}
          chi_tiet={<><DongNoi nhan={d.khoang?.nhan ?? "Tháng này"} gia={yen(d.doanh_thu.gia_tri)} />
            {d.doanh_thu.so_sanh.map(s => <DongNoi key={s.ma} nhan={hoa(s.nhan)} gia={s.co ? yen(s.dt_ck) : "không có dữ liệu"} />)}</>}>
          {d.doanh_thu.so_sanh.map(s => <DongSoSanh key={s.ma} nhan={s.nhan} co={s.co} nay={d.doanh_thu.gia_tri} ss={s.dt_ck} />)}
          <Spark gia_tri={d.doanh_thu.spark} so_sanh={d.doanh_thu.spark_ss} mau={(d.doanh_thu.tang ?? 0) >= 0 ? LUC.ok : LUC.do} />
        </OKpi>
        {d.ngan_sach_chi_theo_thang
          ? <OKpi chua nhan="Ngân sách" gia="chỉ theo tháng" chi_tiet={<div className="o-noi-chu">{NS_THEO_THANG}</div>} />
          : ns ? <OKpi href={KD.hien_ngan_sach ? "/ngan-sach" : "/bao-cao"} nhan={`Ngân sách ${thang_nhan(ns.thang)}`}
              gia={<span style={{ color: mauTienDo(ns.tien_do, ns.moc) }}>{pc(ns.tien_do)}</span>}
              chi_tiet={<><DongNoi nhan="Mốc hôm nay" gia={pc(ns.moc)} />
                <DongNoi nhan={ns.muc_tieu_den_hom_nay != null && ns.thuc_te < ns.muc_tieu_den_hom_nay ? "Thiếu so mốc" : "Vượt mốc"}
                  gia={ns.muc_tieu_den_hom_nay != null ? yen(Math.abs(ns.muc_tieu_den_hom_nay - ns.thuc_te)) : "—"} />
                <DongNoi nhan="Đã bán" gia={yen(ns.thuc_te)} /><DongNoi nhan="Ngân sách" gia={yen(ns.muc_tieu)} /></>}>
              <Spark gia_tri={ns.spark} mau={mauTienDo(ns.tien_do, ns.moc)} />
            </OKpi>
          : <OKpi href={KD.hien_ngan_sach ? "/ngan-sach" : undefined} chua nhan="Ngân sách" gia="chưa đặt"
              chi_tiet={<div className="o-noi-chu">Chưa đặt chỉ tiêu tháng này — đặt ở màn Ngân sách.</div>} />}
        {TN.cong_no && <OKpiCongNo />}
        {/* Ô chưa làm — ẩn theo công tắc kome/man_chua_co.py::HIEN (2026-09-28). */}
        {KD.hien_chua_co && <OKpi chua nhan="Phải trả 7 ngày" gia="chưa có" chi_tiet={<div className="o-noi-chu">{KD.chua_co.dong_tien ?? "Cần sổ phải trả."}</div>} />}
        <OKpi href="/kho-hang" nhan="Kho cần xử lý" gia={so(d.kho.het_hang + d.kho.can_han + d.kho.qua_han)}
          lop={d.kho.het_hang + d.kho.qua_han ? "giam" : undefined}
          chi_tiet={<><DongNoi mau={LUC.do} nhan="Mã hết hàng" gia={so(d.kho.het_hang)} />
            <DongNoi mau={LUC.canh} nhan="Lô cận hạn" gia={so(d.kho.can_han)} />
            <DongNoi mau={LUC.do} nhan="Lô quá hạn" gia={so(d.kho.qua_han)} />
            <em>tính {nm}</em></>} />
        <OKpi href="/lien-he?tat_ca=1" nhan="Khách cần gọi" gia={so(d.khach.can_goi + d.khach.roi_bo)}
          chi_tiet={<><DongNoi mau={LUC.canh} nhan="Im lặng quá nhịp" gia={so(d.khach.can_goi)} />
            <DongNoi mau={LUC.do} nhan="Đã rời bỏ" gia={so(d.khach.roi_bo)} /><em>tính {nm}</em></>} />
      </div>}
    </Khoi>
  );
}

// ---- Tuổi nợ phải thu (đợt 6 — sổ 請求先元帳, mart.cong_no_*) ------------------
type CongNo = null | {
  moc: string; cach_tinh: string; lau_nhat: { ma: string; ten: string; tien: number }[];
  tq: { tong_phai_thu: number; qua_han: number; so_phieu_qua_han: number; so_ben_qua_han: number;
        tuoi: { nhom: string; nhan: string; tien: number; dem: number }[] };
};
const MAU_TUOI: Record<string, string> = { d30: LUC.ok, d60: LUC.canh, d90: LUC.canh, d90p: LUC.do, truoc_ky: LUC.do };

/** Ô "Phải thu quá hạn" của khối Chỉ số — đọc chung ảnh chụp của khối Tuổi nợ. */
function OKpiCongNo() {
  const { data: d, isLoading } = useKhoi<CongNo>("cong_no");
  if (isLoading) return <OKpi nhan="Phải thu quá hạn" gia="…" chua />;
  if (!d) return <OKpi chua nhan="Phải thu quá hạn" gia="chưa có" chi_tiet={<div className="o-noi-chu">Chưa nạp sổ 請求先元帳 nào.</div>} />;
  return (
    <OKpi href="/cong-no?tab=qua_han" nhan="Phải thu quá hạn" gia={gon(d.tq.qua_han)} lop={d.tq.qua_han ? "giam" : undefined}
      chi_tiet={<><DongNoi nhan="Phiếu quá hạn" gia={so(d.tq.so_phieu_qua_han)} />
        <DongNoi nhan="Tổng phải thu" gia={yen(d.tq.tong_phai_thu)} /><em>đến {ngay(d.moc)}</em></>} />);
}

export function KhoiCongNo(p: XemP) {
  const { data: d, isLoading, error } = useKhoi<CongNo>("cong_no");
  const cx = useCachXem("cong_no", p);
  if (!isLoading && !error && !d) return <ChuaCoDuLieu gon tieu_de="Tuổi nợ phải thu" ly_do="Chưa nạp sổ 請求先元帳 nào — xuất từ OBC rồi nạp ở màn Kho dữ liệu." />;
  return (
    <Khoi tieu_de="Tuổi nợ phải thu" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/cong-no" }} cach_xem={cx}
      phu={d ? `đến ${ngay_ngan(d.moc)}` : undefined} cach_tinh={d?.cach_tinh}>
      {d && <>
        <SoLon href="/cong-no?tab=qua_han" gia={gon(d.tq.qua_han)} lop={d.tq.qua_han ? "giam" : undefined} nhan="quá hạn"
          chi_tiet={<><DongNoi nhan="Tổng phải thu" gia={yen(d.tq.tong_phai_thu)} />
            <DongNoi nhan="Phiếu quá hạn" gia={so(d.tq.so_phieu_qua_han)} />
            <DongNoi nhan="Bên nhận hoá đơn quá hạn" gia={so(d.tq.so_ben_qua_han)} />
            {d.lau_nhat.length > 0 && <em>Nợ lâu / quá hạn nhiều nhất:</em>}
            {d.lau_nhat.map(x => <DongNoi key={x.ma} nhan={<span className="ten-jp">{x.ten}</span>} gia={yen(x.tien)} />)}</>} />
        {cx.chon === "lau_nhat"
          ? (d.lau_nhat.length
            ? <ThanhNgang dong={d.lau_nhat.map((x): DongThanh => ({ khoa: x.ma, ten: x.ten, ten_jp: true, gia_tri: x.tien, chu: gon(x.tien),
                mau: LUC.do, chi_tiet: <DongNoi nhan="Còn nợ" gia={yen(x.tien)} /> }))} />
            : <div className="trong">Không bên nào nợ quá hạn.</div>)
          : <ThanhChong dinh_dang={gon} don_vi="Còn nợ"
              khuc={d.tq.tuoi.map(t => ({ khoa: t.nhom, nhan: t.nhan, dem: t.tien, mau: MAU_TUOI[t.nhom] ?? LUC.nhat,
                href: `/cong-no?nhom=${t.nhom}`, chi_tiet: <DongNoi nhan="Số phiếu" gia={so(t.dem)} /> }))} />}
      </>}
    </Khoi>
  );
}

// ---- Tiến độ ngân sách tháng ------------------------------------------------
type NguoiNS = { ma: string; ten: string | null; thuc_te: number; muc_tieu: number | null; muc_tieu_den_hom_nay: number | null; tien_do: number | null;
  muc_tieu_lg: number | null; thuc_te_lg: number; tien_do_lg: number | null; dt_ss: number | null };
type NganSach = {
  chi_theo_thang?: boolean;
  thang: string; co_ngan_sach: boolean; thuc_te: number; muc_tieu: number | null; muc_tieu_den_hom_nay: number | null;
  tien_do: number | null; moc: number | null; ngay_kd: number; ngay_kd_da_qua: number; ngay_kd_con_lai: number;
  can_ban_moi_ngay: number | null; nhip_chuan: number | null; nguoi: NguoiNS[];
  // 041: lãi gộp của CÔNG TY — ngân sách công ty nhập thẳng, không cộng từ từng người.
  co_ngan_sach_lg: boolean; thuc_te_lg: number; muc_tieu_lg: number | null; muc_tieu_lg_den_hom_nay: number | null;
  tien_do_lg: number | null; moc_lg: number | null;
  duong?: DuongNS;
  so_sanh?: SsKhoi;
};
type DiemNS = { nhan: string; tt: number | null; ns: number | null; ss: number | null;
  tt_lg: number | null; ns_lg: number | null; ss_lg: number | null };
type DuongNS = { kieu: "ngay" | "thang"; nhan_ss: string | null; den?: string; diem: DiemNS[] };

/** Đường luỹ kế của khối ngân sách: thực tế cộng dồn · nhịp ngân sách · tháng trước. */
function DuongNganSach({ duong, cs }: { duong: DuongNS; cs: "dt" | "lg" }) {
  const ds = duong.diem;
  if (!ds.length) return null;
  const lg = cs === "lg";
  const tt = (x: DiemNS) => lg ? x.tt_lg : x.tt, ns = (x: DiemNS) => lg ? x.ns_lg : x.ns, ss = (x: DiemNS) => lg ? x.ss_lg : x.ss;
  const theoNgay = duong.kieu === "ngay";
  const coNS = ds.some(x => ns(x) != null);
  const coSS = ds.some(x => ss(x) != null);
  const iDen = theoNgay && duong.den ? ds.findIndex(x => x.nhan === duong.den) : -1;
  const ten = lg ? "Lãi gộp" : "Doanh thu";
  // Nét đứt dành riêng cho KỲ SO (đặc tả 2026-09-28) — nhịp ngân sách là nét liền mảnh.
  const chuoi: Chuoi[] = [
    { ten: `${ten} thực tế (luỹ kế)`, kieu: "duong", gia_tri: ds.map(tt), mau: "var(--lien-ket)", so_voi: coSS ? 1 + (coNS ? 1 : 0) : undefined },
    ...(coNS ? [{ ten: theoNgay ? "Nhịp ngân sách" : "Ngân sách (luỹ kế)", kieu: "duong" as const, gia_tri: ds.map(ns), mau: LUC.ok }] : []),
    ...(coSS ? [{ ten: `${hoa(duong.nhan_ss)} (luỹ kế)`, kieu: "duong_dut" as const, gia_tri: ds.map(ss), mau: MAU_SS }] : []),
  ];
  return (
    <div className="ns-duong">
      <BieuDo key={cs} nhan={ds.map(x => theoNgay ? ngay_ngan(x.nhan) : thang_nhan(x.nhan))}
        nhan_day_du={ds.map(x => theoNgay ? ngay(x.nhan) : thang_nhan(x.nhan))}
        cao={180} mo_ta={`${ten} luỹ kế so với nhịp ngân sách`} chuoi={chuoi}
        vach={iDen >= 0 && iDen < ds.length - 1 ? { i: iDen, chu: "mốc" } : null}
        dinh_dang={v => yen(v)} dinh_dang_truc={v => gon(v)} />
      {!coSS && duong.nhan_ss && <div className="khoi-canh">{hoa(duong.nhan_ss)}: không vẽ được đường luỹ kế để so (không có dữ liệu, hoặc kỳ so không cùng gốc tháng).</div>}
    </div>
  );
}

export function KhoiNganSach(p: XemP) {
  const { data: d, isLoading, error } = useKhoi<NganSach | null>("ns_thang");
  const cx = useCachXem("ns_thang", p);
  if (d?.chi_theo_thang) return <ChuaCoDuLieu gon tieu_de="Tiến độ ngân sách" ly_do={NS_THEO_THANG} />;
  const nguoi = [...(d?.nguoi ?? [])].sort((a, b) => b.thuc_te - a.thuc_te);
  const maxNS = Math.max(1, ...nguoi.map(n => Math.max(n.muc_tieu ?? 0, n.thuc_te, n.dt_ss ?? 0)));
  const ssN = d?.so_sanh;
  const vuot = !!d && d.muc_tieu_den_hom_nay != null && d.thuc_te >= d.muc_tieu_den_hom_nay;
  return (
    <Khoi tieu_de={`Ngân sách ${d ? thang_nhan(d.thang) : ""}`} dang_tai={isLoading} loi={error?.message} cach_xem={d?.duong ? cx : undefined}
      nhan={d ? `Còn ${d.ngay_kd_con_lai} ngày làm việc` : undefined} lien_ket={{ href: "/bao-cao", chu: "Xem chi tiết" }}
      phu={ssN?.co ? <>so {ssN.nhan}</> : undefined}
      cach_tinh={d ? <>{d.co_ngan_sach ? `Vạch đen = mốc đáng lẽ đạt tới hôm nay (${pc(d.moc)}) — tính theo ngày làm việc, trừ ngày lễ.` : "Thanh = doanh thu thực tế của từng người phụ trách."}
        {ssN?.co ? ` Vạch đứt = doanh thu ${ssN.nhan}.` : ""}</> : undefined}
      canh_bao={canhBaoNhieu([
        d && !d.co_ngan_sach ? <>Chưa đặt chỉ tiêu tháng này.{KD.hien_ngan_sach && <> <a href="/ngan-sach">Đặt chỉ tiêu →</a></>}</> : null,
        ssN && !ssN.co ? `${hoa(ssN.nhan)}: không có dữ liệu để so.` : null,
      ])}>
      {d && <div className="ns-luoi">
        <div className="ns-so">
          {d.co_ngan_sach
            ? <SoLon gia={pc(d.tien_do)} mau={mauTienDo(d.tien_do, d.moc)} nhan="tiến độ công ty"
                chi_tiet={<><DongNoi nhan="Mốc hôm nay" gia={pc(d.moc)} />
                  <DongNoi nhan={vuot ? "Vượt mốc" : "Thiếu so mốc"} gia={yen(Math.abs((d.muc_tieu_den_hom_nay ?? 0) - d.thuc_te))} />
                  <DongNoi nhan="Ngân sách" gia={yen(d.muc_tieu)} />
                  <DongNoi nhan="Cần bán mỗi ngày" gia={yen(d.can_ban_moi_ngay)} />
                  {d.can_ban_moi_ngay != null && d.nhip_chuan
                    ? <DongNoi nhan="So nhịp chuẩn" gia={`${(d.can_ban_moi_ngay / d.nhip_chuan).toFixed(2).replace(".", ",")}×`} />
                    : <em>tháng đã hết ngày làm việc</em>}</>} />
            : <SoLon gia={gon(d.thuc_te)} nhan="đã bán tháng này"
                chi_tiet={<><DongNoi nhan="Đã bán" gia={yen(d.thuc_te)} />
                  <DongNoi nhan="Ngày làm việc" gia={`${d.ngay_kd_da_qua}/${d.ngay_kd}`} /></>} />}
        </div>
        <div className="ns-thanh">
          {/* Ngân sách CHUNG của công ty đứng trước (doanh thu + lãi gộp, nhập thẳng — 041), rồi mới tới từng người. */}
          <div className="ns-cong-ty">
            {([["Doanh thu", d.thuc_te, d.muc_tieu, d.tien_do, d.moc, d.co_ngan_sach],
               ["Lãi gộp", d.thuc_te_lg, d.muc_tieu_lg, d.tien_do_lg, d.moc_lg, d.co_ngan_sach_lg]] as const).map(([ten, tt, mt, td, moc, co]) => (
              <ONoi key={ten} className="ns-khoi-dong" noi_dung={<><strong>{ten} · toàn công ty</strong>
                <DongNoi nhan="Thực tế" gia={yen(tt)} /><DongNoi nhan="Ngân sách" gia={co ? yen(mt) : "chưa đặt"} />
                {co && <DongNoi nhan="Mốc hôm nay" gia={pc(moc)} />}</>}>
                <div className="ns-dong"><span>{ten}</span>
                  {co ? <b style={{ color: mauTienDo(td, moc) }}>{pc(td)}</b> : <em className="nhat-chu">chưa đặt</em>}</div>
                {co && <ThanhMoc ty_le={td} moc={moc} mau={mauTienDo(td, moc)} />}
              </ONoi>))}
          </div>
          {nguoi.map(n => (
            <ONoi key={n.ma} className="ns-khoi-dong" noi_dung={<><strong>{tenNguoi(n.ten, n.ma)}</strong>
              <DongNoi nhan="Doanh thu" gia={yen(n.thuc_te)} />
              <DongNoi nhan="Chỉ tiêu" gia={n.muc_tieu ? yen(n.muc_tieu) : "chưa có"} />
              {n.muc_tieu_den_hom_nay != null && <DongNoi nhan="Mốc hôm nay" gia={yen(n.muc_tieu_den_hom_nay)} />}
              {n.muc_tieu_lg != null && <DongNoi nhan="Lãi gộp" gia={pc(n.tien_do_lg)} />}
              {ssN?.co && <DongNoi nhan={hoa(ssN.nhan)} gia={yen(n.dt_ss)} />}</>}>
              <div className="ns-dong"><span>{tenNguoi(n.ten, n.ma)}</span>
                {ssN && <TdSs nay={n.thuc_te} ss={n.dt_ss} nhan={ssN.nhan} />}
                <b style={{ color: mauTienDo(n.tien_do, d.moc) }}>{n.muc_tieu ? pc(n.tien_do) : gon(n.thuc_te)}</b></div>
              <div className="ns-ba-lop">
                <div className="lop-ns" style={{ width: `${(n.muc_tieu ?? 0) / maxNS * 100}%` }} />
                <div className="lop-tt" style={{ width: `${Math.min(n.thuc_te / maxNS, 1) * 100}%`, background: n.muc_tieu ? mauTienDo(n.tien_do, d.moc) : LUC.nhat }} />
                {n.muc_tieu_den_hom_nay != null && <div className="lop-moc" style={{ left: `${n.muc_tieu_den_hom_nay / maxNS * 100}%` }} />}
                {ssN && <VachSoSanh ty_le={n.dt_ss != null ? n.dt_ss / maxNS : null} nhan={`${hoa(ssN.nhan)}: ${yen(n.dt_ss)}`} />}
              </div>
            </ONoi>))}
        </div>
      </div>}
      {d?.duong && <DuongNganSach duong={d.duong} cs={cx.chon === "lai_gop" ? "lg" : "dt"} />}
    </Khoi>
  );
}

// ---- Doanh thu theo sale ----------------------------------------------------
export function KhoiSale(p: XemP) {
  const { data: d, isLoading, error } = useKhoi<NganSach | null>("so_sanh_sale");
  const cx = useCachXem("so_sanh_sale", p);
  if (d?.chi_theo_thang) return <ChuaCoDuLieu gon tieu_de="Theo sale" ly_do={NS_THEO_THANG} />;
  const nguoi = [...(d?.nguoi ?? [])].sort((a, b) => b.thuc_te - a.thuc_te);
  const max = Math.max(1, ...nguoi.map(n => Math.max(n.thuc_te, n.dt_ss ?? 0)));
  const maxLg = Math.max(1, ...nguoi.map(n => n.thuc_te_lg));
  const ssN = d?.so_sanh;
  const xem = cx.chon;
  const coSs = xem !== "lai_gop" && !!ssN?.co;
  const thang = d ? thang_nhan(d.thang).slice(1) : "";
  const noi = (n: NguoiNS) => <><DongNoi nhan="Doanh thu" gia={yen(n.thuc_te)} />
    <DongNoi nhan="Chỉ tiêu" gia={n.muc_tieu ? yen(n.muc_tieu) : "chưa có"} />
    <DongNoi nhan="Lãi gộp" gia={yen(n.thuc_te_lg)} />
    {n.muc_tieu_lg != null && <DongNoi nhan="Chỉ tiêu lãi gộp" gia={yen(n.muc_tieu_lg)} />}
    {ssN?.co && <DongNoi nhan={hoa(ssN.nhan)} gia={yen(n.dt_ss)} />}</>;
  const dong = (n: NguoiNS): DongThanh => xem === "doanh_thu"
    ? { khoa: n.ma, ten: tenNguoi(n.ten, n.ma), gia_tri: n.thuc_te, ss: coSs ? n.dt_ss : null, chu: gon(n.thuc_te),
        phu: ssN ? <TdSs nay={n.thuc_te} ss={n.dt_ss} nhan={ssN.nhan} /> : undefined, mau: LUC.canh, chi_tiet: noi(n) }
    : xem === "lai_gop"
    ? { khoa: n.ma, ten: tenNguoi(n.ten, n.ma), gia_tri: n.muc_tieu_lg ? (n.tien_do_lg ?? 0) : n.thuc_te_lg / maxLg,
        chu: n.muc_tieu_lg ? pc(n.tien_do_lg) : gon(n.thuc_te_lg),
        mau: n.muc_tieu_lg ? mauTienDo(n.tien_do_lg, d?.moc_lg ?? d?.moc) : LUC.ok, chi_tiet: noi(n) }
    : { khoa: n.ma, ten: tenNguoi(n.ten, n.ma),
        gia_tri: n.muc_tieu ? (n.tien_do ?? 0) : n.thuc_te / max,
        ss: coSs && n.dt_ss != null ? (n.muc_tieu ? n.dt_ss / n.muc_tieu : n.dt_ss / max) : null,
        chu: n.muc_tieu ? pc(n.tien_do) : gon(n.thuc_te),
        phu: ssN ? <TdSs nay={n.thuc_te} ss={n.dt_ss} nhan={ssN.nhan} /> : undefined,
        mau: n.muc_tieu ? mauTienDo(n.tien_do, d?.moc) : LUC.canh, chi_tiet: noi(n) };
  const cach = !d ? undefined
    : xem === "doanh_thu" ? `Doanh thu tháng ${thang} của từng người phụ trách.${coSs ? ` Vạch đứt = ${ssN!.nhan}.` : ""}`
    : xem === "lai_gop" ? `% = lãi gộp so chỉ tiêu lãi gộp cá nhân tháng ${thang}; người chưa có chỉ tiêu lãi gộp: thanh = lãi gộp thực tế.`
    : `${d.co_ngan_sach ? `% = tiến độ so ngân sách cá nhân tháng ${thang}` : `Doanh thu tháng ${thang} — chưa đặt chỉ tiêu nên chưa có %`}.${coSs ? ` Vạch đứt = ${ssN!.nhan}.` : ""}`;
  return (
    <Khoi tieu_de="Theo sale" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }} cach_xem={cx}
      phu={coSs ? <>so {ssN!.nhan}</> : undefined} cach_tinh={cach}
      canh_bao={xem === "lai_gop" ? CHI_DT(ssN) : ssN && !ssN.co ? `${hoa(ssN.nhan)}: không có dữ liệu để so.` : undefined}>
      {d && <ThanhNgang thang={xem === "doanh_thu" ? undefined : 1} nhan_ss={coSs ? hoa(ssN!.nhan) : undefined} dong={nguoi.map(dong)} />}
    </Khoi>
  );
}

// ---- Kết quả theo từng tháng ------------------------------------------------
type Thang = { thang: string; thang_trong_ky: number; doanh_thu: number; lai_gop: number; ty_suat: number | null; so_khach: number;
  cung_ky: number | null; co_cung_ky: boolean; ngan_sach: number | null; ngan_sach_lg: number | null; cung_ky_lg: number | null;
  khach_moi: number; khach_moi_da_mua: number; khach_moi_ss: number | null };
/** Chỉ số đang vẽ của khối theo tháng: giá trị · kỳ so · ngân sách (nếu có) của một tháng. */
type ChiSoThang = { ten: string; gt: (x: Thang) => number; ss: (x: Thang) => number | null; ns: (x: Thang) => number | null;
  mau: string; mo: string; tien: boolean };
const CS_THANG: Record<"doanh_thu" | "lai_gop" | "khach_moi", ChiSoThang> = {
  doanh_thu: { ten: "Doanh thu", gt: x => x.doanh_thu, ss: x => x.cung_ky, ns: x => x.ngan_sach, mau: LUC.do, mo: MO, tien: true },
  lai_gop: { ten: "Lãi gộp", gt: x => x.lai_gop, ss: x => x.cung_ky_lg, ns: x => x.ngan_sach_lg, mau: LUC.ok,
    mo: "color-mix(in srgb, var(--ok-vien) 35%, var(--nen-the))", tien: true },
  khach_moi: { ten: "Khách mới", gt: x => x.khach_moi, ss: x => x.khach_moi_ss, ns: () => null, mau: "var(--lien-ket)", mo: MO, tien: false },
};

export function KhoiTheoThang(p: XemP) {
  const cx = useCachXem("theo_thang", p);
  const { data: d, isLoading, error } = useKhoi<{ company_fy: number | null; thang: Thang[]; hom_nay: string | null; khoang: KhoangMayChu | null;
    so_sanh: SsKhoi; cat_cung_ngay: boolean; khach_moi_cach_tinh: string }>("theo_thang");
  const t = d?.thang ?? [];
  const thangNay = d?.hom_nay?.slice(0, 7);
  const kx = d?.khoang;
  const ss = d?.so_sanh;
  const xem = cx.chon;
  // Luỹ kế là luỹ kế DOANH THU; ba cách còn lại mỗi cách một chỉ số.
  const cs = CS_THANG[xem === "lai_gop" ? "lai_gop" : xem === "khach_moi" ? "khach_moi" : "doanh_thu"];
  const dd = (v: number | null | undefined) => (cs.tien ? yen(v) : so(v));
  const tong = t.reduce((s, x) => s + cs.gt(x), 0);
  // Tháng đang chạy chỉ so ngang được khi máy chủ đã cắt kỳ so cùng dải ngày.
  const coCK = t.filter(x => cs.ss(x) != null && (x.thang !== thangNay || d?.cat_cung_ngay));
  const nayCK = coCK.reduce((s, x) => s + cs.gt(x), 0), ck = coCK.reduce((s, x) => s + (cs.ss(x) ?? 0), 0);
  const coNS = t.filter(x => cs.ns(x) != null && x.thang !== thangNay);
  const dat = coNS.filter(x => cs.gt(x) >= (cs.ns(x) ?? 0)).length;
  const cao = t.length ? t.reduce((a, b) => (cs.gt(b) > cs.gt(a) ? b : a)) : null;
  const tongDt = t.reduce((s, x) => s + x.doanh_thu, 0), tongLg = t.reduce((s, x) => s + x.lai_gop, 0);
  const daMua = t.reduce((s, x) => s + x.khach_moi_da_mua, 0);
  const nsL = luyKe(t.map(x => x.ngan_sach)), ckL = luyKe(t.map(x => x.cung_ky));
  const coNsL = nsL.some(v => v != null), coCkL = ckL.some(v => v != null);
  const coNsCs = t.some(x => cs.ns(x) != null);
  const chuoi: Chuoi[] = xem === "luy_ke" ? [
    { ten: "Doanh thu (luỹ kế)", kieu: "duong", gia_tri: luyKe(t.map(x => x.doanh_thu)), mau: LUC.do,
      so_voi: coCkL ? 1 + (coNsL ? 1 : 0) : undefined },
    ...(coNsL ? [{ ten: "Ngân sách (luỹ kế)", kieu: "duong" as const, gia_tri: nsL, mau: "var(--lien-ket)" }] : []),
    ...(coCkL ? [{ ten: `${hoa(ss?.nhan) || "Kỳ so"} (luỹ kế)`, kieu: "duong_dut" as const, gia_tri: ckL, mau: MAU_SS }] : []),
  ] : [
    { ten: hoa(ss?.nhan) || "Kỳ so", kieu: "cot_ma", gia_tri: t.map(x => cs.ss(x)), mau: MAU_SS },
    { ten: cs.ten, kieu: "cot", gia_tri: t.map(x => cs.gt(x)), mau: cs.mau, so_voi: 0,
      mau_tung_cot: t.map(x => { const n = cs.ns(x);
        return !trongKhoang(kx, x.thang) ? cs.mo : n == null ? (cs.tien ? "var(--lien-ket)" : cs.mau)
          : cs.gt(x) >= n ? cs.mau : `color-mix(in srgb, ${cs.mau} 50%, var(--nen-the))`; }) },
    ...(coNsCs ? [{ ten: xem === "lai_gop" ? "Ngân sách lãi gộp" : "Ngân sách tháng", kieu: "duong" as const,
      gia_tri: t.map(x => cs.ns(x)), mau: "var(--lien-ket)" }] : []),
  ];
  const ky = `Cả kỳ chứa ${kx?.nhan ?? "khoảng xem"} (kỳ kết thúc 7/${d?.company_fy})`;
  return (
    <Khoi tieu_de="Theo từng tháng" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao", chu: "Báo cáo" }}
      phu={ss ? <>so {ss.nhan}</> : undefined} cach_xem={cx}
      cach_tinh={!d?.company_fy ? undefined
        : xem === "luy_ke" ? `${ky}, cộng dồn từ đầu kỳ: doanh thu · ngân sách (dừng ở tháng đầu tiên chưa đặt) · nét đứt = ${ss?.nhan ?? "kỳ so"} (dừng ở tháng đầu tiên không có số).`
        : xem === "khach_moi" ? `${ky}. Cột = số khách ĐĂNG KÝ trong tháng (đậm = thuộc khoảng xem); cột viền đứt = ${ss?.nhan ?? "kỳ so"}. ${d.khach_moi_cach_tinh}`
        : xem === "lai_gop" ? `${ky}. Cột = lãi gộp (粗利益) từng tháng, đậm = thuộc khoảng xem; cột viền đứt = ${ss?.nhan ?? "kỳ so"}; đường = ngân sách lãi gộp của công ty. Biên gộp = lãi gộp ÷ doanh thu thuần.`
        : `${ky}. Cột đậm = thuộc khoảng xem; cột viền đứt = ${ss?.nhan ?? "kỳ so"}; đường = ngân sách tháng.`}
      canh_bao={!d ? undefined : canhBaoNhieu([
        ss && ss.co && ss.lech_thang == null ? "Kỳ so không lệch tròn tháng — không so theo tháng được." : null,
        ss && ss.co && ss.lech_thang != null && !coCK.length ? `${hoa(ss.nhan)}: không có dữ liệu để so.` : null,
        ss && !ss.co ? `${hoa(ss.nhan)}: không có dữ liệu để so.` : null,
        thangNay && t.some(x => x.thang === thangNay)
          ? (d.cat_cung_ngay ? `Tháng đang chạy chưa đủ ngày${coNsCs ? " — %NS chưa so ngang được" : ""}; cột ma của tháng này đã cắt cùng dải ngày ở ${ss?.nhan}.`
            : `Tháng đang chạy chưa đủ ngày — ${coNsCs ? "%NS và " : ""}phép so của tháng này chưa so ngang được.`)
          : null,
      ])}>
      {d && <>
        <HangSo>
          <MucSo nhan={xem === "khach_moi" ? "Cả kỳ" : "Luỹ kế"} gia={xem === "khach_moi" ? so(tong) : gon(tong)}
            chi_tiet={<DongNoi nhan="Tháng có dữ liệu"
            gia={t.length ? `${t.length} (${thang_nhan(t[0].thang)} – ${thang_nhan(t[t.length - 1].thang)})` : "0"} />} />
          <MucSo nhan={<>so {ss?.nhan ?? "kỳ so"}</>} gia={ck ? thay_doi(nayCK / ck - 1) : "—"} lop={ck ? (nayCK >= ck ? "tang" : "giam") : undefined}
            chi_tiet={ck ? <><DongNoi nhan="Tháng đối chiếu" gia={so(coCK.length)} />
              <DongNoi nhan="Chênh" gia={cs.tien ? gon(nayCK - ck) : so(nayCK - ck)} /></> : undefined} />
          {xem === "lai_gop" && <MucSo nhan="Biên cả kỳ" gia={tongDt ? pc(tongLg / tongDt) : "—"}
            chi_tiet={<><DongNoi nhan="Lãi gộp" gia={yen(tongLg)} /><DongNoi nhan="Doanh thu" gia={yen(tongDt)} /></>} />}
          {xem === "khach_moi"
            ? <MucSo nhan="Đã có đơn" gia={tong ? `${daMua}/${tong}` : "—"}
                chi_tiet={<div className="o-noi-chu">Khách đăng ký trong kỳ đã có phiếu bán tính đến ngày cuối khoảng.</div>} />
            : <MucSo nhan="Đạt ngân sách" gia={coNS.length ? `${dat}/${coNS.length}` : "—"}
                chi_tiet={<div className="o-noi-chu">{coNS.length ? `Số tháng đã khép lại đạt ngân sách${xem === "lai_gop" ? " lãi gộp" : ""}.`
                  : `Chưa đặt chỉ tiêu ${xem === "lai_gop" ? "lãi gộp " : ""}tháng nào.`}</div>} />}
          <MucSo nhan="Cao nhất" gia={cao ? thang_nhan(cao.thang) : "—"}
            chi_tiet={cao ? <><DongNoi nhan={cs.ten} gia={dd(cs.gt(cao))} /><DongNoi nhan="Biên gộp" gia={pc(cao.ty_suat)} /></> : undefined} />
        </HangSo>
        <BieuDo key={xem} nhan={t.map(x => thang_nhan(x.thang))} chuoi={chuoi} cao={200}
          mo_ta={xem === "luy_ke" ? `Doanh thu luỹ kế của kỳ so ngân sách và ${ss?.nhan ?? "kỳ so"}` : `${cs.ten} từng tháng của kỳ so ${coNsCs ? "ngân sách và " : ""}${ss?.nhan ?? "kỳ so"}`}
          dinh_dang={v => (xem === "khach_moi" ? so(v) : yen(v))} dinh_dang_truc={v => (xem === "khach_moi" ? so(v) : gon(v))}
          vach={thangNay ? { i: t.findIndex(x => x.thang === thangNay), chu: "đang chạy" } : null}
          them_noi={i => { const x = t[i]; return x && (xem === "khach_moi" ? <>
            <div>Đã có đơn<b>{so(x.khach_moi_da_mua)}</b></div>
            <div>Doanh thu<b>{gon(x.doanh_thu)}</b></div></> : <>
            <div>%NS<b>{cs.ns(x) ? pc(cs.gt(x) / cs.ns(x)!, 0) : "—"}</b></div>
            <div>{xem === "lai_gop" ? "Doanh thu" : "Lãi gộp"}<b>{gon(xem === "lai_gop" ? x.doanh_thu : x.lai_gop)}</b></div>
            <div>Biên gộp<b>{pc(x.ty_suat)}</b></div>
            <div>Khách mua<b>{so(x.so_khach)}</b></div>
            <div>Khách mới<b>{so(x.khach_moi)}</b></div></>); }} />
      </>}
    </Khoi>
  );
}

// ---- Xu hướng doanh thu (theo khoảng xem) ---------------------------------
type XuHuong = { khoang: KhoangMayChu | null; kieu: "ngay" | "thang"; diem: [string, number, number, number, number | null][] };

export function KhoiXuHuong(p: XemP) {
  const { data: d, isLoading, error } = useKhoi<XuHuong>("xu_huong");
  const cx = useCachXem("xu_huong", p);
  const ds = d?.diem ?? [];
  const kx = d?.khoang;
  const ss = kx?.so_sanh[0];
  const tong = ds.reduce((s, x) => s + x[1], 0);
  const tongLg = ds.reduce((s, x) => s + x[2], 0);
  const coCk = ds.some(x => x[4] != null);
  const tongCk = ds.reduce((s, x) => s + (x[4] ?? 0), 0);
  const coNgay = ds.filter(x => x[1] !== 0).length;
  const theoNgay = d?.kieu !== "thang";
  const don = theoNgay ? "ngày" : "tháng";
  const xem = cx.chon;
  const coSsVe = xem === "doanh_thu" || xem === "luy_ke";
  const cot = ds.length <= 40;
  const chuoi: Chuoi[] = xem === "luy_ke" ? [
    { ten: "Doanh thu (luỹ kế)", kieu: "duong", gia_tri: luyKe(ds.map(x => x[1])), mau: "var(--lien-ket)", so_voi: coCk ? 1 : undefined },
    ...(coCk ? [{ ten: `${hoa(ss?.nhan) || "Kỳ so"} (luỹ kế)`, kieu: "duong_dut" as const, gia_tri: luyKe(ds.map(x => x[4])), mau: MAU_SS }] : []),
  ] : xem === "lai_gop" ? [
    { ten: `Lãi gộp ${don}`, kieu: cot ? "cot" : "duong", gia_tri: ds.map(x => x[2]), mau: LUC.ok },
  ] : xem === "so_khach" ? [
    { ten: `Số khách mua trong ${don}`, kieu: cot ? "cot" : "duong", gia_tri: ds.map(x => x[3]), mau: "var(--lien-ket)" },
  ] : [
    { ten: theoNgay ? "Doanh thu ngày" : "Doanh thu tháng", kieu: cot ? "cot" : "duong", gia_tri: ds.map(x => x[1]), mau: "var(--lien-ket)", so_voi: 1 },
    // Cột → cột ma, đường → nét đứt (đặc tả 2026-09-28 §6).
    { ten: hoa(ss?.nhan) || "Kỳ so", kieu: cot ? "cot_ma" : "duong_dut", gia_tri: ds.map(x => x[4]), mau: MAU_SS },
  ];
  const tienTe = xem !== "so_khach";
  return (
    <Khoi tieu_de={`Xu hướng · ${kx?.nhan ?? ""}`} dang_tai={isLoading} loi={error?.message} cach_xem={cx}
      phu={ss?.co && coSsVe ? <>so {ss.nhan}</> : undefined}
      cach_tinh={xem === "so_khach" ? `Số khách có đơn trong từng ${don} — một khách mua nhiều ${don} được đếm ở mỗi ${don}, nên không cộng thành tổng.`
        : xem === "lai_gop" ? `Lãi gộp từng ${don}. Biên gộp = tổng lãi gộp ÷ tổng doanh thu thuần của khoảng.`
        : ss?.co ? `${xem === "luy_ke" ? "Cộng dồn từ đầu khoảng. Nét đứt" : cot ? "Cột viền đứt" : "Nét đứt"}: ${ss.nhan} (${ngay(ss.tu)} → ${ngay(ss.den)}).` : undefined}
      canh_bao={!coSsVe ? CHI_DT(ss) : ss && !ss.co ? `${hoa(ss.nhan)}: không có dữ liệu để so.` : ss && !coCk ? "Kỳ so khác độ dài — chỉ so tổng." : undefined}>
      {d && <>
        <HangSo>
          {xem === "so_khach" ? <>
            <MucSo nhan={`TB / ${don} có bán`} gia={so(coNgay ? Math.round(ds.reduce((s, x) => s + x[3], 0) / coNgay) : null)} />
            <MucSo nhan={`Cao nhất một ${don}`} gia={so(Math.max(0, ...ds.map(x => x[3])))} />
          </> : xem === "lai_gop" ? <>
            <MucSo nhan={`Tổng ${ds.length} ${don}`} gia={gon(tongLg)} />
            <MucSo nhan="Biên gộp" gia={tong ? pc(tongLg / tong) : "—"} />
          </> : <>
            <MucSo nhan={`Tổng ${ds.length} ${don}`} gia={gon(tong)} />
            <MucSo nhan={<>so {ss?.nhan ?? "—"}</>} gia={coCk && tongCk > 0 ? thay_doi(tong / tongCk - 1) : "—"} lop={tong >= tongCk ? "tang" : "giam"}
              chi_tiet={coCk ? <DongNoi nhan={hoa(ss?.nhan)} gia={yen(tongCk)} /> : undefined} />
            <MucSo nhan={theoNgay ? "TB / ngày có bán" : "TB / tháng"} gia={gon(theoNgay ? (coNgay ? tong / coNgay : null) : (ds.length ? tong / ds.length : null))} />
          </>}
        </HangSo>
        <BieuDo key={xem} nhan={ds.map(x => theoNgay ? ngay_ngan(x[0]) : thang_nhan(x[0]))} nhan_day_du={ds.map(x => theoNgay ? ngay(x[0]) : thang_nhan(x[0]))}
          cao={200} mo_ta={`${xem === "so_khach" ? "Số khách" : xem === "lai_gop" ? "Lãi gộp" : "Doanh thu"} ${kx?.nhan ?? ""}${coSsVe ? ` so ${ss?.nhan ?? ""}` : ""}`}
          chuoi={chuoi}
          dinh_dang={v => tienTe ? yen(v) : `${so(v)} khách`} dinh_dang_truc={v => tienTe ? gon(v) : so(v)} />
      </>}
    </Khoi>
  );
}

// ---- Sức khoẻ khách hàng ----------------------------------------------------
const MAU_TT: Record<string, string> = { binh_thuong: LUC.ok, canh_bao: LUC.canh, da_roi_bo: LUC.do, ngung_giao_dich: LUC.nhat, chua_du_lich_su: "var(--vien-dam)" };

export function KhoiSucKhoe(p: XemP) {
  const cx = useCachXem("suc_khoe_khach", p);
  const { data: d, isLoading, error } = useKhoi<{ dem: Record<string, number>; nhom: string[]; nhan: Record<string, string> }>("suc_khoe_khach");
  const nm = useNhanMoc();
  const hd = d ? (d.dem.binh_thuong ?? 0) + (d.dem.canh_bao ?? 0) : 0;
  return (
    <Khoi tieu_de="Sức khoẻ khách" phu={`tính ${nm}`} cach_xem={cx} dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}
      cach_tinh="Cần gọi lại = im lặng quá nhịp mua riêng của CHÍNH từng khách (không phải một ngưỡng chung). Bấm một khúc để mở danh sách khách đó.">
      {d && (() => {
        const khuc: Khuc[] = d.nhom.map(n => ({ khoa: n, nhan: d.nhan[n], dem: d.dem[n] ?? 0, mau: MAU_TT[n], href: `/khach-hang?loc=${n}&tat_ca=1` }));
        return cx.chon === "vong"
          ? <Vong dinh_dang={so} don_vi="Khách" khuc={khuc} giua={so(hd)} nhan_giua="đang mua" />
          : <><SoLon gia={so(hd)} nhan="khách đang mua" /><ThanhChong dinh_dang={so} don_vi="Khách" khuc={khuc} /></>;
      })()}
    </Khoi>
  );
}

// ---- Danh sách khách hàng ---------------------------------------------------
type KhachDS = { ma: string; ten: string; sale: string | null; ten_sale: string | null; doanh_thu: number; ty_le_im_lang: number | null;
  trang_thai: string; so_ngay_im_lang: number | null; nhip_ngay: number | null; thang_nay: number; thang_truoc: number | null };

const VIEC_TT: Record<string, string> = { da_roi_bo: "Gọi lại ngay", canh_bao: "Gọi lại trong tuần" };
const SO_KHACH_GON = 15;

export function KhoiDanhSachKhach(p: XemP) {
  const cx = useCachXem("danh_sach_khach", p);
  const { data: d, isLoading, error } = useKhoi<{ khach: KhachDS[]; nhan: Record<string, string>; khoang: KhoangMayChu | null;
    so_sanh: { ma: string; nhan: string; co: boolean; tu: string; den: string } | null }>("danh_sach_khach");
  const nm = useNhanMoc();
  const ss = d?.so_sanh;
  const imLang = cx.chon === "im_lang";
  const tatCa = d?.khach ?? [];
  const ds = imLang
    ? tatCa.filter(k => k.ty_le_im_lang != null).sort((a, b) => (b.ty_le_im_lang ?? 0) - (a.ty_le_im_lang ?? 0)).slice(0, SO_KHACH_GON)
    : [...tatCa].sort((a, b) => b.thang_nay - a.thang_nay).slice(0, SO_KHACH_GON);
  const coSs = !imLang && !!ss?.co;
  const heSo = (v: number) => `${v.toFixed(1).replace(".", ",")}×`;
  return (
    <Khoi tieu_de={imLang ? "Khách lớn đang im lặng" : "Khách lớn nhất"} phu={d ? <>{d.khoang?.nhan}{coSs ? <> · so {ss!.nhan}</> : null}</> : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }} cach_xem={cx}
      cach_tinh={imLang
        ? `Trong ${so(tatCa.length)} khách doanh thu cao nhất của khoảng xem: ${SO_KHACH_GON} khách im lặng lâu nhất so với nhịp mua riêng (số ngày chưa mua ÷ nhịp, tính ${nm}). Màu thanh: đỏ = gọi lại ngay, cam = gọi lại trong tuần, xanh = bình thường.`
        : `${SO_KHACH_GON} khách doanh thu cao nhất trong khoảng xem. Màu thanh: đỏ = gọi lại ngay, cam = gọi lại trong tuần, xanh = bình thường. Im lặng = số ngày chưa mua ÷ nhịp mua riêng của khách, tính ${nm}.${ss?.co ? ` Vạch đứt = ${ss.nhan}.` : ""}`}
      canh_bao={!imLang && ss && !ss.co ? `${hoa(ss.nhan)}: không có dữ liệu để so.` : undefined}>
      {d && <ThanhNgang nhan_ss={coSs ? hoa(ss!.nhan) : undefined} dong={ds.map((k): DongThanh => ({
        khoa: k.ma, ten: k.ten, ten_jp: true,
        gia_tri: imLang ? (k.ty_le_im_lang ?? 0) : k.thang_nay, ss: coSs ? k.thang_truoc : null,
        chu: imLang ? heSo(k.ty_le_im_lang ?? 0) : gon(k.thang_nay),
        phu: imLang ? undefined : <TdSs nay={k.thang_nay} ss={k.thang_truoc} nhan={ss?.nhan ?? ""} />,
        mau: MAU_TT[k.trang_thai] ?? LUC.nhat, href: `/khach-hang/${k.ma}`,
        chi_tiet: <>
          <DongNoi nhan={d.khoang?.nhan ?? "Khoảng xem"} gia={yen(k.thang_nay)} />
          {ss?.co && <DongNoi nhan={hoa(ss.nhan)} gia={k.thang_truoc != null ? yen(k.thang_truoc) : "—"} />}
          <DongNoi nhan="Doanh thu 12 tháng" gia={gon(k.doanh_thu)} />
          <DongNoi nhan="Im lặng" gia={k.ty_le_im_lang != null ? `${k.ty_le_im_lang.toFixed(1).replace(".", ",")}×${k.nhip_ngay ? ` (im ${k.so_ngay_im_lang} / nhịp ${Math.round(k.nhip_ngay)} ngày)` : ""}` : "—"} />
          <DongNoi nhan="Phụ trách" gia={tenNguoi(k.ten_sale, k.sale ?? "—")} />
          <DongNoi mau={MAU_TT[k.trang_thai]} nhan="Cần làm" gia={VIEC_TT[k.trang_thai] ?? d.nhan[k.trang_thai]} /></> }))} />}
    </Khoi>
  );
}

// ---- Sản phẩm sắp hết hạn ---------------------------------------------------
export function KhoiHanSuDung() {
  const { data: d, isLoading, error } = useKhoi<{ can_han_ngay: number; lo: Lo[] }>("han_su_dung");
  const lo = d?.lo ?? [];
  const duoi30 = new Set(lo.filter(x => x.con_lai < 30).map(x => x.ma)).size;
  return (
    <Khoi tieu_de="Sắp hết hạn" nhan={lo.length ? `${duoi30} mã dưới 30 ngày` : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/kho-hang" }}
      cach_tinh={lo.length ? `Trục ngang = số ngày còn tới hạn; mỗi chấm một lô, cỡ chấm theo giá trị tồn. Tổng giá trị tồn rủi ro ${yen(lo.reduce((s, x) => s + x.gia_tri, 0))}.` : undefined}>
      {d && (lo.length ? <DaiHan lo={lo} /> : <div className="trong">Không lô nào hết hạn trong {d.can_han_ngay} ngày tới.</div>)}
    </Khoi>
  );
}

// ---- Hiệu suất theo ngành hàng ----------------------------------------------
type Nganh = { nganh: string; doanh_thu: number; lai_gop: number; ty_trong: number | null; ty_suat: number | null; cung_ky: number | null; co_cung_ky: boolean; tang_truong: number | null };

export function KhoiNganh(p: XemP) {
  const { data: d, isLoading, error } = useKhoi<{ thang: string | null; nganh: Nganh[]; khoang: KhoangMayChu | null }>("hieu_suat_nganh");
  const cx = useCachXem("hieu_suat_nganh", p);
  const ss = d?.khoang?.so_sanh[0];
  const xem = cx.chon;
  const coSs = xem === "doanh_thu" && !!ss?.co;
  const nganh = xem === "bien" ? [...(d?.nganh ?? [])].sort((a, b) => (b.ty_suat ?? -1) - (a.ty_suat ?? -1)) : d?.nganh ?? [];
  const maxBien = Math.max(0.01, ...nganh.map(n => n.ty_suat ?? 0));
  const tang = (n: Nganh) => <span className={(n.tang_truong ?? 0) >= 0 ? "tang" : "giam"}>{n.tang_truong != null ? thay_doi(n.tang_truong) : n.co_cung_ky ? "—" : "chưa có"}</span>;
  return (
    <Khoi tieu_de="Ngành hàng" phu={d?.thang ? <>{d.thang}{ss?.co && xem !== "bien" ? <> · so {ss.nhan}</> : null}</> : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }} cach_xem={cx}
      cach_tinh={xem === "doanh_thu" ? `Thanh = doanh thu của ngành; số bên phải = tăng / giảm so kỳ so.${coSs ? ` Vạch đứt = ${ss!.nhan}.` : ""}`
        : xem === "bien" ? "Thanh = biên gộp của ngành = tổng lãi gộp ÷ tổng doanh thu thuần, xếp giảm dần."
        : "Thanh = tỷ trọng doanh thu của ngành; số bên phải = tăng / giảm so kỳ so. Biên gộp = tổng lãi gộp ÷ tổng doanh thu thuần."}
      canh_bao={ss && !ss.co && xem !== "bien" ? `${hoa(ss.nhan)}: không có dữ liệu để so.` : undefined}>
      {d && <ThanhNgang thang={xem === "bien" ? maxBien : undefined} nhan_ss={coSs ? hoa(ss!.nhan) : undefined} dong={nganh.map((n): DongThanh => ({
        khoa: n.nganh, ten: n.nganh,
        gia_tri: xem === "doanh_thu" ? n.doanh_thu : xem === "bien" ? (n.ty_suat ?? 0) : (n.ty_trong ?? 0),
        ss: coSs && n.co_cung_ky ? n.cung_ky : null,
        chu: xem === "doanh_thu" ? gon(n.doanh_thu) : xem === "bien" ? pc(n.ty_suat) : pc(n.ty_trong),
        phu: xem === "bien" ? undefined : tang(n),
        mau: xem === "bien" ? LUC.ok : "var(--lien-ket)",
        chi_tiet: <><DongNoi nhan="Doanh thu" gia={yen(n.doanh_thu)} /><DongNoi nhan="Lãi gộp" gia={yen(n.lai_gop)} />
          <DongNoi nhan="Tỷ trọng" gia={pc(n.ty_trong)} /><DongNoi nhan="Biên gộp" gia={pc(n.ty_suat)} />
          <DongNoi nhan={<>so {ss?.nhan ?? "kỳ so"}</>} gia={n.tang_truong != null ? thay_doi(n.tang_truong) : "—"} /></> }))} />}
    </Khoi>
  );
}

// ---- Doanh thu × tần suất mua -----------------------------------------------
type Cham = { ma: string; ten: string; doanh_thu: number; so_lan: number; trang_thai: string; ty_suat: number | null };

export function KhoiTuongQuan() {
  const { data: d, isLoading, error } = useKhoi<{ khach: Cham[]; khoang: KhoangMayChu | null }>("tuong_quan");
  const [tro, datTro] = useState<Cham | null>(null);
  const nm = useNhanMoc();
  const kieu = useRef("mouse");
  const k = d?.khach ?? [];
  const W = 600, H = 240, l = 56, r = 586, t = 14, b = 200;
  const lx = (v: number) => Math.log10(Math.max(v, 1)), mxX = Math.max(1, ...k.map(x => lx(x.so_lan))), mxY = Math.max(1, ...k.map(x => lx(x.doanh_thu))), mnY = Math.min(mxY - 1, ...k.map(x => lx(x.doanh_thu)));
  const px = (x: Cham) => l + (r - l) * (lx(x.so_lan) / mxX), py = (x: Cham) => b - (b - t) * ((lx(x.doanh_thu) - mnY) / (mxY - mnY || 1));
  return (
    <Khoi tieu_de="Doanh thu × tần suất" phu={d?.khoang?.nhan} dang_tai={isLoading} loi={error?.message}
      cach_tinh={`Mỗi chấm một khách; màu = trạng thái ${nm}; hai trục thang log. Rê / chạm để xem, bấm (chạm lần nữa) để mở hồ sơ.`}>
      {d && <div className="bd" style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Biểu đồ phân tán doanh thu theo số lần mua của từng khách">
          <line x1={l} y1={t} x2={l} y2={b} className="bd-luoi" /><line x1={l} y1={b} x2={r} y2={b} className="bd-luoi" />
          {k.map(x => <circle key={x.ma} cx={px(x)} cy={py(x)} r={tro?.ma === x.ma ? 6 : 4} fill={MAU_TT[x.trang_thai] ?? LUC.nhat}
            opacity={tro && tro.ma !== x.ma ? 0.35 : 0.72} style={{ cursor: "pointer" }}
            onPointerDown={e => { kieu.current = e.pointerType; }}
            onPointerEnter={e => { if (e.pointerType !== "touch") datTro(x); }} onPointerLeave={e => { if (e.pointerType !== "touch") datTro(null); }}
            onClick={() => {
              const b = buocCham(tro?.ma === x.ma, kieu.current);
              kieu.current = "mouse";
              if (b === "mo") { datTro(x); return; }
              location.href = giuKhoang(`/khach-hang/${x.ma}`);
            }} />)}
          <text x={(l + r) / 2} y={H - 8} textAnchor="middle" className="bd-truc">Số ngày mua trong khoảng (thang log) →</text>
          <text x={12} y={(t + b) / 2} textAnchor="middle" className="bd-truc" transform={`rotate(-90 12 ${(t + b) / 2})`}>Doanh thu trong khoảng (log) →</text>
        </svg>
        {tro && <div className="bd-noi" style={{ left: `${Math.min(Math.max(px(tro) / W * 100, 15), 85)}%` }}>
          <strong className="ten-jp">{tro.ten}</strong><div>Doanh thu<b>{yen(tro.doanh_thu)}</b></div>
          <div>Số ngày mua<b>{so(tro.so_lan)}</b></div><div>Biên gộp<b>{pc(tro.ty_suat)}</b></div></div>}
        <div className="bd-chu-giai">{Object.entries({ binh_thuong: "khoẻ", canh_bao: "cần theo dõi", da_roi_bo: "đang rời bỏ" }).map(([m, n]) =>
          <span key={m}><i style={{ background: MAU_TT[m], borderRadius: "50%", width: 9, height: 9, display: "inline-block", marginRight: 4 }} />{n}</span>)}</div>
      </div>}
    </Khoi>
  );
}

// ---- Số khách đang mua theo kỳ ----------------------------------------------
export function KhoiTangTruong(p: XemP) {
  const cx = useCachXem("tang_truong", p);
  const dt = cx.chon === "doanh_thu";
  const { data: d, isLoading, error } = useKhoi<{ chon: number | null; ky: { company_fy: number; nhan: string; so_thang: number; so_khach: number; doanh_thu: number }[] }>("tang_truong");
  const ky = d?.ky ?? [];
  const cuoi = ky[ky.length - 1];
  return (
    <Khoi tieu_de={dt ? "Doanh thu theo kỳ" : "Khách đang mua"} dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}
      cach_xem={cx} cach_tinh={dt ? "Doanh thu thuần theo từng kỳ kế toán (1/8 → 31/7)." : "Số khách có đơn theo từng kỳ kế toán (1/8 → 31/7)."}
      canh_bao={cuoi && cuoi.so_thang < 12 ? `${cuoi.nhan} mới có ${cuoi.so_thang} tháng — số khách thấp hơn, đừng so thẳng với kỳ đủ.` : undefined}>
      {d && <>
        {cuoi && (dt ? <SoLon gia={gon(cuoi.doanh_thu)} nhan={`doanh thu · ${cuoi.nhan}`} />
          : <SoLon gia={so(cuoi.so_khach)} nhan={`khách có đơn · ${cuoi.nhan}`} />)}
        <BieuDo key={cx.chon} nhan={ky.map(x => `K${x.company_fy}`)} nhan_day_du={ky.map(x => `${x.nhan} · ${x.so_thang} tháng dữ liệu`)} cao={150}
          mo_ta={dt ? "Doanh thu theo từng kỳ kế toán" : "Số khách có đơn theo từng kỳ kế toán"}
          chuoi={[{ ten: dt ? "Doanh thu" : "Khách có đơn", kieu: "cot", gia_tri: ky.map(x => dt ? x.doanh_thu : x.so_khach), mau: "var(--lien-ket)",
            mau_tung_cot: ky.map(x => x.company_fy === d.chon ? "var(--lien-ket)" : MO) }]}
          dinh_dang={v => dt ? yen(v) : `${so(v)} khách`} dinh_dang_truc={v => dt ? gon(v) : so(v)} />
      </>}
    </Khoi>
  );
}

// ---- Khách mới đăng ký (044) ------------------------------------------------
// Nguồn DUY NHẤT: mart.khach_moi_khoang (ngày đăng ký đọc từ mã khách). Số tổng
// toàn công ty; câu cách tính (máy chủ) in dưới khối.
type KhachMoi = { ma: string; ten: string; sale: string | null; ten_sale: string | null; ngay_dang_ky: string;
  lan_dau: string | null; so_ngay_mua: number; doanh_thu: number; da_mua: boolean; da_ngung: boolean };
type KhachMoiKhoi = { khoang: KhoangMayChu | null; so_khach: number; da_mua: number; chua_mua: number;
  so_sanh: { ma: string; nhan: string; co: boolean; so_khach: number | null; so_khach_nay: number }[];
  thang: { thang: string; so_khach: number; da_mua: number; so_khach_ss: number | null }[]; khach: KhachMoi[]; cach_tinh: string;
  ss: SsKhoi };

export function KhoiKhachMoi() {
  const { data: d, isLoading, error } = useKhoi<KhachMoiKhoi>("khach_moi");
  const t = d?.thang ?? [];
  const chua = (d?.khach ?? []).filter(k => !k.da_mua);
  return (
    <Khoi tieu_de="Khách mới" phu={d?.khoang?.nhan} cach_tinh={d?.cach_tinh}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}>
      {d && <>
        <SoLon gia={so(d.so_khach)} nhan="khách mới đăng ký" />
        {d.so_sanh.map(s => <DongSoSanh key={s.ma} nhan={s.nhan} co={s.co && s.so_khach != null}
          nay={s.so_khach_nay} ss={s.so_khach} />)}
        <ThanhChong dinh_dang={so} don_vi="Khách" khuc={[
          { khoa: "da", nhan: "Đã có đơn", dem: d.da_mua, mau: LUC.ok },
          { khoa: "chua", nhan: "Chưa có đơn", dem: d.chua_mua, mau: "var(--canh-chu)",
            chi_tiet: <>{chua.slice(0, 10).map(k => <DongNoi key={k.ma} nhan={<span className="ten-jp">{k.ten}</span>} gia={ngay_ngan(k.ngay_dang_ky)} />)}
              {d.chua_mua > Math.min(chua.length, 10) && <em>… và {so(d.chua_mua - Math.min(chua.length, 10))} khách nữa</em>}</> },
        ]} />
        <BieuDo nhan={t.map(x => thang_nhan(x.thang))} nhan_day_du={t.map(x => `Tháng ${thang_nhan(x.thang)}`)} cao={130}
          mo_ta="Số khách mới đăng ký từng tháng, 12 tháng gần nhất, và số đã có đơn"
          chuoi={[
            { ten: "Đăng ký", kieu: "cot_nen", gia_tri: t.map(x => x.so_khach), mau: "var(--vien)", so_voi: t.some(x => x.so_khach_ss != null) ? 2 : undefined },
            { ten: "Đã có đơn", kieu: "cot", gia_tri: t.map(x => x.da_mua), mau: LUC.ok,
              mau_tung_cot: t.map(x => trongKhoang(d.khoang, x.thang) ? LUC.ok : MO) },
            // Đã có hai lớp cột -> kỳ so là NÉT ĐỨT, không thêm lớp cột thứ ba (đặc tả §6).
            ...(t.some(x => x.so_khach_ss != null) ? [{ ten: `Đăng ký · ${d.ss?.nhan ?? "kỳ so"}`, kieu: "duong_dut" as const,
              gia_tri: t.map(x => x.so_khach_ss), mau: MAU_SS }] : []),
          ]}
          dinh_dang={v => `${so(v)} khách`} dinh_dang_truc={v => so(v)} />
      </>}
    </Khoi>
  );
}

// ---- Biên lợi nhuận theo quý ------------------------------------------------
export function KhoiBien() {
  const { data: d, isLoading, error } = useKhoi<{ thang_chon: string | null; so_sanh: SsKhoi; so_quy: number | null;
    quy: { company_fy: number; quy: number; tu: string; den: string; so_thang: number; doanh_thu: number; lai_gop: number; bien_gop: number | null;
      doanh_thu_ss: number | null; bien_gop_ss: number | null }[] }>("bien_loi_nhuan");
  const q = d?.quy ?? [];
  const ss = d?.so_sanh;
  const coSs = q.some(x => x.doanh_thu_ss != null);
  return (
    <Khoi tieu_de="Biên theo quý" phu={ss && coSs ? <>so {ss.nhan}</> : undefined} dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}
      cach_tinh="Biên gộp = tổng lãi gộp ÷ tổng doanh thu thuần. Biên RÒNG của gói thiết kế chưa có — cần chi phí vận hành, chưa có nguồn."
      canh_bao={ss && !coSs ? (d?.so_quy == null ? `${hoa(ss.nhan)} không lệch tròn quý — không so theo quý được.` : `${hoa(ss.nhan)}: không có dữ liệu để so.`) : undefined}>
      {d && <>
        <BieuDo nhan={q.map(x => `K${x.company_fy}·Q${x.quy}`)} nhan_day_du={q.map(x => `Kỳ ${x.company_fy} quý ${x.quy} (${thang_nhan(x.tu)} – ${thang_nhan(x.den)})${x.so_thang < 3 ? " · chưa đủ quý" : ""}`)}
          cao={170} mo_ta="Biên lãi gộp sáu quý gần nhất"
          chuoi={[
            { ten: "Doanh thu", kieu: "cot", gia_tri: q.map(x => x.doanh_thu), mau: "var(--chu-mo)", so_voi: coSs ? 2 : undefined,
              mau_tung_cot: q.map(x => d.thang_chon && x.tu <= d.thang_chon && d.thang_chon <= x.den ? "var(--lien-ket)" : "var(--chu-mo)") },
            { ten: "Biên gộp", kieu: "duong", gia_tri: q.map(x => x.bien_gop), mau: "var(--ok-vien)", truc_phai: true },
            ...(coSs ? [
              { ten: `Doanh thu · ${ss?.nhan}`, kieu: "cot_ma" as const, gia_tri: q.map(x => x.doanh_thu_ss), mau: MAU_SS },
              { ten: `Biên gộp · ${ss?.nhan}`, kieu: "duong_dut" as const, gia_tri: q.map(x => x.bien_gop_ss), mau: MAU_SS, truc_phai: true },
            ] : []),
          ]}
          dinh_dang={(v, c) => c.truc_phai ? pc(v) : yen(v)} dinh_dang_truc={v => gon(v)} />
      </>}
    </Khoi>
  );
}

// ---- Việc cần làm hôm nay ---------------------------------------------------
type Viec = { muc: "gap" | "canh" | "thuong"; tag: string; chu: string; lien_ket: string; han: string | null };

const MAU_MUC: Record<Viec["muc"], string> = { gap: LUC.do, canh: LUC.canh, thuong: LUC.nhat };
const SO_VIEC_GON = 5;

export function KhoiViec() {
  const [tatCa, datTatCa] = useState(false);
  const [loc, datLoc] = useState<string | null>(null);
  const [moRong, datMoRong] = useState(false);
  const { data: d, isLoading, error } = useKhoi<{ viec: Viec[]; thieu_nguon: string[] }>("viec_hom_nay", true, tatCa ? "tat_ca=1" : "");
  const khoa = `kome_viec_xong_${new Date().toISOString().slice(0, 10)}`;
  const [xong, datXong] = useState<Record<string, boolean>>(() => { try { return JSON.parse(localStorage.getItem(khoa) || "{}"); } catch { return {}; } });
  const v = d?.viec ?? [];
  const soXong = v.filter(x => xong[x.chu]).length;
  const bat = (c: string) => { const m = { ...xong, [c]: !xong[c] }; datXong(m); try { localStorage.setItem(khoa, JSON.stringify(m)); } catch { /* */ } };
  const ds = sapViec(v.filter(x => !loc || x.tag === loc));
  const hien = moRong || loc ? ds : ds.slice(0, SO_VIEC_GON);
  return (
    <Khoi tieu_de="Việc hôm nay" dang_tai={isLoading} loi={error?.message}
      nhan={v.length ? `${soXong}/${v.length} xong` : undefined} mau_nhan={soXong === v.length ? "ok" : "nhat"}
      phu={KD.nguoi?.sale ? <button type="button" className="chip" aria-pressed={!tatCa}
        onClick={() => { datTatCa(t => !t); datLoc(null); datMoRong(false); }}>{tatCa ? "Mọi người" : "Của tôi"}</button> : undefined}
      cach_tinh={d ? `Chưa gom được việc từ ${d.thieu_nguon.join(", ")} — chưa có nguồn dữ liệu. Dấu "xong" chỉ nhớ trên máy này, trong hôm nay. Bấm một khúc của thanh để lọc theo lý do.` : undefined}>
      {d && <>
        {v.length > 0 && <ThanhChong dinh_dang={so} don_vi="Việc"
          khuc={demTheoTag(v).map(t => ({ khoa: t.tag, nhan: t.tag, dem: t.dem, mau: MAU_MUC[t.muc], chon: loc === t.tag,
            onBam: () => datLoc(l => (l === t.tag ? null : t.tag)) }))} />}
        <div className="viec-ds">
          {hien.map(x => (
            <div key={x.chu} className={"viec-dong" + (xong[x.chu] ? " xong" : "")}>
              <input type="checkbox" checked={!!xong[x.chu]} onChange={() => bat(x.chu)} aria-label={`Đánh dấu xong: ${x.chu}`} />
              <i className="viec-cham" style={{ background: MAU_MUC[x.muc] }} aria-hidden="true" />
              <ONoi href={x.lien_ket} className="viec-chu ten-jp"
                noi_dung={<><strong>{x.tag}</strong><div className="o-noi-chu">{x.chu}</div>{x.han && <DongNoi nhan="Hạn" gia={x.han} />}</>}>
                {tenViec(x.chu)}</ONoi>
            </div>))}
          {!v.length && <div className="trong">Không có việc nào hôm nay.</div>}
          {!moRong && !loc && ds.length > SO_VIEC_GON &&
            <button type="button" className="lien-ket viec-them" onClick={() => datMoRong(true)}>+{ds.length - SO_VIEC_GON} việc</button>}
        </div>
      </>}
    </Khoi>
  );
}

// ---- Tháng này chưa mua (036) -----------------------------------------------
// Nguồn DUY NHẤT: mart.khach_thang_nay.nhan (kome/khach_thang.py). Nhìn theo
// THÁNG — khác "im lặng quá nhịp" của khối Sức khoẻ; câu cách tính in dưới khối.
type KhachThang = { ma: string; ten: string; sale: string | null; so_thang: number; tb_thang: number; thang_truoc: number };
type ThangNay = { thang: string | null; ngay_moc: string | null; dem: Record<string, number>; nhan: Record<string, string>;
  cach_tinh: string; thang_truoc_den_ngay: number; khach: KhachThang[] };

export function KhoiThangNay() {
  const [tatCa, datTatCa] = useState(false);
  const { data: d, isLoading, error } = useKhoi<ThangNay>("thang_nay_chua_mua", true, tatCa ? "tat_ca=1" : "");
  const giu = KD.nguoi?.sale && !tatCa ? "" : "&tat_ca=1";
  const da = d?.dem.da_mua ?? 0, truoc = d?.thang_truoc_den_ngay ?? 0;
  return (
    <Khoi tieu_de="Tháng này chưa mua" dang_tai={isLoading} loi={error?.message}
      phu={d?.thang ? <>{thang_nhan(d.thang)} · đến {ngay_ngan(d.ngay_moc ?? "")}
        {KD.nguoi?.sale && <button type="button" className="chip" aria-pressed={!tatCa} onClick={() => datTatCa(t => !t)}
          style={{ marginLeft: ".4rem" }}>{tatCa ? "Mọi người" : "Của tôi"}</button>}</> : undefined}
      lien_ket={{ href: `/lien-he?ly_do=thang_nay_chua_mua${giu}` }}
      cach_tinh={d ? `${d.cach_tinh} Bộ đếm là của cả công ty; thanh = trung bình mỗi tháng, xếp giảm dần.` : undefined}>
      {d && <>
        <SoLon gia={so(d.dem.tre ?? 0)} nhan="khách mua đều chưa có đơn"
          chi_tiet={<><DongNoi nhan="Đã mua tháng này" gia={`${so(da)} khách`} />
            {truoc > 0 && <DongNoi nhan="Tháng trước đến cùng ngày" gia={<>{so(truoc)} <span className={da >= truoc ? "tang" : "giam"}>({thay_doi(da / truoc - 1, 0)})</span></>} />}
            {(d.dem.chua_toi_ngay ?? 0) > 0 && <DongNoi nhan="Thường mua muộn hơn — chưa tới ngày" gia={so(d.dem.chua_toi_ngay)} />}</>} />
        {d.khach.length
          ? <ThanhNgang dong={d.khach.slice(0, 10).map((k): DongThanh => ({
              khoa: k.ma, ten: k.ten, ten_jp: true, gia_tri: k.tb_thang, chu: gon(k.tb_thang), mau: LUC.canh,
              href: `/khach-hang/${k.ma}`,
              chi_tiet: <><DongNoi nhan="Mua" gia={`${k.so_thang}/3 tháng trước`} /><DongNoi nhan="TB / tháng" gia={yen(k.tb_thang)} />
                <DongNoi nhan="Tháng trước" gia={yen(k.thang_truoc)} /></> }))} />
          : <div className="trong">Không có khách mua đều nào đang trễ tháng này.</div>}
      </>}
    </Khoi>
  );
}

// ---- Nạp dữ liệu / phiếu gần nhất -------------------------------------------
export function KhoiNap() {
  const { data: d, isLoading, error } = useKhoi<{ lo: { loai: string; ten_file: string; ngay_du_lieu: string; nap_luc: string; so_dong: number }[];
    phieu: { ngay: string; so: string; ma: string; ten: string; tien: number }[] }>("don_hang");
  return (
    <Khoi tieu_de="Nạp dữ liệu / phiếu gần nhất" dang_tai={isLoading} loi={error?.message} lien_ket={KD.hien_kho ? { href: "/kho-du-lieu" } : undefined}>
      {d && <div className="hai-cot-tt">
        <div><div className="tieu-muc">LẦN NẠP GẦN NHẤT</div>
          <div className="nap-ds">{d.lo.map((x, i) => (
            <ONoi key={i} className="nap-dong" noi_dung={<><strong>{x.loai}</strong><DongNoi nhan="File" gia={x.ten_file} />
              <DongNoi nhan="Ngày dữ liệu" gia={ngay(x.ngay_du_lieu)} /></>}>
              <span>{x.loai}</span><b>{so(x.so_dong)} dòng</b><span className="nhat-chu">{gio_tokyo(x.nap_luc)}</span></ONoi>))}</div></div>
        <div><div className="tieu-muc">PHIẾU BÁN MỚI NHẤT</div>
          <div className="nap-ds">{d.phieu.map(x => (
            <a key={x.so} className="nap-dong" href={`/khach-hang/${x.ma}`}>
              <span className="ten-jp">{x.ten}</span><b>{yen(x.tien)}</b><span className="nhat-chu">{ngay_ngan(x.ngay)}</span></a>))}</div></div>
      </div>}
    </Khoi>
  );
}

// ---- Bảng tra mã khối -> thành phần ------------------------------------------
export const VE: Record<string, (p: XemP) => React.ReactElement> = {
  kpi: () => <KhoiKpi />, ns_thang: p => <KhoiNganSach {...p} />, theo_thang: p => <KhoiTheoThang {...p} />,
  viec_hom_nay: () => <KhoiViec />, xu_huong: p => <KhoiXuHuong {...p} />, suc_khoe_khach: p => <KhoiSucKhoe {...p} />,
  danh_sach_khach: p => <KhoiDanhSachKhach {...p} />, han_su_dung: () => <KhoiHanSuDung />, hieu_suat_nganh: p => <KhoiNganh {...p} />,
  so_sanh_sale: p => <KhoiSale {...p} />, tuong_quan: () => <KhoiTuongQuan />, tang_truong: p => <KhoiTangTruong {...p} />,
  bien_loi_nhuan: () => <KhoiBien />, don_hang: () => <KhoiNap />,
  thang_nay_chua_mua: () => <KhoiThangNay />, cong_no: p => <KhoiCongNo {...p} />, khach_moi: () => <KhoiKhachMoi />,
};

export function veKhoi(id: string, nhan: string, xem: string | null = null, datXem: (ma: string | null) => void = () => {}) {
  const f = VE[id];
  if (f) return f({ xem, datXem });
  return <ChuaCoDuLieu gon tieu_de={nhan} ly_do={KD.chua_co[id] ?? "Chưa có nguồn dữ liệu cho khối này."} />;
}
