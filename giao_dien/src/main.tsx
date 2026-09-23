import { StrictMode } from "react";
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
const MAN: Record<string, () => React.ReactElement> = {
  "/": () => <TongQuan />,
};

function Ung() {
  const Man = MAN[location.pathname];
  return (
    <div className="khung">
      <Nav />
      <main className="khung-than">{Man ? <Man /> : <p>Không có màn này.</p>}</main>
    </div>
  );
}

createRoot(document.getElementById("goc")!).render(
  <StrictMode><QueryClientProvider client={qc}><Ung /></QueryClientProvider></StrictMode>,
);
