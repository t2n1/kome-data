// Khung màn Kho dữ liệu theo gói thiết kế (Kho dữ liệu.dc.html, đợt B 2026-09-24):
// thanh trái các mục · nội dung bên phải. Trên màn hẹp thanh trái thành một dải
// cuộn ngang ở trên. Mục đang xem mang aria-current (bất biến "màu + chữ", không
// chỉ đổi viền). Mục Nạp ẩn ở bản chỉ-đọc — bản đó không nạp được gì.
import type { ReactNode } from "react";
import { KD } from "../khoi_dau";

const TAB = [
  ["tong-quan", "/kho-du-lieu", "◆", "Tổng quan độ phủ"],
  ["nap", "/kho-du-lieu/nap", "＋", "Nạp dữ liệu mới"],
  ["luong", "/kho-du-lieu/luong", "⇄", "Sơ đồ luồng dữ liệu"],
  ["cot-noi", "/kho-du-lieu/cot-noi", "⋈", "Cột nối giữa các file"],
  ["duong-di", "/kho-du-lieu/duong-di", "↳", "Dữ liệu đi đâu"],
] as const;

export type MucKho = typeof TAB[number][0];

export function TabKho({ dang }: { dang: MucKho }) {
  return (
    <nav className="kdl-nav" aria-label="Các phần của màn Kho dữ liệu">
      <div className="kdl-nav-ten">Kho dữ liệu</div>
      {TAB.filter(([ma]) => ma !== "nap" || !KD.chi_doc).map(([ma, duong, ky, nhan]) => (
        <a key={ma} href={duong} className={dang === ma ? "dang-xem" : undefined} aria-current={dang === ma ? "page" : undefined}>
          <span className="kdl-nav-ky" aria-hidden="true">{ky}</span>{nhan}</a>))}
    </nav>
  );
}

/** Khung chung của mọi màn con: thanh trái + nội dung. */
export function KhungKho({ dang, children, lop }: { dang: MucKho; children: ReactNode; lop?: string }) {
  return (
    <div className={"ht kdl-khung" + (lop ? " " + lop : "")}>
      <TabKho dang={dang} />
      <div className="kdl-noi">{children}</div>
    </div>
  );
}
