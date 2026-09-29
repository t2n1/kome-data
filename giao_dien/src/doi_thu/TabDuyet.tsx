// Dữ liệu › Duyệt / sửa (đặc tả giao diện mới §4.6): danh sách dòng AI đọc (lọc cần xem · bất thường · chưa ai xác nhận ·
// chưa ghép) — bấm dòng mở CÙNG pop-up SuaMatHang như tab So sánh (thay khung sửa hai cột cũ); "Đúng rồi" (xác nhận) ngay
// trên dòng; "Thêm hàng AI bỏ sót" và thư mục Drive theo tháng giữ như cũ.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { gui, lay } from "../api";
import type { TongQuan } from "./kieu";
import { Khoi } from "../chung/Khoi";
import { yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { QuanSat } from "./kieu";
import { LOAI_NGUON, NHAN_DUYET } from "./kieu";
import { Ra } from "./NguonDong";
import { cacThangCho, lienKetAnToan, nhanThang, thangCua } from "./nguon";
import { SuaMatHang } from "./SuaMatHang";
import { daSua } from "./sua_logic";

const LOC = [["", "Tất cả"], ["can_xem", "Cần xem"], ["bat_thuong", "Bất thường"], ["chua_xac_nhan", "Chưa ai xác nhận"], ["chua_ghep", "Chưa ghép"]];
// Ô chọn của form "Thêm hàng AI bỏ sót" (khớp CHECK của bảng).
const CHON: Partial<Record<keyof QuanSat, string[][]>> = {
  thue: [["chua", "Chưa thuế"], ["co", "Đã gồm thuế"], ["khong_ro", "Không rõ"]],
  gom_ship: [["co", "Đã gồm ship"], ["khong", "Chưa gồm ship"], ["khong_ro", "Không rõ"]],
  trang_thai: [["con", "Còn"], ["het", "Hết"], ["sap_ve", "Sắp về"], ["khong_ro", "Không rõ"]],
};

const HANG_MOI_TRONG = { ma_doi_thu: "", ten_goc: "", quy_cach_goc: "", gia_goc: "", don_vi_gia: "", kg_moi_don_vi_gia: "",
  thue: "khong_ro", gom_ship: "khong_ro", trang_thai: "con", loai_nguon: "", ghi_chu_nguon: "", lien_ket_bang_chung: "" };
const NHAN_HANG_MOI: [keyof typeof HANG_MOI_TRONG, string][] = [["ten_goc", "Tên hàng"], ["quy_cach_goc", "Quy cách"], ["gia_goc", "Giá"],
  ["don_vi_gia", "Đơn vị giá"], ["kg_moi_don_vi_gia", "Kg / đơn vị giá"], ["ghi_chu_nguon", "Ghi chú nguồn"]];

/** Một dòng "Thư mục Drive tháng …": link đã lưu (nút mở + đổi) hoặc ô dán link (đặc tả §11.1). */
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
  const [sua, datSua] = useState<{ nguon: "nap" | "tay"; id: number; tru_o?: string } | null>(null);
  const [loi, datLoi] = useState<string | null>(null);          // lỗi của nút "Đúng rồi" trên dòng
  const [loiThem, datLoiThem] = useState<string | null>(null);  // lỗi của form thêm hàng
  const [dang_gui, datDangGui] = useState(false);
  const [moThem, datMoThem] = useState(false);
  const [moi, datMoi] = useState(HANG_MOI_TRONG);
  const tq = useQuery({ queryKey: ["doi-thu", "tong-quan", kx],
    queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const tenBen = tq.data?.ben.find(b => b.ma === ben)?.ten ?? ben;
  const lamMoi = () => qc.invalidateQueries({ queryKey: ["doi-thu"] });
  // Chống bấm đúp: mọi nút ghi khoá tới khi yêu cầu xong (thành công hay lỗi).
  const lam = (gui_di: () => Promise<unknown>, sau: () => void, datL: (l: string | null) => void) => {
    if (dang_gui) return;
    datDangGui(true); datL(null);
    gui_di().then(sau).catch((e: Error) => datL(e.message)).finally(() => datDangGui(false));
  };
  return (
    <div className="dt-duyet dt-duyet-mot">
      <section className="dt-khoi">
        <Khoi tieu_de="Dòng cần duyệt" dang_tai={q.isLoading} loi={q.error ? (q.error as Error).message : null} canh_bao={loi}>
          {ben && <p className="dt-ben"><button type="button" className="chip" aria-label={`Bỏ lọc đối thủ ${tenBen}`} onClick={boBen}>
            Đối thủ: {tenBen} ✕</button></p>}
          {cacThangCho(q.data?.dong ?? []).map(t => (
            <ThuMucThang key={t} thang={t} xong={lamMoi}
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
                  onClick={() => lam(() => gui("/api/doi-thu/gia-moi", moi), () => { datMoThem(false); datMoi(HANG_MOI_TRONG); lamMoi(); }, datLoiThem)}>
                  Thêm hàng</button>
                <button type="button" className="chip" onClick={() => { datMoThem(false); datLoiThem(null); }}>Đóng</button>
              </div>
            </fieldset>)}
          <ul className="dt-ds dt-chon dt-duyet-ds">{q.data?.dong.map(x => (
            <li key={x.nguon + x.id}>
              {/* Chưa ghép → con trỏ vào ô Mã KOME; chưa có giá → ô giá (cùng "?" cam như mọi chỗ khác). */}
              <button type="button" aria-label={`Sửa ${x.ma_doi_thu} · ${x.ten_goc}${x.gia_goc == null ? " (chưa có giá)" : ""}${daSua(x) ? " (đã sửa)" : ""}`}
                onClick={() => datSua({ nguon: x.nguon, id: x.id,
                  tru_o: x.gia_goc == null ? "gia_goc" : x.ma_kome == null && x.nhom_khoa == null ? "ma_kome" : undefined })}>
                <b>{x.ma_doi_thu}</b> · {x.ten_goc}{daSua(x) && <span className="dt-nhat" aria-hidden="true"> ✎</span>} ·{" "}
                {x.gia_goc != null ? yen(x.gia_goc) : <span className="dt-hoi-cam" aria-hidden="true">?</span>}/{x.don_vi_gia ?? "?"} ·{" "}
                {NHAN_DUYET[x.trang_thai_duyet]}{x.bat_thuong ? " · bất thường" : ""}</button>
              {x.nguon === "nap" && x.trang_thai_duyet !== "da_xac_nhan" && (
                <button type="button" className="chip dt-dung" disabled={dang_gui} aria-label={`Đúng rồi: ${x.ma_doi_thu} · ${x.ten_goc}`}
                  onClick={() => lam(() => gui("/api/doi-thu/xac-nhan", { fact_id: x.id }), lamMoi, datLoi)}>Đúng rồi</button>)}
            </li>))}
            {q.data && !q.data.dong.length && <li className="dt-nhat">Không có dòng nào.</li>}
          </ul>
        </Khoi>
      </section>
      {sua && <SuaMatHang nguon={sua.nguon} id={sua.id} tru_o={sua.tru_o} dong={() => datSua(null)} xong={() => datSua(null)} />}
    </div>
  );
}
