import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { baoKhoangMayChu, chuoiKhoang, docKhoang, useKhoang, type KhoangMayChu } from "./khung/khoang";
import { batDau, docJson } from "./khung/tien_do";

export class LoiApi extends Error {
  constructor(public ma: number, thong_diep: string) { super(thong_diep); }
}

// fetch() thường: trình duyệt tự gửi If-None-Match và nhận 304 khi dữ liệu
// chưa đổi (máy chủ trả ETag = phiên bản dữ liệu, kome/web/api.py).
export async function lay<T>(url: string): Promise<T> {
  const td = batDau();  // thanh tải chung (khung/ThanhTai.tsx)
  try { return await layThat<T>(url, td); } finally { td.xong(); }
}

async function layThat<T>(url: string, td: ReturnType<typeof batDau>): Promise<T> {
  const r = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
  if (r.status === 401) {
    location.href = "/dang-nhap";
    throw new LoiApi(401, "Chưa đăng nhập");
  }
  if (!r.ok) {
    let thong_diep = `Lỗi ${r.status}`;
    try { thong_diep = (await r.json()).loi ?? thong_diep; } catch { /* không phải JSON */ }
    throw new LoiApi(r.status, thong_diep);
  }
  const d = await docJson(r, td);
  // Dữ liệu doanh số mang `khoang` (kome/khoang_xem.py) — báo cho bộ chọn chung
  // để nó in đúng câu mô tả của máy chủ.
  if (d && typeof d === "object" && "khoang" in d)
    baoKhoangMayChu((d as { khoang: KhoangMayChu | null }).khoang, chuoiKhoang(docKhoang(url.split("?")[1] ?? "")));
  return d as T;
}

export async function gui<T>(url: string, du_lieu: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(du_lieu),
  });
  if (r.status === 401) { location.href = "/dang-nhap"; throw new LoiApi(401, "Chưa đăng nhập"); }
  if (!r.ok) {
    let thong_diep = `Lỗi ${r.status}`;
    try { thong_diep = (await r.json()).loi ?? thong_diep; } catch { /* không phải JSON */ }
    throw new LoiApi(r.status, thong_diep);
  }
  return r.json() as Promise<T>;
}

/** Dữ liệu một khối Tổng quan. Chỉ gọi khi khối đang hiện (`bat`). Luôn gắn
 *  khoảng xem đang chọn — khối không theo khoảng (máy chủ: KHOI[..][3] =
 *  False) bỏ qua tham số đó và trả cùng một ảnh chụp. */
export function useKhoi<T>(ma: string, bat = true, tham_so = "") {
  const kx = chuoiKhoang(useKhoang());
  const q = [tham_so, kx].filter(Boolean).join("&");
  return useQuery<T>({
    queryKey: ["tong-quan", ma, tham_so, kx],
    queryFn: () => lay<T>(`/api/tong-quan/${ma}${q ? "?" + q : ""}`),
    enabled: bat,
    // Đổi tháng: giữ số cũ (mờ) tới khi số mới về, không nháy khung trống.
    placeholderData: keepPreviousData,
  });
}
