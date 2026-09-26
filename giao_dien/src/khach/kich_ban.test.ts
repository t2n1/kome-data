import { describe, expect, it } from "vitest";
import { dauKichBan, kichBanGoi } from "./kich_ban";

describe("kichBanGoi", () => {
  it("đúng từng ký tự như kịch bản cũ của /lien-he", () => {
    const s = kichBanGoi({
      dau: dauKichBan("フォー大阪", "202301150002", "06-1234-5678"),
      ly_do: "Lý do gọi: Lâu không mua — im 34 ngày (nhịp thường 15 ngày).",
      tieu_de_ma: "Nên chào:",
      ma: [{ ten: "フォー麺", chi_tiet: "9 lần · nhịp 14 ngày · lần cuối 20 ngày trước" }],
      cuoi: { ngay: "2026-09-02", noi_dung: "Hẹn đầu tháng" },
    });
    expect(s).toBe([
      "フォー大阪 (202301150002) ☎ 06-1234-5678",
      "Lý do gọi: Lâu không mua — im 34 ngày (nhịp thường 15 ngày).",
      "Nên chào:",
      "- フォー麺 (9 lần · nhịp 14 ngày · lần cuối 20 ngày trước)",
      "Lần liên hệ trước (2026-09-02): Hẹn đầu tháng",
    ].join("\n"));
  });
  it("không có mã thì bỏ cả dòng tiêu đề, không có điện thoại thì bỏ ☎", () => {
    expect(kichBanGoi({ dau: dauKichBan("A", "1", null), ly_do: "L", tieu_de_ma: "X:", ma: [], cuoi: null }))
      .toBe("A (1)\nL");
  });
});
