import { describe, expect, it } from "vitest";
import type { LoaiThe } from "./nhac";
import {
  chenThe, dongDangMua, dongNgungMua, dsGoiY, doLai, ghepCap, ghepTin, locGoiY, thanGhi, thanhGia, thanhNhac, tuDangGo,
  type GoiYApi, type The, type TinDoiThu,
} from "./nhac";

const API: GoiYApi = {
  doi_thu: [{ ma: "THAK", ten: "THAK JSC" }, { ma: "VIFO", ten: "Việt Foods" }],
  hang: [{ khoa: "n:5", ten: "Nhóm cá", loai: "nhom" },
         { khoa: "ma:NT01", ten: "Ca Ba sa cat khuc (500g x 20 packs)", loai: "ma" },
         { khoa: "ma:DU02", ten: "Đậu hũ chiên", loai: "ma" }],
};
const DS = dsGoiY(API);
const dt = (khoa: string, vi_tri_dau: number): The => ({ loai: "doi_thu", khoa, nhan: khoa, vi_tri_dau });
const nh = (khoa: string, nhan: string, vi_tri_dau: number): The => ({ loai: "nhom", khoa, nhan, vi_tri_dau });

describe("tuDangGo — từ đang gõ sau @ tại con trỏ", () => {
  it("vừa gõ @ ở đầu câu: từ rỗng", () => {
    expect(tuDangGo("@", 1, [])).toEqual({ dau: 0, tu: "" });
  });
  it("giữa câu, sau khoảng trắng", () => {
    expect(tuDangGo("Khách nói @th", 13, [])).toEqual({ dau: 10, tu: "th" });
  });
  it("gặp khoảng trắng giữa @ và con trỏ: không còn gõ thẻ", () => {
    expect(tuDangGo("Khách nói @th ak", 16, [])).toBeNull();
  });
  it("@ dính sau chữ/số latin (email) không mở gợi ý", () => {
    expect(tuDangGo("mail a@b", 8, [])).toBeNull();
    expect(tuDangGo("x9@b", 4, [])).toBeNull();
  });
  it("@ ngay sau kanji / kana / dấu câu vẫn mở gợi ý", () => {
    expect(tuDangGo("田中さん@TH", 7, [])).toEqual({ dau: 4, tu: "TH" });
    expect(tuDangGo("ラーメン@", 5, [])).toEqual({ dau: 4, tu: "" });
    expect(tuDangGo("(@TH", 4, [])).toEqual({ dau: 1, tu: "TH" });
  });
  it("con trỏ ngay sau một thẻ đã chọn: không mở lại gợi ý", () => {
    expect(tuDangGo("@THAK", 5, [dt("THAK", 0)])).toBeNull();
  });
  it("không có @ thì không có gì", () => {
    expect(tuDangGo("gọi lại sau", 5, [])).toBeNull();
  });
});

describe("dsGoiY / locGoiY — lọc không dấu, đối thủ trước", () => {
  it("đối thủ đứng trước hàng; nhãn đối thủ là mã, nhãn hàng là tên", () => {
    expect(DS.map(m => m.loai)).toEqual(["doi_thu", "doi_thu", "nhom", "nhom", "nhom"]);
    expect(DS[0].nhan).toBe("THAK");
    expect(DS[3].nhan).toBe("Ca Ba sa cat khuc (500g x 20 packs)");
  });
  it("từ rỗng: mọi mục, có trần", () => {
    expect(locGoiY(DS, "")).toHaveLength(5);
    expect(locGoiY(DS, "", 2)).toHaveLength(2);
  });
  it("không dấu, bỏ khoảng trắng: 'basa' khớp 'Ca Ba sa…'", () => {
    expect(locGoiY(DS, "basa").map(m => m.khoa)).toEqual(["ma:NT01"]);
  });
  it("chữ đ và dấu: 'dau' khớp 'Đậu hũ'", () => {
    expect(locGoiY(DS, "dau").map(m => m.khoa)).toEqual(["ma:DU02"]);
  });
  it("khớp theo mã: 'nt01' và tên đối thủ 'viet'", () => {
    expect(locGoiY(DS, "nt01").map(m => m.khoa)).toEqual(["ma:NT01"]);
    expect(locGoiY(DS, "viet").map(m => m.khoa)).toEqual(["VIFO"]);
  });
  it("mã thuộc nhóm có tên: khoá NHÓM, nhãn tên hàng, chữ phụ 'thuộc nhóm'", () => {
    const ds = dsGoiY({ doi_thu: [], hang: [{ khoa: "n:5", ten: "Nhóm cá", loai: "nhom" },
      { khoa: "n:5", ten: "Ca tra phi le", loai: "ma", ma: "NT05", ten_nhom: "Nhóm cá" },
      { khoa: "ma:NT01", ten: "Basa", loai: "ma", ma: "NT01" }] });
    const m = locGoiY(ds, "catra")[0];
    expect(m).toMatchObject({ loai: "nhom", khoa: "n:5", nhan: "Ca tra phi le", phu: "mã NT05 · thuộc nhóm Nhóm cá" });
    expect(locGoiY(ds, "nt05").map(x => x.khoa)).toEqual(["n:5"]);
    expect(chenThe("@ca", 0, 3, m).the).toEqual({ loai: "nhom", khoa: "n:5", nhan: "Ca tra phi le", vi_tri_dau: 0 });
    expect(ds[2].phu).toBe("mã NT01");
  });
  it("khớp đầu từ xếp trước khớp giữa, nhưng đối thủ vẫn trước hàng", () => {
    const ds = dsGoiY({ doi_thu: [{ ma: "ACA", ten: "A ca" }], hang: [{ khoa: "n:1", ten: "Xa ca", loai: "nhom" },
      { khoa: "n:2", ten: "Cá thu", loai: "nhom" }] });
    expect(locGoiY(ds, "ca").map(m => m.khoa)).toEqual(["ACA", "n:2", "n:1"]);
  });
});

describe("chenThe — chèn @<nhãn> và trả vị trí", () => {
  it("thay từ đang gõ bằng thẻ + khoảng trắng, con trỏ sau khoảng trắng", () => {
    const r = chenThe("Khách nói @th rẻ", 10, 13, DS[0]);
    expect(r.text).toBe("Khách nói @THAK rẻ");
    expect(r.the).toEqual({ loai: "doi_thu", khoa: "THAK", nhan: "THAK", vi_tri_dau: 10 });
    expect(r.con_tro).toBe(16);
  });
  it("cuối câu thì thêm khoảng trắng", () => {
    const r = chenThe("@ba", 0, 3, DS[3]);
    expect(r.text).toBe("@Ca Ba sa cat khuc (500g x 20 packs) ");
    expect(r.con_tro).toBe(r.text.length);
  });
});

describe("doLai — dò lại vị trí thẻ sau mỗi lần sửa", () => {
  const cu = "Khách nói @THAK bán @Nhóm cá rẻ";
  const the = [dt("THAK", 10), nh("n:5", "Nhóm cá", 20)];
  it("gõ thêm trước các thẻ: thẻ dời theo", () => {
    const moi = "Hôm nay khách nói @THAK bán @Nhóm cá rẻ";
    expect(doLai(cu, moi, the).map(t => t.vi_tri_dau)).toEqual([18, 28]);
  });
  it("gõ sau các thẻ: không đổi", () => {
    expect(doLai(cu, cu + " hơn", the)).toEqual(the);
  });
  it("xoá một chữ trong thẻ: thẻ đó bỏ, thẻ sau dời", () => {
    const moi = "Khách nói @THK bán @Nhóm cá rẻ";
    const r = doLai(cu, moi, the);
    expect(r).toEqual([nh("n:5", "Nhóm cá", 19)]);
  });
  it("gõ thêm @ ngay trước thẻ (chữ trùng ở mép sửa): thẻ vẫn giữ, dời đúng", () => {
    const r = doLai("x @THAK", "x @@THAK", [dt("THAK", 2)]);
    expect(r).toEqual([dt("THAK", 3)]);
  });
  it("xoá cả đoạn chứa thẻ: bỏ hết thẻ trong đoạn", () => {
    expect(doLai(cu, "Khách nói rẻ", the)).toEqual([]);
  });
  it("vị trí là đơn vị UTF-16: emoji đứng trước thẻ", () => {
    const moi = "🐟 " + cu;
    const r = doLai(cu, moi, the);
    expect(r.map(t => t.vi_tri_dau)).toEqual([13, 23]);
    for (const t of r) expect(moi.slice(t.vi_tri_dau, t.vi_tri_dau + t.nhan.length + 1)).toBe("@" + t.nhan);
    // Phần gửi lên: đúng dấu @ ở vi_tri_dau theo chỉ số chuỗi JS (máy chủ đổi sang ký tự Unicode).
    expect(thanhNhac(r)).toEqual([
      { loai: "doi_thu", khoa: "THAK", vi_tri_dau: 13, do_dai: 5 },
      { loai: "nhom", khoa: "n:5", vi_tri_dau: 23, do_dai: 8 }]);
  });
  it("chèn thẻ sau emoji: vi_tri_dau là chỉ số JS của @", () => {
    const r = chenThe("🐟 @th", 3, 6, DS[0]);
    expect(r.text[r.the.vi_tri_dau]).toBe("@");
    expect(r.the.vi_tri_dau).toBe(3);
  });
});

describe("ghepCap / thanhGia — mỗi thẻ hàng ghép đối thủ gần nhất đứng TRƯỚC", () => {
  const the = [nh("n:5", "Nhóm cá", 0), dt("THAK", 10), nh("ma:NT01", "Basa", 16), dt("VIFO", 22), nh("ma:DU02", "Đậu", 28),
               nh("ma:NT01", "Basa", 34)];
  it("ghép theo vị trí; hàng đứng trước mọi đối thủ thì null; hàng lặp chỉ một dòng", () => {
    expect(ghepCap(the).map(c => [c.nhom.khoa, c.doi_thu])).toEqual([
      ["n:5", null], ["ma:NT01", "THAK"], ["ma:DU02", "VIFO"]]);
  });
  it("chỉ dòng có giá mới gửi; đổi đối thủ tay thắng ghép sẵn", () => {
    const r = thanhGia(the, {
      "ma:NT01": { gia: "1,200", don_vi: "kg" },
      "ma:DU02": { gia: " 300 ", don_vi: "goi", doi_thu: "THAK" },
      "n:5": { gia: "", don_vi: "kg" } });
    expect(r).toEqual({ loi: null, gia: [
      { ma_doi_thu: "THAK", nhom_khoa: "ma:NT01", gia_goc: "1,200", don_vi_gia: "kg" },
      { ma_doi_thu: "THAK", nhom_khoa: "ma:DU02", gia_goc: "300", don_vi_gia: "goi" }] });
  });
  it("có giá mà chưa có đối thủ: báo lỗi, không gửi", () => {
    const r = thanhGia(the, { "n:5": { gia: "500", don_vi: "kg" } });
    expect(r.gia).toEqual([]);
    expect(r.loi).toContain("Nhóm cá");
  });
  it("đối thủ chọn tay đã bị xoá khỏi câu: rơi về ghép sẵn", () => {
    const r = thanhGia(the, { "ma:NT01": { gia: "1200", don_vi: "kg", doi_thu: "XXX" } });
    expect(r.gia[0].ma_doi_thu).toBe("THAK");
  });
});

// Thẻ đã lưu như GET trả (vị trí theo ký tự; ở đây toàn chữ BMP nên trùng chỉ số JS).
const luu = (cau: string, ...the: [LoaiThe, string, string][]) =>
  the.map(([loai, khoa, chu]) => ({ loai, khoa, vi_tri_dau: cau.indexOf(chu), do_dai: chu.trimEnd().length }))
     .sort((a, b) => a.vi_tri_dau - b.vi_tri_dau);
const CAU_TIN = "@VIFO bán @Nhóm cá, còn @THAK bán @Ca Ba sa rẻ";

describe("ghepTin / dòng hiển thị của hồ sơ khách", () => {
  const tin: TinDoiThu = {
    tiep_xuc_id: 1, ngay: "2026-09-12", nguoi: null,
    noi_dung: CAU_TIN,
    nhac: luu(CAU_TIN, ["doi_thu", "VIFO", "@VIFO"], ["nhom", "n:5", "@Nhóm cá"], ["doi_thu", "THAK", "@THAK"],
              ["nhom", "ma:NT01", "@Ca Ba sa"]),
    doi_thu: [{ ma: "THAK", ten: "THAK JSC" }, { ma: "VIFO", ten: "Việt Foods" }],
    nhom: [{ khoa: "n:5", ten: "Nhóm cá" }, { khoa: "ma:NT01", ten: "Ca Ba sa" }],
    gia: [{ ma_doi_thu: "THAK", ten_doi_thu: "THAK JSC", nhom_khoa: "ma:NT01", ten_nhom: "Ca Ba sa", gia_goc: 1200.0, don_vi_gia: "kg" }],
  };
  it("giá ghi rõ cặp; nhóm không giá ghép theo vị trí trong câu", () => {
    expect(ghepTin(tin).map(d => [d.doi_thu?.ma ?? null, d.nhom?.khoa ?? null, d.gia?.gia_goc ?? null])).toEqual([
      ["THAK", "ma:NT01", 1200], ["VIFO", "n:5", null]]);
  });
  it("hàng đứng trước đối thủ DUY NHẤT của câu vẫn ghép với nó (cùng ghepCap lúc ghi); đối thủ không nhóm vẫn có dòng", () => {
    const cau = "@Nhóm cá lấy của @THAK";
    const t1: TinDoiThu = { ...tin, noi_dung: cau, gia: [], doi_thu: [{ ma: "THAK", ten: "THAK JSC" }],
      nhom: [{ khoa: "n:5", ten: "Nhóm cá" }], nhac: luu(cau, ["nhom", "n:5", "@Nhóm cá"], ["doi_thu", "THAK", "@THAK"]) };
    expect(ghepTin(t1).map(d => [d.doi_thu?.ma, d.nhom?.khoa])).toEqual([["THAK", "n:5"]]);
    expect(ghepCap(t1.nhac).map(c => c.doi_thu)).toEqual(["THAK"]);   // cùng một định nghĩa lúc ghi
    const t2: TinDoiThu = { ...t1, nhom: [], nhac: t1.nhac.filter(z => z.loai === "doi_thu") };
    expect(ghepTin(t2).map(d => [d.doi_thu?.ma, d.nhom])).toEqual([["THAK", null]]);
  });
  it("mã đối thủ là tiền tố của mã khác (VI / VIFO): ghép theo vị trí thẻ, không dò chữ", () => {
    const cau = "@VIFO bán @Basa, @VI bán @Tom";
    const t: TinDoiThu = { tiep_xuc_id: 2, ngay: "2026-09-12", nguoi: null, noi_dung: cau, gia: [],
      doi_thu: [{ ma: "VI", ten: "Vi" }, { ma: "VIFO", ten: "Việt Foods" }],
      nhom: [{ khoa: "ma:NT01", ten: "Basa" }, { khoa: "ma:NT02", ten: "Tom" }],
      nhac: luu(cau, ["doi_thu", "VIFO", "@VIFO"], ["nhom", "ma:NT01", "@Basa"], ["doi_thu", "VI", "@VI "], ["nhom", "ma:NT02", "@Tom"]) };
    expect(ghepTin(t).map(d => [d.doi_thu?.ma, d.nhom?.khoa])).toEqual([["VIFO", "ma:NT01"], ["VI", "ma:NT02"]]);
  });
  it("nhóm / đối thủ đã đổi tên sau khi ghi: cặp vẫn đúng, in tên HIỆN HÀNH", () => {
    const cau = "@VIFO bán @Tom, @THAK bán @Basa";           // chữ trong câu là tên CŨ của n:9
    const t: TinDoiThu = { tiep_xuc_id: 3, ngay: "2026-09-12", nguoi: null, noi_dung: cau, gia: [],
      doi_thu: [{ ma: "THAK", ten: "THAK Holdings" }, { ma: "VIFO", ten: "Việt Foods" }],
      nhom: [{ khoa: "ma:NT02", ten: "Tom" }, { khoa: "n:9", ten: "Cá basa (mới)" }],
      nhac: luu(cau, ["doi_thu", "VIFO", "@VIFO"], ["nhom", "ma:NT02", "@Tom"], ["doi_thu", "THAK", "@THAK"], ["nhom", "n:9", "@Basa"]) };
    expect(dongDangMua([t])).toEqual(["đang mua @VIFO: Tom (12/09)", "đang mua @THAK: Cá basa (mới) (12/09)"]);
  });
  it("câu 'đang mua @THAK: Basa (¥1,200/kg, 12/09)', bỏ trùng cặp giữ tin mới nhất", () => {
    const cu: TinDoiThu = { ...tin, tiep_xuc_id: 0, ngay: "2026-08-01" };
    expect(dongDangMua([tin, cu])).toEqual([
      "đang mua @THAK: Ca Ba sa (¥1,200/kg, 12/09)", "đang mua @VIFO: Nhóm cá (12/09)"]);
  });
  it("lý do ngừng mua", () => {
    expect(dongNgungMua({ ma: "NT01", ten: "Basa", nhom_khoa: "ma:NT01", ten_nhom: "Basa", lan_cuoi: "2026-06-21", so_ngay: 40,
      tiep_xuc_id: 1, tin_ngay: "2026-09-12", doi_thu: [{ ma: "THAK", ten: "THAK JSC" }] }))
      .toBe("Đã ngừng mua Basa (40 ngày chưa mua) — tin 12/09: đang lấy của THAK");
    expect(dongNgungMua({ ma: "NT01", ten: "Basa", nhom_khoa: "ma:NT01", ten_nhom: "Basa", lan_cuoi: "2026-06-21", so_ngay: 40,
      tiep_xuc_id: 1, tin_ngay: "2026-09-12", doi_thu: [] }))
      .toBe("Đã ngừng mua Basa (40 ngày chưa mua) — tin 12/09 có nhắc tới mã này");
  });
});

describe("thanGhi — thân POST", () => {
  it("không có @: ĐÚNG bốn khoá cũ, không nhac / gia", () => {
    const r = thanGhi("goi", "tot", "Gọi lại tuần sau", "2026-10-01", [], { "ma:NT01": { gia: "100", don_vi: "kg" } });
    expect(r.loi).toBeNull();
    expect(r.than).toEqual({ kieu: "goi", ket_qua: "tot", noi_dung: "Gọi lại tuần sau", hen_lai: "2026-10-01" });
    expect(Object.keys(r.than!)).toEqual(["kieu", "ket_qua", "noi_dung", "hen_lai"]);
  });
  it("có thẻ không giá: thêm nhac, không có khoá gia", () => {
    const r = thanGhi("goi", "tot", "@THAK ", "", [dt("THAK", 0)], {});
    expect(r.than).toEqual({ kieu: "goi", ket_qua: "tot", noi_dung: "@THAK ", hen_lai: "",
      nhac: [{ loai: "doi_thu", khoa: "THAK", vi_tri_dau: 0, do_dai: 5 }] });
  });
  it("giá thiếu đối thủ: loi, không có thân", () => {
    const r = thanGhi("goi", "tot", "@Basa", "", [nh("ma:NT01", "Basa", 0)], { "ma:NT01": { gia: "1", don_vi: "kg" } });
    expect(r.than).toBeNull();
    expect(r.loi).toContain("Basa");
  });
});
