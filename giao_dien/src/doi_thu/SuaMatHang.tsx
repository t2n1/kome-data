// Pop-up sửa MỘT mặt hàng đối thủ (đặc tả §4.7, bản phác đã duyệt popup-sua.html): ghép · tình trạng & khuyến mãi ·
// quy cách · giá như bảng in (+ bậc, "vì sao đổi giá") · lịch sử sửa. MỘT nút Lưu → POST /api/doi-thu/sua-mat-hang
// (một giao dịch ở máy chủ). Thân POST dựng ở sua_logic.ts (chỉ trường đã đổi); 409 → khung Ghi đè / Giữ bản kia.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { gui, lay } from "../api";
import { ngay, so_luong } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import { HopThoai } from "./HopThoai";
import { DON_VI, LOAI_NGUON, NHAN_GHEP, NHAN_TRANG_THAI, type Bac, type LichSu, type QuanSat } from "./kieu";
import { NguonDong } from "./NguonDong";
import { KhungXungDot, NutLuu, useGhi } from "./SuaNho";
import { doiGi, formTu, kgThung, kiemForm, lucNgan, payload, type BacNhap, type FormMatHang } from "./sua_logic";

type MatHang = { quan_sat: QuanSat & { hien_hanh?: boolean }; lich_su: LichSu[] };

const hoa = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const NHAN: [FormMatHang["nhan"], string][] = [["cung_hang", hoa(NHAN_GHEP.cung_hang)], ["thay_the", hoa(NHAN_GHEP.thay_the)],
  ["khong", "Không liên quan — bỏ khỏi nhóm"]];
const THUE: [string, string][] = [["co", "Đã gồm thuế"], ["chua", "Chưa thuế"], ["khong_ro", "Không rõ"]];
const DV_SL: [Bac["don_vi_sl"], string][] = [["thung", "thùng"], ["kg", "kg"], ["goi", "gói"], ["pallet", "pallet"]];
const DV_GIA_BAC: [Bac["don_vi_gia"], string][] = [["thung", "thùng"], ["kg", "kg"], ["goi", "gói"]];
const NHAN_LOAI_NK: Record<string, string> = { xac_nhan: "xác nhận đúng", gia_moi: "giá mới", ghep: "ghép", sua: "sửa" };
const BAC_TOI_DA = 10;   // = kome.doi_thu.BAC_TOI_DA
const BAC_TRONG: BacNhap = { tu: "", don_vi_sl: "thung", gia: "", don_vi_gia: "thung" };

export function SuaMatHang({ nguon, id, tru_o, dong, xong }: {
  nguon: "nap" | "tay"; id: number; tru_o?: string; dong: () => void; xong: () => void;
}) {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({
    queryKey: ["doi-thu", "mat-hang", nguon, id, kx], staleTime: 0, refetchOnWindowFocus: false,
    queryFn: () => lay<MatHang>(`/api/doi-thu/mat-hang/${nguon}/${id}${kx ? "?" + kx : ""}`),
  });
  const qs = q.data?.quan_sat;
  return (
    <HopThoai tieu_de={qs ? `Sửa: ${qs.ten_doi_thu ?? qs.ma_doi_thu} · ${qs.ten_goc}` : "Sửa mặt hàng"} dong={dong} rong={680}>
      {q.isPending ? <div className="dt-giu-cho" aria-busy="true"><span /><span /><span /></div>
        : q.isError ? <p role="alert" className="dt-loi">{q.error.message}</p>
        : <FormSua key={`${q.data.quan_sat.nguon}:${q.data.quan_sat.id}`} d={q.data} tru_o={tru_o} dong={dong} xong={xong} />}
    </HopThoai>
  );
}

function Vien({ name, value, chon, dat, nhan, tat, tieu, focus, roi }: {
  name: string; value: string; chon: string; dat: (v: string) => void; nhan: ReactNode; tat?: boolean; tieu?: string;
  focus?: boolean; roi?: () => void;
}) {
  return (
    <label className={"dt-vien" + (tat ? " tat" : "") + (focus ? " dt-tro" : "")} title={tieu}>
      <input type="radio" name={name} value={value} checked={chon === value} disabled={tat} onChange={() => dat(value)}
        {...(focus ? { "data-focus": "", onBlur: roi } : {})} />{nhan}</label>
  );
}

function FormSua({ d, tru_o, dong, xong }: { d: MatHang; tru_o?: string; dong: () => void; xong: () => void }) {
  // Chụp quan sát lúc MỞ: `sua_cuoi` gửi lên là của lần đọc này (truy vấn chạy lại cũng không nới chống sửa đè).
  const [q] = useState(d.quan_sat);
  const [f, datF] = useState<FormMatHang>(() => formTu(q));
  const [tro, datTro] = useState(tru_o ?? null);
  const g = useGhi(xong, dong);
  const goc = useRef<HTMLDivElement>(null);
  const ma = useId();
  const dat = <K extends keyof FormMatHang>(k: K, v: FormMatHang[K]) => datF(x => ({ ...x, [k]: v }));
  const p = payload(q, f, false);
  const kg = kgThung(f.so_goi_thung, f.kl_goi_g);
  const keKhongBo = q.loai_nguon === "khach_ke" && q.nhom_khoa != null;

  // Nội dung về SAU lúc HopThoai dựng (đang tải) → tự đưa con trỏ vào ô `tru_o` (hoặc ô đầu tiên của form).
  useEffect(() => {
    const el = goc.current?.querySelector<HTMLElement>("[data-focus]")
      ?? goc.current?.querySelector<HTMLElement>("input:not([disabled]),select,textarea,button");
    el?.focus();
  }, []);
  // Ô `tru_o`: mang `data-focus` + viền cam (`dt-tro`) tới khi rời ô. `lop` ghép lớp gốc của ô với viền cam.
  const o = (k: string) => (tro === k ? { "data-focus": "", onBlur: () => datTro(null) } : {});
  const lop = (goc_lop: string, k: string) => (goc_lop + (tro === k ? " dt-tro" : "")).trim() || undefined;
  const datBac = (i: number, b: Partial<BacNhap>) => dat("bac", f.bac.map((x, j) => (j === i ? { ...x, ...b } : x)));

  const luu = () => {
    const loi = kiemForm(q, f);
    if (loi) return g.datLoi(loi);
    g.chay(ghi_de => gui("/api/doi-thu/sua-mat-hang", payload(q, f, ghi_de).body));
  };
  const nhom = q.ten_nhom ?? q.ma_kome ?? "hàng KOME";
  const donVi = Object.entries(DON_VI).filter(([m]) => m === "goi" || m === "thung" || m === "kg" || m === f.don_vi_gia);
  const loaiNguon = q.nguon === "nap" ? "bảng giá" : (LOAI_NGUON.find(([m]) => m === q.loai_nguon)?.[1] ?? q.loai_nguon).toLowerCase();

  return (
    <div ref={goc} className="dt-sua-mh">
      <p className="dt-nhat dt-dau-phu">
        {q.quy_cach_goc || "quy cách ?"} · nguồn {loaiNguon} {ngay(q.ngay_nguon)}{q.kenh_gia && <> · {q.kenh_gia}</>}
        {d.quan_sat.hien_hanh === false && <> · <b>bản cũ</b></>} <NguonDong q={q} />
      </p>

      <fieldset><legend>So với {nhom} là</legend>
        <div className="dt-hang">
          {NHAN.map(([m, n], i) => <Vien key={m} name={`${ma}-nhan`} value={m} chon={f.nhan} dat={v => dat("nhan", v as FormMatHang["nhan"])}
            nhan={n} focus={tro === "nhan" && (f.nhan === m || (i === 0 && !NHAN.some(([x]) => x === f.nhan)))}
            roi={() => datTro(null)} tat={m === "khong" && keKhongBo} tieu={m === "khong" && keKhongBo ? "Giá khách kể không bỏ ghép được ở đây." : undefined} />)}
        </div>
        {q.ma_kome == null && q.nhan == null && <p className="dt-goi-y">Mặt hàng này chưa ghép mã KOME nào — ghép ở màn Dữ liệu › Duyệt.</p>}
      </fieldset>

      <fieldset><legend>Tình trạng & khuyến mãi</legend>
        <div className="dt-hang">
          {["con", "het", "sap_ve", ...(q.trang_thai === "khong_ro" ? ["khong_ro"] : [])].map(m =>
            <Vien key={m} name={`${ma}-tt`} value={m} chon={f.trang_thai} dat={v => dat("trang_thai", v)}
              nhan={NHAN_TRANG_THAI[m] ?? m} focus={tro === "trang_thai" && f.trang_thai === m} roi={() => datTro(null)} />)}
        </div>
        <label className="dt-hang">Khuyến mãi
          <input type="text" className={lop("dt-rong-o", "khuyen_mai")} placeholder="để trống = không có"
            value={f.khuyen_mai} onChange={e => dat("khuyen_mai", e.target.value)} {...o("khuyen_mai")} /></label>
      </fieldset>

      <fieldset><legend>Quy cách</legend>
        <div className="dt-hang">
          <label>Gói / thùng <input type="text" inputMode="numeric" className={lop("dt-so", "so_goi_thung")} placeholder="?" value={f.so_goi_thung}
            onChange={e => dat("so_goi_thung", e.target.value)} {...o("so_goi_thung")} /></label>
          <label>Tịnh 1 gói <input type="text" inputMode="decimal" className={lop("dt-so", "kl_goi_g")} placeholder="?" value={f.kl_goi_g}
            onChange={e => dat("kl_goi_g", e.target.value)} {...o("kl_goi_g")} /> g</label>
          <span className="dt-nhat">→ 1 thùng = {kg == null ? <span className="dt-hoi">?</span> : so_luong(kg, 3)} kg</span>
        </div>
      </fieldset>

      <fieldset><legend>Giá (như bảng in)</legend>
        <div className="dt-hang">
          <label>Giá gốc <input type="text" inputMode="decimal" className={lop("dt-so", "gia_goc")} placeholder="?" value={f.gia_goc}
            onChange={e => dat("gia_goc", e.target.value)} {...o("gia_goc")} /> ¥ /</label>
          <select aria-label="Đơn vị giá" className={lop("", "don_vi_gia")} value={f.don_vi_gia} onChange={e => dat("don_vi_gia", e.target.value)} {...o("don_vi_gia")}>
            {!f.don_vi_gia && <option value="">?</option>}
            {donVi.map(([m, n]) => <option key={m} value={m}>{n}</option>)}
            {f.don_vi_gia && !(f.don_vi_gia in DON_VI) && <option value={f.don_vi_gia}>{f.don_vi_gia}</option>}
          </select>
        </div>
        <div className="dt-hang">
          {THUE.map(([m, n]) => <Vien key={m} name={`${ma}-thue`} value={m} chon={f.thue} dat={v => dat("thue", v)} nhan={n}
            focus={tro === "thue" && (f.thue === m || (!f.thue && m === "co"))} roi={() => datTro(null)} />)}
        </div>
        <table className="dt-bac">
          <tbody>
            {f.bac.map((b, i) => <tr key={i}>
              <td>từ <input type="text" inputMode="decimal" className={i === 0 ? lop("dt-so-nho", "bac") : "dt-so-nho"} aria-label={`Bậc ${i + 1}: từ bao nhiêu`} value={b.tu}
                onChange={e => datBac(i, { tu: e.target.value })} {...(i === 0 ? o("bac") : {})} />{" "}
                <select aria-label={`Bậc ${i + 1}: đơn vị số lượng`} value={b.don_vi_sl}
                  onChange={e => datBac(i, { don_vi_sl: e.target.value as Bac["don_vi_sl"] })}>
                  {DV_SL.map(([m, n]) => <option key={m} value={m}>{n}</option>)}</select></td>
              <td>→ <input type="text" inputMode="decimal" className="dt-so" aria-label={`Bậc ${i + 1}: giá`} value={b.gia}
                onChange={e => datBac(i, { gia: e.target.value })} /> ¥ /{" "}
                <select aria-label={`Bậc ${i + 1}: đơn vị giá`} value={b.don_vi_gia}
                  onChange={e => datBac(i, { don_vi_gia: e.target.value as Bac["don_vi_gia"] })}>
                  {DV_GIA_BAC.map(([m, n]) => <option key={m} value={m}>{n}</option>)}</select></td>
              <td><button type="button" className="nut-dong" aria-label={`Bỏ bậc ${i + 1}`}
                onClick={() => dat("bac", f.bac.filter((_, j) => j !== i))}>✕</button></td>
            </tr>)}
          </tbody>
        </table>
        {f.bac.length < BAC_TOI_DA && <button type="button" className={f.bac.length === 0 ? lop("lien-ket dt-them-bac", "bac") : "lien-ket dt-them-bac"}
          {...(f.bac.length === 0 ? o("bac") : {})}
          onClick={() => dat("bac", [...f.bac, f.bac.length ? { ...f.bac[f.bac.length - 1], tu: "", gia: "" } : BAC_TRONG])}>
          + thêm bậc mua nhiều rẻ hơn</button>}
        {p.doi_gia && <div className="dt-doi-gia">
          <div className="dt-hang">Vì sao đổi giá?
            <Vien name={`${ma}-vs`} value="doc_sai" chon={f.vi_sao_gia} dat={v => dat("vi_sao_gia", v as FormMatHang["vi_sao_gia"])}
              nhan="Máy đọc sai bảng giá" />
            <Vien name={`${ma}-vs`} value="da_doi" chon={f.vi_sao_gia} dat={v => dat("vi_sao_gia", v as FormMatHang["vi_sao_gia"])}
              nhan="Giá đã đổi (có nguồn mới)" />
          </div>
          {f.vi_sao_gia === "da_doi" && <div className="dt-hang">
            <label>Nguồn <select value={f.loai_nguon} onChange={e => dat("loai_nguon", e.target.value)}>
              <option value="">— chọn —</option>
              {LOAI_NGUON.map(([m, n]) => <option key={m} value={m}>{n}</option>)}</select></label>
            <label>Link bằng chứng <input type="url" className="dt-rong-o" placeholder="https://drive.google.com/… (tuỳ chọn)"
              value={f.lien_ket_bang_chung} onChange={e => dat("lien_ket_bang_chung", e.target.value)} /></label>
          </div>}
        </div>}
      </fieldset>

      <details className="dt-lich-su">
        <summary>Lịch sử sửa ({d.lich_su.length})</summary>
        <ul>
          {d.lich_su.map(l => <li key={l.id}>
            <b>{l.ai ?? "Ai đó"}</b> · {lucNgan(l.luc)} · {doiGi(l.sau) || NHAN_LOAI_NK[l.loai] || l.loai}</li>)}
          {q.nguon === "nap" && <li className="dt-nhat">Claude đọc từ bảng giá · {ngay(q.ngay_nguon)}</li>}
        </ul>
      </details>

      {g.xung && <KhungXungDot x={g.xung} dang={g.dang} ghiDe={g.ghiDe} giu={g.giu} />}
      <NutLuu luu={luu} dong={dong} tat={p.rong} dang={g.dang} loi={g.loi} chu="Bản gốc máy đọc vẫn giữ; lần sửa ghi vào Nhật ký" />
    </div>
  );
}
