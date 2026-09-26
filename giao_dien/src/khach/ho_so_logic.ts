// Logic thuần của hồ sơ 360° (thiết kế lại 2026-09-26). KHÔNG định nghĩa chỉ số:
// mọi hàm chỉ đổi dạng số máy chủ đã tính (lich, ty_le_im_lang, trang_thai).
import type { LichMa } from "./kieu";

export const TAB_HO_SO = [["mat_hang", "Mặt hàng"], ["don_hang", "Đơn hàng"], ["cong_no", "Công nợ"],
  ["ho_so", "Hồ sơ và nhật ký"]] as const;
export type MaTabHoSo = typeof TAB_HO_SO[number][0];

// Hash của bản 5 tab (trước 2026-09-26) — liên kết cũ không được gãy.
const HASH_CU: Record<string, MaTabHoSo> = { tong_quan: "mat_hang", san_pham: "mat_hang" };

export function tabTuHash(hash: string, coCongNo: boolean): MaTabHoSo {
  const h = hash.replace(/^#/, "");
  if (h in HASH_CU) return HASH_CU[h];
  const co = TAB_HO_SO.some(([m]) => m === h) && (h !== "cong_no" || coCongNo);
  return co ? (h as MaTabHoSo) : "mat_hang";
}

/** Câu phân bậc nhịp — nguyên văn của khối "Nhịp mua" cũ (TabTongQuan). */
export function cauNhip(ty_le: number | null): string {
  if (ty_le == null) return "Chưa đủ 3 lần mua để có nhịp — không đoán.";
  if (ty_le < 1) return "Vẫn trong nhịp mua thường lệ.";
  if (ty_le < 2) return "Đã quá ngày mua thường lệ — gọi trước khi trễ hẳn.";
  if (ty_le < 4) return "Im lặng 2–4× nhịp: quá hạn mua lại.";
  return "Im lặng ≥ 4× nhịp: đang mất khách.";
}

export type DongMuaLai = { ma: string; ten: string; con: number; muc: "qua" | "sap" | "xa"; nhan: string };

/** Dòng của khối "Mã đến ngày mua lại" — đọc h.lich.ma (máy chủ đã tính `con`). */
export function dongMuaLai(lich: LichMa[]): DongMuaLai[] {
  return lich.map(x => ({
    ma: x.ma, ten: x.ten, con: x.con,
    muc: x.con < 0 ? "qua" : x.con <= 7 ? "sap" : "xa",
    nhan: x.con < 0 ? `quá ${-x.con} ngày` : x.con === 0 ? "hôm nay" : `còn ${x.con} ngày`,
  }));
}

/** Tiêu đề "Vì sao cần gọi" hay "Tình hình": đọc màu trạng thái đã có
 *  (DanhSach.MAU_TT: canh/do = cần gọi) và nhãn tháng 036 ('tre'). */
export function laCanGoi(mauTrangThai: string | undefined, nhanThang: string | undefined): boolean {
  return mauTrangThai === "canh" || mauTrangThai === "do" || nhanThang === "tre";
}
