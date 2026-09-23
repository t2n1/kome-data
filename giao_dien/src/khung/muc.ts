// Mục điều hướng — ĐÚNG sáu nhóm, thứ tự, nhãn và icon của `NHOM` trong
// kome-nav.js (gói thiết kế). `url: null` = màn chưa có (nhóm C / thiếu nguồn
// dữ liệu, lộ trình §4.1): hiện mờ, không bấm được — không giả vờ có. Bốn màn
// bị cắt khỏi phạm vi (lộ trình §4.2: web đặt hàng khách, mẫu chứng từ, thị
// trường & đối thủ, sale mobile) KHÔNG hiện.
import { KD } from "../khoi_dau";

export type Muc = { ma: string; nhan: string; url: string | null; icon: string; ly_do?: string };
export type Nhom = { ma: string; ten: string; muc: Muc[] };

const CHUA = "chưa có dữ liệu";

export function nhomDieuHuong(): Nhom[] {
  const nhom: Nhom[] = [
    { ma: "tongquan", ten: "TỔNG QUAN", muc: [
      { ma: "dashboard", nhan: "Dashboard", url: "/", icon: "dashboard" },
      { ma: "baocao", nhan: "Báo cáo doanh thu", url: "/bao-cao", icon: "chart" },
      { ma: "dubao", nhan: "Dự báo doanh thu", url: "/du-bao", icon: "target" },
      ...(KD.hien_ngan_sach ? [{ ma: "ngansach", nhan: "Ngân sách", url: "/ngan-sach", icon: "yen" }] : []),
      { ma: "hieusuat", nhan: "Hiệu suất đội sale", url: null, icon: "team", ly_do: CHUA },
    ] },
    { ma: "khachhang", ten: "KHÁCH HÀNG", muc: [
      { ma: "kh360", nhan: "Khách hàng & bản đồ", url: "/khach-hang", icon: "user" },
      { ma: "bando", nhan: "Bản đồ khách hàng", url: "/ban-do", icon: "pin" },
      { ma: "crm", nhan: "Cần liên hệ", url: "/lien-he", icon: "crm" },
    ] },
    { ma: "banhang", ten: "BÁN HÀNG", muc: [
      { ma: "baogia", nhan: "Báo giá & bảng giá", url: null, icon: "quote", ly_do: CHUA },
      { ma: "lendon", nhan: "Lên đơn hàng", url: null, icon: "cart", ly_do: CHUA },
    ] },
    { ma: "giaothu", ten: "GIAO & THU TIỀN", muc: [
      { ma: "giaohang", nhan: "Giao hàng & điều phối", url: null, icon: "truck", ly_do: CHUA },
      { ma: "congno", nhan: "Công nợ & thu tiền", url: null, icon: "yen", ly_do: CHUA },
      { ma: "trahang", nhan: "Trả hàng & khiếu nại", url: null, icon: "back", ly_do: CHUA },
      { ma: "dongtien", nhan: "Dòng tiền & phải trả", url: null, icon: "yen", ly_do: CHUA },
    ] },
    { ma: "hanghoa", ten: "HÀNG HÓA & KHO", muc: [
      { ma: "kho", nhan: "Kho hàng", url: "/kho-hang", icon: "box" },
      { ma: "muahang", nhan: "Mua hàng & NCC", url: null, icon: "refill", ly_do: CHUA },
      { ma: "sanpham", nhan: "Sản phẩm", url: "/san-pham", icon: "cube" },
    ] },
    { ma: "hethong", ten: "HỆ THỐNG", muc: [
      ...(KD.hien_kho ? [{ ma: "khodl", nhan: "Kho dữ liệu", url: "/kho-du-lieu", icon: "db" }] : []),
      { ma: "nhatky", nhan: "Nhật ký thao tác", url: "/nhat-ky", icon: "cal" },
      { ma: "caidat", nhan: "Cài đặt", url: "/cai-dat", icon: "gear" },
    ] },
  ];
  return nhom;
}

/** Mục đang mở theo đường dẫn — dài nhất khớp trước ("/khach-hang/0001" -> kh360). */
export function mucDangMo(duong: string): string {
  let tot = "", dai = -1;
  for (const g of nhomDieuHuong()) for (const m of g.muc) {
    if (!m.url) continue;
    const khop = m.url === "/" ? duong === "/" : duong === m.url || duong.startsWith(m.url + "/");
    if (khop && m.url.length > dai) { tot = m.ma; dai = m.url.length; }
  }
  return tot;
}
