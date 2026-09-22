"""Đợt 5a Task 4 — bốn khối ngân sách trên màn Báo cáo."""
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kome.bao_cao import tien_do_ngan_sach, ve_luy_ke
from kome.web.app import create_app


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


def test_tong_nhom_cong_du_moi_nguoi(conn, batch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _ban(conn, batch, date(2026, 7, 30), "0105", khach="000000009293")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 6_000_000)
    _chi_tieu(conn, "0105", date(2026, 7, 1), 4_000_000)
    td = tien_do_ngan_sach(conn)
    assert td.muc_tieu == 10_000_000
    assert td.thuc_te == 200_000
    assert td.co_ngan_sach is True


def test_luy_ke_DUNG_o_thang_cua_hom_nay(conn, batch):
    """[IMPORTANT] Đường luỹ kế kéo dài tới hết kỳ bằng số 0 đọc thành "doanh
    thu sụp", không phải "chưa có dữ liệu"."""
    _ban(conn, batch, date(2025, 9, 15), "0104")
    _ban(conn, batch, date(2025, 10, 15), "0104", khach="000000009293")
    for t in ("2025-08", "2025-09", "2025-10", "2025-11"):
        _chi_tieu(conn, "0104", date(int(t[:4]), int(t[5:]), 1), 1_000_000)
    td = tien_do_ngan_sach(conn, 2026)
    sau = {m.thang: m.thuc_te for m in td.luy_ke}
    assert sau["2025-10"] == 200_000, "luỹ kế tới tháng của hom_nay"
    assert sau["2025-11"] is None, "sau hom_nay phải là None, không phải 0"
    ns = {m.thang: m.ngan_sach for m in td.luy_ke}
    assert ns["2025-11"] == 4_000_000, "nhịp ngân sách vẫn chạy hết kỳ"


def test_ve_luy_ke_khong_no_khi_chua_co_chi_tieu(conn, batch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    assert ve_luy_ke(tien_do_ngan_sach(conn))["co"] is False


def test_trang_bao_cao_in_ro_thang_va_ngay_moc(client, conn, batch):
    """Khối phải nói nó đang nói về tháng nào và số liệu tới ngày nào."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 6_000_000)
    html = client.get("/bao-cao").text
    assert "2026-07" in html
    assert "31/07/2026" in html


def test_trang_bao_cao_khong_co_chi_tieu_thi_moi_sang_man_ngan_sach(client, conn, batch):
    _ban(conn, batch, date(2026, 7, 31), "0104")
    html = client.get("/bao-cao").text
    assert "Chưa đặt chỉ tiêu" in html
    assert '/ngan-sach' in html


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
    td = tien_do_ngan_sach(conn)
    assert td.co_ngan_sach is True
    assert td.muc_tieu == 0
    assert td.tien_do is None


def test_trang_bao_cao_khong_no_khi_chi_tieu_bang_0(client, conn, batch):
    """[CRITICAL, vòng sửa 2] Không có test này thì bản sửa chỉ là lời hứa:
    24 test cũ không ca nào đặt chỉ tiêu bằng 0, nên lỗi 500 (None * 100 và
    chia cho 0 ở thẻ "Mốc đến hôm nay") lọt qua hết."""
    _ban(conn, batch, date(2026, 7, 31), "0104")
    _chi_tieu(conn, "0104", date(2026, 7, 1), 0)
    r = client.get("/bao-cao")
    assert r.status_code == 200
    assert "—" in r.text
    # So khớp đúng giá trị được RENDER trong ô .gia — không so "0.0%" trần,
    # vì "30.0%" (Tỷ suất lãi gộp của khối cũ, không liên quan) chứa sẵn
    # chuỗi con "0.0%" và sẽ làm test đỏ giả (dương tính giả) nếu so trần.
    assert 'class="gia">0.0%' not in r.text, \
        "0% nói dối là đã đạt tiến độ, không phải KHÔNG có mẫu số"
    assert "0.0% chỉ tiêu" not in r.text
