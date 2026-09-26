"""Tầng SQL của Sản phẩm 360 (migration 051–053): các hàm mart.sp_*(mã).

Mỗi test khoá một bất biến đã ghi trong CLAUDE.md, không chỉ "chạy được"."""
from datetime import timedelta

import pandas as pd

from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY
from tests.test_mart_san_pham import _ban_qty, _san_pham


def _dong(conn, batch, ma_khach, ngay, ma_hang, qty=1, tien=110_000, tax=10_000, gp=30_000,
          phieu=None, dong=1, pack="02", sale="0104"):
    """Một dòng bán đầy đủ tuỳ biến (phiếu, dòng, quy cách, người phụ trách)."""
    from kome.loaders import sales
    b = batch(abs(hash((ma_khach, ngay, ma_hang, phieu, dong, qty))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": phieu or f"D{ma_khach[-4:]}{ngay:%m%d}{ma_hang}", "line_seq": dong,
        "sales_date": ngay, "customer_code": ma_khach, "product_code": ma_hang,
        "salesperson_code": sale, "pack_code": pack, "case_qty": qty, "qty": qty,
        "unit_price": 0, "unit_cost": 0, "amount": tien, "tax_amount": tax,
        "cost": tien - tax - gp, "gross_profit": gp, "paid_amount": 0, "batch_id": b,
    }]), ngay, b)
    conn.commit()


# ------------------------------------------------------------------ 051

def test_tap_trung_gop_theo_KHACH_khong_theo_nguoi_phu_trach(conn, batch):
    """Bất biến tap_trung_khach: một khách đổi người phụ trách giữa kỳ vẫn MỘT dòng."""
    _san_pham(conn, batch, "T1")
    _ho_so_khach(conn, batch, "KT01", "Quán A")
    _dong(conn, batch, "KT01", HOM_NAY - timedelta(days=40), "T1", sale="0102")
    _dong(conn, batch, "KT01", HOM_NAY - timedelta(days=5), "T1", sale="0104")
    _ho_so_khach(conn, batch, "KT02", "Quán B")
    _dong(conn, batch, "KT02", HOM_NAY - timedelta(days=5), "T1", tien=55_000, tax=5_000)
    _neo(conn, batch)
    r = conn.execute("SELECT customer_code, doanh_thu, luy_ke FROM mart.sp_tap_trung_khach('T1')").fetchall()
    assert [x[0] for x in r] == ["KT01", "KT02"]
    assert r[0][1] == 200_000
    assert abs(float(r[1][2]) - 1.0) < 1e-9


def test_theo_tinh_du_47_o_ke_ca_tinh_khong_ai_mua(conn, batch):
    """LEFT JOIN từ dim_prefecture: tỉnh không có khách mua mã này vẫn là một ô 0."""
    _san_pham(conn, batch, "T2")
    _ho_so_khach(conn, batch, "KT03", "Quán Osaka", prefecture="大阪府")
    _dong(conn, batch, "KT03", HOM_NAY - timedelta(days=3), "T2")
    _neo(conn, batch)
    r = conn.execute("SELECT ten, doanh_thu, so_khach FROM mart.sp_theo_tinh('T2')").fetchall()
    assert len(r) == 47
    d = {x[0]: (x[1], x[2]) for x in r}
    assert d["大阪府"] == (100_000, 1)
    assert d["和歌山県"] == (0, 0)


def test_theo_nguoi_giu_ma_ngoai_danh_sach_phu_trach(conn, batch):
    """Nếp FULL JOIN ngân sách: mã phụ trách '0000' không có trong dim_salesperson vẫn có dòng."""
    _san_pham(conn, batch, "T3")
    _ho_so_khach(conn, batch, "KT04", "Quán C")
    _dong(conn, batch, "KT04", HOM_NAY - timedelta(days=3), "T3", sale="0000")
    _neo(conn, batch)
    r = conn.execute("SELECT salesperson_code, ten, doanh_thu FROM mart.sp_theo_nguoi('T3')").fetchall()
    assert r == [("0000", None, 100_000)]


def test_khach_moi_thang_dem_lan_DAU_mua_ma_nay(conn, batch):
    _san_pham(conn, batch, "T4")
    _ho_so_khach(conn, batch, "KT05", "Quán cũ")
    _dong(conn, batch, "KT05", HOM_NAY - timedelta(days=400), "T4")   # lần đầu từ năm trước
    _dong(conn, batch, "KT05", HOM_NAY - timedelta(days=2), "T4")
    _ho_so_khach(conn, batch, "KT06", "Quán mới")
    _dong(conn, batch, "KT06", HOM_NAY - timedelta(days=1), "T4")
    _neo(conn, batch)
    r = conn.execute("SELECT thang, khach_moi, khach_quay_lai FROM mart.sp_khach_moi_thang('T4')").fetchall()
    assert len(r) == 12 and r[-1][0] == f"{HOM_NAY:%Y-%m}"
    assert (r[-1][1], r[-1][2]) == (1, 1)


def test_ma_noi_bo_khong_vao_ham_nao_cua_051(conn, batch):
    """044: 0090…/0099… là nhân viên mua — ban_den_moc đã lọc, hàm mới không được lọt."""
    _san_pham(conn, batch, "T5")
    _dong(conn, batch, "009000000001", HOM_NAY - timedelta(days=3), "T5")
    _neo(conn, batch)
    assert conn.execute("SELECT count(*) FROM mart.sp_tap_trung_khach('T5')").fetchone()[0] == 0
    assert conn.execute("SELECT coalesce(sum(so_khach),0) FROM mart.sp_theo_tinh('T5')").fetchone()[0] == 0


# ------------------------------------------------------------------ 052

def test_theo_tuan_du_26_tuan_tuan_trong_bang_0(conn, batch):
    _san_pham(conn, batch, "T6")
    _ho_so_khach(conn, batch, "KT07", "Quán D")
    _dong(conn, batch, "KT07", HOM_NAY, "T6", qty=3)
    _neo(conn, batch)
    r = conn.execute("SELECT tuan, so_luong FROM mart.sp_theo_tuan('T6')").fetchall()
    assert len(r) == 26
    assert all(t.isoweekday() == 1 for t, _ in r)
    assert float(r[-1][1]) == 3 and float(r[0][1]) == 0


def test_co_don_dem_dong_TRA_LAI_rieng_khong_loc(conn, batch):
    """赤伝 không bị lọc: dòng âm vào nhóm 'tra_lai'."""
    _san_pham(conn, batch, "T7")
    _ho_so_khach(conn, batch, "KT08", "Quán E")
    _dong(conn, batch, "KT08", HOM_NAY - timedelta(days=9), "T7", qty=4)
    _dong(conn, batch, "KT08", HOM_NAY - timedelta(days=2), "T7", qty=-1, tien=-27_500, tax=-2_500, gp=-7_000)
    _neo(conn, batch)
    r = {(x[0], x[1]): x[3] for x in conn.execute("SELECT * FROM mart.sp_co_don('T7')").fetchall()}
    assert r[("02", "3–5")] == 1 and r[("02", "tra_lai")] == 1


def test_don_gia_la_TY_SO_CAC_TONG(conn, batch):
    """[CRITICAL] 021: trung bình tỷ số bị dòng mẫu số tí hon thổi phồng.
    Hai dòng: 10 đv / ¥100.000 thuần và 1 đv / ¥1.000 thuần.
    Tỷ số các tổng = 101.000 / 11 ≈ 9.181,8; trung bình đơn giá = (10.000 + 1.000)/2 = 5.500."""
    _san_pham(conn, batch, "T8")
    _ho_so_khach(conn, batch, "KT09", "Quán F")
    _dong(conn, batch, "KT09", HOM_NAY - timedelta(days=3), "T8", qty=10, tien=110_000, tax=10_000)
    _dong(conn, batch, "KT09", HOM_NAY - timedelta(days=2), "T8", qty=1, tien=1_100, tax=100)
    _neo(conn, batch)
    r = conn.execute("SELECT don_gia FROM mart.sp_don_gia_thang('T8') WHERE thang = %s AND pack_code = '02'",
                     (f"{HOM_NAY:%Y-%m}",)).fetchone()
    assert abs(float(r[0]) - 101_000 / 11) < 0.01


def test_don_gia_NULL_khi_tong_so_luong_khong_duong(conn, batch):
    _san_pham(conn, batch, "T9")
    _ho_so_khach(conn, batch, "KT10", "Quán G")
    _dong(conn, batch, "KT10", HOM_NAY - timedelta(days=2), "T9", qty=-2, tien=-22_000, tax=-2_000, gp=-5_000)
    _neo(conn, batch)
    r = conn.execute("SELECT don_gia FROM mart.sp_don_gia_thang('T9')").fetchall()
    assert r and r[0][0] is None


def test_khach_gia_chi_khach_DT_duong_va_it_nhat_2_lan(conn, batch):
    _san_pham(conn, batch, "T10")
    _ho_so_khach(conn, batch, "KT11", "Quán hai lần")
    _dong(conn, batch, "KT11", HOM_NAY - timedelta(days=20), "T10", qty=2)
    _dong(conn, batch, "KT11", HOM_NAY - timedelta(days=2), "T10", qty=2)
    _ho_so_khach(conn, batch, "KT12", "Quán một lần")
    _dong(conn, batch, "KT12", HOM_NAY - timedelta(days=2), "T10", qty=2)
    _neo(conn, batch)
    r = conn.execute("SELECT customer_code, so_lan, bien FROM mart.sp_khach_gia('T10')").fetchall()
    assert [x[0] for x in r] == ["KT11"]
    assert r[0][1] == 2 and abs(float(r[0][2]) - 0.3) < 1e-9
