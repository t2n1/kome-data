// Nhật ký thao tác (màn 20, Nhật ký.dc.html): tiêu đề + "⤓ Xuất CSV" → 4 ô →
// hai cột (dòng thời gian có tab loại + ô tìm | nhiều nhất 30 ngày · cần soát
// lại · quy tắc). Máy chủ tính sẵn (kome/nhat_ky.py, ĐÚNG 2 lượt hỏi) và chèn
// vào window.__KOME__.man; lọc là liên kết / biểu mẫu GET như bản trước — loại
// thao tác là của APP NÀY, không dựng "sửa giá", "duyệt ngoại lệ" của prototype.
import { KD } from "../khoi_dau";
import "./he_thong.css";

type Dong = { nguoi: string | null; icon: string; nhan: string; mau: string; khi: string; noi_dung: string; truoc_sau: [string, string] | null };
type Man = {
  ds: Dong[]; loai: string; tim: string; gioi_han: number;
  loai_ds: Record<string, [string, string, string]>;
  th: { tong: number; theo_loai: Record<string, number>; khong_ro_ai: number; theo_nguoi: [string, number][]; soat_lai: Dong[] };
};

export default function NhatKy() {
  const m = KD.man as Man;
  const q = new URLSearchParams();
  if (m.loai) q.set("loai", m.loai);
  if (m.tim) q.set("tim", m.tim);
  const lk = (loai: string) => { const p = new URLSearchParams(); if (loai) p.set("loai", loai); if (m.tim) p.set("tim", m.tim); const s = p.toString(); return "/nhat-ky" + (s ? "?" + s : ""); };
  const dinh = Math.max(1, ...m.th.theo_nguoi.map(x => x[1]));
  return (
    <div className="ht">
      <div className="tieu-de-trang"><div><h1>Nhật ký thao tác</h1>
        <div className="phu">Ai nạp dữ liệu, ai hoàn tác lô, ai sửa ngân sách, ai đổi quyền, ai ghi tiếp xúc — đọc gộp từ chính sổ của
          từng việc, không chép sang bảng thứ hai. Giữ vĩnh viễn, chỉ thêm, không sửa.</div></div>
        <a className="nut-nho" href={"/nhat-ky.csv" + (q.toString() ? "?" + q : "")}>⤓ Xuất CSV</a></div>
      <div className="o-kpi-luoi">
        <div className="o-kpi"><div className="nhan">Thao tác 30 ngày</div><div className="gia">{m.th.tong}</div><div className="dong-phu nhat-chu">mọi loại</div></div>
        <div className="o-kpi"><div className="nhan">Nạp dữ liệu</div><div className="gia">{m.th.theo_loai.nap ?? 0}</div><div className="dong-phu nhat-chu">lô trong 30 ngày</div></div>
        <div className="o-kpi"><div className="nhan">Hoàn tác lô</div><div className="gia">{m.th.theo_loai.huy ?? 0}</div><div className="dong-phu nhat-chu">xoá dữ liệu khỏi kho</div></div>
        <div className="o-kpi"><div className="nhan">Không rõ ai làm</div><div className="gia">{m.th.khong_ro_ai}</div>
          <div className="dong-phu nhat-chu">{m.th.khong_ro_ai ? "máy chưa bật đăng nhập, hoặc đổi bằng script" : "mọi thao tác đều có tên"}</div></div>
      </div>
      <div className="hai-cot-nk tai-lieu">
        <section id="dong-thoi-gian">
          <div className="tieu-de-khoi"><h2>Dòng thời gian</h2>
            <nav className="loc" aria-label="Loại thao tác">
              <a href={lk("")} className={m.loai ? undefined : "dang-xem"} aria-current={m.loai ? undefined : "true"}>Tất cả</a>
              {Object.entries(m.loai_ds).map(([k, [, nhan]]) => (
                <a key={k} href={lk(k)} className={m.loai === k ? "dang-xem" : undefined} aria-current={m.loai === k ? "true" : undefined}>{nhan}</a>))}
            </nav></div>
          <form className="o-tim" method="get" action="/nhat-ky">
            {m.loai && <input type="hidden" name="loai" value={m.loai} />}
            <input type="search" name="tim" defaultValue={m.tim} placeholder="Tìm người hoặc đối tượng…" aria-label="Tìm người hoặc đối tượng" />
            <button type="submit">Tìm</button>
          </form>
          <div className="the-nk">
            {m.ds.map((d, i) => (
              <div key={i} className="dong-tl">
                <span className={"icon-tl vien " + d.mau} aria-hidden="true">{d.icon}</span>
                <div className="than-dong">
                  <div className="dong-nk-dau"><strong>{d.nguoi ?? "(không rõ ai)"}</strong>
                    <span className={"vien " + d.mau}>{d.nhan}</span><span className="khong-ap-dung so">{d.khi}</span></div>
                  <div>{d.noi_dung}</div>
                  {d.truoc_sau && <div className="truoc-sau"><span className="truoc">{d.truoc_sau[0]}</span> <span aria-hidden="true">→</span>
                    <span className="sr">thành</span> <span className="sau">{d.truoc_sau[1]}</span></div>}
                </div>
              </div>))}
            {!m.ds.length && <div className="dong-dc khong-ap-dung">Không có thao tác nào{m.loai || m.tim ? <> khớp bộ lọc — <a href="/nhat-ky">bỏ lọc</a></> : null}.</div>}
          </div>
          <p className="ghi-chu">{m.ds.length} dòng mới nhất{m.ds.length >= m.gioi_han ? ` (giới hạn ${m.gioi_han} — xuất CSV để có đủ)` : ""}.</p>
        </section>
        <div>
          <section>
            <h2>Thao tác nhiều nhất 30 ngày</h2>
            <div className="the-nk">
              {m.th.theo_nguoi.map(([ten, so]) => (
                <div key={ten} className="dong-dc cot"><div className="dong-dc-dau"><span>{ten}</span><strong className="so">{so}</strong></div>
                  <div className="thanh-nho"><div className="thanh-nho-nen"><div style={{ width: `${(so / dinh * 100).toFixed(1)}%` }} /></div></div></div>))}
              {!m.th.theo_nguoi.length && <div className="dong-dc khong-ap-dung">Chưa có thao tác nào có tên người trong 30 ngày.</div>}
            </div>
          </section>
          <section>
            <h2 className="chu-canh">Cần soát lại</h2>
            <div className="the-nk">
              {m.th.soat_lai.map((d, i) => (
                <div key={i} className="dong-dc cot"><div><strong>{d.nguoi ?? "(không rõ ai)"}</strong> · {d.noi_dung}</div>
                  <div className="khong-ap-dung">{d.khi}{d.truoc_sau ? ` · ${d.truoc_sau[0]} → ${d.truoc_sau[1]}` : ""}</div></div>))}
              {!m.th.soat_lai.length && <div className="dong-dc khong-ap-dung">Không có lần hoàn tác lô hay đổi quyền nào trong 30 ngày.</div>}
            </div>
          </section>
          <section>
            <h2>Quy tắc ghi nhật ký</h2>
            <div className="the-nk"><div className="dong-dc cot khong-ap-dung">
              Mỗi lần nạp, hoàn tác lô, sửa chỉ tiêu, đổi quyền và ghi tiếp xúc đều ghi kèm người làm và giá trị trước–sau.
              Sổ tiếp xúc và sổ quyền bị CSDL chặn sửa/xoá; sổ ngân sách và sổ nạp chỉ được code ghi thêm (lô hoàn tác giữ nguyên dòng,
              chỉ đóng dấu thời điểm hoàn tác). "Không rõ ai" nghĩa là thao tác làm khi máy trong công ty chưa bật đăng nhập, hoặc đổi
              quyền bằng <code>scripts/tao_nguoi_dung.py</code>.
            </div></div>
          </section>
        </div>
      </div>
    </div>
  );
}
