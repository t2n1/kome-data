// Nội dung 5 tab của hồ sơ 360° — bố cục Customer 360.dc.html. Biểu đồ SVG tự
// vẽ như gói thiết kế (không thư viện). Mọi số từ /api/khach-hang/{mã}.
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { lay } from "../api";
import { BieuDo } from "../chung/BieuDo";
import { ChuaCoDuLieu } from "../chung/Khoi";

import { gon, ngay, pc, so, thay_doi, yen } from "../dinh_dang";
import type { DongBan, HoSoApi, LichMa, MatHang } from "./kieu";
import { GhiTiepXuc } from "./GhiTiepXuc";
import { OCongNo } from "../cong_no/CongNoKhach";
import { chuoiKhoang, useKhoang, voiKhoang, type KhoangMayChu } from "../khung/khoang";

/** Số trong KHOẢNG XEM của một khách (/api/khach-hang/{mã}/khoang — đợt B;
 *  endpoint riêng vì hồ sơ đã chạm trần 8 lượt hỏi). Nhiều khối gọi chung —
 *  TanStack Query gộp thành một lượt. */
type SoSanhKh = { ma: string; nhan: string; co: boolean; tu: string; den: string; dt: number | null;
  dt_ck: number | null; tang_dt: number | null };
type KhoangKhach = {
  khoang: KhoangMayChu; tong: { dt: number; lg: number; so_phieu: number; so_ngay: number; ty_suat: number | null };
  so_sanh: SoSanhKh[];
  mat_hang: { ma: string; ten: string; doanh_thu: number; lai_gop: number; so_luong: number; so_ngay: number; lan_cuoi: string }[];
  ngay: { ngay: string; so_phieu: number; doanh_thu: number }[];
} | null;
function useKhoangKhach(ma: string) {
  const kx = chuoiKhoang(useKhoang());
  return useQuery<KhoangKhach>({
    queryKey: ["kh-khoang", ma, kx],
    queryFn: () => lay<KhoangKhach>(voiKhoang(`/api/khach-hang/${encodeURIComponent(ma)}/khoang`)),
  });
}
const trongKhoang = (k: KhoangMayChu | undefined, thang: string) =>
  !!k && thang >= k.tu.slice(0, 7) && thang <= k.den.slice(0, 7);

/** Khung "chưa có dữ liệu" trong một thẻ (ChuaCoDuLieu trả fragment — không bọc là vỡ lưới). */
function ChuaCo(p: { tieu_de: string; ly_do: string }) {
  return <section className="kh-the kh-chua-co"><ChuaCoDuLieu {...p} /></section>;
}

const MAU_NGANH = ["var(--do)", "var(--ok-vien)", "var(--lien-ket)", "var(--lam-chu)", "var(--duong-ck)",
  "var(--canh-vien)", "var(--map-3)", "var(--chu-mo)"];

function The({ tieu_de, phu, goc, children, className = "" }: { tieu_de: string; phu?: React.ReactNode;
  goc?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={"kh-the " + className}>
      <div className="kh-the-dau"><h2>{tieu_de}</h2>{goc && <span className="kh-the-goc">{goc}</span>}</div>
      {phu && <p className="phu kh-the-phu">{phu}</p>}
      {children}
    </section>);
}

function dsThang(hom_nay: string | null, n = 12): string[] {
  if (!hom_nay) return [];
  let y = +hom_nay.slice(0, 4), m = +hom_nay.slice(5, 7);
  const ra: string[] = [];
  for (let i = 0; i < n; i++) { ra.unshift(`${y}-${String(m).padStart(2, "0")}`); m--; if (!m) { m = 12; y--; } }
  return ra;
}
const cuoiThang = (t: string) => { const [y, m] = t.split("-").map(Number); return `${t}-${String(new Date(y, m, 0).getDate()).padStart(2, "0")}`; };
const tNhan = (t: string) => `${+t.slice(5, 7)}/${t.slice(2, 4)}`;
const tiLe = (a: number | null | undefined, b: number | null | undefined) => (a != null && b) ? a / b - 1 : null;

// ============================================================ Tổng quan
export function TabTongQuan({ h }: { h: HoSoApi }) {
  const k = h.khach, o = h.o_so;
  const ss30 = tiLe(o.dt_30, o.dt_30_truoc);
  const lan_cuoi = h.nhat_ky[0];
  const { data: kh } = useKhoangKhach(k.ma);
  return (<>
    <div className="o-kpi-luoi hs-o">
      <div className="o-kpi"><div className="nhan">DT · {kh?.khoang.nhan ?? "…"}</div>
        <div className="gia">{kh ? gon(kh.tong.dt) : "…"}</div>
        {kh?.so_sanh.map(s => <div key={s.ma} className={"dong-phu " + (!s.co || s.tang_dt == null ? "nhat-chu" : s.tang_dt >= 0 ? "tang" : "giam")}
          title={s.co ? `${ngay(s.tu)} → ${ngay(s.den)}: ${yen(s.dt_ck)}` : undefined}>
          {!s.co ? `${s.nhan}: không có dữ liệu` : s.tang_dt == null ? `${s.nhan}: ${s.dt_ck ? "—" : "chưa mua"}` : `${thay_doi(s.tang_dt, 0)} so ${s.nhan}`}</div>)}</div>
      <div className="o-kpi"><div className="nhan">DT 30 ngày · hôm nay</div><div className="gia">{gon(o.dt_30)}</div>
        <div className={"dong-phu " + (ss30 == null ? "nhat-chu" : ss30 >= 0 ? "tang" : "giam")}>{ss30 == null ? "30 ngày trước chưa mua" : `${thay_doi(ss30, 0)} so 30 ngày trước`}</div></div>
      <div className="o-kpi"><div className="nhan">Chu kỳ mua</div><div className="gia">{k.nhip_ngay == null ? "—" : `${Math.round(k.nhip_ngay)} ngày`}</div>
        <div className="dong-phu nhat-chu">{k.nhip_ngay == null ? "chưa đủ 3 lần mua" : `im ${k.so_ngay_im_lang} ngày · ${(k.ty_le_im_lang ?? 0).toFixed(1).replace(".", ",")}× nhịp`}</div></div>
      <div className="o-kpi"><div className="nhan">Số mã đang lấy</div><div className="gia">{so(o.so_ma_dang_mua)}</div>
        <div className={"dong-phu " + (o.so_ma_ngung ? "giam" : "nhat-chu")}>{o.so_ma_ngung ? `${o.so_ma_ngung} mã đã ngừng` : "không mã nào ngừng"}</div></div>
      <div className="o-kpi"><div className="nhan">Biên lãi gộp giỏ hàng</div><div className="gia">{pc(k.ty_suat)}</div>
        <div className="dong-phu nhat-chu">lãi gộp ÷ doanh thu thuần, luỹ kế</div></div>
      <OCongNo ma={k.ma} />
    </div>

    <div className="hs-hang hai-mot">
      <The tieu_de="Nhịp mua" phu="số ngày im lặng ÷ nhịp mua riêng của khách (trung vị khoảng cách giữa các lần mua)">
        <DongHo ty_le={k.ty_le_im_lang} />
        <p className="phu">{k.ty_le_im_lang == null ? "Chưa đủ 3 lần mua để có nhịp — không đoán." :
          k.ty_le_im_lang < 1 ? "Vẫn trong nhịp mua thường lệ." : k.ty_le_im_lang < 2 ? "Đã quá ngày mua thường lệ — gọi trước khi trễ hẳn." :
          k.ty_le_im_lang < 4 ? "Im lặng 2–4× nhịp: quá hạn mua lại." : "Im lặng ≥ 4× nhịp: đang mất khách."}</p>
      </The>
      <BieuDo12Thang h={h} />
    </div>

    <Tuan26 h={h} />

    <div className="hs-hang hai">
      <GioNganh h={h} />
      <PhanTan h={h} />
    </div>

    <LichMua h={h} />

    <div className="hs-hang ba">
      <The tieu_de="Thẻ khách hàng" phu="thẻ tự động — mỗi thẻ suy ra từ dữ liệu bán thật">
        <div className="hs-the-ds">{h.the.length ? h.the.map(t => (
          <span key={t.chu} className={"nhan-vien " + (t.mau ?? "nhat")} title={t.vi}>{t.chu}</span>))
          : <span className="phu">Không có thẻ nào.</span>}</div>
        <p className="phu">Thẻ tay (nhân viên tự gắn) chưa có nơi lưu.</p>
      </The>
      <ChuaCo tieu_de="Gợi ý tiếp khách" ly_do="Chưa có công thức gợi ý dựa trên dữ liệu thật — không in câu gõ tay." />
      <The tieu_de="Ghi chú" phu="lần tiếp xúc gần nhất (nhật ký chỉ thêm)">
        {lan_cuoi ? <div className="hs-ghi">{lan_cuoi.icon} <b>{ngay(lan_cuoi.ngay)}</b> · <span className={"nhan-vien " + lan_cuoi.mau_ket_qua}>{lan_cuoi.nhan_ket_qua}</span>
          <p>{lan_cuoi.noi_dung}</p>{lan_cuoi.nguoi && <span className="phu">— {lan_cuoi.nguoi}</span>}</div>
          : <p className="phu">Chưa ghi lần tiếp xúc nào — ghi ở tab Hồ sơ & liên hệ.</p>}
      </The>
    </div>
  </>);
}

function DongHo({ ty_le }: { ty_le: number | null }) {
  const r = 54, cx = 66, cy = 70, MAX = 3;
  const v = ty_le == null ? 0 : Math.min(MAX, Math.max(0, ty_le));
  const diem = (x: number) => { const g = Math.PI * (1 - x / MAX); return [cx + r * Math.cos(g), cy - r * Math.sin(g)]; };
  const cung = (a: number, b: number) => { const [x1, y1] = diem(a), [x2, y2] = diem(b); return `M${x1.toFixed(1)},${y1.toFixed(1)} A${r},${r} 0 0 1 ${x2.toFixed(1)},${y2.toFixed(1)}`; };
  const mau = ty_le == null ? "var(--chu-mo)" : v < 1 ? "var(--ok-vien)" : v < 2 ? "var(--lien-ket)" : "var(--do)";
  return (
    <div className="hs-dong-ho">
      <svg viewBox="0 0 132 84" role="img" aria-label={ty_le == null ? "chưa có nhịp" : `${ty_le.toFixed(1)} lần nhịp mua`}>
        <path d={cung(0, MAX)} stroke="var(--nen-phu)" strokeWidth={13} fill="none" strokeLinecap="round" />
        {[1, 2].map(x => { const [a, b] = diem(x); return <circle key={x} cx={a} cy={b} r={2} fill="var(--vien-dam)" />; })}
        {ty_le != null && v > 0.02 && <path d={cung(0, v)} stroke={mau} strokeWidth={13} fill="none" strokeLinecap="round" />}
        <text x={cx} y={cy - 8} textAnchor="middle" fontSize={22} fontWeight={700} fill="var(--chu)">
          {ty_le == null ? "—" : ty_le.toFixed(1).replace(".", ",") + "×"}</text>
        <text x={cx} y={cy + 8} textAnchor="middle" fontSize={9} fill="var(--chu-nhat)">nhịp mua riêng</text>
        <text x={10} y={82} fontSize={8} fill="var(--chu-mo)">0</text><text x={116} y={82} fontSize={8} fill="var(--chu-mo)">≥3×</text>
      </svg>
    </div>);
}

function BieuDo12Thang({ h }: { h: HoSoApi }) {
  const thang = dsThang(h.hom_nay);
  const kx = useKhoangKhach(h.khach.ma).data?.khoang;
  const theo = Object.fromEntries(h.thang.map(t => [t.thang, t]));
  const gt = thang.map(t => theo[t]?.doanh_thu ?? 0);
  const tb = gt.reduce((s, x) => s + x, 0) / (gt.length || 1);
  const [chon, datChon] = useState<string | null>(null);
  const tb3 = h.thang_nay?.dt_tb_3_thang;
  const ss = h.thang_nay ? tiLe(h.thang_nay.dt_thang_nay, h.thang_nay.dt_thang_truoc_den_ngay) : null;
  return (
    <The tieu_de="Doanh thu 12 tháng" className="rong2"
      goc={ss != null ? <span className={ss >= 0 ? "tang" : "giam"}>{thay_doi(ss, 0)} tháng này so tháng trước cùng ngày</span> : null}
      phu={<>cột = tháng{kx ? <> · cột đậm = thuộc {kx.nhan}</> : null} · nét đứt = trung bình 12 tháng · <b>bấm một tháng</b> để xem mặt hàng tháng đó{tb3 != null && <> · TB 3 tháng trước {gon(tb3)}</>}</>}>
      <BieuDo nhan={thang.map(tNhan)} nhan_day_du={thang.map(t => `Tháng ${+t.slice(5)}/${t.slice(0, 4)}`)} cao={170}
        chuoi={[{ ten: "Doanh thu", kieu: "cot", gia_tri: gt, mau: "var(--ok-vien)",
                  mau_tung_cot: gt.map((v, i) => kx && !trongKhoang(kx, thang[i]) ? "color-mix(in srgb, var(--ok-vien) 30%, var(--nen-the))"
                    : i === gt.length - 1 ? "var(--do)" : v >= tb ? "var(--ok-vien)" : "var(--canh-vien)") },
                { ten: "Trung bình 12 tháng", kieu: "duong_dut", gia_tri: gt.map(() => tb), mau: "var(--chu-nhat)" }]}
        dinh_dang={v => v == null ? "—" : v === 0 ? "không mua" : yen(v)} dinh_dang_truc={gon}
        onBam={i => datChon(thang[i])} mo_ta="Doanh thu 12 tháng của khách, bấm một cột để xem mặt hàng" />
      <div className="hs-luoi-thang" role="group" aria-label="12 tháng — tháng không mua để trống">
        {thang.map((t, i) => (
          <button key={t} type="button" className={gt[i] ? "co" : "trong"} aria-pressed={chon === t} onClick={() => datChon(chon === t ? null : t)}
            title={gt[i] ? `${yen(gt[i])} · ${theo[t]?.so_lan ?? 0} lần mua` : "không mua"}>
            <b>{tNhan(t)}</b><span>{gt[i] ? gon(gt[i]) : "không mua"}</span></button>))}
      </div>
      {chon && <MatHangThang ma={h.khach.ma} thang={chon} dong={() => datChon(null)} />}
    </The>);
}

function MatHangThang({ ma, thang, dong }: { ma: string; thang: string; dong: () => void }) {
  const { data, isLoading, error } = useQuery<{ dong: DongBan[] }>({
    queryKey: ["kh-dong", ma, thang],
    queryFn: () => lay(`/api/khach-hang/${encodeURIComponent(ma)}/dong?tu=${thang}-01&den=${cuoiThang(thang)}`),
  });
  const gop = useMemo(() => {
    const g: Record<string, { ma: string; ten: string; quy_cach: Set<string>; so_luong: number; doanh_thu: number; lan: Set<string> }> = {};
    for (const x of data?.dong ?? []) {
      const o = g[x.ma] ??= { ma: x.ma, ten: x.ten, quy_cach: new Set(), so_luong: 0, doanh_thu: 0, lan: new Set() };
      o.quy_cach.add(x.quy_cach); o.so_luong += x.so_luong; o.doanh_thu += x.doanh_thu; o.lan.add(x.ngay);
    }
    return Object.values(g).sort((a, b) => b.doanh_thu - a.doanh_thu);
  }, [data]);
  return (
    <div className="hs-thang-ct">
      <div className="kh-the-dau"><h3>Mặt hàng tháng {+thang.slice(5)}/{thang.slice(0, 4)}</h3>
        <button type="button" className="nut-dong" onClick={dong} aria-label="Đóng">✕</button></div>
      {error ? <div className="khoi-loi">{(error as Error).message}</div> : isLoading ? <div className="khoi-cho"><span /><span /></div> :
        !gop.length ? <p className="phu">Tháng này khách không có phiếu nào.</p> :
        <div className="bang-cuon"><table className="bang">
          <thead><tr><th>Mã</th><th>Tên hàng</th><th>Quy cách</th><th className="so">Số lượng</th><th className="so">Số ngày mua</th><th className="so">Doanh thu</th></tr></thead>
          <tbody>{gop.map(x => (
            <tr key={x.ma}><td><code>{x.ma}</code></td><td className="ten-jp"><a href={`/san-pham/${encodeURIComponent(x.ma)}`}>{x.ten}</a></td>
              <td className="phu">{[...x.quy_cach].join(", ")}</td><td className="so">{so(x.so_luong)}</td>
              <td className="so">{x.lan.size}</td><td className="so">{yen(x.doanh_thu)}</td></tr>))}</tbody>
        </table></div>}
    </div>);
}

function Tuan26({ h }: { h: HoSoApi }) {
  const co = h.tuan.filter(t => t.so_ngay > 0).length;
  const mx = Math.max(1, ...h.tuan.map(t => t.doanh_thu));
  const mau = co >= 16 ? "tang" : co >= 9 ? "canh-chu" : "giam";
  return (
    <The tieu_de="Nhịp đặt hàng 26 tuần" goc={<span className={mau}>{co}/26 tuần có đơn{h.khach.nhip_ngay ? ` · nhịp ${Math.round(h.khach.nhip_ngay)} ngày` : ""}</span>}
      phu="ô đậm = tuần có đơn lớn · ô trắng = tuần không đặt · tuần tính lùi từ ngày dữ liệu mới nhất">
      <div className="hs-26">{h.tuan.map(t => (
        <i key={t.den} className={t.so_ngay ? "co" : ""} style={t.so_ngay ? { opacity: 0.22 + Math.max(0, t.doanh_thu) / mx * 0.78 } : undefined}
          title={`${ngay(t.tu)} – ${ngay(t.den)}: ${t.so_ngay ? `${t.so_ngay} ngày có đơn · ${yen(t.doanh_thu)}` : "không đặt"}`} />))}</div>
      <div className="hs-26-truc phu"><span>26 tuần trước</span><span>Tuần này</span></div>
    </The>);
}

function GioNganh({ h }: { h: HoSoApi }) {
  const ds = h.nganh.nganh, r = 40, C = 2 * Math.PI * r;
  let luy = 0;
  return (
    <The tieu_de="Giỏ hàng theo ngành" phu="tỷ trọng doanh thu luỹ kế theo ngành hàng (food_category của OBC)">
      {!ds.length ? <p className="phu">Chưa có doanh thu dương để vẽ.</p> :
      <div className="hs-donut">
        <svg viewBox="0 0 108 108" role="img" aria-label="Tỷ trọng doanh thu theo ngành">
          <circle cx={54} cy={54} r={r} fill="none" stroke="var(--nen-phu)" strokeWidth={17} />
          {ds.map((x, i) => { const dai = x.ty_trong * C; const el = <circle key={x.nganh} cx={54} cy={54} r={r} fill="none"
            stroke={MAU_NGANH[i % MAU_NGANH.length]} strokeWidth={17} strokeDasharray={`${dai} ${C - dai}`} strokeDashoffset={-luy}
            transform="rotate(-90 54 54)"><title>{x.nganh}: {pc(x.ty_trong)}</title></circle>; luy += dai; return el; })}
          <text x={54} y={52} textAnchor="middle" fontSize={17} fontWeight={700} fill="var(--chu)">{ds.length}</text>
          <text x={54} y={66} textAnchor="middle" fontSize={8.5} fill="var(--chu-nhat)">ngành hàng</text>
        </svg>
        <ul className="hs-chu-giai">{ds.map((x, i) => (
          <li key={x.nganh}><i style={{ background: MAU_NGANH[i % MAU_NGANH.length] }} /><span className="ten-jp">{x.nganh}</span><b>{pc(x.ty_trong, 0)}</b></li>))}</ul>
      </div>}
      {h.nganh.so_nganh_khong_ve > 0 && <p className="phu">Không vẽ: {yen(h.nganh.khong_ve)} của {h.nganh.so_nganh_khong_ve} ngành doanh thu ≤ 0 (phiếu đỏ).</p>}
    </The>);
}

function PhanTan({ h }: { h: HoSoApi }) {
  const ds = h.nganh.nganh.filter(x => x.bien != null);
  const W = 320, H = 176, L = 34, B = 22;
  const mxX = Math.max(1, ...ds.map(x => x.doanh_thu));
  const b = ds.map(x => x.bien!), mn = Math.min(0, ...b), mx = Math.max(0.05, ...b);
  const X = (v: number) => L + Math.sqrt(v / mxX) * (W - L - 12);
  const Y = (v: number) => H - B - (v - mn) / ((mx - mn) || 1) * (H - B - 12);
  const vach = [mn, (mn + mx) / 2, mx];
  return (
    <The tieu_de="Doanh thu × biên lãi gộp" phu="mỗi chấm một ngành · phải = doanh thu lớn (thang căn bậc hai) · trên = biên cao · ngành phải-trên là ngành đáng đẩy">
      {!ds.length ? <p className="phu">Chưa có ngành nào có doanh thu dương.</p> :
      <svg viewBox={`0 0 ${W} ${H}`} className="hs-phan-tan" role="img" aria-label="Doanh thu và biên lãi gộp theo ngành">
        {vach.map(v => <g key={v}><line x1={L} x2={W - 6} y1={Y(v)} y2={Y(v)} className="bd-luoi" />
          <text x={L - 4} y={Y(v) + 3} textAnchor="end" className="bd-truc">{pc(v, 0)}</text></g>)}
        {ds.map((x, i) => <circle key={x.nganh} cx={X(x.doanh_thu)} cy={Y(x.bien!)} r={4 + Math.sqrt(x.ty_trong) * 12}
          fill={MAU_NGANH[i % MAU_NGANH.length]} opacity={0.78}><title>{x.nganh}: {yen(x.doanh_thu)} · biên {pc(x.bien)}</title></circle>)}
        <text x={W - 6} y={H - 6} textAnchor="end" className="bd-truc">doanh thu →</text>
      </svg>}
      <ul className="hs-chu-giai ngang">{ds.map((x, i) => (
        <li key={x.nganh}><i style={{ background: MAU_NGANH[i % MAU_NGANH.length] }} /><span className="ten-jp">{x.nganh}</span> <span className="phu">biên {pc(x.bien, 0)}</span></li>))}</ul>
    </The>);
}

function LichMua({ h }: { h: HoSoApi }) {
  const N = 45, ds = h.lich.ma;
  const mau = h.lich.so_tre >= 4 ? "giam" : h.lich.so_tre > 0 ? "canh-chu" : "tang";
  return (
    <The tieu_de="Lịch mua dự kiến từng mã" goc={<span className={mau}>{h.lich.so_tre}/{h.lich.tong} mã đã quá ngày mua lại</span>}
      phu="ngày dự kiến = lần mua cuối + nhịp mua riêng của cặp khách–mã · 10 mã gần ngày nhất · mã đã ngừng mua ở tab Sản phẩm">
      {!ds.length ? <p className="phu">Chưa mã nào đủ 3 lần mua để có nhịp riêng.</p> : <>
      <div className="hs-lich">{ds.map(x => {
        const w = Math.min(1, Math.abs(x.con) / N) * 50;
        return (
          <div key={x.ma} className="hs-lich-dong" title={`dự kiến ${ngay(x.du_kien)} · nhịp ${x.nhip ? Math.round(x.nhip) : "—"} ngày · mua cuối ${ngay(x.lan_cuoi)}`}>
            <span className="ten-jp hs-lich-ten">{x.ten}</span>
            <span className="hs-lich-truc"><i className="giua" />
              <i className={x.con < 0 ? (x.con < -14 ? "do" : "canh") : "ok"} style={{ width: `${w}%`, [x.con < 0 ? "right" : "left"]: "50%" } as React.CSSProperties} /></span>
            <b className={x.con < 0 ? "giam" : "tang"}>{x.con > 0 ? "+" : ""}{x.con}n</b>
          </div>);
      })}</div>
      <div className="hs-lich-truc-chu phu"><span>quá hạn {N} ngày</span><span>hôm nay</span><span>còn {N} ngày</span></div></>}
    </The>);
}

// ============================================================ Sản phẩm
function badgeDeXuat(l: LichMa | undefined) {
  if (!l) return <span className="nhan-vien nhat">△ Chưa đủ nhịp</span>;
  if (l.con <= 0) return <span className="nhan-vien ok">◎ Đề xuất</span>;
  if (l.con <= 7) return <span className="nhan-vien canh">○ Sắp tới</span>;
  return <span className="nhan-vien nhat">△ Còn sớm</span>;
}

export function TabSanPham({ h }: { h: HoSoApi }) {
  const lich = Object.fromEntries(h.lich.ma.map(x => [x.ma, x]));
  const mhTheoMa = Object.fromEntries(h.mat_hang.map(x => [x.ma, x]));
  const top = h.mat_hang.filter(m => m.trang_thai_cap !== "ngung").slice(0, 10);
  const mx = Math.max(1, ...top.map(m => m.doanh_thu));
  const thang = dsThang(h.hom_nay, 3);
  const [tatCa, datTatCa] = useState(false);
  const { data: kh } = useKhoangKhach(h.khach.ma);
  // Lịch đầy đủ (không chỉ 10 mã của tab Tổng quan) cho nhãn đề xuất.
  const lichDu = useMemo(() => {
    if (!h.hom_nay) return lich;
    const moc = new Date(h.hom_nay).getTime();
    return Object.fromEntries(h.mat_hang.filter(m => m.du_kien && m.trang_thai_cap === "mua").map(m =>
      [m.ma, { ma: m.ma, ten: m.ten, du_kien: m.du_kien!, con: Math.round((new Date(m.du_kien!).getTime() - moc) / 864e5),
               nhip: m.nhip, lan_cuoi: m.lan_cuoi, doanh_thu: m.doanh_thu, tb_moi_lan: null }]));
  }, [h]); // eslint-disable-line react-hooks/exhaustive-deps
  return (<>
    {kh && <The tieu_de={`Mặt hàng mua · ${kh.khoang.nhan}`} phu={`${kh.mat_hang.length} mã · ${yen(kh.tong.dt)} · ${kh.tong.so_ngay} ngày có mua (${ngay(kh.khoang.tu)} → ${ngay(kh.khoang.den)})`}>
      {!kh.mat_hang.length ? <p className="phu">Không mua mã nào trong khoảng này.</p> :
      <div className="bang-cuon" style={{ maxHeight: 320 }}><table className="bang"><thead><tr><th>Mặt hàng</th><th className="so">Doanh thu</th>
        <th className="so">Lãi gộp</th><th className="so">Số lượng</th><th className="so">Số ngày mua</th><th className="so">Mua cuối</th></tr></thead>
        <tbody>{kh.mat_hang.map(m => (
          <tr key={m.ma}><td className="ten-jp"><a href={`/san-pham/${encodeURIComponent(m.ma)}`}>{m.ten}</a><div className="ma-nho"><code>{m.ma}</code></div></td>
            <td className="so">{yen(m.doanh_thu)}</td><td className="so">{yen(m.lai_gop)}</td><td className="so">{so(m.so_luong)}</td>
            <td className="so">{so(m.so_ngay)}</td><td className="so">{ngay(m.lan_cuoi)}</td></tr>))}</tbody></table></div>}
    </The>}
    <The tieu_de="Top 10 sản phẩm hay mua" phu={<>xếp theo doanh thu luỹ kế · <span className="nhan-vien ok">◎ Đề xuất</span> đã tới ngày mua lại ·{" "}
      <span className="nhan-vien canh">○ Sắp tới</span> ≤ 7 ngày · <span className="nhan-vien nhat">△ Còn sớm</span></>}>
      <div className="hs-top">{top.map((m, i) => (
        <div key={m.ma} className="hs-top-dong">
          <span className="hs-top-so">{i + 1}</span>
          <span><a className="ten-jp" href={`/san-pham/${encodeURIComponent(m.ma)}`}>{m.ten}</a><div className="ma-nho"><code>{m.ma}</code> · {m.nganh}</div></span>
          <span><span className="kh-td-thanh"><i style={{ width: `${Math.max(0, m.doanh_thu) / mx * 100}%` }} /></span>
            <span className="ma-nho">{yen(m.doanh_thu)} · {so(m.so_lan)} lần · nhịp {m.nhip ? Math.round(m.nhip) + " ngày" : "—"} · cuối {ngay(m.lan_cuoi)}</span></span>
          <span className="hs-top-nhan">{badgeDeXuat(lichDu[m.ma])}</span>
        </div>))}
        {!top.length && <p className="phu">Chưa có mặt hàng nào.</p>}</div>
    </The>

    <div className="hs-hang hai">
      <The tieu_de="Sản phẩm đã ngừng mua" phu="từng mua đều (≥ 3 lần) nhưng im lặng ≥ 2× nhịp riêng của cặp khách–mã">
        {!h.da_ngung_mua.length ? <p className="phu">Không có sản phẩm nào bị bỏ quên.</p> :
        <div className="bang-cuon"><table className="bang"><thead><tr><th>Mặt hàng</th><th className="so">Trễ</th><th className="so">Nhịp</th><th className="so">Mua cuối</th><th className="so">Doanh thu</th></tr></thead>
          <tbody>{h.da_ngung_mua.map(m => (
            <tr key={m.ma}><td className="ten-jp"><a href={`/san-pham/${encodeURIComponent(m.ma)}`}>{m.ten}</a><div className="ma-nho"><code>{m.ma}</code></div></td>
              <td className="so giam">{m.tre != null ? `${m.tre} ngày` : "—"}</td><td className="so">{m.nhip ? Math.round(m.nhip) + " ngày" : "—"}</td>
              <td className="so">{ngay(m.lan_cuoi)}</td><td className="so">{yen(m.doanh_thu)}</td></tr>))}</tbody></table></div>}
      </The>
      <The tieu_de="Tháng này chưa mua" phu="đã quá ngày mua lại theo nhịp của mã nhưng chưa tới mức 'ngừng' — một cuộc gọi nhắc là đủ">
        {!h.chua_mua_thang.length ? <p className="phu">Không có mã nào đang trễ.</p> :
        <div className="bang-cuon"><table className="bang"><thead><tr><th>Mặt hàng</th>{thang.map((t, i) =>
          <th key={t} className="so">Tháng {+t.slice(5)}{i === 2 ? " (đến nay)" : ""}</th>)}</tr></thead>
          <tbody>{h.chua_mua_thang.map(c => { const m = mhTheoMa[c.ma]; return (
            <tr key={c.ma}><td className="ten-jp"><a href={`/san-pham/${encodeURIComponent(c.ma)}`}>{c.ten}</a>
              <div className="ma-nho"><code>{c.ma}</code> · trễ {c.tre ?? "—"} ngày</div></td>
              <td className="so">{m ? gon(m.t2) : "—"}</td><td className="so">{m ? gon(m.t1) : "—"}</td>
              <td className={"so " + (m && !m.t0 ? "giam" : "")}><b>{m ? (m.t0 ? gon(m.t0) : "0") : "—"}</b></td></tr>); })}</tbody></table></div>}
      </The>
    </div>

    <div className="hs-hang hai">
      <The tieu_de="Gợi ý hàng chưa từng mua" phu="mã khách chưa mua bao giờ, xếp theo tỷ suất lãi gộp (tỷ số của các tổng — toàn công ty)">
        {!h.goi_y.length ? <p className="phu">Không có gợi ý.</p> :
        <div className="bang-cuon"><table className="bang"><thead><tr><th>#</th><th>Mặt hàng</th><th className="so">Tỷ suất lãi gộp</th></tr></thead>
          <tbody>{h.goi_y.map((g, i) => (
            <tr key={g.ma}><td className="nhat-chu">{i + 1}</td><td className="ten-jp"><a href={`/san-pham/${encodeURIComponent(g.ma)}`}>{g.ten}</a>
              <div className="ma-nho"><code>{g.ma}</code></div></td><td className="so">{pc(g.ty_suat)}</td></tr>))}</tbody></table></div>}
        <p className="phu">Giá để báo cho khách: xem bảng giá của bậc bên cạnh (tách lẻ / thùng).</p>
      </The>
      <The tieu_de={`Bảng giá của bậc ${h.ho_so.bac_gia ?? "—"} (売価No.)`} phu="giá niêm yết mới nhất của bậc giá khách đang hưởng, tách theo quy cách · giá riêng & chiết khấu theo khách: chưa có nguồn">
        {!h.bac_gia.length ? <p className="phu">Khách chưa có bậc giá hoặc bậc chưa có dòng giá.</p> :
        <div className="bang-cuon"><table className="bang"><thead><tr><th>Mặt hàng</th><th>Quy cách</th><th className="so">Giá (chưa thuế)</th><th className="so">Từ ngày</th></tr></thead>
          <tbody>{h.bac_gia.map(g => (
            <tr key={g.ma + g.quy_cach}><td className="ten-jp">{g.ten}<div className="ma-nho"><code>{g.ma}</code></div></td>
              <td className="phu">{g.quy_cach}</td><td className="so">{yen(g.gia)}</td><td className="so">{ngay(g.tu_ngay)}</td></tr>))}</tbody></table></div>}
      </The>
    </div>

    <The tieu_de={`Tất cả mặt hàng (${h.mat_hang.length})`} phu="mọi mã khách từng mua · 3 cột tháng gần nhất để thấy ngay tháng nào vắng"
      goc={<button type="button" className="nut-nho" onClick={() => datTatCa(x => !x)}>{tatCa ? "Thu gọn" : "Hiện bảng"}</button>}>
      {tatCa && <BangMatHang ds={h.mat_hang} thang={thang} />}
    </The>
  </>);
}

function BangMatHang({ ds, thang }: { ds: MatHang[]; thang: string[] }) {
  const NHAN: Record<string, [string, string]> = { mua: ["đang mua", "ok"], ngung: ["đã ngừng", "do"], khong_goi: ["khách ngừng GD", "nhat"] };
  return (
    <div className="bang-cuon" style={{ maxHeight: 460 }}><table className="bang">
      <thead><tr><th>Mặt hàng</th><th>Ngành</th>{thang.map(t => <th key={t} className="so">T{+t.slice(5)}</th>)}
        <th className="so">Luỹ kế</th><th className="so">Lần</th><th className="so">Nhịp</th><th>Trạng thái</th></tr></thead>
      <tbody>{ds.map(m => (
        <tr key={m.ma}><td className="ten-jp"><a href={`/san-pham/${encodeURIComponent(m.ma)}`}>{m.ten}</a><div className="ma-nho"><code>{m.ma}</code></div></td>
          <td className="phu ten-jp">{m.nganh}</td>
          {[m.t2, m.t1, m.t0].map((v, i) => <td key={i} className={"so" + (v ? "" : " nhat-chu")}>{v ? gon(v) : "·"}</td>)}
          <td className="so">{gon(m.doanh_thu)}</td><td className="so">{so(m.so_lan)}</td>
          <td className="so">{m.nhip ? Math.round(m.nhip) + "n" : "—"}</td>
          <td><span className={"nhan-vien " + (NHAN[m.trang_thai_cap]?.[1] ?? "nhat")}>{NHAN[m.trang_thai_cap]?.[0] ?? m.trang_thai_cap}</span></td></tr>))}</tbody>
    </table></div>);
}

// ============================================================ Đơn hàng
export function TabDonHang({ h }: { h: HoSoApi }) {
  const { data: kh } = useKhoangKhach(h.khach.ma);
  // Khoảng xem (đợt B): dòng thời gian = các ngày mua TRONG khoảng; chưa tải
  // xong thì 12 ngày mua gần nhất như trước.
  const ds = kh ? kh.ngay : h.lan_mua_gan_day;
  const [mo, datMo] = useState<string | null>(null);
  return (
    <div className="hs-hang hai-mot">
      <The tieu_de={kh ? `Đơn hàng · ${kh.khoang.nhan}` : "Dòng thời gian đơn hàng"}
        phu={kh ? `${ds.length} ngày có mua (${ngay(kh.khoang.tu)} → ${ngay(kh.khoang.den)}) · bấm một mốc để xem các dòng hàng` : "12 ngày mua gần nhất · bấm một mốc để xem các dòng hàng"}>
        {!ds.length ? <p className="phu">{kh ? "Không có đơn hàng nào trong khoảng này." : "Chưa có đơn hàng nào trong kỳ dữ liệu."}</p> :
        <ol className="hs-dong-tg">{ds.map((l, i) => (
          <li key={l.ngay} className={i === 0 ? "moi" : ""}>
            <button type="button" className="hs-dtg-dau" aria-expanded={mo === l.ngay} onClick={() => datMo(mo === l.ngay ? null : l.ngay)}>
              <b>{ngay(l.ngay)}</b><span className="phu">{l.so_phieu} phiếu · {yen(l.doanh_thu)}</span></button>
            {mo === l.ngay && <DongNgay ma={h.khach.ma} ngay_={l.ngay} />}
          </li>))}</ol>}
      </The>
      <The tieu_de="Dự báo đơn kế tiếp" phu={`mã sắp tới (hoặc đã qua) ngày mua lại dự kiến trong 14 ngày · theo nhịp riêng từng mã — không % "độ tin cậy" vì không đo được`}>
        {!h.du_bao.length ? <p className="phu">Chưa đủ lịch sử mua đều để dự báo — các mã của khách này chưa có nhịp rõ ràng hoặc ngày dự kiến còn xa hơn 14 ngày.</p> : <>
        <div className="bang-cuon"><table className="bang"><thead><tr><th>Mặt hàng</th><th className="so">Ngày dự kiến</th><th className="so">TB mỗi lần</th></tr></thead>
          <tbody>{h.du_bao.map(x => (
            <tr key={x.ma}><td className="ten-jp">{x.ten}<div className="ma-nho"><code>{x.ma}</code> · nhịp {x.nhip ? Math.round(x.nhip) : "—"} ngày</div></td>
              <td className={"so " + (x.con < 0 ? "giam" : x.con <= 7 ? "canh-chu" : "")}>{ngay(x.du_kien)}<div className="ma-nho">{x.con < 0 ? `quá ${-x.con} ngày` : x.con === 0 ? "hôm nay" : `còn ${x.con} ngày`}</div></td>
              <td className="so">{x.tb_moi_lan == null ? "—" : so(x.tb_moi_lan)}</td></tr>))}</tbody></table></div>
        <button type="button" className="nut-chinh" disabled title="Chưa có hệ thống lên đơn — màn 'Lên đơn hàng' chưa có.">Tạo đơn nháp</button></>}
      </The>
    </div>);
}

function DongNgay({ ma, ngay_ }: { ma: string; ngay_: string }) {
  const { data, isLoading } = useQuery<{ dong: DongBan[] }>({
    queryKey: ["kh-dong-ngay", ma, ngay_], queryFn: () => lay(`/api/khach-hang/${encodeURIComponent(ma)}/dong?tu=${ngay_}&den=${ngay_}`),
  });
  if (isLoading) return <div className="khoi-cho"><span /></div>;
  return <ul className="hs-dtg-dong">{(data?.dong ?? []).map(x => (
    <li key={x.ma + x.quy_cach}><span className="ten-jp">{x.ten}</span><span className="phu">{so(x.so_luong)} · {x.quy_cach}</span><b>{yen(x.doanh_thu)}</b></li>))}</ul>;
}

// ============================================================ Công nợ
// Đợt 6: cong_no/CongNoKhach.tsx (/api/cong-no/khach/{mã}).
export { TabCongNo } from "../cong_no/CongNoKhach";

// ============================================================ Hồ sơ & liên hệ
const NHAN_HO_SO: [string, string][] = [["chi_nhanh", "Chi nhánh"], ["buu_chinh", "Bưu chính"], ["dia_chi", "Địa chỉ"],
  ["phan_loai", "Mã phân loại (OBC)"], ["ngay_chot", "Mã ngày chốt công nợ"], ["bac_gia", "Bậc giá (売価No.)"],
  ["vang_lai", "Khách vãng lai"], ["lan_dau", "Mua lần đầu"], ["so_lan_mua", "Số ngày có mua"], ["so_phieu", "Số phiếu"],
  ["gia_tri_tb", "Giá trị TB mỗi lần"]];

export function TabHoSo({ h }: { h: HoSoApi }) {
  const k = h.khach, hs = h.ho_so;
  const hien = (m: string, v: unknown) => v == null || v === "" ? <span className="nhat-chu">—</span>
    : m === "lan_dau" ? ngay(String(v)) : m === "gia_tri_tb" ? yen(Number(v)) : m === "so_lan_mua" || m === "so_phieu" ? so(Number(v)) : String(v);
  return (<>
    <div className="hs-hang hai">
      <The tieu_de="Thông tin khách hàng" phu="từ 得意先全情報 của OBC — sửa trong OBC rồi xuất lại">
        <dl className="hs-dl">
          <dt>Điện thoại</dt><dd>{k.dien_thoai ? <a href={`tel:${k.dien_thoai}`}>{k.dien_thoai}</a> : "—"}</dd>
          <dt>Tỉnh / thành phố</dt><dd className="ten-jp">{[k.tinh, k.thanh_pho].filter(Boolean).join(" ") || "—"}</dd>
          {NHAN_HO_SO.map(([m, nhan]) => <div key={m} className="hs-dl-dong"><dt>{nhan}</dt><dd className={m === "dia_chi" ? "ten-jp" : ""}>{hien(m, hs[m])}</dd></div>)}
        </dl>
      </The>
      <The tieu_de="Thông tin giao hàng 直送先" phu="điểm giao thẳng của khách · khung giờ nhận, ghi chú tài xế: chưa có nguồn">
        {!h.diem_giao.length ? <p className="phu">Khách không có điểm giao thẳng — giao về địa chỉ khách.</p> :
        <ul className="hs-diem-giao">{h.diem_giao.map(g => <li key={g.ma}><b className="ten-jp">{g.ten}</b> <code className="ma-nho">{g.ma}</code>
          <div className="ten-jp phu">{g.dia_chi || "—"}</div></li>)}</ul>}
      </The>
    </div>
    <NhatKy h={h} />
    <div className="hs-hang hai">
      <ChuaCo tieu_de="Hình ảnh cửa hàng" ly_do="Chưa có nơi lưu ảnh theo khách." />
      <ChuaCo tieu_de="Chat Facebook" ly_do="Chưa tích hợp Messenger — không có nguồn tin nhắn." />
    </div>
  </>);
}

function NhatKy({ h }: { h: HoSoApi }) {
  return (
    <The tieu_de="Nhật ký tiếp xúc" phu="gọi, ghé thăm và chat đã ghi nhận · chỉ thêm, không sửa / xoá — ghi sai thì ghi thêm một dòng đính chính">
      <GhiTiepXuc ma={h.khach.ma} kieu_tx={h.kieu_tx} ket_qua_tx={h.ket_qua_tx} id="ghi-tx" lam_moi={[["kh-ho-so", h.khach.ma]]} />
      <ul className="hs-nk">{h.nhat_ky.map((n, i) => (
        <li key={n.thoi_diem + i}><div className="hs-nk-dau">{n.icon} <b>{n.nhan_kieu}</b> · {ngay(n.ngay)}
          <span className={"nhan-vien " + n.mau_ket_qua}>{n.nhan_ket_qua}</span>{n.hen_lai && <span className="phu"> · hẹn {ngay(n.hen_lai)}</span>}</div>
          <p>{n.noi_dung}</p>{n.nguoi && <span className="phu">— {n.nguoi}</span>}</li>))}
        {!h.nhat_ky.length && <li className="phu">Chưa ghi lần tiếp xúc nào.</li>}</ul>
    </The>);
}
