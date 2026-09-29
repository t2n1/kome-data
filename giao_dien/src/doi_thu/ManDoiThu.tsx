// Màn "Thị trường & đối thủ" (/doi-thu, đặc tả 2026-09-29-thi-truong-doi-thu-design.md §5). Bốn tab (?tab=):
// tong_quan (mặc định) · so_sanh · ben (hồ sơ một đối thủ, ?ben=) · duyet · nhom (nhóm & quy cách). Theo khoảng xem.
// Trên URL: ?tab= ?ben= và, riêng tab so_sanh, ?nganh= ?nhom= (nhom_khoa của nhóm mở sẵn).
import { useState } from "react";
import { giuKhoang } from "../khung/khoang";
import { TabTongQuan } from "./TabTongQuan";
import { TabSoSanh } from "./TabSoSanh";
import { TabHoSo } from "./TabHoSo";
import { TabDuyet } from "./TabDuyet";
import { TabNhomQuyCach } from "./TabNhomQuyCach";
import "./doi_thu.css";

type Tab = "tong_quan" | "so_sanh" | "ben" | "duyet" | "nhom";
const TAB: { ma: Tab; nhan: string }[] = [
  { ma: "tong_quan", nhan: "Tổng quan thị trường" }, { ma: "so_sanh", nhan: "So sánh giá" },
  { ma: "ben", nhan: "Hồ sơ đối thủ" }, { ma: "duyet", nhan: "Duyệt / sửa" }, { ma: "nhom", nhan: "Nhóm & quy cách" }];

const docUrl = () => {
  const q = new URLSearchParams(location.search);
  const tab = (TAB.find(t => t.ma === q.get("tab"))?.ma ?? "tong_quan") as Tab;
  return { tab, ben: q.get("ben") ?? "", nganh: q.get("nganh") ?? "", nhom: q.get("nhom") ?? "" };
};

export default function ManDoiThu() {
  const [{ tab, ben, nganh, nhom }, dat] = useState(docUrl);
  const doi = (moi: { tab?: Tab; ben?: string; nganh?: string; nhom?: string }) => {
    const gt = { tab, ben, nganh, nhom, ...moi };
    if (gt.tab !== "so_sanh") { gt.nganh = ""; gt.nhom = ""; }  // ngành / nhóm chỉ có nghĩa ở tab So sánh giá
    dat(gt);
    const p = new URLSearchParams(location.search);
    if (gt.tab === "tong_quan") p.delete("tab"); else p.set("tab", gt.tab);
    if (gt.ben) p.set("ben", gt.ben); else p.delete("ben");
    if (gt.nganh) p.set("nganh", gt.nganh); else p.delete("nganh");
    if (gt.nhom) p.set("nhom", gt.nhom); else p.delete("nhom");
    history.replaceState(null, "", giuKhoang(`${location.pathname}?${p}`));
  };
  return (
    <div className="man-doi-thu">
      <div role="tablist" className="kh-tab" aria-label="Thị trường và đối thủ">
        {TAB.map(t => <button key={t.ma} role="tab" type="button" aria-selected={tab === t.ma}
          onClick={() => doi({ tab: t.ma })}>{t.nhan}</button>)}
      </div>
      {tab === "tong_quan" && <TabTongQuan moBen={b => doi({ tab: "ben", ben: b })}
        moSoSanh={(n, b) => doi({ tab: "so_sanh", nganh: n, ben: b, nhom: "" })}
        moNhom={k => doi({ tab: "so_sanh", nganh: "", ben: "", nhom: k })} />}
      {tab === "so_sanh" && <TabSoSanh nganh={nganh} ben={ben} nhom={nhom}
        datNganh={n => doi({ nganh: n })} datBen={b => doi({ ben: b })} datNhom={k => doi({ nhom: k })} />}
      {tab === "ben" && <TabHoSo ben={ben} chonBen={b => doi({ ben: b })} />}
      {tab === "nhom" && <TabNhomQuyCach />}
      {tab === "duyet" && <TabDuyet ben={ben} boBen={() => doi({ ben: "" })} />}
    </div>
  );
}
