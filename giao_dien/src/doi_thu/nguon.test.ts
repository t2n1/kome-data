import { describe, expect, it } from "vitest";
import { CAN_BANG_CHUNG, cacThangCho, lienKetAnToan, nhanThang, thangCua, timTrongDrive } from "./nguon";

describe("lienKetAnToan", () => {
  it("chỉ nhận https://", () => {
    expect(lienKetAnToan("https://drive.google.com/x")).toBe("https://drive.google.com/x");
    for (const x of ["http://a", "javascript:alert(1)", " https://a", "https://a b", "", null, undefined, 5, "HTTPS://a"])
      expect(lienKetAnToan(x)).toBeNull();
  });
});

describe("timTrongDrive", () => {
  it("mã hoá tên file vào ô tìm của Drive", () => {
    expect(timTrongDrive("MENU HANG KHO 82026.pdf"))
      .toBe("https://drive.google.com/drive/search?q=" + encodeURIComponent("MENU HANG KHO 82026.pdf"));
    expect(timTrongDrive("a&b#c.pdf")).toContain("a%26b%23c.pdf");
  });
});

describe("tháng", () => {
  it("thangCua / nhanThang", () => {
    expect(thangCua("2026-08-01")).toBe("2026-08");
    expect(thangCua(null)).toBeNull();
    expect(nhanThang("2026-08")).toBe("Tháng 8/2026");
  });
  it("cacThangCho: khác nhau, mới trước, bỏ null", () => {
    expect(cacThangCho([{ thang_lo: "2026-07-01" }, { thang_lo: null }, { thang_lo: "2026-08-01" }, { thang_lo: "2026-07-01" }]))
      .toEqual(["2026-08", "2026-07"]);
  });
  it("loại nguồn cần bằng chứng", () => {
    expect([...CAN_BANG_CHUNG]).toEqual(["chung_tu", "to_roi"]);
  });
});
