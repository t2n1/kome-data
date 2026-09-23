// Nội dung chung của một khối: tiêu đề + nhãn + liên kết "Mở →" + thân.
// Vỏ ngoài (kéo thả, đổi cỡ, nút ✕) do lưới Tổng quan lo (tong_quan/Luoi.tsx).
import type { ReactNode } from "react";

export function Khoi({ tieu_de, phu, nhan, mau_nhan = "do", lien_ket, children, dang_tai, loi }: {
  tieu_de: string;
  phu?: ReactNode;
  nhan?: ReactNode;
  mau_nhan?: "do" | "canh" | "ok" | "lam" | "nhat";
  lien_ket?: { href: string; chu?: string };
  children?: ReactNode;
  dang_tai?: boolean;
  loi?: string | null;
}) {
  return (
    <>
      <div className="khoi-dau" data-keo="1">
        <h2>{tieu_de}</h2>
        {nhan != null && <span className={"nhan-vien " + mau_nhan}>{nhan}</span>}
        {phu != null && <span className="khoi-phu">{phu}</span>}
        {lien_ket && <a className="khoi-mo" href={lien_ket.href}>{lien_ket.chu ?? "Mở"} →</a>}
      </div>
      {loi ? <div className="khoi-loi">Không tải được khối này: {loi}</div>
        : dang_tai ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>
        : children}
    </>
  );
}

/** Khối của gói thiết kế chưa có nguồn dữ liệu thật: giữ khung, nói rõ thiếu gì. */
export function ChuaCoDuLieu({ tieu_de, ly_do }: { tieu_de: string; ly_do: string }) {
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

export function Spark({ gia_tri, mau = "var(--ok-vien)", cao = 24 }: { gia_tri: number[]; mau?: string; cao?: number }) {
  if (gia_tri.length < 2) return <div style={{ height: cao }} />;
  const mn = Math.min(...gia_tri), mx = Math.max(...gia_tri), d = mx - mn || 1;
  const p = gia_tri.map((v, i) => `${(i / (gia_tri.length - 1) * 118 + 1).toFixed(1)},${(23 - (v - mn) / d * 20).toFixed(1)}`).join(" ");
  return (
    <svg viewBox="0 0 120 26" preserveAspectRatio="none" style={{ width: "100%", height: cao, marginTop: ".35rem", display: "block" }}
      aria-hidden="true" focusable="false">
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
