// Tab "So sánh giá" (đợt 4b task 6; đặc tả §4.2, bản phác ca-trang-8.html): cột trái chọn tối đa 8 nhóm · thanh điều
// khiển (Khách mua · Cách vẽ · Chỉ cùng thương hiệu · Giá KOME — tất cả trên URL qua url.ts ở ManDoiThu) · dòng đếm ô
// trống · A Cột (BieuDoCot) / B Chấm (BieuDoCham) / C Bảng nhiệt (BangNhiet) · bấm → SuaMatHang. Mọi luật ở
// so_sanh_logic.ts; ở đây chỉ nối. "Tính cả phí giao" (?phi=1, đặc tả §5.5): điều kiện từ /giao-hang (useGiaoHang — chung
// khoá với tab Phí & giao hàng), cộng phí ở so_sanh_logic.ts::giaCoPhi; "?" phí mở SuaGiaoHang / quy cách.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { lay } from "../api";
import { HinhMa } from "../chung/HinhMa";
import { Khoi } from "../chung/Khoi";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import { BangNhiet, ChuGiaiNhiet } from "./BangNhiet";
import { BieuDoCham, ChuGiaiCham } from "./BieuDoCham";
import { BieuDoCot, ChuGiaiCot, type MoPhi, type MoSua } from "./BieuDoCot";
import { phiSoSanh } from "./giao_hang_logic";
import { giaoTrong } from "./ho_so_logic";
import type { GiaoHang, Nhom } from "./kieu";
import { dongMoSan } from "./loc";
import { mauKomeSoTT } from "./mau";
import { tenNganh } from "./nganh";
import { batTat, demThieu, khoaNhom, LUA_CHON_GK, locDanhSach, macDinhSp, NHAN_SL, nhomChon, pcDau, soMatHang,
  type NutNhanh, type SoLuong } from "./so_sanh_logic";
import { SuaMatHang } from "./SuaMatHang";
import { SuaGiaoHang } from "./SuaNho";
import { SuaQuyCach } from "./TabGiaKomeLech";
import { useGiaoHang } from "./TabGiaoHang";
import { TOI_DA_SP, type TrangThaiUrl } from "./url";

type Url = Pick<TrangThaiUrl, "sp" | "sl" | "xem" | "gk" | "cung" | "nganh" | "ben" | "phi">;
type Props = Url & { nhom: string; dat: (moi: Partial<Url & { nhom: string }>) => void };

const NHANH: [NutNhanh, string][] = [["", "Tất cả"], ["dat", "KOME đắt nhất"], ["het", "Đối thủ đang hết"], ["thieu", "Còn ô trống"]];
const XEM: [TrangThaiUrl["xem"], string][] = [["cot", "A · Cột"], ["cham", "B · Chấm"], ["nhiet", "C · Bảng nhiệt"]];
const SL: SoLuong[] = ["1", "5", "10", "pallet"];
const CACH_TINH = <>
  Giá quy về ¥/kg chưa thuế (÷ 1,08 khi bảng giá ghi đã gồm thuế; thuế không rõ tính như chưa thuế). "Khách mua" lấy bậc
  giá rẻ nhất bên đó ghi cho số lượng ấy; bên không ghi giá pallet thì dùng giá lẻ. % = giá đối thủ so với giá KOME đang
  chọn: đỏ = đối thủ rẻ hơn KOME quá 5%, xanh = KOME rẻ hơn quá 5%, xám = ngang. "KOME ±x%" ở cột trái = 標準価格 so với
  trung vị giá lẻ của đối thủ — không đổi theo "Khách mua". Thu gọn: KOME + 5 mặt hàng rẻ nhất + mọi mặt hàng cùng
  thương hiệu. Giá khách kể không vẽ ở đây. "Tính cả phí giao": mỗi giá (KOME và đối thủ) cộng phí ship + daibiki của
  MỘT đơn đúng số thùng đang chọn giao tới Kanto, trả daibiki, chia cho kg của đơn (bao ship thì không cộng ship); % so với
  KOME đã cộng phí. Bên chưa ghi đủ điều kiện, hoặc thiếu kg / thùng, mang dấu "?" và không cộng. Không áp cho pallet và
  nhóm không so theo kg; dải bảng giá / vạch thực bán / KM của KOME không vẽ khi bật.</>;

/** Phần "?" đầu tiên của phí → ô mở sẵn của SuaGiaoHang (daibiki: đã có phí thường thì thiếu là phí sau ngưỡng). */
const truOPhi = (g: GiaoHang | undefined, phan: string | undefined) =>
  phan === "ship" ? "phi_ship" : phan === "vùng" ? "phu_phi" : phan === "daibiki" ? (g?.phi_daibiki != null ? "daibiki_sau" : "phi_daibiki") : undefined;

export function TabSoSanh({ sp, sl, xem, gk, cung, nganh, ben, phi, nhom, dat }: Props) {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "so-sanh", kx],
    queryFn: () => lay<{ nhom: Nhom[] }>(`/api/doi-thu/so-sanh${kx ? "?" + kx : ""}`) });
  const tatCa = q.data?.nhom;
  const [tim, datTim] = useState("");
  const [nhanh, datNhanh] = useState<NutNhanh>("");
  const [sua, datSua] = useState<{ nguon: "nap" | "tay"; id: number; tru_o?: string } | null>(null);
  const gh = useGiaoHang(phi);
  const ps = useMemo(() => (phi && gh.data ? phiSoSanh(gh.data.dong) : null), [phi, gh.data]);
  const [suaGiao, datSuaGiao] = useState<{ g: GiaoHang; tru_o?: string } | null>(null);
  const [suaQc, datSuaQc] = useState<Nhom | null>(null);
  const [toiDa, datToiDa] = useState(false);
  const hen = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(hen.current), []);
  // Chưa ai chọn gì (?sp= trống) → 3 nhóm nhiều bên nhất, KHÔNG ghi lên URL. Bỏ chọn hết bằng tay thì là rỗng thật.
  // Đến với ?ben= (bóng của Tóm tắt không tìm được nhóm nào) → rỗng thật: 3 nhóm mặc định không thuộc bên đó.
  const daChon = useRef(sp.length > 0 || !!ben);
  const chonSp = useMemo(() => (sp.length || daChon.current ? sp : macDinhSp(tatCa ?? [])), [sp, tatCa]);
  const chon = useMemo(() => nhomChon(tatCa ?? [], chonSp), [tatCa, chonSp]);
  const ds = useMemo(() => locDanhSach(tatCa ?? [], { nganh, tim, nhanh, ben }), [tatCa, nganh, tim, nhanh, ben]);
  // Một chip mỗi tên HIỂN THỊ (hai cách viết OBC của cùng ngành → một chip; locDanhSach so theo tên hiển thị).
  const dsNganh = useMemo(() => [...new Map((tatCa ?? []).map(n => [tenNganh(n.nganh), n.nganh ?? ""])).values()]
    .sort((a, b) => a.localeCompare(b, "ja")), [tatCa]);
  const tenBen = useMemo(() => (ben ? (tatCa ?? []).flatMap(n => n.quan_sat).find(q => q.ma_doi_thu === ben)?.ten_doi_thu ?? ben : ""),
    [tatCa, ben]);
  const thieu = useMemo(() => demThieu(chon, { chiCung: cung }), [chon, cung]);
  const mo: MoSua = (x, tru_o) => datSua({ nguon: x.nguon, id: x.id, tru_o });
  // "?" phí giao: thiếu kg / thùng → quy cách (KOME: hộp sửa quy cách mã KOME); thiếu điều kiện → SuaGiaoHang của bên đó.
  const moPhi: MoPhi = (n, d) => {
    if (d.phiHoi === "kg") {
      if (d.kome) datSuaQc(n);
      else mo(d.q!, d.q!.so_goi_thung == null ? "so_goi_thung" : d.q!.kl_goi_g == null ? "kl_goi_g" : undefined);
      return;
    }
    const ma = d.kome ? "KOME" : d.q!.ma_doi_thu;
    const g = gh.data?.dong.find(x => x.ma_doi_thu === ma);
    datSuaGiao({ g: g ?? giaoTrong(ma, d.kome ? "KOME" : d.q!.ten_doi_thu), tru_o: truOPhi(g, d.phi?.chua_ro[0]) });
  };

  const batTatNhom = (khoa: string) => {
    const r = batTat(chonSp, khoa);
    if (r.day) {
      datToiDa(true); clearTimeout(hen.current); hen.current = setTimeout(() => datToiDa(false), 1800);
      return;
    }
    daChon.current = true;
    dat({ sp: r.sp });
  };

  // ?nhom=<nhom_khoa> (từ Tóm tắt / tab khác): đưa nhóm đó lên đầu danh sách chọn, cuộn tới, rồi bỏ tham số.
  // Trỏ tới nhóm KHÔNG có dòng so sánh (vd chỉ có giá khách kể — mart 060 không tính chúng): giữ tham số và nói ra.
  const neo = useRef<Record<string, HTMLElement | null>>({});
  const cuonToi = useRef("");
  const khongDong = !!nhom && !!tatCa && !tatCa.some(n => n.nhom_khoa === nhom);
  useEffect(() => {
    if (!nhom || !tatCa || khongDong) return;
    daChon.current = true;
    cuonToi.current = nhom;
    dat({ sp: [nhom, ...chonSp.filter(k => k !== nhom)].slice(0, TOI_DA_SP), nhom: "" });
  }, [nhom, tatCa, khongDong]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const d = cuonToi.current && dongMoSan(chon, cuonToi.current);   // nhiều đơn vị so → dòng 'kg' trước
    if (!d) return;
    cuonToi.current = "";
    requestAnimationFrame(() => neo.current[khoaNhom(d)]?.scrollIntoView?.({ block: "start" }));
  }, [chon]);

  const ve = { sl, gk, chiCung: cung, mo, phi: ps, moPhi };
  return (
    <section className="dt-khoi">
      <Khoi tieu_de="So sánh giá" dang_tai={q.isLoading} loi={q.error ? (q.error as Error).message : null} cach_tinh={CACH_TINH}>
        {khongDong && <p className="dt-nhat" role="status">Chưa có giá từ bảng giá cho nhóm này — chỉ có tin khách kể (xem Tin thị trường)</p>}
        <div className="dt-ss">
          <aside className="dt-ss-trai" aria-label="Chọn nhóm để so">
            <input type="search" placeholder="🔍 Tìm sản phẩm KOME…" aria-label="Tìm nhóm hoặc mã KOME" value={tim}
              onChange={e => datTim(e.target.value)} />
            <div className="dt-chips" role="group" aria-label="Chọn nhanh">
              {NHANH.map(([m, t]) => <button key={m || "tat"} type="button" className="chip" aria-pressed={nhanh === m}
                onClick={() => datNhanh(m)}>{t}</button>)}
            </div>
            <div className="dt-chips" role="group" aria-label="Ngành">
              <button type="button" className="chip" aria-pressed={!nganh} onClick={() => dat({ nganh: "" })}>Mọi ngành</button>
              {dsNganh.filter(Boolean).map(g => { const on = !!nganh && tenNganh(nganh) === tenNganh(g); return (
                <button key={g} type="button" className="chip" aria-pressed={on}
                  onClick={() => dat({ nganh: on ? "" : g })}>{tenNganh(g)}</button>); })}
            </div>
            {ben && <div className="dt-chips"><button type="button" className="chip" aria-pressed="true"
              aria-label={`Bỏ lọc bên ${tenBen}`} onClick={() => dat({ ben: "" })}>Bên: {tenBen} ✕</button></div>}
            <p className="dt-toi-da" role="status">{toiDa ? `Tối đa ${TOI_DA_SP}` : ""}</p>
            <ul className="dt-mhs">
              {ds.map(n => {
                const on = chonSp.includes(n.nhom_khoa);
                const p = n.lech_trung_vi == null ? null : Math.round(n.lech_trung_vi * 100);
                const ten = n.ten_nhom ?? n.nhom_khoa;
                return (
                  <li key={khoaNhom(n)}>
                    <label className={"dt-mh" + (on ? " chon" : "")}>
                      <input type="checkbox" checked={on} onChange={() => batTatNhom(n.nhom_khoa)} />
                      <HinhMa ma={n.ma_kome?.[0]} ten={ten} co={34} trang_tri />
                      <span>
                        <b><i className={"dt-cham " + mauKomeSoTT(p)} aria-hidden="true" />{ten}</b>
                        <small>KOME {pcDau(p)} · {soMatHang(n)} mặt hàng đối thủ</small>
                      </span>
                    </label>
                  </li>);
              })}
              {tatCa && ds.length === 0 && <li className="dt-nhat">Không có nhóm nào khớp.</li>}
            </ul>
          </aside>

          <div className="dt-ss-phai">
            <div className="dt-dk">
              <span className="dt-dk-nhom" role="group" aria-label="Khách mua">
                <span className="dt-dk-nhan">Khách mua:</span>
                {SL.map(s => <button key={s} type="button" className="chip" aria-pressed={sl === s} onClick={() => dat({ sl: s })}>{NHAN_SL[s]}</button>)}
              </span>
              <span className="dt-dk-nhom" role="group" aria-label="Cách vẽ">
                <span className="dt-dk-nhan">Cách vẽ:</span>
                {XEM.map(([m, t]) => <button key={m} type="button" className="chip" aria-pressed={xem === m} onClick={() => dat({ xem: m })}>{t}</button>)}
              </span>
              <label><input type="checkbox" checked={cung} onChange={e => dat({ cung: e.target.checked })} /> Chỉ cùng thương hiệu</label>
              <label><input type="checkbox" checked={phi} onChange={e => dat({ phi: e.target.checked })} /> Tính cả phí giao</label>
              <label>Giá KOME:
                <select value={gk} onChange={e => dat({ gk: e.target.value })}>
                  {LUA_CHON_GK.map(x => <option key={x.ma} value={x.ma}>{x.nhan}</option>)}
                  {!LUA_CHON_GK.some(x => x.ma === gk) && <option value={gk}>{gk}</option>}
                </select>
              </label>
            </div>
            {phi && sl === "pallet" && <p className="dt-nhat" role="status">Phí giao không áp cho pallet.</p>}
            {phi && gh.isLoading && <p className="dt-nhat" role="status">Đang tải điều kiện giao hàng…</p>}
            {phi && gh.error && <p className="dt-loi" role="alert">Không tải được điều kiện giao hàng: {(gh.error as Error).message}</p>}
            {thieu.so > 0 && thieu.dau && (
              <p className="dt-thieu">✎ {thieu.so} mặt hàng còn thiếu gói / thùng hoặc tịnh 1 gói — <button type="button"
                onClick={() => mo(thieu.dau!, thieu.truong ?? undefined)}>bấm để điền cái đầu tiên</button></p>)}
            {chon.length === 0 ? <p className="dt-nhat">Chọn ít nhất một nhóm ở cột trái.</p>
              : xem === "cot" ? <>
                  {chon.map(n => <BieuDoCot key={khoaNhom(n)} n={n} {...ve}
                    neo={e => { neo.current[khoaNhom(n)] = e; }} />)}
                  <ChuGiaiCot phi={!!ps && sl !== "pallet"} />
                </>
              : xem === "cham" ? <><BieuDoCham ds={chon} {...ve} /><ChuGiaiCham /></>
              : <><BangNhiet ds={chon} {...ve} /><ChuGiaiNhiet /></>}
          </div>
        </div>
      </Khoi>
      {sua && <SuaMatHang nguon={sua.nguon} id={sua.id} tru_o={sua.tru_o} dong={() => datSua(null)} xong={() => datSua(null)} />}
      {suaGiao && <SuaGiaoHang dong={suaGiao.g} tru_o={suaGiao.tru_o} dong_lai={() => datSuaGiao(null)} xong={() => datSuaGiao(null)} />}
      {suaQc && <SuaQuyCach n={suaQc} dong={() => datSuaQc(null)} />}
    </section>
  );
}
