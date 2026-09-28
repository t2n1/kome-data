// Hình dùng chung của các màn ít chữ (đặc tả 2026-09-28-tong-quan-it-chu-design.md §3.3–3.4):
// thanh ngang xếp hạng, thanh chồng nhiều khúc, số lớn, hàng số nhỏ. Mọi chi tiết vào ONoi.
import type { ReactNode } from "react";
import { DongNoi, ONoi } from "./ONoi";
import { VachSoSanh } from "./SoSanh";
import { chiaKhuc, thangChung, tyLeThanh } from "./thanh_logic";

export type DongThanh = { khoa: string; ten: ReactNode; gia_tri: number; ss?: number | null; chu: ReactNode;
  phu?: ReactNode; mau?: string; href?: string; chi_tiet: ReactNode; ten_jp?: boolean };

/** Thanh ngang xếp hạng. `ss` = KỲ SO (vạch đứt) — không dùng cho so sánh nào khác.
 *  `thang` mặc định = lớn nhất của thực tế và kỳ so. */
export function ThanhNgang({ dong, nhan_ss, thang }: { dong: DongThanh[]; nhan_ss?: string; thang?: number }) {
  const m = thang ?? thangChung(dong);
  return (
    <div className="tng-ds">
      {dong.map(x => (
        <ONoi key={x.khoa} href={x.href} className="tng-dong"
          noi_dung={<><strong className={x.ten_jp ? "ten-jp" : undefined}>{x.ten}</strong>{x.chi_tiet}</>}>
          <span className={"tng-ten" + (x.ten_jp ? " ten-jp" : "")}>{x.ten}</span>
          <span className="tng-thanh ss-thanh">
            <span className="tng-day" style={{ width: `${tyLeThanh(x.gia_tri, m) * 100}%`, background: x.mau ?? "var(--lien-ket)" }} />
            {x.ss != null && nhan_ss && <VachSoSanh ty_le={tyLeThanh(x.ss, m)} nhan={nhan_ss} />}
          </span>
          <b className="tng-so">{x.chu}</b>
          {x.phu != null && <span className="tng-phu">{x.phu}</span>}
        </ONoi>))}
    </div>
  );
}

export type Khuc = { khoa: string; nhan: string; dem: number; mau: string; href?: string; onBam?: () => void;
  chi_tiet?: ReactNode; chon?: boolean };

/** Một thanh chia khúc + chú giải chấm màu. Khúc ≤ 0 không vẽ nhưng vẫn có trong chú giải. */
export function ThanhChong({ khuc, dinh_dang, don_vi = "" }: { khuc: Khuc[]; dinh_dang: (v: number) => string; don_vi?: string }) {
  const pt = chiaKhuc(khuc.map(k => k.dem));
  const noi = (k: Khuc, i: number) => <>
    <strong>{k.nhan}</strong>
    <DongNoi mau={k.mau} nhan={don_vi || "Số"} gia={dinh_dang(k.dem)} />
    <DongNoi nhan="Tỷ lệ" gia={`${pt[i].toFixed(1).replace(".", ",")}%`} />
    {k.chi_tiet}
  </>;
  return (
    <div className="tc">
      <div className="tc-thanh">
        {khuc.map((k, i) => pt[i] > 0 && (
          <ONoi key={k.khoa} href={k.href} onBam={k.onBam} nhan={`${k.nhan}: ${dinh_dang(k.dem)}`}
            className={"tc-khuc" + (k.chon ? " chon" : "")} style={{ width: `${pt[i]}%`, background: k.mau }}
            noi_dung={noi(k, i)}><span /></ONoi>))}
      </div>
      <div className="tc-chu-giai">
        {khuc.map((k, i) => (
          <ONoi key={k.khoa} href={k.href} onBam={k.onBam} className={"tc-muc" + (k.chon ? " chon" : "")} noi_dung={noi(k, i)}>
            <i style={{ background: k.mau }} />{k.nhan}<b>{dinh_dang(k.dem)}</b>
          </ONoi>))}
      </div>
    </div>
  );
}

/** Số lớn của khối, chi tiết trong ô nổi. */
export function SoLon({ gia, nhan, chi_tiet, href, lop, mau }: {
  gia: ReactNode; nhan: ReactNode; chi_tiet?: ReactNode; href?: string; lop?: string; mau?: string }) {
  const than = <><b className={lop} style={mau ? { color: mau } : undefined}>{gia}</b><span>{nhan}</span></>;
  return chi_tiet == null && !href ? <div className="so-lon">{than}</div>
    : <ONoi href={href} className="so-lon" noi_dung={<><strong>{nhan}</strong>{chi_tiet}</>}>{than}</ONoi>;
}

/** Hàng số nhỏ thay cho lưới ô số: "Luỹ kế ¥188,2M · ▲1,4% so … · …". */
export function HangSo({ children }: { children: ReactNode }) {
  return <div className="hang-so">{children}</div>;
}

export function MucSo({ nhan, gia, lop, chi_tiet }: { nhan: ReactNode; gia: ReactNode; lop?: string; chi_tiet?: ReactNode }) {
  const than = <><span className="hs-nhan">{nhan}</span> <b className={lop}>{gia}</b></>;
  return chi_tiet == null ? <span className="hs-muc">{than}</span>
    : <ONoi className="hs-muc" noi_dung={<><strong>{nhan}</strong>{chi_tiet}</>}>{than}</ONoi>;
}
