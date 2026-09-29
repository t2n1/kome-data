// Màn "Thị trường & đối thủ" (/doi-thu). Thanh tab: Tóm tắt · So sánh giá · Đối thủ · Tin thị trường · Phí & giao hàng,
// cộng menu "Dữ liệu ▾" ở phải (Duyệt / sửa · Nhóm & quy cách · Giá KOME lệch · Thư mục Drive). Trạng thái ở URL (url.ts);
// ?nhom= (nhom_khoa mở sẵn của tab So sánh cũ) không thuộc url.ts nên được giữ / xoá riêng ở đây.
// Các tab chưa làm lại (đợt 4b task sau: Phí & giao hàng, Giá KOME lệch) tạm hiện một dòng "đang được làm lại".
import { useCallback, useEffect, useRef, useState } from "react";
import { giuKhoang } from "../khung/khoang";
import { TabTomTat } from "./TabTomTat";
import { TabSoSanh } from "./TabSoSanh";
import { TabHoSo } from "./TabHoSo";
import { TabTin } from "./TabTin";
import { TabDuyet } from "./TabDuyet";
import { TabNhomQuyCach } from "./TabNhomQuyCach";
import { docUrl, vietUrl, type Tab, type TrangThaiUrl } from "./url";
import "./doi_thu.css";

const TAB: { ma: Tab; nhan: string }[] = [
  { ma: "tom_tat", nhan: "Tóm tắt" }, { ma: "so_sanh", nhan: "So sánh giá" }, { ma: "ben", nhan: "Đối thủ" },
  { ma: "tin", nhan: "Tin thị trường" }, { ma: "giao_hang", nhan: "Phí & giao hàng" }];

type MucDuLieu = { ma: string; tab: Tab; nhan: string; phu: string; cuon?: boolean };
const MENU: MucDuLieu[] = [
  { ma: "duyet", tab: "duyet", nhan: "Duyệt / sửa bảng giá", phu: "Xác nhận giá AI đọc, sửa, thêm giá tay" },
  { ma: "nhom", tab: "nhom", nhan: "Nhóm & quy cách", phu: "Ghép mã hàng, gói / thùng / kg" },
  { ma: "lech", tab: "lech", nhan: "Giá KOME lệch", phu: "Mã KOME lệch xa trung vị thị trường" },
  { ma: "drive", tab: "duyet", nhan: "Thư mục Drive theo tháng", phu: "Link file gốc từng tháng", cuon: true }];
const TAB_MENU = new Set<Tab>(MENU.map(m => m.tab));

type Ext = TrangThaiUrl & { nhom: string };
const doc = (): Ext => ({ ...docUrl(location.search), nhom: new URLSearchParams(location.search).get("nhom") ?? "" });

/** Chờ khối thư mục Drive của tab Duyệt vẽ xong (nó tải dữ liệu) rồi cuộn tới; bỏ cuộc sau ~2 giây. */
function cuonToiThuMuc() {
  let n = 0;
  const thu = () => {
    const e = document.querySelector<HTMLElement>(".dt-thu-muc");
    if (e) e.scrollIntoView({ block: "center" }); else if (n++ < 20) setTimeout(thu, 100);
  };
  setTimeout(thu, 0);
}

export default function ManDoiThu() {
  const [t, dat] = useState<Ext>(doc);
  const hien = useRef(t);
  hien.current = t;
  const doi = useCallback((moi: Partial<Ext>) => {
    const gt = { ...hien.current, ...moi };
    if (gt.tab !== "so_sanh") gt.nhom = "";   // nhóm mở sẵn chỉ có nghĩa ở tab So sánh giá
    const q = new URLSearchParams(location.search);
    if (gt.nhom) q.set("nhom", gt.nhom); else q.delete("nhom");
    history.replaceState(null, "", giuKhoang(location.pathname + vietUrl(gt, q.toString())));
    hien.current = gt;
    dat(gt);
  }, []);

  const [mo, datMo] = useState(false);
  const dauMo = useRef<"dau" | "cuoi">("dau");   // mục nào nhận focus khi menu mở
  const nut = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const dongMenu = useCallback((tra = false) => { datMo(false); if (tra) nut.current?.focus(); }, []);
  useEffect(() => {
    if (!mo) return;
    const ngoai = (e: MouseEvent) => {
      const n = e.target as Node;
      if (!menu.current?.contains(n) && !nut.current?.contains(n)) datMo(false);
    };
    document.addEventListener("mousedown", ngoai);
    return () => document.removeEventListener("mousedown", ngoai);
  }, [mo]);
  const muc = () => Array.from(menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
  const phimMenu = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") { e.stopPropagation(); dongMenu(true); return; }
    if (e.key === "Tab") { datMo(false); return; }
    const d = muc(), i = d.indexOf(document.activeElement as HTMLElement);
    if (e.key === "ArrowDown") { e.preventDefault(); d[(i + 1) % d.length]?.focus(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); d[(i - 1 + d.length) % d.length]?.focus(); }
    else if (e.key === "Home") { e.preventDefault(); d[0]?.focus(); }
    else if (e.key === "End") { e.preventDefault(); d[d.length - 1]?.focus(); }
  };
  useEffect(() => { if (mo) { const d = muc(); (dauMo.current === "cuoi" ? d[d.length - 1] : d[0])?.focus(); } }, [mo]);

  const chon = (m: MucDuLieu) => { dongMenu(true); doi({ tab: m.tab }); if (m.cuon) cuonToiThuMuc(); };
  const trongMenu = TAB_MENU.has(t.tab);

  return (
    <div className="man-doi-thu">
      <div className="dt-thanh">
        <div role="tablist" className="kh-tab" aria-label="Thị trường và đối thủ">
          {TAB.map(x => <button key={x.ma} role="tab" type="button" aria-selected={t.tab === x.ma}
            // Thanh tab vào So sánh KHÔNG mang bộ lọc bên theo (bên còn lại từ tab Đối thủ sẽ lặng lẽ lọc cột trái);
            // chỉ bóng "Ai bán ngành nào" của Tóm tắt / liên kết tường minh đưa ?ben= vào So sánh.
            onClick={() => doi(x.ma === "so_sanh" ? { tab: x.ma, ben: "" } : { tab: x.ma })}>{x.nhan}</button>)}
        </div>
        <div className="dt-menu-goc">
          <button ref={nut} type="button" className="dt-menu-nut" aria-haspopup="menu" aria-expanded={mo}
            aria-current={trongMenu ? "true" : undefined} onClick={() => { dauMo.current = "dau"; datMo(m => !m); }}
            onKeyDown={e => {
              if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                e.preventDefault(); dauMo.current = e.key === "ArrowUp" ? "cuoi" : "dau";
                if (mo) { const d = muc(); (dauMo.current === "cuoi" ? d[d.length - 1] : d[0])?.focus(); } else datMo(true);
              }
            }}>Dữ liệu ▾</button>
          {mo && (
            <div ref={menu} role="menu" aria-label="Dữ liệu" className="dt-menu" onKeyDown={phimMenu}>
              {MENU.map(m => (
                <button key={m.ma} type="button" role="menuitem" tabIndex={-1} onClick={() => chon(m)}>
                  {m.nhan}<small>{m.phu}</small>
                </button>))}
            </div>)}
        </div>
      </div>
      {t.tab === "tom_tat" && <TabTomTat moBen={b => doi({ tab: "ben", ben: b })} moLech={() => doi({ tab: "lech" })} moTin={() => doi({ tab: "tin" })}
        moSoSanh={o => doi({ tab: "so_sanh", sp: o.sp ?? [], nganh: o.nganh ?? "", ben: o.ben ?? "", nhom: "" })} />}
      {t.tab === "so_sanh" && <TabSoSanh sp={t.sp} sl={t.sl} xem={t.xem} gk={t.gk} cung={t.cung} nganh={t.nganh} ben={t.ben}
        nhom={t.nhom} dat={doi} />}
      {t.tab === "ben" && <TabHoSo ben={t.ben} chonBen={b => doi({ ben: b })} moDuyet={b => doi({ tab: "duyet", ben: b })}
        moLech={() => doi({ tab: "lech" })} />}
      {t.tab === "tin" && <TabTin moBen={b => doi({ tab: "ben", ben: b })}
        moSoSanh={sp => doi({ tab: "so_sanh", sp, nganh: "", ben: "", nhom: "" })} />}
      {t.tab === "nhom" && <TabNhomQuyCach />}
      {t.tab === "duyet" && <TabDuyet ben={t.ben} boBen={() => doi({ ben: "" })} />}
      {(t.tab === "giao_hang" || t.tab === "lech") && <p className="dt-nhat" role="status">Màn này đang được làm lại.</p>}
    </div>
  );
}
