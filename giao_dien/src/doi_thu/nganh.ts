// Tên ngành tiếng Việt — CHỈ để hiển thị. Bộ lọc vẫn gửi tên OBC (`food_category_name`).
// So bằng startsWith: OBC có khi dùng "_" thường, có khi "＿" toàn chiều trước hậu tố nước (VNM / THA).
const NGANH: [string, string][] = [
  ["インスタント食品", "Mì & ăn liền"], ["冷凍食品", "Đông lạnh"], ["冷蔵食品", "Đồ mát"], ["調味料", "Gia vị"],
  ["食材（常温）", "Đồ khô"],
  // "以外" nằm trong ngoặc nên hai ngành đồ uống không là tiền tố của nhau; vẫn xét dài trước cho chắc.
  ["飲料（アルコール以外）", "Nước uống"], ["飲料（アルコール）", "Bia rượu"],
];
export const NGANH_TRONG = "(chưa phân loại)";

export function tenNganh(food_category_name: string | null | undefined): string {
  const s = (food_category_name ?? "").trim();
  if (!s) return NGANH_TRONG;
  for (const [obc, vi] of NGANH) {
    if (s.startsWith(obc)) return /[_＿]THA$/.test(s) ? `${vi} (Thái)` : vi;
  }
  return s;   // "Phí & điều chỉnh", "Hàng tặng (POSM)", "(chưa phân loại)" và mã lạ giữ nguyên
}
