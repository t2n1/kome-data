// Tab "Theo mùa" của màn Mùa vụ: bản đồ nhiệt mã × tháng lịch. Trả lời "mùa này mã nào bán
// chạy, sang mùa khác nó còn chạy không" — cả dải tháng trên CÙNG một hàng (treemap chỉ cho
// một lát thời gian). Logic thuần ở ./nhiet.ts; số mỗi ô = tổng các ngày của tháng từ LuyKe.
import { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useRong } from "../chung/hooks";
import { Khoi } from "../chung/Khoi";
import { HinhMa, HinhMaSvg } from "../chung/HinhMa";
import { DongNoi, ONoi } from "../chung/ONoi";
import { ngay_ngan, pc, thang_nhan } from "../dinh_dang";
import { CAU_SO_LUONG, MUA, inSo, ngayCua, type ChiSo, type DuLieuMV, type LuyKe } from "./du_lieu";
import { bac, bangNhiet, buocPhim, catTen, cungThangNamTruoc, thangCaoDiem, thangCuaKy, xepHang, type KieuXep, type Thang } from "./nhiet";

export type KieuTo = "ma" | "bang";
const CAO_HANG = 16;
const DAU = 36;          // dải mùa + năm + số tháng
const MUA_CAO = 6;
const ANH = CAO_HANG - 2;   // ảnh nhỏ ở cột nhãn — bằng cao hàng
const LE_ANH = 20;          // chỉ vẽ ảnh nhãn cho hàng trong khung cuộn ± 20 hàng (SVG <image> không lazy)
const TEN_THANG = ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];

type Bang = {
  hien: number[];            // mã (chỉ số trong dl.ma) theo thứ tự hàng hiện
  g: Float64Array;           // hàng × cột, CÙNG thứ tự với `hien`
  max_hang: Float64Array;    // tháng DƯƠNG lớn nhất của từng hàng (0 nếu không có)
  max_bang: number;
  tong: Float64Array;
  cao_diem: (number | null)[];
  so_bo: number;             // mã có tổng cả kỳ ≤ 0 — không vẽ
};

export function BanDoNhiet({ dl, L, cs, nganhCua, tat, danhDau, to, datTo, kieu, datKieu, onChon }: {
  dl: DuLieuMV; L: LuyKe; cs: ChiSo; nganhCua: number[]; tat: Set<number>; danhDau: number | null;
  to: KieuTo; datTo: (t: KieuTo) => void; kieu: KieuXep; datKieu: (k: KieuXep) => void;
  onChon: (b: number) => void;
}) {
  const [ref, rong] = useRong<HTMLDivElement>();
  const thang = useMemo(() => thangCuaKy(dl.ngay_dau!, dl.ngay_cuoi!), [dl]);
  const C = thang.length;

  const bang = useMemo<Bang>(() => {
    const ung = dl.ma.map((_, m) => m).filter(m =>
      m !== dl.phi && m !== dl.tang && nganhCua[m] >= 0 && !tat.has(nganhCua[m]));
    const g0 = bangNhiet(L, cs, thang, ung);
    const giu: number[] = []; let so_bo = 0;
    ung.forEach((_, h) => {
      let s = 0; for (let k = 0; k < C; k++) s += g0[h * C + k];
      if (s > 0) giu.push(h); else so_bo++;
    });
    const g1 = new Float64Array(giu.length * C);
    giu.forEach((h, r) => g1.set(g0.subarray(h * C, (h + 1) * C), r * C));
    const thu_tu = xepHang(g1, C, thang, kieu);
    const g = new Float64Array(thu_tu.length * C);
    thu_tu.forEach((r, i) => g.set(g1.subarray(r * C, (r + 1) * C), i * C));
    const hien = thu_tu.map(r => ung[giu[r]]);
    const max_hang = new Float64Array(hien.length), tong = new Float64Array(hien.length);
    let max_bang = 0;
    const cao_diem = hien.map((_, i) => {
      const hang = g.subarray(i * C, (i + 1) * C);
      for (let k = 0; k < C; k++) { tong[i] += hang[k]; if (hang[k] > max_hang[i]) max_hang[i] = hang[k]; }
      if (max_hang[i] > max_bang) max_bang = max_hang[i];
      return thangCaoDiem(hang, thang);
    });
    return { hien, g, max_hang, max_bang, tong, cao_diem, so_bo };
  }, [dl, L, cs, thang, C, nganhCua, tat, kieu]);

  const NHAN = rong && rong < 480 ? 118 : 184;
  const CW = rong ? Math.min(64, Math.max(22, Math.floor((rong - NHAN) / Math.max(1, C)))) : 0;
  const R = bang.hien.length;
  const H = R * CAO_HANG;
  const hangDD = danhDau === null ? -1 : bang.hien.indexOf(danhDau);

  // Roving tabindex: cả lưới là MỘT điểm dừng Tab; ô đang giữ có tabIndex 0, mọi ô khác -1.
  const [hoat0, datHoat] = useState<[number, number]>([0, 0]);
  const hr = Math.max(0, Math.min(R - 1, hoat0[0])), hc = Math.max(0, Math.min(C - 1, hoat0[1]));
  const luoiRef = useRef<SVGSVGElement>(null);
  const phim = (e: React.KeyboardEvent) => {
    const nx = buocPhim(e.key, hr, hc, R, C);
    if (!nx) return;
    e.preventDefault();
    datHoat(nx);
    luoiRef.current?.querySelector<SVGElement>(`[data-o="${nx[0]}-${nx[1]}"]`)?.focus();
  };
  // Focus bằng chuột / chạm cũng dời ô đang giữ (Tab quay lại đúng ô vừa bấm).
  const khiFocus = (e: React.FocusEvent) => {
    const o = (e.target as Element).getAttribute?.("data-o");
    if (!o) return;
    const [r, c] = o.split("-").map(Number);
    if (r !== hr || c !== hc) datHoat([r, c]);
  };

  // Hàng đang trong khung cuộn (± LE_ANH) — chỉ những hàng này có ảnh ở cột nhãn.
  const cuonRef = useRef<HTMLDivElement | null>(null);
  const refCuon = useCallback((e: HTMLDivElement | null) => { cuonRef.current = e; ref(e); }, [ref]);
  const [khung, datKhung] = useState<[number, number]>([0, 40 + LE_ANH]);
  const raf = useRef(0);
  const doKhung = useCallback(() => {
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => {
      const el = cuonRef.current;
      if (!el) return;
      const a = Math.max(0, Math.floor(el.scrollTop / CAO_HANG) - LE_ANH);
      const b = Math.ceil((el.scrollTop + el.clientHeight) / CAO_HANG) + LE_ANH;
      datKhung(k => (k[0] === a && k[1] === b ? k : [a, b]));
    });
  }, []);
  useLayoutEffect(() => { doKhung(); return () => cancelAnimationFrame(raf.current); }, [doKhung, CW, R]);

  const ddRef = useRef<SVGRectElement>(null);
  useEffect(() => { if (hangDD >= 0) ddRef.current?.scrollIntoView({ block: "nearest", inline: "nearest" }); }, [hangDD, danhDau]);

  const doDang = thang.filter(t => t.do_dang);
  const lapLai = Math.max(0, ...Array.from({ length: 12 }, (_, i) => thang.filter(t => +t.thang.slice(5) === i + 1).length));
  const canhBao = [
    doDang.length ? `Tháng dở dang (chữ nghiêng): ${doDang.map(t => `${thang_nhan(t.thang)} chỉ có ${moTaDoDang(dl.ngay_dau!, t)}`).join(" · ")} — không so như tháng trọn, không dùng để tìm tháng cao điểm.` : null,
    lapLai < 3 ? `Mới có ${C} tháng dữ liệu: mỗi mùa mới lặp lại tối đa ${lapLai} lần — chưa đủ để khẳng định một mã là hàng theo mùa.` : null,
  ].filter(Boolean).join(" ");
  const cachTinh = "Mỗi ô = tổng cả tháng của chỉ số đang chọn (doanh thu thuần chưa thuế, đã gồm phiếu đỏ trả hàng; không tính mua hàng của nhân viên; phí & điều chỉnh và hàng tặng không phải sản phẩm nên không có hàng). “Từng mã”: ô so với tháng cao nhất của CHÍNH mã đó; “Toàn bộ”: so với ô lớn nhất của cả bảng. Ô ≤ 0 để trống. Tháng cao điểm = tháng lịch có trung bình mỗi năm cao nhất, chỉ tính tháng trọn. Bấm một ô để mở Ảnh chụp 30 ngày kết thúc ở cuối tháng đó."
    + (cs === "sl" ? CAU_SO_LUONG : "");

  const ctx = useMemo<NgCanh>(() => ({ bang, thang, C, CW, to, cs, dl, L, onChon, NHAN, nganhCua }),
    [bang, thang, C, CW, to, cs, dl, L, onChon, NHAN, nganhCua]);

  const tieuDe = C ? `Theo mùa · ${thang_nhan(thang[0].thang)} → ${thang_nhan(thang[C - 1].thang)}` : "Theo mùa";
  return (
    <Khoi tieu_de={tieuDe} phu={`${R} mã`} cach_tinh={cachTinh} canh_bao={canhBao || undefined}>
      <div className="mv-nh-chon">
        <div className="mv-nhom" role="group" aria-label="Tô theo">
          <span className="mv-nh-nhan-chon">Tô theo</span>
          <button type="button" className="chip" aria-pressed={to === "ma"} onClick={() => datTo("ma")}>Từng mã</button>
          <button type="button" className="chip" aria-pressed={to === "bang"} onClick={() => datTo("bang")}>Toàn bộ</button>
        </div>
        <div className="mv-nhom" role="group" aria-label="Xếp">
          <span className="mv-nh-nhan-chon">Xếp</span>
          <button type="button" className="chip" aria-pressed={kieu === "cao_diem"} onClick={() => datKieu("cao_diem")}>Tháng cao điểm</button>
          <button type="button" className="chip" aria-pressed={kieu === "tong"} onClick={() => datKieu("tong")}>Tổng</button>
        </div>
        <div className="mv-nh-chu-giai" aria-hidden="true">
          <span>thấp</span>{[1, 2, 3, 4, 5].map(b => <i key={b} className={"mv-nh-b" + b} />)}<span>cao</span>
          <i className="mv-nh-b0" /><span>≤ 0</span>
        </div>
      </div>
      <a href="#mv-nh-het" className="mv-bo-qua">Bỏ qua bảng nhiệt</a>
      <p className="mv-nh-phim">Bàn phím: bảng là một điểm dừng Tab — dùng phím mũi tên để đi trong bảng (Home/End: đầu/cuối hàng · PageUp/PageDown: 10 hàng · Enter: mở ảnh chụp tháng đó).</p>
      <div ref={refCuon} className="mv-nh-cuon" onScroll={doKhung}>
        {CW > 0 && (
          <div className="mv-nh-bang" style={{ width: NHAN + C * CW }}>
            <div className="mv-nh-dau">
              <svg className="mv-nh-trai" width={NHAN} height={DAU} aria-hidden="true">
                <rect x={0} y={0} width={NHAN} height={DAU} className="mv-nh-nen-nhan" />
              </svg>
              <svg width={C * CW} height={DAU} role="group" aria-label="Tháng">
                <rect x={0} y={0} width={C * CW} height={DAU} className="mv-nh-nen-nhan" />
                <DauCot thang={thang} CW={CW} ngay_dau={dl.ngay_dau!} />
              </svg>
            </div>
            <div className="mv-nh-than">
              <svg className="mv-nh-trai" width={NHAN} height={H} role="group" aria-label="Tên mã hàng">
                {bang.hien.map((m, i) => <NhanHang key={dl.ma[m].ma} i={i} m={m} anh={i >= khung[0] && i <= khung[1]} ctx={ctx} />)}
                {hangDD >= 0 && <rect ref={ddRef} x={0.5} y={hangDD * CAO_HANG} width={NHAN - 1} height={CAO_HANG - 1}
                  className="mv-nh-danh-dau" pointerEvents="none" />}
              </svg>
              <svg ref={luoiRef} width={C * CW} height={H} role="group"
                aria-label="Bản đồ nhiệt mã hàng theo tháng — dùng phím mũi tên để đi trong bảng"
                onKeyDown={phim} onFocus={khiFocus}>
                {bang.hien.map((m, i) => <HangNhiet key={dl.ma[m].ma} i={i} m={m} hoat={i === hr ? hc : -1} ctx={ctx} />)}
                {hangDD >= 0 && <rect x={0.5} y={hangDD * CAO_HANG} width={C * CW - 1} height={CAO_HANG - 1}
                  className="mv-nh-danh-dau" pointerEvents="none" />}
              </svg>
            </div>
          </div>)}
      </div>
      <p id="mv-nh-het" tabIndex={-1} className="mv-khong-ve">
        {bang.so_bo > 0 ? `${bang.so_bo} mã không có doanh số dương trong cả kỳ — không vẽ.` : ""}
        {danhDau !== null && hangDD < 0 ? ` ${dl.ma[danhDau].ma} không có hàng trong bảng (ngành đang tắt hoặc tổng ≤ 0).` : ""}
      </p>
    </Khoi>
  );
}

type NgCanh = {
  bang: Bang; thang: Thang[]; C: number; CW: number; to: KieuTo; cs: ChiSo; dl: DuLieuMV; L: LuyKe;
  onChon: (b: number) => void; NHAN: number; nganhCua: number[];
};

/** Một hàng ô. `hoat` = cột đang giữ của lưới nếu là hàng này, -1 nếu không — đổi ô chỉ vẽ lại ≤ 2 hàng. */
const HangNhiet = memo(function HangNhiet({ i, m, hoat, ctx }: { i: number; m: number; hoat: number; ctx: NgCanh }) {
  const { bang, thang, C, CW, to, cs, dl, L, onChon } = ctx;
  const ma = dl.ma[m], mh = bang.max_hang[i], ms = to === "ma" ? mh : bang.max_bang, cd = bang.cao_diem[i];
  // Thông tin của cột nhãn (không phải điểm dừng Tab) đi vào nhãn đọc của từng ô.
  const them = `ngành ${ma.nganh ?? "—"} · tổng cả kỳ ${inSo(cs, bang.tong[i])} · cao điểm ${cd === null ? "—" : `tháng ${cd}`}`;
  return (
    <g>
      {thang.map((t, k) => {
        const v = bang.g[i * C + k], b = bac(v, ms);
        const nt = cungThangNamTruoc(thang, k, dl.ngay_dau!);
        return (
          <ONoi key={k} svg tabIndex={k === hoat ? 0 : -1} data_o={`${i}-${k}`} onBam={() => onChon(t.b)}
            nhan={`${ma.ten} · ${thang_nhan(t.thang)}${t.do_dang ? " (dở dang)" : ""}: ${inSo(cs, v)} · ${them}`}
            noi_dung={<div className="o-noi-hinh">
              <HinhMa ma={ma.ma} ten={ma.ten} co={64} trang_tri />
              <div>
                <b>{ma.ten}</b> <span className="mo">{ma.ma}</span>
                <DongNoi nhan={thang_nhan(t.thang) + (t.do_dang ? " (dở dang)" : "")} gia={inSo(cs, v)} />
                <DongNoi nhan="So tháng cao nhất của mã" gia={mh > 0 ? pc(v / mh) : "—"} />
                <DongNoi nhan={nt?.cung_dai_ngay ? "Cùng dải ngày năm trước" : "Cùng tháng năm trước"}
                  gia={nt ? inSo(cs, L.tong(cs, m, nt.a, nt.b)) : "—"} />
                <div className="mo">Bấm để xem ảnh chụp 30 ngày cuối tháng này</div>
              </div>
            </div>}>
            <rect x={k * CW} y={i * CAO_HANG} width={CW - 1} height={CAO_HANG - 1}
              className={"mv-nh-o mv-nh-b" + b} />
          </ONoi>);
      })}
    </g>);
});

/** Nhãn một hàng — chỉ rê / chạm (tabIndex -1; thông tin đã có trong nhãn đọc của ô). `anh` = hàng
 *  đang gần khung cuộn: chỉ khi đó mới có <image> (SVG không có loading="lazy"). */
const NhanHang = memo(function NhanHang({ i, m, anh, ctx }: { i: number; m: number; anh: boolean; ctx: NgCanh }) {
  const { bang, dl, cs, NHAN, nganhCua } = ctx;
  const ma = dl.ma[m], y = i * CAO_HANG, cd = bang.cao_diem[i];
  const toiDa = (NHAN - 19 - ANH) / 6.4;
  return (
    <ONoi svg tabIndex={-1} nhan={ma.ten}
      noi_dung={<div className="o-noi-hinh">
        <HinhMa ma={ma.ma} ten={ma.ten} co={64} trang_tri />
        <div>
          <b>{ma.ten}</b> <span className="mo">{ma.ma}</span>
          <DongNoi nhan="Ngành" gia={ma.nganh} />
          <DongNoi nhan="Tổng cả kỳ" gia={inSo(cs, bang.tong[i])} />
          <DongNoi nhan="Tháng cao điểm" gia={cd === null ? "—" : `tháng ${cd}`} />
        </div>
      </div>}>
      <g className="mv-nh-nhan">
        <rect x={0} y={y} width={NHAN} height={CAO_HANG} className="mv-nh-nen-nhan" />
        <rect x={4} y={y + 4} width={8} height={8} rx={2} className={"mv-n" + (nganhCua[m] % 12)} />
        {anh && <HinhMaSvg ma={ma.ma} ten={ma.ten} x={15} y={y + 1} co={ANH} />}
        <text x={16 + ANH + 3} y={y + 12}>{catTen(ma.ten, toiDa)}</text>
      </g>
    </ONoi>);
});

function moTaDoDang(ngay_dau: string, t: Thang): string {
  // Dở dang ở đầu kỳ → "từ dd/mm"; ở cuối kỳ → "tới dd/mm" (cả hai nếu kỳ ngắn hơn một tháng).
  const [y, m] = t.thang.split("-").map(Number);
  const ngayA = ngayCua(ngay_dau, t.a), ngayB = ngayCua(ngay_dau, t.b);
  const dau = +ngayA.slice(8) !== 1, cuoi = +ngayB.slice(8) !== new Date(Date.UTC(y, m, 0)).getUTCDate();
  return [dau ? `từ ${ngay_ngan(ngayA)}` : "", cuoi ? `tới ${ngay_ngan(ngayB)}` : ""].filter(Boolean).join(" ");
}

// Ô tháng dở dang: chỉ rê / chạm (tabIndex -1) — câu cảnh báo của khối và nhãn đọc "(dở dang)" của
// từng ô đã nói điều đó, nên dải tháng không thêm điểm dừng Tab nào trước lưới.
const DauCot = memo(function DauCot({ thang, CW, ngay_dau }: { thang: Thang[]; CW: number; ngay_dau: string }) {
  return (
    <g>
      {thang.map((t, k) => {
        const [y, m] = t.thang.split("-").map(Number), x = k * CW;
        const chu = <>
          {(k === 0 || m === 1) && <text x={x + 2} y={MUA_CAO + 11} className="mv-nh-nam">{y}</text>}
          <text x={x + CW / 2} y={DAU - 5} textAnchor="middle" className={"mv-nh-thang" + (t.do_dang ? " do-dang" : "")}>
            {TEN_THANG[m]}{t.do_dang ? "*" : ""}</text>
        </>;
        return (
          <g key={t.thang}>
            <rect x={x} y={0} width={CW} height={MUA_CAO} className={"mv-mua-" + MUA[m]} />
            {t.do_dang
              ? <ONoi svg tabIndex={-1} nhan={`${thang_nhan(t.thang)} dở dang`}
                  noi_dung={<div className="o-noi-chu">{thang_nhan(t.thang)} là tháng dở dang: chỉ có dữ liệu {moTaDoDang(ngay_dau, t)}.</div>}>
                  <g><rect x={x} y={MUA_CAO} width={CW} height={DAU - MUA_CAO} fill="transparent" />{chu}</g>
                </ONoi>
              : <g aria-hidden="true">{chu}</g>}
          </g>);
      })}
    </g>
  );
});
