// Màn Kho dữ liệu — tab Vận hành (Kho dữ liệu.dc.html). Máy chủ tính sẵn đúng
// như bản Jinja trước (kome/web/app.py::_du_lieu_kho — vai trò NẠP, không qua
// ảnh chụp: đây là màn phải thấy lô vừa nạp ngay) và chèn vào window.__KOME__.man.
//
// Thứ tự khối có chủ ý: "tôi phải làm gì ngay" (tuổi dữ liệu) → chỗ thả file →
// "có gì sai không" (sức khoẻ) → lô gần nhất + hoàn tác → sổ sách (hai bảng phủ).
// Nạp và Hoàn tác là biểu mẫu POST THẬT (/upload, /undo/{lô}) — chạy cả khi
// JavaScript hỏng; bản chỉ-đọc (Vercel) ẩn hẳn hai khối đó. Hoàn tác nằm sau
// <details>: người bấm phải mở ra đọc "xoá bao nhiêu dòng, khỏi bảng nào" trước.
import { useState } from "react";
import { KD } from "../khoi_dau";
import { so, yen } from "../dinh_dang";
import { DaiTuoi } from "../tong_quan/DaiTuoi";
import { TabKho } from "./TabKho";
import "./he_thong.css";

type O = { trang_thai: string; ky_hieu: string; mo_ta: string };
type Cot = { khoa?: string; nhan: string; chu_giai: string; ten_obc: string; mo_ta?: string };
type Ket = { spec_name: string | null; skipped: boolean; ok: boolean; row_count: number; total: number;
  blockers: { gate: number; message: string }[]; warnings: { gate: number; message: string }[] };
type Lo = { batch_id: number; loai: string; ten_file: string; ngay_du_lieu: string | null; nap_luc: string; so_dong: number;
  co_tien: boolean; tong_tien: number; so_dong_xoa: number | null; ten_bang: string; nhieu_hon_luc_nap: boolean; lam_trong_bang: boolean };
type Man = {
  status: { name: string; last: string | null; rows: number; total: number; co_tien: boolean }[];
  ky: { dau: string | null; cuoi: string | null; thieu: string[]; tu?: string };
  backup: { stale: boolean; last: string | null } | null;
  lo: Lo[]; results?: Ket[];
  bang_ngay: { dau: string; cuoi: string; co_thieu: boolean; cot: Cot[]; thieu: Record<string, number>;
    ngay: { ngay: string; nhan_thu: string; la_cuoi_tuan: boolean; o: O[] }[] };
  bang: { dau_du_lieu: string; cot: Cot[]; thieu_bo_nap: { ten_obc: string; mo_ta: string; ghi_chu: string }[];
    ky: { nhan: string; dau: string; cuoi: string; du_12_thang: boolean; doanh_thu_thuan: number; lai_gop: number; ty_suat: number | null;
      thang: { thang: string; company_fy_month: number; la_thang_chot_ky: boolean; o: O[] }[] }[] };
};

const gio = (iso: string | null) => iso ? `${iso.slice(0, 10)} ${iso.slice(11, 16)}` : "";

export default function KhoDuLieu() {
  const m = KD.man as Man;
  return (
    <div className="ht kdl">
      <h1>Kho dữ liệu</h1>
      <TabKho dang="van-hanh" />
      <section id="hom-nay"><DaiTuoi /></section>
      {!KD.chi_doc && <Nap ket={m.results} />}
      <SucKhoe m={m} />
      {!KD.chi_doc && <LoNap lo={m.lo} />}
      <ChuGiai dau={m.bang.dau_du_lieu} />
      <section id="theo-ngay"><BangNgay b={m.bang_ngay} /></section>
      <BangThang b={m.bang} />
    </div>
  );
}

function Nap({ ket }: { ket?: Ket[] }) {
  const [ten, datTen] = useState<string[]>([]);
  const [keo, datKeo] = useState(false);
  return (
    <section id="nap">
      <h2>Nạp dữ liệu OBC</h2>
      {/* MỘT ô nhận NHIỀU file: người làm việc 13:30 thả 3 file một lần. */}
      <form method="post" action="/upload" encType="multipart/form-data">
        <label className={"drop" + (keo ? " keo" : "")} onDragOver={() => datKeo(true)} onDragLeave={() => datKeo(false)} onDrop={() => datKeo(false)}>
          Kéo thả file Excel vào đây<br />
          <input className="chon-file" type="file" name="files" multiple required
            onChange={e => datTen([...(e.target.files ?? [])].map(f => f.name))} />
          {ten.length > 0 && <span className="kdl-ten-file">{ten.length} file: {ten.join(" · ")}</span>}
        </label>
        <p><button className="nut-nap" type="submit">Nạp</button></p>
      </form>
      {ket && ket.length > 0 && <><h3>Kết quả</h3><ul className="kdl-ket">
        {ket.map((r, i) => (
          <li key={i}>
            {r.skipped ? <span className="kq-ok">⏭️ {r.spec_name} — file này đã nạp rồi, bỏ qua</span>
              : r.ok ? <span className="kq-ok">✅ {r.spec_name} — {so(r.row_count)} dòng · {yen(r.total)}</span>
              : <span className="kq-loi">❌ {r.spec_name || "?"} — KHÔNG nạp</span>}
            {r.blockers.map((b, k) => <div key={k} className="kq-loi">Cổng {b.gate}: {b.message}</div>)}
            {r.warnings.map((w, k) => <div key={k} className="kq-canh">⚠️ Cổng {w.gate}: {w.message}</div>)}
          </li>))}
      </ul></>}
    </section>
  );
}

function SucKhoe({ m }: { m: Man }) {
  const b = m.backup, k = m.ky;
  return (
    <section id="suc-khoe">
      <h2>Sức khoẻ dữ liệu</h2>
      {/* backup null ở bản chỉ-đọc: máy chủ công khai không thấy thư mục sao lưu — im lặng đúng hơn một dải đỏ vĩnh viễn. */}
      {b == null ? <div className="ky">💾 Tình trạng sao lưu chỉ xem được trên bản chạy ở máy trong công ty.</div>
        : b.stale ? <div className="backup-bad">⚠️ Chưa sao lưu {b.last ? `từ ${gio(b.last)}` : "— chưa có bản sao lưu nào"} — chạy sao lưu ngay:
          <code>python -c "from ops.backup import dump, prune; import os, pathlib; dump(os.environ['DATABASE_URL'], pathlib.Path('backups')); prune(pathlib.Path('backups'))"</code></div>
        : <div className="backup-ok">✅ Sao lưu gần nhất: {gio(b.last)}</div>}
      {k.cuoi ? <>
        <div className="ky">📅 Kỳ dữ liệu bán hàng: <strong>{k.dau}</strong> → <strong>{k.cuoi}</strong></div>
        {k.thieu.length > 0 && <div className="ngay-thieu">⚠️ <strong>Thiếu {k.thieu.length} ngày làm việc</strong> trong khoảng {k.tu} → {k.cuoi}:{" "}
          {k.thieu.map((d, i) => <span key={d}><strong>{d}</strong>{i < k.thieu.length - 1 ? " · " : ""}</span>)}
          <br />Ngày lễ quốc gia đã được bỏ qua — kiểm tra xem hôm đó công ty có nghỉ riêng (Obon, cuối năm) không. Nếu không, xuất lại
          売上伝票データ của đúng ngày đó từ OBC rồi kéo–thả vào trang nạp.</div>}
      </> : <div className="ky">📅 Chưa có dòng bán hàng nào — chưa xác định được kỳ dữ liệu.</div>}
      <div className="bang-cuon"><table>
        <thead><tr><th>Loại file</th><th>Nạp lần cuối</th><th>Số dòng</th><th>Tổng tiền</th></tr></thead>
        <tbody>{m.status.map(s => (
          <tr key={s.name}><td>{s.name}</td>
            <td>{s.last ? gio(s.last) : <span className="missing">CHƯA CÓ DỮ LIỆU</span>}</td>
            <td>{so(s.rows)}</td>
            {/* "—" cho loại file không mang tiền (master): "¥0" sẽ bị đọc là đếm hụt tiền. */}
            <td>{s.co_tien ? yen(s.total) : <span className="khong-ap-dung" title="Loại file này không mang giá trị tiền">—</span>}</td></tr>))}</tbody>
      </table></div>
    </section>
  );
}

function LoNap({ lo }: { lo: Lo[] }) {
  return (
    <section id="lo-nap">
      <h2>Lô nạp gần nhất</h2>
      {!lo.length ? <p className="trong">Chưa có lô nạp nào.</p> : <div className="bang-cuon"><table style={{ minWidth: "44rem" }}>
        <thead><tr><th>Loại file</th><th>Tên file</th><th>Ngày dữ liệu</th><th>Nạp lúc</th><th className="so">Số dòng</th><th className="so">Tổng tiền</th><th>Hoàn tác</th></tr></thead>
        <tbody>{lo.map(l => (
          <tr key={l.batch_id}>
            <td>{l.loai}</td><td>{l.ten_file}</td><td>{l.ngay_du_lieu ?? ""}</td><td>{gio(l.nap_luc)}</td>
            <td className="so">{so(l.so_dong)}</td>
            <td className="so">{l.co_tien ? yen(l.tong_tien) : <span className="khong-ap-dung">—</span>}</td>
            <td><details className="hoan-tac"><summary>Hoàn tác</summary>
              {/* SỐ DÒNG Ở ĐÂY LÀ SỐ ĐẾM THẬT (kome/nhat_ky_nap.py), không phải row_count của file: mọi loader upsert, nên
                  batch_id trên một dòng là "lô ĐỘNG VÀO nó lần cuối". Ba điều bắt buộc: số dòng thật, bảng có trống hẳn không, không hoàn lại được. */}
              {l.so_dong_xoa == null ? <p>Loại <strong>{l.loai}</strong> không còn trong cấu hình nên <strong>không đếm được</strong> hoàn tác sẽ xoá
                bao nhiêu dòng. <strong>Không thể hoàn lại.</strong></p>
                : l.so_dong_xoa === 0 ? <p>Lô này <strong>không còn giữ dòng nào</strong> trong {l.ten_bang}: những lần nạp sau đã đè hết lên dòng
                  của nó. Hoàn tác chỉ đánh dấu lô đã huỷ, <strong>không xoá dòng nào</strong>. <strong>Không thể hoàn lại.</strong></p>
                : <p>Xoá <strong>{so(l.so_dong_xoa)} dòng</strong> khỏi <strong>{l.ten_bang}</strong> — số đếm thật trong kho ngay lúc này, gồm cả
                  dòng do lô TRƯỚC nạp vào rồi bị lần nạp này đè lên.
                  {l.nhieu_hon_luc_nap && <><br />⚠️ File chỉ nạp {so(l.so_dong)} dòng nhưng lô đang giữ {so(l.so_dong_xoa)} dòng —{" "}
                    <strong>nhiều hơn</strong>. Hoàn tác xoá cả {so(l.so_dong_xoa)} dòng đó.</>}
                  {l.lam_trong_bang && <><br />⚠️ <strong>{l.ten_bang.charAt(0).toUpperCase() + l.ten_bang.slice(1)} sẽ trống hoàn toàn</strong>, không lùi
                    về lần nạp trước. Muốn khôi phục phải nạp lại file {l.loai}.</>}
                  {" "}<strong>Không thể hoàn lại.</strong></p>}
              <form method="post" action={`/undo/${l.batch_id}`}><button type="submit">Xoá lô {l.batch_id}</button></form>
            </details></td>
          </tr>))}</tbody>
      </table></div>}
    </section>
  );
}

function ChuGiai({ dau }: { dau: string }) {
  return (<>
    <div className="chu-giai">
      <span><i className="mau o-co">●</i> có dữ liệu trong kho</span>
      <span><i className="mau o-khong">·</i> không có dữ liệu</span>
      <span><i className="mau o-ngoai">—</i> ngoài phạm vi</span>
      <span><i className="mau o-co">7</i> cột tồn kho: SỐ NGÀY có ảnh chụp</span>
      <span><i className="mau" style={{ background: "var(--do-nen)", color: "var(--do-chu)" }}>7月</i> tháng chốt kỳ</span>
    </div>
    <div className="ky">📌 <strong>Ràng buộc vĩnh viễn:</strong> dữ liệu bán hàng bắt đầu từ <strong>{dau}</strong>. Trước mốc đó{" "}
      <strong>không tồn tại</strong> — công ty không còn lưu (đặc tả §2.2.1). Các tháng trước mốc hiện là <strong>"ngoài phạm vi"</strong>, đó{" "}
      <em>không phải</em> là thiếu dữ liệu và <em>không</em> có gì để đi tìm.</div>
    <div className="ngay-thieu">⚠️ <strong>Hạn chế cần biết:</strong> ô "không có dữ liệu" <strong>không phân biệt được</strong> hai trường hợp:
      (a) chưa bao giờ xuất file cho tháng đó, và (b) đã xuất nhưng file bị cổng kiểm tra chặn (bản xuất thiếu dòng, sai mẫu…). Cổng kiểm tra
      chặn <strong>trước khi</strong> ghi nhật ký nạp, nên kho không hề biết file đó từng tồn tại. Muốn biết chắc thì đối chiếu với thư mục xuất của OBC.</div>
  </>);
}

function BangNgay({ b }: { b: Man["bang_ngay"] }) {
  return (<>
    <h2>Từng ngày — 90 ngày gần nhất</h2>
    <p className="chu-thich">{b.dau} → {b.cuoi}, mới nhất ở trên. Chỉ 3 nguồn phải xuất <strong>mỗi ngày lúc 13:30</strong>; 4 loại master xuất
      thưa nằm ở bảng tháng bên dưới. Cuối tuần để trống — không ai xuất file thứ Bảy.</p>
    {b.co_thieu ? <div className="ngay-thieu">⚠️ Trong 90 ngày:{" "}
      {b.cot.filter(c => b.thieu[c.khoa!]).map((c, i, a) => <span key={c.khoa}><strong>{c.ten_obc}</strong> thiếu {b.thieu[c.khoa!]} ngày làm việc{i < a.length - 1 ? " · " : ""}</span>)}</div>
      : <div className="backup-ok">✅ Đủ dữ liệu mọi ngày làm việc trong 90 ngày qua.</div>}
    <div className="cuon-ngay"><table className="phu ngay">
      <thead><tr><th>Ngày</th><th>Thứ</th>{b.cot.map(c => <th key={c.nhan} title={c.chu_giai}>{c.nhan}</th>)}</tr></thead>
      <tbody>{b.ngay.map(n => (
        <tr key={n.ngay} className={n.la_cuoi_tuan ? "cuoi-tuan" : undefined}>
          <td className="d">{n.ngay}</td><td className="d">{n.nhan_thu}</td>
          {n.o.map((o, i) => <td key={i} className={"o o-" + o.trang_thai} title={`${b.cot[i]?.chu_giai ?? ""}: ${o.mo_ta}`}>{o.ky_hieu}</td>)}
        </tr>))}</tbody>
    </table></div>
  </>);
}

function BangThang({ b }: { b: Man["bang"] }) {
  return (
    <section id="theo-thang">
      <h2 className="kdl-vach">Theo tháng, nhóm theo kỳ kế toán</h2>
      <p className="chu-thich">Mỗi dòng là một tháng, mỗi cột là một loại file xuất từ OBC. Nhóm theo <strong>kỳ kế toán của công ty: 1/8 → 31/7
        năm sau</strong> (không phải năm tài chính Nhật chuẩn 1/4 → 31/3).</p>
      <p className="chu-thich">Bảng này có đủ 7 loại file và trải toàn bộ lịch sử. Dùng để soát lịch sử; muốn biết hôm qua có sót ngày nào thì xem
        bảng ngày ở trên.</p>
      {b.ky.map(k => (
        <div key={k.nhan} className="khoi-ky">
          <h2>{k.nhan}</h2>
          <div className="chu-thich">{k.dau} → {k.cuoi}{!k.du_12_thang && <> · <strong>kỳ không đủ 12 tháng trong phạm vi dữ liệu</strong> — đừng
            đem so tổng kỳ này với kỳ khác</>}</div>
          <div className="tom-tat">
            <div>Doanh thu thuần<b>{yen(k.doanh_thu_thuan)}</b></div>
            <div>Lãi gộp<b>{yen(k.lai_gop)}</b></div>
            <div>Tỷ suất lãi gộp<b>{k.ty_suat == null ? <span className="khong-ap-dung">chưa có doanh thu</span> : (k.ty_suat * 100).toFixed(1).replace(".", ",") + "%"}</b></div>
          </div>
          <div className="bang-cuon"><table className="phu">
            <thead><tr><th>Tháng</th><th>Tháng thứ<br />trong kỳ</th>{b.cot.map(c => <th key={c.nhan} title={c.chu_giai}>{c.nhan}</th>)}</tr></thead>
            <tbody>{k.thang.map(t => (
              <tr key={t.thang} className={t.la_thang_chot_ky ? "chot-ky" : undefined}>
                <td className="thang">{t.thang}{t.la_thang_chot_ky ? " · chốt kỳ" : ""}</td><td>{t.company_fy_month}</td>
                {t.o.map((o, i) => <td key={i} className={"o o-" + o.trang_thai} title={`${b.cot[i]?.chu_giai ?? ""}: ${o.mo_ta}`}>{o.ky_hieu}</td>)}
              </tr>))}</tbody>
          </table></div>
        </div>))}
      <h2>Chú giải cột</h2>
      <div className="bang-cuon"><table><tbody>{b.cot.map(c => <tr key={c.nhan}><td><strong>{c.nhan}</strong></td><td>{c.ten_obc}</td><td>{c.mo_ta}</td></tr>)}</tbody></table></div>
      <h2>Loại dữ liệu CHƯA vào kho</h2>
      <div className="bang-cuon"><table><tbody>{b.thieu_bo_nap.map(l => <tr key={l.ten_obc}><td>{l.ten_obc}</td><td>{l.mo_ta}</td><td>{l.ghi_chu}</td></tr>)}</tbody></table></div>
    </section>
  );
}

