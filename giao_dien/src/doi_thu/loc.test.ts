import { describe, expect, it } from "vitest";
import { dangLocDong, locNhom, locQuanSat, tachMa, luaChonLoc, viTriKome, dongMoSan, kemGiaTri, nhomIdHopLe } from "./loc";
import type { Nhom, QuanSat } from "./kieu";

const qs = (o: Partial<QuanSat>): QuanSat => ({ nhan: "thay_the", trang_thai_duyet: "ai_doc", ...o } as QuanSat);
const nhom = (o: Partial<Nhom>): Nhom => ({ ten_nhom: "Ca Ba sa cat khuc", ma_kome: ["NT01"], quan_sat: [qs({})], ...o } as Nhom);
const L = { tim: "", chi_cung_hang: false, chi_xac_nhan: false, nganh: "", ben: "", kenh: "", tuoi: null as number | null };

describe("lọc so sánh", () => {
  it("dangLocDong bật khi một trong hai bộ lọc dòng bật (tìm chữ thì không)", () => {
    expect(dangLocDong(L)).toBe(false);
    expect(dangLocDong({ ...L, tim: "basa" })).toBe(false);
    expect(dangLocDong({ ...L, chi_cung_hang: true })).toBe(true);
    expect(dangLocDong({ ...L, chi_xac_nhan: true })).toBe(true);
  });
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

  it("dangLocDong bật cả với bộ lọc bên / kênh / tuổi; ngành thì không (ngành lọc nhóm, không ẩn dòng)", () => {
    expect(dangLocDong({ ...L, nganh: "Cá" })).toBe(false);
    expect(dangLocDong({ ...L, ben: "vfs" })).toBe(true);
    expect(dangLocDong({ ...L, kenh: "si" })).toBe(true);
    expect(dangLocDong({ ...L, tuoi: 30 })).toBe(true);
  });
  it("lọc ngành chọn NHÓM theo n.nganh", () => {
    const ds = [nhom({ nganh: "Cá" }), nhom({ nganh: "Rau", ten_nhom: "Rau muống" })];
    expect(locNhom(ds, { ...L, nganh: "Rau" }).map(n => n.ten_nhom)).toEqual(["Rau muống"]);
    expect(locNhom(ds, L)).toHaveLength(2);
  });
  it("lọc bên ẩn dòng của bên khác và ẩn nhóm không còn dòng", () => {
    const a = qs({ ma_doi_thu: "vfs" }), b = qs({ ma_doi_thu: "abc" });
    expect(locQuanSat([a, b], { ...L, ben: "vfs" })).toEqual([a]);
    expect(locNhom([nhom({ quan_sat: [b] })], { ...L, ben: "vfs" })).toHaveLength(0);
    expect(locNhom([nhom({ quan_sat: [a, b] })], { ...L, ben: "vfs" })).toHaveLength(1);
  });
  it("lọc kênh/mức khớp kenh_gia HOẶC muc_gia", () => {
    const a = qs({ kenh_gia: "si", muc_gia: null }), b = qs({ kenh_gia: null, muc_gia: "si" }), c = qs({ kenh_gia: "le", muc_gia: "thuong" });
    expect(locQuanSat([a, b, c], { ...L, kenh: "si" })).toEqual([a, b]);
  });
  it("lọc tuổi: ≤ N ngày; dòng không biết tuổi bị ẩn khi bộ lọc bật", () => {
    const moi = qs({ tuoi_ngay: 10 }), cu = qs({ tuoi_ngay: 100 }), la = qs({ tuoi_ngay: null }), bien = qs({ tuoi_ngay: 30 });
    expect(locQuanSat([moi, cu, la, bien], { ...L, tuoi: 30 })).toEqual([moi, bien]);
    expect(locQuanSat([moi, cu, la], L)).toHaveLength(3);
  });
  it("luaChonLoc: ngành, bên, kênh có trong dữ liệu, sắp và bỏ trống", () => {
    const ds = [nhom({ nganh: "Rau", quan_sat: [qs({ ma_doi_thu: "vfs", ten_doi_thu: "VFS", kenh_gia: "si", muc_gia: null })] }),
      nhom({ nganh: "Cá", quan_sat: [qs({ ma_doi_thu: "abc", ten_doi_thu: null, kenh_gia: null, muc_gia: "thuong" }),
        qs({ ma_doi_thu: "vfs", ten_doi_thu: "VFS", kenh_gia: "si", muc_gia: "thuong" })] }),
      nhom({ nganh: null, quan_sat: [] })];
    const c = luaChonLoc(ds);
    expect(c.nganh).toEqual(["Cá", "Rau"]);
    expect(c.ben).toEqual([{ ma: "abc", ten: "abc" }, { ma: "vfs", ten: "VFS" }]);
    expect(c.kenh).toEqual(["si", "thuong"]);
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
  it("kemGiaTri: giá trị trên URL không có trong dữ liệu vẫn có mặt trong danh sách", () => {
    expect(kemGiaTri(["Cá", "Rau"], "Thịt")).toEqual(["Cá", "Rau", "Thịt"]);
    expect(kemGiaTri(["Cá"], "Cá")).toEqual(["Cá"]);
    expect(kemGiaTri(["Cá"], "")).toEqual(["Cá"]);
  });
  it("nhomIdHopLe: id không nằm trong danh sách nhóm đã tải thì về rỗng", () => {
    const ds = [{ id: 3 }, { id: 7 }];
    expect(nhomIdHopLe(ds, "7")).toBe("7");
    expect(nhomIdHopLe(ds, "9")).toBe("");
    expect(nhomIdHopLe([], "7")).toBe("");
    expect(nhomIdHopLe(ds, "")).toBe("");
  });
});
