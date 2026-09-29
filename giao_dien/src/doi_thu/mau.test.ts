import { describe, expect, it } from "vitest";
import { LECH_NGANG, NGAY_CU, mauKomeSoTT, mauLech, phanTram } from "./mau";

describe("luật màu: đỏ = bất lợi cho KOME", () => {
  it("hằng số", () => { expect(LECH_NGANG).toBe(5); expect(NGAY_CU).toBe(60); });
  it("đối thủ rẻ hơn KOME hơn 5% -> đỏ", () => { expect(mauLech(-6)).toBe("do"); expect(mauLech(-40)).toBe("do"); });
  it("đối thủ đắt hơn KOME hơn 5% -> xanh", () => { expect(mauLech(6)).toBe("xanh"); expect(mauLech(30)).toBe("xanh"); });
  it("đúng ±5% là ngang (xám)", () => { expect(mauLech(5)).toBe("xam"); expect(mauLech(-5)).toBe("xam"); expect(mauLech(0)).toBe("xam"); });
  it("không biết -> xám, không đỏ", () => { expect(mauLech(null)).toBe("xam"); expect(mauLech(undefined)).toBe("xam"); });
  it("KOME so trung vị ngược chiều: KOME đắt -> đỏ, KOME rẻ -> xanh", () => {
    expect(mauKomeSoTT(6)).toBe("do"); expect(mauKomeSoTT(-6)).toBe("xanh");
    expect(mauKomeSoTT(5)).toBe("xam"); expect(mauKomeSoTT(-5)).toBe("xam"); expect(mauKomeSoTT(null)).toBe("xam");
  });
});

describe("phanTram", () => {
  it("% của giá so với gốc, làm tròn", () => { expect(phanTram(90, 100)).toBe(-10); expect(phanTram(105, 100)).toBe(5); expect(phanTram(1, 3)).toBe(-67); });
  it("thiếu giá hoặc gốc 0/null -> null, không NaN", () => {
    expect(phanTram(null, 100)).toBeNull(); expect(phanTram(100, null)).toBeNull();
    expect(phanTram(100, 0)).toBeNull(); expect(phanTram(undefined, undefined)).toBeNull();
  });
});
