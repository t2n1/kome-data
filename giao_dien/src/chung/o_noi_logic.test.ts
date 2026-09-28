import { describe, expect, it } from "vitest";
import { buocCham, viTriNoi } from "./o_noi_logic";

describe("buocCham", () => {
  it("chạm lần 1 (chưa mở) chỉ mở ô nổi", () => expect(buocCham(false, "touch")).toBe("mo"));
  it("chạm lần 2 (đã mở) mới đi", () => expect(buocCham(true, "touch")).toBe("di"));
  it("chuột bấm là đi, dù ô nổi chưa mở", () => {
    expect(buocCham(false, "mouse")).toBe("di");
    expect(buocCham(true, "mouse")).toBe("di");
  });
  it("bút coi như chuột (có rê)", () => expect(buocCham(false, "pen")).toBe("di"));
});

describe("viTriNoi", () => {
  const khung = { w: 375, h: 800 };
  it("mặc định nằm DƯỚI phần tử, căn giữa", () => {
    expect(viTriNoi({ left: 100, top: 100, right: 200, bottom: 120 }, { w: 100, h: 50 }, khung))
      .toEqual({ left: 100, top: 126 });
  });
  it("sát đáy thì lật LÊN trên", () => {
    expect(viTriNoi({ left: 100, top: 760, right: 200, bottom: 780 }, { w: 100, h: 50 }, khung))
      .toEqual({ left: 100, top: 704 });
  });
  it("không tràn mép trái / phải của điện thoại 375 px", () => {
    expect(viTriNoi({ left: 0, top: 100, right: 20, bottom: 120 }, { w: 200, h: 50 }, khung).left).toBe(8);
    expect(viTriNoi({ left: 360, top: 100, right: 375, bottom: 120 }, { w: 200, h: 50 }, khung).left).toBe(167);
  });
  it("ô nổi rộng hơn màn hình thì dính mép trái", () => {
    expect(viTriNoi({ left: 100, top: 100, right: 200, bottom: 120 }, { w: 500, h: 50 }, khung).left).toBe(8);
  });
  it("không chỗ nào vừa thì vẫn nằm dưới (không đẩy lên khỏi mép trên)", () => {
    expect(viTriNoi({ left: 100, top: 20, right: 200, bottom: 40 }, { w: 100, h: 900 }, khung).top).toBe(46);
  });
});
