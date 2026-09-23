import { useQuery } from "@tanstack/react-query";

export class LoiApi extends Error {
  constructor(public ma: number, thong_diep: string) { super(thong_diep); }
}

// fetch() thường: trình duyệt tự gửi If-None-Match và nhận 304 khi dữ liệu
// chưa đổi (máy chủ trả ETag = phiên bản dữ liệu, kome/web/api.py).
export async function lay<T>(url: string): Promise<T> {
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
  return r.json() as Promise<T>;
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

/** Dữ liệu một khối Tổng quan. Chỉ gọi khi khối đang hiện (`bat`). */
export function useKhoi<T>(ma: string, bat = true, tham_so = "") {
  return useQuery<T>({
    queryKey: ["tong-quan", ma, tham_so],
    queryFn: () => lay<T>(`/api/tong-quan/${ma}${tham_so ? "?" + tham_so : ""}`),
    enabled: bat,
  });
}
