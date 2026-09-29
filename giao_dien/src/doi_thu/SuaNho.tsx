// Pop-up nhỏ của màn Thị trường & đối thủ (đặc tả §4.7): điều kiện bán · thông tin bên · điều kiện giao hàng.
// Cùng khung HopThoai và cùng cách xử lý 409 với SuaMatHang (useGhi + KhungXungDot ở đây, SuaMatHang dùng lại).
import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { gui } from "../api";
import { ngay } from "../dinh_dang";
import { HopThoai } from "./HopThoai";
import { LOAI_DK, type DieuKien, type GiaoHang, type XungDot } from "./kieu";
import {
  GIAO_BOOL, GIAO_SO, VUNG_SO, docXungDot, formGiao, moTaXungDot, payloadGiao, type FormGiao, type TruongGiaoDon, type VungSo,
} from "./sua_logic";

/** Trạng thái một lần Lưu: đang gửi · câu lỗi (400) · xung đột (409). Thành công → làm mới mọi truy vấn "doi-thu"
 *  rồi `xong()`. `ghiDe` gửi lại ĐÚNG hàm vừa gửi với `ghi_de = true`; `giu` = giữ bản kia (làm mới rồi đóng). */
export function useGhi(xong: () => void, dong: () => void) {
  const qc = useQueryClient();
  const [dang, datDang] = useState(false);
  const [loi, datLoi] = useState<string | null>(null);
  const [xung, datXung] = useState<XungDot | null>(null);
  const cuoi = useRef<((ghi_de: boolean) => Promise<unknown>) | null>(null);
  const chay = (fn: (ghi_de: boolean) => Promise<unknown>, ghi_de = false) => {
    if (dang) return;
    cuoi.current = fn; datDang(true); datLoi(null); datXung(null);
    fn(ghi_de)
      .then(() => { qc.invalidateQueries({ queryKey: ["doi-thu"] }); xong(); })
      .catch((e: unknown) => {
        const x = docXungDot(e);
        if (x) datXung(x); else datLoi(e instanceof Error ? e.message : String(e));
      })
      .finally(() => datDang(false));
  };
  return {
    dang, loi, xung, datLoi, chay,
    ghiDe: () => { if (cuoi.current) chay(cuoi.current, true); },
    giu: () => { qc.invalidateQueries({ queryKey: ["doi-thu"] }); dong(); },
  };
}

/** Khung "X vừa sửa lúc …" + Ghi đè / Giữ bản kia (đặc tả §4.7 chống sửa đè). */
export function KhungXungDot({ x, dang, ghiDe, giu }: { x: XungDot; dang: boolean; ghiDe: () => void; giu: () => void }) {
  return (
    <div className="dt-xung" role="alert">
      <p>{moTaXungDot(x)}</p>
      <div className="dt-nut">
        <button type="button" className="nut-chinh" disabled={dang} onClick={ghiDe}>Ghi đè</button>
        <button type="button" className="chip" disabled={dang} onClick={giu}>Giữ bản {x.ai ? `của ${x.ai}` : "kia"}</button>
      </div>
    </div>
  );
}

/** Hàng nút cuối pop-up: Lưu (chính) · Huỷ · câu nhỏ; lỗi 400 dưới nút. */
export function NutLuu({ luu, dong, tat, dang, loi, chu }: {
  luu: () => void; dong: () => void; tat: boolean; dang: boolean; loi: string | null; chu?: string;
}) {
  return <>
    <div className="dt-nut dt-nut-cuoi">
      <button type="button" className="nut-chinh" disabled={tat || dang} onClick={luu}>{dang ? "Đang lưu…" : "Lưu"}</button>
      <button type="button" className="chip" onClick={dong}>Huỷ</button>
      {chu && <small className="dt-nhat">{chu}</small>}
    </div>
    {loi && <p role="alert" className="dt-loi">{loi}</p>}
  </>;
}

// ---------------------------------------------------------------- điều kiện bán

/** Thêm (không `dk`) / sửa / bỏ một điều kiện bán. Dòng thêm tay (`them_tay`): máy chủ nhận ra dòng bằng
 *  (bên, loại, nội dung) — sửa chữ = bỏ dòng cũ (kiểm 409) rồi thêm dòng mới. */
export function SuaDieuKien({ ben, dk, dong, xong }: {
  ben: { ma: string; ten: string | null }; dk?: DieuKien; dong: () => void; xong: () => void;
}) {
  const [loai, datLoai] = useState(dk?.loai ?? "ship");
  const [nd, datNd] = useState(dk?.noi_dung ?? "");
  const [bo, datBo] = useState(false);
  const g = useGhi(xong, dong);
  const doi = !dk || bo || loai !== dk.loai || nd.trim() !== dk.noi_dung;
  const hopLe = bo || (nd.trim().length >= 1 && nd.trim().length <= 300);
  const luu = () => g.chay(async ghi_de => {
    const goc = { ma_doi_thu: ben.ma, da_xem: dk?.sua_cuoi ?? 0, ghi_de };
    if (!dk) return gui("/api/doi-thu/dieu-kien", { ...goc, fact_id: null, loai, noi_dung: nd.trim(), bo: false });
    if (!dk.them_tay) return gui("/api/doi-thu/dieu-kien", { ...goc, fact_id: dk.fact_id, loai, noi_dung: nd.trim(), bo });
    await gui("/api/doi-thu/dieu-kien", { ...goc, fact_id: null, loai: dk.loai, noi_dung: dk.noi_dung, bo: true });
    if (!bo) return gui("/api/doi-thu/dieu-kien", { ...goc, fact_id: null, loai, noi_dung: nd.trim(), bo: false });
  });
  return (
    <HopThoai tieu_de={`${dk ? "Sửa" : "Thêm"} điều kiện bán · ${ben.ten ?? ben.ma}`} dong={dong} rong={480}>
      <div className="dt-nho">
        <label>Loại
          <select value={loai} disabled={bo} onChange={e => datLoai(e.target.value)}>
            {LOAI_DK.map(([m, t]) => <option key={m} value={m}>{t}</option>)}
            {!LOAI_DK.some(([m]) => m === loai) && <option value={loai}>{loai}</option>}
          </select></label>
        <label>Nội dung
          <textarea rows={3} maxLength={300} value={nd} disabled={bo} onChange={e => datNd(e.target.value)} /></label>
        {dk && <label className="dt-o-chon">
          <input type="checkbox" checked={bo} onChange={e => datBo(e.target.checked)} /> Điều kiện này không còn đúng — bỏ đi</label>}
        {dk && <small className="dt-nhat">{dk.them_tay ? "Thêm tay" : "Từ bảng giá"} · {ngay(dk.ngay)}</small>}
        {g.xung && <KhungXungDot x={g.xung} dang={g.dang} ghiDe={g.ghiDe} giu={g.giu} />}
        <NutLuu luu={luu} dong={dong} tat={!doi || !hopLe} dang={g.dang} loi={g.loi} />
      </div>
    </HopThoai>
  );
}

// ---------------------------------------------------------------- thông tin bên

export function SuaBen({ ben, sua_cuoi, dong, xong }: {
  ben: { ma: string; ten: string; web: string | null; ghi_chu: string | null }; sua_cuoi: number; dong: () => void; xong: () => void;
}) {
  const [ten, datTen] = useState(ben.ten);
  const [web, datWeb] = useState(ben.web ?? "");
  const [ghiChu, datGhiChu] = useState(ben.ghi_chu ?? "");
  const g = useGhi(xong, dong);
  const d: Record<string, string> = {};
  if (ten.trim() !== ben.ten) d.ten = ten.trim();
  if (web.trim() !== (ben.web ?? "")) d.web = web.trim();
  if (ghiChu.trim() !== (ben.ghi_chu ?? "")) d.ghi_chu = ghiChu.trim();
  const luu = () => {
    if (!ten.trim()) return g.datLoi("Tên hiển thị không được trống.");
    if (web.trim() && !/^https:\/\/\S+$/i.test(web.trim())) return g.datLoi("Website phải bắt đầu bằng https://");
    g.chay(ghi_de => gui("/api/doi-thu/ben", { ma: ben.ma, ...d, da_xem: sua_cuoi, ghi_de }));
  };
  return (
    <HopThoai tieu_de={`Sửa thông tin: ${ben.ten}`} dong={dong} rong={480}>
      <div className="dt-nho">
        <label>Tên hiển thị <input type="text" maxLength={80} value={ten} onChange={e => datTen(e.target.value)} /></label>
        <label>Website <input type="url" placeholder="https://…" value={web} onChange={e => datWeb(e.target.value)} /></label>
        <label>Ghi chú về bên này
          <textarea rows={3} maxLength={300} placeholder="vd: chỉ bán sỉ, giao Kanto thứ 3 & 6" value={ghiChu}
            onChange={e => datGhiChu(e.target.value)} /></label>
        {g.xung && <KhungXungDot x={g.xung} dang={g.dang} ghiDe={g.ghiDe} giu={g.giu} />}
        <NutLuu luu={luu} dong={dong} tat={!Object.keys(d).length} dang={g.dang} loi={g.loi} />
      </div>
    </HopThoai>
  );
}

// ---------------------------------------------------------------- điều kiện giao hàng

const CHON_GIAO: Partial<Record<TruongGiaoDon, [string, string][]>> = {
  phi_ship_theo: [["don", "mỗi đơn"], ["thung", "mỗi thùng"], ["kien", "mỗi kiện"]],
  thue: [["bao", "Đã gồm thuế"], ["chua", "Chưa gồm thuế"], ["khong_ro", "Bảng không nói"]],
};
const NHAN_GIAO: [TruongGiaoDon, string][] = [
  ["bao_ship", "Bao ship (phí đã nằm trong giá hàng)"], ["phi_ship", "Phí ship (¥)"], ["phi_ship_theo", "Tính phí ship theo"],
  ["mien_ship_tu", "Miễn ship khi đơn từ (¥)"], ["mien_ship_kien", "… hoặc khi đủ (kiện)"], ["thung_moi_kien", "Số thùng / kiện"],
  ["phi_daibiki", "Phí daibiki (¥)"], ["daibiki_tu", "Daibiki giảm khi đơn từ (¥)"], ["daibiki_sau", "… thì phí daibiki còn (¥, 0 = miễn)"],
  ["ck_mien_daibiki", "Chuyển khoản trước thì không phí daibiki"], ["kien_toi_da_kg", "Kiện tối đa (kg)"],
  ["ghep_kien", "Ghép kiện"], ["thue", "Giá hàng đã gồm thuế?"], ["cach_gui", "Phí gửi / cách gửi khác"],
];
const TEN_VUNG: Record<VungSo, string> = { hokkaido: "Hokkaido", tohoku: "Tohoku", kyushu: "Kyushu", chugoku: "Chugoku", shikoku: "Shikoku" };
const GOI_Y: Partial<Record<TruongGiaoDon, string>> = { ghep_kien: "vd: 3–4 loại / kiện", cach_gui: "vd: 宅急便, phí lạnh" };

/** Sửa điều kiện giao hàng của MỘT bên (`dong` = dòng dữ liệu; `dong_lai` = đóng hộp). `tru_o` = tên trường
 *  (`phi_ship`, …; vùng: `phu_phi.hokkaido` / `phu_phi.okinawa`, hoặc `phu_phi` = ô vùng đầu). */
export function SuaGiaoHang({ dong, tru_o, dong_lai, xong }: {
  dong: GiaoHang; tru_o?: string; dong_lai: () => void; xong: () => void;
}) {
  const [f, datF] = useState<FormGiao>(() => formGiao(dong));
  const [xacNhan, datXacNhan] = useState(false);
  const g = useGhi(xong, dong_lai);
  const kome = dong.ma_doi_thu === "KOME";
  const p = payloadGiao(dong, f, false, xacNhan);
  const tro = tru_o === "phu_phi" ? "phu_phi.hokkaido" : tru_o;
  const dau = (k: string) => (tro === k ? { "data-focus": "", className: "dt-tro" } : {});
  const datT = (t: TruongGiaoDon, v: string) => datF({ ...f, truong: { ...f.truong, [t]: v } });
  const o = (t: TruongGiaoDon) => {
    const v = f.truong[t];
    if (GIAO_BOOL.includes(t))
      return <select value={v} onChange={e => datT(t, e.target.value)} {...dau(t)}>
        <option value="">? Chưa rõ</option><option value="true">Có</option><option value="false">Không</option></select>;
    const chon = CHON_GIAO[t];
    if (chon)
      return <select value={v} onChange={e => datT(t, e.target.value)} {...dau(t)}>
        <option value="">? Chưa rõ</option>{chon.map(([m, n]) => <option key={m} value={m}>{n}</option>)}</select>;
    return <input type="text" inputMode={GIAO_SO.includes(t) ? "decimal" : undefined} placeholder={GOI_Y[t] ?? "?"}
      value={v} onChange={e => datT(t, e.target.value)} {...dau(t)} />;
  };
  const luu = () => g.chay(ghi_de => gui("/api/doi-thu/giao-hang", payloadGiao(dong, f, ghi_de, xacNhan).body));
  return (
    <HopThoai tieu_de={`Điều kiện giao hàng · ${dong.ten ?? dong.ma_doi_thu}`} dong={dong_lai} rong={620}>
      <div className="dt-nho">
        {dong.nguon_chu && <p className="dt-nhat dt-goc">Gốc: “{dong.nguon_chu}”{dong.ngay_nguon && <> · {ngay(dong.ngay_nguon)}</>}</p>}
        {kome && dong.suy && !dong.da_xac_nhan && <p className="dt-nhat">Số đang là suy từ phiếu bán — chưa ai xác nhận.</p>}
        <div className="dt-luoi-2">
          {NHAN_GIAO.map(([t, n]) => <label key={t}>{n}{o(t)}</label>)}
        </div>
        <fieldset className="dt-vung"><legend>Phụ phí vùng (+¥ / kiện)</legend>
          <div className="dt-luoi-2">
            {VUNG_SO.map(v => <label key={v}>{TEN_VUNG[v]}
              <input type="text" inputMode="numeric" placeholder="?" value={f.vung[v]} {...dau(`phu_phi.${v}`)}
                onChange={e => datF({ ...f, vung: { ...f.vung, [v]: e.target.value } })} /></label>)}
            <label>Okinawa
              <span className="dt-hang">
                <select value={f.okinawa} {...dau("phu_phi.okinawa")}
                  onChange={e => datF({ ...f, okinawa: e.target.value as FormGiao["okinawa"] })}>
                  <option value="">?</option><option value="co">+¥</option><option value="khong_nhan">không nhận</option></select>
                {f.okinawa === "co" && <input type="text" inputMode="numeric" placeholder="¥ / kiện" aria-label="Phụ phí Okinawa (¥ / kiện)"
                  value={f.okinawa_so} onChange={e => datF({ ...f, okinawa_so: e.target.value })} />}
              </span></label>
          </div>
        </fieldset>
        {kome && <label className="dt-o-chon">
          <input type="checkbox" checked={xacNhan} onChange={e => datXacNhan(e.target.checked)} /> Tôi xác nhận các số này</label>}
        {g.xung && <KhungXungDot x={g.xung} dang={g.dang} ghiDe={g.ghiDe} giu={g.giu} />}
        <NutLuu luu={luu} dong={dong_lai} tat={p.rong} dang={g.dang} loi={g.loi} chu="Để trống = chưa rõ (không phải 0)." />
      </div>
    </HopThoai>
  );
}
