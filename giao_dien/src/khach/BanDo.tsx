// Tab "Bản đồ" — lưới 47 ô vuông bằng nhau (kome/ban_do.py, migration 025),
// KHÔNG phải bản đồ toạ độ Leaflet của gói thiết kế: công ty chỉ có TÊN tỉnh,
// không có toạ độ khách, và gửi địa chỉ khách ra dịch vụ bản đồ ngoài đang
// tạm dừng. Ô tỉnh chưa có khách VẪN hiện ("0") — bất biến LEFT JOIN.
// Bấm một ô / một dòng: sang tab Danh sách, lọc tỉnh đó, GIỮ người phụ trách.
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { useState } from "react";
import { lay } from "../api";
import { chuoiKhoang, useKhoang, voiKhoang } from "../khung/khoang";
import { gon, so, yen } from "../dinh_dang";
import type { BoLoc, Tab } from "./loc";
import { thamSoBanDo } from "./loc";
import type { BanDoApi, ONhanh } from "./kieu";
import { useDs } from "./DanhSach";

const MAU_O = ["var(--map-0)", "var(--map-1)", "var(--map-2)", "var(--map-3)", "var(--map-4)", "var(--map-5)"];
const MAU_CHU = ["var(--chu-nhat)", "var(--chu)", "var(--chu)", "var(--map-chu-alt)", "var(--map-chu-alt)", "var(--map-chu-alt)"];

export function BanDo({ b, dat }: { b: BoLoc; dat: (s: Partial<BoLoc> & { tab?: Tab }, day?: boolean) => void }) {
  const q = thamSoBanDo(b);
  const kx = chuoiKhoang(useKhoang());
  const { data: d, error, isFetching } = useQuery<BanDoApi>({
    queryKey: ["ban-do", q, kx], queryFn: () => lay<BanDoApi>(voiKhoang(`/api/ban-do${q ? "?" + q : ""}`)),
    placeholderData: keepPreviousData,
  });
  // Tên người phụ trách cho ô chọn — cùng lượt gọi danh sách (đã có trong bộ nhớ đệm nếu vừa xem).
  const { data: ds } = useDs({ ...b, tinh: "", trang: 1 });
  const [tro, datTro] = useState<ONhanh | null>(null);
  if (error) return <div className="khoi-loi">Không tải được bản đồ: {(error as Error).message}</div>;
  if (!d) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  const t = d.t, tien = t.chi_so === "doanh_thu" || t.chi_so === "dt_khoang";
  const f = (v: number) => tien ? yen(v) : so(v);
  const moTinh = (ten: string) => dat({ tab: "danh_sach", tinh: ten }, true);
  const nvDang = b.nv || d.sale || ds?.nv_moi_nguoi || "__moi_nguoi";

  return (
    <div className={"kh-bd" + (isFetching ? " dang-tai" : "")}>
      <p className="phu kh-bd-ghi">Lưới <strong>47 ô vuông bằng nhau</strong> xếp theo vị trí tương đối của từng tỉnh — không phải bản
        đồ theo tỷ lệ thật: mọi tỉnh cùng được nhìn thấy, đọc được số và bấm được, kể cả tỉnh chưa có khách.</p>
      <div className="kh-bd-dk">
        <div className="tab-pill" role="group" aria-label="Tô màu theo">
          {Object.entries(d.chi_so_ds).map(([ma, nhan]) => (
            <button key={ma} type="button" aria-pressed={t.chi_so === ma} onClick={() => dat({ chi_so: ma })}>{nhan}</button>))}
        </div>
        <label className="kh-chon"><span>Phụ trách</span>
          <select value={nvDang} onChange={e => dat({ nv: e.target.value, tat_ca: false })}>
            <option value={ds?.nv_moi_nguoi ?? "__moi_nguoi"}>Mọi nhân viên</option>
            {(ds?.tq.nhan_vien ?? []).map(n => <option key={n.ma} value={n.ma}>{n.ten}</option>)}
            {d.sale && !(ds?.tq.nhan_vien ?? []).some(n => n.ma === d.sale) && <option value={d.sale}>{d.ten_sale ?? d.sale}</option>}
          </select></label>
      </div>

      <div className="kh-bd-luoi">
        <div className="kh-bd-hinh">
          <svg viewBox={`0 0 ${t.rong} ${t.cao}`} role="img" aria-label={`Bản đồ 47 tỉnh, tô theo ${d.chi_so_ds[t.chi_so].toLowerCase()}`}>
            {t.o.map(o => (
              <g key={o.ma_jis} className="kh-bd-o" tabIndex={0} role="link" aria-label={`${o.ten}: ${f(o.gia_tri)} — mở danh sách`}
                onClick={() => moTinh(o.ten)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); moTinh(o.ten); } }}
                onMouseEnter={() => datTro(o)} onMouseLeave={() => datTro(null)} onFocus={() => datTro(o)} onBlur={() => datTro(null)}>
                <rect x={o.x} y={o.y} width={d.o_rong} height={d.o_cao} rx={7} fill={MAU_O[o.bac]} />
                <text x={o.x + d.o_rong / 2} y={o.y + 23} textAnchor="middle" fontSize={12} fill={MAU_CHU[o.bac]}>{o.ten_ngan}</text>
                <text x={o.x + d.o_rong / 2} y={o.y + 41} textAnchor="middle" fontSize={tien ? 10.5 : 13} fontWeight={600}
                  fill={MAU_CHU[o.bac]} className="so">{tien ? gon(o.gia_tri) : so(o.gia_tri)}</text>
              </g>))}
          </svg>
          {tro && <div className="kh-bd-noi" role="status">
            <strong className="ten-jp">{tro.ten}</strong> <span className="phu">{tro.vung}</span>
            <div>Số khách <b>{so(tro.so_khach)}</b></div>
            <div>Doanh thu 12 tháng <b>{yen(tro.doanh_thu)}</b></div>
            <div>Cần gọi lại <b>{so(tro.can_goi)}</b>{tro.ty_le_can_goi != null && <> · {(tro.ty_le_can_goi * 100).toFixed(1).replace(".", ",")}%</>}</div>
            <em>bấm để mở danh sách khách của tỉnh này</em>
          </div>}
        </div>
        <aside className="kh-bd-ben">
          <h3>Chú giải</h3>
          <ul className="kh-bd-cg">
            {t.chu_giai.filter(c => c.bac === 0 || c.so_tinh > 0).map(c => (
              <li key={c.bac}><i style={{ background: MAU_O[c.bac] }} />
                {c.bac === 0 ? `Trống — không có ${d.chi_so_ds[t.chi_so].toLowerCase()}` : `${f(c.tu)} – ${f(c.den)}`}
                <span className="phu"> ({so(c.so_tinh)} tỉnh)</span></li>))}
          </ul>
          <h3>Theo vùng (地方)</h3>
          <ul className="kh-bd-vung">{t.vung.map(v => <li key={v.vung}><span className="ten-jp">{v.vung}</span><b>{f(v.gia_tri)}</b></li>)}</ul>
          <p className="phu">Tổng (47 ô + không rõ tỉnh): <b>{so(t.tong.so_khach)}</b> khách · <b>{yen(t.tong.doanh_thu)}</b> doanh thu 12 tháng ·{" "}
            <b>{so(t.tong.can_goi)}</b> cần gọi lại. Không rõ tỉnh: {so(t.khong_ro_tinh)} khách (chưa có hồ sơ 得意先全情報 khớp tỉnh).</p>
        </aside>
      </div>

      <h3 className="kh-muc-nho">Bảng xếp hạng 47 tỉnh</h3>
      <div className="bang-cuon"><table className="bang">
        <thead><tr><th>Tỉnh</th><th>Vùng</th><th className="so">Số khách</th><th className="so">Doanh thu 12 tháng</th>
          <th className="so">Cần gọi</th><th className="so">Tỷ lệ cần gọi</th></tr></thead>
        <tbody>{t.bang.map(o => (
          <tr key={o.ma_jis}>
            <td><button type="button" className="lien-ket ten-jp" onClick={() => moTinh(o.ten)}>{o.ten}</button></td>
            <td className="ten-jp">{o.vung}</td><td className="so">{so(o.so_khach)}</td><td className="so">{yen(o.doanh_thu)}</td>
            <td className="so">{so(o.can_goi)}</td>
            <td className="so">{o.ty_le_can_goi == null ? "—" : `${(o.ty_le_can_goi * 100).toFixed(1).replace(".", ",")}%`}</td>
          </tr>))}</tbody>
      </table></div>
      <p className="phu">Tỷ lệ cần gọi hiện "—" ở tỉnh chưa có khách — không phải 0%.</p>
    </div>
  );
}
