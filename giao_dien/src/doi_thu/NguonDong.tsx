import type { ReactNode } from "react";
import type { QuanSat } from "./kieu";
import { CAN_BANG_CHUNG, lienKetAnToan, nhanThang, thangCua, timTrongDrive } from "./nguon";

export function Ra({ href, children }: { href: string; children: ReactNode }) {
  return <a className="chip" href={href} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">{children}</a>;
}

/** Các nút mở nguồn của MỘT quan sát (đặc tả §11.2). */
export function NguonDong({ q }: { q: QuanSat }) {
  const thuMuc = lienKetAnToan(q.lien_ket_thu_muc);
  const web = lienKetAnToan(q.web_ben);
  const bangChung = lienKetAnToan(q.lien_ket_bang_chung);
  const t = thangCua(q.thang_lo);
  return (
    <span className="dt-nguon">
      {q.nguon === "nap" && q.hinh_thuc_nguon === "file" && q.nguon_file && <>
        {thuMuc && <Ra href={thuMuc}>Mở thư mục {t ? nhanThang(t).toLowerCase() : "tháng"} ↗</Ra>}
        <Ra href={timTrongDrive(q.nguon_file)}>Tìm file trong Drive ↗</Ra>
      </>}
      {q.nguon === "nap" && q.hinh_thuc_nguon === "web" && web && <Ra href={web}>Mở trang của bên ↗</Ra>}
      {q.nguon === "tay" && (bangChung
        ? <Ra href={bangChung}>bằng chứng ↗</Ra>
        : (CAN_BANG_CHUNG as readonly string[]).includes(q.loai_nguon ?? "") && <span className="dt-nhat">chưa có bằng chứng</span>)}
    </span>
  );
}
