// Tài liệu sống của màn Kho dữ liệu (đợt 2b): tab "Sơ đồ luồng" và "Cột nối".
// KHÔNG có chuỗi dữ liệu viết tay: mọi tên bảng, tên file, ngưỡng, cạm bẫy đến
// từ kome/tai_lieu.py (files.yml lúc chạy + ảnh chụp sinh bởi
// scripts/sinh_tai_lieu.py), máy chủ chèn sẵn vào window.__KOME__.man. 0 truy vấn.
import type { ReactNode } from "react";
import { KD } from "../khoi_dau";
import { so } from "../dinh_dang";
import { KhungKho } from "./TabKho";
import "./he_thong.css";

/** Markdown MỘT dòng -> phần tử React: chỉ `**đậm**` và `` `mã` `` (cùng hai mẫu
 *  của kome/tai_lieu.py::md_dong). Không innerHTML: chữ nguồn luôn là CHỮ. */
export function md(s: string | null | undefined): ReactNode {
  if (!s) return null;
  const ra: ReactNode[] = [];
  const re = /\*\*(.+?)\*\*|`([^`]+)`/g;
  let cu = 0, k = 0, m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    if (m.index > cu) ra.push(s.slice(cu, m.index));
    ra.push(m[1] != null ? <strong key={k++}>{m[1]}</strong> : <code key={k++}>{m[2]}</code>);
    cu = re.lastIndex;
  }
  if (cu < s.length) ra.push(s.slice(cu));
  return ra;
}

const NHAC = <p className="trong">Chưa sinh tài liệu — chạy <code>python scripts/sinh_tai_lieu.py</code>.</p>;
const cat = (s: string, n: number) => s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s;

type Luong = {
  tang: { mau: string; ma: string; ten: string; mo_ta: string; muc: string[]; giu?: string | null }[];
  nguon: { ten: string; ja: string; mo_ta: string; kieu: string; kieu_mau: string; tan_suat: string; khoa: string[]; core_table: string; mau: string; header_row: number }[];
  chua_nap: { ten_obc: string; mo_ta: string; ghi_chu: string }[];
  cong: { so: number; ten: string; loai: string; chan: boolean }[];
  ranh_gioi: { mau: string; ten: string; ghi_chu: string; muc: { ten: string; chu_thich?: string | null }[] }[];
  nguong: { ja: string; min_rows: number; required_date: string[]; dedup: boolean; total_column: string | null; row_drop: number; spike: number; drop: number;
    product_check: { result: string; factors: string[] } | null }[];
  cam_bay: { ten: string; cach: string }[];
  lo_trinh: { so: string | number; noi_dung: string; du_lieu: string; man: (string | number)[] }[];
};

export function TaiLieuLuong() {
  const m = KD.man as Luong;
  return (
    <KhungKho dang="luong">
      <div className="tai-lieu">
        <h1>Sơ đồ luồng dữ liệu OBC → web app</h1>
        <p className="ghi-chu">Sơ đồ luồng dữ liệu OBC → web app: bảng nào lấy từ đâu, bao lâu một lần, khoá chính là gì, đối chiếu thế nào.</p>
        <section id="bon-tang">
          <h2>Bốn tầng</h2>
          <div className="tang">{m.tang.map(t => (
            <div key={t.ma} className={"tang-o " + t.mau}>
              <div className="tang-dau"><span className="tang-ma">{t.ma}</span> <span className="tang-ten">{t.ten}</span> <span className="khong-ap-dung">· {t.muc.length}</span></div>
              <div className="tang-mo">{t.mo_ta}</div>
              {t.muc.length ? <ul className="tang-ds">{t.muc.map(x => <li key={x}>{x}</li>)}</ul> : NHAC}
              {t.giu && <div className="tang-giu">▸ {t.giu}</div>}
            </div>))}</div>
          <p className="ghi-chu">Một chiều, không ghi ngược vào OBC. Mọi con số trên màn hình lần ngược được về đúng lô và đúng file gốc (<code>batch_id</code>).</p>
        </section>
        <section id="bay-nguon">
          <div className="tieu-de-khoi"><h2>Các nguồn từ OBC</h2><span className="khong-ap-dung">xuất bằng 汎用データ作成 · kéo–thả vào màn Vận hành</span></div>
          <div className="bang-cuon"><table className="bang-tl">
            <thead><tr><th>Nguồn OBC</th><th>Kiểu nạp</th><th>Tần suất</th><th>Khoá chính</th><th>Bảng đích</th><th>Mẫu tên file</th></tr></thead>
            <tbody>{m.nguon.map(n => (
              <tr key={n.ten}><td><div><strong>{n.mo_ta}</strong></div><div><a href={`/kho-du-lieu/cot-noi?file=${n.ten}`}>{n.ja}</a></div></td>
                <td><span className={"vien " + n.kieu_mau}>{n.kieu}</span></td><td>{n.tan_suat}</td>
                <td>{n.khoa.map((k, i) => <span key={k}><code>{k}</code>{i < n.khoa.length - 1 ? " + " : ""}</span>)}</td>
                <td><code>{n.core_table}</code></td>
                <td><code>{n.mau}</code>{n.header_row !== 1 && <span className="khong-ap-dung"> · header dòng {n.header_row}</span>}</td></tr>))}</tbody>
          </table></div>
          <h3>OBC có, hệ thống chưa nạp</h3>
          <div className="bang-cuon"><table className="bang-tl">
            <thead><tr><th>Nguồn OBC</th><th>Nội dung</th><th>Tình trạng</th></tr></thead>
            <tbody>{m.chua_nap.map(c => <tr key={c.ten_obc}><td>{c.ten_obc}</td><td>{c.mo_ta}</td><td>{c.ghi_chu}</td></tr>)}</tbody>
          </table></div>
        </section>
        <div className="hai-cot-tl">
          <section id="doi-chieu">
            <h2>Đối chiếu bắt buộc sau mỗi lần nạp</h2>
            <p className="ghi-chu">Cổng chặn thì lô không được lưu; cổng cảnh báo thì lô vẫn lưu nhưng màn nạp báo ra.</p>
            {m.cong.length ? <div className="the-nk">{m.cong.map(c => (
              <div key={c.so} className="dong-dc"><div><div className="ten-dc">Cổng {c.so}</div><div className="khong-ap-dung">{c.ten}</div></div>
                <span className={"vien " + (c.chan ? "loi" : "canh")}>{c.loai}</span></div>))}</div> : NHAC}
          </section>
          <section id="ai-la-su-that">
            <h2>Ai là sự thật về cái gì</h2>
            <p className="ghi-chu">Trùng vai là nguồn cơn của mọi tranh cãi số liệu.</p>
            <div className="ranh">{m.ranh_gioi.map(r => (
              <div key={r.ten} className={"ranh-o " + r.mau}>
                <div className="ten-dc">{r.ten}</div><div className="khong-ap-dung">{r.ghi_chu}</div>
                {r.muc.length ? <ul>{r.muc.map(x => <li key={x.ten}><code>{x.ten}</code>{x.chu_thich && <> — <span className="khong-ap-dung">{cat(x.chu_thich, 110)}</span></>}</li>)}</ul> : NHAC}
              </div>))}</div>
          </section>
        </div>
        <section id="nguong">
          <h2>Ngưỡng kiểm của từng file</h2>
          <div className="bang-cuon"><table className="bang-tl">
            <thead><tr><th>File</th><th>Tối thiểu (cổng 3)</th><th>Ngày bắt buộc</th><th>Khử trùng khoá</th><th>Cột tiền đại diện</th><th>Cảnh báo số dòng</th><th>Cảnh báo tiền</th><th>Đối chiếu tích (cổng 5)</th></tr></thead>
            <tbody>{m.nguong.map(g => (
              <tr key={g.ja}><td>{g.ja}</td><td className="so">{so(g.min_rows)} dòng</td>
                <td>{g.required_date.length ? g.required_date.map(d => <span key={d}><code>{d}</code> </span>) : "—"}</td>
                <td>{g.dedup ? "có" : "—"}</td>
                <td>{g.total_column ? <code>{g.total_column}</code> : "—"}</td>
                <td>dưới {Math.round(g.row_drop * 100)}% lần trước</td>
                <td>{g.total_column ? <>&gt; {g.spike}× hoặc &lt; {Math.round(g.drop * 100)}% lần trước</> : "—"}</td>
                <td>{g.product_check ? <><code>{g.product_check.result}</code> = {g.product_check.factors.map((f, i) =>
                  <span key={f}><code>{f}</code>{i < g.product_check!.factors.length - 1 ? " × " : ""}</span>)}</> : "—"}</td></tr>))}</tbody>
          </table></div>
        </section>
        <section id="cam-bay">
          <h2>Cạm bẫy riêng của OBC</h2>
          <p className="ghi-chu">Không xử từ đầu thì sáu tháng sau phải làm lại. Sinh từ mục "Bẫy đã biết" của <code>CLAUDE.md</code> — sửa ở đó, không sửa ở đây.</p>
          {m.cam_bay.length ? <div className="luoi-the">{m.cam_bay.map((c, i) => (
            <div key={i} className="the-tl"><div className="ten-dc">{md(c.ten)}</div><div className="than-tl">{md(c.cach)}</div></div>))}</div> : NHAC}
        </section>
        <section id="lo-trinh">
          <h2>Lộ trình</h2>
          {m.lo_trinh.length ? <div className="luoi-the">{m.lo_trinh.map((g, i) => (
            <div key={i} className="the-tl"><div className="lt-dau"><span className="lt-so">{g.so}</span> <span className="ten-dc">{md(g.noi_dung)}</span></div>
              <div className="khong-ap-dung">Dữ liệu mới: {md(g.du_lieu)}</div>
              {g.man.length > 0 && <div className="lt-man">{g.man.map(x => <span key={x} className="vien nhat">màn {x}</span>)}</div>}</div>))}</div> : NHAC}
        </section>
      </div>
    </KhungKho>
  );
}

type CotNoi = {
  file: string; file_ja: string; core_table: string; dong_so_do: number;
  nguon: { ten: string; ja: string }[];
  ma_tran: { cot: { ja: string; vi: string }[]; hang: { ten: string; ja: string; o: string[] }[] };
  noi: { tro_ra: unknown[]; tro_vao: unknown[] };
  so_do: { trai: { ja: string; cot: string; vai: string }[]; phai: { ten: string; ja: string }[]; duong: { d: string; loai: string }[]; cao: number };
  cot: { ja: string; vi: string; kieu: string; vai: string; noi: string }[];
};

export function TaiLieuCotNoi() {
  const m = KD.man as CotNoi;
  return (
    <KhungKho dang="cot-noi">
      <div className="tai-lieu">
        <h1>Cột nối giữa các file OBC</h1>
        <p className="ghi-chu">Mỗi file OBC chỉ ghép được với file khác qua mấy cột mã dưới đây. Mọi cột mã là TEXT — đọc thành số là mất số 0 đầu
          và không ghép được với gì nữa.</p>
        <section id="ma-tran">
          <h2>Ma trận khoá</h2>
          <p className="ghi-chu"><strong>◆</strong> khoá chính · <strong>●</strong> khoá ngoại · <strong>○</strong> có cột nhưng không phải khoá · trống = không có cột.</p>
          <div className="bang-cuon"><table className="bang-tl ma-tran">
            <thead><tr><th>File</th>{m.ma_tran.cot.map(c => <th key={c.vi}>{c.ja}<br /><code>{c.vi}</code></th>)}</tr></thead>
            <tbody>{m.ma_tran.hang.map(h => (
              <tr key={h.ten}><td><a href={`/kho-du-lieu/cot-noi?file=${h.ten}`} aria-current={h.ten === m.file ? "true" : undefined}>{h.ja}</a></td>
                {h.o.map((o, i) => <td key={i} className="o-khoa">{o}</td>)}</tr>))}</tbody>
          </table></div>
        </section>
        <section id="noi-di-dau">
          <h2>File này nối đi đâu</h2>
          <nav className="loc" aria-label="Chọn file">{m.nguon.map(n => (
            <a key={n.ten} href={`/kho-du-lieu/cot-noi?file=${n.ten}#noi-di-dau`} className={n.ten === m.file ? "dang-xem" : undefined}
              aria-current={n.ten === m.file ? "true" : undefined}>{n.ja}</a>))}</nav>
          <div className="the-nk so-do">
            <div className="so-do-tom">{m.file_ja} trỏ ra {m.noi.tro_ra.length} cột · được {m.noi.tro_vao.length} cột của file khác trỏ vào{!m.so_do.trai.length && " — không nối với file nào"}.</div>
            {m.so_do.trai.length > 0 && <>
              <div className="so-do-nhan"><span>CỘT NỐI CỦA FILE ĐANG CHỌN</span><span>GHÉP ĐƯỢC VỚI</span></div>
              {/* Mỗi hàng cao ĐÚNG dong_so_do px — SVG ở giữa vẽ đường theo cùng số đó (kome.tai_lieu.DONG_SO_DO). Đường là trang trí. */}
              <div className="so-do-luoi">
                <ul className="so-do-trai">{m.so_do.trai.map((t, i) => <li key={i} style={{ height: m.dong_so_do }}><span>{t.ja}</span> <code>{t.cot}</code> <span className="khong-ap-dung">{t.vai}</span></li>)}</ul>
                <svg viewBox={`0 0 100 ${m.so_do.cao}`} preserveAspectRatio="none" aria-hidden="true" focusable="false" style={{ height: m.so_do.cao }}>
                  {m.so_do.duong.map((d, i) => <path key={i} d={d.d} className={"duong-" + d.loai} vectorEffect="non-scaling-stroke" />)}
                </svg>
                <ul className="so-do-phai">{m.so_do.phai.map((p, i) => <li key={i} style={{ height: m.dong_so_do }}><a href={`/kho-du-lieu/cot-noi?file=${p.ten}#noi-di-dau`}>{p.ja}</a></li>)}</ul>
              </div>
              <p className="khong-ap-dung so-do-chu">Đường <span className="chu-ra">xanh lam</span>: file này trỏ ra (khoá ngoại) · đường <span className="chu-vao">xanh lá</span>: file khác trỏ vào khoá chính của nó.</p>
            </>}
          </div>
        </section>
        <section id="cot">
          <h2>Cột trong {m.file_ja}</h2>
          <p className="ghi-chu">{m.cot.length} cột khai trong <code>config/files.yml</code> · vào bảng <code>{m.core_table}</code></p>
          <div className="bang-cuon"><table className="bang-tl bang-cot">
            <thead><tr><th>Cột OBC</th><th>Tên hệ thống</th><th>Kiểu</th><th>Vai</th><th>Nối tới</th></tr></thead>
            <tbody>{m.cot.map(c => <tr key={c.vi}><td className="cot-obc">{c.ja}</td><td><code>{c.vi}</code></td><td>{c.kieu}</td><td className="o-khoa">{c.vai}</td><td>{c.noi}</td></tr>)}</tbody>
          </table></div>
        </section>
      </div>
    </KhungKho>
  );
}
