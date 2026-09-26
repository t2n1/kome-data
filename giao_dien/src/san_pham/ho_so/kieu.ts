// Kiểu dữ liệu của /api/san-pham/{mã} và bốn tab (kome/san_pham_360.py) — trang
// riêng Sản phẩm 360° (đặc tả 2026-09-26-san-pham-360-trang-rieng-design.md).
import type { SanPhamApi } from "../kieu";   // kiểu `sp` của hồ sơ cũ (HoSoSpApi["h"]["sp"])

export type LoTon = { kho: string; ten_kho: string; so_luong: number | null; gia_tri: number; best_before: string | null;
  loai_han: string; nhan_han: string; mau_han: string; han_con_lai: number | null; vai_tro_lo: string;
  bat_dau_ban_sau: number | null; ban_het_sau: number | null; khong_kip_ban: boolean | null; sap_chuyen_lo: boolean | null };
// `con` = số ngày tới ngày dự kiến mua lại — NULL khi `hom_nay` (mốc dữ liệu) là NULL
// (kho chưa có dòng bán nào). KHÔNG `?? 0`: 0 nghĩa là "đúng hôm nay".
export type KhachMuaLai = { ma: string; ten: string; du_kien: string; con: number | null; nhip: number | null; lan_cuoi: string; doanh_thu: number };
export type KhachNenChao = { ma: string; ten: string; lan_cuoi: string | null; doanh_thu_nganh: number; so_ma_nganh: number };
export type ThangMa = { thang: string; so_luong: number; doanh_thu: number; lai_gop: number; dt_nam_truoc: number };
export type CachTinh = Record<string, string>;

export type HoSoMaApi = { h: {
  sp: SanPhamApi; nganh: string; hom_nay: string | null; thang: ThangMa[]; ton: LoTon[];
  mua_lai: KhachMuaLai[]; mua_lai_tong: number; nen_chao: KhachNenChao[]; nen_chao_tong: number;
  so_dang_mua: number; so_da_ngung: number; ngung_ban: boolean; cach_tinh: CachTinh;
  // Doanh thu / lãi gộp 12 tháng — ĐÚNG cửa sổ `sales_date > hom_nay - 365` của
  // kome/san_pham.py::danh_muc (mart.dong_ban), tính ở MÁY CHỦ — không suy lại
  // từ 24 tháng LỊCH ở trình duyệt (hai cửa sổ khác nhau).
  dt_12t: number; lg_12t: number;
}; quy_cach: Record<string, string> };

export type KhachDong = { ma: string; ten: string; doanh_thu: number; so_luong: number | null; so_lan: number;
  lan_cuoi: string; nhip: number | null; tre: number | null };
export type OTinhMa = { ma_jis: string; ten: string; ten_ngan: string; vung: string; x: number; y: number;
  doanh_thu: number; so_khach: number; bac: number };
export type TabKhachApi = { t: {
  tap_trung: { ma: string; ten: string; doanh_thu: number; ty_trong: number | null; luy_ke: number | null }[];
  top10_ty_trong: number | null;
  tinh: { o: OTinhMa[]; rong: number; cao: number; o_rong: number; o_cao: number; khong_ro: number };
  nguoi: { ma: string; ten: string | null; doanh_thu: number; lai_gop: number; so_khach: number }[];
  khach_moi: { thang: string; moi: number; quay_lai: number }[];
  dang_mua: KhachDong[]; da_ngung: KhachDong[];
}; cach_tinh: CachTinh };
export type TabThoiGianApi = { t: {
  tuan: { tuan: string; so_luong: number; doanh_thu: number }[];
  nhip: { nhom: string; so_cap: number }[];
  co_don: { pack_code: string; quy_cach: string; nhom: string; thu_tu: number; so_dong: number; so_luong: number }[];
}; cach_tinh: CachTinh };
export type TabGiaApi = { t: {
  don_gia: { thang: string; pack_code: string; quy_cach: string; so_luong: number; doanh_thu: number; don_gia: number | null }[];
  bac_gia: { bac: string; quy_cach: string; pack_code: string; gia: number; tu_ngay: string }[];
  khach_gia: { ma: string; ten: string; pack_code: string; so_lan: number; so_luong: number | null; doanh_thu: number;
    lai_gop: number; don_gia: number | null; bien: number | null }[];
}; cach_tinh: CachTinh };
export type TabBanThemApi = { t: {
  mua_kem: { ma: string; ten: string; so_phieu: number; ty_le: number | null }[]; tong_phieu: number;
  nen_chao: KhachNenChao[]; ton: LoTon[];
}; cach_tinh: CachTinh };
