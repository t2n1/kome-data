import { beforeEach, describe, expect, it } from "vitest";
import { datLai, dayVao, doSau, goRa, laDinh } from "./hop_thoai_logic";

beforeEach(datLai);
describe("ngăn xếp hộp thoại", () => {
  it("chỉ hộp trên cùng là đỉnh", () => {
    const a = dayVao(), b = dayVao();
    expect(laDinh(a)).toBe(false); expect(laDinh(b)).toBe(true); expect(doSau()).toBe(2);
  });
  it("đóng hộp trên thì hộp dưới thành đỉnh", () => {
    const a = dayVao(), b = dayVao(); goRa(b);
    expect(laDinh(a)).toBe(true); expect(laDinh(b)).toBe(false);
  });
  it("đóng hộp dưới trước: hộp trên vẫn là đỉnh", () => {
    const a = dayVao(), b = dayVao(); goRa(a);
    expect(laDinh(b)).toBe(true); expect(doSau()).toBe(1);
  });
  it("ngăn xếp rỗng: không ai là đỉnh; gỡ hai lần không hỏng", () => {
    const a = dayVao(); goRa(a); goRa(a);
    expect(laDinh(a)).toBe(false); expect(doSau()).toBe(0);
  });
});
