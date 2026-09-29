// Cột trái Sản phẩm 360: "Đối thủ bán nhóm này" (đặc tả Thị trường & đối thủ §5.5). 1 lượt hỏi, endpoint riêng
// (/api/san-pham/{mã}/doi-thu) — ngoài trần 5 của hồ sơ. queryKey bắt đầu bằng "doi-thu" để sau khi duyệt / sửa
// ở màn /doi-thu (invalidateQueries({queryKey: ["doi-thu"]})) khối này cũng được tải lại.
import { useQuery } from "@tanstack/react-query";
import { lay } from "../../api";
import { yen } from "../../dinh_dang";
import { The } from "../../khach/HoSoTab";
import { chuoiKhoang, giuKhoang, useKhoang } from "../../khung/khoang";
import type { Nhom } from "../../doi_thu/kieu";
import { viTriKome } from "../../doi_thu/loc";

export function KhoiDoiThu({ ma }: { ma: string }) {
  const kx = chuoiKhoang(useKhoang());
  const q = useQuery({ queryKey: ["doi-thu", "san-pham", ma, kx],
    queryFn: () => lay<{ nhom: Nhom | null }>(`/api/san-pham/${encodeURIComponent(ma)}/doi-thu${kx ? "?" + kx : ""}`) });
  const n = q.data?.nhom;
  if (!n) return null;
  const vt = viTriKome(n);
  return (
    <The tieu_de="Đối thủ bán nhóm này" className="hs2-viec"
      goc={<span className="phu">{n.so_ben} bên</span>}>
      <p className="phu">Thấp nhất {yen(n.thap_nhat)}/kg ({n.ben_thap_nhat}) · trung vị {yen(n.trung_vi)}/kg</p>
      <p>KOME {n.gia_kome != null ? `${yen(n.gia_kome)}/kg` : "—"}{vt ? ` · ${vt}` : ""}</p>
      <a className="hs2-lien-ket" href={giuKhoang(`/doi-thu?tab=so_sanh&nhom=${encodeURIComponent(n.nhom_khoa)}`)}>Xem so sánh ›</a>
    </The>);
}
