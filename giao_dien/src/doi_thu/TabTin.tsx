// Tab "Tin thị trường" (đợt 4b task 8; bản phác ca-trang-8.html tab Tin thị trường): đối thủ đang hết hàng KOME có ·
// khuyến mãi đang chạy gom theo bên · tin hiện trường 30 ngày. Một query, CHUNG key với Tóm tắt / Đối thủ
// (["doi-thu","tong-quan",kx]). Luật ở tom_tat_logic.ts (coHoi, kmGomBen); ở đây chỉ vẽ + nối.
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { lay } from "../api";
import { HinhMa } from "../chung/HinhMa";
import { Khoi } from "../chung/Khoi";
import { so, yen } from "../dinh_dang";
import { chuoiKhoang, useKhoang } from "../khung/khoang";
import type { TongQuan } from "./kieu";
import { SuaMatHang } from "./SuaMatHang";
import { coHoi, kmGomBen } from "./tom_tat_logic";

type Sua = { nguon: "nap" | "tay"; id: number; tru_o?: string };
const KM_DAU = 4;   // số dòng khuyến mãi hiện sẵn mỗi bên

/** Danh sách thanh ngang đếm (tên · thanh · số). `bam` có thì mỗi dòng là nút. Dùng chung tab Đối thủ (ngành) và Tin. */
export function ThanhDem({ ds, bam, nhan }: {
  ds: { khoa: string; ten: string; so: number }[]; bam?: (khoa: string) => void; nhan?: (x: { ten: string; so: number }) => string;
}) {
  const lon = Math.max(1, ...ds.map(x => x.so));
  return (
    <ul className="dt-dem">{ds.map(x => {
      const than = <><span>{x.ten}</span><span className="dt-dem-o"><i style={{ width: `${100 * x.so / lon}%` }} /></span><b>{so(x.so)}</b></>;
      return <li key={x.khoa}>{bam
        ? <button type="button" onClick={() => bam(x.khoa)} aria-label={nhan?.(x)}>{than}</button>
        : <div>{than}</div>}</li>;
    })}</ul>
  );
}

export function TabTin({ moBen, moSoSanh }: { moBen: (ma: string) => void; moSoSanh: (sp: string[]) => void }) {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "tong-quan", kx],
    queryFn: () => lay<TongQuan>(`/api/doi-thu/tong-quan${kx ? "?" + kx : ""}`) });
  const tq = q.data, loi = q.error ? (q.error as Error).message : null;
  const [sua, datSua] = useState<Sua | null>(null);
  const [moRong, datMoRong] = useState<Set<string>>(() => new Set());
  const moSua = (x: { nguon: string; id: number }, tru_o?: string) => datSua({ nguon: x.nguon as Sua["nguon"], id: x.id, tru_o });
  const ch = useMemo(() => (tq ? coHoi(tq, 16) : []), [tq]);
  const km = useMemo(() => (tq ? kmGomBen(tq) : []), [tq]);
  const ht = tq?.hien_truong;

  return (
    <div className="dt-tt dt-tin">
      <section className="dt-khoi">
        <Khoi tieu_de="Đối thủ đang hết hàng KOME có" dang_tai={q.isLoading} loi={loi}
          cach_tinh="Theo bảng giá mới nhất của từng bên: mặt hàng ghép được với mã KOME mà bên đó ghi hết hàng (không tính 'sắp về'). Xếp theo số bên đang hết; 16 mã đầu. Bấm tên bên để sửa dòng đó.">
          {ch.length === 0 ? <p className="dt-nhat">Không bên nào đang hết hàng KOME có.</p> : (
            <div className="dt-tt-chs">{ch.map(c => (
              <div key={c.ma_kome} className="dt-tt-ch">
                <HinhMa ma={c.ma_kome} ten={c.ten} co={64} trang_tri />
                <b className="dt-tt-ten">{c.ten}</b>
                <small>{c.ma_kome} · <span className="c-vang">{so(c.ben.length)} bên đang hết</span></small>
                <div>{c.ben.map(b => (
                  <button key={b.ma} type="button" className="dt-tt-chip" aria-label={`Sửa: ${b.ten} đang hết ${c.ten}`}
                    onClick={() => moSua(b)}>{b.ten} ✎</button>))}</div>
              </div>))}</div>)}
        </Khoi>
      </section>

      <section className="dt-khoi">
        <Khoi tieu_de="Khuyến mãi đang chạy" dang_tai={q.isLoading} loi={loi}
          phu={tq && tq.khuyen_mai.length > 0 ? `${so(tq.khuyen_mai.length)} khuyến mãi · ${so(km.length)} bên` : undefined}
          cach_tinh="Dòng có ghi chú khuyến mãi hoặc giá trước khuyến mãi trong bảng giá hiện hành, gom theo bên (nhiều trước). Trong mỗi bên: giảm giá nhiều nhất theo % trước. Bấm dòng để sửa.">
          {km.length === 0 ? <p className="dt-nhat">Không có khuyến mãi nào trong bảng giá hiện hành.</p> : (
            <div className="dt-tin-kms">{km.map(b => {
              const mo = moRong.has(b.ma), ds = mo ? b.ds : b.ds.slice(0, KM_DAU), con = b.ds.length - KM_DAU;
              return (
                <div key={b.ma} className="dt-tin-km">
                  <div className="dt-tin-km-dau">
                    <button type="button" className="dt-tt-ten" onClick={() => moBen(b.ma)} aria-label={`Hồ sơ ${b.ten}`}>{b.ten}</button>
                    <span>{so(b.ds.length)} khuyến mãi</span></div>
                  {ds.map(k => (
                    <button key={`${k.nguon}${k.id}`} type="button" className="dt-tin-km-d" onClick={() => moSua(k, k.gia_goc == null ? "gia_goc" : undefined)}
                      aria-label={`Sửa: ${b.ten} — ${k.ten_goc}`}>
                      <span>{k.ten_goc}</span>
                      <b>{k.gia_goc == null ? <span className="dt-hoi-cam" aria-label="chưa có giá">?</span> : yen(k.gia_goc)}
                        {k.gia_truoc_km != null && <> <s>{yen(k.gia_truoc_km)}</s></>}</b>
                      {k.khuyen_mai && <small>{k.khuyen_mai}</small>}
                    </button>))}
                  {con > 0 && (
                    <button type="button" className="dt-xem-them" aria-expanded={mo}
                      onClick={() => datMoRong(s => { const n = new Set(s); if (mo) n.delete(b.ma); else n.add(b.ma); return n; })}>
                      {mo ? "thu gọn ▴" : `+ ${so(con)} khuyến mãi khác ▾`}</button>)}
                </div>);
            })}</div>)}
        </Khoi>
      </section>

      <section className="dt-khoi">
        <Khoi tieu_de={`Tin hiện trường ${ht?.ngay ?? 30} ngày`} dang_tai={q.isLoading} loi={loi}
          phu={ht && ht.tong > 0 ? `${so(ht.tong)} tin` : undefined}
          cach_tinh="Từ thẻ @đối thủ / @hàng sale gõ khi ghi tiếp xúc, theo ngày thật giờ Tokyo. Mỗi đối thủ / hàng / tỉnh đếm số TIN nhắc tới nó (một tin nhắc hai lần vẫn là một). Bấm đối thủ mở hồ sơ bên; bấm hàng mở So sánh giá.">
          {!ht || ht.tong === 0 ? <p className="dt-nhat">Chưa có tin nào trong {ht?.ngay ?? 30} ngày qua.</p> : (
            <div className="dt-tin-ht">
              <div><h3>Đối thủ được nhắc</h3>
                {ht.doi_thu.length ? <ThanhDem ds={ht.doi_thu.map(x => ({ khoa: x.ma, ten: x.ten, so: x.so_tin }))} bam={moBen}
                  nhan={x => `${x.ten}: ${so(x.so)} tin — mở hồ sơ bên`} /> : <p className="dt-nhat">Không tin nào gắn thẻ đối thủ.</p>}</div>
              <div><h3>Hàng được nhắc</h3>
                {ht.nhom.length ? <ThanhDem ds={ht.nhom.map(x => ({ khoa: x.khoa, ten: x.ten ?? x.khoa, so: x.so_tin }))}
                  bam={k => moSoSanh([k])} nhan={x => `${x.ten}: ${so(x.so)} tin — mở So sánh giá`} />
                  : <p className="dt-nhat">Không tin nào gắn thẻ hàng.</p>}</div>
              <div><h3>Tỉnh của khách</h3>
                <div className="dt-tinh"><ThanhDem ds={ht.tinh.map(x => ({ khoa: x.tinh, ten: x.tinh, so: x.so_tin }))} /></div></div>
            </div>)}
        </Khoi>
      </section>

      {sua && <SuaMatHang nguon={sua.nguon} id={sua.id} tru_o={sua.tru_o} dong={() => datSua(null)} xong={() => datSua(null)} />}
    </div>
  );
}
