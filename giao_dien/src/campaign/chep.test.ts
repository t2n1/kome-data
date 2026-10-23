import { describe, expect, it } from "vitest";
import { chepAB, chepF, chepGia, chepMedama, demSheet, docMuc, medamaTuan, gioTu, macDinh, md, soSheet, theoNhom, theoSheet, thieuDong, trangSheet, xepMa } from "./chep";
import type { TuanKeHoach } from "./kieu";

const t: TuanKeHoach = {
  tu: "2026-11-27", den: "2026-12-03", tab: "2026/12", tuan_so: 1, ky: "11/27 ~ 12/3",
  ma: [
    { ma: "NT01", ten: "", nhom: "thuong", ly: "", chon: true },
    { ma: "BA07", ten: "", nhom: "uu_tien", ly: "", chon: true },
    { ma: "DK06", ten: "", nhom: "nghi", ly: "", chon: false },
  ],
};

describe("目玉商品", () => {
  const m = (ma: string, trang: string, off: number, medama?: number) =>
    ({ ma, ten: "", nhom: "thuong" as const, ly: "", chon: true, so: { trang, off, medama } });
  const t1: TuanKeHoach = { ...t, tu: "2026-10-30", ma: [m("A", "lanh", 0.05, 1), m("B", "kho", 0.06, 2), m("C", "kho", 0.3), m("D", "kho", 0.12, 1), m("E", "kho", 0.079, 3)] };
  const t2: TuanKeHoach = { ...t, tu: "2026-11-06", ma: [m("D", "kho", 0.12, 1), m("F", "kho", 0.1, 2), m("B", "kho", 0.09, 3)] };
  it("tách theo trang, xếp theo hạng, không giới hạn số; mã không phải ứng viên là mã phụ dù giảm sâu", () => {
    const [r] = medamaTuan([t1], { kho: 5, lanh: 5 });
    expect(r.kho.map(x => x.ma)).toEqual(["D", "B", "E"]);
    expect(r.lanh.map(x => x.ma)).toEqual(["A"]);
  });
  it("mức giảm riêng từng trang, so trên %OFF đã làm tròn (7.9% < 8%)", () => {
    const [r] = medamaTuan([t1], { kho: 8, lanh: 6 });
    expect(r.kho.map(x => x.ma)).toEqual(["D"]);
    expect(r.lanh).toEqual([]);
  });
  it("không làm 目玉 hai tuần liền — theo đúng mức đang đặt", () => {
    expect(medamaTuan([t1, t2], { kho: 5, lanh: 5 })[1].kho.map(x => x.ma)).toEqual(["F"]);
    expect(medamaTuan([t1, t2], { kho: 10, lanh: 5 })[1].kho.map(x => x.ma)).toEqual(["F"]);
    expect(medamaTuan([t1, t2], { kho: 7, lanh: 5 })[1].kho.map(x => x.ma)).toEqual(["F", "B"]);
  });
  it("chép mã 目玉 đang chọn của một trang", () => {
    const [r] = medamaTuan([t1], { kho: 5, lanh: 5 });
    expect(chepMedama(r.kho, new Set(["B", "C", "D"]))).toBe("D\nB");
  });
  it("đọc mức đã lưu: hỏng / thiếu / ngoài khoảng → mặc định", () => {
    expect(docMuc(null)).toEqual({ kho: 5, lanh: 5 });
    expect(docMuc("{x")).toEqual({ kho: 5, lanh: 5 });
    expect(docMuc('{"kho":8,"lanh":-1}')).toEqual({ kho: 8, lanh: 5 });
    expect(docMuc("null")).toEqual({ kho: 5, lanh: 5 });
  });
});

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
