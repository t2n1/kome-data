// Các khối của Tổng quan — bố cục theo Dashboard.dc.html, số THẬT từ
// /api/tong-quan/<khối> (kome/khoi_tong_quan.py). Không số mẫu ở đâu cả.
import { useMemo, useState } from "react";
import { useKhoi } from "../api";
import { BieuDo, type Chuoi } from "../chung/BieuDo";
import { ChuaCoDuLieu, Khoi, Spark, ThanhMoc, mauTienDo } from "../chung/Khoi";
import { gon, ngay, ngay_ngan, pc, so, thang_nhan, thay_doi, yen } from "../dinh_dang";
import { KD } from "../khoi_dau";

const LUC = { ok: "var(--ok-vien)", canh: "var(--lien-ket)", do: "var(--do)", nhat: "var(--chu-mo)", nen: "var(--vien)" };
const tenNguoi = (ten: string | null | undefined, ma: string) => ten || `(mã ${ma})`;

// ---- Chỉ số hôm nay ---------------------------------------------------------
type Kpi = {
  doanh_thu: { gia_tri: number; tu_ngay: string | null; den_ngay: string | null; cung_ky: number | null; tang: number | null; spark: number[] };
  ngan_sach: null | { tien_do: number | null; thuc_te: number; muc_tieu: number | null; muc_tieu_den_hom_nay: number | null; moc: number | null; spark: number[]; thang: string };
  kho: { het_hang: number; can_han: number; qua_han: number };
  khach: { can_goi: number; roi_bo: number };
};

export function KhoiKpi() {
  const { data: d, isLoading, error } = useKhoi<Kpi>("kpi");
  return (
    <Khoi tieu_de="Chỉ số hôm nay" dang_tai={isLoading} loi={error?.message}
      phu={d?.doanh_thu.tu_ngay ? `tháng ${ngay(d.doanh_thu.tu_ngay)} – ${ngay(d.doanh_thu.den_ngay)}` : undefined}>
      {d && <div className="o-kpi-luoi">
        <a className="o-kpi" href="/bao-cao">
          <div className="nhan">Doanh thu tháng đến hôm nay</div>
          <div className="gia">{yen(d.doanh_thu.gia_tri)}</div>
          <div className={"dong-phu " + ((d.doanh_thu.tang ?? 0) >= 0 ? "tang" : "giam")}>
            {d.doanh_thu.tang != null ? `${thay_doi(d.doanh_thu.tang)} so cùng kỳ năm trước` : "chưa có cùng kỳ để so"}</div>
          <Spark gia_tri={d.doanh_thu.spark} mau={(d.doanh_thu.tang ?? 0) >= 0 ? LUC.ok : LUC.do} />
        </a>
        <a className="o-kpi" href={KD.hien_ngan_sach ? "/ngan-sach" : "/bao-cao"}>
          <div className="nhan">Tiến độ ngân sách {d.ngan_sach ? thang_nhan(d.ngan_sach.thang) : ""}</div>
          {d.ngan_sach ? <>
            <div className="gia">{pc(d.ngan_sach.tien_do)}</div>
            <div className="dong-phu" style={{ color: mauTienDo(d.ngan_sach.tien_do, d.ngan_sach.moc) }}>
              {d.ngan_sach.muc_tieu_den_hom_nay != null && d.ngan_sach.thuc_te < d.ngan_sach.muc_tieu_den_hom_nay
                ? `thiếu ${gon(d.ngan_sach.muc_tieu_den_hom_nay - d.ngan_sach.thuc_te)} so mốc ${pc(d.ngan_sach.moc)}`
                : `vượt mốc ${pc(d.ngan_sach.moc)}`}</div>
            <Spark gia_tri={d.ngan_sach.spark} mau={mauTienDo(d.ngan_sach.tien_do, d.ngan_sach.moc)} />
          </> : <><div className="gia nhat-chu" style={{ fontSize: "1rem" }}>Chưa đặt chỉ tiêu</div>
            <div className="dong-phu nhat-chu">đặt ở màn Ngân sách</div></>}
        </a>
        <OKpiCongNo />
        <div className="o-kpi chua" title={KD.chua_co.dong_tien}>
          <div className="nhan">Phải trả 7 ngày tới</div><div className="gia">chưa có dữ liệu</div>
          <div className="dong-phu nhat-chu">cần sổ phải trả</div></div>
        <a className="o-kpi" href="/kho-hang">
          <div className="nhan">Kho cần xử lý</div>
          <div className="gia">{so(d.kho.het_hang + d.kho.can_han + d.kho.qua_han)}</div>
          <div className={"dong-phu " + (d.kho.het_hang + d.kho.qua_han ? "giam" : "canh-chu")}>
            {d.kho.het_hang} mã hết hàng · {d.kho.can_han} lô cận hạn · {d.kho.qua_han} lô quá hạn</div>
        </a>
        <a className="o-kpi" href="/lien-he?tat_ca=1">
          <div className="nhan">Khách cần gọi</div>
          <div className="gia">{so(d.khach.can_goi + d.khach.roi_bo)}</div>
          <div className="dong-phu canh-chu">{d.khach.can_goi} im lặng quá nhịp · {d.khach.roi_bo} đã rời bỏ</div>
        </a>
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
  if (isLoading) return <div className="o-kpi"><div className="nhan">Phải thu quá hạn</div><div className="gia nhat-chu">…</div></div>;
  if (!d) return (
    <div className="o-kpi chua" title="Chưa nạp sổ 請求先元帳 nào."><div className="nhan">Phải thu quá hạn</div>
      <div className="gia">chưa có dữ liệu</div><div className="dong-phu nhat-chu">chưa nạp sổ công nợ</div></div>);
  return (
    <a className="o-kpi" href="/cong-no?tab=qua_han">
      <div className="nhan">Phải thu quá hạn</div><div className={"gia" + (d.tq.qua_han ? " giam" : "")}>{gon(d.tq.qua_han)}</div>
      <div className="dong-phu nhat-chu">{d.tq.so_phieu_qua_han} phiếu · tổng phải thu {gon(d.tq.tong_phai_thu)} · đến {ngay_ngan(d.moc)}</div></a>);
}

export function KhoiCongNo() {
  const { data: d, isLoading, error } = useKhoi<CongNo>("cong_no");
  if (!isLoading && !error && !d) return <ChuaCoDuLieu tieu_de="Tuổi nợ phải thu" ly_do="Chưa nạp sổ 請求先元帳 nào — xuất từ OBC rồi nạp ở màn Kho dữ liệu." />;
  const max = Math.max(1, ...(d?.tq.tuoi ?? []).map(t => t.tien));
  return (
    <Khoi tieu_de="Tuổi nợ phải thu" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/cong-no" }}
      phu={d ? `tổng ${yen(d.tq.tong_phai_thu)} · tính đến ${ngay(d.moc)}` : undefined}>
      {d && <>
        <div className="tuoi-no">{d.tq.tuoi.map(t => (
          <a key={t.nhom} className="tuoi-no-dong" href={`/cong-no?nhom=${t.nhom}`}>
            <span className="nhat-chu">{t.nhan}</span>
            <span className="tuoi-no-thanh"><i style={{ width: `${Math.max(2, t.tien / max * 100)}%`, background: MAU_TUOI[t.nhom] }} /></span>
            <b className="so">{gon(t.tien)}</b></a>))}</div>
        {d.lau_nhat.length > 0 && <><div className="tieu-muc">NỢ LÂU / QUÁ HẠN NHIỀU NHẤT</div>
          <table className="bang"><tbody>{d.lau_nhat.map(x => (
            <tr key={x.ma}><td className="ten-jp"><a href={`/cong-no?tim=${encodeURIComponent(x.ma)}`}>{x.ten}</a></td>
              <td className="so">{yen(x.tien)}</td></tr>))}</tbody></table></>}
        <p className="phu" style={{ fontSize: ".72rem" }}>{d.cach_tinh}</p>
      </>}
    </Khoi>
  );
}

// ---- Tiến độ ngân sách tháng ------------------------------------------------
type NguoiNS = { ma: string; ten: string | null; thuc_te: number; muc_tieu: number | null; muc_tieu_den_hom_nay: number | null; tien_do: number | null };
type NganSach = {
  thang: string; co_ngan_sach: boolean; thuc_te: number; muc_tieu: number | null; muc_tieu_den_hom_nay: number | null;
  tien_do: number | null; moc: number | null; ngay_kd: number; ngay_kd_da_qua: number; ngay_kd_con_lai: number;
  can_ban_moi_ngay: number | null; nhip_chuan: number | null; nguoi: NguoiNS[];
};

export function KhoiNganSach() {
  const { data: d, isLoading, error } = useKhoi<NganSach | null>("ns_thang");
  const nguoi = [...(d?.nguoi ?? [])].sort((a, b) => b.thuc_te - a.thuc_te);
  const maxNS = Math.max(1, ...nguoi.map(n => Math.max(n.muc_tieu ?? 0, n.thuc_te)));
  return (
    <Khoi tieu_de={`Tiến độ ngân sách tháng ${d ? thang_nhan(d.thang).slice(1) : ""}`} dang_tai={isLoading} loi={error?.message}
      nhan={d ? `Còn ${d.ngay_kd_con_lai} ngày làm việc` : undefined} lien_ket={{ href: "/bao-cao", chu: "Xem chi tiết" }}>
      {d && <div className="ns-luoi">
        <div className="ns-so">
          {d.co_ngan_sach ? <>
            <div><div className="nhan">Tiến độ tháng</div>
              <div className="gia" style={{ color: mauTienDo(d.tien_do, d.moc) }}>{pc(d.tien_do)}</div>
              <div className="phu">mốc hôm nay {pc(d.moc)}</div></div>
            <div><div className="nhan">{d.muc_tieu_den_hom_nay != null && d.thuc_te >= d.muc_tieu_den_hom_nay ? "Vượt mốc" : "Thiếu so mốc"}</div>
              <div className="gia" style={{ color: d.muc_tieu_den_hom_nay != null && d.thuc_te >= d.muc_tieu_den_hom_nay ? LUC.ok : LUC.do }}>
                {yen(Math.abs((d.muc_tieu_den_hom_nay ?? 0) - d.thuc_te))}</div>
              <div className="phu">trên ngân sách {yen(d.muc_tieu)}</div></div>
            <div><div className="nhan">Cần bán mỗi ngày</div>
              <div className="gia">{yen(d.can_ban_moi_ngay)}</div>
              <div className="phu">{d.can_ban_moi_ngay != null && d.nhip_chuan ? `gấp ${(d.can_ban_moi_ngay / d.nhip_chuan).toFixed(2).replace(".", ",")}× nhịp chuẩn` : "tháng đã hết ngày làm việc"}</div></div>
          </> : <>
            <div><div className="nhan">Đã bán tháng này</div><div className="gia">{yen(d.thuc_te)}</div>
              <div className="phu">{d.ngay_kd_da_qua}/{d.ngay_kd} ngày làm việc</div></div>
            <div className="chua-co" style={{ padding: ".55rem .7rem" }}><p>Chưa đặt chỉ tiêu tháng này.</p>
              {KD.hien_ngan_sach && <p><a href="/ngan-sach">Đặt chỉ tiêu →</a></p>}</div>
          </>}
        </div>
        <div className="ns-thanh">
          {nguoi.map(n => (
            <div key={n.ma}>
              <div className="ns-dong"><span>{tenNguoi(n.ten, n.ma)}</span>
                <b style={{ color: mauTienDo(n.tien_do, d.moc) }}>{n.muc_tieu ? pc(n.tien_do) : yen(n.thuc_te)}</b></div>
              <div className="ns-ba-lop">
                <div className="lop-ns" style={{ width: `${(n.muc_tieu ?? 0) / maxNS * 100}%` }} />
                <div className="lop-tt" style={{ width: `${Math.min(n.thuc_te / maxNS, 1) * 100}%`, background: n.muc_tieu ? mauTienDo(n.tien_do, d.moc) : LUC.nhat }} />
                {n.muc_tieu_den_hom_nay != null && <div className="lop-moc" style={{ left: `${n.muc_tieu_den_hom_nay / maxNS * 100}%` }} />}
              </div>
            </div>))}
          {d.co_ngan_sach && <div>
            <div className="ns-dong"><span>Toàn nhóm</span><b style={{ color: mauTienDo(d.tien_do, d.moc) }}>{pc(d.tien_do)}</b></div>
            <ThanhMoc ty_le={d.tien_do} moc={d.moc} mau={mauTienDo(d.tien_do, d.moc)} />
          </div>}
          <div className="phu">{d.co_ngan_sach ? `Vạch đen = mốc đáng lẽ đạt tới hôm nay (${pc(d.moc)}) — tính theo ngày làm việc, trừ ngày lễ.` : "Thanh = doanh thu thực tế của từng người phụ trách."}</div>
        </div>
      </div>}
    </Khoi>
  );
}

// ---- Doanh thu theo sale ----------------------------------------------------
export function KhoiSale() {
  const { data: d, isLoading, error } = useKhoi<NganSach | null>("so_sanh_sale");
  const nguoi = [...(d?.nguoi ?? [])].sort((a, b) => b.thuc_te - a.thuc_te);
  const max = Math.max(1, ...nguoi.map(n => n.thuc_te));
  return (
    <Khoi tieu_de="Doanh thu theo sale" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}>
      {d && <div className="sale-ds">
        {nguoi.map(n => (
          <div key={n.ma}>
            <div className="ns-dong"><span>{tenNguoi(n.ten, n.ma)}</span><span className="so-nhat">{gon(n.thuc_te)}</span>
              {n.muc_tieu ? <b style={{ color: mauTienDo(n.tien_do, d.moc) }}>{pc(n.tien_do)}</b> : <em className="nhat-chu">chưa có chỉ tiêu</em>}</div>
            <div className="thanh-mong"><div style={{ width: `${n.muc_tieu ? Math.min(n.tien_do ?? 0, 1) * 100 : n.thuc_te / max * 100}%`,
              background: n.muc_tieu ? mauTienDo(n.tien_do, d.moc) : LUC.canh }} /></div>
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
  const { data: d, isLoading, error } = useKhoi<{ company_fy: number | null; thang: Thang[]; hom_nay: string }>("theo_thang");
  const t = d?.thang ?? [];
  const thangNay = d?.hom_nay.slice(0, 7);
  const tong = t.reduce((s, x) => s + x.doanh_thu, 0);
  const coCK = t.filter(x => x.cung_ky != null && x.thang !== thangNay);
  const dtCK = coCK.reduce((s, x) => s + x.doanh_thu, 0), ck = coCK.reduce((s, x) => s + (x.cung_ky ?? 0), 0);
  const coNS = t.filter(x => x.ngan_sach != null && x.thang !== thangNay);
  const dat = coNS.filter(x => x.doanh_thu >= (x.ngan_sach ?? 0)).length;
  const cao = t.length ? t.reduce((a, b) => (b.doanh_thu > a.doanh_thu ? b : a)) : null;
  const chuoi: Chuoi[] = [
    { ten: "Cùng kỳ năm trước", kieu: "cot_nen", gia_tri: t.map(x => x.cung_ky), mau: "var(--vien)" },
    { ten: "Doanh thu", kieu: "cot", gia_tri: t.map(x => x.doanh_thu), mau: LUC.do,
      mau_tung_cot: t.map(x => x.ngan_sach == null ? "var(--lien-ket)" : x.doanh_thu >= x.ngan_sach ? LUC.do : "color-mix(in srgb, var(--do) 50%, var(--nen-the))") },
    { ten: "Ngân sách tháng", kieu: "duong", gia_tri: t.map(x => x.ngan_sach), mau: "var(--lien-ket)" },
  ];
  return (
    <Khoi tieu_de="Kết quả theo từng tháng" phu={d?.company_fy ? `Kỳ ${d.company_fy} · so ngân sách và cùng kỳ năm trước` : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao", chu: "Xem báo cáo tháng" }}>
      {d && <>
        <div className="so-khoi o-vien">
          <div><div className="nhan">Luỹ kế {t.length ? `${thang_nhan(t[0].thang)} – ${thang_nhan(t[t.length - 1].thang)}` : ""}</div>
            <div className="gia">{gon(tong)}</div><div className="phu">{t.length} tháng có dữ liệu</div></div>
          <div><div className="nhan">So cùng kỳ ({coCK.length} tháng đối chiếu)</div>
            <div className={"gia " + (dtCK >= ck ? "tang" : "giam")}>{ck ? thay_doi(dtCK / ck - 1) : "—"}</div>
            <div className="phu">{ck ? `chênh ${gon(dtCK - ck)}` : "chưa có cùng kỳ"}</div></div>
          <div><div className="nhan">Tháng đạt ngân sách</div>
            <div className="gia">{coNS.length ? `${dat}/${coNS.length}` : "—"}</div>
            <div className="phu">{coNS.length ? "tháng đã khép lại" : "chưa đặt chỉ tiêu tháng nào"}</div></div>
          <div><div className="nhan">Tháng cao nhất</div><div className="gia">{cao ? thang_nhan(cao.thang) : "—"}</div>
            <div className="phu">{cao ? `${gon(cao.doanh_thu)} · biên gộp ${pc(cao.ty_suat)}` : ""}</div></div>
        </div>
        <div className="hai-cot-tt">
          <BieuDo nhan={t.map(x => thang_nhan(x.thang))} chuoi={chuoi} cao={190} mo_ta="Doanh thu từng tháng của kỳ so ngân sách và cùng kỳ"
            dinh_dang={v => yen(v)} dinh_dang_truc={v => gon(v)}
            vach={thangNay ? { i: t.findIndex(x => x.thang === thangNay), chu: "đang chạy" } : null} />
          <div className="bang-cuon"><table className="bang">
            <thead><tr><th>Tháng</th><th className="so">Doanh thu</th><th className="so">Ngân sách</th><th className="so">%NS</th>
              <th className="so">So cùng kỳ</th><th className="so">Biên gộp</th><th className="so">Khách</th></tr></thead>
            <tbody>{t.map(x => (
              <tr key={x.thang} className={x.thang === thangNay ? "dang-chay" : ""}>
                <td>{thang_nhan(x.thang)}{x.thang === thangNay && <em className="nhat-chu"> · đang chạy</em>}</td>
                <td className="so">{gon(x.doanh_thu)}</td><td className="so">{gon(x.ngan_sach)}</td>
                <td className={"so " + (x.ngan_sach ? (x.doanh_thu >= x.ngan_sach ? "tang" : "giam") : "")}>{x.ngan_sach ? pc(x.doanh_thu / x.ngan_sach, 0) : "—"}</td>
                <td className={"so " + (x.cung_ky ? (x.doanh_thu >= x.cung_ky ? "tang" : "giam") : "")}>{x.cung_ky ? thay_doi(x.doanh_thu / x.cung_ky - 1) : "—"}</td>
                <td className="so">{pc(x.ty_suat)}</td><td className="so">{so(x.so_khach)}</td>
              </tr>))}</tbody>
          </table>
          {thangNay && t.some(x => x.thang === thangNay) && <div className="phu" style={{ marginTop: ".45rem" }}>Tháng đang chạy chưa đủ ngày — %NS và so cùng kỳ của tháng này chưa so ngang được.</div>}
          </div>
        </div>
      </>}
    </Khoi>
  );
}

// ---- Xu hướng doanh thu -----------------------------------------------------
const KHUNG = [["7N", 7], ["30N", 30], ["90N", 90], ["1N", 365]] as const;

export function KhoiXuHuong() {
  const { data: d, isLoading, error } = useKhoi<{ ngay: [string, number, number, number][] }>("xu_huong");
  const [k, datK] = useState(30);
  const ds = d?.ngay ?? [];
  const nay = ds.slice(-k), truoc = ds.slice(-2 * k, -k);
  const tong = nay.reduce((s, x) => s + x[1], 0), tongTruoc = truoc.reduce((s, x) => s + x[1], 0);
  const coNgay = nay.filter(x => x[1] !== 0).length;
  const gop = k > 90 ? 7 : 1;   // 1 năm: gộp theo tuần cho dễ đọc
  const nhom = <T,>(a: T[]) => Array.from({ length: Math.ceil(a.length / gop) }, (_, i) => a.slice(i * gop, (i + 1) * gop));
  const nayG = nhom(nay), truocG = nhom(truoc);
  return (
    <Khoi tieu_de="Xu hướng doanh thu" dang_tai={isLoading} loi={error?.message}
      phu={<span className="tab-pill" role="group" aria-label="Khung thời gian">{KHUNG.map(([n, s]) =>
        <button key={n} type="button" aria-pressed={k === s} onClick={() => datK(s)}>{n}</button>)}</span>}>
      {d && <>
        <div className="xh-so">
          <div><div className="nhan">TỔNG {k} NGÀY</div><div className="gia">{gon(tong)}</div></div>
          <div><div className="nhan">SO {k} NGÀY TRƯỚC</div><div className={"gia " + (tong >= tongTruoc ? "tang" : "giam")}>{tongTruoc ? thay_doi(tong / tongTruoc - 1) : "—"}</div></div>
          <div><div className="nhan">TRUNG BÌNH / NGÀY CÓ BÁN</div><div className="gia">{gon(coNgay ? tong / coNgay : null)}</div></div>
        </div>
        <BieuDo nhan={nayG.map(g => ngay_ngan(g[0][0]))} nhan_day_du={nayG.map(g => g.length > 1 ? `Tuần ${ngay(g[0][0])} – ${ngay(g[g.length - 1][0])}` : ngay(g[0][0]))}
          cao={200} mo_ta={`Doanh thu ${k} ngày gần nhất so với ${k} ngày liền trước`}
          chuoi={[
            { ten: k <= 30 ? "Doanh thu ngày" : "Doanh thu", kieu: k <= 30 ? "cot" : "duong", gia_tri: nayG.map(g => g.reduce((s, x) => s + x[1], 0)), mau: "var(--lien-ket)" },
            { ten: "Kỳ trước", kieu: "duong_dut", gia_tri: nayG.map((_, i) => truocG[i] ? truocG[i].reduce((s, x) => s + x[1], 0) : null), mau: "var(--vien-dam)" },
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
  const tong = d ? d.nhom.reduce((s, n) => s + (d.dem[n] ?? 0), 0) : 0;
  const hd = d ? (d.dem.binh_thuong ?? 0) + (d.dem.canh_bao ?? 0) : 0;
  return (
    <Khoi tieu_de="Sức khoẻ khách hàng" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}>
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
  trang_thai: string; so_ngay_im_lang: number | null; nhip_ngay: number | null; thang_nay: number; thang_truoc: number };
const UU_TIEN: Record<string, number> = { da_roi_bo: 0, canh_bao: 1, binh_thuong: 2, chua_du_lich_su: 3, ngung_giao_dich: 4 };
type CotSap = "can" | "ten" | "thang_nay" | "thang_truoc" | "ty_le" | "doanh_thu";

export function KhoiDanhSachKhach() {
  const { data: d, isLoading, error } = useKhoi<{ khach: KhachDS[]; nhan: Record<string, string> }>("danh_sach_khach");
  const [sap, datSap] = useState<{ cot: CotSap; giam: boolean }>({ cot: "can", giam: false });
  const ds = useMemo(() => {
    const a = [...(d?.khach ?? [])];
    const g = (k: KhachDS): number | string => sap.cot === "can" ? (UU_TIEN[k.trang_thai] ?? 9) * 1e12 - k.doanh_thu
      : sap.cot === "ten" ? k.ten : sap.cot === "ty_le" ? (k.ty_le_im_lang ?? -1) : k[sap.cot];
    a.sort((x, y) => { const p = g(x), q = g(y); const r = p < q ? -1 : p > q ? 1 : 0; return sap.giam ? -r : r; });
    return a;
  }, [d, sap]);
  const th = (cot: CotSap, chu: string, so_ = false) => (
    <th className={"sap" + (so_ ? " so" : "")} aria-sort={sap.cot === cot ? (sap.giam ? "descending" : "ascending") : "none"}
      onClick={() => datSap(s => ({ cot, giam: s.cot === cot ? !s.giam : cot !== "ten" && cot !== "can" }))}>
      {chu}{sap.cot === cot ? (sap.giam ? " ↓" : " ↑") : ""}</th>);
  return (
    <Khoi tieu_de="Danh sách khách hàng" phu="bấm tiêu đề cột để sắp xếp · 60 khách doanh thu cao nhất" dang_tai={isLoading} loi={error?.message}
      lien_ket={{ href: "/khach-hang?tat_ca=1" }}>
      {d && <div className="bang-cuon" style={{ maxHeight: 420 }}><table className="bang">
        <thead><tr>{th("ten", "Khách hàng")}{th("thang_nay", "Tháng này", true)}{th("thang_truoc", "Tháng trước", true)}
          <th className="so">So tháng trước</th>{th("ty_le", "Im lặng", true)}{th("doanh_thu", "Doanh thu tích luỹ", true)}<th>Phụ trách</th>{th("can", "Cần làm")}</tr></thead>
        <tbody>{ds.map(k => (
          <tr key={k.ma}>
            <td className="ten-jp"><a href={`/khach-hang/${k.ma}`}>{k.ten}</a></td>
            <td className="so">{yen(k.thang_nay)}</td><td className="so">{yen(k.thang_truoc)}</td>
            <td className={"so " + (k.thang_truoc ? (k.thang_nay >= k.thang_truoc ? "tang" : "giam") : "")}>{k.thang_truoc ? thay_doi(k.thang_nay / k.thang_truoc - 1, 0) : "—"}</td>
            <td className={"so " + ((k.ty_le_im_lang ?? 0) >= 2 ? "giam" : (k.ty_le_im_lang ?? 0) >= 1 ? "canh-chu" : "")} title={k.nhip_ngay ? `im ${k.so_ngay_im_lang} ngày · nhịp ${Math.round(k.nhip_ngay)} ngày` : undefined}>
              {k.ty_le_im_lang != null ? `${k.ty_le_im_lang.toFixed(1).replace(".", ",")}×` : "—"}</td>
            <td className="so">{gon(k.doanh_thu)}</td>
            <td>{tenNguoi(k.ten_sale, k.sale ?? "—")}</td>
            <td><span className={"nhan-vien " + ({ da_roi_bo: "do", canh_bao: "canh", binh_thuong: "ok" } as Record<string, string>)[k.trang_thai] || "nhat"}>
              {k.trang_thai === "da_roi_bo" ? "Gọi lại ngay" : k.trang_thai === "canh_bao" ? "Gọi lại trong tuần" : d.nhan[k.trang_thai]}</span></td>
          </tr>))}</tbody>
      </table></div>}
      <div className="phu" style={{ marginTop: ".4rem" }}>Im lặng = số ngày chưa mua ÷ nhịp mua riêng của khách. Cột "nợ quá hạn" của gói thiết kế chưa có — chưa nạp sổ công nợ.</div>
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
  const { data: d, isLoading, error } = useKhoi<{ thang: string | null; nganh: Nganh[] }>("hieu_suat_nganh");
  const max = Math.max(0.0001, ...(d?.nganh ?? []).map(n => n.ty_trong ?? 0));
  return (
    <Khoi tieu_de="Hiệu suất theo ngành hàng" phu={d?.thang ? `tháng ${thang_nhan(d.thang)} · so cùng tháng năm trước` : undefined}
      dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}>
      {d && <div className="bang-cuon" style={{ maxHeight: 330 }}><table className="bang">
        <thead><tr><th>Ngành hàng</th><th>Tỷ trọng DT</th><th className="so">Doanh thu</th><th className="so">Biên gộp</th><th className="so">So cùng kỳ</th></tr></thead>
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
  const { data: d, isLoading, error } = useKhoi<{ khach: Cham[] }>("tuong_quan");
  const [tro, datTro] = useState<Cham | null>(null);
  const k = d?.khach ?? [];
  const W = 600, H = 240, l = 56, r = 586, t = 14, b = 200;
  const lx = (v: number) => Math.log10(Math.max(v, 1)), mxX = Math.max(1, ...k.map(x => lx(x.so_lan))), mxY = Math.max(1, ...k.map(x => lx(x.doanh_thu))), mnY = Math.min(mxY - 1, ...k.map(x => lx(x.doanh_thu)));
  const px = (x: Cham) => l + (r - l) * (lx(x.so_lan) / mxX), py = (x: Cham) => b - (b - t) * ((lx(x.doanh_thu) - mnY) / (mxY - mnY || 1));
  return (
    <Khoi tieu_de="Khách hàng theo doanh thu × tần suất mua" phu="mỗi chấm một khách · bấm để mở hồ sơ" dang_tai={isLoading} loi={error?.message}>
      {d && <div className="bd" style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Biểu đồ phân tán doanh thu theo số lần mua của từng khách">
          <line x1={l} y1={t} x2={l} y2={b} className="bd-luoi" /><line x1={l} y1={b} x2={r} y2={b} className="bd-luoi" />
          {k.map(x => <circle key={x.ma} cx={px(x)} cy={py(x)} r={tro?.ma === x.ma ? 6 : 4} fill={MAU_TT[x.trang_thai] ?? LUC.nhat}
            opacity={tro && tro.ma !== x.ma ? 0.35 : 0.72} style={{ cursor: "pointer" }}
            onPointerEnter={() => datTro(x)} onPointerLeave={() => datTro(null)} onClick={() => { location.href = `/khach-hang/${x.ma}`; }} />)}
          <text x={(l + r) / 2} y={H - 8} textAnchor="middle" className="bd-truc">Số lần mua (thang log) →</text>
          <text x={12} y={(t + b) / 2} textAnchor="middle" className="bd-truc" transform={`rotate(-90 12 ${(t + b) / 2})`}>Doanh thu tích luỹ (log) →</text>
        </svg>
        {tro && <div className="bd-noi" style={{ left: `${Math.min(Math.max(px(tro) / W * 100, 15), 85)}%` }}>
          <strong className="ten-jp">{tro.ten}</strong><div>Doanh thu<b>{yen(tro.doanh_thu)}</b></div>
          <div>Số lần mua<b>{so(tro.so_lan)}</b></div><div>Biên gộp<b>{pc(tro.ty_suat)}</b></div><em>bấm để mở hồ sơ</em></div>}
        <div className="bd-chu-giai">{Object.entries({ binh_thuong: "khoẻ", canh_bao: "cần theo dõi", da_roi_bo: "đang rời bỏ" }).map(([m, n]) =>
          <span key={m} className="phu"><i style={{ background: MAU_TT[m], borderRadius: "50%", width: 9, height: 9, display: "inline-block", marginRight: 4 }} />{n}</span>)}</div>
      </div>}
    </Khoi>
  );
}

// ---- Số khách đang mua theo kỳ ----------------------------------------------
export function KhoiTangTruong() {
  const { data: d, isLoading, error } = useKhoi<{ ky: { company_fy: number; nhan: string; so_thang: number; so_khach: number; doanh_thu: number }[] }>("tang_truong");
  const ky = d?.ky ?? [];
  const cuoi = ky[ky.length - 1];
  return (
    <Khoi tieu_de="Số khách đang mua" phu="theo kỳ kế toán (1/8 → 31/7)" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/khach-hang?tat_ca=1" }}>
      {d && <>
        {cuoi && <div className="sk-dau">{so(cuoi.so_khach)} <span>khách có đơn · {cuoi.nhan}{cuoi.so_thang < 12 ? ` (${cuoi.so_thang} tháng)` : ""}</span></div>}
        <BieuDo nhan={ky.map(x => x.nhan.replace(/^Kỳ\s*/, "K"))} nhan_day_du={ky.map(x => `${x.nhan} · ${x.so_thang} tháng dữ liệu`)} cao={150}
          mo_ta="Số khách có đơn theo từng kỳ kế toán"
          chuoi={[{ ten: "Khách có đơn", kieu: "cot", gia_tri: ky.map(x => x.so_khach), mau: "var(--lien-ket)" }]}
          dinh_dang={v => `${so(v)} khách`} dinh_dang_truc={v => so(v)} />
        <div className="phu">Kỳ chưa đủ 12 tháng thì số khách thấp hơn — đừng so thẳng với kỳ đủ.</div>
      </>}
    </Khoi>
  );
}

// ---- Biên lợi nhuận theo quý ------------------------------------------------
export function KhoiBien() {
  const { data: d, isLoading, error } = useKhoi<{ quy: { company_fy: number; quy: number; tu: string; den: string; so_thang: number; doanh_thu: number; lai_gop: number; bien_gop: number | null }[] }>("bien_loi_nhuan");
  const q = d?.quy ?? [];
  return (
    <Khoi tieu_de="Biên lợi nhuận theo quý" phu="biên gộp = tổng lãi gộp ÷ tổng doanh thu thuần" dang_tai={isLoading} loi={error?.message} lien_ket={{ href: "/bao-cao" }}>
      {d && <>
        <BieuDo nhan={q.map(x => `K${x.company_fy}·Q${x.quy}`)} nhan_day_du={q.map(x => `Kỳ ${x.company_fy} quý ${x.quy} (${thang_nhan(x.tu)} – ${thang_nhan(x.den)})${x.so_thang < 3 ? " · chưa đủ quý" : ""}`)}
          cao={170} mo_ta="Biên lãi gộp sáu quý gần nhất"
          chuoi={[
            { ten: "Doanh thu", kieu: "cot", gia_tri: q.map(x => x.doanh_thu), mau: "var(--vien-dam)" },
            { ten: "Biên gộp", kieu: "duong", gia_tri: q.map(x => x.bien_gop), mau: "var(--ok-vien)", truc_phai: true },
          ]}
          dinh_dang={(v, c) => c.truc_phai ? pc(v) : yen(v)} dinh_dang_truc={v => gon(v)} />
        <div className="phu">Biên RÒNG của gói thiết kế chưa có — cần chi phí vận hành, chưa có nguồn.</div>
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
              <td className="so nhat-chu">{x.nap_luc.slice(0, 16).replace("T", " ")}</td></tr>))}</tbody></table></div>
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
  thang_nay_chua_mua: () => <KhoiThangNay />, cong_no: () => <KhoiCongNo />,
};

export function veKhoi(id: string, nhan: string) {
  const f = VE[id];
  if (f) return f();
  return <ChuaCoDuLieu tieu_de={nhan} ly_do={KD.chua_co[id] ?? "Chưa có nguồn dữ liệu cho khối này."} />;
}
