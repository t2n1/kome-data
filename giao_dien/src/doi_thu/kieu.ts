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
  // Liên kết nguồn (đợt 3, đặc tả §11): dòng `tay` có `thang_lo`/`lien_ket_thu_muc` = null.
  thang_lo: string | null; lien_ket_thu_muc: string | null; web_ben: string | null; lien_ket_bang_chung: string | null;
  // Đợt 4b (quy cách / bậc giá / giá theo đơn vị bán): null = chưa biết, KHÔNG phải 0.
  so_goi_thung: number | null; kl_goi_g: number | null; bac: Bac[] | null; kg_thung_dt: number | null;
  gia_goi: number | null; gia_thung: number | null; gia_1: number | null; gia_5: number | null; gia_10: number | null;
  gia_pallet: number | null; sua_cuoi: number; gia_kome_so?: number | null;
};
export type Bac = { tu: number; don_vi_sl: "thung" | "kg" | "goi" | "pallet"; gia: number; don_vi_gia: "thung" | "kg" | "goi" };
export type Nhom = {
  nhom_khoa: string; ten_nhom: string | null; nganh: string | null; don_vi_so: string; ma_kome: string[] | null; gia_kome: number | null;
  so_ben: number; thap_nhat: number; ben_thap_nhat: string; trung_vi: number; cao_nhat: number;
  ty_le_re_hon_kome: number | null; quan_sat: QuanSat[];
  gia_kome_chuan: number | null; gia_kome_bang: Record<string, number> | null; gia_kome_km: number | null;
  gia_kome_so: number | null; lech_trung_vi: number | null; gia_kome_lech: boolean;
  kome_kg_goi: number | null; kome_goi_thung: number | null; kome_kg_thung: number | null;
};
export type Ben = { ma: string; ten: string; web: string | null; ngay_moi: string | null; hinh_thuc: string | null;
                    so_dong: number; cho_duyet: number };
export type TongQuan = {
  ben: Ben[]; luoi: { ben: string; nganh: string; so_ma: number }[];
  khuyen_mai: { nguon: "nap" | "tay"; id: number; ma_hang_dt: string; ma_doi_thu: string; ben: string; ten_goc: string;
                gia_goc: number | null; gia_truoc_km: number | null; khuyen_mai: string | null; ngay: string }[];
  dieu_kien: DieuKien[];
  het_hang: { nguon: "nap" | "tay"; id: number; ma_hang_dt: string; ma_doi_thu: string; ten_doi_thu: string | null;
              ben: string; ten_goc: string; ma_kome: string; ten_nhom: string | null; trang_thai: string }[];
  hien_truong?: HienTruong;
};
export const NHAN_DUYET: Record<QuanSat["trang_thai_duyet"], string> = {
  ai_doc: "AI đọc", can_xem: "Cần xem", da_xac_nhan: "Đã xác nhận", da_sua: "Đã sửa", nhap_tay: "Nhập tay" };
export const NHAN_TRANG_THAI: Record<string, string> = { con: "Còn", het: "Hết", sap_ve: "Sắp về", khong_ro: "?" };
export type NhomCoTen = { id: number; ten: string; ma: { ma: string; ten: string | null }[] };
export type QuyCach = { ma: string; ten: string | null; nganh: string; kg_moi_goi: number | null; goi_moi_thung: number | null;
                        kg_moi_thung: number | null; da_sua: boolean };
export type NhomQuyCach = { nhom: NhomCoTen[]; quy_cach: QuyCach[] };

// ---- Đợt 2 — tin hiện trường `@` (kome/doi_thu.py: goi_y_nhac, khach_doi_thu, ho_so_ben, tong_quan) ----
/** GET /api/doi-thu/goi-y-nhac — đối thủ đang theo dõi + nhóm có tên (`n:<id>`) rồi mã KOME (`ma:<mã>`). */
export type GoiYApi = { doi_thu: { ma: string; ten: string }[];
                        // Mã (`loai = 'ma'`) mang `ma`; mã thuộc nhóm có tên có khoá NHÓM `n:<id>` + `ten_nhom` (mart.nhom_cua_khoa).
                        hang: { khoa: string; ten: string; loai: "nhom" | "ma"; ma?: string; ten_nhom?: string }[] };
export type GiaKhachKe = { ma_doi_thu: string; ten_doi_thu: string | null; nhom_khoa: string; ten_nhom: string | null;
                           gia_goc: number; don_vi_gia: string };
/** Đơn vị giá máy chủ nhận (kome/doi_thu.py, mã không dấu) → nhãn in ra. Dùng chung ô ghi tiếp xúc và các khối đọc. */
export const DON_VI: Record<string, string> = {
  kg: "kg", goi: "gói", thung: "thùng", tui: "túi", con: "con", qua: "quả", lon: "lon", chai: "chai", hop: "hộp",
  cay: "cây", bao: "bao", khac: "khác" };
export const nhanDonVi = (m: string) => DON_VI[m] ?? m;
/** Thẻ của một tin đã lưu, sắp theo `vi_tri_dau`. Vị trí / độ dài theo KÝ TỰ Unicode (code point, như
 *  app.tiep_xuc_nhac) — KHÁC đơn vị UTF-16 của POST; muốn tô chữ phải đổi (hiện không tô). */
export type NhacDaLuu = { loai: "doi_thu" | "nhom"; khoa: string; vi_tri_dau: number; do_dai: number };
/** Một lần tiếp xúc CÓ thẻ `@` (90 ngày); ghép cặp ở nhac.ts::ghepTin từ `nhac` (thứ tự trong câu). */
export type TinDoiThu = { tiep_xuc_id: number; ngay: string; nguoi: string | null; noi_dung: string; nhac: NhacDaLuu[];
                          doi_thu: { ma: string; ten: string }[]; nhom: { khoa: string; ten: string | null }[]; gia: GiaKhachKe[] };
export type LyDoNgung = { ma: string; ten: string; nhom_khoa: string; ten_nhom: string | null; lan_cuoi: string; so_ngay: number;
                          tiep_xuc_id: number; tin_ngay: string; doi_thu: { ma: string; ten: string }[] };
/** GET /api/khach-hang/{ma}/doi-thu */
export type KhachDoiThu = { tin: TinDoiThu[]; ly_do_ngung: LyDoNgung[] };
/** `khach_dang_mua` của GET /api/doi-thu/ben/{ma} — mỗi phần tử một lần tiếp xúc nhắc bên này. */
export type KhachDangMua = { tiep_xuc_id: number; ma_khach: string; ten_khach: string | null; ngay: string;
                             nhom: { khoa: string; ten: string | null }[];
                             gia: { nhom_khoa: string; ten_nhom: string | null; gia_goc: number; don_vi_gia: string }[] };
/** `hien_truong` của GET /api/doi-thu/tong-quan — đếm SỐ TIN (không đếm thẻ). */
export type HienTruong = { ngay: number; tong: number; doi_thu: { ma: string; ten: string; so_tin: number }[];
                           nhom: { khoa: string; ten: string | null; so_tin: number }[]; tinh: { tinh: string; so_tin: number }[] };

// ---- Đợt 4b — lịch sử sửa, điều kiện, phí & giao hàng (đặc tả 2026-09-29-doi-thu-dot-4b) ----
export type LichSu = { id: number; loai: string; doi_tuong: string; ai: string | null; luc: string; truoc: unknown; sau: unknown };
export type DieuKien = { id: number; fact_id: number | null; ben: string; loai: string; noi_dung: string; ngay: string; them_tay: boolean };
export type GiaoHang = { ma_doi_thu: string; ten: string | null; bao_ship: boolean | null; phi_ship: number | null;
  phi_ship_theo: "don" | "thung" | "kien" | null; mien_ship_tu: number | null; mien_ship_kien: number | null;
  thung_moi_kien: number | null; phu_phi: Record<string, number | "khong_nhan"> | null; phi_daibiki: number | null;
  daibiki_tu: number | null; daibiki_sau: number | null; ck_mien_daibiki: boolean | null; kien_toi_da_kg: number | null;
  ghep_kien: string | null; thue: "bao" | "chua" | "khong_ro" | null; cach_gui: string | null; nguon_chu: string | null;
  ngay_nguon: string | null; suy: boolean; da_xac_nhan: boolean; sua_cuoi: number };
/** Nhãn hiển thị ↔ mã CSDL (mã KHÔNG đổi): một chỗ duy nhất cho chữ "cùng / khác thương hiệu". */
export const NHAN_GHEP: Record<"cung_hang" | "thay_the", string> = { cung_hang: "cùng thương hiệu", thay_the: "khác thương hiệu" };
/** Thân 409 của mọi POST sửa: người khác vừa sửa dòng này. `sua_cuoi` = dấu phiên bản mới để "Ghi đè". */
export type XungDot = { ai: string | null; luc: string; sau: unknown; sua_cuoi: number };
