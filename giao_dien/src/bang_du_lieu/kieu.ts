// Hình dạng JSON của GET /api/kho-du-lieu/bang-du-lieu (kome/bang_du_lieu.py::doc) và trạng thái ô chưa lưu.
export type Kieu = "chu" | "so" | "ngay" | "chon";
export type Cot = { ma: string; nhan: string; nhom: string; kieu: Kieu; sua: boolean; chon?: [string, string][] };
/** `o[ma_cot]`: chữ máy chủ đã chuẩn hoá. Khoá `gia:` / `ton:` / `han:` VẮNG (hoặc null) = ô OBC không có → không sửa được. */
export type Dong = { k: string; o: Record<string, string | null> };
/** Khoá `"<k>\t<ma_cot>"` — ô mà bản sửa đang thắng OBC. */
export type Lech = Record<string, { obc: string | null; ai: string | null; luc: string | null }>;
export type BangApi = {
  loai: "sp" | "kh"; sua_duoc: boolean; cot: Cot[]; dong: Dong[]; lech: Lech;
  anh_ton: string | null; lan_nap_gia: string | null;
};
export type Cho = Record<string, string>;          // khoaO -> chữ đang gõ (chưa lưu)
/** khoaO -> chữ máy chủ người sửa đã THẤY lúc ô vào chờ (gửi làm `thay`). Cùng tập khoá với `Cho`. */
export type Thay = Record<string, string | null>;
export type ChoLuu = { cho: Cho; thay: Thay };
