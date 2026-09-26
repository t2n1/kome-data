// Công nợ trong hồ sơ 360° của một khách (đợt 6): /api/cong-no/khach/{mã}.
// Công nợ ghi theo BÊN NHẬN HOÁ ĐƠN (請求先), không theo từng khách — khách dùng
// chung một bên (vd. 代引専用) thấy số của CẢ bên, và màn nói rõ điều đó.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../api";
import { chuoiKhoang, useKhoang, voiKhoang } from "../khung/khoang";
import { ChuaCoDuLieu } from "../chung/Khoi";
import { gon, ngay, so, yen } from "../dinh_dang";
import { nhanHan, type CongNoKhach } from "./kieu";

export function useCongNoKhach(ma: string) {
  return useQuery<CongNoKhach>({
    queryKey: ["cong-no-khach", ma, chuoiKhoang(useKhoang())],
    queryFn: () => lay<CongNoKhach>(voiKhoang(`/api/cong-no/khach/${encodeURIComponent(ma)}`)),
  });
}

/** Công nợ ở cột trái hồ sơ 360° (2026-09-26) — cùng hook; giữ đúng BA câu trạng thái
 *  (đang tải · chưa nạp sổ · bên không có trong sổ) mà ô KPI cũ của tab Tổng quan từng có. */
export function OCongNoGon({ ma }: { ma: string }) {
  const { data: d } = useCongNoKhach(ma);
  const tieu_de = <h2>Công nợ{d?.ben && !d.la_chinh ? " (bên nhận HĐ)" : ""}</h2>;
  if (!d) return <section className="kh-the hs2-viec">{tieu_de}<p className="phu">…</p></section>;
  if (!d.co_so) return <section className="kh-the hs2-viec">{tieu_de}<p className="phu">Chưa nạp sổ công nợ.</p></section>;
  if (!d.ben || !d.tq) return <section className="kh-the hs2-viec">{tieu_de}<p className="phu">Bên nhận hoá đơn không có trong sổ.</p></section>;
  return (
    <section className="kh-the hs2-viec">{tieu_de}
      <a className="hs2-dong" href={`/cong-no?tim=${encodeURIComponent(d.ben_ma)}`}>
        <span>Quá hạn</span><b className={d.tq.qua_han ? "giam" : ""}>{gon(d.tq.qua_han)}</b></a>
      <div className="hs2-dong phu"><span>Dư nợ {gon(d.ben.so_du)} · đến {ngay(d.ben.ky_den)}</span></div>
    </section>);
}

export function TabCongNo({ ma }: { ma: string }) {
  const { data: d, isLoading, error } = useCongNoKhach(ma);
  if (isLoading) return <div className="khoi-cho" aria-busy="true"><span /><span /></div>;
  if (error) return <div className="khoi-loi">Không tải được công nợ: {(error as Error).message}</div>;
  if (!d) return null;
  if (!d.co_so) return <section className="kh-the kh-chua-co"><ChuaCoDuLieu tieu_de="Công nợ" ly_do="Chưa nạp sổ 請求先元帳 nào — nạp ở màn Kho dữ liệu." /></section>;
  if (!d.ben || !d.tq) return <section className="kh-the"><h2>Công nợ</h2>
    <p className="trong-nho">Bên nhận hoá đơn <code>{d.ben_ma}</code> không có dòng nào trong sổ 請求先元帳 mới nhất.</p></section>;
  const b = d.ben, tq = d.tq;
  return (<>
    <div className="hs-hang hai">
      <section className="kh-the">
        <div className="kh-the-dau"><h2>Bên nhận hoá đơn</h2><a className="kh-the-goc" href={`/cong-no?tim=${encodeURIComponent(b.ma)}`}>Mở trong màn Công nợ →</a></div>
        <p className="phu kh-the-phu">{d.la_chinh ? "Khách này tự nhận hoá đơn." : <>Hoá đơn của khách này gửi tới <a href={`/khach-hang/${encodeURIComponent(b.ma)}`} className="ten-jp">{b.ten}</a>.</>}
          {b.so_khach > 1 && <> Bên này nhận hoá đơn cho <b>{so(b.so_khach)} khách</b> — mọi số dưới đây là của cả bên, không riêng khách này.</>}</p>
        <dl className="hs-dl">
          <dt>Điều kiện thanh toán</dt><dd className="ten-jp">{b.dieu_kien ?? "—"}</dd>
          <dt>Kỳ sổ</dt><dd>{ngay(b.ky_tu)} → {ngay(b.ky_den)}</dd>
          <dt>Mang sang đầu kỳ</dt><dd>{yen(b.mang_sang)}</dd>
          <dt>Bán chịu trong kỳ</dt><dd>{yen(b.ban_chiu)}</dd>
          <dt>Đã thu trong kỳ</dt><dd>{yen(b.da_thu)}</dd>
          <dt>Số dư cuối kỳ</dt><dd><b>{yen(b.so_du)}</b>{b.so_du < 0 && " (trả dư)"}</dd>
          <dt>Quá hạn</dt><dd className={tq.qua_han ? "giam" : ""}>{yen(tq.qua_han)}{tq.so_phieu_qua_han ? ` · ${tq.so_phieu_qua_han} phiếu` : ""}</dd>
          <dt>Thu lần cuối</dt><dd>{b.lan_thu_cuoi ? ngay(b.lan_thu_cuoi) : "trong kỳ chưa thu"}</dd>
        </dl>
      </section>
      <section className="kh-the kh-chua-co">
        <ChuaCoDuLieu tieu_de="Hạn mức tín dụng" ly_do="OBC không xuất hạn mức tín dụng trong file nào ta nạp — chưa có nguồn." />
      </section>
    </div>
    <section className="kh-the">
      <div className="kh-the-dau"><h2>Phiếu còn nợ</h2><span className="kh-the-goc phu">{so(d.so_phieu ?? d.phieu.length)} phiếu</span></div>
      <p className="phu kh-the-phu">{d.cach_tinh.fifo}</p>
      {d.phieu.length ? <div className="bang-cuon"><table className="bang">
        <thead><tr><th>Số phiếu</th><th>Ngày</th><th>Hạn (suy)</th><th className="so">Tổng</th><th className="so">Còn lại</th><th>Tuổi nợ</th></tr></thead>
        <tbody>{d.phieu.map((p, i) => { const [nhan, mau] = nhanHan(p); return (
          <tr key={i}><td><code>{p.so ?? "—"}</code>{p.loai === "truoc_ky" && <div className="ma-nho">nợ mang sang trước kỳ</div>}</td>
            <td>{ngay(p.ngay)}</td><td className="nhat-chu">{p.han ? ngay(p.han) : "không suy được"}</td>
            <td className="so">{yen(p.tong)}</td><td className="so"><b>{yen(p.con_lai)}</b></td>
            <td><span className={"nhan-vien " + mau}>{nhan}</span></td></tr>); })}</tbody>
      </table></div> : <p className="trong-nho">Không phiếu nào còn nợ.</p>}
      {(d.so_phieu ?? 0) > d.phieu.length && <p className="phu">Hiện {d.phieu.length} phiếu quá hạn lâu nhất — xem đủ ở màn Công nợ.</p>}
    </section>
  </>);
}
