// Hình sản phẩm — MỘT nguồn: máy chủ chèn `window.__KOME__.hinh` (mã → URL https) từ
// config/hinh_san_pham.csv (kome/hinh_san_pham.py). Chỉ ./HinhMa.tsx đọc hàm này.
// Không import khoi_dau.ts: Vitest chạy môi trường "node" (không có window lúc nạp mô-đun).
import type { KhoiDau } from "../khoi_dau";

type BanDo = Record<string, string>;

const banDoMacDinh = (): BanDo =>
  (typeof window !== "undefined" ? (window as { __KOME__?: KhoiDau }).__KOME__?.hinh : undefined) ?? {};

/** URL hình của mã (mã là CHỮ — không bao giờ ép số), hoặc null. Chỉ nhận https. */
export function hinhCua(ma: string | null | undefined, bd: BanDo = banDoMacDinh()): string | null {
  if (!ma) return null;
  const u = Object.prototype.hasOwnProperty.call(bd, ma) ? bd[ma] : undefined;
  return typeof u === "string" && u.startsWith("https://") ? u : null;
}

/** Chữ của ô giữ chỗ: chữ cái / chữ số đầu của tên, rơi về mã, cuối cùng "?". */
export function chuDau(ten: string | null | undefined, ma: string | null | undefined): string {
  for (const s of [ten, ma]) {
    const m = (s ?? "").match(/[\p{L}\p{N}]/u);
    if (m) return m[0].toUpperCase();
  }
  return "?";
}
