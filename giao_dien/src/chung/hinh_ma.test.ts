import { afterEach, describe, expect, it } from "vitest";
import { chuDau, hinhCua } from "./hinh_ma";

const g = globalThis as { window?: unknown };
afterEach(() => { delete g.window; });

describe("hinhCua", () => {
  it("có hình → URL", () => {
    expect(hinhCua("AO02", { AO02: "https://x/a.jpg" })).toBe("https://x/a.jpg");
  });
  it("không có / mã rỗng → null", () => {
    expect(hinhCua("ZZ", { AO02: "https://x/a.jpg" })).toBeNull();
    expect(hinhCua(null, { AO02: "https://x/a.jpg" })).toBeNull();
    expect(hinhCua("", {})).toBeNull();
  });
  it("mã có số 0 đầu giữ nguyên chữ — không khớp bản bỏ số 0", () => {
    const bd = { "000123": "https://x/1.jpg" };
    expect(hinhCua("000123", bd)).toBe("https://x/1.jpg");
    expect(hinhCua("123", bd)).toBeNull();
  });
  it("không phải https → null (phòng thủ lần hai)", () => {
    expect(hinhCua("A", { A: "javascript:alert(1)" })).toBeNull();
    expect(hinhCua("A", { A: "http://x/a.jpg" })).toBeNull();
  });
  it("mặc định đọc window.__KOME__.hinh; thiếu window → null", () => {
    expect(hinhCua("A")).toBeNull();
    g.window = { __KOME__: { hinh: { A: "https://x/a.jpg" } } };
    expect(hinhCua("A")).toBe("https://x/a.jpg");
  });
});

describe("chuDau", () => {
  it("chữ cái đầu của tên, rơi về mã", () => {
    expect(chuDau("  bánh tráng", "X1")).toBe("B");
    expect(chuDau(null, "x1")).toBe("X");
    expect(chuDau("", "")).toBe("?");
  });
});
