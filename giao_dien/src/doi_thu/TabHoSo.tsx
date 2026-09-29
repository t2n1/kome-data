// Tab "Đối thủ" (đợt 4b task 8; bản phác ca-trang-8.html tab Đối thủ): chip mọi bên · đầu trang (ngày bảng giá, số dòng,
// file gốc, ✎ sửa thông tin bên, website) · 4 ô số · "Giá bên này so với KOME, từng sản phẩm" (thanh lệch quanh vạch KOME,
// ô nổi có lịch sử giá theo tháng) · bán mạnh ngành nào · điều kiện bán + giao hàng · khách đang mua (Đợt 2).
// Luật ở ho_so_logic.ts; màu % theo mau.ts::mauLech; thương hiệu theo kieu.ts::NHAN_GHEP. Mọi chỗ hiện hàng / điều kiện /
// bên bấm được, mở pop-up sửa (SuaMatHang / SuaNho — không tự đóng, đóng ở `xong`).
import { useQuery } from "@tanstack/react-query";
import { Fragment, useMemo, useState } from "react";
import { lay } from "../api";
import { Khoi, Spark } from "../chung/Khoi";
import { DongNoi, ONoi } from "../chung/ONoi";
import { ngay, so, thang_nhan, yen } from "../dinh_dang";
import { chuoiKhoang, giuKhoang, useKhoang } from "../khung/khoang";
import type { DieuKien, GiaoHang, KhachDangMua, TongQuan } from "./kieu";
import { LOAI_DK, NHAN_GHEP, NHAN_TRANG_THAI, nhanDonVi } from "./kieu";
import { mauLech } from "./mau";
import { Ra } from "./NguonDong";
import { lienKetAnToan } from "./nguon";
import { pcDau } from "./so_sanh_logic";
import { SuaMatHang } from "./SuaMatHang";
import { SuaBen, SuaDieuKien, SuaGiaoHang } from "./SuaNho";
import { ThanhDem } from "./TabTin";
import { benMacDinh, chipBen, dauBen, dongSoKome, giaoTrong, lichSuThang, nganhBen, o4, tomTatGiao, type DongHs, type QsHs }
  from "./ho_so_logic";

type HoSo = { ben: { ma: string; ten: string; web: string | null; ghi_chu: string | null };
              dieu_kien: DieuKien[]; quan_sat: QsHs[]; khach_dang_mua?: KhachDangMua[];
              giao_hang: GiaoHang | null; sua_cuoi_ben: number };
type KetQua = HoSo | { khong_co: true };
type Sua = { loai: "mh"; q: QsHs; tru_o?: string } | { loai: "dk"; dk?: DieuKien } | { loai: "ben" } | { loai: "giao"; tru_o?: string };

const MAU: Record<string, string> = { do: "var(--do)", xanh: "var(--ok-vien)", xam: "var(--chu-mo)" };
const nhanLoai = (m: string) => (LOAI_DK.find(([k]) => k === m)?.[1] ?? m).toLowerCase();
const ngan = (t: string, n: number) => (t.length > n ? t.slice(0, n - 1) + "…" : t);

export function TabHoSo({ ben, chonBen, moDuyet }: { ben: string; chonBen: (ma: string) => void; moDuyet: (ma: string) => void }) {
  const kx = chuoiKhoang(useKhoang());
  const tq = useQuery({ queryKey: ["doi-thu", "tong-quan", kx], queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  // Không có ?ben= trên URL → bên nhiều mặt hàng ghép được KOME nhất (ho_so_logic.ts::benMacDinh). KHÔNG ghi lên URL:
  // link chia sẻ không mang bên thì người mở vẫn thấy bên mặc định của dữ liệu lúc đó.
  const ma = ben || (tq.data ? benMacDinh(tq.data) : "");
  const q = useQuery({ queryKey: ["doi-thu", "ben", ma, kx], enabled: !!ma,
    queryFn: () => lay<KetQua>(`/api/doi-thu/ben/${encodeURIComponent(ma)}${kx ? "?" + kx : ""}`) });
  const chip = useMemo(() => (tq.data ? chipBen(tq.data) : []), [tq.data]);
  const hs = q.data && !("khong_co" in q.data) ? q.data : null;
  const [sua, datSua] = useState<Sua | null>(null);
  const dongSua = () => datSua(null);

  return (
    <div className="dt-hs">
      <div className="dt-hs-chip" role="group" aria-label="Chọn đối thủ">
        {chip.map(b => (
          <button key={b.ma} type="button" aria-pressed={b.ma === ma} onClick={() => chonBen(b.ma)}>
            {b.ten} <span>{so(b.so)}</span></button>))}
      </div>
      {tq.isLoading || (!!ma && q.isLoading) ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>
        : tq.error || q.error ? <div className="khoi-loi">Không tải được: {((tq.error ?? q.error) as Error).message}</div>
        : !ma ? <p className="dt-nhat">Chưa theo dõi đối thủ nào.</p>
        : !hs ? <p className="dt-nhat">Không có đối thủ này.</p>
        : <HoSoBen hs={hs} tq={tq.data!} moSua={datSua} moDuyet={moDuyet} />}

      {sua?.loai === "mh" && <SuaMatHang nguon={sua.q.nguon} id={sua.q.id} tru_o={sua.tru_o} dong={dongSua} xong={dongSua} />}
      {hs && sua?.loai === "dk" && <SuaDieuKien ben={{ ma: hs.ben.ma, ten: hs.ben.ten }} dk={sua.dk} dong={dongSua} xong={dongSua} />}
      {hs && sua?.loai === "ben" && <SuaBen ben={hs.ben} sua_cuoi={hs.sua_cuoi_ben} dong={dongSua} xong={dongSua} />}
      {hs && sua?.loai === "giao" && (
        <SuaGiaoHang dong={hs.giao_hang ?? giaoTrong(hs.ben.ma, hs.ben.ten)} tru_o={sua.tru_o} dong_lai={dongSua} xong={dongSua} />)}
    </div>
  );
}

function HoSoBen({ hs, tq, moSua, moDuyet }: { hs: HoSo; tq: TongQuan; moSua: (s: Sua) => void; moDuyet: (ma: string) => void }) {
  const dau = useMemo(() => dauBen(hs.quan_sat), [hs]);
  const so4 = useMemo(() => o4(hs.quan_sat), [hs]);
  const dong = useMemo(() => dongSoKome(hs.quan_sat), [hs]);
  const nganh = useMemo(() => nganhBen(tq, hs.ben.ma), [tq, hs]);
  const web = lienKetAnToan(hs.ben.web);
  const giao = tomTatGiao(hs.giao_hang);
  return (
    <>
      <div className="dt-hs-dau">
        <h3>{hs.ben.ten}</h3>
        <small>
          {dau.ngay && <>bảng giá mới nhất {ngay(dau.ngay)} · </>}
          <button type="button" className="dt-hs-lk" onClick={() => moDuyet(hs.ben.ma)}
            aria-label={`${so(dau.soDong)} dòng hiện hành — mở Duyệt / sửa bảng giá của bên này`}>{so(dau.soDong)} dòng</button>
          {dau.nguon && <> · <Ra href={dau.nguon.href}>{dau.nguon.chu}</Ra></>}
          {" · "}<button type="button" className="dt-hs-lk" onClick={() => moSua({ loai: "ben" })}>✎ sửa thông tin bên</button>
          {web && <> · <Ra href={web}>website ↗</Ra></>}
        </small>
      </div>
      {hs.ben.ghi_chu && <p className="dt-nhat dt-hs-ghi">{hs.ben.ghi_chu}</p>}

      <div className="dt-tt-o4">
        <div className="dt-tt-o"><small>Mặt hàng trùng KOME (có giá để so)</small><b>{so(so4.trung)}</b></div>
        <div className="dt-tt-o"><small>Rẻ hơn KOME &gt; 5%</small><b className="c-do">{so(so4.reHon)}</b></div>
        <div className="dt-tt-o"><small>Đang hết</small><b className="c-vang">{so(so4.het)}</b></div>
        <div className="dt-tt-o"><small>Khuyến mãi đang chạy</small><b className="c-km">{so(so4.km)}</b></div>
      </div>

      <div className="dt-hs-hai">
        <section className="dt-khoi">
          <Khoi tieu_de="Giá bên này so với KOME, từng sản phẩm"
            cach_tinh="Mỗi thanh = một mặt hàng hiện hành của bên này ghép được với nhóm có giá KOME; dài = giá ¥/kg chưa thuế của bên so với giá KOME của nhóm (標準価格, thiếu thì thực bán 90 ngày). Trái = bên này rẻ hơn KOME. Tên là tên nhóm KOME; tên gốc trong ô nổi. Ngoài ±60% vẽ ở mép. Bấm thanh để sửa.">
            {dong.length ? <><BieuDoLech dong={dong} qs={hs.quan_sat} mo={(x, t) => moSua({ loai: "mh", q: x, tru_o: t })} /><ChuGiai /></>
              : <p className="dt-nhat">Chưa mặt hàng nào của bên này ghép được với nhóm có giá KOME.</p>}
          </Khoi>
        </section>
        <div className="dt-hs-phai">
          <section className="dt-khoi">
            <Khoi tieu_de="Bán mạnh ngành nào" cach_tinh="Số mặt hàng hiện hành của bên này ghép được với mã KOME, theo ngành của mã KOME.">
              {nganh.length ? <ThanhDem ds={nganh.map(x => ({ khoa: x.nganh, ten: x.nganh, so: x.so }))} />
                : <p className="dt-nhat">Chưa ghép được mặt hàng nào với ngành của KOME.</p>}
            </Khoi>
          </section>
          <section className="dt-khoi">
            <Khoi tieu_de="Điều kiện bán" cach_tinh="Điều kiện của bảng giá mới nhất (ship · thuế · thanh toán · khuyến mãi chung · khác) cộng dòng thêm tay. Bấm để sửa / bỏ.">
              <div className="dt-hs-dks">
                {hs.dieu_kien.map(k => (
                  <button key={`${k.them_tay ? "t" : "f"}${k.id}`} type="button" className="dt-hs-dk" title={k.noi_dung}
                    onClick={() => moSua({ loai: "dk", dk: k })} aria-label={`Sửa điều kiện: ${nhanLoai(k.loai)} — ${k.noi_dung}`}>
                    <i>{nhanLoai(k.loai)}</i>{ngan(k.noi_dung, 70)}</button>))}
                <button type="button" className="dt-hs-dk dt-hs-dk-moi" onClick={() => moSua({ loai: "dk" })}>+ thêm điều kiện</button>
              </div>
              <div className="dt-hs-giao">
                <b>Giao hàng</b>
                {giao.map(p => (
                  <span key={p.nhan}><i>{p.nhan}</i>{p.chu ?? (
                    <button type="button" className="dt-hoi-cam" aria-label={`${p.nhan}: chưa biết — điền`}
                      onClick={() => moSua({ loai: "giao", tru_o: p.tru_o })}>?</button>)}</span>))}
                <button type="button" className="dt-hs-lk" onClick={() => moSua({ loai: "giao" })}
                  aria-label={`Sửa điều kiện giao hàng của ${hs.ben.ten}`}>sửa</button>
              </div>
            </Khoi>
          </section>
        </div>
      </div>

      <section className="dt-khoi">
        <Khoi tieu_de={`Khách đang mua của bên này (${hs.khach_dang_mua?.length ?? 0})`}
          cach_tinh={`Các lần ghi tiếp xúc 90 ngày qua có gắn thẻ @${hs.ben.ma}, mới nhất trước.`}>
          {hs.khach_dang_mua?.length ? (
            <div className="dt-cuon">
              <table className="bang dt-bang">
                <caption className="dt-an">Các lần ghi tiếp xúc 90 ngày qua có gắn thẻ @{hs.ben.ma}, mới nhất trước</caption>
                <thead><tr><th>Ngày</th><th>Khách</th><th>Hàng nhắc cùng</th><th>Giá khách kể</th></tr></thead>
                <tbody>{hs.khach_dang_mua.map(k => (
                  <tr key={k.tiep_xuc_id}>
                    <td>{ngay(k.ngay)}</td>
                    <td><a href={giuKhoang(`/khach-hang/${encodeURIComponent(k.ma_khach)}`)}>{k.ten_khach ?? k.ma_khach}</a>
                      {" "}<span className="dt-nhat">{k.ma_khach}</span></td>
                    <td>{k.nhom.map(n => n.ten ?? n.khoa).join(" · ") || "—"}</td>
                    <td>{k.gia.map(g => `${g.ten_nhom ?? g.nhom_khoa}: ${yen(g.gia_goc)}/${nhanDonVi(g.don_vi_gia)}`).join(" · ") || "—"}</td>
                  </tr>))}</tbody></table>
            </div>) : <p className="dt-nhat">Chưa lần ghi tiếp xúc nào trong 90 ngày gắn thẻ @{hs.ben.ma}.</p>}
        </Khoi>
      </section>
    </>
  );
}

// ---------------------------------------------------------------- thanh lệch quanh vạch KOME

const W = 720, LW = 230, PHAI = 96, RH = 22, TREN = 22, P_MIN = -60, P_MAX = 60;
const xP = (p: number) => LW + (Math.max(P_MIN, Math.min(P_MAX, p)) - P_MIN) / (P_MAX - P_MIN) * (W - LW - PHAI);

function BieuDoLech({ dong, qs, mo }: { dong: DongHs[]; qs: QsHs[]; mo: (q: QsHs, tru_o?: string) => void }) {
  const H = TREN + dong.length * RH + 18, x0 = xP(0);
  return (
    <div className="dt-cuon">
      <svg viewBox={`0 0 ${W} ${H}`} className="dt-svg dt-svg-hs" role="group" aria-label="Giá từng mặt hàng của bên này so với giá KOME">
        {[-50, -25, 25, 50].map(p => (
          <Fragment key={p}>
            <line x1={xP(p)} x2={xP(p)} y1={TREN - 6} y2={H - 16} className="ke" strokeDasharray="2 3" />
            <text x={xP(p)} y={H - 3} fontSize={10} textAnchor="middle" className="t-nhat">{pcDau(p)}</text>
          </Fragment>))}
        <text x={x0} y={H - 3} fontSize={10} textAnchor="middle" className="t-nhat">0%</text>
        <text x={x0} y={11} fontSize={10.5} textAnchor="middle" className="t-kome">= giá KOME</text>
        <text x={xP(-58)} y={11} fontSize={10.5} className="t-do">◀ bên này rẻ hơn</text>
        <text x={xP(58)} y={11} fontSize={10.5} textAnchor="end" className="t-xanh">KOME rẻ hơn ▶</text>
        {dong.map((d, i) => {
          const y = TREN + i * RH, q = d.q, ten = q.ten_nhom ?? q.ten_goc;
          const nhan = `${ten} (${q.ten_goc}): ${d.p == null ? "chưa có giá để so" : `${pcDau(d.p)} so KOME`} — sửa`;
          const dx = d.p == null ? x0 : xP(d.p), trai = d.p != null && d.p < 0;
          // Nhãn % cạnh đầu thanh; thanh trái sát mép (không đủ chỗ trước cột tên) thì nhãn sang nửa phải (trống) của dòng.
          const chatTrai = trai && dx - LW < 58, xn = trai ? (chatTrai ? x0 + 6 : dx - 4) : dx + 4;
          return (
            <g key={`${q.nguon}${q.id}`} opacity={d.cu ? 0.5 : 1}>
              <text x={LW - 8} y={y + 12} fontSize={11} textAnchor="end" className={d.cung ? "" : "t-khac"}>{ngan(ten, 32)}</text>
              {d.p == null
                ? <ONoi svg nhan={nhan} onBam={() => mo(q, d.tro)} noi_dung={<NoiHs d={d} qs={qs} />}>
                    <text x={x0 + 4} y={y + 13} fontSize={12} className="t-cam t-dam">?</text>
                  </ONoi>
                : <ONoi svg nhan={nhan} onBam={() => mo(q)} noi_dung={<NoiHs d={d} qs={qs} />}>
                    <rect className="dt-dich" x={Math.min(x0, dx)} y={y + 3} width={Math.max(2, Math.abs(dx - x0))} height={13} rx={3}
                      fill={d.cung ? "var(--lam-chu)" : "var(--dt-khac)"}
                      stroke={d.het ? "var(--canh-chu)" : undefined} strokeWidth={d.het ? 2 : undefined} />
                  </ONoi>}
              {d.p != null && d.thueKhongRo && (
                <g className="dt-hoi-thue" role="button" tabIndex={0} aria-label={`${ten}: thuế không rõ — sửa`}
                  onClick={() => mo(q, "thue")} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); mo(q, "thue"); } }}>
                  <circle cx={trai ? dx + 7 : dx - 7} cy={y + 9.5} r={5.5} />
                  <text x={trai ? dx + 7 : dx - 7} y={y + 13} fontSize={9} textAnchor="middle">?</text>
                </g>)}
              {d.p != null && (
                <text x={xn} y={y + 13} fontSize={10.5} textAnchor={trai && !chatTrai ? "end" : "start"}>
                  <tspan className={"t-dam t-" + mauLech(d.p)}>{pcDau(d.p)}</tspan>
                  {d.het && <tspan className="t-vang"> hết</tspan>}
                  {d.km && <tspan className="t-km t-dam"> KM</tspan>}
                  {d.gomShip && <tspan> 🚚</tspan>}
                </text>)}
            </g>);
        })}
        <line x1={x0} x2={x0} y1={TREN - 6} y2={H - 16} stroke="var(--do)" strokeWidth={2} pointerEvents="none" />
      </svg>
    </div>
  );
}

/** Ô nổi của một thanh: tên gốc + quy cách, giá như bảng in, ¥ quy đổi, KOME, lệch, cờ, và đường giá theo tháng (≥ 2 tháng). */
function NoiHs({ d, qs }: { d: DongHs; qs: QsHs[] }) {
  const q = d.q, ls = lichSuThang(qs, q), dv = q.don_vi_so === "kg" ? "kg" : nhanDonVi(q.don_vi_so);
  const co = [q.nhan ? NHAN_GHEP[q.nhan] : null, q.trang_thai !== "con" ? NHAN_TRANG_THAI[q.trang_thai] ?? q.trang_thai : null,
    d.km ? `KM${q.khuyen_mai ? ": " + q.khuyen_mai : ""}` : null, d.gomShip ? "gồm ship 🚚" : null,
    d.thueKhongRo ? "thuế không rõ" : null, d.cu ? `giá ${so(q.tuoi_ngay)} ngày tuổi` : null].filter(Boolean);
  return (
    <>
      <div className="o-noi-chu"><b>{q.ten_goc}</b>{[q.quy_cach_goc, q.kenh_gia, q.muc_gia].filter(Boolean).map(t => ` · ${t}`).join("")}</div>
      <div className="o-noi-chu">{q.ten_nhom ?? q.nhom_khoa}</div>
      <DongNoi nhan="Giá như bảng in" gia={q.gia_goc == null ? "?" : `${yen(q.gia_goc)}/${q.don_vi_gia ? nhanDonVi(q.don_vi_gia) : "?"}`} />
      <DongNoi nhan={`Quy đổi ¥/${dv}`} gia={q.yen_chuan == null ? "?" : yen(q.yen_chuan)} />
      <DongNoi nhan={`KOME ¥/${dv}`} gia={yen(q.gia_kome_so)} />
      <DongNoi nhan="So KOME" gia={d.p == null ? "?" : pcDau(d.p)} mau={MAU[mauLech(d.p)]} />
      {co.length > 0 && <div className="o-noi-chu">{co.join(" · ")}</div>}
      {ls.length > 0 && (
        <div className="dt-hs-spark">
          <Spark gia_tri={ls.map(x => x.gia)} mau="var(--lam-chu)" cao={28} />
          <small>{ls.map(x => `${thang_nhan(x.thang)} ${yen(x.gia)}`).join(" → ")}</small>
        </div>)}
      <div className="o-noi-chu">{ngay(q.ngay_nguon)} · bấm để sửa</div>
    </>
  );
}

function ChuGiai() {
  return (
    <div className="dt-chu-giai">
      <span><i className="cg-cung" />{NHAN_GHEP.cung_hang}</span><span><i className="cg-khac" />{NHAN_GHEP.thay_the}</span>
      <span><i className="cg-het" />đang hết</span><span><b className="t-km-cg">KM</b>khuyến mãi</span>
      <span><b className="cg-vang">?</b>thuế</span><span><b className="cg-cam">?</b>thiếu — bấm để điền</span>
      <span className="cg-mo">mờ = cũ</span><span>🚚 gồm ship</span>
    </div>
  );
}
