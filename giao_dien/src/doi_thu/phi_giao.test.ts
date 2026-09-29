import { describe, expect, it } from "vitest";
import caTho from "../../../tests/du_lieu/phi_giao_ca.json";
import { tinh, type DieuKienGiao, type DonMau, type KetQuaPhi } from "./phi_giao";

type Ca = { ten: string; dk: DieuKienGiao; don: DonMau; ra: KetQuaPhi };
const CA = caTho as unknown as Ca[];

describe("phí đơn mẫu — cùng ca với kome/phi_giao.py", () => {
  for (const c of CA) it(c.ten, () => expect(tinh(c.dk, c.don)).toEqual(c.ra));
});
