import { describe, expect, it } from "vitest";
import { chiaPhanTram, chiaTheoTrongSo, keoVach, phanTramTheo, trongSoMua } from "./ngan_sach_logic";

const cong = (a: number[]) => a.reduce((s, v) => s + v, 0);

describe("chiaTheoTrongSo", () => {
  it("cộng lại ĐÚNG bằng tổng đã gõ (phần dư dồn vào phần lớn nhất)", () => {
    for (const tong of [1_560_000_000, 1_000_000_001, 7, 0]) {
      const ra = chiaTheoTrongSo(tong, [3, 1, 1, 2, 5, 1, 1, 1, 1, 1, 1, 9]);
      expect(cong(ra)).toBe(tong);
      expect(ra.every(v => Number.isInteger(v))).toBe(true);
    }
  });
  it("trọng số rỗng / ≤ 0 -> chia đều", () => {
    expect(chiaTheoTrongSo(12, [0, 0, 0, 0])).toEqual([3, 3, 3, 3]);
    expect(chiaTheoTrongSo(10, [-1, NaN, 0])).toEqual([4, 3, 3]);
  });
});

describe("trongSoMua", () => {
  it("tháng không có năm trước lấy TRUNG BÌNH, không thành 0", () => {
    expect(trongSoMua([100, null, 300])).toEqual([100, 200, 300]);
  });
  it("năm trước âm (赤伝) coi như 0; không có số nào -> đều", () => {
    expect(trongSoMua([-50, 50])).toEqual([0, 50]);
    expect(trongSoMua([null, null])).toEqual([1, 1]);
  });
});

describe("chiaPhanTram", () => {
  it("Σ% = 100 -> Σ phần = tổng tháng đúng từng yên", () => {
    const ra = chiaPhanTram(130_000_001, [42, 33, 25]);
    expect(cong(ra)).toBe(130_000_001);
  });
  it("Σ% < 100 -> phần chưa chia KHÔNG giao cho ai (ô còn)", () => {
    const ra = chiaPhanTram(1_000_000, [40, 30, 25]);
    expect(cong(ra)).toBe(950_000);
    expect(ra).toEqual([400_000, 300_000, 250_000]);
  });
  it("không ai có % -> mọi người 0", () => {
    expect(chiaPhanTram(100, [0, 0])).toEqual([0, 0]);
  });
});

describe("phanTramTheo / keoVach", () => {
  it("% theo năm trước là số nguyên, Σ = 100", () => {
    const pt = phanTramTheo([6.6e8, 5.1e8, 3.1e8]);
    expect(cong(pt)).toBe(100);
    expect(pt.every(v => Number.isInteger(v))).toBe(true);
    expect(phanTramTheo([0, 0, 0])).toEqual([34, 33, 33]);
  });
  it("kéo vạch dời % giữa hai người kề nhau, tổng không đổi, không ai âm", () => {
    expect(keoVach([40, 30, 30], 0, 5)).toEqual([45, 25, 30]);
    expect(keoVach([40, 30, 30], 1, -50)).toEqual([40, 0, 60]);
    expect(keoVach([40, 30, 30], 0, 99)).toEqual([70, 0, 30]);
  });
});
