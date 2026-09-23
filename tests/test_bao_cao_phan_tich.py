"""Đợt 5b Task 2 — tầng dữ liệu của `/bao-cao` (`kome/bao_cao.py`) đọc bảy
view phân tích của migration `029_mart_phan_tich.sql`.

Mỗi test canh một cách hiểu SAI mà nếu lọt thì trang vẫn vẽ ra bình thường,
chỉ là thiếu dòng hoặc nói sai số.
"""
from datetime import date

import pandas as pd
import pytest

from kome.bao_cao import tinh_bao_cao, tien_do_ngan_sach


def _ban(conn, batch, ngay: date, ma_hang: str, khach="000000009292",
         amount=110_000, tax=10_000, gp=30_000, sale="0104", n=1):
    """Một dòng bán thật qua loader, không SQL tay."""
    from kome.loaders import sales
    b = batch(abs(hash((ngay, ma_hang, khach, amount, tax, sale, n))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{khach[-4:]}{ma_hang}{n}", "line_seq": 1,
        "sales_date": ngay, "customer_code": khach, "product_code": ma_hang,
        "pack_code": "02", "case_qty": 1, "qty": 6, "unit_price": 5250,
        "unit_cost": 3210, "amount": amount, "tax_amount": tax,
        "cost": amount - tax - gp, "gross_profit": gp, "paid_amount": 0,
        "salesperson_code": sale, "batch_id": b,
    }]), ngay, b)
    conn.commit()
    return b


def _nganh(conn, batch, ma_hang: str, ten_nganh: str):
    """Một dòng core.dim_product mang ngành, cùng nếp tests/test_phan_tich_mart.py."""
    b = batch(abs(hash(("nganh", ma_hang))) % 40_000 + 300_000)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, food_category_name, batch_id)
           VALUES (%s, %s, %s, %s) ON CONFLICT (product_code) DO NOTHING""",
        (ma_hang, f"Hàng {ma_hang}", ten_nganh, b))
    conn.commit()


def _ngan_sach(conn, sale, thang, muc_tieu):
    conn.execute(
        "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
        "VALUES (%s, %s, %s)", (sale, thang, muc_tieu))
    conn.commit()


def _dem_truy_van(conn, monkeypatch):
    """Bọc `conn.execute` và đếm LÚC CHẠY, cùng nếp tests/test_san_pham.py:50-62."""
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    return dem


def test_bao_cao_khong_qua_11_truy_van(conn, batch, monkeypatch):
    """[IMPORTANT] Đo thật: một round-trip tới pooler Tokyo mất 47 ms. Trang
    chậm dần là cách nó chết mà không lỗi nào nổ ra."""
    _nganh(conn, batch, "AA01", "Ngành A")
    _ban(conn, batch, date(2025, 5, 11), "AA01", amount=110_000, tax=10_000, gp=30_000)
    _ban(conn, batch, date(2026, 5, 11), "AA01", amount=220_000, tax=20_000, gp=60_000, n=2)
    _ngan_sach(conn, "0104", date(2026, 5, 1), 100_000)

    dem = _dem_truy_van(conn, monkeypatch)
    bc = tinh_bao_cao(conn, 2026)
    tien_do_ngan_sach(conn, 2026)
    assert dem["n"] <= 11, f"chạy {dem['n']} truy vấn"
    assert bc.ky.company_fy == 2026


def test_cung_ky_noi_so_thang_doi_chieu(conn, batch):
    _ban(conn, batch, date(2025, 5, 11), "AA01", amount=110_000, tax=10_000, gp=30_000)
    _ban(conn, batch, date(2026, 5, 11), "AA01", amount=220_000, tax=20_000, gp=60_000, n=2)
    bc = tinh_bao_cao(conn, 2026)
    ck = bc.cung_ky
    assert ck is not None
    assert ck.so_thang == 1
    assert ck.tu == "2026-05" == ck.den
    assert ck.dt == 200_000 and ck.dt_ck == 100_000
    assert ck.tang_dt == pytest.approx(1.0)


def test_cung_ky_mau_so_am_thi_tang_truong_None(conn, batch):
    """赤伝 (phiếu đỏ) làm doanh thu cùng kỳ năm trước ÂM — chia cho mẫu số âm
    ra phần trăm ngược dấu, nên phải None chứ không phải một con số sai."""
    _ban(conn, batch, date(2025, 5, 11), "AA01", amount=-110_000, tax=-10_000, gp=-30_000)
    _ban(conn, batch, date(2026, 5, 11), "AA01", amount=220_000, tax=20_000, gp=60_000, n=2)
    bc = tinh_bao_cao(conn, 2026)
    ck = bc.cung_ky
    assert ck.dt_ck == -100_000
    assert ck.tang_dt is None
    assert ck.tang_lg is None


def test_nganh_ky_va_nganh_thang_doc_dung_ky(conn, batch):
    """Không lẫn dòng của kỳ khác — kỳ 2025 và 2026 phải tách bạch."""
    _nganh(conn, batch, "AA01", "Ngành A")
    _ban(conn, batch, date(2024, 12, 11), "AA01", amount=55_000, tax=5_000, gp=10_000)
    _ban(conn, batch, date(2026, 5, 11), "AA01", amount=220_000, tax=20_000, gp=60_000, n=2)

    bc = tinh_bao_cao(conn, 2026)
    thang_cua_2026 = {nt.thang for nt in bc.nganh_thang}
    assert "2024-12" not in thang_cua_2026
    assert "2026-05" in thang_cua_2026

    assert len(bc.nganh_ky) == 1
    assert bc.nganh_ky[0].nganh == "Ngành A"
    assert bc.nganh_ky[0].doanh_thu == 200_000

    bc_2025 = tinh_bao_cao(conn, 2025)
    assert bc_2025.nganh_ky[0].doanh_thu == 50_000


def test_tap_trung_top10_va_so_khach(conn, batch):
    for i in range(12):
        khach = f"00000000{9300 + i}"
        _ban(conn, batch, date(2026, 5, 11), "AA01", khach=khach,
             amount=(110_000 + i * 1_000), tax=10_000, gp=30_000, n=i)
    bc = tinh_bao_cao(conn, 2026)
    tt = bc.tap_trung
    assert tt is not None
    assert len(tt.dong) <= 20
    assert tt.so_khach == 12
    hang_10 = next(d for d in tt.dong if d.thu_hang == 10)
    assert tt.luy_ke_top10 == hang_10.luy_ke


def test_pareto_doc_tap_trung_khach_MOT_LAN():
    """[Vòng soát cuối, I-1] Câu SQL Pareto (khối (3) của `tinh_bao_cao`) chỉ
    được tham chiếu `mart.tap_trung_khach` ĐÚNG MỘT LẦN. Bản trước đọc view
    này hai lần trong CÙNG một câu — SELECT ngoài + truy vấn con
    `(SELECT max(thu_hang) FROM mart.tap_trung_khach ...)` — đúng lớp lỗi
    CTE-trùng đã ghi ở CLAUDE.md: Postgres KHÔNG gộp các truy vấn con trùng
    nhau, mỗi lần tham chiếu là một lần đánh giá lại cả view (cùng phép
    quét/CTE bên trong `mart.tap_trung_khach`). Đọc trực tiếp mã nguồn thay
    vì EXPLAIN vì test này không cần CSDL thật."""
    import inspect
    import re

    from kome import bao_cao as BC

    src = inspect.getsource(BC.tinh_bao_cao)
    m = re.search(r"SELECT customer_code, ten_khach.*?LIMIT 20", src, re.S)
    assert m, "không tìm thấy câu SQL Pareto trong tinh_bao_cao()"
    sql = m.group(0)
    assert sql.count("tap_trung_khach") == 1, (
        "câu SQL Pareto đọc mart.tap_trung_khach nhiều hơn một lần: " + sql)
    assert "count(*) over ()" in sql.lower(), (
        "phải dùng count(*) OVER () thay cho truy vấn con max(thu_hang)")


def test_hang_top10_theo_lai_gop_giu_nguyen_hanh_vi(conn, batch):
    for i in range(15):
        ma = f"MA{i:02d}"
        _ban(conn, batch, date(2026, 5, 11), ma, amount=110_000 + i * 1_000,
             tax=10_000, gp=10_000 + i * 5_000, n=i)
    bc = tinh_bao_cao(conn, 2026)

    truy_van_cu = [dict(zip(
        ("ma", "ten", "nhom", "doanh_thu", "lai_gop", "ty_suat", "so_khach"), r))
        for r in conn.execute(
            """SELECT product_code, ten_hang, food_category_name, doanh_thu_thuan,
                      lai_gop, ty_suat, so_khach_mua
               FROM mart.ban_theo_san_pham WHERE company_fy = 2026
               ORDER BY lai_gop DESC LIMIT 10""").fetchall()]

    assert [h["ma"] for h in bc.hang] == [h["ma"] for h in truy_van_cu]
    assert [h["lai_gop"] for h in bc.hang] == [h["lai_gop"] for h in truy_van_cu]


def test_sap_xep_hang_top10_dung_am_vo_cuc_cho_lai_gop_none():
    """[Vòng soát cuối, M4] Khoá sắp xếp bảng top-10 lãi gộp phải coi
    `lai_gop is None` là `float('-inf')`, KHÔNG phải hằng số `-1`: `lai_gop`
    là số nguyên yên KHÔNG CÓ CHẶN DƯỚI (một mã có thể lỗ hàng chục triệu),
    nên `-1` không phải giá trị nhỏ nhất có thể — một mã lỗ -50.000 yên
    (`-50_000 < -1`) sẽ bị hằng số `-1` xếp SAU nó, tức "không biết lãi gộp"
    trông NHỎ HƠN một khoản lỗ thật, ngược với ý định "không biết luôn đứng
    cuối". `gross_profit` là NOT NULL trong schema (007_fact_sales.sql) nên
    không dàn dựng được một `lai_gop` NULL thật qua loader — kiểm bằng cách
    đọc thẳng mã nguồn khoá sắp xếp, cùng nếp `test_pareto_doc_tap_trung_
    khach_MOT_LAN`."""
    import inspect
    import re

    from kome import bao_cao as BC

    src = inspect.getsource(BC.tinh_bao_cao)
    m = re.search(r"hang = sorted\(hang_theo_nganh,.*?\)\[:TOP\]", src, re.S)
    assert m, "không tìm thấy khối sắp xếp `hang` trong tinh_bao_cao()"
    khoi = m.group(0)
    assert "float(\"-inf\")" in khoi or "float('-inf')" in khoi, (
        "khoá sắp xếp phải dùng float('-inf') cho lai_gop None: " + khoi)
    assert re.search(r"else\s*-1\b", khoi) is None, (
        "khoá sắp xếp vẫn còn hằng số -1 làm giá trị thay thế cho None")


def test_kho_rong_van_dung_duoc_bao_cao(conn):
    bc = tinh_bao_cao(conn)
    assert bc.khong_co_du_lieu is True
    assert bc.cung_ky is None
    assert bc.nganh_thang == []
    assert bc.nganh_ky == []
    assert bc.tap_trung is None
    assert bc.hang_theo_nganh == []
    assert bc.hang == []
