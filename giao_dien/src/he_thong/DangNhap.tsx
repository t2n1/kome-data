// Màn Đăng nhập (Đăng nhập.dc.html): hai cột — dải đỏ giới thiệu | biểu mẫu.
// CỐ Ý không có thanh điều hướng (chưa đăng nhập thì mọi liên kết đều quay về
// đây). Biểu mẫu là <form method="post"> THẬT: gửi được cả khi JavaScript
// hỏng, và máy chủ giữ nguyên luồng cũ (303 về trang định vào / 401 khi sai).
//
// Khác gói thiết kế (đặc tả giai đoạn 5): đăng nhập bằng TÊN, không email;
// không SSO Google, không "nhớ đăng nhập" (vé cố định 12 giờ), không "quên mật
// khẩu" (đổi mật khẩu chỉ qua scripts/tao_nguoi_dung.py); không số liệu công
// ty trên trang — trang này công khai trên Internet, chưa ai đăng nhập.
import { useState } from "react";
import { KD } from "../khoi_dau";
import "./he_thong.css";

export default function DangNhap() {
  const [hien, datHien] = useState(false);
  return (
    <div className="dn">
      <section className="dn-trai" aria-hidden="true">
        <div className="dn-logo"><img src="/static/kome-logo.png" alt="" /><span>KOME</span></div>
        <h2>Hệ thống bán hàng &amp; dữ liệu KOME</h2>
        <p>Doanh thu, khách hàng, tồn kho và dự báo — đọc thẳng từ sổ OBC 奉行 mỗi ngày lúc 13:30.
          OBC là sổ cái chính thức; ở đây chỉ đọc, không sửa số.</p>
      </section>
      <section className="dn-phai">
        <div className="dn-hop">
          <h1>🔒 Đăng nhập</h1>
          <p className="phu">Mỗi người một tài khoản riêng.</p>
          {KD.dang_nhap_sai && <div className="dn-sai" role="alert">Tên đăng nhập hoặc mật khẩu không đúng.</div>}
          <form method="post" action="/dang-nhap">
            <label htmlFor="ten">Tên đăng nhập</label>
            <input id="ten" type="text" name="ten" required autoFocus autoComplete="username" />
            <label htmlFor="mk">Mật khẩu</label>
            <div className="dn-mk">
              <input id="mk" type={hien ? "text" : "password"} name="mat_khau" required autoComplete="current-password" />
              <button type="button" className="nut-nho" onClick={() => datHien(h => !h)}
                aria-pressed={hien} aria-controls="mk">{hien ? "Ẩn" : "Hiện"}</button>
            </div>
            <button type="submit" className="nut-chinh dn-vao">Vào xem</button>
          </form>
          <p className="phu dn-nho">Quên mật khẩu thì nhờ người quản trị đặt lại — không gửi mật khẩu của mình cho ai.</p>
        </div>
      </section>
    </div>
  );
}
