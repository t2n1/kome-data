// Kho dữ liệu → xem MỘT bảng (đợt C, 2026-09-24; gói thiết kế: khối `laBang` của
// Kho dữ liệu.dc.html). Ba tab: Dữ liệu (tìm trên cả dòng, 50 dòng/trang, lọc
// nhanh, CSV) · Cột & khoá · Lần nạp. Mọi thứ đọc bằng vai trò chỉ-đọc
// (kome/bang_kho.py — READ ONLY, tên bảng tra từ danh mục). Màn này KHÔNG ghi gì:
// hoàn tác một lô vẫn ở màn Nạp (nơi có câu "xoá bao nhiêu dòng").
import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { KD } from "../khoi_dau";
import { lay } from "../api";
import { so, yen } from "../dinh_dang";
import { KhungKho } from "./TabKho";
import "./he_thong.css";

type Cot = { ten: string; kieu: string; khong_rong: boolean; khoa_chinh: boolean; khoa_ngoai: string | null; ghi_chu: string | null; ja: string | null };
type LanNap = { batch_id: number; spec: string; ten_file: string; duong_dan: string | null; digest: string; nap_luc: string;
  so_dong: number; tong_tien: number; ngay_du_lieu: string | null; huy_luc: string | null };
type ThongTin = { ten: string; schema: string; ngan: string; loai: "bang" | "view"; so_dong: number | null; mo_ta: string | null;
  cot: Cot[]; khoa_chinh: string[]; nguon: { spec: string; ja: string }[]; cot_ngay: string | null; co_lo: boolean; lan_nap: LanNap[] };
type Dong = { dong: unknown[][]; tong: number; trang: number; moi_trang: number; chip: string };

const TAB = [["du-lieu", "Dữ liệu"], ["cot", "Cột & khoá"], ["nap", "Lần nạp"]] as const;
const SO = /^(integer|bigint|smallint|numeric.*|double precision|real)$/;
// Tách hàng nghìn CHỈ cho cột tiền / lượng (bigint, numeric…) — integer là năm, tháng, số thứ tự: "2.024" là sai.
const SO_NHOM = /^(bigint|numeric.*|double precision|real)$/;
const gio = (iso: string | null) => iso ? `${iso.slice(0, 10)} ${iso.slice(11, 16)}` : "";

function oGia(v: unknown, kieu: string) {
  if (v === null || v === undefined) return <span className="khong-ap-dung">∅</span>;
  // Cột mã là TEXT — không bao giờ định dạng như số (mất số 0 đầu là hỏng mọi liên kết).
  if (typeof v === "number" && SO_NHOM.test(kieu)) return so(v);
  if (typeof v === "boolean") return v ? "true" : "false";
  const s = String(v);
  return s.length > 80 ? <span title={s}>{s.slice(0, 79)}…</span> : s;
}

export default function BangKho() {
  const ten = (KD.man as { bang: string }).bang;
  const [tab, datTab] = useState<typeof TAB[number][0]>("du-lieu");
  const tt = useQuery({ queryKey: ["kdl-bang", ten], queryFn: () => lay<ThongTin>(`/api/kho-du-lieu/bang/${ten}`) });
  const t = tt.data;
  return (
    <KhungKho dang="bang" bang={ten} lop="kdl">
      {tt.isError ? <><h1>{ten}</h1><div className="khoi-loi">{(tt.error as Error).message}</div></>
        : !t ? <><h1>{ten}</h1><p className="khong-ap-dung">Đang tải…</p></> : <>
          <div className="kdl-bang-dau">
            <div>
              <div className="kdl-bang-schema">{t.schema} · {t.loai === "bang" ? "bảng" : "view — tính lại mỗi lần đọc"}</div>
              <h1>{t.ngan}</h1>
              {t.mo_ta && <p className="ghi-chu">{t.mo_ta}</p>}
            </div>
          </div>
          <div className="kdl-bang-meta">
            <span>Nguồn OBC <b>{t.nguon.length ? t.nguon.map(n => n.ja).join(" / ") : "—"}</b></span>
            <span>Khoá chính <b>{t.khoa_chinh.length ? t.khoa_chinh.join(" + ") : "—"}</b></span>
            <span>{t.so_dong != null ? <>khoảng <b>{so(t.so_dong)}</b> dòng</> : "view: không lưu dòng nào"}</span>
            {t.lan_nap[0] && <span>Nạp gần nhất <b>{gio(t.lan_nap.find(l => !l.huy_luc)?.nap_luc ?? null) || "—"}</b></span>}
          </div>
          <div className="kdl-bang-tab" role="tablist">{TAB.map(([ma, nhan]) => (
            <button key={ma} type="button" role="tab" aria-selected={tab === ma} onClick={() => datTab(ma)}>
              {nhan}{ma === "nap" && ` (${t.lan_nap.length})`}{ma === "cot" && ` (${t.cot.length})`}</button>))}</div>
          {tab === "du-lieu" && <DuLieu t={t} />}
          {tab === "cot" && <CotKhoa t={t} />}
          {tab === "nap" && <LanNapTab t={t} />}
          <p className="chu-thich">Chỉ đọc. Muốn sửa số thì sửa ở OBC rồi xuất lại và nạp — màn này không ghi vào kho.</p>
        </>}
    </KhungKho>
  );
}

function DuLieu({ t }: { t: ThongTin }) {
  const [tim, datTim] = useState("");
  const [timGui, datTimGui] = useState("");
  const [chip, datChip] = useState("tat_ca");
  const [trang, datTrang] = useState(1);
  useEffect(() => { const h = setTimeout(() => { datTimGui(tim); datTrang(1); }, 350); return () => clearTimeout(h); }, [tim]);
  const q = new URLSearchParams({ tim: timGui, chip, trang: String(trang) }).toString();
  const d = useQuery({ queryKey: ["kdl-dong", t.ten, q], queryFn: () => lay<Dong>(`/api/kho-du-lieu/bang/${t.ten}/dong?${q}`),
    placeholderData: keepPreviousData });
  const chips: [string, string, string | null][] = [
    ["tat_ca", "Tất cả", null],
    ["thang", "Tháng gần nhất", t.cot_ngay ? null : "Bảng không có cột ngày"],
    ["lo", "Lô mới nhất", t.co_lo ? null : "Bảng không mang batch_id"],
    ["canh", "Có cảnh báo", "Chưa có nguồn: cổng kiểm cảnh báo theo LÔ, không đánh dấu từng dòng"],
  ];
  const r = d.data;
  const so_trang = r ? Math.max(1, Math.ceil(r.tong / r.moi_trang)) : 1;
  const csv = `/api/kho-du-lieu/bang/${t.ten}/csv?${new URLSearchParams({ tim: timGui, chip }).toString()}`;
  return (
    <div>
      <div className="kdl-bang-loc">
        <input type="search" value={tim} onChange={e => datTim(e.target.value)} placeholder="Lọc trong bảng — mã, tên, ngày…" aria-label="Lọc trong bảng" />
        {chips.map(([ma, nhan, tat]) => (
          <button key={ma} type="button" className="kdl-chip" aria-pressed={chip === ma} disabled={!!tat} title={tat ?? undefined}
            onClick={() => { datChip(ma); datTrang(1); }}>{nhan}</button>))}
        <a className="nut-nho" href={csv} download>Tải CSV</a>
      </div>
      {t.loai === "view" && <p className="chu-thich">View của <code>mart</code> tính lại toàn bộ mỗi lần đọc — trang đầu có thể mất vài giây.</p>}
      {d.isError ? <div className="khoi-loi">{(d.error as Error).message}</div> : <>
        <div className={"bang-cuon kdl-bang-luoi" + (d.isFetching ? " dang-tai" : "")}><table className="bang-tl">
          <thead><tr>{t.cot.map(c => (
            <th key={c.ten} className={SO.test(c.kieu) ? "so" : undefined} title={c.ja ? `${c.ja} — ${c.kieu}` : c.kieu}>
              <div>{c.ten}</div>
              <div className="kdl-cot-kieu">{c.kieu}{c.khoa_chinh && <span className="vien loi">◆</span>}{c.khoa_ngoai && <span className="vien lam">●</span>}</div></th>))}</tr></thead>
          <tbody>{r?.dong.map((row, i) => (
            <tr key={i}>{row.map((v, j) => <td key={j} className={SO.test(t.cot[j]?.kieu ?? "") ? "so" : undefined}>{oGia(v, t.cot[j]?.kieu ?? "")}</td>)}</tr>))}
            {r && !r.dong.length && <tr><td colSpan={t.cot.length} className="trong">Không có dòng nào khớp.</td></tr>}</tbody>
        </table></div>
        <div className="kdl-trang">
          <span>{r ? <>{so(r.tong)} dòng khớp · trang {r.trang}/{so_trang}</> : "Đang tải…"}</span>
          <span className="kdl-nut-hang">
            <button type="button" className="nut-nho" disabled={trang <= 1} onClick={() => datTrang(trang - 1)}>‹ Trước</button>
            <button type="button" className="nut-nho" disabled={trang >= so_trang} onClick={() => datTrang(trang + 1)}>Sau ›</button>
          </span>
        </div>
      </>}
    </div>
  );
}

function CotKhoa({ t }: { t: ThongTin }) {
  return (
    <div className="bang-cuon"><table className="bang-tl">
      <thead><tr><th>Cột trong kho</th><th>Tên gốc OBC</th><th>Kiểu</th><th>Khoá / ràng buộc</th><th>Ghi chú</th></tr></thead>
      <tbody>{t.cot.map(c => (
        <tr key={c.ten}><td><code>{c.ten}</code></td><td className="cot-obc">{c.ja ?? "—"}</td><td>{c.kieu}</td>
          <td>{[c.khoa_chinh && "◆ khoá chính", c.khoa_ngoai && `● trỏ tới ${c.khoa_ngoai}`, c.khong_rong && !c.khoa_chinh && "không rỗng"]
            .filter(Boolean).join(" · ") || "—"}</td>
          <td className="khong-ap-dung">{c.ghi_chu ?? ""}</td></tr>))}</tbody>
    </table></div>
  );
}

function LanNapTab({ t }: { t: ThongTin }) {
  if (!t.nguon.length) return <p className="trong">Bảng này không do file OBC nào nạp trực tiếp{t.schema === "mart" ? " — nó là chỉ số tính từ các bảng core" : ""}.</p>;
  if (!t.lan_nap.length) return <p className="trong">Chưa có lần nạp nào vào bảng này.</p>;
  return (<>
    <div className="kdl-lan-nap">{t.lan_nap.map(l => (
      <div key={l.batch_id} className={"kdl-lan-nap-o" + (l.huy_luc ? " huy" : "")}>
        <div className="kdl-lan-nap-ten">
          <b>{l.ten_file}</b> <span className={"vien " + (l.huy_luc ? "nhat" : "ok")}>{l.huy_luc ? `đã hoàn tác ${gio(l.huy_luc)}` : "còn hiệu lực"}</span>
          {l.duong_dan && <div className="khong-ap-dung"><code>{l.duong_dan}</code></div>}
          <div className="khong-ap-dung">sha256 {l.digest.slice(0, 12)}… · lô #{l.batch_id}{l.ngay_du_lieu && ` · ngày dữ liệu ${l.ngay_du_lieu}`}</div>
        </div>
        <div className="kdl-lan-nap-so">
          <div><div className="khong-ap-dung">Nạp lúc</div>{gio(l.nap_luc)}</div>
          <div><div className="khong-ap-dung">Số dòng</div>{so(l.so_dong)}</div>
          <div><div className="khong-ap-dung">Tổng tiền</div>{l.tong_tien ? yen(l.tong_tien) : "—"}</div>
        </div>
      </div>))}</div>
    {!KD.chi_doc && <p className="chu-thich">Hoàn tác một lô ở màn <a href="/kho-du-lieu/nap#lo-nap">Nạp dữ liệu mới</a> — ở đó có câu nói rõ sẽ xoá bao nhiêu dòng.</p>}
  </>);
}
