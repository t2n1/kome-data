// Nội dung chung của một khối: tiêu đề + nhãn + liên kết "Mở →" + thân.
// Vỏ ngoài (kéo thả, đổi cỡ, nút ✕) do lưới Tổng quan lo (tong_quan/Luoi.tsx).
// Luật chữ (đặc tả 2026-09-28-tong-quan-it-chu-design.md §4): câu ĐỊNH NGHĨA cách tính vào
// `cach_tinh` (ⓘ cạnh tiêu đề), câu NGOẠI LỆ đang xảy ra vào `canh_bao` (luôn hiện).
// `phu` chỉ còn cho nhãn kỳ so / nhãn mốc ngắn.
import type { ReactNode } from "react";
import { ONoi } from "./ONoi";

/** Các cách xem của một khối (2026-09-29): danh mục của MÁY CHỦ (bo_cuc.CACH_XEM), cách đang
 *  chọn, và hàm đổi (lưu vào ô bố cục của bảng đang xem). */
export type CachXem = { ds: { id: string; nhan: string }[]; chon: string; dat: (ma: string) => void };

export function Khoi({ tieu_de, phu, nhan, mau_nhan = "do", lien_ket, children, dang_tai, loi, cach_tinh, canh_bao, cach_xem }: {
  tieu_de: string;
  phu?: ReactNode;
  nhan?: ReactNode;
  mau_nhan?: "do" | "canh" | "ok" | "lam" | "nhat";
  lien_ket?: { href: string; chu?: string };
  children?: ReactNode;
  dang_tai?: boolean;
  loi?: string | null;
  cach_tinh?: ReactNode;
  canh_bao?: ReactNode;
  cach_xem?: CachXem;
}) {
  return (
    <>
      <div className="khoi-dau" data-keo="1">
        <h2>{tieu_de}</h2>
        {cach_tinh != null && <ONoi noi_dung={<div className="o-noi-chu">{cach_tinh}</div>} nhan="Cách tính" className="khoi-i">ⓘ</ONoi>}
        {nhan != null && <span className={"nhan-vien " + mau_nhan}>{nhan}</span>}
        {phu != null && <span className="khoi-phu">{phu}</span>}
        {cach_xem && cach_xem.ds.length > 1 && (
          <span className="khoi-xem" role="group" aria-label={`Cách xem ${tieu_de}`}>
            {cach_xem.ds.map(x => <button key={x.id} type="button" aria-pressed={cach_xem.chon === x.id}
              onClick={() => cach_xem.chon !== x.id && cach_xem.dat(x.id)}>{x.nhan}</button>)}
          </span>)}
        {lien_ket && <a className="khoi-mo" href={lien_ket.href}>{lien_ket.chu ?? "Mở"} →</a>}
      </div>
      {loi ? <div className="khoi-loi">Không tải được khối này: {loi}</div>
        : dang_tai ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>
        : <>{children}{canh_bao != null && canh_bao !== false && <div className="khoi-canh" role="note">{canh_bao}</div>}</>}
    </>
  );
}

/** Khối của gói thiết kế chưa có nguồn dữ liệu thật: giữ khung, nói rõ thiếu gì.
 *  `gon` (Tổng quan): chỉ tiêu đề + nhãn "chưa có", lý do trong ⓘ. */
export function ChuaCoDuLieu({ tieu_de, ly_do, gon = false }: { tieu_de: string; ly_do: string; gon?: boolean }) {
  if (gon) return <Khoi tieu_de={tieu_de} nhan="chưa có dữ liệu" mau_nhan="nhat"
    cach_tinh={<>{ly_do}<br />Không hiện số mẫu: khối này sẽ tự có số khi nguồn được nạp.</>} />;
  return (
    <Khoi tieu_de={tieu_de} nhan="chưa có dữ liệu" mau_nhan="nhat">
      <div className="chua-co">
        <svg viewBox="0 0 18 18" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.4"
          aria-hidden="true" focusable="false"><ellipse cx="9" cy="4.6" rx="6" ry="2.2" /><path d="M3 4.6v8.8c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V4.6" /></svg>
        <p>{ly_do}</p>
        <p className="phu">Không hiện số mẫu: khối này sẽ tự có số khi nguồn được nạp.</p>
      </div>
    </Khoi>
  );
}

/** Đường nhỏ trong ô số. `so_sanh` = chuỗi KỲ SO cùng trục X (đặc tả 2026-09-28) — vẽ
 *  nét đứt, CÙNG thang với chuỗi chính để hai đường so được bằng mắt. */
export function Spark({ gia_tri, so_sanh, mau = "var(--ok-vien)", cao = 24 }:
  { gia_tri: number[]; so_sanh?: (number | null)[]; mau?: string; cao?: number }) {
  if (gia_tri.length < 2) return <div style={{ height: cao }} />;
  const ss = (so_sanh ?? []).filter((v): v is number => v != null);
  const tat = [...gia_tri, ...ss];
  const mn = Math.min(...tat), mx = Math.max(...tat), d = mx - mn || 1;
  const toa = (v: number, i: number) => `${(i / (gia_tri.length - 1) * 118 + 1).toFixed(1)},${(23 - (v - mn) / d * 20).toFixed(1)}`;
  const p = gia_tri.map(toa).join(" ");
  const q = ss.length > 1 ? (so_sanh ?? []).slice(0, gia_tri.length).map((v, i) => v == null ? null : toa(v, i)).filter(Boolean).join(" ") : "";
  return (
    <svg viewBox="0 0 120 26" preserveAspectRatio="none" style={{ width: "100%", height: cao, marginTop: ".35rem", display: "block" }}
      aria-hidden="true" focusable="false">
      {q && <polyline points={q} fill="none" stroke="var(--vien-dam)" strokeWidth={1.5} strokeDasharray="3 2.5" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />}
      <polyline points={p} fill="none" stroke={mau} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

/** Thanh ngang có vạch mốc (tiến độ ngân sách): nền = mục tiêu, đầy = thực tế. */
export function ThanhMoc({ ty_le, moc, mau }: { ty_le: number | null; moc?: number | null; mau: string }) {
  const r = Math.max(0, Math.min(1, ty_le ?? 0)) * 100;
  return (
    <div className="thanh-moc" role="img" aria-label={ty_le == null ? "chưa có" : `${Math.round((ty_le) * 100)}%`}>
      <div className="thanh-moc-day" style={{ width: `${r}%`, background: mau }} />
      {moc != null && <div className="thanh-moc-vach" style={{ left: `${Math.max(0, Math.min(1, moc)) * 100}%` }} />}
    </div>
  );
}

/** Màu tiến độ theo mốc — đạt (≥ mốc) / sát (≥ 85%) / hụt, luôn kèm chữ ở nơi dùng. */
export function mauTienDo(tien_do: number | null | undefined, moc: number | null | undefined): string {
  if (tien_do == null) return "var(--chu-mo)";
  const r = moc ? tien_do / moc : tien_do;
  return r >= 1 ? "var(--ok-vien)" : r >= 0.85 ? "var(--lien-ket)" : "var(--do)";
}
