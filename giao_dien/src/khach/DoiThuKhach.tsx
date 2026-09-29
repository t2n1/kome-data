// Khối "Đang mua của đối thủ" ở cột trái hồ sơ 360° (đợt 2 — tin hiện trường `@`). Nguồn:
// /api/khach-hang/{mã}/doi-thu (endpoint RIÊNG — ho_so() giữ trần 8 lượt). Ẩn hẳn khi không có tin nào.
// Câu chữ dựng ở nhac.ts (dongDangMua / dongNgungMua) — không tính chỉ số nào ở đây.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../api";
import type { KhachDoiThu } from "../doi_thu/kieu";
import { The } from "./HoSoTab";
import { dongDangMua, dongNgungMua } from "./nhac";

export function DoiThuKhach({ ma }: { ma: string }) {
  const { data } = useQuery({ queryKey: ["kh-doi-thu", ma],
    queryFn: () => lay<KhachDoiThu>(`/api/khach-hang/${encodeURIComponent(ma)}/doi-thu`) });
  if (!data || (!data.tin.length && !data.ly_do_ngung.length)) return null;
  const mua = dongDangMua(data.tin);
  return (
    <The tieu_de="Đang mua của đối thủ" className="hs2-viec hs2-doi-thu"
      cach_tinh="Từ thẻ @đối thủ / @hàng trong các lần ghi tiếp xúc 90 ngày qua, tin mới nhất trước. Hàng ghép với đối thủ gắn gần nhất đứng trước nó trong câu; giá là giá khách kể.">
      <ul className="hs2-ds">
        {data.ly_do_ngung.map(l => (
          <li key={"n" + l.ma} className="ngung"><a href={`/san-pham/${encodeURIComponent(l.ma)}`}>{dongNgungMua(l)}</a></li>))}
        {mua.map(c => <li key={c}>{c}</li>)}
      </ul>
    </The>);
}
