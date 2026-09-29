// Logic THUẦN của thẻ `@` trong ô ghi tiếp xúc (đợt 2 — tin hiện trường). Không React, có test (nhac.test.ts).
// `@<đối thủ>` (khoá = app.doi_thu.ma, nhãn = mã) và `@<hàng>` — LUÔN là một nhóm so sánh (R-A): khoá
// `n:<id>` (nhóm có tên) hoặc `ma:<mã KOME>` (nhóm ngầm định theo mã), nhãn = tên.
// Vị trí thẻ là chỉ số chuỗi JS (đơn vị UTF-16) trên câu CHƯA cắt khoảng trắng — đúng đơn vị POST nhận
// (kome/lien_he.py::_kiem_the tự đổi sang ký tự Unicode và trừ khoảng trắng đầu). GET trả lại thẻ đã lưu
// (`tin.nhac`, vị trí theo KÝ TỰ, sắp theo vị trí) — ghép cặp khi hiển thị đi qua CHÍNH `ghepCap` như lúc ghi,
// chỉ cần thứ tự nên không đổi đơn vị; KHÔNG dò chữ trong câu (mã tiền tố VI/VIFO, đổi tên nhóm làm dò sai).
import { ngay_ngan, yen } from "../dinh_dang";
import { boDau } from "../doi_thu/loc";
import { nhanDonVi, type GoiYApi, type LyDoNgung, type TinDoiThu } from "../doi_thu/kieu";

export type { GoiYApi, LyDoNgung, TinDoiThu };

export type LoaiThe = "doi_thu" | "nhom";
/** Một mục của danh sách gợi ý. `phu` = chữ phụ in cạnh nhãn (tên đối thủ, "nhóm", "mã …"). */
export type MucGoiY = { loai: LoaiThe; khoa: string; nhan: string; phu: string; tim: string };
/** Một thẻ đã chọn trong câu: chữ trong câu là "@" + nhan, bắt đầu ở vi_tri_dau (UTF-16). */
export type The = { loai: LoaiThe; khoa: string; nhan: string; vi_tri_dau: number };

/** Ô chọn đơn vị giá chỉ mời ba đơn vị (bảng nhãn đầy đủ: doi_thu/kieu.ts::DON_VI). */
export const DON_VI_CHON = ["kg", "goi", "thung"] as const;

const DAI = (t: The) => t.nhan.length + 1;
const gon = (s: string) => boDau(s).replace(/\s+/g, "");
const CHU = /[\p{L}\p{N}_]/u;
const TU_TOI_DA = 40;

/** Từ đang gõ sau `@` tại con trỏ: `{dau: vị trí của @, tu}` — hoặc null khi con trỏ không nằm trong một
 *  từ `@…` đang gõ (có khoảng trắng chen giữa, `@` dính sau chữ như email, hay đó là một thẻ đã chọn). */
export function tuDangGo(text: string, con_tro: number, the: The[]): { dau: number; tu: string } | null {
  for (let i = con_tro - 1; i >= 0 && con_tro - i <= TU_TOI_DA + 1; i--) {
    const c = text[i];
    if (/\s/.test(c)) return null;
    if (c !== "@") continue;
    if (i > 0 && CHU.test(text[i - 1])) return null;
    if (the.some(t => t.vi_tri_dau <= i && i < t.vi_tri_dau + DAI(t))) return null;
    return { dau: i, tu: text.slice(i + 1, con_tro) };
  }
  return null;
}

/** Danh sách gợi ý phẳng: đối thủ trước, rồi hàng (thứ tự của máy chủ). */
export function dsGoiY(api: GoiYApi): MucGoiY[] {
  return [
    ...api.doi_thu.map(d => ({ loai: "doi_thu" as const, khoa: d.ma, nhan: d.ma, phu: d.ten, tim: gon(d.ma + " " + d.ten) })),
    ...api.hang.map(h => {
      const ma = h.khoa.startsWith("ma:") ? h.khoa.slice(3) : "";
      return { loai: "nhom" as const, khoa: h.khoa, nhan: h.ten || ma || h.khoa,
               phu: h.loai === "nhom" ? "nhóm" : `mã ${ma}`, tim: gon(h.ten + " " + ma) };
    })];
}

/** Lọc không dấu, bỏ khoảng trắng ("basa" khớp "Ca Ba sa"). Đối thủ luôn trước hàng; trong mỗi loại, mục
 *  khớp ĐẦU chữ đứng trước mục khớp giữa chữ. */
export function locGoiY(ds: MucGoiY[], tu: string, toi_da = 10): MucGoiY[] {
  const q = gon(tu);
  const hang = (m: MucGoiY) => (m.loai === "doi_thu" ? 0 : 2) + (q && !m.tim.startsWith(q) ? 1 : 0);
  return ds.map((m, i) => ({ m, i }))
    .filter(({ m }) => !q || m.tim.includes(q))
    .sort((a, b) => hang(a.m) - hang(b.m) || a.i - b.i)
    .slice(0, toi_da).map(x => x.m);
}

/** Thay `@<từ đang gõ>` (từ `dau` tới `con_tro`) bằng `@<nhãn>` + một khoảng trắng (nếu sau đó chưa có). */
export function chenThe(text: string, dau: number, con_tro: number, m: MucGoiY): { text: string; the: The; con_tro: number } {
  const sau = text.slice(con_tro);
  const chen = "@" + m.nhan + (/^\s/.test(sau) ? "" : " ");
  return { text: text.slice(0, dau) + chen + sau, the: { loai: m.loai, khoa: m.khoa, nhan: m.nhan, vi_tri_dau: dau },
           con_tro: dau + chen.length + (/^\s/.test(sau) ? 1 : 0) };
}

/** Sau MỖI lần sửa câu: dò lại vị trí từng thẻ. Thẻ nằm trọn trước / sau đoạn bị sửa thì giữ (dời theo);
 *  thẻ chạm đoạn sửa chỉ giữ khi chữ `@<nhãn>` còn nguyên ở vị trí cũ hoặc vị trí đã dời (mép sửa có chữ
 *  trùng làm phép so đầu/cuối lệch một nấc) — thẻ mất chữ thì bỏ. */
export function doLai(cu: string, moi: string, the: The[]): The[] {
  if (cu === moi || !the.length) return the;
  const n = Math.min(cu.length, moi.length);
  let p = 0;
  while (p < n && cu[p] === moi[p]) p++;
  let s = 0;
  while (s < n - p && cu[cu.length - 1 - s] === moi[moi.length - 1 - s]) s++;
  const lech = moi.length - cu.length, het_cu = cu.length - s;
  const dung = (t: The, vt: number) => vt >= 0 && moi.slice(vt, vt + DAI(t)) === "@" + t.nhan;
  const ra: The[] = [];
  for (const t of the) {
    const a = t.vi_tri_dau;
    const ung = a + DAI(t) <= p ? [a] : a >= het_cu ? [a + lech] : [a, a + lech];
    const vt = ung.find(v => dung(t, v));
    if (vt !== undefined) ra.push(vt === a ? t : { ...t, vi_tri_dau: vt });
  }
  ra.sort((x, y) => x.vi_tri_dau - y.vi_tri_dau);
  return ra.filter((t, i) => i === 0 || ra[i - 1].vi_tri_dau + DAI(ra[i - 1]) <= t.vi_tri_dau);
}

/** Thẻ → phần `nhac` của POST (đơn vị UTF-16, câu chưa cắt). */
export function thanhNhac(the: The[]) {
  return the.map(t => ({ loai: t.loai, khoa: t.khoa, vi_tri_dau: t.vi_tri_dau, do_dai: DAI(t) }));
}

type CoViTri = { loai: LoaiThe; khoa: string; vi_tri_dau: number };

/** Ghép cặp — ĐỊNH NGHĨA DUY NHẤT, dùng cả lúc ghi (điền sẵn ô đối thủ) lẫn lúc đọc (ghepTin): mỗi thẻ hàng (mỗi
 *  khoá một lần — lần xuất hiện đầu) ghép với đối thủ gần nhất đứng TRƯỚC nó trong câu; hàng đứng trước mọi đối
 *  thủ thì ghép với đối thủ DUY NHẤT của câu nếu câu chỉ có một ("@Basa lấy của @THAK"), không thì null. Chỉ đọc
 *  thứ tự `vi_tri_dau` nên đơn vị (UTF-16 lúc ghi, ký tự lúc đọc) không quan trọng. */
export function ghepCap<T extends CoViTri>(the: T[]): { nhom: T; doi_thu: string | null }[] {
  const ra: { nhom: T; doi_thu: string | null }[] = [];
  const cacDt = new Set(the.filter(t => t.loai === "doi_thu").map(t => t.khoa));
  const duyNhat = cacDt.size === 1 ? [...cacDt][0] : null;
  let dt: string | null = null;
  for (const t of [...the].sort((x, y) => x.vi_tri_dau - y.vi_tri_dau)) {
    if (t.loai === "doi_thu") dt = t.khoa;
    else if (!ra.some(c => c.nhom.khoa === t.khoa)) ra.push({ nhom: t, doi_thu: dt ?? duyNhat });
  }
  return ra;
}

/** Ô giá của một dòng hàng (theo khoá nhóm). `doi_thu` = người dùng chọn tay (rỗng / không còn trong câu → ghép sẵn). */
export type DongGia = { gia: string; don_vi: string; doi_thu?: string };

/** Dòng giá → phần `gia` của POST: CHỈ dòng có giá. Có giá mà không có đối thủ → `loi` (không gửi gì). */
export function thanhGia(the: The[], dong: Record<string, DongGia>) {
  const co_dt = new Set(the.filter(t => t.loai === "doi_thu").map(t => t.khoa));
  const gia: { ma_doi_thu: string; nhom_khoa: string; gia_goc: string; don_vi_gia: string }[] = [];
  for (const c of ghepCap(the)) {
    const d = dong[c.nhom.khoa];
    const g = d?.gia.trim() ?? "";
    if (!g) continue;
    const dt = d.doi_thu && co_dt.has(d.doi_thu) ? d.doi_thu : c.doi_thu;
    if (!dt) return { loi: `Chọn đối thủ cho giá của @${c.nhom.nhan} (gõ @đối thủ vào câu trước).`, gia: [] };
    gia.push({ ma_doi_thu: dt, nhom_khoa: c.nhom.khoa, gia_goc: g, don_vi_gia: d.don_vi });
  }
  return { loi: null as string | null, gia };
}

/** Thân POST /api/khach-hang/{mã}/tiep-xuc. KHÔNG có thẻ → ĐÚNG bốn khoá cũ {kieu, ket_qua, noi_dung, hen_lai}
 *  (hành vi trước đợt 2); có thẻ → thêm `nhac`, và `gia` khi có dòng giá. Lỗi dòng giá → `loi`, không gửi. */
export function thanGhi(kieu: string, ket_qua: string, noi_dung: string, hen_lai: string, the: The[],
                        dong: Record<string, DongGia>): { than: Record<string, unknown> | null; loi: string | null } {
  const than: Record<string, unknown> = { kieu, ket_qua, noi_dung, hen_lai };
  if (!the.length) return { than, loi: null };
  const g = thanhGia(the, dong);
  if (g.loi) return { than: null, loi: g.loi };
  than.nhac = thanhNhac(the);
  if (g.gia.length) than.gia = g.gia;
  return { than, loi: null };
}

// ---- Hiển thị (hồ sơ khách) --------------------------------------------------------------------
export type DongTin = { ngay: string; doi_thu: { ma: string; ten: string } | null; nhom: { khoa: string; ten: string } | null;
                        gia: { gia_goc: number; don_vi_gia: string } | null };

/** Một tin → các cặp (đối thủ, nhóm). Giá ghi rõ cặp của nó (người ghi đã chọn); nhóm không giá ghép bằng CHÍNH
 *  `ghepCap` trên `t.nhac` (thứ tự trong câu). Tên lấy theo KHOÁ từ `t.doi_thu` / `t.nhom` (tên hiện hành — đổi tên
 *  không làm lệch cặp). Đối thủ không đi với dòng nào vẫn có một dòng. */
export function ghepTin(t: TinDoiThu): DongTin[] {
  const ra: DongTin[] = [];
  const ten_dt = (ma: string) => t.doi_thu.find(d => d.ma === ma) ?? { ma, ten: ma };
  const ten_nh = (khoa: string, ten?: string | null) => ({ khoa, ten: ten || t.nhom.find(n => n.khoa === khoa)?.ten || khoa });
  for (const g of t.gia)
    ra.push({ ngay: t.ngay, doi_thu: ten_dt(g.ma_doi_thu), nhom: ten_nh(g.nhom_khoa, g.ten_nhom),
              gia: { gia_goc: g.gia_goc, don_vi_gia: g.don_vi_gia } });
  for (const c of ghepCap(t.nhac)) {
    if (ra.some(r => r.nhom?.khoa === c.nhom.khoa)) continue;
    ra.push({ ngay: t.ngay, doi_thu: c.doi_thu ? ten_dt(c.doi_thu) : null, nhom: ten_nh(c.nhom.khoa), gia: null });
  }
  const dsDt = [...new Set(t.nhac.filter(z => z.loai === "doi_thu").map(z => z.khoa))];
  for (const ma of dsDt)
    if (!ra.some(r => r.doi_thu?.ma === ma)) ra.push({ ngay: t.ngay, doi_thu: ten_dt(ma), nhom: null, gia: null });
  return ra;
}

const donVi = nhanDonVi;

export function cauDong(d: DongTin): string {
  const ngoac = [d.gia ? `${yen(d.gia.gia_goc)}/${donVi(d.gia.don_vi_gia)}` : "", ngay_ngan(d.ngay)].filter(Boolean).join(", ");
  if (!d.doi_thu) return `có nhắc ${d.nhom?.ten ?? ""} (${ngoac})`;
  return `đang mua @${d.doi_thu.ma}${d.nhom ? ": " + d.nhom.ten : ""} (${ngoac})`;
}

/** Câu "đang mua @THAK: Basa (¥1,200/kg, 12/09)" — tin mới nhất trước, mỗi cặp một lần (giữ tin mới nhất). */
export function dongDangMua(tin: TinDoiThu[], toi_da = 8): string[] {
  const da = new Set<string>(), ra: string[] = [];
  for (const t of tin) for (const d of ghepTin(t)) {
    const k = (d.doi_thu?.ma ?? "") + "|" + (d.nhom?.khoa ?? "");
    if (da.has(k)) continue;
    da.add(k); ra.push(cauDong(d));
  }
  return ra.slice(0, toi_da);
}

/** "Đã ngừng mua <mã> — tin 12/09: đang lấy của THAK". */
export function dongNgungMua(l: LyDoNgung): string {
  const dt = l.doi_thu.map(d => d.ma).join(", ");
  return `Đã ngừng mua ${l.ten || l.ma} — tin ${ngay_ngan(l.tin_ngay)}` + (dt ? `: đang lấy của ${dt}` : " có nhắc tới mã này");
}
