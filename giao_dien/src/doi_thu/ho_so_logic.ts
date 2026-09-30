// Logic thuần của tab "Đối thủ" (đợt 4b task 8; bản phác ca-trang-8.html tab Đối thủ) — không React, có test
// (ho_so_logic.test.ts). Dữ liệu: /api/doi-thu/ben/{ma} (quan_sat gồm cả dòng lịch sử, hien_hanh đánh dấu dòng hiện hành)
// + /api/doi-thu/tong-quan (danh sách bên, lưới ngành). Không định nghĩa chỉ số mới: % = mau.ts::phanTram.
import { yen, so } from "../dinh_dang";
import type { DaBo, GiaoHang, QuanSat, TongQuan } from "./kieu";
import { LECH_NGANG, NGAY_CU, laBatThuong, phanTram } from "./mau";
import { tenNganh } from "./nganh";
import { lienKetAnToan, timTrongDrive } from "./nguon";

export type QsHs = QuanSat & { hien_hanh: boolean };

/** Số mặt hàng trùng KOME của mỗi bên = Σ `so_ma` của tq.luoi (mặt hàng HIỆN HÀNH ghép được mã KOME, đếm theo ngành —
 *  một mặt hàng một mã KOME nên một ngành, cộng lại không đếm trùng). Bên không có dòng lưới → 0. */
export function soMaTrung(tq: TongQuan): Map<string, number> {
  const m = new Map<string, number>(tq.ben.map(b => [b.ma, 0]));
  for (const x of tq.luoi) if (m.has(x.ben)) m.set(x.ben, m.get(x.ben)! + x.so_ma);
  return m;
}

/** Hàng chip: mọi bên đang theo dõi (tq.ben), nhiều mặt hàng trùng KOME trước, rồi nhiều dòng hiện hành, rồi tên. */
export function chipBen(tq: TongQuan): { ma: string; ten: string; so: number }[] {
  const t = soMaTrung(tq);
  return [...tq.ben].sort((a, b) => (t.get(b.ma)! - t.get(a.ma)!) || (b.so_dong - a.so_dong) || a.ten.localeCompare(b.ten, "vi"))
    .map(b => ({ ma: b.ma, ten: b.ten, so: t.get(b.ma)! }));
}

/** Bên mở sẵn khi URL không có `?ben=`: bên có NHIỀU mặt hàng hiện hành ghép được KOME nhất (Σ tq.luoi — "ghép được mã
 *  KOME" ≈ "có nhom_khoa": mọi mã KOME là một nhóm ngầm định); hoà (kể cả khi mọi bên 0) → nhiều dòng hiện hành
 *  (`so_dong`) → tên. Không có bên nào → "". Đúng là phần tử đầu của chipBen. */
export const benMacDinh = (tq: TongQuan): string => chipBen(tq)[0]?.ma ?? "";

/** Dòng hiện hành thuộc bảng giá của bên (khách kể không phải bảng giá của bên), mỗi mặt hàng MỘT dòng đại diện (070). */
const cuaBang = (q: QsHs) => q.hien_hanh && q.loai_nguon !== "khach_ke" && q.dai_dien !== false;

/** Một dòng của biểu đồ "Giá bên này so với KOME": quan sát HIỆN HÀNH có `gia_kome_so` (không tính khách kể — không
 *  phải bảng giá của bên), nhóm KHÔNG có giá KOME lệch (`gia_kome_lech`: > 3× / < ⅓ trung vị — cùng cờ Tóm tắt bỏ khỏi
 *  trục; vẽ nó là thanh −99% đỏ giả). p = % yen_chuan so gia_kome_so (cùng đơn vị so); p null = thiếu giá → "?".
 *  `bt` = giá bất thường (mau.ts::laBatThuong, B18): có dòng kể cả khi nhóm không còn trong So sánh (gia_kome_so null — mọi
 *  giá của nhóm đều bất thường), p = null, tro = undefined, xếp CUỐI; vẽ xám, không vào ô số. */
export type DongHs = { q: QsHs; p: number | null; cung: boolean; het: boolean; km: boolean; cu: boolean; thueKhongRo: boolean;
  gomShip: boolean; tro: "gia_goc" | "kl_goi_g" | undefined; bt: boolean };

export const coKm = (q: Pick<QuanSat, "khuyen_mai" | "gia_truoc_km">) => !!(q.khuyen_mai ?? "").trim() || q.gia_truoc_km != null;

/** Dòng bất thường lên biểu đồ (xám) khi đã ghép nhóm — kể cả khi nhóm không có gia_kome_so. */
const btVe = (q: QsHs) => laBatThuong(q) && q.nhom_khoa != null;

/** Xếp p tăng dần (bên này rẻ nhất so KOME trước); p null sau, bất thường cuối cùng; trong nhóm cùng p theo tên nhóm rồi
 *  tên gốc. */
export function dongSoKome(qs: QsHs[]): DongHs[] {
  const thay = new Set<string>();   // một quan sát một dòng (khoá nguon + id), phòng dữ liệu lặp
  const hang = (d: DongHs) => (d.bt ? 2 : d.p == null ? 1 : 0);
  return qs.filter(q => cuaBang(q) && (q.gia_kome_so != null || btVe(q)) && !q.gia_kome_lech
    && !thay.has(q.nguon + q.id) && !!thay.add(q.nguon + q.id)).map(q => {
    const bt = laBatThuong(q), p = bt ? null : phanTram(q.yen_chuan, q.gia_kome_so);
    return { q, p, bt, cung: q.nhan === "cung_hang", het: q.trang_thai === "het", km: coKm(q), cu: (q.tuoi_ngay ?? 0) > NGAY_CU,
      thueKhongRo: q.thue === "khong_ro", gomShip: q.gom_ship === "co",
      tro: p != null || bt ? undefined : q.gia_goc == null ? "gia_goc" as const : "kl_goi_g" as const };
  }).sort((a, b) => hang(a) - hang(b) || (a.p != null && b.p != null ? a.p - b.p : 0)
    || (a.q.ten_nhom ?? "").localeCompare(b.q.ten_nhom ?? "", "vi") || a.q.ten_goc.localeCompare(b.q.ten_goc, "vi"));
}

const demKhac = (qs: QsHs[], f: (q: QsHs) => boolean) => new Set(qs.filter(q => cuaBang(q) && f(q)).map(q => q.nguon + q.id)).size;
/** Số mặt hàng (dòng hiện hành, không khách kể) KHÔNG lên biểu đồ: `lech` = nhóm có giá KOME lệch (→ Dữ liệu › Giá KOME
 *  lệch); `chuaSo` = không thuộc nhóm nào có giá KOME (chưa ghép, hoặc KOME không bán — → Duyệt / sửa của bên). */
/** Dải "Đã bỏ khỏi nhóm" của tab Đối thủ (B15): dòng hiện hành máy chủ gắn `bo_nhom` → DaBo (cùng dạng `da_bo` của
 *  /so-sanh), theo tên nhóm rồi tên hàng. */
export function daBoCuaBen(qs: QsHs[]): DaBo[] {
  return qs.filter(q => q.hien_hanh && q.bo_nhom)
    .map(q => ({ nguon: q.nguon, id: q.id, ma_doi_thu: q.ma_doi_thu, ten_doi_thu: q.ten_doi_thu, ten_goc: q.ten_goc,
      nhom_khoa: q.bo_nhom!.nhom_khoa, ten_nhom: q.bo_nhom!.ten_nhom, nhan_cu: q.bo_nhom!.nhan_cu, sua_cuoi: q.sua_cuoi }))
    .sort((a, b) => (a.ten_nhom ?? a.nhom_khoa).localeCompare(b.ten_nhom ?? b.nhom_khoa, "vi") || a.ten_goc.localeCompare(b.ten_goc, "vi"));
}

export const ngoaiBieuDo = (qs: QsHs[]) => ({
  lech: demKhac(qs, q => q.gia_kome_so != null && !!q.gia_kome_lech),
  chuaSo: demKhac(qs, q => q.gia_kome_so == null && !btVe(q)),
});

export const THU_GON = 25;
/** Thu gọn biểu đồ: nhiều hơn `n` dòng thì giữ `n` dòng |p| lớn nhất (p null — thiếu giá — xếp sau mọi p, giá bất thường
 *  sau cùng), GIỮ thứ tự p của `dong`; `an` = số dòng ẩn. */
export function thuGon<T extends { p: number | null; bt?: boolean }>(dong: T[], n = THU_GON): { hien: T[]; an: number } {
  if (dong.length <= n) return { hien: dong, an: 0 };
  const giu = new Set(dong.map((d, i) => ({ i, k: d.bt ? -2 : d.p == null ? -1 : Math.abs(d.p) }))
    .sort((a, b) => b.k - a.k || a.i - b.i).slice(0, n).map(x => x.i));
  return { hien: dong.filter((_, i) => giu.has(i)), an: dong.length - n };
}

/** Bốn ô số (nhóm giá KOME lệch và giá bất thường KHÔNG tính): trùng KOME = số dòng KHÔNG bất thường của biểu đồ; rẻ hơn
 *  KOME > 5% (p < −5); đang hết (trong các dòng trùng, như bản phác);
 *  khuyến mãi = mọi dòng hiện hành có KM (cùng vị từ với tq.khuyen_mai: ghi chú KM hoặc giá trước KM), không tính khách kể. */
export function o4(qs: QsHs[]): { trung: number; reHon: number; het: number; km: number } {
  const d = dongSoKome(qs).filter(x => !x.bt);
  return { trung: d.length, reHon: d.filter(x => x.p != null && x.p < -LECH_NGANG).length, het: d.filter(x => x.het).length,
    km: qs.filter(q => cuaBang(q) && coKm(q)).length };
}

/** Lịch sử giá theo tháng của MỘT mặt hàng (cùng ma_hang_dt · kênh · mức giá · đơn vị so — cùng khoá hiện hành của
 *  mart): mỗi tháng lấy quan sát MỚI NHẤT có yen_chuan; tháng tăng dần. < 2 tháng → [] (không vẽ). */
export function lichSuThang(qs: QuanSat[], x: QuanSat): { thang: string; gia: number }[] {
  const theo = new Map<string, { ngay: string; gia: number }>();
  for (const y of qs) {
    if (y.ma_hang_dt !== x.ma_hang_dt || y.kenh_gia !== x.kenh_gia || y.muc_gia !== x.muc_gia || y.don_vi_so !== x.don_vi_so
      || y.yen_chuan == null || y.loai_nguon === "khach_ke") continue;
    const t = y.ngay_nguon.slice(0, 7), c = theo.get(t);
    if (!c || y.ngay_nguon > c.ngay) theo.set(t, { ngay: y.ngay_nguon, gia: y.yen_chuan });
  }
  const r = [...theo.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1)).map(([thang, v]) => ({ thang, gia: v.gia }));
  return r.length >= 2 ? r : [];
}

/** "Bán mạnh ngành nào": dòng tq.luoi của bên, gộp theo tên ngành HIỂN THỊ (hai cách viết OBC → một), nhiều trước. */
export function nganhBen(tq: TongQuan, ben: string): { nganh: string; so: number }[] {
  const m = new Map<string, number>();
  for (const x of tq.luoi) if (x.ben === ben) { const g = tenNganh(x.nganh); m.set(g, (m.get(g) ?? 0) + x.so_ma); }
  return [...m.entries()].map(([nganh, so]) => ({ nganh, so })).sort((a, b) => b.so - a.so || a.nganh.localeCompare(b.nganh, "vi"));
}

/** Đầu trang: ngày bảng giá mới nhất (dòng hiện hành, ưu tiên dòng nạp), số dòng hiện hành (không tính khách kể), và
 *  liên kết nguồn gốc của lô mới nhất — file: tìm file trong Drive; web: trang của bên. Không có → null. */
export function dauBen(qs: QsHs[]): { ngay: string | null; soDong: number; nguon: { href: string; chu: string } | null } {
  const hien = qs.filter(cuaBang);
  const nap = hien.filter(q => q.nguon === "nap");
  const moi = [...(nap.length ? nap : hien)].sort((a, b) => (a.ngay_nguon < b.ngay_nguon ? 1 : a.ngay_nguon > b.ngay_nguon ? -1 : 0))[0];
  let nguon: { href: string; chu: string } | null = null;
  if (moi?.nguon === "nap" && moi.hinh_thuc_nguon === "file" && moi.nguon_file) nguon = { href: timTrongDrive(moi.nguon_file), chu: "mở file gốc ↗" };
  else if (moi?.nguon === "nap" && moi.hinh_thuc_nguon === "web" && lienKetAnToan(moi.web_ben)) nguon = { href: lienKetAnToan(moi.web_ben)!, chu: "mở trang của bên ↗" };
  return { ngay: moi?.ngay_nguon ?? null, soDong: hien.length, nguon };
}

/** Dòng giao hàng rỗng (bên chưa có dòng nào): mọi trường null, chưa suy / chưa xác nhận, chưa sửa lần nào. */
export function giaoTrong(ma: string, ten: string | null): GiaoHang {
  return { ma_doi_thu: ma, ten, bao_ship: null, phi_ship: null, phi_ship_theo: null, mien_ship_tu: null, mien_ship_kien: null,
    thung_moi_kien: null, phu_phi: null, phi_daibiki: null, daibiki_tu: null, daibiki_sau: null, ck_mien_daibiki: null,
    kien_toi_da_kg: null, ghep_kien: null, thue: null, cach_gui: null, nguon_chu: null, ngay_nguon: null, suy: false,
    da_xac_nhan: false, sua_cuoi: 0 };
}

const THEO: Record<string, string> = { don: "đơn", thung: "thùng", kien: "kiện" };

/** Tóm tắt giao hàng một dòng: ship · miễn ship · daibiki. `chu` null = chưa biết → "?" cam, bấm mở pop-up ở ô `tru_o`.
 *  Bao ship thì bỏ phần miễn ship (không có nghĩa). */
export function tomTatGiao(g: GiaoHang | null): { nhan: string; chu: string | null; tru_o: string }[] {
  const r: { nhan: string; chu: string | null; tru_o: string }[] = [];
  if (g?.bao_ship) r.push({ nhan: "ship", chu: "bao ship", tru_o: "bao_ship" });
  else r.push({ nhan: "ship", chu: g?.phi_ship == null ? null : yen(g.phi_ship) + (g.phi_ship_theo ? `/${THEO[g.phi_ship_theo]}` : ""),
    tru_o: "phi_ship" });
  if (!g?.bao_ship) r.push({ nhan: "miễn ship", tru_o: "mien_ship_tu",
    chu: g?.mien_ship_tu != null ? `từ ${yen(g.mien_ship_tu)}` : g?.mien_ship_kien != null ? `từ ${so(g.mien_ship_kien)} kiện` : null });
  const sau = g?.daibiki_tu != null && g.daibiki_sau != null
    ? ` (từ ${yen(g.daibiki_tu)}: ${g.daibiki_sau === 0 ? "miễn" : yen(g.daibiki_sau)})` : "";
  r.push({ nhan: "daibiki", chu: g?.phi_daibiki == null ? null : yen(g.phi_daibiki) + sau, tru_o: "phi_daibiki" });
  return r;
}
