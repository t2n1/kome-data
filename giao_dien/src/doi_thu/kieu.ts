// Kiểu JSON của /api/doi-thu/* (kome/doi_thu.py). Số đã làm tròn ở máy chủ; định dạng qua dinh_dang.ts.
export type QuanSat = {
  ma_doi_thu: string; ten_doi_thu: string | null; nguon: "nap" | "tay"; id: number; ma_hang_dt: string;
  ngay_nguon: string; hinh_thuc_nguon: string; nguon_file: string | null; vi_tri: string | null;
  ten_goc: string; quy_cach_goc: string | null; gia_goc: number | null; don_vi_gia: string | null;
  kg_moi_don_vi_gia: number | null; thue: string | null; gom_ship: string | null; kenh_gia: string | null;
  muc_gia: string | null; gia_bac: string | null; gia_truoc_km: number | null; trang_thai: string;
  khuyen_mai: string | null; loai_nguon: string; ghi_chu: string | null; ma_kome: string | null;
  nhan: "cung_hang" | "thay_the" | null; nhom_khoa: string | null; ten_nhom: string | null;
  trang_thai_duyet: "ai_doc" | "can_xem" | "da_xac_nhan" | "da_sua" | "nhap_tay";
  yen_chuan: number | null; don_vi_so: string; nen_gia: string; tuoi_ngay: number | null; bat_thuong?: boolean;
};
export type Nhom = {
  nhom_khoa: string; ten_nhom: string | null; don_vi_so: string; ma_kome: string[] | null; gia_kome: number | null;
  so_ben: number; thap_nhat: number; ben_thap_nhat: string; trung_vi: number; cao_nhat: number;
  ty_le_re_hon_kome: number | null; quan_sat: QuanSat[];
};
export type Ben = { ma: string; ten: string; web: string | null; ngay_moi: string | null; hinh_thuc: string | null;
                    so_dong: number; cho_duyet: number };
export type TongQuan = {
  ben: Ben[]; luoi: { ben: string; nganh: string; so_ma: number }[];
  khuyen_mai: { ben: string; ten_goc: string; gia_goc: number | null; gia_truoc_km: number | null; khuyen_mai: string | null; ngay: string }[];
  dieu_kien: { ben: string; loai: string; noi_dung: string; ngay: string }[];
  het_hang: { ben: string; ten_goc: string; ma_kome: string; ten_nhom: string | null; trang_thai: string }[];
};
export const NHAN_DUYET: Record<QuanSat["trang_thai_duyet"], string> = {
  ai_doc: "AI đọc", can_xem: "Cần xem", da_xac_nhan: "Đã xác nhận", da_sua: "Đã sửa", nhap_tay: "Nhập tay" };
export const NHAN_TRANG_THAI: Record<string, string> = { con: "Còn", het: "Hết", sap_ve: "Sắp về", khong_ro: "?" };
