import { describe, expect, it } from "vitest";
import { LuyKe, type DuLieuMV } from "./du_lieu";
import { bac, bangNhiet, cungThangNamTruoc, thangCaoDiem, thangCuaKy, xepHang } from "./nhiet";

const di = (iso: string, dau = "2025-03-15") =>
  Math.round((Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) - Date.UTC(+dau.slice(0, 4), +dau.slice(5, 7) - 1, +dau.slice(8, 10))) / 864e5);

describe("thangCuaKy", () => {
  it("tháng đầu / cuối dở dang được đánh dấu, a/b kẹp vào dải dữ liệu", () => {
    const t = thangCuaKy("2025-03-15", "2025-06-10");
    expect(t.map(x => x.thang)).toEqual(["2025-03", "2025-04", "2025-05", "2025-06"]);
    expect(t.map(x => x.do_dang)).toEqual([true, false, false, true]);
    expect(t[0]).toMatchObject({ a: 0, b: di("2025-03-31") });
    expect(t[1]).toMatchObject({ a: di("2025-04-01"), b: di("2025-04-30") });
    expect(t[3]).toMatchObject({ a: di("2025-06-01"), b: di("2025-06-10") });
  });
  it("mùng 1 và ngày cuối tháng → không dở dang; qua năm đúng", () => {
    const t = thangCuaKy("2025-11-01", "2026-02-28");
    expect(t.map(x => x.thang)).toEqual(["2025-11", "2025-12", "2026-01", "2026-02"]);
    expect(t.every(x => !x.do_dang)).toBe(true);
  });
  it("ngày cuối tháng 2 năm nhuận", () => {
    expect(thangCuaKy("2028-02-01", "2028-02-29")[0].do_dang).toBe(false);
    expect(thangCuaKy("2028-02-01", "2028-02-28")[0].do_dang).toBe(true);
  });
});

describe("bac", () => {
  it("≤ 0 hoặc mẫu số ≤ 0 → 0", () => {
    expect(bac(0, 10)).toBe(0); expect(bac(-5, 10)).toBe(0); expect(bac(5, 0)).toBe(0); expect(bac(5, -1)).toBe(0);
  });
  it("ngưỡng đều 0.2", () => {
    expect(bac(0.001, 10)).toBe(1); expect(bac(2, 10)).toBe(1); expect(bac(2.01, 10)).toBe(2);
    expect(bac(6, 10)).toBe(3); expect(bac(8, 10)).toBe(4); expect(bac(8.01, 10)).toBe(5);
  });
  it("đúng bằng max → 5, vượt max vẫn 5", () => { expect(bac(10, 10)).toBe(5); expect(bac(30, 10)).toBe(5); });
});

// Dữ liệu 2025-03-15 → 2025-06-10, hai mã.
const DL: DuLieuMV = {
  ngay_dau: "2025-03-15", ngay_cuoi: "2025-06-10",
  ma: [{ ma: "A", ten: "A", nganh: "X", an: false }, { ma: "B", ten: "B", nganh: "X", an: false }],
  nganh: ["X"],
  dong: {
    i: [0, 0, 0, 0, 1, 1],
    d: [0, di("2025-04-03"), di("2025-05-20"), di("2025-06-10"), di("2025-04-30"), di("2025-05-01")],
    dt: [900, 100, 300, 50, -40, 70], lg: [1, 1, 1, 1, 1, 1], sl: [1, 1, 1, 1, 1, 1],
  },
  phi: null, tang: null,
};

describe("bangNhiet", () => {
  const L = new LuyKe(DL);
  const t = thangCuaKy(DL.ngay_dau!, DL.ngay_cuoi!);
  const g = bangNhiet(L, "dt", t, [0, 1]);
  it("mỗi ô = tổng các ngày của tháng", () => {
    expect(Array.from(g.slice(0, 4))).toEqual([900, 100, 300, 50]);
    expect(Array.from(g.slice(4, 8))).toEqual([0, -40, 70, 0]);   // 赤伝 giữ số âm
  });
  it("đối soát: tổng các cột của một mã = tổng cả kỳ", () => {
    for (const [h, m] of [[0, 0], [1, 1]]) {
      const s = Array.from(g.slice(h * 4, h * 4 + 4)).reduce((a, b) => a + b, 0);
      expect(s).toBe(L.tong("dt", m, 0, L.so_ngay - 1));
    }
  });
  it("cao điểm bỏ cột dở dang (tháng 3 có 900 nhưng dở dang)", () => {
    expect(thangCaoDiem(g.subarray(0, 4), t)).toBe(5);
  });
  it("không có giá trị dương ở tháng trọn → null", () => {
    expect(thangCaoDiem(new Float64Array([5, 0, -1, 9]), t)).toBeNull();
  });
  it("cao điểm so TRUNG BÌNH mỗi năm của cùng tháng lịch, không so tổng", () => {
    const t2 = thangCuaKy("2025-01-01", "2026-02-28");   // 14 tháng trọn: T1, T2 hai lần
    const r = new Float64Array(14); r[0] = 5; r[12] = 5; r[6] = 8;   // T1 tổng 10 nhưng TB 5 < T7 8
    expect(thangCaoDiem(r, t2)).toBe(7);
    r[12] = 13;                                                       // T1 TB 9 > 8
    expect(thangCaoDiem(r, t2)).toBe(1);
  });
});

describe("xepHang", () => {
  const t = thangCuaKy("2025-01-01", "2025-12-31");
  const hang = (thang: number, v: number) => { const r = new Float64Array(12); r[thang - 1] = v; return r; };
  const rows = [hang(1, 50), hang(3, 10), hang(12, 99), hang(3, 20), new Float64Array(12), hang(2, 1)];
  const g = new Float64Array(rows.flatMap(r => Array.from(r)));
  it("cao điểm: bắt đầu từ tháng 3 (3…12, 1, 2), cùng tháng tổng giảm dần, null cuối", () => {
    expect(xepHang(g, 12, t, "cao_diem")).toEqual([3, 1, 2, 0, 5, 4]);
  });
  it("tổng giảm dần", () => expect(xepHang(g, 12, t, "tong")).toEqual([2, 0, 3, 1, 5, 4]));
});

describe("cungThangNamTruoc", () => {
  it("tháng đầu của dữ liệu → không có", () => {
    const t = thangCuaKy("2025-03-01", "2026-04-30");
    expect(cungThangNamTruoc(t, 0, "2025-03-01")).toBeNull();
  });
  it("tháng trọn → cột cùng tháng năm trước", () => {
    const t = thangCuaKy("2025-03-01", "2026-04-30");
    const k = t.findIndex(x => x.thang === "2026-03");
    expect(cungThangNamTruoc(t, k, "2025-03-01")).toEqual({ a: t[0].a, b: t[0].b, cung_dai_ngay: false });
  });
  it("năm trước là tháng dở dang → không có", () => {
    const t = thangCuaKy("2025-03-15", "2026-04-30");
    const k = t.findIndex(x => x.thang === "2026-03");
    expect(cungThangNamTruoc(t, k, "2025-03-15")).toBeNull();
  });
  it("tháng hiện tại dở dang → cùng DẢI NGÀY năm trước", () => {
    const t = thangCuaKy("2025-03-01", "2026-04-10");
    const k = t.length - 1;
    const r = cungThangNamTruoc(t, k, "2025-03-01")!;
    expect(r.cung_dai_ngay).toBe(true);
    expect(r.a).toBe(di("2025-04-01", "2025-03-01"));
    expect(r.b).toBe(di("2025-04-10", "2025-03-01"));
  });
});

import { buocPhim, catTen } from "./nhiet";

describe("buocPhim (roving focus)", () => {
  it("mũi tên đi một ô và kẹp ở mép", () => {
    expect(buocPhim("ArrowRight", 2, 3, 10, 5)).toEqual([2, 4]);
    expect(buocPhim("ArrowRight", 2, 4, 10, 5)).toEqual([2, 4]);
    expect(buocPhim("ArrowLeft", 2, 0, 10, 5)).toEqual([2, 0]);
    expect(buocPhim("ArrowUp", 0, 1, 10, 5)).toEqual([0, 1]);
    expect(buocPhim("ArrowDown", 9, 1, 10, 5)).toEqual([9, 1]);
  });
  it("Home/End = hai đầu hàng; PageUp/PageDown = ±10 hàng", () => {
    expect(buocPhim("Home", 4, 3, 10, 5)).toEqual([4, 0]);
    expect(buocPhim("End", 4, 0, 10, 5)).toEqual([4, 4]);
    expect(buocPhim("PageDown", 4, 2, 30, 5)).toEqual([14, 2]);
    expect(buocPhim("PageDown", 25, 2, 30, 5)).toEqual([29, 2]);
    expect(buocPhim("PageUp", 4, 2, 30, 5)).toEqual([0, 2]);
  });
  it("phím khác / lưới rỗng → null; ô cũ ngoài lưới bị kẹp lại", () => {
    expect(buocPhim("Enter", 0, 0, 10, 5)).toBeNull();
    expect(buocPhim("ArrowDown", 0, 0, 0, 5)).toBeNull();
    expect(buocPhim("ArrowLeft", 50, 9, 10, 5)).toEqual([9, 4]);
  });
});

describe("catTen", () => {
  it("tên vừa thì giữ nguyên, dài thì kết thúc bằng …", () => {
    expect(catTen("Ngo nep", 10)).toBe("Ngo nep");
    expect(catTen("Banh dua nuong dang tui", 10)).toBe("Banh dua …");
  });
  it("chữ toàn khổ tính ≈ 1,7 chữ Latin", () => {
    const t = catTen("※終売※Banh dua nuong", 10);
    expect(t.endsWith("…")).toBe(true);
    expect(t).toBe("※終売※Ba…");   // 4 × 1,7 + 2 = 8,8 ≤ 10 − 1 (chỗ cho "…")
  });
});
