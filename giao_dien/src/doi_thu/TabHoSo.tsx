import { useQuery } from "@tanstack/react-query";
import { lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { ngay, so, yen } from "../dinh_dang";
import { chuoiKhoang, giuKhoang, useKhoang } from "../khung/khoang";
import type { KhachDangMua, QuanSat, TongQuan } from "./kieu";
import { nhanDonVi } from "./kieu";
import { NHAN_TRANG_THAI } from "./kieu";

type HoSo = { ben: { ma: string; ten: string; web: string | null; ghi_chu: string | null };
              dieu_kien: { loai: string; noi_dung: string; ngay: string }[]; quan_sat: (QuanSat & { hien_hanh: boolean })[];
              khach_dang_mua?: KhachDangMua[] };
type KetQua = HoSo | { khong_co: true };

export function TabHoSo({ ben, chonBen }: { ben: string; chonBen: (ma: string) => void }) {
  const kx = chuoiKhoang(useKhoang());
  const tq = useQuery({ queryKey: ["doi-thu", "tong-quan", kx], queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const q = useQuery({ queryKey: ["doi-thu", "ben", ben, kx], enabled: !!ben,
    queryFn: () => lay<KetQua>(`/api/doi-thu/ben/${encodeURIComponent(ben)}${kx ? "?" + kx : ""}`) });
  const khongCo = !!q.data && "khong_co" in q.data;
  const hs = q.data && !("khong_co" in q.data) ? q.data : null;
  const hien = hs?.quan_sat.filter(x => x.hien_hanh) ?? [];
  const lich_su = (x: QuanSat) => hs?.quan_sat.filter(y => y.ma_hang_dt === x.ma_hang_dt && y.kenh_gia === x.kenh_gia && y.muc_gia === x.muc_gia) ?? [];
  // "Mạnh ở ngành nào": hàng của lưới tổng quan cho đúng bên này, xếp theo số mã giảm dần (không tính thêm gì).
  const manh = (tq.data?.luoi ?? []).filter(x => x.ben === ben).sort((a, b) => b.so_ma - a.so_ma);
  return (
    <section className="dt-khoi">
      <Khoi tieu_de={hs?.ben.ten ?? "Hồ sơ đối thủ"} dang_tai={!!ben && q.isLoading} loi={q.error ? (q.error as Error).message : null}>
        <select value={ben} onChange={e => chonBen(e.target.value)} aria-label="Chọn đối thủ">
          <option value="">— chọn đối thủ —</option>
          {tq.data?.ben.map(b => <option key={b.ma} value={b.ma}>{b.ten}</option>)}
        </select>
        {khongCo && <p>Không có đối thủ này.</p>}
        {hs?.ben.web && <p><a href={hs.ben.web} rel="noreferrer" target="_blank">{hs.ben.web}</a></p>}
        {hs && <>
          <h3>Mạnh ở ngành nào</h3>
          {manh.length ? (
            <div className="dt-cuon">
              <table className="bang dt-bang"><thead><tr><th>Ngành</th><th>Số mã</th></tr></thead>
                <tbody>{manh.map(x => <tr key={x.nganh}><td>{x.nganh}</td><td>{so(x.so_ma)}</td></tr>)}</tbody></table>
            </div>) : tq.isSuccess ? <p className="dt-nhat">Chưa ghép được mặt hàng nào với ngành của KOME.</p> : null}
          <h3>Khách đang mua của bên này ({hs.khach_dang_mua?.length ?? 0})</h3>
          {hs.khach_dang_mua?.length ? (
            <div className="dt-cuon">
              <table className="bang dt-bang">
                <caption className="dt-an">Các lần ghi tiếp xúc 90 ngày qua có gắn thẻ @{hs.ben.ma}, mới nhất trước</caption>
                <thead><tr><th>Ngày</th><th>Khách</th><th>Hàng nhắc cùng</th><th>Giá khách kể</th></tr></thead>
                <tbody>{hs.khach_dang_mua.map(k => (
                  <tr key={k.tiep_xuc_id}>
                    <td>{ngay(k.ngay)}</td>
                    <td><a href={giuKhoang(`/khach-hang/${encodeURIComponent(k.ma_khach)}`)}>{k.ten_khach ?? k.ma_khach}</a>
                      {" "}<span className="dt-nhat">{k.ma_khach}</span></td>
                    <td>{k.nhom.map(n => n.ten ?? n.khoa).join(" · ") || "—"}</td>
                    <td>{k.gia.map(g => `${g.ten_nhom ?? g.nhom_khoa}: ${yen(g.gia_goc)}/${nhanDonVi(g.don_vi_gia)}`).join(" · ") || "—"}</td>
                  </tr>))}</tbody></table>
            </div>) : <p className="dt-nhat">Chưa lần ghi tiếp xúc nào trong 90 ngày gắn thẻ @{hs.ben.ma}.</p>}
          <h3>Điều kiện</h3>
          <ul className="dt-ds">{hs.dieu_kien.map((k, i) => <li key={i}>{k.loai} · {k.noi_dung} · {ngay(k.ngay)}</li>)}</ul>
          <h3>Mặt hàng ({hien.length})</h3>
          <div className="dt-cuon">
            <table className="bang dt-bang"><thead><tr><th>Hàng</th><th>Giá</th><th>¥ quy đổi</th><th>Trạng thái</th><th>Ghép KOME</th><th>Lịch sử</th></tr></thead>
              <tbody>{hien.map(x => (
                <tr key={x.nguon + x.id}>
                  <td>{x.ten_goc} <span className="dt-nhat">{x.quy_cach_goc}</span></td>
                  <td>{x.gia_goc != null ? `${yen(x.gia_goc)}/${x.don_vi_gia ?? "?"}` : "—"}</td>
                  <td>{x.yen_chuan != null ? yen(x.yen_chuan) : "—"}</td>
                  <td>{NHAN_TRANG_THAI[x.trang_thai]}</td>
                  <td>{x.ma_kome ? <a href={`/san-pham/${encodeURIComponent(x.ma_kome)}`}>{x.ma_kome}</a> : ""}</td>
                  <td>{lich_su(x).map(y => `${ngay(y.ngay_nguon)} ${y.gia_goc != null ? yen(y.gia_goc) : "—"}`).join(" · ")}</td>
                </tr>))}</tbody></table>
          </div>
        </>}
      </Khoi>
    </section>
  );
}
