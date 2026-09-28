"""Khách hàng + Sản phẩm theo MỘT kỳ so (đặc tả 2026-09-28-ky-so-sanh-toan-web-design.md §7 đợt 3).

Bản đồ, hồ sơ khách (12 tháng · mặt hàng), Sản phẩm 360 (24 tháng · theo ngày · 26 tuần ·
khách mới/quay lại) đọc `so_sanh[0]`, và các ngân sách lượt hỏi không đổi: phép so đi CHUNG
câu có sẵn; 26 tuần / khách mới đọc hàm có tham số ngày cuối (057) — hàm cũ là lớp bọc.
"""
from datetime import date, timedelta

from kome import ban_do as BD
from kome import ban_khoang as BK
from kome import khoang_xem as KX
from kome import san_pham as SP
from kome import san_pham_360 as SP360
from tests.test_ban_do import _ho_so_khach, _mua
from tests.test_mart_san_pham import _san_pham


def _gieo(conn, batch):
    _ho_so_khach(conn, batch, "KA01", "Quan Tokyo", prefecture="東京都", salesperson_code="0104")
    _ho_so_khach(conn, batch, "KA02", "Quan Osaka", prefecture="大阪府", salesperson_code="0102")
    _mua(conn, batch, "KA01", date(2025, 7, 4), tien=44_000, tax=4_000, hang="XT07")
    _mua(conn, batch, "KA01", date(2026, 6, 8), tien=66_000, tax=6_000, hang="XT07")
    _mua(conn, batch, "KA01", date(2026, 6, 20), tien=11_000, tax=1_000, hang="XT08")
    _mua(conn, batch, "KA01", date(2026, 7, 2), tien=110_000, tax=10_000, hang="XT07")
    _mua(conn, batch, "KA01", date(2026, 7, 9), tien=55_000, tax=5_000, hang="XT08")
    _mua(conn, batch, "KA02", date(2026, 6, 5), tien=33_000, tax=3_000, hang="XT07")
    for ma in ("XT07", "XT08", "XT09"):
        _san_pham(conn, batch, ma, ten=f"Hàng {ma}")


def _kx(conn, **ts):
    return KX.giai_conn(conn, KX.doc_tham_so(**ts))


def _dt(conn, tu, den):
    return int(conn.execute("SELECT dt FROM mart.tong_khoang(%s, %s)", (tu, den)).fetchone()[0] or 0)


def test_ban_do_doanh_thu_ky_so_theo_tinh(conn, batch):
    _gieo(conn, batch)
    kx = _kx(conn, ss="truoc")                     # 1 → 9/7/2026, so 1 → 9/6/2026
    t = BD.ban_do(conn, chi_so="dt_khoang", kx=kx)
    o = {x.ten: x for x in t.o}
    assert o["東京都"].dt_khoang_ss == 60_000 and o["大阪府"].dt_khoang_ss == 30_000
    assert t.tong["dt_khoang_ss"] == _dt(conn, kx.so_sanh[0].tu, kx.so_sanh[0].den)
    # Năm trước (1 → 9/7/2025): chỉ KA01 mua ngày 4/7.
    t = BD.ban_do(conn, chi_so="dt_khoang", kx=_kx(conn))
    assert {x.ten: x.dt_khoang_ss for x in t.o if x.dt_khoang_ss} == {"東京都": 40_000}


def test_ho_so_khach_12_thang_va_mat_hang_theo_ky_so(conn, batch):
    _gieo(conn, batch)
    d = BK.cua_khach(conn, _kx(conn, ss="truoc"), "KA01")
    t = d["thang_ss"]
    assert list(t)[-1] == "2026-07" and len(t) == 12
    # 6/2026 ← 5/2026 (trong dải dữ liệu, không mua) = 0; 7/2026 dở dang ← 1 → 9/6 (60.000).
    assert t["2026-06"] == 0 and t["2026-07"] == 60_000
    assert t["2025-08"] == 40_000, "8/2025 ← 7/2025"
    t = BK.cua_khach(conn, _kx(conn), "KA01")["thang_ss"]
    assert t["2026-06"] is None, "năm trước của 6/2026 = 6/2025, trước dữ liệu — không phải 0"
    mh = {m["ma"]: m["dt_ss"] for m in d["mat_hang"]}
    assert mh == {"XT07": 60_000, "XT08": 0}, "XT08 mua 20/6 — ngoài dải so 1 → 9/6"


def test_san_pham_24_thang_theo_ky_so(conn, batch):
    _gieo(conn, batch)
    d = BK.cua_ma(conn, _kx(conn), "XT07")         # năm trước
    t = d["thang_ss"]
    assert len(t) == 24 and list(t)[-1] == "2026-07"
    assert t["2026-07"] == 40_000, "7/2026 dở dang so 1 → 9/7/2025"
    assert t["2026-06"] is None, "6/2025 trước dữ liệu"


def test_ban_theo_ngay_lui_theo_ky_so(conn, batch):
    _gieo(conn, batch)
    d = SP.ban_theo_ngay(conn, "XT07", "2026-07", 12)
    assert d["thang_so"] == "2025-07" and sum(x["doanh_thu"] for x in d["truoc"]) == 40_000
    assert all(x["ngay"].month == 7 and x["ngay"].year == 2025 for x in d["truoc"])
    d = SP.ban_theo_ngay(conn, "XT07", "2026-07", 1)
    assert d["thang_so"] == "2026-06" and sum(x["doanh_thu"] for x in d["truoc"]) == 90_000
    d = SP.ban_theo_ngay(conn, "XT07", "2026-07", None)
    assert d["truoc"] == [] and d["thang_so"] is None


def test_057_ham_cu_BANG_ham_co_tham_so_tai_moc(conn, batch):
    _gieo(conn, batch)
    for ham in ("sp_theo_tuan", "sp_khach_moi_thang"):
        a = conn.execute(f"SELECT * FROM mart.{ham}('XT07')").fetchall()
        b = conn.execute(f"SELECT * FROM mart.{ham}_den('XT07', (SELECT hom_nay FROM mart.moc_thoi_gian))").fetchall()
        assert a == b and a, ham


def test_26_tuan_va_khach_moi_cua_ky_so(conn, batch):
    _gieo(conn, batch)
    tg = SP360.tab_thoi_gian(conn, "XT07", SP360.LUI_MAC_DINH)
    # 26 tuần lùi 52 tuần bắt đầu trước dữ liệu (7/2025) -> không so (không phải "0").
    assert tg["tuan_ss"] == [] and tg["tuan_lui"] == 52
    tg = SP360.tab_thoi_gian(conn, "XT07", SP360.lui_cua(_kx(conn, ss="truoc")))
    assert tg["tuan_lui"] == 4
    kh = SP360.tab_khach(conn, "XT07", (12, None))
    assert kh["khach_moi_ss"] == [], "cửa sổ 12 tháng lùi 12 tháng (8/2024 → 7/2025) bắt đầu trước dữ liệu"
    kh = SP360.tab_khach(conn, "XT07", (1, None))       # 7/2025 → 6/2026: trọn trong dữ liệu
    ss = {x["thang"]: x for x in kh["khach_moi_ss"]}
    assert len(ss) == 12 and ss["2025-07"]["moi"] == 1 and ss["2026-06"]["quay_lai"] == 1
    kh = SP360.tab_khach(conn, "XT07", (None, None))
    assert kh["khach_moi_ss"] == [] and len(kh["khach_moi"]) == 12


def test_26_tuan_ky_so_khop_ham_tai_ngay_lui(conn, batch):
    """Khi cửa sổ lùi nằm trọn trong dữ liệu, chuỗi kỳ so = đúng hàm 057 tại mốc − n tuần."""
    _san_pham(conn, batch, "XT09", ten="Hàng XT09")
    base = date(2025, 1, 6)
    for i in range(0, 60):
        _mua(conn, batch, "KB01", base + timedelta(days=7 * i), tien=1_100, tax=100, hang="XT09")
    tg = SP360.tab_thoi_gian(conn, "XT09", (1, 4))
    moc = conn.execute("SELECT hom_nay FROM mart.moc_thoi_gian").fetchone()[0]
    ky_vong = conn.execute("SELECT tuan, so_luong FROM mart.sp_theo_tuan_den('XT09', %s)",
                           (moc - timedelta(days=28),)).fetchall()
    assert [(x["tuan"], float(x["so_luong"])) for x in tg["tuan_ss"]] == \
        [(str(t), float(sl)) if isinstance(tg["tuan_ss"][0]["tuan"], str) else (t, float(sl)) for t, sl in ky_vong]
    assert len(tg["tuan_ss"]) == 26
