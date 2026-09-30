// Logic thuần của bảng sửa mặt hàng đối thủ (Dữ liệu › Duyệt / sửa — đặc tả 2026-09-30-doi-thu-bang-sua-design.md):
// cột, chữ hiện trong ô, thân POST của MỘT ô, di chuyển bằng bàn phím, ghép dòng sau khi lưu, tìm. Thân POST đi qua
// CHÍNH sua_logic.ts::formTu + payload + kiemForm (một đường dựng thân với pop-up SuaMatHang — không viết lại luật).
import { so_luong, yen } from "../dinh_dang";
import { DON_VI, NHAN_MUC, nhanDonVi, type QuanSat } from "./kieu";
import { boDau } from "./loc";
import { formTu, kiemForm, payload, TRUONG_GIA, type FormMatHang } from "./sua_logic";

/** Trường của FormMatHang mà một ô sửa được. */
export type TruongO = "ten_goc" | "quy_cach_goc" | "so_goi_thung" | "kl_goi_g" | "gia_goc" | "don_vi_gia"
  | "kg_moi_don_vi_gia" | "thue"
  | "trang_thai" | "ma_kome" | "nhan";
export type MaCot = TruongO | "ben" | "muc" | "yen_kg";
/** `kieu` null = chỉ đọc. "so" = ô số, "chon" = ô chọn, "ma" = ô chữ có gợi ý mã KOME. */
export type Cot = { ma: MaCot; nhan: string; kieu: "chu" | "so" | "chon" | "ma" | null; chon?: [string, string][] };

export const THUE: [string, string][] = [["chua", "Chưa thuế"], ["co", "Đã gồm thuế"], ["khong_ro", "Không rõ"]];
export const TRANG_THAI: [string, string][] = [["con", "Còn"], ["het", "Hết"], ["sap_ve", "Sắp về"], ["khong_ro", "Không rõ"]];
export const NHAN_O: [FormMatHang["nhan"], string][] = [["cung_hang", "cùng thương hiệu"], ["thay_the", "khác thương hiệu"],
  ["khong", "không ghép"]];

export const COT: Cot[] = [
  { ma: "ten_goc", nhan: "Tên hàng", kieu: "chu" },       // cột đầu — dính trái khi bảng cuộn ngang
  { ma: "ben", nhan: "Bên", kieu: null },
  { ma: "muc", nhan: "Mức giá", kieu: null },   // 070: chỉ đọc — mỗi mức giá là một dòng của mặt hàng
  { ma: "quy_cach_goc", nhan: "Quy cách", kieu: "chu" },
  { ma: "so_goi_thung", nhan: "Gói/thùng", kieu: "so" },
  { ma: "kl_goi_g", nhan: "Tịnh 1 gói (g)", kieu: "so" },
  { ma: "gia_goc", nhan: "Giá", kieu: "so" },
  { ma: "don_vi_gia", nhan: "Đơn vị", kieu: "chon", chon: Object.entries(DON_VI) },
  // Số kg của MỘT đơn vị giá — cột DUY NHẤT mart (060/067) dùng để quy giá ra ¥/kg (tịnh 1 gói KHÔNG được dùng).
  { ma: "kg_moi_don_vi_gia", nhan: "kg / đơn vị", kieu: "so" },
  { ma: "thue", nhan: "Thuế", kieu: "chon", chon: THUE },
  { ma: "trang_thai", nhan: "Tình trạng", kieu: "chon", chon: TRANG_THAI },
  { ma: "ma_kome", nhan: "Mã KOME", kieu: "ma" },
  { ma: "nhan", nhan: "Thương hiệu", kieu: "chon", chon: NHAN_O },
  { ma: "yen_kg", nhan: "¥/kg", kieu: null },
];

/** Cột đang hiện: "Bên" chỉ khi xem mọi bên. */
export const cotHien = (moiBen: boolean) => COT.filter(c => c.ma !== "ben" || moiBen);

/** Mức giá của dòng: nhãn `muc_gia` · nhãn `kenh_gia` (có cái nào hiện cái đó); không có → "Thường"; mã lạ nguyên văn. */
export function nhanMuc(q: Pick<QuanSat, "muc_gia" | "kenh_gia">): string {
  const r = [q.muc_gia, q.kenh_gia].filter((m): m is string => !!m).map(m => NHAN_MUC[m] ?? m);
  return r.length ? r.join(" · ") : "Thường";
}

/** Nhóm dòng bảng sửa theo MẶT HÀNG (bên + mat_hang_khoa), giữ thứ tự lần gặp đầu. `dau` = dòng đại diện (hoặc dòng đầu khi
 *  không có cờ), `con` = các mức giá khác theo thứ tự đến. */
export function nhomBang<T extends QuanSat>(ds: T[]): { dau: T; con: T[] }[] {
  const theoBen = new Map<string, Map<string, T[]>>();   // lồng hai tầng — không ghép chuỗi khoá nên không thể trùng
  const nhom: T[][] = [];
  for (const q of ds) {
    let m = theoBen.get(q.ma_doi_thu);
    if (!m) theoBen.set(q.ma_doi_thu, m = new Map());
    let g = m.get(q.mat_hang_khoa);
    if (!g) { m.set(q.mat_hang_khoa, g = []); nhom.push(g); }
    g.push(q);
  }
  return nhom.map(g => {
    const dau = g.find(q => q.dai_dien) ?? g[0];
    return { dau, con: g.filter(q => q !== dau) };
  });
}

const laKhachKe = (q: QuanSat) => q.loai_nguon === "khach_ke";
/** Giá khách kể đã mang nhóm (thẻ @hàng): máy chủ không ghép lại ở đây (doi_thu.sua_mat_hang). */
const keDaNhom = (q: QuanSat) => laKhachKe(q) && q.nhom_khoa != null;

/** Ô này sửa được trên dòng này? Dòng đã bị thay (B14) thì không ô nào. */
export function suaDuoc(q: QuanSat, c: Cot): boolean {
  if (c.kieu == null || q.thay_boi) return false;
  if ((c.ma === "ma_kome" || c.ma === "nhan") && keDaNhom(q)) return false;
  return true;
}

const nhanCua = (ds: [string, string][], m: string | null | undefined) => (m == null ? "" : ds.find(x => x[0] === m)?.[1] ?? m);

/** Chữ hiện trong ô + `hoi` (ô còn thiếu → "?" cam). Chưa ghép là "—" (hợp lệ: không có hàng KOME tương ứng), không "?". */
export function hienThi(q: QuanSat, c: Cot): { chu: string; hoi: boolean } {
  const f = formTu(q);
  const thieuQc = (v: number | null) => ({ chu: v == null ? "" : so_luong(v, 1), hoi: v == null && !laKhachKe(q) });
  switch (c.ma) {
    case "ben": return { chu: q.ten_doi_thu ?? q.ma_doi_thu, hoi: false };
    case "muc": return { chu: nhanMuc(q), hoi: false };
    case "ten_goc": return { chu: q.ten_goc, hoi: !q.ten_goc };
    case "quy_cach_goc": return { chu: q.quy_cach_goc ?? "", hoi: false };
    case "so_goi_thung": return thieuQc(q.so_goi_thung);
    case "kl_goi_g": return thieuQc(q.kl_goi_g);
    case "gia_goc": return { chu: q.gia_goc == null ? "" : yen(q.gia_goc), hoi: q.gia_goc == null && q.trang_thai !== "het" };
    case "don_vi_gia": return { chu: q.don_vi_gia ? nhanDonVi(q.don_vi_gia) : "", hoi: !q.don_vi_gia };
    case "kg_moi_don_vi_gia":
      return { chu: q.kg_moi_don_vi_gia == null ? "" : so_luong(q.kg_moi_don_vi_gia, 3), hoi: q.kg_moi_don_vi_gia == null && !laKhachKe(q) };
    case "thue": return { chu: nhanCua(THUE, q.thue), hoi: false };
    case "trang_thai": return { chu: nhanCua(TRANG_THAI, q.trang_thai), hoi: false };
    case "ma_kome": return { chu: f.ma_kome || "—", hoi: false };
    case "nhan": return { chu: f.ma_kome ? nhanCua(NHAN_O, f.nhan) : "—", hoi: false };
    case "yen_kg":
      if (q.don_vi_so !== "kg") return { chu: "chưa quy", hoi: true };
      return { chu: q.yen_chuan == null ? "" : yen(q.yen_chuan), hoi: q.yen_chuan == null };
  }
}

/** Giá trị điền sẵn khi mở ô sửa (= ô tương ứng của form pop-up lúc mở). */
export const giaTriSua = (q: QuanSat, ma: TruongO): string => formTu(q)[ma];

export type KetQuaO = { body: object } | { loi: string } | { can_nhan: true } | null;

/** Thân POST /sua-mat-hang của MỘT ô. null = không đổi gì (không gửi). `can_nhan` = mã KOME mới trên dòng "không ghép":
 *  phải chọn cùng / khác thương hiệu trước (máy chủ bắt buộc). Trường giá (TRUONG_GIA) = "Máy đọc sai"; "Giá đã đổi"
 *  cần loại nguồn nên chỉ qua pop-up. Xoá mã KOME = bỏ ghép (nhãn "không ghép"). */
export function thanO(q: QuanSat, ma: TruongO, gt: string,
  o: { ghi_de?: boolean; nhan?: FormMatHang["nhan"] } = {}): KetQuaO {
  const goc = formTu(q);
  const f: FormMatHang = { ...goc, [ma]: gt };
  if (o.nhan) f.nhan = o.nhan;
  if (ma === "ma_kome") {
    const moi = gt.trim();
    if (!moi) f.nhan = "khong";
    else if (moi !== goc.ma_kome.trim() && f.nhan === "khong") return { can_nhan: true };
  }
  if ((TRUONG_GIA as readonly string[]).includes(ma)) f.vi_sao_gia = "doc_sai";
  const p = payload(q, f, !!o.ghi_de);
  if (p.rong) return null;
  const loi = kiemForm(q, f);
  return loi ? { loi } : { body: p.body };
}

export type ViTri = { d: number; c: number };
export type Huong = "len" | "xuong" | "trai" | "phai" | "tab" | "tab_lui";

/** Ô kế tiếp. Mũi tên: mọi cột, dừng ở biên. Tab / Shift+Tab: ô SỬA ĐƯỢC kế tiếp / trước (theo cột), hết dòng sang
 *  dòng dưới / trên. null = ra ngoài bảng. */
export function oKeTiep(p: ViTri, h: Huong, soDong: number, cots: Cot[]): ViTri | null {
  const trong = (v: ViTri) => (v.d >= 0 && v.d < soDong && v.c >= 0 && v.c < cots.length ? v : null);
  if (h === "len") return trong({ d: p.d - 1, c: p.c });
  if (h === "xuong") return trong({ d: p.d + 1, c: p.c });
  if (h === "trai") return trong({ d: p.d, c: p.c - 1 });
  if (h === "phai") return trong({ d: p.d, c: p.c + 1 });
  const buoc = h === "tab" ? 1 : -1;
  let { d, c } = p;
  for (let i = 0; i < soDong * cots.length; i++) {
    c += buoc;
    if (c >= cots.length) { c = 0; d++; }
    if (c < 0) { c = cots.length - 1; d--; }
    if (d < 0 || d >= soDong) return null;
    if (cots[c].kieu != null) return { d, c };
  }
  return null;
}

/** Thay dòng `cu` bằng bản vừa đọc lại từ /mat-hang (có thể mang id mới — dòng tay "đọc sai" thành dòng tay mới).
 *  Giữ các cột /mat-hang không trả (vd `moc_bat_thuong`). Không tìm thấy → giữ nguyên. */
export function ghepDong(ds: QuanSat[], cu: { nguon: string; id: number }, moi: QuanSat): QuanSat[] {
  const i = ds.findIndex(x => x.nguon === cu.nguon && x.id === cu.id);
  if (i < 0) return ds;
  const r = ds.slice();
  r[i] = { ...ds[i], ...moi };
  return r;
}

/** Lọc ở trình duyệt: bỏ dấu, trên tên hàng · quy cách · mã KOME · bên. */
export function timDong(ds: QuanSat[], tim: string): QuanSat[] {
  const t = boDau(tim.trim());
  if (!t) return ds;
  return ds.filter(q => boDau(`${q.ten_goc} ${q.quy_cach_goc ?? ""} ${q.ma_kome ?? ""} ${q.ma_doi_thu} ${q.ten_doi_thu ?? ""}`).includes(t));
}

/** Khoá NHÓM (mặt hàng) của một dòng — khoá của state mở / đóng. JSON hai phần tử: không ghép chuỗi nên không thể trùng. */
export const khoaNhomBang = (q: Pick<QuanSat, "ma_doi_thu" | "mat_hang_khoa">) => JSON.stringify([q.ma_doi_thu, q.mat_hang_khoa]);

/** Một dòng ĐANG HIỆN của bảng sửa: đầu nhóm (`soCon` = số mức giá khác, `mo` = đang mở, `ep` = mở vì dòng con đang lỗi /
 *  409 — đóng không được) hoặc dòng con (`soCon` null). */
export type DongHien<T extends QuanSat = QuanSat> = { q: T; kn: string; soCon: number | null; mo: boolean; ep: boolean };

/** Danh sách dòng đang hiện: mỗi nhóm dòng đầu, rồi các dòng con ngay dưới khi nhóm mở (`mo` có khoá nhóm) HOẶC khi
 *  `tuMo(con)` đúng với một dòng con (ô lỗi / 409 ở dòng con — không để lỗi nằm trong nhóm đang đóng). Chỉ số bàn phím
 *  `d` của bảng chạy trên CHÍNH danh sách này. */
export function dongHien<T extends QuanSat>(nhom: { dau: T; con: T[] }[], mo: ReadonlySet<string>,
  tuMo: (q: T) => boolean = () => false): DongHien<T>[] {
  const r: DongHien<T>[] = [];
  for (const g of nhom) {
    const kn = khoaNhomBang(g.dau);
    const ep = g.con.some(tuMo);
    const m = g.con.length > 0 && (ep || mo.has(kn));
    r.push({ q: g.dau, kn, soCon: g.con.length, mo: m, ep });
    if (m) for (const c of g.con) r.push({ q: c, kn, soCon: null, mo: true, ep });
  }
  return r;
}

/** Ô đang chọn sau khi mở (`mo` true) / đóng nhóm có dòng đầu ở `dau` và `n` dòng con: dòng dưới nhóm dời theo; ô đang
 *  nằm trong các dòng con vừa đóng về dòng đầu. */
export function chonSauMoNhom(v: ViTri | null, dau: number, n: number, mo: boolean): ViTri | null {
  if (!v || v.d <= dau || !n) return v;
  if (mo) return { d: v.d + n, c: v.c };
  return v.d <= dau + n ? { d: dau, c: v.c } : { d: v.d - n, c: v.c };
}

/** Đích của "Gộp vào…": các MẶT HÀNG khác (dòng đầu nhóm) cùng bên với `q`, lọc bằng ô tìm (cùng luật timDong). */
export function dichGop<T extends QuanSat>(ds: T[], q: Pick<QuanSat, "ma_doi_thu" | "mat_hang_khoa">, tim: string): T[] {
  const dau = nhomBang(ds.filter(x => x.ma_doi_thu === q.ma_doi_thu)).map(g => g.dau)
    .filter(x => x.mat_hang_khoa !== q.mat_hang_khoa);
  return timDong(dau, tim) as T[];
}

/** Dòng đã được gộp vào mặt hàng khác (khoá mặt hàng ≠ mã hàng của chính nó) — có nút "Tách ra". */
export const daGop = (q: Pick<QuanSat, "mat_hang_khoa" | "ma_hang_dt">) => q.mat_hang_khoa !== q.ma_hang_dt;
