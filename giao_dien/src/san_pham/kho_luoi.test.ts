import { describe, expect, it } from "vitest";
import { gomTheoMa } from "./kho_luoi";
import type { DongKho } from "./kieu";

const d = (ma: string, kho: string, sl: number, gt: number, vai: "dang_xuat" | "cho", han: number | null, kk = false) =>
  ({ ma, ten: ma, nganh: "N", nhan_trang_thai: "Đủ hàng", mau: "ok", kho, so_luong: sl, gia_tri: gt,
     vai_tro_lo: vai, han_con_lai: han, khong_kip_ban: kk }) as unknown as DongKho;

describe("gomTheoMa", () => {
  it("một thẻ mỗi mã, cộng hai lô, lô đang xuất đứng trước", () => {
    const t = gomTheoMa([d("A", "1002", 50, 500, "cho", 300), d("B", "0001", 10, 900, "dang_xuat", 40),
      d("A", "0001", 20, 200, "dang_xuat", 120, true)]);
    expect(t.map(x => x.ma)).toEqual(["B", "A"]);
    const a = t[1];
    expect([a.so_luong, a.gia_tri, a.khong_kip, a.han_gan]).toEqual([70, 700, true, 120]);
    expect(a.lo.map(x => x.kho)).toEqual(["0001", "1002"]);
  });
  it("Σ giá trị thẻ = Σ giá trị dòng (không mất dòng)", () => {
    const ds = [d("A", "0001", 1, 3, "dang_xuat", null), d("C", "0001", 1, 7, "dang_xuat", 5), d("A", "1002", 1, 4, "cho", 9)];
    expect(gomTheoMa(ds).reduce((s, x) => s + x.gia_tri, 0)).toBe(14);
    expect(gomTheoMa(ds).reduce((s, x) => s + x.lo.length, 0)).toBe(3);
  });
});
