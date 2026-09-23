// Ngân sách — chỉ tiêu doanh thu: 5 người phụ trách × 12 tháng của một kỳ.
// Biểu mẫu POST /ngan-sach THẬT (một giao dịch; một ô rác => không ô nào được
// lưu, máy chủ trả lại đúng những gì vừa gõ — `da_go` — và đánh dấu ô sai).
//
// `inputMode="numeric"` chứ KHÔNG `type="number"`: cuộn chuột trên ô number là
// đổi số. Ô chưa đặt hiện TRỐNG, không 0 — "chưa đặt" khác "bằng không" (cùng
// nếp mart.san_pham_360.ton). Dải TỔNG in "—" khi không ô nào đứng sau nó.
// Tiền dấu CHẤM ngăn nghìn — khớp /bao-cao (dinh_dang.ts::yen).
import { KD } from "../khoi_dau";
import { yen } from "../dinh_dang";
import "./he_thong.css";

type Man = {
  moi_ky: number[]; ky: number; thang: string[]; nguoi: { ma: string; ten: string }[];
  o_txt: Record<string, number>; da_go: Record<string, string>; loi: string[];
};

const cham = (n: number) => n.toLocaleString("de-DE");

export default function NganSach() {
  const m = KD.man as Man;
  const loi = new Set(m.loi);
  const coGo = Object.keys(m.da_go).length > 0;
  const o = (ma: string, th: string) => m.o_txt[`${ma}-${th}`];
  const tongNguoi = (ma: string) => m.thang.map(th => o(ma, th)).filter((v): v is number => v != null);
  const tongThang = (th: string) => m.nguoi.map(n => o(n.ma, th)).filter((v): v is number => v != null);
  const tatCa = Object.values(m.o_txt);
  const tong = (ds: number[]) => ds.length ? yen(ds.reduce((s, v) => s + v, 0)) : "—";
  return (
    <div className="ht ns">
      <h1>Ngân sách — chỉ tiêu doanh thu</h1>
      <div className="chon-ky" role="group" aria-label="Kỳ kế toán">
        {m.moi_ky.map(k => <a key={k} href={`/ngan-sach?ky=${k}`} className={k === m.ky ? "dang-xem" : undefined}
          aria-current={k === m.ky ? "page" : undefined}>Kỳ {k}</a>)}
      </div>
      {m.loi.length > 0 && <div className="ngay-thieu" role="alert">Có {m.loi.length} ô không đọc được thành số —{" "}
        <strong>chưa ô nào được lưu</strong>. Sửa những ô được đánh dấu rồi bấm Lưu lại. Chỉ nhận chữ số; dấu chấm, dấu phẩy và dấu cách
        đều bỏ qua được.</div>}
      <p className="ghi-chu">Ô để trống nghĩa là <strong>chưa đặt chỉ tiêu</strong>. Muốn đặt chỉ tiêu bằng không thì gõ số <code>0</code> — hai
        điều đó khác nhau, và màn Báo cáo hiện chúng khác nhau.</p>
      <form method="post" action="/ngan-sach">
        <input type="hidden" name="ky" value={m.ky} />
        <div className="bang-cuon">
          <table className="bang ns-bang">
            <thead><tr><th>Nhân viên</th>{m.thang.map(th => <th key={th} className="thang">{th}</th>)}<th className="so">Cả kỳ</th></tr></thead>
            <tbody>
              {m.nguoi.map(n => (
                <tr key={n.ma}><td>{n.ten}<br /><small className="nhat-chu">{n.ma}</small></td>
                  {m.thang.map(th => {
                    const khoa = `${n.ma}-${th}`;
                    // Thứ tự có nghĩa: đúng những gì vừa gõ (bị từ chối) > giá trị đang lưu > rỗng (CHƯA ĐẶT).
                    const gt = coGo && khoa in m.da_go ? m.da_go[khoa] : o(n.ma, th) != null ? cham(o(n.ma, th)) : "";
                    return <td key={th}><input type="text" inputMode="numeric" autoComplete="off" name={"o-" + khoa}
                      aria-label={`${n.ten} — ${th}`} className={loi.has(khoa) ? "sai" : undefined}
                      aria-invalid={loi.has(khoa) ? true : undefined} defaultValue={gt} /></td>;
                  })}
                  <td className="so tong">{tong(tongNguoi(n.ma))}</td></tr>))}
              <tr className="tong"><td>Cả nhóm</td>
                {m.thang.map(th => <td key={th} className="so">{tong(tongThang(th))}</td>)}
                <td className="so">{tong(tatCa)}</td></tr>
            </tbody>
          </table>
        </div>
        <button className="nut-chinh ns-luu" type="submit">Lưu</button>
      </form>
    </div>
  );
}
