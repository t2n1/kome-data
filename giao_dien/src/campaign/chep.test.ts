import { describe, expect, it } from "vitest";
import { chepAB, chepF, chepGia, gioTu, macDinh, md, soSheet, theoNhom, theoSheet, thieuDong } from "./chep";
import type { TuanKeHoach } from "./kieu";

const t: TuanKeHoach = {
  tu: "2026-11-27", den: "2026-12-03", tab: "2026/12", tuan_so: 1, ky: "11/27 ~ 12/3",
  ma: [
    { ma: "NT01", ten: "", nhom: "thuong", ly: "", chon: true },
    { ma: "BA07", ten: "", nhom: "uu_tien", ly: "", chon: true },
    { ma: "DK06", ten: "", nhom: "nghi", ly: "", chon: false },
  ],
};

describe("chuỗi chép", () => {
  it("mặc định = mã được chọn sẵn", () => expect([...macDinh(t)].sort()).toEqual(["BA07", "NT01"]));
  it("A–B và F cùng thứ tự, mỗi mã một dòng", () => {
    const c = macDinh(t);
    expect(chepAB(t, c)).toBe("1\t11/27 ~ 12/3\n1\t11/27 ~ 12/3");
    expect(chepF(c)).toBe("BA07\nNT01");
  });
  it("値段管理 giữ đúng thứ tự dòng, ô trống cho mã không chạy và dòng trống", () => {
    const c = new Set(["NT01", "DK06"]);
    expect(chepGia(["BA07", "", "DK06", "NT01"], c)).toBe("\n\nDK06\nNT01");
  });
  it("báo mã đã chọn mà 値段管理 không có dòng", () => expect(thieuDong(["BA07"], macDinh(t))).toEqual(["NT01"]));
  it("theo nhóm, xếp mã", () => {
    const g = theoNhom(t.ma);
    expect(g.get("uu_tien")!.map(m => m.ma)).toEqual(["BA07"]);
    expect(g.get("loai")).toEqual([]);
  });
  it("ngày ngắn và tuổi bản soát", () => {
    expect(md("2026-01-05")).toBe("1/5");
    expect(md(null)).toBe("—");
    expect(gioTu("2026-10-23T00:00:00+09:00", new Date("2026-10-24T12:00:00+09:00"))).toBe(36);
  });
  it("so với sheet: thêm / bỏ; tuần chưa có trên sheet → null", () => {
    expect(soSheet(t, macDinh(t))).toBeNull();
    const s = { ...t, tren_sheet: ["DK06", "NT01", "ZZ09"] };
    expect(soSheet(s, macDinh(s))).toEqual({ them: ["BA07"], bo: ["DK06", "ZZ09"] });
    expect([...theoSheet(s)].sort()).toEqual(["DK06", "NT01", "ZZ09"]);
  });
});
