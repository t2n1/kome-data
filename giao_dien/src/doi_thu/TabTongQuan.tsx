import { useQuery } from "@tanstack/react-query";
import { lay } from "../api";
import { Khoi } from "../chung/Khoi";
import { ngay, so, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { TongQuan } from "./kieu";
import { NHAN_TRANG_THAI } from "./kieu";

export function TabTongQuan({ moBen }: { moBen: (ma: string) => void }) {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "tong-quan", kx],
    queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const d = q.data;
  const nganh = d ? [...new Set(d.luoi.map(x => x.nganh))].sort() : [];
  const o = (ben: string, n: string) => d?.luoi.find(x => x.ben === ben && x.nganh === n)?.so_ma ?? 0;
  const loi = q.error ? (q.error as Error).message : null;
  return (
    <div className="dt-luoi-khoi">
      <section className="dt-khoi dt-rong">
        <Khoi tieu_de="Đối thủ × ngành hàng" dang_tai={q.isLoading} loi={loi}
          cach_tinh="Ô = số mặt hàng của đối thủ ghép được với ngành đó của KOME (cùng hàng hoặc thay thế).">
          <div className="dt-cuon">
            <table className="bang dt-bang">
              <thead><tr><th>Đối thủ</th>{nganh.map(n => <th key={n}>{n}</th>)}<th>Nguồn mới nhất</th><th>Chờ duyệt</th></tr></thead>
              <tbody>{d?.ben.map(b => (
                <tr key={b.ma}>
                  <th><button type="button" className="lien-ket" onClick={() => moBen(b.ma)}>{b.ten}</button></th>
                  {nganh.map(n => { const v = o(b.ma, n); return <td key={n} className={v ? "dt-o co" : "dt-o"}>{v ? so(v) : ""}</td>; })}
                  <td>{b.ngay_moi ? `${ngay(b.ngay_moi)} · ${b.hinh_thuc === "web" ? "web" : "file"}` : "chưa có"}</td>
                  <td>{b.cho_duyet ? so(b.cho_duyet) : ""}</td>
                </tr>))}</tbody>
            </table>
          </div>
        </Khoi>
      </section>
      <section className="dt-khoi">
        <Khoi tieu_de="Đối thủ đang hết / sắp về" dang_tai={q.isLoading}
          cach_tinh="Hàng ghép được với mã KOME mà bảng giá mới nhất của đối thủ ghi hết hàng hoặc sắp về — cơ hội chào hàng.">
          <ul className="dt-ds">{d?.het_hang.map((h, i) => (
            <li key={i}><b>{h.ten_nhom ?? h.ma_kome}</b> · {h.ben} · {NHAN_TRANG_THAI[h.trang_thai]}
              {" "}<a href={`/san-pham/${encodeURIComponent(h.ma_kome)}`}>mã {h.ma_kome} →</a></li>))}</ul>
        </Khoi>
      </section>
      <section className="dt-khoi">
        <Khoi tieu_de="Khuyến mãi đang chạy" dang_tai={q.isLoading}>
          <ul className="dt-ds">{d?.khuyen_mai.slice(0, 60).map((k, i) => (
            <li key={i}><b>{k.ben}</b> · {k.ten_goc} · {k.gia_goc != null ? yen(k.gia_goc) : ""}
              {k.gia_truoc_km != null && <s> {yen(k.gia_truoc_km)}</s>} {k.khuyen_mai}</li>))}</ul>
        </Khoi>
      </section>
      <section className="dt-khoi dt-rong">
        <Khoi tieu_de="Điều kiện bán của từng bên" dang_tai={q.isLoading}>
          <div className="dt-cuon">
            <table className="bang dt-bang"><tbody>{d?.dieu_kien.map((k, i) => (
              <tr key={i}><th>{k.ben}</th><td>{k.loai}</td><td>{k.noi_dung}</td><td>{ngay(k.ngay)}</td></tr>))}</tbody></table>
          </div>
        </Khoi>
      </section>
    </div>
  );
}
