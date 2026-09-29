// Dải "Đã bỏ khỏi nhóm: … hoàn tác" dưới biểu đồ (đặc tả §4.7, B15). Danh sách do máy chủ tính (so-sanh `da_bo`, /ben
// `bo_nhom`): mặt hàng hiện hành đang mang ghép 'khong'. "hoàn tác" = ghi lại nhãn cũ qua CÙNG đường lưu của pop-up
// (POST /sua-mat-hang, sua_logic.ts::thanHoanTac) — chống sửa đè như mọi lần sửa; xong làm mới mọi truy vấn "doi-thu".
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { gui } from "../api";
import type { DaBo } from "./kieu";
import { docXungDot, moTaXungDot, thanHoanTac } from "./sua_logic";

const HIEN_TOI_DA = 12;

export function DaBoNhom({ ds, ben = true }: { ds: DaBo[]; ben?: boolean }) {
  const qc = useQueryClient();
  const [dang, datDang] = useState<string | null>(null);
  const [loi, datLoi] = useState<string | null>(null);
  const [moRong, datMoRong] = useState(false);
  if (!ds.length) return null;
  const hien = moRong ? ds : ds.slice(0, HIEN_TOI_DA);
  const hoanTac = (x: DaBo) => {
    const k = `${x.nguon}${x.id}`;
    if (dang) return;
    datDang(k); datLoi(null);
    gui("/api/doi-thu/sua-mat-hang", thanHoanTac(x))
      .then(() => qc.invalidateQueries({ queryKey: ["doi-thu"] }))
      .catch((e: unknown) => {
        const xd = docXungDot(e);
        datLoi(xd ? `${moTaXungDot(xd)} — đã tải lại, thử lại nếu vẫn muốn hoàn tác.` : e instanceof Error ? e.message : String(e));
        if (xd) qc.invalidateQueries({ queryKey: ["doi-thu"] });
      })
      .finally(() => datDang(null));
  };
  return (
    <div className="dt-da-bo" role="group" aria-label="Mặt hàng đã bỏ khỏi nhóm">
      <span className="dt-nhat">Đã bỏ khỏi nhóm:</span>
      {hien.map(x => {
        const ten = `${ben ? `${x.ten_doi_thu ?? x.ma_doi_thu} · ` : ""}${x.ten_goc}`;
        return (
          <span key={`${x.nguon}${x.id}`} className="dt-da-bo-mh">
            {ten} <small className="dt-nhat">(khỏi {x.ten_nhom ?? x.nhom_khoa})</small>{" "}
            <button type="button" className="lien-ket" disabled={!!dang}
              aria-label={`Hoàn tác: đưa ${ten} trở lại nhóm ${x.ten_nhom ?? x.nhom_khoa}`}
              onClick={() => hoanTac(x)}>{dang === `${x.nguon}${x.id}` ? "đang hoàn tác…" : "hoàn tác"}</button>
          </span>);
      })}
      {ds.length > HIEN_TOI_DA && <button type="button" className="lien-ket" onClick={() => datMoRong(!moRong)}>
        {moRong ? "thu gọn" : `và ${ds.length - HIEN_TOI_DA} mặt hàng khác`}</button>}
      {loi && <p role="alert" className="dt-loi">{loi}</p>}
    </div>
  );
}
