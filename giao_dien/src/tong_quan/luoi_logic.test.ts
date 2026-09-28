import { describe, expect, it } from "vitest";
import type { OBoCuc } from "../khoi_dau";
import { an, chong, datCho, dichPhim, doiCo, hangTai, hienODay, nen, soHang } from "./luoi_logic";

// Cùng file ca với tests/test_bo_cuc.py::test_nen_giong_het_ban_typescript.
import caTho from "../../../tests/du_lieu/luoi_nen_ca.json";
const CA = caTho as { ten: string; vao: OBoCuc[]; ra: Record<string, number[]> }[];

const o = (id: string, x: number, y: number, rong: number, cao: number): OBoCuc => ({ id, x, y, rong, cao, an: false });
const vt = (ds: OBoCuc[]) => Object.fromEntries(ds.map(p => [p.id, [p.x, p.y]]));
const sach = (ds: OBoCuc[]) => {
  const h = ds.filter(p => !p.an);
  return h.every((a, i) => h.slice(i + 1).every(b => !chong(a, b.x, b.y, b.rong, b.cao)));
};

describe("nen — giống hệt bản Python", () => {
  it("có đủ ca", () => expect(CA.length).toBeGreaterThanOrEqual(8));
  for (const c of CA) it(c.ten, () => expect(vt(nen(c.vao))).toEqual(c.ra));
});

describe("datCho", () => {
  const cot = [o("a", 0, 0, 12, 3), o("b", 0, 3, 12, 3), o("c", 0, 6, 12, 3)];
  it("kéo xuống chưa quá nửa khối: không đổi", () => expect(vt(datCho(cot, "a", 0, 1))).toEqual(vt(cot)));
  it("kéo xuống quá nửa khối: đổi chỗ với khối dưới", () =>
    expect(vt(datCho(cot, "a", 0, 2))).toEqual({ b: [0, 0], a: [0, 3], c: [0, 6] }));
  it("kéo lên quá nửa khối: đổi chỗ với khối trên", () =>
    expect(vt(datCho(cot, "c", 0, 4))).toEqual({ a: [0, 0], c: [0, 3], b: [0, 6] }));
  it("thả ngang lên khối bên cạnh: hai khối đổi chỗ", () => {
    const r = datCho([o("a", 0, 0, 6, 3), o("b", 6, 0, 6, 3)], "a", 6, 0);
    expect(vt(r)).toEqual({ b: [0, 0], a: [6, 0] });
  });
  it("thả ngang mà không còn chỗ bên cạnh: khối bị đè xuống dưới", () => {
    const r = datCho([o("a", 0, 0, 4, 3), o("b", 4, 0, 8, 3)], "a", 4, 0);
    expect(vt(r)).toEqual({ a: [4, 0], b: [4, 3] });
  });
  it("kéo dọc không dạt ngang", () => {
    const r = datCho([o("a", 0, 0, 6, 3), o("b", 0, 3, 6, 3)], "a", 0, 3);
    expect(vt(r)).toEqual({ b: [0, 0], a: [0, 3] });
  });
  it("kẹp trong 12 cột và không âm", () => expect(vt(datCho([o("a", 0, 0, 8, 2)], "a", 9, -4))).toEqual({ a: [4, 0] }));
  it("không bao giờ chồng nhau", () => {
    const ds = [o("a", 0, 0, 8, 6), o("b", 8, 0, 4, 3), o("c", 8, 3, 4, 6), o("d", 0, 6, 6, 3), o("e", 6, 9, 6, 3)];
    for (let x = 0; x < 12; x++) for (let y = 0; y < 14; y++) for (const id of "abcde") expect(sach(datCho(ds, id, x, y))).toBe(true);
  });
});

describe("doiCo / ẩn / hiện", () => {
  it("giãn rộng đẩy khối bên cạnh xuống", () =>
    expect(vt(doiCo([o("a", 0, 0, 6, 3), o("b", 6, 0, 6, 3)], "a", 8, 3))).toEqual({ a: [0, 0], b: [6, 3] }));
  it("kẹp cỡ tối thiểu và mép phải", () => {
    const r = doiCo([o("a", 6, 0, 6, 3)], "a", 20, 0)[0];
    expect([r.rong, r.cao]).toEqual([6, 2]);
  });
  it("ẩn thì khối dưới nổi lên; hiện lại ở đáy", () => {
    const ds = [o("a", 0, 0, 12, 3), o("b", 0, 3, 12, 3)];
    const d = an(ds, "a");
    expect(vt(d.filter(p => !p.an))).toEqual({ b: [0, 0] });
    expect(vt(hienODay(d, "a"))).toEqual({ b: [0, 0], a: [0, 3] });
  });
});

describe("dichPhim", () => {
  const cot = [o("a", 0, 0, 12, 3), o("b", 0, 3, 12, 2), o("c", 0, 5, 12, 4)];
  it("xuống: đổi với khối liền dưới", () => expect(vt(dichPhim(cot, "a", "xuong"))).toEqual({ b: [0, 0], a: [0, 2], c: [0, 5] }));
  it("lên: đổi với khối liền trên", () => expect(vt(dichPhim(cot, "c", "len"))).toEqual({ a: [0, 0], c: [0, 3], b: [0, 7] }));
  it("trái ở mép: đứng yên", () => expect(vt(dichPhim(cot, "a", "trai"))).toEqual(vt(cot)));
});

describe("hangTai / soHang", () => {
  it("hàng đều", () => {
    expect(hangTai(0, [40, 40, 40], 12, 40)).toBe(0);
    expect(hangTai(30, [40, 40, 40], 12, 40)).toBe(1);
    expect(hangTai(110, [], 12, 40)).toBe(2);
  });
  it("hàng giãn theo nội dung", () => expect(hangTai(150, [40, 200, 40], 12, 40)).toBe(1));
  it("số hàng phủ", () => {
    expect(soHang(144, 0, [], 12, 40)).toBe(3);
    expect(soHang(10, 0, [], 12, 40)).toBe(1);
  });
});
