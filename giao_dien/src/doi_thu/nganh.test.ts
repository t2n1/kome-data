import { describe, expect, it } from "vitest";
import { tenNganh } from "./nganh";

describe("tenNganh — tên tiếng Việt chỉ để hiển thị", () => {
  it.each([
    ["インスタント食品_VNM", "Mì & ăn liền"], ["冷凍食品_VNM", "Đông lạnh"], ["冷蔵食品_VNM", "Đồ mát"],
    ["調味料_VNM", "Gia vị"], ["食材（常温）＿VNM", "Đồ khô"], ["飲料（アルコール）_VNM", "Bia rượu"],
    ["飲料（アルコール以外）＿VNM", "Nước uống"], ["飲料（アルコール以外）_THA", "Nước uống (Thái)"],
  ])("%s -> %s", (obc, vi) => expect(tenNganh(obc)).toBe(vi));
  it("hậu tố THA, cả gạch thường lẫn gạch toàn chiều", () => {
    expect(tenNganh("調味料＿THA")).toBe("Gia vị (Thái)"); expect(tenNganh("冷凍食品_THA")).toBe("Đông lạnh (Thái)");
  });
  it("rượu không lẫn với nước uống", () => {
    expect(tenNganh("飲料（アルコール）_THA")).toBe("Bia rượu (Thái)");
  });
  it("nhãn nội bộ giữ nguyên", () => {
    for (const s of ["Phí & điều chỉnh", "Hàng tặng (POSM)", "(chưa phân loại)"]) expect(tenNganh(s)).toBe(s);
  });
  it("mã lạ -> nguyên văn; rỗng / null -> (chưa phân loại)", () => {
    expect(tenNganh("雑貨_VNM")).toBe("雑貨_VNM");
    expect(tenNganh(null)).toBe("(chưa phân loại)"); expect(tenNganh("")).toBe("(chưa phân loại)"); expect(tenNganh(undefined)).toBe("(chưa phân loại)");
  });
});
