import { describe, expect, it } from "vitest";
import { giaoTrong } from "./ho_so_logic";
import type { GiaoHang } from "./kieu";
import { chuanGiao, oBang, phiSoSanh, thanhPhi, truOPhan } from "./giao_hang_logic";

const g = (ma: string, o: Partial<GiaoHang> = {}): GiaoHang => ({ ...giaoTrong(ma, ma), ...o });
const KOME = g("KOME", { bao_ship: false, phi_ship: 500, phi_ship_theo: "don", mien_ship_tu: 20000, phi_daibiki: 330,
  daibiki_tu: 20000, daibiki_sau: 300, phu_phi: {}, thue: "chua", suy: true });
const don = (o = {}) => ({ tien: 15000, thung: 1, vung: "kanto" as const, tra: "daibiki" as const, ...o });

describe("chuanGiao — số về dạng chuỗi ở ranh giới API", () => {
  it("đổi chuỗi số thành số, giữ null / chữ / khong_nhan", () => {
    const raw = { ...g("A"), phi_ship: "605", mien_ship_tu: "20000.00", thung_moi_kien: "2", phi_daibiki: null,
      phu_phi: { hokkaido: "800", okinawa: "khong_nhan" }, ghep_kien: "3–4 loại", sua_cuoi: "12" } as unknown as GiaoHang;
    const c = chuanGiao(raw);
    expect(c.phi_ship).toBe(605); expect(c.mien_ship_tu).toBe(20000); expect(c.thung_moi_kien).toBe(2);
    expect(c.phi_daibiki).toBeNull(); expect(c.phu_phi).toEqual({ hokkaido: 800, okinawa: "khong_nhan" });
    expect(c.ghep_kien).toBe("3–4 loại"); expect(c.sua_cuoi).toBe(12);
  });
  it("chuỗi không phải số → null (không bao giờ NaN / 0)", () => {
    const c = chuanGiao({ ...g("A"), phi_ship: "abc", phu_phi: { tohoku: "?" } } as unknown as GiaoHang);
    expect(c.phi_ship).toBeNull(); expect(c.phu_phi).toEqual({});
  });
});

describe("thanhPhi — biểu đồ 'Khách phải trả thêm'", () => {
  const A = g("A", { bao_ship: false, phi_ship: 605, phi_ship_theo: "thung", mien_ship_tu: 20000, phi_daibiki: 440, phu_phi: { hokkaido: 800 } });
  const B = g("B", { bao_ship: true, phi_daibiki: 330, phu_phi: { okinawa: "khong_nhan" } });
  const C = g("C", { bao_ship: false, phi_ship: null, mien_ship_tu: 20000, phi_daibiki: null, phu_phi: {} });
  it("tính bằng phi_giao.tinh, xếp: không nhận cuối, nhiều '?' sau, rồi tổng tăng", () => {
    const r = thanhPhi([KOME, A, B, C], don());
    expect(r.map(x => x.g.ma_doi_thu)).toEqual(["B", "KOME", "A", "C"]);   // B 330 · KOME 830 · A 1045 · C 2 "?"
    expect(r.find(x => x.kome)!.tong).toBe(830);
    expect(r.find(x => x.g.ma_doi_thu === "C")!.r.chua_ro).toEqual(["ship", "daibiki"]);
    const o = thanhPhi([KOME, A, B, C], don({ vung: "okinawa" }));
    expect(o[o.length - 1].g.ma_doi_thu).toBe("B");
    expect(o[o.length - 1].r.khong_nhan).toBe(true);
  });
  it("lệch so KOME (¥), màu theo DẤU (rẻ hơn = đỏ, đắt hơn = xanh, bằng = xám — không ngưỡng ±5%); không so khi có '?'", () => {
    const r = thanhPhi([KOME, A, B, C], don());
    const b = r.find(x => x.g.ma_doi_thu === "B")!;
    expect(b).toMatchObject({ lech: -500, mau: "do" });           // 330 − 830: rẻ hơn KOME ¥500 (chỉ 3% đơn) — vẫn đỏ
    expect(r.find(x => x.g.ma_doi_thu === "A")).toMatchObject({ lech: 215, mau: "xanh" });
    const D = g("D", { bao_ship: false, phi_ship: 500, phi_ship_theo: "don", mien_ship_tu: 20000, phi_daibiki: 330 });
    expect(thanhPhi([KOME, D], don()).find(x => x.g.ma_doi_thu === "D")).toMatchObject({ lech: 0, mau: "xam" });
    expect(r.find(x => x.g.ma_doi_thu === "C")).toMatchObject({ lech: null, mau: null });
    expect(r.find(x => x.kome)!.lech).toBeNull();
    const k2 = { ...KOME, phi_daibiki: null };
    expect(thanhPhi([k2, B], don()).find(x => x.g.ma_doi_thu === "B")!.lech).toBeNull();
  });
  it("chuyển khoản: không daibiki", () => {
    expect(thanhPhi([KOME], don({ tra: "ck" }))[0].tong).toBe(500);
  });
});

describe("truOPhan — ô '?' mở pop-up đúng ô", () => {
  it("ship / vùng theo vùng đang chọn / daibiki trước và sau ngưỡng", () => {
    expect(truOPhan("ship", KOME, don())).toBe("phi_ship");
    expect(truOPhan("vùng", KOME, don({ vung: "tohoku" }))).toBe("phu_phi.tohoku");
    expect(truOPhan("vùng", KOME, don({ vung: "okinawa" }))).toBe("phu_phi.okinawa");
    expect(truOPhan("daibiki", KOME, don())).toBe("phi_daibiki");
    expect(truOPhan("daibiki", KOME, don({ tien: 25000 }))).toBe("daibiki_sau");
  });
});

describe("oBang — bảng điều kiện", () => {
  it("ô thiếu = null ('?' cam) kèm đúng trường; thuế không rõ = vàng", () => {
    const o = oBang(g("X", { thue: "khong_ro" }), KOME);
    expect(o.map(x => [x.k, x.chu])).toEqual([["phi_ship", null], ["mien_ship_tu", null], ["phu_phi", null],
      ["phi_daibiki", null], ["ghep_kien", null], ["kien_toi_da_kg", null], ["thue", null]]);
    expect(o[6].vang).toBe(true);
  });
  it("bao ship; miễn ship thấp hơn KOME = đỏ; vùng; daibiki có ngưỡng; ghép theo thùng / kiện", () => {
    const o = oBang(g("Y", { bao_ship: true, phi_daibiki: 330, daibiki_tu: 20000, daibiki_sau: 0, thung_moi_kien: 2,
      kien_toi_da_kg: 25, phu_phi: { hokkaido: 1200, okinawa: "khong_nhan" }, thue: "bao" }), KOME);
    expect(o[0]).toMatchObject({ k: "bao_ship", chu: "bao ship (trong giá)" });
    expect(o[1]).toMatchObject({ chu: "—" });
    expect(o[2].chu).toBe("Hokkaido +¥1,200 · Okinawa không nhận");
    expect(o[3].chu).toBe("¥330 (từ ¥20,000: miễn)");
    expect(o[4].chu).toBe("2 thùng / kiện");
    expect(o[5].chu).toBe("25 kg");
    expect(o[6].chu).toBe("đã gồm");
    const z = oBang(g("Z", { bao_ship: false, phi_ship: 605, phi_ship_theo: "thung", mien_ship_tu: 10000, phu_phi: {} }), KOME);
    expect(z[0].chu).toBe("¥605 / thùng");
    expect(z[1]).toMatchObject({ chu: "từ ¥10,000", mau: "do" });
    expect(z[2].chu).toBe("không");
    expect(oBang(KOME, KOME)[1].mau).toBeUndefined();
  });
});

describe("phiSoSanh — điều kiện cho 'Tính cả phí giao'", () => {
  it("theo ma_doi_thu + dòng KOME riêng", () => {
    const p = phiSoSanh([KOME, g("A", { phi_ship: 1 })]);
    expect(p.kome?.phi_ship).toBe(500);
    expect(p.ben.get("A")?.phi_ship).toBe(1);
    expect(p.ben.has("KOME")).toBe(false);
    expect(phiSoSanh([g("A")]).kome).toBeNull();
  });
});
