import { describe, expect, it } from "vitest";
import { LuyKe, cuaSo, namTruoc, ngayCua, type DuLieuMV } from "./du_lieu";

const DL: DuLieuMV = {
  ngay_dau: "2025-03-03", ngay_cuoi: "2025-03-10",
  ma: [{ ma: "A", ten: "A", nganh: "X", an: false }, { ma: "B", ten: "B", nganh: "Y", an: false }],
  nganh: ["X", "Y"],
  dong: { i: [0, 0, 1, 0], d: [0, 2, 2, 7], dt: [100, 50, -30, 10], lg: [10, 5, -3, 1], sl: [1.5, 1, -1, 0.25] },
  phi: null, tang: null,
};

describe("LuyKe", () => {
  const L = new LuyKe(DL);
  it("số ngày = ngay_cuoi − ngay_dau + 1", () => expect(L.so_ngay).toBe(8));
  it("tổng cửa sổ = cộng đúng các ngày trong [a, b]", () => {
    expect(L.tong("dt", 0, 0, 7)).toBe(160);
    expect(L.tong("dt", 0, 1, 2)).toBe(50);
    expect(L.tong("dt", 1, 0, 7)).toBe(-30);          // 赤伝 giữ số âm
    expect(L.tong("sl", 0, 0, 7)).toBeCloseTo(2.75);  // số lượng thập phân
  });
  it("a kẹp về 0, b kẹp về so_ngay − 1", () => expect(L.tong("dt", 0, -5, 99)).toBe(160));
  it("tổng theo ngày gồm mọi mã", () => expect(Array.from(L.tongNgay)).toEqual([100, 0, 20, 0, 0, 0, 0, 10]));
});

describe("cửa sổ và năm trước", () => {
  it("ngayCua", () => expect(ngayCua("2025-03-03", 30)).toBe("2025-04-02"));
  it("cửa sổ thiếu ngày đầu", () => expect(cuaSo(5, 30)).toEqual({ a: 0, b: 5, thieu: true }));
  it("cửa sổ đủ", () => expect(cuaSo(40, 30)).toEqual({ a: 11, b: 40, thieu: false }));
  it("năm trước trước dữ liệu → null", () => expect(namTruoc("2025-03-03", 200, 30)).toBeNull());
  it("năm trước cùng ngày lịch", () => {
    // b = 2026-07-15 ⇒ năm trước b' = 2025-07-15
    const b = (Date.UTC(2026, 6, 15) - Date.UTC(2025, 2, 3)) / 864e5;
    const r = namTruoc("2025-03-03", b, 30)!;
    expect(ngayCua("2025-03-03", r.b)).toBe("2025-07-15");
    expect(r.b - r.a + 1).toBe(30);
  });
  it("29/2 lùi về 28/2", () => {
    const b = (Date.UTC(2028, 1, 29) - Date.UTC(2025, 2, 3)) / 864e5;
    expect(ngayCua("2025-03-03", namTruoc("2025-03-03", b, 7)!.b)).toBe("2027-02-28");
  });
});
