// Kiểu dữ liệu của /api/san-pham, /api/san-pham/{mã}, /api/san-pham/{mã}/ngay,
// /api/kho-hang (kome/san_pham.py). Số lượng CÓ phần thập phân; `ton` null =
// "chưa rõ tồn" (không có dòng nào trong 在庫一覧) — KHÁC 0.

export type MaHang = {
  ma: string; ten: string; nhom: string | null; nganh: string;
  doanh_thu: number; lai_gop: number; ty_suat: number | null; so_luong_ban: number | null;
  ton: number | null; toc_do_ngay: number | null; toc_do_ngay_theo_tuoi: number | null;
  du_ban_ngay: number | null; trang_thai: string; nhan_trang_thai: string; mau: string;
  so_khach: number; lan_dau: string | null; lan_cuoi: string | null;
  dt_12t: number; lg_12t: number; ts_12t: number | null; thang_dt: number[]; thang_sl: (number | null)[];
};

export type DanhMucApi = {
  hom_nay: string | null; thang: string[]; ma: MaHang[];
  trang_thai: Record<string, [string, string]>;
};

export type KhachMa = {
  ma: string; ten: string; doanh_thu: number; so_luong: number | null; so_lan: number;
  lan_cuoi: string | null; nhip: number | null; tre: number | null;
};

export type TonDong = {
  kho: string; ten_kho: string | null; so_luong: number | null; gia_tri: number;
  best_before: string | null; loai_han: string | null; nhan_han: string; mau_han: string;
  han_con_lai: number | null;
};

export type HoSoSpApi = {
  h: {
    sp: MaHang;
    thang: { thang: string; so_luong: number | null; doanh_thu: number | null; lai_gop: number | null }[];
    khach_mua: KhachMa[]; khach_ngung: KhachMa[]; ton: TonDong[];
    bac_gia: { bac: string; quy_cach: string; gia: number; tu_ngay: string | null }[];
  };
};

export type NgayBan = { ngay: string; la_ngay_kd: boolean; so_luong: number; doanh_thu: number; lai_gop: number; so_khach: number };
export type NgayApi = { thang: string; hom_nay: string | null; nay: NgayBan[]; truoc: NgayBan[] };

export type DongKho = TonDong & {
  ma: string; ten: string; trang_thai: string | null; nhan_trang_thai: string; mau: string;
  nhom: string | null; du_ban_ngay: number | null; toc_do: number | null;
};

export type KhoApi = {
  k: {
    ngay_chup: string | null; o_tong_quan: Record<string, number>; dong: DongKho[];
    theo_kho: { ma: string; ten: string; gia_tri: number; so_dong: number }[];
    can_han: DongKho[]; qua_han: DongKho[]; ds_kho: [string, string][];
    kho: string; loc: string; gia_tri_ton: number;
  };
  trang_thai: Record<string, [string, string]>;
  loai_han: Record<string, [string, string]>;
  can_han_ngay: number;
};
