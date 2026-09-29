// Hình sản phẩm — MỘT thành phần cho mọi màn (nguồn: config/hinh_san_pham.csv → window.__KOME__.hinh,
// đọc qua ./hinh_ma.ts::hinhCua). Mã không có hình HOẶC ảnh lỗi → ô giữ chỗ cùng cỡ (chữ cái đầu của
// tên) — không bao giờ để khung ảnh vỡ. Ảnh tải từ máy chủ ngoài (cos.ec-design.co.jp), không gửi Referer.
import { useState } from "react";
import { chuDau, hinhCua } from "./hinh_ma";

/** Ảnh HTML. `ten` là alt; `trang_tri` = tên đã in ngay cạnh → alt rỗng (trình đọc màn hình không đọc hai lần). */
export function HinhMa({ ma, ten, co, trang_tri, className }: {
  ma: string | null | undefined; ten?: string | null; co: number; trang_tri?: boolean; className?: string;
}) {
  const src = hinhCua(ma);
  const [loi, datLoi] = useState<string | null>(null);
  const cls = "hinh-ma" + (className ? " " + className : "");
  const st = { width: co, height: co, fontSize: Math.max(9, Math.round(co * 0.42)) };
  if (!src || loi === src) {
    return <span className={cls + " hinh-ma-cho"} style={st} aria-hidden="true">{chuDau(ten, ma)}</span>;
  }
  return <img className={cls} src={src} alt={trang_tri ? "" : (ten ?? "")} width={co} height={co} style={st}
    loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => datLoi(src)} />;
}

/** Ảnh trong SVG (treemap, bản đồ nhiệt) — luôn aria-hidden (tên đã có ở chữ / ô nổi). Không có
 *  hình hoặc lỗi: `cho` = true vẽ ô giữ chỗ, false thì không vẽ gì. */
export function HinhMaSvg({ ma, ten, x, y, co, cho = true }: {
  ma: string | null | undefined; ten?: string | null; x: number; y: number; co: number; cho?: boolean;
}) {
  const src = hinhCua(ma);
  const [loi, datLoi] = useState<string | null>(null);
  if (!src || loi === src) {
    if (!cho) return null;
    return (
      <g aria-hidden="true" className="hinh-ma-svg-cho" pointerEvents="none">
        <rect x={x} y={y} width={co} height={co} rx={Math.min(4, co / 5)} />
        <text x={x + co / 2} y={y + co / 2} dy="0.35em" textAnchor="middle" fontSize={Math.max(8, co * 0.5)}>
          {chuDau(ten, ma)}</text>
      </g>);
  }
  return (
    <g aria-hidden="true" pointerEvents="none">
      <rect x={x} y={y} width={co} height={co} rx={Math.min(4, co / 5)} className="hinh-ma-svg-nen" />
      <image href={src} x={x} y={y} width={co} height={co} preserveAspectRatio="xMidYMid meet"
        onError={() => datLoi(src)} />
    </g>);
}
