import { describe, expect, it } from "vitest";
import { tinhThe, type VaoThe } from "./nguoi_logic";

const vao = (v: Partial<VaoThe>): VaoThe => ({ tt: 0, mt: 1_000, moc: null, cs: null, ss: null, conNgay: true, ...v });

describe("thước của thẻ", () => {
  it("không ai vượt ngân sách: đầy thanh = ngân sách, không vạch ngân sách riêng", () => {
    const t = tinhThe(vao({ tt: 500, cs: 800, moc: 600, ss: 700 })).thanh!;
    expect(t).toEqual({ tt: 50, db: 80, ns: null, nhip: 60, ss: 70 });
  });

  it("kỳ so vượt ngân sách KHÔNG bị kẹp ở mép — thước dài ra, ngân sách là một vạch", () => {
    const t = tinhThe(vao({ mt: 2_000, tt: 1_000, ss: 4_000 })).thanh!;
    expect(t.ss).toBe(100);
    expect(t.ns).toBe(50);
    expect(t.tt).toBe(25);
  });

  it("đã có và dự báo cùng vượt: phần nhạt vẫn dài hơn phần đậm", () => {
    const t = tinhThe(vao({ mt: 1_000, tt: 1_400, cs: 2_000 })).thanh!;
    expect(t.db).toBe(100);
    expect(t.tt).toBe(70);
    expect(t.ns).toBe(50);
  });

  it("kỳ so âm (赤伝) không có chỗ trên thanh", () => {
    expect(tinhThe(vao({ tt: 100, ss: -50 })).thanh!.ss).toBeNull();
  });

  it("chưa đặt hoặc đặt bằng 0: không thanh (không chia cho 0)", () => {
    expect(tinhThe(vao({ mt: null, tt: 100 })).thanh).toBeNull();
    expect(tinhThe(vao({ mt: 0, tt: 100 })).thanh).toBeNull();
  });
});

describe("dòng nhịp", () => {
  it("bằng đúng mức lẽ ra: 'đúng', không phải 'vượt'", () => {
    expect(tinhThe(vao({ tt: 300, moc: 300 })).lech).toEqual({ kieu: "dung", so: 0 });
  });

  it("chưa qua ngày làm việc nào (mốc 0): không in dòng nhịp", () => {
    expect(tinhThe(vao({ tt: 0, moc: 0 })).lech).toBeNull();
  });

  it("tháng đã khép: không in dòng nhịp", () => {
    expect(tinhThe(vao({ tt: 300, moc: 1_000, conNgay: false })).lech).toBeNull();
  });

  it("thiếu / vượt nói bằng tiền", () => {
    expect(tinhThe(vao({ tt: 200, moc: 300 })).lech).toEqual({ kieu: "thieu", so: 100 });
    expect(tinhThe(vao({ tt: 400, moc: 300 })).lech).toEqual({ kieu: "vuot", so: 100 });
  });
});

describe("còn lại so với ngân sách", () => {
  it("ngân sách đặt bằng 0 không bao giờ là 'đã đạt'", () => {
    expect(tinhThe(vao({ mt: 0, tt: 0 })).con).toEqual({ kieu: "ns_khong" });
    expect(tinhThe(vao({ mt: 0, tt: -50 })).con).toEqual({ kieu: "ns_khong" });
  });

  it("thiếu tính cả số âm; bằng = đạt; hơn = vượt kèm số", () => {
    expect(tinhThe(vao({ mt: 1_000, tt: -50 })).con).toEqual({ kieu: "thieu", so: 1_050 });
    expect(tinhThe(vao({ mt: 1_000, tt: 1_000 })).con).toEqual({ kieu: "dat" });
    expect(tinhThe(vao({ mt: 1_000, tt: 1_200 })).con).toEqual({ kieu: "vuot", so: 200 });
  });

  it("chưa đặt: không dòng nào", () => {
    expect(tinhThe(vao({ mt: null, tt: 10 })).con).toBeNull();
  });
});
