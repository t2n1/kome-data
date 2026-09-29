import { describe, expect, it } from "vitest";
import type { Ben, GiaoHang, TongQuan } from "./kieu";
import { benMacDinh, chipBen, dauBen, dongSoKome, giaoTrong, lichSuThang, nganhBen, o4, soMaTrung, tomTatGiao, type QsHs }
  from "./ho_so_logic";

let seq = 0;
const q = (o: Partial<QsHs> = {}): QsHs => ({ ma_doi_thu: "a", ten_doi_thu: "Bên A", nguon: "nap", id: ++seq, ma_hang_dt: `h${seq}`,
  ngay_nguon: "2026-08-01", hinh_thuc_nguon: "file", nguon_file: "a.xlsx", loai_nguon: "bang_gia", ten_goc: `hàng ${seq}`,
  ten_nhom: `Nhóm ${seq}`, nhan: "thay_the", trang_thai: "con", khuyen_mai: null, gia_truoc_km: null, tuoi_ngay: 10, thue: "chua",
  gom_ship: "khong", kenh_gia: null, muc_gia: null, don_vi_so: "kg", gia_goc: 100, yen_chuan: 100, gia_kome_so: 100,
  hien_hanh: true, web_ben: null, ...o } as unknown as QsHs);
const ben = (ma: string, so_dong = 0, ten = ma.toUpperCase()): Ben =>
  ({ ma, ten, web: null, ngay_moi: null, hinh_thuc: null, so_dong, cho_duyet: 0 });
const tq = (o: Partial<TongQuan> = {}): TongQuan => ({ ben: [], luoi: [], khuyen_mai: [], dieu_kien: [], het_hang: [], ...o });

describe("soMaTrung / chipBen / benMacDinh", () => {
  const t = tq({ ben: [ben("a", 50), ben("b", 10), ben("c", 99)], luoi: [
    { ben: "a", nganh: "調味料_VNM", so_ma: 3 }, { ben: "b", nganh: "調味料_VNM", so_ma: 4 }, { ben: "b", nganh: "冷凍食品_VNM", so_ma: 2 },
    { ben: "zz", nganh: "調味料_VNM", so_ma: 40 },   // bên không theo dõi: bỏ
  ] });
  it("cộng so_ma theo bên; bên không có lưới = 0; bên ngoài tq.ben bỏ", () =>
    expect([...soMaTrung(t)]).toEqual([["a", 3], ["b", 6], ["c", 0]]));
  it("chip: nhiều mặt hàng trùng trước, hoà thì nhiều dòng", () => {
    expect(chipBen(t).map(x => [x.ma, x.so])).toEqual([["b", 6], ["a", 3], ["c", 0]]);
    expect(benMacDinh(t)).toBe("b");
  });
  it("mọi bên 0 mặt hàng trùng thì nhiều dòng hiện hành nhất; không bên nào thì chuỗi rỗng", () => {
    expect(benMacDinh(tq({ ben: [ben("a", 5), ben("c", 9)] }))).toBe("c");
    expect(benMacDinh(tq())).toBe("");
  });
});

describe("dongSoKome / o4", () => {
  it("chỉ hiện hành + có gia_kome_so + không khách kể; p = % yen_chuan so KOME; xếp p tăng, p null cuối", () => {
    const qs = [
      q({ yen_chuan: 130, ten_goc: "đắt" }), q({ yen_chuan: 80, ten_goc: "rẻ" }), q({ yen_chuan: null, ten_goc: "thiếu" }),
      q({ yen_chuan: 96, ten_goc: "ngang" }),
      q({ hien_hanh: false, yen_chuan: 10 }), q({ gia_kome_so: null }), q({ loai_nguon: "khach_ke", yen_chuan: 10 }),
    ];
    const d = dongSoKome(qs);
    expect(d.map(x => [x.q.ten_goc, x.p])).toEqual([["rẻ", -20], ["ngang", -4], ["đắt", 30], ["thiếu", null]]);
    expect(d[3].tro).toBe("kl_goi_g");
    expect(dongSoKome([q({ yen_chuan: null, gia_goc: null })])[0].tro).toBe("gia_goc");
    const x = q();
    expect(dongSoKome([x, { ...x }])).toHaveLength(1);
  });
  it("cờ: cùng thương hiệu, hết, KM (ghi chú hoặc giá trước KM), cũ > 60 ngày, thuế không rõ, gồm ship", () => {
    const [d] = dongSoKome([q({ nhan: "cung_hang", trang_thai: "het", gia_truoc_km: 120, tuoi_ngay: 61, thue: "khong_ro", gom_ship: "co" })]);
    expect([d.cung, d.het, d.km, d.cu, d.thueKhongRo, d.gomShip]).toEqual([true, true, true, true, true, true]);
    const [e] = dongSoKome([q({ khuyen_mai: "  ", tuoi_ngay: 60 })]);
    expect([e.km, e.cu]).toEqual([false, false]);
  });
  it("4 ô: trùng · rẻ hơn > 5% (−5 không tính) · hết trong dòng trùng · KM mọi dòng hiện hành không khách kể", () => {
    const qs = [q({ yen_chuan: 94 }), q({ yen_chuan: 95 }), q({ yen_chuan: 120, trang_thai: "het" }),
      q({ gia_kome_so: null, trang_thai: "het", khuyen_mai: "SALE" }), q({ hien_hanh: false, khuyen_mai: "SALE" }),
      q({ loai_nguon: "khach_ke", khuyen_mai: "SALE" })];
    expect(o4(qs)).toEqual({ trung: 3, reHon: 1, het: 1, km: 1 });
  });
});

describe("lichSuThang", () => {
  it("cùng hàng + kênh + mức + đơn vị so; mỗi tháng lấy ngày mới nhất; tháng tăng dần", () => {
    const x = q({ ma_hang_dt: "H", ngay_nguon: "2026-08-20", yen_chuan: 110 });
    const qs = [x, q({ ma_hang_dt: "H", ngay_nguon: "2026-08-02", yen_chuan: 999, hien_hanh: false }),
      q({ ma_hang_dt: "H", ngay_nguon: "2026-06-10", yen_chuan: 100, hien_hanh: false }),
      q({ ma_hang_dt: "H", ngay_nguon: "2026-07-10", yen_chuan: null, hien_hanh: false }),
      q({ ma_hang_dt: "H", ngay_nguon: "2026-05-10", yen_chuan: 1, kenh_gia: "si", hien_hanh: false }),
      q({ ma_hang_dt: "K", ngay_nguon: "2026-04-10", yen_chuan: 1, hien_hanh: false })];
    expect(lichSuThang(qs, x)).toEqual([{ thang: "2026-06", gia: 100 }, { thang: "2026-08", gia: 110 }]);
  });
  it("một tháng thì rỗng (không vẽ)", () => {
    const x = q({ ma_hang_dt: "H" });
    expect(lichSuThang([x, q({ ma_hang_dt: "H", ngay_nguon: "2026-08-05" })], x)).toEqual([]);
  });
});

describe("nganhBen", () => {
  it("gộp hai cách viết OBC về một tên hiển thị; chỉ bên đó; nhiều trước", () => {
    const t = tq({ luoi: [{ ben: "a", nganh: "飲料（アルコール以外）_VNM", so_ma: 2 }, { ben: "a", nganh: "飲料（アルコール以外）＿VNM", so_ma: 3 },
      { ben: "a", nganh: "調味料_VNM", so_ma: 7 }, { ben: "b", nganh: "調味料_VNM", so_ma: 9 }] });
    expect(nganhBen(t, "a")).toEqual([{ nganh: "Gia vị", so: 7 }, { nganh: "Nước uống", so: 5 }]);
  });
});

describe("dauBen", () => {
  it("ngày mới nhất của dòng nạp hiện hành; số dòng hiện hành không khách kể; file thì tìm trong Drive", () => {
    const r = dauBen([q({ ngay_nguon: "2026-08-03", nguon_file: "cu.xlsx" }), q({ ngay_nguon: "2026-08-21", nguon_file: "moi.xlsx" }),
      q({ nguon: "tay", ngay_nguon: "2026-09-01" }), q({ loai_nguon: "khach_ke" }), q({ hien_hanh: false, ngay_nguon: "2026-09-09" })]);
    expect(r.ngay).toBe("2026-08-21");
    expect(r.soDong).toBe(3);
    expect(r.nguon?.href).toContain("moi.xlsx");
  });
  it("web thì trang của bên (chỉ https); không có dòng thì null", () => {
    expect(dauBen([q({ hinh_thuc_nguon: "web", web_ben: "https://x.jp" })]).nguon?.href).toBe("https://x.jp");
    expect(dauBen([q({ hinh_thuc_nguon: "web", web_ben: "javascript:alert(1)" })]).nguon).toBeNull();
    expect(dauBen([])).toEqual({ ngay: null, soDong: 0, nguon: null });
  });
});

describe("giaoTrong / tomTatGiao", () => {
  it("dòng rỗng: mọi trường null, ma_doi_thu = bên, sua_cuoi 0", () => {
    const g = giaoTrong("a", "An");
    expect(g.ma_doi_thu).toBe("a");
    expect([g.suy, g.da_xac_nhan, g.sua_cuoi, g.phi_ship, g.bao_ship]).toEqual([false, false, 0, null, null]);
    expect(tomTatGiao(g).map(x => x.chu)).toEqual([null, null, null]);
    expect(tomTatGiao(null).map(x => x.tru_o)).toEqual(["phi_ship", "mien_ship_tu", "phi_daibiki"]);
  });
  it("phí ship theo đơn vị, miễn từ ¥ hoặc kiện, daibiki kèm mức giảm", () => {
    const g: GiaoHang = { ...giaoTrong("a", null), phi_ship: 800, phi_ship_theo: "thung", mien_ship_kien: 3, phi_daibiki: 330,
      daibiki_tu: 30000, daibiki_sau: 0 };
    expect(tomTatGiao(g).map(x => x.chu)).toEqual(["¥800/thùng", "từ 3 kiện", "¥330 (từ ¥30,000: miễn)"]);
  });
  it("bao ship thì bỏ phần miễn ship", () => {
    expect(tomTatGiao({ ...giaoTrong("a", null), bao_ship: true }).map(x => x.nhan)).toEqual(["ship", "daibiki"]);
  });
});
