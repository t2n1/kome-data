"""Migration 040 — mốc thời gian dời được ("mọi thứ quay về tháng đó").

Đẳng thức vàng: đặt mốc D phải cho ra ĐÚNG kết quả như thể kho chỉ có dữ liệu bán
tới D — trạng thái khách, nhịp mua, hạng 12 tháng, nhóm cần gọi, "tháng này chưa
mua", cần liên hệ, tốc độ bán… không được lệch một dòng nào.
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from kome import khoang_xem as KX
from kome.web.app import create_app
from tests.test_ban_do import _ho_so_khach
from tests.test_san_pham import _ton_ngay

D = date(2026, 3, 31)

# (view, cột sắp) — mọi view "tính đến hôm nay" của mart mà màn hình đọc.
VIEW = [
    ("mart.moc_thoi_gian", "1"),
    ("mart.khach_360", "customer_code"),
    ("mart.khach_nhom_viec", "customer_code, nhom"),
    ("mart.khach_thang_nay", "customer_code"),
    ("mart.uu_tien_lien_he", "customer_code"),
    ("mart.khach_mat_hang", "customer_code, product_code"),
    ("mart.hang_doanh_thu", "customer_code"),
    ("mart.nhip_mua", "customer_code"),
    ("mart.toc_do_ban", "product_code"),
    ("mart.tai_nhan_vien", "salesperson_code"),
    ("mart.khach_theo_tinh", "prefecture, salesperson_code"),
    ("mart.ban_theo_thang", "thang"),
    ("mart.tong_theo_ky", "company_fy"),
]


def _gieo(conn, batch):
    """Ba khách mua đều ở ba nhịp khác nhau, từ 10/2025 tới 7/2026 — MỘT lô nạp
    (gieo từng dòng một lô là ~75 lượt nạp qua mạng, vài phút mỗi test)."""
    import pandas as pd
    from kome.loaders import sales
    dong = []
    for ma, tinh, nhip in (("MA01", "東京都", 7), ("MA02", "大阪府", 14), ("MA03", "東京都", 30)):
        _ho_so_khach(conn, batch, ma, f"Quan {ma}", prefecture=tinh)
        d, i = date(2025, 10, 1), 0
        while d <= date(2026, 7, 20):
            # MA02 ngừng mua sau 2/2026 — lúc 31/3 đã "im lặng", sau đó vẫn im.
            if not (ma == "MA02" and d > date(2026, 2, 15)):
                tien, hang = 11_000 * (1 + i % 3), ("XT07", "XT08")[i % 2]
                dong.append({"slip_no": f"S{ma}{d:%Y%m%d}", "line_seq": 1, "sales_date": d,
                             "customer_code": ma, "product_code": hang, "pack_code": "02",
                             "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
                             "amount": tien, "tax_amount": 1_000, "cost": tien - 1_000 - 3_000,
                             "gross_profit": 3_000, "paid_amount": 0, "salesperson_code": "0104"})
            d += timedelta(days=nhip)
            i += 1
    b = batch(777)
    df = pd.DataFrame(dong)
    df["batch_id"] = b
    sales.load(conn, df, date(2026, 7, 20), b)
    conn.commit()


def _chup(conn):
    return {v: conn.execute(f"SELECT * FROM {v} ORDER BY {k}").fetchall() for v, k in VIEW}


def test_moc_D_BANG_kho_chi_co_du_lieu_toi_D(conn, batch):
    _gieo(conn, batch)
    conn.execute("SELECT set_config('kome.moc', %s, true)", (D.isoformat(),))
    co_moc = _chup(conn)
    conn.rollback()
    assert conn.execute("SELECT hom_nay FROM mart.moc_thoi_gian").fetchone()[0] > D, \
        "set_config(…, true) phải hết hiệu lực sau giao dịch"
    conn.execute("DELETE FROM core.fact_sales_line WHERE sales_date > %s", (D,))
    conn.commit()
    that = _chup(conn)
    for v, _ in VIEW:
        assert co_moc[v] == that[v], f"{v} lệch khi đặt mốc {D}"
    assert co_moc["mart.khach_360"], "phải có dữ liệu để so"


def test_khong_dat_moc_la_nhu_cu(conn, batch):
    _gieo(conn, batch)
    assert conn.execute("SELECT (SELECT hom_nay FROM mart.moc_thoi_gian) = max(sales_date), "
                        "(SELECT count(*) FROM mart.dong_ban) = count(*) FROM core.fact_sales_line").fetchone() == (True, True)
    assert conn.execute("SELECT mart.moc_lui()").fetchone()[0] is None


def test_moc_bang_hoac_sau_ngay_ban_cuoi_la_khong_doi(conn, batch):
    _gieo(conn, batch)
    cuoi = conn.execute("SELECT max(sales_date) FROM core.fact_sales_line").fetchone()[0]
    for m in (cuoi, date(2030, 1, 1)):
        conn.execute("SELECT set_config('kome.moc', %s, true)", (m.isoformat(),))
        assert conn.execute("SELECT mart.moc_lui()").fetchone()[0] is None
    conn.rollback()


def test_ton_truoc_anh_chup_dau_tien_la_khong_co(conn, batch):
    """Chủ DN chọn: tháng cũ không có ảnh chụp tồn thì NÓI RÕ là không có — không
    lấy ảnh chụp sau mốc. Xem hiện tại thì vẫn dùng ảnh chụp mới nhất, kể cả khi
    nó SAU ngày bán cuối (bản thật: tồn 16/9, bán tới 31/7)."""
    _gieo(conn, batch)
    _ton_ngay(conn, batch, "XT07", date(2026, 9, 16))
    assert conn.execute("SELECT count(*) FROM mart.ton_hien_tai").fetchone()[0] == 1
    conn.execute("SELECT set_config('kome.moc', '2026-03-31', true)")
    assert conn.execute("SELECT count(*) FROM mart.ton_hien_tai").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM mart.san_pham_360 WHERE ton IS NOT NULL").fetchone()[0] == 0,         "không có ảnh chụp tới mốc: tồn là KHÔNG BIẾT (NULL), không phải 0"
    conn.rollback()
    _ton_ngay(conn, batch, "XT07", date(2026, 3, 20), sl=40)
    conn.execute("SELECT set_config('kome.moc', '2026-03-31', true)")
    assert conn.execute("SELECT so_luong FROM mart.ton_hien_tai").fetchall() == [(40,)]
    conn.rollback()


def test_giai_conn_dat_moc_trong_cung_luot_hoi(conn, batch, monkeypatch):
    _gieo(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    kx = KX.giai_conn(conn, KX.doc_tham_so(thang="2026-03"))
    assert dem["n"] == 1
    assert kx.hom_nay == conn.execute("SELECT hom_nay FROM mart.moc_thoi_gian").fetchone()[0] <= D
    # Về lại mặc định trên CÙNG giao dịch: mốc phải được gỡ.
    kx = KX.giai_conn(conn, KX.doc_tham_so())
    assert kx.hom_nay > D
    assert conn.execute("SELECT mart.moc_lui()").fetchone()[0] is None


def test_khoi_hom_nay_quay_ve_thang_chon(conn, batch, test_db_url):
    _gieo(conn, batch)
    c = TestClient(create_app(db_url=test_db_url))
    nay = c.get("/api/tong-quan/suc_khoe_khach").json()
    t3 = c.get("/api/tong-quan/suc_khoe_khach?thang=2026-03").json()
    assert nay["dem"] != t3["dem"] or nay != t3
    conn.execute("SELECT set_config('kome.moc', '2026-03-31', true)")
    dem = dict(conn.execute("SELECT trang_thai, count(*) FROM mart.khach_360 GROUP BY 1").fetchall())
    conn.rollback()
    assert {k: v for k, v in t3["dem"].items() if v} == dem
