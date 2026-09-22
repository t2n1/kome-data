"""Đợt 4c — bảng tra 47 tỉnh và view gộp theo tỉnh."""
from datetime import date, timedelta

import pandas as pd
import pytest


# Ba hàm gieo dữ liệu dưới đây chép NGUYÊN VĂN từ tests/test_khach_hang.py —
# dùng chung cho cả ba task của đợt 4c (Task 2, Task 3 dùng lại). Tên và chữ
# ký phải giữ y hệt bản gốc, nếu không hai task sau chép lại sẽ lệch.

def _mua(conn, batch, ma_khach, ngay: date, tien=110_000, tax=10_000, gp=30_000,
         hang="XT07"):
    from kome.loaders import sales
    b = batch(abs(hash((ma_khach, ngay, hang))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ma_khach[-4:]}{ngay:%m%d}{hang}", "line_seq": 1,
        "sales_date": ngay, "customer_code": ma_khach, "product_code": hang,
        "pack_code": "02", "case_qty": 1, "qty": 6, "unit_price": 5250,
        "unit_cost": 3210, "amount": tien, "tax_amount": tax,
        "cost": tien - tax - gp, "gross_profit": gp, "paid_amount": 0,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


def _ho_so_khach(conn, batch, ma, ten, **kw):
    """Một dòng core.dim_customer hiện hành."""
    b = batch(abs(hash(ma)) % 80_000 + 10_000)
    conn.execute(
        """INSERT INTO core.dim_customer
             (customer_code, valid_from, valid_to, is_current, customer_name,
              phone, prefecture, city, address, salesperson_code,
              price_level_code, batch_id)
           VALUES (%s, '2025-01-01', '9999-12-31', true, %s, %s, %s, %s, %s, %s,
                   %s, %s)""",
        (ma, ten, kw.get("phone", "080-0000-0000"), kw.get("prefecture", "東京都"),
         kw.get("city", "渋谷区"), kw.get("address", "1-1-1"),
         kw.get("salesperson_code", "0104"), kw.get("price_level_code"), b))
    conn.commit()


# Mốc thời gian của mọi phép tính = ngày bán mới nhất trong kho.
HOM_NAY = date(2026, 7, 31)


def test_dim_prefecture_du_47_tinh(conn):
    assert conn.execute("SELECT count(*) FROM core.dim_prefecture").fetchone()[0] == 47


def test_ma_jis_du_01_den_47_khong_thieu_khong_trung(conn):
    ma = [r[0] for r in conn.execute(
        "SELECT ma_jis FROM core.dim_prefecture ORDER BY ma_jis").fetchall()]
    assert ma == [f"{i:02d}" for i in range(1, 48)]


def test_khong_hai_tinh_cung_mot_o_luoi(conn):
    # Ràng buộc UNIQUE (hang_luoi, cot_luoi) của bảng đã chặn một INSERT trùng
    # ô ngay lúc migration chạy — nên test này KHÔNG BAO GIỜ đỏ vì DỮ LIỆU sai
    # (dữ liệu sai kiểu đó không lọt được qua migration để đến đây). Giá trị
    # thật của nó là canh CHÍNH RÀNG BUỘC còn tồn tại: bắt một migration sau
    # này lỡ DROP/CREATE lại bảng mà quên chép UNIQUE — lúc đó, và chỉ lúc đó,
    # một tỉnh chồng ô mới lọt vào được và bài test này mới có cơ hội đỏ.
    trung = conn.execute("""
        SELECT hang_luoi, cot_luoi, count(*) FROM core.dim_prefecture
        GROUP BY 1, 2 HAVING count(*) > 1""").fetchall()
    assert trung == []


def test_moi_vung_la_mot_khoi_lien_nhau(conn):
    # Kề 8 hướng (kể cả chéo). Một vùng bị vỡ làm đôi trên lưới là lưới đặt sai,
    # và mắt người đọc bản đồ sẽ thấy trước khi test thấy.
    o = {}
    for vung, h, c in conn.execute(
            "SELECT vung, hang_luoi, cot_luoi FROM core.dim_prefecture").fetchall():
        o.setdefault(vung, set()).add((h, c))
    for vung, cells in o.items():
        dau = next(iter(cells))
        tham, hang_doi = {dau}, [dau]
        while hang_doi:
            h, c = hang_doi.pop()
            for dh in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    ke = (h + dh, c + dc)
                    if ke in cells and ke not in tham:
                        tham.add(ke)
                        hang_doi.append(ke)
        assert tham == cells, f"vùng {vung} bị vỡ thành nhiều khối rời"


def test_ten_tinh_khop_chuoi_OBC_that(conn, batch):
    # Khoá nối là chính chuỗi tên tỉnh OBC ghi. Sai một ký tự là tỉnh đó rỗng
    # vĩnh viễn trên bản đồ, và không có lỗi nào nổ ra. Test phải DÙNG dòng nó
    # gieo — khẳng định phép NỐI THẬT (JOIN core.dim_customer trên
    # dim_prefecture.ten), không chỉ khẳng định dim_prefecture có sẵn dòng
    # '東京都' (điều đó đúng ngay cả khi phép nối hỏng hoàn toàn).
    conn.execute("""
        INSERT INTO core.dim_customer
            (customer_code, customer_name, prefecture, is_current, valid_from, batch_id)
        VALUES ('BD01', 'Quan an Tokyo', '東京都', true, '2026-01-01', %s)""", (batch(1),))
    dem = conn.execute("""
        SELECT count(*) FROM core.dim_prefecture p
        JOIN core.dim_customer c ON c.prefecture = p.ten
        WHERE c.customer_code = 'BD01'""").fetchone()[0]
    assert dem == 1


def test_khach_theo_tinh_khong_dem_trung_khi_khach_o_NHIEU_nhom_viec(conn, batch):
    # mart.khach_nhom_viec cho phép MỘT khách thuộc NHIỀU nhóm ('im' và 'tut'
    # cùng lúc). LEFT JOIN thẳng vào nó sẽ nhân đôi dòng khách và thổi phồng
    # `so_khach` của tỉnh. Phải dùng EXISTS — đúng nếp migration 022.
    #
    # Không gieo một khách "vừa im vừa tụt" (dựng được nhưng mong manh: nó phụ
    # thuộc hai công thức khác nhau cùng khớp). Khẳng định bất biến TỔNG, thứ
    # vỡ ngay khi có BẤT KỲ dòng nào bị nhân lên, dù vì nhóm nào.
    _ho_so_khach(conn, batch, "BD01", "Quan A", prefecture="東京都")
    _mua(conn, batch, "BD01", HOM_NAY - timedelta(days=5))
    tong_view = conn.execute(
        "SELECT coalesce(sum(so_khach), 0) FROM mart.khach_theo_tinh").fetchone()[0]
    tong_that = conn.execute("SELECT count(*) FROM mart.khach_360").fetchone()[0]
    assert tong_view == tong_that
