import { describe, expect, it } from "vitest";
import type { DaBo, GiaoHang, QuanSat } from "./kieu";
import {
  daSua, docSoNhap, docXungDot, doiGi, formGiao, formTu, kgThung, kiemForm, lucNgan, moTaThayBoi, payload, payloadGiao,
  thanHoanTac,
} from "./sua_logic";

function qs(o: Partial<QuanSat> = {}): QuanSat {
  return {
    ma_doi_thu: "THAK", ten_doi_thu: "Thái Khang", nguon: "nap", id: 7, ma_hang_dt: "ten:gao", mat_hang_khoa: "ten:gao", an: false, ngay_nguon: "2026-08-01",
    hinh_thuc_nguon: "file", nguon_file: "thak.pdf", vi_tri: null, ten_goc: "Gạo ST25", quy_cach_goc: "20 x 500g",
    gia_goc: 5300, don_vi_gia: "thung", kg_moi_don_vi_gia: 10, thue: "chua", gom_ship: "khong_ro", kenh_gia: null,
    muc_gia: null, gia_bac: null, gia_truoc_km: null, trang_thai: "con", khuyen_mai: null, loai_nguon: "bang_gia",
    ghi_chu: null, ma_kome: "ST25", nhan: "cung_hang", nhom_khoa: "ma:ST25", ten_nhom: "Gạo ST25", trang_thai_duyet: "ai_doc",
    yen_chuan: 530, don_vi_so: "kg", nen_gia: "chuan", tuoi_ngay: 30, thang_lo: "2026-08", lien_ket_thu_muc: null,
    web_ben: null, lien_ket_bang_chung: null, so_goi_thung: 20, kl_goi_g: 500,
    bac: [{ tu: 5, don_vi_sl: "thung", gia: 5100, don_vi_gia: "thung" }], kg_thung_dt: 10,
    gia_goi: null, gia_thung: 5300, gia_1: 530, gia_5: 510, gia_10: 510, gia_pallet: null, sua_cuoi: 42, ...o,
  };
}

describe("formTu", () => {
  it("số → chuỗi, null → rỗng", () => {
    const f = formTu(qs({ gia_goc: null, khuyen_mai: null, thue: null, nhan: null }));
    expect(f.gia_goc).toBe(""); expect(f.khuyen_mai).toBe(""); expect(f.thue).toBe(""); expect(f.nhan).toBe("khong");
    expect(f.so_goi_thung).toBe("20"); expect(f.kl_goi_g).toBe("500");
    expect(f.bac).toEqual([{ tu: "5", don_vi_sl: "thung", gia: "5100", don_vi_gia: "thung" }]);
    expect(f.vi_sao_gia).toBe("");
  });
  it("bac null → mảng rỗng", () => expect(formTu(qs({ bac: null })).bac).toEqual([]));
});

describe("payload", () => {
  it("không đổi → rong, da_xem = sua_cuoi", () => {
    const q = qs(); const p = payload(q, formTu(q), false);
    expect(p.rong).toBe(true); expect(p.doi_gia).toBe(false);
    expect(p.body).toMatchObject({ nguon: "nap", id: 7, da_xem: 42, ghi_de: false, thay_doi: {} });
    expect("nhan" in p.body).toBe(false);
  });
  it("đổi kl_goi_g → chỉ trường đó, không phải giá", () => {
    const q = qs(); const p = payload(q, { ...formTu(q), kl_goi_g: "450" }, false);
    expect(p.rong).toBe(false); expect(p.doi_gia).toBe(false);
    expect((p.body as { thay_doi: object }).thay_doi).toEqual({ kl_goi_g: "450" });
    expect("vi_sao_gia" in p.body).toBe(false);
  });
  it("gõ lại cùng số (5,300 = 5300) không tính là đổi", () => {
    const q = qs(); expect(payload(q, { ...formTu(q), gia_goc: "5,300" }, false).rong).toBe(true);
  });
  it("đổi gia_goc → doi_gia, kèm vi_sao_gia / nguồn khi đã đổi", () => {
    const q = qs();
    const p = payload(q, { ...formTu(q), gia_goc: "5500", vi_sao_gia: "da_doi", loai_nguon: "to_roi",
      lien_ket_bang_chung: " https://drive.google.com/x " }, true);
    expect(p.doi_gia).toBe(true);
    expect(p.body).toMatchObject({ ghi_de: true, thay_doi: { gia_goc: "5500" }, vi_sao_gia: "da_doi", loai_nguon: "to_roi",
      lien_ket_bang_chung: "https://drive.google.com/x" });
  });
  it("vi_sao đã chọn nhưng giá không đổi → không gửi vi_sao", () => {
    const q = qs(); const p = payload(q, { ...formTu(q), vi_sao_gia: "doc_sai", khuyen_mai: "Tặng 1" }, false);
    expect(p.doi_gia).toBe(false); expect("vi_sao_gia" in p.body).toBe(false);
    expect((p.body as { thay_doi: object }).thay_doi).toEqual({ khuyen_mai: "Tặng 1" });
  });
  it("đọc sai → không gửi loại nguồn / link", () => {
    const q = qs(); const p = payload(q, { ...formTu(q), thue: "co", vi_sao_gia: "doc_sai", loai_nguon: "khac" }, false);
    expect(p.body).toMatchObject({ vi_sao_gia: "doc_sai", thay_doi: { thue: "co" } });
    expect("loai_nguon" in p.body).toBe(false);
  });
  it("bậc trống cả hai ô bị bỏ; '5,300' → 5300; bậc là giá", () => {
    const q = qs(); const f = formTu(q);
    const p = payload(q, { ...f, bac: [...f.bac, { tu: "", don_vi_sl: "thung", gia: "", don_vi_gia: "thung" },
      { tu: "10", don_vi_sl: "thung", gia: "5,000", don_vi_gia: "thung" }] }, false);
    expect(p.doi_gia).toBe(true);
    expect((p.body as { thay_doi: { bac: unknown } }).thay_doi.bac).toEqual([
      { tu: 5, don_vi_sl: "thung", gia: 5100, don_vi_gia: "thung" }, { tu: 10, don_vi_sl: "thung", gia: 5000, don_vi_gia: "thung" }]);
  });
  it("chỉ thêm một bậc trống → không đổi", () => {
    const q = qs(); const f = formTu(q);
    expect(payload(q, { ...f, bac: [...f.bac, { tu: "", don_vi_sl: "kg", gia: " ", don_vi_gia: "kg" }] }, false).rong).toBe(true);
  });
  it("xoá hết bậc → bac []", () => {
    const q = qs(); const p = payload(q, { ...formTu(q), bac: [] }, false);
    expect((p.body as { thay_doi: { bac: unknown } }).thay_doi.bac).toEqual([]); expect(p.doi_gia).toBe(true);
  });
  it("nhan khác → có nhan; không đổi trường nào vẫn không rong", () => {
    const q = qs(); const p = payload(q, { ...formTu(q), nhan: "thay_the" }, false);
    expect(p.rong).toBe(false); expect(p.body).toMatchObject({ nhan: "thay_the", thay_doi: {} });
  });
  it("nhan null giữ 'khong' → không gửi nhan", () => {
    const q = qs({ nhan: null }); expect(payload(q, formTu(q), false).rong).toBe(true);
  });
  it("khuyến mãi xoá → gửi ''", () => {
    const q = qs({ khuyen_mai: "Giảm 5%" });
    expect((payload(q, { ...formTu(q), khuyen_mai: "  " }, false).body as { thay_doi: object }).thay_doi).toEqual({ khuyen_mai: "" });
  });
});

describe("kgThung", () => {
  it("20 gói × 500 g = 10 kg", () => expect(kgThung("20", "500")).toBe(10));
  it("thiếu / sai → null", () => {
    expect(kgThung("", "500")).toBeNull(); expect(kgThung("20", "abc")).toBeNull(); expect(kgThung("0", "500")).toBeNull();
  });
  it("tịnh dùng phẩy thập phân: 12 × 1,5 g", () => expect(kgThung("12", "1,5")).toBe(0.018));
});

describe("docSoNhap", () => {
  it("phẩy nghìn / phẩy thập phân / sai", () => {
    expect(docSoNhap("5,300")).toBe(5300); expect(docSoNhap("12,345.5")).toBe(12345.5); expect(docSoNhap("0,5")).toBe(0.5);
    expect(docSoNhap(" 42 ")).toBe(42); expect(docSoNhap("")).toBeNull(); expect(Number.isNaN(docSoNhap("1e3"))).toBe(true);
    expect(docSoNhap("1,500", true)).toBe(1.5);
  });
});

describe("kiemForm", () => {
  const q = qs();
  it("đổi giá mà chưa chọn vì sao", () => expect(kiemForm(q, { ...formTu(q), gia_goc: "1" })).toMatch(/vì sao/i));
  it("giá đã đổi cần loại nguồn", () =>
    expect(kiemForm(q, { ...formTu(q), gia_goc: "1", vi_sao_gia: "da_doi" })).toMatch(/nguồn/i));
  it("link phải https", () =>
    expect(kiemForm(q, { ...formTu(q), gia_goc: "1", vi_sao_gia: "da_doi", loai_nguon: "khac", lien_ket_bang_chung: "http://x" })).toMatch(/https/));
  it("gói / thùng nguyên 1..100000", () => {
    expect(kiemForm(q, { ...formTu(q), so_goi_thung: "2.5" })).toMatch(/nguyên/);
    expect(kiemForm(q, { ...formTu(q), so_goi_thung: "100001" })).toMatch(/nguyên/);
    expect(kiemForm(q, { ...formTu(q), so_goi_thung: "24" })).toBeNull();
  });
  it("tịnh > 0 và ≤ 30000", () => {
    expect(kiemForm(q, { ...formTu(q), kl_goi_g: "0" })).toMatch(/Tịnh/);
    expect(kiemForm(q, { ...formTu(q), kl_goi_g: "30001" })).toMatch(/Tịnh/);
  });
  it("bậc thiếu một ô", () => {
    const f = formTu(q);
    expect(kiemForm(q, { ...f, vi_sao_gia: "doc_sai", bac: [{ tu: "3", don_vi_sl: "thung", gia: "", don_vi_gia: "thung" }] })).toMatch(/bậc/i);
  });
  it("hợp lệ → null", () => expect(kiemForm(q, { ...formTu(q), gia_goc: "5400", vi_sao_gia: "doc_sai" })).toBeNull());
});

describe("xung đột", () => {
  it("docXungDot đọc thân 409", () => {
    const e = { ma: 409, du_lieu: { loi: "x", xung_dot: { ai: "lan", luc: "2026-09-30T05:02:00+00:00", sau: { gia_goc: "1" }, sua_cuoi: 50 } } };
    expect(docXungDot(e)).toEqual({ ai: "lan", luc: "2026-09-30T05:02:00+00:00", sau: { gia_goc: "1" }, sua_cuoi: 50, thay_boi: null });
    expect(docXungDot({ ma: 400, du_lieu: {} })).toBeNull(); expect(docXungDot(new Error("x"))).toBeNull();
    expect(docXungDot({ ma: 409 })).toEqual({ ai: null, luc: "", sau: null, sua_cuoi: 0, thay_boi: null });
  });
  it("lucNgan = giờ:phút dd/mm giờ Tokyo", () => expect(lucNgan("2026-09-30T05:02:00+00:00")).toBe("14:02 30/09"));
  it("doiGi liệt kê khoá của sau (nhãn Việt), bỏ khoá kỹ thuật", () => {
    expect(doiGi({ gia_goc: "1", kl_goi_g: "2", tay_moi: 9 })).toBe("giá, tịnh 1 gói");
    expect(doiGi(null)).toBe(""); expect(doiGi({ la: 1 })).toBe("la");
  });
});

function gh(o: Partial<GiaoHang> = {}): GiaoHang {
  return { ma_doi_thu: "IMAI", ten: "Imai", bao_ship: false, phi_ship: 800, phi_ship_theo: "don", mien_ship_tu: 20000,
    mien_ship_kien: null, thung_moi_kien: null, phu_phi: { hokkaido: 800, okinawa: "khong_nhan", kanto: 0 }, phi_daibiki: 330,
    daibiki_tu: null, daibiki_sau: null, ck_mien_daibiki: null, kien_toi_da_kg: null, ghep_kien: null, thue: "chua",
    cach_gui: null, nguon_chu: "送料800円", ngay_nguon: "2026-08-01", suy: false, da_xac_nhan: false, sua_cuoi: 5, ...o };
}

describe("giao hàng", () => {
  it("không đổi → rong", () => { const g = gh(); expect(payloadGiao(g, formGiao(g), false, false).rong).toBe(true); });
  it("chỉ gửi trường đổi; '' = xoá; bool thật", () => {
    const g = gh(); const f = formGiao(g);
    const p = payloadGiao(g, { ...f, truong: { ...f.truong, phi_ship: "", bao_ship: "true", cach_gui: "宅急便" } }, true, false);
    expect(p.body).toEqual({ ma_doi_thu: "IMAI", da_xem: 5, ghi_de: true,
      thay_doi: { phi_ship: "", bao_ship: true, cach_gui: "宅急便" } });
  });
  it("phụ phí: giữ vùng không sửa, số là number, Okinawa +¥", () => {
    const g = gh(); const f = formGiao(g);
    expect(f.vung.hokkaido).toBe("800"); expect(f.okinawa).toBe("khong_nhan");
    const p = payloadGiao(g, { ...f, vung: { ...f.vung, tohoku: "400" }, okinawa: "co", okinawa_so: "1,200" }, false, false);
    expect((p.body as { thay_doi: { phu_phi: unknown } }).thay_doi.phu_phi).toEqual({ hokkaido: 800, kanto: 0, tohoku: 400, okinawa: 1200 });
  });
  it("xoá hết phụ phí → ''", () => {
    const g = gh({ phu_phi: { hokkaido: 800 } }); const f = formGiao(g);
    expect((payloadGiao(g, { ...f, vung: { ...f.vung, hokkaido: "" } }, false, false).body as { thay_doi: object }).thay_doi)
      .toEqual({ phu_phi: "" });
  });
  it("KOME xác nhận không đổi trường nào", () => {
    const g = gh({ ma_doi_thu: "KOME" }); const p = payloadGiao(g, formGiao(g), false, true);
    expect(p.rong).toBe(false); expect((p.body as { thay_doi: object }).thay_doi).toEqual({ xac_nhan: true });
  });
});

describe("vòng sửa 1", () => {
  it("gia_truoc_km: số → chuỗi, đổi → gửi, xoá → ''", () => {
    const q = qs({ gia_truoc_km: 6000 }); const f = formTu(q);
    expect(f.gia_truoc_km).toBe("6000");
    expect(payload(q, { ...f, gia_truoc_km: "6,000" }, false).rong).toBe(true);
    expect((payload(q, { ...f, gia_truoc_km: "6500" }, false).body as { thay_doi: object }).thay_doi).toEqual({ gia_truoc_km: "6500" });
    const p = payload(q, { ...f, gia_truoc_km: " " }, false);
    expect((p.body as { thay_doi: object }).thay_doi).toEqual({ gia_truoc_km: "" }); expect(p.doi_gia).toBe(false);
  });
  it("gia_truoc_km sai → kiemForm báo", () => {
    const q = qs(); expect(kiemForm(q, { ...formTu(q), gia_truoc_km: "abc" })).toMatch(/trước khuyến mãi/);
  });
  it("giá đã đổi: gửi kèm bậc / khuyến mãi / giá trước KM ĐANG THẤY dù không đổi", () => {
    const q = qs({ khuyen_mai: "Giảm 5%", gia_truoc_km: 5600 }); const f = formTu(q);
    const p = payload(q, { ...f, gia_goc: "5500", vi_sao_gia: "da_doi", loai_nguon: "bang_gia" }, false);
    expect((p.body as { thay_doi: object }).thay_doi).toEqual({ gia_goc: "5500", khuyen_mai: "Giảm 5%", gia_truoc_km: "5600",
      bac: [{ tu: 5, don_vi_sl: "thung", gia: 5100, don_vi_gia: "thung" }] });
  });
  it("giá đã đổi: ô trống không kèm", () => {
    const q = qs({ bac: null }); const f = formTu(q);
    const p = payload(q, { ...f, gia_goc: "5500", vi_sao_gia: "da_doi", loai_nguon: "bang_gia" }, false);
    expect((p.body as { thay_doi: object }).thay_doi).toEqual({ gia_goc: "5500" });
  });
  it("đọc sai: không kèm trường không đổi", () => {
    const q = qs({ khuyen_mai: "Giảm 5%" }); const f = formTu(q);
    expect((payload(q, { ...f, gia_goc: "5500", vi_sao_gia: "doc_sai" }, false).body as { thay_doi: object }).thay_doi)
      .toEqual({ gia_goc: "5500" });
  });
  it("dòng nạp: xoá gói / tịnh / giá (không phải giá đã đổi) → báo trước khi gửi", () => {
    const q = qs(); const f = formTu(q);
    expect(kiemForm(q, { ...f, so_goi_thung: "" })).toMatch(/Để trống/);
    expect(kiemForm(q, { ...f, kl_goi_g: "" })).toMatch(/Để trống/);
    expect(kiemForm(q, { ...f, gia_goc: "", vi_sao_gia: "doc_sai" })).toMatch(/Để trống/);
    expect(kiemForm(q, { ...f, gia_goc: "", vi_sao_gia: "da_doi", loai_nguon: "khac" }) ?? "").not.toMatch(/Để trống/);
    const t = qs({ nguon: "tay" }); expect(kiemForm(t, { ...formTu(t), so_goi_thung: "" })).toBeNull();
  });
});


describe("ghép mã KOME / nhóm trong pop-up (B13)", () => {
  const chuaGhep = () => qs({ ma_kome: null, nhan: null, nhom_khoa: null, ten_nhom: null, ma_ghep: null, nhom_ghep: null });
  it("formTu: mã hiện hành, không thì mã đã nhớ ở lần bỏ nhóm; nhóm ghép tường minh", () => {
    expect(formTu(qs()).ma_kome).toBe("ST25");
    expect(formTu(qs({ ma_kome: null, ma_ghep: "NT01", nhan: null })).ma_kome).toBe("NT01");
    expect(formTu(qs({ nhom_ghep: 9 })).nhom_id).toBe("9");
    expect(formTu(chuaGhep())).toMatchObject({ ma_kome: "", nhom_id: "", nhan: "khong" });
  });
  it("dòng chưa ghép: gõ mã + chọn nhãn → gửi ma_kome + nhan; không đổi thì không gửi khoá", () => {
    const q = chuaGhep();
    const p = payload(q, { ...formTu(q), ma_kome: " NT01 ", nhan: "cung_hang" }, false);
    expect(p.rong).toBe(false);
    expect(p.body).toMatchObject({ ma_kome: "NT01", nhan: "cung_hang" });
    expect("nhom_id" in p.body).toBe(false);
    const k = payload(qs(), formTu(qs()), false).body;
    expect("ma_kome" in k || "nhom_id" in k).toBe(false);
  });
  it("đổi mã sai sang mã khác (nhãn giữ) · chọn nhóm · bỏ nhóm về theo mã", () => {
    const q = qs({ nhom_ghep: 3 });
    expect(payload(q, { ...formTu(q), ma_kome: "NT02" }, false).body).toMatchObject({ ma_kome: "NT02" });
    expect("nhan" in payload(q, { ...formTu(q), ma_kome: "NT02" }, false).body).toBe(false);
    expect(payload(q, { ...formTu(q), nhom_id: "5" }, false).body).toMatchObject({ nhom_id: 5 });
    expect(payload(q, { ...formTu(q), nhom_id: "" }, false).body).toMatchObject({ nhom_id: null });
    expect(payload(q, { ...formTu(q), ma_kome: "" , nhan: "khong" }, false).body).toMatchObject({ ma_kome: null, nhan: "khong" });
  });
  it("kiemForm: mã mới mà vẫn 'không liên quan' / nhãn ghép mà không có mã → câu lỗi", () => {
    const q = chuaGhep();
    expect(kiemForm(q, { ...formTu(q), ma_kome: "NT01" })).toMatch(/cùng thương hiệu hoặc khác thương hiệu/);
    expect(kiemForm(q, { ...formTu(q), nhan: "thay_the" })).toMatch(/mã KOME/);
    expect(kiemForm(q, { ...formTu(q), ma_kome: "NT01", nhan: "thay_the" })).toBeNull();
    expect(kiemForm(qs(), { ...formTu(qs()), ma_kome: "", nhan: "khong" })).toBeNull();   // bỏ ghép hẳn
  });
});

describe("dòng đã bị thay (B14) · ✎ · hoàn tác (B15)", () => {
  it("docXungDot đọc thay_boi; 409 thường thì null", () => {
    const e = { ma: 409, du_lieu: { xung_dot: { ai: "Hải", luc: "2026-09-30T05:02:00+00:00", sau: {}, sua_cuoi: 9,
      thay_boi: { nguon: "tay", id: 12 } } } };
    expect(docXungDot(e)?.thay_boi).toEqual({ nguon: "tay", id: 12 });
    expect(docXungDot({ ma: 409, du_lieu: { xung_dot: { ai: null } } })?.thay_boi).toBeNull();
    expect(docXungDot({ ma: 409, du_lieu: { xung_dot: { thay_boi: { nguon: "x", id: "1" } } } })?.thay_boi).toBeNull();
  });
  it("moTaThayBoi có / không có người sửa", () => {
    expect(moTaThayBoi(null)).toMatch(/đã có bản mới/);
    expect(moTaThayBoi({ ai: "Hải", luc: "2026-09-30T05:02:00+00:00" })).toMatch(/Hải sửa lúc 14:02 30\/09/);
  });
  it("daSua = sua_cuoi > 0", () => {
    expect(daSua(qs({ sua_cuoi: 0 }))).toBe(false); expect(daSua(qs({ sua_cuoi: 3 }))).toBe(true); expect(daSua(undefined)).toBe(false);
  });
  it("thanHoanTac ghi lại nhãn cũ, chống sửa đè bằng sua_cuoi", () => {
    const x: DaBo = { nguon: "nap", id: 4, ma_doi_thu: "THAK", ten_doi_thu: null, ten_goc: "Basa", nhom_khoa: "ma:NT01",
      ten_nhom: "Basa", nhan_cu: "cung_hang", sua_cuoi: 17 };
    expect(thanHoanTac(x)).toEqual({ nguon: "nap", id: 4, da_xem: 17, ghi_de: false, nhan: "cung_hang" });
  });
});
