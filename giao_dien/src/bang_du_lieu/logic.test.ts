import { afterEach, describe, expect, it, vi } from "vitest";
import type { Cot, Dong, Lech } from "./kieu";
import { cotMacDinh, dan, datO, docCotDaChon, ghiCotDaChon, giaTri, hienThi, khoaO, khungNhin, kiemO, locDong, loiCho,
  suaDuocO, tachO, thanLuu } from "./logic";

const cot = (ma: string, kieu: Cot["kieu"], sua = true, chon?: [string, string][]): Cot =>
  ({ ma, nhan: ma, nhom: "x", kieu, sua, ...(chon ? { chon } : {}) });
const TEN = cot("product_name", "chu"), SL = cot("ton:0001", "so"), GIA = cot("gia:02|01", "so"),
  HAN = cot("han:0001", "ngay"), HANG = cot("rank_code", "chon", true, [["0001", "S"], ["0002", "A"]]),
  CHI = cot("dt_12t", "so", false);
const d = (k: string, o: Record<string, string | null>): Dong => ({ k, o });

describe("khoaO / tachO / giaTri", () => {
  it("khoá khứ hồi, tab trong khoá", () => {
    expect(khoaO("A1", "gia:02|01")).toBe("A1\tgia:02|01");
    expect(tachO("A1\tgia:02|01")).toEqual(["A1", "gia:02|01"]);
  });
  it("chữ đang gõ thắng; thiếu khoá → null", () => {
    const x = d("A", { product_name: "gốc" });
    expect(giaTri(x, "product_name", {})).toBe("gốc");
    expect(giaTri(x, "product_name", { [khoaO("A", "product_name")]: "" })).toBe("");
    expect(giaTri(x, "dt_12t", {})).toBeNull();
  });
});

describe("hienThi", () => {
  it("số theo chuẩn Nhật, tiền có ¥, chọn theo tên, ngày giữ ISO", () => {
    expect(hienThi(SL, "1234.5000")).toBe("1,234.5");
    expect(hienThi(GIA, "1200")).toBe("¥1,200");
    expect(hienThi(HANG, "0002")).toBe("A");
    expect(hienThi(HANG, "9999")).toBe("9999");
    expect(hienThi(HAN, "2026-12-31")).toBe("2026-12-31");
    expect(hienThi(SL, null)).toBe("");
  });
});

describe("kiemO", () => {
  it("chữ: trim", () => expect(kiemO(TEN, "  Gạo  ")).toEqual({ gt: "Gạo" }));
  it("số: bỏ ¥ , khoảng trắng; ≤ 4 thập phân; không 0 thừa", () => {
    expect(kiemO(SL, " 1,234.5 ")).toEqual({ gt: "1234.5" });
    expect(kiemO(SL, "20.0000")).toEqual({ gt: "20" });
    expect(kiemO(SL, "83.75")).toEqual({ gt: "83.75" });
    expect(kiemO(SL, "0")).toEqual({ gt: "0" });
    expect(kiemO(SL, "¥ 12")).toEqual({ gt: "12" });
  });
  it("số: lỗi", () => {
    for (const x of ["", "abc", "-1", "1e3", "1,5", "NaN", "Infinity", "1.2.3", "10000000000"])
      expect(kiemO(SL, x), x).toHaveProperty("loi");
  });
  it("giá: số yên nguyên > 0 — phần lẻ bị TỪ CHỐI, không làm tròn", () => {
    expect(kiemO(GIA, "¥1,200")).toEqual({ gt: "1200" });
    expect(kiemO(GIA, "1200.00")).toEqual({ gt: "1200" });
    expect(kiemO(GIA, "1200.4")).toEqual({ loi: "Giá là số yên nguyên" });
    expect(kiemO(GIA, "99.6")).toEqual({ loi: "Giá là số yên nguyên" });
    for (const x of ["0", "0.4", "-5", ""]) expect(kiemO(GIA, x), x).toHaveProperty("loi");
  });
  it("số lượng: quá 4 chữ số thập phân bị TỪ CHỐI (số 0 thừa cuối thì được)", () => {
    expect(kiemO(SL, "1.00005")).toEqual({ loi: "Tối đa 4 chữ số thập phân" });
    expect(kiemO(SL, "1.2345")).toEqual({ gt: "1.2345" });
    expect(kiemO(SL, "1.234500")).toEqual({ gt: "1.2345" });
    expect(kiemO(SL, "007.50")).toEqual({ gt: "7.5" });
    expect(kiemO(SL, ".5")).toEqual({ gt: "0.5" });
    expect(kiemO(SL, "3.")).toEqual({ gt: "3" });
    expect(kiemO(SL, "9999999999.9999")).toEqual({ gt: "9999999999.9999" });
  });
  it("chữ: tối đa 200 ký tự (sau trim, đếm theo ký tự Unicode)", () => {
    expect(kiemO(TEN, "a".repeat(200))).toEqual({ gt: "a".repeat(200) });
    expect(kiemO(TEN, " " + "ạ".repeat(200) + " ")).toEqual({ gt: "ạ".repeat(200) });
    expect(kiemO(TEN, "😀".repeat(200))).toEqual({ gt: "😀".repeat(200) });
    expect(kiemO(TEN, "a".repeat(201))).toEqual({ loi: "Tối đa 200 ký tự" });
  });
  it("ngày: ISO hợp lệ / không hạn / rỗng", () => {
    expect(kiemO(HAN, "2026-02-28")).toEqual({ gt: "2026-02-28" });
    expect(kiemO(HAN, "2028-02-29")).toEqual({ gt: "2028-02-29" });
    expect(kiemO(HAN, "Không hạn")).toEqual({ gt: "không hạn" });
    expect(kiemO(HAN, " ")).toEqual({ gt: "" });
    for (const x of ["2026-02-30", "2026-13-01", "26-01-01", "2026/01/01", "abc"])
      expect(kiemO(HAN, x), x).toHaveProperty("loi");
  });
  it("chọn: mã, hoặc TÊN đổi ra mã", () => {
    expect(kiemO(HANG, "0001")).toEqual({ gt: "0001" });
    expect(kiemO(HANG, "A")).toEqual({ gt: "0002" });
    expect(kiemO(HANG, "zz")).toHaveProperty("loi");
  });
  it("cột chỉ xem → lỗi", () => expect(kiemO(CHI, "5")).toHaveProperty("loi"));
});

describe("datO", () => {
  const x = d("A", { "ton:0001": "20.0000", product_name: "Gạo", rank_code: "0001", "han:0001": "" });
  it("khác máy chủ → vào cho, chữ đã chuẩn hoá", () => {
    expect(datO({}, x, SL, "¥25")).toEqual({ [khoaO("A", "ton:0001")]: "25" });
  });
  it("bằng máy chủ (so số: 20 ≡ 20.0000) → xoá khỏi cho", () => {
    const cho = { [khoaO("A", "ton:0001")]: "25", [khoaO("A", "product_name")]: "x" };
    expect(datO(cho, x, SL, "20")).toEqual({ [khoaO("A", "product_name")]: "x" });
    expect(datO(cho, x, SL, "20.0000")).toEqual({ [khoaO("A", "product_name")]: "x" });
  });
  it("chữ / chọn (tên ≡ mã) / rỗng ≡ null bằng máy chủ → xoá", () => {
    expect(datO({ [khoaO("A", "product_name")]: "x" }, x, TEN, " Gạo ")).toEqual({});
    expect(datO({ [khoaO("A", "rank_code")]: "0002" }, x, HANG, "S")).toEqual({});
    expect(datO({ [khoaO("A", "han:0001")]: "2026-01-01" }, x, HAN, "")).toEqual({});
    const y = d("B", { product_name: null });
    expect(datO({ [khoaO("B", "product_name")]: "x" }, y, TEN, "")).toEqual({});
  });
  it("không hợp lệ → giữ chữ gõ để báo lỗi; không đổi cho gốc", () => {
    const cho = {};
    expect(datO(cho, x, SL, "abc")).toEqual({ [khoaO("A", "ton:0001")]: "abc" });
    expect(cho).toEqual({});
  });
});

describe("dan", () => {
  const cots = [TEN, SL, CHI, GIA];
  const dongs = [d("A", { product_name: "a", "ton:0001": "1", "gia:02|01": null }), d("B", { product_name: "b", "ton:0001": "2", "gia:02|01": "100" }),
    d("C", { product_name: "c" })];
  it("khối 2×2 từ ô neo", () => {
    const r = dan("x\t5\r\ny\t6\r\n", { d: 0, c: 0 }, cots, dongs);
    expect(r).toEqual({ bo_qua: 0, o: [
      { k: "A", cot: "product_name", chu: "x" }, { k: "A", cot: "ton:0001", chu: "5" },
      { k: "B", cot: "product_name", chu: "y" }, { k: "B", cot: "ton:0001", chu: "6" }] });
  });
  it("ô khoá / ô OBC không có / ngoài bảng → bo_qua", () => {
    const r = dan("5\t7\t9\n1\t2\t3", { d: 0, c: 1 }, cots, dongs);   // A: ton, CHI (khoá), gia (null); B: ...
    expect(r.o.map(z => `${z.k}|${z.cot}|${z.chu}`)).toEqual(["A|ton:0001|5", "B|ton:0001|1", "B|gia:02|01|3"]);
    expect(r.bo_qua).toBe(3);
    expect(dan("1\t2", { d: 2, c: 1 }, cots, dongs)).toEqual({ o: [], bo_qua: 2 });   // C không có ton; cột CHI khoá
    expect(dan("1\n2", { d: 2, c: 0 }, cots, dongs).bo_qua).toBe(1);                   // dòng thứ 2 ngoài bảng
  });
  it("clipboard đúng MỘT ô rỗng → xoá ô neo (nếu sửa được)", () => {
    for (const x of ["", "\n", "\r\n"])
      expect(dan(x, { d: 1, c: 1 }, cots, dongs), JSON.stringify(x)).toEqual({ o: [{ k: "B", cot: "ton:0001", chu: "" }], bo_qua: 0 });
    expect(dan("", { d: 0, c: 2 }, cots, dongs)).toEqual({ o: [], bo_qua: 1 });      // ô neo khoá
    expect(dan("\n\n", { d: 0, c: 0 }, cots, dongs)).toEqual({ o: [], bo_qua: 0 });   // nhiều dòng rỗng: vẫn là "không có gì"
  });
  it("chỉ bỏ dòng rỗng CUỐI", () => {
    expect(dan("a\n\nb\n\n", { d: 0, c: 0 }, cots, dongs).o.map(z => z.chu)).toEqual(["a", "", "b"]);
  });
});

describe("loiCho / suaDuocO", () => {
  it("ô không chờ / hợp lệ → null; sai → câu lỗi; về OBC (kể cả mã lạ) → null", () => {
    const ko = khoaO("A", "rank_code");
    expect(loiCho(HANG, ko, {}, {})).toBeNull();
    expect(loiCho(HANG, ko, { [ko]: "0002" }, {})).toBeNull();
    expect(loiCho(HANG, ko, { [ko]: "zz" }, {})).toBe("Giá trị không có trong danh sách");
    const lech: Lech = { [ko]: { obc: "0777", ai: "an", luc: null } };
    expect(loiCho(HANG, ko, { [ko]: "0777" }, lech)).toBeNull();
    expect(loiCho(TEN, khoaO("A", "product_name"), { [khoaO("A", "product_name")]: "" },
      { [khoaO("A", "product_name")]: { obc: null, ai: null, luc: null } })).toBeNull();
  });
  it("suaDuocO: cột khoá, ô giá / tồn / hạn OBC không có → false", () => {
    expect(suaDuocO(d("A", { product_name: "x" }), TEN)).toBe(true);
    expect(suaDuocO(d("A", {}), CHI)).toBe(false);
    expect(suaDuocO(d("A", { "gia:02|01": null }), GIA)).toBe(false);
    expect(suaDuocO(d("A", {}), SL)).toBe(false);
    expect(suaDuocO(d("A", { "ton:0001": "0" }), SL)).toBe(true);
  });
});

describe("thanLuu", () => {
  it("thay = ĐÚNG chữ máy chủ (null nếu null); bỏ ô của dòng không còn", () => {
    const dongs = [d("A", { "ton:0001": "20.0000", product_name: null })];
    const cho = { [khoaO("A", "ton:0001")]: "25", [khoaO("A", "product_name")]: "Gạo", [khoaO("Z", "product_name")]: "?" };
    expect(thanLuu("sp", cho, dongs)).toEqual({ loai: "sp", o: [
      { k: "A", cot: "ton:0001", gia_tri: "25", thay: "20.0000" },
      { k: "A", cot: "product_name", gia_tri: "Gạo", thay: null }] });
  });
});

describe("locDong", () => {
  const ds = [d("000000000001", { customer_name: "Cửa hàng Đặng Văn", city: null }), d("B2", { customer_name: "Quán Sài Gòn" })];
  const lech: Lech = { [khoaO("B2", "customer_name")]: { obc: "x", ai: "an", luc: null } };
  it("bỏ dấu trên mã và mọi ô", () => {
    expect(locDong(ds, "dang van", false, {}).map(z => z.k)).toEqual(["000000000001"]);
    expect(locDong(ds, "SAI GON", false, {}).map(z => z.k)).toEqual(["B2"]);
    expect(locDong(ds, "0001", false, {}).map(z => z.k)).toEqual(["000000000001"]);
    expect(locDong(ds, "  ", false, {})).toHaveLength(2);
  });
  it("chiLech giữ dòng có ô lệch", () => {
    expect(locDong(ds, "", true, lech).map(z => z.k)).toEqual(["B2"]);
    expect(locDong(ds, "dang", true, lech)).toEqual([]);
  });
});

describe("cotMacDinh", () => {
  it("sp: 5 cột đầu + 2 giá đầu + tồn/hạn kho đầu + dt_12t, chỉ mã có trong cots", () => {
    const cots = ["product_name", "food_category_code", "rank_code", "unit", "case_qty", "barcode", "gia:00|std", "gia:02|std", "gia:02|01",
      "ton:0001", "han:0001", "ton:1002", "han:1002", "dt_12t", "ton_tong"].map(m => cot(m, "chu"));
    expect(cotMacDinh("sp", cots)).toEqual(["product_name", "food_category_code", "rank_code", "unit", "case_qty", "gia:00|std",
      "gia:02|std", "ton:0001", "han:0001", "dt_12t"]);
    expect(cotMacDinh("sp", [cot("product_name", "chu")])).toEqual(["product_name"]);
  });
  it("kh", () => {
    const cots = ["customer_name", "rank_code", "phone", "dt_12t", "lan_cuoi", "city"].map(m => cot(m, "chu"));
    expect(cotMacDinh("kh", cots)).toEqual(["customer_name", "rank_code", "phone", "dt_12t", "lan_cuoi"]);
  });
});

describe("khungNhin", () => {
  it("đầu: không âm; cuối: không quá số dòng", () => {
    expect(khungNhin(0, 400, 2142, 28)).toEqual({ dau: 0, cuoi: 25 });      // ceil(400/28)=15, +10
    expect(khungNhin(28 * 100, 280, 2142, 28)).toEqual({ dau: 90, cuoi: 120 });
    expect(khungNhin(28 * 2140, 400, 2142, 28)).toEqual({ dau: 2130, cuoi: 2142 });
    expect(khungNhin(1e9, 400, 2142, 28)).toEqual({ dau: 2142, cuoi: 2142 });
    expect(khungNhin(-50, 100, 5, 28)).toEqual({ dau: 0, cuoi: 5 });
    expect(khungNhin(0, 100, 0, 28)).toEqual({ dau: 0, cuoi: 0 });
    expect(khungNhin(100, 100, 50, 28, 0)).toEqual({ dau: 3, cuoi: 8 });
  });
});

describe("cột đã chọn (localStorage)", () => {
  afterEach(() => vi.unstubAllGlobals());
  const gia = (o: object) => vi.stubGlobal("localStorage", o);
  it("ném lỗi → null / không nổ", () => {
    const no = () => { throw new Error("chặn"); };
    gia({ getItem: no, setItem: no });
    expect(docCotDaChon("sp")).toBeNull();
    expect(() => ghiCotDaChon("sp", ["a"])).not.toThrow();
  });
  it("khứ hồi theo loại; hỏng → null", () => {
    const kho: Record<string, string> = {};
    gia({ getItem: (k: string) => kho[k] ?? null, setItem: (k: string, v: string) => { kho[k] = v; } });
    expect(docCotDaChon("sp")).toBeNull();
    ghiCotDaChon("sp", ["a", "b"]);
    expect(Object.keys(kho)).toEqual(["kome_bdl_cot_v1:sp"]);
    expect(docCotDaChon("sp")).toEqual(["a", "b"]);
    expect(docCotDaChon("kh")).toBeNull();
    kho["kome_bdl_cot_v1:kh"] = "{hỏng"; expect(docCotDaChon("kh")).toBeNull();
    kho["kome_bdl_cot_v1:kh"] = "[1,2]"; expect(docCotDaChon("kh")).toBeNull();
  });
});
