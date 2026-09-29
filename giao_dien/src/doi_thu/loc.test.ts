import { describe, expect, it } from "vitest";
import { locNhom, locQuanSat, viTriKome } from "./loc";
import type { Nhom, QuanSat } from "./kieu";

const qs = (o: Partial<QuanSat>): QuanSat => ({ nhan: "thay_the", trang_thai_duyet: "ai_doc", ...o } as QuanSat);
const nhom = (o: Partial<Nhom>): Nhom => ({ ten_nhom: "Ca Ba sa cat khuc", ma_kome: ["NT01"], quan_sat: [qs({})], ...o } as Nhom);
const L = { tim: "", chi_cung_hang: false, chi_xac_nhan: false };

describe("lọc so sánh", () => {
  it("chỉ cùng hàng ẩn hàng thay thế", () => {
    expect(locQuanSat([qs({ nhan: "cung_hang" }), qs({})], { ...L, chi_cung_hang: true })).toHaveLength(1);
  });
  it("nhóm không còn quan sát nào thì ẩn", () => {
    expect(locNhom([nhom({})], { ...L, chi_xac_nhan: true })).toHaveLength(0);
  });
  it("tìm được chữ đ", () => {
    expect(locNhom([nhom({ ten_nhom: "Đậu hũ" })], { ...L, tim: "dau hu" })).toHaveLength(1);
  });
  it("tìm không dấu, theo cả mã KOME", () => {
    expect(locNhom([nhom({})], { ...L, tim: "basa" })).toHaveLength(0);
    expect(locNhom([nhom({})], { ...L, tim: "ba sa" })).toHaveLength(1);
    expect(locNhom([nhom({})], { ...L, tim: "nt01" })).toHaveLength(1);
  });
  it("vị trí KOME", () => {
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0 }))).toBe("KOME rẻ nhất");
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0.25 }))).toBe("25% giá đối thủ rẻ hơn KOME");
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 1 }))).toBe("KOME đắt nhất");
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0.004 }))).not.toContain("rẻ nhất");
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0.996 }))).not.toContain("đắt nhất");
    expect(viTriKome(nhom({ gia_kome: null, ty_le_re_hon_kome: null }))).toBeNull();
  });
});
