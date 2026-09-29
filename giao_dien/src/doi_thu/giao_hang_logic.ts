// Logic thuần của tab "Phí & giao hàng" (đặc tả giao diện mới §4.5, §5.4) và phần điều kiện của "Tính cả phí giao" (§5.5).
// Phí của đơn mẫu = phi_giao.ts::tinh (MỘT thuật toán, chung ca với kome/phi_giao.py) — ở đây chỉ gom, xếp, và dựng chữ ô.
import { so, so_luong, yen } from "../dinh_dang";
import type { GiaoHang } from "./kieu";
import { mauLech, phanTram, type MauLech } from "./mau";
import { tinh, type DieuKienGiao, type DonMau, type KetQuaPhi, type Vung } from "./phi_giao";
import type { PhiSoSanh } from "./so_sanh_logic";

export const DON_TIEN = [8000, 15000, 25000, 60000];
export const DON_THUNG = [1, 2, 4];
export const DON_VUNG: [Vung, string][] = [["kanto", "Kanto · Kansai · Chubu"], ["tohoku", "Tohoku"], ["hokkaido", "Hokkaido"],
  ["kyushu", "Kyushu"], ["okinawa", "Okinawa"]];
export const TEN_VUNG: Record<string, string> = { hokkaido: "Hokkaido", tohoku: "Tohoku", kanto: "Kanto", chubu: "Chubu",
  kansai: "Kansai", chugoku: "Chugoku", shikoku: "Shikoku", kyushu: "Kyushu", okinawa: "Okinawa" };
const THU_TU_VUNG = Object.keys(TEN_VUNG);

const SO: (keyof GiaoHang)[] = ["phi_ship", "mien_ship_tu", "mien_ship_kien", "thung_moi_kien", "phi_daibiki", "daibiki_tu",
  "daibiki_sau", "kien_toi_da_kg", "sua_cuoi"];
/** Chuỗi / số từ JSON → số; rỗng, null hoặc không phải số → null (không bao giờ NaN / 0). */
export const soHoac = (v: unknown): number | null => {
  if (v == null || v === "") return null;
  const n = typeof v === "number" ? v : Number(String(v).trim());
  return Number.isFinite(n) ? n : null;
};

/** Ranh giới API: numeric của Postgres có thể về dạng chuỗi — đổi Number() TRƯỚC khi gọi `tinh` (chuỗi "605" cộng vào là
 *  nối chuỗi). Chuỗi không phải số → null ("?"), không bao giờ NaN / 0. Phụ phí vùng: số, hoặc "khong_nhan". */
export function chuanGiao(g: GiaoHang): GiaoHang {
  const r = { ...g } as Record<string, unknown>;
  for (const k of SO) r[k] = k === "sua_cuoi" ? soHoac(g.sua_cuoi) ?? 0 : soHoac(g[k]);
  if (g.phu_phi != null && typeof g.phu_phi === "object") {
    const pp: Record<string, number | "khong_nhan"> = {};
    for (const [v, x] of Object.entries(g.phu_phi)) {
      if (x === "khong_nhan") pp[v] = x;
      else { const n = soHoac(x); if (n != null) pp[v] = n; }
    }
    r.phu_phi = pp;
  }
  return r as GiaoHang;
}

/** GiaoHang → DieuKienGiao của phi_giao.tinh (cùng tên trường; GiaoHang là tập lớn hơn). */
export const dieuKien = (g: GiaoHang): DieuKienGiao => g as unknown as DieuKienGiao;

/** Điều kiện cho "Tính cả phí giao" của tab So sánh: theo ma_doi_thu + dòng KOME. */
export function phiSoSanh(ds: GiaoHang[]): PhiSoSanh {
  const ben = new Map<string, DieuKienGiao>();
  let kome: DieuKienGiao | null = null;
  for (const g of ds) { if (g.ma_doi_thu === "KOME") kome = dieuKien(g); else ben.set(g.ma_doi_thu, dieuKien(g)); }
  return { ben, kome };
}

/** Một thanh của biểu đồ: `tong` = ship + vùng + daibiki (phần đã biết); `lech` = tong − tổng KOME (¥, null khi bên này
 *  hoặc KOME có "?" / không nhận — so nửa vời là nói sai); `mau` theo DẤU của `lech` (phán quyết chủ DN, bản phác
 *  ca-trang-8): khách tốn ít hơn ở bên đó = đỏ (bất lợi KOME), nhiều hơn = xanh, bằng = xám — KHÔNG ngưỡng ±5%. */
export type ThanhPhi = { g: GiaoHang; r: KetQuaPhi; tong: number; kome: boolean; lech: number | null; mau: MauLech | null };

export function thanhPhi(ds: GiaoHang[], don: DonMau): ThanhPhi[] {
  const ra = ds.map((g, i) => {
    const r = tinh(dieuKien(g), don);
    return { g, r, tong: r.ship + r.vung + r.daibiki, kome: g.ma_doi_thu === "KOME", lech: null as number | null, mau: null as MauLech | null, i };
  });
  const K = ra.find(x => x.kome);
  const soDuoc = (x: typeof ra[number]) => !x.r.chua_ro.length && !x.r.khong_nhan;
  if (K && soDuoc(K)) for (const x of ra) if (!x.kome && soDuoc(x)) {
    x.lech = x.tong - K.tong;
    x.mau = x.lech < 0 ? "do" : x.lech > 0 ? "xanh" : "xam";
  }
  ra.sort((a, b) => (+a.r.khong_nhan - +b.r.khong_nhan) || (a.r.chua_ro.length - b.r.chua_ro.length) || (a.tong - b.tong) || a.i - b.i);
  return ra.map(({ i: _i, ...x }) => x);
}

/** Phần "?" của thanh → trường mở sẵn trong pop-up SuaGiaoHang. */
export function truOPhan(phan: string, g: GiaoHang, don: DonMau): string {
  if (phan === "ship") return "phi_ship";
  if (phan === "vùng") return `phu_phi.${don.vung}`;
  return g.daibiki_tu != null && don.tien >= g.daibiki_tu ? "daibiki_sau" : "phi_daibiki";
}

/** Một ô của bảng điều kiện: `k` = trường mở sẵn khi bấm; `chu` null = chưa ai điền ("?" cam); `vang` = "?" vàng (thuế
 *  không rõ — bảng nói là không rõ, khác với chưa điền); `mau` = so với KOME theo mau.ts (chỉ Miễn ship từ). */
export type OBang = { k: string; chu: string | null; vang?: boolean; mau?: MauLech; nhat?: boolean };
const THEO: Record<string, string> = { don: "đơn", thung: "thùng", kien: "kiện" };

export function oBang(g: GiaoHang, K: GiaoHang | undefined): OBang[] {
  const kome = g.ma_doi_thu === "KOME";
  const ship: OBang = g.bao_ship ? { k: "bao_ship", chu: "bao ship (trong giá)" }
    : g.phi_ship != null ? { k: "phi_ship", chu: `${yen(g.phi_ship)}${g.phi_ship_theo ? ` / ${THEO[g.phi_ship_theo]}` : ""}` }
    : { k: "phi_ship", chu: null };
  const mien: OBang = g.bao_ship ? { k: "mien_ship_tu", chu: "—", nhat: true }
    : g.mien_ship_tu != null ? { k: "mien_ship_tu",
        chu: `từ ${yen(g.mien_ship_tu)}${g.mien_ship_kien != null ? ` hoặc ${so(g.mien_ship_kien)} kiện` : ""}`,
        mau: kome || K?.mien_ship_tu == null ? undefined : mauLech(phanTram(g.mien_ship_tu, K.mien_ship_tu)) }
    : g.mien_ship_kien != null ? { k: "mien_ship_kien", chu: `từ ${so(g.mien_ship_kien)} kiện` }
    : { k: "mien_ship_tu", chu: null };
  const pp = g.phu_phi;
  const vung: OBang = pp == null ? { k: "phu_phi", chu: null }
    : { k: "phu_phi", chu: Object.keys(pp).length === 0 ? "không"
        : Object.entries(pp).sort(([a], [b]) => THU_TU_VUNG.indexOf(a) - THU_TU_VUNG.indexOf(b))
            .map(([v, x]) => `${TEN_VUNG[v] ?? v} ${x === "khong_nhan" ? "không nhận" : `+${yen(x)}`}`).join(" · ") };
  const sau = g.daibiki_tu != null
    ? ` (từ ${yen(g.daibiki_tu)}: ${g.daibiki_sau == null ? "?" : g.daibiki_sau === 0 ? "miễn" : yen(g.daibiki_sau)})` : "";
  const dai: OBang = g.phi_daibiki != null ? { k: "phi_daibiki", chu: yen(g.phi_daibiki) + sau }
    : { k: "phi_daibiki", chu: sau ? `?${sau}` : null };
  const ghep: OBang = { k: g.ghep_kien == null && g.thung_moi_kien != null ? "thung_moi_kien" : "ghep_kien",
    chu: g.ghep_kien ?? (g.thung_moi_kien != null ? `${so(g.thung_moi_kien)} thùng / kiện` : null) };
  const kg: OBang = { k: "kien_toi_da_kg", chu: g.kien_toi_da_kg == null ? null : `${so_luong(g.kien_toi_da_kg, 1)} kg` };
  const thue: OBang = g.thue === "bao" ? { k: "thue", chu: "đã gồm" } : g.thue === "chua" ? { k: "thue", chu: "chưa gồm" }
    : { k: "thue", chu: null, vang: g.thue === "khong_ro" };
  return [ship, mien, vung, dai, ghep, kg, thue];
}
