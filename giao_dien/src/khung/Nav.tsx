// Thanh bên — chép kome-nav.js của gói thiết kế: logo, chuông, "Tìm nhanh ⌘K",
// sáu nhóm gập được, đăng xuất. Khác gói thiết kế: mục chưa có màn hiện mờ
// (không giả vờ có), mục Kho dữ liệu / Ngân sách ẩn theo cờ quyền, cuối thanh
// có bốn chế độ giao diện (cookie + render máy chủ, KHÔNG localStorage —
// bất biến CLAUDE.md), và chuông chỉ báo những gì CÓ nguồn thật.
import { useEffect, useState } from "react";
import { KD } from "../khoi_dau";
import { Icon } from "./icon";
import { nhomDieuHuong, mucDangMo } from "./muc";
import { TimNhanh } from "./TimNhanh";
import { Chuong } from "./Chuong";

const KHOA_THU = "kome_nav_thu_gon_v1"; // tiện nghi riêng từng máy — mất cũng không sao

function docThu(): Record<string, boolean> {
  try { return JSON.parse(localStorage.getItem(KHOA_THU) || "{}") || {}; } catch { return {}; }
}

const CHE_DO = [["sang", "Sáng"], ["toi", "Tối"], ["he-thong", "Hệ thống"], ["theo-gio", "Theo giờ"]] as const;

export function Nav() {
  const dangMo = mucDangMo(location.pathname);
  const [thu, datThu] = useState(docThu);
  const [tim, datTim] = useState(false);
  const [chuong, datChuong] = useState(false);
  const [menu, datMenu] = useState(false);   // chỉ có tác dụng ở màn hẹp (CSS)

  useEffect(() => {
    const phim = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) { e.preventDefault(); datTim(t => !t); }
      else if (e.key === "Escape") { datTim(false); datChuong(false); }
    };
    document.addEventListener("keydown", phim);
    return () => document.removeEventListener("keydown", phim);
  }, []);

  const gap = (ma: string) => {
    const moi = { ...thu, [ma]: !thu[ma] };
    datThu(moi);
    try { localStorage.setItem(KHOA_THU, JSON.stringify(moi)); } catch { /* chế độ riêng tư */ }
  };

  return (
    <nav className="knav" aria-label="Điều hướng chính">
      <div className="knav-dau">
        <a href="/" className="knav-logo"><img src="/static/kome-logo.png" alt="" /><span>KOME</span></a>
        <Chuong mo={chuong} datMo={datChuong} />
        <button type="button" className="knav-menu" aria-expanded={menu} aria-controls="knav-than"
          aria-label={menu ? "Đóng menu" : "Mở menu"} onClick={() => datMenu(m => !m)}>{menu ? "✕" : "☰"}</button>
      </div>
      <div id="knav-than" className={"knav-than" + (menu ? " mo" : "")}>
      <button type="button" className="knav-tim" onClick={() => datTim(true)}>
        <Icon ten="tim" co={14} /><span>Tìm nhanh</span><kbd>⌘K</kbd>
      </button>

      {nhomDieuHuong().map(g => {
        const coMo = g.muc.some(m => m.ma === dangMo);
        const dong = !!thu[g.ma] && !coMo;
        return (
          <div key={g.ma} className="knav-nhom">
            <button type="button" className="knav-nhom-ten" aria-expanded={!dong} onClick={() => gap(g.ma)}>
              <span className={"knav-mui" + (dong ? " dong" : "")} aria-hidden="true">▾</span>{g.ten}
            </button>
            {!dong && <div className="knav-ds">
              {g.muc.map(m => m.url
                ? <a key={m.ma} href={m.url} className={"knav-muc" + (m.ma === dangMo ? " on" : "")}
                    aria-current={m.ma === dangMo ? "page" : undefined}>
                    <Icon ten={m.icon} /><span>{m.nhan}</span></a>
                : <span key={m.ma} className="knav-muc chua" aria-disabled="true" title={m.ly_do}>
                    <Icon ten={m.icon} /><span>{m.nhan}</span><em>chưa có</em></span>)}
            </div>}
          </div>
        );
      })}

      <div className="knav-cuoi">
        {KD.nguoi && <div className="knav-toi" title={KD.nguoi.ten_sale ?? undefined}>
          <Icon ten="user" /><span>{KD.nguoi.ten_sale || KD.nguoi.ten_dang_nhap}</span></div>}
        <div className="knav-che-do" role="group" aria-label="Giao diện">
          {CHE_DO.map(([ma, nhan]) => (
            <a key={ma} href={`/giao-dien?che_do=${ma}`}
               className={KD.che_do_giao_dien === ma ? "on" : ""}
               aria-current={KD.che_do_giao_dien === ma ? "true" : undefined}>{nhan}</a>
          ))}
        </div>
        {KD.co_dang_nhap && <form method="post" action="/dang-xuat">
          <button type="submit" className="knav-muc knav-thoat"><Icon ten="out" /><span>Đăng xuất</span></button>
        </form>}
      </div>
      </div>
      {tim && <TimNhanh dong={() => datTim(false)} />}
    </nav>
  );
}
