// Lọc / sắp / đếm danh mục sản phẩm — ở trình duyệt, trên CẢ danh mục (232 mã,
// một ảnh chụp /api/san-pham). Hàm thuần: không đọc DOM, không gọi mạng.
//
// Luật bộ đếm (cùng nếp kome/san_pham.py::danh_sach và kome/khach_hang.py):
// mỗi dải điều khiển đếm theo MỌI bộ lọc TRỪ bộ lọc của chính nó — dải chip
// trạng thái theo `tim` + `nganh` nhưng không theo `loc`; dải ngành hàng theo
// `tim` + `loc` nhưng không theo `nganh`. Tự lọc theo mình thì bấm một chip xong
// các số khác về 0 hết; bỏ qua bộ lọc kia thì con số nói dối về danh sách nó mở.
import type { MaHang } from "./kieu";

// `nganh` = ngành hàng (food_category_name; rỗng đã thành NGANH_TRONG ở máy chủ).
export type LocSp = { tim: string; loc: string; nganh: string; sap: string; giam: "" | "0" | "1" };

export function docLocSp(search: string): LocSp {
  const q = new URLSearchParams(search);
  return { tim: q.get("tim") ?? "", loc: q.get("loc") ?? "", nganh: q.get("nganh") ?? "",
    sap: q.get("sap") ?? "dt_khoang", giam: (q.get("giam") as LocSp["giam"]) ?? "" };
}

export function chuoiLocSp(b: LocSp): string {
  const q = new URLSearchParams();
  if (b.tim.trim()) q.set("tim", b.tim.trim());
  if (b.loc) q.set("loc", b.loc);
  if (b.nganh) q.set("nganh", b.nganh);
  if (b.sap !== "dt_khoang") q.set("sap", b.sap);
  if (b.giam) q.set("giam", b.giam);
  return q.toString();
}

const bo_dau = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\u0111/g, "d").replace(/\u0110/g, "D").toLowerCase();

export function khopTim(m: { ma: string; ten: string; nganh?: string | null }, tim: string): boolean {
  const t = bo_dau(tim.trim());
  if (!t) return true;
  return [m.ma, m.ten, m.nganh ?? ""].some(x => bo_dau(x).includes(t));
}
export const khopNganh = (m: MaHang, nganh: string) => !nganh || m.nganh === nganh;
/** `loc` lạ (không có trong danh sách trạng thái) = KHÔNG lọc — y hệt `_dk_loc` phía máy chủ. */
export const khopLoc = (m: MaHang, loc: string, hop_le: Record<string, unknown>) =>
  !loc || !(loc in hop_le) || m.trang_thai === loc;

// Chiều sắp mặc định của từng cột: câu hỏi của "còn đủ bán" là "cái nào sắp hết
// trước" nên TĂNG dần; còn lại giảm dần. null luôn đứng CUỐI, ở cả hai chiều —
// "không tính được" chưa bao giờ là câu trả lời đáng đứng đầu bảng.
export const SAP: Record<string, { lay: (m: MaHang) => number | string | null; tang: boolean }> = {
  ten: { lay: m => m.ten, tang: true },
  nganh: { lay: m => m.nganh, tang: true },
  trang_thai: { lay: m => m.trang_thai, tang: true },
  ton: { lay: m => m.ton, tang: false },
  toc_do: { lay: m => m.toc_do_ngay_theo_tuoi, tang: false },
  du_ban: { lay: m => m.du_ban_ngay, tang: true },
  dt_12t: { lay: m => m.dt_12t, tang: false },
  dt_khoang: { lay: m => m.dt_khoang ?? null, tang: false },
  sl_khoang: { lay: m => m.sl_khoang ?? null, tang: false },
  kh_khoang: { lay: m => m.kh_khoang ?? null, tang: false },
  so_khoang: { lay: m => m.dt_ss ? (m.dt_khoang ?? 0) / m.dt_ss : null, tang: false },
  doanh_thu: { lay: m => m.doanh_thu, tang: false },
  ty_suat: { lay: m => m.ts_12t, tang: false },
  so_khach: { lay: m => m.so_khach, tang: false },
  lan_cuoi: { lay: m => m.lan_cuoi, tang: false },
};

export function sapXep(ds: MaHang[], sap: string, giam: LocSp["giam"]): MaHang[] {
  const c = SAP[sap] ?? SAP.dt_khoang;
  const tang = giam === "" ? c.tang : giam === "0";
  return [...ds].sort((a, b) => {
    const x = c.lay(a), y = c.lay(b);
    if (x == null && y == null) return a.ma.localeCompare(b.ma);
    if (x == null) return 1;
    if (y == null) return -1;
    const s = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "ja");
    return (tang ? s : -s) || a.ma.localeCompare(b.ma);
  });
}

export function locDanhMuc(ds: MaHang[], b: LocSp, trang_thai: Record<string, unknown>) {
  const theoTim = ds.filter(m => khopTim(m, b.tim));
  const dem_trang_thai: Record<string, number> = {};
  for (const m of theoTim) if (khopNganh(m, b.nganh)) dem_trang_thai[m.trang_thai] = (dem_trang_thai[m.trang_thai] ?? 0) + 1;
  const dem_nganh = new Map<string, number>();
  for (const m of theoTim) if (khopLoc(m, b.loc, trang_thai)) dem_nganh.set(m.nganh, (dem_nganh.get(m.nganh) ?? 0) + 1);
  const hang = sapXep(theoTim.filter(m => khopNganh(m, b.nganh) && khopLoc(m, b.loc, trang_thai)), b.sap, b.giam);
  return { hang, dem_trang_thai, dem_nganh: [...dem_nganh.entries()].sort((a, b) => b[1] - a[1]),
    tong_theo_tim: theoTim.length };
}
