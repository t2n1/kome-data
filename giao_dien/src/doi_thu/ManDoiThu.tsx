// Màn "Thị trường & đối thủ" (/doi-thu, đặc tả 2026-09-29-thi-truong-doi-thu-design.md §5). Bốn tab (?tab=):
// tong_quan (mặc định) · so_sanh · ben (hồ sơ một đối thủ, ?ben=) · duyet. Theo khoảng xem (mốc = cuối khoảng).
import { useState } from "react";
import { giuKhoang } from "../khung/khoang";
import { TabTongQuan } from "./TabTongQuan";
import { TabSoSanh } from "./TabSoSanh";
import { TabHoSo } from "./TabHoSo";
import { TabDuyet } from "./TabDuyet";
import "./doi_thu.css";

type Tab = "tong_quan" | "so_sanh" | "ben" | "duyet";
const TAB: { ma: Tab; nhan: string }[] = [
  { ma: "tong_quan", nhan: "Tổng quan thị trường" }, { ma: "so_sanh", nhan: "So sánh giá" },
  { ma: "ben", nhan: "Hồ sơ đối thủ" }, { ma: "duyet", nhan: "Duyệt / sửa" }];

const docUrl = () => {
  const q = new URLSearchParams(location.search);
  const tab = (TAB.find(t => t.ma === q.get("tab"))?.ma ?? "tong_quan") as Tab;
  return { tab, ben: q.get("ben") ?? "" };
};

export default function ManDoiThu() {
  const [{ tab, ben }, dat] = useState(docUrl);
  const doi = (moi: { tab?: Tab; ben?: string }) => {
    const gt = { tab, ben, ...moi };
    dat(gt);
    const p = new URLSearchParams(location.search);
    if (gt.tab === "tong_quan") p.delete("tab"); else p.set("tab", gt.tab);
    if (gt.ben) p.set("ben", gt.ben); else p.delete("ben");
    history.replaceState(null, "", giuKhoang(`${location.pathname}?${p}`));
  };
  return (
    <div className="man-doi-thu">
      <div role="tablist" className="kh-tab" aria-label="Thị trường và đối thủ">
        {TAB.map(t => <button key={t.ma} role="tab" type="button" aria-selected={tab === t.ma}
          onClick={() => doi({ tab: t.ma })}>{t.nhan}</button>)}
      </div>
      {tab === "tong_quan" && <TabTongQuan moBen={b => doi({ tab: "ben", ben: b })} />}
      {tab === "so_sanh" && <TabSoSanh />}
      {tab === "ben" && <TabHoSo ben={ben} chonBen={b => doi({ ben: b })} />}
      {tab === "duyet" && <TabDuyet ben={ben} />}
    </div>
  );
}
