"""Đợt 5a Task 4 — bốn khối ngân sách trên màn Báo cáo.

Giai đoạn 3: /bao-cao là React (giao_dien/src/bao_cao/BaoCao.tsx) — các
test "trang" kiểm dữ liệu /api/bao-cao (con số mà màn in ra) và, khi bất biến
là cách IN (ô trống, "không có dữ liệu", không tự tính phần trăm), kiểm thẳng
mã nguồn React."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kome.bao_cao import tien_do_ngan_sach, ve_luy_ke
from kome.web.app import create_app

NGUON = (Path(__file__).resolve().parents[1] / "giao_dien" / "src" / "bao_cao" / "BaoCao.tsx")


def _src() -> str:
    return NGUON.read_text(encoding="utf-8")


def _td(client, ky=None) -> dict:
    """Vỏ React trả 200, và khối ngân sách (`td`) của /api/bao-cao."""
    assert client.get("/bao-cao" + (f"?ky={ky}" if ky else "")).status_code == 200
    r = client.get("/api/bao-cao" + (f"?ky={ky}" if ky else ""))
    assert r.status_code == 200, r.text
    return r.json()["td"]


def _nguoi(td, ma) -> dict:
    return next(n for n in td["nguoi"] if n["ma"] == ma)


@pytest.fixture
def client(conn, test_db_url):
    return TestClient(create_app(db_url=test_db_url))


def _ban(conn, batch, ngay: date, sale: str, amount=110_000, tax=10_000, gp=30_000,
         khach="000000009292"):
    from kome.loaders import sales
    b = batch(abs(hash((ngay, sale, amount, khach))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{sale}", "line_seq": 1, "sales_date": ngay,
        "customer_code": khach, "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": amount, "tax_amount": tax, "cost": amount - tax - gp,
        "gross_profit": gp, "paid_amount": 0, "salesperson_code": sale,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


def _chi_tieu(conn, sale, thang: date, muc_tieu):
    conn.execute("INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
                 "VALUES (%s, %s, %s)", (sale, thang, muc_tieu))
    conn.commit()


def _cong_ty(conn, thang: date, doanh_thu, lai_gop=None):
    """Ngân sách CÔNG TY (041) — số nhập thẳng, không phải tổng từng người."""
    conn.execute("INSERT INTO app.ngan_sach_cong_ty (thang, doanh_thu, lai_gop) "
                 "VALUES (%s, %s, %s)", (thang, doanh_thu, lai_gop))
    conn.commit()


def test_thang_lay_theo_HOM_NAY_khong_theo_dong_ho_that(conn, batch):
    """[CRITICAL] Đo thật 2026-09-22: phiếu bán mới nhất trong kho là
    2026-07-31 — gần hai tháng không ai nạp file bán hàng. Lấy current_date
    thì trang báo "tháng 9 đạt 0% ngân sách" trong khi sự thật là chưa ai nạp
    dữ liệu tháng 9, và người ta đi hỏi nhân viên vì sao không bán được gì."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    td = tien_do_ngan_sach(conn)
    assert td.thang == "2026-07"
    assert td.hom_nay == date(2026, 7, 31)


def test_kho_rong_thi_tra_None_chu_khong_no(conn):
    assert tien_do_ngan_sach(conn) is None


def test_ma_ngoai_dim_salesperson_co_dong_rieng_khong_bi_bo(conn, batch):
    """[CRITICAL] Bỏ dòng này đi là giấu doanh thu thật; gắn cho nó một chỉ
    tiêu là bịa ra một con số."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _ban(conn, batch, date(2026, 7, 30), "0000", amount=33_000, tax=3_000, gp=9_000,
         khach="000000009293")
    td = tien_do_ngan_sach(conn)
    la = next(n for n in td.nguoi if n.ma == "0000")
    assert la.ten is None, "mã ngoài danh sách phụ trách KHÔNG có tên"
    assert la.thuc_te == 30_000 and la.muc_tieu is None


def test_khong_ai_dat_chi_tieu_thi_co_ngan_sach_FALSE(conn, batch):
    """Khối rỗng phải nói "chưa đặt chỉ tiêu", KHÔNG hiện 0%."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    td = tien_do_ngan_sach(conn)
    assert td.co_ngan_sach is False
    assert td.muc_tieu is None and td.tien_do is None


def test_ngan_sach_cong_ty_la_so_NHAP_THANG_khong_phai_tong_tung_nguoi(conn, batch):
    """041: chủ DN đặt ngân sách công ty riêng. Từng người cộng lại 10M, công ty đặt 12M
    -> tiến độ công ty so với 12M; công ty CHƯA đặt -> "chưa đặt", KHÔNG rơi về 10M."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _ban(conn, batch, date(2026, 7, 30), "0105", khach="000000009293")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 6_000_000)
    _chi_tieu(conn, "0105", date(2026, 7, 1), 4_000_000)
    td = tien_do_ngan_sach(conn)
    assert td.co_ngan_sach is False and td.muc_tieu is None
    assert td.thuc_te == 200_000
    assert sum(n.muc_tieu for n in td.nguoi if n.muc_tieu) == 10_000_000
    _cong_ty(conn, date(2026, 7, 1), 12_000_000, 3_000_000)
    td = tien_do_ngan_sach(conn)
    assert td.co_ngan_sach is True and td.muc_tieu == 12_000_000
    assert td.muc_tieu_lg == 3_000_000 and td.thuc_te_lg == 60_000
    assert td.tien_do == 200_000 / 12_000_000


def test_cong_ty_dat_ma_tung_nguoi_KHONG_dat_van_co_tien_do(conn, batch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _cong_ty(conn, date(2026, 7, 1), 1_000_000, None)
    td = tien_do_ngan_sach(conn)
    assert td.co_ngan_sach is True and td.tien_do == 0.1
    assert td.muc_tieu_lg is None and td.co_ngan_sach_lg is False
    assert all(n.muc_tieu is None for n in td.nguoi)


def test_moc_lai_gop_DUNG_cong_thuc_ngay_lam_viec(conn, batch):
    _ban(conn, batch, date(2026, 7, 15), "0104")
    _cong_ty(conn, date(2026, 7, 1), 22_000_000, 2_200_000)
    td = tien_do_ngan_sach(conn)
    assert td.muc_tieu_lg_den_hom_nay == round(2_200_000 * td.ngay_kd_da_qua / td.ngay_kd)
    assert td.muc_tieu_den_hom_nay == round(22_000_000 * td.ngay_kd_da_qua / td.ngay_kd)


def test_luy_ke_DUNG_o_thang_cua_hom_nay(conn, batch):
    """[IMPORTANT] Đường luỹ kế kéo dài tới hết kỳ bằng số 0 đọc thành "doanh
    thu sụp", không phải "chưa có dữ liệu"."""
    _ban(conn, batch, date(2025, 9, 15), "0104")
    _ban(conn, batch, date(2025, 10, 15), "0104", khach="000000009293")
    for t in ("2025-08", "2025-09", "2025-10", "2025-11"):
        _chi_tieu(conn, "0104", date(int(t[:4]), int(t[5:]), 1), 1_000_000)
        _cong_ty(conn, date(int(t[:4]), int(t[5:]), 1), 1_000_000)
    td = tien_do_ngan_sach(conn, 2026)
    sau = {m.thang: m.thuc_te for m in td.luy_ke}
    assert sau["2025-10"] == 200_000, "luỹ kế tới tháng của hom_nay"
    assert sau["2025-11"] is None, "sau hom_nay phải là None, không phải 0"
    ns = {m.thang: m.ngan_sach for m in td.luy_ke}
    assert ns["2025-11"] == 4_000_000, "nhịp ngân sách vẫn chạy hết kỳ"


def test_ve_luy_ke_khong_no_khi_chua_co_chi_tieu(conn, batch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    assert ve_luy_ke(tien_do_ngan_sach(conn))["co"] is False


def test_ve_luy_ke_tra_toa_do_nhan_truc_hoanh(conn, batch):
    """[Vòng soát cuối, việc 10] `nhan` từng là list chuỗi TRẦN không kèm
    toạ độ nên template bỏ qua luôn — biểu đồ luỹ kế không nói điểm nào là
    tháng nào. Giờ mỗi mục phải mang `x` (toạ độ SVG) và `thang`."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 6_000_000)
    _cong_ty(conn, date(2026, 7, 1), 6_000_000)
    lk = ve_luy_ke(tien_do_ngan_sach(conn))
    assert lk["co"] is True
    assert len(lk["nhan"]) == 12
    assert lk["nhan"][0]["thang"] == "2025-08"
    assert lk["nhan"][-1]["thang"] == "2026-07"
    assert isinstance(lk["nhan"][0]["x"], float)
    assert lk["nhan"][0]["x"] < lk["nhan"][-1]["x"], "tháng đầu phải ở BÊN TRÁI tháng cuối"


def test_luy_ke_chi_tieu_DUNG_BANG_0_giu_nguyen_la_0_khong_thanh_None(conn, batch):
    """[Vòng soát cuối, việc 10] `ngan_sach=c_ns if c_ns else None` từng lẫn
    "luỹ kế chỉ tiêu đúng bằng 0" (mọi tháng tới giờ đều đặt = 0, hoặc chưa
    ai đặt) với "chưa có dữ liệu để vẽ" — đúng cái lẫn 0-khác-chưa-đặt mà cả
    đợt 5a tồn tại để phân biệt (app.ngan_sach CHECK >= 0 cho phép muc_tieu
    = 0 là một giá trị ĐÃ ĐẶT). Sau bản sửa (`is not None`), mốc 0 phải giữ
    nguyên là số 0, không bị đổi thành None và biến mất khỏi đường luỹ kế."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 0)
    _cong_ty(conn, date(2026, 7, 1), 0)
    td = tien_do_ngan_sach(conn)
    thang_7 = next(m for m in td.luy_ke if m.thang == "2026-07")
    assert thang_7.ngan_sach == 0, "0 hợp lệ phải giữ nguyên 0, không phải None"


def test_trang_bao_cao_in_ro_thang_va_ngay_moc(client, conn, batch):
    """Khối phải nói nó đang nói về tháng nào và số liệu tới ngày nào.

    Giai đoạn 3: API trả tháng + ngày mốc; React in cả hai trong khối."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 6_000_000)
    td = _td(client)
    assert td["thang"] == "2026-07"
    assert td["hom_nay"] == "2026-07-31"
    src = _src()
    assert "<h2>Tiến độ ngân sách tháng {tNhan}</h2>" in src
    assert "Số liệu đến {ngay(td.hom_nay)}" in src


def test_trang_bao_cao_khong_co_chi_tieu_thi_moi_sang_man_ngan_sach(client, conn, batch):
    """Giai đoạn 3: API nói kỳ chưa có chỉ tiêu; React in "Chưa đặt chỉ tiêu"
    kèm liên kết sang /ngan-sach (gác bởi cờ — xem test_ngan_sach_web.py)."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    td = _td(client)
    assert td["co_ngan_sach"] is False
    src = _src()
    assert "{!v.co ? <div className=\"khoi-loi\">Chưa đặt ngân sách {ten} của công ty cho tháng này." in src
    assert "href={`/ngan-sach?ky=${td.company_fy}`}" in src


def test_tien_do_ngan_sach_khong_qua_3_truy_van(conn, batch, monkeypatch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 6_000_000)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    tien_do_ngan_sach(conn)
    assert dem["n"] <= 3, f"tien_do_ngan_sach() chạy {dem['n']} truy vấn"


def test_chi_tieu_bang_0_la_HOP_LE_tien_do_None_khong_no(conn, batch):
    """[CRITICAL, vòng sửa 2] muc_tieu = 0 là ĐÃ ĐẶT và đặt bằng không — khác
    "chưa đặt" (không có dòng). CHECK (muc_tieu >= 0) của app.ngan_sach cho
    phép nó, và màn /ngan-sach nhận nó. tien_do phải None (không có mẫu số
    để chia), KHÔNG được để lộ ZeroDivisionError."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 0)
    _cong_ty(conn, date(2026, 7, 1), 0)
    td = tien_do_ngan_sach(conn)
    assert td.co_ngan_sach is True
    assert td.muc_tieu == 0
    assert td.tien_do is None


def test_trang_bao_cao_khong_no_khi_chi_tieu_bang_0(client, conn, batch):
    """[CRITICAL, vòng sửa 2] Không có test này thì bản sửa chỉ là lời hứa:
    24 test cũ không ca nào đặt chỉ tiêu bằng 0, nên lỗi 500 (None * 100 và
    chia cho 0 ở thẻ "Mốc đến hôm nay") lọt qua hết.

    Giai đoạn 3: API không nổ (200) và trả `tien_do`/`rong_thanh` = None —
    không phải 0 ("0% nói dối là đã đạt tiến độ, không phải KHÔNG có mẫu
    số"); React in "—" cho `tien_do` None và "chưa có chỉ tiêu" thay vì một
    thanh 0%."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 0)
    _cong_ty(conn, date(2026, 7, 1), 0)
    td = _td(client)
    assert td["co_ngan_sach"] is True and td["muc_tieu"] == 0
    assert td["tien_do"] is None and td["rong_thanh"] is None
    assert _nguoi(td, "0104")["tien_do"] is None
    src = _src()
    assert '{v.td != null ? p1(v.td) : "—"}' in src
    assert 'if (rong == null) return <div className="phu">chưa có chỉ tiêu</div>;' in src


# ---- vòng soát cuối, việc 2/3: "So cùng kỳ" đọc từ mart, không tính lại ---

def test_cung_ky_AM_khong_ra_phan_tram_NGUOC_DAU(conn, batch):
    """[CRITICAL, vòng soát cuối việc 2] Doanh thu thuần một tháng của MỘT
    nhân viên có thể ÂM do 赤伝 (phiếu đỏ, luật cấm lọc bỏ). Bản Jinja cũ tính
    `(thuc_te / cung_ky - 1) * 100` thẳng trong template: thực tế dương chia
    cho một mẫu số ÂM (nhưng khác 0) cho ra phần trăm NGƯỢC DẤU — trang nói
    doanh thu SỤT trong khi thật ra nó TĂNG. `tang_truong` (đọc từ
    mart.tien_do_ngan_sach, gate `> 0`, migration 028) phải là None, KHÔNG
    phải một con số âm khổng lồ."""
    _ban(conn, batch, date(2026, 7, 31), "0104", amount=100_000, tax=0, gp=30_000)
    # Cùng kỳ năm trước (2025-07) của CHÍNH người này: net ÂM (một phiếu đỏ
    # lớn hơn phần bán được).
    _ban(conn, batch, date(2025, 7, 11), "0104", amount=-60_000, tax=-10_000,
         gp=-20_000, khach="000000009293")
    td = tien_do_ngan_sach(conn)
    n = next(x for x in td.nguoi if x.ma == "0104")
    assert n.co_cung_ky is True, "có dòng cùng kỳ (dù âm) thì co_cung_ky phải TRUE"
    assert n.cung_ky == -50_000
    assert n.tang_truong is None, \
        "mẫu số ÂM không có tỷ lệ tăng trưởng nào đọc được — phải là None"


def test_trang_bao_cao_khong_hien_phan_tram_nguoc_dau_khi_cung_ky_am(client, conn, batch):
    """Giai đoạn 3: API trả `tang_truong` None (mẫu số âm), và React CHỈ in
    `tang_truong` của API — không tự chia `thuc_te / cung_ky` (công thức cũ
    cho ra -300.0% ngược dấu)."""
    _ban(conn, batch, date(2026, 7, 31), "0104", amount=100_000, tax=0, gp=30_000)
    _ban(conn, batch, date(2025, 7, 11), "0104", amount=-60_000, tax=-10_000,
         gp=-20_000, khach="000000009293")
    n = _nguoi(_td(client), "0104")
    assert n["co_cung_ky"] is True and n["cung_ky"] == -50_000
    assert n["tang_truong"] is None
    src = _src()
    assert "n.thuc_te / n.cung_ky" not in src and "/ n.cung_ky" not in src
    assert "{n.tang_truong != null ? <span" in src


def test_cung_ky_TON_TAI_nhung_BAN_0_DONG_hien_0_khong_hien_khong_co_du_lieu(
        conn, batch):
    """[IMPORTANT, vòng soát cuối việc 3] "Không có dữ liệu" chỉ đúng khi
    tháng cùng kỳ KHÔNG TỒN TẠI trong kho (trước 2025-03-03). Một tháng CÓ
    dữ liệu mà người này bán ròng 0 đồng (ví dụ một dòng amount=tax=gp=0, hay
    bán rồi trả đủ) là sự thật ¥0 — khác "không biết"."""
    _ban(conn, batch, date(2026, 7, 31), "0104", amount=100_000, tax=0, gp=30_000)
    _ban(conn, batch, date(2025, 7, 11), "0104", amount=0, tax=0, gp=0,
         khach="000000009293")
    td = tien_do_ngan_sach(conn)
    n = next(x for x in td.nguoi if x.ma == "0104")
    assert n.co_cung_ky is True
    assert n.cung_ky == 0


def test_trang_bao_cao_hien_0_dong_khong_hien_khong_co_du_lieu(client, conn, batch):
    """Giai đoạn 3: API trả `co_cung_ky` True + `cung_ky` 0 — và React chọn
    "không có dữ liệu" THEO `co_cung_ky`, không theo giá trị số (0 là falsy
    trong JS: `n.cung_ky ? … : "không có dữ liệu"` sẽ nói sai đúng ca này)."""
    _ban(conn, batch, date(2026, 7, 31), "0104", amount=100_000, tax=0, gp=30_000)
    _ban(conn, batch, date(2025, 7, 11), "0104", amount=0, tax=0, gp=0,
         khach="000000009293")
    n = _nguoi(_td(client), "0104")
    assert n["co_cung_ky"] is True
    # [Vòng soát cuối 3, việc 2] Không có dòng này, cái tên "hiện 0 đồng"
    # của test không còn được kiểm chứng.
    assert n["cung_ky"] == 0
    assert '{n.co_cung_ky ? yen(n.cung_ky ?? 0) : "không có dữ liệu"}' in _src()


# ---- vòng soát cuối 2: hồi quy do chính 027 gây ra -------------------------
#
# 027 lọc mart.ban_theo_nhan_vien_thang_so_sanh theo THÁNG ĐANG XÉT (không
# phải tháng cùng kỳ) — nên một người CÓ muc_tieu mà KHÔNG một dòng bán nào
# trong tháng đang xét mất luôn dữ liệu cùng kỳ NĂM NGOÁI, dù nó có thật.
# Ba test dưới đây khớp NGUYÊN VĂN ba kịch bản bản soát cuối yêu cầu.

def test_khong_ban_thang_nay_nhung_CO_ban_cung_ky_hien_so_that(conn, batch):
    """[CRITICAL, vòng soát cuối 2, việc 1] Người có muc_tieu, KHÔNG một
    dòng bán nào trong tháng M, nhưng CÓ doanh thu ở tháng M-12 → cột "Cùng
    kỳ năm trước" phải hiện SỐ THẬT của năm ngoái, `co_cung_ky` True."""
    _ban(conn, batch, date(2026, 5, 11), "0104")            # M=2026-05 tồn tại
    _ban(conn, batch, date(2025, 5, 20), "0105", amount=88_000, tax=8_000,
         gp=20_000, khach="000000009293")                   # cùng kỳ CỦA 0105
    _chi_tieu(conn, "0105", date(2026, 5, 1), 9_000_000)
    td = tien_do_ngan_sach(conn, 2026)
    n = next(x for x in td.nguoi if x.ma == "0105")
    assert n.thuc_te == 0, "0105 không bán gì tháng đang xét"
    assert n.co_cung_ky is True
    assert n.cung_ky == 80_000, "phải là số THẬT của năm ngoái, không phải None"
    assert n.tang_truong == pytest.approx(-1.0)


def test_trang_bao_cao_khong_bao_khong_co_du_lieu_khi_cung_ky_co_that(
        client, conn, batch):
    """Giai đoạn 3: khẳng định TRỰC TIẾP hai giá trị màn in ra — cùng kỳ
    ¥80.000 và -100% — từ API."""
    _ban(conn, batch, date(2026, 5, 11), "0104")
    _ban(conn, batch, date(2025, 5, 20), "0105", amount=88_000, tax=8_000,
         gp=20_000, khach="000000009293")
    _chi_tieu(conn, "0105", date(2026, 5, 1), 9_000_000)
    n = _nguoi(_td(client, 2026), "0105")
    assert n["co_cung_ky"] is True
    assert n["cung_ky"] == 80_000, "phải hiện đúng số cùng kỳ của 0105"
    assert n["tang_truong"] == pytest.approx(-1.0)


def test_M12_khong_ton_tai_trong_kho_hien_khong_co_du_lieu(conn, batch):
    """[CRITICAL, vòng soát cuối 2, việc 1] Tháng M-12 KHÔNG TỒN TẠI trong
    kho (chưa từng có dòng bán nào, ở BẤT KỲ ai) → co_cung_ky False."""
    _ban(conn, batch, date(2025, 4, 20), "0104")   # M=2025-04, M-12=2024-04
    td = tien_do_ngan_sach(conn, 2025)
    n = next(x for x in td.nguoi if x.ma == "0104")
    assert n.co_cung_ky is False
    assert n.cung_ky is None


def test_trang_bao_cao_hien_khong_co_du_lieu_khi_M12_khong_ton_tai(client, conn, batch):
    """Giai đoạn 3: API trả `co_cung_ky` False + `cung_ky` None, và React in
    "không có dữ liệu" ở cả hai cột cùng kỳ cho đúng trường hợp đó."""
    _ban(conn, batch, date(2025, 4, 20), "0104")
    n = _nguoi(_td(client, 2025), "0104")
    assert n["co_cung_ky"] is False and n["cung_ky"] is None
    src = _src()
    assert '{n.co_cung_ky ? yen(n.cung_ky ?? 0) : "không có dữ liệu"}' in src
    assert ': n.co_cung_ky ? "—" : "không có dữ liệu"}' in src


# ---- vòng soát cuối, việc 9: thanh tiến độ CSS thuần -----------------------

def test_pct_rong_kep_am_ve_0_khong_ve_am(conn, batch):
    """[IMPORTANT] Thực tế ÂM (赤伝) không được vẽ thành chiều rộng âm."""
    from kome.bao_cao import _pct_rong
    assert _pct_rong(-50_000, 1_000_000) == 0.0


def test_pct_rong_kep_vuot_ve_100(conn, batch):
    """Vượt chỉ tiêu không được vẽ tràn khỏi khung."""
    from kome.bao_cao import _pct_rong
    assert _pct_rong(2_000_000, 1_000_000) == 100.0


def test_pct_rong_mau_so_0_hoac_None_tra_None(conn, batch):
    """Chỉ tiêu 0 hoặc chưa đặt: không thanh nào để vẽ, không chia cho 0."""
    from kome.bao_cao import _pct_rong
    assert _pct_rong(500_000, 0) is None
    assert _pct_rong(500_000, None) is None


def test_trang_bao_cao_khong_ve_thanh_am_khi_thuc_te_am(client, conn, batch):
    """[CRITICAL] Toàn nhóm có thực tế ÂM (nhiều 赤伝 hơn doanh số) vẫn phải
    ra trang 200, không có chiều rộng CSS âm nào.

    Giai đoạn 3: chiều rộng thanh là `rong_thanh` của API (React chỉ đặt
    `width: ${rong}%`) — nên kiểm nó đã kẹp về 0 ở cả dòng toàn nhóm lẫn
    từng người."""
    _ban(conn, batch, date(2026, 7, 31), "0104", amount=-60_000, tax=-10_000,
         gp=-20_000)
    _chi_tieu(conn, "0104", date(2026, 7, 1), 1_000_000)
    _cong_ty(conn, date(2026, 7, 1), 1_000_000)
    td = _td(client)
    assert td["thuc_te"] < 0
    assert td["rong_thanh"] == 0.0, "không được vẽ chiều rộng thanh ÂM"
    assert _nguoi(td, "0104")["rong_thanh"] == 0.0
    assert 'style={{ width: `${rong}%` }}' in _src()


def test_trang_bao_cao_khong_ve_thanh_khi_chi_tieu_bang_0(client, conn, batch):
    """Chỉ tiêu bằng 0: không có mẫu số để vẽ thanh nào — không được chia
    cho 0 làm trang 500. Giai đoạn 3: API 200, `rong_thanh` None."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 0)
    _cong_ty(conn, date(2026, 7, 1), 0)
    td = _td(client)
    assert td["rong_thanh"] is None and _nguoi(td, "0104")["rong_thanh"] is None


