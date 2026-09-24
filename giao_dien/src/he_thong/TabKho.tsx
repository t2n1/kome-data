// Khung màn Kho dữ liệu theo gói thiết kế (Kho dữ liệu.dc.html, đợt B 2026-09-24):
// thanh trái các mục · nội dung bên phải. Trên màn hẹp thanh trái thành một dải
// cuộn ngang ở trên. Mục đang xem mang aria-current (bất biến "màu + chữ", không
// chỉ đổi viền). Mục Nạp ẩn ở bản chỉ-đọc — bản đó không nạp được gì.
//
// Đợt C: dưới các mục là "Duyệt bảng" — mọi bảng/view của core · mart · meta mà
// vai trò đọc được SELECT (/api/kho-du-lieu/bang, 1 lượt hỏi, tải SAU khi màn đã
// vẽ — các màn tài liệu vẫn 0 truy vấn ở máy chủ).
import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { KD } from "../khoi_dau";
import { lay } from "../api";
import { so } from "../dinh_dang";

const TAB = [
  ["tong-quan", "/kho-du-lieu", "◆", "Tổng quan độ phủ"],
  ["nap", "/kho-du-lieu/nap", "＋", "Nạp dữ liệu mới"],
  ["luong", "/kho-du-lieu/luong", "⇄", "Sơ đồ luồng dữ liệu"],
  ["cot-noi", "/kho-du-lieu/cot-noi", "⋈", "Cột nối giữa các file"],
  ["duong-di", "/kho-du-lieu/duong-di", "↳", "Dữ liệu đi đâu"],
] as const;

export type MucKho = typeof TAB[number][0] | "bang";
export type BangDs = { schema: string; ten: string; ngan: string; loai: "bang" | "view"; so_dong: number | null; mo_ta: string | null };

const MO_TA_SCHEMA: Record<string, string> = { core: "đã làm sạch", mart: "chỉ số (view)", meta: "nhật ký nạp" };

export function TabKho({ dang, bang }: { dang: MucKho; bang?: string }) {
  return (
    <nav className="kdl-nav" aria-label="Các phần của màn Kho dữ liệu">
      <div className="kdl-nav-ten">Kho dữ liệu</div>
      {TAB.filter(([ma]) => ma !== "nap" || !KD.chi_doc).map(([ma, duong, ky, nhan]) => (
        <a key={ma} href={duong} className={dang === ma ? "dang-xem" : undefined} aria-current={dang === ma ? "page" : undefined}>
          <span className="kdl-nav-ky" aria-hidden="true">{ky}</span>{nhan}</a>))}
      <DuyetBang dang={bang} />
    </nav>
  );
}

function DuyetBang({ dang }: { dang?: string }) {
  const { data, isError } = useQuery({ queryKey: ["kdl-bang"], queryFn: () => lay<BangDs[]>("/api/kho-du-lieu/bang"), staleTime: 60_000 });
  const [loc, datLoc] = useState("");
  // Màn hẹp: mặc định ĐÓNG (danh sách ~60 bảng đẩy nội dung xuống quá xa); màn rộng: mở.
  const [mo] = useState(() => typeof matchMedia === "undefined" || !matchMedia("(max-width: 860px)").matches);
  const q = loc.trim().toLowerCase();
  const ds = (data ?? []).filter(b => !q || b.ten.includes(q) || (b.mo_ta ?? "").toLowerCase().includes(q));
  return (
    <details className="kdl-duyet" open={mo}>
      <summary className="kdl-nav-ten">Duyệt bảng</summary>
      <input type="search" className="kdl-duyet-tim" placeholder="Tìm bảng…" value={loc} onChange={e => datLoc(e.target.value)} aria-label="Tìm bảng" />
      {isError ? <p className="khong-ap-dung">Không đọc được danh sách bảng.</p>
        : !data ? <p className="khong-ap-dung">Đang tải…</p>
        : (["core", "mart", "meta"] as const).map(s => {
          const nhom = ds.filter(b => b.schema === s);
          if (!nhom.length) return null;
          return (
            <div key={s} className="kdl-duyet-nhom">
              <div className="kdl-duyet-dau"><b>{s}</b> <span>{MO_TA_SCHEMA[s]}</span></div>
              {nhom.map(b => (
                <a key={b.ten} href={`/kho-du-lieu/bang/${b.ten}`} className={dang === b.ten ? "dang-xem" : undefined}
                  aria-current={dang === b.ten ? "page" : undefined} title={b.mo_ta ?? b.ten}>
                  <span className="kdl-duyet-ten">{b.ngan}</span>
                  <span className="kdl-duyet-so">{b.so_dong != null ? so(b.so_dong) : "view"}</span></a>))}
            </div>);
        })}
    </details>
  );
}

/** Khung chung của mọi màn con: thanh trái + nội dung. */
export function KhungKho({ dang, children, lop, bang }: { dang: MucKho; children: ReactNode; lop?: string; bang?: string }) {
  return (
    <div className={"ht kdl-khung" + (lop ? " " + lop : "")}>
      <TabKho dang={dang} bang={bang} />
      <div className="kdl-noi">{children}</div>
    </div>
  );
}
