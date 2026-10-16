import { describe, expect, it } from "vitest";
import { catXem } from "./XemThem";

describe("catXem", () => {
  it("cắt n dòng đầu, giữ thứ tự, đếm phần ẩn", () => {
    expect(catXem([1, 2, 3, 4, 5], 3, false)).toEqual({ hien: [1, 2, 3], an: 2 });
  });
  it("mở thì hiện hết", () => {
    expect(catXem([1, 2, 3, 4, 5], 3, true)).toEqual({ hien: [1, 2, 3, 4, 5], an: 0 });
  });
  it("không quá n thì không ẩn gì", () => {
    expect(catXem([1, 2], 3, false)).toEqual({ hien: [1, 2], an: 0 });
  });
});
