import { describe, expect, it } from "vitest";
import type { MaGia, OGia } from "./kieu";
import { chuoiLocBg, coCua, docLocBg, giaiO, locBangGia } from "./loc";

const o = (s: Partial<OGia> = {}): OGia => ({ gia: 100, truoc: 100, lech: false, doi: false, duoi: false, bo: false, ...s });
const ma = (m: string, nganh: string, g: Record<string, OGia>[] = [{ "01": o() }], thieu_kg = false): MaGia => ({
  ma: m, ten: "Hàng " + m, nganh, ngung_ban: false, thieu_kg,
  dong: g.map((x, i) => ({ qc: i ? "00" : "02", ten_qc: "", tu: "2026-09-08", tu_truoc: "2026-08-13", gia_von: 50, g: x })) });

describe("cờ của mã = có ô nào mang cờ đó", () => {
  it("gộp từ mọi quy cách", () => {
    expect([...coCua(ma("A", "x", [{ "01": o() }, { "01": o({ doi: true, duoi: true }) }]))].sort()).toEqual(["doi", "duoi"]);
  });
  it("bậc bị bỏ vẫn là 'đổi' nhưng không làm 'hai cột lệch'", () => {
    expect([...coCua(ma("A", "x", [{ "10": o({ bo: true, doi: true, lech: true, gia: null }), "01": o() }]))]).toEqual(["doi"]);
  });
  it("không dòng nào, hoặc chỉ còn bậc bị bỏ = chưa có giá", () => {
    expect(coCua({ ...ma("A", "x"), dong: [] }).has("chua_co")).toBe(true);
    expect(coCua(ma("A", "x", [{ "10": o({ bo: true, doi: true, gia: null }) }])).has("chua_co")).toBe(true);
    expect(coCua(ma("A", "x")).has("chua_co")).toBe(false);
  });
  it("thiếu kg lấy nguyên cờ máy chủ", () => { expect(coCua(ma("A", "x", undefined, true)).has("thieu_kg")).toBe(true); });
});

describe("lọc và đếm", () => {
  const ds = [ma("A1", "Gạo", [{ "01": o({ doi: true }) }]), ma("A2", "Gạo"), ma("B1", "Mì", [{ "01": o({ doi: true }) }])];
  it("dải cờ đếm theo tìm + ngành, không theo cờ", () => {
    const k = locBangGia(ds, { tim: "", nganh: "Gạo", co: "doi" });
    expect(k.dem_co.doi).toBe(1);
    expect(k.tong_co).toBe(2);
    expect(k.hang.map(m => m.ma)).toEqual(["A1"]);
  });
  it("dải ngành đếm theo tìm + cờ, không theo ngành", () => {
    const k = locBangGia(ds, { tim: "", nganh: "Gạo", co: "doi" });
    expect(Object.fromEntries(k.dem_nganh)).toEqual({ "Gạo": 1, "Mì": 1 });
    expect(k.tong_nganh).toBe(2);
  });
  it("cờ lạ = không lọc", () => { expect(locBangGia(ds, { tim: "", nganh: "", co: "xyz" }).hang).toHaveLength(3); });
  it("tìm không dấu theo mã / tên", () => { expect(locBangGia(ds, { tim: "hang b1", nganh: "", co: "" }).hang.map(m => m.ma)).toEqual(["B1"]); });
  it("URL đi hai chiều", () => {
    const b = { tim: "gao", nganh: "Gạo", co: "duoi" };
    expect(docLocBg("?" + chuoiLocBg(b))).toEqual(b);
    expect(chuoiLocBg({ tim: " ", nganh: "", co: "" })).toBe("");
  });
});

describe("chữ ô nổi", () => {
  const y = (n: number) => "¥" + n, d = (s: string) => s.slice(5);
  it("đổi giá", () => { expect(giaiO(o({ gia: 120, truoc: 100, doi: true }), "2026-09-08", "2026-08-13", y, d)).toBe("¥100 → ¥120 (08-13 → 09-08)"); });
  it("bậc mới", () => { expect(giaiO(o({ truoc: null, doi: true }), "2026-09-08", "2026-08-13", y, d)).toMatch(/^Bậc mới/); });
  it("bậc bị bỏ", () => { expect(giaiO(o({ gia: null, truoc: 90, bo: true, doi: true }), "2026-09-08", "2026-08-13", y, d)).toMatch(/¥90.*không còn/); });
  it("không đổi = không chữ", () => { expect(giaiO(o(), "2026-09-08", "2026-08-13", y, d)).toBe(""); });
});
