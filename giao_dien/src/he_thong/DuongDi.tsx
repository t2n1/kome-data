// Kho dữ liệu → "Dữ liệu đi đâu" (2026-09-24): mỗi cột OBC một phán quyết "bỏ
// khỏi bản xuất lần sau có sao không". Máy chủ chèn sẵn ảnh chụp của MỘT file
// (kome/cot_dung.py — sinh bởi scripts/sinh_cot_dung.py từ danh mục Postgres +
// files.yml + mã kome/). 0 truy vấn. Không có phán quyết nào tính ở đây: màn chỉ
// lọc, vẽ và cho tải danh sách.
import { useMemo, useState } from "react";
import { KD } from "../khoi_dau";
import { TabKho } from "./TabKho";
import "./he_thong.css";

type Loai = "nap" | "man" | "luu" | "khong_nap";
type Cot = { ja: string; he: string | null; core: string | null; loai: Loai; ly_do: string; view: string[]; man: string[]; ma: string[] };
type TomFile = { ten: string; ja: string; core_table: string; mau: string | null; dem: Record<Loai, number> };
type Man = {
  chon: string | null; files: TomFile[];
  file: { ten: string; ja: string; core_table: string; mau: string | null; cot: Cot[] } | null;
  man_hinh: Record<string, { ten: string; duong: string }>;
  view_man: Record<string, string[]>;
  khoa: { bang: { ten: string; cot: string[]; khoa: string[] }[]; noi: { tu: string; den: string; nguon: string }[] };
};

const LOAI: { ma: Loai; nhan: string; mau: string; bo: string; mo_ta: string }[] = [
  { ma: "nap", nhan: "Bộ nạp cần", mau: "loi", bo: "Không bỏ được",
    mo_ta: "Khoá của file, cột tổng tiền cổng kiểm đem đối chiếu, cột kiểm số lượng × đơn giá, ngày bắt buộc. Thiếu là cả file bị chặn." },
  { ma: "man", nhan: "Màn hình đang dùng", mau: "canh", bo: "Không nên bỏ",
    mo_ta: "Có màn hiện nó (trực tiếp hay qua một chỉ số). Bỏ là màn đó mất số." },
  { ma: "luu", nhan: "Nạp vào kho, chưa màn nào dùng", mau: "ok", bo: "Bỏ được — sau khi sửa khai báo nạp",
    mo_ta: "Chỉ đang lưu. Báo trước để sửa config/files.yml, không thì cổng 2 chặn cả file. Mất lịch sử cột từ ngày bỏ." },
  { ma: "khong_nap", nhan: "Có trong file, kho không nạp", mau: "nhat", bo: "Bỏ được ngay",
    mo_ta: "Bộ nạp đang bỏ qua cột này — bỏ khỏi mẫu xuất không cần sửa gì." },
];
const LOAI_CUA = Object.fromEntries(LOAI.map(l => [l.ma, l])) as Record<Loai, typeof LOAI[number]>;
const BO_DUOC: Loai[] = ["luu", "khong_nap"];

function taiCsv(ten: string, dong: string[][]) {
  const o = (s: string) => /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  // BOM: Excel mở thẳng file UTF-8 mà không vỡ chữ Nhật / Việt.
  const blob = new Blob(["﻿" + dong.map(d => d.map(o).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = ten;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

export default function DuongDi() {
  const m = KD.man as Man;
  const f = m.file;
  const [loc, datLoc] = useState<"tat_ca" | "bo_duoc" | Loai>("tat_ca");
  const [tim, datTim] = useState("");
  const [chon, datChon] = useState<string | null>(null);
  const tenMan = (k: string) => m.man_hinh[k]?.ten ?? k;

  const dong = useMemo(() => {
    if (!f) return [];
    const q = tim.trim().toLowerCase();
    return f.cot.filter(c =>
      (loc === "tat_ca" || (loc === "bo_duoc" ? BO_DUOC.includes(c.loai) : c.loai === loc))
      && (!q || [c.ja, c.he ?? "", c.core ?? "", ...c.view, ...c.man.map(tenMan)].some(x => x.toLowerCase().includes(q))));
  }, [f, loc, tim]);

  if (!f) return (
    <div className="ht"><h1>Kho dữ liệu</h1><TabKho dang="duong-di" />
      <p className="trong">Chưa sinh ảnh chụp — chạy <code>python scripts/sinh_cot_dung.py</code>.</p></div>);

  const dem = m.files.find(x => x.ten === f.ten)!.dem;
  const boDuoc = f.cot.filter(c => BO_DUOC.includes(c.loai));

  return (
    <div className="ht">
      <h1>Kho dữ liệu</h1>
      <TabKho dang="duong-di" />
      <div className="tai-lieu dd">
        <p className="ghi-chu">Mỗi cột trong file xuất từ OBC đi đâu trong web app — và <strong>bỏ khỏi bản xuất lần sau có sao không</strong>.
          Phân loại SINH từ danh mục CSDL, khai báo nạp và mã của web app; không có dòng nào chép tay.</p>
        <div className="ngay-thieu">⚠️ Cột <strong>đang khai báo nạp</strong> mà biến mất khỏi file thì <strong>cổng 2 chặn cả file</strong> hôm đó.
          Muốn bỏ một cột loại "Nạp vào kho, chưa màn nào dùng" thì báo trước để sửa <code>config/files.yml</code> rồi mới đổi mẫu xuất 汎用データ作成.</div>

        <div className="dd-loai">{LOAI.map(l => (
          <div key={l.ma} className="dd-loai-o">
            <div><span className={"vien " + l.mau}>{l.nhan}</span></div>
            <div className="dd-bo"><strong>{l.bo}</strong></div>
            <div className="khong-ap-dung">{l.mo_ta}</div>
          </div>))}</div>

        <section id="file">
          <nav className="loc" aria-label="Chọn file OBC">{m.files.map(x => {
            const n = x.dem.luu + x.dem.khong_nap;
            return <a key={x.ten} href={`/kho-du-lieu/duong-di?file=${x.ten}`} className={x.ten === f.ten ? "dang-xem" : undefined}
              aria-current={x.ten === f.ten ? "true" : undefined}>{x.ja}{n > 0 && <span className="dd-dem"> · {n} bỏ được</span>}</a>;
          })}</nav>

          <div className="tieu-de-khoi"><h2>Cột của {f.ja}</h2>
            <span className="khong-ap-dung">vào <code>{f.core_table}</code>
              {f.mau ? <> · tiêu đề đọc từ file mẫu <code>{f.mau}</code></> : <> · <strong>chưa có file mẫu</strong> nên không biết file thật còn cột nào kho không nạp</>}</span></div>
          <div className="dd-tong">{LOAI.map(l => (
            <button key={l.ma} type="button" className={"dd-so " + l.mau} aria-pressed={loc === l.ma} onClick={() => datLoc(loc === l.ma ? "tat_ca" : l.ma)}>
              <span className="dd-so-gia">{dem[l.ma]}</span><span>{l.nhan}</span></button>))}</div>

          <div className="dd-thanh">
            <div className="tab-pill" role="group" aria-label="Lọc cột">
              <button type="button" aria-pressed={loc === "tat_ca"} onClick={() => datLoc("tat_ca")}>Tất cả ({f.cot.length})</button>
              <button type="button" aria-pressed={loc === "bo_duoc"} onClick={() => datLoc("bo_duoc")}>Chỉ cột bỏ được ({boDuoc.length})</button>
            </div>
            <input type="search" className="dd-tim" placeholder="Tìm cột, bảng, màn hình…" value={tim} onChange={e => datTim(e.target.value)} aria-label="Tìm cột" />
            <button type="button" className="nut-nho" disabled={!boDuoc.length}
              onClick={() => taiCsv(`cot-bo-duoc-${f.ten}.csv`, [["File OBC", "Cột OBC", "Loại", "Cần làm", "Lý do"],
                ...boDuoc.map(c => [f.ja, c.ja, LOAI_CUA[c.loai].nhan, LOAI_CUA[c.loai].bo, c.ly_do])])}>Tải CSV cột bỏ được</button>
          </div>

          <div className="bang-cuon"><table className="bang-tl dd-bang">
            <thead><tr><th>Cột OBC</th><th>Phân loại</th><th>Vào kho</th><th>Màn hình hiện nó</th><th>Lý do</th></tr></thead>
            <tbody>{dong.map(c => (
              <tr key={c.ja} className={chon === "o:" + c.ja ? "dd-dang" : undefined}
                onClick={() => c.loai !== "khong_nap" && datChon(chon === "o:" + c.ja ? null : "o:" + c.ja)}>
                <td className="cot-obc">{c.ja}</td>
                <td><span className={"vien " + LOAI_CUA[c.loai].mau}>{LOAI_CUA[c.loai].nhan}</span></td>
                <td>{c.core ? <code>{c.core.replace(/^core\./, "")}</code> : c.loai === "khong_nap" ? "—" : <span className="khong-ap-dung">không lưu</span>}</td>
                {/* "Mã web chung" chỉ hiện khi nó là chỗ DUY NHẤT dùng cột — cạnh tên màn cụ thể thì nó không nói thêm gì. */}
                <td>{c.man.length ? c.man.filter(k => k !== "chung" || c.man.length === 1)
                  .map(k => <span key={k} className="vien nhat dd-man">{tenMan(k)}</span>) : "—"}</td>
                <td className="khong-ap-dung">{c.ly_do}</td>
              </tr>))}
              {!dong.length && <tr><td colSpan={5} className="trong">Không có cột nào khớp bộ lọc.</td></tr>}</tbody>
          </table></div>
        </section>

        <SoDoDuongDi f={f} m={m} chon={chon} datChon={datChon} />
        <SoDoKhoa m={m} bangFile={f.core_table} />

        <section id="han-che">
          <h2>Giới hạn của phép dò</h2>
          <ul className="dd-han">
            <li>Postgres chỉ ghi "view X dùng cột Y", không ghi cột Y chảy vào cột nào của X — nên phép dò lần theo <strong>tên cột trong định nghĩa view</strong>. Trùng tên giữa hai bảng thì tính là dùng cả hai.</li>
            <li>Mã Python đọc bảng bằng <code>SELECT *</code> thì mọi cột của bảng đó tính là đang dùng.</li>
            <li>Mọi chỗ nghi ngờ đều xếp về phía "đang dùng": phép dò có thể báo thừa, không báo thiếu. Cột "bỏ được" là cột chắc chắn không màn nào của web app đọc.</li>
            <li>Không biết công cụ ngoài (BI, Excel nối thẳng CSDL qua vai trò <code>kome_report</code>) có đọc cột nào không.</li>
            <li>Cột bỏ rồi thì từ ngày đó không còn số — tính năng làm sau cần cột đó sẽ không có lịch sử.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hình đường đi: cột OBC → cột kho → chỉ số mart → màn hình. Bấm một mục bất kỳ
// để sáng đường đi của nó. Vị trí tính ở đây (không có số liệu nào được tính).
// ---------------------------------------------------------------------------

const DONG = 22, DAU = 34;
const X = [0, 250, 520, 820], RONG = 1000;

function SoDoDuongDi({ f, m, chon, datChon }: { f: NonNullable<Man["file"]>; m: Man; chon: string | null; datChon: (s: string | null) => void }) {
  const cot = f.cot.filter(c => c.loai !== "khong_nap");
  const core = [...new Set(cot.map(c => c.core).filter((x): x is string => !!x))];
  const view = [...new Set(cot.flatMap(c => c.view))].sort();
  const man = [...new Set(cot.flatMap(c => c.man))].sort((a, b) => (m.man_hinh[a]?.ten ?? a).localeCompare(m.man_hinh[b]?.ten ?? b));
  const cao = DAU + Math.max(cot.length, core.length, view.length, man.length, 1) * DONG + 8;
  const y = (i: number) => DAU + i * DONG + DONG / 2;
  const iCore = new Map(core.map((c, i) => [c, i])), iView = new Map(view.map((v, i) => [v, i])), iMan = new Map(man.map((k, i) => [k, i]));

  // Mỗi cột OBC → các nút nó chạm. Chọn một nút = sáng mọi cột OBC chạm nút đó.
  const cham = cot.map(c => new Set(["o:" + c.ja, ...(c.core ? ["c:" + c.core] : []), ...c.view.map(v => "v:" + v), ...c.man.map(k => "m:" + k)]));
  const sang = chon ? cot.map((_, i) => cham[i].has(chon)) : null;
  const nutSang = new Set<string>();
  if (sang) cot.forEach((_, i) => sang[i] && cham[i].forEach(n => nutSang.add(n)));

  type Duong = { d: string; i: number };
  const duong: Duong[] = [];
  const noi = (x1: number, y1: number, x2: number, y2: number) => {
    const g = (x1 + x2) / 2;
    return `M${x1},${y1} C${g},${y1} ${g},${y2} ${x2},${y2}`;
  };
  cot.forEach((c, i) => {
    if (c.core) duong.push({ d: noi(X[0] + 200, y(i), X[1], y(iCore.get(c.core)!)), i });
    for (const v of c.view) if (c.core) duong.push({ d: noi(X[1] + 220, y(iCore.get(c.core)!), X[2], y(iView.get(v)!)), i });
    for (const k of c.man) {
      const qua = c.view.filter(v => (m.view_man[v] ?? []).includes(k));
      if (qua.length) for (const v of qua) duong.push({ d: noi(X[2] + 250, y(iView.get(v)!), X[3], y(iMan.get(k)!)), i });
      else if (c.core) duong.push({ d: noi(X[1] + 220, y(iCore.get(c.core)!), X[3], y(iMan.get(k)!)), i });
    }
  });
  // Đường trùng (cùng d) chỉ vẽ một lần; sáng nếu một trong các cột của nó đang sáng.
  const gop = new Map<string, boolean>();
  for (const d of duong) gop.set(d.d, (gop.get(d.d) ?? false) || (sang ? sang[d.i] : false));

  const nut = (id: string, x: number, i: number, chu: string, phu?: string, rong = 200) => {
    const bat = chon === id, s = nutSang.has(id);
    return (
      <g key={id} className={"dd-nut" + (s ? " sang" : sang ? " mo" : "") + (bat ? " bat" : "")} onClick={() => datChon(bat ? null : id)}
        role="button" tabIndex={0} onKeyDown={e => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), datChon(bat ? null : id))}
        aria-pressed={bat}>
        <rect x={x} y={DAU + i * DONG + 2} width={rong} height={DONG - 4} rx={4} />
        <text x={x + 6} y={y(i) + 4}>{chu}{phu && <tspan className="dd-phu"> {phu}</tspan>}</text>
      </g>);
  };

  return (
    <section id="duong-di">
      <div className="tieu-de-khoi"><h2>Đường đi từng cột</h2>
        <span className="khong-ap-dung">bấm một mục để sáng đường đi · bấm lại để bỏ{chon && <> · <button type="button" className="nut-nho" onClick={() => datChon(null)}>Bỏ chọn</button></>}</span></div>
      <p className="ghi-chu">{cot.length} cột được nạp (cột kho không nạp không có đường đi nên không vẽ). Mục <strong>chỉ số</strong> là view/hàm
        trong <code>mart</code> — nơi DUY NHẤT định nghĩa chỉ số.</p>
      <div className="bang-cuon"><svg className="dd-svg" viewBox={`0 0 ${RONG} ${cao}`} style={{ minWidth: 900 }} role="img"
        aria-label={`Đường đi của ${cot.length} cột ${f.ja} tới màn hình`}>
        {["CỘT OBC", "VÀO KHO (core)", "CHỈ SỐ (mart)", "MÀN HÌNH"].map((t, i) => <text key={t} x={X[i]} y={16} className="dd-cot-nhan">{t}</text>)}
        <g className="dd-duong">{[...gop].map(([d, s]) => <path key={d} d={d} className={s ? "sang" : sang ? "mo" : undefined} />)}</g>
        {cot.map((c, i) => nut("o:" + c.ja, X[0], i, c.ja))}
        {core.map((c, i) => nut("c:" + c, X[1], i, c.replace(/^core\./, ""), undefined, 220))}
        {view.map((v, i) => nut("v:" + v, X[2], i, v.replace(/^mart\./, ""), undefined, 250))}
        {man.map((k, i) => nut("m:" + k, X[3], i, m.man_hinh[k]?.ten ?? k, undefined, 180))}
      </svg></div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Sơ đồ nối khoá: mỗi bảng core một hộp; đường kẻ từ cột khoá ngoại sang cột
// khoá của bảng đích. Bảng fact bên trái, bảng dim bên phải.
// ---------------------------------------------------------------------------

function SoDoKhoa({ m, bangFile }: { m: Man; bangFile: string }) {
  const [chon, datChon] = useState<string | null>(bangFile);
  const { bang, noi } = m.khoa;
  // Chỉ hiện cột có vai trò khoá: khoá chính + cột nằm trong một đường nối.
  const cotCua = (b: { ten: string; cot: string[]; khoa: string[] }) => {
    const dung = new Set([...b.khoa, ...noi.flatMap(n => [n.tu, n.den]).filter(x => x.startsWith(b.ten + ".")).map(x => x.slice(b.ten.length + 1))]);
    return b.cot.filter(c => dung.has(c));
  };
  const trai = bang.filter(b => !b.ten.includes(".dim_")), phai = bang.filter(b => b.ten.includes(".dim_"));
  const DH = 20, DAU_H = 26, GIUA = 18;
  const vi = new Map<string, { x: number; y: number; w: number }>();
  const hop: { ten: string; x: number; y: number; w: number; h: number; cot: string[]; khoa: string[] }[] = [];
  const xep = (ds: typeof bang, x: number, w: number) => {
    let yy = 10;
    for (const b of ds) {
      const c = cotCua(b);
      const h = DAU_H + Math.max(c.length, 1) * DH + 6;
      hop.push({ ten: b.ten, x, y: yy, w, h, cot: c, khoa: b.khoa });
      c.forEach((ten, i) => vi.set(`${b.ten}.${ten}`, { x, y: yy + DAU_H + i * DH + DH / 2, w }));
      yy += h + GIUA;
    }
    return yy;
  };
  const W = 250, XT = 20, XP = 620;
  const cao = Math.max(xep(trai, XT, W), xep(phai, XP, W));
  const sangNoi = (n: { tu: string; den: string }) => !!chon && (n.tu.startsWith(chon + ".") || n.den.startsWith(chon + "."));

  return (
    <section id="noi-khoa">
      <div className="tieu-de-khoi"><h2>Sơ đồ nối khoá</h2>
        <span className="khong-ap-dung">◆ khoá chính · ● khoá ngoại · bấm một bảng để sáng các đường nối của nó</span></div>
      <p className="ghi-chu">Đường liền: khoá ngoại thật của CSDL (ghi sai là CSDL từ chối) · đường đứt: nối theo nghĩa nghiệp vụ khai trong
        <code> files.yml</code> (CSDL không kiểm — mã không khớp thì dòng chỉ lặng lẽ không nối được).</p>
      <div className="bang-cuon"><svg className="dd-svg dd-khoa" viewBox={`0 0 900 ${cao}`} style={{ minWidth: 760 }} role="img" aria-label="Sơ đồ nối khoá giữa các bảng core">
        <g className="dd-duong">{noi.map((n, i) => {
          const a = vi.get(n.tu), b = vi.get(n.den);
          if (!a || !b) return null;
          const x1 = a.x < b.x ? a.x + a.w : a.x, x2 = a.x < b.x ? b.x : b.x + b.w;
          const cung = a.x === b.x, g = cung ? a.x - 40 : (x1 + x2) / 2;
          const d = cung ? `M${a.x},${a.y} C${g},${a.y} ${g},${b.y} ${b.x},${b.y}` : `M${x1},${a.y} C${g},${a.y} ${g},${b.y} ${x2},${b.y}`;
          return <path key={i} d={d} className={(sangNoi(n) ? "sang" : chon ? "mo" : "") + (n.nguon.startsWith("files") ? " dut" : "")}>
            <title>{`${n.tu} → ${n.den} (${n.nguon})`}</title></path>;
        })}</g>
        {hop.map(h => (
          <g key={h.ten} className={"dd-hop" + (chon === h.ten ? " bat" : "")} onClick={() => datChon(chon === h.ten ? null : h.ten)}
            role="button" tabIndex={0} aria-pressed={chon === h.ten}
            onKeyDown={e => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), datChon(chon === h.ten ? null : h.ten))}>
            <rect x={h.x} y={h.y} width={h.w} height={h.h} rx={6} />
            <text x={h.x + 8} y={h.y + 17} className="dd-hop-ten">{h.ten.replace(/^core\./, "")}</text>
            {h.cot.map((c, i) => (
              <text key={c} x={h.x + 10} y={h.y + DAU_H + i * DH + DH / 2 + 4}>{h.khoa.includes(c) ? "◆ " : "● "}{c}</text>))}
          </g>))}
      </svg></div>
    </section>
  );
}
