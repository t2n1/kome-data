import { describe, expect, it } from "vitest";
import caTho from "../../../tests/du_lieu/squarify_ca.json";
import { squarify } from "./cay_o";

type Ca = { ten: string; gia_tri: number[]; khung: [number, number, number, number]; o: number[][] };
const CA = caTho as unknown as Ca[];

describe("squarify chạy chung file ca với Python", () => {
  for (const ca of CA) it(ca.ten, () => {
    const o = squarify(ca.gia_tri, ...ca.khung).map(r => [r.x, r.y, r.w, r.h]);
    expect(o.length).toBe(ca.o.length);
    o.forEach((r, i) => r.forEach((v, j) => expect(v).toBeCloseTo(ca.o[i][j], 6)));
  });
});
