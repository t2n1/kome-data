import { describe, expect, it } from "vitest";
import { chiaKhuc, thangChung, tyLeThanh } from "./thanh_logic";

describe("tyLeThanh", () => {
  it("tỷ lệ theo thang", () => expect(tyLeThanh(50, 200)).toBe(0.25));
  it("số ÂM (赤伝) → 0, không âm, không lỗi", () => expect(tyLeThanh(-30, 200)).toBe(0));
  it("vượt thang → kẹp 1", () => expect(tyLeThanh(300, 200)).toBe(1));
  it("null / thang 0 → 0", () => {
    expect(tyLeThanh(null, 200)).toBe(0);
    expect(tyLeThanh(10, 0)).toBe(0);
  });
});

describe("thangChung", () => {
  it("lớn nhất của cả thực tế lẫn kỳ so", () =>
    expect(thangChung([{ gia_tri: 10, ss: 40 }, { gia_tri: 30 }])).toBe(40));
  it("toàn số âm / rỗng → 1 (không chia 0)", () => {
    expect(thangChung([{ gia_tri: -5 }])).toBe(1);
    expect(thangChung([])).toBe(1);
  });
});

describe("chiaKhuc", () => {
  it("Σ = 100", () => {
    const p = chiaKhuc([173, 176, 905, 163]);
    expect(p.reduce((s, x) => s + x, 0)).toBeCloseTo(100);
  });
  it("khúc 0 / âm được 0% và không làm lệch khúc khác", () =>
    expect(chiaKhuc([0, 3, -2, 1])).toEqual([0, 75, 0, 25]));
  it("toàn 0 → toàn 0", () => expect(chiaKhuc([0, 0])).toEqual([0, 0]));
});
