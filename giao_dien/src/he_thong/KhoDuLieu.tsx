// Màn Kho dữ liệu theo gói thiết kế (Kho dữ liệu.dc.html, đợt B 2026-09-24) —
// hai màn con: Tổng quan độ phủ (/kho-du-lieu — lưới tháng × loại dữ liệu từ
// 2026-09-25) và Nạp dữ liệu mới
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
import { useState, type ReactNode } from "react";
import { KD } from "../khoi_dau";
import { gio_tokyo, ngay, so, yen } from "../dinh_dang";
import { giuKhoang } from "../khung/khoang";
import { DaiTuoi } from "../tong_quan/DaiTuoi";
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
  backup: { stale: boolean; last: string | null } | null;
  nguon: Nut[];
  phu: Phu;
  ngay_thang: string | null;
  thieu_bo_nap: { ten_obc: string; mo_ta: string; ghi_chu: string }[];
};
type ManNap = { nguon: Nut[]; lo: Lo[]; cho: { ma: string; ten_file: string; o: string; luc: string }[]; kiem?: Kiem[]; results?: Ket[] };

// Giờ Tokyo, không cắt chuỗi ISO (sẽ ra giờ UTC) — dinh_dang.gio_tokyo.
const gio = (iso: string | null) => gio_tokyo(iso);
const nhanThang = (t: string) => `${+t.slice(5)}/${t.slice(0, 4)}`;

// ---------------------------------------------------------------------------
// Tổng quan độ phủ — lưới tháng × loại dữ liệu (đặc tả
// 2026-09-25-tong-quan-do-phu-luoi-design.md). Câu hỏi của màn: "đã có dữ liệu
// tháng nào, loại nào". Máy chủ tính mọi ô (kome/coverage.py::tinh_luoi_phu),
// kể cả từng NGÀY của mọi tháng — đổi tháng ở khối chi tiết không hỏi máy chủ.
// ---------------------------------------------------------------------------

export default function KhoDuLieu() {
  const m = KD.man as Man;
  const p = m.phu;
  const [chon, datChon] = useState(() => {
    const i = p.thang.findIndex(t => t.thang === m.ngay_thang);
    return i >= 0 ? i : p.thang.length - 1;
  });
  const doiThang = (i: number, cuon = false) => {
    datChon(i);
    history.replaceState(null, "", giuKhoang(`/kho-du-lieu?ngay_thang=${p.thang[i].thang}`));
    if (cuon) document.getElementById("theo-ngay")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  return (
    <KhungKho dang="tong-quan" lop="kdl">
      <h1>Tổng quan độ phủ dữ liệu</h1>
      <p className="ghi-chu">Kho đang có dữ liệu tháng nào, của loại nào. Mỗi dòng một loại dữ liệu, mỗi cột một tháng — bấm một tháng để xem từng ngày.</p>
      <TomTat m={m} />
      <LuoiThang m={m} chon={chon} doiThang={doiThang} />
      <ChiTietThang p={p} i={chon} doiThang={doiThang} />
      <CuoiTrang m={m} />
    </KhungKho>
  );
}

type OL = { trang_thai: "du" | "thieu" | "khong" | "moi" | "trong"; so_co: number; meisai: boolean; ngay: string };
type DongL = { khoa: string; spec: string; nhan: string; ten_obc: string; nhom: "lich_su" | "nen"; bang: string;
  o: OL[]; dau: string | null; cuoi: string | null; thieu: string[] };
type ThangL = { thang: string; ky: string; chot: boolean; so_kd: number; lich: string };
type Phu = { dau_du_lieu: string; hom_nay: string; thang: ThangL[]; dong: DongL[] };

const nutCua = (nguon: Nut[], d: DongL) => nguon.find(n => n.spec === d.spec);

function TomTat({ m }: { m: Man }) {
  const p = m.phu;
  const hangNgay = m.nguon.filter(n => n.nhip === "ngay");
  const da = hangNgay.filter(n => n.nap_hom_nay);
  // Ngày nghỉ (cuối tuần, lễ) không ai xuất file — "0/3 · còn: …" hôm đó là một nhắc việc sai.
  const nghi = hangNgay.length > 0 && hangNgay.every(n => n.cau.startsWith("hôm nay nghỉ"));
  const mauHomNay = nghi ? "" : hangNgay.some(n => n.mau === "do") ? "loi" : da.length < hangNgay.length ? "canh" : "ok";
  return (
    <section id="hom-nay" className="kdl-tt">
      {m.phu.dong.filter(d => d.nhom === "lich_su").map(d => {
        const meisai = d.o.filter(o => o.meisai).length;
        // Cả THÁNG trống giữa ngày đầu và ngày cuối (sự cố thật: tháng 8/2026) — gọi
        // đích danh, không để nó chìm trong "thiếu n ngày": mọi màn coi tháng đó là bán ¥0.
        const trong = d.dau ? p.thang.filter((t, i) => d.o[i].trang_thai === "khong"
          && t.thang > d.dau!.slice(0, 7) && t.thang < d.cuoi!.slice(0, 7)).map(t => nhanThang(t.thang)) : [];
        return (
          <div key={d.khoa} className="kdl-tt-o">
            <div className="nhan">{d.nhan} có liên tục</div>
            <div className="gia">{d.dau ? <>{ngay(d.dau)} → {ngay(d.cuoi)}</> : "chưa có dữ liệu"}</div>
            {d.dau && <div className={"phu " + (d.thieu.length ? "canh" : "ok")}>{d.thieu.length
              ? `thiếu ${d.thieu.length} ngày làm việc`
              : "không thiếu ngày làm việc nào"}</div>}
            {trong.length > 0 && <div className="phu loi">cả tháng không có dòng nào: {trong.join(" · ")} — mọi màn đang coi là ¥0</div>}
            {meisai > 0 && <div className="phu">{meisai} tháng có ngày lấy từ 売上明細表</div>}
          </div>);
      })}
      <div className="kdl-tt-o">
        <div className="nhan">Hôm nay (nhịp 13:30)</div>
        <div className="gia">{da.length}/{hangNgay.length} file đã nạp</div>
        <div className={"phu " + mauHomNay}>{nghi && da.length < hangNgay.length ? "hôm nay nghỉ — không cần nạp"
          : da.length === hangNgay.length ? "đủ nhịp"
          : "còn: " + hangNgay.filter(n => !n.nap_hom_nay).map(n => n.nhan).join(" · ")}</div>
      </div>
    </section>
  );
}

const CHU_O: Record<OL["trang_thai"], string> = {
  du: "đủ mọi ngày làm việc", thieu: "thiếu một phần", khong: "không có dữ liệu",
  moi: "có xuất bản mới trong tháng", trong: "không có bản mới — vẫn dùng bản trước",
};

function moTaO(d: DongL, o: OL, t: ThangL) {
  const dau = `${d.nhan} · tháng ${nhanThang(t.thang)}: `;
  if (d.nhom === "nen") return dau + (o.so_co ? `${o.so_co} lần xuất bản mới` : CHU_O.trong);
  if (o.trang_thai === "khong") return dau + CHU_O.khong;
  return dau + `${o.so_co}/${t.so_kd} ngày làm việc có dữ liệu` + (o.meisai ? " · có ngày lấy từ 売上明細表" : "");
}

function LuoiThang({ m, chon, doiThang }: { m: Man; chon: number; doiThang: (i: number, cuon?: boolean) => void }) {
  const p = m.phu, n = p.thang.length;
  // Dải kỳ kế toán: gộp các tháng liền nhau cùng một kỳ thành một ô.
  const ky: { ky: string; so: number }[] = [];
  p.thang.forEach(t => { if (ky.length && ky[ky.length - 1].ky === t.ky) ky[ky.length - 1].so++; else ky.push({ ky: t.ky, so: 1 }); });
  const nhom = [["lich_su", "Lịch sử — mỗi ngày một phần, thiếu ngày là thiếu số"],
    ["nen", "Dữ liệu nền — bản mới đè bản cũ, tháng trống không phải thiếu"]] as const;
  return (
    <section id="theo-thang" aria-label="Độ phủ theo tháng">
      <div className="bang-cuon">
        <div className="kdl-l" style={{ gridTemplateColumns: `minmax(8.5rem,11rem) repeat(${n}, minmax(1.7rem,1fr)) minmax(8rem,12rem)` }}>
          <div />{ky.map(k => <div key={k.ky} className="kdl-l-ky" style={{ gridColumn: `span ${k.so}` }}>{k.ky}</div>)}<div />
          <div />{p.thang.map((t, i) => (
            <button key={t.thang} type="button" className={"kdl-l-thang" + (i === chon ? " chon" : "") + (t.chot ? " chot" : "")}
              aria-pressed={i === chon} aria-label={`Xem từng ngày tháng ${nhanThang(t.thang)}`} onClick={() => doiThang(i, true)}>
              {+t.thang.slice(5)}<span>{i === 0 || t.thang.endsWith("-01") ? `’${t.thang.slice(2, 4)}` : " "}</span></button>))}
          <div className="kdl-l-dau-cot">Tình trạng</div>
          {nhom.map(([ma, nhan]) => {
            const ds = p.dong.filter(d => d.nhom === ma);
            return ds.length ? [
              <div key={ma} className="kdl-l-nhom">{nhan}</div>,
              ...ds.flatMap(d => {
                const nut = nutCua(m.nguon, d);
                return [
                  <a key={d.khoa + "-ten"} className="kdl-l-ten" href={`/kho-du-lieu/bang/${d.bang}`}><b>{d.nhan}</b><span>{d.ten_obc}</span></a>,
                  ...d.o.map((o, i) => (
                    <div key={d.khoa + i} className={`kdl-l-o o-${o.trang_thai}` + (o.meisai ? " meisai" : "") + (i === chon ? " chon" : "")}
                      title={moTaO(d, o, p.thang[i])} onClick={() => doiThang(i, true)}>
                      {o.trang_thai === "thieu" ? o.so_co : ""}</div>)),
                  <div key={d.khoa + "-tt"} className={"kdl-l-tt " + (nut?.mau ?? "nen")}>
                    {nut?.cau ?? ""}{d.nhom === "nen" && d.cuoi && <span>bản {ngay(d.cuoi)}</span>}</div>,
                ];
              }),
            ] : null;
          })}
        </div>
      </div>
      <div className="kdl-l-chu-giai">
        <span><i className="kdl-l-o o-du" />đủ mọi ngày làm việc</span>
        <span><i className="kdl-l-o o-du meisai" />đủ, có ngày lấy từ 売上明細表 (ít cột, doanh thu chưa thuế)</span>
        <span><i className="kdl-l-o o-thieu">5</i>thiếu một phần — số là ngày làm việc có dữ liệu</span>
        <span><i className="kdl-l-o o-khong" />không có dữ liệu</span>
        <span><i className="kdl-l-o o-moi" />có xuất bản mới trong tháng</span>
        <span><i className="kdl-chot-mau" />tháng chốt kỳ</span>
      </div>
    </section>
  );
}

const LOP_NGAY: Record<string, string> = { c: "o-du", m: "o-du meisai", k: "o-khong", n: "o-nghi", x: "o-ngoai", b: "o-moi", ".": "" };
const CHU_NGAY: Record<string, string> = { c: "có dữ liệu", m: "có dữ liệu (từ 売上明細表)", k: "THIẾU — ngày làm việc không có dữ liệu",
  n: "ngày nghỉ", x: "trước ngày đầu của kho — không tồn tại", b: "có xuất bản mới", ".": "không có bản mới" };

function ChiTietThang({ p, i, doiThang }: { p: Phu; i: number; doiThang: (i: number) => void }) {
  const t = p.thang[i];
  if (!t) return null;
  const lichSu = p.dong.filter(d => d.nhom === "lich_su");
  const viec: { loai: string; d: DongL; cau: ReactNode }[] = [];
  for (const d of lichSu) {
    const o = d.o[i], thieu = d.thieu.filter(x => x.startsWith(t.thang));
    if (thieu.length) viec.push({ loai: "canh", d, cau: <>thiếu {thieu.length} ngày làm việc: <strong>{thieu.map(x => +x.slice(8)).join(", ")}</strong> — xuất
      lại {d.ten_obc} của đúng những ngày đó từ OBC rồi nạp.</> });
    else if (o.trang_thai === "khong") viec.push({ loai: "nhat", d, cau: <>chưa có dữ liệu tháng này{d.dau && t.thang < d.dau.slice(0, 7)
      ? <> — dữ liệu bắt đầu từ {ngay(d.dau)}</> : null}.</> });
  }
  const coMeisai = lichSu.some(d => d.o[i].meisai);
  return (
    <section id="theo-ngay">
      <div className="tieu-de-khoi">
        <h2>Từng ngày — tháng {nhanThang(t.thang)}</h2>
        <span className="kdl-dieu">
          <button type="button" className="nut-nho" disabled={i === 0} onClick={() => doiThang(i - 1)} aria-label="Tháng trước">‹</button>
          <button type="button" className="nut-nho" disabled={i === p.thang.length - 1} onClick={() => doiThang(i + 1)} aria-label="Tháng sau">›</button>
        </span>
        <span className="khong-ap-dung">{t.ky} · {t.so_kd} ngày làm việc{t.chot ? " · tháng chốt kỳ" : ""}</span>
      </div>
      <div className="bang-cuon">
        <div className="kdl-l kdl-l-ngay" style={{ gridTemplateColumns: `minmax(8.5rem,11rem) repeat(${t.lich.length}, minmax(1.25rem,1fr))` }}>
          <div />{[...t.lich].map((c, j) => <div key={j} className={"kdl-l-so" + (c === "0" ? " nghi" : "")}>{j + 1}</div>)}
          {p.dong.flatMap(d => [
            <div key={d.khoa} className="kdl-l-ten"><b>{d.nhan}</b><span>{d.ten_obc}</span></div>,
            ...[...d.o[i].ngay].map((c, j) => <div key={d.khoa + j} className={"kdl-l-o " + LOP_NGAY[c]}
              title={`${j + 1}/${nhanThang(t.thang)} · ${d.nhan}: ${CHU_NGAY[c]}`} />),
          ])}
        </div>
      </div>
      {viec.length ? viec.map(v => <div key={v.d.khoa} className={v.loai === "canh" ? "ngay-thieu" : "ky"}><strong>{v.d.nhan}</strong> {v.cau}</div>)
        : <div className="backup-ok">✅ Đủ dữ liệu mọi ngày làm việc trong tháng này.</div>}
      {coMeisai && <div className="ky">Ô sọc: ngày bán lấy từ <strong>売上明細表</strong> — bản đó ít cột hơn 売上伝票データ và doanh thu là số chưa thuế.</div>}
      <p className="chu-thich">Ngày nghỉ (cuối tuần, ngày lễ quốc gia) không bao giờ tính là thiếu. Ngày nghỉ riêng của công ty (Obon, cuối năm) kho
        không biết, nên vẫn đếm là ngày làm việc — kiểm tra trước khi đi tìm file.</p>
    </section>
  );
}

function CuoiTrang({ m }: { m: Man }) {
  const b = m.backup;
  return (<>
    {/* Sao lưu cũ thì khối tự mở: một cảnh báo nằm sau nút thu gọn là cảnh báo không ai đọc. */}
    <details id="suc-khoe" className="kdl-gon" open={b?.stale || undefined}>
      <summary><h2>Sức khoẻ dữ liệu — sao lưu, lần nạp cuối</h2></summary>
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
    </details>
    <details className="kdl-gon">
      <summary><h2>Loại dữ liệu chưa vào kho</h2></summary>
      <div className="bang-cuon"><table><tbody>{m.thieu_bo_nap.map(l => <tr key={l.ten_obc}><td>{l.ten_obc}</td><td>{l.mo_ta}</td><td>{l.ghi_chu}</td></tr>)}</tbody></table></div>
    </details>
    <details className="kdl-gon">
      <summary><h2>Hạn chế cần biết</h2></summary>
      <div className="ky">📌 Dữ liệu bán hàng bắt đầu từ <strong>{ngay(m.phu.dau_du_lieu)}</strong>. Trước mốc đó dữ liệu{" "}
        <strong>không tồn tại</strong> (công ty không còn lưu) — lưới bắt đầu từ tháng đó, không có gì để đi tìm.</div>
      <div className="ngay-thieu">⚠️ Ô "không có dữ liệu" <strong>không phân biệt được</strong> hai trường hợp: (a) chưa bao giờ xuất file cho
        khoảng đó, và (b) đã xuất nhưng file bị cổng kiểm tra chặn (bản xuất thiếu dòng, sai mẫu…). Cổng kiểm tra chặn <strong>trước khi</strong>{" "}
        ghi nhật ký nạp, nên kho không hề biết file đó từng tồn tại. Muốn biết chắc thì đối chiếu với thư mục xuất của OBC.</div>
      <div className="ky">Dải trên đầu lưới là kỳ kế toán của công ty: <strong>1/8 → 31/7</strong> năm sau (không phải 1/4 → 31/3).</div>
    </details>
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
