import { describe, expect, it } from "vitest";
import { banKinh, mienHan, xHan } from "./han_logic";

describe("mienHan", () => {
  it("luôn phủ ít nhất −15 → 90 ngày", () => expect(mienHan([10, 40])).toEqual({ tu: -15, den: 90 }));
  it("giãn theo lô quá hạn lâu / còn xa", () => expect(mienHan([-40, 150])).toEqual({ tu: -40, den: 150 }));
  it("rỗng vẫn có miền", () => expect(mienHan([])).toEqual({ tu: -15, den: 90 }));
});

describe("xHan", () => {
  it("tuyến tính trong miền, kẹp 0..1", () => {
    const m = { tu: -10, den: 90 };
    expect(xHan(-10, m)).toBe(0);
    expect(xHan(40, m)).toBe(0.5);
    expect(xHan(200, m)).toBe(1);
  });
});

describe("banKinh", () => {
  it("4 px cho 0, 12 px cho lớn nhất, ∝ căn bậc hai", () => {
    expect(banKinh(0, 100)).toBe(4);
    expect(banKinh(100, 100)).toBe(12);
    expect(banKinh(25, 100)).toBe(8);
  });
  it("giá trị âm / max 0 → 4", () => { expect(banKinh(-5, 100)).toBe(4); expect(banKinh(5, 0)).toBe(4); });
});
