import { pc } from "../dinh_dang";
import type { Nhom, QuanSat } from "./kieu";

export type BoLoc = {
  tim: string; chi_cung_hang: boolean; chi_xac_nhan: boolean;
  nganh: string;          // lọc NHÓM (Nhom.nganh); "" = mọi ngành
  ben: string;            // lọc DÒNG theo ma_doi_thu; "" = mọi bên
  kenh: string;           // lọc DÒNG: khớp kenh_gia HOẶC muc_gia; "" = tất cả
  tuoi: number | null;    // lọc DÒNG: tuoi_ngay ≤ số này; null = tất cả (dòng không biết tuổi bị ẩn khi bật)
};
export const BO_LOC_TRONG: BoLoc = { tim: "", chi_cung_hang: false, chi_xac_nhan: false, nganh: "", ben: "", kenh: "", tuoi: null };

// \p{M} = mọi dấu kết hợp (thanh, mũ, móc…) sau NFD; "đ" không phân rã nên đổi riêng (hạ chữ thường TRƯỚC để "Đ" hoa cũng khớp).
export const boDau = (s: string) => s.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "").replace(/đ/g, "d");

/** Bộ lọc dòng đang bật — chỉ ẩn dòng chi tiết, số nhóm vẫn của mọi hàng. Ngành lọc NHÓM nên không tính. */
export const dangLocDong = (l: BoLoc) => l.chi_cung_hang || l.chi_xac_nhan || !!l.ben || !!l.kenh || l.tuoi != null;

/** Quan sát còn lại của một nhóm sau bộ lọc (không đổi số của máy chủ — chỉ ẩn dòng). */
export function locQuanSat(ds: QuanSat[], l: BoLoc): QuanSat[] {
  return ds.filter(q => (!l.chi_cung_hang || q.nhan === "cung_hang")
    && (!l.chi_xac_nhan || q.trang_thai_duyet === "da_xac_nhan" || q.trang_thai_duyet === "da_sua" || q.trang_thai_duyet === "nhap_tay")
    && (!l.ben || q.ma_doi_thu === l.ben)
    && (!l.kenh || q.kenh_gia === l.kenh || q.muc_gia === l.kenh)
    && (l.tuoi == null || (q.tuoi_ngay != null && q.tuoi_ngay <= l.tuoi)));
}

export function locNhom(ds: Nhom[], l: BoLoc): Nhom[] {
  const t = boDau(l.tim.trim());
  return ds.filter(n => (!l.nganh || n.nganh === l.nganh) && (!t || boDau(`${n.ten_nhom ?? ""} ${(n.ma_kome ?? []).join(" ")}`).includes(t))
    && locQuanSat(n.quan_sat, l).length > 0);
}

/** Vị trí giá KOME trong nhóm, dạng câu ngắn. "Rẻ nhất" / "đắt nhất" CHỈ khi tỷ lệ đúng bằng 0 / 1. */
export function viTriKome(n: Nhom): string | null {
  if (n.gia_kome == null || n.ty_le_re_hon_kome == null) return null;
  const t = n.ty_le_re_hon_kome;
  if (t === 0) return "KOME rẻ nhất";
  if (t === 1) return "KOME đắt nhất";
  return `${pc(t, 0)} giá đối thủ rẻ hơn KOME`;
}

/** Giá trị có thật trong dữ liệu cho các ô chọn Ngành / Bên / Kênh-mức (đã sắp, bỏ trống). */
export function luaChonLoc(ds: Nhom[]) {
  const nganh = new Set<string>(), kenh = new Set<string>(), ben = new Map<string, string>();
  for (const n of ds) {
    if (n.nganh) nganh.add(n.nganh);
    for (const q of n.quan_sat) {
      if (!ben.has(q.ma_doi_thu)) ben.set(q.ma_doi_thu, q.ten_doi_thu ?? q.ma_doi_thu);
      if (q.kenh_gia) kenh.add(q.kenh_gia);
      if (q.muc_gia) kenh.add(q.muc_gia);
    }
  }
  const sap = (a: Iterable<string>) => [...a].sort((x, y) => x.localeCompare(y, "vi"));
  return { nganh: sap(nganh), kenh: sap(kenh),
    ben: [...ben].map(([ma, ten]) => ({ ma, ten })).sort((x, y) => x.ma.localeCompare(y.ma)) };
}

/** Tách ô nhập nhiều mã (cách nhau bởi phẩy / khoảng trắng / xuống dòng); bỏ trống và trùng. */
export const tachMa = (s: string): string[] => [...new Set(s.split(/[\s,;、，]+/).map(x => x.trim()).filter(Boolean))];

/** Quy cách chưa có kg nào (cả kg/gói lẫn kg/thùng) — chip "Chưa có kg". */
export const chuaCoKg = (q: { kg_moi_goi: number | null; kg_moi_thung: number | null }) => q.kg_moi_goi == null && q.kg_moi_thung == null;
