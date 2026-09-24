import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Nav } from "./khung/Nav";
import { KhoangXem } from "./khung/KhoangXem";
import { ganVietLaiLienKet } from "./khung/khoang";
import { TongQuan } from "./tong_quan/TongQuan";
import { KD } from "./khoi_dau";
import "./khung/khung.css";
import "./chung/chung.css";

// Dữ liệu chỉ đổi khi nạp (13:30) / hoàn tác / sửa ngân sách: giữ 5 phút rồi
// hỏi lại — máy chủ trả 304 rỗng nếu chưa đổi (ETag = phiên bản dữ liệu).
const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60_000, retry: 1, refetchOnWindowFocus: true } },
});

// Mỗi màn đã chuyển một mục. Màn chưa chuyển vẫn là trang Jinja — thanh điều
// hướng trỏ thẳng địa chỉ, nên đi qua lại là một lượt tải trang bình thường.
// Màn Khách hàng (giai đoạn 2) tải trễ: người chỉ mở Tổng quan không tải mã của nó.
const ManKhach = lazy(() => import("./khach/ManKhach"));
const HoSo = lazy(() => import("./khach/HoSo"));
// Giai đoạn 3.
const LienHe = lazy(() => import("./lien_he/LienHe"));
const BaoCao = lazy(() => import("./bao_cao/BaoCao"));
const DuBao = lazy(() => import("./du_bao/DuBao"));
// Giai đoạn 4.
const ManSanPham = lazy(() => import("./san_pham/ManSanPham"));
const KhoHang = lazy(() => import("./san_pham/KhoHang"));
// Đợt 6.
const ManCongNo = lazy(() => import("./cong_no/ManCongNo"));
// Giai đoạn 5 — nhóm HỆ THỐNG. Máy chủ tính sẵn dữ liệu vào window.__KOME__.man.
const KhoDuLieu = lazy(() => import("./he_thong/KhoDuLieu"));
const TaiLieuLuong = lazy(() => import("./he_thong/TaiLieu").then(m => ({ default: m.TaiLieuLuong })));
const TaiLieuCotNoi = lazy(() => import("./he_thong/TaiLieu").then(m => ({ default: m.TaiLieuCotNoi })));
const NhatKy = lazy(() => import("./he_thong/NhatKy"));
const CaiDat = lazy(() => import("./he_thong/CaiDat"));
const NganSach = lazy(() => import("./he_thong/NganSach"));
const DangNhap = lazy(() => import("./he_thong/DangNhap"));
const ThongBao = lazy(() => import("./he_thong/ThongBao"));

function man(duong: string): (() => React.ReactElement) | null {
  // Trang thông báo của máy chủ (lỗi / không có quyền / bản chỉ-đọc) thắng mọi địa chỉ.
  if (KD.thong_bao) return () => <ThongBao />;
  if (duong === "/") return () => <TongQuan />;
  if (duong === "/khach-hang" || duong === "/ban-do") return () => <ManKhach />;
  if (duong === "/lien-he") return () => <LienHe />;
  if (duong === "/bao-cao") return () => <BaoCao />;
  if (duong === "/du-bao") return () => <DuBao />;
  if (duong === "/san-pham" || /^\/san-pham\/[^/]+$/.test(duong)) return () => <ManSanPham />;
  if (duong === "/kho-hang") return () => <KhoHang />;
  if (duong === "/cong-no") return () => <ManCongNo />;
  if (KD.man != null) {
    if (duong === "/kho-du-lieu" || duong === "/upload") return () => <KhoDuLieu />;
    if (duong === "/kho-du-lieu/luong") return () => <TaiLieuLuong />;
    if (duong === "/kho-du-lieu/cot-noi") return () => <TaiLieuCotNoi />;
    if (duong === "/nhat-ky") return () => <NhatKy />;
    if (duong === "/cai-dat") return () => <CaiDat />;
    if (duong === "/ngan-sach") return () => <NganSach />;
  }
  const m = duong.match(/^\/khach-hang\/([^/]+)$/);
  if (m) return () => <HoSo ma={decodeURIComponent(m[1])} />;
  return null;
}

// Bộ chọn khoảng xem (đặc tả khoảng xem §3): màn doanh số -> bật; màn luôn
// tính theo hôm nay -> hiện MỜ kèm lý do; màn hệ thống -> không hiện. Tham số
// khoảng vẫn nằm trên URL ở mọi màn, nên quay lại màn doanh số không mất lựa chọn.
function boChon(duong: string): { hien: boolean; mo?: string } {
  if (KD.thong_bao || !KD.nguoi && KD.co_dang_nhap) return { hien: false };
  if (duong === "/" || duong === "/bao-cao") return { hien: true };
  // Từ migration 040 ("mọi thứ quay về tháng đó") cả bốn màn này cũng theo mốc của khoảng.
  if (["/cong-no", "/kho-hang", "/lien-he", "/du-bao"].includes(duong)) return { hien: true };
  if (duong === "/khach-hang" || duong === "/ban-do" || /^\/khach-hang\//.test(duong)) return { hien: true };
  if (/^\/san-pham(\/|$)/.test(duong)) return { hien: true };
  return { hien: false };
}

function Ung() {
  // Đăng nhập: CỐ Ý không có thanh điều hướng (chưa đăng nhập thì mọi liên kết quay về đây).
  if (location.pathname === "/dang-nhap" && !KD.thong_bao)
    return <Suspense fallback={null}><DangNhap /></Suspense>;
  const Man = man(location.pathname);
  const bc = boChon(location.pathname);
  return (
    <div className="khung">
      <Nav />
      <main className="khung-than">
        {bc.hien && <KhoangXem mo={bc.mo} />}
        <Suspense fallback={<div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>}>
          {Man ? <Man /> : <p>Không có màn này.</p>}
        </Suspense></main>
    </div>
  );
}

ganVietLaiLienKet();

createRoot(document.getElementById("goc")!).render(
  <StrictMode><QueryClientProvider client={qc}><Ung /></QueryClientProvider></StrictMode>,
);
