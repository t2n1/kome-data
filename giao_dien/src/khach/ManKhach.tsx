// Màn "Khách hàng" (Customer 360.dc.html — màn tong_quan): hai tab Danh sách /
// Bản đồ trên CÙNG một trạng thái lọc (./loc.ts). /khach-hang và /ban-do là
// hai địa chỉ của màn này; đổi tab là pushState, không tải lại trang.
import { BanDo } from "./BanDo";
import { DanhSach } from "./DanhSach";
import { useBoLoc } from "./loc";
import "./khach.css";

export default function ManKhach() {
  const { tab, b, dat } = useBoLoc();
  return (
    <div className="kh">
      <div className="tieu-de-trang">
        <div><h1>Khách hàng</h1>
          <div className="phu">Danh bạ khách mua hàng · bấm một dòng để mở hồ sơ 360° · việc gọi lại nằm ở{" "}
            <a href="/lien-he">Cần liên hệ</a></div></div>
      </div>
      <div className="kh-tab" role="tablist" aria-label="Cách xem">
        <button type="button" role="tab" aria-selected={tab === "danh_sach"} onClick={() => dat({ tab: "danh_sach" }, true)}>Danh sách khách</button>
        <button type="button" role="tab" aria-selected={tab === "ban_do"} onClick={() => dat({ tab: "ban_do" }, true)}>Bản đồ</button>
      </div>
      {tab === "danh_sach" ? <DanhSach b={b} dat={dat} /> : <BanDo b={b} dat={dat} />}
    </div>
  );
}
