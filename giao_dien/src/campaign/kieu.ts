// Dạng bản campaign do máy công ty gửi lên (kome/campaign.py::kiem, phien_ban 1). Ngày là chuỗi ISO YYYY-MM-DD.
export type Nhom = "uu_tien" | "day_han" | "thuong" | "can_nhip" | "loai" | "nghi";
// `tren_sheet` (thêm 2026-10-23, có thể vắng ở bản cũ): mã đang có trên tab tháng của tuần đó.
export type MaKeHoach = { ma: string; ten: string; nhom: Nhom; ly: string; chon: boolean; tren_sheet?: boolean };
export type TuanKeHoach = {
  tu: string; den: string; tab: string; tuan_so: number; ky: string; ma: MaKeHoach[];
  tren_sheet?: string[] | null;   // null = tuần chưa có trên sheet
};
export type DongSoat = { ma: string; ten: string; pd: string; ly: string; moi: boolean; off: string };
export type TuanSoat = { tu: string; den: string; so_ma: number; dong: DongSoat[] };
export type LichDoi = { kieu: string; ngay: string; trang_thai: string; tieu_de: string; truoc: string | null; ma: string[] };
export type Lo = { ma: string; sl: number; ngay: string; ngay_obc?: string; trang_thai: string; cybozu: string };
export type GoiY = { ma: string; ten: string; ton: number; con_ngay: number; lo_ngay: string; lo_sl: number; trang_thai: string; cach: string };
export type Soat = {
  lan_truoc: string | null; lich_doi: LichDoi[]; tuan: TuanSoat[]; lo_qua_han: Lo[]; lo_lech: Lo[];
  khong_cybozu: { ma: string; ngay: string }[]; goi_y: GoiY[];
};
export type BanCampaign = {
  phien_ban: 1; lap_luc: string; nguon: string; thu_tu_gia: string[]; ke_hoach: TuanKeHoach[]; soat: Soat;
};
export type CampaignApi = { id: number | null; nop_luc: string | null; du_lieu: BanCampaign | null };
