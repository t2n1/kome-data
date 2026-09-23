// Chuông thông báo — bảng trượt của kome-nav.js. CHỈ những gì có nguồn thật
// (/api/thong-bao): hôm nay chưa nạp, khách cần gọi, lô quá hạn / cận hạn,
// mã hết hàng. "Đã đọc" nhớ ở máy này (tiện nghi riêng, mất cũng không sao).
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { lay } from "../api";
import { Icon } from "./icon";

type TB = { ma: string; muc: "gap" | "canh" | "thuong" | "ok"; loai: string; tieu_de: string; noi_dung: string; lien_ket: string };
const KHOA = "kome_tb_da_doc_v1";
const KY_HIEU = { gap: "!", canh: "▲", thuong: "•", ok: "✓" } as const;

function docDaDoc(): Record<string, boolean> {
  try { return JSON.parse(localStorage.getItem(KHOA) || "{}") || {}; } catch { return {}; }
}

export function Chuong({ mo, datMo }: { mo: boolean; datMo: (m: boolean) => void }) {
  const { data } = useQuery({ queryKey: ["thong-bao"], queryFn: () => lay<{ tb: TB[] }>("/api/thong-bao"), staleTime: 5 * 60_000 });
  const [daDoc, datDaDoc] = useState(docDaDoc);
  const tb = data?.tb ?? [];
  const chua = tb.filter(x => !daDoc[x.ma]);
  const ghi = (o: Record<string, boolean>) => { datDaDoc(o); try { localStorage.setItem(KHOA, JSON.stringify(o)); } catch { /* */ } };

  return (
    <>
      <button type="button" className="knav-chuong" aria-label={`Thông báo${chua.length ? `, ${chua.length} chưa đọc` : ""}`}
        onClick={() => datMo(!mo)}>
        <Icon ten="bell" />
        {chua.length > 0 && <span className="knav-dem" aria-hidden="true">{chua.length}</span>}
      </button>
      {mo && <>
        <div className="lop-phu mo" onClick={() => datMo(false)} />
        <aside className="tb-bang" role="dialog" aria-label="Thông báo">
          <div className="tb-dau">
            <div><strong>Thông báo</strong>
              <div className="phu">{chua.length ? `${chua.length} chưa đọc · ${chua.filter(x => x.muc === "gap").length} việc khẩn` : "đã xem hết"}</div></div>
            <button type="button" className="nut-nho" onClick={() => ghi(Object.fromEntries(tb.map(x => [x.ma, true])))}>Đánh dấu đã đọc</button>
            <button type="button" className="nut-dong" aria-label="Đóng" onClick={() => datMo(false)}>✕</button>
          </div>
          <ul className="tb-ds">
            {tb.map(x => (
              <li key={x.ma} className={"tb-muc " + x.muc + (daDoc[x.ma] ? " da-doc" : "")}>
                <a href={x.lien_ket} onClick={() => ghi({ ...daDoc, [x.ma]: true })}>
                  <span className="tb-ky" aria-hidden="true">{KY_HIEU[x.muc]}</span>
                  <span className="tb-than"><span className="tb-loai">{x.loai}</span>
                    <strong>{x.tieu_de}</strong><span className="phu">{x.noi_dung}</span></span>
                </a>
              </li>
            ))}
            {!tb.length && <li className="trong">Không có thông báo nào.</li>}
          </ul>
          <p className="tb-chu-thich">Chưa có thông báo công nợ, giao hàng, khiếu nại, đơn hàng — chưa có nguồn dữ liệu.</p>
        </aside>
      </>}
    </>
  );
}
