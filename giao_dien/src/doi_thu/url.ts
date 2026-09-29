// Trạng thái màn /doi-thu trên URL. Mọi tham số KHÁC (khoảng xem ?thang= ?ss_*, ?nhom= của tab cũ…) được giữ nguyên.
export type Tab = "tom_tat" | "so_sanh" | "ben" | "tin" | "giao_hang" | "duyet" | "nhom" | "lech";
export type TrangThaiUrl = { tab: Tab; ben: string; nganh: string; sp: string[]; sl: "1" | "5" | "10" | "pallet";
  xem: "cot" | "cham" | "nhiet"; gk: string; cung: boolean };

export const TAB_HOP_LE: Tab[] = ["tom_tat", "so_sanh", "ben", "tin", "giao_hang", "duyet", "nhom", "lech"];
const SL: TrangThaiUrl["sl"][] = ["1", "5", "10", "pallet"];
const XEM: TrangThaiUrl["xem"][] = ["cot", "cham", "nhiet"];
export const TOI_DA_SP = 8;

export function docUrl(search: string): TrangThaiUrl {
  const q = new URLSearchParams(search);
  const tab = q.get("tab");
  const sl = q.get("sl"), xem = q.get("xem");
  return {
    tab: (TAB_HOP_LE as string[]).includes(tab ?? "") ? (tab as Tab) : "tom_tat",   // tong_quan cũ / tab lạ → tom_tat
    ben: q.get("ben") ?? "", nganh: q.get("nganh") ?? "",
    sp: (q.get("sp") ?? "").split(",").filter(Boolean).slice(0, TOI_DA_SP),
    sl: (SL as string[]).includes(sl ?? "") ? (sl as TrangThaiUrl["sl"]) : "1",
    xem: (XEM as string[]).includes(xem ?? "") ? (xem as TrangThaiUrl["xem"]) : "cot",
    gk: q.get("gk") || "chuan",
    cung: q.get("cung") === "1",
  };
}

/** "?…" (hoặc "" khi không còn tham số nào). Giá trị mặc định KHÔNG in ra. */
export function vietUrl(t: TrangThaiUrl, search: string): string {
  const q = new URLSearchParams(search);
  const dat = (k: string, v: string, macDinh: string) => { if (v && v !== macDinh) q.set(k, v); else q.delete(k); };
  dat("tab", t.tab, "tom_tat"); dat("ben", t.ben, ""); dat("nganh", t.nganh, "");
  dat("sp", t.sp.slice(0, TOI_DA_SP).join(","), ""); dat("sl", t.sl, "1"); dat("xem", t.xem, "cot");
  dat("gk", t.gk, "chuan"); dat("cung", t.cung ? "1" : "", "");
  const s = q.toString().replace(/%2C/gi, ",");
  return s ? `?${s}` : "";
}
