"""Khối "Tiến độ ngân sách tháng" của `/` — đường luỹ kế theo ngày
(`kome.khoi_tong_quan.duong_luy_ke`). Đường chỉ là hình để vẽ: tại mốc nó phải
trùng ĐÚNG các con số chữ của khối (thực tế, mốc đáng lẽ đạt tới hôm nay)."""
from datetime import date

import pandas as pd

from kome import khoang_xem as KX
from kome import khoi_tong_quan as KTQ


def _ban(conn, batch, ngay: date, sale="0104", amount=110_000, tax=10_000):
    from kome.loaders import sales
    b = batch(abs(hash((ngay, sale, amount))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{sale}", "line_seq": 1, "sales_date": ngay,
        "customer_code": "000000009292", "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": amount, "tax_amount": tax, "cost": amount - tax - 30_000,
        "gross_profit": 30_000, "paid_amount": 0, "salesperson_code": sale,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


def _gieo(conn, batch):
    _ban(conn, batch, date(2026, 6, 5))
    _ban(conn, batch, date(2026, 7, 10))
    _ban(conn, batch, date(2026, 7, 20))
    conn.execute("INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
                 "VALUES ('0104', '2026-07-01', 10000000)")
    conn.execute("INSERT INTO app.ngan_sach_cong_ty (thang, doanh_thu, lai_gop) "
                 "VALUES ('2026-07-01', 10000000, 2000000)")
    conn.commit()


def _theo_ngay(d):
    return {x["nhan"]: x for x in d["duong"]["diem"]}


def test_duong_trung_con_so_chu_tai_moc(conn, batch):
    _gieo(conn, batch)
    d = KTQ.ngan_sach_thang(conn, None, KX.ThamSo())
    duong = d["duong"]
    assert duong["kieu"] == "ngay" and len(duong["diem"]) == 31
    p = _theo_ngay(d)
    assert p["2026-07-20"]["tt"] == d["thuc_te"] == 200_000
    assert p["2026-07-20"]["ns"] == d["muc_tieu_den_hom_nay"]
    assert p["2026-07-31"]["ns"] == d["muc_tieu"] == 10_000_000
    assert p["2026-07-21"]["tt"] is None          # sau mốc: chưa có dữ liệu
    assert p["2026-07-09"]["tt"] == 0 and p["2026-07-10"]["tt"] == 100_000
    # luỹ kế tháng trước theo cùng số ngày; tháng 6 không có ngày 31
    assert p["2026-07-04"]["ss"] == 0 and p["2026-07-05"]["ss"] == 100_000
    assert p["2026-07-31"]["ss"] is None


def test_nhip_ngan_sach_chi_tang_vao_ngay_lam_viec(conn, batch):
    _gieo(conn, batch)
    p = _theo_ngay(KTQ.ngan_sach_thang(conn, None, KX.ThamSo()))
    # 2026-07-11/12 là thứ Bảy/Chủ nhật: nhịp đứng yên
    assert p["2026-07-10"]["ns"] == p["2026-07-11"]["ns"] == p["2026-07-12"]["ns"]
    assert p["2026-07-13"]["ns"] > p["2026-07-12"]["ns"]


def test_chua_dat_chi_tieu_thi_khong_co_duong_nhip(conn, batch):
    _ban(conn, batch, date(2026, 7, 20))
    d = KTQ.ngan_sach_thang(conn, None, KX.ThamSo())
    assert all(x["ns"] is None for x in d["duong"]["diem"])
    assert _theo_ngay(d)["2026-07-20"]["tt"] == 100_000


def test_thang_cu_ve_tron_thang_do(conn, batch):
    _gieo(conn, batch)
    d = KTQ.ngan_sach_thang(conn, None, KX.ThamSo(thang="2026-06"))
    p = _theo_ngay(d)
    assert len(d["duong"]["diem"]) == 30
    assert p["2026-06-30"]["tt"] == 100_000       # chỉ phiếu tháng 6, không lẫn tháng 7


def test_dang_ky_dung_luy_ke_theo_thang(conn, batch):
    _gieo(conn, batch)
    d = KTQ.ngan_sach_thang(conn, None, KX.ThamSo(ky=2026))
    assert d["duong"]["kieu"] == "thang"
    assert [x["nhan"] for x in d["duong"]["diem"]] == [m["thang"] for m in d["luy_ke"]]


def test_duong_lai_gop_trung_con_so_chu_tai_moc(conn, batch):
    _gieo(conn, batch)
    d = KTQ.ngan_sach_thang(conn, None, KX.ThamSo())
    p = _theo_ngay(d)
    assert p["2026-07-20"]["tt_lg"] == d["thuc_te_lg"] == 60_000
    assert p["2026-07-20"]["ns_lg"] == d["muc_tieu_lg_den_hom_nay"]
    assert p["2026-07-31"]["ns_lg"] == d["muc_tieu_lg"] == 2_000_000
    assert p["2026-07-05"]["ss_lg"] == 30_000
