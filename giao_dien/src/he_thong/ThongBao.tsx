// Trang thông báo của máy chủ, vẽ trong khung chung (thanh bên còn nguyên — nó
// là lối ra duy nhất của trang lỗi). Máy chủ chọn loại và mã HTTP
// (kome/web/app.py::_thong_bao): 500 lỗi ngoài dự kiến, 403 không có quyền /
// bản chỉ-đọc. Chuỗi ngoại lệ gốc KHÔNG BAO GIỜ tới đây — chỉ nằm trong nhật ký
// máy chủ. Ba màn bị từ chối vì ba lý do khác nhau, nên ba câu khác nhau.
import { KD } from "../khoi_dau";
import "./he_thong.css";

export default function ThongBao() {
  const tb = KD.thong_bao!;
  const ten = KD.nguoi?.ten_dang_nhap;
  if (tb.loai === "loi") return (
    <div className="tb loi-hop">
      <h1>❌ Hệ thống gặp lỗi khi {tb.viec}</h1>
      <p><strong>Dữ liệu chưa được nạp.</strong> Lần nạp vừa rồi đã được huỷ hoàn toàn, không có gì nửa vời nằm lại trong cơ sở dữ liệu.</p>
      <p>Hãy làm theo thứ tự:</p>
      <ol>
        <li>Chụp lại <strong>toàn bộ màn hình này</strong>.</li>
        <li>Gửi ảnh chụp kèm file Excel vừa kéo–thả cho người phụ trách kỹ thuật.</li>
        <li><strong>Đừng thử nạp lại nhiều lần</strong> — thử lại không làm hết lỗi.</li>
      </ol>
    </div>);
  if (tb.loai === "chi_doc") return (
    <div className="tb ngay-thieu">
      <h1>👀 Bản này chỉ để xem</h1>
      <p>Việc <strong>nạp dữ liệu</strong> và <strong>hoàn tác</strong> chỉ làm được ở bản chạy trên <strong>máy trong công ty</strong>, không làm được ở đây.</p>
      <p>Không phải vì thiếu quyền, mà vì máy chủ công khai không làm nổi:</p>
      <ul>
        <li>Mỗi lần gửi bị chặn ở <strong>4,5 MB</strong>, trong khi một file <code>売上伝票データ</code> nặng khoảng <strong>100 MB</strong>.</li>
        <li>Ổ đĩa ở đây là <strong>tạm</strong> — ghi xong là mất, nên không giữ được bản gốc file Excel như quy định.</li>
      </ul>
      <p>Hãy mở trang nạp dữ liệu trên máy trong công ty rồi kéo–thả file ở đó. Sau đó quay lại đây bấm <a href="/kho-du-lieu">Kho dữ liệu</a> để xem kết quả.</p>
    </div>);
  if (tb.loai === "cam_kho_du_lieu") return (
    <div className="tb ngay-thieu">
      <h1>🔐 Bạn không có quyền vào Kho dữ liệu</h1>
      <p>Màn <strong>Kho dữ liệu</strong> là nơi nạp file từ OBC và <strong>hoàn tác</strong> một lần nạp — thao tác xoá được cả một
        tháng doanh thu khỏi kho nếu bấm nhầm lô. Vì vậy nó chỉ mở cho người phụ trách nạp dữ liệu và chủ doanh nghiệp.</p>
      <p>Cần vào đây để làm việc? Nhờ người quản trị cấp quyền cho tài khoản {ten && <strong>{ten}</strong>}.</p>
      <p>Mọi số liệu bán hàng, khách hàng và báo cáo vẫn xem được bình thường:{" "}
        <a href="/">Tổng quan</a> · <a href="/khach-hang">Khách hàng</a> · <a href="/bao-cao">Báo cáo doanh thu</a>.</p>
    </div>);
  if (tb.loai === "cam_ngan_sach") return (
    <div className="tb ngay-thieu">
      <h1>🔐 Bạn không có quyền sửa Ngân sách</h1>
      <p>Màn <strong>Ngân sách</strong> là nơi đặt chỉ tiêu doanh thu cho từng nhân viên từng tháng. Con số đó là thước đo mà cả
        công ty được đánh giá theo, nên nó chỉ mở cho chủ doanh nghiệp.</p>
      <p>Cần đặt hoặc sửa chỉ tiêu? Nhờ người quản trị cấp quyền cho tài khoản {ten && <strong>{ten}</strong>}.</p>
      <p>Tiến độ so với chỉ tiêu vẫn xem được bình thường ở <a href="/bao-cao">Báo cáo doanh thu</a>.</p>
    </div>);
  // cam_cai_dat
  return (
    <div className="tb ngay-thieu">
      <h1>🔐 Bạn không có quyền đổi quyền của người khác</h1>
      <p>Ba cờ trên màn <strong>Cài đặt</strong> quyết định ai được nạp và hoàn tác dữ liệu (nút xoá được cả một tháng doanh thu) và
        ai được sửa ngân sách, nên chỉ người có cờ <strong>quản trị</strong> đổi được.</p>
      <p>Cần đổi? Nhờ người quản trị, hoặc chủ doanh nghiệp chạy{" "}
        <code>python scripts/tao_nguoi_dung.py quyen {ten ?? "<tên>"} --quan-tri</code>.</p>
      <p><a href="/cai-dat">← Quay lại Cài đặt</a></p>
    </div>);
}
