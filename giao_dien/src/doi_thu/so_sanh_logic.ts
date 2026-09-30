// Logic thuần của tab "So sánh giá" (đợt 4b, đặc tả §5) — không React, có test (so_sanh_logic.test.ts).
// Giá đã là ¥/kg chưa thuế; gia_1/5/10 máy chủ đã lấy min(giá lẻ, bậc áp dụng). Khách kể KHÔNG vẽ ở đây.
import { boDau } from "./loc";
import { NGAY_CU, laBatThuong, phanTram } from "./mau";
import { tenNganh } from "./nganh";
import { so, so_luong } from "../dinh_dang";
import { TOI_DA_SP } from "./url";
import { nhanDonVi, type Bac, type Nhom, type QuanSat } from "./kieu";
import { tinh, type DieuKienGiao, type KetQuaPhi } from "./phi_giao";

export type SoLuong = "1" | "5" | "10" | "pallet";
export const NHAN_SL: Record<SoLuong, string> = { "1": "1 thùng", "5": "5 thùng", "10": "10 thùng", pallet: "1 pallet" };

/** Giá (¥/kg) của một mặt hàng khi khách mua `sl`. Pallet không ghi → giá lẻ + khongGhiPallet = true (không đoán). */
export function giaTai(q: QuanSat, sl: SoLuong): { gia: number | null; khongGhiPallet: boolean } {
  const le = q.gia_1 ?? q.yen_chuan ?? null;
  if (sl === "1") return { gia: le, khongGhiPallet: false };
  if (sl === "5") return { gia: q.gia_5 ?? le, khongGhiPallet: false };
  if (sl === "10") return { gia: q.gia_10 ?? le, khongGhiPallet: false };
  const pl = q.gia_pallet_mh ?? q.gia_pallet;   // 070: giá pallet của MẶT HÀNG (mức pallet có thể là dòng khác)
  return pl != null ? { gia: pl, khongGhiPallet: false } : { gia: le, khongGhiPallet: true };
}

/** Giá KOME để so: "chuan" → 標準価格 (thiếu thì giá thực bán); "thuc" → thực bán 90 ngày; "01".."10" → bảng 売価No (thiếu → null). */
export function giaKome(n: Nhom, gk: string): number | null {
  if (gk === "chuan") return n.gia_kome_chuan ?? n.gia_kome;
  if (gk === "thuc") return n.gia_kome;
  return n.gia_kome_bang?.[gk] ?? null;
}

export const LUA_CHON_GK: { ma: string; nhan: string }[] = [
  { ma: "chuan", nhan: "標準価格" }, { ma: "thuc", nhan: "thực bán 90 ngày" },
  { ma: "01", nhan: "売価No.01" }, { ma: "02", nhan: "売価No.02" }, { ma: "04", nhan: "売価No.04" },
  { ma: "05", nhan: "売価No.05" }, { ma: "09", nhan: "売価No.09" }, { ma: "10", nhan: "売価No.10 · khuyến mãi" },
];

/** `phiHoi` (chỉ khi bật "Tính cả phí giao"): phí KHÔNG cộng được — "kg" = thiếu kg / thùng, "dk" = thiếu điều kiện giao
 *  hàng hoặc một phần chưa rõ (`phi.chua_ro`). `phi` = kết quả phi_giao.tinh của đơn (null khi không tính).
 *  `bt` = giá bất thường (mau.ts::laBatThuong, B18): p = null (không màu), xếp sau mọi dòng thường, vẽ xám. */
export type Dong = { kome: boolean; q?: QuanSat; ben: string; ten: string; gia: number | null; giaLe: number | null;
  p: number | null; cung: boolean; soGoi: number | null; klGoi: number | null; thieu: boolean; cu: boolean;
  thueKhongRo: boolean; gomShip: boolean; het: boolean; km: boolean; khongGhiPallet: boolean;
  phiHoi: LyDoHoiPhi | null; phi: KetQuaPhi | null; bt: boolean };

// ---- "Tính cả phí giao" (đặc tả §5.5, đợt 4b task 9) ----
export type PhiDon = Pick<KetQuaPhi, "ship" | "vung" | "daibiki" | "chua_ro">;
export type LyDoHoiPhi = "kg" | "dk";
/** Điều kiện giao hàng đã nạp: theo ma_doi_thu, và dòng KOME. Không có → null (tắt "Tính cả phí giao"). */
export type PhiSoSanh = { ben: Map<string, DieuKienGiao>; kome: DieuKienGiao | null };

/** Giá (¥/kg) cộng phí của một đơn: gia + (ship + vùng + daibiki) ÷ kg của đơn. Có phần chưa rõ (hoặc kg của đơn không
 *  dương) → giữ `gia`, cờ `chuaRo` — KHÔNG cộng phần đã biết (cộng nửa vời là con số không ai trả). */
export function giaCoPhi(gia: number, kgDon: number, phi: PhiDon): { gia: number; chuaRo: boolean } {
  if (phi.chua_ro.length || !(kgDon > 0) || !Number.isFinite(kgDon)) return { gia, chuaRo: true };
  return { gia: gia + (phi.ship + phi.vung + phi.daibiki) / kgDon, chuaRo: false };
}

/** Phí của đơn `thung` thùng (Kanto, trả daibiki — đặc tả §5.5) cộng vào giá ¥/kg. `tien` = tiền hàng của đơn
 *  (mặc định giá × kg của đơn) — quyết định ngưỡng miễn ship / daibiki. Bao ship: phi_giao.tinh không cộng ship. */
export function apPhi(gia: number | null, o: { dk: DieuKienGiao | null | undefined; thung: number; kgThung: number | null; tien?: number | null }):
  { gia: number | null; hoi: LyDoHoiPhi | null; phi: KetQuaPhi | null } {
  if (gia == null) return { gia, hoi: null, phi: null };
  if (o.kgThung == null || !(o.kgThung > 0)) return { gia, hoi: "kg", phi: null };
  if (!o.dk) return { gia, hoi: "dk", phi: null };
  const kgDon = o.kgThung * o.thung;
  const r = tinh(o.dk, { tien: o.tien ?? gia * kgDon, thung: o.thung, vung: "kanto", tra: "daibiki" });
  const g = giaCoPhi(gia, kgDon, r);
  return { gia: g.gia, hoi: g.chuaRo ? "dk" : null, phi: r };
}

/** Phí chỉ áp khi bật, nhóm so theo kg và khách mua theo THÙNG (pallet: không áp — không đoán số thùng một pallet). */
export const phiCua = (n: Pick<Nhom, "don_vi_so">, sl: SoLuong, phi: PhiSoSanh | null | undefined) =>
  phi && sl !== "pallet" && n.don_vi_so === "kg" ? phi : null;

/** Giá một mặt hàng tại `sl` (+ giá 1 thùng) — kèm phí khi `phi` (đã qua phiCua). Giá 1 thùng = đơn 1 thùng. */
function giaMH(q: QuanSat, sl: SoLuong, phi: PhiSoSanh | null) {
  const t = giaTai(q, sl), le = giaTai(q, "1").gia;
  if (!phi) return { ...t, giaLe: le, hoi: null as LyDoHoiPhi | null, phi: null as KetQuaPhi | null };
  const dk = phi.ben.get(q.ma_doi_thu), thung = Number(sl);
  const a = apPhi(t.gia, { dk, thung, kgThung: q.kg_thung_dt, tien: q.gia_thung == null ? null : q.gia_thung * thung });
  const l = apPhi(le, { dk, thung: 1, kgThung: q.kg_thung_dt, tien: q.gia_thung });
  return { gia: a.gia, khongGhiPallet: t.khongGhiPallet, giaLe: l.hoi ? le : l.gia, hoi: a.hoi, phi: a.phi };
}

/** Giá KOME để so (giaKome) — kèm phí khi `phi` áp được: đơn = số thùng × kome_kg_thung, tiền = giá × kg của đơn. */
export function giaKomePhi(n: Nhom, gk: string, sl: SoLuong, phi?: PhiSoSanh | null):
  { gia: number | null; giaLe: number | null; hoi: LyDoHoiPhi | null; phi: KetQuaPhi | null } {
  const gK = giaKome(n, gk), p = phiCua(n, sl, phi);
  if (!p) return { gia: gK, giaLe: gK, hoi: null, phi: null };
  const a = apPhi(gK, { dk: p.kome, thung: Number(sl), kgThung: n.kome_kg_thung });
  const l = apPhi(gK, { dk: p.kome, thung: 1, kgThung: n.kome_kg_thung });
  return { gia: a.gia, giaLe: l.hoi ? gK : l.gia, hoi: a.hoi, phi: a.phi };
}

export const thieuQuyCach = (q: QuanSat) => q.so_goi_thung == null || q.kl_goi_g == null;
/** MỘT chỗ quyết định dòng nào VẼ / ĐẾM: không khách kể, và (070) là dòng đại diện của mặt hàng — các mức giá khác của cùng
 *  mặt hàng không vẽ thêm thanh. Dòng thiếu cờ (`dai_dien` undefined) vẫn vẽ. */
export const veDuoc = (q: QuanSat) => q.loai_nguon !== "khach_ke" && q.dai_dien !== false;
/** Các mức giá KHÁC của cùng mặt hàng (cùng bên + mat_hang_khoa) trong nhóm — để liệt kê trong ô nổi; rẻ trước. */
export const mucKhac = (n: Nhom, q: QuanSat): QuanSat[] =>
  n.quan_sat.filter(x => x !== q && x.loai_nguon !== "khach_ke" && x.ma_doi_thu === q.ma_doi_thu && x.mat_hang_khoa === q.mat_hang_khoa)
    .sort((a, b) => (a.yen_chuan == null ? (b.yen_chuan == null ? 0 : 1) : b.yen_chuan == null ? -1 : a.yen_chuan - b.yen_chuan));
const tenBen = (q: QuanSat) => q.ten_doi_thu ?? q.ma_doi_thu;
/** So giá tăng dần, null xếp cuối (ổn định). */
const theoGia = (a: number | null, b: number | null) => (a == null ? (b == null ? 0 : 1) : b == null ? -1 : a - b);
/** Dòng biểu đồ: thường trước (giá tăng), bất thường sau cùng. */
const theoDong = (a: Dong, b: Dong) => Number(a.bt) - Number(b.bt) || theoGia(a.gia, b.gia);

/** % so KOME — nhưng KHÔNG BAO GIỜ so giá đã cộng phí với giá trần: một bên (mặt hàng hoặc KOME) còn "?" phí → null. */
const pSo = (gia: number | null, gK: number | null, hoi: LyDoHoiPhi | null, komeHoi: LyDoHoiPhi | null) =>
  (hoi || komeHoi ? null : phanTram(gia, gK));

function dongTu(q: QuanSat, sl: SoLuong, gK: number | null, phi: PhiSoSanh | null, komeHoi: LyDoHoiPhi | null): Dong {
  const { gia, khongGhiPallet, giaLe, hoi, phi: r } = giaMH(q, sl, phi);
  const bt = laBatThuong(q);
  return { kome: false, q, ben: tenBen(q), ten: q.ten_goc, gia, giaLe, p: bt ? null : pSo(gia, gK, hoi, komeHoi), phiHoi: hoi, phi: r, bt,
    cung: q.nhan === "cung_hang", soGoi: q.so_goi_thung, klGoi: q.kl_goi_g, thieu: thieuQuyCach(q),
    cu: (q.tuoi_ngay ?? 0) > NGAY_CU, thueKhongRo: q.thue === "khong_ro", gomShip: q.gom_ship === "co",
    het: q.trang_thai === "het", km: !!q.khuyen_mai || q.gia_truoc_km != null, khongGhiPallet };
}

/** Dòng KOME của một nhóm (biểu đồ cột; bảng nhiệt dùng nó để mở hộp phí / quy cách KOME khi "?" phí là của KOME). */
function dongKome(n: Nhom, k: ReturnType<typeof giaKomePhi>): Dong {
  return { kome: true, ben: "KOME", ten: "KOME", gia: k.gia, giaLe: k.giaLe, p: null, cung: false,
    soGoi: n.kome_goi_thung, klGoi: n.kome_kg_goi == null ? null : n.kome_kg_goi * 1000, thieu: false, cu: false,
    thueKhongRo: false, gomShip: false, het: false, km: false, khongGhiPallet: false, phiHoi: k.hoi, phi: k.phi, bt: false };
}

/** Dòng của biểu đồ cột một nhóm: KOME + mọi mặt hàng (bỏ khách kể; bất thường vẫn vẽ — xám, CUỐI, `d.bt`), lọc chiCung,
 *  xếp giá tăng (null cuối); chưa mở rộng thì giữ KOME + 5 hàng rẻ nhất (không tính bất thường) + mọi cùng thương hiệu.
 *  `an` = số dòng bị ẩn. */
export function dongCot(n: Nhom, o: { sl: SoLuong; gk: string; chiCung: boolean; moRong: boolean; phi?: PhiSoSanh | null }):
  { dong: Dong[]; an: number } {
  const p = phiCua(n, o.sl, o.phi);
  const k = giaKomePhi(n, o.gk, o.sl, p), gK = k.gia;
  const kome = dongKome(n, k);
  const hang = n.quan_sat.filter(q => veDuoc(q) && (!o.chiCung || q.nhan === "cung_hang"))
    .map(q => dongTu(q, o.sl, gK, p, k.hoi)).sort(theoDong);
  const giu = o.moRong ? null : new Set([...hang.filter(d => !d.bt).slice(0, 5), ...hang.filter(d => d.cung)]);
  const hien = giu ? hang.filter(d => giu.has(d)) : hang;
  return { dong: [kome, ...hien].sort(theoDong), an: hang.length - hien.length };
}

/** Khoá ô bảng nhiệt / neo cuộn của MỘT dòng nhóm (nhom_khoa + don_vi_so) và một bên. */
export const khoaNhom = (n: Pick<Nhom, "nhom_khoa" | "don_vi_so">) => `${n.nhom_khoa}|${n.don_vi_so}`;
export const khoaONhiet = (n: Pick<Nhom, "nhom_khoa" | "don_vi_so">, ben: string) => `${khoaNhom(n)}|${ben}`;

/** Ô bảng nhiệt: mỗi (nhóm, bên) — mặt hàng cùng thương hiệu rẻ nhất, không có thì khác thương hiệu rẻ nhất.
 *  `ben` = tên hiển thị (ten_doi_thu ?? ma_doi_thu), xếp theo số nhóm có mặt giảm dần; khoá ô = `khoaONhiet(n, ben)`
 *  (`${nhom_khoa}|${don_vi_so}|${ben}` — một nhom_khoa có thể có nhiều dòng, mỗi don_vi_so một dòng). */
/** `hoi` = "?" phí của MẶT HÀNG; `komeHoi` = "?" phí của KOME (nhóm đó) — ô bấm mở đúng hộp của bên thiếu (`dong` /
 *  `dongKome` là dòng mà MoPhi của BieuDoCot nhận). */
/** `bt` = ô chỉ có giá bất thường (bên đó không còn mặt hàng thường nào trong nhóm): xám, p null, bấm mở pop-up. */
export type ONhiet = { q: QuanSat; p: number | null; so: number; cung: boolean; hoi: LyDoHoiPhi | null;
  komeHoi: LyDoHoiPhi | null; dong: Dong; dongKome: Dong; bt: boolean };
export function oNhiet(ds: Nhom[], o: { sl: SoLuong; gk: string; chiCung: boolean; phi?: PhiSoSanh | null }):
  { ben: string[]; o: Map<string, ONhiet> } {
  const ket = new Map<string, ONhiet>();
  const soNhom = new Map<string, number>();
  for (const n of ds) {
    const p = phiCua(n, o.sl, o.phi);
    const k = giaKomePhi(n, o.gk, o.sl, p), gK = k.gia;
    const theoBen = new Map<string, QuanSat[]>();
    for (const q of n.quan_sat) {
      if (!veDuoc(q) || (o.chiCung && q.nhan !== "cung_hang")) continue;
      const b = tenBen(q);
      (theoBen.get(b) ?? theoBen.set(b, []).get(b)!).push(q);
    }
    for (const [b, ds3] of theoBen) {
      // Giá bất thường chỉ đứng ô khi bên đó KHÔNG còn mặt hàng thường nào (không để ¥1 chỗ giữ thành "rẻ nhất").
      const thuong = ds3.filter(q => !laBatThuong(q)), ds2 = thuong.length ? thuong : ds3, bt = !thuong.length;
      const cung = ds2.filter(q => q.nhan === "cung_hang");
      const chon = (cung.length ? cung : ds2).map(q => ({ q, g: giaMH(q, o.sl, p) })).sort((x, y) => theoGia(x.g.gia, y.g.gia))[0];
      ket.set(khoaONhiet(n, b), { q: chon.q, p: bt ? null : pSo(chon.g.gia, gK, chon.g.hoi, k.hoi), so: ds3.length,
        cung: cung.length > 0, hoi: chon.g.hoi, komeHoi: k.hoi, dong: dongTu(chon.q, o.sl, gK, p, k.hoi), dongKome: dongKome(n, k), bt });
      soNhom.set(b, (soNhom.get(b) ?? 0) + 1);
    }
  }
  const ben = [...soNhom.keys()].sort((a, b) => soNhom.get(b)! - soNhom.get(a)! || a.localeCompare(b, "vi"));
  return { ben, o: ket };
}

/** Bấm một ô bảng nhiệt: mặt hàng chưa có giá → pop-up ở ô giá; "?" phí của mặt hàng → hộp phí / quy cách của BÊN đó;
 *  "?" phí chỉ của KOME → hộp phí / quy cách của KOME (cùng MoPhi với biểu đồ cột); còn lại → pop-up mặt hàng. `phiChu` =
 *  đuôi của nhãn đọc màn hình. */
export function bamONhiet(c: ONhiet, sl: SoLuong):
  { loai: "gia" } | { loai: "phi"; dong: Dong } | { loai: "sua" } {
  if (c.bt) return { loai: "sua" };
  if (giaTai(c.q, sl).gia == null) return { loai: "gia" };
  if (c.hoi) return { loai: "phi", dong: c.dong };
  if (c.komeHoi) return { loai: "phi", dong: c.dongKome };
  return { loai: "sua" };
}
export const phiChuONhiet = (c: ONhiet) =>
  (c.bt ? "" : c.hoi ? ", phí giao chưa cộng" : c.komeHoi ? ", phí giao chưa cộng (KOME thiếu điều kiện / quy cách)" : "");

/** Dòng nhóm có giá KHÔNG quy được ra ¥/kg (`don_vi_so` = "don_vi:<đơn vị>", mart.gia_doi_thu_quan_sat): nhãn đơn vị
 *  ("gói", "thùng"…) để tiêu đề thẻ nói rõ "giá theo gói, chưa quy ra ¥/kg" — dòng KOME của thẻ đó không có giá để so
 *  (giá KOME là ¥/kg). Nhóm so theo kg → null. */
export const donViChuaQuy = (n: Pick<Nhom, "don_vi_so">): string | null =>
  n.don_vi_so === "kg" ? null : nhanDonVi(n.don_vi_so.replace(/^don_vi:/, ""));

/** Đếm mặt hàng thiếu quy cách (không tính khách kể; `chiCung` = chỉ đếm hàng cùng thương hiệu — đúng những dòng đang vẽ):
 *  số lượng, mặt hàng đầu tiên, và trường thiếu của nó (để mở pop-up đúng ô). */
export function demThieu(ds: Nhom[], o: { chiCung?: boolean } = {}):
  { so: number; dau: QuanSat | null; truong: "so_goi_thung" | "kl_goi_g" | null } {
  let so = 0; let dau: QuanSat | null = null;
  for (const n of ds) for (const q of n.quan_sat)
    if (veDuoc(q) && (!o.chiCung || q.nhan === "cung_hang") && thieuQuyCach(q)) { so++; dau ??= q; }
  return { so, dau, truong: dau ? (dau.so_goi_thung == null ? "so_goi_thung" : "kl_goi_g") : null };
}

export type NutNhanh = "" | "dat" | "het" | "thieu";
const soThieu = (n: Nhom) => n.quan_sat.filter(q => veDuoc(q) && thieuQuyCach(q)).length;

/** Danh sách cột trái: lọc ngành (URL mang tên OBC, so theo tên HIỂN THỊ `tenNganh` — hai cách viết "_" / "＿" của cùng
 *  ngành là một), bên (`ben` = ma_doi_thu: nhóm có mặt hàng vẽ được của bên đó — từ bóng "Ai bán ngành nào" của Tóm tắt),
 *  tìm (bỏ dấu, ten_nhom + ma_kome), nút nhanh; xếp so_ben giảm dần
 *  ("dat": KOME đắt hơn trung vị > 5%, xếp lệch giảm dần; "het": có mặt hàng hết; "thieu": có mặt hàng thiếu quy cách, xếp số thiếu giảm dần).
 *  Nhóm `gia_kome_lech` (giá KOME lệch bất thường — thường sai đơn vị) không hiện. */
export function locDanhSach(ds: Nhom[], o: { nganh: string; tim: string; nhanh: NutNhanh; ben?: string }): Nhom[] {
  const t = boDau(o.tim.trim());
  const g = o.nganh ? tenNganh(o.nganh) : "";
  const r = ds.filter(n => !n.gia_kome_lech && (!g || tenNganh(n.nganh) === g)
    && (!o.ben || n.quan_sat.some(q => veDuoc(q) && q.ma_doi_thu === o.ben))
    && (!t || boDau(`${n.ten_nhom ?? ""} ${(n.ma_kome ?? []).join(" ")}`).includes(t))
    && (o.nhanh === "" || (o.nhanh === "dat" ? (n.lech_trung_vi ?? 0) > 0.05
      : o.nhanh === "het" ? n.quan_sat.some(q => veDuoc(q) && q.trang_thai === "het") : soThieu(n) > 0)));
  return r.sort((a, b) => o.nhanh === "dat" ? (b.lech_trung_vi ?? 0) - (a.lech_trung_vi ?? 0)
    : o.nhanh === "thieu" ? soThieu(b) - soThieu(a) || b.so_ben - a.so_ben : b.so_ben - a.so_ben);
}

// ---- Đợt 4b task 6 — phụ trợ thuần cho thành phần của tab So sánh (TabSoSanh, BieuDo*, ONoiGia) ----

/** Số mặt hàng đối thủ VẼ được của nhóm (không tính khách kể) — "n mặt hàng đối thủ" ở cột trái. */
export const soMatHang = (n: Nhom) => n.quan_sat.filter(veDuoc).length;

/** Một dòng cột trái = MỘT nhóm. mart.so_sanh_nhom trả mỗi (nhom_khoa, don_vi_so) một dòng — giá đối thủ không quy được
 *  ra ¥/kg (ghi theo gói mà thiếu tịnh 1 gói…) là dòng thứ hai cùng nhóm; hiện cả hai là trông như hai sản phẩm (thấy trên
 *  dữ liệu thật: 88/137 nhóm). `loc` (đã lọc + xếp) quyết định nhóm nào hiện và thứ tự (lần gặp đầu); số đếm và dòng đại diện
 *  (dòng 'kg' — mang % KOME) lấy từ MỌI dòng của nhóm trong `tatCa`, trừ dòng `gia_kome_lech` (cột trái không bao giờ hiện). */
export type DongTrai = { n: Nhom; soKg: number; soChuaQuy: number };
export function dongTrai(loc: Nhom[], tatCa: Nhom[]): DongTrai[] {
  return [...new Set(loc.map(n => n.nhom_khoa))].map(k => {
    const c = tatCa.filter(n => n.nhom_khoa === k && !n.gia_kome_lech);
    const kg = c.find(n => n.don_vi_so === "kg");
    const soChuaQuy = c.filter(n => n.don_vi_so !== "kg").reduce((t, n) => t + soMatHang(n), 0);
    return { n: kg ?? c[0] ?? loc.find(n => n.nhom_khoa === k)!, soKg: kg ? soMatHang(kg) : 0, soChuaQuy };
  });
}

/** "+12%" · "−8%" · "0%"; null → "—". Dấu trừ là "−" (U+2212), cùng nếp `yen` của dinh_dang.ts. */
export const pcDau = (p: number | null | undefined) =>
  p == null ? "—" : `${p > 0 ? "+" : p < 0 ? "−" : ""}${so(Math.abs(p))}%`;

/** Tịnh 1 gói: gam → "250 g" / "1.5 kg" (từ 1.000 g). null → null (thành phần in "?"). */
export const nhanKlGoi = (g: number | null | undefined) =>
  g == null ? null : g >= 1000 ? `${so_luong(g / 1000)} kg` : `${so_luong(g, 1)} g`;

/** Nhóm mặc định khi `?sp=` trống: 3 nhóm nhiều bên nhất (cùng thứ tự "Tất cả" của cột trái). */
export const macDinhSp = (ds: Nhom[]) =>
  [...new Set(locDanhSach(ds, { nganh: "", tim: "", nhanh: "" }).map(n => n.nhom_khoa))].slice(0, 3);

/** Bật / tắt một nhóm trong danh sách chọn. Đã đủ TOI_DA_SP mà bật thêm → giữ nguyên, `day` = true (nháy "Tối đa 8"). */
export function batTat(sp: string[], khoa: string): { sp: string[]; day: boolean } {
  if (sp.includes(khoa)) return { sp: sp.filter(k => k !== khoa), day: false };
  if (sp.length >= TOI_DA_SP) return { sp, day: true };
  return { sp: [...sp, khoa], day: false };
}

/** Nhóm đang chọn theo đúng thứ tự `sp` (một khoá có thể ứng nhiều đơn vị so — giữ hết). */
export const nhomChon = (ds: Nhom[], sp: string[]) => sp.flatMap(k => ds.filter(n => n.nhom_khoa === k));

/** Mọi mặt hàng (vẽ được) của MỘT bên trong một nhóm — ô nổi của bảng nhiệt liệt kê hết; rẻ trước (giá tại `sl`). */
export function matHangCuaBen(n: Nhom, ben: string, o: { sl: SoLuong; chiCung: boolean; phi?: PhiSoSanh | null }): QuanSat[] {
  const p = phiCua(n, o.sl, o.phi);
  return n.quan_sat.filter(q => veDuoc(q) && tenBen(q) === ben && (!o.chiCung || q.nhan === "cung_hang"))
    .sort((a, b) => theoGia(giaMH(a, o.sl, p).gia, giaMH(b, o.sl, p).gia));
}

/** Tiền (¥/kg chưa thuế) của MỘT bậc giá — BẢN HIỂN THỊ của `mart.gia_bac_kg` (migration 067), chỉ cho bảng bậc
 *  của ô nổi (biểu đồ dùng gia_1/5/10/pallet máy chủ đã tính). Cùng công thức: đơn vị giá thùng ÷ kg_thung_dt,
 *  gói ÷ (kl_goi_g / 1000), kg giữ nguyên; ÷ 1,08 khi thue = 'co'. Thiếu quy cách → null (không đoán). */
export function giaBacKg(b: Bac, q: Pick<QuanSat, "kg_thung_dt" | "kl_goi_g" | "thue">): number | null {
  const chia = b.don_vi_gia === "kg" ? 1 : b.don_vi_gia === "thung" ? q.kg_thung_dt : q.kl_goi_g == null ? null : q.kl_goi_g / 1000;
  if (!chia) return null;
  return b.gia / chia / (q.thue === "co" ? 1.08 : 1);
}

/** Một bậc quy ra số thùng (cùng `tu_thung` của mart.gia_bac_kg); pallet → Infinity; thiếu quy cách → null. */
function tuThung(b: Bac, q: QuanSat): number | null {
  if (b.don_vi_sl === "pallet") return Infinity;
  if (b.don_vi_sl === "thung") return b.tu;
  const chia = b.don_vi_sl === "kg" ? q.kg_thung_dt : q.so_goi_thung;
  return chia ? b.tu / chia : null;
}

/** Nhãn bậc đúng như bảng giá ghi: "từ 24 kg" · "từ 5 thùng" · "từ 40 gói" · "giá pallet". */
export const nhanBac = (b: Bac) => b.don_vi_sl === "pallet" ? "giá pallet"
  : `từ ${so_luong(b.tu)} ${b.don_vi_sl === "thung" ? "thùng" : b.don_vi_sl === "goi" ? "gói" : "kg"}`;

export type DongBac = { nhan: string; kg: number | null; goi: number | null; thung: number | null; p: number | null;
  dang: boolean; re: boolean };

/** Bảng bậc của ô nổi: dòng "giá lẻ" (yen_chuan) rồi từng bậc theo thứ tự bảng giá ghi; không có bậc → MỘT dòng
 *  "mọi số lượng". ¥/gói = ¥/kg × kl_goi_g/1000, ¥/thùng = ¥/kg × kg_thung_dt (thiếu quy cách → null).
 *  `dang` = dòng ứng với giá máy chủ đã chọn cho `sl` (giaTai; lệch ≤ ¥1 vì làm tròn — trùng giá thì dòng đầu).
 *  `re` = rẻ hơn dòng trên. `toiThieu` = nhãn bậc đầu khi bậc đầu > 1 thùng mà KHÔNG rẻ hơn giá lẻ (tức giá lẻ chỉ bán
 *  từ số lượng đó — "530¥/kg x 20kg"); bậc đầu rẻ hơn giá lẻ là giảm giá, không phải đặt tối thiểu. */
export function bangBac(q: QuanSat, sl: SoLuong, gK: number | null):
  { dong: DongBac[]; coBac: boolean; toiThieu: string | null } {
  const le = q.yen_chuan ?? q.gia_1;
  const dong1 = (nhan: string, kg: number | null) => ({ nhan, kg,
    goi: kg == null || q.kl_goi_g == null ? null : kg * q.kl_goi_g / 1000,
    thung: kg == null || q.kg_thung_dt == null ? null : kg * q.kg_thung_dt,
    p: phanTram(kg, gK), dang: false, re: false });
  const bac = q.bac ?? [];
  if (!bac.length) return { dong: [{ ...dong1("mọi số lượng", q.gia_1 ?? le), dang: true }], coBac: false, toiThieu: null };
  const dong: DongBac[] = [dong1("giá lẻ", le), ...bac.map(b => dong1(nhanBac(b), giaBacKg(b, q)))];
  dong.forEach((d, i) => { const t = dong[i - 1]?.kg; d.re = i > 0 && d.kg != null && t != null && d.kg < t - 0.5; });
  const muc = giaTai(q, sl).gia;
  if (muc != null) {
    let tot = -1, lech = Infinity;
    dong.forEach((d, i) => { if (d.kg != null && Math.abs(d.kg - muc) < lech - 1e-9) { lech = Math.abs(d.kg - muc); tot = i; } });
    if (tot >= 0 && lech <= 1) dong[tot].dang = true;
  }
  const dau = bac[0], tu = tuThung(dau, q), gDau = giaBacKg(dau, q);
  const toiThieu = dau.don_vi_sl !== "pallet" && tu != null && tu > 1 && gDau != null && le != null && gDau >= le - 0.5 ? nhanBac(dau).replace(/^từ /, "") : null;
  return { dong, coBac: true, toiThieu };
}

/** Phần "phí giao" của ô nổi (null khi không áp: tắt, pallet, nhóm không so theo kg). */
export type PhiNoi = { gia: number | null; hoi: LyDoHoiPhi | null; r: KetQuaPhi | null; thung: number };
export function phiMatHang(n: Nhom, q: QuanSat, sl: SoLuong, phi: PhiSoSanh | null | undefined): PhiNoi | null {
  const p = phiCua(n, sl, phi);
  if (!p) return null;
  const g = giaMH(q, sl, p);
  return { gia: g.gia, hoi: g.hoi, r: g.phi, thung: Number(sl) };
}
export function phiKome(n: Nhom, gk: string, sl: SoLuong, phi: PhiSoSanh | null | undefined): PhiNoi | null {
  if (!phiCua(n, sl, phi)) return null;
  const k = giaKomePhi(n, gk, sl, phi);
  return { gia: k.gia, hoi: k.hoi, r: k.phi, thung: Number(sl) };
}
