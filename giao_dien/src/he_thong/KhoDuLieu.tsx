// Màn Kho dữ liệu theo gói thiết kế (Kho dữ liệu.dc.html, đợt B 2026-09-24) —
// hai màn con: Tổng quan độ phủ (/kho-du-lieu) và Nạp dữ liệu mới
// (/kho-du-lieu/nap). Máy chủ tính sẵn (kome/web/app.py::_du_lieu_kho /
// _du_lieu_nap — vai trò NẠP, không qua ảnh chụp: phải thấy lô vừa nạp ngay) và
// chèn vào window.__KOME__.man. Màu và câu của từng nguồn tính ở
// kome/kho_du_lieu.py — ở đây chỉ vẽ.
//
// Nạp HAI BƯỚC: thả file vào ô → POST /upload/kiem (5 cổng, KHÔNG ghi gì) → màn
// hiện từng cổng → Xác nhận (POST /upload/xac-nhan, nạp đầy đủ, 5 cổng chạy lại)
// hoặc Huỷ. Mọi nút là biểu mẫu POST THẬT; bản chỉ-đọc (KOME_CHI_DOC) ẩn hẳn khối nạp và
// khối hoàn tác. Hoàn tác nằm sau <details>: người bấm phải đọc "xoá bao nhiêu
// dòng, khỏi bảng nào" trước. Bản Vercel (045) nạp được file hằng ngày, nhưng trần
// 4,5 MB mỗi yêu cầu: trình duyệt chặn file quá KD.gioi_han_tai_len trước khi gửi.
import { useState } from "react";
import { KD } from "../khoi_dau";
import { so, yen } from "../dinh_dang";
import { DaiTuoi } from "../tong_quan/DaiTuoi";
import { KhungKho } from "./TabKho";
import "./he_thong.css";

type O = { trang_thai: string; ky_hieu: string; mo_ta: string };
type Cot = { khoa?: string; nhan: string; chu_giai: string; ten_obc: string; mo_ta?: string };
type Loi = { gate: number; message: string };
type Ket = { spec_name: string | null; skipped: boolean; ok: boolean; row_count: number; total: number;
  blockers: Loi[]; warnings: Loi[] };
type Lo = { batch_id: number; loai: string; ten_file: string; ngay_du_lieu: string | null; nap_luc: string; so_dong: number;
  co_tien: boolean; tong_tien: number; so_dong_xoa: number | null; ten_bang: string; nhieu_hon_luc_nap: boolean; lam_trong_bang: boolean };
type Nut = { ma: string; nhan: string; ja: string; spec: string; nhip: "ngay" | "nen" | "ky"; mau: "ok" | "cho" | "do" | "nen"; cau: string; bang: string;
  nap_hom_nay: boolean; nap_luc: string | null };
type Kiem = { ma: string | null; ten_file: string; o: string; spec_name: string | null; ja: string | null; bang: string | null;
  ok: boolean; skipped: boolean; row_count: number; total: number; co_tien: boolean; data_date: string | null;
  blockers: Loi[]; warnings: Loi[];
  cong: { so: number; ten: string; trang_thai: "dat" | "chan" | "canh" | "khong_chay"; loi: string[] }[] };
type Man = {
  status: { name: string; spec: string; last: string | null; rows: number; total: number; co_tien: boolean }[];
  ky: { dau: string | null; cuoi: string | null; thieu: string[]; tu?: string };
  backup: { stale: boolean; last: string | null } | null;
  nguon: Nut[];
  o_so: { nhan: string; gia: number; phu: string; mau: string }[];
  luoi: { thang: string; truoc: string | null; sau: string | null };
  bang_ngay: { dau: string; cuoi: string; co_thieu: boolean; cot: Cot[]; thieu: Record<string, number>;
    ngay: { ngay: string; nhan_thu: string; la_cuoi_tuan: boolean; o: O[] }[] };
  bang: { dau_du_lieu: string; cot: Cot[]; thieu_bo_nap: { ten_obc: string; mo_ta: string; ghi_chu: string }[];
    ky: { nhan: string; dau: string; cuoi: string; du_12_thang: boolean; doanh_thu_thuan: number; lai_gop: number; ty_suat: number | null;
      thang: { thang: string; company_fy_month: number; la_thang_chot_ky: boolean; o: O[] }[] }[] };
};
type ManNap = { nguon: Nut[]; lo: Lo[]; cho: { ma: string; ten_file: string; o: string; luc: string }[]; kiem?: Kiem[]; results?: Ket[] };

const gio = (iso: string | null) => iso ? `${iso.slice(0, 10)} ${iso.slice(11, 16)}` : "";
const nhanThang = (t: string) => `${+t.slice(5)}/${t.slice(0, 4)}`;

// ---------------------------------------------------------------------------
// Tổng quan độ phủ
// ---------------------------------------------------------------------------

export default function KhoDuLieu() {
  const m = KD.man as Man;
  return (
    <KhungKho dang="tong-quan" lop="kdl">
      <h1>Tổng quan độ phủ dữ liệu</h1>
      <p className="ghi-chu">Có gì trong kho, cập nhật đến ngày nào — theo NGÀY cho 3 loại dữ liệu cập nhật hằng ngày, theo THÁNG cho mọi loại file.</p>
      <section id="hom-nay"><DaiTuoi /></section>
      <SoDoNguon nut={m.nguon} />
      <div className="kdl-o-so">{m.o_so.map(o => (
        <div key={o.nhan} className="kdl-o-so-o"><div className="nhan">{o.nhan}</div>
          <div className={"gia" + (o.mau ? " " + o.mau : "")}>{so(o.gia)}</div><div className="phu">{o.phu}</div></div>))}</div>
      <section id="theo-ngay"><LuoiNgay b={m.bang_ngay} luoi={m.luoi} /></section>
      <SucKhoe m={m} />
      <ChuGiai dau={m.bang.dau_du_lieu} />
      <BangThang b={m.bang} />
    </KhungKho>
  );
}

// Sơ đồ nguồn: OBC ở giữa, mỗi ô nạp một nhánh (vị trí là trang trí — chữ mới là
// thứ đọc được, nên dưới 640px sơ đồ thành lưới thẻ, xem he_thong.css).
const W = 760, H = 500, CX = 380, CY = 250, RX = 285, RY = 190;
const MAU_DAY: Record<Nut["mau"], string> = { ok: "var(--ok-chu)", cho: "var(--canh-chu)", do: "var(--loi-chu)", nen: "var(--vien-dam)" };

function SoDoNguon({ nut }: { nut: Nut[] }) {
  const vi = nut.map((_, i) => {
    const g = -Math.PI / 2 + (2 * Math.PI * i) / nut.length;
    return { x: CX + RX * Math.cos(g), y: CY + RY * Math.sin(g) };
  });
  return (
    <section className="kdl-so-do-khung" aria-label="Các nguồn dữ liệu OBC">
      <div className="kdl-so-do">
        <svg viewBox={`0 0 ${W} ${H}`} aria-hidden="true" focusable="false">
          {vi.map((p, i) => {
            const n = nut[i];
            return <path key={n.ma} d={`M${CX},${CY} Q${(CX + p.x) / 2 + (p.y - CY) * .15},${(CY + p.y) / 2 - (p.x - CX) * .15} ${p.x},${p.y}`}
              fill="none" stroke={MAU_DAY[n.mau]} strokeWidth={n.mau === "nen" ? 1.5 : 2.5} strokeLinecap="round"
              strokeDasharray={n.mau === "nen" ? "4 5" : undefined} />;
          })}
        </svg>
        <div className="kdl-tam"><b>OBC</b><span>hệ thống<br />bán hàng</span></div>
        {nut.map((n, i) => (
          <a key={n.ma} href={`/kho-du-lieu/bang/${n.bang}`} className={"kdl-nut " + n.mau}
            style={{ left: `${(vi[i].x / W) * 100}%`, top: `${(vi[i].y / H) * 100}%` }}>
            <span className="cham" aria-hidden="true" />
            <b>{n.nhan}</b><span className="ja">{n.ja}</span><span className="cau">{n.cau}</span></a>))}
      </div>
      <div className="kdl-chu-giai-nguon">
        <span><i className="ok" />đúng nhịp hằng ngày</span><span><i className="nen" />dữ liệu nền / sổ theo kỳ, ít đổi</span>
        <span><i className="cho" />chưa tới 13:30</span><span><i className="do" />trễ so với nhịp — cần nạp</span>
        <span className="phai">Bấm một nhánh để xem dữ liệu của loại đó.</span>
      </div>
    </section>
  );
}

const TEN_NGAY: Record<string, string> = { ban: "Bán hàng", ton: "Tồn kho", tokuisaki: "Khách hàng" };

function LuoiNgay({ b, luoi }: { b: Man["bang_ngay"]; luoi: Man["luoi"] }) {
  const ngay = [...b.ngay].reverse();              // máy chủ trả mới nhất trước
  const dat = (t: string | null) => t ? `/kho-du-lieu?ngay_thang=${t}#theo-ngay` : undefined;
  return (<>
    <div className="tieu-de-khoi">
      <h2>Theo ngày — tháng {nhanThang(luoi.thang)}</h2>
      <span className="kdl-dieu">
        {luoi.truoc ? <a className="nut-nho" href={dat(luoi.truoc)} aria-label="Tháng trước">‹</a> : <span className="nut-nho mo" aria-hidden="true">‹</span>}
        {luoi.sau ? <a className="nut-nho" href={dat(luoi.sau)} aria-label="Tháng sau">›</a> : <span className="nut-nho mo" aria-hidden="true">›</span>}
      </span>
      <span className="khong-ap-dung">3 loại cập nhật hằng ngày · {b.dau} → {b.cuoi}</span>
    </div>
    {b.co_thieu ? <div className="ngay-thieu">⚠️ Trong tháng này:{" "}
      {b.cot.filter(c => b.thieu[c.khoa!]).map((c, i, a) => <span key={c.khoa}><strong>{c.ten_obc}</strong> thiếu {b.thieu[c.khoa!]} ngày làm việc{i < a.length - 1 ? " · " : ""}</span>)}</div>
      : <div className="backup-ok">✅ Đủ dữ liệu mọi ngày làm việc trong tháng này.</div>}
    <div className="bang-cuon"><table className="phu kdl-luoi">
      <thead><tr><th />{ngay.map(n => <th key={n.ngay} className={n.la_cuoi_tuan ? "nghi" : undefined} title={`${n.ngay} · ${n.nhan_thu}`}>{+n.ngay.slice(8)}</th>)}</tr></thead>
      <tbody>{b.cot.map((c, j) => (
        <tr key={c.nhan}><th className="ten"><div>{TEN_NGAY[c.khoa!] ?? c.nhan}</div><div className="ja">{c.ten_obc}</div></th>
          {ngay.map(n => { const o = n.o[j]; return <td key={n.ngay} className={"o o-" + o.trang_thai} title={`${n.ngay} · ${c.ten_obc}: ${o.mo_ta}`}>{o.ky_hieu}</td>; })}</tr>))}</tbody>
    </table></div>
    <p className="chu-thich">Cuối tuần và ngày lễ để trống — không ai xuất file hôm đó. 4 loại master xuất thưa nằm ở bảng tháng bên dưới.</p>
  </>);
}

// ---------------------------------------------------------------------------
// Nạp dữ liệu mới — hai bước
// ---------------------------------------------------------------------------

export function NapDuLieu() {
  const m = KD.man as ManNap;
  const hangNgay = m.nguon.filter(n => ["ban", "ton", "khach"].includes(n.ma));
  const daNap = hangNgay.filter(n => n.nap_hom_nay);
  return (
    <KhungKho dang="nap" lop="kdl">
      <h1>Nạp dữ liệu mới</h1>
      <p className="ghi-chu">Mỗi loại file OBC một ô. Thả file vào đúng ô của nó — kho chạy <strong>5 cổng kiểm trước khi ghi</strong> và cho xem kết quả;
        bấm <strong>Xác nhận</strong> mới ghi vào kho. Không sửa được số: chỉ nạp thêm, hoặc hoàn tác cả lô.</p>
      <section id="hom-nay"><DaiTuoi /></section>
      {KD.chi_doc ? <div className="ky">Bản này đang tắt nạp dữ liệu — nạp ở máy trong công ty.</div> : <>
        <KhoiKiem ds={m.kiem} />
        <KhoiKet ket={m.results} />
        <Cho ds={m.cho} />
        <Nap nguon={m.nguon} daNap={daNap.length} tong={hangNgay.length} thieu={hangNgay.filter(n => !n.nap_hom_nay).map(n => n.nhan)} />
      </>}
      {!KD.chi_doc && <LoNap lo={m.lo} />}
    </KhungKho>
  );
}

const MB = (b: number) => (b / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 });

// Câu chặn khi tổng cỡ vượt trần của bản web, null nếu gửi được (hoặc không có trần).
function quaCo(files: FileList | null): string | null {
  const tran = KD.gioi_han_tai_len;
  const tong = [...(files ?? [])].reduce((s, f) => s + f.size, 0);
  if (!tran || tong <= tran) return null;
  return `${files!.length > 1 ? `${files!.length} file cộng lại` : "File này"} ${MB(tong)} MB — quá lớn cho bản web `
    + `(tối đa ${MB(tran)} MB). Thả từng file vào ô riêng của nó; file đối soát tháng / cả quý thì nạp ở máy trong công ty.`;
}

function Nap({ nguon, daNap, tong, thieu }: { nguon: Nut[]; daNap: number; tong: number; thieu: string[] }) {
  const [ten, datTen] = useState<string[]>([]);
  const [keo, datKeo] = useState(false);
  const [chan, datChan] = useState<string | null>(null);
  return (
    <section id="nap">
      {chan && <div className="ky" role="alert">{chan}</div>}
      <div className="kdl-tien-do">
        <div className="kdl-tien-do-chu"><b>{daNap}/{tong} file hằng ngày đã nạp hôm nay</b>
          <span className="khong-ap-dung">{thieu.length ? `còn: ${thieu.join(" · ")}` : "đủ nhịp 13:30"}</span></div>
        <div className="kdl-thanh"><div style={{ width: `${tong ? (daNap / tong) * 100 : 0}%` }} /></div>
      </div>
      <div className="kdl-o-nap">{nguon.map(n => (
        <form key={n.ma} method="post" action="/upload/kiem" encType="multipart/form-data" className={"kdl-o " + n.mau}>
          <input type="hidden" name="o" value={n.ma} />
          <label>
            {/* Nhãn "chưa nạp hôm nay" chỉ cho 3 file của nhịp 13:30 — file nền mà mang nhãn đó là một dải đỏ vĩnh viễn. */}
            <span className="kdl-o-dau"><b>{n.nhan}</b>{n.nap_hom_nay ? <span className="vien ok">đã nạp hôm nay</span>
              : n.nhip === "ngay" ? <span className={"vien " + (n.mau === "do" ? "loi" : "canh")}>chưa nạp hôm nay</span>
              : <span className="vien nhat">{n.nhip === "ky" ? "sổ theo kỳ" : "dữ liệu nền"}</span>}</span>
            <span className="ja">{n.ja}</span>
            <span className="kdl-o-tha" aria-hidden="true">⇧ kéo–thả hoặc bấm để chọn file</span>
            <span className="kdl-o-cau">{n.cau}</span>
            <code className="kdl-o-bang">{n.bang}</code>
            {/* Chọn xong là gửi đi kiểm ngay — bước này KHÔNG ghi gì vào kho. */}
            <input className="chon-file" type="file" name="files" required accept=".xlsx" aria-label={`Chọn file ${n.nhan}`}
              onChange={e => {
                const c = quaCo(e.currentTarget.files);
                datChan(c);
                if (c) e.currentTarget.value = "";
                else if (e.currentTarget.files?.length) e.currentTarget.form?.requestSubmit();
              }} />
          </label>
        </form>))}</div>
      {/* MỘT ô nhận NHIỀU file: người làm việc 13:30 thả 3 file một lần. Kho tự nhận loại theo tên file. */}
      <form method="post" action="/upload/kiem" encType="multipart/form-data" className="kdl-nhieu"
        onSubmit={e => {
          const c = quaCo((e.currentTarget.elements.namedItem("files") as HTMLInputElement).files);
          datChan(c);
          if (c) e.preventDefault();
        }}>
        <input type="hidden" name="o" value="" />
        <label className={"drop" + (keo ? " keo" : "")} onDragOver={() => datKeo(true)} onDragLeave={() => datKeo(false)} onDrop={() => datKeo(false)}>
          <b>Nạp nhiều file cùng lúc</b> — kéo thả cả 3 file 13:30 (hay mọi loại) vào đây, kho tự nhận loại theo tên file<br />
          <input className="chon-file" type="file" name="files" multiple required accept=".xlsx"
            onChange={e => datTen([...(e.target.files ?? [])].map(f => f.name))} />
          {ten.length > 0 && <span className="kdl-ten-file">{ten.length} file: {ten.join(" · ")}</span>}
        </label>
        <p><button className="nut-nap" type="submit">Kiểm {ten.length > 1 ? `${ten.length} file` : "file"}</button></p>
      </form>
    </section>
  );
}

const KY_CONG = { dat: "✓", chan: "✗", canh: "⚠", khong_chay: "·" } as const;
const CHU_CONG = { dat: "đạt", chan: "chặn", canh: "cảnh báo", khong_chay: "không chạy — cổng trước đã chặn" } as const;

function KhoiKiem({ ds }: { ds?: Kiem[] }) {
  if (!ds?.length) return null;
  const cho = ds.filter(k => k.ma);
  return (
    <section id="kiem" className="kdl-kiem">
      <h2>Kết quả kiểm — chưa ghi gì vào kho</h2>
      {ds.map((k, i) => (
        <div key={i} className={"kdl-kiem-o " + (k.ma ? "ok" : k.skipped ? "nhat" : "loi")}>
          <div className="kdl-kiem-ten"><b>{k.ten_file}</b>{k.ja && <span className="khong-ap-dung"> · {k.ja}{k.data_date && ` · ngày dữ liệu ${k.data_date}`}</span>}</div>
          {k.skipped ? <p>⏭️ File này đã nạp rồi (cùng nội dung) — không cần nạp lại.</p> : <>
            <ul className="kdl-cong">{k.cong.map(c => (
              <li key={c.so} className={c.trang_thai}><span className="ky" aria-hidden="true">{KY_CONG[c.trang_thai]}</span>
                <span className="so">Cổng {c.so}</span><span className="ten">{c.ten}</span><span className="kq">{CHU_CONG[c.trang_thai]}</span>
                {c.loi.map((l, j) => <div key={j} className="cong-loi">{l}</div>)}</li>))}</ul>
            {k.ma ? <div className="kdl-kiem-chot">Qua đủ 5 cổng — <b>{so(k.row_count)} dòng</b>{k.co_tien && <> · {yen(k.total)}</>}, sẵn sàng ghi vào <code>{k.bang}</code>.</div>
              : <div className="kq-loi">❌ Không nạp được file này — sửa theo dòng cổng bị chặn rồi xuất lại từ OBC.</div>}
          </>}
          {k.ma && <div className="kdl-nut-hang">
            <form method="post" action="/upload/xac-nhan"><input type="hidden" name="ma" value={k.ma} /><button type="submit" className="nut-nap">Xác nhận nạp vào kho</button></form>
            <form method="post" action="/upload/huy"><input type="hidden" name="ma" value={k.ma} /><button type="submit" className="nut-nho">Huỷ</button></form>
          </div>}
        </div>))}
      {cho.length > 1 && <form method="post" action="/upload/xac-nhan" className="kdl-nut-hang">
        {cho.map(k => <input key={k.ma} type="hidden" name="ma" value={k.ma!} />)}
        <button type="submit" className="nut-nap">Xác nhận nạp cả {cho.length} file</button></form>}
    </section>
  );
}

function Cho({ ds }: { ds: ManNap["cho"] }) {
  if (!ds.length) return null;
  return (
    <section id="cho">
      <h2>Đang chờ xác nhận</h2>
      <p className="chu-thich">File đã kiểm nhưng chưa ai bấm Xác nhận. Xác nhận là kiểm lại 5 cổng trên kho lúc này rồi mới ghi. File chờ quá 24 giờ tự bị dọn.</p>
      <ul className="kdl-cho">{ds.map(c => (
        <li key={c.ma}><b>{c.ten_file}</b> <span className="khong-ap-dung">kiểm lúc {c.luc.replace("T", " ")}</span>
          <form method="post" action="/upload/xac-nhan"><input type="hidden" name="ma" value={c.ma} /><button type="submit" className="nut-nho">Xác nhận</button></form>
          <form method="post" action="/upload/huy"><input type="hidden" name="ma" value={c.ma} /><button type="submit" className="nut-nho">Huỷ</button></form></li>))}</ul>
    </section>
  );
}

function KhoiKet({ ket }: { ket?: Ket[] }) {
  if (!ket?.length) return null;
  return (
    <section id="ket-qua">
      <h2>Kết quả nạp</h2>
      <ul className="kdl-ket">
        {ket.map((r, i) => (
          <li key={i}>
            {r.skipped ? <span className="kq-ok">⏭️ {r.spec_name} — file này đã nạp rồi, bỏ qua</span>
              : r.ok ? <span className="kq-ok">✅ {r.spec_name} — {so(r.row_count)} dòng · {yen(r.total)}</span>
              : <span className="kq-loi">❌ {r.spec_name || "?"} — KHÔNG nạp</span>}
            {r.blockers.map((b, k) => <div key={k} className="kq-loi">Cổng {b.gate}: {b.message}</div>)}
            {r.warnings.map((w, k) => <div key={k} className="kq-canh">⚠️ Cổng {w.gate}: {w.message}</div>)}
          </li>))}
      </ul>
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

