import { describe, expect, it } from "vitest";
import { cauNhip, dongMuaLai, laCanGoi, tabTuHash, TAB_HO_SO } from "./ho_so_logic";
import type { LichMa } from "./kieu";

const lm = (ma: string, con: number): LichMa => ({ ma, ten: "T" + ma, du_kien: "2026-09-01", con, nhip: 14,
  lan_cuoi: "2026-08-01", doanh_thu: 1000, tb_moi_lan: null });

describe("tabTuHash", () => {
  it("hash cũ của bản 5 tab rơi về Mặt hàng", () => {
    expect(tabTuHash("#tong_quan", true)).toBe("mat_hang");
    expect(tabTuHash("#san_pham", true)).toBe("mat_hang");
  });
  it("hash hợp lệ giữ nguyên, hash lạ về Mặt hàng", () => {
    expect(tabTuHash("#ho_so", true)).toBe("ho_so");
    expect(tabTuHash("#don_hang", false)).toBe("don_hang");
    expect(tabTuHash("#xyz", true)).toBe("mat_hang");
    expect(tabTuHash("", true)).toBe("mat_hang");
  });
  it("tab Công nợ tắt thì #cong_no về Mặt hàng", () => {
    expect(tabTuHash("#cong_no", false)).toBe("mat_hang");
    expect(tabTuHash("#cong_no", true)).toBe("cong_no");
  });
  it("đủ 4 tab đúng thứ tự", () => {
    expect(TAB_HO_SO.map(t => t[0])).toEqual(["mat_hang", "don_hang", "cong_no", "ho_so"]);
  });
});

describe("cauNhip", () => {
  it("giữ nguyên văn bốn bậc cũ của khối Nhịp mua", () => {
    expect(cauNhip(null)).toBe("Chưa đủ 3 lần mua để có nhịp — không đoán.");
    expect(cauNhip(0.5)).toBe("Vẫn trong nhịp mua thường lệ.");
    expect(cauNhip(1.5)).toBe("Đã quá ngày mua thường lệ — gọi trước khi trễ hẳn.");
    expect(cauNhip(3)).toBe("Im lặng 2–4× nhịp: quá hạn mua lại.");
    expect(cauNhip(4)).toBe("Im lặng ≥ 4× nhịp: đang mất khách.");
  });
});

describe("dongMuaLai", () => {
  it("phân mức: quá (<0), sắp (0..7), xa (>7) và in nhãn", () => {
    const r = dongMuaLai([lm("a", -12), lm("b", 0), lm("c", 7), lm("d", 20)]);
    expect(r.map(x => x.muc)).toEqual(["qua", "sap", "sap", "xa"]);
    expect(r.map(x => x.nhan)).toEqual(["quá 12 ngày", "hôm nay", "còn 7 ngày", "còn 20 ngày"]);
  });
  it("giữ thứ tự máy chủ gửi (lich đã sắp theo ngày)", () => {
    expect(dongMuaLai([lm("x", 3), lm("y", -1)]).map(d => d.ma)).toEqual(["x", "y"]);
  });
});

describe("laCanGoi", () => {
  it("đọc màu trạng thái có sẵn (MAU_TT) và nhãn tháng, không tự định nghĩa nhóm", () => {
    expect(laCanGoi("canh", "da_mua")).toBe(true);
    expect(laCanGoi("do", undefined)).toBe(true);
    expect(laCanGoi("ok", "tre")).toBe(true);
    expect(laCanGoi("ok", "da_mua")).toBe(false);
    expect(laCanGoi(undefined, undefined)).toBe(false);
  });
});
