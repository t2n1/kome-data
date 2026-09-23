// Cài đặt (màn 21, Cài đặt.dc.html): danh mục mục bên trái, nội dung bên phải.
// CHỈ dựng những mục có thứ thật đằng sau (xem đặc tả màn 20/21):
//   * Người dùng & phân quyền — đổi ba cờ (chỉ người có duoc_quan_tri; máy
//     chưa bật đăng nhập thì từ chối). Biểu mẫu POST /cai-dat/quyen/{id} THẬT,
//     không nhận mật khẩu bao giờ — tạo tài khoản / mật khẩu chỉ bằng script.
//   * Ngân sách & ngày nghỉ, Quy tắc khách hàng, Nguồn, Hiển thị — đọc, trỏ về nơi thật.
// Không có "tính năng bật/tắt", "kênh thông báo" của prototype: một công tắc
// không nối vào đâu là nói dối người bấm.
import { KD } from "../khoi_dau";
import "./he_thong.css";

type Nguoi = { id: number; ten_dang_nhap: string; salesperson_code: string | null; ten_sale: string | null } & Record<string, unknown>;
type Man = {
  nguoi_dung: Nguoi[]; ngay_le: [string, string][]; co_cong: boolean; duoc_sua: boolean;
  co_quyen: [string, string][]; muc: [string, string, string, string][]; loi: string; xong: string;
};

const CHE_DO = [["sang", "Sáng"], ["toi", "Tối"], ["he-thong", "Theo hệ thống"], ["theo-gio", "Theo giờ"]] as const;

export default function CaiDat() {
  const m = KD.man as Man;
  const toi = KD.nguoi?.id;
  return (
    <div className="ht">
      <h1>Cài đặt</h1>
      <p className="ghi-chu">Mọi thay đổi ở đây được ghi vào <a href="/nhat-ky?loai=quyen">Nhật ký thao tác</a>.</p>
      {m.loi && <p className="ngay-thieu" role="alert">{m.loi}</p>}
      {m.xong && <p className="backup-ok" role="status">{m.xong}</p>}
      <div className="cai-dat tai-lieu">
        <nav className="muc-cd" aria-label="Các mục cài đặt">
          {m.muc.map(([ma, ten, ja, mo_ta]) => (
            <a key={ma} href={"#" + ma}><strong>{ten}</strong><span className="khong-ap-dung">{ja}</span><span className="mo-cd">{mo_ta}</span></a>))}
        </nav>
        <div className="noi-dung-cd">
          <section id="nguoi-dung" className="the-cd">
            <h2>Người dùng &amp; phân quyền <span className="khong-ap-dung">ユーザー管理</span></h2>
            {!m.co_cong ? <p className="ngay-thieu tai-lieu">Máy này chưa bật đăng nhập (<code>KOME_SESSION_SECRET</code> trống) — ai mở được
              trang cũng làm được mọi thứ, nên ba cờ bên dưới chưa bảo vệ được gì. Xem <code>docs/runbook.md</code>, mục "Bật đăng nhập trên máy
              trong công ty".</p>
              : !m.duoc_sua && <p className="ghi-chu">Bạn xem được danh sách nhưng không đổi được quyền — cần cờ <strong>quản trị</strong>.</p>}
            <div className="bang-cuon"><table>
              <thead><tr><th>Tài khoản</th><th>Phụ trách khách</th>{m.co_quyen.map(([co, nhan]) => <th key={co}>{nhan}</th>)}<th /></tr></thead>
              <tbody>
                {m.nguoi_dung.map(n => (
                  <tr key={n.id}>
                    <td><strong>{n.ten_dang_nhap}</strong>{n.id === toi && <> <span className="vien nhat">bạn</span></>}
                      {/* form rỗng; ô tích ở từng cột trỏ về nó bằng thuộc tính form= (HTML5) — mỗi ô nằm ĐÚNG cột tiêu đề của nó. */}
                      <form id={"q" + n.id} method="post" action={`/cai-dat/quyen/${n.id}`} /></td>
                    <td>{n.ten_sale || (n.salesperson_code ? "mã " + n.salesperson_code : "— (thấy toàn công ty)")}</td>
                    {m.co_quyen.map(([co, nhan]) => (
                      <td key={co}><label className="o-quyen">
                        <input type="checkbox" form={"q" + n.id} name={co} value="1" defaultChecked={!!n[co]} disabled={!m.duoc_sua} />{" "}
                        <span className="sr">{nhan} cho {n.ten_dang_nhap}</span><span aria-hidden="true">{n[co] ? "có" : "—"}</span></label></td>))}
                    <td>{m.duoc_sua && <button type="submit" form={"q" + n.id} className="nut-nap">Lưu</button>}</td>
                  </tr>))}
                {!m.nguoi_dung.length && <tr><td colSpan={6} className="khong-ap-dung">Chưa có tài khoản nào — tạo bằng <code>python scripts/tao_nguoi_dung.py them &lt;tên&gt;</code>.</td></tr>}
              </tbody>
            </table></div>
            <p className="ghi-chu"><strong>Kho dữ liệu</strong> = nạp file và bấm Hoàn tác (xoá được cả một tháng doanh thu) ·{" "}
              <strong>Ngân sách</strong> = đặt chỉ tiêu cả công ty · <strong>Quản trị</strong> = đổi ba cờ này của người khác.
              Tạo tài khoản, đổi mật khẩu: <code>python scripts/tao_nguoi_dung.py</code> (không làm trên web).
              Lọc "khách của tôi" là mặc định tiện dụng, không phải hàng rào — ai cũng xem được mọi khách.</p>
          </section>
          <section id="ngan-sach" className="the-cd">
            <h2>Ngân sách &amp; ngày nghỉ <span className="khong-ap-dung">予算設定</span></h2>
            <p>Chỉ tiêu doanh thu 5 người × 12 tháng đặt ở <a href="/ngan-sach">màn Ngân sách</a>.</p>
            <h3>Ngày lễ quốc gia sắp tới</h3>
            <p className="ghi-chu">Đã trừ khỏi "ngày làm việc" ở mọi chỗ (tiến độ ngân sách, dự báo, ngày thiếu dữ liệu). Ngày nghỉ riêng
              của công ty (Obon, 年末年始) CHƯA có — không có nguồn nào để đọc.</p>
            <ul className="ngay-le">
              {m.ngay_le.map(([d, ten]) => <li key={d}><span className="so">{d.slice(8, 10)}/{d.slice(5, 7)}/{d.slice(0, 4)}</span> {ten}</li>)}
              {!m.ngay_le.length && <li className="khong-ap-dung">Không có ngày lễ nào trong dải lịch.</li>}
            </ul>
          </section>
          <section id="quy-tac" className="the-cd">
            <h2>Quy tắc khách hàng <span className="khong-ap-dung">ランク管理</span></h2>
            <p className="ghi-chu">Định nghĩa nằm trong <code>mart</code> (một khái niệm, một công thức) — đổi nó là một migration, không phải một ô nhập.</p>
            <ul>
              <li><strong>Nhịp mua</strong> = trung vị khoảng cách giữa các lần mua của CHÍNH khách đó (cần ≥ 3 lần mua).</li>
              <li><strong>Quá hạn mua lại</strong> khi im lặng ≥ 2 lần nhịp · <strong>lâu không mua</strong> khi ≥ 4 lần · <strong>sắp đến hạn</strong> khi 1–2 lần.</li>
              <li><strong>Hạng</strong> tính theo doanh thu 12 tháng của ta, KHÔNG phải 得意先ランク của OBC.</li>
              <li><strong>Mua đều, tháng này chưa</strong> = có đơn đến cùng ngày ở ≥ 2 trong 3 tháng trước mà tháng này chưa.</li>
              <li>Khách OBC đánh dấu ※廃業※ / ※取引停止※ không bao giờ vào danh sách gọi lại.</li>
            </ul>
          </section>
          <section id="nguon" className="the-cd">
            <h2>Nguồn dữ liệu &amp; đồng bộ <span className="khong-ap-dung">データ連携</span></h2>
            <p>3 file hằng ngày lúc 13:30, đối soát lại cả tháng trước vào đầu tháng. Bảng nguồn, khoá, 5 cổng kiểm và ngưỡng:{" "}
              <a href="/kho-du-lieu/luong">Sơ đồ luồng</a> · <a href="/kho-du-lieu/cot-noi">Cột nối</a>.</p>
          </section>
          <section id="hien-thi" className="the-cd">
            <h2>Hiển thị <span className="khong-ap-dung">表示設定</span></h2>
            <nav className="loc" aria-label="Giao diện">
              {CHE_DO.map(([ma, nhan]) => (
                <a key={ma} href={`/giao-dien?che_do=${ma}`} className={KD.che_do_giao_dien === ma ? "dang-xem" : undefined}
                  aria-current={KD.che_do_giao_dien === ma ? "true" : undefined}>{nhan}</a>))}
            </nav>
            <p className="ghi-chu">Lưu trong cookie của trình duyệt này. Tiền in dạng ¥1.234.567 (chấm ngăn nghìn); kỳ kế toán của công ty chạy
              1/8 → 31/7 (kỳ 2026 = 8/2025 → 7/2026).</p>
          </section>
        </div>
      </div>
    </div>
  );
}
