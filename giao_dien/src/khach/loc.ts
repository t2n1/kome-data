// Trạng thái lọc của màn Khách hàng — MỘT nguồn cho cả tab Danh sách và tab
// Bản đồ, nằm trên URL (chia sẻ được, nút Back chạy đúng). Bất biến của
// /ban-do cũ ("mọi liên kết rời bản đồ sang danh sách phải mang tat_ca/nv")
// được giữ bằng CẤU TRÚC: bấm một tỉnh chỉ ĐỔI `tinh` và tab trên chính trạng
// thái này, nên bộ lọc người phụ trách không có cách nào rơi mất.
import { useCallback, useEffect, useState } from "react";

export type BoLoc = {
  tim: string; loc: string; nhom: string; hang: string[]; tinh: string; nv: string;
  tat_ca: boolean; thang: string; sap: string; giam: "" | "1" | "0"; trang: number; co: number;
  chi_so: string;
};

export const MAC_DINH: BoLoc = {
  tim: "", loc: "", nhom: "", hang: [], tinh: "", nv: "", tat_ca: false, thang: "",
  sap: "doanh_thu", giam: "", trang: 1, co: 50, chi_so: "khach",
};

export function docUrl(search: string): BoLoc {
  const q = new URLSearchParams(search);
  return {
    tim: q.get("tim") ?? "", loc: q.get("loc") ?? "", nhom: q.get("nhom") ?? "",
    hang: (q.get("hang") ?? "").split(",").filter(Boolean), tinh: q.get("tinh") ?? "",
    nv: q.get("nv") ?? "", tat_ca: q.get("tat_ca") === "1", thang: q.get("thang") ?? "",
    sap: q.get("sap") ?? "doanh_thu", giam: (q.get("giam") as BoLoc["giam"]) ?? "",
    trang: Math.max(1, +(q.get("trang") ?? 1) || 1), co: +(q.get("co") ?? 50) || 50,
    chi_so: q.get("chi_so") ?? "khach",
  };
}

/** Chuỗi query CHỈ gồm tham số khác mặc định. `bo` = các khoá bỏ ra (vd bản đồ
 *  không cần `sap`/`trang`). */
export function chuoiLoc(b: BoLoc, bo: (keyof BoLoc)[] = []): string {
  const q = new URLSearchParams();
  const dat = (k: keyof BoLoc, v: string) => { if (!bo.includes(k) && v) q.set(k, v); };
  dat("tim", b.tim.trim()); dat("loc", b.loc); dat("nhom", b.nhom); dat("hang", b.hang.join(","));
  dat("tinh", b.tinh); dat("nv", b.nv); dat("tat_ca", b.tat_ca ? "1" : ""); dat("thang", b.thang);
  dat("sap", b.sap === "doanh_thu" ? "" : b.sap); dat("giam", b.giam);
  dat("trang", b.trang > 1 ? String(b.trang) : ""); dat("co", b.co !== 50 ? String(b.co) : "");
  dat("chi_so", b.chi_so === "khach" ? "" : b.chi_so);
  return q.toString();
}

/** Tham số API danh sách (bỏ `chi_so` — của bản đồ). */
export const thamSoDs = (b: BoLoc) => chuoiLoc(b, ["chi_so"]);
/** Tham số API bản đồ: chỉ người phụ trách + chỉ số. */
export const thamSoBanDo = (b: BoLoc) => {
  const q = new URLSearchParams();
  if (b.nv) q.set("nv", b.nv);
  if (b.tat_ca) q.set("tat_ca", "1");
  if (b.chi_so !== "khach") q.set("chi_so", b.chi_so);
  return q.toString();
};

export type Tab = "danh_sach" | "ban_do";

/** Trạng thái lọc + tab, đồng bộ với URL. `dat(sua, day)`: `day` = thêm mốc
 *  lịch sử (đổi tab, bấm tỉnh) — còn gõ tìm / đổi trang thì thay tại chỗ. */
export function useBoLoc() {
  const doc = () => ({ tab: (location.pathname.startsWith("/ban-do") ? "ban_do" : "danh_sach") as Tab,
                       b: docUrl(location.search) });
  const [tt, datTt] = useState(doc);
  useEffect(() => {
    const f = () => datTt(doc());
    addEventListener("popstate", f);
    return () => removeEventListener("popstate", f);
  }, []);
  const dat = useCallback((sua: Partial<BoLoc> & { tab?: Tab }, day = false) => {
    datTt(cu => {
      const { tab = cu.tab, ...phan } = sua;
      // Đổi bất kỳ bộ lọc nào (không phải chính số trang) là về trang 1.
      const b = { ...cu.b, ...phan, trang: "trang" in phan ? phan.trang! : 1 };
      const q = chuoiLoc(b);
      const url = (tab === "ban_do" ? "/ban-do" : "/khach-hang") + (q ? "?" + q : "");
      if (url !== location.pathname + location.search) history[day ? "pushState" : "replaceState"](null, "", url);
      return { tab, b };
    });
  }, []);
  return { tab: tt.tab, b: tt.b, dat };
}

// Danh sách vừa xem (để hồ sơ có ‹ n/N ›) — tiện nghi riêng máy này.
const KHOA_DS = "kome_kh_ds_v1";
export function nhoDanhSach(ma: string[], url: string) {
  try { sessionStorage.setItem(KHOA_DS, JSON.stringify({ ma, url })); } catch { /* */ }
}
export function docDanhSach(): { ma: string[]; url: string } | null {
  try { return JSON.parse(sessionStorage.getItem(KHOA_DS) || "null"); } catch { return null; }
}
