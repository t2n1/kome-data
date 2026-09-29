import { describe, expect, it } from "vitest";
import type { Ben, Nhom, QuanSat, TongQuan } from "./kieu";
import { bongNganh, coHoi, datNhat, diemVitri, goiY, kmGomBen, kmNoiBat, kmTheoBen, mauTT, nganhObc, nhomCuaO, reNhat, SO_COT, tiLe,
  tongSo } from "./tom_tat_logic";

let seq = 0;
const nh = (o: Partial<Nhom> = {}): Nhom => ({
  nhom_khoa: `ma:K${++seq}`, ten_nhom: `Nhóm ${seq}`, nganh: "調味料_VNM", don_vi_so: "kg", ma_kome: [`K${seq}`], gia_kome: 500,
  so_ben: 2, thap_nhat: 400, ben_thap_nhat: "a", trung_vi: 500, cao_nhat: 600, ty_le_re_hon_kome: null, quan_sat: [],
  gia_kome_chuan: 500, gia_kome_bang: null, gia_kome_km: null, gia_kome_so: 500, lech_trung_vi: 0, gia_kome_lech: false,
  kome_kg_goi: null, kome_goi_thung: null, kome_kg_thung: null, ...o,
});
const qs = (o: Partial<QuanSat>) => ({ ma_doi_thu: "a", ten_doi_thu: "Bên A", nguon: "nap", id: ++seq, loai_nguon: "bang_gia",
  ...o } as unknown as QuanSat);
const ben = (ma: string, ten = ma.toUpperCase()): Ben => ({ ma, ten, web: null, ngay_moi: null, hinh_thuc: null, so_dong: 0, cho_duyet: 0 });
type Het = TongQuan["het_hang"][number];
const het = (o: Partial<Het>): Het => ({ nguon: "nap", id: ++seq, ma_hang_dt: `h${seq}`, ma_doi_thu: "a", ten_doi_thu: "Bên A",
  ben: "a", ten_goc: "x", ma_kome: "K1", ten_nhom: "Gạo", trang_thai: "het", ...o });
type Km = TongQuan["khuyen_mai"][number];
const km = (o: Partial<Km>): Km => ({ nguon: "nap", id: ++seq, ma_hang_dt: `h${seq}`, ma_doi_thu: "a", ben: "a", ten_goc: "x",
  gia_goc: null, gia_truoc_km: null, khuyen_mai: null, ngay: "2026-09-01", ...o });
const tq = (o: Partial<TongQuan> = {}): TongQuan => ({ ben: [], luoi: [], khuyen_mai: [], dieu_kien: [], het_hang: [], ...o });

describe("tongSo", () => {
  it("coGia chỉ nhóm kg có giá KOME và không lệch; datHon > 5%; maHet đếm mã khác nhau 'het'; km + số bên", () => {
    const ss = [
      nh({ lech_trung_vi: 0.2 }), nh({ lech_trung_vi: 0.05 }), nh({ lech_trung_vi: 0.06 }), nh({ lech_trung_vi: -0.3 }),
      nh({ lech_trung_vi: 5, gia_kome_lech: true }),            // lệch — không đếm
      nh({ don_vi_so: "goi", lech_trung_vi: 0.5 }),             // không phải kg
      nh({ gia_kome_so: null, lech_trung_vi: null }),           // KOME không bán
    ];
    const t = tq({
      het_hang: [het({ ma_kome: "K1" }), het({ ma_kome: "K1", ma_doi_thu: "b" }), het({ ma_kome: "K2" }),
        het({ ma_kome: "K3", trang_thai: "sap_ve" })],
      khuyen_mai: [km({ ben: "a" }), km({ ben: "a" }), km({ ben: "b" })],
    });
    expect(tongSo(ss, t)).toEqual({ coGia: 4, datHon: 2, maHet: 2, km: 3, soBenKm: 2 });
  });
});

describe("tiLe", () => {
  it("rẻ / ngang / đắt trên nhóm có giá; không bán = gia_kome_so null; lệch đếm riêng; tổng = mọi dòng", () => {
    const ss = [nh({ lech_trung_vi: -0.2 }), nh({ lech_trung_vi: -0.04 }), nh({ lech_trung_vi: 0.051 }), nh({ lech_trung_vi: 0.05 }),
      nh({ gia_kome_so: null, lech_trung_vi: null }), nh({ gia_kome_so: null, lech_trung_vi: null, don_vi_so: "goi" }),
      nh({ lech_trung_vi: 4, gia_kome_lech: true })];
    expect(tiLe(ss)).toEqual({ re: 1, ngang: 2, dat: 1, khongBan: 2, lech: 1, tong: 7 });
  });
  it("lệch đếm nhom_khoa khác nhau, không đếm dòng (một nhóm nhiều đơn vị so)", () => {
    const ss = [nh({ nhom_khoa: "n:1", gia_kome_lech: true, lech_trung_vi: 4 }),
      nh({ nhom_khoa: "n:1", don_vi_so: "goi", gia_kome_lech: true, lech_trung_vi: 4 }), nh({ gia_kome_lech: true, lech_trung_vi: 5 })];
    expect(tiLe(ss).lech).toBe(2);
  });
});

describe("mauTT", () => {
  it("màu từ lech CHƯA làm tròn: 5,1% là đỏ (khớp danh sách đắt nhất) dù in ra +5%", () => {
    expect(mauTT(nh({ lech_trung_vi: 0.051 }))).toBe("do");
    expect(mauTT(nh({ lech_trung_vi: -0.051 }))).toBe("xanh");
    expect(mauTT(nh({ lech_trung_vi: 0.05 }))).toBe("xam");
    expect(mauTT(nh({ lech_trung_vi: null }))).toBe("xam");
  });
});

describe("diemVitri", () => {
  it("p làm tròn và kẹp [−60, 70]; cột theo SO_COT; tầng = thứ tự trong cột; bỏ nhóm lệch / không kg / không giá", () => {
    const a = nh({ lech_trung_vi: -0.9 }), b = nh({ lech_trung_vi: 1.5 }), c = nh({ lech_trung_vi: 0.1 }),
      d = nh({ lech_trung_vi: 0.1004 }), e = nh({ lech_trung_vi: 0.0996 });
    const r = diemVitri([b, nh({ gia_kome_lech: true, lech_trung_vi: 0.1 }), nh({ don_vi_so: "goi", lech_trung_vi: 0.1 }),
      nh({ gia_kome_so: null, lech_trung_vi: null }), c, a, d, e]);
    expect(r.map(x => x.nhom)).toEqual([a, e, c, d, b]);
    expect(r.find(x => x.nhom === a)!.p).toBe(-60);
    expect(r.find(x => x.nhom === a)!.cot).toBe(0);
    expect(r.find(x => x.nhom === b)!.p).toBe(70);
    expect(r.find(x => x.nhom === b)!.cot).toBe(SO_COT);
    const cot10 = Math.round(70 / 130 * SO_COT);
    expect(r.filter(x => x.p === 10).map(x => [x.cot, x.tang])).toEqual([[cot10, 0], [cot10, 1], [cot10, 2]]);
  });
  it("hai p khác nhau rơi cùng cột thì xếp tầng tiếp nhau", () => {
    // SO_COT < 130 nên có hai % liền nhau chung một cột
    const ps = Array.from({ length: 131 }, (_, i) => i - 60);
    const r = diemVitri(ps.map(p => nh({ lech_trung_vi: p / 100 })));
    const trung = r.find((x, i) => i > 0 && x.cot === r[i - 1].cot)!;
    expect(trung.tang).toBe(1);
  });
});

describe("datNhat / reNhat", () => {
  const ss = [nh({ lech_trung_vi: 0.3 }), nh({ lech_trung_vi: 0.05 }), nh({ lech_trung_vi: 0.9 }), nh({ lech_trung_vi: 0.051 }),
    nh({ lech_trung_vi: 3, gia_kome_lech: true }), nh({ lech_trung_vi: -0.2 }), nh({ lech_trung_vi: -0.05 }),
    nh({ lech_trung_vi: -0.5 }), nh({ gia_kome_so: null, lech_trung_vi: null })];
  it("đắt nhất: chỉ > 5%, giảm dần, bỏ nhóm lệch", () => {
    expect(datNhat(ss).map(n => n.lech_trung_vi)).toEqual([0.9, 0.3, 0.051]);
    expect(datNhat(ss, 1).map(n => n.lech_trung_vi)).toEqual([0.9]);
  });
  it("rẻ nhất: chỉ < −5%, tăng dần", () => {
    expect(reNhat(ss).map(n => n.lech_trung_vi)).toEqual([-0.5, -0.2]);
  });
});

describe("coHoi", () => {
  it("gộp 'het' theo mã KOME, một bên một chip, xếp số bên giảm dần, cắt n", () => {
    const t = tq({ het_hang: [
      het({ ma_kome: "K1", ten_nhom: "Gạo", ma_doi_thu: "a", ten_doi_thu: "Bên A", nguon: "nap", id: 1 }),
      het({ ma_kome: "K2", ten_nhom: null, ma_doi_thu: "a", ten_doi_thu: null, nguon: "tay", id: 2 }),
      het({ ma_kome: "K2", ten_nhom: null, ma_doi_thu: "b", ten_doi_thu: "Bên B", id: 3 }),
      het({ ma_kome: "K2", ten_nhom: null, ma_doi_thu: "b", ten_doi_thu: "Bên B", id: 4 }),   // cùng bên — một chip
      het({ ma_kome: "K3", ma_doi_thu: "c", trang_thai: "sap_ve", id: 5 }),                    // sắp về — không phải cơ hội
    ] });
    const r = coHoi(t);
    expect(r.map(x => x.ma_kome)).toEqual(["K2", "K1"]);
    expect(r[0]).toEqual({ ma_kome: "K2", ten: "K2", ben: [{ ma: "a", ten: "a", nguon: "tay", id: 2 }, { ma: "b", ten: "Bên B", nguon: "nap", id: 3 }] });
    expect(r[1].ten).toBe("Gạo");
    expect(coHoi(t, 1)).toHaveLength(1);
  });
});

describe("bongNganh / nganhObc", () => {
  const t = tq({
    ben: [ben("a"), ben("b"), ben("c")],
    luoi: [
      { ben: "a", nganh: "調味料_VNM", so_ma: 5 }, { ben: "a", nganh: "調味料＿VNM", so_ma: 2 },   // cùng tên hiển thị → gộp
      { ben: "b", nganh: "飲料（アルコール以外）_THA", so_ma: 20 }, { ben: "b", nganh: "調味料_VNM", so_ma: 1 },
      { ben: "x", nganh: "調味料_VNM", so_ma: 99 },   // bên không theo dõi — bỏ
    ],
  });
  it("gộp theo tenNganh, ngành và bên xếp theo tổng giảm dần; bên không có ô vẫn có dòng", () => {
    const r = bongNganh(t);
    expect(r.nganh).toEqual(["Nước uống (Thái)", "Gia vị"]);
    expect(r.ben.map(b => b.ma)).toEqual(["b", "a", "c"]);
    expect(r.o.get("a|Gia vị")).toBe(7);
    expect(r.o.get("b|Nước uống (Thái)")).toBe(20);
    expect(r.o.has("c|Gia vị")).toBe(false);
  });
  it("tên OBC đại diện của một ngành hiển thị = tên có nhiều mã nhất (của bên đó nếu cho)", () => {
    expect(nganhObc(t, "Gia vị")).toBe("調味料_VNM");
    expect(nganhObc(t, "Gia vị", "a")).toBe("調味料_VNM");
    expect(nganhObc(t, "Không có")).toBe("");
  });
});

describe("nhomCuaO", () => {
  it("nhóm của một ô bóng: cùng ngành hiển thị, có mặt hàng của bên, nhiều bên trước, bỏ khách kể", () => {
    const g1 = nh({ nganh: "調味料_VNM", so_ben: 2, quan_sat: [qs({ ma_doi_thu: "a" })] });
    const g2 = nh({ nganh: "調味料＿VNM", so_ben: 5, quan_sat: [qs({ ma_doi_thu: "a" })] });
    const g3 = nh({ nganh: "調味料_VNM", so_ben: 9, quan_sat: [qs({ ma_doi_thu: "b" })] });
    const g4 = nh({ nganh: "調味料_VNM", so_ben: 9, quan_sat: [qs({ ma_doi_thu: "a", loai_nguon: "khach_ke" })] });
    const g5 = nh({ nganh: "冷凍食品_VNM", quan_sat: [qs({ ma_doi_thu: "a" })] });
    expect(nhomCuaO([g1, g2, g3, g4, g5], "Gia vị", "a")).toEqual([g2.nhom_khoa, g1.nhom_khoa]);
    expect(nhomCuaO([g1, g2, g3], "Gia vị", "a", 1)).toEqual([g2.nhom_khoa]);
  });
});

describe("kmTheoBen / kmNoiBat", () => {
  const t = tq({ ben: [ben("a", "An"), ben("b", "Bình")], khuyen_mai: [
    km({ ben: "a" }), km({ ben: "a" }), km({ ben: "b" }), km({ ben: "z" }), km({ ben: "z" }), km({ ben: "z" }),
  ] });
  it("đếm theo bên, nhiều trước, tên từ tq.ben (không có thì mã), cắt n", () => {
    expect(kmTheoBen(t)).toEqual([{ ma: "z", ten: "z", so: 3 }, { ma: "a", ten: "An", so: 2 }, { ma: "b", ten: "Bình", so: 1 }]);
    expect(kmTheoBen(t, 1)).toHaveLength(1);
  });
  it("nổi bật: có gia_truoc_km > gia_goc, giảm nhiều (theo %) trước", () => {
    const a = km({ gia_goc: 90, gia_truoc_km: 100 }), b = km({ gia_goc: 50, gia_truoc_km: 100 }),
      c = km({ gia_goc: 100, gia_truoc_km: 100 }), d = km({ gia_goc: null, gia_truoc_km: 100 }), e = km({ khuyen_mai: "1+1" });
    expect(kmNoiBat(tq({ khuyen_mai: [a, b, c, d, e] }))).toEqual([b, a]);
  });
});

describe("goiY", () => {
  const ss = [nh({ nhom_khoa: "n:1", ten_nhom: "Nước mắm Phú Quốc", ma_kome: ["BA09"] }),
    nh({ nhom_khoa: "n:1", ten_nhom: "Nước mắm Phú Quốc", don_vi_so: "goi" }),   // cùng nhóm, đơn vị khác — một gợi ý
    nh({ nhom_khoa: "ma:BA10", ten_nhom: "Nuoc mam chay", ma_kome: ["BA10"] }), nh({ ten_nhom: "Gạo" })];
  const bs = [ben("hsc", "HSC Station"), ben("mam", "Mắm Việt")];
  it("bỏ dấu, tìm cả mã; bên trước (≤ 3), rồi nhóm; tối đa n; rỗng khi chưa gõ", () => {
    expect(goiY(ss, bs, "")).toEqual([]);
    const r = goiY(ss, bs, "mam");
    expect(r.map(x => x.loai + ":" + x.khoa)).toEqual(["ben:mam", "nhom:n:1", "nhom:ma:BA10"]);
    expect(goiY(ss, bs, "ba09").map(x => x.khoa)).toEqual(["n:1"]);
    expect(goiY(ss, bs, "hsc")[0]).toEqual({ loai: "ben", khoa: "hsc", ten: "HSC Station", phu: "hsc" });
    expect(goiY(ss, bs, "m", 2)).toHaveLength(2);
  });
});

describe("kmGomBen", () => {
  it("gom theo bên, bên nhiều trước; trong bên: giảm % lớn trước, rồi tên; tên bên từ tq.ben", () => {
    const t = tq({ ben: [ben("a", "An"), ben("b", "Bình")], khuyen_mai: [
      km({ ben: "b", ten_goc: "z" }),
      km({ ben: "a", ten_goc: "c" }), km({ ben: "a", ten_goc: "b", gia_goc: 90, gia_truoc_km: 100 }),
      km({ ben: "a", ten_goc: "a" }), km({ ben: "a", ten_goc: "d", gia_goc: 50, gia_truoc_km: 100 }),
      km({ ben: "x", ten_goc: "q" }), km({ ben: "x", ten_goc: "r" }),
    ] });
    const r = kmGomBen(t);
    expect(r.map(x => [x.ma, x.ten, x.ds.length])).toEqual([["a", "An", 4], ["x", "x", 2], ["b", "Bình", 1]]);
    expect(r[0].ds.map(k => k.ten_goc)).toEqual(["d", "b", "a", "c"]);
  });
  it("không khuyến mãi thì rỗng", () => expect(kmGomBen(tq())).toEqual([]));
});
