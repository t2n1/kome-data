import { describe, expect, it } from "vitest";
import type { Ben, GiaoHang, TongQuan } from "./kieu";
import { benMacDinh, chipBen, daBoCuaBen, dauBen, dongSoKome, giaoTrong, lichSuThang, nganhBen, ngoaiBieuDo, o4, soMaTrung, thuGon, tomTatGiao,
  type QsHs }
  from "./ho_so_logic";

let seq = 0;
const q = (o: Partial<QsHs> = {}): QsHs => ({ ma_doi_thu: "a", ten_doi_thu: "Bên A", nguon: "nap", id: ++seq, ma_hang_dt: `h${seq}`, mat_hang_khoa: `h${seq}`, an: false,
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

describe("giá KOME lệch / chưa so được / thu gọn", () => {
  it("nhóm gia_kome_lech không lên biểu đồ, không vào 4 ô; đếm riêng; chưa so = không có gia_kome_so", () => {
    const qs = [q({ yen_chuan: 5, gia_kome_so: 5000, gia_kome_lech: true }), q({ yen_chuan: 5, gia_kome_so: 5000, gia_kome_lech: true }),
      q({ yen_chuan: 80 }), q({ gia_kome_so: null }), q({ gia_kome_so: null, hien_hanh: false }),
      q({ gia_kome_so: null, loai_nguon: "khach_ke" }), q({ gia_kome_lech: true, hien_hanh: false })];
    expect(dongSoKome(qs).map(d => d.p)).toEqual([-20]);
    expect(o4(qs)).toMatchObject({ trung: 1, reHon: 1 });
    expect(ngoaiBieuDo(qs)).toEqual({ lech: 2, chuaSo: 1 });
  });
  it("thu gọn: giữ n dòng |p| lớn nhất theo thứ tự cũ, p null sau cùng; ít hơn n thì giữ hết", () => {
    const d = [-50, -3, null, 2, 40, 10].map(p => ({ p }));
    expect(thuGon(d, 3)).toEqual({ hien: [{ p: -50 }, { p: 40 }, { p: 10 }], an: 3 });
    expect(thuGon(d, 6)).toEqual({ hien: d, an: 0 });
    expect(thuGon([{ p: null }, { p: 1 }], 1).hien).toEqual([{ p: 1 }]);
  });
});


describe("daBoCuaBen (B15)", () => {
  it("chỉ dòng hiện hành có bo_nhom, theo tên nhóm rồi tên hàng", () => {
    const ds = daBoCuaBen([
      q({ ten_goc: "b", sua_cuoi: 5, bo_nhom: { nhom_khoa: "ma:X", ten_nhom: "Xoài", nhan_cu: "cung_hang" } }),
      q({ ten_goc: "a", sua_cuoi: 2, bo_nhom: { nhom_khoa: "n:1", ten_nhom: "Cá", nhan_cu: "thay_the" } }),
      q({ ten_goc: "c", hien_hanh: false, bo_nhom: { nhom_khoa: "n:1", ten_nhom: "Cá", nhan_cu: "thay_the" } }),
      q({ ten_goc: "d", bo_nhom: null }),
    ]);
    expect(ds.map(x => [x.ten_goc, x.nhom_khoa, x.nhan_cu, x.sua_cuoi])).toEqual([["a", "n:1", "thay_the", 2], ["b", "ma:X", "cung_hang", 5]]);
  });
});

describe("giá bất thường trên tab Đối thủ (B18)", () => {
  const qs = [
    q({ yen_chuan: 1, bat_thuong: true, moc_bat_thuong: 454, moc_bat_thuong_la: "kome", ten_goc: "chỗ giữ ¥1" }),
    q({ yen_chuan: 3, bat_thuong: true, gia_kome_so: null, nhom_khoa: "ma:X", ten_goc: "nhóm chỉ còn bất thường" }),
    q({ yen_chuan: 3, bat_thuong: true, gia_kome_so: null, nhom_khoa: null, ten_goc: "chưa ghép" }),
    q({ yen_chuan: 80, ten_goc: "rẻ thật" }), q({ yen_chuan: 120, ten_goc: "đắt" }),
  ];
  it("vẽ (xám, p null, không '?' trỏ ô) và xếp CUỐI — kể cả khi nhóm không còn giá KOME; chưa ghép thì không vẽ", () => {
    const d = dongSoKome(qs);
    expect(d.map(x => [x.q.ten_goc, x.p, x.bt, x.tro])).toEqual([
      ["rẻ thật", -20, false, undefined], ["đắt", 20, false, undefined],
      ["chỗ giữ ¥1", null, true, undefined], ["nhóm chỉ còn bất thường", null, true, undefined]]);
  });
  it("không vào ô số: trùng / rẻ hơn KOME chỉ đếm dòng thường", () =>
    expect(o4(qs)).toEqual({ trung: 2, reHon: 1, het: 0, km: 0 }));
  it("không bị đếm là 'chưa so được' khi đã vẽ; dòng chưa ghép vẫn đếm", () =>
    expect(ngoaiBieuDo(qs)).toEqual({ lech: 0, chuaSo: 1 }));
  it("thu gọn giữ bất thường sau cùng (dù |p| giả của nó lớn nhất)", () => {
    const d = [{ p: -99, bt: true }, { p: 5 }, { p: null }, { p: -30 }];
    expect(thuGon(d, 2).hien).toEqual([{ p: 5 }, { p: -30 }]);
    expect(thuGon(d, 3).hien).toEqual([{ p: 5 }, { p: null }, { p: -30 }]);
  });
});

describe("070 — mỗi mặt hàng một thanh", () => {
  it("hai dòng hiện hành cùng mặt hàng (một dai_dien: false) chỉ ra MỘT thanh, một dòng ở o4 / đếm", () => {
    const a = q({ mat_hang_khoa: "m1", dai_dien: true, yen_chuan: 90 } as Partial<QsHs>);
    const b = q({ mat_hang_khoa: "m1", dai_dien: false, yen_chuan: 95 } as Partial<QsHs>);
    expect(dongSoKome([a, b]).map(d => d.q.id)).toEqual([a.id]);
    expect(o4([a, b]).trung).toBe(1);
    expect(dauBen([a, b]).soDong).toBe(1);
    expect(ngoaiBieuDo([a, b])).toEqual({ lech: 0, chuaSo: 0 });
  });
  it("dòng lịch sử (hien_hanh false) không bị cờ đại diện ảnh hưởng", () => {
    expect(lichSuThang([q({ ma_hang_dt: "x", dai_dien: false, yen_chuan: 5, ngay_nguon: "2026-07-01" } as Partial<QsHs>),
      q({ ma_hang_dt: "x", dai_dien: false, yen_chuan: 6, ngay_nguon: "2026-08-01" } as Partial<QsHs>)],
      q({ ma_hang_dt: "x" }))).toHaveLength(2);
  });
});
