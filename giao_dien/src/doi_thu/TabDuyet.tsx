import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { gui, lay } from "../api";
import type { TongQuan } from "./kieu";
import { Khoi } from "../chung/Khoi";
import { ngay, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { QuanSat } from "./kieu";
import { NHAN_DUYET } from "./kieu";

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

export function TabDuyet({ ben, boBen }: { ben: string; boBen: () => void }) {
  const kx = chuoiKhoang(useKhoang());
  const qc = useQueryClient();
  const [loc, datLoc] = useState("can_xem");
  const url = `/api/doi-thu/duyet?${new URLSearchParams({ ben, loc })}${kx ? "&" + kx : ""}`;
  const q = useQuery({ queryKey: ["doi-thu", "duyet", ben, loc, kx], queryFn: () => lay<{ dong: QuanSat[] }>(url) });
  const [chon, datChon] = useState<QuanSat | null>(null);
  const [sua, datSua] = useState<Record<string, string>>({});
  const [nguon, datNguon] = useState({ loai_nguon: "", ghi_chu_nguon: "" });
  const [maKome, datMaKome] = useState("");
  const [loi, datLoi] = useState<string | null>(null);
  const [dang_gui, datDangGui] = useState(false);
  const tq = useQuery({ queryKey: ["doi-thu", "tong-quan", kx], enabled: !!ben,
    queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const tenBen = tq.data?.ben.find(b => b.ma === ben)?.ten ?? ben;
  const xong = () => { datChon(null); datSua({}); datLoi(null); datMaKome(""); qc.invalidateQueries({ queryKey: ["doi-thu"] }); };
  // Chống bấm đúp: mọi nút ghi khoá tới khi yêu cầu xong (thành công hay lỗi).
  const lam = (gui_di: () => Promise<unknown>) => {
    if (dang_gui) return;
    datDangGui(true);
    gui_di().then(xong).catch((e: Error) => datLoi(e.message)).finally(() => datDangGui(false));
  };
  return (
    <div className="dt-duyet">
      <section className="dt-khoi">
        <Khoi tieu_de="Dòng cần duyệt" dang_tai={q.isLoading} loi={q.error ? (q.error as Error).message : null}>
          {ben && <p className="dt-ben"><button type="button" className="chip" aria-label={`Bỏ lọc đối thủ ${tenBen}`} onClick={boBen}>
            Đối thủ: {tenBen} ✕</button></p>}
          <div className="dt-loc" role="group" aria-label="Lọc">
            {LOC.map(([m, n]) => <button key={m} type="button" className="chip" aria-pressed={loc === m} onClick={() => datLoc(m)}>{n}</button>)}
          </div>
          <ul className="dt-ds dt-chon">{q.data?.dong.map(x => (
            <li key={x.nguon + x.id}><button type="button" aria-pressed={chon?.id === x.id && chon.nguon === x.nguon}
              onClick={() => { datChon(x); datSua({}); datLoi(null); datMaKome(x.ma_kome ?? ""); }}>
              <b>{x.ma_doi_thu}</b> · {x.ten_goc} · {x.gia_goc != null ? yen(x.gia_goc) : "—"}/{x.don_vi_gia ?? "?"} ·{" "}
              {NHAN_DUYET[x.trang_thai_duyet]}{x.bat_thuong ? " · bất thường" : ""}</button></li>))}</ul>
        </Khoi>
      </section>
      {chon && chon.nguon === "nap" && (
        <section className="dt-khoi dt-sua">
          <Khoi tieu_de={chon.ten_goc} canh_bao={loi}>
            <p className="dt-nhat">Nguồn: {chon.nguon_file} · {chon.vi_tri} · {ngay(chon.ngay_nguon)}{chon.ghi_chu ? ` · ${chon.ghi_chu}` : ""}</p>
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
              <button type="button" className="chip" disabled={dang_gui || !nguon.loai_nguon || !sua.gia_goc}
                onClick={() => lam(() => gui("/api/doi-thu/gia-moi", { fact_goc_id: chon.id, ...sua, ...nguon }))}>Lưu giá mới</button>
            </fieldset>
            <fieldset><legend>Ghép với KOME</legend>
              <input placeholder="Mã KOME (trống = không ghép)" aria-label="Mã KOME" value={maKome} onChange={e => datMaKome(e.target.value)} />
              {(["cung_hang", "thay_the", "khong"] as const).map(n => (
                <button key={n} type="button" className="chip"
                  disabled={dang_gui || (n !== "khong" && !maKome.trim())}
                  title={n !== "khong" && !maKome.trim() ? "Nhập mã KOME trước" : undefined} onClick={() => {
                  const ma = maKome.trim();
                  lam(() => gui("/api/doi-thu/ghep", { ma_doi_thu: chon.ma_doi_thu, ma_hang_dt: chon.ma_hang_dt,
                    product_code: n === "khong" ? null : ma || null, nhom_id: null, nhan: n }));
                }}>{n === "cung_hang" ? "Cùng hàng" : n === "thay_the" ? "Thay thế" : "Không ghép"}</button>))}
            </fieldset>
          </Khoi>
        </section>)}
    </div>
  );
}
