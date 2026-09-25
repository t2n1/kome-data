// Dữ liệu máy chủ chèn sẵn vào index.html (kome/web/app.py::_khoi_dau) —
// đủ để vẽ khung ngay, không chờ /api.

export type NguoiDung = {
  id: number;
  ten_dang_nhap: string;
  sale: string | null;
  ten_sale: string | null;
  duoc_vao_kho_du_lieu: boolean;
  duoc_sua_ngan_sach: boolean;
  duoc_quan_tri: boolean;
};

export type OBoCuc = { id: string; rong: number; cao: number; an: boolean };
export type MucKhoi = { id: string; nhan: string; rong: number; cao: number; nhom: string; mo_ta: string };

export type KhoiDau = {
  nguoi: NguoiDung | null;
  co_dang_nhap: boolean;
  chi_doc: boolean;
  // Cỡ file tối đa (byte) được gửi lên — chỉ bản Vercel (trần 4,5 MB mỗi yêu cầu), 045.
  gioi_han_tai_len?: number | null;
  hien_kho: boolean;
  hien_ngan_sach: boolean;
  che_do_giao_dien: "sang" | "toi" | "he-thong" | "theo-gio";
  bo_cuc: OBoCuc[];
  sap_xep_duoc: boolean;
  danh_muc: {
    khoi: MucKhoi[];
    nhom: { id: string; nhan: string }[];
    vai_tro: { id: string; nhan: string; khoi: string[] }[];
  };
  chua_co: Record<string, string>;
  // Giai đoạn 5 — màn do máy chủ tính sẵn (route cũ giữ nguyên truy vấn, chỉ đổi
  // cách vẽ): dữ liệu của màn đang mở, trang thông báo (lỗi / không có quyền /
  // bản chỉ-đọc), và cờ "vừa đăng nhập sai".
  man?: unknown;
  thong_bao?: { loai: "loi" | "chi_doc" | "cam_kho_du_lieu" | "cam_ngan_sach" | "cam_cai_dat"; viec?: string };
  dang_nhap_sai?: boolean;
};

declare global {
  interface Window { __KOME__?: KhoiDau }
}

export const KD: KhoiDau = window.__KOME__ ?? {
  nguoi: null, co_dang_nhap: false, chi_doc: false, hien_kho: true, hien_ngan_sach: true,
  che_do_giao_dien: "he-thong", bo_cuc: [], sap_xep_duoc: false,
  danh_muc: { khoi: [], nhom: [], vai_tro: [] }, chua_co: {},
};
