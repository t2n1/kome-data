import { describe, expect, it } from "vitest";
import { boDau, tachMa, viTriKome, dongMoSan, nhomIdHopLe } from "./loc";
import type { Nhom, QuanSat } from "./kieu";

const qs = (o: Partial<QuanSat>): QuanSat => ({ nhan: "thay_the", trang_thai_duyet: "ai_doc", ...o } as QuanSat);
const nhom = (o: Partial<Nhom>): Nhom => ({ ten_nhom: "Ca Ba sa cat khuc", ma_kome: ["NT01"], quan_sat: [qs({})], ...o } as Nhom);

describe("phụ trợ /doi-thu", () => {
  it("boDau: bỏ dấu, hạ chữ thường, đổi cả Đ/đ", () => {
    expect(boDau("Đậu hũ")).toBe("dau hu");
    expect(boDau("Cá Ba sa")).toBe("ca ba sa");
  });
  it("vị trí KOME", () => {
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0 }))).toBe("KOME rẻ nhất");
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0.25 }))).toBe("25% giá đối thủ rẻ hơn KOME");
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 1 }))).toBe("KOME đắt nhất");
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0.004 }))).not.toContain("rẻ nhất");
    expect(viTriKome(nhom({ gia_kome: 600, ty_le_re_hon_kome: 0.996 }))).not.toContain("đắt nhất");
    expect(viTriKome(nhom({ gia_kome: null, ty_le_re_hon_kome: null }))).toBeNull();
  });

  it("tachMa tách theo phẩy / khoảng trắng / xuống dòng, bỏ trống và trùng", () => {
    expect(tachMa(" NT01, NT02  NT01\nNT03,, ")).toEqual(["NT01", "NT02", "NT03"]);
    expect(tachMa("   ")).toEqual([]);
  });

  it("dongMoSan: nhom_khoa nhiều đơn vị → dòng 'kg' nếu có, không thì dòng đầu; không thấy → null", () => {
    const a = nhom({ nhom_khoa: "ma:NT01", don_vi_so: "don_vi:goi" }), b = nhom({ nhom_khoa: "ma:NT01", don_vi_so: "kg" });
    const c = nhom({ nhom_khoa: "ma:NT02", don_vi_so: "don_vi:goi" });
    expect(dongMoSan([a, b, c], "ma:NT01")).toBe(b);
    expect(dongMoSan([a, c], "ma:NT01")).toBe(a);
    expect(dongMoSan([a, b, c], "ma:XX")).toBeNull();
  });
  it("nhomIdHopLe: id không nằm trong danh sách nhóm đã tải thì về rỗng", () => {
    const ds = [{ id: 3 }, { id: 7 }];
    expect(nhomIdHopLe(ds, "7")).toBe("7");
    expect(nhomIdHopLe(ds, "9")).toBe("");
    expect(nhomIdHopLe([], "7")).toBe("");
    expect(nhomIdHopLe(ds, "")).toBe("");
  });
});
