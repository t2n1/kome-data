import { describe, expect, it } from "vitest";
import { demTheoTag, sapViec, tenViec } from "./viec_logic";

describe("tenViec", () => {
  it("lấy tên khách ra khỏi câu gọi", () => {
    expect(tenViec("Gọi MANH NGA合同会社 — im 53 ngày")).toBe("MANH NGA合同会社");
    expect(tenViec("Gọi AMILY — mua đều 3/3 tháng, tháng này chưa có đơn")).toBe("AMILY");
  });
  it("câu không phải gọi khách giữ nguyên", () =>
    expect(tenViec("Chưa nạp 得意先全情報 hôm nay")).toBe("Chưa nạp 得意先全情報 hôm nay"));
  it("hẹn gọi lại — có ghi chú", () =>
    expect(tenViec("Gọi lại 山田商店 — báo giá mới")).toBe("山田商店"));
  it("hẹn gọi lại — không ghi chú", () =>
    expect(tenViec("Gọi lại 山田商店")).toBe("山田商店"));
});

describe("sapViec", () => {
  it("gấp trước, cảnh sau, thường cuối — giữ thứ tự trong cùng mức", () => {
    const v = [{ muc: "thuong", tag: "a", chu: "1" }, { muc: "gap", tag: "b", chu: "2" },
      { muc: "canh", tag: "c", chu: "3" }, { muc: "gap", tag: "b", chu: "4" }] as const;
    expect(sapViec([...v]).map(x => x.chu)).toEqual(["2", "4", "3", "1"]);
  });
});

describe("demTheoTag", () => {
  it("đếm theo tag, thứ tự xuất hiện đầu tiên", () => {
    const v = [{ muc: "canh", tag: "Quá hạn", chu: "1" }, { muc: "gap", tag: "Lâu không mua", chu: "2" },
      { muc: "canh", tag: "Quá hạn", chu: "3" }] as const;
    expect(demTheoTag([...v])).toEqual([{ tag: "Quá hạn", muc: "canh", dem: 2 }, { tag: "Lâu không mua", muc: "gap", dem: 1 }]);
  });
});
