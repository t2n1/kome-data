import { describe, expect, it } from "vitest";
import { docUrl, vietUrl, type TrangThaiUrl } from "./url";

const MAC_DINH: TrangThaiUrl = { tab: "tom_tat", ben: "", nganh: "", sp: [], sl: "1", xem: "cot", gk: "chuan", cung: false, phi: false };

describe("docUrl", () => {
  it("rỗng -> mặc định", () => expect(docUrl("")).toEqual(MAC_DINH));
  it("tab lạ và tong_quan cũ -> tom_tat", () => {
    expect(docUrl("?tab=xyz").tab).toBe("tom_tat"); expect(docUrl("?tab=tong_quan").tab).toBe("tom_tat");
  });
  it("mọi tab hợp lệ", () => {
    for (const t of ["tom_tat", "so_sanh", "ben", "tin", "giao_hang", "duyet", "nhom", "lech"]) expect(docUrl(`?tab=${t}`).tab).toBe(t);
  });
  it("sp tách dấu phẩy, bỏ rỗng, tối đa 8", () => {
    expect(docUrl("?sp=a,,b,").sp).toEqual(["a", "b"]);
    expect(docUrl("?sp=1,2,3,4,5,6,7,8,9,10").sp).toEqual(["1", "2", "3", "4", "5", "6", "7", "8"]);
  });
  it("giá trị không hợp lệ rơi về mặc định", () => {
    const t = docUrl("?sl=7&xem=lung");
    expect(t.sl).toBe("1"); expect(t.xem).toBe("cot"); expect(t.gk).toBe("chuan");
  });
  it("phi: chỉ ?phi=1 là bật", () => {
    expect(docUrl("?phi=1").phi).toBe(true); expect(docUrl("?phi=0").phi).toBe(false); expect(docUrl("?phi=co").phi).toBe(false);
  });
  it("sl / xem / cung / ben / nganh", () => {
    expect(docUrl("?sl=pallet&xem=nhiet&cung=1&ben=ABC&nganh=%E8%AA%BF%E5%91%B3%E6%96%99_VNM")).toMatchObject(
      { sl: "pallet", xem: "nhiet", cung: true, ben: "ABC", nganh: "調味料_VNM" });
  });
});

describe("vietUrl", () => {
  it("mặc định -> không tham số", () => expect(vietUrl(MAC_DINH, "")).toBe(""));
  it("bỏ giá trị mặc định, giữ khoảng xem", () => {
    expect(vietUrl(MAC_DINH, "?thang=2026-08&tab=duyet&sl=5")).toBe("?thang=2026-08");
  });
  it("khứ hồi", () => {
    const t: TrangThaiUrl = { tab: "so_sanh", ben: "X", nganh: "調味料_VNM", sp: ["a", "b"], sl: "10", xem: "nhiet", gk: "km", cung: true, phi: true };
    expect(docUrl(vietUrl(t, "?thang=2026-08"))).toEqual(t);
    expect(new URLSearchParams(vietUrl(t, "?thang=2026-08")).get("thang")).toBe("2026-08");
  });
  it("phi tắt không in, bật in ?phi=1", () => {
    expect(vietUrl({ ...MAC_DINH, phi: true }, "")).toBe("?phi=1");
    expect(vietUrl({ ...MAC_DINH, phi: false }, "?phi=1")).toBe("");
  });
  it("sp viết dấu phẩy trần", () => {
    expect(vietUrl({ ...MAC_DINH, sp: ["a", "b"] }, "")).toBe("?sp=a,b");
  });
  it("giữ tham số lạ (nhom, ss_thang…)", () => {
    expect(vietUrl({ ...MAC_DINH, tab: "tin" }, "?nhom=n%3A3&ss=truoc")).toBe("?nhom=n%3A3&ss=truoc&tab=tin");
  });
});
