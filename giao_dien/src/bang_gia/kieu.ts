// Hình dạng /api/bang-gia (kome/bang_gia.py). Giá: yên CHƯA thuế, đã làm tròn ở máy chủ.
export type OGia = {
  gia: number | null;      // null khi bậc bị bỏ (bo)
  truoc: number | null;    // giá ở lần nạp trước; null = bậc chưa có lúc đó (hoặc chưa có lần trước)
  lech: boolean;           // hai cột thuế mâu thuẫn — lấy gồm thuế ÷ 1,08 (071)
  doi: boolean;            // đổi so với lần nạp trước (giá khác / bậc mới / bậc bị bỏ) — cờ của mart.bang_gia_kome
  duoi: boolean;           // dưới giá vốn
  bo: boolean;             // có ở lần trước, lần này không còn
};
export type DongGia = { qc: string; ten_qc: string; tu: string; tu_truoc: string | null; gia_von: number | null; g: Record<string, OGia> };
export type MaGia = { ma: string; ten: string; nganh: string; ngung_ban: boolean; thieu_kg: boolean; dong: DongGia[] };
export type BangGiaApi = { bac: { ma: string; nhan: string }[]; ma: MaGia[]; nganh: string[]; moi_nhat: string | null };
