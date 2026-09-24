// Hình dạng JSON của /api/khach-hang/* và /api/ban-do (kome/web/api.py).
import type { KhoangMayChu } from "../khung/khoang";

export type KhachDong = {
  ma: string; ten: string; tinh: string | null; thanh_pho: string | null; dien_thoai: string | null;
  nguoi_phu_trach: string | null; doanh_thu: number; lai_gop: number; ty_suat: number | null;
  lan_cuoi: string | null; so_ngay_im_lang: number | null; nhip_ngay: number | null;
  ty_le_im_lang: number | null; trang_thai: string; dau_hieu_obc: string | null;
  hang: string | null; thang_nay: number | null; thang_truoc_cung_ngay: number | null;
  tb_3_thang: number | null; nhan_thang: string | null;
  dt_khoang: number | null; lg_khoang: number | null; so_phieu_khoang: number | null; dt_ss: number | null;
};

export type NhanVien = { ma: string; ten: string; so_khach: number; doanh_thu: number; canh_bao: number };

export type TongQuan = {
  nhom: Record<"im" | "tut" | "moi", number>; tong: number;
  hang: [string, number][]; tinh: [string, number][]; nhan_vien: NhanVien[];
  dem_trang_thai: Record<string, number>; tong_tat_ca: number;
  hang_tien: Record<string, number>; tinh_tien: Record<string, number>;
  thang: Record<string, number>; chua_pt: number; tinh_day_du: [string, number][]; co_mua: number;
};

export type TrangDs = {
  khach: KhachDong[]; tong: number; trang: number; so_trang: number; sap: string; co: number;
  tong_dt_thang_nay: number; tong_dt_thang_truoc_cung_ngay: number; tong_doanh_thu: number;
  so_can_xu_ly: number; tong_dt_khoang: number; tong_dt_ss: number | null; co_mua: boolean;
};

export type DsApi = {
  trang: TrangDs; tq: TongQuan; sale: string | null; ten_sale: string | null; hom_nay: string | null;
  nhan_trang_thai: Record<string, string>; can_xu_ly: string[]; khong_ro: string; tinh_trong: string;
  nv_moi_nguoi: string; pt_trong: string; nhan_thang: Record<string, string>;
  khoang: KhoangMayChu | null; so_sanh_phu: { ma: string; nhan: string; co: boolean; tu: string; den: string } | null;
};

export type ONhanh = {
  ma_jis: string; ten: string; ten_ngan: string; ten_latin: string; vung: string; hang: number; cot: number;
  so_khach: number; doanh_thu: number; can_goi: number; ty_le_can_goi: number | null;
  gia_tri: number; bac: number; x: number; y: number; dt_khoang: number; khach_mua: number;
};
export type BanDoApi = {
  t: {
    o: ONhanh[]; vung: { vung: string; gia_tri: number }[]; bang: ONhanh[];
    chu_giai: { bac: number; tu: number; den: number; so_tinh: number }[];
    khong_ro_tinh: number; tong: { so_khach: number; doanh_thu: number; can_goi: number };
    chi_so: string; rong: number; cao: number;
  };
  sale: string | null; ten_sale: string | null; chi_so_ds: Record<string, string>; o_rong: number; o_cao: number;
  khoang: KhoangMayChu | null;
};

export type MatHang = {
  ma: string; ten: string; doanh_thu: number; lai_gop: number; so_luong: number; so_lan: number;
  lan_cuoi: string | null; nhip: number | null; du_kien: string | null; tre: number | null;
  trang_thai_cap: string; nganh: string; t2: number; t1: number; t0: number;
};
export type LanTiepXuc = {
  kieu: string; ket_qua: string; noi_dung: string; thoi_diem: string; hen_lai: string | null;
  nguoi: string | null; icon: string; nhan_kieu: string; nhan_ket_qua: string; mau_ket_qua: string; ngay: string;
};
export type LichMa = { ma: string; ten: string; du_kien: string; con: number; nhip: number | null;
  lan_cuoi: string | null; doanh_thu: number; tb_moi_lan: number | null };

export type HoSoApi = {
  khach: KhachDong; hang: string | null; hom_nay: string | null;
  ho_so: Record<string, string | number | null>;
  nhan_trang_thai: Record<string, string>;
  thang_nay: null | { nhan: string; thang: string; dt_thang_nay: number; dt_thang_truoc_den_ngay: number;
    dt_thang_truoc: number; dt_tb_3_thang: number; so_thang_mua_3: number };
  nhan_thang: Record<string, string>; cach_tinh_thang: string;
  dien_giai: string; the: { chu: string; vi: string; mau?: string }[];
  o_so: { dt_30: number; dt_30_truoc: number; so_ma_dang_mua: number; so_ma_ngung: number };
  thang: { thang: string; doanh_thu: number; lai_gop: number; so_lan: number }[];
  tuan: { tu: string; den: string; so_ngay: number; doanh_thu: number }[];
  nganh: { nganh: { nganh: string; doanh_thu: number; lai_gop: number; so_ma: number; ty_trong: number; bien: number | null }[];
    khong_ve: number; so_nganh_khong_ve: number };
  mat_hang: MatHang[];
  da_ngung_mua: MatHang[];
  chua_mua_thang: { ma: string; ten: string; lan_cuoi: string; tre: number | null }[];
  goi_y: { ma: string; ten: string; ty_suat: number | null }[];
  lich: { ma: LichMa[]; so_tre: number; tong: number };
  du_bao: LichMa[];
  lan_mua_gan_day: { ngay: string; so_phieu: number; doanh_thu: number; lai_gop: number }[];
  bac_gia: { ma: string; ten: string; gia: number; quy_cach: string; tu_ngay: string }[];
  diem_giao: { ma: string; ten: string; dia_chi: string }[];
  nhat_ky: LanTiepXuc[];
  kieu_tx: Record<string, [string, string]>;
  ket_qua_tx: Record<string, [string, string]>;
};

export type DongBan = { ngay: string; ma: string; ten: string; quy_cach: string; so_luong: number;
  doanh_thu: number; lai_gop: number; so_phieu: number };
