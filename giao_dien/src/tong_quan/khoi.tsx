// Các khối của Tổng quan — bố cục theo Dashboard.dc.html, số THẬT từ
// /api/tong-quan/<khối> (kome/khoi_tong_quan.py). Không số mẫu ở đâu cả.
import { useMemo, useState } from "react";
import { useKhoi } from "../api";
import { giuKhoang } from "../khung/khoang";
import { BieuDo, type Chuoi } from "../chung/BieuDo";
import { ChuaCoDuLieu, Khoi, Spark, ThanhMoc, mauTienDo } from "../chung/Khoi";
import { gio_tokyo, gon, ngay, ngay_ngan, pc, so, thang_nhan, thay_doi, yen } from "../dinh_dang";
import { KD, TN } from "../khoi_dau";
import { useNhanMoc, type KhoangMayChu } from "../khung/khoang";
import { DongSoSanh, VachSoSanh } from "../chung/SoSanh";
import { DongNoi, ONoi } from "../chung/ONoi";
import { HangSo, MucSo, SoLon, ThanhChong } from "../chung/Hinh";

const LUC = { ok: "var(--ok-vien)", canh: "var(--lien-ket)", do: "var(--do)", nhat: "var(--chu-mo)", nen: "var(--vien)" };
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
        <OKpi chua nhan="Phải trả 7 ngày" gia="chưa có" chi_tiet={<div className="o-noi-chu">{KD.chua_co.dong_tien ?? "Cần sổ phải trả."}</div>} />
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

export function KhoiCongNo() {
  const { data: d, isLoading, error } = useKhoi<CongNo>("cong_no");
  if (!isLoading && !error && !d) return <ChuaCoDuLieu gon tieu_de="Tuổi nợ phải thu" ly_do="Chưa nạp sổ 請求先元帳 nào — xuất từ OBC rồi nạp ở màn Kho dữ liệu." />;
  return (
    <Khoi tieu_de="Tuổi nợ phải thu" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/cong-no" }}
      phu={d ? `đến ${ngay_ngan(d.moc)}` : undefined} cach_tinh={d?.cach_tinh}>
      {d && <>
        <SoLon href="/cong-no?tab=qua_han" gia={gon(d.tq.qua_han)} lop={d.tq.qua_han ? "giam" : undefined} nhan="quá hạn"
          chi_tiet={<><DongNoi nhan="Tổng phải thu" gia={yen(d.tq.tong_phai_thu)} />
            <DongNoi nhan="Phiếu quá hạn" gia={so(d.tq.so_phieu_qua_han)} />
            <DongNoi nhan="Bên nhận hoá đơn quá hạn" gia={so(d.tq.so_ben_qua_han)} />
            {d.lau_nhat.length > 0 && <em>Nợ lâu / quá hạn nhiều nhất:</em>}
            {d.lau_nhat.map(x => <DongNoi key={x.ma} nhan={<span className="ten-jp">{x.ten}</span>} gia={yen(x.tien)} />)}</>} />
        <ThanhChong dinh_dang={gon} don_vi="Còn nợ"
          khuc={d.tq.tuoi.map(t => ({ khoa: t.nhom, nhan: t.nhan, dem: t.tien, mau: MAU_TUOI[t.nhom] ?? LUC.nhat,
            href: `/cong-no?nhom=${t.nhom}`, chi_tiet: <DongNoi nhan="Số phiếu" gia={so(t.dem)} /> }))} />
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
function DuongNganSach({ duong }: { duong: DuongNS }) {
  const [cs, datCs] = useState<"dt" | "lg">("dt");
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
      <div className="ns-chon" role="group" aria-label="Chỉ số của biểu đồ">
        {(["dt", "lg"] as const).map(k => <button key={k} type="button" aria-pressed={cs === k} className={cs === k ? "dang-chon" : undefined}
          onClick={() => datCs(k)}>{k === "dt" ? "Doanh thu" : "Lãi gộp"}</button>)}
      </div>
      <BieuDo key={cs} nhan={ds.map(x => theoNgay ? ngay_ngan(x.nhan) : thang_nhan(x.nhan))}
        nhan_day_du={ds.map(x => theoNgay ? ngay(x.nhan) : thang_nhan(x.nhan))}
        cao={180} mo_ta={`${ten} luỹ kế so với nhịp ngân sách`} chuoi={chuoi}
        vach={iDen >= 0 && iDen < ds.length - 1 ? { i: iDen, chu: "mốc" } : null}
        dinh_dang={v => yen(v)} dinh_dang_truc={v => gon(v)} />
      {!coSS && duong.nhan_ss && <div className="khoi-canh">{hoa(duong.nhan_ss)}: không vẽ được đường luỹ kế để so (không có dữ liệu, hoặc kỳ so không cùng gốc tháng).</div>}
    </div>
  );
}

export function KhoiNganSach() {
  const { data: d, isLoading, error } = useKhoi<NganSach | null>("ns_thang");
  if (d?.chi_theo_thang) return <ChuaCoDuLieu gon tieu_de="Tiến độ ngân sách" ly_do={NS_THEO_THANG} />;
  const nguoi = [...(d?.nguoi ?? [])].sort((a, b) => b.thuc_te - a.thuc_te);
  const maxNS = Math.max(1, ...nguoi.map(n => Math.max(n.muc_tieu ?? 0, n.thuc_te, n.dt_ss ?? 0)));
  const ssN = d?.so_sanh;
  const vuot = !!d && d.muc_tieu_den_hom_nay != null && d.thuc_te >= d.muc_tieu_den_hom_nay;
  return (
    <Khoi tieu_de={`Ngân sách ${d ? thang_nhan(d.thang) : ""}`} dang_tai={isLoading} loi={error?.message}
      nhan={d ? `Còn ${d.ngay_kd_con_lai} ngày làm việc` : undefined} lien_ket={{ href: "/bao-cao", chu: "Xem chi tiết" }}
      phu={ssN?.co ? <>so {ssN.nhan}</> : undefined}
      cach_tinh={d ? <>{d.co_ngan_sach ? `Vạch đen = mốc đáng lẽ đạt tới hôm nay (${pc(d.moc)}) — tính theo ngày làm việc, trừ ngày lễ.` : "Thanh = doanh thu thực tế của từng người phụ trách."}
        {ssN?.co ? ` Vạch đứt = doanh thu ${ssN.nhan}.` : ""}</> : undefined}
      canh_bao={d && !d.co_ngan_sach ? <>Chưa đặt chỉ tiêu tháng này.{KD.hien_ngan_sach && <> <a href="/ngan-sach">Đặt chỉ tiêu →</a></>}</>
        : ssN && !ssN.co ? `${hoa(ssN.nhan)}: không có dữ liệu để so.` : undefined}>
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
      {d?.duong && <DuongNganSach duong={d.duong} />}
    </Khoi>
  );
}

// ---- Doanh thu theo sale ----------------------------------------------------
export function KhoiSale() {
  const { data: d, isLoading, error } = useKhoi<NganSach | null>("so_sanh_sale");
  if (d?.chi_theo_thang) return <ChuaCoDuLieu tieu_de="Doanh thu theo sale" ly_do={NS_THEO_THANG} />;
  const nguoi = [...(d?.nguoi ?? [])].sort((a, b) => b.thuc_te - a.thuc_te);
  const max = Math.max(1, ...nguoi.map(n => Math.max(n.thuc_te, n.dt_ss ?? 0)));
  const ssN = d?.so_sanh;
  return (
    <Khoi tieu_de="Doanh thu theo sale" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}
      phu={ssN ? (ssN.co ? `vạch đứt = ${ssN.nhan}` : `${hoa(ssN.nhan)}: không có dữ liệu để so`) : undefined}>
      {d && <div className="sale-ds">
        {nguoi.map(n => (
          <div key={n.ma}>
            <div className="ns-dong"><span>{tenNguoi(n.ten, n.ma)}</span><span className="so-nhat">{gon(n.thuc_te)}</span>
              {ssN && <TdSs nay={n.thuc_te} ss={n.dt_ss} nhan={ssN.nhan} />}
              {n.muc_tieu ? <b style={{ color: mauTienDo(n.tien_do, d.moc) }}>{pc(n.tien_do)}</b> : <em className="nhat-chu">chưa có chỉ tiêu</em>}</div>
            <div className="ss-thanh"><div className="thanh-mong"><div style={{ width: `${n.muc_tieu ? Math.min(n.tien_do ?? 0, 1) * 100 : n.thuc_te / max * 100}%`,
              background: n.muc_tieu ? mauTienDo(n.tien_do, d.moc) : LUC.canh }} /></div>
              {ssN && <VachSoSanh ty_le={n.dt_ss == null ? null : n.muc_tieu ? n.dt_ss / n.muc_tieu : n.dt_ss / max}
                nhan={`${hoa(ssN.nhan)}: ${yen(n.dt_ss)}`} />}</div>
          </div>))}
        <div className="phu">{d.co_ngan_sach ? `% là tiến độ so ngân sách cá nhân tháng ${thang_nhan(d.thang).slice(1)}` : `Doanh thu tháng ${thang_nhan(d.thang).slice(1)} — chưa đặt chỉ tiêu nên chưa có %`}</div>
      </div>}
    </Khoi>
  );
}

// ---- Kết quả theo từng tháng ------------------------------------------------
type Thang = { thang: string; thang_trong_ky: number; doanh_thu: number; lai_gop: number; ty_suat: number | null; so_khach: number;
  cung_ky: number | null; co_cung_ky: boolean; ngan_sach: number | null };

export function KhoiTheoThang() {
  const { data: d, isLoading, error } = useKhoi<{ company_fy: number | null; thang: Thang[]; hom_nay: string | null; khoang: KhoangMayChu | null;
    so_sanh: SsKhoi; cat_cung_ngay: boolean }>("theo_thang");
  const t = d?.thang ?? [];
  const thangNay = d?.hom_nay?.slice(0, 7);
  const kx = d?.khoang;
  const tong = t.reduce((s, x) => s + x.doanh_thu, 0);
  const ss = d?.so_sanh;
  // Tháng đang chạy chỉ so ngang được khi máy chủ đã cắt kỳ so cùng dải ngày.
  const coCK = t.filter(x => x.cung_ky != null && (x.thang !== thangNay || d?.cat_cung_ngay));
  const dtCK = coCK.reduce((s, x) => s + x.doanh_thu, 0), ck = coCK.reduce((s, x) => s + (x.cung_ky ?? 0), 0);
  const coNS = t.filter(x => x.ngan_sach != null && x.thang !== thangNay);
  const dat = coNS.filter(x => x.doanh_thu >= (x.ngan_sach ?? 0)).length;
  const cao = t.length ? t.reduce((a, b) => (b.doanh_thu > a.doanh_thu ? b : a)) : null;
  const chuoi: Chuoi[] = [
    { ten: hoa(ss?.nhan) || "Kỳ so", kieu: "cot_ma", gia_tri: t.map(x => x.cung_ky), mau: MAU_SS },
    { ten: "Doanh thu", kieu: "cot", gia_tri: t.map(x => x.doanh_thu), mau: LUC.do, so_voi: 0,
      mau_tung_cot: t.map(x => !trongKhoang(kx, x.thang) ? MO : x.ngan_sach == null ? "var(--lien-ket)" : x.doanh_thu >= x.ngan_sach ? LUC.do : "color-mix(in srgb, var(--do) 50%, var(--nen-the))") },
    { ten: "Ngân sách tháng", kieu: "duong", gia_tri: t.map(x => x.ngan_sach), mau: "var(--lien-ket)" },
  ];
  return (
    <Khoi tieu_de="Theo từng tháng" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao", chu: "Báo cáo" }}
      phu={ss ? <>so {ss.nhan}</> : undefined}
      cach_tinh={d?.company_fy ? `Cả kỳ chứa ${kx?.nhan ?? "khoảng xem"} (kỳ kết thúc 7/${d.company_fy}). Cột đậm = thuộc khoảng xem; cột viền đứt = ${ss?.nhan ?? "kỳ so"}; đường = ngân sách tháng.` : undefined}
      canh_bao={!d ? undefined
        : ss && ss.co && ss.lech_thang == null ? "Kỳ so không lệch tròn tháng — không so theo tháng được."
        : ss && !ck ? `${hoa(ss.nhan)}: không có dữ liệu để so.`
        : thangNay && t.some(x => x.thang === thangNay)
          ? (d.cat_cung_ngay ? `Tháng đang chạy chưa đủ ngày — %NS chưa so ngang được; cột ma của tháng này đã cắt cùng dải ngày ở ${ss?.nhan}.`
            : "Tháng đang chạy chưa đủ ngày — %NS và phép so của tháng này chưa so ngang được.")
          : undefined}>
      {d && <>
        <HangSo>
          <MucSo nhan="Luỹ kế" gia={gon(tong)} chi_tiet={<DongNoi nhan="Tháng có dữ liệu"
            gia={t.length ? `${t.length} (${thang_nhan(t[0].thang)} – ${thang_nhan(t[t.length - 1].thang)})` : "0"} />} />
          <MucSo nhan={<>so {ss?.nhan ?? "kỳ so"}</>} gia={ck ? thay_doi(dtCK / ck - 1) : "—"} lop={ck ? (dtCK >= ck ? "tang" : "giam") : undefined}
            chi_tiet={ck ? <><DongNoi nhan="Tháng đối chiếu" gia={so(coCK.length)} /><DongNoi nhan="Chênh" gia={gon(dtCK - ck)} /></> : undefined} />
          <MucSo nhan="Đạt ngân sách" gia={coNS.length ? `${dat}/${coNS.length}` : "—"}
            chi_tiet={<div className="o-noi-chu">{coNS.length ? "Số tháng đã khép lại đạt ngân sách." : "Chưa đặt chỉ tiêu tháng nào."}</div>} />
          <MucSo nhan="Cao nhất" gia={cao ? thang_nhan(cao.thang) : "—"}
            chi_tiet={cao ? <><DongNoi nhan="Doanh thu" gia={yen(cao.doanh_thu)} /><DongNoi nhan="Biên gộp" gia={pc(cao.ty_suat)} /></> : undefined} />
        </HangSo>
        <BieuDo nhan={t.map(x => thang_nhan(x.thang))} chuoi={chuoi} cao={200} mo_ta={`Doanh thu từng tháng của kỳ so ngân sách và ${ss?.nhan ?? "kỳ so"}`}
          dinh_dang={v => yen(v)} dinh_dang_truc={v => gon(v)}
          vach={thangNay ? { i: t.findIndex(x => x.thang === thangNay), chu: "đang chạy" } : null}
          them_noi={i => { const x = t[i]; return x && <>
            <div>%NS<b>{x.ngan_sach ? pc(x.doanh_thu / x.ngan_sach, 0) : "—"}</b></div>
            <div>Biên gộp<b>{pc(x.ty_suat)}</b></div>
            <div>Khách<b>{so(x.so_khach)}</b></div></>; }} />
      </>}
    </Khoi>
  );
}

// ---- Xu hướng doanh thu (theo khoảng xem) ---------------------------------
type XuHuong = { khoang: KhoangMayChu | null; kieu: "ngay" | "thang"; diem: [string, number, number, number, number | null][] };

export function KhoiXuHuong() {
  const { data: d, isLoading, error } = useKhoi<XuHuong>("xu_huong");
  const ds = d?.diem ?? [];
  const kx = d?.khoang;
  const ss = kx?.so_sanh[0];
  const tong = ds.reduce((s, x) => s + x[1], 0);
  const coCk = ds.some(x => x[4] != null);
  const tongCk = ds.reduce((s, x) => s + (x[4] ?? 0), 0);
  const coNgay = ds.filter(x => x[1] !== 0).length;
  const theoNgay = d?.kieu !== "thang";
  return (
    <Khoi tieu_de={`Xu hướng · ${kx?.nhan ?? ""}`} dang_tai={isLoading} loi={error?.message}
      phu={ss?.co ? <>so {ss.nhan}</> : undefined}
      cach_tinh={ss?.co ? `${ds.length <= 40 ? "Cột viền đứt" : "Nét đứt"}: ${ss.nhan} (${ngay(ss.tu)} → ${ngay(ss.den)}).` : undefined}
      canh_bao={ss && !ss.co ? `${hoa(ss.nhan)}: không có dữ liệu để so.` : ss && !coCk ? "Kỳ so khác độ dài — chỉ so tổng." : undefined}>
      {d && <>
        <HangSo>
          <MucSo nhan={`Tổng ${ds.length} ${theoNgay ? "ngày" : "tháng"}`} gia={gon(tong)} />
          <MucSo nhan={<>so {ss?.nhan ?? "—"}</>} gia={coCk && tongCk > 0 ? thay_doi(tong / tongCk - 1) : "—"} lop={tong >= tongCk ? "tang" : "giam"}
            chi_tiet={coCk ? <DongNoi nhan={hoa(ss?.nhan)} gia={yen(tongCk)} /> : undefined} />
          <MucSo nhan={theoNgay ? "TB / ngày có bán" : "TB / tháng"} gia={gon(theoNgay ? (coNgay ? tong / coNgay : null) : (ds.length ? tong / ds.length : null))} />
        </HangSo>
        <BieuDo nhan={ds.map(x => theoNgay ? ngay_ngan(x[0]) : thang_nhan(x[0]))} nhan_day_du={ds.map(x => theoNgay ? ngay(x[0]) : thang_nhan(x[0]))}
          cao={200} mo_ta={`Doanh thu ${kx?.nhan ?? ""} so ${ss?.nhan ?? ""}`}
          chuoi={[
            { ten: theoNgay ? "Doanh thu ngày" : "Doanh thu tháng", kieu: ds.length <= 40 ? "cot" : "duong", gia_tri: ds.map(x => x[1]), mau: "var(--lien-ket)", so_voi: 1 },
            // Cột → cột ma, đường → nét đứt (đặc tả 2026-09-28 §6).
            { ten: hoa(ss?.nhan) || "Kỳ so", kieu: ds.length <= 40 ? "cot_ma" : "duong_dut", gia_tri: ds.map(x => x[4]), mau: MAU_SS },
          ]}
          dinh_dang={v => yen(v)} dinh_dang_truc={v => gon(v)} />
      </>}
    </Khoi>
  );
}

// ---- Sức khoẻ khách hàng ----------------------------------------------------
const MAU_TT: Record<string, string> = { binh_thuong: LUC.ok, canh_bao: LUC.canh, da_roi_bo: LUC.do, ngung_giao_dich: LUC.nhat, chua_du_lich_su: "var(--vien-dam)" };

export function KhoiSucKhoe() {
  const { data: d, isLoading, error } = useKhoi<{ dem: Record<string, number>; nhom: string[]; nhan: Record<string, string> }>("suc_khoe_khach");
  const nm = useNhanMoc();
  const tong = d ? d.nhom.reduce((s, n) => s + (d.dem[n] ?? 0), 0) : 0;
  const hd = d ? (d.dem.binh_thuong ?? 0) + (d.dem.canh_bao ?? 0) : 0;
  return (
    <Khoi tieu_de="Sức khoẻ khách hàng" phu={`tính ${nm}`} dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}>
      {d && <>
        <div className="sk-dau">{so(hd)} <span>khách đang mua</span></div>
        <div className="phu" style={{ marginBottom: ".6rem" }}>{so(d.dem.canh_bao ?? 0)} khách im lặng quá nhịp mua riêng · so với nhịp của CHÍNH từng khách</div>
        <div className="sk-thanh">{d.nhom.map(n => (d.dem[n] ?? 0) > 0 &&
          <a key={n} href={`/khach-hang?loc=${n}&tat_ca=1`} style={{ width: `${(d.dem[n] ?? 0) / (tong || 1) * 100}%`, background: MAU_TT[n] }}
             title={`${d.nhan[n]}: ${so(d.dem[n])} khách`} aria-label={`${d.nhan[n]}: ${so(d.dem[n])} khách`} />)}</div>
        <div className="sk-ds">{d.nhom.map(n => (
          <a key={n} href={`/khach-hang?loc=${n}&tat_ca=1`}><i style={{ background: MAU_TT[n] }} />{d.nhan[n]}<b>{so(d.dem[n] ?? 0)}</b></a>))}</div>
      </>}
    </Khoi>
  );
}

// ---- Danh sách khách hàng ---------------------------------------------------
type KhachDS = { ma: string; ten: string; sale: string | null; ten_sale: string | null; doanh_thu: number; ty_le_im_lang: number | null;
  trang_thai: string; so_ngay_im_lang: number | null; nhip_ngay: number | null; thang_nay: number; thang_truoc: number | null };
const UU_TIEN: Record<string, number> = { da_roi_bo: 0, canh_bao: 1, binh_thuong: 2, chua_du_lich_su: 3, ngung_giao_dich: 4 };
type CotSap = "can" | "ten" | "thang_nay" | "thang_truoc" | "ty_le" | "doanh_thu";

export function KhoiDanhSachKhach() {
  const { data: d, isLoading, error } = useKhoi<{ khach: KhachDS[]; nhan: Record<string, string>; khoang: KhoangMayChu | null;
    so_sanh: { ma: string; nhan: string; co: boolean; tu: string; den: string } | null }>("danh_sach_khach");
  const nhanSs = d?.so_sanh ? d.so_sanh.nhan.replace(/^./, c => c.toUpperCase()) : "So sánh";
  const nm = useNhanMoc();
  const [sap, datSap] = useState<{ cot: CotSap; giam: boolean }>({ cot: "can", giam: false });
  const ds = useMemo(() => {
    const a = [...(d?.khach ?? [])];
    const g = (k: KhachDS): number | string => sap.cot === "can" ? (UU_TIEN[k.trang_thai] ?? 9) * 1e12 - k.doanh_thu
      : sap.cot === "ten" ? k.ten : sap.cot === "ty_le" ? (k.ty_le_im_lang ?? -1) : (k[sap.cot] ?? -Infinity);
    a.sort((x, y) => { const p = g(x), q = g(y); const r = p < q ? -1 : p > q ? 1 : 0; return sap.giam ? -r : r; });
    return a;
  }, [d, sap]);
  const th = (cot: CotSap, chu: string, so_ = false) => (
    <th className={"sap" + (so_ ? " so" : "")} aria-sort={sap.cot === cot ? (sap.giam ? "descending" : "ascending") : "none"}
      onClick={() => datSap(s => ({ cot, giam: s.cot === cot ? !s.giam : cot !== "ten" && cot !== "can" }))}>
      {chu}{sap.cot === cot ? (sap.giam ? " ↓" : " ↑") : ""}</th>);
  return (
    <Khoi tieu_de="Danh sách khách hàng" phu={`60 khách doanh thu cao nhất · ${d?.khoang?.nhan ?? ""} · bấm tiêu đề cột để sắp xếp`} dang_tai={isLoading} loi={error?.message}
      lien_ket={{ href: "/khach-hang?tat_ca=1" }}>
      {d && <div className="bang-cuon" style={{ maxHeight: 420 }}><table className="bang">
        <thead><tr>{th("ten", "Khách hàng")}{th("thang_nay", d.khoang?.nhan ?? "Khoảng xem", true)}{th("thang_truoc", nhanSs, true)}
          <th className="so">So {d.so_sanh?.nhan ?? ""}</th>{th("ty_le", `Im lặng · ${nm}`, true)}{th("doanh_thu", "Doanh thu 12 tháng", true)}<th>Phụ trách</th>{th("can", "Cần làm")}</tr></thead>
        <tbody>{ds.map(k => (
          <tr key={k.ma}>
            <td className="ten-jp"><a href={`/khach-hang/${k.ma}`}>{k.ten}</a></td>
            <td className="so">{yen(k.thang_nay)}</td><td className="so">{k.thang_truoc != null ? yen(k.thang_truoc) : "—"}</td>
            <td className={"so " + (k.thang_truoc ? (k.thang_nay >= k.thang_truoc ? "tang" : "giam") : "")}>{k.thang_truoc ? thay_doi(k.thang_nay / k.thang_truoc - 1, 0) : "—"}</td>
            <td className={"so " + ((k.ty_le_im_lang ?? 0) >= 2 ? "giam" : (k.ty_le_im_lang ?? 0) >= 1 ? "canh-chu" : "")} title={k.nhip_ngay ? `im ${k.so_ngay_im_lang} ngày · nhịp ${Math.round(k.nhip_ngay)} ngày` : undefined}>
              {k.ty_le_im_lang != null ? `${k.ty_le_im_lang.toFixed(1).replace(".", ",")}×` : "—"}</td>
            <td className="so">{gon(k.doanh_thu)}</td>
            <td>{tenNguoi(k.ten_sale, k.sale ?? "—")}</td>
            <td><span className={"nhan-vien " + ({ da_roi_bo: "do", canh_bao: "canh", binh_thuong: "ok" } as Record<string, string>)[k.trang_thai] || "nhat"}>
              {k.trang_thai === "da_roi_bo" ? "Gọi lại ngay" : k.trang_thai === "canh_bao" ? "Gọi lại trong tuần" : d.nhan[k.trang_thai]}</span></td>
          </tr>))}</tbody>
      </table></div>}
      <div className="phu" style={{ marginTop: ".4rem" }}>Im lặng = số ngày chưa mua ÷ nhịp mua riêng của khách, tính {nm}.{d?.so_sanh && !d.so_sanh.co ? ` ${d.so_sanh.nhan}: không có dữ liệu để so.` : ""}</div>
    </Khoi>
  );
}

// ---- Sản phẩm sắp hết hạn ---------------------------------------------------
type Lo = { ma: string; ten: string; kho: string; ten_kho: string | null; han: string; con_lai: number; so_luong: number; gia_tri: number };

export function KhoiHanSuDung() {
  const { data: d, isLoading, error } = useKhoi<{ can_han_ngay: number; lo: Lo[] }>("han_su_dung");
  const lo = d?.lo ?? [];
  const duoi30 = new Set(lo.filter(x => x.con_lai < 30).map(x => x.ma)).size;
  const xu = (c: number) => c < 0 ? ["Quá hạn — xử lý", "do"] : c < 30 ? ["Xả hàng ngay", "do"] : c < 60 ? ["Chào ưu tiên", "canh"] : ["Theo dõi", "nhat"];
  return (
    <Khoi tieu_de="Sản phẩm sắp hết hạn" nhan={lo.length ? `${duoi30} mã dưới 30 ngày` : undefined}
      phu={lo.length ? `giá trị tồn rủi ro ${yen(lo.reduce((s, x) => s + x.gia_tri, 0))}` : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/kho-hang" }}>
      {d && (lo.length ? <div className="bang-cuon" style={{ maxHeight: 360 }}><table className="bang">
        <thead><tr><th>Sản phẩm</th><th>Kho</th><th>Hạn dùng</th><th className="so">Còn lại</th><th className="so">Tồn</th><th className="so">Giá trị tồn</th><th>Xử lý</th></tr></thead>
        <tbody>{lo.map((x, i) => { const [chu, mau] = xu(x.con_lai); return (
          <tr key={i}><td><a href={`/san-pham/${x.ma}`}>{x.ten}</a><div className="ma-nho">{x.ma}</div></td>
            <td>{x.ten_kho || x.kho}</td><td className="so">{ngay(x.han)}</td>
            <td className={"so " + (x.con_lai < 30 ? "giam" : x.con_lai < 60 ? "canh-chu" : "")}><b>{x.con_lai} ngày</b></td>
            <td className="so">{so(x.so_luong)}</td><td className="so">{yen(x.gia_tri)}</td>
            <td><span className={"nhan-vien " + mau}>{chu}</span></td></tr>); })}</tbody>
      </table></div> : <div className="trong">Không lô nào hết hạn trong {d.can_han_ngay} ngày tới.</div>)}
    </Khoi>
  );
}

// ---- Hiệu suất theo ngành hàng ----------------------------------------------
type Nganh = { nganh: string; doanh_thu: number; lai_gop: number; ty_trong: number | null; ty_suat: number | null; cung_ky: number | null; co_cung_ky: boolean; tang_truong: number | null };

export function KhoiNganh() {
  const { data: d, isLoading, error } = useKhoi<{ thang: string | null; nganh: Nganh[]; khoang: KhoangMayChu | null }>("hieu_suat_nganh");
  const ss = d?.khoang?.so_sanh[0];
  const max = Math.max(0.0001, ...(d?.nganh ?? []).map(n => n.ty_trong ?? 0));
  return (
    <Khoi tieu_de="Hiệu suất theo ngành hàng" phu={d?.thang ? `${d.thang} · so ${ss?.nhan ?? "kỳ so"}${ss && !ss.co ? " (không có dữ liệu)" : ""}` : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}>
      {d && <div className="bang-cuon" style={{ maxHeight: 330 }}><table className="bang">
        <thead><tr><th>Ngành hàng</th><th>Tỷ trọng DT</th><th className="so">Doanh thu</th><th className="so">Biên gộp</th><th className="so">So {ss?.nhan ?? "kỳ so"}</th></tr></thead>
        <tbody>{d.nganh.map(n => (
          <tr key={n.nganh}><td>{n.nganh}</td>
            <td><span className="ty-trong"><span className="thanh-mong"><span style={{ width: `${(n.ty_trong ?? 0) / max * 100}%` }} /></span>{pc(n.ty_trong)}</span></td>
            <td className="so">{gon(n.doanh_thu)}</td><td className="so">{pc(n.ty_suat)}</td>
            <td className={"so " + ((n.tang_truong ?? 0) >= 0 ? "tang" : "giam")}>{n.tang_truong != null ? thay_doi(n.tang_truong) : n.co_cung_ky ? "—" : "chưa có"}</td></tr>))}</tbody>
      </table></div>}
    </Khoi>
  );
}

// ---- Doanh thu × tần suất mua -----------------------------------------------
type Cham = { ma: string; ten: string; doanh_thu: number; so_lan: number; trang_thai: string; ty_suat: number | null };

export function KhoiTuongQuan() {
  const { data: d, isLoading, error } = useKhoi<{ khach: Cham[]; khoang: KhoangMayChu | null }>("tuong_quan");
  const [tro, datTro] = useState<Cham | null>(null);
  const k = d?.khach ?? [];
  const W = 600, H = 240, l = 56, r = 586, t = 14, b = 200;
  const lx = (v: number) => Math.log10(Math.max(v, 1)), mxX = Math.max(1, ...k.map(x => lx(x.so_lan))), mxY = Math.max(1, ...k.map(x => lx(x.doanh_thu))), mnY = Math.min(mxY - 1, ...k.map(x => lx(x.doanh_thu)));
  const px = (x: Cham) => l + (r - l) * (lx(x.so_lan) / mxX), py = (x: Cham) => b - (b - t) * ((lx(x.doanh_thu) - mnY) / (mxY - mnY || 1));
  return (
    <Khoi tieu_de="Khách hàng theo doanh thu × tần suất mua" phu={`${d?.khoang?.nhan ?? ""} · mỗi chấm một khách · màu = trạng thái hôm nay · bấm để mở hồ sơ`} dang_tai={isLoading} loi={error?.message}>
      {d && <div className="bd" style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Biểu đồ phân tán doanh thu theo số lần mua của từng khách">
          <line x1={l} y1={t} x2={l} y2={b} className="bd-luoi" /><line x1={l} y1={b} x2={r} y2={b} className="bd-luoi" />
          {k.map(x => <circle key={x.ma} cx={px(x)} cy={py(x)} r={tro?.ma === x.ma ? 6 : 4} fill={MAU_TT[x.trang_thai] ?? LUC.nhat}
            opacity={tro && tro.ma !== x.ma ? 0.35 : 0.72} style={{ cursor: "pointer" }}
            onPointerEnter={() => datTro(x)} onPointerLeave={() => datTro(null)} onClick={() => { location.href = giuKhoang(`/khach-hang/${x.ma}`); }} />)}
          <text x={(l + r) / 2} y={H - 8} textAnchor="middle" className="bd-truc">Số ngày mua trong khoảng (thang log) →</text>
          <text x={12} y={(t + b) / 2} textAnchor="middle" className="bd-truc" transform={`rotate(-90 12 ${(t + b) / 2})`}>Doanh thu trong khoảng (log) →</text>
        </svg>
        {tro && <div className="bd-noi" style={{ left: `${Math.min(Math.max(px(tro) / W * 100, 15), 85)}%` }}>
          <strong className="ten-jp">{tro.ten}</strong><div>Doanh thu<b>{yen(tro.doanh_thu)}</b></div>
          <div>Số ngày mua<b>{so(tro.so_lan)}</b></div><div>Biên gộp<b>{pc(tro.ty_suat)}</b></div><em>bấm để mở hồ sơ</em></div>}
        <div className="bd-chu-giai">{Object.entries({ binh_thuong: "khoẻ", canh_bao: "cần theo dõi", da_roi_bo: "đang rời bỏ" }).map(([m, n]) =>
          <span key={m} className="phu"><i style={{ background: MAU_TT[m], borderRadius: "50%", width: 9, height: 9, display: "inline-block", marginRight: 4 }} />{n}</span>)}</div>
      </div>}
    </Khoi>
  );
}

// ---- Số khách đang mua theo kỳ ----------------------------------------------
export function KhoiTangTruong() {
  const { data: d, isLoading, error } = useKhoi<{ chon: number | null; ky: { company_fy: number; nhan: string; so_thang: number; so_khach: number; doanh_thu: number }[] }>("tang_truong");
  const ky = d?.ky ?? [];
  const cuoi = ky[ky.length - 1];
  return (
    <Khoi tieu_de="Số khách đang mua" phu="theo kỳ kế toán (1/8 → 31/7)" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}>
      {d && <>
        {cuoi && <div className="sk-dau">{so(cuoi.so_khach)} <span>khách có đơn · {cuoi.nhan}{cuoi.so_thang < 12 ? ` (${cuoi.so_thang} tháng)` : ""}</span></div>}
        <BieuDo nhan={ky.map(x => x.nhan.replace(/^Kỳ\s*/, "K"))} nhan_day_du={ky.map(x => `${x.nhan} · ${x.so_thang} tháng dữ liệu`)} cao={150}
          mo_ta="Số khách có đơn theo từng kỳ kế toán"
          chuoi={[{ ten: "Khách có đơn", kieu: "cot", gia_tri: ky.map(x => x.so_khach), mau: "var(--lien-ket)",
            mau_tung_cot: ky.map(x => x.company_fy === d.chon ? "var(--lien-ket)" : MO) }]}
          dinh_dang={v => `${so(v)} khách`} dinh_dang_truc={v => so(v)} />
        <div className="phu">Kỳ chưa đủ 12 tháng thì số khách thấp hơn — đừng so thẳng với kỳ đủ.</div>
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
  const [chiChuaMua, datChiChuaMua] = useState(false);
  const t = d?.thang ?? [];
  const ds = (d?.khach ?? []).filter(k => !chiChuaMua || !k.da_mua);
  return (
    <Khoi tieu_de="Khách mới đăng ký" phu={d?.khoang ? `${d.khoang.nhan} · theo ngày trong mã khách` : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}>
      {d && <>
        <div className="tn-dau">
          <div><b>{so(d.so_khach)}</b><span>khách mới đăng ký</span></div>
          <div className="phu">Đã có đơn: <b>{so(d.da_mua)}</b> · chưa có đơn: <b className={d.chua_mua ? "canh-chu" : ""}>{so(d.chua_mua)}</b></div>
          {d.so_sanh.map(s => <DongSoSanh key={s.ma} className="phu" nhan={s.nhan} co={s.co && s.so_khach != null}
            nay={s.so_khach_nay} ss={s.so_khach} dinh_dang={v => `${so(v)} khách`} />)}
        </div>
        <BieuDo nhan={t.map(x => thang_nhan(x.thang))} nhan_day_du={t.map(x => `Tháng ${thang_nhan(x.thang)}`)} cao={130}
          mo_ta="Số khách mới đăng ký từng tháng, 12 tháng gần nhất, và số đã có đơn"
          chuoi={[
            { ten: "Đăng ký", kieu: "cot_nen", gia_tri: t.map(x => x.so_khach), mau: "var(--vien)", so_voi: t.some(x => x.so_khach_ss != null) ? 2 : undefined },
            { ten: "Đã có đơn", kieu: "cot", gia_tri: t.map(x => x.da_mua), mau: "var(--lien-ket)",
              mau_tung_cot: t.map(x => trongKhoang(d.khoang, x.thang) ? "var(--lien-ket)" : MO) },
            // Đã có hai lớp cột -> kỳ so là NÉT ĐỨT, không thêm lớp cột thứ ba (đặc tả §6).
            ...(t.some(x => x.so_khach_ss != null) ? [{ ten: `Đăng ký · ${d.ss?.nhan ?? "kỳ so"}`, kieu: "duong_dut" as const,
              gia_tri: t.map(x => x.so_khach_ss), mau: MAU_SS }] : []),
          ]}
          dinh_dang={v => `${so(v)} khách`} dinh_dang_truc={v => so(v)} />
        <div style={{ margin: ".4rem 0" }}>
          <button type="button" className="chip" aria-pressed={chiChuaMua} onClick={() => datChiChuaMua(c => !c)}>
            Chỉ khách chưa có đơn ({so(d.chua_mua)})</button></div>
        <div className="bang-cuon" style={{ maxHeight: 300 }}><table className="bang">
          <thead><tr><th>Khách hàng</th><th>Đăng ký</th><th>Đơn đầu</th><th className="so">Doanh thu</th><th>Phụ trách</th></tr></thead>
          <tbody>{ds.map(k => (
            <tr key={k.ma}>
              <td className="ten-jp"><a href={`/khach-hang/${k.ma}`}>{k.ten}</a><div className="ma-nho">{k.ma}{k.da_ngung ? " · OBC đánh dấu ngừng" : ""}</div></td>
              <td className="so">{ngay(k.ngay_dang_ky)}</td>
              <td className="so">{k.lan_dau ? ngay(k.lan_dau) : <span className="nhan-vien canh">Chưa có đơn</span>}</td>
              <td className="so">{k.da_mua ? yen(k.doanh_thu) : "—"}</td>
              <td>{k.sale ? tenNguoi(k.ten_sale, k.sale) : "—"}</td>
            </tr>))}</tbody></table>
          {!ds.length && <div className="trong">{d.so_khach ? "Mọi khách mới đều đã có đơn." : "Không có khách mới đăng ký trong khoảng này."}</div>}
          {d.so_khach > d.khach.length && <div className="phu">Hiện {so(d.khach.length)}/{so(d.so_khach)} khách mới nhất.</div>}
        </div>
        <div className="phu" style={{ marginTop: ".4rem" }}>{d.cach_tinh}</div>
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
    <Khoi tieu_de="Biên lợi nhuận theo quý" phu="biên gộp = tổng lãi gộp ÷ tổng doanh thu thuần" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}>
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
        <div className="phu">{ss && !coSs ? (d.so_quy == null ? `${hoa(ss.nhan)} không lệch tròn quý — không so theo quý được. ` : `${hoa(ss.nhan)}: không có dữ liệu để so. `) : ""}
          Biên RÒNG của gói thiết kế chưa có — cần chi phí vận hành, chưa có nguồn.</div>
      </>}
    </Khoi>
  );
}

// ---- Việc cần làm hôm nay ---------------------------------------------------
type Viec = { muc: "gap" | "canh" | "thuong"; tag: string; chu: string; lien_ket: string; han: string | null };

export function KhoiViec() {
  const [tatCa, datTatCa] = useState(false);
  const { data: d, isLoading, error } = useKhoi<{ viec: Viec[]; thieu_nguon: string[] }>("viec_hom_nay", true, tatCa ? "tat_ca=1" : "");
  const khoa = `kome_viec_xong_${new Date().toISOString().slice(0, 10)}`;
  const [xong, datXong] = useState<Record<string, boolean>>(() => { try { return JSON.parse(localStorage.getItem(khoa) || "{}"); } catch { return {}; } });
  const v = d?.viec ?? [];
  const soXong = v.filter(x => xong[x.chu]).length;
  const bat = (c: string) => { const m = { ...xong, [c]: !xong[c] }; datXong(m); try { localStorage.setItem(khoa, JSON.stringify(m)); } catch { /* */ } };
  return (
    <Khoi tieu_de="Việc cần làm hôm nay" dang_tai={isLoading} loi={error?.message}
      phu={<span className="viec-tt">{soXong}/{v.length} xong
        <span className="thanh-mong" style={{ width: 90 }}><span style={{ width: `${v.length ? soXong / v.length * 100 : 0}%`, background: LUC.ok }} /></span>
        {KD.nguoi?.sale && <button type="button" className="chip" aria-pressed={!tatCa} onClick={() => datTatCa(t => !t)}>{tatCa ? "Việc của mọi người" : "Chỉ việc của tôi"}</button>}
      </span>}>
      {d && <div className="viec-ds">
        {v.map(x => (
          <div key={x.chu} className={"viec-dong" + (xong[x.chu] ? " xong" : "")}>
            <input type="checkbox" checked={!!xong[x.chu]} onChange={() => bat(x.chu)} aria-label={`Đánh dấu xong: ${x.chu}`} />
            <span className={"nhan-vien " + (x.muc === "gap" ? "do" : x.muc === "canh" ? "canh" : "nhat")}>{x.tag}</span>
            <span className="viec-chu">{x.chu}</span>
            {x.han && <span className="viec-han">{x.han}</span>}
            <a href={x.lien_ket}>Mở →</a>
          </div>))}
        {!v.length && <div className="trong">Không có việc nào hôm nay.</div>}
        <div className="phu" style={{ marginTop: ".5rem" }}>Chưa gom được việc từ {d.thieu_nguon.join(", ")} — chưa có nguồn dữ liệu. Dấu "xong" chỉ nhớ trên máy này, trong hôm nay.</div>
      </div>}
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
      phu={d?.thang ? <>tháng {thang_nhan(d.thang)} · tính đến {ngay(d.ngay_moc)}
        {KD.nguoi?.sale && <button type="button" className="chip" aria-pressed={!tatCa} onClick={() => datTatCa(t => !t)}
          style={{ marginLeft: ".4rem" }}>{tatCa ? "Khách của mọi người" : "Chỉ khách của tôi"}</button>}</> : undefined}
      lien_ket={{ href: `/lien-he?ly_do=thang_nay_chua_mua${giu}` }}>
      {d && <>
        <div className="tn-dau">
          <div><b>{so(d.dem.tre ?? 0)}</b><span>khách mua đều, tháng này chưa có đơn</span></div>
          <div className="phu">Đã mua tháng này: <b>{so(da)}</b> khách
            {truoc > 0 && <> · tháng trước đến cùng ngày: {so(truoc)} <span className={da >= truoc ? "tang" : "giam"}>({thay_doi(da / truoc - 1, 0)})</span></>}</div>
          {(d.dem.chua_toi_ngay ?? 0) > 0 &&
            <div className="phu nhat-chu">+ {so(d.dem.chua_toi_ngay)} khách mua đều nhưng thường mua muộn hơn trong tháng — chưa tới ngày.</div>}
        </div>
        <div className="bang-cuon"><table className="bang">
          <thead><tr><th>Khách hàng</th><th className="so">TB/tháng</th><th className="so">Tháng trước</th></tr></thead>
          <tbody>{d.khach.map(k => (
            <tr key={k.ma}>
              <td className="ten-jp"><a href={`/khach-hang/${k.ma}`}>{k.ten}</a><div className="ma-nho">mua {k.so_thang}/3 tháng trước</div></td>
              <td className="so">{gon(k.tb_thang)}</td><td className="so">{gon(k.thang_truoc)}</td>
            </tr>))}</tbody></table>
          {!d.khach.length && <div className="trong">Không có khách mua đều nào đang trễ tháng này.</div>}
        </div>
        <div className="phu" style={{ marginTop: ".4rem" }}>{d.cach_tinh} Bộ đếm là của cả công ty; danh sách xếp theo trung bình mỗi tháng.</div>
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
          <table className="bang"><tbody>{d.lo.map((x, i) => (
            <tr key={i}><td>{x.loai}<div className="ma-nho">{x.ten_file}</div></td><td className="so">{so(x.so_dong)} dòng</td>
              <td className="so nhat-chu">{gio_tokyo(x.nap_luc)}</td></tr>))}</tbody></table></div>
        <div><div className="tieu-muc">PHIẾU BÁN MỚI NHẤT</div>
          <table className="bang"><tbody>{d.phieu.map(x => (
            <tr key={x.so}><td className="nhat-chu">{ngay_ngan(x.ngay)}</td><td className="ten-jp"><a href={`/khach-hang/${x.ma}`}>{x.ten}</a></td>
              <td className="so">{yen(x.tien)}</td></tr>))}</tbody></table></div>
      </div>}
    </Khoi>
  );
}

// ---- Bảng tra mã khối -> thành phần ------------------------------------------
export const VE: Record<string, () => React.ReactElement> = {
  kpi: () => <KhoiKpi />, ns_thang: () => <KhoiNganSach />, theo_thang: () => <KhoiTheoThang />,
  viec_hom_nay: () => <KhoiViec />, xu_huong: () => <KhoiXuHuong />, suc_khoe_khach: () => <KhoiSucKhoe />,
  danh_sach_khach: () => <KhoiDanhSachKhach />, han_su_dung: () => <KhoiHanSuDung />, hieu_suat_nganh: () => <KhoiNganh />,
  so_sanh_sale: () => <KhoiSale />, tuong_quan: () => <KhoiTuongQuan />, tang_truong: () => <KhoiTangTruong />,
  bien_loi_nhuan: () => <KhoiBien />, don_hang: () => <KhoiNap />,
  thang_nay_chua_mua: () => <KhoiThangNay />, cong_no: () => <KhoiCongNo />, khach_moi: () => <KhoiKhachMoi />,
};

export function veKhoi(id: string, nhan: string) {
  const f = VE[id];
  if (f) return f();
  return <ChuaCoDuLieu tieu_de={nhan} ly_do={KD.chua_co[id] ?? "Chưa có nguồn dữ liệu cho khối này."} />;
}
