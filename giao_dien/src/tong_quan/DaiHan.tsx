// Dải thời gian lô sắp hết hạn (đặc tả 2026-09-28-tong-quan-it-chu-design.md §5): trục ngang =
// số ngày còn tới hạn (vùng quá hạn · 0–30 · 30–60 · 60+), mỗi lô một chấm, cỡ ∝ √giá trị tồn.
// Chấm là HTML (ONoi) chứ không phải SVG — ô nổi / liên kết / bàn phím dùng chung một linh kiện.
import { DongNoi, ONoi } from "../chung/ONoi";
import { ngay, so, yen } from "../dinh_dang";
import { banKinh, mienHan, xHan } from "./han_logic";

export type Lo = { ma: string; ten: string; kho: string; ten_kho: string | null; han: string; con_lai: number; so_luong: number; gia_tri: number };

const xuLy = (c: number): [string, string] =>
  c < 0 ? ["Quá hạn — xử lý", "var(--do)"] : c < 30 ? ["Xả hàng ngay", "var(--do)"] : c < 60 ? ["Chào ưu tiên", "var(--lien-ket)"] : ["Theo dõi", "var(--chu-mo)"];

export function DaiHan({ lo }: { lo: Lo[] }) {
  const m = mienHan(lo.map(x => x.con_lai));
  const maxGT = Math.max(0, ...lo.map(x => x.gia_tri));
  const pc = (c: number) => `${xHan(c, m) * 100}%`;
  const vung = [[m.tu, 0, "dh-qua"], [0, 30, "dh-30"], [30, 60, "dh-60"], [60, m.den, "dh-xa"]] as const;
  return (
    <div className="dh">
      <div className="dh-ray">
        {vung.map(([a, b, lop]) => <div key={lop} className={"dh-vung " + lop} style={{ left: pc(a), width: `calc(${pc(b)} - ${pc(a)})` }} />)}
        {lo.map((x, i) => {
          const [chu, mau] = xuLy(x.con_lai), r = banKinh(x.gia_tri, maxGT);
          return (
            <ONoi key={`${x.ma}-${x.kho}-${x.han}`} href={`/san-pham/${x.ma}`} className="dh-cham" nhan={`${x.ten}: còn ${x.con_lai} ngày`}
              style={{ left: pc(x.con_lai), top: `${18 + (i % 4) * 18}%`, width: r * 2, height: r * 2, background: mau }}
              noi_dung={<><strong>{x.ten}</strong>
                <DongNoi nhan="Mã" gia={x.ma} /><DongNoi nhan="Lô" gia={x.ten_kho || x.kho} />
                <DongNoi nhan="Hạn dùng" gia={ngay(x.han)} /><DongNoi nhan="Còn lại" gia={`${x.con_lai} ngày`} />
                <DongNoi nhan="Tồn" gia={so(x.so_luong)} /><DongNoi nhan="Giá trị tồn" gia={yen(x.gia_tri)} />
                <DongNoi mau={mau} nhan="Xử lý" gia={chu} /></>}><span /></ONoi>);
        })}
      </div>
      <div className="dh-truc">
        {[0, 30, 60, 90].filter(c => c >= m.tu && c <= m.den).map(c => <span key={c} style={{ left: pc(c) }}>{c === 0 ? "hạn" : `${c} ngày`}</span>)}
      </div>
    </div>
  );
}
