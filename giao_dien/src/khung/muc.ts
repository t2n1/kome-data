// Mục điều hướng — nhãn và icon theo `NHOM` trong kome-nav.js (gói thiết kế); từ 2026-10-16 NHÓM theo
// tần suất dùng (xem chú thích trong nhomDieuHuong). `url: null` = màn chưa có (nhóm C / thiếu nguồn
// dữ liệu, lộ trình §4.1): hiện mờ, không bấm được — không giả vờ có. Bốn màn
// bị cắt khỏi phạm vi (lộ trình §4.2: web đặt hàng khách, mẫu chứng từ,
// sale mobile) KHÔNG hiện. Từ 2026-09-28 mục `url: null` cũng
// KHÔNG hiện khi công tắc kome/man_chua_co.py::HIEN tắt (mặc định).
// "muavu" (Mùa vụ sản phẩm, 2026-09-29) dùng icon "chart" — TA CHỌN trong bộ 24 icon;
// gói thiết kế không có màn này.
// "doithu" (Thị trường & đối thủ, 2026-09-29) — lộ trình §4.2 từng cắt, đặc tả
// 2026-09-29-thi-truong-doi-thu-design.md §0 đảo lại; dùng icon "target", TA CHỌN (gói thiết kế không có màn này).
// "banggia" (Bảng giá KOME, 2026-09-30) — TÁCH từ mục "Báo giá & bảng giá" của gói thiết kế: phần bảng giá đã có
// (/bang-gia, chỉ xem), phần báo giá vẫn chưa; giữ icon "quote" của mục gốc cho cả hai.
// LỆCH CÓ CHỦ Ý khỏi gói thiết kế (2026-10-16, chủ DN thấy menu rối): bỏ "Bản đồ khách hàng" (tab của Khách hàng);
// "Bảng giá KOME" và "Thị trường & đối thủ" về nhóm HÀNG HÓA & KHO.
import { KD, TN } from "../khoi_dau";

export type Muc = { ma: string; nhan: string; url: string | null; icon: string; ly_do?: string };
export type Nhom = { ma: string; ten: string; muc: Muc[] };

const CHUA = "chưa có dữ liệu";
// Màn có sẵn nhưng công ty chưa dùng nguồn của nó (kome/nguon_dung.py): mờ như màn chưa có.
const CHUA_DUNG = "công ty chưa dùng nguồn này";

const laQuanTri = () => !KD.nguoi || KD.nguoi.duoc_quan_tri;

export function nhomDieuHuong(): Nhom[] {
  // 2026-10-16 (chủ DN: "1 trang có nhiều chức năng quá nên khó xài"): nhóm theo TẦN SUẤT DÙNG thay sáu nhóm nghiệp vụ
  // của gói thiết kế — nhân viên sale chỉ cần nhìn nhóm đầu. Màn chưa có (url null) gom vào "SẮP CÓ", chỉ hiện khi
  // công tắc man_chua_co bật.
  const nhom: Nhom[] = [
    { ma: "hangngay", ten: "HẰNG NGÀY", muc: [
      { ma: "dashboard", nhan: "Tổng quan", url: "/", icon: "dashboard" },
      // Cần gọi (trước 2026-10-16: "Cần liên hệ") = MỌI danh sách làm việc; Khách hàng chỉ còn tra cứu + bản đồ.
      { ma: "crm", nhan: "Cần gọi", url: "/lien-he", icon: "crm" },
      // Bản đồ là TAB của màn Khách hàng (cùng trạng thái lọc); /ban-do vẫn mở được và đánh dấu mục kh360.
      { ma: "kh360", nhan: "Khách hàng", url: "/khach-hang", icon: "user" },
      { ma: "kho", nhan: "Kho hàng", url: "/kho-hang", icon: "box" },
      { ma: "congno", nhan: "Công nợ & thu tiền", url: TN.cong_no ? "/cong-no" : null, icon: "yen", ...(TN.cong_no ? {} : { ly_do: CHUA_DUNG }) },
    ] },
    { ma: "phantich", ten: "PHÂN TÍCH", muc: [
      // 2026-09-30: Báo cáo · Dự báo · Ngân sách gộp thành MỘT trang "Doanh thu" (/du-bao → 301;
      // màn nhập /ngan-sach vào bằng nút "✎ Sửa ngân sách" trên trang, vẫn đánh dấu mục này).
      { ma: "baocao", nhan: "Doanh thu", url: "/bao-cao", icon: "chart" },
      { ma: "sanpham", nhan: "Sản phẩm", url: "/san-pham", icon: "cube" },
      { ma: "muavu", nhan: "Mùa vụ sản phẩm", url: "/mua-vu", icon: "chart" },
      { ma: "banggia", nhan: "Bảng giá KOME", url: "/bang-gia", icon: "quote" },
      { ma: "doithu", nhan: "Thị trường & đối thủ", url: "/doi-thu", icon: "target" },
    ] },
    { ma: "sapco", ten: "SẮP CÓ", muc: [
      { ma: "hieusuat", nhan: "Hiệu suất đội sale", url: null, icon: "team", ly_do: CHUA },
      { ma: "baogia", nhan: "Báo giá", url: null, icon: "quote", ly_do: CHUA },
      { ma: "lendon", nhan: "Lên đơn hàng", url: null, icon: "cart", ly_do: CHUA },
      { ma: "giaohang", nhan: "Giao hàng & điều phối", url: null, icon: "truck", ly_do: CHUA },
      { ma: "trahang", nhan: "Trả hàng & khiếu nại", url: null, icon: "back", ly_do: CHUA },
      { ma: "dongtien", nhan: "Dòng tiền & phải trả", url: null, icon: "yen", ly_do: CHUA },
      { ma: "muahang", nhan: "Mua hàng & NCC", url: null, icon: "refill", ly_do: CHUA },
    ] },
    { ma: "hethong", ten: "HỆ THỐNG", muc: [
      ...(KD.hien_kho ? [{ ma: "khodl", nhan: "Nạp dữ liệu", url: "/kho-du-lieu", icon: "db" }] : []),
      // 2026-10-16 (chủ DN: "đơn giản cho người không rành"): Nhật ký / Cài đặt chỉ hiện cho người có cờ quản trị
      // (máy chưa bật đăng nhập: ai cũng thấy). Địa chỉ vẫn mở được — đây là bớt rối, không phải phân quyền.
      ...(laQuanTri() ? [{ ma: "nhatky", nhan: "Nhật ký thao tác", url: "/nhat-ky", icon: "cal" },
        { ma: "caidat", nhan: "Cài đặt", url: "/cai-dat", icon: "gear" }] : []),
    ] },
  ];
  // Màn chưa làm tạm ẩn (kome/man_chua_co.py, chủ DN 2026-09-28): bỏ mục không có `url`,
  // nhóm hết mục thì bỏ luôn. `hien_chua_co` thiếu (bản build cũ / test) = ẩn.
  if (KD.hien_chua_co) return nhom;
  return nhom.map(g => ({ ...g, muc: g.muc.filter(m => m.url) })).filter(g => g.muc.length);
}

/** Mục đang mở theo đường dẫn — dài nhất khớp trước ("/khach-hang/0001" -> kh360). */
export function mucDangMo(duong: string): string {
  // Màn nhập ngân sách không còn mục riêng — nó thuộc trang Doanh thu.
  if (duong === "/ngan-sach" || duong.startsWith("/ngan-sach/")) return "baocao";
  // Bản đồ là tab của màn Khách hàng (không còn mục riêng).
  if (duong === "/ban-do") return "kh360";
  let tot = "", dai = -1;
  for (const g of nhomDieuHuong()) for (const m of g.muc) {
    if (!m.url) continue;
    const khop = m.url === "/" ? duong === "/" : duong === m.url || duong.startsWith(m.url + "/");
    if (khop && m.url.length > dai) { tot = m.ma; dai = m.url.length; }
  }
  return tot;
}
