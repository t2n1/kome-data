"""047 — dòng không có mã hàng (điều chỉnh làm tròn của OBC) không phải một mặt hàng.

Sự cố thật 2026-09-25: 1.531 khách có một "mã" rỗng trong mart.khach_mat_hang,
381 khách bị đếm thêm 1 "mã đã ngừng mua", hồ sơ hiện một dòng không tên
"quá hạn 25 ngày" trong Lịch mua dự kiến."""
from datetime import date, timedelta

import pandas as pd

KHACH = "000000009292"


def _nap(conn, batch, dong):
    from kome.loaders import sales
    b = batch(4401)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{i:04d}", "line_seq": 1 if ma else 2, "sales_date": ngay, "customer_code": KHACH,
        "product_code": ma, "pack_code": "02" if ma else "", "case_qty": 1 if ma else 0,
        "qty": 6 if ma else 0, "unit_price": 5250 if ma else 0, "unit_cost": 3210 if ma else 0,
        "amount": tien, "tax_amount": 0, "cost": 0, "gross_profit": 0, "paid_amount": 0,
        "salesperson_code": "0104", "batch_id": b,
    } for i, (ngay, ma, tien) in enumerate(dong)]), max(d[0] for d in dong), b)
    conn.commit()


def test_dong_khong_ma_hang_khong_vao_trang_thai_cap_nhung_van_vao_tong(conn, batch):
    dau = date(2026, 6, 1)
    dong = []
    for k in range(5):                            # 5 phiếu, mỗi phiếu có 1 dòng làm tròn
        d = dau + timedelta(days=7 * k)
        dong += [(d, "AA01", 10_000), (d, "", 1)]
    _nap(conn, batch, dong)

    ma = [r[0] for r in conn.execute(
        "SELECT product_code FROM mart.khach_mat_hang WHERE customer_code = %s", (KHACH,))]
    assert ma == ["AA01"]
    # tiền của dòng làm tròn vẫn là doanh thu thật của khách
    tong = conn.execute("SELECT doanh_thu_thuan FROM mart.khach_360 WHERE customer_code = %s",
                        (KHACH,)).fetchone()[0]
    assert tong == 5 * 10_001
    # danh sách theo khoảng giữ dòng đó (cộng đúng bằng tổng), với tên đọc được
    kh = {r[0]: (r[1], r[2]) for r in conn.execute(
        "SELECT product_code, ten_hang, dt FROM mart.khach_mat_hang_khoang(%s, %s) WHERE customer_code = %s",
        (dau, dau + timedelta(days=60), KHACH))}
    assert kh[""][0] and kh[""][1] == 5
    assert sum(v[1] for v in kh.values()) == tong
