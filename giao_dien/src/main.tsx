import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Nav } from "./khung/Nav";
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

function Ung() {
  // Đăng nhập: CỐ Ý không có thanh điều hướng (chưa đăng nhập thì mọi liên kết quay về đây).
  if (location.pathname === "/dang-nhap" && !KD.thong_bao)
    return <Suspense fallback={null}><DangNhap /></Suspense>;
  const Man = man(location.pathname);
  return (
    <div className="khung">
      <Nav />
      <main className="khung-than">
        <Suspense fallback={<div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>}>
          {Man ? <Man /> : <p>Không có màn này.</p>}
        </Suspense></main>
    </div>
  );
}

createRoot(document.getElementById("goc")!).render(
  <StrictMode><QueryClientProvider client={qc}><Ung /></QueryClientProvider></StrictMode>,
);
