// Kịch bản gọi — văn bản thuần để dán vào LINE / Zalo / ghi chú. Dùng chung
// cho thẻ /lien-he ("Nên chào:") và hồ sơ 360° ("Mã đến ngày mua lại:") —
// hai danh sách mã KHÁC định nghĩa nên tiêu đề do bên gọi truyền vào.
export type MaKichBan = { ten: string; chi_tiet: string };

export const dauKichBan = (ten: string, ma: string, dien_thoai: string | null) =>
  `${ten} (${ma})${dien_thoai ? " ☎ " + dien_thoai : ""}`;

export function kichBanGoi(p: { dau: string; ly_do: string; tieu_de_ma: string; ma: MaKichBan[];
  cuoi: { ngay: string; noi_dung: string } | null }): string {
  const dong = [p.dau, p.ly_do];
  if (p.ma.length) dong.push(p.tieu_de_ma, ...p.ma.map(m => `- ${m.ten} (${m.chi_tiet})`));
  if (p.cuoi) dong.push(`Lần liên hệ trước (${p.cuoi.ngay}): ${p.cuoi.noi_dung}`);
  return dong.join("\n");
}
