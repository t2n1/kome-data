// Phụ trợ thuần dùng chung của màn /doi-thu (bỏ dấu, vị trí KOME, tách mã, quy cách, dòng mở sẵn, id nhóm hợp lệ).
import { pc } from "../dinh_dang";
import type { Nhom } from "./kieu";

// \p{M} = mọi dấu kết hợp (thanh, mũ, móc…) sau NFD; "đ" không phân rã nên đổi riêng (hạ chữ thường TRƯỚC để "Đ" hoa cũng khớp).
export const boDau = (s: string) => s.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "").replace(/đ/g, "d");

/** Vị trí giá KOME trong nhóm, dạng câu ngắn. "Rẻ nhất" / "đắt nhất" CHỈ khi tỷ lệ đúng bằng 0 / 1. */
export function viTriKome(n: Nhom): string | null {
  if (n.gia_kome == null || n.ty_le_re_hon_kome == null) return null;
  const t = n.ty_le_re_hon_kome;
  if (t === 0) return "KOME rẻ nhất";
  if (t === 1) return "KOME đắt nhất";
  return `${pc(t, 0)} giá đối thủ rẻ hơn KOME`;
}

/** Tách ô nhập nhiều mã (cách nhau bởi phẩy / khoảng trắng / xuống dòng); bỏ trống và trùng. */
export const tachMa = (s: string): string[] => [...new Set(s.split(/[\s,;、，]+/).map(x => x.trim()).filter(Boolean))];

/** Quy cách chưa có kg nào (cả kg/gói lẫn kg/thùng) — chip "Chưa có kg". */
export const chuaCoKg = (q: { kg_moi_goi: number | null; kg_moi_thung: number | null }) => q.kg_moi_goi == null && q.kg_moi_thung == null;

/** Dòng nhóm để mở sẵn cho ?nhom=<nhom_khoa>: một nhom_khoa có thể có nhiều dòng (mỗi don_vi_so một dòng) — ưu tiên 'kg'. */
export function dongMoSan(ds: Nhom[], khoa: string): Nhom | null {
  const c = ds.filter(n => n.nhom_khoa === khoa);
  return c.find(n => n.don_vi_so === "kg") ?? c[0] ?? null;
}

