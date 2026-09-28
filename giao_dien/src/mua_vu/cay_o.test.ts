import { describe, expect, it } from "vitest";
import caTho from "../../../tests/du_lieu/squarify_ca.json";
import { squarify, xep } from "./cay_o";

type Ca = { ten: string; gia_tri: number[]; khung: [number, number, number, number]; o: number[][] };
const CA = caTho as unknown as Ca[];

describe("squarify chạy chung file ca với Python", () => {
  for (const ca of CA) it(ca.ten, () => {
    const o = squarify(ca.gia_tri, ...ca.khung).map(r => [r.x, r.y, r.w, r.h]);
    expect(o.length).toBe(ca.o.length);
    o.forEach((r, i) => r.forEach((v, j) => expect(v).toBeCloseTo(ca.o[i][j], 6)));
  });
});

describe("xep hai tầng ngành → mã", () => {
  // mã: 0,1 ngành 0 · 2 ngành 1 · 3 ngành 1 (âm) · 4 ngành 2 (tắt) · 5 phí · 6 tặng
  const p = {
    gia_tri: [60, 20, 30, -5, 40, 7, 3], nganh_cua: [0, 0, 1, 1, 2, -1, -1],
    thu_tu_nganh: [1, 0, 2], tat: new Set([2]), phi: 5, tang: 6, w: 400, h: 300,
  };
  const r = xep(p);
  it("đối soát: vẽ + không vẽ = tổng", () => {
    const ve = r.nganh.reduce((s, n) => s + n.v, 0);
    const kv = r.khong_ve;
    expect(ve + kv.phi + kv.tang + kv.am + kv.tat).toBe(r.tong);
    expect(r.tong).toBe(155);
  });
  it("mã ≤ 0 vào khong_ve.am, ngành tắt vào khong_ve.tat, mã giả vào phi/tang", () => {
    expect(r.khong_ve).toEqual({ phi: 7, tang: 3, am: -5, so_am: 1, tat: 40 });
  });
  it("thứ tự ngành cố định theo thu_tu_nganh, không theo giá trị cửa sổ", () => {
    expect(r.nganh.map(n => n.n)).toEqual([1, 0]);
  });
  it("mã trong ngành xếp giảm dần, diện tích tỷ lệ giá trị", () => {
    const n0 = r.nganh.find(n => n.n === 0)!;
    expect(n0.ma.map(m => m.m)).toEqual([0, 1]);
    const dt = (o: { w: number; h: number }) => o.w * o.h;
    expect(dt(n0.ma[0]) / dt(n0.ma[1])).toBeCloseTo(3, 1);
  });
  it("mọi ngành tắt / rỗng → không ô nào, không nổ", () => {
    const r2 = xep({ ...p, tat: new Set([0, 1, 2]) });
    expect(r2.nganh).toEqual([]);
    expect(r2.khong_ve.tat).toBe(150);
  });
});
