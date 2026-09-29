import { describe, expect, it } from "vitest";
import type { Nhom, QuanSat } from "./kieu";
import { LUA_CHON_GK, khoaNhom, khoaONhiet, NHAN_SL, bangBac, batTat, demThieu, dongCot, giaBacKg, giaKome, giaTai, locDanhSach, macDinhSp, matHangCuaBen,
  nhanBac, nhanKlGoi, nhomChon, oNhiet, pcDau, soMatHang, thieuQuyCach } from "./so_sanh_logic";

let seq = 0;
const qs = (o: Partial<QuanSat>): QuanSat => ({
  ma_doi_thu: "a", ten_doi_thu: "Bên A", nguon: "nap", id: ++seq, ma_hang_dt: `h${seq}`, ngay_nguon: "2026-09-01",
  hinh_thuc_nguon: "web", nguon_file: null, vi_tri: null, ten_goc: `Hàng ${seq}`, quy_cach_goc: null, gia_goc: null,
  don_vi_gia: null, kg_moi_don_vi_gia: null, thue: "chua", gom_ship: null, kenh_gia: null, muc_gia: null, gia_bac: null,
  gia_truoc_km: null, trang_thai: "con", khuyen_mai: null, loai_nguon: "bang_gia", ghi_chu: null, ma_kome: "K1",
  nhan: "thay_the", nhom_khoa: "ma:K1", ten_nhom: "Nhóm", trang_thai_duyet: "ai_doc", yen_chuan: null, don_vi_so: "kg",
  nen_gia: "", tuoi_ngay: 5, thang_lo: null, lien_ket_thu_muc: null, web_ben: null, lien_ket_bang_chung: null,
  so_goi_thung: 10, kl_goi_g: 500, bac: null, kg_thung_dt: null, gia_goi: null, gia_thung: null, gia_1: null, gia_5: null,
  gia_10: null, gia_pallet: null, sua_cuoi: 0, ...o,
} as unknown as QuanSat);

const nh = (o: Partial<Nhom> = {}): Nhom => ({
  nhom_khoa: "ma:K1", ten_nhom: "Gạo", nganh: "米", don_vi_so: "kg", ma_kome: ["K1"], gia_kome: 500, so_ben: 3, thap_nhat: 0,
  ben_thap_nhat: "", trung_vi: 0, cao_nhat: 0, ty_le_re_hon_kome: null, quan_sat: [], gia_kome_chuan: 520,
  gia_kome_bang: { "10": 430, "01": 510 }, gia_kome_km: null, gia_kome_so: 500, lech_trung_vi: 0, gia_kome_lech: false,
  kome_kg_goi: 0.5, kome_goi_thung: 20, kome_kg_thung: 10, ...o,
});

// 8 mặt hàng (+1 khách kể): 2 cùng thương hiệu (M1, M2 — đắt), 1 thiếu quy cách (M4), 1 hết (M5), có giá pallet ở M1 và M8.
const mau = (): Nhom => nh({ quan_sat: [
  qs({ ten_goc: "M1", gia_1: 900, gia_5: 880, gia_10: 860, gia_pallet: 800, nhan: "cung_hang", ma_doi_thu: "a", ten_doi_thu: "Bên A" }),
  qs({ ten_goc: "M2", gia_1: 800, nhan: "cung_hang", ma_doi_thu: "b", ten_doi_thu: "Bên B" }),
  qs({ ten_goc: "M3", gia_1: 700, ma_doi_thu: "c", ten_doi_thu: "Bên C" }),
  qs({ ten_goc: "M4", gia_1: 600, so_goi_thung: null, ma_doi_thu: "d", ten_doi_thu: "Bên D" }),
  qs({ ten_goc: "M5", gia_1: 500, trang_thai: "het", ma_doi_thu: "e", ten_doi_thu: "Bên E" }),
  qs({ ten_goc: "M6", gia_1: 400, ma_doi_thu: "f", ten_doi_thu: "Bên F" }),
  qs({ ten_goc: "M7", gia_1: 300, ma_doi_thu: "g", ten_doi_thu: "Bên G" }),
  qs({ ten_goc: "M8", gia_1: 450, gia_pallet: 350, ma_doi_thu: "h", ten_doi_thu: "Bên H" }),
  qs({ ten_goc: "KHACH", gia_1: 100, loai_nguon: "khach_ke", ma_doi_thu: "i", ten_doi_thu: "Bên I" }),
] });

describe("giaTai / giaKome", () => {
  it("giá theo số lượng", () => {
    const q = qs({ gia_1: 900, gia_5: 880, gia_10: 860, gia_pallet: 800 });
    expect(giaTai(q, "1").gia).toBe(900);
    expect(giaTai(q, "5").gia).toBe(880);
    expect(giaTai(q, "10").gia).toBe(860);
    expect(giaTai(q, "pallet")).toEqual({ gia: 800, khongGhiPallet: false });
  });
  it("pallet không ghi → giá lẻ + khongGhiPallet", () => {
    expect(giaTai(qs({ gia_1: 900 }), "pallet")).toEqual({ gia: 900, khongGhiPallet: true });
    expect(giaTai(qs({ gia_1: 900 }), "5").khongGhiPallet).toBe(false);
  });
  it("giaKome theo lựa chọn", () => {
    const n = nh();
    expect(giaKome(n, "chuan")).toBe(520);
    expect(giaKome(n, "thuc")).toBe(500);
    expect(giaKome(n, "10")).toBe(430);
    expect(giaKome(n, "04")).toBeNull();
    expect(giaKome(nh({ gia_kome_chuan: null }), "chuan")).toBe(500);
    expect(giaKome(nh({ gia_kome_bang: null }), "10")).toBeNull();
  });
  it("danh sách lựa chọn", () => {
    expect(LUA_CHON_GK.map(x => x.ma)).toEqual(["chuan", "thuc", "01", "02", "04", "05", "09", "10"]);
    expect(NHAN_SL.pallet).toBe("1 pallet");
  });
});

describe("dongCot", () => {
  const o = { sl: "1" as const, gk: "thuc", chiCung: false, moRong: false };
  it("thu gọn giữ KOME + 5 rẻ nhất + cùng thương hiệu; bỏ khách kể", () => {
    const { dong, an } = dongCot(mau(), o);
    // 8 hàng + KOME; 5 rẻ nhất (kể cả KOME) = M7,M6,M8,KOME,M5 ... KOME luôn giữ nên tính riêng: 5 hàng rẻ nhất = M7,M6,M8,M5,M4
    expect(an).toBe(1);
    expect(dong.map(d => d.ten)).toEqual(["M7", "M6", "M8", "KOME", "M5", "M4", "M2", "M1"]);
    expect(dong.some(d => d.ten === "KHACH")).toBe(false);
  });
  it("mở rộng không ẩn gì", () => {
    const r = dongCot(mau(), { ...o, moRong: true });
    expect(r.an).toBe(0);
    expect(r.dong).toHaveLength(9);
  });
  it("chiCung bỏ khác thương hiệu, KOME còn", () => {
    const { dong, an } = dongCot(mau(), { ...o, chiCung: true });
    expect(dong.map(d => d.ten)).toEqual(["KOME", "M2", "M1"]);
    expect(an).toBe(0);
  });
  it("cờ và p của dòng", () => {
    const { dong } = dongCot(mau(), { ...o, moRong: true });
    const k = dong.find(d => d.kome)!;
    expect(k.gia).toBe(500); expect(k.soGoi).toBe(20); expect(k.klGoi).toBe(500); expect(k.p).toBeNull();
    const m5 = dong.find(d => d.ten === "M5")!;
    expect(m5.het).toBe(true); expect(m5.p).toBe(0);
    expect(dong.find(d => d.ten === "M4")!.thieu).toBe(true);
    expect(dong.find(d => d.ten === "M1")!.cung).toBe(true);
    expect(dong.find(d => d.ten === "M7")!.p).toBe(-40);
    expect(dong.find(d => d.ten === "M7")!.ben).toBe("Bên G");
  });
  it("pallet: hàng không ghi giá pallet mang khongGhiPallet (giá lẻ)", () => {
    const { dong } = dongCot(mau(), { ...o, sl: "pallet", moRong: true });
    expect(dong.find(d => d.ten === "M3")!.khongGhiPallet).toBe(true);
    expect(dong.find(d => d.ten === "M3")!.gia).toBe(700);
    expect(dong.find(d => d.ten === "M8")!.gia).toBe(350);
    expect(dong.find(d => d.ten === "M8")!.khongGhiPallet).toBe(false);
    expect(dong.find(d => d.kome)!.khongGhiPallet).toBe(false);
  });
  it("giá null xếp cuối; giá cũ / km / thuế / ship", () => {
    const n = nh({ quan_sat: [qs({ ten_goc: "X" }), qs({ ten_goc: "Y", gia_1: 10, tuoi_ngay: 61, thue: "khong_ro", gom_ship: "co", gia_truoc_km: 12 })] });
    const { dong } = dongCot(n, { sl: "1", gk: "thuc", chiCung: false, moRong: true });
    expect(dong.map(d => d.ten)).toEqual(["Y", "KOME", "X"]);
    const y = dong[0];
    expect([y.cu, y.thueKhongRo, y.gomShip, y.km]).toEqual([true, true, true, true]);
    expect(dong[2].gia).toBeNull(); expect(dong[2].p).toBeNull();
  });
  it("bất thường vẫn vẽ, mang cờ trên q", () => {
    const n = nh({ quan_sat: [qs({ ten_goc: "Z", gia_1: 5, bat_thuong: true })] });
    const { dong } = dongCot(n, { sl: "1", gk: "thuc", chiCung: false, moRong: true });
    expect(dong[0].q?.bat_thuong).toBe(true);
  });
});

describe("oNhiet", () => {
  it("chọn cùng thương hiệu trước, dù đắt hơn; ben xếp theo số nhóm", () => {
    const n1 = nh({ nhom_khoa: "n1", quan_sat: [
      qs({ ten_doi_thu: "A", ma_doi_thu: "a", gia_1: 300, nhan: "thay_the" }),
      qs({ ten_doi_thu: "A", ma_doi_thu: "a", gia_1: 900, nhan: "cung_hang" }),
      qs({ ten_doi_thu: "A", ma_doi_thu: "a", gia_1: 950, nhan: "cung_hang" }),
      qs({ ten_doi_thu: "B", ma_doi_thu: "b", gia_1: 700, nhan: "thay_the" }),
      qs({ ten_doi_thu: "B", ma_doi_thu: "b", gia_1: 600, nhan: "thay_the" }),
    ] });
    const n2 = nh({ nhom_khoa: "n2", quan_sat: [qs({ ten_doi_thu: "B", ma_doi_thu: "b", gia_1: 100 }), qs({ loai_nguon: "khach_ke", ten_doi_thu: "K", ma_doi_thu: "k", gia_1: 1 })] });
    const r = oNhiet([n1, n2], { sl: "1", gk: "thuc", chiCung: false });
    expect(r.ben).toEqual(["B", "A"]);
    const a = r.o.get("n1|kg|A")!;
    expect(a.q.gia_1).toBe(900); expect(a.cung).toBe(true); expect(a.so).toBe(3); expect(a.p).toBe(80);
    const b = r.o.get("n1|kg|B")!;
    expect(b.q.gia_1).toBe(600); expect(b.cung).toBe(false); expect(b.so).toBe(2);
    expect(r.o.has("n2|kg|K")).toBe(false);
    expect(r.o.get("n2|kg|B")!.p).toBe(-80);
  });
  it("hai dòng cùng nhom_khoa khác don_vi_so không ghi đè ô của nhau", () => {
    const kg = nh({ nhom_khoa: "ma:X", don_vi_so: "kg", gia_kome: 500, quan_sat: [qs({ ten_doi_thu: "A", ma_doi_thu: "a", gia_1: 400 })] });
    const goi = nh({ nhom_khoa: "ma:X", don_vi_so: "don_vi:goi", gia_kome: 100, gia_kome_chuan: 100,
      quan_sat: [qs({ ten_doi_thu: "A", ma_doi_thu: "a", gia_1: 150 })] });
    const r = oNhiet([kg, goi], { sl: "1", gk: "thuc", chiCung: false });
    expect(r.o.get(khoaONhiet(kg, "A"))!.p).toBe(-20);
    expect(r.o.get(khoaONhiet(goi, "A"))!.p).toBe(50);
    expect(khoaONhiet(goi, "A")).toBe("ma:X|don_vi:goi|A");
    expect(khoaNhom(kg)).not.toBe(khoaNhom(goi));
    expect(r.ben).toEqual(["A"]);
  });
  it("chiCung bỏ ô chỉ có khác thương hiệu", () => {
    const n1 = nh({ nhom_khoa: "n1", quan_sat: [qs({ ten_doi_thu: "A", ma_doi_thu: "a", gia_1: 300, nhan: "thay_the" }), qs({ ten_doi_thu: "B", ma_doi_thu: "b", gia_1: 300, nhan: "cung_hang" })] });
    const r = oNhiet([n1], { sl: "1", gk: "thuc", chiCung: true });
    expect(r.ben).toEqual(["B"]);
    expect(r.o.has("n1|kg|A")).toBe(false);
  });
});

describe("demThieu / locDanhSach", () => {
  it("demThieu trả mặt hàng đầu + trường thiếu", () => {
    const n = mau();
    n.quan_sat.push(qs({ ten_goc: "T2", kl_goi_g: null }));
    const r = demThieu([n]);
    expect(r.so).toBe(2);
    expect(r.dau!.ten_goc).toBe("M4");
    expect(r.truong).toBe("so_goi_thung");
    expect(demThieu([nh({ quan_sat: [qs({ kl_goi_g: null })] })]).truong).toBe("kl_goi_g");
    expect(demThieu([nh({ quan_sat: [qs({})] })])).toEqual({ so: 0, dau: null, truong: null });
    expect(thieuQuyCach(qs({ kl_goi_g: null }))).toBe(true);
    // chiCung: chỉ đếm hàng cùng thương hiệu (M4, T2 là khác thương hiệu).
    expect(demThieu([n], { chiCung: true })).toEqual({ so: 0, dau: null, truong: null });
    n.quan_sat.push(qs({ ten_goc: "C1", nhan: "cung_hang", kl_goi_g: null }));
    expect(demThieu([n], { chiCung: true })).toMatchObject({ so: 1, truong: "kl_goi_g" });
    expect(demThieu([n]).so).toBe(3);
  });
  const ds = () => [
    nh({ nhom_khoa: "1", ten_nhom: "Gạo Việt", ma_kome: ["G01"], nganh: "米", so_ben: 2, lech_trung_vi: 0.5, quan_sat: [qs({})] }),
    nh({ nhom_khoa: "2", ten_nhom: "Bún khô", ma_kome: ["B02"], nganh: "麺", so_ben: 5, lech_trung_vi: 0.1, quan_sat: [qs({ trang_thai: "het" })] }),
    nh({ nhom_khoa: "3", ten_nhom: "Nước mắm", ma_kome: ["N03"], nganh: "調味料", so_ben: 4, lech_trung_vi: 0.02, quan_sat: [qs({ so_goi_thung: null }), qs({ kl_goi_g: null })] }),
    nh({ nhom_khoa: "4", ten_nhom: "Lệch", nganh: "米", so_ben: 9, lech_trung_vi: 9, gia_kome_lech: true, quan_sat: [qs({})] }),
  ];
  const k = (o: Partial<{ nganh: string; tim: string; nhanh: "" | "dat" | "het" | "thieu" }> = {}) =>
    locDanhSach(ds(), { nganh: "", tim: "", nhanh: "", ...o }).map(n => n.nhom_khoa);
  it("mặc định: so_ben giảm dần, bỏ nhóm lệch", () => expect(k()).toEqual(["2", "3", "1"]));
  it("ngành, tìm bỏ dấu (tên + mã KOME)", () => {
    expect(k({ nganh: "米" })).toEqual(["1"]);
    expect(k({ tim: "nuoc mam" })).toEqual(["3"]);
    expect(k({ tim: "g01" })).toEqual(["1"]);
  });
  it("ngành so theo tên HIỂN THỊ (hai cách viết OBC là một ngành); ?ben= giữ nhóm có mặt hàng của bên đó (không tính khách kể)", () => {
    const d = [
      nh({ nhom_khoa: "x", nganh: "調味料_VNM", so_ben: 3, quan_sat: [qs({ ma_doi_thu: "a" })] }),
      nh({ nhom_khoa: "y", nganh: "調味料＿VNM", so_ben: 2, quan_sat: [qs({ ma_doi_thu: "b" })] }),
      nh({ nhom_khoa: "z", nganh: "冷凍食品_VNM", so_ben: 1, quan_sat: [qs({ ma_doi_thu: "b", loai_nguon: "khach_ke" })] }),
    ];
    const l = (o: { nganh?: string; ben?: string }) => locDanhSach(d, { nganh: "", tim: "", nhanh: "", ...o }).map(n => n.nhom_khoa);
    expect(l({ nganh: "調味料＿VNM" })).toEqual(["x", "y"]);
    expect(l({ ben: "b" })).toEqual(["y"]);
    expect(l({ ben: "b", nganh: "調味料_VNM" })).toEqual(["y"]);
  });
  it("nút nhanh", () => {
    expect(k({ nhanh: "dat" })).toEqual(["1", "2"]);
    expect(k({ nhanh: "het" })).toEqual(["2"]);
    expect(k({ nhanh: "thieu" })).toEqual(["3"]);
  });
});

describe("phụ trợ thành phần (task 6)", () => {
  it("soMatHang bỏ khách kể; pcDau; nhanKlGoi", () => {
    expect(soMatHang(mau())).toBe(8);
    expect([pcDau(12), pcDau(-8), pcDau(0), pcDau(null)]).toEqual(["+12%", "−8%", "0%", "—"]);
    expect([nhanKlGoi(250), nhanKlGoi(1000), nhanKlGoi(1500), nhanKlGoi(null)]).toEqual(["250 g", "1 kg", "1.5 kg", null]);
    expect(nhanKlGoi(333.3333)).toBe("333.3 g");
  });
  it("macDinhSp = 3 nhóm nhiều bên nhất (bỏ nhóm lệch); nhomChon giữ thứ tự sp", () => {
    const ds = [nh({ nhom_khoa: "a", so_ben: 1 }), nh({ nhom_khoa: "b", so_ben: 7 }), nh({ nhom_khoa: "c", so_ben: 3 }),
      nh({ nhom_khoa: "d", so_ben: 5 }), nh({ nhom_khoa: "x", so_ben: 99, gia_kome_lech: true })];
    expect(macDinhSp(ds)).toEqual(["b", "d", "c"]);
    expect(nhomChon(ds, ["c", "zz", "a"]).map(n => n.nhom_khoa)).toEqual(["c", "a"]);
  });
  it("batTat: tối đa 8", () => {
    expect(batTat(["a"], "b")).toEqual({ sp: ["a", "b"], day: false });
    expect(batTat(["a", "b"], "a")).toEqual({ sp: ["b"], day: false });
    const tam = ["1", "2", "3", "4", "5", "6", "7", "8"];
    expect(batTat(tam, "9")).toEqual({ sp: tam, day: true });
    expect(batTat(tam, "3").sp).toHaveLength(7);
  });
  it("matHangCuaBen: một bên, rẻ trước, bỏ khách kể, theo chiCung", () => {
    const n = nh({ quan_sat: [qs({ ten_goc: "A2", ten_doi_thu: "A", gia_1: 900, nhan: "cung_hang" }), qs({ ten_goc: "A1", ten_doi_thu: "A", gia_1: 300 }),
      qs({ ten_goc: "B", ten_doi_thu: "B", gia_1: 1 }), qs({ ten_goc: "K", ten_doi_thu: "A", gia_1: 1, loai_nguon: "khach_ke" })] });
    expect(matHangCuaBen(n, "A", { sl: "1", chiCung: false }).map(q => q.ten_goc)).toEqual(["A1", "A2"]);
    expect(matHangCuaBen(n, "A", { sl: "1", chiCung: true }).map(q => q.ten_goc)).toEqual(["A2"]);
  });
  it("giaBacKg = công thức mart.gia_bac_kg (067)", () => {
    const q = { kg_thung_dt: 10, kl_goi_g: 500, thue: "chua" };
    expect(giaBacKg({ tu: 5, don_vi_sl: "thung", gia: 5300, don_vi_gia: "thung" }, q)).toBe(530);
    expect(giaBacKg({ tu: 5, don_vi_sl: "thung", gia: 300, don_vi_gia: "goi" }, q)).toBe(600);
    expect(giaBacKg({ tu: 20, don_vi_sl: "kg", gia: 530, don_vi_gia: "kg" }, q)).toBe(530);
    expect(giaBacKg({ tu: 20, don_vi_sl: "kg", gia: 540, don_vi_gia: "kg" }, { ...q, thue: "co" })).toBeCloseTo(500);
    expect(giaBacKg({ tu: 5, don_vi_sl: "thung", gia: 5300, don_vi_gia: "thung" }, { ...q, kg_thung_dt: null })).toBeNull();
    expect(nhanBac({ tu: 24, don_vi_sl: "kg", gia: 1, don_vi_gia: "kg" })).toBe("từ 24 kg");
    expect(nhanBac({ tu: 5, don_vi_sl: "thung", gia: 1, don_vi_gia: "kg" })).toBe("từ 5 thùng");
    expect(nhanBac({ tu: 1, don_vi_sl: "pallet", gia: 1, don_vi_gia: "kg" })).toBe("giá pallet");
  });
  it("bangBac: không bậc → một dòng 'mọi số lượng' tô đậm", () => {
    const r = bangBac(qs({ yen_chuan: 600, gia_1: 600, kg_thung_dt: 10 }), "5", 500);
    expect(r.coBac).toBe(false); expect(r.toiThieu).toBeNull();
    expect(r.dong).toEqual([{ nhan: "mọi số lượng", kg: 600, goi: 300, thung: 6000, p: 20, dang: true, re: false }]);
  });
  it("bangBac: bậc áp dụng tô đậm theo giá máy chủ; rẻ hơn dòng trên; đặt tối thiểu", () => {
    const bac = [{ tu: 20, don_vi_sl: "kg" as const, gia: 530, don_vi_gia: "kg" as const },
                 { tu: 40, don_vi_sl: "kg" as const, gia: 510, don_vi_gia: "kg" as const }];
    const q = qs({ yen_chuan: 530, gia_1: 530, gia_5: 510, gia_10: 510, kg_thung_dt: 10, bac });
    const a = bangBac(q, "1", 500);
    expect(a.dong.map(d => d.nhan)).toEqual(["giá lẻ", "từ 20 kg", "từ 40 kg"]);
    expect(a.dong.map(d => d.dang)).toEqual([true, false, false]);
    expect(a.dong.map(d => d.re)).toEqual([false, false, true]);
    expect(a.toiThieu).toBe("20 kg");
    expect(bangBac(q, "5", 500).dong.map(d => d.dang)).toEqual([false, false, true]);
    // Bậc đầu rẻ hơn giá lẻ = giảm giá, không phải đặt tối thiểu.
    const q2 = qs({ yen_chuan: 550, gia_1: 550, gia_5: 530, kg_thung_dt: 10,
      bac: [{ tu: 5, don_vi_sl: "thung", gia: 5300, don_vi_gia: "thung" }] });
    expect(bangBac(q2, "5", 500).toiThieu).toBeNull();
    expect(bangBac(q2, "5", 500).dong[1]).toMatchObject({ kg: 530, thung: 5300, dang: true, re: true, p: 6 });
  });
});
