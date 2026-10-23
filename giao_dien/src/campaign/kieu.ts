// Dạng bản campaign do máy công ty gửi lên (kome/campaign.py::kiem, phien_ban 1). Ngày là chuỗi ISO YYYY-MM-DD.
export type Nhom = "uu_tien" | "day_han" | "thuong" | "can_nhip" | "hoan" | "loai" | "nghi";   // hoan: thêm 2026-10-23
// `tren_sheet` (thêm 2026-10-23, có thể vắng ở bản cũ): mã đang có trên tab tháng của tuần đó.
// `so` (thêm 2026-10-23, kome/campaign.py::_kiem_so): CÙNG nội dung `ly` tách thành ô cho bảng — mọi khoá tuỳ chọn;
// vắng `so` (bản cũ) thì dòng in nguyên câu `ly`.
export type LoVe = { ngay: string; sl: number; tt?: string };
export type SoMa = {
  ton?: number; ngay?: number;          // thùng đầu tuần · số ngày bán còn lại (script kẹp ≤ 999)
  lo?: LoVe; han?: LoVe;                // lô sắp về gần nhất · lô không kịp bán trước hạn (ngày = hạn dùng)
  bien?: number;                        // tỷ lệ lãi ở giá sàn (0.27)
  // ¥ lãi gộp thêm của MỘT LẦN sale (tuần sale + tuần ngay sau, so tuần thường cùng mùa); uoc = chưa đo được (ước);
  // tuan_do = số lần đo · lan_loi = số lần lời · on_dinh "loi"/"lo" = ≥ 4 lần, ≥ 75% cùng dấu, "" = lúc lời lúc lỗ
  lai?: number; uoc?: boolean; tuan_do?: number; lan_loi?: number; on_dinh?: string;
  mua?: number;                         // cùng kỳ năm trước ÷ bình thường — chỉ có khi lệch rõ
  ngan?: string; canh?: string; ngung?: boolean;   // lý do ngắn (nhóm Không chạy) · cảnh báo lô · ※終売※ bán nốt tồn
  // 目玉商品 (2026-10-23): trang campaign "kho" (hangkho) / "lanh" (hanglanh) · khách mua 90 ngày · giá 標準 / セール · %OFF
  // (0.079) · ngày bán kể cả lô về trong 4 tuần · medama = hạng 目玉 trong trang (1 = đầu trang; vắng = mã phụ)
  trang?: string; khach?: number; gia_std?: number; gia_san?: number; off?: number; ngay_lo?: number; medama?: number;
};
export type MaKeHoach = { ma: string; ten: string; nhom: Nhom; ly: string; chon: boolean; tren_sheet?: boolean; so?: SoMa };
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
