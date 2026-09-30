// Màn Kho dữ liệu — MỘT trang "Nạp dữ liệu" (2026-09-30, chủ DN: "chủ yếu để upload dữ liệu và xem dữ liệu",
// "ít chữ, nhiều visual"): ba ô file 13:30 · hàng nút file khác · kết quả kiểm / nạp · lô gần nhất + hoàn tác ·
// lịch dữ liệu (lưới tháng × loại, bấm tháng xem từng ngày). Chữ giải thích nằm trong ô nổi ⓘ. Sức khoẻ /
// loại chưa vào kho / hạn chế sang "Tình trạng kho" (/kho-du-lieu/tinh-trang, mục Nâng cao).
// /kho-du-lieu và /kho-du-lieu/nap vẽ CÙNG màn này. Máy chủ tính sẵn (kome/web/app.py::_du_lieu_kho —
// vai trò NẠP, không qua ảnh chụp: phải thấy lô vừa nạp ngay) vào window.__KOME__.man. Màu và câu của
// từng nguồn tính ở kome/kho_du_lieu.py, mọi ô lưới ở kome/coverage.py::tinh_luoi_phu — ở đây chỉ vẽ.
//
// Nạp HAI BƯỚC: thả file vào ô → POST /upload/kiem (5 cổng, KHÔNG ghi gì) → màn hiện từng cổng → Xác nhận
// (POST /upload/xac-nhan, nạp đầy đủ, 5 cổng chạy lại) hoặc Huỷ. Mọi nút là biểu mẫu POST THẬT; bản
// chỉ-đọc (KOME_CHI_DOC) ẩn hẳn khối nạp và khối hoàn tác. Hoàn tác nằm sau <details>: người bấm phải đọc
// "xoá bao nhiêu dòng, khỏi bảng nào" trước. Bản Vercel (045) nạp được file hằng ngày, nhưng trần 4,5 MB
// mỗi yêu cầu: trình duyệt chặn file quá KD.gioi_han_tai_len trước khi gửi.
import { useState, type ChangeEvent, type ReactNode } from "react";
import { KD } from "../khoi_dau";
import { gio_tokyo, ngay, so, yen } from "../dinh_dang";
import { giuKhoang } from "../khung/khoang";
import { ONoi } from "../chung/ONoi";
import { KhungKho } from "./TabKho";
import "./he_thong.css";

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
  backup?: { stale: boolean; last: string | null } | null;
  nguon: Nut[];
  phu: Phu;
  ngay_thang: string | null;
  thieu_bo_nap: { ten_obc: string; mo_ta: string; ghi_chu: string }[];
  lo: Lo[];
  cho: { ma: string; ten_file: string; o: string; luc: string }[];
  kiem?: Kiem[];
  results?: Ket[];
};

type OL = { trang_thai: "du" | "thieu" | "khong" | "moi" | "trong"; so_co: number; meisai: boolean; ngay: string };
type DongL = { khoa: string; spec: string; nhan: string; ten_obc: string; nhom: "lich_su" | "nen"; bang: string;
  o: OL[]; dau: string | null; cuoi: string | null; thieu: string[] };
type ThangL = { thang: string; ky: string; chot: boolean; so_kd: number; lich: string };
type Phu = { dau_du_lieu: string; hom_nay: string; thang: ThangL[]; dong: DongL[] };

// Giờ Tokyo, không cắt chuỗi ISO (sẽ ra giờ UTC) — dinh_dang.gio_tokyo.
const gio = (iso: string | null) => gio_tokyo(iso);
const nhanThang = (t: string) => `${+t.slice(5)}/${t.slice(0, 4)}`;

export default function KhoDuLieu() {
  const m = KD.man as Man;
  const p = m.phu;
  // Tháng đang mở chi tiết từng ngày: chỉ khi URL chọn sẵn (?ngay_thang=) hoặc người bấm — mặc định gọn.
  const [chon, datChon] = useState<number | null>(() => {
    const i = p.thang.findIndex(t => t.thang === m.ngay_thang);
    return i >= 0 ? i : null;
  });
  const doiThang = (i: number | null, cuon = false) => {
    datChon(i);
    history.replaceState(null, "", giuKhoang(i == null ? location.pathname : `${location.pathname}?ngay_thang=${p.thang[i].thang}`));
    if (cuon && i != null) requestAnimationFrame(() => document.getElementById("theo-ngay")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };
  return (
    <KhungKho dang="nap" lop="kdl kdl-gon-man">
      <h1>Nạp dữ liệu</h1>
      {m.backup?.stale && <a className="kdl-bao loi" href="/kho-du-lieu/tinh-trang#suc-khoe">⚠ Chưa sao lưu {m.backup.last ? `từ ${gio(m.backup.last)}` : ""} — xem Tình trạng kho</a>}
      {KD.chi_doc ? <div className="ky">Bản này đang tắt nạp dữ liệu — nạp ở máy trong công ty.</div> : <>
        <KhoiKiem ds={m.kiem} />
        <KhoiKet ket={m.results} />
        <Cho ds={m.cho} />
        <Nap nguon={m.nguon} />
      </>}
      {!KD.chi_doc && <LoNap lo={m.lo} />}
      <Lich m={m} chon={chon} doiThang={doiThang} />
      {chon != null && <ChiTietThang p={p} i={chon} doiThang={doiThang} />}
    </KhungKho>
  );
}

// /kho-du-lieu/nap và các trang kết quả POST /upload* vẽ đúng màn trên.
export const NapDuLieu = KhoDuLieu;

// ---------------------------------------------------------------------------
// Ô thả file
// ---------------------------------------------------------------------------

const MB = (b: number) => (b / 1_000_000).toLocaleString("ja-JP", { maximumFractionDigits: 1 });

// Câu chặn khi tổng cỡ vượt trần của bản web, null nếu gửi được (hoặc không có trần).
function quaCo(files: FileList | null): string | null {
  const tran = KD.gioi_han_tai_len;
  const tong = [...(files ?? [])].reduce((s, f) => s + f.size, 0);
  if (!tran || tong <= tran) return null;
  return `${files!.length > 1 ? `${files!.length} file cộng lại` : "File này"} ${MB(tong)} MB — quá lớn cho bản web `
    + `(tối đa ${MB(tran)} MB). Thả từng file vào ô riêng của nó; file đối soát tháng / cả quý thì nạp ở máy trong công ty.`;
}

// Chọn xong là gửi đi kiểm ngay — bước này KHÔNG ghi gì vào kho.
function guiKhiChon(datChan: (c: string | null) => void) {
  return (e: ChangeEvent<HTMLInputElement>) => {
    const c = quaCo(e.currentTarget.files);
    datChan(c);
    if (c) e.currentTarget.value = "";
    else if (e.currentTarget.files?.length) e.currentTarget.form?.requestSubmit();
  };
}

type TrangThaiO = "ok" | "cho" | "do" | "nghi" | "nen";
function trangThai(n: Nut): TrangThaiO {
  if (n.nap_hom_nay) return "ok";
  if (n.nhip !== "ngay") return "nen";
  // Ngày nghỉ (cuối tuần, lễ) không ai xuất file — nhắc "chưa nạp" hôm đó là nhắc sai.
  if (n.cau.startsWith("hôm nay nghỉ")) return "nghi";
  return n.mau === "do" ? "do" : "cho";
}

function ChiTietNguon({ n }: { n: Nut }) {
  return <><b>{n.nhan}</b> · <span className="ten-jp">{n.ja}</span><br />{n.cau}<br /><code>{n.bang}</code></>;
}

function Nap({ nguon }: { nguon: Nut[] }) {
  const [chan, datChan] = useState<string | null>(null);
  const [keo, datKeo] = useState<string | null>(null);
  const hangNgay = nguon.filter(n => n.nhip === "ngay");
  const khac = nguon.filter(n => n.nhip !== "ngay");
  const o = (n: Nut, lon: boolean) => {
    const tt = trangThai(n);
    return (
      <form key={n.ma} method="post" action="/upload/kiem" encType="multipart/form-data"
        className={`kdl-tha ${lon ? "lon" : "nho"} ${tt}` + (keo === n.ma ? " keo" : "")}>
        <input type="hidden" name="o" value={n.ma} />
        <label onDragEnter={() => datKeo(n.ma)} onDragLeave={() => datKeo(null)} onDrop={() => datKeo(null)}>
          <span className="kdl-tha-ky" aria-hidden="true">{tt === "ok" ? "✓" : lon ? "⇧" : "＋"}</span>
          <b>{n.nhan}</b>
          {lon && <span className="kdl-tha-phu">{tt === "ok" ? gio(n.nap_luc).slice(-5) : tt === "nghi" ? "nghỉ" : "thả file"}</span>}
          <input className="chon-file" type="file" name="files" required accept=".xlsx" aria-label={`Chọn file ${n.nhan}`}
            onChange={guiKhiChon(datChan)} />
        </label>
        <ONoi className="kdl-tha-i" nhan={`Chi tiết ${n.nhan}`} noi_dung={<ChiTietNguon n={n} />}>ⓘ</ONoi>
      </form>);
  };
  return (<>
    {chan && <div className="ky" role="alert">{chan}</div>}
    <section id="hom-nay" className="kdl-tha-ba" aria-label="Ba file hằng ngày 13:30">{hangNgay.map(n => o(n, true))}</section>
    <section id="nap" className="kdl-tha-hang" aria-label="File khác">
      {khac.map(n => o(n, false))}
      {/* MỘT ô nhận NHIỀU file: thả cả 3 file 13:30 một lần — kho tự nhận loại theo tên file. */}
      <form method="post" action="/upload/kiem" encType="multipart/form-data" className={"kdl-tha nho nhieu" + (keo === "*" ? " keo" : "")}
        onSubmit={e => {
          // Ô nhiều file kiểm TỔNG cỡ cả lúc gửi (không chỉ lúc chọn).
          const c = quaCo((e.currentTarget.elements.namedItem("files") as HTMLInputElement).files);
          datChan(c);
          if (c) e.preventDefault();
        }}>
        <input type="hidden" name="o" value="" />
        <label onDragEnter={() => datKeo("*")} onDragLeave={() => datKeo(null)} onDrop={() => datKeo(null)}>
          <span className="kdl-tha-ky" aria-hidden="true">⧉</span><b>Nhiều file</b>
          <input className="chon-file" type="file" name="files" multiple required accept=".xlsx" aria-label="Chọn nhiều file"
            onChange={guiKhiChon(datChan)} />
        </label>
        <ONoi className="kdl-tha-i" nhan="Nạp nhiều file" noi_dung="Thả nhiều file cùng lúc — kho tự nhận loại theo tên file.">ⓘ</ONoi>
      </form>
    </section>
  </>);
}

// ---------------------------------------------------------------------------
// Kiểm · chờ · kết quả
// ---------------------------------------------------------------------------

const KY_CONG = { dat: "✓", chan: "✗", canh: "⚠", khong_chay: "·" } as const;
const CHU_CONG = { dat: "đạt", chan: "chặn", canh: "cảnh báo", khong_chay: "không chạy — cổng trước đã chặn" } as const;

function KhoiKiem({ ds }: { ds?: Kiem[] }) {
  if (!ds?.length) return null;
  const cho = ds.filter(k => k.ma);
  return (
    <section id="kiem" className="kdl-kiem" aria-label="Kết quả kiểm — chưa ghi gì vào kho">
      {ds.map((k, i) => (
        <div key={i} className={"kdl-kiem-o " + (k.ma ? "ok" : k.skipped ? "nhat" : "loi")}>
          <div className="kdl-kiem-ten"><b>{k.ten_file}</b>
            {!k.skipped && <ul className="kdl-cong-cham" aria-label="5 cổng kiểm">{k.cong.map(c => (
              <li key={c.so} className={c.trang_thai} title={`Cổng ${c.so} · ${c.ten}: ${CHU_CONG[c.trang_thai]}`}>{KY_CONG[c.trang_thai]}</li>))}</ul>}
            {k.ma && <span className="kdl-kiem-so">{so(k.row_count)} dòng{k.co_tien && <> · {yen(k.total)}</>}</span>}
          </div>
          {k.skipped ? <p>⏭ Đã nạp rồi (cùng nội dung).</p>
            : k.cong.flatMap(c => c.loi.map((l, j) => <div key={c.so + "-" + j} className={"cong-loi " + c.trang_thai}>Cổng {c.so}: {l}</div>))}
          {!k.ma && !k.skipped && <div className="kq-loi">✗ Không nạp được — sửa theo dòng trên rồi xuất lại từ OBC.</div>}
          {k.ma && <div className="kdl-nut-hang">
            <form method="post" action="/upload/xac-nhan"><input type="hidden" name="ma" value={k.ma} /><button type="submit" className="nut-nap">Xác nhận nạp</button></form>
            <form method="post" action="/upload/huy"><input type="hidden" name="ma" value={k.ma} /><button type="submit" className="nut-nho">Huỷ</button></form>
          </div>}
        </div>))}
      {cho.length > 1 && <form method="post" action="/upload/xac-nhan" className="kdl-nut-hang">
        {cho.map(k => <input key={k.ma} type="hidden" name="ma" value={k.ma!} />)}
        <button type="submit" className="nut-nap">Xác nhận cả {cho.length} file</button></form>}
    </section>
  );
}

function Cho({ ds }: { ds: Man["cho"] }) {
  if (!ds.length) return null;
  return (
    <section id="cho" aria-label="Đang chờ xác nhận">
      <ul className="kdl-cho">{ds.map(c => (
        <li key={c.ma}><span aria-hidden="true">⏳</span><b>{c.ten_file}</b>
          <ONoi nhan="Đang chờ xác nhận" noi_dung="Đã kiểm, chưa ai bấm Xác nhận. Xác nhận là kiểm lại 5 cổng rồi mới ghi. Chờ quá 24 giờ tự bị dọn.">
            <span className="khong-ap-dung">{c.luc.replace("T", " ").slice(0, 16)}</span></ONoi>
          <form method="post" action="/upload/xac-nhan"><input type="hidden" name="ma" value={c.ma} /><button type="submit" className="nut-nho">Xác nhận</button></form>
          <form method="post" action="/upload/huy"><input type="hidden" name="ma" value={c.ma} /><button type="submit" className="nut-nho">Huỷ</button></form></li>))}</ul>
    </section>
  );
}

function KhoiKet({ ket }: { ket?: Ket[] }) {
  if (!ket?.length) return null;
  return (
    <section id="ket-qua" aria-label="Kết quả nạp">
      <ul className="kdl-ket">
        {ket.map((r, i) => (
          <li key={i}>
            {r.skipped ? <span className="kq-ok">⏭ {r.spec_name} — đã nạp rồi, bỏ qua</span>
              : r.ok ? <span className="kq-ok">✓ {r.spec_name} — {so(r.row_count)} dòng · {yen(r.total)}</span>
              : <span className="kq-loi">✗ {r.spec_name || "?"} — KHÔNG nạp</span>}
            {r.blockers.map((b, k) => <div key={k} className="kq-loi">Cổng {b.gate}: {b.message}</div>)}
            {r.warnings.map((w, k) => <div key={k} className="kq-canh">⚠ Cổng {w.gate}: {w.message}</div>)}
          </li>))}
      </ul>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Lô gần nhất + hoàn tác
// ---------------------------------------------------------------------------

const LO_GON = 5;

function LoNap({ lo }: { lo: Lo[] }) {
  const [het, datHet] = useState(false);
  const ds = het ? lo : lo.slice(0, LO_GON);
  return (
    <section id="lo-nap">
      <div className="kdl-dau-nho"><span aria-hidden="true">↺</span> Lô gần nhất</div>
      {!lo.length ? <p className="trong">Chưa có lô nạp nào.</p> : <ul className="kdl-lo">{ds.map(l => (
        <li key={l.batch_id}>
          <ONoi className="kdl-lo-ten" nhan={`Lô ${l.batch_id}`} noi_dung={<><code>{l.ten_file}</code><br />nạp {gio(l.nap_luc)} · lô {l.batch_id}</>}>
            <b>{l.loai}</b><span>{l.ngay_du_lieu ?? ""}</span></ONoi>
          <span className="so">{so(l.so_dong)}</span>
          <span className="so">{l.co_tien ? yen(l.tong_tien) : ""}</span>
          <details className="hoan-tac"><summary>Hoàn tác</summary>
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
          </details>
        </li>))}</ul>}
      {lo.length > LO_GON && <button type="button" className="nut-nho" onClick={() => datHet(!het)}>{het ? "Thu gọn" : `+ ${lo.length - LO_GON} lô`}</button>}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Lịch dữ liệu — lưới tháng × loại dữ liệu (đặc tả 2026-09-25-tong-quan-do-phu-luoi-design.md, bản gọn
// 2026-09-30). Máy chủ tính mọi ô (kome/coverage.py::tinh_luoi_phu), kể cả từng NGÀY của mọi tháng — đổi
// tháng không hỏi máy chủ.
// ---------------------------------------------------------------------------

const CHU_O: Record<OL["trang_thai"], string> = {
  du: "đủ mọi ngày làm việc", thieu: "thiếu một phần", khong: "không có dữ liệu",
  moi: "có xuất bản mới trong tháng", trong: "không có bản mới — vẫn dùng bản trước",
};

function moTaO(d: DongL, o: OL, t: ThangL) {
  const dau = `${d.nhan} · ${nhanThang(t.thang)}: `;
  if (d.nhom === "nen") return dau + (o.so_co ? `${o.so_co} lần xuất bản mới` : CHU_O.trong);
  if (o.trang_thai === "khong") return dau + CHU_O.khong;
  return dau + `${o.so_co}/${t.so_kd} ngày làm việc có dữ liệu` + (o.meisai ? " · có ngày lấy từ 売上明細表" : "");
}

// Cả THÁNG trống giữa ngày đầu và ngày cuối (sự cố thật: tháng 8/2026) — gọi đích danh: mọi màn coi tháng đó là bán ¥0.
function thangTrong(d: DongL, p: Phu) {
  return d.dau ? p.thang.filter((t, i) => d.o[i].trang_thai === "khong"
    && t.thang > d.dau!.slice(0, 7) && t.thang < d.cuoi!.slice(0, 7)).map(t => nhanThang(t.thang)) : [];
}

function TenDong({ d, p }: { d: DongL; p: Phu }) {
  const trong = d.nhom === "lich_su" ? thangTrong(d, p) : [];
  const canh = trong.length > 0 ? "loi" : d.thieu.length ? "canh" : "";
  return (
    <ONoi className="kdl-l-ten" href={`/kho-du-lieu/bang/${d.bang}`} nhan={d.nhan} noi_dung={<>
      <b>{d.nhan}</b> · <span className="ten-jp">{d.ten_obc}</span><br />
      {d.dau ? <>{ngay(d.dau)} → {ngay(d.cuoi)}</> : "chưa có dữ liệu"}
      {d.nhom === "lich_su" && d.dau && <><br />{d.thieu.length ? `thiếu ${d.thieu.length} ngày làm việc` : "không thiếu ngày làm việc nào"}</>}
      {trong.length > 0 && <><br /><b>cả tháng không có dòng nào: {trong.join(" · ")}</b> — mọi màn đang coi là ¥0</>}
      {d.nhom === "nen" && <><br />dữ liệu nền — bản mới đè bản cũ, tháng trống không phải thiếu</>}
    </>}>
      <b>{d.nhan}</b>{canh && <i className={"kdl-l-dau " + canh} aria-hidden="true" />}
    </ONoi>);
}

function Lich({ m, chon, doiThang }: { m: Man; chon: number | null; doiThang: (i: number | null, cuon?: boolean) => void }) {
  const p = m.phu, n = p.thang.length;
  const dong = [...p.dong.filter(d => d.nhom === "lich_su"), ...p.dong.filter(d => d.nhom === "nen")];
  return (
    <section id="theo-thang" aria-label="Lịch dữ liệu theo tháng">
      <div className="kdl-dau-nho"><span aria-hidden="true">▦</span> Lịch dữ liệu
        <ONoi className="kdl-i" nhan="Cách đọc lịch" noi_dung={<>Mỗi dòng một loại dữ liệu, mỗi cột một tháng — bấm tháng để xem từng ngày.
          Ngày nghỉ (cuối tuần, lễ) không tính là thiếu; ngày nghỉ riêng của công ty kho không biết. Kỳ kế toán 1/8 → 31/7.</>}>ⓘ</ONoi></div>
      <div className="bang-cuon">
        <div className="kdl-l kdl-l-gon" style={{ gridTemplateColumns: `minmax(6.5rem,9rem) repeat(${n}, minmax(1.4rem,1fr))` }}>
          <div />{p.thang.map((t, i) => (
            <button key={t.thang} type="button" className={"kdl-l-thang" + (i === chon ? " chon" : "") + (t.chot ? " chot" : "")}
              aria-pressed={i === chon} aria-label={`Xem từng ngày tháng ${nhanThang(t.thang)}`} onClick={() => doiThang(i === chon ? null : i, true)}>
              {+t.thang.slice(5)}<span>{i === 0 || t.thang.endsWith("-01") ? `’${t.thang.slice(2, 4)}` : " "}</span></button>))}
          {dong.flatMap(d => [
            <TenDong key={d.khoa + "-ten"} d={d} p={p} />,
            ...d.o.map((o, i) => (
              <div key={d.khoa + i} className={`kdl-l-o o-${o.trang_thai}` + (o.meisai ? " meisai" : "") + (i === chon ? " chon" : "")}
                title={moTaO(d, o, p.thang[i])} onClick={() => doiThang(i, true)}>
                {o.trang_thai === "thieu" ? o.so_co : ""}</div>)),
          ])}
        </div>
      </div>
      <div className="kdl-l-chu-giai">
        <span><i className="kdl-l-o o-du" />đủ</span>
        <span><i className="kdl-l-o o-thieu">5</i>thiếu</span>
        <span><i className="kdl-l-o o-khong" />không có</span>
        <span><i className="kdl-l-o o-moi" />bản mới</span>
        <span><i className="kdl-l-o o-du meisai" />từ 売上明細表</span>
      </div>
    </section>
  );
}

const LOP_NGAY: Record<string, string> = { c: "o-du", m: "o-du meisai", k: "o-khong", n: "o-nghi", x: "o-ngoai", b: "o-moi", ".": "" };
const CHU_NGAY: Record<string, string> = { c: "có dữ liệu", m: "có dữ liệu (từ 売上明細表)", k: "THIẾU — ngày làm việc không có dữ liệu",
  n: "ngày nghỉ", x: "trước ngày đầu của kho — không tồn tại", b: "có xuất bản mới", ".": "không có bản mới" };

function ChiTietThang({ p, i, doiThang }: { p: Phu; i: number; doiThang: (i: number | null) => void }) {
  const t = p.thang[i];
  if (!t) return null;
  const viec: { d: DongL; cau: ReactNode }[] = [];
  for (const d of p.dong.filter(d => d.nhom === "lich_su")) {
    const thieu = d.thieu.filter(x => x.startsWith(t.thang));
    if (thieu.length) viec.push({ d, cau: <>thiếu <strong>{thieu.map(x => +x.slice(8)).join(", ")}</strong></> });
  }
  return (
    <section id="theo-ngay">
      <div className="tieu-de-khoi">
        <span className="kdl-dieu">
          <button type="button" className="nut-nho" disabled={i === 0} onClick={() => doiThang(i - 1)} aria-label="Tháng trước">‹</button>
          <b>{nhanThang(t.thang)}</b>
          <button type="button" className="nut-nho" disabled={i === p.thang.length - 1} onClick={() => doiThang(i + 1)} aria-label="Tháng sau">›</button>
        </span>
        <span className="khong-ap-dung">{t.so_kd} ngày làm việc{t.chot ? " · tháng chốt kỳ" : ""}</span>
        <button type="button" className="nut-nho kdl-dong" onClick={() => doiThang(null)} aria-label="Đóng từng ngày">✕</button>
      </div>
      <div className="bang-cuon">
        <div className="kdl-l kdl-l-ngay" style={{ gridTemplateColumns: `minmax(6.5rem,9rem) repeat(${t.lich.length}, minmax(1.25rem,1fr))` }}>
          <div />{[...t.lich].map((c, j) => <div key={j} className={"kdl-l-so" + (c === "0" ? " nghi" : "")}>{j + 1}</div>)}
          {p.dong.flatMap(d => [
            <div key={d.khoa} className="kdl-l-ten"><b>{d.nhan}</b></div>,
            ...[...d.o[i].ngay].map((c, j) => <div key={d.khoa + j} className={"kdl-l-o " + LOP_NGAY[c]}
              title={`${j + 1}/${nhanThang(t.thang)} · ${d.nhan}: ${CHU_NGAY[c]}`} />),
          ])}
        </div>
      </div>
      {viec.length ? viec.map(v => (
        <ONoi key={v.d.khoa} className="ngay-thieu" nhan={v.d.nhan} noi_dung={<>Xuất lại {v.d.ten_obc} của đúng những ngày đó từ OBC rồi nạp.</>}>
          <strong>{v.d.nhan}</strong> {v.cau}</ONoi>))
        : <div className="backup-ok">✓ Đủ mọi ngày làm việc.</div>}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Tình trạng kho (/kho-du-lieu/tinh-trang, mục Nâng cao) — sức khoẻ, lần nạp cuối, loại chưa vào kho, hạn chế.
// ---------------------------------------------------------------------------

export function TinhTrangKho() {
  const m = KD.man as Man;
  return (
    <KhungKho dang="tinh-trang" lop="kdl">
      <h1>Tình trạng kho</h1>
      <CuoiTrang m={m} />
    </KhungKho>
  );
}

function CuoiTrang({ m }: { m: Man }) {
  const b = m.backup;
  return (<>
    <section id="suc-khoe" className="kdl-gon">
      <h2>Sức khoẻ dữ liệu — sao lưu, lần nạp cuối</h2>
      {/* backup null ở bản chỉ-đọc: máy chủ công khai không thấy thư mục sao lưu — im lặng đúng hơn một dải đỏ vĩnh viễn. */}
      {b == null ? <div className="ky">💾 Tình trạng sao lưu chỉ xem được trên bản chạy ở máy trong công ty.</div>
        : b.stale ? <div className="backup-bad">⚠️ Chưa sao lưu {b.last ? `từ ${gio(b.last)}` : "— chưa có bản sao lưu nào"} — chạy sao lưu ngay:
          <code>python -c "from ops.backup import dump, prune; import os, pathlib; dump(os.environ['DATABASE_URL'], pathlib.Path('backups')); prune(pathlib.Path('backups'))"</code></div>
        : <div className="backup-ok">✅ Sao lưu gần nhất: {gio(b.last)}</div>}
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
    <section className="kdl-gon">
      <h2>Loại dữ liệu chưa vào kho</h2>
      <div className="bang-cuon"><table><tbody>{m.thieu_bo_nap.map(l => <tr key={l.ten_obc}><td>{l.ten_obc}</td><td>{l.mo_ta}</td><td>{l.ghi_chu}</td></tr>)}</tbody></table></div>
    </section>
    <section className="kdl-gon">
      <h2>Hạn chế cần biết</h2>
      <div className="ky">📌 Dữ liệu bán hàng bắt đầu từ <strong>{ngay(m.phu.dau_du_lieu)}</strong>. Trước mốc đó dữ liệu{" "}
        <strong>không tồn tại</strong> (công ty không còn lưu) — lịch bắt đầu từ tháng đó, không có gì để đi tìm.</div>
      <div className="ngay-thieu">⚠️ Ô "không có dữ liệu" <strong>không phân biệt được</strong> hai trường hợp: (a) chưa bao giờ xuất file cho
        khoảng đó, và (b) đã xuất nhưng file bị cổng kiểm tra chặn (bản xuất thiếu dòng, sai mẫu…). Cổng kiểm tra chặn <strong>trước khi</strong>{" "}
        ghi nhật ký nạp, nên kho không hề biết file đó từng tồn tại. Muốn biết chắc thì đối chiếu với thư mục xuất của OBC.</div>
      <div className="ky">Kỳ kế toán của công ty: <strong>1/8 → 31/7</strong> năm sau (không phải 1/4 → 31/3). Ngày nghỉ riêng của công ty
        (Obon, cuối năm) kho không biết, nên vẫn đếm là ngày làm việc — kiểm tra trước khi đi tìm file.</div>
    </section>
  </>);
}
