// Dự báo doanh thu (/du-bao) — bố cục Dự báo.dc.html: Chốt tháng (4 ô + đường
// luỹ kế + theo người phụ trách) → 12 tháng tới (3 kịch bản) → Đơn kỳ vọng 14
// ngày | Nguy cơ ngừng mua → Dự báo đã chuẩn tới đâu. Mọi con số + hình học từ
// /api/du-bao (kome/du_bao.py, kome/ve_du_bao.py). Lệch có chủ ý so với gói
// thiết kế (bất biến đợt 8): KHÔNG "% chắc chắn" / "% nguy cơ" — không đo được;
// khoảng thấp–cao là sai số thật của chính cách tính, không hệ số cố định.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { lay } from "../api";
import { giuKhoang } from "../khung/khoang";
import { ngay, yen } from "../dinh_dang";
import "./du_bao.css";

type Kiem = { thang: string; du_bao: number; thuc_te: number; lech: number | null };
type Chot = { thang: string; hom_nay: string; da_ban: number; e: number; n: number; co_so: number; thap: number | null;
  cao: number | null; kiem: Kiem[]; moc_kiem: number; ngan_sach: number | null; xong: boolean; so_ngan_sach: number | null };
type ThangDb = { thang: string; co_so: number; thap: number; cao: number; cung_ky: number };
type Nam = { lich_su: [string, number][]; du_bao: ThangDb[]; he_so: number | null; he_so_thap: number | null;
  he_so_cao: number | null; doi_chieu: string[]; tong_cung_ky: number; tong_12_qua: number };
type Nguoi = { ma: string; ten: string | null; da_ban: number; co_so: number; ngan_sach: number | null; tien_do: number | null };
type KyVong = { ma: string; ten: string; du_kien: string; gia_tri: number; dung_nhip: number; so_khoang: number; do_deu: number | null };
type NguyCo = { ma: string; ten: string; so_ngay_im_lang: number; ty_le: number; doanh_thu: number; trang_thai: string };
type Truc = { y: number; nhan: string };
type VeChot = { co: boolean; rong: number; cao: number; trai: number; phai: number; truc: Truc[]; dai?: string; ns?: string;
  cao_?: string; thap?: string; cs?: string; tt: string; x_nay: number; y_nay: number; x_cuoi: number; y_cuoi: number;
  day_truc: number; nhan_ngay: { x: number; nhan: string }[] };
type VeNam = { co: boolean; rong: number; cao: number; trai: number; phai: number; truc: Truc[];
  cot: { x: number; y: number; w: number; h: number; loai: string; chu: string }[]; rau: { x: number; y1: number; y2: number }[];
  nhan: { x: number; nhan: string }[]; x_chia: number | null; day_truc: number };
type DuBaoApi = {
  db: null | { chot: Chot | null; nam: Nam; nguoi: Nguoi[];
    kh: { ky_vong: KyVong[]; so_ky_vong: number; tong_ky_vong: number; nguy_co: NguyCo[]; so_nguy_co: number; tien_nguy_co: number } };
  kich_ban: Record<string, string>; tong: Record<string, number>; theo: Record<string, number[]>;
  ve_chot: VeChot; ve_nam: Record<string, VeNam> | null;
};

const pct = (v: number) => (v >= 0 ? "+" : "") + (v * 100).toFixed(1).replace(".", ",") + "%";
const tNhan = (t: string) => `${t.slice(5)}/${t.slice(0, 4)}`;

export default function DuBao() {
  const [kb, datKb] = useState(() => new URLSearchParams(location.search).get("kb") ?? "cs");
  const { data: d, error } = useQuery<DuBaoApi>({ queryKey: ["du-bao"], queryFn: () => lay<DuBaoApi>("/api/du-bao") });
  const chonKb = (k: string) => { datKb(k); history.replaceState(null, "", giuKhoang(k === "cs" ? "/du-bao" : `/du-bao?kb=${k}`)); };

  if (error) return <div className="khoi-loi">Không tải được dự báo: {(error as Error).message}</div>;
  if (!d) return <div className="khoi-cho" aria-busy="true"><span /><span /><span /></div>;
  if (!d.db) return <><h1>Dự báo doanh thu</h1><div className="trong">Chưa có dòng bán nào — chưa có gì để dự báo.</div></>;
  const { chot: c, nam: m, nguoi, kh } = d.db;
  // Kịch bản lạ trên URL (?kb=...) rơi về "cơ sở" cho MỌI ô — không để biểu
  // đồ vẽ cơ sở trong khi các ô số in ¥0 cho một kịch bản không tồn tại.
  const kbD = kb in d.kich_ban ? kb : "cs";
  const g = d.ve_chot, b = d.ve_nam?.[kbD];
  const tong = d.tong[kbD], theo = d.theo[kbD];
  const iDinh = m.du_bao.reduce((bi, t, i, a) => (t.co_so > a[bi].co_so ? i : bi), 0);
  const heSo = kbD === "thap" ? m.he_so_thap : kbD === "cao" ? m.he_so_cao : m.he_so;
  const to = Math.max(...nguoi.map(s => s.co_so), ...nguoi.map(s => s.ngan_sach ?? 0), 1);

  return (
    <div className="db">
      <div className="tieu-de-trang"><div><h1>Dự báo doanh thu</h1>
        <div className="phu">Toàn công ty, tính từ dữ liệu bán tới <b>{c ? ngay(c.hom_nay) : "—"}</b> (ngày bán mới nhất trong kho). Ba cách tính
          đều giải thích được bằng một câu — đọc ở chân từng khối. Ngày làm việc đã trừ thứ Bảy, Chủ nhật và ngày lễ quốc gia Nhật
          (chưa trừ ngày nghỉ riêng của công ty).</div></div></div>

      {c && <section id="chot-thang">
        <div className="tieu-de-khoi"><h2>Chốt tháng {tNhan(c.thang)}</h2>
          <span className="khong-ap-dung">{c.e}/{c.n} ngày làm việc đã qua{c.xong ? " — tháng đã đủ ngày" : ""}</span></div>
        <div className="the-so">
          <div><div className="nhan">Đã bán</div><div className="gia">{yen(c.da_ban)}</div><div className="nhan">tới {ngay(c.hom_nay)}</div></div>
          <div><div className="nhan">Dự báo chốt tháng (cơ sở)</div><div className="gia">{yen(c.co_so)}</div>
            <div className="nhan">{c.xong ? "= đã bán, không còn ngày nào" : `+ ${yen(c.co_so - c.da_ban)} cho ${c.n - c.e} ngày còn lại`}</div></div>
          <div><div className="nhan">Khoảng thấp – cao</div>
            <div className="gia">{c.thap != null && c.cao != null ? `${yen(c.thap)} – ${yen(c.cao)}` : "—"}</div>
            <div className="nhan">{c.thap == null ? "chưa đủ 3 tháng cũ để đo sai số" : c.xong ? "tháng đã đủ ngày" : `sai số thật trên ${c.kiem.length} tháng trước`}</div></div>
          <div><div className="nhan">So ngân sách tháng</div>
            <div className="gia">{c.ngan_sach ? `${c.co_so >= c.ngan_sach ? "+" : ""}${Math.trunc((c.co_so / c.ngan_sach - 1) * 100)}%` : "—"}</div>
            <div className="nhan">{c.ngan_sach ? <>{c.co_so >= c.ngan_sach ? yen(c.co_so - c.ngan_sach) : "thiếu " + yen(c.ngan_sach - c.co_so)} · ngân sách {yen(c.ngan_sach)}</>
              : <>chưa đặt ngân sách tháng này — <a href="/ngan-sach">đặt</a></>}</div></div>
        </div>
        {g.co && <div className="the-bieu-do">
          <svg viewBox={`0 0 ${g.rong} ${g.cao}`} width="100%" role="img" aria-label={`Doanh thu luỹ kế tháng ${c.thang}: đã bán ${yen(c.da_ban)}, dự báo chốt ${yen(c.co_so)}`}>
            {g.truc.map(t => <g key={t.y}><line x1={g.trai} y1={t.y} x2={g.phai} y2={t.y} className="luoi-truc" />
              <text x={g.trai - 8} y={t.y + 4} textAnchor="end" className="chu-truc">{t.nhan}</text></g>)}
            {g.dai && <path d={g.dai} className="dai-db" />}
            {g.ns && <polyline points={g.ns} className="duong-ns" />}
            {g.cao_ && <><polyline points={g.cao_} className="duong-bien" /><polyline points={g.thap} className="duong-bien" /></>}
            {g.cs && <polyline points={g.cs} className="duong-cs" />}
            <polyline points={g.tt} className="duong-tt" />
            <line x1={g.x_nay} y1={14} x2={g.x_nay} y2={g.day_truc} className="vach-nay" />
            <circle cx={g.x_nay} cy={g.y_nay} r={4.5} className="cham-tt"><title>Đã bán {yen(c.da_ban)} tới {ngay(c.hom_nay)}</title></circle>
            {!c.xong && <circle cx={g.x_cuoi} cy={g.y_cuoi} r={4.5} className="cham-cs"><title>Dự báo chốt {yen(c.co_so)}</title></circle>}
            {g.nhan_ngay.map(n => <text key={n.x} x={n.x} y={g.cao - 10} textAnchor="middle" className="chu-truc">{n.nhan}</text>)}
          </svg>
          <div className="chu-giai">
            <span><i className="mau" style={{ background: "var(--ok-vien)" }} />Luỹ kế thực tế</span>
            {!c.xong && <span><i className="mau" style={{ background: "var(--do)" }} />Dự báo cơ sở (nét đứt)</span>}
            {g.dai && <span><i className="mau" style={{ background: "var(--vien-dam)" }} />Khoảng thấp – cao</span>}
            {g.ns && <span><i className="mau" style={{ background: "var(--chu-mo)" }} />Nhịp ngân sách</span>}
          </div>
        </div>}
        {nguoi.length > 0 && <div className="the-bieu-do">
          <div className="ten-dc">Dự báo chốt tháng theo người phụ trách</div>
          {nguoi.map(s => (
            <div key={s.ma || "trong"} className="dong-sale">
              <div className="dong-sale-dau"><span>{s.ten || (!s.ma ? "(chưa gán người phụ trách)" : `(mã ${s.ma} không có trong danh sách phụ trách)`)}</span>
                <span className="khong-ap-dung">{yen(s.co_so)}{s.tien_do != null && <> · <strong>{Math.round(s.tien_do * 100)}% ngân sách</strong></>}</span></div>
              <div className="thanh-sale" role="img" aria-label={`Đã bán ${yen(s.da_ban)}, dự báo ${yen(s.co_so)}${s.ngan_sach ? `, ngân sách ${yen(s.ngan_sach)}` : ""}`}>
                <div className="phan-ban" style={{ width: `${Math.max(s.da_ban / to * 100, 0)}%` }} />
                <div className="phan-them" style={{ width: `${Math.max((s.co_so - s.da_ban) / to * 100, 0)}%` }} />
                {s.ngan_sach ? <div className="vach-ns" style={{ left: `${s.ngan_sach / to * 100}%` }} /> : null}
              </div>
            </div>))}
          <div className="chu-giai">
            <span><i className="mau" style={{ background: "var(--ok-vien)" }} />Đã bán</span>
            <span><i className="mau" style={{ background: "var(--do-nen)", border: "1px solid var(--do)" }} />Dự báo thêm tới cuối tháng</span>
            <span><i className="mau" style={{ background: "var(--chu)" }} />Ngân sách cá nhân</span>
          </div>
        </div>}
        <p className="ghi-chu">Cách tính: đã bán + (đã bán ÷ {c.e} ngày làm việc đã qua) × {c.n - c.e} ngày làm việc còn lại.</p>
      </section>}

      <section id="muoi-hai-thang">
        <div className="tieu-de-khoi"><h2>12 tháng tới</h2>
          {m.du_bao.length > 0 && <span className="khong-ap-dung">{tNhan(m.du_bao[0].thang)} → {tNhan(m.du_bao[m.du_bao.length - 1].thang)}</span>}
          <div className="tab-pill" role="group" aria-label="Kịch bản">
            {Object.entries(d.kich_ban).map(([k, nhan]) => <button key={k} type="button" aria-pressed={k === kbD} onClick={() => chonKb(k)}>{nhan}</button>)}
          </div></div>
        {m.du_bao.length > 0 && b ? <>
          <div className="the-so">
            <div><div className="nhan">Tổng {m.du_bao.length} tháng tới · {d.kich_ban[kbD]}</div><div className="gia">{yen(tong)}</div>
              <div className="nhan">hệ số ×{heSo != null ? heSo.toFixed(3).replace(".", ",") : "—"} so cùng kỳ</div></div>
            <div><div className="nhan">So với cùng kỳ năm trước</div><div className="gia">{m.tong_cung_ky > 0 ? pct(tong / m.tong_cung_ky - 1) : "—"}</div>
              <div className="nhan">{yen(m.tong_cung_ky)} của cùng {m.du_bao.length} tháng năm trước</div></div>
            <div><div className="nhan">Tháng cao nhất</div><div className="gia">{tNhan(m.du_bao[iDinh].thang)}</div>
              <div className="nhan">{yen(theo[iDinh])}</div></div>
          </div>
          <div className="the-bieu-do">
            <svg viewBox={`0 0 ${b.rong} ${b.cao}`} width="100%" role="img" aria-label="Doanh thu 12 tháng qua và dự báo 12 tháng tới">
              {b.truc.map(t => <g key={t.y}><line x1={b.trai} y1={t.y} x2={b.phai} y2={t.y} className="luoi-truc" />
                <text x={b.trai - 8} y={t.y + 4} textAnchor="end" className="chu-truc">{t.nhan}</text></g>)}
              {b.cot.map((c2, i) => <rect key={i} x={c2.x} y={c2.y} width={c2.w} height={c2.h} rx={3} className={"cot-" + c2.loai}><title>{c2.chu}</title></rect>)}
              {b.rau.map((r, i) => <line key={i} x1={r.x} y1={r.y1} x2={r.x} y2={r.y2} className="rau-db" />)}
              {b.x_chia != null && <><line x1={b.x_chia} y1={14} x2={b.x_chia} y2={b.day_truc} className="vach-chia" />
                <text x={b.x_chia + 6} y={26} className="chu-truc">Dự báo →</text></>}
              {b.nhan.map(n => <text key={n.x} x={n.x} y={b.cao - 10} textAnchor="middle" className="chu-truc">{n.nhan}</text>)}
            </svg>
            <div className="chu-giai">
              <span><i className="mau" style={{ background: "var(--chu-mo)" }} />Thực tế</span>
              <span><i className="mau" style={{ background: "var(--do)" }} />Dự báo theo kịch bản đang chọn</span>
              <span><i className="mau" style={{ background: "var(--canh-chu)" }} />Khoảng thận trọng – lạc quan</span>
            </div>
          </div>
          <p className="ghi-chu">Cách tính: doanh thu cùng tháng năm trước × hệ số tăng trưởng. Hệ số cơ sở = tổng {m.doi_chieu.length} tháng
            đối chiếu ({m.doi_chieu[0]} → {m.doi_chieu[m.doi_chieu.length - 1]}) ÷ tổng cùng các tháng đó năm trước; thận trọng/lạc quan là tỷ số
            tháng thấp nhất/cao nhất trong chính các tháng đó.</p>
        </> : <div className="trong">Chưa đủ dữ liệu để so cùng kỳ — cần ít nhất 13 tháng bán hàng đầy đủ.</div>}
      </section>

      <div className="hai-cot-tl">
        <section id="ky-vong">
          <div className="tieu-de-khoi"><h2>Đơn kỳ vọng 14 ngày tới</h2>
            <span className="khong-ap-dung">{kh.so_ky_vong} khách · {yen(kh.tong_ky_vong)} theo giá trị trung bình mỗi lần</span></div>
          <div className="the-nk">
            {kh.ky_vong.map(k => (
              <div key={k.ma} className="dong-dc cot">
                <div className="dong-dc-dau"><a href={`/khach-hang/${encodeURIComponent(k.ma)}`} className="ten-jp">{k.ten}</a>
                  <span className="khong-ap-dung so">{k.du_kien.slice(8, 10)}/{k.du_kien.slice(5, 7)}</span><strong className="so">{yen(k.gia_tri)}</strong></div>
                <div className="thanh-nho"><div className="thanh-nho-nen"><div style={{ width: `${((k.do_deu ?? 0) * 100).toFixed(1)}%` }} /></div>
                  <span className="khong-ap-dung">{k.dung_nhip}/{k.so_khoang} lần mua đúng nhịp</span></div>
              </div>))}
            {!kh.ky_vong.length && <div className="dong-dc khong-ap-dung">Không khách nào tới hạn mua lại trong 14 ngày tới.</div>}
          </div>
          <p className="ghi-chu">Ngày dự kiến = lần mua cuối + nhịp mua riêng (trung vị khoảng cách). "Đúng nhịp" = khoảng cách nằm trong 0,5–1,5 lần nhịp.</p>
        </section>
        <section id="nguy-co">
          <div className="tieu-de-khoi"><h2>Nguy cơ ngừng mua</h2>
            <span className="khong-ap-dung">{kh.so_nguy_co} khách · {yen(kh.tien_nguy_co)} doanh thu luỹ kế · <a href="/lien-he?tat_ca=1">gọi lại →</a></span></div>
          <div className="the-nk">
            {kh.nguy_co.map(k => (
              <div key={k.ma} className="dong-dc cot">
                <div className="dong-dc-dau"><a href={`/khach-hang/${encodeURIComponent(k.ma)}`} className="ten-jp">{k.ten}</a>
                  <span className="khong-ap-dung">im lặng {k.so_ngay_im_lang} ngày</span><strong className="so">{yen(k.doanh_thu)}</strong></div>
                <div className={"thanh-nho " + (k.trang_thai === "da_roi_bo" ? "loi" : "canh")}><div className="thanh-nho-nen">
                  <div style={{ width: `${(Math.min(k.ty_le / 4, 1) * 100).toFixed(1)}%` }} /></div>
                  <span className="khong-ap-dung">{k.ty_le.toFixed(1).replace(".", ",")}× nhịp mua riêng</span></div>
              </div>))}
            {!kh.nguy_co.length && <div className="dong-dc khong-ap-dung">Không khách nào đang im lặng quá 2 lần nhịp.</div>}
          </div>
          <p className="ghi-chu">Cùng định nghĩa "khách đang rời đi" với <a href="/lien-he?tat_ca=1">Cần liên hệ</a>, xếp theo doanh thu luỹ kế.</p>
        </section>
      </div>

      {c && <section id="da-chuan">
        <div className="tieu-de-khoi"><h2>Dự báo đã chuẩn tới đâu</h2>
          <span className="khong-ap-dung">cách tính chốt tháng, lập sau {c.moc_kiem} ngày làm việc của mỗi tháng</span></div>
        {c.kiem.length ? <div className="the-nk">
          {(() => { const to2 = Math.max(...c.kiem.map(k => k.du_bao), ...c.kiem.map(k => k.thuc_te), 1); return c.kiem.map(k => (
            <div key={k.thang} className="dong-kiem">
              <span className="so">{k.thang.slice(5)}/{k.thang.slice(2, 4)}</span>
              <div className="hai-thanh" role="img" aria-label={`Dự báo ${yen(k.du_bao)}, thực tế ${yen(k.thuc_te)}`} title={`Dự báo ${yen(k.du_bao)} · thực tế ${yen(k.thuc_te)}`}>
                <div className="thanh-db" style={{ width: `${Math.max(k.du_bao / to2 * 100, 0)}%` }} />
                <div className="thanh-tt" style={{ width: `${Math.max(k.thuc_te / to2 * 100, 0)}%` }} /></div>
              <span className="so">{k.lech != null ? pct(k.lech) : "—"}</span>
            </div>)); })()}
          <div className="dong-dc khong-ap-dung">Thanh trên: dự báo · thanh dưới: thực tế · lệch dương = dự báo cao hơn thực tế.</div>
        </div> : <div className="trong">Chưa có tháng đủ ngày nào trước tháng này để kiểm.</div>}
      </section>}
    </div>
  );
}
