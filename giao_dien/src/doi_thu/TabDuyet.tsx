import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { gui, lay } from "../api";
import type { NhomQuyCach, TongQuan } from "./kieu";
import { nhomIdHopLe } from "./loc";
import { Khoi } from "../chung/Khoi";
import { ngay, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { QuanSat } from "./kieu";
import { NHAN_DUYET } from "./kieu";
import { NguonDong, Ra } from "./NguonDong";
import { cacThangCho, lienKetAnToan, nhanThang, thangCua } from "./nguon";

const LOC = [["", "Tất cả"], ["can_xem", "Cần xem"], ["bat_thuong", "Bất thường"], ["chua_xac_nhan", "Chưa ai xác nhận"], ["chua_ghep", "Chưa ghép"]];
const LOAI_NGUON = [["bang_gia", "Bảng giá / web"], ["chung_tu", "Chứng từ khách đưa"], ["to_roi", "Tờ rơi / tin nhắn"], ["khach_ke", "Khách kể"], ["khac", "Nghe nói / khác"]];
// Trường có tập giá trị đóng (khớp CHECK của bảng) là ô chọn; còn lại là ô gõ.
const CHON: Partial<Record<keyof QuanSat, string[][]>> = {
  thue: [["chua", "Chưa thuế"], ["co", "Đã gồm thuế"], ["khong_ro", "Không rõ"]],
  gom_ship: [["co", "Đã gồm ship"], ["khong", "Chưa gồm ship"], ["khong_ro", "Không rõ"]],
  trang_thai: [["con", "Còn"], ["het", "Hết"], ["sap_ve", "Sắp về"], ["khong_ro", "Không rõ"]],
};
const TRUONG: [keyof QuanSat, string][] = [["ten_goc", "Tên"], ["quy_cach_goc", "Quy cách"], ["gia_goc", "Giá"], ["don_vi_gia", "Đơn vị"],
  ["kg_moi_don_vi_gia", "Kg / đơn vị"], ["thue", "Thuế"], ["gom_ship", "Ship"],
  ["kenh_gia", "Kênh"], ["muc_gia", "Mức"], ["trang_thai", "Trạng thái"]];

const HANG_MOI_TRONG = { ma_doi_thu: "", ten_goc: "", quy_cach_goc: "", gia_goc: "", don_vi_gia: "", kg_moi_don_vi_gia: "",
  thue: "khong_ro", gom_ship: "khong_ro", trang_thai: "con", loai_nguon: "", ghi_chu_nguon: "", lien_ket_bang_chung: "" };
const NHAN_HANG_MOI: [keyof typeof HANG_MOI_TRONG, string][] = [["ten_goc", "Tên hàng"], ["quy_cach_goc", "Quy cách"], ["gia_goc", "Giá"],
  ["don_vi_gia", "Đơn vị giá"], ["kg_moi_don_vi_gia", "Kg / đơn vị giá"], ["ghi_chu_nguon", "Ghi chú nguồn"]];

/** Một dòng "Thư mục Drive tháng …": link đã lưu (nút mở + đổi) hoặc ô dán link (đặc tả §11.1). */
const NGUON_TRONG = { loai_nguon: "", ghi_chu_nguon: "", lien_ket_bang_chung: "" };

function ThuMucThang({ thang, hien, xong }: { thang: string; hien: string | null; xong: () => void }) {
  const [sua, datSua] = useState(false);
  const [gt, datGt] = useState("");
  const [loi, datLoi] = useState<string | null>(null);
  const [dang, datDang] = useState(false);
  const [daLuu, datDaLuu] = useState<string | null>(null);   // link vừa lưu — giữ hiện tới khi truy vấn lại về
  useEffect(() => { datDaLuu(null); }, [hien]);
  const co = daLuu ?? hien;
  const nhan = nhanThang(thang);
  const luu = () => {
    if (dang) return;
    datDang(true);
    const lk = gt.trim();
    gui("/api/doi-thu/thu-muc", { thang, lien_ket: lk })
      .then(() => { datDaLuu(lienKetAnToan(lk)); datSua(false); datGt(""); datLoi(null); xong(); })
      .catch((e: Error) => datLoi(e.message)).finally(() => datDang(false));
  };
  return (
    <p className="dt-thu-muc">Thư mục Drive {nhan}:{" "}
      {co && !sua ? <>
        <Ra href={co}>Mở thư mục ↗</Ra>{" "}
        <button type="button" className="chip" aria-label={`Đổi link thư mục Drive ${nhan}`} onClick={() => { datGt(co); datSua(true); }}>đổi</button>
      </> : <>
        <input type="url" aria-label={`Link thư mục Drive ${nhan}`} placeholder="https://drive.google.com/…" value={gt}
          onChange={e => datGt(e.target.value)} />{" "}
        <button type="button" className="chip" aria-label={`Lưu link thư mục ${nhan}`} disabled={dang || !gt.trim()} onClick={luu}>Lưu</button>
        {co && <> <button type="button" className="chip" aria-label={`Bỏ sửa link thư mục ${nhan}`} onClick={() => { datSua(false); datLoi(null); }}>Bỏ</button></>}
      </>}
      {loi && <span role="alert" className="dt-loi"> {loi}</span>}
    </p>);
}

export function TabDuyet({ ben, boBen }: { ben: string; boBen: () => void }) {
  const kx = chuoiKhoang(useKhoang());
  const qc = useQueryClient();
  const [loc, datLoc] = useState("can_xem");
  const url = `/api/doi-thu/duyet?${new URLSearchParams({ ben, loc })}${kx ? "&" + kx : ""}`;
  const q = useQuery({ queryKey: ["doi-thu", "duyet", ben, loc, kx], queryFn: () => lay<{ dong: QuanSat[] }>(url) });
  const [chon, datChon] = useState<QuanSat | null>(null);
  const [sua, datSua] = useState<Record<string, string>>({});
  const [nguon, datNguon] = useState(NGUON_TRONG);
  const [maKome, datMaKome] = useState("");
  const [loi, datLoi] = useState<string | null>(null);          // lỗi của khung sửa / ghép dòng đang chọn
  const [loiThem, datLoiThem] = useState<string | null>(null);  // lỗi của form thêm hàng
  const [dang_gui, datDangGui] = useState(false);
  const [nhomId, datNhomId] = useState("");
  const [moThem, datMoThem] = useState(false);
  const [moi, datMoi] = useState(HANG_MOI_TRONG);
  const tq = useQuery({ queryKey: ["doi-thu", "tong-quan", kx],
    queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const nq = useQuery({ queryKey: ["doi-thu", "nhom-quy-cach", kx], enabled: !!chon && chon.nguon === "nap",
    queryFn: () => lay<NhomQuyCach>(`/api/doi-thu/nhom-quy-cach${kx ? "?" + kx : ""}`) });
  const nhomCoTen = nq.data?.nhom ?? [];
  const nhomChon = nhomIdHopLe(nhomCoTen, nhomId);  // chỉ nhóm CÓ trong ô chọn mới được gửi
  const tenBen = tq.data?.ben.find(b => b.ma === ben)?.ten ?? ben;
  const xong = () => { datChon(null); datSua({}); datNguon(NGUON_TRONG); datLoi(null); datMaKome(""); datNhomId(""); qc.invalidateQueries({ queryKey: ["doi-thu"] }); };
  // Chống bấm đúp: mọi nút ghi khoá tới khi yêu cầu xong (thành công hay lỗi).
  const lam = (gui_di: () => Promise<unknown>, sau: () => void = xong, datL = datLoi) => {
    if (dang_gui) return;
    datDangGui(true);
    gui_di().then(sau).catch((e: Error) => datL(e.message)).finally(() => datDangGui(false));
  };
  return (
    <div className="dt-duyet">
      <section className="dt-khoi">
        <Khoi tieu_de="Dòng cần duyệt" dang_tai={q.isLoading} loi={q.error ? (q.error as Error).message : null}>
          {ben && <p className="dt-ben"><button type="button" className="chip" aria-label={`Bỏ lọc đối thủ ${tenBen}`} onClick={boBen}>
            Đối thủ: {tenBen} ✕</button></p>}
          {cacThangCho(q.data?.dong ?? []).map(t => (
            <ThuMucThang key={t} thang={t} xong={() => qc.invalidateQueries({ queryKey: ["doi-thu"] })}
              hien={lienKetAnToan(q.data?.dong.find(d => thangCua(d.thang_lo) === t && d.lien_ket_thu_muc)?.lien_ket_thu_muc)} />))}
          <div className="dt-loc" role="group" aria-label="Lọc">
            {LOC.map(([m, n]) => <button key={m} type="button" className="chip" aria-pressed={loc === m} onClick={() => datLoc(m)}>{n}</button>)}
          </div>
          <p><button type="button" className="chip" aria-expanded={moThem} onClick={() => { datMoThem(!moThem); datLoiThem(null); }}>
            Thêm hàng AI bỏ sót</button></p>
          {moThem && (
            <fieldset className="dt-them" aria-label="Thêm hàng AI bỏ sót">
              <legend>Thêm hàng AI bỏ sót</legend>
              <label>Đối thủ<select value={moi.ma_doi_thu} onChange={e => datMoi({ ...moi, ma_doi_thu: e.target.value })}>
                <option value="">— chọn bên —</option>
                {tq.data?.ben.map(b => <option key={b.ma} value={b.ma}>{b.ten}</option>)}</select></label>
              {NHAN_HANG_MOI.map(([k, n]) => (
                <label key={k}>{n}<input value={moi[k]} onChange={e => datMoi({ ...moi, [k]: e.target.value })} /></label>))}
              {(["thue", "gom_ship", "trang_thai"] as const).map(k => (
                <label key={k}>{{ thue: "Thuế", gom_ship: "Ship", trang_thai: "Trạng thái" }[k]}
                  <select value={moi[k]} onChange={e => datMoi({ ...moi, [k]: e.target.value })}>
                    {CHON[k]!.map(([m, t]) => <option key={m} value={m}>{t}</option>)}</select></label>))}
              <label>Link bằng chứng (hàng thêm)<input type="url" placeholder="Link bằng chứng (tuỳ chọn) — ảnh trên Drive"
                value={moi.lien_ket_bang_chung} onChange={e => datMoi({ ...moi, lien_ket_bang_chung: e.target.value })} /></label>
              <label>Loại nguồn<select value={moi.loai_nguon} onChange={e => datMoi({ ...moi, loai_nguon: e.target.value })}>
                <option value="">— loại nguồn (bắt buộc) —</option>
                {LOAI_NGUON.map(([m, n]) => <option key={m} value={m}>{n}</option>)}</select></label>
              {loiThem && <p role="alert" className="dt-loi">{loiThem}</p>}
              <div className="dt-nut">
                <button type="button" className="chip"
                  disabled={dang_gui || !moi.ma_doi_thu || !moi.ten_goc.trim() || !moi.loai_nguon || (moi.trang_thai !== "het" && !moi.gia_goc.trim())}
                  title="Cần: đối thủ, tên hàng, loại nguồn và giá (trừ khi hàng đã hết)"
                  onClick={() => lam(() => gui("/api/doi-thu/gia-moi", moi), () => { datMoThem(false); datMoi(HANG_MOI_TRONG); datLoiThem(null); qc.invalidateQueries({ queryKey: ["doi-thu"] }); }, datLoiThem)}>
                  Thêm hàng</button>
                <button type="button" className="chip" onClick={() => { datMoThem(false); datLoiThem(null); }}>Đóng</button>
              </div>
            </fieldset>)}
          <ul className="dt-ds dt-chon">{q.data?.dong.map(x => (
            <li key={x.nguon + x.id}><button type="button" aria-pressed={chon?.id === x.id && chon.nguon === x.nguon}
              onClick={() => { datChon(x); datSua({}); datNguon(NGUON_TRONG); datLoi(null); datMaKome(x.ma_kome ?? "");
                datNhomId(x.nhom_khoa?.startsWith("n:") ? x.nhom_khoa.slice(2) : ""); }}>
              <b>{x.ma_doi_thu}</b> · {x.ten_goc} · {x.gia_goc != null ? yen(x.gia_goc) : "—"}/{x.don_vi_gia ?? "?"} ·{" "}
              {NHAN_DUYET[x.trang_thai_duyet]}{x.bat_thuong ? " · bất thường" : ""}</button></li>))}</ul>
        </Khoi>
      </section>
      {chon && chon.nguon === "nap" && (
        <section className="dt-khoi dt-sua">
          <Khoi tieu_de={chon.ten_goc} canh_bao={loi}>
            <p className="dt-nhat">Nguồn: {chon.nguon_file} · {chon.vi_tri} · {ngay(chon.ngay_nguon)}{chon.ghi_chu ? ` · ${chon.ghi_chu}` : ""} <NguonDong q={chon} /></p>
            {TRUONG.map(([k, n]) => {
              const goc = String(chon[k] ?? ""), gt = sua[k] ?? goc, ds = CHON[k];
              const doi = (v: string) => { const { [k]: _bo, ...con } = sua; datSua(v === goc ? con : { ...con, [k]: v }); };
              return ds ? (
                <label key={k}>{n}<select value={gt} onChange={e => doi(e.target.value)}>
                  {!ds.some(([m]) => m === goc) && <option value={goc}>{goc || "— chưa có —"}</option>}
                  {ds.map(([m, t]) => <option key={m} value={m}>{t}</option>)}</select></label>
              ) : (
                <label key={k}>{n}<input value={gt} onChange={e => datSua({ ...sua, [k]: e.target.value })} /></label>);
            })}
            <div className="dt-nut">
              <button type="button" className="chip" disabled={dang_gui} onClick={() => lam(() => gui("/api/doi-thu/xac-nhan", { fact_id: chon.id }))}>Đúng rồi</button>
              <button type="button" className="chip" disabled={dang_gui || !Object.keys(sua).length}
                onClick={() => lam(() => gui("/api/doi-thu/sua", { fact_id: chon.id, thay_doi: sua }))}>Lưu sửa (AI đọc sai)</button>
            </div>
            <fieldset><legend>Giá đã đổi (nguồn mới)</legend>
              <select value={nguon.loai_nguon} onChange={e => datNguon({ ...nguon, loai_nguon: e.target.value })} aria-label="Loại nguồn">
                <option value="">— loại nguồn (bắt buộc) —</option>
                {LOAI_NGUON.map(([m, n]) => <option key={m} value={m}>{n}</option>)}</select>
              <input placeholder="Ghi chú nguồn (Zalo 29/9, hoá đơn khách …)" aria-label="Ghi chú nguồn" value={nguon.ghi_chu_nguon}
                onChange={e => datNguon({ ...nguon, ghi_chu_nguon: e.target.value })} />
              <input type="url" aria-label="Link bằng chứng (giá đã đổi)" placeholder="Link bằng chứng (tuỳ chọn) — ảnh trên Drive" value={nguon.lien_ket_bang_chung}
                onChange={e => datNguon({ ...nguon, lien_ket_bang_chung: e.target.value })} />
              <button type="button" className="chip" disabled={dang_gui || !nguon.loai_nguon || !sua.gia_goc}
                onClick={() => lam(() => gui("/api/doi-thu/gia-moi", { fact_goc_id: chon.id, ...sua, ...nguon }))}>Lưu giá mới</button>
            </fieldset>
            <fieldset><legend>Ghép với KOME</legend>
              <input placeholder="Mã KOME (trống = không ghép)" aria-label="Mã KOME" value={maKome} onChange={e => datMaKome(e.target.value)} />
              <select aria-label="Nhóm so sánh" value={nhomChon} onChange={e => datNhomId(e.target.value)}>
                <option value="">— theo mã KOME —</option>
                {nhomCoTen.map(g => <option key={g.id} value={String(g.id)}>{g.ten}</option>)}</select>
              {(["cung_hang", "thay_the", "khong"] as const).map(n => (
                <button key={n} type="button" className="chip"
                  disabled={dang_gui || (n !== "khong" && !maKome.trim())}
                  title={n !== "khong" && !maKome.trim() ? "Nhập mã KOME trước" : undefined} onClick={() => {
                  const ma = maKome.trim();
                  lam(() => gui("/api/doi-thu/ghep", { ma_doi_thu: chon.ma_doi_thu, ma_hang_dt: chon.ma_hang_dt,
                    product_code: n === "khong" ? null : ma || null,
                    nhom_id: n === "khong" || !nhomChon ? null : Number(nhomChon), nhan: n }));
                }}>{n === "cung_hang" ? "Cùng hàng" : n === "thay_the" ? "Thay thế" : "Không ghép"}</button>))}
            </fieldset>
          </Khoi>
        </section>)}
    </div>
  );
}
