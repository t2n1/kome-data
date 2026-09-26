// Khối "sắp có" — chỗ dành cho nguồn CHƯA có (ảnh cửa hàng, chat Facebook).
// Hình rỗng nét đứt cho biết khối sẽ trông thế nào; KHÔNG ảnh / tin nhắn mẫu
// (không ai được tưởng là dữ liệu thật) và KHÔNG nút vô hiệu.
export function KhoiSapCo({ tieu_de, icon, hinh, cong_dung, can }: {
  tieu_de: string; icon: string; hinh: "anh" | "chat"; cong_dung: string; can: string;
}) {
  return (
    <section className="kh-the hs2-sap-co">
      <div className="kh-the-dau"><h2><span aria-hidden="true">{icon}</span> {tieu_de}</h2>
        <span className="hs2-nhan-sap-co">Chưa có nguồn</span></div>
      <div className={"hs2-hinh-rong " + hinh} aria-hidden="true">
        {hinh === "anh" ? <><i /><i /><i /></> : <><i /><i className="phai" /><i /></>}
      </div>
      <p className="hs2-cong-dung">{cong_dung}</p>
      <p className="hs2-can">Cần để bật: {can}</p>
    </section>);
}
