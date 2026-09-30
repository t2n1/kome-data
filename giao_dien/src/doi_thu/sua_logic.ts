// Logic thuần của các pop-up sửa (SuaMatHang.tsx, SuaNho.tsx) — đặc tả 2026-09-29-doi-thu-giao-dien-moi §4.7.
// Máy chủ (kome/doi_thu.py::sua_mat_hang, kome/doi_thu_giao.py) vẫn là trọng tài: ở đây chỉ dựng thân POST gồm
// ĐÚNG những trường đã đổi so với lúc mở, và chặn sớm vài lỗi hiển nhiên để khỏi mất một lượt gửi.
import { gio_tokyo } from "../dinh_dang";
import type { Bac, DaBo, GiaoHang, QuanSat, ThayBoi, XungDot } from "./kieu";

export type BacNhap = { tu: string; don_vi_sl: Bac["don_vi_sl"]; gia: string; don_vi_gia: Bac["don_vi_gia"] };
/** `ten_goc` / `quy_cach_goc` / `kg_moi_don_vi_gia`: chỉ bảng sửa (TabDuyet › BangSua) đổi — pop-up không vẽ hai ô này, nên chúng luôn bằng lúc mở.
 *  `ma_kome` / `nhom_id`: ô "Mã KOME" và "Nhóm so sánh" của phần So với (B13 — thay khung "Ghép với KOME" cũ của Duyệt);
 *  `nhom_id` "" = theo mã KOME (không nhóm ghép tường minh). */
export type FormMatHang = { nhan: "cung_hang" | "thay_the" | "khong"; ma_kome: string; nhom_id: string;
  ten_goc: string; quy_cach_goc: string; kg_moi_don_vi_gia: string;
  trang_thai: string; khuyen_mai: string;
  gia_truoc_km: string; so_goi_thung: string; kl_goi_g: string; gia_goc: string; don_vi_gia: string; thue: string; bac: BacNhap[];
  vi_sao_gia: "" | "doc_sai" | "da_doi"; loai_nguon: string; lien_ket_bang_chung: string };

/** Trường giá: đụng vào là phải nói "vì sao đổi giá" (= kome.doi_thu.TRUONG_GIA). */
export const TRUONG_GIA = ["gia_goc", "don_vi_gia", "thue", "bac"] as const;
export const GOI_TOI_DA = 100000;        // = kome.doi_thu.GOI_TOI_DA
export const KL_GOI_TOI_DA = 30000;      // = kome.doi_thu.KL_GOI_TOI_DA (g)

const PHAY_NGHIN = /^\d{1,3}(,\d{3})+(\.\d+)?$/;
const PHAY_THAP_PHAN = /^\d+,\d+$/;
const SO_THUONG = /^\d+(\.\d+)?$/;

/** Đọc số người gõ, CÙNG luật `kome.doi_thu._so`: '5,300' = phẩy nghìn, '0,5' = phẩy thập phân; `phayThapPhan`
 *  (ô gam / kg): phẩy LUÔN là thập phân ('1,500' = 1.5). Rỗng → null; không phải số thường → NaN. */
export function docSoNhap(s: string, phayThapPhan = false): number | null {
  let t = s.trim();
  if (!t) return null;
  if (phayThapPhan && PHAY_THAP_PHAN.test(t)) t = t.replace(",", ".");
  else if (PHAY_NGHIN.test(t)) t = t.replace(/,/g, "");
  else if (PHAY_THAP_PHAN.test(t)) t = t.replace(",", ".");
  return SO_THUONG.test(t) ? Number(t) : NaN;
}

const chu = (n: number | null | undefined) => (n == null ? "" : String(n));

export function formTu(q: QuanSat): FormMatHang {
  return {
    nhan: q.nhan ?? "khong", ma_kome: q.ma_kome ?? q.ma_ghep ?? "", nhom_id: q.nhom_ghep == null ? "" : String(q.nhom_ghep),
    ten_goc: q.ten_goc ?? "", quy_cach_goc: q.quy_cach_goc ?? "", kg_moi_don_vi_gia: chu(q.kg_moi_don_vi_gia),
    trang_thai: q.trang_thai, khuyen_mai: q.khuyen_mai ?? "",
    gia_truoc_km: chu(q.gia_truoc_km),
    so_goi_thung: chu(q.so_goi_thung), kl_goi_g: chu(q.kl_goi_g), gia_goc: chu(q.gia_goc),
    don_vi_gia: q.don_vi_gia ?? "", thue: q.thue ?? "",
    bac: (q.bac ?? []).map(b => ({ tu: String(b.tu), don_vi_sl: b.don_vi_sl, gia: String(b.gia), don_vi_gia: b.don_vi_gia })),
    vi_sao_gia: "", loai_nguon: "", lien_ket_bang_chung: "",
  };
}

/** Hai ô số "bằng nhau" khi cùng giá trị số (gõ '5,300' cho 5300 không phải là đổi); không đọc được thì so chữ. */
function cungSo(a: string, b: string, phayThapPhan = false): boolean {
  const x = docSoNhap(a, phayThapPhan), y = docSoNhap(b, phayThapPhan);
  if (x === null || y === null) return x === y;
  if (Number.isNaN(x) || Number.isNaN(y)) return a.trim() === b.trim();
  return x === y;
}

/** Số của bậc gửi lên: số khi đọc được, chữ gốc khi không (máy chủ trả câu lỗi), null khi ô trống. */
function soBac(s: string): number | string | null {
  const x = docSoNhap(s);
  return x === null ? null : Number.isNaN(x) ? s.trim() : x;
}

/** Bậc chuẩn hoá: bỏ bậc trống CẢ HAI ô. */
function bacGui(ds: BacNhap[]) {
  return ds.filter(b => b.tu.trim() || b.gia.trim())
    .map(b => ({ tu: soBac(b.tu), don_vi_sl: b.don_vi_sl, gia: soBac(b.gia), don_vi_gia: b.don_vi_gia }));
}

/** Những trường ĐÃ ĐỔI so với lúc mở (formTu(q)), dạng máy chủ nhận. */
function thayDoi(q: QuanSat, f: FormMatHang): Record<string, unknown> {
  const g = formTu(q), d: Record<string, unknown> = {};
  if (f.ten_goc.trim() !== g.ten_goc.trim()) d.ten_goc = f.ten_goc.trim();
  if (f.quy_cach_goc.trim() !== g.quy_cach_goc.trim()) d.quy_cach_goc = f.quy_cach_goc.trim();
  if (!cungSo(f.kg_moi_don_vi_gia, g.kg_moi_don_vi_gia, true)) d.kg_moi_don_vi_gia = f.kg_moi_don_vi_gia.trim();
  if (f.trang_thai !== g.trang_thai) d.trang_thai = f.trang_thai;
  if (f.khuyen_mai.trim() !== g.khuyen_mai.trim()) d.khuyen_mai = f.khuyen_mai.trim();
  if (!cungSo(f.gia_truoc_km, g.gia_truoc_km)) d.gia_truoc_km = f.gia_truoc_km.trim();     // "" = xoá (TRUONG_XOA_DUOC)
  if (!cungSo(f.so_goi_thung, g.so_goi_thung)) d.so_goi_thung = f.so_goi_thung.trim();
  if (!cungSo(f.kl_goi_g, g.kl_goi_g, true)) d.kl_goi_g = f.kl_goi_g.trim();
  if (!cungSo(f.gia_goc, g.gia_goc)) d.gia_goc = f.gia_goc.trim();
  if (f.don_vi_gia !== g.don_vi_gia) d.don_vi_gia = f.don_vi_gia;
  if (f.thue !== g.thue) d.thue = f.thue;
  const bac = bacGui(f.bac);
  if (JSON.stringify(bac) !== JSON.stringify(bacGui(g.bac))) d.bac = bac;
  return d;
}

/** Phần ghép đã đổi so với lúc mở: nhãn · mã KOME · nhóm ghép tường minh. */
function doiGhep(q: QuanSat, f: FormMatHang) {
  const g = formTu(q);
  return { nhan: f.nhan !== g.nhan, ma: f.ma_kome.trim() !== g.ma_kome.trim(), nhom: f.nhom_id !== g.nhom_id };
}

export function payload(q: QuanSat, f: FormMatHang, ghi_de: boolean): { body: object; doi_gia: boolean; rong: boolean } {
  const thay_doi = thayDoi(q, f);
  const doi_gia = TRUONG_GIA.some(k => k in thay_doi);
  const gh = doiGhep(q, f);
  const body: Record<string, unknown> = { nguon: q.nguon, id: q.id, da_xem: q.sua_cuoi, ghi_de };
  if (gh.nhan) body.nhan = f.nhan;
  // Gửi khoá CHỈ khi đổi (máy chủ: có khoá = đổi; không khoá = giữ mã / nhóm đang có). "" / null = bỏ.
  if (gh.ma) body.ma_kome = f.ma_kome.trim() || null;
  if (gh.nhom) body.nhom_id = f.nhom_id ? Number(f.nhom_id) : null;
  body.thay_doi = thay_doi;
  if (doi_gia && f.vi_sao_gia) {
    body.vi_sao_gia = f.vi_sao_gia;
    if (f.vi_sao_gia === "da_doi") {
      // "Giá đã đổi" thêm một dòng giá MỚI; máy chủ không chép bậc / khuyến mãi của dòng nạp cũ (điều kiện của giá cũ)
      // → gửi kèm những gì người dùng ĐANG THẤY trong form (ô trống thì thôi), để thấy gì lưu nấy.
      const bac = bacGui(f.bac);
      if (!("bac" in thay_doi) && bac.length) thay_doi.bac = bac;
      if (!("khuyen_mai" in thay_doi) && f.khuyen_mai.trim()) thay_doi.khuyen_mai = f.khuyen_mai.trim();
      if (!("gia_truoc_km" in thay_doi) && f.gia_truoc_km.trim()) thay_doi.gia_truoc_km = f.gia_truoc_km.trim();
      body.loai_nguon = f.loai_nguon;
      if (f.lien_ket_bang_chung.trim()) body.lien_ket_bang_chung = f.lien_ket_bang_chung.trim();
    }
  }
  return { body, doi_gia, rong: !gh.nhan && !gh.ma && !gh.nhom && Object.keys(thay_doi).length === 0 };
}

/** "→ 1 thùng = … kg": số gói × tịnh 1 gói (g) ÷ 1000; thiếu / sai / ≤ 0 → null (in "?", không in 0). */
export const kgThung = (so_goi: string, kl_goi_g: string): number | null => {
  const n = docSoNhap(so_goi), g = docSoNhap(kl_goi_g, true);
  if (n === null || g === null || !(n > 0) || !(g > 0)) return null;
  return Math.round(n * g) / 1000;
};

/** Lỗi hiển nhiên trước khi gửi (máy chủ vẫn kiểm lại hết); null = gửi được. Chỉ xét trường ĐÃ ĐỔI. */
export function kiemForm(q: QuanSat, f: FormMatHang): string | null {
  const gh = doiGhep(q, f);
  if (gh.ma && f.ma_kome.trim() && f.nhan === "khong") return "Ghép với mã mới: chọn cùng thương hiệu hoặc khác thương hiệu.";
  if ((gh.nhan || gh.ma || gh.nhom) && f.nhan !== "khong" && !f.ma_kome.trim()) return "Nhập mã KOME trước.";
  const d = thayDoi(q, f);
  const daDoi = f.vi_sao_gia === "da_doi" && TRUONG_GIA.some(k => k in d);
  if (q.nguon === "nap" && !daDoi && (["ten_goc", "quy_cach_goc", "kg_moi_don_vi_gia", "so_goi_thung", "kl_goi_g", "gia_goc"] as const).some(k => k in d && !f[k].trim()))
    return "Để trống không xoá được số máy đã đọc — nhập số đúng, hoặc chọn “Giá đã đổi” nếu bảng giá mới khác.";
  if ("so_goi_thung" in d && f.so_goi_thung.trim()) {
    const n = docSoNhap(f.so_goi_thung);
    if (n === null || !Number.isInteger(n) || n < 1 || n > GOI_TOI_DA)
      return `Số gói / thùng phải là số nguyên từ 1 đến ${GOI_TOI_DA.toLocaleString("ja-JP")}.`;
  }
  if ("kl_goi_g" in d && f.kl_goi_g.trim()) {
    const g = docSoNhap(f.kl_goi_g, true);
    if (g === null || !(g > 0) || g > KL_GOI_TOI_DA) return `Tịnh 1 gói (g) phải lớn hơn 0 và tối đa ${KL_GOI_TOI_DA.toLocaleString("ja-JP")}.`;
  }
  if ("kg_moi_don_vi_gia" in d && f.kg_moi_don_vi_gia.trim()) {
    const x = docSoNhap(f.kg_moi_don_vi_gia, true);
    if (x === null || !(x > 0)) return "Số kg / đơn vị giá phải lớn hơn 0.";
  }
  if ("gia_goc" in d && f.gia_goc.trim()) {
    const x = docSoNhap(f.gia_goc);
    if (x === null || Number.isNaN(x)) return "Giá phải là số.";
  }
  if ("gia_truoc_km" in d && f.gia_truoc_km.trim()) {
    const x = docSoNhap(f.gia_truoc_km);
    if (x === null || Number.isNaN(x)) return "Giá trước khuyến mãi phải là số.";
  }
  if ("bac" in d) {
    for (const b of f.bac) {
      if (!b.tu.trim() && !b.gia.trim()) continue;
      if (!b.tu.trim() || !b.gia.trim()) return "Mỗi bậc cần cả số lượng và giá.";
      const t = docSoNhap(b.tu), g = docSoNhap(b.gia);
      if (!(t !== null && t > 0) || !(g !== null && g > 0)) return "Số lượng và giá của bậc phải là số lớn hơn 0.";
    }
  }
  if (TRUONG_GIA.some(k => k in d)) {
    if (!f.vi_sao_gia) return "Chọn vì sao đổi giá.";
    if (f.vi_sao_gia === "da_doi") {
      if (!f.loai_nguon) return "Chọn loại nguồn của giá mới.";
      const lk = f.lien_ket_bang_chung.trim();
      if (lk && !/^https:\/\/\S+$/i.test(lk)) return "Link bằng chứng phải bắt đầu bằng https://";
    }
  }
  return null;
}

// ---------------------------------------------------------------- xung đột (409) + lịch sử

/** Thân 409 của mọi POST sửa → XungDot; lỗi khác → null. 409 không kèm `xung_dot` vẫn cho hỏi Ghi đè. */
export function docXungDot(e: unknown): XungDot | null {
  if (!e || typeof e !== "object" || (e as { ma?: unknown }).ma !== 409) return null;
  const x = ((e as { du_lieu?: unknown }).du_lieu as { xung_dot?: Partial<XungDot> } | null | undefined)?.xung_dot;
  const tb = x?.thay_boi;
  return {
    ai: typeof x?.ai === "string" ? x.ai : null, luc: typeof x?.luc === "string" ? x.luc : "",
    sau: x?.sau ?? null, sua_cuoi: typeof x?.sua_cuoi === "number" ? x.sua_cuoi : 0,
    thay_boi: tb && (tb.nguon === "tay" || tb.nguon === "nap") && typeof tb.id === "number" ? { nguon: tb.nguon, id: tb.id } : null,
  };
}

/** Dấu ✎ (đặc tả §4.7 "dòng đó mang dấu ✎"): mặt hàng đã có ít nhất một lần ghi nhật ký (sửa / xác nhận / ghép). */
export const daSua = (q: Pick<QuanSat, "sua_cuoi"> | null | undefined) => (q?.sua_cuoi ?? 0) > 0;

/** "Hoàn tác" của dải "Đã bỏ khỏi nhóm" (B15): ghi lại nhãn cũ qua CÙNG đường lưu của pop-up (POST /sua-mat-hang),
 *  chống sửa đè bằng sua_cuoi lúc đọc. */
export const thanHoanTac = (x: DaBo) => ({ nguon: x.nguon, id: x.id, da_xem: x.sua_cuoi, ghi_de: false, nhan: x.nhan_cu });

/** Câu của khung "dòng này đã có bản mới" (B14). */
export function moTaThayBoi(x: Pick<XungDot, "ai" | "luc"> | null): string {
  if (!x || (!x.ai && !x.luc)) return "Dòng này đã có bản mới — sửa trên bản mới.";
  return `Dòng này đã có bản mới (${x.ai || "ai đó"} sửa${x.luc ? ` lúc ${lucNgan(x.luc)}` : ""}) — sửa trên bản mới.`;
}
export type { ThayBoi };

/** "14:02 30/09" (giờ Tokyo). */
export function lucNgan(iso: string | null | undefined): string {
  const t = gio_tokyo(iso);                // "YYYY-MM-DD HH:MM"
  const m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2})$/.exec(t);
  return m ? `${m[4]} ${m[3]}/${m[2]}` : t;
}

/** Nhãn Việt của khoá trong `sau` của nhật ký (mặt hàng, ghép, điều kiện, bên, giao hàng). */
export const NHAN_TRUONG: Record<string, string> = {
  gia_goc: "giá", don_vi_gia: "đơn vị giá", thue: "thuế", bac: "bậc giá", so_goi_thung: "gói / thùng", kl_goi_g: "tịnh 1 gói",
  trang_thai: "tình trạng", khuyen_mai: "khuyến mãi", gia_truoc_km: "giá trước khuyến mãi", ten_goc: "tên hàng",
  quy_cach_goc: "quy cách", kg_moi_don_vi_gia: "kg / đơn vị giá", gom_ship: "gồm ship", kenh_gia: "kênh", muc_gia: "mức giá",
  nhan: "ghép", product_code: "mã KOME", nhom_id: "nhóm", loai_nguon: "loại nguồn", lien_ket_bang_chung: "link bằng chứng",
  ten: "tên", web: "website", ghi_chu: "ghi chú", loai: "loại", noi_dung: "nội dung", bo: "bỏ",
  bao_ship: "bao ship", phi_ship: "phí ship", phi_ship_theo: "tính ship theo", mien_ship_tu: "miễn ship từ",
  mien_ship_kien: "miễn ship theo kiện", thung_moi_kien: "thùng / kiện", phu_phi: "phụ phí vùng", phi_daibiki: "phí daibiki",
  daibiki_tu: "daibiki giảm từ", daibiki_sau: "daibiki sau ngưỡng", ck_mien_daibiki: "chuyển khoản miễn daibiki",
  kien_toi_da_kg: "kiện tối đa", ghep_kien: "ghép kiện", cach_gui: "cách gửi", xac_nhan: "xác nhận",
  an: "ẩn / khôi phục", vao: "gộp mặt hàng",       // 070: nhật ký 'an' / 'hien' (sau = {an}) và 'gop' (sau = {vao})
};
const KHOA_KY_THUAT = new Set(["tay_cu", "tay_moi"]);

/** "đổi gì" = khoá của `sau` (nhãn Việt), bỏ khoá kỹ thuật; không phải object → "". */
export function doiGi(sau: unknown): string {
  if (!sau || typeof sau !== "object" || Array.isArray(sau)) return "";
  return Object.keys(sau).filter(k => !KHOA_KY_THUAT.has(k)).map(k => NHAN_TRUONG[k] ?? k).join(", ");
}

/** "<ai | Ai đó> vừa sửa lúc 14:02 30/09: giá, bậc giá" */
export function moTaXungDot(x: XungDot): string {
  const gi = doiGi(x.sau);
  return `${x.ai || "Ai đó"} vừa sửa${x.luc ? ` lúc ${lucNgan(x.luc)}` : ""}${gi ? `: ${gi}` : ""}`;
}

// ---------------------------------------------------------------- giao hàng (15 trường, kome/doi_thu_giao.py)

export const TRUONG_GIAO_DON = ["bao_ship", "phi_ship", "phi_ship_theo", "mien_ship_tu", "mien_ship_kien", "thung_moi_kien",
  "phi_daibiki", "daibiki_tu", "daibiki_sau", "ck_mien_daibiki", "kien_toi_da_kg", "ghep_kien", "thue", "cach_gui"] as const;
export type TruongGiaoDon = typeof TRUONG_GIAO_DON[number];
export const GIAO_BOOL: readonly TruongGiaoDon[] = ["bao_ship", "ck_mien_daibiki"];
export const GIAO_SO: readonly TruongGiaoDon[] = ["phi_ship", "mien_ship_tu", "mien_ship_kien", "thung_moi_kien", "phi_daibiki",
  "daibiki_tu", "daibiki_sau", "kien_toi_da_kg"];
/** Vùng có ô số riêng; Okinawa là ô chọn (? / +¥ / không nhận). Vùng khác trong `phu_phi` được giữ nguyên. */
export const VUNG_SO = ["hokkaido", "tohoku", "kyushu", "chugoku", "shikoku"] as const;
export type VungSo = typeof VUNG_SO[number];

export type FormGiao = { truong: Record<TruongGiaoDon, string>; vung: Record<VungSo, string>;
  okinawa: "" | "co" | "khong_nhan"; okinawa_so: string };

export function formGiao(g: GiaoHang): FormGiao {
  const truong = {} as Record<TruongGiaoDon, string>;
  for (const t of TRUONG_GIAO_DON) {
    const v = g[t];
    truong[t] = v == null ? "" : String(v);        // bool → "true" / "false"
  }
  const pp = g.phu_phi ?? {};
  const vung = {} as Record<VungSo, string>;
  for (const v of VUNG_SO) vung[v] = typeof pp[v] === "number" ? String(pp[v]) : "";
  const o = pp.okinawa;
  return { truong, vung, okinawa: o === "khong_nhan" ? "khong_nhan" : typeof o === "number" ? "co" : "",
           okinawa_so: typeof o === "number" ? String(o) : "" };
}

const soVung = (s: string): number | string => { const x = docSoNhap(s); return x === null || Number.isNaN(x) ? s.trim() : x; };
function okinawaCua(f: FormGiao): number | string | "khong_nhan" | undefined {
  if (f.okinawa === "khong_nhan") return "khong_nhan";
  return f.okinawa === "co" && f.okinawa_so.trim() ? soVung(f.okinawa_so) : undefined;
}

/** Thân POST /api/doi-thu/giao-hang: CHỈ trường đổi ('' = xoá về "chưa rõ"); `xac_nhan` chỉ cho dòng KOME. */
export function payloadGiao(g: GiaoHang, f: FormGiao, ghi_de: boolean, xac_nhan: boolean): { body: object; rong: boolean } {
  const goc = formGiao(g), d: Record<string, unknown> = {};
  for (const t of TRUONG_GIAO_DON) {
    const a = f.truong[t], b = goc.truong[t];
    const doi = GIAO_SO.includes(t) ? !cungSo(a, b) : a.trim() !== b.trim();   // = _so của máy chủ (phẩy nghìn)
    if (!doi) continue;
    d[t] = GIAO_BOOL.includes(t) ? (a === "" ? "" : a === "true") : a.trim();
  }
  const doiVung = VUNG_SO.filter(v => !cungSo(f.vung[v], goc.vung[v]));
  const doiOki = JSON.stringify(okinawaCua(f)) !== JSON.stringify(okinawaCua(goc));
  if (doiVung.length || doiOki) {
    const pp: Record<string, unknown> = { ...(g.phu_phi ?? {}) };
    for (const v of doiVung) { if (f.vung[v].trim()) pp[v] = soVung(f.vung[v]); else delete pp[v]; }
    if (doiOki) { const o = okinawaCua(f); if (o === undefined) delete pp.okinawa; else pp.okinawa = o; }
    d.phu_phi = Object.keys(pp).length ? pp : "";
  }
  const xac = xac_nhan && g.ma_doi_thu === "KOME";
  const rong = Object.keys(d).length === 0 && !xac;
  if (xac) d.xac_nhan = true;
  return { body: { ma_doi_thu: g.ma_doi_thu, da_xem: g.sua_cuoi, ghi_de, thay_doi: d }, rong };
}
