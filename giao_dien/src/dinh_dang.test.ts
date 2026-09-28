import { describe, expect, it } from "vitest";
import { gon, pc, so, so_luong, thay_doi, yen } from "./dinh_dang";

// Cùng ca với tests/test_dinh_dang.py (bản Python kome/dinh_dang.py).
describe("chuẩn Nhật", () => {
  it("yen phẩy nghìn", () => {
    expect(yen(1234567)).toBe("¥1,234,567");
    expect(yen(-1500)).toBe("−¥1,500");
    expect(so(2080)).toBe("2,080");
  });
  it("gon theo 万/億", () => {
    const ca: [number, string][] = [[8_500, "¥8,500"], [98_000, "¥9.8万"], [100_000, "¥10万"], [11_700_000, "¥1,170万"],
      [99_990_000, "¥9,999万"], [120_000_000, "¥1.2億"], [100_000_000, "¥1億"], [1_880_000_000, "¥18.8億"], [-26_258_617, "−¥2,626万"]];
    for (const [v, ra] of ca) expect(gon(v)).toBe(ra);
  });
  it("thập phân dấu chấm", () => {
    expect(pc(0.629)).toBe("62.9%");
    expect(thay_doi(-0.011)).toBe("▼1.1%");
    expect(so_luong(83.75)).toBe("83.75");
  });
});
