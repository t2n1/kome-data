// Liên kết nguồn (đặc tả §11): web KHÔNG lưu ảnh, chỉ trỏ sang Google Drive / trang của bên.
// Máy chủ đã chặn link không https:// lúc ghi; kiểm LẠI lúc vẽ (dữ liệu cũ / sửa tay không được mở `javascript:`).

export const CAN_BANG_CHUNG = ["chung_tu", "to_roi"] as const;

export function lienKetAnToan(u: unknown): string | null {
  return typeof u === "string" && /^https:\/\/\S+$/.test(u) ? u : null;
}

export function timTrongDrive(tenFile: string): string {
  return "https://drive.google.com/drive/search?q=" + encodeURIComponent(tenFile);
}

export function thangCua(thangLo: string | null): string | null {
  return thangLo ? thangLo.slice(0, 7) : null;
}

export function nhanThang(t: string): string {
  const [y, m] = t.split("-");
  return `Tháng ${Number(m)}/${y}`;
}

export function cacThangCho(dong: { thang_lo: string | null }[]): string[] {
  const s = new Set<string>();
  for (const d of dong) { const t = thangCua(d.thang_lo); if (t) s.add(t); }
  return [...s].sort().reverse();
}
