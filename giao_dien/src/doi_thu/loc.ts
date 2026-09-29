import type { Nhom, QuanSat } from "./kieu";

export type BoLoc = { tim: string; chi_cung_hang: boolean; chi_xac_nhan: boolean };

const bo_dau = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").toLowerCase();

/** Quan sát còn lại của một nhóm sau bộ lọc (không đổi số của máy chủ — chỉ ẩn dòng). */
export function locQuanSat(ds: QuanSat[], l: BoLoc): QuanSat[] {
  return ds.filter(q => (!l.chi_cung_hang || q.nhan === "cung_hang")
    && (!l.chi_xac_nhan || q.trang_thai_duyet === "da_xac_nhan" || q.trang_thai_duyet === "da_sua" || q.trang_thai_duyet === "nhap_tay"));
}

export function locNhom(ds: Nhom[], l: BoLoc): Nhom[] {
  const t = bo_dau(l.tim.trim());
  return ds.filter(n => (!t || bo_dau(`${n.ten_nhom ?? ""} ${(n.ma_kome ?? []).join(" ")}`).includes(t))
    && locQuanSat(n.quan_sat, l).length > 0);
}

/** Vị trí giá KOME trong nhóm, dạng câu ngắn. */
export function viTriKome(n: Nhom): string | null {
  if (n.gia_kome == null || n.ty_le_re_hon_kome == null) return null;
  const p = Math.round(n.ty_le_re_hon_kome * 100);
  return p === 0 ? "KOME rẻ nhất" : p === 100 ? "KOME đắt nhất" : `${p}% giá đối thủ rẻ hơn KOME`;
}
