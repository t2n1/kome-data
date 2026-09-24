// Ngân sách theo tháng (041): khối CÔNG TY (doanh thu + lãi gộp, nhập thẳng — KHÔNG phải tổng
// từng người) rồi khối TỪNG NGƯỜI phụ trách (hai dòng mỗi người, không bắt buộc).
// Biểu mẫu POST /ngan-sach THẬT (một giao dịch; một ô rác => không ô nào được lưu, máy chủ trả
// lại đúng những gì vừa gõ — `da_go` — và đánh dấu ô sai). Tên ô: `o-<đối tượng>-<chỉ số>-<tháng>`.
//
// `inputMode="numeric"` chứ KHÔNG `type="number"`: cuộn chuột trên ô number là đổi số. Ô chưa
// đặt hiện TRỐNG, không 0 — "chưa đặt" khác "bằng không" (cùng nếp mart.san_pham_360.ton).
// Dải TỔNG in "—" khi không ô nào đứng sau nó. Tiền dấu CHẤM ngăn nghìn — khớp /bao-cao.
import { KD } from "../khoi_dau";
import { yen } from "../dinh_dang";
import "./he_thong.css";

type Man = {
  moi_ky: number[]; ky: number; thang: string[]; nguoi: { ma: string; ten: string }[]; cong_ty: string;
  o_txt: Record<string, number>; da_go: Record<string, string>; loi: string[];
};
type ChiSo = "doanh_thu" | "lai_gop";
const TEN_CS: Record<ChiSo, string> = { doanh_thu: "Doanh thu", lai_gop: "Lãi gộp" };

const cham = (n: number) => n.toLocaleString("de-DE");
const pc = (tu: number, mau: number) => mau ? `${(tu / mau * 100).toFixed(1).replace(".", ",")}%` : "—";

export default function NganSach() {
  const m = KD.man as Man;
  const loi = new Set(m.loi);
  const coGo = Object.keys(m.da_go).length > 0;
  const khoa = (doi: string, cs: ChiSo, th: string) => `${doi}-${cs}-${th}`;
  const o = (doi: string, cs: ChiSo, th: string): number | undefined => m.o_txt[khoa(doi, cs, th)];
  const co = (ds: (number | undefined)[]) => ds.filter((v): v is number => v != null);
  const tong = (ds: number[]) => ds.length ? yen(ds.reduce((s, v) => s + v, 0)) : "—";
  const cong = (ds: number[]) => ds.reduce((s, v) => s + v, 0);
  const ct = m.cong_ty;
  const cuaNguoi = (cs: ChiSo, th: string) => co(m.nguoi.map(n => o(n.ma, cs, th)));

  // Hàm thường, không phải thành phần: khai báo thành phần TRONG render là mỗi lần vẽ lại một kiểu mới -> React gắn lại ô.
  const oNhap = (doi: string, cs: ChiSo, th: string, nhan: string) => {
    const k = khoa(doi, cs, th);
    // Thứ tự có nghĩa: đúng những gì vừa gõ (bị từ chối) > giá trị đang lưu > rỗng (CHƯA ĐẶT).
    const v = o(doi, cs, th);
    const gt = coGo && k in m.da_go ? m.da_go[k] : v != null ? cham(v) : "";
    return <td key={th}><input type="text" inputMode="numeric" autoComplete="off" name={"o-" + k}
      aria-label={`${nhan} — ${TEN_CS[cs]} — ${th}`} className={loi.has(k) ? "sai" : undefined}
      aria-invalid={loi.has(k) ? true : undefined} defaultValue={gt} /></td>;
  };
  const dauBang = (cot: string) => (
    <thead><tr><th>{cot}</th><th></th>{m.thang.map(th => <th key={th} className="thang">{th}</th>)}<th className="so">Cả kỳ</th></tr></thead>);

  return (
    <div className="ht ns">
      <h1>Ngân sách theo tháng — doanh thu &amp; lãi gộp</h1>
      <div className="chon-ky" role="group" aria-label="Kỳ kế toán">
        {m.moi_ky.map(k => <a key={k} href={`/ngan-sach?ky=${k}`} className={k === m.ky ? "dang-xem" : undefined}
          aria-current={k === m.ky ? "page" : undefined}>Kỳ {k}</a>)}
      </div>
      {m.loi.length > 0 && <div className="ngay-thieu" role="alert">Có {m.loi.length} ô không đọc được thành số —{" "}
        <strong>chưa ô nào được lưu</strong>. Sửa những ô được đánh dấu rồi bấm Lưu lại. Chỉ nhận chữ số; dấu chấm, dấu phẩy và dấu cách
        đều bỏ qua được.</div>}
      <p className="ghi-chu">Ô để trống nghĩa là <strong>chưa đặt</strong>. Muốn đặt bằng không thì gõ số <code>0</code> — hai điều đó khác
        nhau, và màn Báo cáo hiện chúng khác nhau. Lãi gộp = 粗利益 (doanh thu trừ giá vốn, như OBC).</p>
      <form method="post" action="/ngan-sach">
        <input type="hidden" name="ky" value={m.ky} />

        <h2 className="ns-muc">Ngân sách công ty</h2>
        <p className="ghi-chu">Số của cả công ty, nhập thẳng — Tổng quan, Báo cáo và Dự báo so tiến độ với dòng này, <strong>không</strong> cộng
          từ chỉ tiêu từng người.</p>
        <div className="bang-cuon">
          <table className="bang ns-bang">
            {dauBang("Công ty")}
            <tbody>
              {(["doanh_thu", "lai_gop"] as ChiSo[]).map(cs => (
                <tr key={cs}><td>{cs === "doanh_thu" ? "Toàn công ty" : ""}</td><td className="ns-cs">{TEN_CS[cs]}</td>
                  {m.thang.map(th => oNhap(ct, cs, th, "Công ty"))}
                  <td className="so tong">{tong(co(m.thang.map(th => o(ct, cs, th))))}</td></tr>))}
              <tr className="ns-bien"><td></td><td className="ns-cs">Biên gộp dự kiến</td>
                {m.thang.map(th => { const dt = o(ct, "doanh_thu", th), lg = o(ct, "lai_gop", th);
                  return <td key={th} className="so">{dt != null && lg != null ? pc(lg, dt) : "—"}</td>; })}
                <td className="so">{(() => {
                  const th2 = m.thang.filter(th => o(ct, "doanh_thu", th) != null && o(ct, "lai_gop", th) != null);
                  return th2.length ? pc(cong(th2.map(th => o(ct, "lai_gop", th)!)), cong(th2.map(th => o(ct, "doanh_thu", th)!))) : "—";
                })()}</td></tr>
            </tbody>
          </table>
        </div>

        <h2 className="ns-muc">Chỉ tiêu từng người phụ trách</h2>
        <p className="ghi-chu">Không bắt buộc. Dùng cho thanh tiến độ từng người trên Tổng quan và Báo cáo.</p>
        <div className="bang-cuon">
          <table className="bang ns-bang">
            {dauBang("Nhân viên")}
            <tbody>
              {m.nguoi.map(n => (["doanh_thu", "lai_gop"] as ChiSo[]).map(cs => (
                <tr key={n.ma + cs} className={cs === "lai_gop" ? "ns-dong-2" : undefined}>
                  <td>{cs === "doanh_thu" && <>{n.ten}<br /><small className="nhat-chu">{n.ma}</small></>}</td>
                  <td className="ns-cs">{TEN_CS[cs]}</td>
                  {m.thang.map(th => oNhap(n.ma, cs, th, n.ten))}
                  <td className="so tong">{tong(co(m.thang.map(th => o(n.ma, cs, th))))}</td></tr>)))}
              {(["doanh_thu", "lai_gop"] as ChiSo[]).map(cs => (
                <tr key={"tong" + cs} className="tong"><td>{cs === "doanh_thu" ? "Tổng từng người" : ""}</td><td className="ns-cs">{TEN_CS[cs]}</td>
                  {m.thang.map(th => <td key={th} className="so">{tong(cuaNguoi(cs, th))}</td>)}
                  <td className="so">{tong(m.thang.flatMap(th => cuaNguoi(cs, th)))}</td></tr>))}
              {(["doanh_thu", "lai_gop"] as ChiSo[]).map(cs => (
                <tr key={"lech" + cs} className="ns-lech"><td>{cs === "doanh_thu" ? "Công ty − tổng từng người" : ""}</td><td className="ns-cs">{TEN_CS[cs]}</td>
                  {m.thang.map(th => { const c = o(ct, cs, th), ng = cuaNguoi(cs, th);
                    return <td key={th} className="so">{c != null && ng.length ? yen(c - cong(ng)) : "—"}</td>; })}
                  <td></td></tr>))}
            </tbody>
          </table>
        </div>
        <p className="ghi-chu">Dòng "Công ty − tổng từng người" là phần ngân sách công ty chưa chia cho ai (âm = chỉ tiêu từng người cộng lại vượt ngân sách công ty).</p>
        <button className="nut-chinh ns-luu" type="submit">Lưu</button>
      </form>
    </div>
  );
}
