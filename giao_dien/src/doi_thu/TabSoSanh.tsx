// Tab "So sánh giá" (đợt 4b task 6; đặc tả §4.2, bản phác ca-trang-8.html): cột trái chọn tối đa 8 nhóm · thanh điều
// khiển (Khách mua · Cách vẽ · Chỉ cùng thương hiệu · Giá KOME — tất cả trên URL qua url.ts ở ManDoiThu) · dòng đếm ô
// trống · A Cột (BieuDoCot) / B Chấm (BieuDoCham) / C Bảng nhiệt (BangNhiet) · bấm → SuaMatHang. Mọi luật ở
// so_sanh_logic.ts; ở đây chỉ nối. "Tính cả phí giao" chưa có (task 9) — ẩn hẳn.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { lay } from "../api";
import { HinhMa } from "../chung/HinhMa";
import { Khoi } from "../chung/Khoi";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import { BangNhiet, ChuGiaiNhiet } from "./BangNhiet";
import { BieuDoCham, ChuGiaiCham } from "./BieuDoCham";
import { BieuDoCot, ChuGiaiCot, type MoSua } from "./BieuDoCot";
import type { Nhom } from "./kieu";
import { dongMoSan } from "./loc";
import { mauKomeSoTT } from "./mau";
import { tenNganh } from "./nganh";
import { batTat, demThieu, khoaNhom, LUA_CHON_GK, locDanhSach, macDinhSp, NHAN_SL, nhomChon, pcDau, soMatHang,
  type NutNhanh, type SoLuong } from "./so_sanh_logic";
import { SuaMatHang } from "./SuaMatHang";
import { TOI_DA_SP, type TrangThaiUrl } from "./url";

type Url = Pick<TrangThaiUrl, "sp" | "sl" | "xem" | "gk" | "cung" | "nganh">;
type Props = Url & { nhom: string; dat: (moi: Partial<Url & { nhom: string }>) => void };

const NHANH: [NutNhanh, string][] = [["", "Tất cả"], ["dat", "KOME đắt nhất"], ["het", "Đối thủ đang hết"], ["thieu", "Còn ô trống"]];
const XEM: [TrangThaiUrl["xem"], string][] = [["cot", "A · Cột"], ["cham", "B · Chấm"], ["nhiet", "C · Bảng nhiệt"]];
const SL: SoLuong[] = ["1", "5", "10", "pallet"];
const CACH_TINH = <>
  Giá quy về ¥/kg chưa thuế (÷ 1,08 khi bảng giá ghi đã gồm thuế; thuế không rõ tính như chưa thuế). "Khách mua" lấy bậc
  giá rẻ nhất bên đó ghi cho số lượng ấy; bên không ghi giá pallet thì dùng giá lẻ. % = giá đối thủ so với giá KOME đang
  chọn: đỏ = đối thủ rẻ hơn KOME quá 5%, xanh = KOME rẻ hơn quá 5%, xám = ngang. "KOME ±x%" ở cột trái = 標準価格 so với
  trung vị giá lẻ của đối thủ — không đổi theo "Khách mua". Thu gọn: KOME + 5 mặt hàng rẻ nhất + mọi mặt hàng cùng
  thương hiệu. Giá khách kể không vẽ ở đây.</>;

export function TabSoSanh({ sp, sl, xem, gk, cung, nganh, nhom, dat }: Props) {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "so-sanh", kx],
    queryFn: () => lay<{ nhom: Nhom[] }>(`/api/doi-thu/so-sanh${kx ? "?" + kx : ""}`) });
  const tatCa = q.data?.nhom;
  const [tim, datTim] = useState("");
  const [nhanh, datNhanh] = useState<NutNhanh>("");
  const [sua, datSua] = useState<{ nguon: "nap" | "tay"; id: number; tru_o?: string } | null>(null);
  const [toiDa, datToiDa] = useState(false);
  const hen = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(hen.current), []);
  // Chưa ai chọn gì (?sp= trống) → 3 nhóm nhiều bên nhất, KHÔNG ghi lên URL. Bỏ chọn hết bằng tay thì là rỗng thật.
  const daChon = useRef(sp.length > 0);
  const chonSp = useMemo(() => (sp.length || daChon.current ? sp : macDinhSp(tatCa ?? [])), [sp, tatCa]);
  const chon = useMemo(() => nhomChon(tatCa ?? [], chonSp), [tatCa, chonSp]);
  const ds = useMemo(() => locDanhSach(tatCa ?? [], { nganh, tim, nhanh }), [tatCa, nganh, tim, nhanh]);
  const dsNganh = useMemo(() => [...new Set((tatCa ?? []).map(n => n.nganh ?? ""))].sort((a, b) => a.localeCompare(b, "ja")), [tatCa]);
  const thieu = useMemo(() => demThieu(chon, { chiCung: cung }), [chon, cung]);
  const mo: MoSua = (x, tru_o) => datSua({ nguon: x.nguon, id: x.id, tru_o });

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

  const ve = { sl, gk, chiCung: cung, mo };
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
              {dsNganh.filter(Boolean).map(g => <button key={g} type="button" className="chip" aria-pressed={nganh === g}
                onClick={() => dat({ nganh: nganh === g ? "" : g })}>{tenNganh(g)}</button>)}
            </div>
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
              <label>Giá KOME:
                <select value={gk} onChange={e => dat({ gk: e.target.value })}>
                  {LUA_CHON_GK.map(x => <option key={x.ma} value={x.ma}>{x.nhan}</option>)}
                  {!LUA_CHON_GK.some(x => x.ma === gk) && <option value={gk}>{gk}</option>}
                </select>
              </label>
            </div>
            {thieu.so > 0 && thieu.dau && (
              <p className="dt-thieu">✎ {thieu.so} mặt hàng còn thiếu gói / thùng hoặc tịnh 1 gói — <button type="button"
                onClick={() => mo(thieu.dau!, thieu.truong ?? undefined)}>bấm để điền cái đầu tiên</button></p>)}
            {chon.length === 0 ? <p className="dt-nhat">Chọn ít nhất một nhóm ở cột trái.</p>
              : xem === "cot" ? <>
                  {chon.map(n => <BieuDoCot key={khoaNhom(n)} n={n} {...ve}
                    neo={e => { neo.current[khoaNhom(n)] = e; }} />)}
                  <ChuGiaiCot />
                </>
              : xem === "cham" ? <><BieuDoCham ds={chon} {...ve} /><ChuGiaiCham /></>
              : <><BangNhiet ds={chon} {...ve} /><ChuGiaiNhiet /></>}
          </div>
        </div>
      </Khoi>
      {sua && <SuaMatHang nguon={sua.nguon} id={sua.id} tru_o={sua.tru_o} dong={() => datSua(null)} xong={() => datSua(null)} />}
    </section>
  );
}
