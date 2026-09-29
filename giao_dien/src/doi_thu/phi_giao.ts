// Phí khách trả THÊM cho một đơn mẫu (đặc tả giao diện mới §5.4). MỘT thuật toán, hai bản: file này và kome/phi_giao.py —
// cả hai chạy tests/du_lieu/phi_giao_ca.json; sửa một bản là sửa cả hai. NULL cần tới → `chua_ro`, không cộng 0.
export type Vung = "hokkaido" | "tohoku" | "kanto" | "chubu" | "kansai" | "chugoku" | "shikoku" | "kyushu" | "okinawa";
export type DieuKienGiao = {
  bao_ship: boolean | null; phi_ship: number | null; phi_ship_theo: "don" | "thung" | "kien" | null;
  mien_ship_tu: number | null; mien_ship_kien: number | null; thung_moi_kien: number | null;
  phu_phi: Partial<Record<Vung, number | "khong_nhan">> | null; phi_daibiki: number | null; daibiki_tu: number | null;
  daibiki_sau: number | null; ck_mien_daibiki: boolean | null; kien_toi_da_kg: number | null; ghep_kien: string | null;
  thue: "bao" | "chua" | "khong_ro" | null; cach_gui: string | null;
};
export type DonMau = { tien: number; thung: number; vung: Vung; tra: "daibiki" | "ck" };
export type KetQuaPhi = { ship: number; vung: number; daibiki: number; chua_ro: string[]; khong_nhan: boolean };

const VUNG_GOC: Vung[] = ["kanto", "chubu", "kansai"];

export function tinh(dk: DieuKienGiao, don: DonMau): KetQuaPhi {
  const ra: KetQuaPhi = { ship: 0, vung: 0, daibiki: 0, chua_ro: [], khong_nhan: false };
  const tmk = dk.thung_moi_kien;
  const kien = tmk ? Math.ceil(don.thung / tmk) : 1;
  const mien = (dk.mien_ship_tu != null && don.tien >= dk.mien_ship_tu)
    || (dk.mien_ship_kien != null && don.thung >= dk.mien_ship_kien * (tmk || 1));
  if (!dk.bao_ship && !mien) {
    if (dk.phi_ship == null) ra.chua_ro.push("ship");
    else ra.ship = dk.phi_ship * (dk.phi_ship_theo === "thung" ? don.thung : dk.phi_ship_theo === "kien" ? kien : 1);
  }
  if (!VUNG_GOC.includes(don.vung)) {
    const pp = dk.phu_phi;
    if (pp == null) ra.chua_ro.push("vùng");
    else if (pp[don.vung] === "khong_nhan") ra.khong_nhan = true;
    else if (pp[don.vung] != null) ra.vung = (pp[don.vung] as number) * kien;
  }
  if (don.tra === "daibiki") {
    if (dk.daibiki_tu != null && don.tien >= dk.daibiki_tu) {
      // tới ngưỡng mà không ghi phí sau ngưỡng: chưa rõ, KHÔNG phải miễn (0 mới là miễn)
      if (dk.daibiki_sau == null) ra.chua_ro.push("daibiki");
      else ra.daibiki = dk.daibiki_sau;
    }
    else if (dk.phi_daibiki == null) ra.chua_ro.push("daibiki");
    else ra.daibiki = dk.phi_daibiki;
  }
  return ra;
}
