// Kiểu dữ liệu của /api/cong-no và /api/cong-no/khach/{mã} (kome/cong_no.py).
export type Ben = {
  ma: string; ten: string | null; dieu_kien: string | null; so_du: number; mang_sang: number;
  ban_chiu: number; da_thu: number; lan_thu_cuoi: string | null; lan_ban_cuoi: string | null;
  so_khach: number; sale: string | null; ten_sale: string | null; ky_tu: string; ky_den: string;
};
export type Phieu = {
  ma: string; loai: "phieu" | "truoc_ky"; so: string | null; ngay: string | null; tong: number | null;
  con_lai: number; da_thu: number | null; han: string | null; tuoi: number | null;
  qua_han: number | null; nhom: "d30" | "d60" | "d90" | "d90p" | "truoc_ky";
};
export type TongHop = {
  tong_phai_thu: number; so_ben_no: number; qua_han: number; so_phieu_qua_han: number; so_ben_qua_han: number;
  sap_den_han: number; so_phieu_sap: number; khong_suy_han: number; da_thu_ky: number; ban_chiu_ky: number;
  tra_du: number; so_ben_tra_du: number; tuoi: { nhom: Phieu["nhom"]; nhan: string; tien: number; dem: number }[];
};
export type CachTinh = { so_du: string; fifo: string; tuoi: string; han: string; da_thu: string };
export type CongNoApi = {
  co_du_lieu: boolean; ky_tu: string | null; moc: string | null; tq: TongHop; ben: Ben[]; phieu: Phieu[];
  viec: string[]; cach_tinh: CachTinh; sap_den_han_ngay: number;
};
export type CongNoKhach = {
  co_so: boolean; ben: Ben | null; ben_ma: string; la_chinh?: boolean; phieu: Phieu[]; so_phieu?: number;
  tq: TongHop | null; cach_tinh: CachTinh;
};

/** Nhãn tuổi / hạn của một phiếu — màu đi kèm chữ, không bao giờ màu một mình. */
export function nhanHan(p: Phieu): [string, string] {
  if (p.qua_han == null) return [p.tuoi == null ? "trước kỳ" : `${p.tuoi} ngày · không suy được hạn`, "nhat"];
  if (p.qua_han > 0) return [`quá hạn ${p.qua_han} ngày`, "do"];
  if (p.qua_han === 0) return ["đến hạn hôm mốc", "canh"];
  return [`còn ${-p.qua_han} ngày tới hạn`, "ok"];
}
