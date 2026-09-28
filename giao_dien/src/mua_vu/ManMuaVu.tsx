// Màn "Mùa vụ sản phẩm" (/mua-vu, đặc tả 2026-09-29-mua-vu-san-pham-design.md): kéo thanh
// thời gian theo NGÀY, treemap ngành → mã đổi theo cửa sổ N ngày kết thúc ở ngày đó.
// Không theo khoảng xem chung (thanh kéo là trục thời gian riêng). Chỉ số (?cs=) và cửa
// sổ (?n=) nằm trên URL; vị trí thanh kéo thì không.
import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useRef, useState } from "react";
import { lay } from "../api";
import { useRong } from "../chung/hooks";
import { Khoi } from "../chung/Khoi";
import { DongNoi, ONoi } from "../chung/ONoi";
import { gon, ngay, pc, so_luong, yen } from "../dinh_dang";
import { giuKhoang } from "../khung/khoang";
import { CAO_NHAN, xep } from "./cay_o";
import { LuyKe, cuaSo, namTruoc, ngayCua, type ChiSo, type DuLieuMV } from "./du_lieu";
import { ThanhThoiGian } from "./ThanhThoiGian";
import "./mua_vu.css";

const CHI_SO: { ma: ChiSo; nhan: string }[] = [
  { ma: "dt", nhan: "Doanh thu" }, { ma: "lg", nhan: "Lãi gộp" }, { ma: "sl", nhan: "Số lượng" }];
const CUA_SO = [7, 30, 90];
const CAO_CAY = 460;

const docUrl = () => {
  const q = new URLSearchParams(location.search);
  const cs = (["dt", "lg", "sl"] as ChiSo[]).find(x => x === q.get("cs")) ?? "dt";
  const n = CUA_SO.find(x => String(x) === q.get("n")) ?? 30;
  return { cs, n };
};

const inSo = (cs: ChiSo, v: number) => (cs === "sl" ? so_luong(v) : yen(v));
const inGon = (cs: ChiSo, v: number) => (cs === "sl" ? so_luong(v, 0) : gon(v));

export default function ManMuaVu() {
  const q = useQuery({ queryKey: ["mua-vu"], queryFn: () => lay<DuLieuMV>("/api/mua-vu"), staleTime: 5 * 60e3 });
  const [{ cs, n }, datUrl] = useState(docUrl);
  const [b, datBTho] = useState<number | null>(null);
  const [tat, datTat] = useState<Set<number>>(new Set());
  const [danhDau, datDanhDau] = useState<number | null>(null);
  const [tim, datTim] = useState("");
  const [ref, rong] = useRong<HTMLDivElement>();

  // Gom nhiều cú kéo trong một khung hình thành một lần vẽ lại.
  const raf = useRef(0);
  const datB = useCallback((x: number) => {
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => datBTho(x));
  }, []);

  const doiUrl = (moi: { cs?: ChiSo; n?: number }) => {
    const gt = { cs, n, ...moi };
    datUrl(gt);
    const p = new URLSearchParams(location.search);
    p.set("cs", gt.cs); p.set("n", String(gt.n));
    history.replaceState(null, "", giuKhoang(`${location.pathname}?${p}`));
  };

  const dl = q.data;
  const L = useMemo(() => (dl ? new LuyKe(dl) : null), [dl]);
  const nganhCua = useMemo(() => dl?.ma.map(m => (m.nganh ? dl.nganh.indexOf(m.nganh) : -1)) ?? [], [dl]);
  // Thứ tự ngành cố định: tổng chỉ số trên TOÀN kỳ dữ liệu (không đổi khi kéo).
  const thuTu = useMemo(() => {
    if (!dl || !L) return [];
    const t = dl.nganh.map((_, k) => ({ k, v: 0 }));
    dl.ma.forEach((_, m) => { if (nganhCua[m] >= 0) t[nganhCua[m]].v += Math.max(0, L.tong(cs, m, 0, L.so_ngay - 1)); });
    return t.sort((a, c) => c.v - a.v).map(x => x.k);
  }, [dl, L, cs, nganhCua]);

  // Mở trang ở NGÀY CUỐI có dữ liệu (đặc tả §3) — suy trực tiếp từ `b ?? …`,
  // không qua một effect chạy SAU lần vẽ đầu (effect đó từng làm ô đầu tiên vẽ
  // ở ngày 0 rồi mới nhảy sang ngày cuối, ai mở trang cũng thấy mọi ô "bay" một
  // nhịp animation từ bố cục ngày 0 sang bố cục thật).
  const bb = b ?? (L ? Math.max(0, L.so_ngay - 1) : 0);
  const cua = cuaSo(bb, n);
  const truoc = dl?.ngay_dau ? namTruoc(dl.ngay_dau, bb, n) : null;
  const gia = useMemo(() => (L ? Float64Array.from({ length: L.so_ma }, (_, m) => L.tong(cs, m, cua.a, cua.b)) : new Float64Array()),
    [L, cs, cua.a, cua.b]);
  const cay = useMemo(() => (dl && rong ? xep({
    gia_tri: gia, nganh_cua: nganhCua, thu_tu_nganh: thuTu, tat,
    phi: dl.phi, tang: dl.tang, w: rong, h: CAO_CAY,
  }) : null), [dl, rong, gia, nganhCua, thuTu, tat]);

  if (q.isLoading || q.error || !dl || !L) {
    return <Khoi tieu_de="Mùa vụ sản phẩm" dang_tai={q.isLoading} loi={q.error ? (q.error as Error).message : undefined} />;
  }
  if (!L.so_ngay) return <Khoi tieu_de="Mùa vụ sản phẩm" canh_bao="Kho chưa có dòng bán nào." />;

  const kv = cay?.khong_ve;
  // Mảng đoạn thay vì nối chuỗi trực tiếp — tránh dấu " · " lửng lơ ở cuối khi
  // đoạn cuối cùng có giá trị nhưng các đoạn sau nó (rỗng) từng để lại dấu chấm mồ côi.
  const khongVe = kv ? [
    kv.phi ? `phí & điều chỉnh ${inSo(cs, kv.phi)}` : null,
    kv.tang ? `hàng tặng ${inSo(cs, kv.tang)}` : null,
    kv.am ? `${kv.so_am} mã ≤ 0 trong cửa sổ ${inSo(cs, kv.am)}` : null,
    kv.tat ? `ngành đang tắt ${inSo(cs, kv.tat)}` : null,
  ].filter((x): x is string => x !== null) : [];
  const timMa = tim.trim().toLowerCase();
  const goiY = timMa ? dl.ma.map((m, k) => ({ m, k })).filter(({ m, k }) => nganhCua[k] >= 0
    && (m.ma.toLowerCase().includes(timMa) || m.ten.toLowerCase().includes(timMa))).slice(0, 8) : [];

  const canhBao = [
    cua.thieu ? `Cửa sổ chưa đủ ${n} ngày — dữ liệu chỉ có từ ${ngay(dl.ngay_dau)}.` : null,
    !truoc ? "Năm trước chưa có dữ liệu cho cửa sổ này — số so năm trước trong ô nổi mỗi mã sẽ hiện “—”." : null,
  ].filter(Boolean).join(" ");

  const cachTinh = `Mỗi ô = tổng ${n} ngày kết thúc ở ngày đang chọn. Doanh thu thuần (chưa thuế), đã gồm phiếu đỏ (trả hàng, số âm). Không tính mua hàng của nhân viên. Phí & điều chỉnh và hàng tặng không phải sản phẩm nên không vẽ, nhưng tiền vẫn có trong tổng.`
    + (cs === "sl" ? " Số lượng cộng lẫn thùng (ケース) và lẻ (バラ): so MỘT mã qua các mùa là đúng, so kích thước ô giữa hai mã khác nhau thì không." : "");

  return (
    <div className="mv">
      <div className="mv-chon">
        <div className="mv-nhom" role="group" aria-label="Chỉ số">
          {CHI_SO.map(c => <button key={c.ma} type="button" className="chip"
            aria-pressed={c.ma === cs} onClick={() => doiUrl({ cs: c.ma })}>{c.nhan}</button>)}
        </div>
        <div className="mv-nhom" role="group" aria-label="Cửa sổ">
          {CUA_SO.map(x => <button key={x} type="button" className="chip"
            aria-pressed={x === n} onClick={() => doiUrl({ n: x })}>{x} ngày</button>)}
        </div>
        <div className="mv-tim">
          <input type="search" placeholder="Đánh dấu một mã…" value={tim} onChange={e => datTim(e.target.value)}
                 onKeyDown={e => { if (e.key === "Escape") { datTim(""); datDanhDau(null); } }} />
          {goiY.length > 0 && (
            <ul className="mv-goi-y">{goiY.map(({ m, k }) => (
              <li key={m.ma}><button type="button" onClick={() => { datDanhDau(k); datTim(""); }}>{m.ma} · {m.ten}</button></li>))}
            </ul>)}
          {danhDau !== null && <button type="button" className="chip" aria-pressed onClick={() => datDanhDau(null)}>
            {dl.ma[danhDau].ma} ✕</button>}
        </div>
      </div>
      <div className="mv-nhom mv-nganh" role="group" aria-label="Ngành">
        {thuTu.map(k => (
          <button key={k} type="button" className="chip mv-chip-n" aria-pressed={!tat.has(k)}
            onClick={() => datTat(s => { const t = new Set(s); t.has(k) ? t.delete(k) : t.add(k); return t; })}>
            <i className={"mv-n" + (k % 12)} /> {dl.nganh[k]}
          </button>))}
      </div>

      <Khoi tieu_de={`${n} ngày · ${ngay(ngayCua(dl.ngay_dau!, cua.a))} → ${ngay(ngayCua(dl.ngay_dau!, cua.b))}`}
            phu={cay ? `Tổng ${inSo(cs, cay.tong)}` : undefined} cach_tinh={cachTinh} canh_bao={canhBao || undefined}>
        <a href="#mv-ngay-cuoi" className="mv-bo-qua">Bỏ qua ô, tới thanh thời gian</a>
        <div ref={ref} className="mv-cay">
          {cay && (
            <svg width={rong} height={CAO_CAY} role="group" aria-label="Treemap ngành và mã hàng">
              {cay.nganh.map(g => (
                <g key={"n" + g.n}>
                  <rect x={g.x} y={g.y} width={g.w} height={g.h} className={"mv-o-nganh mv-n" + (g.n % 12)} />
                  {g.h >= 40 && g.w >= 60 && <text x={g.x + 4} y={g.y + CAO_NHAN - 4} className="mv-chu-nganh">
                    {dl.nganh[g.n]} · {inGon(cs, g.v)}</text>}
                  {g.ma.map(o => {
                    const m = dl.ma[o.m];
                    const nt = truoc ? L.tong(cs, o.m, truoc.a, truoc.b) : null;
                    const hang = g.ma.indexOf(o) + 1;
                    return (
                      <ONoi key={m.ma} svg href={m.an ? undefined : giuKhoang(`/san-pham/${encodeURIComponent(m.ma)}`)}
                        nhan={m.ten}
                        noi_dung={<>
                          <b>{m.ten}</b> <span className="mo">{m.ma}</span>
                          <DongNoi nhan="Ngành" gia={m.nganh} />
                          <DongNoi nhan={`${n} ngày này`} gia={inSo(cs, o.v)} />
                          <DongNoi nhan="Cùng kỳ năm trước" gia={nt === null ? "—" : inSo(cs, nt)} />
                          <DongNoi nhan="Hạng trong ngành" gia={`${hang}/${g.ma.length} · ${pc(o.v / g.v)}`} />
                          {m.an && <div className="mo">Đã ngừng kinh doanh — không có trang sản phẩm.</div>}
                        </>}>
                        <g className={"mv-o-ma" + (o.m === danhDau ? " danh-dau" : "")}>
                          <rect x={o.x} y={o.y} width={o.w} height={o.h} />
                          {o.w >= 54 && o.h >= 22 && <text x={o.x + 3} y={o.y + 13} className="mv-chu-ma">
                            {m.ten.length > o.w / 7 ? m.ten.slice(0, Math.max(1, Math.floor(o.w / 7) - 1)) + "…" : m.ten}</text>}
                        </g>
                      </ONoi>);
                  })}
                </g>))}
            </svg>)}
        </div>
        {khongVe.length > 0 && <p className="mv-khong-ve">Không vẽ: {khongVe.join(" · ")}</p>}
      </Khoi>

      <ThanhThoiGian so_ngay={L.so_ngay} ngay_dau={dl.ngay_dau!} tong_ngay={L.tongNgay} b={bb} n={n} datB={datB} />
    </div>
  );
}
