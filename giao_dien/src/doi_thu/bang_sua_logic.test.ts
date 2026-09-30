import { describe, expect, it } from "vitest";
import type { QuanSat } from "./kieu";
import { COT, cotHien, daGop, dichGop, dongHien, ghepDong, giaTriSua, hienThi, khoaDong, khoaNhomBang, neoKeTiep, nhanMuc, nhomBang, oKeTiep,
  suaDuoc, viTriNeo, thanO, timDong, type Cot } from "./bang_sua_logic";

let seq = 0;
const qs = (o: Partial<QuanSat> = {}): QuanSat => ({
  ma_doi_thu: "NEXT", ten_doi_thu: "Next", nguon: "nap", id: ++seq, ma_hang_dt: `h${seq}`, mat_hang_khoa: `h${seq}`, an: false, ngay_nguon: "2026-09-01",
  hinh_thuc_nguon: "file", nguon_file: null, vi_tri: null, ten_goc: "Sứa ăn liền", quy_cach_goc: "30 gói", gia_goc: 285,
  don_vi_gia: "goi", kg_moi_don_vi_gia: null, thue: "chua", gom_ship: null, kenh_gia: null, muc_gia: null, gia_bac: null,
  gia_truoc_km: null, trang_thai: "con", khuyen_mai: null, loai_nguon: "bang_gia", ghi_chu: null, ma_kome: "XT02",
  nhan: "thay_the", nhom_khoa: "ma:XT02", ten_nhom: "Sứa", trang_thai_duyet: "ai_doc", yen_chuan: 1425, don_vi_so: "kg",
  nen_gia: "", tuoi_ngay: 5, thang_lo: null, lien_ket_thu_muc: null, web_ben: null, lien_ket_bang_chung: null,
  so_goi_thung: 30, kl_goi_g: 200, bac: null, kg_thung_dt: 6, gia_goi: null, gia_thung: null, gia_1: null, gia_5: null,
  gia_10: null, gia_pallet: null, sua_cuoi: 7, bat_thuong: false, ...o,
} as unknown as QuanSat);
const cot = (ma: string) => COT.find(c => c.ma === ma)!;

describe("cột", () => {
  it("Bên chỉ hiện khi xem mọi bên; ¥/kg và Bên không sửa được", () => {
    expect(cotHien(false).some(c => c.ma === "ben")).toBe(false);
    expect(cotHien(true).map(c => c.ma).slice(0, 2)).toEqual(["ten_goc", "ben"]);
    expect(suaDuoc(qs(), cot("yen_kg"))).toBe(false);
    expect(suaDuoc(qs(), cot("ben"))).toBe(false);
    expect(suaDuoc(qs(), cot("kl_goi_g"))).toBe(true);
  });
  it("dòng đã bị thay không sửa được ô nào; khách kể đã có nhóm không ghép lại", () => {
    const thay = qs({ thay_boi: { nguon: "tay", id: 9 } } as Partial<QuanSat>);
    expect(COT.some(c => suaDuoc(thay, c))).toBe(false);
    const ke = qs({ loai_nguon: "khach_ke", nhom_khoa: "ma:XT02" });
    expect(suaDuoc(ke, cot("ma_kome"))).toBe(false);
    expect(suaDuoc(ke, cot("nhan"))).toBe(false);
    expect(suaDuoc(ke, cot("gia_goc"))).toBe(true);
  });
});

describe("hienThi", () => {
  it("số, nhãn, ô trống '?'", () => {
    const q = qs({ kl_goi_g: null, so_goi_thung: 30 });
    expect(hienThi(q, cot("kl_goi_g"))).toEqual({ chu: "", hoi: true });
    expect(hienThi(q, cot("so_goi_thung"))).toEqual({ chu: "30", hoi: false });
    expect(hienThi(q, cot("gia_goc")).chu).toBe("¥285");
    expect(hienThi(q, cot("don_vi_gia")).chu).toBe("gói");
    expect(hienThi(q, cot("thue")).chu).toBe("Chưa thuế");
    expect(hienThi(q, cot("nhan")).chu).toBe("khác thương hiệu");
    expect(hienThi(qs({ gia_goc: null }), cot("gia_goc")).hoi).toBe(true);
  });
  it("hàng đã hết không cần giá; chưa ghép là '—' chứ không '?'", () => {
    expect(hienThi(qs({ gia_goc: null, trang_thai: "het" }), cot("gia_goc")).hoi).toBe(false);
    const chua = qs({ ma_kome: null, nhan: null } as Partial<QuanSat>);
    expect(hienThi(chua, cot("ma_kome"))).toEqual({ chu: "—", hoi: false });
    expect(hienThi(chua, cot("nhan"))).toEqual({ chu: "—", hoi: false });
    expect(hienThi(qs({ ma_kome: null, ma_ghep: "XT02", nhan: null } as Partial<QuanSat>), cot("ma_kome")).chu).toBe("XT02");
  });
  it("¥/kg: máy chủ tính; nhóm không so theo kg → 'chưa quy'; khách kể không đòi quy cách", () => {
    expect(hienThi(qs(), cot("yen_kg")).chu).toBe("¥1,425");
    expect(hienThi(qs({ don_vi_so: "don_vi:goi", yen_chuan: 285 }), cot("yen_kg"))).toEqual({ chu: "chưa quy", hoi: true });
    expect(hienThi(qs({ loai_nguon: "khach_ke", kl_goi_g: null }), cot("kl_goi_g")).hoi).toBe(false);
  });
});

describe("thanO — thân POST của MỘT ô (dựng qua sua_logic.payload)", () => {
  it("không đổi → null; số gõ kiểu '5,300' cho 5300 không phải là đổi", () => {
    expect(thanO(qs(), "kl_goi_g", "200")).toBeNull();
    expect(thanO(qs({ gia_goc: 5300 }), "gia_goc", "5,300")).toBeNull();
  });
  it("ô thường: chỉ đúng trường đó, kèm da_xem = sua_cuoi", () => {
    const q = qs({ kl_goi_g: null });
    expect(thanO(q, "kl_goi_g", "200")).toEqual({ body: { nguon: "nap", id: q.id, da_xem: 7, ghi_de: false, thay_doi: { kl_goi_g: "200" } } });
    expect(thanO(q, "ten_goc", " Sứa ăn liền loại 1 ")).toMatchObject({ body: { thay_doi: { ten_goc: "Sứa ăn liền loại 1" } } });
  });
  it("trường giá = 'Máy đọc sai'", () => {
    expect(thanO(qs(), "gia_goc", "290")).toMatchObject({ body: { thay_doi: { gia_goc: "290" }, vi_sao_gia: "doc_sai" } });
    expect(thanO(qs(), "thue", "co")).toMatchObject({ body: { thay_doi: { thue: "co" }, vi_sao_gia: "doc_sai" } });
    expect(thanO(qs(), "trang_thai", "het")).not.toHaveProperty("body.vi_sao_gia");
  });
  it("kg / đơn vị giá: cột quy ra ¥/kg — phẩy là thập phân, không cần 'vì sao đổi giá', phải > 0", () => {
    const q = qs({ kg_moi_don_vi_gia: null });
    expect(hienThi(q, cot("kg_moi_don_vi_gia"))).toEqual({ chu: "", hoi: true });
    expect(hienThi(qs({ kg_moi_don_vi_gia: 0.2 }), cot("kg_moi_don_vi_gia")).chu).toBe("0.2");
    const t = thanO(q, "kg_moi_don_vi_gia", "0,2") as { body: Record<string, unknown> };
    expect(t.body.thay_doi).toEqual({ kg_moi_don_vi_gia: "0,2" });
    expect(t.body).not.toHaveProperty("vi_sao_gia");
    expect(thanO(qs({ kg_moi_don_vi_gia: 0.2 }), "kg_moi_don_vi_gia", "0,2")).toBeNull();
    expect(thanO(q, "kg_moi_don_vi_gia", "0")).toHaveProperty("loi");
  });
  it("ghi đè", () => {
    expect(thanO(qs(), "so_goi_thung", "20", { ghi_de: true })).toMatchObject({ body: { ghi_de: true } });
  });
  it("lỗi hiển nhiên chặn trước khi gửi (kiemForm)", () => {
    expect(thanO(qs(), "so_goi_thung", "2.5")).toHaveProperty("loi");
    expect(thanO(qs(), "kl_goi_g", "")).toHaveProperty("loi");           // dòng nạp: để trống không xoá được
  });
  it("mã KOME mới trên dòng 'không ghép' cần chọn thương hiệu; chọn rồi thì gửi cả hai", () => {
    const q = qs({ ma_kome: null, nhan: null } as Partial<QuanSat>);
    expect(thanO(q, "ma_kome", "XT02")).toEqual({ can_nhan: true });
    expect(thanO(q, "ma_kome", "XT02", { nhan: "cung_hang" })).toMatchObject({ body: { ma_kome: "XT02", nhan: "cung_hang" } });
  });
  it("đổi mã trên dòng đã ghép giữ nhãn; xoá mã = bỏ ghép", () => {
    const b = thanO(qs(), "ma_kome", "XT03") as { body: Record<string, unknown> };
    expect(b.body.ma_kome).toBe("XT03");
    expect(b.body).not.toHaveProperty("nhan");
    expect(thanO(qs(), "ma_kome", "")).toMatchObject({ body: { ma_kome: null, nhan: "khong" } });
  });
  it("giaTriSua điền sẵn ô sửa từ giá trị hiện hành", () => {
    expect(giaTriSua(qs(), "kl_goi_g")).toBe("200");
    expect(giaTriSua(qs({ kl_goi_g: null }), "kl_goi_g")).toBe("");
    expect(giaTriSua(qs(), "nhan")).toBe("thay_the");
  });
});

describe("oKeTiep — di chuyển bằng bàn phím", () => {
  const cots: Cot[] = cotHien(false);                   // ten_goc … yen_kg
  const iSua = (ma: string) => cots.findIndex(c => c.ma === ma);
  it("xuống / lên cùng cột, dừng ở biên", () => {
    expect(oKeTiep({ d: 0, c: 3 }, "xuong", 3, cots)).toEqual({ d: 1, c: 3 });
    expect(oKeTiep({ d: 2, c: 3 }, "xuong", 3, cots)).toBeNull();
    expect(oKeTiep({ d: 0, c: 3 }, "len", 3, cots)).toBeNull();
  });
  it("mũi tên trái / phải đi qua mọi cột (kể cả không sửa được)", () => {
    const cuoi = cots.length - 1;
    expect(oKeTiep({ d: 0, c: cuoi - 1 }, "phai", 3, cots)).toEqual({ d: 0, c: cuoi });
    expect(oKeTiep({ d: 0, c: cuoi }, "phai", 3, cots)).toBeNull();
    expect(oKeTiep({ d: 0, c: 0 }, "trai", 3, cots)).toBeNull();
  });
  it("Tab bỏ qua cột không sửa được, hết dòng sang dòng dưới; Shift+Tab ngược lại", () => {
    expect(oKeTiep({ d: 0, c: iSua("nhan") }, "tab", 3, cots)).toEqual({ d: 1, c: iSua("ten_goc") });
    expect(oKeTiep({ d: 1, c: iSua("ten_goc") }, "tab_lui", 3, cots)).toEqual({ d: 0, c: iSua("nhan") });
    expect(oKeTiep({ d: 2, c: iSua("nhan") }, "tab", 3, cots)).toBeNull();
  });
});

describe("ghepDong / timDong", () => {
  it("ghép dòng mới về từ /mat-hang: giữ cột /mat-hang không trả, thay được cả id (dòng tay mới)", () => {
    const a = qs({ moc_bat_thuong: 900 } as Partial<QuanSat>), b = qs();
    const moi = { ...a, id: 999, nguon: "tay" as const, kl_goi_g: 250 } as QuanSat;
    delete (moi as Partial<QuanSat>).moc_bat_thuong;
    const r = ghepDong([a, b], { nguon: a.nguon, id: a.id }, moi);
    expect(r.map(x => x.id)).toEqual([999, b.id]);
    expect(r[0].kl_goi_g).toBe(250);
    expect(r[0].moc_bat_thuong).toBe(900);
    expect(ghepDong([b], { nguon: "nap", id: -1 }, moi)).toEqual([b]);
  });
  it("tìm bỏ dấu trên tên, quy cách, mã KOME", () => {
    const ds = [qs({ ten_goc: "Sứa ăn liền" }), qs({ ten_goc: "Chân gà", quy_cach_goc: "Túi 500g", ma_kome: "CG01" })];
    expect(timDong(ds, "sua an").length).toBe(1);
    expect(timDong(ds, "tui 500").length).toBe(1);
    expect(timDong(ds, "cg01").length).toBe(1);
    expect(timDong(ds, "  ").length).toBe(2);
  });
});

describe("070 — nhóm dòng theo mặt hàng", () => {
  it("nhanMuc", () => {
    expect(nhanMuc(qs({ kenh_gia: "tai_kho", muc_gia: null }))).toBe("Tại kho");
    expect(nhanMuc(qs({ kenh_gia: null, muc_gia: "pallet" }))).toBe("Pallet");
    expect(nhanMuc(qs({ kenh_gia: "tai_kho", muc_gia: "dac_biet" }))).toBe("Đặc biệt · Tại kho");
    expect(nhanMuc(qs({ kenh_gia: null, muc_gia: null }))).toBe("Thường");
    expect(nhanMuc(qs({ kenh_gia: "xyz", muc_gia: null }))).toBe("xyz");
  });
  it("nhomBang: đầu nhóm là dòng đại diện, giữ thứ tự lần gặp đầu", () => {
    const a1 = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1", dai_dien: false } as Partial<QuanSat>);
    const a2 = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1", dai_dien: true } as Partial<QuanSat>);
    const b1 = qs({ ma_doi_thu: "N", mat_hang_khoa: "h2", dai_dien: true } as Partial<QuanSat>);
    const c1 = qs({ ma_doi_thu: "M", mat_hang_khoa: "h1" } as Partial<QuanSat>);
    const g = nhomBang([a1, b1, a2, c1]);
    expect(g.map(x => [x.dau.id, x.con.map(y => y.id)])).toEqual([[a2.id, [a1.id]], [b1.id, []], [c1.id, []]]);
  });
  it("nhomBang: không dòng nào có dai_dien → đầu nhóm là dòng đầu tiên; bên khác cùng khoá mặt hàng là nhóm khác", () => {
    const a = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1" } as Partial<QuanSat>);
    const b = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1" } as Partial<QuanSat>);
    const c = qs({ ma_doi_thu: "M", mat_hang_khoa: "h1" } as Partial<QuanSat>);
    expect(nhomBang([a, b, c]).map(x => [x.dau.id, x.con.map(y => y.id)])).toEqual([[a.id, [b.id]], [c.id, []]]);
  });
  it("cột Mức giá chỉ đọc, đứng sau Bên", () => {
    const c = cotHien(true).map(x => x.ma);
    expect(c.indexOf("muc")).toBe(c.indexOf("ben") + 1);
    expect(COT.find(x => x.ma === "muc")!.kieu).toBeNull();
    expect(hienThi(qs({ kenh_gia: "gui" }), cot("muc"))).toEqual({ chu: "Gửi", hoi: false });
  });
});

describe("nhóm theo mặt hàng (070)", () => {
  const P = (o: Partial<QuanSat>) => qs(o as Partial<QuanSat>);
  it("dongHien: mặc định đóng — chỉ dòng đầu; mở nhóm thì dòng con ngay dưới dòng đầu", () => {
    const a1 = P({ ma_doi_thu: "N", mat_hang_khoa: "h1", dai_dien: true }), a2 = P({ ma_doi_thu: "N", mat_hang_khoa: "h1", dai_dien: false });
    const b = P({ ma_doi_thu: "N", mat_hang_khoa: "h2", dai_dien: true });
    const g = nhomBang([a1, b, a2]);
    const dong = dongHien(g, new Set());
    expect(dong.map(x => [x.q.id, x.soCon, x.mo])).toEqual([[a1.id, 1, false], [b.id, 0, false]]);
    const mo = dongHien(g, new Set([khoaNhomBang(a1)]));
    expect(mo.map(x => [x.q.id, x.soCon])).toEqual([[a1.id, 1], [a2.id, null], [b.id, 0]]);
    expect(mo[0].mo).toBe(true);
  });
  it("dongHien: nhóm có dòng con đang lỗi / 409 tự mở; nhóm không có dòng con không bao giờ 'mở'", () => {
    const a1 = P({ ma_doi_thu: "N", mat_hang_khoa: "h1", dai_dien: true }), a2 = P({ ma_doi_thu: "N", mat_hang_khoa: "h1" });
    const b = P({ ma_doi_thu: "N", mat_hang_khoa: "h2" });
    const d = dongHien(nhomBang([a1, a2, b]), new Set([khoaNhomBang(b)]), q => q.id === a2.id);
    expect(d.map(x => [x.q.id, x.mo, x.ep])).toEqual([[a1.id, true, true], [a2.id, true, true], [b.id, false, false]]);
  });
  it("khoaNhomBang: bên và khoá mặt hàng có '|' vẫn không trùng", () => {
    expect(khoaNhomBang({ ma_doi_thu: "A|B", mat_hang_khoa: "C" })).not.toBe(khoaNhomBang({ ma_doi_thu: "A", mat_hang_khoa: "B|C" }));
  });
  it("viTriNeo: ô neo theo KHOÁ — dòng phía trên rời bảng thì chỉ số đổi nhưng vẫn là đúng dòng; dòng mất → null", () => {
    expect(viTriNeo(["a", "b", "c"], { k: "c", c: 2 })).toEqual({ d: 2, c: 2 });
    expect(viTriNeo(["b", "c"], { k: "c", c: 2 })).toEqual({ d: 1, c: 2 });   // "a" đã ẩn: ô đang sửa vẫn ở "c"
    expect(viTriNeo(["b", "c"], { k: "a", c: 2 })).toBeNull();
    expect(viTriNeo(["a"], null)).toBeNull();
  });
  it("viTriNeo trên dongHien: mở nhóm chèn dòng con — ô neo dưới nhóm vẫn chỉ đúng dòng của nó", () => {
    const a1 = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1", dai_dien: true } as Partial<QuanSat>);
    const a2 = qs({ ma_doi_thu: "N", mat_hang_khoa: "h1" } as Partial<QuanSat>);
    const b = qs({ ma_doi_thu: "N", mat_hang_khoa: "h2" } as Partial<QuanSat>);
    const g = nhomBang([a1, a2, b]);
    const dong = (mo: Set<string>) => dongHien(g, mo).map(x => khoaDong(x.q));
    const neo = { k: khoaDong(b), c: 1 };
    expect(viTriNeo(dong(new Set()), neo)).toEqual({ d: 1, c: 1 });
    expect(viTriNeo(dong(new Set([khoaNhomBang(a1)])), neo)).toEqual({ d: 2, c: 1 });
  });
  it("neoKeTiep: đi theo luật oKeTiep trên danh sách khoá; dòng gốc không còn hiện → null", () => {
    const cots = cotHien(false);
    expect(neoKeTiep(["a", "b"], { k: "a", c: 0 }, "xuong", cots)).toEqual({ k: "b", c: 0 });
    expect(neoKeTiep(["a", "b"], { k: "b", c: 0 }, "xuong", cots)).toBeNull();
    expect(neoKeTiep(["a", "b"], { k: "z", c: 0 }, "xuong", cots)).toBeNull();
    expect(neoKeTiep(["a", "b"], { k: "a", c: cots.length - 1 }, "tab", cots)).toEqual({ k: "b", c: 0 });
  });
  it("khoaDong: _k thắng nguon:id", () => {
    expect(khoaDong({ nguon: "tay", id: 5 })).toBe("tay:5");
    expect(khoaDong({ nguon: "tay", id: 9, _k: "tay:5" })).toBe("tay:5");
  });
  it("dichGop: mặt hàng khác CÙNG bên (một dòng mỗi mặt hàng), lọc theo ô tìm", () => {
    const a1 = P({ ma_doi_thu: "N", mat_hang_khoa: "h1", dai_dien: true, ten_goc: "Sứa" });
    const a2 = P({ ma_doi_thu: "N", mat_hang_khoa: "h1", ten_goc: "Sứa" });
    const b1 = P({ ma_doi_thu: "N", mat_hang_khoa: "h2", ten_goc: "Bánh đa" });
    const b2 = P({ ma_doi_thu: "N", mat_hang_khoa: "h2", dai_dien: true, ten_goc: "Bánh đa" });
    const c = P({ ma_doi_thu: "N", mat_hang_khoa: "h3", ten_goc: "Phở khô" });
    const m = P({ ma_doi_thu: "M", mat_hang_khoa: "h9", ten_goc: "Bánh đa" });
    const ds = [a1, a2, b1, b2, c, m];
    expect(dichGop(ds, a2, "").map(x => x.id)).toEqual([b2.id, c.id]);
    expect(dichGop(ds, a1, "banh").map(x => x.id)).toEqual([b2.id]);
  });
  it("daGop: khoá mặt hàng khác mã hàng của chính dòng", () => {
    expect(daGop({ mat_hang_khoa: "h1", ma_hang_dt: "h1" })).toBe(false);
    expect(daGop({ mat_hang_khoa: "h1", ma_hang_dt: "h2" })).toBe(true);
  });
});
