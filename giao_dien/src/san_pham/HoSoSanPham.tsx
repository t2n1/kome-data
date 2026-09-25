// Hồ sơ 360° một mã (Sản phẩm.dc.html — phần dưới danh mục). Số THẬT từ
// /api/san-pham/{mã} (kome/san_pham.py::ho_so, trần 5 lượt hỏi) và
// /api/san-pham/{mã}/ngay (bán theo ngày, tải khi xem). Khối gói thiết kế không
// có nguồn (khách chưa mua / cơ hội chào hàng, hàng về, ảnh sản phẩm) là khung
// "chưa có dữ liệu" nói rõ thiếu gì — không số mẫu.
import { useQuery } from "@tanstack/react-query";
import { keepPreviousData } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { lay } from "../api";
import { BieuDo } from "../chung/BieuDo";
import { ChuaCoDuLieu } from "../chung/Khoi";
import { gon, ngay, pc, so, so_luong as soLuong, thang_nhan, thay_doi, yen } from "../dinh_dang";
import type { HoSoSpApi, MaHang, NgayApi } from "./kieu";
import { chuoiKhoang, useKhoang, voiKhoang, type KhoangMayChu } from "../khung/khoang";
import { TN } from "../khoi_dau";

/** Một mã trong KHOẢNG XEM (/api/san-pham/{mã}/khoang — đợt C). */
type MaKhoang = {
  khoang: KhoangMayChu; so_sanh: { ma: string; nhan: string; co: boolean; tu: string; den: string };
  tong: { dt: number; lg: number; so_luong: number; so_khach: number }; dt_ss: number | null; tang: number | null;
  khach: { ma: string; ten: string; doanh_thu: number; so_luong: number; so_ngay: number; lan_cuoi: string }[];
} | null;

const CHI_SO = [["so_luong", "Số lượng"], ["doanh_thu", "Doanh thu"], ["lai_gop", "Lãi gộp"]] as const;
type ChiSo = typeof CHI_SO[number][0];

export function HoSoSanPham({ ma, dong, onDong }: { ma: string; dong: MaHang | null; onDong: () => void }) {
  const { data, error } = useQuery<HoSoSpApi>({
    queryKey: ["sp-ho-so", ma, chuoiKhoang(useKhoang())], queryFn: () => lay<HoSoSpApi>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}`)),
    placeholderData: keepPreviousData,
  });
  const [thang, datThang] = useState<string | null>(null);
  useEffect(() => { datThang(null); }, [ma]);
  const kxs = chuoiKhoang(useKhoang());
  const { data: mk } = useQuery<MaKhoang>({
    queryKey: ["sp-ma-khoang", ma, kxs], placeholderData: keepPreviousData,
    queryFn: () => lay<MaKhoang>(voiKhoang(`/api/san-pham/${encodeURIComponent(ma)}/khoang`)),
  });
  useEffect(() => { datThang(null); }, [kxs]);

  if (error) return <section className="kh-the sp-hs"><div className="khoi-loi">{(error as Error).message}</div></section>;
  if (!data) return <section className="kh-the sp-hs"><div className="khoi-cho" aria-busy="true"><span /><span /><span /></div></section>;
  const h = data.h, sp = h.sp;
  const cu = sp.ma !== ma;                           // đang hiện hồ sơ mã trước trong lúc tải mã mới
  const thangCuoi = h.thang.length ? h.thang[h.thang.length - 1].thang : null;
  // Biểu đồ theo ngày mặc định = tháng của ngày cuối khoảng xem (nếu nằm trong 12 tháng của mã).
  const thangKx = mk?.khoang.den.slice(0, 7);
  const thangXem = thang ?? (thangKx && h.thang.some(t => t.thang === thangKx) ? thangKx : thangCuoi);
  const tongKhach = h.khach_mua.reduce((s, k) => s + k.doanh_thu, 0);
  const maxKhach = Math.max(1, ...h.khach_mua.map(k => k.doanh_thu));
  const tonTong = sp.ton;

  return (
    <div className={"sp-hs-khung" + (cu ? " dang-tai" : "")}>
      <section className="kh-the sp-hs">
        <div className="sp-hs-dau">
          <div className="sp-anh" aria-hidden="true">{(sp.ten.trim()[0] ?? "?").toUpperCase()}</div>
          <div className="sp-hs-ten">
            <div className="sp-hs-dong"><h2 className="ten-jp">{sp.ten}</h2>
              <span className={"nhan-vien " + sp.mau}>{sp.nhan_trang_thai}</span>
              <button type="button" className="nut-nho sp-dong-hs" onClick={onDong} aria-label="Đóng hồ sơ">✕</button></div>
            <div className="phu"><code>{sp.ma}</code>{dong ? <> · <span className="ten-jp">{dong.nganh}</span></> : null} · bán lần đầu {ngay(sp.lan_dau)} · gần nhất {ngay(sp.lan_cuoi)}</div>
            <p className="sp-tom-tat">{tomTat(sp, dong)}</p>
          </div>
          <div className="sp-hs-o">
            <div className="o-kpi"><div className="nhan">Tồn hiện tại</div><div className="gia">{tonTong == null ? "—" : soLuong(tonTong)}</div>
              <div className="dong-phu nhat-chu">{tonTong == null ? "chưa rõ tồn — không phải 0" : "tổng cả hai lô (đang xuất + chờ)"}</div></div>
            <div className="o-kpi"><div className="nhan">Bán/ngày (theo tuổi mã)</div><div className="gia">{soLuong(sp.toc_do_ngay_theo_tuoi)}</div>
              <div className="dong-phu nhat-chu">90 ngày, chia cho số ngày mã có mặt</div></div>
            <div className="o-kpi"><div className="nhan">Còn đủ bán</div>
              <div className={"gia" + (sp.du_ban_ngay != null && sp.du_ban_ngay < 14 ? " giam" : "")}>{sp.du_ban_ngay == null ? "—" : `${Math.round(sp.du_ban_ngay)} ngày`}</div>
              <div className="dong-phu nhat-chu">tồn ÷ bán/ngày</div></div>
            <div className="o-kpi"><div className="nhan">Doanh thu 12 tháng</div><div className="gia">{dong ? gon(dong.dt_12t) : "—"}</div>
              <div className="dong-phu nhat-chu">tỷ suất {pc(dong?.ts_12t)} · luỹ kế {gon(sp.doanh_thu)}</div></div>
            <div className="o-kpi"><div className="nhan">Khách đã mua</div><div className="gia">{so(sp.so_khach)}</div>
              <div className="dong-phu nhat-chu">{so(h.khach_ngung.length)}{h.khach_ngung.length >= 10 ? "+" : ""} khách đã bỏ</div></div>
          </div>
        </div>
        {sp.trang_thai === "chua_ro_ton" && <div className="sp-canh">⚠️ <b>Chưa rõ tồn.</b> Mã này không có dòng nào trong 在庫一覧 gần nhất — ta <b>không biết</b> kho còn bao nhiêu (khác hẳn "đã hết"). Tra OBC trước khi đặt hàng.</div>}
        {sp.trang_thai === "het_hang" && <div className="sp-canh do">⚠️ <b>Hết hàng.</b> Tồn bằng 0 mà 90 ngày qua vẫn có đơn — cần đặt hàng.</div>}
        {sp.trang_thai === "sap_thieu" && <div className="sp-canh">⚠️ <b>Sắp thiếu.</b> Với nhịp bán hiện tại, tồn còn đủ chưa tới 14 ngày.</div>}
      </section>

      <BanTheoNgay ma={sp.ma} thang={thangXem} ds_thang={h.thang.map(t => t.thang)} datThang={datThang} />

      {mk && <section className="kh-the">
        <div className="kh-the-dau"><h2>Khách mua · {mk.khoang.nhan}</h2>
          <span className="kh-the-goc nhat-chu">{so(mk.tong.so_khach)} khách · {yen(mk.tong.dt)} · {soLuong(mk.tong.so_luong)} đơn vị
            {mk.so_sanh.co && mk.tang != null ? <> · <span className={mk.tang >= 0 ? "tang" : "giam"}>{thay_doi(mk.tang, 0)} so {mk.so_sanh.nhan}</span></> : ""}</span></div>
        {!mk.khach.length ? <p className="trong-nho">Không khách nào mua mã này trong khoảng đang xem.</p> :
        <div className="bang-cuon" style={{ maxHeight: 300 }}><table className="bang"><thead><tr><th>Khách hàng</th>
          <th className="so">Doanh thu</th><th className="so">Số lượng</th><th className="so">Số ngày mua</th><th className="so">Mua cuối</th></tr></thead>
          <tbody>{mk.khach.map(k => (
            <tr key={k.ma}><td className="ten-jp"><a href={`/khach-hang/${encodeURIComponent(k.ma)}`}>{k.ten}</a></td>
              <td className="so">{yen(k.doanh_thu)}</td><td className="so">{soLuong(k.so_luong)}</td>
              <td className="so">{so(k.so_ngay)}</td><td className="so">{ngay(k.lan_cuoi)}</td></tr>))}</tbody></table></div>}
        {mk.tong.so_khach > mk.khach.length && <p className="phu">Hiện {so(mk.khach.length)} khách doanh thu cao nhất trên {so(mk.tong.so_khach)}.</p>}
      </section>}

      <div className="sp-luoi-3">
        <section className="kh-the">
          <div className="kh-the-dau"><h2>Khách đang mua</h2><span className="kh-the-goc nhat-chu">{so(h.khach_mua.length)} khách{h.khach_mua.length >= 20 ? " đầu" : ""} · {yen(tongKhach)}</span></div>
          <p className="phu">Theo doanh thu của <em>chính mã này</em> (luỹ kế). Nhịp = trung vị khoảng cách giữa hai lần mua mã này; dưới 3 lần thì "—".</p>
          {h.khach_mua.length ? <div className="sp-khach">{h.khach_mua.map(k => (
            <a key={k.ma} className="sp-khach-dong" href={`/khach-hang/${encodeURIComponent(k.ma)}`}>
              <span className="sp-khach-nhan"><b className="ten-jp">{k.ten}</b><span>{yen(k.doanh_thu)}</span></span>
              <span className="kh-td-thanh mong"><i style={{ width: `${k.doanh_thu / maxKhach * 100}%` }} /></span>
              <span className="sp-khach-phu">{k.so_lan} lần · cuối {ngay(k.lan_cuoi)} · nhịp {k.nhip ? `${Math.round(k.nhip)} ngày` : "—"}
                {k.tre != null && k.tre > 0 ? ` · quá ${k.tre} ngày` : ""}</span>
            </a>))}</div> : <p className="trong-nho">Chưa có khách nào đang mua mã này.</p>}
        </section>
        <section className="kh-the">
          <div className="kh-the-dau"><h2>Khách đã ngừng mua mã này</h2><span className="kh-the-goc giam">{so(h.khach_ngung.length)}{h.khach_ngung.length >= 10 ? "+" : ""}</span></div>
          <p className="phu">Im lặng quá <b>2× nhịp mua riêng</b> của chính cặp khách–mã (không phải một ngưỡng chung) — cùng định nghĩa với hồ sơ khách. Khách ※廃業※ không có ở đây. Tối đa 10 khách mất nhiều tiền nhất.</p>
          {h.khach_ngung.length ? <div className="bang-cuon"><table className="bang"><thead><tr><th>Khách</th><th className="so">Nhịp</th><th className="so">Trễ</th><th className="so">Đã mua</th></tr></thead>
            <tbody>{h.khach_ngung.map(k => (
              <tr key={k.ma}><td><a className="ten-jp" href={`/khach-hang/${encodeURIComponent(k.ma)}`}>{k.ten}</a>
                <div className="ma-nho">{k.so_lan} lần · cuối {ngay(k.lan_cuoi)}</div></td>
                <td className="so">{k.nhip ? `${Math.round(k.nhip)}n` : "—"}</td>
                <td className="so giam">{k.tre != null ? `${k.tre}n` : "—"}</td>
                <td className="so">{gon(k.doanh_thu)}</td></tr>))}</tbody></table></div>
            : <p className="trong-nho">Không khách nào bỏ mã này. Tốt.</p>}
        </section>
        <section className="kh-the kh-chua-co">
          <ChuaCoDuLieu tieu_de="Khách chưa mua mã này"
            ly_do="Gợi ý chào hàng cần một cách chọn khách có kiểm chứng (khách cùng loại hình / cùng giỏ hàng). OBC chỉ xuất MÃ loại hình khách, không có tên — chưa dựng được gợi ý thật." />
        </section>
      </div>

      <div className="sp-luoi-2">
        <section className="kh-the">
          <div className="kh-the-dau"><h2>Tồn theo lô &amp; hàng về</h2>
            <a className="kh-the-goc" href={`/kho-hang?tim=${encodeURIComponent(sp.ma)}`}>Xem ở Kho hàng →</a></div>
          <p className="phu">Ảnh chụp 在庫一覧 mới nhất. Hai "kho" của OBC là hai <b>lô</b> trong cùng một kho: lô đang xuất bán trước, lô chờ (hạn mới hơn) được chuyển lên khi lô kia hết — xếp đúng thứ tự bán.
            "Còn hạn" và "Bán hết" đếm từ mốc dữ liệu (ngày bán mới nhất); "Bán hết" = tồn cộng dồn tới lô đó ÷ tốc độ bán (cùng tốc độ xếp trạng thái).</p>
          {h.ton.length ? <div className="bang-cuon"><table className="bang"><thead><tr><th>Lô</th><th className="so">Số lượng</th><th className="so">Giá trị</th><th>Hạn sử dụng</th><th className="so">Còn hạn</th><th className="so">Bán hết sau</th></tr></thead>
            <tbody>{h.ton.map((t, i) => (
              <tr key={i}><td><b>{t.vai_tro_lo === "dang_xuat" ? "Lô đang xuất" : "Lô chờ"}</b><div className="ma-nho ten-jp">{t.ten_kho ? `${t.kho} ${t.ten_kho}` : t.kho}</div></td>
                <td className="so">{soLuong(t.so_luong)}</td><td className="so">{yen(t.gia_tri)}</td>
                <td><span className={"nhan-vien " + t.mau_han}>{t.nhan_han}</span>{t.best_before && <div className="ma-nho ten-jp">{t.best_before}</div>}</td>
                <td className={"so " + (t.han_con_lai != null && t.han_con_lai < 0 ? "giam" : t.han_con_lai != null && t.han_con_lai <= 90 ? "canh-chu" : "")}>
                  {t.han_con_lai == null ? "—" : t.han_con_lai < 0 ? `quá ${-t.han_con_lai} ngày` : `${t.han_con_lai} ngày`}</td>
                <td className={"so " + (t.khong_kip_ban ? "giam" : "")} title={t.khong_kip_ban ? "Dự kiến bán hết SAU hạn sử dụng — không kịp bán" : undefined}>
                  {t.ban_het_sau == null ? "—" : `${Math.round(t.ban_het_sau)} ngày`}{t.khong_kip_ban ? " ⚠" : ""}</td></tr>))}</tbody></table></div>
            : <p className="trong-nho">Không có dòng nào trong 在庫一覧 gần nhất — <b>chưa rõ tồn</b>, không phải tồn bằng 0.</p>}
          <div className="sp-hang-ve"><span className="nhan-vien nhat">hàng về · chưa có dữ liệu</span>
            <span className="phu">OBC chưa xuất đơn mua / lịch container (仕入・発注) — chưa biết lô nào sắp về.</span></div>
        </section>
        {TN.bang_gia && <section className="kh-the">
          <div className="kh-the-dau"><h2>Giá theo bậc (売価No.)</h2><span className="kh-the-goc nhat-chu">giá chưa thuế</span></div>
          <p className="phu">Giá <b>đáng lẽ phải bán</b> của từng bậc giá OBC, dòng mới nhất của mỗi cặp (bậc, 荷姿). Bậc giá OBC KHÔNG phải hạng khách theo doanh thu 12 tháng.</p>
          {h.bac_gia.length ? <div className="sp-bac">{h.bac_gia.map((g, i) => (
            <div key={i} className="sp-bac-dong"><span className="nhan-vien lam">Bậc {g.bac}</span><span className="ten-jp">{g.quy_cach}</span>
              <b>{yen(g.gia)}</b><span className="phu">từ {ngay(g.tu_ngay)}</span></div>))}</div>
            : <p className="trong-nho">Mã này chưa có dòng nào trong 取引単価データ.</p>}
        </section>}
      </div>

      <XuHuong h={h} chon={thangXem} datThang={t => { datThang(t); document.getElementById("sp-ngay")?.scrollIntoView({ behavior: "smooth", block: "start" }); }} />
    </div>
  );
}

function tomTat(sp: MaHang, dong: MaHang | null): string {
  const ph: string[] = [];
  if (dong && dong.dt_12t) ph.push(`12 tháng qua bán ${gon(dong.dt_12t)}, tỷ suất ${pc(dong.ts_12t)}.`);
  else ph.push("12 tháng qua không có doanh thu.");
  if (sp.ton == null) ph.push("Chưa rõ tồn.");
  else if (sp.du_ban_ngay != null) ph.push(`Tồn ${soLuong(sp.ton)} — đủ bán khoảng ${Math.round(sp.du_ban_ngay)} ngày với nhịp hiện tại.`);
  else ph.push(`Tồn ${soLuong(sp.ton)}, 90 ngày qua không bán.`);
  ph.push(`${so(sp.so_khach)} khách đã từng mua.`);
  return ph.join(" ");
}

function BanTheoNgay({ ma, thang, ds_thang, datThang }: { ma: string; thang: string | null; ds_thang: string[]; datThang: (t: string) => void }) {
  const [cs, datCs] = useState<ChiSo>("so_luong");
  const { data, error, isFetching } = useQuery<NgayApi>({
    queryKey: ["sp-ngay", ma, thang], enabled: !!thang, placeholderData: keepPreviousData,
    queryFn: () => lay<NgayApi>(`/api/san-pham/${encodeURIComponent(ma)}/ngay?thang=${thang}`),
  });
  if (!thang) return <section className="kh-the sp-ngay" id="sp-ngay"><div className="kh-the-dau"><h2>Lượng bán theo ngày</h2></div>
    <p className="trong-nho">Mã này chưa từng có dòng bán.</p></section>;
  const n = data?.nay ?? [], t = data?.truoc ?? [];
  const mocNgay = data?.hom_nay && data.hom_nay.slice(0, 7) === thang ? +data.hom_nay.slice(8, 10) : null;
  const trongMoc = (d: { ngay: string }) => mocNgay == null || +d.ngay.slice(8, 10) <= mocNgay;
  const tong = (ds: typeof n, k: ChiSo) => ds.filter(trongMoc).reduce((s, d) => s + d[k], 0);
  const nay = tong(n, cs), truoc = tong(t, cs);
  const ss = truoc ? nay / truoc - 1 : null;
  const dinh = n.reduce<(typeof n)[number] | null>((a, d) => (!a || d[cs] > a[cs] ? d : a), null);
  const ngayCoBan = n.filter(d => d.so_luong !== 0).length;
  const fmt = (v: number | null) => v == null ? "—" : cs === "so_luong" ? soLuong(v) : yen(v);
  const tmoi = +thang.slice(5), ttruoc = tmoi === 1 ? 12 : tmoi - 1;
  const iThang = ds_thang.indexOf(thang);
  // Cột nhạt = CÙNG NGÀY của tháng trước (ngày 31 không có ở tháng trước thì trống).
  const theoNgay = new Map(t.map(d => [+d.ngay.slice(8, 10), d]));

  return (
    <section className={"kh-the sp-ngay" + (isFetching ? " dang-tai" : "")} id="sp-ngay">
      <div className="kh-the-dau">
        <h2>Lượng bán theo ngày</h2>
        <span className="phu">tháng {tmoi}/{thang.slice(0, 4)}{mocNgay ? ` · đến ngày ${mocNgay}` : ""} · cột nhạt là cùng ngày tháng {ttruoc}</span>
        <span className="sp-thang-chon">
          <button type="button" className="nut-nho" disabled={iThang <= 0} onClick={() => datThang(ds_thang[iThang - 1])} aria-label="Tháng trước">‹</button>
          <select value={thang} onChange={e => datThang(e.target.value)} aria-label="Chọn tháng">
            {[...ds_thang].reverse().map(x => <option key={x} value={x}>Tháng {+x.slice(5)}/{x.slice(0, 4)}</option>)}</select>
          <button type="button" className="nut-nho" disabled={iThang < 0 || iThang >= ds_thang.length - 1} onClick={() => datThang(ds_thang[iThang + 1])} aria-label="Tháng sau">›</button>
        </span>
        <span className="tab-pill" role="group" aria-label="Chỉ số">
          {CHI_SO.map(([k, nhan]) => <button key={k} type="button" aria-pressed={cs === k} onClick={() => datCs(k)}>{nhan}</button>)}</span>
      </div>
      {error ? <div className="khoi-loi">{(error as Error).message}</div> : !data ? <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div> : <>
        <div className="so-khoi sp-ngay-o">
          <div><div className="nhan">{CHI_SO.find(c => c[0] === cs)![1]} tháng {tmoi}{mocNgay ? ` (1–${mocNgay})` : ""}</div><div className="gia">{fmt(nay)}</div></div>
          <div><div className="nhan">So tháng {ttruoc} {mocNgay ? "cùng ngày" : "cả tháng"}</div>
            <div className={"gia " + (ss == null ? "nhat-chu" : ss >= 0 ? "tang" : "giam")}>{ss == null ? "—" : thay_doi(ss)}</div>
            <div className="phu">tháng {ttruoc}: {fmt(truoc)}</div></div>
          <div><div className="nhan">Ngày bán nhiều nhất</div><div className="gia">{dinh && dinh[cs] ? fmt(dinh[cs]) : "—"}</div>
            <div className="phu">{dinh && dinh[cs] ? ngay(dinh.ngay) : "không có ngày nào có đơn"}</div></div>
          <div><div className="nhan">Số ngày có đơn</div><div className="gia">{so(ngayCoBan)}</div>
            <div className="phu">trên {so(n.filter(d => d.la_ngay_kd && trongMoc(d)).length)} ngày làm việc</div></div>
        </div>
        <BieuDo nhan={n.map(d => String(+d.ngay.slice(8, 10)))}
          nhan_day_du={n.map(d => `${ngay(d.ngay)}${d.la_ngay_kd ? "" : " · ngày nghỉ"}`)} cao={190} moi_nhan={n.length > 20 ? 2 : 1}
          mo_ta={`Lượng bán theo ngày của mã ${ma}, tháng ${tmoi}/${thang.slice(0, 4)}`}
          chuoi={[
            { ten: `Tháng ${ttruoc} cùng ngày`, kieu: "cot_nen", mau: "var(--do-nen)",
              gia_tri: n.map(d => theoNgay.get(+d.ngay.slice(8, 10))?.[cs] ?? null) },
            { ten: `Tháng ${tmoi}`, kieu: "cot", mau: "var(--do)",
              mau_tung_cot: n.map(d => d.la_ngay_kd ? null : "var(--chu-mo)"),
              gia_tri: n.map(d => mocNgay != null && +d.ngay.slice(8, 10) > mocNgay ? null : d[cs]) },
          ]}
          dinh_dang={v => fmt(v)} dinh_dang_truc={v => cs === "so_luong" ? soLuong(v, 0) : gon(v)}
          vach={mocNgay ? { i: mocNgay - 1, chu: "mốc dữ liệu" } : null} />
        <p className="phu sp-ghi">Cột xám = ngày nghỉ (thứ Bảy, Chủ nhật, ngày lễ — <code>mart.lich_kinh_doanh</code>). Ngày không có phiếu là 0. Bấm một tháng ở "Xu hướng theo tháng" bên dưới để xem tháng đó.</p>
      </>}
    </section>
  );
}

function XuHuong({ h, chon, datThang }: { h: HoSoSpApi["h"]; chon: string | null; datThang: (t: string) => void }) {
  if (!h.thang.length) return null;
  const i = chon ? h.thang.findIndex(t => t.thang === chon) : -1;
  return (
    <section className="kh-the sp-xu-huong">
      <div className="kh-the-dau"><h2>Xu hướng theo tháng</h2>
        <span className="kh-the-goc nhat-chu">{thang_nhan(h.thang[0].thang)} → {thang_nhan(h.thang[h.thang.length - 1].thang)} · bấm một tháng để xem theo ngày</span></div>
      <BieuDo nhan={h.thang.map(t => thang_nhan(t.thang))} nhan_day_du={h.thang.map(t => `Tháng ${+t.thang.slice(5)}/${t.thang.slice(0, 4)}`)} cao={180}
        mo_ta="Doanh thu và lãi gộp theo tháng của mã này" onBam={k => datThang(h.thang[k].thang)}
        chuoi={[
          { ten: "Doanh thu", kieu: "cot", mau: "var(--lien-ket)", mau_tung_cot: h.thang.map((_, k) => k === i ? "var(--do)" : null),
            gia_tri: h.thang.map(t => t.doanh_thu == null ? null : Number(t.doanh_thu)) },
          { ten: "Lãi gộp", kieu: "duong", mau: "var(--ok-vien)", gia_tri: h.thang.map(t => t.lai_gop == null ? null : Number(t.lai_gop)) },
          { ten: "Số lượng", kieu: "duong_dut", mau: "var(--canh-vien)", truc_phai: true, an_mac_dinh: true,
            gia_tri: h.thang.map(t => t.so_luong == null ? null : Number(t.so_luong)) },
        ]}
        dinh_dang={(v, c) => c.ten === "Số lượng" ? soLuong(v) : yen(v)} dinh_dang_truc={v => gon(v)} />
    </section>
  );
}
