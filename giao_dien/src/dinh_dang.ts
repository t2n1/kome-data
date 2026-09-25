// Định dạng số theo gói thiết kế: ¥1.234.567 (chấm nghìn), ¥11,7M (phẩy
// thập phân), 62,9%. Một chỗ — mọi khối dùng chung.

const NGHIN = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 });

export function so(n: number | null | undefined): string {
  return n == null ? "—" : NGHIN.format(Math.round(n));
}

export function yen(n: number | null | undefined): string {
  if (n == null) return "—";
  return (n < 0 ? "−¥" : "¥") + NGHIN.format(Math.abs(Math.round(n)));
}

/** ¥11,7M · ¥980K · ¥1,2B — cho nhãn gọn trên biểu đồ và ô số lớn. */
export function gon(n: number | null | undefined): string {
  if (n == null) return "—";
  const a = Math.abs(n), dau = n < 0 ? "−¥" : "¥";
  const f = (x: number, d = 1) => x.toFixed(d).replace(".", ",");
  if (a >= 1e9) return dau + f(a / 1e9) + "B";
  if (a >= 1e6) return dau + f(a / 1e6) + "M";
  if (a >= 1e4) return dau + f(a / 1e3, 0) + "K";
  return dau + NGHIN.format(Math.round(a));
}

export function pc(ty_le: number | null | undefined, chu_so = 1): string {
  if (ty_le == null || !isFinite(ty_le)) return "—";
  return (ty_le * 100).toFixed(chu_so).replace(".", ",") + "%";
}

/** ▲4,2% / ▼1,1% — tăng giảm có dấu, dùng kèm lớp màu tang/giam. */
export function thay_doi(ty_le: number | null | undefined, chu_so = 1): string {
  if (ty_le == null || !isFinite(ty_le)) return "—";
  return (ty_le >= 0 ? "▲" : "▼") + Math.abs(ty_le * 100).toFixed(chu_so).replace(".", ",") + "%";
}

export function ngay(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export function ngay_ngan(iso: string): string {
  const [, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}`;
}

export function thang_nhan(t: string): string {
  const [y, m] = t.split("-");
  return `T${+m}/${y.slice(2)}`;
}

/** Số lượng (CÓ phần thập phân: 83,75 ケース) — không làm tròn về số nguyên. */
export function so_luong(n: number | null | undefined, chu_so = 2): string {
  return n == null ? "—" : n.toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: chu_so });
}

const GIO_TOKYO = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit",
  day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });

/** "YYYY-MM-DD HH:MM" GIỜ TOKYO của một mốc ISO. `loaded_at` là timestamptz,
 *  máy chủ gửi kèm `+00:00` — cắt chuỗi thẳng là in giờ UTC (nạp lúc 20:33 hiện
 *  11:33, sự cố thật 2026-09-25). Chuỗi không mang múi giờ thì giữ nguyên chữ. */
export function gio_tokyo(iso: string | null | undefined): string {
  if (!iso) return "";
  if (!/(Z|[+-]\d\d:?\d\d)$/.test(iso)) return `${iso.slice(0, 10)} ${iso.slice(11, 16)}`.trim();
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const p = GIO_TOKYO.formatToParts(d), g = (t: string) => p.find(x => x.type === t)?.value ?? "";
  return `${g("year")}-${g("month")}-${g("day")} ${g("hour") === "24" ? "00" : g("hour")}:${g("minute")}`;
}
