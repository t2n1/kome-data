// Cách vẽ chung cho KỲ SO của khoảng xem (đặc tả 2026-09-28-ky-so-sanh-toan-web-design.md §6):
// kỳ đang xem = nét liền, kỳ so = nét đứt. Nhãn kỳ so luôn là của MÁY CHỦ
// (`khoang.so_sanh[0].nhan`) — không viết cứng "năm trước" ở đâu cả.
import { thay_doi } from "../dinh_dang";

/** Mẫu nét nhỏ đặt trước chữ: `lien` = kỳ đang xem, mặc định = kỳ so (nét đứt). */
export function MauSs({ lien = false }: { lien?: boolean }) {
  return <i className={"ss-mau" + (lien ? " lien" : "")} aria-hidden="true" />;
}

const hoa = (s: string) => s.replace(/^./, c => c.toUpperCase());

/** Dòng so sánh của một ô số: "▲ 12.3% so ╌ Năm trước ¥1,410万". `ss` null khi
 *  kỳ so không có dữ liệu (`co` false) — in đúng câu đó, không in "—" trơn. */
export function DongSoSanh({ nhan, co, nay, ss, dinh_dang, className = "dong-phu" }: {
  nhan: string; co: boolean; nay: number | null | undefined; ss: number | null | undefined;
  dinh_dang?: (v: number) => string; className?: string;
}) {
  if (!co) return <div className={`${className} ss-dong nhat-chu`}><MauSs />{hoa(nhan)}: không có dữ liệu để so</div>;
  const td = nay != null && ss ? nay / ss - 1 : null;
  return (
    <div className={`${className} ss-dong ${td == null ? "nhat-chu" : td >= 0 ? "tang" : "giam"}`}>
      <b>{td != null ? thay_doi(td) : "—"}</b> so <MauSs />{nhan}
      {ss != null && dinh_dang && <span className="ss-gia"> {dinh_dang(ss)}</span>}
    </div>
  );
}

/** Vạch đứt dọc ở mức kỳ so trên một thanh ngang (`ty_le` 0–1 theo bề rộng thanh).
 *  Đặt trong phần tử cha `position: relative` (lớp `ss-thanh`). */
export function VachSoSanh({ ty_le, nhan }: { ty_le: number | null | undefined; nhan: string }) {
  if (ty_le == null || !isFinite(ty_le)) return null;
  return <span className="ss-vach" style={{ left: `${Math.max(0, Math.min(1, ty_le)) * 100}%` }} title={nhan} aria-hidden="true" />;
}
