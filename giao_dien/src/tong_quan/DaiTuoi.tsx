// Ô "hôm nay đã có dữ liệu chưa" — chép _tuoi_du_lieu.html. Đặt TRÊN mọi con số
// và NGOÀI lưới kéo thả: nó quyết định các con số bên dưới có đáng tin không.
// Chỉ ĐỎ khi đã qua 13:30, là ngày làm việc, mà nguồn vẫn thiếu (một dải đỏ
// vĩnh viễn dạy người đọc bỏ qua dải đỏ). Màu luôn đi kèm chữ.
import { KD } from "../khoi_dau";
import { ngay } from "../dinh_dang";

type Nguon = { spec: string; ten: string; ngay: string | null; trang_thai: "xanh" | "cho" | "do" | "nghi"; tre: number | null };
type Tuoi = { hom_nay: string; co_thieu: boolean; nguon: Nguon[] };

export function DaiTuoi() {
  const t = (KD as unknown as { tuoi?: Tuoi | null }).tuoi;
  if (!t || !t.nguon.length) return null;
  const thieu = t.nguon.filter(n => n.trang_thai === "do");
  const cho = t.nguon.filter(n => n.trang_thai === "cho");
  const hn = ngay(t.hom_nay);
  if (t.nguon[0].trang_thai === "nghi")
    return <div className="tuoi im">🛌 Hôm nay ({hn}) là ngày nghỉ — không cần xuất file.</div>;
  if (thieu.length)
    return (
      <div className="tuoi do" role="alert">
        <strong>⚠️ Chưa có dữ liệu hôm nay ({hn})</strong>
        <ul>{thieu.map(n => <li key={n.spec}><strong>{n.ten}</strong> — {n.ngay
          ? <>mới có đến {ngay(n.ngay)}{n.tre ? ` (trễ ${n.tre} ngày làm việc)` : ""}</> : "chưa nạp lần nào"}</li>)}</ul>
        <p>Xuất {thieu.length} file trên từ OBC (đặt tên đúng mẫu <code>&lt;tên&gt;_{t.hom_nay.replace(/-/g, "")}.xlsx</code>)
          rồi kéo–thả vào {KD.hien_kho ? <a href="/kho-du-lieu">trang nạp</a> : "trang nạp"}.</p>
      </div>
    );
  if (cho.length)
    return <div className="tuoi im">🕐 Chưa tới giờ xuất file (13:30) — còn thiếu {cho.map((n, i) =>
      <span key={n.spec}><strong>{n.ten}</strong>{i < cho.length - 1 ? ", " : ""}</span>)}.</div>;
  return <div className="tuoi du">✅ Cả {t.nguon.length} nguồn đã có dữ liệu hôm nay ({hn}).</div>;
}
