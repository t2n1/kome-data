// Ô nổi giá của tab So sánh (đặc tả §4.2 "Ô nổi", bản phác tooltip-thung-4.html / ca-trang-8.html): một mặt hàng đối thủ —
// bên, tên, quy cách gốc, nhãn · 3 ô quy cách cạnh số KOME · bảng bậc (bậc áp dụng cho "Khách mua" tô đậm) · dòng KOME ·
// câu nhắc · dòng nguồn. Mọi quyết định (giá tại số lượng, bậc → ¥/kg, đặt tối thiểu) ở so_sanh_logic.ts.
// Bọc bằng chung/ONoi.tsx (`svg`) ở chỗ gọi; ở đây chỉ là NỘI DUNG.
import { ngay, so_luong, yen } from "../dinh_dang";
import { NHAN_GHEP, type Nhom, type QuanSat } from "./kieu";
import { mauLech, NGAY_CU } from "./mau";
import { bangBac, giaKome, giaTai, LUA_CHON_GK, nhanKlGoi, pcDau, phiKome, phiMatHang, type PhiNoi, type PhiSoSanh,
  type SoLuong } from "./so_sanh_logic";

const kgChu = (v: number | null | undefined) => (v == null ? null : `${so_luong(v, 1)} kg`);

function O({ nhan, gia, kome }: { nhan: string; gia: string | null; kome: string | null }) {
  return (
    <div><small>{nhan}</small>{gia == null ? <b className="dt-thieu-o">?</b> : <b>{gia}</b>}<em>KOME {kome ?? "?"}</em></div>
  );
}

/** Dòng "kèm phí giao" (chỉ khi bật "Tính cả phí giao" và áp được). */
function DongPhi({ p }: { p: PhiNoi | null }) {
  if (!p) return null;
  if (p.hoi) return <p className="dt-ng-chu vang">? Phí giao chưa cộng — {p.hoi === "kg" ? "thiếu kg / thùng"
    : p.r?.chua_ro.length ? `chưa rõ ${p.r.chua_ro.join(", ")}` : "chưa có điều kiện giao hàng"}</p>;
  const r = p.r!;
  return (
    <p className="dt-ng-chu">Kèm phí giao (đơn {p.thung} thùng, Kanto, daibiki): <b>{yen(p.gia)}/kg</b> — ship {yen(r.ship)}
      {r.vung ? ` · vùng ${yen(r.vung)}` : ""} · daibiki {yen(r.daibiki)}</p>);
}

/** Nội dung ô nổi của MỘT mặt hàng. */
export function NoiGia({ n, q, sl, gk, phi }: { n: Nhom; q: QuanSat; sl: SoLuong; gk: string; phi?: PhiSoSanh | null }) {
  const gK = giaKome(n, gk);
  const { khongGhiPallet } = giaTai(q, sl);
  const b = bangBac(q, sl, gK);
  const km = !!q.khuyen_mai || q.gia_truoc_km != null;
  const cu = (q.tuoi_ngay ?? 0) > NGAY_CU;
  const klKome = n.kome_kg_goi == null ? null : n.kome_kg_goi * 1000;
  const khacCo = q.kg_thung_dt != null && n.kome_kg_thung != null && Math.abs(q.kg_thung_dt - n.kome_kg_thung) > 0.01;
  const nhanGk = LUA_CHON_GK.find(x => x.ma === gk)?.nhan ?? gk;
  // Bật "Tính cả phí giao": bảng bậc vẫn là giá TRẦN hai phía (so trần với trần); giá kèm phí ở dòng DongPhi bên dưới.
  const pPhi = phiMatHang(n, q, sl, phi);
  return (
    <div className="dt-ng">
      <p className="dt-ng-ben">{q.ten_doi_thu ?? q.ma_doi_thu}</p>
      <p className="dt-ng-ten">{q.ten_goc}{q.quy_cach_goc ? ` · ${q.quy_cach_goc}` : ""}</p>
      <p>
        {q.nhan && <span className={"dt-nh " + (q.nhan === "cung_hang" ? "cung" : "khac")}>{NHAN_GHEP[q.nhan]}</span>}
        {q.trang_thai === "het" && <span className="dt-nh het">đang hết</span>}
        {km && <span className="dt-nh km">khuyến mãi{q.khuyen_mai ? `: ${q.khuyen_mai}` : ""}</span>}
      </p>
      <div className="dt-ng-o3">
        <O nhan="gói / thùng" gia={q.so_goi_thung == null ? null : so_luong(q.so_goi_thung)}
          kome={n.kome_goi_thung == null ? null : so_luong(n.kome_goi_thung)} />
        <O nhan="tịnh 1 gói" gia={nhanKlGoi(q.kl_goi_g)} kome={nhanKlGoi(klKome)} />
        <O nhan="1 thùng" gia={kgChu(q.kg_thung_dt)} kome={kgChu(n.kome_kg_thung)} />
      </div>
      <table>
        <thead><tr><th>Mua</th><th className="r">¥ / gói</th><th className="r">¥ / thùng</th><th className="r">¥ / kg</th>
          <th className="r">{pPhi ? "so KOME (giá trần)" : "so KOME"}</th></tr></thead>
        <tbody>
          {b.dong.map((d, i) => (
            <tr key={i} className={d.dang ? "dang" : undefined}>
              <td>{d.nhan}{d.re ? " ↓" : ""}</td>
              <td className="r">{yen(d.goi)}</td><td className="r">{yen(d.thung)}</td><td className="r">{yen(d.kg)}</td>
              <td className={"r c-" + mauLech(d.p)}>{pcDau(d.p)}</td>
            </tr>))}
          <tr className="kome">
            <td>KOME <small>({nhanGk})</small></td>
            <td className="r">{yen(gK == null || klKome == null ? null : gK * klKome / 1000)}</td>
            <td className="r">{yen(gK == null || n.kome_kg_thung == null ? null : gK * n.kome_kg_thung)}</td>
            <td className="r">{yen(gK)}</td><td />
          </tr>
        </tbody>
      </table>
      {!b.coBac && <p className="dt-ng-chu">Bên này không ghi giá bậc</p>}
      {b.toiThieu && <p className="dt-ng-chu">Đặt tối thiểu: {b.toiThieu}</p>}
      {khacCo && <p className="dt-ng-chu vang">Thùng bên này {kgChu(q.kg_thung_dt)}, thùng KOME {kgChu(n.kome_kg_thung)} — so theo ¥/kg</p>}
      {q.thue === "khong_ro" && <p className="dt-ng-chu vang">? Thuế không rõ: đang tính như CHƯA thuế — nếu đã gồm 8% thì giá thật thấp hơn ~7%</p>}
      {cu && <p className="dt-ng-chu vang">Bảng giá đã {q.tuoi_ngay} ngày</p>}
      {sl === "pallet" && khongGhiPallet && <p className="dt-ng-chu">Bên này không ghi giá pallet — đang dùng giá lẻ</p>}
      {q.gom_ship === "co" && <p className="dt-ng-chu">🚚 Giá đã gồm ship</p>}
      <DongPhi p={pPhi} />
      <p className="dt-ng-chu">
        Giá gốc {q.gia_goc == null ? "?" : `${yen(q.gia_goc)}/${q.don_vi_gia ?? "?"}`}
        {q.gia_bac ? ` · bậc ghi: “${q.gia_bac}”` : ""}{q.kenh_gia ? ` · ${q.kenh_gia}` : ""} · {ngay(q.ngay_nguon)}
      </p>
    </div>
  );
}

/** Ô nổi của dòng KOME (biểu đồ cột): giá đang chọn, thực bán, 標準価格, bảng 売価No. */
export function NoiKome({ n, gk, sl = "1", phi }: { n: Nhom; gk: string; sl?: SoLuong; phi?: PhiSoSanh | null }) {
  const bang = Object.entries(n.gia_kome_bang ?? {}).sort(([a], [b]) => a.localeCompare(b));
  return (
    <div className="dt-ng">
      <p className="dt-ng-ben">KOME · {n.ten_nhom ?? n.nhom_khoa}</p>
      <table><tbody>
        {LUA_CHON_GK.slice(0, 2).map(x => (
          <tr key={x.ma} className={gk === x.ma ? "dang" : undefined}><td>{x.nhan}</td><td className="r">{yen(giaKome(n, x.ma))}</td></tr>))}
        {bang.map(([m, g]) => (
          <tr key={m} className={gk === m ? "dang" : undefined}><td>売価No.{m}{m === "10" ? " · khuyến mãi" : ""}</td><td className="r">{yen(g)}</td></tr>))}
      </tbody></table>
      {gk === "chuan" && n.gia_kome_chuan == null && <p className="dt-ng-chu vang">Chưa có 標準価格 — đang dùng thực bán 90 ngày</p>}
      {gk !== "chuan" && gk !== "thuc" && giaKome(n, gk) == null && <p className="dt-ng-chu vang">Mã này không có 売価No.{gk}</p>}
      <DongPhi p={phiKome(n, gk, sl, phi)} />
    </div>
  );
}
