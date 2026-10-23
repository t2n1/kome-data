import { describe, expect, it } from "vitest";
import { chepAB, chepF, chepGia, demSheet, gioTu, macDinh, md, soSheet, theoNhom, theoSheet, thieuDong, trangSheet, xepMa } from "./chep";
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
  it("theo nhóm, giữ thứ tự của bản gửi (script đã xếp theo điểm)", () => {
    const g = theoNhom([...t.ma, { ma: "AA01", ten: "", nhom: "thuong", ly: "", chon: true }]);
    expect(g.get("uu_tien")!.map(m => m.ma)).toEqual(["BA07"]);
    expect(g.get("thuong")!.map(m => m.ma)).toEqual(["NT01", "AA01"]);
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
  it("ba ô so với sheet và trạng thái từng mã; mã sheet có mà ngoài danh sách vẫn đếm vào bỏ", () => {
    const s = { ...t, tren_sheet: ["DK06", "NT01", "ZZ09"] };
    const c = macDinh(s);
    expect(demSheet(t, c)).toBeNull();
    expect(demSheet(s, c)).toEqual({ giu: 1, them: 1, bo: 2, ngoai: ["ZZ09"] });
    expect(s.ma.map(m => trangSheet(s, c, m))).toEqual(["giu", "them", "bo"]);
    expect(trangSheet(t, c, t.ma[0])).toBeNull();
  });
  it("xếp theo cột số giảm dần, mã không có số xuống cuối, bằng nhau giữ thứ tự gửi", () => {
    const ds = [
      { ma: "A", ten: "", nhom: "thuong" as const, ly: "", chon: true, so: { lai: 100 } },
      { ma: "B", ten: "", nhom: "thuong" as const, ly: "", chon: true },
      { ma: "C", ten: "", nhom: "thuong" as const, ly: "", chon: true, so: { lai: -5 } },
      { ma: "D", ten: "", nhom: "thuong" as const, ly: "", chon: true, so: { lai: 100 } },
      { ma: "E", ten: "", nhom: "thuong" as const, ly: "", chon: true, so: { lai: 900 } },
    ];
    expect(xepMa(ds, "lai").map(m => m.ma)).toEqual(["E", "A", "D", "C", "B"]);
    expect(xepMa(ds, null)).toBe(ds);
  });
});
