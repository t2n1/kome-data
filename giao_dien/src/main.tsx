import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Nav } from "./khung/Nav";
import { TongQuan } from "./tong_quan/TongQuan";
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

function man(duong: string): (() => React.ReactElement) | null {
  if (duong === "/") return () => <TongQuan />;
  if (duong === "/khach-hang" || duong === "/ban-do") return () => <ManKhach />;
  if (duong === "/lien-he") return () => <LienHe />;
  if (duong === "/bao-cao") return () => <BaoCao />;
  if (duong === "/du-bao") return () => <DuBao />;
  const m = duong.match(/^\/khach-hang\/([^/]+)$/);
  if (m) return () => <HoSo ma={decodeURIComponent(m[1])} />;
  return null;
}

function Ung() {
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
